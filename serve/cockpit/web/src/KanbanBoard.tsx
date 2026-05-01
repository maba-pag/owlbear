import { useState, useEffect, useRef } from 'react'
import { Column } from './components/Column'
import ArchivalModal from './components/ArchivalModal'
import { type Board, type Task } from './hooks/useBoard'

// ─── KanbanBoard ──────────────────────────────────────────────────────────────

interface ContextMenuState {
  taskId: number
  taskStatus: string
  taskUpdated: string
  x: number
  y: number
}

interface ArchivalModalState {
  taskId: number
  taskStatus: string
  expectedUpdated: string
}

interface DragSourceState {
  status: string
  taskId: number
  taskUpdated: string
}

export interface KanbanBoardProps {
  board?: Board | null
  tasks?: Task[]
  loading?: boolean
  error?: string | null
  refetchTasks?: () => void
  selectedId?: number | null
  onSelectTask?: (taskId: number) => void
}

interface ResolvedKanbanBoardProps {
  board: Board | null
  tasks: Task[]
  loading: boolean
  error: string | null
  refetchTasks: () => void
  selectedId: number | null
  onSelectTask?: (taskId: number) => void
}

function KanbanBoardContent({
  board,
  tasks,
  loading,
  error,
  refetchTasks,
  selectedId,
  onSelectTask,
}: ResolvedKanbanBoardProps) {
  const [contextMenu, setContextMenu] = useState<ContextMenuState | null>(null)
  const [archivalModal, setArchivalModal] = useState<ArchivalModalState | null>(null)
  const [moveError, setMoveError] = useState<string | null>(null)
  const [dragSource, setDragSource] = useState<DragSourceState | null>(null)
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

  const handleDragStart = (status: string, taskId: number, taskUpdated: string) => {
    setDragSource({ status, taskId, taskUpdated })
  }

  const handleDragEnd = () => {
    setDragSource(null)
  }

  async function handleDrop(targetStatus: string) {
    if (!dragSource) {
      return
    }

    const { taskId, taskUpdated } = dragSource
    setMoveError(null)
    setDragSource(null)

    try {
      const res = await fetch(`/api/tasks/${taskId}/move`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: targetStatus, updated: taskUpdated }),
      })
      if (res.ok) {
        refetchTasks()
        return
      }

      if (res.status === 409) {
        setMoveError('Move failed: stale snapshot (409)')
        refetchTasks()
        return
      }

      setMoveError(`Move failed: ${res.status}`)
    } catch {
      setMoveError('Move failed: network error')
    }
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

  async function handleTransitionClick(taskId: number, targetStatus: string, taskStatus: string, updated: string) {
    setContextMenu(null)
    setMoveError(null)

    if (targetStatus === 'archived') {
      setArchivalModal({
        taskId,
        taskStatus,
        expectedUpdated: updated,
      })
      return
    }

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
            selectedId={selectedId}
            onSelectTask={onSelectTask}
            onContextMenu={handleContextMenu}
            onDragStart={handleDragStart}
            onDrop={handleDrop}
            onDragEnd={handleDragEnd}
            isValidDragTarget={
              dragSource !== null &&
              (board.valid_transitions[dragSource.status] ?? []).includes(name)
            }
          />
        )
      })}

      {moveError && <div data-testid="move-error">{moveError}</div>}

      {archivalModal && (
        <ArchivalModal
          taskId={archivalModal.taskId}
          taskStatus={archivalModal.taskStatus}
          expectedUpdated={archivalModal.expectedUpdated}
          onClose={() => {
            setArchivalModal(null)
          }}
          onRefresh={refetchTasks}
        />
      )}

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
              onClick={() =>
                void handleTransitionClick(
                  contextMenu.taskId,
                  target,
                  tasks.find((task) => task.id === contextMenu.taskId)?.status ?? contextMenu.taskStatus,
                  contextMenu.taskUpdated,
                )
              }
            >
              → {target}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default function KanbanBoard({
  board = null,
  tasks = [],
  loading = true,
  error = null,
  refetchTasks = () => {},
  selectedId = null,
  onSelectTask,
}: KanbanBoardProps) {
  return (
    <KanbanBoardContent
      board={board}
      tasks={tasks}
      loading={loading}
      error={error}
      refetchTasks={refetchTasks}
      selectedId={selectedId}
      onSelectTask={onSelectTask}
    />
  )
}
