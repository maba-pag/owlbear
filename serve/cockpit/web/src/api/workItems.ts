export type WorkItemStage = "design" | "planning" | "implementation" | "completed";
export type WorkItemScope = "outcome" | "change-publication";
export type WorkItemNeed = "you" | "dependency" | "none";
export type WorkItemNextActor = "you" | "agent" | "dependency" | "none";
export type WorkItemActivityState = "idle" | "ready" | "working";
export type WorkItemActionKind =
  | "none"
  | "resume-design"
  | "answer-request"
  | "clear-block"
  | "grant-attempt"
  | "recover-claim"
  | "finalize"
  | "reconcile-checkpoint"
  | "sync-target"
  | "mark-ready"
  | "observe-acceptance"
  | "resolve-attention"
  | "adopt-external-head"
  | "resume-change"
  | "start-orchestration";
export type WorkItemProgressKind = "tasks" | "design-return" | "plan" | "publication";
export type WorkItemChangeLifecycle =
  | "in-delivery"
  | "finalization"
  | "publication"
  | "awaiting-merge"
  | "acceptance"
  | "deferred"
  | "abandoned";
export type DeliveryWorkerRole = "planner" | "builder";
export type WorkItemPublicationPhase =
  | "finalization-invalidated"
  | "review-repair"
  | "ready-for-finalization"
  | "checkpoint-pending"
  | "pull-request-draft"
  | "awaiting-merge"
  | "acceptance-observed"
  | "deferred"
  | "abandoned";

export interface WorkItemActivity {
  state: WorkItemActivityState;
  worker_role: DeliveryWorkerRole | null;
  started_at: string | null;
  task_id: string | null;
}

export interface WorkItemAction {
  kind: WorkItemActionKind;
  label: string | null;
  command: string | null;
  attention_id?: string | null;
  expected_head?: string | null;
  adopted_head?: string | null;
}

export interface WorkItemProgress {
  kind: WorkItemProgressKind;
  label: string;
  done: number | null;
  total: number | null;
}

export type DeliveryReadinessStatus = "ready" | "running" | "waiting" | "blocked" | "unavailable" | "complete";
export type DeliveryReadinessChecksState = "not-run" | "failed" | "passed" | "unknown";
export type DeliveryReadinessReasonCode =
  | "ready"
  | "design-attention"
  | "active-custody"
  | "builder-transition-contained"
  | "retry-transition-contained"
  | "finalization-failed"
  | "settled-attention-target-drift"
  | "claim-activation-failed"
  | "coordination-unavailable"
  | "execution-occupancy-unavailable"
  | "engine-action-pending"
  | "engine-action-blocked"
  | "engine-action-interrupted"
  | "engine-action-failed"
  | "engine-action-incomplete"
  | "target-sync-required"
  | "claim-custody-unreconciled"
  | "runtime-unavailable"
  | "dependency-wait"
  | "request-action"
  | "change-paused"
  | "change-terminal"
  | "outcome-complete"
  | "task-incomplete"
  | "workspace-inspection-failed"
  | "workspace-dirty"
  | "workspace-preflight-failed"
  | "review-repair"
  | "publication-wait"
  | "checkpoint-pending"
  | "report-store-unavailable"
  | "retry-backoff"
  | "retry-exhausted"
  | "acceptance-wait"
  | "retry-containment"
  | "retry-ledger-unavailable"
  | "worker-stall-wait"
  | "merge-approval-required"
  | "merge-checking"
  | "merge-blocked"
  | "checks-running"
  | "provider-unavailable"
  | "merge-in-progress"
  | "merge-response-unknown";

export type MergeBlockReason =
  | "conflicts"
  | "behind"
  | "protection"
  | "draft"
  | "closed"
  | "checks-failed"
  | "queue-required"
  | "stacked"
  | "wrong-base"
  | "capability-unavailable"
  | "method-not-allowed";

export interface MergeBlock {
  reason: MergeBlockReason;
  detail: string | null;
}

/** The one unsettled merge approval of a Change and the pull request to check in GitHub. */
export interface MergeAttemptSummary {
  approval_id: string;
  state: "intent" | "released" | "pending";
  approved_head: string;
  pr_url: string;
  released_at?: string | null;
}

export interface MergeOffer {
  offer_id: string;
  repository: string;
  number: number;
  node_id: string;
  title: string;
  head_sha: string;
  base_branch: string;
  target_head: string;
  finalization_id: string;
  ready_receipt_id: string;
  merge_method: "merge" | "squash" | "rebase";
  stack_size: number;
  required_checks: Array<{ name: string; conclusion: string }>;
  check_summary: {
    required_passed: number;
    required_pending: number;
    required_failed: number;
    optional_failed: number;
  };
  proof: {
    observation_count: number;
    review_id: string;
    proof_target: string;
  };
}

/** Engine-projected situation; Cockpit only maps keys to labels and tones. */
export type DeliverySituation =
  | "with-agent"
  | "ready-for-next-step"
  | "your-decision"
  | "waiting-on-github"
  | "waiting-on-delivery"
  | "waiting-on-dependency"
  | "retrying-automatically"
  | "needs-attention"
  | "pausing"
  | "paused"
  | "abandoned"
  | "done";
