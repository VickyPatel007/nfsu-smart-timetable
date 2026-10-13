import { createServerFn } from '@tanstack/react-start'
import { deleteCookie, getCookie, setCookie } from '@tanstack/start-server-core'

type LocalRole = 'admin' | 'student'

export type LocalUser = {
  id: string
  email: string
  name: string
  roles: LocalRole[]
}

type StoredUser = LocalUser & { passwordHash: string; salt: string }
type LoginInput = { email: string; password: string }
type SignupInput = { email: string; password: string; name: string }

type LocalAuthState = {
  users: Map<string, StoredUser>
  sessions: Map<string, LocalUser>
  seeded: boolean
}

const stateKey = Symbol.for('nfsu.smart-timetable.local-auth')
const globalState = globalThis as typeof globalThis & { [stateKey]?: LocalAuthState }
const state = (globalState[stateKey] ??= { users: new Map(), sessions: new Map(), seeded: false })
const users = state.users
const sessions = state.sessions
const COOKIE = 'nfsu_local_session'
const USERS_FILE = '/tmp/nfsu-smart-timetable-users.json'

async function hashPassword(password: string, salt: string) {
  const bytes = new TextEncoder().encode(`${salt}:${password}`)
  const digest = await crypto.subtle.digest('SHA-256', bytes)
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, '0')).join('')
}

async function seedUser(email: string, name: string, role: LocalRole) {
  const salt = crypto.randomUUID()
  users.set(email, {
    id: `local-${role}`,
    email,
    name,
    roles: [role],
    salt,
    passwordHash: await hashPassword(role, salt),
  })
}

async function ensureSeeded() {
  const { readFile, writeFile } = await import('node:fs/promises')
  try {
    const saved = JSON.parse(await readFile(USERS_FILE, 'utf8')) as StoredUser[]
    users.clear()
    for (const user of saved) users.set(user.email, user)
    state.seeded = true
    return
  } catch {
    // The local container has no user file on its first start.
  }
  if (state.seeded) return
  await Promise.all([
    seedUser('admin', 'Local administrator', 'admin'),
    seedUser('student', 'Local student', 'student'),
  ])
  await writeFile(USERS_FILE, JSON.stringify([...users.values()]), 'utf8')
  state.seeded = true
}

async function persistUsers() {
  const { writeFile } = await import('node:fs/promises')
  await writeFile(USERS_FILE, JSON.stringify([...users.values()]), 'utf8')
}

function publicUser(user: StoredUser): LocalUser {
  const { passwordHash: _passwordHash, salt: _salt, ...safeUser } = user
  return safeUser
}

function requireLocalAuth() {
  if (process.env.LOCAL_AUTH !== 'true') throw new Error('Local authentication is disabled')
}

export const getLocalUser = createServerFn({ method: 'GET' }).handler(async () => {
  requireLocalAuth()
  await ensureSeeded()
  const token = getCookie(COOKIE)
  return token ? sessions.get(token) ?? null : null
})

export const localLogin = createServerFn({ method: 'POST' })
  .validator((data: LoginInput) => data)
  .handler(async ({ data }) => {
  requireLocalAuth()
  await ensureSeeded()
  const { email, password } = data
  const { readFile } = await import('node:fs/promises')
  const savedUsers = JSON.parse(await readFile(USERS_FILE, 'utf8')) as StoredUser[]
  const user = savedUsers.find((candidate) => candidate.email === email.trim().toLowerCase())
  const passwordHash = await hashPassword(password, user?.salt ?? '')
  if (!user || passwordHash !== user.passwordHash) {
    throw new Error('Invalid email or password')
  }
  const token = crypto.randomUUID()
  sessions.set(token, publicUser(user))
  setCookie(COOKIE, token, { httpOnly: true, sameSite: 'lax', path: '/', secure: false, maxAge: 60 * 60 * 24 })
  return publicUser(user)
  })

export const localSignup = createServerFn({ method: 'POST' })
  .validator((data: SignupInput) => data)
  .handler(async ({ data }) => {
  requireLocalAuth()
  await ensureSeeded()
  const { email, password, name } = data
  const normalizedEmail = email.trim().toLowerCase()
  if (!normalizedEmail || password.length < 6 || !name.trim()) throw new Error('Enter a name, email, and a password of at least 6 characters')
  if (users.has(normalizedEmail)) throw new Error('An account with this email already exists')
  const salt = crypto.randomUUID()
  const user: StoredUser = {
    id: `local-${crypto.randomUUID()}`,
    email: normalizedEmail,
    name: name.trim(),
    roles: ['student'],
    salt,
    passwordHash: await hashPassword(password, salt),
  }
  users.set(normalizedEmail, user)
  await persistUsers()
  const token = crypto.randomUUID()
  sessions.set(token, publicUser(user))
  setCookie(COOKIE, token, { httpOnly: true, sameSite: 'lax', path: '/', secure: false, maxAge: 60 * 60 * 24 })
  return publicUser(user)
  })

export const localLogout = createServerFn({ method: 'POST' }).handler(async () => {
  requireLocalAuth()
  const token = getCookie(COOKIE)
  if (token) sessions.delete(token)
  deleteCookie(COOKIE, { path: '/' })
})
