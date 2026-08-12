import type { DeliveryWorkerRole, WorkItemCardView, WorkItemStage } from '../api/workItems'

export const PROGRESS_STAGE_LABELS: Record<WorkItemStage, string> = {
  design: 'Design',
  planning: 'Planning',
  implementation: 'Implementation',
  completed: 'Completed',
}

const WORKER_STATUS_LABELS: Record<DeliveryWorkerRole, string> = {
  planner: 'Planner working',
  builder: 'Builder working',
}

export function workItemStatusLabel(item: WorkItemCardView): string {
  if (item.needs === 'you') return item.needs_headline ?? 'Needs your intervention'
  if (item.needs === 'dependency') return item.needs_headline ?? 'Waiting on a dependency'
  if (item.activity.state === 'working' || item.activity.state === 'repairing') {
    return item.activity.worker_role ? WORKER_STATUS_LABELS[item.activity.worker_role] : 'Agent working'
  }
  if (item.activity.state === 'ready') {
    return item.scope === 'change-publication' ? item.progress.label : 'Waiting for Orchestration'
  }
  if (item.stage === 'completed') return 'Done'
  return 'No active work'
}
