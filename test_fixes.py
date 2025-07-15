#!/usr/bin/env python3
"""
Test script to verify that the main issues have been fixed
"""

import requests
import time
import sys

def test_server_response():
    """Test if the server is responding"""
    try:
        response = requests.get('http://localhost:5000', timeout=5)
        print(f"✅ Server is responding with status code: {response.status_code}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ Server is not responding: {e}")
        return False

def test_admin_login():
    """Test admin login functionality"""
    try:
        session = requests.Session()
        
        # Get login page
        login_page = session.get('http://localhost:5000/admin')
        if login_page.status_code != 200:
            print(f"❌ Admin login page not accessible: {login_page.status_code}")
            return False
        
        # Try to login
        login_data = {
            'email': 'admin@example.com',
            'password': 'admin123'
        }
        
        login_response = session.post('http://localhost:5000/admin', data=login_data)
        if login_response.status_code in [200, 302]:  # Success or redirect
            print("✅ Admin login is working")
            return True
        else:
            print(f"❌ Admin login failed: {login_response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Admin login test failed: {e}")
        return False

def test_admin_dashboard():
    """Test admin dashboard access"""
    try:
        session = requests.Session()
        
        # Login first
        login_data = {
            'email': 'admin@example.com',
            'password': 'admin123'
        }
        session.post('http://localhost:5000/admin', data=login_data)
        
        # Access dashboard
        dashboard_response = session.get('http://localhost:5000/admin/')
        if dashboard_response.status_code == 200:
            print("✅ Admin dashboard is accessible")
            return True
        else:
            print(f"❌ Admin dashboard failed: {dashboard_response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Admin dashboard test failed: {e}")
        return False

def test_settings_pages():
    """Test settings pages that were previously failing"""
    try:
        session = requests.Session()
        
        # Login first
        login_data = {
            'email': 'admin@example.com',
            'password': 'admin123'
        }
        session.post('http://localhost:5000/admin', data=login_data)
        
        settings_pages = [
            '/admin/settings/email',
            '/admin/settings/payments',
            '/admin/settings/subscription'
        ]
        
        results = []
        for page in settings_pages:
            try:
                response = session.get(f'http://localhost:5000{page}')
                if response.status_code == 200:
                    print(f"✅ {page} is working")
                    results.append(True)
                else:
                    print(f"❌ {page} failed: {response.status_code}")
                    results.append(False)
            except Exception as e:
                print(f"❌ {page} error: {e}")
                results.append(False)
        
        return all(results)
        
    except Exception as e:
        print(f"❌ Settings pages test failed: {e}")
        return False

def test_public_pages():
    """Test public pages that were previously 404"""
    try:
        pages = [
            '/page/about',
            '/page/contact', 
            '/page/pricing'
        ]
        
        results = []
        for page in pages:
            try:
                response = requests.get(f'http://localhost:5000{page}')
                if response.status_code == 200:
                    print(f"✅ {page} is working")
                    results.append(True)
                else:
                    print(f"❌ {page} failed: {response.status_code}")
                    results.append(False)
            except Exception as e:
                print(f"❌ {page} error: {e}")
                results.append(False)
        
        return all(results)
        
    except Exception as e:
        print(f"❌ Public pages test failed: {e}")
        return False

def test_api_endpoints():
    """Test API endpoints"""
    try:
        session = requests.Session()
        
        # Login first
        login_data = {
            'email': 'admin@example.com',
            'password': 'admin123'
        }
        session.post('http://localhost:5000/admin', data=login_data)
        
        api_endpoints = [
            '/api/jobs',
            '/api/user/credits'
        ]
        
        results = []
        for endpoint in api_endpoints:
            try:
                response = session.get(f'http://localhost:5000{endpoint}')
                if response.status_code == 200:
                    print(f"✅ {endpoint} is working")
                    results.append(True)
                else:
                    print(f"❌ {endpoint} failed: {response.status_code}")
                    results.append(False)
            except Exception as e:
                print(f"❌ {endpoint} error: {e}")
                results.append(False)
        
        return all(results)
        
    except Exception as e:
        print(f"❌ API endpoints test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing Email Scraper Application Fixes")
    print("=" * 50)
    
    # Wait for server to start
    print("⏳ Waiting for server to start...")
    time.sleep(3)
    
    tests = [
        ("Server Response", test_server_response),
        ("Admin Login", test_admin_login),
        ("Admin Dashboard", test_admin_dashboard),
        ("Settings Pages", test_settings_pages),
        ("Public Pages", test_public_pages),
        ("API Endpoints", test_api_endpoints)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n🔍 Testing {test_name}...")
        result = test_func()
        results.append(result)
    
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(results)
    total = len(results)
    
    for i, (test_name, _) in enumerate(tests):
        status = "✅ PASS" if results[i] else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed ({(passed/total)*100:.1f}%)")
    
    if passed == total:
        print("🎉 All tests passed! The fixes are working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 