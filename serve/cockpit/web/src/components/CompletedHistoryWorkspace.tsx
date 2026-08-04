import { useDeferredValue, useState } from 'react'
import { PButton, PHeading, PInputSearch, PTag } from '@porsche-design-system/components-react'
import type { CompletedChangeRecord } from '../api/workItems'
import { useCompletedChange, useCompletedHistory } from '../hooks/useWorkItems'

type FieldValueEvent = { target?: { value?: unknown }; detail?: { value?: unknown } }

function fieldValue(event: FieldValueEvent): string {
  const value = event.detail?.value ?? event.target?.value
  return typeof value === 'string' ? value : ''
}

function CompletedRecord({ record, onSelect }: { record: CompletedChangeRecord; onSelect: () => void }) {
  return (
    <article className="grid gap-static-sm border-b border-contrast-low py-static-md" data-testid="completed-change-record">
      <div className="flex min-w-0 flex-wrap items-start justify-between gap-static-sm">
        <div className="min-w-0">
          <PHeading tag="h3" size="medium">{record.title}</PHeading>
          <p className="mt-static-xs text-sm text-contrast-medium">{record.change_id}</p>
        </div>
        <PTag compact>Completed</PTag>
      </div>
      <p className="text-sm leading-relaxed">{record.semantic_summary}</p>
      <div>
        <PButton type="button" variant="secondary" compact onClick={onSelect}>Inspect</PButton>
      </div>
    </article>
  )
}

function CompletedDetail({ record, onClose }: { record: CompletedChangeRecord; onClose: () => void }) {
  return (
    <aside className="min-w-0 border-t border-contrast-low pt-static-lg lg:border-l lg:border-t-0 lg:pl-static-lg lg:pt-0" data-testid="completed-change-detail">
      <div className="flex items-start justify-between gap-static-sm">
        <PHeading tag="h2" size="large">Completion detail</PHeading>
        <PButton type="button" variant="secondary" icon="close" hideLabel onClick={onClose}>Close</PButton>
      </div>
      <PHeading tag="h3" size="medium" className="mt-static-lg">{record.title}</PHeading>
      <p className="mt-static-sm leading-relaxed">{record.semantic_summary}</p>
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
      <div className="grid gap-static-md border-b border-contrast-low pb-static-lg md:grid-cols-[minmax(0,1fr)_minmax(16rem,24rem)] md:items-end">
        <div>
          <PHeading tag="h2" size="large" id="completed-history-heading">Completed history</PHeading>
          <p className="mt-static-xs text-sm text-contrast-medium" aria-live="polite">
            {history.page.records.length} completed {history.page.records.length === 1 ? 'change' : 'changes'}
          </p>
        </div>
        <PInputSearch
          name="completed-history-search"
          label="Search completed work"
          value={query}
          clear
          indicator
          loading={history.isLoading}
          onInput={(event) => setQuery(fieldValue(event as FieldValueEvent))}
          onChange={(event) => setQuery(fieldValue(event as FieldValueEvent))}
        />
      </div>

      {history.error ? (
        <div className="mt-static-lg flex flex-wrap items-center gap-static-sm border-l-4 border-danger bg-surface p-static-md" role="alert">
          <span className="min-w-0 flex-1">Completed history is unavailable. {history.error.message}</span>
          <PButton type="button" variant="secondary" onClick={history.retry}>Retry history</PButton>
        </div>
      ) : null}
      {history.isLoading && history.page.records.length === 0 ? <p className="mt-static-lg" role="status">Loading completed history...</p> : null}
      {!history.isLoading && !history.error && history.page.records.length === 0 ? <p className="mt-static-lg">No completed changes found.</p> : null}

      {history.page.records.length > 0 ? (
        <div className="grid min-w-0 gap-static-lg lg:grid-cols-[minmax(0,1fr)_minmax(20rem,0.42fr)]">
          <div>
            {history.page.records.map((record) => (
              <CompletedRecord
                key={record.completion_id}
                record={record}
                onSelect={() => setSelected({ changeId: record.change_id, completionId: record.completion_id })}
              />
            ))}
            {history.page.next_cursor ? (
              <PButton type="button" variant="secondary" className="mt-static-lg" loading={history.isLoading} onClick={() => void history.loadMore()}>
                Load more
              </PButton>
            ) : null}
          </div>
          {detail.data ? <CompletedDetail record={detail.data} onClose={() => setSelected(null)} /> : null}
          {detail.isLoading ? <p role="status">Loading completion detail...</p> : null}
          {detail.error ? <p role="alert">Completion detail is unavailable. {detail.error.message}</p> : null}
        </div>
      ) : null}
    </section>
  )
}
