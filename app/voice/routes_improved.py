"""
Enhanced Voice Routes with AI-like capabilities
Replaces the existing routes.py with improved context awareness and personalization
"""

from flask import render_template, request, jsonify, session, redirect, url_for
from flask_login import login_required, current_user
from app.voice import bp
from app.database import search_trains, find_stations, get_booking_by_pnr, get_user_bookings, create_booking
from datetime import datetime, timedelta
import re
import json
from difflib import SequenceMatcher
import random

# In-memory session storage for voice context
VOICE_SESSIONS = {}

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
    """Process voice commands with AI-like context awareness"""
    try:
        data = request.get_json()
        command = data.get('command', '').lower().strip()
        session_id = data.get('session_id')
        
        if not command:
            return jsonify({
                'status': 'error',
                'message': 'No command received',
                'speak': 'I did not hear anything. Please speak again.'
            })
        
        if not session_id:
            session_id = generate_voice_session_id()
        
        voice_session = get_or_create_voice_session(session_id, current_user.id)
        voice_session['history'].append({
            'command': command,
            'timestamp': datetime.now().isoformat()
        })
        
        #Process with context awareness
        response = parse_command_with_context(command, voice_session, current_user)
        
        return jsonify({
            'status': 'success',
            'session_id': session_id,
            'command': command,
            'response': response['response'],
            'speak': response['speak'],
            'action': response.get('action'),
            'data': response.get('data')
        })
    except Exception as e:
        print(f'Error processing voice command: {str(e)}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': f'Error: {str(e)}',
            'speak': 'I encountered an error. Could you please rephrase that?'
        }), 200

@bp.route('/get-stations', methods=['GET'])
def get_stations_list():
    """Get list of stations for voice recognition"""
    stations = find_stations('')
    station_data = []
    
    for station in stations:
        station_data.append({
            'code': station['station_code'],
            'name': station['station_name'],
            'city': station['city'],
            'aliases': [station['station_name'].lower(), station['city'].lower(), station['station_code'].lower()]
        })
    
    return jsonify({'stations': station_data})


# AI-LIKE SMART FUNCTIONS

def parse_command_with_context(command, voice_session, user):
    """Parse command with context awareness - the core AI engine"""
    
    # Priority State: PNR Collection for Cancellation (Bug Fix)
    if voice_session.get('state') == 'collecting_cancel_pnr':
        return handle_cancel_pnr_collection(command, voice_session, user)

    # 1. Get Intent First to check for interruptions
    context = analyze_context(command, voice_session)
    intent = detect_smart_intent(command, context, voice_session)
    
    # Priority 1: High-level Interruptions (like cancelling a ticket vs cancelling a prompt)
    if intent['type'] == 'cancel_booking' and 'booking' in command:
        voice_session['booking_in_progress'] = None 
        voice_session['state'] = None
        return handle_cancel_booking(command, voice_session, user)

    # Priority 2: Active Multi-step Flows
    if voice_session.get('booking_in_progress'):
        return handle_booking_details_collection(command, voice_session, user)

    state = voice_session.get('state')
    
    # Priority 3: State-based collections
    if state == 'wait_for_locations':
        search_params = extract_locations(command)
        if search_params:
            voice_session['state'] = None 
            date = extract_date_smart(command)
            return process_train_search_smart(search_params[0], search_params[1], date, voice_session, user)
    
    # Priority 4: Branch on Intent
    if intent['type'] == 'greeting':
        return handle_greeting_personalized(user)
    elif intent['type'] == 'start_booking':
        return handle_start_booking(intent['train_index'], voice_session)
    elif intent['type'] == 'cancel_booking':
        return handle_cancel_booking(command, voice_session, user)
    elif intent['type'] == 'search_trains':
        voice_session['last_search'] = {'source': intent.get('source'), 'destination': intent.get('destination'), 'date': intent.get('date')}
        return process_train_search_smart(intent.get('source'), intent.get('destination'), intent.get('date'), voice_session, user)
    elif intent['type'] == 'incomplete_search':
        return handle_incomplete_search(voice_session)
    elif intent['type'] == 'pnr_status':
        return process_pnr_check_smart(intent.get('pnr'))
    elif intent['type'] == 'booking_history':
        return process_booking_history_smart(user)
    elif intent['type'] == 'follow_up':
        return handle_follow_up_smart(command, voice_session)
    elif intent['type'] == 'help':
        return handle_help_personalized(user)
    else:
        suggestions = get_smart_suggestions(command, voice_session, user)
        return handle_unknown_smart(command, suggestions)


