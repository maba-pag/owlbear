import { useEffect, useRef, useState } from 'react'
import { usePollingFetch } from './usePollingFetch'

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
  const [error, setError] = useState<Error | null>(null)
  const isMountedRef = useRef(true)

  const { isFetching, hasFetched, refetch } = usePollingFetch<unknown>('/api/tasks/scan', {
    intervalMs,
    method: 'POST',
    onSuccess: async (payload) => {
      if (!isMountedRef.current) {
        return
      }
      setItems(Array.isArray(payload) ? (payload as ScanItem[]) : [])
      setError(null)
    },
    onError: async (caught) => {
      if (!isMountedRef.current) {
        return
      }
      setItems([])
      setError(caught)
    },
  })

  useEffect(() => {
    isMountedRef.current = true
    return () => {
      isMountedRef.current = false
    }
  }, [])

  return {
    items,
    isLoading: !hasFetched || isFetching,
    error,
    refetch,
  }
}

