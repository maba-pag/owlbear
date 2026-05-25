import { useState, useEffect, useRef, type KeyboardEvent as ReactKeyboardEvent } from 'react'
import { PButton, PTag } from '@porsche-design-system/components-react'
import { Column } from './components/Column'
import ArchivalModal from './components/ArchivalModal'
import FilterPanel from './components/FilterPanel'
import { WorkspaceHeader, WorkspaceHeaderMetric } from './components/WorkspaceHeader'
import { filterTasks, type FilterState } from './utils/filterTasks'
import { formatStatusLabel, getOrderedTransitionTargets, shouldShowArchiveAction } from './utils/taskTransitions'
import { type Board, type Task } from './hooks/useBoard'
import { moveTask } from './api/tasks'
import { ApiError } from './api/errors'

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

const EMPTY_FILTER: FilterState = {
  text: '',
  priority: '',
  tags: [],
  blocked: false,
}

const CONTEXT_MENU_VIEWPORT_PADDING = 8
const CONTEXT_MENU_MIN_WIDTH = 160
const CONTEXT_MENU_ITEM_HEIGHT = 40
const CONTEXT_MENU_VERTICAL_CHROME = 10
const INITIAL_ALIGNMENT_CONTEXT_COLUMNS = 1
const INITIAL_ALIGNMENT_EDGE_TOLERANCE = 1

function getActiveFilterLabels(filter: FilterState): string[] {
  const labels: string[] = []
  const searchText = filter.text.trim()

  if (searchText) {
    labels.push(`Search: ${searchText}`)
  }
  if (filter.priority) {
    labels.push(`Priority: ${formatStatusLabel(filter.priority)}`)
  }
  if (filter.tags.length > 0) {
    labels.push(`Tags: ${filter.tags.join(', ')}`)
  }
  if (filter.blocked) {
    labels.push('Blocked only')
  }

  return labels
}

function clampContextMenuCoordinates(
  x: number,
  y: number,
  width: number,
  height: number,
): { x: number; y: number } {
  const maxX = Math.max(
    CONTEXT_MENU_VIEWPORT_PADDING,
    window.innerWidth - width - CONTEXT_MENU_VIEWPORT_PADDING,
  )
  const maxY = Math.max(
    CONTEXT_MENU_VIEWPORT_PADDING,
    window.innerHeight - height - CONTEXT_MENU_VIEWPORT_PADDING,
  )

  return {
    x: Math.min(Math.max(CONTEXT_MENU_VIEWPORT_PADDING, x), maxX),
    y: Math.min(Math.max(CONTEXT_MENU_VIEWPORT_PADDING, y), maxY),
  }
}

function clampContextMenuPosition(x: number, y: number, menu: HTMLElement): { x: number; y: number } {
  const rect = menu.getBoundingClientRect()
  return clampContextMenuCoordinates(
    x,
    y,
    Math.max(CONTEXT_MENU_MIN_WIDTH, rect.width, menu.offsetWidth),
    Math.max(CONTEXT_MENU_ITEM_HEIGHT, rect.height, menu.offsetHeight),
  )
}

