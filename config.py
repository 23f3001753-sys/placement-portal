"""
config.py - Application Configuration
--------------------------------------
Centralises all Flask configuration settings.
Keeps sensitive keys and paths in one place for easy modification.
"""

import os

# Base directory of the project (same folder as this file)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Config:
    # ── Security ─────────────────────────────────────────────────────────────
    # IMPORTANT: Change this secret key before deploying to production
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'placement-portal-secret-key-2024'

    # ── Database ──────────────────────────────────────────────────────────────
    # SQLite database stored in the project root
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'placement_portal.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False  # Suppress unnecessary warnings

    # ── File Uploads ──────────────────────────────────────────────────────────
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024   # 5 MB maximum file upload size
    ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx'}
