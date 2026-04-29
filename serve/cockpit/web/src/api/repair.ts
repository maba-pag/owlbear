export interface RepairOutcome {
  task_id: number | null
  file_path: string
  code: string
  action: 'fixed' | 'quarantined' | 'failed'
  detail: string | null
}

export async function repairStorage(): Promise<RepairOutcome[]> {
  const response = await fetch('/api/tasks/repair', { method: 'POST' })
  if (!response.ok) {
    throw new Error(`Repair request failed with status ${response.status}`)
  }
  return (await response.json()) as RepairOutcome[]
}
