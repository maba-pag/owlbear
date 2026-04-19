import { useState, useRef, useEffect, useCallback } from 'react'
import { useConnectionHealth, type HealthState } from './useConnectionHealth'

export type { HealthState }

export interface UsePollingResult {
  health: HealthState
  skipNextPoll: () => void
  lastMtime: number | null
}

export function usePolling(url: string): UsePollingResult {
  const [lastMtime, setLastMtime] = useState<number | null>(null)
  const lastMtimeRef = useRef<number | null>(null)
  const skipRef = useRef<boolean>(false)
  const { health, markHealthy, updateHealth } = useConnectionHealth()

  const poll = useCallback(async () => {
    try {
      const res = await fetch(url, { method: 'GET' })
      if (res.ok) {
        markHealthy()
        const data = (await res.json()) as { mtime?: number }
        if (data.mtime !== undefined && data.mtime !== lastMtimeRef.current) {
          lastMtimeRef.current = data.mtime
          setLastMtime(data.mtime)
        }
      }
    } catch {
      // network error — health degrades by elapsed time
    }
    updateHealth()
  }, [url, markHealthy, updateHealth])

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
