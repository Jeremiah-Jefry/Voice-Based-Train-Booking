"""
Voice Assistant for Train Booking
=================================
Uses NLU (keyword matching) + Dialogue Manager + Static Replies
"""

from flask import render_template, request, jsonify, redirect, url_for
from flask_login import login_required, current_user
from app.voice import bp
from app.database import search_trains, find_stations, get_booking_by_pnr, get_user_bookings, create_booking
from datetime import datetime
import re

# ============================================================================
# STATIC REPLIES - All responses defined here for consistency
# ============================================================================

REPLIES = {
    # Greetings
    'greeting': [
        "Hello! I'm your train booking assistant. Say 'search trains from Mumbai to Delhi' to find trains.",
        "Hi there! Ready to book your train? Tell me your source and destination.",
        "Welcome! I can help you search trains, book tickets, or check PNR status."
    ],
    
    # Help
    'help': """I can help you with:

🚂 **Search Trains**: "trains from Mumbai to Delhi"
🎫 **Book Ticket**: After search, say "book 1" or "book first"
📋 **Check PNR**: "check PNR 1234567890"
📜 **My Bookings**: "show my bookings"

Just speak naturally!""",
    
    # Search
    'search_no_source': "Where do you want to travel FROM? Say the city name.",
    'search_no_dest': "Where do you want to travel TO? Say the destination city.",
    'search_not_found_source': "I couldn't find that source city. Try: Mumbai, Delhi, Bangalore, Chennai, Kolkata, Pune.",
    'search_not_found_dest': "I couldn't find that destination city. Try: Mumbai, Delhi, Bangalore, Chennai, Kolkata, Pune.", 
    'search_no_trains': "No trains found for this route. Try a different route.",
    'search_found': "Found {count} trains from {source} to {dest}! Say 'book 1' to book the first train.",
    
    # Booking - Start
    'book_no_trains': "Please search for trains first. Say 'trains from Mumbai to Delhi'.",
    'book_invalid_number': "Please say which train to book: 'book 1', 'book 2', etc.",
    'book_started': "Booking {train_name}. What is your full name?",
    
    # Booking - Steps
    'ask_name': "What is your full name?",
    'ask_age': "What is your age?",
    'ask_gender': "What is your gender? Say male, female, or other.",
    'ask_phone': "What is your 10-digit phone number?",
    'ask_class': "Which class? Say: Sleeper, AC 3, AC 2, or First Class.",
    'ask_confirm': "Please confirm: {name}, {age} years, {gender}, {phone}, {travel_class} class. Say YES to book or NO to cancel.",
    
    # Booking - Validation errors
    'invalid_name': "Please say your full name clearly.",
    'invalid_age': "Please say a valid age between 1 and 120.",
    'invalid_gender': "Please say: male, female, or other.",
    'invalid_phone': "Please say your 10-digit phone number.",
    'invalid_class': "Please say: Sleeper, AC 3, AC 2, or First Class.",
    
    # Booking - Confirmation
    'booking_success': "Booking confirmed! Your PNR is {pnr}. Seat: {seat}. Amount: ₹{amount}.",
    'booking_failed': "Booking failed. Please try again or use the website.",
    'booking_cancelled': "Booking cancelled. Want to search for another train?",
    
    # PNR
    'pnr_ask': "Please say your 10-digit PNR number.",
    'pnr_not_found': "PNR {pnr} not found. Please check the number.",
    'pnr_found': "PNR {pnr}: {status}. Passenger: {name}. Train: {train}.",
    
    # Booking History
    'history_empty': "You have no bookings yet. Say 'trains from Mumbai to Delhi' to search.",
    'history_found': "You have {count} bookings. Latest: PNR {pnr}.",
    
    # Unknown
    'unknown': "I didn't understand that. Say 'help' for available commands.",
    'error': "Something went wrong. Please try again."
}

# ============================================================================
# KEYWORDS - For intent detection (NLU)
# ============================================================================

