import { useState, useEffect, useRef } from 'react'

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

// ─── Hook ─────────────────────────────────────────────────────────────────────

export function useBoard() {
  const [board, setBoard] = useState<Board | null>(null)
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isFetching, setIsFetching] = useState(false)
  const [isStale, setIsStale] = useState(false)
  const mtimeRef = useRef<number | null>(null)
  const inFlightRef = useRef(false)

  useEffect(() => {
    const controller = new AbortController()
    let cancelled = false
    let pendingPoll = false

    async function load() {
      try {
        const [boardRes, tasksRes] = await Promise.all([
          fetch('/api/board', { signal: controller.signal }),
          fetch('/api/tasks', { signal: controller.signal }),
        ])

        if (!boardRes.ok) throw new Error(`Board API error: ${boardRes.status}`)
        if (!tasksRes.ok) throw new Error(`Tasks API error: ${tasksRes.status}`)

        const boardData = (await boardRes.json()) as Board
        const tasksData = (await tasksRes.json()) as TasksResponse

        if (!cancelled) {
          mtimeRef.current = tasksData.mtime
          setBoard(boardData)
          setTasks(tasksData.tasks)
          setLoading(false)
        }
      } catch (err) {
        if (!cancelled && !(err instanceof DOMException && err.name === 'AbortError')) {
          setError(err instanceof Error ? err.message : 'Failed to load board')
          setLoading(false)
        }
      }
    }

    async function pollTasks() {
      if (inFlightRef.current) {
        pendingPoll = true
        return
      }
      inFlightRef.current = true
      pendingPoll = false
      setIsFetching(true)
      try {
        const res = await fetch('/api/tasks', { signal: controller.signal })
        if (!res.ok) throw new Error(`Poll error: ${res.status}`)
        const data = (await res.json()) as TasksResponse
        if (!cancelled) {
          if (data.mtime !== mtimeRef.current) {
            mtimeRef.current = data.mtime
            setTasks(data.tasks)
          }
          setError(null)
          setIsStale(false)
        }
      } catch (err) {
        if (!cancelled && !(err instanceof DOMException && err.name === 'AbortError')) {
          setError(err instanceof Error ? err.message : 'Poll failed')
          setIsStale(true)
        }
      } finally {
        inFlightRef.current = false
        if (!cancelled) setIsFetching(false)
        if (pendingPoll && !cancelled) {
          pendingPoll = false
          void pollTasks()
        }
      }
    }

    void load()
    const intervalId = setInterval(() => void pollTasks(), 3000)

    return () => {
      cancelled = true
      controller.abort()
      clearInterval(intervalId)
    }
  }, [])

  function refetchTasks() {
    void (async () => {
      try {
        const res = await fetch('/api/tasks')
        if (res.ok) {
          const data = (await res.json()) as TasksResponse
          if (data.mtime !== mtimeRef.current) {
            mtimeRef.current = data.mtime
            setTasks(data.tasks)
          }
        }
      } catch {
        // silent — board data stays stale
      }
    })()
  }

  return { board, tasks, loading, error, isFetching, isStale, refetchTasks }
}
