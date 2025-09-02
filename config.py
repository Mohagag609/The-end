import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-musharaka'
    
    # Database configuration
    DATABASE_URL = os.environ.get('DATABASE_URL')
    
    if DATABASE_URL:
        # Fix for Render's PostgreSQL URL
        if DATABASE_URL.startswith("postgres://"):
            DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
        SQLALCHEMY_DATABASE_URI = DATABASE_URL
    else:
        # Local SQLite for development
        SQLALCHEMY_DATABASE_URI = 'sqlite:///musharaka.db'
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }
    
    # Application settings
    BASE_CURRENCY = 'EGP'
    DECIMAL_PLACES = 2
    QTY_DECIMAL_PLACES = 3
    COST_DECIMAL_PLACES = 4