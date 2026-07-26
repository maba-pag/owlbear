export const CANDIDATE_REVISION = 'HEAD' as const

export type NativeResource =
  | 'changes'
  | 'graphs'
  | 'receipts'
  | 'jobs'
  | 'attempts'
  | 'findings'
  | 'requests'

export interface NativeChangedEvent {
  resources: NativeResource[]
  token: string
}

export interface NativeJob {
  schema_version: number
  job_id: number
  kind: 'plan' | 'build' | 'accept' | 'audit' | 'supersession'
  priority: number
  created_at: string
  updated_at: string
  change_id: string
  delivery_digest: string
  target_node_id: string
  disposition: 'pending' | 'cancelled' | 'superseded'
  claim_id: string | null
  attempt_id: string | null
  pending_request_ids: string[]
  predecessor_job_ids: number[]
  receipt_id: string | null
}

export interface StoredNativeJob {
  job: NativeJob
  token: string
}

export interface NativeJobProjection {
  job_id: number
  token: string
  kind: NativeJob['kind']
  priority: number
  change_id: string
  delivery_digest: string
  target_node_id: string
  title: string
  outcome: string
  acceptance: string[]
  modules: string[]
  interfaces: string[]
  proof: string
  dependency_ready: boolean
  claim_id: string | null
  disposition: NativeJob['disposition']
  requests: NativeStoredRequest[]
  block_id: string | null
  attempt: NativeAttempt | null
  finding: NativeFinding | null
  receipt: NativeReceipt | null
  validity: NativeReceiptValidity | null
}

export interface NativeJobDetail {
  job: NativeJob
  token: string
  title: string
  outcome: string
  acceptance: string[]
  modules: string[]
  interfaces: string[]
  proof: string
}

export interface NativePage<T> {
  items: T[]
  next_cursor: string | null
}

export interface NativeConflictDetail {
  code: string
  detail?: string
  message?: string
  current_delivery_digest?: string
  target?: string
  token?: string
  current?: StoredNativeJob | Record<string, unknown>
  lower_code?: string
  validation?: unknown[]
}

export interface NativeRequestRecord {
  request_id: string
  kind: string
  title: string
  summary: string
  body: string
  agent: string
  created_at: string
  change_id: string
  delivery_digest: string
  target_node_id: string | null
  job_ids: number[]
  evidence?: string[]
  resume_condition?: string | null
  options?: Array<{
    option_id: string
    label: string
    recommended: boolean
    confidence: number
    rationale: string
    pros: string[]
    cons: string[]
    risks: string[]
  }>
}

export interface NativeStoredRequest {
  request: NativeRequestRecord
  resolution: {
    request_id: string
    disposition: 'local' | 'material'
    resolved_at: string
    resolved_by: string
    selected_option_id: string | null
    response: string | null
    rationale: string
  } | null
}

export interface NativeAttempt {
  attempt_id: string
  claim_id: string
  job_id: number
  actor_id: string
  process_id: string
  timestamp: string
  kind: string
  [key: string]: unknown
}

export interface NativeFinding {
  finding_id: string
  created_at: string
  [key: string]: unknown
}

export interface NativeReceipt {
  receipt_id: string
  kind: string
  issued_at: string
  [key: string]: unknown
}

export interface NativeReceiptValidity {
  code: string
  detail: string
  [key: string]: unknown
}

export interface NativeActivityEntry {
  identity: string
  timestamp: string
  kind: string
  [key: string]: unknown
}

export interface NativeChangeList {
  changes: Array<{
    change_id: string
    state: 'loaded' | 'invalid'
    delivery_digest: string | null
    diagnostics: Array<{ code: string; detail: string; target: string | null }>
  }>
}

export interface NativeChangeDetail {
  change_id: string
  delivery_digest: string
  intent: string
  design: string
  decisions: Record<string, unknown>
  graph: Record<string, unknown>
}

export interface NativeGraphDetail {
  change_id: string
  delivery_digest: string
  graph: {
    schema_version: number
    change_id: string
    state: string
    authority: { intent: string; design: string; decisions: string; research: string[] }
    admission: Record<string, unknown> | null
    requirements: Array<Record<string, unknown>>
    negative_requirements: Array<Record<string, unknown>>
    preserved_behaviors: Array<Record<string, unknown>>
    workflows: Array<Record<string, unknown>>
    modules: Array<Record<string, unknown>>
    nodes: NativeDeliveryNode[]
    interfaces: NativeInterfaceContract[]
    migrations: NativeMigrationContract[]
    risks: Array<Record<string, unknown>>
    proofs: Array<Record<string, unknown>>
    [key: string]: unknown
  }
  plans: Record<string, NativeNodePlan>
}

