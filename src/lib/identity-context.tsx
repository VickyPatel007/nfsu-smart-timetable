import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { getUser, logout as netlifyLogout, onAuthChange, type User } from '@netlify/identity'
import { isLocalAuth } from './auth-mode'
import { getLocalUser, localLogout } from './local-auth'

interface IdentityContextValue {
  user: User | null
  ready: boolean
  logout: () => Promise<void>
}

const IdentityContext = createContext<IdentityContextValue | null>(null)

export function IdentityProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [ready, setReady] = useState(false)

  useEffect(() => {
    let mounted = true
    void (isLocalAuth ? getLocalUser() : getUser()).then((currentUser) => {
      if (mounted) {
        setUser(currentUser ?? null)
        setReady(true)
      }
    })

    const unsubscribe = isLocalAuth ? () => {} : onAuthChange((_event, nextUser) => {
      if (mounted) setUser(nextUser ?? null)
    })

    return () => {
      mounted = false
      unsubscribe()
    }
  }, [])

  const logout = async () => {
    if (isLocalAuth) {
      await localLogout()
      setUser(null)
    } else {
      await netlifyLogout()
    }
  }

  return <IdentityContext.Provider value={{ user, ready, logout }}>{children}</IdentityContext.Provider>
}

export function useIdentity() {
  const context = useContext(IdentityContext)
  if (!context) throw new Error('useIdentity must be used within IdentityProvider')
  return context
}

export function hasRole(user: User | null, role: string) {
  return Boolean(user?.roles?.includes(role))
}
