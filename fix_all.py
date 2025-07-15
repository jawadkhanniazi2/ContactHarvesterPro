import os
import sys
import re
import sqlite3
from datetime import datetime

# Fix 1: Check for missing UserSubscription import error
def fix_import_error():
    """Fix the UserSubscription import error"""
    print("Step 1: Fixing import errors...")
    
    # Target files
    settings_routes_file = 'admin/settings_routes.py'
    
    if os.path.exists(settings_routes_file):
        # Read the file
        with open(settings_routes_file, 'r') as f:
            content = f.read()
        
        # Check if UserSubscription is imported
        if 'UserSubscription' in content:
            # Find import lines
            import_lines = re.findall(r'from models import.*', content)
            
            # Remove UserSubscription from imports
            for line in import_lines:
                if 'UserSubscription' in line:
                    new_line = line.replace(', UserSubscription', '').replace('UserSubscription, ', '')
                    content = content.replace(line, new_line)
            
            # Write the fixed content back
            with open(settings_routes_file, 'w') as f:
                f.write(content)
            
            print(f"✓ Fixed UserSubscription import in {settings_routes_file}")
            return True
    
    # If we reach here, no fix was necessary
    print("✓ No import errors found.")
    return True

# Fix 2: Add missing columns to Subscription table
def fix_database_schema():
    """Add missing columns to the subscriptions table"""
    print("\nStep 2: Fixing database schema...")
    
    # Database path
    db_path = 'contact_harvester.db'
    
    if not os.path.exists(db_path):
        print(f"Database file {db_path} not found.")
        return False
    
    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get existing columns
        cursor.execute("PRAGMA table_info(subscriptions)")
        columns = [row[1] for row in cursor.fetchall()]
        
        # Define required columns with default values
        required_columns = [
            {"name": "currency", "type": "VARCHAR(10)", "default": "'USD'"},
            {"name": "is_public", "type": "BOOLEAN", "default": "1"},
            {"name": "is_featured", "type": "BOOLEAN", "default": "0"},
            {"name": "allow_cancellation", "type": "BOOLEAN", "default": "1"},
            {"name": "stripe_plan_id", "type": "VARCHAR(100)", "default": "NULL"},
            {"name": "features", "type": "TEXT", "default": "NULL"}
        ]
        
        # Add missing columns
        for column in required_columns:
            if column["name"] not in columns:
                sql = f"ALTER TABLE subscriptions ADD COLUMN {column['name']} {column['type']} DEFAULT {column['default']}"
                cursor.execute(sql)
                print(f"✓ Added column {column['name']} to subscriptions table")
        
        # Commit changes
        conn.commit()
        
        # Verify columns have been added
        cursor.execute("PRAGMA table_info(subscriptions)")
        columns_after = [row[1] for row in cursor.fetchall()]
        
        print(f"✓ Subscription table columns: {', '.join(columns_after)}")
        conn.close()
        
        return True
    except Exception as e:
        print(f"✗ Error fixing database schema: {e}")
        if 'conn' in locals() and conn:
            conn.close()
        return False

# Fix 3: Check and create the pending_comments_count template variable
def fix_context_processor():
    """Add a context processor for pending_comments_count if not present"""
    print("\nStep 3: Checking for context processor...")
    
    app_file = 'app.py'
    context_processor_function = "def utility_processor():"
    pending_comments_code = "pending_comments_count"
    
    try:
        if os.path.exists(app_file):
            with open(app_file, 'r') as f:
                content = f.read()
            
            # Check if context processor already exists
            if context_processor_function in content and pending_comments_code in content:
                print("✓ Context processor for pending_comments_count already exists.")
                return True
            
            # Find a good insertion point - just before if __name__ == '__main__':
            insertion_point = content.find("if __name__ == '__main__':")
            
            if insertion_point != -1:
                # Prepare the code to insert
                code_to_insert = """
# Template context processor to add common variables to all templates
@app.context_processor
def utility_processor():
    def get_pending_comments_count():
        try:
            # Try to import BlogComment if it exists
            from models import BlogComment
            return BlogComment.query.filter_by(approved=False).count()
        except (ImportError, AttributeError):
            # If the class doesn't exist or table doesn't exist yet
            return 0
            
    return {
        'pending_comments_count': get_pending_comments_count()
    }
"""
                # Insert the code
                new_content = content[:insertion_point] + code_to_insert + "\n" + content[insertion_point:]
                
                # Write the updated content back
                with open(app_file, 'w') as f:
                    f.write(new_content)
                
                print("✓ Added context processor for pending_comments_count.")
                return True
        
        print("✗ Could not find appropriate place to add context processor.")
        return False
    except Exception as e:
        print(f"✗ Error adding context processor: {e}")
        return False

# Fix 4: Ensure the template handles undefined variables
def fix_template():
    """Update template to handle undefined variables"""
    print("\nStep 4: Fixing template references...")
    
    template_file = 'templates/admin/layout.html'
    
    try:
        if os.path.exists(template_file):
            with open(template_file, 'r') as f:
                content = f.read()
            
            # Look for pending_comments_count references
            if "pending_comments_count > 0" in content and "pending_comments_count is defined" not in content:
                # Replace with safer version
                content = content.replace("{% if pending_comments_count > 0 %}", 
                                          "{% if pending_comments_count is defined and pending_comments_count > 0 %}")
                
                # Write back to file
                with open(template_file, 'w') as f:
                    f.write(content)
                
                print(f"✓ Fixed template reference in {template_file}")
                return True
            else:
                print(f"✓ No template fixes needed in {template_file}")
                return True
        
        print(f"✗ Template file {template_file} not found.")
        return False
    except Exception as e:
        print(f"✗ Error fixing template: {e}")
        return False

# Run all fixes
def run_all_fixes():
    print("======================================================")
    print("Running fixes for admin dashboard issues...")
    print("======================================================")
    
    # Run all fixes
    import_fixed = fix_import_error()
    schema_fixed = fix_database_schema()
    context_fixed = fix_context_processor()
    template_fixed = fix_template()
    
    # Check if all fixes were successful
    if import_fixed and schema_fixed and context_fixed and template_fixed:
        print("\n✓ All fixes completed successfully!")
        print("You can now run the application with: python run.py")
        return 0
    else:
        print("\n✗ Some fixes failed. Please check the errors above.")
        return 1

# Run the fixes if executed directly
if __name__ == "__main__":
    sys.exit(run_all_fixes()) 