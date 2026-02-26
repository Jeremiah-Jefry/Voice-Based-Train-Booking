"""
Database seeder for Voice Train Booking Platform
Populates the database with sample data for development and testing
"""

from app import create_app, db
from app.models import User, Train, Station, Route, Schedule, TrainClass
from datetime import datetime, time
import random

def seed_database():
    """Seed the database with initial data"""
    
    app = create_app()
    with app.app_context():
        print("Seeding database...")
        
        # Create all tables
        db.create_all()
        
        # Seed stations
        seed_stations()
        
        # Seed trains
        seed_trains()
        
        # Seed routes and schedules
        seed_routes_and_schedules()
        
        # Seed sample user
        seed_sample_user()
        
        print("Database seeding completed!")

def seed_stations():
    """Seed major Indian railway stations"""
    
    stations_data = [
        # Major Metro Cities
        ("CSMT", "Chhatrapati Shivaji Maharaj Terminus", "Mumbai", "Maharashtra"),
        ("LTT", "Lokmanya Tilak Terminus", "Mumbai", "Maharashtra"),
        ("NDLS", "New Delhi Railway Station", "New Delhi", "Delhi"),
        ("DLI", "Delhi Junction", "New Delhi", "Delhi"),
        ("HWH", "Howrah Junction", "Kolkata", "West Bengal"),
        ("SBC", "KSR Bengaluru City Junction", "Bangalore", "Karnataka"),
        ("MAS", "Chennai Central", "Chennai", "Tamil Nadu"),
        ("HYB", "Hyderabad Deccan", "Hyderabad", "Telangana"),
        ("PUNE", "Pune Junction", "Pune", "Maharashtra"),
        ("ADI", "Ahmedabad Junction", "Ahmedabad", "Gujarat"),
        
        # Secondary Cities
        ("JP", "Jaipur Junction", "Jaipur", "Rajasthan"),
        ("LKO", "Lucknow Charbagh", "Lucknow", "Uttar Pradesh"),
        ("BPL", "Bhopal Junction", "Bhopal", "Madhya Pradesh"),
        ("TVC", "Thiruvananthapuram Central", "Thiruvananthapuram", "Kerala"),
        ("VSKP", "Visakhapatnam Junction", "Visakhapatnam", "Andhra Pradesh"),
        ("BBS", "Bhubaneswar", "Bhubaneswar", "Odisha"),
        ("GWL", "Gwalior Junction", "Gwalior", "Madhya Pradesh"),
        ("JBP", "Jabalpur Junction", "Jabalpur", "Madhya Pradesh"),
        ("UDZ", "Udaipur City", "Udaipur", "Rajasthan"),
        ("CDG", "Chandigarh Railway Station", "Chandigarh", "Punjab"),
    ]
    
    for code, name, city, state in stations_data:
        existing = Station.query.filter_by(station_code=code).first()
        if not existing:
            station = Station(
                station_code=code,
                station_name=name,
                city=city,
                state=state,
                zone="CR" if state == "Maharashtra" else "NR" if state in ["Delhi", "Punjab"] else "SR"
            )
            db.session.add(station)
    
    db.session.commit()
    print(f"Seeded {len(stations_data)} stations")

def seed_trains():
    """Seed popular Indian trains"""
    
    trains_data = [
        ("12951", "Mumbai Rajdhani Express", "Rajdhani", True, True, True, False, False, False),
        ("12302", "Kolkata Rajdhani Express", "Rajdhani", True, True, True, False, False, False),
        ("12434", "Chennai Rajdhani Express", "Rajdhani", True, True, True, False, False, False),
        ("12009", "Shatabdi Express", "Shatabdi", False, False, False, False, True, False),
        ("12627", "Karnataka Express", "Express", False, True, True, True, False, False),
        ("12163", "Dadar Express", "Express", False, False, True, True, False, False),
        ("19037", "Avadh Express", "Express", False, False, True, True, False, False),
        ("12617", "Mangala Lakshadweep Express", "Express", False, True, True, True, False, False),
        ("12049", "Gatimaan Express", "Express", False, False, False, False, True, False),
        ("22691", "Rajdhani Express", "Rajdhani", True, True, True, False, False, False),
        ("12801", "Purushottam Express", "Express", False, True, True, True, False, False),
        ("12315", "Ananya Express", "Express", False, True, True, True, False, False),
        ("12413", "Poornima Express", "Express", False, False, True, True, False, False),
        ("19023", "Firozpur Express", "Express", False, False, True, True, False, False),
        ("12615", "Grand Trunk Express", "Express", False, False, True, True, False, False),
    ]
    
    for number, name, train_type, ac1, ac2, ac3, sl, cc, ss in trains_data:
        existing = Train.query.filter_by(train_number=number).first()
        if not existing:
            train = Train(
                train_number=number,
                train_name=name,
                train_type=train_type,
                has_ac_1=ac1,
                has_ac_2=ac2,
                has_ac_3=ac3,
                has_sleeper=sl,
                has_chair_car=cc,
                has_second_sitting=ss
            )
            db.session.add(train)
    
    db.session.commit()
    print(f"Seeded {len(trains_data)} trains")

