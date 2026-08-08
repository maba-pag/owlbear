import { useDeferredValue, useEffect, useRef, useState } from 'react'
import { PButton, PButtonPure, PFlyout, PIcon, PSelect, PSelectOption, PTagDismissible } from '@porsche-design-system/components-react'
import { useLocation, useNavigate } from 'react-router'
import type { ChangeGroupView, WorkItemNeed, WorkItemPortfolioTotals } from '../api/workItems'
import CompletedHistoryWorkspace from '../components/CompletedHistoryWorkspace'
import { WorkspaceHeader, WorkspaceHeaderMetric } from '../components/WorkspaceHeader'
import WorkspaceViewHeader, { WorkspaceViewCount } from '../components/WorkspaceViewHeader'
import WorkItemDetail from '../components/WorkItemDetail'
import WorkPortfolioTable from '../components/WorkPortfolioTable'
import { useWorkItemDetail, useWorkPortfolio, type WorkItemIdentity } from '../hooks/useWorkItems'

type SelectValueEvent = { target?: { value?: unknown }; detail?: { value?: unknown } }

function selectedValue(event: SelectValueEvent): string {
  const value = event.detail?.value ?? event.target?.value
  return typeof value === 'string' ? value : ''
}

function PortfolioStatusSummary({ totals }: { totals: WorkItemPortfolioTotals }) {
  return (
    <>
      <WorkspaceHeaderMetric value={totals.total} label={totals.total === 1 ? 'work item' : 'work items'} />
      <WorkspaceHeaderMetric value={totals.needs.you} label="need you" tone={totals.needs.you > 0 ? 'error' : 'neutral'} />
      <WorkspaceHeaderMetric value={totals.needs.dependency} label="dependency" />
      <WorkspaceHeaderMetric value={totals.needs.repair} label="need repair" tone={totals.needs.repair > 0 ? 'error' : 'neutral'} />
      <WorkspaceHeaderMetric value={totals.activity.working + totals.activity.repairing} label="active" />
      <WorkspaceHeaderMetric value={totals.activity.ready} label="ready" />
      <WorkspaceHeaderMetric value={totals.complete} label="complete" />
    </>
  )
}

