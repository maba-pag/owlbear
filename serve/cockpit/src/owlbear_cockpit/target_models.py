"""Strict HTTP models for current Delivery work and operator controls."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from owlbear_delivery.delivery_runtime import DeliveryStage
from owlbear_delivery.portfolio_operating import PortfolioOperatingView
from owlbear_delivery.publication_provider import (
    PublicationCheckBlockingState,
    PublicationCheckKind,
    classify_publication_check,
)
from owlbear_delivery.work_items import ChangeGroupView, WorkItemDetailView

if TYPE_CHECKING:
    from owlbear_delivery.change_workspace import ChangeTargetSyncAbortReceipt, ChangeTargetSyncReceipt
    from owlbear_delivery.draft_pull_request import PublicationCheckObservationReceipt
    from owlbear_delivery.portfolio_application import (
        DeliveryAcceptanceReconciliationOutcome,
        DeliveryChangePublicationSupersessionReceipt,
        DeliveryChangeWorktreeCleanup,
        DeliveryChangeWorktreeRecovery,
    )


class _TargetHTTPModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class NeedsCounts(_TargetHTTPModel):
    """Count portfolio rows by their mutually exclusive Needs state."""

    you: int = Field(ge=0)
    dependency: int = Field(ge=0)
    none: int = Field(ge=0)


class ActivityCounts(_TargetHTTPModel):
    """Count portfolio rows by current execution activity."""

    idle: int = Field(ge=0)
    ready: int = Field(ge=0)
    working: int = Field(ge=0)


class WorkItemPortfolioTotals(_TargetHTTPModel):
    """Independent portfolio totals for rows, lifecycle, Needs, and Activity."""

    total: int = Field(ge=0)
    complete: int = Field(ge=0)
    needs: NeedsCounts
    activity: ActivityCounts


class WorkItemPortfolioResponse(_TargetHTTPModel):
    """Return Change-grouped current Work Items and independent totals."""

    groups: tuple[ChangeGroupView, ...]
    totals: WorkItemPortfolioTotals
    operating: PortfolioOperatingView


class WorkItemDetailResponse(_TargetHTTPModel):
    """Semantic and operator detail from one exact snapshot."""

    item: WorkItemDetailView


class PublicationCheckView(_TargetHTTPModel):
    """One bounded provider check with Delivery-owned readiness meaning."""

    check_id: str = Field(min_length=1)
    kind: PublicationCheckKind
    name: str = Field(min_length=1)
    status: str = Field(min_length=1)
    conclusion: str | None = None
    required: bool
    blocking_state: PublicationCheckBlockingState


class PublicationChecksObservationResponse(_TargetHTTPModel):
    """Bounded exact-head publication checks observed through Delivery."""

    schema_version: Literal[1] = 1
    observation_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    change_id: str = Field(min_length=1)
    repository: str = Field(min_length=3, pattern=r"^[^\s/]+/[^\s/]+$")
    pull_request_number: int = Field(gt=0)
    exact_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    observed_at: datetime
    rollup_state: str | None = Field(default=None, min_length=1)
    checks: tuple[PublicationCheckView, ...]
    required_failure_count: int = Field(ge=0)
    truncated_count: int = Field(ge=0)

    @classmethod
    def from_receipt(cls, receipt: PublicationCheckObservationReceipt) -> PublicationChecksObservationResponse:
        """Order and bound provider checks without moving readiness authority to HTTP."""
        classified = tuple((check, classify_publication_check(check)) for check in receipt.snapshot.checks)
        state_order = {
            PublicationCheckBlockingState.BLOCKING: 0,
            PublicationCheckBlockingState.REQUIRED_PENDING: 1,
            PublicationCheckBlockingState.NOT_BLOCKING: 2,
        }
        ordered = tuple(
            sorted(
                classified,
                key=lambda item: (state_order[item[1]], item[0].name.casefold(), item[0].check_id),
            )
        )
        limit = 200
        return cls(
            observation_id=receipt.observation_id,
            change_id=receipt.change_id,
            repository=receipt.repository,
            pull_request_number=receipt.number,
            exact_commit=receipt.exact_commit,
            observed_at=receipt.observed_at,
            rollup_state=receipt.snapshot.rollup_state,
            checks=tuple(
                PublicationCheckView(
                    check_id=check.check_id,
                    kind=check.kind,
                    name=check.name,
                    status=check.status,
                    conclusion=check.conclusion,
                    required=check.required,
                    blocking_state=state,
                )
                for check, state in ordered[:limit]
            ),
            required_failure_count=sum(state is PublicationCheckBlockingState.BLOCKING for _check, state in classified),
            truncated_count=max(len(ordered) - limit, 0),
        )


class AcceptanceReconciliationRequest(_TargetHTTPModel):
    """Optional current Change IDs supplied by one visible Cockpit page."""

    change_ids: list[Annotated[str, Field(min_length=1)]] | None = Field(default=None, max_length=100)


class AcceptanceReconciliationOutcomeResponse(_TargetHTTPModel):
    """One bounded provider reconciliation result."""

    change_id: str = Field(min_length=1)
    status: str = Field(min_length=1)
    code: str | None = Field(default=None, min_length=1)
    detail: str | None = Field(default=None, min_length=1)
    completion_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def from_result(cls, result: DeliveryAcceptanceReconciliationOutcome) -> AcceptanceReconciliationOutcomeResponse:
        """Convert one Delivery outcome without adding transport semantics."""
        return cls(**result.model_dump(mode="json"))


class AcceptanceReconciliationResponse(_TargetHTTPModel):
    """Batch of isolated acceptance reconciliation outcomes."""

    outcomes: tuple[AcceptanceReconciliationOutcomeResponse, ...]


class DesignWorkDetailResponse(_TargetHTTPModel):
    """Verified authored Design sources for one pre-admission package."""

    change_id: str = Field(min_length=1)
    package_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    intent_markdown: str
    design_markdown: str


class AnswerRequestBody(_TargetHTTPModel):
    """Selected option, free-text answer, or both for one pending request."""

    selected_option_id: str | None = None
    response_text: str | None = None

    @model_validator(mode="after")
    def _require_answer(self) -> AnswerRequestBody:
        if self.selected_option_id is None and (self.response_text is None or not self.response_text.strip()):
            message = "request answer requires a selected option or response text"
            raise ValueError(message)
        return self


class ClearBlockBody(_TargetHTTPModel):
    """Operator evidence clearing one requestless same-stage block."""

    operator_note: str = Field(min_length=1)
    locators: list[str] = Field(min_length=1)


class ConfirmLostClaimBody(_TargetHTTPModel):
    """Explicit confirmation for removal of one exact failed claim."""

    confirmed_lost: Literal[True]
    attempt_id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)


class ResolveChangeAttentionBody(_TargetHTTPModel):
    """Exact Change attention identity selected by the operator."""

    expected_disposition_id: str = Field(pattern=r"^[0-9a-f]{64}$")


class ChangeDispositionReasonBody(_TargetHTTPModel):
    """User reason for deferring or abandoning one Change."""

    reason: str = Field(min_length=1)


class AbandonChangeBody(_TargetHTTPModel):
    """Explicit confirmation and reason for irreversible Change abandonment."""

    confirmed_abandonment: Literal[True]
    reason: str = Field(min_length=1)


class CleanupCompletedChangeBody(_TargetHTTPModel):
    """Exact completion receipt required for completed worktree cleanup."""

    completion_id: str = Field(pattern=r"^[0-9a-f]{64}$")


class RecoverChangeWorktreeBody(_TargetHTTPModel):
    """Explicit confirmation and exact reviewed head for worktree recovery."""

    confirmed_recovery: Literal[True]
    recovery_reviewed_head: str = Field(pattern=r"^[0-9a-f]{40}$")


class TargetSyncBody(_TargetHTTPModel):
    """Stable operation identity used to reconcile a target-sync retry."""

    operation_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class TargetSyncConflictBody(_TargetHTTPModel):
    """Exact operation and attention identity for one preserved target conflict exit."""

    expected_disposition_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    target_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    operation_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class SupersedePublicationBody(_TargetHTTPModel):
    """Stable operation identity used to reconcile a publication successor retry."""

    operation_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class TargetSyncResponse(_TargetHTTPModel):
    """Typed receipt returned after one exact target synchronization."""

    schema_version: Literal[1] = 1
    receipt_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    operation_id: str = Field(min_length=1)
    change_id: str = Field(min_length=1)
    target_branch: str = Field(min_length=1)
    expected_target: str = Field(pattern=r"^[0-9a-f]{40}$")
    target_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    change_head_before: str = Field(pattern=r"^[0-9a-f]{40}$")
    merged_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    merge_commit: bool

    @classmethod
    def from_receipt(cls, receipt: ChangeTargetSyncReceipt) -> TargetSyncResponse:
        """Convert one application sync receipt into the HTTP transport shape."""
        return cls(
            receipt_id=receipt.receipt_id,
            operation_id=receipt.operation_id,
            change_id=receipt.change_id,
            target_branch=receipt.integration_target,
            expected_target=receipt.expected_target,
            target_head=receipt.target_head,
            change_head_before=receipt.change_head_before,
            merged_head=receipt.merged_head,
            merge_commit=receipt.merge_commit,
        )


class TargetSyncAbortResponse(_TargetHTTPModel):
    """Typed receipt returned after one exact target-sync abort."""

    schema_version: Literal[1] = 1
    receipt_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    operation_id: str = Field(min_length=1)
    change_id: str = Field(min_length=1)
    target_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    restored_head: str = Field(pattern=r"^[0-9a-f]{40}$")

    @classmethod
    def from_receipt(cls, receipt: ChangeTargetSyncAbortReceipt) -> TargetSyncAbortResponse:
        """Convert one application abort receipt into the HTTP transport shape."""
        return cls(**receipt.model_dump())


class PublicationSupersessionResponse(_TargetHTTPModel):
    """Compact application receipt returned after one publication successor operation."""

    schema_version: Literal[1] = 1
    receipt_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    operation_id: str = Field(min_length=1)
    change_id: str = Field(min_length=1)
    predecessor_publication_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    successor_publication_id: str = Field(pattern=r"^[0-9a-f]{64}$")

    @classmethod
    def from_receipt(cls, receipt: DeliveryChangePublicationSupersessionReceipt) -> PublicationSupersessionResponse:
        """Convert one application supersession receipt into the HTTP transport shape."""
        return cls(
            receipt_id=receipt.receipt_id,
            operation_id=receipt.operation_id,
            change_id=receipt.change_id,
            predecessor_publication_id=receipt.predecessor_publication_id,
            successor_publication_id=receipt.successor_publication_id,
        )


class ChangeWorktreeCleanupResponse(_TargetHTTPModel):
    """Typed receipt returned after one exact terminal worktree cleanup."""

    cleanup_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    change_id: str = Field(min_length=1)
    branch: str = Field(min_length=1)
    worktree_path: str = Field(min_length=1)
    branch_head: str = Field(pattern=r"^[0-9a-f]{40}$")

    @classmethod
    def from_receipt(cls, receipt: DeliveryChangeWorktreeCleanup) -> ChangeWorktreeCleanupResponse:
        """Convert one application receipt into the HTTP transport shape."""
        return cls(
            cleanup_id=receipt.cleanup_id,
            change_id=receipt.change_id,
            branch=receipt.branch,
            worktree_path=str(receipt.worktree_path),
            branch_head=receipt.branch_head,
        )


class ChangeWorktreeRecoveryResponse(_TargetHTTPModel):
    """Typed receipt returned after one exact Change worktree recovery."""

    change_id: str = Field(min_length=1)
    branch: str = Field(min_length=1)
    worktree_path: str = Field(min_length=1)
    branch_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    recovery_reviewed_head: str = Field(pattern=r"^[0-9a-f]{40}$")

    @classmethod
    def from_receipt(cls, receipt: DeliveryChangeWorktreeRecovery) -> ChangeWorktreeRecoveryResponse:
        """Convert one application receipt into the HTTP transport shape."""
        return cls(
            change_id=receipt.change_id,
            branch=receipt.branch,
            worktree_path=str(receipt.worktree_path),
            branch_head=receipt.branch_head,
            recovery_reviewed_head=receipt.recovery_reviewed_head,
        )


class BackwardMoveBody(_TargetHTTPModel):
    """Operator-selected earlier stage and reason."""

    target: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    snapshot_version: str = Field(pattern=r"^[0-9a-f]{64}$")

    @field_validator("target")
    @classmethod
    def _validate_target(cls, value: str) -> str:
        DeliveryStage(value)
        return value


class BackwardMovePreviewBody(_TargetHTTPModel):
    """Earlier stage selected for exact invalidation preview."""

    target: str = Field(min_length=1)

    @field_validator("target")
    @classmethod
    def _validate_target(cls, value: str) -> str:
        DeliveryStage(value)
        return value


__all__ = [
    "AbandonChangeBody",
    "AcceptanceReconciliationOutcomeResponse",
    "AcceptanceReconciliationRequest",
    "AcceptanceReconciliationResponse",
    "ActivityCounts",
    "AnswerRequestBody",
    "BackwardMoveBody",
    "BackwardMovePreviewBody",
    "ChangeDispositionReasonBody",
    "ChangeWorktreeCleanupResponse",
    "ChangeWorktreeRecoveryResponse",
    "CleanupCompletedChangeBody",
    "ClearBlockBody",
    "ConfirmLostClaimBody",
    "DesignWorkDetailResponse",
    "NeedsCounts",
    "PublicationCheckView",
    "PublicationChecksObservationResponse",
    "RecoverChangeWorktreeBody",
    "ResolveChangeAttentionBody",
    "TargetSyncAbortResponse",
    "TargetSyncConflictBody",
    "TargetSyncResponse",
    "WorkItemDetailResponse",
    "WorkItemPortfolioResponse",
    "WorkItemPortfolioTotals",
]
