"""Strict HTTP models for current Delivery work and operator controls."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from owlbear_delivery.delivery_runtime import DeliveryStage
from owlbear_delivery.portfolio_application import DeliveryOperatorContext
from owlbear_delivery.work_items import WorkItemProjection


class _TargetHTTPModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class AttentionCounts(_TargetHTTPModel):
    """Count portfolio cards by orthogonal attention state."""

    user: int = Field(ge=0)
    agent: int = Field(ge=0)
    waiting: int = Field(ge=0)
    none: int = Field(ge=0)


class WorkItemPortfolioResponse(_TargetHTTPModel):
    """Return mixed-change cards and portfolio attention totals."""

    items: tuple[WorkItemSummaryResponse, ...]
    attention_counts: AttentionCounts


class WorkItemLinks(_TargetHTTPModel):
    """Typed control and attention resources for one outcome."""

    self: str
    answer_request: str
    clear_block: str
    recover_claim: str
    move_backward: str
    integration_attention: str
    integration_retry: str


class WorkItemSummaryResponse(_TargetHTTPModel):
    """One bounded current card with typed Delivery resources."""

    card: WorkItemProjection
    links: WorkItemLinks


class WorkItemDetailResponse(_TargetHTTPModel):
    """Bounded current operator state for one exact outcome."""

    operator: DeliveryOperatorContext
    links: WorkItemLinks


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


class BackwardMoveBody(_TargetHTTPModel):
    """Operator-selected earlier stage and reason."""

    target: str = Field(min_length=1)
    reason: str = Field(min_length=1)

    @field_validator("target")
    @classmethod
    def _validate_target(cls, value: str) -> str:
        DeliveryStage(value)
        return value


__all__ = [
    "AnswerRequestBody",
    "AttentionCounts",
    "BackwardMoveBody",
    "ClearBlockBody",
    "ConfirmLostClaimBody",
    "WorkItemDetailResponse",
    "WorkItemLinks",
    "WorkItemPortfolioResponse",
    "WorkItemSummaryResponse",
]
