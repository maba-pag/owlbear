import { useDeferredValue, useEffect, useRef, useState, type CSSProperties, type KeyboardEvent as ReactKeyboardEvent } from 'react'
import { PButton, PButtonPure, PFlyout, PHeading, PIcon, PPopover, PSelect, PSelectOption, PTagDismissible } from '@porsche-design-system/components-react'
import { useLocation, useNavigate } from 'react-router'
import type { ChangeGroupView, DeliveryHealthResponse, PortfolioChangeLifecycleStatus, PortfolioChangeStage, WorkItemNeed } from '../api/workItems'
import CompletedHistoryWorkspace from '../components/CompletedHistoryWorkspace'
import DesignWorkDetail from '../components/DesignWorkDetail'
import DesignWorkSection from '../components/DesignWorkSection'
import { designWorkTitle } from '../components/designWorkPresentation'
import PortfolioOperatingSummary, { PortfolioHeaderSummary } from '../components/PortfolioOperatingSummary'
import { WorkspaceHeader } from '../components/WorkspaceHeader'
import { WorkspaceViewCount } from '../components/WorkspaceViewHeader'
import WorkItemDetail from '../components/WorkItemDetail'
import WorkPortfolioTable from '../components/WorkPortfolioTable'
import {
  useAcceptanceReconciliation,
  useDesignWorkDetail,
  useWorkItemDetail,
  useWorkPortfolio,
  type WorkItemIdentity,
} from '../hooks/useWorkItems'

type SelectValueEvent = { target?: { value?: unknown }; detail?: { value?: unknown } }
type FocusDestination = 'trigger' | 'current-view' | 'history-view'

const CHANGE_STAGE_LABELS: Record<PortfolioChangeStage, string> = {
  design: 'Design',
  building: 'Building',
  finalized: 'Finalized',
  'awaiting-merge': 'Awaiting merge',
  'publication-attention': 'Publication attention',
  'acceptance-attention': 'Acceptance attention',
  deferred: 'Deferred',
  abandoned: 'Abandoned',
  completed: 'Completed',
}

function isUnadmittedDesign(status: PortfolioChangeLifecycleStatus): boolean {
  return status.admission === 'unadmitted' && status.stage === 'design'
}

function isUnavailableAdmitted(status: PortfolioChangeLifecycleStatus): boolean {
  return status.admission === 'admitted' && !status.actionable_runtime
}

function selectedValue(event: SelectValueEvent): string {
  const value = event.detail?.value ?? event.target?.value
  return typeof value === 'string' ? value : ''
}

function PortfolioViewSwitch({ workspace, onChange }: { workspace: 'current' | 'history'; onChange: (workspace: 'current' | 'history') => void }) {
  return (
    <nav
      className="flex shrink-0 items-stretch gap-static-lg bg-canvas pb-static-xs"
      aria-label="Delivery portfolio views"
      data-testid="work-view-selector"
    >
      {([
        ['current', 'Current delivery'],
        ['history', 'Change history'],
      ] as const).map(([value, label]) => (
        <button
          key={value}
          type="button"
          className={[
            'border-b-2 pb-static-xs pt-1 text-xs focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus',
            workspace === value ? 'border-primary font-semibold text-primary' : 'border-transparent font-medium text-contrast-medium hover:text-primary',
          ].join(' ')}
          data-workspace-view={value}
          aria-pressed={workspace === value}
          onClick={() => onChange(value)}
        >
          {label}
        </button>
      ))}
    </nav>
  )
}

interface FilterProps {
  changes: Array<{ id: string; title: string }>
  changeFilter: string
  needsFilter: WorkItemNeed | ''
  open: boolean
  onToggle: () => void
  onDismiss: () => void
  onChangeFilter: (value: string) => void
  onNeedsFilter: (value: WorkItemNeed | '') => void
}

