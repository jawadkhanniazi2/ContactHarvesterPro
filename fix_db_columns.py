import os
import sys
import sqlite3

def fix_database_schema():
    """Add missing columns to the subscriptions table"""
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
                print(f"Added column {column['name']} to subscriptions table")
        
        # Commit changes
        conn.commit()
        
        # Verify columns have been added
        cursor.execute("PRAGMA table_info(subscriptions)")
        columns_after = [row[1] for row in cursor.fetchall()]
        
        print(f"Subscription table columns: {', '.join(columns_after)}")
        conn.close()
        
        return True
    except Exception as e:
        print(f"Error fixing database schema: {e}")
        if conn:
            conn.close()
        return False

if __name__ == "__main__":
    if fix_database_schema():
        print("Database schema updated successfully!")
    else:
        print("Failed to update database schema.")
        sys.exit(1) 