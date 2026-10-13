import { Link, createFileRoute } from '@tanstack/react-router'
import { useState } from 'react'
import { ArrowUpRight, CalendarOff, Search, Star } from 'lucide-react'
import * as db from '@/data/fixtures'
import { facultyLoad, subjectColor } from '@/lib/timetable'
import { MiniWeek } from '@/components/MiniWeek'
import { Meter, PageHeader } from '@/components/ui'

export const Route = createFileRoute('/faculty')({
  head: () => ({ meta: [{ title: 'Faculty · NFSU Smart Timetable' }] }),
  component: FacultyPage,
})

const initials = (name: string) =>
  name
    .replace(/^(Dr|Prof)\.?\s*/i, '')
    .split(/\s+/)
    .map((w) => w[0])
    .join('')
    .slice(0, 2)

function FacultyPage() {
  const [q, setQ] = useState('')
  const list = db.faculty.filter((f) => {
    const subjects = db.subjects.filter((s) => s.faculty_id === f.id)
    const hay = [f.name, f.employee_id, ...subjects.map((s) => `${s.code} ${s.name}`)].join(' ').toLowerCase()
    return hay.includes(q.toLowerCase())
  })
  const total = db.faculty.reduce((n, f) => n + facultyLoad(f).periods, 0)

  return (
    <>
      <PageHeader
        eyebrow="Faculty"
        title={
          <>
            {db.faculty.length} teachers, <span className="italic text-oxblood">{total}</span> periods a week.
          </>
        }
        lede="Availability, preferences and daily ceilings for every faculty member — the inputs the engine respects before placing a single lecture."
        actions={
          <label className="relative block">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search name, ID or subject"
              className="w-72 rounded-lg border border-rule bg-card py-2 pl-9 pr-3 text-sm shadow-card placeholder:text-muted focus:border-navy focus:outline-none"
            />
          </label>
        }
      />

      <div className="stagger grid gap-5 md:grid-cols-2 xl:grid-cols-3">
        {list.map((f) => {
          const load = facultyLoad(f)
          const subjects = db.subjects.filter((s) => s.faculty_id === f.id)
          const sessions = db.scheduledSessions.filter((s) => s.faculty_id === f.id)
          return (
            <article key={f.id} className="flex flex-col rounded-2xl border border-rule bg-card shadow-card">
              <div className="flex items-start gap-4 p-5">
                <span className="grid h-12 w-12 shrink-0 place-items-center rounded-full bg-ink font-serif text-lg text-paper">
                  {initials(f.name)}
                </span>
                <div className="min-w-0 flex-1">
                  <h2 className="font-serif text-xl leading-tight">{f.name}</h2>
                  <p className="font-mono text-[11px] text-muted">{f.employee_id}</p>
                </div>
                <div className="text-right">
                  <div className="font-serif text-3xl font-light leading-none tabular">{load.periods}</div>
                  <div className="text-[10px] text-muted">periods/wk</div>
                </div>
              </div>

              <div className="flex flex-wrap gap-1.5 px-5">
                {subjects.map((s) => (
                  <span
                    key={s.id}
                    className="rounded-md px-2 py-0.5 text-[11.5px]"
                    style={{ background: `color-mix(in oklab, ${subjectColor(s.id)} 12%, #fffdf9)`, color: subjectColor(s.id) }}
                  >
                    <span className="font-mono text-[10px]">{s.code}</span> {s.name}
                  </span>
                ))}
              </div>

              <div className="mt-5 grid grid-cols-[1fr_auto] gap-5 border-t border-rule-soft px-5 py-4">
                <MiniWeek sessions={sessions} blocked={f.unavailable_slots} />
                <dl className="w-32 space-y-3 text-[12px]">
                  <div>
                    <dt className="text-muted">Peak day</dt>
                    <dd className="mb-1 font-mono tabular">
                      {load.peak} / {f.max_periods_per_day}
                    </dd>
                    <Meter value={load.peak} max={f.max_periods_per_day} tone={load.peak >= f.max_periods_per_day ? '#8c2f39' : '#4f7a5a'} />
                  </div>
                  <div>
                    <dt className="text-muted">Hours</dt>
                    <dd className="font-mono tabular">
                      {f.available_time_start}–{f.available_time_end}
                    </dd>
                  </div>
                </dl>
              </div>

              <div className="mt-auto flex items-center justify-between gap-3 border-t border-rule-soft bg-paper/40 px-5 py-3 text-[12px] text-ink-soft">
                <span className="flex min-w-0 items-center gap-1.5 truncate">
                  {f.unavailable_slots.length ? (
                    <>
                      <CalendarOff className="h-3.5 w-3.5 text-oxblood" />
                      Away {f.unavailable_slots.map((u) => `${u.day.slice(0, 3)} ${u.start}–${u.end}`).join(', ')}
                    </>
                  ) : f.preferred_slots.length ? (
                    <>
                      <Star className="h-3.5 w-3.5 text-gold" />
                      Prefers mornings
                    </>
                  ) : (
                    'Fully available'
                  )}
                </span>
                <Link
                  to="/timetable"
                  search={{ view: 'faculty', id: f.id }}
                  className="inline-flex shrink-0 items-center gap-1 font-medium text-oxblood hover:underline"
                >
                  Week <ArrowUpRight className="h-3.5 w-3.5" />
                </Link>
              </div>
            </article>
          )
        })}
      </div>
      {list.length === 0 && <p className="py-16 text-center text-muted">No faculty match “{q}”.</p>}
    </>
  )
}
