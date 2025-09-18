from flask import Blueprint, request, jsonify, render_template, redirect, url_for
from models import User, db
from auth import hash_password, log_action
from werkzeug.security import generate_password_hash
import os
import re
import secrets
import smtplib
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from datetime import datetime, timedelta

registration_bp = Blueprint('registration', __name__)

def is_email_domain_allowed(email):
    """Check if email domain is in allowed domains list"""
    allowed_domains = os.getenv('ALLOWED_EMAIL_DOMAINS', '').split(',')
    if not allowed_domains or not allowed_domains[0]:
        return True  # No restriction if not configured

    email_domain = email.split('@')[-1].lower()
    allowed_domains = [domain.strip().lower() for domain in allowed_domains]
    return email_domain in allowed_domains

def generate_verification_token():
    """Generate a secure verification token"""
    return secrets.token_urlsafe(32)

def send_verification_email(user, token):
    """Send email verification to user"""
    try:
        smtp_server = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('MAIL_PORT', '587'))
        smtp_username = os.getenv('MAIL_USERNAME')
        smtp_password = os.getenv('MAIL_PASSWORD')

        if not all([smtp_username, smtp_password]):
            print("Email configuration not found, skipping email verification")
            return False

        verification_url = f"{request.host_url}verify-email/{token}"
        organization_name = os.getenv('ORGANIZATION_NAME', 'TimeTracker Pro')

        # Create email content
        msg = MimeMultipart()
        msg['From'] = smtp_username
        msg['To'] = user.email
        msg['Subject'] = f"Verify your {organization_name} account"

        body = f"""
        Hello {user.first_name},

        Welcome to {organization_name}! Please verify your email address by clicking the link below:

        {verification_url}

        This link will expire in 24 hours.

        If you didn't create an account, please ignore this email.

        Best regards,
        {organization_name} Team
        """

        msg.attach(MimeText(body, 'plain'))

        # Send email
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.send_message(msg)
        server.quit()

        return True

    except Exception as e:
        print(f"Failed to send verification email: {e}")
        return False

def send_admin_notification(user):
    """Send notification to admins about new user registration"""
    try:
        # Get admin users
        admin_users = User.query.filter_by(role='admin', is_active=True).all()

        if not admin_users:
            return

        smtp_server = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('MAIL_PORT', '587'))
        smtp_username = os.getenv('MAIL_USERNAME')
        smtp_password = os.getenv('MAIL_PASSWORD')

        if not all([smtp_username, smtp_password]):
            return

        organization_name = os.getenv('ORGANIZATION_NAME', 'TimeTracker Pro')
        admin_url = f"{request.host_url}admin/users"

        for admin in admin_users:
            msg = MimeMultipart()
            msg['From'] = smtp_username
            msg['To'] = admin.email
            msg['Subject'] = f"New user registration requires approval - {organization_name}"

            body = f"""
            Hello {admin.first_name},

            A new user has registered for {organization_name} and requires approval:

            Name: {user.first_name} {user.last_name}
            Email: {user.email}
            Registration Date: {user.created_at}

            Please review and approve the user account:
            {admin_url}

            Best regards,
            {organization_name} System
            """

            msg.attach(MimeText(body, 'plain'))

            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)
            server.quit()

    except Exception as e:
        print(f"Failed to send admin notification: {e}")

