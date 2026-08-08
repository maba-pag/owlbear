import { WorkspaceHeaderMetric } from './WorkspaceHeader'
import type { PortfolioGuidance, PortfolioOperatingView } from '../api/workItems'

function countLabel(count: number, singular: string, plural = `${singular}s`) {
  return `${count} ${count === 1 ? singular : plural}`
}

function guidanceText(guidance: PortfolioGuidance) {
  switch (guidance.kind) {
    case 'intervene':
      return `Review ${countLabel(guidance.work_count, 'item')} that needs you.`
    case 'resume-design':
      return `Continue Design for ${guidance.change_ids.join(' or ')} with ${guidance.change_ids.map((changeId) => `/design ${changeId}`).join(' or ')}.`
    case 'start-orchestration':
      return `Start /orchestrate for ${countLabel(guidance.work_count, 'queued item')}.`
    case 'work-underway':
      return '/orchestrate is already working; no new session is needed.'
    case 'wait':
      return 'No session action needed.'
    case 'create-change':
      return 'Start /ideate or /design <change-id>.'
  }
}

export function PortfolioHeaderSummary({ operating }: { operating: PortfolioOperatingView }) {
  return (
    <>
      <WorkspaceHeaderMetric
        value={operating.unfinished_change_count}
        label={operating.unfinished_change_count === 1 ? 'unfinished Change' : 'unfinished Changes'}
      />
      {operating.claimed.length > 0 ? (
        <WorkspaceHeaderMetric value={operating.claimed.length} label="being worked on" />
      ) : null}
      {operating.queued_for_orchestration.length > 0 ? (
        <WorkspaceHeaderMetric value={operating.queued_for_orchestration.length} label="waiting for Orchestration" />
      ) : null}
      <WorkspaceHeaderMetric
        value={operating.interventions.length}
        label="need you"
        tone={operating.interventions.length > 0 ? 'error' : 'neutral'}
      />
    </>
  )
}

export default function PortfolioOperatingSummary({ operating }: { operating: PortfolioOperatingView }) {
  if (operating.guidance.length === 0) return null
  return (
    <aside className="min-w-0 text-sm leading-relaxed text-contrast-medium" aria-label="Session suggestions">
      <span className="mr-static-xs font-semibold text-primary">Session suggestions</span>
      {operating.guidance.map((guidance) => <span className="mr-static-sm" key={guidance.kind}>{guidanceText(guidance)}</span>)}
    </aside>
  )
}
