import {
  PButton,
  PHeading,
  PIcon,
  PInputText,
  PModal,
  PSelect,
  PSelectOption,
  PTag,
} from "@porsche-design-system/components-react";
import { type ReactNode, useEffect, useState } from "react";
import {
  type BackwardMovePreview,
  type DeliveryConfirmationScope,
  type DeliveryCriterionStatus,
  type DeliveryEvidenceItem,
  type DeliveryReadiness,
  type DeliveryRequest,
  type DeliveryRequestResolution,
  type DeliveryWorkerRole,
  isUnavailableDetail,
  type MergeOffer,
  type PublicationCheckBlockingState,
  type PublicationChecksObservationResponse,
  WorkItemApiError,
  type WorkItemAvailableDetailResponse,
  type WorkItemDetailResponse,
  type WorkItemPublicationPhase,
  type WorkItemStage,
  type WorkItemUnavailableDetailResponse,
} from "../api/workItems";
import CopyCommand from "./CopyCommand";
import { SectionCard, StatusChip } from "./DeliveryPrimitives";
import MergeApprovalDialog from "./MergeApprovalDialog";
import {
  CONFIRMATION_KIND_LABELS,
  CONTINUATION_PROMPT_HELP,
  changePauseUnavailableMessage,
  DECISION_ORIGIN_LABELS,
  EVIDENCE_STATUS_LABELS,
  EVIDENCE_STATUS_TONES,
  EVIDENCE_VERDICT_LABELS,
  FINALIZATION_RULES_LABELS,
  IDENTITY_SOURCE_LABELS,
  isContinuationPrompt,
  MERGE_BLOCK_LABELS,
  NEXT_ACTOR_LABELS,
  PROGRESS_STAGE_LABELS,
  progressLabel,
  progressTone,
  progressWaitLine,
  READINESS_CHECKS_LABELS,
  READINESS_STATUS_LABELS,
  REVISION_PROMPT_HELP,
  readinessTone,
  workItemStatus,
  workItemStatusLabel,
} from "./workItemPresentation";

type FieldValueEvent = {
  target?: { value?: unknown };
  detail?: { value?: unknown };
};

function fieldValue(event: FieldValueEvent): string {
  const value = event.detail?.value ?? event.target?.value;
  return typeof value === "string" ? value : "";
}

function ConfirmationContent({ children, onClose }: { children: ReactNode; onClose: () => void }) {
  return (
    <div
      className="grid w-[min(32rem,calc(100vw-2rem))] gap-static-md text-primary"
      onKeyDownCapture={(event) => {
        if (event.key !== "Escape") return;
        event.preventDefault();
        onClose();
      }}
    >
      {children}
    </div>
  );
}

interface WorkItemDetailProps {
  detail: WorkItemAvailableDetailResponse;
  pendingAction: string | null;
  actionError: Error | null;
  actionResult: string | null;
  onAnswerRequest: (requestId: string, resolution: DeliveryRequestResolution) => Promise<Error | null>;
  onClearBlock: (blockId: string, note: string, locators: string[]) => Promise<Error | null>;
  onGrantAttempt: (blockId: string) => Promise<Error | null>;
  onReleaseStuckWorker: (attemptId: string, claimId: string) => Promise<Error | null>;
  onPreviewBackward: (target: WorkItemStage) => Promise<BackwardMovePreview | null>;
  onMoveBackward: (target: WorkItemStage, reason: string, snapshotVersion: string) => Promise<Error | null>;
  onReconcilePublication: () => Promise<Error | null>;
  onMarkPublicationReady: () => Promise<Error | null>;
  publicationChecks: PublicationChecksObservationResponse | null;
  publicationChecksError: Error | null;
  publicationChecksStale: boolean;
  isObservingPublicationChecks: boolean;
  onObservePublicationChecks: () => Promise<Error | null>;
  onObserveAcceptance: () => Promise<Error | null>;
  onApproveMerge: (offerId: string, submissionId: string) => Promise<Error | null>;
  onAdoptExternalHeadAfterAcceptanceAttention: (
    expectedDispositionId: string,
    expectedHead: string,
    adoptedHead: string,
  ) => Promise<Error | null>;
  onResolveAttention: (expectedDispositionId: string) => Promise<Error | null>;
  onSupersedePublication: () => Promise<Error | null>;
  onSyncTarget: () => Promise<Error | null>;
  onAbortTargetSync: (expectedDispositionId: string, targetHead: string, operationId: string) => Promise<Error | null>;
  onResolveTargetSync: (
    expectedDispositionId: string,
    targetHead: string,
    operationId: string,
  ) => Promise<Error | null>;
  onDeferChange: (reason: string) => Promise<Error | null>;
  onResumeChange: () => Promise<Error | null>;
  onAbandonChange: (reason: string) => Promise<Error | null>;
  onCleanupAbandonedChange: () => Promise<Error | null>;
  onDiscardAbandonedTargetSync: (targetHead: string, operationId: string) => Promise<Error | null>;
  onCleanupCompletedChange: (completionId: string) => Promise<Error | null>;
  onRecoverChangeWorktree: (recoveryReviewedHead: string) => Promise<Error | null>;
  /** The Change's continuation prompt from its portfolio cards; the Change's next step. */
  changeContinuationPrompt?: string | null;
}

const WORKER_ROLE_LABELS: Record<DeliveryWorkerRole, string> = {
  planner: "Planner",
  builder: "Builder",
};

const REQUEST_KIND_LABELS: Record<DeliveryRequest["kind"], string> = {
  decision: "Decision",
  action: "Action",
};

const TASK_STATUS_LABELS: Record<WorkItemAvailableDetailResponse["item"]["tasks"][number]["status"], string> = {
  pending: "Pending",
  active: "Active",
  reviewed: "Reviewed",
};

function DetailHeader({ detail }: Pick<WorkItemDetailProps, "detail">) {
  const card = {
    ...detail.item.card,
    readiness: detail.item.card.readiness ?? detail.item.readiness,
  };
  return (
    <div className="flex min-w-0 flex-wrap items-start justify-between gap-static-sm">
      <div className="min-w-0">
        <span className="text-xs text-contrast-medium">
          <strong className="text-primary">{detail.item.change_title}</strong>
          {" / "}
          {card.scope === "outcome" ? <code>{card.work_item_id}</code> : "Change publication"}
        </span>
        <PHeading id="work-detail-heading" tag="h2" size="lg">
          {card.scope === "outcome" ? card.title : "Publication"}
        </PHeading>
      </div>
      <div className="flex flex-wrap gap-static-xs">
        <StatusChip label={workItemStatusLabel(card)} tone={workItemStatus(card).tone} />
      </div>
    </div>
  );
}

function RequestControl({
  request,
  superseded,
  pending,
  onAnswer,
}: {
  request: DeliveryRequest;
  superseded: boolean;
  pending: boolean;
  onAnswer: WorkItemDetailProps["onAnswerRequest"];
}) {
  const [selectedOptionId, setSelectedOptionId] = useState("");
  const [responseText, setResponseText] = useState("");
  const canSubmit = Boolean(request.kind === "decision" ? selectedOptionId : responseText.trim()) && !pending;
  const answer = () =>
    onAnswer(request.request_id, {
      selected_option_id: selectedOptionId || null,
      response_text: request.kind === "action" ? responseText.trim() || null : null,
    });
  if (request.resolution) {
    const answerText =
      request.resolution.response_text ||
      request.options.find((option) => option.option_id === request.resolution?.selected_option_id)?.label ||
      "Answered";
    if (superseded) {
      return (
        <p className="mt-static-xs text-sm text-contrast-medium">
          <PTag compact>Superseded</PTag> <s>{answerText}</s> · replaced by a later decision
        </p>
      );
    }
    return <p className="mt-static-xs text-sm text-success">{answerText}</p>;
  }
  return (
    <div className="mt-static-sm grid gap-static-sm">
      {request.kind === "decision" ? (
        <PSelect
          compact
          label="Decision"
          name={`request-${request.request_id}-option`}
          value={selectedOptionId}
          disabled={pending}
          onChange={(event) => setSelectedOptionId(fieldValue(event as FieldValueEvent))}
        >
          <PSelectOption value="">Select an option</PSelectOption>
          {request.options.map((option) => (
            <PSelectOption key={option.option_id} value={option.option_id}>
              {option.label}
            </PSelectOption>
          ))}
        </PSelect>
      ) : null}
      {request.kind === "action" ? (
        <PInputText
          compact
          name={`request-${request.request_id}-answer`}
          label="Action response"
          value={responseText}
          disabled={pending}
          onChange={(event) => setResponseText(fieldValue(event as FieldValueEvent))}
          onInput={(event) => setResponseText(fieldValue(event as FieldValueEvent))}
        />
      ) : null}
      <PButton className="w-fit" type="button" compact disabled={!canSubmit} onClick={() => void answer()}>
        {pending ? "Submitting..." : "Submit answer"}
      </PButton>
    </div>
  );
}

function RequestScope({
  scope,
  detail,
}: {
  scope: DeliveryConfirmationScope;
  detail: WorkItemAvailableDetailResponse;
}) {
  const statements = new Map(
    (detail.item.evidence?.criteria ?? []).map((criterion) => [criterion.acceptance_id, criterion.statement]),
  );
  return (
    <dl
      className="mt-static-xs grid grid-cols-[auto_minmax(0,1fr)] gap-x-static-md text-sm"
      data-testid={`request-scope-${scope.kind}`}
    >
      <dt className="text-contrast-medium">Applies to</dt>
      <dd>{CONFIRMATION_KIND_LABELS[scope.kind]}</dd>
      <dt className="text-contrast-medium">Criteria</dt>
      <dd>
        <ul className="grid gap-1">
          {scope.acceptance.map((reference) => (
            <li key={reference.acceptance_id}>
              <code>{reference.acceptance_id}</code> {statements.get(reference.acceptance_id) ?? ""}
            </li>
          ))}
        </ul>
      </dd>
      <dt className="text-contrast-medium">Procedure</dt>
      <dd className="break-words">{scope.procedure}</dd>
    </dl>
  );
}

function RequestsSection({ detail, pendingAction, onAnswerRequest }: WorkItemDetailProps) {
  if (detail.item.card.scope !== "outcome") return null;
  const requests = detail.item.requests;
  if (requests.length === 0) return null;
  const superseded = new Set(detail.item.superseded_request_ids ?? []);
  return (
    <section aria-labelledby="work-requests-heading">
      <PHeading id="work-requests-heading" tag="h3" size="md">
        Requests
      </PHeading>
      <div className="mt-static-sm grid gap-static-md">
        {requests.map((request) => (
          <article key={request.request_id} className="border-l-2 border-info pl-static-sm">
            <div className="flex flex-wrap items-center justify-between gap-static-xs">
              <strong className="text-sm">{request.summary}</strong>
              <PTag compact>{REQUEST_KIND_LABELS[request.kind]}</PTag>
            </div>
            {request.applies_to ? <RequestScope scope={request.applies_to} detail={detail} /> : null}
            <RequestControl
              request={request}
              superseded={superseded.has(request.request_id)}
              pending={pendingAction !== null}
              onAnswer={onAnswerRequest}
            />
          </article>
        ))}
      </div>
    </section>
  );
}

