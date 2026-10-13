import { getStore } from '@netlify/blobs'
import { createServerFn } from '@tanstack/react-start'
import { requireRoleMiddleware } from '@/middleware/identity'

export type PublicationState = {
  status: 'draft' | 'generated' | 'published'
  updatedAt: string
}

const DEFAULT_STATE: PublicationState = {
  status: 'draft',
  updatedAt: new Date(0).toISOString(),
}

const timetableStore = () => getStore({ name: 'nfsu-timetable', consistency: 'strong' })

export const getPublicationState = createServerFn({ method: 'GET' })
  .middleware([requireRoleMiddleware('admin')])
  .handler(async () => {
    const state = (await timetableStore().get('publication', { type: 'json' })) as PublicationState | null
    return state ?? DEFAULT_STATE
  })

export const setPublicationState = createServerFn({ method: 'POST' })
  .validator((data: PublicationState) => data)
  .middleware([requireRoleMiddleware('admin')])
  .handler(async ({ data }) => {
    if (!['draft', 'generated', 'published'].includes(data.status)) {
      throw new Error('Invalid publication status')
    }
    const nextState = { ...data, updatedAt: new Date().toISOString() }
    await timetableStore().setJSON('publication', nextState)
    return nextState
  })
