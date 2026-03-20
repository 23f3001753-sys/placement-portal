# Placement Portal Application

A web-based Placement Portal built using Flask, SQLAlchemy, Jinja2, and SQLite.

## Project Overview
This application helps manage campus placement activities digitally. It supports three main roles:
- Admin
- Student
- Company

## Features
### Admin
- Login as default admin
- Approve/reject company registrations
- Activate/deactivate users
- Blacklist companies
- View placement drives and applications

### Student
- Register and login
- Create/update profile
- View approved placement drives
- Apply for drives
- Track application status

### Company
- Register and login
- Create/update company profile
- Create placement drives
- View applicants for their drives

## Tech Stack
- Backend: Flask
- ORM: SQLAlchemy
- Frontend: HTML, CSS, Jinja2
- Database: SQLite
- Authentication: Flask-Login

## Folder Structure
- `app.py` → Flask routes and app logic
- `models.py` → Database models
- `templates/` → Jinja2 HTML templates
- `static/` → CSS, JS, images
- `requirements.txt` → Python dependencies
- `README.md` → Project documentation

## Installation
1. Clone the repository
2. Create virtual environment
3. Install dependencies:
   pip install -r requirements.txt

## Run the Project
python app.py

## Default Admin Credentials
- Email: admin@example.com
- Password: admin123

## Database
- SQLite database is used for local development.

## Notes
- The database may be auto-created on first run using `db.create_all()`.
- If schema changes are made without migrations, delete the old `.db` file and restart the app.

## Future Improvements
- Add REST API endpoints
- Add Flask-Migrate for database migrations
- Add email notifications
- Add advanced filtering and analytics
