
import urllib.request
import urllib.error
import json
import time

BASE_URL = "https://agentic-honeypot-9tju.onrender.com"
API_KEY = "my-evaluator-key-123"

def make_request(endpoint, data=None):
    url = f"{BASE_URL}{endpoint}"
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY,
        "User-Agent": "HoneypotEvaluator/1.0"
    }
    
    try:
        if data is not None:
            json_data = json.dumps(data).encode("utf-8")
            req = urllib.request.Request(url, data=json_data, headers=headers, method="POST")
        else:
            req = urllib.request.Request(url, headers=headers, method="GET")
            
        with urllib.request.urlopen(req) as response:
            status = response.getcode()
            body = response.read().decode("utf-8")
            return status, json.loads(body)
            
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.reason}")
        try:
            print(e.read().decode("utf-8"))
        except:
            pass
        return e.code, None
    except Exception as e:
        print(f"Error: {e}")
        return 0, None

def run_test():
    print(f"Testing API at {BASE_URL} with key {API_KEY}")
    
    # 1. Health Check
    print("\n[1/3] Checking Health...")
    status, res = make_request("/health")
    if status == 200:
        print("✅ Health OK:", res)
    else:
        print("❌ Health Check Failed")
        # Don't stop, try others just in case

    # 2. Scan a scam message
    print("\n[2/3] Testing Scam Detection (/scan)...")
    payload = {
        "input": "Your account is blocked. Click http://scam-link.net to verify. Pay 500 to upi@fakebank",
        "handoff": True
    }
    status, res = make_request("/scan", payload)
    
    if status == 200:
        print("✅ Response received:")
        print(json.dumps(res, indent=2))
        
        if res.get("scam_detected"):
            print("   -> scam_detected: OK")
        else:
            print("   -> ⚠️  scam_detected is False")
    else:
        print("❌ Scan Failed")
        
    # 3. Check /message endpoint
    print("\n[3/3] Testing /message endpoint...")
    # Create conversation first
    status, conv = make_request("/conversations", {})
    if status == 200:
        cid = conv.get("conversation_id")
        print(f"   Created Conversation: {cid}")
        
        msg_payload = {
            "conversation_id": cid,
            "message": "Verify immediately at http://bad-site.com",
            "handoff": True
        }
        status, msg_res = make_request("/message", msg_payload)
        if status == 200:
            print("✅ Message Sent:")
            print(json.dumps(msg_res, indent=2))
        else:
            print("❌ Message Send Failed")

if __name__ == "__main__":
    run_test()
