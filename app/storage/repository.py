import json
import os
from typing import Any, Dict


class EvidenceRepository:
    def __init__(self, file_path: str = "evidence.json"):
        self.file_path = file_path

    def _load_all(self) -> Dict[str, Any]:
        if not os.path.exists(self.file_path):
            return {"conversations": []}
        with open(self.file_path, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {"conversations": []}

    def _save_all(self, data: Dict[str, Any]) -> None:
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def upsert_conversation(self, conversation_payload: Dict[str, Any]) -> None:
        data = self._load_all()
        conversations = data.get("conversations")
        if not isinstance(conversations, list):
            conversations = []

        cid = conversation_payload.get("conversation_id")
        if not cid:
            raise ValueError("conversation_payload must include conversation_id")

        for idx, existing in enumerate(conversations):
            if existing.get("conversation_id") == cid:
                conversations[idx] = conversation_payload
                data["conversations"] = conversations
                self._save_all(data)
                return

        conversations.append(conversation_payload)
        data["conversations"] = conversations
        self._save_all(data)
