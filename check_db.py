import sqlite3

conn = sqlite3.connect('train_booking.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Check tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print("Tables:", [t['name'] for t in tables])

# Check trains
cursor.execute("SELECT COUNT(*) as count FROM trains")
print("Trains:", cursor.fetchone()['count'])

# Check schedules
cursor.execute("SELECT COUNT(*) as count FROM schedules")
print("Schedules:", cursor.fetchone()['count'])

# Check routes
cursor.execute("SELECT COUNT(*) as count FROM routes")
print("Routes:", cursor.fetchone()['count'])

# Check stations
cursor.execute("SELECT COUNT(*) as count FROM stations")
print("Stations:", cursor.fetchone()['count'])

# Check sample schedule data
cursor.execute("""
    SELECT t.train_name, s.departure_time, r.distance_km 
    FROM schedules s
    JOIN trains t ON s.train_id = t.id
    JOIN routes r ON s.route_id = r.id
    LIMIT 3
""")
results = cursor.fetchall()
print("\nSample schedules:")
for row in results:
    print(f"  {dict(row)}")

conn.close()
