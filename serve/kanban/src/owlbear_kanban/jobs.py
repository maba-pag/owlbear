"""Side-effect-free planning and serialization of initial shape jobs."""

from __future__ import annotations

import contextlib
import hashlib
import os
import stat
from enum import StrEnum
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator

from owlbear_kanban.change import ChangeRevision, Digest
from owlbear_kanban.runtime_transaction import ReplacementTransactionParticipant
from owlbear_kanban.storage_io import locked_roots
from owlbear_kanban.yaml_rt import make_yaml

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping, Sequence


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


class JobDisposition(StrEnum):
    PENDING = "pending"
    CANCELLED = "cancelled"
    SUPERSEDED = "superseded"


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
    disposition: JobDisposition = JobDisposition.PENDING

    @field_validator("disposition", mode="before")
    @classmethod
    def _parse_disposition(cls, value: object) -> object:
        return JobDisposition(value) if isinstance(value, str) else value


class StoredJob(BaseModel):
    """One persisted job record with its immutable OCC token."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    job: JobRecord
    token: str


class JobConflictError(FileExistsError):
    """Raised when materialization would replace a different job record."""

    code = "ERR_JOB_CONFLICT"

    def __init__(self, job_id: int) -> None:
        super().__init__(f"job already exists with different content: {job_id}")
        self.job_id = job_id


class JobConcurrencyError(RuntimeError):
    """Raised when an operational write uses an outdated OCC token."""

    code = "ERR_JOB_OCC_STALE"

    def __init__(self, job_id: int) -> None:
        super().__init__(f"job OCC token is stale: {job_id}")
        self.job_id = job_id


_DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
_FILE_FLAGS = os.O_RDONLY | os.O_NOFOLLOW
_CREATE_FLAGS = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW


def _job_filename(job_id: int) -> str:
    if job_id <= 0:
        msg = "job ID must be positive"
        raise ValueError(msg)
    return f"{job_id}.yaml"


def _serialized_job(record: JobRecord) -> str:
    stream = StringIO()
    make_yaml(explicit_start=True).dump(record.model_dump(mode="json"), stream)
    return stream.getvalue()


def _stored_job(text: str, job_id: int) -> StoredJob:
    value = make_yaml().load(text)
    if not isinstance(value, dict):
        msg = "job document must be a mapping"
        raise TypeError(msg)
    normalized = dict(value)
    for field in ("predecessor_job_ids", "pending_request_ids", "evidence_ids"):
        if isinstance(normalized.get(field), list):
            normalized[field] = tuple(normalized[field])
    record = JobRecord.model_validate(normalized)
    if record.job_id != job_id:
        msg = "job filename and record identities differ"
        raise ValueError(msg)
    return StoredJob(job=record, token=hashlib.sha256(text.encode("utf-8")).hexdigest())


class JobStore:
    """Contained active/archive job storage rooted at an explicit work directory."""

    def __init__(self, work_root: Path) -> None:
        self._work_root = work_root

    @contextlib.contextmanager
    def _root(self) -> Iterator[int]:
        try:
            root_fd = os.open(self._work_root, _DIRECTORY_FLAGS)
        except OSError as exc:
            msg = "work root could not be opened safely"
            raise ValueError(msg) from exc
        try:
            yield root_fd
        finally:
            os.close(root_fd)

    @staticmethod
    def _directory(root_fd: int, name: str, *, create: bool) -> int | None:
        if create:
            with contextlib.suppress(FileExistsError):
                os.mkdir(name, mode=0o755, dir_fd=root_fd)
        try:
            return os.open(name, _DIRECTORY_FLAGS, dir_fd=root_fd)
        except FileNotFoundError:
            return None
        except OSError as exc:
            msg = f"job {name} directory could not be opened safely"
            raise ValueError(msg) from exc

    @contextlib.contextmanager
    def _locked_root(self) -> Iterator[int]:
        with locked_roots((self._work_root,)), self._root() as root_fd:
            yield root_fd

    @staticmethod
    def _read(directory_fd: int, job_id: int) -> tuple[StoredJob, str]:
        filename = _job_filename(job_id)
        file_fd = os.open(filename, _FILE_FLAGS, dir_fd=directory_fd)
        try:
            if not stat.S_ISREG(os.fstat(file_fd).st_mode):
                msg = "job path must identify a regular file"
                raise ValueError(msg)
            with os.fdopen(os.dup(file_fd), "r", encoding="utf-8") as handle:
                text = handle.read()
        finally:
            os.close(file_fd)
        return _stored_job(text, job_id), text

    @staticmethod
    def _create(directory_fd: int, record: JobRecord) -> None:
        filename = _job_filename(record.job_id)
        content = _serialized_job(record)
        file_fd = os.open(filename, _CREATE_FLAGS, 0o644, dir_fd=directory_fd)
        try:
            with os.fdopen(os.dup(file_fd), "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.fsync(directory_fd)
        finally:
            os.close(file_fd)

    @staticmethod
    def _replace(directory_fd: int, record: JobRecord) -> None:
        filename = _job_filename(record.job_id)
        temporary = f".tmp-{filename}-{os.urandom(8).hex()}"
        content = _serialized_job(record)
        file_fd = os.open(temporary, _CREATE_FLAGS, 0o644, dir_fd=directory_fd)
        try:
            with os.fdopen(os.dup(file_fd), "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, filename, src_dir_fd=directory_fd, dst_dir_fd=directory_fd)
            os.fsync(directory_fd)
        finally:
            with contextlib.suppress(FileNotFoundError):
                os.unlink(temporary, dir_fd=directory_fd)
            os.close(file_fd)

    def materialize(self, generation: JobGeneration) -> tuple[StoredJob, ...]:
        """Create accepted generation jobs idempotently without overwriting records."""
        with self._locked_root() as root_fd:
            directory_fd = self._directory(root_fd, "jobs", create=True)
            assert directory_fd is not None
            try:
                records = tuple(JobRecord(schema_version=1, **shape_job.model_dump()) for shape_job in generation.jobs)
                for record in records:
                    try:
                        stored, _text = self._read(directory_fd, record.job_id)
                    except FileNotFoundError:
                        continue
                    if stored.job != record:
                        raise JobConflictError(record.job_id)
                materialized: list[StoredJob] = []
                for record in records:
                    try:
                        stored, _text = self._read(directory_fd, record.job_id)
                    except FileNotFoundError:
                        self._create(directory_fd, record)
                        stored, _text = self._read(directory_fd, record.job_id)
                    materialized.append(stored)
                return tuple(materialized)
            finally:
                os.close(directory_fd)

    def read(self, job_id: int, *, archived: bool = False) -> StoredJob:
        """Read one active or archived job and its current OCC token."""
        with self._root() as root_fd:
            directory_fd = self._directory(root_fd, "archive" if archived else "jobs", create=False)
            if directory_fd is None:
                raise FileNotFoundError(_job_filename(job_id))
            try:
                return self._read(directory_fd, job_id)[0]
            finally:
                os.close(directory_fd)

    def list(self, *, archived: bool = False) -> tuple[StoredJob, ...]:
        """List active or archived jobs in ascending numeric job-ID order."""
        with self._root() as root_fd:
            directory_fd = self._directory(root_fd, "archive" if archived else "jobs", create=False)
            if directory_fd is None:
                return ()
            try:
                job_ids = sorted(
                    int(name.removesuffix(".yaml"))
                    for name in os.listdir(directory_fd)  # noqa: PTH208 - requires pinned descriptor.
                    if name.endswith(".yaml") and name.removesuffix(".yaml").isdigit()
                )
                return tuple(self._read(directory_fd, job_id)[0] for job_id in job_ids)
            finally:
                os.close(directory_fd)

    def update(self, record: JobRecord, expected_token: str) -> StoredJob:
        """Replace one active record when its supplied OCC token is current."""
        with self._locked_root() as root_fd:
            directory_fd = self._directory(root_fd, "jobs", create=False)
            if directory_fd is None:
                raise FileNotFoundError(_job_filename(record.job_id))
            try:
                current, _text = self._read(directory_fd, record.job_id)
                if current.token != expected_token:
                    raise JobConcurrencyError(record.job_id)
                self._replace(directory_fd, record)
                return self._read(directory_fd, record.job_id)[0]
            finally:
                os.close(directory_fd)

    def replacement_participant(self, replacement: JobRecord, expected_token: str) -> ReplacementTransactionParticipant:
        """Plan a non-mutating OCC-guarded replacement transaction participant."""
        with self._locked_root() as root_fd:
            directory_fd = self._directory(root_fd, "jobs", create=False)
            if directory_fd is None:
                raise FileNotFoundError(_job_filename(replacement.job_id))
            try:
                current, current_text = self._read(directory_fd, replacement.job_id)
                if current.token != expected_token:
                    raise JobConcurrencyError(replacement.job_id)
                return ReplacementTransactionParticipant(
                    self._work_root,
                    Path("jobs") / _job_filename(replacement.job_id),
                    current_text.encode("utf-8"),
                    _serialized_job(replacement).encode("utf-8"),
                )
            finally:
                os.close(directory_fd)

    def archive(self, job_id: int, expected_token: str) -> StoredJob:
        """Move one active job into archive when its supplied OCC token is current."""
        with self._locked_root() as root_fd:
            active_fd = self._directory(root_fd, "jobs", create=False)
            archive_fd = self._directory(root_fd, "archive", create=True)
            if active_fd is None:
                raise FileNotFoundError(_job_filename(job_id))
            assert archive_fd is not None
            try:
                current, _text = self._read(active_fd, job_id)
                if current.token != expected_token:
                    raise JobConcurrencyError(job_id)
                filename = _job_filename(job_id)
                try:
                    os.link(filename, filename, src_dir_fd=active_fd, dst_dir_fd=archive_fd, follow_symlinks=False)
                except FileExistsError as exc:
                    raise JobConflictError(job_id) from exc
                os.unlink(filename, dir_fd=active_fd)
                os.fsync(active_fd)
                os.fsync(archive_fd)
                return self._read(archive_fd, job_id)[0]
            finally:
                os.close(active_fd)
                os.close(archive_fd)


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
    "JobConcurrencyError",
    "JobConflictError",
    "JobDiagnostic",
    "JobDiagnosticCode",
    "JobDisposition",
    "JobGeneration",
    "JobParseResult",
    "JobProjection",
    "JobRecord",
    "JobStore",
    "ShapeJob",
    "StoredJob",
    "parse_job_mapping",
    "plan_shape_jobs",
    "project_job",
    "read_job_generation",
]
