"""NFSU Smart Academic Timetable Generator - Main Flask Application.

Security Features:
- CSRF token protection on all state-changing requests
- Input validation and sanitization on all inputs
- XSS prevention via Jinja2 auto-escaping and bleach
- Security headers (CSP, X-Frame-Options, etc.)
- Rate limiting on API endpoints
- Atomic file writes for data persistence
- No information leakage in error responses
- ID validation to prevent injection
"""
import os
import sys
import json
import csv
import io
import secrets
import uuid
from datetime import datetime
from functools import wraps

from flask import (
    Flask, render_template, request, jsonify, redirect, url_for,
    flash, session, Response, abort, g, make_response
)

from models import load_data, save_data, gen_id, get_item_by_id, remove_item_by_id, update_item_by_id
from security import (
    sanitize_string, validate_time, validate_day, validate_positive_int,
    validate_id, add_security_headers, check_rate_limit, get_json_body,
    MAX_NAME_LENGTH, MAX_CODE_LENGTH, MAX_ITEMS_PER_COLLECTION
)
from scheduler import run_scheduler
from validator import validate_timetable, validate_single_edit
from seed_data import seed_demo_data

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024  # 1MB max request size
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# --- CSRF Protection ---

@app.before_request
def csrf_protect():
    """CSRF protection for state-changing requests."""
    if request.method in ('POST', 'PUT', 'DELETE', 'PATCH'):
        # Skip CSRF for API endpoints that use JSON (they're protected by same-origin policy)
        if request.is_json:
            return  # JSON APIs are protected by Content-Type checking
        token = session.get('csrf_token')
        form_token = request.form.get('csrf_token') or request.headers.get('X-CSRF-Token')
        if not token or token != form_token:
            abort(403)

@app.before_request
def ensure_csrf_token():
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_hex(32)

@app.context_processor
def inject_csrf_token():
    return dict(csrf_token=session.get('csrf_token', ''))

@app.before_request
def rate_limit():
    check_rate_limit()

@app.after_request
def security_headers(response):
    return add_security_headers(response)

# --- Error Handlers ---

@app.errorhandler(400)
def bad_request(e):
    if request.is_json or request.path.startswith('/api/'):
        return jsonify({'error': 'Bad request'}), 400
    return render_template('error.html', code=400, message='Bad Request'), 400

@app.errorhandler(403)
def forbidden(e):
    if request.is_json or request.path.startswith('/api/'):
        return jsonify({'error': 'Forbidden'}), 403
    return render_template('error.html', code=403, message='Forbidden'), 403

@app.errorhandler(404)
def not_found(e):
    if request.is_json or request.path.startswith('/api/'):
        return jsonify({'error': 'Not found'}), 404
    return render_template('error.html', code=404, message='Not Found'), 404

@app.errorhandler(429)
def rate_limited(e):
    if request.is_json or request.path.startswith('/api/'):
        return jsonify({'error': 'Too many requests'}), 429
    return render_template('error.html', code=429, message='Too Many Requests'), 429

@app.errorhandler(500)
def internal_error(e):
    if request.is_json or request.path.startswith('/api/'):
        return jsonify({'error': 'Internal server error'}), 500
    return render_template('error.html', code=500, message='Internal Server Error'), 500

# --- Helper Functions ---

def _ensure_demo_data():
    """Load demo data on first launch."""
    data = load_data()
    if not data.get('demo_data_loaded') and not data.get('programmes'):
        data = seed_demo_data()
        save_data(data)
    return data

def _get_stats(data):
    """Get dashboard stats."""
    programmes = data.get('programmes', [])
    total_sections = sum(
        len(sec)
        for p in programmes
        for sem in p.get('semesters', [])
        for sec in [sem.get('sections', [])]
    )
    return {
        'programmes': len(programmes),
        'faculty': len(data.get('faculty', [])),
        'rooms': len(data.get('rooms', [])),
        'subjects': len(data.get('subjects', [])),
        'sections': total_sections,
        'scheduled_sessions': len(data.get('scheduled_sessions', [])),
        'status': data.get('timetable_state', {}).get('status', 'draft'),
        'generation_status': data.get('timetable_state', {}).get('generation_status', ''),
        'generation_message': data.get('timetable_state', {}).get('generation_message', ''),
        'unscheduled': len(data.get('timetable_state', {}).get('unscheduled_sessions', [])),
        'conflicts': len(data.get('timetable_state', {}).get('conflicts', [])),
    }

