import { createFileRoute, redirect, useNavigate, Link } from '@tanstack/react-router'
import { LogOut } from 'lucide-react'
import { Button, PageHeader } from '@/components/ui'
import { useIdentity } from '@/lib/identity-context'
import { getServerUser } from '@/lib/auth'
import { allSections } from '@/lib/timetable'

export const Route = createFileRoute('/student')({
  beforeLoad: async () => {
    const user = await getServerUser()
    if (!user && !import.meta.env.DEV) throw redirect({ to: '/login' })
    return { user }
  },
  head: () => ({ meta: [{ title: 'Student timetable · NFSU Smart Timetable' }] }),
  component: StudentPage,
})

function StudentPage() {
  const { user, logout } = useIdentity()
  const navigate = useNavigate()

  const signOut = async () => {
    await logout()
    await navigate({ to: '/login' })
  }

  return (
    <>
      <PageHeader
        eyebrow="Student portal"
        title="Your published timetable"
        lede="Select your section to view the latest timetable published by the timetable office."
        actions={<Button onClick={() => void signOut()}><LogOut className="h-4 w-4" /> Sign out</Button>}
      />
      <div className="mb-6 rounded-xl border border-rule bg-card px-4 py-3 text-sm">
        Welcome, <strong>{user?.name || user?.email}</strong>. This portal is read-only.
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {allSections.map(({ section, programme, semester }) => (
          <Link
            key={section.id}
            to="/timetable"
            search={{ view: 'section', id: section.id }}
            className="rounded-xl border border-rule bg-card p-5 shadow-card transition hover:-translate-y-0.5 hover:border-oxblood/40"
          >
            <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-muted">{programme.code}</p>
            <h2 className="mt-2 font-serif text-xl">Semester {semester.number} · Section {section.name}</h2>
            <p className="mt-2 text-sm text-muted">{programme.name}</p>
            <p className="mt-4 text-xs font-medium text-oxblood">Open published schedule →</p>
          </Link>
        ))}
      </div>
    </>
  )
}