KEYWORDS = {
    'greeting': ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening', 'namaste'],
    'help': ['help', 'what can you do', 'commands', 'options', 'guide'],
    'search': ['train', 'trains', 'search', 'find', 'from', 'to', 'travel', 'go', 'going'],
    'book': ['book', 'reserve', 'booking', 'ticket'],
    'pnr': ['pnr', 'status', 'check pnr', 'track'],
    'history': ['my booking', 'my ticket', 'history', 'booked'],
    'confirm_yes': ['yes', 'yeah', 'yep', 'confirm', 'ok', 'okay', 'sure', 'correct', 'right', 'proceed'],
    'confirm_no': ['no', 'nope', 'cancel', 'stop', 'wrong', 'change', 'restart'],
    'numbers': ['1', '2', '3', '4', '5', '6', 'one', 'two', 'three', 'four', 'five', 'six', 'first', 'second', 'third'],
    'gender_male': ['male', 'man', 'boy', 'gent'],
    'gender_female': ['female', 'woman', 'girl', 'lady'],
    'gender_other': ['other'],
    'class_sleeper': ['sleeper', 'sl'],
    'class_ac3': ['ac 3', 'ac3', '3 tier', 'three tier', 'third tier'],
    'class_ac2': ['ac 2', 'ac2', '2 tier', 'two tier', 'second tier'],
    'class_ac1': ['ac 1', 'ac1', '1 tier', 'first class', 'first tier'],
    'class_chair': ['chair', 'cc', 'chair car']
}

# City aliases for better matching
CITY_ALIASES = {
    'mumbai': ['mumbai', 'bombay'],
    'delhi': ['delhi', 'new delhi', 'dilli'],
    'bangalore': ['bangalore', 'bengaluru'],
    'chennai': ['chennai', 'madras'],
    'kolkata': ['kolkata', 'calcutta'],
    'hyderabad': ['hyderabad'],
    'pune': ['pune', 'poona'],
    'jaipur': ['jaipur'],
    'ahmedabad': ['ahmedabad'],
    'lucknow': ['lucknow']
}

# ============================================================================
# SESSION MANAGEMENT
# ============================================================================

SESSIONS = {}

def get_session(session_id, user_id):
    """Get or create user session"""
    if session_id not in SESSIONS:
        SESSIONS[session_id] = {
            'user_id': user_id,
            'state': 'idle',  # idle, searching, booking_name, booking_age, etc.
            'trains': [],
            'booking': {}
        }
    return SESSIONS[session_id]

def clear_booking(sess):
    """Clear booking data from session"""
    sess['state'] = 'idle'
    sess['booking'] = {}

# ============================================================================
# NLU - Natural Language Understanding
# ============================================================================

def detect_intent(text):
    """Detect user intent from text using keyword matching"""
    text = text.lower()
    
    # Check each intent
    for intent, keywords in KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                return intent
    
    return 'unknown'

def extract_cities(text):
    """Extract source and destination cities from text"""
    text = text.lower()
    source = None
    destination = None
    
    # Pattern: "from X to Y"
    match = re.search(r'from\s+(\w+)\s+to\s+(\w+)', text)
    if match:
        source = match.group(1)
        destination = match.group(2)
    else:
        # Pattern: "X to Y"
        match = re.search(r'(\w+)\s+to\s+(\w+)', text)
        if match:
            source = match.group(1)
            destination = match.group(2)
    
    # Validate cities
    if source:
        source = normalize_city(source)
    if destination:
        destination = normalize_city(destination)
    
    return source, destination

def normalize_city(city):
    """Normalize city name using aliases"""
    city = city.lower().strip()
    
    # Check aliases
    for standard, aliases in CITY_ALIASES.items():
        if city in aliases:
            return standard.title()
    
    # Return as-is with title case
    return city.title()

def extract_number(text):
    """Extract a number from text"""
    text = text.lower()
    
    # Direct digits
    match = re.search(r'\b(\d+)\b', text)
    if match:
        return int(match.group(1))
    
    # Word to number
    word_nums = {
        'one': 1, 'first': 1,
        'two': 2, 'second': 2,
        'three': 3, 'third': 3,
        'four': 4, 'fourth': 4,
        'five': 5, 'fifth': 5,
        'six': 6, 'sixth': 6
    }
    
    for word, num in word_nums.items():
        if word in text:
            return num
    
    return None

