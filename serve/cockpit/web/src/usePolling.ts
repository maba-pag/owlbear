// RED-phase stub — minimal shell so tests compile.
// Builder replaces this with the real implementation.

export type HealthState = 'green' | 'yellow' | 'red'

export interface UsePollingResult {
  health: HealthState
  skipNextPoll: () => void
}

export function usePolling(_url: string): UsePollingResult {
  return { health: 'green', skipNextPoll: () => {} }
}
