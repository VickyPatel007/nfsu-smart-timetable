import { createFileRoute, Link, redirect, useNavigate } from '@tanstack/react-router'
import { BookOpen, Building2, LogOut, Users } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Button, Card, CardTitle, PageHeader } from '@/components/ui'
import { useIdentity } from '@/lib/identity-context'
import { getServerUser } from '@/lib/auth'
import { openGenerate, setStatus, uiStore } from '@/lib/store'
import { useStore } from '@tanstack/react-store'
import { getPublicationState, setPublicationState, type PublicationState } from '@/lib/admin-data'

export const Route = createFileRoute('/admin')({
  beforeLoad: async () => {
    const user = await getServerUser()
    if (!user) throw redirect({ to: '/login' })
    if (!user.roles?.includes('admin')) throw redirect({ to: '/student' })
    return { user }
  },
  head: () => ({ meta: [{ title: 'Admin · NFSU Smart Timetable' }] }),
  component: AdminPage,
})

function AdminPage() {
  const { user, logout } = useIdentity()
  const navigate = useNavigate()
  const status = useStore(uiStore, (state) => state.status)
  const [publication, setPublication] = useState<PublicationState | null>(null)

  useEffect(() => {
    void getPublicationState().then(setPublication)
  }, [])

  const updatePublication = async (nextStatus: PublicationState['status']) => {
    const next = await setPublicationState({ data: { status: nextStatus, updatedAt: new Date().toISOString() } })
    setPublication(next)
    setStatus(next.status)
  }

  const signOut = async () => {
    await logout()
    await navigate({ to: '/login' })
  }

  return (
    <>
      <PageHeader
        eyebrow="Timetable office"
        title="Admin control room"
        lede="Manage academic resources, generate schedules, and publish the student timetable."
        actions={
          <Button onClick={() => void signOut()}>
            <LogOut className="h-4 w-4" /> Sign out
          </Button>
        }
      />
      <div className="mb-6 rounded-xl border border-rule bg-card px-4 py-3 text-sm">
        Signed in as <strong>{user?.email}</strong>. Role: <span className="font-mono text-xs text-oxblood">admin</span>
      </div>
      <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
        <Card>
          <CardTitle title="Generation & publishing" />
          <p className="mt-3 text-sm text-muted">Current timetable status: <strong className="text-ink">{publication?.status ?? status}</strong></p>
          <div className="mt-4 flex flex-wrap gap-2">
            <Button variant="primary" onClick={() => openGenerate(true)}>Generate</Button>
            <Button onClick={() => void updatePublication(publication?.status === 'published' ? 'generated' : 'published')}>{publication?.status === 'published' ? 'Unpublish' : 'Publish'}</Button>
          </div>
        </Card>
        <ManagementCard href="/faculty" icon={<Users className="h-4 w-4" />} title="Faculty" text="Review teaching staff and weekly load." />
        <ManagementCard href="/rooms" icon={<Building2 className="h-4 w-4" />} title="Rooms & labs" text="Review capacity and occupancy." />
        <ManagementCard href="/timetable" icon={<BookOpen className="h-4 w-4" />} title="Timetable editor" text="Inspect sections, faculty, and room schedules." />
        <Card>
          <CardTitle title="Academic data" />
          <p className="mt-3 text-sm text-muted">Publication state is persisted server-side. Existing academic fixtures remain the safe initial dataset until CRUD storage is seeded.</p>
          <p className="mt-3 text-xs text-ochre">Connect Netlify Blobs in the site environment before publishing.</p>
        </Card>
        <Card>
          <CardTitle title="Health overview" />
          <p className="mt-3 text-sm text-muted">Use Overview for constraint health and utilisation metrics.</p>
          <Link to="/" className="mt-4 inline-block text-sm font-medium text-oxblood underline underline-offset-4">Open overview</Link>
        </Card>
      </div>
    </>
  )
}

function ManagementCard({ href, icon, title, text }: { href: '/faculty' | '/rooms' | '/timetable'; icon: React.ReactNode; title: string; text: string }) {
  return (
    <Card>
      <CardTitle title={title} action={icon} />
      <p className="mt-3 text-sm text-muted">{text}</p>
      <Link to={href} className="mt-4 inline-block text-sm font-medium text-oxblood underline underline-offset-4">Open workspace</Link>
    </Card>
  )
}
