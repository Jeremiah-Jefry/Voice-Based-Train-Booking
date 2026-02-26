from flask import render_template, request, jsonify, session, redirect, url_for
from flask_login import login_required, current_user
from app.voice import bp
from app.database import search_trains, find_stations, get_booking_by_pnr, get_user_bookings, create_booking, get_schedule_by_id
from datetime import datetime, timedelta
import re
import json
from difflib import SequenceMatcher
import hashlib
import random
import uuid

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
    
    # Check if we have a PNR waiting for confirmation
    if voice_session.get('pnr_to_confirm'):
        if command.lower() in ['yes', 'yeah', 'correct', 'right', 'yep', 'confirm', 'ok', 'okay', 'check it', 'go ahead']:
            pnr = voice_session.pop('pnr_to_confirm')
            return process_pnr_check(pnr)
        elif command.lower() in ['no', 'nope', 'wrong', 'incorrect', 'retry', 'again', 'restart']:
            voice_session.pop('pnr_to_confirm', None)
            voice_session['collecting_pnr'] = True
            voice_session['pnr_digits'] = []
            return handle_pnr_request()
    
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
        return process_train_search_smart(source, destination, travel_date, voice_session, user)
    
    elif intent['type'] == 'pnr_status':
        pnr_number = intent.get('pnr')
        return process_pnr_check(pnr_number)
    
    elif intent['type'] == 'booking_history':
        return process_booking_history(user)
    
    elif intent['type'] == 'pnr_request':
        # Mark that we're collecting PNR
        voice_session['collecting_pnr'] = True
        voice_session['pnr_digits'] = []
        return handle_pnr_request()
    
    # Check if we're collecting PNR digits
    elif voice_session.get('collecting_pnr'):
        return handle_pnr_digit_collection(command, voice_session)
    
    # Check if we're collecting booking details
    elif voice_session.get('booking_in_progress'):
        return handle_booking_details_collection(command, voice_session, user)
    
    elif intent['type'] == 'help':
        return handle_help_personalized(user)
    
    elif intent['type'] == 'follow_up':
        # Handle follow-up questions about last search
        return handle_follow_up_smart(command, voice_session)
    
    elif intent['type'] == 'book_now':
        return handle_booking_request_smart(command, voice_session, user)
    
    elif intent['type'] == 'unknown':
        suggestions = get_smart_suggestions(command, voice_session, user)
        return handle_unknown_command_smart(command, suggestions, voice_session)
    
    return {
        'response': 'I did not understand that. Could you rephrase?',
        'speak': 'I did not quite get that. Could you please rephrase your question?'
    }


def analyze_context(command, voice_session):
    """Analyze conversational context from history with comprehensive keyword understanding"""
    context = {
        'is_follow_up': False,
        'related_to_last': None,
        'conversation_length': len(voice_session.get('history', []))
    }
    
    # Comprehensive follow-up question keywords
    follow_up_keywords = [
        # Selection questions
        'which', 'which one', 'which train', 'what', 'what about',
        'first', 'second', 'third', 'fourth', 'fifth', 'last', 'option',
        # Price/cost questions
        'cheapest', 'cheap', 'affordable', 'budget', 'economical',
        'price', 'cost', 'fare', 'rate', 'charges', 'expensive',
        'low price', 'high price', 'how much',
        # Speed/timing questions  
        'fastest', 'fast', 'quick', 'quickest', 'speedy', 'slow',
        'when', 'what time', 'timing', 'schedule', 'departure', 'arrival',
        'duration', 'how long', 'travel time',
        # Quality questions
        'best', 'good', 'better', 'recommended', 'suggest',
        'comfortable', 'comfort', 'luxury', 'ac', 'sleeper',
        # Action questions
        'book', 'reserve', 'confirm', 'proceed', 'go ahead',
        'yes', 'okay', 'ok', 'sure',
        # Info questions
        'more', 'details', 'tell me', 'explain', 'about', 'info',
        'show', 'display', 'see'
    ]
    
    if any(keyword in command for keyword in follow_up_keywords):
        if voice_session.get('last_search'):
            context['is_follow_up'] = True
            context['related_to_last'] = 'search'
    
    return context


