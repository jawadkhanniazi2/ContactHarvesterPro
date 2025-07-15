from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required
import os
import json
from datetime import datetime

from models import db, SiteSetting, Subscription, User
from auth import admin_required
from utils import save_image, delete_image

# Create blueprint
settings_bp = Blueprint('settings', __name__, url_prefix='/admin/settings')

@settings_bp.route('/')
@admin_required
def index():
    """Show settings dashboard"""
    return render_template('admin/settings/index.html')

@settings_bp.route('/site', methods=['GET', 'POST'])
@admin_required
def site():
    """Manage site settings"""
    if request.method == 'POST':
        # Get all settings
        site_name = request.form.get('site_name')
        site_description = request.form.get('site_description')
        site_keywords = request.form.get('site_keywords')
        contact_email = request.form.get('contact_email')
        footer_text = request.form.get('footer_text')
        google_analytics_id = request.form.get('google_analytics_id')
        maintenance_mode = 'maintenance_mode' in request.form
        
        # Save each setting
        update_setting('site_name', site_name)
        update_setting('site_description', site_description)
        update_setting('site_keywords', site_keywords)
        update_setting('contact_email', contact_email)
        update_setting('footer_text', footer_text)
        update_setting('google_analytics_id', google_analytics_id)
        update_setting('maintenance_mode', '1' if maintenance_mode else '0')
        
        # Handle logo upload
        if 'site_logo' in request.files and request.files['site_logo']:
            # Get current logo
            current_logo = get_setting('site_logo')
            
            # Delete old logo if exists
            if current_logo:
                delete_image(current_logo)
            
            # Save new logo
            logo_path = save_image(request.files['site_logo'], 'uploads/site', size=(300, 100))
            update_setting('site_logo', logo_path)
        
        # Handle favicon upload
        if 'favicon' in request.files and request.files['favicon']:
            # Get current favicon
            current_favicon = get_setting('favicon')
            
            # Delete old favicon if exists
            if current_favicon:
                delete_image(current_favicon)
            
            # Save new favicon
            favicon_path = save_image(request.files['favicon'], 'uploads/site', size=(32, 32))
            update_setting('favicon', favicon_path)
        
        flash('Site settings updated successfully!', 'success')
        return redirect(url_for('settings.site'))
    
    # Get all settings
    settings = {
        'site_name': get_setting('site_name', 'Contact Harvester Pro'),
        'site_description': get_setting('site_description', 'Extract emails, phones, and social media links from websites'),
        'site_keywords': get_setting('site_keywords', 'email scraper, contact extractor, lead generation'),
        'contact_email': get_setting('contact_email', 'contact@example.com'),
        'footer_text': get_setting('footer_text', '© 2025 Contact Harvester Pro. All rights reserved.'),
        'google_analytics_id': get_setting('google_analytics_id', ''),
        'maintenance_mode': get_setting('maintenance_mode', '0') == '1',
        'site_logo': get_setting('site_logo', ''),
        'favicon': get_setting('favicon', '')
    }
    
    return render_template('admin/settings/site.html', settings=settings)

@settings_bp.route('/email', methods=['GET', 'POST'])
@admin_required
def email():
    """Manage email settings"""
    if request.method == 'POST':
        # Get all settings
        mail_server = request.form.get('mail_server')
        mail_port = request.form.get('mail_port')
        mail_use_tls = 'mail_use_tls' in request.form
        mail_use_ssl = 'mail_use_ssl' in request.form
        mail_username = request.form.get('mail_username')
        mail_password = request.form.get('mail_password')
        mail_default_sender = request.form.get('mail_default_sender')
        
        # Save each setting
        update_setting('mail_server', mail_server)
        update_setting('mail_port', mail_port)
        update_setting('mail_use_tls', '1' if mail_use_tls else '0')
        update_setting('mail_use_ssl', '1' if mail_use_ssl else '0')
        update_setting('mail_username', mail_username)
        
        # Only update password if provided
        if mail_password:
            update_setting('mail_password', mail_password)
            
        update_setting('mail_default_sender', mail_default_sender)
        
        flash('Email settings updated successfully!', 'success')
        return redirect(url_for('settings.email'))
    
    # Get all settings
    settings = {
        'mail_server': get_setting('mail_server', 'smtp.gmail.com'),
        'mail_port': get_setting('mail_port', '587'),
        'mail_use_tls': get_setting('mail_use_tls', '1') == '1',
        'mail_use_ssl': get_setting('mail_use_ssl', '0') == '1',
        'mail_username': get_setting('mail_username', ''),
        'mail_password': '',  # Don't show password
        'mail_default_sender': get_setting('mail_default_sender', '')
    }
    
    return render_template('admin/settings/email.html', settings=settings)

