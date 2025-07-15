#!/usr/bin/env python
"""Test script to check user blueprint registration"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    print("Testing user blueprint import...")
    from user import user_bp
    print(f"✓ User blueprint imported successfully: {user_bp}")
    print(f"✓ Blueprint name: {user_bp.name}")
    print(f"✓ URL prefix: {user_bp.url_prefix}")
    
    print("\nTesting app import...")
    from app import app
    print("✓ App imported successfully")
    
    print("\nChecking registered blueprints...")
    for name, bp in app.blueprints.items():
        print(f"  - {name}: {bp}")
    
    print("\nChecking URL rules...")
    user_routes = []
    for rule in app.url_map.iter_rules():
        if 'user' in rule.rule:
            user_routes.append(f"{rule.rule} -> {rule.endpoint}")
    
    if user_routes:
        print("✓ User routes found:")
        for route in user_routes:
            print(f"  - {route}")
    else:
        print("✗ No user routes found!")
    
    # Test URL generation
    print("\nTesting URL generation...")
    with app.app_context():
        try:
            from flask import url_for
            dashboard_url = url_for('user.dashboard')
            print(f"✓ user.dashboard URL: {dashboard_url}")
        except Exception as e:
            print(f"✗ Error generating user.dashboard URL: {e}")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc() 