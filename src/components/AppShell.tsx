import { Link, useRouterState } from '@tanstack/react-router'
import { useStore } from '@tanstack/react-store'
import { useState } from 'react'
import { Building2, CalendarDays, LayoutGrid, LogIn, Menu, ShieldCheck, Sparkles, Users, X } from 'lucide-react'
import { settings } from '@/data/fixtures'
import { openGenerate, uiStore } from '@/lib/store'
import { GenerateDialog } from './GenerateDialog'
import { StatusPill } from './ui'
import { useIdentity } from '@/lib/identity-context'

const NAV = [
  { to: '/', label: 'Overview', icon: LayoutGrid },
  { to: '/timetable', label: 'Timetable', icon: CalendarDays },
  { to: '/faculty', label: 'Faculty', icon: Users },
  { to: '/rooms', label: 'Rooms & Labs', icon: Building2 },
] as const

export function Crest({ className = '' }: { className?: string }) {
  return (
    <svg viewBox="0 0 40 40" className={className} aria-hidden>
      <rect width="40" height="40" rx="10" fill="#1a2233" />
      <circle cx="20" cy="20" r="11" fill="none" stroke="#b8893b" strokeWidth="1.8" />
      <circle cx="20" cy="20" r="14.5" fill="none" stroke="#b8893b" strokeOpacity=".35" strokeWidth=".8" strokeDasharray="1.2 2.2" />
      <path d="M20 13v7l5 3.5" fill="none" stroke="#fffdf9" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function Brand() {
  return (
    <Link to="/" className="flex items-center gap-3">
      <Crest className="h-10 w-10 shrink-0" />
      <div className="leading-tight">
        <div className="font-serif text-[17px] font-semibold tracking-tight">Smart Timetable</div>
        <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted">NFSU · SCSDF</div>
      </div>
    </Link>
  )
}

function NavLinks({ onNavigate }: { onNavigate?: () => void }) {
  const path = useRouterState({ select: (s) => s.location.pathname })
  const { user } = useIdentity()
  return (
    <nav className="flex flex-col gap-0.5">
      {NAV.map(({ to, label, icon: Icon }) => {
        const active = to === '/' ? path === '/' : path.startsWith(to)
        return (
          <Link
            key={to}
            to={to}
            onClick={onNavigate}
            className={`group relative flex items-center gap-3 rounded-lg px-3 py-2 text-[14px] transition-colors ${
              active ? 'bg-card text-ink shadow-card' : 'text-ink-soft hover:bg-card/60 hover:text-ink'
            }`}
          >
            {active && <span className="absolute -left-4 top-2 bottom-2 w-[3px] rounded-r bg-oxblood" />}
            <Icon className={`h-4 w-4 ${active ? 'text-oxblood' : 'text-muted group-hover:text-ink-soft'}`} strokeWidth={1.8} />
            {label}
          </Link>
        )
      })}
      {user?.roles?.includes('admin') ? (
        <Link to="/admin" onClick={onNavigate} className="group relative flex items-center gap-3 rounded-lg px-3 py-2 text-[14px] text-ink-soft hover:bg-card/60 hover:text-ink">
          <ShieldCheck className="h-4 w-4 text-muted group-hover:text-ink-soft" strokeWidth={1.8} />
          Admin panel
        </Link>
      ) : (
        <Link to="/student" onClick={onNavigate} className="group relative flex items-center gap-3 rounded-lg px-3 py-2 text-[14px] text-ink-soft hover:bg-card/60 hover:text-ink">
          <GraduationCapIcon />
          Student panel
        </Link>
      )}
    </nav>
  )
}

function GraduationCapIcon() {
  return <Users className="h-4 w-4 text-muted group-hover:text-ink-soft" strokeWidth={1.8} />
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const [menu, setMenu] = useState(false)
  const status = useStore(uiStore, (s) => s.status)
  const { user, ready } = useIdentity()

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[248px_1fr]">
      <aside className="no-print sticky top-0 hidden h-screen flex-col border-r border-rule bg-paper-deep/60 px-4 py-6 lg:flex">
        <div className="px-1">
          <Brand />
        </div>
        <div className="mt-8 px-3 font-mono text-[10px] uppercase tracking-[0.2em] text-muted">Workspace</div>
        <div className="mt-2">
          <NavLinks />
        </div>

        <button
          onClick={() => openGenerate(true)}
          className="mt-8 flex items-center justify-center gap-2 rounded-lg bg-ink px-3 py-2.5 text-sm font-medium text-paper shadow-lift transition hover:bg-navy"
        >
          <Sparkles className="h-4 w-4 text-gold" strokeWidth={1.8} />
          Generate timetable
        </button>
        <div className="mt-4 flex items-center gap-2 px-3 text-xs text-muted">
          {ready && user ? (
            <>
              <ShieldCheck className="h-3.5 w-3.5 text-sage" />
              <Link to={user.roles?.includes('admin') ? '/admin' : '/student'} className="truncate hover:text-ink">{user.name || user.email}</Link>
            </>
          ) : (
            <Link to="/login" className="flex items-center gap-2 text-oxblood"><LogIn className="h-3.5 w-3.5" /> Sign in</Link>
          )}
        </div>

        <div className="mt-auto rounded-xl border border-rule bg-card p-4">
          <div className="flex items-center justify-between">
            <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted">Odd Sem · 2026–27</span>
            <StatusPill status={status} />
          </div>
          <p className="mt-2 font-serif text-[15px] leading-snug">{settings.department}</p>
          <p className="mt-1 text-xs text-muted">{settings.name}</p>
        </div>
      </aside>

      <header className="no-print sticky top-0 z-30 flex items-center justify-between border-b border-rule bg-paper/90 px-4 py-3 backdrop-blur lg:hidden">
        <Brand />
        <button onClick={() => setMenu(true)} className="rounded-lg border border-rule bg-card p-2" aria-label="Open menu">
          <Menu className="h-5 w-5" />
        </button>
      </header>

      {menu && (
        <div className="no-print fixed inset-0 z-50 lg:hidden">
          <div className="absolute inset-0 bg-ink/30 animate-fade" onClick={() => setMenu(false)} />
          <div className="absolute inset-y-0 left-0 w-72 bg-paper p-5 shadow-lift animate-slide-in">
            <div className="flex items-center justify-between">
              <Brand />
              <button onClick={() => setMenu(false)} aria-label="Close menu">
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="mt-8 pl-4">
              <NavLinks onNavigate={() => setMenu(false)} />
            </div>
            <button
              onClick={() => {
                setMenu(false)
                openGenerate(true)
              }}
              className="mt-6 flex w-full items-center justify-center gap-2 rounded-lg bg-ink px-3 py-2.5 text-sm font-medium text-paper"
            >
              <Sparkles className="h-4 w-4 text-gold" /> Generate timetable
            </button>
          </div>
        </div>
      )}

      <main className="print-full min-w-0 px-4 py-6 sm:px-8 lg:px-10 lg:py-8">
        <div className="mx-auto max-w-[1320px]">{children}</div>
      </main>

      <GenerateDialog />
    </div>
  )
}
