import { useState, useRef, useCallback } from 'react'

export type HealthState = 'green' | 'yellow' | 'red'

function computeHealth(elapsed: number): HealthState {
  if (elapsed < 6000) return 'green'
  if (elapsed < 15000) return 'yellow'
  return 'red'
}

export function useConnectionHealth() {
  const [health, setHealth] = useState<HealthState>('green')
  const lastHealthyAt = useRef<number>(Date.now())

  const markHealthy = useCallback(() => {
    lastHealthyAt.current = Date.now()
  }, [])

  const updateHealth = useCallback(() => {
    const elapsed = Date.now() - lastHealthyAt.current
    setHealth(computeHealth(elapsed))
  }, [])

  return { health, markHealthy, updateHealth }
}
