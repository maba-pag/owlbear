import { useState, useEffect, useRef } from 'react'

type StatusConfig = { name: string }

type BoardOut = {
  statuses: StatusConfig[]
  priorities: string[]
  valid_transitions: Record<string, string[]>
}

type TaskSummary = {
  id: number
  title: string
  status: string
  priority: string
  tags: string[]
  blocked: boolean
  block_reason: string | null
  claimed: boolean
}

type TaskListOut = {
  tasks: TaskSummary[]
  mtime: number
}

type ContextMenuState = {
  taskId: number
  status: string
  x: number
  y: number
} | null

export default function KanbanBoard() {
  const [board, setBoard] = useState<BoardOut | null>(null)
  const [tasks, setTasks] = useState<TaskSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [contextMenu, setContextMenu] = useState<ContextMenuState>(null)
  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    let cancelled = false
    Promise.all([
      fetch('/api/board').then(r => {
        if (!r.ok) throw new Error('board fetch failed')
        return r.json()
      }),
      fetch('/api/tasks').then(r => {
        if (!r.ok) throw new Error('tasks fetch failed')
        return r.json()
      }),
    ])
      .then(([boardData, tasksData]: [BoardOut, TaskListOut]) => {
        if (!cancelled) {
          setBoard(boardData)
          setTasks(tasksData.tasks)
          setLoading(false)
        }
      })
      .catch((err: Error) => {
        if (!cancelled) {
          setError(err.message || 'Failed to load board')
          setLoading(false)
        }
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (!contextMenu) return
    const close = () => setContextMenu(null)
    document.addEventListener('click', close)
    return () => document.removeEventListener('click', close)
  }, [contextMenu])

  if (loading) {
    return <div data-testid="loading-indicator">Loading…</div>
  }

  if (error) {
    return <div data-testid="error-message">Failed to load board. Please retry.</div>
  }

  if (!board) return null

  return (
    <div style={{ display: 'flex', flexDirection: 'row', overflow: 'auto' }}>
      {board.statuses.map(({ name }) => {
        const colTasks = tasks
          .filter(t => t.status === name)
          .sort(
            (a, b) =>
              board.priorities.indexOf(b.priority) - board.priorities.indexOf(a.priority),
          )

        return (
          <div
            key={name}
            data-column={name}
            style={{ minWidth: 200, padding: 8, overflowY: 'auto' }}
          >
            <div>
              <span>{name}</span>
              <span data-testid="column-count">{colTasks.length}</span>
            </div>
            {colTasks.length === 0 ? (
              <div data-testid="empty-column">No tasks here</div>
            ) : (
              colTasks.map(task => (
                <div
                  key={task.id}
                  data-testid="task-card"
                  data-id={String(task.id)}
                  data-priority={task.priority}
                  onContextMenu={e => {
                    e.preventDefault()
                    setContextMenu({ taskId: task.id, status: task.status, x: e.clientX, y: e.clientY })
                  }}
                >
                  <span data-testid="card-title" title={task.title}>
                    {task.title}
                  </span>
                  {task.blocked && (
                    <span
                      data-testid="block-badge"
                      title={task.block_reason ?? 'Blocked'}
                      aria-label={task.block_reason ?? 'Blocked'}
                    >
                      Blocked
                    </span>
                  )}
                  {task.claimed && <span data-testid="running-indicator">Running</span>}
                </div>
              ))
            )}
          </div>
        )
      })}
      {contextMenu && (
        <div
          ref={menuRef}
          data-testid="context-menu"
          style={{ position: 'fixed', top: contextMenu.y, left: contextMenu.x }}
          onClick={e => e.stopPropagation()}
        >
          {(board.valid_transitions[contextMenu.status] ?? []).map(target => (
            <div key={target} data-testid="transition-item" data-status={target}>
              Move to {target}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