export interface NativeDeliveryNode {
  id: string
  title: string
  outcome: string
  owns: string[]
  supports: string[]
  modules: string[]
  produces: string[]
  consumes: string[]
  dependencies: string[]
  risks: string[]
  proof: string
}

export interface NativeInterfaceContract {
  id: string
  migration: string | null
  [key: string]: unknown
}

export interface NativeMigrationContract {
  id: string
  title: string
  [key: string]: unknown
}

export interface NativeNodePlan {
  packets: Array<{
    id: string
    dependencies: string[]
    impact_closure: { paths: string[]; authority_targets: string[] }
  }>
}

export interface NativeHealthPage<TFinding = Record<string, unknown>> {
  findings: TFinding[]
  checked_paths: string[]
  next_cursor: string | null
}

export interface NativeInvalidationDetail {
  invalidation_id: string
  supersession_receipt_id: string
  issued_at: string
  affected_receipt_ids: string[]
  corrective_finding_ids: string[]
  corrective_job_ids: number[]
  [key: string]: unknown
}

export interface LegacyInventory {
  tasks: unknown[]
  requests: unknown[]
  activity: unknown[]
  [key: string]: unknown
}

export class NativeApiError extends Error {
  readonly status: number
  readonly code: string
  readonly detail: string
  readonly serverMessage?: string
  readonly currentDeliveryDigest?: string
  readonly target?: string
  readonly token?: string
  readonly current?: StoredNativeJob | Record<string, unknown>
  readonly lowerCode?: string
  readonly validation: unknown[]

  constructor(status: number, payload: NativeConflictDetail) {
    const detail = payload.detail ?? payload.message ?? `Native request failed with status ${status}`
    super(detail)
    this.name = 'NativeApiError'
    this.status = status
    this.code = payload.code
    this.detail = detail
    this.serverMessage = payload.message
    this.currentDeliveryDigest = payload.current_delivery_digest
    this.target = payload.target
    this.token =
      payload.token ??
      (payload.current && typeof payload.current.token === 'string' ? payload.current.token : undefined)
    this.current = payload.current
    this.lowerCode = payload.lower_code
    this.validation = payload.validation ?? []
  }
}

