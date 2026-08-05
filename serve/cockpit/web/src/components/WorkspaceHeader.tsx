import type { ReactNode } from 'react'

interface WorkspaceHeaderProps {
  title: string
  titleId: string
  headingLevel?: 1 | 2
  summaryLabel?: string
  summary?: ReactNode
  actions?: ReactNode
  /** Suppress the header rule when the page renders its own adjacent chrome below it. */
  flush?: boolean
}

interface WorkspaceHeaderMetricProps {
  value: ReactNode
  label: ReactNode
  tone?: 'neutral' | 'error'
}

interface WorkspaceHeaderPillProps {
  children: ReactNode
  tone?: 'neutral' | 'error' | 'info'
}

export function WorkspaceHeader({
  title,
  titleId,
  headingLevel = 1,
  summaryLabel,
  summary,
  actions,
  flush = false,
}: WorkspaceHeaderProps) {
  const Heading = headingLevel === 1 ? 'h1' : 'h2'

  return (
    <header
      data-testid="workspace-header"
      className={[
        'sticky top-0 z-10 flex min-h-16 shrink-0 flex-wrap items-center justify-between gap-x-static-xl gap-y-static-xs bg-canvas px-static-lg py-static-sm',
        flush ? '' : 'border-b border-contrast-low',
      ].join(' ')}
    >
      <Heading id={titleId} className="m-0 min-w-0 text-xl font-semibold leading-none text-primary">
        {title}
      </Heading>
      {summary || actions ? (
        <div className="flex min-w-0 flex-wrap items-center gap-x-static-lg gap-y-static-xs">
          {summary ? (
            <div
              data-testid="workspace-header-summary"
              className="flex min-w-0 flex-wrap items-baseline gap-x-static-md gap-y-static-xs [&>[data-workspace-header-metric]~[data-workspace-header-metric]]:border-l [&>[data-workspace-header-metric]~[data-workspace-header-metric]]:border-contrast-low [&>[data-workspace-header-metric]~[data-workspace-header-metric]]:pl-static-md"
              aria-label={summaryLabel}
            >
              {summary}
            </div>
          ) : null}
          {actions ? (
            <div
              data-testid="workspace-header-actions"
              className="flex min-h-[34px] flex-wrap items-center gap-static-xs"
            >
              {actions}
            </div>
          ) : null}
        </div>
      ) : null}
    </header>
  )
}

export function WorkspaceHeaderMetric({ value, label, tone = 'neutral' }: WorkspaceHeaderMetricProps) {
  return (
    <span
      data-testid="workspace-header-metric"
      data-workspace-header-metric=""
      className={[
        'inline-flex items-baseline gap-1.5 whitespace-nowrap text-xs',
        tone === 'error' ? 'text-error' : 'text-primary',
      ].join(' ')}
    >
      <strong
        className={[
          'text-lg font-semibold leading-none',
          tone === 'error' ? 'text-error' : 'text-primary',
        ].join(' ')}
      >
        {value}
      </strong>
      <span>{label}</span>
    </span>
  )
}

export function WorkspaceHeaderPill({ children, tone = 'neutral' }: WorkspaceHeaderPillProps) {
  return (
    <span
      className={[
        'inline-flex min-h-8 items-center whitespace-nowrap rounded-full border px-static-xs py-1 text-xs font-semibold leading-none',
        tone === 'error'
          ? 'border-error bg-error-low text-error'
          : tone === 'info'
            ? 'border-info bg-info-low text-primary'
            : 'border-contrast-low bg-surface text-primary',
      ].join(' ')}
    >
      {children}
    </span>
  )
}
