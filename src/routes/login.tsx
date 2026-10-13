import { login, requestPasswordRecovery, signup } from '@netlify/identity'
import { createFileRoute, Link, useNavigate } from '@tanstack/react-router'
import { useEffect, useState } from 'react'
import { Crest } from '@/components/AppShell'
import { useIdentity } from '@/lib/identity-context'
import { Button } from '@/components/ui'

export const Route = createFileRoute('/login')({
  head: () => ({ meta: [{ title: 'Sign in · NFSU Smart Timetable' }] }),
  component: LoginPage,
})

function LoginPage() {
  const { user, ready } = useIdentity()
  const navigate = useNavigate()
  const [mode, setMode] = useState<'login' | 'signup'>('login')
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [pending, setPending] = useState(false)

  useEffect(() => {
    if (ready && user) void navigate({ to: user.roles?.includes('admin') ? '/admin' : '/student' })
  }, [navigate, ready, user])

  if (ready && user) return null

  const submit = async () => {
    setPending(true)
    setError('')
    setMessage('')
    try {
      if (mode === 'signup') {
        await signup(email, password, { full_name: name })
        setMessage(`Confirmation email sent to ${email}. Confirm it before signing in.`)
      } else {
        await login(email, password)
        await navigate({ to: '/student' })
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Unable to authenticate')
    } finally {
      setPending(false)
    }
  }

  const recover = async () => {
    setError('')
    try {
      await requestPasswordRecovery(email)
      setMessage(`Password reset email sent to ${email}.`)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Unable to send reset email')
    }
  }

  return (
    <div className="mx-auto flex min-h-[70vh] max-w-md items-center justify-center">
      <div className="w-full rounded-2xl border border-rule bg-card p-6 shadow-card sm:p-8">
        <Link to="/" className="mb-8 flex items-center gap-3">
          <Crest className="h-10 w-10" />
          <span className="font-serif text-lg font-semibold">NFSU Smart Timetable</span>
        </Link>
        <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted">
          {mode === 'login' ? 'Secure access' : 'Create student account'}
        </p>
        <h1 className="mt-2 font-serif text-3xl">{mode === 'login' ? 'Sign in' : 'Join the timetable'}</h1>
        <p className="mt-2 text-sm text-muted">
          {mode === 'login' ? 'Use your university email to continue.' : 'Student accounts can view published schedules.'}
        </p>

        <div className="mt-6 space-y-3">
          {mode === 'signup' && (
            <input value={name} onChange={(event) => setName(event.target.value)} placeholder="Full name" className="w-full rounded-lg border border-rule bg-paper px-3 py-2.5 text-sm outline-none focus:border-navy" />
          )}
          <input value={email} onChange={(event) => setEmail(event.target.value)} type="email" placeholder="University email" className="w-full rounded-lg border border-rule bg-paper px-3 py-2.5 text-sm outline-none focus:border-navy" />
          <input value={password} onChange={(event) => setPassword(event.target.value)} type="password" placeholder="Password" className="w-full rounded-lg border border-rule bg-paper px-3 py-2.5 text-sm outline-none focus:border-navy" />
        </div>

        {error && <p className="mt-3 rounded-lg bg-oxblood/10 px-3 py-2 text-sm text-oxblood">{error}</p>}
        {message && <p className="mt-3 rounded-lg bg-sage/10 px-3 py-2 text-sm text-sage">{message}</p>}

        <Button variant="primary" onClick={() => void submit()} disabled={pending} className="mt-5 w-full justify-center">
          {pending ? 'Please wait…' : mode === 'login' ? 'Sign in' : 'Create account'}
        </Button>
        {mode === 'login' && (
          <button onClick={() => void recover()} className="mt-3 w-full text-center text-xs text-muted underline underline-offset-4">
            Forgot password?
          </button>
        )}
        <button
          onClick={() => {
            setMode(mode === 'login' ? 'signup' : 'login')
            setError('')
            setMessage('')
          }}
          className="mt-5 w-full text-center text-sm text-oxblood underline underline-offset-4"
        >
          {mode === 'login' ? 'Create a student account' : 'Already have an account? Sign in'}
        </button>
      </div>
    </div>
  )
}
