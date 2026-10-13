import { useEffect, useState } from 'react'
import { todayName } from './timetable'

/** Current date resolved on the client only, so server and client markup agree on first render. */
export function useToday() {
  const [now, setNow] = useState<Date | null>(null)
  useEffect(() => setNow(new Date()), [])
  return { now, day: now ? todayName(now) : undefined }
}
