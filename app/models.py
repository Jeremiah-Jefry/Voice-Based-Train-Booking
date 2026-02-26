from flask_login import UserMixin
from app.database import get_user_by_id

class User(UserMixin):
    def __init__(self, user_data):
        self.id = user_data['id']
        self.username = user_data['username']
        self.email = user_data['email']
        self.first_name = user_data['first_name']
        self.last_name = user_data['last_name']
        self.phone = user_data['phone']
        self.voice_enabled = user_data['voice_enabled']
        self.preferred_language = user_data['preferred_language']
        self.created_at = user_data['created_at']
        self.last_login = user_data.get('last_login')
    
    def get_id(self):
        return str(self.id)
    
    @staticmethod
    def get(user_id):
        user_data = get_user_by_id(user_id)
        if user_data:
            return User(user_data)
        return None

# User loader for Flask-Login
from app import login

@login.user_loader
def load_user(user_id):
    return User.get(int(user_id))