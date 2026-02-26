import requests
import json

BASE_URL = "http://127.0.0.1:5000"

def test_fixes():
    session = requests.Session()
    session_id = "test_fixes_session"

    # Step 1: Login
    print("[1] Logging in...")
    login_data = {"username": "demo_user", "password": "password123"}
    session.post(f"{BASE_URL}/auth/login", data=login_data)

    # Step 2: Search for trains to Mumbai to Delhi (this populates trains_available)
    print("[2] Searching Mumbai to Delhi...")
    cmd_search = {"command": "trains from Mumbai to Delhi", "session_id": session_id}
    res_search = session.post(f"{BASE_URL}/voice/process-command", json=cmd_search).json()
    print(f"Bot Search Speak: {res_search['speak'][:50]}...")

    # Step 3: Test Booking Selection Loop Fix (Fix 1)
    print("[3] Testing 'Book train 1'...")
    cmd_book = {"command": "book train 1", "session_id": session_id}
    res_book = session.post(f"{BASE_URL}/voice/process-command", json=cmd_book).json()
    print(f"Bot Book Speak: {res_book['speak']}")
    
    if "What is your full name" in res_book['speak']:
        print("SUCCESS: Booking selection handled correctly (Fix 1).")
    else:
        print("FAILED: Booking selection failed.")

    # Step 4: Test Cancellation (Fix 2)
    print("[4] Testing 'Cancel my booking'...")
    cmd_cancel = {"command": "cancel my booking", "session_id": session_id}
    res_cancel = session.post(f"{BASE_URL}/voice/process-command", json=cmd_cancel).json()
    print(f"Bot Cancel Speak: {res_cancel['speak']}")
    
    if "please tell me your 10 digit PNR" in res_cancel['speak'].lower():
        print("SUCCESS: Cancellation prompt triggered (Fix 2).")
    else:
        print("FAILED: Cancellation prompt failed.")

    # Step 5: Test Coimbatore (Fix 4)
    print("[5] Searching to Coimbatore...")
    cmd_cbe = {"command": "trains to coimbatore", "session_id": session_id}
    # This might fail on search because we don't have Kovai/CBE in DB, but it should trigger incomplete_search or search_trains intent
    res_cbe = session.post(f"{BASE_URL}/voice/process-command", json=cmd_cbe).json()
    print(f"Bot Coimbatore Speak: {res_cbe['speak']}")
    
    # Check if Coimbatore was recognized as a location
    if "Where are you traveling from" in res_cbe['speak'] or "from Coimbatore" in res_cbe['speak'] or "to Coimbatore" in res_cbe['speak']:
         print("SUCCESS: Coimbatore recognized (Fix 4).")
    else:
         print("FAILED: Coimbatore not recognized.")

if __name__ == "__main__":
    test_fixes()
