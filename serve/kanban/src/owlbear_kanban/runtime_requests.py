"""Revision-scoped decision and action request operations."""

from __future__ import annotations

from enum import StrEnum
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator

from owlbear_kanban.change import ChangeRevision, Digest
from owlbear_kanban.jobs import JobStore, StoredJob, project_job
from owlbear_kanban.runtime_transaction import (
    ReplacementTransactionParticipant,
    RuntimeTransaction,
    TransactionConflictError,
    TransactionParticipant,
)
from owlbear_kanban.yaml_rt import make_yaml

if TYPE_CHECKING:
    from collections.abc import Callable

RequestId = Annotated[str, StringConstraints(strict=True, pattern=r"^[a-z0-9][a-z0-9-]{0,126}[a-z0-9]$")]
RequestKind = Literal["decision", "action"]
RequestDisposition = Literal["local", "material"]
_MIN_DECISION_OPTIONS = 2


class RequestConflictError(RuntimeError):
    """A request identity already names different immutable content."""

    code = "ERR_NATIVE_REQUEST_CONFLICT"


class RequestReferenceError(ValueError):
    """A request references authority or work outside its revision."""

    code = "ERR_NATIVE_REQUEST_REFERENCE"


class RequestNotFoundError(FileNotFoundError):
    """A native request does not exist."""

    code = "ERR_NATIVE_REQUEST_NOT_FOUND"


class RequestOption(BaseModel):
    """One immutable decision option with its complete trade-off record."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    option_id: RequestId
    label: str
    pros: tuple[str, ...]
    cons: tuple[str, ...]
    risks: tuple[str, ...]
    recommended: bool
    confidence: float = Field(ge=0.0, le=1.0, allow_inf_nan=False)
    rationale: str


class NativeRequest(BaseModel):
    """One immutable request attached to a native change revision."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal[1] = 1
    request_id: RequestId
    kind: RequestKind
    title: str
    summary: str
    body: str
    agent: str
    created_at: str
    change_id: str
    delivery_digest: Digest
    target_node_id: str | None = None
    job_ids: tuple[int, ...] = ()
    options: tuple[RequestOption, ...] = ()
    evidence: tuple[str, ...] = ()
    resume_condition: str | None = None

    @field_validator("job_ids")
    @classmethod
    def _unique_job_ids(cls, value: tuple[int, ...]) -> tuple[int, ...]:
        if any(job_id <= 0 for job_id in value) or len(set(value)) != len(value):
            msg = "job references must be unique positive IDs"
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def _validate_kind_payload(self) -> NativeRequest:
        if self.kind == "decision":
            if len(self.options) < _MIN_DECISION_OPTIONS or self.evidence or self.resume_condition is not None:
                msg = "decision requests need options and no action payload"
                raise ValueError(msg)
            if sum(option.recommended for option in self.options) > 1:
                msg = "at most one decision option may be recommended"
                raise ValueError(msg)
        elif self.options or not self.evidence or not self.resume_condition:
            msg = "action requests need exact evidence and a resume condition"
            raise ValueError(msg)
        return self


class RequestResolution(BaseModel):
    """One immutable local or material resolution."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal[1] = 1
    request_id: RequestId
    disposition: RequestDisposition
    resolved_at: str
    resolved_by: str
    selected_option_id: RequestId | None = None
    response: str | None = None
    rationale: str

    @model_validator(mode="after")
    def _require_response(self) -> RequestResolution:
        if self.selected_option_id is None and not self.response:
            msg = "a resolution needs a selected option or response"
            raise ValueError(msg)
        return self


class StoredRequest(BaseModel):
    """A request projection with optional immutable resolution."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    request: NativeRequest
    resolution: RequestResolution | None = None


class RequestResumeIntent(BaseModel):
    """Local invalidation intent for the linked dependent slice."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    disposition: Literal["resume-linked-jobs"] = "resume-linked-jobs"
    request_id: RequestId
    target_node_id: str | None
    job_ids: tuple[int, ...]


class DesignReentryDisposition(BaseModel):
    """Material authority resolution routed back to the current revision."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    disposition: Literal["design-reentry"] = "design-reentry"
    request_id: RequestId
    change_id: str
    delivery_digest: Digest
    target_node_id: str | None
    job_ids: tuple[int, ...]


