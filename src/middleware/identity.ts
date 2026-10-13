import { createMiddleware } from '@tanstack/react-start'
import { getUser } from '@netlify/identity'
import { getLocalUser } from '@/lib/local-auth'

const currentUser = () => process.env.LOCAL_AUTH === 'true' ? getLocalUser() : getUser()

export const requireAuthMiddleware = createMiddleware().server(async ({ next }) => {
  const user = await currentUser()
  if (!user) throw new Error('Authentication required')
  return next({ context: { user } })
})

export function requireRoleMiddleware(role: string) {
  return createMiddleware().server(async ({ next }) => {
    const user = await currentUser()
    if (!user) throw new Error('Authentication required')
    if (!user.roles?.includes(role)) throw new Error(`Role '${role}' required`)
    return next({ context: { user } })
  })
}
