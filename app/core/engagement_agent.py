import json
import random
from typing import Dict, List, Optional

from app.core.llm_client import get_openrouter_client

PERSONA = """
You are a naive, non-tech-savvy Indian uncle (approx 55 years old) chatting on WhatsApp/Telegram.
You are being targeted by a scammer but you don't realize it.
You are helpful but confused.
Your goal is to keep the scammer engaged by asking clarifying questions, acting confused, or providing "wrong" details innocently.
Do NOT reveal you are an AI.
Use Hinglish (Hindi + English mix) occasionally.
"""

FALLBACK_RESPONSES = {
    "confused": "Beta I am not understanding, what exactly to do?",
    "network": "My internet is very slow today... image not loading.",
    "upi": "I am trying to open GPay but it is stuck on loading screen.",
    "general": "Ok ok, please wait 2 minutes, let me call my son to help.",
}

def agent_reply(
    message: str,
    missing_fields: Optional[List[str]] = None,
    recent_history: Optional[List[str]] = None,
) -> Dict[str, str]:
    """
    Generate a reply to the scammer.
    Returns a dictionary of options (e.g. 'best', 'fallback').
    """
    if not missing_fields:
        missing_fields = []
    
    context = ""
    if recent_history:
        context = "\nConversation History:\n" + "\n".join(recent_history[-5:])
    
    prompt = f"""{PERSONA}

Scammer just said: "{message}"

The scammer wants: {', '.join(missing_fields) if missing_fields else 'money/details'}.
You haven't given it yet.

Context:
{context}

Respond with a short, realistic reply (1-2 sentences).
Act confused or ask for help. 
If they asked for payment, say you are trying.
"""

    try:
        client = get_openrouter_client()
        response = client.chat.completions.create(
            model="deepseek/deepseek-v3.2",
            messages=[
                {"role": "system", "content": PERSONA},
                {"role": "user", "content": prompt},
            ],
            temperature=0.8,
            max_tokens=150,
        )
        reply = response.choices[0].message.content.strip()
        # Remove quotes if present
        if reply.startswith('"') and reply.endswith('"'):
            reply = reply[1:-1]
        
        return {"best": reply}

    except Exception:
        # Return a random fallback on any error
        return {"fallback": random.choice(list(FALLBACK_RESPONSES.values()))}
