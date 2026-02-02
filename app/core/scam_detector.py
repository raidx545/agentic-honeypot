import json

from openai import AuthenticationError

from app.core.llm_client import get_openrouter_client
from app.utils.regex_utils import extract_upi_ids, extract_urls


def is_scam(message: str) -> bool:
    SCAM_KEYWORDS = [
        # Urgency & Fear
        "urgent", "account blocked", "suspended", "deactivated", "frozen", 
        "unauthorized", "immediate action", "expire", "lapse", "debit alert",

        # Verification & Authority
        "verify now", "kyc", "update pan", "link aadhaar", "re-activate", 
        "credentials", "customer care", "support team", "bank manager",

        # Money & Technical
        "send money", "upi", "otp", "pin", "cvv", "scan qr", "refund", 
        "cashback", "revert transaction", "anydesk", "screen share",

        # Lures & Rewards
        "won", "winning", "prize", "lucky draw", "lottery", "redeem points", 
        "credit limit", "bonus", "investment", "double money"
    ]

    FALLBACK_EXTRA_KEYWORDS = [
        "pay",
        "payment",
        "transfer",
        "send",
        "upi://",
        "bank account",
    ]
    SYSTEM_PROMPT = f"""You are a scam detection system.
    Rules:
    - If the message contains ANY of these keywords:
    {", ".join(SCAM_KEYWORDS)} 
    classify it as a scam.
    - Otherwise classify it as non-scam.
    Respond ONLY in valid JSON. 
    No extra text.
    JSON format:
    {{
    "is_scam": true or false,
    "confidence": number between 0 and 1
    }}
"""
    
    try:
        client = get_openrouter_client()
        response = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {"role": "system", "content": f"{SYSTEM_PROMPT}"},
                {"role": "user", "content": f"{message}"},
            ],
        )
        raw_output = response.choices[0].message.content.strip()

        try:
            result = json.loads(raw_output)
        except json.JSONDecodeError as e:
            raise ValueError(f"Wrong JSON format from LLM: {raw_output}") from e

        return bool(result.get("is_scam", False))
    except (AuthenticationError, ValueError):
        lowered = message.lower()
        if any(k in lowered for k in SCAM_KEYWORDS):
            return True
        if any(k in lowered for k in FALLBACK_EXTRA_KEYWORDS):
            return True
        if extract_upi_ids(message):
            return True
        if extract_urls(message):
            return True
        return False
