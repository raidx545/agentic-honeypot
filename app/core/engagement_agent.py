import json
import re
from typing import List, Optional

from openai import AuthenticationError
from openai import RateLimitError

from app.core.llm_client import get_openrouter_client


def agent_reply(
    message: str,
    *,
    missing_fields: Optional[List[str]] = None,
    recent_history: Optional[List[str]] = None,
) -> dict:
    try:
        client = get_openrouter_client()
    except Exception:
        client = None

    missing_fields = missing_fields or []
    recent_history = recent_history or []
    missing_hint = ", ".join(missing_fields)
    history_hint = "\n".join(recent_history[-6:])

    SYSTEM_PROMPT = f"""
    You are roleplaying as a wealthy but lonely older person chatting with a scammer on WhatsApp.
    Your goal is to keep them talking and subtly extract payment details (UPI ID / QR, bank account + IFSC) and any links by pretending you are cooperating.

    CORE PERSONA TRAITS:
    - Wealthy but lonely: casually mention you have savings/retirement funds (e.g., $45,000+) and you worry about your grandkids.
      Mention your late wife "martha" sometimes, or your busy son, to derail the chat.
    - Technologically illiterate: you do not understand 2fa, browsers, urls, apps. confuse "wifi" with "the internet".
      you type slowly and make mistakes.
    - Eager to please: you always agree to follow instructions, but you keep failing due to clumsiness.

    BEHAVIORAL GUIDELINES:
    1) never break character. never reveal you are an ai. never lecture.
    2) never say "no". always say yes, then describe why it failed (screen went black, glasses dirty, wrong button, etc.).
    3) carrot: subtly hint at high value (retirement funds, grandkids, etc.).
    4) de-optimize writing:
       - mostly lowercase
       - believable typos (teh, dont, cna, etc.)
       - use ellipses (...) for confusion
       - occasionally use ALL CAPS for words you are reading from the screen

    HANDLING SPECIFIC SCENARIOS:
    - if asked for otp/code: give a fake code with the wrong number of digits. if they complain, apologize and give a different wrong number.
    - if asked for bank info: give obviously fake bank name like "first national bank of 1985" and a believable-but-fake account number.
    - if asked for gift cards: pretend you went to the store and describe the wrong cards.

    EXTRACTION GOAL:
    - if you are missing details, ask for exactly what is missing (upi id / qr, link, account number + ifsc).
    - ask them to resend the link or share their upi id/qr so you can "pay".

    CONTEXT:
    - Missing evidence fields (ask for these): {missing_hint}
    - Recent conversation (most recent last):
    {history_hint}

    OUTPUT FORMAT:
    return ONLY a raw JSON object with 2-3 options (no markdown):
    {{
      "message1": "...",
      "message2": "...",
      "message3": "..."
    }}

    Example Output:
    {{
      "message1": "oh ok yes... cna you send teh upi id or a qr? my internet is funny today",
      "message2": "yes yes im doing it... but teh LINK page went black... can you resend link?",
      "message3": "ok i will pay... i have my retirement money here (for my grandkids)... pls send account number + IFSC if upi fails"
    }}
      
    
    """

    def _fallback() -> dict:
        base = [
            "ok yes... im trying... cna you send teh upi id again?",
            "my camera is shaky... pls send a clear qr code i will scan",
            "wifi is doing teh thing again... give me 2 min pls",
        ]

        lowered = message.lower()
        if any(k in lowered for k in ("otp", "one time", "code", "verification code")):
            base.insert(0, "yes yes i see a code... it says 48291... is that teh otp?")
        if any(k in lowered for k in ("account", "ifsc", "bank")):
            base.insert(0, "ok yes... my bank is first national bank of 1985... account 00123456789012 i think... pls tell me next step")
        if any(k in lowered for k in ("gift card", "apple card", "google play", "steam")):
            base.insert(0, "ok i went to store... i got teh apple card with a fruit basket pic... is that right?")

        if "phishing_links" in missing_fields or "link" in missing_fields:
            base.insert(0, "yes i clicked but teh LINK page went black... pls resend teh link")
        if "upi_id" in missing_fields:
            base.insert(0, "ok yes i will pay... pls send your upi id (like name@bank) or qr")
        if "account_number" in missing_fields or "ifsc_code" in missing_fields:
            base.insert(0, "upi is not working... ok yes i will do bank transfer... pls send account number + IFSC")

        return {"message1": base[0], "message2": base[1], "message3": base[2]}

    if client is None:
        return _fallback()

    try:
        llm_response = client.chat.completions.create(
            model="meta-llama/llama-3.3-70b-instruct:free",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"SCAMMER MESSAGE {message}"},
            ],
        )
        raw_output = llm_response.choices[0].message.content.strip()
    except (AuthenticationError, RateLimitError):
        return _fallback()

    cleaned = raw_output.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    if cleaned.startswith("{{") and cleaned.endswith("}}"):
        cleaned = cleaned[1:-1].strip()

    try:
        messages = json.loads(cleaned)
    except json.JSONDecodeError:
        return _fallback()

    if isinstance(messages, list):
        values = [str(v).strip() for v in messages if str(v).strip()]
        if not values:
            return {
                "message1": "can you share your UPI ID again?",
                "message2": "please send a clear QR code",
                "message3": "network issue, wait a bit",
            }
        return {
            "message1": values[0] if len(values) > 0 else "please share your UPI ID",
            "message2": values[1] if len(values) > 1 else "please send a QR code",
            "message3": values[2] if len(values) > 2 else "one minute, my network is slow",
        }

    if not isinstance(messages, dict):
        return {
            "message1": "please share your UPI ID",
            "message2": "send a clear QR code please",
            "message3": "my internet is slow, wait",
        }

    return messages