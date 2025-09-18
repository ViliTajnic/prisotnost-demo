from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import TimeEntry, User, Project, Geofence
from auth import log_action, validate_geofence, require_role
from app import db
from datetime import datetime, timedelta
import json

time_bp = Blueprint('time', __name__)

@time_bp.route('/api/clock-in', methods=['POST'])
@jwt_required()
def clock_in():
    user_id = get_jwt_identity()
    data = request.get_json()

    existing_entry = TimeEntry.query.filter_by(
        user_id=user_id,
        clock_out_time=None
    ).first()

    if existing_entry:
        return jsonify({'error': 'Already clocked in'}), 400

    latitude = data.get('latitude')
    longitude = data.get('longitude')
    project_id = data.get('project_id')

    if latitude and longitude:
        if not validate_geofence(latitude, longitude, []):
            return jsonify({'error': 'Clock-in location not authorized'}), 403

    time_entry = TimeEntry(
        user_id=user_id,
        clock_in_time=datetime.utcnow(),
        location_lat=latitude,
        location_lon=longitude,
        project_id=project_id,
        notes=data.get('notes', '')
    )

    db.session.add(time_entry)
    db.session.commit()

    log_action(user_id, 'CLOCK_IN', 'time_entries', time_entry.id)

    return jsonify({
        'message': 'Clocked in successfully',
        'entry_id': time_entry.id,
        'clock_in_time': time_entry.clock_in_time.isoformat()
    })

@time_bp.route('/api/clock-out', methods=['POST'])
@jwt_required()
def clock_out():
    user_id = get_jwt_identity()
    data = request.get_json()

    time_entry = TimeEntry.query.filter_by(
        user_id=user_id,
        clock_out_time=None
    ).first()

    if not time_entry:
        return jsonify({'error': 'Not currently clocked in'}), 400

    time_entry.clock_out_time = datetime.utcnow()
    time_entry.break_duration = data.get('break_duration', 0)

    duration = time_entry.clock_out_time - time_entry.clock_in_time
    total_hours = duration.total_seconds() / 3600
    time_entry.total_hours = max(0, total_hours - time_entry.break_duration)

    user = User.query.get(user_id)
    daily_hours = get_daily_hours(user_id, time_entry.clock_in_time.date())

    if daily_hours > 8:
        time_entry.is_overtime = True

    if data.get('notes'):
        time_entry.notes += f"\nClock-out notes: {data.get('notes')}"

    db.session.commit()

    log_action(user_id, 'CLOCK_OUT', 'time_entries', time_entry.id)

    return jsonify({
        'message': 'Clocked out successfully',
        'total_hours': time_entry.total_hours,
        'is_overtime': time_entry.is_overtime
    })

@time_bp.route('/api/break-start', methods=['POST'])
@jwt_required()
def start_break():
    user_id = get_jwt_identity()

    active_entry = TimeEntry.query.filter_by(
        user_id=user_id,
        clock_out_time=None
    ).first()

    if not active_entry:
        return jsonify({'error': 'Not currently clocked in'}), 400

    log_action(user_id, 'BREAK_START', 'time_entries', active_entry.id)

    return jsonify({'message': 'Break started', 'break_start_time': datetime.utcnow().isoformat()})

@time_bp.route('/api/break-end', methods=['POST'])
@jwt_required()
def end_break():
    user_id = get_jwt_identity()
    data = request.get_json()

    active_entry = TimeEntry.query.filter_by(
        user_id=user_id,
        clock_out_time=None
    ).first()

    if not active_entry:
        return jsonify({'error': 'Not currently clocked in'}), 400

    break_duration = data.get('break_duration', 0)
    active_entry.break_duration += break_duration

    db.session.commit()

    log_action(user_id, 'BREAK_END', 'time_entries', active_entry.id)

    return jsonify({'message': 'Break ended', 'total_break_duration': active_entry.break_duration})

@time_bp.route('/api/time-entries')
@jwt_required()
def get_time_entries():
    user_id = get_jwt_identity()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    query = TimeEntry.query.filter_by(user_id=user_id)

    if start_date:
        query = query.filter(TimeEntry.clock_in_time >= datetime.fromisoformat(start_date))
    if end_date:
        query = query.filter(TimeEntry.clock_in_time <= datetime.fromisoformat(end_date))

    entries = query.order_by(TimeEntry.clock_in_time.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        'entries': [{
            'id': entry.id,
            'clock_in_time': entry.clock_in_time.isoformat(),
            'clock_out_time': entry.clock_out_time.isoformat() if entry.clock_out_time else None,
            'total_hours': entry.total_hours,
            'break_duration': entry.break_duration,
            'is_overtime': entry.is_overtime,
            'project_id': entry.project_id,
            'project_name': entry.project.name if entry.project else None,
            'notes': entry.notes,
            'status': entry.status
        } for entry in entries.items],
        'total': entries.total,
        'pages': entries.pages,
        'current_page': entries.page
    })

