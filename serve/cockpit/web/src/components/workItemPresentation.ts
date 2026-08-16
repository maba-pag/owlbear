import type { DeliveryWorkerRole, WorkItemCardView, WorkItemStage } from '../api/workItems'

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

export function workItemStatus(item: WorkItemCardView): WorkItemStatusPresentation {
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
