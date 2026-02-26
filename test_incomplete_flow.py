import requests
import json

BASE_URL = "http://127.0.0.1:5000"

def test_incomplete_flow():
    session = requests.Session()
    session_id = "test_vui_flow"

    # Step 1: Login
    print("[1] Logging in...")
    login_data = {"username": "demo_user", "password": "password123"}
    session.post(f"{BASE_URL}/auth/login", data=login_data)

    # Step 2: Incomplete command
    print("[2] Sending: 'Book a ticket'")
    cmd1 = {"command": "book a ticket", "session_id": session_id}
    res1 = session.post(f"{BASE_URL}/voice/process-command", json=cmd1).json()
    print(f"Bot: {res1['speak']}")
    
    if "Where are you traveling from" in res1['speak']:
        print("SUCCESS: Incomplete search prompted correctly.")
    else:
        print("FAILED: Unexpected response.")

    # Step 3: Follow-up with locations
    print("[3] Sending: 'From Mumbai to Delhi tomorrow'")
    cmd2 = {"command": "from Mumbai to Delhi tomorrow", "session_id": session_id}
    res2 = session.post(f"{BASE_URL}/voice/process-command", json=cmd2).json()
    
    # We avoid printing the whole response because of potential Unicode issues in terminal
    speak_text = res2['speak']
    # Removing non-ASCII for terminal display safety if needed, but let's just check contents
    print(f"Bot Speak length: {len(speak_text)}")
    
    if "I found" in speak_text and "seats available" in speak_text:
        print("SUCCESS: Search triggered after follow-up with seats.")
        # Check if seats and price are there
        if "rupees" in speak_text:
            print("SUCCESS: Price mentioned in VUI format (rupees).")
    else:
        print("FAILED: Search or seats missing in response.")
        print(f"Actual Speak: {speak_text}")

if __name__ == "__main__":
    test_incomplete_flow()