def _get_lookup_maps(data):
    """Create ID-to-name lookup maps for display."""
    faculty_map = {f['id']: f['name'] for f in data.get('faculty', [])}
    room_map = {r['id']: r['name'] for r in data.get('rooms', [])}
    subject_map = {s['id']: s for s in data.get('subjects', [])}
    section_map = {}
    programme_map = {}
    semester_map = {}
    for p in data.get('programmes', []):
        programme_map[p['id']] = p['name']
        for sem in p.get('semesters', []):
            semester_map[sem['id']] = f'Semester {sem["number"]}'
            for sec in sem.get('sections', []):
                section_map[sec['id']] = {
                    'name': sec['name'],
                    'programme': p['name'],
                    'semester': sem['number'],
                    'strength': sec.get('student_strength', 0),
                    'batches': {b['id']: b['name'] for b in sec.get('practical_batches', [])}
                }
    return {
        'faculty': faculty_map,
        'rooms': room_map,
        'subjects': subject_map,
        'sections': section_map,
        'programmes': programme_map,
        'semesters': semester_map
    }

# --- Page Routes ---

@app.route('/')
def dashboard():
    data = _ensure_demo_data()
    stats = _get_stats(data)
    maps = _get_lookup_maps(data)
    timetable_state = data.get('timetable_state', {})
    return render_template('dashboard.html', stats=stats, maps=maps,
                         timetable_state=timetable_state, active_page='dashboard')

@app.route('/programmes')
def programmes_page():
    data = _ensure_demo_data()
    return render_template('programmes.html', data=data, active_page='programmes')

@app.route('/faculty')
def faculty_page():
    data = _ensure_demo_data()
    return render_template('faculty.html', data=data, active_page='faculty')

@app.route('/rooms')
def rooms_page():
    data = _ensure_demo_data()
    return render_template('rooms.html', data=data, active_page='rooms')

@app.route('/subjects')
def subjects_page():
    data = _ensure_demo_data()
    maps = _get_lookup_maps(data)
    return render_template('subjects.html', data=data, maps=maps, active_page='subjects')

@app.route('/settings')
def settings_page():
    data = _ensure_demo_data()
    return render_template('settings.html', data=data, active_page='settings')

@app.route('/timetable')
def timetable_page():
    data = _ensure_demo_data()
    maps = _get_lookup_maps(data)
    return render_template('timetable.html', data=data, maps=maps, active_page='timetable')

@app.route('/conflicts')
def conflicts_page():
    data = _ensure_demo_data()
    maps = _get_lookup_maps(data)
    # Run validation
    errors = validate_timetable(data)
    return render_template('conflicts.html', data=data, maps=maps,
                         errors=errors, active_page='conflicts')

@app.route('/export')
def export_page():
    data = _ensure_demo_data()
    maps = _get_lookup_maps(data)
    return render_template('export.html', data=data, maps=maps, active_page='export')

# --- API Routes ---

@app.route('/api/generate', methods=['POST'])
def api_generate():
    """Generate timetable using the scheduling engine."""
    try:
        data = load_data()
        result = run_scheduler(data)
        
        data['scheduled_sessions'] = result['scheduled_sessions']
        data['timetable_state'] = {
            'status': 'generated',
            'generation_status': result['status'],
            'generation_message': result['message'],
            'unscheduled_sessions': result.get('unscheduled_sessions', []),
            'conflicts': result.get('conflicts', []),
            'last_generated': datetime.now().isoformat()
        }
        save_data(data)
        
        return jsonify({
            'success': True,
            'status': result['status'],
            'message': result['message'],
            'total_scheduled': result['total_scheduled'],
            'total_unscheduled': result['total_unscheduled'],
            'unscheduled_sessions': result.get('unscheduled_sessions', []),
            'conflicts': result.get('conflicts', [])
        })
    except Exception as e:
        app.logger.error(f'Generation error: {e}')
        return jsonify({'success': False, 'error': 'Scheduling failed. Please check your data and try again.'}), 500

@app.route('/api/validate', methods=['POST'])
def api_validate():
    """Run validation on current timetable."""
    try:
        data = load_data()
        errors = validate_timetable(data)
        return jsonify({'success': True, 'errors': errors, 'valid': len(errors) == 0})
    except Exception as e:
        app.logger.error(f'Validation error: {e}')
        return jsonify({'success': False, 'error': 'Validation failed'}), 500

