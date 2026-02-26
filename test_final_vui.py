import requests
import json

BASE_URL = "http://127.0.0.1:5000"

def test_final_vui():
    session = requests.Session()
    session_id = f"final_test_{id(session)}"

    # Step 1: Login
    print("[1] Logging in...")
    login_data = {"username": "demo_user", "password": "password123"}
    session.post(f"{BASE_URL}/auth/login", data=login_data)

    # Step 2: Test Search with Delhi (Word boundary fix)
    print("[2] Searching Mumbai to Delhi...")
    cmd_search = {"command": "trains from Mumbai to Delhi", "session_id": session_id}
    res_search = session.post(f"{BASE_URL}/voice/process-command", json=cmd_search).json()
    print(f"Bot: {res_search['speak']}")
    if "I found" in res_search['speak'] and "trains" in res_search['speak'].lower():
        print("SUCCESS: Delhi search identified correctly (not as greeting).")

    # Step 3: Test Booking Selection (Fix 1)
    print("[3] Testing 'Book the first one'...")
    cmd_book = {"command": "book the first one", "session_id": session_id}
    res_book = session.post(f"{BASE_URL}/voice/process-command", json=cmd_book).json()
    print(f"Bot: {res_book['speak']}")
    if "What is your full name" in res_book['speak']:
        print("SUCCESS: Booking selection loop fixed.")

    # Step 4: Test Cancellation overriding flow (Fix 2 & prioritisation)
    print("[4] Testing 'Cancel my booking' while in flow...")
    cmd_cancel = {"command": "cancel my booking", "session_id": session_id}
    res_cancel = session.post(f"{BASE_URL}/voice/process-command", json=cmd_cancel).json()
    print(f"Bot: {res_cancel['speak']}")
    if "pnr number" in res_cancel['speak'].lower():
        print("SUCCESS: Cancellation intent prioritized over active booking flow.")

    # Step 5: Test Coimbatore and partial search
    print("[5] Searching 'trains to Coimbatore'...")
    cmd_cbe = {"command": "trains to Coimbatore", "session_id": session_id}
    res_cbe = session.post(f"{BASE_URL}/voice/process-command", json=cmd_cbe).json()
    print(f"Bot: {res_cbe['speak']}")
    if "Where are you traveling from" in res_cbe['speak']:
        print("SUCCESS: Coimbatore partial search triggered incomplete prompt.")

if __name__ == "__main__":
    test_final_vui()
