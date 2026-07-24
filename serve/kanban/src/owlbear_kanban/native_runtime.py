"""Transport-free native job lifecycle operations."""

from __future__ import annotations

from datetime import datetime, timedelta
from enum import StrEnum
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from owlbear_kanban.attempts import AttemptEvent, AttemptStore
from owlbear_kanban.jobs import JobDisposition, JobStore, StoredJob, project_job
from owlbear_kanban.receipt import ReceiptStore, ReceiptValidityCode, RepositoryHistory
from owlbear_kanban.runtime_transaction import RuntimeTransaction, TransactionConflictError

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    from owlbear_kanban.change import ChangeRevision

_RECOVERY_EVENT_SEQUENCE = 2


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


class ReleaseJobDiagnosticCode(StrEnum):
    NO_ACTIVE_CLAIM = "ERR_RELEASE_NO_ACTIVE_CLAIM"
    NON_OWNER = "ERR_RELEASE_NON_OWNER"


class ReleaseJobRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    job_id: int
    attempt_id: str
    claim_id: str
    actor_id: str
    process_id: str
    released_at: str


class ReleaseJobDiagnostic(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    code: ReleaseJobDiagnosticCode
    detail: str


class ReleaseJobResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    job: StoredJob | None = None
    event: AttemptEvent | None = None
    diagnostic: ReleaseJobDiagnostic | None = None

    @model_validator(mode="after")
    def _require_one_outcome(self) -> ReleaseJobResult:
        if self.diagnostic is None and self.job is not None and self.event is not None:
            return self
        if self.diagnostic is not None and self.job is None and self.event is None:
            return self
        msg = "release result must contain a job/event pair or one diagnostic"
        raise ValueError(msg)


class FailJobDiagnosticCode(StrEnum):
    NO_ACTIVE_CLAIM = "ERR_FAIL_NO_ACTIVE_CLAIM"
    NON_OWNER = "ERR_FAIL_NON_OWNER"


class FailJobRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    job_id: int
    attempt_id: str
    claim_id: str
    actor_id: str
    process_id: str
    failed_at: str
    detail: str
    evidence_ids: tuple[str, ...]


class FailJobDiagnostic(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    code: FailJobDiagnosticCode
    detail: str


class FailJobResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    job: StoredJob | None = None
    event: AttemptEvent | None = None
    diagnostic: FailJobDiagnostic | None = None

    @model_validator(mode="after")
    def _require_one_outcome(self) -> FailJobResult:
        if self.diagnostic is None and self.job is not None and self.event is not None:
            return self
        if self.diagnostic is not None and self.job is None and self.event is None:
            return self
        msg = "failure result must contain a job/event pair or one diagnostic"
        raise ValueError(msg)


class RecoveryDiagnosticCode(StrEnum):
    IDENTITY_INVALID = "ERR_RECOVERY_IDENTITY_INVALID"
    CONFLICT = "ERR_RECOVERY_CONFLICT"


def _aware_datetime(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        msg = "timestamp must be valid ISO 8601"
        raise ValueError(msg) from exc
    if parsed.utcoffset() is None:
        msg = "timestamp must include a timezone"
        raise ValueError(msg)
    return parsed


class RecoverExpiredClaimsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    recovered_at: str
    actor_id: str
    process_id: str

    @field_validator("recovered_at")
    @classmethod
    def _validate_recovered_at(cls, value: str) -> str:
        _aware_datetime(value)
        return value


class RecoveredClaim(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    job: StoredJob
    event: AttemptEvent


class RecoveryDiagnostic(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    job_id: int
    code: RecoveryDiagnosticCode
    detail: str


class RecoverExpiredClaimsResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    recovered: tuple[RecoveredClaim, ...] = ()
    diagnostics: tuple[RecoveryDiagnostic, ...] = ()


class NativeRuntime:
    """Assemble native stores behind the public job-start mutation boundary."""

    def __init__(
        self,
        revision: ChangeRevision,
        work_root: Path,
        history: RepositoryHistory,
        claim_expiry: timedelta,
    ) -> None:
        if claim_expiry <= timedelta(0):
            msg = "claim expiry must be positive"
            raise ValueError(msg)
        self._revision = revision
        self._work_root = work_root
        self._history = history
        self._claim_expiry = claim_expiry
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

    def release_job(self, request: ReleaseJobRequest) -> ReleaseJobResult:
        result = self._finalize(
            request,
            kind="released",
            timestamp=request.released_at,
            detail=None,
            evidence_ids=(),
        )
        if isinstance(result, tuple):
            return ReleaseJobResult(job=result[0], event=result[1])
        return ReleaseJobResult(
            diagnostic=ReleaseJobDiagnostic(
                code=ReleaseJobDiagnosticCode(result), detail="claim is not owned by the requesting attempt"
            )
        )

    def fail_job(self, request: FailJobRequest) -> FailJobResult:
        result = self._finalize(
            request,
            kind="failed",
            timestamp=request.failed_at,
            detail=request.detail,
            evidence_ids=request.evidence_ids,
        )
        if isinstance(result, tuple):
            return FailJobResult(job=result[0], event=result[1])
        return FailJobResult(
            diagnostic=FailJobDiagnostic(
                code=FailJobDiagnosticCode(result), detail="claim is not owned by the requesting attempt"
            )
        )

    def recover_expired_claims(self, request: RecoverExpiredClaimsRequest) -> RecoverExpiredClaimsResult:
        RuntimeTransaction.recover_all(self._work_root)
        events = {(event.attempt_id, event.sequence): event for event in self._attempts.list()}
        recovered_at = _aware_datetime(request.recovered_at)
        recovered: list[RecoveredClaim] = []
        diagnostics: list[RecoveryDiagnostic] = []
        for stored in self._jobs.list():
            job = stored.job
            if job.claim_id is None and job.attempt_id is None:
                replay = self._recovered_replay(stored, request, events.values())
                if replay is not None:
                    recovered.append(replay)
                continue
            if job.claim_id is None or job.attempt_id is None:
                diagnostics.append(self._recovery_identity_diagnostic(job.job_id))
                continue
            started = events.get((job.attempt_id, 1))
            if not self._valid_started_identity(stored, started):
                diagnostics.append(self._recovery_identity_diagnostic(job.job_id))
                continue
            assert started is not None
            try:
                claimed_at = _aware_datetime(started.timestamp)
            except ValueError:
                diagnostics.append(self._recovery_identity_diagnostic(job.job_id))
                continue
            if recovered_at <= claimed_at + self._claim_expiry:
                continue
            outcome = self._commit_recovery(stored, started, request)
            if outcome is None:
                diagnostics.append(
                    RecoveryDiagnostic(
                        job_id=job.job_id,
                        code=RecoveryDiagnosticCode.CONFLICT,
                        detail="recovery transaction conflicts with persisted state",
                    )
                )
            else:
                recovered.append(outcome)
        return RecoverExpiredClaimsResult(recovered=tuple(recovered), diagnostics=tuple(diagnostics))

    @staticmethod
    def _recovery_identity_diagnostic(job_id: int) -> RecoveryDiagnostic:
        return RecoveryDiagnostic(
            job_id=job_id,
            code=RecoveryDiagnosticCode.IDENTITY_INVALID,
            detail="active claim identity is inconsistent",
        )

    @staticmethod
    def _valid_started_identity(stored: StoredJob, started: AttemptEvent | None) -> bool:
        job = stored.job
        return bool(
            started is not None
            and started.kind == "started"
            and started.job_id == job.job_id
            and started.attempt_id == job.attempt_id
            and started.claim_id == job.claim_id
        )

    @staticmethod
    def _recovered_replay(
        stored: StoredJob,
        request: RecoverExpiredClaimsRequest,
        events: Iterable[AttemptEvent],
    ) -> RecoveredClaim | None:
        if stored.job.updated_at != request.recovered_at:
            return None
        current_events = tuple(
            event for event in events if event.job_id == stored.job.job_id and event.timestamp == stored.job.updated_at
        )
        if len(current_events) != 1:
            return None
        event = current_events[0]
        if (
            event.sequence == _RECOVERY_EVENT_SEQUENCE
            and event.kind == "crashed"
            and event.actor_id == request.actor_id
            and event.process_id == request.process_id
            and event.detail == "claim expired"
            and not event.evidence_ids
        ):
            return RecoveredClaim(job=stored, event=event)
        return None

    def _commit_recovery(
        self,
        stored: StoredJob,
        started: AttemptEvent,
        request: RecoverExpiredClaimsRequest,
    ) -> RecoveredClaim | None:
        job = stored.job
        replacement = job.model_copy(update={"claim_id": None, "attempt_id": None, "updated_at": request.recovered_at})
        event = AttemptEvent(
            schema_version=1,
            attempt_id=started.attempt_id,
            claim_id=started.claim_id,
            job_id=job.job_id,
            change_id=job.change_id,
            delivery_digest=job.delivery_digest,
            target_node_id=job.target_node_id,
            actor_id=request.actor_id,
            process_id=request.process_id,
            sequence=_RECOVERY_EVENT_SEQUENCE,
            timestamp=request.recovered_at,
            kind="crashed",
            detail="claim expired",
        )
        try:
            RuntimeTransaction(
                self._work_root,
                f"recover-{job.job_id}-{started.attempt_id}",
                (
                    self._jobs.replacement_participant(replacement, stored.token),
                    self._attempts.create_participant(event),
                ),
            ).commit()
        except TransactionConflictError:
            return None
        return RecoveredClaim(job=self._jobs.read(job.job_id), event=event)

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
            claim_id=request.claim_id,
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

    def _finalize(
        self,
        request: ReleaseJobRequest | FailJobRequest,
        *,
        kind: str,
        timestamp: str,
        detail: str | None,
        evidence_ids: tuple[str, ...],
    ) -> tuple[StoredJob, AttemptEvent] | str:
        stored = self._jobs.read(request.job_id)
        completed = self._attempts.read(request.attempt_id, 2).event
        if completed is not None and completed.job_id == request.job_id:
            if (
                completed.kind == kind
                and completed.claim_id == request.claim_id
                and completed.actor_id == request.actor_id
                and completed.process_id == request.process_id
                and completed.timestamp == timestamp
                and completed.detail == detail
                and completed.evidence_ids == evidence_ids
            ):
                return stored, completed
            return "ERR_RELEASE_NON_OWNER" if kind == "released" else "ERR_FAIL_NON_OWNER"
        job = stored.job
        if job.claim_id is None and job.attempt_id is None:
            return "ERR_RELEASE_NO_ACTIVE_CLAIM" if kind == "released" else "ERR_FAIL_NO_ACTIVE_CLAIM"
        if job.claim_id != request.claim_id or job.attempt_id != request.attempt_id:
            return "ERR_RELEASE_NON_OWNER" if kind == "released" else "ERR_FAIL_NON_OWNER"
        started = self._attempts.read(request.attempt_id, 1).event
        if (
            started is None
            or started.claim_id != request.claim_id
            or started.actor_id != request.actor_id
            or started.process_id != request.process_id
        ):
            return "ERR_RELEASE_NON_OWNER" if kind == "released" else "ERR_FAIL_NON_OWNER"
        replacement = job.model_copy(update={"claim_id": None, "attempt_id": None, "updated_at": timestamp})
        event = AttemptEvent(
            schema_version=1,
            attempt_id=request.attempt_id,
            claim_id=request.claim_id,
            job_id=job.job_id,
            change_id=job.change_id,
            delivery_digest=job.delivery_digest,
            target_node_id=job.target_node_id,
            actor_id=request.actor_id,
            process_id=request.process_id,
            sequence=2,
            timestamp=timestamp,
            kind=kind,
            detail=detail,
            evidence_ids=evidence_ids,
        )
        RuntimeTransaction(
            self._work_root,
            f"{kind}-{request.attempt_id}",
            (self._jobs.replacement_participant(replacement, stored.token), self._attempts.create_participant(event)),
        ).commit()
        return self._jobs.read(request.job_id), event


__all__ = [
    "FailJobDiagnostic",
    "FailJobDiagnosticCode",
    "FailJobRequest",
    "FailJobResult",
    "NativeRuntime",
    "RecoverExpiredClaimsRequest",
    "RecoverExpiredClaimsResult",
    "RecoveredClaim",
    "RecoveryDiagnostic",
    "RecoveryDiagnosticCode",
    "ReleaseJobDiagnostic",
    "ReleaseJobDiagnosticCode",
    "ReleaseJobRequest",
    "ReleaseJobResult",
    "StartJobDiagnostic",
    "StartJobDiagnosticCode",
    "StartJobRequest",
    "StartJobResult",
]
