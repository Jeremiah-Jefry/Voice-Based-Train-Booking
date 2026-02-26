from flask import render_template, request, jsonify, session, redirect, url_for
from flask_login import login_required, current_user
from app.voice import bp
from app.database import search_trains, find_stations, get_booking_by_pnr, get_user_bookings
from datetime import datetime, timedelta
import re
import json
from difflib import SequenceMatcher
import hashlib

# Voice session storage for context and memory
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
    """Process voice commands with context awareness and personalization"""
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
        
        # Initialize or get voice session with context
        if not session_id:
            session_id = generate_voice_session_id()
        
        voice_session = get_or_create_voice_session(session_id, current_user.id)
        
        # Add command to history for context
        voice_session['history'].append({
            'command': command,
            'timestamp': datetime.now().isoformat()
        })
        
        # Process the command with context awareness
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
            'speak': 'I encountered an error. Please try rephrasing your request.'
        }), 200

@bp.route('/get-stations', methods=['GET'])
def get_stations_list():
    """Get list of stations for voice recognition"""
    stations = find_stations('')  # Get all stations
    station_data = []
    
    for station in stations:
        station_data.append({
            'code': station['station_code'],
            'name': station['station_name'],
            'city': station['city'],
            'aliases': [station['station_name'].lower(), station['city'].lower(), station['station_code'].lower()]
        })
    
    return jsonify({'stations': station_data})

def parse_command_with_context(command, voice_session, user):
    """Parse voice command with context awareness and personalization"""
    
    # Check if this is a follow-up based on recent history
    context = analyze_context(command, voice_session)
    
    # Detect command intent
    intent = detect_command_intent(command, context, voice_session)
    
    if intent['type'] == 'greeting':
        return handle_greeting_personalized(user)
    
    elif intent['type'] == 'search_trains':
        source = intent.get('source')
        destination = intent.get('destination')
        travel_date = intent.get('date')
        # Store in session for follow-up commands
        voice_session['last_search'] = {
            'source': source,
            'destination': destination,
            'date': travel_date
        }
        return process_train_search_advanced(source, destination, travel_date, voice_session, user)
    
    elif intent['type'] == 'pnr_status':
        pnr_number = intent.get('pnr')
        return process_pnr_check(pnr_number)
    
    elif intent['type'] == 'booking_history':
        return process_booking_history(user)
    
    elif intent['type'] == 'help':
        return handle_help_personalized(user)
    
    elif intent['type'] == 'follow_up':
        # Handle follow-up questions about last search
        return handle_follow_up_question(command, voice_session, intent)
    
    elif intent['type'] == 'unknown':
        suggestions = get_smart_suggestions(command, voice_session, user)
        return handle_unknown_command_smart(command, suggestions)
    
    return {
        'response': 'I did not understand that. Could you rephrase?',
        'speak': 'I did not quite get that. Could you please rephrase your question?'
    }


def analyze_context(command, voice_session):
    """Analyze conversational context from history"""
    context = {
        'is_follow_up': False,
        'related_to_last': None,
        'conversation_length': len(voice_session.get('history', []))
    }
    
    # Check if follow-up question about trains
    follow_up_keywords = ['which', 'first', 'second', 'third', 'cheapest', 'fastest', 'when', 'price', 'cost']
    if any(keyword in command for keyword in follow_up_keywords):
        if voice_session.get('last_search'):
            context['is_follow_up'] = True
            context['related_to_last'] = 'search'
    
    return context


