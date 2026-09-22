"""Deterministic portfolio acquisition and bounded worker context."""

from __future__ import annotations

import hashlib
import html
import json
import logging
import stat
import subprocess
import time
import uuid
from contextlib import ExitStack, contextmanager, suppress
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path, PurePosixPath
from threading import Lock
from typing import TYPE_CHECKING, Literal, Never

from markdown_it import MarkdownIt
from pydantic import BaseModel, ConfigDict, Field, model_validator

from owlbear_delivery.acceptance import (
    CompletionEvidence,
    CompletionPullRequestIdentity,
    CompletionReceipt,
)
from owlbear_delivery.change_publication import (
    ChangeBranchPublicationReceipt,
    ChangeBranchPublisher,
    ChangeBranchSupersessionReceipt,
    PublishChangeBranch,
    SupersedeChangeBranch,
)
from owlbear_delivery.change_workspace import (
    AdoptExternalHead,
    ChangeContinuationAction,
    ChangeCoordination,
    ChangeDesignPackageSnapshotReceipt,
    ChangeExternalHeadAdoptionReceipt,
    ChangeExternalHeadPromotionReceipt,
    ChangeFinalizationAttempt,
    ChangeTargetSyncAbortReceipt,
    ChangeTargetSyncConflictError,
    ChangeTargetSyncReceipt,
    ChangeTargetSyncStaleError,
    ChangeWorkspaceManager,
    ChangeWorktreeAttentionCode,
    ChangeWorktreeAttentionError,
    ChangeWriter,
    CoordinationConflictError,
    OutOfBandHeadRecoveryReceipt,
    PortfolioCoordinator,
    PromoteExternalHead,
    PublicationBaselineRecoveryReceipt,
    PublicationBaselineUnavailableError,
    RecoverOutOfBandHead,
    RetainedChangeWorktree,
    SyncChangeWithTarget,
    TargetSyncConflictRequest,
    WorkspaceRecoverySnapshot,
)
from owlbear_delivery.delivery_admission import DeliveryAdmissionReceipt
from owlbear_delivery.delivery_contract_discovery import (
    DeliveryChangeObservation,
    DeliveryDiscoveryRootError,
    contract_fingerprint,
    discover_persisted_changes,
)
from owlbear_delivery.delivery_runtime import (
    ActivateDeliveryClaim,
    AdministrativeDeliveryMove,
    AdministrativeDeliveryMovePreview,
    AdministrativeDeliveryMoveResult,
    AdvanceDelivery,
    DeliveryAcceptanceAttentionReason,
    DeliveryAcceptanceWaitingError,
    DeliveryActionSelectionConflictError,
    DeliveryActiveClaim,
    DeliveryBlock,
    DeliveryChangeAbandonment,
    DeliveryChangeDeferral,
    DeliveryChangeDispositionBusyError,
    DeliveryChangeDispositionKind,
    DeliveryChangeDispositionResolution,
    DeliveryChangePublicationHistory,
    DeliveryChangePublicationIdentity,
    DeliveryChangeStage,
    DeliveryCheckpointPublicationState,
    DeliveryCheckpointTrigger,
    DeliveryCheckpointTriggerKind,
    DeliveryFinalizationInvalidationReceipt,
    DeliveryFinalizationReceipt,
    DeliveryFrontier,
    DeliveryIntegrationAttention,
    DeliveryIntegrationAttentionCode,
    DeliveryIntegrationAttentionDisposition,
    DeliveryMergedPullRequestLatch,
    DeliveryPendingCheckpoint,
    DeliveryPendingStatePublication,
    DeliveryPlanCandidate,
    DeliveryRecoveryAttention,
    DeliveryRequest,
    DeliveryRequestKind,
    DeliveryRequestResolution,
    DeliveryResultCandidate,
    DeliveryReturnContext,
    DeliveryRuntime,
    DeliveryRuntimeConflictError,
    DeliveryRuntimeReferenceError,
    DeliveryStage,
    DeliveryTaskDefinition,
    DeliveryTaskResult,
    DeliveryTransition,
    DeliveryWorkerRole,
    FinalizeDeliveryChange,
    OutcomeAuthorityBinding,
    PrepareCompletedOutcomeRepair,
    PublishDeliveryPlan,
    PublishDeliveryResult,
    derive_change_stage,
    integration_attention_disposition,
    is_acceptance_waiting_observation,
    is_change_terminal,
    parse_delivery_frontier,
    repair_missing_request_provenance,
)
from owlbear_delivery.design_package import DesignPackageResult
from owlbear_delivery.draft_pull_request import (
    CreateOrReconcileDraftPullRequest,
    DraftPullRequestPublicationHistory,
    DraftPullRequestPublicationReceipt,
    DraftPullRequestPublisher,
    DraftPullRequestSupersessionReceipt,
    GeneratedPullRequestSummaryReceipt,
    MarkChangePullRequestReady,
    ObserveChangePublicationChecks,
    ObserveChangePublicationPullRequest,
    PublicationCheckObservationReceipt,
    PublicationPullRequestObservationReceipt,
    PullRequestReadyReceipt,
    ReadChangePublicationCheckObservations,
    ReadChangePublicationHistory,
    ReturnChangePullRequestToDraft,
    SupersedeDraftPullRequest,
    UpdateGeneratedPullRequestSummary,
)
from owlbear_delivery.finalization_reports import (
    FinalizationAttempt,
    FinalizationReport,
    FinalizationReportError,
    FinalizationReportSnapshot,
    FinalizationReportStore,
    ReportFinalizationFailure,
)
from owlbear_delivery.portfolio_operating import (
    DeliveryHealthDiagnostic,
    DeliveryHealthReason,
    DeliveryHealthResolution,
    DeliveryHealthStatus,
    DeliveryHealthView,
    PortfolioChangeAdmission,
    PortfolioChangeLifecycleStatus,
    PortfolioGuidanceFacts,
    PortfolioOperatingView,
    PortfolioWorkReference,
    PortfolioWorkScope,
    derive_portfolio_guidance,
)
from owlbear_delivery.publication_provider import (
    PublicationCheck,
    PublicationCheckSnapshot,
    PublicationProviderError,
    PublicationPullRequest,
    failed_required_publication_checks,
)
from owlbear_delivery.recovery import (
    MAX_RECOVERY_INTENTS,
    DeliveryWorkerExclusionRequiredError,
    RecoveryEvidence,
    RecoveryEvidenceProvider,
    RecoveryEvidenceReference,
    RecoveryIntent,
    RecoveryInvocation,
    RecoveryInvocationRequest,
    RecoveryReceipt,
    RetryAttempt,
    RetryEpisodeKey,
    RetryFailureClass,
    RetryLedger,
    RetryLedgerConflictError,
    RetryLedgerCorruptError,
    RetryReservation,
    RetryStopCode,
    UnavailableRecoveryEvidenceProvider,
    digest,
    invocation_path,
    is_canonical_admitted_path,
    journal_path,
    publish_record,
    read_record,
    verify_evidence,
)
from owlbear_delivery.runtime_transaction import (
    ReplacementTransactionParticipant,
    RuntimeTransaction,
    TransactionParticipant,
)
from owlbear_delivery.storage_io import atomic_write, locked_roots
from owlbear_delivery.target_contract import (
    DeliveryCommitment,
    DeliveryCompilationResult,
    DeliveryOutcome,
    compile_delivery_contract,
)
from owlbear_delivery.work_items import (
    ChangeGroupView,
    DeliveryPortfolioSnapshot,
    DeliveryReadiness,
    DeliveryReadinessBasis,
    DeliveryReadinessReason,
    WorkItemAction,
    WorkItemActionKind,
    WorkItemActivityState,
    WorkItemCardView,
    WorkItemClaimView,
    WorkItemDetailView,
    WorkItemNeed,
    WorkItemNextActor,
    WorkItemProjector,
    WorkItemPublicationPhase,
    WorkItemRecoveryView,
    WorkItemScope,
    WorkItemTargetSyncConflictView,
    WorkItemWorktreeCleanupView,
    WorkItemWorktreeRecoveryView,
    resolve_publication_phase,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator, Mapping

    from owlbear_delivery.completed_history import (
        CompletedChangePage,
        CompletedChangeRecord,
        CompletedHistoryCatalog,
    )
    from owlbear_delivery.delivery_admission import (
        DeliveryAdmissionRequest,
        DeliveryAdmissionResult,
        DeliveryAuthorityRegistry,
    )
    from owlbear_delivery.delivery_state import DeliveryStatePublicationReceipt, DeliveryStatePublisher
    from owlbear_delivery.design_package import (
        DesignCheckpointResult,
        DesignPackageStore,
        VerifiedDesignPackage,
    )
    from owlbear_delivery.work_items import WorkItemDetail, WorkItemProjection


def _timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        message = "Delivery claim timestamps must include a timezone"
        raise ValueError(message)
    return parsed.astimezone(UTC)


def _health_detail(detail: str | None, fallback: str) -> str:
    compact = " ".join((detail or "").split())
    return (compact or fallback)[:_MAX_HEALTH_DETAIL_LENGTH]


def _health_diagnostic_key(diagnostic: DeliveryHealthDiagnostic) -> tuple[object, ...]:
    return (
        diagnostic.source,
        diagnostic.code,
        diagnostic.detail,
        diagnostic.change_id,
        diagnostic.path,
        diagnostic.retry_safe,
        diagnostic.reason,
        diagnostic.resolution,
        diagnostic.expected_head,
        diagnostic.observed_head,
        diagnostic.observed_local_head,
        diagnostic.head_relation,
    )


def _canonical_model_bytes(model: BaseModel) -> bytes:
    return (json.dumps(model.model_dump(mode="json"), sort_keys=True, separators=(",", ":")) + "\n").encode()


_MAX_PULL_REQUEST_TITLE_LENGTH = 256
_MAX_ACCEPTANCE_RECONCILIATION_CHANGES = 8
_ACCEPTANCE_RECONCILIATION_CURSOR_FILE = "cursor.json"
_ATTENTION_RESOLUTION_LOCK_TIMEOUT_SECONDS = 2.0
_ATTENTION_RESOLUTION_LOCK_RETRY_SECONDS = 0.05
_MAX_REQUIRED_CHECK_DIAGNOSTICS = 8
_MAX_CHECK_DIAGNOSTIC_VALUE_LENGTH = 160
_MAX_AUTOMATION_PATHS = 32
_MAX_AUTOMATION_PATH_LENGTH = 240
_MAX_PR_OUTCOMES = 24
_MAX_PR_GOAL_LENGTH = 1_200
_MAX_PR_INTENT_LENGTH = 1_600
_MAX_PR_OUTCOME_TITLE_LENGTH = 180
_MAX_PR_OUTCOME_PROMISE_LENGTH = 480
_CHECKPOINT_RETRY_BASE_SECONDS = 5
_CHECKPOINT_RETRY_MAX_SECONDS = 5 * 60
_CHECKPOINT_RETRY_ERROR_CODE = "ERR_DELIVERY_CHECKPOINT_RECONCILIATION"
_CHECKPOINT_REVIEW_ERROR_CODE = "ERR_DELIVERY_CHECKPOINT_AWAITS_REVIEW"
_CHECKPOINT_MISSING_HEAD_ERROR_CODE = "ERR_DELIVERY_CHECKPOINT_HEAD_MISSING"
_MAX_CHECKPOINT_ERROR_DETAIL_LENGTH = 240
_PUBLICATION_OBSERVATION_CACHE_SECONDS = 15
_MAX_HEALTH_DETAIL_LENGTH = 240
_MAX_HEALTH_DIAGNOSTICS = 64
_INTENT_SUMMARY_HEADING = "Problem And Product Promise"
_logger = logging.getLogger(__name__)


def _failed_required_publication_checks(snapshot: PublicationCheckSnapshot) -> tuple[PublicationCheck, ...]:
    """Return provider-marked required checks with terminal non-success evidence."""
    return failed_required_publication_checks(snapshot)


def _check_diagnostic_value(value: str | None) -> str:
    """Bound provider-controlled values embedded in durable attention diagnostics."""
    if value is None:
        return "<missing>"
    printable = "".join(character if character.isprintable() else " " for character in value)
    compact = " ".join(printable.split())
    return (compact or "<empty>")[:_MAX_CHECK_DIAGNOSTIC_VALUE_LENGTH]


def _required_check_diagnostics(
    snapshot: PublicationCheckSnapshot,
    observation_id: str,
    failures: tuple[PublicationCheck, ...],
) -> tuple[str, ...]:
    """Build deterministic bounded attention diagnostics for one check observation."""
    ordered = tuple(sorted(failures, key=lambda check: (check.name.casefold(), check.check_id)))
    diagnostics = [
        "required-publication-check-failure",
        f"exact-head:{snapshot.head_sha}",
        f"check-observation:{observation_id}",
        f"failing-required-checks:{len(ordered)}",
    ]
    diagnostics.extend(
        "required-check:"
        f"{_check_diagnostic_value(check.check_id)}:"
        f"name={_check_diagnostic_value(check.name)}:"
        f"status={_check_diagnostic_value(check.status)}:"
        f"conclusion={_check_diagnostic_value(check.conclusion)}"
        for check in ordered[:_MAX_REQUIRED_CHECK_DIAGNOSTICS]
    )
    if len(ordered) > _MAX_REQUIRED_CHECK_DIAGNOSTICS:
        diagnostics.append(f"required-checks-truncated:{len(ordered) - _MAX_REQUIRED_CHECK_DIAGNOSTICS}")
    return tuple(diagnostics)


def _operating_scope(scope: WorkItemScope) -> PortfolioWorkScope:
    if scope == WorkItemScope.CHANGE_PUBLICATION:
        return PortfolioWorkScope.PUBLICATION
    return PortfolioWorkScope.OUTCOME


def _checkpoint_operation_id(kind: str, *parts: str) -> str:
    payload = json.dumps((kind, *parts), separators=(",", ":"))
    return f"checkpoint-{kind}-{hashlib.sha256(payload.encode()).hexdigest()}"


def _checkpoint_retry_ready(pending: DeliveryPendingCheckpoint, now: datetime) -> bool:
    """Return whether a failed checkpoint has waited its bounded retry delay."""
    if pending.last_attempted_at is None or pending.attempt_count == 0:
        return True
    exponent = min(max(pending.attempt_count - 1, 0), 6)
    delay_seconds = min(_CHECKPOINT_RETRY_MAX_SECONDS, _CHECKPOINT_RETRY_BASE_SECONDS * 2**exponent)
    return now >= pending.last_attempted_at + timedelta(seconds=delay_seconds)


def _checkpoint_error_detail(value: str, fallback: str) -> str:
    """Bound provider or Git text retained in checkpoint diagnostics."""
    printable = "".join(character if character.isprintable() else " " for character in value)
    return (" ".join(printable.split()) or fallback)[:_MAX_CHECKPOINT_ERROR_DETAIL_LENGTH]


def _checkpoint_error_code(exc: BaseException) -> str:
    """Return a stable bounded code for one checkpoint reconciliation failure."""
    value = getattr(exc, "code", None)
    return value[:120] if isinstance(value, str) and value else _CHECKPOINT_RETRY_ERROR_CODE


def _checkpoint_awaits_review(runtime: DeliveryRuntime) -> bool:
    """Return whether target synchronization requires fresh finalization before publication."""
    target_sync = runtime.target_sync_receipt()
    return target_sync is not None and target_sync.review_required and runtime.finalization() is None


def _dirty_recovery_operation_id(change_id: str, outcome_id: str, attempt_id: str, claim_id: str) -> str:
    payload = json.dumps(
        ("dirty-worktree-recovery", change_id, outcome_id, attempt_id, claim_id),
        separators=(",", ":"),
    )
    return f"recover-dirty-{hashlib.sha256(payload.encode()).hexdigest()}"


def _checkpoint_summary(  # noqa: PLR0913 - summary binds semantic and checkpoint publication inputs.
    runtime: DeliveryRuntime,
    package: VerifiedDesignPackage,
    pending: DeliveryPendingCheckpoint | None,
    head: str,
    automation_paths: tuple[str, ...],
    *,
    supersedes_publication_id: str | None = None,
) -> str:
    goal, intent = _intent_summary(package.intent_bytes, runtime)
    bindings = {binding.outcome_id: binding for binding in runtime.bindings()}
    completed_outcomes = sum(binding.stage == DeliveryStage.COMPLETED for binding in bindings.values())
    lines = [
        "> **OwlBear-managed pull request:**",
        "> Do not manually change this PR's draft/ready state or push to its branch.",
        "> Use Delivery controls so provider state and Delivery evidence stay synchronized.",
        "",
        "## Goal",
        "",
        f"> {_summary_text(goal, _MAX_PR_GOAL_LENGTH)}",
        "",
        "## Intent",
        "",
        f"> {_summary_text(intent, _MAX_PR_INTENT_LENGTH)}",
        "",
        "## Promised Outcomes",
        "",
    ]
    visible_outcomes = runtime.contract.outcomes[:_MAX_PR_OUTCOMES]
    for outcome in visible_outcomes:
        binding = bindings[outcome.outcome_id]
        complete = binding.stage == DeliveryStage.COMPLETED
        state = "complete" if complete else binding.stage.value
        checkbox = "x" if complete else " "
        outcome_line = (
            f"- [{checkbox}] **{_summary_text(outcome.title, _MAX_PR_OUTCOME_TITLE_LENGTH)}** "
            f"(`{outcome.outcome_id}`; {state})"
        )
        lines.extend(
            (
                outcome_line,
                f"  Promised result: {_summary_text(outcome.promise, _MAX_PR_OUTCOME_PROMISE_LENGTH)}",
            )
        )
    omitted_outcomes = len(runtime.contract.outcomes) - len(visible_outcomes)
    if omitted_outcomes:
        lines.append(f"- {omitted_outcomes} additional Outcome(s) omitted from this summary")
    lines.extend(
        (
            "",
            "## Delivery Status",
            "",
            f"As of reviewed checkpoint `{head}`:",
            "",
            f"- Outcomes complete: {completed_outcomes} of {len(runtime.contract.outcomes)}",
        )
    )
    if pending is not None:
        lines.append(
            f"- Checkpoint includes: {', '.join(_checkpoint_trigger_label(trigger) for trigger in pending.triggers)}"
        )
    finalization = runtime.finalization()
    if finalization is not None and finalization.exact_head == head:
        lines.extend(
            (
                "- Delivery finalization: recorded for this checkpoint",
                "- Independent exact-commit review: passed for this checkpoint",
            )
        )
    if supersedes_publication_id is not None:
        lines.append(f"- Publication supersedes provider publication `{supersedes_publication_id}`")
    lines.extend(_automation_summary(automation_paths))
    if finalization is not None and finalization.exact_head == head:
        lines.extend(
            (
                "",
                "## Review And Merge",
                "",
                (
                    "- To evaluate and address reviewer feedback, run "
                    f"`/address-pr-feedback {runtime.contract.change_id}`."
                ),
                (
                    "- When satisfied with the review, merge this pull request in GitHub; "
                    "Delivery records acceptance afterward."
                ),
            )
        )
    return "\n".join(lines)


def _checkpoint_trigger_label(trigger: DeliveryCheckpointTrigger) -> str:
    if trigger.kind == DeliveryCheckpointTriggerKind.ADMITTED_DESIGN:
        return "admitted Design package"
    if trigger.kind == DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK:
        return "first promoted Task result"
    if trigger.kind == DeliveryCheckpointTriggerKind.VERIFIED_TASK:
        return "verified Task result"
    if trigger.kind == DeliveryCheckpointTriggerKind.VERIFIED_OUTCOME:
        return f"Outcome `{trigger.outcome_id}` verified"
    if trigger.kind == DeliveryCheckpointTriggerKind.FINALIZATION:
        return "finalization recorded"
    return "explicit publication request"


def _intent_summary(intent_bytes: bytes, runtime: DeliveryRuntime) -> tuple[str, str]:
    paragraphs = _intent_summary_paragraphs(intent_bytes)
    if paragraphs:
        goal = paragraphs[0]
        intent = " ".join(paragraphs[1:]).strip() or "Deliver the promised Outcomes below."
        return goal, intent
    fallback = next(
        (
            commitment.statement
            for commitment in runtime.contract.commitments
            if commitment.commitment_class.value in {"dealbreaker", "protected-request"}
        ),
        runtime.contract.title,
    )
    return fallback, "Deliver the promised Outcomes below."


def _intent_summary_paragraphs(intent_bytes: bytes) -> tuple[str, ...]:
    text = intent_bytes.decode("utf-8", errors="replace")
    tokens = MarkdownIt("commonmark").parse(text)
    in_summary_section = False
    in_paragraph = False
    paragraphs: list[str] = []
    for index, token in enumerate(tokens):
        if token.type == "heading_open":
            heading = ""
            if index + 1 < len(tokens) and tokens[index + 1].type == "inline":
                heading = tokens[index + 1].content
            if token.tag == "h2" and heading == _INTENT_SUMMARY_HEADING:
                in_summary_section = True
            elif token.tag in {"h1", "h2"}:
                in_summary_section = False
            in_paragraph = False
        elif token.type == "paragraph_open":
            in_paragraph = in_summary_section
        elif token.type == "paragraph_close":
            in_paragraph = False
        elif token.type == "inline" and in_paragraph and token.content.strip():
            paragraphs.append(token.content)
    return tuple(paragraphs)


def _summary_text(value: str, max_length: int) -> str:
    normalized = " ".join("".join(character if character.isprintable() else " " for character in value).split())
    if not normalized:
        return "Not provided."
    escaped = _escape_summary_text(normalized)
    if len(escaped) <= max_length:
        return escaped
    suffix = "..."
    low = 0
    high = len(normalized)
    while low < high:
        midpoint = (low + high + 1) // 2
        candidate = normalized[:midpoint].rstrip() + suffix
        if len(_escape_summary_text(candidate)) <= max_length:
            low = midpoint
        else:
            high = midpoint - 1
    return _escape_summary_text(normalized[:low].rstrip() + suffix)


def _escape_summary_text(value: str) -> str:
    escaped = html.escape(value, quote=False)
    replacements = {
        ord(character): replacement
        for character, replacement in (
            ("\\", "&#92;"),
            ("`", "&#96;"),
            ("@", "&#64;"),
            ("#", "&#35;"),
            (":", "&#58;"),
            ("/", "&#47;"),
            ("*", "&#42;"),
            ("_", "&#95;"),
            ("[", "&#91;"),
            ("]", "&#93;"),
            ("~", "&#126;"),
            ("|", "&#124;"),
        )
    }
    return escaped.translate(replacements)


def _automation_summary(paths: tuple[str, ...]) -> tuple[str, ...]:
    """Render bounded repository automation paths for a generated PR summary."""
    if not paths:
        return ()
    lines = ["", "### Repository automation changed"]
    visible = paths[:_MAX_AUTOMATION_PATHS]
    lines.extend(f"- {_automation_path_markup(path)}" for path in visible)
    omitted = len(paths) - len(visible)
    if omitted:
        lines.append(f"- {omitted} additional automation path(s) omitted")
    return tuple(lines)


def _automation_path_markup(path: str) -> str:
    """Escape and bound one repository-controlled path for Markdown HTML."""
    printable = []
    for character in path:
        if character == "\n":
            printable.append(r"\n")
        elif character == "\r":
            printable.append(r"\r")
        elif character == "\t":
            printable.append(r"\t")
        elif character.isprintable():
            printable.append(character)
        else:
            printable.append(f"\\u{ord(character):04x}")
    bounded = "".join(printable)
    if len(bounded) > _MAX_AUTOMATION_PATH_LENGTH:
        bounded = f"{bounded[: _MAX_AUTOMATION_PATH_LENGTH - 3]}..."
    escaped = html.escape(bounded, quote=True).replace("`", "&#96;")
    return f"<code>{escaped}</code>"


def _checkpoint_pull_request_title(runtime: DeliveryRuntime) -> str:
    printable = "".join(character if character.isprintable() else " " for character in runtime.contract.title)
    title = " ".join(printable.split()) or f"Delivery Change {runtime.contract.change_id}"
    if len(title) <= _MAX_PULL_REQUEST_TITLE_LENGTH:
        return title
    return f"{title[: _MAX_PULL_REQUEST_TITLE_LENGTH - 3]}..."


def _publication_identity(
    publication: DraftPullRequestPublicationReceipt,
) -> DeliveryChangePublicationIdentity:
    return DeliveryChangePublicationIdentity(
        change_id=publication.change_id,
        repository=publication.repository,
        number=publication.number,
        node_id=publication.node_id,
        head_sha=publication.head_sha,
    )


def _operator_claim(claim: DeliveryActiveClaim | None) -> DeliveryOperatorClaim | None:
    if claim is None:
        return None
    return DeliveryOperatorClaim(
        attempt_id=claim.attempt_id,
        claim_id=claim.claim_id,
        started_at=claim.started_at,
        worker_role=claim.worker_role,
        task_id=claim.task_id,
    )


def _operator_recovery_attention(
    attention: DeliveryRecoveryAttention | None,
) -> DeliveryOperatorRecoveryAttention | None:
    if attention is None:
        return None
    return DeliveryOperatorRecoveryAttention(
        attempt_id=attention.attempt_id,
        claim_id=attention.claim_id,
        reason=attention.reason,
        custody_retained=attention.custody_retained,
        retry_condition=attention.retry_condition,
    )


def _operator_integration_attention(
    attention: DeliveryIntegrationAttention | None,
) -> DeliveryOperatorIntegrationAttention | None:
    if attention is None:
        return None
    return DeliveryOperatorIntegrationAttention(
        code=attention.code,
        disposition=integration_attention_disposition(attention.code),
        diagnostics=attention.diagnostics,
        retry_condition=attention.retry_condition,
    )


class _ApplicationModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class DeliveryRolePolicy(_ApplicationModel):
    """Worker and reviewer agents for one mechanical stage role."""

    worker_role: DeliveryWorkerRole
    worker_agent: str = Field(min_length=1)
    reviewer_agent: str = Field(min_length=1)


class DeliveryActionSelection(_ApplicationModel):
    """Fence one explicitly selected next Planner or Builder action."""

    change_id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    expected_stage: Literal[DeliveryStage.PLANNING, DeliveryStage.IMPLEMENTATION]
    expected_task_id: str | None = Field(default=None, min_length=1)
    expected_frontier_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_source_head: str = Field(pattern=r"^[0-9a-f]{40}$")

    @model_validator(mode="after")
    def _validate_task_selection(self) -> DeliveryActionSelection:
        if (self.expected_stage == DeliveryStage.IMPLEMENTATION) != (self.expected_task_id is not None):
            message = "only an Implementation selection requires the expected next task identity"
            raise ValueError(message)
        return self


class DeliveryLaunchPackage(_ApplicationModel):
    """Bounded identity and source locators for one named worker invocation."""

    change_id: str = Field(min_length=1)
    authority_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    plan_scope_id: str = Field(pattern=r"^SCOPE-[0-9]{3}$")
    task_id: str | None = None
    claim: DeliveryActiveClaim
    policy: DeliveryRolePolicy
    package_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    package_root: Path
    worktree_path: Path
    branch: str = Field(min_length=1)
    source_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    integration_target: str = Field(min_length=1)
    last_reviewed_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    writer: ChangeWriter | None = None

    @model_validator(mode="after")
    def _validate_role_custody(self) -> DeliveryLaunchPackage:
        if self.policy.worker_role != self.claim.worker_role or self.task_id != self.claim.task_id:
            message = "launch policy and task identity must match the active claim"
            raise ValueError(message)
        if (self.claim.worker_role == DeliveryWorkerRole.BUILDER) != (self.writer is not None):
            message = "only Build launch packages carry writer custody"
            raise ValueError(message)
        if self.writer is not None and (
            self.writer.attempt_id != self.claim.attempt_id
            or self.writer.claim_id != self.claim.claim_id
            or self.writer.actor_id != self.claim.owner_id
            or self.writer.process_id != self.claim.process_id
        ):
            message = "writer custody must match the active claim"
            raise ValueError(message)
        return self


class DeliveryContinuationRequest(_ApplicationModel):
    """Acquire at most one supported action from an observed Change view."""

    change_id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    expected_basis: DeliveryReadinessBasis
    capabilities: tuple[Literal["planner", "builder", "finalizer", "engine"], ...]
    host_id: str = Field(min_length=1, max_length=128)
    session_id: str = Field(min_length=1, max_length=128)

    @model_validator(mode="after")
    def _validate_basis(self) -> DeliveryContinuationRequest:
        if self.expected_basis.contract_digest is None or self.expected_basis.frontier_digest is None:
            message = "continuation requires an observed contract and frontier"
            raise ValueError(message)
        if len(set(self.capabilities)) != len(self.capabilities):
            message = "continuation capabilities must be unique"
            raise ValueError(message)
        return self


DeliveryContinuationReason = (
    DeliveryReadinessReason
    | Literal[
        "host-capability-unavailable",
        "execution-capacity",
        "execution-occupancy-unavailable",
        "source-head-changed",
        "state-publication-reconciled",
        "state-publication-failed",
        "operation-in-progress",
        "publication-reconciliation-required",
        "readiness-changed",
        "source-unavailable",
        "repair-required",
        "engine-action-completed",
        "engine-action-incomplete",
        "engine-action-failed",
        "engine-action-interrupted",
        "engine-owner-unavailable",
        "merge-approval-required",
    ]
)


class DeliveryContinuationResult(_ApplicationModel):
    """One launch or a non-dispatching disposition; never a portfolio batch."""

    change_id: str = Field(min_length=1)
    kind: Literal[
        "acquired", "reconciled", "busy", "stale", "waiting", "human", "unsupported", "unavailable", "terminal"
    ]
    reason_code: DeliveryContinuationReason
    readiness: DeliveryReadiness
    failure: DeliveryAcquisitionFailure | None = None
    launch: DeliveryLaunchPackage | None = None
    finalization: DeliveryFinalizationLaunch | None = None
    engine_action: ChangeContinuationAction | None = None
    engine_result: DeliveryEngineActionResult | None = None

    @model_validator(mode="after")
    def _validate_launch(self) -> DeliveryContinuationResult:
        launches = sum(item is not None for item in (self.launch, self.finalization, self.engine_action))
        if launches != (1 if self.kind == "acquired" else 0):
            message = "only acquired continuation results carry a launch"
            raise ValueError(message)
        if self.launch is not None and self.launch.change_id != self.change_id:
            message = "continuation launch must belong to the selected Change"
            raise ValueError(message)
        if self.finalization is not None and self.finalization.context.change_id != self.change_id:
            message = "finalization launch must belong to the selected Change"
            raise ValueError(message)
        if self.failure is not None and (self.kind != "unavailable" or self.failure.change_id != self.change_id):
            message = "continuation failure requires an unavailable result for the selected Change"
            raise ValueError(message)
        if self.engine_action is not None and (
            self.engine_action.change_id != self.change_id or self.engine_action.finished_at is not None
        ):
            message = "engine action must belong to the selected Change"
            raise ValueError(message)
        if self.engine_result is not None and (
            self.engine_result.action.change_id != self.change_id or self.kind == "acquired"
        ):
            message = "engine result must belong to a non-acquired selected Change response"
            raise ValueError(message)
        if self.engine_result is not None:
            kinds = {"completed": "reconciled", "waiting": "human", "stale": "stale", "blocked": "unavailable"}
            if (
                self.kind != kinds[self.engine_result.kind]
                or self.reason_code != self.engine_result.reason_code
                or self.failure != self.engine_result.failure
            ):
                message = "continuation must preserve the exact engine disposition and failure"
                raise ValueError(message)
        return self


class DeliveryAcquisitionFailure(_ApplicationModel):
    """Bounded fail-closed preparation result, optionally tied to a started claim."""

    change_id: str = Field(min_length=1)
    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    attempt_id: str | None = None
    claim_id: str | None = None
    code: str = Field(min_length=1)
    detail: str = Field(min_length=1)
    retry_condition: str = Field(min_length=1)


class DeliveryIntegrationAttentionStatus(_ApplicationModel):
    """One non-retryable Integration attention exposed by acquisition."""

    change_id: str = Field(min_length=1)
    code: DeliveryIntegrationAttentionCode
    disposition: DeliveryIntegrationAttentionDisposition
    retry_condition: str = Field(min_length=1)


class DeliveryClaimRecoveryStatus(StrEnum):
    """Observable disposition of one exact-claim recovery request."""

    RECOVERED = "recovered"
    ATTENTION = "attention"


class DeliveryClaimRecoveryResult(_ApplicationModel):
    """Recovered claim state, isolated preservation evidence, or retained repair attention."""

    status: DeliveryClaimRecoveryStatus
    change_id: str = Field(min_length=1)
    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    attempt_id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)
    preserved_commit: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    preserved_ref: str | None = None
    quarantine_commit: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    quarantine_ref: str | None = None
    attention: DeliveryRecoveryAttention | None = None

    @model_validator(mode="after")
    def _validate_disposition(self) -> DeliveryClaimRecoveryResult:
        if (self.status == DeliveryClaimRecoveryStatus.ATTENTION) != (self.attention is not None):
            message = "only retained recovery requires repair attention"
            raise ValueError(message)
        if (self.quarantine_commit is None) != (self.quarantine_ref is None):
            message = "quarantine recovery evidence requires both commit and ref"
            raise ValueError(message)
        return self


class DeliveryRepairKind(StrEnum):
    """High-level repair proposal categories exposed by the application facade."""

    CONFIRM_LOST_WORKER = "confirm-lost-worker"


class DeliveryRepairProposal(_ApplicationModel):
    """One versioned repair choice that can be applied without caller-selected internals."""

    proposal_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    kind: DeliveryRepairKind
    change_id: str = Field(min_length=1)
    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    attempt_id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)
    expected_frontier_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    summary: str = Field(min_length=1)
    consequence: str = Field(min_length=1)

    @classmethod
    def create(  # noqa: PLR0913 - proposal identity binds each exact repair input.
        cls,
        *,
        kind: DeliveryRepairKind,
        change_id: str,
        outcome_id: str,
        attempt_id: str,
        claim_id: str,
        expected_frontier_digest: str,
        summary: str,
        consequence: str,
    ) -> DeliveryRepairProposal:
        """Create a stable proposal identity from the exact repair evidence."""
        values = {
            "kind": kind,
            "change_id": change_id,
            "outcome_id": outcome_id,
            "attempt_id": attempt_id,
            "claim_id": claim_id,
            "expected_frontier_digest": expected_frontier_digest,
            "summary": summary,
            "consequence": consequence,
        }
        proposal_id = hashlib.sha256(
            json.dumps(
                {key: value.value if isinstance(value, StrEnum) else value for key, value in values.items()},
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
        return cls(proposal_id=proposal_id, **values)


class DeliveryRepairResult(_ApplicationModel):
    """One repair diagnosis or the exact recovery result of an applied proposal."""

    change_id: str = Field(min_length=1)
    proposal: DeliveryRepairProposal | None = None
    recovery: DeliveryClaimRecoveryResult | None = None

    @model_validator(mode="after")
    def _validate_result(self) -> DeliveryRepairResult:
        if self.proposal is None and self.recovery is None:
            return self
        if self.proposal is not None and self.recovery is not None:
            message = "repair result cannot contain both proposal and recovery"
            raise ValueError(message)
        if self.proposal is not None and self.proposal.change_id != self.change_id:
            message = "repair proposal does not match its Change"
            raise ValueError(message)
        if self.recovery is not None and self.recovery.change_id != self.change_id:
            message = "repair recovery does not match its Change"
            raise ValueError(message)
        return self


class DeliveryUnresolvedOutcome(_ApplicationModel):
    """Bounded unresolved outcome evidence retained alongside Change detail."""

    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    card: WorkItemCardView
    requests: tuple[DeliveryRequest, ...] = ()
    block: DeliveryBlock | None = None
    active_claim: WorkItemClaimView | None = None
    recovery_attention: WorkItemRecoveryView | None = None


class DeliveryChangeView(_ApplicationModel):
    """One coherent semantic, health, and repair view for a Delivery Change."""

    change_id: str = Field(min_length=1)
    frontier_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    detail: WorkItemDetailView
    health: DeliveryHealthView
    repair: DeliveryRepairResult | None = None
    unresolved_outcomes: tuple[DeliveryUnresolvedOutcome, ...] = ()
    kind: Literal["available"] = "available"
    readiness: DeliveryReadiness
    finalization_attempt: ChangeFinalizationAttempt | None = None
    continuation_action: ChangeContinuationAction | None = None


class DeliveryUnavailableChangeView(_ApplicationModel):
    """Known Change whose canonical runtime authority could not be composed."""

    kind: Literal["unavailable"] = "unavailable"
    change_id: str = Field(min_length=1)
    title: str | None = None
    diagnostics: tuple[Literal["runtime-unavailable", "coordination-unavailable"], ...] = ("runtime-unavailable",)
    coordination_status: Literal["missing", "unreadable"] | None = None
    readiness: DeliveryReadiness


class _FinalizationReadUnavailableError(RuntimeError):
    def __init__(self, readiness: DeliveryReadiness) -> None:
        self.readiness = readiness
        super().__init__(readiness.reason_code)


class DeliveryResultSubmission(_ApplicationModel):
    """One claim-bound Builder result submitted for publication and promotion."""

    change_id: str = Field(min_length=1)
    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    claim_id: str = Field(min_length=1)
    result: DeliveryTaskResult


class DeliveryResultSubmissionResult(_ApplicationModel):
    """The promoted Builder result and its current runtime binding."""

    kind: Literal["submitted"] = "submitted"
    change_id: str = Field(min_length=1)
    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    claim_id: str = Field(min_length=1)
    result_id: str = Field(min_length=1)
    binding: OutcomeAuthorityBinding

    @model_validator(mode="after")
    def _validate_binding(self) -> DeliveryResultSubmissionResult:
        if self.binding.outcome_id != self.outcome_id:
            message = "submitted result binding does not match its Outcome"
            raise ValueError(message)
        return self


class DeliveryDesignPut(_ApplicationModel):
    """One create-or-CAS-revise request for authored Design bytes."""

    change_id: str = Field(min_length=1)
    intent_bytes: bytes
    design_bytes: bytes
    expected_package_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


class DeliveryChangeIntentKind(StrEnum):
    """User-directed Change lifecycle intent categories."""

    DEFER = "defer"
    RESUME = "resume"
    ABANDON = "abandon"


class DeliveryChangeIntent(_ApplicationModel):
    """One version-bound request to pause, resume, or abandon a Change."""

    change_id: str = Field(min_length=1)
    kind: DeliveryChangeIntentKind
    expected_frontier_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    reason: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def _validate_reason(self) -> DeliveryChangeIntent:
        if self.kind is DeliveryChangeIntentKind.RESUME:
            if self.reason is not None:
                message = "resume intent does not accept a reason"
                raise ValueError(message)
        elif self.reason is None or not self.reason.strip():
            message = "defer and abandon intents require a reason"
            raise ValueError(message)
        return self


class DeliveryChangeIntentResult(_ApplicationModel):
    """The applied Change intent receipt and resulting frontier version."""

    change_id: str = Field(min_length=1)
    kind: DeliveryChangeIntentKind
    frontier_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    receipt: DeliveryChangeDeferral | DeliveryChangeAbandonment

    @model_validator(mode="after")
    def _validate_receipt(self) -> DeliveryChangeIntentResult:
        if self.receipt.change_id != self.change_id:
            message = "Change intent receipt does not match its Change"
            raise ValueError(message)
        if self.kind is DeliveryChangeIntentKind.ABANDON and not isinstance(self.receipt, DeliveryChangeAbandonment):
            message = "abandon intent requires an abandonment receipt"
            raise ValueError(message)
        if self.kind is not DeliveryChangeIntentKind.ABANDON and not isinstance(self.receipt, DeliveryChangeDeferral):
            message = "defer or resume intent requires a deferral receipt"
            raise ValueError(message)
        return self


class DeliveryAnswerKind(StrEnum):
    """High-level user answer targets currently supported by Delivery."""

    REQUEST = "request"
    BLOCK = "block"
    DISPOSITION = "disposition"


class DeliveryAnswer(_ApplicationModel):
    """One version-bound answer to a retained request or requestless block."""

    change_id: str = Field(min_length=1)
    kind: DeliveryAnswerKind = DeliveryAnswerKind.REQUEST
    expected_frontier_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    request_id: str | None = None
    resolution: DeliveryRequestResolution | None = None
    outcome_id: str | None = Field(default=None, pattern=r"^OUT-[0-9]{3}$")
    block_id: str | None = None
    operator_note: str | None = None
    locators: tuple[str, ...] = ()
    expected_disposition_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _validate_target(self) -> DeliveryAnswer:
        if self.kind is DeliveryAnswerKind.REQUEST:
            if self.request_id is None or self.resolution is None:
                message = "request answers require request identity and resolution"
                raise ValueError(message)
            if any((self.outcome_id, self.block_id, self.operator_note)) or self.locators:
                message = "request answers cannot include block evidence"
                raise ValueError(message)
        elif self.kind is DeliveryAnswerKind.BLOCK:
            if (
                self.outcome_id is None
                or self.block_id is None
                or self.operator_note is None
                or not self.operator_note.strip()
                or not self.locators
            ):
                message = "block answers require outcome, block, note, and locators"
                raise ValueError(message)
            if self.request_id is not None or self.resolution is not None:
                message = "block answers cannot include request resolution"
                raise ValueError(message)
        else:
            if self.expected_disposition_id is None:
                message = "disposition answers require an expected disposition identity"
                raise ValueError(message)
            if any((self.request_id, self.outcome_id, self.block_id, self.operator_note)) or self.locators:
                message = "disposition answers cannot include request or block evidence"
                raise ValueError(message)
        return self


class DeliveryAnswerResult(_ApplicationModel):
    """The answered authority and frontier version after an accepted answer."""

    change_id: str = Field(min_length=1)
    kind: DeliveryAnswerKind
    frontier_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    request: DeliveryRequest | None = None
    binding: OutcomeAuthorityBinding | None = None
    disposition: DeliveryChangeDispositionResolution | None = None

    @model_validator(mode="after")
    def _validate_result(self) -> DeliveryAnswerResult:
        if self.kind is DeliveryAnswerKind.REQUEST and self.request is None:
            message = "request answer results require the resolved request"
            raise ValueError(message)
        if self.kind is DeliveryAnswerKind.BLOCK and self.binding is None:
            message = "block answer results require the cleared binding"
            raise ValueError(message)
        if self.kind is DeliveryAnswerKind.DISPOSITION and self.disposition is None:
            message = "disposition answer results require the resolution receipt"
            raise ValueError(message)
        return self


class DeliveryAcquisitionResult(_ApplicationModel):
    """Launchable task claims plus typed attention from one refresh."""

    launch_packages: tuple[DeliveryLaunchPackage, ...]
    integration_attention: tuple[DeliveryIntegrationAttentionStatus, ...] = ()
    recoveries: tuple[DeliveryClaimRecoveryResult, ...] = ()
    failures: tuple[DeliveryAcquisitionFailure, ...] = ()
    health_hint: str | None = Field(default=None, max_length=240)


class DeliveryPlanContext(_ApplicationModel):
    """Plan authority and current same-outcome successor context."""

    launch: DeliveryLaunchPackage
    outcome: DeliveryOutcome
    commitments: tuple[DeliveryCommitment, ...]
    requests: tuple[DeliveryRequest, ...]
    return_context: DeliveryReturnContext | None = None


class DeliveryBuildContext(_ApplicationModel):
    """Build authority, predecessor results, and current source coordination."""

    launch: DeliveryLaunchPackage
    task: DeliveryTaskDefinition
    task_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    commitments: tuple[DeliveryCommitment, ...]
    predecessor_results: tuple[DeliveryTaskResult, ...]
    requests: tuple[DeliveryRequest, ...]
    return_context: DeliveryReturnContext | None = None
    recovery_attention: DeliveryRecoveryAttention | None = None


class DeliveryFinalizationContext(_ApplicationModel):
    """Engine-resolved read context for exact Change finalization."""

    change_id: str = Field(min_length=1)
    branch: str = Field(min_length=1)
    worktree_path: Path
    change_head: str | None = Field(pattern=r"^[0-9a-f]{40}$")
    reviewed_change_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    publication_phase: WorkItemPublicationPhase
    ready_for_finalization: bool
    readiness_diagnostics: tuple[str, ...]
    finalization_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    finalized_head: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    finalization_invalidation_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    readiness: DeliveryReadiness


class DeliveryFinalizationLaunch(_ApplicationModel):
    """Finalizer handoff; use the attempt identity as the finalization operation ID."""

    attempt: ChangeFinalizationAttempt
    context: DeliveryFinalizationContext


class DeliveryRetainedWorktreeCleanupBlockReason(StrEnum):
    """Why one retained Change worktree cannot yet be cleaned up."""

    ORPHAN = "orphan"
    COMPLETION_STATE_INCONSISTENT = "completion-state-inconsistent"
    NONTERMINAL = "nonterminal"
    ACTIVE_WRITER = "active-writer"
    ACTIVE_PUBLICATION_LEASE = "active-publication-lease"
    WORKTREE_ATTENTION = "worktree-attention"


class DeliveryRetainedChangeWorktree(_ApplicationModel):
    """Bounded retained-worktree inventory row for Delivery consumers."""

    change_id: str = Field(min_length=1)
    worktree_path: Path
    branch: str = Field(min_length=1)
    branch_head: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    recovery_reviewed_head: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    coordination_registered: bool
    git_registered: bool
    worktree_present: bool
    worktree_head: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    worktree_branch: str | None = None
    worktree_locked: bool = False
    worktree_prunable: bool = False
    worktree_bare: bool = False
    attention: tuple[ChangeWorktreeAttentionCode, ...] = ()
    lifecycle: DeliveryChangeStage | None = None
    orphan: bool
    cleanup_eligible: bool
    cleanup_blocked_reason: DeliveryRetainedWorktreeCleanupBlockReason | None = None


class DeliveryChangeWorktreeCleanup(_ApplicationModel):
    """Application receipt for one exact managed Change worktree cleanup."""

    cleanup_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    change_id: str = Field(min_length=1)
    branch: str = Field(min_length=1)
    worktree_path: Path
    branch_head: str = Field(pattern=r"^[0-9a-f]{40}$")


class DeliveryChangeWorktreeRecovery(_ApplicationModel):
    """Application receipt for one exact managed Change worktree recovery."""

    change_id: str = Field(min_length=1)
    branch: str = Field(min_length=1)
    worktree_path: Path
    branch_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    recovery_reviewed_head: str = Field(pattern=r"^[0-9a-f]{40}$")


class DeliveryOperatorClaim(_ApplicationModel):
    """Bounded active-claim identity required for explicit operator recovery."""

    attempt_id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)
    started_at: str = Field(min_length=1)
    worker_role: DeliveryWorkerRole
    task_id: str | None = None


class DeliveryOperatorRecoveryAttention(_ApplicationModel):
    """Recovery evidence without workspace or Git custody internals."""

    attempt_id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    custody_retained: bool
    retry_condition: str = Field(min_length=1)


class DeliveryOperatorIntegrationAttention(_ApplicationModel):
    """Integration attention without raw Git boundary identities."""

    code: DeliveryIntegrationAttentionCode
    disposition: DeliveryIntegrationAttentionDisposition
    diagnostics: tuple[str, ...] = Field(min_length=1)
    retry_condition: str = Field(min_length=1)


class DeliveryOperatorContext(_ApplicationModel):
    """Current bounded state consumed by user-owned Delivery controls."""

    change_id: str = Field(min_length=1)
    outcome_id: str = Field(min_length=1)
    stage: DeliveryStage
    block: DeliveryBlock | None = None
    requests: tuple[DeliveryRequest, ...] = ()
    active_claim: DeliveryOperatorClaim | None = None
    return_context: DeliveryReturnContext | None = None
    recovery_attention: DeliveryOperatorRecoveryAttention | None = None
    integration_attention: DeliveryOperatorIntegrationAttention | None = None


class DeliveryIntegrationRepairRecoveryResult(_ApplicationModel):
    """Recovered exact Integration repair claim and preserved commit evidence."""

    status: Literal[DeliveryClaimRecoveryStatus.RECOVERED] = DeliveryClaimRecoveryStatus.RECOVERED
    change_id: str = Field(min_length=1)
    attempt_id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)
    preserved_commit: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")


class DeliveryTargetSyncRepairReceipt(_ApplicationModel):
    """Evidence that one target-sync head and its portable state were reconciled."""

    schema_version: Literal[1] = 1
    receipt_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    operation_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
    change_id: str = Field(min_length=1)
    target_sync_operation_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
    target_branch: str = Field(min_length=1)
    target_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    expected_remote_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    repaired_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    review_required: Literal[True] = True

    @classmethod
    def create(  # noqa: PLR0913 - receipt identity binds each exact repair input.
        cls,
        *,
        operation_id: str,
        change_id: str,
        target_sync_operation_id: str,
        target_branch: str,
        target_head: str,
        expected_remote_head: str,
        repaired_head: str,
    ) -> DeliveryTargetSyncRepairReceipt:
        """Create deterministic evidence for one target-sync publication repair."""
        values = {
            "operation_id": operation_id,
            "change_id": change_id,
            "target_sync_operation_id": target_sync_operation_id,
            "target_branch": target_branch,
            "target_head": target_head,
            "expected_remote_head": expected_remote_head,
            "repaired_head": repaired_head,
            "review_required": True,
        }
        candidate = cls.model_construct(receipt_id="0" * 64, schema_version=1, **values)
        payload = candidate.model_dump(mode="json", exclude={"receipt_id"})
        receipt_id = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        return cls(receipt_id=receipt_id, **values)

    @model_validator(mode="after")
    def _validate_identity(self) -> DeliveryTargetSyncRepairReceipt:
        payload = self.model_dump(mode="json", exclude={"receipt_id"})
        expected = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        if self.receipt_id != expected:
            message = "target-sync publication repair identity is invalid"
            raise ValueError(message)
        return self


class DeliveryStateSnapshotRepairReceipt(_ApplicationModel):
    """Evidence that one quarantined local frontier successor was published."""

    schema_version: Literal[1] = 1
    receipt_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    operation_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
    change_id: str = Field(min_length=1)
    snapshot_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    published_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    local_frontier_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def create(
        cls,
        *,
        operation_id: str,
        change_id: str,
        publication: DeliveryStatePublicationReceipt,
        local_frontier_digest: str,
    ) -> DeliveryStateSnapshotRepairReceipt:
        """Create deterministic evidence for one local frontier repair."""
        values = {
            "operation_id": operation_id,
            "change_id": change_id,
            "snapshot_id": publication.snapshot_id,
            "published_head": publication.published_head,
            "local_frontier_digest": local_frontier_digest,
        }
        candidate = cls.model_construct(receipt_id="0" * 64, schema_version=1, **values)
        payload = candidate.model_dump(mode="json", exclude={"receipt_id"})
        receipt_id = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        return cls(receipt_id=receipt_id, **values)

    @model_validator(mode="after")
    def _validate_identity(self) -> DeliveryStateSnapshotRepairReceipt:
        payload = self.model_dump(mode="json", exclude={"receipt_id"})
        expected = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        if self.receipt_id != expected:
            message = "Delivery-state snapshot repair identity is invalid"
            raise ValueError(message)
        return self


class DeliveryStrandedFrontierRepairReceipt(_ApplicationModel):
    """Evidence that one confirmed legacy request-provenance defect was repaired."""

    schema_version: Literal[1] = 1
    receipt_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    operation_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
    change_id: str = Field(min_length=1)
    request_id: str = Field(min_length=1)
    previous_frontier_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    frontier_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    preserved_frontier_path: str = Field(min_length=1)

    @classmethod
    def create(  # noqa: PLR0913 - receipt identity binds each exact repair input.
        cls,
        *,
        operation_id: str,
        change_id: str,
        request_id: str,
        previous_frontier_digest: str,
        frontier_digest: str,
        preserved_frontier_path: str,
    ) -> DeliveryStrandedFrontierRepairReceipt:
        """Create deterministic evidence for one frontier repair."""
        values = {
            "operation_id": operation_id,
            "change_id": change_id,
            "request_id": request_id,
            "previous_frontier_digest": previous_frontier_digest,
            "frontier_digest": frontier_digest,
            "preserved_frontier_path": preserved_frontier_path,
        }
        candidate = cls.model_construct(receipt_id="0" * 64, schema_version=1, **values)
        payload = candidate.model_dump(mode="json", exclude={"receipt_id"})
        receipt_id = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        return cls(receipt_id=receipt_id, **values)

    @model_validator(mode="after")
    def _validate_identity(self) -> DeliveryStrandedFrontierRepairReceipt:
        payload = self.model_dump(mode="json", exclude={"receipt_id"})
        expected = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        if self.receipt_id != expected:
            message = "stranded frontier repair identity is invalid"
            raise ValueError(message)
        return self


class DeliveryQuarantinedSnapshotRepairReceipt(_ApplicationModel):
    """Evidence that one quarantined remote snapshot was replaced under CAS."""

    schema_version: Literal[1] = 1
    receipt_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    operation_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
    change_id: str = Field(min_length=1)
    invalid_snapshot_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_remote_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    snapshot_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    published_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    diagnostic_code: Literal["snapshot-invalid", "snapshot-identity-invalid"]

    @classmethod
    def create(  # noqa: PLR0913 - receipt identity binds each exact repair input.
        cls,
        *,
        operation_id: str,
        change_id: str,
        invalid_snapshot_digest: str,
        expected_remote_head: str,
        publication: DeliveryStatePublicationReceipt,
        diagnostic_code: Literal["snapshot-invalid", "snapshot-identity-invalid"],
    ) -> DeliveryQuarantinedSnapshotRepairReceipt:
        """Create deterministic evidence for one remote snapshot repair."""
        values = {
            "operation_id": operation_id,
            "change_id": change_id,
            "invalid_snapshot_digest": invalid_snapshot_digest,
            "expected_remote_head": expected_remote_head,
            "snapshot_id": publication.snapshot_id,
            "published_head": publication.published_head,
            "diagnostic_code": diagnostic_code,
        }
        candidate = cls.model_construct(receipt_id="0" * 64, schema_version=1, **values)
        payload = candidate.model_dump(mode="json", exclude={"receipt_id"})
        receipt_id = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        return cls(receipt_id=receipt_id, **values)

    @model_validator(mode="after")
    def _validate_identity(self) -> DeliveryQuarantinedSnapshotRepairReceipt:
        payload = self.model_dump(mode="json", exclude={"receipt_id"})
        expected = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        if self.receipt_id != expected:
            message = "quarantined snapshot repair identity is invalid"
            raise ValueError(message)
        return self


class DeliveryQuarantinedSnapshotRepairProposal(_ApplicationModel):
    """Typed confirmation boundary for one known invalid remote snapshot."""

    change_id: str = Field(min_length=1)
    diagnostic_code: Literal["snapshot-invalid", "snapshot-identity-invalid"]
    expected_remote_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    snapshot_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    requires_confirmation: Literal[True] = True
    consequence: str = Field(min_length=1)


class PortfolioApplicationError(RuntimeError):
    """Portfolio preparation or scoped context validation failed closed."""

    code = "ERR_DELIVERY_PORTFOLIO"


class DeliveryCapacityWaitingError(DeliveryRuntimeConflictError):
    """Selected work can be retried when shared execution capacity is available."""

    code = "ERR_DELIVERY_CAPACITY_WAITING"


class DeliveryActionBusyError(DeliveryRuntimeConflictError):
    """A selected Change is temporarily locked by another operation."""

    code = "ERR_DELIVERY_ACTION_BUSY"


class DeliveryRuntimeReconciliationError(DeliveryRuntimeConflictError):
    """A runtime map entry changed or became unreadable during a read-side reconciliation."""

    code = "ERR_DELIVERY_RUNTIME_RECONCILIATION"
    retry_safe = True

    def __init__(self, change_id: str | None, detail: str) -> None:
        self.change_id = change_id
        target = f" for {change_id}" if change_id is not None else ""
        super().__init__(f"Delivery runtime reconciliation is required{target}: {detail}")


class RequiredPublicationChecksFailedError(PortfolioApplicationError):
    """A ready transition retained attention for failing provider-required checks."""

    code = "ERR_DELIVERY_REQUIRED_CHECKS_FAILED"

    def __init__(self, *, exact_head: str, observation_id: str, disposition_id: str) -> None:
        self.exact_head = exact_head
        self.observation_id = observation_id
        self.disposition_id = disposition_id
        super().__init__(
            f"required publication checks failed for exact head {exact_head}; "
            f"attention {disposition_id} retained from observation {observation_id}"
        )


class PortfolioReadView(_ApplicationModel):
    """Grouped work and operating facts derived from one portfolio capture."""

    groups: tuple[ChangeGroupView, ...]
    operating: PortfolioOperatingView
    health: DeliveryHealthView = DeliveryHealthView(status=DeliveryHealthStatus.HEALTHY)
    unavailable_changes: tuple[DeliveryUnavailableChangeView, ...] = ()


class DeliveryCheckpointReconciliationResult(_ApplicationModel):
    """One deterministic checkpoint reconciliation attempt and remaining queue state."""

    change_id: str = Field(min_length=1)
    attempted_head: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    branch_publication: ChangeBranchPublicationReceipt | None = None
    draft_pull_request: DraftPullRequestPublicationReceipt | None = None
    generated_summary: GeneratedPullRequestSummaryReceipt | None = None
    state: DeliveryCheckpointPublicationState
    reconciled: bool
    error_code: str | None = Field(default=None, min_length=1)
    error_detail: str | None = Field(default=None, min_length=1)


class ExecuteDeliveryChangeAction(_ApplicationModel):
    """Invoke only the engine-owned operation already selected for this Change."""

    change_id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    operation_id: str = Field(pattern=r"^continue-[0-9a-f]{64}$")


class DeliveryEngineActionResult(_ApplicationModel):
    """Exact retained owner result; blocked effects never release custody."""

    action: ChangeContinuationAction
    kind: Literal["completed", "waiting", "stale", "blocked"]
    reason_code: Literal[
        "engine-action-completed",
        "engine-action-incomplete",
        "engine-action-failed",
        "engine-action-interrupted",
        "readiness-changed",
        "merge-approval-required",
    ]
    failure: DeliveryAcquisitionFailure | None = None
    checkpoint: DeliveryCheckpointReconciliationResult | None = None
    checkpoint_snapshot: ChangeDesignPackageSnapshotReceipt | None = None
    target_sync: ChangeTargetSyncReceipt | None = None
    ready: PullRequestReadyReceipt | None = None
    acceptance: CompletionReceipt | None = None

    @model_validator(mode="after")
    def _validate_owner_result(self) -> DeliveryEngineActionResult:
        if self.action.finished_at is not None:
            message = "engine result must bind the original acquired action"
            raise ValueError(message)
        kinds = {
            "engine-action-completed": "completed",
            "engine-action-incomplete": "blocked",
            "engine-action-failed": "blocked",
            "engine-action-interrupted": "blocked",
            "readiness-changed": "stale",
            "merge-approval-required": "waiting",
        }
        if self.kind != kinds[self.reason_code]:
            message = "engine disposition must match its reason"
            raise ValueError(message)
        receipts = {
            "reconcile-checkpoint": self.checkpoint,
            "sync-target": self.target_sync,
            "mark-ready": self.ready,
            "observe-acceptance": self.acceptance,
        }
        if any(value is not None and key != self.action.kind for key, value in receipts.items()):
            message = "engine result must match its fixed owner"
            raise ValueError(message)
        receipt = receipts[self.action.kind]
        if self.kind == "completed" and (receipt is None or (self.checkpoint and not self.checkpoint.reconciled)):
            message = "completed engine action requires a successful exact owner receipt"
            raise ValueError(message)
        if receipt is not None and receipt.change_id != self.action.change_id:
            message = "engine receipt must match the selected Change"
            raise ValueError(message)
        if self.kind == "waiting" and self.action.kind != "observe-acceptance":
            message = "only acceptance observation can wait for merge approval"
            raise ValueError(message)
        if self.kind in {"waiting", "stale"} and receipt is not None:
            message = "unexecuted engine action cannot carry a successful receipt"
            raise ValueError(message)
        if self.reason_code == "engine-action-incomplete" and (self.checkpoint is None or self.checkpoint.reconciled):
            message = "incomplete engine action requires its pending checkpoint evidence"
            raise ValueError(message)
        self._validate_failure()
        self._validate_exact_receipts()
        return self

    def _validate_failure(self) -> None:
        if self.failure is not None and (
            self.kind != "blocked"
            or self.failure.change_id != self.action.change_id
            or self.failure.attempt_id != self.action.operation_id
        ):
            message = "engine failure must retain the blocked Change identity"
            raise ValueError(message)
        if self.reason_code in {"engine-action-failed", "engine-action-interrupted"} and self.failure is None:
            message = "failed engine action requires its retained failure"
            raise ValueError(message)

    def _validate_exact_receipts(self) -> None:
        self._validate_checkpoint_receipt()
        if self.target_sync is not None and (
            self.target_sync.operation_id != self.action.operation_id
            or self.target_sync.expected_target != self.action.target_head
            or self.target_sync.change_head_before != self.action.exact_head
        ):
            message = "target sync result differs from the exact action"
            raise ValueError(message)
        if self.ready is not None and (
            self.ready.operation_id != self.action.operation_id
            or self.ready.head_sha != self.action.exact_head
            or self.ready.finalization_id != self.action.finalization_id
        ):
            message = "ready result differs from the exact action"
            raise ValueError(message)
        if self.acceptance is not None and (
            self.acceptance.finalized_change_head != self.action.exact_head
            or self.acceptance.finalization_receipt_id != self.action.finalization_id
        ):
            message = "acceptance result differs from the exact action"
            raise ValueError(message)

    def _validate_checkpoint_receipt(self) -> None:
        head = self.action.exact_head
        snapshot = self.checkpoint_snapshot
        if snapshot is not None:
            if self.checkpoint is None or snapshot.change_id != self.action.change_id or snapshot.previous_head != head:
                message = "checkpoint snapshot differs from the exact action"
                raise ValueError(message)
            head = snapshot.snapshot_head
        checkpoint = self.checkpoint
        if checkpoint is None:
            return
        if checkpoint.attempted_head not in {None, head}:
            message = "checkpoint result differs from the exact action"
            raise ValueError(message)
        if self.kind == "completed" and (
            checkpoint.state.published_head != head
            or checkpoint.state.change_id != self.action.change_id
            or checkpoint.state.pending_checkpoint is not None
            or checkpoint.branch_publication is None
            or checkpoint.generated_summary is None
            or checkpoint.branch_publication.published_head != head
            or checkpoint.generated_summary.head_sha != head
            or checkpoint.branch_publication.change_id != self.action.change_id
            or checkpoint.generated_summary.change_id != self.action.change_id
            or (
                checkpoint.draft_pull_request is not None
                and (
                    checkpoint.draft_pull_request.head_sha != head
                    or checkpoint.draft_pull_request.change_id != self.action.change_id
                )
            )
        ):
            message = "checkpoint result differs from the exact action or lacks observed publication receipts"
            raise ValueError(message)


class DeliveryAcceptanceReconciliationStatus(StrEnum):
    """Bounded outcome of one provider acceptance reconciliation attempt."""

    COMPLETED = "completed"
    WAITING = "waiting"
    HEAD_MOVED = "head-moved"
    ATTENTION = "attention"
    PROVIDER_UNAVAILABLE = "provider-unavailable"
    SKIPPED = "skipped"


class DeliveryAcceptanceReconciliationOutcome(_ApplicationModel):
    """Per-Change result that keeps a polling batch isolated."""

    change_id: str = Field(min_length=1)
    status: DeliveryAcceptanceReconciliationStatus
    code: str | None = Field(default=None, min_length=1)
    detail: str | None = Field(default=None, min_length=1)
    completion_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


class _AcceptanceReconciliationCursor(_ApplicationModel):
    """Persisted next starting Change for bounded acceptance polling."""

    schema_version: Literal[1] = 1
    next_change_id: str | None = Field(default=None, min_length=1)


class DeliveryChangePublicationSupersessionReceipt(_ApplicationModel):
    """Bind one Git successor publication to its provider and runtime evidence."""

    schema_version: Literal[1] = 1
    receipt_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    operation_id: str = Field(min_length=1)
    change_id: str = Field(min_length=1)
    predecessor_publication_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    successor_publication_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    git_supersession: ChangeBranchSupersessionReceipt
    provider_supersession: DraftPullRequestSupersessionReceipt
    publication_history: DeliveryChangePublicationHistory

    @classmethod
    def create(
        cls,
        *,
        operation_id: str,
        predecessor_publication_id: str,
        git_supersession: ChangeBranchSupersessionReceipt,
        provider_supersession: DraftPullRequestSupersessionReceipt,
        publication_history: DeliveryChangePublicationHistory,
    ) -> DeliveryChangePublicationSupersessionReceipt:
        """Create one content-addressed application supersession receipt."""
        change_id = provider_supersession.change_id
        payload = {
            "schema_version": 1,
            "operation_id": operation_id,
            "change_id": change_id,
            "predecessor_publication_id": predecessor_publication_id,
            "successor_publication_id": provider_supersession.successor_receipt_id,
            "git_supersession": git_supersession,
            "provider_supersession": provider_supersession,
            "publication_history": publication_history,
        }
        candidate = cls.model_construct(receipt_id="0" * 64, **payload)
        digest = hashlib.sha256(
            json.dumps(
                candidate.model_dump(mode="json", exclude={"receipt_id"}),
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
        return cls(receipt_id=digest, **payload)

    @model_validator(mode="after")
    def _validate_binding(self) -> DeliveryChangePublicationSupersessionReceipt:
        git = self.git_supersession
        provider = self.provider_supersession
        if (
            git.operation_id != self.operation_id
            or git.change_id != self.change_id
            or provider.operation_id != self.operation_id
            or provider.change_id != self.change_id
            or provider.predecessor_receipt_id != self.predecessor_publication_id
            or provider.successor_receipt_id != self.successor_publication_id
            or git.predecessor_branch != provider.predecessor_branch
            or git.predecessor_head != provider.predecessor_head
            or git.successor_branch != provider.successor_branch
            or git.superseding_head != provider.superseding_head
        ):
            message = "publication supersession receipts do not share one exact successor"
            raise ValueError(message)
        if self.publication_history.current != _publication_identity(provider.successor_publication):
            message = "publication supersession history does not end at the provider successor"
            raise ValueError(message)
        payload = self.model_dump(mode="json", exclude={"receipt_id"})
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        if self.receipt_id != digest:
            message = "publication supersession receipt identity is invalid"
            raise ValueError(message)
        return self


class PortfolioApplicationConfig(_ApplicationModel):
    """Configured capacity, claim timeout, source root, and stage-role policy."""

    package_root: Path
    execution_capacity: int = Field(gt=0)
    claim_timeout_seconds: int = Field(default=60 * 60, gt=0)
    role_policies: tuple[DeliveryRolePolicy, ...] = Field(min_length=2, max_length=2)

    @model_validator(mode="after")
    def _validate_roles(self) -> PortfolioApplicationConfig:
        roles = tuple(policy.worker_role for policy in self.role_policies)
        expected = {DeliveryWorkerRole.PLANNER, DeliveryWorkerRole.BUILDER}
        if set(roles) != expected or len(roles) != len(set(roles)):
            message = "role policy must define each live worker role once"
            raise ValueError(message)
        return self


@dataclass(frozen=True)
class PortfolioApplicationDependencies:
    """Existing state owners composed by the portfolio application service."""

    target_root: Path
    package_store: DesignPackageStore
    authority_registry: DeliveryAuthorityRegistry
    coordinator: PortfolioCoordinator
    workspace_manager: ChangeWorkspaceManager
    completed_history_catalog: CompletedHistoryCatalog | None = None
    delivery_state_publisher: DeliveryStatePublisher | None = None
    change_branch_publisher: ChangeBranchPublisher | None = None
    draft_pull_request_publisher: DraftPullRequestPublisher | None = None
    health_diagnostics: tuple[DeliveryHealthDiagnostic, ...] = ()
    recovery_evidence_provider: RecoveryEvidenceProvider = field(default_factory=UnavailableRecoveryEvidenceProvider)


@dataclass(frozen=True)
class PortfolioApplicationHooks:
    """Nondeterministic identity and clock sources replaced only below public proof."""

    identity_factory: Callable[[], str]
    clock: Callable[[], str]


@dataclass(frozen=True)
class _Candidate:
    sort_key: tuple[int, int, int, str]
    change_id: str
    runtime: DeliveryRuntime
    binding: OutcomeAuthorityBinding
    task_id: str | None
    role: DeliveryWorkerRole


@dataclass(frozen=True)
class _PreparedSource:
    package: VerifiedDesignPackage
    coordination: ChangeCoordination
    source_head: str


@dataclass(frozen=True)
class _PreparedCheckpointHead:
    state: DeliveryCheckpointPublicationState
    pending: DeliveryPendingCheckpoint
    head: str
    first_checkpoint: bool
    finalization_invalidated: bool = False


@dataclass(frozen=True)
class _SupersessionPublishContext:
    change_id: str
    expected_publication_id: str
    operation_id: str
    predecessor: DraftPullRequestPublicationReceipt
    superseding_head: str
    target_branch: str


@dataclass(frozen=True)
class _AcceptanceReconciliationAuthority:
    exact_head: str
    ready: PullRequestReadyReceipt
    target_branch: str


@dataclass(frozen=True)
class _ReviewRepairAuthority:
    invalidation: DeliveryFinalizationInvalidationReceipt | None
    expected_finalization_id: str
    expected_head: str
    repository: str
    number: int
    node_id: str


class PortfolioApplication:
    """Compose Delivery runtimes, source packages, and warm workspace custody."""

    def __init__(
        self,
        runtimes: Mapping[str, DeliveryRuntime],
        dependencies: PortfolioApplicationDependencies,
        config: PortfolioApplicationConfig,
        hooks: PortfolioApplicationHooks | None = None,
    ) -> None:
        if set(runtimes) != {runtime.contract.change_id for runtime in runtimes.values()}:
            message = "runtime mapping keys must match admitted change identities"
            raise ValueError(message)
        self._runtime_reconciliation_lock = Lock()
        self._runtimes = dict(runtimes)
        self._discovered_changes: dict[str, DeliveryChangeObservation] = {}
        self._runtime_reconciliation_errors: dict[str, str] = {}
        self._runtime_snapshots: dict[str, DeliveryPortfolioSnapshot] = {}
        self._publication_observation_cache: dict[
            str,
            tuple[float, str, PublicationPullRequestObservationReceipt | None],
        ] = {}
        self._acceptance_reconciliation_cursor: str | None = None
        self._has_reconciled_runtimes = False
        self._target_root = dependencies.target_root.resolve()
        self._package_store = dependencies.package_store
        self._authority_registry = dependencies.authority_registry
        self._package_root = config.package_root.resolve()
        self._coordinator = dependencies.coordinator
        self._workspace_manager = dependencies.workspace_manager
        self._completed_history_catalog = dependencies.completed_history_catalog
        self._delivery_state_publisher = dependencies.delivery_state_publisher
        self._change_branch_publisher = dependencies.change_branch_publisher
        self._draft_pull_request_publisher = dependencies.draft_pull_request_publisher
        self._startup_health_diagnostics = dependencies.health_diagnostics
        self._recovery_evidence_provider = dependencies.recovery_evidence_provider
        self._execution_capacity = config.execution_capacity
        self._claim_timeout = timedelta(seconds=config.claim_timeout_seconds)
        self._policies = {policy.worker_role: policy for policy in config.role_policies}
        self._identity_factory = hooks.identity_factory if hooks else lambda: str(uuid.uuid4())
        self._clock = (
            hooks.clock
            if hooks
            else lambda: datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        )
        for runtime in self._runtimes.values():
            try:
                with locked_roots((self._checkpoint_lock_root(runtime.contract.change_id),), blocking=False):
                    self._reconcile_retry_results(runtime)
            except (OSError, RuntimeError, ValueError):
                _logger.warning("Retry accounting remains contained for %s", runtime.contract.change_id)

    def _reconcile_retry_results(self, runtime: DeliveryRuntime) -> None:
        """Replay accounting only from owner receipts; absent evidence keeps reservations."""
        self._import_legacy_worker_budgets(runtime)
        ledger = runtime.retry_ledger(clock=self._clock)
        ledger.reconcile_owner_results()
        finalization = runtime.finalization()
        for attempt in ledger.pending_attempts():
            if attempt.key.outcome_id is not None:
                self._reconcile_worker_retry_receipt(runtime, ledger, attempt)
            elif (
                attempt.key.action_kind == "finalize"
                and finalization is not None
                and finalization.operation_id == attempt.attempt_id
                and finalization.exact_head == attempt.key.exact_head
            ):
                ledger.record_accepted_progress(attempt.attempt_id, now=finalization.finalized_at)
            elif attempt.attempt_id.startswith("continue-"):
                result = self._read_engine_result(
                    ExecuteDeliveryChangeAction(change_id=runtime.contract.change_id, operation_id=attempt.attempt_id)
                )
                if result is not None:
                    self._record_engine_attempt_result(result.action, result)
        reports = FinalizationReportStore(self._target_root, runtime.contract.change_id).read()
        for report in reports.reports:
            if any(report.request.attempt_key in episode.attempt_ids for episode in ledger.read().episodes):
                ledger.record_failure(
                    report.request.attempt_key, failure_code=report.request.code.value, now=report.observed_at
                )

    def _reconcile_worker_retry_receipt(
        self, runtime: DeliveryRuntime, ledger: RetryLedger, attempt: RetryAttempt
    ) -> None:
        """Recognize an original Builder receipt written before owner-result companions."""
        if attempt.operation_alias is None:
            return
        binding = runtime.show_binding(attempt.key.outcome_id)
        for result in binding.results:
            try:
                runtime.require_result_replay(binding.outcome_id, attempt.operation_alias, result)
            except (DeliveryRuntimeConflictError, DeliveryRuntimeReferenceError):
                continue
            ledger.record_accepted_progress(attempt.attempt_id, now=self._clock())
            return

    def _import_legacy_worker_budgets(self, runtime: DeliveryRuntime) -> None:
        """Preserve historical failures before a mutation can clear binding metadata."""
        for binding in runtime.bindings():
            if not binding.retry_count or binding.stage not in {DeliveryStage.PLANNING, DeliveryStage.IMPLEMENTATION}:
                continue
            role = (
                DeliveryWorkerRole.BUILDER
                if binding.stage is DeliveryStage.IMPLEMENTATION
                else DeliveryWorkerRole.PLANNER
            )
            completed = {result.task_id for result in binding.results}
            task_id = (
                binding.active_task_id
                or next(
                    (
                        task.task_id
                        for task in binding.tasks
                        if task.task_id not in completed and set(task.dependency_ids) <= completed
                    ),
                    None,
                )
                if role is DeliveryWorkerRole.BUILDER
                else None
            )
            change_id = runtime.contract.change_id
            candidate = _Candidate((0, 0, 0, change_id), change_id, runtime, binding, task_id, role)
            key = self._worker_retry_key(candidate, self._workspace_manager.show(change_id).last_reviewed_commit)
            claim = binding.active_claim
            runtime.retry_ledger(clock=self._clock).import_legacy_failures(
                key,
                binding.retry_count,
                now=self._clock(),
                existing_attempt=(claim.attempt_id, claim.claim_id) if claim is not None else None,
            )

    def create_design_session(
        self,
        change_id: str,
        intent_bytes: bytes,
        design_bytes: bytes,
    ) -> DesignPackageResult:
        """Create or replay one exact authored Design package."""
        return self._package_store.create(change_id, intent_bytes, design_bytes)

    def put_design(self, design: DeliveryDesignPut) -> DesignPackageResult:
        """Create or CAS-revise one exact authored Design package."""
        if design.expected_package_id is None:
            return self._package_store.create(design.change_id, design.intent_bytes, design.design_bytes)
        revised = self.revise_design_session(
            design.change_id,
            design.expected_package_id,
            design.intent_bytes,
            design.design_bytes,
        )
        return DesignPackageResult(
            change_id=revised.change_id,
            package_id=revised.package_id,
            package_root=self._package_root / design.change_id,
            manifest=revised.manifest,
            replayed=False,
        )

    def observe_change_publication_checks(
        self,
        change_id: str,
    ) -> PublicationCheckObservationReceipt:
        """Observe provider checks at the exact durable published Change head."""
        if self._draft_pull_request_publisher is None:
            message = "draft pull-request publication is not configured"
            raise PortfolioApplicationError(message)
        published_head = self._runtime(change_id).checkpoint_publication_state().published_head
        if published_head is None:
            message = "Change has no reconciled checkpoint publication"
            raise PortfolioApplicationError(message)
        return self._draft_pull_request_publisher.observe_checks(
            ObserveChangePublicationChecks(change_id=change_id, published_head=published_head)
        )

    def sync_change_with_target(
        self,
        change_id: str,
        expected_target: str,
        operation_id: str,
    ) -> ChangeTargetSyncReceipt:
        """Fetch and merge one exact target head through the managed Change worktree."""
        runtime = self._runtime(change_id, for_mutation=True)
        request = SyncChangeWithTarget(
            change_id=change_id,
            expected_target=expected_target,
            operation_id=operation_id,
        )
        with self._engine_checkpoint_lock(change_id):
            self._require_target_sync_change_mutable(runtime)
            self._require_no_review_repair(runtime, "target synchronization")
            if runtime.change_disposition() is not None:
                self._fail("target synchronization requires Change attention resolution first")
            if runtime.active_claims() or runtime.integration_repair_claim() is not None:
                self._fail("target synchronization cannot overlap an active Delivery claim")
            try:
                receipt = self._workspace_manager.sync_with_target(
                    request,
                    before_head_change=lambda: self._return_publication_to_draft_before_head_change(
                        change_id,
                        runtime,
                        operation_id,
                    ),
                )
            except ChangeTargetSyncStaleError:
                raise
            except ChangeTargetSyncConflictError as exc:
                history = runtime.publication_history()
                runtime.capture_target_sync_conflict(
                    exc.operation_id,
                    exc.target_head,
                    _timestamp(self._clock()),
                    (
                        "target synchronization merge conflict",
                        *tuple(f"conflict-path:{path}" for path in exc.conflict_paths),
                    ),
                    publication_identity=history.current if history is not None else None,
                )
                self._publish_attention_best_effort(
                    change_id,
                    runtime,
                    f"target-sync-attention-{exc.operation_id}",
                )
                raise
            except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as exc:
                self._fail("target synchronization could not be completed", exc)
            runtime.record_target_sync(receipt, _timestamp(self._clock()))
            self._publish_target_sync_branch(change_id, runtime, receipt.merged_head)
            self._publish_delivery_state(change_id, runtime, f"target-sync-{receipt.receipt_id}")
            self._acknowledge_published_target_sync_checkpoint(runtime, receipt.merged_head)
            return receipt

    def sync_change_with_current_target(
        self,
        change_id: str,
        operation_id: str,
    ) -> ChangeTargetSyncReceipt:
        """Bind the current remote-tracking target and perform one exact sync operation."""
        try:
            expected_target = self._workspace_manager.integration_context(change_id).target_head
        except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as exc:
            self._fail("target synchronization target head is unavailable", exc)
        return self.sync_change_with_target(change_id, expected_target, operation_id)

    def adopt_external_head(
        self,
        change_id: str,
        expected_head: str,
        adopted_head: str,
        operation_id: str,
    ) -> ChangeExternalHeadAdoptionReceipt:
        """Adopt one exact remote Change descendant through managed workspace custody."""
        runtime = self._runtime(change_id, for_mutation=True)
        request = AdoptExternalHead(
            change_id=change_id,
            expected_head=expected_head,
            adopted_head=adopted_head,
            operation_id=operation_id,
        )
        with locked_roots((self._checkpoint_lock_root(change_id),)):
            self._require_external_head_adoption_change_mutable(runtime)
            self._require_no_review_repair(runtime, "external Change head adoption")
            if runtime.change_disposition() is not None:
                self._fail("external Change head adoption requires Change attention resolution first")
            if runtime.active_claims() or runtime.integration_repair_claim() is not None:
                self._fail("external Change head adoption cannot overlap an active Delivery claim")
            publication_identity = runtime.change_disposition_publication()
            if publication_identity is None:
                ready = runtime.ready_receipt()
                if ready is not None:
                    publication_identity = DeliveryChangePublicationIdentity(
                        change_id=ready.change_id,
                        repository=ready.repository,
                        number=ready.number,
                        node_id=ready.node_id,
                        head_sha=ready.head_sha,
                    )
            demoted = False

            def demote_before_head_change() -> None:
                nonlocal demoted
                self._return_publication_to_draft_before_head_change(
                    change_id,
                    runtime,
                    operation_id,
                )
                demoted = True

            try:
                receipt = self._workspace_manager.adopt_external_head(
                    request,
                    before_head_change=demote_before_head_change,
                )
            except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as exc:
                if demoted:
                    with suppress(DeliveryRuntimeConflictError):
                        runtime.capture_publication_attention(
                            _timestamp(self._clock()),
                            (
                                "external-head-adoption-movement-failed",
                                f"external-head-adoption-operation:{operation_id}",
                                f"expected-head:{expected_head}",
                                f"adopted-head:{adopted_head}",
                            ),
                            publication_identity=publication_identity,
                        )
                        self._publish_attention_best_effort(
                            change_id,
                            runtime,
                            f"adoption-attention-{operation_id}",
                        )
                self._fail("external Change head could not be adopted", exc)
            runtime.record_external_head_adoption(receipt, _timestamp(self._clock()))
            self._publish_delivery_state(change_id, runtime, f"adoption-{receipt.receipt_id}")
            return receipt

    def adopt_external_head_after_acceptance_attention(
        self,
        change_id: str,
        expected_disposition_id: str,
        expected_head: str,
        adopted_head: str,
        operation_id: str,
    ) -> ChangeExternalHeadAdoptionReceipt:
        """Adopt one moved open PR head after exact acceptance-attention validation."""
        publisher = self._draft_pull_request_publisher
        if publisher is None:
            self._fail("acceptance head adoption requires a publication provider")
        runtime = self._runtime(change_id, for_mutation=True)
        request = AdoptExternalHead(
            change_id=change_id,
            expected_head=expected_head,
            adopted_head=adopted_head,
            operation_id=operation_id,
        )
        with locked_roots((self._checkpoint_lock_root(change_id),)):
            disposition = runtime.change_disposition()
            if (
                disposition is None
                or disposition.disposition_id != expected_disposition_id
                or disposition.kind != DeliveryChangeDispositionKind.ACCEPTANCE_ATTENTION
                or disposition.acceptance_reason != DeliveryAcceptanceAttentionReason.HEAD_MOVED
            ):
                self._fail("acceptance head adoption requires matching head-moved attention")
            publication = runtime.change_disposition_publication()
            if publication is None or publication.head_sha != adopted_head:
                self._fail("acceptance head adoption does not match observed pull-request authority")
            coordination = self._workspace_manager.show(change_id)
            if coordination.last_reviewed_commit != expected_head:
                self._fail("acceptance head adoption expected head differs from the reviewed boundary")
            if runtime.active_claims() or runtime.integration_repair_claim() is not None:
                self._fail("acceptance head adoption cannot overlap an active Delivery claim")
            observation = publisher.observe_pull_request(ObserveChangePublicationPullRequest(change_id=change_id))
            if observation is None or observation.snapshot.state != "open" or observation.snapshot.merged:
                self._fail("acceptance head adoption requires an open unmerged pull request")
            if observation.snapshot.head_sha != adopted_head:
                self._fail("acceptance head adoption pull-request head changed")
            try:
                receipt = self._workspace_manager.adopt_external_head(
                    request,
                    before_head_change=lambda: self._return_publication_to_draft_before_head_change(
                        change_id,
                        runtime,
                        operation_id,
                        finalization_id=(
                            runtime.finalization_invalidation().finalization_id
                            if runtime.finalization_invalidation() is not None
                            else None
                        ),
                    ),
                )
            except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as exc:
                self._fail("external Change head could not be adopted", exc)
            resolved_at = _timestamp(self._clock())
            runtime.resolve_change_disposition(expected_disposition_id, resolved_at)
            runtime.record_external_head_adoption(receipt, resolved_at)
            self._publish_delivery_state(change_id, runtime, f"adoption-{receipt.receipt_id}")
            return receipt

    def promote_external_head(
        self,
        change_id: str,
        expected_head: str,
        operation_id: str,
    ) -> ChangeExternalHeadPromotionReceipt:
        """Promote one exact adopted head before granting Builder authority."""
        runtime = self._runtime(change_id, for_mutation=True)
        with locked_roots((self._checkpoint_lock_root(change_id),)):
            self._require_external_head_promotion_change_mutable(runtime)
            self._require_no_review_repair(runtime, "external Change head promotion")
            if runtime.change_disposition() is not None:
                self._fail("external Change-head promotion requires Change attention resolution first")
            if runtime.active_claims() or runtime.integration_repair_claim() is not None:
                self._fail("external Change-head promotion cannot overlap an active Delivery claim")
            request = PromoteExternalHead(
                change_id=change_id,
                expected_head=expected_head,
                operation_id=operation_id,
            )
            coordination = self._workspace_manager.show(change_id)
            promotion = coordination.external_head_promotion_receipt
            runtime_promotion = runtime.external_head_promotion_receipt()
            if promotion != runtime_promotion and (
                promotion is None or promotion.operation_id != operation_id or promotion.promoted_head != expected_head
            ):
                self._fail("external Change-head promotion requires reconciled promotion evidence")
            adoption = coordination.external_head_adoption_receipt
            if adoption is None or runtime.external_head_adoption_receipt() != adoption:
                self._fail("external Change-head promotion requires reconciled adoption evidence")
            try:
                promoted = self._workspace_manager.promote_external_head(request)
            except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as exc:
                self._fail("external Change head could not be promoted", exc)
            if promoted is None:
                self._fail("external Change-head promotion has no adopted head to promote")
            runtime.record_external_head_promotion(promoted, _timestamp(self._clock()))
            self._publish_delivery_state(change_id, runtime, f"promotion-{promoted.receipt_id}")
            return promoted

    def abort_target_sync_conflict(
        self,
        change_id: str,
        expected_disposition_id: str,
        target_head: str,
        operation_id: str,
    ) -> ChangeTargetSyncAbortReceipt:
        """Abort one exact preserved target merge and clear its attention."""
        runtime = self._runtime(change_id, for_mutation=True)
        with locked_roots((self._checkpoint_lock_root(change_id),)):
            disposition = runtime.change_disposition()
            attention_active = disposition is not None
            if attention_active:
                runtime.validate_target_sync_conflict(expected_disposition_id, operation_id)
                self._require_target_sync_change_mutable(runtime)
            else:
                resolution = runtime.change_disposition_resolution()
                if resolution is None or resolution.disposition_id != expected_disposition_id:
                    runtime.validate_target_sync_conflict(expected_disposition_id, operation_id)
            if runtime.active_claims() or runtime.integration_repair_claim() is not None:
                self._fail("target synchronization conflict exit cannot overlap an active Delivery claim")
            request = TargetSyncConflictRequest(
                change_id=change_id,
                target_head=target_head,
                operation_id=operation_id,
            )
            try:
                receipt = self._workspace_manager.abort_target_sync_conflict(request)
            except (OSError, subprocess.SubprocessError, ValueError) as exc:
                self._fail("target synchronization conflict could not be aborted", exc)
            if attention_active:
                resolution = runtime.record_target_sync_abort(
                    expected_disposition_id,
                    operation_id,
                    _timestamp(self._clock()),
                )
                self._publish_delivery_state(change_id, runtime, f"target-sync-abort-{resolution.resolution_id}")
            return receipt

    def resolve_target_sync_conflict(
        self,
        change_id: str,
        expected_disposition_id: str,
        target_head: str,
        operation_id: str,
    ) -> ChangeTargetSyncReceipt:
        """Record one exact semantic target merge and clear its attention."""
        runtime = self._runtime(change_id, for_mutation=True)
        request = TargetSyncConflictRequest(
            change_id=change_id,
            target_head=target_head,
            operation_id=operation_id,
        )
        with locked_roots((self._checkpoint_lock_root(change_id),)):
            existing = runtime.target_sync_receipt()
            if existing is not None:
                return self._replay_target_sync_resolution(
                    runtime,
                    existing,
                    expected_disposition_id,
                    request,
                )
            return self._record_target_sync_resolution(
                runtime,
                expected_disposition_id,
                request,
            )

    def _replay_target_sync_resolution(
        self,
        runtime: DeliveryRuntime,
        existing: ChangeTargetSyncReceipt,
        expected_disposition_id: str,
        request: TargetSyncConflictRequest,
    ) -> ChangeTargetSyncReceipt:
        if existing.operation_id != request.operation_id or existing.target_head != request.target_head:
            self._fail("target synchronization resolution identity differs from runtime evidence")
        if runtime.change_disposition() is not None:
            runtime.validate_target_sync_conflict(expected_disposition_id, request.operation_id)
        else:
            resolution = runtime.change_disposition_resolution()
            if resolution is None or resolution.disposition_id != expected_disposition_id:
                self._fail("target synchronization resolution attention identity differs from runtime evidence")
        receipt = self._resolve_target_sync_workspace(request)
        if receipt != existing:
            self._fail("target synchronization resolution differs from runtime evidence")
        resolution = runtime.change_disposition_resolution()
        if resolution is not None:
            checkpoint = runtime.checkpoint_publication_state()
            if checkpoint.published_head != receipt.merged_head:
                self._publish_target_sync_branch(request.change_id, runtime, receipt.merged_head)
            self._publish_delivery_state(
                request.change_id,
                runtime,
                f"target-sync-resolution-{resolution.resolution_id}",
            )
            self._acknowledge_published_target_sync_checkpoint(runtime, receipt.merged_head)
        return receipt

    def _record_target_sync_resolution(
        self,
        runtime: DeliveryRuntime,
        expected_disposition_id: str,
        request: TargetSyncConflictRequest,
    ) -> ChangeTargetSyncReceipt:
        runtime.validate_target_sync_conflict(expected_disposition_id, request.operation_id)
        self._require_target_sync_change_mutable(runtime)
        if runtime.active_claims() or runtime.integration_repair_claim() is not None:
            self._fail("target synchronization conflict exit cannot overlap an active Delivery claim")
        receipt = self._resolve_target_sync_workspace(request)
        receipt = runtime.record_resolved_target_sync(
            receipt,
            expected_disposition_id,
            request.operation_id,
            _timestamp(self._clock()),
        )
        resolution = runtime.change_disposition_resolution()
        if resolution is None:
            self._fail("target synchronization resolution did not record attention resolution")
        self._publish_target_sync_branch(request.change_id, runtime, receipt.merged_head)
        self._publish_delivery_state(
            request.change_id,
            runtime,
            f"target-sync-resolution-{resolution.resolution_id}",
        )
        self._acknowledge_published_target_sync_checkpoint(runtime, receipt.merged_head)
        return receipt

    def _resolve_target_sync_workspace(
        self,
        request: TargetSyncConflictRequest,
    ) -> ChangeTargetSyncReceipt:
        try:
            return self._workspace_manager.resolve_target_sync_conflict(request)
        except (OSError, subprocess.SubprocessError, ValueError) as exc:
            self._fail("target synchronization conflict could not be resolved", exc)

    def supersede_publication(
        self,
        change_id: str,
        expected_publication_id: str,
        operation_id: str,
    ) -> DeliveryChangePublicationSupersessionReceipt:
        """Publish one successor branch and PR for an exact publication attention."""
        if self._change_branch_publisher is None or self._draft_pull_request_publisher is None:
            self._fail("publication supersession is not configured")
        runtime = self._runtime(change_id, for_mutation=True)
        with locked_roots((self._checkpoint_lock_root(change_id),)):
            self._require_fresh_target_sync_review(runtime)
            runtime_history, predecessor, replay_head = self._read_supersession_context(
                runtime,
                change_id,
                expected_publication_id,
                operation_id,
            )

            try:
                superseding_head = self._workspace_manager.reviewed_source_head(change_id)
            except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as exc:
                self._fail("publication supersession requires a clean reviewed Change head", exc)
            if replay_head is not None and superseding_head != replay_head:
                self._fail("publication supersession replay requires the stored successor head")

            git_receipt, provider_receipt = self._publish_supersession(
                runtime,
                _SupersessionPublishContext(
                    change_id=change_id,
                    expected_publication_id=expected_publication_id,
                    operation_id=operation_id,
                    predecessor=predecessor,
                    superseding_head=superseding_head,
                    target_branch=self._draft_pull_request_publisher.target_branch,
                ),
            )
            finalization = runtime.finalization()
            if finalization is not None and finalization.exact_head != superseding_head:
                runtime.reconcile_finalization_head(superseding_head, _timestamp(self._clock()))
            updated_history = self._bind_supersession_successor(
                runtime,
                runtime_history,
                predecessor,
                provider_receipt,
            )
            self._publish_delivery_state(
                change_id, runtime, f"supersession-{provider_receipt.successor_publication.receipt_id}"
            )
            return DeliveryChangePublicationSupersessionReceipt.create(
                operation_id=operation_id,
                predecessor_publication_id=expected_publication_id,
                git_supersession=git_receipt,
                provider_supersession=provider_receipt,
                publication_history=updated_history,
            )

    def supersede_current_publication(
        self,
        change_id: str,
        operation_id: str,
    ) -> DeliveryChangePublicationSupersessionReceipt:
        """Resolve the current provider publication before starting one successor operation."""
        publisher = self._draft_pull_request_publisher
        if publisher is None:
            self._fail("publication supersession is not configured")
        self._require_fresh_target_sync_review(self._runtime(change_id, for_mutation=True))
        try:
            superseding_head = self._workspace_manager.reviewed_source_head(change_id)
            self._workspace_manager.repository_automation_paths(change_id, superseding_head)
        except PublicationBaselineUnavailableError:
            raise
        except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as exc:
            self._fail("publication supersession requires a clean reviewed Change head", exc)
        provider_history = publisher.read_publication_history(ReadChangePublicationHistory(change_id=change_id))
        if provider_history is None:
            self._fail("publication supersession requires current provider publication history")
        return self.supersede_publication(change_id, provider_history.current_receipt_id, operation_id)

    def _read_supersession_context(
        self,
        runtime: DeliveryRuntime,
        change_id: str,
        expected_publication_id: str,
        operation_id: str,
    ) -> tuple[DeliveryChangePublicationHistory, DraftPullRequestPublicationReceipt, str | None]:
        disposition = runtime.change_disposition()
        if disposition is None or disposition.kind != DeliveryChangeDispositionKind.PUBLICATION_ATTENTION:
            self._fail("publication supersession requires current publication attention")
        runtime_history = runtime.publication_history()
        if runtime_history is None:
            self._fail("publication supersession requires current runtime publication history")
        if runtime.change_disposition_publication() != runtime_history.current:
            self._fail("publication attention does not retain the current runtime publication")
        publisher = self._draft_pull_request_publisher
        if publisher is None:
            self._fail("publication supersession is not configured")
        provider_history = publisher.read_publication_history(ReadChangePublicationHistory(change_id=change_id))
        if provider_history is None:
            self._fail("publication supersession requires current provider publication history")
        predecessor = next(
            (
                publication
                for publication in provider_history.publications
                if publication.receipt_id == expected_publication_id
            ),
            None,
        )
        if predecessor is None:
            self._fail("expected publication identity is not in provider publication history")
        replay_head = self._validate_supersession_history(
            runtime_history,
            provider_history,
            predecessor,
            expected_publication_id,
            operation_id,
        )
        if predecessor.base_branch != publisher.target_branch:
            self._fail("publication predecessor targets a different integration branch")
        return runtime_history, predecessor, replay_head

    def _validate_supersession_history(
        self,
        runtime_history: DeliveryChangePublicationHistory,
        provider_history: DraftPullRequestPublicationHistory,
        predecessor: DraftPullRequestPublicationReceipt,
        expected_publication_id: str,
        operation_id: str,
    ) -> str | None:
        predecessor_identity = _publication_identity(predecessor)
        provider_current = provider_history.publications[-1]
        provider_current_identity = _publication_identity(provider_current)
        if provider_current.receipt_id == expected_publication_id:
            if runtime_history.current != predecessor_identity:
                self._fail("runtime and provider publication predecessors differ")
            return None
        if (
            provider_current.operation_id != operation_id
            or provider_history.predecessor_receipt_ids[-1] != expected_publication_id
            or runtime_history.current not in (predecessor_identity, provider_current_identity)
        ):
            self._fail("provider publication history has a different current successor")
        return provider_current.head_sha

    def _publish_supersession(
        self,
        runtime: DeliveryRuntime,
        context: _SupersessionPublishContext,
    ) -> tuple[ChangeBranchSupersessionReceipt, DraftPullRequestSupersessionReceipt]:
        branch_publisher = self._change_branch_publisher
        provider_publisher = self._draft_pull_request_publisher
        if branch_publisher is None or provider_publisher is None:
            self._fail("publication supersession is not configured")
        package = self._package_store.read_verified(context.change_id)
        self._validate_package_authority(runtime, package)
        automation_paths = self._workspace_manager.repository_automation_paths(
            context.change_id,
            context.superseding_head,
        )
        git_receipt = branch_publisher.supersede(
            SupersedeChangeBranch(
                change_id=context.change_id,
                expected_published_branch=context.predecessor.head_branch,
                expected_published_head=context.predecessor.head_sha,
                superseding_head=context.superseding_head,
                operation_id=context.operation_id,
            )
        )
        self._validate_git_supersession(
            git_receipt,
            context,
        )
        provider_receipt = provider_publisher.supersede(
            SupersedeDraftPullRequest(
                change_id=context.change_id,
                operation_id=context.operation_id,
                expected_predecessor_receipt_id=context.expected_publication_id,
                predecessor_branch=context.predecessor.head_branch,
                predecessor_head=context.predecessor.head_sha,
                successor_branch=git_receipt.successor_branch,
                superseding_head=context.superseding_head,
                title=_checkpoint_pull_request_title(runtime),
                generated_summary=_checkpoint_summary(
                    runtime,
                    package,
                    None,
                    context.superseding_head,
                    automation_paths,
                    supersedes_publication_id=context.expected_publication_id,
                ),
            )
        )
        self._validate_provider_supersession(
            provider_receipt,
            git_receipt,
            context,
        )
        return git_receipt, provider_receipt

    def _bind_supersession_successor(
        self,
        runtime: DeliveryRuntime,
        runtime_history: DeliveryChangePublicationHistory,
        predecessor: DraftPullRequestPublicationReceipt,
        provider_receipt: DraftPullRequestSupersessionReceipt,
    ) -> DeliveryChangePublicationHistory:
        predecessor_identity = _publication_identity(predecessor)
        successor_identity = _publication_identity(provider_receipt.successor_publication)
        if runtime_history.current == successor_identity:
            return runtime_history
        if runtime_history.current != predecessor_identity:
            self._fail("runtime publication history cannot bind the provider successor")
        return runtime.record_publication_successor(predecessor_identity, successor_identity)

    @staticmethod
    def _validate_git_supersession(
        receipt: ChangeBranchSupersessionReceipt,
        context: _SupersessionPublishContext,
    ) -> None:
        if (
            receipt.change_id != context.change_id
            or receipt.predecessor_branch != context.predecessor.head_branch
            or receipt.predecessor_head != context.predecessor.head_sha
            or receipt.superseding_head != context.superseding_head
        ):
            message = "Git supersession receipt does not match provider publication authority"
            raise PortfolioApplicationError(message)

    @staticmethod
    def _validate_provider_supersession(
        receipt: DraftPullRequestSupersessionReceipt,
        git_receipt: ChangeBranchSupersessionReceipt,
        context: _SupersessionPublishContext,
    ) -> None:
        if (
            receipt.change_id != context.change_id
            or receipt.predecessor_receipt_id != context.expected_publication_id
            or receipt.predecessor_branch != git_receipt.predecessor_branch
            or receipt.predecessor_head != git_receipt.predecessor_head
            or receipt.successor_branch != git_receipt.successor_branch
            or receipt.superseding_head != git_receipt.superseding_head
            or receipt.base_branch != context.target_branch
        ):
            message = "provider supersession receipt does not match Git publication authority"
            raise PortfolioApplicationError(message)

    def show_change_checkpoint_publication(self, change_id: str) -> DeliveryCheckpointPublicationState:
        """Return the durable checkpoint queue for one admitted Change."""
        return self._runtime(change_id).checkpoint_publication_state()

    def list_retained_change_worktrees(self) -> tuple[DeliveryRetainedChangeWorktree, ...]:
        """List retained Change worktrees and exact cleanup eligibility facts."""
        self._reconcile_runtimes()
        return tuple(self._retained_change_worktree_view(item) for item in self._workspace_manager.list_retained())

    def recover_change_worktree(
        self,
        change_id: str,
        recovery_reviewed_head: str,
        *,
        confirmed_recovery: Literal[True],
    ) -> DeliveryChangeWorktreeRecovery:
        """Recreate one missing Change worktree from explicit reviewed authority."""
        if confirmed_recovery is not True:
            self._fail("Change worktree recovery requires explicit confirmation")
        runtime = self._runtime(change_id, for_mutation=True, allow_finalizer=True)
        with self._coordinator.acquisition_lock(), locked_roots((self._checkpoint_lock_root(change_id),)):
            if runtime.active_claims() or runtime.integration_repair_claim() is not None:
                raise DeliveryWorkerExclusionRequiredError
            try:
                coordination = self._workspace_manager.recover(change_id, recovery_reviewed_head)
                branch_head = self._workspace_manager.observed_change_head(change_id)
            except ChangeWorktreeAttentionError:
                raise
            except CoordinationConflictError:
                raise
            except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as exc:
                self._fail("Change worktree recovery could not complete", exc)
        return DeliveryChangeWorktreeRecovery(
            change_id=coordination.change_id,
            branch=coordination.branch,
            worktree_path=coordination.worktree_path,
            branch_head=branch_head,
            recovery_reviewed_head=recovery_reviewed_head,
        )

    def cleanup_change_worktree(
        self,
        change_id: str,
        expected_completion_id: str | None = None,
    ) -> DeliveryChangeWorktreeCleanup:
        """Clean one terminal Change worktree after exact lifecycle validation."""
        runtime = self._runtime(change_id, for_mutation=True)
        with locked_roots((self._checkpoint_lock_root(change_id),)):
            return self._cleanup_change_worktree_locked(change_id, runtime, expected_completion_id)

    def _cleanup_change_worktree_locked(
        self,
        change_id: str,
        runtime: DeliveryRuntime,
        expected_completion_id: str | None = None,
    ) -> DeliveryChangeWorktreeCleanup:
        """Clean one terminal Change worktree while its checkpoint lock is held."""
        lifecycle = runtime.change_stage()
        completion = runtime.completion_receipt()
        completed = lifecycle == DeliveryChangeStage.COMPLETED and completion is not None
        if lifecycle != DeliveryChangeStage.ABANDONED and not completed:
            self._fail("Change worktree cleanup requires an abandoned or completed Change")
        if expected_completion_id is not None and (not completed or completion.completion_id != expected_completion_id):
            self._fail("completed Change worktree cleanup requires the exact completion receipt")
        try:
            receipt = self._workspace_manager.cleanup(change_id)
        except ChangeWorktreeAttentionError:
            raise
        except CoordinationConflictError:
            raise
        except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as exc:
            self._fail("Change worktree cleanup could not complete", exc)
        return DeliveryChangeWorktreeCleanup(
            cleanup_id=receipt.cleanup_id,
            change_id=receipt.change_id,
            branch=receipt.branch,
            worktree_path=receipt.worktree_path,
            branch_head=receipt.branch_head,
        )

    def cleanup_abandoned_change_worktree(self, change_id: str) -> DeliveryChangeWorktreeCleanup:
        """Clean one abandoned Change worktree without reopening its terminal state."""
        runtime = self._runtime(change_id, for_mutation=True)
        if runtime.change_stage() != DeliveryChangeStage.ABANDONED:
            self._fail("abandoned Change worktree cleanup requires an abandoned Change")
        return self.cleanup_change_worktree(change_id)

    def cleanup_abandoned_change_worktree_after_target_sync_discard(
        self,
        change_id: str,
        *,
        confirmed_discard: Literal[True],
        expected_target_head: str,
        expected_operation_id: str,
    ) -> DeliveryChangeWorktreeCleanup:
        """Discard one abandoned target merge and then clean its exact Change worktree."""
        if confirmed_discard is not True:
            self._fail("discarding an abandoned target synchronization conflict requires explicit confirmation")
        runtime = self._runtime(change_id, for_mutation=True)
        with locked_roots((self._checkpoint_lock_root(change_id),)):
            if runtime.change_stage() != DeliveryChangeStage.ABANDONED:
                self._fail("abandoned target synchronization conflict cleanup requires an abandoned Change")
            coordination = self._workspace_manager.show(change_id)
            self._discard_abandoned_target_sync_conflict(
                change_id,
                coordination,
                expected_target_head,
                expected_operation_id,
            )
            return self._cleanup_change_worktree_locked(change_id, runtime)

    def _discard_abandoned_target_sync_conflict(
        self,
        change_id: str,
        coordination: ChangeCoordination,
        expected_target_head: str,
        expected_operation_id: str,
    ) -> None:
        conflict = coordination.target_sync_conflict
        if conflict is None:
            return
        if conflict.target_head != expected_target_head or conflict.operation_id != expected_operation_id:
            self._fail("abandoned target synchronization conflict evidence is stale")
        retained = next(
            (item for item in self._workspace_manager.list_retained() if item.change_id == change_id),
            None,
        )
        if retained is None:
            self._fail("abandoned target synchronization conflict worktree is not registered")
        if not retained.worktree_present or not retained.git_registered:
            try:
                coordination = self._workspace_manager.recover(
                    change_id,
                    coordination.last_reviewed_commit,
                )
            except ChangeWorktreeAttentionError:
                raise
            except CoordinationConflictError:
                raise
            except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as exc:
                self._fail("abandoned target synchronization conflict worktree could not be recovered", exc)
        try:
            self._workspace_manager.abort_target_sync_conflict(
                TargetSyncConflictRequest(
                    change_id=change_id,
                    target_head=conflict.target_head,
                    operation_id=conflict.operation_id,
                )
            )
        except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as exc:
            self._fail("abandoned target synchronization conflict could not be discarded", exc)

    def cleanup_completed_change_worktree(
        self,
        change_id: str,
        completion_id: str,
    ) -> DeliveryChangeWorktreeCleanup:
        """Clean one completed Change worktree after matching its durable receipt."""
        return self.cleanup_change_worktree(change_id, expected_completion_id=completion_id)

    def show_finalization_context(self, change_id: str) -> DeliveryFinalizationContext:
        """Return engine-resolved finalization context without changing Delivery state."""
        runtime = self._runtime(change_id)
        snapshot = self._delivery_snapshot(runtime)
        projector = self._read_projector(snapshot)
        cards = projector.group_view().items
        card = next((item for item in cards if item.item_key == "publication"), cards[0])
        readiness = card.readiness
        if readiness is None:
            self._fail("finalization readiness was not captured")
        coordination = self._workspace_manager.show(change_id)
        finalization = snapshot.frontier.finalization
        invalidation = snapshot.frontier.finalization_invalidation
        ready = readiness.executable and readiness.operation is WorkItemActionKind.FINALIZE
        return DeliveryFinalizationContext(
            change_id=change_id,
            branch=coordination.branch,
            worktree_path=coordination.worktree_path,
            change_head=readiness.basis.candidate_head,
            reviewed_change_head=coordination.last_reviewed_commit,
            publication_phase=resolve_publication_phase(snapshot.frontier),
            ready_for_finalization=ready,
            readiness_diagnostics=() if ready else (readiness.reason_code,),
            finalization_id=finalization.finalization_id if finalization is not None else None,
            finalized_head=finalization.exact_head if finalization is not None else None,
            finalization_invalidation_id=invalidation.invalidation_id if invalidation is not None else None,
            readiness=readiness,
        )

    def finalize_change(
        self,
        change_id: str,
        request: FinalizeDeliveryChange,
    ) -> DeliveryFinalizationReceipt:
        """Finalize one exact clean reviewed Change head and queue its checkpoint."""
        runtime = self._runtime(change_id, for_mutation=True, allow_finalizer=True)
        with locked_roots((self._checkpoint_lock_root(change_id),)):
            return self._finalize_change_locked(change_id, runtime, request)

    def _finalize_change_locked(
        self, change_id: str, runtime: DeliveryRuntime, request: FinalizeDeliveryChange
    ) -> DeliveryFinalizationReceipt:
        existing = runtime.finalization()
        if existing is not None:
            if (
                existing.operation_id == request.operation_id
                and existing.exact_head == request.exact_head
                and existing.observations == request.observations
                and existing.review == request.review
            ):
                self._record_finalization_retry_success(runtime, request.operation_id)
                self._promote_finalized_external_head(change_id, existing.exact_head)
                self._retire_finalization_report(runtime, existing.exact_head)
                return existing
            self._fail(
                "Delivery Change is already finalized with different authority",
                ValueError("finalization request is not an exact replay"),
            )
        if runtime.change_disposition() is not None:
            self._fail("finalization requires current Change attention resolution")
        attempt = self._workspace_manager.show(change_id).finalization_attempt
        reports = FinalizationReportStore(self._target_root, change_id).read()
        if any(report.request.attempt_key == request.operation_id for report in reports.reports):
            message = "failed finalization attempt cannot submit success after retirement"
            raise DeliveryActionBusyError(message)
        active = attempt is not None and attempt.finished_at is None
        if active:
            self._require_finalization_attempt(runtime, request, attempt)
        context = self.show_finalization_context(change_id)
        if not active and not context.ready_for_finalization:
            self._fail(
                "finalization requires a ready exact Change context",
                ValueError("; ".join(context.readiness_diagnostics)),
            )
        if request.exact_head != context.change_head:
            self._fail(
                "finalization request does not match the current Change head",
                ValueError("Change head changed"),
            )
        results = tuple(result for binding in runtime.bindings() for result in binding.results)
        with self._coordinator.publication_lock(change_id) as publication_lock:
            boundary_participant = self._workspace_manager.prepare_finalization_boundary(
                change_id,
                request.exact_head,
                tuple(result.completed_commit for result in results),
                publication_lock,
                completion=(request.operation_id, self._clock()),
            )
            additional_participants = () if boundary_participant is None else (boundary_participant,)
            finalization = runtime.finalize_change(
                request,
                _timestamp(self._clock()),
                additional_participants=additional_participants,
            )
        self._record_finalization_retry_success(runtime, request.operation_id)
        self._promote_finalized_external_head(change_id, finalization.exact_head)
        self._retire_finalization_report(runtime, finalization.exact_head)
        return finalization

    def _record_finalization_retry_success(self, runtime: DeliveryRuntime, attempt_id: str) -> None:
        """Close a reserved finalizer attempt after its durable receipt is published."""
        with suppress(OSError, RetryLedgerConflictError, RetryLedgerCorruptError, RuntimeError, ValueError):
            runtime.retry_ledger(clock=self._clock).record_accepted_progress(attempt_id, now=self._clock())

    def _record_worker_retry_success(self, runtime: DeliveryRuntime, outcome_id: str, claim_id: str) -> None:
        """Close a reserved worker attempt after its claim-scoped output is accepted."""
        with suppress(OSError, RetryLedgerConflictError, RetryLedgerCorruptError, RuntimeError, ValueError):
            binding = runtime.show_binding(outcome_id)
            claim = binding.active_claim
            ledger = runtime.retry_ledger(clock=self._clock)
            attempt_id = (
                claim.attempt_id
                if claim is not None and claim.claim_id == claim_id
                else ledger.attempt_for_operation(claim_id)
            )
            if attempt_id is not None:
                ledger.record_accepted_progress(attempt_id, now=self._clock())

    def _record_retry_release(
        self,
        runtime: DeliveryRuntime,
        *,
        attempt_id: str | None = None,
        outcome_id: str | None = None,
    ) -> None:
        """Release verified custody without resetting the affected retry budget."""
        if attempt_id is None and outcome_id is None:
            return
        with suppress(OSError, RetryLedgerConflictError, RetryLedgerCorruptError, RuntimeError, ValueError):
            ledger = runtime.retry_ledger(clock=self._clock)
            if attempt_id is not None:
                reports = FinalizationReportStore(self._target_root, runtime.contract.change_id).read()
                report = next(
                    (item for item in reports.reports if item.request.attempt_key == attempt_id),
                    None,
                )
                if report is not None:
                    ledger.record_failure(
                        attempt_id,
                        failure_code=report.request.code.value,
                        failure_detail=report.summary,
                        now=report.observed_at,
                    )
                ledger.record_recovery_release(attempt_id, now=self._clock())
            elif outcome_id is not None:
                ledger.record_recovery_release_for_outcome(outcome_id, now=self._clock())

    def _require_finalization_attempt(
        self, runtime: DeliveryRuntime, request: FinalizeDeliveryChange, attempt: ChangeFinalizationAttempt
    ) -> None:
        if (
            request.operation_id != attempt.writer.attempt_id
            or request.exact_head != attempt.exact_head
            or hashlib.sha256(runtime.frontier_bytes()).hexdigest() != attempt.frontier_digest
            or contract_fingerprint(runtime.contract) != attempt.contract_digest
        ):
            message = "finalization attempt does not match current authority"
            raise DeliveryActionSelectionConflictError(message)
        reports = FinalizationReportStore(self._target_root, runtime.contract.change_id).read()
        if any(report.request.attempt_key == request.operation_id for report in reports.reports):
            message = "failed finalization retains custody pending supported recovery"
            raise DeliveryActionBusyError(message)

    def _retire_finalization_report(self, runtime: DeliveryRuntime, exact_head: str) -> None:
        try:
            FinalizationReportStore(self._target_root, runtime.contract.change_id).retire(
                exact_head, contract_fingerprint(runtime.contract)
            )
        except FinalizationReportError:
            _logger.warning("Successful finalization retained a diagnostic pointer: report-store-unavailable")

    def report_finalization_failure(
        self,
        request: ReportFinalizationFailure,
    ) -> FinalizationReport | DeliveryReadiness:
        """Persist structural diagnostics without granting lifecycle or proof authority."""
        with locked_roots((self._checkpoint_lock_root(request.change_id),)):
            try:
                report = FinalizationReportStore(self._target_root, request.change_id).record(
                    request,
                    _timestamp(self._clock()),
                    lambda: self._validate_finalization_report_basis(request),
                )
            except _FinalizationReadUnavailableError as exc:
                return exc.readiness
            if isinstance(report, FinalizationReport):
                with suppress(OSError, RetryLedgerConflictError, RetryLedgerCorruptError, RuntimeError, ValueError):
                    self._runtime(request.change_id).retry_ledger(clock=self._clock).record_failure(
                        request.attempt_key,
                        failure_code=request.code.value,
                        failure_detail=report.summary,
                        now=report.observed_at,
                    )
            return report

    def _validate_finalization_report_basis(self, request: ReportFinalizationFailure) -> None:
        self._reconcile_runtimes()
        observation = self._discovered_changes.get(request.change_id)
        if observation is not None and not observation.actionable_runtime:
            raise _FinalizationReadUnavailableError(self._unavailable_change(request.change_id).readiness)
        runtime = self._runtime(request.change_id)
        attempt = self._workspace_manager.show(request.change_id).finalization_attempt
        if attempt is not None and attempt.finished_at is None and request.attempt_key != attempt.writer.attempt_id:
            msg = "diagnostic-conflict"
            raise FinalizationReportError(msg)
        snapshot = self._delivery_snapshot(runtime)
        basis = DeliveryReadinessBasis(
            contract_digest=contract_fingerprint(snapshot.contract), frontier_digest=snapshot.version
        )
        try:
            coordination, head, fingerprint, paths, reason = self._workspace_manager.capture_finalization_workspace(
                request.change_id,
                tuple(result.completed_commit for binding in snapshot.frontier.bindings for result in binding.results),
            )
        except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as exc:
            raise _FinalizationReadUnavailableError(
                DeliveryReadiness(
                    status="unavailable",
                    next_actor=WorkItemNextActor.NONE,
                    reason_code="workspace-inspection-failed",
                    basis=basis,
                )
            ) from exc
        if (
            request.expected_contract_digest != basis.contract_digest
            or request.expected_frontier_digest != basis.frontier_digest
            or request.expected_change_head != head
            or request.expected_reviewed_head != coordination.last_reviewed_commit
        ):
            msg = "diagnostic-conflict"
            raise FinalizationReportError(msg)
        if request.category == "custody-preflight" and (
            request.expected_workspace_fingerprint != fingerprint
            or not set(request.paths) <= set(paths)
            or (request.code.value == "workspace-dirty" and not paths)
            or (request.code.value == "workspace-preflight-failed" and reason is None)
        ):
            msg = "diagnostic-conflict"
            raise FinalizationReportError(msg)
        if request.category == "proof-mutation" and (
            (
                request.expected_workspace_fingerprint is not None
                and request.expected_workspace_fingerprint != request.proof_fingerprint_before
            )
            or request.proof_fingerprint_after != fingerprint
            or not set(request.paths) <= set(paths)
        ):
            msg = "diagnostic-conflict"
            raise FinalizationReportError(msg)

    def mark_change_ready(
        self,
        change_id: str,
        request: MarkChangePullRequestReady,
    ) -> PullRequestReadyReceipt:
        """Mark the exact finalized and fully published Change pull request ready."""
        if self._draft_pull_request_publisher is None:
            message = "draft pull-request publication is not configured"
            raise PortfolioApplicationError(message)
        runtime = self._runtime(change_id, for_mutation=True)
        with self._engine_checkpoint_lock(change_id):
            if runtime.change_disposition() is not None:
                message = "pull-request readiness requires current Change attention resolution"
                raise PortfolioApplicationError(message)
            finalization = runtime.finalization()
            publication = runtime.checkpoint_publication_state()
            if (
                finalization is None
                or request.change_id != change_id
                or request.finalization_id != finalization.finalization_id
                or request.exact_head != finalization.exact_head
            ):
                message = "pull-request ready request does not match current finalization authority"
                raise PortfolioApplicationError(message)
            if publication.published_head != finalization.exact_head or publication.pending_checkpoint is not None:
                message = "pull-request readiness requires the reconciled final checkpoint"
                raise PortfolioApplicationError(message)
            existing_ready = runtime.ready_receipt()
            if (
                existing_ready is not None
                and existing_ready.finalization_id == finalization.finalization_id
                and existing_ready.head_sha == finalization.exact_head
            ):
                receipt = self._draft_pull_request_publisher.mark_ready(request)
                ready = runtime.mark_awaiting_merge(receipt)
                self._publish_delivery_state(change_id, runtime, f"ready-{ready.receipt_id}")
                return ready
            observation, failures = self._observe_required_checks_for_ready(
                change_id,
                finalization.exact_head,
            )
            receipt = self._draft_pull_request_publisher.mark_ready(request)
            ready = runtime.mark_awaiting_merge(receipt)
            if failures:
                self._record_required_check_attention(runtime, observation, failures, ready)
            self._publish_delivery_state(change_id, runtime, f"ready-{ready.receipt_id}")
            return ready

    def _observe_required_checks_for_ready(
        self,
        change_id: str,
        exact_head: str,
    ) -> tuple[PublicationCheckObservationReceipt, tuple[PublicationCheck, ...]]:
        """Observe provider-required checks without gating the pull-request ready state."""
        publisher = self._draft_pull_request_publisher
        if publisher is None:
            message = "draft pull-request publication is not configured"
            raise PortfolioApplicationError(message)
        observation = publisher.observe_checks(
            ObserveChangePublicationChecks(change_id=change_id, published_head=exact_head)
        )
        failures = _failed_required_publication_checks(observation.snapshot)
        return observation, failures

    @staticmethod
    def _record_required_check_attention(
        runtime: DeliveryRuntime,
        observation: PublicationCheckObservationReceipt,
        failures: tuple[PublicationCheck, ...],
        ready: PullRequestReadyReceipt,
    ) -> None:
        """Retain failing provider-required checks after the PR is ready."""
        runtime.capture_publication_attention(
            observation.observed_at,
            _required_check_diagnostics(observation.snapshot, observation.observation_id, failures),
            publication_identity=DeliveryChangePublicationIdentity(
                change_id=ready.change_id,
                repository=ready.repository,
                number=ready.number,
                node_id=ready.node_id,
                head_sha=ready.head_sha,
            ),
        )

    def mark_current_change_ready(self, change_id: str) -> PullRequestReadyReceipt:
        """Mark the current exact finalization ready without caller-supplied authority."""
        finalization = self._runtime(change_id).finalization()
        if finalization is None:
            message = "pull-request readiness requires current finalization authority"
            raise PortfolioApplicationError(message)
        return self.mark_change_ready(
            change_id,
            MarkChangePullRequestReady(
                change_id=change_id,
                operation_id=f"ready-{finalization.finalization_id}",
                finalization_id=finalization.finalization_id,
                exact_head=finalization.exact_head,
            ),
        )

    def prepare_review_repair(self, change_id: str) -> DeliveryFinalizationInvalidationReceipt:
        """Return an open Change pull request to draft before external review repair."""
        publisher = self._draft_pull_request_publisher
        if publisher is None:
            message = "review repair requires a publication provider"
            raise PortfolioApplicationError(message)
        runtime = self._runtime(change_id, for_mutation=True)
        with locked_roots((self._checkpoint_lock_root(change_id),)):
            authority = self._review_repair_authority(runtime)
            observation = self._observe_review_repair_pull_request(change_id, publisher, authority)
            replayed = self._replay_review_repair(change_id, publisher, authority, observation)
            if replayed is not None:
                return replayed
            if not observation.snapshot.draft:
                publisher.return_to_draft(
                    ReturnChangePullRequestToDraft(
                        change_id=change_id,
                        operation_id=f"review-repair-draft-{authority.expected_finalization_id}",
                        finalization_id=authority.expected_finalization_id,
                        exact_head=authority.expected_head,
                    )
                )
            invalidation = runtime.prepare_review_repair(
                authority.expected_finalization_id,
                _timestamp(self._clock()),
            )
            self._publish_delivery_state(change_id, runtime, f"review-repair-{invalidation.invalidation_id}")
            return invalidation

    @staticmethod
    def _review_repair_authority(runtime: DeliveryRuntime) -> _ReviewRepairAuthority:
        """Validate local review-repair authority and return its exact publication fence."""
        if runtime.change_disposition() is not None:
            message = "review repair requires current Change attention resolution"
            raise PortfolioApplicationError(message)
        invalidation = runtime.finalization_invalidation()
        finalization = runtime.finalization()
        if finalization is None and (invalidation is None or invalidation.reason != "review-repair"):
            message = "review repair requires current finalization authority"
            raise PortfolioApplicationError(message)
        if runtime.merged_pull_request_latch() is not None:
            message = "merged Change cannot be reopened for review repair"
            raise PortfolioApplicationError(message)
        ready = runtime.ready_receipt()
        publication = runtime.publication_history()
        expected_finalization_id = (
            invalidation.finalization_id if invalidation is not None else finalization.finalization_id
        )
        expected_head = invalidation.expected_head if invalidation is not None else finalization.exact_head
        if ready is not None and (ready.finalization_id != expected_finalization_id or ready.head_sha != expected_head):
            message = "review repair ready authority does not match finalization"
            raise PortfolioApplicationError(message)
        if finalization is None and ready is not None:
            message = "review repair cannot replay with ready authority"
            raise PortfolioApplicationError(message)
        identity = ready if ready is not None else None if publication is None else publication.current
        if identity is None:
            message = "review repair requires current publication identity"
            raise PortfolioApplicationError(message)
        return _ReviewRepairAuthority(
            invalidation=invalidation,
            expected_finalization_id=expected_finalization_id,
            expected_head=expected_head,
            repository=identity.repository,
            number=identity.number,
            node_id=identity.node_id,
        )

    def _require_no_review_repair(self, runtime: DeliveryRuntime, operation: str) -> None:
        """Reject Change head movement while external review repair owns the boundary."""
        invalidation = runtime.finalization_invalidation()
        if invalidation is not None and invalidation.reason == "review-repair":
            self._fail(f"{operation} requires review repair to be aborted or finalized first")

    @staticmethod
    def _observe_review_repair_pull_request(
        change_id: str,
        publisher: DraftPullRequestPublisher,
        authority: _ReviewRepairAuthority,
    ) -> PublicationPullRequestObservationReceipt:
        """Observe the bound open pull request at the exact review-repair head."""
        observation = publisher.observe_pull_request(ObserveChangePublicationPullRequest(change_id=change_id))
        if observation is None:
            message = "review repair requires a bound pull request"
            raise PortfolioApplicationError(message)
        snapshot = observation.snapshot
        if (
            snapshot.repository != publisher.repository
            or snapshot.repository != authority.repository
            or snapshot.number != authority.number
            or snapshot.node_id != authority.node_id
            or snapshot.base_branch != publisher.target_branch
            or snapshot.head_sha != authority.expected_head
            or snapshot.state != "open"
            or snapshot.merged
        ):
            message = "review repair requires an open pull request at the finalized head"
            raise PortfolioApplicationError(message)
        return observation

    @staticmethod
    def _replay_review_repair(
        change_id: str,
        publisher: DraftPullRequestPublisher,
        authority: _ReviewRepairAuthority,
        observation: PublicationPullRequestObservationReceipt,
    ) -> DeliveryFinalizationInvalidationReceipt | None:
        """Replay an existing review-repair fence without duplicating provider state changes."""
        invalidation = authority.invalidation
        if invalidation is None:
            return None
        if invalidation.reason != "review-repair" or invalidation.finalization_id != authority.expected_finalization_id:
            message = "review repair finalization invalidation is not replayable"
            raise PortfolioApplicationError(message)
        if not observation.snapshot.draft:
            publisher.return_to_draft(
                ReturnChangePullRequestToDraft(
                    change_id=change_id,
                    operation_id=f"review-repair-draft-{authority.expected_finalization_id}",
                    finalization_id=authority.expected_finalization_id,
                    exact_head=authority.expected_head,
                )
            )
        return invalidation

    def resolve_change_disposition(
        self,
        change_id: str,
        expected_disposition_id: str,
    ) -> DeliveryChangeDispositionResolution:
        """Resolve one exact Change attention record without recreating provider authority."""
        runtime = self._runtime(change_id, for_mutation=True)
        with self._attention_resolution_lock(change_id):
            resolution = runtime.resolve_change_disposition(expected_disposition_id, _timestamp(self._clock()))
            self._publish_delivery_state(change_id, runtime, f"attention-resolution-{resolution.resolution_id}")
            return resolution

    @contextmanager
    def _attention_resolution_lock(self, change_id: str) -> Iterator[None]:
        """Bound checkpoint contention for disposition resolution."""
        deadline = time.monotonic() + _ATTENTION_RESOLUTION_LOCK_TIMEOUT_SECONDS
        with ExitStack() as stack:
            while True:
                try:
                    stack.enter_context(locked_roots((self._checkpoint_lock_root(change_id),), blocking=False))
                except BlockingIOError as exc:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        message = (
                            "Change attention resolution is already in progress; "
                            "retry after the active mutation finishes"
                        )
                        raise DeliveryChangeDispositionBusyError(message) from exc
                    time.sleep(min(_ATTENTION_RESOLUTION_LOCK_RETRY_SECONDS, remaining))
                else:
                    break
            yield

    def recover_publication_baseline(
        self,
        change_id: str,
        expected_change_head: str,
        publication_base_head: str,
        operation_id: str,
        *,
        confirmed_recovery: bool = False,
    ) -> PublicationBaselineRecoveryReceipt:
        """Recover one unknown publication baseline after explicit operator confirmation."""
        if not confirmed_recovery:
            message = "publication baseline recovery requires explicit confirmation"
            raise PortfolioApplicationError(message)
        runtime = self._runtime(change_id, for_mutation=True)
        with locked_roots((self._checkpoint_lock_root(change_id),)):
            if runtime.active_claims() or runtime.integration_repair_claim() is not None:
                message = "publication baseline recovery cannot overlap an active claim"
                raise PortfolioApplicationError(message)
            return self._workspace_manager.recover_publication_baseline(
                change_id,
                expected_change_head,
                publication_base_head,
                operation_id,
            )

    def defer_change(self, change_id: str, reason: str) -> DeliveryChangeDeferral:
        """Retain one nonterminal Change and pause its claimable frontier."""
        runtime = self._runtime(change_id, for_mutation=True)
        with locked_roots((self._checkpoint_lock_root(change_id),)):
            deferral = runtime.defer_change(reason, _timestamp(self._clock()))
            self._publish_delivery_state(change_id, runtime, f"deferral-{deferral.deferral_id}")
            return deferral

    def resume_change(self, change_id: str) -> DeliveryChangeDeferral:
        """Resume one exact deferred Change from its retained prior state."""
        runtime = self._runtime(change_id, for_mutation=True)
        with locked_roots((self._checkpoint_lock_root(change_id),)):
            deferral = runtime.resume_change()
            self._publish_delivery_state(change_id, runtime, f"resume-{deferral.deferral_id}")
            return deferral

    def reconcile_awaiting_acceptance(
        self,
        change_ids: tuple[str, ...] | None = None,
        *,
        limit: int = _MAX_ACCEPTANCE_RECONCILIATION_CHANGES,
    ) -> tuple[DeliveryAcceptanceReconciliationOutcome, ...]:
        """Reconcile a bounded set of observed awaiting-merge Changes."""
        self._reconcile_runtimes()
        if limit < 1:
            message = "acceptance reconciliation limit must be positive"
            raise ValueError(message)
        effective_limit = min(limit, _MAX_ACCEPTANCE_RECONCILIATION_CHANGES)
        requested = None if change_ids is None else frozenset(change_ids)
        all_eligible = tuple(
            change_id
            for change_id, runtime in sorted(self._runtimes.items())
            if self._is_acceptance_reconciliation_eligible(runtime)
        )
        eligible = (
            all_eligible
            if requested is None
            else tuple(change_id for change_id in all_eligible if change_id in requested)
        )
        if not eligible:
            return ()
        selected = self._select_acceptance_reconciliation_changes(
            all_eligible,
            effective_limit,
            requested=requested,
        )
        selected_ids = frozenset(selected)
        outcomes = [self._reconcile_awaiting_acceptance_change(change_id) for change_id in selected]
        outcomes.extend(
            DeliveryAcceptanceReconciliationOutcome(
                change_id=change_id,
                status=DeliveryAcceptanceReconciliationStatus.SKIPPED,
                code="ERR_DELIVERY_RECONCILIATION_LIMIT",
                detail="Acceptance reconciliation batch limit reached.",
            )
            for change_id in eligible
            if change_id not in selected_ids
        )
        return tuple(outcomes)

    def _select_acceptance_reconciliation_changes(
        self,
        eligible: tuple[str, ...],
        limit: int,
        *,
        requested: frozenset[str] | None,
    ) -> tuple[str, ...]:
        """Reserve a fair bounded batch and persist its next starting Change."""
        if not eligible:
            return ()
        cursor_root = self._target_root / "claims" / "acceptance-reconciliation"
        cursor = self._acceptance_reconciliation_cursor
        try:
            with locked_roots((cursor_root,)):
                with suppress(OSError, ValueError):
                    cursor = _AcceptanceReconciliationCursor.model_validate_json(
                        (cursor_root / _ACCEPTANCE_RECONCILIATION_CURSOR_FILE).read_bytes()
                    ).next_change_id
                selected, next_cursor = self._rotate_acceptance_reconciliation_batch(
                    eligible,
                    limit,
                    cursor,
                    requested=requested,
                )
                atomic_write(
                    cursor_root / _ACCEPTANCE_RECONCILIATION_CURSOR_FILE,
                    json.dumps(
                        _AcceptanceReconciliationCursor(next_change_id=next_cursor).model_dump(
                            mode="json",
                        ),
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                    + "\n",
                )
        except (OSError, ValueError):
            selected, next_cursor = self._rotate_acceptance_reconciliation_batch(
                eligible,
                limit,
                self._acceptance_reconciliation_cursor,
                requested=requested,
            )
        self._acceptance_reconciliation_cursor = next_cursor
        return selected

    @staticmethod
    def _rotate_acceptance_reconciliation_batch(
        eligible: tuple[str, ...],
        limit: int,
        cursor: str | None,
        *,
        requested: frozenset[str] | None,
    ) -> tuple[tuple[str, ...], str]:
        """Return one wrapped batch and the deterministic cursor after it."""
        start = (
            0
            if cursor is None
            else next(
                (index for index, change_id in enumerate(eligible) if change_id >= cursor),
                0,
            )
        )
        ordered = tuple(eligible[(start + offset) % len(eligible)] for offset in range(len(eligible)))
        selected = tuple(change_id for change_id in ordered if requested is None or change_id in requested)[:limit]
        eligible_ids = frozenset(eligible)
        requested_eligible_ids = frozenset(
            change_id for change_id in eligible if requested is not None and change_id in requested
        )
        if requested is not None and requested_eligible_ids != eligible_ids:
            return selected, ordered[0]
        selected_ids = frozenset(selected)
        next_cursor = next(
            (change_id for change_id in ordered if change_id not in selected_ids),
            ordered[0],
        )
        return selected, next_cursor

    @staticmethod
    def _is_acceptance_reconciliation_eligible(runtime: DeliveryRuntime) -> bool:
        """Select only live awaiting-merge Changes without competing custody."""
        return runtime.change_stage() == DeliveryChangeStage.AWAITING_MERGE and not runtime.active_claims()

    def _reconcile_awaiting_acceptance_change(
        self,
        change_id: str,
    ) -> DeliveryAcceptanceReconciliationOutcome:
        runtime = self._runtime(change_id, for_mutation=True)
        try:
            with locked_roots((self._checkpoint_lock_root(change_id),), blocking=False):
                if not self._is_acceptance_reconciliation_eligible(runtime):
                    return self._reconciliation_skipped_outcome(change_id, "Change is no longer awaiting merge.")
                reservation = self._reserve_acceptance_observation(runtime, explicit=False)
                if not reservation.allowed:
                    return DeliveryAcceptanceReconciliationOutcome(
                        change_id=change_id,
                        status=DeliveryAcceptanceReconciliationStatus.WAITING,
                        code=reservation.reason_code,
                        detail="Acceptance observation is waiting for its durable retry policy.",
                    )
                try:
                    outcome = self._reconcile_awaiting_acceptance_locked(change_id, runtime, reservation.attempt_id)
                except PublicationProviderError as exc:
                    runtime.retry_ledger(clock=self._clock).record_failure(
                        reservation, failure_code=exc.code.value, now=self._clock()
                    )
                    raise
                except PortfolioApplicationError as exc:
                    outcome = DeliveryAcceptanceReconciliationOutcome(
                        change_id=change_id,
                        status=(
                            DeliveryAcceptanceReconciliationStatus.ATTENTION
                            if runtime.change_disposition() is not None
                            else DeliveryAcceptanceReconciliationStatus.SKIPPED
                        ),
                        code=exc.code,
                        detail=str(exc),
                    )
                ledger = runtime.retry_ledger(clock=self._clock)
                if outcome is not None and outcome.status is DeliveryAcceptanceReconciliationStatus.COMPLETED:
                    ledger.record_accepted_progress(reservation, now=self._clock())
                else:
                    ledger.record_failure(reservation, failure_code="acceptance-wait", now=self._clock())
        except BlockingIOError:
            return DeliveryAcceptanceReconciliationOutcome(
                change_id=change_id,
                status=DeliveryAcceptanceReconciliationStatus.SKIPPED,
                code="ERR_DELIVERY_RECONCILIATION_BUSY",
                detail="Change reconciliation is already in progress.",
            )
        except PublicationProviderError as exc:
            return self._provider_unavailable_outcome(change_id, exc)
        except (
            DeliveryRuntimeConflictError,
            RetryLedgerConflictError,
            RetryLedgerCorruptError,
            OSError,
            ValueError,
        ) as exc:
            return DeliveryAcceptanceReconciliationOutcome(
                change_id=change_id,
                status=DeliveryAcceptanceReconciliationStatus.SKIPPED,
                code="ERR_DELIVERY_RECONCILIATION_STATE_CHANGED",
                detail=str(exc) or "Change state changed during reconciliation.",
            )
        result = outcome
        disposition = runtime.change_disposition()
        if disposition is not None:
            self._publish_attention_best_effort(
                change_id,
                runtime,
                f"acceptance-attention-{disposition.disposition_id}",
            )
        return result

    def _reconcile_awaiting_acceptance_locked(
        self,
        change_id: str,
        runtime: DeliveryRuntime,
        attempt_id: str,
    ) -> DeliveryAcceptanceReconciliationOutcome:
        """Read one provider snapshot while holding only the Change checkpoint lock."""
        if not self._is_acceptance_reconciliation_eligible(runtime):
            return self._reconciliation_skipped_outcome(change_id, "Change is no longer awaiting merge.")
        publisher = self._draft_pull_request_publisher
        if publisher is None:
            return DeliveryAcceptanceReconciliationOutcome(
                change_id=change_id,
                status=DeliveryAcceptanceReconciliationStatus.PROVIDER_UNAVAILABLE,
                code="ERR_DELIVERY_PROVIDER_NOT_CONFIGURED",
                detail="Draft pull-request publication is not configured.",
            )
        finalization = runtime.finalization()
        ready = runtime.ready_receipt()
        if finalization is None or ready is None:
            return self._reconciliation_skipped_outcome(change_id, "Awaiting-merge authority is incomplete.")
        observation = publisher.observe_pull_request(ObserveChangePublicationPullRequest(change_id=change_id))
        if observation is None:
            return self._reconciliation_skipped_outcome(
                change_id,
                "No bound pull-request publication was found.",
                code="ERR_DELIVERY_PUBLICATION_MISSING",
            )
        outcome = self._classify_acceptance_observation(
            change_id,
            runtime,
            observation,
            _AcceptanceReconciliationAuthority(
                exact_head=finalization.exact_head,
                ready=ready,
                target_branch=publisher.target_branch,
            ),
        )
        if outcome is not None:
            return outcome
        receipt = self._observe_acceptance_once(change_id, runtime, attempt_id=attempt_id, observation=observation)
        return DeliveryAcceptanceReconciliationOutcome(
            change_id=change_id,
            status=DeliveryAcceptanceReconciliationStatus.COMPLETED,
            completion_id=receipt.completion_id,
        )

    @staticmethod
    def _reconciliation_skipped_outcome(
        change_id: str,
        detail: str,
        *,
        code: str = "ERR_DELIVERY_RECONCILIATION_STATE_CHANGED",
    ) -> DeliveryAcceptanceReconciliationOutcome:
        return DeliveryAcceptanceReconciliationOutcome(
            change_id=change_id,
            status=DeliveryAcceptanceReconciliationStatus.SKIPPED,
            code=code,
            detail=detail,
        )

    def _classify_acceptance_observation(
        self,
        change_id: str,
        runtime: DeliveryRuntime,
        observation: PublicationPullRequestObservationReceipt,
        authority: _AcceptanceReconciliationAuthority,
    ) -> DeliveryAcceptanceReconciliationOutcome | None:
        snapshot = observation.snapshot
        if self._acceptance_reconciliation_authority_matches(
            snapshot, authority.exact_head, authority.ready, authority.target_branch
        ):
            self._remember_acceptance_observation(observation)
        if snapshot.state == "open" and not snapshot.merged:
            if snapshot.head_sha == authority.exact_head:
                return DeliveryAcceptanceReconciliationOutcome(
                    change_id=change_id,
                    status=DeliveryAcceptanceReconciliationStatus.WAITING,
                    detail="The pull request is open and not merged.",
                )
            self._reconcile_finalization_head_locked(
                change_id,
                runtime,
                observation=observation,
                acceptance_reason=DeliveryAcceptanceAttentionReason.HEAD_MOVED,
            )
            return DeliveryAcceptanceReconciliationOutcome(
                change_id=change_id,
                status=DeliveryAcceptanceReconciliationStatus.HEAD_MOVED,
                code="ERR_DELIVERY_ACCEPTANCE_HEAD_MOVED",
                detail=(
                    "The open pull request head differed from the finalized Change head; finalization was invalidated."
                ),
            )
        if snapshot.state == "closed" and not snapshot.merged:
            runtime.capture_acceptance_attention(
                observation,
                ("provider pull request is closed without a merge",),
                reason=DeliveryAcceptanceAttentionReason.CLOSED_UNMERGED,
            )
            return DeliveryAcceptanceReconciliationOutcome(
                change_id=change_id,
                status=DeliveryAcceptanceReconciliationStatus.ATTENTION,
                code="ERR_DELIVERY_ACCEPTANCE_ATTENTION",
                detail="The provider pull request is closed without a merge.",
            )
        if not self._acceptance_reconciliation_authority_matches(
            snapshot,
            authority.exact_head,
            authority.ready,
            authority.target_branch,
        ):
            runtime.capture_acceptance_attention(
                observation,
                ("provider acceptance evidence does not match awaiting-merge authority",),
                reason=DeliveryAcceptanceAttentionReason.IDENTITY_MISMATCH,
            )
            return DeliveryAcceptanceReconciliationOutcome(
                change_id=change_id,
                status=DeliveryAcceptanceReconciliationStatus.ATTENTION,
                code="ERR_DELIVERY_ACCEPTANCE_ATTENTION",
                detail="Provider acceptance evidence does not match the finalized Change.",
            )
        return None

    @staticmethod
    def _acceptance_reconciliation_authority_matches(
        snapshot: PublicationPullRequest,
        exact_head: str,
        ready: PullRequestReadyReceipt,
        target_branch: str,
    ) -> bool:
        return (
            snapshot.repository == ready.repository
            and snapshot.number == ready.number
            and snapshot.node_id == ready.node_id
            and snapshot.base_branch == target_branch
            and snapshot.head_sha == ready.head_sha == exact_head
        )

    def _remember_acceptance_observation(self, observation: PublicationPullRequestObservationReceipt) -> None:
        self._publication_observation_cache[observation.change_id] = (
            time.monotonic() + _PUBLICATION_OBSERVATION_CACHE_SECONDS,
            observation.snapshot.head_sha,
            observation,
        )

    @staticmethod
    def _provider_unavailable_outcome(
        change_id: str,
        error: PublicationProviderError,
    ) -> DeliveryAcceptanceReconciliationOutcome:
        return DeliveryAcceptanceReconciliationOutcome(
            change_id=change_id,
            status=DeliveryAcceptanceReconciliationStatus.PROVIDER_UNAVAILABLE,
            code=error.code.value,
            detail=str(error) or error.code.value,
        )

    def abandon_change(self, change_id: str, reason: str) -> DeliveryChangeAbandonment:
        """Record one terminal user abandonment without mutating the user checkout."""
        runtime = self._runtime(change_id, for_mutation=True)
        with locked_roots((self._checkpoint_lock_root(change_id),)):
            abandonment = runtime.abandon_change(reason, _timestamp(self._clock()))
            self._publish_delivery_state(change_id, runtime, f"abandonment-{abandonment.abandonment_id}")
            return abandonment

    def observe_acceptance(self, change_id: str) -> CompletionReceipt:
        """Explicitly observe once, including one bounded read after automatic waiting."""
        runtime = self._runtime(change_id, for_mutation=True)
        with self._engine_checkpoint_lock(change_id):
            existing = runtime.completion_receipt()
            if existing is not None:
                self._publish_delivery_state(change_id, runtime, f"acceptance-{existing.completion_id}")
                return existing
            reservation = self._reserve_acceptance_observation(runtime, explicit=True)
            if not reservation.allowed:
                raise DeliveryAcceptanceWaitingError(reservation.reason_code)
            try:
                receipt = self._observe_acceptance_once(change_id, runtime, attempt_id=reservation.attempt_id)
            except (DeliveryAcceptanceWaitingError, PublicationProviderError, PortfolioApplicationError) as exc:
                runtime.retry_ledger(clock=self._clock).record_failure(
                    reservation, failure_code=getattr(exc, "code", "acceptance-wait"), now=self._clock()
                )
                raise
            runtime.retry_ledger(clock=self._clock).record_accepted_progress(reservation, now=self._clock())
            return receipt

    def _reserve_acceptance_observation(self, runtime: DeliveryRuntime, *, explicit: bool) -> RetryReservation:
        if runtime.change_disposition() is not None:
            message = "Delivery Change requires attention resolution before acceptance observation"
            raise PortfolioApplicationError(message)
        finalization = runtime.finalization()
        if finalization is None or runtime.ready_receipt() is None:
            message = "acceptance observation requires awaiting-merge authority"
            raise PortfolioApplicationError(message)
        key = RetryEpisodeKey.engine(
            runtime.contract.change_id,
            "observe-acceptance",
            finalization.exact_head,
            self._workspace_manager.observed_target_head(),
            finalization.finalization_id,
        )
        ledger = runtime.retry_ledger(clock=self._clock)
        episode = ledger.episode(key)
        return ledger.reserve(
            key,
            failure_class=RetryFailureClass.ACCEPTANCE,
            now=self._clock(),
            automatic=not (explicit and episode is not None and episode.stop_code is RetryStopCode.ACCEPTANCE_WAIT),
        )

    def _observe_acceptance_once(
        self,
        change_id: str,
        runtime: DeliveryRuntime,
        *,
        attempt_id: str,
        observation: PublicationPullRequestObservationReceipt | None = None,
    ) -> CompletionReceipt:
        """Apply one already-reserved observation under the Change checkpoint lock."""
        if self._draft_pull_request_publisher is None:
            message = "draft pull-request publication is not configured"
            raise PortfolioApplicationError(message)
        existing = runtime.completion_receipt()
        if existing is not None:
            self._publish_delivery_state(change_id, runtime, f"acceptance-{existing.completion_id}")
            return existing
        if runtime.change_disposition() is not None:
            message = "Delivery Change requires attention resolution before acceptance observation"
            raise PortfolioApplicationError(message)
        finalization = runtime.finalization()
        ready = runtime.ready_receipt()
        publication = runtime.checkpoint_publication_state()
        if finalization is None or ready is None:
            message = "acceptance observation requires awaiting-merge authority"
            raise PortfolioApplicationError(message)
        if publication.published_head != finalization.exact_head or publication.pending_checkpoint is not None:
            message = "acceptance observation requires the reconciled final checkpoint"
            raise PortfolioApplicationError(message)
        if observation is None:
            observation = self._draft_pull_request_publisher.observe_pull_request(
                ObserveChangePublicationPullRequest(change_id=change_id)
            )
        if observation is None:
            message = "acceptance observation requires a bound pull request"
            raise PortfolioApplicationError(message)
        snapshot = observation.snapshot
        if (
            snapshot.repository != self._draft_pull_request_publisher.repository
            or snapshot.repository != ready.repository
            or snapshot.number != ready.number
            or snapshot.node_id != ready.node_id
            or snapshot.base_branch != self._draft_pull_request_publisher.target_branch
            or snapshot.head_sha != finalization.exact_head
        ):
            runtime.capture_acceptance_attention(
                observation,
                ("provider pull request does not satisfy acceptance authority",),
                reason=DeliveryAcceptanceAttentionReason.IDENTITY_MISMATCH,
            )
            self._publish_attention_best_effort(
                change_id,
                runtime,
                f"acceptance-attention-{observation.observation_id}",
            )
            message = "provider pull request does not satisfy acceptance authority"
            raise PortfolioApplicationError(message)
        self._remember_acceptance_observation(observation)
        latch = self._latch_acceptance_observation(change_id, runtime, observation)
        checks = self._draft_pull_request_publisher.read_check_observations(
            ReadChangePublicationCheckObservations(
                change_id=change_id,
                repository=latch.repository,
                number=latch.number,
                exact_commit=finalization.exact_head,
            )
        )
        receipt = CompletionReceipt.create(
            CompletionEvidence(
                change_id=change_id,
                finalization_receipt_id=finalization.finalization_id,
                finalized_change_head=finalization.exact_head,
                repository_identity=latch.repository,
                pull_request_identity=CompletionPullRequestIdentity(
                    number=latch.number,
                    node_id=latch.node_id,
                ),
                accepted_target_ref=latch.base_branch,
                accepted_merge_commit=latch.accepted_merge_commit,
                merged_at=latch.merged_at,
                acceptance_observation_id=latch.acceptance_observation_id,
                check_observation_ids=tuple(item.observation_id for item in checks),
                review_receipt_ids=(finalization.review.review_id,),
                completed_at=_timestamp(self._clock()),
            )
        )
        completed = runtime.complete_change(
            receipt,
            additional_participants=runtime.retry_ledger(clock=self._clock).owner_result_participants(
                attempt_id, accepted=True, now=receipt.completed_at
            ),
        )
        self._publish_delivery_state(change_id, runtime, f"acceptance-{receipt.completion_id}")
        return completed

    def _latch_acceptance_observation(
        self,
        change_id: str,
        runtime: DeliveryRuntime,
        observation: PublicationPullRequestObservationReceipt,
    ) -> DeliveryMergedPullRequestLatch:
        """Route one fresh provider observation through the immutable merge latch."""
        if runtime.merged_pull_request_latch() is not None:
            try:
                return runtime.latch_merged_pull_request(observation)
            except DeliveryRuntimeConflictError as exc:
                self._publish_attention_best_effort(
                    change_id,
                    runtime,
                    f"acceptance-attention-{observation.observation_id}",
                )
                message = "provider acceptance evidence regressed from the established merged observation"
                raise PortfolioApplicationError(message) from exc
        if is_acceptance_waiting_observation(observation):
            message = "provider pull request is still open and unmerged"
            raise DeliveryAcceptanceWaitingError(message)
        snapshot = observation.snapshot
        if snapshot.state != "closed" or not snapshot.merged:
            runtime.capture_acceptance_attention(
                observation,
                ("provider pull request does not satisfy acceptance authority",),
                reason=DeliveryAcceptanceAttentionReason.CLOSED_UNMERGED,
            )
            self._publish_attention_best_effort(
                change_id,
                runtime,
                f"acceptance-attention-{observation.observation_id}",
            )
            message = "provider pull request does not satisfy acceptance authority"
            raise PortfolioApplicationError(message)
        if snapshot.merge_commit_sha is None or snapshot.merged_at is None:
            runtime.capture_acceptance_attention(
                observation,
                ("provider pull request is missing merge evidence",),
                reason=DeliveryAcceptanceAttentionReason.MERGE_EVIDENCE_MISSING,
            )
            self._publish_attention_best_effort(
                change_id,
                runtime,
                f"acceptance-attention-{observation.observation_id}",
            )
            message = "provider pull request does not satisfy acceptance authority"
            raise PortfolioApplicationError(message)
        return runtime.latch_merged_pull_request(observation)

    def _publish_attention_best_effort(
        self,
        change_id: str,
        runtime: DeliveryRuntime,
        operation_id: str,
    ) -> None:
        try:
            self._publish_delivery_state(change_id, runtime, operation_id)
        except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as exc:
            _logger.warning(
                "Delivery attention publication failed for Change %s (%s): %s",
                change_id,
                operation_id,
                exc,
            )
            return

    def _reconcile_finalization_head_locked(
        self,
        change_id: str,
        runtime: DeliveryRuntime,
        *,
        observation: PublicationPullRequestObservationReceipt | None = None,
        acceptance_reason: DeliveryAcceptanceAttentionReason | None = None,
    ) -> DeliveryFinalizationReceipt | DeliveryFinalizationInvalidationReceipt | None:
        """Retain or invalidate finalization while the Change checkpoint lock is held."""
        if runtime.completion_receipt() is not None:
            finalization = runtime.finalization()
            if finalization is not None:
                self._promote_finalized_external_head(change_id, finalization.exact_head)
            return finalization
        finalization = runtime.finalization()
        ready = runtime.ready_receipt()
        if observation is None:
            observation = (
                None
                if self._draft_pull_request_publisher is None
                else self._draft_pull_request_publisher.observe_pull_request(
                    ObserveChangePublicationPullRequest(change_id=change_id)
                )
            )
        observed_head = (
            self._workspace_manager.observed_change_head(change_id)
            if observation is None
            else observation.snapshot.head_sha
        )
        if (
            finalization is not None
            and ready is not None
            and observation is not None
            and observed_head != finalization.exact_head
        ):
            publisher = self._draft_pull_request_publisher
            if publisher is None:
                self._fail("finalization reconciliation requires a publication provider")
            publisher.return_to_draft(
                ReturnChangePullRequestToDraft(
                    change_id=change_id,
                    operation_id=f"return-draft-{ready.finalization_id}",
                    finalization_id=ready.finalization_id,
                    exact_head=observation.snapshot.head_sha,
                )
            )
            if acceptance_reason is not None:
                runtime.capture_acceptance_attention(
                    observation,
                    ("provider pull request head differs from finalized Change head",),
                    reason=acceptance_reason,
                )
        result = runtime.reconcile_finalization_head(observed_head, _timestamp(self._clock()))
        if isinstance(result, DeliveryFinalizationReceipt):
            self._promote_finalized_external_head(change_id, result.exact_head)
        if not isinstance(result, DeliveryFinalizationInvalidationReceipt) and observation is not None:
            runtime.reconcile_pull_request_draft_state(
                provider_draft=observation.snapshot.draft,
                observed_at=observation.observed_at,
                observation_id=observation.observation_id,
            )
        return result

    def reconcile_finalization_head(
        self,
        change_id: str,
    ) -> DeliveryFinalizationReceipt | DeliveryFinalizationInvalidationReceipt | None:
        """Retain or invalidate finalization from the engine-derived Change branch head."""
        runtime = self._runtime(change_id, for_mutation=True)
        with locked_roots((self._checkpoint_lock_root(change_id),)):
            before_frontier = runtime.frontier_bytes()
            before_coordination = self._workspace_manager.show(change_id)
            result = self._reconcile_finalization_head_locked(change_id, runtime)
            if (
                runtime.frontier_bytes() != before_frontier
                or self._workspace_manager.show(change_id) != before_coordination
            ):
                operation_suffix = (
                    result.invalidation_id
                    if isinstance(result, DeliveryFinalizationInvalidationReceipt)
                    else result.finalization_id
                    if isinstance(result, DeliveryFinalizationReceipt)
                    else "state"
                )
                self._publish_delivery_state(
                    change_id,
                    runtime,
                    f"finalization-reconciliation-{operation_suffix}",
                )
            return result

    def reconcile_change_checkpoint(self, change_id: str) -> DeliveryCheckpointReconciliationResult:
        """Reconcile one durable checkpoint without accepting caller-supplied external fences."""
        if self._change_branch_publisher is None or self._draft_pull_request_publisher is None:
            message = "checkpoint publication is not configured"
            raise PortfolioApplicationError(message)
        runtime = self._runtime(change_id, for_mutation=True)
        with self._engine_checkpoint_lock(change_id):
            current = runtime.checkpoint_publication_state()
            pending = current.pending_checkpoint
            if pending is not None and not _checkpoint_retry_ready(pending, _timestamp(self._clock())):
                return DeliveryCheckpointReconciliationResult(
                    change_id=change_id,
                    attempted_head=pending.head,
                    state=current,
                    reconciled=False,
                    error_code=pending.last_error_code,
                    error_detail=pending.last_error_detail or "Checkpoint retry is waiting for its next eligible time.",
                )
            return self._reconcile_change_checkpoint_with_failure_recording(change_id, runtime)

    def _reconcile_change_checkpoint_with_failure_recording(
        self,
        change_id: str,
        runtime: DeliveryRuntime,
    ) -> DeliveryCheckpointReconciliationResult:
        """Reconcile one checkpoint and retain bounded failure evidence for retries."""
        try:
            return self._reconcile_change_checkpoint(change_id, runtime)
        except (
            PublicationProviderError,
            PublicationBaselineUnavailableError,
            DeliveryRuntimeConflictError,
            OSError,
            RuntimeError,
            subprocess.SubprocessError,
            ValueError,
        ) as exc:
            state = runtime.checkpoint_publication_state()
            pending = state.pending_checkpoint
            if pending is not None:
                with suppress(DeliveryRuntimeConflictError):
                    runtime.record_checkpoint_failure(
                        pending,
                        _timestamp(self._clock()),
                        _checkpoint_error_code(exc),
                        _checkpoint_error_detail(
                            str(exc),
                            "Checkpoint reconciliation failed; the pending checkpoint was retained.",
                        ),
                    )
            raise

    def reconcile_pending_checkpoints(
        self,
        *,
        limit: int = 8,
    ) -> tuple[DeliveryCheckpointReconciliationResult, ...]:
        """Drain a bounded set of pending checkpoints without failing sibling Changes."""
        if self._change_branch_publisher is None or self._draft_pull_request_publisher is None:
            return ()
        if limit < 1:
            message = "checkpoint reconciliation limit must be positive"
            raise ValueError(message)
        self._reconcile_runtimes()
        now = _timestamp(self._clock())
        pending_change_ids = tuple(
            change_id
            for change_id, runtime in sorted(self._runtimes.items())
            if (
                (pending := runtime.checkpoint_publication_state().pending_checkpoint) is not None
                and pending.head is not None
                and not _checkpoint_awaits_review(runtime)
                and _checkpoint_retry_ready(pending, now)
            )
        )[:limit]
        results = []
        for change_id in pending_change_ids:
            runtime = self._runtimes.get(change_id)
            if runtime is None:
                continue
            try:
                with locked_roots((self._checkpoint_lock_root(change_id),), blocking=False):
                    current = runtime.checkpoint_publication_state()
                    pending = current.pending_checkpoint
                    if pending is None or not _checkpoint_retry_ready(pending, now):
                        continue
                    results.append(self._reconcile_change_checkpoint(change_id, runtime))
            except BlockingIOError:
                state = runtime.checkpoint_publication_state()
                results.append(
                    DeliveryCheckpointReconciliationResult(
                        change_id=change_id,
                        state=state,
                        reconciled=False,
                        error_code="ERR_DELIVERY_CHECKPOINT_BUSY",
                        error_detail="Checkpoint reconciliation is already in progress.",
                    )
                )
            except (
                PublicationProviderError,
                PublicationBaselineUnavailableError,
                DeliveryRuntimeConflictError,
                OSError,
                RuntimeError,
                subprocess.SubprocessError,
                ValueError,
            ) as exc:
                state = runtime.checkpoint_publication_state()
                pending = state.pending_checkpoint
                error_code = _checkpoint_error_code(exc)
                error_detail = _checkpoint_error_detail(
                    str(exc),
                    "Checkpoint reconciliation failed; the pending checkpoint was retained.",
                )
                if pending is not None:
                    with suppress(DeliveryRuntimeConflictError):
                        state = runtime.record_checkpoint_failure(
                            pending,
                            now,
                            error_code,
                            error_detail,
                        )
                results.append(
                    DeliveryCheckpointReconciliationResult(
                        change_id=change_id,
                        attempted_head=pending.head if pending else None,
                        state=state,
                        reconciled=False,
                        error_code=error_code,
                        error_detail=error_detail,
                    )
                )
        return tuple(results)

    def _reconcile_change_checkpoint(  # noqa: C901
        self,
        change_id: str,
        runtime: DeliveryRuntime,
    ) -> DeliveryCheckpointReconciliationResult:
        initial = runtime.checkpoint_publication_state()
        pending = initial.pending_checkpoint
        if pending is None:
            finalization = runtime.finalization()
            if finalization is not None and initial.published_head != finalization.exact_head:
                raise DeliveryRuntimeReconciliationError(
                    change_id,
                    "published checkpoint does not match the finalized Change head; "
                    "reconcile finalization before retrying publication",
                )
            return DeliveryCheckpointReconciliationResult(
                change_id=change_id,
                attempted_head=None,
                state=initial,
                reconciled=True,
            )
        if pending.head is None:
            return DeliveryCheckpointReconciliationResult(
                change_id=change_id,
                attempted_head=None,
                state=initial,
                reconciled=False,
                error_code=_CHECKPOINT_MISSING_HEAD_ERROR_CODE,
                error_detail=(
                    "Checkpoint publication is waiting for a reviewed Change head after authority invalidation."
                ),
            )

        target_sync = runtime.target_sync_receipt()
        if target_sync is not None and target_sync.review_required and runtime.finalization() is None:
            return DeliveryCheckpointReconciliationResult(
                change_id=change_id,
                attempted_head=None,
                state=initial,
                reconciled=False,
                error_code=_CHECKPOINT_REVIEW_ERROR_CODE,
                error_detail="Checkpoint publication awaits fresh finalization review after target synchronization.",
            )

        head = pending.head
        try:
            automation_paths = self._workspace_manager.repository_automation_paths(change_id, head)
        except PublicationBaselineUnavailableError:
            with suppress(DeliveryRuntimeConflictError):
                runtime.capture_publication_attention(
                    _timestamp(self._clock()),
                    ("publication-baseline-unavailable", f"exact-head:{head}"),
                )
            raise
        prepared = self._prepare_checkpoint_head(
            change_id,
            runtime,
            initial,
            pending,
        )
        if prepared.finalization_invalidated:
            return DeliveryCheckpointReconciliationResult(
                change_id=change_id,
                attempted_head=prepared.head,
                state=prepared.state,
                reconciled=False,
            )
        initial = prepared.state
        pending = prepared.pending
        head = prepared.head
        first_checkpoint = prepared.first_checkpoint
        package = self._package_store.read_verified(change_id)
        self._validate_package_authority(runtime, package)
        summary = _checkpoint_summary(runtime, package, pending, head, automation_paths)
        pull_request_title = _checkpoint_pull_request_title(runtime)
        branch_receipt = self._publish_checkpoint_branch(change_id, initial, head)
        if initial.published_head != head:
            state = runtime.record_checkpoint_branch_publication(initial, branch_receipt.published_head)
        else:
            state = runtime.checkpoint_publication_state()

        current = state.pending_checkpoint
        if current is None or current.head is None or not set(pending.triggers) <= set(current.triggers):
            return DeliveryCheckpointReconciliationResult(
                change_id=change_id,
                attempted_head=head,
                branch_publication=branch_receipt,
                state=state,
                reconciled=False,
            )

        draft_receipt = None
        if first_checkpoint:
            draft_receipt = self._draft_pull_request_publisher.publish(
                CreateOrReconcileDraftPullRequest(
                    change_id=change_id,
                    operation_id=_checkpoint_operation_id("pull-request", change_id, head, summary),
                    published_head=head,
                    title=pull_request_title,
                    generated_summary=summary,
                )
            )
            runtime.record_publication_identity(
                DeliveryChangePublicationIdentity(
                    change_id=draft_receipt.change_id,
                    repository=draft_receipt.repository,
                    number=draft_receipt.number,
                    node_id=draft_receipt.node_id,
                    head_sha=draft_receipt.head_sha,
                )
            )
        summary_receipt = self._draft_pull_request_publisher.update_generated_summary(
            UpdateGeneratedPullRequestSummary(
                change_id=change_id,
                operation_id=_checkpoint_operation_id("summary", change_id, head, summary),
                published_head=head,
                generated_summary=summary,
            )
        )
        history = runtime.publication_history()
        if history is not None:
            runtime.record_publication_identity(
                history.current.model_copy(
                    update={
                        "repository": summary_receipt.repository,
                        "number": summary_receipt.number,
                        "head_sha": summary_receipt.head_sha,
                    }
                )
            )
        self._publish_delivery_state(
            change_id,
            runtime,
            _checkpoint_operation_id("state", change_id, head),
        )
        state = runtime.checkpoint_publication_state()
        if state.pending_checkpoint is not None and state.published_head == head:
            state = runtime.acknowledge_checkpoint_publication(pending, head)
        return DeliveryCheckpointReconciliationResult(
            change_id=change_id,
            attempted_head=head,
            branch_publication=branch_receipt,
            draft_pull_request=draft_receipt,
            generated_summary=summary_receipt,
            state=state,
            reconciled=state.pending_checkpoint is None,
        )

    def _publish_checkpoint_branch(
        self,
        change_id: str,
        checkpoint: DeliveryCheckpointPublicationState,
        head: str,
    ) -> ChangeBranchPublicationReceipt:
        """Publish one exact checkpoint head through the managed Change branch."""
        publisher = self._change_branch_publisher
        if publisher is None:
            self._fail("Change branch publication is not configured")
        pending = checkpoint.pending_checkpoint
        if pending is None or pending.head != head:
            self._fail("Change branch publication does not match the pending checkpoint")
        return publisher.publish(
            PublishChangeBranch(
                change_id=change_id,
                expected_remote_head=checkpoint.published_head,
                expected_published_head=head,
                operation_id=_checkpoint_operation_id("branch", change_id, head),
            )
        )

    def _publish_target_sync_branch(
        self,
        change_id: str,
        runtime: DeliveryRuntime,
        merged_head: str,
    ) -> ChangeBranchPublicationReceipt | None:
        """Publish a target-sync head before its portable Delivery snapshot."""
        if self._change_branch_publisher is None:
            return None
        checkpoint = runtime.checkpoint_publication_state()
        branch_receipt = self._publish_checkpoint_branch(change_id, checkpoint, merged_head)
        runtime.record_checkpoint_branch_publication(checkpoint, branch_receipt.published_head)
        return branch_receipt

    @staticmethod
    def _acknowledge_published_target_sync_checkpoint(runtime: DeliveryRuntime, published_head: str) -> None:
        checkpoint = runtime.checkpoint_publication_state()
        pending = checkpoint.pending_checkpoint
        if pending is not None and pending.head == published_head and checkpoint.published_head == published_head:
            runtime.acknowledge_checkpoint_publication(pending, published_head)

    def _prepare_checkpoint_head(
        self,
        change_id: str,
        runtime: DeliveryRuntime,
        initial: DeliveryCheckpointPublicationState,
        pending: DeliveryPendingCheckpoint,
    ) -> _PreparedCheckpointHead:
        """Prepare the exact first checkpoint head and its pull-request boundary."""
        first_checkpoint = any(
            trigger.kind
            in {
                DeliveryCheckpointTriggerKind.ADMITTED_DESIGN,
                DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK,
            }
            for trigger in pending.triggers
        )
        first_task_checkpoint = any(
            trigger.kind == DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK for trigger in pending.triggers
        )
        if first_task_checkpoint and initial.published_head is None:
            package = self._package_store.read_verified(change_id)
            self._validate_package_authority(runtime, package)
            snapshot = self._workspace_manager.snapshot_design_package(
                change_id,
                package.package_id,
                {
                    "authority.json": package.authority_bytes,
                    "design.md": package.design_bytes,
                    "intent.md": package.intent_bytes,
                    "manifest.json": package.manifest.canonical_bytes(),
                },
                _checkpoint_operation_id("package", change_id, pending.head, package.package_id),
            )
            if snapshot.snapshot_head != pending.head:
                runtime.record_design_package_snapshot(initial, snapshot)
                initial = runtime.checkpoint_publication_state()
                pending = initial.pending_checkpoint
                if pending is None or pending.head is None:
                    self._fail("Design package snapshot removed the pending checkpoint")
                if runtime.finalization() is not None:
                    runtime.reconcile_finalization_head(snapshot.snapshot_head, _timestamp(self._clock()))
                    return _PreparedCheckpointHead(
                        state=runtime.checkpoint_publication_state(),
                        pending=pending,
                        head=snapshot.snapshot_head,
                        first_checkpoint=first_checkpoint,
                        finalization_invalidated=True,
                    )
        if pending.head is None:
            self._fail("checkpoint preparation removed the pending head")
        return _PreparedCheckpointHead(
            state=initial,
            pending=pending,
            head=pending.head,
            first_checkpoint=first_checkpoint,
        )

    def read_design_session(self, change_id: str) -> VerifiedDesignPackage:
        """Return one verified authored Design package and its current identity."""
        return self._package_store.read_verified(change_id)

    def revise_design_session(
        self,
        change_id: str,
        expected_package_id: str,
        intent_bytes: bytes,
        design_bytes: bytes,
    ) -> VerifiedDesignPackage:
        """Replace authored Design bytes for one exact package identity."""
        self._reconcile_runtimes()
        runtime = self._runtimes.get(change_id)
        if runtime is not None and not self._admitted_design_revision_allowed(runtime):
            self._fail("admitted Delivery Changes cannot revise their Design package")
        return self._package_store.revise(change_id, expected_package_id, intent_bytes, design_bytes)

    @staticmethod
    def _admitted_design_revision_allowed(runtime: DeliveryRuntime) -> bool:
        """Allow revision only for a quiescent Change with an explicit Design return."""
        return (
            runtime.change_stage() is DeliveryChangeStage.DESIGN
            and any(binding.stage is DeliveryStage.DESIGN for binding in runtime.bindings())
            and not runtime.active_claims()
            and runtime.change_disposition() is None
            and runtime.integration_repair_claim() is None
            and runtime.finalization() is None
        )

    def publish_design_checkpoint(self, change_id: str) -> DesignCheckpointResult:
        """Checkpoint one verified active package without touching product refs."""
        return self._package_store.checkpoint(change_id)

    def derive_delivery_contract(self, change_id: str) -> DeliveryCompilationResult:
        """Compile one verified package without publishing generated authority."""
        package = self._package_store.read_verified(change_id)
        return compile_delivery_contract(change_id, package.intent_bytes, package.design_bytes)

    def admit_delivery_change(self, request: DeliveryAdmissionRequest) -> DeliveryAdmissionResult:
        """Admit source-bound Delivery authority through the owning registry."""
        self._reconcile_runtimes()
        with self._coordinator.acquisition_lock():
            self._workspace_manager.validate_recovery(request.change_id, request.recovery_reviewed_head)
            result = self._authority_registry.admit(request)
            self._workspace_manager.ensure(
                request.change_id,
                recovery_reviewed_head=request.recovery_reviewed_head,
            )
            runtime = DeliveryRuntime(
                self._target_root,
                result.contract,
                workspace_manager=self._workspace_manager,
            )
            with self._runtime_reconciliation_lock:
                self._runtimes = {**self._runtimes, request.change_id: runtime}
            package = self._package_store.read_verified(request.change_id)
            self._validate_package_authority(runtime, package)
            snapshot = self._workspace_manager.snapshot_design_package(
                request.change_id,
                package.package_id,
                {
                    "authority.json": package.authority_bytes,
                    "design.md": package.design_bytes,
                    "intent.md": package.intent_bytes,
                    "manifest.json": package.manifest.canonical_bytes(),
                },
                _checkpoint_operation_id("package", request.change_id, package.package_id),
                request.expected_design_package_snapshot_receipt_id,
            )
            checkpoint = runtime.checkpoint_publication_state()
            if checkpoint.pending_checkpoint is not None:
                runtime.record_design_package_snapshot(checkpoint, snapshot)
            elif checkpoint.published_head is not None and checkpoint.published_head != snapshot.snapshot_head:
                runtime.queue_explicit_checkpoint(snapshot.snapshot_head)
            else:
                runtime.queue_admitted_design_checkpoint(snapshot.snapshot_head)
            if self._change_branch_publisher is not None and self._draft_pull_request_publisher is not None:
                self._reconcile_change_checkpoint(request.change_id, runtime)
            self._reconcile_runtimes()
            return result.model_copy(
                update={"frontier": DeliveryFrontier.model_validate_json(runtime.frontier_bytes(), strict=False)}
            )

    def admit_change(self, request: DeliveryAdmissionRequest) -> DeliveryAdmissionResult:
        """Admit one exact approved Design version as executable Delivery authority."""
        return self.admit_delivery_change(request)

    def publish_delivery_plan(
        self,
        change_id: str,
        request: PublishDeliveryPlan,
    ) -> DeliveryPlanCandidate:
        """Publish one validated Planning candidate through its exact runtime."""
        runtime = self._runtime(change_id, for_mutation=True)
        return runtime.publish_plan(request)

    def publish_delivery_result(
        self,
        change_id: str,
        request: PublishDeliveryResult,
    ) -> DeliveryResultCandidate:
        """Publish one validated Build result through its exact runtime."""
        runtime = self._runtime(change_id, for_mutation=True)
        return runtime.publish_result(request)

    def transition_delivery(
        self,
        change_id: str,
        request: DeliveryTransition,
    ) -> OutcomeAuthorityBinding:
        """Apply one validated mechanical transition through its exact runtime."""
        runtime = self._runtime(change_id, for_mutation=True)
        with locked_roots((self._checkpoint_lock_root(change_id),)):
            self._import_legacy_worker_budgets(runtime)
            binding = runtime.transition(request, retry_observed_at=self._clock())
            if request.action == "advance":
                self._record_worker_retry_success(runtime, request.outcome_id, request.claim_id)
            elif request.action in {"block", "return"}:
                with suppress(OSError, RuntimeError, ValueError):
                    ledger = runtime.retry_ledger(clock=self._clock)
                    attempt_id = ledger.attempt_for_operation(request.claim_id)
                    if attempt_id is not None:
                        ledger.record_failure(
                            attempt_id,
                            failure_code="worker-returned" if request.action == "return" else "worker-blocked",
                            now=self._clock(),
                        )
            self._publish_delivery_state(
                change_id,
                runtime,
                _checkpoint_operation_id("transition", change_id, request.outcome_id, request.claim_id),
            )
            return binding

    def list_integration_attention(self) -> tuple[DeliveryIntegrationAttentionStatus, ...]:
        """List non-retryable Integration attention in stable identity order."""
        return self._integration_attention_statuses(self._portfolio_snapshots())

    def _integration_attention_statuses(
        self,
        snapshots: tuple[DeliveryPortfolioSnapshot, ...],
    ) -> tuple[DeliveryIntegrationAttentionStatus, ...]:
        """Project Integration attention from an already captured portfolio."""
        statuses = []
        for snapshot in snapshots:
            attention = snapshot.frontier.integration_attention
            if (
                attention is None
                or snapshot.frontier.integration_repair_claim is not None
                or self._integration_attention_is_superseded(snapshot.contract.change_id, attention)
            ):
                continue
            disposition = integration_attention_disposition(attention.code)
            if disposition == DeliveryIntegrationAttentionDisposition.RETRYABLE:
                continue
            statuses.append(
                DeliveryIntegrationAttentionStatus(
                    change_id=snapshot.contract.change_id,
                    code=attention.code,
                    disposition=disposition,
                    retry_condition=attention.retry_condition,
                )
            )
        return tuple(statuses)

    def _integration_attention_is_superseded(
        self,
        change_id: str,
        attention: DeliveryIntegrationAttention,
    ) -> bool:
        try:
            context = self._workspace_manager.integration_context(change_id)
        except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as exc:
            self._fail(f"current Integration target is unavailable for {change_id}", exc)
        return attention.target_head != context.target_head

    def show_integration_attention(self, change_id: str) -> DeliveryIntegrationAttention | None:
        """Return current typed Integration attention without mutating runtime state."""
        return self._runtime(change_id).integration_attention()

    def list_work_items(self) -> tuple[WorkItemProjection, ...]:
        """List bounded work-item projections in stable portfolio order."""
        projections = []
        for snapshot in self._portfolio_snapshots():
            if snapshot.contract.change_id in self._runtime_reconciliation_errors:
                continue
            if not self._is_work_portfolio_visible(snapshot):
                continue
            projections.extend(WorkItemProjector(snapshot).list_items())
        return tuple(
            sorted(
                projections,
                key=lambda item: (
                    item.stage.value == "completed",
                    item.change_id,
                    item.work_item_id,
                ),
            )
        )

    def list_work_item_groups(self) -> tuple[ChangeGroupView, ...]:
        """List grouped Cockpit views from exact per-change snapshots."""
        return tuple(
            self._read_projector(snapshot).group_view()
            for snapshot in self._portfolio_snapshots()
            if snapshot.contract.change_id not in self._runtime_reconciliation_errors
            if self._is_work_portfolio_visible(snapshot)
        )

    def list_changes(self) -> PortfolioReadView:
        """Return current grouped Change state and operating guidance."""
        return self.portfolio_read_view()

    def portfolio_read_view(self) -> PortfolioReadView:
        """Return grouped work and operating facts from one immutable capture."""
        snapshots = self._portfolio_snapshots()
        groups = tuple(
            self._read_projector(snapshot).group_view()
            for snapshot in snapshots
            if snapshot.contract.change_id not in self._runtime_reconciliation_errors
            if self._is_work_portfolio_visible(snapshot)
        )
        return PortfolioReadView(
            groups=groups,
            operating=self._portfolio_operating_view(snapshots, groups),
            health=self._delivery_health_view(inspect_workspaces=False),
            unavailable_changes=tuple(
                self._unavailable_change(change_id)
                for change_id, observation in sorted(self._discovered_changes.items())
                if not observation.actionable_runtime or change_id in self._runtime_reconciliation_errors
            ),
        )

    def portfolio_operating_view(self) -> PortfolioOperatingView:
        """Return portfolio-wide operating facts and advisory session guidance."""
        snapshots = self._portfolio_snapshots()
        groups = tuple(
            WorkItemProjector(snapshot).group_view()
            for snapshot in snapshots
            if snapshot.contract.change_id not in self._runtime_reconciliation_errors
            if self._is_work_portfolio_visible(snapshot)
        )
        return self._portfolio_operating_view(snapshots, groups)

    def delivery_health(self, change_id: str | None = None) -> DeliveryHealthView:
        """Return bounded diagnostics for state excluded from Delivery authority."""
        self._reconcile_runtimes()
        return self._delivery_health_view(scoped_change_id=change_id)

    def repair_delivery_state_snapshot(
        self,
        change_id: str,
        operation_id: str,
        *,
        confirmed_repair: Literal[True],
    ) -> DeliveryStateSnapshotRepairReceipt:
        """Publish one explicitly confirmed local block successor over a stale snapshot."""
        if confirmed_repair is not True:
            self._fail("Delivery-state snapshot repair requires explicit confirmation")
        publisher = self._delivery_state_publisher
        if publisher is None:
            self._fail("Delivery-state snapshot repair requires a configured state publisher")
        self._reconcile_runtimes()
        with locked_roots((self._checkpoint_lock_root(change_id),)):
            inventory = publisher.read_snapshot_inventory()
            snapshot = next((item for item in inventory.snapshots if item.change_id == change_id), None)
            if snapshot is None or inventory.remote_head is None:
                self._fail("Delivery-state snapshot repair requires the current remote snapshot")
            runtime = self._runtimes.get(change_id)
            if runtime is None:
                runtime = DeliveryRuntime(
                    self._target_root,
                    snapshot.contract,
                    workspace_manager=self._workspace_manager,
                )
            diagnostics = tuple(
                diagnostic
                for diagnostic in self._startup_health_diagnostics
                if (
                    diagnostic.source == "remote-state"
                    and diagnostic.code == "remote-state-reconciliation-required"
                    and diagnostic.change_id == change_id
                    and diagnostic.reason is DeliveryHealthReason.LOCAL_FRONTIER_MISMATCH
                )
            )
            frontier_bytes = runtime.frontier_bytes()
            frontier = DeliveryFrontier.model_validate_json(frontier_bytes, strict=False)
            if not diagnostics:
                self._fail("Delivery-state snapshot repair diagnostic is absent or incompatible")
            if not self._is_repairable_frontier_successor(snapshot.frontier, frontier):
                self._fail("Delivery-state snapshot repair successor is outside the allowed block shape")
            publication = self._publish_delivery_state(
                change_id,
                runtime,
                operation_id,
                expected_remote_head=inventory.remote_head,
            )
            if publication is None:
                self._fail("Delivery-state snapshot repair did not produce a publication receipt")
            self._clear_remote_state_reconciliation(change_id)
            return DeliveryStateSnapshotRepairReceipt.create(
                operation_id=operation_id,
                change_id=change_id,
                publication=publication,
                local_frontier_digest=hashlib.sha256(frontier_bytes).hexdigest(),
            )

    def repair_stranded_frontier(
        self,
        change_id: str,
        request_id: str,
        expected_frontier_digest: str,
        operation_id: str,
        *,
        confirmed_repair: Literal[True],
    ) -> DeliveryStrandedFrontierRepairReceipt:
        """Repair one confirmed legacy request-provenance defect with CAS fencing."""
        if confirmed_repair is not True:
            self._fail("stranded frontier repair requires explicit confirmation")
        frontier_path = self._target_root / "changes" / change_id / "frontier.json"
        history_relative = Path("changes") / change_id / "revisions" / expected_frontier_digest / "frontier.json"
        history_path = self._target_root / history_relative
        with self._coordinator.acquisition_lock(), locked_roots((self._checkpoint_lock_root(change_id),)):
            try:
                current_bytes = frontier_path.read_bytes()
            except OSError as exc:
                self._fail("stranded frontier repair requires the current frontier", exc)
            current_digest = hashlib.sha256(current_bytes).hexdigest()
            if current_digest != expected_frontier_digest:
                if not history_path.is_file():
                    self._fail("Delivery frontier changed before stranded frontier repair")
                history_bytes = history_path.read_bytes()
                if hashlib.sha256(history_bytes).hexdigest() != expected_frontier_digest:
                    self._fail("stranded frontier repair history does not match the expected frontier")
                _frontier, repaired_bytes = repair_missing_request_provenance(history_bytes, request_id)
                if current_bytes != repaired_bytes:
                    self._fail("stranded frontier repair predecessor is not the expected repaired successor")
                return DeliveryStrandedFrontierRepairReceipt.create(
                    operation_id=operation_id,
                    change_id=change_id,
                    request_id=request_id,
                    previous_frontier_digest=expected_frontier_digest,
                    frontier_digest=hashlib.sha256(repaired_bytes).hexdigest(),
                    preserved_frontier_path=history_relative.as_posix(),
                )

            _frontier, repaired_bytes = repair_missing_request_provenance(current_bytes, request_id)
            if history_path.exists() and history_path.read_bytes() != current_bytes:
                self._fail("stranded frontier repair history already contains different evidence")
            participants: list[TransactionParticipant | ReplacementTransactionParticipant] = []
            if not history_path.exists():
                participants.append(TransactionParticipant(self._target_root, history_relative, current_bytes))
            participants.append(
                ReplacementTransactionParticipant(
                    self._target_root,
                    frontier_path.relative_to(self._target_root),
                    current_bytes,
                    repaired_bytes,
                )
            )
            pending_path = frontier_path.with_name("state-publication.json")
            pending_bytes = _canonical_model_bytes(
                DeliveryPendingStatePublication.pending(
                    expected_frontier_digest,
                    hashlib.sha256(repaired_bytes).hexdigest(),
                )
            )
            if pending_path.exists():
                participants.append(
                    ReplacementTransactionParticipant(
                        self._target_root,
                        pending_path.relative_to(self._target_root),
                        pending_path.read_bytes(),
                        pending_bytes,
                    )
                )
            else:
                participants.append(
                    TransactionParticipant(
                        self._target_root,
                        pending_path.relative_to(self._target_root),
                        pending_bytes,
                    )
                )
            RuntimeTransaction(
                self._target_root,
                f"delivery-stranded-frontier-repair-{change_id}-{expected_frontier_digest}",
                tuple(participants),
            ).commit()
            self._reconcile_runtimes()
            return DeliveryStrandedFrontierRepairReceipt.create(
                operation_id=operation_id,
                change_id=change_id,
                request_id=request_id,
                previous_frontier_digest=expected_frontier_digest,
                frontier_digest=hashlib.sha256(repaired_bytes).hexdigest(),
                preserved_frontier_path=history_relative.as_posix(),
            )

    def propose_quarantined_delivery_state_snapshot_repair(
        self,
        change_id: str,
    ) -> DeliveryQuarantinedSnapshotRepairProposal:
        """Return exact fences for one known quarantined remote snapshot."""
        publisher = self._delivery_state_publisher
        if publisher is None:
            self._fail("quarantined snapshot repair requires a configured state publisher")
        inventory = publisher.read_snapshot_inventory()
        diagnostics = tuple(
            item
            for item in inventory.diagnostics
            if item.change_id == change_id
            and item.code in {"snapshot-invalid", "snapshot-identity-invalid"}
            and item.raw_digest is not None
        )
        if inventory.remote_head is None or len(diagnostics) != 1:
            self._fail("no uniquely repairable quarantined remote snapshot exists")
        diagnostic = diagnostics[0]
        if diagnostic.raw_digest is None:
            self._fail("quarantined remote snapshot has no raw-byte fence")
        return DeliveryQuarantinedSnapshotRepairProposal(
            change_id=change_id,
            diagnostic_code=diagnostic.code,
            expected_remote_head=inventory.remote_head,
            snapshot_digest=diagnostic.raw_digest,
            consequence="Replace the quarantined predecessor with a fresh snapshot from validated local authority.",
        )

    def repair_quarantined_delivery_state_snapshot(  # noqa: PLR0913 - repair binds each exact authority fence.
        self,
        change_id: str,
        operation_id: str,
        *,
        confirmed_repair: Literal[True],
        expected_remote_head: str,
        expected_snapshot_digest: str,
        expected_diagnostic_code: Literal["snapshot-invalid", "snapshot-identity-invalid"],
    ) -> DeliveryQuarantinedSnapshotRepairReceipt:
        """Replace one known invalid remote snapshot from validated local authority."""
        if confirmed_repair is not True:
            self._fail("quarantined snapshot repair requires explicit confirmation")
        publisher = self._delivery_state_publisher
        if publisher is None:
            self._fail("quarantined snapshot repair requires a configured state publisher")
        self._reconcile_runtimes()
        with self._coordinator.acquisition_lock(), locked_roots((self._checkpoint_lock_root(change_id),)):
            inventory = publisher.read_snapshot_inventory()
            diagnostic = next(
                (
                    item
                    for item in inventory.diagnostics
                    if item.change_id == change_id
                    and item.code == expected_diagnostic_code
                    and item.raw_digest == expected_snapshot_digest
                ),
                None,
            )
            if diagnostic is None and inventory.remote_head == expected_remote_head:
                self._fail("expected quarantined remote snapshot diagnostic is absent")
            change_diagnostics = tuple(item for item in self._startup_health_diagnostics if item.change_id == change_id)
            if len(change_diagnostics) != 1 or not (
                change_diagnostics[0].source == "remote-state"
                and change_diagnostics[0].code == expected_diagnostic_code
            ):
                self._fail("quarantined remote snapshot repair has unrelated Change diagnostics")
            runtime = self._runtimes.get(change_id)
            if runtime is None:
                detail = self._runtime_reconciliation_errors.get(change_id)
                if detail is not None:
                    raise DeliveryRuntimeReconciliationError(change_id, detail)
                self._fail(f"Delivery runtime is absent: {change_id}")
            package = self._package_store.read_verified(change_id)
            self._validate_package_authority(runtime, package)
            admission_path = self._target_root / "changes" / change_id / "admission.json"
            admission = DeliveryAdmissionReceipt.model_validate_json(admission_path.read_bytes())
            publication = publisher.repair_quarantined_snapshot(
                change_id=change_id,
                package_id=package.package_id,
                coordination=self._workspace_manager.show(change_id),
                runtime=runtime,
                admission=admission,
                operation_id=operation_id,
                captured_at=_timestamp(self._clock()),
                expected_remote_head=expected_remote_head,
                expected_snapshot_digest=expected_snapshot_digest,
                expected_diagnostic_code=expected_diagnostic_code,
            )
            runtime.acknowledge_pending_publication(hashlib.sha256(runtime.frontier_bytes()).hexdigest())
            self._clear_remote_state_reconciliation(change_id)
            return DeliveryQuarantinedSnapshotRepairReceipt.create(
                operation_id=operation_id,
                change_id=change_id,
                invalid_snapshot_digest=expected_snapshot_digest,
                expected_remote_head=expected_remote_head,
                publication=publication,
                diagnostic_code=expected_diagnostic_code,
            )

    def recover_out_of_band_head(  # noqa: C901, PLR0912, PLR0913 - recovery binds exact Delivery and Git fences.
        self,
        change_id: str,
        expected_reviewed_head: str,
        expected_remote_head: str,
        expected_branch_head: str,
        operation_id: str,
        *,
        confirmed_recovery: Literal[True],
    ) -> OutOfBandHeadRecoveryReceipt:
        """Preserve an out-of-band head and reconcile the reviewed Change checkpoint."""
        if confirmed_recovery is not True:
            self._fail("out-of-band head recovery requires explicit confirmation")
        if (
            self._change_branch_publisher is None
            or self._delivery_state_publisher is None
            or self._draft_pull_request_publisher is None
        ):
            self._fail("out-of-band head recovery requires configured checkpoint publishers")
        self._reconcile_runtimes()
        with locked_roots((self._checkpoint_lock_root(change_id),)):
            runtime = self._runtimes.get(change_id)
            if runtime is None:
                self._fail("out-of-band head recovery requires an available Change runtime")
            diagnostic = next(
                (
                    item
                    for item in self._startup_health_diagnostics
                    if (
                        item.source == "remote-state"
                        and item.change_id == change_id
                        and item.code == "remote-state-reconciliation-required"
                        and item.reason is DeliveryHealthReason.REMOTE_CHANGE_HEAD_MISMATCH
                        and item.expected_head == expected_reviewed_head
                        and item.observed_head == expected_remote_head
                    )
                ),
                None,
            )
            if diagnostic is None:
                self._fail("out-of-band head recovery diagnostic is absent or stale")
            checkpoint = runtime.checkpoint_publication_state()
            if checkpoint.published_head != expected_remote_head:
                self._fail("out-of-band head recovery remote checkpoint changed")
            coordination = self._workspace_manager.show(change_id)
            if coordination.last_reviewed_commit != expected_reviewed_head:
                self._fail("out-of-band head recovery reviewed boundary changed")
            if runtime.active_claims() or runtime.integration_repair_claim() is not None:
                self._fail("out-of-band head recovery cannot overlap active Delivery work")
            if runtime.finalization() is not None or runtime.change_disposition() is not None:
                self._fail("out-of-band head recovery requires an unresolved nonterminal Change")
            if self._workspace_manager.observed_change_head(change_id) != expected_branch_head:
                self._fail("out-of-band head recovery branch head changed")
            try:
                observed_remote_head = self._change_branch_publisher.observe_remote_head(change_id)
            except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as exc:
                self._fail("out-of-band Change head recovery could not observe the remote branch", exc)
            if observed_remote_head != expected_remote_head:
                self._fail("out-of-band Change head recovery remote branch changed")
            request = RecoverOutOfBandHead(
                change_id=change_id,
                expected_reviewed_head=expected_reviewed_head,
                expected_remote_head=expected_remote_head,
                expected_branch_head=expected_branch_head,
                operation_id=operation_id,
            )
            try:
                receipt = self._workspace_manager.recover_out_of_band_head(request)
            except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as exc:
                self._fail("out-of-band Change head recovery could not complete", exc)
            runtime.queue_explicit_checkpoint(expected_reviewed_head)
            result = self._reconcile_change_checkpoint_with_failure_recording(change_id, runtime)
            if not result.reconciled:
                self._fail("out-of-band Change head recovery checkpoint remains unreconciled")
            self._clear_remote_state_reconciliation(change_id)
            return receipt

    def repair_target_sync_publication(  # noqa: PLR0913 - repair binds each exact remote and target identity.
        self,
        change_id: str,
        expected_remote_head: str,
        expected_merged_head: str,
        target_sync_operation_id: str,
        operation_id: str,
        *,
        confirmed_repair: Literal[True],
    ) -> DeliveryTargetSyncRepairReceipt:
        """Reconcile one quarantined target-sync head through Delivery-owned publication."""
        if confirmed_repair is not True:
            self._fail("target-sync publication repair requires explicit confirmation")
        if self._change_branch_publisher is None or self._delivery_state_publisher is None:
            self._fail("target-sync publication repair requires configured publishers")
        self._reconcile_runtimes()
        with locked_roots((self._checkpoint_lock_root(change_id),)):
            runtime = self._target_sync_repair_runtime(
                change_id,
                expected_remote_head,
                expected_merged_head,
                target_sync_operation_id,
            )
            branch_receipt = self._publish_target_sync_branch(change_id, runtime, expected_merged_head)
            if branch_receipt is None:
                self._fail("target-sync publication repair could not publish the Change branch")
            checkpoint = runtime.checkpoint_publication_state()
            pending = checkpoint.pending_checkpoint
            self._publish_delivery_state(change_id, runtime, f"target-sync-repair-{operation_id}")
            if pending is not None and runtime.checkpoint_publication_state().pending_checkpoint is not None:
                runtime.acknowledge_checkpoint_publication(pending, branch_receipt.published_head)
            self._clear_target_sync_reconciliation(change_id)
            target_sync = runtime.target_sync_receipt()
            if target_sync is None:
                self._fail("target-sync publication repair lost target-sync authority")
            return DeliveryTargetSyncRepairReceipt.create(
                operation_id=operation_id,
                change_id=change_id,
                target_sync_operation_id=target_sync_operation_id,
                target_branch=target_sync.integration_target,
                target_head=target_sync.target_head,
                expected_remote_head=expected_remote_head,
                repaired_head=branch_receipt.published_head,
            )

    def _target_sync_repair_runtime(
        self,
        change_id: str,
        expected_remote_head: str,
        expected_merged_head: str,
        target_sync_operation_id: str,
    ) -> DeliveryRuntime:
        runtime = self._runtimes.get(change_id)
        if runtime is None:
            self._fail("target-sync publication repair requires an available Change runtime")
        reconciliation_error = self._runtime_reconciliation_errors.get(change_id)
        matching_diagnostics = tuple(
            diagnostic
            for diagnostic in self._startup_health_diagnostics
            if (
                diagnostic.source == "remote-state"
                and diagnostic.code == "remote-state-reconciliation-required"
                and diagnostic.change_id == change_id
                and (
                    diagnostic.reason is DeliveryHealthReason.REMOTE_CHANGE_HEAD_MISMATCH
                    or diagnostic.reason is DeliveryHealthReason.LOCAL_FRONTIER_MISMATCH
                )
            )
        )
        if reconciliation_error is not None and not matching_diagnostics:
            self._fail("target-sync publication repair diagnostic is absent or incompatible")
        if any(
            diagnostic.source == "remote-state"
            and diagnostic.change_id == change_id
            and diagnostic.code == "remote-state-reconciliation-required"
            and diagnostic not in matching_diagnostics
            for diagnostic in self._startup_health_diagnostics
        ):
            self._fail("target-sync publication repair diagnostic is absent or incompatible")
        target_sync = runtime.target_sync_receipt()
        if (
            target_sync is None
            or not target_sync.review_required
            or target_sync.operation_id != target_sync_operation_id
            or target_sync.merged_head != expected_merged_head
        ):
            self._fail("target-sync publication repair does not match current target-sync authority")
        coordination = self._workspace_manager.show(change_id)
        checkpoint = runtime.checkpoint_publication_state()
        if (
            coordination.last_reviewed_commit != expected_merged_head
            or checkpoint.published_head not in {expected_remote_head, expected_merged_head}
            or checkpoint.pending_checkpoint is None
            or checkpoint.pending_checkpoint.head != expected_merged_head
            or runtime.finalization() is not None
            or runtime.change_disposition() is not None
            or runtime.active_claims()
            or runtime.integration_repair_claim() is not None
        ):
            self._fail("target-sync publication repair authority has changed")
        if self._workspace_manager.source_head(change_id) != expected_merged_head:
            self._fail("target-sync publication repair local head differs from the expected merge")
        return runtime

    @staticmethod
    def _is_repairable_frontier_successor(  # noqa: PLR0911
        snapshot: DeliveryFrontier,
        local: DeliveryFrontier,
    ) -> bool:
        """Accept only one local block/request addition over an exact remote frontier."""
        if (
            len(snapshot.bindings) != len(local.bindings)
            or any(binding.active_claim is not None for binding in local.bindings)
            or local.integration_repair_claim is not None
        ):
            return False
        changed = 0
        for snapshot_binding, local_binding in zip(snapshot.bindings, local.bindings, strict=True):
            if snapshot_binding.outcome_id != local_binding.outcome_id:
                return False
            if snapshot_binding == local_binding:
                continue
            if snapshot_binding.block is not None or snapshot_binding.requests or local_binding.block is None:
                return False
            if local_binding.block.request_id is None:
                if local_binding.requests:
                    return False
            elif (
                len(local_binding.requests) != 1
                or local_binding.requests[0].request_id != local_binding.block.request_id
                or local_binding.requests[0].outcome_id != local_binding.outcome_id
            ):
                return False
            if local_binding.model_copy(update={"block": None, "requests": ()}) != snapshot_binding:
                return False
            changed += 1
        return changed == 1

    def _clear_target_sync_reconciliation(self, change_id: str) -> None:
        self._clear_remote_state_reconciliation(change_id)

    def _clear_remote_state_reconciliation(self, change_id: str) -> None:
        self._startup_health_diagnostics = tuple(
            diagnostic
            for diagnostic in self._startup_health_diagnostics
            if not (
                diagnostic.source == "remote-state"
                and diagnostic.change_id == change_id
                and diagnostic.code
                in {
                    "remote-state-reconciliation-required",
                    "snapshot-invalid",
                    "snapshot-identity-invalid",
                    "snapshot-path-identity-mismatch",
                    "snapshot-unreadable",
                }
            )
        )
        self._runtime_reconciliation_errors.pop(change_id, None)
        self._runtime_snapshots.pop(change_id, None)
        self._reconcile_runtimes()
        if change_id in self._runtime_reconciliation_errors:
            self._fail(
                "Delivery-state reconciliation completed with remaining Change errors: "
                f"{self._runtime_reconciliation_errors[change_id]}"
            )

    def _delivery_health_view(
        self, *, scoped_change_id: str | None = None, inspect_workspaces: bool = True
    ) -> DeliveryHealthView:
        diagnostics: list[DeliveryHealthDiagnostic] = [
            *self._startup_health_diagnostics,
        ]
        diagnosed_change_ids = {diagnostic.change_id for diagnostic in diagnostics if diagnostic.change_id is not None}
        for change_id, runtime in sorted(self._runtimes.items()):
            if inspect_workspaces and change_id not in diagnosed_change_ids:
                out_of_band = self._out_of_band_head_diagnostic(change_id)
                if out_of_band is not None:
                    diagnostics.append(out_of_band)
                    diagnosed_change_ids.add(change_id)
            marker_path = f".owlbear/delivery/runtime/changes/{change_id}/state-publication.json"
            try:
                pending = runtime.pending_state_publication()
            except (OSError, RuntimeError, ValueError) as exc:
                diagnostics.append(
                    DeliveryHealthDiagnostic(
                        source="local-runtime",
                        code="state-publication-invalid",
                        detail=_health_detail(
                            f"Delivery-state publication intent is invalid: {exc}",
                            "Delivery-state publication intent is invalid.",
                        ),
                        change_id=change_id,
                        path=marker_path,
                        reason=DeliveryHealthReason.STATE_PUBLICATION_INVALID,
                        resolution=DeliveryHealthResolution.AUTHORITY_GAP,
                    )
                )
            else:
                if pending is not None and self._delivery_state_publisher is not None:
                    diagnostics.append(
                        DeliveryHealthDiagnostic(
                            source="local-runtime",
                            code="state-publication-pending",
                            detail="Delivery-state publication is pending replay.",
                            change_id=change_id,
                            path=marker_path,
                            retry_safe=True,
                            reason=DeliveryHealthReason.STATE_PUBLICATION_PENDING,
                            resolution=DeliveryHealthResolution.RETRY,
                        )
                    )
        diagnostics.extend(
            DeliveryHealthDiagnostic(
                source="local-runtime",
                code=observation.diagnostic_code or "runtime-unavailable",
                detail=_health_detail(
                    observation.diagnostic_detail,
                    "Persisted Delivery state is unavailable.",
                ),
                change_id=observation.change_id,
                path=f".owlbear/delivery/runtime/changes/{observation.change_id}",
                reason=DeliveryHealthReason.RUNTIME_UNAVAILABLE,
                resolution=DeliveryHealthResolution.AUTHORITY_GAP,
            )
            for observation in self._discovered_changes.values()
            if observation.error is not None
            and not any(diagnostic.change_id == observation.change_id for diagnostic in diagnostics)
        )
        diagnostic_change_ids = {diagnostic.change_id for diagnostic in diagnostics if diagnostic.change_id is not None}
        diagnostics.extend(
            DeliveryHealthDiagnostic(
                source="runtime-reconciliation",
                code="runtime-reconciliation-required",
                detail=_health_detail(detail, "Delivery runtime reconciliation is required."),
                change_id=change_id,
                reason=DeliveryHealthReason.RUNTIME_RECONCILIATION_REQUIRED,
                resolution=DeliveryHealthResolution.AUTHORITY_GAP,
            )
            for change_id, detail in self._runtime_reconciliation_errors.items()
            if change_id not in diagnostic_change_ids
        )
        unique = {_health_diagnostic_key(diagnostic): diagnostic for diagnostic in diagnostics}
        ordered = tuple(
            sorted(
                unique.values(),
                key=lambda item: (
                    item.change_id or "",
                    item.source,
                    item.code,
                    item.path or "",
                ),
            )
        )
        if scoped_change_id is not None:
            ordered = tuple(item for item in ordered if item.change_id is None or item.change_id == scoped_change_id)
        bounded = ordered[:_MAX_HEALTH_DIAGNOSTICS]
        return DeliveryHealthView(
            status=DeliveryHealthStatus.ATTENTION if bounded else DeliveryHealthStatus.HEALTHY,
            diagnostics=bounded,
        )

    def _out_of_band_head_diagnostic(self, change_id: str) -> DeliveryHealthDiagnostic | None:
        """Report a clean local Change head that has no Delivery adoption evidence."""
        try:
            coordination = self._workspace_manager.show(change_id)
            if coordination.writer is not None or coordination.external_head_adoption_receipt is not None:
                return None
            observed_head = self._workspace_manager.observed_change_head(change_id)
        except (OSError, RuntimeError, subprocess.SubprocessError, ValueError):
            return None
        if observed_head == coordination.last_reviewed_commit:
            return None
        return DeliveryHealthDiagnostic(
            source="local-runtime",
            code="local-change-head-out-of-band",
            detail="Local Change branch is outside its reviewed Delivery boundary without adoption evidence.",
            change_id=change_id,
            reason=DeliveryHealthReason.LOCAL_CHANGE_HEAD_OUT_OF_BAND,
            resolution=DeliveryHealthResolution.AUTHORITY_GAP,
            expected_head=coordination.last_reviewed_commit,
            observed_local_head=observed_head,
        )

    def _portfolio_operating_view(
        self,
        snapshots: tuple[DeliveryPortfolioSnapshot, ...],
        groups: tuple[ChangeGroupView, ...],
    ) -> PortfolioOperatingView:
        verified_package_ids = {package.change_id for package in self._package_store.list_verified()}
        health_change_ids = tuple(
            diagnostic.change_id for diagnostic in self._startup_health_diagnostics if diagnostic.change_id is not None
        )
        status_ids = sorted((*verified_package_ids, *self._discovered_changes, *health_change_ids))
        change_statuses = tuple(
            status
            for status in (
                self._change_lifecycle_status(change_id, self._discovered_changes.get(change_id))
                for change_id in dict.fromkeys(status_ids)
            )
            if status.stage not in {DeliveryChangeStage.COMPLETED, DeliveryChangeStage.ABANDONED}
            or not status.actionable_runtime
        )
        draft_design_ids = tuple(status.change_id for status in change_statuses if not status.admitted)
        design_required_ids = tuple(
            status.change_id
            for status in change_statuses
            if status.admitted and status.stage == DeliveryChangeStage.DESIGN
        )
        operational_snapshots = tuple(
            snapshot for snapshot in snapshots if snapshot.contract.change_id not in self._runtime_reconciliation_errors
        )
        claimed = self._claimed_work(operational_snapshots)
        queued = self._queued_work(operational_snapshots)
        operational_groups = tuple(
            group for group in groups if group.change_id not in self._runtime_reconciliation_errors
        )
        interventions = tuple(
            PortfolioWorkReference(
                change_id=item.change_id,
                item_key=item.item_key,
                scope=_operating_scope(item.scope),
            )
            for group in operational_groups
            for item in group.items
            if item.needs == WorkItemNeed.YOU
        )
        dependency_waits = tuple(
            PortfolioWorkReference(
                change_id=item.change_id,
                item_key=item.item_key,
                scope=_operating_scope(item.scope),
            )
            for group in operational_groups
            for item in group.items
            if item.needs == WorkItemNeed.DEPENDENCY
        )
        snapshot_ids = {snapshot.contract.change_id for snapshot in operational_snapshots}
        unavailable_frontiers = tuple(
            observation.frontier
            for change_id, observation in sorted(self._discovered_changes.items())
            if (observation.admitted and change_id not in snapshot_ids and observation.frontier is not None)
        )
        unfinished_runtime_count = sum(
            not is_change_terminal(snapshot.frontier) for snapshot in operational_snapshots
        ) + sum(not is_change_terminal(frontier) for frontier in unavailable_frontiers)
        unfinished_runtime_count += len(
            {
                diagnostic.change_id
                for diagnostic in self._delivery_health_view().diagnostics
                if diagnostic.change_id is not None
            }
            - snapshot_ids
            - set(self._discovered_changes)
        )
        unfinished_runtime_count += len(
            {
                change_id
                for change_id in self._runtime_reconciliation_errors
                if change_id not in snapshot_ids
                and change_id in self._discovered_changes
                and self._discovered_changes[change_id].frontier is None
            }
        )
        unfinished_change_count = unfinished_runtime_count
        completed_change_count = sum(
            snapshot.frontier.change_completion is not None for snapshot in operational_snapshots
        ) + sum(frontier.change_completion is not None for frontier in unavailable_frontiers)
        design_change_ids = tuple(dict.fromkeys((*draft_design_ids, *design_required_ids)))
        guidance = derive_portfolio_guidance(
            PortfolioGuidanceFacts(
                unfinished_change_count=unfinished_change_count,
                design_change_ids=design_change_ids,
                claimed=claimed,
                queued=queued,
                interventions=interventions,
                dependency_waits=dependency_waits,
            )
        )
        return PortfolioOperatingView(
            unfinished_change_count=unfinished_change_count,
            completed_change_count=completed_change_count,
            statuses=change_statuses,
            draft_design_change_ids=draft_design_ids,
            design_required_change_ids=design_required_ids,
            claimed=claimed,
            queued_for_orchestration=queued,
            interventions=interventions,
            dependency_waits=dependency_waits,
            guidance=guidance,
        )

    def _change_lifecycle_status(
        self,
        change_id: str,
        observation: DeliveryChangeObservation | None,
    ) -> PortfolioChangeLifecycleStatus:
        reconciliation_error = self._runtime_reconciliation_errors.get(change_id)
        health_diagnostic = next(
            (diagnostic for diagnostic in self._startup_health_diagnostics if diagnostic.change_id == change_id),
            None,
        )
        if observation is None or not observation.admitted:
            if health_diagnostic is not None:
                return PortfolioChangeLifecycleStatus(
                    change_id=change_id,
                    admission=PortfolioChangeAdmission.ADMITTED,
                    stage=None,
                    actionable_runtime=False,
                    diagnostic_code=health_diagnostic.code,
                    diagnostic_detail=_health_detail(
                        health_diagnostic.detail,
                        "Delivery state requires reconciliation.",
                    ),
                )
            return PortfolioChangeLifecycleStatus(
                change_id=change_id,
                admission=PortfolioChangeAdmission.UNADMITTED,
                stage=DeliveryChangeStage.DESIGN,
                actionable_runtime=False,
            )
        diagnostic_code = observation.diagnostic_code
        diagnostic_detail = observation.diagnostic_detail
        if diagnostic_code is None and reconciliation_error is not None:
            diagnostic_code = "runtime-reconciliation-required"
        if diagnostic_detail is None and reconciliation_error is not None:
            diagnostic_detail = reconciliation_error
        return PortfolioChangeLifecycleStatus(
            change_id=change_id,
            admission=PortfolioChangeAdmission.ADMITTED,
            stage=observation.stage,
            actionable_runtime=observation.actionable_runtime and reconciliation_error is None,
            diagnostic_code=diagnostic_code,
            diagnostic_detail=_health_detail(diagnostic_detail, "Delivery state requires reconciliation")
            if diagnostic_detail is not None
            else None,
        )

    def _claimed_work(
        self,
        snapshots: tuple[DeliveryPortfolioSnapshot, ...],
    ) -> tuple[PortfolioWorkReference, ...]:
        claimed = []
        for snapshot in snapshots:
            if snapshot.contract.change_id in self._runtime_reconciliation_errors:
                continue
            claimed.extend(
                PortfolioWorkReference(
                    change_id=snapshot.contract.change_id,
                    item_key=f"outcome:{binding.outcome_id}",
                    scope=PortfolioWorkScope.OUTCOME,
                )
                for binding in snapshot.frontier.bindings
                if binding.active_claim is not None
            )
        return tuple(claimed)

    def _queued_work(
        self,
        snapshots: tuple[DeliveryPortfolioSnapshot, ...],
    ) -> tuple[PortfolioWorkReference, ...]:
        return self._queued_outcome_work(snapshots)

    def _queued_outcome_work(
        self,
        snapshots: tuple[DeliveryPortfolioSnapshot, ...],
    ) -> tuple[PortfolioWorkReference, ...]:
        ranked = tuple(
            candidate for snapshot in snapshots if (candidate := self._queued_outcome_candidate(snapshot)) is not None
        )
        return tuple(item[4] for item in sorted(ranked, key=lambda item: item[:4]))

    def _queued_outcome_candidate(
        self,
        snapshot: DeliveryPortfolioSnapshot,
    ) -> tuple[int, int, int, str, PortfolioWorkReference] | None:
        if (
            snapshot.contract.change_id in self._runtime_reconciliation_errors
            or self._snapshot_change_stage(snapshot) != DeliveryChangeStage.BUILDING
            or snapshot.frontier.change_disposition is not None
            or self._snapshot_has_active_claims(snapshot)
        ):
            return None
        completed = {
            binding.outcome_id for binding in snapshot.frontier.bindings if binding.stage == DeliveryStage.COMPLETED
        }
        bindings = {binding.outcome_id: binding for binding in snapshot.frontier.bindings}
        ranked = []
        for outcome_index, outcome in enumerate(snapshot.contract.outcomes):
            binding = bindings[outcome.outcome_id]
            if (
                binding.stage in {DeliveryStage.DESIGN, DeliveryStage.COMPLETED}
                or binding.active_claim is not None
                or (binding.block is not None and not binding.block.resolved)
                or not set(outcome.dependency_ids) <= completed
            ):
                continue
            task_index = self._snapshot_task_index(binding)
            if task_index is None:
                continue
            ranked.append(
                (
                    self._snapshot_dependency_depth(snapshot, outcome.outcome_id),
                    outcome_index,
                    task_index,
                    snapshot.contract.change_id,
                    PortfolioWorkReference(
                        change_id=snapshot.contract.change_id,
                        item_key=f"outcome:{outcome.outcome_id}",
                        scope=PortfolioWorkScope.OUTCOME,
                    ),
                )
            )
        return min(ranked, key=lambda item: item[:4]) if ranked else None

    @staticmethod
    def _snapshot_task_index(binding: OutcomeAuthorityBinding) -> int | None:
        if binding.stage != DeliveryStage.IMPLEMENTATION:
            return 0
        completed = {result.task_id for result in binding.results}
        task = next(
            (item for item in binding.tasks if item.task_id not in completed and set(item.dependency_ids) <= completed),
            None,
        )
        return binding.task_ids.index(task.task_id) if task is not None else None

    def show_work_item(self, change_id: str, work_item_id: str) -> WorkItemDetail:
        """Show bounded semantic detail from one exact change projector."""
        try:
            return self._work_item_projector(self._runtime(change_id)).show(work_item_id)
        except KeyError as exc:
            if work_item_id == "publication":
                self._fail(
                    "work item identity is invalid for MCP publication lookup: "
                    f"use Change ID '{change_id}' as work_item_id",
                    exc,
                )
            self._fail(f"work item is absent: {work_item_id}", exc)

    def show_work_item_view(self, change_id: str, item_key: str) -> WorkItemDetailView | DeliveryUnavailableChangeView:
        """Show semantic and operator detail from one exact snapshot."""
        self._reconcile_runtimes()
        observation = self._discovered_changes.get(change_id)
        if observation is not None and not observation.actionable_runtime:
            return self._unavailable_change(change_id)
        runtime = self._runtime(change_id)
        return self._captured_detail(runtime, self._work_item_projector(runtime), item_key)

    def _captured_detail(
        self,
        runtime: DeliveryRuntime,
        projector: WorkItemProjector,
        item_key: str,
    ) -> WorkItemDetailView:
        change_id = runtime.contract.change_id
        try:
            view = projector.show_view(item_key)
        except (KeyError, StopIteration) as exc:
            self._fail(f"work item is absent: {item_key}", exc)
        if view.publication is None:
            return view
        try:
            coordination = self._workspace_manager.show(change_id)
        except (OSError, RuntimeError, ValueError):
            unavailable = self._unavailable_change(change_id, "coordination-unavailable")
            return view.model_copy(update={"readiness": unavailable.readiness})
        conflict = coordination.target_sync_conflict
        conflict_view = (
            WorkItemTargetSyncConflictView(
                conflict_id=conflict.conflict_id,
                operation_id=conflict.operation_id,
                target_head=conflict.target_head,
                change_head_before=conflict.change_head_before,
                conflict_paths=conflict.conflict_paths,
            )
            if conflict is not None
            else None
        )
        publication = view.publication.model_copy(update={"target_sync_conflict": conflict_view})
        if view.readiness is not None:
            ready = view.readiness.executable and view.readiness.operation is WorkItemActionKind.FINALIZE
            publication = publication.model_copy(
                update={
                    "ready_for_finalization": ready,
                    "readiness_diagnostics": () if ready else (view.readiness.reason_code,),
                }
            )
        if coordination.worktree_cleanup is None and (
            publication.phase
            in {
                WorkItemPublicationPhase.ABANDONED,
                WorkItemPublicationPhase.ACCEPTANCE_OBSERVED,
            }
            or not coordination.worktree_path.exists()
        ):
            retained = self._workspace_manager.inspect_retained(change_id, coordination)
            publication = publication.model_copy(
                update={
                    "worktree_cleanup": self._worktree_cleanup_view(runtime, retained),
                    "worktree_recovery": self._worktree_recovery_view(retained),
                }
            )
        return view.model_copy(update={"publication": publication})

    def show_operator_context(self, change_id: str, outcome_id: str) -> DeliveryOperatorContext:
        """Show current bounded operator state from one exact runtime binding."""
        runtime = self._runtime(change_id)
        binding = runtime.show_binding(outcome_id)
        return DeliveryOperatorContext(
            change_id=change_id,
            outcome_id=outcome_id,
            stage=binding.stage,
            block=binding.block,
            requests=binding.requests,
            active_claim=_operator_claim(binding.active_claim),
            return_context=binding.return_context,
            recovery_attention=_operator_recovery_attention(binding.recovery_attention),
        )

    def resolve_request(
        self,
        change_id: str,
        request_id: str,
        resolution: DeliveryRequestResolution,
    ) -> DeliveryRequest:
        """Persist one request resolution by delegating to the owning runtime."""
        with self._coordinator.acquisition_lock():
            runtime = self._runtime(change_id, for_mutation=True)
            with locked_roots((self._checkpoint_lock_root(change_id),)):
                self._import_legacy_worker_budgets(runtime)
                resolved = runtime.resolve_request(request_id, resolution)
                self._record_retry_release(runtime, outcome_id=resolved.outcome_id)
                self._publish_delivery_state(
                    change_id,
                    runtime,
                    _checkpoint_operation_id("request-resolution", change_id, request_id),
                )
                return resolved

    def clear_block(
        self,
        change_id: str,
        outcome_id: str,
        block_id: str,
        operator_note: str,
        locators: tuple[str, ...],
    ) -> OutcomeAuthorityBinding:
        """Clear a requestless same-stage block with operator evidence via runtime."""
        with self._coordinator.acquisition_lock():
            runtime = self._runtime(change_id, for_mutation=True)
            with locked_roots((self._checkpoint_lock_root(change_id),)):
                self._import_legacy_worker_budgets(runtime)
                binding = runtime.unblock(outcome_id, block_id, operator_note, locators)
                self._record_retry_release(runtime, outcome_id=outcome_id)
                self._publish_delivery_state(
                    change_id,
                    runtime,
                    _checkpoint_operation_id("block-resolution", change_id, outcome_id, block_id),
                )
                return binding

    def administrative_move(
        self,
        change_id: str,
        request: AdministrativeDeliveryMove,
    ) -> AdministrativeDeliveryMoveResult:
        """Delegate an authorized operator backward movement to the owning runtime."""
        with self._coordinator.acquisition_lock():
            runtime = self._runtime(change_id, for_mutation=True)
            with locked_roots((self._checkpoint_lock_root(change_id),)):
                self._import_legacy_worker_budgets(runtime)
                result = runtime.administrative_move(request)
                self._publish_delivery_state(
                    change_id,
                    runtime,
                    _checkpoint_operation_id("administrative-move", change_id, request.move_id),
                )
                return result

    def preview_administrative_move(
        self,
        change_id: str,
        outcome_id: str,
        target: DeliveryStage,
    ) -> AdministrativeDeliveryMovePreview:
        """Preview one exact backward movement without mutating authority."""
        return self._runtime(change_id).preview_administrative_move(outcome_id, target)

    def _work_item_projector(self, runtime: DeliveryRuntime) -> WorkItemProjector:
        return self._read_projector(self._delivery_snapshot(runtime))

    def _read_projector(self, snapshot: DeliveryPortfolioSnapshot) -> WorkItemProjector:
        cards = WorkItemProjector(snapshot).group_view().items
        basis = DeliveryReadinessBasis(
            contract_digest=contract_fingerprint(snapshot.contract),
            frontier_digest=snapshot.version,
            candidate_head=snapshot.frontier.finalization.exact_head if snapshot.frontier.finalization else None,
        )
        basis, workspace_reason = self._capture_action_basis(snapshot, cards, basis)
        try:
            reports = FinalizationReportStore(self._target_root, snapshot.contract.change_id).read()
        except FinalizationReportError:
            reports = None
        basis = basis.model_copy(update={"diagnostic_sequence": reports.sequence if reports is not None else None})
        decisions = tuple(
            self._with_finalization_report(self._card_readiness(snapshot, card, basis, workspace_reason), reports)
            for card in cards
        )
        decisions = tuple(
            self._with_retry_readiness(snapshot, card, decision)
            for card, decision in zip(cards, decisions, strict=True)
        )
        return WorkItemProjector(snapshot, decisions)

    def _with_retry_readiness(  # noqa: C901 - maps one persisted policy to the shared readiness contract.
        self,
        snapshot: DeliveryPortfolioSnapshot,
        card: WorkItemCardView,
        decision: DeliveryReadiness,
    ) -> DeliveryReadiness:
        """Overlay durable retry state without creating or mutating a ledger on read."""
        action = decision.operation
        if action is None:
            return decision
        if decision.status == "running":
            return decision
        exact_head = decision.basis.candidate_head or decision.basis.source_head
        if exact_head is None:
            return decision
        finalization = snapshot.frontier.finalization
        key = RetryEpisodeKey.engine(
            snapshot.contract.change_id,
            action.value,
            exact_head,
            decision.basis.target_head,
            finalization.finalization_id if finalization is not None else None,
        )
        if card.scope is WorkItemScope.OUTCOME and card.work_item_id != snapshot.contract.change_id:
            outcome = next((item for item in snapshot.contract.outcomes if item.outcome_id == card.work_item_id), None)
            binding = next((item for item in snapshot.frontier.bindings if item.outcome_id == card.work_item_id), None)
            if outcome is not None and binding is not None:
                role = (
                    DeliveryWorkerRole.BUILDER
                    if binding.stage is DeliveryStage.IMPLEMENTATION
                    else DeliveryWorkerRole.PLANNER
                )
                completed = {result.task_id for result in binding.results}
                task_lineage = (
                    next(
                        (
                            task.task_id
                            for task in binding.tasks
                            if task.task_id not in completed and set(task.dependency_ids) <= completed
                        ),
                        card.work_item_id,
                    )
                    if role is DeliveryWorkerRole.BUILDER
                    else card.work_item_id
                )
                key = RetryEpisodeKey.worker(
                    snapshot.contract.change_id,
                    f"{role.value}-claim",
                    exact_head,
                    contract_digest=contract_fingerprint(snapshot.contract),
                    outcome_id=card.work_item_id,
                    task_lineage=task_lineage,
                    procedure_class=role.value,
                    original_candidate=(
                        binding.candidate.digest
                        if binding.candidate is not None
                        else binding.result_candidate.digest
                        if binding.result_candidate is not None
                        else card.work_item_id
                    ),
                )
        failure_class = (
            RetryFailureClass.ACCEPTANCE
            if action is WorkItemActionKind.OBSERVE_ACCEPTANCE
            else RetryFailureClass.TRANSIENT
            if action in {WorkItemActionKind.SYNC_TARGET, WorkItemActionKind.OBSERVE_ACCEPTANCE}
            else RetryFailureClass.MECHANICAL
        )
        try:
            episode = RetryLedger(self._target_root, snapshot.contract.change_id, clock=self._clock).episode(key)
        except (OSError, RetryLedgerCorruptError, RuntimeError, ValueError):
            return decision.model_copy(
                update={
                    "status": "unavailable",
                    "reason_code": "retry-ledger-unavailable",
                    "executable": False,
                    "action": None,
                    "stop_reason": "retry-ledger-unavailable",
                }
            )
        if episode is None or episode.failure_class is not failure_class:
            return decision
        updates: dict[str, object] = {
            "attempts": episode.total_attempts,
            "next_eligible_at": episode.next_eligible_at,
            "stop_reason": episode.stop_code.value if episode.stop_code is not None else None,
        }
        backoff_active = episode.next_eligible_at is not None and _timestamp(self._clock()) < _timestamp(
            episode.next_eligible_at
        )
        if backoff_active:
            updates.update(
                {
                    "status": "waiting",
                    "reason_code": "retry-backoff",
                    "executable": False,
                    "action": None,
                    "next_actor": WorkItemNextActor.AGENT,
                }
            )
        elif episode.last_status in {"reserved", "contained"}:
            updates.update(
                {
                    "status": "blocked",
                    "reason_code": "retry-containment",
                    "executable": False,
                    "action": None,
                    "next_actor": WorkItemNextActor.YOU,
                    "stop_reason": RetryStopCode.CONTAINMENT.value,
                }
            )
        elif episode.stop_code is RetryStopCode.EXHAUSTED:
            updates.update(
                {
                    "status": "blocked",
                    "reason_code": "retry-exhausted",
                    "executable": False,
                    "action": None,
                    "next_actor": WorkItemNextActor.YOU,
                }
            )
        elif episode.stop_code is RetryStopCode.ACCEPTANCE_WAIT:
            updates.update(
                {
                    "status": "waiting",
                    "reason_code": "acceptance-wait",
                    "executable": False,
                    "action": None,
                    "next_actor": WorkItemNextActor.YOU,
                }
            )
        elif episode.stop_code is RetryStopCode.CONTAINMENT:
            updates.update(
                {
                    "status": "blocked",
                    "reason_code": "retry-containment",
                    "executable": False,
                    "action": None,
                    "next_actor": WorkItemNextActor.YOU,
                }
            )
        return decision.model_copy(update=updates)

    def _capture_action_basis(
        self, snapshot: DeliveryPortfolioSnapshot, cards: tuple[WorkItemCardView, ...], basis: DeliveryReadinessBasis
    ) -> tuple[DeliveryReadinessBasis, str | None]:
        try:
            coordination = self._workspace_manager.show(snapshot.contract.change_id)
        except (OSError, RuntimeError, ValueError):
            return basis, "coordination-unavailable"
        if not self._coordinator.recovery_exclusions_verified(coordination):
            return basis, "coordination-unavailable"
        action = coordination.continuation_action
        basis = basis.model_copy(update={"continuation_id": action.operation_id if action else None})
        if action is not None and action.finished_at is None:
            result_path = self._coordinator.continuation_record_path(action.change_id, action.operation_id, result=True)
            return basis, "engine-action-blocked" if result_path.exists() else "engine-action-pending"
        needs_workspace = self._supports_finalization(snapshot.frontier) or any(
            card.action.kind
            in {
                WorkItemActionKind.FINALIZE,
                WorkItemActionKind.RECONCILE_CHECKPOINT,
                WorkItemActionKind.MARK_READY,
                WorkItemActionKind.OBSERVE_ACCEPTANCE,
            }
            for card in cards
        )
        if needs_workspace and not self._snapshot_has_active_claims(snapshot):
            basis, reason = self._capture_readiness_workspace(snapshot, basis)
            sync = snapshot.frontier.target_sync_receipt
            pending = snapshot.frontier.pending_checkpoint
            if (
                reason is None
                and self._supports_finalization(snapshot.frontier)
                and self._change_branch_publisher is not None
            ):
                if pending is not None and pending.head is not None and snapshot.frontier.published_head is None:
                    reason = "checkpoint-pending"
                elif sync is None or sync.target_head != basis.target_head:
                    reason = "target-sync-required"
            return basis, reason
        if any(
            self._captured_action(snapshot.frontier, card).kind is WorkItemActionKind.START_ORCHESTRATION
            for card in cards
        ):
            basis = basis.model_copy(update={"source_head": coordination.last_reviewed_commit})
        if any(
            binding.active_claim is not None
            and binding.active_claim.worker_role is DeliveryWorkerRole.BUILDER
            and (
                coordination.writer is None
                or coordination.writer.kind != "build"
                or coordination.writer.claim_id != binding.active_claim.claim_id
                or coordination.writer.attempt_id != binding.active_claim.attempt_id
            )
            for binding in snapshot.frontier.bindings
        ):
            return basis, "claim-custody-unreconciled"
        return basis, None

    @staticmethod
    def _with_finalization_report(
        decision: DeliveryReadiness,
        reports: FinalizationReportSnapshot | None,
    ) -> DeliveryReadiness:
        if reports is None:
            return decision.model_copy(
                update={
                    "reason_code": "report-store-unavailable"
                    if decision.reason_code == "ready"
                    else decision.reason_code,
                    "checks_state": "passed" if decision.checks_state == "passed" else "unknown",
                }
            )
        if not reports.reports:
            return decision
        report = reports.reports[-1]
        current = (
            report.request.expected_change_head == decision.basis.candidate_head
            and report.request.expected_contract_digest == decision.basis.contract_digest
            and decision.checks_state != "passed"
        )
        updates = {
            "last_attempt": FinalizationAttempt(report=report, applicability="current" if current else "historical")
        }
        if current and decision.reason_code not in {"workspace-dirty", "workspace-inspection-failed"}:
            updates["checks_state"] = report.request.checks_state
        if current and decision.executable and decision.operation is WorkItemActionKind.FINALIZE:
            updates["action"] = decision.action.model_copy(update={"label": "Retry verification"})
        return decision.model_copy(update=updates)

    def _capture_readiness_workspace(
        self,
        snapshot: DeliveryPortfolioSnapshot,
        basis: DeliveryReadinessBasis,
    ) -> tuple[DeliveryReadinessBasis, str | None]:
        try:
            coordination = self._workspace_manager.show(snapshot.contract.change_id)
            basis = basis.model_copy(
                update={
                    "reviewed_head": coordination.last_reviewed_commit,
                    "target_head": self._workspace_manager.observed_target_head(),
                }
            )
            if (coordination.writer is not None and coordination.writer.kind != "finalize") or (
                coordination.publication_lease is not None
            ):
                return basis, "active-custody"
            coordination, head, fingerprint, _paths, reason = self._workspace_manager.capture_finalization_workspace(
                snapshot.contract.change_id,
                tuple(result.completed_commit for binding in snapshot.frontier.bindings for result in binding.results),
            )
            basis = basis.model_copy(update={"candidate_head": head, "workspace_fingerprint": fingerprint})
            if coordination.writer is not None and coordination.writer.kind == "finalize":
                reports = FinalizationReportStore(self._target_root, snapshot.contract.change_id).read()
                if any(report.request.attempt_key == coordination.writer.attempt_id for report in reports.reports):
                    return basis, "finalization-failed"
            invalidation = snapshot.frontier.finalization_invalidation
            if invalidation and invalidation.reason == "review-repair" and head == invalidation.expected_head:
                reason = "review-repair"
        except (OSError, RuntimeError, subprocess.SubprocessError, ValueError):
            return basis, "workspace-inspection-failed"
        return basis, reason

    @staticmethod
    def _supports_finalization(frontier: DeliveryFrontier) -> bool:
        return (
            frontier.finalization is None
            and frontier.change_completion is None
            and frontier.change_abandonment is None
            and frontier.change_deferral is None
            and frontier.change_disposition is None
            and frontier.integration_repair_claim is None
            and all(
                binding.stage is DeliveryStage.COMPLETED
                and binding.active_claim is None
                and binding.recovery_attention is None
                and not any(request.resolution is None for request in binding.requests)
                and (binding.block is None or binding.block.resolved)
                and tuple(result.task_id for result in binding.results) == binding.task_ids
                for binding in frontier.bindings
            )
        )

    @classmethod
    def _captured_action(cls, frontier: DeliveryFrontier, card: WorkItemCardView) -> WorkItemAction:
        if card.scope is WorkItemScope.CHANGE_PUBLICATION and cls._supports_finalization(frontier):
            return WorkItemAction(
                kind=WorkItemActionKind.FINALIZE, label="Finalize Change", command=f"/finalize-change {card.change_id}"
            )
        if card.action.kind is WorkItemActionKind.FINALIZE:
            return WorkItemAction()
        if (
            card.scope is WorkItemScope.OUTCOME
            and card.stage is not None
            and card.stage.value in {"planning", "implementation"}
            and card.needs is WorkItemNeed.NONE
            and card.activity.state is WorkItemActivityState.READY
            and card.action.kind is WorkItemActionKind.NONE
        ):
            return WorkItemAction(kind=WorkItemActionKind.START_ORCHESTRATION, label="Start Orchestration")
        return card.action

    @staticmethod
    def _action_prerequisites(operation: WorkItemActionKind | None, workspace_reason: str | None) -> tuple[str, str]:
        if operation in {
            WorkItemActionKind.FINALIZE,
            WorkItemActionKind.RECONCILE_CHECKPOINT,
            WorkItemActionKind.SYNC_TARGET,
            WorkItemActionKind.MARK_READY,
            WorkItemActionKind.OBSERVE_ACCEPTANCE,
        } and workspace_reason not in {None, "target-sync-required", "checkpoint-pending"}:
            return ("unavailable" if workspace_reason == "workspace-inspection-failed" else "blocked"), workspace_reason
        if operation is None:
            return "waiting", "publication-wait"
        return "ready", "ready"

    @classmethod
    def _card_readiness(
        cls,
        snapshot: DeliveryPortfolioSnapshot,
        card: WorkItemCardView,
        basis: DeliveryReadinessBasis,
        workspace_reason: str | None,
    ) -> DeliveryReadiness:
        frontier = snapshot.frontier
        finalization = card.scope is WorkItemScope.CHANGE_PUBLICATION and cls._supports_finalization(frontier)
        action = cls._captured_action(frontier, card)
        prerequisites = {
            "target-sync-required": WorkItemAction(kind=WorkItemActionKind.SYNC_TARGET, label="Synchronize target"),
            "checkpoint-pending": WorkItemAction(
                kind=WorkItemActionKind.RECONCILE_CHECKPOINT, label="Publish checkpoint"
            ),
        }
        action = prerequisites.get(workspace_reason, action) if finalization else action
        operation = action.kind if action.kind is not WorkItemActionKind.NONE else None
        status, reason = "ready", "ready"
        if workspace_reason in {"engine-action-pending", "engine-action-blocked"}:
            status = "running" if workspace_reason == "engine-action-pending" else "blocked"
            reason = workspace_reason
        elif workspace_reason == "coordination-unavailable":
            status, reason = "unavailable", workspace_reason
        elif workspace_reason == "claim-custody-unreconciled":
            status, reason = "blocked", workspace_reason
        elif (
            card.activity.state is WorkItemActivityState.WORKING
            or (
                card.scope is WorkItemScope.CHANGE_PUBLICATION
                and (any(binding.active_claim for binding in frontier.bindings) or frontier.integration_repair_claim)
            )
            or (card.scope is WorkItemScope.CHANGE_PUBLICATION and workspace_reason == "active-custody")
        ):
            status, reason = "running", "active-custody"
        elif frontier.change_completion is not None or frontier.change_abandonment is not None:
            status, reason = "complete", "change-terminal"
        elif frontier.change_deferral is not None:
            status, reason = ("ready" if operation else "blocked"), "change-paused"
        elif card.scope is WorkItemScope.OUTCOME and card.stage is not None and card.stage.value == "completed":
            status, reason = "complete", "change-terminal"
        elif card.needs is WorkItemNeed.DEPENDENCY:
            status, reason = "waiting", "dependency-wait"
        elif card.needs is WorkItemNeed.YOU and not finalization:
            status, reason = ("ready" if operation else "blocked"), "request-action"
        else:
            status, reason = cls._action_prerequisites(operation, workspace_reason)
        executable = status == "ready" and operation is not None
        return DeliveryReadiness(
            status=status,
            operation=operation,
            executable=executable,
            next_actor=WorkItemNextActor.AGENT if finalization else card.next_actor,
            reason_code=reason,
            checks_state="passed" if frontier.finalization is not None else "not-run",
            basis=basis,
            action=action if executable else None,
        )

    def _worktree_cleanup_view(
        self, runtime: DeliveryRuntime, retained: RetainedChangeWorktree
    ) -> WorkItemWorktreeCleanupView:
        projection = self._retained_change_worktree_view(retained)
        try:
            completion = runtime.completion_receipt()
        except (OSError, ValueError, DeliveryRuntimeConflictError):
            completion = None
        return WorkItemWorktreeCleanupView(
            eligible=projection.cleanup_eligible,
            blocked_reason=projection.cleanup_blocked_reason.value
            if projection.cleanup_blocked_reason is not None
            else None,
            completion_id=completion.completion_id if completion is not None else None,
        )

    def _worktree_recovery_view(
        self,
        retained: RetainedChangeWorktree,
    ) -> WorkItemWorktreeRecoveryView | None:
        if ChangeWorktreeAttentionCode.WORKTREE_MISSING not in retained.attention:
            return None
        allowed_attention = {
            ChangeWorktreeAttentionCode.COORDINATION_MISSING,
            ChangeWorktreeAttentionCode.GIT_REGISTRATION_MISSING,
            ChangeWorktreeAttentionCode.PRUNABLE,
            ChangeWorktreeAttentionCode.WORKTREE_MISSING,
        }
        blocked_reason: str | None = None
        if retained.writer is not None:
            blocked_reason = DeliveryRetainedWorktreeCleanupBlockReason.ACTIVE_WRITER.value
        elif retained.publication_expiry is not None and retained.publication_expiry > _timestamp(self._clock()):
            blocked_reason = DeliveryRetainedWorktreeCleanupBlockReason.ACTIVE_PUBLICATION_LEASE.value
        elif any(code not in allowed_attention for code in retained.attention):
            blocked_reason = DeliveryRetainedWorktreeCleanupBlockReason.WORKTREE_ATTENTION.value
        elif retained.last_reviewed_commit is None:
            blocked_reason = "reviewed-head-unavailable"
        return WorkItemWorktreeRecoveryView(
            eligible=blocked_reason is None,
            blocked_reason=blocked_reason,
            recovery_reviewed_head=retained.last_reviewed_commit,
        )

    def _reconcile_runtimes(self) -> None:
        with self._runtime_reconciliation_lock:
            previous_runtimes = self._runtimes
            initial_reconciliation = not self._has_reconciled_runtimes
        reconciled, observations, reconciliation_errors = self._reconcile_runtime_snapshot(
            previous_runtimes,
            initial_reconciliation=initial_reconciliation,
        )
        self._publish_reconciled_runtimes(
            previous_runtimes,
            reconciled,
            observations,
            reconciliation_errors,
        )

    def _reconcile_runtime_snapshot(
        self,
        previous_runtimes: dict[str, DeliveryRuntime],
        *,
        initial_reconciliation: bool,
    ) -> tuple[
        dict[str, DeliveryRuntime],
        dict[str, DeliveryChangeObservation],
        dict[str, str],
    ]:
        try:
            discovered = discover_persisted_changes(self._target_root)
        except DeliveryDiscoveryRootError as exc:
            raise DeliveryRuntimeReconciliationError(None, exc.detail) from exc

        observations = {observation.change_id: observation for observation in discovered}
        reconciled: dict[str, DeliveryRuntime] = {}
        reconciliation_errors = {
            diagnostic.change_id: f"{diagnostic.code}: {diagnostic.detail}"
            for diagnostic in self._startup_health_diagnostics
            if diagnostic.change_id is not None
        }

        for change_id, runtime in previous_runtimes.items():
            observation = observations.get(change_id)
            if observation is None:
                continue
            reconciled_runtime, error = self._reconcile_existing_runtime(
                runtime,
                observation,
                initial_reconciliation=initial_reconciliation,
            )
            if reconciled_runtime is not None:
                reconciled[change_id] = reconciled_runtime
            if error is not None and change_id not in reconciliation_errors:
                reconciliation_errors[change_id] = error

        for change_id, observation in observations.items():
            if change_id in reconciled:
                continue
            runtime, error = self._reconcile_new_runtime(observation)
            if runtime is not None:
                reconciled[change_id] = runtime
            if error is not None and change_id not in reconciliation_errors:
                reconciliation_errors[change_id] = error

        return reconciled, observations, reconciliation_errors

    def _publish_reconciled_runtimes(
        self,
        previous_runtimes: dict[str, DeliveryRuntime],
        reconciled: dict[str, DeliveryRuntime],
        observations: dict[str, DeliveryChangeObservation],
        reconciliation_errors: dict[str, str],
    ) -> None:
        with self._runtime_reconciliation_lock:
            current_runtimes = self._runtimes
            if current_runtimes is not previous_runtimes:
                for change_id in previous_runtimes.keys() - current_runtimes.keys():
                    reconciled.pop(change_id, None)
                reconciled.update(
                    {
                        change_id: runtime
                        for change_id, runtime in current_runtimes.items()
                        if previous_runtimes.get(change_id) is not runtime
                    }
                )
            self._runtimes = reconciled
            self._discovered_changes = observations
            self._runtime_reconciliation_errors = reconciliation_errors
            self._has_reconciled_runtimes = True

    def _reconcile_existing_runtime(
        self,
        runtime: DeliveryRuntime,
        observation: DeliveryChangeObservation,
        *,
        initial_reconciliation: bool,
    ) -> tuple[DeliveryRuntime | None, str | None]:
        active = self._runtime_has_active_work(runtime)
        reconciled_runtime: DeliveryRuntime | None = runtime
        error: str | None = None
        if not observation.admitted:
            if self._retain_unadmitted_runtime(
                observation,
                active=active,
                initial_reconciliation=initial_reconciliation,
            ):
                error = self._observation_detail(observation)
            else:
                reconciled_runtime = None
        elif not observation.actionable_runtime or observation.contract is None:
            error = self._observation_detail(observation)
        elif observation.contract_fingerprint != contract_fingerprint(runtime.contract):
            if active:
                error = "persisted contract fingerprint differs from runtime authority"
            else:
                try:
                    reconciled_runtime = self._compose_runtime(observation)
                except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as exc:
                    error = str(exc) or "replacement runtime is unavailable"
        return reconciled_runtime, error

    @staticmethod
    def _retain_unadmitted_runtime(
        observation: DeliveryChangeObservation,
        *,
        active: bool,
        initial_reconciliation: bool,
    ) -> bool:
        return (
            active
            or not initial_reconciliation
            or (
                initial_reconciliation
                and observation.frontier is not None
                and any(binding.results for binding in observation.frontier.bindings)
            )
        )

    def _reconcile_new_runtime(
        self,
        observation: DeliveryChangeObservation,
    ) -> tuple[DeliveryRuntime | None, str | None]:
        if not observation.admitted or not observation.actionable_runtime or observation.contract is None:
            if observation.admitted and not observation.actionable_runtime:
                return None, self._observation_detail(observation)
            return None, None
        try:
            return self._compose_runtime(observation), None
        except (OSError, RuntimeError, ValueError) as exc:
            return None, _health_detail(str(exc), "runtime is unavailable")

    def _compose_runtime(self, observation: DeliveryChangeObservation) -> DeliveryRuntime:
        if observation.contract is None:
            self._fail("reconciled Change contract is unavailable")
        return DeliveryRuntime(
            self._target_root,
            observation.contract,
            workspace_manager=self._workspace_manager,
        )

    @staticmethod
    def _runtime_has_active_work(runtime: DeliveryRuntime) -> bool:
        try:
            return bool(runtime.active_claims()) or runtime.integration_repair_claim() is not None
        except (OSError, RuntimeError, ValueError):
            return True

    @staticmethod
    def _observation_detail(observation: DeliveryChangeObservation) -> str:
        code = observation.diagnostic_code
        detail = observation.diagnostic_detail or "persisted Change authority is unavailable"
        return f"{code}: {detail}" if code is not None else detail

    def _portfolio_snapshots(self) -> tuple[DeliveryPortfolioSnapshot, ...]:
        self._reconcile_runtimes()
        return self._capture_portfolio_snapshots()

    def _capture_portfolio_snapshots(self) -> tuple[DeliveryPortfolioSnapshot, ...]:
        """Capture current runtime snapshots without rediscovering persisted Changes."""
        snapshots: list[DeliveryPortfolioSnapshot] = []
        retained_snapshots: dict[str, DeliveryPortfolioSnapshot] = {}
        for change_id, runtime in sorted(self._runtimes.items()):
            try:
                snapshot = self._delivery_snapshot(runtime)
            except (OSError, RuntimeError, ValueError):
                snapshot = self._runtime_snapshots.get(change_id)
                if snapshot is None:
                    continue
                self._runtime_reconciliation_errors.setdefault(
                    change_id,
                    "Delivery runtime snapshot could not be refreshed.",
                )
            retained_snapshots[change_id] = snapshot
            snapshots.append(snapshot)
        self._runtime_snapshots = retained_snapshots
        return tuple(snapshots)

    def _execution_occupancy(self) -> int:
        """Count the largest observed active outcome claim set once per Change."""
        occupancy: dict[str, int] = {}
        for change_id, observation in self._discovered_changes.items():
            frontier = observation.frontier
            if frontier is None and change_id not in self._runtimes:
                raise DeliveryRuntimeReconciliationError(change_id, "execution occupancy is unknown")
            if frontier is not None:
                occupancy[change_id] = sum(binding.active_claim is not None for binding in frontier.bindings)
        for change_id, runtime in self._runtimes.items():
            try:
                active_count = len(runtime.active_claims())
            except (OSError, RuntimeError, ValueError):
                active_count = self._persisted_claim_occupancy(change_id)
            occupancy[change_id] = max(occupancy.get(change_id, 0), active_count)
        try:
            registered = self._coordinator.list_registered()
            for change_id in self._runtimes.keys() | self._discovered_changes.keys():
                self._coordinator.show(change_id)
        except (OSError, RuntimeError, ValueError) as exc:
            raise DeliveryRuntimeReconciliationError(None, f"execution custody is unknown: {exc}") from exc
        for coordination in registered:
            if coordination.writer is not None or (
                coordination.continuation_action is not None and coordination.continuation_action.finished_at is None
            ):
                occupancy[coordination.change_id] = max(occupancy.get(coordination.change_id, 0), 1)
        return sum(occupancy.values())

    def _persisted_claim_occupancy(self, change_id: str) -> int:
        """Count structurally valid custody without admitting incompatible runtime authority."""
        try:
            path = self._target_root / "changes" / change_id / "frontier.json"
            frontier = parse_delivery_frontier(path.read_bytes())[0]
        except (OSError, RuntimeError, ValueError) as exc:
            raise DeliveryRuntimeReconciliationError(change_id, "execution occupancy is unreadable") from exc
        return sum(binding.active_claim is not None for binding in frontier.bindings)

    def _delivery_snapshot(
        self, runtime: DeliveryRuntime, *, observe_publication: bool = True
    ) -> DeliveryPortfolioSnapshot:
        frontier_bytes = runtime.frontier_bytes()
        frontier = parse_delivery_frontier(frontier_bytes)[0]
        cached = self._publication_observation_cache.get(runtime.contract.change_id)
        observation = cached[2] if cached is not None and cached[1] == frontier.published_head else None
        if observe_publication:
            observation = self._publication_observation(runtime.contract.change_id, frontier)
        return DeliveryPortfolioSnapshot.capture(
            runtime.contract,
            frontier_bytes,
            publication_observation=observation,
        )

    def _publication_observation(
        self,
        change_id: str,
        frontier: DeliveryFrontier,
    ) -> PublicationPullRequestObservationReceipt | None:
        publisher = self._draft_pull_request_publisher
        history = frontier.change_publication_history
        published_head = frontier.published_head
        if publisher is None or history is None or published_head is None or history.current.head_sha != published_head:
            return None
        now = time.monotonic()
        cached = self._publication_observation_cache.get(change_id)
        if frontier.ready is not None:
            return cached[2] if cached is not None and cached[1] == published_head else None
        if cached is not None and cached[0] > now and cached[1] == published_head:
            return cached[2]
        try:
            observation = publisher.observe_pull_request(ObserveChangePublicationPullRequest(change_id=change_id))
        except (OSError, PublicationProviderError, RuntimeError, subprocess.SubprocessError, ValueError):
            observation = None
        if isinstance(observation, PublicationPullRequestObservationReceipt):
            snapshot = observation.snapshot
            publication = history.current
            if (
                observation.change_id != change_id
                or snapshot.repository != publication.repository
                or snapshot.number != publication.number
                or snapshot.node_id != publication.node_id
                or snapshot.head_sha != published_head
            ):
                observation = None
        else:
            observation = None
        self._publication_observation_cache[change_id] = (
            now + _PUBLICATION_OBSERVATION_CACHE_SECONDS,
            published_head,
            observation,
        )
        return observation

    def _retained_change_worktree_view(
        self,
        retained: RetainedChangeWorktree,
    ) -> DeliveryRetainedChangeWorktree:
        runtime = self._runtimes.get(retained.change_id)
        lifecycle: DeliveryChangeStage | None = None
        completion: CompletionReceipt | None = None
        completion_state_inconsistent = False
        if runtime is not None:
            try:
                lifecycle = runtime.change_stage()
            except (OSError, ValueError, DeliveryRuntimeConflictError):
                completion_state_inconsistent = True
            if not completion_state_inconsistent:
                try:
                    completion = runtime.completion_receipt()
                except (OSError, ValueError, DeliveryRuntimeConflictError):
                    completion_state_inconsistent = True
        reason = self._retained_cleanup_block_reason(
            retained,
            runtime,
            lifecycle,
            completion,
            completion_state_inconsistent=completion_state_inconsistent,
        )
        return DeliveryRetainedChangeWorktree(
            change_id=retained.change_id,
            worktree_path=retained.worktree_path,
            branch=retained.branch,
            branch_head=retained.branch_head,
            recovery_reviewed_head=retained.last_reviewed_commit,
            coordination_registered=retained.coordination_registered,
            git_registered=retained.git_registered,
            worktree_present=retained.worktree_present,
            worktree_head=retained.worktree_head,
            worktree_branch=retained.worktree_branch,
            worktree_locked=retained.worktree_locked,
            worktree_prunable=retained.worktree_prunable,
            worktree_bare=retained.worktree_bare,
            attention=retained.attention,
            lifecycle=lifecycle,
            orphan=runtime is None,
            cleanup_eligible=reason is None,
            cleanup_blocked_reason=reason,
        )

    def _retained_cleanup_block_reason(
        self,
        retained: RetainedChangeWorktree,
        runtime: DeliveryRuntime | None,
        lifecycle: DeliveryChangeStage | None,
        completion: CompletionReceipt | None,
        *,
        completion_state_inconsistent: bool,
    ) -> DeliveryRetainedWorktreeCleanupBlockReason | None:
        reason: DeliveryRetainedWorktreeCleanupBlockReason | None = None
        if runtime is None:
            reason = DeliveryRetainedWorktreeCleanupBlockReason.ORPHAN
        elif completion_state_inconsistent:
            reason = DeliveryRetainedWorktreeCleanupBlockReason.COMPLETION_STATE_INCONSISTENT
        elif completion is None and lifecycle != DeliveryChangeStage.ABANDONED:
            reason = DeliveryRetainedWorktreeCleanupBlockReason.NONTERMINAL
        elif retained.writer is not None:
            reason = DeliveryRetainedWorktreeCleanupBlockReason.ACTIVE_WRITER
        elif retained.publication_expiry is not None and retained.publication_expiry > _timestamp(self._clock()):
            reason = DeliveryRetainedWorktreeCleanupBlockReason.ACTIVE_PUBLICATION_LEASE
        elif retained.attention:
            reason = DeliveryRetainedWorktreeCleanupBlockReason.WORKTREE_ATTENTION
        return reason

    @staticmethod
    def _snapshot_change_stage(snapshot: DeliveryPortfolioSnapshot) -> DeliveryChangeStage:
        return derive_change_stage(snapshot.frontier)

    @staticmethod
    def _is_work_portfolio_visible(snapshot: DeliveryPortfolioSnapshot) -> bool:
        return snapshot.frontier.change_abandonment is None and not is_change_terminal(snapshot.frontier)

    @staticmethod
    def _snapshot_has_active_claims(snapshot: DeliveryPortfolioSnapshot) -> bool:
        return any(binding.active_claim is not None for binding in snapshot.frontier.bindings)

    @staticmethod
    def _snapshot_dependency_depth(snapshot: DeliveryPortfolioSnapshot, outcome_id: str) -> int:
        dependencies = {outcome.outcome_id: outcome.dependency_ids for outcome in snapshot.contract.outcomes}

        def depth(current: str) -> int:
            return 0 if not dependencies[current] else 1 + max(depth(item) for item in dependencies[current])

        return depth(outcome_id)

    def list_completed_changes(self, cursor: str | None = None, limit: int = 100) -> CompletedChangePage:
        """List one bounded page rebuilt from configured target history."""
        return self._completed_history().list(cursor, limit)

    def search_completed_changes(
        self,
        query: str,
        cursor: str | None = None,
        limit: int = 100,
    ) -> CompletedChangePage:
        """Search completed semantic summaries in configured target history."""
        return self._completed_history().search(query, cursor, limit)

    def show_completed_change(
        self,
        change_id: str,
        completion_id: str | None = None,
    ) -> CompletedChangeRecord:
        """Show one verified completed-history record by exact identity."""
        return self._completed_history().show(change_id, completion_id)

    def _completed_history(self) -> CompletedHistoryCatalog:
        if self._completed_history_catalog is None:
            self._fail("completed-history catalog dependency is not configured")
        return self._completed_history_catalog

    def _recover_expired_claims(
        self,
    ) -> tuple[tuple[DeliveryClaimRecoveryResult, ...], tuple[DeliveryAcquisitionFailure, ...]]:
        cutoff = _timestamp(self._clock()) - self._claim_timeout
        recoveries: list[DeliveryClaimRecoveryResult] = []
        failures: list[DeliveryAcquisitionFailure] = []
        for change_id, runtime in sorted(self._runtimes.items()):
            try:
                active_claims = runtime.active_claims()
            except (OSError, RuntimeError, ValueError) as exc:
                self._runtime_reconciliation_errors.setdefault(
                    change_id,
                    _health_detail(
                        str(exc),
                        "Delivery claim state is unavailable and requires reconciliation.",
                    ),
                )
                continue
            for outcome_id, claim in active_claims:
                try:
                    if claim.continuation or _timestamp(claim.started_at) > cutoff:
                        continue
                    if claim.worker_role in {DeliveryWorkerRole.PLANNER, DeliveryWorkerRole.BUILDER}:
                        failures.append(
                            DeliveryAcquisitionFailure(
                                change_id=change_id,
                                outcome_id=outcome_id,
                                code=DeliveryWorkerExclusionRequiredError.code,
                                detail=str(DeliveryWorkerExclusionRequiredError()),
                                retry_condition=(
                                    "Supported host-owned exclusion evidence is required before recovery."
                                ),
                            )
                        )
                        continue
                    recovered = self._recover_claim(
                        change_id,
                        outcome_id,
                        claim.attempt_id,
                        claim.claim_id,
                    )
                except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as exc:
                    failures.append(
                        DeliveryAcquisitionFailure(
                            change_id=change_id,
                            outcome_id=outcome_id,
                            attempt_id=claim.attempt_id,
                            claim_id=claim.claim_id,
                            code=getattr(exc, "code", PortfolioApplicationError.code),
                            detail=str(exc) or "expired claim recovery failed",
                            retry_condition="Retry exact claim recovery after reconciling workspace custody.",
                        )
                    )
                else:
                    recoveries.append(recovered)
                    if recovered.status == DeliveryClaimRecoveryStatus.ATTENTION:
                        attention = recovered.attention
                        if attention is None:
                            self._fail("expired claim recovery returned incomplete attention")
                        failures.append(
                            DeliveryAcquisitionFailure(
                                change_id=change_id,
                                outcome_id=outcome_id,
                                attempt_id=claim.attempt_id,
                                claim_id=claim.claim_id,
                                code=PortfolioApplicationError.code,
                                detail=attention.reason,
                                retry_condition=attention.retry_condition,
                            )
                        )
        return tuple(recoveries), tuple(failures)

    def acquire_frontier_work(self) -> DeliveryAcquisitionResult:
        """Start at most one ready claim per available execution slot."""
        with self._coordinator.acquisition_lock():
            try:
                self._execution_occupancy()
            except DeliveryRuntimeReconciliationError as exc:
                return DeliveryAcquisitionResult(
                    launch_packages=(),
                    failures=(
                        DeliveryAcquisitionFailure(
                            change_id=exc.change_id or "portfolio",
                            outcome_id="OUT-000",
                            code=exc.code,
                            detail=str(exc),
                            retry_condition=(
                                "Restore readable custody before batch acquisition; preserve unknown writers."
                            ),
                        ),
                    ),
                )
            self._coordinator.recover_pending_transactions()
            self._reconcile_runtimes()
            pre_claim_snapshots = self._capture_portfolio_snapshots()
            recoveries, recovery_failures = self._recover_expired_claims()
            failures = list(recovery_failures)
            if recoveries or recovery_failures:
                self._reconcile_runtimes()
            pending_publication_failures = self._replay_pending_state_publications()
            failures.extend(pending_publication_failures)
            occupied = self._execution_occupancy()
            available = max(self._execution_capacity - occupied, 0)
            launches: list[DeliveryLaunchPackage] = []
            for candidate in self._candidates():
                if available == 0:
                    break
                source = self._prepare_source(
                    candidate.change_id,
                    candidate.runtime,
                    candidate.binding.outcome_id,
                    candidate.role,
                    allow_dirty=candidate.role is DeliveryWorkerRole.BUILDER,
                )
                if isinstance(source, DeliveryAcquisitionFailure):
                    failures.append(source)
                    continue
                launch = self._activate_candidate(candidate, source)
                available -= 1
                if isinstance(launch, DeliveryAcquisitionFailure):
                    failures.append(launch)
                    continue
                launches.append(launch)
            self._capture_portfolio_snapshots()
            return DeliveryAcquisitionResult(
                launch_packages=tuple(launches),
                integration_attention=self._integration_attention_statuses(pre_claim_snapshots),
                recoveries=recoveries,
                failures=tuple(failures),
                health_hint=(
                    "Call delivery_health for current Delivery diagnostics."
                    if self._delivery_health_view().diagnostics
                    else None
                ),
            )

    def acquire_change_action(self, request: DeliveryContinuationRequest) -> DeliveryContinuationResult:
        """Continue one Change without recovering, dispatching, or claiming sibling work."""
        view = self.get_change(request.change_id)
        if view.kind == "unavailable":
            return DeliveryContinuationResult(
                change_id=request.change_id,
                kind="unavailable",
                reason_code=view.readiness.reason_code,
                readiness=view.readiness,
            )
        try:
            with (
                self._coordinator.acquisition_lock(),
                self._selected_action_checkpoint_lock(request.change_id),
            ):
                return self._acquire_change_action_locked(request, view.readiness)
        except DeliveryRuntimeReconciliationError as exc:
            action = view.continuation_action if exc.change_id == request.change_id else None
            reason = "engine-action-blocked" if action is not None else "execution-occupancy-unavailable"
            return DeliveryContinuationResult(
                change_id=request.change_id,
                kind="unavailable",
                reason_code=reason,
                readiness=view.readiness.model_copy(
                    update={
                        "status": "unavailable",
                        "reason_code": reason,
                        "executable": False,
                        "action": None,
                    }
                ),
                failure=DeliveryAcquisitionFailure(
                    change_id=request.change_id,
                    outcome_id="OUT-000",
                    attempt_id=action.operation_id if action is not None else None,
                    code=exc.code,
                    detail=str(exc),
                    retry_condition=(
                        "Preserve original action journals for D03 reconciliation; do not reconstruct or retry effects."
                        if action is not None
                        else "Restore readable custody through maintenance diagnosis; do not release unknown writers."
                    ),
                ),
            )
        except (DeliveryActionBusyError, DeliveryWorkerExclusionRequiredError):
            return DeliveryContinuationResult(
                change_id=request.change_id,
                kind="busy",
                reason_code="operation-in-progress",
                readiness=self.get_change(request.change_id).readiness,
            )

    def _acquire_change_action_locked(
        self, request: DeliveryContinuationRequest, observed: DeliveryReadiness
    ) -> DeliveryContinuationResult:
        self._coordinator.recover_pending_transactions()
        runtime = self._runtimes.get(request.change_id)
        if runtime is not None:
            self._reconcile_retry_results(runtime)
        replay = self._replay_continuation_action(request, observed)
        if replay is not None:
            return replay
        runtime = self._runtime(request.change_id, for_mutation=True, allow_finalizer=True)
        snapshot = self._delivery_snapshot(runtime, observe_publication=False)
        cards = self._read_projector(snapshot).group_view().items
        card = self._selected_change_card(snapshot, cards)
        readiness = card.readiness
        if readiness is None:
            self._fail("continuation readiness was not captured")

        stop = self._continuation_stop(request, runtime, readiness, repair=self._repair_proposal(snapshot))
        if stop is not None:
            return stop
        if readiness.executable and readiness.operation in {
            WorkItemActionKind.RECONCILE_CHECKPOINT,
            WorkItemActionKind.SYNC_TARGET,
            WorkItemActionKind.MARK_READY,
            WorkItemActionKind.OBSERVE_ACCEPTANCE,
        }:
            return self._acquire_engine_action(request, runtime, readiness)
        return self._acquire_continuation_worker(request, cards, readiness)

    def _acquire_continuation_worker(
        self, request: DeliveryContinuationRequest, cards: tuple[WorkItemCardView, ...], readiness: DeliveryReadiness
    ) -> DeliveryContinuationResult:
        candidate = self._continuation_candidate(request.change_id, cards)
        finalizer = readiness.executable and readiness.operation is WorkItemActionKind.FINALIZE
        role = "finalizer" if finalizer else candidate.role.value if candidate else None
        if role is None:
            kind = "human" if readiness.next_actor is WorkItemNextActor.YOU else "unsupported"
            if readiness.status in {"waiting", "running"}:
                kind = "waiting"
            return DeliveryContinuationResult(
                change_id=request.change_id, kind=kind, reason_code=readiness.reason_code, readiness=readiness
            )
        reason = None
        if role not in request.capabilities:
            reason = "host-capability-unavailable"
        elif self._execution_occupancy() >= self._execution_capacity:
            reason = "execution-capacity"
        if reason is not None:
            return DeliveryContinuationResult(
                change_id=request.change_id, kind="waiting", reason_code=reason, readiness=readiness
            )
        if finalizer:
            return self._launch_continuation_finalizer(request, readiness)
        return self._launch_continuation_candidate(request, readiness, candidate)

    def _continuation_candidate(self, change_id: str, cards: tuple[WorkItemCardView, ...]) -> _Candidate | None:
        candidate = next(iter(self._candidates(change_id)), None)
        if candidate is None:
            return None
        selected = next(item for item in cards if item.work_item_id == candidate.binding.outcome_id)
        return candidate if selected.readiness is not None and selected.readiness.executable else None

    @staticmethod
    def _continuation_operation_id(request: DeliveryContinuationRequest) -> str:
        payload = json.dumps(
            {"change_id": request.change_id, "basis": request.expected_basis.model_dump(mode="json")},
            sort_keys=True,
            separators=(",", ":"),
        )
        return f"continue-{hashlib.sha256(payload.encode()).hexdigest()}"

    def _replay_continuation_action(
        self, request: DeliveryContinuationRequest, readiness: DeliveryReadiness
    ) -> DeliveryContinuationResult | None:
        operation_id = self._continuation_operation_id(request)
        path = self._coordinator.continuation_record_path(request.change_id, operation_id)
        execution = ExecuteDeliveryChangeAction(change_id=request.change_id, operation_id=operation_id)
        action = self._read_engine_intent(execution) if path.exists() else None
        retained = self._coordinator.show(request.change_id).continuation_action
        if retained is not None:
            retained_request = ExecuteDeliveryChangeAction(
                change_id=request.change_id, operation_id=retained.operation_id
            )
            original = self._read_engine_intent(retained_request)
            if original != retained.model_copy(update={"finished_at": None}):
                raise DeliveryRuntimeReconciliationError(request.change_id, "retained continuation intent differs")
            if retained.finished_at is not None:
                result = self._read_engine_result(retained_request)
                if result is None or result.kind == "blocked":
                    raise DeliveryRuntimeReconciliationError(
                        request.change_id, "finished continuation result is missing or blocked"
                    )
        if action is None and retained is not None and retained.finished_at is None:
            action = original
        if action is None:
            return None
        result = self._read_engine_result(
            ExecuteDeliveryChangeAction(change_id=request.change_id, operation_id=action.operation_id)
        )
        if result is not None:
            self._record_engine_attempt_result(action, result)
            kinds = {"completed": "reconciled", "waiting": "human", "stale": "stale", "blocked": "unavailable"}
            return DeliveryContinuationResult(
                change_id=request.change_id,
                kind=kinds[result.kind],
                reason_code=result.reason_code,
                readiness=readiness,
                engine_result=result,
                failure=result.failure,
            )
        if retained != action:
            raise DeliveryRuntimeReconciliationError(request.change_id, "original continuation result is missing")
        return DeliveryContinuationResult(
            change_id=request.change_id,
            kind="acquired" if "engine" in request.capabilities else "waiting",
            reason_code="engine-action-pending" if "engine" in request.capabilities else "host-capability-unavailable",
            readiness=readiness,
            engine_action=action if "engine" in request.capabilities else None,
        )

    def _acquire_engine_action(
        self, request: DeliveryContinuationRequest, runtime: DeliveryRuntime, readiness: DeliveryReadiness
    ) -> DeliveryContinuationResult:
        reason = None
        pending = runtime.checkpoint_publication_state().pending_checkpoint
        if "engine" not in request.capabilities:
            reason = "host-capability-unavailable"
        elif (
            self._draft_pull_request_publisher is None
            or readiness.basis.candidate_head is None
            or readiness.basis.target_head is None
            or (
                readiness.operation in {WorkItemActionKind.RECONCILE_CHECKPOINT, WorkItemActionKind.SYNC_TARGET}
                and self._change_branch_publisher is None
            )
        ):
            reason = "engine-owner-unavailable"
        elif (
            readiness.operation is WorkItemActionKind.RECONCILE_CHECKPOINT
            and pending is not None
            and (pending.head is None or not _checkpoint_retry_ready(pending, _timestamp(self._clock())))
        ):
            reason = "checkpoint-pending"
        elif self._execution_occupancy() >= self._execution_capacity:
            reason = "execution-capacity"
        if reason is not None:
            return DeliveryContinuationResult(
                change_id=request.change_id, kind="waiting", reason_code=reason, readiness=readiness
            )
        reservation = self._reserve_engine_attempt(runtime, readiness, self._continuation_operation_id(request))
        if reservation is not None and not reservation.allowed:
            retry_status = "waiting" if reservation.reason_code in {"retry-backoff", "acceptance-wait"} else "blocked"
            retry_readiness = readiness.model_copy(
                update={
                    "status": retry_status,
                    "reason_code": (
                        reservation.reason_code
                        if reservation.reason_code
                        in {"retry-backoff", "retry-exhausted", "acceptance-wait", "retry-containment"}
                        else "retry-exhausted"
                    ),
                    "executable": False,
                    "action": None,
                    "attempts": reservation.attempts,
                    "next_eligible_at": reservation.next_eligible_at,
                    "stop_reason": reservation.stop_code.value if reservation.stop_code is not None else None,
                }
            )
            return DeliveryContinuationResult(
                change_id=request.change_id,
                kind="waiting" if retry_readiness.status == "waiting" else "unsupported",
                reason_code=retry_readiness.reason_code,
                readiness=retry_readiness,
            )
        finalization = runtime.finalization()
        action = ChangeContinuationAction(
            operation_id=self._continuation_operation_id(request),
            change_id=request.change_id,
            kind=readiness.operation.value,
            contract_digest=readiness.basis.contract_digest,
            frontier_digest=readiness.basis.frontier_digest,
            exact_head=readiness.basis.candidate_head,
            target_head=readiness.basis.target_head,
            finalization_id=finalization.finalization_id if finalization else None,
            host_id=request.host_id,
            session_id=request.session_id,
            acquired_at=self._clock(),
        )
        self._register_recovery_invocation(
            runtime, action.operation_id, action.operation_id, action.kind, action.exact_head
        )
        self._coordinator.acquire_continuation_action(action)
        return DeliveryContinuationResult(
            change_id=request.change_id, kind="acquired", reason_code="ready", readiness=readiness, engine_action=action
        )

    def _reserve_engine_attempt(
        self,
        runtime: DeliveryRuntime,
        readiness: DeliveryReadiness,
        attempt_id: str,
    ) -> RetryReservation | None:
        """Reserve a semantic engine attempt before continuation custody is published."""
        if readiness.operation is None or readiness.basis.candidate_head is None:
            return None
        finalization = runtime.finalization()
        key = RetryEpisodeKey.engine(
            runtime.contract.change_id,
            readiness.operation.value,
            readiness.basis.candidate_head,
            readiness.basis.target_head,
            finalization.finalization_id if finalization is not None else None,
        )
        failure_class = (
            RetryFailureClass.ACCEPTANCE
            if readiness.operation is WorkItemActionKind.OBSERVE_ACCEPTANCE
            else RetryFailureClass.TRANSIENT
            if readiness.operation is WorkItemActionKind.SYNC_TARGET
            else RetryFailureClass.MECHANICAL
        )
        ledger = runtime.retry_ledger(clock=self._clock)
        return ledger.reserve(
            key,
            failure_class=failure_class,
            now=self._clock(),
            attempt_id=attempt_id,
            automatic=True,
            operation_alias=attempt_id,
        )

    def _record_engine_attempt_result(
        self,
        action: ChangeContinuationAction,
        result: DeliveryEngineActionResult,
    ) -> None:
        """Account for a known engine result; unknown effects remain outside retry policy."""
        key = RetryEpisodeKey.engine(
            action.change_id,
            action.kind,
            action.exact_head,
            action.target_head,
            action.finalization_id,
        )
        ledger = RetryLedger(self._target_root, action.change_id, clock=self._clock)
        episode = ledger.episode(key)
        if episode is None:
            return
        reservation = next((item for item in episode.attempt_ids if item == action.operation_id), None)
        if reservation is None:
            return
        if result.kind == "completed":
            ledger.record_accepted_progress(reservation, now=self._clock())
        elif result.kind == "waiting" or (
            result.kind == "blocked" and result.reason_code != "engine-action-interrupted"
        ):
            ledger.record_failure(
                reservation,
                failure_code=result.reason_code,
                failure_detail=(result.failure.detail if result.failure is not None else None),
                now=self._clock(),
            )

    def _read_engine_intent(self, request: ExecuteDeliveryChangeAction) -> ChangeContinuationAction:
        path = self._coordinator.continuation_record_path(request.change_id, request.operation_id)
        try:
            action = ChangeContinuationAction.model_validate_json(path.read_bytes())
        except (OSError, ValueError) as exc:
            raise DeliveryRuntimeReconciliationError(
                request.change_id, "original continuation intent is unavailable"
            ) from exc
        if (
            action.change_id != request.change_id
            or action.operation_id != request.operation_id
            or action.finished_at is not None
        ):
            raise DeliveryRuntimeReconciliationError(request.change_id, "original continuation intent identity differs")
        return action

    def _read_engine_result(self, request: ExecuteDeliveryChangeAction) -> DeliveryEngineActionResult | None:
        path = self._coordinator.continuation_record_path(request.change_id, request.operation_id, result=True)
        if not path.exists():
            return None
        try:
            result = DeliveryEngineActionResult.model_validate_json(path.read_bytes())
        except (OSError, ValueError) as exc:
            raise DeliveryRuntimeReconciliationError(request.change_id, "continuation result is unreadable") from exc
        if result.action.operation_id != request.operation_id or result.action.change_id != request.change_id:
            raise DeliveryRuntimeReconciliationError(request.change_id, "continuation result identity differs")
        if self._read_engine_intent(request) != result.action:
            raise DeliveryRuntimeReconciliationError(request.change_id, "continuation result lacks its original intent")
        return result

    def execute_change_action(self, request: ExecuteDeliveryChangeAction) -> DeliveryEngineActionResult:
        """Execute the fixed retained owner once, or return its exact durable result."""
        with self._selected_action_checkpoint_lock(request.change_id):
            self._coordinator.recover_pending_transactions()
            existing = self._read_engine_result(request)
            if existing is not None:
                self._record_engine_attempt_result(existing.action, existing)
                return existing
            action = self._read_engine_intent(request)
            with self._coordinator.continuation_execution(action):
                result = self._execute_engine_action(action)
                self._coordinator.finish_continuation_action(
                    action, (result.model_dump_json() + "\n").encode(), self._clock(), release=result.kind != "blocked"
                )
                self._record_engine_attempt_result(action, result)
                return result

    def _execute_engine_action(self, action: ChangeContinuationAction) -> DeliveryEngineActionResult:
        try:
            if self._coordinator.continuation_action_started(action):
                return self._engine_action_failure(
                    action, "engine-action-interrupted", "Original owner result is unknown."
                )
            runtime = self._runtime(action.change_id, for_mutation=True)
            preflight = self._engine_action_preflight(action, runtime)
            if preflight is not None:
                return preflight
            if self._coordinator.start_continuation_action(action):
                result = self._invoke_engine_owner(action)
            else:
                result = self._engine_action_failure(
                    action, "engine-action-interrupted", "Original owner result is unknown."
                )
        except ChangeTargetSyncStaleError:
            return DeliveryEngineActionResult(action=action, kind="stale", reason_code="readiness-changed")
        except DeliveryAcceptanceWaitingError:
            return DeliveryEngineActionResult(action=action, kind="waiting", reason_code="merge-approval-required")
        except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as exc:
            return self._engine_action_failure(action, "engine-action-failed", str(exc), getattr(exc, "code", None))
        else:
            return result

    def _engine_action_preflight(
        self, action: ChangeContinuationAction, runtime: DeliveryRuntime
    ) -> DeliveryEngineActionResult | None:
        if runtime.active_claims() or runtime.integration_repair_claim() is not None:
            return self._engine_action_failure(action, "engine-action-failed", "An existing claim retains custody.")
        _coordination, head, _fingerprint, _paths, reason = self._workspace_manager.capture_finalization_workspace(
            action.change_id,
            tuple(
                result.completed_commit
                for binding in parse_delivery_frontier(runtime.frontier_bytes())[0].bindings
                for result in binding.results
            ),
        )
        if reason not in {None, "workspace-dirty"}:
            return self._engine_action_failure(action, "engine-action-failed", reason)
        if (
            contract_fingerprint(runtime.contract) != action.contract_digest
            or hashlib.sha256(runtime.frontier_bytes()).hexdigest() != action.frontier_digest
            or head != action.exact_head
            or self._workspace_manager.observed_target_head() != action.target_head
            or reason == "workspace-dirty"
        ):
            return DeliveryEngineActionResult(action=action, kind="stale", reason_code="readiness-changed")
        return None

    @staticmethod
    def _engine_action_failure(
        action: ChangeContinuationAction, reason: str, detail: str, code: str | None = None
    ) -> DeliveryEngineActionResult:
        return DeliveryEngineActionResult(
            action=action,
            kind="blocked",
            reason_code=reason,
            failure=DeliveryAcquisitionFailure(
                change_id=action.change_id,
                outcome_id="OUT-000",
                attempt_id=action.operation_id,
                code=code or "ERR_DELIVERY_ENGINE_ACTION_BLOCKED",
                detail=_checkpoint_error_detail(detail, "Engine operation did not complete."),
                retry_condition=(
                    "Preserve exact operation custody and owner journals. D03 repair/reconciliation is required; "
                    "do not release custody, infer worker termination, or start a replacement operation."
                ),
            ),
        )

    def _invoke_engine_owner(self, action: ChangeContinuationAction) -> DeliveryEngineActionResult:
        values = {}
        if action.kind == "reconcile-checkpoint":
            checkpoint = self.reconcile_change_checkpoint(action.change_id)
            snapshot = self._coordinator.show(action.change_id).design_package_snapshot
            if snapshot is not None and snapshot.previous_head == action.exact_head:
                values["checkpoint_snapshot"] = snapshot
            if not checkpoint.reconciled:
                return DeliveryEngineActionResult(
                    action=action,
                    kind="blocked",
                    reason_code="engine-action-incomplete",
                    checkpoint=checkpoint,
                    **values,
                )
            values["checkpoint"] = checkpoint
        elif action.kind == "sync-target":
            values["target_sync"] = self.sync_change_with_target(
                action.change_id, action.target_head, action.operation_id
            )
        elif action.kind == "mark-ready":
            values["ready"] = self.mark_change_ready(
                action.change_id,
                MarkChangePullRequestReady(
                    change_id=action.change_id,
                    operation_id=action.operation_id,
                    finalization_id=action.finalization_id,
                    exact_head=action.exact_head,
                ),
            )
        else:
            values["acceptance"] = self._observe_acceptance_once(
                action.change_id, self._runtime(action.change_id, for_mutation=True), attempt_id=action.operation_id
            )
        return DeliveryEngineActionResult(
            action=action, kind="completed", reason_code="engine-action-completed", **values
        )

    @contextmanager
    def _engine_checkpoint_lock(self, change_id: str) -> Iterator[None]:
        if self._coordinator.executing_continuation(change_id):
            yield
        else:
            with locked_roots((self._checkpoint_lock_root(change_id),)):
                yield

    def _continuation_stop(
        self,
        request: DeliveryContinuationRequest,
        runtime: DeliveryRuntime,
        readiness: DeliveryReadiness,
        *,
        repair: DeliveryRepairProposal | None,
    ) -> DeliveryContinuationResult | None:
        failure = None
        coordination = self._workspace_manager.show(request.change_id)
        if readiness.status == "unavailable" or readiness.reason_code in {
            "finalization-failed",
            "claim-custody-unreconciled",
        }:
            kind, reason = "unavailable", readiness.reason_code
        elif runtime.active_claims() or runtime.integration_repair_claim() or coordination.writer:
            kind, reason = ("unsupported", "repair-required") if repair is not None else ("busy", "active-custody")
        elif coordination.publication_lease is not None:
            kind, reason = "unsupported", "publication-reconciliation-required"
        elif readiness.basis != request.expected_basis:
            kind, reason = "stale", "readiness-changed"
        elif runtime.change_stage() in {DeliveryChangeStage.COMPLETED, DeliveryChangeStage.ABANDONED}:
            kind, reason = "terminal", "change-terminal"
        elif runtime.change_stage() is DeliveryChangeStage.DEFERRED:
            kind, reason = "waiting", "change-paused"
        elif runtime.pending_state_publication() is not None:
            failures = self._replay_pending_state_publications(request.change_id)
            kind = "unavailable" if failures else "reconciled"
            failure = failures[0] if failures else None
            reason = "state-publication-failed" if failure else "state-publication-reconciled"
        elif readiness.reason_code == "review-repair" or readiness.operation in {
            WorkItemActionKind.RECOVER_CLAIM,
            WorkItemActionKind.RESOLVE_ATTENTION,
        }:
            kind, reason = "unsupported", "repair-required"
        else:
            return None
        return DeliveryContinuationResult(
            change_id=request.change_id, kind=kind, reason_code=reason, readiness=readiness, failure=failure
        )

    def _launch_continuation_finalizer(
        self, request: DeliveryContinuationRequest, readiness: DeliveryReadiness
    ) -> DeliveryContinuationResult:
        context = self.show_finalization_context(request.change_id)
        if context.readiness.basis != readiness.basis or not context.ready_for_finalization:
            return DeliveryContinuationResult(
                change_id=request.change_id,
                kind="stale",
                reason_code="readiness-changed",
                readiness=context.readiness,
            )
        runtime = self._runtime(request.change_id)
        finalizer_attempt_id = self._identity_factory()
        key = RetryEpisodeKey.engine(
            request.change_id,
            WorkItemActionKind.FINALIZE.value,
            context.change_head,
            self._workspace_manager.observed_target_head(),
            runtime.finalization().finalization_id if runtime.finalization() is not None else None,
        )
        reservation = runtime.retry_ledger(clock=self._clock).reserve(
            key,
            failure_class=RetryFailureClass.MECHANICAL,
            now=self._clock(),
            attempt_id=finalizer_attempt_id,
            automatic=True,
            operation_alias=finalizer_attempt_id,
        )
        if not reservation.allowed:
            retry_status = "waiting" if reservation.reason_code in {"retry-backoff", "acceptance-wait"} else "blocked"
            retry_reason = (
                reservation.reason_code
                if reservation.reason_code
                in {"retry-backoff", "retry-exhausted", "acceptance-wait", "retry-containment"}
                else "retry-exhausted"
            )
            blocked = readiness.model_copy(
                update={
                    "status": retry_status,
                    "reason_code": retry_reason,
                    "executable": False,
                    "action": None,
                    "attempts": reservation.attempts,
                    "next_eligible_at": reservation.next_eligible_at,
                    "stop_reason": reservation.stop_code.value if reservation.stop_code is not None else None,
                }
            )
            return DeliveryContinuationResult(
                change_id=request.change_id,
                kind="unsupported",
                reason_code=blocked.reason_code,
                readiness=blocked,
            )
        attempt = ChangeFinalizationAttempt(
            writer=ChangeWriter(
                attempt_id=finalizer_attempt_id,
                claim_id=self._identity_factory(),
                actor_id=request.host_id,
                process_id=request.session_id,
                claimed_at=self._clock(),
                job_id=1,
                kind="finalize",
            ),
            contract_digest=readiness.basis.contract_digest,
            frontier_digest=readiness.basis.frontier_digest,
            exact_head=context.change_head,
            target_head=self._workspace_manager.observed_target_head(),
        )
        self._register_recovery_invocation(
            self._runtime(request.change_id),
            attempt.writer.claim_id,
            attempt.writer.attempt_id,
            "finalizer",
            attempt.exact_head,
        )
        self._coordinator.acquire(request.change_id, attempt.writer, finalization_attempt=attempt)
        return DeliveryContinuationResult(
            change_id=request.change_id,
            kind="acquired",
            reason_code="ready",
            readiness=readiness,
            finalization=DeliveryFinalizationLaunch(attempt=attempt, context=context),
        )

    def _launch_continuation_candidate(
        self, request: DeliveryContinuationRequest, readiness: DeliveryReadiness, candidate: _Candidate
    ) -> DeliveryContinuationResult:
        source = self._prepare_source(
            candidate.change_id,
            candidate.runtime,
            candidate.binding.outcome_id,
            candidate.role,
            allow_dirty=candidate.role is DeliveryWorkerRole.BUILDER,
        )
        if isinstance(source, DeliveryAcquisitionFailure):
            return DeliveryContinuationResult(
                change_id=request.change_id,
                kind="unavailable",
                reason_code="source-unavailable",
                readiness=readiness,
                failure=source,
            )
        if source.source_head != request.expected_basis.source_head:
            return DeliveryContinuationResult(
                change_id=request.change_id, kind="stale", reason_code="source-head-changed", readiness=readiness
            )
        launch = self._activate_candidate(
            candidate,
            source,
            expected_frontier_digest=request.expected_basis.frontier_digest,
            host_identity=(request.host_id, request.session_id),
        )
        if isinstance(launch, DeliveryAcquisitionFailure):
            return self._continuation_launch_failure(candidate, readiness, launch)
        return DeliveryContinuationResult(
            change_id=request.change_id, kind="acquired", reason_code="ready", readiness=readiness, launch=launch
        )

    def _continuation_launch_failure(
        self, candidate: _Candidate, readiness: DeliveryReadiness, failure: DeliveryAcquisitionFailure
    ) -> DeliveryContinuationResult:
        try:
            snapshot = self._delivery_snapshot(candidate.runtime)
            cards = self._read_projector(snapshot).group_view().items
            current = self._selected_change_card(snapshot, cards).readiness
        except (OSError, RuntimeError, ValueError):
            current = readiness
        if failure.code == "ERR_DELIVERY_RETRY_EXHAUSTED" and current.reason_code in {
            "retry-backoff",
            "retry-exhausted",
            "retry-containment",
        }:
            return DeliveryContinuationResult(
                change_id=candidate.change_id,
                kind="waiting" if current.status == "waiting" else "unsupported",
                reason_code=current.reason_code,
                readiness=current,
            )
        return DeliveryContinuationResult(
            change_id=candidate.change_id,
            kind="unavailable",
            reason_code="claim-activation-failed",
            readiness=current.model_copy(
                update={
                    "status": "blocked",
                    "reason_code": "claim-activation-failed",
                    "executable": False,
                    "action": None,
                }
            ),
            failure=failure,
        )

    def acquire_actions(self, selection: DeliveryActionSelection | None = None) -> DeliveryAcquisitionResult:
        """Acquire a fenced selected action, or the explicitly requested portfolio batch."""
        if selection is None:
            return self.acquire_frontier_work()
        with (
            self._coordinator.acquisition_lock(),
            self._selected_action_checkpoint_lock(selection.change_id),
        ):
            runtime = self._runtime(selection.change_id, for_mutation=True)
            if runtime.active_claims() or runtime.integration_repair_claim() is not None:
                return DeliveryAcquisitionResult(
                    launch_packages=(),
                    failures=(
                        DeliveryAcquisitionFailure(
                            change_id=selection.change_id,
                            outcome_id=selection.outcome_id,
                            code="ERR_DELIVERY_ACTION_ALREADY_ACTIVE",
                            detail=(
                                "The selected Change already has an active claim; "
                                "no worker was dispatched by this call."
                            ),
                            retry_condition=(
                                "Inspect get_change before continuing. Do not redispatch an existing worker or recover "
                                "its claim without establishing that the worker has stopped."
                            ),
                        ),
                    ),
                )
            if hashlib.sha256(runtime.frontier_bytes()).hexdigest() != selection.expected_frontier_digest:
                message = "selected action frontier changed; refresh the selection"
                raise DeliveryActionSelectionConflictError(message)
            failures = self._replay_pending_state_publications(selection.change_id)
            if failures:
                return DeliveryAcquisitionResult(launch_packages=(), failures=failures)
            candidate = next(
                iter(self._candidates(selection.change_id)),
                None,
            )
            if candidate is None:
                self._fail("selected Change has no currently claimable action")
            if (
                candidate.binding.outcome_id != selection.outcome_id
                or candidate.binding.stage != selection.expected_stage
                or candidate.task_id != selection.expected_task_id
            ):
                message = "selected action does not match the next eligible outcome, stage, and task"
                raise DeliveryActionSelectionConflictError(message)
            if self._execution_occupancy() >= self._execution_capacity:
                message = "selected action is waiting for execution capacity"
                raise DeliveryCapacityWaitingError(message)
            return self._acquire_selected_candidate(candidate, selection)

    @contextmanager
    def _selected_action_checkpoint_lock(self, change_id: str) -> Iterator[None]:
        with ExitStack() as stack:
            try:
                stack.enter_context(locked_roots((self._checkpoint_lock_root(change_id),), blocking=False))
            except BlockingIOError as exc:
                message = "selected Change has an operation in progress; retry after that operation finishes"
                raise DeliveryActionBusyError(message) from exc
            yield

    def _acquire_selected_candidate(
        self,
        candidate: _Candidate,
        selection: DeliveryActionSelection,
    ) -> DeliveryAcquisitionResult:
        source = self._prepare_source(
            candidate.change_id,
            candidate.runtime,
            candidate.binding.outcome_id,
            candidate.role,
            allow_dirty=candidate.role is DeliveryWorkerRole.BUILDER,
        )
        if isinstance(source, DeliveryAcquisitionFailure):
            return DeliveryAcquisitionResult(launch_packages=(), failures=(source,))
        if source.source_head != selection.expected_source_head:
            message = "selected action source head changed; refresh the selection"
            raise DeliveryActionSelectionConflictError(message)
        if hashlib.sha256(candidate.runtime.frontier_bytes()).hexdigest() != selection.expected_frontier_digest:
            message = "selected action frontier changed during source preparation; refresh the selection"
            raise DeliveryActionSelectionConflictError(message)
        launch = self._activate_candidate(
            candidate,
            source,
            expected_frontier_digest=selection.expected_frontier_digest,
        )
        if isinstance(launch, DeliveryAcquisitionFailure):
            return DeliveryAcquisitionResult(launch_packages=(), failures=(launch,))
        return DeliveryAcquisitionResult(launch_packages=(launch,))

    def _replay_pending_state_publications(
        self, selected_change_id: str | None = None
    ) -> tuple[DeliveryAcquisitionFailure, ...]:
        """Replay durable local state publications before exposing new claims."""
        failures = []
        for change_id, runtime in sorted(
            self._runtimes.items()
            if selected_change_id is None
            else ((selected_change_id, self._runtimes[selected_change_id]),)
        ):
            failure = self._replay_pending_state_publication(change_id, runtime)
            if failure is not None:
                failures.append(failure)
        return tuple(failures)

    def _replay_pending_state_publication(
        self, change_id: str, runtime: DeliveryRuntime
    ) -> DeliveryAcquisitionFailure | None:
        context = self._pending_state_publication_context(change_id, runtime)
        if context is None:
            return None
        if isinstance(context, DeliveryAcquisitionFailure):
            return context
        pending, current_digest, publisher = context
        if publisher is None:
            return self._handle_unpublished_pending_state(
                change_id,
                runtime,
                pending,
                current_digest,
            )
        if current_digest != pending.frontier_digest:
            reconciled = self._reconcile_pending_state_publication(
                change_id,
                runtime,
                pending,
                current_digest,
                publisher,
            )
            if isinstance(reconciled, DeliveryAcquisitionFailure):
                return reconciled
            pending, current_digest = reconciled
        try:
            remote_head = self._pending_publication_remote_head(
                change_id,
                pending,
                current_frontier_digest=current_digest,
            )
            self._publish_delivery_state(
                change_id,
                runtime,
                f"replay-state-{pending.frontier_digest}",
                expected_remote_head=remote_head,
            )
        except (OSError, RuntimeError, subprocess.SubprocessError, TypeError, ValueError) as exc:
            return DeliveryAcquisitionFailure(
                change_id=change_id,
                outcome_id="OUT-000",
                code=getattr(exc, "code", PortfolioApplicationError.code),
                detail=str(exc),
                retry_condition="Retry Delivery-state publication replay.",
            )
        return None

    def _pending_state_publication_context(
        self, change_id: str, runtime: DeliveryRuntime
    ) -> tuple[DeliveryPendingStatePublication, str, DeliveryStatePublisher | None] | DeliveryAcquisitionFailure | None:
        try:
            pending = runtime.pending_state_publication()
        except (OSError, RuntimeError, ValueError) as exc:
            return DeliveryAcquisitionFailure(
                change_id=change_id,
                outcome_id="OUT-000",
                code=getattr(exc, "code", PortfolioApplicationError.code),
                detail=f"Delivery-state publication intent is invalid: {exc}",
                retry_condition="Repair the local Delivery-state publication intent.",
            )
        if pending is None:
            return None
        if change_id in self._runtime_reconciliation_errors:
            return DeliveryAcquisitionFailure(
                change_id=change_id,
                outcome_id="OUT-000",
                code=PortfolioApplicationError.code,
                detail=self._runtime_reconciliation_errors[change_id],
                retry_condition="Resolve the retained Delivery reconciliation attention.",
            )
        if pending.base_frontier_digest is None:
            return DeliveryAcquisitionFailure(
                change_id=change_id,
                outcome_id="OUT-000",
                code=PortfolioApplicationError.code,
                detail="Pending Delivery-state publication lacks its pre-mutation frontier boundary.",
                retry_condition="Repair the local Delivery-state publication intent.",
            )
        return (
            pending,
            hashlib.sha256(runtime.frontier_bytes()).hexdigest(),
            self._delivery_state_publisher,
        )

    def _handle_unpublished_pending_state(
        self,
        change_id: str,
        runtime: DeliveryRuntime,
        pending: DeliveryPendingStatePublication,
        current_digest: str,
    ) -> DeliveryAcquisitionFailure | None:
        if current_digest == pending.frontier_digest:
            runtime.acknowledge_pending_publication(current_digest)
            return None
        return DeliveryAcquisitionFailure(
            change_id=change_id,
            outcome_id="OUT-000",
            code=PortfolioApplicationError.code,
            detail="Delivery-state publication publisher is unavailable; pending publication is retained.",
            retry_condition="Restore the Delivery-state publisher before replaying publication.",
        )

    def _reconcile_pending_state_publication(
        self,
        change_id: str,
        runtime: DeliveryRuntime,
        pending: DeliveryPendingStatePublication,
        current_digest: str,
        publisher: DeliveryStatePublisher,
    ) -> tuple[DeliveryPendingStatePublication, str] | DeliveryAcquisitionFailure:
        try:
            inventory = publisher.read_snapshot_inventory()
            snapshot = next(
                (item for item in inventory.snapshots if item.change_id == change_id),
                None,
            )
            remote_digest = (
                None if snapshot is None else hashlib.sha256(_canonical_model_bytes(snapshot.frontier)).hexdigest()
            )
        except (OSError, RuntimeError, subprocess.SubprocessError, TypeError, ValueError) as exc:
            return DeliveryAcquisitionFailure(
                change_id=change_id,
                outcome_id="OUT-000",
                code=getattr(exc, "code", PortfolioApplicationError.code),
                detail=str(exc),
                retry_condition="Retry Delivery-state publication replay.",
            )
        if remote_digest == pending.frontier_digest:
            runtime.reanchor_pending_publication(pending.frontier_digest)
            pending = runtime.pending_state_publication()
            if pending is not None:
                current_digest = hashlib.sha256(runtime.frontier_bytes()).hexdigest()
        elif remote_digest == current_digest:
            runtime.reanchor_pending_publication(current_digest)
            pending = runtime.pending_state_publication()
            if pending is not None:
                current_digest = hashlib.sha256(runtime.frontier_bytes()).hexdigest()
        if pending is not None and current_digest == pending.frontier_digest:
            return pending, current_digest
        return DeliveryAcquisitionFailure(
            change_id=change_id,
            outcome_id="OUT-000",
            code=PortfolioApplicationError.code,
            detail="Pending Delivery-state publication does not match the current frontier.",
            retry_condition="Reconcile the local frontier and its pending publication intent.",
        )

    def _pending_publication_remote_head(
        self,
        change_id: str,
        pending: DeliveryPendingStatePublication,
        current_frontier_digest: str | None = None,
    ) -> str:
        """Return the remote state head only when its snapshot matches the pending base."""
        publisher = self._delivery_state_publisher
        if publisher is None:
            self._fail("pending Delivery-state publication has no configured publisher")
        inventory = publisher.read_snapshot_inventory()
        snapshot = next(
            (item for item in inventory.snapshots if item.change_id == change_id),
            None,
        )
        if inventory.remote_head is None or snapshot is None:
            self._fail("remote Delivery snapshot is unavailable for pending replay")
        remote_digest = hashlib.sha256(_canonical_model_bytes(snapshot.frontier)).hexdigest()
        if remote_digest not in {pending.base_frontier_digest, current_frontier_digest}:
            self._fail("remote Delivery snapshot no longer matches the pending publication base")
        return inventory.remote_head

    def show_plan_context(
        self,
        change_id: str,
        outcome_id: str,
        attempt_id: str,
        claim_id: str,
    ) -> DeliveryPlanContext:
        """Project exact same-outcome Planning authority for one active claim."""
        runtime = self._runtime(change_id)
        binding = runtime.require_active_claim(outcome_id, attempt_id, claim_id)
        if binding.stage != DeliveryStage.PLANNING:
            self._fail("active claim is not Planning work")
        launch = self._current_launch(change_id, runtime, binding)
        outcome = self._outcome(runtime, outcome_id)
        return DeliveryPlanContext(
            launch=launch,
            outcome=outcome,
            commitments=self._commitments(runtime, outcome.commitment_ids),
            requests=binding.requests,
            return_context=binding.return_context,
        )

    def show_build_context(
        self,
        change_id: str,
        outcome_id: str,
        attempt_id: str,
        claim_id: str,
    ) -> DeliveryBuildContext:
        """Project exact task and predecessor authority for one active Build claim."""
        runtime = self._runtime(change_id)
        binding = runtime.require_active_claim(outcome_id, attempt_id, claim_id)
        if binding.stage != DeliveryStage.IMPLEMENTATION or binding.active_task_id is None:
            self._fail("active claim is not Build work")
        launch = self._current_launch(change_id, runtime, binding)
        task = next(item for item in binding.tasks if item.task_id == binding.active_task_id)
        predecessor_task_ids = set(task.dependency_ids)
        outcome = self._outcome(runtime, outcome_id)
        dependency_outcomes = set(outcome.dependency_ids)
        predecessor_results = tuple(
            result
            for candidate in runtime.contract.outcomes
            for result in runtime.show_binding(candidate.outcome_id).results
            if result.task_id in predecessor_task_ids or candidate.outcome_id in dependency_outcomes
        )
        return DeliveryBuildContext(
            launch=launch,
            task=task,
            task_digest=task.digest,
            commitments=self._commitments(runtime, task.commitment_ids),
            predecessor_results=predecessor_results,
            requests=binding.requests,
            return_context=binding.return_context,
            recovery_attention=binding.recovery_attention,
        )

    def _repair_proposal(self, snapshot: DeliveryPortfolioSnapshot) -> DeliveryRepairProposal | None:
        cutoff = _timestamp(self._clock()) - self._claim_timeout
        return next(
            (
                DeliveryRepairProposal.create(
                    kind=DeliveryRepairKind.CONFIRM_LOST_WORKER,
                    change_id=snapshot.contract.change_id,
                    outcome_id=binding.outcome_id,
                    attempt_id=claim.attempt_id,
                    claim_id=claim.claim_id,
                    expected_frontier_digest=snapshot.version,
                    summary="Recovery requires supported host-owned exclusion of the stale Builder invocation.",
                    consequence=(
                        "Custody and files remain unchanged without verified exclusion of every descendant writer "
                        "and outstanding tool job. Caller confirmation alone cannot authorize recovery."
                    ),
                )
                for binding in snapshot.frontier.bindings
                if (claim := binding.active_claim) is not None
                and not claim.continuation
                and claim.worker_role is DeliveryWorkerRole.BUILDER
                and _timestamp(claim.started_at) <= cutoff
            ),
            None,
        )

    def _selected_change_card(
        self, snapshot: DeliveryPortfolioSnapshot, cards: tuple[WorkItemCardView, ...]
    ) -> WorkItemCardView:
        proposal = self._repair_proposal(snapshot)
        if proposal is not None:
            return next(card for card in cards if card.work_item_id == proposal.outcome_id)
        return next((card for card in cards if card.item_key == "publication"), cards[0])

    def repair_change(
        self,
        change_id: str,
        proposal_id: str | None = None,
        *,
        confirmed_lost: bool = False,  # noqa: ARG002 - retained request shape is not evidence.
    ) -> DeliveryRepairResult:
        """Diagnose or apply one exact stale-Builder recovery proposal."""
        if proposal_id is not None:
            replay = self._completed_claim_recovery(change_id, proposal_id=proposal_id)
            if replay is not None:
                return DeliveryRepairResult(change_id=change_id, recovery=replay)
        with self._coordinator.acquisition_lock():
            runtime = self._runtime(change_id, for_mutation=proposal_id is not None)
            frontier_bytes = runtime.frontier_bytes()
            digest = hashlib.sha256(frontier_bytes).hexdigest()
            proposal = self._repair_proposal(DeliveryPortfolioSnapshot.capture(runtime.contract, frontier_bytes))
            if proposal_id is None:
                return DeliveryRepairResult(change_id=change_id, proposal=proposal)
            if proposal is None or proposal.proposal_id != proposal_id:
                self._fail("repair proposal is stale or unavailable")
            if digest != proposal.expected_frontier_digest:
                self._fail("repair proposal frontier changed")
            if proposal.kind is not DeliveryRepairKind.CONFIRM_LOST_WORKER:
                self._fail("repair proposal kind is unsupported")
            recovery = self._recover_claim(
                change_id,
                proposal.outcome_id,
                proposal.attempt_id,
                proposal.claim_id,
            )
            return DeliveryRepairResult(change_id=change_id, recovery=recovery)

    def repair(
        self,
        change_id: str,
        proposal_id: str | None = None,
        *,
        confirmed_lost: bool = False,
    ) -> DeliveryRepairResult:
        """Diagnose or apply one high-level repair proposal."""
        return self.repair_change(change_id, proposal_id, confirmed_lost=confirmed_lost)

    def repair_completed_outcome(
        self,
        change_id: str,
        request: PrepareCompletedOutcomeRepair,
    ) -> OutcomeAuthorityBinding:
        """Apply the fenced engine-derived repair-task route for a completed outcome."""
        with self._coordinator.acquisition_lock(), locked_roots((self._checkpoint_lock_root(change_id),)):
            runtime = self._runtime(change_id, for_mutation=True, allow_finalizer=True)
            if request.outcome_id not in {binding.outcome_id for binding in runtime.bindings()}:
                self._fail("completed-outcome repair references an unknown outcome")
            replay = runtime.has_completed_outcome_repair(request)
            if not replay:
                self._validate_completed_outcome_repair_request(change_id, runtime, request)
            binding = runtime.prepare_completed_outcome_repair(request)
            # A replay after the publication acknowledgment must not invoke the
            # provider again.  An unacknowledged local intent remains retryable.
            if not replay or runtime.pending_state_publication() is not None:
                self._publish_delivery_state(
                    change_id,
                    runtime,
                    _checkpoint_operation_id(
                        "completed-outcome-repair", change_id, request.outcome_id, request.attempt_id
                    ),
                )
            return binding

    def _validate_completed_outcome_repair_request(
        self,
        change_id: str,
        runtime: DeliveryRuntime,
        request: PrepareCompletedOutcomeRepair,
    ) -> None:
        """Require engine-owned failure evidence before reopening completed work."""
        coordination = self._workspace_manager.show(change_id)
        writer = coordination.writer
        attempt = coordination.finalization_attempt
        if runtime.active_claims() or runtime.integration_repair_claim() is not None:
            self._fail("completed-outcome repair cannot overlap another active Delivery claim")
        if (
            attempt is None
            or attempt.writer.attempt_id != request.original_action_id
            or writer is not None
            or attempt.finished_at is None
        ):
            self._fail("completed-outcome repair requires the matching failed finalizer record")
        try:
            reports = FinalizationReportStore(self._target_root, change_id).read().reports
            preservation = self._workspace_manager.verify_preservation(change_id, request.preservation_id)
        except (FinalizationReportError, OSError, RuntimeError, ValueError) as exc:
            self._fail("completed-outcome repair evidence is unavailable", exc)
        matching = tuple(report for report in reports if report.request.attempt_key == request.original_action_id)
        if not matching:
            self._fail("completed-outcome repair requires a recorded finalization failure")
        report = matching[-1]
        if (
            report.request.change_id != change_id
            or report.request.code.value != request.defect_code
            or report.request.expected_frontier_digest != request.expected_frontier_digest
            or report.request.expected_contract_digest != contract_fingerprint(runtime.contract)
            or report.request.expected_change_head != attempt.exact_head
        ):
            self._fail("completed-outcome repair defect is not derived from the finalization failure")
        if request.finding_boundary == "proof-procedure" and report.request.category != "proof-mutation":
            self._fail("proof-procedure repair requires a proof-mutation diagnostic")
        if request.finding_boundary == "implementation" and report.request.category == "proof-mutation":
            self._fail("implementation repair cannot consume a proof-procedure diagnostic")
        if preservation.preservation_id != request.preservation_id:
            self._fail("completed-outcome repair preservation identity is stale")
        if runtime.change_stage() is DeliveryChangeStage.COMPLETED:
            self._fail("completed-outcome repair requires a nonterminal Change")
        self._validate_completed_outcome_repair_retry(runtime, request)

    def _validate_completed_outcome_repair_retry(
        self,
        runtime: DeliveryRuntime,
        request: PrepareCompletedOutcomeRepair,
    ) -> None:
        """Require a pending mechanical repair reservation for the failed finalizer episode."""
        try:
            ledger = runtime.retry_ledger(clock=self._clock)
            summary = ledger.read()
            pending = ledger.pending_attempts()
        except (OSError, RetryLedgerConflictError, RetryLedgerCorruptError, RuntimeError, ValueError) as exc:
            self._fail("completed-outcome repair retry authority is unavailable", exc)
        episodes = tuple(
            episode
            for episode in summary.episodes
            if request.original_action_id in episode.attempt_ids
        )
        if len(episodes) != 1:
            self._fail("completed-outcome repair is not bound to one retry episode")
        episode = episodes[0]
        if (
            request.episode_id != episode.episode_id
            or episode.failure_class is not RetryFailureClass.MECHANICAL
            or digest(f"{request.original_action_id}:failed".encode()) not in episode.outcome_ids
        ):
            self._fail("completed-outcome repair does not match the failed retry episode")
        repair_attempts = tuple(item for item in pending if item.attempt_id == request.attempt_id)
        if (
            len(repair_attempts) != 1
            or repair_attempts[0].episode_id != episode.episode_id
            or repair_attempts[0].kind != "repair"
            or repair_attempts[0].failure_class is not RetryFailureClass.MECHANICAL
        ):
            self._fail("completed-outcome repair requires a pending mechanical retry reservation")

    def _unavailable_change(
        self, change_id: str, reason: Literal["runtime-unavailable", "coordination-unavailable"] = "runtime-unavailable"
    ) -> DeliveryUnavailableChangeView:
        observation = self._discovered_changes.get(change_id)
        runtime = self._runtimes.get(change_id)
        contract = (
            observation.contract if observation is not None else runtime.contract if runtime is not None else None
        )
        coordination_status = None
        if reason == "coordination-unavailable":
            try:
                if self._coordinator.find_registered(change_id) is None:
                    coordination_status = "missing"
            except (OSError, RuntimeError, ValueError):
                coordination_status = "unreadable"
        return DeliveryUnavailableChangeView(
            change_id=change_id,
            title=contract.title if contract is not None else None,
            diagnostics=(reason,),
            coordination_status=coordination_status,
            readiness=DeliveryReadiness(
                status="unavailable",
                next_actor=WorkItemNextActor.NONE,
                reason_code=reason,
                checks_state="unknown",
                basis=DeliveryReadinessBasis(contract_digest=contract_fingerprint(contract) if contract else None),
            ),
        )

    def get_change(self, change_id: str) -> DeliveryChangeView | DeliveryUnavailableChangeView:
        """Return one coherent Change view without requiring caller-side projection joins."""
        self._reconcile_runtimes()
        observation = self._discovered_changes.get(change_id)
        if observation is not None and (not observation.actionable_runtime or change_id not in self._runtimes):
            return self._unavailable_change(change_id)
        runtime = self._runtime(change_id)
        try:
            coordination = self._workspace_manager.show(change_id)
        except (OSError, RuntimeError, ValueError):
            return self._unavailable_change(change_id, "coordination-unavailable")
        snapshot = self._delivery_snapshot(runtime)
        proposal = self._repair_proposal(snapshot)
        projector = self._read_projector(snapshot)
        frontier_digest = snapshot.version
        items = projector.group_view().items
        if not items:
            self._fail(f"Change has no projected work items: {change_id}")
        item_key = self._selected_change_card(snapshot, items).item_key
        detail = self._captured_detail(runtime, projector, item_key)
        health = self._delivery_health_view(scoped_change_id=change_id, inspect_workspaces=False)
        unresolved_outcomes = tuple(
            DeliveryUnresolvedOutcome(
                outcome_id=outcome_detail.card.work_item_id,
                card=outcome_detail.card,
                requests=tuple(request for request in outcome_detail.requests if request.resolution is None),
                block=outcome_detail.block if outcome_detail.block and not outcome_detail.block.resolved else None,
                active_claim=outcome_detail.active_claim,
                recovery_attention=outcome_detail.recovery_attention,
            )
            for card in items
            if card.scope is WorkItemScope.OUTCOME
            for outcome_detail in (projector.show_view(card.item_key),)
            if (
                any(request.resolution is None for request in outcome_detail.requests)
                or (outcome_detail.block is not None and not outcome_detail.block.resolved)
                or outcome_detail.active_claim is not None
                or outcome_detail.recovery_attention is not None
            )
        )
        return DeliveryChangeView(
            change_id=change_id,
            finalization_attempt=coordination.finalization_attempt,
            continuation_action=coordination.continuation_action,
            frontier_digest=frontier_digest,
            detail=detail,
            health=health,
            repair=DeliveryRepairResult(change_id=change_id, proposal=proposal) if proposal is not None else None,
            unresolved_outcomes=unresolved_outcomes,
            readiness=detail.readiness,
        )

    def set_change_intent(self, intent: DeliveryChangeIntent) -> DeliveryChangeIntentResult:
        """Apply one version-bound user lifecycle intent through the owning runtime."""
        with self._coordinator.acquisition_lock():
            runtime = self._runtime(intent.change_id, for_mutation=True)
            with locked_roots((self._checkpoint_lock_root(intent.change_id),)):
                current_digest = hashlib.sha256(runtime.frontier_bytes()).hexdigest()
                if current_digest != intent.expected_frontier_digest:
                    if intent.kind is DeliveryChangeIntentKind.DEFER:
                        receipt = runtime.change_deferral()
                        if receipt is not None and receipt.reason == intent.reason:
                            return DeliveryChangeIntentResult(
                                change_id=intent.change_id,
                                kind=intent.kind,
                                frontier_digest=current_digest,
                                receipt=receipt,
                            )
                    elif intent.kind is DeliveryChangeIntentKind.ABANDON:
                        receipt = runtime.change_abandonment()
                        if receipt is not None and receipt.reason == intent.reason:
                            return DeliveryChangeIntentResult(
                                change_id=intent.change_id,
                                kind=intent.kind,
                                frontier_digest=current_digest,
                                receipt=receipt,
                            )
                    self._fail("Change intent frontier changed")
                if intent.kind is DeliveryChangeIntentKind.DEFER:
                    if intent.reason is None:
                        self._fail("defer intent requires a reason")
                    receipt = runtime.defer_change(intent.reason, _timestamp(self._clock()))
                elif intent.kind is DeliveryChangeIntentKind.RESUME:
                    receipt = runtime.resume_change()
                else:
                    if intent.reason is None:
                        self._fail("abandon intent requires a reason")
                    receipt = runtime.abandon_change(intent.reason, _timestamp(self._clock()))
                self._publish_delivery_state(
                    intent.change_id,
                    runtime,
                    _checkpoint_operation_id(intent.kind.value, intent.change_id, receipt.model_dump_json()),
                )
                return DeliveryChangeIntentResult(
                    change_id=intent.change_id,
                    kind=intent.kind,
                    frontier_digest=hashlib.sha256(runtime.frontier_bytes()).hexdigest(),
                    receipt=receipt,
                )

    def submit_result(self, submission: DeliveryResultSubmission) -> DeliveryResultSubmissionResult:
        """Publish and promote one exact Builder result as one claim-bound operation."""
        with self._coordinator.acquisition_lock():
            runtime = self._runtime(submission.change_id, for_mutation=True)
            with locked_roots((self._checkpoint_lock_root(submission.change_id),)):
                self._import_legacy_worker_budgets(runtime)
                binding = runtime.show_binding(submission.outcome_id)
                existing = next(
                    (item for item in binding.results if item.task_id == submission.result.task_id),
                    None,
                )
                if existing is not None:
                    if existing != submission.result or (
                        binding.active_claim is not None and binding.active_claim.task_id == submission.result.task_id
                    ):
                        self._fail("submitted result conflicts with current Outcome authority")
                    runtime.require_result_replay(submission.outcome_id, submission.claim_id, submission.result)
                    self._record_worker_retry_success(runtime, submission.outcome_id, submission.claim_id)
                    if runtime.pending_state_publication() is not None:
                        self._publish_delivery_state(
                            submission.change_id,
                            runtime,
                            _checkpoint_operation_id(
                                "submit-result",
                                submission.change_id,
                                submission.outcome_id,
                                submission.result.result_id,
                            ),
                        )
                    return DeliveryResultSubmissionResult(
                        change_id=submission.change_id,
                        outcome_id=submission.outcome_id,
                        claim_id=submission.claim_id,
                        result_id=submission.result.result_id,
                        binding=binding,
                    )
                candidate = runtime.publish_result(
                    PublishDeliveryResult(
                        outcome_id=submission.outcome_id,
                        claim_id=submission.claim_id,
                        result=submission.result,
                    )
                )
                binding = runtime.transition(
                    AdvanceDelivery(
                        action="advance",
                        outcome_id=submission.outcome_id,
                        claim_id=submission.claim_id,
                        output=candidate.output,
                    ),
                    retry_observed_at=self._clock(),
                )
                self._record_worker_retry_success(runtime, submission.outcome_id, submission.claim_id)
                self._publish_delivery_state(
                    submission.change_id,
                    runtime,
                    _checkpoint_operation_id(
                        "submit-result",
                        submission.change_id,
                        submission.outcome_id,
                        submission.result.result_id,
                    ),
                )
                return DeliveryResultSubmissionResult(
                    change_id=submission.change_id,
                    outcome_id=submission.outcome_id,
                    claim_id=submission.claim_id,
                    result_id=submission.result.result_id,
                    binding=binding,
                )

    def answer(self, answer: DeliveryAnswer) -> DeliveryAnswerResult:  # noqa: C901, PLR0911
        """Apply one version-bound request answer or requestless block evidence."""
        with self._coordinator.acquisition_lock():
            runtime = self._runtime(answer.change_id, for_mutation=True)
            checkpoint_lock = (
                self._attention_resolution_lock(answer.change_id)
                if answer.kind is DeliveryAnswerKind.DISPOSITION
                else locked_roots((self._checkpoint_lock_root(answer.change_id),))
            )
            with checkpoint_lock:
                current_digest = hashlib.sha256(runtime.frontier_bytes()).hexdigest()
                if answer.kind is DeliveryAnswerKind.REQUEST:
                    current = self._request(runtime, answer.request_id)
                    if current.kind is DeliveryRequestKind.DECISION and (
                        answer.resolution.selected_option_id is None or answer.resolution.response_text is not None
                    ):
                        self._fail("Decision answers require exactly one selected option")
                    if current_digest != answer.expected_frontier_digest:
                        if current.resolution == answer.resolution:
                            return DeliveryAnswerResult(
                                change_id=answer.change_id,
                                kind=answer.kind,
                                request=current,
                                frontier_digest=current_digest,
                            )
                        self._fail("answer frontier changed")
                    resolved = runtime.resolve_request(answer.request_id, answer.resolution)
                    self._publish_delivery_state(
                        answer.change_id,
                        runtime,
                        _checkpoint_operation_id("request-answer", answer.change_id, answer.request_id),
                    )
                    return DeliveryAnswerResult(
                        change_id=answer.change_id,
                        kind=answer.kind,
                        request=resolved,
                        frontier_digest=hashlib.sha256(runtime.frontier_bytes()).hexdigest(),
                    )

                if answer.kind is DeliveryAnswerKind.BLOCK:
                    binding = runtime.show_binding(answer.outcome_id)
                    block = binding.block
                    if current_digest != answer.expected_frontier_digest:
                        if (
                            block is not None
                            and block.resolved
                            and block.resolution_note == answer.operator_note
                            and block.resolution_locators == answer.locators
                        ):
                            return DeliveryAnswerResult(
                                change_id=answer.change_id,
                                kind=answer.kind,
                                binding=binding,
                                frontier_digest=current_digest,
                            )
                        self._fail("answer frontier changed")
                    cleared = runtime.unblock(
                        answer.outcome_id,
                        answer.block_id,
                        answer.operator_note,
                        answer.locators,
                    )
                    self._publish_delivery_state(
                        answer.change_id,
                        runtime,
                        _checkpoint_operation_id("block-answer", answer.change_id, answer.outcome_id, answer.block_id),
                    )
                    return DeliveryAnswerResult(
                        change_id=answer.change_id,
                        kind=answer.kind,
                        binding=cleared,
                        frontier_digest=hashlib.sha256(runtime.frontier_bytes()).hexdigest(),
                    )

                disposition = runtime.change_disposition()
                resolution = runtime.change_disposition_resolution()
                if current_digest != answer.expected_frontier_digest:
                    if resolution is not None and resolution.disposition_id == answer.expected_disposition_id:
                        return DeliveryAnswerResult(
                            change_id=answer.change_id,
                            kind=answer.kind,
                            disposition=resolution,
                            frontier_digest=current_digest,
                        )
                    self._fail("answer frontier changed")
                if disposition is None and resolution is not None:
                    if resolution.disposition_id != answer.expected_disposition_id:
                        self._fail("answer disposition is stale")
                    return DeliveryAnswerResult(
                        change_id=answer.change_id,
                        kind=answer.kind,
                        disposition=resolution,
                        frontier_digest=current_digest,
                    )
                resolved = runtime.resolve_change_disposition(
                    answer.expected_disposition_id,
                    _timestamp(self._clock()),
                )
                self._publish_delivery_state(
                    answer.change_id,
                    runtime,
                    f"attention-resolution-{resolved.resolution_id}",
                )
                return DeliveryAnswerResult(
                    change_id=answer.change_id,
                    kind=answer.kind,
                    disposition=resolved,
                    frontier_digest=hashlib.sha256(runtime.frontier_bytes()).hexdigest(),
                )

    def recover_claim(
        self,
        change_id: str,
        outcome_id: str,
        attempt_id: str,
        claim_id: str,
        *,
        confirmed_lost: bool = False,  # noqa: ARG002 - retained request shape is not evidence.
    ) -> DeliveryClaimRecoveryResult:
        """Reject assertion-only recovery without releasing an exact active claim."""
        replay = self._completed_claim_recovery(change_id, identity=(outcome_id, attempt_id, claim_id))
        if replay is not None:
            return replay
        with self._coordinator.acquisition_lock():
            return self._recover_claim(change_id, outcome_id, attempt_id, claim_id)

    def recover_integration_repair_claim(
        self,
        change_id: str,
        attempt_id: str,
        claim_id: str,
    ) -> DeliveryIntegrationRepairRecoveryResult:
        """Reject legacy Integration recovery without verified worker exclusion."""
        with self._coordinator.acquisition_lock():
            return self._recover_integration_repair_claim(change_id, attempt_id, claim_id)

    def _recover_integration_repair_claim(
        self,
        change_id: str,
        attempt_id: str,
        claim_id: str,
    ) -> DeliveryIntegrationRepairRecoveryResult:
        runtime = self._runtime(change_id, for_mutation=True)
        runtime.require_integration_repair_claim(attempt_id, claim_id)
        raise DeliveryWorkerExclusionRequiredError

    def _recover_claim(
        self,
        change_id: str,
        outcome_id: str,
        attempt_id: str,
        claim_id: str,
    ) -> DeliveryClaimRecoveryResult:
        runtime = self._runtime(change_id, for_mutation=True)
        runtime.require_active_claim(outcome_id, attempt_id, claim_id)
        raise DeliveryWorkerExclusionRequiredError

    def _register_recovery_invocation(  # noqa: PLR0913, PLR0917 - exact engine-issued custody and resource binding.
        self,
        runtime: DeliveryRuntime,
        owner_id: str,
        attempt_id: str,
        kind: str,
        exact_head: str,
        outcome_id: str | None = None,
    ) -> None:
        """Capture host provenance at issuance, before a claim can be dispatched."""
        if isinstance(self._recovery_evidence_provider, UnavailableRecoveryEvidenceProvider):
            return
        coordination = self._coordinator.show(runtime.contract.change_id)
        request = RecoveryInvocationRequest(
            change_id=runtime.contract.change_id,
            owner_id=owner_id,
            attempt_id=attempt_id,
            outcome_id=outcome_id,
            kind=kind,
            contract_digest=contract_fingerprint(runtime.contract),
            exact_head=exact_head,
            target_head=self._workspace_manager.observed_target_head(),
            branch=coordination.branch,
            worktree=str(coordination.worktree_path),
            repository=str(self._workspace_manager.repository),
            runtime_root=str(self._target_root),
            integration_target=coordination.integration_target,
            publication_repository=(
                self._draft_pull_request_publisher.repository
                if self._draft_pull_request_publisher is not None
                else None
            ),
        )
        invocation = self._recovery_evidence_provider.register(request)
        if invocation is None:
            return
        if not isinstance(invocation, RecoveryInvocation) or invocation.request != request:
            raise DeliveryWorkerExclusionRequiredError
        publish_record(self._target_root, invocation_path(request), invocation)

    def _propose_recovery(self, change_id: str) -> RecoveryIntent:
        """Internal owner path: capture exact custody, without waiting for host closure."""
        with (
            self._coordinator.acquisition_lock(),
            self._selected_action_checkpoint_lock(change_id),
            self._coordinator.recovery_lock(change_id),
        ):
            intent = self._capture_recovery_intent(change_id)
            path = journal_path(change_id, intent.recovery_id, "intent")
            directory = self._target_root / path.parent.parent
            if (
                directory.exists()
                and len(tuple(directory.iterdir())) >= MAX_RECOVERY_INTENTS
                and not (self._target_root / path).exists()
            ):
                raise DeliveryWorkerExclusionRequiredError
            self._coordinator.record_recovery_intent(intent)
            return intent

    @staticmethod
    def _recovery_admitted_task(
        runtime: DeliveryRuntime,
        owner: ChangeContinuationAction | ChangeFinalizationAttempt | DeliveryActiveClaim,
        kind: str,
    ) -> DeliveryTaskDefinition | None:
        if kind != "clean-claim" or not isinstance(owner, DeliveryActiveClaim) or owner.task_id is None:
            return None
        binding = next((candidate for candidate in runtime.bindings() if candidate.active_claim == owner), None)
        if binding is None:
            raise DeliveryWorkerExclusionRequiredError
        task = next((candidate for candidate in binding.tasks if candidate.task_id == owner.task_id), None)
        if task is None:
            raise DeliveryWorkerExclusionRequiredError
        return task

    @staticmethod
    def _exact_task_scope(task: DeliveryTaskDefinition, worktree: Path) -> tuple[str, ...]:
        scope, _kinds = PortfolioApplication._exact_task_scope_details(task, worktree)
        return scope

    @staticmethod
    def _exact_task_scope_details(
        task: DeliveryTaskDefinition,
        worktree: Path,
        baseline_kinds: dict[str, str] | None = None,
    ) -> tuple[tuple[str, ...], dict[str, Literal["directory", "file", "missing"]]]:
        surfaces = tuple(task.maintained_surfaces)
        if len(surfaces) != len(set(surfaces)):
            raise DeliveryWorkerExclusionRequiredError
        if baseline_kinds is not None and (
            set(baseline_kinds) != set(surfaces)
            or any(kind not in {"directory", "file", "missing"} for kind in baseline_kinds.values())
        ):
            raise DeliveryWorkerExclusionRequiredError
        kinds: dict[str, Literal["directory", "file", "missing"]] = {}
        for surface in surfaces:
            path = PurePosixPath(surface)
            if not is_canonical_admitted_path(surface):
                raise DeliveryWorkerExclusionRequiredError
            candidate = worktree
            try:
                for part in path.parts:
                    candidate /= part
                    metadata = candidate.lstat()
                    if stat.S_ISLNK(metadata.st_mode):
                        raise DeliveryWorkerExclusionRequiredError
            except FileNotFoundError:
                baseline_kind = (baseline_kinds or {}).get(surface, "missing")
                if baseline_kind not in {"directory", "file", "missing"}:
                    raise DeliveryWorkerExclusionRequiredError
                kinds[surface] = baseline_kind
                continue
            except OSError as exc:
                raise DeliveryWorkerExclusionRequiredError from exc
            observed_kind = "directory" if stat.S_ISDIR(metadata.st_mode) else "file"
            baseline_kind = (baseline_kinds or {}).get(surface)
            if baseline_kind in {"directory", "file"} and observed_kind != baseline_kind:
                raise DeliveryWorkerExclusionRequiredError
            kinds[surface] = observed_kind
        return tuple(sorted(surfaces)), kinds

    @staticmethod
    def _scope_admits_path(
        worktree: Path,
        scope: str,
        path: str,
        *,
        scope_kind: Literal["directory", "file", "missing"] | None = None,
    ) -> bool:
        scope_parts = PurePosixPath(scope).parts
        path_parts = PurePosixPath(path).parts
        if path_parts == scope_parts:
            return True
        if len(path_parts) <= len(scope_parts) or path_parts[: len(scope_parts)] != scope_parts:
            return False
        if scope_kind is not None:
            return scope_kind == "directory"
        try:
            metadata = (worktree / PurePosixPath(scope)).lstat()
        except FileNotFoundError:
            return False
        except OSError as exc:
            raise DeliveryWorkerExclusionRequiredError from exc
        if stat.S_ISLNK(metadata.st_mode):
            return False
        return stat.S_ISDIR(metadata.st_mode)

    @staticmethod
    def _recovery_admission_fields(
        task: DeliveryTaskDefinition | None,
        paths: tuple[str, ...],
        worktree: Path,
        *,
        scope_details: tuple[tuple[str, ...], dict[str, Literal["directory", "file", "missing"]]] | None = None,
    ) -> tuple[str | None, str | None, tuple[str, ...], tuple[str, ...]]:
        if task is None:
            if paths:
                raise DeliveryWorkerExclusionRequiredError
            return None, None, (), ()
        if any(not is_canonical_admitted_path(path) for path in paths):
            raise DeliveryWorkerExclusionRequiredError
        if not paths:
            # Clean Recovery-A carries no path authority; unsupported task-scope
            # descriptors remain a dirty-admission concern only.
            return None, None, (), ()
        scope, scope_kinds = scope_details or PortfolioApplication._exact_task_scope_details(task, worktree)
        admitted_paths = tuple(sorted(paths))
        if any(
            not any(
                PortfolioApplication._scope_admits_path(
                    worktree,
                    candidate,
                    path,
                    scope_kind=scope_kinds[candidate],
                )
                for candidate in scope
            )
            for path in admitted_paths
        ):
            raise DeliveryWorkerExclusionRequiredError
        return task.task_id, task.digest, scope, admitted_paths

    def _capture_recovery_intent(self, change_id: str) -> RecoveryIntent:
        runtime = self._runtime(change_id)
        frontier = parse_delivery_frontier(runtime.frontier_bytes())[0]
        coordination = self._coordinator.show(change_id)
        owner, owner_id, kind, failure_id, effect_id = self._recovery_owner(runtime, coordination)
        admitted_task = self._recovery_admitted_task(runtime, owner, kind)
        coordination, head, _status, paths, reason = self._workspace_manager.capture_recovery_workspace_metadata(
            change_id, tuple(result.completed_commit for binding in frontier.bindings for result in binding.results)
        )
        # Recovery A never rewrites files, moves heads, repairs corruption, or interprets
        # unpromoted output as proof of a completed effect.
        if (
            reason not in {None, "workspace-dirty"}
            or coordination.publication_lease is not None
        ):
            raise DeliveryWorkerExclusionRequiredError
        baseline_kinds = (
            self._workspace_manager.baseline_scope_kinds(
                coordination.worktree_path,
                head,
                tuple(admitted_task.maintained_surfaces),
            )
            if admitted_task is not None and paths
            else None
        )
        scope_details = (
            self._exact_task_scope_details(admitted_task, coordination.worktree_path, baseline_kinds)
            if admitted_task is not None and paths
            else None
        )
        (
            admitted_task_id,
            admitted_task_digest,
            admitted_task_scope,
            admitted_paths,
        ) = self._recovery_admission_fields(
            admitted_task,
            paths,
            coordination.worktree_path,
            scope_details=scope_details,
        )
        if (
            scope_details is not None
            and self._exact_task_scope_details(admitted_task, coordination.worktree_path, baseline_kinds)
            != scope_details
        ):
            raise DeliveryWorkerExclusionRequiredError
        coordination, head, fingerprint, captured_paths, reason = self._workspace_manager.capture_recovery_workspace(
            change_id,
            tuple(result.completed_commit for binding in frontier.bindings for result in binding.results),
            expected_paths=paths,
            expected_scope_details=scope_details,
        )
        if captured_paths != paths or reason not in {None, "workspace-dirty"}:
            raise DeliveryWorkerExclusionRequiredError
        relative = Path("changes") / change_id / "invocations" / f"{digest(owner_id.encode())}.json"
        try:
            invocation = RecoveryInvocation.model_validate_json(read_record(self._target_root, relative))
        except (OSError, ValueError) as exc:
            raise DeliveryWorkerExclusionRequiredError from exc
        request = invocation.request
        if (
            request.change_id != change_id
            or request.owner_id != owner_id
            or request.contract_digest != contract_fingerprint(runtime.contract)
            or request.exact_head != head
            or request.target_head != self._workspace_manager.observed_target_head()
            or request.worktree != str(coordination.worktree_path)
            or request.branch != coordination.branch
            or request.repository != str(self._workspace_manager.repository)
            or request.runtime_root != str(self._target_root)
            or request.integration_target != coordination.integration_target
            or request.publication_repository
            != (
                self._draft_pull_request_publisher.repository
                if self._draft_pull_request_publisher is not None
                else None
            )
        ):
            raise DeliveryWorkerExclusionRequiredError
        expected_kind = {"clean-claim": "claim", "clean-finalizer": "finalizer", "ready-readback": "mark-ready"}[kind]
        expected_attempt = (
            owner.operation_id
            if kind == "ready-readback"
            else (owner.writer.attempt_id if kind == "clean-finalizer" else owner.attempt_id)
        )
        if request.kind != expected_kind or request.attempt_id != expected_attempt:
            raise DeliveryWorkerExclusionRequiredError
        if kind == "clean-claim":
            binding = runtime.require_active_claim(request.outcome_id, request.attempt_id, request.owner_id)
            if binding.active_claim != owner:
                raise DeliveryWorkerExclusionRequiredError
        proposal = self._repair_proposal(DeliveryPortfolioSnapshot.capture(runtime.contract, runtime.frontier_bytes()))
        result_digest = None
        if kind == "ready-readback":
            result = self._read_engine_result(
                ExecuteDeliveryChangeAction(change_id=change_id, operation_id=request.owner_id)
            )
            if result is not None and result.kind != "blocked":
                raise DeliveryWorkerExclusionRequiredError
            path = self._coordinator.continuation_record_path(change_id, request.owner_id, result=True)
            result_digest = digest(path.read_bytes() if result is not None else b"")
        maintained_surfaces = tuple(
            sorted(
                {
                    surface
                    for binding in runtime.bindings()
                    for task in binding.tasks
                    for surface in task.maintained_surfaces
                }
            )
        )
        last_write_provenance = tuple(
            sorted(
                {
                    f"change-head:{head}",
                    f"frontier:{digest(runtime.frontier_bytes())}",
                    f"owner:{owner_id}",
                    f"attempt:{request.attempt_id}",
                    *(
                        f"result:{result.result_id}:{result.completed_commit}"
                        for binding in runtime.bindings()
                        for result in binding.results
                    ),
                }
            )
        )
        return RecoveryIntent(
            invocation=invocation,
            frontier_digest=digest(runtime.frontier_bytes()),
            coordination_digest=digest(self._coordinator.recovery_coordination_bytes(change_id, owner_id)),
            exact_head=head,
            target_head=request.target_head,
            workspace_fingerprint=fingerprint,
            owner_record=owner.model_dump_json(),
            failure_id=failure_id,
            effect_receipt_id=effect_id,
            kind=kind,
            proposal_id=proposal.proposal_id if proposal is not None else None,
            engine_result_digest=result_digest,
            maintained_surfaces=maintained_surfaces,
            last_write_provenance=last_write_provenance,
            admitted_task_id=admitted_task_id,
            admitted_task_digest=admitted_task_digest,
            admitted_task_scope=admitted_task_scope,
            admitted_paths=admitted_paths,
        )

    def _recovery_owner(
        self, runtime: DeliveryRuntime, coordination: ChangeCoordination
    ) -> tuple[
        ChangeContinuationAction | ChangeFinalizationAttempt | DeliveryActiveClaim, str, str, str | None, str | None
    ]:
        claims = runtime.active_claims()
        action = coordination.continuation_action
        if runtime.integration_repair_claim() is not None:
            raise DeliveryWorkerExclusionRequiredError
        if action is not None and action.finished_at is None:
            ready = runtime.ready_receipt()
            if (
                claims
                or coordination.writer is not None
                or action.kind != "mark-ready"
                or ready is None
                or ready.operation_id != action.operation_id
                or ready.finalization_id != action.finalization_id
                or ready.head_sha != action.exact_head
                or runtime.pending_state_publication() is not None
                or runtime.checkpoint_publication_state().pending_checkpoint is not None
            ):
                raise DeliveryWorkerExclusionRequiredError
            path = self._coordinator.continuation_record_path(action.change_id, action.operation_id)
            original = path.read_bytes()
            if (
                ChangeContinuationAction.model_validate_json(original) != action
                or path.with_name("started.json").read_bytes() != original
            ):
                raise DeliveryWorkerExclusionRequiredError
            return action, action.operation_id, "ready-readback", action.operation_id, ready.receipt_id
        attempt = coordination.finalization_attempt
        if coordination.writer is not None and coordination.writer.kind == "finalize":
            if claims or attempt is None or attempt.writer != coordination.writer or attempt.finished_at is not None:
                raise DeliveryWorkerExclusionRequiredError
            reports = FinalizationReportStore(self._target_root, runtime.contract.change_id).read().reports
            report = next((item for item in reports if item.request.attempt_key == attempt.writer.attempt_id), None)
            if report is None:
                raise DeliveryWorkerExclusionRequiredError
            return attempt, attempt.writer.claim_id, "clean-finalizer", report.report_id, None
        if len(claims) != 1:
            raise DeliveryWorkerExclusionRequiredError
        outcome_id, claim = claims[0]
        binding = runtime.show_binding(outcome_id)
        writer = coordination.writer
        if (
            binding.output is not None
            or binding.result_candidate is not None
            or binding.candidate is not None
            or (
                writer is not None
                and (
                    writer.claim_id != claim.claim_id or writer.attempt_id != claim.attempt_id or writer.kind != "build"
                )
            )
        ):
            raise DeliveryWorkerExclusionRequiredError
        return claim, claim.claim_id, "clean-claim", claim.attempt_id, None

    def _complete_recovery(
        self, change_id: str, recovery_id: str, reference: RecoveryEvidenceReference
    ) -> RecoveryReceipt:
        """Verify outside locks, then CAS receipt and release in one runtime transaction."""
        intent_path = journal_path(change_id, recovery_id, "intent")
        intent = RecoveryIntent.model_validate_json(read_record(self._target_root, intent_path))
        if intent.recovery_id != recovery_id or intent.invocation.request.change_id != change_id:
            raise DeliveryWorkerExclusionRequiredError
        evidence = verify_evidence(self._recovery_evidence_provider, reference, intent)
        receipt_path = self._target_root / journal_path(change_id, recovery_id, "receipt")
        self._coordinator.recover_pending_transactions()
        if receipt_path.exists():
            return self._verified_recovery_replay(intent, evidence, receipt_path)
        observation_id = self._readback_recovery_ready(intent) if intent.kind == "ready-readback" else None
        with (
            self._coordinator.acquisition_lock(),
            self._selected_action_checkpoint_lock(change_id),
            self._coordinator.recovery_lock(change_id),
        ):
            self._coordinator.recover_pending_transactions()
            if receipt_path.exists():
                return self._verified_recovery_replay(intent, evidence, receipt_path)
            self._coordinator.forget_verified_exclusion(recovery_id)
            if intent.admitted_task_id is None:
                self._require_legacy_recovery_clean(change_id, intent)
            current_intent = self._capture_recovery_intent(change_id)
            if intent.admitted_task_id is None and current_intent.admitted_paths:
                raise DeliveryWorkerExclusionRequiredError
            if not intent.authority_matches(current_intent):
                raise DeliveryWorkerExclusionRequiredError
            evidence_path = journal_path(change_id, recovery_id, "evidence")
            if (self._target_root / evidence_path).exists():
                recorded = RecoveryEvidence.model_validate_json(read_record(self._target_root, evidence_path))
                self._require_revalidated_evidence(recorded, evidence)
                evidence = recorded
            publish_record(self._target_root, evidence_path, evidence)
            receipt = RecoveryReceipt(
                recovery_id=recovery_id,
                evidence=evidence,
                finished_at=self._clock(),
                owner_effect="ready-receipt-readback" if intent.kind == "ready-readback" else "no-workspace-effect",
                owner_observation_id=observation_id,
            )
            self._runtime(change_id).complete_recovery(intent, receipt)
            self._record_retry_release(self._runtime(change_id), attempt_id=intent.invocation.request.attempt_id)
            self._coordinator.record_verified_exclusion(recovery_id)
            return receipt

    def _require_legacy_recovery_clean(self, change_id: str, intent: RecoveryIntent) -> None:
        """Contain old journals to clean recovery until path admission exists."""
        runtime = self._runtime(change_id)
        frontier = parse_delivery_frontier(runtime.frontier_bytes())[0]
        _coordination, _head, status, paths, reason = self._workspace_manager.capture_recovery_workspace_metadata(
            change_id,
            tuple(result.completed_commit for binding in frontier.bindings for result in binding.results),
        )
        # A legacy journal has no persisted path authority.  The metadata
        # capture deliberately does not expose ignored paths, so retain the
        # stronger guard reason as well as the ordinary dirty inventory.
        if status or paths or reason is not None:
            raise DeliveryWorkerExclusionRequiredError

    def _verified_recovery_replay(
        self, intent: RecoveryIntent, evidence: RecoveryEvidence, path: Path
    ) -> RecoveryReceipt:
        receipt = RecoveryReceipt.model_validate_json(
            read_record(self._target_root, path.relative_to(self._target_root))
        )
        request = intent.invocation.request
        self._require_revalidated_evidence(receipt.evidence, evidence)
        runtime = self._runtime(request.change_id)
        coordination = self._coordinator.show(request.change_id)
        action = coordination.continuation_action
        writer = coordination.writer
        if (
            receipt.recovery_id != intent.recovery_id
            or receipt.owner_effect
            != ("ready-receipt-readback" if intent.kind == "ready-readback" else "no-workspace-effect")
            or any(claim.claim_id == request.owner_id for _, claim in runtime.active_claims())
            or coordination.recovery_owner_id == request.owner_id
            or (writer is not None and writer.claim_id == request.owner_id)
            or (action is not None and action.operation_id == request.owner_id and action.finished_at is None)
        ):
            raise DeliveryWorkerExclusionRequiredError
        self._coordinator.record_verified_exclusion(intent.recovery_id)
        self._record_retry_release(runtime, attempt_id=request.attempt_id)
        return receipt

    @staticmethod
    def _require_revalidated_evidence(recorded: RecoveryEvidence, current: RecoveryEvidence) -> None:
        if (
            recorded.model_copy(update={"status": current.status}) != current
            or recorded.status not in {"closed", "excluded"}
            or (recorded.status == "closed" and current.status != "closed")
        ):
            raise DeliveryWorkerExclusionRequiredError

    def _completed_claim_recovery(
        self, change_id: str, *, identity: tuple[str, str, str] | None = None, proposal_id: str | None = None
    ) -> DeliveryClaimRecoveryResult | None:
        """Public forms may only replay an independently verified completed exact receipt."""
        root = self._target_root / journal_path(change_id, "0" * 64, "intent").parent.parent
        self._coordinator.recover_pending_transactions()
        if not root.exists():
            return None
        paths = tuple(root.iterdir())
        if len(paths) > MAX_RECOVERY_INTENTS:
            raise DeliveryWorkerExclusionRequiredError
        for path in paths:
            receipt_path = self._target_root / journal_path(change_id, path.name, "receipt")
            if not receipt_path.exists():
                continue
            intent = RecoveryIntent.model_validate_json(
                read_record(self._target_root, journal_path(change_id, path.name, "intent"))
            )
            request = intent.invocation.request
            if (
                intent.kind != "clean-claim"
                or intent.recovery_id != path.name
                or request.change_id != change_id
                or (identity is not None and identity != (request.outcome_id, request.attempt_id, request.owner_id))
                or (proposal_id is not None and intent.proposal_id != proposal_id)
            ):
                continue
            receipt = RecoveryReceipt.model_validate_json(
                read_record(self._target_root, journal_path(change_id, path.name, "receipt"))
            )
            self._coordinator.forget_verified_exclusion(intent.recovery_id)
            evidence = verify_evidence(self._recovery_evidence_provider, receipt.evidence.reference, intent)
            self._verified_recovery_replay(intent, evidence, receipt_path)
            return self._recovered(change_id, request.outcome_id, request.attempt_id, request.owner_id)
        return None

    def _readback_recovery_ready(self, intent: RecoveryIntent) -> str:
        """Reconcile only a fully recorded ready effect; never invoke the mutation again."""
        change_id = intent.invocation.request.change_id
        publisher = self._draft_pull_request_publisher
        ready = self._runtime(change_id).ready_receipt()
        if publisher is None or ready is None or ready.receipt_id != intent.effect_receipt_id:
            raise DeliveryWorkerExclusionRequiredError
        observation = publisher.observe_pull_request(ObserveChangePublicationPullRequest(change_id=change_id))
        if observation is None:
            raise DeliveryWorkerExclusionRequiredError
        snapshot = observation.snapshot
        if (
            snapshot.repository != ready.repository
            or snapshot.number != ready.number
            or snapshot.node_id != ready.node_id
            or snapshot.head_sha != intent.exact_head
            or snapshot.base_branch != publisher.target_branch
            or snapshot.draft
            or snapshot.state != "open"
            or snapshot.merged
        ):
            raise DeliveryWorkerExclusionRequiredError
        return observation.observation_id

    def _candidates(self, selected_change_id: str | None = None) -> tuple[_Candidate, ...]:  # noqa: C901
        candidates = []
        for change_id, runtime in self._runtimes.items():
            if selected_change_id is not None and change_id != selected_change_id:
                continue
            if change_id in self._runtime_reconciliation_errors:
                continue
            try:
                pending_publication = runtime.pending_state_publication()
                occupied = (
                    runtime.active_claims()
                    or runtime.change_stage() != DeliveryChangeStage.BUILDING
                    or self._workspace_manager.show(change_id).writer is not None
                )
            except (OSError, RuntimeError, ValueError):
                continue
            if pending_publication is not None or occupied:
                continue
            pending = runtime.checkpoint_publication_state().pending_checkpoint
            if pending is not None and any(
                trigger.kind == DeliveryCheckpointTriggerKind.ADMITTED_DESIGN for trigger in pending.triggers
            ):
                continue
            claimable = set(runtime.claimable_outcome_ids())
            ranked = []
            for outcome_index, outcome in enumerate(runtime.contract.outcomes):
                if outcome.outcome_id not in claimable:
                    continue
                binding = runtime.show_binding(outcome.outcome_id)
                task_id = None
                task_index = 0
                if binding.stage == DeliveryStage.IMPLEMENTATION:
                    task_ids = runtime.claimable_task_ids(outcome.outcome_id)
                    if not task_ids:
                        continue
                    task_id = task_ids[0]
                    task_index = binding.task_ids.index(task_id)
                role = {
                    DeliveryStage.PLANNING: DeliveryWorkerRole.PLANNER,
                    DeliveryStage.IMPLEMENTATION: DeliveryWorkerRole.BUILDER,
                }[binding.stage]
                ranked.append(
                    _Candidate(
                        sort_key=(
                            self._dependency_depth(runtime, outcome.outcome_id),
                            outcome_index,
                            task_index,
                            change_id,
                        ),
                        change_id=change_id,
                        runtime=runtime,
                        binding=binding,
                        task_id=task_id,
                        role=role,
                    )
                )
            if ranked:
                candidates.append(min(ranked, key=lambda item: item.sort_key))
        return tuple(sorted(candidates, key=lambda item: item.sort_key))

    def _prepare_source(
        self,
        change_id: str,
        runtime: DeliveryRuntime,
        outcome_id: str,
        worker_role: DeliveryWorkerRole,
        *,
        allow_dirty: bool = False,
    ) -> _PreparedSource | DeliveryAcquisitionFailure:
        try:
            package = self._package_store.read_verified(change_id)
            self._validate_package_authority(runtime, package)
            coordination = self._workspace_manager.show(change_id)
            source_head = self._workspace_manager.source_head(change_id, require_clean=not allow_dirty)
            adoption = coordination.external_head_adoption_receipt
            promotion = coordination.external_head_promotion_receipt
            if promotion != runtime.external_head_promotion_receipt():
                return DeliveryAcquisitionFailure(
                    change_id=change_id,
                    outcome_id=outcome_id,
                    code=PortfolioApplicationError.code,
                    detail="external Change head promotion is not reconciled to Delivery authority",
                    retry_condition="Replay the exact external Change head promotion operation.",
                )
            if source_head != coordination.last_reviewed_commit and (
                adoption is None or runtime.external_head_adoption_receipt() != adoption
            ):
                return DeliveryAcquisitionFailure(
                    change_id=change_id,
                    outcome_id=outcome_id,
                    code=PortfolioApplicationError.code,
                    detail="external Change head adoption is not reconciled to Delivery authority",
                    retry_condition="Replay the exact external Change head adoption operation.",
                )
            if worker_role == DeliveryWorkerRole.BUILDER and source_head != coordination.last_reviewed_commit:
                return DeliveryAcquisitionFailure(
                    change_id=change_id,
                    outcome_id=outcome_id,
                    code=PortfolioApplicationError.code,
                    detail="Builder authority requires explicit promotion of the adopted Change head",
                    retry_condition="Promote the exact adopted Change head before acquiring Build work.",
                )
        except (OSError, RuntimeError, ValueError) as exc:
            return DeliveryAcquisitionFailure(
                change_id=change_id,
                outcome_id=outcome_id,
                code=getattr(exc, "code", PortfolioApplicationError.code),
                detail=str(exc),
                retry_condition="Restore the admitted package and clean reviewed source boundary.",
            )
        return _PreparedSource(package, coordination, source_head)

    def _promote_finalized_external_head(self, change_id: str, exact_head: str) -> None:
        try:
            runtime = self._runtime(change_id, for_mutation=True)
            coordination = self._workspace_manager.show(change_id)
            if (
                coordination.last_reviewed_commit == exact_head
                and coordination.external_head_promotion_receipt == runtime.external_head_promotion_receipt()
            ):
                return
            operation_id = f"finalization-{exact_head}"
            promotion = self._workspace_manager.promote_external_head(
                PromoteExternalHead(
                    change_id=change_id,
                    expected_head=exact_head,
                    operation_id=operation_id,
                ),
                provenance="finalization",
            )
            if promotion is not None:
                runtime.record_external_head_promotion(promotion, _timestamp(self._clock()))
        except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as exc:
            self._fail("finalization could not promote the reviewed adopted Change head", exc)

    def _return_publication_to_draft_before_head_change(
        self,
        change_id: str,
        runtime: DeliveryRuntime,
        operation_id: str,
        *,
        finalization_id: str | None = None,
    ) -> None:
        """Demote the bound provider pull request before its Change head moves."""
        finalization = runtime.finalization()
        ready = runtime.ready_receipt()
        if finalization is None or ready is None:
            if finalization_id is None:
                return
            publication = runtime.change_disposition_publication()
            if publication is None:
                self._fail("Change head movement requires a bound publication identity")
            expected_finalization_id = finalization_id
            expected_repository = publication.repository
            expected_number = publication.number
            expected_node_id = publication.node_id
        else:
            expected_finalization_id = finalization.finalization_id
            expected_repository = ready.repository
            expected_number = ready.number
            expected_node_id = ready.node_id
        publisher = self._draft_pull_request_publisher
        if publisher is None:
            self._fail("Change head movement requires a configured publication provider")
        observation = publisher.observe_pull_request(ObserveChangePublicationPullRequest(change_id=change_id))
        if observation is None:
            self._fail("Change head movement requires a bound pull request")
        snapshot = observation.snapshot
        if (
            snapshot.repository != expected_repository
            or snapshot.number != expected_number
            or snapshot.node_id != expected_node_id
            or snapshot.base_branch != publisher.target_branch
            or snapshot.state != "open"
            or snapshot.merged
        ):
            self._fail("Change head movement requires an open bound pull request")
        if snapshot.draft:
            if finalization is not None and ready is not None:
                runtime.clear_ready_for_head_change(
                    finalization.finalization_id,
                    finalization.exact_head,
                )
            return
        publisher.return_to_draft(
            ReturnChangePullRequestToDraft(
                change_id=change_id,
                operation_id=f"return-draft-{operation_id}",
                finalization_id=expected_finalization_id,
                exact_head=snapshot.head_sha,
            )
        )
        if finalization is not None and ready is not None:
            runtime.clear_ready_for_head_change(
                finalization.finalization_id,
                finalization.exact_head,
            )

    @staticmethod
    def _require_fresh_target_sync_review(runtime: DeliveryRuntime) -> None:
        """Reject publication paths that still contain an unreviewed resolved target merge."""
        target_sync = runtime.target_sync_receipt()
        if target_sync is not None and target_sync.review_required and runtime.finalization() is None:
            message = "target synchronization resolution requires fresh finalization review"
            raise PortfolioApplicationError(message)

    def _activate_candidate(
        self,
        candidate: _Candidate,
        source: _PreparedSource,
        *,
        expected_frontier_digest: str | None = None,
        host_identity: tuple[str, str] | None = None,
    ) -> DeliveryLaunchPackage | DeliveryAcquisitionFailure:
        claim = self._new_claim(candidate.role, candidate.task_id)
        if host_identity is not None:
            claim = claim.model_copy(
                update={"owner_id": host_identity[0], "process_id": host_identity[1], "continuation": True}
            )
        reservation = self._reserve_worker_attempt(candidate, source, claim.attempt_id, claim.claim_id)
        if reservation is not None and not reservation.allowed:
            return DeliveryAcquisitionFailure(
                change_id=candidate.change_id,
                outcome_id=candidate.binding.outcome_id,
                attempt_id=claim.attempt_id,
                claim_id=claim.claim_id,
                code="ERR_DELIVERY_RETRY_EXHAUSTED",
                detail="Automatic worker repair is not eligible for this semantic failure episode.",
                retry_condition=(
                    "Wait for the durable retry eligibility time or record accepted progress for this exact episode; "
                    "do not create a new allowance by renaming the task or operation."
                ),
            )
        self._register_recovery_invocation(
            candidate.runtime,
            claim.claim_id,
            claim.attempt_id,
            "claim",
            source.source_head,
            candidate.binding.outcome_id,
        )
        candidate.runtime.activate_claim(
            ActivateDeliveryClaim(
                outcome_id=candidate.binding.outcome_id,
                claim=claim,
                expected_frontier_digest=expected_frontier_digest,
            )
        )
        try:
            writer = None
            if candidate.role == DeliveryWorkerRole.BUILDER:
                coordination = self._coordinator.acquire(
                    candidate.change_id,
                    ChangeWriter(
                        attempt_id=claim.attempt_id,
                        claim_id=claim.claim_id,
                        actor_id=claim.owner_id,
                        process_id=claim.process_id,
                        claimed_at=claim.started_at,
                        job_id=1,
                        kind="build",
                    ),
                )
                writer = coordination.writer
            return self._launch_package(candidate, claim, source, writer)
        except (OSError, RuntimeError, ValueError) as exc:
            if reservation is not None and reservation.attempt_id is not None:
                with suppress(OSError, RuntimeError, ValueError):
                    candidate.runtime.retry_ledger(clock=self._clock).record_failure(
                        reservation,
                        failure_code=getattr(exc, "code", PortfolioApplicationError.code),
                        failure_detail=str(exc),
                        now=self._clock(),
                    )
            return DeliveryAcquisitionFailure(
                change_id=candidate.change_id,
                outcome_id=candidate.binding.outcome_id,
                attempt_id=claim.attempt_id,
                claim_id=claim.claim_id,
                code=getattr(exc, "code", PortfolioApplicationError.code),
                detail=str(exc) or "worker launch preparation failed after claim activation",
                retry_condition=(
                    "Retain the exact claim and any writer custody. D03 closed-worker recovery is required; "
                    "do not redispatch, infer termination, or use confirmed_lost recovery."
                    if claim.continuation
                    else "Recover the exact failed claim after reconciling writer custody."
                ),
            )

    def _reserve_worker_attempt(
        self,
        candidate: _Candidate,
        source: _PreparedSource,
        attempt_id: str,
        claim_id: str,
    ) -> RetryReservation | None:
        """Reserve worker/check repair before publishing a claim or writer."""
        key = self._worker_retry_key(candidate, source.source_head)
        ledger = candidate.runtime.retry_ledger(clock=self._clock)
        ledger.import_legacy_failures(key, candidate.binding.retry_count, now=self._clock())
        return ledger.reserve(
            key,
            failure_class=RetryFailureClass.MECHANICAL,
            now=self._clock(),
            attempt_id=attempt_id,
            automatic=True,
            operation_alias=claim_id,
        )

    @staticmethod
    def _worker_retry_key(candidate: _Candidate, source_head: str) -> RetryEpisodeKey:
        original_candidate = (
            candidate.binding.candidate.digest
            if candidate.binding.candidate is not None
            else candidate.binding.result_candidate.digest
            if candidate.binding.result_candidate is not None
            else candidate.binding.outcome_id
        )
        return RetryEpisodeKey.worker(
            candidate.change_id,
            f"{candidate.role.value}-claim",
            source_head,
            contract_digest=contract_fingerprint(candidate.runtime.contract),
            outcome_id=candidate.binding.outcome_id,
            task_lineage=candidate.task_id or candidate.binding.outcome_id,
            procedure_class=candidate.role.value,
            original_candidate=original_candidate,
        )

    def _current_launch(
        self,
        change_id: str,
        runtime: DeliveryRuntime,
        binding: OutcomeAuthorityBinding,
    ) -> DeliveryLaunchPackage:
        source = self._prepare_source(
            change_id,
            runtime,
            binding.outcome_id,
            binding.active_claim.worker_role,
            allow_dirty=binding.active_claim.worker_role is DeliveryWorkerRole.BUILDER,
        )
        if isinstance(source, DeliveryAcquisitionFailure):
            self._fail(source.detail)
        claim = binding.active_claim
        if claim is None:
            self._fail("outcome has no active claim")
        writer = source.coordination.writer if claim.worker_role == DeliveryWorkerRole.BUILDER else None
        candidate = _Candidate((0, 0, 0, change_id), change_id, runtime, binding, claim.task_id, claim.worker_role)
        return self._launch_package(candidate, claim, source, writer)

    def _launch_package(
        self,
        candidate: _Candidate,
        claim: DeliveryActiveClaim,
        source: _PreparedSource,
        writer: ChangeWriter | None,
    ) -> DeliveryLaunchPackage:
        return DeliveryLaunchPackage(
            change_id=candidate.change_id,
            authority_digest=candidate.runtime.authority_digest,
            outcome_id=candidate.binding.outcome_id,
            plan_scope_id=candidate.binding.plan_scope_id,
            task_id=candidate.task_id,
            claim=claim,
            policy=self._policies[candidate.role],
            package_id=source.package.package_id,
            package_root=self._package_root / candidate.change_id,
            worktree_path=source.coordination.worktree_path,
            branch=source.coordination.branch,
            source_head=source.source_head,
            integration_target=source.coordination.integration_target,
            last_reviewed_commit=source.coordination.last_reviewed_commit,
            writer=writer,
        )

    def _new_claim(self, role: DeliveryWorkerRole, task_id: str | None) -> DeliveryActiveClaim:
        return DeliveryActiveClaim(
            attempt_id=self._identity_factory(),
            claim_id=self._identity_factory(),
            owner_id=self._identity_factory(),
            process_id=self._identity_factory(),
            started_at=self._clock(),
            worker_role=role,
            task_id=task_id,
        )

    @staticmethod
    def _released_recovery_matches(snapshot: WorkspaceRecoverySnapshot) -> bool:
        return (
            snapshot.clean
            and snapshot.branch_head == snapshot.last_reviewed_commit
            and snapshot.worktree_head == snapshot.last_reviewed_commit
            and snapshot.worktree_branch == snapshot.branch
        )

    @staticmethod
    def _active_recovery_matches(
        snapshot: WorkspaceRecoverySnapshot,
        attempt_id: str,
        claim_id: str,
    ) -> bool:
        writer = snapshot.writer
        if (
            writer is None
            or writer.attempt_id != attempt_id
            or writer.claim_id != claim_id
            or not snapshot.reviewed_ancestor
            or not snapshot.preserved_reviewed_ancestor
        ):
            return False
        rejected_head = snapshot.preserved_commit or snapshot.branch_head
        if snapshot.branch_head not in {rejected_head, snapshot.last_reviewed_commit}:
            return False
        if snapshot.worktree_head is None:
            return snapshot.preserved_commit is not None and snapshot.worktree_branch is None
        return snapshot.worktree_head == snapshot.branch_head and snapshot.worktree_branch == snapshot.branch

    def _retain_recovery_attention(  # noqa: PLR0913 - recovery attention binds exact claim and workspace evidence.
        self,
        runtime: DeliveryRuntime,
        outcome_id: str,
        claim: DeliveryActiveClaim,
        snapshot: WorkspaceRecoverySnapshot,
        *,
        reason: str | None = None,
        retry_condition: str = "Restore a clean recorded worktree and reconcile exact writer custody.",
    ) -> DeliveryClaimRecoveryResult:
        attention = DeliveryRecoveryAttention(
            attempt_id=claim.attempt_id,
            claim_id=claim.claim_id,
            reason=reason or self._recovery_reason(snapshot, claim),
            worktree_path=str(snapshot.worktree_path),
            branch_head=snapshot.branch_head,
            worktree_head=snapshot.worktree_head,
            last_reviewed_commit=snapshot.last_reviewed_commit,
            writer_claim_id=snapshot.writer.claim_id if snapshot.writer is not None else None,
            custody_retained=snapshot.writer is not None,
            retry_condition=retry_condition,
        )
        runtime.publish_recovery_attention(outcome_id, attention)
        return DeliveryClaimRecoveryResult(
            status=DeliveryClaimRecoveryStatus.ATTENTION,
            change_id=runtime.contract.change_id,
            outcome_id=outcome_id,
            attempt_id=claim.attempt_id,
            claim_id=claim.claim_id,
            attention=attention,
        )

    @staticmethod
    def _recovery_reason(snapshot: WorkspaceRecoverySnapshot, claim: DeliveryActiveClaim) -> str:
        writer = snapshot.writer
        if writer is None:
            return "Build source is outside the reviewed boundary without writer custody."
        if writer.attempt_id != claim.attempt_id or writer.claim_id != claim.claim_id:
            return "Build claim does not match recorded writer custody."
        if not snapshot.clean:
            return "Build worktree contains uncommitted changes."
        if snapshot.worktree_branch != snapshot.branch or snapshot.worktree_head != snapshot.branch_head:
            return "Build worktree does not match its recorded branch head."
        if not snapshot.reviewed_ancestor:
            return "Build branch does not descend from its reviewed boundary."
        return "Build attempt history ref conflicts with the current branch head."

    @staticmethod
    def _recovered(  # noqa: PLR0913 - recovery result binds exact claim and preservation evidence.
        change_id: str,
        outcome_id: str,
        attempt_id: str,
        claim_id: str,
        preserved_commit: str | None = None,
        *,
        quarantine_commit: str | None = None,
        quarantine_ref: str | None = None,
    ) -> DeliveryClaimRecoveryResult:
        return DeliveryClaimRecoveryResult(
            status=DeliveryClaimRecoveryStatus.RECOVERED,
            change_id=change_id,
            outcome_id=outcome_id,
            attempt_id=attempt_id,
            claim_id=claim_id,
            preserved_commit=preserved_commit,
            preserved_ref=(f"refs/owlbear/attempts/{change_id}/{attempt_id}" if preserved_commit is not None else None),
            quarantine_commit=quarantine_commit,
            quarantine_ref=quarantine_ref,
        )

    def _validate_package_authority(self, runtime: DeliveryRuntime, package: VerifiedDesignPackage) -> None:
        if hashlib.sha256(package.authority_bytes).hexdigest() != runtime.authority_digest:
            self._fail("active package authority does not match the Delivery runtime")
        source_digests = {binding.source_name: binding.sha256 for binding in runtime.contract.source_bindings}
        if source_digests != {
            "intent.md": package.manifest.intent_sha256,
            "design.md": package.manifest.design_sha256,
        }:
            self._fail("active package sources do not match admitted Delivery bindings")

    def _publish_delivery_state(
        self,
        change_id: str,
        runtime: DeliveryRuntime,
        operation_id: str,
        *,
        expected_remote_head: str | None = None,
    ) -> DeliveryStatePublicationReceipt | None:
        if self._delivery_state_publisher is None:
            return None
        checkpoint = runtime.checkpoint_publication_state()
        pending = checkpoint.pending_checkpoint
        if pending is not None and pending.head is not None and checkpoint.published_head != pending.head:
            branch_receipt = self._publish_checkpoint_branch(change_id, checkpoint, pending.head)
            runtime.record_checkpoint_branch_publication(checkpoint, branch_receipt.published_head)
        package = self._package_store.read_verified(change_id)
        self._validate_package_authority(runtime, package)
        admission_path = self._target_root / "changes" / change_id / "admission.json"
        admission = DeliveryAdmissionReceipt.model_validate_json(admission_path.read_bytes())
        publication = self._delivery_state_publisher.publish(
            change_id=change_id,
            package_id=package.package_id,
            coordination=self._workspace_manager.show(change_id),
            runtime=runtime,
            admission=admission,
            operation_id=operation_id,
            captured_at=_timestamp(self._clock()),
            expected_remote_head=expected_remote_head,
        )
        runtime.acknowledge_pending_publication(hashlib.sha256(runtime.frontier_bytes()).hexdigest())
        return publication

    def _dependency_depth(self, runtime: DeliveryRuntime, outcome_id: str) -> int:
        dependencies = {outcome.outcome_id: outcome.dependency_ids for outcome in runtime.contract.outcomes}

        def depth(current: str) -> int:
            return 0 if not dependencies[current] else 1 + max(depth(item) for item in dependencies[current])

        return depth(outcome_id)

    def _runtime(self, change_id: str, *, for_mutation: bool = False, allow_finalizer: bool = False) -> DeliveryRuntime:
        self._reconcile_runtimes()
        try:
            runtime = self._runtimes[change_id]
        except KeyError as exc:
            detail = self._runtime_reconciliation_errors.get(change_id)
            if detail is not None:
                raise DeliveryRuntimeReconciliationError(change_id, detail) from exc
            self._fail(f"Delivery runtime is absent: {change_id}", exc)
        if for_mutation:
            detail = self._runtime_reconciliation_errors.get(change_id)
            if detail is not None:
                raise DeliveryRuntimeReconciliationError(change_id, detail)
            try:
                coordination = self._workspace_manager.show(change_id)
            except (OSError, RuntimeError, ValueError) as exc:
                raise DeliveryRuntimeReconciliationError(change_id, str(exc)) from exc
            self._coordinator.require_no_pending_recovery(change_id)
            action = coordination.continuation_action
            if (
                action is not None
                and action.finished_at is None
                and not self._coordinator.executing_continuation(change_id)
            ):
                message = f"selected Change retains engine action custody: {action.operation_id}"
                raise DeliveryActionBusyError(message)
            writer = coordination.writer
            if not allow_finalizer and writer is not None and writer.kind == "finalize":
                message = "selected Change retains active finalizer custody"
                raise DeliveryActionBusyError(message)
        return runtime

    def _require_target_sync_change_mutable(self, runtime: DeliveryRuntime) -> None:
        if runtime.change_stage() in {
            DeliveryChangeStage.DEFERRED,
            DeliveryChangeStage.ABANDONED,
            DeliveryChangeStage.COMPLETED,
        }:
            self._fail("target synchronization requires a mutable Change")

    def _require_external_head_adoption_change_mutable(self, runtime: DeliveryRuntime) -> None:
        if runtime.change_stage() in {
            DeliveryChangeStage.DEFERRED,
            DeliveryChangeStage.ABANDONED,
            DeliveryChangeStage.COMPLETED,
        }:
            self._fail("external Change head adoption requires a mutable Change")

    def _require_external_head_promotion_change_mutable(self, runtime: DeliveryRuntime) -> None:
        if (
            runtime.change_stage()
            in {
                DeliveryChangeStage.DEFERRED,
                DeliveryChangeStage.ABANDONED,
                DeliveryChangeStage.COMPLETED,
            }
            or runtime.finalization() is not None
        ):
            self._fail("external Change head promotion requires a pre-finalization mutable Change")

    def _checkpoint_lock_root(self, change_id: str) -> Path:
        return self._target_root / "publications/checkpoints/locks" / change_id

    @staticmethod
    def _outcome(runtime: DeliveryRuntime, outcome_id: str) -> DeliveryOutcome:
        return next(item for item in runtime.contract.outcomes if item.outcome_id == outcome_id)

    @staticmethod
    def _request(runtime: DeliveryRuntime, request_id: str) -> DeliveryRequest:
        matches = tuple(
            request
            for outcome in runtime.contract.outcomes
            for request in runtime.show_binding(outcome.outcome_id).requests
            if request.request_id == request_id
        )
        if len(matches) != 1:
            message = f"Delivery request is absent or ambiguous: {request_id}"
            raise PortfolioApplicationError(message)
        return matches[0]

    @staticmethod
    def _commitments(runtime: DeliveryRuntime, commitment_ids: tuple[str, ...]) -> tuple[DeliveryCommitment, ...]:
        selected = set(commitment_ids)
        return tuple(item for item in runtime.contract.commitments if item.commitment_id in selected)

    @staticmethod
    def _fail(message: str, cause: Exception | None = None) -> Never:
        raise PortfolioApplicationError(message) from cause


__all__ = [
    "ChangeExternalHeadPromotionReceipt",
    "DeliveryAcceptanceReconciliationOutcome",
    "DeliveryAcceptanceReconciliationStatus",
    "DeliveryAcquisitionFailure",
    "DeliveryAcquisitionResult",
    "DeliveryActionBusyError",
    "DeliveryActionSelection",
    "DeliveryBuildContext",
    "DeliveryCapacityWaitingError",
    "DeliveryClaimRecoveryResult",
    "DeliveryClaimRecoveryStatus",
    "DeliveryFinalizationContext",
    "DeliveryIntegrationAttentionStatus",
    "DeliveryLaunchPackage",
    "DeliveryPlanContext",
    "DeliveryRolePolicy",
    "DeliveryRuntimeReconciliationError",
    "PortfolioApplication",
    "PortfolioApplicationConfig",
    "PortfolioApplicationDependencies",
    "PortfolioApplicationError",
    "PortfolioApplicationHooks",
]
