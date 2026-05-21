import { PIcon, PText } from '@porsche-design-system/components-react'

import { useDRState } from '../hooks/CockpitProvider'

function formatAge(created: string): string {
  const ageMs = Math.max(0, Date.now() - Date.parse(created))
  const ageMinutes = Math.max(1, Math.floor(ageMs / 60_000))
  const unitIndex = Number(ageMinutes >= 60) + Number(ageMinutes >= 24 * 60)
  const divisors = [1, 60, 24 * 60]
  const units = ['m', 'h', 'd']
  const value = Math.floor(ageMinutes / divisors[unitIndex])
  return `${value}${units[unitIndex]} ago`
}

function truncatePreview(value: string): string {
  return value.slice(0, 200)
}

function formatRequestType(value: string): string {
  return value
    .replace(/[-_]/g, ' ')
    .trim()
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function formatDecisionTitle(item: { title: string; task_id: number }): string {
  const title = item.title.trim()
  return title || `Decision needed for task #${item.task_id}`
}

function DecisionsPage() {
  const drState = useDRState()
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
  } else if (drState.items.length === 0) {
    content = (
      <div className="rounded-lg border border-contrast-low bg-canvas p-static-lg text-center">
        <PText data-testid="decisions-empty-state">No decisions are waiting.</PText>
      </div>
    )
  } else {
    content = (
      <div className="flex min-h-0 flex-col gap-static-md overflow-y-auto pr-static-xs" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        {drState.items.map((item) => (
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
            <article data-testid={item.id} className="grid min-h-[112px] grid-cols-[4px_minmax(0,1fr)] lg:grid-cols-[4px_minmax(0,1fr)_minmax(180px,auto)]">
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
                </div>
                <h2 className="m-0 text-lg font-semibold leading-tight text-primary">{formatDecisionTitle(item)}</h2>
                <p className="m-0 max-w-[72ch] pt-static-xs text-sm leading-normal text-primary line-clamp-2">{truncatePreview(item.body_preview)}</p>
              </div>
              <div className="flex items-center justify-between gap-static-sm border-t border-contrast-low bg-surface px-static-md py-static-sm text-sm font-semibold text-primary lg:flex-col lg:items-end lg:justify-center lg:border-l lg:border-t-0 lg:text-right">
                <span className="text-xs font-semibold uppercase leading-tight text-contrast-high">Requested by</span>
                <span className="flex items-center gap-static-xs">
                  <span>{item.agent}</span>
                  <PIcon name="arrow-right" size="small" color="inherit" aria-hidden="true" />
                </span>
              </div>
            </article>
          </div>
        ))}
      </div>
    )
  }

  return (
    <section data-testid="decisions-page" className="flex h-full min-h-0 w-full flex-col gap-static-md bg-canvas" style={{ width: '100%' }}>
      <header className="flex min-w-0 flex-wrap items-end justify-between gap-static-md border-b border-contrast-low pb-static-md">
        <div className="min-w-0">
          <h1 className="m-0 text-3xl font-semibold leading-tight text-primary">Decisions</h1>
        </div>
        <div className="inline-flex min-h-10 items-baseline gap-static-xs rounded-full border border-contrast-low bg-surface px-static-sm py-static-xs">
          <span className="text-2xl font-semibold leading-none text-primary">{drState.items.length}</span>
          <span className="text-sm text-primary">waiting</span>
        </div>
      </header>
      {content}
    </section>
  )
}

export default DecisionsPage
