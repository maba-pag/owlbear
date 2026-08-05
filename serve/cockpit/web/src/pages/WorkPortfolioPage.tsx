import { useDeferredValue, useState } from 'react'
import { PButton, PButtonPure, PFlyout, PIcon, PSelect, PSelectOption, PTagDismissible } from '@porsche-design-system/components-react'
import type { AttentionCounts, WorkItemAttention, WorkItemProjection } from '../api/workItems'
import { ATTENTION_LABELS, ATTENTION_SUMMARY_LABELS, workItemCountLabel } from '../attentionVocabulary'
import CompletedHistoryWorkspace from '../components/CompletedHistoryWorkspace'
import { WorkspaceHeader, WorkspaceHeaderMetric } from '../components/WorkspaceHeader'
import WorkspaceViewHeader, { WorkspaceViewCount } from '../components/WorkspaceViewHeader'
import WorkItemDetail from '../components/WorkItemDetail'
import WorkPortfolioBoard from '../components/WorkPortfolioBoard'
import { useWorkItemDetail, useWorkPortfolio, type WorkItemIdentity } from '../hooks/useWorkItems'

type SelectValueEvent = { target?: { value?: unknown }; detail?: { value?: unknown } }

function selectedValue(event: SelectValueEvent): string {
  const value = event.detail?.value ?? event.target?.value
  return typeof value === 'string' ? value : ''
}

/** Short visible wording with the full phrase kept for assistive technology. */
function AttentionMetricLabel({ state }: { state: WorkItemAttention }) {
  const { short, full } = ATTENTION_SUMMARY_LABELS[state]
  return (
    <span title={full}>
      <span aria-hidden="true">{short}</span>
      <span className="sr-only">{full}</span>
    </span>
  )
}

/**
 * Portfolio status strip: one total plus the four orthogonal attention states the API counts,
 * so the parts always add up to the whole.
 */
function PortfolioStatusSummary({ counts }: { counts: AttentionCounts }) {
  const total = counts.user + counts.agent + counts.waiting + counts.none
  return (
    <>
      <WorkspaceHeaderMetric value={total} label={workItemCountLabel(total)} />
      <WorkspaceHeaderMetric value={counts.user} label={<AttentionMetricLabel state="user" />} tone={counts.user > 0 ? 'error' : 'neutral'} />
      <WorkspaceHeaderMetric value={counts.agent} label={<AttentionMetricLabel state="agent" />} />
      <WorkspaceHeaderMetric value={counts.waiting} label={<AttentionMetricLabel state="waiting" />} />
      <WorkspaceHeaderMetric value={counts.none} label={<AttentionMetricLabel state="none" />} />
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
  changes: string[]
  changeFilter: string
  attentionFilter: WorkItemAttention | ''
  open: boolean
  onToggle: () => void
  onChangeFilter: (value: string) => void
  onAttentionFilter: (value: WorkItemAttention | '') => void
}

/** Collapsed trigger plus active-filter chips; the expanded surface renders separately below. */
function PortfolioFilterTools(props: FilterProps) {
  const activeCount = (props.changeFilter ? 1 : 0) + (props.attentionFilter ? 1 : 0)
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
      {props.attentionFilter ? (
        <PTagDismissible
          compact
          label={`Attention: ${ATTENTION_LABELS[props.attentionFilter]}`}
          data-testid="work-filter-chip-attention"
          aria={{ 'aria-label': `Remove attention filter ${ATTENTION_LABELS[props.attentionFilter]}` }}
          onClick={() => props.onAttentionFilter('')}
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
  const activeCount = (props.changeFilter ? 1 : 0) + (props.attentionFilter ? 1 : 0)
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
        {props.changes.map((changeId) => <PSelectOption key={changeId} value={changeId}>{changeId}</PSelectOption>)}
      </PSelect>
      <PSelect
        compact
        className="w-56"
        label="Attention"
        name="work-attention-filter"
        value={props.attentionFilter}
        onChange={(event) => props.onAttentionFilter(selectedValue(event as SelectValueEvent) as WorkItemAttention | '')}
      >
        <PSelectOption value="">Any attention</PSelectOption>
        <PSelectOption value="user">{ATTENTION_LABELS.user}</PSelectOption>
        <PSelectOption value="agent">{ATTENTION_LABELS.agent}</PSelectOption>
        <PSelectOption value="waiting">{ATTENTION_LABELS.waiting}</PSelectOption>
        <PSelectOption value="none">{ATTENTION_LABELS.none}</PSelectOption>
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
          props.onAttentionFilter('')
        }}
      >
        Clear filters
      </PButtonPure>
    </div>
  )
}


