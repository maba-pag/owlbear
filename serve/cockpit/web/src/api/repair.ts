import { getResponseErrorMessage } from './errorMessage'
import type { WorkspaceModuleHealth } from '../hooks/useWorkspaceHealth'

export interface RepairOutcome {
  task_id: number | null
  file_path: string
  code: string
  action: 'fixed' | 'quarantined' | 'failed'
  detail: string | null
}

export interface WorkspaceRepairResponse {
  outcomes: RepairOutcome[]
  task_health_result: WorkspaceModuleHealth | null
}

export async function repairWorkspace(): Promise<WorkspaceRepairResponse> {
  const response = await fetch('/health/tasks/repair', { method: 'POST' })
  if (!response.ok) {
    throw new Error(await getResponseErrorMessage(response, `Repair request failed with status ${response.status}`))
  }
  return (await response.json()) as WorkspaceRepairResponse
}
