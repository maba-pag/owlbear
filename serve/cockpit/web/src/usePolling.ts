import { useState, useRef, useEffect, useCallback } from 'react'

export type HealthState = 'green' | 'yellow' | 'red'

export interface UsePollingResult {
  health: HealthState
  skipNextPoll: () => void
}

function computeHealth(elapsed: number): HealthState {
  if (elapsed < 6000) return 'green'
  if (elapsed < 15000) return 'yellow'
  return 'red'
}

export function usePolling(url: string): UsePollingResult {
  const [health, setHealth] = useState<HealthState>('green')
  const lastHealthyAt = useRef<number>(Date.now())
  const skipRef = useRef<boolean>(false)

  const poll = useCallback(async () => {
    try {
      const res = await fetch(url, { method: 'GET' })
      if (res.ok) {
        lastHealthyAt.current = Date.now()
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
  }
}
