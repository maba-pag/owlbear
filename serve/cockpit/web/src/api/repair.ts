import { getResponseErrorMessage } from './errorMessage'

export interface RepairOutcome {
  task_id: number | null
  file_path: string
  code: string
  action: 'fixed' | 'removed' | 'moved' | 'quarantined' | 'skipped' | 'failed' | 'unresolved'
  detail: string | null
}

export interface TaskRepairHealthResult {
  findings: Array<Record<string, unknown>>
  repairable_count: number
  checked_paths: string[]
}

export interface WorkspaceRepairResponse {
  status: 'completed'
  started_at: string
  completed_at: string
  removed_count: number
  moved_count: number
  quarantined_count: number
  skipped_count: number
  failed_count: number
  unresolved_count: number
  outcomes: RepairOutcome[]
  unresolved_findings: Array<Record<string, unknown>>
  task_health_result: TaskRepairHealthResult | null
}

export async function repairWorkspace(): Promise<WorkspaceRepairResponse> {
  const response = await fetch('/health/tasks/repair', { method: 'POST' })
  if (!response.ok) {
    throw new Error(await getResponseErrorMessage(response, `Repair request failed with status ${response.status}`))
  }
  return (await response.json()) as WorkspaceRepairResponse
}
