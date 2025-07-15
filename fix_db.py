import os
import sys
from flask import Flask
from datetime import datetime

# Create temporary Flask app for database operations
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///contact_harvester.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Import and initialize the database
from models import db, User, Subscription, BlogComment

# Initialize the app with the database
db.init_app(app)

# Create a context
with app.app_context():
    try:
        # Create necessary tables
        db.create_all()
        
        # Add BlogComment if it doesn't exist
        if not hasattr(db.Model, 'blog_comments'):
            class BlogComment(db.Model):
                __tablename__ = 'blog_comments'
                
                id = db.Column(db.Integer, primary_key=True)
                post_id = db.Column(db.Integer, db.ForeignKey('blog_posts.id'))
                user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
                content = db.Column(db.Text, nullable=False)
                created_at = db.Column(db.DateTime, default=datetime.utcnow)
                approved = db.Column(db.Boolean, default=False)
                
                # Relationship
                user = db.relationship('User', backref='comments')
            
            # Create the table
            db.create_all()
            print("Created BlogComment table")
            
        # Add missing fields to Subscription model if needed
        try:
            # Check if a subscription exists to test fields
            test_sub = Subscription.query.first()
            if test_sub:
                # Try to access fields to see if they exist
                try:
                    currency = test_sub.currency
                except:
                    print("Adding missing currency field to Subscription")
                    with db.engine.connect() as conn:
                        conn.execute('ALTER TABLE subscriptions ADD COLUMN currency VARCHAR(10) DEFAULT "USD"')
                
                try:
                    is_public = test_sub.is_public
                except:
                    print("Adding missing is_public field to Subscription")
                    with db.engine.connect() as conn:
                        conn.execute('ALTER TABLE subscriptions ADD COLUMN is_public BOOLEAN DEFAULT 1')
                
                try:
                    is_featured = test_sub.is_featured
                except:
                    print("Adding missing is_featured field to Subscription")
                    with db.engine.connect() as conn:
                        conn.execute('ALTER TABLE subscriptions ADD COLUMN is_featured BOOLEAN DEFAULT 0')
                
                try:
                    allow_cancellation = test_sub.allow_cancellation
                except:
                    print("Adding missing allow_cancellation field to Subscription")
                    with db.engine.connect() as conn:
                        conn.execute('ALTER TABLE subscriptions ADD COLUMN allow_cancellation BOOLEAN DEFAULT 1')
                
                try:
                    stripe_plan_id = test_sub.stripe_plan_id
                except:
                    print("Adding missing stripe_plan_id field to Subscription")
                    with db.engine.connect() as conn:
                        conn.execute('ALTER TABLE subscriptions ADD COLUMN stripe_plan_id VARCHAR(100)')
                
                try:
                    features = test_sub.features
                except:
                    print("Adding missing features field to Subscription")
                    with db.engine.connect() as conn:
                        conn.execute('ALTER TABLE subscriptions ADD COLUMN features TEXT')
        except Exception as e:
            print(f"Error checking subscription fields: {e}")
            
        print("Database fixes applied successfully!")
    except Exception as e:
        print(f"Error fixing database: {e}")
        sys.exit(1) 