function PortfolioWorkspace({ items, onChanged }: { items: WorkItemProjection[]; onChanged: () => void }) {
  const [selected, setSelected] = useState<WorkItemIdentity | null>(null)
  const selectedDetail = useWorkItemDetail(selected, onChanged)
  const selectedProjection = selected
    ? items.find((item) => item.change_id === selected.changeId && item.work_item_id === selected.workItemId) ?? null
    : null
  return (
    <div className="min-w-0">
      <WorkPortfolioBoard items={items} selected={selected} onSelect={setSelected} />
      <PFlyout
        id="work-item-flyout"
        open={selected !== null}
        position="end"
        aria={{ 'aria-label': 'Work item details' }}
        onDismiss={() => setSelected(null)}
      >
        {selectedDetail.detail.data && selectedProjection ? (
          <WorkItemDetail
            key={`${selectedDetail.detail.data.operator.change_id}:${selectedDetail.detail.data.operator.outcome_id}`}
            detail={selectedDetail.detail.data}
            projection={selectedProjection}
            pendingAction={selectedDetail.pendingAction}
            actionError={selectedDetail.actionError}
            actionResult={selectedDetail.actionResult}
            onAnswerRequest={selectedDetail.answerRequest}
            onClearBlock={selectedDetail.clearBlock}
            onRecoverClaim={selectedDetail.recoverClaim}
            onMoveBackward={selectedDetail.moveBackward}
            onRetryIntegration={selectedDetail.retryIntegration}
          />
        ) : selectedDetail.detail.isLoading ? (
          <p className="p-static-lg" role="status">Loading work item details...</p>
        ) : selectedDetail.detail.error ? (
          <div className="p-static-lg"><EmptyDetail error={selectedDetail.detail.error} retry={selectedDetail.retry} /></div>
        ) : null}
      </PFlyout>
    </div>
  )
}

function EmptyDetail({ error, retry }: { error: Error | null; retry: () => void }) {
  if (error) return (
    <div className="flex items-center gap-static-sm" role="alert">
      <span>Work item is unavailable. {error.message}</span>
      <PButton type="button" variant="secondary" onClick={retry}>Retry item</PButton>
    </div>
  )
  return null
}

export default function WorkPortfolioPage() {
  const { portfolio, hasData, error, isLoading, retry } = useWorkPortfolio()
  const [changeFilter, setChangeFilter] = useState('')
  const [attentionFilter, setAttentionFilter] = useState<WorkItemAttention | ''>('')
  const [filtersOpen, setFiltersOpen] = useState(false)
  const [workspace, setWorkspace] = useState<'current' | 'history'>('current')
  const deferredChange = useDeferredValue(changeFilter)
  const deferredAttention = useDeferredValue(attentionFilter)
  const items = portfolio.items.map((item) => item.card)
  const changes = [...new Set(items.map((item) => item.change_id))].sort()
  const filteredItems = items.filter(
    (item) => (!deferredChange || item.change_id === deferredChange)
      && (!deferredAttention || item.attention === deferredAttention),
  )
  const isFiltered = Boolean(deferredChange || deferredAttention)
  const filterProps: FilterProps = {
    changes,
    changeFilter,
    attentionFilter,
    open: filtersOpen,
    onToggle: () => setFiltersOpen((open) => !open),
    onChangeFilter: setChangeFilter,
    onAttentionFilter: setAttentionFilter,
  }

  return (
    <main className="flex h-full min-h-0 min-w-0 flex-col overflow-hidden bg-canvas text-primary" data-testid="work-portfolio-page">
      <WorkspaceHeader
        flush
        title="Delivery portfolio"
        titleId="delivery-portfolio-heading"
        summaryLabel="Delivery portfolio status"
        summary={workspace === 'current' ? <PortfolioStatusSummary counts={portfolio.attention_counts} /> : undefined}
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
                title="Delivery stages"
                metaTestId="work-shown-count"
                meta={isFiltered ? <WorkspaceViewCount value={`${filteredItems.length} of ${items.length}`} unit={`${workItemCountLabel(items.length)} shown`} /> : null}
                tools={<PortfolioFilterTools {...filterProps} />}
              />
              {filtersOpen ? <PortfolioFilterPanel {...filterProps} /> : null}
            </div>

            {isLoading ? <p role="status">Loading work portfolio...</p> : null}
            {error ? (
              <section className="flex flex-wrap items-center gap-static-sm border-l-4 border-danger bg-surface p-static-md" role="alert">
                <PIcon name="error" aria-hidden="true" />
                <span className="min-w-0 flex-1">Work portfolio is unavailable. {error.message}</span>
                <PButton type="button" variant="secondary" onClick={retry}>Retry portfolio</PButton>
              </section>
            ) : null}

            {hasData && !error ? <PortfolioWorkspace items={filteredItems} onChanged={retry} /> : null}
          </>
        ) : <CompletedHistoryWorkspace />}
      </div>
    </main>
  )
}
