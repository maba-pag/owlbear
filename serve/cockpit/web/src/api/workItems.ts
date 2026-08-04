export type WorkItemStage = 'design' | 'planning' | 'implementation' | 'assembly' | 'completed'
export type WorkItemAttention = 'user' | 'agent' | 'waiting' | 'none'
export type DeliveryWorkerRole = 'planner' | 'builder' | 'assembly-reviewer'

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

export interface WorkItemLinks {
  self: string
  answer_request: string
  clear_block: string
  recover_claim: string
  move_backward: string
  integration_attention: string
  integration_retry: string
}

export interface WorkItemSummaryResponse {
  card: WorkItemProjection
  links: WorkItemLinks
}

export interface AttentionCounts {
  user: number
  agent: number
  waiting: number
  none: number
}

export interface WorkItemPortfolioResponse {
  items: WorkItemSummaryResponse[]
  attention_counts: AttentionCounts
}

export interface DeliveryRequestResolution {
  selected_option_id: string | null
  response_text: string | null
}

export interface DeliveryRequest {
  request_id: string
  kind: 'decision' | 'action'
  outcome_id: string
  summary: string
  options: Array<{ option_id: string; label: string }>
  resolution: DeliveryRequestResolution | null
}

export interface DeliveryBlock {
  block_id: string
  reason: string
  unblock_condition: string
  expected_evidence: string[]
  locators: string[]
  request_id: string | null
  resolution_note: string | null
  resolution_locators: string[]
  resume_commit: string | null
}

export interface DeliveryOperatorContext {
  change_id: string
  outcome_id: string
  stage: WorkItemStage
  block: DeliveryBlock | null
  requests: DeliveryRequest[]
  active_claim: {
    attempt_id: string
    claim_id: string
    started_at: string
    worker_role: DeliveryWorkerRole
    task_id: string | null
  } | null
  return_context: {
    target: WorkItemStage
    reason: string
    locators: string[]
  } | null
  recovery_attention: {
    attempt_id: string
    claim_id: string
    reason: string
    custody_retained: boolean
    retry_condition: string
  } | null
  integration_attention: {
    code: string
    diagnostics: string[]
    retry_condition: string
  } | null
}

export interface WorkItemDetailResponse {
  operator: DeliveryOperatorContext
  links: WorkItemLinks
}

export interface BackwardMoveResult {
  move: {
    move_id: string
    outcome_id: string
    destination: WorkItemStage
    reason: string
    invalidated_outcome_ids: string[]
  }
  invalidated_outcome_ids: string[]
}

export interface CompletedChangeRecord {
  change_id: string
  completion_id: string
  completion_path: string
  package_id: string
  introducing_target_commit: string
  source_target_commit: string
  title: string
  semantic_summary: string
}

export interface CompletedChangePage {
  records: CompletedChangeRecord[]
  next_cursor: string | null
}

interface WorkItemRequestOptions extends RequestInit {
  fallbackCode: string
}

export class WorkItemApiError extends Error {
  readonly status: number
  readonly code: string
  readonly authority: string | null
  readonly retrySafe: boolean

  constructor(status: number, code: string, detail: string, authority: string | null, retrySafe: boolean) {
    super(detail)
    this.name = 'WorkItemApiError'
    this.status = status
    this.code = code
    this.authority = authority
    this.retrySafe = retrySafe
  }
}

async function workItemRequest<T>(url: string, options: WorkItemRequestOptions): Promise<T> {
  const response = await fetch(url, options)
  if (response.ok) return response.json() as Promise<T>
  const payload = await response.json().catch(() => ({})) as Record<string, unknown>
  const nested = typeof payload.detail === 'object' && payload.detail !== null
    ? payload.detail as Record<string, unknown>
    : payload
  throw new WorkItemApiError(
    response.status,
    typeof nested.code === 'string' ? nested.code : options.fallbackCode,
    typeof nested.detail === 'string' ? nested.detail : `Delivery request failed with status ${response.status}`,
    typeof nested.authority === 'string' ? nested.authority : null,
    nested.retry_safe === true,
  )
}

