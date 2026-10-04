import type {
  ChangePauseUnavailableReason,
  DeliveryAcceptanceIdentitySource,
  DeliveryConfirmationKind,
  DeliveryCriterionStatus,
  DeliveryEvidenceVerdict,
  DeliveryFinalizationRules,
  DeliveryProgress,
  DeliveryReadinessChecksState,
  DeliveryReadinessReasonCode,
  DeliveryReadinessStatus,
  DeliveryWorkerRole,
  MergeBlockReason,
  WorkItemCardView,
  WorkItemNextActor,
  WorkItemPublicationPhase,
  WorkItemStage,
} from "../api/workItems";

export const PROGRESS_STAGE_LABELS: Record<WorkItemStage, string> = {
  design: "Design",
  planning: "Planning",
  implementation: "Implementation",
  completed: "Completed",
};

export const READINESS_STATUS_LABELS: Record<DeliveryReadinessStatus, string> = {
  ready: "Ready",
  running: "Running",
  waiting: "Waiting",
  blocked: "Blocked",
  unavailable: "Unavailable",
  complete: "Complete",
};

export const READINESS_REASON_LABELS: Record<DeliveryReadinessReasonCode, string> = {
  ready: "Delivery reports this operation is eligible now.",
  "design-attention": "The returned Design needs human review before re-admission.",
  "active-custody": "An active operation retains Change custody.",
  "builder-transition-contained":
    "The Builder transition was refused; custody is retained and host worker-exclusion evidence is missing.",
  "retry-transition-contained":
    "The worker retry was refused; its claim remains held until host worker-exclusion is verified.",
  "finalization-failed": "A recorded finalization diagnostic retains that attempt.",
  "settled-attention-target-drift":
    "The target changed after failed verification. Inspection only; sync, retry, and reset remain blocked.",
  "claim-activation-failed": "Delivery could not activate custody for the selected action.",
  "coordination-unavailable": "This Change has no readable coordination record.",
  "execution-occupancy-unavailable": "Delivery could not read current execution occupancy.",
  "engine-action-pending": "A retained engine action is acquired but has not started.",
  "engine-action-blocked": "A retained engine action journal is unverifiable; custody remains retained.",
  "engine-action-interrupted": "A retained engine action started without an authoritative result.",
  "engine-action-failed": "A retained engine action has a recorded failure.",
  "engine-action-incomplete": "A retained engine action has a recorded incomplete result.",
  "target-sync-required": "The Change must be synchronized with its integration target first.",
  "claim-custody-unreconciled": "Claim custody has not been reconciled with the workspace.",
  "runtime-unavailable": "Delivery could not compose this Change runtime.",
  "dependency-wait": "A dependency has not completed yet.",
  "request-action": "An open request needs an answer first.",
  "change-paused": "This Change is paused.",
  "change-terminal": "This Change reached a terminal state.",
  "task-incomplete": "Planned tasks are not complete yet.",
  "workspace-inspection-failed": "Managed workspace readiness could not be observed.",
  "workspace-dirty": "Managed workspace preflight is blocked by local changes.",
  "workspace-preflight-failed": "Managed workspace preflight did not pass.",
  "review-repair": "Review repair requires a new Change commit before verification.",
  "publication-wait": "Publication is waiting on an external result.",
  "checkpoint-pending": "A durable checkpoint is still pending.",
  "report-store-unavailable": "Finalization diagnostics could not be read.",
  "retry-backoff": "Automatic recovery is waiting for its next eligible time.",
  "retry-exhausted": "Automatic retries are exhausted; Delivery offers no action to reset this budget.",
  "acceptance-wait": "Acceptance is unchanged; observe later without repeating the effect.",
  "retry-containment":
    "A prior attempt has no authoritative outcome. Preserve custody; no caller action can retry or release it.",
  "retry-ledger-unavailable": "Retry authority could not be read safely.",
  "worker-stall-wait":
    "The VS Code window that ran this worker closed. Delivery records a failed attempt once no process uses " +
    "the worktree and it has stayed unchanged for 30 seconds.",
  "merge-approval-required": "Merge the pull request in GitHub.",
  "merge-checking": "GitHub is still computing mergeability.",
  "merge-blocked": "The pull request cannot be merged as offered; the next step is shown below.",
  "checks-running": "Required checks are still running.",
  "provider-unavailable": "GitHub could not be read; Delivery will read it again shortly.",
};

export const MERGE_BLOCK_LABELS: Record<MergeBlockReason, string> = {
  conflicts: "The pull request has merge conflicts; synchronize the target before merging.",
  behind: "The pull request is behind its target; synchronize the target before merging.",
  protection: "Branch protection blocks the merge; resolve it in GitHub, then merge there.",
  draft: "The pull request is a draft in GitHub; mark it ready there or merge in GitHub.",
  closed: "The pull request is closed in GitHub.",
  "checks-failed": "Required checks failed; fix them, then merge in GitHub.",
  "queue-required": "The target only accepts queued merges; merge in GitHub.",
  stacked: "The pull request is part of a stack; merge in GitHub.",
  "wrong-base": "The pull request targets another base branch; merge in GitHub or retarget it.",
  "capability-unavailable": "Delivery cannot merge here; merge the pull request in GitHub.",
  "method-not-allowed": "The repository disallows merge commits; merge in GitHub.",
};