function ChangeDispositionSection(props: WorkItemDetailProps) {
  const [reason, setReason] = useState("");
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [actionFailed, setActionFailed] = useState(false);
  const phase = props.detail.item.publication?.phase;
  if (props.detail.item.abandon_available !== true) return null;
  const canSubmit = reason.trim().length > 0 && props.pendingAction === null;
  const abandon = async () => {
    const error = await props.onAbandonChange(reason.trim());
    setActionFailed(error !== null);
    if (!error) setConfirmOpen(false);
  };
  return (
    <details className="border-t border-contrast-low pt-static-sm" aria-labelledby="change-disposition-heading">
      <summary
        id="change-disposition-heading"
        className={[
          "cursor-pointer text-xs font-semibold uppercase text-contrast-medium",
          "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus",
        ].join(" ")}
      >
        Change lifecycle
      </summary>
      <div className="mt-static-md grid gap-static-sm">
        <p className="text-sm text-contrast-medium">
          Use only when the Change should leave its current delivery path. Abandonment is permanent.
        </p>
        {props.detail.item.change_progress?.situation === "paused" || phase === "deferred" ? (
          <p className="text-sm">This Change is paused and retains its worktree.</p>
        ) : null}
        <PInputText
          compact
          name="change-disposition-reason"
          label="Reason"
          value={reason}
          disabled={props.pendingAction !== null}
          onChange={(event) => setReason(fieldValue(event as FieldValueEvent))}
          onInput={(event) => setReason(fieldValue(event as FieldValueEvent))}
        />
        <div className="flex flex-wrap gap-static-sm">
          <PButton
            type="button"
            compact
            variant="secondary"
            disabled={!canSubmit}
            onClick={() => {
              setActionFailed(false);
              setConfirmOpen(true);
            }}
          >
            {props.pendingAction === "change-abandon" ? "Abandoning..." : "Abandon Change"}
          </PButton>
        </div>
      </div>
      {confirmOpen ? (
        <PModal
          open
          role="alertdialog"
          aria-modal="true"
          dismissButton={false}
          disableBackdropClick
          onDismiss={() => setConfirmOpen(false)}
          aria={{
            role: "alertdialog",
            "aria-label": "Confirm Change abandonment",
          }}
        >
          <ConfirmationContent onClose={() => setConfirmOpen(false)}>
            <PHeading tag="h2" size="lg">
              Confirm Change abandonment
            </PHeading>
            <p className="text-sm">
              Abandonment is permanent. The Change will be retained in Change history as an abandoned record.
            </p>
            <p className="text-sm text-contrast-medium">Reason: {reason.trim()}</p>
            {actionFailed && props.actionError ? <ActionFeedback error={props.actionError} result={null} /> : null}
            <div className="flex flex-wrap justify-end gap-static-xs">
              <PButton type="button" variant="secondary" onClick={() => setConfirmOpen(false)}>
                Cancel
              </PButton>
              <PButton type="button" disabled={props.pendingAction !== null} onClick={() => void abandon()}>
                {props.pendingAction === "change-abandon" ? "Abandoning..." : "Confirm abandon Change"}
              </PButton>
            </div>
          </ConfirmationContent>
        </PModal>
      ) : null}
    </details>
  );
}

export interface ChangePauseControlProps {
  changeId: string;
  paused: boolean;
  /** A recorded Pause request still draining the started step; Resume clears it. */
  pauseRequested?: boolean;
  /** Delivery's reason Pause would be refused, or null when the defer intent is accepted. */
  unavailableMessage: string | null;
  pendingAction: string | null;
  reasonName: string;
  actionError?: Error | null;
  onPause: (reason: string) => Promise<Error | null>;
  onResume: () => Promise<Error | null>;
}

/** Change-level Pause and Resume over the existing defer intent; Pause never stops a running step. */
export function ChangePauseControl(props: ChangePauseControlProps) {
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("");
  const busy = props.pendingAction !== null;
  const pause = async () => {
    const error = await props.onPause(reason.trim());
    if (!error) {
      setOpen(false);
      setReason("");
    }
  };
  return (
    <div className="grid min-w-0 gap-static-xs" data-testid={`change-pause-${props.changeId}`}>
      {props.paused || props.pauseRequested ? (
        <div className="flex flex-wrap items-center gap-static-xs">
          {props.pauseRequested && !props.paused ? (
            <PTag compact data-testid={`pause-requested-${props.changeId}`}>
              Pause requested
            </PTag>
          ) : null}
          <PButton
            className="w-fit"
            type="button"
            compact
            variant="secondary"
            disabled={busy}
            onClick={() => void props.onResume()}
          >
            {props.pendingAction === "change-resume" ? "Resuming..." : "Resume"}
          </PButton>
        </div>
      ) : open && props.unavailableMessage === null ? (
        <div className="flex flex-wrap items-end gap-static-xs">
          <PInputText
            compact
            name={props.reasonName}
            label="Pause reason"
            value={reason}
            disabled={busy}
            onChange={(event) => setReason(fieldValue(event as FieldValueEvent))}
            onInput={(event) => setReason(fieldValue(event as FieldValueEvent))}
          />
          <PButton type="button" compact disabled={!reason.trim() || busy} onClick={() => void pause()}>
            {props.pendingAction === "change-defer" ? "Pausing..." : "Confirm pause"}
          </PButton>
          <PButton type="button" compact variant="secondary" disabled={busy} onClick={() => setOpen(false)}>
            Cancel
          </PButton>
        </div>
      ) : (
        <div className="flex flex-wrap items-center gap-static-xs">
          <PButton
            type="button"
            compact
            variant="secondary"
            disabled={busy || props.unavailableMessage !== null}
            onClick={() => setOpen(true)}
          >
            Pause
          </PButton>
          {props.unavailableMessage !== null ? (
            <span className="text-xs text-contrast-medium">{props.unavailableMessage}</span>
          ) : null}
        </div>
      )}
      {props.actionError ? <ActionFeedback error={props.actionError} result={null} /> : null}
    </div>
  );
}

function ChangePauseSection(props: WorkItemDetailProps) {
  const item = props.detail.item;
  const phase = item.publication?.phase;
  const situation = item.change_progress?.situation;
  if (situation === "done" || situation === "abandoned" || phase === "abandoned") return null;
  const paused = situation === "paused" || phase === "deferred";
  const continuation = props.changeContinuationPrompt;
  const showContinuation = !paused && continuation && continuation !== item.readiness?.prompt;
  return (
    <section aria-labelledby="change-pause-heading" className="grid gap-static-xs">
      <PHeading id="change-pause-heading" tag="h3" size="sm">
        Change
      </PHeading>
      {showContinuation ? (
        <CopyCommand command={continuation} label="Copy continuation prompt" helper={CONTINUATION_PROMPT_HELP} />
      ) : null}
      <ChangePauseControl
        changeId={item.card.change_id}
        paused={paused}
        pauseRequested={item.pause_unavailable_reason === "pause-requested"}
        unavailableMessage={changePauseUnavailableMessage(item)}
        pendingAction={props.pendingAction}
        reasonName="change-pause-reason"
        onPause={props.onDeferChange}
        onResume={props.onResumeChange}
      />
      {item.revision_prompt ? (
        <CopyCommand command={item.revision_prompt} label="Change requirements" helper={REVISION_PROMPT_HELP} />
      ) : null}
    </section>
  );
}

function BlockSection({ detail, pendingAction, onClearBlock, onGrantAttempt }: WorkItemDetailProps) {
  const block = detail.item.block;
  const [note, setNote] = useState("");
  const [locator, setLocator] = useState("");
  if (!block) return null;
  const requestless = block.request_id === null;
  // Attempt-limit, return-limit and legacy exhaustion blocks keep their handoff: only their own card action lifts them.
  const clearable = requestless && detail.item.card.action.kind === "clear-block" && !block.resolution_note;
  const grantable = detail.item.card.action.kind === "grant-attempt" && !block.resolution_note;
  const reviseDesign = detail.item.card.action.kind === "resume-design" ? detail.item.card.action : null;
  const canClear = requestless && note.trim().length > 0 && locator.trim().length > 0 && pendingAction === null;
  return (
    <section className="border-l-4 border-warning bg-surface p-static-md" aria-labelledby="work-block-heading">
      <PHeading id="work-block-heading" tag="h3" size="md">
        Blocked
      </PHeading>
      <p className="mt-static-xs text-sm">{block.reason}</p>
      <p className="mt-static-xs text-sm text-contrast-medium">Clear when: {block.unblock_condition}</p>
      {reviseDesign?.command ? (
        <div className="mt-static-md grid gap-static-sm" data-testid="block-revise-design">
          <p className="text-sm">
            {reviseDesign.label}: Pause the Change, then revise its Design. The revision first keeps the Builder's work
            under refs and keeps completed tasks and answered requests.
          </p>
          <CopyCommand command={reviseDesign.command} />
        </div>
      ) : null}
      {grantable ? (
        <div className="mt-static-md grid gap-static-sm">
          <p className="text-sm">
            Granting adds exactly one more Builder attempt for this task. Earlier attempts stay recorded; if it fails
            again, the task stops here for your decision.
          </p>
          <PButton
            className="w-fit"
            type="button"
            compact
            disabled={pendingAction !== null}
            onClick={() => void onGrantAttempt(block.block_id)}
          >
            {pendingAction === "grant-attempt" ? "Granting..." : "Grant one more attempt"}
          </PButton>
        </div>
      ) : null}
      {clearable ? (
        <div className="mt-static-md grid gap-static-sm">
          <PInputText
            compact
            name="block-note"
            label="Operator note"
            value={note}
            disabled={pendingAction !== null}
            onChange={(event) => setNote(fieldValue(event as FieldValueEvent))}
            onInput={(event) => setNote(fieldValue(event as FieldValueEvent))}
          />
          <PInputText
            compact
            name="block-locator"
            label="Evidence locator"
            value={locator}
            disabled={pendingAction !== null}
            onChange={(event) => setLocator(fieldValue(event as FieldValueEvent))}
            onInput={(event) => setLocator(fieldValue(event as FieldValueEvent))}
          />
          <PButton
            className="w-fit"
            type="button"
            compact
            disabled={!canClear}
            onClick={() => void onClearBlock(block.block_id, note.trim(), [locator.trim()])}
          >
            {pendingAction === "clear" ? "Clearing..." : "Clear block"}
          </PButton>
        </div>
      ) : null}
    </section>
  );
}

function elapsedAge(startedAt: string): string {
  const elapsed = Math.max(Date.now() - new Date(startedAt).getTime(), 0);
  const hours = Math.floor(elapsed / 3_600_000);
  if (hours >= 24) return `${Math.floor(hours / 24)}d ${hours % 24}h`;
  if (hours > 0) return `${hours}h`;
  return `${Math.max(Math.floor(elapsed / 60_000), 0)}m`;
}

