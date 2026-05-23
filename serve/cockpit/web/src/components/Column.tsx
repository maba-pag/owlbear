import { useCallback, useEffect, useRef, useState } from 'react'
import { Card } from './Card'
import type { Task } from '../hooks/useBoard'

const PRIORITY_RANK: Record<string, number> = {
  critical: 5,
  needed: 4,
  important: 3,
  'nice-to-have': 2,
  someday: 1,
}

export interface ColumnProps {
  status: string
  tasks: Task[]
  priorities: string[]
  selectedId?: number | null
  pendingDRIds?: Set<number>
  onSelectTask?: (taskId: number) => void
  onContextMenu: (e: React.MouseEvent, task: Task) => void
}

function toDisplayStatus(status: string): string {
  const normalized = status.replace(/-/g, ' ').trim()
  if (!normalized) {
    return ''
  }

  return normalized
    .split(/\s+/)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

function priorityRank(priority: string | null | undefined, priorities: string[]): number {
  if (typeof priority !== 'string') {
    return -1
  }

  const normalized = priority.trim().toLowerCase()
  if (normalized in PRIORITY_RANK) {
    return PRIORITY_RANK[normalized]
  }

  const configuredIndex = priorities.indexOf(priority)
  return configuredIndex >= 0 ? configuredIndex : -1
}

function updatedTimestamp(updated: string | null | undefined): number {
  if (typeof updated !== 'string') {
    return Number.NEGATIVE_INFINITY
  }

  const parsed = Date.parse(updated)
  return Number.isFinite(parsed) ? parsed : Number.NEGATIVE_INFINITY
}

function compareDescending(left: number, right: number): number {
  if (left === right) {
    return 0
  }
  return left > right ? -1 : 1
}

function compareTasksByDefaultOrder(priorities: string[]) {
  return (left: Task, right: Task): number => {
    const priorityDelta = compareDescending(priorityRank(left.priority, priorities), priorityRank(right.priority, priorities))
    if (priorityDelta !== 0) {
      return priorityDelta
    }

    const updatedDelta = compareDescending(updatedTimestamp(left.updated), updatedTimestamp(right.updated))
    if (updatedDelta !== 0) {
      return updatedDelta
    }

    return left.id - right.id
  }
}

export function Column({
  status,
  tasks,
  priorities,
  selectedId,
  pendingDRIds,
  onSelectTask,
  onContextMenu,
}: ColumnProps) {
  const bodyRef = useRef<HTMLDivElement>(null)
  const [canScrollDown, setCanScrollDown] = useState(false)
  const displayStatus = toDisplayStatus(status)

  const sorted = [...tasks].sort(compareTasksByDefaultOrder(priorities))
  const density = sorted.length === 0 ? 'empty' : sorted.length <= 2 ? 'sparse' : 'active'

  const updateScrollCue = useCallback(() => {
    const body = bodyRef.current
    setCanScrollDown(Boolean(body && body.scrollHeight - body.scrollTop - body.clientHeight > 1))
  }, [])

  useEffect(() => {
    const body = bodyRef.current
    if (!body) {
      return
    }

    const syncFocusableState = () => {
      // Keep column-body focusable only while vertical overflow exists.
      if (body.scrollHeight > body.clientHeight) {
        body.setAttribute('tabIndex', '0')
      } else {
        body.removeAttribute('tabIndex')
      }
    }

    syncFocusableState()
    updateScrollCue()

    const observer = new ResizeObserver(() => {
      syncFocusableState()
      updateScrollCue()
    })

    const onWindowResize = () => {
      syncFocusableState()
      updateScrollCue()
    }

    const styleObserver = new MutationObserver(() => {
      syncFocusableState()
      updateScrollCue()
    })

    observer.observe(body)
    window.addEventListener('resize', onWindowResize)
    styleObserver.observe(document.head, { childList: true, subtree: true })

    return () => {
      observer.disconnect()
      window.removeEventListener('resize', onWindowResize)
      styleObserver.disconnect()
    }
  }, [tasks.length, updateScrollCue])

  return (
    <div
      className={[
        'column',
        'relative flex min-w-[var(--kanban-column-min)] flex-col overflow-hidden rounded-md border border-transparent border-t border-t-contrast-low bg-surface',
      ].join(' ')}
      data-column={status}
      data-density={density}
    >
      <header className="flex min-h-12 shrink-0 items-center justify-between px-static-sm text-[0.8125rem] font-semibold capitalize text-primary">
        <span>{displayStatus}</span>
        <span className="min-w-6 rounded-full bg-canvas px-2 py-0.5 text-center text-xs font-semibold text-primary" data-testid="column-count">{tasks.length}</span>
      </header>
      <div
        ref={bodyRef}
        className="column-body relative flex min-h-0 min-w-0 flex-1 flex-col gap-static-sm overflow-x-hidden overflow-y-auto p-static-sm"
        data-testid="column-body"
        onScroll={updateScrollCue}
      >
        {sorted.length === 0 ? (
          <div className="flex min-h-[120px] items-center justify-center px-static-md py-static-lg text-center text-xs font-medium text-contrast-high" data-testid="empty-column">{`No ${displayStatus} tasks`}</div>
        ) : (
          sorted.map((task) => (
            <Card
              key={task.id}
              task={task}
              selected={selectedId === task.id}
              pendingDRIds={pendingDRIds}
              onSelect={onSelectTask}
              onContextMenu={onContextMenu}
            />
          ))
        )}
      </div>
      {canScrollDown ? (
        <div
          aria-hidden="true"
          data-testid="column-scroll-cue"
          className="pointer-events-none absolute inset-x-0 bottom-0 h-8 [background:linear-gradient(to_bottom,transparent,var(--p-color-surface))]"
        />
      ) : null}
    </div>
  )
}
