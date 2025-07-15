from flask import Flask, render_template, request, jsonify, send_file, url_for, redirect, flash, session
from flask_login import LoginManager, current_user, login_user, login_required, logout_user
from flask_migrate import Migrate
from werkzeug.utils import secure_filename
from scraper import ContactScraper
import os
import logging
import pandas as pd
import threading
import queue
import time
import json
from datetime import datetime, timezone
import requests
from bs4 import BeautifulSoup
import re
import urllib.parse

# Import models and created modules
from models import db, User, Role, UserRole, SiteSetting, Page, BlogPost, BlogCategory, ScrapeJobHistory
from auth import auth_bp, admin_required, editor_required
from utils import mail, send_email
from admin.routes import admin_bp
from admin.blog_routes import blog_bp
from admin.page_routes import page_bp
from admin.settings_routes import settings_bp
from admin.scrape_routes import scrape_bp
from user import user_bp

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get('SECRET_KEY', os.urandom(24)),
    UPLOAD_FOLDER='uploads',
    MAX_CONTENT_LENGTH=10 * 1024 * 1024,  # 10MB max upload
    MAX_URLS_PER_BATCH=100,  # Maximum number of URLs to process in one batch
    SQLALCHEMY_DATABASE_URI=os.environ.get('DATABASE_URL', 'sqlite:///contact_harvester.db'),
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    # Mail configuration - these will be overridden from the database
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USE_SSL=False,
    MAIL_USERNAME=os.environ.get('MAIL_USERNAME', ''),
    MAIL_PASSWORD=os.environ.get('MAIL_PASSWORD', ''),
    MAIL_DEFAULT_SENDER=os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@example.com'),
    # Google OAuth
    GOOGLE_CLIENT_ID=os.environ.get('GOOGLE_CLIENT_ID', ''),
    GOOGLE_CLIENT_SECRET=os.environ.get('GOOGLE_CLIENT_SECRET', '')
)

# Initialize extensions
db.init_app(app)
mail.init_app(app)
migrate = Migrate(app, db)

# Initialize login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(blog_bp)
app.register_blueprint(page_bp)
app.register_blueprint(settings_bp)
app.register_blueprint(scrape_bp)
app.register_blueprint(user_bp)

# Register custom template filters
@app.template_filter('format_price')
def format_price_filter(price, currency='$'):
    """Format price with currency symbol"""
    if price is None:
        return f"{currency}0.00"
    return f"{currency}{price:.2f}"

# Add built-in functions to Jinja2 environment
app.jinja_env.globals.update(min=min, max=max)

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('results', exist_ok=True)
os.makedirs(os.path.join('static', 'uploads', 'blog'), exist_ok=True)
os.makedirs(os.path.join('static', 'uploads', 'site'), exist_ok=True)
os.makedirs('backups', exist_ok=True)

