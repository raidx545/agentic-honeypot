
import os
import uuid
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from fastapi import Body, Depends, FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.core.conversation_manager import ConversationManager
from app.core.engagement_agent import agent_reply
from app.core.scam_detector import is_scam
from app.services.intelligence_service import extract_evidence
from app.storage.repository import EvidenceRepository


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


def _process_message(cm: ConversationManager, message: str, *, handoff: bool) -> MessageResponse:
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

    _repo.upsert_conversation(cm.to_json())

    return MessageResponse(
        conversation_id=cm.state.conversation_id,
        scam_detected=cm.state.scam_detected,
        handoff_active=cm.state.handoff_active,
        agent_message=agent_message,
        evidence=cm.state.evidence,
    )


@app.api_route("/health", methods=["GET", "HEAD"])
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/", response_model=MessageResponse, dependencies=[Depends(_require_api_key_flexible)])
def evaluate(payload: Any = Body(default=None)) -> MessageResponse:
    """Primary evaluation endpoint (single URL).

    Accepts flexible request shapes used by different evaluators.
    Supported message fields: message | text | input
    """
    if payload is None:
        payload = {}

    if not isinstance(payload, dict):
        payload = {}

    raw_message = payload.get("message") or payload.get("text") or payload.get("input")
    message_provided = isinstance(raw_message, str) and bool(raw_message.strip())
    message = raw_message.strip() if message_provided else "Hello, please share your UPI ID or QR code for verification."

    conversation_id = payload.get("conversation_id") or payload.get("conversationId") or str(uuid.uuid4())

    handoff_keys_present = any(
        k in payload for k in ("handoff", "handoff_active", "handoffActive")
    )
    if message_provided:
        handoff = (
            bool(payload.get("handoff") or payload.get("handoff_active") or payload.get("handoffActive"))
            if handoff_keys_present
            else True
        )
    else:
        handoff = False

    cm = _sessions.get(conversation_id)
    if cm is None:
        cm = ConversationManager(conversation_id=conversation_id)
        _sessions[conversation_id] = cm
    return _process_message(cm, message, handoff=handoff)


@app.post("/honeypot", response_model=MessageResponse, dependencies=[Depends(_require_api_key_flexible)])
def evaluate_alias(payload: MessageRequest) -> MessageResponse:
    return evaluate(payload.model_dump())


@app.post("/scan", response_model=ScanResponse, dependencies=[Depends(_require_api_key_flexible)])
def scan(payload: Any = Body(default=None)) -> ScanResponse:
    """Stateless endpoint: evaluator sends one message, receives one JSON output.

    Supported message fields: message | text | input
    Optional flags: handoff | handoff_active | handoffActive (to request agent reply)
    """
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


@app.post("/conversations", response_model=CreateConversationResponse, dependencies=[Depends(_require_api_key_flexible)])
def create_conversation() -> CreateConversationResponse:
    conversation_id = str(uuid.uuid4())
    _sessions[conversation_id] = ConversationManager(conversation_id=conversation_id)
    _repo.upsert_conversation(_sessions[conversation_id].to_json())
    return CreateConversationResponse(conversation_id=conversation_id)


@app.post("/message", response_model=MessageResponse, dependencies=[Depends(_require_api_key_flexible)])
def post_message(payload: MessageRequest) -> MessageResponse:
    conversation_id = payload.conversation_id or str(uuid.uuid4())
    cm = _sessions.get(conversation_id)
    if cm is None:
        cm = ConversationManager(conversation_id=conversation_id)
        _sessions[conversation_id] = cm
    return _process_message(cm, payload.message, handoff=payload.handoff)
