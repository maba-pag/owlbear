"""Strict HTTP models for current Delivery work and operator controls."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from owlbear_delivery.delivery_runtime import DeliveryStage
from owlbear_delivery.portfolio_operating import PortfolioOperatingView
from owlbear_delivery.work_items import ChangeGroupView, WorkItemDetailView


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
    "ClearBlockBody",
    "ConfirmLostClaimBody",
    "DesignWorkDetailResponse",
    "NeedsCounts",
    "ResolveChangeAttentionBody",
    "WorkItemDetailResponse",
    "WorkItemPortfolioResponse",
    "WorkItemPortfolioTotals",
]