function ClaimSection({ detail, pendingAction, actionError, onReleaseStuckWorker }: WorkItemDetailProps) {
  const outcomeClaim = detail.item.active_claim;
  const finalizer = detail.item.held_finalizer;
  const claim = outcomeClaim
    ? { ...outcomeClaim, role: WORKER_ROLE_LABELS[outcomeClaim.worker_role] }
    : finalizer
      ? { ...finalizer, role: "Finalizer", continuation: true, task_id: null }
      : null;
  const [confirmTarget, setConfirmTarget] = useState<{ attemptId: string; claimId: string } | null>(null);
  const [actionFailed, setActionFailed] = useState(false);
  if (!claim) return null;
  const readiness = detail.item.card.readiness ?? detail.item.readiness;
  // A stall wait belongs to Delivery's automatic window-loss settlement, not to a user release.
  const releasable =
    (finalizer !== null || outcomeClaim?.worker_role === "planner" || outcomeClaim?.worker_role === "builder") &&
    Boolean(claim.attempt_id && claim.claim_id) &&
    readiness?.status === "running";
  // Polling may replace the claim; the dialog only ever confirms the claim it was opened for.
  const confirmOpen =
    releasable &&
    confirmTarget !== null &&
    confirmTarget.attemptId === claim.attempt_id &&
    confirmTarget.claimId === claim.claim_id;
  const closeConfirmation = () => setConfirmTarget(null);
  const release = async () => {
    if (!confirmTarget) return;
    const error = await onReleaseStuckWorker(confirmTarget.attemptId, confirmTarget.claimId);
    setActionFailed(error !== null);
    if (!error) closeConfirmation();
  };
  return (
    <section aria-labelledby="work-claim-heading">
      <PHeading id="work-claim-heading" tag="h3" size="md">
        Active claim
      </PHeading>
      <dl className="mt-static-sm grid gap-static-xs text-sm">
        <div className="flex justify-between gap-static-sm">
          <dt>Role</dt>
          <dd>{claim.role}</dd>
        </div>
        <div className="flex justify-between gap-static-sm">
          <dt>Started</dt>
          <dd>{elapsedAge(claim.started_at)} ago</dd>
        </div>
        <div className="flex justify-between gap-static-sm">
          <dt>Routing</dt>
          <dd>{claim.continuation ? "Engine continuation" : "Dispatched worker"}</dd>
        </div>
        <div className="flex justify-between gap-static-sm break-all">
          <dt>Recorded host</dt>
          <dd>{claim.owner_id}</dd>
        </div>
        <div className="flex justify-between gap-static-sm break-all">
          <dt>Recorded process</dt>
          <dd>{claim.process_id}</dd>
        </div>
        {claim.task_id ? (
          <div className="flex justify-between gap-static-sm">
            <dt>Task</dt>
            <dd>{claim.task_id}</dd>
          </div>
        ) : null}
      </dl>
      <p className="mt-static-xs text-sm leading-relaxed">
        Host and process are the routing provenance recorded when custody was granted, not evidence that the worker is
        still running.
      </p>
      {claim.continuation ? (
        <p className="mt-static-md text-sm leading-relaxed" data-testid="claim-continuation-custody">
          Delivery holds this custody as an engine continuation.
        </p>
      ) : null}
      {releasable ? (
        <PButton
          className="mt-static-md"
          type="button"
          compact
          variant="secondary"
          disabled={pendingAction !== null}
          onClick={() => {
            setActionFailed(false);
            setConfirmTarget({ attemptId: claim.attempt_id, claimId: claim.claim_id });
          }}
        >
          Release stuck worker
        </PButton>
      ) : null}
      {confirmOpen ? (
        <PModal
          open
          role="alertdialog"
          aria-modal="true"
          dismissButton={false}
          disableBackdropClick
          onDismiss={closeConfirmation}
          aria={{ role: "alertdialog", "aria-label": "Release stuck worker" }}
        >
          <ConfirmationContent onClose={closeConfirmation}>
            <PHeading tag="h2" size="lg">
              Release stuck worker
            </PHeading>
            <p className="text-sm">
              Use this only for a worker whose chat was stopped or whose VS Code window closed. Delivery records the
              attempt as failed, and it counts toward this work's retry budget.
            </p>
            <p className="text-sm">
              The worktree, including uncommitted work, is preserved for the next attempt. Delivery refuses the release
              and changes nothing while any process still uses the worktree or if it changed in the last 30 seconds.
            </p>
            <dl className="grid gap-static-xs break-all text-sm">
              <dt>Attempt</dt>
              <dd>{confirmTarget?.attemptId}</dd>
              <dt>Claim</dt>
              <dd>{confirmTarget?.claimId}</dd>
            </dl>
            {actionFailed && actionError ? <ActionFeedback error={actionError} result={null} /> : null}
            <div className="flex flex-wrap justify-end gap-static-xs">
              <PButton type="button" variant="secondary" onClick={closeConfirmation}>
                Cancel
              </PButton>
              <PButton type="button" disabled={pendingAction !== null} onClick={() => void release()}>
                {pendingAction === "release-stuck" ? "Releasing..." : "Confirm release"}
              </PButton>
            </div>
          </ConfirmationContent>
        </PModal>
      ) : null}
    </section>
  );
}

function ExceptionalStateSection({ detail }: Pick<WorkItemDetailProps, "detail">) {
  const { return_context: returned, recovery_attention: recovery, retry_diagnostic: retry } = detail.item;
  if (!returned && !recovery && !retry) return null;
  return (
    <section aria-labelledby="work-attention-heading">
      <PHeading id="work-attention-heading" tag="h3" size="md">
        Current exception
      </PHeading>
      <div className="mt-static-sm grid gap-static-md text-sm">
        {returned ? (
          <AttentionItem
            label={`Returned to ${PROGRESS_STAGE_LABELS[returned.target]}`}
            reason={returned.reason}
            retry={returned.target === "design" ? `Resume /design ${detail.item.card.change_id}.` : undefined}
            evidence={returned.locators.join(", ")}
            sourceBoundary={returned.source_boundary}
          />
        ) : null}
        {recovery ? (
          <AttentionItem label="Recovery attention" reason={recovery.reason} retry={recovery.retry_condition} />
        ) : null}
        {retry ? (
          <AttentionItem
            label="Retry refused"
            reason={
              `${retry.code}: ${retry.transition.failure_code} for attempt ${retry.attempt_id} ` +
              `and claim ${retry.transition.claim_id} remains active because host worker-exclusion evidence is missing.`
            }
            retry="Do not retry or release until supported host exclusion is verified."
          />
        ) : null}
      </div>
    </section>
  );
}

function CourseChangesSection({ detail }: Pick<WorkItemDetailProps, "detail">) {
  const moves = detail.item.operator_moves;
  if (moves.length === 0) return null;
  return (
    <section aria-labelledby="work-course-changes-heading">
      <h3 id="work-course-changes-heading" className="text-xs font-semibold uppercase text-contrast-medium">
        Recorded Change course changes
      </h3>
      <ol className="mt-static-sm grid list-decimal gap-static-md pl-static-lg text-sm">
        {moves.map((move) => (
          <li key={move.move_id}>
            <strong>
              {move.outcome_id} moved back to {PROGRESS_STAGE_LABELS[move.destination]}
            </strong>
            <p className="mt-static-xs">{move.reason}</p>
            <p className="mt-static-xs text-contrast-medium">Reset: {move.invalidated_outcome_ids.join(", ")}</p>
          </li>
        ))}
      </ol>
    </section>
  );
}

function AttentionItem({
  label,
  reason,
  retry,
  evidence,
  sourceBoundary,
}: {
  label: string;
  reason: string;
  retry?: string;
  evidence?: string;
  sourceBoundary?: string | null;
}) {
  return (
    <div>
      <strong>{label}</strong>
      <p>{reason}</p>
      {retry ? <p className="text-contrast-medium">Next: {retry}</p> : null}
      {evidence ? <p className="text-contrast-medium">Evidence: {evidence}</p> : null}
      {sourceBoundary ? <p className="text-contrast-medium">Source boundary: {sourceBoundary}</p> : null}
    </div>
  );
}

const STAGES: WorkItemStage[] = ["design", "planning", "implementation", "completed"];

function BackwardMoveSection({ detail, pendingAction, onPreviewBackward, onMoveBackward }: WorkItemDetailProps) {
  const currentStage = detail.item.card.stage;
  const available = currentStage ? STAGES.slice(0, STAGES.indexOf(currentStage)) : [];
  const [target, setTarget] = useState<WorkItemStage | "">("");
  const [reason, setReason] = useState("");
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [preview, setPreview] = useState<BackwardMovePreview | null>(null);
  const [previewStale, setPreviewStale] = useState(false);
  const targetIsAvailable = target !== "" && available.includes(target);
  const canMove = targetIsAvailable && Boolean(reason.trim()) && pendingAction === null;
  useEffect(() => {
    if (!target || targetIsAvailable) return;
    setTarget("");
    setPreview(null);
    setConfirmOpen(false);
  }, [target, targetIsAvailable]);
  useEffect(() => {
    if (!preview || preview.snapshot_version === detail.item.snapshot_version) return;
    setPreview(null);
    setConfirmOpen(false);
    setPreviewStale(true);
  }, [detail.item.snapshot_version, preview]);
  if (detail.item.card.scope !== "outcome" || available.length === 0) return null;
  const move = async () => {
    if (!target || !preview || preview.snapshot_version !== detail.item.snapshot_version) return;
    const error = await onMoveBackward(target, reason.trim(), preview.snapshot_version);
    if (!error) setConfirmOpen(false);
  };
  const review = async () => {
    if (!targetIsAvailable) return;
    setPreviewStale(false);
    const next = await onPreviewBackward(target);
    if (!next) return;
    setPreview(next);
    setConfirmOpen(true);
  };
  return (
    <details>
      <summary className="cursor-pointer text-xs font-semibold uppercase text-contrast-medium">
        Administrative actions
      </summary>
      <div className="mt-static-md">
        <div className="mt-static-sm flex flex-wrap items-end gap-static-sm">
          <PSelect
            compact
            className="w-48"
            label="Earlier stage"
            name="backward-stage"
            value={target}
            disabled={pendingAction !== null}
            onChange={(event) => {
              setTarget(fieldValue(event as FieldValueEvent) as WorkItemStage | "");
              setPreview(null);
              setPreviewStale(false);
            }}
          >
            <PSelectOption value="">Select a stage</PSelectOption>
            {available.map((stage) => (
              <PSelectOption key={stage} value={stage}>
                {PROGRESS_STAGE_LABELS[stage]}
              </PSelectOption>
            ))}
          </PSelect>
          <PInputText
            compact
            className="min-w-48 flex-1"
            name="backward-reason"
            label="Reason"
            value={reason}
            disabled={pendingAction !== null}
            onChange={(event) => setReason(fieldValue(event as FieldValueEvent))}
            onInput={(event) => setReason(fieldValue(event as FieldValueEvent))}
          />
          <PButton
            className="w-fit"
            type="button"
            compact
            variant="secondary"
            disabled={!canMove}
            onClick={() => void review()}
          >
            {pendingAction === "preview" ? "Preparing preview..." : "Review backward move"}
          </PButton>
        </div>
        {previewStale ? (
          <p className="mt-static-md border-l-4 border-warning bg-surface p-static-sm text-sm" role="status">
            The backward-move preview expired because Delivery changed. Review the move again.
          </p>
        ) : null}
        {confirmOpen ? (
          <PModal
            open
            role="alertdialog"
            aria-modal="true"
            dismissButton={false}
            disableBackdropClick
            onDismiss={() => setConfirmOpen(false)}
            aria={{
              role: "alertdialog",
              "aria-label": "Confirm backward move",
            }}
          >
            <ConfirmationContent onClose={() => setConfirmOpen(false)}>
              <PHeading tag="h2" size="lg">
                Move to {target ? PROGRESS_STAGE_LABELS[target] : ""}
              </PHeading>
              <p className="text-sm">The following Outcomes will be reset:</p>
              <ul className="grid list-disc gap-static-xs pl-static-lg text-sm">
                {preview?.invalidated_outcome_ids.map((outcomeId) => (
                  <li key={outcomeId}>{outcomeId}</li>
                ))}
              </ul>
              <p className="text-sm text-contrast-medium">Reason: {reason.trim()}</p>
              <div className="flex flex-wrap justify-end gap-static-xs">
                <PButton type="button" variant="secondary" onClick={() => setConfirmOpen(false)}>
                  Cancel
                </PButton>
                <PButton type="button" disabled={pendingAction !== null} onClick={() => void move()}>
                  {pendingAction === "move" ? "Moving..." : "Confirm backward move"}
                </PButton>
              </div>
            </ConfirmationContent>
          </PModal>
        ) : null}
      </div>
    </details>
  );
}

function SemanticDetail({ detail }: Pick<WorkItemDetailProps, "detail">) {
  const item = detail.item;
  if (item.card.scope !== "outcome") return null;
  return (
    <>
      {item.acceptance.length > 0 ? (
        <details>
          <summary
            id="work-acceptance-heading"
            className="cursor-pointer text-xs font-semibold uppercase text-contrast-medium"
          >
            Acceptance ({item.acceptance.length})
          </summary>
          <ol className="mt-static-sm grid list-decimal gap-static-sm pl-static-lg text-sm text-primary">
            {item.acceptance.map((observation) => (
              <li key={observation}>{observation}</li>
            ))}
          </ol>
        </details>
      ) : null}
      {item.tasks.length > 0 ? (
        <details>
          <summary
            id="work-evidence-heading"
            className="cursor-pointer text-xs font-semibold uppercase text-contrast-medium"
          >
            Delivery task evidence ({item.tasks.length})
          </summary>
          <div className="mt-static-sm grid gap-static-md">
            {item.tasks.map((task) => (
              <article key={task.task_id} className="border-l-2 border-contrast-low pl-static-sm text-sm text-primary">
                <div className="flex flex-wrap items-start justify-between gap-static-xs">
                  <strong>{task.title}</strong>
                  <PTag compact>{TASK_STATUS_LABELS[task.status]}</PTag>
                </div>
                <p className="mt-static-xs">{task.result}</p>
                {task.completed_commit ? (
                  <code
                    className="mt-static-xs inline-block bg-canvas px-static-xs py-1 text-xs text-contrast-medium"
                    title={task.completed_commit}
                  >
                    {task.completed_commit.slice(0, 12)}
                  </code>
                ) : null}
              </article>
            ))}
          </div>
        </details>
      ) : null}
      {item.dependencies.length > 0 || item.commitments.length > 0 ? (
        <details>
          <summary className="cursor-pointer text-xs font-semibold uppercase text-contrast-medium">References</summary>
          <ol className="mt-static-sm grid list-decimal gap-static-md pl-static-lg text-sm text-primary">
            {item.dependencies.map((dependency) => (
              <li key={dependency.outcome_id}>
                <strong className="block text-xs">{dependency.outcome_id}</strong>
                {dependency.title} · {PROGRESS_STAGE_LABELS[dependency.stage]}
              </li>
            ))}
            {item.commitments.map((commitment) => (
              <li key={commitment.commitment_id}>
                <strong className="block text-xs">{commitment.commitment_id}</strong>
                {commitment.statement}
              </li>
            ))}
          </ol>
        </details>
      ) : null}
      <details>
        <summary className="cursor-pointer text-xs font-semibold uppercase text-contrast-medium">
          Technical identity
        </summary>
        <code className="mt-static-sm block break-all text-xs text-contrast-medium">
          {item.card.change_id} / {item.card.item_key}
        </code>
      </details>
    </>
  );
}

