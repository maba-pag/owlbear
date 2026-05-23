import { useMemo } from 'react'
import { PIcon, PTag, PText } from '@porsche-design-system/components-react'

import { WorkspaceHeader, WorkspaceHeaderMetric } from '../components/WorkspaceHeader'
import { useDRState } from '../hooks/CockpitProvider'
import { formatAge, formatRequestType, getDecisionBrief } from '../utils/decisionBrief'

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
        <PText data-testid="decisions-empty-state">No decisions are waiting.</PText>
      </div>
    )
  } else {
    content = (
      <div className="flex min-h-0 flex-col gap-static-md overflow-y-auto pr-static-xs" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        {sortedItems.map((item) => {
          const brief = getDecisionBrief(item)
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
                <div className="mb-static-xs flex min-w-0 flex-wrap items-center gap-static-xs">
                  <PTag compact variant="secondary">
                    {formatRequestType(item.request_type)}
                  </PTag>
                  <PTag compact variant="secondary">
                    Task #{item.task_id}
                  </PTag>
                  <span className="text-xs font-semibold text-contrast-high">{formatAge(item.created)}</span>
                  <span className="text-xs font-semibold text-contrast-high">{item.agent}</span>
                </div>
                <div className="flex min-w-0 flex-wrap items-start justify-between gap-static-sm">
                  <h2 className="m-0 min-w-0 text-base font-semibold leading-tight text-primary">{brief.title}</h2>
                  <span className="inline-flex items-center gap-static-xs whitespace-nowrap text-sm font-semibold text-primary">
                    <span>Open resolver</span>
                    <PIcon name="arrow-right" size="small" color="inherit" aria-hidden="true" />
                  </span>
                </div>
                {brief.isStructured ? (
                  <div className="mt-static-sm grid gap-static-sm xl:grid-cols-[minmax(0,1fr)_minmax(280px,0.58fr)]">
                    {brief.context ? (
                      <section data-testid={`dr-context-${item.id}`} className="grid min-w-0 content-start gap-1 border-t border-contrast-low pt-static-xs">
                        <span className="text-xs font-semibold uppercase leading-tight text-contrast-high">Context</span>
                        <p className="m-0 text-sm leading-normal text-primary line-clamp-3">{brief.context}</p>
                      </section>
                    ) : null}
                    {brief.options.length > 0 || brief.request ? (
                      <section data-testid={`dr-options-${item.id}`} className="grid min-w-0 content-start gap-1 border-t border-contrast-low pt-static-xs">
                        <span className="text-xs font-semibold uppercase leading-tight text-contrast-high">{brief.options.length > 0 ? 'Options' : 'Request'}</span>
                        {brief.options.length > 0 ? (
                          <ol className="m-0 grid list-none gap-1 p-0 text-sm leading-normal text-primary">
                            {brief.options.map((option, optionIndex) => (
                              <li key={option} className="grid min-w-0 grid-cols-[1.5rem_minmax(0,1fr)] gap-static-xs">
                                <span className="inline-flex size-5 items-center justify-center rounded-full border border-contrast-low bg-surface text-xs font-semibold leading-none text-primary">
                                  {optionIndex + 1}
                                </span>
                                <span className="min-w-0 line-clamp-1">{option}</span>
                              </li>
                            ))}
                          </ol>
                        ) : (
                          <p className="m-0 text-sm leading-normal text-primary line-clamp-2">{brief.request}</p>
                        )}
                      </section>
                    ) : null}
                  </div>
                ) : (
                  <div className="mt-static-sm grid gap-static-sm xl:grid-cols-[minmax(0,1fr)_minmax(280px,0.58fr)]">
                    <section data-testid={`dr-summary-${item.id}`} className="grid min-w-0 content-start gap-1 border-t border-contrast-low pt-static-xs">
                      <span className="text-xs font-semibold uppercase leading-tight text-contrast-high">Summary</span>
                      <p className="m-0 text-sm leading-normal text-primary line-clamp-3">{brief.summary}</p>
                    </section>
                    {brief.options.length > 0 ? (
                      <section data-testid={`dr-options-${item.id}`} className="grid min-w-0 content-start gap-1 border-t border-contrast-low pt-static-xs">
                        <span className="text-xs font-semibold uppercase leading-tight text-contrast-high">Options</span>
                        <ol className="m-0 grid list-none gap-1 p-0 text-sm leading-normal text-primary">
                          {brief.options.map((option, optionIndex) => (
                            <li key={option} className="grid min-w-0 grid-cols-[1.5rem_minmax(0,1fr)] gap-static-xs">
                              <span className="inline-flex size-5 items-center justify-center rounded-full border border-contrast-low bg-surface text-xs font-semibold leading-none text-primary">
                                {optionIndex + 1}
                              </span>
                              <span className="min-w-0 line-clamp-1">{option}</span>
                            </li>
                          ))}
                        </ol>
                      </section>
                    ) : null}
                  </div>
                )}
                {brief.recommendation || brief.consequence ? (
                  <div className="mt-static-sm grid gap-static-sm lg:grid-cols-2">
                    {brief.recommendation ? (
                      <section data-testid={`dr-recommendation-${item.id}`} className="grid gap-1 border-l-2 border-info pl-static-xs">
                        <span className="text-xs font-semibold uppercase leading-tight text-contrast-high">Recommendation</span>
                        <p className="m-0 text-sm leading-normal text-primary line-clamp-2">{brief.recommendation}</p>
                      </section>
                    ) : null}
                    {brief.consequence ? (
                      <section data-testid={`dr-consequence-${item.id}`} className="grid gap-1 border-l-2 border-contrast-low pl-static-xs">
                        <span className="text-xs font-semibold uppercase leading-tight text-contrast-high">Impact</span>
                        <p className="m-0 text-sm leading-normal text-primary line-clamp-2">{brief.consequence}</p>
                      </section>
                    ) : null}
                  </div>
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