@settings_bp.route('/payments', methods=['GET', 'POST'])
@admin_required
def payments():
    """Manage payment settings"""
    if request.method == 'POST':
        # Get all settings
        payment_currency = request.form.get('payment_currency')
        stripe_public_key = request.form.get('stripe_public_key')
        stripe_secret_key = request.form.get('stripe_secret_key')
        paypal_client_id = request.form.get('paypal_client_id')
        paypal_secret = request.form.get('paypal_secret')
        paypal_mode = request.form.get('paypal_mode')
        
        # Save each setting
        update_setting('payment_currency', payment_currency)
        update_setting('stripe_public_key', stripe_public_key)
        update_setting('stripe_secret_key', stripe_secret_key)
        update_setting('paypal_client_id', paypal_client_id)
        update_setting('paypal_secret', paypal_secret)
        update_setting('paypal_mode', paypal_mode)
        
        flash('Payment settings updated successfully!', 'success')
        return redirect(url_for('settings.payments'))
    
    # Get all settings
    settings = {
        'payment_currency': get_setting('payment_currency', 'USD'),
        'stripe_public_key': get_setting('stripe_public_key', ''),
        'stripe_secret_key': get_setting('stripe_secret_key', ''),
        'paypal_client_id': get_setting('paypal_client_id', ''),
        'paypal_secret': get_setting('paypal_secret', ''),
        'paypal_mode': get_setting('paypal_mode', 'sandbox')
    }
    
    # Currencies
    currencies = [
        {'code': 'USD', 'name': 'US Dollar'},
        {'code': 'EUR', 'name': 'Euro'},
        {'code': 'GBP', 'name': 'British Pound'},
        {'code': 'JPY', 'name': 'Japanese Yen'},
        {'code': 'CAD', 'name': 'Canadian Dollar'},
        {'code': 'AUD', 'name': 'Australian Dollar'}
    ]
    
    return render_template('admin/settings/payments.html', settings=settings, currencies=currencies)

@settings_bp.route('/subscription')
@admin_required
def subscription():
    """Manage subscription plans"""
    plans = Subscription.query.all()
    return render_template('admin/settings/subscription/index.html', plans=plans)

@settings_bp.route('/subscription/create', methods=['GET', 'POST'])
@admin_required
def add_subscription():
    """Create a new subscription plan"""
    if request.method == 'POST':
        name = request.form.get('name')
        price = float(request.form.get('price'))
        duration_days = int(request.form.get('duration_days'))
        scrape_limit = int(request.form.get('scrape_limit'))
        description = request.form.get('description')
        is_active = 'is_active' in request.form
        is_public = 'is_public' in request.form
        is_featured = 'is_featured' in request.form
        allow_cancellation = 'allow_cancellation' in request.form
        stripe_plan_id = request.form.get('stripe_plan_id')
        currency = request.form.get('currency')
        features = request.form.getlist('features')
        
        # Create subscription
        subscription = Subscription(
            name=name,
            price=price,
            currency=currency,
            duration_days=duration_days,
            scrape_limit=scrape_limit,
            description=description,
            is_active=is_active,
            is_public=is_public,
            is_featured=is_featured,
            allow_cancellation=allow_cancellation,
            stripe_plan_id=stripe_plan_id,
            features=features
        )
        
        db.session.add(subscription)
        db.session.commit()
        
        flash('Subscription plan created successfully!', 'success')
        return redirect(url_for('settings.subscription'))
    
    return render_template('admin/settings/subscription/create.html')

