import { useMemo } from 'react'
import { PIcon, PText } from '@porsche-design-system/components-react'

import { WorkspaceHeader, WorkspaceHeaderMetric } from '../components/WorkspaceHeader'
import { useDRState } from '../hooks/CockpitProvider'
import { formatAge, formatRequestType, getDecisionBrief } from '../utils/decisionBrief'

function parseCreated(value: string): number {
  const timestamp = Date.parse(value)
  return Number.isFinite(timestamp) ? timestamp : Number.MAX_SAFE_INTEGER
}

function DecisionsPage() {
  const drState = useDRState()
  const sortedItems = useMemo(
    () => [...drState.items].sort((left, right) => parseCreated(left.created) - parseCreated(right.created)),
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
            className="group overflow-hidden rounded-lg border border-contrast-low bg-canvas text-primary shadow-sm transition-[border-color,box-shadow] duration-sm hover:border-primary hover:shadow-md focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-focus)]"
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
            <article data-testid={item.id} className="grid min-h-[132px] grid-cols-[4px_minmax(0,1fr)] lg:grid-cols-[4px_minmax(0,1fr)_minmax(220px,auto)]">
              <span className="bg-warning" aria-hidden="true" />
              <div className="min-w-0 p-static-md">
                <div className="mb-static-xs flex min-w-0 flex-wrap items-center gap-static-xs">
                  <span className="rounded-full border border-contrast-low bg-surface px-static-xs py-1 text-xs font-semibold text-primary">
                    {formatRequestType(item.request_type)}
                  </span>
                  <span className="rounded-full border border-contrast-low bg-surface px-static-xs py-1 text-xs font-semibold text-primary">
                    Task #{item.task_id}
                  </span>
                  <span className="text-xs font-semibold text-primary">{formatAge(item.created)}</span>
                  <span className="text-xs font-semibold text-primary">{item.agent}</span>
                </div>
                <h2 className="m-0 text-base font-semibold leading-tight text-primary">{brief.title}</h2>
                <div className="mt-static-sm grid gap-static-sm xl:grid-cols-[minmax(0,1fr)_minmax(280px,0.58fr)]">
                  <section data-testid={`dr-context-${item.id}`} className="grid min-w-0 gap-1 border-t border-contrast-low pt-static-xs">
                    <span className="text-xs font-semibold uppercase leading-tight text-contrast-high">Context</span>
                    <p className="m-0 text-sm leading-normal text-primary line-clamp-3">{brief.context}</p>
                  </section>
                  <section data-testid={`dr-options-${item.id}`} className="grid min-w-0 gap-1 border-t border-contrast-low pt-static-xs">
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
                </div>
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
              <div className="col-span-full grid min-w-0 content-center gap-static-xs border-t border-contrast-low bg-surface px-static-md py-static-sm text-sm text-primary sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center lg:col-auto lg:flex lg:flex-col lg:items-start lg:justify-center lg:border-l lg:border-t-0">
                <div className="grid min-w-0 gap-1">
                  <span className="text-xs font-semibold uppercase leading-tight text-contrast-high">Decision</span>
                  <span className="text-sm leading-normal text-primary">Choose the response in the resolver.</span>
                </div>
                <span className="inline-flex items-center gap-static-xs whitespace-nowrap text-sm font-semibold text-primary">
                  <span>Open resolver</span>
                  <PIcon name="arrow-right" size="small" color="inherit" aria-hidden="true" />
                </span>
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
