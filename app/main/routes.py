from flask import render_template, request, jsonify, session, redirect, url_for, flash
from flask_login import login_required, current_user
from app.main import bp
from app.database import search_trains, get_user_bookings, get_booking_by_pnr, get_stations_by_type, get_train_schedules_with_routes, get_schedule_by_id, create_booking, get_booking_details
from datetime import datetime, timedelta

@bp.route('/')
def index():
    return render_template('main/index.html')

@bp.route('/dashboard')
@login_required
def dashboard():
    # Get user's recent bookings
    recent_bookings = get_user_bookings(current_user.id, 5)
    
    # Get upcoming journeys (filter by travel date >= today)
    upcoming_journeys = [booking for booking in recent_bookings 
                        if booking.get('travel_date') and 
                        datetime.strptime(booking['travel_date'], '%Y-%m-%d').date() >= datetime.now().date()]
    
    return render_template('main/dashboard.html', 
                         recent_bookings=recent_bookings,
                         upcoming_journeys=upcoming_journeys[:3])

@bp.route('/search')
def search():
    return render_template('main/search.html')

@bp.route('/search-trains', methods=['POST'])
def search_trains_endpoint():
    data = request.get_json() if request.is_json else request.form
    
    source = data.get('source')
    destination = data.get('destination') 
    travel_date = data.get('travel_date')
    train_class = data.get('train_class', 'sleeper')
    
    if not all([source, destination, travel_date]):
        return jsonify({'error': 'Missing required search parameters'}), 400
    
    try:
        travel_date = datetime.strptime(travel_date, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format'}), 400
    
    # Search trains using SQLite3
    train_results = search_trains(source, destination, travel_date)
    
    if not train_results:
        return jsonify({'error': 'No trains found between these stations'}), 404
    
    # Format results for response
    formatted_results = []
    for train in train_results:
        result = {
            'train_number': train['train_number'],
            'train_name': train['train_name'],
            'train_type': train['train_type'],
            'departure_time': train['departure_time'],
            'arrival_time': train['arrival_time'],
            'duration': calculate_duration(train['departure_time'], train['arrival_time']),
            'price': get_class_price(train, train_class),
            'available_seats': get_available_capacity(train, train_class),
            'schedule_id': train['schedule_id']
        }
        formatted_results.append(result)
    
    return jsonify({
        'trains': formatted_results,
        'search_params': {
            'source': train_results[0]['source_name'] if train_results else source,
            'destination': train_results[0]['dest_name'] if train_results else destination,
            'date': travel_date.strftime('%Y-%m-%d'),
            'class': train_class
        }
    })

@bp.route('/book/<int:schedule_id>')
@login_required
def book_ticket(schedule_id):
    travel_date = request.args.get('date')
    train_class = request.args.get('class', 'sleeper')
    
    if not travel_date:
        flash('Please provide a travel date', 'error')
        return redirect(url_for('main.search'))
    
    try:
        travel_date_obj = datetime.strptime(travel_date, '%Y-%m-%d').date()
    except ValueError:
        flash('Invalid travel date', 'error')
        return redirect(url_for('main.search'))
    
    # Fetch schedule details
    schedule = get_schedule_by_id(schedule_id)
    
    if not schedule:
        flash('Train schedule not found', 'error')
        return redirect(url_for('main.search'))
    
    # Get price for selected class
    price_map = {
        'ac_1': schedule.get('price_ac_1'),
        'ac_2': schedule.get('price_ac_2'),
        'ac_3': schedule.get('price_ac_3'),
        'sleeper': schedule.get('price_sleeper'),
        'chair_car': schedule.get('price_chair_car'),
        'second_sitting': schedule.get('price_second_sitting')
    }
    ticket_price = price_map.get(train_class, 0.0) or 0.0
    gst_amount = ticket_price * 0.05
    total_amount = ticket_price + gst_amount
    
    return render_template('main/booking.html',
                         schedule=schedule,
                         travel_date=travel_date_obj,
                         train_class=train_class,
                         ticket_price=ticket_price,
                         gst_amount=gst_amount,
                         total_amount=total_amount)


@bp.route('/submit-booking', methods=['POST'])
@login_required
def submit_booking():
    data = request.get_json() if request.is_json else request.form
    
    schedule_id = data.get('schedule_id')
    passenger_name = data.get('passenger_name')
    passenger_age = data.get('passenger_age')
    passenger_gender = data.get('passenger_gender')
    passenger_phone = data.get('passenger_phone')
    travel_class = data.get('travel_class')
    travel_date = data.get('travel_date')
    
    # Validate required fields
    if not all([schedule_id, passenger_name, passenger_age, passenger_gender, passenger_phone, travel_class, travel_date]):
        return jsonify({'success': False, 'error': 'All fields are required'}), 400
    
    # Create booking
    booking = create_booking(
        user_id=current_user.id,
        schedule_id=int(schedule_id),
        passenger_name=passenger_name,
        passenger_age=int(passenger_age),
        passenger_gender=passenger_gender,
        passenger_phone=passenger_phone,
        travel_class=travel_class,
        travel_date=travel_date
    )
    
    if not booking:
        return jsonify({'success': False, 'error': 'Failed to create booking'}), 500
    
    return jsonify({
        'success': True,
        'booking': booking,
        'message': 'Booking confirmed successfully!',
        'redirect_url': url_for('main.view_eticket', booking_id=booking['booking_id'])
    })

@bp.route('/e-ticket/<int:booking_id>')
@login_required
def view_eticket(booking_id):
    """Display e-ticket for a confirmed booking"""
    # Get complete booking details with train information
    booking = get_booking_details(booking_id)
    
    if not booking:
        flash('Booking not found', 'error')
        return redirect(url_for('main.booking_history'))
    
    # Verify booking belongs to current user
    if booking['user_id'] != current_user.id:
        flash('Unauthorized access', 'error')
        return redirect(url_for('main.booking_history'))
    
    return render_template('main/eticket.html', booking=booking)

@bp.route('/booking-history')
@login_required
def booking_history():
    # Get user bookings from database
    bookings_data = get_user_bookings(current_user.id)
    
    return render_template('main/booking_history.html', bookings=bookings_data or [])

@bp.route('/pnr-status')
def pnr_status():
    pnr = request.args.get('pnr')
    
    if not pnr:
        return render_template('main/pnr_status.html')
    
    booking = get_booking_by_pnr(pnr)
    
    if not booking:
        return render_template('main/pnr_status.html', error='PNR not found')
    
    return render_template('main/pnr_status.html', booking=booking)

def get_class_price(train_data, train_class):
    """Get price for specific class"""
    price_map = {
        'ac_1': train_data.get('price_ac_1'),
        'ac_2': train_data.get('price_ac_2'),
        'ac_3': train_data.get('price_ac_3'),
        'sleeper': train_data.get('price_sleeper'),
        'chair_car': train_data.get('price_chair_car'),
        'second_sitting': train_data.get('price_second_sitting')
    }
    return price_map.get(train_class.lower(), 0.0)

def get_available_capacity(train_data, train_class):
    """Get available capacity for specific class"""
    capacity_map = {
        'ac_1': train_data.get('capacity_ac_1', 0),
        'ac_2': train_data.get('capacity_ac_2', 0),
        'ac_3': train_data.get('capacity_ac_3', 0),
        'sleeper': train_data.get('capacity_sleeper', 0),
        'chair_car': train_data.get('capacity_chair_car', 0),
        'second_sitting': train_data.get('capacity_second_sitting', 0)
    }
    return capacity_map.get(train_class.lower(), 0)

def calculate_duration(departure_time, arrival_time):
    """Calculate journey duration"""
    try:
        # Parse time strings
        dep_time = datetime.strptime(departure_time, '%H:%M').time() if isinstance(departure_time, str) else departure_time
        arr_time = datetime.strptime(arrival_time, '%H:%M').time() if isinstance(arrival_time, str) else arrival_time
        
        departure = datetime.combine(datetime.today(), dep_time)
        arrival = datetime.combine(datetime.today(), arr_time)
        
        # Handle overnight journeys
        if arrival < departure:
            arrival += timedelta(days=1)
        
        duration = arrival - departure
        hours = duration.seconds // 3600
        minutes = (duration.seconds % 3600) // 60
        
        return f"{hours}h {minutes}m"
    except Exception:
        return "N/A"

@bp.route('/all-trains')
def all_trains():
    """Display all trains with their schedules and routes"""
    schedules = get_train_schedules_with_routes()
    
    # Group by train for better display
    trains_dict = {}
    for schedule in schedules:
        train_id = schedule['train_id']
        if train_id not in trains_dict:
            trains_dict[train_id] = {
                'train_number': schedule['train_number'],
                'train_name': schedule['train_name'],
                'train_type': schedule['train_type'],
                'schedules': []
            }
        
        trains_dict[train_id]['schedules'].append(schedule)
    
    trains_list = list(trains_dict.values())
    
    return render_template('main/train_schedules.html', trains=trains_list)

@bp.route('/api/stations')
def get_stations():
    """Return list of all stations as JSON"""
    search_term = request.args.get('q', '')
    stations = get_stations_by_type(search_term if search_term else None)
    
    return jsonify({
        'stations': [
            {
                'station_code': s['station_code'],
                'station_name': s['station_name'],
                'city': s['city']
            }
            for s in stations
        ]
    })