function getEstimatedContextMenuHeight(itemCount: number): number {
  return (itemCount * CONTEXT_MENU_ITEM_HEIGHT) + CONTEXT_MENU_VERTICAL_CHROME
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
  onMutationSuccess?: (message?: string) => void
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
  onMutationSuccess?: (message?: string) => void
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
  const [filter, setFilter] = useState<FilterState>(EMPTY_FILTER)
  const [panelOpen, setPanelOpen] = useState(false)
  const [isMobileLayout, setIsMobileLayout] = useState(() => {
    if (typeof window === 'undefined') {
      return false
    }
    return window.innerWidth <= 767 || window.matchMedia('(max-width: 767px)').matches
  })
  const [filterAnnouncement, setFilterAnnouncement] = useState('')
  const menuRef = useRef<HTMLDivElement | null>(null)
  const filterToggleRef = useRef<HTMLElement | null>(null)
  const announcementTimerRef = useRef<number | null>(null)
  const contextMenuOriginRef = useRef<HTMLElement | null>(null)
  const archivalReturnFocusRef = useRef<HTMLElement | null>(null)
  const columnStripRef = useRef<HTMLDivElement | null>(null)
  const lastAutoAlignedSignatureRef = useRef<string | null>(null)

  const filteredTasks = filterTasks(tasks, filter)
  const availableTags = [...new Set(tasks.flatMap((task) => task.tags))]
  const activeFilterCount =
    (filter.text ? 1 : 0) +
    (filter.priority ? 1 : 0) +
    (filter.tags.length > 0 ? 1 : 0) +
    (filter.blocked ? 1 : 0)
  const hasActiveFilters = activeFilterCount > 0
  const activeFilterLabels = getActiveFilterLabels(filter)
  const boardTaskCount = hasActiveFilters ? `${filteredTasks.length} / ${tasks.length}` : tasks.length
  const boardTaskLabel = 'tasks'

  useEffect(() => {
    const mediaQuery = window.matchMedia('(max-width: 767px)')
    const handleViewportChange = () => {
      setIsMobileLayout(window.innerWidth <= 767 || mediaQuery.matches)
    }

    handleViewportChange()
    mediaQuery.addEventListener('change', handleViewportChange)

    return () => {
      mediaQuery.removeEventListener('change', handleViewportChange)
    }
  }, [])

  useEffect(() => {
    if (!contextMenu) return

    const menuElement = menuRef.current
    if (menuElement) {
      const nextPosition = clampContextMenuPosition(contextMenu.x, contextMenu.y, menuElement)
      if (nextPosition.x !== contextMenu.x || nextPosition.y !== contextMenu.y) {
        setContextMenu((current) => current ? { ...current, ...nextPosition } : current)
        return
      }
    }

    function handleMouseDown(e: MouseEvent) {
      if (menuRef.current && menuRef.current.contains(e.target as Node)) return
      setContextMenu(null)
      contextMenuOriginRef.current?.focus()
    }

    function handleKeyDown(e: globalThis.KeyboardEvent) {
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

  useEffect(() => {
    const toggleElement = filterToggleRef.current
    if (!toggleElement) {
      return
    }

    toggleElement.setAttribute('aria-controls', 'filter-panel')
    toggleElement.setAttribute('aria-expanded', panelOpen ? 'true' : 'false')
  }, [panelOpen])

  const handleContextMenu = (e: React.MouseEvent, task: Task) => {
    e.preventDefault()
    if (!board) return
    const transitions = getOrderedTransitionTargets(board, task.status)
    const hasArchiveAction = shouldShowArchiveAction(task.status)
    if (transitions.length === 0 && !hasArchiveAction) return
    const itemCount = transitions.length + (hasArchiveAction ? 1 : 0)
    const position = clampContextMenuCoordinates(
      e.clientX,
      e.clientY,
      CONTEXT_MENU_MIN_WIDTH,
      getEstimatedContextMenuHeight(itemCount),
    )
    contextMenuOriginRef.current = e.currentTarget as HTMLElement
    setContextMenu({
      taskId: task.id,
      taskStatus: task.status,
      taskUpdated: task.updated,
      x: position.x,
      y: position.y,
    })
  }

  function handleMenuItemKeyDown(event: ReactKeyboardEvent<HTMLDivElement>) {
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
  }

  const tasksByStatus = filteredTasks.reduce<Record<string, Task[]>>((acc, task) => {
    if (!acc[task.status]) acc[task.status] = []
    acc[task.status].push(task)
    return acc
  }, {})
  const firstNonEmptyStatusIndex = board?.statuses.findIndex(({ name }) => (tasksByStatus[name]?.length ?? 0) > 0) ?? -1
  const firstNonEmptyStatus = firstNonEmptyStatusIndex >= 0 ? board?.statuses[firstNonEmptyStatusIndex]?.name ?? null : null
  const initialLeadStatusIndex = firstNonEmptyStatusIndex >= 0
    ? Math.max(0, firstNonEmptyStatusIndex - INITIAL_ALIGNMENT_CONTEXT_COLUMNS)
    : -1
  const initialLeadStatus = firstNonEmptyStatusIndex >= 0
    ? board?.statuses[initialLeadStatusIndex]?.name ?? firstNonEmptyStatus
    : null
  const statusOccupancySignature = board
    ? board.statuses.map(({ name }) => `${name}:${tasksByStatus[name]?.length ?? 0}`).join('|')
    : ''

  useEffect(() => {
    if (!firstNonEmptyStatus || !initialLeadStatus || statusOccupancySignature === lastAutoAlignedSignatureRef.current) {
      return
    }

    const columnStrip = columnStripRef.current
    if (!columnStrip) {
      return
    }

    lastAutoAlignedSignatureRef.current = statusOccupancySignature
    if (columnStrip.scrollWidth <= columnStrip.clientWidth) {
      return
    }

    const columns = Array.from(columnStrip.querySelectorAll<HTMLElement>('[data-column]'))
    const targetColumn = columns
      .find((column) => column.dataset.column === firstNonEmptyStatus)
    const leadColumn = columns
      .find((column) => column.dataset.column === initialLeadStatus)
    if (!targetColumn) {
      return
    }
    if (!leadColumn) {
      return
    }

    const stripRect = columnStrip.getBoundingClientRect()
    const targetRect = targetColumn.getBoundingClientRect()
    const paddingLeft = Number.parseFloat(getComputedStyle(columnStrip).paddingLeft) || 0
    const contextDesiredLeadLeft = initialLeadStatusIndex <= 0 ? stripRect.left + paddingLeft : stripRect.left
    const leadRect = leadColumn.getBoundingClientRect()
    const contextScrollDelta = leadRect.left - contextDesiredLeadLeft
    const projectedTargetLeft = targetRect.left - contextScrollDelta
    const projectedTargetRight = targetRect.right - contextScrollDelta
    const contextKeepsTargetVisible = projectedTargetLeft >= stripRect.left && projectedTargetRight <= stripRect.right
    const alignmentColumn = contextKeepsTargetVisible ? leadColumn : targetColumn
    const alignmentStatusIndex = contextKeepsTargetVisible ? initialLeadStatusIndex : firstNonEmptyStatusIndex
    const alignmentRect = alignmentColumn.getBoundingClientRect()
    const desiredAlignmentLeft = alignmentStatusIndex <= 0 ? stripRect.left + paddingLeft : stripRect.left
    const alignmentSatisfied = Math.abs(alignmentRect.left - desiredAlignmentLeft) <= INITIAL_ALIGNMENT_EDGE_TOLERANCE
    const targetFullyVisible = targetRect.left >= stripRect.left && targetRect.right <= stripRect.right
    if (alignmentSatisfied && targetFullyVisible) {
      return
    }

    const nextScrollLeft = Math.max(0, columnStrip.scrollLeft + alignmentRect.left - desiredAlignmentLeft)
    columnStrip.scrollTo({ left: nextScrollLeft, behavior: 'auto' })
  }, [firstNonEmptyStatus, firstNonEmptyStatusIndex, initialLeadStatus, initialLeadStatusIndex, statusOccupancySignature])

  if (loading) {
    return <div data-testid="loading-indicator" role="status">Preparing board...</div>
  }

  if (error) {
    return <div data-testid="error-message">Board is unavailable. {error}</div>
  }

  if (!board) {
    return (
      <div data-testid="error-message">Board is unavailable. Please refresh and try again.</div>
    )
  }

  const contextMenuTransitions = contextMenu
    ? getOrderedTransitionTargets(board, contextMenu.taskStatus)
    : []
  const contextMenuHasArchiveTransition = contextMenu
    ? (board.valid_transitions[contextMenu.taskStatus] ?? []).includes('archived')
    : false
  const contextMenuHasArchiveAction = contextMenu
    ? shouldShowArchiveAction(contextMenu.taskStatus)
    : false

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
      onMutationSuccess?.(`Task moved to ${formatStatusLabel(targetStatus)}`)
    } catch (error) {
      if (error instanceof ApiError) {
        if (error.status === 409) {
          refetchTasks()
        }
        const fallback = 'Move could not be completed. Try again.'
        const message = error.message === `Move task request failed with status ${error.status}`
          ? fallback
          : error.message
        onMutationError?.('Move failed', message, 'error')
        return
      }

      const networkMessage = error instanceof Error ? error.message : 'Move could not be completed. Check your connection and try again.'
      onMutationError?.('Move failed', networkMessage, 'error')
    }
  }

  const handleFilterChange = (nextFilter: FilterState) => {
    setContextMenu(null)

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

  const clearFilters = () => {
    handleFilterChange(EMPTY_FILTER)
  }

  return (
    <div
      className="relative flex h-full min-h-0 flex-col [--kanban-column-min:clamp(248px,12.5vw,280px)]"
      data-testid="kanban-board"
    >
      <section className="relative flex h-full min-h-0 flex-col overflow-hidden rounded-lg bg-canvas shadow-sm" aria-labelledby="kanban-board-title">
        <WorkspaceHeader
          title="Kanban"
          titleId="kanban-board-title"
          headingLevel={2}
          summaryLabel="Board summary"
          summary={(
            <WorkspaceHeaderMetric value={boardTaskCount} label={boardTaskLabel} />
          )}
          actions={(
            <>
              <span
                className="absolute -left-[9999px]"
                data-testid="filter-result-count-live"
                aria-live="polite"
              >
                {filterAnnouncement}
              </span>
              {activeFilterLabels.length > 0 ? (
                <span
                  className="flex min-w-0 flex-wrap items-center gap-static-xs"
                  data-testid="active-filter-summary"
                  aria-label="Active filters"
                >
                  {activeFilterLabels.map((label) => (
                    <PTag key={label} compact variant="secondary" data-testid="active-filter-chip" className="max-w-[18rem] truncate">
                      {label}
                    </PTag>
                  ))}
                </span>
              ) : null}
              <PButton
                ref={filterToggleRef}
                data-testid="filter-toggle"
                data-pds-exception="filter-toggle"
                className="max-w-fit"
                variant="secondary"
                compact
                onClick={() => setPanelOpen((open) => !open)}
              >
                Filters
                {hasActiveFilters ? ` (${activeFilterCount})` : ''}
              </PButton>
              {hasActiveFilters ? (
                <PButton
                  type="button"
                  data-testid="filter-clear-active"
                  variant="secondary"
                  compact
                  onClick={clearFilters}
                >
                  Clear filters
                </PButton>
              ) : null}
            </>
          )}
        />

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
          ref={columnStripRef}
          data-testid="kanban-column-strip"
          className="grid flex-1 min-h-0 gap-static-sm overflow-x-auto overflow-y-hidden bg-canvas py-static-md pl-static-md pr-[calc(var(--spacing-static-md)*2+var(--spacing-static-sm))] [scrollbar-gutter:stable]"
          // inline-justified: grid column count is runtime-driven by board status count.
          style={{
            display: 'grid',
            gridTemplateColumns: isMobileLayout
              ? 'minmax(0, 1fr)'
              : `repeat(${board.statuses.length}, minmax(var(--kanban-column-min), 1fr))`,
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
              />
            )
          })}
        </div>
      </section>
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
          className="fixed z-50 min-w-[160px] overflow-hidden rounded-md border border-contrast-low bg-surface py-1 shadow-lg"
          data-testid="context-menu"
          role="menu"
          aria-label="Task actions"
          // inline-justified: menu anchor coordinates are computed from pointer position.
          style={{ position: 'fixed', top: contextMenu.y, left: contextMenu.x }}
        >
          {contextMenuTransitions.map((target) => (
            <div
              key={target}
              data-testid="transition-item"
              data-status={target}
              role="menuitem"
              tabIndex={-1}
              className="block w-full cursor-pointer px-3 py-2 text-left text-sm hover:bg-frosted"
              onKeyDown={handleMenuItemKeyDown}
              onClick={() =>
                void handleTransitionClick(
                  contextMenu.taskId,
                  target,
                  tasks.find((task) => task.id === contextMenu.taskId)?.status ?? contextMenu.taskStatus,
                  contextMenu.taskUpdated,
                )
              }
            >
              Move to {formatStatusLabel(target)}
            </div>
          ))}
          {contextMenuHasArchiveAction ? (
            <div
              {...(contextMenuHasArchiveTransition
                ? { 'data-testid': 'transition-item', 'data-status': 'archived' }
                : {})}
              role="menuitem"
              tabIndex={-1}
              className={`${contextMenuTransitions.length > 0 ? 'border-t border-contrast-low ' : ''}block w-full cursor-pointer px-3 py-2 text-left text-sm text-error hover:bg-frosted`}
              onKeyDown={handleMenuItemKeyDown}
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
          ) : null}
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
