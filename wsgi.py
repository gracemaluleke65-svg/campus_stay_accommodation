import os
import sys
from app import create_app, app, db
from models import User, Accommodation, Booking, Review, Favorite

# Get port from environment variable
port = int(os.environ.get("PORT", 5000))

# Create application
application = create_app()

# CRITICAL: Create database tables on startup
with application.app_context():
    try:
        print("Creating database tables...")
        db.create_all()
        print("Database tables created successfully!")
        
        # Seed admin user
        from app import seed_admin
        seed_admin()
        print("Admin seeding completed!")
        
    except Exception as e:
        print(f"Error initializing database: {e}")
        import traceback
        traceback.print_exc()

# For Gunicorn compatibility
app = application

if __name__ == "__main__":
    application.run(host='0.0.0.0', port=port, debug=False)