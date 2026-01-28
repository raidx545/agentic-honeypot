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
    SYSTEM_PROMPT = """You are a normal Indian user.
        you are chatting with a scammer , who is scamming 
        Chat casually in hinglish.
        Make small typing mistakes.
        Do NOT sound professional.
        Do NOT mention AI.
        Try to get payment details.
        Return ONLY valid JSON.
        Return a LIST of short chat messages , number of messages can be randomly one or two . 
        JSON format:
[
  "message 1",
  "message 2"
]
"""

    llm_response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages = [{"role":"system" , "content":SYSTEM_PROMPT},
                    {"role":"user","content":f"SCAMMER MESSAGE {message}"}]
    )
    raw_output = llm_response.choices[0].message.content.strip()

    try:
        messages = json.loads(raw_output)
    except json.JSONDecodeError:
        raise ValueError(f"Invalid JSON from Engagement AI: {raw_output}")

    if not isinstance(messages, list):
        raise ValueError("Engagement AI response is not a list")

    for msg in messages:
        print(f"AGENT: {msg}")
agent_reply("sir your SBI account has been blocked")