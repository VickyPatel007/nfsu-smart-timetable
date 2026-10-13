"""Timetable validation engine for NFSU Smart Academic Timetable Generator.

Re-usable validation that runs after generation, after manual edits, and before publication.
Returns structured error objects with affected session, day, time, resource, and human-readable explanation.
"""

from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple, Union

# Attempt import from scheduler; provide robust fallbacks if scheduler is not yet available
try:
    from scheduler import generate_time_slots, is_faculty_available, time_to_minutes, times_overlap
except ImportError:
    try:
        from .scheduler import generate_time_slots, is_faculty_available, time_to_minutes, times_overlap
    except ImportError:
        def time_to_minutes(time_str: str) -> int:
            """Convert 'HH:MM' string to minutes from midnight."""
            if not time_str or not isinstance(time_str, str) or ':' not in time_str:
                return 0
            try:
                parts = time_str.strip().split(':')
                return int(parts[0]) * 60 + int(parts[1])
            except (ValueError, IndexError):
                return 0

        def times_overlap(start1: str, end1: str, start2: str, end2: str) -> bool:
            """Check if two time intervals overlap (half-open [start, end))."""
            s1 = time_to_minutes(start1)
            e1 = time_to_minutes(end1)
            s2 = time_to_minutes(start2)
            e2 = time_to_minutes(end2)
            return max(s1, s2) < min(e1, e2)

        def is_faculty_available(faculty: dict, day: str, start_time: str, end_time: str) -> bool:
            """Check if a faculty member is available on given day and time range."""
            if not faculty:
                return False

            avail_days = faculty.get('available_days')
            if avail_days is not None and isinstance(avail_days, (list, tuple, set)):
                if day not in avail_days:
                    return False

            unavail = faculty.get('unavailable_slots') or faculty.get('unavailability') or []
            if isinstance(unavail, list):
                for slot in unavail:
                    if isinstance(slot, dict) and slot.get('day') == day:
                        slot_start = slot.get('start') or slot.get('start_time', '')
                        slot_end = slot.get('end') or slot.get('end_time', '')
                        if slot_start and slot_end and times_overlap(start_time, end_time, slot_start, slot_end):
                            return False

            avail_map = faculty.get('availability')
            if isinstance(avail_map, dict):
                day_avail = avail_map.get(day)
                if day_avail is False:
                    return False
                if isinstance(day_avail, list):
                    req_start = time_to_minutes(start_time)
                    req_end = time_to_minutes(end_time)
                    in_any_slot = False
                    for slot in day_avail:
                        if isinstance(slot, dict):
                            s_str = slot.get('start') or slot.get('start_time', '')
                            e_str = slot.get('end') or slot.get('end_time', '')
                            if s_str and e_str:
                                s_min = time_to_minutes(s_str)
                                e_min = time_to_minutes(e_str)
                                if req_start >= s_min and req_end <= e_min:
                                    in_any_slot = True
                                    break
                        elif isinstance(slot, str) and '-' in slot:
                            parts = slot.split('-')
                            s_min = time_to_minutes(parts[0].strip())
                            e_min = time_to_minutes(parts[1].strip())
                            if req_start >= s_min and req_end <= e_min:
                                in_any_slot = True
                                break
                    if day_avail and not in_any_slot:
                        return False

            return True

        def generate_time_slots(settings: dict) -> list:
            """Generate discrete time slots based on settings (start, end, duration, breaks)."""
            if not settings:
                return []
            start_str = settings.get('start_time', '09:00')
            end_str = settings.get('end_time', '17:00')
            duration = settings.get('period_duration', 60)
            breaks = settings.get('breaks', [])

            start_min = time_to_minutes(start_str)
            end_min = time_to_minutes(end_str)
            if duration <= 0 or start_min >= end_min:
                return []

            break_intervals = []
            for brk in breaks:
                b_start = time_to_minutes(brk.get('start', ''))
                b_end = time_to_minutes(brk.get('end', ''))
                if b_start < b_end:
                    break_intervals.append((b_start, b_end))

            slots = []
            current = start_min
            slot_index = 1
            while current + duration <= end_min:
                slot_end = current + duration
                overlaps_break = False
                for b_start, b_end in break_intervals:
                    if max(current, b_start) < min(slot_end, b_end):
                        overlaps_break = True
                        current = b_end
                        break
                if overlaps_break:
                    continue

                def _fmt(m: int) -> str:
                    return f"{m // 60:02d}:{m % 60:02d}"

                slots.append({
                    'index': slot_index,
                    'start': _fmt(current),
                    'end': _fmt(slot_end),
                    'label': f"Period {slot_index} ({_fmt(current)}-{_fmt(slot_end)})"
                })
                slot_index += 1
                current = slot_end

            return slots


