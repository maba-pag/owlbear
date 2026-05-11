import { useEffect, useRef, useState } from 'react'
import { usePollingFetch } from './usePollingFetch'

const DEFAULT_INTERVAL_MS = 60_000

export interface PendingDR {
  id: string
  task_id: number
  agent: string
  request_type: string
  created: string
  title: string
  body: string
  body_preview: string
}

export interface UsePendingDRsOptions {
  intervalMs?: number
}

export interface UsePendingDRsResult {
  count: number
  items: PendingDR[]
  isLoading: boolean
  error: Error | null
  refetch: () => void
}

interface PendingDRResponse {
  count?: number
  items?: PendingDR[]
}

export function usePendingDRs(options?: UsePendingDRsOptions): UsePendingDRsResult {
  const intervalMs = options?.intervalMs ?? DEFAULT_INTERVAL_MS
  const [count, setCount] = useState<number>(0)
  const [items, setItems] = useState<PendingDR[]>([])
  const [error, setError] = useState<Error | null>(null)
  const isMountedRef = useRef(true)

  const { isFetching, hasFetched, refetch } = usePollingFetch<PendingDRResponse>('/api/decisions/pending', {
    intervalMs,
    onSuccess: async (payload) => {
      if (!isMountedRef.current) {
        return
      }
      const nextItems = Array.isArray(payload.items) ? payload.items : []
      setItems(nextItems)
      setCount(typeof payload.count === 'number' ? payload.count : nextItems.length)
      setError(null)
    },
    onError: async (caught) => {
      if (!isMountedRef.current) {
        return
      }
      setItems([])
      setCount(0)
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
    count,
    items,
    isLoading: !hasFetched || isFetching,
    error,
    refetch,
  }
}

