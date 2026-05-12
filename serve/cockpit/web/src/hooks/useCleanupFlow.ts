import { useState } from 'react'
import { cleanupTasks, type CleanupResult } from '../api/cleanup'

export type CleanupPhase = 'idle' | 'confirming' | 'running' | 'done' | 'error'

export interface UseCleanupFlowOptions {
  onSuccess?: () => void
}

export interface UseCleanupFlowResult {
  phase: CleanupPhase
  results: CleanupResult | null
  error: string | null
  requestCleanup: () => void
  confirmCleanup: () => Promise<void>
  cancelCleanup: () => void
  dismissResults: () => void
}

export function useCleanupFlow(options?: UseCleanupFlowOptions): UseCleanupFlowResult {
  const [phase, setPhase] = useState<CleanupPhase>('idle')
  const [results, setResults] = useState<CleanupResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  const requestCleanup = (): void => {
    setResults(null)
    setError(null)
    setPhase('confirming')
  }

  const cancelCleanup = (): void => {
    setResults(null)
    setError(null)
    setPhase('idle')
  }

  const dismissResults = (): void => {
    setResults(null)
    setError(null)
    setPhase('idle')
  }

  const confirmCleanup = async (): Promise<void> => {
    setError(null)
    setPhase('running')
    try {
      const response = await cleanupTasks()
      setResults(response)
      setPhase('done')
      options?.onSuccess?.()
    } catch (caught: unknown) {
      const message = caught instanceof Error ? caught.message : String(caught)
      setResults(null)
      setError(message)
      setPhase('error')
    }
  }

  return {
    phase,
    results,
    error,
    requestCleanup,
    confirmCleanup,
    cancelCleanup,
    dismissResults,
  }
}
