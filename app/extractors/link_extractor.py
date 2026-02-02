from typing import Dict, List

from app.utils.regex_utils import extract_urls


def extract_phishing_links(message: str) -> Dict[str, List[str]]:
    links = extract_urls(message)
    if not links:
        return {"phishing_links": []}
    return {"phishing_links": links}
