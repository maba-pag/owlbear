import { useMemo } from 'react'
import { PButton, PIcon, PTag, PText } from '@porsche-design-system/components-react'

import { WorkspaceHeader, WorkspaceHeaderMetric } from '../components/WorkspaceHeader'
import { useDRState } from '../hooks/CockpitProvider'
import { formatAge } from '../utils/decisionBrief'
import { openTaskDetail } from '../utils/openTaskDetail'

function formatKindLabel(value: 'decision' | 'action'): 'Decision' | 'Action' {
  return value === 'decision' ? 'Decision' : 'Action'
}

function formatOptionCount(count: number): string {
  return `${count} option${count === 1 ? '' : 's'}`
}

function formatConfidenceWidth(confidence: number): string {
  if (!Number.isFinite(confidence)) {
    return '0%'
  }

  const clamped = Math.max(0, Math.min(1, confidence))
  return `${Math.round(clamped * 100)}%`
}

function parseCreated(value: string | null | undefined): number {
  if (typeof value !== 'string') {
    return Number.MAX_SAFE_INTEGER
  }

  const timestamp = Date.parse(value)
  return Number.isFinite(timestamp) ? timestamp : Number.MAX_SAFE_INTEGER
}

function comparePendingDecisions(left: { created?: string | null; id: string }, right: { created?: string | null; id: string }): number {
  const createdDelta = parseCreated(left.created) - parseCreated(right.created)
  if (createdDelta !== 0) {
    return createdDelta
  }

  return left.id.localeCompare(right.id)
}

function DecisionsPage() {
  const drState = useDRState()
  const sortedItems = useMemo(
    () => [...drState.items].sort(comparePendingDecisions),
    [drState.items],
  )
  let content

  if (drState.isLoading) {
    content = (
      <div className="rounded-lg border border-contrast-low bg-canvas p-static-md" role="status">
        <PText>Collecting decision requests...</PText>
      </div>
    )
  } else if (drState.error) {
    content = (
      <div className="rounded-lg border border-error bg-error-low p-static-md">
        <PText role="alert">Decision requests are unavailable. {drState.error.message}</PText>
      </div>
    )
  } else if (sortedItems.length === 0) {
    content = (
      <div className="rounded-lg border border-contrast-low bg-canvas p-static-lg text-center">
        <PText data-testid="decisions-empty-state">No pending requests</PText>
      </div>
    )
  } else {
    content = (
      <div className="flex min-h-0 flex-col gap-static-md overflow-y-auto pr-static-xs" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        {sortedItems.map((item) => {
          return (
          <div
            key={item.id}
            data-testid={`dr-item-${item.id}`}
            role="button"
            tabIndex={0}
            aria-label={`Open decision request ${item.id} for task ${item.task_id}`}
            className="group relative overflow-hidden rounded-lg border border-contrast-low bg-canvas text-primary shadow-sm transition-[border-color,box-shadow] duration-sm hover:border-primary hover:shadow-md focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus)]"
            onClick={() => {
              drState.setSelectedDRId(item.id)
            }}
            onKeyDown={(event) => {
              if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault()
                drState.setSelectedDRId(item.id)
              }
            }}
          >
            <article data-testid={item.id} className="grid min-h-[124px] gap-static-sm p-static-md pl-[calc(var(--spacing-static-md)+4px)]">
              <span className="absolute inset-y-0 left-0 w-1 bg-warning" aria-hidden="true" />
              <div className="min-w-0">
                <div data-testid={`dr-primary-meta-${item.id}`} className="mb-static-xs flex min-w-0 flex-wrap items-center gap-static-xs">
                  <PTag compact variant="secondary">
                    {formatKindLabel(item.kind)}
                  </PTag>
                  <PButton
                    type="button"
                    data-testid={`dr-open-task-${item.id}`}
                    variant="secondary"
                    compact
                    onClick={(event) => {
                      event.stopPropagation()
                      openTaskDetail(item.task_id)
                    }}
                    onKeyDown={(event) => {
                      event.stopPropagation()
                    }}
                  >
                    Task #{item.task_id}
                  </PButton>
                  <span className="text-xs font-semibold text-contrast-high">{formatAge(item.created)}</span>
                  <span className="text-xs text-contrast-medium">{item.agent}</span>
                </div>
                <div className="flex min-w-0 flex-wrap items-start justify-between gap-static-sm">
                  <h2 className="m-0 min-w-0 text-base font-semibold leading-tight text-primary">{item.title}</h2>
                  <span className="inline-flex items-center gap-static-xs whitespace-nowrap text-sm font-semibold text-primary">
                    <span>Open resolver</span>
                    <PIcon name="arrow-right" size="small" color="inherit" aria-hidden="true" />
                  </span>
                </div>
                <p className="m-0 mt-static-sm text-sm leading-normal text-primary">{item.summary}</p>
                {item.kind === 'decision' ? (
                  <section data-testid={`dr-options-${item.id}`} className="mt-static-sm grid min-w-0 content-start gap-2 border-t border-contrast-low pt-static-xs">
                    <span className="text-xs font-semibold uppercase leading-tight text-contrast-high">{formatOptionCount(item.options.length)}</span>
                    <div className="grid gap-2">
                      {item.options.map((option) => (
                        <div key={option.option_id} className="grid gap-1">
                          <div className="flex items-center justify-between gap-static-xs text-xs text-contrast-high">
                            <span className="min-w-0 truncate">{option.label}</span>
                            <span>{formatConfidenceWidth(option.confidence)}</span>
                          </div>
                          <div className="h-1.5 rounded-full bg-surface">
                            <span
                              data-testid={`confidence-bar-${option.option_id}`}
                              className="block h-full rounded-full bg-info"
                              style={{ width: formatConfidenceWidth(option.confidence) }}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  </section>
                ) : null}
              </div>
            </article>
          </div>
          )
        })}
      </div>
    )
  }

  return (
    <section data-testid="decisions-page" className="relative flex h-full min-h-0 w-full flex-col overflow-hidden rounded-lg bg-canvas shadow-sm" style={{ width: '100%' }} aria-labelledby="decisions-title">
      <WorkspaceHeader
        title="Decisions"
        titleId="decisions-title"
        summaryLabel="Decision summary"
        summary={<WorkspaceHeaderMetric value={drState.items.length} label="waiting" />}
      />
      <div className="flex min-h-0 flex-1 flex-col gap-static-md overflow-hidden p-static-md">
        {content}
      </div>
    </section>
  )
}

export default DecisionsPage
