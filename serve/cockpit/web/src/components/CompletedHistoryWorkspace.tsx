import { useDeferredValue, useState } from 'react'
import { PButton, PHeading, PInputSearch, PTag } from '@porsche-design-system/components-react'
import type { CompletedChangeRecord } from '../api/workItems'
import { useCompletedChange, useCompletedHistory } from '../hooks/useWorkItems'
import WorkspaceViewHeader, { WorkspaceViewCount } from './WorkspaceViewHeader'

type FieldValueEvent = { target?: { value?: unknown }; detail?: { value?: unknown } }

function fieldValue(event: FieldValueEvent): string {
  const value = event.detail?.value ?? event.target?.value
  return typeof value === 'string' ? value : ''
}

/**
 * `wide` fills the view width with a record grid — identity, summary, actions — so the list rule
 * lines up with the view-header rule. `split` stacks the same parts beside an open detail.
 */
function CompletedRecord({
  record,
  layout,
  onSelect,
}: {
  record: CompletedChangeRecord
  layout: 'wide' | 'split'
  onSelect: () => void
}) {
  return (
    <article
      className={[
        'grid gap-x-static-lg gap-y-static-sm border-b border-contrast-low py-static-md',
        layout === 'wide' ? 'md:grid-cols-[minmax(0,20rem)_minmax(0,1fr)_auto] md:items-start' : '',
      ].join(' ')}
      data-testid="completed-change-record"
    >
      <div className="min-w-0">
        <PHeading tag="h3" size="small">{record.title}</PHeading>
        <p className="mt-1 text-xs text-contrast-medium">{record.change_id}</p>
      </div>
      <p className="min-w-0 max-w-[70ch] text-sm leading-relaxed">{record.semantic_summary}</p>
      <div className={['flex shrink-0 items-center gap-static-sm', layout === 'wide' ? 'md:justify-end' : ''].join(' ')}>
        <PTag compact>Completed</PTag>
        <PButton type="button" variant="secondary" compact onClick={onSelect}>Inspect</PButton>
      </div>
    </article>
  )
}

function CompletedDetail({ record, onClose }: { record: CompletedChangeRecord; onClose: () => void }) {
  return (
    <aside
      aria-label="Completion detail"
      className="min-w-0 border-t border-contrast-low pt-static-lg lg:border-l lg:border-t-0 lg:pl-static-lg lg:pt-0"
      data-testid="completed-change-detail"
    >
      <div className="flex items-start justify-between gap-static-sm">
        <h2 className="m-0 text-2xs font-semibold uppercase tracking-[0.08em] text-contrast-high">Completion detail</h2>
        <PButton type="button" variant="secondary" icon="close" hideLabel compact onClick={onClose}>Close</PButton>
      </div>
      <PHeading tag="h3" size="small" className="mt-static-md">{record.title}</PHeading>
      <p className="mt-static-sm text-sm leading-relaxed">{record.semantic_summary}</p>
      <dl className="mt-static-lg grid gap-static-sm text-sm">
        <div>
          <dt className="font-semibold">Change</dt>
          <dd className="break-words text-contrast-medium">{record.change_id}</dd>
        </div>
        <div>
          <dt className="font-semibold">Completion</dt>
          <dd className="break-all font-mono text-xs text-contrast-medium">{record.completion_id}</dd>
        </div>
      </dl>
    </aside>
  )
}

export default function CompletedHistoryWorkspace() {
  const [query, setQuery] = useState('')
  const deferredQuery = useDeferredValue(query.trim())
  const history = useCompletedHistory(deferredQuery)
  const [selected, setSelected] = useState<{ changeId: string; completionId: string } | null>(null)
  const detail = useCompletedChange(selected)

  return (
    <section aria-labelledby="completed-history-heading" data-testid="completed-history-workspace">
      <WorkspaceViewHeader
        headingId="completed-history-heading"
        title="Completed changes"
        metaTestId="completed-history-count"
        meta={<WorkspaceViewCount value={history.page.records.length} unit={history.page.records.length === 1 ? 'completed change' : 'completed changes'} />}
        tools={(
          <PInputSearch
            compact
            hideLabel
            className="w-[min(22rem,100%)]"
            name="completed-history-search"
            label="Search completed work"
            value={query}
            clear
            indicator
            loading={history.isLoading}
            onInput={(event) => setQuery(fieldValue(event as FieldValueEvent))}
            onChange={(event) => setQuery(fieldValue(event as FieldValueEvent))}
          />
        )}
      />

      {history.error ? (
        <div className="mt-static-lg flex flex-wrap items-center gap-static-sm border-l-4 border-danger bg-surface p-static-md" role="alert">
          <span className="min-w-0 flex-1">Completed history is unavailable. {history.error.message}</span>
          <PButton type="button" variant="secondary" onClick={history.retry}>Retry history</PButton>
        </div>
      ) : null}
      {history.isLoading && history.page.records.length === 0 ? <p className="mt-static-lg" role="status">Loading completed history...</p> : null}
      {!history.isLoading && !history.error && history.page.records.length === 0 ? <p className="mt-static-lg">No completed changes found.</p> : null}

      {history.page.records.length > 0 ? (
        <div className={[
          'grid min-w-0 gap-x-static-lg gap-y-static-md',
          selected ? 'lg:grid-cols-[minmax(0,1fr)_minmax(20rem,0.42fr)]' : '',
        ].join(' ')}>
          <div className="min-w-0">
            {history.page.records.map((record) => (
              <CompletedRecord
                key={record.completion_id}
                record={record}
                layout={selected ? 'split' : 'wide'}
                onSelect={() => setSelected({ changeId: record.change_id, completionId: record.completion_id })}
              />
            ))}
            {history.page.next_cursor ? (
              <PButton type="button" variant="secondary" className="mt-static-lg" loading={history.isLoading} onClick={() => void history.loadMore()}>
                Load more
              </PButton>
            ) : null}
          </div>
          {selected ? (
            <div className="min-w-0">
              {detail.data ? <CompletedDetail record={detail.data} onClose={() => setSelected(null)} /> : null}
              {detail.isLoading ? <p role="status">Loading completion detail...</p> : null}
              {detail.error ? <p role="alert">Completion detail is unavailable. {detail.error.message}</p> : null}
            </div>
          ) : null}
        </div>
      ) : null}
    </section>
  )
}
