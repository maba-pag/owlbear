export interface RepairOutcome {
  task_id: number | null
  file_path: string
  code: string
  action: 'fixed' | 'quarantined' | 'failed'
  detail: string | null
}

export async function repairStorage(): Promise<RepairOutcome[]> {
  try {
    const response = await fetch('/api/tasks/repair', { method: 'POST' })
    if (!response.ok) {
      throw new Error(`Repair request failed with status ${response.status}`)
    }
    return (await response.json()) as RepairOutcome[]
  } catch (error: unknown) {
    if (error instanceof Error) {
      throw error
    }
    const detail =
      typeof error === 'object' && error !== null
        ? JSON.stringify(error)
        : String(error)
    const wrappedError = new Error(`Repair request failed: ${detail}`) as Error & {
      cause?: unknown
    }
    wrappedError.cause = error
    throw wrappedError
  }
}