export type DeliveryWaitingOn = "you" | "agent" | "delivery" | "github" | "outcome" | "change" | "none";
export type TargetSyncAvailability = "required" | "optional" | "unavailable" | "unnecessary";

/** The one user-facing situation Delivery derives; Cockpit renders it without reconstruction. */
export interface DeliveryProgress {
  situation: DeliverySituation;
  headline: string;
  waiting_on: DeliveryWaitingOn;
  waiting_on_id?: string | null;
  since?: string | null;
  next_eligible_at?: string | null;
  target_sync?: TargetSyncAvailability | null;
}

/** Delivery's own reason that the defer intent would refuse Pause; Cockpit only maps keys to copy. */
export type ChangePauseUnavailableReason =
  | "finalizer-custody"
  | "step-in-progress"
  | "recovery-required"
  | "state-unavailable"
  | "change-inactive"
  | "pause-requested";
export type FinalizationFailureCode =
  | "workspace-dirty"
  | "workspace-preflight-failed"
  | "maintained-check-failed"
  | "maintained-check-unavailable"
  | "independent-review-failed"
  | "independent-review-unavailable"
  | "proof-mutated-worktree"
  | "finalizer-ended-without-report";
export type FinalizationFailureCategory =
  | "custody-preflight"
  | "maintained-check"
  | "independent-review"
  | "proof-mutation"
  | "worker-ended";

export interface DeliveryReadinessBasis {
  contract_digest: string | null;
  frontier_digest: string | null;
  source_head: string | null;
  target_head: string | null;
  continuation_id: string | null;
  candidate_head: string | null;
  reviewed_head: string | null;
  workspace_fingerprint: string | null;
  diagnostic_sequence: number | null;
}

export interface FinalizationReport {
  report_id: string;
  sequence: number;
  observed_at: string;
  summary: string;
  producer: "finalization-diagnostic";
  request: {
    change_id: string;
    attempt_key: string;
    category: FinalizationFailureCategory;
    code: FinalizationFailureCode;
    checks_state: "not-run" | "failed" | "unknown";
    check_id: string | null;
    exit_status: number | null;
    procedure_id: string | null;
    proof_fingerprint_before: string | null;
    proof_fingerprint_after: string | null;
    paths: string[];
  };
}

export interface FinalizationAttempt {
  report: FinalizationReport;
  applicability: "current" | "historical";
}

/** Bounded metadata for one durable retry attempt; never failure prose or paths. */
export interface DeliveryRetryAttempt {
  ordinal: number;
  kind: "original" | "repair" | "observation";
  status: "pending" | "failed" | "waiting" | "succeeded" | "contained" | "paused";
  failure_code: string | null;
  observed_at: string | null;
}

/** Engine-computed eligibility for one supported action at a captured basis. */
export interface DeliveryReadiness {
  status: DeliveryReadinessStatus;
  operation: WorkItemActionKind | null;
  executable: boolean;
  next_actor: WorkItemNextActor;
  reason_code: DeliveryReadinessReasonCode;
  checks_state: DeliveryReadinessChecksState;
  basis: DeliveryReadinessBasis;
  action: WorkItemAction | null;
  last_attempt: FinalizationAttempt | null;
  attempts?: number;
  next_eligible_at?: string | null;
  stop_reason?: string | null;
  retry_history?: DeliveryRetryAttempt[];
  prompt?: string | null;
  progress?: DeliveryProgress | null;
  merge_offer?: MergeOffer | null;
  merge_block?: MergeBlock | null;
  merge_attempt?: MergeAttemptSummary | null;
}

export interface WorkItemCardView {
  item_key: string;
  work_item_id: string;
  change_id: string;
  scope: WorkItemScope;
  title: string;
  stage: WorkItemStage | null;
  publication_phase?: WorkItemPublicationPhase | null;
  needs: WorkItemNeed;
  needs_headline: string | null;
  next_actor: WorkItemNextActor;
  next_step: string;
  activity: WorkItemActivity;
  progress: WorkItemProgress;
  action: WorkItemAction;
  readiness?: DeliveryReadiness | null;
}

export interface ChangeGroupView {
  change_id: string;
  title: string;
  snapshot_version: string;
  lifecycle: WorkItemChangeLifecycle;
  outcome_total: number;
  outcome_completed: number;
  items: WorkItemCardView[];
  progress?: DeliveryProgress | null;
  pause_available?: boolean;
  pause_unavailable_reason?: ChangePauseUnavailableReason | null;
  /** A Pause request waits for the started step to drain; new work is refused meanwhile. */
  pause_requested?: boolean;
}

export interface NeedsCounts {
  you: number;
  dependency: number;
  none: number;
}

export interface ActivityCounts {
  idle: number;
  ready: number;
  working: number;
}

export interface WorkItemPortfolioTotals {
  total: number;
  complete: number;
  needs: NeedsCounts;
  activity: ActivityCounts;
}

export type PortfolioChangeAdmission = "admitted" | "unadmitted";
export type PortfolioChangeStage =
  | "design"
  | "building"
  | "finalized"
  | "awaiting-merge"
  | "publication-attention"
  | "acceptance-attention"
  | "deferred"
  | "abandoned"
  | "completed";

export interface PortfolioChangeLifecycleStatus {
  change_id: string;
  admission: PortfolioChangeAdmission;
  stage: PortfolioChangeStage | null;
  actionable_runtime: boolean;
  diagnostic_code: string | null;
  diagnostic_detail: string | null;
}