def handle_cancel_pnr_collection(command, voice_session, user):
    """Handle the PNR collection loop for cancellation with exit path"""
    # 1. Check for Abort keywords
    if any(w in command for w in ['stop', 'cancel', 'never mind', 'exit', 'quit']):
        voice_session['state'] = None
        return {
            'response': "Ok, I've aborted the cancellation. How else can I help?",
            'speak': "Ok, cancelled. What else can I do for you?"
        }

    # 2. Extract PNR
    pnr_match = re.search(r'(\d{10})', command)
    if pnr_match:
        pnr = pnr_match.group(1)
        voice_session['state'] = None # Clear state
        return {
            'response': f"✓ Cancellation request for PNR **{pnr}** submitted.",
            'speak': f"Ok, I have submitted the cancellation request for PNR {pnr}."
        }
    
    # 3. Ask again
    return {
        'response': "I couldn't find a 10-digit number. Please say the **PNR number** clearly, or say 'stop' to go back.",
        'speak': "I didn't hear a PNR. Please say the PNR number clearly, or say stop to go back."
    }


def handle_incomplete_search(voice_session):
    """Handle missing journey details for a search or booking intent"""
    voice_session['state'] = 'wait_for_locations'
    prompt = "I can help with that! Where are you traveling from, where to, and on what date?"
    return {'response': prompt, 'speak': prompt}


def handle_start_booking(train_index, voice_session):
    """Start the detailed booking collection flow"""
    trains = voice_session.get('trains_available', [])
    if not trains or train_index >= len(trains):
        return {'response': "Please select a valid train.", 'speak': "I couldn't find that train. Which one would you like?"}
    
    train = trains[train_index]
    voice_session['booking_in_progress'] = {'train': train, 'stage': 'collect_name', 'collected': {}}
    
    response = f"Great, booking **{train['train_name']}**. What is your **full name**?"
    speak = f"Ok, booking {train['train_name']}. What is your full name?"
    return {'response': response, 'speak': speak}


def handle_booking_details_collection(command, voice_session, user):
    """Guide user through multi-step details for booking"""
    booking = voice_session['booking_in_progress']
    stage = booking['stage']
    collected = booking['collected']
    
    if any(w in command for w in ['cancel', 'stop', 'quit']):
        voice_session['booking_in_progress'] = None
        return {'response': "Booking cancelled. How else can I help?", 'speak': "Cancelled. What else can I do?"}

    if stage == 'collect_name':
        name = command.title()
        collected['name'] = name
        booking['stage'] = 'collect_age'
        return {'response': f"Got it, **{name}**. How old are you?", 'speak': f"Got it, {name}. How old are you?"}
    
    elif stage == 'collect_age':
        age_match = re.search(r'(\d+)', command)
        if age_match:
            age = age_match.group(1)
            collected['age'] = age
            booking['stage'] = 'collect_gender'
            return {'response': f"Age **{age}**. Got it. What is your gender?", 'speak': f"{age}. Got it. What is your gender?"}
        return {'response': "Please say your age as a number.", 'speak': "I didn't catch that. Say your age as a number."}
    
    elif stage == 'collect_gender':
        gender = 'Male' if 'male' in command else 'Female' if 'female' in command else 'Other'
        collected['gender'] = gender
        booking['stage'] = 'confirm_booking'
        
        # Summary for VUI
        summary = f"{booking['train']['train_name']} for {collected['name']}, age {collected['age']}."
        return {
            'response': f"✓ **Confirm Booking Details**:\n\n• Train: **{booking['train']['train_name']}**\n• Passenger: **{collected['name']}**\n• Age: **{collected['age']}**\n• Gender: **{collected['gender']}**\n\nShall I proceed with the booking? Say **Yes** or **No**.",
            'speak': f"I have your details. Booking {summary}. Shall I proceed with the booking?"
        }
    
    elif stage == 'confirm_booking':
        if any(w in command for w in ['yes', 'yeah', 'sure', 'proceed', 'go ahead', 'confirm']):
            return complete_booking(voice_session, user)
        else:
            voice_session['booking_in_progress'] = None
            return {'response': "Booking aborted. How else can I help?", 'speak': "Ok, I have aborted the booking. What else can I do?"}
    
    return {'response': "I didn't quite get that.", 'speak': "Sorry, please repeat that."}


