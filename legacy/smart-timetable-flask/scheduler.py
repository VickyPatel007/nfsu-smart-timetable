"""Constraint-aware timetable scheduling engine for NFSU.

Algorithm: Priority-based greedy scheduling with constraint propagation and backtracking.

1. Parse all inputs into scheduling tasks
2. Place fixed sessions first
3. Preserve locked sessions  
4. Sort remaining tasks by constraint tightness (most constrained first)
5. For each task, find valid slots satisfying ALL hard constraints
6. Rank valid slots by preferences
7. Place the best slot
8. If no valid slot found, attempt backtracking (limited)
9. Report results

Hard Constraints (MUST satisfy):
- Session within university working hours, outside breaks
- Faculty available at assigned time
- No faculty overlap (same faculty, same time)
- No room overlap (same room, same time)
- No student-group overlap (same section, same time)
- Whole-class theory must not overlap with practical of same section
- Room capacity >= student count
- Practical must use suitable lab (matching lab_type)
- Practical must use consecutive periods
- All required weekly sessions must be scheduled
- Fixed sessions stay in their slots
- Locked sessions preserved during regeneration

Soft Preferences (used to rank valid slots):
- Faculty preferred time slots
- Max periods per day limit (soft)
- Spread sessions across days
"""

import copy
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple


def time_to_minutes(t: str) -> int:
    """Convert HH:MM to minutes since midnight."""
    if not t or ':' not in t:
        return 0
    h, m = map(int, t.strip().split(':'))
    return h * 60 + m


def minutes_to_time(m: int) -> str:
    """Convert minutes since midnight to HH:MM."""
    return f'{m // 60:02d}:{m % 60:02d}'


def generate_time_slots(settings: dict) -> list:
    """Generate all available time periods based on university settings.
    Returns list of {'start': 'HH:MM', 'end': 'HH:MM', 'period_index': int} for each day.
    Excludes break periods.
    """
    start = time_to_minutes(settings.get('start_time', '09:00'))
    end = time_to_minutes(settings.get('end_time', '17:00'))
    duration = settings.get('period_duration', 60)
    breaks = settings.get('breaks', [])

    slots = []
    current = start
    period_idx = 0
    while current + duration <= end:
        slot_start = current
        slot_end = current + duration

        # Check if slot overlaps with any break
        is_break = False
        for brk in breaks:
            brk_start = time_to_minutes(brk['start'])
            brk_end = time_to_minutes(brk['end'])
            if slot_start < brk_end and slot_end > brk_start:
                is_break = True
                # Jump past the break
                current = brk_end
                break

        if not is_break:
            slots.append({
                'start': minutes_to_time(slot_start),
                'end': minutes_to_time(slot_end),
                'period_index': period_idx
            })
            period_idx += 1
            current = slot_end

    return slots


def times_overlap(s1_start: str, s1_end: str, s2_start: str, s2_end: str) -> bool:
    """Check if two time ranges overlap."""
    a1 = time_to_minutes(s1_start)
    a2 = time_to_minutes(s1_end)
    b1 = time_to_minutes(s2_start)
    b2 = time_to_minutes(s2_end)
    return a1 < b2 and b1 < a2


def is_faculty_available(faculty: dict, day: str, start: str, end: str) -> bool:
    """Check if faculty is available at the given day/time."""
    if not faculty:
        return False
    avail_days = faculty.get('available_days')
    if avail_days is not None:
        if day not in avail_days:
            return False
    # Check availability window
    fac_start = time_to_minutes(faculty.get('available_time_start') or '09:00')
    fac_end = time_to_minutes(faculty.get('available_time_end') or '17:00')
    slot_start = time_to_minutes(start)
    slot_end = time_to_minutes(end)
    if slot_start < fac_start or slot_end > fac_end:
        return False
    # Check unavailable slots
    for unavail in faculty.get('unavailable_slots', []):
        if unavail.get('day') == day and times_overlap(start, end, unavail.get('start', ''), unavail.get('end', '')):
            return False
    return True


