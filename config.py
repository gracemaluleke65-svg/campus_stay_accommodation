import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Use environment variable for secret key, fallback for local dev only
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # DATABASE - THIS IS THE CRITICAL FIX FOR RENDER
    # Use PostgreSQL on Render, SQLite only as absolute fallback for local testing
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///accommodation.db'
    
    # Fix for Render's PostgreSQL URL format (postgres:// vs postgresql://)
    if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace("postgres://", "postgresql://", 1)
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,  # Checks connections before using them
        'pool_recycle': 300,    # Recycle connections every 5 minutes (prevents timeout issues)
    }
    
    UPLOAD_FOLDER = os.path.join('static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max
    
    # Stripe Keys - MUST be set in environment variables on Render
    STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY') or 'pk_test_your_key_here'
    STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY') or 'sk_test_your_key_here'
    
    # Admin seed - MUST be set in environment variables on Render
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL') or 'admin@campusstay.com'
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD') or 'admin123'