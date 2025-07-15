from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, jsonify, current_app, session
from flask_login import login_required, current_user, login_user
from sqlalchemy import func, desc, cast, Date
from datetime import datetime, timedelta
import calendar
import json
import os

from models import db, User, UserRole, Role, ScrapeJob, Subscription, SubscriptionPlan, BlogPost, BlogCategory, BlogTag, ScrapeJobHistory, ApiKey, SiteSetting, Page, Payment
from auth import admin_required, editor_required
from utils import unique_slug, save_image, delete_image, generate_api_key, get_setting, format_date

# Create blueprint
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Decorator to require admin access
def admin_required(f):
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.has_role('admin'):
            abort(403)
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

# Dashboard
@admin_bp.route('/')
@admin_required
def dashboard():
    """Display admin dashboard with statistics"""
    # User statistics
    total_users = User.query.count()
    admin_users = User.query.join(User.roles).filter(Role.name == UserRole.ADMIN.value).count()
    new_users = User.query.filter(User.created_at >= (datetime.utcnow() - timedelta(days=7))).count()
    
    # Subscription statistics
    total_subscriptions = Subscription.query.count()
    active_subscriptions = Subscription.query.filter_by(is_active=True).count()
    
    # Content statistics
    blog_posts = 0
    blog_categories = 0
    
    try:
        blog_posts = BlogPost.query.count()
        blog_categories = BlogCategory.query.count()
    except:
        # Tables might not exist yet
        pass
    
    # Get page statistics
    pages = 0
    try:
        pages = Page.query.count()
    except:
        pass
    
    # Get job statistics
    jobs_count = 0
    active_jobs = 0
    total_emails = 0
    try:
        jobs_count = ScrapeJob.query.count()
        # Count active jobs (you might need to adjust this based on your job status field)
        active_jobs = ScrapeJob.query.filter_by(status='in_progress').count()
        # Sum up total emails found (you might need to adjust this based on your schema)
        total_emails = ScrapeJob.query.with_entities(func.sum(ScrapeJob.emails_found)).scalar() or 0
    except:
        pass
    
    # Calculate pending comments count
    pending_comments_count = 0
    try:
        # Import BlogComment from models if available
        from models import BlogComment
        pending_comments_count = BlogComment.query.filter_by(approved=False).count()
    except:
        # BlogComment table or module might not exist
        pass
    
    # Recent activity
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    
    # Create stats object to match template expectations
    stats = {
        'total_users': total_users,
        'admin_users': admin_users,
        'new_users': new_users,
        'total_subscriptions': total_subscriptions,
        'active_subscriptions': active_subscriptions,
        'blog_posts': blog_posts,
        'blog_categories': blog_categories,
        'pages': pages,
        'jobs_count': jobs_count,
        'active_jobs': active_jobs,
        'total_emails': total_emails,
        'pending_comments_count': pending_comments_count
    }
    
    return render_template('admin/dashboard.html',
                           stats=stats,
                           recent_users=recent_users)

# User Management routes
@admin_bp.route('/users')
@admin_required
def users():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # Base query
    query = User.query
    
    # Apply filters if provided
    search = request.args.get('search', '')
    if search:
        query = query.filter(
            (User.username.ilike(f'%{search}%')) |
            (User.email.ilike(f'%{search}%')) |
            (User.first_name.ilike(f'%{search}%')) |
            (User.last_name.ilike(f'%{search}%'))
        )
    
    role_id = request.args.get('role', '')
    if role_id:
        query = query.filter(User.roles.any(Role.id == role_id))
    
    status = request.args.get('status', '')
    if status == 'active':
        query = query.filter(User.is_active == True)
    elif status == 'inactive':
        query = query.filter(User.is_active == False)
    
    subscription_id = request.args.get('subscription', '')
    if subscription_id:
        query = query.join(User.subscriptions).filter(
            Subscription.plan_id == subscription_id,
            Subscription.status == 'active'
        )
    
    # Pagination
    pagination = query.order_by(User.created_at.desc()).paginate(page=page, per_page=per_page)
    users = pagination.items
    
    # Get all roles and subscription plans for the filter form
    roles = Role.query.all()
    subscription_plans = SubscriptionPlan.query.all()
    
    # Pagination metadata
    pagination_info = {
        'page': page,
        'pages': pagination.pages,
        'total': pagination.total,
        'offset': (page - 1) * per_page
    }
    
    return render_template('admin/users.html', 
                          users=users, 
                          roles=roles,
                          subscription_plans=subscription_plans,
                          pagination=pagination_info)

