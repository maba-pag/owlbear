"""Side-effect-free planning and serialization of initial shape jobs."""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING, Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from owlbear_kanban.change import ChangeRevision, Digest

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence


class JobDiagnosticCode(StrEnum):
    DUPLICATE_ID = "ERR_JOB_ID_DUPLICATE"
    DUPLICATE_TARGET = "ERR_JOB_TARGET_DUPLICATE"
    MISSING_TARGET = "ERR_JOB_TARGET_MISSING"
    WRONG_KIND = "ERR_JOB_KIND_INVALID"
    DIGEST_MISMATCH = "ERR_JOB_DIGEST_MISMATCH"
    RECEIPT_MISMATCH = "ERR_JOB_RECEIPT_MISMATCH"
    UNKNOWN_TARGET = "ERR_JOB_TARGET_UNKNOWN"
    UNKNOWN_FIELD = "ERR_JOB_FIELD_UNKNOWN"
    SCHEMA_INVALID = "ERR_JOB_SCHEMA_INVALID"


class JobDiagnostic(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    code: JobDiagnosticCode
    detail: str
    target: str | None = None


class ShapeJob(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    job_id: int = Field(gt=0)
    kind: Literal["shape"]
    priority: int
    created_at: str
    updated_at: str
    change_id: str
    delivery_digest: Digest
    target_node_id: str
    receipt_id: str


JobKind = Literal["shape", "build", "accept", "audit", "supersession"]
DeliveryNodeId = Annotated[str, StringConstraints(strict=True, pattern=r"^DN-[0-9]{3}$")]


class JobRecord(BaseModel):
    """Immutable operational job identity and references."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal[1]
    job_id: int = Field(gt=0)
    kind: JobKind
    priority: int
    created_at: str
    updated_at: str
    change_id: str
    delivery_digest: Digest
    target_node_id: DeliveryNodeId
    node_plan_digest: Digest | None = None
    predecessor_job_ids: tuple[int, ...] = ()
    claim_id: str | None = None
    block_id: str | None = None
    pending_request_ids: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    attempt_id: str | None = None
    finding_id: str | None = None
    receipt_id: str | None = None
    superseded_by_receipt_id: str | None = None
    disposition: str = "pending"


class JobProjection(BaseModel):
    """Authoritative delivery context assembled for an operational job."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    title: str
    outcome: str
    acceptance: tuple[str, ...]
    modules: tuple[str, ...]
    interfaces: tuple[str, ...]
    proof: str


class JobParseResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    job: JobRecord | None = None
    diagnostics: tuple[JobDiagnostic, ...] = ()

    @model_validator(mode="after")
    def _require_one_outcome(self) -> JobParseResult:
        if (self.job is None) == (not self.diagnostics):
            detail = "job result must contain either one job or diagnostics"
            raise ValueError(detail)
        return self


def parse_job_mapping(value: Mapping[str, object]) -> JobParseResult:
    """Parse a schema-version-1 native job mapping with stable diagnostics."""
    normalized = dict(value)
    for field in ("predecessor_job_ids", "pending_request_ids", "evidence_ids"):
        if isinstance(normalized.get(field), list):
            normalized[field] = tuple(normalized[field])
    try:
        job = JobRecord.model_validate(normalized)
    except ValueError as exc:
        message = str(exc)
        code = JobDiagnosticCode.SCHEMA_INVALID
        if "kind" in message:
            code = JobDiagnosticCode.WRONG_KIND
        elif "target_node_id" in message:
            code = JobDiagnosticCode.UNKNOWN_TARGET
        elif "Extra inputs" in message:
            code = JobDiagnosticCode.UNKNOWN_FIELD
        return JobParseResult(diagnostics=(JobDiagnostic(code=code, detail=message),))
    return JobParseResult(job=job)


def project_job(
    job: JobRecord,
    revision: ChangeRevision,
    node_plan: Mapping[str, object] | None = None,
) -> JobProjection:
    """Resolve normative job context from the authoritative revision and plan."""
    if job.change_id != revision.change_id or job.delivery_digest != revision.delivery_digest:
        raise ValueError(JobDiagnosticCode.DIGEST_MISMATCH.value)
    node = next((item for item in revision.graph.nodes if item.id == job.target_node_id), None)
    if node is None:
        raise ValueError(JobDiagnosticCode.UNKNOWN_TARGET.value)
    requirements = {item.id: item.statement for item in revision.graph.requirements}
    plan = node_plan or {}
    acceptance_value = plan.get("acceptance", tuple(requirements[item] for item in node.owns if item in requirements))
    acceptance = tuple(acceptance_value) if isinstance(acceptance_value, (list, tuple)) else (str(acceptance_value),)
    return JobProjection(
        title=node.title,
        outcome=node.outcome,
        acceptance=acceptance,
        modules=node.modules,
        interfaces=tuple(
            interface.name
            for interface in revision.graph.interfaces
            if interface.id in node.produces or interface.id in node.consumes
        ),
        proof=node.proof,
    )


class JobGeneration(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal[1]
    change_id: str
    delivery_digest: Digest
    receipt_id: str
    jobs: tuple[ShapeJob, ...]

    @model_validator(mode="after")
    def _unique_jobs(self) -> JobGeneration:
        ids = [job.job_id for job in self.jobs]
        targets = [job.target_node_id for job in self.jobs]
        if len(ids) != len(set(ids)):
            raise ValueError(JobDiagnosticCode.DUPLICATE_ID.value)
        if len(targets) != len(set(targets)):
            raise ValueError(JobDiagnosticCode.DUPLICATE_TARGET.value)
        return self


def plan_shape_jobs(
    revision: ChangeRevision,
    receipt_id: str,
    job_ids: Sequence[int],
    *,
    priority: int = 0,
    timestamp: str,
) -> JobGeneration:
    """Plan one immutable shape job for every authored delivery node."""
    nodes = revision.graph.nodes
    if len(job_ids) != len(nodes):
        raise ValueError(JobDiagnosticCode.MISSING_TARGET.value)
    jobs = tuple(
        ShapeJob(
            job_id=job_id,
            kind="shape",
            priority=priority,
            created_at=timestamp,
            updated_at=timestamp,
            change_id=revision.change_id,
            delivery_digest=revision.delivery_digest,
            target_node_id=node.id,
            receipt_id=receipt_id,
        )
        for job_id, node in zip(job_ids, nodes, strict=True)
    )
    return JobGeneration(
        schema_version=1,
        change_id=revision.change_id,
        delivery_digest=revision.delivery_digest,
        receipt_id=receipt_id,
        jobs=jobs,
    )


def read_job_generation(
    value: Mapping[str, object], revision: ChangeRevision
) -> tuple[JobGeneration | None, tuple[JobDiagnostic, ...]]:
    """Validate a serialized generation against its authoritative revision."""
    normalized = dict(value)
    if isinstance(normalized.get("jobs"), list):
        normalized["jobs"] = tuple(normalized["jobs"])
    try:
        generation = JobGeneration.model_validate(normalized)
    except ValueError as exc:
        message = str(exc)
        code = next((item for item in JobDiagnosticCode if item.value in message), JobDiagnosticCode.WRONG_KIND)
        return None, (JobDiagnostic(code=code, detail=message),)
    diagnostics: list[JobDiagnostic] = []
    if generation.change_id != revision.change_id:
        diagnostics.append(
            JobDiagnostic(
                code=JobDiagnosticCode.UNKNOWN_TARGET,
                detail="generation change does not match revision",
            )
        )
    if generation.delivery_digest != revision.delivery_digest:
        diagnostics.append(
            JobDiagnostic(
                code=JobDiagnosticCode.DIGEST_MISMATCH,
                detail="generation digest does not match revision",
            )
        )
    node_ids = tuple(node.id for node in revision.graph.nodes)
    targets = tuple(job.target_node_id for job in generation.jobs)
    diagnostics.extend(
        JobDiagnostic(
            code=JobDiagnosticCode.UNKNOWN_TARGET,
            detail="job target is outside revision",
            target=target,
        )
        for target in targets
        if target not in node_ids
    )
    if set(targets) != set(node_ids):
        diagnostics.append(
            JobDiagnostic(
                code=JobDiagnosticCode.MISSING_TARGET,
                detail="generation does not cover every authored node",
            )
        )
    if generation.receipt_id and any(job.receipt_id != generation.receipt_id for job in generation.jobs):
        diagnostics.append(
            JobDiagnostic(
                code=JobDiagnosticCode.RECEIPT_MISMATCH,
                detail="job receipt does not match generation",
            )
        )
    if any(job.delivery_digest != revision.delivery_digest for job in generation.jobs):
        diagnostics.append(
            JobDiagnostic(
                code=JobDiagnosticCode.DIGEST_MISMATCH,
                detail="job digest does not match revision",
            )
        )
    return (generation if not diagnostics else None), tuple(diagnostics)


__all__ = [
    "JobDiagnostic",
    "JobDiagnosticCode",
    "JobGeneration",
    "JobParseResult",
    "JobProjection",
    "JobRecord",
    "ShapeJob",
    "parse_job_mapping",
    "plan_shape_jobs",
    "project_job",
    "read_job_generation",
]