export type PortfolioWorkScope = "outcome" | "publication";
export type PortfolioGuidanceKind =
  | "resume-design"
  | "start-orchestration"
  | "work-underway"
  | "intervene"
  | "wait"
  | "create-change";

export interface PortfolioWorkReference {
  change_id: string;
  item_key: string;
  scope: PortfolioWorkScope;
}

export interface PortfolioGuidance {
  kind: PortfolioGuidanceKind;
  change_ids: string[];
  work_count: number;
}

export interface PortfolioOperatingView {
  unfinished_change_count: number;
  completed_change_count: number;
  statuses: PortfolioChangeLifecycleStatus[];
  draft_design_change_ids: string[];
  design_required_change_ids: string[];
  claimed: PortfolioWorkReference[];
  queued_for_orchestration: PortfolioWorkReference[];
  interventions: PortfolioWorkReference[];
  dependency_waits: PortfolioWorkReference[];
  guidance: PortfolioGuidance[];
}

export type DeliveryHealthStatus = "healthy" | "attention";
export type DeliveryHealthResolution = "retry" | "inspect" | "authority-gap";
export type DeliveryHealthReason =
  | "unknown"
  | "remote-state-unavailable"
  | "remote-state-reconciliation"
  | "remote-state-version-unsupported"
  | "remote-change-head-ahead"
  | "remote-change-head-mismatch"
  | "local-change-head-out-of-band"
  | "local-frontier-mismatch"
  | "runtime-unavailable"
  | "state-publication-invalid"
  | "state-publication-pending"
  | "runtime-reconciliation-required";
export type DeliveryHealthHeadRelation = "equal" | "descendant" | "ancestor" | "divergent";

export interface DeliveryHealthDiagnostic {
  source: string;
  code: string;
  detail: string;
  change_id: string | null;
  path: string | null;
  retry_safe: boolean;
  reason: DeliveryHealthReason;
  resolution: DeliveryHealthResolution;
  expected_head: string | null;
  observed_head: string | null;
  observed_local_head: string | null;
  head_relation: DeliveryHealthHeadRelation | null;
}

export interface DeliveryHealthResponse {
  status: DeliveryHealthStatus;
  diagnostics: DeliveryHealthDiagnostic[];
}

export type DeliveryUnavailableDiagnostic = "runtime-unavailable" | "coordination-unavailable";
export type DeliveryCoordinationStatus = "missing" | "unreadable";

export interface DeliveryUnavailableChangeResponse {
  kind: "unavailable";
  change_id: string;
  title: string | null;
  diagnostics: DeliveryUnavailableDiagnostic[];
  coordination_status: DeliveryCoordinationStatus | null;
  readiness: DeliveryReadiness;
}

export interface WorkItemPortfolioResponse {
  groups: ChangeGroupView[];
  unavailable_changes?: DeliveryUnavailableChangeResponse[];
  totals: WorkItemPortfolioTotals;
  operating: PortfolioOperatingView;
  health: DeliveryHealthResponse;
}

export interface DesignWorkDetailResponse {
  change_id: string;
  package_id: string;
  intent_markdown: string;
  design_markdown: string;
}

export interface DeliveryRequestResolution {
  selected_option_id: string | null;
  response_text: string | null;
}

export interface DeliveryAcceptanceRef {
  acceptance_id: string;
  acceptance_version: string;
}

export type DeliveryConfirmationKind = "waive" | "confirm-check";

export interface DeliveryConfirmationScope {
  kind: DeliveryConfirmationKind;
  acceptance: DeliveryAcceptanceRef[];
  procedure: string;
}

export interface DeliveryRequest {
  request_id: string;
  kind: "decision" | "action";
  outcome_id: string;
  summary: string;
  options: Array<{ option_id: string; label: string }>;
  resolution: DeliveryRequestResolution | null;
  applies_to?: DeliveryConfirmationScope | null;
}

export type DeliveryCriterionStatus = "covered" | "waived" | "missing" | "uncovered" | "unknown";
export type DeliveryEvidenceVerdict = "passed" | "expected-negative" | "failed" | "missing" | "waived";
export type DeliveryAcceptanceIdentitySource = "authored" | "legacy-position";
export type DeliveryFinalizationRules = "typed" | "legacy" | "none";

export interface DeliveryEvidenceItem {
  observation_id: string;
  observation_schema: 1 | 2;
  source: "task" | "finalization";
  task_or_finalization_id: string;
  exact_commit: string;
  observation_kind: string;
  procedure: string;
  verdict: DeliveryEvidenceVerdict | null;
  owner: "agent" | "user" | "provider" | "assisted-check" | null;
  reason: string | null;
  provenance: "machine-observed" | "human-confirmed" | null;
  request_id: string | null;
  locator: string | null;
  summary: string | null;
  observed_at: string;
}

export interface DeliveryAcceptanceEvidence {
  acceptance_id: string;
  acceptance_version: string;
  outcome_id: string;
  statement: string;
  identity_source: DeliveryAcceptanceIdentitySource;
  status: DeliveryCriterionStatus;
  decided_by: string | null;
  evidence: DeliveryEvidenceItem[];
  evidence_truncated: number;
}

