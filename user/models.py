from datetime import datetime
from app import db
from models import User  # Import the existing User model

class SubscriptionPlan(db.Model):
    __tablename__ = 'subscription_plans'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    billing_cycle = db.Column(db.String(20), default='month', nullable=False)  # month, year
    features = db.Column(db.Text)  # Comma-separated list of features
    job_limit = db.Column(db.Integer, default=10)  # Number of jobs allowed
    email_limit = db.Column(db.Integer, default=1000)  # Number of emails allowed
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    subscriptions = db.relationship('UserSubscription', backref='plan', lazy=True)
    
    def __repr__(self):
        return f'<SubscriptionPlan {self.name}>'


class UserSubscription(db.Model):
    __tablename__ = 'user_subscriptions'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    plan_id = db.Column(db.Integer, db.ForeignKey('subscription_plans.id'), nullable=False)
    status = db.Column(db.String(20), default='active')  # active, canceled, expired
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    end_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<UserSubscription {self.id}>'


class Payment(db.Model):
    __tablename__ = 'payments'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    subscription_id = db.Column(db.Integer, db.ForeignKey('user_subscriptions.id'))
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default='USD')
    payment_type = db.Column(db.String(20))  # visa, mastercard, etc.
    last_four = db.Column(db.String(4))  # Last 4 digits of card
    expiry_month = db.Column(db.String(2))
    expiry_year = db.Column(db.String(2))
    is_default = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(20), default='pending')  # pending, successful, failed
    invoice_id = db.Column(db.String(50), unique=True)
    description = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Payment {self.invoice_id}>'


class Job(db.Model):
    __tablename__ = 'jobs'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    target_url = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, in_progress, completed, failed
    depth = db.Column(db.Integer, default=1)
    include_subdomains = db.Column(db.Boolean, default=False)
    verify_emails = db.Column(db.Boolean, default=True)
    emails_found = db.Column(db.Integer, default=0)
    pages_crawled = db.Column(db.Integer, default=0)
    unique_domains = db.Column(db.Integer, default=0)
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    
    # Relationships
    emails = db.relationship('Email', backref='job', lazy=True)
    
    def __repr__(self):
        return f'<Job {self.name}>'


class Email(db.Model):
    __tablename__ = 'emails'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey('jobs.id'), nullable=False)
    address = db.Column(db.String(120), nullable=False)
    domain = db.Column(db.String(100))
    source_url = db.Column(db.String(255))
    is_valid = db.Column(db.Boolean)
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    position = db.Column(db.String(100))
    company = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Email {self.address}>' 