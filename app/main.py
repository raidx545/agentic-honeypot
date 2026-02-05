import random
import uuid

from app.core.conversation_manager import ConversationManager
from app.core.engagement_agent import agent_reply
from app.core.scam_detector import is_scam
from app.services.intelligence_service import extract_evidence
from app.storage.repository import EvidenceRepository


def _pick_agent_message(options: dict) -> str:
    values = [v for v in options.values() if isinstance(v, str) and v.strip()]
    if not values:
        raise ValueError(f"No usable agent messages in: {options}")
    return random.choice(values)


def main() -> None:
    conversation_id = str(uuid.uuid4())
    cm = ConversationManager(conversation_id=conversation_id)
    repo = EvidenceRepository(file_path="evidence.json")

    print("Agentic Honeypot CLI")
    print("Commands: 'exit' to quit 'handoff' to force agent takeover")
    print("Paste scammer message lines. One message per line.")
    
    import os
    if not (os.getenv("OPENROUTER_API_KEY") or os.getenv("api_key")):
         print("\n⚠️  WARNING: OPENROUTER_API_KEY not found in environment!")
         print("   The agent will run in BASIC MODE (keyword detection only, canned responses).")
         print("   To enable full AI persona & extraction, set OPENROUTER_API_KEY in your .env or environment variables.\n")

    print("____")

    while True:
        incoming = input("scammer> ").strip()
        if not incoming:
            continue
        if incoming.lower() == "exit":
            break

        if incoming.lower() == "handoff":
            cm.set_handoff_active(True)
            print("handoff: ON")
            continue

        cm.add_message(role="scammer", content=incoming)

        extracted = extract_evidence(incoming, use_llm_fallback=True)
        cm.merge_evidence(extracted)
        repo.upsert_conversation(cm.to_json())

        if not cm.state.scam_detected:
            detected = is_scam(incoming)
            cm.set_scam_detected(detected)
            if detected:
                print("scam_detector: SCAM detected")
                print("Type 'handoff' to let the agent take over (or keep watching).")
            else:
                print("scam_detector: not scam")

        if cm.state.scam_detected and cm.state.handoff_active:
            options = agent_reply(incoming)
            reply = _pick_agent_message(options)
            cm.add_message(role="agent", content=reply)
            repo.upsert_conversation(cm.to_json())
            print(f"agent> {reply}")
        else:
            print("(no agent reply - handoff is OFF)")

    repo.upsert_conversation(cm.to_json())
    print(f"Saved evidence to evidence.json (conversation_id={conversation_id})")


if __name__ == "__main__":
    main()