def handle_follow_up_question(command, voice_session, intent):
    """Handle follow-up questions about previous searches"""
    last_search = voice_session.get('last_search')
    
    if not last_search:
        return {
            'response': 'I do not have a previous search in memory. Could you please specify the route?',
            'speak': 'I do not have a recent search to reference. Please tell me which route you are interested in.'
        }
    
    # Handle different follow-up types
    if any(word in command for word in ['which', 'first', 'best', 'recommended']):
        response_text = f"Based on your search from {last_search['source']} to {last_search['destination']}, I recommend checking the first train listed - it usually has the best timing.\n\nWould you like me to show details or help with booking?"
        speak_text = f"For your trip from {last_search['source']} to {last_search['destination']}, I'd recommend the first option. Would you like to proceed with booking?"
        
    elif any(word in command for word in ['cheapest', 'lowest', 'price', 'cost']):
        response_text = f"Looking at prices for {last_search['source']} to {last_search['destination']}. The sleeper class is typically the most economical option."
        speak_text = f"For affordable options from {last_search['source']} to {last_search['destination']}, sleeper class usually offers the best value."
        
    elif any(word in command for word in ['fastest', 'quick', 'least time']):
        response_text = f"The fastest trains from {last_search['source']} to {last_search['destination']} are typically the Rajdhani or Shatabdi express trains."
        speak_text = f"Rajdhani express trains are the fastest from {last_search['source']} to {last_search['destination']}."
        
    else:
        response_text = f"Regarding your search from {last_search['source']} to {last_search['destination']}, what specific information do you need?"
        speak_text = f"Tell me more about what you need for your journey from {last_search['source']} to {last_search['destination']}."
    
    return {
        'response': response_text,
        'speak': speak_text
    }


def detect_command_intent(command, context, voice_session):
    """Enhanced intent detection with context awareness"""
    
    # Greeting patterns
    greeting_keywords = ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening', 'namaste', 'sarah']
    if any(keyword in command for keyword in greeting_keywords):
        return {'type': 'greeting'}
    
    # Help patterns
    help_keywords = ['help', 'what can you do', 'commands', 'guide', 'assist', 'capabilities']
    if any(keyword in command for keyword in help_keywords):
        return {'type': 'help'}
    
    # Booking history patterns
    history_keywords = ['my bookings', 'booking history', 'my tickets', 'past bookings', 'previous', 'reservations']
    if any(keyword in command for keyword in history_keywords):
        return {'type': 'booking_history'}
    
    # PNR status patterns
    pnr_match = re.search(r'(?:check|status|pnr).*?(\d{10})', command, re.IGNORECASE)
    if pnr_match or re.search(r'\d{10}', command):
        pnr_number = pnr_match.group(1) if pnr_match else re.search(r'(\d{10})', command).group(1)
        return {'type': 'pnr_status', 'pnr': pnr_number}
    
    # Train search patterns
    search_result = extract_train_search_params(command)
    if search_result:
        return {
            'type': 'search_trains',
            'source': search_result['source'],
            'destination': search_result['destination'],
            'date': search_result.get('date')
        }
    
    # Follow-up questions
    if context.get('is_follow_up'):
        follow_up_keywords = ['which', 'first', 'second', 'cheapest', 'fastest', 'price']
        if any(keyword in command for keyword in follow_up_keywords):
            return {'type': 'follow_up'}
    
    return {'type': 'unknown'}


def get_smart_suggestions(command, voice_session, user):
    """Provide intelligent suggestions based on command and history"""
    suggestions = []
    
    # Check for location words
    station_keywords = ['mumbai', 'delhi', 'bangalore', 'kolkata', 'chennai', 'hyderabad', 'pune', 'ahmedabad', 'jaipur', 'lucknow']
    location_words = [word for word in command.split() if word in station_keywords]
    
    if len(location_words) >= 2:
        suggestions.append(f"Did you mean to search trains from {location_words[0]} to {location_words[1]}?")
    elif len(location_words) == 1:
        suggestions.append(f"Are you looking to travel from or to {location_words[0]}?")
    elif any(char.isdigit() for char in command):
        suggestions.append("Did you mean to check a PNR status?")
    elif any(word in command for word in ['booking', 'ticket', 'history']):
        suggestions.append("Did you want to view your booking history?")
    
    # Use user history for better suggestions
    if voice_session.get('last_search'):
        last_search = voice_session['last_search']
        suggestions.append(f"Or would you like to modify your {last_search['source']} to {last_search['destination']} search?")
    
    return suggestions[:3]