export interface DeliveryEvidenceProjection {
  change_id: string;
  contract_digest: string;
  frontier_digest: string;
  finalization_id: string | null;
  finalization_rules: DeliveryFinalizationRules;
  criteria: DeliveryAcceptanceEvidence[];
  unattributed: DeliveryEvidenceItem[];
  unattributed_truncated: number;
  counts: Record<DeliveryCriterionStatus, number>;
}

export interface DeliveryBlock {
  block_id: string;
  reason: string;
  unblock_condition: string;
  expected_evidence: string[];
  locators: string[];
  request_id: string | null;
  resolution_note: string | null;
  resolution_locators: string[];
  resume_commit: string | null;
}

export interface WorkItemCommitment {
  commitment_id: string;
  commitment_class: string;
  /** Schema-2 contracts name provenance; schema-3 contracts name decisions instead. */
  provenance?: string;
  decision_ids?: string[];
  statement: string;
}

export type DeliveryDecisionOrigin = "decided" | "approved" | "autonomous";

export interface DeliveryDecision {
  decision_id: string;
  origin: DeliveryDecisionOrigin;
  basis: string;
  statement: string;
  supersedes: string[];
}

export interface WorkItemDependency {
  outcome_id: string;
  title: string;
  stage: WorkItemStage;
}

export interface WorkItemTaskEvidence {
  task_id: string;
  title: string;
  result: string;
  status: "pending" | "active" | "reviewed";
  completed_commit: string | null;
  acceptance_observations: string[];
  proof_boundaries: string[];
}

export interface WorkItemPublicationGeneration {
  repository: string;
  number: number;
  node_id: string;
  head_sha: string;
}

export type PublicationCheckKind = "check_run" | "status_context";
export type PublicationCheckBlockingState = "blocking" | "required-pending" | "not-blocking";

export interface PublicationCheckView {
  check_id: string;
  kind: PublicationCheckKind;
  name: string;
  status: string;
  conclusion: string | null;
  required: boolean;
  blocking_state: PublicationCheckBlockingState;
}

export interface PublicationChecksObservationResponse {
  schema_version: 1;
  observation_id: string;
  change_id: string;
  repository: string;
  pull_request_number: number;
  exact_commit: string;
  observed_at: string;
  rollup_state: string | null;
  checks: PublicationCheckView[];
  required_failure_count: number;
  truncated_count: number;
}

export interface WorkItemPublicationReconciliationResponse {
  change_id: string;
  attempted_head: string | null;
  reconciled: boolean;
  error_code: string | null;
  error_detail: string | null;
  pending_checkpoint_attempt_count: number;
  pending_checkpoint_last_attempted_at: string | null;
  pending_checkpoint_error_code: string | null;
  pending_checkpoint_error_detail: string | null;
}

export interface WorkItemPublicationView {
  phase: WorkItemPublicationPhase;
  finalization_id: string | null;
  finalized_head: string | null;
  ready_for_finalization?: boolean | null;
  readiness_diagnostics?: string[];
  published_head: string | null;
  pending_checkpoint_head: string | null;
  pending_checkpoint_triggers: string[];
  pending_checkpoint_attempt_count?: number;
  pending_checkpoint_last_attempted_at?: string | null;
  pending_checkpoint_error_code?: string | null;
  pending_checkpoint_error_detail?: string | null;
  invalidated_expected_head: string | null;
  invalidated_observed_head: string | null;
  repository: string | null;
  pull_request_number: number | null;
  pull_request_head: string | null;
  mergeable?: boolean | null;
  merge_state_status?: string | null;
  mergeability_observed_at?: string | null;
  accepted_merge_commit: string | null;
  merged_at: string | null;
  publication_generations: WorkItemPublicationGeneration[];
  attention?: {
    disposition_id: string;
    kind: "publication-attention" | "acceptance-attention";
    change_id: string;
    entered_from: string;
    recorded_at: string;
    diagnostics: string[];
    acceptance_reason?:
      | "head-moved"
      | "closed-unmerged"
      | "identity-mismatch"
      | "merge-evidence-missing"
      | "latch-regression"
      | null;
  } | null;
  target_sync?: WorkItemTargetSyncView | null;
  target_sync_conflict?: WorkItemTargetSyncConflictView | null;
  worktree_cleanup?: WorkItemWorktreeCleanupView | null;
  worktree_recovery?: WorkItemWorktreeRecoveryView | null;
}

export interface WorkItemTargetSyncView {
  receipt_id: string;
  operation_id: string;
  target_branch: string;
  expected_target: string;
  target_head: string;
  change_head_before: string;
  merged_head: string;
  merge_commit: boolean;
  review_required: boolean;
}

export interface WorkItemTargetSyncConflictView {
  conflict_id: string;
  operation_id: string;
  target_head: string;
  change_head_before: string;
  conflict_paths: string[];
}

export interface WorkItemWorktreeCleanupView {
  eligible: boolean;
  blocked_reason: string | null;
  completion_id: string | null;
}

export interface WorkItemWorktreeRecoveryView {
  eligible: boolean;
  blocked_reason: string | null;
  recovery_reviewed_head: string | null;
}

export interface ChangeWorktreeCleanupResponse {
  cleanup_id: string;
  change_id: string;
  branch: string;
  worktree_path: string;
  branch_head: string;
}

export interface ChangeWorktreeRecoveryResponse {
  change_id: string;
  branch: string;
  worktree_path: string;
  branch_head: string;
  recovery_reviewed_head: string;
}

