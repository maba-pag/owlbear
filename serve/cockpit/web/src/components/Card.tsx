import type { Task } from '../hooks/useBoard'
import './Card.css'

type CardSignal = 'dr-pending' | 'blocked' | 'claimed' | 'deps-unmet' | 'ready'

export interface CardProps {
  task: Task
  pendingDRIds?: Set<number>
  selected?: boolean
  onSelect?: (taskId: number) => void
  onContextMenu: (e: React.MouseEvent, task: Task) => void
  onDragStart: (taskId: number, updated: string) => void
  onDragEnd: () => void
}

function resolveSignal(task: Task, pendingDRIds: Set<number>): CardSignal {
  if (pendingDRIds.has(task.id)) {
    return 'dr-pending'
  }
  if (task.blocked) {
    return 'blocked'
  }
  if (task.claimed) {
    return 'claimed'
  }
  if (task.dep_status === 'blocked') {
    return 'deps-unmet'
  }

  return 'ready'
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
  const signal = resolveSignal(task, pendingDRIds)

  function openContextMenu(event: React.KeyboardEvent<HTMLDivElement>) {
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
      event.preventDefault()
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
      role="button"
      tabIndex={0}
      aria-haspopup="menu"
      className="card"
      draggable={true}
      onClick={() => onSelect?.(task.id)}
      onKeyDown={handleKeyDown}
      onDragStart={() => onDragStart(task.id, task.updated)}
      onDragEnd={onDragEnd}
      onContextMenu={(e) => onContextMenu(e, task)}
    >
      <span data-testid="card-title" title={task.title}>
        {task.title}
      </span>
    </div>
  )
}

