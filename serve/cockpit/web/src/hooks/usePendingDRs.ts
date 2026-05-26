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
  summary: string
  kind: 'decision' | 'action'
  options: PendingDROption[]
  body: string
  body_preview: string
}

export interface PendingDROption {
  option_id: string
  label: string
  confidence: number
  recommended: boolean
  rationale: string
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

interface PendingRequestResponse {
  request_id: string
  task_id: number
  kind: 'decision' | 'action'
  title: string
  summary: string
  agent: string
  created_at: string
  options: PendingDROption[]
  body: string
}

type PendingDRResponse = PendingRequestResponse[]

function normalizePendingDRItem(item: PendingRequestResponse): PendingDR {
  return {
    id: item.request_id,
    task_id: item.task_id,
    agent: item.agent,
    request_type: item.kind,
    created: item.created_at,
    title: item.title,
    summary: item.summary,
    kind: item.kind,
    options: Array.isArray(item.options) ? item.options : [],
    body: item.body,
    body_preview: item.summary,
  }
}

export function usePendingDRs(options?: UsePendingDRsOptions): UsePendingDRsResult {
  const intervalMs = options?.intervalMs ?? DEFAULT_INTERVAL_MS
  const [count, setCount] = useState<number>(0)
  const [items, setItems] = useState<PendingDR[]>([])
  const [error, setError] = useState<Error | null>(null)
  const isMountedRef = useRef(true)

  const { isFetching, hasFetched, refetch } = usePollingFetch<PendingDRResponse>('/api/requests/pending', {
    intervalMs,
    onSuccess: async (payload) => {
      if (!isMountedRef.current) {
        return
      }
      const nextItems = payload.map(normalizePendingDRItem)
      setItems(nextItems)
      setCount(nextItems.length)
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
