import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'voice-train-booking-dev-key-2026'
    
    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'train_booking.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session configuration
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)
    SESSION_TYPE = 'filesystem'
    
    # Redis configuration for caching
    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://localhost:6379/0'
    
    # Payment configuration
    STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY')
    STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')
    RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID')
    RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET')
    
    # Voice API configuration
    SPEECH_API_TIMEOUT = 10  # seconds
    VOICE_LANGUAGE = 'en-IN'
    
    # Booking configuration
    SEAT_RESERVATION_TIMEOUT = 600  # 10 minutes in seconds
    INVENTORY_CACHE_TIMEOUT = 900   # 15 minutes in seconds
    
    # IRCTC integration (mock for development)
    IRCTC_API_BASE = os.environ.get('IRCTC_API_BASE') or 'https://api-mock.irctc.co.in'
    IRCTC_API_KEY = os.environ.get('IRCTC_API_KEY') or 'development-key'