import * as db from '@/data/fixtures'
import type { Faculty, Programme, Room, ScheduledSession, Section, Semester, Subject } from '@/data/types'

export const toMin = (t: string) => {
  const [h, m] = t.split(':').map(Number)
  return h * 60 + m
}
export const fromMin = (m: number) =>
  `${String(Math.floor(m / 60)).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`

export const fmt12 = (t: string) => {
  const m = toMin(t)
  const h = Math.floor(m / 60)
  const suffix = h >= 12 ? 'pm' : 'am'
  const hh = h % 12 === 0 ? 12 : h % 12
  const mm = m % 60
  return mm ? `${hh}:${String(mm).padStart(2, '0')}${suffix}` : `${hh}${suffix}`
}

export type Slot =
  | { kind: 'period'; index: number; start: string; end: string }
  | { kind: 'break'; name: string; start: string; end: string }

/** Teaching periods and breaks for the working day, derived from university settings. */
export function daySlots(settings = db.settings): Slot[] {
  const slots: Slot[] = []
  let t = toMin(settings.start_time)
  const end = toMin(settings.end_time)
  let index = 0
  while (t < end) {
    const br = settings.breaks.find((b) => toMin(b.start) === t)
    if (br) {
      slots.push({ kind: 'break', name: br.name, start: br.start, end: br.end })
      t = toMin(br.end)
      continue
    }
    const next = Math.min(t + settings.period_duration, end)
    slots.push({ kind: 'period', index: index++, start: fromMin(t), end: fromMin(next) })
    t = next
  }
  return slots
}

export const periods = () =>
  daySlots().filter((s): s is Extract<Slot, { kind: 'period' }> => s.kind === 'period')

export interface SectionRef {
  programme: Programme
  semester: Semester
  section: Section
}

export const allSections: SectionRef[] = db.programmes.flatMap((programme) =>
  programme.semesters.flatMap((semester) =>
    semester.sections.map((section) => ({ programme, semester, section })),
  ),
)

const byId = <T extends { id: string }>(items: T[]) => new Map(items.map((i) => [i.id, i]))
export const roomById = byId<Room>(db.rooms)
export const facultyById = byId<Faculty>(db.faculty)
export const subjectById = byId<Subject>(db.subjects)
export const sectionById = new Map(allSections.map((s) => [s.section.id, s]))

/** A scheduled session with its related records resolved, and consecutive practical periods merged. */
export interface Block {
  id: string
  sessionIds: string[]
  day: string
  start: string
  end: string
  type: string
  subject: Subject
  faculty: Faculty
  room: Room
  ref: SectionRef
  batch: string
  fixed: boolean
}

export function toBlocks(sessions: ScheduledSession[]): Block[] {
  const sorted = [...sessions].sort(
    (a, b) => a.day.localeCompare(b.day) || toMin(a.start_time) - toMin(b.start_time),
  )
  const blocks: Block[] = []
  for (const s of sorted) {
    const prev = blocks.at(-1)
    if (
      prev &&
      s.session_type === 'practical' &&
      prev.type === 'practical' &&
      prev.day === s.day &&
      prev.end === s.start_time &&
      prev.subject.id === s.subject_id &&
      prev.batch === s.batch_name &&
      prev.room.id === s.room_id
    ) {
      prev.end = s.end_time
      prev.sessionIds.push(s.id)
      continue
    }
    blocks.push({
      id: s.id,
      sessionIds: [s.id],
      day: s.day,
      start: s.start_time,
      end: s.end_time,
      type: s.session_type,
      subject: subjectById.get(s.subject_id)!,
      faculty: facultyById.get(s.faculty_id)!,
      room: roomById.get(s.room_id)!,
      ref: sectionById.get(s.section_id)!,
      batch: s.batch_name,
      fixed: s.is_fixed,
    })
  }
  return blocks
}

export const allBlocks = toBlocks(db.scheduledSessions)

export type ViewKind = 'section' | 'faculty' | 'room'

export function blocksFor(view: ViewKind, id: string) {
  return allBlocks.filter((b) =>
    view === 'section' ? b.ref.section.id === id : view === 'faculty' ? b.faculty.id === id : b.room.id === id,
  )
}

export const blockMinutes = (b: Block) => toMin(b.end) - toMin(b.start)

/** Periods each faculty member teaches per week (a period is one teaching hour of one session). */
export function facultyLoad(f: Faculty) {
  const sessions = db.scheduledSessions.filter((s) => s.faculty_id === f.id)
  const perDay = Object.fromEntries(db.settings.working_days.map((d) => [d, 0])) as Record<string, number>
  for (const s of sessions) perDay[s.day] = (perDay[s.day] ?? 0) + 1
  const capacity = f.max_periods_per_day * db.settings.working_days.length
  return { periods: sessions.length, perDay, capacity, peak: Math.max(...Object.values(perDay)) }
}

export function roomUtilisation(r: Room) {
  const total = periods().length * db.settings.working_days.length
  const used = db.scheduledSessions.filter((s) => s.room_id === r.id)
  const perDay = Object.fromEntries(db.settings.working_days.map((d) => [d, 0])) as Record<string, number>
  for (const s of used) perDay[s.day] = (perDay[s.day] ?? 0) + 1
  return { used: used.length, total, pct: Math.round((used.length / total) * 100), perDay }
}

export function isFree(kind: 'faculty_id' | 'room_id', id: string, day: string, start: string) {
  return !db.scheduledSessions.some((s) => s[kind] === id && s.day === day && s.start_time === start)
}

const PALETTE = [
  '#3D5A9E', '#2F7F7A', '#7B4B8A', '#B0583A', '#6E7F3A', '#4C6E91',
  '#A64D6B', '#A97A2B', '#3E8C9A', '#5A7A4E', '#8C2F39', '#555E6E',
  '#6A5ACD', '#2E6B4F', '#9C5F2E', '#4F5D9E', '#7A3E5D',
]
const subjectColors = new Map(db.subjects.map((s, i) => [s.id, PALETTE[i % PALETTE.length]]))
export const subjectColor = (id: string) => subjectColors.get(id) ?? '#555E6E'

export const shortDay = (d: string) => d.slice(0, 3)

/** The working day to show as "today"; weekends roll forward to the first working day. */
export function todayName(now = new Date()) {
  const name = now.toLocaleDateString('en-US', { weekday: 'long' })
  return db.settings.working_days.includes(name) ? name : db.settings.working_days[0]
}

export function sessionsToCsv(blocks: Block[]) {
  const head = ['Day', 'Start', 'End', 'Programme', 'Semester', 'Section', 'Batch', 'Subject Code', 'Subject', 'Type', 'Faculty', 'Room']
  const esc = (v: string | number) => `"${String(v).replace(/"/g, '""')}"`
  const rows = blocks.map((b) => [
    b.day, b.start, b.end, b.ref.programme.code, b.ref.semester.number, b.ref.section.name, b.batch || 'Whole class',
    b.subject.code, b.subject.name, b.type, b.faculty.name, b.room.name,
  ])
  return [head, ...rows].map((r) => r.map(esc).join(',')).join('\n')
}

export function downloadText(filename: string, text: string) {
  const url = URL.createObjectURL(new Blob([text], { type: 'text/csv;charset=utf-8' }))
  const a = Object.assign(document.createElement('a'), { href: url, download: filename })
  a.click()
  URL.revokeObjectURL(url)
}
