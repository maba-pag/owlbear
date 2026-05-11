import { getResponseErrorMessage } from './errorMessage'

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
      const errorMessage = await getResponseErrorMessage(
        response,
        `Repair request failed with status ${response.status}`,
      )
      throw new Error(errorMessage)
    }
    return (await response.json()) as RepairOutcome[]
  } catch (error: unknown) {
    if (error instanceof Error) {
      throw error
    }
    let detail: string
    if (typeof error === 'object' && error !== null) {
      try {
        detail = JSON.stringify(error) ?? '[unserializable object]'
      } catch {
        detail = '[unserializable object]'
      }
    } else {
      detail = String(error)
    }
    const wrappedError = new Error(`Repair request failed: ${detail}`) as Error & {
      cause?: unknown
    }
    wrappedError.cause = error
    throw wrappedError
  }
}