@admin_bp.route('/users/create', methods=['GET', 'POST'])
@admin_required
def create_user():
    if request.method == 'POST':
        # Extract form data
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        
        # Check if user with the same email or username already exists
        existing_user = User.query.filter((User.email == email) | (User.username == username)).first()
        if existing_user:
            flash('A user with this email or username already exists.', 'danger')
            return redirect(url_for('admin.create_user'))
        
        # Create new user
        user = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            is_active=request.form.get('is_active') == 'on'
        )
        
        # Set password
        user.set_password(password)
        
        # Handle profile image if uploaded
        if 'profile_image' in request.files and request.files['profile_image'].filename:
            filename = save_image(request.files['profile_image'], folder='profile_images')
            if filename:
                user.profile_image = filename
        
        # Add user to database
        db.session.add(user)
        db.session.flush()  # Get user ID without committing
        
        # Assign roles
        role_ids = request.form.getlist('roles')
        if role_ids:
            roles = Role.query.filter(Role.id.in_(role_ids)).all()
            for role in roles:
                user.roles.append(role)
        
        # Handle subscription
        subscription_plan_id = request.form.get('subscription_plan')
        if subscription_plan_id:
            # End any existing active subscriptions
            for sub in user.subscriptions:
                if sub.status == 'active':
                    sub.status = 'canceled'
                    sub.end_date = datetime.utcnow()
            
            # Create new subscription
            subscription = Subscription(
                user_id=user.id,
                plan_id=subscription_plan_id,
                status=request.form.get('subscription_status', 'active'),
                start_date=datetime.strptime(request.form.get('subscription_start'), '%Y-%m-%d') if request.form.get('subscription_start') else datetime.utcnow(),
                end_date=datetime.strptime(request.form.get('subscription_end'), '%Y-%m-%d') if request.form.get('subscription_end') else datetime.utcnow() + timedelta(days=30)
            )
            db.session.add(subscription)
        
        db.session.commit()
        flash('User created successfully!', 'success')
        return redirect(url_for('admin.users'))
    
    # For GET request
    roles = Role.query.all()
    subscription_plans = SubscriptionPlan.query.all()
    
    # List of countries for the form
    countries = [
        ("US", "United States"),
        ("GB", "United Kingdom"),
        ("CA", "Canada"),
        ("AU", "Australia"),
        ("DE", "Germany"),
        ("FR", "France"),
        # Add more countries as needed
    ]
    
    return render_template('admin/user_form.html', 
                          user=None,
                          roles=roles,
                          subscription_plans=subscription_plans,
                          countries=countries)

@admin_bp.route('/users/<int:user_id>/edit', methods=['GET'])
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    roles = Role.query.all()
    subscription_plans = SubscriptionPlan.query.all()
    
    # List of countries for the form
    countries = [
        ("US", "United States"),
        ("GB", "United Kingdom"),
        ("CA", "Canada"),
        ("AU", "Australia"),
        ("DE", "Germany"),
        ("FR", "France"),
        # Add more countries as needed
    ]
    
    return render_template('admin/user_form.html', 
                          user=user,
                          roles=roles,
                          subscription_plans=subscription_plans,
                          countries=countries)

