import * as db from '@/data/fixtures'
import { allBlocks, allSections, facultyLoad, roomUtilisation, toMin } from './timetable'

const inside = (t: string, r: { start: string; end: string }) => toMin(r.start) <= toMin(t) && toMin(t) < toMin(r.end)

/** Share of sessions taught by faculty with preferences that land inside a preferred window. */
function preferredScore() {
  const withPrefs = db.faculty.filter((f) => f.preferred_slots.length)
  const sessions = db.scheduledSessions.filter((s) => withPrefs.some((f) => f.id === s.faculty_id))
  if (!sessions.length) return 100
  const hit = sessions.filter((s) =>
    withPrefs.find((f) => f.id === s.faculty_id)!.preferred_slots.some((p) => p.day === s.day && inside(s.start_time, p)),
  )
  return Math.round((hit.length / sessions.length) * 100)
}

/** How evenly each section's periods are spread over the week (100 = perfectly even). */
function balanceScore() {
  const scores = allSections
    .map(({ section }) => {
      const counts = db.settings.working_days.map((d) => db.scheduledSessions.filter((s) => s.section_id === section.id && s.day === d).length)
      const total = counts.reduce((a, b) => a + b, 0)
      if (!total) return null
      const mean = total / counts.length
      const dev = Math.sqrt(counts.reduce((a, c) => a + (c - mean) ** 2, 0) / counts.length)
      return Math.max(0, 1 - dev / Math.max(mean, 1))
    })
    .filter((x): x is number => x !== null)
  return Math.round((scores.reduce((a, b) => a + b, 0) / scores.length) * 100)
}

/** Share of subjects whose theory lectures never repeat on the same day. */
function spreadScore() {
  const theory = db.subjects.filter((s) => s.theory_periods_per_week > 0)
  const ok = theory.filter((s) => {
    const days = db.scheduledSessions.filter((x) => x.subject_id === s.id && x.session_type === 'theory').map((x) => x.day)
    return new Set(days).size === days.length
  })
  return Math.round((ok.length / theory.length) * 100)
}

export const HARD_CONSTRAINTS = [
  'University hours & break isolation',
  'Faculty availability windows',
  'No faculty double-booking',
  'No room double-booking',
  'No student-group overlap',
  'Theory vs lab batch separation',
  'Room capacity ≥ cohort strength',
  'Lab specialisation matching',
  'Practicals in consecutive periods',
  'Fixed & locked sessions preserved',
]

export function insights() {
  const loads = db.faculty.map((f) => ({ f, ...facultyLoad(f) })).sort((a, b) => b.periods - a.periods)
  const rooms = db.rooms.map((r) => ({ r, ...roomUtilisation(r) }))
  const demand = db.subjects.reduce((n, s) => {
    const sec = allSections.find((x) => x.section.id === s.section_id)!.section
    const batches = s.is_for_batches ? Math.max(1, sec.practical_batches.length) : 1
    return n + s.theory_periods_per_week + s.practical_sessions_per_week * s.practical_consecutive_periods * batches
  }, 0)
  return {
    periods: db.scheduledSessions.length,
    demand,
    blocks: allBlocks.length,
    students: allSections.reduce((n, s) => n + s.section.student_strength, 0),
    loads,
    rooms,
    avgUtil: Math.round(rooms.reduce((n, r) => n + r.pct, 0) / rooms.length),
    soft: [
      { label: 'Preferred faculty slots honoured', value: preferredScore() },
      { label: 'Daily load balanced per section', value: balanceScore() },
      { label: 'Subjects spread across weekdays', value: spreadScore() },
    ],
  }
}