@settings_bp.route('/subscription/edit/<int:plan_id>', methods=['GET', 'POST'])
@admin_required
def edit_subscription(plan_id):
    """Edit an existing subscription plan"""
    plan = Subscription.query.get_or_404(plan_id)
    
    if request.method == 'POST':
        plan.name = request.form.get('name')
        plan.price = float(request.form.get('price'))
        plan.currency = request.form.get('currency')
        plan.duration_days = int(request.form.get('duration_days'))
        plan.scrape_limit = int(request.form.get('scrape_limit'))
        plan.description = request.form.get('description')
        plan.is_active = 'is_active' in request.form
        plan.is_public = 'is_public' in request.form
        plan.is_featured = 'is_featured' in request.form
        plan.allow_cancellation = 'allow_cancellation' in request.form
        plan.stripe_plan_id = request.form.get('stripe_plan_id')
        plan.features = request.form.getlist('features')
        
        db.session.commit()
        
        flash('Subscription plan updated successfully!', 'success')
        return redirect(url_for('settings.subscription'))
    
    return render_template('admin/settings/subscription/edit.html', plan=plan)

@settings_bp.route('/subscription/view/<int:plan_id>')
@admin_required
def view_subscription(plan_id):
    """View subscription plan details"""
    plan = Subscription.query.get_or_404(plan_id)
    subscribers = User.query.filter_by(subscription_id=plan.id).all()
    
    return render_template('admin/settings/subscription/view.html', 
                          plan=plan, 
                          subscribers=subscribers,
                          now=datetime.utcnow())

@settings_bp.route('/subscription/delete/<int:plan_id>', methods=['POST'])
@admin_required
def delete_subscription(plan_id):
    """Delete a subscription plan"""
    plan = Subscription.query.get_or_404(plan_id)
    
    # Check if plan is being used by any users
    subscribers = User.query.filter_by(subscription_id=plan.id).all()
    if subscribers:
        flash('Cannot delete plan because it has active subscribers.', 'danger')
        return redirect(url_for('settings.subscription'))
    
    db.session.delete(plan)
    db.session.commit()
    
    flash('Subscription plan deleted successfully!', 'success')
    return redirect(url_for('settings.subscription'))

@settings_bp.route('/api')
@admin_required
def api_settings():
    """Manage API settings"""
    # Get all settings
    settings = {
        'api_rate_limit': get_setting('api_rate_limit', '100'),
        'api_enable_rate_limit': get_setting('api_enable_rate_limit', '1') == '1'
    }
    
    return render_template('admin/settings/api.html', settings=settings)

@settings_bp.route('/api', methods=['POST'])
@admin_required
def update_api_settings():
    """Update API settings"""
    api_rate_limit = request.form.get('api_rate_limit')
    api_enable_rate_limit = 'api_enable_rate_limit' in request.form
    
    # Save settings
    update_setting('api_rate_limit', api_rate_limit)
    update_setting('api_enable_rate_limit', '1' if api_enable_rate_limit else '0')
    
    flash('API settings updated successfully!', 'success')
    return redirect(url_for('settings.api_settings'))

@settings_bp.route('/backup')
@admin_required
def backup():
    """Backup and restore database"""
    return render_template('admin/settings/backup.html')