interface NativeRequestOptions extends RequestInit {
  fallbackCode?: string
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function readConflict(payload: unknown, fallbackCode: string): NativeConflictDetail {
  if (isRecord(payload) && Array.isArray(payload.detail)) {
    return { code: fallbackCode, detail: 'Request validation failed', validation: payload.detail }
  }
  const wrapped = isRecord(payload) && isRecord(payload.detail) ? payload.detail : payload
  if (!isRecord(wrapped)) {
    return { code: fallbackCode }
  }

  const current = isRecord(wrapped.current) ? wrapped.current : undefined
  return {
    code: typeof wrapped.code === 'string' ? wrapped.code : fallbackCode,
    detail: typeof wrapped.detail === 'string' ? wrapped.detail : undefined,
    message: typeof wrapped.message === 'string' ? wrapped.message : undefined,
    current_delivery_digest:
      typeof wrapped.current_delivery_digest === 'string' ? wrapped.current_delivery_digest : undefined,
    target: typeof wrapped.target === 'string' ? wrapped.target : undefined,
    token:
      typeof wrapped.token === 'string'
        ? wrapped.token
        : current && typeof current.token === 'string'
          ? current.token
          : undefined,
    current,
    lower_code: typeof wrapped.lower_code === 'string' ? wrapped.lower_code : undefined,
  }
}

async function nativeRequest<T>(url: string, options: NativeRequestOptions = {}): Promise<T> {
  const response = await fetch(url, options)
  if (!response.ok) {
    let payload: unknown
    try {
      payload = await response.json()
    } catch {
      payload = undefined
    }
    throw new NativeApiError(response.status, readConflict(payload, options.fallbackCode ?? 'ERR_NATIVE_REQUEST'))
  }
  return (await response.json()) as T
}

function pageUrl(path: string, cursor?: string, limit = 100): string {
  const params = new URLSearchParams({ limit: String(limit) })
  if (cursor) {
    params.set('cursor', cursor)
  }
  return `${path}?${params.toString()}`
}

export function listNativeJobs(changeId: string, cursor?: string, limit = 100): Promise<NativePage<NativeJobProjection>> {
  const params = new URLSearchParams({ candidate_revision: CANDIDATE_REVISION, limit: String(limit) })
  if (cursor) {
    params.set('cursor', cursor)
  }
  return nativeRequest(`/api/changes/${encodeURIComponent(changeId)}/jobs?${params.toString()}`)
}

export function getNativeJob(changeId: string, jobId: number): Promise<NativeJobDetail> {
  return nativeRequest(`/api/changes/${encodeURIComponent(changeId)}/jobs/${jobId}`)
}

export const listNativeChanges = (): Promise<NativeChangeList> => nativeRequest('/api/changes')

export const getNativeChange = (changeId: string): Promise<NativeChangeDetail> =>
  nativeRequest(`/api/changes/${encodeURIComponent(changeId)}`)

export const getNativeGraph = (changeId: string): Promise<NativeGraphDetail> =>
  nativeRequest(`/api/changes/${encodeURIComponent(changeId)}/graph`)

export const listNativeRequests = (changeId: string, cursor?: string): Promise<NativePage<NativeStoredRequest>> =>
  nativeRequest(pageUrl(`/api/changes/${encodeURIComponent(changeId)}/requests`, cursor))

export const getNativeRequest = (changeId: string, requestId: string): Promise<NativeStoredRequest> =>
  nativeRequest(`/api/changes/${encodeURIComponent(changeId)}/requests/${encodeURIComponent(requestId)}`)

export const listNativeAttempts = (changeId: string, cursor?: string): Promise<NativePage<NativeAttempt>> =>
  nativeRequest(pageUrl(`/api/changes/${encodeURIComponent(changeId)}/attempts`, cursor))

export const listNativeFindings = (changeId: string, cursor?: string): Promise<NativePage<NativeFinding>> =>
  nativeRequest(pageUrl(`/api/changes/${encodeURIComponent(changeId)}/findings`, cursor))

export const listNativeReceipts = (changeId: string, cursor?: string): Promise<NativePage<NativeReceipt>> =>
  nativeRequest(pageUrl(`/api/changes/${encodeURIComponent(changeId)}/receipts`, cursor))

export const listNativeActivity = (changeId: string, cursor?: string): Promise<NativePage<NativeActivityEntry>> =>
  nativeRequest(pageUrl(`/api/changes/${encodeURIComponent(changeId)}/activity`, cursor))

export const getNativeInvalidation = (changeId: string, receiptId: string): Promise<NativeInvalidationDetail> =>
  nativeRequest(`/api/changes/${encodeURIComponent(changeId)}/invalidations/${encodeURIComponent(receiptId)}`)

export const getNativeWorkHealth = (changeId: string, cursor?: string): Promise<NativeHealthPage> =>
  nativeRequest(pageUrl(`/api/changes/${encodeURIComponent(changeId)}/health/work`, cursor))

export const getNativeChangeHealth = (changeId: string, cursor?: string): Promise<NativeHealthPage> =>
  nativeRequest(pageUrl(`/api/changes/${encodeURIComponent(changeId)}/health/change`, cursor))

export const getLegacyInventory = (): Promise<LegacyInventory> => nativeRequest('/api/legacy')

export interface SetJobPriorityInput {
  job_id: number
  delivery_digest: string
  expected_token: string
  priority: number
  updated_at: string
}

export interface CancelJobInput {
  job_id: number
  delivery_digest: string
  expected_token: string
  cancelled_at: string
}

export interface ReleaseJobInput {
  job_id: number
  delivery_digest: string
  attempt_id: string
  claim_id: string
  actor_id: string
  process_id: string
  released_at: string
}

export interface ResolveNativeRequestInput {
  delivery_digest: string
  disposition: 'local' | 'material'
  resolved_at: string
  resolved_by: string
  selected_option_id?: string | null
  response?: string | null
  rationale: string
}

export interface ResolveNativeRequestResult {
  request: NativeStoredRequest
  resumed_jobs: StoredNativeJob[]
  resume: { disposition: 'resume-linked-jobs'; request_id: string; target_node_id: string | null; job_ids: number[] } | null
  design_reentry: {
    disposition: 'design-reentry'
    request_id: string
    change_id: string
    delivery_digest: string
    target_node_id: string | null
    job_ids: number[]
  } | null
}

export function setNativeJobPriority(changeId: string, input: SetJobPriorityInput): Promise<{ job: StoredNativeJob }> {
  return nativeRequest(`/api/changes/${encodeURIComponent(changeId)}/jobs/${input.job_id}/priority`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  })
}

export function cancelNativeJob(changeId: string, input: CancelJobInput): Promise<{ job: StoredNativeJob }> {
  return nativeRequest(`/api/changes/${encodeURIComponent(changeId)}/jobs/${input.job_id}/cancel`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  })
}

export function releaseNativeJob(changeId: string, input: ReleaseJobInput): Promise<{ job: StoredNativeJob }> {
  const { job_id: jobId, ...body } = input
  return nativeRequest(`/api/changes/${encodeURIComponent(changeId)}/jobs/${jobId}/release`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export function resolveNativeRequest(
  changeId: string,
  requestId: string,
  input: ResolveNativeRequestInput,
): Promise<ResolveNativeRequestResult> {
  return nativeRequest(
    `/api/changes/${encodeURIComponent(changeId)}/requests/${encodeURIComponent(requestId)}/resolve`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(input),
    },
  )
}
