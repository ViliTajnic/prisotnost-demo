from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_cors import CORS
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import oracledb

load_dotenv()

# python-oracledb automatically uses thin mode when no init_oracle_client() is called
# This requires no Oracle client installation

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# Updated DATABASE_URL for python-oracledb
oracle_url = os.getenv('DATABASE_URL', 'oracle+oracledb://system:MyPassword123@localhost:1521/?service_name=FREEPDB1')
app.config['SQLALCHEMY_DATABASE_URI'] = oracle_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key-change-in-production')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=1)

# OAuth Configuration
app.config['GOOGLE_CLIENT_ID'] = os.getenv('GOOGLE_CLIENT_ID')
app.config['GOOGLE_CLIENT_SECRET'] = os.getenv('GOOGLE_CLIENT_SECRET')

# Initialize database from separate module to avoid circular imports
from database import db
db.init_app(app)

jwt = JWTManager(app)
CORS(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

from models import *
from authlib.integrations.flask_client import OAuth
from flask import session
import requests

# Initialize OAuth
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    access_token_url='https://oauth2.googleapis.com/token',
    client_kwargs={
        'scope': 'email profile',
        'response_type': 'code'
    }
)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()})

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            access_token = create_access_token(identity=user.id)
            return jsonify({
                'success': True,
                'access_token': access_token,
                'user_id': user.id,
                'role': user.role,
                'message': 'Login successful'
            })

        return jsonify({'error': 'Invalid credentials'}), 401

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/clock-in', methods=['POST'])
@login_required
def clock_in():
    user_id = current_user.id
    data = request.get_json()

    existing_entry = TimeEntry.query.filter_by(
        user_id=user_id,
        clock_out_time=None
    ).first()

    if existing_entry:
        return jsonify({'error': 'Already clocked in'}), 400

    time_entry = TimeEntry(
        user_id=user_id,
        clock_in_time=datetime.utcnow(),
        location_lat=data.get('latitude'),
        location_lon=data.get('longitude')
    )

    db.session.add(time_entry)
    db.session.commit()

    return jsonify({'message': 'Clocked in successfully', 'entry_id': time_entry.id})

@app.route('/api/clock-out', methods=['POST'])
@login_required
def clock_out():
    user_id = current_user.id

    time_entry = TimeEntry.query.filter_by(
        user_id=user_id,
        clock_out_time=None
    ).first()

    if not time_entry:
        return jsonify({'error': 'Not currently clocked in'}), 400

    time_entry.clock_out_time = datetime.utcnow()

    duration = time_entry.clock_out_time - time_entry.clock_in_time
    time_entry.total_hours = duration.total_seconds() / 3600

    db.session.commit()

    return jsonify({'message': 'Clocked out successfully', 'total_hours': time_entry.total_hours})

@app.route('/api/time-entries')
@login_required
def get_time_entries():
    user_id = current_user.id
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    query = TimeEntry.query.filter_by(user_id=user_id).order_by(TimeEntry.clock_in_time.desc())

    if per_page:
        entries = query.limit(per_page).all()
    else:
        entries = query.all()

    return jsonify([{
        'id': entry.id,
        'clock_in_time': entry.clock_in_time.isoformat(),
        'clock_out_time': entry.clock_out_time.isoformat() if entry.clock_out_time else None,
        'total_hours': entry.total_hours,
        'project_id': entry.project_id
    } for entry in entries])

@app.route('/api/current-status')
@login_required
def get_current_status():
    user_id = current_user.id
    current_entry = TimeEntry.query.filter_by(
        user_id=user_id,
        clock_out_time=None
    ).first()

    if current_entry:
        return jsonify({
            'status': 'clocked_in',
            'entry_id': current_entry.id,
            'clock_in_time': current_entry.clock_in_time.isoformat(),
            'project_id': current_entry.project_id
        })
    else:
        return jsonify({
            'status': 'clocked_out'
        })

@app.route('/api/weekly-summary')
@login_required
def get_weekly_summary():
    user_id = current_user.id
    from datetime import datetime, timedelta

    # Get start and end of current week
    today = datetime.now().date()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    entries = TimeEntry.query.filter(
        TimeEntry.user_id == user_id,
        TimeEntry.clock_in_time >= start_of_week,
        TimeEntry.clock_in_time <= end_of_week + timedelta(days=1)
    ).all()

    total_hours = sum(entry.total_hours or 0 for entry in entries)

    return jsonify({
        'total_hours': total_hours,
        'entries_count': len(entries),
        'week_start': start_of_week.isoformat(),
        'week_end': end_of_week.isoformat()
    })

