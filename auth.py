from flask import Blueprint, render_template, redirect, url_for, flash, request, session, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import secrets
import os
from functools import wraps
import pyotp
import qrcode
from io import BytesIO
import base64
import jwt
from urllib.parse import urlencode

from models import db, User, Role, UserRole
from utils import send_email

# Create blueprint
auth_bp = Blueprint('auth', __name__)

# Decorator for admin-only routes
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

# Decorator for editor or admin routes
def editor_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or (not current_user.has_role(UserRole.EDITOR.value) and not current_user.is_admin()):
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.is_admin():
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('user.dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = 'remember' in request.form
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            if not user.is_active:
                flash('Your account is inactive. Please contact the administrator.', 'danger')
                return redirect(url_for('auth.login'))
            
            # Check if 2FA is enabled
            if user.two_factor_enabled:
                session['user_id'] = user.id
                return redirect(url_for('auth.two_factor_auth'))
            
            # Update last login time
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            login_user(user, remember=remember)
            flash('Login successful!', 'success')
            
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                if user.is_admin():
                    next_page = url_for('admin.dashboard')
                else:
                    next_page = url_for('user.dashboard')
            
            return redirect(next_page)
        else:
            flash('Invalid email or password. Please try again.', 'danger')
    
    # Generate OAuth URLs if configured
    google_oauth_url = None
    if current_app.config.get('GOOGLE_CLIENT_ID'):
        google_oauth_url = url_for('auth.oauth_login', provider='google')
    
    return render_template('auth/login.html', google_oauth_url=google_oauth_url)

@auth_bp.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated:
        if current_user.is_admin():
            return redirect(url_for('admin.dashboard'))
        else:
            flash('You do not have permission to access the admin area.', 'danger')
            return redirect(url_for('user.dashboard'))
    
    if request.method == 'POST':
        identifier = request.form.get('identifier')
        password = request.form.get('password')
        remember = 'remember' in request.form
        
        # Validate input
        if not identifier or not password:
            flash('Please provide both identifier and password.', 'danger')
            return render_template('auth/admin_login.html', now=datetime.utcnow())
        
        # Check if identifier is an email (contains @) or username
        if '@' in identifier:
            user = User.query.filter_by(email=identifier).first()
        else:
            user = User.query.filter_by(username=identifier).first()
        
        if user and user.check_password(password):
            if not user.is_active:
                flash('Your account is inactive. Please contact the administrator.', 'danger')
                return redirect(url_for('auth.admin_login'))
            
            # Check if user is an admin
            if not user.is_admin():
                flash('You do not have permission to access the admin area.', 'danger')
                return redirect(url_for('auth.user_login'))
            
            # Check if 2FA is enabled
            if user.two_factor_enabled:
                session['user_id'] = user.id
                session['admin_login'] = True
                return redirect(url_for('auth.two_factor_auth'))
            
            # Update last login time
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            login_user(user, remember=remember)
            flash('Admin login successful!', 'success')
            
            return redirect(url_for('admin.dashboard'))
        else:
            flash('Invalid admin credentials. Please try again.', 'danger')
    
    return render_template('auth/admin_login.html', now=datetime.utcnow())

@auth_bp.route('/user', methods=['GET', 'POST'])
def user_login():
    if current_user.is_authenticated:
        return redirect(url_for('user.dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = 'remember' in request.form
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            if not user.is_active:
                flash('Your account is inactive. Please contact the administrator.', 'danger')
                return redirect(url_for('auth.user_login'))
            
            # Check if 2FA is enabled
            if user.two_factor_enabled:
                session['user_id'] = user.id
                session['user_login'] = True
                return redirect(url_for('auth.two_factor_auth'))
            
            # Update last login time
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            login_user(user, remember=remember)
            flash('Login successful!', 'success')
            
            # Redirect based on user role
            if user.is_admin():
                return redirect(url_for('admin.dashboard'))
            else:
                return redirect(url_for('user.dashboard'))
        else:
            flash('Invalid email or password. Please try again.', 'danger')
    
    # Generate OAuth URLs if configured
    google_oauth_url = None
    if current_app.config.get('GOOGLE_CLIENT_ID'):
        google_oauth_url = url_for('auth.oauth_login', provider='google')
    
    return render_template('auth/user_login.html', google_oauth_url=google_oauth_url)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('auth.login'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        if current_user.is_admin():
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('user.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        
        # Basic validation
        if not all([username, email, password, confirm_password]):
            flash('All fields are required.', 'danger')
            return redirect(url_for('auth.register'))
        
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('auth.register'))
        
        # Check if username or email already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists. Please choose another.', 'danger')
            return redirect(url_for('auth.register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered. Please log in or use a different email.', 'danger')
            return redirect(url_for('auth.register'))
        
        # Create new user
        new_user = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            created_at=datetime.utcnow()
        )
        new_user.set_password(password)
        
        # Assign default user role
        user_role = Role.query.filter_by(name=UserRole.USER.value).first()
        if user_role:
            new_user.roles.append(user_role)
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html')

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        if current_user.is_admin():
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('user.dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        
        if user:
            # Generate token
            token = generate_reset_token(user.id)
            
            # Create reset URL
            reset_url = url_for('auth.reset_password', token=token, _external=True)
            
            # Send email
            send_email(
                subject='Password Reset Request',
                recipients=[user.email],
                body=f'Click the following link to reset your password: {reset_url}\nThis link will expire in 1 hour.',
                html=render_template('emails/password_reset.html', reset_url=reset_url, user=user)
            )
        
        # Always show success message to prevent email enumeration
        flash('If your email is registered, you will receive password reset instructions shortly.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/forgot_password.html')

@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        if current_user.is_admin():
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('user.dashboard'))
    
    # Verify token
    try:
        user_id = verify_reset_token(token)
        user = User.query.get(user_id)
        if not user:
            flash('Invalid or expired token. Please try again.', 'danger')
            return redirect(url_for('auth.forgot_password'))
    except:
        flash('Invalid or expired token. Please try again.', 'danger')
        return redirect(url_for('auth.forgot_password'))
    
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if not password or not confirm_password:
            flash('All fields are required.', 'danger')
            return redirect(url_for('auth.reset_password', token=token))
        
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('auth.reset_password', token=token))
        
        # Update password
        user.set_password(password)
        db.session.commit()
        
        flash('Your password has been updated! You can now log in with your new password.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/reset_password.html', token=token)

@auth_bp.route('/two-factor', methods=['GET', 'POST'])
def two_factor_auth():
    if 'user_id' not in session:
        flash('Please log in first.', 'danger')
        return redirect(url_for('auth.login'))
    
    user = User.query.get(session['user_id'])
    if not user or not user.two_factor_enabled:
        flash('Two-factor authentication is not enabled for this account.', 'danger')
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        token = request.form.get('token')
        totp = pyotp.TOTP(user.two_factor_secret)
        
        if totp.verify(token):
            # Update last login time
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            login_user(user)
            # Check if this is an admin login or user login
            is_admin_login = session.pop('admin_login', False)
            is_user_login = session.pop('user_login', False)
            session.pop('user_id', None)
            
            flash('Two-factor authentication successful!', 'success')
            
            if is_admin_login:
                return redirect(url_for('admin.dashboard'))
            elif is_user_login or not user.is_admin():
                return redirect(url_for('user.dashboard'))
            else:
                # Default to admin dashboard for admin users
                return redirect(url_for('admin.dashboard'))
        else:
            flash('Invalid authentication code. Please try again.', 'danger')
    
    # Determine which login form to return to if canceled
    is_admin_login = session.get('admin_login', False)
    is_user_login = session.get('user_login', False)
    
    if is_admin_login:
        return_url = url_for('auth.admin_login')
    elif is_user_login:
        return_url = url_for('auth.user_login')
    else:
        return_url = url_for('auth.login')
    
    return render_template('auth/two_factor.html', return_url=return_url)

@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'update_profile':
            current_user.first_name = request.form.get('first_name')
            current_user.last_name = request.form.get('last_name')
            current_user.username = request.form.get('username')
            
            # Check if username is already taken by another user
            if User.query.filter(User.username == current_user.username, User.id != current_user.id).first():
                flash('Username already exists. Please choose another.', 'danger')
            else:
                db.session.commit()
                flash('Profile updated successfully!', 'success')
        
        elif action == 'change_password':
            current_password = request.form.get('current_password')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')
            
            if not current_user.check_password(current_password):
                flash('Current password is incorrect.', 'danger')
            elif new_password != confirm_password:
                flash('New passwords do not match.', 'danger')
            else:
                current_user.set_password(new_password)
                db.session.commit()
                flash('Password changed successfully!', 'success')
        
        elif action == 'setup_2fa':
            # Generate new secret key
            secret = pyotp.random_base32()
            current_user.two_factor_secret = secret
            db.session.commit()
            
            # Generate QR code
            totp = pyotp.TOTP(secret)
            uri = totp.provisioning_uri(current_user.email, issuer_name="Contact Harvester Pro")
            
            img = qrcode.make(uri)
            buffered = BytesIO()
            img.save(buffered)
            qr_code = base64.b64encode(buffered.getvalue()).decode()
            
            flash('Two-factor authentication has been set up. Scan the QR code with your authenticator app.', 'success')
            return render_template('auth/profile.html', qr_code=qr_code, secret=secret)
        
        elif action == 'verify_2fa':
            token = request.form.get('token')
            totp = pyotp.TOTP(current_user.two_factor_secret)
            
            if totp.verify(token):
                current_user.two_factor_enabled = True
                db.session.commit()
                flash('Two-factor authentication has been enabled successfully!', 'success')
            else:
                flash('Invalid authentication code. Please try again.', 'danger')
        
        elif action == 'disable_2fa':
            current_user.two_factor_enabled = False
            db.session.commit()
            flash('Two-factor authentication has been disabled.', 'success')
    
    return render_template('auth/profile.html')

@auth_bp.route('/oauth/<provider>')
def oauth_login(provider):
    """Redirect to OAuth provider's authorization page"""
    if provider == 'google':
        # Google OAuth configuration
        client_id = current_app.config.get('GOOGLE_CLIENT_ID')
        redirect_uri = url_for('auth.oauth_callback', provider='google', _external=True)
        scope = 'email profile'
        
        # Create authorization URL
        params = {
            'client_id': client_id,
            'redirect_uri': redirect_uri,
            'scope': scope,
            'response_type': 'code',
            'access_type': 'offline',
            'prompt': 'consent'
        }
        authorize_url = 'https://accounts.google.com/o/oauth2/auth?' + urlencode(params)
        
        return redirect(authorize_url)
    
    flash('Unsupported OAuth provider.', 'danger')
    return redirect(url_for('auth.login'))

@auth_bp.route('/oauth/callback/<provider>')
def oauth_callback(provider):
    """Handle OAuth callback from provider"""
    code = request.args.get('code')
    
    if not code:
        flash('Authentication failed. Please try again.', 'danger')
        return redirect(url_for('auth.login'))
    
    if provider == 'google':
        try:
            # Exchange code for token
            client_id = current_app.config.get('GOOGLE_CLIENT_ID')
            client_secret = current_app.config.get('GOOGLE_CLIENT_SECRET')
            redirect_uri = url_for('auth.oauth_callback', provider='google', _external=True)
            
            token_url = 'https://oauth2.googleapis.com/token'
            token_data = {
                'code': code,
                'client_id': client_id,
                'client_secret': client_secret,
                'redirect_uri': redirect_uri,
                'grant_type': 'authorization_code'
            }
            
            import requests
            token_response = requests.post(token_url, data=token_data)
            token_json = token_response.json()
            
            access_token = token_json.get('access_token')
            
            # Get user info
            user_info_url = 'https://www.googleapis.com/oauth2/v1/userinfo'
            headers = {'Authorization': f'Bearer {access_token}'}
            user_info_response = requests.get(user_info_url, headers=headers)
            user_info = user_info_response.json()
            
            # Check if user exists
            email = user_info.get('email')
            user = User.query.filter_by(email=email).first()
            
            if user:
                # Update OAuth information if needed
                if not user.oauth_provider or not user.oauth_id:
                    user.oauth_provider = 'google'
                    user.oauth_id = user_info.get('id')
                    db.session.commit()
            else:
                # Create new user
                new_user = User(
                    username=email.split('@')[0],  # Use part of email as username
                    email=email,
                    first_name=user_info.get('given_name', ''),
                    last_name=user_info.get('family_name', ''),
                    oauth_provider='google',
                    oauth_id=user_info.get('id'),
                    profile_picture=user_info.get('picture'),
                    created_at=datetime.utcnow()
                )
                
                # Generate a random password (user won't use it)
                random_password = secrets.token_urlsafe(16)
                new_user.set_password(random_password)
                
                # Assign default user role
                user_role = Role.query.filter_by(name=UserRole.USER.value).first()
                if user_role:
                    new_user.roles.append(user_role)
                
                db.session.add(new_user)
                db.session.commit()
                
                user = new_user
            
            # Log in the user
            login_user(user)
            flash('Login successful via Google!', 'success')
            return redirect(url_for('admin.dashboard'))
            
        except Exception as e:
            flash(f'OAuth authentication failed: {str(e)}', 'danger')
            return redirect(url_for('auth.login'))
    
    flash('Unsupported OAuth provider.', 'danger')
    return redirect(url_for('auth.login'))

# Helper functions
def generate_reset_token(user_id):
    """Generate JWT token for password reset"""
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(hours=1)
    }
    token = jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')
    return token

def verify_reset_token(token):
    """Verify JWT token for password reset"""
    try:
        payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
        return payload['user_id']
    except:
        return None 