def complete_booking(voice_session, user):
    """Create the booking in database and return VUI success"""
    booking = voice_session.get('booking_in_progress')
    if not booking:
        return {'response': "Something went wrong.", 'speak': "Sorry, something went wrong with the booking."}
    
    train = booking['train']
    collected = booking['collected']
    
    try:
        # Final confirmation and DB insertion
        result = create_booking(
            user_id=user.id,
            schedule_id=train.get('schedule_id'),
            passenger_name=collected['name'],
            passenger_age=collected['age'],
            passenger_gender=collected['gender'],
            passenger_phone=user.phone,
            travel_class='sleeper', # Default for voice
            travel_date=datetime.now().strftime('%Y-%m-%d')
        )
        
        if result:
            pnr = result.get('pnr', 'N/A')
            voice_session['booking_in_progress'] = None
            voice_session['trains_available'] = [] # Clear search
            
            response = f"🎉 **CONGRATULATIONS!**\n\nYour ticket for **{train['train_name']}** is booked.\n✅ **PNR:** {pnr}\n✅ **Seat:** {result.get('seat_number')} (Sleeper)\n\nHave a great journey! 🚂"
            speak = f"Congratulations! Your ticket is booked. Your PNR is {pnr}. Have a great journey!"
            
            return {
                'response': response,
                'speak': speak,
                'action': 'booking_complete',
                'data': result
            }
        else:
            voice_session['booking_in_progress'] = None
            return {'response': "Booking failed. Please try again later.", 'speak': "I am sorry, the booking failed. Please try again later."}
            
    except Exception as e:
        print(f"[VOICE BOOKING ERROR] {e}")
        voice_session['booking_in_progress'] = None
        return {'response': f"Error: {str(e)}", 'speak': "I encountered an error while booking. Please try again."}


def handle_cancel_booking(command, voice_session, user):
    """Handle booking cancellation flow"""
    pnr_match = re.search(r'(\d{10})', command)
    pnr = pnr_match.group(1) if pnr_match else None
    
    if pnr:
        voice_session['state'] = None
        return {
            'response': f"✓ Cancellation request for PNR **{pnr}** submitted.",
            'speak': f"Ok, I have submitted the cancellation request for PNR {pnr}."
        }
    
    voice_session['state'] = 'collecting_cancel_pnr'
    return {
        'response': "Search for PNR to cancel. Please tell me your **10-digit PNR number**.",
        'speak': "To cancel, please tell me your 10 digit PNR number."
    }


def analyze_context(command, voice_session):
    """Analyze previous context to understand intent better"""
    context = {
        'has_recent_search': bool(voice_session.get('last_search')),
        'conversation_turns': len(voice_session.get('history', [])),
        'recent_action': voice_session.get('last_search')
    }
    return context


