import { useDeferredValue, useEffect, useRef, useState, type CSSProperties, type KeyboardEvent as ReactKeyboardEvent } from 'react'
import { PButton, PHeading, PIcon, PInputSearch, PFlyout, PTag } from '@porsche-design-system/components-react'
import type { CompletedChangeRecord, ReceiptCompletedChangeRecord } from '../api/workItems'
import { useCopyToClipboard } from './CopyCommand'
import { useCompletedChange, useCompletedHistory } from '../hooks/useWorkItems'
import WorkspaceViewHeader, { WorkspaceViewCount } from './WorkspaceViewHeader'

type FieldValueEvent = { target?: { value?: unknown }; detail?: { value?: unknown } }

function fieldValue(event: FieldValueEvent): string {
  const value = event.detail?.value ?? event.target?.value
  return typeof value === 'string' ? value : ''
}

function isReceipt(record: CompletedChangeRecord): record is ReceiptCompletedChangeRecord {
  return record.record_kind === 'completion-receipt'
}

function formatCompletedAt(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(date)
}

function pullRequestUrl(repositoryIdentity: string, number: number): string {
  const repositoryUrl = repositoryIdentity.startsWith('http')
    ? repositoryIdentity.replace(/\/$/, '')
    : `https://github.com/${repositoryIdentity}`
  return `${repositoryUrl}/pull/${number}`
}

function PullRequestLink({ record }: { record: ReceiptCompletedChangeRecord }) {
  return (
    <a
      className="font-medium text-primary underline decoration-contrast-low underline-offset-2 hover:decoration-primary"
      href={pullRequestUrl(record.repository_identity, record.pull_request_identity.number)}
      target="_blank"
      rel="noreferrer"
    >
      PR #{record.pull_request_identity.number}
    </a>
  )
}

function CopyValue({ label, value, truncate = false }: { label: string; value: string; truncate?: boolean }) {
  const { copyState, copy } = useCopyToClipboard()
  const displayValue = truncate && value.length > 12 ? `${value.slice(0, 12)}...` : value
  return (
    <button
      type="button"
      className={`inline-flex max-w-full items-start gap-1 border-0 bg-transparent p-0 text-left text-xs focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus ${copyState === 'copied' ? 'text-success' : copyState === 'failed' ? 'text-error' : 'text-contrast-medium hover:text-primary'}`}
      aria-label={`Copy ${label}`}
      title={copyState === 'copied' ? `Copied ${label}` : `Copy ${label}`}
      onClick={() => void copy(value, { success: `Copied ${label}`, failure: `Could not copy ${label}` })}
    >
      <PIcon name="copy" size="inherit" color="inherit" aria-hidden="true" />
      <code className="min-w-0 break-all font-mono text-inherit">{displayValue}</code>
    </button>
  )
}

/**
 * The title is the primary inspect target, matching the active Delivery and Design work lists.
 */
function CompletedRecord({
  record,
  onSelect,
}: {
  record: CompletedChangeRecord
  onSelect: (trigger: HTMLElement) => void
}) {
  return (
    <article
      className={[
        'relative grid gap-x-static-lg gap-y-static-sm border-b border-contrast-low bg-surface py-static-md hover:bg-frosted-soft',
        'md:grid-cols-[minmax(0,20rem)_minmax(0,1fr)] md:items-start',
      ].join(' ')}
      data-testid="completed-change-record"
    >
      <div className="min-w-0">
        <PHeading tag="h3" size="small">
          <button
            type="button"
            className="block w-full text-left font-semibold text-primary after:absolute after:inset-0 after:content-[''] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
            data-completed-history-primary-trigger
            aria-label={`Inspect ${record.title}`}
            onClick={(event) => onSelect(event.currentTarget)}
          >
            {record.title}
          </button>
        </PHeading>
        <p className="mt-1 text-xs text-contrast-medium">{record.change_id}</p>
      </div>
      <div className="relative z-[1] min-w-0">
        <p className="max-w-[70ch] text-sm leading-relaxed">{record.semantic_summary}</p>
        {isReceipt(record) ? (
          <div className="mt-static-sm flex min-w-0 flex-wrap items-center gap-x-static-md gap-y-static-xs text-xs text-contrast-medium">
            <PullRequestLink record={record} />
            <CopyValue label="accepted merge commit" value={record.accepted_merge_commit} truncate />
            <time dateTime={record.completed_at}>{formatCompletedAt(record.completed_at)}</time>
          </div>
        ) : null}
      </div>
    </article>
  )
}

