from flask import Blueprint, request, jsonify, redirect, url_for, session
from flask_jwt_extended import create_access_token
from authlib.integrations.flask_client import OAuth
from models import User, db
from auth import log_action
import os
import requests
from datetime import datetime

oauth_bp = Blueprint('oauth', __name__)

# Initialize OAuth
oauth = OAuth()

def init_oauth(app):
    """Initialize OAuth with Flask app"""
    oauth.init_app(app)

    # Configure Google OAuth
    google = oauth.register(
        name='google',
        client_id=os.getenv('GOOGLE_CLIENT_ID'),
        client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
        server_metadata_url='https://accounts.google.com/.well-known/openid_configuration',
        client_kwargs={
            'scope': 'openid email profile'
        }
    )

    return google

@oauth_bp.route('/auth/google')
def google_login():
    """Initiate Google OAuth login"""
    redirect_uri = url_for('oauth.google_callback', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@oauth_bp.route('/auth/google/callback')
def google_callback():
    """Handle Google OAuth callback"""
    try:
        # Get the authorization token
        token = oauth.google.authorize_access_token()

        # Get user info from Google
        user_info = token.get('userinfo')
        if not user_info:
            # Fallback: fetch user info manually
            resp = oauth.google.parse_id_token(token)
            user_info = resp

        google_id = user_info.get('sub')
        email = user_info.get('email')
        first_name = user_info.get('given_name', '')
        last_name = user_info.get('family_name', '')
        picture = user_info.get('picture', '')

        if not google_id or not email:
            return jsonify({'error': 'Failed to get user information from Google'}), 400

        # Check domain restriction
        allowed_domains = os.getenv('ALLOWED_EMAIL_DOMAINS', '').split(',')
        if allowed_domains and allowed_domains[0]:  # If domain restriction is configured
            email_domain = email.split('@')[-1].lower()
            allowed_domains = [domain.strip().lower() for domain in allowed_domains]

            if email_domain not in allowed_domains:
                return redirect(f'/login?error=domain_not_allowed&domain={email_domain}')

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
                log_action(user.id, 'GOOGLE_ACCOUNT_LINKED')
            else:
                # Create new user
                # Generate username from email
                username = email.split('@')[0]
                counter = 1
                original_username = username

                # Ensure username is unique
                while User.query.filter_by(username=username).first():
                    username = f"{original_username}{counter}"
                    counter += 1

                # Check if admin approval is required
                require_approval = os.getenv('REQUIRE_ADMIN_APPROVAL', 'false').lower() == 'true'
                is_active = not require_approval  # If approval required, start inactive

                user = User(
                    username=username,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    google_id=google_id,
                    profile_picture=picture,
                    password_hash='',  # No password for OAuth users
                    role='employee',  # Default role
                    is_active=is_active,
                    auth_provider='google',
                    email_verified=True  # Google emails are verified
                )

                db.session.add(user)
                db.session.commit()
                log_action(user.id, 'GOOGLE_ACCOUNT_CREATED')

        # Check if user account is active
        if not user.is_active:
            return redirect('/login?error=account_pending_approval')

        # Update last login
        user.last_login = datetime.utcnow()
        db.session.commit()

        # Create JWT token
        access_token = create_access_token(identity=user.id)

        # Store user info in session for frontend
        session['user_id'] = user.id
        session['access_token'] = access_token

        log_action(user.id, 'GOOGLE_LOGIN_SUCCESS')

        # Redirect to dashboard with token
        return redirect(f'/dashboard?token={access_token}&provider=google')

    except Exception as e:
        print(f"Google OAuth error: {e}")
        return redirect('/login?error=oauth_failed')

@oauth_bp.route('/auth/google/link', methods=['POST'])
def link_google_account():
    """Link existing account with Google OAuth"""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400

    # Verify user credentials
    from werkzeug.security import check_password_hash
    user = User.query.filter_by(username=username).first()

    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({'error': 'Invalid credentials'}), 401

    if user.google_id:
        return jsonify({'error': 'Account already linked to Google'}), 400

    # Store user ID in session for linking after OAuth
    session['link_user_id'] = user.id

    # Return OAuth URL
    redirect_uri = url_for('oauth.google_link_callback', _external=True)
    auth_url = oauth.google.create_authorization_url(redirect_uri)

    return jsonify({'auth_url': auth_url['url']})

@oauth_bp.route('/auth/google/link/callback')
def google_link_callback():
    """Handle Google OAuth callback for account linking"""
    try:
        token = oauth.google.authorize_access_token()
        user_info = token.get('userinfo')

        if not user_info:
            resp = oauth.google.parse_id_token(token)
            user_info = resp

        google_id = user_info.get('sub')
        email = user_info.get('email')

        # Get user to link
        user_id = session.get('link_user_id')
        if not user_id:
            return redirect('/login?error=link_session_expired')

        user = User.query.get(user_id)
        if not user:
            return redirect('/login?error=user_not_found')

        # Check if Google account is already linked to another user
        existing_google_user = User.query.filter_by(google_id=google_id).first()
        if existing_google_user:
            return redirect('/login?error=google_account_already_linked')

        # Link accounts
        user.google_id = google_id
        user.profile_picture = user_info.get('picture', '')

        # Update email if it matches Google email
        if user.email == email:
            user.email_verified = True

        db.session.commit()

        # Clean up session
        session.pop('link_user_id', None)

        log_action(user.id, 'GOOGLE_ACCOUNT_LINKED')

        return redirect('/dashboard?linked=success')

    except Exception as e:
        print(f"Google linking error: {e}")
        return redirect('/login?error=link_failed')

@oauth_bp.route('/auth/unlink/google', methods=['POST'])
def unlink_google_account():
    """Unlink Google account from user"""
    from flask_jwt_extended import jwt_required, get_jwt_identity

    @jwt_required()
    def _unlink():
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user:
            return jsonify({'error': 'User not found'}), 404

        if not user.google_id:
            return jsonify({'error': 'Google account not linked'}), 400

        # Check if user has a password (can't unlink if no other auth method)
        if not user.password_hash:
            return jsonify({
                'error': 'Cannot unlink Google account. Please set a password first.'
            }), 400

        # Unlink account
        user.google_id = None
        user.profile_picture = ''
        db.session.commit()

        log_action(user.id, 'GOOGLE_ACCOUNT_UNLINKED')

        return jsonify({'message': 'Google account unlinked successfully'})

    return _unlink()

@oauth_bp.route('/auth/providers')
def get_auth_providers():
    """Get available OAuth providers"""
    providers = []

    if os.getenv('GOOGLE_CLIENT_ID'):
        providers.append({
            'name': 'google',
            'display_name': 'Google',
            'auth_url': url_for('oauth.google_login', _external=True),
            'icon': 'fab fa-google'
        })

    # Add more providers here (GitHub, Microsoft, etc.)

    return jsonify({'providers': providers})

def get_user_from_oauth_token(provider, token):
    """Get user information from OAuth token"""
    if provider == 'google':
        try:
            # Verify Google token
            response = requests.get(
                f'https://www.googleapis.com/oauth2/v1/userinfo?access_token={token}'
            )

            if response.status_code == 200:
                user_info = response.json()
                google_id = user_info.get('id')

                if google_id:
                    user = User.query.filter_by(google_id=google_id).first()
                    return user

        except Exception as e:
            print(f"Token validation error: {e}")

    return None