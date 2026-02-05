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
from app.extractors.qr_extractor import decode_qr_from_image_path
import urllib.request
import tempfile
import os
import uuid


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

    # --- QR Code Extraction (from image URLs) ---
    # If we found links that look like images, try to download and scan them.
    # We only try this if we have links.
    image_extensions = (".jpg", ".jpeg", ".png", ".webp")
    for link in evidence["phishing_links"]:
        if link.lower().endswith(image_extensions):
            try:
                # Basic download with urllib
                # Create a temp file
                ext = link.split(".")[-1]
                tmp_name = f"temp_qr_{uuid.uuid4()}.{ext}"
                
                # Download (with timeout)
                # User-Agent header often helps avoids 403 blocks from some CDNs
                req = urllib.request.Request(
                    link, 
                    headers={'User-Agent': 'Mozilla/5.0'}
                )
                with urllib.request.urlopen(req, timeout=10) as response:
                    data = response.read()
                    with open(tmp_name, "wb") as f:
                        f.write(data)
                
                # Scan
                decoded = decode_qr_from_image_path(tmp_name)
                
                # Clean up
                if os.path.exists(tmp_name):
                    os.remove(tmp_name)

                if decoded:
                    # If we found text in QR, run regex on THAT text too!
                    # This finds hidden UPI IDs inside the QR payload.
                    evidence["upi_id"].extend(extract_upi_ids(decoded))
                    evidence["phishing_links"].extend(extract_urls(decoded))
                    # Also store the raw QR data just in case
                    evidence["qr_data"] = decoded
                    
            except Exception as e:
                # print(f"Failed to scan QR from {link}: {e}")
                pass

    # Deduplicate lists
    evidence["upi_id"] = sorted(list(set(evidence["upi_id"])))
    evidence["phishing_links"] = sorted(list(set(evidence["phishing_links"])))

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