function CompletedDetail({ record, onClose }: { record: CompletedChangeRecord; onClose: () => void }) {
  const outcomePromises = record.outcome_promises ?? []
  return (
    <article
      aria-label="Completion detail"
      className="min-w-0"
      data-testid="completed-change-detail"
    >
      <div className="flex items-start justify-between gap-static-sm">
        <div>
          <h2 className="m-0 text-2xs font-semibold uppercase tracking-[0.08em] text-contrast-high">Completed change</h2>
          <p className="mt-static-xs text-sm text-contrast-medium">What this Change delivered and the evidence retained for its completion.</p>
        </div>
        <PButton type="button" variant="secondary" icon="close" hideLabel compact onClick={onClose}>Close</PButton>
      </div>
      <PHeading tag="h3" size="small" className="mt-static-md">{record.title}</PHeading>
      <section className="mt-static-lg grid gap-static-xs">
        <h4 className="text-2xs font-semibold uppercase tracking-[0.08em] text-contrast-high">Purpose</h4>
        {outcomePromises.length > 0 ? (
          <ul className="m-0 grid gap-static-xs pl-static-md text-sm leading-relaxed">
            {outcomePromises.map((promise) => <li key={promise}>{promise}</li>)}
          </ul>
        ) : <p className="text-sm leading-relaxed text-contrast-medium">Purpose details were not retained in this completion record.</p>}
      </section>
      <section className="mt-static-lg grid gap-static-xs">
        <h4 className="text-2xs font-semibold uppercase tracking-[0.08em] text-contrast-high">Delivered outcomes</h4>
        <ul className="m-0 grid gap-static-xs pl-static-md text-sm leading-relaxed">
          {record.outcome_titles.map((title) => <li key={title}>{title}</li>)}
        </ul>
      </section>
      <PTag compact className="mt-static-md">
        {record.record_kind === 'completion-receipt' ? 'Completion receipt' : 'Legacy package'}
      </PTag>
      {isReceipt(record) ? (
        <section className="mt-static-lg grid gap-static-xs">
          <h4 className="text-2xs font-semibold uppercase tracking-[0.08em] text-contrast-high">Accepted delivery</h4>
          <dl className="grid gap-static-sm text-sm">
            <div>
              <dt className="font-semibold">Pull request</dt>
              <dd><PullRequestLink record={record} /></dd>
            </div>
            <div>
              <dt className="font-semibold">Repository</dt>
              <dd className="break-words text-contrast-medium">{record.repository_identity}</dd>
            </div>
            <div>
              <dt className="font-semibold">Target</dt>
              <dd className="break-words font-mono text-xs text-contrast-medium">{record.accepted_target_ref}</dd>
            </div>
            <div>
              <dt className="font-semibold">Merged</dt>
              <dd className="break-words text-contrast-medium"><time dateTime={record.merged_at}>{formatCompletedAt(record.merged_at)}</time></dd>
            </div>
            <div>
              <dt className="font-semibold">Completed</dt>
              <dd className="break-words text-contrast-medium"><time dateTime={record.completed_at}>{formatCompletedAt(record.completed_at)}</time></dd>
            </div>
          </dl>
        </section>
      ) : (
        <section className="mt-static-lg grid gap-static-xs">
          <h4 className="text-2xs font-semibold uppercase tracking-[0.08em] text-contrast-high">Historical delivery</h4>
          <p className="text-sm leading-relaxed text-contrast-medium">Verified from the retained completion package.</p>
        </section>
      )}
      <details className="mt-static-lg border-t border-contrast-low pt-static-sm">
        <summary className="cursor-pointer text-2xs font-semibold uppercase tracking-[0.08em] text-contrast-high">Evidence</summary>
        <dl className="mt-static-md grid gap-static-sm text-sm">
          <div>
            <dt className="font-semibold">Change</dt>
            <dd className="break-words text-contrast-medium">{record.change_id}</dd>
          </div>
          <div>
            <dt className="font-semibold">Completion</dt>
            <dd><CopyValue label="completion ID" value={record.completion_id} /></dd>
          </div>
          {isReceipt(record) ? (
            <>
              <div>
                <dt className="font-semibold">Finalized Change head</dt>
                <dd><CopyValue label="finalized Change head" value={record.finalized_change_head} /></dd>
              </div>
              <div>
                <dt className="font-semibold">Accepted merge commit</dt>
                <dd><CopyValue label="accepted merge commit" value={record.accepted_merge_commit} /></dd>
              </div>
            </>
          ) : (
            <>
              <div>
                <dt className="font-semibold">Package path</dt>
                <dd className="break-all font-mono text-xs text-contrast-medium">{record.completion_path}</dd>
              </div>
              <div>
                <dt className="font-semibold">Package ID</dt>
                <dd><CopyValue label="package ID" value={record.package_id} /></dd>
              </div>
              <div>
                <dt className="font-semibold">Introducing target commit</dt>
                <dd><CopyValue label="introducing target commit" value={record.introducing_target_commit} /></dd>
              </div>
              <div>
                <dt className="font-semibold">Source target commit</dt>
                <dd><CopyValue label="source target commit" value={record.source_target_commit} /></dd>
              </div>
              <div>
                <dt className="font-semibold">Historical locator</dt>
                <dd className="break-all font-mono text-xs text-contrast-medium">{record.historical_completion_locator}</dd>
              </div>
            </>
          )}
        </dl>
      </details>
    </article>
  )
}

