import requests

# Test server
try:
    r = requests.get('http://localhost:5000')
    print(f"Server: {r.status_code}")
except Exception as e:
    print(f"Server error: {e}")

# Test admin login and user creation
try:
    s = requests.Session()
    
    # Login as admin
    login_response = s.post('http://localhost:5000/admin', data={
        'identifier': 'admin@example.com',
        'password': 'admin123'
    })
    print(f"Admin login: {login_response.status_code}")
    
    # Test user creation page
    create_page = s.get('http://localhost:5000/admin/users/create')
    print(f"User create page: {create_page.status_code}")
    
    # Test user creation
    user_response = s.post('http://localhost:5000/admin/users/create', data={
        'username': 'testuser789',
        'email': 'testuser789@example.com',
        'password': 'testpass123',
        'first_name': 'Test',
        'last_name': 'User',
        'is_active': 'on'
    })
    print(f"User creation: {user_response.status_code}")
    
    # Test API credits
    credits_response = s.get('http://localhost:5000/api/user/credits')
    print(f"API credits: {credits_response.status_code}")
    
except Exception as e:
    print(f"Test error: {e}")

# Test public pages
pages = ['/page/about', '/page/contact', '/page/pricing']
for page in pages:
    try:
        r = requests.get(f'http://localhost:5000{page}')
        print(f"{page}: {r.status_code}")
    except Exception as e:
        print(f"{page} error: {e}")

print("Test completed!") 