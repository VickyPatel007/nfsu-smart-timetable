import { Link, createFileRoute } from '@tanstack/react-router'
import { useState } from 'react'
import { ArrowUpRight, Armchair, FlaskConical, Presentation } from 'lucide-react'
import * as db from '@/data/fixtures'
import { roomUtilisation, subjectById, toMin } from '@/lib/timetable'
import { useToday } from '@/lib/useToday'
import { MiniWeek } from '@/components/MiniWeek'
import { Meter, PageHeader, Segmented } from '@/components/ui'

export const Route = createFileRoute('/rooms')({
  head: () => ({ meta: [{ title: 'Rooms & Labs · NFSU Smart Timetable' }] }),
  component: RoomsPage,
})

type Filter = 'all' | 'classroom' | 'laboratory'

function RoomsPage() {
  const [filter, setFilter] = useState<Filter>('all')
  const { now } = useToday()
  const list = db.rooms.filter((r) => filter === 'all' || r.room_type === filter)
  const seats = db.rooms.reduce((n, r) => n + r.capacity, 0)

  const occupant = (roomId: string) => {
    if (!now) return undefined
    const day = now.toLocaleDateString('en-US', { weekday: 'long' })
    const m = now.getHours() * 60 + now.getMinutes()
    return db.scheduledSessions.find((s) => s.room_id === roomId && s.day === day && toMin(s.start_time) <= m && m < toMin(s.end_time))
  }

  return (
    <>
      <PageHeader
        eyebrow="Rooms & labs"
        title={
          <>
            {db.rooms.length} spaces, <span className="italic text-oxblood">{seats}</span> seats.
          </>
        }
        lede="Classrooms are matched to cohort size; practicals only land in a laboratory whose specialisation matches the subject."
        actions={
          <Segmented<Filter>
            value={filter}
            onChange={setFilter}
            options={[
              { value: 'all', label: 'All' },
              { value: 'classroom', label: 'Classrooms' },
              { value: 'laboratory', label: 'Labs' },
            ]}
          />
        }
      />

      <div className="stagger grid gap-5 md:grid-cols-2 xl:grid-cols-4">
        {list.map((r) => {
          const u = roomUtilisation(r)
          const lab = r.room_type === 'laboratory'
          const live = occupant(r.id)
          const sessions = db.scheduledSessions.filter((s) => s.room_id === r.id)
          return (
            <article key={r.id} className="flex flex-col overflow-hidden rounded-2xl border border-rule bg-card shadow-card">
              <div className={`relative px-5 pb-4 pt-5 ${lab ? 'bg-sage/[0.07]' : 'bg-navy/[0.04]'}`}>
                <div className="flex items-center justify-between">
                  <span className={`inline-flex items-center gap-1.5 text-[11px] font-medium ${lab ? 'text-sage' : 'text-navy'}`}>
                    {lab ? <FlaskConical className="h-3.5 w-3.5" /> : <Presentation className="h-3.5 w-3.5" />}
                    {lab ? r.lab_type : 'Classroom'}
                  </span>
                  {now && (
                    <span
                      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10.5px] font-medium ${
                        live ? 'bg-oxblood/10 text-oxblood' : 'bg-sage/10 text-sage'
                      }`}
                    >
                      <span className={`h-1.5 w-1.5 rounded-full ${live ? 'animate-pulse bg-oxblood' : 'bg-sage'}`} />
                      {live ? 'In use' : 'Free now'}
                    </span>
                  )}
                </div>
                <h2 className="mt-3 font-serif text-2xl leading-none">{r.name}</h2>
                <p className="mt-2 flex items-center gap-1.5 text-xs text-ink-soft">
                  <Armchair className="h-3.5 w-3.5" /> {r.capacity} seats
                  {live && <span className="truncate text-muted">· {subjectById.get(live.subject_id)?.code} until {live.end_time}</span>}
                </p>
              </div>
              <div className="px-5 py-4">
                <MiniWeek sessions={sessions} />
              </div>
              <div className="mt-auto border-t border-rule-soft px-5 py-3">
                <div className="mb-1.5 flex justify-between text-[12px]">
                  <span className="text-ink-soft">Utilisation</span>
                  <span className="font-mono tabular">
                    {u.used}/{u.total} · {u.pct}%
                  </span>
                </div>
                <Meter value={u.used} max={u.total} tone={lab ? '#4f7a5a' : '#22346b'} />
                <Link
                  to="/timetable"
                  search={{ view: 'room', id: r.id }}
                  className="mt-3 inline-flex items-center gap-1 text-[12px] font-medium text-oxblood hover:underline"
                >
                  Room week <ArrowUpRight className="h-3.5 w-3.5" />
                </Link>
              </div>
            </article>
          )
        })}
      </div>
    </>
  )
}