def detect_smart_intent(command, context, voice_session):
    """Detect intent with context-awareness - smarter than keywords alone"""
    
    # 1. Greetings - use word boundaries to avoid matching "hi" in "delhi"
    greeting_words = ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'namaste', 'sarah']
    if any(re.search(rf'\b{word}\b', command) for word in greeting_words):
        return {'type': 'greeting'}
    
    # 2. Help
    if any(word in command for word in ['help', 'what can you', 'how do', 'assist']):
        return {'type': 'help'}

    # 3. Booking history (Prioritized to avoid overlap)
    if 'show' in command or 'history' in command or ('my' in command and 'booking' in command):
        if not any(word in command for word in ['to', 'from', 'between']): # Simple check to not block search
            return {'type': 'booking_history'}

    # 4. PNR Status
    pnr_match = re.search(r'(\d{10})', command)
    if pnr_match or 'pnr' in command:
        pnr_num = pnr_match.group(1) if pnr_match else None
        return {'type': 'pnr_status', 'pnr': pnr_num}

    # 5. Booking Selection (Bug Fix 1)
    if voice_session.get('last_search') or voice_session.get('trains_available'):
        # Check for phrases like "book 1", "first one", "book option 2"
        book_match = re.search(r'(?:book|select|take|want)\s+(?:train|option|number)?\s*(?:one|two|three|1|2|3|first|second|third)', command)
        ordinals = {'first': 0, 'second': 1, 'third': 2}
        words = {'one': 0, 'two': 1, 'three': 2}
        
        if book_match or any(w in command for w in ['first', 'second', 'third']):
            match_text = book_match.group(0) if book_match else command
            idx = 0
            for k, v in ordinals.items():
                if k in match_text: idx = v
            for k, v in words.items():
                if k in match_text: idx = v
            digit_match = re.search(r'(\d)', match_text)
            if digit_match: idx = int(digit_match.group(1)) - 1
            
            return {'type': 'start_booking', 'train_index': max(0, idx)}

    # 6. Cancel Booking
    if 'cancel' in command and any(w in command for w in ['booking', 'ticket', 'train', 'pnr', 'reservation']):
        return {'type': 'cancel_booking'}

    # 7. Search / Booking (Filtering out history keywords)
    search_keywords = ['book', 'train', 'search', 'ticket', 'travel', 'go to', 'find']
    history_keywords = ['show', 'history', 'my tickets', 'previous']
    
    has_search_trigger = any(kw in command for kw in search_keywords)
    is_not_history = not any(kw in command for kw in history_keywords)
    
    search_params = extract_locations(command)
    
    if search_params and search_params[0] and search_params[1] and is_not_history:
        return {
            'type': 'search_trains',
            'source': search_params[0],
            'destination': search_params[1],
            'date': extract_date_smart(command)
        }
    
    # Trigger incomplete search if intent is seen or partial locations found (and not history)
    if (has_search_trigger and is_not_history) or (search_params and (search_params[0] or search_params[1]) and is_not_history):
        return {'type': 'incomplete_search'}

    # 8. Follow-up to previous search
    if context.get('has_recent_search'):
        follow_up_words = ['which', 'first', 'best', 'cheapest', 'fastest', 'price', 'cost']
        if any(word in command for word in follow_up_words):
            return {'type': 'follow_up'}

    return {'type': 'unknown'}


def extract_locations(command):
    """Smart location extraction using fuzzy matching and excluding command words"""
    # 1. Check for Coimbatore Fix
    locations = {
        'mumbai': ['mumbai', 'bombay', 'csmt', 'dadar'],
        'delhi': ['delhi', 'ndls', 'new delhi'],
        'bangalore': ['bangalore', 'bengaluru', 'sbc'],
        'kolkata': ['kolkata', 'calcutta', 'hwh'],
        'chennai': ['chennai', 'madras', 'mas'],
        'hyderabad': ['hyderabad', 'hyb'],
        'pune': ['pune', 'poona'],
        'ahmedabad': ['ahmedabad', 'adi'],
        'jaipur': ['jaipur', 'jp'],
        'lucknow': ['lucknow', 'lko'],
        'coimbatore': ['coimbatore', 'cbe', 'kovai']
    }
    
    found_locations = []
    # Normalize and split, but only keep words that aren't common command keywords
    keywords_to_exclude = ['trains', 'train', 'book', 'search', 'ticket', 'from', 'to', 'for']
    words = [w for w in command.lower().split() if w not in keywords_to_exclude]
    
    for city, aliases in locations.items():
        if any(alias in command.lower() for alias in aliases):
            found_locations.append(city)
    
    # Deduplicate while preserving order
    unique_locations = list(dict.fromkeys(found_locations))
    
    if len(unique_locations) >= 2:
        return (unique_locations[0], unique_locations[1])
    
    # Handle single location searches if triggered by "to [city]"
    dest_match = re.search(r'(?:to|towards|for)\s+([a-z]+)', command.lower())
    if dest_match:
        city = dest_match.group(1)
        if city in locations:
             return (None, city) # Source unknown, Destination found

    return None


def extract_date_smart(command):
    """Smart date extraction"""
    today = datetime.now().date()
    
    if 'tomorrow' in command:
        return today + timedelta(days=1)
    elif 'today' in command:
        return today
    elif 'day after' in command:
        return today + timedelta(days=2)
    
    # Check for "in X days"
    days_match = re.search(r'in\s+(\d+)\s+days?', command)
    if days_match:
        return today + timedelta(days=int(days_match.group(1)))
    
    # Default to today
    return today


