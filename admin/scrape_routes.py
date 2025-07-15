from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app, send_file
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import os
import pandas as pd

from models import db, ScrapeJobHistory, ApiKey, User, Subscription
from auth import admin_required, login_required
from utils import generate_api_key

# Create blueprint
scrape_bp = Blueprint('scrape', __name__, url_prefix='/admin/scrape')

@scrape_bp.route('/jobs')
@login_required
def jobs():
    """List all scrape jobs"""
    # Admin sees all jobs, regular users see only their own
    if current_user.is_admin():
        jobs = ScrapeJobHistory.query.order_by(ScrapeJobHistory.created_at.desc()).all()
    else:
        jobs = ScrapeJobHistory.query.filter_by(user_id=current_user.id).order_by(ScrapeJobHistory.created_at.desc()).all()
    
    return render_template('admin/scrape/jobs.html', jobs=jobs)

@scrape_bp.route('/jobs/view/<string:job_id>')
@login_required
def view_job(job_id):
    """View details of a scrape job"""
    # Get job
    job = ScrapeJobHistory.query.filter_by(job_id=job_id).first_or_404()
    
    # Check if user has permission to view this job
    if not current_user.is_admin() and job.user_id != current_user.id:
        flash('You do not have permission to view this job.', 'danger')
        return redirect(url_for('scrape.jobs'))
    
    # Get job results
    results = []
    if job.result_file and os.path.exists(job.result_file):
        try:
            df = pd.read_excel(job.result_file)
            # Convert to list of dicts for template
            results = df.to_dict('records')
        except Exception as e:
            flash(f'Error reading results file: {str(e)}', 'danger')
    
    return render_template('admin/scrape/job_details.html', job=job, results=results)

@scrape_bp.route('/jobs/delete/<string:job_id>', methods=['POST'])
@login_required
def delete_job(job_id):
    """Delete a scrape job"""
    # Get job
    job = ScrapeJobHistory.query.filter_by(job_id=job_id).first_or_404()
    
    # Check if user has permission to delete this job
    if not current_user.is_admin() and job.user_id != current_user.id:
        flash('You do not have permission to delete this job.', 'danger')
        return redirect(url_for('scrape.jobs'))
    
    # Delete result file if exists
    if job.result_file and os.path.exists(job.result_file):
        try:
            os.remove(job.result_file)
        except Exception as e:
            current_app.logger.error(f'Error deleting result file: {str(e)}')
    
    # Delete job from database
    db.session.delete(job)
    db.session.commit()
    
    flash('Job deleted successfully!', 'success')
    return redirect(url_for('scrape.jobs'))

@scrape_bp.route('/jobs/download/<string:job_id>')
@login_required
def download_job(job_id):
    """Download job results"""
    # Get job
    job = ScrapeJobHistory.query.filter_by(job_id=job_id).first_or_404()
    
    # Check if user has permission to download this job
    if not current_user.is_admin() and job.user_id != current_user.id:
        flash('You do not have permission to download this job.', 'danger')
        return redirect(url_for('scrape.jobs'))
    
    # Check if result file exists
    if not job.result_file or not os.path.exists(job.result_file):
        flash('Result file not found.', 'danger')
        return redirect(url_for('scrape.view_job', job_id=job_id))
    
    # Send file for download
    return send_file(job.result_file, as_attachment=True, download_name=f'scrape_results_{job_id}.xlsx')

@scrape_bp.route('/api-keys')
@login_required
def api_keys():
    """Manage API keys"""
    # Admin sees all API keys, regular users see only their own
    if current_user.is_admin():
        api_keys = ApiKey.query.all()
        users = User.query.all()
    else:
        api_keys = ApiKey.query.filter_by(user_id=current_user.id).all()
        users = [current_user]
    
    return render_template('admin/scrape/api_keys.html', api_keys=api_keys, users=users, datetime=datetime)

@scrape_bp.route('/api-keys/create', methods=['GET', 'POST'])
@login_required
def create_api_key():
    """Create a new API key"""
    if request.method == 'POST':
        name = request.form.get('name')
        
        # Admin can create for any user, regular users only for themselves
        if current_user.is_admin():
            user_id = request.form.get('user_id', type=int)
            if not user_id:
                flash('Please select a user.', 'danger')
                return redirect(url_for('scrape.create_api_key'))
        else:
            user_id = current_user.id
        
        # Check if user exists
        user = User.query.get(user_id)
        if not user:
            flash('Selected user does not exist.', 'danger')
            return redirect(url_for('scrape.api_keys'))
        
        # Generate API key
        key = generate_api_key()
        
        # Set expiration date (1 year from now)
        expires_at = datetime.utcnow() + timedelta(days=365)
        
        # Create API key
        api_key = ApiKey(
            user_id=user_id,
            key=key,
            name=name,
            created_at=datetime.utcnow(),
            expires_at=expires_at,
            is_active=True
        )
        
        db.session.add(api_key)
        db.session.commit()
        
        flash(f'API key created successfully! Your key is: {key}', 'success')
        return redirect(url_for('scrape.api_keys'))
    
    # Get users for admin
    users = User.query.all() if current_user.is_admin() else None
    
    return render_template('admin/scrape/api_keys_create.html', users=users)

@scrape_bp.route('/api-keys/toggle/<int:key_id>', methods=['POST'])
@login_required
def toggle_api_key(key_id):
    """Toggle API key active status"""
    # Get API key
    api_key = ApiKey.query.get_or_404(key_id)
    
    # Check if user has permission to modify this key
    if not current_user.is_admin() and api_key.user_id != current_user.id:
        flash('You do not have permission to modify this API key.', 'danger')
        return redirect(url_for('scrape.api_keys'))
    
    # Toggle status
    api_key.is_active = not api_key.is_active
    db.session.commit()
    
    status = 'activated' if api_key.is_active else 'deactivated'
    flash(f'API key {status} successfully!', 'success')
    return redirect(url_for('scrape.api_keys'))

@scrape_bp.route('/api-keys/delete/<int:key_id>', methods=['POST'])
@login_required
def delete_api_key(key_id):
    """Delete an API key"""
    # Get API key
    api_key = ApiKey.query.get_or_404(key_id)
    
    # Check if user has permission to delete this key
    if not current_user.is_admin() and api_key.user_id != current_user.id:
        flash('You do not have permission to delete this API key.', 'danger')
        return redirect(url_for('scrape.api_keys'))
    
    db.session.delete(api_key)
    db.session.commit()
    
    flash('API key deleted successfully!', 'success')
    return redirect(url_for('scrape.api_keys'))

@scrape_bp.route('/limits')
@admin_required
def scrape_limits():
    """Manage scraping limits"""
    subscriptions = Subscription.query.all()
    return render_template('admin/scrape/limits.html', subscriptions=subscriptions)

@scrape_bp.route('/limits/update', methods=['POST'])
@admin_required
def update_scrape_limits():
    """Update scraping limits for a subscription plan"""
    subscription_id = request.form.get('subscription_id', type=int)
    scrape_limit = request.form.get('scrape_limit', type=int)
    
    if not subscription_id or scrape_limit is None:
        flash('Invalid data submitted.', 'danger')
        return redirect(url_for('scrape.scrape_limits'))
    
    # Get subscription
    subscription = Subscription.query.get_or_404(subscription_id)
    
    # Update limit
    subscription.scrape_limit = scrape_limit
    db.session.commit()
    
    flash(f'Scrape limit for {subscription.name} updated successfully!', 'success')
    return redirect(url_for('scrape.scrape_limits')) 