"""
SQLite3 Database Seeder for Voice Train Booking Platform
Populates the database with sample data for development and testing
"""

import sqlite3
import hashlib
import secrets
from datetime import datetime, time
import os

DATABASE = 'train_booking.db'

def hash_password(password):
    salt = secrets.token_hex(16)
    return hashlib.sha256((salt + password).encode()).hexdigest() + ':' + salt

def seed_stations(cursor):
    stations_data = [
        ("CSMT", "Chhatrapati Shivaji Maharaj Terminus", "Mumbai", "Maharashtra", "CR"),
        ("LTT", "Lokmanya Tilak Terminus", "Mumbai", "Maharashtra", "CR"),
        ("NDLS", "New Delhi Railway Station", "New Delhi", "Delhi", "NR"),
        ("DLI", "Delhi Junction", "New Delhi", "Delhi", "NR"),
        ("HWH", "Howrah Junction", "Kolkata", "West Bengal", "ER"),
        ("SBC", "KSR Bengaluru City Junction", "Bangalore", "Karnataka", "SR"),
        ("MAS", "Chennai Central", "Chennai", "Tamil Nadu", "SR"),
        ("HYB", "Hyderabad Deccan", "Hyderabad", "Telangana", "SCR"),
        ("PUNE", "Pune Junction", "Pune", "Maharashtra", "CR"),
        ("ADI", "Ahmedabad Junction", "Ahmedabad", "Gujarat", "WR"),
        ("JP", "Jaipur Junction", "Jaipur", "Rajasthan", "NWR"),
        ("LKO", "Lucknow Charbagh", "Lucknow", "Uttar Pradesh", "NR"),
        ("BPL", "Bhopal Junction", "Bhopal", "Madhya Pradesh", "WCR"),
        ("TVC", "Thiruvananthapuram Central", "Thiruvananthapuram", "Kerala", "SR"),
        ("VSKP", "Visakhapatnam Junction", "Visakhapatnam", "Andhra Pradesh", "ECoR"),
        ("BBS", "Bhubaneswar", "Bhubaneswar", "Odisha", "ECoR"),
        ("GWL", "Gwalior Junction", "Gwalior", "Madhya Pradesh", "NCR"),
        ("JBP", "Jabalpur Junction", "Jabalpur", "Madhya Pradesh", "WCR"),
        ("UDZ", "Udaipur City", "Udaipur", "Rajasthan", "NWR"),
        ("CDG", "Chandigarh Railway Station", "Chandigarh", "Punjab", "NR"),
    ]
    for code, name, city, state, zone in stations_data:
        cursor.execute('INSERT OR IGNORE INTO stations (station_code, station_name, city, state, zone) VALUES (?, ?, ?, ?, ?)', (code, name, city, state, zone))
    print(f"Seeded {len(stations_data)} stations")

def seed_demo_user(cursor):
    password_hash = hash_password("password123")
    cursor.execute('INSERT OR IGNORE INTO users (username, email, password_hash, first_name, last_name, phone, voice_enabled, preferred_language) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
        ("demo_user", "demo@example.com", password_hash, "Demo", "User", "9876543210", 1, "en-IN"))
    print("Created demo user (username: demo_user, password: password123)")