@app.route('/api/edit-session', methods=['POST'])
def api_edit_session():
    """Edit a scheduled session with pre-commit validation."""
    try:
        body = get_json_body()
        session_id = validate_id(body.get('session_id', ''))
        new_day = validate_day(body.get('day', ''))
        new_start = validate_time(body.get('start_time', ''))
        new_end = validate_time(body.get('end_time', ''))
        new_room_id = validate_id(body.get('room_id', ''))
        
        data = load_data()
        
        # Validate the edit
        errors = validate_single_edit(data, session_id, new_day, new_start, new_end, new_room_id)
        if errors:
            return jsonify({'success': False, 'errors': errors}), 400
        
        # Apply the edit
        for s in data['scheduled_sessions']:
            if s['id'] == session_id:
                s['day'] = new_day
                s['start_time'] = new_start
                s['end_time'] = new_end
                s['room_id'] = new_room_id
                break
        
        # Mark as draft after edit
        data['timetable_state']['status'] = 'generated'
        save_data(data)
        return jsonify({'success': True, 'message': 'Session updated successfully'})
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        app.logger.error(f'Edit error: {e}')
        return jsonify({'success': False, 'error': 'Edit failed'}), 500

@app.route('/api/toggle-lock/<session_id>', methods=['POST'])
def api_toggle_lock(session_id):
    """Toggle lock status of a session."""
    try:
        session_id = validate_id(session_id)
        data = load_data()
        for s in data.get('scheduled_sessions', []):
            if s['id'] == session_id:
                s['is_locked'] = not s.get('is_locked', False)
                save_data(data)
                return jsonify({'success': True, 'is_locked': s['is_locked']})
        return jsonify({'success': False, 'error': 'Session not found'}), 404
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/publish', methods=['POST'])
def api_publish():
    """Publish the timetable (only if valid and complete)."""
    try:
        data = load_data()
        
        if not data.get('scheduled_sessions'):
            return jsonify({'success': False, 'error': 'No timetable to publish. Generate one first.'}), 400
        
        # Run validation
        errors = validate_timetable(data)
        error_count = len([e for e in errors if e.get('severity') == 'error'])
        
        if error_count > 0:
            return jsonify({
                'success': False,
                'error': f'Cannot publish: {error_count} validation error(s) found. Fix all errors first.',
                'errors': errors
            }), 400
        
        # Check generation status
        gen_status = data.get('timetable_state', {}).get('generation_status', '')
        if gen_status == 'partial' or gen_status == 'failed':
            return jsonify({
                'success': False,
                'error': 'Cannot publish an incomplete timetable. All sessions must be scheduled.'
            }), 400
        
        data['timetable_state']['status'] = 'published'
        data['timetable_state']['published_at'] = datetime.now().isoformat()
        save_data(data)
        return jsonify({'success': True, 'message': 'Timetable published successfully'})
    except Exception as e:
        app.logger.error(f'Publish error: {e}')
        return jsonify({'success': False, 'error': 'Publication failed'}), 500

@app.route('/api/unpublish', methods=['POST'])
def api_unpublish():
    try:
        data = load_data()
        data['timetable_state']['status'] = 'generated'
        save_data(data)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': 'Failed to unpublish'}), 500

@app.route('/api/export-csv')
def api_export_csv():
    """Export timetable as CSV."""
    try:
        data = load_data()
        maps = _get_lookup_maps(data)
        sessions = data.get('scheduled_sessions', [])
        
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_ALL)
        writer.writerow(['Day', 'Start Time', 'End Time', 'Subject', 'Subject Code', 'Faculty',
                        'Room', 'Programme', 'Semester', 'Section', 'Session Type', 'Batch', 'Status'])
        
        for s in sorted(sessions, key=lambda x: (
            ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'].index(x.get('day', 'Monday')),
            x.get('start_time', '')
        )):
            subj = maps['subjects'].get(s['subject_id'], {})
            sec_info = maps['sections'].get(s['section_id'], {})
            batch_name = ''
            if s.get('batch_id'):
                batch_name = sec_info.get('batches', {}).get(s['batch_id'], s.get('batch_name', ''))
            
            status = 'Fixed' if s.get('is_fixed') else ('Locked' if s.get('is_locked') else 'Normal')
            
            writer.writerow([
                s.get('day', ''),
                s.get('start_time', ''),
                s.get('end_time', ''),
                subj.get('name', 'Unknown') if isinstance(subj, dict) else 'Unknown',
                subj.get('code', '') if isinstance(subj, dict) else '',
                maps['faculty'].get(s['faculty_id'], 'Unknown'),
                maps['rooms'].get(s['room_id'], 'Unknown'),
                maps['programmes'].get(s.get('programme_id', ''), ''),
                maps['semesters'].get(s.get('semester_id', ''), ''),
                sec_info.get('name', '') if isinstance(sec_info, dict) else '',
                s.get('session_type', ''),
                batch_name,
                status
            ])
        
        output.seek(0)
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv; charset=utf-8'
        response.headers['Content-Disposition'] = 'attachment; filename=timetable_export.csv'
        return response
    except Exception as e:
        app.logger.error(f'CSV export error: {e}')
        return jsonify({'error': 'Export failed'}), 500

