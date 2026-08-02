export type WorkItemStage = 'design' | 'planning' | 'implementation' | 'assembly' | 'completed'
export type WorkItemAttention = 'user' | 'agent' | 'waiting' | 'none'

export interface WorkItemProjection {
  work_item_id: string
  change_id: string
  scope: string
  title: string
  promise: string
  stage: WorkItemStage
  attention: WorkItemAttention
  dependency_ready: boolean
  commitment_ids: string[]
  dependency_ids: string[]
  replacement_ids: string[]
  task_count: number
  reviewed_task_count: number
  next_action: string
}

export interface AttentionCounts {
  user: number
  agent: number
  waiting: number
  none: number
}

export interface WorkItemPortfolioResponse {
  items: WorkItemProjection[]
  attention_counts: AttentionCounts
}

export interface WorkItemDetailResponse {
  card: WorkItemProjection
  authority_identity: string
  commitments: Array<{
    commitment_id: string
    commitment_class: string
    provenance: string
    statement: string
  }>
  acceptance: string[]
  task_progress: Array<{
    scope_id: string
    task_count: number
    reviewed_task_count: number
  }>
  correction_history: Array<Record<string, unknown>>
  semantic_updates: Array<{
    update_id: string
    work_item_id: string
    rationale: string
    changed_commitment_ids: string[]
  }>
  completion_summary: {
    work_item_id: string
    satisfied_commitment_ids: string[]
    accepted_deviations: string[]
    known_limits: string[]
  } | null
  trace_links: {
    activity: string
    evidence: string
    requests: string
  }
}

export interface WorkItemTraceResponse {
  activity: Array<Record<string, unknown>>
  evidence: Array<Record<string, unknown>>
}

export interface WorkItemRequestsResponse {
  requests: Array<Record<string, unknown>>
}

export interface CreateWorkItemRequestBody {
  request_id: string
  authority_digest: string
  commitment_id: string
  task_id: string | null
  created_at: string
  summary: string
}

interface WorkItemRequestOptions extends RequestInit {
  fallbackCode: string
}

export class WorkItemApiError extends Error {
  readonly status: number
  readonly code: string

  constructor(status: number, code: string, detail: string) {
    super(detail)
    this.name = 'WorkItemApiError'
    this.status = status
    this.code = code
  }
}

async function workItemRequest<T>(url: string, options: WorkItemRequestOptions): Promise<T> {
  const response = await fetch(url, options)
  if (response.ok) {
    return response.json() as Promise<T>
  }
  const payload = await response.json().catch(() => ({})) as Record<string, unknown>
  const nested = typeof payload.detail === 'object' && payload.detail !== null
    ? payload.detail as Record<string, unknown>
    : payload
  throw new WorkItemApiError(
    response.status,
    typeof nested.code === 'string' ? nested.code : options.fallbackCode,
    typeof nested.detail === 'string' ? nested.detail : `Work item request failed with status ${response.status}`,
  )
}

function scopedUrl(path: string, changeId?: string): string {
  if (!changeId) return path
  const query = new URLSearchParams({ change_id: changeId })
  return `${path}?${query.toString()}`
}

export function listWorkItems(): Promise<WorkItemPortfolioResponse> {
  return workItemRequest('/api/work-items', { fallbackCode: 'ERR_WORK_ITEM_PORTFOLIO' })
}

export function showWorkItem(workItemId: string, changeId: string): Promise<WorkItemDetailResponse> {
  return workItemRequest(scopedUrl(`/api/work-items/${encodeURIComponent(workItemId)}`, changeId), {
    fallbackCode: 'ERR_WORK_ITEM_DETAIL',
  })
}

export function showWorkItemTrace(workItemId: string, changeId: string): Promise<WorkItemTraceResponse> {
  return workItemRequest(scopedUrl(`/api/work-items/${encodeURIComponent(workItemId)}/trace`, changeId), {
    fallbackCode: 'ERR_WORK_ITEM_TRACE',
  })
}

export function listWorkItemRequests(workItemId: string, changeId: string): Promise<WorkItemRequestsResponse> {
  return workItemRequest(scopedUrl(`/api/work-items/${encodeURIComponent(workItemId)}/requests`, changeId), {
    fallbackCode: 'ERR_WORK_ITEM_REQUESTS',
  })
}

export function createWorkItemRequest(
  workItemId: string,
  changeId: string,
  body: CreateWorkItemRequestBody,
): Promise<Record<string, unknown>> {
  return workItemRequest(scopedUrl(`/api/work-items/${encodeURIComponent(workItemId)}/requests`, changeId), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    fallbackCode: 'ERR_WORK_ITEM_REQUEST_CREATE',
  })
}
