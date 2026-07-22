"""Side-effect-free planning and serialization of initial shape jobs."""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

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


__all__ = ["JobDiagnostic", "JobDiagnosticCode", "JobGeneration", "ShapeJob", "plan_shape_jobs", "read_job_generation"]
