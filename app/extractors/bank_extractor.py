import json

from openai import AuthenticationError
from openai import RateLimitError

from app.core.llm_client import get_openrouter_client


def llm_extract(message: str) -> dict:
    client = get_openrouter_client()

    SYSTEM_PROMPT = """You are an information extraction engine.

Your task is to extract all identifiable structured data present in the given message.
Extract ONLY what is explicitly present. Do NOT guess, infer, or hallucinate missing values.

Identify and extract the following fields when available:
- person_name
- bank_name
- account_number
- ifsc_code
- upi_id
- mobile_number
- email
- phishing_links (URLs, shortened links, suspicious domains)

Output rules:
- Return the result in STRICT JSON format.
- If a field is not present, leave it , don't add into output .
- Do not add any explanation, comments, or extra text.
- Preserve original formatting of extracted values.
- phishing_links must be an array (empty array if none found).

Output JSON schema:

{
  "person_name": null,
  "bank_name": null,
  "account_number": null,
  "ifsc_code": null,
  "upi_id": null,
  "mobile_number": null,
  "email": null,
  "phishing_links": []
}

"""

    try:
        llm_response = client.chat.completions.create(
            model="meta-llama/llama-3.3-70b-instruct:free",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": message},
            ],
        )
        raw_output = llm_response.choices[0].message.content.strip()
    except Exception:
        # Fallback for any LLM error (quota, auth, connection, etc.)
        return {}
    try:
        parsed = json.loads(raw_output)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON from extractor LLM: {raw_output}") from e

    if not isinstance(parsed, dict):
        raise ValueError(f"Extractor must return a JSON object, got: {type(parsed)}")

    return parsed
