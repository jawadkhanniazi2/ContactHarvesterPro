import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Ensure required directories exist
directories = ['uploads', 'results', 'static/uploads/blog', 'static/uploads/site', 'backups']
for directory in directories:
    os.makedirs(directory, exist_ok=True)

# Set environment variables if not already set
if not os.environ.get('SECRET_KEY'):
    os.environ['SECRET_KEY'] = os.urandom(24).hex()

if not os.environ.get('DATABASE_URL'):
    os.environ['DATABASE_URL'] = 'sqlite:///contact_harvester.db'

# Import the app after setting environment variables
try:
    from app import app, db
    
    # Create the database and tables if they don't exist
    with app.app_context():
        db.create_all()
    
    if __name__ == "__main__":
        app.run(debug=True, host='0.0.0.0')
        
except ImportError as e:
    print(f"Error importing app: {e}")
    print("\nPlease ensure all required packages are installed:")
    print("pip install -r requirements.txt")
    sys.exit(1)
except Exception as e:
    print(f"Error starting application: {e}")
    sys.exit(1) 