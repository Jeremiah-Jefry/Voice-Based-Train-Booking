"""
SQLite3 Database operations for Voice Train Booking Platform
"""

import sqlite3
import hashlib
import secrets
from datetime import datetime
from flask import g
import os

DATABASE = 'train_booking.db'

def get_db():
    """Get database connection"""
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e=None):
    """Close database connection"""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_database():
    """Initialize database with tables"""
    if os.path.exists(DATABASE):
        print("Database already exists")
        return
        
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Create tables
    create_tables(cursor)
    
    # Insert sample data
    insert_sample_data(cursor)
    
    conn.commit()
    conn.close()
    print("Database initialized with sample data")

def create_tables(cursor):
    """Create all database tables"""
    
    # Users table
    cursor.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            voice_enabled BOOLEAN DEFAULT 1,
            preferred_language TEXT DEFAULT 'en-IN',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_login DATETIME
        )
    ''')
    
    # Stations table
    cursor.execute('''
        CREATE TABLE stations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            station_code TEXT UNIQUE NOT NULL,
            station_name TEXT NOT NULL,
            city TEXT NOT NULL,
            state TEXT NOT NULL,
            zone TEXT
        )
    ''')
    
    # Trains table
    cursor.execute('''
        CREATE TABLE trains (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            train_number TEXT UNIQUE NOT NULL,
            train_name TEXT NOT NULL,
            train_type TEXT,
            has_ac_1 BOOLEAN DEFAULT 0,
            has_ac_2 BOOLEAN DEFAULT 0,
            has_ac_3 BOOLEAN DEFAULT 0,
            has_sleeper BOOLEAN DEFAULT 1,
            has_chair_car BOOLEAN DEFAULT 0,
            has_second_sitting BOOLEAN DEFAULT 0
        )
    ''')
    
    # Routes table
    cursor.execute('''
        CREATE TABLE routes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_station_id INTEGER NOT NULL,
            destination_station_id INTEGER NOT NULL,
            distance_km INTEGER,
            FOREIGN KEY (source_station_id) REFERENCES stations (id),
            FOREIGN KEY (destination_station_id) REFERENCES stations (id)
        )
    ''')
    
    # Schedules table
    cursor.execute('''
        CREATE TABLE schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            train_id INTEGER NOT NULL,
            route_id INTEGER NOT NULL,
            departure_time TEXT NOT NULL,
            arrival_time TEXT NOT NULL,
            journey_days TEXT DEFAULT 'Daily',
            price_ac_1 REAL,
            price_ac_2 REAL,
            price_ac_3 REAL,
            price_sleeper REAL,
            price_chair_car REAL,
            price_second_sitting REAL,
            capacity_ac_1 INTEGER DEFAULT 0,
            capacity_ac_2 INTEGER DEFAULT 0,
            capacity_ac_3 INTEGER DEFAULT 0,
            capacity_sleeper INTEGER DEFAULT 0,
            capacity_chair_car INTEGER DEFAULT 0,
            capacity_second_sitting INTEGER DEFAULT 0,
            FOREIGN KEY (train_id) REFERENCES trains (id),
            FOREIGN KEY (route_id) REFERENCES routes (id)
        )
    ''')
    
    # Bookings table
    cursor.execute('''
        CREATE TABLE bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pnr_number TEXT UNIQUE NOT NULL,
            user_id INTEGER NOT NULL,
            schedule_id INTEGER NOT NULL,
            travel_date DATE NOT NULL,
            train_class TEXT NOT NULL,
            passenger_name TEXT NOT NULL,
            passenger_age INTEGER NOT NULL,
            passenger_gender TEXT NOT NULL,
            total_amount REAL NOT NULL,
            booking_status TEXT DEFAULT 'pending',
            waiting_list_number INTEGER,
            payment_id TEXT,
            payment_status TEXT DEFAULT 'pending',
            payment_method TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            confirmed_at DATETIME,
            cancelled_at DATETIME,
            booked_via_voice BOOLEAN DEFAULT 0,
            voice_session_id TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (schedule_id) REFERENCES schedules (id)
        )
    ''')

def insert_sample_data(cursor):
    """Insert sample data for testing"""
    
    # Insert demo user
    password_hash = hash_password('password123')
    cursor.execute('''
        INSERT INTO users (username, email, password_hash, 
                          first_name, last_name, phone, voice_enabled, preferred_language)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', ('demo_user', 'demo@example.com', password_hash, 
          'Demo', 'User', '9876543210', 1, 'en-IN'))
    
    # Insert major stations
    stations = [
        ('CSMT', 'Chhatrapati Shivaji Maharaj Terminus', 'Mumbai', 'Maharashtra', 'CR'),
        ('NDLS', 'New Delhi Railway Station', 'New Delhi', 'Delhi', 'NR'),
        ('HWH', 'Howrah Junction', 'Kolkata', 'West Bengal', 'ER'),
        ('SBC', 'KSR Bengaluru City Junction', 'Bangalore', 'Karnataka', 'SR'),
        ('MAS', 'Chennai Central', 'Chennai', 'Tamil Nadu', 'SR'),
        ('HYB', 'Hyderabad Deccan', 'Hyderabad', 'Telangana', 'SCR'),
        ('PUNE', 'Pune Junction', 'Pune', 'Maharashtra', 'CR'),
        ('ADI', 'Ahmedabad Junction', 'Ahmedabad', 'Gujarat', 'WR'),
        ('JP', 'Jaipur Junction', 'Jaipur', 'Rajasthan', 'NWR'),
        ('LKO', 'Lucknow Charbagh', 'Lucknow', 'Uttar Pradesh', 'NR')
    ]
    
    cursor.executemany('''
        INSERT INTO stations (station_code, station_name, city, state, zone)
        VALUES (?, ?, ?, ?, ?)
    ''', stations)
    
    # Insert popular trains
    trains = [
        ('12951', 'Mumbai Rajdhani Express', 'Rajdhani', 1, 1, 1, 0, 0, 0),
        ('12302', 'Kolkata Rajdhani Express', 'Rajdhani', 1, 1, 1, 0, 0, 0),
        ('12434', 'Chennai Rajdhani Express', 'Rajdhani', 1, 1, 1, 0, 0, 0),
        ('12627', 'Karnataka Express', 'Express', 0, 1, 1, 1, 0, 0),
        ('12163', 'Dadar Express', 'Express', 0, 0, 1, 1, 0, 0)
    ]
    
    cursor.executemany('''
        INSERT INTO trains (train_number, train_name, train_type, has_ac_1, has_ac_2, 
                           has_ac_3, has_sleeper, has_chair_car, has_second_sitting)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', trains)
    
    # Insert routes
    routes = [
        (1, 2, 1384),  # Mumbai to Delhi
        (2, 3, 1447),  # Delhi to Kolkata
        (1, 4, 1279),  # Mumbai to Bangalore
        (1, 5, 1279),  # Mumbai to Chennai
        (4, 2, 2146),  # Bangalore to Delhi
    ]
    
    cursor.executemany('''
        INSERT INTO routes (source_station_id, destination_station_id, distance_km)
        VALUES (?, ?, ?)
    ''', routes)
    
    # Insert schedules
    schedules = [
        (1, 1, '16:55', '09:55', 'Daily', 3500.0, 2500.0, 1800.0, None, None, None, 18, 46, 64, 0, 0, 0),
        (2, 2, '17:00', '10:40', 'Daily', 3800.0, 2800.0, 2000.0, None, None, None, 18, 46, 64, 0, 0, 0),
        (4, 3, '21:15', '22:40', 'Daily', None, 1200.0, 900.0, 600.0, None, None, 0, 46, 64, 72, 0, 0),
        (4, 4, '22:50', '06:00', 'Daily', None, 1300.0, 950.0, 650.0, None, None, 0, 46, 64, 72, 0, 0),
        (5, 3, '14:00', '05:30', 'Daily', None, 1400.0, 1000.0, 700.0, None, None, 0, 46, 64, 72, 0, 0)
    ]
    
    cursor.executemany('''
        INSERT INTO schedules (train_id, route_id, departure_time, arrival_time, journey_days,
                              price_ac_1, price_ac_2, price_ac_3, price_sleeper, 
                              price_chair_car, price_second_sitting,
                              capacity_ac_1, capacity_ac_2, capacity_ac_3,
                              capacity_sleeper, capacity_chair_car, capacity_second_sitting)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', schedules)

def validate_password(password):
    """Validate password requirements"""
    if len(password) < 6:
        return False, 'Password must be at least 6 characters long'
    if not any(c.isupper() for c in password):
        return False, 'Password must contain at least one uppercase letter'
    if not any(c.islower() for c in password):
        return False, 'Password must contain at least one lowercase letter'
    return True, 'Password is valid'

def hash_password(password):
    """Hash password using SHA256 with salt"""
    salt = secrets.token_hex(16)
    return hashlib.sha256((salt + password).encode()).hexdigest() + ':' + salt

def verify_password(password, password_hash):
    """Verify password against hash"""
    if ':' not in password_hash:
        return False
    hash_part, salt = password_hash.split(':')
    return hashlib.sha256((salt + password).encode()).hexdigest() == hash_part

def get_user_by_username(username):
    """Get user by username"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = cursor.fetchone()
    conn.close()
    
    return dict(user) if user else None

def get_user_by_id(user_id):
    """Get user by ID"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    
    return dict(user) if user else None

def search_trains(source, destination, date=None):
    """Search trains between stations"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    query = '''
        SELECT  
            t.train_number, t.train_name, t.train_type,
            s.departure_time, s.arrival_time,
            s.price_ac_1, s.price_ac_2, s.price_ac_3, 
            s.price_sleeper, s.price_chair_car, s.price_second_sitting,
            s.capacity_ac_1, s.capacity_ac_2, s.capacity_ac_3,
            s.capacity_sleeper, s.capacity_chair_car, s.capacity_second_sitting,
            s.id as schedule_id,
            src.station_name as source_name, dst.station_name as dest_name
        FROM schedules s
        JOIN trains t ON s.train_id = t.id
        JOIN routes r ON s.route_id = r.id
        JOIN stations src ON r.source_station_id = src.id
        JOIN stations dst ON r.destination_station_id = dst.id
        WHERE (src.station_code LIKE ? OR src.station_name LIKE ? OR src.city LIKE ?)
        AND (dst.station_code LIKE ? OR dst.station_name LIKE ? OR dst.city LIKE ?)
        ORDER BY s.departure_time
    '''
    
    source_pattern = f'%{source}%'
    dest_pattern = f'%{destination}%'
    
    cursor.execute(query, (source_pattern, source_pattern, source_pattern,
                          dest_pattern, dest_pattern, dest_pattern))
    
    results = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in results]

def find_stations(search_term):
    """Find stations by name, code, or city"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    query = '''
        SELECT * FROM stations 
        WHERE station_code LIKE ? OR station_name LIKE ? OR city LIKE ?
        ORDER BY station_name
        LIMIT 10
    '''
    
    pattern = f'%{search_term}%'
    cursor.execute(query, (pattern, pattern, pattern))
    
    results = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in results]

def get_booking_by_pnr(pnr):
    """Get booking details by PNR with complete train and route information"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    query = '''
        SELECT 
            b.*,
            t.train_number,
            t.train_name,
            t.train_type,
            s.departure_time,
            s.arrival_time,
            s.journey_days,
            src_station.station_code as source_code,
            src_station.station_name as source_station,
            src_station.city as source_city,
            dest_station.station_code as dest_code,
            dest_station.station_name as dest_station,
            dest_station.city as dest_city,
            r.distance_km
        FROM bookings b
        JOIN schedules s ON b.schedule_id = s.id
        JOIN trains t ON s.train_id = t.id
        JOIN routes r ON s.route_id = r.id
        JOIN stations src_station ON r.source_station_id = src_station.id
        JOIN stations dest_station ON r.destination_station_id = dest_station.id
        WHERE b.pnr_number = ?
    '''
    
    cursor.execute(query, (pnr,))
    result = cursor.fetchone()
    conn.close()
    
    return dict(result) if result else None

def get_user_bookings(user_id, limit=10):
    """Get user's booking history"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    query = '''
        SELECT b.*, t.train_name, t.train_number,
               src.station_name as source_name, dst.station_name as dest_name
        FROM bookings b
        JOIN schedules s ON b.schedule_id = s.id
        JOIN trains t ON s.train_id = t.id
        JOIN routes r ON s.route_id = r.id
        JOIN stations src ON r.source_station_id = src.id
        JOIN stations dst ON r.destination_station_id = dst.id
        WHERE b.user_id = ?
        ORDER BY b.created_at DESC
        LIMIT ?
    '''
    
    cursor.execute(query, (user_id, limit))
    results = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in results]

def update_user_login(user_id):
    """Update user's last login time"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('UPDATE users SET last_login = ? WHERE id = ?', 
                   (datetime.now().isoformat(), user_id))
    
    conn.commit()
    conn.close()

def create_user(username, email, password, first_name, last_name, phone, voice_enabled=True):
    """Create a new user"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    try:
        # Check if username or email already exists
        cursor.execute('SELECT id FROM users WHERE username = ? OR email = ?', 
                      (username, email))
        existing_user = cursor.fetchone()
        
        if existing_user:
            conn.close()
            return None, "Username or email already exists"
        
        # Hash password
        password_hash = hash_password(password)
        
        # Insert new user
        cursor.execute('''
            INSERT INTO users (username, email, password_hash, first_name, last_name, phone, voice_enabled)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (username, email, password_hash, first_name, last_name, phone, voice_enabled))
        
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return user_id, "User created successfully"
        
    except sqlite3.Error as e:
        conn.close()
        return None, f"Database error: {str(e)}"

