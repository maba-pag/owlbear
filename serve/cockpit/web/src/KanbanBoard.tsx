import { useState, useEffect, useRef } from 'react'
import { Column } from './components/Column'
import ArchivalModal from './components/ArchivalModal'
import FilterPanel from './components/FilterPanel'
import { filterTasks, type FilterState } from './utils/filterTasks'
import { type Board, type Task } from './hooks/useBoard'
import { moveTask } from './api/tasks'
import { ApiError } from './api/errors'
import { PButton } from '@porsche-design-system/components-react'
import './KanbanBoard.css'

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

const EMPTY_FILTER: FilterState = {
  text: '',
  priority: '',
  tags: [],
  blocked: false,
}

export interface KanbanBoardProps {
  board?: Board | null
  tasks?: Task[]
  loading?: boolean
  error?: string | null
  refetchTasks?: () => void
  selectedId?: number | null
  pendingDRIds?: Set<number>
  onSelectTask?: (taskId: number) => void
  onMutationError?: (heading: string, description: string, state: 'error' | 'warning') => void
  onMutationSuccess?: () => void
}

interface ResolvedKanbanBoardProps {
  board: Board | null
  tasks: Task[]
  loading: boolean
  error: string | null
  refetchTasks: () => void
  selectedId: number | null
  pendingDRIds: Set<number>
  onSelectTask?: (taskId: number) => void
  onMutationError?: (heading: string, description: string, state: 'error' | 'warning') => void
  onMutationSuccess?: () => void
}

