import os
import re
import uuid
import random
import string
from datetime import datetime
from flask import current_app
from flask_mail import Message, Mail
from PIL import Image
import math

mail = Mail()

def send_email(subject, recipients, body, html=None):
    """Send email utility function"""
    try:
        msg = Message(
            subject=subject,
            recipients=recipients,
            body=body,
            html=html,
            sender=current_app.config.get('MAIL_DEFAULT_SENDER')
        )
        mail.send(msg)
        return True
    except Exception as e:
        current_app.logger.error(f"Email sending failed: {str(e)}")
        return False

def get_setting(key, default=None):
    """Get a setting from the database or return default"""
    from models import SiteSetting
    setting = SiteSetting.query.filter_by(key=key).first()
    return setting.value if setting else default

def generate_slug(text):
    """Generate a URL-friendly slug from the given text"""
    # Convert to lowercase and remove special characters
    slug = text.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    # Replace spaces with hyphens
    slug = re.sub(r'\s+', '-', slug)
    # Remove consecutive hyphens
    slug = re.sub(r'-+', '-', slug)
    # Remove leading and trailing hyphens
    slug = slug.strip('-')
    return slug

def unique_slug(text, model, instance_id=None):
    """Generate a unique slug for a model instance"""
    original_slug = generate_slug(text)
    slug = original_slug
    query = model.query.filter_by(slug=slug)
    
    # If editing an existing instance, exclude it from the uniqueness check
    if instance_id:
        query = query.filter(model.id != instance_id)
    
    instance = query.first()
    counter = 1
    
    # If the slug already exists, append a number to it
    while instance:
        slug = f"{original_slug}-{counter}"
        query = model.query.filter_by(slug=slug)
        if instance_id:
            query = query.filter(model.id != instance_id)
        instance = query.first()
        counter += 1
    
    return slug

def generate_api_key():
    """Generate a secure API key"""
    return str(uuid.uuid4()) + str(uuid.uuid4()).replace('-', '')

def format_datetime(value, format='%Y-%m-%d %H:%M:%S'):
    """Format a datetime object to string"""
    if value is None:
        return ""
    return value.strftime(format)

def format_date(value, format='%Y-%m-%d'):
    """Format a date object to string"""
    if value is None:
        return ""
    return value.strftime(format)

def save_image(file, folder, size=(800, 800)):
    """Save an image file and optionally resize it"""
    if not file:
        return None
    
    # Generate random filename
    random_hex = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    _, file_ext = os.path.splitext(file.filename)
    filename = random_hex + file_ext.lower()  # Ensure lowercase extension
    
    # Create folder if it doesn't exist
    if folder.startswith('/'):
        # Handle absolute path
        upload_folder = os.path.join(current_app.root_path, folder.lstrip('/'))
    else:
        # Handle relative path (from static folder)
        upload_folder = os.path.join(current_app.static_folder, folder)
    
    os.makedirs(upload_folder, exist_ok=True)
    
    # Save original file
    file_path = os.path.join(upload_folder, filename)
    file.save(file_path)
    
    # Resize image if needed
    if size:
        try:
            with Image.open(file_path) as img:
                # Use reduce instead of thumbnail for Pillow 11.2.1
                img.thumbnail(size, Image.LANCZOS)  # LANCZOS is a high-quality resampling filter
                img.save(file_path, optimize=True)
        except Exception as e:
            current_app.logger.error(f"Image processing error: {str(e)}")
    
    # Return path relative to static for templates
    if folder.startswith('/'):
        return os.path.join(folder, filename).lstrip('/')
    else:
        return f"{folder}/{filename}"

def delete_image(filepath):
    """Delete an image file"""
    if not filepath:
        return
    
    # Get full path
    if filepath.startswith('/'):
        # Handle absolute path
        full_path = os.path.join(current_app.root_path, filepath.lstrip('/'))
    else:
        # Handle relative path (from static folder)
        full_path = os.path.join(current_app.static_folder, filepath)
    
    # Check if file exists
    if os.path.exists(full_path):
        os.remove(full_path)

def human_readable_size(size_bytes):
    """Convert bytes to human-readable format"""
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}" 