@time_bp.route('/api/time-entries/<int:entry_id>', methods=['PUT'])
@jwt_required()
@require_role('manager')
def update_time_entry(entry_id):
    user_id = get_jwt_identity()
    data = request.get_json()

    time_entry = TimeEntry.query.get_or_404(entry_id)
    old_values = {
        'clock_in_time': time_entry.clock_in_time.isoformat(),
        'clock_out_time': time_entry.clock_out_time.isoformat() if time_entry.clock_out_time else None,
        'total_hours': time_entry.total_hours,
        'notes': time_entry.notes
    }

    if 'clock_in_time' in data:
        time_entry.clock_in_time = datetime.fromisoformat(data['clock_in_time'])

    if 'clock_out_time' in data:
        time_entry.clock_out_time = datetime.fromisoformat(data['clock_out_time'])

    if 'notes' in data:
        time_entry.notes = data['notes']

    if time_entry.clock_in_time and time_entry.clock_out_time:
        duration = time_entry.clock_out_time - time_entry.clock_in_time
        time_entry.total_hours = max(0, (duration.total_seconds() / 3600) - time_entry.break_duration)

    db.session.commit()

    new_values = {
        'clock_in_time': time_entry.clock_in_time.isoformat(),
        'clock_out_time': time_entry.clock_out_time.isoformat() if time_entry.clock_out_time else None,
        'total_hours': time_entry.total_hours,
        'notes': time_entry.notes
    }

    log_action(user_id, 'UPDATE_TIME_ENTRY', 'time_entries', entry_id, old_values, new_values)

    return jsonify({'message': 'Time entry updated successfully'})

@time_bp.route('/api/current-status')
@jwt_required()
def get_current_status():
    user_id = get_jwt_identity()

    active_entry = TimeEntry.query.filter_by(
        user_id=user_id,
        clock_out_time=None
    ).first()

    if active_entry:
        current_time = datetime.utcnow()
        duration = current_time - active_entry.clock_in_time
        current_hours = duration.total_seconds() / 3600

        return jsonify({
            'status': 'clocked_in',
            'entry_id': active_entry.id,
            'clock_in_time': active_entry.clock_in_time.isoformat(),
            'current_hours': current_hours,
            'project_id': active_entry.project_id,
            'project_name': active_entry.project.name if active_entry.project else None
        })

    return jsonify({'status': 'clocked_out'})

def get_daily_hours(user_id, date):
    start_of_day = datetime.combine(date, datetime.min.time())
    end_of_day = start_of_day + timedelta(days=1)

    entries = TimeEntry.query.filter(
        TimeEntry.user_id == user_id,
        TimeEntry.clock_in_time >= start_of_day,
        TimeEntry.clock_in_time < end_of_day,
        TimeEntry.total_hours.isnot(None)
    ).all()

    return sum(entry.total_hours for entry in entries)

@time_bp.route('/api/weekly-summary')
@jwt_required()
def get_weekly_summary():
    user_id = get_jwt_identity()
    week_start = request.args.get('week_start')

    if week_start:
        start_date = datetime.fromisoformat(week_start).date()
    else:
        today = datetime.now().date()
        start_date = today - timedelta(days=today.weekday())

    end_date = start_date + timedelta(days=6)

    daily_hours = []
    total_hours = 0
    overtime_hours = 0

    for i in range(7):
        current_date = start_date + timedelta(days=i)
        day_hours = get_daily_hours(user_id, current_date)
        daily_hours.append({
            'date': current_date.isoformat(),
            'hours': day_hours,
            'overtime': max(0, day_hours - 8)
        })
        total_hours += day_hours
        overtime_hours += max(0, day_hours - 8)

    return jsonify({
        'week_start': start_date.isoformat(),
        'week_end': end_date.isoformat(),
        'daily_hours': daily_hours,
        'total_hours': total_hours,
        'overtime_hours': overtime_hours,
        'regular_hours': min(total_hours, 40)
    })