def check_user_exists(username=None, email=None):
    """Check if user exists by username or email"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    conditions = []
    params = []
    
    if username:
        conditions.append('username = ?')
        params.append(username)
    if email:
        conditions.append('email = ?')
        params.append(email)
    
    if not conditions:
        conn.close()
        return False
    
    query = f"SELECT id FROM users WHERE {' OR '.join(conditions)}"
    cursor.execute(query, params)
    result = cursor.fetchone()
    conn.close()
    
    return result is not None

def get_all_trains():
    """Get all trains"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM trains ORDER BY train_name')
    results = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in results]

def get_train_schedules_with_routes():
    """Get all train schedules with route information"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    query = '''
        SELECT 
            t.id as train_id,
            t.train_number, t.train_name, t.train_type,
            t.has_ac_1, t.has_ac_2, t.has_ac_3, 
            t.has_sleeper, t.has_chair_car, t.has_second_sitting,
            s.id as schedule_id,
            s.departure_time, s.arrival_time, s.journey_days,
            s.price_ac_1, s.price_ac_2, s.price_ac_3, 
            s.price_sleeper, s.price_chair_car, s.price_second_sitting,
            s.capacity_ac_1, s.capacity_ac_2, s.capacity_ac_3,
            s.capacity_sleeper, s.capacity_chair_car, s.capacity_second_sitting,
            src.station_code as source_code, src.station_name as source_name,
            src.city as source_city,
            dst.station_code as dest_code, dst.station_name as dest_name,
            dst.city as dest_city,
            r.distance_km
        FROM schedules s
        JOIN trains t ON s.train_id = t.id
        JOIN routes r ON s.route_id = r.id
        JOIN stations src ON r.source_station_id = src.id
        JOIN stations dst ON r.destination_station_id = dst.id
        ORDER BY t.train_name, s.departure_time
    '''
    
    cursor.execute(query)
    results = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in results]


def get_stations_by_type(search_term=None):
    """Get all stations, optionally filtered by search term"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if search_term:
        query = '''
            SELECT DISTINCT station_code, station_name, city FROM stations 
            WHERE station_code LIKE ? OR station_name LIKE ? OR city LIKE ?
            ORDER BY city, station_name
            LIMIT 20
        '''
        pattern = f'%{search_term}%'
        cursor.execute(query, (pattern, pattern, pattern))
    else:
        query = '''
            SELECT DISTINCT station_code, station_name, city FROM stations 
            ORDER BY city, station_name
        '''
        cursor.execute(query)
    
    results = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in results]