/** Collapsed trigger plus active-filter chips; the expanded surface renders separately below. */
function PortfolioFilterTools(props: FilterProps) {
  const activeCount = (props.changeFilter ? 1 : 0) + (props.needsFilter ? 1 : 0)
  const triggerRef = useRef<HTMLButtonElement | null>(null)
  return (
    <>
      {props.changeFilter ? (
        <PTagDismissible
          compact
          label={`Change: ${props.changeFilter}`}
          data-testid="work-filter-chip-change"
          aria={{ 'aria-label': `Remove change filter ${props.changeFilter}` }}
          onClick={() => props.onChangeFilter('')}
        />
      ) : null}
      {props.needsFilter ? (
        <PTagDismissible
          compact
          label={`Attention: ${props.needsFilter === 'you' ? 'Needs you' : props.needsFilter === 'dependency' ? 'Waiting on dependency' : 'No intervention'}`}
          data-testid="work-filter-chip-needs"
          aria={{ 'aria-label': 'Remove Attention filter' }}
          onClick={() => props.onNeedsFilter('')}
        />
      ) : null}
      <PPopover
        compact
        open={props.open}
        direction="bottom"
        aria={{ 'aria-label': 'Delivery filters' }}
        className="max-w-full"
        onDismiss={() => {
          props.onDismiss()
          window.requestAnimationFrame(() => triggerRef.current?.focus())
        }}
      >
        <button
          type="button"
          slot="button"
          ref={triggerRef}
          className="inline-flex items-center gap-1 border-0 bg-transparent p-0 text-xs font-medium text-primary focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus hover:text-primary"
          data-testid="work-filters-toggle"
          aria-expanded={props.open}
          aria-controls="work-filters-panel"
          onClick={props.onToggle}
        >
          <PIcon name="filter" size="inherit" aria-hidden="true" />
          {activeCount > 0 ? `Filter (${activeCount})` : 'Filter'}
        </button>
        {props.open ? <PortfolioFilterPanel {...props} /> : null}
      </PPopover>
    </>
  )
}

function PortfolioFilterPanel(props: FilterProps) {
  const activeCount = (props.changeFilter ? 1 : 0) + (props.needsFilter ? 1 : 0)
  return (
    <div
      id="work-filters-panel"
      data-testid="work-filters-panel"
      className="flex w-[min(36rem,calc(100vw-2rem))] max-w-[calc(100vw-2rem)] flex-wrap items-end gap-x-static-sm gap-y-static-xs rounded-sm border border-contrast-low bg-surface px-static-sm py-static-xs"
    >
      <PSelect
        compact
        className="w-full sm:w-48"
        label="Change"
        name="work-change-filter"
        value={props.changeFilter}
        onChange={(event) => props.onChangeFilter(selectedValue(event as SelectValueEvent))}
      >
        <PSelectOption value="">All changes</PSelectOption>
        {props.changes.map((change) => <PSelectOption key={change.id} value={change.id}>{change.title}</PSelectOption>)}
      </PSelect>
      <PSelect
        compact
        className="w-full sm:w-56"
        label="Attention"
        name="work-needs-filter"
        value={props.needsFilter}
        onChange={(event) => props.onNeedsFilter(selectedValue(event as SelectValueEvent) as WorkItemNeed | '')}
      >
        <PSelectOption value="">Any attention state</PSelectOption>
        <PSelectOption value="you">Needs you</PSelectOption>
        <PSelectOption value="dependency">Waiting on dependency</PSelectOption>
        <PSelectOption value="none">No intervention</PSelectOption>
      </PSelect>
      <PButtonPure
        type="button"
        icon="reset"
        size="small"
        className="mb-1"
        data-testid="work-filters-reset"
        disabled={activeCount === 0}
        onClick={() => {
          props.onChangeFilter('')
          props.onNeedsFilter('')
        }}
      >
        Clear filters
      </PButtonPure>
    </div>
  )
}


function parseSelection(pathname: string): WorkItemIdentity | null {
  const parts = pathname.split('/').filter(Boolean)
  if (parts.length !== 3 || parts[0] !== 'delivery') return null
  try {
    return { changeId: decodeURIComponent(parts[1]), itemKey: decodeURIComponent(parts[2]) }
  } catch {
    return null
  }
}