@registration_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration endpoint"""
    if request.method == 'GET':
        # Check if self-registration is allowed
        if os.getenv('ALLOW_SELF_REGISTRATION', 'false').lower() != 'true':
            return render_template('error.html',
                                 error='Self-registration is not enabled',
                                 message='Please contact your administrator for an account.')

        return render_template('register.html')

    # Handle POST request
    data = request.get_json()

    # Validate required fields
    required_fields = ['first_name', 'last_name', 'email', 'password']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'error': f'{field.replace("_", " ").title()} is required'}), 400

    first_name = data['first_name'].strip()
    last_name = data['last_name'].strip()
    email = data['email'].strip().lower()
    password = data['password']

    # Validate email format
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        return jsonify({'error': 'Invalid email format'}), 400

    # Check domain restriction
    if not is_email_domain_allowed(email):
        allowed_domains = os.getenv('ALLOWED_EMAIL_DOMAINS', '')
        return jsonify({
            'error': f'Registration is restricted to {allowed_domains} email addresses'
        }), 400

    # Check if user already exists
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email address already registered'}), 400

    # Generate username from email
    username = email.split('@')[0]
    counter = 1
    original_username = username

    # Ensure username is unique
    while User.query.filter_by(username=username).first():
        username = f"{original_username}{counter}"
        counter += 1

    # Validate password strength
    if len(password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters long'}), 400

    # Check if admin approval is required
    require_approval = os.getenv('REQUIRE_ADMIN_APPROVAL', 'false').lower() == 'true'
    is_active = not require_approval

    # Create user
    try:
        user = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            password_hash=generate_password_hash(password),
            role='employee',
            is_active=is_active,
            auth_provider='local',
            email_verified=False
        )

        # Generate email verification token if email is configured
        verification_token = None
        if os.getenv('MAIL_USERNAME'):
            verification_token = generate_verification_token()
            user.email_verification_token = verification_token
            user.email_verification_expires = datetime.utcnow() + timedelta(hours=24)

        db.session.add(user)
        db.session.commit()

        log_action(user.id, 'USER_REGISTERED')

        # Send verification email
        email_sent = False
        if verification_token:
            email_sent = send_verification_email(user, verification_token)

        # Send admin notification if approval required
        if require_approval:
            send_admin_notification(user)

        # Prepare response message
        if require_approval:
            message = 'Registration successful! Your account is pending admin approval.'
        elif verification_token and email_sent:
            message = 'Registration successful! Please check your email to verify your account.'
        elif verification_token and not email_sent:
            message = 'Registration successful! Email verification failed - please contact support.'
        else:
            message = 'Registration successful! You can now log in.'

        return jsonify({
            'message': message,
            'user_id': user.id,
            'requires_approval': require_approval,
            'requires_verification': bool(verification_token)
        })

    except Exception as e:
        db.session.rollback()
        print(f"Registration error: {e}")
        return jsonify({'error': 'Registration failed. Please try again.'}), 500

@registration_bp.route('/verify-email/<token>')
def verify_email(token):
    """Verify user email with token"""
    user = User.query.filter_by(email_verification_token=token).first()

    if not user:
        return render_template('error.html',
                             error='Invalid verification link',
                             message='This verification link is invalid or has already been used.')

    # Check if token has expired
    if user.email_verification_expires and user.email_verification_expires < datetime.utcnow():
        return render_template('error.html',
                             error='Verification link expired',
                             message='This verification link has expired. Please request a new one.')

    # Verify email
    user.email_verified = True
    user.email_verification_token = None
    user.email_verification_expires = None
    db.session.commit()

    log_action(user.id, 'EMAIL_VERIFIED')

    return render_template('success.html',
                         title='Email Verified',
                         message='Your email has been verified successfully! You can now log in.')

@registration_bp.route('/resend-verification', methods=['POST'])
def resend_verification():
    """Resend email verification"""
    data = request.get_json()
    email = data.get('email', '').strip().lower()

    if not email:
        return jsonify({'error': 'Email is required'}), 400

    user = User.query.filter_by(email=email).first()

    if not user:
        return jsonify({'error': 'User not found'}), 404

    if user.email_verified:
        return jsonify({'error': 'Email already verified'}), 400

    # Generate new verification token
    verification_token = generate_verification_token()
    user.email_verification_token = verification_token
    user.email_verification_expires = datetime.utcnow() + timedelta(hours=24)
    db.session.commit()

    # Send verification email
    if send_verification_email(user, verification_token):
        return jsonify({'message': 'Verification email sent successfully'})
    else:
        return jsonify({'error': 'Failed to send verification email'}), 500

@registration_bp.route('/check-domain', methods=['POST'])
def check_domain():
    """Check if email domain is allowed"""
    data = request.get_json()
    email = data.get('email', '').strip().lower()

    if not email:
        return jsonify({'valid': False, 'error': 'Email is required'})

    # Validate email format
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        return jsonify({'valid': False, 'error': 'Invalid email format'})

    # Check domain
    if is_email_domain_allowed(email):
        return jsonify({'valid': True})
    else:
        allowed_domains = os.getenv('ALLOWED_EMAIL_DOMAINS', '')
        return jsonify({
            'valid': False,
            'error': f'Registration is restricted to {allowed_domains} email addresses'
        })