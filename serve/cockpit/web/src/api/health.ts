/** Workspace health projections for persisted workspace surfaces. */

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
