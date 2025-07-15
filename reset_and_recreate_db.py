import os
import sys
import sqlite3

def reset_database():
    """Reset and recreate the database completely."""
    print("Resetting and recreating database...")
    
    # Database path
    db_path = 'contact_harvester.db'
    
    # Delete existing database if it exists
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
            print(f"✓ Deleted existing database: {db_path}")
        except Exception as e:
            print(f"✗ Failed to delete database: {e}")
            return False
    
    try:
        # Create a new database connection
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create Users table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username VARCHAR(100) NOT NULL UNIQUE,
            email VARCHAR(100) NOT NULL UNIQUE,
            password_hash VARCHAR(200) NOT NULL,
            first_name VARCHAR(50),
            last_name VARCHAR(50),
            created_at DATETIME,
            is_active BOOLEAN DEFAULT 1,
            profile_picture VARCHAR(255),
            last_login DATETIME,
            oauth_provider VARCHAR(50),
            oauth_id VARCHAR(255),
            subscription_id INTEGER,
            subscription_end_date DATETIME,
            two_factor_enabled BOOLEAN DEFAULT 0,
            two_factor_secret VARCHAR(255),
            FOREIGN KEY (subscription_id) REFERENCES subscriptions(id)
        )
        ''')
        
        # Create Roles table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS roles (
            id INTEGER PRIMARY KEY,
            name VARCHAR(50) NOT NULL UNIQUE,
            description VARCHAR(255)
        )
        ''')
        
        # Create User Roles junction table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_roles (
            user_id INTEGER NOT NULL,
            role_id INTEGER NOT NULL,
            PRIMARY KEY (user_id, role_id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (role_id) REFERENCES roles(id)
        )
        ''')
        
        # Create Subscription Plans table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS subscription_plans (
            id INTEGER PRIMARY KEY,
            name VARCHAR(100) NOT NULL UNIQUE,
            price FLOAT NOT NULL,
            duration_days INTEGER NOT NULL,
            features TEXT,
            is_active BOOLEAN DEFAULT 1,
            scrape_limit INTEGER DEFAULT 100
        )
        ''')
        
        # Create Subscriptions table with ALL required fields
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            price FLOAT NOT NULL,
            duration_days INTEGER NOT NULL,
            scrape_limit INTEGER NOT NULL,
            description TEXT,
            is_active BOOLEAN DEFAULT 1,
            plan_id INTEGER,
            status VARCHAR(50) DEFAULT 'active',
            currency VARCHAR(10) DEFAULT 'USD',
            is_public BOOLEAN DEFAULT 1,
            is_featured BOOLEAN DEFAULT 0,
            allow_cancellation BOOLEAN DEFAULT 1,
            stripe_plan_id VARCHAR(100),
            features TEXT,
            FOREIGN KEY (plan_id) REFERENCES subscription_plans(id)
        )
        ''')
        
        # Create Blog Categories table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS blog_categories (
            id INTEGER PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            slug VARCHAR(100) NOT NULL UNIQUE,
            description TEXT
        )
        ''')
        
        # Create Blog Tags table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS blog_tags (
            id INTEGER PRIMARY KEY,
            name VARCHAR(50) NOT NULL,
            slug VARCHAR(50) NOT NULL UNIQUE
        )
        ''')
        
        # Create Blog Posts table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS blog_posts (
            id INTEGER PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            slug VARCHAR(255) NOT NULL UNIQUE,
            content TEXT NOT NULL,
            excerpt TEXT,
            featured_image VARCHAR(255),
            created_at DATETIME,
            updated_at DATETIME,
            published BOOLEAN DEFAULT 0,
            meta_title VARCHAR(255),
            meta_description TEXT,
            author_id INTEGER,
            category_id INTEGER,
            FOREIGN KEY (author_id) REFERENCES users(id),
            FOREIGN KEY (category_id) REFERENCES blog_categories(id)
        )
        ''')
        
        # Create Blog Comments table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS blog_comments (
            id INTEGER PRIMARY KEY,
            post_id INTEGER,
            user_id INTEGER,
            content TEXT NOT NULL,
            created_at DATETIME,
            approved BOOLEAN DEFAULT 0,
            FOREIGN KEY (post_id) REFERENCES blog_posts(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        ''')
        
        # Create Post Tags junction table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS post_tags (
            post_id INTEGER,
            tag_id INTEGER,
            PRIMARY KEY (post_id, tag_id),
            FOREIGN KEY (post_id) REFERENCES blog_posts(id),
            FOREIGN KEY (tag_id) REFERENCES blog_tags(id)
        )
        ''')
        
        # Create Site Settings table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS site_settings (
            id INTEGER PRIMARY KEY,
            key VARCHAR(100) NOT NULL UNIQUE,
            value TEXT,
            category VARCHAR(50)
        )
        ''')
        
        # Create Pages table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS pages (
            id INTEGER PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            slug VARCHAR(255) NOT NULL UNIQUE,
            content TEXT NOT NULL,
            created_at DATETIME,
            updated_at DATETIME,
            published BOOLEAN DEFAULT 1,
            meta_title VARCHAR(255),
            meta_description TEXT,
            layout_template VARCHAR(100) DEFAULT 'default'
        )
        ''')
        
        # Insert default Roles
        cursor.execute('''
        INSERT INTO roles (name, description) VALUES
        ('admin', 'Administrator with full access'),
        ('editor', 'Editor with content management access'),
        ('user', 'Regular user with limited access')
        ''')
        
        # Create a default admin user (admin/admin123)
        admin_password_hash = 'pbkdf2:sha256:150000$lLgXgOSk$0a03dda7afe218b3bd9be56a2c93f340e3a55dcb6bfa8b0bbe74afa946184d7d'
        cursor.execute('''
        INSERT INTO users (username, email, password_hash, first_name, last_name, is_active, created_at)
        VALUES ('admin', 'admin@example.com', ?, 'Admin', 'User', 1, datetime('now'))
        ''', (admin_password_hash,))
        
        # Get admin user ID and admin role ID
        cursor.execute('SELECT id FROM users WHERE username = ?', ('admin',))
        admin_id = cursor.fetchone()[0]
        
        cursor.execute('SELECT id FROM roles WHERE name = ?', ('admin',))
        admin_role_id = cursor.fetchone()[0]
        
        # Assign admin role to admin user
        cursor.execute('''
        INSERT INTO user_roles (user_id, role_id) VALUES (?, ?)
        ''', (admin_id, admin_role_id))
        
        # Insert default subscription plans
        cursor.execute('''
        INSERT INTO subscriptions (name, price, duration_days, scrape_limit, description, is_active, currency, is_public, is_featured, allow_cancellation, features)
        VALUES
        ('Free Plan', 0.00, 30, 5, 'Basic plan with limited features', 1, 'USD', 1, 0, 1, 'export_excel,export_csv'),
        ('Premium Plan', 19.99, 30, 100, 'Advanced plan with all features', 1, 'USD', 1, 1, 1, 'export_excel,export_csv,bulk_scraping,api_access,priority_support,advanced_filters')
        ''')
        
        # Insert default site settings
        default_settings = [
            ('site_name', 'Email Scraper Pro', 'Name of the website'),
            ('site_description', 'Extract emails, phones, and social media from websites', 'Website description for SEO'),
            ('site_keywords', 'email scraper, email extractor, contact finder', 'Keywords for SEO'),
            ('contact_email', 'contact@example.com', 'Contact email address'),
            ('footer_text', '© 2025 Email Scraper Pro. All rights reserved.', 'Footer text'),
            ('maintenance_mode', '0', 'Maintenance mode (0=off, 1=on)')
        ]
        
        for setting in default_settings:
            cursor.execute('''
            INSERT INTO site_settings (key, value, category) VALUES (?, ?, ?)
            ''', (setting[0], setting[1], setting[2]))
        
        # Commit changes and close connection
        conn.commit()
        conn.close()
        
        print("✓ Database created successfully with all required tables and default data!")
        return True
    except Exception as e:
        print(f"✗ Error creating database: {e}")
        if 'conn' in locals() and conn:
            conn.close()
        return False

if __name__ == "__main__":
    if reset_database():
        print("\nDatabase reset and recreated successfully!")
        print("You can now run the application with: python run.py")
        print("Login with the default admin account - Username: admin, Password: admin123")
    else:
        print("\nFailed to reset and recreate database.")
        sys.exit(1) 