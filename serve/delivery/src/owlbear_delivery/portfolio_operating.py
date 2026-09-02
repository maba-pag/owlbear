"""Portfolio-wide operating facts and advisory session guidance."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from owlbear_delivery.delivery_runtime import DeliveryChangeStage


class PortfolioWorkScope(StrEnum):
    """Scopes that can participate in current Delivery operation."""

    OUTCOME = "outcome"
    PUBLICATION = "publication"


class PortfolioGuidanceKind(StrEnum):
    """Advisory operator choices derived from current portfolio facts."""

    RESUME_DESIGN = "resume-design"
    START_ORCHESTRATION = "start-orchestration"
    WORK_UNDERWAY = "work-underway"
    INTERVENE = "intervene"
    WAIT = "wait"
    CREATE_CHANGE = "create-change"


class PortfolioChangeAdmission(StrEnum):
    """Persisted admission state for one current Change."""

    ADMITTED = "admitted"
    UNADMITTED = "unadmitted"


class _OperatingModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class PortfolioWorkReference(_OperatingModel):
    """One scope-qualified current work identity."""

    change_id: str = Field(min_length=1)
    item_key: str = Field(min_length=1)
    scope: PortfolioWorkScope


class PortfolioGuidance(_OperatingModel):
    """One portfolio-level recommendation with its factual targets."""

    kind: PortfolioGuidanceKind
    change_ids: tuple[str, ...] = ()
    work_count: int = Field(default=0, ge=0)


class PortfolioGuidanceFacts(_OperatingModel):
    """Facts used to derive concurrent portfolio guidance."""

    unfinished_change_count: int = Field(ge=0)
    design_change_ids: tuple[str, ...] = ()
    claimed: tuple[PortfolioWorkReference, ...] = ()
    queued: tuple[PortfolioWorkReference, ...] = ()
    interventions: tuple[PortfolioWorkReference, ...] = ()
    dependency_waits: tuple[PortfolioWorkReference, ...] = ()


class PortfolioChangeLifecycleStatus(_OperatingModel):
    """Explicit lifecycle facts for one current Change."""

    change_id: str = Field(min_length=1)
    admission: PortfolioChangeAdmission
    stage: DeliveryChangeStage | None = None
    actionable_runtime: bool
    diagnostic_code: str | None = Field(default=None, min_length=1)
    diagnostic_detail: str | None = Field(default=None, min_length=1, max_length=240)

    @property
    def admitted(self) -> bool:
        """Return whether persisted admission evidence exists."""
        return self.admission is PortfolioChangeAdmission.ADMITTED


class DeliveryHealthStatus(StrEnum):
    """Overall availability of the current Delivery application."""

    HEALTHY = "healthy"
    ATTENTION = "attention"


class DeliveryHealthDiagnostic(_OperatingModel):
    """Bounded diagnostic for state excluded from Delivery authority."""

    source: str = Field(min_length=1)
    code: str = Field(min_length=1)
    detail: str = Field(min_length=1, max_length=240)
    change_id: str | None = Field(default=None, min_length=1)
    path: str | None = Field(default=None, min_length=1)
    retry_safe: bool = False


class DeliveryHealthView(_OperatingModel):
    """Current Delivery availability and bounded state diagnostics."""

    status: DeliveryHealthStatus
    diagnostics: tuple[DeliveryHealthDiagnostic, ...] = Field(default=(), max_length=64)


class PortfolioOperatingView(_OperatingModel):
    """Current operating facts and derived guidance for the whole portfolio.

    The status projection excludes normally completed Changes; completion totals retain them.
    """

    unfinished_change_count: int = Field(ge=0)
    completed_change_count: int = Field(ge=0)
    statuses: tuple[PortfolioChangeLifecycleStatus, ...] = ()
    draft_design_change_ids: tuple[str, ...] = ()
    design_required_change_ids: tuple[str, ...] = ()
    claimed: tuple[PortfolioWorkReference, ...] = ()
    queued_for_orchestration: tuple[PortfolioWorkReference, ...] = ()
    interventions: tuple[PortfolioWorkReference, ...] = ()
    dependency_waits: tuple[PortfolioWorkReference, ...] = ()
    guidance: tuple[PortfolioGuidance, ...] = ()


def derive_portfolio_guidance(facts: PortfolioGuidanceFacts) -> tuple[PortfolioGuidance, ...]:
    """Derive concurrent operator choices without treating orchestration as Change-scoped."""
    guidance = []
    if facts.interventions:
        guidance.append(
            PortfolioGuidance(
                kind=PortfolioGuidanceKind.INTERVENE,
                change_ids=_change_ids(facts.interventions),
                work_count=len(facts.interventions),
            )
        )
    if facts.design_change_ids:
        guidance.append(
            PortfolioGuidance(
                kind=PortfolioGuidanceKind.RESUME_DESIGN,
                change_ids=facts.design_change_ids,
                work_count=len(facts.design_change_ids),
            )
        )
    if facts.claimed:
        guidance.append(
            PortfolioGuidance(
                kind=PortfolioGuidanceKind.WORK_UNDERWAY,
                change_ids=_change_ids(facts.claimed),
                work_count=len(facts.claimed),
            )
        )
    elif facts.queued:
        guidance.append(
            PortfolioGuidance(
                kind=PortfolioGuidanceKind.START_ORCHESTRATION,
                change_ids=_change_ids(facts.queued),
                work_count=len(facts.queued),
            )
        )
    elif facts.dependency_waits:
        guidance.append(
            PortfolioGuidance(
                kind=PortfolioGuidanceKind.WAIT,
                change_ids=_change_ids(facts.dependency_waits),
                work_count=len(facts.dependency_waits),
            )
        )
    if facts.unfinished_change_count == 0 and not facts.design_change_ids:
        guidance.append(PortfolioGuidance(kind=PortfolioGuidanceKind.CREATE_CHANGE))
    return tuple(guidance)


def _change_ids(references: tuple[PortfolioWorkReference, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(reference.change_id for reference in references))
