import type { ReactNode } from 'react'
import type { WorkItemNeed } from '../api/workItems'
import { workItemStatusClassName, type WorkItemStatusTone } from './workItemPresentation'

interface StatusChipProps {
  label: string
  tone: WorkItemStatusTone
  testId?: string
}

export function StatusChip({ label, tone, testId }: StatusChipProps) {
  return (
    <span
      className={`inline-flex items-center rounded-sm border px-static-xs py-1 text-xs font-semibold leading-none ${workItemStatusClassName(tone)}`}
      data-status-tone={tone}
      data-testid={testId}
    >
      {label}
    </span>
  )
}

interface WorkRowProps {
  children: ReactNode
  selected?: boolean
  needs?: WorkItemNeed
  ariaLabel?: string
  dataWorkItem?: string
  className?: string
}

export function WorkRow({ children, selected = false, needs = 'none', ariaLabel, dataWorkItem, className = '' }: WorkRowProps) {
  const attentionClass = needs === 'you' ? 'border-l-4 border-l-error' : 'border-l-4 border-l-contrast-low'
  return (
    <article
      className={[
        'relative min-w-0 rounded-lg border-y border-r border-contrast-low bg-surface',
        attentionClass,
        selected ? 'bg-frosted-soft' : 'hover:bg-frosted-soft',
        className,
      ].join(' ')}
      aria-label={ariaLabel}
      data-work-item={dataWorkItem}
    >
      {children}
    </article>
  )
}

type SectionCardElement = 'section' | 'article' | 'div' | 'details'
type SectionCardTone = 'neutral' | 'warning' | 'danger' | 'info'

interface SectionCardProps {
  children: ReactNode
  as?: SectionCardElement
  tone?: SectionCardTone
  muted?: boolean
  interactive?: boolean
  ariaLabel?: string
  dataTestId?: string
  dataStale?: boolean
  className?: string
}

const TONE_CLASS_NAMES: Record<SectionCardTone, string> = {
  neutral: 'border-contrast-low bg-surface',
  warning: 'border-warning bg-warning-low',
  danger: 'border-danger bg-surface',
  info: 'border-info bg-info-low',
}

export function SectionCard({
  children,
  as = 'section',
  tone = 'neutral',
  muted = false,
  interactive = false,
  ariaLabel,
  dataTestId,
  dataStale,
  className = '',
}: SectionCardProps) {
  const Element = as
  return (
    <Element
      className={[
        'min-w-0 rounded-lg border',
        TONE_CLASS_NAMES[tone],
        muted ? 'bg-frosted-soft' : '',
        interactive ? 'hover:bg-frosted-soft' : '',
        className,
      ].join(' ')}
      aria-label={ariaLabel}
      data-stale={dataStale ? 'true' : undefined}
      data-testid={dataTestId}
    >
      {children}
    </Element>
  )
}
