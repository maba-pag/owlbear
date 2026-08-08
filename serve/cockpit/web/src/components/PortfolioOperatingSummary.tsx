import { WorkspaceHeaderMetric } from './WorkspaceHeader'
import type { PortfolioGuidance, PortfolioOperatingView } from '../api/workItems'
import CopyCommand from './CopyCommand'
import { designCommand } from './designWorkPresentation'

function countLabel(count: number, singular: string, plural = `${singular}s`) {
  return `${count} ${count === 1 ? singular : plural}`
}

function Command({ children }: { children: string }) {
  return <span className="mx-static-xs inline-flex max-w-full"><CopyCommand command={children} className="text-xs" /></span>
}

function Guidance({ guidance }: { guidance: PortfolioGuidance }) {
  switch (guidance.kind) {
    case 'intervene':
      return <>{guidance.work_count === 1 ? 'Review 1 item that needs you.' : `Review ${guidance.work_count} items that need you.`}</>
    case 'resume-design':
      return <>Continue Design with {guidance.change_ids.map((changeId, index) => <span key={changeId}>{index > 0 ? ' or ' : null}<Command>{designCommand(changeId)}</Command></span>)}.</>
    case 'start-orchestration':
      return <>Process {countLabel(guidance.work_count, 'queued work item')} with <Command>/orchestrate</Command>.</>
    case 'work-underway':
      return <><Command>/orchestrate</Command> is already working; no new session is needed.</>
    case 'wait':
      return <>No session action needed.</>
    case 'create-change':
      return <>Start with <Command>/ideate</Command> or <Command>/design &lt;change-id&gt;</Command>.</>
  }
}

export function PortfolioHeaderSummary({ operating }: { operating: PortfolioOperatingView }) {
  const designCount = operating.draft_design_change_ids.length + operating.design_required_change_ids.length
  const deliveryCount = Math.max(0, operating.unfinished_change_count - operating.design_required_change_ids.length)
  const currentChangeCount = operating.unfinished_change_count + operating.draft_design_change_ids.length

  return (
    <>
      <WorkspaceHeaderMetric
        value={currentChangeCount}
        label={currentChangeCount === 1 ? 'current Change' : 'current Changes'}
      />
      {designCount > 0 ? <WorkspaceHeaderMetric value={designCount} label="in Design" /> : null}
      {deliveryCount > 0 ? <WorkspaceHeaderMetric value={deliveryCount} label="in Delivery" /> : null}
      {operating.claimed.length > 0 ? (
        <WorkspaceHeaderMetric
          value={operating.claimed.length}
          label={operating.claimed.length === 1 ? 'work item active' : 'work items active'}
        />
      ) : null}
      {operating.queued_for_orchestration.length > 0 ? (
        <WorkspaceHeaderMetric
          value={operating.queued_for_orchestration.length}
          label={operating.queued_for_orchestration.length === 1 ? 'work item queued' : 'work items queued'}
        />
      ) : null}
      {operating.interventions.length > 0 ? (
        <WorkspaceHeaderMetric
          value={operating.interventions.length}
          label={operating.interventions.length === 1 ? 'work item needs you' : 'work items need you'}
          tone="error"
        />
      ) : null}
      {operating.dependency_waits.length > 0 ? (
        <WorkspaceHeaderMetric
          value={operating.dependency_waits.length}
          label={operating.dependency_waits.length === 1 ? 'work item waiting' : 'work items waiting'}
        />
      ) : null}
    </>
  )
}

export default function PortfolioOperatingSummary({ operating }: { operating: PortfolioOperatingView }) {
  if (operating.guidance.length === 0) return null
  return (
    <aside className="grid min-w-0 gap-static-xs px-static-sm text-sm leading-relaxed text-contrast-medium sm:grid-cols-[auto_minmax(0,1fr)] sm:items-start sm:gap-static-md" aria-label="Session suggestions">
      <strong className="text-primary">Session suggestions</strong>
      <ul className="m-0 flex min-w-0 list-none flex-wrap gap-x-static-lg gap-y-static-xs p-0">
        {operating.guidance.map((guidance) => <li key={guidance.kind}><Guidance guidance={guidance} /></li>)}
      </ul>
    </aside>
  )
}
