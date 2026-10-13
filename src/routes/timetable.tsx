import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useStore } from '@tanstack/react-store'
import { useMemo, useState } from 'react'
import { Building2, Download, GraduationCap, Printer, Send, Undo2, Users } from 'lucide-react'
import * as db from '@/data/fixtures'
import { setStatus, uiStore } from '@/lib/store'
import { type Block, type ViewKind, allSections, blocksFor, downloadText, sessionsToCsv, subjectColor } from '@/lib/timetable'
import { WeekGrid } from '@/components/WeekGrid'
import { SessionDrawer } from '@/components/SessionDrawer'
import { Button, PageHeader, Segmented, StatusPill } from '@/components/ui'

type Search = { view?: ViewKind; id?: string }

export const Route = createFileRoute('/timetable')({
  validateSearch: (s: Record<string, unknown>): Search => {
    const view = (['section', 'faculty', 'room'] as const).includes(s.view as ViewKind) ? (s.view as ViewKind) : undefined
    return { view, id: typeof s.id === 'string' && s.id ? s.id : undefined }
  },
  head: () => ({ meta: [{ title: 'Timetable · NFSU Smart Timetable' }] }),
  component: TimetablePage,
})

const entities = (view: ViewKind) =>
  view === 'section'
    ? allSections.map((s) => ({
        id: s.section.id,
        label: `${s.programme.code} · Sem ${s.semester.number} · Sec ${s.section.name}`,
        sub: s.programme.name,
      }))
    : view === 'faculty'
      ? db.faculty.map((f) => ({ id: f.id, label: f.name, sub: f.employee_id }))
      : db.rooms.map((r) => ({ id: r.id, label: r.name, sub: r.room_type === 'laboratory' ? r.lab_type : `Classroom · ${r.capacity} seats` }))

function TimetablePage() {
  const { view = 'section', id: rawId } = Route.useSearch()
  const navigate = useNavigate({ from: '/timetable' })
  const status = useStore(uiStore, (s) => s.status)
  const list = entities(view)
  const id = list.find((e) => e.id === rawId)?.id ?? list[0].id
  const current = list.find((e) => e.id === id)!
  const blocks = useMemo(() => blocksFor(view, id), [view, id])
  const [selected, setSelected] = useState<Block | null>(null)
  const [highlight, setHighlight] = useState<string>()

  const subjects = [...new Map(blocks.map((b) => [b.subject.id, b.subject])).values()]
  const hours = blocks.reduce((n, b) => n + b.sessionIds.length, 0)
  const labs = blocks.filter((b) => b.type === 'practical').length

  const go = (next: Partial<Search>) => navigate({ search: (prev: Search) => ({ ...prev, ...next }) })

  return (
    <>
      <PageHeader
        eyebrow="Weekly timetable"
        title={
          <>
            {current.label.split(' · ')[0]}
            <span className="text-muted">{current.label.includes(' · ') ? ` · ${current.label.split(' · ').slice(1).join(' · ')}` : ''}</span>
          </>
        }
        lede={current.sub}
        actions={
          <>
            <StatusPill status={status} />
            <Button onClick={() => window.print()}>
              <Printer className="h-4 w-4" /> Print
            </Button>
            <Button
              onClick={() =>
                downloadText(`timetable-${current.label.replace(/[^a-z0-9]+/gi, '-').toLowerCase()}.csv`, sessionsToCsv(blocks))
              }
            >
              <Download className="h-4 w-4" /> CSV
            </Button>
            {status === 'published' ? (
              <Button onClick={() => setStatus('generated')}>
                <Undo2 className="h-4 w-4" /> Unpublish
              </Button>
            ) : (
              <Button variant="primary" onClick={() => setStatus('published')}>
                <Send className="h-4 w-4" /> Publish
              </Button>
            )}
          </>
        }
      />

      <div className="print-only mb-4">
        <p className="font-serif text-xl">{db.settings.name}</p>
        <p className="text-sm">{db.settings.department} · Odd Semester 2026–27</p>
      </div>

      <div className="no-print mb-5 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <Segmented
          value={view}
          onChange={(v) => go({ view: v, id: undefined })}
          options={[
            { value: 'section', label: 'Sections', icon: <GraduationCap className="h-3.5 w-3.5" /> },
            { value: 'faculty', label: 'Faculty', icon: <Users className="h-3.5 w-3.5" /> },
            { value: 'room', label: 'Rooms & labs', icon: <Building2 className="h-3.5 w-3.5" /> },
          ]}
        />
        <select
          value={id}
          onChange={(e) => go({ id: e.target.value })}
          className="w-full rounded-lg border border-rule bg-card px-3 py-2 text-sm shadow-card focus:border-navy focus:outline-none lg:w-96"
          aria-label="Choose timetable"
        >
          {list.map((e) => (
            <option key={e.id} value={e.id}>
              {e.label}
            </option>
          ))}
        </select>
      </div>

      <div className="grid gap-5 xl:grid-cols-[1fr_260px]">
        <WeekGrid blocks={blocks} view={view} onSelect={setSelected} selectedId={selected?.id} highlight={highlight} />

        <aside className="no-print space-y-4">
          <div className="grid grid-cols-3 gap-px overflow-hidden rounded-2xl border border-rule bg-rule xl:grid-cols-1">
            {[
              [hours, 'teaching periods'],
              [subjects.length, 'subjects'],
              [labs, 'lab blocks'],
            ].map(([v, l]) => (
              <div key={l} className="bg-card px-4 py-3">
                <div className="font-serif text-3xl font-light tabular">{v}</div>
                <div className="text-xs text-muted">{l}</div>
              </div>
            ))}
          </div>

          <div className="rounded-2xl border border-rule bg-card p-4 shadow-card">
            <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted">Subjects · hover to focus</p>
            <ul className="mt-3 space-y-1" onMouseLeave={() => setHighlight(undefined)}>
              {subjects.map((s) => (
                <li key={s.id}>
                  <button
                    onMouseEnter={() => setHighlight(s.id)}
                    onFocus={() => setHighlight(s.id)}
                    onClick={() => setHighlight((h) => (h === s.id ? undefined : s.id))}
                    className="flex w-full items-center gap-2.5 rounded-lg px-2 py-1.5 text-left hover:bg-paper"
                  >
                    <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: subjectColor(s.id) }} />
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-[13px]">{s.name}</span>
                      <span className="font-mono text-[10px] text-muted">{s.code}</span>
                    </span>
                  </button>
                </li>
              ))}
              {subjects.length === 0 && <li className="text-sm text-muted">Nothing scheduled here yet.</li>}
            </ul>
          </div>

          <div className="rounded-2xl border border-rule p-4 text-xs leading-relaxed text-ink-soft">
            <p className="font-medium text-ink">Reading the grid</p>
            <p className="mt-1">Each colour is a subject. Lab blocks span consecutive periods; a pin marks a fixed commitment, a padlock a session you have locked.</p>
          </div>
        </aside>
      </div>

      <SessionDrawer block={selected} onClose={() => setSelected(null)} />
    </>
  )
}
