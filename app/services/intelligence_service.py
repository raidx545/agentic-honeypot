from typing import Any, Dict

from app.extractors.bank_extractor import llm_extract
from app.utils.regex_utils import (
    extract_account_numbers,
    extract_emails,
    extract_ifsc_codes,
    extract_mobile_numbers,
    extract_upi_ids,
    extract_urls,
)


_BANK_KEYWORDS = [
    "sbi",
    "state bank",
    "hdfc",
    "icici",
    "axis",
    "kotak",
    "pnb",
    "punjab national",
    "canara",
    "bob",
    "bank of baroda",
    "union bank",
    "indusind",
]


def _guess_bank_name(message: str) -> str | None:
    lower = message.lower()
    for k in _BANK_KEYWORDS:
        if k in lower:
            return k.upper() if len(k) <= 5 else k.title()
    return None


def extract_evidence(message: str, *, use_llm_fallback: bool = True) -> Dict[str, Any]:
    evidence: Dict[str, Any] = {
        "upi_id": extract_upi_ids(message),
        "ifsc_code": extract_ifsc_codes(message),
        "account_number": extract_account_numbers(message),
        "mobile_number": extract_mobile_numbers(message),
        "email": extract_emails(message),
        "phishing_links": extract_urls(message),
    }

    bank_name = _guess_bank_name(message)
    if bank_name:
        evidence["bank_name"] = bank_name

    if use_llm_fallback:
        has_any = any(bool(v) for v in evidence.values() if v is not None)
        if not has_any:
            extracted = llm_extract(message)
            if isinstance(extracted, dict):
                for k, v in extracted.items():
                    if v is None:
                        continue
                    if isinstance(v, list) and not v:
                        continue
                    evidence[k] = v

    compact: Dict[str, Any] = {}
    for k, v in evidence.items():
        if v is None:
            continue
        if isinstance(v, list) and not v:
            continue
        compact[k] = v

    return compact
