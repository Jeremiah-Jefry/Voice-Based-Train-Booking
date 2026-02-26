import sqlite3

conn = sqlite3.connect('train_booking.db')
cursor = conn.cursor()
cursor.execute('SELECT irctc_id, password_hash FROM users WHERE irctc_id = ?', ('DEMO123456',))
row = cursor.fetchone()
if row:
    irctc_id, pwd_hash = row
    print(f'IRCTC ID: {irctc_id}')
    print(f'Password Hash: {pwd_hash}')
    has_colon = ':' in pwd_hash
    print(f'Hash contains colon: {has_colon}')
else:
    print('User not found')
conn.close()