def extract_age(text):
    """Extract age from text"""
    # Try direct number
    match = re.search(r'\b(\d{1,3})\b', text)
    if match:
        age = int(match.group(1))
        if 1 <= age <= 120:
            return age
    
    # Word numbers for common ages
    age_words = {
        'eighteen': 18, 'nineteen': 19, 'twenty': 20,
        'twenty one': 21, 'twenty two': 22, 'twenty three': 23,
        'twenty four': 24, 'twenty five': 25, 'twenty six': 26,
        'twenty seven': 27, 'twenty eight': 28, 'twenty nine': 29,
        'thirty': 30, 'thirty five': 35, 'forty': 40,
        'forty five': 45, 'fifty': 50, 'sixty': 60
    }
    
    text = text.lower()
    for word, age in age_words.items():
        if word in text:
            return age
    
    return None

def extract_phone(text):
    """Extract 10-digit phone number from text"""
    # Get all digits
    digits = ''.join(re.findall(r'\d', text))
    
    # Also convert word numbers
    word_digits = {
        'zero': '0', 'oh': '0', 'o': '0',
        'one': '1', 'two': '2', 'three': '3',
        'four': '4', 'five': '5', 'six': '6',
        'seven': '7', 'eight': '8', 'nine': '9'
    }
    
    words = text.lower().split()
    for word in words:
        if word in word_digits:
            digits += word_digits[word]
    
    if len(digits) >= 10:
        return digits[:10]
    
    return None

def extract_gender(text):
    """Extract gender from text"""
    text = text.lower()
    
    for kw in KEYWORDS['gender_male']:
        if kw in text:
            return 'Male'
    
    for kw in KEYWORDS['gender_female']:
        if kw in text:
            return 'Female'
    
    for kw in KEYWORDS['gender_other']:
        if kw in text:
            return 'Other'
    
    return None

def extract_class(text):
    """Extract travel class from text"""
    text = text.lower()
    
    for kw in KEYWORDS['class_ac1']:
        if kw in text:
            return 'ac_1'
    
    for kw in KEYWORDS['class_ac2']:
        if kw in text:
            return 'ac_2'
    
    for kw in KEYWORDS['class_ac3']:
        if kw in text:
            return 'ac_3'
    
    for kw in KEYWORDS['class_sleeper']:
        if kw in text:
            return 'sleeper'
    
    for kw in KEYWORDS['class_chair']:
        if kw in text:
            return 'chair_car'
    
    # Default if just "ac" mentioned
    if 'ac' in text:
        return 'ac_3'
    
    return None

def extract_pnr(text):
    """Extract 10-digit PNR from text"""
    match = re.search(r'\b(\d{10})\b', text)
    if match:
        return match.group(1)
    return None

def has_confirm_yes(text):
    """Check if user is confirming"""
    text = text.lower()
    for kw in KEYWORDS['confirm_yes']:
        if kw in text:
            return True
    return False

def has_confirm_no(text):
    """Check if user is cancelling"""
    text = text.lower()
    for kw in KEYWORDS['confirm_no']:
        if kw in text:
            return True
    return False

# ============================================================================
# DIALOGUE MANAGER - Handles conversation flow
# ============================================================================