def detect_command_intent(command, context, voice_session):
    """Enhanced intent detection with comprehensive keyword understanding"""
    
    # Greeting patterns - only pure greetings, not travel commands
    greeting_keywords = [
        'hello', 'hi', 'hey', 'hii', 'helo', 'hellow',
        'good morning', 'good afternoon', 'good evening', 'good night',
        'namaste', 'namaskar', 'sup', 'what\'s up', 'whats up',
        'sarah', 'hey sarah', 'hi sarah', 'hello sarah',
        'greetings', 'howdy', 'yo'
    ]
    # Don't treat as greeting if it contains travel/booking keywords
    travel_keywords = ['train', 'ticket', 'book', 'from', 'to', 'search', 'travel', 'journey']
    has_travel_intent = any(tk in command for tk in travel_keywords)
    
    if any(keyword in command for keyword in greeting_keywords) and not has_travel_intent:
        return {'type': 'greeting'}
    
    # Help patterns - comprehensive variations
    help_keywords = [
        'help', 'help me', 'need help', 'can you help',
        'what can you do', 'what do you do', 'how do you work',
        'commands', 'command list', 'available commands',
        'guide', 'user guide', 'instructions', 'tutorial',
        'assist', 'assistance', 'support',
        'capabilities', 'features', 'functions',
        'how to', 'how can i', 'how do i',
        'what are your features', 'tell me about yourself'
    ]
    if any(keyword in command for keyword in help_keywords):
        return {'type': 'help'}
    
    # Booking patterns - check for booking intent with last search
    booking_keywords = [
        'book', 'booking', 'reserve', 'reservation',
        'confirm', 'confirm booking', 'proceed',
        'ticket', 'buy ticket', 'purchase',
        'yes book', 'book it', 'book this', 'book that',
        'i want to book', 'want to reserve',
        'make booking', 'make reservation',
        'go ahead', 'proceed booking'
    ]
    if any(keyword in command for keyword in booking_keywords) and voice_session.get('last_search'):
        return {'type': 'book_now'}
    
    # Booking history patterns - expanded
    history_keywords = [
        'my bookings', 'my booking', 'booking history',
        'my tickets', 'my ticket', 'show tickets',
        'past bookings', 'previous bookings', 'old bookings',
        'reservations', 'my reservations', 'show reservations',
        'booking list', 'ticket history', 'travel history',
        'show my bookings', 'view bookings', 'see bookings',
        'what did i book', 'what have i booked',
        'my travel', 'my trips', 'booked trains'
    ]
    if any(keyword in command for keyword in history_keywords):
        return {'type': 'booking_history'}
    
    # PNR status patterns - check with number first (10 consecutive digits only)
    pnr_match = re.search(r'\b(\d{10})\b', command)
    if pnr_match:
        pnr_number = pnr_match.group(1)
        return {'type': 'pnr_status', 'pnr': pnr_number}
    
    # PNR status request without number - comprehensive
    pnr_keywords = [
        'pnr', 'p n r', 'pnr status', 'pnr check',
        'check pnr', 'verify pnr', 'track pnr',
        'check status', 'booking status', 'ticket status',
        'check my pnr', 'check my booking', 'check my ticket',
        'verify booking', 'verify ticket', 'confirm status',
        'track booking', 'track ticket', 'where is my ticket',
        'status of booking', 'status of ticket',
        'my pnr status', 'what is my status'
    ]
    if any(keyword in command for keyword in pnr_keywords):
        return {'type': 'pnr_request'}
    
    # Train search patterns
    search_result = extract_train_search_params(command)
    if search_result:
        return {
            'type': 'search_trains',
            'source': search_result['source'],
            'destination': search_result['destination'],
            'date': search_result.get('date')
        }
    
    # Follow-up questions - expanded comprehension
    if context.get('is_follow_up'):
        follow_up_keywords = [
            'which', 'which one', 'which train',
            'first', 'second', 'third', 'last', 'option',
            'cheapest', 'cheap', 'affordable', 'budget', 'low price',
            'fastest', 'fast', 'quick', 'quickest', 'speedy',
            'price', 'cost', 'fare', 'rate', 'charges',
            'when', 'what time', 'timing', 'schedule',
            'best', 'good', 'better', 'recommended',
            'comfortable', 'comfort', 'luxury', 'ac',
            'more details', 'tell me more', 'explain'
        ]
        if any(keyword in command for keyword in follow_up_keywords):
            return {'type': 'follow_up'}
    
    return {'type': 'unknown'}


def handle_greeting_personalized(user):
    """Humanized personalized greetings - Like a real person"""
    # Safe fallback for user name
    user_name = getattr(user, 'first_name', None) or 'there'
    
    greetings = [
        f"Hey {user_name}! 👋 I'm Sarah, your personal train booking assistant. Ready to find the perfect train for your next trip?",
        f"Hi {user_name}! I'm Sarah. Planning to travel? Let me help you find and book amazing trains!",
        f"Welcome back, {user_name}! 🚂 I'm Sarah. Where would you like to go today?",
        f"Hey {user_name}! I'm Sarah, your travel buddy. All set to book your next train journey?",
        f"Hi there {user_name}! Sarah here! Looking to book a train? I've got incredible options waiting for you!",
        f"Welcome {user_name}! I'm Sarah. Let me help you discover the best trains and get you booked instantly!"
    ]
    
    greeting = random.choice(greetings)
    return {'response': greeting, 'speak': greeting}


def handle_follow_up_smart(command, voice_session):
    """Handle follow-ups with human-like responses and proactive booking suggestions"""
    last_search = voice_session.get('last_search', {})
    
    if not last_search:
        return {
            'response': 'I do not have a previous search. Tell me where you want to go!',
            'speak': 'Let me know your source and destination, and I will find great options for you.'
        }
    
    source = last_search.get('source', 'your source')
    dest = last_search.get('destination', 'your destination')
    
    # Humanized follow-up responses with proactive booking suggestions
    if any(word in command for word in ['which', 'first', 'best', 'recommend']):
        response = f"""Perfect! 🎯 For your {source} to {dest} route, here's my recommendation:

🥇 **Best Overall**: The first option - excellent timing and reliability
⏱️ **Fastest**: Rajdhani Express - gets you there in record time  
💰 **Budget-Friendly**: Sleeper class - amazing value for money
🌙 **Night Train**: Great if you prefer traveling overnight

Which one interests you? Just say "Book the first one" or "I want sleeper class" and I'll get you booked instantly! ✨"""
        speak = f"For your trip from {source} to {dest}, I recommend the first option - great departure time! Or if you want speed, go Rajdhani. Just tell me which one you like and say book it!"
        
    elif any(word in command for word in ['cheapest', 'price', 'cost', 'budget', 'affordable']):
        response = f"""Smart! 💡 Here's your money-saving breakdown for {source} to {dest}:

💰 **Most Economical**: Sleeper Class ⭐ BEST VALUE
💵 **Mid-Range**: General/Second Sitting - Great comfort!
💎 **Premium Comfort**: AC Classes - Maximum luxury

Sleeper class is unbeatable for price! Ready to book? Just say "Start sleeper booking" and I'll guide you through it!"""
        speak = f"Sleeper class offers unbeatable value from {source} to {dest}. Shall I start your booking right away? I can complete it in seconds!"
        
    elif any(word in command for word in ['fastest', 'quick', 'asap', 'urgent', 'time']):
        response = f"""Need speed? ⚡ Here are your fastest options {source} to {dest}:

🚀 **FASTEST**: Rajdhani Express - Premium express service!
⚡ **Quick**: Shatabdi Express - Daytime express
✈️ **Alternative**: Consider flights if extremely urgent

Rajdhani is your speed champion! Want me to book it now for you? Complete your booking in seconds!"""
        speak = f"Rajdhani is your fastest option from {source} to {dest}. Super quick ride! Should I book it for you right now?"
        
    elif any(word in command for word in ['comfort', 'class', 'ac', 'sleeper', 'chair']):
        response = f"""Comfort preferences for {source} to {dest}:

🌟 **Maximum Comfort**: AC First Class - Pure luxury
🛏️ **Great Comfort**: AC 2-Tier - All amenities
😴 **Budget Comfort**: Sleeper - Roomy and relaxing
👥 **Social Travel**: General/Chair Car - Most affordable

Tell me your preference and I'll instantly find and book the best option for you! What do you say? Ready to book? 🎟️"""
        speak = f"I can help you find the perfect comfort level from {source} to {dest}. AC first class is peak luxury, while sleeper offers great value. Which appeals to you? I can book it right away!"
        
    else:
        response = f"""Still exploring {source} to {dest}? Here's what I can do:

🔍 **Search More**: Find trains with different criteria
💺 **Compare Options**: I'll show you all details
✅ **Book Instantly**: Ready to buy your ticket
📱 **Track Journey**: Monitor your booking anytime

What's your next move? Let me help you get booked! 🚄"""
        speak = f"For your {source} to {dest} journey, I can show you more options, explain ticket details, or book instantly. What would you prefer? Ready to go?"
    
    return {'response': response, 'speak': speak}


