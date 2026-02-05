
import os
import uuid
from typing import Any, Dict, Optional, List

from dotenv import load_dotenv
from fastapi import Body, Depends, FastAPI, Header, HTTPException, Request, BackgroundTasks
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.core.conversation_manager import ConversationManager
from app.core.engagement_agent import agent_reply
from app.core.scam_detector import is_scam
from app.services.intelligence_service import extract_evidence
from app.storage.repository import EvidenceRepository
from app.services.reporting_service import report_to_evaluator


load_dotenv()

app = FastAPI(title="Agentic AI Honeypot", version="1.0")

_repo = EvidenceRepository(file_path="evidence.json")
_sessions: Dict[str, ConversationManager] = {}


def _require_api_key(x_api_key: Optional[str] = Header(default=None)) -> None:
    expected = os.getenv("HONEYPOT_API_KEY")
    if not expected:
        raise HTTPException(
            status_code=500,
            detail="Server misconfigured: set env var HONEYPOT_API_KEY",
        )

    if x_api_key and x_api_key.strip() == expected:
        return

    raise HTTPException(status_code=401, detail="Invalid API key")


def _require_api_key_flexible(
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    authorization: Optional[str] = Header(default=None),
) -> None:
    expected = os.getenv("HONEYPOT_API_KEY")
    if not expected:
        raise HTTPException(
            status_code=500,
            detail="Server misconfigured: set env var HONEYPOT_API_KEY",
        )

    if x_api_key and x_api_key.strip() == expected:
        return

    if authorization:
        parts = authorization.strip().split()
        if len(parts) == 2 and parts[0].lower() == "bearer" and parts[1] == expected:
            return

    raise HTTPException(status_code=401, detail="Invalid API key")


class CreateConversationResponse(BaseModel):
    conversation_id: str


class MessageRequest(BaseModel):
    conversation_id: Optional[str] = None
    message: str
    handoff: bool = False


class MessageResponse(BaseModel):
    conversation_id: str
    scam_detected: bool
    handoff_active: bool
    agent_message: Optional[str] = None
    evidence: Dict[str, Any] = {}


class ScanResponse(BaseModel):
    scam_detected: bool
    agent_message: Optional[str] = None
    evidence: Dict[str, Any] = {}


class IncomingMessage(BaseModel):
    sender: str
    text: str
    timestamp: Optional[int] = None


class IncomingMetadata(BaseModel):
    channel: Optional[str] = None
    language: Optional[str] = None
    locale: Optional[str] = None


class EvaluationRequest(BaseModel):
    sessionId: Optional[str] = None
    message: Optional[IncomingMessage] = None
    conversationHistory: Optional[List[IncomingMessage]] = []
    metadata: Optional[IncomingMetadata] = None
    # Flexible extra fields
    conversation_id: Optional[str] = None
    text: Optional[str] = None
    input: Optional[str] = None
    handoff: Optional[bool] = None


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={
            "error": "INVALID_REQUEST_BODY",
            "detail": "Request body did not match expected JSON schema.",
        },
    )


def _process_message(cm: ConversationManager, message: str, *, handoff: bool, background_tasks: Optional[BackgroundTasks] = None) -> MessageResponse:
    if handoff:
        cm.set_handoff_active(True)

    cm.add_message(role="scammer", content=message)

    extracted = extract_evidence(message, use_llm_fallback=True)
    cm.merge_evidence(extracted)

    detected_now = is_scam(message)
    if detected_now:
        cm.set_scam_detected(True)

    agent_message: Optional[str] = None
    if cm.state.scam_detected and cm.state.handoff_active:
        desired_fields = ("upi_id", "phishing_links", "account_number", "ifsc_code")
        missing_fields = [k for k in desired_fields if not cm.state.evidence.get(k)]
        recent_history = [f"{e.role}: {e.content}" for e in cm.state.history[-10:]]
        options = agent_reply(
            message,
            missing_fields=missing_fields,
            recent_history=recent_history,
        )
        values = [v for v in options.values() if isinstance(v, str) and v.strip()]
        agent_message = values[0] if values else None
        if agent_message:
            agent_message = " ".join(agent_message.split())
            cm.add_message(role="agent", content=agent_message)
        
        # Trigger external reporting if scam is confirmed and we are engaging
        if background_tasks:
            background_tasks.add_task(
                report_to_evaluator,
                session_id=cm.state.conversation_id,
                scam_detected=True,
                total_messages=len(cm.state.history),
                evidence=cm.state.evidence,
                agent_notes="Scam detected and agent engaging."
            )

    _repo.upsert_conversation(cm.to_json())

    return MessageResponse(
        conversation_id=cm.state.conversation_id,
        scam_detected=cm.state.scam_detected,
        handoff_active=cm.state.handoff_active,
        agent_message=agent_message,
        evidence=cm.state.evidence,
    )


