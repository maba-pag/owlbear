"""Deterministic portfolio acquisition and bounded worker context."""

from __future__ import annotations

import hashlib
import html
import json
import logging
import subprocess
import time
import uuid
from contextlib import ExitStack, suppress
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
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
    ChangeCoordination,
    ChangeExternalHeadAdoptionReceipt,
    ChangeExternalHeadPromotionReceipt,
    ChangeTargetSyncAbortReceipt,
    ChangeTargetSyncConflictError,
    ChangeTargetSyncReceipt,
    ChangeWorkspaceManager,
    ChangeWorktreeAttentionCode,
    ChangeWorktreeAttentionError,
    ChangeWriter,
    CoordinationConflictError,
    DirtyWorktreeQuarantineReceipt,
    PortfolioCoordinator,
    PromoteExternalHead,
    PublicationBaselineRecoveryReceipt,
    PublicationBaselineUnavailableError,
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
    DeliveryAcceptanceAttentionReason,
    DeliveryAcceptanceWaitingError,
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
    DeliveryPlanCandidate,
    DeliveryRecoveryAttention,
    DeliveryRequest,
    DeliveryRequestResolution,
    DeliveryResultCandidate,
    DeliveryReturnContext,
    DeliveryRuntime,
    DeliveryRuntimeConflictError,
    DeliveryStage,
    DeliveryTaskDefinition,
    DeliveryTaskResult,
    DeliveryTransition,
    DeliveryWorkerRole,
    FinalizeDeliveryChange,
    OutcomeAuthorityBinding,
    PublishDeliveryPlan,
    PublishDeliveryResult,
    derive_change_stage,
    integration_attention_disposition,
    is_acceptance_waiting_observation,
    is_change_terminal,
    parse_delivery_frontier,
)
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
from owlbear_delivery.portfolio_operating import (
    DeliveryHealthDiagnostic,
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
    WorkItemDetailView,
    WorkItemNeed,
    WorkItemProjector,
    WorkItemPublicationPhase,
    WorkItemScope,
    WorkItemTargetSyncConflictView,
    WorkItemWorktreeCleanupView,
    WorkItemWorktreeRecoveryView,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

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
    from owlbear_delivery.delivery_state import DeliveryStatePublisher
    from owlbear_delivery.design_package import (
        DesignCheckpointResult,
        DesignPackageResult,
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
    change_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    reviewed_change_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    publication_phase: WorkItemPublicationPhase
    ready_for_finalization: bool
    readiness_diagnostics: tuple[str, ...]
    finalization_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    finalized_head: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    finalization_invalidation_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


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


class PortfolioApplicationError(RuntimeError):
    """Portfolio preparation or scoped context validation failed closed."""

    code = "ERR_DELIVERY_PORTFOLIO"


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
        self._execution_capacity = config.execution_capacity
        self._claim_timeout = timedelta(seconds=config.claim_timeout_seconds)
        self._policies = {policy.worker_role: policy for policy in config.role_policies}
        self._identity_factory = hooks.identity_factory if hooks else lambda: str(uuid.uuid4())
        self._clock = (
            hooks.clock
            if hooks
            else lambda: datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        )

    def create_design_session(
        self,
        change_id: str,
        intent_bytes: bytes,
        design_bytes: bytes,
    ) -> DesignPackageResult:
        """Create or replay one exact authored Design package."""
        return self._package_store.create(change_id, intent_bytes, design_bytes)

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
        with locked_roots((self._checkpoint_lock_root(change_id),)):
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
        self._runtime(change_id, for_mutation=True)
        with locked_roots((self._checkpoint_lock_root(change_id),)):
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
        coordination = self._workspace_manager.show(change_id)
        try:
            change_head = self._workspace_manager.observed_change_head(change_id)
        except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as exc:
            self._fail("finalization context could not resolve the managed Change head", exc)
        ready, diagnostics = runtime.finalization_readiness()
        finalization = runtime.finalization()
        invalidation = runtime.finalization_invalidation()
        if (
            ready
            and invalidation is not None
            and invalidation.reason == "review-repair"
            and change_head == invalidation.expected_head
        ):
            ready = False
            diagnostics = (*diagnostics, "review repair requires a new Change commit before finalization")
        if ready:
            try:
                self._workspace_manager.validate_finalization_head(
                    change_id,
                    change_head,
                    tuple(result.completed_commit for binding in runtime.bindings() for result in binding.results),
                )
            except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as exc:
                ready = False
                diagnostics = (str(exc),)
        return DeliveryFinalizationContext(
            change_id=change_id,
            branch=coordination.branch,
            worktree_path=coordination.worktree_path,
            change_head=change_head,
            reviewed_change_head=coordination.last_reviewed_commit,
            publication_phase=self._work_item_projector(runtime).publication_phase(),
            ready_for_finalization=ready,
            readiness_diagnostics=diagnostics,
            finalization_id=finalization.finalization_id if finalization is not None else None,
            finalized_head=finalization.exact_head if finalization is not None else None,
            finalization_invalidation_id=invalidation.invalidation_id if invalidation is not None else None,
        )

    def finalize_change(
        self,
        change_id: str,
        request: FinalizeDeliveryChange,
    ) -> DeliveryFinalizationReceipt:
        """Finalize one exact clean reviewed Change head and queue its checkpoint."""
        runtime = self._runtime(change_id, for_mutation=True)
        existing = runtime.finalization()
        if existing is not None:
            if (
                existing.operation_id == request.operation_id
                and existing.exact_head == request.exact_head
                and existing.observations == request.observations
                and existing.review == request.review
            ):
                with locked_roots((self._checkpoint_lock_root(change_id),)):
                    self._promote_finalized_external_head(change_id, existing.exact_head)
                return existing
            self._fail(
                "Delivery Change is already finalized with different authority",
                ValueError("finalization request is not an exact replay"),
            )
        if runtime.change_disposition() is not None:
            self._fail("finalization requires current Change attention resolution")
        context = self.show_finalization_context(change_id)
        if not context.ready_for_finalization:
            self._fail(
                "finalization requires a ready exact Change context",
                ValueError("; ".join(context.readiness_diagnostics)),
            )
        if request.exact_head != context.change_head:
            self._fail(
                "finalization request does not match the current Change head",
                ValueError("Change head changed"),
            )
        with locked_roots((self._checkpoint_lock_root(change_id),)):
            results = tuple(result for binding in runtime.bindings() for result in binding.results)
            with self._coordinator.publication_lock(change_id) as publication_lock:
                boundary_participant = self._workspace_manager.prepare_finalization_boundary(
                    change_id,
                    request.exact_head,
                    tuple(result.completed_commit for result in results),
                    publication_lock,
                )
                additional_participants = () if boundary_participant is None else (boundary_participant,)
                finalization = runtime.finalize_change(
                    request,
                    _timestamp(self._clock()),
                    additional_participants=additional_participants,
                )
            self._promote_finalized_external_head(change_id, finalization.exact_head)
            return finalization

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
        with locked_roots((self._checkpoint_lock_root(change_id),)):
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
            resolution = runtime.resolve_change_disposition(expected_disposition_id, _timestamp(self._clock()))
            self._publish_delivery_state(change_id, runtime, f"attention-resolution-{resolution.resolution_id}")
            return resolution

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
            return runtime.defer_change(reason, _timestamp(self._clock()))

    def resume_change(self, change_id: str) -> DeliveryChangeDeferral:
        """Resume one exact deferred Change from its retained prior state."""
        runtime = self._runtime(change_id, for_mutation=True)
        with locked_roots((self._checkpoint_lock_root(change_id),)):
            return runtime.resume_change()

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
                outcome = self._reconcile_awaiting_acceptance_locked(change_id, runtime)
        except BlockingIOError:
            return DeliveryAcceptanceReconciliationOutcome(
                change_id=change_id,
                status=DeliveryAcceptanceReconciliationStatus.SKIPPED,
                code="ERR_DELIVERY_RECONCILIATION_BUSY",
                detail="Change reconciliation is already in progress.",
            )
        except PublicationProviderError as exc:
            return self._provider_unavailable_outcome(change_id, exc)
        except (DeliveryRuntimeConflictError, OSError, ValueError) as exc:
            return DeliveryAcceptanceReconciliationOutcome(
                change_id=change_id,
                status=DeliveryAcceptanceReconciliationStatus.SKIPPED,
                code="ERR_DELIVERY_RECONCILIATION_STATE_CHANGED",
                detail=str(exc) or "Change state changed during reconciliation.",
            )
        result = outcome if outcome is not None else self._reconcile_merged_acceptance(change_id, runtime)
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
    ) -> DeliveryAcceptanceReconciliationOutcome | None:
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
        return self._classify_acceptance_observation(
            change_id,
            runtime,
            observation,
            _AcceptanceReconciliationAuthority(
                exact_head=finalization.exact_head,
                ready=ready,
                target_branch=publisher.target_branch,
            ),
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

    def _reconcile_merged_acceptance(
        self,
        change_id: str,
        runtime: DeliveryRuntime,
    ) -> DeliveryAcceptanceReconciliationOutcome:
        """Use the existing exact completion path after a matching merged read."""
        try:
            receipt = self.observe_acceptance(change_id)
        except DeliveryAcceptanceWaitingError as exc:
            return DeliveryAcceptanceReconciliationOutcome(
                change_id=change_id,
                status=DeliveryAcceptanceReconciliationStatus.WAITING,
                detail=str(exc),
            )
        except PublicationProviderError as exc:
            return self._provider_unavailable_outcome(change_id, exc)
        except PortfolioApplicationError as exc:
            if runtime.change_disposition() is not None:
                return DeliveryAcceptanceReconciliationOutcome(
                    change_id=change_id,
                    status=DeliveryAcceptanceReconciliationStatus.ATTENTION,
                    code=exc.code,
                    detail=str(exc),
                )
            return DeliveryAcceptanceReconciliationOutcome(
                change_id=change_id,
                status=DeliveryAcceptanceReconciliationStatus.SKIPPED,
                code=exc.code,
                detail=str(exc),
            )
        except (DeliveryRuntimeConflictError, OSError, ValueError) as exc:
            return DeliveryAcceptanceReconciliationOutcome(
                change_id=change_id,
                status=DeliveryAcceptanceReconciliationStatus.SKIPPED,
                code="ERR_DELIVERY_RECONCILIATION_STATE_CHANGED",
                detail=str(exc) or "Change state changed during reconciliation.",
            )
        return DeliveryAcceptanceReconciliationOutcome(
            change_id=change_id,
            status=DeliveryAcceptanceReconciliationStatus.COMPLETED,
            completion_id=receipt.completion_id,
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
            return runtime.abandon_change(reason, _timestamp(self._clock()))

    def observe_acceptance(self, change_id: str) -> CompletionReceipt:
        """Complete one Change from a fresh exact merged-PR observation."""
        if self._draft_pull_request_publisher is None:
            message = "draft pull-request publication is not configured"
            raise PortfolioApplicationError(message)
        runtime = self._runtime(change_id, for_mutation=True)
        with locked_roots((self._checkpoint_lock_root(change_id),)):
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
            completed = runtime.complete_change(receipt)
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
        with locked_roots((self._checkpoint_lock_root(change_id),)):
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
            )
            runtime.queue_admitted_design_checkpoint(snapshot.snapshot_head)
            if self._change_branch_publisher is not None and self._draft_pull_request_publisher is not None:
                self._reconcile_change_checkpoint(request.change_id, runtime)
            self._reconcile_runtimes()
            return result.model_copy(
                update={"frontier": parse_delivery_frontier(runtime.frontier_bytes())[0]}
            )

    def publish_delivery_plan(
        self,
        change_id: str,
        request: PublishDeliveryPlan,
    ) -> DeliveryPlanCandidate:
        """Publish one validated Planning candidate through its exact runtime."""
        return self._runtime(change_id, for_mutation=True).publish_plan(request)

    def publish_delivery_result(
        self,
        change_id: str,
        request: PublishDeliveryResult,
    ) -> DeliveryResultCandidate:
        """Publish one validated Build result through its exact runtime."""
        return self._runtime(change_id, for_mutation=True).publish_result(request)

    def transition_delivery(
        self,
        change_id: str,
        request: DeliveryTransition,
    ) -> OutcomeAuthorityBinding:
        """Apply one validated mechanical transition through its exact runtime."""
        runtime = self._runtime(change_id, for_mutation=True)
        with locked_roots((self._checkpoint_lock_root(change_id),)):
            return runtime.transition(request)

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
            WorkItemProjector(snapshot).group_view()
            for snapshot in self._portfolio_snapshots()
            if snapshot.contract.change_id not in self._runtime_reconciliation_errors
            if self._is_work_portfolio_visible(snapshot)
        )

    def portfolio_read_view(self) -> PortfolioReadView:
        """Return grouped work and operating facts from one immutable capture."""
        snapshots = self._portfolio_snapshots()
        groups = tuple(
            WorkItemProjector(snapshot).group_view()
            for snapshot in snapshots
            if snapshot.contract.change_id not in self._runtime_reconciliation_errors
            if self._is_work_portfolio_visible(snapshot)
        )
        return PortfolioReadView(
            groups=groups,
            operating=self._portfolio_operating_view(snapshots, groups),
            health=self._delivery_health_view(),
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

    def delivery_health(self) -> DeliveryHealthView:
        """Return bounded diagnostics for state excluded from Delivery authority."""
        self._reconcile_runtimes()
        return self._delivery_health_view()

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
            self._publish_delivery_state(change_id, runtime, f"target-sync-repair-{operation_id}")
            checkpoint = runtime.checkpoint_publication_state()
            if checkpoint.pending_checkpoint is not None:
                runtime.acknowledge_checkpoint_publication(
                    checkpoint.pending_checkpoint,
                    branch_receipt.published_head,
                )
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
                    "remote Change branch differs from Delivery-state snapshot" in diagnostic.detail
                    or "local Delivery runtime artifact differs from its remote snapshot: frontier.json"
                    in diagnostic.detail
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

    def _clear_target_sync_reconciliation(self, change_id: str) -> None:
        self._startup_health_diagnostics = tuple(
            diagnostic
            for diagnostic in self._startup_health_diagnostics
            if not (
                diagnostic.source == "remote-state"
                and diagnostic.code == "remote-state-reconciliation-required"
                and diagnostic.change_id == change_id
            )
        )
        self._runtime_reconciliation_errors.pop(change_id, None)
        self._runtime_snapshots.pop(change_id, None)
        self._reconcile_runtimes()
        if change_id in self._runtime_reconciliation_errors:
            self._fail("target-sync publication repair completed with remaining Change reconciliation errors")

    def _delivery_health_view(self) -> DeliveryHealthView:
        diagnostics: list[DeliveryHealthDiagnostic] = [
            *self._startup_health_diagnostics,
        ]
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
            )
            for change_id, detail in self._runtime_reconciliation_errors.items()
            if change_id not in diagnostic_change_ids
        )
        unique = {
            (
                diagnostic.source,
                diagnostic.code,
                diagnostic.detail,
                diagnostic.change_id,
                diagnostic.path,
                diagnostic.retry_safe,
            ): diagnostic
            for diagnostic in diagnostics
        }
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
        bounded = ordered[:_MAX_HEALTH_DIAGNOSTICS]
        return DeliveryHealthView(
            status=DeliveryHealthStatus.ATTENTION if bounded else DeliveryHealthStatus.HEALTHY,
            diagnostics=bounded,
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

    def show_work_item_view(self, change_id: str, item_key: str) -> WorkItemDetailView:
        """Show semantic and operator detail from one exact snapshot."""
        runtime = self._runtime(change_id)
        try:
            view = self._work_item_projector(runtime).show_view(item_key)
        except (KeyError, StopIteration) as exc:
            self._fail(f"work item is absent: {item_key}", exc)
        if view.publication is None:
            return view
        cleanup = self._worktree_cleanup_view(runtime)
        conflict = self._workspace_manager.show(change_id).target_sync_conflict
        retained = next(
            (item for item in self._workspace_manager.list_retained() if item.change_id == change_id),
            None,
        )
        recovery = self._worktree_recovery_view(retained) if retained is not None else None
        publication = view.publication.model_copy(
            update={
                "worktree_cleanup": cleanup,
                "worktree_recovery": recovery,
                "target_sync_conflict": (
                    WorkItemTargetSyncConflictView(
                        conflict_id=conflict.conflict_id,
                        operation_id=conflict.operation_id,
                        target_head=conflict.target_head,
                        change_head_before=conflict.change_head_before,
                        conflict_paths=conflict.conflict_paths,
                    )
                    if conflict is not None
                    else None
                ),
            }
        )
        if publication.phase in {
            WorkItemPublicationPhase.READY_FOR_FINALIZATION,
            WorkItemPublicationPhase.FINALIZATION_INVALIDATED,
        }:
            try:
                finalization_context = self.show_finalization_context(change_id)
            except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as exc:
                diagnostic = str(exc) or "Finalization readiness could not be inspected."
                publication = publication.model_copy(
                    update={
                        "ready_for_finalization": False,
                        "readiness_diagnostics": (diagnostic,),
                    }
                )
            else:
                publication = publication.model_copy(
                    update={
                        "ready_for_finalization": finalization_context.ready_for_finalization,
                        "readiness_diagnostics": finalization_context.readiness_diagnostics,
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
            return self._runtime(change_id, for_mutation=True).resolve_request(request_id, resolution)

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
            return self._runtime(change_id, for_mutation=True).unblock(outcome_id, block_id, operator_note, locators)

    def administrative_move(
        self,
        change_id: str,
        request: AdministrativeDeliveryMove,
    ) -> AdministrativeDeliveryMoveResult:
        """Delegate an authorized operator backward movement to the owning runtime."""
        with self._coordinator.acquisition_lock():
            runtime = self._runtime(change_id, for_mutation=True)
            with locked_roots((self._checkpoint_lock_root(change_id),)):
                return runtime.administrative_move(request)

    def preview_administrative_move(
        self,
        change_id: str,
        outcome_id: str,
        target: DeliveryStage,
    ) -> AdministrativeDeliveryMovePreview:
        """Preview one exact backward movement without mutating authority."""
        return self._runtime(change_id).preview_administrative_move(outcome_id, target)

    def _work_item_projector(self, runtime: DeliveryRuntime) -> WorkItemProjector:
        return WorkItemProjector(self._delivery_snapshot(runtime))

    def _worktree_cleanup_view(self, runtime: DeliveryRuntime) -> WorkItemWorktreeCleanupView | None:
        change_id = runtime.contract.change_id
        retained = next(
            (item for item in self._workspace_manager.list_retained() if item.change_id == change_id),
            None,
        )
        if retained is None:
            return None
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
            if frontier is not None:
                occupancy[change_id] = sum(binding.active_claim is not None for binding in frontier.bindings)
        for change_id, runtime in self._runtimes.items():
            try:
                active_count = len(runtime.active_claims())
            except (OSError, RuntimeError, ValueError):
                continue
            occupancy[change_id] = max(occupancy.get(change_id, 0), active_count)
        return sum(occupancy.values())

    def _delivery_snapshot(self, runtime: DeliveryRuntime) -> DeliveryPortfolioSnapshot:
        frontier_bytes = runtime.frontier_bytes()
        frontier = parse_delivery_frontier(frontier_bytes)[0]
        return DeliveryPortfolioSnapshot.capture(
            runtime.contract,
            frontier_bytes,
            publication_observation=self._publication_observation(runtime.contract.change_id, frontier),
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
                    if _timestamp(claim.started_at) > cutoff:
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
            self._coordinator.recover_pending_transactions()
            self._reconcile_runtimes()
            pre_claim_snapshots = self._capture_portfolio_snapshots()
            recoveries, recovery_failures = self._recover_expired_claims()
            failures = list(recovery_failures)
            if recoveries or recovery_failures:
                self._reconcile_runtimes()
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

    def recover_claim(
        self,
        change_id: str,
        outcome_id: str,
        attempt_id: str,
        claim_id: str,
    ) -> DeliveryClaimRecoveryResult:
        """Automatically preserve and recover one exact failed claim or retain typed attention."""
        with self._coordinator.acquisition_lock():
            return self._recover_claim(change_id, outcome_id, attempt_id, claim_id)

    def recover_integration_repair_claim(
        self,
        change_id: str,
        attempt_id: str,
        claim_id: str,
    ) -> DeliveryIntegrationRepairRecoveryResult:
        """Restart and remove one exact failed Integration repair claim."""
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
        snapshot = self._workspace_manager.recovery_snapshot(change_id, attempt_id)
        preserved_commit = snapshot.preserved_commit or snapshot.branch_head
        if snapshot.writer is not None:
            if not self._active_recovery_matches(snapshot, attempt_id, claim_id):
                self._fail("repair recovery does not match active writer custody")
            self._workspace_manager.restart(change_id, attempt_id, preserved_commit)
        elif not self._released_recovery_matches(snapshot):
            self._fail("released repair recovery does not match reviewed workspace state")
        runtime.remove_integration_repair_claim(attempt_id, claim_id)
        return DeliveryIntegrationRepairRecoveryResult(
            change_id=change_id,
            attempt_id=attempt_id,
            claim_id=claim_id,
            preserved_commit=preserved_commit,
        )

    def _recover_claim(  # noqa: PLR0911 - each exact recovery disposition has distinct observable evidence.
        self,
        change_id: str,
        outcome_id: str,
        attempt_id: str,
        claim_id: str,
    ) -> DeliveryClaimRecoveryResult:
        runtime = self._runtime(change_id, for_mutation=True)
        binding = runtime.require_active_claim(outcome_id, attempt_id, claim_id)
        claim = binding.active_claim
        if claim is None:
            self._fail("outcome has no active claim")
        if claim.worker_role != DeliveryWorkerRole.BUILDER:
            runtime.remove_active_claim(outcome_id, attempt_id, claim_id)
            return self._recovered(change_id, outcome_id, attempt_id, claim_id)
        snapshot = self._workspace_manager.recovery_snapshot(change_id, attempt_id)
        if snapshot.writer is None:
            if self._released_recovery_matches(snapshot):
                quarantine: DirtyWorktreeQuarantineReceipt | None = None
                if snapshot.quarantine_ref is not None or snapshot.quarantine_commit is not None:
                    try:
                        quarantine = self._workspace_manager.verify_dirty_worktree_quarantine(
                            change_id,
                            attempt_id,
                            claim_id,
                            _dirty_recovery_operation_id(change_id, outcome_id, attempt_id, claim_id),
                        )
                    except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as exc:
                        return self._retain_recovery_attention(
                            runtime,
                            outcome_id,
                            claim,
                            snapshot,
                            reason=f"Automatic dirty worktree preservation evidence could not be verified: {exc}",
                            retry_condition="Retry automatic recovery while the preserved quarantine evidence remains.",
                        )
                runtime.remove_active_claim(outcome_id, attempt_id, claim_id)
                return self._recovered(
                    change_id,
                    outcome_id,
                    attempt_id,
                    claim_id,
                    snapshot.preserved_commit,
                    quarantine_commit=(
                        quarantine.quarantine_commit if quarantine is not None else snapshot.quarantine_commit
                    ),
                    quarantine_ref=quarantine.quarantine_ref if quarantine is not None else snapshot.quarantine_ref,
                )
            return self._retain_recovery_attention(runtime, outcome_id, claim, snapshot)
        if not self._active_recovery_matches(snapshot, attempt_id, claim_id):
            return self._retain_recovery_attention(runtime, outcome_id, claim, snapshot)
        quarantine: DirtyWorktreeQuarantineReceipt | None = None
        if (
            snapshot.quarantine_ref is not None
            or snapshot.quarantine_commit is not None
            or (snapshot.worktree_head is not None and not snapshot.clean)
        ):
            try:
                quarantine = self._workspace_manager.quarantine_dirty_worktree(
                    change_id,
                    attempt_id,
                    claim_id,
                    _dirty_recovery_operation_id(change_id, outcome_id, attempt_id, claim_id),
                )
            except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as exc:
                return self._retain_recovery_attention(
                    runtime,
                    outcome_id,
                    claim,
                    snapshot,
                    reason=f"Automatic dirty worktree preservation failed: {exc}",
                    retry_condition="Retry automatic preservation while exact Builder custody is retained.",
                )
        rejected_head = snapshot.preserved_commit or snapshot.branch_head
        self._workspace_manager.restart(change_id, attempt_id, rejected_head)
        runtime.remove_active_claim(outcome_id, attempt_id, claim_id)
        return self._recovered(
            change_id,
            outcome_id,
            attempt_id,
            claim_id,
            rejected_head,
            quarantine_commit=quarantine.quarantine_commit if quarantine is not None else snapshot.quarantine_commit,
            quarantine_ref=quarantine.quarantine_ref if quarantine is not None else snapshot.quarantine_ref,
        )

    def _candidates(self) -> tuple[_Candidate, ...]:
        candidates = []
        for change_id, runtime in self._runtimes.items():
            if change_id in self._runtime_reconciliation_errors:
                continue
            if runtime.active_claims() or runtime.change_stage() != DeliveryChangeStage.BUILDING:
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
    ) -> _PreparedSource | DeliveryAcquisitionFailure:
        try:
            package = self._package_store.read_verified(change_id)
            self._validate_package_authority(runtime, package)
            coordination = self._workspace_manager.show(change_id)
            source_head = self._workspace_manager.source_head(change_id)
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
    ) -> DeliveryLaunchPackage | DeliveryAcquisitionFailure:
        claim = self._new_claim(candidate.role, candidate.task_id)
        candidate.runtime.activate_claim(ActivateDeliveryClaim(outcome_id=candidate.binding.outcome_id, claim=claim))
        writer = None
        if candidate.role == DeliveryWorkerRole.BUILDER:
            try:
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
            except CoordinationConflictError as exc:
                return DeliveryAcquisitionFailure(
                    change_id=candidate.change_id,
                    outcome_id=candidate.binding.outcome_id,
                    attempt_id=claim.attempt_id,
                    claim_id=claim.claim_id,
                    code=exc.code,
                    detail=str(exc),
                    retry_condition="Remove the exact failed claim after reconciling writer custody.",
                )
            writer = coordination.writer
        return self._launch_package(candidate, claim, source, writer)

    def _current_launch(
        self,
        change_id: str,
        runtime: DeliveryRuntime,
        binding: OutcomeAuthorityBinding,
    ) -> DeliveryLaunchPackage:
        source = self._prepare_source(change_id, runtime, binding.outcome_id, binding.active_claim.worker_role)
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
    ) -> None:
        if self._delivery_state_publisher is None:
            return
        package = self._package_store.read_verified(change_id)
        self._validate_package_authority(runtime, package)
        admission_path = self._target_root / "changes" / change_id / "admission.json"
        admission = DeliveryAdmissionReceipt.model_validate_json(admission_path.read_bytes())
        self._delivery_state_publisher.publish(
            change_id=change_id,
            package_id=package.package_id,
            coordination=self._workspace_manager.show(change_id),
            runtime=runtime,
            admission=admission,
            operation_id=operation_id,
            captured_at=_timestamp(self._clock()),
        )

    def _dependency_depth(self, runtime: DeliveryRuntime, outcome_id: str) -> int:
        dependencies = {outcome.outcome_id: outcome.dependency_ids for outcome in runtime.contract.outcomes}

        def depth(current: str) -> int:
            return 0 if not dependencies[current] else 1 + max(depth(item) for item in dependencies[current])

        return depth(outcome_id)

    def _runtime(self, change_id: str, *, for_mutation: bool = False) -> DeliveryRuntime:
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
    "DeliveryBuildContext",
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