def process_train_search_smart(source, destination, travel_date, voice_session, user):
    """Search with humanized responses and automatic booking guidance"""
    
    source_stations = find_stations_fuzzy(source)
    dest_stations = find_stations_fuzzy(destination)
    
    # If stations not found, ask for clarification
    if not source_stations:
        return {
            'response': f'🤔 I couldn\'t find "{source}" station. Could you clarify?\n\nTry: Mumbai, Delhi, Bangalore, Chennai, Kolkata, Hyderabad, Pune, Jaipur',
            'speak': f'I could not find {source} station. Please say the city name again. For example: Mumbai, Delhi, or Bangalore.'
        }
    
    if not dest_stations:
        return {
            'response': f'🤔 I couldn\'t find "{destination}" station. Could you clarify?\n\nTry: Mumbai, Delhi, Bangalore, Chennai, Kolkata, Hyderabad, Pune, Jaipur',
            'speak': f'I could not find {destination} station. Please say the destination city again.'
        }
    
    source_station = source_stations[0]
    dest_station = dest_stations[0]
    
    trains = search_trains(source_station['station_name'], dest_station['station_name'])
    
    if not trains:
        return {
            'response': f'Hmm, no trains available {source_station["station_name"]} → {dest_station["station_name"]} on that date. Try another date? 📅',
            'speak': f'No trains for that date. How about trying a different day?'
        }
    
    # Humanized, varied introductions
    intro_phrases = [
        f'Excellent! 🎉 I found {len(trains)} amazing trains for you! Let me show you...',
        f'Perfect timing! 🚆 {len(trains)} great options available!',
        f'Great news! ✨ I have {len(trains)} excellent choices for your journey!',
        f'Awesome! 🎯 {len(trains)} wonderful trains are running that day!'
    ]
    
    speak = random.choice(intro_phrases) + f' From {source_station["station_name"]} to {dest_station["station_name"]}. '
    
    response = f"""🎉 **Found {len(trains)} Trains from {source_station["station_name"]} to {dest_station["station_name"]}!**

💡 **To book instantly, say:** "Book 1" or "Book 2" etc.

"""
    
    trains_data = []
    for i, train in enumerate(trains[:6], 1):
        price = train.get('price_sleeper', 0) or train.get('price_ac_3', 0) or 0
        departure = train.get('departure_time', 'N/A')
        arrival = train.get('arrival_time', 'N/A')
        
        # Human-readable format with emojis
        emoji = '🏆' if i == 1 else '⭐' if i <= 3 else '👍'
        response += f"""{emoji} **Option {i}**: {train["train_name"]}
   ➜ Departs: {departure} | Arrives: {arrival}
   💰 From ₹{int(price)} | **Say "Book {i}"** to reserve!

"""
        
        if i <= 2:
            speak += f'{train["train_name"]} leaving at {departure}. '
        
        trains_data.append({
            'schedule_id': train.get('schedule_id'),
            'train_number': train.get('train_number'),
            'train_name': train.get('train_name'),
            'departure': train.get('departure_time'),
            'arrival': train.get('arrival_time'),
            'price': price
        })
    
    if len(trains) > 2:
        speak += f'Plus {len(trains) - 2} more! '
    
    # Store trains data in session for booking
    voice_session['last_search'] = {
        'source': source_station['station_name'],
        'destination': dest_station['station_name'],
        'date': travel_date,
        'trains_data': trains_data
    }
    
    # Proactive booking guidance
    if len(trains) <= 3:
        speak += f'Which one would you like to book? Say "Book 1", "Book 2", or ask for the cheapest or fastest option!'
    else:
        speak += f'I found {len(trains)} options! Say "Book 1" for the first train, or ask me for the cheapest or fastest option!'
    
    response += f"""

🎫 **Ready to Book?**
• Say: "**Book 1**" (or 2, 3, etc.)  
• Or ask: "Which is cheapest?" / "Which is fastest?"
• I'll guide you through passenger details step-by-step!"""
    
    return {
        'response': response,
        'speak': speak,
        'action': 'show_trains',
        'data': {
            'trains': trains_data,
            'source': source_station['station_name'],
            'destination': dest_station['station_name'],
            'ready_to_book': True
        }
    }


