import { useEffect, useRef, useState } from 'react'

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
  refetch: () => Promise<void>
}

interface PendingDRResponse {
  count?: number
  items?: PendingDR[]
}

export function usePendingDRs(options?: UsePendingDRsOptions): UsePendingDRsResult {
  const intervalMs = options?.intervalMs ?? DEFAULT_INTERVAL_MS
  const [count, setCount] = useState<number>(0)
  const [items, setItems] = useState<PendingDR[]>([])
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
      const response = await fetch('/api/decisions/pending', { method: 'GET' })
      if (!response.ok) {
        throw new Error(`Pending DR request failed with status ${response.status}`)
      }
      const payload = (await response.json()) as PendingDRResponse
      if (!isMountedRef.current) {
        return
      }
      const nextItems = Array.isArray(payload.items) ? payload.items : []
      setItems(nextItems)
      setCount(typeof payload.count === 'number' ? payload.count : nextItems.length)
      setError(null)
    } catch (caught) {
      if (!isMountedRef.current) {
        return
      }
      setItems([])
      setCount(0)
      setError(caught instanceof Error ? caught : new Error('Pending DR request failed'))
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

    void poll()
    const intervalId = setInterval(() => {
      void poll()
    }, intervalMs)

    return () => {
      isMountedRef.current = false
      clearInterval(intervalId)
    }
  }, [intervalMs])

  return {
    count,
    items,
    isLoading,
    error,
    refetch: poll,
  }
}