/** Truthful check labels: absence of a run is never reported as a pass. */
export const READINESS_CHECKS_LABELS: Record<DeliveryReadinessChecksState, string> = {
  "not-run": "Not run",
  failed: "Failed",
  passed: "Passed",
  unknown: "Unknown",
};

export const NEXT_ACTOR_LABELS: Record<WorkItemNextActor, string> = {
  you: "You",
  agent: "Agent",
  dependency: "Dependency",
  none: "Nobody",
};

/** Delivery's evaluator decides each status; Cockpit only names it. */
export const EVIDENCE_STATUS_LABELS: Record<DeliveryCriterionStatus, string> = {
  covered: "Covered",
  waived: "Waived by you",
  missing: "Missing",
  uncovered: "Uncovered",
  unknown: "Unknown (legacy evidence)",
};

export const EVIDENCE_STATUS_TONES: Record<DeliveryCriterionStatus, WorkItemStatusTone> = {
  covered: "complete",
  waived: "neutral",
  missing: "attention",
  uncovered: "blocked",
  unknown: "neutral",
};

export const EVIDENCE_VERDICT_LABELS: Record<DeliveryEvidenceVerdict, string> = {
  passed: "Passed",
  "expected-negative": "Expected failure observed",
  failed: "Failed",
  missing: "Missing",
  waived: "Waived",
};

export const IDENTITY_SOURCE_LABELS: Record<DeliveryAcceptanceIdentitySource, string> = {
  authored: "Authored identity",
  "legacy-position": "Legacy position",
};

export const FINALIZATION_RULES_LABELS: Record<DeliveryFinalizationRules, string> = {
  typed: "Finalized with typed evidence",
  legacy: "Finalized under legacy rules",
  none: "Not finalized",
};

export const CONFIRMATION_KIND_LABELS: Record<DeliveryConfirmationKind, string> = {
  waive: "Waiver",
  "confirm-check": "Person-only check",
};

export function readinessTone(status: DeliveryReadinessStatus): WorkItemStatusTone {
  switch (status) {
    case "ready":
      return "ready";
    case "running":
      return "active";
    case "waiting":
      return "neutral";
    case "blocked":
      return "blocked";
    case "unavailable":
      return "attention";
    case "complete":
      return "complete";
  }
}

const WORKER_STATUS_LABELS: Record<DeliveryWorkerRole, string> = {
  planner: "Planner",
  builder: "Builder",
};

export type WorkItemStatusTone = "attention" | "blocked" | "active" | "ready" | "complete" | "neutral";

/** Labels for engine-projected progress; Delivery decides which key applies. */
export const DELIVERY_PROGRESS_LABELS: Record<DeliveryProgress, string> = {
  preparing: "Preparing",
  working: "Working",
  checking: "Checking",
  repairing: "Repairing",
  "needs-decision": "Needs your decision",
  "needs-sign-in": "Needs your sign-in",
  "waiting-for-service": "Waiting for service",
  "waiting-for-change": "Waiting for another Change",
  "ready-to-merge": "Ready to merge",
  completed: "Completed",
  paused: "Paused",
  "waiting-for-chat": "Waiting for chat to resume",
};

const DELIVERY_PROGRESS_TONES: Record<DeliveryProgress, WorkItemStatusTone> = {
  preparing: "active",
  working: "active",
  checking: "active",
  repairing: "active",
  "needs-decision": "attention",
  "needs-sign-in": "attention",
  "waiting-for-service": "neutral",
  "waiting-for-change": "neutral",
  "ready-to-merge": "ready",
  completed: "complete",
  paused: "neutral",
  "waiting-for-chat": "neutral",
};

export function progressTone(progress: DeliveryProgress): WorkItemStatusTone {
  return DELIVERY_PROGRESS_TONES[progress];
}

/** Only the engine-authored `/continue-change <this Change> …` prompt is a continuation prompt. */
export function isContinuationPrompt(prompt: string | null | undefined, changeId: string): prompt is string {
  return typeof prompt === "string" && prompt.startsWith(`/continue-change ${changeId} `);
}

export const CONTINUATION_PROMPT_HELP = "Run it in Copilot Chat. Copying does not start an agent.";

/** Copy for Delivery's own reason that the defer intent would refuse Pause. */
export const PAUSE_UNAVAILABLE_COPY: Record<ChangePauseUnavailableReason, string> = {
  "finalizer-custody": "A Finalizer attempt holds this Change.",
  "step-in-progress": "A step is in progress; Pause is available when it returns.",
  "recovery-required": "An interrupted step must be recovered first.",
  "state-unavailable": "Delivery cannot confirm this Change is idle, so Pause is unavailable.",
  "change-inactive": "This Change cannot be paused.",
  "pause-requested": "Pause requested; the current step finishes first.",
};

/**
 * Pause availability comes only from Delivery's Change-level projection, never from card readiness;
 * a view without the field fails closed.
 */