class ValidationError:
    """Structured timetable validation error object."""

    def __init__(
        self,
        error_type: str,
        message: str,
        session_id: str = '',
        day: str = '',
        time_range: str = '',
        resource: str = '',
        severity: str = 'error'
    ):
        self.error_type = error_type
        self.message = message
        self.session_id = session_id or ''
        self.day = day or ''
        self.time_range = time_range or ''
        self.resource = resource or ''
        self.severity = severity

    def to_dict(self) -> Dict[str, Any]:
        return {
            'error_type': self.error_type,
            'message': self.message,
            'session_id': self.session_id,
            'day': self.day,
            'time_range': self.time_range,
            'resource': self.resource,
            'severity': self.severity
        }

    def __getitem__(self, key: str) -> Any:
        return self.to_dict()[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self.to_dict().get(key, default)

    def __repr__(self) -> str:
        return f"<ValidationError [{self.severity.upper()}] {self.error_type}: {self.message}>"


def _get_name(items: list, item_id: str, field: str = 'name') -> str:
    """Retrieve name or specified field of an item by id."""
    if not items or not item_id:
        return 'Unknown'
    for item in items:
        if isinstance(item, dict) and item.get('id') == item_id:
            return str(item.get(field, 'Unknown'))
    return 'Unknown'


def _get_item(items: list, item_id: str) -> Optional[dict]:
    """Retrieve dictionary item from list by id."""
    if not items or not item_id:
        return None
    for item in items:
        if isinstance(item, dict) and item.get('id') == item_id:
            return item
    return None


def _get_section(programmes: list, section_id: str) -> Tuple[Optional[dict], Optional[dict], Optional[dict]]:
    """Retrieve section, programme, and semester by section id."""
    if not programmes or not section_id:
        return None, None, None
    for prog in programmes:
        if not isinstance(prog, dict):
            continue
        for sem in prog.get('semesters', []):
            if not isinstance(sem, dict):
                continue
            for sec in sem.get('sections', []):
                if isinstance(sec, dict) and sec.get('id') == section_id:
                    return sec, prog, sem
    return None, None, None


def validate_timetable(data: dict) -> List[Dict[str, Any]]:
    """Run all validation checks on the current timetable.

    Returns list of ValidationError dicts.
    """
    if not isinstance(data, dict):
        return [ValidationError('invalid_input', 'Timetable data must be a dictionary.').to_dict()]

    errors: List[ValidationError] = []
    sessions = data.get('scheduled_sessions', [])
    settings = data.get('settings', {})
    rooms = data.get('rooms', [])
    faculty_list = data.get('faculty', [])
    programmes = data.get('programmes', [])
    subjects = data.get('subjects', [])
    fixed_sessions = data.get('fixed_sessions', [])
    previous_sessions = data.get('_previous_sessions', [])

    time_slots = generate_time_slots(settings)
    breaks = settings.get('breaks', [])

    # 1. Check university hours and breaks
    errors.extend(_check_university_hours(sessions, settings, breaks))

    # 2. Check faculty availability
    errors.extend(_check_faculty_availability(sessions, faculty_list))

    # 3. Check faculty overlaps
    errors.extend(_check_faculty_overlaps(sessions, faculty_list))

    # 4. Check room overlaps
    errors.extend(_check_room_overlaps(sessions, rooms))

    # 5. Check student-group overlaps (section level)
    errors.extend(_check_section_overlaps(sessions, programmes))

    # 6. Check whole-class vs batch overlaps
    errors.extend(_check_class_batch_overlaps(sessions, programmes))

    # 7. Check room capacity
    errors.extend(_check_room_capacity(sessions, rooms, programmes))

    # 8. Check room type (practical must use lab)
    errors.extend(_check_room_type(sessions, rooms, subjects))

    # 9. Check practical consecutive periods
    errors.extend(_check_consecutive_periods(sessions, subjects, time_slots, settings))

    # 10. Check weekly session counts
    errors.extend(_check_weekly_counts(sessions, subjects, programmes))

    # 11. Check fixed session preservation
    errors.extend(_check_fixed_sessions(sessions, fixed_sessions))

    # 12. Check locked session preservation
    errors.extend(_check_locked_sessions(sessions, previous_sessions))

    return [e.to_dict() if isinstance(e, ValidationError) else e for e in errors]


def _check_university_hours(sessions: list, settings: dict, breaks: list) -> List[ValidationError]:
    errors = []
    uni_start_str = settings.get('start_time', '09:00')
    uni_end_str = settings.get('end_time', '17:00')
    uni_start = time_to_minutes(uni_start_str)
    uni_end = time_to_minutes(uni_end_str)
    working_days = settings.get('working_days', [])

    for s in sessions:
        start_str = s.get('start_time', '')
        end_str = s.get('end_time', '')
        day = s.get('day', '')
        sess_id = s.get('id', '')
        time_range = f"{start_str}-{end_str}"

        s_start = time_to_minutes(start_str)
        s_end = time_to_minutes(end_str)

        # Check valid start and end
        if s_start >= s_end:
            errors.append(ValidationError(
                'invalid_time_range',
                f'Session at {day} {time_range} has invalid duration (start time >= end time)',
                session_id=sess_id, day=day, time_range=time_range
            ))
            continue

        # Check within university hours
        if s_start < uni_start or s_end > uni_end:
            errors.append(ValidationError(
                'university_hours',
                f'Session at {day} {time_range} is outside university hours ({uni_start_str}-{uni_end_str})',
                session_id=sess_id, day=day, time_range=time_range
            ))

        # Check working day
        if working_days and day not in working_days:
            errors.append(ValidationError(
                'working_day',
                f'Session scheduled on {day} which is not a working day',
                session_id=sess_id, day=day, time_range=time_range
            ))

        # Check breaks
        for brk in breaks:
            brk_start_str = brk.get('start', '')
            brk_end_str = brk.get('end', '')
            brk_name = brk.get('name', 'break')
            brk_start = time_to_minutes(brk_start_str)
            brk_end = time_to_minutes(brk_end_str)
            if s_start < brk_end and s_end > brk_start:
                errors.append(ValidationError(
                    'break_overlap',
                    f'Session at {day} {time_range} overlaps with {brk_name} break ({brk_start_str}-{brk_end_str})',
                    session_id=sess_id, day=day, time_range=time_range
                ))
    return errors


def _check_faculty_availability(sessions: list, faculty_list: list) -> List[ValidationError]:
    errors = []
    for s in sessions:
        fid = s.get('faculty_id')
        if not fid:
            continue
        day = s.get('day', '')
        start_str = s.get('start_time', '')
        end_str = s.get('end_time', '')
        sess_id = s.get('id', '')
        time_range = f"{start_str}-{end_str}"

        fac = _get_item(faculty_list, fid)
        if not fac:
            errors.append(ValidationError(
                'faculty_missing',
                f'Faculty ID {fid} not found for session at {day} {start_str}',
                session_id=sess_id, day=day, time_range=time_range, resource=str(fid)
            ))
            continue

        if not is_faculty_available(fac, day, start_str, end_str):
            fac_name = fac.get('name', str(fid))
            errors.append(ValidationError(
                'faculty_availability',
                f'{fac_name} is not available at {day} {time_range}',
                session_id=sess_id, day=day, time_range=time_range, resource=fac_name
            ))
    return errors


def _check_faculty_overlaps(sessions: list, faculty_list: list) -> List[ValidationError]:
    errors = []
    fac_day = defaultdict(list)
    for s in sessions:
        fid = s.get('faculty_id')
        day = s.get('day')
        if fid and day and s.get('start_time') and s.get('end_time'):
            fac_day[(fid, day)].append(s)

    for (fid, day), day_sessions in fac_day.items():
        n = len(day_sessions)
        for i in range(n):
            for j in range(i + 1, n):
                s1, s2 = day_sessions[i], day_sessions[j]
                if s1.get('id') and s1.get('id') == s2.get('id'):
                    continue
                if times_overlap(s1['start_time'], s1['end_time'], s2['start_time'], s2['end_time']):
                    fac_name = _get_name(faculty_list, fid)
                    errors.append(ValidationError(
                        'faculty_overlap',
                        f'{fac_name} has overlapping sessions on {day}: {s1["start_time"]}-{s1["end_time"]} and {s2["start_time"]}-{s2["end_time"]}',
                        session_id=s1.get('id', ''), day=day,
                        time_range=f'{s1["start_time"]}-{s1["end_time"]}',
                        resource=fac_name
                    ))
    return errors


def _check_room_overlaps(sessions: list, rooms: list) -> List[ValidationError]:
    errors = []
    room_day = defaultdict(list)
    for s in sessions:
        rid = s.get('room_id')
        day = s.get('day')
        if rid and day and s.get('start_time') and s.get('end_time'):
            room_day[(rid, day)].append(s)

    for (rid, day), day_sessions in room_day.items():
        n = len(day_sessions)
        for i in range(n):
            for j in range(i + 1, n):
                s1, s2 = day_sessions[i], day_sessions[j]
                if s1.get('id') and s1.get('id') == s2.get('id'):
                    continue
                if times_overlap(s1['start_time'], s1['end_time'], s2['start_time'], s2['end_time']):
                    room_name = _get_name(rooms, rid)
                    errors.append(ValidationError(
                        'room_overlap',
                        f'{room_name} has overlapping sessions on {day}: {s1["start_time"]}-{s1["end_time"]} and {s2["start_time"]}-{s2["end_time"]}',
                        session_id=s1.get('id', ''), day=day,
                        time_range=f'{s1["start_time"]}-{s1["end_time"]}',
                        resource=room_name
                    ))
    return errors


def _check_section_overlaps(sessions: list, programmes: list) -> List[ValidationError]:
    errors = []
    # Group whole-class sessions (no batch_id) by section and day
    sec_day = defaultdict(list)
    for s in sessions:
        if not s.get('batch_id') and s.get('section_id') and s.get('day') and s.get('start_time') and s.get('end_time'):
            sec_day[(s['section_id'], s['day'])].append(s)

    for (sid, day), day_sessions in sec_day.items():
        n = len(day_sessions)
        for i in range(n):
            for j in range(i + 1, n):
                s1, s2 = day_sessions[i], day_sessions[j]
                if s1.get('id') and s1.get('id') == s2.get('id'):
                    continue
                if times_overlap(s1['start_time'], s1['end_time'], s2['start_time'], s2['end_time']):
                    errors.append(ValidationError(
                        'section_overlap',
                        f'Section has overlapping sessions on {day}: {s1["start_time"]}-{s1["end_time"]} and {s2["start_time"]}-{s2["end_time"]}',
                        session_id=s1.get('id', ''), day=day,
                        time_range=f'{s1["start_time"]}-{s1["end_time"]}',
                        resource=str(sid)
                    ))

    # Also group practical sessions with the same batch_id by (section_id, batch_id, day)
    batch_day = defaultdict(list)
    for s in sessions:
        if s.get('batch_id') and s.get('section_id') and s.get('day') and s.get('start_time') and s.get('end_time'):
            batch_day[(s['section_id'], s['batch_id'], s['day'])].append(s)

    for (sid, bid, day), day_sessions in batch_day.items():
        n = len(day_sessions)
        for i in range(n):
            for j in range(i + 1, n):
                s1, s2 = day_sessions[i], day_sessions[j]
                if s1.get('id') and s1.get('id') == s2.get('id'):
                    continue
                if times_overlap(s1['start_time'], s1['end_time'], s2['start_time'], s2['end_time']):
                    errors.append(ValidationError(
                        'batch_overlap',
                        f'Batch {bid} has overlapping sessions on {day}: {s1["start_time"]}-{s1["end_time"]} and {s2["start_time"]}-{s2["end_time"]}',
                        session_id=s1.get('id', ''), day=day,
                        time_range=f'{s1["start_time"]}-{s1["end_time"]}',
                        resource=str(bid)
                    ))

    return errors


def _check_class_batch_overlaps(sessions: list, programmes: list) -> List[ValidationError]:
    """Check that whole-class sessions don't overlap with practicals from the same section."""
    errors = []
    whole_class = defaultdict(list)
    batch_sessions = defaultdict(list)

    for s in sessions:
        sec_id = s.get('section_id')
        if not sec_id or not s.get('day') or not s.get('start_time') or not s.get('end_time'):
            continue
        if s.get('batch_id'):
            batch_sessions[sec_id].append(s)
        else:
            whole_class[sec_id].append(s)

    for section_id, wc_list in whole_class.items():
        if section_id not in batch_sessions:
            continue
        for wc in wc_list:
            for bs in batch_sessions[section_id]:
                if wc['day'] == bs['day'] and times_overlap(
                    wc['start_time'], wc['end_time'],
                    bs['start_time'], bs['end_time']
                ):
                    errors.append(ValidationError(
                        'class_batch_overlap',
                        f'Whole-class session ({wc["start_time"]}-{wc["end_time"]}) overlaps with practical batch session ({bs["start_time"]}-{bs["end_time"]}) on {wc["day"]}',
                        session_id=wc.get('id', ''), day=wc['day'],
                        time_range=f'{wc["start_time"]}-{wc["end_time"]}',
                        resource=str(section_id)
                    ))
    return errors


def _check_room_capacity(sessions: list, rooms: list, programmes: list) -> List[ValidationError]:
    errors = []
    for s in sessions:
        rid = s.get('room_id')
        sess_id = s.get('id', '')
        day = s.get('day', '')
        start_str = s.get('start_time', '')
        end_str = s.get('end_time', '')
        time_range = f"{start_str}-{end_str}"

        room = _get_item(rooms, rid)
        if not room:
            errors.append(ValidationError(
                'room_missing',
                f'Room not found for session at {day} {start_str}',
                session_id=sess_id, day=day, time_range=time_range, resource=str(rid)
            ))
            continue

        student_count = 0
        if s.get('batch_id'):
            for prog in programmes:
                for sem in prog.get('semesters', []):
                    for sec in sem.get('sections', []):
                        if sec.get('id') == s.get('section_id'):
                            for batch in sec.get('practical_batches', []):
                                if batch.get('id') == s.get('batch_id'):
                                    try:
                                        student_count = int(batch.get('strength', 0))
                                    except (ValueError, TypeError):
                                        student_count = 0
                                    break
        else:
            for prog in programmes:
                for sem in prog.get('semesters', []):
                    for sec in sem.get('sections', []):
                        if sec.get('id') == s.get('section_id'):
                            try:
                                student_count = int(sec.get('student_strength', 0))
                            except (ValueError, TypeError):
                                student_count = 0
                            break

        try:
            capacity = int(room.get('capacity', 0))
        except (ValueError, TypeError):
            capacity = 0

        room_name = room.get('name', str(rid))
        if student_count > 0 and capacity < student_count:
            errors.append(ValidationError(
                'room_capacity',
                f'{room_name} (capacity {capacity}) is too small for {student_count} students',
                session_id=sess_id, day=day, time_range=time_range, resource=room_name
            ))
    return errors


def _check_room_type(sessions: list, rooms: list, subjects: list) -> List[ValidationError]:
    errors = []
    for s in sessions:
        if s.get('session_type') != 'practical':
            continue
        rid = s.get('room_id')
        sub_id = s.get('subject_id')
        sess_id = s.get('id', '')
        day = s.get('day', '')
        time_range = f"{s.get('start_time', '')}-{s.get('end_time', '')}"

        room = _get_item(rooms, rid)
        subject = _get_item(subjects, sub_id)
        if not room or not subject:
            continue

        room_name = room.get('name', str(rid))
        if room.get('room_type') != 'laboratory':
            errors.append(ValidationError(
                'room_type',
                f'Practical session assigned to {room_name} which is not a laboratory',
                session_id=sess_id, day=day, time_range=time_range, resource=room_name
            ))

        req_lab = subject.get('required_lab_type', '')
        if req_lab and room.get('lab_type', '') != req_lab:
            errors.append(ValidationError(
                'lab_type_mismatch',
                f'Practical requires {req_lab} but assigned to {room.get("lab_type", "unknown")} ({room_name})',
                session_id=sess_id, day=day, time_range=time_range, resource=room_name
            ))
    return errors


def _check_consecutive_periods(sessions: list, subjects: list, time_slots: list, settings: Optional[dict] = None) -> List[ValidationError]:
    errors = []
    settings = settings or {}
    for s in sessions:
        if s.get('session_type') != 'practical':
            continue
        sub_id = s.get('subject_id')
        subject = _get_item(subjects, sub_id)
        if not subject:
            continue

        try:
            required_consec = int(subject.get('practical_consecutive_periods', 2))
        except (ValueError, TypeError):
            required_consec = 2

        start_str = s.get('start_time', '00:00')
        end_str = s.get('end_time', '00:00')
        actual_duration = time_to_minutes(end_str) - time_to_minutes(start_str)

        period_duration = 0
        if time_slots:
            try:
                period_duration = time_to_minutes(time_slots[0]['end']) - time_to_minutes(time_slots[0]['start'])
            except (KeyError, TypeError):
                period_duration = 0

        if period_duration <= 0:
            try:
                period_duration = int(settings.get('period_duration', 60))
            except (ValueError, TypeError):
                period_duration = 60

        expected_duration = required_consec * period_duration
        if actual_duration < expected_duration:
            errors.append(ValidationError(
                'consecutive_periods',
                f'Practical session needs {required_consec} consecutive periods ({expected_duration} min) but only has {actual_duration} min',
                session_id=s.get('id', ''), day=s.get('day', ''),
                time_range=f'{start_str}-{end_str}'
            ))
    return errors


def _check_weekly_counts(sessions: list, subjects: list, programmes: list) -> List[ValidationError]:
    """Check that every subject has its required weekly sessions."""
    errors = []
    for subject in subjects:
        sub_id = subject.get('id')
        sub_name = subject.get('name', 'Unknown')
        sub_code = subject.get('code', '')

        # Count theory sessions
        theory_count = sum(
            1 for s in sessions
            if s.get('subject_id') == sub_id and s.get('session_type') == 'theory'
        )
        try:
            required_theory = int(subject.get('theory_periods_per_week', 0))
        except (ValueError, TypeError):
            required_theory = 0

        if theory_count < required_theory:
            errors.append(ValidationError(
                'weekly_theory_count',
                f'{sub_name} ({sub_code}): Has {theory_count}/{required_theory} theory periods scheduled',
                resource=sub_name,
                severity='error'
            ))

        # Count practical sessions (per batch if applicable)
        try:
            required_practical = int(subject.get('practical_sessions_per_week', 0))
        except (ValueError, TypeError):
            required_practical = 0

        if required_practical > 0:
            is_for_batches = subject.get('is_for_batches', False)
            section_id = subject.get('section_id', '')

            if is_for_batches:
                # Find section and its batches
                section = None
                for prog in programmes:
                    for sem in prog.get('semesters', []):
                        for sec in sem.get('sections', []):
                            if sec.get('id') == section_id:
                                section = sec
                                break

                if section:
                    for batch in section.get('practical_batches', []):
                        bid = batch.get('id')
                        bname = batch.get('name', bid)
                        batch_prac_count = sum(
                            1 for s in sessions
                            if s.get('subject_id') == sub_id
                            and s.get('session_type') == 'practical'
                            and s.get('batch_id') == bid
                        )
                        if batch_prac_count < required_practical:
                            errors.append(ValidationError(
                                'weekly_practical_count',
                                f'{sub_name} ({sub_code}): Batch {bname} has {batch_prac_count}/{required_practical} practical sessions',
                                resource=f'{sub_name} - {bname}',
                                severity='error'
                            ))
            else:
                prac_count = sum(
                    1 for s in sessions
                    if s.get('subject_id') == sub_id and s.get('session_type') == 'practical'
                )
                if prac_count < required_practical:
                    errors.append(ValidationError(
                        'weekly_practical_count',
                        f'{sub_name} ({sub_code}): Has {prac_count}/{required_practical} practical sessions',
                        resource=sub_name,
                        severity='error'
                    ))
    return errors


def _check_fixed_sessions(sessions: list, fixed_sessions: list) -> List[ValidationError]:
    errors = []
    for fixed in fixed_sessions:
        f_sub = fixed.get('subject_id')
        f_day = fixed.get('day')
        f_start = fixed.get('start_time')
        f_end = fixed.get('end_time', '')
        time_range = f"{f_start}-{f_end}"

        found = any(
            s.get('is_fixed') and
            s.get('subject_id') == f_sub and
            s.get('day') == f_day and
            s.get('start_time') == f_start
            for s in sessions
        )
        if not found:
            errors.append(ValidationError(
                'fixed_session_missing',
                f'Fixed session on {f_day} {time_range} is missing from the schedule',
                day=f_day or '',
                time_range=time_range,
                severity='error'
            ))
    return errors


def _check_locked_sessions(sessions: list, previous_sessions: list) -> List[ValidationError]:
    errors = []
    for prev in previous_sessions:
        if not prev.get('is_locked'):
            continue
        p_id = prev.get('id')
        p_day = prev.get('day')
        p_start = prev.get('start_time')
        p_end = prev.get('end_time', '')
        p_room = prev.get('room_id')
        time_range = f"{p_start}-{p_end}"

        found = any(
            s.get('id') == p_id and
            s.get('day') == p_day and
            s.get('start_time') == p_start and
            s.get('room_id') == p_room
            for s in sessions
        )
        if not found:
            errors.append(ValidationError(
                'locked_session_moved',
                f'Locked session on {p_day} {time_range} was modified',
                session_id=p_id or '',
                day=p_day or '',
                time_range=time_range,
                severity='error'
            ))
    return errors


def validate_single_edit(
    data: dict,
    session_id: str,
    new_day: str,
    new_start: str,
    new_end: str,
    new_room_id: str
) -> List[Dict[str, Any]]:
    """Validate a single session edit before committing.

    Returns list of ValidationError dicts. Empty list means edit is valid.
    """
    errors: List[ValidationError] = []
    sessions = data.get('scheduled_sessions', [])
    settings = data.get('settings', {})
    rooms = data.get('rooms', [])
    faculty_list = data.get('faculty', [])
    subjects = data.get('subjects', [])
    programmes = data.get('programmes', [])

    # Find the session being edited
    target = None
    for s in sessions:
        if s.get('id') == session_id:
            target = s
            break

    if not target:
        return [ValidationError('not_found', 'Session not found', session_id=session_id).to_dict()]

    if target.get('is_locked'):
        return [ValidationError('locked', 'Cannot edit a locked session. Unlock it first.', session_id=session_id).to_dict()]

    if target.get('is_fixed'):
        return [ValidationError('fixed', 'Cannot edit a fixed session.', session_id=session_id).to_dict()]

    time_range = f"{new_start}-{new_end}"

    # Check start before end
    if time_to_minutes(new_start) >= time_to_minutes(new_end):
        errors.append(ValidationError(
            'invalid_time_range',
            f'Time range {time_range} is invalid (start time >= end time)',
            session_id=session_id, day=new_day, time_range=time_range
        ))

    # Check university hours
    uni_start = time_to_minutes(settings.get('start_time', '09:00'))
    uni_end = time_to_minutes(settings.get('end_time', '17:00'))
    if time_to_minutes(new_start) < uni_start or time_to_minutes(new_end) > uni_end:
        errors.append(ValidationError(
            'university_hours',
            f'Time {new_start}-{new_end} is outside university hours',
            session_id=session_id, day=new_day, time_range=time_range
        ))

    # Check breaks
    for brk in settings.get('breaks', []):
        brk_start = brk.get('start', '')
        brk_end = brk.get('end', '')
        if brk_start and brk_end and times_overlap(new_start, new_end, brk_start, brk_end):
            errors.append(ValidationError(
                'break_overlap',
                f'Time overlaps with {brk.get("name", "break")} break',
                session_id=session_id, day=new_day, time_range=time_range
            ))

    # Check working day
    working_days = settings.get('working_days', [])
    if working_days and new_day not in working_days:
        errors.append(ValidationError(
            'working_day',
            f'{new_day} is not a working day',
            session_id=session_id, day=new_day, time_range=time_range
        ))

    # Check faculty availability
    fac_id = target.get('faculty_id')
    fac = _get_item(faculty_list, fac_id) if fac_id else None
    if fac and not is_faculty_available(fac, new_day, new_start, new_end):
        fac_name = fac.get('name', str(fac_id))
        errors.append(ValidationError(
            'faculty_availability',
            f'{fac_name} is not available at {new_day} {new_start}-{new_end}',
            session_id=session_id, day=new_day, time_range=time_range, resource=fac_name
        ))

    # Check faculty overlap
    if fac_id:
        for s in sessions:
            if s.get('id') == session_id:
                continue
            if s.get('faculty_id') == fac_id and s.get('day') == new_day:
                if times_overlap(new_start, new_end, s.get('start_time', ''), s.get('end_time', '')):
                    fac_name = fac.get('name', fac_id) if fac else _get_name(faculty_list, fac_id)
                    errors.append(ValidationError(
                        'faculty_overlap',
                        f'Faculty already has a session at {new_day} {s.get("start_time", "")}-{s.get("end_time", "")}',
                        session_id=session_id, day=new_day, time_range=time_range, resource=fac_name
                    ))

    # Check room overlap
    if new_room_id:
        for s in sessions:
            if s.get('id') == session_id:
                continue
            if s.get('room_id') == new_room_id and s.get('day') == new_day:
                if times_overlap(new_start, new_end, s.get('start_time', ''), s.get('end_time', '')):
                    room_name = _get_name(rooms, new_room_id)
                    errors.append(ValidationError(
                        'room_overlap',
                        f'{room_name} is already occupied at {new_day} {s.get("start_time", "")}-{s.get("end_time", "")}',
                        session_id=session_id, day=new_day, time_range=time_range, resource=room_name
                    ))

    # Check section/batch overlap
    sec_id = target.get('section_id')
    if sec_id:
        target_batch = target.get('batch_id', '')
        for s in sessions:
            if s.get('id') == session_id:
                continue
            if s.get('section_id') == sec_id and s.get('day') == new_day:
                s_batch = s.get('batch_id', '')
                if not target_batch or not s_batch:
                    if times_overlap(new_start, new_end, s.get('start_time', ''), s.get('end_time', '')):
                        errors.append(ValidationError(
                            'section_overlap',
                            f'Student group has another session at {s.get("start_time", "")}-{s.get("end_time", "")}',
                            session_id=session_id, day=new_day, time_range=time_range, resource=str(sec_id)
                        ))
                elif target_batch == s_batch:
                    if times_overlap(new_start, new_end, s.get('start_time', ''), s.get('end_time', '')):
                        errors.append(ValidationError(
                            'batch_overlap',
                            f'Batch already has a session at {s.get("start_time", "")}-{s.get("end_time", "")}',
                            session_id=session_id, day=new_day, time_range=time_range, resource=str(target_batch)
                        ))

    # Check room capacity and type
    room = _get_item(rooms, new_room_id)
    if room:
        room_name = room.get('name', str(new_room_id))
        if target.get('session_type') == 'practical':
            if room.get('room_type') != 'laboratory':
                errors.append(ValidationError(
                    'room_type',
                    f'{room_name} is not a laboratory',
                    session_id=session_id, day=new_day, time_range=time_range, resource=room_name
                ))
            subject = _get_item(subjects, target.get('subject_id'))
            if subject and subject.get('required_lab_type') and room.get('lab_type') != subject['required_lab_type']:
                errors.append(ValidationError(
                    'lab_type',
                    f'Requires {subject["required_lab_type"]} but {room_name} is {room.get("lab_type", "unknown")}',
                    session_id=session_id, day=new_day, time_range=time_range, resource=room_name
                ))

        # Check room capacity
        student_count = 0
        if target.get('batch_id'):
            for prog in programmes:
                for sem in prog.get('semesters', []):
                    for sec in sem.get('sections', []):
                        if sec.get('id') == target.get('section_id'):
                            for batch in sec.get('practical_batches', []):
                                if batch.get('id') == target.get('batch_id'):
                                    try:
                                        student_count = int(batch.get('strength', 0))
                                    except (ValueError, TypeError):
                                        student_count = 0
                                    break
        else:
            for prog in programmes:
                for sem in prog.get('semesters', []):
                    for sec in sem.get('sections', []):
                        if sec.get('id') == target.get('section_id'):
                            try:
                                student_count = int(sec.get('student_strength', 0))
                            except (ValueError, TypeError):
                                student_count = 0
                            break

        try:
            capacity = int(room.get('capacity', 0))
        except (ValueError, TypeError):
            capacity = 0

        if student_count > 0 and capacity < student_count:
            errors.append(ValidationError(
                'room_capacity',
                f'{room_name} (capacity {capacity}) is too small for {student_count} students',
                session_id=session_id, day=new_day, time_range=time_range, resource=room_name
            ))

    return [e.to_dict() if isinstance(e, ValidationError) else e for e in errors]


def is_valid_timetable(data: dict) -> bool:
    """Convenience helper to check if timetable has zero error-level issues."""
    errors = validate_timetable(data)
    return not any(e.get('severity') == 'error' for e in errors)
