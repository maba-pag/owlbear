export type WorkItemStage = 'design' | 'planning' | 'implementation' | 'completed'
export type WorkItemScope = 'outcome' | 'change-publication'
export type WorkItemNeed = 'you' | 'dependency' | 'none'
export type WorkItemNextActor = 'you' | 'agent' | 'dependency' | 'none'
export type WorkItemActivityState = 'idle' | 'ready' | 'working'
export type WorkItemActionKind =
  | 'none'
  | 'answer-request'
  | 'clear-block'
  | 'recover-claim'
  | 'finalize'
  | 'reconcile-checkpoint'
  | 'mark-ready'
  | 'observe-acceptance'
  | 'resolve-attention'
  | 'resume-change'
  | 'start-orchestration'
export type WorkItemProgressKind = 'tasks' | 'design-return' | 'plan' | 'publication'
export type WorkItemChangeLifecycle = 'in-delivery' | 'finalization' | 'publication' | 'awaiting-merge' | 'acceptance' | 'deferred' | 'abandoned'
export type DeliveryWorkerRole = 'planner' | 'builder'
export type WorkItemPublicationPhase =
  | 'finalization-invalidated'
  | 'ready-for-finalization'
  | 'checkpoint-pending'
  | 'pull-request-draft'
  | 'awaiting-merge'
  | 'acceptance-observed'
  | 'deferred'
  | 'abandoned'

export interface WorkItemActivity {
  state: WorkItemActivityState
  worker_role: DeliveryWorkerRole | null
  started_at: string | null
  task_id: string | null
}

export interface WorkItemAction {
  kind: WorkItemActionKind
  label: string | null
  command: string | null
  attention_id?: string | null
}

export interface WorkItemProgress {
  kind: WorkItemProgressKind
  label: string
  done: number | null
  total: number | null
}

export interface WorkItemCardView {
  item_key: string
  work_item_id: string
  change_id: string
  scope: WorkItemScope
  title: string
  stage: WorkItemStage | null
  needs: WorkItemNeed
  needs_headline: string | null
  next_actor: WorkItemNextActor
  next_step: string
  activity: WorkItemActivity
  progress: WorkItemProgress
  action: WorkItemAction
}

export interface ChangeGroupView {
  change_id: string
  title: string
  snapshot_version: string
  lifecycle: WorkItemChangeLifecycle
  outcome_total: number
  outcome_completed: number
  items: WorkItemCardView[]
}

export interface NeedsCounts {
  you: number
  dependency: number
  none: number
}

export interface ActivityCounts {
  idle: number
  ready: number
  working: number
}

export interface WorkItemPortfolioTotals {
  total: number
  complete: number
  needs: NeedsCounts
  activity: ActivityCounts
}

export type PortfolioWorkScope = 'outcome' | 'publication'
export type PortfolioGuidanceKind =
  | 'resume-design'
  | 'start-orchestration'
  | 'work-underway'
  | 'intervene'
  | 'wait'
  | 'create-change'

export interface PortfolioWorkReference {
  change_id: string
  item_key: string
  scope: PortfolioWorkScope
}

export interface PortfolioGuidance {
  kind: PortfolioGuidanceKind
  change_ids: string[]
  work_count: number
}

export interface PortfolioOperatingView {
  unfinished_change_count: number
  completed_change_count: number
  draft_design_change_ids: string[]
  design_required_change_ids: string[]
  claimed: PortfolioWorkReference[]
  queued_for_orchestration: PortfolioWorkReference[]
  interventions: PortfolioWorkReference[]
  dependency_waits: PortfolioWorkReference[]
  guidance: PortfolioGuidance[]
}

export interface WorkItemPortfolioResponse {
  groups: ChangeGroupView[]
  totals: WorkItemPortfolioTotals
  operating: PortfolioOperatingView
}

