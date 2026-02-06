import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.api.routes import app

# Setup client
# We need to ensure the environment variable for API Key is set or mocked.
# The app loads dotenv, but for tests we can override or rely on .env
# Let's read .env manually to be sure we have a valid key for the headers
from dotenv import load_dotenv
load_dotenv()

API_KEY = os.getenv("HONEYPOT_API_KEY", "dev-key")
HEADERS = {"X-API-Key": API_KEY}

client = TestClient(app)

def test_root_endpoint_variations():
    print(f"Testing with API Key: {API_KEY}")
    
    # 1. Standard "message" payload
    payload1 = {"message": "hello scammer"}
    resp1 = client.post("/", json=payload1, headers=HEADERS)
    print(f"POST / (message): {resp1.status_code}")
    if resp1.status_code != 200:
        print(f"ERROR: {resp1.text}")
        sys.exit(1)
    
    # 2. "text" payload
    payload2 = {"text": "hello scammer text"}
    resp2 = client.post("/", json=payload2, headers=HEADERS)
    print(f"POST / (text): {resp2.status_code}")
    assert resp2.status_code == 200

    # 3. "input" payload
    payload3 = {"input": "hello scammer input"}
    resp3 = client.post("/", json=payload3, headers=HEADERS)
    print(f"POST / (input): {resp3.status_code}")
    assert resp3.status_code == 200

    # 4. Empty payload (defaults)
    resp4 = client.post("/", json={}, headers=HEADERS)
    print(f"POST / (empty): {resp4.status_code}")
    assert resp4.status_code == 200

    # 5. Handoff flag check
    payload5 = {"message": "scam likely", "handoff": True}
    resp5 = client.post("/", json=payload5, headers=HEADERS)
    print(f"POST / (handoff=True): {resp5.status_code}")
    assert resp5.status_code == 200
    data = resp5.json()
    if "agent_message" not in data:
         print("WARNING: agent_message missing in response structure")

    print("\nSUCCESS: Root endpoint accepts all expected payload variations.")

if __name__ == "__main__":
    test_root_endpoint_variations()
