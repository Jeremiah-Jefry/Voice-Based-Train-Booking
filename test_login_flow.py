import sys
sys.path.insert(0, '/Users/ADMIN/Documents/train')

from app.database import get_user_by_irctc_id, verify_password

# Test getting user
irctc_id = "DEMO123456"
password = "password123"

user_data = get_user_by_irctc_id(irctc_id)

if user_data:
    print(f'User found: {user_data}')
    print(f'Verifying password...')
    pwd_match = verify_password(password, user_data['password_hash'])
    print(f'Password match: {pwd_match}')
    print(f'Verified status: {user_data.get("irctc_verified")}')
else:
    print('User not found')
