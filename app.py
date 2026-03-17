"""
================================================================================
  PLACEMENT PORTAL - Flask Web Application
================================================================================

  SETUP INSTRUCTIONS (run these commands in your terminal):
  ---------------------------------------------------------
  1. Create a virtual environment:
       python -m venv venv

  2. Activate the virtual environment:
       Windows :  venv\Scripts\activate
       Mac/Linux: source venv/bin/activate

  3. Install all required packages:
       pip install -r requirements.txt

  4. Run the application:
       python app.py

  5. Open in browser:
       http://127.0.0.1:5000

  DEFAULT ADMIN CREDENTIALS:
  --------------------------
    Email   : admin@portal.com
    Password: admin123

  NOTE: The SQLite database is created automatically on first run.
        No manual database setup is needed.
================================================================================
"""

import os
from datetime import datetime, date

from flask import (Flask, render_template, redirect, url_for,
                   request, flash, abort)
from flask_login import (LoginManager, login_user, logout_user,
                          login_required, current_user)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from config import Config
from models import db, User, CompanyProfile, StudentProfile, PlacementDrive, Application


# ─── Application Factory ──────────────────────────────────────────────────────

app = Flask(__name__)
app.config.from_object(Config)   # Load settings from config.py

# ─── Extension Initialisation ─────────────────────────────────────────────────

db.init_app(app)   # Bind SQLAlchemy to this app

login_manager = LoginManager(app)
login_manager.login_view = 'login'               # Redirect here if not logged in
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'warning'


# ─── Flask-Login: User Loader ─────────────────────────────────────────────────

@login_manager.user_loader
def load_user(user_id):
    """
    Required by Flask-Login.
    Loads a user from the DB using the ID stored in the session cookie.
    """
    return User.query.get(int(user_id))


# ─── Context Processor ────────────────────────────────────────────────────────

@app.context_processor
def inject_globals():
    """Inject variables available in ALL templates automatically."""
    return {'now': datetime.utcnow()}


# ─── Helper Functions ─────────────────────────────────────────────────────────

