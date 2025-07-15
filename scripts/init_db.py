import os
import sys
from datetime import datetime

# Add the parent directory to the path to import the application
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from user.models import User, SubscriptionPlan, Subscription, Payment

def init_db():
    """Initialize the database with sample data."""
    app = create_app()
    
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Check if we already have subscription plans
        if SubscriptionPlan.query.count() > 0:
            print("Database already contains subscription plans. Skipping initialization.")
            return
        
        # Create subscription plans
        basic_plan = SubscriptionPlan(
            name="Basic",
            description="Essential features for individuals",
            price=9.99,
            billing_cycle="month",
            features="5 scraping jobs per month,Up to 500 emails,Email export,Basic support",
            job_limit=5,
            email_limit=500,
            is_active=True
        )
        
        professional_plan = SubscriptionPlan(
            name="Professional",
            description="Advanced features for professionals",
            price=24.99,
            billing_cycle="month",
            features="15 scraping jobs per month,Up to 2000 emails,Email export,Priority support,Advanced filtering,Data enrichment",
            job_limit=15,
            email_limit=2000,
            is_active=True
        )
        
        enterprise_plan = SubscriptionPlan(
            name="Enterprise",
            description="Complete solution for businesses",
            price=49.99,
            billing_cycle="month",
            features="Unlimited scraping jobs,Unlimited emails,Email export,24/7 Premium support,Advanced filtering,Data enrichment,API access,Team collaboration",
            job_limit=100,
            email_limit=10000,
            is_active=True
        )
        
        free_plan = SubscriptionPlan(
            name="Free",
            description="Basic features for trying out the service",
            price=0.00,
            billing_cycle="month",
            features="1 scraping job per month,Up to 50 emails,Email export",
            job_limit=1,
            email_limit=50,
            is_active=True
        )
        
        # Add plans to the session
        db.session.add(basic_plan)
        db.session.add(professional_plan)
        db.session.add(enterprise_plan)
        db.session.add(free_plan)
        
        # Create admin user if it doesn't exist
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                email='admin@contacthound.com',
                password='pbkdf2:sha256:150000$VukD9RYQ$499c6a176a643a7e174374b69cc5f46b916e164522a5ad5a1c07ff87b4fcd449',  # 'password'
                first_name='Admin',
                last_name='User',
                is_active=True,
                is_admin=True,
                created_at=datetime.utcnow(),
                last_login=datetime.utcnow()
            )
            db.session.add(admin)
        
        # Create test user if it doesn't exist
        test_user = User.query.filter_by(username='testuser').first()
        if not test_user:
            test_user = User(
                username='testuser',
                email='test@example.com',
                password='pbkdf2:sha256:150000$VukD9RYQ$499c6a176a643a7e174374b69cc5f46b916e164522a5ad5a1c07ff87b4fcd449',  # 'password'
                first_name='Test',
                last_name='User',
                is_active=True,
                is_admin=False,
                created_at=datetime.utcnow(),
                last_login=datetime.utcnow()
            )
            db.session.add(test_user)
            
            # Assign professional plan to test user
            db.session.flush()  # Flush to get IDs
            
            subscription = Subscription(
                user_id=test_user.id,
                plan_id=professional_plan.id,
                status='active',
                start_date=datetime.utcnow()
            )
            db.session.add(subscription)
            
            # Add a payment method for test user
            payment = Payment(
                user_id=test_user.id,
                subscription_id=1,  # This will be the ID of the subscription
                amount=24.99,
                currency='USD',
                payment_type='visa',
                last_four='4242',
                expiry_month='12',
                expiry_year='24',
                is_default=True,
                status='successful',
                invoice_id='INV-2023-001',
                description='Professional Plan - Monthly Subscription',
                created_at=datetime.utcnow()
            )
            db.session.add(payment)
        
        # Commit all changes
        db.session.commit()
        
        print("Database initialized with subscription plans and test users.")

if __name__ == '__main__':
    init_db() 