@settings_bp.route('/backup/create', methods=['POST'])
@admin_required
def create_backup():
    """Create a database backup"""
    try:
        # Create backup directory if it doesn't exist
        backup_dir = os.path.join(current_app.root_path, 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        # Generate backup filename with timestamp
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        filename = f'backup_{timestamp}.json'
        backup_path = os.path.join(backup_dir, filename)
        
        # Create backup data
        backup_data = {}
        
        # Backup site settings
        settings = SiteSetting.query.all()
        backup_data['site_settings'] = [{'key': s.key, 'value': s.value, 'description': s.description} for s in settings]
        
        # Backup subscriptions
        subscriptions = Subscription.query.all()
        backup_data['subscriptions'] = [{
            'id': s.id,
            'name': s.name,
            'price': s.price,
            'duration_days': s.duration_days,
            'scrape_limit': s.scrape_limit,
            'description': s.description,
            'is_active': s.is_active
        } for s in subscriptions]
        
        # Save backup file
        with open(backup_path, 'w') as f:
            json.dump(backup_data, f, indent=4)
        
        flash(f'Backup created successfully: {filename}', 'success')
    except Exception as e:
        flash(f'Error creating backup: {str(e)}', 'danger')
    
    return redirect(url_for('settings.backup'))

@settings_bp.route('/backup/restore', methods=['POST'])
@admin_required
def restore_backup():
    """Restore a database backup"""
    if 'backup_file' not in request.files:
        flash('No backup file selected.', 'danger')
        return redirect(url_for('settings.backup'))
    
    backup_file = request.files['backup_file']
    if not backup_file.filename:
        flash('No backup file selected.', 'danger')
        return redirect(url_for('settings.backup'))
    
    try:
        # Load backup data
        backup_data = json.load(backup_file)
        
        # Restore site settings
        if 'site_settings' in backup_data:
            for setting in backup_data['site_settings']:
                # Update or create setting
                site_setting = SiteSetting.query.filter_by(key=setting['key']).first()
                if site_setting:
                    site_setting.value = setting['value']
                    site_setting.description = setting['description']
                else:
                    new_setting = SiteSetting(
                        key=setting['key'],
                        value=setting['value'],
                        description=setting['description']
                    )
                    db.session.add(new_setting)
        
        # Restore subscriptions
        if 'subscriptions' in backup_data:
            # First, get all current subscription IDs
            current_ids = [s.id for s in Subscription.query.all()]
            restored_ids = []
            
            for sub_data in backup_data['subscriptions']:
                sub_id = sub_data.get('id')
                
                # Try to find existing subscription
                subscription = None
                if sub_id:
                    subscription = Subscription.query.get(sub_id)
                
                if subscription:
                    # Update existing subscription
                    subscription.name = sub_data['name']
                    subscription.price = sub_data['price']
                    subscription.duration_days = sub_data['duration_days']
                    subscription.scrape_limit = sub_data['scrape_limit']
                    subscription.description = sub_data['description']
                    subscription.is_active = sub_data['is_active']
                    restored_ids.append(sub_id)
                else:
                    # Create new subscription
                    new_sub = Subscription(
                        name=sub_data['name'],
                        price=sub_data['price'],
                        duration_days=sub_data['duration_days'],
                        scrape_limit=sub_data['scrape_limit'],
                        description=sub_data['description'],
                        is_active=sub_data['is_active']
                    )
                    db.session.add(new_sub)
        
        db.session.commit()
        flash('Backup restored successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error restoring backup: {str(e)}', 'danger')
    
    return redirect(url_for('settings.backup'))

# Helper functions
def get_setting(key, default=None):
    """Get a setting from the database or return default"""
    setting = SiteSetting.query.filter_by(key=key).first()
    return setting.value if setting else default

def update_setting(key, value, description=None):
    """Update or create a setting"""
    setting = SiteSetting.query.filter_by(key=key).first()
    
    if setting:
        setting.value = value
        if description:
            setting.description = description
    else:
        setting = SiteSetting(
            key=key,
            value=value,
            description=description or f'Setting for {key}'
        )
        db.session.add(setting)
    
    db.session.commit()
    return setting 