def allowed_file(filename):
    """Return True if the uploaded file has an allowed extension."""
    return ('.' in filename and
            filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS'])


def create_default_admin():
    """
    Create the default admin account on first startup.
    Skips creation if admin already exists (safe to call on every startup).
    """
    if not User.query.filter_by(email='admin@portal.com').first():
        admin = User(
            name='Admin',
            email='admin@portal.com',
            password=generate_password_hash('admin123'),
            role='admin',
            is_active=True,
            is_approved=True
        )
        db.session.add(admin)
        db.session.commit()
        print('✅  Default admin created  →  admin@portal.com / admin123')


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN ROUTES
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    """Root URL: redirect to appropriate dashboard based on role."""
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif current_user.role == 'company':
            return redirect(url_for('company_dashboard'))
        elif current_user.role == 'student':
            return redirect(url_for('student_dashboard'))
    return redirect(url_for('login'))


# ─── Authentication Routes ────────────────────────────────────────────────────

@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Login page for all roles (admin, company, student).
    Validates credentials and enforces approval checks.
    """
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        user = User.query.filter_by(email=email).first()

        # Step 1: Verify email and password
        if not user or not check_password_hash(user.password, password):
            flash('Invalid email or password. Please try again.', 'danger')
            return render_template('login.html')

        # Step 2: Check if account is active (not blacklisted)
        if not user.is_active:
            flash('Your account has been blacklisted. Contact the administrator.', 'danger')
            return render_template('login.html')

        # Step 3: Company-specific check — must be approved by admin
        if user.role == 'company':
            profile = CompanyProfile.query.filter_by(user_id=user.id).first()
            if not profile or profile.approval_status != 'Approved':
                flash('Your company account is pending admin approval.', 'warning')
                return render_template('login.html')

        # All checks passed — log the user in
        login_user(user)
        flash(f'Welcome back, {user.name}!', 'success')

        # Redirect to the page they originally tried to access, or index
        next_page = request.args.get('next')
        return redirect(next_page or url_for('index'))

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    """Log out the current user and redirect to login page."""
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('login'))


# ─── Registration Routes ──────────────────────────────────────────────────────

@app.route('/register/student', methods=['GET', 'POST'])
def register_student():
    """
    Student registration.
    Creates both a User record and a StudentProfile record.
    Students are auto-approved for simplicity.
    """
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        name    = request.form.get('name', '').strip()
        email   = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        course  = request.form.get('course', '').strip()
        cgpa_str = request.form.get('cgpa', '').strip()
        contact = request.form.get('contact_number', '').strip()

        # Validate: email must be unique
        if User.query.filter_by(email=email).first():
            flash('An account with this email already exists.', 'danger')
            return render_template('register_student.html')

        # Validate: CGPA must be a valid float between 0 and 10
        try:
            cgpa = float(cgpa_str)
            if not (0.0 <= cgpa <= 10.0):
                raise ValueError
        except (ValueError, TypeError):
            flash('CGPA must be a number between 0.0 and 10.0.', 'danger')
            return render_template('register_student.html')

        # Create User record
        new_user = User(
            name=name,
            email=email,
            password=generate_password_hash(password),
            role='student',
            is_active=True,
            is_approved=True   # Students are auto-approved
        )
        db.session.add(new_user)
        db.session.flush()     # Flush to get new_user.id before committing

        # Create linked StudentProfile
        profile = StudentProfile(
            user_id=new_user.id,
            course=course,
            cgpa=cgpa,
            contact_number=contact
        )
        db.session.add(profile)
        db.session.commit()

        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register_student.html')


@app.route('/register/company', methods=['GET', 'POST'])
def register_company():
    """
    Company registration.
    Creates a User and CompanyProfile; awaits admin approval before login is allowed.
    """
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        name         = request.form.get('name', '').strip()
        email        = request.form.get('email', '').strip().lower()
        password     = request.form.get('password', '')
        company_name = request.form.get('company_name', '').strip()
        hr_contact   = request.form.get('hr_contact', '').strip()
        website      = request.form.get('website', '').strip()

        # Validate: email must be unique
        if User.query.filter_by(email=email).first():
            flash('An account with this email already exists.', 'danger')
            return render_template('register_company.html')

        # Create User record (not approved by default)
        new_user = User(
            name=name,
            email=email,
            password=generate_password_hash(password),
            role='company',
            is_active=True,
            is_approved=False  # Admin must approve before company can log in
        )
        db.session.add(new_user)
        db.session.flush()

        # Create linked CompanyProfile
        profile = CompanyProfile(
            user_id=new_user.id,
            company_name=company_name,
            hr_contact=hr_contact,
            website=website,
            approval_status='Pending'
        )
        db.session.add(profile)
        db.session.commit()

        flash('Registration submitted! Please wait for admin approval before logging in.', 'success')
        return redirect(url_for('login'))

    return render_template('register_company.html')


# ─────────────────────────────────────────────────────────────────────────────
#  ADMIN ROUTES
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    """
    Admin dashboard.
    Shows platform statistics, manages companies, students, and drives.
    Supports search for students and companies via query parameters.
    """
    if current_user.role != 'admin':
        flash('Access denied. Admins only.', 'danger')
        return redirect(url_for('index'))

    # ── Platform Statistics ──────────────────────────────────────────────────
    stats = {
        'total_students'    : User.query.filter_by(role='student').count(),
        'total_companies'   : User.query.filter_by(role='company').count(),
        'total_drives'      : PlacementDrive.query.count(),
        'total_applications': Application.query.count(),
    }

    # ── Search Parameters ────────────────────────────────────────────────────
    search_student = request.args.get('search_student', '').strip()
    search_company = request.args.get('search_company', '').strip()

    # ── Students (with optional search) ─────────────────────────────────────
    students_query = User.query.filter_by(role='student')
    if search_student:
        students_query = students_query.filter(
            (User.name.ilike(f'%{search_student}%')) |
            (User.email.ilike(f'%{search_student}%'))
        )
    students = students_query.order_by(User.name).all()

    # ── Companies (with optional search by company name) ─────────────────────
    all_company_users = User.query.filter_by(role='company').all()
    if search_company:
        # Filter in Python using the relationship (simpler for viva)
        companies = [
            u for u in all_company_users
            if u.company_profile and
               search_company.lower() in u.company_profile.company_name.lower()
        ]
    else:
        companies = all_company_users

    # ── Pending Drives (awaiting admin approval) ─────────────────────────────
    pending_drives = PlacementDrive.query.filter_by(status='Pending').all()

    return render_template(
        'admin_dashboard.html',
        stats=stats,
        students=students,
        companies=companies,
        pending_drives=pending_drives,
        search_student=search_student,
        search_company=search_company
    )


@app.route('/admin/approve_company/<int:user_id>')
@login_required
def approve_company(user_id):
    """Approve a company account so it can log in and post drives."""
    if current_user.role != 'admin':
        abort(403)

    company_user    = User.query.get_or_404(user_id)
    company_profile = CompanyProfile.query.filter_by(user_id=user_id).first()

    company_user.is_approved = True
    if company_profile:
        company_profile.approval_status = 'Approved'

    db.session.commit()
    flash(f'Company "{company_profile.company_name}" has been approved.', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/reject_company/<int:user_id>')
@login_required
def reject_company(user_id):
    """Reject a company account."""
    if current_user.role != 'admin':
        abort(403)

    company_profile = CompanyProfile.query.filter_by(user_id=user_id).first()
    if company_profile:
        company_profile.approval_status = 'Rejected'
        db.session.commit()
        flash(f'Company "{company_profile.company_name}" has been rejected.', 'warning')
    else:
        flash('Company profile not found.', 'danger')

    return redirect(url_for('admin_dashboard'))


@app.route('/admin/approve_drive/<int:drive_id>')
@login_required
def approve_drive(drive_id):
    """Approve a placement drive so students can see and apply to it."""
    if current_user.role != 'admin':
        abort(403)

    drive = PlacementDrive.query.get_or_404(drive_id)
    drive.status = 'Approved'
    db.session.commit()
    flash(f'Drive "{drive.job_title}" has been approved.', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/reject_drive/<int:drive_id>')
@login_required
def reject_drive(drive_id):
    """Reject a placement drive."""
    if current_user.role != 'admin':
        abort(403)

    drive = PlacementDrive.query.get_or_404(drive_id)
    drive.status = 'Rejected'
    db.session.commit()
    flash(f'Drive "{drive.job_title}" has been rejected.', 'warning')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/blacklist/<int:user_id>')
@login_required
def blacklist_user(user_id):
    """
    Toggle blacklist status of any user (student or company).
    A blacklisted user cannot log in.
    Admin cannot blacklist themselves.
    """
    if current_user.role != 'admin':
        abort(403)

    if user_id == current_user.id:
        flash('You cannot blacklist your own account.', 'danger')
        return redirect(url_for('admin_dashboard'))

    user = User.query.get_or_404(user_id)
    user.is_active = not user.is_active   # Toggle active status
    db.session.commit()

    status = 'reactivated' if user.is_active else 'blacklisted'
    flash(f'User "{user.name}" has been {status}.', 'info')
    return redirect(url_for('admin_dashboard'))


# ─────────────────────────────────────────────────────────────────────────────
#  COMPANY ROUTES
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/company/dashboard')
@login_required
def company_dashboard():
    """
    Company dashboard.
    Displays the company's profile and all drives they have created,
    along with the applicant count per drive.
    """
    if current_user.role != 'company':
        flash('Access denied. Companies only.', 'danger')
        return redirect(url_for('index'))

    company = CompanyProfile.query.filter_by(user_id=current_user.id).first()
    if not company:
        flash('Company profile not found. Please contact admin.', 'danger')
        return redirect(url_for('login'))

    # Fetch all drives for this company, newest first
    drives = PlacementDrive.query.filter_by(company_id=company.id)\
                                 .order_by(PlacementDrive.created_at.desc()).all()

    # Build list of (drive, applicant_count) tuples for the template
    drive_data = []
    for drive in drives:
        applicant_count = Application.query.filter_by(drive_id=drive.id).count()
        drive_data.append({'drive': drive, 'applicant_count': applicant_count})

    return render_template('company_dashboard.html',
                           company=company,
                           drive_data=drive_data)


@app.route('/company/drive/create', methods=['GET', 'POST'])
@login_required
def create_drive():
    """
    Create a new placement drive.
    Newly created drives have Pending status until admin approves them.
    """
    if current_user.role != 'company':
        abort(403)

    company = CompanyProfile.query.filter_by(user_id=current_user.id).first()

    if request.method == 'POST':
        job_title       = request.form.get('job_title', '').strip()
        job_description = request.form.get('job_description', '').strip()
        eligibility     = request.form.get('eligibility', '').strip()
        deadline_str    = request.form.get('deadline', '').strip()

        # Validate and parse deadline date
        try:
            deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Please enter a valid deadline date.', 'danger')
            return render_template('drives.html', company=company, action='create')

        new_drive = PlacementDrive(
            company_id=company.id,
            job_title=job_title,
            job_description=job_description,
            eligibility=eligibility,
            deadline=deadline,
            status='Pending'   # Requires admin approval before students can see it
        )
        db.session.add(new_drive)
        db.session.commit()

        flash('Placement drive submitted! It will be visible to students after admin approval.', 'success')
        return redirect(url_for('company_dashboard'))

    return render_template('drives.html', company=company, action='create', drive=None)


@app.route('/company/drive/edit/<int:drive_id>', methods=['GET', 'POST'])
@login_required
def edit_drive(drive_id):
    """
    Edit an existing placement drive.
    After editing, the drive goes back to Pending status for re-approval.
    Only the company that owns the drive can edit it.
    """
    if current_user.role != 'company':
        abort(403)

    company = CompanyProfile.query.filter_by(user_id=current_user.id).first()
    drive   = PlacementDrive.query.get_or_404(drive_id)

    # Security check: ensure this drive belongs to the current company
    if drive.company_id != company.id:
        abort(403)

    if request.method == 'POST':
        drive.job_title       = request.form.get('job_title', '').strip()
        drive.job_description = request.form.get('job_description', '').strip()
        drive.eligibility     = request.form.get('eligibility', '').strip()
        deadline_str          = request.form.get('deadline', '').strip()

        try:
            drive.deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Please enter a valid deadline date.', 'danger')
            return render_template('drives.html', company=company, drive=drive, action='edit')

        drive.status = 'Pending'   # Reset to pending after edit — needs re-approval
        db.session.commit()

        flash('Drive updated and re-submitted for admin approval.', 'success')
        return redirect(url_for('company_dashboard'))

    return render_template('drives.html', company=company, drive=drive, action='edit')


@app.route('/company/drive/close/<int:drive_id>')
@login_required
def close_drive(drive_id):
    """
    Close a placement drive (no more applications accepted).
    Only the owning company can close it.
    """
    if current_user.role != 'company':
        abort(403)

    company = CompanyProfile.query.filter_by(user_id=current_user.id).first()
    drive   = PlacementDrive.query.get_or_404(drive_id)

    if drive.company_id != company.id:
        abort(403)

    drive.status = 'Closed'
    db.session.commit()
    flash(f'Drive "{drive.job_title}" has been closed.', 'info')
    return redirect(url_for('company_dashboard'))


@app.route('/company/applicants/<int:drive_id>')
@login_required
def view_applicants(drive_id):
    """
    View all applicants for a specific drive.
    Only the owning company can access this.
    """
    if current_user.role != 'company':
        abort(403)

    company = CompanyProfile.query.filter_by(user_id=current_user.id).first()
    drive   = PlacementDrive.query.get_or_404(drive_id)

    if drive.company_id != company.id:
        abort(403)

    # Fetch all applications with related student data
    applications = Application.query.filter_by(drive_id=drive_id)\
                                    .order_by(Application.application_date).all()

    return render_template('applications.html',
                           drive=drive,
                           applications=applications,
                           view='company')


@app.route('/company/update_application/<int:app_id>', methods=['POST'])
@login_required
def update_application_status(app_id):
    """
    Update the status of a student's application (Shortlisted / Selected / Rejected).
    Only the company that owns the drive can update application statuses.
    """
    if current_user.role != 'company':
        abort(403)

    application = Application.query.get_or_404(app_id)
    company     = CompanyProfile.query.filter_by(user_id=current_user.id).first()

    # Ensure the application belongs to this company's drive
    if application.drive.company_id != company.id:
        abort(403)

    new_status = request.form.get('status', '').strip()
    valid_statuses = ['Applied', 'Shortlisted', 'Selected', 'Rejected']

    if new_status in valid_statuses:
        application.status = new_status
        db.session.commit()
        flash(f'Application status updated to "{new_status}".', 'success')
    else:
        flash('Invalid status value.', 'danger')

    return redirect(url_for('view_applicants', drive_id=application.drive_id))


# ─────────────────────────────────────────────────────────────────────────────
#  STUDENT ROUTES
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/student/dashboard')
@login_required
def student_dashboard():
    """
    Student dashboard.
    Shows available (approved) placement drives and recent applications.
    """
    if current_user.role != 'student':
        flash('Access denied. Students only.', 'danger')
        return redirect(url_for('index'))

    student = StudentProfile.query.filter_by(user_id=current_user.id).first()
    if not student:
        flash('Student profile not found. Please contact admin.', 'danger')
        return redirect(url_for('login'))

    # Only show drives with 'Approved' status
    available_drives = PlacementDrive.query.filter_by(status='Approved')\
                                           .order_by(PlacementDrive.deadline).all()

    # Collect drive IDs the student has already applied to (prevents duplicate apply buttons)
    applied_drive_ids = {app.drive_id for app in student.applications}

    # Show last 5 applications on the dashboard
    recent_applications = Application.query.filter_by(student_id=student.id)\
                                           .order_by(Application.application_date.desc())\
                                           .limit(5).all()

    return render_template(
        'student_dashboard.html',
        student=student,
        available_drives=available_drives,
        applied_drive_ids=applied_drive_ids,
        recent_applications=recent_applications,
        view='dashboard'
    )


@app.route('/student/apply/<int:drive_id>', methods=['POST'])
@login_required
def apply_drive(drive_id):
    """
    Apply to a placement drive.
    Prevents duplicate applications (DB constraint + application-level check).
    Checks that the deadline has not passed.
    """
    if current_user.role != 'student':
        abort(403)

    student = StudentProfile.query.filter_by(user_id=current_user.id).first()
    drive   = PlacementDrive.query.get_or_404(drive_id)

    # Drive must be approved and open
    if drive.status != 'Approved':
        flash('This drive is not available for applications.', 'danger')
        return redirect(url_for('student_dashboard'))

    # Check if the application deadline has passed
    if drive.deadline and drive.deadline < date.today():
        flash('The application deadline for this drive has passed.', 'danger')
        return redirect(url_for('student_dashboard'))

    # Prevent duplicate application
    existing = Application.query.filter_by(
        student_id=student.id,
        drive_id=drive_id
    ).first()

    if existing:
        flash('You have already applied to this placement drive.', 'warning')
        return redirect(url_for('student_dashboard'))

    # Create application record
    application = Application(
        student_id=student.id,
        drive_id=drive_id,
        status='Applied'
    )
    db.session.add(application)
    db.session.commit()

    flash(f'Successfully applied to "{drive.job_title}"! Good luck!', 'success')
    return redirect(url_for('student_dashboard'))


@app.route('/student/applications')
@login_required
def student_applications():
    """View the complete application history of the logged-in student."""
    if current_user.role != 'student':
        abort(403)

    student = StudentProfile.query.filter_by(user_id=current_user.id).first()
    applications = Application.query.filter_by(student_id=student.id)\
                                    .order_by(Application.application_date.desc()).all()

    return render_template('applications.html',
                           applications=applications,
                           view='student')


@app.route('/student/profile', methods=['GET', 'POST'])
@login_required
def student_profile():
    """
    View and update student profile.
    Also handles resume file upload (PDF/DOC/DOCX, max 5 MB).
    """
    if current_user.role != 'student':
        abort(403)

    student = StudentProfile.query.filter_by(user_id=current_user.id).first()

    if request.method == 'POST':
        # Update name on User record
        current_user.name = request.form.get('name', current_user.name).strip()

        # Update student profile fields
        student.course         = request.form.get('course', student.course).strip()
        student.contact_number = request.form.get('contact_number', student.contact_number).strip()

        # Validate and update CGPA
        cgpa_str = request.form.get('cgpa', '').strip()
        try:
            cgpa = float(cgpa_str)
            if 0.0 <= cgpa <= 10.0:
                student.cgpa = cgpa
            else:
                raise ValueError
        except (ValueError, TypeError):
            flash('CGPA must be a number between 0.0 and 10.0.', 'danger')
            return render_template('student_dashboard.html',
                                   student=student, view='profile')

        # ── Handle Resume Upload ────────────────────────────────────────────
        if 'resume' in request.files:
            file = request.files['resume']
            if file and file.filename:
                if allowed_file(file.filename):
                    # Delete the old resume file if one exists
                    if student.resume_filename:
                        old_path = os.path.join(app.config['UPLOAD_FOLDER'],
                                                student.resume_filename)
                        if os.path.exists(old_path):
                            os.remove(old_path)

                    # Prefix with user ID to avoid filename collisions
                    filename = secure_filename(f"student_{current_user.id}_{file.filename}")
                    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    student.resume_filename = filename
                    flash('Resume uploaded successfully.', 'success')
                else:
                    flash('Invalid file type. Only PDF, DOC, DOCX files are allowed.', 'danger')
                    return render_template('student_dashboard.html',
                                           student=student, view='profile')

        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('student_profile'))

    return render_template('student_dashboard.html', student=student, view='profile')


# ─────────────────────────────────────────────────────────────────────────────
#  APPLICATION ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    with app.app_context():
        # Create all database tables (safe to run multiple times)
        db.create_all()
        print('✅  Database tables created (or already exist).')

        # Create the default admin account if not present
        create_default_admin()

        # Ensure the uploads folder exists
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        print('📁  Upload folder ready.')

    print('\n' + '='*50)
    print('🚀  Placement Portal is running!')
    print('📌  URL  : http://127.0.0.1:5000')
    print('🔑  Admin: admin@portal.com / admin123')
    print('='*50 + '\n')

    app.run(debug=True)