function DecisionsSection({ detail }: Pick<WorkItemDetailProps, "detail">) {
  const [onlyYours, setOnlyYours] = useState(false);
  const decisions = detail.item.decisions ?? [];
  if (decisions.length === 0) return null;
  const superseded = new Set(decisions.flatMap((decision) => decision.supersedes));
  const shown = onlyYours ? decisions.filter((decision) => decision.origin === "decided") : decisions;
  return (
    <details>
      <summary
        id="work-decisions-heading"
        className="cursor-pointer text-xs font-semibold uppercase text-contrast-medium"
      >
        Decisions ({decisions.length})
      </summary>
      <div className="mt-static-sm">
        <PButton
          type="button"
          variant="secondary"
          compact
          aria={{ "aria-pressed": onlyYours }}
          onClick={() => setOnlyYours(!onlyYours)}
        >
          {onlyYours ? "Show all decisions" : "Show only your decisions"}
        </PButton>
      </div>
      <ol
        aria-labelledby="work-decisions-heading"
        className="mt-static-sm grid list-decimal gap-static-md pl-static-lg text-sm text-primary"
      >
        {shown.map((decision) => (
          <li key={decision.decision_id} data-testid={`work-decision-${decision.decision_id}`}>
            <div className="flex flex-wrap items-center gap-static-xs">
              <strong className="text-xs">{decision.decision_id}</strong>
              <PTag compact>{DECISION_ORIGIN_LABELS[decision.origin]}</PTag>
              {superseded.has(decision.decision_id) ? <PTag compact>Superseded</PTag> : null}
            </div>
            <p className="mt-static-xs">{decision.statement}</p>
            <p className="text-xs text-contrast-medium">
              {decision.basis}
              {decision.supersedes.length > 0 ? ` · replaces ${decision.supersedes.join(", ")}` : ""}
            </p>
          </li>
        ))}
      </ol>
      {shown.length === 0 ? <p className="text-sm text-contrast-medium">You decided none of these directly.</p> : null}
    </details>
  );
}

function EvidenceRecord({ item }: { item: DeliveryEvidenceItem }) {
  const facts = [
    item.verdict ? EVIDENCE_VERDICT_LABELS[item.verdict] : "Legacy record",
    item.owner ? `owner: ${item.owner}` : null,
    item.reason,
    item.summary,
  ].filter(Boolean);
  return (
    <li className="text-xs text-contrast-medium">
      {facts.join(" · ")} · <code>{item.procedure}</code>
      {item.request_id ? (
        <>
          {" "}
          · request <code>{item.request_id}</code>
        </>
      ) : null}
      {item.locator ? (
        <>
          {" "}
          · <code data-testid="evidence-locator">{item.locator}</code>
        </>
      ) : null}{" "}
      · <code title={item.exact_commit}>{item.exact_commit.slice(0, 12)}</code>
    </li>
  );
}

function EvidenceSummary({ detail }: Pick<WorkItemDetailProps, "detail">) {
  const evidence = detail.item.evidence;
  if (!evidence) return null;
  const counts = (Object.keys(EVIDENCE_STATUS_LABELS) as DeliveryCriterionStatus[])
    .filter((status) => evidence.counts[status] > 0)
    .map((status) => `${evidence.counts[status]} ${EVIDENCE_STATUS_LABELS[status].toLowerCase()}`)
    .join(", ");
  const unattributed = evidence.unattributed.length + evidence.unattributed_truncated;
  return (
    <details data-testid="evidence-summary">
      <summary className="cursor-pointer text-xs font-semibold uppercase text-contrast-medium">
        Acceptance evidence ({counts || "no criteria"})
      </summary>
      <p className="mt-static-sm text-xs text-contrast-medium">
        {FINALIZATION_RULES_LABELS[evidence.finalization_rules]}
      </p>
      <ol className="mt-static-sm grid gap-static-md text-sm text-primary">
        {evidence.criteria.map((criterion) => (
          <li key={criterion.acceptance_id} data-testid={`evidence-${criterion.acceptance_id}`}>
            <div className="flex flex-wrap items-start justify-between gap-static-xs">
              <span>
                <code title={IDENTITY_SOURCE_LABELS[criterion.identity_source]}>{criterion.acceptance_id}</code>{" "}
                {criterion.statement}
              </span>
              <StatusChip
                label={EVIDENCE_STATUS_LABELS[criterion.status]}
                tone={EVIDENCE_STATUS_TONES[criterion.status]}
              />
            </div>
            {criterion.evidence.length > 0 ? (
              <ul className="mt-static-xs grid gap-1">
                {criterion.evidence.map((item) => (
                  <EvidenceRecord key={item.observation_id} item={item} />
                ))}
              </ul>
            ) : null}
            {criterion.evidence_truncated > 0 ? (
              <p className="mt-1 text-xs text-contrast-medium">
                {criterion.evidence_truncated} earlier record(s) not shown
              </p>
            ) : null}
          </li>
        ))}
      </ol>
      {unattributed > 0 ? (
        <div className="mt-static-sm">
          <p className="text-xs font-semibold text-contrast-medium">
            Records without a current criterion ({unattributed})
          </p>
          <ul className="mt-static-xs grid gap-1">
            {evidence.unattributed.map((item) => (
              <EvidenceRecord key={item.observation_id} item={item} />
            ))}
          </ul>
        </div>
      ) : null}
    </details>
  );
}

const PUBLICATION_PHASE_LABELS: Record<WorkItemPublicationPhase, string> = {
  "finalization-invalidated": "Finalization invalidated",
  "review-repair": "Review feedback repair",
  "ready-for-finalization": "Ready for finalization",
  "checkpoint-pending": "Checkpoint pending",
  "pull-request-draft": "Delivery ready state not recorded",
  "awaiting-merge": "Awaiting merge in GitHub",
  "acceptance-observed": "Acceptance observed",
  deferred: "Change paused",
  abandoned: "Change abandoned",
};

function IdentityRow({ label, value }: { label: string; value: string | number | null }) {
  if (value === null) return null;
  return (
    <>
      <dt className="text-contrast-medium">{label}</dt>
      <dd className="min-w-0 break-all font-mono text-xs">{value}</dd>
    </>
  );
}

function ReadinessBasisRows({ basis }: { basis: DeliveryReadiness["basis"] }) {
  return (
    <>
      <IdentityRow label="Source head" value={basis.source_head} />
      <IdentityRow label="Target branch head" value={basis.target_head} />
      <IdentityRow label="Engine operation" value={basis.continuation_id} />
      <IdentityRow label="Candidate head" value={basis.candidate_head} />
      <IdentityRow label="Reviewed head" value={basis.reviewed_head} />
      <IdentityRow label="Contract digest" value={basis.contract_digest} />
      <IdentityRow label="Frontier digest" value={basis.frontier_digest} />
      <IdentityRow label="Workspace fingerprint" value={basis.workspace_fingerprint} />
      <IdentityRow label="Diagnostic sequence" value={basis.diagnostic_sequence} />
    </>
  );
}

function ReadinessAttempt({ attempt }: { attempt: NonNullable<DeliveryReadiness["last_attempt"]> }) {
  return (
    <div className="mt-static-sm border-t border-contrast-low pt-static-sm" data-testid="readiness-last-attempt">
      <p className="flex flex-wrap items-center gap-static-xs text-sm">
        <strong>Last finalization attempt</strong>
        <StatusChip
          label={attempt.applicability === "current" ? "Applies to this candidate" : "Historical"}
          tone={attempt.applicability === "current" ? "attention" : "neutral"}
          testId="readiness-attempt-applicability"
        />
      </p>
      <p className="mt-1 text-sm leading-relaxed">{attempt.report.summary}</p>
      <dl className="mt-static-xs grid grid-cols-[auto_minmax(0,1fr)] gap-x-static-md text-xs">
        <dt className="text-contrast-medium">Category</dt>
        <dd>{attempt.report.request.category}</dd>
        <dt className="text-contrast-medium">Code</dt>
        <dd>
          <code>{attempt.report.request.code}</code>
        </dd>
        <dt className="text-contrast-medium">Checks</dt>
        <dd>{READINESS_CHECKS_LABELS[attempt.report.request.checks_state]}</dd>
        <IdentityRow label="Procedure" value={attempt.report.request.procedure_id} />
        <IdentityRow label="Proof fingerprint before" value={attempt.report.request.proof_fingerprint_before} />
        <IdentityRow label="Proof fingerprint after" value={attempt.report.request.proof_fingerprint_after} />
        <IdentityRow label="Report" value={attempt.report.report_id} />
        <IdentityRow label="Observed at" value={attempt.report.observed_at} />
      </dl>
    </div>
  );
}

/** Merge offer summary; the Approve merge control renders beside it. */
function MergeOfferSummary({ offer }: { offer: MergeOffer }) {
  const checks = offer.check_summary;
  const proof = offer.proof;
  return (
    <>
      <dl
        className="mt-static-xs grid grid-cols-[auto_minmax(0,1fr)] gap-x-static-md text-xs"
        data-testid="merge-offer"
      >
        <IdentityRow label="Pull request" value={`${offer.repository}#${offer.number} ${offer.title}`} />
        <IdentityRow label="Head" value={offer.head_sha.slice(0, 12)} />
        <IdentityRow label="Target" value={`${offer.base_branch} at ${offer.target_head.slice(0, 12)}`} />
        <IdentityRow label="Merge method" value={offer.merge_method} />
        <IdentityRow
          label="Required checks"
          value={
            `${checks.required_passed} passed, ${checks.required_pending} pending, ` +
            `${checks.required_failed} failed; ${checks.optional_failed} optional failed`
          }
        />
        <IdentityRow
          label="Proof"
          value={
            `${proof.observation_count} observations, review ${proof.review_id.slice(0, 12)}, ` +
            `proof target ${proof.proof_target.slice(0, 12)}`
          }
        />
      </dl>
      {proof.proof_target !== offer.target_head ? (
        <p className="mt-static-xs text-sm" data-testid="merge-offer-target-drift">
          {offer.base_branch} moved since the proof ({proof.proof_target.slice(0, 12)} to{" "}
          {offer.target_head.slice(0, 12)}). The proof does not cover the newer commits.
        </p>
      ) : null}
    </>
  );
}

