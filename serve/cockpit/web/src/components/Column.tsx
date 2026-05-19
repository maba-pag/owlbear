import { useEffect, useRef, useState } from 'react'
import { Card } from './Card'
import type { Task } from '../hooks/useBoard'

export interface ColumnProps {
  status: string
  tasks: Task[]
  priorities: string[]
  selectedId?: number | null
  pendingDRIds?: Set<number>
  onSelectTask?: (taskId: number) => void
  onContextMenu: (e: React.MouseEvent, task: Task) => void
  onDragStart: (status: string, taskId: number, updated: string) => void
  onDrop: (targetStatus: string) => void
  onDragEnd: () => void
  isValidDragTarget: boolean
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

export function Column({
  status,
  tasks,
  priorities,
  selectedId,
  pendingDRIds,
  onSelectTask,
  onContextMenu,
  onDragStart,
  onDrop,
  onDragEnd,
  isValidDragTarget,
}: ColumnProps) {
  const [isDragOver, setIsDragOver] = useState(false)
  const bodyRef = useRef<HTMLDivElement>(null)
  const displayStatus = toDisplayStatus(status)

  const sorted = [...tasks].sort((a, b) => priorities.indexOf(b.priority) - priorities.indexOf(a.priority))
  const density = sorted.length === 0 ? 'empty' : sorted.length <= 2 ? 'sparse' : 'active'

  const handleCardDragStart = (taskId: number, updated: string) => {
    onDragStart(status, taskId, updated)
  }

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

    const observer = new ResizeObserver(() => {
      syncFocusableState()
    })

    const onWindowResize = () => {
      syncFocusableState()
    }

    const styleObserver = new MutationObserver(() => {
      syncFocusableState()
    })

    observer.observe(body)
    window.addEventListener('resize', onWindowResize)
    styleObserver.observe(document.head, { childList: true, subtree: true })

    return () => {
      observer.disconnect()
      window.removeEventListener('resize', onWindowResize)
      styleObserver.disconnect()
    }
  }, [tasks.length])

  return (
    <div
      className={[
        'column',
        'flex min-w-[var(--kanban-column-min)] flex-col overflow-hidden rounded-md border border-contrast-low bg-surface',
        isDragOver && isValidDragTarget ? 'bg-[var(--p-color-frosted)]' : '',
      ].join(' ')}
      data-column={status}
      data-density={density}
      data-drag-over={isDragOver && isValidDragTarget ? 'true' : undefined}
      onDragOver={(e) => {
        if (isValidDragTarget) {
          e.preventDefault()
          setIsDragOver(true)
        }
      }}
      onDragLeave={() => setIsDragOver(false)}
      onDrop={(e) => {
        setIsDragOver(false)
        if (!isValidDragTarget) {
          return
        }
        e.preventDefault()
        onDrop(status)
      }}
    >
      <header className="flex min-h-11 shrink-0 items-center justify-between border-b border-contrast-low px-static-sm text-[0.8125rem] font-semibold capitalize">
        <span>{displayStatus}</span>
        <span className="rounded-full border border-contrast-low bg-[var(--p-color-frosted-soft)] px-2 py-0.5 text-xs font-semibold" data-testid="column-count">{tasks.length}</span>
      </header>
      <div
        ref={bodyRef}
        className={[
          'column-body relative flex min-h-0 min-w-0 flex-1 flex-col gap-static-sm overflow-y-auto p-static-sm',
          density === 'empty' || density === 'sparse' ? 'bg-[var(--p-color-frosted-soft)]' : 'bg-canvas',
        ].join(' ')}
        data-testid="column-body"
      >
        {sorted.length === 0 ? (
          <div className="flex min-h-[120px] items-center justify-center rounded-md border border-dashed border-contrast-low bg-surface p-static-md text-center text-xs text-contrast-high opacity-70" data-testid="empty-column">{`No ${displayStatus} tasks`}</div>
        ) : (
          sorted.map((task) => (
            <Card
              key={task.id}
              task={task}
              selected={selectedId === task.id}
              pendingDRIds={pendingDRIds}
              onSelect={onSelectTask}
              onContextMenu={onContextMenu}
              onDragStart={handleCardDragStart}
              onDragEnd={onDragEnd}
            />
          ))
        )}
      </div>
    </div>
  )
}