export function changePauseUnavailableMessage(view: {
  pause_available?: boolean;
  pause_unavailable_reason?: ChangePauseUnavailableReason | null;
}): string | null {
  if (view.pause_available === true) return null;
  return PAUSE_UNAVAILABLE_COPY[view.pause_unavailable_reason ?? "state-unavailable"];
}

export interface WorkItemStatusPresentation {
  label: string;
  tone: WorkItemStatusTone;
  detail: string | null;
}

function distinctDetail(label: string, detail: string | null): string | null {
  return detail && detail !== label ? detail : null;
}

const PUBLICATION_PHASE_LABELS: Record<WorkItemPublicationPhase, string> = {
  "finalization-invalidated": "Finalization invalidated",
  "review-repair": "Review feedback needed",
  "ready-for-finalization": "Ready for finalization",
  "checkpoint-pending": "Checkpoint pending",
  "pull-request-draft": "Delivery ready state not recorded",
  "awaiting-merge": "Awaiting merge",
  "acceptance-observed": "Acceptance observed",
  deferred: "Change deferred",
  abandoned: "Change abandoned",
};

function publicationStatus(item: WorkItemCardView): WorkItemStatusPresentation | null {
  if (item.scope !== "change-publication" || !item.publication_phase) return null;
  if (item.action.kind === "resolve-attention" || item.action.kind === "adopt-external-head") {
    return {
      label: "Publication attention",
      tone: "attention",
      detail: distinctDetail("Publication attention", item.needs_headline ?? item.next_step),
    };
  }
  if (item.publication_phase === "pull-request-draft" && item.needs === "you") {
    return {
      label: "Publication needs reconciliation",
      tone: "attention",
      detail: distinctDetail("Publication needs reconciliation", item.needs_headline ?? item.next_step),
    };
  }
  const phaseLabel = PUBLICATION_PHASE_LABELS[item.publication_phase];
  const progress = item.readiness?.progress;
  if (progress) {
    const label = DELIVERY_PROGRESS_LABELS[progress];
    return { label, tone: progressTone(progress), detail: distinctDetail(label, phaseLabel) };
  }
  // Engine readiness owns the reported state; the lifecycle phase is identified separately.
  if (item.readiness) {
    const label = READINESS_STATUS_LABELS[item.readiness.status];
    return {
      label,
      tone: readinessTone(item.readiness.status),
      detail: distinctDetail(label, phaseLabel),
    };
  }
  const tone: WorkItemStatusTone =
    item.publication_phase === "acceptance-observed"
      ? "complete"
      : item.publication_phase === "finalization-invalidated" ||
          item.publication_phase === "review-repair" ||
          item.publication_phase === "awaiting-merge"
        ? "attention"
        : item.publication_phase === "checkpoint-pending"
          ? "active"
          : item.publication_phase === "ready-for-finalization" || item.publication_phase === "pull-request-draft"
            ? "ready"
            : "neutral";
  return {
    label: phaseLabel,
    tone,
    detail: distinctDetail(phaseLabel, item.needs_headline),
  };
}

export function workItemStatus(item: WorkItemCardView): WorkItemStatusPresentation {
  const publication = publicationStatus(item);
  if (publication) return publication;
  const progress = item.readiness?.progress;
  if (progress) {
    const label = DELIVERY_PROGRESS_LABELS[progress];
    return { label, tone: progressTone(progress), detail: distinctDetail(label, item.needs_headline) };
  }
  if (item.readiness) {
    const label = READINESS_STATUS_LABELS[item.readiness.status];
    // Held custody without progress is neutral: the step names who holds it, never that work runs.
    const detail = item.readiness.status === "running" ? item.next_step : item.needs_headline;
    return {
      label,
      tone: readinessTone(item.readiness.status),
      detail: distinctDetail(label, detail),
    };
  }
  if (item.needs === "you") {
    return {
      label: "Needs you",
      tone: "attention",
      detail: item.needs_headline,
    };
  }
  if (item.needs === "dependency") {
    return { label: "Blocked", tone: "blocked", detail: item.needs_headline };
  }
  if (item.activity.state === "working") {
    return {
      label: "Claimed",
      tone: "neutral",
      detail: item.activity.worker_role ? WORKER_STATUS_LABELS[item.activity.worker_role] : "Agent",
    };
  }
  if (item.activity.state === "ready") {
    return { label: "Ready", tone: "ready", detail: null };
  }
  if (item.stage === "completed") {
    return { label: "Complete", tone: "complete", detail: null };
  }
  return { label: "Idle", tone: "neutral", detail: null };
}

export function workItemStatusClassName(tone: WorkItemStatusTone): string {
  switch (tone) {
    case "attention":
      return "border-error bg-error-low text-primary";
    case "blocked":
      return "border-warning bg-warning-low text-primary";
    case "active":
      return "border-info bg-info-low text-primary";
    case "complete":
      return "border-success bg-surface text-success";
    case "ready":
      return "border-contrast-low bg-surface text-primary";
    default:
      return "border-contrast-low bg-surface text-contrast-medium";
  }
}

export function workItemStatusLabel(item: WorkItemCardView): string {
  return workItemStatus(item).label;
}
