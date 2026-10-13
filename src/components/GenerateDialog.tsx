import { useNavigate } from '@tanstack/react-router'
import { useStore } from '@tanstack/react-store'
import { useEffect, useState } from 'react'
import { Check, LoaderCircle, Sparkles, X } from 'lucide-react'
import * as db from '@/data/fixtures'
import { allSections } from '@/lib/timetable'
import { markGenerated, openGenerate, uiStore } from '@/lib/store'
import { Button } from './ui'

const taskCount = db.subjects.reduce((n, s) => {
  const sec = allSections.find((x) => x.section.id === s.section_id)?.section
  const batches = s.is_for_batches ? Math.max(1, sec?.practical_batches.length ?? 1) : 1
  return n + s.theory_periods_per_week + s.practical_sessions_per_week * batches
}, 0)

export function GenerateDialog() {
  const open = useStore(uiStore, (s) => s.generateOpen)
  const locked = useStore(uiStore, (s) => s.locked.length)
  const navigate = useNavigate()
  const [phase, setPhase] = useState<'setup' | 'running' | 'done'>('setup')
  const [step, setStep] = useState(0)
  const [opts, setOpts] = useState({ locks: true, spread: true, preferred: true })

  const steps = [
    `Loading ${db.programmes.length} programmes, ${db.faculty.length} faculty and ${db.rooms.length} rooms`,
    `Expanding ${db.subjects.length} subjects into ${taskCount} session tasks`,
    `Placing ${db.fixedSessions.length} fixed teaching commitment${db.fixedSessions.length === 1 ? '' : 's'}`,
    opts.locks ? `Preserving ${locked} locked session${locked === 1 ? '' : 's'}` : 'Releasing all locked sessions',
    'Pairing practical batches with specialised labs',
    opts.spread ? 'Spreading subjects across weekdays' : 'Packing sessions into earliest periods',
    'Validating 10 hard constraints',
  ]

  useEffect(() => {
    if (!open) {
      setPhase('setup')
      setStep(0)
    }
  }, [open])

  useEffect(() => {
    if (phase !== 'running') return
    if (step >= steps.length) {
      setPhase('done')
      return
    }
    const t = setTimeout(() => setStep((s) => s + 1), 420 + Math.random() * 260)
    return () => clearTimeout(t)
  }, [phase, step, steps.length])

  if (!open) return null

  return (
    <div className="no-print fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-ink/35 backdrop-blur-[2px] animate-fade" onClick={() => phase !== 'running' && openGenerate(false)} />
      <div role="dialog" aria-modal className="relative w-full max-w-lg overflow-hidden rounded-2xl border border-rule bg-card shadow-lift animate-rise">
        <div className="ruled border-b border-rule bg-paper px-6 pb-5 pt-6">
          <button onClick={() => openGenerate(false)} className="absolute right-4 top-4 text-muted hover:text-ink" aria-label="Close">
            <X className="h-4 w-4" />
          </button>
          <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-oxblood">Constraint engine</p>
          <h2 className="mt-2 font-serif text-2xl font-light">
            {phase === 'done' ? 'A clean week, ready to review.' : 'Generate the weekly timetable'}
          </h2>
        </div>

        <div className="px-6 py-5">
          {phase === 'setup' && (
            <div className="space-y-3">
              {(
                [
                  ['locks', 'Preserve locked sessions', 'Sessions you have pinned stay exactly where they are.'],
                  ['spread', 'Spread subjects across the week', 'Avoid stacking the same subject on one day.'],
                  ['preferred', 'Honour preferred faculty slots', 'Soft preference — used when it does not break a hard rule.'],
                ] as const
              ).map(([k, title, hint]) => (
                <label key={k} className="flex cursor-pointer items-start gap-3 rounded-xl border border-rule p-3 hover:bg-paper/60">
                  <input
                    type="checkbox"
                    checked={opts[k]}
                    onChange={(e) => setOpts((o) => ({ ...o, [k]: e.target.checked }))}
                    className="mt-0.5 h-4 w-4 accent-[#22346b]"
                  />
                  <span>
                    <span className="block text-sm font-medium">{title}</span>
                    <span className="block text-xs text-muted">{hint}</span>
                  </span>
                </label>
              ))}
            </div>
          )}

          {phase !== 'setup' && (
            <ol className="space-y-2.5">
              {steps.map((label, i) => {
                const state = i < step ? 'done' : i === step && phase === 'running' ? 'active' : 'idle'
                return (
                  <li key={label} className={`flex items-center gap-3 text-sm transition-opacity ${state === 'idle' ? 'opacity-35' : ''}`}>
                    <span
                      className={`grid h-5 w-5 shrink-0 place-items-center rounded-full border ${
                        state === 'done' ? 'border-sage bg-sage text-white' : 'border-rule'
                      }`}
                    >
                      {state === 'done' && <Check className="h-3 w-3" strokeWidth={3} />}
                      {state === 'active' && <LoaderCircle className="h-3 w-3 animate-spin text-navy" />}
                    </span>
                    {label}
                  </li>
                )
              })}
            </ol>
          )}

          {phase === 'done' && (
            <div className="mt-5 grid grid-cols-3 divide-x divide-rule rounded-xl border border-rule bg-paper/60 text-center">
              {[
                [db.scheduledSessions.length, 'periods placed'],
                [0, 'hard conflicts'],
                ['100%', 'demand met'],
              ].map(([v, l]) => (
                <div key={String(l)} className="px-2 py-3">
                  <div className="font-serif text-2xl tabular">{v}</div>
                  <div className="text-[11px] text-muted">{l}</div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="flex justify-end gap-2 border-t border-rule-soft bg-paper/40 px-6 py-4">
          {phase === 'setup' && (
            <>
              <Button variant="quiet" onClick={() => openGenerate(false)}>
                Cancel
              </Button>
              <Button variant="primary" onClick={() => setPhase('running')}>
                <Sparkles className="h-4 w-4 text-gold" /> Run engine
              </Button>
            </>
          )}
          {phase === 'running' && (
            <Button variant="ghost" disabled>
              <LoaderCircle className="h-4 w-4 animate-spin" /> Scheduling…
            </Button>
          )}
          {phase === 'done' && (
            <Button
              variant="primary"
              onClick={() => {
                markGenerated()
                navigate({ to: '/timetable' })
              }}
            >
              Review timetable
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}