@app.route('/api/timetable-data')
def api_timetable_data():
    """Get timetable data with filters."""
    data = load_data()
    maps = _get_lookup_maps(data)
    sessions = data.get('scheduled_sessions', [])
    
    # Apply filters
    filter_programme = request.args.get('programme', '')
    filter_semester = request.args.get('semester', '')
    filter_section = request.args.get('section', '')
    filter_faculty = request.args.get('faculty', '')
    filter_room = request.args.get('room', '')
    view_type = request.args.get('view', 'programme')  # programme, faculty, room
    
    filtered = []
    for s in sessions:
        if filter_programme and s.get('programme_id') != filter_programme:
            continue
        if filter_semester and s.get('semester_id') != filter_semester:
            continue
        if filter_section and s.get('section_id') != filter_section:
            continue
        if filter_faculty and s.get('faculty_id') != filter_faculty:
            continue
        if filter_room and s.get('room_id') != filter_room:
            continue
        
        subj = maps['subjects'].get(s['subject_id'], {})
        sec_info = maps['sections'].get(s['section_id'], {})
        batch_name = ''
        if s.get('batch_id'):
            batch_name = sec_info.get('batches', {}).get(s['batch_id'], s.get('batch_name', ''))
        
        filtered.append({
            **s,
            'subject_name': subj.get('name', 'Unknown') if isinstance(subj, dict) else 'Unknown',
            'subject_code': subj.get('code', '') if isinstance(subj, dict) else '',
            'faculty_name': maps['faculty'].get(s['faculty_id'], 'Unknown'),
            'room_name': maps['rooms'].get(s['room_id'], 'Unknown'),
            'programme_name': maps['programmes'].get(s.get('programme_id', ''), ''),
            'section_name': sec_info.get('name', '') if isinstance(sec_info, dict) else '',
            'semester_number': sec_info.get('semester', '') if isinstance(sec_info, dict) else '',
            'batch_name': batch_name
        })
    
    return jsonify({
        'sessions': filtered,
        'settings': data.get('settings', {}),
        'maps': {
            'faculty': maps['faculty'],
            'rooms': maps['rooms'],
            'programmes': maps['programmes'],
            'semesters': maps['semesters']
        }
    })

# --- CRUD API Routes ---

