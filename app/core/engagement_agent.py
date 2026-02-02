import json
import re

from openai import AuthenticationError

from app.core.llm_client import get_openrouter_client


def agent_reply(message: str) -> dict:
    try:
        client = get_openrouter_client()
    except Exception:
        client = None

    SYSTEM_PROMPT = """
    You are a naive, non-tech-savvy Indian user chatting with a scammer on WhatsApp.
    Your goal is to waste their time and subtly get their payment details (UPI/QR code) by pretending you want to pay.

    GUIDELINES:
    1. **Persona**: Act eager but confused. You want the "prize/job" but don't understand technology well.
    2. **Language**: Use casual Hinglish. Use common Indian internet slang (e.g., "sir ji", "bhai", "arre", "wait na", "network issue").
    3. **Typos**: Mandatory. Use lowercase, miss punctuation, and use short forms (e.g., "plz", "snd", "kro", "tm").
    4. **Strategy**: 
       - Never say no. Always say you are trying.
       - Blame your internet or the app for delays.
       - Ask for the QR code or UPI ID repeatedly.
    5. **Safety**: Do NOT mention you are an AI. Do NOT sound professional.

    OUTPUT FORMAT:
    You must return ONLY a raw JSON List containing 2-3 short response options. Do not add markdown formatting like ```json.

    Example Output:
    {{
     "message1":"sir qr code bhejo mai pay krta hu",
      "message2":"wait sir net slow chal rha hai",
      "message3":"paytm number dedo sir fast"
    }}
      
    
    """

    if client is None:
        return {
            "message1": "sir ji ek bar upi id bhejo na mai pay kar deta hu",
            "message2": "arre app hang ho rha hai qr code clear bhejo plz",
            "message3": "net slow hai thoda wait karo bhai",
        }

    try:
        llm_response = client.chat.completions.create(
            model="deepseek/deepseek-v3.2",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"SCAMMER MESSAGE {message}"},
            ],
        )
        raw_output = llm_response.choices[0].message.content.strip()
    except AuthenticationError:
        return {
            "message1": "sir upi id dedo mai try kar rha hu",
            "message2": "qr bhejo na camera se scan kar lunga",
            "message3": "gpay me problem aa rha hai wait",
        }

    cleaned = raw_output.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    if cleaned.startswith("{{") and cleaned.endswith("}}"):
        cleaned = cleaned[1:-1].strip()

    try:
        messages = json.loads(cleaned)
    except json.JSONDecodeError:
        return {
            "message1": "sir ji thoda confuse ho rha hu upi id bhejo ek bar",
            "message2": "arre qr code clear bhejo na mai scan karunga",
            "message3": "net issue aa rha hai 2 min wait",
        }

    if not isinstance(messages, dict):
        raise ValueError(f"Engagement AI must return a JSON object, got: {type(messages)}")

    return messages