def handle_booking_request_smart(command, voice_session, user):
    """Intelligently handle booking requests with complete flow"""
    last_search = voice_session.get('last_search')
    
    if not last_search or not last_search.get('trains_data'):
        return {
            'response': 'Please search for trains first! Tell me: "Search trains from [city] to [city]"',
            'speak': 'Let me find trains for you first. Where do you want to travel from and to?'
        }
    
    # Try to extract train number from command
    train_number = extract_train_number_from_command(command)
    
    if not train_number or train_number > len(last_search['trains_data']):
        return {
            'response': f'Which train would you like to book? Say "Book 1", "Book 2", etc. (Options 1 to {len(last_search["trains_data"])})',
            'speak': f'Which train option? Say a number from 1 to {len(last_search["trains_data"])}.'
        }
    
    # Get selected train
    selected_train = last_search['trains_data'][train_number - 1]
    
    # Start booking process
    voice_session['booking_in_progress'] = {
        'train_option': train_number,
        'train_data': selected_train,
        'stage': 'collect_name',
        'source': last_search['source'],
        'destination': last_search['destination'],
        'date': last_search.get('date', datetime.now().date().isoformat()),
        'collected': {}
    }
    
    response = f"""🎫 **Booking {selected_train['train_name']}!**

📋 **Step 1 of 5**: What is your full name?

💡 Just say your name clearly, like: "My name is Rajesh Kumar" """
    
    speak = f"Great! I'm booking {selected_train['train_name']} for you. First, what is your full name?"
    
    return {'response': response, 'speak': speak}

def handle_booking_details_collection(command, voice_session, user):
    """Collect booking details step by step"""
    booking = voice_session['booking_in_progress']
    stage = booking['stage']
    collected = booking['collected']
    
    # Handle confirmation responses
    if command in ['yes', 'yeah', 'correct', 'right', 'yep', 'confirm', 'ok', 'okay']:
        if stage == 'confirm_all':
            return complete_booking(voice_session, user)
        
    elif command in ['no', 'nope', 'wrong', 'incorrect', 'retry']:
        if stage == 'confirm_all':
            booking['stage'] = 'collect_name'
            collected.clear()
            return {
                'response': "Let's start over. What is your full name?",
                'speak': "No problem. Let's try again. What is your name?"
            }
    
    # Collect based on stage
    if stage == 'collect_name':
        name = extract_name_from_command(command)
        if name:
            collected['name'] = name
            booking['stage'] = 'collect_age'
            return {
                'response': f"✓ Name: **{name}**\n\n📋 **Step 2 of 5**: How old are you?",
                'speak': f"Got it, {name}. What is your age?"
            }
        return {
            'response': "I didn't catch your name. Please say your full name clearly.",
            'speak': "Sorry, I didn't get your name. Please say it again."
        }
    
    elif stage == 'collect_age':
        age = extract_age_from_command(command)
        if age and 1 <= age <= 120:
            collected['age'] = age
            booking['stage'] = 'collect_gender'
            return {
                'response': f"✓ Age: **{age} years**\n\n📋 **Step 3 of 5**: What is your gender? (Male/Female/Other)",
                'speak': "What is your gender? Say male, female, or other."
            }
        return {
            'response': "I didn't get a valid age. Please say your age as a number.",
            'speak': "Please say your age. For example: twenty five."
        }
    
    elif stage == 'collect_gender':
        gender = extract_gender_from_command(command)
        if gender:
            collected['gender'] = gender
            booking['stage'] = 'collect_phone'
            return {
                'response': f"✓ Gender: **{gender}**\n\n📋 **Step 4 of 5**: What is your phone number? (10 digits)",
                'speak': "What is your phone number? Say all 10 digits."
            }
        return {
            'response': "Please say Male, Female, or Other.",
            'speak': "Say male, female, or other."
        }
    
    elif stage == 'collect_phone':
        phone = extract_phone_from_command(command)
        if phone and len(phone) == 10:
            collected['phone'] = phone
            booking['stage'] = 'collect_class'
            return {
                'response': f"✓ Phone: **{phone}**\n\n📋 **Step 5 of 5**: Which class?\n\n1. AC 1st Tier\n2. AC 2nd Tier\n3. AC 3rd Tier\n4. Sleeper\n5. Chair Car\n\nSay the class name or number.",
                'speak': "Which class would you prefer? Say sleeper, A C, or chair car."
            }
        return {
            'response': "Please say your 10-digit phone number clearly.",
            'speak': "Say your phone number, all 10 digits."
        }
    
    elif stage == 'collect_class':
        train_class = extract_class_from_command(command)
        if train_class:
            collected['class'] = train_class
            booking['stage'] = 'confirm_all'
            
            # Show summary for confirmation
            summary = f"""📋 **Booking Summary - Please Confirm**

🚂 Train: {booking['train_data']['train_name']}
📍 From: {booking['source']} → To: {booking['destination']}
📅 Date: {booking['date']}

👤 **Passenger Details:**
• Name: {collected['name']}
• Age: {collected['age']} years
• Gender: {collected['gender']}
• Phone: {collected['phone']}
• Class: {train_class.upper().replace('_', ' ')}

💰 Estimated Fare: ₹{int(booking['train_data'].get('price', 1000))}

**Say 'YES' to confirm or 'NO' to restart**"""
            
            speak = f"Confirming: {collected['name']}, {collected['age']} years old, {collected['gender']}, traveling in {train_class.replace('_', ' ')} class. Say yes to book, or no to change details."
            
            return {'response': summary, 'speak': speak}
        return {
            'response': "Please choose: AC 1, AC 2, AC 3, Sleeper, or Chair Car.",
            'speak': "Which class? Say A C, sleeper, or chair car."
        }
    
    return {
        'response': "Something went wrong. Let's start over. Say 'book trains' again.",
        'speak': "Sorry, let's try booking again."
    }