function isHistoryRoute(pathname: string): boolean {
  const parts = pathname.split('/').filter(Boolean)
  return parts[0] === 'delivery' && parts[1] === 'history' && (parts.length === 2 || parts.length === 4)
}

function SelectedDesignDetail({ changeId, onClose }: { changeId: string; onClose: () => void }) {
  const detail = useDesignWorkDetail(changeId)
  if (detail.data) return (
    <>
      {detail.error ? (
        <div className="mb-static-lg flex flex-wrap items-center gap-static-sm border-l-4 border-warning bg-surface p-static-md" role="alert">
          <span className="min-w-0 flex-1">Showing the last successful Design detail; live updates paused. {detail.error.message}</span>
          <PButton type="button" variant="secondary" disabled={detail.isRefreshing} onClick={detail.retry}>
            {detail.isRefreshing ? 'Retrying Design...' : 'Retry Design'}
          </PButton>
        </div>
      ) : null}
      <DesignWorkDetail detail={detail.data} />
    </>
  )
  if (detail.isLoading) return <p role="status">Loading Design work...</p>
  return <EmptyDetail error={detail.error} retry={detail.retry} onClose={onClose} subject="Design work" retryLabel="Retry Design" />
}

function SelectedWorkItemDetail({
  identity,
  onChanged,
  onClose,
}: {
  identity: WorkItemIdentity
  onChanged: () => void
  onClose: () => void
}) {
  const selectedDetail = useWorkItemDetail(identity, onChanged)
  if (selectedDetail.detail.data) return (
    <>
      {selectedDetail.detail.error ? (
        <div className="mb-static-lg flex flex-wrap items-center gap-static-sm border-l-4 border-warning bg-surface p-static-md" role="alert">
          <span className="min-w-0 flex-1">Showing the last successful Work Item detail; live updates paused. {selectedDetail.detail.error.message}</span>
          <PButton type="button" variant="secondary" disabled={selectedDetail.detail.isRefreshing} onClick={selectedDetail.retry}>
            {selectedDetail.detail.isRefreshing ? 'Retrying Work Item...' : 'Retry Work Item'}
          </PButton>
        </div>
      ) : null}
      <WorkItemDetail
        detail={selectedDetail.detail.data}
        pendingAction={selectedDetail.pendingAction}
        actionError={selectedDetail.actionError}
        actionResult={selectedDetail.actionResult}
        onAnswerRequest={selectedDetail.answerRequest}
        onClearBlock={selectedDetail.clearBlock}
        onRecoverClaim={selectedDetail.recoverClaim}
        onPreviewBackward={selectedDetail.previewBackward}
        onMoveBackward={selectedDetail.moveBackward}
        onReconcilePublication={selectedDetail.reconcilePublication}
        onMarkPublicationReady={selectedDetail.markPublicationReady}
        publicationChecks={selectedDetail.publicationChecks}
        publicationChecksError={selectedDetail.publicationChecksError}
        publicationChecksStale={selectedDetail.publicationChecksStale}
        isObservingPublicationChecks={selectedDetail.isObservingPublicationChecks}
        onObservePublicationChecks={selectedDetail.observePublicationChecks}
        onObserveAcceptance={selectedDetail.observeAcceptance}
        onAdoptExternalHeadAfterAcceptanceAttention={selectedDetail.adoptExternalHeadAfterAcceptanceAttention}
        onResolveAttention={selectedDetail.resolveAttention}
        onSupersedePublication={selectedDetail.supersedePublication}
        onSyncTarget={selectedDetail.syncTarget}
        onAbortTargetSync={selectedDetail.abortTargetSync}
        onResolveTargetSync={selectedDetail.resolveTargetSync}
        onDeferChange={selectedDetail.deferChange}
        onResumeChange={selectedDetail.resumeChange}
        onAbandonChange={selectedDetail.abandonChange}
        onCleanupAbandonedChange={selectedDetail.cleanupAbandonedChange}
        onDiscardAbandonedTargetSync={selectedDetail.discardAbandonedTargetSync}
        onCleanupCompletedChange={selectedDetail.cleanupCompletedChange}
        onRecoverChangeWorktree={selectedDetail.recoverChangeWorktree}
      />
    </>
  )
  if (selectedDetail.detail.isLoading) return <p role="status">Loading Work Item details...</p>
  return <EmptyDetail error={selectedDetail.detail.error} retry={selectedDetail.retry} onClose={onClose} />
}

