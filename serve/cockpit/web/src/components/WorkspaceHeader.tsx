import type { ReactNode } from 'react'

interface WorkspaceHeaderProps {
  title: string
  titleId: string
  headingLevel?: 1 | 2
  summaryLabel?: string
  summary?: ReactNode
  actions?: ReactNode
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
}: WorkspaceHeaderProps) {
  const Heading = headingLevel === 1 ? 'h1' : 'h2'

  return (
    <header
      data-testid="workspace-header"
      className="grid min-h-16 grid-cols-[minmax(0,1fr)] items-center gap-static-sm border-b border-contrast-low bg-canvas px-static-lg py-static-sm md:grid-cols-[minmax(0,1fr)_auto_auto] md:gap-static-md"
    >
      <div className="flex min-w-0 flex-col">
        <Heading id={titleId} className="m-0 text-xl font-semibold leading-none text-primary">
          {title}
        </Heading>
      </div>
      {summary ? (
        <div
          data-testid="workspace-header-summary"
          className="flex min-w-0 flex-wrap items-center gap-static-sm md:justify-end [&>[data-workspace-header-metric]~[data-workspace-header-metric]]:border-l [&>[data-workspace-header-metric]~[data-workspace-header-metric]]:border-contrast-low [&>[data-workspace-header-metric]~[data-workspace-header-metric]]:pl-static-sm"
          aria-label={summaryLabel}
        >
          {summary}
        </div>
      ) : null}
      {actions ? (
        <div
          data-testid="workspace-header-actions"
          className="flex min-h-[34px] flex-wrap items-center gap-static-xs md:justify-end"
        >
          {actions}
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
        'inline-flex min-h-8 items-baseline gap-1.5 whitespace-nowrap text-xs',
        tone === 'error' ? 'text-error' : 'text-primary',
      ].join(' ')}
    >
      <strong
        className={[
          'text-base font-semibold leading-none',
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
