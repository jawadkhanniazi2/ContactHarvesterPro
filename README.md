# Email Scraper Admin Dashboard

A comprehensive tool for scraping email addresses from websites with a full-featured admin dashboard.

## Features

- Email extraction from websites
- User authentication system
- Role-based access control
- Admin dashboard for user management
- Blog content management
- Settings management
- Activity logging
- API key management
- Subscription plans

## Installation

1. Clone the repository
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Set up environment variables in `.env` file or update the existing one

## Running the Application

Run the application using the included run script:

```bash
python run.py
```

This will:
- Set up all required directories
- Create the database if it doesn't exist
- Start the Flask development server

## Accessing the Admin Dashboard

1. Navigate to `http://localhost:5000/login` in your browser
2. Use the default admin credentials:
   - Email: `admin@example.com`
   - Password: `admin123`

After successful login, you'll be redirected to the admin dashboard.

## Troubleshooting

If you encounter dependency issues:

1. Make sure you have installed all dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. For specific package versions:
   - This application requires pandas 2.2.3 and Pillow 11.2.1
   - Make sure these are correctly installed:
     ```bash
     pip install pandas==2.2.3 pillow==11.2.1
     ```

3. If there are database errors, try removing the existing database file and restart:
   ```bash
   rm contact_harvester.db
   python run.py
   ```

## Project Structure

- `app.py`: Main application file
- `models.py`: Database models
- `auth.py`: Authentication system
- `utils.py`: Utility functions
- `scraper.py`: Email scraping functionality
- `admin/`: Admin dashboard routes
- `templates/`: HTML templates
- `static/`: Static files (CSS, JS, images)

## Adding New Users

New users can register themselves, or an admin can create users through the admin dashboard.