export interface TargetSyncResponse {
  schema_version: 1;
  receipt_id: string;
  operation_id: string;
  change_id: string;
  target_branch: string;
  expected_target: string;
  target_head: string;
  change_head_before: string;
  merged_head: string;
  merge_commit: boolean;
  review_required: boolean;
}

export interface TargetSyncAbortResponse {
  schema_version: 1;
  receipt_id: string;
  operation_id: string;
  change_id: string;
  target_head: string;
  restored_head: string;
}

export interface ExternalHeadAdoptionResponse {
  schema_version: 2;
  receipt_id: string;
  operation_id: string;
  change_id: string;
  branch: string;
  expected_head: string;
  adopted_head: string;
  provenance: "fast-forward" | "observed";
}

export interface PublicationSupersessionResponse {
  schema_version: 1;
  receipt_id: string;
  operation_id: string;
  change_id: string;
  predecessor_publication_id: string;
  successor_publication_id: string;
}

export type BuilderTransitionDiagnostic =
  | {
      action: "block";
      outcome_id: string;
      claim_id: string;
      block_id: string;
      reason: string;
      unblock_condition: string;
      expected_evidence: string[];
      locators: string[];
      request: DeliveryRequest | null;
      resume_commit: string | null;
    }
  | {
      action: "return";
      outcome_id: string;
      claim_id: string;
      target: WorkItemStage;
      reason: string;
      locators: string[];
      preserved_commit: string | null;
      attempt_id: string | null;
      source_boundary: string | null;
    };

export interface WorkItemRetryDiagnostic {
  code: "ERR_DELIVERY_WORKER_EXCLUSION_REQUIRED";
  attempt_id: string;
  transition: {
    action: "retry";
    outcome_id: string;
    claim_id: string;
    abandoned_commit: string | null;
    attempt_id: string | null;
    failure_code: string;
  };
}

export interface WorkItemDetailView {
  snapshot_version: string;
  change_title: string;
  card: WorkItemCardView;
  promise: string;
  acceptance: string[];
  commitments: WorkItemCommitment[];
  decisions: DeliveryDecision[];
  dependencies: WorkItemDependency[];
  tasks: WorkItemTaskEvidence[];
  block: DeliveryBlock | null;
  requests: DeliveryRequest[];
  superseded_request_ids: string[];
  active_claim: {
    attempt_id: string;
    claim_id: string;
    owner_id: string;
    process_id: string;
    continuation: boolean;
    started_at: string;
    worker_role: DeliveryWorkerRole;
    task_id: string | null;
  } | null;
  held_finalizer: {
    attempt_id: string;
    claim_id: string;
    owner_id: string;
    process_id: string;
    started_at: string;
  } | null;
  return_context: {
    target: WorkItemStage;
    reason: string;
    locators: string[];
    source_boundary: string | null;
    preserved_commit: string | null;
  } | null;
  operator_moves: Array<{
    move_id: string;
    outcome_id: string;
    destination: WorkItemStage;
    reason: string;
    invalidated_outcome_ids: string[];
  }>;
  recovery_attention: {
    attempt_id: string;
    claim_id: string;
    reason: string;
    custody_retained: boolean;
    retry_condition: string;
    diagnostic_transition?: BuilderTransitionDiagnostic | null;
  } | null;
  retry_diagnostic: WorkItemRetryDiagnostic | null;
  publication: WorkItemPublicationView | null;
  readiness?: DeliveryReadiness | null;
  change_progress?: DeliveryProgress | null;
  abandon_available?: boolean;
  pause_available?: boolean;
  pause_unavailable_reason?: ChangePauseUnavailableReason | null;
  evidence?: DeliveryEvidenceProjection | null;
  revision_prompt?: string | null;
}

export interface WorkItemAvailableDetailResponse {
  kind?: "available";
  item: WorkItemDetailView;
}

export interface WorkItemUnavailableDetailResponse {
  kind: "unavailable";
  change_id: string;
  title: string | null;
  diagnostics: DeliveryUnavailableDiagnostic[];
  coordination_status: DeliveryCoordinationStatus | null;
  readiness: DeliveryReadiness;
}

export type WorkItemDetailResponse = WorkItemAvailableDetailResponse | WorkItemUnavailableDetailResponse;

export function isUnavailableDetail(detail: WorkItemDetailResponse): detail is WorkItemUnavailableDetailResponse {
  return detail.kind === "unavailable";
}

export interface BackwardMoveResult {
  move: {
    move_id: string;
    outcome_id: string;
    destination: WorkItemStage;
    reason: string;
    invalidated_outcome_ids: string[];
  };
  invalidated_outcome_ids: string[];
}

export interface BackwardMovePreview {
  outcome_id: string;
  target: WorkItemStage;
  snapshot_version: string;
  invalidated_outcome_ids: string[];
}

interface CompletedChangeRecordBase {
  schema_version: 2;
  change_id: string;
  completion_id: string;
  title: string;
  semantic_summary: string;
  outcome_titles: string[];
  outcome_promises?: string[] | null;
}

export interface CompletionPullRequestIdentity {
  number: number;
  node_id: string;
}