@admin_bp.route('/users/<int:user_id>/update', methods=['POST'])
@admin_required
def update_user(user_id):
    user = User.query.get_or_404(user_id)
    
    # Update basic information (only fields that exist in User model)
    user.username = request.form.get('username')
    user.email = request.form.get('email')
    user.first_name = request.form.get('first_name')
    user.last_name = request.form.get('last_name')
    user.is_active = request.form.get('is_active') == 'on'
    
    # Update custom scrape limit (admin-controlled)
    custom_limit = request.form.get('custom_scrape_limit')
    if custom_limit and custom_limit.strip():
        try:
            user.custom_scrape_limit = int(custom_limit) if custom_limit != '0' else None
        except ValueError:
            user.custom_scrape_limit = None
    else:
        user.custom_scrape_limit = None
    
    # Update password if provided
    if request.form.get('password') and request.form.get('password') == request.form.get('confirm_password'):
        user.set_password(request.form.get('password'))
    
    # Handle profile image if uploaded
    if 'profile_image' in request.files and request.files['profile_image'].filename:
        # Delete old image if exists
        if user.profile_picture:
            delete_image(user.profile_picture, folder='profile_images')
        
        # Save new image
        filename = save_image(request.files['profile_image'], folder='profile_images')
        if filename:
            user.profile_picture = filename
    
    # Update roles
    user.roles = []  # Clear existing roles
    role_ids = request.form.getlist('roles')
    if role_ids:
        roles = Role.query.filter(Role.id.in_(role_ids)).all()
        for role in roles:
            user.roles.append(role)
    
    # Handle subscription
    subscription_plan_id = request.form.get('subscription_plan')
    if subscription_plan_id:
        # End any existing active subscriptions
        for sub in user.subscriptions:
            if sub.status == 'active':
                sub.status = 'canceled'
                sub.end_date = datetime.utcnow()
        
        # Create new subscription
        subscription = Subscription(
            user_id=user.id,
            plan_id=subscription_plan_id,
            status=request.form.get('subscription_status', 'active'),
            start_date=datetime.strptime(request.form.get('subscription_start'), '%Y-%m-%d') if request.form.get('subscription_start') else datetime.utcnow(),
            end_date=datetime.strptime(request.form.get('subscription_end'), '%Y-%m-%d') if request.form.get('subscription_end') else datetime.utcnow() + timedelta(days=30)
        )
        db.session.add(subscription)
    
    db.session.commit()
    flash('User updated successfully!', 'success')
    return redirect(url_for('admin.users'))

@admin_bp.route('/users/<int:user_id>/delete')
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    
    # Prevent deleting yourself
    if user.id == current_user.id:
        flash('You cannot delete your own account!', 'danger')
        return redirect(url_for('admin.users'))
    
    # Delete profile picture if exists
    if user.profile_picture:
        delete_image(user.profile_picture, folder='profile_images')
    
    # Delete user
    db.session.delete(user)
    db.session.commit()
    
    flash('User deleted successfully!', 'success')
    return redirect(url_for('admin.users'))

@admin_bp.route('/users/<int:user_id>/login-as')
@admin_required
def login_as_user(user_id):
    # Store current user's ID in session to restore later
    session['admin_id'] = current_user.id
    
    # Login as the target user
    user = User.query.get_or_404(user_id)
    login_user(user)
    
    flash(f'You are now logged in as {user.username}. Return to admin to revert back.', 'info')
    return redirect(url_for('main.index'))

@admin_bp.route('/return-to-admin')
@login_required
def return_to_admin():
    # Check if admin_id is in session
    if 'admin_id' not in session:
        abort(403)
    
    # Login back as admin
    admin_id = session.pop('admin_id')
    admin_user = User.query.get_or_404(admin_id)
    login_user(admin_user)
    
    flash('You have returned to your admin account.', 'info')
    return redirect(url_for('admin.dashboard'))

# Role Management routes
@admin_bp.route('/roles')
@admin_required
def roles():
    roles = Role.query.all()
    return render_template('admin/roles.html', roles=roles)

