import { useEffect, useRef, useState } from 'react'

const DEFAULT_INTERVAL_MS = 60_000

export interface ScanItem {
  code: string | null
  detail: string | null
  file_path: string | null
}

export interface UseScanPollingOptions {
  intervalMs?: number
}

export interface UseScanPollingResult {
  items: ScanItem[]
  isLoading: boolean
  error: Error | null
  refetch: () => void
}

export function useScanPolling(options?: UseScanPollingOptions): UseScanPollingResult {
  const intervalMs = options?.intervalMs ?? DEFAULT_INTERVAL_MS
  const [items, setItems] = useState<ScanItem[]>([])
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const [error, setError] = useState<Error | null>(null)
  const isMountedRef = useRef(true)
  const inFlightRef = useRef(false)
  const pendingPollRef = useRef(false)

  const poll = async (): Promise<void> => {
    if (inFlightRef.current) {
      pendingPollRef.current = true
      return
    }

    inFlightRef.current = true
    pendingPollRef.current = false
    setIsLoading(true)
    try {
      const response = await fetch('/api/tasks/scan', { method: 'POST' })
      if (!response.ok) {
        throw new Error(`Scan request failed with status ${response.status}`)
      }

      const payload = (await response.json()) as unknown
      if (isMountedRef.current) {
        setItems(Array.isArray(payload) ? (payload as ScanItem[]) : [])
        setError(null)
      }
    } catch (caught) {
      if (isMountedRef.current) {
        setItems([])
        setError(caught instanceof Error ? caught : new Error('Scan request failed'))
      }
    } finally {
      inFlightRef.current = false
      if (isMountedRef.current) {
        setIsLoading(false)
      }
      if (pendingPollRef.current && isMountedRef.current) {
        pendingPollRef.current = false
        void poll()
      }
    }
  }

  useEffect(() => {
    isMountedRef.current = true
    return () => {
      isMountedRef.current = false
    }
  }, [])

  useEffect(() => {
    void poll()
    const intervalId = setInterval(() => {
      void poll()
    }, intervalMs)

    return () => {
      clearInterval(intervalId)
    }
  }, [intervalMs])

  return {
    items,
    isLoading,
    error,
    refetch: () => {
      void poll()
    },
  }
}
