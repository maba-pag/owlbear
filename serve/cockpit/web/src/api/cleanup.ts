import { getResponseErrorMessage } from './errorMessage'

export interface SkippedCleanupItem {
  path: string
  reason: string
}

export interface CleanupResult {
  released_claim_ids: number[]
  archived_task_ids: number[]
  skipped_items: SkippedCleanupItem[]
}

export async function cleanupTasks(): Promise<CleanupResult> {
  const response = await fetch('/api/tasks/cleanup', { method: 'POST' })
  if (!response.ok) {
    const errorMessage = await getResponseErrorMessage(
      response,
      `Cleanup request failed with status ${response.status}`,
    )
    throw new Error(errorMessage)
  }
  return (await response.json()) as CleanupResult
}