def process_dialogue(text, sess, user):
    """
    Main dialogue manager - routes based on current state
    Returns: dict with 'response', 'speak', optionally 'action' and 'data'
    """
    state = sess.get('state', 'idle')
    
    print(f"[DM] State: {state}, Input: '{text}'")
    
    # STATE-BASED ROUTING
    if state == 'booking_name':
        return handle_booking_name(text, sess)
    
    elif state == 'booking_age':
        return handle_booking_age(text, sess)
    
    elif state == 'booking_gender':
        return handle_booking_gender(text, sess)
    
    elif state == 'booking_phone':
        return handle_booking_phone(text, sess)
    
    elif state == 'booking_class':
        return handle_booking_class(text, sess)
    
    elif state == 'booking_confirm':
        return handle_booking_confirm(text, sess, user)
    
    elif state == 'collecting_pnr':
        return handle_pnr_input(text, sess)
    
    # IDLE STATE - Detect intent
    intent = detect_intent(text)
    print(f"[DM] Intent: {intent}")
    
    # GREETING
    if intent == 'greeting' and 'from' not in text and 'to' not in text:
        import random
        return reply(random.choice(REPLIES['greeting']))
    
    # HELP
    if intent == 'help':
        return reply(REPLIES['help'])
    
    # BOOKING HISTORY
    if intent == 'history':
        return handle_history(user)
    
    # PNR CHECK
    if intent == 'pnr':
        pnr = extract_pnr(text)
        if pnr:
            return handle_pnr_check(pnr)
        else:
            sess['state'] = 'collecting_pnr'
            return reply(REPLIES['pnr_ask'])
    
    # BOOK COMMAND
    if intent == 'book' or any(kw in text for kw in KEYWORDS['numbers']):
        if sess.get('trains'):
            num = extract_number(text)
            if num and 1 <= num <= len(sess['trains']):
                return start_booking(num, sess)
            else:
                return reply(REPLIES['book_invalid_number'])
        else:
            return reply(REPLIES['book_no_trains'])
    
    # SEARCH TRAINS
    if intent == 'search' or 'to' in text:
        source, dest = extract_cities(text)
        if source and dest:
            return handle_search(source, dest, sess)
        elif source:
            return reply(REPLIES['search_no_dest'])
        elif dest:
            return reply(REPLIES['search_no_source'])
    
    # UNKNOWN
    return reply(REPLIES['unknown'])

def reply(text, speak=None, action=None, data=None):
    """Create a response dict"""
    return {
        'response': text,
        'speak': speak or text,
        'action': action,
        'data': data
    }

# ============================================================================
# HANDLERS - Process specific intents
# ============================================================================

def handle_search(source, dest, sess):
    """Handle train search"""
    # Find stations
    source_stations = find_stations(source)
    dest_stations = find_stations(dest)
    
    if not source_stations:
        return reply(REPLIES['search_not_found_source'])
    
    if not dest_stations:
        return reply(REPLIES['search_not_found_dest'])
    
    src_name = source_stations[0]['station_name']
    dst_name = dest_stations[0]['station_name']
    
    # Search trains
    trains = search_trains(src_name, dst_name)
    
    if not trains:
        return reply(REPLIES['search_no_trains'])
    
    # Store in session
    sess['trains'] = trains[:6]
    sess['source'] = src_name
    sess['destination'] = dst_name
    
    # Build response
    response = f"🚂 **Found {len(trains)} trains from {src_name} to {dst_name}!**\n\n"
    
    for i, t in enumerate(trains[:6], 1):
        price = t.get('price_sleeper', 500)
        response += f"**{i}. {t['train_name']}**\n"
        response += f"   🕐 {t.get('departure_time', 'N/A')} → {t.get('arrival_time', 'N/A')}\n"
        response += f"   💰 From ₹{int(price)}\n\n"
    
    response += "**Say 'book 1' to book the first train.**"
    
    speak = REPLIES['search_found'].format(
        count=len(trains),
        source=source,
        dest=dest
    )
    
    return reply(response, speak, 'show_trains', {
        'trains': trains[:6],
        'source': src_name,
        'destination': dst_name
    })

def start_booking(train_num, sess):
    """Start booking process for selected train"""
    trains = sess.get('trains', [])
    
    if not trains or train_num > len(trains):
        return reply(REPLIES['book_no_trains'])
    
    train = trains[train_num - 1]
    
    # Initialize booking
    sess['state'] = 'booking_name'
    sess['booking'] = {
        'train': train,
        'source': sess.get('source', ''),
        'destination': sess.get('destination', ''),
        'date': datetime.now().strftime('%Y-%m-%d')
    }
    
    response = f"🎫 **Booking: {train['train_name']}**\n"
    response += f"📍 {sess['source']} → {sess['destination']}\n\n"
    response += "**Step 1/5: " + REPLIES['ask_name'] + "**"
    
    speak = REPLIES['book_started'].format(train_name=train['train_name'])
    
    return reply(response, speak)

