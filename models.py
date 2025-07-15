from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import enum

db = SQLAlchemy()

# Role definitions
class UserRole(enum.Enum):
    ADMIN = "admin"
    EDITOR = "editor"
    USER = "user"

# Association table for users and roles
user_roles = db.Table('user_roles',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id')),
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id'))
)

# User model
class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    profile_picture = db.Column(db.String(255))
    last_login = db.Column(db.DateTime)
    
    # OAuth related fields
    oauth_provider = db.Column(db.String(50))  # e.g., 'google', 'facebook'
    oauth_id = db.Column(db.String(255))
    
    # Subscription related fields
    subscription_id = db.Column(db.Integer, db.ForeignKey('subscriptions.id'))
    subscription_end_date = db.Column(db.DateTime)
    
    # Two-factor authentication
    two_factor_enabled = db.Column(db.Boolean, default=False)
    two_factor_secret = db.Column(db.String(255))
    
    # Usage limits - Admin controlled
    custom_scrape_limit = db.Column(db.Integer, nullable=True)  # If set, overrides default limits
    
    # Relationships
    roles = db.relationship('Role', secondary=user_roles, backref=db.backref('users', lazy='dynamic'))
    subscription = db.relationship('Subscription', backref='users', foreign_keys=[subscription_id])
    blog_posts = db.relationship('BlogPost', backref='author', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def has_role(self, role_name):
        return any(role.name == role_name for role in self.roles)
    
    def is_admin(self):
        return self.has_role(UserRole.ADMIN.value)
    
    def get_scrape_limit(self):
        """Get the effective scrape limit for this user"""
        # Admin users have unlimited access
        if self.is_admin():
            return float('inf')
        
        # If admin has set a custom limit, use that
        if self.custom_scrape_limit is not None:
            return self.custom_scrape_limit
        
        # If user has a subscription, use subscription limit
        if self.subscription and self.subscription.is_active:
            return self.subscription.scrape_limit
        
        # Default free user limit
        return 50

# Role model
class Role(db.Model):
    __tablename__ = 'roles'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(255))
    
    def __repr__(self):
        return f'<Role {self.name}>'

# Subscription model
class Subscription(db.Model):
    __tablename__ = 'subscriptions'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    duration_days = db.Column(db.Integer, nullable=False)  # Duration in days
    scrape_limit = db.Column(db.Integer, nullable=False)  # Number of URLs allowed
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('subscription_plans.id'))  # Add reference to subscription plan
    status = db.Column(db.String(50), default='active')  # active, expired, cancelled
    currency = db.Column(db.String(10), default='USD')
    is_public = db.Column(db.Boolean, default=True)
    is_featured = db.Column(db.Boolean, default=False)
    allow_cancellation = db.Column(db.Boolean, default=True)
    stripe_plan_id = db.Column(db.String(100))
    features = db.Column(db.Text)  # Stored as JSON or comma-separated values
    
    def __repr__(self):
        return f'<Subscription {self.name}>'

# SubscriptionPlan model
class SubscriptionPlan(db.Model):
    __tablename__ = 'subscription_plans'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    price = db.Column(db.Float, nullable=False)
    duration_days = db.Column(db.Integer, nullable=False)
    features = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    scrape_limit = db.Column(db.Integer, default=100)
    
    # Relationships
    subscriptions = db.relationship('Subscription', backref='plan')
    
    def __repr__(self):
        return f'<SubscriptionPlan {self.name}>'

# ScrapeJob model
class ScrapeJob(db.Model):
    __tablename__ = 'scrape_jobs'
    
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.String(100), nullable=False, unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    total_urls = db.Column(db.Integer, nullable=False)
    successful_urls = db.Column(db.Integer, default=0)
    emails_found = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    status = db.Column(db.String(50), default='in_progress')  # in_progress, completed, failed
    result_file = db.Column(db.String(255))
    
    # Relationship
    user = db.relationship('User', backref='scrape_jobs')
    
    def __repr__(self):
        return f'<ScrapeJob {self.job_id}>'

