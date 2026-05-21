import { useEffect, useRef, useState } from 'react'
import { usePollingFetch } from './usePollingFetch'

export const MEMORY_PENDING_COUNT_EVENT = 'owlbear:memory-pending-count-change'

interface MemoryPendingCountEventDetail {
  delta?: number
}

type MemoryState = 'pending' | 'curated' | 'approved' | 'deleted'

interface MemoryEntry {
  state: MemoryState
}

interface MemoriesResponse {
  entries?: MemoryEntry[]
}

interface UsePendingMemoryCountResult {
  count: number
  isLoading: boolean
  error: Error | null
  refetch: () => void
}

export function usePendingMemoryCount(): UsePendingMemoryCountResult {
  const [count, setCount] = useState(0)
  const [error, setError] = useState<Error | null>(null)
  const isMountedRef = useRef(true)

  const { isFetching, hasFetched, refetch } = usePollingFetch<MemoriesResponse>('/api/memories', {
    intervalMs: 60_000,
    onSuccess: async (payload) => {
      if (!isMountedRef.current) {
        return
      }

      const entries = Array.isArray(payload.entries) ? payload.entries : []
      setCount(entries.filter((entry) => entry.state === 'pending').length)
      setError(null)
    },
    onError: async (caught) => {
      if (!isMountedRef.current) {
        return
      }
      setCount(0)
      setError(caught)
    },
  })

  useEffect(() => {
    function handlePendingCountChange(event: Event) {
      const detail = (event as CustomEvent<MemoryPendingCountEventDetail>).detail
      const delta = typeof detail?.delta === 'number' ? detail.delta : 0
      if (delta !== 0) {
        setCount((current) => Math.max(0, current + delta))
      }
      refetch()
    }

    window.addEventListener(MEMORY_PENDING_COUNT_EVENT, handlePendingCountChange)
    return () => {
      window.removeEventListener(MEMORY_PENDING_COUNT_EVENT, handlePendingCountChange)
    }
  }, [refetch])

  return {
    count,
    isLoading: !hasFetched || isFetching,
    error,
    refetch,
  }
}
