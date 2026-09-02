import type { DeliveryWorkerRole, WorkItemCardView, WorkItemPublicationPhase, WorkItemStage } from '../api/workItems'

export const PROGRESS_STAGE_LABELS: Record<WorkItemStage, string> = {
  design: 'Design',
  planning: 'Planning',
  implementation: 'Implementation',
  completed: 'Completed',
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
      detail: item.needs_headline ?? item.next_step,
    }
  }
  if (item.publication_phase === 'pull-request-draft' && item.needs === 'you') {
    return {
      label: 'Publication needs reconciliation',
      tone: 'attention',
      detail: item.needs_headline ?? item.next_step,
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
    label: PUBLICATION_PHASE_LABELS[item.publication_phase],
    tone,
    detail: item.needs_headline,
  }
}

export function workItemStatus(item: WorkItemCardView): WorkItemStatusPresentation {
  const publication = publicationStatus(item)
  if (publication) return publication
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
