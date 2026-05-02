import { useState, useEffect, useRef } from 'react'
import { useConnectionHealth, type HealthState } from './useConnectionHealth'
import { usePollingFetch } from './usePollingFetch'
import { useSSEEvent } from './EventSourceProvider'

// ─── Types ────────────────────────────────────────────────────────────────────

export interface BoardStatus {
  name: string
}

export interface Board {
  statuses: BoardStatus[]
  priorities: string[]
  valid_transitions: Record<string, string[]>
}

export interface Task {
  id: number
  title: string
  status: string
  priority: string
  updated: string
  tags: string[]
  blocked: boolean
  block_reason: string | null
  claimed: boolean
}

interface TasksResponse {
  tasks: Task[]
  mtime: number
}

interface UseBoardResult {
  board: Board | null
  tasks: Task[]
  loading: boolean
  error: string | null
  isFetching: boolean
  isStale: boolean
  health: HealthState
  refetchTasks: () => void
  lastDecisionsMtime: number | null
}

// ─── Hook ─────────────────────────────────────────────────────────────────────

export function useBoard(): UseBoardResult {
  const [board, setBoard] = useState<Board | null>(null)
  const [tasks, setTasks] = useState<Task[]>([])
  const [boardReady, setBoardReady] = useState(false)
  const [tasksReady, setTasksReady] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isStale, setIsStale] = useState(false)
  const mtimeRef = useRef<number | null>(null)
  const lastObservedTasksMtimeRef = useRef<number | null>(null)
  const { status: sseStatus, mtime: lastTasksMtime } = useSSEEvent('tasks-changed')
  const { mtime: lastDecisionsMtime } = useSSEEvent('decisions-changed')
  const { health, markHealthy, updateHealth } = useConnectionHealth()

  const { isFetching, refetch: refetchTasks } = usePollingFetch<TasksResponse>('/api/tasks', {
    intervalMs: 3000,
    paused: sseStatus === 'open',
    onSuccess: async (data) => {
      if (data.mtime !== mtimeRef.current) {
        mtimeRef.current = data.mtime
        setTasks(data.tasks)
      }
      setError(null)
      setIsStale(false)
      setTasksReady(true)
      markHealthy()
      updateHealth()
    },
    onError: async (pollError) => {
      setError(pollError.message)
      setIsStale(true)
      setTasksReady(true)
      updateHealth()
    },
  })

  const refetchTasksRef = useRef(refetchTasks)
  useEffect(() => {
    refetchTasksRef.current = refetchTasks
  }, [refetchTasks])

  useEffect(() => {
    if (
      sseStatus === 'open' &&
      lastTasksMtime !== null &&
      lastObservedTasksMtimeRef.current !== lastTasksMtime
    ) {
      refetchTasksRef.current()
    }

    lastObservedTasksMtimeRef.current = lastTasksMtime
  }, [lastTasksMtime, sseStatus])

  useEffect(() => {
    const controller = new AbortController()
    let cancelled = false

    void (async () => {
      try {
        const boardRes = await fetch('/api/board', { signal: controller.signal })

        if (!boardRes.ok) {
          throw new Error(`Board API error: ${boardRes.status}`)
        }

        const boardData = (await boardRes.json()) as Board
        if (!cancelled) {
          setBoard(boardData)
        }
      } catch (err) {
        if (!cancelled && !(err instanceof DOMException && err.name === 'AbortError')) {
          setError(err instanceof Error ? err.message : 'Failed to load board')
        }
      } finally {
        if (!cancelled) {
          setBoardReady(true)
        }
      }
    })()

    return () => {
      cancelled = true
      controller.abort()
    }
  }, [])

  const loading = !boardReady || !tasksReady
  const effectiveHealth: HealthState =
    sseStatus === 'open' ? 'green' : sseStatus === 'connecting' ? 'yellow' : health

  return {
    board,
    tasks,
    loading,
    error,
    isFetching,
    isStale,
    health: effectiveHealth,
    refetchTasks,
    lastDecisionsMtime,
  }
}