/** Render engine-computed readiness. Eligibility is never recomputed here. */
function ReadinessSection({
  readiness,
  changeId,
  children,
}: {
  readiness: DeliveryReadiness | null | undefined;
  changeId: string;
  children?: ReactNode;
}) {
  if (!readiness) return null;
  const progress = readiness.progress;
  const timing = progress ? progressWaitLine(progress) : null;
  return (
    <SectionCard dataTestId="delivery-readiness" ariaLabel="Delivery readiness" className="p-static-sm">
      {progress ? (
        <div className="grid gap-static-xs" data-situation={progress.situation}>
          <div className="flex flex-wrap items-center gap-static-xs">
            <StatusChip label={progressLabel(progress)} tone={progressTone(progress)} testId="readiness-progress" />
            {timing ? (
              <span className="text-xs text-contrast-medium" data-testid="readiness-timing">
                {timing}
              </span>
            ) : null}
          </div>
          <p className="text-sm leading-relaxed" data-testid="readiness-headline">
            {progress.headline}
          </p>
        </div>
      ) : null}
      {readiness.merge_offer ? <MergeOfferSummary offer={readiness.merge_offer} /> : null}
      {children}
      {readiness.merge_attempt ? (
        <p className="mt-static-xs text-sm leading-relaxed" data-testid="merge-attempt">
          <a
            className="font-medium text-primary underline decoration-contrast-low underline-offset-2"
            href={readiness.merge_attempt.pr_url}
            target="_blank"
            rel="noreferrer"
          >
            Open the pull request in GitHub
          </a>{" "}
          (approved head {readiness.merge_attempt.approved_head.slice(0, 12)})
        </p>
      ) : null}
      {readiness.prompt ? (
        <pre
          className="mt-static-xs whitespace-pre-wrap break-words rounded-md bg-contrast-low p-static-xs text-xs"
          data-testid="readiness-prompt"
        >
          <code>{readiness.prompt}</code>
        </pre>
      ) : null}
      {readiness.prompt ? (
        <CopyCommand
          className="mt-static-xs"
          command={readiness.prompt}
          label={isContinuationPrompt(readiness.prompt, changeId) ? "Copy continuation prompt" : "Copy prompt"}
          helper={CONTINUATION_PROMPT_HELP}
        />
      ) : null}
      <details className="mt-static-sm border-t border-contrast-low pt-static-xs" data-testid="readiness-details">
        <summary className="cursor-pointer text-xs font-semibold uppercase text-contrast-medium">Details</summary>
        <div className="mt-static-xs flex flex-wrap items-center gap-static-xs">
          <StatusChip
            label={READINESS_STATUS_LABELS[readiness.status]}
            tone={readinessTone(readiness.status)}
            testId="readiness-status"
          />
          <span className="text-xs text-contrast-medium" data-testid="readiness-checks-state">
            Checks: {READINESS_CHECKS_LABELS[readiness.checks_state]}
          </span>
          <span className="text-xs text-contrast-medium" data-readiness-actor={readiness.next_actor}>
            Next: {NEXT_ACTOR_LABELS[readiness.next_actor]}
            {readiness.next_actor === "agent" && isContinuationPrompt(readiness.prompt, changeId)
              ? ", after you run the prompt"
              : ""}
          </span>
        </div>
        <p className="mt-static-xs text-xs text-contrast-medium" data-readiness-reason={readiness.reason_code}>
          Reason: <code>{readiness.reason_code}</code>
        </p>
        {readiness.merge_block ? (
          <p className="mt-static-xs text-sm leading-relaxed" data-testid="merge-block">
            {MERGE_BLOCK_LABELS[readiness.merge_block.reason]}
            {readiness.merge_block.detail ? ` (${readiness.merge_block.detail})` : ""}
          </p>
        ) : null}
        {!readiness.executable ? (
          <p className="mt-static-xs text-xs text-contrast-medium" data-testid="readiness-not-executable">
            Delivery offers no runnable operation for this Work Item right now.
          </p>
        ) : null}
        {readiness.reason_code === "worker-stall-wait" && !readiness.next_eligible_at ? (
          <p className="mt-static-xs text-xs text-contrast-medium" data-testid="worker-stall-no-eligible-time">
            No eligible time yet: processes still use this worker's worktree, or it cannot be observed safely. The
            readiness prompt names any such processes.
          </p>
        ) : null}
        <dl className="mt-static-xs grid grid-cols-[auto_minmax(0,1fr)] gap-x-static-md text-xs">
          <IdentityRow label="Automatic attempts" value={readiness.attempts ?? null} />
          <IdentityRow label="Next eligible at" value={readiness.next_eligible_at ?? null} />
          <IdentityRow label="Stop reason" value={readiness.stop_reason ?? null} />
          <ReadinessBasisRows basis={readiness.basis} />
        </dl>
        {readiness.last_attempt ? <ReadinessAttempt attempt={readiness.last_attempt} /> : null}
        {readiness.retry_history?.length ? (
          <div className="mt-static-sm border-t border-contrast-low pt-static-sm" data-testid="readiness-retry-history">
            <strong className="text-sm">Attempt history</strong>
            <ol className="mt-static-xs text-xs">
              {readiness.retry_history.map((attempt) => (
                <li key={attempt.ordinal}>
                  {attempt.ordinal}. {attempt.kind} {attempt.status}
                  {attempt.failure_code ? (
                    <>
                      {" "}
                      <code>{attempt.failure_code}</code>
                    </>
                  ) : null}
                  {attempt.observed_at ? ` at ${attempt.observed_at}` : null}
                </li>
              ))}
            </ol>
          </div>
        ) : null}
      </details>
    </SectionCard>
  );
}

function UnavailableChangeDetail({ detail }: { detail: WorkItemUnavailableDetailResponse }) {
  return (
    <section className="min-w-0" aria-labelledby="work-detail-heading" data-testid="work-item-detail">
      <div className="grid gap-static-lg">
        <div>
          <span className="text-xs text-contrast-medium">
            <strong className="text-primary">{detail.title ?? `Change ${detail.change_id}`}</strong>
            {" / "}
            <code>{detail.change_id}</code>
          </span>
          <PHeading id="work-detail-heading" size="medium" tag="h2" className="mt-static-xs">
            Runtime unavailable
          </PHeading>
          <p className="mt-static-md max-w-[72ch] text-base leading-relaxed">
            Delivery could not compose the canonical runtime for this Change, so no Work Item detail is available. This
            view is read-only inspection evidence; no Change operation is offered here.
          </p>
        </div>
        <SectionCard
          tone="warning"
          dataTestId="unavailable-change-diagnostics"
          ariaLabel="Runtime diagnostics"
          className="p-static-sm"
        >
          <p className="text-sm font-semibold">Diagnostics</p>
          <ul className="mt-static-xs grid gap-1 text-sm">
            {detail.diagnostics.map((diagnostic) => (
              <li key={diagnostic}>
                <code>{diagnostic}</code>
              </li>
            ))}
          </ul>
          {detail.coordination_status ? (
            <p className="mt-static-xs text-sm">Coordination record: {detail.coordination_status}</p>
          ) : null}
        </SectionCard>
        <ReadinessSection readiness={detail.readiness} changeId={detail.change_id} />
      </div>
    </section>
  );
}

function pullRequestUrl(repository: string, number: number): string {
  const repositoryUrl = repository.startsWith("http")
    ? repository.replace(/\/$/, "")
    : `https://github.com/${repository}`;
  return `${repositoryUrl}/pull/${number}`;
}

function ExternalHeadAdoptionSection(props: WorkItemDetailProps) {
  const action = props.detail.item.card.action;
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [actionFailed, setActionFailed] = useState(false);
  if (action.kind !== "adopt-external-head" || !action.attention_id || !action.expected_head || !action.adopted_head)
    return null;
  const run = async () => {
    const error = await props.onAdoptExternalHeadAfterAcceptanceAttention(
      action.attention_id as string,
      action.expected_head as string,
      action.adopted_head as string,
    );
    setActionFailed(error !== null);
    if (!error) setConfirmOpen(false);
  };
  return (
    <section
      className="mt-static-md border-l-4 border-warning bg-surface p-static-md"
      aria-labelledby="external-head-adoption-heading"
    >
      <PHeading id="external-head-adoption-heading" tag="h4" size="sm">
        Pull request head changed
      </PHeading>
      <p className="mt-static-xs text-sm">
        Adopt the exact open pull-request head before re-running finalization and review.
      </p>
      <dl
        className={[
          "mt-static-md grid grid-cols-[auto_minmax(0,1fr)] gap-x-static-md",
          "gap-y-static-xs break-all text-xs",
        ].join(" ")}
      >
        <IdentityRow label="Finalized head" value={action.expected_head} />
        <IdentityRow label="Pull request head" value={action.adopted_head} />
      </dl>
      <PButton
        className="mt-static-md"
        type="button"
        compact
        variant="secondary"
        data-testid="acceptance-head-adopt"
        disabled={props.pendingAction !== null}
        onClick={() => {
          setActionFailed(false);
          setConfirmOpen(true);
        }}
      >
        {props.pendingAction === "acceptance-head-adopt" ? "Adopting..." : "Adopt changed PR head"}
      </PButton>
      {confirmOpen ? (
        <PModal
          open
          role="alertdialog"
          aria-modal="true"
          dismissButton={false}
          disableBackdropClick
          onDismiss={() => setConfirmOpen(false)}
          aria={{
            role: "alertdialog",
            "aria-label": "Confirm changed pull-request head adoption",
          }}
        >
          <ConfirmationContent onClose={() => setConfirmOpen(false)}>
            <PHeading tag="h2" size="lg">
              Confirm changed PR head
            </PHeading>
            <p className="text-sm">
              The exact open pull-request head will become the new Change head. Finalization and pull-request readiness
              will be cleared; run the continuation prompt again afterward.
            </p>
            <dl className="grid gap-static-xs break-all text-sm">
              <dt className="font-semibold">Finalized head</dt>
              <dd>{action.expected_head}</dd>
              <dt className="font-semibold">Pull request head</dt>
              <dd>{action.adopted_head}</dd>
            </dl>
            {actionFailed && props.actionError ? <ActionFeedback error={props.actionError} result={null} /> : null}
            <div className="flex flex-wrap justify-end gap-static-xs">
              <PButton type="button" variant="secondary" onClick={() => setConfirmOpen(false)}>
                Cancel
              </PButton>
              <PButton type="button" disabled={props.pendingAction !== null} onClick={() => void run()}>
                {props.pendingAction === "acceptance-head-adopt" ? "Adopting..." : "Confirm adoption"}
              </PButton>
            </div>
          </ConfirmationContent>
        </PModal>
      ) : null}
    </section>
  );
}

function WorktreeRecoverySection(props: WorkItemDetailProps) {
  const recovery = props.detail.item.publication?.worktree_recovery;
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [actionFailed, setActionFailed] = useState(false);
  if (!recovery) return null;
  if (!recovery.eligible || !recovery.recovery_reviewed_head) {
    return recovery.blocked_reason ? (
      <p className="mt-static-md border-l-4 border-warning bg-surface p-static-sm text-sm" role="status">
        Worktree recovery unavailable: {recovery.blocked_reason.replace(/-/g, " ")}.
      </p>
    ) : null;
  }
  const pendingAction = "change-worktree-recover";
  const run = async () => {
    const error = await props.onRecoverChangeWorktree(recovery.recovery_reviewed_head as string);
    setActionFailed(error !== null);
    if (!error) setConfirmOpen(false);
  };
  return (
    <section
      className="mt-static-md border-l-4 border-warning bg-surface p-static-md"
      aria-labelledby="worktree-recovery-heading"
    >
      <PHeading id="worktree-recovery-heading" tag="h4" size="sm">
        Missing worktree
      </PHeading>
      <p className="mt-static-xs text-sm">
        Delivery can recreate the missing worktree from the exact reviewed Change head.
      </p>
      <code className="mt-static-sm block break-all text-xs text-contrast-medium">
        Reviewed head: {recovery.recovery_reviewed_head}
      </code>
      <PButton
        className="mt-static-md"
        type="button"
        compact
        variant="secondary"
        disabled={props.pendingAction !== null}
        onClick={() => {
          setActionFailed(false);
          setConfirmOpen(true);
        }}
      >
        {props.pendingAction === pendingAction ? "Recovering..." : "Recover missing worktree"}
      </PButton>
      {confirmOpen ? (
        <PModal
          open
          role="alertdialog"
          aria-modal="true"
          dismissButton={false}
          disableBackdropClick
          onDismiss={() => setConfirmOpen(false)}
          aria={{
            role: "alertdialog",
            "aria-label": "Confirm worktree recovery",
          }}
        >
          <ConfirmationContent onClose={() => setConfirmOpen(false)}>
            <PHeading tag="h2" size="lg">
              Recover missing worktree
            </PHeading>
            <p className="text-sm">
              The managed worktree will be recreated at its canonical path. The Change branch and reviewed head will
              remain unchanged.
            </p>
            {actionFailed && props.actionError ? <ActionFeedback error={props.actionError} result={null} /> : null}
            <div className="flex flex-wrap justify-end gap-static-xs">
              <PButton type="button" variant="secondary" onClick={() => setConfirmOpen(false)}>
                Cancel
              </PButton>
              <PButton type="button" disabled={props.pendingAction !== null} onClick={() => void run()}>
                {props.pendingAction === pendingAction ? "Recovering..." : "Confirm worktree recovery"}
              </PButton>
            </div>
          </ConfirmationContent>
        </PModal>
      ) : null}
    </section>
  );
}

