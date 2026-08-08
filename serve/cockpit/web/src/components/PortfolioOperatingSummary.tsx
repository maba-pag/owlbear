import { WorkspaceHeaderMetric } from './WorkspaceHeader'
import type { PortfolioGuidance, PortfolioOperatingView } from '../api/workItems'

function countLabel(count: number, singular: string, plural = `${singular}s`) {
  return `${count} ${count === 1 ? singular : plural}`
}

function guidanceText(guidance: PortfolioGuidance) {
  switch (guidance.kind) {
    case 'intervene':
      return `Review ${countLabel(guidance.work_count, 'intervention')}.`
    case 'resume-design':
      return `Resume ${guidance.change_ids.map((changeId) => `/design ${changeId}`).join(' or ')}.`
    case 'start-orchestration':
      return 'Start /orchestrate.'
    case 'work-underway':
      return 'Let the current /orchestrate session continue.'
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
    <div className="min-w-0 text-sm leading-relaxed" aria-label="Recommended next steps">
      <span className="mr-static-xs font-semibold">Session</span>
      {operating.guidance.map((guidance, index) => (
        <span key={guidance.kind}>
          {index > 0 ? <span className="mx-static-xs text-contrast-medium" aria-hidden="true">·</span> : null}
          {guidanceText(guidance)}
        </span>
      ))}
    </div>
  )
}
