from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from datetime import datetime
import os

from models import db, BlogPost, BlogCategory, BlogTag, BlogComment
from auth import editor_required
from utils import unique_slug, save_image, delete_image

# Create blueprint
blog_bp = Blueprint('blog', __name__, url_prefix='/admin/blog')

# Blog Posts
@blog_bp.route('/posts')
@editor_required
def posts():
    """List all blog posts"""
    posts = BlogPost.query.order_by(BlogPost.created_at.desc()).all()
    return render_template('admin/blog/posts/index.html', posts=posts)

@blog_bp.route('/posts/create', methods=['GET', 'POST'])
@editor_required
def create_post():
    """Create a new blog post"""
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        excerpt = request.form.get('excerpt')
        category_id = request.form.get('category_id') or None
        tag_ids = request.form.getlist('tags')
        published = 'published' in request.form
        meta_title = request.form.get('meta_title')
        meta_description = request.form.get('meta_description')
        
        # Generate slug
        slug = unique_slug(title, BlogPost)
        
        # Handle featured image
        featured_image = None
        if 'featured_image' in request.files and request.files['featured_image']:
            featured_image = save_image(request.files['featured_image'], 'uploads/blog')
        
        # Create post
        post = BlogPost(
            title=title,
            slug=slug,
            content=content,
            excerpt=excerpt,
            category_id=category_id,
            featured_image=featured_image,
            published=published,
            meta_title=meta_title,
            meta_description=meta_description,
            author_id=current_user.id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Add tags
        if tag_ids:
            tags = BlogTag.query.filter(BlogTag.id.in_(tag_ids)).all()
            post.tags = tags
        
        db.session.add(post)
        db.session.commit()
        
        flash('Blog post created successfully!', 'success')
        return redirect(url_for('blog.posts'))
    
    categories = BlogCategory.query.all()
    tags = BlogTag.query.all()
    return render_template('admin/blog/posts/create.html', categories=categories, tags=tags)

@blog_bp.route('/posts/edit/<int:post_id>', methods=['GET', 'POST'])
@editor_required
def edit_post(post_id):
    """Edit an existing blog post"""
    post = BlogPost.query.get_or_404(post_id)
    
    # Check if user is the author or an admin
    if post.author_id != current_user.id and not current_user.is_admin():
        flash('You do not have permission to edit this post.', 'danger')
        return redirect(url_for('blog.posts'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        excerpt = request.form.get('excerpt')
        category_id = request.form.get('category_id') or None
        tag_ids = request.form.getlist('tags')
        published = 'published' in request.form
        meta_title = request.form.get('meta_title')
        meta_description = request.form.get('meta_description')
        
        # Generate slug if title changed
        if title != post.title:
            slug = unique_slug(title, BlogPost, post.id)
            post.slug = slug
        
        # Handle featured image
        if 'featured_image' in request.files and request.files['featured_image']:
            # Delete old image if exists
            if post.featured_image:
                delete_image(post.featured_image)
            
            featured_image = save_image(request.files['featured_image'], 'uploads/blog')
            post.featured_image = featured_image
        
        # Update post
        post.title = title
        post.content = content
        post.excerpt = excerpt
        post.category_id = category_id
        post.published = published
        post.meta_title = meta_title
        post.meta_description = meta_description
        post.updated_at = datetime.utcnow()
        
        # Update tags
        if tag_ids:
            tags = BlogTag.query.filter(BlogTag.id.in_(tag_ids)).all()
            post.tags = tags
        else:
            post.tags = []
        
        db.session.commit()
        
        flash('Blog post updated successfully!', 'success')
        return redirect(url_for('blog.posts'))
    
    categories = BlogCategory.query.all()
    tags = BlogTag.query.all()
    post_tag_ids = [tag.id for tag in post.tags]
    
    return render_template('admin/blog/posts/edit.html', 
                           post=post, 
                           categories=categories, 
                           tags=tags,
                           post_tag_ids=post_tag_ids)

@blog_bp.route('/posts/delete/<int:post_id>', methods=['POST'])
@editor_required
def delete_post(post_id):
    """Delete a blog post"""
    post = BlogPost.query.get_or_404(post_id)
    
    # Check if user is the author or an admin
    if post.author_id != current_user.id and not current_user.is_admin():
        flash('You do not have permission to delete this post.', 'danger')
        return redirect(url_for('blog.posts'))
    
    # Delete associated image
    if post.featured_image:
        delete_image(post.featured_image)
    
    db.session.delete(post)
    db.session.commit()
    
    flash('Blog post deleted successfully!', 'success')
    return redirect(url_for('blog.posts'))

# Blog Categories
@blog_bp.route('/categories')
@editor_required
def categories():
    """List all blog categories"""
    categories = BlogCategory.query.all()
    return render_template('admin/blog/categories/index.html', categories=categories)

@blog_bp.route('/categories/create', methods=['GET', 'POST'])
@editor_required
def create_category():
    """Create a new blog category"""
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        
        # Generate slug
        slug = unique_slug(name, BlogCategory)
        
        # Create category
        category = BlogCategory(
            name=name,
            slug=slug,
            description=description
        )
        
        db.session.add(category)
        db.session.commit()
        
        flash('Category created successfully!', 'success')
        return redirect(url_for('blog.categories'))
    
    return render_template('admin/blog/categories/create.html')

@blog_bp.route('/categories/edit/<int:category_id>', methods=['GET', 'POST'])
@editor_required
def edit_category(category_id):
    """Edit an existing blog category"""
    category = BlogCategory.query.get_or_404(category_id)
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        
        # Generate slug if name changed
        if name != category.name:
            slug = unique_slug(name, BlogCategory, category.id)
            category.slug = slug
        
        # Update category
        category.name = name
        category.description = description
        
        db.session.commit()
        
        flash('Category updated successfully!', 'success')
        return redirect(url_for('blog.categories'))
    
    return render_template('admin/blog/categories/edit.html', category=category)

@blog_bp.route('/categories/delete/<int:category_id>', methods=['POST'])
@editor_required
def delete_category(category_id):
    """Delete a blog category"""
    category = BlogCategory.query.get_or_404(category_id)
    
    # Check if category has posts
    if category.posts:
        flash('Cannot delete category because it has associated posts.', 'danger')
        return redirect(url_for('blog.categories'))
    
    db.session.delete(category)
    db.session.commit()
    
    flash('Category deleted successfully!', 'success')
    return redirect(url_for('blog.categories'))

# Blog Tags
@blog_bp.route('/tags')
@editor_required
def tags():
    """List all blog tags"""
    tags = BlogTag.query.all()
    return render_template('admin/blog/tags/index.html', tags=tags)

@blog_bp.route('/tags/create', methods=['GET', 'POST'])
@editor_required
def create_tag():
    """Create a new blog tag"""
    if request.method == 'POST':
        name = request.form.get('name')
        
        # Generate slug
        slug = unique_slug(name, BlogTag)
        
        # Create tag
        tag = BlogTag(
            name=name,
            slug=slug
        )
        
        db.session.add(tag)
        db.session.commit()
        
        flash('Tag created successfully!', 'success')
        return redirect(url_for('blog.tags'))
    
    return render_template('admin/blog/tags/create.html')

@blog_bp.route('/tags/edit/<int:tag_id>', methods=['GET', 'POST'])
@editor_required
def edit_tag(tag_id):
    """Edit an existing blog tag"""
    tag = BlogTag.query.get_or_404(tag_id)
    
    if request.method == 'POST':
        name = request.form.get('name')
        
        # Generate slug if name changed
        if name != tag.name:
            slug = unique_slug(name, BlogTag, tag.id)
            tag.slug = slug
        
        # Update tag
        tag.name = name
        
        db.session.commit()
        
        flash('Tag updated successfully!', 'success')
        return redirect(url_for('blog.tags'))
    
    return render_template('admin/blog/tags/edit.html', tag=tag)

@blog_bp.route('/tags/delete/<int:tag_id>', methods=['POST'])
@editor_required
def delete_tag(tag_id):
    """Delete a blog tag"""
    tag = BlogTag.query.get_or_404(tag_id)
    
    # Remove tag from all posts instead of checking if it's in use
    # This allows deletion even if the tag is used
    tag.posts = []
    db.session.commit()
    
    db.session.delete(tag)
    db.session.commit()
    
    flash('Tag deleted successfully!', 'success')
    return redirect(url_for('blog.tags'))

# Blog Comments
@blog_bp.route('/comments')
@editor_required
def comments():
    """List all blog comments"""
    comments = BlogComment.query.order_by(BlogComment.created_at.desc()).all()
    return render_template('admin/blog/comments/index.html', comments=comments)

@blog_bp.route('/comments/approve/<int:comment_id>', methods=['POST'])
@editor_required
def approve_comment(comment_id):
    """Approve a blog comment"""
    comment = BlogComment.query.get_or_404(comment_id)
    
    comment.approved = True
    db.session.commit()
    
    flash('Comment approved successfully!', 'success')
    return redirect(url_for('blog.comments'))

@blog_bp.route('/comments/reject/<int:comment_id>', methods=['POST'])
@editor_required
def reject_comment(comment_id):
    """Reject and delete a blog comment"""
    comment = BlogComment.query.get_or_404(comment_id)
    
    db.session.delete(comment)
    db.session.commit()
    
    flash('Comment rejected and deleted successfully!', 'success')
    return redirect(url_for('blog.comments')) 