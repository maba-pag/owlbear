import { WorkspaceHeaderMetric } from './WorkspaceHeader'
import type { PortfolioGuidance, PortfolioOperatingView } from '../api/workItems'

function countLabel(count: number, singular: string, plural = `${singular}s`) {
  return `${count} ${count === 1 ? singular : plural}`
}

function pipelineStatement(operating: PortfolioOperatingView) {
  const designWorkCount = operating.draft_design_change_ids.length + operating.design_required_change_ids.length
  if (operating.unfinished_change_count === 0 && designWorkCount === 0) return 'No unfinished Design or Delivery work.'
  if (operating.claimed.length > 0) {
    const queue = operating.queued_for_orchestration.length > 0
      ? ` ${countLabel(operating.queued_for_orchestration.length, 'item')} waiting for Orchestration.`
      : ''
    return `Delivery is underway. ${countLabel(operating.claimed.length, 'item')} being worked on.${queue}`
  }
  if (operating.queued_for_orchestration.length > 0) {
    return `${countLabel(operating.queued_for_orchestration.length, 'item')} waiting for an Orchestration session.`
  }
  if (operating.interventions.length > 0) return 'Delivery is waiting for your intervention.'
  if (designWorkCount > 0) {
    return 'Design work exists, but no Delivery work is currently underway.'
  }
  return 'Work exists, but nothing can advance yet.'
}

function guidanceText(guidance: PortfolioGuidance) {
  switch (guidance.kind) {
    case 'intervene':
      return `${countLabel(guidance.work_count, 'intervention')} ${guidance.work_count === 1 ? 'requires' : 'require'} you before affected work can continue.`
    case 'resume-design':
      return `Resume ${guidance.change_ids.map((changeId) => `/design ${changeId}`).join(' or ')}.`
    case 'start-orchestration':
      return `Start /orchestrate. It can pick up ${countLabel(guidance.work_count, 'waiting item')}.`
    case 'work-underway':
      return 'Keep the current /orchestrate session running; it owns the portfolio queue.'
    case 'wait':
      return `${countLabel(guidance.work_count, 'item')} waiting on dependencies. No session needs starting.`
    case 'create-change':
      return 'Start /ideate to shape a new Change, or /design <change-id> to create one directly.'
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
  return (
    <section className="border-y border-contrast-low py-static-md" aria-labelledby="pipeline-heading">
      <p id="pipeline-heading" className="text-2xs font-semibold uppercase text-contrast-medium">Pipeline</p>
      <p className="mt-static-xs max-w-[72ch] text-lg font-semibold leading-snug">{pipelineStatement(operating)}</p>
      {operating.guidance.length > 0 ? (
        <div className="mt-static-md grid gap-static-xs border-t border-contrast-low pt-static-sm" aria-label="Recommended next steps">
          {operating.guidance.map((guidance) => (
            <p key={guidance.kind} className="text-sm leading-relaxed">
              {guidanceText(guidance)}
            </p>
          ))}
        </div>
      ) : null}
    </section>
  )
}