class SchedulingTask:
    """Represents a single session that needs to be scheduled."""
    def __init__(
        self,
        subject_id: str,
        faculty_id: str,
        section_id: str,
        programme_id: str,
        semester_id: str,
        session_type: str,
        num_periods: int,
        required_lab_type: str = '',
        batch_id: str = '',
        batch_name: str = '',
        student_count: int = 0,
        subject_name: str = '',
        faculty_name: str = ''
    ):
        self.subject_id = subject_id
        self.faculty_id = faculty_id
        self.section_id = section_id
        self.programme_id = programme_id
        self.semester_id = semester_id
        self.session_type = session_type
        self.num_periods = num_periods  # consecutive periods needed
        self.required_lab_type = required_lab_type
        self.batch_id = batch_id
        self.batch_name = batch_name
        self.student_count = student_count
        self.subject_name = subject_name
        self.faculty_name = faculty_name
        self.valid_slots: List[dict] = []  # computed during scheduling


class SchedulerEngine:
    def __init__(self, data: dict):
        self.data = data
        self.settings = data.get('settings', {})
        self.rooms = data.get('rooms', [])
        self.programmes = data.get('programmes', [])
        self.faculty = data.get('faculty', [])
        self.subjects = data.get('subjects', [])
        self.fixed_sessions = data.get('fixed_sessions', [])
        self.existing_sessions = data.get('scheduled_sessions', [])
        self.locked_sessions = data.get('locked_sessions', [])

        self.time_slots = generate_time_slots(self.settings)
        self.working_days = self.settings.get('working_days', ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'])

        # Occupancy tracking: resource_id -> set of (day, start, end) tuples
        self.faculty_occupied: Dict[str, Set[Tuple[str, str, str]]] = {}
        self.room_occupied: Dict[str, Set[Tuple[str, str, str]]] = {}
        self.section_occupied: Dict[str, Set[Tuple[str, str, str]]] = {}  # Whole-class sessions
        self.batch_occupied: Dict[str, Set[Tuple[str, str, str]]] = {}    # Practical batch sessions

        # Mapping: section_id -> set of known batch_ids
        self.section_batches: Dict[str, Set[str]] = {}
        for prog in self.programmes:
            for sem in prog.get('semesters', []):
                for sec in sem.get('sections', []):
                    sec_id = sec.get('id')
                    if sec_id:
                        if sec_id not in self.section_batches:
                            self.section_batches[sec_id] = set()
                        for b in sec.get('practical_batches', []):
                            if b.get('id'):
                                self.section_batches[sec_id].add(b['id'])

        # Faculty daily period count tracking: (faculty_id, day) -> count
        self.faculty_daily_periods: Dict[Tuple[str, str], int] = {}

        self.scheduled: List[dict] = []    # final scheduled sessions
        self.unscheduled: List[dict] = []  # tasks that couldn't be scheduled
        self.conflicts: List[str] = []     # conflict explanations
        self.backtrack_limit = 1000
        self.backtrack_count = 0

    def _get_faculty(self, fid: str) -> Optional[dict]:
        for f in self.faculty:
            if f.get('id') == fid:
                return f
        return None

    def _get_room(self, rid: str) -> Optional[dict]:
        for r in self.rooms:
            if r.get('id') == rid:
                return r
        return None

    def _get_section(self, sid: str) -> Optional[dict]:
        for prog in self.programmes:
            for sem in prog.get('semesters', []):
                for sec in sem.get('sections', []):
                    if sec.get('id') == sid:
                        return sec
        for sec in self.data.get('sections', []):
            if sec.get('id') == sid:
                return sec
        return None

    def _get_subject(self, sid: str) -> Optional[dict]:
        for s in self.subjects:
            if s.get('id') == sid:
                return s
        return None

    def _mark_occupied(self, session: dict) -> None:
        """Mark resources as occupied for a scheduled session."""
        key = (session['day'], session['start_time'], session['end_time'])
        periods = session.get('_num_periods', 1)

        fid = session.get('faculty_id')
        if fid:
            if fid not in self.faculty_occupied:
                self.faculty_occupied[fid] = set()
            self.faculty_occupied[fid].add(key)
            dk = (fid, session['day'])
            self.faculty_daily_periods[dk] = self.faculty_daily_periods.get(dk, 0) + periods

        rid = session.get('room_id')
        if rid:
            if rid not in self.room_occupied:
                self.room_occupied[rid] = set()
            self.room_occupied[rid].add(key)

        sid = session.get('section_id')
        bid = session.get('batch_id', '')
        if bid:
            if bid not in self.batch_occupied:
                self.batch_occupied[bid] = set()
            self.batch_occupied[bid].add(key)
            if sid:
                if sid not in self.section_batches:
                    self.section_batches[sid] = set()
                self.section_batches[sid].add(bid)
        else:
            if sid:
                if sid not in self.section_occupied:
                    self.section_occupied[sid] = set()
                self.section_occupied[sid].add(key)

    def _unmark_occupied(self, session: dict) -> None:
        """Unmark resources (for backtracking)."""
        key = (session['day'], session['start_time'], session['end_time'])
        periods = session.get('_num_periods', 1)

        fid = session.get('faculty_id')
        if fid and fid in self.faculty_occupied:
            self.faculty_occupied[fid].discard(key)
            dk = (fid, session['day'])
            self.faculty_daily_periods[dk] = max(0, self.faculty_daily_periods.get(dk, 0) - periods)

        rid = session.get('room_id')
        if rid and rid in self.room_occupied:
            self.room_occupied[rid].discard(key)

        sid = session.get('section_id')
        bid = session.get('batch_id', '')
        if bid:
            if bid in self.batch_occupied:
                self.batch_occupied[bid].discard(key)
        else:
            if sid and sid in self.section_occupied:
                self.section_occupied[sid].discard(key)

    def _check_overlap(self, occupied_set: Set[Tuple[str, str, str]], day: str, start: str, end: str) -> bool:
        """Check if any existing occupation overlaps with proposed time."""
        for occ_day, occ_start, occ_end in occupied_set:
            if occ_day == day and times_overlap(start, end, occ_start, occ_end):
                return True
        return False

    def _check_section_batch_overlap(self, section_id: str, batch_id: str, day: str, start: str, end: str) -> bool:
        """Check whole-class vs batch overlap.
        A whole-class session (no batch) must not overlap with any batch practical of the same section.
        A batch session must not overlap with whole-class sessions of the same section.
        """
        if not batch_id:
            # Whole-class session: check against all known batches of this section
            batches = set(self.section_batches.get(section_id, set()))
            section = self._get_section(section_id)
            if section:
                for b in section.get('practical_batches', []):
                    if b.get('id'):
                        batches.add(b['id'])
            for bid in batches:
                if bid in self.batch_occupied:
                    if self._check_overlap(self.batch_occupied[bid], day, start, end):
                        return True
            # Also check whole-class section-level overlap
            if section_id in self.section_occupied:
                if self._check_overlap(self.section_occupied[section_id], day, start, end):
                    return True
        else:
            # Batch session: check against whole-class sessions (section_occupied)
            if section_id in self.section_occupied:
                if self._check_overlap(self.section_occupied[section_id], day, start, end):
                    return True
            # Also check same batch overlap
            if batch_id in self.batch_occupied:
                if self._check_overlap(self.batch_occupied[batch_id], day, start, end):
                    return True
        return False

    def _find_valid_slots(self, task: SchedulingTask) -> list:
        """Find all valid (day, room, start_time, end_time) combinations for a task."""
        valid = []
        faculty = self._get_faculty(task.faculty_id)
        if not faculty:
            return valid

        for day in self.working_days:
            # Check faculty available on this day
            fac_days = faculty.get('available_days')
            if fac_days is not None and day not in fac_days:
                continue

            # Find consecutive slot combinations
            for i in range(len(self.time_slots)):
                if i + task.num_periods > len(self.time_slots):
                    break

                # Check consecutive slots
                slot_group = self.time_slots[i:i + task.num_periods]
                is_consecutive = True
                for j in range(1, len(slot_group)):
                    if time_to_minutes(slot_group[j]['start']) != time_to_minutes(slot_group[j - 1]['end']):
                        is_consecutive = False
                        break
                if not is_consecutive:
                    continue

                start_time = slot_group[0]['start']
                end_time = slot_group[-1]['end']

                # Check faculty availability window and unavailable slots
                if not is_faculty_available(faculty, day, start_time, end_time):
                    continue

                # Check faculty not already occupied
                if task.faculty_id in self.faculty_occupied:
                    if self._check_overlap(self.faculty_occupied[task.faculty_id], day, start_time, end_time):
                        continue

                # Check section/batch not overlapping
                if self._check_section_batch_overlap(task.section_id, task.batch_id, day, start_time, end_time):
                    continue

                # Find suitable rooms
                for room in self.rooms:
                    # Check room available on this day
                    room_days = room.get('available_days')
                    if room_days is not None and day not in room_days:
                        continue

                    # Check room type
                    if task.session_type == 'practical':
                        if room.get('room_type') != 'laboratory':
                            continue
                        if task.required_lab_type and room.get('lab_type', '') != task.required_lab_type:
                            continue
                    else:
                        # Theory can use classroom or laboratory (classroom preferred via scoring)
                        pass

                    # Check capacity
                    if room.get('capacity', 0) < task.student_count:
                        continue

                    # Check room not occupied
                    if room['id'] in self.room_occupied:
                        if self._check_overlap(self.room_occupied[room['id']], day, start_time, end_time):
                            continue

                    valid.append({
                        'day': day,
                        'room_id': room['id'],
                        'start_time': start_time,
                        'end_time': end_time,
                        'room_name': room.get('name', ''),
                        'room_type': room.get('room_type', '')
                    })

        return valid

    def _score_slot(self, task: SchedulingTask, slot: dict) -> float:
        """Score a valid slot based on soft preferences. Higher is better."""
        score = 0.0
        faculty = self._get_faculty(task.faculty_id)

        # Prefer classroom for theory, lab for practical
        if task.session_type == 'theory' and slot.get('room_type') == 'classroom':
            score += 10.0
        elif task.session_type == 'practical' and slot.get('room_type') == 'laboratory':
            score += 10.0

        # Check faculty preferred slots
        if faculty:
            for pref in faculty.get('preferred_slots', []):
                if pref.get('day') == slot['day'] and times_overlap(
                    slot['start_time'], slot['end_time'],
                    pref.get('start', ''), pref.get('end', '')
                ):
                    score += 5.0

        # Prefer spreading across days - penalize days with many faculty periods
        dk = (task.faculty_id, slot['day'])
        daily_count = self.faculty_daily_periods.get(dk, 0)
        score -= daily_count * 2.0

        # Check max periods per day (soft constraint)
        if faculty:
            max_per_day = faculty.get('max_periods_per_day', 6)
            if daily_count + task.num_periods > max_per_day:
                score -= 20.0  # Strongly discourage exceeding max

        # Prefer earlier days in the week for spreading
        day_order = {'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3, 'Friday': 4, 'Saturday': 5, 'Sunday': 6}
        score -= day_order.get(slot['day'], 0) * 0.1

        return score

    def _create_tasks(self) -> list:
        """Create scheduling tasks from subjects."""
        tasks = []

        for subject in self.subjects:
            section = self._get_section(subject.get('section_id'))
            if not section:
                continue

            faculty = self._get_faculty(subject.get('faculty_id', ''))
            faculty_name = faculty['name'] if faculty else 'Unknown'
            student_count = section.get('student_strength', 0)

            # Theory tasks
            theory_count = subject.get('theory_periods_per_week', 0)
            for _ in range(theory_count):
                tasks.append(SchedulingTask(
                    subject_id=subject['id'],
                    faculty_id=subject.get('faculty_id', ''),
                    section_id=subject['section_id'],
                    programme_id=subject.get('programme_id', ''),
                    semester_id=subject.get('semester_id', ''),
                    session_type='theory',
                    num_periods=1,
                    required_lab_type='',
                    student_count=student_count,
                    subject_name=subject.get('name', ''),
                    faculty_name=faculty_name
                ))

            # Practical tasks
            prac_count = subject.get('practical_sessions_per_week', 0)
            if prac_count > 0:
                consec = subject.get('practical_consecutive_periods', 2)
                lab_type = subject.get('required_lab_type', '')
                is_for_batches = subject.get('is_for_batches', False)
                batches = section.get('practical_batches', [])

                if is_for_batches and batches:
                    # Create tasks per batch per practical session
                    for batch in batches:
                        batch_strength = batch.get('strength') or batch.get('student_count') or max(1, student_count // len(batches))
                        for _ in range(prac_count):
                            tasks.append(SchedulingTask(
                                subject_id=subject['id'],
                                faculty_id=subject.get('faculty_id', ''),
                                section_id=subject['section_id'],
                                programme_id=subject.get('programme_id', ''),
                                semester_id=subject.get('semester_id', ''),
                                session_type='practical',
                                num_periods=consec,
                                required_lab_type=lab_type,
                                batch_id=batch.get('id', ''),
                                batch_name=batch.get('name', ''),
                                student_count=batch_strength,
                                subject_name=subject.get('name', ''),
                                faculty_name=faculty_name
                            ))
                else:
                    # Whole-class practical
                    for _ in range(prac_count):
                        tasks.append(SchedulingTask(
                            subject_id=subject['id'],
                            faculty_id=subject.get('faculty_id', ''),
                            section_id=subject['section_id'],
                            programme_id=subject.get('programme_id', ''),
                            semester_id=subject.get('semester_id', ''),
                            session_type='practical',
                            num_periods=consec,
                            required_lab_type=lab_type,
                            student_count=student_count,
                            subject_name=subject.get('name', ''),
                            faculty_name=faculty_name
                        ))

        return tasks

    def _count_valid_slots(self, task: SchedulingTask) -> int:
        """Quick estimate of how constrained a task is (for sorting)."""
        return len(self._find_valid_slots(task))

    def _attempt_backtracking(self, task: SchedulingTask) -> bool:
        """Attempt to reschedule an existing flexible session to accommodate the blocked task.
        Returns True if successful, False otherwise.
        """
        if self.backtrack_count >= self.backtrack_limit:
            return False

        # Look for placed flexible sessions (not locked, not fixed)
        candidates = [
            s for s in reversed(self.scheduled)
            if not s.get('is_locked', False) and not s.get('is_fixed', False)
        ]

        for candidate in candidates:
            if self.backtrack_count >= self.backtrack_limit:
                break
            self.backtrack_count += 1

            # Temporarily unplace candidate
            self.scheduled.remove(candidate)
            self._unmark_occupied(candidate)

            # Check if task now has valid slots
            task_slots = self._find_valid_slots(task)
            if task_slots:
                # Reconstruct task object for candidate to check if candidate can find another slot
                cand_task = SchedulingTask(
                    subject_id=candidate['subject_id'],
                    faculty_id=candidate['faculty_id'],
                    section_id=candidate['section_id'],
                    programme_id=candidate.get('programme_id', ''),
                    semester_id=candidate.get('semester_id', ''),
                    session_type=candidate.get('session_type', 'theory'),
                    num_periods=candidate.get('_num_periods', 1),
                    required_lab_type='',
                    batch_id=candidate.get('batch_id', ''),
                    batch_name=candidate.get('batch_name', ''),
                    student_count=0,
                    subject_name=candidate.get('subject_name', ''),
                    faculty_name=candidate.get('faculty_name', '')
                )
                cand_subj = self._get_subject(cand_task.subject_id)
                if cand_subj:
                    cand_task.required_lab_type = cand_subj.get('required_lab_type', '')
                cand_sec = self._get_section(cand_task.section_id)
                if cand_sec:
                    cand_task.student_count = cand_sec.get('student_strength', 0)

                # Try placing task in its best slot
                scored_task_slots = [(self._score_slot(task, s), s) for s in task_slots]
                scored_task_slots.sort(key=lambda x: -x[0])

                for _, t_slot in scored_task_slots:
                    new_task_session = {
                        'id': str(uuid.uuid4()),
                        'subject_id': task.subject_id,
                        'faculty_id': task.faculty_id,
                        'section_id': task.section_id,
                        'programme_id': task.programme_id,
                        'semester_id': task.semester_id,
                        'room_id': t_slot['room_id'],
                        'room_name': t_slot.get('room_name', ''),
                        'subject_name': task.subject_name,
                        'faculty_name': task.faculty_name,
                        'day': t_slot['day'],
                        'start_time': t_slot['start_time'],
                        'end_time': t_slot['end_time'],
                        'session_type': task.session_type,
                        'batch_id': task.batch_id,
                        'batch_name': task.batch_name,
                        'is_locked': False,
                        'is_fixed': False,
                        '_num_periods': task.num_periods
                    }
                    self.scheduled.append(new_task_session)
                    self._mark_occupied(new_task_session)

                    # Now check if candidate can find a valid alternative slot
                    cand_slots = self._find_valid_slots(cand_task)
                    if cand_slots:
                        scored_cand_slots = [(self._score_slot(cand_task, s), s) for s in cand_slots]
                        scored_cand_slots.sort(key=lambda x: -x[0])
                        best_cand_slot = scored_cand_slots[0][1]

                        candidate['room_id'] = best_cand_slot['room_id']
                        candidate['room_name'] = best_cand_slot.get('room_name', '')
                        candidate['day'] = best_cand_slot['day']
                        candidate['start_time'] = best_cand_slot['start_time']
                        candidate['end_time'] = best_cand_slot['end_time']

                        self.scheduled.append(candidate)
                        self._mark_occupied(candidate)
                        return True
                    else:
                        # Rollback task placement and try next slot
                        self.scheduled.remove(new_task_session)
                        self._unmark_occupied(new_task_session)

            # Rollback: restore candidate to original slot
            self.scheduled.append(candidate)
            self._mark_occupied(candidate)

        return False

    def generate(self) -> dict:
        """Main scheduling entry point."""
        self.scheduled = []
        self.unscheduled = []
        self.conflicts = []
        self.faculty_occupied = {}
        self.room_occupied = {}
        self.section_occupied = {}
        self.batch_occupied = {}
        self.faculty_daily_periods = {}
        self.backtrack_count = 0

        # Step 1: Place locked sessions from existing schedule and locked_sessions
        locked_candidates = []
        for s in self.existing_sessions:
            if s.get('is_locked', False):
                locked_candidates.append(s)
        for s in self.locked_sessions:
            if not any(x.get('id') == s.get('id') for x in locked_candidates):
                s_copy = copy.deepcopy(s)
                s_copy['is_locked'] = True
                locked_candidates.append(s_copy)

        for session in locked_candidates:
            session_copy = copy.deepcopy(session)
            # Calculate periods if not present
            start_m = time_to_minutes(session_copy.get('start_time', '09:00'))
            end_m = time_to_minutes(session_copy.get('end_time', '10:00'))
            duration = self.settings.get('period_duration', 60)
            session_copy['_num_periods'] = max(1, (end_m - start_m) // duration) if duration > 0 else 1
            self.scheduled.append(session_copy)
            self._mark_occupied(session_copy)

        # Step 2: Place fixed sessions
        for fixed in self.fixed_sessions:
            # Check if already placed as locked
            if any(s.get('id') == fixed.get('id') for s in self.scheduled):
                continue

            subj = self._get_subject(fixed.get('subject_id'))
            fac = self._get_faculty(fixed.get('faculty_id'))
            rm = self._get_room(fixed.get('room_id'))

            start_m = time_to_minutes(fixed.get('start_time', '09:00'))
            end_m = time_to_minutes(fixed.get('end_time', '10:00'))
            duration = self.settings.get('period_duration', 60)
            num_periods = max(1, (end_m - start_m) // duration) if duration > 0 else 1

            session = {
                'id': fixed.get('id', str(uuid.uuid4())),
                'subject_id': fixed['subject_id'],
                'faculty_id': fixed['faculty_id'],
                'section_id': fixed['section_id'],
                'programme_id': fixed.get('programme_id', ''),
                'semester_id': fixed.get('semester_id', ''),
                'room_id': fixed['room_id'],
                'room_name': fixed.get('room_name') or (rm['name'] if rm else ''),
                'subject_name': fixed.get('subject_name') or (subj['name'] if subj else ''),
                'faculty_name': fixed.get('faculty_name') or (fac['name'] if fac else ''),
                'day': fixed['day'],
                'start_time': fixed['start_time'],
                'end_time': fixed['end_time'],
                'session_type': fixed.get('session_type', 'theory'),
                'batch_id': fixed.get('batch_id', ''),
                'batch_name': fixed.get('batch_name', ''),
                'is_locked': False,
                'is_fixed': True,
                '_num_periods': num_periods
            }

            # Validate fixed session doesn't conflict
            has_conflict = False
            fid = session['faculty_id']
            if fid in self.faculty_occupied:
                if self._check_overlap(self.faculty_occupied[fid], session['day'], session['start_time'], session['end_time']):
                    self.conflicts.append(f"Fixed session conflict: Faculty {session.get('faculty_name', fid)} already occupied at {session['day']} {session['start_time']}-{session['end_time']}")
                    has_conflict = True

            rid = session['room_id']
            if rid in self.room_occupied:
                if self._check_overlap(self.room_occupied[rid], session['day'], session['start_time'], session['end_time']):
                    self.conflicts.append(f"Fixed session conflict: Room {session.get('room_name', rid)} already occupied at {session['day']} {session['start_time']}-{session['end_time']}")
                    has_conflict = True

            if self._check_section_batch_overlap(session['section_id'], session.get('batch_id', ''), session['day'], session['start_time'], session['end_time']):
                self.conflicts.append(f"Fixed session conflict: Student group {session['section_id']} already occupied at {session['day']} {session['start_time']}-{session['end_time']}")
                has_conflict = True

            if not has_conflict:
                self.scheduled.append(session)
                self._mark_occupied(session)

        # Step 3: Create tasks from subjects
        all_tasks = self._create_tasks()

        # Remove tasks that are already satisfied by fixed/locked sessions
        placed_counts: Dict[Tuple[str, str, str], int] = {}
        for s in self.scheduled:
            key = (s['subject_id'], s['session_type'], s.get('batch_id', ''))
            placed_counts[key] = placed_counts.get(key, 0) + 1

        remaining_tasks = []
        task_counts: Dict[Tuple[str, str, str], int] = {}
        for task in all_tasks:
            key = (task.subject_id, task.session_type, task.batch_id)
            task_counts[key] = task_counts.get(key, 0) + 1
            placed = placed_counts.get(key, 0)
            if task_counts[key] > placed:
                remaining_tasks.append(task)

        # Step 4: Sort by constraint tightness (most constrained first)
        def task_priority(t: SchedulingTask) -> Tuple[int, int, int]:
            # Practicals first (harder to schedule: specific lab + consecutive periods)
            type_priority = 0 if t.session_type == 'practical' else 1
            # Multi-period sessions first
            period_priority = -t.num_periods
            # Tasks with fewer initial valid slots first
            slot_count = self._count_valid_slots(t)
            return (type_priority, period_priority, slot_count)

        remaining_tasks.sort(key=task_priority)

        # Step 5: Schedule each task
        for task in remaining_tasks:
            valid_slots = self._find_valid_slots(task)

            if not valid_slots:
                # Attempt limited backtracking by swapping a previously placed flexible session
                backtracked = self._attempt_backtracking(task)
                if backtracked:
                    continue

                # Identify failure reason
                reason = self._diagnose_failure(task)
                self.unscheduled.append({
                    'subject_name': task.subject_name,
                    'subject_id': task.subject_id,
                    'session_type': task.session_type,
                    'batch_name': task.batch_name,
                    'batch_id': task.batch_id,
                    'faculty_name': task.faculty_name,
                    'faculty_id': task.faculty_id,
                    'section_id': task.section_id,
                    'reason': reason
                })
                continue

            # Score and sort valid slots
            scored_slots = [(self._score_slot(task, s), s) for s in valid_slots]
            scored_slots.sort(key=lambda x: -x[0])  # highest score first

            best_slot = scored_slots[0][1]
            session = {
                'id': str(uuid.uuid4()),
                'subject_id': task.subject_id,
                'faculty_id': task.faculty_id,
                'section_id': task.section_id,
                'programme_id': task.programme_id,
                'semester_id': task.semester_id,
                'room_id': best_slot['room_id'],
                'room_name': best_slot.get('room_name', ''),
                'subject_name': task.subject_name,
                'faculty_name': task.faculty_name,
                'day': best_slot['day'],
                'start_time': best_slot['start_time'],
                'end_time': best_slot['end_time'],
                'session_type': task.session_type,
                'batch_id': task.batch_id,
                'batch_name': task.batch_name,
                'is_locked': False,
                'is_fixed': False,
                '_num_periods': task.num_periods
            }
            self.scheduled.append(session)
            self._mark_occupied(session)

        # Clean up internal fields
        for s in self.scheduled:
            s.pop('_num_periods', None)

        # Determine overall status
        if not self.unscheduled and not self.conflicts:
            status = 'success'
            message = f'Successfully scheduled {len(self.scheduled)} sessions with no conflicts.'
        elif self.scheduled and self.unscheduled:
            status = 'partial'
            message = f'Scheduled {len(self.scheduled)} sessions but {len(self.unscheduled)} sessions could not be placed.'
        else:
            status = 'failed'
            message = 'Scheduling failed with conflicts.'

        return {
            'status': status,
            'message': message,
            'scheduled_sessions': self.scheduled,
            'unscheduled_sessions': self.unscheduled,
            'conflicts': self.conflicts,
            'total_scheduled': len(self.scheduled),
            'total_unscheduled': len(self.unscheduled)
        }

    def _diagnose_failure(self, task: SchedulingTask) -> str:
        """Diagnose why a task couldn't be scheduled."""
        reasons = []
        faculty = self._get_faculty(task.faculty_id)

        if not faculty:
            return 'Faculty not found in the system'

        # Check if faculty has ANY available day matching working days
        avail_days = faculty.get('available_days')
        if avail_days is not None:
            common_days = set(avail_days) & set(self.working_days)
            if not common_days:
                return f'Faculty {faculty.get("name", task.faculty_id)} has no available days that match working days'

        # Check each day
        for day in self.working_days:
            if avail_days is not None and day not in avail_days:
                reasons.append(f'{day}: Faculty unavailable')
                continue

            day_reasons = []
            for i in range(len(self.time_slots)):
                if i + task.num_periods > len(self.time_slots):
                    break

                slot_group = self.time_slots[i:i + task.num_periods]
                is_consecutive = True
                for j in range(1, len(slot_group)):
                    if time_to_minutes(slot_group[j]['start']) != time_to_minutes(slot_group[j - 1]['end']):
                        is_consecutive = False
                        break
                if not is_consecutive:
                    continue

                start_time = slot_group[0]['start']
                end_time = slot_group[-1]['end']

                if not is_faculty_available(faculty, day, start_time, end_time):
                    day_reasons.append(f'{start_time}-{end_time}: Faculty unavailable')
                elif task.faculty_id in self.faculty_occupied and self._check_overlap(self.faculty_occupied[task.faculty_id], day, start_time, end_time):
                    day_reasons.append(f'{start_time}-{end_time}: Faculty already teaching')
                elif self._check_section_batch_overlap(task.section_id, task.batch_id, day, start_time, end_time):
                    day_reasons.append(f'{start_time}-{end_time}: Student group has another session')
                else:
                    # Check rooms
                    room_found = False
                    for room in self.rooms:
                        room_days = room.get('available_days')
                        if room_days is not None and day not in room_days:
                            continue
                        if task.session_type == 'practical' and room.get('room_type') != 'laboratory':
                            continue
                        if task.required_lab_type and room.get('lab_type', '') != task.required_lab_type:
                            continue
                        if room.get('capacity', 0) < task.student_count:
                            continue
                        if room['id'] in self.room_occupied and self._check_overlap(self.room_occupied[room['id']], day, start_time, end_time):
                            continue
                        room_found = True
                        break

                    if not room_found:
                        if task.session_type == 'practical':
                            day_reasons.append(f'{start_time}-{end_time}: No suitable lab available (need {task.required_lab_type}, capacity >= {task.student_count})')
                        else:
                            day_reasons.append(f'{start_time}-{end_time}: No suitable room available (capacity >= {task.student_count})')

            if day_reasons:
                reasons.append(f'{day}: ' + '; '.join(day_reasons[:3]))

        if reasons:
            return 'All slots blocked: ' + ' | '.join(reasons[:3])
        return 'No valid time/room combination found (all slots occupied)'


def run_scheduler(data: dict) -> dict:
    """Main entry point for scheduling."""
    engine = SchedulerEngine(data)
    return engine.generate()