function WorktreeCleanupSection(props: WorkItemDetailProps) {
  const publication = props.detail.item.publication;
  const cleanup = publication?.worktree_cleanup;
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [actionFailed, setActionFailed] = useState(false);
  if (!publication || !cleanup) return null;
  const terminal = publication.phase === "abandoned" || publication.phase === "acceptance-observed";
  if (!terminal) return null;
  const abandonedConflict = publication.phase === "abandoned" && Boolean(publication.target_sync_conflict);
  if (abandonedConflict) {
    return <AbandonedTargetSyncCleanupSection {...props} />;
  }
  if (!cleanup.eligible) {
    return cleanup.blocked_reason ? (
      <p className="mt-static-md border-l-4 border-warning bg-surface p-static-sm text-sm" role="status">
        Worktree cleanup unavailable: {cleanup.blocked_reason.replace(/-/g, " ")}.
      </p>
    ) : null;
  }
  const completed = publication.phase === "acceptance-observed";
  const action = completed
    ? cleanup.completion_id
      ? () => props.onCleanupCompletedChange(cleanup.completion_id as string)
      : null
    : props.onCleanupAbandonedChange;
  if (!action) return null;
  const actionName = completed ? "Clean completed worktree" : "Clean abandoned worktree";
  const pendingAction = completed ? "change-cleanup-completed" : "change-cleanup-abandoned";
  const run = async () => {
    const error = await action();
    setActionFailed(error !== null);
    if (!error) setConfirmOpen(false);
  };
  return (
    <section
      className="mt-static-md border-l-4 border-warning bg-surface p-static-md"
      aria-labelledby="worktree-cleanup-heading"
    >
      <PHeading id="worktree-cleanup-heading" tag="h4" size="sm">
        Retained worktree
      </PHeading>
      <p className="mt-static-xs text-sm">
        The terminal Change worktree is clean and ready for removal. Its branch is preserved.
      </p>
      <PButton
        className="mt-static-md"
        type="button"
        compact
        variant="secondary"
        disabled={props.pendingAction !== null}
        onClick={() => {
          setActionFailed(false);
          setConfirmOpen(true);
        }}
      >
        {props.pendingAction === pendingAction ? "Cleaning..." : actionName}
      </PButton>
      {confirmOpen ? (
        <PModal
          open
          role="alertdialog"
          aria-modal="true"
          dismissButton={false}
          disableBackdropClick
          onDismiss={() => setConfirmOpen(false)}
          aria={{
            role: "alertdialog",
            "aria-label": `Confirm ${actionName.toLowerCase()}`,
          }}
        >
          <ConfirmationContent onClose={() => setConfirmOpen(false)}>
            <PHeading tag="h2" size="lg">
              {actionName}
            </PHeading>
            <p className="text-sm">
              The worktree directory will be removed. The Change branch and cleanup receipt will remain.
            </p>
            {actionFailed && props.actionError ? <ActionFeedback error={props.actionError} result={null} /> : null}
            <div className="flex flex-wrap justify-end gap-static-xs">
              <PButton type="button" variant="secondary" onClick={() => setConfirmOpen(false)}>
                Cancel
              </PButton>
              <PButton type="button" disabled={props.pendingAction !== null} onClick={() => void run()}>
                {props.pendingAction === pendingAction ? "Cleaning..." : `Confirm ${actionName.toLowerCase()}`}
              </PButton>
            </div>
          </ConfirmationContent>
        </PModal>
      ) : null}
    </section>
  );
}

function AbandonedTargetSyncCleanupSection(props: WorkItemDetailProps) {
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [actionFailed, setActionFailed] = useState(false);
  const conflict = props.detail.item.publication?.target_sync_conflict;
  if (!conflict) return null;
  const run = async () => {
    const error = await props.onDiscardAbandonedTargetSync(conflict.target_head, conflict.operation_id);
    setActionFailed(error !== null);
    if (!error) setConfirmOpen(false);
  };
  return (
    <section
      className="mt-static-md border-l-4 border-danger bg-surface p-static-md"
      aria-labelledby="abandoned-target-sync-cleanup-heading"
    >
      <PHeading id="abandoned-target-sync-cleanup-heading" tag="h4" size="sm">
        Abandoned target sync
      </PHeading>
      <p className="mt-static-xs text-sm">
        The abandoned Change still contains a preserved target merge. Discard that merge before removing the worktree.
      </p>
      <PButton
        className="mt-static-md"
        type="button"
        compact
        variant="secondary"
        disabled={props.pendingAction !== null}
        onClick={() => {
          setActionFailed(false);
          setConfirmOpen(true);
        }}
      >
        {props.pendingAction === "change-cleanup-abandoned-target-sync"
          ? "Discarding and cleaning..."
          : "Discard merge and clean worktree"}
      </PButton>
      {confirmOpen ? (
        <PModal
          open
          role="alertdialog"
          aria-modal="true"
          dismissButton={false}
          disableBackdropClick
          onDismiss={() => setConfirmOpen(false)}
          aria={{
            role: "alertdialog",
            "aria-label": "Confirm target merge discard and worktree cleanup",
          }}
        >
          <ConfirmationContent onClose={() => setConfirmOpen(false)}>
            <PHeading tag="h2" size="lg">
              Discard target merge and clean worktree
            </PHeading>
            <p className="text-sm">
              The preserved target merge will be aborted and its worktree directory removed. The abandoned Change branch
              and receipts will remain.
            </p>
            {actionFailed && props.actionError ? <ActionFeedback error={props.actionError} result={null} /> : null}
            <div className="flex flex-wrap justify-end gap-static-xs">
              <PButton type="button" variant="secondary" onClick={() => setConfirmOpen(false)}>
                Cancel
              </PButton>
              <PButton type="button" disabled={props.pendingAction !== null} onClick={() => void run()}>
                {props.pendingAction === "change-cleanup-abandoned-target-sync"
                  ? "Discarding and cleaning..."
                  : "Confirm discard and cleanup"}
              </PButton>
            </div>
          </ConfirmationContent>
        </PModal>
      ) : null}
    </section>
  );
}

function TargetSyncConflictSection(props: WorkItemDetailProps) {
  const publication = props.detail.item.publication;
  const conflict = publication?.target_sync_conflict;
  const attention = publication?.attention;
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [actionFailed, setActionFailed] = useState(false);
  if (!publication || !conflict) return null;
  const canExit = attention?.kind === "publication-attention";
  const command = props.detail.item.card.action.command;
  const promptOffersCommand = Boolean(command && props.detail.item.readiness?.prompt?.startsWith(command));
  const abort = async () => {
    if (!attention) return;
    const error = await props.onAbortTargetSync(attention.disposition_id, conflict.target_head, conflict.operation_id);
    setActionFailed(error !== null);
    if (!error) setConfirmOpen(false);
  };
  return (
    <section className="border-l-4 border-danger bg-surface p-static-md" aria-labelledby="target-sync-conflict-heading">
      <PHeading id="target-sync-conflict-heading" tag="h4" size="sm">
        Target sync conflict
      </PHeading>
      <p className="mt-static-xs text-sm">
        Merging the latest target stopped on conflicting files. Delivery keeps the merge in the Change worktree until it
        is resolved or aborted.
      </p>
      {conflict.conflict_paths.length > 0 ? (
        <ul className="mt-static-md list-disc break-all pl-static-md text-sm" data-testid="target-sync-conflict-paths">
          {conflict.conflict_paths.map((path) => (
            <li key={path}>{path}</li>
          ))}
        </ul>
      ) : (
        <p className="mt-static-md text-sm text-contrast-medium">Git did not report individual conflict paths.</p>
      )}
      {command && !promptOffersCommand ? (
        <div className="mt-static-md">
          <p className="text-sm">Resolve them with the target conflict workflow.</p>
          <CopyCommand className="mt-static-xs" command={command} />
        </div>
      ) : null}
      {canExit && attention ? (
        <div className="mt-static-md grid gap-static-sm">
          <div>
            <PButton
              type="button"
              compact
              variant="secondary"
              data-testid="target-sync-conflict-abort"
              aria-describedby="target-sync-conflict-abort-help"
              disabled={props.pendingAction !== null}
              onClick={() => {
                setActionFailed(false);
                setConfirmOpen(true);
              }}
            >
              {props.pendingAction === "target-sync-abort" ? "Aborting..." : "Abort target sync"}
            </PButton>
            <p id="target-sync-conflict-abort-help" className="mt-static-xs text-xs text-contrast-medium">
              Rolls the Change back to its reviewed head; the latest target stays unmerged.
            </p>
          </div>
          <div>
            <PButton
              type="button"
              compact
              variant="secondary"
              data-testid="target-sync-conflict-resolve"
              aria-describedby="target-sync-conflict-resolve-help"
              disabled={props.pendingAction !== null}
              onClick={() =>
                void props.onResolveTargetSync(attention.disposition_id, conflict.target_head, conflict.operation_id)
              }
            >
              {props.pendingAction === "target-sync-resolve" ? "Submitting..." : "Submit resolved merge"}
            </PButton>
            <p id="target-sync-conflict-resolve-help" className="mt-static-xs text-xs text-contrast-medium">
              Only after you resolved and staged every conflicting file in the Change worktree yourself; the target
              conflict workflow submits it for you.
            </p>
          </div>
        </div>
      ) : (
        <p className="mt-static-md text-sm text-contrast-medium">Waiting for the matching Change attention record.</p>
      )}
      <details className="mt-static-md border-t border-contrast-low pt-static-xs">
        <summary className="cursor-pointer text-xs font-semibold uppercase text-contrast-medium">
          Technical details
        </summary>
        <dl
          className={[
            "mt-static-xs grid grid-cols-[auto_minmax(0,1fr)] gap-x-static-md",
            "gap-y-static-xs break-all text-xs",
          ].join(" ")}
        >
          <IdentityRow label="Operation" value={conflict.operation_id} />
          <IdentityRow label="Target head" value={conflict.target_head} />
          <IdentityRow label="Reviewed head" value={conflict.change_head_before} />
        </dl>
      </details>
      {confirmOpen ? (
        <PModal
          open
          role="alertdialog"
          aria-modal="true"
          dismissButton={false}
          disableBackdropClick
          onDismiss={() => setConfirmOpen(false)}
          aria={{
            role: "alertdialog",
            "aria-label": "Confirm target sync abort",
          }}
        >
          <ConfirmationContent onClose={() => setConfirmOpen(false)}>
            <PHeading tag="h2" size="lg">
              Abort target sync
            </PHeading>
            <p className="text-sm">
              The preserved target merge will be aborted and the Change will return to its reviewed head. Any
              target-sync merge state will be discarded.
            </p>
            {actionFailed && props.actionError ? <ActionFeedback error={props.actionError} result={null} /> : null}
            <div className="flex flex-wrap justify-end gap-static-xs">
              <PButton type="button" variant="secondary" onClick={() => setConfirmOpen(false)}>
                Cancel
              </PButton>
              <PButton type="button" disabled={props.pendingAction !== null} onClick={() => void abort()}>
                {props.pendingAction === "target-sync-abort" ? "Aborting..." : "Confirm abort"}
              </PButton>
            </div>
          </ConfirmationContent>
        </PModal>
      ) : null}
    </section>
  );
}

const TARGET_SYNC_COPY: Record<"required" | "optional", string> = {
  required:
    "The pull request cannot merge until the latest integration target is in the Change. If that changes the Change " +
    "head, the Change must be finalized again by running its prompt in Copilot Chat before it can merge.",
  optional:
    "The target has moved since this Change was verified. You can merge now, or update it first; updating returns " +
    "the pull request to draft, requires finalizing again and may raise conflicts.",
};

