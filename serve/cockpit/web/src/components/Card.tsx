import type { Task } from '../hooks/useBoard'

const PRIORITY_COLORS: Record<string, string> = {
  critical: '#e00000',
  needed: '#ff8000',
  important: '#ffcc00',
  'nice-to-have': '#0066cc',
  someday: '#888888',
}

export interface CardProps {
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
