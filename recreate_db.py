# Script to recreate the database

from flask import Flask
from models import db, User, Role, UserRole
from datetime import datetime
import os

# Initialize Flask app
app = Flask(__name__)
app.config.update(
    SECRET_KEY='dev_key',
    SQLALCHEMY_DATABASE_URI='sqlite:///contact_harvester.db',
    SQLALCHEMY_TRACK_MODIFICATIONS=False
)

# Initialize database
db.init_app(app)

def main():
    with app.app_context():
        # Drop all tables
        print("Dropping all tables...")
        db.drop_all()
        
        # Create all tables
        print("Creating tables from models...")
        db.create_all()
        
        # Create default roles
        print("Creating default roles...")
        roles = {
            UserRole.ADMIN.value: 'Administrator with full access',
            UserRole.EDITOR.value: 'Editor with content management access',
            UserRole.USER.value: 'Regular user with limited access'
        }
        
        for role_name, description in roles.items():
            role = Role(name=role_name, description=description)
            db.session.add(role)
        
        # Create default admin user
        print("Creating admin user...")
        admin_role = Role.query.filter_by(name=UserRole.ADMIN.value).first()
        
        if admin_role:
            admin = User(
                username='admin',
                email='admin@example.com',
                first_name='Admin',
                last_name='User',
                is_active=True,
                created_at=datetime.utcnow()
            )
            admin.set_password('admin123')
            admin.roles.append(admin_role)
            db.session.add(admin)
        
        # Commit changes
        db.session.commit()
        print("Database setup complete!")

if __name__ == '__main__':
    main()

