# Contact Harvester Pro

A powerful web application for extracting email addresses, phone numbers, and social media profiles from websites. Built with Python, Selenium, and Flask.

## Features

- **Advanced Email Pattern Recognition**: Extract emails even from complex web structures
- **Phone Number Detection**: Identify phone numbers in various international formats
- **Social Media Profile Extraction**: Automatically find LinkedIn, Twitter, Facebook, Instagram, and other social profiles
- **Multi-threaded Processing**: Scan multiple websites concurrently for improved performance
- **Job Management**: Track progress and manage multiple scraping jobs
- **Modern UI**: Beautiful and intuitive user interface for a seamless experience
- **Export to Excel**: Download your results in a convenient Excel format

## Installation

### Prerequisites

- Python 3.8 or higher
- Chrome browser (for Selenium WebDriver)

### Setup

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/contact-harvester-pro.git
   cd contact-harvester-pro
   ```

2. Create and activate a virtual environment (optional but recommended):
   ```
   python -m venv venv
   # On Windows
   venv\Scripts\activate
   # On macOS/Linux
   source venv/bin/activate
   ```

3. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

4. Create necessary directories:
   ```
   mkdir -p uploads results
   ```

## Usage

1. Start the application:
   ```
   python app.py
   ```

2. Open your browser and navigate to:
   ```
   http://localhost:5000
   ```

3. Use the application:
   - Upload a CSV, Excel, or TXT file containing URLs (one URL per line)
   - Or manually enter URLs in the text area
   - Start the scraping process
   - Monitor progress and download results when completed

## Project Structure

```
contact-harvester-pro/
│
├── app.py              # Flask application
├── scraper.py          # Contact scraping logic
├── requirements.txt    # Python dependencies
│
├── static/             # Static assets
│   ├── css/            # CSS stylesheets
│   ├── js/             # JavaScript files
│   └── img/            # Images
│
├── templates/          # HTML templates
│   └── index.html      # Main application template
│
├── uploads/            # Temporary storage for uploaded files
└── results/            # Storage for generated results
```

## API Endpoints

The application provides the following API endpoints:

- `POST /api/upload`: Upload a file containing URLs
- `POST /api/manual`: Submit URLs manually
- `GET /api/jobs`: Get all job statuses
- `GET /api/jobs/<job_id>`: Get status of a specific job
- `GET /api/download/<job_id>`: Download completed job results

## Configuration

You can configure the application by modifying the following settings in `app.py`:

- `MAX_CONTENT_LENGTH`: Maximum file upload size (default: 10MB)
- `MAX_URLS_PER_BATCH`: Maximum number of URLs per batch (default: 100)

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- [Flask](https://flask.palletsprojects.com/) - Web framework
- [Selenium](https://www.selenium.dev/) - Browser automation
- [Bootstrap](https://getbootstrap.com/) - Frontend framework
- [Font Awesome](https://fontawesome.com/) - Icons

## Contact

For questions or support, please open an issue on GitHub or contact the author.

## Deployment

This application can be deployed to various free hosting platforms. Here are instructions for two popular options:

### Render.com (Free Tier)

1. Create a [Render.com](https://render.com) account
2. Create a new web service by connecting your GitHub repository
3. Select "Python" as the environment
4. Set the build command: `pip install -r requirements.txt`
5. Set the start command: `gunicorn app:app`
6. Select the free plan
7. Click "Create Web Service"

### PythonAnywhere (Free Tier)

1. Create a [PythonAnywhere](https://www.pythonanywhere.com/) account
2. Go to the Web tab and create a new web app
3. Choose "Flask" and select the latest Python version
4. Upload your project files to your PythonAnywhere account
5. Set up a virtual environment with your dependencies:
   ```
   mkvirtualenv --python=python3.9 myenv
   pip install -r requirements.txt
   ```
6. Configure your WSGI file to import your app correctly
7. Click "Reload" to start your application

Note: Free tiers have limitations such as sleep periods after inactivity (Render) or daily CPU quotas (PythonAnywhere). 