export interface DesignWorkDetailResponse {
  change_id: string
  package_id: string
  intent_markdown: string
  design_markdown: string
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

export interface WorkItemCommitment {
  commitment_id: string
  commitment_class: string
  provenance: string
  statement: string
}

export interface WorkItemDependency {
  outcome_id: string
  title: string
  stage: WorkItemStage
}

export interface WorkItemTaskEvidence {
  task_id: string
  title: string
  result: string
  status: 'pending' | 'active' | 'reviewed'
  completed_commit: string | null
  acceptance_observations: string[]
  proof_boundaries: string[]
}

export interface WorkItemPublicationView {
  phase: WorkItemPublicationPhase
  finalization_id: string | null
  finalized_head: string | null
  published_head: string | null
  pending_checkpoint_head: string | null
  pending_checkpoint_triggers: string[]
  invalidated_expected_head: string | null
  invalidated_observed_head: string | null
  repository: string | null
  pull_request_number: number | null
  pull_request_head: string | null
  accepted_merge_commit: string | null
  merged_at: string | null
  attention?: {
    disposition_id: string
    kind: 'publication-attention' | 'acceptance-attention'
    change_id: string
    entered_from: string
    recorded_at: string
    diagnostics: string[]
  } | null
  worktree_cleanup?: WorkItemWorktreeCleanupView | null
  worktree_recovery?: WorkItemWorktreeRecoveryView | null
}

export interface WorkItemWorktreeCleanupView {
  eligible: boolean
  blocked_reason: string | null
  completion_id: string | null
}

export interface WorkItemWorktreeRecoveryView {
  eligible: boolean
  blocked_reason: string | null
  recovery_reviewed_head: string | null
}

export interface ChangeWorktreeCleanupResponse {
  cleanup_id: string
  change_id: string
  branch: string
  worktree_path: string
  branch_head: string
}

export interface ChangeWorktreeRecoveryResponse {
  change_id: string
  branch: string
  worktree_path: string
  branch_head: string
  recovery_reviewed_head: string
}

export interface WorkItemDetailView {
  snapshot_version: string
  change_title: string
  card: WorkItemCardView
  promise: string
  acceptance: string[]
  commitments: WorkItemCommitment[]
  dependencies: WorkItemDependency[]
  tasks: WorkItemTaskEvidence[]
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
    source_boundary: string | null
    preserved_commit: string | null
  } | null
  operator_moves: Array<{
    move_id: string
    outcome_id: string
    destination: WorkItemStage
    reason: string
    invalidated_outcome_ids: string[]
  }>
  recovery_attention: {
    attempt_id: string
    claim_id: string
    reason: string
    custody_retained: boolean
    retry_condition: string
  } | null
  publication: WorkItemPublicationView | null
}