@app.route('/schedule')
@login_required
def schedule():
    return render_template('schedule.html')

@app.route('/reports')
@login_required
def reports():
    return render_template('reports.html')

# User profile and settings routes
@app.route('/profile')
@login_required
def profile():
    departments = Department.query.all()
    return render_template('profile.html', user=current_user, departments=departments)

@app.route('/profile', methods=['POST'])
@login_required
def update_profile():
    try:
        data = request.get_json()

        # Update user information
        current_user.first_name = data.get('first_name', current_user.first_name)
        current_user.last_name = data.get('last_name', current_user.last_name)
        current_user.email = data.get('email', current_user.email)

        # Update department if provided
        department_id = data.get('department_id')
        if department_id:
            current_user.department_id = int(department_id)
        elif department_id == '':
            current_user.department_id = None

        # Update password if provided
        new_password = data.get('new_password')
        if new_password:
            current_password = data.get('current_password')
            if not current_password or not check_password_hash(current_user.password_hash, current_password):
                return jsonify({'success': False, 'message': 'Current password is incorrect'}), 400
            current_user.password_hash = generate_password_hash(new_password)

        db.session.commit()
        return jsonify({'success': True, 'message': 'Profile updated successfully'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error updating profile: {str(e)}'}), 500

@app.route('/settings')
@login_required
def settings():
    return render_template('settings.html', user=current_user)

@app.route('/settings', methods=['POST'])
@login_required
def update_settings():
    try:
        data = request.get_json()

        # For now, we'll store user preferences in a simple way
        # In a real application, you might want a separate UserSettings table

        # You can extend this to handle various settings like:
        # - Theme preference
        # - Notification settings
        # - Time format preferences
        # - Default project selection
        # etc.

        # Example: Store theme preference (this would require adding a theme_preference column to users table)
        # current_user.theme_preference = data.get('theme_preference', 'auto')

        db.session.commit()
        return jsonify({'success': True, 'message': 'Settings updated successfully'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error updating settings: {str(e)}'}), 500

# Admin routes
@app.route('/admin/users')
@login_required
def manage_users():
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    users = User.query.all()
    departments = Department.query.filter_by(is_active=True).all()
    return render_template('admin/users.html', users=users, departments=departments)

@app.route('/admin/departments')
@login_required
def manage_departments():
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    departments = Department.query.all()
    users = User.query.all()
    return render_template('admin/departments.html', departments=departments, users=users)

@app.route('/admin/projects')
@login_required
def manage_projects():
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    projects = Project.query.all()
    return render_template('admin/projects.html', projects=projects)

@app.route('/admin/geofences')
@login_required
def manage_geofences():
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    geofences = Geofence.query.all()
    return render_template('admin/geofences.html', geofences=geofences)

# API routes for admin functionality
@app.route('/api/users', methods=['GET', 'POST'])
@login_required
def api_users():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    if request.method == 'POST':
        data = request.get_json()
        # Convert department_id to int if provided, otherwise set to None
        department_id = None
        if data.get('department_id') and data['department_id'].strip():
            department_id = int(data['department_id'])

        user = User(
            username=data['username'],
            email=data['email'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            role=data.get('role', 'employee'),
            department_id=department_id,
            password_hash=generate_password_hash(data['password'])
        )
        db.session.add(user)
        db.session.commit()
        return jsonify({'success': True, 'message': 'User created successfully'})

    users = User.query.all()
    return jsonify([{
        'id': u.id,
        'username': u.username,
        'email': u.email,
        'first_name': u.first_name,
        'last_name': u.last_name,
        'role': u.role,
        'is_active': u.is_active,
        'created_at': u.created_at.isoformat() if u.created_at else None
    } for u in users])

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@login_required
def delete_user(user_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    user = User.query.get_or_404(user_id)

    # Prevent deleting the current admin user
    if user.id == current_user.id:
        return jsonify({'error': 'Cannot delete your own account'}), 400

    try:
        db.session.delete(user)
        db.session.commit()
        return jsonify({'success': True, 'message': 'User deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to delete user: ' + str(e)}), 500

@app.route('/api/projects', methods=['GET', 'POST'])
@login_required
def api_projects():
    if request.method == 'POST':
        if current_user.role != 'admin':
            return jsonify({'error': 'Unauthorized'}), 403
        data = request.get_json()
        project = Project(
            name=data['name'],
            description=data.get('description'),
            client_name=data.get('client_name'),
            project_code=data.get('project_code'),
            hourly_rate=data.get('hourly_rate'),
            is_billable=data.get('is_billable', True)
        )
        db.session.add(project)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Project created successfully'})

    projects = Project.query.all()
    return jsonify([{
        'id': p.id,
        'name': p.name,
        'description': p.description,
        'client_name': p.client_name,
        'project_code': p.project_code,
        'hourly_rate': p.hourly_rate,
        'is_billable': p.is_billable,
        'status': p.status
    } for p in projects])

@app.route('/api/projects/<int:project_id>', methods=['DELETE'])
@login_required
def delete_project(project_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    project = Project.query.get_or_404(project_id)

    try:
        db.session.delete(project)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Project deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to delete project: ' + str(e)}), 500

@app.route('/api/geofences', methods=['GET', 'POST'])
@login_required
def api_geofences():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    if request.method == 'POST':
        data = request.get_json()
        geofence = Geofence(
            name=data['name'],
            center_lat=data['center_lat'],
            center_lon=data['center_lon'],
            radius=data['radius'],
            is_active=data.get('is_active', True)
        )
        db.session.add(geofence)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Geofence created successfully'})

    geofences = Geofence.query.all()
    return jsonify([{
        'id': g.id,
        'name': g.name,
        'center_lat': g.center_lat,
        'center_lon': g.center_lon,
        'radius': g.radius,
        'is_active': g.is_active,
        'created_at': g.created_at.isoformat() if g.created_at else None
    } for g in geofences])

@app.route('/api/reports', methods=['GET'])
@login_required
def api_reports():
    from datetime import datetime, timedelta
    from sqlalchemy import func

    # Get query parameters
    report_type = request.args.get('report_type', 'attendance')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    employee_id = request.args.get('employee_id')
    page = int(request.args.get('page', 1))
    per_page = 20

    try:
        # Parse dates
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
        else:
            start_date = datetime.now() - timedelta(days=7)

        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
        else:
            end_date = datetime.now()

        # Base query for time entries
        query = TimeEntry.query.filter(
            TimeEntry.clock_in_time >= start_date,
            TimeEntry.clock_in_time <= end_date + timedelta(days=1)
        )

        # Filter by employee if specified and user has permission
        if employee_id and current_user.role in ['admin', 'manager']:
            query = query.filter(TimeEntry.user_id == employee_id)
        elif current_user.role not in ['admin', 'manager']:
            # Regular users can only see their own data
            query = query.filter(TimeEntry.user_id == current_user.id)

        # Get time entries for calculations
        time_entries = query.all()

        # Calculate summary statistics
        total_hours = 0
        regular_hours = 0
        overtime_hours = 0

        for entry in time_entries:
            if entry.clock_out_time:
                duration = (entry.clock_out_time - entry.clock_in_time).total_seconds() / 3600
                total_hours += duration
                if duration <= 8:
                    regular_hours += duration
                else:
                    regular_hours += 8
                    overtime_hours += duration - 8

        # Calculate attendance rate (simplified)
        working_days = (end_date - start_date).days + 1
        attendance_rate = (len(set(entry.clock_in_time.date() for entry in time_entries)) / max(working_days, 1)) * 100

        summary = {
            'total_hours': total_hours,
            'regular_hours': regular_hours,
            'overtime_hours': overtime_hours,
            'attendance_rate': attendance_rate
        }

        # Generate chart data based on report type
        if report_type == 'attendance':
            chart_data = generate_attendance_chart(time_entries, start_date, end_date)
        elif report_type == 'overtime':
            chart_data = generate_overtime_chart(time_entries, start_date, end_date)
        elif report_type == 'project':
            chart_data = generate_project_chart(time_entries, start_date, end_date)
        else:
            chart_data = generate_attendance_chart(time_entries, start_date, end_date)

        # Generate secondary chart (time distribution)
        secondary_chart = {
            'labels': ['Regular Hours', 'Overtime Hours', 'Break Time'],
            'datasets': [{
                'data': [regular_hours, overtime_hours, total_hours * 0.1],
                'backgroundColor': ['#198754', '#ffc107', '#6c757d']
            }]
        }

        # Generate table data
        table_data = generate_table_data(time_entries, report_type, page, per_page)

        return jsonify({
            'summary': summary,
            'chart_data': chart_data,
            'secondary_chart': secondary_chart,
            'table_data': table_data,
            'pagination': {
                'current_page': page,
                'total_pages': max(1, (len(time_entries) + per_page - 1) // per_page)
            }
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

def generate_attendance_chart(time_entries, start_date, end_date):
    from collections import defaultdict

    daily_hours = defaultdict(float)

    for entry in time_entries:
        if entry.clock_out_time:
            date_key = entry.clock_in_time.date()
            duration = (entry.clock_out_time - entry.clock_in_time).total_seconds() / 3600
            daily_hours[date_key] += duration

    # Generate labels for all days in range
    current_date = start_date.date()
    end_date_only = end_date.date()
    labels = []
    data = []

    while current_date <= end_date_only:
        labels.append(current_date.strftime('%m/%d'))
        data.append(daily_hours.get(current_date, 0))
        current_date += timedelta(days=1)

    return {
        'labels': labels,
        'datasets': [{
            'label': 'Daily Hours',
            'data': data,
            'borderColor': '#0d6efd',
            'backgroundColor': 'rgba(13, 110, 253, 0.1)',
            'tension': 0.1
        }]
    }

def generate_overtime_chart(time_entries, start_date, end_date):
    from collections import defaultdict

    daily_overtime = defaultdict(float)

    for entry in time_entries:
        if entry.clock_out_time:
            date_key = entry.clock_in_time.date()
            duration = (entry.clock_out_time - entry.clock_in_time).total_seconds() / 3600
            if duration > 8:
                daily_overtime[date_key] += duration - 8

    # Generate labels for all days in range
    current_date = start_date.date()
    end_date_only = end_date.date()
    labels = []
    data = []

    while current_date <= end_date_only:
        labels.append(current_date.strftime('%m/%d'))
        data.append(daily_overtime.get(current_date, 0))
        current_date += timedelta(days=1)

    return {
        'labels': labels,
        'datasets': [{
            'label': 'Overtime Hours',
            'data': data,
            'borderColor': '#ffc107',
            'backgroundColor': 'rgba(255, 193, 7, 0.1)',
            'tension': 0.1
        }]
    }

def generate_project_chart(time_entries, start_date, end_date):
    from collections import defaultdict

    project_hours = defaultdict(float)

    for entry in time_entries:
        if entry.clock_out_time:
            project_name = entry.project.name if entry.project else 'No Project'
            duration = (entry.clock_out_time - entry.clock_in_time).total_seconds() / 3600
            project_hours[project_name] += duration

    return {
        'labels': list(project_hours.keys()),
        'datasets': [{
            'label': 'Project Hours',
            'data': list(project_hours.values()),
            'borderColor': '#198754',
            'backgroundColor': 'rgba(25, 135, 84, 0.1)',
            'tension': 0.1
        }]
    }

def generate_table_data(time_entries, report_type, page, per_page):
    start_index = (page - 1) * per_page
    end_index = start_index + per_page
    page_entries = time_entries[start_index:end_index]

    if report_type == 'attendance':
        headers = ['Date', 'Employee', 'Clock In', 'Clock Out', 'Total Hours', 'Status']
        rows = []
        for entry in page_entries:
            duration = 0
            status = 'Incomplete'
            if entry.clock_out_time:
                duration = (entry.clock_out_time - entry.clock_in_time).total_seconds() / 3600
                status = 'Complete'

            rows.append([
                entry.clock_in_time.strftime('%Y-%m-%d'),
                f"{entry.user.first_name} {entry.user.last_name}",
                entry.clock_in_time.strftime('%H:%M'),
                entry.clock_out_time.strftime('%H:%M') if entry.clock_out_time else 'N/A',
                f"{duration:.2f}",
                status
            ])
    else:
        # Default table structure
        headers = ['Date', 'Employee', 'Hours', 'Notes']
        rows = []
        for entry in page_entries:
            duration = 0
            if entry.clock_out_time:
                duration = (entry.clock_out_time - entry.clock_in_time).total_seconds() / 3600

            rows.append([
                entry.clock_in_time.strftime('%Y-%m-%d'),
                f"{entry.user.first_name} {entry.user.last_name}",
                f"{duration:.2f}",
                entry.notes or 'N/A'
            ])

    return {
        'headers': headers,
        'rows': rows
    }

@app.route('/api/employees', methods=['GET'])
@login_required
def api_employees():
    if current_user.role not in ['admin', 'manager']:
        return jsonify({'error': 'Unauthorized'}), 403

    users = User.query.filter_by(role='employee').all()
    return jsonify([{
        'id': u.id,
        'first_name': u.first_name,
        'last_name': u.last_name,
        'email': u.email
    } for u in users])

@app.route('/api/departments', methods=['GET', 'POST'])
@login_required
def api_departments():
    if current_user.role not in ['admin', 'manager']:
        return jsonify({'error': 'Unauthorized'}), 403

    if request.method == 'POST':
        if current_user.role != 'admin':
            return jsonify({'error': 'Only admins can create departments'}), 403

        data = request.get_json()
        department = Department(
            name=data['name'],
            description=data.get('description'),
            manager_id=data.get('manager_id'),
            is_active=data.get('is_active', True)
        )
        db.session.add(department)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Department created successfully'})

    departments = Department.query.all()
    return jsonify([{
        'id': d.id,
        'name': d.name,
        'description': d.description,
        'manager_id': d.manager_id,
        'is_active': d.is_active,
        'created_at': d.created_at.isoformat() if d.created_at else None
    } for d in departments])

@app.route('/api/export-report', methods=['POST'])
@login_required
def api_export_report():
    try:
        data = request.get_json()
        format_type = data.get('format', 'pdf')

        # For now, return a simple success message
        # In a full implementation, this would generate actual files
        return jsonify({
            'success': True,
            'message': f'Report export in {format_type} format initiated',
            'download_url': f'/downloads/report.{format_type}'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Blueprints temporarily disabled due to circular imports
# Will be added back once circular import issues are resolved

@app.route('/api/break-start', methods=['POST'])
@login_required
def start_break():
    user_id = current_user.id

    active_entry = TimeEntry.query.filter_by(
        user_id=user_id,
        clock_out_time=None
    ).first()

    if not active_entry:
        return jsonify({'error': 'Not currently clocked in'}), 400

    return jsonify({'message': 'Break started', 'break_start_time': datetime.utcnow().isoformat()})

@app.route('/api/break-end', methods=['POST'])
@login_required
def end_break():
    user_id = current_user.id
    data = request.get_json()

    active_entry = TimeEntry.query.filter_by(
        user_id=user_id,
        clock_out_time=None
    ).first()

    if not active_entry:
        return jsonify({'error': 'Not currently clocked in'}), 400

    break_duration = data.get('break_duration', 0)
    if active_entry.break_duration is None:
        active_entry.break_duration = 0
    active_entry.break_duration += break_duration

    db.session.commit()

    return jsonify({'message': 'Break ended', 'total_break_duration': active_entry.break_duration})

# OAuth Routes
@app.route('/auth/google')
def google_login():
    """Initiate Google OAuth login"""
    redirect_uri = url_for('google_callback', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/auth/google/callback')
def google_callback():
    """Handle Google OAuth callback"""
    try:
        # Get the authorization token
        token = google.authorize_access_token()

        # Get user info from Google using the access token
        import requests
        access_token = token.get('access_token')

        # Fetch user info from Google's userinfo endpoint
        userinfo_response = requests.get(
            'https://www.googleapis.com/oauth2/v2/userinfo',
            headers={'Authorization': f'Bearer {access_token}'}
        )

        if userinfo_response.status_code != 200:
            print(f"Failed to fetch user info: {userinfo_response.status_code}")
            return redirect('/login?error=oauth_failed')

        user_info = userinfo_response.json()

        google_id = user_info.get('id')  # Changed from 'sub' to 'id' for v2 API
        email = user_info.get('email')
        first_name = user_info.get('given_name', '')
        last_name = user_info.get('family_name', '')
        picture = user_info.get('picture', '')

        if not google_id or not email:
            return redirect('/login?error=oauth_failed')

        # Check if user already exists
        user = User.query.filter_by(google_id=google_id).first()

        if not user:
            # Check if user exists with this email
            user = User.query.filter_by(email=email).first()

            if user:
                # Link existing account with Google
                user.google_id = google_id
                user.profile_picture = picture
                db.session.commit()
            else:
                # Create new user
                username = email.split('@')[0]
                counter = 1
                original_username = username

                # Ensure username is unique
                while User.query.filter_by(username=username).first():
                    username = f"{original_username}{counter}"
                    counter += 1

                user = User(
                    username=username,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    google_id=google_id,
                    profile_picture=picture,
                    password_hash='',  # No password for OAuth users
                    role='employee',  # Default role
                    is_active=True,
                    auth_provider='google',
                    email_verified=True  # Google emails are verified
                )

                db.session.add(user)
                db.session.commit()

        # Check if user account is active
        if not user.is_active:
            return redirect('/login?error=account_pending_approval')

        # Update last login
        user.last_login = datetime.utcnow()
        db.session.commit()

        # Create JWT token and log in user
        access_token = create_access_token(identity=user.id)
        login_user(user)

        # Store user info in session for frontend
        session['user_id'] = user.id
        session['access_token'] = access_token

        # Redirect to dashboard
        return redirect('/dashboard')

    except Exception as e:
        print(f"Google OAuth error: {e}")
        import traceback
        traceback.print_exc()
        return redirect('/login?error=oauth_failed')

if __name__ == '__main__':
    # Skip db.create_all() since tables already exist and there are model issues
    # with app.app_context():
    #     db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5001)