def detect_command_intent(command):
    """Detect the intent of the voice command using pattern matching and keyword analysis"""
    
    # Greeting patterns
    greeting_keywords = ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening', 'namaste']
    if any(keyword in command for keyword in greeting_keywords):
        return {'type': 'greeting'}
    
    # Help patterns
    help_keywords = ['help', 'what can you do', 'commands', 'guide', 'assistant']
    if any(keyword in command for keyword in help_keywords):
        return {'type': 'help'}
    
    # Booking history patterns
    history_keywords = ['my bookings', 'booking history', 'my tickets', 'show bookings', 'past bookings', 'my reservations']
    if any(keyword in command for keyword in history_keywords):
        return {'type': 'booking_history'}
    
    # PNR status patterns
    pnr_match = re.search(r'(?:check|status|pnr).*?(\d{10})', command, re.IGNORECASE)
    if pnr_match or re.search(r'\d{10}', command):
        pnr_number = pnr_match.group(1) if pnr_match else re.search(r'(\d{10})', command).group(1)
        return {'type': 'pnr_status', 'pnr': pnr_number}
    
    # Train search patterns
    search_result = extract_train_search_params(command)
    if search_result:
        return {
            'type': 'search_trains',
            'source': search_result['source'],
            'destination': search_result['destination'],
            'date': search_result.get('date')
        }
    
    return {'type': 'unknown'}


def extract_train_search_params(command):
    """Extract train search parameters from natural language command"""
    
    # Enhanced search patterns that catch variations
    search_patterns = [
        # "search/book/find/need trains from X to Y" - most flexible
        r'(?:need\s+to\s+)?(?:search|find|look for|book|want|need)\s+(?:train[s]?)?\s*(?:from|for)\s+([a-z\s]+)\s+(?:to)\s+([a-z\s]+)',
        # "I need to book from X to Y"
        r'(?:i\s+)?(?:need\s+to\s+)?book\s+(?:train[s]?)?\s+from\s+([a-z\s]+)\s+to\s+([a-z\s]+)',
        # "X to Y trains" or "trains X to Y"
        r'(?:train[s]?)?\s*([a-z\s]+)\s+(?:to)\s+([a-z\s]+)(?:\s+train[s]?)?',
        # Direct format "from X to Y"
        r'from\s+([a-z\s]+)\s+(?:to)\s+([a-z\s]+)',
        # "trains from X to Y tomorrow/today/date"
        r'(?:train[s]?)?\s*(?:from|for)\s+([a-z\s]+)\s+to\s+([a-z\s]+)',
    ]
    
    for pattern in search_patterns:
        match = re.search(pattern, command, re.IGNORECASE)
        if match:
            source = match.group(1).strip()
            destination = match.group(2).strip()
            
            # Skip if too short or if it's a common word
            if len(source) < 2 or len(destination) < 2:
                continue
            
            # Skip if matches greeting or other patterns
            if any(word in source.lower() for word in ['hello', 'hi', 'what', 'can', 'you']):
                continue
            
            # Extract date if present
            travel_date = extract_date_from_command(command)
            
            return {
                'source': source,
                'destination': destination,
                'date': travel_date
            }
    
    return None


def get_command_suggestions(command):
    """Get suggestions for what user might have meant"""
    suggestions = []
    
    keywords_in_command = set(command.split())
    
    # Check if command contains location-like words
    station_keywords = ['mumbai', 'delhi', 'bangalore', 'kolkata', 'chennai', 'hyderabad', 'pune', 'ahmedabad', 'jaipur', 'lucknow']
    
    location_words = [word for word in keywords_in_command if word in station_keywords]
    
    if len(location_words) >= 2:
        suggestions.append(f"Did you mean to search trains from {location_words[0]} to {location_words[1]}?")
    elif 'pnr' in command or any(char.isdigit() for char in command):
        suggestions.append("Did you mean to check PNR status?")
    elif any(word in command for word in ['booking', 'ticket', 'history']):
        suggestions.append("Did you mean to view your booking history?")
    
    return suggestions


