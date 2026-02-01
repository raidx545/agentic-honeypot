from openai import OpenAI
message = """Dear Customer,

We have detected unauthorized activity on your bank account.
For your safety, your account has been temporarily restricted.

Details:
6395897431


To restore full access, verify your KYC immediately:
👉 https://sbi-verify-kyc-secure[.]com

If verification is not completed within 20 minutes,
your account will be permanently blocked.

📧 supportsbi@gamil[.]com"""
client = OpenAI(
    api_key="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",
    base_url="https://openrouter.ai/api/v1"
)
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
llm_response = client.chat.completions.create(
    model="deepseek/deepseek-v3.2",
    messages=[{"role":"system","content":SYSTEM_PROMPT},{"role":"user","content":message}]
)

raw_output=llm_response.choices[0].message.content

print(raw_output)
