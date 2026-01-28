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
      "urgent", "account blocked", "verify now",
      "send money", "upi", "otp", "kyc"
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

print(is_scam("Sir your account has been blocked , send me money to this number"))