def complete_booking(voice_session, user):
    """Complete the booking by creating it in database"""
    booking_data = voice_session['booking_in_progress']
    collected = booking_data['collected']
    train = booking_data['train_data']
    
    try:
        # Create booking in database
        booking = create_booking(
            user_id=user.id,
            schedule_id=train['schedule_id'],
            passenger_name=collected['name'],
            passenger_age=collected['age'],
            passenger_gender=collected['gender'],
            passenger_phone=collected['phone'],
            travel_class=collected['class'],
            travel_date=booking_data['date']
        )
        
        if booking:
            # Clear booking in progress
            voice_session['booking_in_progress'] = None
            
            response = f"""✅ **BOOKING CONFIRMED!**

🎫 **PNR Number**: {booking['pnr']}
🪑 **Seat**: {booking['seat_number']}
💰 **Total Paid**: ₹{booking['total_amount']:.2f}

✨ Your ticket has been booked successfully!

📋 **View your booking:**
• Check **Booking History** to see all your tickets
• Download e-ticket: /e-ticket/{booking['booking_id']}
• Track status anytime with PNR: {booking['pnr']}

📧 Confirmation sent to your email!
🎉 Have a wonderful journey!"""
            
            speak = f"Congratulations! Your booking is confirmed. P N R number is {' '.join(booking['pnr'])}. Seat number {booking['seat_number']}. Total amount {int(booking['total_amount'])} rupees. You can check your booking history to see all details. Have a great journey!"
            
            return {
                'response': response,
                'speak': speak,
                'action': 'booking_complete',
                'data': booking
            }
        else:
            voice_session['booking_in_progress'] = None
            return {
                'response': "❌ Booking failed. Please try again or use the web form.",
                'speak': "Sorry, the booking could not be completed. Please try again."
            }
    except Exception as e:
        print(f"Booking error: {e}")
        import traceback
        traceback.print_exc()
        voice_session['booking_in_progress'] = None
        return {
            'response': f"❌ Error: {str(e)}. Please try booking through the website.",
            'speak': "Sorry, there was an error. Please use the website to book."
        }

def extract_name_from_command(command):
    """Extract name from command"""
    # Remove common phrases
    command = re.sub(r'^(my name is|i am|i\'m|this is|name is|it\'s|its)\s+', '', command, flags=re.IGNORECASE)
    # Remove trailing phrases
    command = re.sub(r'\s+(book|booking|train|ticket)$', '', command, flags=re.IGNORECASE)
    name = command.strip().title()
    return name if len(name) >= 3 else None

def extract_age_from_command(command):
    """Extract age from command"""
    # Look for numeric age
    match = re.search(r'\b(\d{1,3})\b', command)
    if match:
        return int(match.group(1))
    
    # Handle word numbers for age
    words_to_nums = {
        'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
        'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
        'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14, 'fifteen': 15,
        'sixteen': 16, 'seventeen': 17, 'eighteen': 18, 'nineteen': 19, 'twenty': 20,
        'twenty one': 21, 'twenty two': 22, 'twenty three': 23, 'twenty four': 24, 'twenty five': 25,
        'thirty': 30, 'forty': 40, 'fifty': 50, 'sixty': 60, 'seventy': 70, 'eighty': 80, 'ninety': 90
    }
    
    for word, num in words_to_nums.items():
        if word in command.lower():
            return num
    
    return None

def extract_gender_from_command(command):
    """Extract gender from command"""
    command = command.lower()
    if any(word in command for word in ['male', 'man', 'boy', 'mr', 'gentleman']):
        return 'male'
    elif any(word in command for word in ['female', 'woman', 'girl', 'lady', 'mrs', 'miss', 'ms']):
        return 'female'
    elif any(word in command for word in ['other', 'prefer not', 'non binary', 'transgender']):
        return 'other'
    return None

def extract_phone_from_command(command):
    """Extract phone number from command"""
    # Extract digits
    digits = ''.join(re.findall(r'\d', command))
    return digits if len(digits) == 10 else None

def extract_class_from_command(command):
    """Extract train class from command"""
    command = command.lower()
    if 'ac 1' in command or 'ac1' in command or 'first tier' in command or '1st' in command:
        return 'ac_1'
    elif 'ac 2' in command or 'ac2' in command or 'second tier' in command or '2nd' in command:
        return 'ac_2'
    elif 'ac 3' in command or 'ac3' in command or 'third tier' in command or '3rd' in command or 'ac' in command:
        return 'ac_3'
    elif 'sleeper' in command or 'sleep' in command or 'sl' in command:
        return 'sleeper'
    elif 'chair' in command or 'cc' in command or 'sitting' in command:
        return 'chair_car'
    elif 'second sitting' in command or '2s' in command:
        return 'second_sitting'
    return None


def extract_train_number_from_command(command):
    """Extract train number (1-6) from booking command"""
    # Look for patterns like "book 1", "option 2", "choose 3"
    match = re.search(r'(?:book|option|choose|the|first|second|third|fourth|fifth|sixth)\s*(\d|first|second|third|fourth|fifth|sixth)', command, re.IGNORECASE)
    
    if match:
        text = match.group(1).lower()
        number_map = {
            '1': 1, 'first': 1, 'one': 1,
            '2': 2, 'second': 2, 'two': 2,
            '3': 3, 'third': 3, 'three': 3,
            '4': 4, 'fourth': 4, 'four': 4,
            '5': 5, 'fifth': 5, 'five': 5,
            '6': 6, 'sixth': 6, 'six': 6
        }
        return number_map.get(text)
    
    return None


