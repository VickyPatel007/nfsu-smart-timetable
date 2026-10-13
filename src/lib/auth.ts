import { createServerFn } from '@tanstack/react-start'
import { getUser } from '@netlify/identity'

export type IdentityUser = {
  id: string
  email: string
  name: string
  roles: string[]
}

export const getServerUser = createServerFn({ method: 'GET' }).handler(async () => {
  const user = await getUser()
  return user
    ? { id: user.id, email: user.email, name: user.name, roles: user.roles }
    : null
})
