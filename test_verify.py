import sqlite3
import hashlib
import secrets

DATABASE = 'train_booking.db'

def hash_password(password):
    salt = secrets.token_hex(16)
    return hashlib.sha256((salt + password).encode()).hexdigest() + ':' + salt

def verify_password(password, password_hash):
    if ':' not in password_hash:
        return False
    hash_part, salt = password_hash.split(':')
    return hashlib.sha256((salt + password).encode()).hexdigest() == hash_part

# Check current user
conn = sqlite3.connect(DATABASE)
cursor = conn.cursor()
cursor.execute('SELECT irctc_id, password_hash FROM users WHERE irctc_id = ?', ('DEMO123456',))
row = cursor.fetchone()

if row:
    irctc_id, stored_hash = row
    print(f'Stored hash repr: {repr(stored_hash)}')
    print(f'Hash length: {len(stored_hash)}')
    
    # Test verification
    test_pwd = 'password123'
    result = verify_password(test_pwd, stored_hash)
    print(f'Verification result for "password123": {result}')
else:
    print('User not found in database')

conn.close()
