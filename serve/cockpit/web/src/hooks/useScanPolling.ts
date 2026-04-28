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
}

export function useScanPolling(options?: UseScanPollingOptions): UseScanPollingResult {
  const intervalMs = options?.intervalMs ?? DEFAULT_INTERVAL_MS
  const [items, setItems] = useState<ScanItem[]>([])
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const [error, setError] = useState<Error | null>(null)
  const inFlightRef = useRef(false)

  useEffect(() => {
    let cancelled = false
    let pendingPoll = false

    const poll = async (): Promise<void> => {
      if (inFlightRef.current) {
        pendingPoll = true
        return
      }

      inFlightRef.current = true
      pendingPoll = false
      setIsLoading(true)
      try {
        const response = await fetch('/api/tasks/scan', { method: 'POST' })
        if (!response.ok) {
          throw new Error(`Scan request failed with status ${response.status}`)
        }

        const payload = (await response.json()) as unknown
        if (!cancelled) {
          setItems(Array.isArray(payload) ? (payload as ScanItem[]) : [])
          setError(null)
        }
      } catch (caught) {
        if (!cancelled) {
          setItems([])
          setError(caught instanceof Error ? caught : new Error('Scan request failed'))
        }
      } finally {
        inFlightRef.current = false
        if (!cancelled) {
          setIsLoading(false)
        }
        if (pendingPoll && !cancelled) {
          pendingPoll = false
          void poll()
        }
      }
    }

    void poll()
    const intervalId = setInterval(() => {
      void poll()
    }, intervalMs)

    return () => {
      cancelled = true
      clearInterval(intervalId)
    }
  }, [intervalMs])

  return {
    items,
    isLoading,
    error,
  }
}
