"""
models.py - Database Models (SQLAlchemy)
-----------------------------------------
Defines all database tables using SQLAlchemy ORM.
Tables are created automatically on first run - NO manual DB setup needed.

Models:
    User            -> Stores all users (admin / company / student)
    CompanyProfile  -> Company-specific details linked to User
    StudentProfile  -> Student-specific details linked to User
    PlacementDrive  -> Job drives created by companies
    Application     -> Student applications for drives
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

# SQLAlchemy instance — initialised in app.py via db.init_app(app)
db = SQLAlchemy()


# ─── User Model ───────────────────────────────────────────────────────────────

class User(UserMixin, db.Model):
    """
    Central user table for all three roles: admin, company, student.
    flask_login uses this model for session management.
    is_active is used to blacklist users — Flask-Login checks this automatically.
    """
    __tablename__ = 'users'

    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(100), nullable=False)
    email       = db.Column(db.String(120), unique=True, nullable=False)
    password    = db.Column(db.String(200), nullable=False)   # Stored as hash
    role        = db.Column(db.String(20), nullable=False)    # admin / company / student
    is_active   = db.Column(db.Boolean, default=True)         # False = blacklisted
    is_approved = db.Column(db.Boolean, default=False)        # Admin must approve

    # One-to-one relationships
    company_profile = db.relationship('CompanyProfile', backref='user',
                                      uselist=False, cascade='all, delete-orphan')
    student_profile = db.relationship('StudentProfile', backref='user',
                                      uselist=False, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<User {self.email} [{self.role}]>'


# ─── Company Profile Model ────────────────────────────────────────────────────

class CompanyProfile(db.Model):
    """
    Stores company-specific details.
    approval_status is separate from User.is_approved to track pending/rejected states.
    """
    __tablename__ = 'company_profiles'

    id              = db.Column(db.Integer, primary_key=True)
    user_id         = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    company_name    = db.Column(db.String(200), nullable=False)
    hr_contact      = db.Column(db.String(100))
    website         = db.Column(db.String(200))
    approval_status = db.Column(db.String(20), default='Pending')  # Pending / Approved / Rejected

    # One company can have many placement drives
    drives = db.relationship('PlacementDrive', backref='company',
                             lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<CompanyProfile {self.company_name}>'


# ─── Student Profile Model ────────────────────────────────────────────────────

class StudentProfile(db.Model):
    """
    Stores student-specific academic and contact details.
    resume_filename stores only the filename (not full path) for security.
    """
    __tablename__ = 'student_profiles'

    id              = db.Column(db.Integer, primary_key=True)
    user_id         = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    resume_filename = db.Column(db.String(200), nullable=True)  # Uploaded resume file
    course          = db.Column(db.String(100))
    cgpa            = db.Column(db.Float)
    contact_number  = db.Column(db.String(15))

    # One student can have many applications
    applications = db.relationship('Application', backref='student',
                                   lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<StudentProfile user_id={self.user_id}>'


# ─── Placement Drive Model ────────────────────────────────────────────────────

class PlacementDrive(db.Model):
    """
    Represents a job drive created by a company.
    Status flow: Pending -> Approved (by admin) -> Closed (by company)
    Only Approved drives are visible to students.
    """
    __tablename__ = 'placement_drives'

    id              = db.Column(db.Integer, primary_key=True)
    company_id      = db.Column(db.Integer, db.ForeignKey('company_profiles.id'), nullable=False)
    job_title       = db.Column(db.String(200), nullable=False)
    job_description = db.Column(db.Text)
    eligibility     = db.Column(db.String(300))
    deadline        = db.Column(db.Date)
    status          = db.Column(db.String(20), default='Pending')  # Pending / Approved / Closed / Rejected
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)

    # One drive can have many applications
    applications = db.relationship('Application', backref='drive',
                                   lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<PlacementDrive {self.job_title}>'


# ─── Application Model ────────────────────────────────────────────────────────

class Application(db.Model):
    """
    Links a student to a placement drive.
    UniqueConstraint prevents the same student from applying twice to the same drive.
    Status flow: Applied -> Shortlisted -> Selected / Rejected
    """
    __tablename__ = 'applications'

    id               = db.Column(db.Integer, primary_key=True)
    student_id       = db.Column(db.Integer, db.ForeignKey('student_profiles.id'), nullable=False)
    drive_id         = db.Column(db.Integer, db.ForeignKey('placement_drives.id'), nullable=False)
    application_date = db.Column(db.DateTime, default=datetime.utcnow)
    status           = db.Column(db.String(20), default='Applied')  # Applied/Shortlisted/Selected/Rejected

    # Composite unique constraint: one student can apply to each drive only once
    __table_args__ = (
        db.UniqueConstraint('student_id', 'drive_id', name='unique_student_drive'),
    )

    def __repr__(self):
        return f'<Application student={self.student_id} drive={self.drive_id}>'
