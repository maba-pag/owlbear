/**
 * Workspace health projections and the explicit Delivery expired-claim maintenance operation.
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

export interface DeliveryClaimRecovery {
  status: 'recovered' | 'attention'
  change_id: string
  outcome_id: string
  attempt_id: string
  claim_id: string
  attention?: {
    reason: string
    retry_condition: string
  } | null
}

export interface DeliveryExpiredClaimRecoveryResponse {
  recoveries: DeliveryClaimRecovery[]
  repair_recoveries: Array<{ change_id: string; attempt_id: string; claim_id: string }>
}

export const MEMORY_HEALTH_URL = '/health/memory'
export const IDEAS_HEALTH_URL = '/health/ideas'
export const DELIVERY_EXPIRED_CLAIMS_URL = '/api/work-items/claims/recover-expired'
