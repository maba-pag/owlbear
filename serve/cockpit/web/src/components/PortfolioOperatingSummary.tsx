import { PIcon } from '@porsche-design-system/components-react'
import type {
  PortfolioGuidance,
  PortfolioOperatingView,
  WorkItemNeed,
  WorkItemPortfolioTotals,
} from '../api/workItems'
import CopyCommand from './CopyCommand'
import { designCommand } from './designWorkPresentation'

function countLabel(count: number, singular: string, plural = `${singular}s`) {
  return `${count} ${count === 1 ? singular : plural}`
}

function Command({ children }: { children: string }) {
  return (
    <span className="ml-static-sm inline-flex max-w-full items-center align-middle">
      <CopyCommand command={children} />
    </span>
  )
}

function Guidance({ guidance }: { guidance: PortfolioGuidance }) {
  switch (guidance.kind) {
    case 'intervene':
      return <>{guidance.work_count === 1 ? 'Review 1 item that needs you.' : `Review ${guidance.work_count} items that need you.`}</>
    case 'resume-design':
      return <>Continue Design with:{guidance.change_ids.map((changeId, index) => <span key={changeId}>{index > 0 ? ' or ' : null}<Command>{designCommand(changeId)}</Command></span>)}</>
    case 'start-orchestration':
      return <>Process {countLabel(guidance.work_count, 'queued work item')} with:<Command>/orchestrate</Command></>
    case 'work-underway':
      return <><Command>/orchestrate</Command> is already working; no new session is needed.</>
    case 'wait':
      return <>No session action needed.</>
    case 'create-change':
      return <>Start with:<Command>/ideate</Command> or <Command>/design &lt;change-id&gt;</Command></>
  }
}

interface PortfolioHeaderSummaryProps {
  operating: PortfolioOperatingView
  totals: WorkItemPortfolioTotals
  needsFilter: WorkItemNeed | ''
  onNeedsFilter: (value: WorkItemNeed | '') => void
}

interface AttentionMetricProps {
  count: number
  filter: Exclude<WorkItemNeed, 'none'>
  icon: 'warning' | 'clock' | 'wrench'
  label: string
  selected: boolean
  onSelect: (value: WorkItemNeed | '') => void
}

function AttentionMetric({ count, filter, icon, label, selected, onSelect }: AttentionMetricProps) {
  const content = (
    <>
      <PIcon name={icon} size="x-small" color="inherit" aria-hidden="true" />
      <strong className="font-semibold tabular-nums">{count}</strong>
      <span>{label}</span>
    </>
  )
  const tone = filter === 'you'
    ? 'border-error bg-error-low text-error'
    : 'border-warning bg-warning-low text-primary'

  if (count === 0) {
    return (
      <span
        data-testid={`portfolio-attention-${filter}`}
        className="inline-flex min-h-8 items-center gap-1.5 whitespace-nowrap rounded-sm border border-transparent px-static-xs py-1 text-xs font-semibold leading-none text-contrast-medium"
      >
        {content}
      </span>
    )
  }

  return (
    <button
      type="button"
      data-testid={`portfolio-attention-${filter}`}
      className={[
        'inline-flex min-h-8 items-center gap-1.5 whitespace-nowrap rounded-sm border px-static-xs py-1 text-xs font-semibold leading-none transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus',
        tone,
        selected ? 'outline outline-2 outline-offset-1 outline-focus' : '',
      ].join(' ')}
      aria-label={`Filter to ${count} ${count === 1 ? 'work item' : 'work items'}: ${label}`}
      aria-pressed={selected}
      onClick={() => onSelect(selected ? '' : filter)}
    >
      {content}
    </button>
  )
}

function ActivityMetric({ count, icon, label }: { count: number; icon: 'play' | 'list'; label: string }) {
  return (
    <span
      data-testid={`portfolio-activity-${label.toLowerCase()}`}
      className={[
        'inline-flex items-center gap-1.5 whitespace-nowrap tabular-nums',
        count === 0 ? 'text-contrast-medium' : 'text-primary',
      ].join(' ')}
    >
      <PIcon name={icon} size="x-small" color="inherit" aria-hidden="true" />
      <strong className="text-sm font-semibold leading-none">{count}</strong>
      <span className="text-xs leading-none">{label}</span>
    </span>
  )
}

export function PortfolioHeaderSummary({ operating, totals, needsFilter, onNeedsFilter }: PortfolioHeaderSummaryProps) {
  const designCount = operating.statuses.filter((status) => status.stage === 'design').length
  const deliveryCount = operating.statuses.filter((status) => status.admission === 'admitted' && status.stage !== 'design').length
  const currentChangeCount = operating.statuses.length
  const runningCount = totals.activity.working

  return (
    <>
      <div
        className="flex min-w-0 flex-wrap items-baseline gap-x-static-md gap-y-static-xs"
        role="group"
        aria-label="Portfolio inventory"
        data-testid="portfolio-inventory-summary"
      >
        <span className="inline-flex items-baseline gap-1.5 whitespace-nowrap text-xs text-primary">
          <strong className="text-lg font-semibold leading-none tabular-nums">{currentChangeCount}</strong>
          <span>Changes</span>
        </span>
        <span className="inline-flex items-baseline gap-static-xs whitespace-nowrap text-xs text-contrast-medium">
          <strong className="font-semibold tabular-nums text-primary">{designCount}</strong>
          <span>Design</span>
          <span className="text-contrast-low" aria-hidden="true">·</span>
          <strong className="font-semibold tabular-nums text-primary">{deliveryCount}</strong>
          <span>Delivery</span>
        </span>
      </div>
      <div
        className="flex min-w-0 flex-wrap items-center gap-x-static-md gap-y-static-xs border-t border-contrast-low pt-static-xs sm:translate-y-0.5 sm:self-center sm:border-l sm:border-t-0 sm:pl-static-md sm:pt-0"
        role="group"
        aria-label="Work item status"
        data-testid="portfolio-work-summary"
      >
        <div className="flex flex-wrap items-center gap-static-xs" role="group" aria-label="Attention">
          <AttentionMetric count={totals.needs.you} filter="you" icon="warning" label="Needs you" selected={needsFilter === 'you'} onSelect={onNeedsFilter} />
          <AttentionMetric count={totals.needs.dependency} filter="dependency" icon="clock" label="Blocked" selected={needsFilter === 'dependency'} onSelect={onNeedsFilter} />
        </div>
        <div className="flex items-center gap-static-md" role="group" aria-label="Activity">
          <ActivityMetric count={runningCount} icon="play" label="Running" />
          <ActivityMetric count={totals.activity.ready} icon="list" label="Ready" />
        </div>
      </div>
    </>
  )
}

export default function PortfolioOperatingSummary({ operating }: { operating: PortfolioOperatingView }) {
  if (operating.guidance.length === 0) return null
  return (
    <aside className="grid min-w-0 gap-static-xs px-static-sm text-sm leading-relaxed text-contrast-medium sm:grid-cols-[auto_minmax(0,1fr)] sm:items-start sm:gap-static-md" aria-label="Session suggestions">
      <strong className="text-primary">Session suggestions</strong>
      <ul className="m-0 flex min-w-0 flex-wrap items-center gap-x-static-xl gap-y-static-xs p-0">
        {operating.guidance.map((guidance) => <li className="min-w-0" key={guidance.kind}><Guidance guidance={guidance} /></li>)}
      </ul>
    </aside>
  )
}
