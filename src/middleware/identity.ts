import { createMiddleware } from '@tanstack/react-start'
import { getUser } from '@netlify/identity'

export const requireAuthMiddleware = createMiddleware().server(async ({ next }) => {
  const user = await getUser()
  if (!user) throw new Error('Authentication required')
  return next({ context: { user } })
})

export function requireRoleMiddleware(role: string) {
  return createMiddleware().server(async ({ next }) => {
    const user = await getUser()
    if (!user) throw new Error('Authentication required')
    if (!user.roles?.includes(role)) throw new Error(`Role '${role}' required`)
    return next({ context: { user } })
  })
}
