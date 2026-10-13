"""Data models for NFSU Smart Academic Timetable Generator.
Uses dataclasses + JSON file storage for simplicity.
All IDs are UUIDs. All times stored as 'HH:MM' strings.
"""
import json
import os
import uuid
import copy
import threading
from dataclasses import dataclass, field, asdict
from typing import Optional
from pathlib import Path

DATA_FILE = Path(__file__).parent / 'data.json'
_lock = threading.Lock()

def gen_id() -> str:
    return str(uuid.uuid4())

@dataclass
class UniversitySettings:
    name: str = 'National Forensic Sciences University'
    department: str = 'School of Cyber Security & Digital Forensics'
    working_days: list = field(default_factory=lambda: ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'])
    start_time: str = '09:00'
    end_time: str = '17:00'
    period_duration: int = 60  # minutes
    breaks: list = field(default_factory=list)  # [{"name": "Lunch", "start": "13:00", "end": "14:00"}]

@dataclass
class Room:
    id: str = field(default_factory=gen_id)
    name: str = ''
    capacity: int = 40
    room_type: str = 'classroom'  # 'classroom' or 'laboratory'
    lab_type: str = ''  # e.g., 'CS Lab', 'Network Lab' - only for laboratories
    available_days: list = field(default_factory=lambda: ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'])

@dataclass
class Programme:
    id: str = field(default_factory=gen_id)
    name: str = ''
    code: str = ''
    duration_years: int = 2
    semesters: list = field(default_factory=list)  # list of Semester dicts

@dataclass 
class Semester:
    id: str = field(default_factory=gen_id)
    programme_id: str = ''
    number: int = 1
    sections: list = field(default_factory=list)  # list of Section dicts

@dataclass
class Section:
    id: str = field(default_factory=gen_id)
    semester_id: str = ''
    programme_id: str = ''
    name: str = 'A'
    student_strength: int = 40
    practical_batches: list = field(default_factory=list)  # [{"id": "...", "name": "B1", "strength": 20}]

@dataclass
class Faculty:
    id: str = field(default_factory=gen_id)
    name: str = ''
    employee_id: str = ''
    available_days: list = field(default_factory=lambda: ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'])
    available_time_start: str = '09:00'
    available_time_end: str = '17:00'
    unavailable_slots: list = field(default_factory=list)  # [{"day": "Monday", "start": "09:00", "end": "10:00"}]
    max_periods_per_day: int = 6
    preferred_slots: list = field(default_factory=list)  # [{"day": "Monday", "start": "09:00", "end": "10:00"}]

@dataclass
class Subject:
    id: str = field(default_factory=gen_id)
    name: str = ''
    code: str = ''
    section_id: str = ''
    programme_id: str = ''
    semester_id: str = ''
    faculty_id: str = ''
    theory_periods_per_week: int = 3
    practical_sessions_per_week: int = 0
    practical_consecutive_periods: int = 2
    required_lab_type: str = ''  # must match a lab's lab_type
    is_for_batches: bool = False  # True if practicals are per-batch

@dataclass
class FixedSession:
    id: str = field(default_factory=gen_id)
    subject_id: str = ''
    faculty_id: str = ''
    section_id: str = ''
    room_id: str = ''
    day: str = ''
    start_time: str = ''
    end_time: str = ''
    session_type: str = 'theory'  # 'theory' or 'practical'
    batch_id: str = ''  # if practical for specific batch

@dataclass
class ScheduledSession:
    id: str = field(default_factory=gen_id)
    subject_id: str = ''
    faculty_id: str = ''
    section_id: str = ''
    programme_id: str = ''
    semester_id: str = ''
    room_id: str = ''
    day: str = ''
    start_time: str = ''
    end_time: str = ''
    session_type: str = 'theory'
    batch_id: str = ''
    batch_name: str = ''
    is_locked: bool = False
    is_fixed: bool = False

@dataclass
class TimetableState:
    status: str = 'draft'  # 'draft', 'generated', 'published'
    generation_status: str = ''  # 'success', 'partial', 'failed', ''
    generation_message: str = ''
    unscheduled_sessions: list = field(default_factory=list)
    conflicts: list = field(default_factory=list)
    last_generated: str = ''

@dataclass
class AppData:
    settings: dict = field(default_factory=lambda: asdict(UniversitySettings()))
    rooms: list = field(default_factory=list)
    programmes: list = field(default_factory=list)
    faculty: list = field(default_factory=list)
    subjects: list = field(default_factory=list)
    fixed_sessions: list = field(default_factory=list)
    scheduled_sessions: list = field(default_factory=list)
    timetable_state: dict = field(default_factory=lambda: asdict(TimetableState()))
    demo_data_loaded: bool = False

def load_data() -> dict:
    """Load all app data from JSON file. Thread-safe."""
    with _lock:
        if DATA_FILE.exists():
            try:
                with open(DATA_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return asdict(AppData())

def save_data(data: dict) -> None:
    """Save all app data to JSON file. Thread-safe with atomic write."""
    with _lock:
        DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp_file = DATA_FILE.with_suffix('.tmp')
        try:
            with open(tmp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            tmp_file.replace(DATA_FILE)  # atomic on POSIX
        except Exception:
            if tmp_file.exists():
                tmp_file.unlink()
            raise

def get_item_by_id(items: list, item_id: str) -> Optional[dict]:
    """Find an item by ID in a list of dicts."""
    for item in items:
        if item.get('id') == item_id:
            return item
    return None

def remove_item_by_id(items: list, item_id: str) -> bool:
    """Remove an item by ID from a list. Returns True if found."""
    for i, item in enumerate(items):
        if item.get('id') == item_id:
            items.pop(i)
            return True
    return False

def update_item_by_id(items: list, item_id: str, updates: dict) -> bool:
    """Update an item's fields by ID. Returns True if found."""
    for item in items:
        if item.get('id') == item_id:
            item.update(updates)
            return True
    return False