def seed_trains(cursor):
    """Seed trains data"""
    trains_data = [
        ("12001", "Bhopal Shatabdi", "Shatabdi", 1, 1, 0, 0, 0, 0),
        ("12345", "Rajdhani Express", "Rajdhani", 1, 1, 1, 0, 0, 0),
        ("12456", "Mumbai Rajdhani", "Rajdhani", 1, 1, 1, 0, 0, 0),
        ("19001", "Dehradun Express", "Superfast", 0, 1, 1, 1, 0, 0),
        ("12621", "Tamil Nadu Express", "Express", 0, 1, 1, 1, 1, 0),
        ("12625", "Kerala Express", "Express", 0, 1, 1, 1, 1, 0),
        ("12952", "Tamilnadu Sampark Kranti", "Superfast", 0, 1, 1, 1, 0, 0),
        ("13005", "Darbhanga Express", "Express", 0, 0, 1, 1, 1, 1),
        ("14006", "Lichchavi Express", "Express", 0, 0, 1, 1, 1, 1),
        ("15015", "Guwahati Express", "Express", 0, 0, 1, 1, 1, 1),
    ]
    
    for train_num, train_name, train_type, ac1, ac2, ac3, sleeper, chair, sitting in trains_data:
        cursor.execute('''
            INSERT OR IGNORE INTO trains 
            (train_number, train_name, train_type, has_ac_1, has_ac_2, has_ac_3, has_sleeper, has_chair_car, has_second_sitting)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (train_num, train_name, train_type, ac1, ac2, ac3, sleeper, chair, sitting))
    
    print(f"Seeded {len(trains_data)} trains")

def seed_routes(cursor):
    """Seed routes connecting major cities"""
    # Get station IDs
    station_ids = {}
    cursor.execute("SELECT id, station_code FROM stations")
    for row in cursor.fetchall():
        station_ids[row[1]] = row[0]
    
    routes_data = [
        (station_ids['BPL'], station_ids['CSMT'], 700),   # Bhopal-Mumbai
        (station_ids['BPL'], station_ids['NDLS'], 1200),  # Bhopal-Delhi
        (station_ids['CSMT'], station_ids['NDLS'], 1600), # Mumbai-Delhi
        (station_ids['NDLS'], station_ids['HWH'], 2300),  # Delhi-Kolkata
        (station_ids['CSMT'], station_ids['SBC'], 1500),  # Mumbai-Bangalore
        (station_ids['SBC'], station_ids['MAS'], 350),    # Bangalore-Chennai
        (station_ids['MAS'], station_ids['HWH'], 1500),   # Chennai-Kolkata
        (station_ids['HYB'], station_ids['SBC'], 700),    # Hyderabad-Bangalore
        (station_ids['PUNE'], station_ids['CSMT'], 200),  # Pune-Mumbai
        (station_ids['JP'], station_ids['NDLS'], 280),    # Jaipur-Delhi
        (station_ids['NDLS'], station_ids['LKO'], 470),   # Delhi-Lucknow
        (station_ids['ADI'], station_ids['NDLS'], 900),   # Ahmedabad-Delhi
    ]
    
    for source_id, dest_id, distance in routes_data:
        cursor.execute('''
            INSERT OR IGNORE INTO routes (source_station_id, destination_station_id, distance_km)
            VALUES (?, ?, ?)
        ''', (source_id, dest_id, distance))
    
    print(f"Seeded {len(routes_data)} routes")

def seed_schedules(cursor):
    """Seed train schedules"""
    # Get train and route data
    trains = {}
    cursor.execute("SELECT id, train_number FROM trains")
    for row in cursor.fetchall():
        trains[row[1]] = row[0]
    
    routes = []
    cursor.execute("SELECT id FROM routes")
    for row in cursor.fetchall():
        routes.append(row[0])
    
    schedules_data = [
        (trains['12345'], routes[0], "08:00:00", "18:00:00", "Daily", 2500, 2000, 1500, 800, 1200, 1000),
        (trains['12456'], routes[1], "22:00:00", "08:00:00", "Daily", 3000, 2400, 1800, 1000, 1400, 1100),
        (trains['19001'], routes[2], "14:30:00", "22:30:00", "Daily", 1800, 1400, 1100, 600, 900, 700),
        (trains['12621'], routes[3], "17:45:00", "14:15:00", "Daily", 1200, 900, 700, 400, 600, 500),
        (trains['12625'], routes[4], "15:00:00", "12:00:00", "Daily", 1500, 1100, 850, 500, 700, 600),
        (trains['12952'], routes[5], "06:00:00", "22:00:00", "Daily", 2200, 1700, 1300, 700, 1000, 800),
        (trains['13005'], routes[6], "12:00:00", "08:00:00", "Daily", 1000, 800, 600, 400, 550, 450),
        (trains['14006'], routes[7], "19:00:00", "09:00:00", "Daily", 1100, 850, 650, 400, 600, 500),
        (trains['15015'], routes[8], "10:30:00", "20:30:00", "Daily", 800, 700, 600, 350, 500, 400),
        (trains['12001'], routes[9], "06:15:00", "10:15:00", "Daily", 900, 0, 0, 0, 0, 0),
    ]
    
    for route_idx, (train_id, route_id, dep_time, arr_time, days, p_ac1, p_ac2, p_ac3, p_sleeper, p_chair, p_sitting) in enumerate(schedules_data):
        if route_idx < len(routes):
            cursor.execute('''
                INSERT OR IGNORE INTO schedules 
                (train_id, route_id, departure_time, arrival_time, journey_days, 
                 price_ac_1, price_ac_2, price_ac_3, price_sleeper, price_chair_car, price_second_sitting,
                 capacity_ac_1, capacity_ac_2, capacity_ac_3, capacity_sleeper, capacity_chair_car, capacity_second_sitting)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 20, 30, 40, 50, 60, 70)
            ''', (train_id, route_id, dep_time, arr_time, days, p_ac1, p_ac2, p_ac3, p_sleeper, p_chair, p_sitting))
    
    print(f"Seeded {len(schedules_data)} schedules")

def main():
    if not os.path.exists(DATABASE):
        print("Database does not exist. Please run the app once to initialize the schema.")
        return
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    seed_stations(cursor)
    seed_trains(cursor)
    seed_routes(cursor)
    seed_schedules(cursor)
    seed_demo_user(cursor)
    conn.commit()
    conn.close()
    print("Seeding complete.")

if __name__ == "__main__":
    main()