function TargetSyncSection(props: WorkItemDetailProps) {
  const publication = props.detail.item.publication;
  const availability = props.detail.item.readiness?.progress?.target_sync;
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [actionFailed, setActionFailed] = useState(false);
  if (!publication || !availability || availability === "unnecessary") return null;
  if (availability === "unavailable")
    return publication.target_sync_conflict ? null : (
      <p className="border-t border-contrast-low pt-static-sm text-sm text-contrast-medium" data-testid="target-sync">
        Updating the Change from its target is not offered in its current state.
      </p>
    );
  const run = async () => {
    const error = await props.onSyncTarget();
    setActionFailed(error !== null);
    if (!error) setConfirmOpen(false);
  };
  return (
    <section
      className="border-t border-contrast-low pt-static-sm"
      aria-labelledby="target-sync-heading"
      data-testid="target-sync"
      data-target-sync={availability}
    >
      <h4 id="target-sync-heading" className="text-xs font-semibold uppercase text-contrast-medium">
        {availability === "required" ? "Update required" : "Change maintenance"}
      </h4>
      <p className="mt-static-xs text-sm text-contrast-medium">{TARGET_SYNC_COPY[availability]}</p>
      <PButton
        className="mt-static-sm"
        type="button"
        compact
        variant={availability === "required" ? "primary" : "secondary"}
        disabled={props.pendingAction !== null || props.isObservingPublicationChecks}
        onClick={() => {
          setActionFailed(false);
          setConfirmOpen(true);
        }}
      >
        {props.pendingAction === "target-sync" ? "Updating Change..." : "Merge latest target into Change"}
      </PButton>
      {confirmOpen ? (
        <PModal
          open
          role="alertdialog"
          aria-modal="true"
          dismissButton={false}
          disableBackdropClick
          onDismiss={() => setConfirmOpen(false)}
          aria={{
            role: "alertdialog",
            "aria-label": "Confirm target synchronization",
          }}
        >
          <ConfirmationContent onClose={() => setConfirmOpen(false)}>
            <PHeading tag="h2" size="lg">
              Merge latest target into Change
            </PHeading>
            <p className="text-sm">
              Delivery will merge the current integration target into the managed Change. This can create a merge commit
              or conflicts, invalidate finalization, and require a new review.
            </p>
            {actionFailed && props.actionError ? <ActionFeedback error={props.actionError} result={null} /> : null}
            <div className="flex flex-wrap justify-end gap-static-xs">
              <PButton type="button" variant="secondary" onClick={() => setConfirmOpen(false)}>
                Cancel
              </PButton>
              <PButton type="button" disabled={props.pendingAction !== null} onClick={() => void run()}>
                {props.pendingAction === "target-sync" ? "Updating Change..." : "Confirm target update"}
              </PButton>
            </div>
          </ConfirmationContent>
        </PModal>
      ) : null}
    </section>
  );
}

const PUBLICATION_CHECK_STATE_LABELS: Record<PublicationCheckBlockingState, string> = {
  blocking: "Blocking",
  "required-pending": "Required pending",
  "not-blocking": "Not blocking",
};

function PublicationCheckItem({ check }: { check: PublicationChecksObservationResponse["checks"][number] }) {
  return (
    <li className="border-l-2 border-contrast-low pl-static-sm" data-testid="publication-check">
      <div className="flex flex-wrap items-start justify-between gap-static-xs">
        <strong className="text-sm">{check.name}</strong>
        <PTag compact>{PUBLICATION_CHECK_STATE_LABELS[check.blocking_state]}</PTag>
      </div>
      <p className="mt-static-xs text-xs text-contrast-medium">
        {check.required ? "Required" : "Optional"} · {check.status}
        {check.conclusion ? ` · ${check.conclusion}` : ""}
      </p>
    </li>
  );
}

function PublicationChecksSection(props: WorkItemDetailProps) {
  const publication = props.detail.item.publication;
  const observable = Boolean(
    publication &&
      (publication.phase === "pull-request-draft" || publication.phase === "awaiting-merge") &&
      publication.published_head !== null &&
      publication.publication_generations.length > 0,
  );
  const draftPublication = observable && publication?.phase === "pull-request-draft";
  const observation = props.publicationChecks;
  const retainsEvidence = observation !== null || props.publicationChecksStale;
  if (!observable && !retainsEvidence) return null;
  const errorCode =
    props.publicationChecksError instanceof WorkItemApiError
      ? props.publicationChecksError.code
      : "ERR_WORK_ITEM_PUBLICATION_CHECKS_OBSERVE";
  const status = props.isObservingPublicationChecks
    ? "Observing publication checks..."
    : props.publicationChecksStale
      ? "Previous check results were cleared because the published head changed. Observe again for the current head."
      : observation
        ? `Checks observed for ${observation.exact_commit}.`
        : draftPublication
          ? null
          : "No checks observed for this head yet.";
  return (
    <section
      className="border-l border-contrast-low bg-surface p-static-md"
      aria-labelledby="publication-checks-heading"
    >
      <div className="flex flex-wrap items-start justify-between gap-static-sm">
        <PHeading id="publication-checks-heading" tag="h4" size="sm">
          PR CI checks
        </PHeading>
        {observable ? (
          <PButton
            type="button"
            compact
            variant="secondary"
            data-testid="publication-checks-observe"
            aria-describedby={draftPublication ? "publication-checks-draft-guidance" : undefined}
            disabled={draftPublication || props.isObservingPublicationChecks || props.pendingAction !== null}
            onClick={draftPublication ? undefined : () => void props.onObservePublicationChecks()}
          >
            {props.isObservingPublicationChecks ? "Checking CI..." : "Observe current checks"}
          </PButton>
        ) : null}
      </div>
      {draftPublication ? (
        <p
          id="publication-checks-draft-guidance"
          className="mt-static-sm text-sm"
          role="status"
          data-testid="publication-checks-draft-guidance"
        >
          You can observe check results here once this pull request is ready for review.
        </p>
      ) : null}
      {status ? (
        <p className="mt-static-sm text-sm" aria-live="polite" role="status" data-testid="publication-checks-status">
          {status}
        </p>
      ) : null}
      {props.publicationChecksError ? (
        <p
          className={[
            "mt-static-sm flex items-center gap-static-xs border-l-4",
            "border-danger bg-surface p-static-sm text-sm",
          ].join(" ")}
          role="alert"
        >
          <PIcon name="error" size="sm" aria-hidden="true" />
          <strong>{errorCode}</strong>: {props.publicationChecksError.message}
        </p>
      ) : null}
      {observation ? (
        <>
          <dl className="mt-static-md grid grid-cols-[auto_minmax(0,1fr)] gap-x-static-md gap-y-static-xs text-sm">
            <dt className="text-contrast-medium">Observed commit</dt>
            <dd className="min-w-0 break-all font-mono text-xs">{observation.exact_commit}</dd>
            <dt className="text-contrast-medium">Evidence recorded</dt>
            <dd className="min-w-0 break-all font-mono text-xs">
              <time dateTime={observation.observed_at}>{observation.observed_at}</time>
            </dd>
            <dt className="text-contrast-medium">Required blocking checks</dt>
            <dd>{observation.required_failure_count}</dd>
            {observation.rollup_state ? (
              <>
                <dt className="text-contrast-medium">Provider rollup</dt>
                <dd>{observation.rollup_state}</dd>
              </>
            ) : null}
          </dl>
          {observation.truncated_count > 0 ? (
            <p className="mt-static-sm border-l-4 border-warning bg-surface p-static-sm text-sm" role="status">
              {observation.truncated_count} additional check
              {observation.truncated_count === 1 ? "" : "s"} not shown.
            </p>
          ) : null}
          <ul className="mt-static-md grid gap-static-sm" aria-label="Publication check results">
            {observation.checks.map((check) => (
              <PublicationCheckItem key={check.check_id} check={check} />
            ))}
          </ul>
        </>
      ) : null}
    </section>
  );
}

