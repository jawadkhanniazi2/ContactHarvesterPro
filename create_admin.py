from flask import Flask
from werkzeug.security import generate_password_hash
from datetime import datetime
import os
import sys

# Add the current directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import db, User, Role, UserRole

# Create a minimal Flask app to initialize the database connection
app = Flask(__name__)
app.config.update(
    SQLALCHEMY_DATABASE_URI=os.environ.get('DATABASE_URL', 'sqlite:///contact_harvester.db'),
    SQLALCHEMY_TRACK_MODIFICATIONS=False
)

# Initialize the database with the app
db.init_app(app)

def create_admin_user():
    with app.app_context():
        # Check if user already exists
        existing_user = User.query.filter_by(username='admin').first()
        if existing_user:
            print(f"Admin user already exists with username: {existing_user.username}")
            # Update password
            existing_user.set_password('jawad123')
            db.session.commit()
            print("Admin password updated successfully!")
            return

        # Create new admin user
        admin_user = User(
            username='admin',
            email='admin@contacthound.com',
            first_name='Admin',
            last_name='User',
            is_active=True,
            created_at=datetime.utcnow()
        )
        admin_user.set_password('jawad123')
        
        # Find the admin role
        admin_role = Role.query.filter_by(name=UserRole.ADMIN.value).first()
        if not admin_role:
            # Create admin role if it doesn't exist
            admin_role = Role(name=UserRole.ADMIN.value, description="Administrator role")
            db.session.add(admin_role)
            db.session.flush()

        # Assign admin role to user
        admin_user.roles.append(admin_role)
        
        # Add and commit the new user
        db.session.add(admin_user)
        db.session.commit()
        
        print(f"Admin user created successfully!")
        print(f"Username: admin")
        print(f"Email: admin@contacthound.com")
        print(f"Password: jawad123")

if __name__ == "__main__":
    create_admin_user() 