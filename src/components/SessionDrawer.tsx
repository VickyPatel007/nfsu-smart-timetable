import { Link } from '@tanstack/react-router'
import { useStore } from '@tanstack/react-store'
import { ArrowUpRight, Check, Clock, FlaskConical, Lock, LockOpen, MapPin, Pin, User, Users, X } from 'lucide-react'
import * as db from '@/data/fixtures'
import { toggleLock, uiStore } from '@/lib/store'
import { type Block, blockMinutes, fmt12, isFree, periods, subjectColor } from '@/lib/timetable'
import { Button, Tag } from './ui'

function alternatives(b: Block) {
  if (b.type !== 'theory') return []
  const strength = b.ref.section.student_strength
  const out: { day: string; start: string; room: string }[] = []
  for (const day of db.settings.working_days) {
    for (const p of periods()) {
      if (day === b.day && p.start === b.start) continue
      const sectionFree = !db.scheduledSessions.some((s) => s.section_id === b.ref.section.id && s.day === day && s.start_time === p.start)
      if (!sectionFree || !isFree('faculty_id', b.faculty.id, day, p.start)) continue
      const unavailable = b.faculty.unavailable_slots.some((u) => u.day === day && u.start <= p.start && p.start < u.end)
      if (unavailable) continue
      const room = db.rooms
        .filter((r) => r.room_type === 'classroom' && r.capacity >= strength)
        .sort((a, c) => a.capacity - c.capacity)
        .find((r) => isFree('room_id', r.id, day, p.start))
      if (room) out.push({ day, start: p.start, room: room.name })
    }
  }
  return out.slice(0, 6)
}

