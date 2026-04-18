import { useState, useRef, useEffect, useCallback } from 'react'

export type HealthState = 'green' | 'yellow' | 'red'

export interface UsePollingResult {
  health: HealthState
  skipNextPoll: () => void
  lastMtime: number | null
}

function computeHealth(elapsed: number): HealthState {
  if (elapsed < 6000) return 'green'
  if (elapsed < 15000) return 'yellow'
  return 'red'
}

export function usePolling(url: string): UsePollingResult {
  const [health, setHealth] = useState<HealthState>('green')
  const [lastMtime, setLastMtime] = useState<number | null>(null)
  const lastHealthyAt = useRef<number>(Date.now())
  const lastMtimeRef = useRef<number | null>(null)
  const skipRef = useRef<boolean>(false)

  const poll = useCallback(async () => {
    try {
      const res = await fetch(url, { method: 'GET' })
      if (res.ok) {
        lastHealthyAt.current = Date.now()
        const data = (await res.json()) as { mtime?: number }
        if (data.mtime !== undefined && data.mtime !== lastMtimeRef.current) {
          lastMtimeRef.current = data.mtime
          setLastMtime(data.mtime)
        }
      }
    } catch {
      // network error — health degrades by elapsed time
    }
    const elapsed = Date.now() - lastHealthyAt.current
    setHealth(computeHealth(elapsed))
  }, [url])

  useEffect(() => {
    void poll()
    const id = setInterval(() => {
      if (skipRef.current) {
        skipRef.current = false
        return
      }
      void poll()
    }, 3000)
    return () => clearInterval(id)
  }, [poll])

  return {
    health,
    skipNextPoll: () => {
      skipRef.current = true
    },
    lastMtime,
  }
}