# Global variables for tracking progress
active_jobs = {}

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Load settings from database when app starts
@app.before_first_request
def load_settings():
    # Create all tables
    db.create_all()
    
    with app.app_context():
        # Create default roles if they don't exist
        roles = {
            UserRole.ADMIN.value: 'Administrator with full access',
            UserRole.EDITOR.value: 'Editor with content management access',
            UserRole.USER.value: 'Regular user with limited access'
        }
        
        for role_name, description in roles.items():
            if not Role.query.filter_by(name=role_name).first():
                role = Role(name=role_name, description=description)
                db.session.add(role)
        
        # Create default admin user if no users exist
        if User.query.count() == 0:
            admin_role = Role.query.filter_by(name=UserRole.ADMIN.value).first()
            
            if admin_role:
                admin = User(
                    username='admin',
                    email='admin@example.com',
                    first_name='Admin',
                    last_name='User',
                    is_active=True,
                    created_at=datetime.now(timezone.utc)
                )
                admin.set_password('admin123')  # Set a default password
                admin.roles.append(admin_role)
                db.session.add(admin)
        
        # Create default pages if they don't exist
        default_pages = [
            {
                'title': 'About Us',
                'slug': 'about',
                'content': '''
                <h1>About Our Email Scraping Service</h1>
                <p>We provide professional email scraping services to help businesses find contact information from websites efficiently and ethically.</p>
                <h2>Our Mission</h2>
                <p>To provide reliable, fast, and accurate email extraction tools that help businesses grow their contact databases while respecting privacy and data protection regulations.</p>
                <h2>Features</h2>
                <ul>
                    <li>Fast and accurate email extraction</li>
                    <li>Support for multiple file formats</li>
                    <li>Bulk URL processing</li>
                    <li>Export to Excel and CSV</li>
                    <li>API access for developers</li>
                </ul>
                ''',
                'meta_title': 'About Us - Email Scraping Service',
                'meta_description': 'Learn about our professional email scraping service and how we help businesses find contact information efficiently.'
            },
            {
                'title': 'Contact Us',
                'slug': 'contact',
                'content': '''
                <h1>Contact Us</h1>
                <p>Get in touch with our team for support, questions, or business inquiries.</p>
                <div class="row">
                    <div class="col-md-6">
                        <h3>Support</h3>
                        <p>Email: support@emailscraper.com</p>
                        <p>Response time: Within 24 hours</p>
                    </div>
                    <div class="col-md-6">
                        <h3>Business Inquiries</h3>
                        <p>Email: business@emailscraper.com</p>
                        <p>Phone: +1 (555) 123-4567</p>
                    </div>
                </div>
                <h3>Office Hours</h3>
                <p>Monday - Friday: 9:00 AM - 6:00 PM EST</p>
                <p>Saturday - Sunday: Closed</p>
                ''',
                'meta_title': 'Contact Us - Email Scraping Service',
                'meta_description': 'Contact our support team for help with email scraping services, technical support, or business inquiries.'
            },
            {
                'title': 'Pricing',
                'slug': 'pricing',
                'content': '''
                <h1>Pricing Plans</h1>
                <p>Choose the plan that best fits your email scraping needs.</p>
                <div class="row">
                    <div class="col-md-4">
                        <div class="card">
                            <div class="card-header">
                                <h3>Free</h3>
                            </div>
                            <div class="card-body">
                                <h2>$0/month</h2>
                                <ul>
                                    <li>10 URLs per month</li>
                                    <li>Basic email extraction</li>
                                    <li>CSV export</li>
                                    <li>Community support</li>
                                </ul>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="card">
                            <div class="card-header">
                                <h3>Pro</h3>
                            </div>
                            <div class="card-body">
                                <h2>$29/month</h2>
                                <ul>
                                    <li>1,000 URLs per month</li>
                                    <li>Advanced email extraction</li>
                                    <li>Excel & CSV export</li>
                                    <li>Priority support</li>
                                    <li>API access</li>
                                </ul>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="card">
                            <div class="card-header">
                                <h3>Enterprise</h3>
                            </div>
                            <div class="card-body">
                                <h2>$99/month</h2>
                                <ul>
                                    <li>Unlimited URLs</li>
                                    <li>Premium extraction</li>
                                    <li>All export formats</li>
                                    <li>24/7 support</li>
                                    <li>Full API access</li>
                                    <li>Custom integrations</li>
                                </ul>
                            </div>
                        </div>
                    </div>
                </div>
                ''',
                'meta_title': 'Pricing Plans - Email Scraping Service',
                'meta_description': 'View our affordable pricing plans for email scraping services. Choose from Free, Pro, or Enterprise plans.'
            }
        ]
        
        for page_data in default_pages:
            if not Page.query.filter_by(slug=page_data['slug']).first():
                page = Page(
                    title=page_data['title'],
                    slug=page_data['slug'],
                    content=page_data['content'],
                    meta_title=page_data['meta_title'],
                    meta_description=page_data['meta_description'],
                    published=True,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                db.session.add(page)
        
        # Load mail settings from database
        mail_settings = {
            'MAIL_SERVER': get_setting('mail_server', app.config['MAIL_SERVER']),
            'MAIL_PORT': int(get_setting('mail_port', app.config['MAIL_PORT'])),
            'MAIL_USE_TLS': get_setting('mail_use_tls', '1') == '1',
            'MAIL_USE_SSL': get_setting('mail_use_ssl', '0') == '1',
            'MAIL_USERNAME': get_setting('mail_username', app.config['MAIL_USERNAME']),
            'MAIL_PASSWORD': get_setting('mail_password', app.config['MAIL_PASSWORD']),
            'MAIL_DEFAULT_SENDER': get_setting('mail_default_sender', app.config['MAIL_DEFAULT_SENDER'])
        }
        
        # Update mail config
        app.config.update(mail_settings)
        
        # Commit changes
        db.session.commit()

# Utility function to get settings
def get_setting(key, default=None):
    """Get a setting from the database or return default"""
    setting = SiteSetting.query.filter_by(key=key).first()
    return setting.value if setting else default

# Insert your existing ScrapeJob class here
class ScrapeJob:
    """Class to track progress of a scraping job"""
    def __init__(self, job_id, total_urls=0):
        self.job_id = job_id
        self.total_urls = total_urls
        self.completed_urls = 0
        self.status = "initializing"  # initializing, running, completed, error
        self.start_time = time.time()
        self.end_time = None
        self.result_file = None
        self.error = None
        self.results = []  # Store raw results for direct access
    
    def update_progress(self, completed, total):
        """Update job progress"""
        self.completed_urls = completed
        self.total_urls = total
        
    def add_result(self, result):
        """Add a result to the job's results list"""
        if result:
            self.results.append(result)
            logger.info(f"Added result to job {self.job_id}, now have {len(self.results)} results")
            
            # DEBUG: Log first result added for single URL jobs
            if self.total_urls == 1 and len(self.results) == 1:
                logger.info(f"CRITICAL DEBUG - First result for single URL job: {result}")
                
                # Special validation for results that will be sent to the frontend
                if 'emails' in result and not isinstance(result['emails'], list):
                    logger.warning(f"Converting emails to list for first result: {result['emails']}")
                    result['emails'] = [result['emails']] if result['emails'] else []
                
                if 'phones' in result and not isinstance(result['phones'], list):
                    logger.warning(f"Converting phones to list for first result: {result['phones']}")
                    result['phones'] = [result['phones']] if result['phones'] else []
        
    def complete(self, result_file):
        """Mark job as completed"""
        self.status = "completed"
        self.end_time = time.time()
        self.result_file = result_file
        logger.info(f"Job {self.job_id} completed with {len(self.results)} results")
        
    def fail(self, error):
        """Mark job as failed"""
        self.status = "error"
        self.end_time = time.time()
        self.error = str(error)
    
    def to_dict(self):
        """Convert to dictionary for JSON response"""
        elapsed = self.end_time - self.start_time if self.end_time else time.time() - self.start_time
        progress = (self.completed_urls / self.total_urls) * 100 if self.total_urls > 0 else 0
        
        result_dict = {
            "job_id": self.job_id,
            "status": self.status,
            "total_urls": self.total_urls,
            "completed_urls": self.completed_urls,
            "progress": round(progress, 1),
            "elapsed_time": round(elapsed, 1),
            "result_file": self.result_file,
            "error": self.error
        }
        
        # Add preview of results if available
        if self.results and len(self.results) > 0:
            # Only return first 5 for preview
            result_dict["result_preview"] = self.results[:5]
            result_dict["total_results"] = len(self.results)
            
            # Critical fix: For single-URL jobs, include ALL results and first result separately
            if self.total_urls == 1:
                # Make a deep copy for first result to avoid reference issues
                first_result = dict(self.results[0])
                
                # Ensure emails and phones are lists
                if 'emails' in first_result and not isinstance(first_result['emails'], list):
                    first_result['emails'] = [first_result['emails']] if first_result['emails'] else []
                
                if 'phones' in first_result and not isinstance(first_result['phones'], list):
                    first_result['phones'] = [first_result['phones']] if first_result['phones'] else []
                
                # Log the structure format
                logger.info(f"IMPORTANT DEBUG - Single URL first_result format: {first_result}")
                
                # Add all fields for redundancy
                result_dict["single_result"] = first_result
                result_dict["direct_results"] = [first_result]  # Wrap in list to ensure it's an array
                result_dict["first_domain_result"] = first_result
                
                logger.info(f"Set all single URL result fields for job {self.job_id}")
        
        return result_dict


def process_url_file(file_path):
    """Extract URLs from uploaded file"""
    try:
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
            # Assume the first column contains URLs
            urls = df.iloc[:, 0].tolist()
        elif file_path.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(file_path)
            # Assume the first column contains URLs
            urls = df.iloc[:, 0].tolist()
        elif file_path.endswith('.txt'):
            with open(file_path, 'r') as f:
                urls = [line.strip() for line in f if line.strip()]
        else:
            raise ValueError("Unsupported file format")
        
        # Filter out invalid URLs
        valid_urls = [url for url in urls if isinstance(url, str) and url.strip()]
        
        return valid_urls
    except Exception as e:
        logger.error(f"Error processing URL file: {str(e)}")
        raise


# Simple scraper fallback functions in case Selenium fails
def simple_extract_emails(text):
    """Extract emails without using Selenium"""
    # Standard email pattern
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = re.findall(email_pattern, text)
    
    # Set for faster duplicate checking
    filtered_emails = set()
    
    for email in emails:
        if not any(invalid in email.lower() for invalid in ['@example.', '@domain.', '@email.']):
            filtered_emails.add(email.lower())
    
    # Additional patterns for protected emails
    
    # Pattern for emails with "at" and "dot" text encoding
    encoded_pattern = r'([a-zA-Z0-9._%+-]+)[\s]*(?:\[at\]|@|[\(\[\{]at[\)\]\}]|&#64;|%40)[\s]*([a-zA-Z0-9.-]+)[\s]*(?:\[dot\]|\.|\(dot\)|\[dot\]|&#46;|%2E)[\s]*([a-zA-Z]{2,})'
    encoded_matches = re.finditer(encoded_pattern, text, re.IGNORECASE)
    for match in encoded_matches:
        if match.group(1) and match.group(2) and match.group(3):
            email = f"{match.group(1).strip()}@{match.group(2).strip()}.{match.group(3).strip()}"
            filtered_emails.add(email.lower())
    
    # Pattern for JavaScript obfuscated emails
    js_pattern = r'document\.write\([\'"]([a-zA-Z0-9._%+-]+)[\'"][\s]*\+[\s]*[\'"]@[\'"][\s]*\+[\s]*[\'"]([a-zA-Z0-9.-]+)[\s]*[\'"][\s]*\+[\s]*[\'"]\.[\'"][\s]*\+[\s]*[\'"]([a-zA-Z]{2,})[\'"]'
    js_matches = re.finditer(js_pattern, text)
    for match in js_matches:
        if match.group(1) and match.group(2) and match.group(3):
            email = f"{match.group(1)}@{match.group(2)}.{match.group(3)}"
            filtered_emails.add(email.lower())
    
    # Pattern for HTML entity encoded emails
    html_entity_pattern = r'([a-zA-Z0-9._%+-]+)(?:&#64;|&#0*64;|%40)([a-zA-Z0-9.-]+)(?:&#46;|&#0*46;|%2E)([a-zA-Z]{2,})'
    entity_matches = re.finditer(html_entity_pattern, text)
    for match in entity_matches:
        if match.group(1) and match.group(2) and match.group(3):
            email = f"{match.group(1)}@{match.group(2)}.{match.group(3)}"
            filtered_emails.add(email.lower())
    
    # Pattern for separated email parts with CSS display tricks
    css_pattern = r'<span[^>]*data-user=["\']([^"\']+)["\'][^>]*>.*?</span>.*?<span[^>]*data-domain=["\']([^"\']+)["\'][^>]*>.*?</span>'
    css_matches = re.finditer(css_pattern, text)
    for match in css_matches:
        if match.group(1) and match.group(2):
            email = f"{match.group(1)}@{match.group(2)}"
            filtered_emails.add(email.lower())
    
    # Pattern for unicode obfuscation
    unicode_pattern = r'([a-zA-Z0-9._%+-]+)(?:\\u0*40|\\x40)([a-zA-Z0-9.-]+)(?:\\u0*2e|\\x2e)([a-zA-Z]{2,})'
    unicode_matches = re.finditer(unicode_pattern, text)
    for match in unicode_matches:
        if match.group(1) and match.group(2) and match.group(3):
            email = f"{match.group(1)}@{match.group(2)}.{match.group(3)}"
            filtered_emails.add(email.lower())
    
    return list(filtered_emails)

def simple_extract_phones(text):
    """Extract phone numbers without using Selenium"""
    phone_pattern = r'(?:\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
    phones = re.findall(phone_pattern, text)
    return list(set(phones))

def simple_extract_social(text):
    """Extract social media links without using Selenium"""
    social_patterns = {
        'linkedin': r'(?:https?:\/\/)?(?:www\.)?linkedin\.com\/(?:in|company)\/[a-zA-Z0-9_-]+\/?',
        'twitter': r'(?:https?:\/\/)?(?:www\.)?(?:twitter\.com|x\.com)\/[a-zA-Z0-9_-]+\/?',
        'facebook': r'(?:https?:\/\/)?(?:www\.)?facebook\.com\/(?:profile\.php\?id=\d+|[a-zA-Z0-9._-]+)\/?',
    }
    
    social = {}
    for platform, pattern in social_patterns.items():
        matches = re.findall(pattern, text)
        if matches:
            social[platform] = matches[0]
    return social

def decode_cloudflare_email(encoded_email):
    """Decode a Cloudflare protected email"""
    try:
        # Cloudflare encoding uses a simple XOR cipher
        decoded = ""
        
        # Convert hex to bytes
        hex_encoded = bytes.fromhex(encoded_email)
        
        # First byte is the key
        key = hex_encoded[0]
        
        # Decode each byte with XOR
        for i in range(1, len(hex_encoded)):
            decoded += chr(hex_encoded[i] ^ key)
        
        return decoded
    except Exception as e:
        logger.warning(f"Failed to decode Cloudflare email: {str(e)}")
        return None

def find_cloudflare_emails(html):
    """Find Cloudflare protected emails in HTML content"""
    # Look for Cloudflare protected email patterns
    cf_pattern = r'<a[^>]*href="/cdn-cgi/l/email-protection#([a-zA-Z0-9]+)"[^>]*>.*?</a>'
    cf_data_pattern = r'<a[^>]*data-cfemail="([a-zA-Z0-9]+)"[^>]*>.*?</a>'
    
    emails = []
    
    # Find emails with href pattern
    for match in re.finditer(cf_pattern, html, re.IGNORECASE):
        encoded = match.group(1)
        decoded = decode_cloudflare_email(encoded)
        if decoded and '@' in decoded:
            emails.append(decoded.lower())
    
    # Find emails with data-cfemail pattern
    for match in re.finditer(cf_data_pattern, html, re.IGNORECASE):
        encoded = match.group(1)
        decoded = decode_cloudflare_email(encoded)
        if decoded and '@' in decoded:
            emails.append(decoded.lower())
    
    return list(set(emails))

def find_mailto_links(soup):
    """Extract email addresses from mailto links"""
    emails = []
    
    # Find all mailto links
    for link in soup.find_all('a', href=True):
        href = link.get('href', '')
        if href.startswith('mailto:'):
            # Extract email from mailto: link
            email = href.replace('mailto:', '').strip()
            # Remove any query parameters
            email = email.split('?')[0].strip()
            if '@' in email and '.' in email:
                emails.append(email.lower())
    
    return list(set(emails))

def find_image_emails(soup):
    """Find email addresses in image alt tags"""
    emails = []
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    
    # Find all images
    for img in soup.find_all('img', alt=True):
        alt_text = img.get('alt', '')
        # Check for email patterns in alt text
        matches = re.findall(email_pattern, alt_text)
        for email in matches:
            if '@' in email and '.' in email:
                emails.append(email.lower())
    
    # Also check title attributes which sometimes contain emails
    for elem in soup.find_all(title=True):
        title_text = elem.get('title', '')
        matches = re.findall(email_pattern, title_text)
        for email in matches:
            if '@' in email and '.' in email:
                emails.append(email.lower())
    
    return list(set(emails))

def simple_scrape_url(url):
    """Simple fallback scraper using requests instead of Selenium"""
    try:
        logger.info(f"Using simple scraper for URL: {url}")
        
        # Normalize URL
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            
        # Get domain
        domain = urllib.parse.urlparse(url).netloc
        
        # Make request with timeout
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Parse content
        content = response.text
        soup = BeautifulSoup(content, 'html.parser')
        text = soup.get_text()
        
        # Extract information
        emails = simple_extract_emails(text)
        phones = simple_extract_phones(text)
        social = simple_extract_social(content)
        
        # Check for Cloudflare protected emails
        cloudflare_emails = find_cloudflare_emails(content)
        if cloudflare_emails:
            logger.info(f"Found {len(cloudflare_emails)} Cloudflare protected emails")
            emails.extend(cloudflare_emails)
            
        # Check for emails in image alt tags
        img_emails = find_image_emails(soup)
        if img_emails:
            logger.info(f"Found {len(img_emails)} emails in image alt tags")
            emails.extend(img_emails)
            
        # Check for mailto links
        mailto_emails = find_mailto_links(soup)
        if mailto_emails:
            logger.info(f"Found {len(mailto_emails)} emails in mailto links")
            emails.extend(mailto_emails)
            
        # Try to find and visit contact page
        for link in soup.find_all('a', href=True):
            href = link.get('href')
            if href and any(keyword in href.lower() or keyword in link.get_text().lower() 
                           for keyword in ['contact', 'about']):
                try:
                    # Handle relative URLs
                    if not href.startswith(('http://', 'https://')):
                        contact_url = urllib.parse.urljoin(url, href)
                    else:
                        contact_url = href
                        
                    # Visit contact page
                    logger.info(f"Visiting contact page: {contact_url}")
                    contact_response = requests.get(contact_url, headers=headers, timeout=15)
                    if contact_response.ok:
                        contact_content = contact_response.text
                        contact_soup = BeautifulSoup(contact_content, 'html.parser')
                        contact_text = contact_soup.get_text()
                        
                        # Extract additional information
                        emails.extend(simple_extract_emails(contact_text))
                        phones.extend(simple_extract_phones(contact_text))
                        social.update(simple_extract_social(contact_content))
                        
                        # Remove duplicates
                        emails = list(set(emails))
                        phones = list(set(phones))
                except Exception as e:
                    logger.warning(f"Error visiting contact page {href}: {str(e)}")
                    continue
                    
                # Only check one contact page to avoid too many requests
                break
            
        logger.info(f"Simple scraper found: {len(emails)} emails, {len(phones)} phones")
        return {
            'url': url,
            'domain': domain,
            'emails': emails,
            'phones': phones,
            'social_media': social,
            'status': 'success (simple scraper)'
        }
    except Exception as e:
        logger.error(f"Simple scraper error for {url}: {str(e)}")
        return {
            'url': url,
            'domain': urllib.parse.urlparse(url).netloc if url.startswith(('http://', 'https://')) else '',
            'emails': [],
            'phones': [],
            'social_media': {},
            'status': f"Error (simple scraper): {str(e)}"
        }

def run_scrape_job(job, urls, headless=True, user_id=None):
    """Run scraping job in a separate thread"""
    try:
        job.status = "running"
        
        # Create job history record if user is authenticated
        job_history = None
        if user_id:
            with app.app_context():
                job_history = ScrapeJobHistory(
                    job_id=job.job_id,
                    user_id=user_id,
                    total_urls=len(urls),
                    created_at=datetime.now(timezone.utc),
                    status='in_progress'
                )
                db.session.add(job_history)
                db.session.commit()
        
        # Use simple scraper by default for better performance
        logger.info("Using requests-based scraper for better performance")
        
        # Process URLs with simple scraper
        results = []
        total = len(urls)
        
        # Log the number of URLs to process
        logger.info(f"Processing {total} URLs for job {job.job_id}")
        
        # Special attention for single URL jobs
        is_single_url = (total == 1)
        if is_single_url:
            logger.info("Special handling for single URL job")
        
        for i, url in enumerate(urls):
            logger.info(f"Processing URL {i+1}/{total}: {url}")
            result = simple_scrape_url(url)
            
            # CRITICAL FIX: Ensure fields are properly formatted for the first URL
            if i == 0:
                # Ensure emails and phones are lists
                if 'emails' in result and not isinstance(result['emails'], list):
                    logger.warning(f"Converting emails to list format: {result['emails']}")
                    result['emails'] = [result['emails']] if result['emails'] else []
                
                if 'phones' in result and not isinstance(result['phones'], list):
                    logger.warning(f"Converting phones to list format: {result['phones']}")
                    result['phones'] = [result['phones']] if result['phones'] else []
            
            results.append(result)
            
            # Use the add_result method to track the result
            job.add_result(result)
            
            # Log results for debugging, especially for first URL
            if i == 0:
                logger.info(f"Result for first URL: {result}")
                # Log important field types for debugging
                logger.info(f"First result field types - emails: {type(result.get('emails'))}, phones: {type(result.get('phones'))}")
                
            job.update_progress(i+1, total)
            
        # Generate timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_file = f"results/scrape_results_{timestamp}.xlsx"
        
        # Log the final results
        logger.info(f"Job {job.job_id} completed with {len(results)} results")
        if results:
            logger.info(f"First result: {results[0]}")
        
        # Export results
        df = pd.DataFrame(results)
        
        # Handle empty DataFrame
        if df.empty:
            logger.warning(f"No results found for job {job.job_id}")
            df = pd.DataFrame(columns=['url', 'domain', 'emails', 'phones', 'social_media', 'status'])
        else:
            logger.info(f"Created DataFrame with {len(df)} rows and columns: {list(df.columns)}")
            
            # For single URL jobs, ensure the row is properly formatted
            if is_single_url:
                logger.info(f"Single URL DataFrame row: {df.iloc[0].to_dict()}")
                
                # EXTRA VALIDATION: Make sure the first result is properly stored and accessible
                if len(job.results) > 0:
                    first_result = job.results[0]
                    logger.info("FINAL VALIDATION - First result that will be sent to frontend:")
                    logger.info(f"- complete object: {first_result}")
                    logger.info(f"- emails (type: {type(first_result.get('emails', []))}, value: {first_result.get('emails', [])})")
                    logger.info(f"- phones (type: {type(first_result.get('phones', []))}, value: {first_result.get('phones', [])})")
        
        # Convert social media dict to columns
        if 'social_media' in df.columns:
            social_df = pd.json_normalize(df['social_media'].fillna({}))
            df = df.drop('social_media', axis=1)
            
            # Combine with social media columns
            if not social_df.empty:
                final_df = pd.concat([df, social_df], axis=1)
            else:
                final_df = df
        else:
            final_df = df
        
        # Clean up lists in cells
        for col in final_df.columns:
            if final_df[col].dtype == 'object':
                final_df[col] = final_df[col].apply(
                    lambda x: ', '.join(map(str, x)) if isinstance(x, list) else x
                )
        
        # Log the final DataFrame before saving
        logger.info(f"Final DataFrame has {len(final_df)} rows")
        if not final_df.empty:
            logger.info(f"First row in final DataFrame: {final_df.iloc[0].to_dict() if len(final_df) > 0 else 'No rows'}")
        
        # Special save handling for single URL jobs
        if is_single_url and not final_df.empty:
            logger.info("Ensuring single URL result is properly saved")
            # Force write of a valid single-row DataFrame
            first_row = final_df.iloc[0].to_dict()
            logger.info(f"Single URL first row: {first_row}")
            
        final_df.to_excel(result_file, index=False)
        logger.info(f"Results exported to {result_file}")
        
        # Mark job as completed
        job.complete(result_file)
        
        # Update job history record if exists
        if job_history:
            with app.app_context():
                try:
                    # Refresh the job_history object to get the latest state
                    db.session.refresh(job_history)
                    
                    job_history.status = 'completed'
                    job_history.completed_at = datetime.now(timezone.utc)
                    job_history.result_file = result_file
                    job_history.successful_urls = len(results)
                    # Count total emails found across all results
                    total_emails = sum(len(result.get('emails', [])) for result in results if isinstance(result.get('emails', []), list))
                    job_history.emails_found = total_emails
                    
                    db.session.commit()
                    logger.info(f"Successfully updated job history for {job.job_id} to completed status")
                except Exception as e:
                    logger.error(f"Error updating job history for {job.job_id}: {str(e)}")
                    db.session.rollback()
                    # Try alternative approach - query and update directly
                    try:
                        db_job = ScrapeJobHistory.query.filter_by(job_id=job.job_id).first()
                        if db_job:
                            db_job.status = 'completed'
                            db_job.completed_at = datetime.now(timezone.utc)
                            db_job.result_file = result_file
                            db_job.successful_urls = len(results)
                            total_emails = sum(len(result.get('emails', [])) for result in results if isinstance(result.get('emails', []), list))
                            db_job.emails_found = total_emails
                            db.session.commit()
                            logger.info(f"Successfully updated job history for {job.job_id} using alternative method")
                    except Exception as e2:
                        logger.error(f"Alternative job history update also failed for {job.job_id}: {str(e2)}")
                        db.session.rollback()
        
    except Exception as e:
        logger.error(f"Error in scrape job {job.job_id}: {str(e)}")
        job.fail(str(e))
        
        # Update job history record if exists
        if job_history:
            with app.app_context():
                try:
                    # Refresh the job_history object to get the latest state
                    db.session.refresh(job_history)
                    
                    job_history.status = 'failed'
                    job_history.completed_at = datetime.now(timezone.utc)
                    db.session.commit()
                    logger.info(f"Successfully updated job history for {job.job_id} to failed status")
                except Exception as e2:
                    logger.error(f"Error updating failed job history for {job.job_id}: {str(e2)}")
                    db.session.rollback()
                    # Try alternative approach - query and update directly
                    try:
                        db_job = ScrapeJobHistory.query.filter_by(job_id=job.job_id).first()
                        if db_job:
                            db_job.status = 'failed'
                            db_job.completed_at = datetime.now(timezone.utc)
                            db.session.commit()
                            logger.info(f"Successfully updated failed job history for {job.job_id} using alternative method")
                    except Exception as e3:
                        logger.error(f"Alternative failed job history update also failed for {job.job_id}: {str(e3)}")
                        db.session.rollback()


@app.route('/')
def index():
    """Render the main landing page with scraping interface."""
    return render_template('index.html')


@app.route('/dashboard')
@login_required
def dashboard_redirect():
    """Redirect to the appropriate dashboard based on user role."""
    if current_user.is_admin():
        return redirect(url_for('admin.dashboard'))
    return redirect(url_for('user.dashboard'))


@app.route('/login')
def login_redirect():
    """Redirect to the user login route."""
    return redirect(url_for('auth.user_login'))


@app.route('/admin')
def admin_redirect():
    """Redirect to the admin login page."""
    return redirect(url_for('auth.admin_login'))


@app.route('/user')
def user_redirect():
    """Redirect to the user login page."""
    return redirect(url_for('auth.user_login'))


# Add custom HTTP error handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('errors/404.html'), 404

@app.errorhandler(403)
def access_forbidden(e):
    """Handle 403 errors - redirect users to appropriate dashboard instead of showing error"""
    if current_user.is_authenticated:
        if current_user.is_admin():
            flash('Access denied to that resource.', 'warning')
            return redirect(url_for('admin.dashboard'))
        else:
            flash('You don\'t have permission to access that page. Redirected to your dashboard.', 'info')
            return redirect(url_for('user.dashboard'))
    else:
        flash('Please log in to access that page.', 'warning')
        return redirect(url_for('auth.login'))

@app.errorhandler(500)
def server_error(e):
    return render_template('errors/500.html'), 500


# Add a custom response function to ensure proper headers
def json_response(data, status=200):
    """Return a JSON response with the correct content type"""
    response = jsonify(data)
    response.status_code = status
    response.headers['Content-Type'] = 'application/json'
    return response

@app.route('/api/preview-file', methods=['POST'])
def preview_file():
    """Preview file contents and URL count before processing"""
    try:
        if 'file' not in request.files:
            return json_response({'error': 'No file uploaded'}, 400)
        
        file = request.files['file']
        if file.filename == '':
            return json_response({'error': 'No file selected'}, 400)
        
        # Check file type
        if not file.filename.lower().endswith(('.csv', '.xlsx', '.xls', '.txt')):
            return json_response({'error': 'Invalid file format. Please upload CSV, Excel, or TXT file'}, 400)
        
        # Save file temporarily to read it
        filename = secure_filename(file.filename)
        temp_file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"temp_{filename}")
        file.save(temp_file_path)
        
        try:
            # Read and count URLs
            urls = process_url_file(temp_file_path)
            url_count = len(urls)
            
            # Get user's limit
            current_user_obj = current_user if current_user.is_authenticated else None
            user_limit = get_user_url_limit(current_user_obj)
            
            preview_urls = urls[:5]  # Show first 5 URLs as preview
            
            return json_response({
                'url_count': url_count,
                'user_limit': user_limit,
                'preview_urls': preview_urls,
                'exceeds_limit': url_count > user_limit,
                'filename': file.filename
            })
            
        finally:
            # Clean up temp file
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
                
    except Exception as e:
        logger.error(f"Error previewing file: {str(e)}")
        return json_response({'error': str(e)}, 500)

