// RED-phase stub — minimal shell so tests compile.
// Builder replaces this with the real implementation.

export interface UseOptimisticResult<T> {
  state: T
  mutate: (updater: (s: T) => T) => void
  rollback: () => void
}

export function useOptimistic<T>(initial: T): UseOptimisticResult<T> {
  return {
    state: initial,
    mutate: (_updater: (s: T) => T) => {},
    rollback: () => {},
  }
}