def handle_unknown_command(suggestions):
    """Handle unknown command with suggestions"""
    response = 'I did not understand that command.'
    speak = 'Sorry, I did not understand that command.'
    
    if suggestions:
        response += ' ' + ' Or '.join(suggestions)
        speak += ' ' + suggestions[0]
    
    response += ' Try saying "Help" for available commands.'
    speak += ' Say help for available commands.'
    
    return {
        'response': response,
        'speak': speak
    }


def handle_greeting():
    """Handle greeting command"""
    return {
        'response': f'Hello {current_user.first_name}! 👋 I am Sarah, your voice assistant for train bookings. I can help you search trains, check PNR status, or view your bookings. What would you like to do?',
        'speak': f'Hello {current_user.first_name}! I am Sarah. How can I help you with your train bookings today?'
    }


def handle_help():
    """Handle help command"""
    return {
        'response': '''Hello! I am Sarah, your voice train booking assistant. Here are the commands I can help you with:

1. **Search Trains**: "Search trains from Mumbai to Delhi" or "Book from Bangalore to Chennai tomorrow"
2. **Check PNR**: "What is the status of PNR 1234567890" or "Check 1234567890"
3. **My Bookings**: "Show my bookings" or "My booking history"
4. **General**: "Help" or "What can you do?"

Just speak naturally! I can understand variations like:
- "Trains from X to Y tomorrow"
- "I want to go from X to Y"
- "Book my ticket from X to Y"
''',
        'speak': 'I am Sarah! I can help you search trains between any two stations, check your PNR status, or view your booking history. Just speak naturally about what you need. For example, you could say Search trains from Mumbai to Delhi or Check my booking status.'
    }

def process_train_search(source, destination, travel_date, voice_session):
    """Process train search command with intelligent station matching"""
    
    # Find source and destination stations with fuzzy matching
    source_stations = find_stations_fuzzy(source)
    dest_stations = find_stations_fuzzy(destination)
    
    # Handle source station not found
    if not source_stations:
        suggestions = suggest_stations(source)
        suggest_text = f" Did you mean {' or '.join(suggestions)}?" if suggestions else ""
        return {
            'response': f'I could not find a station matching "{source}".{suggest_text} Please try with a different name or station code.',
            'speak': f'I could not find the station {source}.{suggest_text} Please try again.'
        }
    
    # Handle destination station not found
    if not dest_stations:
        suggestions = suggest_stations(destination)
        suggest_text = f" Did you mean {' or '.join(suggestions)}?" if suggestions else ""
        return {
            'response': f'I could not find a station matching "{destination}".{suggest_text} Please try with a different name or station code.',
            'speak': f'I could not find the station {destination}.{suggest_text} Please try again.'
        }
    
    # Confirm if multiple matches found
    source_station = source_stations[0]
    dest_station = dest_stations[0]
    
    if len(source_stations) > 1 or len(dest_stations) > 1:
        # Using first match for now, but could ask for confirmation
        pass
    
    # Store search parameters in session
    voice_session['search'] = {
        'source': source_station['station_name'],
        'destination': dest_station['station_name'],
        'source_id': source_station['id'],
        'destination_id': dest_station['id'],
        'date': travel_date.strftime('%Y-%m-%d') if travel_date else None
    }
    
    # Find trains
    trains = search_trains(source_station['station_name'], dest_station['station_name'])
    
    if not trains:
        return {
            'response': f'No trains found between {source_station["station_name"]} and {dest_station["station_name"]} on the requested date.',
            'speak': f'No trains are currently available between {source_station["station_name"]} and {dest_station["station_name"]}. Please try a different date or route.'
        }
    
    # Format response with train details
    response_text = f'Found {len(trains)} trains from {source_station["station_name"]} to {dest_station["station_name"]}:\n\n'
    speak_text = f'I found {len(trains)} trains from {source_station["station_name"]} to {dest_station["station_name"]}. '
    
    train_list = []
    for i, train in enumerate(trains[:5], 1):  # Limit to 5 trains
        price = train.get("price_sleeper", 0) or train.get("price_ac_3", 0) or 0
        train_info = f'{i}. {train["train_name"]} ({train["train_number"]}) - Departs {train["departure_time"]}, Arrives {train["arrival_time"]}, From ₹{int(price)}'
        response_text += train_info + '\n'
        
        if i <= 3:  # Only speak first 3 trains
            speak_text += f'{train["train_name"]} departing at {train["departure_time"]}. '
        
        train_list.append({
            'schedule_id': train['schedule_id'],
            'train_number': train['train_number'],
            'train_name': train['train_name'],
            'departure': train['departure_time'],
            'arrival': train['arrival_time'],
            'price': price
        })
    
    if len(trains) > 3:
        speak_text += f'And {len(trains) - 3} more trains are available.'
    
    return {
        'response': response_text,
        'speak': speak_text,
        'action': 'show_trains',
        'data': {
            'trains': train_list,
            'source': source_station['station_name'],
            'destination': dest_station['station_name'],
            'date': travel_date.strftime('%Y-%m-%d') if travel_date else datetime.now().strftime('%Y-%m-%d')
        }
    }