@app.route('/api/upload', methods=['POST'])
def upload_urls():
    """Handle file upload and start scraping job"""
    try:
        # Check if user is authenticated to track job history
        user_id = None
        if current_user.is_authenticated:
            user_id = current_user.id
            
            # Check if user has exceeded scraping limit
            if current_user.subscription:
                # Get user's recent jobs count
                recent_jobs = ScrapeJobHistory.query.filter_by(user_id=user_id).count()
                
                if recent_jobs >= current_user.subscription.scrape_limit:
                    return json_response({
                        'error': f'You have reached your scraping limit of {current_user.subscription.scrape_limit} jobs. Please upgrade your subscription or wait for your limit to reset.'
                    }, 403)
        
        # Check if file is present
        if 'file' not in request.files:
            return json_response({'error': 'No file part'}, 400)
        
        file = request.files['file']
        if file.filename == '':
            return json_response({'error': 'No selected file'}, 400)
        
        # Check file type
        if not file.filename.lower().endswith(('.csv', '.xlsx', '.xls', '.txt')):
            return json_response({'error': 'Invalid file format. Please upload CSV, Excel, or TXT file'}, 400)
        
        # Save file
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Process URLs
        urls = process_url_file(file_path)
        
        # Check if we have valid URLs
        if not urls:
            return json_response({'error': 'No valid URLs found in the file'}, 400)
        
        # Get dynamic URL limit based on user status
        current_user_obj = current_user if current_user.is_authenticated else None
        max_urls = get_user_url_limit(current_user_obj)
        
        # Limit number of URLs
        if len(urls) > max_urls:
            return json_response({
                'error': f'Too many URLs. Maximum allowed is {max_urls} URLs per batch for your account type'
            }, 400)
        
        # Generate job ID
        job_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create job
        job = ScrapeJob(job_id, len(urls))
        active_jobs[job_id] = job
        
        # Start scraping thread
        thread = threading.Thread(
            target=run_scrape_job, 
            args=(job, urls, True, user_id)
        )
        thread.daemon = True
        thread.start()
        
        return json_response({
            'success': True,
            'job_id': job_id,
            'message': f'Scraping job started with {len(urls)} URLs',
            'total_urls': len(urls)
        }, 202)
        
    except Exception as e:
        logger.error(f"Error in upload: {str(e)}")
        return json_response({'error': str(e)}, 500)


