"""Strict HTTP models for current Delivery work and operator controls."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from owlbear_delivery.delivery_runtime import DeliveryStage
from owlbear_delivery.portfolio_operating import PortfolioOperatingView
from owlbear_delivery.work_items import ChangeGroupView, WorkItemDetailView

if TYPE_CHECKING:
    from owlbear_delivery.change_workspace import ChangeTargetSyncAbortReceipt, ChangeTargetSyncReceipt
    from owlbear_delivery.portfolio_application import DeliveryChangeWorktreeCleanup, DeliveryChangeWorktreeRecovery


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


class TargetSyncResponse(_TargetHTTPModel):
    """Typed receipt returned after one exact target synchronization."""

    schema_version: Literal[1] = 1
    receipt_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    operation_id: str = Field(min_length=1)
    change_id: str = Field(min_length=1)
    integration_target: str = Field(min_length=1)
    expected_target: str = Field(pattern=r"^[0-9a-f]{40}$")
    target_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    change_head_before: str = Field(pattern=r"^[0-9a-f]{40}$")
    merged_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    merge_commit: bool

    @classmethod
    def from_receipt(cls, receipt: ChangeTargetSyncReceipt) -> TargetSyncResponse:
        """Convert one application sync receipt into the HTTP transport shape."""
        return cls(**receipt.model_dump())


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
    "RecoverChangeWorktreeBody",
    "ResolveChangeAttentionBody",
    "TargetSyncAbortResponse",
    "TargetSyncConflictBody",
    "TargetSyncResponse",
    "WorkItemDetailResponse",
    "WorkItemPortfolioResponse",
    "WorkItemPortfolioTotals",
]