export interface ReceiptCompletedChangeRecord extends CompletedChangeRecordBase {
  record_kind: "completion-receipt";
  finalization_receipt_id: string;
  finalized_change_head: string;
  repository_identity: string;
  pull_request_identity: CompletionPullRequestIdentity;
  accepted_target_ref: string;
  accepted_merge_commit: string;
  merged_at: string;
  acceptance_observation_id: string;
  check_observation_ids: string[];
  review_receipt_ids: string[];
  acceptance_evidence_digest: string;
  completed_at: string;
}

export interface AbandonedChangeRecord {
  schema_version: 1;
  record_kind: "abandoned-change";
  change_id: string;
  abandonment_id: string;
  title: string;
  semantic_summary: string;
  outcome_titles: string[];
  outcome_promises?: string[] | null;
  prior_stage:
    | "design"
    | "building"
    | "finalized"
    | "awaiting-merge"
    | "publication-attention"
    | "acceptance-attention"
    | "deferred";
  reason: string;
  abandoned_at: string;
  cleanup_available: boolean;
  target_sync_conflict: boolean;
  target_sync_conflict_target_head: string | null;
  target_sync_conflict_operation_id: string | null;
}

export type CompletedChangeRecord = ReceiptCompletedChangeRecord | AbandonedChangeRecord;

export interface CompletedChangePage {
  records: CompletedChangeRecord[];
  total_count: number;
  next_cursor: string | null;
}

interface WorkItemRequestOptions extends RequestInit {
  fallbackCode: string;
}

export class WorkItemApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly authority: string | null;
  readonly retrySafe: boolean;
  readonly retryAfter: string | null;

  constructor(
    status: number,
    code: string,
    detail: string,
    authority: string | null,
    retrySafe: boolean,
    retryAfter: string | null = null,
  ) {
    super(detail);
    this.name = "WorkItemApiError";
    this.status = status;
    this.code = code;
    this.authority = authority;
    this.retrySafe = retrySafe;
    this.retryAfter = retryAfter;
  }
}

async function workItemRequest<T>(url: string, options: WorkItemRequestOptions): Promise<T> {
  const response = await fetch(url, options);
  if (response.ok) return response.json() as Promise<T>;
  const payload = (await response.json().catch(() => ({}))) as Record<string, unknown>;
  const nested =
    typeof payload.detail === "object" && payload.detail !== null
      ? (payload.detail as Record<string, unknown>)
      : payload;
  throw new WorkItemApiError(
    response.status,
    typeof nested.code === "string" ? nested.code : options.fallbackCode,
    typeof nested.detail === "string" ? nested.detail : `Delivery request failed with status ${response.status}`,
    typeof nested.authority === "string" ? nested.authority : null,
    nested.retry_safe === true,
    typeof nested.retry_after === "string" ? nested.retry_after : null,
  );
}

function controlRequest<T>(url: string, fallbackCode: string, body?: object, signal?: AbortSignal): Promise<T> {
  return workItemRequest(url, {
    method: "POST",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
    signal,
    fallbackCode,
  });
}

export function listWorkItems(): Promise<WorkItemPortfolioResponse> {
  return workItemRequest("/api/work-items", {
    fallbackCode: "ERR_WORK_ITEM_PORTFOLIO",
  });
}

export function listCompletedChanges(cursor?: string, signal?: AbortSignal): Promise<CompletedChangePage> {
  const query = cursor ? `?${new URLSearchParams({ cursor }).toString()}` : "";
  return workItemRequest(`/api/work-items/completed${query}`, {
    fallbackCode: "ERR_COMPLETED_HISTORY",
    signal,
  });
}

export function searchCompletedChanges(
  query: string,
  cursor?: string,
  signal?: AbortSignal,
): Promise<CompletedChangePage> {
  const parameters = new URLSearchParams({ query });
  if (cursor) parameters.set("cursor", cursor);
  return workItemRequest(`/api/work-items/completed/search?${parameters.toString()}`, {
    fallbackCode: "ERR_COMPLETED_HISTORY_SEARCH",
    signal,
  });
}

export function completedChangeRecordId(record: CompletedChangeRecord): string {
  return record.record_kind === "abandoned-change" ? record.abandonment_id : record.completion_id;
}

export function showCompletedChange(changeId: string, recordId: string): Promise<CompletedChangeRecord> {
  const query = new URLSearchParams({ completion_id: recordId });
  return workItemRequest(`/api/work-items/completed/${encodeURIComponent(changeId)}?${query.toString()}`, {
    fallbackCode: "ERR_COMPLETED_HISTORY_DETAIL",
  });
}

export function workItemDetailUrl(changeId: string, itemKey: string): string {
  return `/api/changes/${encodeURIComponent(changeId)}/work-items/${encodeURIComponent(itemKey)}`;
}

export function showWorkItem(changeId: string, itemKey: string): Promise<WorkItemDetailResponse> {
  return workItemRequest(workItemDetailUrl(changeId, itemKey), {
    fallbackCode: "ERR_WORK_ITEM_DETAIL",
  });
}

export function designWorkDetailUrl(changeId: string): string {
  return `/api/design-work/${encodeURIComponent(changeId)}`;
}

export function showDesignWork(changeId: string): Promise<DesignWorkDetailResponse> {
  return workItemRequest(designWorkDetailUrl(changeId), {
    fallbackCode: "ERR_DESIGN_WORK_DETAIL",
  });
}