def handle_help_personalized(user):
    """Humanized help with personality and examples"""
    # Safe fallback for user name
    user_name = getattr(user, 'first_name', None) or 'there'
    
    responses = [
        f"""Hi {user_name}! 👋 I'm **Sarah**, your AI train booking assistant! Here's how I can transform your travel:

🚂 **Search & Book Trains**
   "Book trains from Mumbai to Delhi"
   "I need a sleeper ticket tomorrow"
   "Find trains from Bangalore to Pune"

🔍 **I Understand Natural Speech**
   "Need to go from Mumbai to Chennai"
   "Trains from Delhi to Jaipur for tomorrow"
   "Cheapest option from Hyderabad to Goa"

💡 **Smart Booking Tips**
   After searching, ask: "Which is fastest?" "Cheapest option?" "Show AC trains?"
   Then: "Book the first one" or "I want sleeper class booking"
   
📱 **Check Your Tickets**
   "Show my bookings" - See all your tickets
   "Check PNR 1234567890" - Verify any booking status

✨ **The Best Part?** I'll guide you through booking in SECONDS with proactive suggestions! Just tell me naturally what you want - cheapest? fastest? most comfortable? I'll book it for you automatically!""",
        
        f"""Hey {user_name}! 🎯 I'm **Sarah**, here to make train booking super easy!

**What I Can Do:**
✅ Find trains between ANY two Indian cities
✅ Search by speed, price, or comfort - your choice!
✅ Book tickets instantly with just your details
✅ Check booking status with PNR numbers
✅ Show your booking history anytime

**How to Talk to Me:**
Just speak naturally! Examples:
• "Search trains from Mumba to Delhi tomorrow"
• "Book the cheapest option"
• "I want Rajdhani - fastest speed"
• "Show me sleeper class prices"

**The Magic Part:** Once you search, I'll suggest the best options and book for you instantly! No forms, no hassle. The future of travel is here! 🚄✨"""
    ]
    
    response = random.choice(responses)
    speak = f"Hi {user_name}! I'm Sarah, your voice booking assistant. I can help you search trains by saying things like: Search trains from Mumbai to Delhi. Then ask me about prices or speed, and I'll book for you instantly!"
    
    return {'response': response, 'speak': speak}


def handle_unknown_command_smart(command, suggestions, voice_session):
    """Smart unknown command handling with contextual suggestions"""
    
    responses = [
        f"Hmm, I didn't quite catch that. 🤔 {' Or, ' + suggestions[0] if suggestions else 'Tell me where you want to travel?'}",
        f"Sorry, could you rephrase that? 😊 {' Maybe you meant: ' + suggestions[0] if suggestions else 'Say where you want to go?'}",
        f"I'm still learning! 📚 {' Did you mean: ' + suggestions[0] if suggestions else 'Let me know your travel route?'}"
    ]
    
    speak = f"I didn't understand that. {suggestions[0] if suggestions else 'Tell me where you want to travel and I will find amazing trains for you!'}"
    
    return {
        'response': random.choice(responses),
        'speak': speak
    }


def get_smart_suggestions(command, voice_session, user):
    """Provide intelligent, proactive suggestions"""
    suggestions = []
    
    # Check for location words
    station_keywords = ['mumbai', 'delhi', 'bangalore', 'kolkata', 'chennai', 'hyderabad', 'pune', 'ahmedabad', 'jaipur', 'lucknow']
    location_words = [word for word in command.split() if word in station_keywords]
    
    if len(location_words) >= 2:
        suggestions.append(f"Did you want to search trains from {location_words[0]} to {location_words[1]}?")
    elif len(location_words) == 1:
        suggestions.append(f"Looking to travel from or to {location_words[0]}?")
    
    # Check for booking intent
    if any(word in command for word in ['book', 'reserve', 'ticket']):
        if voice_session.get('last_search'):
            suggestions.append(f"Ready to book your {voice_session['last_search']['source']} to {voice_session['last_search']['destination']} trip?")
        else:
            suggestions.append("First, tell me where you want to go and I'll find trains!")
    
    elif any(char.isdigit() for char in command):
        suggestions.append("Did you want to check a PNR status?")
    
    elif any(word in command for word in ['history', 'previous', 'past']):
        suggestions.append("Want to see your booking history?")
    
    return suggestions[:2]


