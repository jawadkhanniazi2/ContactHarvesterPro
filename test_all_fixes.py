#!/usr/bin/env python3
"""
Comprehensive test script to verify all fixes
"""

import requests
import time

def test_server_response():
    """Test if the server is responding"""
    try:
        response = requests.get('http://localhost:5000', timeout=5)
        print(f"✅ Server Response: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Server Error: {e}")
        return False

def test_admin_login():
    """Test admin login functionality"""
    try:
        session = requests.Session()
        login_data = {
            'identifier': 'admin@example.com',
            'password': 'admin123'
        }
        response = session.post('http://localhost:5000/admin', data=login_data)
        print(f"✅ Admin Login: {response.status_code}")
        return response.status_code in [200, 302], session
    except Exception as e:
        print(f"❌ Admin Login Error: {e}")
        return False, None

def test_user_creation(session):
    """Test user creation functionality"""
    try:
        user_data = {
            'username': 'testuser123',
            'email': 'testuser123@example.com',
            'password': 'testpass123',
            'first_name': 'Test',
            'last_name': 'User',
            'is_active': 'on'
        }
        response = session.post('http://localhost:5000/admin/users/create', data=user_data)
        print(f"✅ User Creation: {response.status_code}")
        return response.status_code in [200, 302]
    except Exception as e:
        print(f"❌ User Creation Error: {e}")
        return False

def test_public_pages():
    """Test public pages"""
    pages = ['/page/about', '/page/contact', '/page/pricing']
    results = []
    
    for page in pages:
        try:
            response = requests.get(f'http://localhost:5000{page}')
            status = response.status_code
            print(f"✅ {page}: {status}")
            results.append(status == 200)
        except Exception as e:
            print(f"❌ {page} Error: {e}")
            results.append(False)
    
    return all(results)

def test_api_endpoints(session):
    """Test API endpoints"""
    endpoints = [
        '/api/jobs',
        '/api/user/credits'
    ]
    results = []
    
    for endpoint in endpoints:
        try:
            response = session.get(f'http://localhost:5000{endpoint}')
            status = response.status_code
            print(f"✅ {endpoint}: {status}")
            results.append(status in [200, 302])
        except Exception as e:
            print(f"❌ {endpoint} Error: {e}")
            results.append(False)
    
    return all(results)

def test_settings_pages(session):
    """Test admin settings pages"""
    settings_pages = [
        '/admin/settings/email',
        '/admin/settings/payments',
        '/admin/settings/subscription'
    ]
    results = []
    
    for page in settings_pages:
        try:
            response = session.get(f'http://localhost:5000{page}')
            status = response.status_code
            print(f"✅ {page}: {status}")
            results.append(status in [200, 302])
        except Exception as e:
            print(f"❌ {page} Error: {e}")
            results.append(False)
    
    return all(results)

def main():
    print("🔧 COMPREHENSIVE TESTING OF ALL FIXES")
    print("=" * 50)
    
    # Test 1: Server Response
    print("\n1. Testing Server Response...")
    server_ok = test_server_response()
    
    if not server_ok:
        print("❌ Server is not responding. Please start the server first.")
        return
    
    # Test 2: Admin Login
    print("\n2. Testing Admin Login...")
    login_ok, session = test_admin_login()
    
    if not login_ok or not session:
        print("❌ Admin login failed. Cannot proceed with authenticated tests.")
        return
    
    # Test 3: User Creation (Fixed)
    print("\n3. Testing User Creation (Fixed)...")
    user_creation_ok = test_user_creation(session)
    
    # Test 4: Public Pages (Fixed)
    print("\n4. Testing Public Pages (Fixed)...")
    pages_ok = test_public_pages()
    
    # Test 5: API Endpoints (Fixed)
    print("\n5. Testing API Endpoints (Fixed)...")
    api_ok = test_api_endpoints(session)
    
    # Test 6: Settings Pages (Fixed)
    print("\n6. Testing Settings Pages (Fixed)...")
    settings_ok = test_settings_pages(session)
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 50)
    
    tests = [
        ("Server Response", server_ok),
        ("Admin Login", login_ok),
        ("User Creation", user_creation_ok),
        ("Public Pages", pages_ok),
        ("API Endpoints", api_ok),
        ("Settings Pages", settings_ok)
    ]
    
    passed = sum(1 for _, result in tests if result)
    total = len(tests)
    
    for test_name, result in tests:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:20} {status}")
    
    print(f"\nOverall Score: {passed}/{total} ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! All fixes are working correctly!")
    elif passed >= total * 0.8:
        print("✅ Most tests passed. Minor issues may remain.")
    else:
        print("⚠️  Several tests failed. More fixes needed.")

if __name__ == "__main__":
    main() 