# BlogPost model
class BlogPost(db.Model):
    __tablename__ = 'blog_posts'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(255), unique=True, nullable=False)
    content = db.Column(db.Text, nullable=False)
    excerpt = db.Column(db.Text)
    featured_image = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    published = db.Column(db.Boolean, default=False)
    
    # SEO fields
    meta_title = db.Column(db.String(255))
    meta_description = db.Column(db.Text)
    
    # Foreign keys
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    category_id = db.Column(db.Integer, db.ForeignKey('blog_categories.id'))
    
    # Relationships
    category = db.relationship('BlogCategory', backref='posts')
    tags = db.relationship('BlogTag', secondary='post_tags', backref='posts')
    comments = db.relationship('BlogComment', backref='post', lazy='dynamic')
    
    def __repr__(self):
        return f'<BlogPost {self.title}>'

# BlogCategory model
class BlogCategory(db.Model):
    __tablename__ = 'blog_categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    
    def __repr__(self):
        return f'<BlogCategory {self.name}>'

# BlogTag model
class BlogTag(db.Model):
    __tablename__ = 'blog_tags'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    slug = db.Column(db.String(50), unique=True, nullable=False)
    
    def __repr__(self):
        return f'<BlogTag {self.name}>'

# Association table for posts and tags
post_tags = db.Table('post_tags',
    db.Column('post_id', db.Integer, db.ForeignKey('blog_posts.id')),
    db.Column('tag_id', db.Integer, db.ForeignKey('blog_tags.id'))
)

# BlogComment model
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
    
    def __repr__(self):
        return f'<BlogComment {self.id}>'

# Page model for custom pages
class Page(db.Model):
    __tablename__ = 'pages'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(255), unique=True, nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    published = db.Column(db.Boolean, default=True)
    
    # SEO fields
    meta_title = db.Column(db.String(255))
    meta_description = db.Column(db.Text)
    
    # Layout settings
    layout_template = db.Column(db.String(100), default='default')
    
    def __repr__(self):
        return f'<Page {self.title}>'

# ScrapeJobHistory model - tracks history of scraping jobs for users
class ScrapeJobHistory(db.Model):
    __tablename__ = 'scrape_job_history'
    
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    total_urls = db.Column(db.Integer, nullable=False)
    successful_urls = db.Column(db.Integer, default=0)
    emails_found = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    status = db.Column(db.String(50))  # 'completed', 'failed', 'in_progress'
    result_file = db.Column(db.String(255))
    
    # Relationship
    user = db.relationship('User', backref='job_history')
    
    def __repr__(self):
        return f'<ScrapeJobHistory {self.job_id}>'

# ApiKey model
class ApiKey(db.Model):
    __tablename__ = 'api_keys'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    key = db.Column(db.String(255), nullable=False, unique=True)
    name = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)
    last_used_at = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationship
    user = db.relationship('User', backref='api_keys')
    
    def __repr__(self):
        return f'<ApiKey {self.name}>'

# SiteSetting model
class SiteSetting(db.Model):
    __tablename__ = 'site_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), nullable=False, unique=True)
    value = db.Column(db.Text)
    category = db.Column(db.String(50))  # e.g., 'general', 'email', 'payment'
    
    def __repr__(self):
        return f'<SiteSetting {self.key}>'

# Payment model
class Payment(db.Model):
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    subscription_id = db.Column(db.Integer, db.ForeignKey('subscriptions.id'))
    amount = db.Column(db.Float, nullable=False)
    transaction_id = db.Column(db.String(255))
    payment_method = db.Column(db.String(50))  # e.g., 'credit_card', 'paypal'
    status = db.Column(db.String(50))  # e.g., 'succeeded', 'failed', 'pending'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='payments')
    # Temporarily removing this relationship to fix startup issues
    # subscription = db.relationship('Subscription', backref='payments', foreign_keys=[subscription_id])
    
    def __repr__(self):
        return f'<Payment {self.id}>' 