class ResolveRequestResult(BaseModel):
    """Resolved request plus exactly one resulting disposition."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    request: StoredRequest
    resumed_jobs: tuple[StoredJob, ...] = ()
    resume: RequestResumeIntent | None = None
    design_reentry: DesignReentryDisposition | None = None

    @model_validator(mode="after")
    def _require_one_disposition(self) -> ResolveRequestResult:
        if (self.resume is None) == (self.design_reentry is None):
            msg = "resolution result needs exactly one disposition"
            raise ValueError(msg)
        return self


class RequestStatus(StrEnum):
    """Enumerate lifecycle states for native runtime requests."""

    PENDING = "pending"
    RESOLVED = "resolved"


class NativeRequestRuntime:
    """Coordinate immutable request records and linked job state."""

    def __init__(self, revision: ChangeRevision, work_root: Path) -> None:
        self._revision = revision
        self._work_root = work_root
        self._jobs = JobStore(work_root)

    def create_request(
        self,
        request: NativeRequest,
        *,
        failure: Callable[[str], None] | None = None,
    ) -> StoredRequest:
        """Create or exactly replay one request and all linked job blocks."""
        self._recover()
        linked = self._validate_references(request)
        existing = self._read_optional(request.request_id)
        if existing is not None and existing.request != request:
            raise RequestConflictError
        if existing is not None and existing.resolution is not None:
            return existing
        participants: list[TransactionParticipant | ReplacementTransactionParticipant] = [
            TransactionParticipant(
                self._work_root,
                self._pending_path(request.request_id),
                _serialize(request),
            )
        ]
        for stored in linked:
            pending = stored.job.pending_request_ids
            pending_request_ids = pending if request.request_id in pending else (*pending, request.request_id)
            replacement = stored.job.model_copy(update={"pending_request_ids": pending_request_ids})
            participants.append(self._jobs.replacement_participant(replacement, stored.token))
        try:
            RuntimeTransaction(
                self._work_root,
                f"request-create-{request.request_id}",
                tuple(participants),
            ).commit(failure=failure)
        except TransactionConflictError as exc:
            replay = self._read_optional(request.request_id)
            if (
                replay is not None
                and replay.request == request
                and all(
                    request.request_id in self._jobs.read(job_id).job.pending_request_ids for job_id in request.job_ids
                )
            ):
                return replay
            raise RequestConflictError from exc
        return self.show_request(request.request_id)

    def show_request(self, request_id: RequestId) -> StoredRequest:
        """Read one request and its resolution status."""
        self._recover()
        stored = self._read_optional(request_id)
        if stored is None:
            raise RequestNotFoundError(request_id)
        return stored

    def list_requests(self, status: RequestStatus | None = None) -> tuple[StoredRequest, ...]:
        """List requests in stable identity order with an optional status filter."""
        self._recover()
        directory = self._work_root / "requests" / "pending"
        if not directory.is_dir():
            return ()
        records = tuple(self.show_request(path.stem) for path in sorted(directory.glob("*.yaml")))
        if status is None:
            return records
        resolved = status is RequestStatus.RESOLVED
        return tuple(record for record in records if (record.resolution is not None) is resolved)

    def resolve_request(
        self,
        resolution: RequestResolution,
        *,
        failure: Callable[[str], None] | None = None,
    ) -> ResolveRequestResult:
        """Resolve once, resuming local links or returning material design re-entry."""
        self._recover()
        current = self.show_request(resolution.request_id)
        if current.resolution is not None:
            if current.resolution != resolution:
                raise RequestConflictError
            return self._resolution_result(current)
        request = current.request
        self._validate_resolution(request, resolution)
        linked = self._validate_references(request)
        participants: list[TransactionParticipant | ReplacementTransactionParticipant] = [
            TransactionParticipant(
                self._work_root,
                self._resolved_path(request.request_id),
                _serialize(resolution),
            )
        ]
        if resolution.disposition == "local":
            for stored in linked:
                replacement = stored.job.model_copy(
                    update={
                        "pending_request_ids": tuple(
                            request_id
                            for request_id in stored.job.pending_request_ids
                            if request_id != request.request_id
                        )
                    }
                )
                participants.append(self._jobs.replacement_participant(replacement, stored.token))
        try:
            RuntimeTransaction(
                self._work_root,
                f"request-resolve-{request.request_id}",
                tuple(participants),
            ).commit(failure=failure)
        except TransactionConflictError as exc:
            replay = self._read_optional(request.request_id)
            if replay is not None and replay.resolution == resolution:
                return self._resolution_result(replay)
            raise RequestConflictError from exc
        return self._resolution_result(self.show_request(request.request_id))

    def _recover(self) -> None:
        RuntimeTransaction.recover_all(self._work_root)

    def _read_optional(self, request_id: str) -> StoredRequest | None:
        pending = self._work_root / self._pending_path(request_id)
        if not pending.is_file():
            return None
        request = NativeRequest.model_validate(_load(pending))
        resolved = self._work_root / self._resolved_path(request_id)
        resolution = RequestResolution.model_validate(_load(resolved)) if resolved.is_file() else None
        return StoredRequest(request=request, resolution=resolution)

    def _validate_references(self, request: NativeRequest) -> tuple[StoredJob, ...]:
        if request.change_id != self._revision.change_id or request.delivery_digest != self._revision.delivery_digest:
            raise RequestReferenceError
        node_ids = {node.id for node in self._revision.graph.nodes}
        if request.target_node_id is not None and request.target_node_id not in node_ids:
            raise RequestReferenceError
        linked: list[StoredJob] = []
        for job_id in request.job_ids:
            try:
                stored = self._jobs.read(job_id)
                project_job(stored.job, self._revision)
            except (FileNotFoundError, ValueError) as exc:
                raise RequestReferenceError from exc
            if request.target_node_id is not None and stored.job.target_node_id != request.target_node_id:
                raise RequestReferenceError
            linked.append(stored)
        return tuple(linked)

    @staticmethod
    def _validate_resolution(request: NativeRequest, resolution: RequestResolution) -> None:
        if resolution.selected_option_id is None:
            return
        if request.kind != "decision" or resolution.selected_option_id not in {
            option.option_id for option in request.options
        }:
            raise RequestReferenceError

    def _resolution_result(self, stored: StoredRequest) -> ResolveRequestResult:
        resolution = stored.resolution
        assert resolution is not None
        request = stored.request
        if resolution.disposition == "material":
            return ResolveRequestResult(
                request=stored,
                design_reentry=DesignReentryDisposition(
                    request_id=request.request_id,
                    change_id=request.change_id,
                    delivery_digest=request.delivery_digest,
                    target_node_id=request.target_node_id,
                    job_ids=request.job_ids,
                ),
            )
        jobs = tuple(self._jobs.read(job_id) for job_id in request.job_ids)
        return ResolveRequestResult(
            request=stored,
            resumed_jobs=jobs,
            resume=RequestResumeIntent(
                request_id=request.request_id,
                target_node_id=request.target_node_id,
                job_ids=request.job_ids,
            ),
        )

    @staticmethod
    def _pending_path(request_id: str) -> Path:
        return Path("requests") / "pending" / f"{request_id}.yaml"

    @staticmethod
    def _resolved_path(request_id: str) -> Path:
        return Path("requests") / "resolved" / f"{request_id}.yaml"


def _serialize(model: BaseModel) -> bytes:
    stream = StringIO()
    make_yaml(explicit_start=True).dump(model.model_dump(mode="json"), stream)
    return stream.getvalue().encode("utf-8")


def _load(path: Path) -> object:
    text = path.read_text(encoding="utf-8")
    value = make_yaml().load(text)
    if not isinstance(value, dict):
        msg = "request document must be a mapping"
        raise TypeError(msg)
    for field in ("job_ids", "options", "evidence", "pros", "cons", "risks"):
        if isinstance(value.get(field), list):
            value[field] = tuple(value[field])
    if isinstance(value.get("options"), tuple):
        value["options"] = tuple(
            {
                **option,
                **{
                    field: tuple(option[field])
                    for field in ("pros", "cons", "risks")
                    if isinstance(option.get(field), list)
                },
            }
            for option in value["options"]
        )
    return value


__all__ = [
    "DesignReentryDisposition",
    "NativeRequest",
    "NativeRequestRuntime",
    "RequestConflictError",
    "RequestNotFoundError",
    "RequestOption",
    "RequestReferenceError",
    "RequestResolution",
    "RequestResumeIntent",
    "RequestStatus",
    "ResolveRequestResult",
    "StoredRequest",
]
