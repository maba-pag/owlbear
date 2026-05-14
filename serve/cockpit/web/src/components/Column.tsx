import { useEffect, useRef, useState } from 'react'
import { Card } from './Card'
import type { Task } from '../hooks/useBoard'
import './Column.css'

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

  const handleCardDragStart = (taskId: number, updated: string) => {
    onDragStart(status, taskId, updated)
  }

  useEffect(() => {
    const body = bodyRef.current
    if (!body) {
      return
    }

    // Use an explicit attribute so Playwright can assert keyboard focusability via getAttribute().
    body.setAttribute('tabIndex', '0')
  }, [tasks.length])

  return (
    <div
      className="column"
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
        setIsDragOver(false)
        if (!isValidDragTarget) {
          return
        }
        e.preventDefault()
        onDrop(status)
      }}
    >
      <header>
        <span>{displayStatus}</span>
        <span className="column-count" data-testid="column-count">{tasks.length}</span>
      </header>
      <div ref={bodyRef} className="column-body" data-testid="column-body">
        {sorted.length === 0 ? (
          <div className="column-empty" data-testid="empty-column">{`No ${displayStatus} tasks`}</div>
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
