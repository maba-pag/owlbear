import type {
  ChangePauseUnavailableReason,
  DeliveryAcceptanceIdentitySource,
  DeliveryConfirmationKind,
  DeliveryCriterionStatus,
  DeliveryDecisionOrigin,
  DeliveryEvidenceVerdict,
  DeliveryFinalizationRules,
  DeliveryProgress,
  DeliveryReadinessChecksState,
  DeliveryReadinessStatus,
  DeliverySituation,
  DeliveryWaitingOn,
  DeliveryWorkerRole,
  MergeBlockReason,
  WorkItemActionKind,
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

/** Who made a recorded decision; only `decided` ones were asked of the user directly. */
export const DECISION_ORIGIN_LABELS: Record<DeliveryDecisionOrigin, string> = {
  decided: "Decided by you",
  approved: "Approved by you",
  autonomous: "Made by an agent",
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

/** Labels for Delivery's situation; Delivery decides which key applies and writes the headline. */
export const SITUATION_LABELS: Record<DeliverySituation, string> = {
  "with-agent": "With an agent",
  "ready-for-next-step": "Ready for next step",
  "your-decision": "Your decision",
  "waiting-on-github": "Waiting on GitHub",
  "waiting-on-delivery": "Waiting on Delivery",
  "waiting-on-dependency": "Waiting on another Outcome",
  "retrying-automatically": "Retrying automatically",
  "needs-attention": "Needs attention",
  pausing: "Pausing",
  paused: "Paused",
  abandoned: "Abandoned",
  done: "Done",
};

const SITUATION_TONES: Record<DeliverySituation, WorkItemStatusTone> = {
  "with-agent": "active",
  "ready-for-next-step": "ready",
  "your-decision": "attention",
  "waiting-on-github": "neutral",
  "waiting-on-delivery": "neutral",
  "waiting-on-dependency": "neutral",
  "retrying-automatically": "neutral",
  "needs-attention": "blocked",
  pausing: "neutral",
  paused: "neutral",
  abandoned: "neutral",
  done: "complete",
};

export function progressTone(progress: DeliveryProgress): WorkItemStatusTone {
  return SITUATION_TONES[progress.situation];
}

export function progressLabel(progress: DeliveryProgress): string {
  if (progress.situation === "waiting-on-dependency" && progress.waiting_on === "change")
    return "Waiting on another Change";
  // The portfolio counts these as "Needs you"; the same item keeps that name everywhere.
  if (progress.situation === "needs-attention" && progress.waiting_on === "you") return "Needs you";
  return SITUATION_LABELS[progress.situation];
}

/** Element id of a Work Item's first open request; links ending in this hash focus it. */
export const OPEN_REQUEST_ANCHOR = "open-request";

function formatClock(iso: string | null | undefined): string | null {
  if (!iso) return null;
  const at = new Date(iso);
  return Number.isNaN(at.getTime()) ? null : at.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

const WAITING_ON_LABELS: Record<Exclude<DeliveryWaitingOn, "none">, string> = {
  you: "you",
  agent: "an agent",
  delivery: "Delivery",
  github: "GitHub",
  outcome: "an Outcome",
  change: "another Change",
};

/** "Waiting on X since T · not before T", from the facts Delivery supplied with its situation. */
export function progressWaitLine(progress: DeliveryProgress): string | null {
  const parts: string[] = [];
  const since = formatClock(progress.since);
  if (progress.waiting_on !== "none")
    parts.push(`Waiting on ${WAITING_ON_LABELS[progress.waiting_on]}${since ? ` since ${since}` : ""}`);
  const eligible = progress.next_eligible_at ? new Date(progress.next_eligible_at) : null;
  const next = formatClock(progress.next_eligible_at);
  if (eligible && next && eligible.getTime() > Date.now()) parts.push(`not before ${next}`);
  return parts.length ? parts.join(" · ") : null;
}

/** The Change advances once the user runs its prompt in a new chat, and nothing says to wait first. */
export function changeAwaitsPrompt(group: {
  change_id: string;
  progress?: DeliveryProgress | null;
  items: WorkItemCardView[];
}): boolean {
  const progress = group.progress;
  if (progress?.situation !== "ready-for-next-step") return false;
  const eligible = progress.next_eligible_at ? Date.parse(progress.next_eligible_at) : Number.NaN;
  if (eligible > Date.now()) return false;
  return group.items.some((item) => isContinuationPrompt(item.readiness?.prompt, group.change_id));
}

/** Only the engine-authored `/continue-change <this Change> …` prompt is a continuation prompt. */
export function isContinuationPrompt(prompt: string | null | undefined, changeId: string): prompt is string {
  return typeof prompt === "string" && prompt.startsWith(`/continue-change ${changeId} `);
}

const CONTINUATION_OPERATIONS: ReadonlySet<WorkItemActionKind> = new Set([
  "start-orchestration",
  "finalize",
  "reconcile-checkpoint",
  "sync-target",
  "mark-ready",
  "observe-acceptance",
]);

/** The Change's next step: the first executable agent continuation prompt among its cards, if any. */
export function changeContinuationPrompt(items: WorkItemCardView[], changeId: string): string | null {
  for (const item of items) {
    const readiness = item.readiness;
    if (
      readiness?.executable &&
      readiness.operation &&
      CONTINUATION_OPERATIONS.has(readiness.operation) &&
      isContinuationPrompt(readiness.prompt, changeId)
    )
      return readiness.prompt;
  }
  return null;
}

export const CONTINUATION_PROMPT_HELP = "Run it in Copilot Chat. Copying does not start an agent.";

export const REVISION_PROMPT_HELP =
  "Copies a /design prompt. Add the requirement change and run it in Copilot Chat. Copying does not start an agent.";

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
  deferred: "Change paused",
  abandoned: "Change abandoned",
};

function publicationStatus(item: WorkItemCardView): WorkItemStatusPresentation | null {
  if (item.scope !== "change-publication" || !item.publication_phase) return null;
  // Delivery's composed situation is the one answer; phase-specific copy is only a fallback.
  const progress = item.readiness?.progress;
  if (progress) return progressStatus(progress);
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

export function progressStatus(progress: DeliveryProgress): WorkItemStatusPresentation {
  const label = progressLabel(progress);
  return { label, tone: progressTone(progress), detail: distinctDetail(label, progress.headline) };
}

export function workItemStatus(item: WorkItemCardView): WorkItemStatusPresentation {
  const publication = publicationStatus(item);
  if (publication) return publication;
  const progress = item.readiness?.progress;
  if (progress) return progressStatus(progress);
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
