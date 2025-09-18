from functools import wraps
from flask import request, jsonify, current_app
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from models import User, AuditLog
from app import db
import bcrypt

def require_role(required_role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            verify_jwt_in_request()
            user_id = get_jwt_identity()
            user = User.query.get(user_id)

            if not user or not user.is_active:
                return jsonify({'error': 'User not found or inactive'}), 401

            role_hierarchy = {
                'employee': 1,
                'manager': 2,
                'hr': 3,
                'admin': 4
            }

            user_level = role_hierarchy.get(user.role, 0)
            required_level = role_hierarchy.get(required_role, 5)

            if user_level < required_level:
                return jsonify({'error': 'Insufficient permissions'}), 403

            return f(*args, **kwargs)
        return decorated_function
    return decorator

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_password(password, hashed_password):
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

def log_action(user_id, action, table_name=None, record_id=None, old_values=None, new_values=None):
    try:
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            table_name=table_name,
            record_id=record_id,
            old_values=str(old_values) if old_values else None,
            new_values=str(new_values) if new_values else None,
            ip_address=request.remote_addr if request else None,
            user_agent=request.headers.get('User-Agent') if request else None
        )
        db.session.add(audit_log)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(f"Failed to log action: {e}")

def validate_geofence(latitude, longitude, allowed_geofences):
    from models import Geofence
    import math

    if not latitude or not longitude:
        return False

    active_geofences = Geofence.query.filter_by(is_active=True).all()

    for geofence in active_geofences:
        distance = calculate_distance(
            latitude, longitude,
            geofence.center_lat, geofence.center_lon
        )

        if distance <= geofence.radius:
            return True

    return False

def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371000

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = (math.sin(delta_lat / 2) * math.sin(delta_lat / 2) +
         math.cos(lat1_rad) * math.cos(lat2_rad) *
         math.sin(delta_lon / 2) * math.sin(delta_lon / 2))

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c