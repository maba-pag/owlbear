import { useEffect, useRef, useState, type CSSProperties, type KeyboardEvent as ReactKeyboardEvent } from 'react'
import { PButton, PHeading, PIcon, PInputSearch, PFlyout, PModal, PTag } from '@porsche-design-system/components-react'
import { useLocation, useNavigate } from 'react-router'
import { WorkItemApiError, cleanupAbandonedWorkItemChange, completedChangeRecordId, discardAbandonedTargetSyncAndCleanup, type AbandonedChangeRecord, type CompletedChangeRecord, type ReceiptCompletedChangeRecord } from '../api/workItems'
import { useCopyToClipboard } from './CopyCommand'
import { useCompletedChange, useCompletedHistory } from '../hooks/useWorkItems'
import WorkspaceViewHeader, { WorkspaceViewCount } from './WorkspaceViewHeader'

type FieldValueEvent = { target?: { value?: unknown }; detail?: { value?: unknown } }
interface CompletedHistorySelection {
  changeId: string
  completionId: string
}

function parseSelection(pathname: string): CompletedHistorySelection | null {
  const parts = pathname.split('/').filter(Boolean)
  if (parts.length !== 4 || parts[0] !== 'delivery' || parts[1] !== 'history') return null
  try {
    return { changeId: decodeURIComponent(parts[2]), completionId: decodeURIComponent(parts[3]) }
  } catch {
    return null
  }
}

function historyDetailPath(record: CompletedChangeRecord): string {
  return `/delivery/history/${encodeURIComponent(record.change_id)}/${encodeURIComponent(completedChangeRecordId(record))}`
}

function fieldValue(event: FieldValueEvent): string {
  const value = event.detail?.value ?? event.target?.value
  return typeof value === 'string' ? value : ''
}

function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debouncedValue, setDebouncedValue] = useState(value)
  useEffect(() => {
    const timeoutId = window.setTimeout(() => setDebouncedValue(value), delayMs)
    return () => window.clearTimeout(timeoutId)
  }, [delayMs, value])
  return debouncedValue
}

function isReceipt(record: CompletedChangeRecord): record is ReceiptCompletedChangeRecord {
  return record.record_kind === 'completion-receipt'
}

function isAbandoned(record: CompletedChangeRecord): record is AbandonedChangeRecord {
  return record.record_kind === 'abandoned-change'
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
  stale,
  onSelect,
}: {
  record: CompletedChangeRecord
  stale: boolean
  onSelect: (trigger: HTMLElement) => void
}) {
  return (
    <article
      className={[
        'relative grid gap-x-static-lg gap-y-static-sm border-b border-contrast-low py-static-md',
        stale ? 'bg-frosted-soft' : 'bg-surface hover:bg-frosted-soft',
        'md:grid-cols-[minmax(0,20rem)_minmax(0,1fr)] md:items-start',
      ].join(' ')}
      aria-label={stale ? `${record.title}, previous search result` : undefined}
      data-stale={stale ? 'true' : undefined}
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
        ) : isAbandoned(record) ? (
          <div className="mt-static-sm flex min-w-0 flex-wrap items-center gap-x-static-md gap-y-static-xs text-xs text-contrast-medium">
            <PTag compact>Abandoned</PTag>
            <time dateTime={record.abandoned_at}>{formatCompletedAt(record.abandoned_at)}</time>
          </div>
        ) : null}
      </div>
    </article>
  )
}

