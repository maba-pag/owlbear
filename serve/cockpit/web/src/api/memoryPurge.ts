import { getResponseErrorMessage } from './errorMessage'

export interface MemoryPurgePreview {
  deleted_total: number
  eligible: number
  too_recent: number
}

export interface MemoryPurgeReceipt {
  purged: number
  skipped: number
  failed: number
}

async function postPurge<T>(url: string, minAgeDays: number): Promise<T> {
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ min_age_days: minAgeDays }),
  })
  if (!response.ok) {
    throw new Error(await getResponseErrorMessage(response, `Memory purge request failed with status ${response.status}`))
  }
  return (await response.json()) as T
}

export function previewMemoryPurge(minAgeDays: number): Promise<MemoryPurgePreview> {
  return postPurge<MemoryPurgePreview>('/api/memories/purge/preview', minAgeDays)
}

export function purgeMemories(minAgeDays: number): Promise<MemoryPurgeReceipt> {
  return postPurge<MemoryPurgeReceipt>('/api/memories/purge', minAgeDays)
}