function SelectedDetail(props: { identity: WorkItemIdentity; onChanged: () => void; onClose: () => void }) {
  if (props.identity.itemKey === 'design') {
    return <SelectedDesignDetail changeId={props.identity.changeId} onClose={props.onClose} />
  }
  return <SelectedWorkItemDetail {...props} />
}

function PortfolioWorkspace({
  groups,
  selected,
  emptyMessage,
  onSelect,
}: {
  groups: ChangeGroupView[]
  selected: WorkItemIdentity | null
  emptyMessage?: string
  onSelect: (identity: WorkItemIdentity, trigger: HTMLElement) => void
}) {
  return <WorkPortfolioTable groups={groups} selected={selected} emptyMessage={emptyMessage} onSelect={onSelect} />
}

function EmptyPortfolioState({ filtered }: { filtered: boolean }) {
  return (
    <section className="grid min-h-40 place-items-center border border-dashed border-contrast-low bg-surface px-static-lg py-static-xl text-center" data-testid="work-empty-state">
      <div className="grid max-w-[44rem] gap-static-xs">
        <PHeading tag="h2" size="small">{filtered ? 'No matching delivery work' : 'No current Delivery work'}</PHeading>
        <p className="text-sm leading-relaxed text-contrast-medium">
          {filtered ? 'Try clearing a filter to see the rest of the portfolio.' : 'Newly admitted Changes and active Outcomes will appear here.'}
        </p>
      </div>
    </section>
  )
}

function DeliveryStatusSection({ statuses }: { statuses: PortfolioChangeLifecycleStatus[] }) {
  if (statuses.length === 0) return null
  return (
    <section className="min-w-0" aria-labelledby="delivery-status-heading" data-testid="delivery-status-section">
      <h2 id="delivery-status-heading" className="mb-static-sm border-b border-contrast-lower px-static-sm pb-static-xs text-md font-semibold text-primary">Delivery status</h2>
      <div className="grid gap-static-sm">
        {statuses.map((status) => (
          <article
            key={status.change_id}
            className="relative min-w-0 rounded-lg border border-l-4 border-warning bg-surface px-static-sm py-static-sm text-sm"
            data-delivery-status={status.change_id}
          >
            <dl className="grid gap-static-sm md:grid-cols-[minmax(0,44fr)_minmax(0,24fr)_minmax(0,32fr)] md:gap-0">
              <div className="min-w-0 md:pr-static-sm">
                <dt className="mb-1 text-2xs font-semibold uppercase text-contrast-high md:sr-only">Change</dt>
                <dd>
                  <strong className="font-semibold text-primary">Change</strong>
                  <code className="block text-xs text-contrast-medium">{status.change_id}</code>
                </dd>
              </div>
              <div className="md:px-static-sm">
                <dt className="mb-1 text-2xs font-semibold uppercase text-contrast-high md:sr-only">Progress</dt>
                <dd>
                  <strong className="font-medium text-primary">{status.stage ? CHANGE_STAGE_LABELS[status.stage] : 'Delivery'}</strong>
                  <span className="block text-xs text-contrast-medium">Admitted to Delivery</span>
                </dd>
              </div>
              <div className="md:pl-static-sm">
                <dt className="mb-1 text-2xs font-semibold uppercase text-contrast-high md:sr-only">Status</dt>
                <dd>
                  <span className="inline-flex items-center rounded-sm border border-warning bg-warning-low px-static-xs py-1 text-xs font-semibold leading-none text-primary">Runtime unavailable</span>
                  {status.diagnostic_detail ? <span className="mt-1 block text-xs text-contrast-medium">{status.diagnostic_detail}</span> : null}
                </dd>
              </div>
            </dl>
          </article>
        ))}
      </div>
    </section>
  )
}

