import { useDeferredValue, useState } from 'react'
import { PButton, PHeading, PIcon, PSelect, PSelectOption, PTag } from '@porsche-design-system/components-react'
import type { AttentionCounts, WorkItemAttention, WorkItemProjection } from '../api/workItems'
import WorkItemDetail from '../components/WorkItemDetail'
import WorkPortfolioBoard from '../components/WorkPortfolioBoard'
import { useWorkItemDetail, useWorkPortfolio, type WorkItemIdentity } from '../hooks/useWorkItems'

type SelectValueEvent = { target?: { value?: unknown }; detail?: { value?: unknown } }

function selectedValue(event: SelectValueEvent): string {
  const value = event.detail?.value ?? event.target?.value
  return typeof value === 'string' ? value : ''
}

function PortfolioHeader({ counts }: { counts: AttentionCounts }) {
  return (
    <header className="flex min-w-0 flex-col gap-static-md border-b border-contrast-low pb-static-lg md:flex-row md:items-end md:justify-between">
      <div className="min-w-0">
        <p className="mb-static-xs text-sm font-semibold text-contrast-medium">Global delivery portfolio</p>
        <PHeading tag="h1" size="xl">Work</PHeading>
      </div>
      <div className="flex flex-wrap gap-static-xs" aria-label="Attention totals">
        <PTag compact>User {counts.user}</PTag>
        <PTag compact>Agent {counts.agent}</PTag>
        <PTag compact>Waiting {counts.waiting}</PTag>
      </div>
    </header>
  )
}

interface FilterProps {
  changes: string[]
  changeFilter: string
  attentionFilter: WorkItemAttention | ''
  shown: number
  total: number
  onChangeFilter: (value: string) => void
  onAttentionFilter: (value: WorkItemAttention | '') => void
}

function PortfolioFilters(props: FilterProps) {
  return (
    <section aria-labelledby="work-filters-heading" className="grid gap-static-sm sm:grid-cols-2 xl:grid-cols-[minmax(12rem,18rem)_minmax(12rem,18rem)_1fr] xl:items-end">
      <h2 id="work-filters-heading" className="sr-only">Portfolio filters</h2>
      <label className="grid gap-static-xs text-sm font-semibold">
        Change
        <PSelect name="work-change-filter" value={props.changeFilter} onChange={(event) => props.onChangeFilter(selectedValue(event as SelectValueEvent))}>
          <PSelectOption value="">All changes</PSelectOption>
          {props.changes.map((changeId) => <PSelectOption key={changeId} value={changeId}>{changeId}</PSelectOption>)}
        </PSelect>
      </label>
      <label className="grid gap-static-xs text-sm font-semibold">
        Attention
        <PSelect name="work-attention-filter" value={props.attentionFilter} onChange={(event) => props.onAttentionFilter(selectedValue(event as SelectValueEvent) as WorkItemAttention | '')}>
          <PSelectOption value="">All attention</PSelectOption>
          <PSelectOption value="user">User</PSelectOption>
          <PSelectOption value="agent">Agent</PSelectOption>
          <PSelectOption value="waiting">Waiting</PSelectOption>
          <PSelectOption value="none">None</PSelectOption>
        </PSelect>
      </label>
      <p className="text-sm text-contrast-medium lg:text-right" aria-live="polite" data-testid="work-shown-count">
        Showing <strong>{props.shown}</strong> of {props.total}
      </p>
    </section>
  )
}

function PortfolioWorkspace({ items, onChanged }: { items: WorkItemProjection[]; onChanged: () => void }) {
  const [selected, setSelected] = useState<WorkItemIdentity | null>(null)
  const selectedDetail = useWorkItemDetail(selected, onChanged)
  const selectedProjection = selected
    ? items.find((item) => item.change_id === selected.changeId && item.work_item_id === selected.workItemId) ?? null
    : null
  return (
    <div className="grid min-w-0 gap-static-lg lg:grid-cols-[minmax(0,1fr)_minmax(20rem,0.42fr)]">
      <WorkPortfolioBoard items={items} selected={selected} onSelect={setSelected} />
      {selectedDetail.detail.data && selectedProjection ? (
        <WorkItemDetail
          key={`${selectedDetail.detail.data.operator.change_id}:${selectedDetail.detail.data.operator.outcome_id}`}
          detail={selectedDetail.detail.data}
          projection={selectedProjection}
          pendingAction={selectedDetail.pendingAction}
          actionError={selectedDetail.actionError}
          actionResult={selectedDetail.actionResult}
          onClose={() => setSelected(null)}
          onAnswerRequest={selectedDetail.answerRequest}
          onClearBlock={selectedDetail.clearBlock}
          onRecoverClaim={selectedDetail.recoverClaim}
          onMoveBackward={selectedDetail.moveBackward}
          onRetryIntegration={selectedDetail.retryIntegration}
        />
      ) : selectedDetail.detail.isLoading ? <p role="status">Loading work item...</p> : <EmptyDetail error={selectedDetail.detail.error} retry={selectedDetail.retry} />}
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
  return (
    <aside className="border-t border-contrast-low pt-static-lg text-sm text-contrast-medium lg:border-l lg:border-t-0 lg:pl-static-lg lg:pt-0">
      Select a work item to inspect its specification and requests.
    </aside>
  )
}

export default function WorkPortfolioPage() {
  const { portfolio, error, isLoading, retry } = useWorkPortfolio()
  const [changeFilter, setChangeFilter] = useState('')
  const [attentionFilter, setAttentionFilter] = useState<WorkItemAttention | ''>('')
  const deferredChange = useDeferredValue(changeFilter)
  const deferredAttention = useDeferredValue(attentionFilter)
  const items = portfolio.items.map((item) => item.card)
  const changes = [...new Set(items.map((item) => item.change_id))].sort()
  const filteredItems = items.filter(
    (item) => (!deferredChange || item.change_id === deferredChange)
      && (!deferredAttention || item.attention === deferredAttention),
  )

  return (
    <main className="min-h-dvh min-w-0 bg-canvas text-primary" data-testid="work-portfolio-page">
      <div className="mx-auto flex w-full max-w-[1440px] flex-col gap-static-lg px-static-md py-static-lg md:px-static-xl">
        <PortfolioHeader counts={portfolio.attention_counts} />
        <PortfolioFilters
          changes={changes}
          changeFilter={changeFilter}
          attentionFilter={attentionFilter}
          shown={filteredItems.length}
          total={items.length}
          onChangeFilter={setChangeFilter}
          onAttentionFilter={setAttentionFilter}
        />

        {isLoading ? <p role="status">Loading work portfolio...</p> : null}
        {error ? (
          <section className="flex flex-wrap items-center gap-static-sm border-l-4 border-danger bg-surface p-static-md" role="alert">
            <PIcon name="error" aria-hidden="true" />
            <span className="min-w-0 flex-1">Work portfolio is unavailable. {error.message}</span>
            <PButton type="button" variant="secondary" onClick={retry}>Retry portfolio</PButton>
          </section>
        ) : null}

        {!isLoading && !error ? <PortfolioWorkspace items={filteredItems} onChanged={retry} /> : null}
      </div>
    </main>
  )
}
