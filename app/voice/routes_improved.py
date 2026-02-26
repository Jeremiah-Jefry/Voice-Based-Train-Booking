"""
Enhanced Voice Routes with AI-like capabilities
Replaces the existing routes.py with improved context awareness and personalization
"""

from flask import render_template, request, jsonify, session, redirect, url_for
from flask_login import login_required, current_user
from app.voice import bp
from app.database import search_trains, find_stations, get_booking_by_pnr, get_user_bookings
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
    
    context = analyze_context(command, voice_session)
    intent = detect_smart_intent(command, context, voice_session)
    
    if intent['type'] == 'greeting':
        return handle_greeting_personalized(user)
    elif intent['type'] == 'search_trains':
        voice_session['last_search'] = {
            'source': intent.get('source'),
            'destination': intent.get('destination'),
            'date': intent.get('date')
        }
        return process_train_search_smart(intent.get('source'), intent.get('destination'), intent.get('date'), voice_session, user)
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


def analyze_context(command, voice_session):
    """Analyze previous context to understand intent better"""
    context = {
        'has_recent_search': bool(voice_session.get('last_search')),
        'conversation_turns': len(voice_session.get('history', [])),
        'recent_action': voice_session.get('last_search')
    }
    return context


def detect_smart_intent(command, context, voice_session):
    """Detect intent with context-awareness - smarter than regex alone"""
    
    # Check greeting first
    if any(word in command for word in ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'namaste', 'sarah']):
        return {'type': 'greeting'}
    
    # Check help
    if any(word in command for word in ['help', 'what can', 'how do', 'assist', 'capability']):
        return {'type': 'help'}
    
    # Check booking history
    if any(word in command for word in ['my bookings', 'booking', 'ticket', 'reservation', 'history', 'previous']):
        if not ('from' in command or 'to' in command):  # Don't confuse with search
            return {'type': 'booking_history'}
    
    # Check PNR
    pnr_match = re.search(r'(\d{10})', command)
    if pnr_match or 'pnr' in command:
        pnr_num = pnr_match.group(1) if pnr_match else None
        return {'type': 'pnr_status', 'pnr': pnr_num}
    
    # Check train search
    search_params = extract_locations(command)
    if search_params:
        return {
            'type': 'search_trains',
            'source': search_params[0],
            'destination': search_params[1],
            'date': extract_date_smart(command)
        }
    
    # Check if follow-up to previous search
    if context.get('has_recent_search'):
        follow_up_words = ['which', 'first', 'best', 'cheapest', 'fastest', 'price', 'when', 'how much']
        if any(word in command for word in follow_up_words):
            return {'type': 'follow_up'}
    
    return {'type': 'unknown'}


def extract_locations(command):
    """Smart location extraction using fuzzy matching"""
    # List of known locations
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
        'lucknow': ['lucknow', 'lko']
    }
    
    found_locations = []
    words = command.split()
    
    for city, aliases in locations.items():
        for word in words:
            if any(alias in word.lower() for alias in aliases):
                found_locations.append(city)
                break
    
    if len(found_locations) >= 2:
        return (found_locations[0], found_locations[1])
    
    # Try regex fallback
    patterns = [
        r'(?:from|for)\s+([a-z]+)\s+to\s+([a-z]+)',
        r'([a-z]+)\s+to\s+([a-z]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, command)
        if match:
            return (match.group(1), match.group(2))
    
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
    """Search trains with better matching and varied responses"""
    
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
    
    # Varied response
    variations = [
        f'Great! Found {len(trains)} excellent options for you!',
        f'Perfect! {len(trains)} trains available for your journey.',
        f'Excellent news! {len(trains)} trains to choose from.',
        f'You are in luck! {len(trains)} options found.'
    ]
    
    speak = random.choice(variations) + f' From {source_station["station_name"]} to {dest_station["station_name"]}. '
    
    response = f'Found {len(trains)} trains from {source_station["station_name"]} to {dest_station["station_name"]}:\n\n'
    
    trains_data = []
    for i, train in enumerate(trains[:6], 1):
        price = train.get('price_sleeper', 0) or train.get('price_ac_3', 0) or 0
        response += f'{i}. {train["train_name"]} - Departs {train["departure_time"]}, From ₹{int(price)}\n'
        
        if i <= 2:
            speak += f'{train["train_name"]} at {train["departure_time"]}. '
        
        trains_data.append({
            'schedule_id': train.get('schedule_id'),
            'train_number': train.get('train_number'),
            'train_name': train.get('train_name'),
            'departure': train.get('departure_time'),
            'price': price
        })
    
    if len(trains) > 2:
        speak += f'And {len(trains) - 2} more options available.'
    
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
    """Fuzzy station matching"""
    if not search_term:
        return []
    
    # Try exact match first
    stations = find_stations(search_term)
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
        'lucknow': ['lko']
    }
    
    search_lower = search_term.lower()
    
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
