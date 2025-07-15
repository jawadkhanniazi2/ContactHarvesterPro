from flask import Blueprint, render_template, flash, redirect, url_for, request, jsonify, send_file, current_app as app
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from user.models import UserSubscription, SubscriptionPlan, Payment, Job, Email
from werkzeug.security import generate_password_hash
import csv
import io
import tempfile
import xlsxwriter
from werkzeug.utils import secure_filename
import os
from models import db, User, ScrapeJob, ScrapeJobHistory, Subscription
import uuid
import threading
import time
import re

user_bp = Blueprint('user', __name__, url_prefix='/user')

@user_bp.route('/subscription')
@login_required
def subscription():
    """Subscription management page"""
    # Get all available plans
    plans = SubscriptionPlan.query.filter_by(is_active=True).all()
    
    # Get user's current subscription
    current_subscription = current_user.subscription
    
    # Calculate usage
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    jobs_used = ScrapeJobHistory.query.filter_by(
        user_id=current_user.id
    ).filter(ScrapeJobHistory.created_at >= month_start).count()
    
    usage = {
        'jobs_used': jobs_used,
        'subscription_limit': current_subscription.scrape_limit if current_subscription else 10,
        'remaining': max(0, (current_subscription.scrape_limit if current_subscription else 10) - jobs_used)
    }
    
    return render_template('user/subscription.html',
                          plans=plans,
                          current_subscription=current_subscription,
                          usage=usage)

@user_bp.route('/billing')
@login_required
def billing():
    """Billing history and payment management"""
    # Get payment history
    payments = Payment.query.filter_by(
        user_id=current_user.id
    ).order_by(Payment.created_at.desc()).all()
    
    return render_template('user/billing.html', payments=payments)

@user_bp.route('/dashboard')
@login_required
def dashboard():
    """Enhanced user dashboard showing credits, usage, and recent activity"""
    try:
        # Calculate monthly usage
        month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Get recent scraping jobs
        recent_jobs = ScrapeJobHistory.query.filter_by(
            user_id=current_user.id
        ).order_by(ScrapeJobHistory.created_at.desc()).limit(5).all()
        
        # Calculate usage statistics
        jobs_this_month = ScrapeJobHistory.query.filter_by(
            user_id=current_user.id
        ).filter(ScrapeJobHistory.created_at >= month_start).count()
        
        total_jobs = ScrapeJobHistory.query.filter_by(user_id=current_user.id).count()
        
        # Get subscription info
        subscription_limit = 10  # Default free limit
        subscription_name = 'Free'
        
        if current_user.subscription:
            subscription_limit = current_user.subscription.scrape_limit
            subscription_name = current_user.subscription.name
        
        remaining_credits = max(0, subscription_limit - jobs_this_month)
        
        # Calculate usage percentage
        usage_percentage = min(100, (jobs_this_month / subscription_limit) * 100) if subscription_limit > 0 else 0
        
        # Get account info
        account_stats = {
            'member_since': current_user.created_at,
            'last_login': current_user.last_login,
            'total_jobs': total_jobs,
            'jobs_this_month': jobs_this_month,
            'subscription_limit': subscription_limit,
            'remaining_credits': remaining_credits,
            'subscription_name': subscription_name,
            'usage_percentage': usage_percentage
        }
        
        return render_template('user/dashboard.html', 
                              recent_jobs=recent_jobs,
                              account_stats=account_stats)
    except Exception as e:
        app.logger.error(f"Error in user dashboard: {str(e)}")
        flash('Error loading dashboard. Please try again.', 'danger')
        return redirect(url_for('auth.login'))

