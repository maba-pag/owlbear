import { PIcon, type IconName } from '@porsche-design-system/components-react'
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

function isRedundantDecisionTag(tag: string, signal: CardSignal): boolean {
  return signal === 'dr-pending' && tag.trim().toLowerCase() === 'active-decision'
}

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
  const visibleTags = task.tags.filter((tag) => !isRedundantDecisionTag(tag, signal))
  const previewTags = visibleTags.slice(0, TAG_PREVIEW_LIMIT)
  const overflowTags = visibleTags.length - previewTags.length
  const updatedAge = formatUpdatedAge(task.updated)
  const signalLabel = signal.replace('-', ' ')
  const displaySignalLabel = SIGNAL_LABEL[signal] ?? signalLabel
  const signalIconName = SIGNAL_ICON_NAME[signal]
  const hasVisibleSignal = signal !== 'ready' && signal !== 'unknown'
  const secondaryCues = [
    { key: 'blocked', show: task.blocked && signal !== 'blocked', testId: 'card-blocked-cue', label: 'Blocked', className: 'text-error' },
    { key: 'claimed', show: task.claimed && signal !== 'claimed', testId: 'card-claimed-cue', label: 'Claimed', className: 'text-contrast-high' },
    { key: 'deps-unmet', show: task.dep_status === 'blocked' && signal !== 'deps-unmet', testId: 'card-deps-unmet-cue', label: 'Dependencies blocked', className: 'text-contrast-high' },
    { key: 'dr-pending', show: pendingDRIds.has(task.id) && signal !== 'dr-pending', testId: 'card-dr-pending-cue', label: 'Decision pending', className: 'text-contrast-high' },
  ]
  const visibleSecondaryCues = secondaryCues.filter((cue) => cue.show)
  const hasSecondaryCues = visibleSecondaryCues.length > 0

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
    signal === 'ready' && task.priority === 'needed' ? 'border-l-warning' :
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
            <span data-testid="card-id" className="font-mono text-[0.72rem] font-medium leading-normal text-contrast-high">
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

        {hasSecondaryCues ? (
          <div className="mt-auto flex min-w-0 flex-wrap items-center gap-x-static-xs gap-y-1 border-t border-contrast-low pt-static-xs">
            {visibleSecondaryCues.map((cue) => (
              <span key={cue.key} data-testid={cue.testId} className={["text-[0.72rem] font-semibold leading-normal", cue.className].join(' ')}>
                {cue.label}
              </span>
            ))}
          </div>
        ) : null}

        {visibleTags.length > 0 ? (
          <div className={[hasSecondaryCues ? '' : 'mt-auto', 'flex min-w-0 flex-wrap items-center gap-x-static-xs gap-y-1'].join(' ')}>
            <span data-testid="card-tags" className="flex min-w-0 max-w-full flex-wrap items-center gap-x-1.5 gap-y-1 text-[0.72rem] leading-normal text-contrast-high" aria-label={`Tags: ${previewTags.join(', ')}`}>
              {previewTags.map((tag, index) => (
                <span
                  key={`${tag}-${index}`}
                  className="inline-flex max-w-full items-center gap-x-1.5 truncate"
                >
                  {index > 0 ? <span aria-hidden="true" className="shrink-0 text-contrast-medium">/</span> : null}
                  <span data-testid="card-tag" className="truncate">{tag}</span>
                </span>
              ))}
            </span>
            {overflowTags > 0 ? (
              <span
                data-testid="card-tag-overflow"
                className="text-[0.72rem] leading-normal text-contrast-high"
                aria-label={`${overflowTags} more tags`}
              >
                +{overflowTags} tags
              </span>
            ) : null}
          </div>
        ) : null}
      </div>
    </motion.div>
  )
}