def handle_booking_name(text, sess):
    """Collect passenger name"""
    # Clean name
    name = re.sub(r'^(my name is|i am|this is|name is|it\'s|its)\s*', '', text, flags=re.I)
    name = name.strip().title()
    
    if len(name) >= 2:
        sess['booking']['name'] = name
        sess['state'] = 'booking_age'
        
        response = f"✅ Name: **{name}**\n\n**Step 2/5: " + REPLIES['ask_age'] + "**"
        return reply(response, REPLIES['ask_age'])
    
    return reply(REPLIES['invalid_name'])

def handle_booking_age(text, sess):
    """Collect passenger age"""
    age = extract_age(text)
    
    if age:
        sess['booking']['age'] = age
        sess['state'] = 'booking_gender'
        
        response = f"✅ Age: **{age}**\n\n**Step 3/5: " + REPLIES['ask_gender'] + "**"
        return reply(response, REPLIES['ask_gender'])
    
    return reply(REPLIES['invalid_age'])

def handle_booking_gender(text, sess):
    """Collect passenger gender"""
    gender = extract_gender(text)
    
    if gender:
        sess['booking']['gender'] = gender
        sess['state'] = 'booking_phone'
        
        response = f"✅ Gender: **{gender}**\n\n**Step 4/5: " + REPLIES['ask_phone'] + "**"
        return reply(response, REPLIES['ask_phone'])
    
    return reply(REPLIES['invalid_gender'])

def handle_booking_phone(text, sess):
    """Collect passenger phone"""
    phone = extract_phone(text)
    
    if phone:
        sess['booking']['phone'] = phone
        sess['state'] = 'booking_class'
        
        response = f"✅ Phone: **{phone}**\n\n**Step 5/5: " + REPLIES['ask_class'] + "**"
        return reply(response, REPLIES['ask_class'])
    
    return reply(REPLIES['invalid_phone'])

def handle_booking_class(text, sess):
    """Collect travel class"""
    travel_class = extract_class(text)
    
    if travel_class:
        sess['booking']['travel_class'] = travel_class
        sess['state'] = 'booking_confirm'
        
        booking = sess['booking']
        class_display = travel_class.upper().replace('_', ' ')
        
        response = f"""📋 **BOOKING SUMMARY**

🚂 **Train:** {booking['train']['train_name']}
📍 **Route:** {booking['source']} → {booking['destination']}

👤 **Passenger:**
• Name: {booking['name']}
• Age: {booking['age']} years
• Gender: {booking['gender']}
• Phone: {booking['phone']}
• Class: {class_display}

**Say YES to confirm or NO to cancel.**"""
        
        speak = REPLIES['ask_confirm'].format(
            name=booking['name'],
            age=booking['age'],
            gender=booking['gender'],
            phone=booking['phone'],
            travel_class=class_display
        )
        
        return reply(response, speak)
    
    return reply(REPLIES['invalid_class'])

def handle_booking_confirm(text, sess, user):
    """Handle booking confirmation"""
    if has_confirm_yes(text):
        return complete_booking(sess, user)
    
    if has_confirm_no(text):
        clear_booking(sess)
        return reply(REPLIES['booking_cancelled'])
    
    return reply("Please say YES to confirm or NO to cancel.")

def complete_booking(sess, user):
    """Create the booking in database"""
    booking = sess['booking']
    train = booking['train']
    
    try:
        result = create_booking(
            user_id=user.id,
            schedule_id=train.get('schedule_id'),
            passenger_name=booking['name'],
            passenger_age=booking['age'],
            passenger_gender=booking['gender'],
            passenger_phone=booking['phone'],
            travel_class=booking['travel_class'],
            travel_date=booking['date']
        )
        
        if result:
            clear_booking(sess)
            sess['trains'] = []  # Clear search too
            
            pnr = result.get('pnr', 'N/A')
            seat = result.get('seat_number', 'N/A')
            amount = int(result.get('total_amount', 0))
            
            response = f"""🎉 **BOOKING CONFIRMED!**

✅ **PNR:** {pnr}
🪑 **Seat:** {seat}
💰 **Amount:** ₹{amount}

Save your PNR: **{pnr}**
View in: **Booking History**

Have a great journey! 🚂"""
            
            speak = REPLIES['booking_success'].format(pnr=pnr, seat=seat, amount=amount)
            
            return reply(response, speak, 'booking_complete', result)
        else:
            clear_booking(sess)
            return reply(REPLIES['booking_failed'])
            
    except Exception as e:
        print(f"[BOOKING ERROR] {e}")
        clear_booking(sess)
        return reply(REPLIES['booking_failed'])

