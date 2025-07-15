from flask import Flask
from admin.settings_routes import settings_bp

app = Flask(__name__)
app.register_blueprint(settings_bp)

with app.test_request_context():
    # List all the settings route endpoints
    for rule in app.url_map.iter_rules():
        if rule.endpoint.startswith('settings.'):
            print(f"Endpoint: {rule.endpoint}, URL: {rule.rule}")
        
    # Specifically try the API settings route
    try:
        from flask import url_for
        print("\nTesting api_settings URL:")
        print(f"Route for settings.api_settings: {url_for('settings.api_settings')}")
    except Exception as e:
        print(f"Error generating URL for settings.api_settings: {e}")

    # Test the correct URL
    try:
        print("\nTesting other possible API settings URLs:")
        urls = [
            'settings.api',
            'settings.api_settings',
            'settings.update_api_settings'
        ]
        
        for url in urls:
            try:
                print(f"Route for {url}: {url_for(url)}")
            except Exception as e:
                print(f"Error generating URL for {url}: {e}")
    except Exception as e:
        print(f"Error during testing: {e}") 