from openai import OpenAI
from pydantic import BaseModel
import json
import os 
from dotenv import load_dotenv
class ScamRequest(BaseModel):
    message: str

def is_scam(message:str) -> bool:
    load_dotenv()
    client = OpenAI(
        api_key = os.getenv("api_key"),
        base_url="https://openrouter.ai/api/v1"
    )

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
    
    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[{"role":"system" , "content":f"{SYSTEM_PROMPT}"},
                  {
                      "role":"user" , "content" : f"{message}"
                  }
        ]
    )

    raw_output = response.choices[0].message.content.strip()

    try :
        result = json.loads(raw_output)
    except json.JSONDecodeError:
        raise ValueError("Wrong JSON format from LLM")
    
    return result["is_scam"]

message = """Hi,
Your loan application of Rs.5,00,000 is on hold due to pending KYC.
Ref ID: Tuy09
Submit verification details to move forward.
Reply STOP to opt out.
3:34 PM"""
print(is_scam(message))
