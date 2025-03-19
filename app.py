from flask import Flask, render_template, request, jsonify, send_file, url_for
from werkzeug.utils import secure_filename
from scraper import ContactScraper
import os
import logging
import pandas as pd
import threading
import queue
import time
import json
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import re
import urllib.parse

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
    SECRET_KEY=os.urandom(24),
    UPLOAD_FOLDER='uploads',
    MAX_CONTENT_LENGTH=10 * 1024 * 1024,  # 10MB max upload
    MAX_URLS_PER_BATCH=100,  # Maximum number of URLs to process in one batch
)

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('results', exist_ok=True)

# Global variables for tracking progress
active_jobs = {}


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
        
    def complete(self, result_file):
        """Mark job as completed"""
        self.status = "completed"
        self.end_time = time.time()
        self.result_file = result_file
        
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

def run_scrape_job(job, urls, headless=True):
    """Run scraping job in a separate thread"""
    try:
        job.status = "running"
        
        # Use simple scraper by default for better performance
        logger.info("Using requests-based scraper for better performance")
        
        # Process URLs with simple scraper
        results = []
        total = len(urls)
        for i, url in enumerate(urls):
            result = simple_scrape_url(url)
            results.append(result)
            job.update_progress(i+1, total)
            
            # Store partial results directly with the job
            job.results = results.copy()
            
        # Generate timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_file = f"results/scrape_results_{timestamp}.xlsx"
        
        # Export results
        df = pd.DataFrame(results)
        
        # Handle empty DataFrame
        if df.empty:
            df = pd.DataFrame(columns=['url', 'domain', 'emails', 'phones', 'social_media', 'status'])
        
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
        
        final_df.to_excel(result_file, index=False)
        logger.info(f"Results exported to {result_file}")
        
        # Mark job as completed
        job.complete(result_file)
        
    except Exception as e:
        logger.error(f"Error in scrape job {job.job_id}: {str(e)}")
        job.fail(str(e))


@app.route('/')
def index():
    """Render main page"""
    return render_template('index.html')


@app.route('/api/upload', methods=['POST'])
def upload_urls():
    """Handle file upload and start scraping job"""
    try:
        # Check if file is present
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        
        # Check file type
        if not file.filename.lower().endswith(('.csv', '.xlsx', '.xls', '.txt')):
            return jsonify({'error': 'Invalid file format. Please upload CSV, Excel, or TXT file'}), 400
        
        # Save file
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Process URLs
        urls = process_url_file(file_path)
        
        # Check if we have valid URLs
        if not urls:
            return jsonify({'error': 'No valid URLs found in the file'}), 400
        
        # Limit number of URLs per batch
        if len(urls) > app.config['MAX_URLS_PER_BATCH']:
            return jsonify({
                'error': f'Too many URLs. Maximum allowed is {app.config["MAX_URLS_PER_BATCH"]} URLs per batch'
            }), 400
        
        # Generate job ID
        job_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create job
        job = ScrapeJob(job_id, len(urls))
        active_jobs[job_id] = job
        
        # Start scraping thread
        thread = threading.Thread(
            target=run_scrape_job, 
            args=(job, urls)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'job_id': job_id,
            'message': f'Scraping job started with {len(urls)} URLs',
            'total_urls': len(urls)
        }), 202
        
    except Exception as e:
        logger.error(f"Error in upload: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/jobs/<job_id>', methods=['GET'])
def get_job_status(job_id):
    """Get status of a specific job"""
    if job_id not in active_jobs:
        return jsonify({'error': 'Job not found'}), 404
    
    job = active_jobs[job_id]
    return jsonify(job.to_dict())


@app.route('/api/jobs', methods=['GET'])
def get_all_jobs():
    """Get status of all jobs"""
    return jsonify({
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
        # Fix for download issue - force download with correct content type
        return send_file(
            job.result_file, 
            as_attachment=True,
            download_name=os.path.basename(job.result_file),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}")
        return jsonify({'error': 'Failed to download file'}), 500


@app.route('/api/results/<job_id>', methods=['GET'])
def get_job_results(job_id):
    """Get detailed results for a specific job"""
    if job_id not in active_jobs:
        return jsonify({'error': 'Job not found'}), 404
    
    job = active_jobs[job_id]
    
    if job.status != "completed" or not job.result_file:
        return jsonify({'error': 'Results not available'}), 404
    
    try:
        # Read the Excel file and convert to JSON
        df = pd.read_excel(job.result_file)
        
        # Format the results for display
        results = []
        for _, row in df.iterrows():
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
        
        return jsonify({
            'job_id': job_id,
            'total_results': len(results),
            'results': results
        })
        
    except Exception as e:
        logger.error(f"Error retrieving results: {str(e)}")
        return jsonify({'error': 'Failed to retrieve results'}), 500


@app.route('/api/manual', methods=['POST'])
def manual_scrape():
    """Handle manual URL input"""
    try:
        data = request.json
        
        if not data or 'urls' not in data:
            return jsonify({'error': 'No URLs provided'}), 400
        
        urls = data['urls']
        
        # Validate URLs
        if not isinstance(urls, list):
            return jsonify({'error': 'URLs must be provided as a list'}), 400
        
        # Filter out empty URLs
        urls = [url.strip() for url in urls if url and isinstance(url, str)]
        
        if not urls:
            return jsonify({'error': 'No valid URLs provided'}), 400
        
        # Limit number of URLs
        if len(urls) > app.config['MAX_URLS_PER_BATCH']:
            return jsonify({
                'error': f'Too many URLs. Maximum allowed is {app.config["MAX_URLS_PER_BATCH"]} URLs per batch'
            }), 400
        
        # Generate job ID
        job_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create job
        job = ScrapeJob(job_id, len(urls))
        active_jobs[job_id] = job
        
        # Start scraping thread
        thread = threading.Thread(
            target=run_scrape_job, 
            args=(job, urls)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'job_id': job_id,
            'message': f'Scraping job started with {len(urls)} URLs',
            'total_urls': len(urls)
        }), 202
        
    except Exception as e:
        logger.error(f"Error in manual scrape: {str(e)}")
        return jsonify({'error': str(e)}), 500


# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def server_error(error):
    return jsonify({'error': 'Server error'}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port) 