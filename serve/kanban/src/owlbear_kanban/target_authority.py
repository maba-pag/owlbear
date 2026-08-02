"""Semantic authority for the target delivery runtime."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from owlbear_kanban.identities import ChangeId

AuthorityId = Annotated[str, StringConstraints(strict=True, pattern=r"^[A-Z]+-[0-9]{3}$")]


class CommitmentClass(StrEnum):
    """Provenance-based semantic commitment strength."""

    DEALBREAKER = "dealbreaker"
    PROTECTED_REQUEST = "protected-request"
    IMPORTANT_REVIEWED = "important-reviewed"
    AGREED_PATH = "agreed-path"
    IMPLEMENTATION_DISCRETION = "implementation-discretion"


class AuthorityStatus(StrEnum):
    """Lifecycle of one immutable semantic identity."""

    ACTIVE = "active"
    SUPERSEDED = "superseded"
    DROPPED = "dropped"


class PlanScopeKind(StrEnum):
    """Semantic parent accepted task planning may refine."""

    OUTCOME = "outcome"
    CHANGE_ASSEMBLY = "change-assembly"


class _AuthorityModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class Commitment(_AuthorityModel):
    """One provenance-preserving semantic commitment."""

    commitment_id: AuthorityId
    commitment_class: CommitmentClass
    provenance: str = Field(min_length=1)
    statement: str = Field(min_length=1)
    status: AuthorityStatus = AuthorityStatus.ACTIVE
    superseded_by: tuple[AuthorityId, ...] = ()

    @model_validator(mode="after")
    def _validate_supersession(self) -> Commitment:
        if self.status == AuthorityStatus.SUPERSEDED and not self.superseded_by:
            msg = "superseded commitments require replacement identities"
            raise ValueError(msg)
        if self.status != AuthorityStatus.SUPERSEDED and self.superseded_by:
            msg = "only superseded commitments may name replacements"
            raise ValueError(msg)
        if self.commitment_id in self.superseded_by:
            msg = "commitments cannot supersede themselves"
            raise ValueError(msg)
        return self


class Outcome(_AuthorityModel):
    """One immutable user-facing result identity."""

    outcome_id: AuthorityId
    title: str = Field(min_length=1)
    promise: str = Field(min_length=1)
    acceptance: tuple[str, ...] = Field(min_length=1)
    commitment_ids: tuple[AuthorityId, ...] = ()
    dependency_ids: tuple[AuthorityId, ...] = ()
    status: AuthorityStatus = AuthorityStatus.ACTIVE
    superseded_by: tuple[AuthorityId, ...] = ()

    @model_validator(mode="after")
    def _validate_supersession(self) -> Outcome:
        if self.status == AuthorityStatus.SUPERSEDED and not self.superseded_by:
            msg = "superseded outcomes require replacement identities"
            raise ValueError(msg)
        if self.status != AuthorityStatus.SUPERSEDED and self.superseded_by:
            msg = "only superseded outcomes may name replacements"
            raise ValueError(msg)
        if self.outcome_id in self.superseded_by:
            msg = "outcomes cannot supersede themselves"
            raise ValueError(msg)
        return self


class TaskPlanScope(_AuthorityModel):
    """Accepted authority for tasks under one semantic scope."""

    scope_id: AuthorityId
    kind: PlanScopeKind
    target_id: str = Field(min_length=1)
    composition_claim: str | None = None

    @model_validator(mode="after")
    def _validate_change_assembly(self) -> TaskPlanScope:
        if self.kind == PlanScopeKind.CHANGE_ASSEMBLY and not self.composition_claim:
            msg = "change assembly scopes require a composition claim"
            raise ValueError(msg)
        return self


class DesignReentryBriefing(_AuthorityModel):
    """Persist the semantic context required to resume collaborative Design."""

    work_item_id: str = Field(min_length=1)
    failed_claim: str = Field(min_length=1)
    affected_commitment_ids: tuple[AuthorityId, ...] = Field(min_length=1)
    evidence: tuple[str, ...] = Field(min_length=1)
    blocked_work_item_ids: tuple[str, ...] = ()
    continuing_work_item_ids: tuple[str, ...] = ()
    resume_condition: str = Field(min_length=1)


class SemanticUpdate(_AuthorityModel):
    """One non-blocking revision to agent-owned direction."""

    update_id: AuthorityId
    work_item_id: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    changed_commitment_ids: tuple[AuthorityId, ...] = ()


class CompletionSummary(_AuthorityModel):
    """Commitment-level result shown when one work item closes."""

    work_item_id: str = Field(min_length=1)
    satisfied_commitment_ids: tuple[AuthorityId, ...] = ()
    accepted_deviations: tuple[str, ...] = ()
    known_limits: tuple[str, ...] = ()


class TargetAuthority(_AuthorityModel):
    """One admitted semantic revision consumed by target projections."""

    schema_version: Literal[1] = 1
    change_id: ChangeId
    title: str = Field(min_length=1)
    commitments: tuple[Commitment, ...] = ()
    outcomes: tuple[Outcome, ...] = ()
    task_plan_scopes: tuple[TaskPlanScope, ...] = ()
    design_reentries: tuple[DesignReentryBriefing, ...] = ()
    semantic_updates: tuple[SemanticUpdate, ...] = ()
    completion_summaries: tuple[CompletionSummary, ...] = ()

    @model_validator(mode="after")
    def _validate_references(self) -> TargetAuthority:
        commitments = _unique(self.commitments, "commitment_id", "commitment")
        outcomes = _unique(self.outcomes, "outcome_id", "outcome")
        _unique(self.task_plan_scopes, "scope_id", "task plan scope")
        _unique(self.semantic_updates, "update_id", "semantic update")
        work_item_ids = {self.change_id, *outcomes}

        for commitment in self.commitments:
            _require_references(commitment.superseded_by, commitments, "commitment replacement")
        for outcome in self.outcomes:
            _require_references(outcome.commitment_ids, commitments, "outcome commitment")
            _require_references(outcome.dependency_ids, outcomes, "outcome dependency")
            _require_references(outcome.superseded_by, outcomes, "outcome replacement")
        for scope in self.task_plan_scopes:
            if scope.kind == PlanScopeKind.OUTCOME and scope.target_id not in outcomes:
                msg = f"task plan outcome is missing: {scope.target_id}"
                raise ValueError(msg)
            if scope.kind == PlanScopeKind.CHANGE_ASSEMBLY and scope.target_id != self.change_id:
                msg = "change assembly scope must target its change"
                raise ValueError(msg)
        for briefing in self.design_reentries:
            _require_work_item(briefing.work_item_id, work_item_ids)
            _require_references(briefing.affected_commitment_ids, commitments, "briefing commitment")
            _require_references(briefing.blocked_work_item_ids, work_item_ids, "blocked work item")
            _require_references(briefing.continuing_work_item_ids, work_item_ids, "continuing work item")
        for update in self.semantic_updates:
            _require_work_item(update.work_item_id, work_item_ids)
            _require_references(update.changed_commitment_ids, commitments, "updated commitment")
        for summary in self.completion_summaries:
            _require_work_item(summary.work_item_id, work_item_ids)
            _require_references(summary.satisfied_commitment_ids, commitments, "satisfied commitment")
        return self


def _unique(items: tuple[BaseModel, ...], field: str, label: str) -> set[str]:
    identities = [str(getattr(item, field)) for item in items]
    if len(identities) != len(set(identities)):
        msg = f"{label} identities must be unique"
        raise ValueError(msg)
    return set(identities)


def _require_references(references: tuple[str, ...], available: set[str], label: str) -> None:
    missing = sorted(set(references) - available)
    if missing:
        msg = f"{label} is missing: {', '.join(missing)}"
        raise ValueError(msg)


def _require_work_item(work_item_id: str, available: set[str]) -> None:
    if work_item_id not in available:
        msg = f"work item is missing: {work_item_id}"
        raise ValueError(msg)
