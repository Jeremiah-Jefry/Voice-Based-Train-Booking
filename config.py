import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'voice-train-booking-dev-key-2026'
    
    # Database configuration
    DATABASE_PATH = os.path.join(basedir, 'train_booking.db')
    
    # Session configuration
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)
    SESSION_TYPE = 'filesystem'
    
    # Voice API configuration
    SPEECH_API_TIMEOUT = 10  # seconds
    VOICE_LANGUAGE = 'en-IN'
    
    # Booking configuration
    SEAT_RESERVATION_TIMEOUT = 600  # 10 minutes in seconds
    INVENTORY_CACHE_TIMEOUT = 900   # 15 minutes in seconds
    
    # IRCTC integration (mock for development)
    IRCTC_API_BASE = os.environ.get('IRCTC_API_BASE') or 'https://api-mock.irctc.co.in'
    IRCTC_API_KEY = os.environ.get('IRCTC_API_KEY') or 'development-key'