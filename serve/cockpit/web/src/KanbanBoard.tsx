import { useState, useEffect, useRef } from 'react'
import { useBoard, type Board, type Task } from './hooks/useBoard'

export { useBoard }

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
  onDragStart: () => void
  onDragEnd: () => void
}

export function Card({ task, onContextMenu, onDragStart, onDragEnd }: CardProps) {
  return (
    <div
      data-testid="task-card"
      data-id={task.id}
      data-priority={task.priority}
      draggable={true}
      onDragStart={onDragStart}
      onDragEnd={onDragEnd}
      onContextMenu={(e) => onContextMenu(e, task)}
      style={{
        borderLeft: `4px solid ${PRIORITY_COLORS[task.priority] ?? '#888888'}`,
        minHeight: '48px',
        maxHeight: '56px',
        display: 'flex',
        alignItems: 'center',
        padding: '0 8px',
        boxSizing: 'border-box',
        overflow: 'hidden',
      }}
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
  onDragStart: (status: string) => void
  onDragEnd: () => void
  isValidDragTarget: boolean
}

export function Column({
  status,
  tasks,
  priorities,
  onContextMenu,
  onDragStart,
  onDragEnd,
  isValidDragTarget,
}: ColumnProps) {
  const [isDragOver, setIsDragOver] = useState(false)

  const sorted = [...tasks].sort((a, b) => priorities.indexOf(b.priority) - priorities.indexOf(a.priority))

  const handleCardDragStart = () => {
    onDragStart(status)
  }

  return (
    <div
      data-column={status}
      data-drag-over={isDragOver && isValidDragTarget ? 'true' : undefined}
      onDragOver={(e) => {
        if (isValidDragTarget) {
          e.preventDefault()
          setIsDragOver(true)
        }
      }}
      onDragLeave={() => setIsDragOver(false)}
      onDrop={(e) => {
        e.preventDefault()
        setIsDragOver(false)
      }}
      style={{ overflowY: 'auto', maxHeight: 'calc(100vh - 56px)' }}
    >
      <header>
        <span>{status}</span>
        <span data-testid="column-count">{tasks.length}</span>
      </header>
      {sorted.length === 0 ? (
        <div data-testid="empty-column">No tasks</div>
      ) : (
        sorted.map((task) => (
          <Card
            key={task.id}
            task={task}
            onContextMenu={onContextMenu}
            onDragStart={handleCardDragStart}
            onDragEnd={onDragEnd}
          />
        ))
      )}
    </div>
  )
}

// ─── KanbanBoard ──────────────────────────────────────────────────────────────

interface ContextMenuState {
  taskId: number
  taskStatus: string
  taskUpdated: string
  x: number
  y: number
}

export default function KanbanBoard() {
  const { board, tasks, loading, error, refetchTasks } = useBoard()
  const [contextMenu, setContextMenu] = useState<ContextMenuState | null>(null)
  const [moveError, setMoveError] = useState<string | null>(null)
  const [dragSourceStatus, setDragSourceStatus] = useState<string | null>(null)
  const menuRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (!contextMenu) return

    function handleMouseDown(e: MouseEvent) {
      if (menuRef.current && menuRef.current.contains(e.target as Node)) return
      setContextMenu(null)
    }

    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') setContextMenu(null)
    }

    document.addEventListener('mousedown', handleMouseDown)
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('mousedown', handleMouseDown)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [contextMenu])

  const handleContextMenu = (e: React.MouseEvent, task: Task) => {
    e.preventDefault()
    const transitions = board?.valid_transitions[task.status] ?? []
    if (transitions.length === 0) return
    setMoveError(null)
    setContextMenu({
      taskId: task.id,
      taskStatus: task.status,
      taskUpdated: task.updated,
      x: e.clientX,
      y: e.clientY,
    })
  }

  const handleDragStart = (status: string) => {
    setDragSourceStatus(status)
  }

  const handleDragEnd = () => {
    setDragSourceStatus(null)
  }

  const tasksByStatus = tasks.reduce<Record<string, Task[]>>((acc, task) => {
    if (!acc[task.status]) acc[task.status] = []
    acc[task.status].push(task)
    return acc
  }, {})

  if (loading) {
    return <div data-testid="loading-indicator">Loading…</div>
  }

  if (error || !board) {
    return (
      <div data-testid="error-message">Failed to load board. Please try again.</div>
    )
  }

  async function handleTransitionClick(taskId: number, targetStatus: string, updated: string) {
    setContextMenu(null)
    setMoveError(null)
    try {
      const res = await fetch(`/api/tasks/${taskId}/move`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: targetStatus, updated }),
      })
      if (!res.ok) {
        setMoveError(`Move failed: ${res.status}`)
        return
      }
      refetchTasks()
    } catch {
      setMoveError('Move failed: network error')
    }
  }

  return (
    <div data-testid="kanban-board" style={{ display: 'flex', gap: '16px', overflowX: 'auto' }}>
      {board.statuses.map(({ name }) => {
        const colTasks = tasksByStatus[name] ?? []
        return (
          <Column
            key={name}
            status={name}
            tasks={colTasks}
            priorities={board.priorities}
            onContextMenu={handleContextMenu}
            onDragStart={handleDragStart}
            onDragEnd={handleDragEnd}
            isValidDragTarget={
              dragSourceStatus !== null &&
              (board.valid_transitions[dragSourceStatus] ?? []).includes(name)
            }
          />
        )
      })}

      {moveError && <div data-testid="move-error">{moveError}</div>}

      {contextMenu && (
        <div
          ref={menuRef}
          data-testid="context-menu"
          role="menu"
          style={{ position: 'fixed', top: contextMenu.y, left: contextMenu.x }}
        >
          {(board.valid_transitions[contextMenu.taskStatus] ?? []).map((target) => (
            <div
              key={target}
              data-testid="transition-item"
              data-status={target}
              role="menuitem"
              onClick={() => void handleTransitionClick(contextMenu.taskId, target, contextMenu.taskUpdated)}
            >
              → {target}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