export default function CompletedHistoryWorkspace() {
  const [query, setQuery] = useState('')
  const deferredQuery = useDeferredValue(query.trim())
  const history = useCompletedHistory(deferredQuery)
  const [selected, setSelected] = useState<{ changeId: string; completionId: string } | null>(null)
  const detail = useCompletedChange(selected)
  const lastTrigger = useRef<HTMLElement | null>(null)
  const restoreFocusAfterClose = useRef(false)

  const closeSelected = () => {
    restoreFocusAfterClose.current = true
    setSelected(null)
  }

  useEffect(() => {
    if (selected || !restoreFocusAfterClose.current) return
    let secondFrame: number | null = null
    const firstFrame = window.requestAnimationFrame(() => {
      secondFrame = window.requestAnimationFrame(() => {
        lastTrigger.current?.focus()
        restoreFocusAfterClose.current = false
      })
    })
    return () => {
      window.cancelAnimationFrame(firstFrame)
      if (secondFrame !== null) window.cancelAnimationFrame(secondFrame)
    }
  }, [selected])

  function handleFlyoutKeyDown(event: ReactKeyboardEvent<HTMLDivElement>) {
    if (event.key !== 'Escape') return
    event.preventDefault()
    closeSelected()
  }

  return (
    <section aria-labelledby="completed-history-heading" data-testid="completed-history-workspace">
      <WorkspaceViewHeader
        headingId="completed-history-heading"
        title="Completed changes"
        metaTestId="completed-history-count"
        meta={<WorkspaceViewCount separator value={history.page.records.length} unit={history.page.records.length === 1 ? 'completed change' : 'completed changes'} />}
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
      {!history.isLoading && !history.error && history.page.records.length === 0 ? (
        <section className="mt-static-lg grid min-h-40 place-items-center border border-dashed border-contrast-low bg-surface px-static-lg py-static-xl text-center" data-testid="completed-history-empty-state">
          <div className="grid max-w-[44rem] gap-static-xs">
            <PHeading tag="h3" size="small">No completed changes yet</PHeading>
            <p className="text-sm leading-relaxed text-contrast-medium">Accepted Delivery changes will appear here with their merge evidence.</p>
          </div>
        </section>
      ) : null}

      {history.page.records.length > 0 ? (
        <div className="min-w-0">
          <div className="min-w-0">
            {history.page.records.map((record) => (
              <CompletedRecord
                key={record.completion_id}
                record={record}
                onSelect={(trigger) => {
                  lastTrigger.current = trigger
                  setSelected({ changeId: record.change_id, completionId: record.completion_id })
                }}
              />
            ))}
            {history.page.next_cursor ? (
              <PButton type="button" variant="secondary" className="mt-static-lg" loading={history.isLoading} onClick={() => void history.loadMore()}>
                Load more
              </PButton>
            ) : null}
          </div>
        </div>
      ) : null}

      <PFlyout
        open={selected !== null}
        position="end"
        backdrop="shading"
        background="canvas"
        fullscreen={{ base: true, m: false }}
        style={{ '--p-flyout-width': 'min(56rem, 100vw)' } as CSSProperties}
        aria={{ 'aria-label': 'Completion detail' }}
        onDismiss={closeSelected}
        onKeyDownCapture={handleFlyoutKeyDown}
      >
        <div className="min-w-0 max-w-full p-static-lg">
          {selected ? <>
            {detail.data ? <CompletedDetail record={detail.data} onClose={closeSelected} /> : null}
            {detail.isLoading ? <p role="status">Loading completion detail...</p> : null}
            {detail.error ? <p role="alert">Completion detail is unavailable. {detail.error.message}</p> : null}
          </> : null}
        </div>
      </PFlyout>
    </section>
  )
}