@user_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """Enhanced user profile management"""
    if request.method == 'POST':
        try:
            # Update user profile
            current_user.first_name = request.form.get('first_name', '')
            current_user.last_name = request.form.get('last_name', '')
            
            # Handle password change if provided
            current_password = request.form.get('current_password')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')
            
            if new_password:
                if not current_password:
                    flash('Current password is required to change password.', 'danger')
                    return redirect(url_for('user.profile'))
                
                if not current_user.check_password(current_password):
                    flash('Current password is incorrect.', 'danger')
                    return redirect(url_for('user.profile'))
                
                if new_password != confirm_password:
                    flash('New passwords do not match.', 'danger')
                    return redirect(url_for('user.profile'))
                
                if len(new_password) < 6:
                    flash('Password must be at least 6 characters long.', 'danger')
                    return redirect(url_for('user.profile'))
                
                current_user.set_password(new_password)
                flash('Password updated successfully.', 'success')
            
            db.session.commit()
            flash('Profile updated successfully.', 'success')
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error updating profile: {str(e)}")
            flash('Error updating profile. Please try again.', 'danger')
        
        return redirect(url_for('user.profile'))
    
    return render_template('user/profile.html')

@user_bp.route('/jobs')
@login_required
def jobs():
    """List user's scraping jobs with enhanced filtering and search"""
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # Base query
    query = ScrapeJobHistory.query.filter_by(user_id=current_user.id)
    
    # Apply filters
    status_filter = request.args.get('status', '')
    if status_filter:
        query = query.filter(ScrapeJobHistory.status == status_filter)
    
    # Date range filter
    date_filter = request.args.get('date_range', '')
    if date_filter:
        if date_filter == 'today':
            today = datetime.utcnow().date()
            query = query.filter(ScrapeJobHistory.created_at >= today)
        elif date_filter == 'week':
            week_ago = datetime.utcnow() - timedelta(days=7)
            query = query.filter(ScrapeJobHistory.created_at >= week_ago)
        elif date_filter == 'month':
            month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            query = query.filter(ScrapeJobHistory.created_at >= month_start)
    
    # Pagination
    pagination = query.order_by(ScrapeJobHistory.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    jobs = pagination.items
    
    # Statistics
    total_jobs = ScrapeJobHistory.query.filter_by(user_id=current_user.id).count()
    completed_jobs = ScrapeJobHistory.query.filter_by(user_id=current_user.id, status='completed').count()
    failed_jobs = ScrapeJobHistory.query.filter_by(user_id=current_user.id, status='failed').count()
    
    stats = {
        'total': total_jobs,
        'completed': completed_jobs,
        'failed': failed_jobs,
        'success_rate': round((completed_jobs / total_jobs * 100) if total_jobs > 0 else 0, 1)
    }
    
    return render_template('user/jobs.html', 
                          jobs=jobs,
                          pagination=pagination,
                          stats=stats,
                          status_filter=status_filter,
                          date_filter=date_filter)

@user_bp.route('/jobs/<job_id>')
@login_required
def view_job(job_id):
    """View details of a specific scraping job"""
    job = ScrapeJobHistory.query.filter_by(
        job_id=job_id, 
        user_id=current_user.id
    ).first_or_404()
    
    return render_template('user/job_detail.html', job=job)

@user_bp.route('/api/usage')
@login_required
def get_usage():
    """API endpoint to get current user usage"""
    try:
        month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        jobs_this_month = ScrapeJobHistory.query.filter_by(
            user_id=current_user.id
        ).filter(ScrapeJobHistory.created_at >= month_start).count()
        
        subscription_limit = current_user.subscription.scrape_limit if current_user.subscription else 10
        remaining = max(0, subscription_limit - jobs_this_month)
        
        return jsonify({
            'used': jobs_this_month,
            'limit': subscription_limit,
            'remaining': remaining,
            'percentage': min(100, (jobs_this_month / subscription_limit) * 100) if subscription_limit > 0 else 0
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@user_bp.route('/billing/history')
@login_required
def billing_history():
    """User billing history page."""
    # Fetch billing history from database
    transactions = Payment.query.filter_by(user_id=current_user.id).order_by(Payment.created_at.desc()).all()
    
    return render_template(
        'user/subscription/billing_history.html',
        transactions=transactions
    )

@user_bp.route('/download/invoice/<invoice_id>')
@login_required
def download_invoice(invoice_id):
    """Download invoice PDF."""
    payment = Payment.query.filter_by(user_id=current_user.id, invoice_id=invoice_id).first_or_404()
    
    # In a real application, you would generate a PDF invoice here
    # For demo purposes, we'll just flash a message
    flash('In a real application, this would download your invoice PDF.', 'info')
    
    return redirect(url_for('user.billing_history'))

@user_bp.route('/download/receipt/<invoice_id>')
@login_required
def download_receipt(invoice_id):
    """Download receipt PDF."""
    payment = Payment.query.filter_by(user_id=current_user.id, invoice_id=invoice_id, status='successful').first_or_404()
    
    # In a real application, you would generate a PDF receipt here
    # For demo purposes, we'll just flash a message
    flash('In a real application, this would download your receipt PDF.', 'info')
    
    return redirect(url_for('user.billing_history'))

@user_bp.route('/emails')
@login_required
def emails():
    """List all emails found across all jobs"""
    # Get all emails for this user
    emails = Email.query.filter_by(user_id=current_user.id).order_by(Email.created_at.desc()).all()
    
    # Count statistics
    total_emails = len(emails)
    valid_emails = sum(1 for email in emails if email.is_valid is True)
    unique_domains = len(set(email.domain for email in emails if email.domain))
    
    return render_template('user/emails/index.html', 
                          emails=emails,
                          total_emails=total_emails,
                          valid_emails=valid_emails,
                          unique_domains=unique_domains)

@user_bp.route('/emails/export')
@login_required
def export_all_emails():
    """Export all emails from all jobs"""
    # Get all emails for this user
    emails = Email.query.filter_by(user_id=current_user.id).all()
    
    if not emails:
        flash('No emails found to export.', 'warning')
        return redirect(url_for('user.emails'))
    
    # Determine format (default to CSV)
    format = request.args.get('format', 'csv')
    
    if format == 'csv':
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['Email Address', 'Valid', 'Domain', 'Source URL', 'Job Name', 'First Name', 'Last Name', 'Position', 'Company', 'Date Found'])
        
        # Write data
        for email in emails:
            job = Job.query.get(email.job_id)
            job_name = job.name if job else 'Unknown'
            valid_status = 'Yes' if email.is_valid is True else 'No' if email.is_valid is False else 'Unknown'
            
            writer.writerow([
                email.address,
                valid_status,
                email.domain,
                email.source_url,
                job_name,
                email.first_name or '',
                email.last_name or '',
                email.position or '',
                email.company or '',
                email.created_at.strftime('%Y-%m-%d %H:%M:%S')
            ])
        
        # Prepare response
        output.seek(0)
        filename = f"all_emails_{datetime.utcnow().strftime('%Y%m%d')}.csv"
        
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            as_attachment=True,
            download_name=filename,
            mimetype='text/csv'
        )
        
    elif format == 'xlsx':
        try:
            import pandas as pd
            from io import BytesIO
            
            # Convert to pandas DataFrame
            email_data = []
            for email in emails:
                job = Job.query.get(email.job_id)
                job_name = job.name if job else 'Unknown'
                valid_status = 'Yes' if email.is_valid is True else 'No' if email.is_valid is False else 'Unknown'
                
                email_data.append({
                    'Email Address': email.address,
                    'Valid': valid_status,
                    'Domain': email.domain,
                    'Source URL': email.source_url,
                    'Job Name': job_name,
                    'First Name': email.first_name,
                    'Last Name': email.last_name,
                    'Position': email.position,
                    'Company': email.company,
                    'Date Found': email.created_at.strftime('%Y-%m-%d %H:%M:%S')
                })
            
            df = pd.DataFrame(email_data)
            
            # Create Excel file in memory
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, sheet_name='All Emails', index=False)
                
                # Auto-adjust columns width
                worksheet = writer.sheets['All Emails']
                for i, col in enumerate(df.columns):
                    column_width = max(df[col].astype(str).map(len).max(), len(col))
                    worksheet.set_column(i, i, column_width + 2)
            
            # Prepare response
            output.seek(0)
            filename = f"all_emails_{datetime.utcnow().strftime('%Y%m%d')}.xlsx"
            
            return send_file(
                output,
                as_attachment=True,
                download_name=filename,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
        except ImportError:
            flash('Excel export requires pandas and xlsxwriter. Defaulting to CSV.', 'warning')
            return redirect(url_for('user.export_all_emails', format='csv'))
    else:
        flash('Unsupported format. Please use CSV or XLSX.', 'danger')
        return redirect(url_for('user.emails')) 