def handle_follow_up_smart(command, voice_session):
    """Handle follow-up questions with intelligence"""
    last_search = voice_session.get('last_search', {})
    
    if not last_search:
        return {
            'response': 'I do not have a previous search. Could you specify your route again?',
            'speak': 'Please tell me which stations you want to travel between.'
        }
    
    source = last_search.get('source', 'your source')
    dest = last_search.get('destination', 'your destination')
    
    if any(word in command for word in ['which', 'first', 'best']):
        response = f"For your journey from {source} to {dest}, the first option usually has great schedules. Would you like more details?"
        speak = f"The first train from {source} to {dest} is usually a good choice. Shall I help you book?"
    elif any(word in command for word in ['cheapest', 'price', 'cost']):
        response = f"The most economical option from {source} to {dest} is typically sleeper class."
        speak = f"Sleeper class offers the best value for your journey from {source} to {dest}."
    elif any(word in command for word in ['fastest', 'quick']):
        response = f"Rajdhani trains are the fastest between {source} and {dest}."
        speak = f"Rajdhani is your fastest option from {source} to {dest}."
    else:
        response = f"Regarding your {source} to {dest} search, what would you like to know?"
        speak = f"Tell me more about your {source} to {dest} trip."
    
    return {'response': response, 'speak': speak}


def process_train_search_smart(source, destination, travel_date, voice_session, user):
    """Search trains with availability and pricing info for VUI"""
    
    source_stations = find_stations_fuzzy(source)
    dest_stations = find_stations_fuzzy(destination)
    
    if not source_stations or not dest_stations:
        return {
            'response': f'I could not find one of those stations. Could you try with different station names or codes?',
            'speak': 'I am not sure about one of those stations. Please try different station names.'
        }
    
    source_station = source_stations[0]
    dest_station = dest_stations[0]
    
    trains = search_trains(source_station['station_name'], dest_station['station_name'])
    
    if not trains:
        return {
            'response': f'No trains between {source_station["station_name"]} and {dest_station["station_name"]}. Try a different date?',
            'speak': f'No trains available for that route on that date. Would you like to try a different date?'
        }
    
    # Store for future booking
    voice_session['trains_available'] = trains[:6]
    
    response = f'Found {len(trains)} trains from {source_station["station_name"]} to {dest_station["station_name"]}:\n\n'
    speak = f"I found {len(trains)} trains for your trip from {source_station['city']} to {dest_station['city']}. "
    
    trains_data = []
    for i, train in enumerate(trains[:3], 1): # VUI should only speak top options clearly
        price = train.get('price_sleeper', 0) or train.get('price_ac_3', 0) or 850
        seats = random.randint(12, 85) # Mock seat availability
        
        response += f'{i}. {train["train_name"]} - {train["departure_time"]} - From ₹{int(price)} ({seats} seats)\n'
        
        # VUI optimized speak string (no symbols, no markdown)
        speak += f"Train {i} is {train['train_name']} at {train['departure_time']}. Tickets start at {int(price)} rupees with {seats} seats available. "
        
        trains_data.append({
            'schedule_id': train.get('schedule_id'),
            'train_number': train.get('train_number'),
            'train_name': train.get('train_name'),
            'departure': train.get('departure_time'),
            'price': price,
            'seats': seats
        })
    
    speak += "Which one would you like to book? Say book 1, book 2, or ask for the cheapest option."
    
    return {
        'response': response,
        'speak': speak,
        'action': 'show_trains',
        'data': {'trains': trains_data, 'source': source_station['station_name'], 'destination': dest_station['station_name']}
    }


def handle_greeting_personalized(user):
    """Personalized greetings - never repeat"""
    greetings = [
        f"Hello {user.first_name}! I am Sarah, your AI train booking assistant. Ready to help you book?",
        f"Hey {user.first_name}! I am Sarah. Looking for trains or checking bookings today?",
        f"Hi {user.first_name}! I am Sarah. How can I assist with your train travel?",
        f"Welcome back {user.first_name}! I am Sarah. What can I help you with?"
    ]
    
    greeting = random.choice(greetings)
    return {'response': greeting, 'speak': greeting}


def handle_help_personalized(user):
    """Personalized help responses"""
    help_text = f"""I am Sarah, your AI train booking assistant for {user.first_name}.

✓ **Search Trains**: "Search trains from Mumbai to Delhi" or "Book from Bangalore to Chennai tomorrow"
✓ **Check PNR**: "Check PNR 1234567890" or "What is status of 1234567890"
✓ **My Bookings**: "Show my bookings" or "My booking history"
✓ **Smart Questions**: "Which is cheapest?", "Which is fastest?", "Best price for this route?"

I learn from your preferences and remember your searches!"""
    
    help_speak = f"I am Sarah! I can search trains, check PNR, show your bookings, and answer follow-up questions. Just speak naturally {user.first_name}!"
    
    return {'response': help_text, 'speak': help_speak}


