from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from database import db

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=True)  # Nullable for OAuth users
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(20), default='employee')
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    hire_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # OAuth fields
    google_id = db.Column(db.String(100), unique=True, nullable=True)
    github_id = db.Column(db.String(100), unique=True, nullable=True)
    microsoft_id = db.Column(db.String(100), unique=True, nullable=True)
    auth_provider = db.Column(db.String(20), default='local')  # local, google, github, microsoft
    profile_picture = db.Column(db.String(500), nullable=True)
    email_verified = db.Column(db.Boolean, default=False)
    last_login = db.Column(db.DateTime, nullable=True)

    # Email verification fields
    email_verification_token = db.Column(db.String(100), nullable=True)
    email_verification_expires = db.Column(db.DateTime, nullable=True)

    time_entries = db.relationship('TimeEntry', backref='user', lazy=True)
    leave_requests = db.relationship('LeaveRequest', foreign_keys='LeaveRequest.user_id', backref='user', lazy=True)
    approved_leave_requests = db.relationship('LeaveRequest', foreign_keys='LeaveRequest.approved_by', backref='approver', lazy=True)
    schedules = db.relationship('Schedule', backref='user', lazy=True)

    # Department relationship
    department = db.relationship('Department', foreign_keys=[department_id], backref='employees')

class Department(db.Model):
    __tablename__ = 'departments'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    manager_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    # Relationships
    manager = db.relationship('User', foreign_keys=[manager_id], backref='managed_departments')

class TimeEntry(db.Model):
    __tablename__ = 'time_entries'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    clock_in_time = db.Column(db.DateTime, nullable=False)
    clock_out_time = db.Column(db.DateTime)
    total_hours = db.Column(db.Float)
    break_duration = db.Column(db.Float, default=0)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'))
    location_lat = db.Column(db.Float)
    location_lon = db.Column(db.Float)
    notes = db.Column(db.Text)
    is_overtime = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Project(db.Model):
    __tablename__ = 'projects'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    client_name = db.Column(db.String(200))
    project_code = db.Column(db.String(50), unique=True)
    hourly_rate = db.Column(db.Float)
    is_billable = db.Column(db.Boolean, default=True)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    time_entries = db.relationship('TimeEntry', backref='project', lazy=True)

class Schedule(db.Model):
    __tablename__ = 'schedules'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    shift_type = db.Column(db.String(50))
    notes = db.Column(db.Text)
    is_recurring = db.Column(db.Boolean, default=False)
    recurrence_pattern = db.Column(db.String(50))
    status = db.Column(db.String(20), default='scheduled')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class LeaveRequest(db.Model):
    __tablename__ = 'leave_requests'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    leave_type = db.Column(db.String(50), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    total_days = db.Column(db.Float)
    reason = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    approved_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Geofence(db.Model):
    __tablename__ = 'geofences'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    center_lat = db.Column(db.Float, nullable=False)
    center_lon = db.Column(db.Float, nullable=False)
    radius = db.Column(db.Float, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    action = db.Column(db.String(100), nullable=False)
    table_name = db.Column(db.String(50))
    record_id = db.Column(db.Integer)
    old_values = db.Column(db.Text)
    new_values = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)