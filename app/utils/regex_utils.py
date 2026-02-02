import re
from typing import List


_URL_REGEX = re.compile(
    r"""\b((?:https?://|www\.)[^\s<>\]\)\}]+)""",
    re.IGNORECASE,
)
_EMAIL_REGEX = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_UPI_REGEX = re.compile(r"\b[a-z0-9.\-_]{2,}@[a-z0-9]{2,}\b", re.IGNORECASE)
_IFSC_REGEX = re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b", re.IGNORECASE)
_INDIAN_MOBILE_REGEX = re.compile(r"\b(?:\+?91[-\s]?)?[6-9]\d{9}\b")


def _deobfuscate(text: str) -> str:
    return (
        text.replace("[.]", ".")
        .replace("(.)", ".")
        .replace("hxxp://", "http://")
        .replace("hxxps://", "https://")
    )


def extract_urls(text: str) -> List[str]:
    cleaned = _deobfuscate(text)
    urls = [m.group(1) for m in _URL_REGEX.finditer(cleaned)]
    normalized = []
    for u in urls:
        if u.lower().startswith("www."):
            u = "https://" + u
        normalized.append(u)
    return sorted(set(normalized))


def extract_emails(text: str) -> List[str]:
    cleaned = _deobfuscate(text)
    return sorted(set(_EMAIL_REGEX.findall(cleaned)))


def extract_upi_ids(text: str) -> List[str]:
    cleaned = _deobfuscate(text)
    return sorted(set(m.group(0) for m in _UPI_REGEX.finditer(cleaned)))


def extract_ifsc_codes(text: str) -> List[str]:
    cleaned = _deobfuscate(text)
    return sorted(set(m.group(0).upper() for m in _IFSC_REGEX.finditer(cleaned)))


def extract_mobile_numbers(text: str) -> List[str]:
    cleaned = _deobfuscate(text)
    matches = [m.group(0) for m in _INDIAN_MOBILE_REGEX.finditer(cleaned)]
    normalized = []
    for m in matches:
        digits = re.sub(r"\D", "", m)
        if digits.startswith("91") and len(digits) == 12:
            digits = digits[2:]
        if len(digits) == 10:
            normalized.append(digits)
    return sorted(set(normalized))


def extract_account_numbers(text: str) -> List[str]:
    cleaned = _deobfuscate(text)
    candidates = re.findall(r"\b\d{9,18}\b", cleaned)

    mobile_set = set(extract_mobile_numbers(cleaned))

    filtered = []
    for c in candidates:
        digits = re.sub(r"\D", "", c)
        if digits in mobile_set:
            continue
        if len(digits) == 10:
            continue
        filtered.append(digits)

    return sorted(set(filtered))
