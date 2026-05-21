import { PIcon, PTag, type IconName } from '@porsche-design-system/components-react'
import { motion } from 'framer-motion'
import type { Task } from '../hooks/useBoard'
import { computeSignal, type CardSignal } from '../utils/computeSignal'

const SIGNAL_ICON_NAME: Partial<Record<CardSignal, IconName>> = {
  blocked: 'lock',
  'dr-pending': 'information',
  claimed: 'user',
  'deps-unmet': 'unlinked',
}

const SIGNAL_LABEL: Record<string, string> = {
  ready: 'Ready',
  blocked: 'Blocked',
  'dr-pending': 'Decision',
  claimed: 'Claimed',
  'deps-unmet': 'Dependencies',
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
}

export function Card({
  task,
  pendingDRIds = new Set<number>(),
  selected = false,
  onSelect,
  onContextMenu,
}: CardProps) {
  const signal = computeSignal(task, pendingDRIds)
  const previewTags = task.tags.slice(0, TAG_PREVIEW_LIMIT)
  const overflowTags = task.tags.length - previewTags.length
  const updatedAge = formatUpdatedAge(task.updated)
  const signalLabel = signal.replace('-', ' ')
  const displaySignalLabel = SIGNAL_LABEL[signal] ?? signalLabel
  const signalIconName = SIGNAL_ICON_NAME[signal]
  const hasVisibleSignal = signal !== 'ready' && signal !== 'unknown'
  const hasIntegrationCues =
    task.blocked || task.claimed || task.dep_status === 'blocked' || pendingDRIds.has(task.id)

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
      initial={false}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.96 }}
      transition={{ layout: { duration: 0.25, ease: 'easeOut' }, opacity: { duration: 0.15 } }}
      data-testid="task-card"
      data-id={task.id}
      data-priority={task.priority}
      data-selected={selected ? 'true' : 'false'}
      data-signal={signal}
      role="button"
      tabIndex={0}
      aria-haspopup="menu"
      aria-label={
        `Task #${task.id}: ${task.title}. ${task.priority} priority. ${signalLabel}. Updated ${updatedAge}.`
      }
      className={[
        'card',
        'relative flex min-h-[116px] items-start overflow-hidden rounded-lg border border-transparent border-l-[6px] bg-canvas',
        'px-static-sm pb-static-sm pt-static-sm text-xs leading-normal',
        'cursor-pointer shadow-sm',
        'transition-[box-shadow,background-color,border-color,transform] duration-sm',
        'hover:-translate-y-0.5 hover:bg-frosted hover:shadow-md',
        'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus)]',
        signalBorderClass,
        selected ? 'border-primary bg-frosted inset-ring-2 inset-ring-primary shadow-lg' : '',
      ].join(' ')}
      draggable={false}
      onClick={() => onSelect?.(task.id)}
      onKeyDown={handleKeyDown}
      onContextMenu={(e) => onContextMenu(e, task)}
    >
      <div className="flex min-h-[92px] w-full min-w-0 flex-col gap-static-sm">
        <div className="flex min-w-0 items-start justify-between gap-static-xs" aria-hidden="true">
          <div className="flex min-w-0 flex-wrap items-center gap-static-xs">
            <span data-testid="card-id" className="rounded-full border border-contrast-low bg-surface px-2 py-px font-mono text-[0.72rem] leading-normal text-primary">
              #{task.id}
            </span>
            {hasVisibleSignal ? (
              <span data-testid="card-signal" className="inline-flex min-h-6 items-center gap-1 rounded-full bg-surface px-2 py-px text-[0.72rem] font-semibold leading-normal text-primary">
                {signalIconName ? (
                  <PIcon
                    size="xs"
                    aria-label={signal}
                    name={signalIconName}
                    ref={(el) => { if (el) { el.setAttribute('size', 'xs'); el.setAttribute('aria-label', signal) } }}
                  />
                ) : null}
                {displaySignalLabel}
              </span>
            ) : null}
          </div>
          <span data-testid="card-updated" className="shrink-0 text-[0.72rem] leading-normal text-primary" aria-label={`Updated ${updatedAge}`}>
            {updatedAge}
          </span>
        </div>

        <span
          data-testid="card-title"
          className="line-clamp-2 text-[0.95rem] font-semibold leading-tight text-primary"
          title={task.title}
        >
          {task.title}
        </span>

        {hasIntegrationCues ? (
          <div className="mt-auto flex min-w-0 flex-wrap items-center gap-static-xs border-t border-contrast-low pt-static-xs">
            {task.blocked ? (
              <span data-testid="card-blocked-cue" className="rounded-full bg-surface px-2 py-px text-[0.72rem] font-medium text-error">Blocked</span>
            ) : null}
            {task.claimed ? (
              <span data-testid="card-claimed-cue" className="rounded-full bg-surface px-2 py-px text-[0.72rem] font-medium text-primary">Claimed</span>
            ) : null}
            {task.dep_status === 'blocked' ? (
              <span data-testid="card-deps-unmet-cue" className="rounded-full bg-surface px-2 py-px text-[0.72rem] font-medium text-primary">Dependencies blocked</span>
            ) : null}
            {pendingDRIds.has(task.id) ? (
              <span data-testid="card-dr-pending-cue" className="rounded-full bg-surface px-2 py-px text-[0.72rem] font-medium text-primary">Decision pending</span>
            ) : null}
          </div>
        ) : null}

        {task.tags.length > 0 ? (
          <div className={[hasIntegrationCues ? '' : 'mt-auto', 'flex min-w-0 flex-wrap items-center gap-static-xs'].join(' ')}>
            <span data-testid="card-tags" className="max-w-full overflow-hidden text-ellipsis whitespace-nowrap text-primary" aria-label={`Tags: ${previewTags.join(', ')}`}>
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
