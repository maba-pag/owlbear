import type {
  DeliveryReadinessChecksState,
  DeliveryReadinessReasonCode,
  DeliveryReadinessStatus,
  DeliveryWorkerRole,
  WorkItemCardView,
  WorkItemNextActor,
  WorkItemPublicationPhase,
  WorkItemStage,
} from '../api/workItems'

export const PROGRESS_STAGE_LABELS: Record<WorkItemStage, string> = {
  design: 'Design',
  planning: 'Planning',
  implementation: 'Implementation',
  completed: 'Completed',
}

export const READINESS_STATUS_LABELS: Record<DeliveryReadinessStatus, string> = {
  ready: 'Ready',
  running: 'Running',
  waiting: 'Waiting',
  blocked: 'Blocked',
  unavailable: 'Unavailable',
  complete: 'Complete',
}

export const READINESS_REASON_LABELS: Record<DeliveryReadinessReasonCode, string> = {
  ready: 'Delivery reports this operation is eligible now.',
  'active-custody': 'An active operation retains Change custody.',
  'finalization-failed': 'A recorded finalization diagnostic retains that attempt.',
  'claim-activation-failed': 'Delivery could not activate custody for the selected action.',
  'coordination-unavailable': 'This Change has no readable coordination record.',
  'execution-occupancy-unavailable': 'Delivery could not read current execution occupancy.',
  'engine-action-pending': 'An engine-owned action is acquired and not yet finished.',
  'engine-action-blocked': 'A retained engine action is blocked and keeps its custody.',
  'target-sync-required': 'The Change must be synchronized with its integration target first.',
  'claim-custody-unreconciled': 'Claim custody has not been reconciled with the workspace.',
  'runtime-unavailable': 'Delivery could not compose this Change runtime.',
  'dependency-wait': 'A dependency has not completed yet.',
  'request-action': 'An open request needs an answer first.',
  'change-paused': 'This Change is paused.',
  'change-terminal': 'This Change reached a terminal state.',
  'task-incomplete': 'Planned tasks are not complete yet.',
  'workspace-inspection-failed': 'Managed workspace readiness could not be observed.',
  'workspace-dirty': 'Managed workspace preflight is blocked by local changes.',
  'workspace-preflight-failed': 'Managed workspace preflight did not pass.',
  'review-repair': 'Review repair requires a new Change commit before verification.',
  'publication-wait': 'Publication is waiting on an external result.',
  'checkpoint-pending': 'A durable checkpoint is still pending.',
  'report-store-unavailable': 'Finalization diagnostics could not be read.',
}

/** Truthful check labels: absence of a run is never reported as a pass. */
export const READINESS_CHECKS_LABELS: Record<DeliveryReadinessChecksState, string> = {
  'not-run': 'Not run',
  failed: 'Failed',
  passed: 'Passed',
  unknown: 'Unknown',
}

export const NEXT_ACTOR_LABELS: Record<WorkItemNextActor, string> = {
  you: 'You',
  agent: 'Agent',
  dependency: 'Dependency',
  none: 'Nobody',
}

export function readinessTone(status: DeliveryReadinessStatus): WorkItemStatusTone {
  switch (status) {
    case 'ready':
      return 'ready'
    case 'running':
      return 'active'
    case 'waiting':
      return 'neutral'
    case 'blocked':
      return 'blocked'
    case 'unavailable':
      return 'attention'
    case 'complete':
      return 'complete'
  }
}

const WORKER_STATUS_LABELS: Record<DeliveryWorkerRole, string> = {
  planner: 'Planner',
  builder: 'Builder',
}

export type WorkItemStatusTone = 'attention' | 'blocked' | 'active' | 'ready' | 'complete' | 'neutral'

export interface WorkItemStatusPresentation {
  label: string
  tone: WorkItemStatusTone
  detail: string | null
}

function distinctDetail(label: string, detail: string | null): string | null {
  return detail && detail !== label ? detail : null
}

