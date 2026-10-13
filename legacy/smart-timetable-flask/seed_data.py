"""Demo data seeding for NFSU Smart Academic Timetable Generator.

Provides deterministic demo data for National Forensic Sciences University (NFSU),
School of Cyber Security & Digital Forensics.
Includes classrooms, laboratories, faculty with preferences/constraints,
programmes, semesters, sections with batches, subjects, and fixed sessions.
"""
import uuid
from dataclasses import asdict

from models import (
    UniversitySettings,
    Room,
    Programme,
    Semester,
    Section,
    Faculty,
    Subject,
    FixedSession,
    TimetableState,
    AppData,
)

# Fixed namespace UUID to guarantee deterministic UUID generation for seed data
DEMO_NAMESPACE = uuid.UUID('7b1e42c2-7cb3-4874-9b21-897dbfa401a8')

def demo_id(key: str) -> str:
    """Generate a deterministic UUID string based on a key."""
    return str(uuid.uuid5(DEMO_NAMESPACE, key))

def seed_demo_data() -> dict:
    """Create and return a complete AppData dict populated with NFSU demo data.
    
    The resulting dictionary is fully schedulable, respects all constraints,
    and is ready to be saved via models.save_data().
    """
    # 1. University Settings
    settings = UniversitySettings(
        name='National Forensic Sciences University',
        department='School of Cyber Security & Digital Forensics',
        working_days=['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'],
        start_time='09:00',
        end_time='17:00',
        period_duration=60,
        breaks=[{
            'name': 'Lunch',
            'start': '13:00',
            'end': '14:00'
        }]
    )

    # 2. Rooms & Laboratories
    rooms = [
        Room(
            id=demo_id('room_cr101'),
            name='CR-101',
            capacity=60,
            room_type='classroom',
            lab_type='',
            available_days=['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        ),
        Room(
            id=demo_id('room_cr102'),
            name='CR-102',
            capacity=40,
            room_type='classroom',
            lab_type='',
            available_days=['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        ),
        Room(
            id=demo_id('room_cr103'),
            name='CR-103',
            capacity=40,
            room_type='classroom',
            lab_type='',
            available_days=['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        ),
        Room(
            id=demo_id('room_cr104'),
            name='CR-104',
            capacity=30,
            room_type='classroom',
            lab_type='',
            available_days=['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        ),
        Room(
            id=demo_id('room_cslab1'),
            name='CS Lab 1',
            capacity=25,
            room_type='laboratory',
            lab_type='CS Lab',
            available_days=['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        ),
        Room(
            id=demo_id('room_cslab2'),
            name='CS Lab 2',
            capacity=25,
            room_type='laboratory',
            lab_type='CS Lab',
            available_days=['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        ),
        Room(
            id=demo_id('room_netlab'),
            name='Network Lab',
            capacity=20,
            room_type='laboratory',
            lab_type='Network Lab',
            available_days=['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        ),
        Room(
            id=demo_id('room_forensicslab'),
            name='Digital Forensics Lab',
            capacity=20,
            room_type='laboratory',
            lab_type='Forensics Lab',
            available_days=['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        ),
    ]

    # 3. Faculty Members
    faculty = [
        Faculty(
            id=demo_id('faculty_sharma'),
            name='Dr. Sharma',
            employee_id='NFSU-FAC-001',
            available_days=['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'],
            available_time_start='09:00',
            available_time_end='17:00',
            unavailable_slots=[],
            max_periods_per_day=6,
            preferred_slots=[
                {'day': 'Monday', 'start': '09:00', 'end': '12:00'},
                {'day': 'Tuesday', 'start': '09:00', 'end': '12:00'},
                {'day': 'Wednesday', 'start': '09:00', 'end': '12:00'},
                {'day': 'Thursday', 'start': '09:00', 'end': '12:00'},
                {'day': 'Friday', 'start': '09:00', 'end': '12:00'},
            ]
        ),
        Faculty(
            id=demo_id('faculty_patel'),
            name='Dr. Patel',
            employee_id='NFSU-FAC-002',
            available_days=['Monday', 'Tuesday', 'Wednesday', 'Thursday'],
            available_time_start='09:00',
            available_time_end='17:00',
            unavailable_slots=[],
            max_periods_per_day=6,
            preferred_slots=[]
        ),
        Faculty(
            id=demo_id('faculty_singh'),
            name='Prof. Singh',
            employee_id='NFSU-FAC-003',
            available_days=['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'],
            available_time_start='09:00',
            available_time_end='17:00',
            unavailable_slots=[],
            max_periods_per_day=6,
            preferred_slots=[]
        ),
        Faculty(
            id=demo_id('faculty_gupta'),
            name='Dr. Gupta',
            employee_id='NFSU-FAC-004',
            available_days=['Tuesday', 'Wednesday', 'Thursday', 'Friday'],
            available_time_start='09:00',
            available_time_end='17:00',
            unavailable_slots=[],
            max_periods_per_day=6,
            preferred_slots=[]
        ),
        Faculty(
            id=demo_id('faculty_mehta'),
            name='Prof. Mehta',
            employee_id='NFSU-FAC-005',
            available_days=['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'],
            available_time_start='09:00',
            available_time_end='17:00',
            unavailable_slots=[],
            max_periods_per_day=6,
            preferred_slots=[]
        ),
        Faculty(
            id=demo_id('faculty_verma'),
            name='Dr. Verma',
            employee_id='NFSU-FAC-006',
            available_days=['Monday', 'Wednesday', 'Friday'],
            available_time_start='09:00',
            available_time_end='17:00',
            unavailable_slots=[],
            max_periods_per_day=6,
            preferred_slots=[]
        ),
    ]

    # IDs for Programmes, Semesters, Sections
    prog_btech_id = demo_id('prog_btech_cse_cs')
    sem_btech_s1_id = demo_id('sem_btech_cse_cs_s1')
    sec_btech_a_id = demo_id('sec_btech_cse_cs_s1_a')

    prog_mtech_cs_id = demo_id('prog_mtech_cs')
    sem_mtech_cs_s1_id = demo_id('sem_mtech_cs_s1')
    sec_mtech_cs_a_id = demo_id('sec_mtech_cs_s1_a')

    prog_mtech_aids_id = demo_id('prog_mtech_aids')
    sem_mtech_aids_s1_id = demo_id('sem_mtech_aids_s1')
    sec_mtech_aids_a_id = demo_id('sec_mtech_aids_s1_a')

    prog_msc_cs_id = demo_id('prog_msc_cs')
    sem_msc_cs_s1_id = demo_id('sem_msc_cs_s1')
    sec_msc_cs_a_id = demo_id('sec_msc_cs_s1_a')

    prog_msc_dfis_id = demo_id('prog_msc_dfis')
    sem_msc_dfis_s1_id = demo_id('sem_msc_dfis_s1')
    sec_msc_dfis_a_id = demo_id('sec_msc_dfis_s1_a')

    # 4. Programmes with Semesters & Sections
    programmes = [
        # BTech_MTech CSE CS (5-year Integrated)
        Programme(
            id=prog_btech_id,
            name='B.Tech-M.Tech Computer Science & Engineering (Cyber Security)',
            code='BTECH-MTECH-CSE-CS',
            duration_years=5,
            semesters=[
                asdict(Semester(
                    id=sem_btech_s1_id,
                    programme_id=prog_btech_id,
                    number=1,
                    sections=[
                        asdict(Section(
                            id=sec_btech_a_id,
                            semester_id=sem_btech_s1_id,
                            programme_id=prog_btech_id,
                            name='A',
                            student_strength=40,
                            practical_batches=[
                                {'id': demo_id('batch_btech_b1'), 'name': 'B1', 'strength': 20},
                                {'id': demo_id('batch_btech_b2'), 'name': 'B2', 'strength': 20},
                            ]
                        ))
                    ]
                ))
            ]
        ),
        # MTech CS (2-year)
        Programme(
            id=prog_mtech_cs_id,
            name='M.Tech Cyber Security',
            code='MTECH-CS',
            duration_years=2,
            semesters=[
                asdict(Semester(
                    id=sem_mtech_cs_s1_id,
                    programme_id=prog_mtech_cs_id,
                    number=1,
                    sections=[
                        asdict(Section(
                            id=sec_mtech_cs_a_id,
                            semester_id=sem_mtech_cs_s1_id,
                            programme_id=prog_mtech_cs_id,
                            name='A',
                            student_strength=30,
                            practical_batches=[
                                {'id': demo_id('batch_mtech_cs_b1'), 'name': 'B1', 'strength': 15},
                                {'id': demo_id('batch_mtech_cs_b2'), 'name': 'B2', 'strength': 15},
                            ]
                        ))
                    ]
                ))
            ]
        ),
        # MTech AIDS (2-year)
        Programme(
            id=prog_mtech_aids_id,
            name='M.Tech Artificial Intelligence & Data Science',
            code='MTECH-AIDS',
            duration_years=2,
            semesters=[
                asdict(Semester(
                    id=sem_mtech_aids_s1_id,
                    programme_id=prog_mtech_aids_id,
                    number=1,
                    sections=[
                        asdict(Section(
                            id=sec_mtech_aids_a_id,
                            semester_id=sem_mtech_aids_s1_id,
                            programme_id=prog_mtech_aids_id,
                            name='A',
                            student_strength=30,
                            practical_batches=[
                                {'id': demo_id('batch_mtech_aids_b1'), 'name': 'B1', 'strength': 15},
                                {'id': demo_id('batch_mtech_aids_b2'), 'name': 'B2', 'strength': 15},
                            ]
                        ))
                    ]
                ))
            ]
        ),
        # MSc CS (2-year)
        Programme(
            id=prog_msc_cs_id,
            name='M.Sc. Cyber Security',
            code='MSC-CS',
            duration_years=2,
            semesters=[
                asdict(Semester(
                    id=sem_msc_cs_s1_id,
                    programme_id=prog_msc_cs_id,
                    number=1,
                    sections=[
                        asdict(Section(
                            id=sec_msc_cs_a_id,
                            semester_id=sem_msc_cs_s1_id,
                            programme_id=prog_msc_cs_id,
                            name='A',
                            student_strength=25,
                            practical_batches=[]
                        ))
                    ]
                ))
            ]
        ),
        # MSc DFIS (2-year)
        Programme(
            id=prog_msc_dfis_id,
            name='M.Sc. Digital Forensics & Information Security',
            code='MSC-DFIS',
            duration_years=2,
            semesters=[
                asdict(Semester(
                    id=sem_msc_dfis_s1_id,
                    programme_id=prog_msc_dfis_id,
                    number=1,
                    sections=[
                        asdict(Section(
                            id=sec_msc_dfis_a_id,
                            semester_id=sem_msc_dfis_s1_id,
                            programme_id=prog_msc_dfis_id,
                            name='A',
                            student_strength=25,
                            practical_batches=[]
                        ))
                    ]
                ))
            ]
        ),
    ]

    # 5. Subjects
    subjects = [
        # BTech CSE Semester 1 Section A Subjects
        Subject(
            id=demo_id('subj_cs101'),
            name='Data Structures',
            code='CS101',
            section_id=sec_btech_a_id,
            programme_id=prog_btech_id,
            semester_id=sem_btech_s1_id,
            faculty_id=demo_id('faculty_sharma'),
            theory_periods_per_week=3,
            practical_sessions_per_week=1,
            practical_consecutive_periods=2,
            required_lab_type='CS Lab',
            is_for_batches=True
        ),
        Subject(
            id=demo_id('subj_cs102'),
            name='Digital Logic',
            code='CS102',
            section_id=sec_btech_a_id,
            programme_id=prog_btech_id,
            semester_id=sem_btech_s1_id,
            faculty_id=demo_id('faculty_patel'),
            theory_periods_per_week=3,
            practical_sessions_per_week=0,
            practical_consecutive_periods=2,
            required_lab_type='',
            is_for_batches=False
        ),
        Subject(
            id=demo_id('subj_ma101'),
            name='Mathematics-I',
            code='MA101',
            section_id=sec_btech_a_id,
            programme_id=prog_btech_id,
            semester_id=sem_btech_s1_id,
            faculty_id=demo_id('faculty_singh'),
            theory_periods_per_week=4,
            practical_sessions_per_week=0,
            practical_consecutive_periods=2,
            required_lab_type='',
            is_for_batches=False
        ),
        Subject(
            id=demo_id('subj_hs101'),
            name='Communication Skills',
            code='HS101',
            section_id=sec_btech_a_id,
            programme_id=prog_btech_id,
            semester_id=sem_btech_s1_id,
            faculty_id=demo_id('faculty_gupta'),
            theory_periods_per_week=2,
            practical_sessions_per_week=0,
            practical_consecutive_periods=2,
            required_lab_type='',
            is_for_batches=False
        ),
        Subject(
            id=demo_id('subj_cs103'),
            name='Introduction to Cyber Security',
            code='CS103',
            section_id=sec_btech_a_id,
            programme_id=prog_btech_id,
            semester_id=sem_btech_s1_id,
            faculty_id=demo_id('faculty_mehta'),
            theory_periods_per_week=3,
            practical_sessions_per_week=1,
            practical_consecutive_periods=2,
            required_lab_type='CS Lab',
            is_for_batches=True
        ),

        # MTech CS Semester 1 Section A Subjects
        Subject(
            id=demo_id('subj_cs501'),
            name='Advanced Algorithms',
            code='CS501',
            section_id=sec_mtech_cs_a_id,
            programme_id=prog_mtech_cs_id,
            semester_id=sem_mtech_cs_s1_id,
            faculty_id=demo_id('faculty_sharma'),
            theory_periods_per_week=3,
            practical_sessions_per_week=0,
            practical_consecutive_periods=2,
            required_lab_type='',
            is_for_batches=False
        ),
        Subject(
            id=demo_id('subj_cs502'),
            name='Machine Learning',
            code='CS502',
            section_id=sec_mtech_cs_a_id,
            programme_id=prog_mtech_cs_id,
            semester_id=sem_mtech_cs_s1_id,
            faculty_id=demo_id('faculty_verma'),
            theory_periods_per_week=3,
            practical_sessions_per_week=1,
            practical_consecutive_periods=2,
            required_lab_type='CS Lab',
            is_for_batches=True
        ),
        Subject(
            id=demo_id('subj_cs503'),
            name='Research Methodology',
            code='CS503',
            section_id=sec_mtech_cs_a_id,
            programme_id=prog_mtech_cs_id,
            semester_id=sem_mtech_cs_s1_id,
            faculty_id=demo_id('faculty_singh'),
            theory_periods_per_week=2,
            practical_sessions_per_week=0,
            practical_consecutive_periods=2,
            required_lab_type='',
            is_for_batches=False
        ),
    ]

    # 6. Fixed Sessions
    # Mathematics-I fixed on Monday 09:00-10:00 in CR-101
    fixed_sessions = [
        FixedSession(
            id=demo_id('fixed_ma101_mon_09_10'),
            subject_id=demo_id('subj_ma101'),
            faculty_id=demo_id('faculty_singh'),
            section_id=sec_btech_a_id,
            room_id=demo_id('room_cr101'),
            day='Monday',
            start_time='09:00',
            end_time='10:00',
            session_type='theory',
            batch_id=''
        )
    ]

    # Construct the full AppData object
    app_data = AppData(
        settings=asdict(settings),
        rooms=[asdict(r) for r in rooms],
        programmes=[asdict(p) for p in programmes],
        faculty=[asdict(f) for f in faculty],
        subjects=[asdict(s) for s in subjects],
        fixed_sessions=[asdict(fs) for fs in fixed_sessions],
        scheduled_sessions=[],
        timetable_state=asdict(TimetableState(
            status='draft',
            generation_status='',
            generation_message='',
            unscheduled_sessions=[],
            conflicts=[],
            last_generated=''
        )),
        demo_data_loaded=True
    )

    return asdict(app_data)


def is_demo_data_loaded(data: dict) -> bool:
    """Check if demo data is loaded in the application state."""
    if not isinstance(data, dict):
        return False
    return bool(data.get('demo_data_loaded', False))