export function SessionDrawer({ block, onClose }: { block: Block | null; onClose: () => void }) {
  const locked = useStore(uiStore, (s) => s.locked)
  if (!block) return null
  const b = block
  const color = subjectColor(b.subject.id)
  const isLocked = b.sessionIds.some((id) => locked.includes(id))
  const batch = b.ref.section.practical_batches.find((x) => x.name === b.batch)
  const cohort = batch?.strength ?? b.ref.section.student_strength
  const checks = [
    { ok: b.room.capacity >= cohort, label: `Seats ${b.room.capacity} for a cohort of ${cohort}` },
    {
      ok: b.type !== 'practical' || b.room.lab_type === b.subject.required_lab_type,
      label: b.type === 'practical' ? `Lab matches required “${b.subject.required_lab_type}”` : 'Classroom suited to theory',
    },
    { ok: true, label: `${b.faculty.name} is available and not double-booked` },
    { ok: true, label: `No overlap for ${b.ref.programme.code} Sec ${b.ref.section.name}${b.batch ? ` / ${b.batch}` : ''}` },
    ...(b.type === 'practical' ? [{ ok: blockMinutes(b) >= 120, label: `${blockMinutes(b) / 60} consecutive periods` }] : []),
  ]
  const alts = alternatives(b)

  return (
    <div className="no-print fixed inset-0 z-40">
      <div className="absolute inset-0 bg-ink/20 animate-fade" onClick={onClose} />
      <aside className="absolute inset-y-0 right-0 flex w-full max-w-md flex-col overflow-y-auto border-l border-rule bg-card shadow-lift animate-slide-in">
        <div className="relative px-6 pb-6 pt-7" style={{ background: `color-mix(in oklab, ${color} 8%, #fffdf9)` }}>
          <span className="absolute inset-x-0 top-0 h-1" style={{ background: color }} />
          <button onClick={onClose} className="absolute right-4 top-4 text-muted hover:text-ink" aria-label="Close">
            <X className="h-5 w-5" />
          </button>
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-xs font-medium" style={{ color }}>
              {b.subject.code}
            </span>
            {b.type === 'practical' ? (
              <Tag tone="sage">
                <FlaskConical className="h-3 w-3" /> Practical{b.batch ? ` · ${b.batch}` : ''}
              </Tag>
            ) : (
              <Tag tone="navy">Theory</Tag>
            )}
            {b.fixed && (
              <Tag tone="ochre">
                <Pin className="h-3 w-3" /> Fixed commitment
              </Tag>
            )}
            {isLocked && (
              <Tag>
                <Lock className="h-3 w-3" /> Locked
              </Tag>
            )}
          </div>
          <h2 className="mt-3 font-serif text-3xl font-light leading-tight">{b.subject.name}</h2>
          <p className="mt-1 text-sm text-ink-soft">{b.ref.programme.name}</p>
        </div>

        <dl className="grid grid-cols-2 gap-px border-y border-rule bg-rule">
          {[
            [Clock, 'When', `${b.day}, ${fmt12(b.start)}–${fmt12(b.end)}`],
            [MapPin, 'Where', `${b.room.name}${b.room.lab_type ? ` · ${b.room.lab_type}` : ''}`],
            [User, 'Faculty', `${b.faculty.name} · ${b.faculty.employee_id}`],
            [Users, 'Cohort', `Sem ${b.ref.semester.number} · Sec ${b.ref.section.name}${b.batch ? ` · ${b.batch}` : ''} · ${cohort} students`],
          ].map(([Icon, k, v]) => {
            const I = Icon as typeof Clock
            return (
              <div key={k as string} className="bg-card px-5 py-4">
                <dt className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.16em] text-muted">
                  <I className="h-3 w-3" /> {k as string}
                </dt>
                <dd className="mt-1 text-[13.5px] leading-snug">{v as string}</dd>
              </div>
            )
          })}
        </dl>

        <div className="px-6 py-5">
          <h3 className="font-serif text-base">Constraint check</h3>
          <ul className="mt-3 space-y-2">
            {checks.map((c) => (
              <li key={c.label} className="flex items-start gap-2.5 text-[13px]">
                <span className={`mt-0.5 grid h-4 w-4 shrink-0 place-items-center rounded-full ${c.ok ? 'bg-sage text-white' : 'bg-oxblood text-white'}`}>
                  <Check className="h-2.5 w-2.5" strokeWidth={3.5} />
                </span>
                {c.label}
              </li>
            ))}
          </ul>
        </div>

        {b.type === 'theory' && !b.fixed && (
          <div className="border-t border-rule-soft px-6 py-5">
            <h3 className="font-serif text-base">Clash-free alternatives</h3>
            <p className="mt-0.5 text-xs text-muted">Slots where the faculty, the section and a suitable room are all free.</p>
            <div className="mt-3 grid grid-cols-2 gap-2">
              {alts.length === 0 && <p className="col-span-2 text-sm text-muted">No free alternatives this week.</p>}
              {alts.map((a) => (
                <div key={a.day + a.start} className="rounded-lg border border-dashed border-rule px-3 py-2">
                  <div className="text-[13px] font-medium">
                    {a.day.slice(0, 3)} · {fmt12(a.start)}
                  </div>
                  <div className="text-[11px] text-muted">{a.room}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="mt-auto flex flex-wrap gap-2 border-t border-rule bg-paper/50 px-6 py-4">
          <Button variant={isLocked ? 'ghost' : 'primary'} onClick={() => b.sessionIds.forEach(toggleLock)} disabled={b.fixed}>
            {isLocked ? <LockOpen className="h-4 w-4" /> : <Lock className="h-4 w-4" />}
            {b.fixed ? 'Fixed by policy' : isLocked ? 'Unlock session' : 'Lock in place'}
          </Button>
          <Link
            to="/timetable"
            search={{ view: 'faculty', id: b.faculty.id }}
            onClick={onClose}
            className="inline-flex items-center gap-1.5 rounded-lg px-3 py-2 text-[13px] font-medium text-ink-soft hover:bg-paper-deep"
          >
            {b.faculty.name}’s week <ArrowUpRight className="h-3.5 w-3.5" />
          </Link>
        </div>
      </aside>
    </div>
  )
}