def seed_routes_and_schedules():
    """Seed routes between major stations and their schedules"""
    
    # Get stations and trains
    stations = {s.station_code: s for s in Station.query.all()}
    trains = {t.train_number: t for t in Train.query.all()}
    
    # Popular routes
    routes_data = [
        ("CSMT", "NDLS", 1384),  # Mumbai to Delhi
        ("NDLS", "HWH", 1447),   # Delhi to Kolkata
        ("MAS", "NDLS", 2194),   # Chennai to Delhi
        ("SBC", "NDLS", 2146),   # Bangalore to Delhi
        ("CSMT", "SBC", 1279),   # Mumbai to Bangalore
        ("CSMT", "MAS", 1279),   # Mumbai to Chennai
        ("HYB", "NDLS", 1566),   # Hyderabad to Delhi
        ("PUNE", "NDLS", 1457),  # Pune to Delhi
        ("ADI", "NDLS", 934),    # Ahmedabad to Delhi
        ("JP", "NDLS", 308),     # Jaipur to Delhi
    ]
    
    for source_code, dest_code, distance in routes_data:
        if source_code in stations and dest_code in stations:
            source = stations[source_code]
            dest = stations[dest_code]
            
            # Check if route exists
            existing_route = Route.query.filter_by(
                source_station_id=source.id,
                destination_station_id=dest.id
            ).first()
            
            if not existing_route:
                route = Route(
                    source_station_id=source.id,
                    destination_station_id=dest.id,
                    distance_km=distance
                )
                db.session.add(route)
                db.session.flush()  # Get the route ID
                
                # Create schedules for this route
                create_schedules_for_route(route, trains)
    
    db.session.commit()
    print("Seeded routes and schedules")

def create_schedules_for_route(route, trains):
    """Create sample schedules for a route"""
    
    # Sample train assignments for routes
    sample_trains = ["12951", "12302", "12627", "12163", "19037"]
    
    for train_number in sample_trains[:3]:  # Limit to 3 trains per route
        if train_number in trains:
            train = trains[train_number]
            
            # Generate random but realistic timings
            dep_hour = random.randint(6, 23)
            dep_minute = random.choice([0, 15, 30, 45])
            departure_time = time(dep_hour, dep_minute)
            
            # Calculate arrival time (add journey duration)
            journey_hours = random.randint(8, 24)
            arr_hour = (dep_hour + journey_hours) % 24
            arrival_time = time(arr_hour, dep_minute)
            
            # Set prices based on train type and class
            base_price = 500 if train.train_type == "Rajdhani" else 300
            distance_factor = route.distance_km / 1000
            
            schedule = Schedule(
                train_id=train.id,
                route_id=route.id,
                departure_time=departure_time,
                arrival_time=arrival_time,
                journey_days="Daily",
                price_ac_1=base_price * 3 * distance_factor if train.has_ac_1 else None,
                price_ac_2=base_price * 2 * distance_factor if train.has_ac_2 else None,
                price_ac_3=base_price * 1.5 * distance_factor if train.has_ac_3 else None,
                price_sleeper=base_price * distance_factor if train.has_sleeper else None,
                price_chair_car=base_price * 0.8 * distance_factor if train.has_chair_car else None,
                price_second_sitting=base_price * 0.5 * distance_factor if train.has_second_sitting else None,
                capacity_ac_1=18 if train.has_ac_1 else 0,
                capacity_ac_2=46 if train.has_ac_2 else 0,
                capacity_ac_3=64 if train.has_ac_3 else 0,
                capacity_sleeper=72 if train.has_sleeper else 0,
                capacity_chair_car=78 if train.has_chair_car else 0,
                capacity_second_sitting=108 if train.has_second_sitting else 0
            )
            db.session.add(schedule)

def seed_sample_user():
    """Create a sample user for testing"""
    
    existing_user = User.query.filter_by(username="demo_user").first()
    if not existing_user:
        user = User(
            username="demo_user",
            email="demo@example.com",
            irctc_id="DEMO123456",
            first_name="Demo",
            last_name="User",
            phone="9876543210",
            irctc_verified=True,  # Already verified for demo
            voice_enabled=True,
            preferred_language="en-IN"
        )
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()
        print("Created demo user (username: demo_user, password: password123)")

if __name__ == "__main__":
    seed_database()