def find_stations_fuzzy(search_term):
    """Find stations with fuzzy matching for better results"""
    if not search_term or len(search_term) < 2:
        return []
    
    # First try exact/close match
    stations = find_stations(search_term)
    
    if stations:
        return stations
    
    # If no results, try fuzzy matching with common stations
    common_stations = [
        ('Mumbai', ['mumbai', 'bombay', 'csmt', 'dadar']),
        ('New Delhi', ['delhi', 'ndls', 'new delhi']),
        ('Bangalore', ['bangalore', 'bengaluru', 'sbc']),
        ('Kolkata', ['kolkata', 'calcutta', 'hwh']),
        ('Chennai', ['chennai', 'madras', 'mas']),
        ('Hyderabad', ['hyderabad', 'hyderabad deccan', 'hyb']),
        ('Pune', ['pune', 'poona']),
        ('Ahmedabad', ['ahmedabad', 'adi']),
        ('Jaipur', ['jaipur', 'jp']),
        ('Lucknow', ['lucknow', 'lko'])
    ]
    
    search_lower = search_term.lower().strip()
    
    for station_name, aliases in common_stations:
        for alias in aliases:
            if alias in search_lower or search_lower in alias:
                return find_stations(station_name)
    
    return []


def suggest_stations(partial_name):
    """Suggest station names based on partial input"""
    if not partial_name or len(partial_name) < 2:
        return []
    
    common_stations = ['Mumbai', 'Delhi', 'Bangalore', 'Kolkata', 'Chennai', 'Hyderabad', 'Pune', 'Ahmedabad', 'Jaipur', 'Lucknow']
    
    suggestions = []
    search_lower = partial_name.lower()
    
    for station in common_stations:
        if search_lower in station.lower() or station.lower().startswith(search_lower):
            suggestions.append(station)
    
    return suggestions[:3]  # Return top 3 suggestions

def process_pnr_check(pnr_number):
    """Process PNR status check"""
    
    booking = get_booking_by_pnr(pnr_number)
    
    if not booking:
        return {
            'response': f'PNR {pnr_number} not found in our system.',
            'speak': f'Sorry, PNR {pnr_number} was not found.'
        }
    
    status_text = f'PNR {pnr_number}: {booking["booking_status"].title()}'
    speak_text = f'Your PNR {pnr_number} is {booking["booking_status"].replace("_", " ")}'
    
    return {
        'response': status_text,
        'speak': speak_text,
        'action': 'show_pnr',
        'data': {
            'pnr': pnr_number,
            'status': booking['booking_status'],
            'train': f'{booking["train_name"]} ({booking["train_number"]})'
        }
    }