@app.get("/health", dependencies=[Depends(_require_api_key_flexible)])
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/", response_model=MessageResponse, dependencies=[Depends(_require_api_key_flexible)])
def evaluate(background_tasks: BackgroundTasks, payload: Any = Body(default=None)) -> MessageResponse:
    """Primary evaluation endpoint (single URL).

    Accepts flexible request shapes used by different evaluators.
    Supported message fields: message | text | input
    """
    if payload is None:
        payload = {}

    if isinstance(payload, bytes):
        # Should not happen with FastAPI parsing logic usually
        pass 
        
    # Logic to normalize different payload shapes 
    # default values
    message_text = ""
    session_id = str(uuid.uuid4())
    handoff = True # Default to True for this endpoint as per requirements implying auto-agent activation if scam detected

    if isinstance(payload, dict):
        # Check for new format keys first
        if "sessionId" in payload:
            session_id = payload["sessionId"]
        elif "conversation_id" in payload:
            session_id = payload["conversation_id"]
        elif "conversationId" in payload:
            session_id = payload["conversationId"]
            
        # Check message content
        if "message" in payload and isinstance(payload["message"], dict):
            # Nested message object
            message_text = payload["message"].get("text", "")
        else:
            # Flat or legacy fields
            message_text = payload.get("message") or payload.get("text") or payload.get("input") or ""

        # Check handoff
        if "handoff" in payload:
             handoff = bool(payload["handoff"])
        elif "handoff_active" in payload:
             handoff = bool(payload["handoff_active"])

        # Create/Get Session
        cm = _sessions.get(session_id)
        if cm is None:
            cm = ConversationManager(conversation_id=session_id)
            _sessions[session_id] = cm
            
            # Populate history if new session and history provided in payload
            if "conversationHistory" in payload and isinstance(payload["conversationHistory"], list):
                for msg in payload["conversationHistory"]:
                    if isinstance(msg, dict):
                        role = "scammer" if msg.get("sender") == "scammer" else "user" # mapping 'user' to something? or 'agent'? 
                        # Assuming 'user' maps to 'agent' context or just ignored if innocent.
                        # Simple mapping:
                        role_map = "scammer" if msg.get("sender") == "scammer" else "agent"
                        cm.add_message(role=role_map, content=msg.get("text", ""))

    elif isinstance(payload, EvaluationRequest):
        # Pydantic model usage (if fastAPI matches it automatically, but we used Any above)
        # This branch might not be hit if we stick to Any validation manual
        pass
        
    if not message_text.strip():
        # Fallback for empty message
        message_text = "Hello"

    cm = _sessions.get(session_id)
    if cm is None:
        cm = ConversationManager(conversation_id=session_id)
        _sessions[session_id] = cm

    return _process_message(cm, message_text, handoff=handoff, background_tasks=background_tasks)


@app.post("/conversations", response_model=CreateConversationResponse, dependencies=[Depends(_require_api_key_flexible)])
def create_conversation() -> CreateConversationResponse:
    conversation_id = str(uuid.uuid4())
    _sessions[conversation_id] = ConversationManager(conversation_id=conversation_id)
    _repo.upsert_conversation(_sessions[conversation_id].to_json())
    return CreateConversationResponse(conversation_id=conversation_id)


@app.post("/message", response_model=MessageResponse, dependencies=[Depends(_require_api_key_flexible)])
def post_message(background_tasks: BackgroundTasks, payload: MessageRequest) -> MessageResponse:
    conversation_id = payload.conversation_id or str(uuid.uuid4())
    cm = _sessions.get(conversation_id)
    if cm is None:
        cm = ConversationManager(conversation_id=conversation_id)
        _sessions[conversation_id] = cm
    return _process_message(cm, payload.message, handoff=payload.handoff, background_tasks=background_tasks)

@app.post("/honeypot", response_model=MessageResponse, dependencies=[Depends(_require_api_key_flexible)])
def evaluate_alias(background_tasks: BackgroundTasks, payload: MessageRequest) -> MessageResponse:
    return evaluate(background_tasks, payload.model_dump())

@app.post("/scan", response_model=ScanResponse, dependencies=[Depends(_require_api_key_flexible)])
def scan(payload: Any = Body(default=None)) -> ScanResponse:
    # ... (existing scan logic, maybe update to use new reporting if needed? scan is stateless so maybe not)
    # Keeping scan purely stateless as before
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}

    message = payload.get("message") or payload.get("text") or payload.get("input")
    if not isinstance(message, str) or not message.strip():
        raise HTTPException(status_code=400, detail="INVALID_REQUEST_BODY")

    want_agent = bool(payload.get("handoff") or payload.get("handoff_active") or payload.get("handoffActive"))

    evidence = extract_evidence(message, use_llm_fallback=True)
    scam = is_scam(message)

    agent_message: Optional[str] = None
    if scam and want_agent:
        desired_fields = ("upi_id", "phishing_links", "account_number", "ifsc_code")
        missing_fields = [k for k in desired_fields if not evidence.get(k)]
        options = agent_reply(message, missing_fields=missing_fields, recent_history=[f"scammer: {message}"])
        values = [v for v in options.values() if isinstance(v, str) and v.strip()]
        agent_message = values[0] if values else None
        if agent_message:
            agent_message = " ".join(agent_message.split())

    return ScanResponse(
        scam_detected=scam,
        agent_message=agent_message,
        evidence=evidence,
    )
