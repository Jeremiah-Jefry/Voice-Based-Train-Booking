import sqlite3

DATABASE = 'train_booking.db'

conn = sqlite3.connect(DATABASE)
cursor = conn.cursor()
cursor.execute('SELECT id, username, email, irctc_id, irctc_verified FROM users WHERE irctc_id = ?', ('DEMO123456',))
row = cursor.fetchone()

if row:
    id_val, username, email, irctc_id, verified = row
    print(f'User ID: {id_val}')
    print(f'Username: {username}')
    print(f'Email: {email}')
    print(f'IRCTC ID: {irctc_id}')
    print(f'Verified: {verified} (type: {type(verified).__name__})')
else:
    print('User not found')

conn.close()
