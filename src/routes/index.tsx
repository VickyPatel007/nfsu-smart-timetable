import { Link, createFileRoute } from '@tanstack/react-router'
import { useStore } from '@tanstack/react-store'
import { ArrowRight, Check, FlaskConical, Pin, Sparkles } from 'lucide-react'
import * as db from '@/data/fixtures'
import { HARD_CONSTRAINTS, insights } from '@/lib/insights'
import { openGenerate, uiStore } from '@/lib/store'
import { allBlocks, allSections, fmt12, periods, shortDay, subjectColor } from '@/lib/timetable'
import { useToday } from '@/lib/useToday'
import { Button, Card, CardTitle, Meter, PageHeader, StatusPill } from '@/components/ui'

export const Route = createFileRoute('/')({
  component: Overview,
})

const data = insights()

function greeting(now: Date | null) {
  if (!now) return 'Welcome back'
  const h = now.getHours()
  return h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening'
}

function Overview() {
  const { now, day } = useToday()
  const status = useStore(uiStore, (s) => s.status)
  const lastGenerated = useStore(uiStore, (s) => s.lastGenerated)
  const todayDay = day ?? db.settings.working_days[0]
  const isWeekend = now ? !db.settings.working_days.includes(now.toLocaleDateString('en-US', { weekday: 'long' })) : false
  const todays = allBlocks.filter((b) => b.day === todayDay).sort((a, b) => a.start.localeCompare(b.start))

  return (
    <>
      <PageHeader
        eyebrow={
          now
            ? now.toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }) + ' · Odd Semester'
            : 'Odd Semester 2026–27'
        }
        title={
          <>
            {greeting(now)}. This week runs with <em className="font-normal italic text-oxblood">zero clashes</em>.
          </>
        }
        lede={`${data.periods} teaching periods across ${db.programmes.length} programmes, ${db.faculty.length} faculty and ${db.rooms.length} rooms — every hard constraint satisfied.`}
        actions={
          <>
            <Button variant="primary" onClick={() => openGenerate(true)}>
              <Sparkles className="h-4 w-4 text-gold" /> Regenerate
            </Button>
            <Link
              to="/timetable"
              search={{ view: 'section' }}
              className="inline-flex items-center gap-2 rounded-lg border border-rule bg-card px-3.5 py-2 text-[13px] font-medium shadow-card transition hover:border-ink/25"
            >
              Open timetable <ArrowRight className="h-4 w-4" />
            </Link>
          </>
        }
      />

      {/* Headline figures */}
      <div className="stagger grid grid-cols-2 gap-px overflow-hidden rounded-2xl border border-rule bg-rule shadow-card lg:grid-cols-4">
        {[
          { v: data.periods, l: 'Periods scheduled', s: `of ${data.demand} required · ${Math.round((data.periods / data.demand) * 100)}% met` },
          { v: data.students, l: 'Students served', s: `${allSections.length} sections · ${db.subjects.length} subjects` },
          { v: `${data.avgUtil}%`, l: 'Avg. room utilisation', s: `${db.rooms.filter((r) => r.room_type === 'laboratory').length} specialised labs` },
          { v: 0, l: 'Hard conflicts', s: 'Validated against 10 rules', good: true },
        ].map((k) => (
          <div key={k.l} className="bg-card px-5 py-5 sm:px-6">
            <p className="text-[13px] text-ink-soft">{k.l}</p>
            <p className={`mt-1 font-serif text-[2.75rem] font-light leading-none tabular ${k.good ? 'text-sage' : ''}`}>{k.v}</p>
            <p className="mt-2 text-xs text-muted">{k.s}</p>
          </div>
        ))}
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-[1.35fr_1fr]">
        <Card>
          <CardTitle
            title={isWeekend ? `Next up · ${todayDay}` : `On campus today · ${todayDay}`}
            hint={`${todays.length} sessions · ${new Set(todays.map((b) => b.room.id)).size} rooms in use`}
            action={
              <Link to="/timetable" search={{ view: 'room' }} className="text-xs font-medium text-oxblood hover:underline">
                Room view
              </Link>
            }
          />
          <ol className="relative max-h-[460px] overflow-y-auto px-5 py-4">
            <span className="absolute bottom-6 left-[86px] top-6 w-px bg-rule" />
            {todays.map((b) => {
              const color = subjectColor(b.subject.id)
              return (
                <li key={b.id} className="relative grid grid-cols-[62px_1fr] gap-6 py-2.5">
                  <span className="pt-0.5 text-right font-mono text-[11px] text-ink-soft tabular">
                    {b.start}
                    <span className="block text-muted">{b.end}</span>
                  </span>
                  <span className="absolute left-[63px] top-4 h-2.5 w-2.5 rounded-full ring-4 ring-card" style={{ background: color }} />
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-x-2">
                      <span className="font-serif text-[15.5px]">{b.subject.name}</span>
                      {b.type === 'practical' && (
                        <span className="inline-flex items-center gap-1 text-[11px] font-medium text-sage">
                          <FlaskConical className="h-3 w-3" /> Lab {b.batch}
                        </span>
                      )}
                      {b.fixed && <Pin className="h-3 w-3 text-ochre" />}
                    </div>
                    <p className="text-xs text-muted">
                      {b.ref.programme.code} · Sec {b.ref.section.name} — {b.faculty.name} · {b.room.name}
                    </p>
                  </div>
                </li>
              )
            })}
          </ol>
        </Card>

        <Card>
          <CardTitle
            title="Constraint health"
            hint={lastGenerated && now ? `Last run ${new Date(lastGenerated).toLocaleString('en-GB', { dateStyle: 'medium', timeStyle: 'short' })}` : undefined}
            action={<StatusPill status={status} />}
          />
          <div className="px-5 py-4">
            <ul className="grid grid-cols-1 gap-x-4 gap-y-2 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2">
              {HARD_CONSTRAINTS.map((c) => (
                <li key={c} className="flex items-start gap-2 text-[12.5px] leading-snug text-ink-soft">
                  <span className="mt-px grid h-4 w-4 shrink-0 place-items-center rounded-full bg-sage/15 text-sage">
                    <Check className="h-2.5 w-2.5" strokeWidth={3.5} />
                  </span>
                  {c}
                </li>
              ))}
            </ul>
            <div className="mt-5 space-y-3 border-t border-rule-soft pt-4">
              <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted">Soft optimisation</p>
              {data.soft.map((s) => (
                <div key={s.label}>
                  <div className="mb-1 flex justify-between text-[12.5px]">
                    <span>{s.label}</span>
                    <span className="font-mono tabular text-ink-soft">{s.value}%</span>
                  </div>
                  <Meter value={s.value} max={100} tone={s.value >= 80 ? '#4f7a5a' : '#b5852f'} />
                </div>
              ))}
            </div>
          </div>
        </Card>
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Card>
          <CardTitle
            title="Faculty load"
            hint="Periods per week against each member’s weekly ceiling"
            action={
              <Link to="/faculty" className="text-xs font-medium text-oxblood hover:underline">
                All faculty
              </Link>
            }
          />
          <ul className="divide-y divide-rule-soft px-5 py-2">
            {data.loads.map(({ f, periods: p, capacity, peak }) => (
              <li key={f.id} className="grid grid-cols-[120px_1fr_64px] items-center gap-4 py-2.5">
                <Link to="/timetable" search={{ view: 'faculty', id: f.id }} className="truncate text-[13.5px] hover:text-oxblood">
                  {f.name}
                </Link>
                <Meter value={p} max={Math.min(capacity, 20)} tone={peak >= f.max_periods_per_day ? '#8c2f39' : '#22346b'} />
                <span className="text-right font-mono text-[11px] text-ink-soft tabular">
                  {p} <span className="text-muted">· pk {peak}</span>
                </span>
              </li>
            ))}
          </ul>
        </Card>

        <Card>
          <CardTitle
            title="Room occupancy"
            hint={`Periods booked per day, out of ${periods().length}`}
            action={
              <Link to="/rooms" className="text-xs font-medium text-oxblood hover:underline">
                Rooms & labs
              </Link>
            }
          />
          <div className="overflow-x-auto px-5 py-4">
            <table className="w-full border-separate border-spacing-1 text-[12px]">
              <thead>
                <tr>
                  <th />
                  {db.settings.working_days.map((d) => (
                    <th key={d} className="pb-1 text-center font-mono text-[10px] font-normal uppercase tracking-wider text-muted">
                      {shortDay(d)}
                    </th>
                  ))}
                  <th className="pb-1 text-right font-mono text-[10px] font-normal uppercase tracking-wider text-muted">Week</th>
                </tr>
              </thead>
              <tbody>
                {data.rooms.map(({ r, perDay, pct }) => (
                  <tr key={r.id}>
                    <td className="whitespace-nowrap pr-2">
                      <Link to="/timetable" search={{ view: 'room', id: r.id }} className="hover:text-oxblood">
                        {r.name}
                      </Link>
                    </td>
                    {db.settings.working_days.map((d) => {
                      const n = perDay[d] ?? 0
                      const a = n / periods().length
                      return (
                        <td
                          key={d}
                          title={`${r.name} · ${d}: ${n} periods`}
                          className="h-7 min-w-9 rounded-md text-center font-mono text-[10.5px] tabular"
                          style={{
                            background: n ? `color-mix(in oklab, ${r.room_type === 'laboratory' ? '#4f7a5a' : '#22346b'} ${12 + a * 70}%, #fffdf9)` : '#f3efe6',
                            color: a > 0.5 ? '#fffdf9' : '#485266',
                          }}
                        >
                          {n || ''}
                        </td>
                      )
                    })}
                    <td className="pl-2 text-right font-mono text-[11px] text-ink-soft tabular">{pct}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>

      <h2 className="mb-4 mt-10 font-serif text-2xl font-light">Programmes this semester</h2>
      <div className="stagger grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        {db.programmes.map((p) => {
          const refs = allSections.filter((s) => s.programme.id === p.id)
          const subjects = db.subjects.filter((s) => s.programme_id === p.id || refs.some((r) => r.section.id === s.section_id))
          const count = db.scheduledSessions.filter((s) => refs.some((r) => r.section.id === s.section_id)).length
          return (
            <Link
              key={p.id}
              to="/timetable"
              search={{ view: 'section', id: refs[0]?.section.id }}
              className="group flex flex-col rounded-2xl border border-rule bg-card p-5 shadow-card transition hover:-translate-y-0.5 hover:shadow-lift"
            >
              <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-oxblood">{p.code}</span>
              <span className="mt-2 font-serif text-[16px] leading-snug">{p.name}</span>
              <span className="mt-1 text-xs text-muted">
                {p.duration_years}-year · {refs.reduce((n, r) => n + r.section.student_strength, 0)} students
              </span>
              <div className="mt-auto flex items-end justify-between pt-5">
                <div className="flex -space-x-1">
                  {subjects.map((s) => (
                    <span key={s.id} title={s.name} className="h-3 w-3 rounded-full ring-2 ring-card" style={{ background: subjectColor(s.id) }} />
                  ))}
                </div>
                <span className="text-right">
                  <span className="block font-serif text-2xl font-light leading-none tabular">{count}</span>
                  <span className="text-[10px] text-muted">periods/wk</span>
                </span>
              </div>
            </Link>
          )
        })}
      </div>

      <p className="mt-10 text-center font-mono text-[10px] uppercase tracking-[0.2em] text-muted">
        Working hours {fmt12(db.settings.start_time)}–{fmt12(db.settings.end_time)} · {db.settings.breaks.map((b) => `${b.name} ${fmt12(b.start)}`).join(' · ')}
      </p>
    </>
  )
}
