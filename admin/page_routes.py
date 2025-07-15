from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from datetime import datetime

from models import db, Page
from auth import editor_required
from utils import unique_slug

# Create blueprint
page_bp = Blueprint('page', __name__, url_prefix='/admin/pages')

@page_bp.route('/')
@editor_required
def pages():
    """List all pages"""
    pages = Page.query.order_by(Page.title).all()
    return render_template('admin/pages/index.html', pages=pages)

@page_bp.route('/create', methods=['GET', 'POST'])
@editor_required
def create_page():
    """Create a new page"""
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        published = 'published' in request.form
        meta_title = request.form.get('meta_title')
        meta_description = request.form.get('meta_description')
        layout_template = request.form.get('layout_template')
        
        # Generate slug
        slug = unique_slug(title, Page)
        
        # Create page
        page = Page(
            title=title,
            slug=slug,
            content=content,
            published=published,
            meta_title=meta_title,
            meta_description=meta_description,
            layout_template=layout_template,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.session.add(page)
        db.session.commit()
        
        flash('Page created successfully!', 'success')
        return redirect(url_for('page.pages'))
    
    # Get available templates
    templates = [
        {'value': 'default', 'name': 'Default Template'},
        {'value': 'full-width', 'name': 'Full Width'},
        {'value': 'sidebar', 'name': 'With Sidebar'},
        {'value': 'landing', 'name': 'Landing Page'}
    ]
    
    return render_template('admin/pages/create.html', templates=templates)

@page_bp.route('/edit/<int:page_id>', methods=['GET', 'POST'])
@editor_required
def edit_page(page_id):
    """Edit an existing page"""
    page = Page.query.get_or_404(page_id)
    
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        published = 'published' in request.form
        meta_title = request.form.get('meta_title')
        meta_description = request.form.get('meta_description')
        layout_template = request.form.get('layout_template')
        
        # Generate slug if title changed
        if title != page.title:
            slug = unique_slug(title, Page, page.id)
            page.slug = slug
        
        # Update page
        page.title = title
        page.content = content
        page.published = published
        page.meta_title = meta_title
        page.meta_description = meta_description
        page.layout_template = layout_template
        page.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        flash('Page updated successfully!', 'success')
        return redirect(url_for('page.pages'))
    
    # Get available templates
    templates = [
        {'value': 'default', 'name': 'Default Template'},
        {'value': 'full-width', 'name': 'Full Width'},
        {'value': 'sidebar', 'name': 'With Sidebar'},
        {'value': 'landing', 'name': 'Landing Page'}
    ]
    
    return render_template('admin/pages/edit.html', page=page, templates=templates)

@page_bp.route('/delete/<int:page_id>', methods=['POST'])
@editor_required
def delete_page(page_id):
    """Delete a page"""
    page = Page.query.get_or_404(page_id)
    
    db.session.delete(page)
    db.session.commit()
    
    flash('Page deleted successfully!', 'success')
    return redirect(url_for('page.pages')) 