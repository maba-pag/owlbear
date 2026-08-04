"""Protocol models for the target delivery MCP surface."""

from __future__ import annotations

import json

from pydantic import BaseModel, ConfigDict, Field

from owlbear_kanban.delivery_application_loader import (
    DeliveryRoleIdentityConfig,
    DeliveryRolePoliciesConfig,
    DeliveryStartupConfig,
)
from owlbear_kanban.delivery_runtime import (
    DeliveryIntegrationRepair,
    DeliveryTransition,
    PublishDeliveryPlan,
    PublishDeliveryResult,
)
from owlbear_kanban.identities import ChangeId
from owlbear_kanban.target_admission import DeliveryAdmissionRequest


class _TargetProtocolModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class DeliveryStartupDiagnostic(RuntimeError):
    """Structured fail-closed Delivery startup failure."""

    __slots__ = ("code", "detail", "field", "retry_safe")

    def __init__(self, code: str, detail: str, field: str) -> None:
        self.code = code
        self.detail = detail
        self.field = field
        self.retry_safe = False
        super().__init__(json.dumps(self.model_dump(), sort_keys=True))

    def model_dump(self) -> dict[str, str | bool]:
        """Return the stable diagnostic fields without rejected values."""
        return {
            "code": self.code,
            "detail": self.detail,
            "field": self.field,
            "retry_safe": self.retry_safe,
        }


class TargetDiagnostic(_TargetProtocolModel):
    """Stable transport failure with current semantic authority identity."""

    code: str = Field(min_length=1)
    detail: str = Field(min_length=1)
    current_authority_identity: str = Field(min_length=1)
    retry_safe: bool


class EmptyParams(_TargetProtocolModel):
    """Validate an operation that accepts no parameters."""


class ChangeParams(_TargetProtocolModel):
    """Validate one exact Delivery change identity."""

    change_id: ChangeId


class CreateDesignSessionParams(ChangeParams):
    """Validate authored Design source bytes."""

    intent_bytes: bytes
    design_bytes: bytes


class ReviseDesignSessionParams(CreateDesignSessionParams):
    """Validate one compare-and-swap authored Design revision."""

    expected_package_id: str = Field(pattern=r"^[0-9a-f]{64}$")


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
    "DeliveryRoleIdentityConfig",
    "DeliveryRolePoliciesConfig",
    "DeliveryStartupConfig",
    "DeliveryStartupDiagnostic",
    "EmptyParams",
    "IntegrationRepairParams",
    "PublishDeliveryPlanParams",
    "PublishDeliveryResultParams",
    "ReviseDesignSessionParams",
    "SearchCompletedParams",
    "ShowCompletedParams",
    "TargetDiagnostic",
    "TransitionDeliveryParams",
    "WorkItemParams",
]
