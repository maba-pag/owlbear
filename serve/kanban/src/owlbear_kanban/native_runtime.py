"""Transport-free native job lifecycle operations."""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, model_validator

from owlbear_kanban.attempts import AttemptEvent, AttemptStore
from owlbear_kanban.jobs import JobDisposition, JobStore, StoredJob, project_job
from owlbear_kanban.receipt import ReceiptStore, ReceiptValidityCode, RepositoryHistory
from owlbear_kanban.runtime_transaction import RuntimeTransaction

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear_kanban.change import ChangeRevision


class StartJobDiagnosticCode(StrEnum):
    AUTHORITY_STALE = "ERR_START_AUTHORITY_STALE"
    PREDECESSOR_INVALID = "ERR_START_PREDECESSOR_INVALID"
    REQUEST_PENDING = "ERR_START_REQUEST_PENDING"
    TERMINAL = "ERR_START_TERMINAL"
    ACTIVE_CLAIM = "ERR_START_ACTIVE_CLAIM"
    IDENTITY_CONFLICT = "ERR_START_IDENTITY_CONFLICT"


class StartJobRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    job_id: int
    attempt_id: str
    claim_id: str
    actor_id: str
    process_id: str
    claimed_at: str
    candidate_revision: str


class StartJobDiagnostic(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    code: StartJobDiagnosticCode
    detail: str
    lower_code: str | None = None
    target: str | None = None


class StartJobResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    job: StoredJob | None = None
    event: AttemptEvent | None = None
    diagnostic: StartJobDiagnostic | None = None

    @model_validator(mode="after")
    def _require_one_outcome(self) -> StartJobResult:
        if self.diagnostic is None and self.job is not None and self.event is not None:
            return self
        if self.diagnostic is not None and self.job is None and self.event is None:
            return self
        msg = "start result must contain a job/event pair or one diagnostic"
        raise ValueError(msg)


class NativeRuntime:
    """Assemble native stores behind the public job-start mutation boundary."""

    def __init__(self, revision: ChangeRevision, work_root: Path, history: RepositoryHistory) -> None:
        self._revision = revision
        self._work_root = work_root
        self._history = history
        self._jobs = JobStore(work_root)
        self._attempts = AttemptStore(work_root)
        self._receipts = ReceiptStore(revision)

    @staticmethod
    def _diagnostic(
        code: StartJobDiagnosticCode,
        detail: str,
        *,
        lower_code: str | None = None,
        target: str | None = None,
    ) -> StartJobResult:
        return StartJobResult(
            diagnostic=StartJobDiagnostic(code=code, detail=detail, lower_code=lower_code, target=target)
        )

    def start_job(self, request: StartJobRequest) -> StartJobResult:
        stored = self._authoritative_job(request)
        if isinstance(stored, StartJobResult):
            return stored
        for check in (self._predecessor_check, self._readiness_check, self._active_claim_check):
            diagnostic = check(stored, request)
            if diagnostic is not None:
                return diagnostic
        return self._commit_start(stored, request)

    def _authoritative_job(self, request: StartJobRequest) -> StoredJob | StartJobResult:
        try:
            stored = self._jobs.read(request.job_id)
            project_job(stored.job, self._revision)
        except (FileNotFoundError, ValueError):
            return self._diagnostic(
                StartJobDiagnosticCode.AUTHORITY_STALE,
                "job authority does not match the loaded revision",
                target=str(request.job_id),
            )
        return stored

    def _predecessor_check(self, stored: StoredJob, request: StartJobRequest) -> StartJobResult | None:
        for predecessor_id in stored.job.predecessor_job_ids:
            try:
                predecessor = self._jobs.read(predecessor_id).job
            except FileNotFoundError:
                return self._diagnostic(
                    StartJobDiagnosticCode.PREDECESSOR_INVALID,
                    "predecessor job is missing",
                    target=str(predecessor_id),
                )
            if predecessor.receipt_id is None:
                return self._diagnostic(
                    StartJobDiagnosticCode.PREDECESSOR_INVALID,
                    "predecessor receipt ID is missing",
                    target=str(predecessor_id),
                )
            validity = self._receipts.evaluate_currentness(
                predecessor.receipt_id, self._history, request.candidate_revision
            )
            if validity.code is not ReceiptValidityCode.CURRENT:
                return self._diagnostic(
                    StartJobDiagnosticCode.PREDECESSOR_INVALID,
                    "predecessor receipt is not current",
                    lower_code=validity.code.value,
                    target=validity.target or predecessor.receipt_id,
                )
        return None

    def _readiness_check(self, stored: StoredJob, _request: StartJobRequest) -> StartJobResult | None:
        job = stored.job
        if job.pending_request_ids:
            return self._diagnostic(
                StartJobDiagnosticCode.REQUEST_PENDING,
                "job has pending requests",
                target=job.pending_request_ids[0],
            )
        if job.disposition is not JobDisposition.PENDING:
            return self._diagnostic(
                StartJobDiagnosticCode.TERMINAL,
                "job has a terminal disposition",
                target=job.disposition.value,
            )
        return None

    def _active_claim_check(self, stored: StoredJob, request: StartJobRequest) -> StartJobResult | None:
        job = stored.job
        if job.claim_id is None and job.attempt_id is None:
            return None
        if job.claim_id != request.claim_id or job.attempt_id != request.attempt_id:
            return self._diagnostic(StartJobDiagnosticCode.ACTIVE_CLAIM, "job already has an active claim")
        existing = self._attempts.read(request.attempt_id, 1).event
        if existing is None:
            return self._diagnostic(StartJobDiagnosticCode.ACTIVE_CLAIM, "active attempt event is unavailable")
        if (
            existing.actor_id != request.actor_id
            or existing.process_id != request.process_id
            or existing.timestamp != request.claimed_at
        ):
            return self._diagnostic(
                StartJobDiagnosticCode.IDENTITY_CONFLICT,
                "active claim identity differs from the request",
            )
        return StartJobResult(job=stored, event=existing)

    def _commit_start(self, stored: StoredJob, request: StartJobRequest) -> StartJobResult:
        job = stored.job
        replacement = job.model_copy(
            update={"claim_id": request.claim_id, "attempt_id": request.attempt_id, "updated_at": request.claimed_at}
        )
        event = AttemptEvent(
            schema_version=1,
            attempt_id=request.attempt_id,
            job_id=job.job_id,
            change_id=job.change_id,
            delivery_digest=job.delivery_digest,
            target_node_id=job.target_node_id,
            actor_id=request.actor_id,
            process_id=request.process_id,
            sequence=1,
            timestamp=request.claimed_at,
            kind="started",
        )
        RuntimeTransaction(
            self._work_root,
            f"start-{request.attempt_id}",
            (self._jobs.replacement_participant(replacement, stored.token), self._attempts.create_participant(event)),
        ).commit()
        return StartJobResult(job=self._jobs.read(request.job_id), event=event)


__all__ = [
    "NativeRuntime",
    "StartJobDiagnostic",
    "StartJobDiagnosticCode",
    "StartJobRequest",
    "StartJobResult",
]
