import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react'
import { getUser, logout as netlifyLogout, onAuthChange, type User } from '@netlify/identity'

interface IdentityContextValue {
  user: User | null
  ready: boolean
  logout: () => Promise<void>
  localMode: boolean
}

const IdentityContext = createContext<IdentityContextValue | null>(null)
const LOCAL_USER_KEY = 'nfsu-local-user'
const LOCAL_USERS_KEY = 'nfsu-local-users'
type LocalUser = User & { password: string }

function readLocalUser() {
  if (typeof window === 'undefined') return null
  const raw = window.localStorage.getItem(LOCAL_USER_KEY)
  return raw ? (JSON.parse(raw) as User) : null
}

function ensureDemoUsers() {
  if (typeof window === 'undefined') return
  const currentUsers = window.localStorage.getItem(LOCAL_USERS_KEY)
  if (currentUsers) {
    const users = JSON.parse(currentUsers) as LocalUser[]
    const hasCurrentDefaults = users.some((user) => user.email === 'admin' || user.email === 'student')
    if (hasCurrentDefaults) return
    window.localStorage.removeItem(LOCAL_USER_KEY)
  }
  const users: LocalUser[] = [
    {
      id: 'local-admin',
      email: 'admin',
      name: 'Timetable Admin',
      password: 'admin',
      roles: ['admin'],
      userMetadata: {},
      appMetadata: {},
    },
    {
      id: 'local-student',
      email: 'student',
      name: 'Demo Student',
      password: 'student',
      roles: ['student'],
      userMetadata: {},
      appMetadata: {},
    },
  ]
  window.localStorage.setItem(LOCAL_USERS_KEY, JSON.stringify(users))
}

export function IdentityProvider({ children }: { children: ReactNode }) {
  const localMode = import.meta.env.DEV
  const [user, setUser] = useState<User | null>(null)
  const [ready, setReady] = useState(false)

  useEffect(() => {
    if (localMode) {
      ensureDemoUsers()
      setUser(readLocalUser())
      const syncLocalUser = () => setUser(readLocalUser())
      window.addEventListener('nfsu-auth-change', syncLocalUser)
      setReady(true)
      return () => window.removeEventListener('nfsu-auth-change', syncLocalUser)
    }
    let mounted = true
    void getUser().then((currentUser) => {
      if (mounted) {
        setUser(currentUser ?? null)
        setReady(true)
      }
    })

    const unsubscribe = onAuthChange((_event, nextUser) => {
      if (mounted) setUser(nextUser ?? null)
    })

    return () => {
      mounted = false
      unsubscribe()
    }
  }, [localMode])

  const logout = async () => {
    if (localMode) {
      window.localStorage.removeItem(LOCAL_USER_KEY)
      setUser(null)
      return
    }
    await netlifyLogout()
  }

  return <IdentityContext.Provider value={{ user, ready, logout, localMode }}>{children}</IdentityContext.Provider>
}

export function useIdentity() {
  const context = useContext(IdentityContext)
  if (!context) throw new Error('useIdentity must be used within IdentityProvider')
  return context
}

export function hasRole(user: User | null, role: string) {
  return Boolean(user?.roles?.includes(role))
}

export async function localLogin(email: string, password: string) {
  const users = JSON.parse(window.localStorage.getItem(LOCAL_USERS_KEY) ?? '[]') as LocalUser[]
  const user = users.find((candidate) => candidate.email === email && candidate.password === password)
  if (!user) throw new Error('Invalid local demo email or password')
  const { password: _password, ...safeUser } = user
  window.localStorage.setItem(LOCAL_USER_KEY, JSON.stringify(safeUser))
  window.dispatchEvent(new Event('nfsu-auth-change'))
  return safeUser
}

export async function localSignup(name: string, email: string, password: string) {
  const users = JSON.parse(window.localStorage.getItem(LOCAL_USERS_KEY) ?? '[]') as LocalUser[]
  if (users.some((candidate) => candidate.email === email)) throw new Error('An account with this email already exists')
  const user: LocalUser = {
    id: crypto.randomUUID(),
    email,
    name,
    password,
    roles: ['student'],
    userMetadata: {},
    appMetadata: {},
  }
  users.push(user)
  window.localStorage.setItem(LOCAL_USERS_KEY, JSON.stringify(users))
  const { password: _password, ...safeUser } = user
  window.localStorage.setItem(LOCAL_USER_KEY, JSON.stringify(safeUser))
  window.dispatchEvent(new Event('nfsu-auth-change'))
  return safeUser
}
