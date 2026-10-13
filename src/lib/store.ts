import { Store } from '@tanstack/store'
import { timetableState } from '@/data/fixtures'

/** Client-only UI state for the demo. Persistence arrives with the data milestone in PLAN.md. */
export const uiStore = new Store({
  status: timetableState.status as 'draft' | 'generated' | 'published',
  lastGenerated: timetableState.last_generated,
  locked: [] as string[],
  generateOpen: false,
})

export const toggleLock = (id: string) =>
  uiStore.setState((s) => ({
    ...s,
    locked: s.locked.includes(id) ? s.locked.filter((x) => x !== id) : [...s.locked, id],
  }))

export const setStatus = (status: 'draft' | 'generated' | 'published') =>
  uiStore.setState((s) => ({ ...s, status }))

export const openGenerate = (open: boolean) => uiStore.setState((s) => ({ ...s, generateOpen: open }))

export const markGenerated = () =>
  uiStore.setState((s) => ({ ...s, status: 'generated', lastGenerated: new Date().toISOString(), generateOpen: false }))
