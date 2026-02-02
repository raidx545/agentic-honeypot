import os

from dotenv import load_dotenv
from openai import OpenAI


def get_openrouter_client() -> OpenAI:
    load_dotenv()
    api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("api_key")
    if not api_key:
        raise ValueError(
            "Missing OpenRouter API key. Set 'OPENROUTER_API_KEY' (or legacy 'api_key') in your .env file."
        )

    return OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")