const PUBLICATION_PHASE_LABELS: Record<WorkItemPublicationPhase, string> = {
  'finalization-invalidated': 'Finalization invalidated',
  'review-repair': 'Review feedback needed',
  'ready-for-finalization': 'Ready for finalization',
  'checkpoint-pending': 'Checkpoint pending',
  'pull-request-draft': 'Delivery ready state not recorded',
  'awaiting-merge': 'Awaiting merge',
  'acceptance-observed': 'Acceptance observed',
  deferred: 'Change deferred',
  abandoned: 'Change abandoned',
}

function publicationStatus(item: WorkItemCardView): WorkItemStatusPresentation | null {
  if (item.scope !== 'change-publication' || !item.publication_phase) return null
  if (item.action.kind === 'resolve-attention' || item.action.kind === 'adopt-external-head') {
    return {
      label: 'Publication attention',
      tone: 'attention',
      detail: distinctDetail('Publication attention', item.needs_headline ?? item.next_step),
    }
  }
  if (item.publication_phase === 'pull-request-draft' && item.needs === 'you') {
    return {
      label: 'Publication needs reconciliation',
      tone: 'attention',
      detail: distinctDetail('Publication needs reconciliation', item.needs_headline ?? item.next_step),
    }
  }
  const phaseLabel = PUBLICATION_PHASE_LABELS[item.publication_phase]
  // Engine readiness owns the reported state; the lifecycle phase is identified separately.
  if (item.readiness) {
    return {
      label: READINESS_STATUS_LABELS[item.readiness.status],
      tone: readinessTone(item.readiness.status),
      detail: distinctDetail(READINESS_STATUS_LABELS[item.readiness.status], phaseLabel),
    }
  }
  const tone: WorkItemStatusTone = item.publication_phase === 'acceptance-observed'
    ? 'complete'
    : item.publication_phase === 'finalization-invalidated' || item.publication_phase === 'review-repair' || item.publication_phase === 'awaiting-merge'
      ? 'attention'
      : item.publication_phase === 'checkpoint-pending'
        ? 'active'
        : item.publication_phase === 'ready-for-finalization' || item.publication_phase === 'pull-request-draft'
          ? 'ready'
          : 'neutral'
  return {
    label: phaseLabel,
    tone,
    detail: distinctDetail(phaseLabel, item.needs_headline),
  }
}

export function workItemStatus(item: WorkItemCardView): WorkItemStatusPresentation {
  const publication = publicationStatus(item)
  if (publication) return publication
  if (item.readiness) {
    const label = READINESS_STATUS_LABELS[item.readiness.status]
    return {
      label,
      tone: readinessTone(item.readiness.status),
      detail: distinctDetail(label, item.needs_headline),
    }
  }
  if (item.needs === 'you') {
    return { label: 'Needs you', tone: 'attention', detail: item.needs_headline }
  }
  if (item.needs === 'dependency') {
    return { label: 'Blocked', tone: 'blocked', detail: item.needs_headline }
  }
  if (item.activity.state === 'working') {
    return {
      label: 'Working',
      tone: 'active',
      detail: item.activity.worker_role ? WORKER_STATUS_LABELS[item.activity.worker_role] : 'Agent',
    }
  }
  if (item.activity.state === 'ready') {
    return { label: 'Ready', tone: 'ready', detail: null }
  }
  if (item.stage === 'completed') {
    return { label: 'Complete', tone: 'complete', detail: null }
  }
  return { label: 'Idle', tone: 'neutral', detail: null }
}

export function workItemStatusClassName(tone: WorkItemStatusTone): string {
  switch (tone) {
    case 'attention':
      return 'border-error bg-error-low text-primary'
    case 'blocked':
      return 'border-warning bg-warning-low text-primary'
    case 'active':
      return 'border-info bg-info-low text-primary'
    case 'complete':
      return 'border-success bg-surface text-success'
    case 'ready':
      return 'border-contrast-low bg-surface text-primary'
    default:
      return 'border-contrast-low bg-surface text-contrast-medium'
  }
}

export function workItemStatusLabel(item: WorkItemCardView): string {
  return workItemStatus(item).label
}
