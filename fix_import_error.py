import os
import sys
import re

def fix_import_error():
    """Fix the UserSubscription import error"""
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
            
            print(f"Fixed UserSubscription import in {settings_routes_file}")
            return True
    
    # If we reach here, no fix was necessary
    print("No import error found.")
    return False

if __name__ == "__main__":
    fixed = fix_import_error()
    
    if fixed:
        print("Import error fixed successfully!")
    else:
        print("No fixes were necessary.") 