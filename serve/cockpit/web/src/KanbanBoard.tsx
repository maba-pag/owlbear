import { useState, useEffect } from 'react'

// ─── Types ────────────────────────────────────────────────────────────────────

interface BoardStatus {
  name: string
}

interface Board {
  statuses: BoardStatus[]
  priorities: string[]
  valid_transitions: Record<string, string[]>
}

interface Task {
  id: number
  title: string
  status: string
  priority: string
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
}

// ─── Hook ─────────────────────────────────────────────────────────────────────

export function useBoard(): UseBoardResult {
  const [board, setBoard] = useState<Board | null>(null)
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    async function load() {
      try {
        const [boardRes, tasksRes] = await Promise.all([fetch('/api/board'), fetch('/api/tasks')])

        if (!boardRes.ok) throw new Error(`Board API error: ${boardRes.status}`)
        if (!tasksRes.ok) throw new Error(`Tasks API error: ${tasksRes.status}`)

        const boardData = (await boardRes.json()) as Board
        const tasksData = (await tasksRes.json()) as TasksResponse

        if (!cancelled) {
          setBoard(boardData)
          setTasks(tasksData.tasks)
          setLoading(false)
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load board')
          setLoading(false)
        }
      }
    }

    void load()
    return () => {
      cancelled = true
    }
  }, [])

  return { board, tasks, loading, error }
}

// ─── Priority colours ───────────────────────────────────────────────────────

const PRIORITY_COLORS: Record<string, string> = {
  critical: '#e00000',
  needed: '#ff8000',
  important: '#ffcc00',
  'nice-to-have': '#0066cc',
  someday: '#888888',
}

// ─── Card ─────────────────────────────────────────────────────────────────────

interface CardProps {
  task: Task
  onContextMenu: (e: React.MouseEvent, task: Task) => void
}

function Card({ task, onContextMenu }: CardProps) {
  return (
    <div
      data-testid="task-card"
      data-id={task.id}
      data-priority={task.priority}
      style={{ borderLeft: `4px solid ${PRIORITY_COLORS[task.priority] ?? '#888888'}` }}
      onContextMenu={(e) => onContextMenu(e, task)}
    >
      <span data-testid="card-title" title={task.title}>
        {task.title}
      </span>
      {task.blocked && (
        <span
          data-testid="block-badge"
          title={task.block_reason ?? ''}
          aria-label={task.block_reason ?? ''}
        >
          ⛔
        </span>
      )}
      {task.claimed && <span data-testid="running-indicator">▶</span>}
    </div>
  )
}

// ─── Column ───────────────────────────────────────────────────────────────────

interface ColumnProps {
  status: string
  tasks: Task[]
  priorities: string[]
  onContextMenu: (e: React.MouseEvent, task: Task) => void
}

function Column({ status, tasks, priorities, onContextMenu }: ColumnProps) {
  const sorted = [...tasks].sort(
    (a, b) => priorities.indexOf(b.priority) - priorities.indexOf(a.priority),
  )

  return (
    <div data-column={status}>
      <header>
        <span>{status}</span>
        <span data-testid="column-count">{tasks.length}</span>
      </header>
      {sorted.length === 0 ? (
        <div data-testid="empty-column">No tasks</div>
      ) : (
        sorted.map((task) => <Card key={task.id} task={task} onContextMenu={onContextMenu} />)
      )}
    </div>
  )
}

// ─── KanbanBoard ──────────────────────────────────────────────────────────────

interface ContextMenuState {
  taskStatus: string
  x: number
  y: number
}

export default function KanbanBoard() {
  const { board, tasks, loading, error } = useBoard()
  const [contextMenu, setContextMenu] = useState<ContextMenuState | null>(null)

  if (loading) {
    return <div data-testid="loading-indicator">Loading…</div>
  }

  if (error || !board) {
    return (
      <div data-testid="error-message">Failed to load board. Please try again.</div>
    )
  }

  function handleContextMenu(e: React.MouseEvent, task: Task) {
    e.preventDefault()
    setContextMenu({ taskStatus: task.status, x: e.clientX, y: e.clientY })
  }

  return (
    <div style={{ display: 'flex', gap: '16px', overflowX: 'auto' }}>
      {board.statuses.map(({ name }) => {
        const colTasks = tasks.filter((t) => t.status === name)
        return (
          <Column
            key={name}
            status={name}
            tasks={colTasks}
            priorities={board.priorities}
            onContextMenu={handleContextMenu}
          />
        )
      })}

      {contextMenu && (
        <div
          data-testid="context-menu"
          style={{ position: 'fixed', top: contextMenu.y, left: contextMenu.x }}
        >
          {(board.valid_transitions[contextMenu.taskStatus] ?? []).map((target) => (
            <div key={target} data-testid="transition-item" data-status={target}>
              → {target}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
