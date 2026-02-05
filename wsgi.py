import os
from app import create_app

# Get port from environment variable (Render sets this)
port = int(os.environ.get("PORT", 5000))

application = create_app()

# For Gunicorn compatibility
app = application

if __name__ == "__main__":
    application.run(host='0.0.0.0', port=port)