def extract_train_search_params(command):
    """Extract train search parameters from comprehensive natural language variations"""
    
    # Comprehensive search patterns - handles many natural variations
    search_patterns = [
        # "I need to search/find train from X to Y" - PRIORITY
        r'(?:i\s+)?(?:need|want|would like)?\s*(?:to\s+)?(?:search|find|look for|check)\s+(?:for\s+)?(?:a\s+)?(?:train[s]?|ticket[s]?)\s+from\s+([a-z\s]+)\s+(?:to|till)\s+([a-z\s]+)',
        
        # "search/find trains from X to Y"
        r'(?:search|find|look for|look|show|check)\s+(?:me\s+)?(?:for\s+)?(?:train[s]?|ticket[s]?)\s+(?:from|for)\s+([a-z\s]+)\s+(?:to|till)\s+([a-z\s]+)',
        
        # "need to book/reserve train from X to Y"
        r'(?:need|want|would like|wish)\s+to\s+(?:book|reserve|get|buy|search)\s+(?:a\s+)?(?:train|ticket)\s+from\s+([a-z\s]+)\s+(?:to|till)\s+([a-z\s]+)',
        
        # "book/reserve train from X to Y"
        r'(?:book|reserve|get|buy)\s+(?:me\s+)?(?:a\s+)?(?:train|ticket)\s+from\s+([a-z\s]+)\s+(?:to|till)\s+([a-z\s]+)',
        
        # "I need/want to book from X to Y"
        r'(?:i\s+)?(?:need|want|would like)\s+(?:to\s+)?(?:book|reserve|get)\s+(?:train[s]?|ticket[s]?)?\s*from\s+([a-z\s]+)\s+(?:to|till)\s+([a-z\s]+)',
        
        # "I need/want to go/travel from X to Y"
        r'(?:i\s+)?(?:need|want|would like|wish|plan)\s+(?:to\s+)?(?:go|travel|visit|reach|journey)\s+(?:from|for)\s+([a-z\s]+)\s+(?:to|till)\s+([a-z\s]+)',
        
        # "trains/tickets from X to Y"
        r'(?:train[s]?|ticket[s]?)\s+(?:from|for)\s+([a-z\s]+)\s+(?:to|till)\s+([a-z\s]+)',
        
        # Direct format "from X to Y"
        r'(?:going\s+|traveling\s+)?from\s+([a-z\s]+)\s+(?:to|till)\s+([a-z\s]+)',
        
        # "I'm going/traveling to Y from X"
        r'(?:i\'m|i am|im)\s+(?:going|traveling|heading|moving)\s+to\s+([a-z\s]+)\s+from\s+([a-z\s]+)',
        
        # "take me from X to Y"
        r'(?:take me|get me)\s+from\s+([a-z\s]+)\s+to\s+([a-z\s]+)',
        
        # Simple "X to Y" pattern (LAST - most ambiguous)
        r'([a-z\s]+)\s+(?:to|till)\s+([a-z\s]+)',
    ]
    
    for pattern in search_patterns:
        match = re.search(pattern, command, re.IGNORECASE)
        if match:
            # Handle patterns with swapped order (destination before source)
            if 'moving to' in command or 'going to' in command or 'traveling to' in command:
                destination = match.group(1).strip()
                source = match.group(2).strip()
            else:
                source = match.group(1).strip()
                destination = match.group(2).strip()
            
            # Skip if too short
            if len(source) < 3 or len(destination) < 3:
                continue
            
            # Skip if matches common words that aren't cities
            skip_words = ['hello', 'hi', 'hey', 'what', 'can', 'you', 'help', 'do', 'how', 
                         'who', 'why', 'when', 'where', 'the', 'this', 'that', 'need', 'want',
                         'book', 'search', 'find', 'train', 'ticket', 'show', 'get', 'about',
                         'tell', 'me', 'for', 'please', 'is', 'are', 'it', 'a', 'an']
            
            # Clean up source and destination
            source_words = [w for w in source.lower().split() if w not in skip_words]
            dest_words = [w for w in destination.lower().split() if w not in skip_words]
            
            if not source_words or not dest_words:
                continue
            
            # Reconstruct cleaned names
            source = ' '.join(source_words)
            destination = ' '.join(dest_words)
            
            # Skip if source and destination are the same
            if source.lower() == destination.lower():
                continue
            
            # Extract date if present
            travel_date = extract_date_from_command(command)
            
            return {
                'source': source.title(),
                'destination': destination.title(),
                'date': travel_date
            }
    
    return None


def find_stations_fuzzy(search_term):
    """Find stations with fuzzy matching for better results"""
    if not search_term or len(search_term) < 2:
        return []
    
    stations = find_stations(search_term)
    
    if stations:
        return stations
    
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
    
    return suggestions[:3]


def handle_pnr_request():
    """Ask user for PNR number with clear instructions"""
    responses = [
        "I can check your PNR status! Please say all 10 digits clearly, one after another.",
        "Sure! Please speak your 10-digit PNR number slowly and clearly.",
        "I'll help you check! Say your PNR number - all 10 digits, nice and clear.",
        "Let me look that up! Please say the 10 digits of your PNR number."
    ]
    
    response = random.choice(responses)
    speak = f"{response} For example: one two three four five six seven eight nine zero."
    
    return {
        'response': f"📋 {response}\n\n💡 **Important**: Say each digit separately and clearly.\n\nExample: Say \"one two three four five six seven eight nine zero\" for PNR 1234567890.\n\nAlternatively, you can say the full number: \"Check PNR 1234567890\"",
        'speak': speak
    }

def handle_pnr_digit_collection(command, voice_session):
    """Collect PNR digits step by step with confirmation"""
    # Extract all digits from command
    digits = extract_digits_from_speech(command)
    
    if not digits:
        return {
            'response': "I didn't catch any digits. Please say the PNR number clearly, digit by digit.",
            'speak': "I didn't hear any numbers. Please say your PNR digits again."
        }
    
    # If we got all 10 digits at once
    if len(digits) == 10:
        pnr = ''.join(digits)
        # Confirm before checking
        voice_session['pnr_to_confirm'] = pnr
        voice_session['collecting_pnr'] = False
        
        return {
            'response': f"📋 I heard PNR: **{pnr}**\n\nIs this correct? Say 'yes' to check, or 'no' to try again.",
            'speak': f"I heard P N R {' '.join(digits)}. Is that correct? Say yes to check, or no to try again."
        }
    
    # If got partial digits, ask for remaining
    voice_session.setdefault('pnr_digits', []).extend(digits)
    collected = voice_session['pnr_digits'][:10]  # Only keep first 10
    remaining = 10 - len(collected)
    
    if remaining > 0:
        return {
            'response': f"Got {len(collected)} digits so far: **{' '.join(collected)}**\n\nPlease say the remaining {remaining} digits.",
            'speak': f"I have {len(collected)} digits. Please say the remaining {remaining} digits."
        }
    else:
        # Got all 10 digits
        pnr = ''.join(collected[:10])
        voice_session['pnr_to_confirm'] = pnr
        voice_session['collecting_pnr'] = False
        voice_session['pnr_digits'] = []
        
        return {
            'response': f"📋 Complete PNR: **{pnr}**\n\nIs this correct? Say 'yes' to check, or 'no' to try again.",
            'speak': f"I have P N R {' '.join(pnr)}. Is that correct? Say yes to check."
        }

