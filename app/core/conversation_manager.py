from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class ConversationEvent:
    role: str
    content: str
    ts: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class ConversationState:
    conversation_id: str
    scam_detected: bool = False
    handoff_active: bool = False
    history: List[ConversationEvent] = field(default_factory=list)
    evidence: Dict[str, Any] = field(default_factory=dict)


class ConversationManager:
    def __init__(self, conversation_id: str):
        self.state = ConversationState(conversation_id=conversation_id)

    def add_message(self, role: str, content: str) -> None:
        self.state.history.append(ConversationEvent(role=role, content=content))

    def set_scam_detected(self, detected: bool) -> None:
        self.state.scam_detected = detected

    def set_handoff_active(self, active: bool) -> None:
        self.state.handoff_active = active

    def merge_evidence(self, extracted: Dict[str, Any]) -> None:
        if not extracted:
            return
        for k, v in extracted.items():
            if v is None:
                continue

            existing = self.state.evidence.get(k)
            if isinstance(v, list):
                merged = set(existing or [])
                merged.update(v)
                self.state.evidence[k] = sorted(merged)
            else:
                if existing in (None, ""):
                    self.state.evidence[k] = v

    def to_json(self) -> Dict[str, Any]:
        return {
            "conversation_id": self.state.conversation_id,
            "scam_detected": self.state.scam_detected,
            "handoff_active": self.state.handoff_active,
            "history": [e.__dict__ for e in self.state.history],
            "evidence": self.state.evidence,
        }
