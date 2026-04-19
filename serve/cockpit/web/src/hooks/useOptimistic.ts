import { useState, useRef } from 'react'

export interface UseOptimisticResult<T> {
  state: T
  mutate: (updater: (s: T) => T) => void
  rollback: () => void
}

export function useOptimistic<T>(initial: T): UseOptimisticResult<T> {
  const [state, setState] = useState<T>(initial)
  const snapshot = useRef<T>(initial)

  function mutate(updater: (s: T) => T): void {
    setState((prev) => {
      snapshot.current = prev
      return updater(prev)
    })
  }

  function rollback(): void {
    setState(snapshot.current)
  }

  return { state, mutate, rollback }
}