function KanbanBoardContent({
  board,
  tasks,
  loading,
  error,
  refetchTasks,
  selectedId,
  pendingDRIds,
  onSelectTask,
  onMutationError,
  onMutationSuccess,
}: ResolvedKanbanBoardProps) {
  const [contextMenu, setContextMenu] = useState<ContextMenuState | null>(null)
  const [archivalModal, setArchivalModal] = useState<ArchivalModalState | null>(null)
  const [dragSource, setDragSource] = useState<DragSourceState | null>(null)
  const [filter, setFilter] = useState<FilterState>(EMPTY_FILTER)
  const [panelOpen, setPanelOpen] = useState(false)
  const [filterAnnouncement, setFilterAnnouncement] = useState('')
  const menuRef = useRef<HTMLDivElement | null>(null)
  const filterToggleRef = useRef<HTMLElement | null>(null)
  const announcementTimerRef = useRef<number | null>(null)
  const contextMenuOriginRef = useRef<HTMLElement | null>(null)
  const archivalReturnFocusRef = useRef<HTMLElement | null>(null)

  const filteredTasks = filterTasks(tasks, filter)
  const availableTags = [...new Set(tasks.flatMap((task) => task.tags))]
  const activeFilterCount =
    (filter.text ? 1 : 0) +
    (filter.priority ? 1 : 0) +
    (filter.tags.length > 0 ? 1 : 0) +
    (filter.blocked ? 1 : 0)
  const hasActiveFilters = activeFilterCount > 0

  useEffect(() => {
    if (!contextMenu) return

    function handleMouseDown(e: MouseEvent) {
      if (menuRef.current && menuRef.current.contains(e.target as Node)) return
      setContextMenu(null)
      contextMenuOriginRef.current?.focus()
    }

    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        setContextMenu(null)
        contextMenuOriginRef.current?.focus()
      }
    }

    document.addEventListener('mousedown', handleMouseDown)
    document.addEventListener('keydown', handleKeyDown)

    const firstItem = menuRef.current?.querySelector<HTMLElement>('[role="menuitem"]')
    firstItem?.focus()

    return () => {
      document.removeEventListener('mousedown', handleMouseDown)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [contextMenu])

  useEffect(() => {
    return () => {
      if (announcementTimerRef.current !== null) {
        window.clearTimeout(announcementTimerRef.current)
      }
    }
  }, [])

  const handleContextMenu = (e: React.MouseEvent, task: Task) => {
    e.preventDefault()
    const transitions = board?.valid_transitions[task.status] ?? []
    if (transitions.length === 0) return
    contextMenuOriginRef.current = e.currentTarget as HTMLElement
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
    setDragSource(null)

    try {
      await moveTask(taskId, { status: targetStatus, updated: taskUpdated })
      refetchTasks()
      onMutationSuccess?.()
    } catch (error) {
      if (error instanceof ApiError) {
        if (error.status === 409) {
          refetchTasks()
        }
        const fallback = `Move failed: ${error.status}`
        const message = error.message === `Move task request failed with status ${error.status}`
          ? fallback
          : error.message
        onMutationError?.('Move failed', message, 'error')
        return
      }

      const networkMessage = error instanceof Error ? error.message : 'Move failed: network error'
      onMutationError?.('Move failed', networkMessage, 'error')
    }
  }

  const tasksByStatus = filteredTasks.reduce<Record<string, Task[]>>((acc, task) => {
    if (!acc[task.status]) acc[task.status] = []
    acc[task.status].push(task)
    return acc
  }, {})

  if (loading) {
    return <div data-testid="loading-indicator">Loading…</div>
  }

  if (error) {
    return <div data-testid="error-message">{error}</div>
  }

  if (!board) {
    return (
      <div data-testid="error-message">Failed to load board. Please try again.</div>
    )
  }

  async function handleTransitionClick(taskId: number, targetStatus: string, taskStatus: string, updated: string) {
    setContextMenu(null)

    if (targetStatus === 'archived') {
      archivalReturnFocusRef.current = document.querySelector<HTMLElement>(
        `[data-testid="task-card"][data-id="${taskId}"]`,
      )
      setArchivalModal({
        taskId,
        taskStatus,
        expectedUpdated: updated,
      })
      return
    }

    try {
      await moveTask(taskId, { status: targetStatus, updated })
      refetchTasks()
      onMutationSuccess?.()
    } catch (error) {
      if (error instanceof ApiError) {
        if (error.status === 409) {
          refetchTasks()
        }
        const fallback = `Move failed: ${error.status}`
        const message = error.message === `Move task request failed with status ${error.status}`
          ? fallback
          : error.message
        onMutationError?.('Move failed', message, 'error')
        return
      }

      const networkMessage = error instanceof Error ? error.message : 'Move failed: network error'
      onMutationError?.('Move failed', networkMessage, 'error')
    }
  }

  const handleFilterChange = (nextFilter: FilterState) => {
    setContextMenu(null)
    setDragSource(null)

    if (announcementTimerRef.current !== null) {
      window.clearTimeout(announcementTimerRef.current)
    }

    const updateAnnouncement = () => {
      const nextFilteredCount = filterTasks(tasks, nextFilter).length
      setFilterAnnouncement(`${nextFilteredCount} / ${tasks.length} tasks`)
    }

    if (nextFilter.text !== filter.text) {
      announcementTimerRef.current = window.setTimeout(updateAnnouncement, 300)
    } else {
      updateAnnouncement()
    }

    setFilter(nextFilter)
  }

  return (
    <div
      data-testid="kanban-board"
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '16px',
        minHeight: 0,
        height: '100%',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <PButton
          ref={filterToggleRef}
          type="button"
          data-testid="filter-toggle"
          tabIndex={0}
          aria-expanded={panelOpen ? 'true' : 'false'}
          aria-controls="filter-panel"
          variant="secondary"
          onClick={() => setPanelOpen((open) => !open)}
        >
          Filters
          {hasActiveFilters ? ` (${activeFilterCount})` : ''}
        </PButton>
        <span
          data-testid="filter-result-count-live"
          aria-live="polite"
          style={{ position: 'absolute', left: '-9999px' }}
        >
          {filterAnnouncement}
        </span>
        {hasActiveFilters ? (
          <span data-testid="filter-result-count">
            {filteredTasks.length} / {tasks.length} tasks
          </span>
        ) : null}
      </div>

      <FilterPanel
        filter={filter}
        onFilterChange={handleFilterChange}
        priorities={board.priorities}
        availableTags={availableTags}
        open={panelOpen}
        onClose={() => {
          setPanelOpen(false)
          filterToggleRef.current?.focus()
        }}
      />

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: 'var(--pds-spacing-md)',
          padding: 'var(--pds-spacing-md)',
          overflowX: 'auto',
          flex: 1,
          minHeight: 0,
        }}
      >
        {board.statuses.map(({ name }) => {
          const colTasks = tasksByStatus[name] ?? []
          return (
            <Column
              key={name}
              status={name}
              tasks={colTasks}
              priorities={board.priorities}
              selectedId={selectedId}
              pendingDRIds={pendingDRIds}
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
      </div>
      {archivalModal && (
        <ArchivalModal
          taskId={archivalModal.taskId}
          taskStatus={archivalModal.taskStatus}
          expectedUpdated={archivalModal.expectedUpdated}
          returnFocusTo={archivalReturnFocusRef.current}
          onClose={() => {
            setArchivalModal(null)
          }}
          onRefresh={refetchTasks}
        />
      )}

      {contextMenu && (
        <div
          ref={menuRef}
          className="kanban-context-menu"
          data-testid="context-menu"
          role="menu"
          aria-label="Task actions"
          style={{ position: 'fixed', top: contextMenu.y, left: contextMenu.x }}
        >
          {(board.valid_transitions[contextMenu.taskStatus] ?? []).map((target) => (
            <div
              key={target}
              data-testid="transition-item"
              data-status={target}
              role="menuitem"
              tabIndex={-1}
              onKeyDown={(event) => {
                if (event.key === 'Enter' || event.key === ' ') {
                  event.preventDefault()
                  event.currentTarget.click()
                  return
                }

                const menu = event.currentTarget.parentElement
                if (!menu) return
                const items = Array.from(menu.querySelectorAll<HTMLElement>('[role="menuitem"]'))
                const index = items.indexOf(event.currentTarget)

                if (event.key === 'ArrowDown') {
                  event.preventDefault()
                  items[(index + 1) % items.length]?.focus()
                } else if (event.key === 'ArrowUp') {
                  event.preventDefault()
                  items[(index - 1 + items.length) % items.length]?.focus()
                } else if (event.key === 'Home') {
                  event.preventDefault()
                  items[0]?.focus()
                } else if (event.key === 'End') {
                  event.preventDefault()
                  items[items.length - 1]?.focus()
                }
              }}
              onClick={() =>
                void handleTransitionClick(
                  contextMenu.taskId,
                  target,
                  tasks.find((task) => task.id === contextMenu.taskId)?.status ?? contextMenu.taskStatus,
                  contextMenu.taskUpdated,
                )
              }
            >
              Move to {target}
            </div>
          ))}
          {(board.valid_transitions[contextMenu.taskStatus] ?? []).includes('archived') ? null : (
            <div
              role="menuitem"
              onClick={() =>
                void handleTransitionClick(
                  contextMenu.taskId,
                  'archived',
                  tasks.find((task) => task.id === contextMenu.taskId)?.status ?? contextMenu.taskStatus,
                  contextMenu.taskUpdated,
                )
              }
            >
              Archive
            </div>
          )}
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
  pendingDRIds = new Set<number>(),
  onSelectTask,
  onMutationError,
  onMutationSuccess,
}: KanbanBoardProps) {
  return (
    <KanbanBoardContent
      board={board}
      tasks={tasks}
      loading={loading}
      error={error}
      refetchTasks={refetchTasks}
      selectedId={selectedId}
      pendingDRIds={pendingDRIds}
      onSelectTask={onSelectTask}
      onMutationError={onMutationError}
      onMutationSuccess={onMutationSuccess}
    />
  )
}