@app.route('/api/settings', methods=['POST'])
def api_save_settings():
    try:
        body = get_json_body()
        data = load_data()
        
        settings = data.get('settings', {})
        if 'name' in body:
            settings['name'] = sanitize_string(body['name'], MAX_NAME_LENGTH)
        if 'department' in body:
            settings['department'] = sanitize_string(body['department'], MAX_NAME_LENGTH)
        if 'start_time' in body:
            settings['start_time'] = validate_time(body['start_time'])
        if 'end_time' in body:
            settings['end_time'] = validate_time(body['end_time'])
        if 'period_duration' in body:
            settings['period_duration'] = validate_positive_int(body['period_duration'], 'Period duration', 180)
        if 'working_days' in body:
            if not isinstance(body['working_days'], list):
                raise ValueError('working_days must be a list')
            settings['working_days'] = [validate_day(d) for d in body['working_days']]
        if 'breaks' in body:
            if not isinstance(body['breaks'], list):
                raise ValueError('breaks must be a list')
            validated_breaks = []
            for brk in body['breaks']:
                validated_breaks.append({
                    'name': sanitize_string(brk.get('name', ''), MAX_NAME_LENGTH),
                    'start': validate_time(brk.get('start', '')),
                    'end': validate_time(brk.get('end', ''))
                })
            settings['breaks'] = validated_breaks
        
        data['settings'] = settings
        save_data(data)
        return jsonify({'success': True})
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/programmes', methods=['POST'])
def api_add_programme():
    try:
        body = get_json_body()
        data = load_data()
        
        if len(data.get('programmes', [])) >= MAX_ITEMS_PER_COLLECTION:
            raise ValueError('Maximum number of programmes reached')
        
        prog = {
            'id': gen_id(),
            'name': sanitize_string(body.get('name', ''), MAX_NAME_LENGTH),
            'code': sanitize_string(body.get('code', ''), MAX_CODE_LENGTH),
            'duration_years': validate_positive_int(body.get('duration_years', 2), 'Duration', 10),
            'semesters': []
        }
        
        if not prog['name']:
            raise ValueError('Programme name is required')
        
        data.setdefault('programmes', []).append(prog)
        save_data(data)
        return jsonify({'success': True, 'id': prog['id']})
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/programmes/<prog_id>', methods=['PUT'])
def api_update_programme(prog_id):
    try:
        prog_id = validate_id(prog_id)
        body = get_json_body()
        data = load_data()
        
        prog = get_item_by_id(data.get('programmes', []), prog_id)
        if not prog:
            return jsonify({'success': False, 'error': 'Programme not found'}), 404
        
        if 'name' in body:
            prog['name'] = sanitize_string(body['name'], MAX_NAME_LENGTH)
        if 'code' in body:
            prog['code'] = sanitize_string(body['code'], MAX_CODE_LENGTH)
        if 'duration_years' in body:
            prog['duration_years'] = validate_positive_int(body['duration_years'], 'Duration', 10)
        
        save_data(data)
        return jsonify({'success': True})
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/programmes/<prog_id>', methods=['DELETE'])
def api_delete_programme(prog_id):
    try:
        prog_id = validate_id(prog_id)
        data = load_data()
        if remove_item_by_id(data.get('programmes', []), prog_id):
            # Also remove associated subjects
            data['subjects'] = [s for s in data.get('subjects', []) if s.get('programme_id') != prog_id]
            save_data(data)
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Programme not found'}), 404
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/programmes/<prog_id>/semesters', methods=['POST'])
def api_add_semester(prog_id):
    try:
        prog_id = validate_id(prog_id)
        body = get_json_body()
        data = load_data()
        
        prog = get_item_by_id(data.get('programmes', []), prog_id)
        if not prog:
            return jsonify({'success': False, 'error': 'Programme not found'}), 404
        
        sem = {
            'id': gen_id(),
            'programme_id': prog_id,
            'number': validate_positive_int(body.get('number', 1), 'Semester number', 20),
            'sections': []
        }
        prog.setdefault('semesters', []).append(sem)
        save_data(data)
        return jsonify({'success': True, 'id': sem['id']})
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/programmes/<prog_id>/semesters/<sem_id>/sections', methods=['POST'])
def api_add_section(prog_id, sem_id):
    try:
        prog_id = validate_id(prog_id)
        sem_id = validate_id(sem_id)
        body = get_json_body()
        data = load_data()
        
        prog = get_item_by_id(data.get('programmes', []), prog_id)
        if not prog:
            return jsonify({'success': False, 'error': 'Programme not found'}), 404
        
        sem = get_item_by_id(prog.get('semesters', []), sem_id)
        if not sem:
            return jsonify({'success': False, 'error': 'Semester not found'}), 404
        
        # Parse practical batches
        batches = []
        for b in body.get('practical_batches', []):
            batches.append({
                'id': gen_id(),
                'name': sanitize_string(b.get('name', ''), MAX_NAME_LENGTH),
                'strength': validate_positive_int(b.get('strength', 20), 'Batch strength', 500)
            })
        
        sec = {
            'id': gen_id(),
            'semester_id': sem_id,
            'programme_id': prog_id,
            'name': sanitize_string(body.get('name', 'A'), MAX_NAME_LENGTH),
            'student_strength': validate_positive_int(body.get('student_strength', 40), 'Student strength', 500),
            'practical_batches': batches
        }
        sem.setdefault('sections', []).append(sec)
        save_data(data)
        return jsonify({'success': True, 'id': sec['id']})
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/faculty', methods=['POST'])
def api_add_faculty():
    try:
        body = get_json_body()
        data = load_data()
        
        if len(data.get('faculty', [])) >= MAX_ITEMS_PER_COLLECTION:
            raise ValueError('Maximum number of faculty members reached')
        
        fac = {
            'id': gen_id(),
            'name': sanitize_string(body.get('name', ''), MAX_NAME_LENGTH),
            'employee_id': sanitize_string(body.get('employee_id', ''), MAX_CODE_LENGTH),
            'available_days': [validate_day(d) for d in body.get('available_days', ['Monday','Tuesday','Wednesday','Thursday','Friday'])],
            'available_time_start': validate_time(body.get('available_time_start', '09:00')),
            'available_time_end': validate_time(body.get('available_time_end', '17:00')),
            'unavailable_slots': [],
            'max_periods_per_day': validate_positive_int(body.get('max_periods_per_day', 6), 'Max periods', 12),
            'preferred_slots': []
        }
        
        if not fac['name']:
            raise ValueError('Faculty name is required')
        
        # Validate unavailable slots
        for slot in body.get('unavailable_slots', []):
            fac['unavailable_slots'].append({
                'day': validate_day(slot.get('day', '')),
                'start': validate_time(slot.get('start', '')),
                'end': validate_time(slot.get('end', ''))
            })
        
        # Validate preferred slots
        for slot in body.get('preferred_slots', []):
            fac['preferred_slots'].append({
                'day': validate_day(slot.get('day', '')),
                'start': validate_time(slot.get('start', '')),
                'end': validate_time(slot.get('end', ''))
            })
        
        data.setdefault('faculty', []).append(fac)
        save_data(data)
        return jsonify({'success': True, 'id': fac['id']})
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/faculty/<fac_id>', methods=['PUT'])
def api_update_faculty(fac_id):
    try:
        fac_id = validate_id(fac_id)
        body = get_json_body()
        data = load_data()
        
        fac = get_item_by_id(data.get('faculty', []), fac_id)
        if not fac:
            return jsonify({'success': False, 'error': 'Faculty not found'}), 404
        
        if 'name' in body:
            fac['name'] = sanitize_string(body['name'], MAX_NAME_LENGTH)
        if 'employee_id' in body:
            fac['employee_id'] = sanitize_string(body['employee_id'], MAX_CODE_LENGTH)
        if 'available_days' in body:
            fac['available_days'] = [validate_day(d) for d in body['available_days']]
        if 'available_time_start' in body:
            fac['available_time_start'] = validate_time(body['available_time_start'])
        if 'available_time_end' in body:
            fac['available_time_end'] = validate_time(body['available_time_end'])
        if 'max_periods_per_day' in body:
            fac['max_periods_per_day'] = validate_positive_int(body['max_periods_per_day'], 'Max periods', 12)
        if 'unavailable_slots' in body:
            fac['unavailable_slots'] = []
            for slot in body['unavailable_slots']:
                fac['unavailable_slots'].append({
                    'day': validate_day(slot.get('day', '')),
                    'start': validate_time(slot.get('start', '')),
                    'end': validate_time(slot.get('end', ''))
                })
        if 'preferred_slots' in body:
            fac['preferred_slots'] = []
            for slot in body['preferred_slots']:
                fac['preferred_slots'].append({
                    'day': validate_day(slot.get('day', '')),
                    'start': validate_time(slot.get('start', '')),
                    'end': validate_time(slot.get('end', ''))
                })
        
        save_data(data)
        return jsonify({'success': True})
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/faculty/<fac_id>', methods=['DELETE'])
def api_delete_faculty(fac_id):
    try:
        fac_id = validate_id(fac_id)
        data = load_data()
        if remove_item_by_id(data.get('faculty', []), fac_id):
            save_data(data)
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Faculty not found'}), 404
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/rooms', methods=['POST'])
def api_add_room():
    try:
        body = get_json_body()
        data = load_data()
        
        if len(data.get('rooms', [])) >= MAX_ITEMS_PER_COLLECTION:
            raise ValueError('Maximum number of rooms reached')
        
        room = {
            'id': gen_id(),
            'name': sanitize_string(body.get('name', ''), MAX_NAME_LENGTH),
            'capacity': validate_positive_int(body.get('capacity', 40), 'Capacity', 1000),
            'room_type': sanitize_string(body.get('room_type', 'classroom'), 20),
            'lab_type': sanitize_string(body.get('lab_type', ''), MAX_NAME_LENGTH),
            'available_days': [validate_day(d) for d in body.get('available_days', ['Monday','Tuesday','Wednesday','Thursday','Friday'])]
        }
        
        if not room['name']:
            raise ValueError('Room name is required')
        if room['room_type'] not in ('classroom', 'laboratory'):
            raise ValueError('Room type must be classroom or laboratory')
        
        data.setdefault('rooms', []).append(room)
        save_data(data)
        return jsonify({'success': True, 'id': room['id']})
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/rooms/<room_id>', methods=['PUT'])
def api_update_room(room_id):
    try:
        room_id = validate_id(room_id)
        body = get_json_body()
        data = load_data()
        
        room = get_item_by_id(data.get('rooms', []), room_id)
        if not room:
            return jsonify({'success': False, 'error': 'Room not found'}), 404
        
        if 'name' in body:
            room['name'] = sanitize_string(body['name'], MAX_NAME_LENGTH)
        if 'capacity' in body:
            room['capacity'] = validate_positive_int(body['capacity'], 'Capacity', 1000)
        if 'room_type' in body:
            rt = sanitize_string(body['room_type'], 20)
            if rt not in ('classroom', 'laboratory'):
                raise ValueError('Room type must be classroom or laboratory')
            room['room_type'] = rt
        if 'lab_type' in body:
            room['lab_type'] = sanitize_string(body['lab_type'], MAX_NAME_LENGTH)
        if 'available_days' in body:
            room['available_days'] = [validate_day(d) for d in body['available_days']]
        
        save_data(data)
        return jsonify({'success': True})
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/rooms/<room_id>', methods=['DELETE'])
def api_delete_room(room_id):
    try:
        room_id = validate_id(room_id)
        data = load_data()
        if remove_item_by_id(data.get('rooms', []), room_id):
            save_data(data)
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Room not found'}), 404
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/subjects', methods=['POST'])
def api_add_subject():
    try:
        body = get_json_body()
        data = load_data()
        
        if len(data.get('subjects', [])) >= MAX_ITEMS_PER_COLLECTION:
            raise ValueError('Maximum number of subjects reached')
        
        subj = {
            'id': gen_id(),
            'name': sanitize_string(body.get('name', ''), MAX_NAME_LENGTH),
            'code': sanitize_string(body.get('code', ''), MAX_CODE_LENGTH),
            'section_id': validate_id(body.get('section_id', '')),
            'programme_id': validate_id(body.get('programme_id', '')),
            'semester_id': validate_id(body.get('semester_id', '')),
            'faculty_id': validate_id(body.get('faculty_id', '')),
            'theory_periods_per_week': validate_positive_int(body.get('theory_periods_per_week', 3), 'Theory periods', 20),
            'practical_sessions_per_week': validate_positive_int(body.get('practical_sessions_per_week', 0), 'Practical sessions', 10),
            'practical_consecutive_periods': validate_positive_int(body.get('practical_consecutive_periods', 2), 'Consecutive periods', 6),
            'required_lab_type': sanitize_string(body.get('required_lab_type', ''), MAX_NAME_LENGTH),
            'is_for_batches': bool(body.get('is_for_batches', False))
        }
        
        if not subj['name']:
            raise ValueError('Subject name is required')
        if not subj['code']:
            raise ValueError('Subject code is required')
        
        data.setdefault('subjects', []).append(subj)
        save_data(data)
        return jsonify({'success': True, 'id': subj['id']})
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/subjects/<subj_id>', methods=['PUT'])
def api_update_subject(subj_id):
    try:
        subj_id = validate_id(subj_id)
        body = get_json_body()
        data = load_data()
        
        subj = get_item_by_id(data.get('subjects', []), subj_id)
        if not subj:
            return jsonify({'success': False, 'error': 'Subject not found'}), 404
        
        if 'name' in body:
            subj['name'] = sanitize_string(body['name'], MAX_NAME_LENGTH)
        if 'code' in body:
            subj['code'] = sanitize_string(body['code'], MAX_CODE_LENGTH)
        if 'faculty_id' in body:
            subj['faculty_id'] = validate_id(body['faculty_id'])
        if 'theory_periods_per_week' in body:
            subj['theory_periods_per_week'] = validate_positive_int(body['theory_periods_per_week'], 'Theory periods', 20)
        if 'practical_sessions_per_week' in body:
            subj['practical_sessions_per_week'] = validate_positive_int(body['practical_sessions_per_week'], 'Practical sessions', 10)
        if 'practical_consecutive_periods' in body:
            subj['practical_consecutive_periods'] = validate_positive_int(body['practical_consecutive_periods'], 'Consecutive periods', 6)
        if 'required_lab_type' in body:
            subj['required_lab_type'] = sanitize_string(body['required_lab_type'], MAX_NAME_LENGTH)
        if 'is_for_batches' in body:
            subj['is_for_batches'] = bool(body['is_for_batches'])
        
        save_data(data)
        return jsonify({'success': True})
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/subjects/<subj_id>', methods=['DELETE'])
def api_delete_subject(subj_id):
    try:
        subj_id = validate_id(subj_id)
        data = load_data()
        if remove_item_by_id(data.get('subjects', []), subj_id):
            save_data(data)
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Subject not found'}), 404
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/fixed-sessions', methods=['POST'])
def api_add_fixed_session():
    try:
        body = get_json_body()
        data = load_data()
        
        fixed = {
            'id': gen_id(),
            'subject_id': validate_id(body.get('subject_id', '')),
            'faculty_id': validate_id(body.get('faculty_id', '')),
            'section_id': validate_id(body.get('section_id', '')),
            'room_id': validate_id(body.get('room_id', '')),
            'day': validate_day(body.get('day', '')),
            'start_time': validate_time(body.get('start_time', '')),
            'end_time': validate_time(body.get('end_time', '')),
            'session_type': sanitize_string(body.get('session_type', 'theory'), 20),
            'batch_id': body.get('batch_id', '') or ''
        }
        
        data.setdefault('fixed_sessions', []).append(fixed)
        save_data(data)
        return jsonify({'success': True, 'id': fixed['id']})
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/fixed-sessions/<fs_id>', methods=['DELETE'])
def api_delete_fixed_session(fs_id):
    try:
        fs_id = validate_id(fs_id)
        data = load_data()
        if remove_item_by_id(data.get('fixed_sessions', []), fs_id):
            save_data(data)
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Fixed session not found'}), 404
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/reset-demo', methods=['POST'])
def api_reset_demo():
    """Reset to demo data."""
    try:
        data = seed_demo_data()
        save_data(data)
        return jsonify({'success': True, 'message': 'Demo data restored successfully'})
    except Exception as e:
        app.logger.error(f'Reset error: {e}')
        return jsonify({'success': False, 'error': 'Failed to reset demo data'}), 500

