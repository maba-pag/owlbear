import { useState } from 'react'
import type { Task } from '../hooks/useBoard'
import { computeSignal } from '../utils/computeSignal'
import './Card.css'

const TAG_PREVIEW_LIMIT = 3

function formatUpdatedAge(updated: string): string {
  const updatedAt = Date.parse(updated)
  if (!Number.isFinite(updatedAt)) {
    return 'Updated recently'
  }

  const ageMs = Math.max(0, Date.now() - updatedAt)
  const ageMinutes = Math.max(1, Math.floor(ageMs / 60_000))

  if (ageMinutes < 60) {
    return `${ageMinutes}m ago`
  }

  if (ageMinutes < 24 * 60) {
    return `${Math.floor(ageMinutes / 60)}h ago`
  }

  return `${Math.floor(ageMinutes / (24 * 60))}d ago`
}

export interface CardProps {
  task: Task
  pendingDRIds?: Set<number>
  selected?: boolean
  onSelect?: (taskId: number) => void
  onContextMenu: (e: React.MouseEvent, task: Task) => void
  onDragStart: (taskId: number, updated: string) => void
  onDragEnd: () => void
}

export function Card({
  task,
  pendingDRIds = new Set<number>(),
  selected = false,
  onSelect,
  onContextMenu,
  onDragStart,
  onDragEnd,
}: CardProps) {
  const signal = computeSignal(task, pendingDRIds)
  const [dragging, setDragging] = useState(false)
  const previewTags = task.tags.slice(0, TAG_PREVIEW_LIMIT)
  const overflowTags = task.tags.length - previewTags.length
  const updatedAge = formatUpdatedAge(task.updated)

  function openContextMenu(event: React.KeyboardEvent<HTMLDivElement>) {
    event.preventDefault()
    const rect = event.currentTarget.getBoundingClientRect()
    const syntheticEvent = {
      preventDefault: () => {},
      clientX: rect.left,
      clientY: rect.bottom,
    } as unknown as React.MouseEvent
    onContextMenu(syntheticEvent, task)
  }

  function handleKeyDown(event: React.KeyboardEvent<HTMLDivElement>) {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      if (onSelect) {
        onSelect(task.id)
      } else if (event.key === 'Enter') {
        openContextMenu(event)
      }
      return
    }

    if (event.key === 'F10' && event.shiftKey) {
      openContextMenu(event)
    }
  }

  return (
    <div
      data-testid="task-card"
      data-id={task.id}
      data-priority={task.priority}
      data-selected={selected ? 'true' : 'false'}
      data-signal={signal}
      data-dragging={dragging ? 'true' : 'false'}
      role="button"
      tabIndex={0}
      aria-haspopup="menu"
      className="card"
      draggable={true}
      onClick={() => onSelect?.(task.id)}
      onKeyDown={handleKeyDown}
      onDragStart={() => {
        setDragging(true)
        onDragStart(task.id, task.updated)
      }}
      onDragEnd={() => {
        setDragging(false)
        onDragEnd()
      }}
      onContextMenu={(e) => onContextMenu(e, task)}
    >
      <div className="card-main">
        <div className="card-header-row">
          <span data-testid="card-id" className="card-chip card-id">
            #{task.id}
          </span>
          <span data-testid="card-priority" className="card-chip card-priority">
            {task.priority}
          </span>
          <span data-testid="card-updated" className="card-chip card-updated" aria-label={`Updated ${updatedAge}`}>
            {updatedAge}
          </span>
        </div>

        <span data-testid="card-title" className="card-title" title={task.title}>
          {task.title}
        </span>

        {task.tags.length > 0 ? (
          <div className="card-tags-row">
            <span data-testid="card-tags" className="card-tags" aria-label={`Tags: ${previewTags.join(', ')}`}>
              {previewTags.join(', ')}
            </span>
            {overflowTags > 0 ? (
              <span data-testid="card-tag-overflow" className="card-chip card-tag-overflow" aria-label={`${overflowTags} more tags`}>
                +{overflowTags}
              </span>
            ) : null}
          </div>
        ) : null}

        <div className="card-cues-row" aria-label="Task state cues">
          {task.blocked ? (
            <span data-testid="card-blocked-cue" className="card-chip card-cue card-cue-blocked">
              Blocked
            </span>
          ) : null}
          {task.claimed ? (
            <span data-testid="card-claimed-cue" className="card-chip card-cue card-cue-claimed">
              Claimed
            </span>
          ) : null}
          {task.dep_status === 'blocked' ? (
            <span data-testid="card-deps-unmet-cue" className="card-chip card-cue card-cue-deps">
              Dependencies blocked
            </span>
          ) : null}
          {signal === 'dr-pending' ? (
            <span data-testid="card-dr-pending-cue" className="card-chip card-cue card-cue-dr">
              Decision pending
            </span>
          ) : null}
        </div>
      </div>
    </div>
  )
}