def handle_unknown_smart(command, suggestions):
    """Smart unknown command handling"""
    response = f"Hmm, I am not sure about that request.\n\n"
    
    if suggestions:
        response += "Did you mean:\n" + "\n".join([f"• {s}" for s in suggestions])
    else:
        response += "Please try: Search trains, Check PNR, or Show my bookings"
    
    speak = suggestions[0] if suggestions else "Could you rephrase that please?"
    
    return {'response': response, 'speak': speak}


def get_smart_suggestions(command, voice_session, user):
    """Generate smart context-based suggestions"""
    suggestions = []
    
    words = command.split()
    locations = ['mumbai', 'delhi', 'bangalore', 'kolkata', 'chennai', 'hyderabad', 'pune', 'ahmedabad']
    found = [w for w in words if w in locations]
    
    if len(found) == 2:
        suggestions.append(f"Search trains from {found[0]} to {found[1]}?")
    elif len(found) == 1:
        suggestions.append(f"Which station would you like to travel to from {found[0]}?")
    
    if voice_session.get('last_search'):
        s = voice_session['last_search']
        suggestions.append(f"Modify your {s['source']} to {s['destination']} search?")
    
    return suggestions[:3]


def process_pnr_check_smart(pnr):
    """Smart PNR checking"""
    booking = get_booking_by_pnr(pnr) if pnr else None
    
    if not booking:
        return {
            'response': f'PNR {pnr} not found in my records.',
            'speak': f'I could not find PNR {pnr}. Please double-check the number.'
        }
    
    response = f"Your PNR {pnr} Status: {booking.get('booking_status', 'Unknown').upper()}\nTrain: {booking.get('train_name', 'N/A')}"
    speak = f"Your PNR {pnr} is {booking.get('booking_status', 'unknown')}"
    
    return {'response': response, 'speak': speak}


def process_booking_history_smart(user):
    """Get booking history with smart formatting"""
    bookings = get_user_bookings(user.id, 5)
    
    if not bookings:
        return {
            'response': f'You have not made any bookings yet, {user.first_name}. Would you like to search for trains?',
            'speak': f'No bookings found. Would you like to search for trains?'
        }
    
    response = f"Your recent bookings:\n\n"
    speak = f"You have {len(bookings)} recent bookings. "
    
    for i, b in enumerate(bookings[:3], 1):
        response += f"{i}. {b.get('train_name')} - PNR {b.get('pnr_number')} - {b.get('booking_status')}\n"
        if i == 1:
            speak += f"First booking: {b.get('train_name')}. "
    
    return {'response': response, 'speak': speak}


def find_stations_fuzzy(search_term):
    """Fuzzy station matching with prioritization"""
    if not search_term:
        return []
    
    # Try exact match first
    search_lower = search_term.lower()
    stations = find_stations(search_term)
    
    # Prioritize New Delhi (NDLS) if "delhi" is searched
    if search_lower == 'delhi' and stations:
        stations.sort(key=lambda s: 0 if s['station_code'] == 'NDLS' else 1)
        return stations
        
    if stations:
        return stations
    
    # Common aliases
    aliases = {
        'mumbai': ['bombay', 'csmt', 'dadar'],
        'delhi': ['ndls', 'new delhi'],
        'bangalore': ['bengaluru', 'sbc'],
        'kolkata': ['calcutta', 'hwh'],
        'chennai': ['madras', 'mas'],
        'hyderabad': ['hyb'],
        'jaipur': ['jp'],
        'lucknow': ['lko'],
        'coimbatore': ['coimbatore', 'cbe', 'kovai']
    }
    
    for city, alias_list in aliases.items():
        for alias in alias_list:
            if alias in search_lower or search_lower in alias:
                return find_stations(city)
    
    return []


def generate_voice_session_id():
    """Generate unique session ID"""
    import uuid
    return str(uuid.uuid4())


def get_or_create_voice_session(session_id, user_id=None):
    """Get or create session with history tracking"""
    if session_id not in VOICE_SESSIONS:
        VOICE_SESSIONS[session_id] = {
            'created_at': datetime.now().isoformat(),
            'user_id': user_id,
            'history': [],
            'last_search': None
        }
    
    return VOICE_SESSIONS[session_id]
