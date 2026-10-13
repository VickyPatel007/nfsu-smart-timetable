import { useStore } from '@tanstack/react-store'
import { FlaskConical, Lock, Pin } from 'lucide-react'
import { settings } from '@/data/fixtures'
import { uiStore } from '@/lib/store'
import { type Block, type ViewKind, daySlots, fmt12, shortDay, subjectColor, toMin } from '@/lib/timetable'
import { useToday } from '@/lib/useToday'

export function WeekGrid({
  blocks,
  view,
  onSelect,
  selectedId,
  highlight,
}: {
  blocks: Block[]
  view: ViewKind
  onSelect: (b: Block) => void
  selectedId?: string
  highlight?: string
}) {
  const slots = daySlots()
  const days = settings.working_days
  const { day: today } = useToday()
  const locked = useStore(uiStore, (s) => s.locked)

  const rowOf = (time: string) => slots.findIndex((s) => toMin(s.start) <= toMin(time) && toMin(time) < toMin(s.end)) + 2
  const rowEnd = (time: string) => slots.findIndex((s) => toMin(s.end) >= toMin(time)) + 3

  return (
    <div className="overflow-x-auto rounded-2xl border border-rule bg-card shadow-card print-flat">
      <div
        className="grid min-w-[880px]"
        style={{
          gridTemplateColumns: `76px repeat(${days.length}, minmax(0, 1fr))`,
          gridTemplateRows: `44px ${slots.map((s) => (s.kind === 'break' ? '34px' : 'minmax(92px, auto)')).join(' ')}`,
        }}
      >
        <div className="sticky left-0 z-10 border-b border-rule bg-card" style={{ gridRow: 1, gridColumn: 1 }} />
        {days.map((d, i) => (
          <div
            key={d}
            style={{ gridRow: 1, gridColumn: i + 2 }}
            className={`flex items-center justify-between border-b border-l border-rule px-3 text-[13px] ${
              d === today ? 'bg-oxblood/[0.04]' : ''
            }`}
          >
            <span className="font-medium">
              <span className="hidden xl:inline">{d}</span>
              <span className="xl:hidden">{shortDay(d)}</span>
            </span>
            {d === today && <span className="font-mono text-[9px] uppercase tracking-[0.18em] text-oxblood">Today</span>}
          </div>
        ))}

        {slots.map((s, r) => (
          <div
            key={s.start}
            style={{ gridRow: r + 2, gridColumn: 1 }}
            className="sticky left-0 z-10 flex flex-col border-b border-rule-soft bg-card px-3 pt-2 last:border-b-0"
          >
            {s.kind === 'period' ? (
              <>
                <span className="font-mono text-[11px] text-ink tabular">{s.start}</span>
                <span className="font-mono text-[10px] text-muted tabular">P{s.index + 1}</span>
              </>
            ) : (
              <span className="font-mono text-[10px] text-muted tabular">{s.start}</span>
            )}
          </div>
        ))}

        {slots.map((s, r) =>
          days.map((d, c) => (
            <div
              key={`${d}-${s.start}`}
              style={{ gridRow: r + 2, gridColumn: c + 2 }}
              className={`border-b border-l border-rule-soft ${s.kind === 'break' ? 'hatch' : ''} ${
                d === today && s.kind === 'period' ? 'bg-oxblood/[0.025]' : ''
              }`}
            >
              {s.kind === 'break' && c === 0 && (
                <span className="flex h-full items-center px-3 font-mono text-[10px] uppercase tracking-[0.2em] text-muted">
                  {s.name} · {fmt12(s.start)}–{fmt12(s.end)}
                </span>
              )}
            </div>
          )),
        )}

        {blocks.map((b) => {
          const col = days.indexOf(b.day) + 2
          if (col < 2) return null
          const color = subjectColor(b.subject.id)
          const isLocked = b.sessionIds.some((id) => locked.includes(id))
          const dim = highlight && highlight !== b.subject.id
          const meta =
            view === 'section'
              ? [b.faculty.name, b.room.name]
              : view === 'faculty'
                ? [`${b.ref.programme.code} · ${b.ref.section.name}`, b.room.name]
                : [`${b.ref.programme.code} · ${b.ref.section.name}`, b.faculty.name]
          return (
            <button
              key={b.id}
              onClick={() => onSelect(b)}
              style={{
                gridColumn: col,
                gridRow: `${rowOf(b.start)} / ${rowEnd(b.end)}`,
                background: `color-mix(in oklab, ${color} 9%, #fffdf9)`,
                borderColor: `color-mix(in oklab, ${color} 28%, transparent)`,
                ['--c' as string]: color,
              }}
              className={`group relative z-[1] m-1 flex flex-col overflow-hidden rounded-xl border p-2.5 pl-3.5 text-left transition duration-200 hover:-translate-y-px hover:shadow-lift focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-navy animate-rise ${
                selectedId === b.id ? 'ring-2 ring-[var(--c)] ring-offset-1 ring-offset-card' : ''
              } ${dim ? 'opacity-30 saturate-50' : ''}`}
            >
              <span className="absolute inset-y-2 left-1.5 w-[3px] rounded-full" style={{ background: color }} />
              <span className="flex items-center justify-between gap-1">
                <span className="font-mono text-[10.5px] font-medium tracking-wide" style={{ color }}>
                  {b.subject.code}
                </span>
                <span className="flex items-center gap-1 text-ink-soft">
                  {b.fixed && <Pin className="h-3 w-3 text-ochre" strokeWidth={2.2} />}
                  {isLocked && <Lock className="h-3 w-3" strokeWidth={2.2} />}
                </span>
              </span>
              <span className="mt-0.5 font-serif text-[14.5px] leading-[1.2] text-ink">{b.subject.name}</span>
              <span className="mt-auto pt-2 text-[11.5px] leading-snug text-ink-soft">
                {meta[0]}
                <span className="text-muted"> · </span>
                {meta[1]}
              </span>
              {b.type === 'practical' && (
                <span
                  className="mt-1.5 inline-flex w-fit items-center gap-1 rounded-md px-1.5 py-0.5 text-[10.5px] font-medium"
                  style={{ background: `color-mix(in oklab, ${color} 16%, transparent)`, color }}
                >
                  <FlaskConical className="h-3 w-3" /> Lab{b.batch ? ` · ${b.batch}` : ''} · {fmt12(b.start)}–{fmt12(b.end)}
                </span>
              )}
            </button>
          )
        })}
      </div>
    </div>
  )
}
