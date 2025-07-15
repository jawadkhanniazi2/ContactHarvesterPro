from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def index():
    return "Email Scraper is running! This is a test page."

@app.route('/test')
def test():
    return "Test route is working."

if __name__ == '__main__':
    app.run(debug=True) 