export type Day = 'Monday' | 'Tuesday' | 'Wednesday' | 'Thursday' | 'Friday' | 'Saturday'

export interface TimeRange {
  day: string
  start: string
  end: string
}

export interface Settings {
  name: string
  department: string
  working_days: string[]
  start_time: string
  end_time: string
  period_duration: number
  breaks: { name: string; start: string; end: string }[]
}

export interface Room {
  id: string
  name: string
  capacity: number
  room_type: 'classroom' | 'laboratory' | string
  lab_type: string
  available_days: string[]
}

export interface Batch {
  id: string
  name: string
  strength: number
}

export interface Section {
  id: string
  semester_id: string
  programme_id: string
  name: string
  student_strength: number
  practical_batches: Batch[]
}

export interface Semester {
  id: string
  programme_id: string
  number: number
  sections: Section[]
}

export interface Programme {
  id: string
  name: string
  code: string
  duration_years: number
  semesters: Semester[]
}

export interface Faculty {
  id: string
  name: string
  employee_id: string
  available_days: string[]
  available_time_start: string
  available_time_end: string
  unavailable_slots: TimeRange[]
  max_periods_per_day: number
  preferred_slots: TimeRange[]
}

export interface Subject {
  id: string
  name: string
  code: string
  section_id: string
  programme_id: string
  semester_id: string
  faculty_id: string
  theory_periods_per_week: number
  practical_sessions_per_week: number
  practical_consecutive_periods: number
  required_lab_type: string
  is_for_batches: boolean
}

export interface FixedSession {
  id: string
  subject_id: string
  faculty_id: string
  section_id: string
  room_id: string
  day: string
  start_time: string
  end_time: string
  session_type: string
  batch_id: string
}

export interface ScheduledSession {
  id: string
  subject_id: string
  faculty_id: string
  section_id: string
  programme_id: string
  semester_id: string
  room_id: string
  room_name?: string
  subject_name?: string
  faculty_name?: string
  day: string
  start_time: string
  end_time: string
  session_type: 'theory' | 'practical' | string
  batch_id: string
  batch_name: string
  is_locked: boolean
  is_fixed: boolean
}

export interface TimetableState {
  status: 'draft' | 'generated' | 'published' | string
  generation_status: string
  generation_message: string
  unscheduled_sessions: unknown[]
  conflicts: unknown[]
  last_generated: string
}