@admin_bp.route('/roles/create', methods=['GET', 'POST'])
@admin_required
def create_role():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description', '')
        
        # Check if role already exists
        existing_role = Role.query.filter_by(name=name).first()
        if existing_role:
            flash('A role with this name already exists.', 'danger')
            return redirect(url_for('admin.create_role'))
        
        # Create new role
        role = Role(name=name, description=description)
        db.session.add(role)
        db.session.commit()
        
        flash('Role created successfully!', 'success')
        return redirect(url_for('admin.roles'))
    
    return render_template('admin/role_form.html', role=None)

@admin_bp.route('/roles/<int:role_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_role(role_id):
    role = Role.query.get_or_404(role_id)
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description', '')
        
        # Check if role name changed and already exists
        if name != role.name and Role.query.filter_by(name=name).first():
            flash('A role with this name already exists.', 'danger')
            return redirect(url_for('admin.edit_role', role_id=role.id))
        
        # Update role
        role.name = name
        role.description = description
        db.session.commit()
        
        flash('Role updated successfully!', 'success')
        return redirect(url_for('admin.roles'))
    
    return render_template('admin/role_form.html', role=role)

@admin_bp.route('/roles/<int:role_id>/delete')
@admin_required
def delete_role(role_id):
    role = Role.query.get_or_404(role_id)
    
    # Prevent deleting default roles
    if role.name in ['admin', 'user']:
        flash('You cannot delete default roles!', 'danger')
        return redirect(url_for('admin.roles'))
    
    db.session.delete(role)
    db.session.commit()
    
    flash('Role deleted successfully!', 'success')
    return redirect(url_for('admin.roles'))

# Profile Management
@admin_bp.route('/profile')
@login_required
def profile():
    return render_template('admin/profile.html', user=current_user)

@admin_bp.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    # Update user profile fields (only fields that exist in User model)
    current_user.first_name = request.form.get('first_name')
    current_user.last_name = request.form.get('last_name')
    
    # Update password if provided
    if request.form.get('password') and request.form.get('password') == request.form.get('confirm_password'):
        current_user.set_password(request.form.get('password'))
    
    # Handle profile image if uploaded
    if 'profile_image' in request.files and request.files['profile_image'].filename:
        # Delete old image if exists
        if current_user.profile_picture:
            delete_image(current_user.profile_picture, folder='profile_images')
        
        # Save new image
        filename = save_image(request.files['profile_image'], folder='profile_images')
        if filename:
            current_user.profile_picture = filename
    
    db.session.commit()
    flash('Profile updated successfully!', 'success')
    return redirect(url_for('admin.profile'))

# Activity Log
@admin_bp.route('/activity-log')
@login_required
def activity_log():
    """Display user activity logs"""
    # Get query parameters for filtering
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # In a real implementation, you would have an ActivityLog model
    # For now, let's create a simple demo log using ScrapeJobHistory
    
    # Get scrape job history as a placeholder for activity
    if current_user.is_admin():
        # Admin sees all jobs
        query = ScrapeJobHistory.query.join(User)
    else:
        # Regular users see only their own
        query = ScrapeJobHistory.query.filter_by(user_id=current_user.id)
    
    # Apply filters
    user_id = request.args.get('user_id', type=int)
    if user_id:
        query = query.filter(ScrapeJobHistory.user_id == user_id)
    
    action_type = request.args.get('action_type')
    if action_type:
        query = query.filter(ScrapeJobHistory.status == action_type)
    
    # Date range filter
    date_from = request.args.get('date_from')
    if date_from:
        try:
            date_from = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(ScrapeJobHistory.created_at >= date_from)
        except ValueError:
            pass
    
    date_to = request.args.get('date_to')
    if date_to:
        try:
            date_to = datetime.strptime(date_to, '%Y-%m-%d')
            date_to = date_to.replace(hour=23, minute=59, second=59)
            query = query.filter(ScrapeJobHistory.created_at <= date_to)
        except ValueError:
            pass
    
    # Order by most recent first
    query = query.order_by(ScrapeJobHistory.created_at.desc())
    
    # Paginate results
    pagination = query.paginate(page=page, per_page=per_page)
    activities = pagination.items
    
    # Get users for filter dropdown
    users = User.query.all() if current_user.is_admin() else [current_user]
    
    # Action types for filter dropdown
    action_types = ['completed', 'failed', 'in_progress']
    
    return render_template('admin/activity_log.html', 
                          activities=activities,
                          pagination=pagination,
                          users=users,
                          action_types=action_types)

# Search
@admin_bp.route('/search')
@admin_required
def search():
    """Search across users, jobs, and settings"""
    query = request.args.get('q', '')
    if not query or len(query) < 2:
        return render_template('admin/search_results.html', query=query, results={})
    
    # Initialize results dictionary
    results = {
        'users': [],
        'jobs': [],
        'blog_posts': [],
        'pages': [],
        'settings': []
    }
    
    # Search users
    users = User.query.filter(
        (User.username.ilike(f"%{query}%")) |
        (User.email.ilike(f"%{query}%")) |
        (User.first_name.ilike(f"%{query}%")) |
        (User.last_name.ilike(f"%{query}%"))
    ).limit(10).all()
    results['users'] = users
    
    # Search scrape jobs
    jobs = ScrapeJob.query.filter(
        ScrapeJob.job_id.ilike(f"%{query}%")
    ).order_by(ScrapeJob.created_at.desc()).limit(10).all()
    results['jobs'] = jobs
    
    # Search blog posts if they exist in the database
    blog_posts = BlogPost.query.filter(
        (BlogPost.title.ilike(f"%{query}%")) |
        (BlogPost.content.ilike(f"%{query}%"))
    ).order_by(BlogPost.created_at.desc()).limit(10).all()
    results['blog_posts'] = blog_posts
    
    # Search pages
    pages = Page.query.filter(
        (Page.title.ilike(f"%{query}%")) |
        (Page.content.ilike(f"%{query}%"))
    ).order_by(Page.updated_at.desc()).limit(10).all()
    results['pages'] = pages
    
    # Search settings
    settings = SiteSetting.query.filter(
        (SiteSetting.key.ilike(f"%{query}%")) |
        (SiteSetting.value.ilike(f"%{query}%"))
    ).limit(10).all()
    results['settings'] = settings
    
    return render_template('admin/search_results.html', query=query, results=results)

# Helper functions for dashboard
def get_user_growth_data():
    """Get user growth data for charts"""
    # Last 12 months of user registrations
    months = []
    counts = []
    
    for i in range(11, -1, -1):
        date = datetime.utcnow() - timedelta(days=i*30)
        start_date = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        if i > 0:
            end_date = (date.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)
        else:
            end_date = datetime.utcnow()
            
        count = User.query.filter(User.created_at.between(start_date, end_date)).count()
        
        months.append(start_date.strftime('%b %Y'))
        counts.append(count)
    
    return {'labels': months, 'data': counts}

def get_jobs_data():
    """Get job statistics for charts"""
    # Categorize jobs by status
    statuses = ['completed', 'error', 'in_progress']
    counts = []
    
    for status in statuses:
        count = ScrapeJobHistory.query.filter_by(status=status).count()
        counts.append(count)
    
    return {'labels': statuses, 'data': counts}

def get_revenue_data():
    """Get revenue data for charts"""
    # Last 6 months of revenue
    months = []
    revenues = []
    
    for i in range(5, -1, -1):
        date = datetime.utcnow() - timedelta(days=i*30)
        start_date = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        if i > 0:
            end_date = (date.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)
        else:
            end_date = datetime.utcnow()
            
        payments = Payment.query.filter(Payment.payment_date.between(start_date, end_date)).all()
        revenue = sum(payment.amount for payment in payments)
        
        months.append(start_date.strftime('%b %Y'))
        revenues.append(revenue)
    
    return {'labels': months, 'data': revenues} 