@app.route('/api/jobs/<job_id>', methods=['GET'])
def get_job_status(job_id):
    """Get status of a specific job"""
    if job_id not in active_jobs:
        return json_response({'error': 'Job not found'}, 404)
    
    job = active_jobs[job_id]
    return json_response(job.to_dict())


@app.route('/api/jobs', methods=['GET'])
def get_all_jobs():
    """Get status of all jobs"""
    return json_response({
        'jobs': [job.to_dict() for job in active_jobs.values()]
    })


@app.route('/api/download/<job_id>', methods=['GET'])
def download_results(job_id):
    """Download results file"""
    if job_id not in active_jobs:
        return jsonify({'error': 'Job not found'}), 404
    
    job = active_jobs[job_id]
    
    if job.status != "completed" or not job.result_file:
        return jsonify({'error': 'Results not available'}), 404
    
    try:
        # Set appropriate headers for file download
        filename = f"scrape_results_{job_id}.xlsx"
        
        response = send_file(
            job.result_file, 
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
        # Add extra headers to ensure download works properly
        response.headers["Content-Disposition"] = f"attachment; filename={filename}"
        response.headers["X-Suggested-Filename"] = filename
        response.headers["Access-Control-Expose-Headers"] = "Content-Disposition, X-Suggested-Filename"
        
        return response
    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}")
        return jsonify({'error': 'Failed to download file'}), 500