function controlRequest<T>(url: string, fallbackCode: string, body?: object): Promise<T> {
  return workItemRequest(url, {
    method: 'POST',
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
    fallbackCode,
  })
}

export function listWorkItems(): Promise<WorkItemPortfolioResponse> {
  return workItemRequest('/api/work-items', { fallbackCode: 'ERR_WORK_ITEM_PORTFOLIO' })
}

export function listCompletedChanges(cursor?: string): Promise<CompletedChangePage> {
  const query = cursor ? `?${new URLSearchParams({ cursor }).toString()}` : ''
  return workItemRequest(`/api/work-items/completed${query}`, { fallbackCode: 'ERR_COMPLETED_HISTORY' })
}

export function searchCompletedChanges(query: string, cursor?: string): Promise<CompletedChangePage> {
  const parameters = new URLSearchParams({ query })
  if (cursor) parameters.set('cursor', cursor)
  return workItemRequest(
    `/api/work-items/completed/search?${parameters.toString()}`,
    { fallbackCode: 'ERR_COMPLETED_HISTORY_SEARCH' },
  )
}

export function showCompletedChange(changeId: string, completionId: string): Promise<CompletedChangeRecord> {
  const query = new URLSearchParams({ completion_id: completionId })
  return workItemRequest(
    `/api/work-items/completed/${encodeURIComponent(changeId)}?${query.toString()}`,
    { fallbackCode: 'ERR_COMPLETED_HISTORY_DETAIL' },
  )
}

export function showWorkItem(changeId: string, outcomeId: string): Promise<WorkItemDetailResponse> {
  return workItemRequest(
    `/api/changes/${encodeURIComponent(changeId)}/outcomes/${encodeURIComponent(outcomeId)}`,
    { fallbackCode: 'ERR_WORK_ITEM_DETAIL' },
  )
}

export function answerWorkItemRequest(
  changeId: string,
  requestId: string,
  resolution: DeliveryRequestResolution,
): Promise<DeliveryRequest> {
  return controlRequest(
    `/api/changes/${encodeURIComponent(changeId)}/requests/${encodeURIComponent(requestId)}/answer`,
    'ERR_WORK_ITEM_REQUEST_ANSWER',
    resolution,
  )
}

export function clearWorkItemBlock(
  changeId: string,
  outcomeId: string,
  blockId: string,
  operatorNote: string,
  locators: string[],
): Promise<unknown> {
  return controlRequest(
    `/api/changes/${encodeURIComponent(changeId)}/outcomes/${encodeURIComponent(outcomeId)}/blocks/${encodeURIComponent(blockId)}/clear`,
    'ERR_WORK_ITEM_BLOCK_CLEAR',
    { operator_note: operatorNote, locators },
  )
}

export function recoverWorkItemClaim(
  changeId: string,
  outcomeId: string,
  attemptId: string,
  claimId: string,
): Promise<unknown> {
  return controlRequest(
    `/api/changes/${encodeURIComponent(changeId)}/outcomes/${encodeURIComponent(outcomeId)}/claims/recover`,
    'ERR_WORK_ITEM_CLAIM_RECOVERY',
    { confirmed_lost: true, attempt_id: attemptId, claim_id: claimId },
  )
}

export function moveWorkItemBackward(
  changeId: string,
  outcomeId: string,
  target: WorkItemStage,
  reason: string,
): Promise<BackwardMoveResult> {
  return controlRequest(
    `/api/changes/${encodeURIComponent(changeId)}/outcomes/${encodeURIComponent(outcomeId)}/move-backward`,
    'ERR_WORK_ITEM_BACKWARD_MOVE',
    { target, reason },
  )
}

export function retryWorkItemIntegration(changeId: string): Promise<unknown> {
  return controlRequest(
    `/api/changes/${encodeURIComponent(changeId)}/integration/retry`,
    'ERR_WORK_ITEM_INTEGRATION_RETRY',
  )
}
