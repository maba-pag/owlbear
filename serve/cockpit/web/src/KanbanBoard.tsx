import { useState, useEffect, useRef } from 'react'
import { Column } from './components/Column'
import ArchivalModal from './components/ArchivalModal'
import { useBoard, type Task } from './hooks/useBoard'

export { useBoard }

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

export default function KanbanBoard() {
  const { board, tasks, loading, error, refetchTasks } = useBoard()
  const [contextMenu, setContextMenu] = useState<ContextMenuState | null>(null)
  const [archivalModal, setArchivalModal] = useState<ArchivalModalState | null>(null)
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
                  contextMenu.taskStatus,
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