def get_schedule_by_id(schedule_id):
    """Get detailed schedule information by schedule ID"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    query = '''
        SELECT 
            t.id as train_id,
            t.train_number, t.train_name, t.train_type,
            t.has_ac_1, t.has_ac_2, t.has_ac_3, 
            t.has_sleeper, t.has_chair_car, t.has_second_sitting,
            s.id as schedule_id,
            s.departure_time, s.arrival_time, s.journey_days,
            s.price_ac_1, s.price_ac_2, s.price_ac_3, 
            s.price_sleeper, s.price_chair_car, s.price_second_sitting,
            s.capacity_ac_1, s.capacity_ac_2, s.capacity_ac_3,
            s.capacity_sleeper, s.capacity_chair_car, s.capacity_second_sitting,
            src.station_code as source_code, src.station_name as source_name,
            src.city as source_city,
            dst.station_code as dest_code, dst.station_name as dest_name,
            dst.city as dest_city,
            r.distance_km
        FROM schedules s
        JOIN trains t ON s.train_id = t.id
        JOIN routes r ON s.route_id = r.id
        JOIN stations src ON r.source_station_id = src.id
        JOIN stations dst ON r.destination_station_id = dst.id
        WHERE s.id = ?
    '''
    
    cursor.execute(query, (schedule_id,))
    result = cursor.fetchone()
    conn.close()
    
    return dict(result) if result else None


def create_booking(user_id, schedule_id, passenger_name, passenger_age, passenger_gender, 
                   passenger_phone, travel_class, travel_date, seat_number=None):
    """Create a new booking"""
    import random
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Generate PNR (10 digits)
    pnr = ''.join([str(random.randint(0, 9)) for _ in range(10)])
    
    # Get schedule details for price
    schedule = get_schedule_by_id(schedule_id)
    if not schedule:
        conn.close()
        return None
    
    # Get price based on class
    price_map = {
        'ac_1': schedule.get('price_ac_1'),
        'ac_2': schedule.get('price_ac_2'),
        'ac_3': schedule.get('price_ac_3'),
        'sleeper': schedule.get('price_sleeper'),
        'chair_car': schedule.get('price_chair_car'),
        'second_sitting': schedule.get('price_second_sitting')
    }
    ticket_price = price_map.get(travel_class, 0.0) or 0.0
    
    # Calculate total with GST (5%)
    gst_amount = ticket_price * 0.05
    total_amount = ticket_price + gst_amount
    
    # Generate seat number if not provided
    if not seat_number:
        seat_number = f"{travel_class.upper()}-{random.randint(1, 72)}"
    
    query = '''
        INSERT INTO bookings (
            pnr_number, user_id, schedule_id, travel_date, train_class,
            passenger_name, passenger_age, passenger_gender, total_amount,
            booking_status, payment_status, confirmed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
    '''
    
    try:
        cursor.execute(query, (
            pnr, user_id, schedule_id, travel_date, travel_class,
            passenger_name, passenger_age, passenger_gender, total_amount,
            'confirmed', 'completed'
        ))
        conn.commit()
        booking_id = cursor.lastrowid
        conn.close()
        
        return {
            'booking_id': booking_id,
            'pnr': pnr,
            'seat_number': seat_number,
            'ticket_price': ticket_price,
            'gst_amount': gst_amount,
            'total_amount': total_amount,
            'schedule': schedule
        }
    except Exception as e:
        print(f"Error creating booking: {e}")
        import traceback
        traceback.print_exc()
        conn.close()
        return None


def get_booking_details(booking_id):
    """Get complete booking details with train and schedule information"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    query = '''
        SELECT 
            b.*,
            t.train_number, t.train_name, t.train_type,
            s.departure_time, s.arrival_time, s.journey_days,
            src.station_name as source_station, src.station_code as source_code,
            dst.station_name as dest_station, dst.station_code as dest_code
        FROM bookings b
        JOIN schedules s ON b.schedule_id = s.id
        JOIN trains t ON s.train_id = t.id
        JOIN routes r ON s.route_id = r.id
        JOIN stations src ON r.source_station_id = src.id
        JOIN stations dst ON r.destination_station_id = dst.id
        WHERE b.id = ?
    '''
    
    cursor.execute(query, (booking_id,))
    result = cursor.fetchone()
    conn.close()
    
    return dict(result) if result else None


def cancel_booking_by_pnr(pnr_number):
    """Cancel a booking by its PNR number"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    try:
        # Check if PNR exists
        cursor.execute('SELECT id FROM bookings WHERE pnr_number = ?', (pnr_number,))
        booking = cursor.fetchone()
        
        if not booking:
            conn.close()
            return False
            
        # Update status to cancelled
        cursor.execute('''
            UPDATE bookings 
            SET booking_status = 'cancelled',
                cancelled_at = ?
            WHERE pnr_number = ?
        ''', (datetime.now().isoformat(), pnr_number))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error cancelling booking: {e}")
        conn.close()
        return False
