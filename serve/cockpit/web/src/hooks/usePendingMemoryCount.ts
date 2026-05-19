import { useRef, useState } from 'react'
import { usePollingFetch } from './usePollingFetch'

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

  return {
    count,
    isLoading: !hasFetched || isFetching,
    error,
    refetch,
  }
}
