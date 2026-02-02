
import os
import uuid
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException
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
    if not x_api_key or x_api_key != expected:
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
        options = agent_reply(message)
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


@app.get("/health", dependencies=[Depends(_require_api_key)])
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/", response_model=MessageResponse, dependencies=[Depends(_require_api_key)])
def evaluate(payload: MessageRequest) -> MessageResponse:
    """Primary evaluation endpoint (single URL)."""
    conversation_id = payload.conversation_id or str(uuid.uuid4())
    cm = _sessions.get(conversation_id)
    if cm is None:
        cm = ConversationManager(conversation_id=conversation_id)
        _sessions[conversation_id] = cm
    return _process_message(cm, payload.message, handoff=payload.handoff)


@app.post("/honeypot", response_model=MessageResponse, dependencies=[Depends(_require_api_key)])
def evaluate_alias(payload: MessageRequest) -> MessageResponse:
    return evaluate(payload)


@app.post("/conversations", response_model=CreateConversationResponse, dependencies=[Depends(_require_api_key)])
def create_conversation() -> CreateConversationResponse:
    conversation_id = str(uuid.uuid4())
    _sessions[conversation_id] = ConversationManager(conversation_id=conversation_id)
    _repo.upsert_conversation(_sessions[conversation_id].to_json())
    return CreateConversationResponse(conversation_id=conversation_id)


@app.post("/message", response_model=MessageResponse, dependencies=[Depends(_require_api_key)])
def post_message(payload: MessageRequest) -> MessageResponse:
    conversation_id = payload.conversation_id or str(uuid.uuid4())
    cm = _sessions.get(conversation_id)
    if cm is None:
        cm = ConversationManager(conversation_id=conversation_id)
        _sessions[conversation_id] = cm
    return _process_message(cm, payload.message, handoff=payload.handoff)