def extract_digits_from_speech(command):
    """Extract digits from speech, handling both numeric and word forms"""
    word_to_digit = {
        'zero': '0', 'oh': '0', 'o': '0',
        'one': '1', 'won': '1',
        'two': '2', 'to': '2', 'too': '2',
        'three': '3', 'tree': '3',
        'four': '4', 'for': '4',
        'five': '5',
        'six': '6', 'sex': '6',
        'seven': '7',
        'eight': '8', 'ate': '8',
        'nine': '9', 'niner': '9'
    }
    
    digits = []
    words = command.lower().split()
    
    for word in words:
        # Check if word is a digit word
        if word in word_to_digit:
            digits.append(word_to_digit[word])
        # Check if word is already a digit
        elif word.isdigit():
            digits.extend(list(word))
    
    # Also check for continuous digit strings
    digit_matches = re.findall(r'\d+', command)
    for match in digit_matches:
        digits.extend(list(match))
    
    return digits


def process_pnr_check(pnr_number):
    """Process PNR status check with complete details"""
    
    booking = get_booking_by_pnr(pnr_number)
    
    if not booking:
        return {
            'response': f'🔍 PNR **{pnr_number}** not found in our system.\n\nPlease check the number and try again, or say "check another PNR" to enter a new one.',
            'speak': f'Sorry, P N R {" ".join(pnr_number)} was not found. Would you like to try another number?'
        }
    
    status_emoji = {
        'confirmed': '✅',
        'pending': '⏳',
        'cancelled': '❌',
        'on_board': '🚂'
    }
    emoji = status_emoji.get(booking['booking_status'], '📋')
    
    # Build comprehensive response
    response = f"""{emoji} **PNR {pnr_number}: {booking['booking_status'].upper()}**

🚂 **Train**: {booking['train_number']} - {booking['train_name']}
📍 **Route**: {booking.get('source_station', 'N/A')} → {booking.get('dest_station', 'N/A')}
📅 **Date**: {booking['travel_date']}
🎫 **Class**: {booking['train_class'].upper().replace('_', ' ')}
👤 **Passenger**: {booking['passenger_name']} ({booking['passenger_age']}Y, {booking['passenger_gender'].upper()})
💰 **Fare**: ₹{booking['total_amount']}

💡 View full e-ticket at /e-ticket/{booking['id']}"""
    
    speak_text = f"Your P N R is {booking['booking_status']}. Train {booking['train_number']} {booking['train_name']}, traveling on {booking['travel_date']}, passenger {booking['passenger_name']}. Total fare is {int(booking['total_amount'])} rupees."
    
    return {
        'response': response,
        'speak': speak_text,
        'action': 'show_pnr',
        'data': {
            'pnr': pnr_number,
            'booking_id': booking['id'],
            'status': booking['booking_status'],
            'train': f"{booking['train_name']} ({booking['train_number']})",
            'passenger': booking['passenger_name']
        }
    }


def process_booking_history(user):
    """Process booking history with humanized format"""
    
    recent_bookings = get_user_bookings(user.id, 5)
    
    if not recent_bookings:
        return {
            'response': 'No bookings yet! 🚄 Ready to plan your first trip? Just tell me where you want to go!',
            'speak': 'You have not made any bookings yet. Let me help you find and book amazing trains!'
        }
    
    response_text = f'📋 **Your Recent {len(recent_bookings)} Bookings**:\n\n'
    speak_text = f'You have {len(recent_bookings)} recent bookings. '
    
    for i, booking in enumerate(recent_bookings, 1):
        status_icon = '✅' if booking['booking_status'] == 'confirmed' else '⏳'
        booking_info = f'{i}. {status_icon} PNR {booking["pnr_number"]} - {booking["train_name"]} [{booking["booking_status"].title()}]'
        response_text += booking_info + '\n'
        
        if i <= 3:
            speak_text += f'PNR {booking["pnr_number"]} for {booking["train_name"]} is {booking["booking_status"].replace("_", " ")}. '
    
    response_text += '\n💡 Want to book another trip? Just tell me where you want to go!'
    
    return {
        'response': response_text,
        'speak': speak_text,
        'action': 'show_bookings'
    }


def extract_date_from_command(command):
    """Extract date from voice command with support for multiple formats"""
    command_lower = command.lower()
    
    today = datetime.now().date()
    
    if any(word in command_lower for word in ['today', 'this day', 'same day']):
        return today
    
    if any(word in command_lower for word in ['tomorrow', 'next day', 'following day']):
        return today + timedelta(days=1)
    
    if any(word in command_lower for word in ['day after tomorrow', 'the day after']):
        return today + timedelta(days=2)
    
    for i, day in enumerate(['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']):
        if day in command_lower:
            current_day = today.weekday()
            target_day = i
            days_ahead = target_day - current_day
            if days_ahead <= 0:
                days_ahead += 7
            return today + timedelta(days=days_ahead)
    
    days_match = re.search(r'in\s+(\d+)\s+days?', command_lower)
    if days_match:
        return today + timedelta(days=int(days_match.group(1)))
    
    months = {
        'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
        'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12,
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'jun': 6, 'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
    }
    
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
    
    return today


def generate_voice_session_id():
    """Generate unique voice session ID"""
    return str(uuid.uuid4())


def get_or_create_voice_session(session_id, user_id):
    """Get or create voice session data with memory"""
    if session_id not in VOICE_SESSIONS:
        VOICE_SESSIONS[session_id] = {
            'created_at': datetime.now().isoformat(),
            'user_id': user_id,
            'history': [],
            'last_search': {},
            'context': {},
            'booking_in_progress': None
        }
    
    return VOICE_SESSIONS[session_id]
