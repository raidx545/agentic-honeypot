
# Agentic AI Honeypot System

An agentic “honeypot” chat system for engaging suspected scammers with a realistic human persona, extracting key evidence (UPI IDs, bank details, phishing links), and writing it to a JSON file for reporting.

## Features

- **Scam detection**
  - Uses an LLM via OpenRouter when configured.
  - Automatically falls back to **keyword-based detection** if the API key is missing/invalid.
- **User handoff**
  - Once a scam is detected, you can type `handoff` to transfer control to the agent.
- **Engagement agent (persona)**
  - Generates naive, non-tech-savvy Hinglish responses to keep the scammer engaged.
  - Falls back to safe canned responses if the LLM is unavailable.
- **Evidence extraction**
  - Extracts:
    - `upi_id`
    - `account_number`
    - `ifsc_code`
    - `mobile_number`
    - `email`
    - `phishing_links`
    - `bank_name` (keyword match)
  - Regex-first extraction with optional LLM fallback.
- **JSON evidence output**
  - Writes/updates `evidence.json` with conversation history and extracted evidence.

## Project Structure

- `app/main.py` — interactive CLI runner
- `app/core/scam_detector.py` — scam detection (LLM + fallback)
- `app/core/engagement_agent.py` — persona engagement agent (LLM + fallback)
- `app/core/conversation_manager.py` — conversation state + evidence merge
- `app/services/intelligence_service.py` — extraction pipeline
- `app/utils/regex_utils.py` — regex extractors (UPI/links/IFSC/etc.)
- `app/storage/repository.py` — JSON persistence (`evidence.json`)

## Requirements

- Python 3.10+
- (Optional) OpenRouter API key for LLM features

Dependencies are listed in `requirements.txt`.

## Setup

1. Create and activate a virtual environment (recommended).
2. Install dependencies:

```bash
pip3 install -r requirements.txt
```

3. Create a `.env` file in the project root (recommended):

```bash
OPENROUTER_API_KEY=your_openrouter_key_here
```

Notes:
- The code also supports legacy key name `api_key`, but `OPENROUTER_API_KEY` is preferred.
- If you do not set a key (or the key is invalid), the project still runs using fallback logic.

## Run (CLI Demo)

Start the honeypot CLI:

```bash
python3 -m app.main
```

### Commands

- `handoff` — enable agent takeover
- `exit` — stop the program

### Demo Flow (Recommended)

1. Paste a scammer message.
2. If `scam_detector: SCAM detected` appears, type `handoff` on a new line.
3. Continue pasting scammer messages.
4. The agent replies as `agent>` and evidence is saved continuously.

## Evidence Output (`evidence.json`)

The system writes a single file `evidence.json` at the project root. It stores a list of conversations, each containing:

- `conversation_id`
- `scam_detected`
- `handoff_active`
- `history`: list of `{ role, content, ts }`
- `evidence`: extracted structured fields (UPI, IFSC, links, etc.)

Example (simplified):

```json
{
  "conversations": [
    {
      "conversation_id": "...",
      "scam_detected": true,
      "handoff_active": true,
      "history": [
        {"role": "scammer", "content": "...", "ts": "..."},
        {"role": "agent", "content": "...", "ts": "..."}
      ],
      "evidence": {
        "upi_id": ["raz@okaxis"],
        "ifsc_code": ["SBIN0004598"],
        "phishing_links": ["http://sbi-secure-verify.online"]
      }
    }
  ]
}
```

## Notes / Troubleshooting

- If you see `Missing OpenRouter API key`, add `OPENROUTER_API_KEY` to `.env`.
- If the LLM responds with slightly invalid JSON, the agent attempts to clean it. If it still fails, it uses fallback replies.

## Disclaimer

Use only for defensive/security research, education, and lawful reporting. Do not use for harassment or unlawful activity.