export function answerWorkItemRequest(
  changeId: string,
  requestId: string,
  resolution: DeliveryRequestResolution,
  expectedFrontierDigest: string,
): Promise<DeliveryRequest> {
  return controlRequest(
    `/api/changes/${encodeURIComponent(changeId)}/requests/${encodeURIComponent(requestId)}/answer`,
    "ERR_WORK_ITEM_REQUEST_ANSWER",
    { ...resolution, expected_frontier_digest: expectedFrontierDigest },
  );
}

export function clearWorkItemBlock(
  changeId: string,
  outcomeId: string,
  blockId: string,
  operatorNote: string,
  locators: string[],
  expectedFrontierDigest: string,
): Promise<unknown> {
  const blockPath = [
    "/api/changes",
    encodeURIComponent(changeId),
    "outcomes",
    encodeURIComponent(outcomeId),
    "blocks",
    encodeURIComponent(blockId),
    "clear",
  ].join("/");
  return controlRequest(blockPath, "ERR_WORK_ITEM_BLOCK_CLEAR", {
    operator_note: operatorNote,
    locators,
    expected_frontier_digest: expectedFrontierDigest,
  });
}

/** Funds exactly one more Builder attempt for an exhausted same-task retry block; retry history is kept. */
export function grantWorkItemAttempt(
  changeId: string,
  outcomeId: string,
  blockId: string,
  expectedFrontierDigest: string,
): Promise<unknown> {
  const grantPath = [
    "/api/changes",
    encodeURIComponent(changeId),
    "outcomes",
    encodeURIComponent(outcomeId),
    "blocks",
    encodeURIComponent(blockId),
    "grant-attempt",
  ].join("/");
  return controlRequest(grantPath, "ERR_WORK_ITEM_ATTEMPT_GRANT", {
    expected_frontier_digest: expectedFrontierDigest,
  });
}

/** A null outcome names the Change's Finalizer attempt; recent worktree activity is refused unchanged. */
export function releaseStuckWorker(
  changeId: string,
  outcomeId: string | null,
  attemptId: string,
  claimId: string,
): Promise<unknown> {
  return controlRequest(
    `/api/changes/${encodeURIComponent(changeId)}/workers/release-stuck`,
    "ERR_WORK_ITEM_RELEASE_STUCK_WORKER",
    { outcome_id: outcomeId, attempt_id: attemptId, claim_id: claimId },
  );
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
    "ERR_WORK_ITEM_BACKWARD_MOVE",
    { target, reason, snapshot_version: snapshotVersion },
  );
}

export function previewWorkItemBackward(
  changeId: string,
  outcomeId: string,
  target: WorkItemStage,
): Promise<BackwardMovePreview> {
  return controlRequest(
    `/api/changes/${encodeURIComponent(changeId)}/outcomes/${encodeURIComponent(outcomeId)}/move-backward/preview`,
    "ERR_WORK_ITEM_BACKWARD_PREVIEW",
    { target },
  );
}

export function reconcileWorkItemPublication(changeId: string): Promise<WorkItemPublicationReconciliationResponse> {
  return controlRequest(
    `/api/changes/${encodeURIComponent(changeId)}/publication/reconcile`,
    "ERR_WORK_ITEM_PUBLICATION_RECONCILE",
  );
}

export function markWorkItemPublicationReady(changeId: string): Promise<unknown> {
  return controlRequest(
    `/api/changes/${encodeURIComponent(changeId)}/publication/ready`,
    "ERR_WORK_ITEM_PUBLICATION_READY",
  );
}

export function observeWorkItemPublicationChecks(changeId: string): Promise<PublicationChecksObservationResponse> {
  return controlRequest(
    `/api/changes/${encodeURIComponent(changeId)}/publication/checks/observe`,
    "ERR_WORK_ITEM_PUBLICATION_CHECKS_OBSERVE",
  );
}

export function observeWorkItemAcceptance(changeId: string): Promise<unknown> {
  return controlRequest(
    `/api/changes/${encodeURIComponent(changeId)}/acceptance/observe`,
    "ERR_WORK_ITEM_ACCEPTANCE_OBSERVE",
  );
}

/** The approval's attempt after Delivery sent its single request (N05 D14). */
export interface MergeApprovalResponse {
  approval_id: string;
  state: "intent" | "released" | "pending" | "merged" | "refused" | "not-sent" | "head-changed" | "closed";
  refusal_reason: string | null;
  pr_url: string;
  completion_id: string | null;
}

/** A retried POST repeats `submissionId`, so Delivery returns the same attempt and sends nothing again. */
export function approveWorkItemMerge(
  changeId: string,
  offerId: string,
  submissionId: string,
): Promise<MergeApprovalResponse> {
  return controlRequest(`/api/changes/${encodeURIComponent(changeId)}/approve-merge`, "ERR_WORK_ITEM_MERGE_APPROVE", {
    offer_id: offerId,
    submission_id: submissionId,
  });
}

export function adoptExternalHeadAfterAcceptanceAttention(
  changeId: string,
  expectedDispositionId: string,
  expectedHead: string,
  adoptedHead: string,
  operationId: string,
): Promise<ExternalHeadAdoptionResponse> {
  return controlRequest(
    `/api/changes/${encodeURIComponent(changeId)}/acceptance/external-head/adopt`,
    "ERR_WORK_ITEM_ACCEPTANCE_HEAD_ADOPTION",
    {
      expected_disposition_id: expectedDispositionId,
      expected_head: expectedHead,
      adopted_head: adoptedHead,
      operation_id: operationId,
    },
  );
}

