from flask import Flask
from flask_login import LoginManager
from config import Config
import sqlite3
import os

login = LoginManager()
login.login_view = 'auth.login'
login.login_message = 'Please log in to access this page.'

def get_db_connection():
    conn = sqlite3.connect('train_booking.db')
    conn.row_factory = sqlite3.Row
    return conn

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    login.init_app(app)

    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    from app.voice import bp as voice_bp
    app.register_blueprint(voice_bp, url_prefix='/voice')
    
    # Initialize database
    from app.database import init_database
    with app.app_context():
        init_database()

    return app