@app.route('/api/results/<job_id>', methods=['GET'])
def get_job_results(job_id):
    """Get detailed results for a specific job"""
    if job_id not in active_jobs:
        logger.error(f"Job not found: {job_id}")
        return json_response({'error': 'Job not found'}, 404)
    
    job = active_jobs[job_id]
    
    if job.status != "completed":
        logger.error(f"Job not completed: {job_id}, status: {job.status}")
        return json_response({'error': 'Results not available - job not completed'}, 404)
    
    logger.info(f"Job {job_id} has {len(job.results)} raw results")
    
    try:
        # For all cases, prefer job.results as the primary source
        if job.results and len(job.results) > 0:
            logger.info(f"Using results directly from job object: {len(job.results)} results")
            
            results = []
            for idx, result in enumerate(job.results):
                if idx == 0:
                    logger.info(f"Processing job result [0]: {result}")
                
                processed_result = {
                    'url': result.get('url', ''),
                    'domain': result.get('domain', ''),
                    'emails': result.get('emails', []) if isinstance(result.get('emails', []), list) else [],
                    'phones': result.get('phones', []) if isinstance(result.get('phones', []), list) else [],
                    'status': result.get('status', ''),
                    'social_media': result.get('social_media', {})
                }
                results.append(processed_result)
            
            logger.info(f"Processed {len(results)} results directly from job.results")
            
            if results:
                return json_response({
                    'job_id': job_id,
                    'total_results': len(results),
                    'results': results
                })
        
        # Fallback to Excel file
        if not job.result_file:
            logger.error(f"No result file available for job {job_id}")
            return json_response({'error': 'Results file not available'}, 404)
            
        logger.info(f"Reading results from Excel file: {job.result_file}")
        df = pd.read_excel(job.result_file)
        
        logger.info(f"Read DataFrame with {len(df)} rows and columns: {list(df.columns)}")
        
        if df.empty:
            logger.warning(f"DataFrame is empty for job {job_id}")
            return json_response({
                'job_id': job_id,
                'total_results': 0,
                'results': []
            })
        
        # Format results from Excel
        results = []
        for idx, row in df.iterrows():
            if idx == 0:
                logger.info(f"Processing Excel row [0]: {row.to_dict()}")
                
            result = {
                'url': row.get('url', ''),
                'domain': row.get('domain', ''),
                'emails': row.get('emails', '').split(', ') if isinstance(row.get('emails', ''), str) and row.get('emails', '') else [],
                'phones': row.get('phones', '').split(', ') if isinstance(row.get('phones', ''), str) and row.get('phones', '') else [],
                'status': row.get('status', '')
            }
            
            # Add social media if present
            social_media = {}
            for col in df.columns:
                if col in ['linkedin', 'twitter', 'facebook']:
                    if pd.notna(row.get(col)):
                        social_media[col] = row.get(col)
            
            result['social_media'] = social_media
            results.append(result)
        
        logger.info(f"Formatted {len(results)} results from Excel for job {job_id}")
        
        if results:
            logger.info(f"First result from Excel: {results[0]}")
        
        return json_response({
            'job_id': job_id,
            'total_results': len(results),
            'results': results
        })
        
    except Exception as e:
        logger.error(f"Error retrieving results for job {job_id}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return json_response({'error': f'Failed to retrieve results: {str(e)}'}, 500)


@app.route('/api/manual', methods=['POST'])
def manual_scrape():
    """Handle manual URL input"""
    try:
        # Check if user is authenticated to track job history
        user_id = None
        if current_user.is_authenticated:
            user_id = current_user.id
            
            # Check if user has exceeded scraping limit
            if current_user.subscription:
                # Get user's recent jobs count
                recent_jobs = ScrapeJobHistory.query.filter_by(user_id=user_id).count()
                
                if recent_jobs >= current_user.subscription.scrape_limit:
                    return json_response({
                        'error': f'You have reached your scraping limit of {current_user.subscription.scrape_limit} jobs. Please upgrade your subscription or wait for your limit to reset.'
                    }, 403)
        
        data = request.json
        
        if not data or 'urls' not in data:
            return json_response({'error': 'No URLs provided'}, 400)
        
        urls = data['urls']
        
        # Validate URLs
        if not isinstance(urls, list):
            return json_response({'error': 'URLs must be provided as a list'}, 400)
        
        # Filter out empty URLs
        urls = [url.strip() for url in urls if url and isinstance(url, str)]
        
        if not urls:
            return json_response({'error': 'No valid URLs provided'}, 400)
        
        # Get dynamic URL limit based on user status
        current_user_obj = current_user if current_user.is_authenticated else None
        max_urls = get_user_url_limit(current_user_obj)
        
        # Limit number of URLs
        if len(urls) > max_urls:
            return json_response({
                'error': f'Too many URLs. Maximum allowed is {max_urls} URLs per batch for your account type'
            }, 400)
        
        # Generate job ID
        job_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create job
        job = ScrapeJob(job_id, len(urls))
        active_jobs[job_id] = job
        
        # Start scraping thread
        thread = threading.Thread(
            target=run_scrape_job, 
            args=(job, urls, True, user_id)
        )
        thread.daemon = True
        thread.start()
        
        return json_response({
            'success': True,
            'job_id': job_id,
            'message': f'Scraping job started with {len(urls)} URLs',
            'total_urls': len(urls)
        }, 202)
        
    except Exception as e:
        logger.error(f"Error in manual scrape: {str(e)}")
        return json_response({'error': str(e)}, 500)


@app.route('/page/<slug>')
def view_page(slug):
    """View a public page by slug"""
    page = Page.query.filter_by(slug=slug, published=True).first_or_404()
    
    template = f'pages/{page.layout_template}.html'
    
    # Check if template exists, default to 'default' if not
    try:
        from flask import current_app
        current_app.jinja_env.get_template(template)
    except:
        template = 'pages/default.html'
    
    return render_template(template, page=page)

@app.route('/blog')
def blog_list():
    """Display list of published blog posts"""
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # Get published blog posts
    posts = BlogPost.query.filter_by(published=True).order_by(BlogPost.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Get categories for sidebar
    categories = BlogCategory.query.all()
    
    # Get recent posts
    recent_posts = BlogPost.query.filter_by(published=True).order_by(BlogPost.created_at.desc()).limit(5).all()
    
    return render_template('blog/list.html', 
                         posts=posts, 
                         categories=categories,
                         recent_posts=recent_posts)

@app.route('/blog/<slug>')
def view_blog_post(slug):
    """View a single blog post by slug"""
    post = BlogPost.query.filter_by(slug=slug, published=True).first_or_404()
    
    # Get related posts (same category)
    related_posts = BlogPost.query.filter_by(
        category_id=post.category_id, 
        published=True
    ).filter(BlogPost.id != post.id).limit(3).all()
    
    # Get categories for sidebar
    categories = BlogCategory.query.all()
    
    # Get recent posts
    recent_posts = BlogPost.query.filter_by(published=True).order_by(BlogPost.created_at.desc()).limit(5).all()
    
    return render_template('blog/post.html', 
                         post=post, 
                         related_posts=related_posts,
                         categories=categories,
                         recent_posts=recent_posts)

@app.route('/blog/category/<slug>')
def view_blog_category(slug):
    """View blog posts by category"""
    category = BlogCategory.query.filter_by(slug=slug).first_or_404()
    
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    posts = BlogPost.query.filter_by(
        category_id=category.id, 
        published=True
    ).order_by(BlogPost.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Get all categories for sidebar
    categories = BlogCategory.query.all()
    
    # Get recent posts
    recent_posts = BlogPost.query.filter_by(published=True).order_by(BlogPost.created_at.desc()).limit(5).all()
    
    return render_template('blog/category.html', 
                         category=category,
                         posts=posts, 
                         categories=categories,
                         recent_posts=recent_posts)

@app.route('/api/admin/sync-jobs', methods=['POST'])
@login_required
def sync_job_statuses():
    """Manually synchronize job statuses between memory and database"""
    if not current_user.is_admin():
        return json_response({'error': 'Admin access required'}, 403)
    
    try:
        # Get all database jobs that are still marked as in_progress
        stuck_jobs = ScrapeJobHistory.query.filter_by(status='in_progress').all()
        
        fixed_count = 0
        messages = []
        
        for db_job in stuck_jobs:
            # Check if this job exists in memory
            if db_job.job_id in active_jobs:
                memory_job = active_jobs[db_job.job_id]
                
                # If memory job is completed but database isn't, update database
                if memory_job.status == "completed" and db_job.status == 'in_progress':
                    try:
                        db_job.status = 'completed'
                        db_job.completed_at = datetime.now(timezone.utc)
                        if memory_job.result_file:
                            db_job.result_file = memory_job.result_file
                        if hasattr(memory_job, 'results'):
                            total_emails = sum(len(result.get('emails', [])) for result in memory_job.results if isinstance(result.get('emails', []), list))
                            db_job.emails_found = total_emails
                            db_job.successful_urls = len(memory_job.results)
                        
                        db.session.commit()
                        fixed_count += 1
                        messages.append(f"Fixed job {db_job.job_id}: completed")
                    except Exception as e:
                        db.session.rollback()
                        messages.append(f"Error fixing job {db_job.job_id}: {str(e)}")
                
                elif memory_job.status == "error" and db_job.status == 'in_progress':
                    try:
                        db_job.status = 'failed'
                        db_job.completed_at = datetime.now(timezone.utc)
                        db.session.commit()
                        fixed_count += 1
                        messages.append(f"Fixed job {db_job.job_id}: failed")
                    except Exception as e:
                        db.session.rollback()
                        messages.append(f"Error fixing job {db_job.job_id}: {str(e)}")
            else:
                # For jobs not in memory, check if they're old and mark as failed
                if db_job.created_at:
                    time_elapsed = datetime.now(timezone.utc) - db_job.created_at.replace(tzinfo=timezone.utc)
                    if time_elapsed.total_seconds() > 3600:  # 1 hour
                        try:
                            db_job.status = 'failed'
                            db_job.completed_at = datetime.now(timezone.utc)
                            db.session.commit()
                            fixed_count += 1
                            messages.append(f"Marked old job {db_job.job_id} as failed (running for {time_elapsed})")
                        except Exception as e:
                            db.session.rollback()
                            messages.append(f"Error marking old job {db_job.job_id} as failed: {str(e)}")
        
        return json_response({
            'success': True,
            'fixed_count': fixed_count,
            'total_stuck_jobs': len(stuck_jobs),
            'messages': messages
        })
        
    except Exception as e:
        logger.error(f"Error in job sync: {str(e)}")
        return json_response({'error': str(e)}, 500)

@app.route('/api/user/credits')
@login_required
def get_user_credits():
    """Get user's remaining credits and usage"""
    try:
        # Calculate user's usage this month
        month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Count scraping jobs this month
        jobs_this_month = ScrapeJobHistory.query.filter_by(
            user_id=current_user.id
        ).filter(ScrapeJobHistory.created_at >= month_start).count()
        
        # Get user's subscription info
        subscription_limit = 0
        if current_user.subscription:
            subscription_limit = current_user.subscription.scrape_limit
        
        remaining_credits = max(0, subscription_limit - jobs_this_month)
        
        return json_response({
            'user_id': current_user.id,
            'subscription_limit': subscription_limit,
            'used_this_month': jobs_this_month,
            'remaining_credits': remaining_credits,
            'subscription_name': current_user.subscription.name if current_user.subscription else 'Free'
        })
        
    except Exception as e:
        logger.error(f"Error getting user credits: {str(e)}")
        return json_response({'error': str(e)}, 500)

# Template context processor to add common variables to all templates
@app.context_processor
def utility_processor():
    """Make utility functions and data available to all templates"""
    
    def get_pending_comments_count():
        """Get count of pending blog comments for admin notification"""
        try:
            from models import BlogComment
            return BlogComment.query.filter_by(approved=False).count()
        except:
            return 0
    
    def get_user_limit():
        """Get the current user's URL limit for frontend display"""
        try:
            current_user_obj = current_user if current_user.is_authenticated else None
            return get_user_url_limit(current_user_obj)
        except:
            return 10  # Default guest limit
    
    def get_limit_description():
        """Get a description of the user's current limit"""
        try:
            if not current_user.is_authenticated:
                return "Guest users"
            elif current_user.is_admin():
                return "Admin (unlimited)"
            elif hasattr(current_user, 'custom_scrape_limit') and current_user.custom_scrape_limit is not None:
                return "Custom limit"
            elif current_user.subscription and current_user.subscription.is_active:
                return f"Subscription ({current_user.subscription.name})"
            else:
                return "Free registered user"
        except:
            return "Guest users"
    
    return {
        'get_pending_comments_count': get_pending_comments_count,
        'get_user_limit': get_user_limit,
        'get_limit_description': get_limit_description
    }

def get_user_url_limit(user=None):
    """Get the effective URL limit for the current user or guest"""
    if user is None:
        # Guest user (not logged in) - limit to 10 URLs
        return 10
    
    # Use the user's get_scrape_limit method which handles all logic
    limit = user.get_scrape_limit()
    
    # Convert infinity to a large number for practical purposes
    if limit == float('inf'):
        return 999999  # Effectively unlimited for admin
    
    return int(limit)

if __name__ == '__main__':
    with app.app_context():
        # Create database tables
        db.create_all()
        
        # Load settings
        load_settings()
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True) 