export interface WorkItemDetailResponse {
  item: WorkItemDetailView
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

export interface BackwardMovePreview {
  outcome_id: string
  target: WorkItemStage
  snapshot_version: string
  invalidated_outcome_ids: string[]
}

interface CompletedChangeRecordBase {
  schema_version: 2
  change_id: string
  completion_id: string
  title: string
  semantic_summary: string
}

export interface LegacyCompletedChangeRecord extends CompletedChangeRecordBase {
  record_kind: 'legacy-package'
  completion_path: string
  historical_completion_locator: string
  package_id: string
  introducing_target_commit: string
  source_target_commit: string
}

export interface CompletionPullRequestIdentity {
  number: number
  node_id: string
}

export interface ReceiptCompletedChangeRecord extends CompletedChangeRecordBase {
  record_kind: 'completion-receipt'
  finalization_receipt_id: string
  finalized_change_head: string
  repository_identity: string
  pull_request_identity: CompletionPullRequestIdentity
  accepted_target_ref: string
  accepted_merge_commit: string
  merged_at: string
  acceptance_observation_id: string
  check_observation_ids: string[]
  review_receipt_ids: string[]
  acceptance_evidence_digest: string
  completed_at: string
}

export type CompletedChangeRecord = LegacyCompletedChangeRecord | ReceiptCompletedChangeRecord

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

export function workItemDetailUrl(changeId: string, itemKey: string): string {
  return `/api/changes/${encodeURIComponent(changeId)}/work-items/${encodeURIComponent(itemKey)}`
}

export function showWorkItem(changeId: string, itemKey: string): Promise<WorkItemDetailResponse> {
  return workItemRequest(
    workItemDetailUrl(changeId, itemKey),
    { fallbackCode: 'ERR_WORK_ITEM_DETAIL' },
  )
}

export function showDesignWork(changeId: string): Promise<DesignWorkDetailResponse> {
  return workItemRequest(
    `/api/design-work/${encodeURIComponent(changeId)}`,
    { fallbackCode: 'ERR_DESIGN_WORK_DETAIL' },
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
  snapshotVersion: string,
): Promise<BackwardMoveResult> {
  return controlRequest(
    `/api/changes/${encodeURIComponent(changeId)}/outcomes/${encodeURIComponent(outcomeId)}/move-backward`,
    'ERR_WORK_ITEM_BACKWARD_MOVE',
    { target, reason, snapshot_version: snapshotVersion },
  )
}

export function previewWorkItemBackward(
  changeId: string,
  outcomeId: string,
  target: WorkItemStage,
): Promise<BackwardMovePreview> {
  return controlRequest(
    `/api/changes/${encodeURIComponent(changeId)}/outcomes/${encodeURIComponent(outcomeId)}/move-backward/preview`,
    'ERR_WORK_ITEM_BACKWARD_PREVIEW',
    { target },
  )
}

export function reconcileWorkItemPublication(changeId: string): Promise<unknown> {
  return controlRequest(
    `/api/changes/${encodeURIComponent(changeId)}/publication/reconcile`,
    'ERR_WORK_ITEM_PUBLICATION_RECONCILE',
  )
}

export function markWorkItemPublicationReady(changeId: string): Promise<unknown> {
  return controlRequest(
    `/api/changes/${encodeURIComponent(changeId)}/publication/ready`,
    'ERR_WORK_ITEM_PUBLICATION_READY',
  )
}

export function observeWorkItemAcceptance(changeId: string): Promise<unknown> {
  return controlRequest(
    `/api/changes/${encodeURIComponent(changeId)}/acceptance/observe`,
    'ERR_WORK_ITEM_ACCEPTANCE_OBSERVE',
  )
}

export function resolveWorkItemAttention(changeId: string, expectedDispositionId: string): Promise<unknown> {
  return controlRequest(
    `/api/changes/${encodeURIComponent(changeId)}/attention/resolve`,
    'ERR_WORK_ITEM_ATTENTION_RESOLVE',
    { expected_disposition_id: expectedDispositionId },
  )
}

export function deferWorkItemChange(changeId: string, reason: string): Promise<unknown> {
  return controlRequest(
    `/api/changes/${encodeURIComponent(changeId)}/defer`,
    'ERR_WORK_ITEM_CHANGE_DEFER',
    { reason },
  )
}

export function resumeWorkItemChange(changeId: string): Promise<unknown> {
  return controlRequest(
    `/api/changes/${encodeURIComponent(changeId)}/resume`,
    'ERR_WORK_ITEM_CHANGE_RESUME',
  )
}

export function abandonWorkItemChange(changeId: string, reason: string): Promise<unknown> {
  return controlRequest(
    `/api/changes/${encodeURIComponent(changeId)}/abandon`,
    'ERR_WORK_ITEM_CHANGE_ABANDON',
    { confirmed_abandonment: true, reason },
  )
}

export function cleanupAbandonedWorkItemChange(changeId: string): Promise<ChangeWorktreeCleanupResponse> {
  return controlRequest(
    `/api/changes/${encodeURIComponent(changeId)}/worktree/cleanup/abandoned`,
    'ERR_WORK_ITEM_ABANDONED_WORKTREE_CLEANUP',
  )
}

export function cleanupCompletedWorkItemChange(
  changeId: string,
  completionId: string,
): Promise<ChangeWorktreeCleanupResponse> {
  return controlRequest(
    `/api/changes/${encodeURIComponent(changeId)}/worktree/cleanup/completed`,
    'ERR_WORK_ITEM_COMPLETED_WORKTREE_CLEANUP',
    { completion_id: completionId },
  )
}

export function recoverWorkItemChange(
  changeId: string,
  recoveryReviewedHead: string,
): Promise<ChangeWorktreeRecoveryResponse> {
  return controlRequest(
    `/api/changes/${encodeURIComponent(changeId)}/worktree/recover`,
    'ERR_WORK_ITEM_WORKTREE_RECOVERY',
    { confirmed_recovery: true, recovery_reviewed_head: recoveryReviewedHead },
  )
}