function DeliveryHealthSection({ health }: { health: DeliveryHealthResponse }) {
  if (health.status !== 'attention' || health.diagnostics.length === 0) return null
  return (
    <section className="min-w-0" aria-labelledby="delivery-health-heading" data-testid="delivery-health-section">
      <h2 id="delivery-health-heading" className="mb-static-sm border-b border-contrast-lower px-static-sm pb-static-xs text-md font-semibold text-primary">Delivery health</h2>
      <div className="grid gap-static-sm" role="list">
        {health.diagnostics.map((diagnostic, index) => (
          <article
            key={`${diagnostic.change_id ?? 'portfolio'}-${diagnostic.code}-${index}`}
            className="min-w-0 rounded-sm border border-l-4 border-warning bg-surface px-static-sm py-static-sm text-sm"
            role="listitem"
          >
            <p className="mb-static-sm font-medium text-primary">Quarantined state is hidden from dispatch.</p>
            <dl className="grid gap-static-sm md:grid-cols-[minmax(0,24fr)_minmax(0,24fr)_minmax(0,52fr)] md:gap-0">
              <div className="min-w-0 md:pr-static-sm">
                <dt className="mb-1 text-2xs font-semibold uppercase text-contrast-high">Change</dt>
                <dd className="break-words font-mono text-xs text-contrast-medium">{diagnostic.change_id ?? 'Delivery portfolio'}</dd>
              </div>
              <div className="min-w-0 md:px-static-sm">
                <dt className="mb-1 text-2xs font-semibold uppercase text-contrast-high">Source / code</dt>
                <dd className="break-words text-xs text-contrast-medium"><code>{diagnostic.source}</code><span aria-hidden="true"> / </span><code>{diagnostic.code}</code></dd>
              </div>
              <div className="min-w-0 md:pl-static-sm">
                <dt className="mb-1 text-2xs font-semibold uppercase text-contrast-high">Detail</dt>
                <dd className="break-words text-xs text-contrast-medium">{diagnostic.detail}</dd>
                {diagnostic.path ? <dd className="mt-1 break-all font-mono text-2xs text-contrast-medium">{diagnostic.path}</dd> : null}
              </div>
            </dl>
          </article>
        ))}
      </div>
    </section>
  )
}

function EmptyDetail({
  error,
  retry,
  onClose,
  subject = 'Work Item',
  retryLabel = 'Retry item',
}: {
  error: Error | null
  retry: () => void
  onClose: () => void
  subject?: string
  retryLabel?: string
}) {
  if (error) return (
    <div className="grid gap-static-sm" role="alert">
      <span>This {subject} is unavailable. It may have completed or the link may be invalid.</span>
      <details>
        <summary className="cursor-pointer text-xs font-semibold">Technical evidence</summary>
        <p className="mt-static-xs break-words text-xs text-contrast-medium">{error.message}</p>
      </details>
      <div className="flex flex-wrap gap-static-sm"><PButton type="button" variant="secondary" onClick={retry}>{retryLabel}</PButton><PButton type="button" variant="secondary" onClick={onClose}>Back to current delivery</PButton></div>
    </div>
  )
  return null
}