def handle_history(user):
    """Show user's booking history"""
    bookings = get_user_bookings(user.id)
    
    if not bookings:
        return reply(REPLIES['history_empty'])
    
    response = f"📜 **Your Bookings ({len(bookings)})**\n\n"
    
    for i, b in enumerate(bookings[:5], 1):
        response += f"{i}. **PNR: {b['pnr_number']}** - {b.get('passenger_name', 'N/A')} - {b.get('booking_status', 'confirmed')}\n"
    
    speak = REPLIES['history_found'].format(
        count=len(bookings),
        pnr=bookings[0]['pnr_number']
    )
    
    return reply(response, speak, 'show_bookings', {'bookings': bookings})

def handle_pnr_check(pnr):
    """Check PNR status"""
    booking = get_booking_by_pnr(pnr)
    
    if booking:
        response = f"""✅ **PNR Status: {pnr}**

🚂 Train: {booking.get('train_name', 'N/A')}
📍 Route: {booking.get('source_station', 'N/A')} → {booking.get('dest_station', 'N/A')}
👤 Passenger: {booking.get('passenger_name', 'N/A')}
🎫 Status: **{booking.get('booking_status', 'confirmed').upper()}**"""
        
        speak = REPLIES['pnr_found'].format(
            pnr=pnr,
            status=booking.get('booking_status', 'confirmed'),
            name=booking.get('passenger_name', 'unknown'),
            train=booking.get('train_name', 'train')
        )
        
        return reply(response, speak, 'show_pnr', booking)
    else:
        return reply(REPLIES['pnr_not_found'].format(pnr=pnr))

def handle_pnr_input(text, sess):
    """Handle PNR input when collecting"""
    pnr = extract_pnr(text)
    
    if pnr:
        sess['state'] = 'idle'
        return handle_pnr_check(pnr)
    
    # Try to extract digits
    digits = ''.join(re.findall(r'\d', text))
    if len(digits) >= 10:
        sess['state'] = 'idle'
        return handle_pnr_check(digits[:10])
    
    return reply(REPLIES['pnr_ask'])

# ============================================================================
# FLASK ROUTES
# ============================================================================

@bp.route('/interface')
@login_required
def voice_interface():
    """Render the voice interface page"""
    if not current_user.voice_enabled:
        return redirect(url_for('auth.voice_preferences'))
    return render_template('voice/interface.html')

@bp.route('/process-command', methods=['POST'])
@login_required
def process_voice_command():
    """Process voice commands via API"""
    try:
        data = request.get_json()
        text = data.get('command', '').strip()
        session_id = data.get('session_id', str(current_user.id))
        
        if not text:
            return jsonify({
                'status': 'success',
                'session_id': session_id,
                'response': 'I did not hear anything. Please speak again.',
                'speak': 'I did not hear anything. Please speak again.'
            })
        
        # Get session
        sess = get_session(session_id, current_user.id)
        
        print(f"\n[VOICE] Input: '{text}'")
        
        # Process through dialogue manager
        result = process_dialogue(text.lower(), sess, current_user)
        
        print(f"[VOICE] Output: '{result.get('speak', '')[:60]}...'")
        
        return jsonify({
            'status': 'success',
            'session_id': session_id,
            'command': text,
            'response': result.get('response', ''),
            'speak': result.get('speak', ''),
            'action': result.get('action'),
            'data': result.get('data')
        })
        
    except Exception as e:
        print(f"[VOICE ERROR] {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'status': 'success',
            'response': REPLIES['error'],
            'speak': REPLIES['error']
        })

@bp.route('/get-stations', methods=['GET'])
def get_stations_list():
    """Get list of stations"""
    stations = find_stations('')
    return jsonify({
        'stations': [
            {'code': s['station_code'], 'name': s['station_name'], 'city': s['city']}
            for s in stations
        ]
    })
