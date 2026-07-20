import { useRef, useState } from 'react'
import { cleanupTasks, type CleanupResult } from '../api/cleanup'
import { previewMemoryPurge, purgeMemories, type MemoryPurgePreview, type MemoryPurgeReceipt } from '../api/memoryPurge'

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

export type MemoryPurgePhase = 'idle' | 'configuring' | 'previewing' | 'confirming' | 'running' | 'done' | 'error'

export interface UseMemoryPurgeFlowOptions {
  onSuccess?: () => void
}

export interface UseMemoryPurgeFlowResult {
  phase: MemoryPurgePhase
  threshold: string
  preview: MemoryPurgePreview | null
  receipt: MemoryPurgeReceipt | null
  error: string | null
  setThreshold: (value: string) => void
  requestPreview: () => Promise<void>
  confirmPurge: () => Promise<void>
  cancelPurge: () => void
}

function parseThreshold(value: string): number | null {
  if (!/^\d+$/.test(value.trim())) return null
  const threshold = Number(value)
  return Number.isSafeInteger(threshold) ? threshold : null
}

export function useMemoryPurgeFlow(options?: UseMemoryPurgeFlowOptions): UseMemoryPurgeFlowResult {
  const [phase, setPhase] = useState<MemoryPurgePhase>('idle')
  const [threshold, setThreshold] = useState('30')
  const [preview, setPreview] = useState<MemoryPurgePreview | null>(null)
  const [receipt, setReceipt] = useState<MemoryPurgeReceipt | null>(null)
  const [error, setError] = useState<string | null>(null)
  const acceptedThreshold = useRef<number | null>(null)
  const previewRequest = useRef(0)
  const purgeInFlight = useRef(false)

  const changeThreshold = (value: string): void => {
    ++previewRequest.current
    acceptedThreshold.current = null
    setThreshold(value)
    setPreview(null)
    setReceipt(null)
    setError(null)
    setPhase('configuring')
  }

  const requestPreview = async (): Promise<void> => {
    const parsed = parseThreshold(threshold)
    if (parsed === null) {
      setError('Threshold must be a nonnegative whole number')
      setPreview(null)
      setPhase('error')
      return
    }
    const requestId = ++previewRequest.current
    acceptedThreshold.current = parsed
    setError(null)
    setPreview(null)
    setPhase('previewing')
    try {
      const response = await previewMemoryPurge(parsed)
      if (requestId !== previewRequest.current || acceptedThreshold.current !== parsed) return
      setPreview(response)
      setPhase('confirming')
    } catch (caught: unknown) {
      if (requestId !== previewRequest.current) return
      setError(caught instanceof Error ? caught.message : String(caught))
      setPhase('error')
    }
  }

  const confirmPurge = async (): Promise<void> => {
    const parsed = acceptedThreshold.current
    if (parsed === null || preview === null || purgeInFlight.current) return
    purgeInFlight.current = true
    setError(null)
    setPhase('running')
    try {
      const response = await purgeMemories(parsed)
      setReceipt(response)
      setPhase('done')
      options?.onSuccess?.()
    } catch (caught: unknown) {
      setError(caught instanceof Error ? caught.message : String(caught))
      setPhase('error')
    } finally {
      purgeInFlight.current = false
    }
  }

  const cancelPurge = (): void => {
    ++previewRequest.current
    acceptedThreshold.current = null
    setPreview(null)
    setReceipt(null)
    setError(null)
    setPhase('idle')
  }

  return { phase, threshold, preview, receipt, error, setThreshold: changeThreshold, requestPreview, confirmPurge, cancelPurge }
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
