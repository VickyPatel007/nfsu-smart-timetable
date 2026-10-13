import * as db from '@/data/fixtures'
import type { ScheduledSession } from '@/data/types'
import { periods, subjectColor, subjectById } from '@/lib/timetable'

/** Compact days × periods occupancy map, coloured by subject. */
export function MiniWeek({ sessions, blocked = [] }: { sessions: ScheduledSession[]; blocked?: { day: string; start: string; end: string }[] }) {
  const ps = periods()
  return (
    <div className="grid gap-[3px]" style={{ gridTemplateColumns: `repeat(${db.settings.working_days.length}, minmax(0, 1fr))` }}>
      {db.settings.working_days.map((d) => (
        <div key={d} className="flex flex-col gap-[3px]">
          <span className="mb-0.5 text-center font-mono text-[9px] uppercase text-muted">{d[0]}</span>
          {ps.map((p) => {
            const s = sessions.find((x) => x.day === d && x.start_time === p.start)
            const off = blocked.some((b) => b.day === d && b.start <= p.start && p.start < b.end)
            return (
              <span
                key={p.start}
                title={s ? `${d} ${p.start} · ${subjectById.get(s.subject_id)?.name}` : off ? `${d} ${p.start} · unavailable` : `${d} ${p.start} · free`}
                className={`h-3 rounded-[3px] ${off && !s ? 'hatch bg-rule-soft' : ''}`}
                style={{ background: s ? subjectColor(s.subject_id) : off ? undefined : '#efeadf' }}
              />
            )
          })}
        </div>
      ))}
    </div>
  )
}
