from typing import Dict, List

from app.utils.regex_utils import extract_upi_ids


def extract_upi(message: str) -> Dict[str, List[str]]:
    upis = extract_upi_ids(message)
    if not upis:
        return {"upi_id": []}
    return {"upi_id": upis}