export function resolveWorkItemAttention(
  changeId: string,
  expectedDispositionId: string,
  expectedFrontierDigest: string,
): Promise<unknown> {
  return controlRequest(
    `/api/changes/${encodeURIComponent(changeId)}/attention/resolve`,
    "ERR_WORK_ITEM_ATTENTION_RESOLVE",
    {
      expected_disposition_id: expectedDispositionId,
      expected_frontier_digest: expectedFrontierDigest,
    },
  );
}

export function supersedeWorkItemPublication(
  changeId: string,
  operationId: string,
): Promise<PublicationSupersessionResponse> {
  return controlRequest(
    `/api/changes/${encodeURIComponent(changeId)}/publication/supersede`,
    "ERR_WORK_ITEM_PUBLICATION_SUPERSEDE",
    { operation_id: operationId },
  );
}

export function syncWorkItemTarget(changeId: string, operationId: string): Promise<TargetSyncResponse> {
  return controlRequest(`/api/changes/${encodeURIComponent(changeId)}/target/sync`, "ERR_WORK_ITEM_TARGET_SYNC", {
    operation_id: operationId,
  });
}

export function abortWorkItemTargetSync(
  changeId: string,
  expectedDispositionId: string,
  targetHead: string,
  operationId: string,
): Promise<TargetSyncAbortResponse> {
  return controlRequest(
    `/api/changes/${encodeURIComponent(changeId)}/target/conflict/abort`,
    "ERR_WORK_ITEM_TARGET_SYNC_ABORT",
    {
      expected_disposition_id: expectedDispositionId,
      target_head: targetHead,
      operation_id: operationId,
    },
  );
}

export function resolveWorkItemTargetSync(
  changeId: string,
  expectedDispositionId: string,
  targetHead: string,
  operationId: string,
): Promise<TargetSyncResponse> {
  return controlRequest(
    `/api/changes/${encodeURIComponent(changeId)}/target/conflict/resolve`,
    "ERR_WORK_ITEM_TARGET_SYNC_RESOLVE",
    {
      expected_disposition_id: expectedDispositionId,
      target_head: targetHead,
      operation_id: operationId,
    },
  );
}

export function deferWorkItemChange(
  changeId: string,
  reason: string,
  expectedFrontierDigest: string,
): Promise<unknown> {
  return controlRequest(`/api/changes/${encodeURIComponent(changeId)}/defer`, "ERR_WORK_ITEM_CHANGE_DEFER", {
    reason,
    expected_frontier_digest: expectedFrontierDigest,
  });
}

export function resumeWorkItemChange(changeId: string, expectedFrontierDigest: string): Promise<unknown> {
  return controlRequest(`/api/changes/${encodeURIComponent(changeId)}/resume`, "ERR_WORK_ITEM_CHANGE_RESUME", {
    expected_frontier_digest: expectedFrontierDigest,
  });
}

export function abandonWorkItemChange(
  changeId: string,
  reason: string,
  expectedFrontierDigest: string,
): Promise<unknown> {
  return controlRequest(`/api/changes/${encodeURIComponent(changeId)}/abandon`, "ERR_WORK_ITEM_CHANGE_ABANDON", {
    confirmed_abandonment: true,
    reason,
    expected_frontier_digest: expectedFrontierDigest,
  });
}

export function cleanupAbandonedWorkItemChange(changeId: string): Promise<ChangeWorktreeCleanupResponse> {
  return controlRequest(
    `/api/changes/${encodeURIComponent(changeId)}/worktree/cleanup/abandoned`,
    "ERR_WORK_ITEM_ABANDONED_WORKTREE_CLEANUP",
  );
}

export function discardAbandonedTargetSyncAndCleanup(
  changeId: string,
  expectedTargetHead: string,
  expectedOperationId: string,
): Promise<ChangeWorktreeCleanupResponse> {
  return controlRequest(
    `/api/changes/${encodeURIComponent(changeId)}/worktree/cleanup/abandoned/target-sync-discard`,
    "ERR_WORK_ITEM_TARGET_SYNC_DISCARD_CLEANUP",
    {
      confirmed_discard: true,
      expected_target_head: expectedTargetHead,
      expected_operation_id: expectedOperationId,
    },
  );
}

export function cleanupCompletedWorkItemChange(
  changeId: string,
  completionId: string,
): Promise<ChangeWorktreeCleanupResponse> {
  return controlRequest(
    `/api/changes/${encodeURIComponent(changeId)}/worktree/cleanup/completed`,
    "ERR_WORK_ITEM_COMPLETED_WORKTREE_CLEANUP",
    { completion_id: completionId },
  );
}

export function recoverWorkItemChange(
  changeId: string,
  recoveryReviewedHead: string,
): Promise<ChangeWorktreeRecoveryResponse> {
  return controlRequest(
    `/api/changes/${encodeURIComponent(changeId)}/worktree/recover`,
    "ERR_WORK_ITEM_WORKTREE_RECOVERY",
    { confirmed_recovery: true, recovery_reviewed_head: recoveryReviewedHead },
  );
}
