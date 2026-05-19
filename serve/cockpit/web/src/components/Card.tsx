import { useState } from 'react'
import { PIcon, PTag } from '@porsche-design-system/components-react'
import { motion } from 'framer-motion'
import type { Task } from '../hooks/useBoard'
import { computeSignal } from '../utils/computeSignal'

function statusToVariant(status: string): 'primary' | 'success' | 'warning' | 'error' | 'secondary' {
  switch (status) {
    case 'done': return 'success'
    case 'in-progress': return 'warning'
    case 'blocked': return 'error'
    case 'todo': return 'primary'
    default: return 'secondary'
  }
}

function priorityToVariant(priority: string): 'error' | 'warning' | 'primary' | 'secondary' {
  switch (priority) {
    case 'critical': return 'error'
    case 'needed':
    case 'important': return 'warning'
    case 'nice-to-have': return 'primary'
    default: return 'secondary'
  }
}

const SIGNAL_ICON_NAME: Record<string, string> = {
  blocked: 'lock',
  'dr-pending': 'information',
  claimed: 'user',
  'deps-unmet': 'link',
}

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
  const signalLabel = signal.replace('-', ' ')

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

  // Compute border-left signal color
  const signalBorderClass =
    signal === 'blocked' ? 'border-l-error' :
    signal === 'dr-pending' ? 'border-l-warning' :
    signal === 'claimed' ? 'border-l-[var(--custom-signal-claimed)]' :
    signal === 'deps-unmet' ? 'border-l-contrast-medium' :
    signal === 'ready' && task.priority === 'critical' ? 'border-l-error' :
    signal === 'ready' && (task.priority === 'needed' || task.priority === 'important') ? 'border-l-warning' :
    'border-l-contrast-medium'

  return (
    <motion.div
        layout
        layoutId={`card-${task.id}`}
        initial={{ opacity: 0, scale: 0.96 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.96 }}
        transition={{ layout: { duration: 0.25, ease: 'easeOut' }, opacity: { duration: 0.15 } }}
        data-testid="task-card"
        data-id={task.id}
        data-priority={task.priority}
        data-selected={selected ? 'true' : 'false'}
        data-signal={signal}
        data-dragging={dragging ? 'true' : 'false'}
        role="button"
        tabIndex={0}
        aria-haspopup="menu"
        aria-label={
          `Task #${task.id}: ${task.title}. ${task.priority} priority. ${signalLabel}. Updated ${updatedAge}.`
        }
        className={[
          'card',
          'flex min-h-[108px] items-start overflow-hidden rounded-md border border-contrast-low border-l-4 bg-canvas',
          'px-static-sm pb-static-sm pt-2.5 text-xs leading-normal',
          'cursor-pointer shadow-md',
          'transition-[box-shadow,background-color,border-color] duration-sm',
          'hover:-translate-y-0.5 hover:bg-frosted hover:shadow-lg',
          'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus)]',
          signalBorderClass,
          selected ? 'inset-ring-1 inset-ring-success shadow-sm bg-success-frosted' : '',
          dragging ? 'opacity-50' : '',
        ].join(' ')}
        draggable={true}
        onClick={() => onSelect?.(task.id)}
        onKeyDown={handleKeyDown}
        onDragStart={() => {
          onSelect?.(task.id)
          setDragging(true)
          onDragStart(task.id, task.updated)
        }}
        onDragEnd={() => {
          setDragging(false)
          onDragEnd()
        }}
        onContextMenu={(e) => onContextMenu(e, task)}
    >
      <div className="flex min-h-[88px] w-full min-w-0 flex-col gap-1.5">
          {/* Top row: id + signal icon + updated */}
          <div className="flex min-w-0 flex-wrap items-center justify-between gap-static-xs" aria-hidden="true">
            <div className="flex items-center gap-static-xs">
              <span data-testid="card-id" className="rounded-full border border-contrast-low px-2 py-px font-mono text-[0.72rem] leading-normal text-contrast-high">
                #{task.id}
              </span>
              {signal !== 'ready' && SIGNAL_ICON_NAME[signal] ? (
                <PIcon
                  size="xs"
                  aria-label={signal}
                  name={SIGNAL_ICON_NAME[signal] as never}
                  ref={(el) => { if (el) { el.setAttribute('size', 'xs'); el.setAttribute('aria-label', signal) } }}
                />
              ) : null}
            </div>
            <span data-testid="card-updated" className="text-[0.72rem] leading-normal text-contrast-medium" aria-label={`Updated ${updatedAge}`}>
              {updatedAge}
            </span>
          </div>

          <span data-testid="card-title" className="line-clamp-2 text-sm font-semibold leading-tight" title={task.title}>
            {task.title}
          </span>

          {/* Status + Priority chips */}
          <div className="flex min-w-0 flex-wrap items-center gap-static-xs">
            <PTag
              compact
              data-testid="card-status"
              variant={statusToVariant(task.status)}
              ref={(el) => { if (el) { el.setAttribute('compact', ''); el.setAttribute('variant', statusToVariant(task.status)); el.setAttribute('data-testid', 'card-status') } }}
            >
              {task.status}
            </PTag>
            <PTag
              compact
              data-testid="card-priority"
              variant={priorityToVariant(task.priority)}
              ref={(el) => { if (el) { el.setAttribute('compact', ''); el.setAttribute('variant', priorityToVariant(task.priority)); el.setAttribute('data-testid', 'card-priority') } }}
            >
              {task.priority}
            </PTag>
          </div>

          {/* Signal cue spans (conditionally rendered) */}
          {task.blocked ? (
            <span data-testid="card-blocked-cue" className="text-[0.72rem] font-medium text-error">Blocked</span>
          ) : null}
          {task.claimed ? (
            <span data-testid="card-claimed-cue" className="text-[0.72rem] font-medium text-[var(--custom-signal-claimed)]">Claimed</span>
          ) : null}
          {task.dep_status === 'blocked' ? (
            <span data-testid="card-deps-unmet-cue" className="text-[0.72rem] font-medium text-contrast-medium">Dependencies blocked</span>
          ) : null}
          {pendingDRIds.has(task.id) ? (
            <span data-testid="card-dr-pending-cue" className="text-[0.72rem] font-medium text-warning">Decision pending</span>
          ) : null}

          {/* Tags */}
          {task.tags.length > 0 ? (
            <div className="mt-auto flex min-w-0 flex-wrap items-center gap-static-xs opacity-80">
              <span data-testid="card-tags" className="max-w-full overflow-hidden text-ellipsis whitespace-nowrap text-contrast-medium" aria-label={`Tags: ${previewTags.join(', ')}`}>
                {previewTags.map((tag) => (
                  <PTag
                    key={tag}
                    compact
                    variant="secondary"
                    ref={(element) => {
                      if (element) {
                        element.setAttribute('compact', '')
                        element.setAttribute('variant', 'secondary')
                      }
                    }}
                  >
                    {tag}
                  </PTag>
                ))}
              </span>
              {overflowTags > 0 ? (
                <span
                  data-testid="card-tag-overflow"
                  className="rounded-full border border-contrast-low px-2 py-px text-[0.72rem] leading-normal text-contrast-high"
                  aria-label={`${overflowTags} more tags`}
                >
                  +{overflowTags}
                </span>
              ) : null}
            </div>
          ) : null}
      </div>
    </motion.div>
  )
}
