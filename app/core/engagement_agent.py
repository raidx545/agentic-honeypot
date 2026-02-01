from openai import OpenAI
from pydantic import BaseModel
import os 
from dotenv import load_dotenv
import json
class agent(BaseModel):
    message: str


#letting that scam_detector detects message as True
def agent_reply(message:str):

    load_dotenv()

    client = OpenAI(
        api_key = os.getenv("api_key"),
        base_url="https://openrouter.ai/api/v1"
    )

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

    llm_response = client.chat.completions.create(
        model="deepseek/deepseek-v3.2",
        messages = [{"role":"system" , "content":SYSTEM_PROMPT},
                    {"role":"user","content":f"SCAMMER MESSAGE {message}"}]
    )
    raw_output = llm_response.choices[0].message.content.strip()

    # print(raw_output)
    try:
        messages = json.loads(raw_output)
    except json.JSONDecodeError:
        raise ValueError(f"Invalid JSON from Engagement AI: {raw_output}")

    for i in messages:
        print(messages[i])

agent_reply("Hello sir! Congratulations! You have won Rs. 50,00,000 in our lucky draw! Please share your bank details to receive the amount.")