function PortfolioViewSwitch({ workspace, onChange }: { workspace: 'current' | 'history'; onChange: (workspace: 'current' | 'history') => void }) {
  return (
    <nav
      className="flex shrink-0 items-stretch gap-static-lg bg-canvas px-static-lg pb-static-xs"
      aria-label="Delivery portfolio views"
      data-testid="work-view-selector"
    >
      {([
        ['current', 'Current delivery'],
        ['history', 'Completed history'],
      ] as const).map(([value, label]) => (
        <button
          key={value}
          type="button"
          className={[
            'border-b-2 pb-static-xs pt-1 text-xs focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus',
            workspace === value ? 'border-primary font-semibold text-primary' : 'border-transparent font-medium text-contrast-medium hover:text-primary',
          ].join(' ')}
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
  onChangeFilter: (value: string) => void
  onNeedsFilter: (value: WorkItemNeed | '') => void
}

/** Collapsed trigger plus active-filter chips; the expanded surface renders separately below. */
function PortfolioFilterTools(props: FilterProps) {
  const activeCount = (props.changeFilter ? 1 : 0) + (props.needsFilter ? 1 : 0)
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
          label={`Attention: ${props.needsFilter === 'you' ? 'Needs you' : props.needsFilter === 'dependency' ? 'Waiting on dependency' : props.needsFilter === 'repair' ? 'Repair required' : 'No intervention'}`}
          data-testid="work-filter-chip-needs"
          aria={{ 'aria-label': 'Remove Attention filter' }}
          onClick={() => props.onNeedsFilter('')}
        />
      ) : null}
      <PButtonPure
        type="button"
        icon="filter"
        size="small"
        data-testid="work-filters-toggle"
        aria={{ 'aria-expanded': props.open }}
        onClick={props.onToggle}
      >
        {activeCount > 0 ? `Filter (${activeCount})` : 'Filter'}
      </PButtonPure>
    </>
  )
}

function PortfolioFilterPanel(props: FilterProps) {
  const activeCount = (props.changeFilter ? 1 : 0) + (props.needsFilter ? 1 : 0)
  return (
    <div
      id="work-filters-panel"
      data-testid="work-filters-panel"
      className="ml-auto flex w-fit max-w-full flex-wrap items-end gap-x-static-sm gap-y-static-xs rounded-sm border border-contrast-low bg-surface px-static-sm py-static-xs"
    >
      <PSelect
        compact
        className="w-48"
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
        className="w-56"
        label="Attention"
        name="work-needs-filter"
        value={props.needsFilter}
        onChange={(event) => props.onNeedsFilter(selectedValue(event as SelectValueEvent) as WorkItemNeed | '')}
      >
        <PSelectOption value="">Any attention state</PSelectOption>
        <PSelectOption value="you">Needs you</PSelectOption>
        <PSelectOption value="dependency">Waiting on dependency</PSelectOption>
        <PSelectOption value="repair">Repair required</PSelectOption>
        <PSelectOption value="none">No intervention</PSelectOption>
      </PSelect>
      <PButtonPure
        type="button"
        icon="reset"
        size="small"
        className="mb-2"
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

function SelectedDetail({
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
      onRetryIntegration={selectedDetail.retryIntegration}
    />
  )
  if (selectedDetail.detail.isLoading) return <p role="status">Loading Work Item details...</p>
  return <EmptyDetail error={selectedDetail.detail.error} retry={selectedDetail.retry} onClose={onClose} />
}

function PortfolioWorkspace({
  groups,
  selected,
  onSelect,
  onClose,
  onChanged,
}: {
  groups: ChangeGroupView[]
  selected: WorkItemIdentity | null
  onSelect: (identity: WorkItemIdentity, trigger: HTMLAnchorElement) => void
  onClose: () => void
  onChanged: () => void
}) {
  const workspaceRef = useRef<HTMLDivElement>(null)
  const [split, setSplit] = useState(false)

  useEffect(() => {
    const workspace = workspaceRef.current
    if (!workspace) return
    const updateSplit = () => setSplit(workspace.getBoundingClientRect().width >= 1200)
    updateSplit()
    window.addEventListener('resize', updateSplit)
    if (typeof ResizeObserver === 'undefined') return () => window.removeEventListener('resize', updateSplit)
    const observer = new ResizeObserver(updateSplit)
    observer.observe(workspace)
    return () => {
      observer.disconnect()
      window.removeEventListener('resize', updateSplit)
    }
  }, [])

  return (
    <div
      ref={workspaceRef}
      className={['grid min-w-0 gap-static-lg', selected && split ? 'grid-cols-[minmax(0,1fr)_minmax(26rem,28rem)] items-start' : ''].join(' ')}
    >
      <div className="min-w-0"><WorkPortfolioTable groups={groups} selected={selected} onSelect={onSelect} /></div>
      {selected && split ? (
        <aside className="sticky top-0 min-h-0 min-w-0 self-start overflow-hidden border-l border-contrast-low pl-static-lg" aria-label="Work Item inspector">
          <div className="grid h-[calc(100dvh-13rem)] min-h-0 grid-rows-[auto_minmax(0,1fr)] overflow-hidden">
            <div className="flex justify-end border-b border-contrast-low pb-static-sm"><PButton type="button" compact variant="secondary" icon="close" hideLabel onClick={onClose}>Close inspector</PButton></div>
            <div className="min-h-0 overflow-y-auto pb-static-lg pr-static-xs pt-static-md" data-testid="work-inspector-scroll">
              <SelectedDetail key={`${selected.changeId}:${selected.itemKey}`} identity={selected} onChanged={onChanged} onClose={onClose} />
            </div>
          </div>
        </aside>
      ) : null}
      {selected && !split ? (
        <PFlyout open position="end" aria={{ 'aria-label': 'Work Item inspector' }} onDismiss={onClose}>
          <div className="p-static-lg">
            <SelectedDetail key={`${selected.changeId}:${selected.itemKey}`} identity={selected} onChanged={onChanged} onClose={onClose} />
          </div>
        </PFlyout>
      ) : null}
    </div>
  )
}

function EmptyDetail({ error, retry, onClose }: { error: Error | null; retry: () => void; onClose: () => void }) {
  if (error) return (
    <div className="grid gap-static-sm" role="alert">
      <span>This Work Item is unavailable. It may have completed or the link may be invalid.</span>
      <details>
        <summary className="cursor-pointer text-xs font-semibold">Technical evidence</summary>
        <p className="mt-static-xs break-words text-xs text-contrast-medium">{error.message}</p>
      </details>
      <div className="flex flex-wrap gap-static-sm"><PButton type="button" variant="secondary" onClick={retry}>Retry item</PButton><PButton type="button" variant="secondary" onClick={onClose}>Back to current delivery</PButton></div>
    </div>
  )
  return null
}

export default function WorkPortfolioPage() {
  const { portfolio, hasData, error, isLoading, retry } = useWorkPortfolio()
  const location = useLocation()
  const navigate = useNavigate()
  const [changeFilter, setChangeFilter] = useState('')
  const [needsFilter, setNeedsFilter] = useState<WorkItemNeed | ''>('')
  const [filtersOpen, setFiltersOpen] = useState(false)
  const [workspace, setWorkspace] = useState<'current' | 'history'>('current')
  const deferredChange = useDeferredValue(changeFilter)
  const deferredNeeds = useDeferredValue(needsFilter)
  const selected = parseSelection(location.pathname)
  const selectedIdentity = selected ? `${selected.changeId}:${selected.itemKey}` : null
  const lastTrigger = useRef<HTMLAnchorElement | null>(null)
  const lastTriggerIdentity = useRef<string | null>(null)
  const restoreFocusAfterClose = useRef(false)
  const selectedWasPresent = useRef(false)
  const changes = portfolio.groups.map((group) => ({ id: group.change_id, title: group.title }))
  const filteredGroups = portfolio.groups
    .filter((group) => !deferredChange || group.change_id === deferredChange)
    .map((group) => ({
      ...group,
      items: group.items.filter((item) => !deferredNeeds || item.needs === deferredNeeds),
    }))
    .filter((group) => group.items.length > 0)
  const shownCount = filteredGroups.reduce((total, group) => total + group.items.length, 0)
  const isFiltered = Boolean(deferredChange || deferredNeeds)

  const closeInspector = () => {
    restoreFocusAfterClose.current = true
    navigate('/delivery')
  }

  useEffect(() => {
    if (selected || !restoreFocusAfterClose.current) return
    let secondFrame: number | null = null
    const firstFrame = window.requestAnimationFrame(() => {
      secondFrame = window.requestAnimationFrame(() => {
        const primaryTrigger = Array.from(document.querySelectorAll<HTMLAnchorElement>('[data-work-item-primary-trigger]'))
          .find((candidate) => candidate.dataset.workItemIdentity === lastTriggerIdentity.current)
        const focusTarget = lastTrigger.current?.isConnected ? lastTrigger.current : primaryTrigger
        focusTarget?.focus()
        restoreFocusAfterClose.current = false
      })
    })
    return () => {
      window.cancelAnimationFrame(firstFrame)
      if (secondFrame !== null) window.cancelAnimationFrame(secondFrame)
    }
  }, [selectedIdentity])

  useEffect(() => {
    if (!selected || !hasData) {
      selectedWasPresent.current = false
      return
    }
    const present = portfolio.groups.some((group) => group.change_id === selected.changeId
      && group.items.some((item) => item.item_key === selected.itemKey))
    if (present) selectedWasPresent.current = true
    if (!present && selectedWasPresent.current) {
      selectedWasPresent.current = false
      const changeCompleted = portfolio.groups.every((group) => group.change_id !== selected.changeId)
      if (changeCompleted) setWorkspace('history')
      navigate('/delivery', { replace: true })
    }
  }, [hasData, navigate, portfolio.groups, selected])

  const filterProps: FilterProps = {
    changes,
    changeFilter,
    needsFilter,
    open: filtersOpen,
    onToggle: () => setFiltersOpen((open) => !open),
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
        summary={workspace === 'current' ? <PortfolioStatusSummary totals={portfolio.totals} /> : undefined}
      />

      <PortfolioViewSwitch workspace={workspace} onChange={setWorkspace} />

      <div
        className="flex min-h-0 w-full min-w-0 flex-1 flex-col gap-static-md overflow-y-auto overflow-x-hidden px-static-lg pb-static-lg pt-6"
        data-testid="work-scroll-surface"
      >
        {workspace === 'current' ? (
          <>
            <div className="grid gap-static-xs">
              <WorkspaceViewHeader
                headingId="work-board-heading"
                title="Current delivery"
                metaTestId="work-shown-count"
                meta={isFiltered ? <WorkspaceViewCount value={`${shownCount} of ${portfolio.totals.total}`} unit="work items shown" /> : null}
                tools={<PortfolioFilterTools {...filterProps} />}
              />
              {filtersOpen ? <PortfolioFilterPanel {...filterProps} /> : null}
            </div>

            {isLoading ? <div className="grid gap-static-sm" role="status" aria-label="Loading current delivery">{Array.from({ length: 4 }, (_, index) => <span key={index} className="block h-12 animate-pulse bg-surface" />)}</div> : null}
            {error ? (
              <section className="flex flex-wrap items-center gap-static-sm border-l-4 border-danger bg-surface p-static-md" role="alert">
                <PIcon name="error" aria-hidden="true" />
                <span className="min-w-0 flex-1">{hasData ? 'Showing the last successful refresh — live updates paused.' : 'Work portfolio is unavailable.'} {error.message}</span>
                <PButton type="button" variant="secondary" onClick={retry}>Retry portfolio</PButton>
              </section>
            ) : null}

            {hasData ? (
              <PortfolioWorkspace
                groups={filteredGroups}
                selected={selected}
                onSelect={(identity, trigger) => {
                  lastTrigger.current = trigger
                  lastTriggerIdentity.current = `${identity.changeId}:${identity.itemKey}`
                }}
                onClose={closeInspector}
                onChanged={retry}
              />
            ) : null}
          </>
        ) : <CompletedHistoryWorkspace />}
      </div>
    </main>
  )
}