function PublicationSection(props: WorkItemDetailProps) {
  const publication = props.detail.item.publication;
  const [readyConflictConfirmOpen, setReadyConflictConfirmOpen] = useState(false);
  if (!publication) return null;
  const finalizationPhase =
    publication.phase === "ready-for-finalization" || publication.phase === "finalization-invalidated";
  const finalizationBlocked = finalizationPhase && publication.ready_for_finalization === false;
  const action = props.detail.item.card.action;
  const targetSyncAttention = Boolean(
    publication.target_sync_conflict && publication.attention?.kind === "publication-attention",
  );
  const publicationGenerations = publication.publication_generations ?? [];
  const canSupersede =
    publication.attention?.kind === "publication-attention" &&
    publicationGenerations.length > 0 &&
    !targetSyncAttention;
  const control =
    action.kind === "reconcile-checkpoint"
      ? props.onReconcilePublication
      : action.kind === "mark-ready"
        ? props.onMarkPublicationReady
        : action.kind === "observe-acceptance"
          ? props.onObserveAcceptance
          : action.kind === "resolve-attention" && action.attention_id && !targetSyncAttention
            ? () => props.onResolveAttention(action.attention_id as string)
            : action.kind === "resume-change"
              ? props.onResumeChange
              : null;
  const pending =
    action.kind === "reconcile-checkpoint"
      ? props.pendingAction === "publication-reconcile"
      : action.kind === "mark-ready"
        ? props.pendingAction === "publication-ready"
        : action.kind === "observe-acceptance"
          ? props.pendingAction === "acceptance-observe"
          : action.kind === "resolve-attention"
            ? props.pendingAction === "attention-resolve"
            : props.pendingAction === "change-resume";
  const readiness = props.detail.item.card.readiness ?? props.detail.item.readiness;
  const publicationStatus = workItemStatus({
    ...props.detail.item.card,
    publication_phase: publication.phase,
    readiness,
  });
  const statusTone = publicationStatus.tone;
  const situationTone =
    statusTone === "attention" || statusTone === "blocked"
      ? "warning"
      : statusTone === "active"
        ? "info"
        : statusTone === "complete"
          ? "success"
          : "neutral";
  const invalidationReason =
    publication.invalidated_expected_head && publication.invalidated_observed_head
      ? [
          "The Change head moved from",
          publication.invalidated_expected_head.slice(0, 12),
          "to",
          publication.invalidated_observed_head.slice(0, 12),
          "so the previous finalization no longer matches.",
        ].join(" ")
      : null;
  const runControl = () => {
    if (!control) return;
    if (action.kind === "mark-ready" && publication.mergeable === false) {
      setReadyConflictConfirmOpen(true);
      return;
    }
    void control();
  };
  const confirmReadyDespiteConflict = () => {
    setReadyConflictConfirmOpen(false);
    if (control) void control();
  };
  return (
    <section className="min-w-0" aria-labelledby="work-publication-heading">
      <SectionCard tone={situationTone} className="border-l-4 p-static-md">
        <div className="flex min-w-0 flex-wrap items-center justify-between gap-static-sm">
          <PHeading id="work-publication-heading" tag="h3" size="md">
            {PUBLICATION_PHASE_LABELS[publication.phase]}
          </PHeading>
          {readiness && !targetSyncAttention ? (
            <StatusChip
              label={publicationStatus.label}
              tone={publicationStatus.tone}
              testId="publication-readiness-status"
            />
          ) : null}
        </div>
        {invalidationReason || !targetSyncAttention ? (
          <p className="mt-static-xs text-sm leading-relaxed">
            {invalidationReason ?? props.detail.item.card.next_step}
          </p>
        ) : null}
        {invalidationReason ? (
          <div className="mt-static-sm grid grid-cols-[auto_minmax(0,1fr)] gap-x-static-sm gap-y-static-xs text-xs">
            <span className="text-contrast-medium">Expected</span>
            <code>{publication.invalidated_expected_head}</code>
            <span className="text-contrast-medium">Observed</span>
            <code>{publication.invalidated_observed_head}</code>
          </div>
        ) : null}
        {invalidationReason && !targetSyncAttention ? (
          <p className="mt-static-sm text-sm text-contrast-medium">Next: {props.detail.item.card.next_step}</p>
        ) : null}
        {action.command && !finalizationBlocked && !targetSyncAttention ? (
          <CopyCommand command={action.command} className="mt-static-md" />
        ) : null}
        {control &&
        action.label &&
        (!action.command || action.kind === "mark-ready" || action.kind === "observe-acceptance") ? (
          <PButton
            className="mt-static-md"
            type="button"
            compact
            disabled={props.pendingAction !== null || props.isObservingPublicationChecks}
            onClick={runControl}
          >
            {pending ? "Working..." : action.label}
          </PButton>
        ) : null}
      </SectionCard>
      {readyConflictConfirmOpen ? (
        <PModal
          open
          role="alertdialog"
          aria-modal="true"
          dismissButton={false}
          disableBackdropClick
          onDismiss={() => setReadyConflictConfirmOpen(false)}
          aria={{
            role: "alertdialog",
            "aria-label": "Confirm making conflicted pull request ready",
          }}
        >
          <ConfirmationContent onClose={() => setReadyConflictConfirmOpen(false)}>
            <PHeading tag="h2" size="lg">
              Make conflicted PR ready?
            </PHeading>
            <p className="text-sm">
              GitHub reports conflicts with the integration target. Making the pull request ready will not resolve them,
              and reviewers will still be unable to merge it.
            </p>
            {action.command ? (
              <p className="text-sm">
                Recommended next step: <CopyCommand command={action.command} />
              </p>
            ) : null}
            <div className="flex flex-wrap justify-end gap-static-xs">
              <PButton type="button" variant="secondary" onClick={() => setReadyConflictConfirmOpen(false)}>
                Keep PR in draft
              </PButton>
              <PButton type="button" disabled={props.pendingAction !== null} onClick={confirmReadyDespiteConflict}>
                Make PR ready anyway
              </PButton>
            </div>
          </ConfirmationContent>
        </PModal>
      ) : null}
      {finalizationBlocked && !targetSyncAttention ? (
        <section
          className="mt-static-md border-l-4 border-warning bg-surface p-static-sm"
          role="status"
          data-testid="finalization-readiness"
        >
          <PHeading tag="h4" size="sm">
            Finalization unavailable
          </PHeading>
          <p className="mt-static-xs text-sm">Delivery cannot finalize the current Change yet.</p>
          {(publication.readiness_diagnostics ?? []).length > 0 ? (
            <ul className="mt-static-xs list-disc pl-static-md text-sm">
              {(publication.readiness_diagnostics ?? []).map((diagnostic) => (
                <li key={diagnostic}>{diagnostic}</li>
              ))}
            </ul>
          ) : null}
          <p className="mt-static-xs text-sm text-contrast-medium">
            Follow the next step under Delivery readiness above.
          </p>
        </section>
      ) : null}
      <TargetSyncConflictSection {...props} />
      {publication.attention && !targetSyncAttention ? (
        <div className="mt-static-md border-l-4 border-warning bg-surface p-static-sm" role="alert">
          <PHeading tag="h4" size="sm">
            Change attention
          </PHeading>
          <p className="mt-static-xs text-sm">
            {publication.attention.kind === "publication-attention"
              ? "Publication evidence needs reconciliation."
              : "Acceptance evidence needs reconciliation."}
          </p>
          <details className="mt-static-xs">
            <summary className="cursor-pointer text-xs font-semibold uppercase text-contrast-medium">
              Technical details
            </summary>
            <ul className="mt-static-xs list-disc pl-static-md text-sm">
              {publication.attention.diagnostics.map((diagnostic) => (
                <li key={diagnostic}>{diagnostic}</li>
              ))}
            </ul>
            <p className="mt-static-xs break-all font-mono text-xs">
              Disposition: {publication.attention.disposition_id}
            </p>
          </details>
        </div>
      ) : null}
      <ExternalHeadAdoptionSection {...props} />
      <details className="mt-static-md border-t border-contrast-low pt-static-sm">
        <summary
          className={[
            "cursor-pointer text-xs font-semibold uppercase text-contrast-medium",
            "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus",
          ].join(" ")}
        >
          Publication evidence
        </summary>
        <dl className="mt-static-md grid grid-cols-[auto_minmax(0,1fr)] gap-x-static-md gap-y-static-xs text-sm">
          <IdentityRow label="Repository" value={publication.repository} />
          {publication.repository && publication.pull_request_number ? (
            <>
              <dt className="text-contrast-medium">Pull request</dt>
              <dd className="min-w-0 break-all text-xs">
                <a
                  className={[
                    "font-medium text-primary underline decoration-contrast-low",
                    "underline-offset-2 hover:decoration-primary",
                  ].join(" ")}
                  href={pullRequestUrl(publication.repository, publication.pull_request_number)}
                  target="_blank"
                  rel="noreferrer"
                >
                  {publication.repository} #{publication.pull_request_number}
                </a>
              </dd>
            </>
          ) : (
            <IdentityRow label="Pull request" value={publication.pull_request_number} />
          )}
          <IdentityRow label="Finalized head" value={publication.finalized_head} />
          <IdentityRow label="Published head" value={publication.published_head} />
          <IdentityRow label="Pull request head" value={publication.pull_request_head} />
          <IdentityRow label="Accepted merge commit" value={publication.accepted_merge_commit} />
          <IdentityRow label="Expected head" value={publication.invalidated_expected_head} />
          <IdentityRow label="Observed head" value={publication.invalidated_observed_head} />
          <IdentityRow label="Merged at" value={publication.merged_at} />
          <IdentityRow label="Target head" value={publication.target_sync?.target_head ?? null} />
          <IdentityRow label="Target-sync merge result" value={publication.target_sync?.merged_head ?? null} />
        </dl>
        {publication.target_sync ? (
          <p className="mt-static-sm text-xs text-contrast-medium">
            Last target sync: {publication.target_sync.target_branch}
            {publication.target_sync.merge_commit ? " (merge commit)" : " (fast-forward)"}
          </p>
        ) : null}
        {publicationGenerations.length > 0 ? (
          <div className="mt-static-md" data-testid="publication-history">
            <PHeading tag="h4" size="sm">
              Publication history
            </PHeading>
            <ol className="mt-static-xs grid gap-static-xs text-xs">
              {publicationGenerations.map((generation, index) => (
                <li key={`${generation.node_id}-${generation.head_sha}`} className="break-all">
                  Generation {index + 1}: {generation.repository} #{generation.number} / {generation.head_sha}
                </li>
              ))}
            </ol>
          </div>
        ) : null}
        {publication.phase === "checkpoint-pending" &&
        ((publication.pending_checkpoint_attempt_count ?? 0) > 0 ||
          publication.pending_checkpoint_error_code ||
          publication.pending_checkpoint_head ||
          publication.pending_checkpoint_triggers.length > 0) ? (
          <div
            className={[
              "mt-static-sm border-l-2 p-static-sm text-sm",
              publication.pending_checkpoint_error_code || (publication.pending_checkpoint_attempt_count ?? 0) > 0
                ? "border-warning bg-surface"
                : "border-info bg-info-low",
            ].join(" ")}
            data-testid="checkpoint-diagnostics"
            role={publication.pending_checkpoint_error_code ? "alert" : "status"}
          >
            <p>
              <strong>Checkpoint recovery</strong>
            </p>
            {(publication.pending_checkpoint_attempt_count ?? 0) > 0 ? (
              <p className="mt-static-xs">
                {publication.pending_checkpoint_attempt_count} attempt
                {publication.pending_checkpoint_attempt_count === 1 ? "" : "s"} recorded
              </p>
            ) : null}
            {publication.pending_checkpoint_head ? (
              <p className="mt-static-xs break-all text-xs text-contrast-medium">
                Pending head: <code>{publication.pending_checkpoint_head}</code>
              </p>
            ) : null}
            {publication.pending_checkpoint_triggers.length > 0 ? (
              <p className="mt-static-xs break-words text-xs text-contrast-medium">
                Triggered by: {Array.from(new Set(publication.pending_checkpoint_triggers)).join(", ")}
              </p>
            ) : null}
            {publication.pending_checkpoint_last_attempted_at ? (
              <p className="mt-static-xs text-xs text-contrast-medium">
                Last attempt:{" "}
                <time dateTime={publication.pending_checkpoint_last_attempted_at}>
                  {publication.pending_checkpoint_last_attempted_at}
                </time>
              </p>
            ) : null}
            {publication.pending_checkpoint_error_code ? (
              <p className="mt-static-xs break-words">
                <strong>{publication.pending_checkpoint_error_code}</strong>
                {publication.pending_checkpoint_error_detail ? `: ${publication.pending_checkpoint_error_detail}` : ""}
              </p>
            ) : null}
          </div>
        ) : null}
      </details>
      <PublicationChecksSection {...props} />
      {canSupersede ? (
        <PButton
          className="mt-static-md"
          type="button"
          compact
          variant="secondary"
          data-testid="publication-supersede"
          disabled={props.pendingAction !== null || props.isObservingPublicationChecks}
          onClick={() => void props.onSupersedePublication()}
        >
          {props.pendingAction === "publication-supersede" ? "Superseding..." : "Supersede publication"}
        </PButton>
      ) : null}
      <TargetSyncSection {...props} />
      <WorktreeRecoverySection {...props} />
      <WorktreeCleanupSection {...props} />
    </section>
  );
}

function ActionFeedback({ error, result }: { error: Error | null; result: string | null }) {
  if (error) {
    const code = error instanceof WorkItemApiError ? error.code : "ERR_DELIVERY_CONTROL";
    const retryAfter = error instanceof WorkItemApiError ? error.retryAfter : null;
    const workerActive = code === "ERR_DELIVERY_WORKER_ACTIVE";
    const waiting = code === "ERR_DELIVERY_ACCEPTANCE_WAITING" || workerActive;
    return (
      <p
        className={[
          "flex items-center gap-static-xs border-l-4",
          waiting ? "border-warning" : "border-danger",
          "bg-surface p-static-sm text-sm",
        ].join(" ")}
        role={waiting ? "status" : "alert"}
      >
        <PIcon name={waiting ? "warning" : "error"} size="sm" aria-hidden="true" />
        <span>
          <strong>{code}</strong>:{" "}
          {workerActive && retryAfter ? (
            <>
              The worktree changed recently, so the worker may still be active. Nothing was changed. Try again at or
              after{" "}
              <time dateTime={retryAfter} data-testid="worker-active-retry-after">
                {retryAfter}
              </time>
              .
            </>
          ) : (
            error.message
          )}
        </span>
      </p>
    );
  }
  return result ? (
    <p className="border-l-4 border-success bg-surface p-static-sm text-sm" role="status">
      {result}
    </p>
  ) : null;
}

export default function WorkItemDetail(
  props: Omit<WorkItemDetailProps, "detail"> & {
    detail: WorkItemDetailResponse;
  },
) {
  if (isUnavailableDetail(props.detail)) return <UnavailableChangeDetail detail={props.detail} />;
  const available = { ...props, detail: props.detail };
  const { card } = props.detail.item;
  return (
    <section className="min-w-0" aria-labelledby="work-detail-heading" data-testid="work-item-detail">
      <div className="grid gap-static-lg">
        <div>
          <DetailHeader detail={props.detail} />
          <p className="mt-static-md max-w-[72ch] text-base leading-relaxed">{props.detail.item.promise}</p>
          <dl className="mt-static-md grid grid-cols-[auto_minmax(0,1fr)] gap-x-static-md py-static-xs text-sm">
            <dt className="text-contrast-medium">Progress</dt>
            <dd>{card.progress.label}</dd>
            {props.detail.item.change_progress ? (
              <>
                <dt className="text-contrast-medium">Change</dt>
                <dd data-testid="change-progress">
                  {progressLabel(props.detail.item.change_progress)}
                  <span className="text-contrast-medium"> · {props.detail.item.change_progress.headline}</span>
                  {progressWaitLine(props.detail.item.change_progress) ? (
                    <span className="block text-xs text-contrast-medium">
                      {progressWaitLine(props.detail.item.change_progress)}
                    </span>
                  ) : null}
                </dd>
              </>
            ) : null}
          </dl>
        </div>
        <ActionFeedback error={props.actionError} result={props.actionResult} />
        <ReadinessSection readiness={props.detail.item.readiness} changeId={card.change_id}>
          <MergeApprovalDialog
            offer={
              props.detail.item.readiness?.reason_code === "merge-approval-required"
                ? (props.detail.item.readiness.merge_offer ?? null)
                : null
            }
            pendingAction={props.pendingAction}
            onApproveMerge={props.onApproveMerge}
          />
        </ReadinessSection>
        <ChangePauseSection {...available} />
        <BlockSection {...available} />
        <RequestsSection {...available} />
        <PublicationSection {...available} />
        <CourseChangesSection detail={props.detail} />
        <SemanticDetail detail={props.detail} />
        <DecisionsSection detail={props.detail} />
        <EvidenceSummary detail={props.detail} />
        <ClaimSection {...available} />
        <ExceptionalStateSection detail={props.detail} />
        <BackwardMoveSection {...available} />
        <ChangeDispositionSection {...available} />
      </div>
    </section>
  );
}
