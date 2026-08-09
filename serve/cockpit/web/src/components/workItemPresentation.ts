import type { DeliveryWorkerRole, WorkItemCardView, WorkItemStage } from '../api/workItems'

export const PROGRESS_STAGE_LABELS: Record<WorkItemStage, string> = {
  design: 'Design',
  planning: 'Planning',
  implementation: 'Implementation',
  assembly: 'Assembly',
  completed: 'Completed',
}

const WORKER_STATUS_LABELS: Record<DeliveryWorkerRole, string> = {
  planner: 'Planner working',
  builder: 'Builder working',
  'assembly-reviewer': 'Assembly reviewer working',
  'integration-repairer': 'Integration repairer working',
}

export function workItemStatusLabel(item: WorkItemCardView): string {
  if (item.needs === 'you') return item.needs_headline ?? 'Needs your intervention'
  if (item.needs === 'dependency') return item.needs_headline ?? 'Waiting on a dependency'
  if (item.activity.state === 'working' || item.activity.state === 'repairing') {
    return item.activity.worker_role ? WORKER_STATUS_LABELS[item.activity.worker_role] : 'Agent working'
  }
  if (item.activity.state === 'ready') {
    if (item.action.kind === 'retry-integration') return 'Ready for Integration retry'
    return item.activity.worker_role === 'integration-repairer'
      ? 'Ready for Integration repair'
      : 'Waiting for Orchestration'
  }
  if (item.stage === 'completed') return 'Done'
  return 'No active work'
}

export function hasOptionalManualAction(item: WorkItemCardView): boolean {
  return item.needs === 'none'
    && item.next_actor === 'agent'
    && (item.action.kind === 'integrate-change' || item.action.kind === 'retry-integration')
}

export function canHandOffIntegration(item: WorkItemCardView): boolean {
  const attention = item.integration_attention
  return item.scope === 'change-integration'
    && item.needs === 'you'
    && attention?.disposition === 'operator-required'
    && !attention.superseded
}

export function integrationHandoffPrompt(item: WorkItemCardView): string {
  const attention = item.integration_attention
  if (!attention) return ''
  return `/resolve-delivery-attention ${item.change_id} ${attention.attention_id}`
}
