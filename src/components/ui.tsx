import type { ReactNode } from 'react'

export function StatusPill({ status }: { status: string }) {
  const map: Record<string, { label: string; cls: string; dot: string }> = {
    published: { label: 'Published', cls: 'bg-sage/10 text-sage border-sage/25', dot: 'bg-sage' },
    generated: { label: 'Generated', cls: 'bg-navy/[0.07] text-navy border-navy/20', dot: 'bg-navy' },
    draft: { label: 'Draft', cls: 'bg-ochre/10 text-ochre border-ochre/25', dot: 'bg-ochre' },
  }
  const s = map[status] ?? map.draft
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[11px] font-medium ${s.cls}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${s.dot}`} />
      {s.label}
    </span>
  )
}

export function PageHeader({
  eyebrow,
  title,
  lede,
  actions,
}: {
  eyebrow: string
  title: ReactNode
  lede?: ReactNode
  actions?: ReactNode
}) {
  return (
    <header className="mb-8 flex flex-col gap-5 border-b border-rule pb-7 md:flex-row md:items-end md:justify-between animate-rise">
      <div className="max-w-2xl">
        <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-oxblood">{eyebrow}</p>
        <h1 className="mt-3 font-serif text-[clamp(2rem,4vw,3rem)] font-light leading-[1.04] tracking-tight text-ink">
          {title}
        </h1>
        {lede && <p className="mt-3 max-w-xl text-[15px] leading-relaxed text-ink-soft">{lede}</p>}
      </div>
      {actions && <div className="no-print flex flex-wrap items-center gap-2">{actions}</div>}
    </header>
  )
}

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <section className={`rounded-2xl border border-rule bg-card shadow-card ${className}`}>{children}</section>
}

export function CardTitle({ title, hint, action }: { title: string; hint?: string; action?: ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-rule-soft px-5 py-4">
      <div>
        <h2 className="font-serif text-lg leading-tight">{title}</h2>
        {hint && <p className="mt-0.5 text-xs text-muted">{hint}</p>}
      </div>
      {action}
    </div>
  )
}

export function Button({
  children,
  variant = 'ghost',
  className = '',
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'primary' | 'ghost' | 'quiet' }) {
  const v = {
    primary: 'bg-ink text-paper hover:bg-navy shadow-card',
    ghost: 'border border-rule bg-card text-ink hover:border-ink/25 shadow-card',
    quiet: 'text-ink-soft hover:bg-paper-deep hover:text-ink',
  }[variant]
  return (
    <button
      {...props}
      className={`inline-flex items-center gap-2 rounded-lg px-3.5 py-2 text-[13px] font-medium transition disabled:opacity-50 ${v} ${className}`}
    >
      {children}
    </button>
  )
}

export function Segmented<T extends string>({
  value,
  onChange,
  options,
}: {
  value: T
  onChange: (v: T) => void
  options: { value: T; label: string; icon?: ReactNode }[]
}) {
  return (
    <div className="inline-flex rounded-lg border border-rule bg-paper-deep/70 p-0.5" role="tablist">
      {options.map((o) => (
        <button
          key={o.value}
          role="tab"
          aria-selected={value === o.value}
          onClick={() => onChange(o.value)}
          className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-[13px] font-medium transition ${
            value === o.value ? 'bg-card text-ink shadow-card' : 'text-ink-soft hover:text-ink'
          }`}
        >
          {o.icon}
          {o.label}
        </button>
      ))}
    </div>
  )
}

export function Tag({ children, tone = 'neutral' }: { children: ReactNode; tone?: 'neutral' | 'sage' | 'ochre' | 'navy' | 'oxblood' }) {
  const t = {
    neutral: 'bg-paper-deep text-ink-soft border-rule',
    sage: 'bg-sage/10 text-sage border-sage/20',
    ochre: 'bg-ochre/10 text-ochre border-ochre/25',
    navy: 'bg-navy/[0.06] text-navy border-navy/15',
    oxblood: 'bg-oxblood/[0.07] text-oxblood border-oxblood/20',
  }[tone]
  return <span className={`inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5 text-[11px] font-medium ${t}`}>{children}</span>
}

/** Thin horizontal meter used for load and utilisation. */
export function Meter({ value, max, tone = '#22346b' }: { value: number; max: number; tone?: string }) {
  const pct = Math.min(100, (value / Math.max(1, max)) * 100)
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-rule-soft">
      <div className="h-full rounded-full transition-[width] duration-700" style={{ width: `${pct}%`, background: tone }} />
    </div>
  )
}