function CompletedDetail({
  record,
  onClose,
  onCleanup,
}: {
  record: CompletedChangeRecord
  onClose: () => void
  onCleanup: () => Promise<Error | null>
}) {
  const outcomePromises = record.outcome_promises ?? []
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [cleanupError, setCleanupError] = useState<Error | null>(null)
  const [cleanupComplete, setCleanupComplete] = useState(false)
  const abandoned = isAbandoned(record)
  const cleanup = async () => {
    const error = await onCleanup()
    setCleanupError(error)
    if (!error) {
      setCleanupComplete(true)
      setConfirmOpen(false)
    }
  }
  return (
    <article
      aria-label={abandoned ? 'Abandoned change detail' : 'Completion detail'}
      className="min-w-0"
      data-testid="completed-change-detail"
    >
      <div className="flex items-start justify-between gap-static-sm">
        <div>
          <h2 className="m-0 text-2xs font-semibold uppercase tracking-[0.08em] text-contrast-high">{abandoned ? 'Abandoned change' : 'Completed change'}</h2>
          <p className="mt-static-xs text-sm text-contrast-medium">{abandoned ? 'Why this Change ended before completion and what terminal evidence remains.' : 'What this Change delivered and the evidence retained for its completion.'}</p>
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
        {record.record_kind === 'completion-receipt' ? 'Completion receipt' : record.record_kind === 'abandoned-change' ? 'Abandonment record' : 'Legacy package'}
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
      ) : abandoned ? (
        <section className="mt-static-lg grid gap-static-xs">
          <h4 className="text-2xs font-semibold uppercase tracking-[0.08em] text-contrast-high">Abandonment</h4>
          <dl className="grid gap-static-sm text-sm">
            <div><dt className="font-semibold">Prior stage</dt><dd className="text-contrast-medium">{record.prior_stage}</dd></div>
            <div><dt className="font-semibold">Reason</dt><dd className="break-words text-contrast-medium">{record.reason}</dd></div>
            <div><dt className="font-semibold">Abandoned</dt><dd className="text-contrast-medium"><time dateTime={record.abandoned_at}>{formatCompletedAt(record.abandoned_at)}</time></dd></div>
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
          {isAbandoned(record) ? (
            <div>
              <dt className="font-semibold">Abandonment ID</dt>
              <dd><CopyValue label="abandonment ID" value={record.abandonment_id} /></dd>
            </div>
          ) : isReceipt(record) ? (
            <>
              <div>
                <dt className="font-semibold">Completion</dt>
                <dd><CopyValue label="completion ID" value={record.completion_id} /></dd>
              </div>
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
                <dt className="font-semibold">Completion</dt>
                <dd><CopyValue label="completion ID" value={record.completion_id} /></dd>
              </div>
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
      {abandoned && record.cleanup_available ? (
        <>
          {cleanupComplete ? <p className="mt-static-lg border-l-4 border-success bg-surface p-static-sm text-sm" role="status">
            {record.target_sync_conflict
              ? 'Target merge discarded and abandoned Change worktree cleaned up.'
              : 'Abandoned Change worktree cleaned up.'}
          </p> : null}
          <PButton type="button" variant="secondary" className="mt-static-lg" onClick={() => { setCleanupError(null); setCleanupComplete(false); setConfirmOpen(true) }}>
            {record.target_sync_conflict ? 'Discard conflict and clean worktree' : 'Clean abandoned worktree'}
          </PButton>
          {confirmOpen ? (
            <PModal open role="alertdialog" aria-modal="true" dismissButton={false} disableBackdropClick onDismiss={() => setConfirmOpen(false)} aria={{ role: 'alertdialog', 'aria-label': 'Confirm abandoned worktree cleanup' }}>
              <div className="grid w-[min(32rem,calc(100vw-2rem))] gap-static-md text-primary">
                <PHeading tag="h2" size="lg">{record.target_sync_conflict ? 'Discard conflict and clean worktree' : 'Clean abandoned worktree'}</PHeading>
                <p className="text-sm">{record.target_sync_conflict ? 'Delivery will discard the preserved target merge before removing the abandoned worktree.' : 'Delivery will remove the abandoned worktree while retaining the branch and abandonment record.'}</p>
                {cleanupError ? <p className="border-l-4 border-danger bg-surface p-static-sm text-sm" role="alert">{cleanupError.message}</p> : null}
                <div className="flex flex-wrap justify-end gap-static-xs">
                  <PButton type="button" variant="secondary" onClick={() => setConfirmOpen(false)}>Cancel</PButton>
                  <PButton type="button" onClick={() => void cleanup()}>Confirm cleanup</PButton>
                </div>
              </div>
            </PModal>
          ) : null}
        </>
      ) : null}
    </article>
  )
}

export default function CompletedHistoryWorkspace() {
  const location = useLocation()
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const searchQuery = useDebouncedValue(query.trim(), 300)
  const history = useCompletedHistory(searchQuery)
  const canRetryLoadMore = history.canRetryLoadMore
  const isQueryLoading = history.isLoading && !history.isLoadingMore
  const showingStaleResults = (isQueryLoading || (history.error !== null && !canRetryLoadMore)) && history.page.records.length > 0
  const selected = parseSelection(location.pathname)
  const detail = useCompletedChange(selected ? { changeId: selected.changeId, recordId: selected.completionId } : null)
  const lastTrigger = useRef<HTMLElement | null>(null)
  const historyWorkspace = useRef<HTMLElement | null>(null)
  const restoreFocusAfterClose = useRef(false)
  const loadMoreFocusPending = useRef(false)
  const loadMoreQuery = useRef<string | null>(null)
  const previousSelectedKey = useRef<string | null>(selected ? `${selected.changeId}:${selected.completionId}` : null)
  const selectedKey = selected ? `${selected.changeId}:${selected.completionId}` : null

  const closeSelected = () => {
    if (!selected) return
    restoreFocusAfterClose.current = true
    navigate('/delivery/history', { replace: true })
  }

  useEffect(() => {
    if (previousSelectedKey.current && !selectedKey) restoreFocusAfterClose.current = true
    previousSelectedKey.current = selectedKey
  }, [selectedKey])

  useEffect(() => {
    if (!selected) return
    if (detail.error instanceof WorkItemApiError && detail.error.status === 404) {
      restoreFocusAfterClose.current = true
      navigate('/delivery/history', { replace: true })
      return
    }
    if (isQueryLoading || history.error || detail.isLoading) return
    const present = history.page.records.some((record) => record.change_id === selected.changeId
      && completedChangeRecordId(record) === selected.completionId)
    if (present) return
    if (searchQuery) {
      restoreFocusAfterClose.current = true
      navigate('/delivery/history', { replace: true })
      return
    }
    if (detail.data) return
  }, [detail.data, detail.error, detail.isLoading, history.error, history.page.records, isQueryLoading, navigate, searchQuery, selected])

  useEffect(() => {
    if (selected || !restoreFocusAfterClose.current) return
    let secondFrame: number | null = null
    const firstFrame = window.requestAnimationFrame(() => {
      secondFrame = window.requestAnimationFrame(() => {
        const trigger = lastTrigger.current
        if (trigger?.isConnected && !trigger.closest('[data-stale="true"]')) {
          trigger.focus()
        } else {
          historyWorkspace.current?.focus()
        }
        restoreFocusAfterClose.current = false
      })
    })
    return () => {
      window.cancelAnimationFrame(firstFrame)
      if (secondFrame !== null) window.cancelAnimationFrame(secondFrame)
    }
  }, [selectedKey])

  useEffect(() => {
    if (history.isLoadingMore || !loadMoreFocusPending.current) return
    const requestedQuery = loadMoreQuery.current
    loadMoreFocusPending.current = false
    loadMoreQuery.current = null
    if (history.error || requestedQuery !== searchQuery) return
    const loadMoreButton = historyWorkspace.current?.querySelector<HTMLElement>('[data-testid="completed-history-load-more"]')
    ;(loadMoreButton ?? historyWorkspace.current)?.focus()
  }, [history.error, history.isLoadingMore, searchQuery])

  function handleFlyoutKeyDown(event: ReactKeyboardEvent<HTMLDivElement>) {
    if (event.key !== 'Escape') return
    event.preventDefault()
    closeSelected()
  }

  return (
    <section
      ref={historyWorkspace}
      tabIndex={-1}
      aria-labelledby="completed-history-heading"
      data-testid="completed-history-workspace"
    >
      <WorkspaceViewHeader
        headingId="completed-history-heading"
        title="Change history"
        metaTestId="completed-history-count"
        meta={<WorkspaceViewCount separator value={history.page.total_count} unit={history.page.total_count === 1 ? 'change' : 'changes'} />}
        tools={(
          <PInputSearch
            compact
            hideLabel
            className="w-[min(22rem,100%)]"
            name="completed-history-search"
            label="Search Change history"
            value={query}
            clear
            indicator
            onInput={(event) => setQuery(fieldValue(event as FieldValueEvent))}
            onChange={(event) => setQuery(fieldValue(event as FieldValueEvent))}
          />
        )}
      />

      {history.error ? (
        <div className="mt-static-lg flex flex-wrap items-center gap-static-sm border-l-4 border-danger bg-surface p-static-md" role="alert">
          <span className="min-w-0 flex-1">{canRetryLoadMore ? 'Could not load more Change history.' : 'Change history is unavailable.'} {history.error.message}</span>
          <PButton
            type="button"
            variant="secondary"
            loading={history.isLoading}
            onClick={canRetryLoadMore ? history.retryLoadMore : history.retry}
          >
            {canRetryLoadMore ? 'Retry loading more' : 'Retry history'}
          </PButton>
        </div>
      ) : null}
      {history.isLoading && history.page.records.length === 0 ? <p className="mt-static-lg" role="status">Loading Change history...</p> : null}
      {showingStaleResults ? (
        <p
          id="completed-history-stale-status"
          className="mt-static-lg border-l-4 border-info bg-frosted-soft p-static-sm text-sm"
          role="status"
          data-testid="completed-history-stale-status"
        >
          {history.error ? 'Previous results are shown while this search is retried.' : 'Updating Change history results. Previous results are shown until the search finishes.'}
        </p>
      ) : null}
      {!history.isLoading && !history.error && history.page.records.length === 0 ? (
        <section className="mt-static-lg grid min-h-40 place-items-center border border-dashed border-contrast-low bg-surface px-static-lg py-static-xl text-center" data-testid="completed-history-empty-state">
          <div className="grid max-w-[44rem] gap-static-xs">
            <PHeading tag="h3" size="small">
              {searchQuery ? `No changes match "${searchQuery}"` : 'No changes in history yet'}
            </PHeading>
            <p className="text-sm leading-relaxed text-contrast-medium">
              {searchQuery ? 'Try a different search or clear the current search.' : 'Completed and abandoned Changes will appear here with their retained evidence.'}
            </p>
            {searchQuery ? (
              <PButton type="button" variant="secondary" className="mx-auto" onClick={() => setQuery('')}>
                Clear search
              </PButton>
            ) : null}
          </div>
        </section>
      ) : null}

      {history.page.records.length > 0 ? (
        <div
          className="min-w-0"
          aria-busy={history.isLoading}
          aria-describedby={showingStaleResults ? 'completed-history-stale-status' : undefined}
          data-testid="completed-history-results"
        >
          <div className="min-w-0">
            {history.page.records.map((record) => (
              <CompletedRecord
                key={completedChangeRecordId(record)}
                record={record}
                stale={showingStaleResults}
                onSelect={(trigger) => {
                  lastTrigger.current = trigger
                  navigate(historyDetailPath(record))
                }}
              />
            ))}
            {history.page.next_cursor ? (
              <PButton
                type="button"
                variant="secondary"
                className="mt-static-lg"
                data-testid="completed-history-load-more"
                loading={history.isLoading}
                disabled={history.error !== null || history.isLoading}
                onClick={() => {
                  if (history.isLoading) return
                  loadMoreFocusPending.current = true
                  loadMoreQuery.current = searchQuery
                  void history.loadMore()
                }}
              >
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
            {detail.data ? <CompletedDetail record={detail.data} onClose={closeSelected} onCleanup={async () => {
              if (detail.data?.record_kind !== 'abandoned-change') return null
              try {
                if (detail.data.target_sync_conflict) {
                  await discardAbandonedTargetSyncAndCleanup(detail.data.change_id)
                } else {
                  await cleanupAbandonedWorkItemChange(detail.data.change_id)
                }
                history.retry()
                return null
              } catch (caught: unknown) {
                return caught instanceof Error ? caught : new Error('Abandoned worktree cleanup failed')
              }
            }} /> : null}
            {detail.isLoading ? <p role="status">Loading completion detail...</p> : null}
            {detail.error ? (
              <div className="flex flex-wrap items-center gap-static-sm border-l-4 border-danger bg-surface p-static-md" role="alert">
                <span className="min-w-0 flex-1">Completion detail is unavailable. {detail.error.message}</span>
                <PButton type="button" variant="secondary" loading={detail.isLoading} disabled={detail.isLoading} onClick={detail.retry}>Retry completion detail</PButton>
              </div>
            ) : null}
          </> : null}
        </div>
      </PFlyout>
    </section>
  )
}
