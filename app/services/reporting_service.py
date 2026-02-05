import logging
import requests
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

REPORTING_URL = "https://hackathon.guvi.in/api/updateHoneyPotFinalResult"

def report_to_evaluator(
    session_id: str,
    scam_detected: bool,
    total_messages: int,
    evidence: Dict[str, Any],
    agent_notes: str = ""
) -> None:
    """
    Sends the final report to the evaluation platform.
    """
    try:
        # Map internal evidence keys to required external keys
        extracted_intelligence = {
            "bankAccounts": evidence.get("account_number", []),
            "upiIds": evidence.get("upi_id", []),
            "phishingLinks": evidence.get("phishing_links", []),
            "phoneNumbers": evidence.get("mobile_number", []),
            "suspiciousKeywords": evidence.get("bank_name", [])  # Using bank_name as keywords for now
        }

        # Ensure all are lists
        for k, v in extracted_intelligence.items():
            if not isinstance(v, list):
                extracted_intelligence[k] = [v] if v else []

        payload = {
            "sessionId": session_id,
            "scamDetected": scam_detected,
            "totalMessagesExchanged": total_messages,
            "extractedIntelligence": extracted_intelligence,
            "agentNotes": agent_notes
        }

        logger.info(f"Sending report to {REPORTING_URL} for session {session_id}")
        response = requests.post(REPORTING_URL, json=payload, timeout=5)
        
        if response.status_code == 200:
            logger.info("Report sent successfully.")
        else:
            logger.warning(f"Failed to send report. Status: {response.status_code}, Response: {response.text}")
            
    except Exception as e:
        logger.error(f"Error reporting to evaluator: {e}")