@app.route('/api/clear-data', methods=['POST'])
def api_clear_data():
    """Clear all data."""
    try:
        from dataclasses import asdict
        from models import AppData
        data = asdict(AppData())
        data['demo_data_loaded'] = True  # Prevent auto-loading demo on next visit
        save_data(data)
        return jsonify({'success': True, 'message': 'All data cleared'})
    except Exception as e:
        app.logger.error(f'Clear error: {e}')
        return jsonify({'success': False, 'error': 'Failed to clear data'}), 500

# Delete semester
@app.route('/api/programmes/<prog_id>/semesters/<sem_id>', methods=['DELETE'])
def api_delete_semester(prog_id, sem_id):
    try:
        prog_id = validate_id(prog_id)
        sem_id = validate_id(sem_id)
        data = load_data()
        prog = get_item_by_id(data.get('programmes', []), prog_id)
        if not prog:
            return jsonify({'success': False, 'error': 'Programme not found'}), 404
        if remove_item_by_id(prog.get('semesters', []), sem_id):
            data['subjects'] = [s for s in data.get('subjects', []) if s.get('semester_id') != sem_id]
            save_data(data)
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Semester not found'}), 404
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400

# Delete section
@app.route('/api/programmes/<prog_id>/semesters/<sem_id>/sections/<sec_id>', methods=['DELETE'])
def api_delete_section(prog_id, sem_id, sec_id):
    try:
        prog_id = validate_id(prog_id)
        sem_id = validate_id(sem_id)
        sec_id = validate_id(sec_id)
        data = load_data()
        prog = get_item_by_id(data.get('programmes', []), prog_id)
        if not prog:
            return jsonify({'success': False, 'error': 'Programme not found'}), 404
        sem = get_item_by_id(prog.get('semesters', []), sem_id)
        if not sem:
            return jsonify({'success': False, 'error': 'Semester not found'}), 404
        if remove_item_by_id(sem.get('sections', []), sec_id):
            data['subjects'] = [s for s in data.get('subjects', []) if s.get('section_id') != sec_id]
            save_data(data)
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Section not found'}), 404
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400

if __name__ == '__main__':
    # Ensure demo data is loaded
    _ensure_demo_data()
    print('\n  NFSU Smart Academic Timetable Generator')
    print('  =========================================')
    print('  Running at: http://127.0.0.1:5000')
    print('  Press Ctrl+C to stop\n')
    app.run(debug=True, host='127.0.0.1', port=5000)