export default function WorkPortfolioPage() {
  const location = useLocation()
  const navigate = useNavigate()
  const [workspace, setWorkspace] = useState<'current' | 'history'>(() => isHistoryRoute(location.pathname) ? 'history' : 'current')
  const { portfolio, hasData, error, isLoading, retry } = useWorkPortfolio(workspace === 'history')
  const acceptanceReconciliation = useAcceptanceReconciliation(portfolio, retry, workspace === 'history')
  const [changeFilter, setChangeFilter] = useState('')
  const [needsFilter, setNeedsFilter] = useState<WorkItemNeed | ''>('')
  const [filtersOpen, setFiltersOpen] = useState(false)
  const deferredChange = useDeferredValue(changeFilter)
  const deferredNeeds = useDeferredValue(needsFilter)
  const selected = parseSelection(location.pathname)
  const selectedIdentity = selected ? `${selected.changeId}:${selected.itemKey}` : null
  const lastTrigger = useRef<HTMLElement | null>(null)
  const lastTriggerIdentity = useRef<string | null>(null)
  const restoreFocusAfterClose = useRef(false)
  const previousSelectedIdentity = useRef<string | null>(null)
  const focusDestination = useRef<FocusDestination>('trigger')
  const selectedWasPresent = useRef(false)
  const statuses = portfolio.operating.statuses
  const designWorkStatuses = statuses.filter(isUnadmittedDesign)
  const unavailableStatuses = statuses.filter(isUnavailableAdmitted)
  const designWorkIds = designWorkStatuses.map((status) => status.change_id)
  const changes = [
    ...statuses.map((status) => {
      const group = portfolio.groups.find((candidate) => candidate.change_id === status.change_id)
      return {
        id: status.change_id,
        title: group?.title ?? (isUnadmittedDesign(status) ? designWorkTitle(status.change_id) : `Change ${status.change_id}`),
      }
    }),
    ...portfolio.groups
      .filter((group) => !statuses.some((status) => status.change_id === group.change_id))
      .map((group) => ({ id: group.change_id, title: group.title })),
  ]
  const filteredGroups = portfolio.groups
    .filter((group) => !deferredChange || group.change_id === deferredChange)
    .map((group) => ({
      ...group,
      items: group.items.filter((item) => !deferredNeeds || item.needs === deferredNeeds),
    }))
    .filter((group) => group.items.length > 0)
  const shownCount = filteredGroups.reduce((total, group) => total + group.items.length, 0)
  const designMatchesAttention = !deferredNeeds || deferredNeeds === 'you'
  const visibleDesignWorkStatuses = designMatchesAttention && (!deferredChange || designWorkIds.includes(deferredChange))
    ? designWorkStatuses.filter((status) => !deferredChange || status.change_id === deferredChange)
    : []
  const visibleUnavailableStatuses = designMatchesAttention && (!deferredChange || unavailableStatuses.some((status) => status.change_id === deferredChange))
    ? unavailableStatuses.filter((status) => !deferredChange || status.change_id === deferredChange)
    : []
  const shownEntryCount = shownCount + visibleDesignWorkStatuses.length + visibleUnavailableStatuses.length
  const totalEntryCount = portfolio.totals.total + designWorkStatuses.length + unavailableStatuses.length
  const isFiltered = Boolean(deferredChange || deferredNeeds)

  const closeInspector = (destination: FocusDestination = 'trigger') => {
    restoreFocusAfterClose.current = true
    focusDestination.current = destination
    navigate('/delivery', { replace: true })
  }

  useEffect(() => {
    setWorkspace(isHistoryRoute(location.pathname) ? 'history' : 'current')
  }, [location.pathname])

  const handleWorkspaceChange = (nextWorkspace: 'current' | 'history') => {
    if (nextWorkspace === 'history') {
      setWorkspace('history')
      if (selected) {
        restoreFocusAfterClose.current = true
        focusDestination.current = 'history-view'
        navigate('/delivery/history', { replace: true })
      } else if (!isHistoryRoute(location.pathname)) {
        navigate('/delivery/history')
      }
      return
    }
    setWorkspace('current')
    if (restoreFocusAfterClose.current) {
      focusDestination.current = 'current-view'
    }
    if (isHistoryRoute(location.pathname)) {
      navigate('/delivery', { replace: true })
    }
  }

  const handleInspectorKeyDown = (event: ReactKeyboardEvent<HTMLDivElement>) => {
    if (event.key !== 'Escape') return
    if (event.target instanceof HTMLElement && event.target.closest('p-modal')) return
    event.preventDefault()
    closeInspector()
  }

  useEffect(() => {
    if (selected) {
      previousSelectedIdentity.current = selectedIdentity
      return
    }
    if (!previousSelectedIdentity.current && !restoreFocusAfterClose.current) return
    previousSelectedIdentity.current = null
    let secondFrame: number | null = null
    const firstFrame = window.requestAnimationFrame(() => {
      secondFrame = window.requestAnimationFrame(() => {
        const primaryTrigger = Array.from(document.querySelectorAll<HTMLElement>('[data-work-item-primary-trigger]'))
          .find((candidate) => candidate.dataset.workItemIdentity === lastTriggerIdentity.current)
        const destination = focusDestination.current
        const triggerFocusTarget = lastTrigger.current?.isConnected ? lastTrigger.current : primaryTrigger
        const focusTarget = destination === 'history-view'
          ? document.querySelector<HTMLElement>('[data-workspace-view="history"]')
          : destination === 'current-view'
            ? document.querySelector<HTMLElement>('[data-workspace-view="current"]')
            : triggerFocusTarget
              ?? (isFiltered ? document.querySelector<HTMLElement>('[data-testid="work-filters-toggle"]') : null)
              ?? document.querySelector<HTMLElement>('[data-workspace-view="current"]')
        focusTarget?.focus()
        restoreFocusAfterClose.current = false
        focusDestination.current = 'trigger'
      })
    })
    return () => {
      window.cancelAnimationFrame(firstFrame)
      if (secondFrame !== null) window.cancelAnimationFrame(secondFrame)
    }
  }, [isFiltered, selectedIdentity])

  useEffect(() => {
    if (!selected || !hasData) {
      selectedWasPresent.current = false
      return
    }
    const isDesignWork = selected.itemKey === 'design'
    const present = isDesignWork
      ? designWorkIds.includes(selected.changeId)
      : portfolio.groups.some((group) => group.change_id === selected.changeId
        && group.items.some((item) => item.item_key === selected.itemKey))
    if (present) selectedWasPresent.current = true
    if (!present && selectedWasPresent.current) {
      selectedWasPresent.current = false
      const changeCompleted = !isDesignWork && portfolio.groups.every((group) => group.change_id !== selected.changeId)
      restoreFocusAfterClose.current = true
      focusDestination.current = changeCompleted ? 'history-view' : 'current-view'
      if (changeCompleted) setWorkspace('history')
      navigate(changeCompleted ? '/delivery/history' : '/delivery', { replace: true })
    }
  }, [hasData, navigate, portfolio.groups, selected])

  const filterProps: FilterProps = {
    changes,
    changeFilter,
    needsFilter,
    open: filtersOpen,
    onToggle: () => setFiltersOpen((open) => !open),
    onDismiss: () => setFiltersOpen(false),
    onChangeFilter: setChangeFilter,
    onNeedsFilter: setNeedsFilter,
  }

  return (
    <main className="flex h-full min-h-0 min-w-0 flex-col overflow-hidden bg-canvas text-primary" data-testid="work-portfolio-page">
      <WorkspaceHeader
        flush
        title="Delivery portfolio"
        titleId="delivery-portfolio-heading"
        summaryLabel="Delivery portfolio status"
        summary={workspace === 'current' && hasData ? (
          <PortfolioHeaderSummary
            operating={portfolio.operating}
            totals={portfolio.totals}
            needsFilter={needsFilter}
            onNeedsFilter={setNeedsFilter}
          />
        ) : undefined}
      />

      <div className="flex min-w-0 shrink-0 flex-wrap items-end gap-x-static-md gap-y-static-xs bg-canvas px-static-lg">
        <PortfolioViewSwitch workspace={workspace} onChange={handleWorkspaceChange} />
        {workspace === 'current' ? (
          <div className="ml-auto flex min-w-0 max-w-full flex-wrap items-center justify-end gap-static-xs pb-static-xs">
            {isFiltered ? <span data-testid="work-shown-count"><WorkspaceViewCount value={`${shownEntryCount} of ${totalEntryCount}`} unit="portfolio entries shown" /></span> : null}
            <PortfolioFilterTools {...filterProps} />
          </div>
        ) : null}
      </div>

      <div
        className="flex min-h-0 w-full min-w-0 flex-1 flex-col gap-static-lg overflow-y-auto overflow-x-hidden px-static-lg py-static-lg"
        data-testid="work-scroll-surface"
      >
        {workspace === 'current' ? (
          <>
            {isLoading ? <div className="grid gap-static-sm" role="status" aria-label="Loading current delivery">{Array.from({ length: 4 }, (_, index) => <span key={index} className="block h-12 animate-pulse bg-surface" />)}</div> : null}
            {error ? (
              <section className="flex flex-wrap items-center gap-static-sm border-l-4 border-danger bg-surface p-static-md" role="alert">
                <PIcon name="error" aria-hidden="true" />
                <span className="min-w-0 flex-1">{hasData ? 'Showing the last successful refresh — live updates paused.' : 'Work portfolio is unavailable.'} {error.message}</span>
                <PButton type="button" variant="secondary" onClick={retry}>Retry portfolio</PButton>
              </section>
            ) : null}
            {acceptanceReconciliation.providerError ? (
              <section className="flex flex-wrap items-center gap-static-sm border-l-4 border-warning bg-surface p-static-md" role="alert">
                <PIcon name="warning" aria-hidden="true" />
                <span className="min-w-0 flex-1">
                  GitHub acceptance checks are unavailable for {acceptanceReconciliation.providerChangeIds.join(', ')}. {acceptanceReconciliation.providerError.message}
                </span>
                <PButton type="button" variant="secondary" loading={acceptanceReconciliation.isRetrying} onClick={acceptanceReconciliation.retry}>
                  {acceptanceReconciliation.isRetrying ? 'Retrying acceptance check...' : 'Retry acceptance check'}
                </PButton>
              </section>
            ) : null}

            {hasData ? (
              <>
                <DeliveryHealthSection health={portfolio.health} />
                {filteredGroups.length > 0 ? (
                  <PortfolioWorkspace
                    groups={filteredGroups}
                    selected={selected}
                    onSelect={(identity, trigger) => {
                      lastTrigger.current = trigger
                      lastTriggerIdentity.current = `${identity.changeId}:${identity.itemKey}`
                    }}
                  />
                ) : null}
                {visibleUnavailableStatuses.length > 0 ? (
                  <DeliveryStatusSection statuses={visibleUnavailableStatuses} />
                ) : null}
                {visibleDesignWorkStatuses.length > 0 ? (
                  <DesignWorkSection
                    statuses={visibleDesignWorkStatuses}
                    selectedChangeId={selected?.itemKey === 'design' ? selected.changeId : null}
                    onSelect={(identity, trigger) => {
                      lastTrigger.current = trigger
                      lastTriggerIdentity.current = `${identity.changeId}:${identity.itemKey}`
                    }}
                  />
                ) : null}
                {filteredGroups.length === 0 && visibleUnavailableStatuses.length === 0 && visibleDesignWorkStatuses.length === 0 ? (
                  <EmptyPortfolioState filtered={isFiltered} />
                ) : null}
                <PortfolioOperatingSummary operating={portfolio.operating} />
              </>
            ) : null}
          </>
        ) : <CompletedHistoryWorkspace />}
      </div>

      <PFlyout
        open={selected !== null}
        position="end"
        backdrop="shading"
        background="canvas"
        fullscreen={{ base: true, m: false }}
        style={{ '--p-flyout-width': 'min(56rem, 100vw)' } as CSSProperties}
        aria={{ 'aria-label': selected?.itemKey === 'design' ? 'Design detail' : 'Work Item detail' }}
        onDismiss={() => closeInspector()}
        onKeyDownCapture={handleInspectorKeyDown}
      >
        <div className="min-w-0 max-w-full p-static-lg">
          {selected ? <SelectedDetail key={selectedIdentity} identity={selected} onChanged={retry} onClose={closeInspector} /> : null}
        </div>
      </PFlyout>
    </main>
  )
}
