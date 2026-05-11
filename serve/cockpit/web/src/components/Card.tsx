import type { Task } from '../hooks/useBoard'

const PRIORITY_COLORS: Record<string, string> = {
  critical: 'var(--pds-theme-light-notification-error)',
  needed: 'var(--pds-theme-light-notification-warning)',
  important: 'var(--pds-theme-light-notification-info)',
  'nice-to-have': 'var(--pds-theme-light-notification-info)',
  someday: 'var(--pds-theme-light-contrast-medium)',
}

export interface CardProps {
  task: Task
  selected?: boolean
  onSelect?: (taskId: number) => void
  onContextMenu: (e: React.MouseEvent, task: Task) => void
  onDragStart: (taskId: number, updated: string) => void
  onDragEnd: () => void
}

export function Card({ task, selected = false, onSelect, onContextMenu, onDragStart, onDragEnd }: CardProps) {
  return (
    <div
      data-testid="task-card"
      data-id={task.id}
      data-priority={task.priority}
      data-selected={selected ? 'true' : 'false'}
      draggable={true}
      onClick={() => onSelect?.(task.id)}
      onDragStart={() => onDragStart(task.id, task.updated)}
      onDragEnd={onDragEnd}
      onContextMenu={(e) => onContextMenu(e, task)}
      style={{
        border: selected ? '1px solid var(--pds-theme-light-notification-success)' : '1px solid transparent',
        borderLeft: `4px solid ${PRIORITY_COLORS[task.priority] ?? 'var(--pds-theme-light-contrast-medium)'}`,
        backgroundColor: selected ? 'var(--pds-theme-light-notification-success-soft)' : 'transparent',
        minHeight: '48px',
        maxHeight: '56px',
        display: 'flex',
        alignItems: 'center',
        padding: '0 8px',
        boxSizing: 'border-box',
        overflow: 'hidden',
        cursor: 'pointer',
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
