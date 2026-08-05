/**
 * Read-only workspace health projections. The Cockpit backend exposes one endpoint per module
 * (`/health/memory`, `/health/ideas`); there is no aggregate endpoint and no repair endpoint.
 */

export interface MemoryHealthFinding {
  path?: string
  code?: string
  detail?: string
  repairable?: boolean
}

export interface MemoryHealthResponse {
  status: string
  findings?: MemoryHealthFinding[]
  repairable_count?: number
  /** Problem paths only (unreadable and duplicate); never the full set of inspected files. */
  checked_paths?: string[]
}

export interface IdeasHealthResponse {
  status: string
  path: string
  detail?: string | null
}

export const MEMORY_HEALTH_URL = '/health/memory'
export const IDEAS_HEALTH_URL = '/health/ideas'