def process_booking_history():
    """Process booking history request"""
    
    recent_bookings = get_user_bookings(current_user.id, 5)
    
    if not recent_bookings:
        return {
            'response': 'You have no booking history.',
            'speak': 'You have not made any bookings yet.'
        }
    
    response_text = f'Your recent {len(recent_bookings)} bookings:\\n\\n'
    speak_text = f'You have {len(recent_bookings)} recent bookings. '
    
    for i, booking in enumerate(recent_bookings, 1):
        booking_info = f'{i}. PNR {booking["pnr_number"]} - {booking["train_name"]} - {booking["booking_status"].title()}'
        response_text += booking_info + '\\n'
        
        if i <= 3:
            speak_text += f'PNR {booking["pnr_number"]} for {booking["train_name"]} is {booking["booking_status"].replace("_", " ")}. '
    
    return {
        'response': response_text,
        'speak': speak_text,
        'action': 'show_bookings'
    }

def extract_date_from_command(command):
    """Extract date from voice command with support for multiple formats"""
    command_lower = command.lower()
    
    # Today, tomorrow, day after patterns
    today = datetime.now().date()
    
    if any(word in command_lower for word in ['today', 'this day', 'same day']):
        return today
    
    if any(word in command_lower for word in ['tomorrow', 'next day', 'following day']):
        return today + timedelta(days=1)
    
    if any(word in command_lower for word in ['day after tomorrow', 'the day after']):
        return today + timedelta(days=2)
    
    # Next week patterns
    for i, day in enumerate(['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']):
        if day in command_lower:
            current_day = today.weekday()
            target_day = i
            days_ahead = target_day - current_day
            if days_ahead <= 0:
                days_ahead += 7
            return today + timedelta(days=days_ahead)
    
    # Relative day patterns (in 2 days, in 3 days, etc.)
    days_match = re.search(r'in\s+(\d+)\s+days?', command_lower)
    if days_match:
        return today + timedelta(days=int(days_match.group(1)))
    
    # Date patterns like "25th February", "Feb 25", "February 25"
    months = {
        'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
        'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12,
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'jun': 6, 'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
    }
    
    # "25th February" or "25 February"
    date_pattern = r'(\d{1,2})(?:st|nd|rd|th)?\s+(\w+)'
    date_match = re.search(date_pattern, command_lower)
    if date_match:
        day = int(date_match.group(1))
        month_str = date_match.group(2).lower()
        if month_str in months:
            month = months[month_str]
            try:
                return datetime(today.year, month, day).date()
            except ValueError:
                pass
    
    # "February 25" or "Feb 25"
    date_pattern2 = r'(\w+)\s+(\d{1,2})(?:st|nd|rd|th)?'
    date_match2 = re.search(date_pattern2, command_lower)
    if date_match2:
        month_str = date_match2.group(1).lower()
        day = int(date_match2.group(2))
        if month_str in months:
            month = months[month_str]
            try:
                return datetime(today.year, month, day).date()
            except ValueError:
                pass
    
    # Default to tomorrow if date mentioned but not understood
    if any(word in command_lower for word in ['date', 'when', 'on', 'at']):
        return today + timedelta(days=1)
    
    # Return today as default
    return today

def generate_voice_session_id():
    """Generate unique voice session ID"""
    import uuid
    return str(uuid.uuid4())

def get_or_create_voice_session(session_id):
    """Get or create voice session data"""
    if 'voice_sessions' not in session:
        session['voice_sessions'] = {}
    
    if session_id not in session['voice_sessions']:
        session['voice_sessions'][session_id] = {
            'created_at': datetime.now().isoformat(),
            'user_id': current_user.id,
            'search': {},
            'context': {}
        }
    
    return session['voice_sessions'][session_id]