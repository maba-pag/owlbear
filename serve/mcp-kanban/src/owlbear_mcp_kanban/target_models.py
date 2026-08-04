"""Protocol models for the target delivery MCP surface."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from owlbear_kanban.delivery_runtime import (
    DeliveryIntegrationRepair,
    DeliveryTransition,
    PublishDeliveryPlan,
    PublishDeliveryResult,
)
from owlbear_kanban.identities import ChangeId
from owlbear_kanban.target_admission import DeliveryAdmissionRequest
from owlbear_kanban.target_runtime import RuntimeId
from owlbear_kanban.work_items import WorkItemProjection


class _TargetProtocolModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class TargetDiagnostic(_TargetProtocolModel):
    """Stable transport failure with current semantic authority identity."""

    code: str = Field(min_length=1)
    detail: str = Field(min_length=1)
    current_authority_identity: str = Field(min_length=1)
    retry_safe: bool


class WorkItemPage(_TargetProtocolModel):
    """One stable page from the global semantic work portfolio."""

    items: tuple[WorkItemProjection, ...]
    authority_identity: str = Field(min_length=1)
    next_cursor: str | None = None


class TargetCursor(_TargetProtocolModel):
    """Opaque cursor payload bound to one exact portfolio projection."""

    schema_version: Literal[1] = 1
    query_identity: str = Field(min_length=1)
    offset: int = Field(ge=0)


class TargetRequestParams(_TargetProtocolModel):
    """Validate one scoped target request at the MCP boundary."""

    request_id: RuntimeId
    change_id: ChangeId
    authority_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    work_item_id: str = Field(min_length=1)
    commitment_id: str = Field(min_length=1)
    task_id: str | None = None
    created_at: str = Field(min_length=1)
    summary: str = Field(min_length=1)


class EmptyParams(_TargetProtocolModel):
    """Validate an operation that accepts no parameters."""


class ChangeParams(_TargetProtocolModel):
    """Validate one exact Delivery change identity."""

    change_id: ChangeId


class CreateDesignSessionParams(ChangeParams):
    """Validate authored Design source bytes."""

    intent_bytes: bytes
    design_bytes: bytes


class WorkItemParams(ChangeParams):
    """Validate one exact work item within a Delivery change."""

    work_item_id: str = Field(min_length=1)


class ClaimContextParams(ChangeParams):
    """Validate one exact active Delivery claim."""

    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    attempt_id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)


class AdmitDeliveryChangeParams(_TargetProtocolModel):
    """Validate source-bound Delivery admission."""

    request: DeliveryAdmissionRequest


class PublishDeliveryPlanParams(ChangeParams):
    """Validate one Planning publication."""

    request: PublishDeliveryPlan


class PublishDeliveryResultParams(ChangeParams):
    """Validate one Build result publication."""

    request: PublishDeliveryResult


class TransitionDeliveryParams(ChangeParams):
    """Validate one worker-owned mechanical transition."""

    request: DeliveryTransition


class IntegrationRepairParams(_TargetProtocolModel):
    """Validate one independently reviewed Integration repair."""

    repair: DeliveryIntegrationRepair


class CompletedPageParams(_TargetProtocolModel):
    """Validate one bounded completed-history page request."""

    cursor: str | None = None
    limit: int = Field(default=100, gt=0, le=100)


class SearchCompletedParams(CompletedPageParams):
    """Validate one completed-history semantic search."""

    query: str = Field(min_length=1)


class ShowCompletedParams(ChangeParams):
    """Validate one exact completed Delivery record lookup."""

    completion_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


__all__ = [
    "AdmitDeliveryChangeParams",
    "ChangeParams",
    "ClaimContextParams",
    "CompletedPageParams",
    "CreateDesignSessionParams",
    "EmptyParams",
    "IntegrationRepairParams",
    "PublishDeliveryPlanParams",
    "PublishDeliveryResultParams",
    "SearchCompletedParams",
    "ShowCompletedParams",
    "TargetCursor",
    "TargetDiagnostic",
    "TargetRequestParams",
    "TransitionDeliveryParams",
    "WorkItemPage",
    "WorkItemParams",
]
