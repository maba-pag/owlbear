"""Transport-free native job lifecycle operations."""

from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import datetime, timedelta
from enum import StrEnum
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from owlbear_kanban.attempts import AttemptEvent, AttemptStore
from owlbear_kanban.change import load_change
from owlbear_kanban.invalidation import InvalidationRequest, InvalidationResult, InvalidationRuntime
from owlbear_kanban.jobs import JobDisposition, JobRecord, JobStore, StoredJob, project_job
from owlbear_kanban.node_plan import NodePlanStore
from owlbear_kanban.receipt import (
    ImpactClosure,
    ReceiptRecord,
    ReceiptStore,
    ReceiptValidity,
    ReceiptValidityCode,
    RepositoryHistory,
    compute_node_plan_digest,
    evaluate_code_revision_currency,
    evaluate_receipt_currentness,
    parse_impact_closure,
)
from owlbear_kanban.runtime_query import (
    RuntimeHistoryEntry,
    RuntimeJobProjection,
    RuntimePage,
    RuntimeQuery,
    WorkHealthResult,
)
from owlbear_kanban.runtime_transaction import (
    ReplacementTransactionParticipant,
    RuntimeTransaction,
    TransactionConflictError,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable
    from pathlib import Path

    from owlbear_kanban.change import ChangeRevision
    from owlbear_kanban.finding import Finding
    from owlbear_kanban.proof_checkout import ProofCheckoutManager
    from owlbear_kanban.runtime_requests import StoredRequest

_RECOVERY_EVENT_SEQUENCE = 2
_PACKET_ID = re.compile(r"^(DN-[0-9]{3})-PK-[0-9]{3}$")
_STABLE_ID = re.compile(r"^(?:REQ|NEG|KEEP|DEC|WF|MOD|IF|MIG|RISK|PROOF|DN)-[0-9]{3}$")


class StartJobDiagnosticCode(StrEnum):
    """Enumerate stable failures that prevent a native job claim."""

    AUTHORITY_STALE = "ERR_START_AUTHORITY_STALE"
    PREDECESSOR_INVALID = "ERR_START_PREDECESSOR_INVALID"
    REQUEST_PENDING = "ERR_START_REQUEST_PENDING"
    TERMINAL = "ERR_START_TERMINAL"
    ACTIVE_CLAIM = "ERR_START_ACTIVE_CLAIM"
    IDENTITY_CONFLICT = "ERR_START_IDENTITY_CONFLICT"


class StartJobRequest(BaseModel):
    """Identify an actor's attempt to claim one job against a code revision."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    job_id: int
    attempt_id: str
    claim_id: str
    actor_id: str
    process_id: str
    claimed_at: str
    candidate_revision: str


class StartJobDiagnostic(BaseModel):
    """Describe why a native job claim was rejected."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    code: StartJobDiagnosticCode
    detail: str
    lower_code: str | None = None
    target: str | None = None


class StartJobResult(BaseModel):
    """Contain either a claimed job and start event or one diagnostic."""

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
    """Enumerate stable failures that prevent releasing a job claim."""

    NO_ACTIVE_CLAIM = "ERR_RELEASE_NO_ACTIVE_CLAIM"
    NON_OWNER = "ERR_RELEASE_NON_OWNER"


class ReleaseJobRequest(BaseModel):
    """Identify an actor's request to release one active job claim."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    job_id: int
    attempt_id: str
    claim_id: str
    actor_id: str
    process_id: str
    released_at: str


class ReleaseJobDiagnostic(BaseModel):
    """Describe why an active job claim could not be released."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    code: ReleaseJobDiagnosticCode
    detail: str


class ReleaseJobResult(BaseModel):
    """Contain either a released job and event or one diagnostic."""

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
    """Enumerate stable failures that prevent recording a failed attempt."""

    NO_ACTIVE_CLAIM = "ERR_FAIL_NO_ACTIVE_CLAIM"
    NON_OWNER = "ERR_FAIL_NON_OWNER"


class FailJobRequest(BaseModel):
    """Provide the owned claim, failure detail, and evidence for a failed attempt."""

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
    """Describe why a failed attempt could not be recorded."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    code: FailJobDiagnosticCode
    detail: str


class FailJobResult(BaseModel):
    """Contain either a failed job and event or one diagnostic."""

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


class FinishJobDiagnosticCode(StrEnum):
    """Enumerate stable failures that prevent completing a native job."""

    AUTHORITY_STALE = "ERR_FINISH_AUTHORITY_STALE"
    PREDECESSOR_INVALID = "ERR_FINISH_PREDECESSOR_INVALID"
    WRONG_KIND = "ERR_FINISH_KIND_INVALID"
    NO_ACTIVE_CLAIM = "ERR_FINISH_NO_ACTIVE_CLAIM"
    NON_OWNER = "ERR_FINISH_NON_OWNER"
    EVIDENCE_INVALID = "ERR_FINISH_EVIDENCE_INVALID"
    NODE_PLAN_INVALID = "ERR_FINISH_NODE_PLAN_INVALID"
    IDENTITY_CONFLICT = "ERR_FINISH_IDENTITY_CONFLICT"


class FinishJobRequest(BaseModel):
    """Provide claim identity, evidence, and receipt authority for job completion."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    job_id: int
    attempt_id: str
    claim_id: str
    actor_id: str
    process_id: str
    finished_at: str
    receipt_id: str
    code_revision: str
    evidence: dict[str, object]
    evidence_ids: tuple[str, ...] = ()
    impact_closure: ImpactClosure | None = None


class FinishPlanRequest(FinishJobRequest):
    """Extend job completion with a node plan and downstream job identities."""

    node_plan: dict[str, object]
    build_job_ids: tuple[int, ...]
    accept_job_id: int


class FinishAcceptRequest(FinishJobRequest):
    """Extend acceptance completion with dependent reconciliation-plan identities."""

    reconciliation_plan_job_ids: tuple[int, ...]


class FinishJobDiagnostic(BaseModel):
    """Describe why a native job could not be completed."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    code: FinishJobDiagnosticCode
    detail: str
    lower_code: str | None = None
    target: str | None = None


class FinishJobResult(BaseModel):
    """Contain a completed job, receipt, event, and derived jobs or one diagnostic."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    job: StoredJob | None = None
    receipt: ReceiptRecord | None = None
    event: AttemptEvent | None = None
    created_jobs: tuple[JobRecord, ...] = ()
    diagnostic: FinishJobDiagnostic | None = None

    @model_validator(mode="after")
    def _require_one_outcome(self) -> FinishJobResult:
        complete = self.job is not None and self.receipt is not None and self.event is not None
        if (self.diagnostic is None and complete) or (
            self.diagnostic is not None
            and self.job is None
            and self.receipt is None
            and self.event is None
            and not self.created_jobs
        ):
            return self
        msg = "finish result must contain a job/receipt/event outcome or one diagnostic"
        raise ValueError(msg)


class RecoveryDiagnosticCode(StrEnum):
    """Enumerate stable expired-claim recovery failures."""

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
    """Identify the actor and timestamp for an expired-claim recovery pass."""

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
    """Pair a recovered job with its generated crash event."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    job: StoredJob
    event: AttemptEvent


class RecoveryDiagnostic(BaseModel):
    """Describe why one job claim could not be recovered."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    job_id: int
    code: RecoveryDiagnosticCode
    detail: str


class RecoverExpiredClaimsResult(BaseModel):
    """Collect recovered claims and per-job recovery diagnostics."""

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
        proof_checkouts: ProofCheckoutManager | None = None,
    ) -> None:
        if claim_expiry <= timedelta(0):
            msg = "claim expiry must be positive"
            raise ValueError(msg)
        self._revision = revision
        self._work_root = work_root
        self._history = history
        self._claim_expiry = claim_expiry
        self._proof_checkouts = proof_checkouts
        self._jobs = JobStore(work_root)
        self._attempts = AttemptStore(work_root)
        self._receipts = ReceiptStore(revision)
        self._invalidation = InvalidationRuntime(revision, work_root)
        self._query = RuntimeQuery(revision, work_root, history, proof_checkouts)
        RuntimeTransaction.recover_all(work_root, roots=(work_root, revision.source_dir))

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
        """Claim an eligible job and append its immutable start event."""
        return self._start_job(request)

    def _start_job(
        self,
        request: StartJobRequest,
        participants: tuple[ReplacementTransactionParticipant, ...] = (),
    ) -> StartJobResult:
        stored = self._authoritative_job(request)
        if isinstance(stored, StartJobResult):
            return stored
        for check in (self._predecessor_check, self._readiness_check, self._active_claim_check):
            diagnostic = check(stored, request)
            if diagnostic is not None:
                return diagnostic
        result = self._commit_start(stored, request, participants)
        self._query.reset()
        return result

    def list_jobs(
        self,
        *,
        candidate_revision: str,
        cursor: str | None = None,
        limit: int = 100,
    ) -> RuntimePage[RuntimeJobProjection]:
        """Return one bounded page of indexed job projections."""
        return self._query.list_jobs(candidate_revision=candidate_revision, cursor=cursor, limit=limit)

    def list_attempts(self, *, cursor: str | None = None, limit: int = 100) -> RuntimePage[AttemptEvent]:
        """Return one bounded page of attempt history."""
        return self._query.list_attempts(cursor=cursor, limit=limit)

    def list_findings(self, *, cursor: str | None = None, limit: int = 100) -> RuntimePage[Finding]:
        """Return one bounded page of corrective findings."""
        return self._query.list_findings(cursor=cursor, limit=limit)

    def list_receipts(self, *, cursor: str | None = None, limit: int = 100) -> RuntimePage[ReceiptRecord]:
        """Return one bounded page of immutable receipts."""
        return self._query.list_receipts(cursor=cursor, limit=limit)

    def list_requests(self, *, cursor: str | None = None, limit: int = 100) -> RuntimePage[StoredRequest]:
        """Return one bounded page of native requests."""
        return self._query.list_requests(cursor=cursor, limit=limit)

    def list_history(self, *, cursor: str | None = None, limit: int = 100) -> RuntimePage[RuntimeHistoryEntry]:
        """Return one bounded page across immutable runtime history."""
        return self._query.list_history(cursor=cursor, limit=limit)

    def invalidate(self, request: InvalidationRequest) -> InvalidationResult:
        """Apply invalidation and refresh only its affected index closure."""
        result = self._invalidation.apply(request)
        if result.outcome is not None:
            self._query.refresh_closure(
                (*result.outcome.affected_receipt_ids, result.outcome.supersession_receipt.receipt_id),
                (
                    *result.outcome.affected_job_ids,
                    *(item.job.job_id for item in result.outcome.corrective_jobs),
                ),
            )
        return result

    def work_health(self, *, cursor: str | None = None, limit: int = 100) -> WorkHealthResult:
        """Return bounded stable work findings without mutation."""
        return self._query.work_health(cursor=cursor, limit=limit)

    def release_job(self, request: ReleaseJobRequest) -> ReleaseJobResult:
        """Release an owned job claim and append its release event."""
        return self._release_job(request)

    def _release_job(
        self,
        request: ReleaseJobRequest,
        participants: tuple[ReplacementTransactionParticipant, ...] = (),
    ) -> ReleaseJobResult:
        result = self._finalize(
            request,
            kind="released",
            timestamp=request.released_at,
            detail=None,
            evidence_ids=(),
            participants=participants,
        )
        if isinstance(result, tuple):
            self._query.reset()
            return ReleaseJobResult(job=result[0], event=result[1])
        return ReleaseJobResult(
            diagnostic=ReleaseJobDiagnostic(
                code=ReleaseJobDiagnosticCode(result), detail="claim is not owned by the requesting attempt"
            )
        )

    def fail_job(self, request: FailJobRequest) -> FailJobResult:
        """Record an owned attempt failure and release its job claim."""
        return self._fail_job(request)

    def _fail_job(
        self,
        request: FailJobRequest,
        participants: tuple[ReplacementTransactionParticipant, ...] = (),
    ) -> FailJobResult:
        result = self._finalize(
            request,
            kind="failed",
            timestamp=request.failed_at,
            detail=request.detail,
            evidence_ids=request.evidence_ids,
            participants=participants,
        )
        if isinstance(result, tuple):
            self._query.reset()
            return FailJobResult(job=result[0], event=result[1])
        return FailJobResult(
            diagnostic=FailJobDiagnostic(
                code=FailJobDiagnosticCode(result), detail="claim is not owned by the requesting attempt"
            )
        )

    def finish_plan(self, request: FinishPlanRequest) -> FinishJobResult:
        """Complete plan work and publish its receipt and downstream jobs."""
        result = self._finish(request, "plan")
        if result.diagnostic is None:
            self._query.reset()
        return result

    def finish_build(self, request: FinishJobRequest) -> FinishJobResult:
        """Complete build work and publish its immutable receipt."""
        result = self._finish(request, "build")
        if result.diagnostic is None:
            self._query.reset()
        return result

    def finish_accept(self, request: FinishAcceptRequest) -> FinishJobResult:
        """Complete acceptance work and publish its immutable receipt."""
        result = self._finish(request, "accept", self._accept_participants)
        if result.diagnostic is None:
            self._query.reset()
        return result

    def finish_audit(self, request: FinishJobRequest) -> FinishJobResult:
        """Complete audit work and publish its immutable receipt."""
        result = self._finish(request, "audit")
        if result.diagnostic is None:
            self._query.reset()
        return result

    def recover_expired_claims(self, request: RecoverExpiredClaimsRequest) -> RecoverExpiredClaimsResult:
        """Release expired claims and append deterministic crash events."""
        return self._recover_expired_claims(request, lambda _stored, _started: ())

    def _recover_expired_claims(
        self,
        request: RecoverExpiredClaimsRequest,
        participant_factory: Callable[[StoredJob, AttemptEvent], tuple[ReplacementTransactionParticipant, ...]],
    ) -> RecoverExpiredClaimsResult:
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
            outcome = self._commit_recovery(stored, started, request, participant_factory(stored, started))
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
        if recovered:
            self._query.reset()
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
        participants: tuple[ReplacementTransactionParticipant, ...],
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
                    *participants,
                ),
            ).commit()
        except TransactionConflictError:
            return None
        return RecoveredClaim(job=self._jobs.read(job.job_id), event=event)

    def _authoritative_job(self, request: StartJobRequest) -> StoredJob | StartJobResult:
        try:
            stored = self._jobs.read(request.job_id)
            diagnostic = self._authority_diagnostic(stored.job)
        except FileNotFoundError, ValueError:
            return self._diagnostic(
                StartJobDiagnosticCode.AUTHORITY_STALE,
                "job authority does not match the loaded revision",
                target=str(request.job_id),
            )
        if diagnostic is not None:
            return diagnostic
        return stored

    def _dispatch_eligibility(self, stored: StoredJob, candidate_revision: str) -> str | None:
        """Return the start-gate code that excludes a read-only dispatch candidate."""
        try:
            diagnostic = self._authority_diagnostic(stored.job)
        except ValueError:
            return StartJobDiagnosticCode.AUTHORITY_STALE.value
        if diagnostic is not None:
            return diagnostic.diagnostic.code.value
        request = StartJobRequest(
            job_id=stored.job.job_id,
            attempt_id="dispatch-plan",
            claim_id="dispatch-plan",
            actor_id="dispatch-plan",
            process_id="dispatch-plan",
            claimed_at="1970-01-01T00:00:00Z",
            candidate_revision=candidate_revision,
        )
        for check in (self._predecessor_check, self._readiness_check, self._active_claim_check):
            result = check(stored, request)
            if result is not None:
                if result.diagnostic is None:
                    return StartJobDiagnosticCode.ACTIVE_CLAIM.value
                return result.diagnostic.code.value
        return None

    def _authority_diagnostic(self, job: JobRecord) -> StartJobResult | None:
        project_job(job, self._revision, self._revision.read_node_plan(job.target_node_id))
        if (
            job.kind != "plan"
            and job.node_plan_digest is not None
            and job.node_plan_digest != compute_node_plan_digest(self._revision, job.target_node_id)
        ):
            return self._diagnostic(
                StartJobDiagnosticCode.AUTHORITY_STALE,
                "job node-plan digest differs from current authority",
                lower_code=ReceiptValidityCode.NODE_PLAN_DIGEST_STALE.value,
                target=job.target_node_id,
            )
        return None

    def _predecessor_check(self, stored: StoredJob, request: StartJobRequest) -> StartJobResult | None:
        if stored.job.kind == "build":
            reconciliation = self._reconciliation_predecessors(stored.job.target_node_id, request.candidate_revision)
            if isinstance(reconciliation, StartJobResult):
                return reconciliation
        for predecessor_id in stored.job.predecessor_job_ids:
            try:
                predecessor = self._read_job(predecessor_id).job
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

    def _read_job(self, job_id: int) -> StoredJob:
        try:
            return self._jobs.read(job_id)
        except FileNotFoundError:
            return self._jobs.read(job_id, archived=True)

    @staticmethod
    def _finish_diagnostic(
        code: FinishJobDiagnosticCode,
        detail: str,
        *,
        lower_code: str | None = None,
        target: str | None = None,
    ) -> FinishJobResult:
        return FinishJobResult(
            diagnostic=FinishJobDiagnostic(code=code, detail=detail, lower_code=lower_code, target=target)
        )

    def _finish(  # noqa: C901, PLR0911, PLR0912, PLR0915
        self,
        request: FinishJobRequest,
        kind: str,
        participant_factory: (
            Callable[[StoredJob, FinishJobRequest], tuple[ReplacementTransactionParticipant, ...]] | None
        ) = None,
    ) -> FinishJobResult:
        RuntimeTransaction.recover_all(
            self._work_root,
            roots=(self._work_root, self._revision.source_dir),
        )
        replay = self._finish_replay(request, kind)
        if replay is not None:
            return replay
        try:
            stored = self._jobs.read(request.job_id)
            project_job(
                stored.job,
                self._revision,
                self._revision.read_node_plan(stored.job.target_node_id),
            )
        except FileNotFoundError, ValueError:
            return self._finish_diagnostic(
                FinishJobDiagnosticCode.AUTHORITY_STALE,
                "job authority does not match the loaded revision",
                target=str(request.job_id),
            )
        job = stored.job
        if job.kind != kind:
            return self._finish_diagnostic(
                FinishJobDiagnosticCode.WRONG_KIND,
                "finish operation does not match job purpose",
                target=job.kind,
            )
        ownership = self._finish_ownership(job, request)
        if ownership is not None:
            return ownership
        predecessors = self._finish_predecessors(job, request.code_revision)
        if isinstance(predecessors, FinishJobResult):
            return predecessors

        revision = self._revision
        participants: list[object] = []
        created_jobs: tuple[JobRecord, ...] = ()
        if kind == "plan":
            assert isinstance(request, FinishPlanRequest)
            prepared = self._prepare_plan(stored, request)
            if isinstance(prepared, FinishJobResult):
                return prepared
            revision, graph_participant, created_jobs, closure = prepared
            participants.append(graph_participant)
            participants.extend(self._jobs.create_participant(item) for item in created_jobs)
        else:
            prepared_closure = self._finish_closure(job, request)
            if isinstance(prepared_closure, FinishJobResult):
                return prepared_closure
            closure = prepared_closure
        if participant_factory is not None:
            try:
                participants.extend(participant_factory(stored, request))
            except ValueError as exc:
                return self._finish_diagnostic(FinishJobDiagnosticCode.IDENTITY_CONFLICT, str(exc))

        node_plan_digest = compute_node_plan_digest(
            revision,
            job.target_node_id,
            request.node_plan if isinstance(request, FinishPlanRequest) else None,
        )
        if kind != "plan" and job.node_plan_digest != node_plan_digest:
            return self._finish_diagnostic(
                FinishJobDiagnosticCode.AUTHORITY_STALE,
                "job node-plan digest differs from current authority",
                lower_code=ReceiptValidityCode.NODE_PLAN_DIGEST_STALE.value,
                target=job.target_node_id,
            )
        receipt_value = {
            "schema_version": 1,
            "kind": kind,
            "receipt_id": request.receipt_id,
            "change_id": revision.change_id,
            "delivery_digest": revision.delivery_digest,
            "issued_at": request.finished_at,
            "impact_closure": closure.model_dump(mode="json"),
            "target_node_id": job.target_node_id,
            "node_plan_digest": node_plan_digest,
            "predecessor_receipt_ids": list(predecessors),
            "evidence": request.evidence,
            "code_revision": request.code_revision,
        }
        try:
            receipt = ReceiptRecord.from_mapping(receipt_value)
        except TypeError, ValueError:
            return self._finish_diagnostic(
                FinishJobDiagnosticCode.EVIDENCE_INVALID,
                "receipt evidence is malformed",
                target=request.receipt_id,
            )
        validity = self._new_receipt_validity(
            revision,
            receipt,
            request.code_revision,
            request.node_plan if isinstance(request, FinishPlanRequest) else None,
        )
        if not validity.current:
            return self._finish_diagnostic(
                FinishJobDiagnosticCode.EVIDENCE_INVALID,
                validity.detail,
                lower_code=validity.code.value,
                target=validity.target,
            )
        receipt_store = ReceiptStore(revision)
        receipt, receipt_participant = receipt_store.create_participant(request.receipt_id, receipt_value)
        event = self._success_event(job, request)
        archived = job.model_copy(
            update={
                "claim_id": None,
                "attempt_id": None,
                "receipt_id": request.receipt_id,
                "updated_at": request.finished_at,
            }
        )
        participants.extend(
            (
                receipt_participant,
                self._attempts.create_participant(event),
                self._jobs.archive_participant(archived, stored.token),
            )
        )
        RuntimeTransaction(
            self._work_root,
            f"finish-{request.attempt_id}",
            tuple(participants),  # type: ignore[arg-type]
        ).commit()
        if kind == "plan":
            loaded = load_change(self._revision.source_dir.parent, self._revision.change_id)
            assert loaded.revision is not None
            self._revision = loaded.revision
            self._receipts = ReceiptStore(self._revision)
            self._query = RuntimeQuery(self._revision, self._work_root, self._history, self._proof_checkouts)
        return FinishJobResult(
            job=self._jobs.read(job.job_id, archived=True),
            receipt=receipt,
            event=event,
            created_jobs=created_jobs,
        )

    def _finish_replay(self, request: FinishJobRequest, kind: str) -> FinishJobResult | None:
        try:
            stored = self._jobs.read(request.job_id, archived=True)
        except FileNotFoundError:
            return None
        if stored.job.receipt_id != request.receipt_id:
            return self._finish_diagnostic(
                FinishJobDiagnosticCode.IDENTITY_CONFLICT,
                "archived finish identity differs from the request",
                target=str(request.job_id),
            )
        try:
            event = self._attempts.read(request.attempt_id, 2).event
        except FileNotFoundError:
            return self._finish_diagnostic(
                FinishJobDiagnosticCode.IDENTITY_CONFLICT,
                "archived finish identity differs from the request",
                target=str(request.job_id),
            )
        receipt_result = self._receipts.read(request.receipt_id)
        receipt = receipt_result.receipt
        receipt_payload = receipt.model_dump(mode="json")["payload"] if receipt is not None else {}
        if isinstance(request, FinishPlanRequest):
            validated = self._validate_node_plan(stored.job.target_node_id, request.node_plan)
            prepared_closure = (
                validated if isinstance(validated, FinishJobResult) else self._union_closures(validated[2])
            )
        else:
            prepared_closure = self._finish_closure(stored.job, request)
        closure_matches = (
            receipt is not None
            and not isinstance(prepared_closure, FinishJobResult)
            and receipt.impact_closure == prepared_closure
        )
        shape_identity_matches = True
        if isinstance(request, FinishPlanRequest):
            node_plan = self._revision.read_node_plan(stored.job.target_node_id)
            generated_jobs = tuple(
                item.job
                for item in (*self._jobs.list(), *self._jobs.list(archived=True))
                if item.job.target_node_id == stored.job.target_node_id
                and item.job.node_plan_digest == receipt_payload.get("node_plan_digest")
                and (item.job.kind != "build" or stored.job.job_id in item.job.predecessor_job_ids)
                and (item.job.kind != "accept" or item.job.predecessor_job_ids == request.build_job_ids)
            )
            build_job_ids = tuple(item.job_id for item in generated_jobs if item.kind == "build")
            accept_job_ids = tuple(item.job_id for item in generated_jobs if item.kind == "accept")
            shape_identity_matches = (
                node_plan == request.node_plan
                and build_job_ids == request.build_job_ids
                and accept_job_ids == (request.accept_job_id,)
            )
        if isinstance(request, FinishAcceptRequest):
            dependents = self._dependent_nodes(stored.job.target_node_id)
            reconciliation_jobs = tuple(
                item.job
                for dependent in dependents
                for item in self._jobs.list()
                if item.job.kind == "plan" and item.job.target_node_id == dependent.id
            )
            shape_identity_matches = (
                tuple(job.job_id for job in reconciliation_jobs) == request.reconciliation_plan_job_ids
            )
        if (
            stored.job.kind == kind
            and stored.job.receipt_id == request.receipt_id
            and event is not None
            and event.kind == "succeeded"
            and event.job_id == request.job_id
            and event.claim_id == request.claim_id
            and event.actor_id == request.actor_id
            and event.process_id == request.process_id
            and event.timestamp == request.finished_at
            and event.evidence_ids == request.evidence_ids
            and receipt is not None
            and receipt.payload.get("code_revision") == request.code_revision
            and receipt_payload.get("evidence") == request.evidence
            and closure_matches
            and shape_identity_matches
        ):
            return FinishJobResult(job=stored, receipt=receipt, event=event)
        return self._finish_diagnostic(
            FinishJobDiagnosticCode.IDENTITY_CONFLICT,
            "archived finish identity differs from the request",
            target=str(request.job_id),
        )

    def _finish_ownership(self, job: JobRecord, request: FinishJobRequest) -> FinishJobResult | None:
        if job.claim_id is None and job.attempt_id is None:
            return self._finish_diagnostic(
                FinishJobDiagnosticCode.NO_ACTIVE_CLAIM,
                "job has no active claim",
            )
        if job.claim_id != request.claim_id or job.attempt_id != request.attempt_id:
            return self._finish_diagnostic(FinishJobDiagnosticCode.NON_OWNER, "claim is not owned by the attempt")
        started = self._attempts.read(request.attempt_id, 1).event
        if (
            started is None
            or started.job_id != job.job_id
            or started.claim_id != request.claim_id
            or started.actor_id != request.actor_id
            or started.process_id != request.process_id
        ):
            return self._finish_diagnostic(FinishJobDiagnosticCode.NON_OWNER, "attempt identity is not current")
        return None

    def _finish_predecessors(self, job: JobRecord, code_revision: str) -> tuple[str, ...] | FinishJobResult:
        receipt_ids: list[str] = []
        for predecessor_job_id in job.predecessor_job_ids:
            try:
                predecessor = self._read_job(predecessor_job_id).job
            except FileNotFoundError:
                return self._finish_diagnostic(
                    FinishJobDiagnosticCode.PREDECESSOR_INVALID,
                    "predecessor job is missing",
                    target=str(predecessor_job_id),
                )
            if predecessor.receipt_id is None:
                return self._finish_diagnostic(
                    FinishJobDiagnosticCode.PREDECESSOR_INVALID,
                    "predecessor receipt is missing",
                    target=str(predecessor_job_id),
                )
            validity = self._receipts.evaluate_currentness(predecessor.receipt_id, self._history, code_revision)
            if not validity.current:
                return self._finish_diagnostic(
                    FinishJobDiagnosticCode.PREDECESSOR_INVALID,
                    "predecessor receipt is not current",
                    lower_code=validity.code.value,
                    target=validity.target or predecessor.receipt_id,
                )
            receipt_ids.append(predecessor.receipt_id)
        return tuple(receipt_ids)

    def _dependent_nodes(self, node_id: str) -> tuple[object, ...]:
        return tuple(node for node in self._revision.graph.nodes if node_id in node.dependencies)

    def _accept_participants(
        self, stored: StoredJob, request: FinishJobRequest
    ) -> tuple[ReplacementTransactionParticipant, ...]:
        assert isinstance(request, FinishAcceptRequest)
        dependents = self._dependent_nodes(stored.job.target_node_id)
        if len(request.reconciliation_plan_job_ids) != len(dependents):
            msg = "dependent reconciliation identities do not correspond"
            raise ValueError(msg)
        if len(set(request.reconciliation_plan_job_ids)) != len(dependents) or any(
            job_id <= 0 or job_id == stored.job.job_id for job_id in request.reconciliation_plan_job_ids
        ):
            msg = "dependent reconciliation identities are invalid"
            raise ValueError(msg)
        participants: list[ReplacementTransactionParticipant] = []
        for dependent, job_id in zip(dependents, request.reconciliation_plan_job_ids, strict=True):
            predecessors = self._reconciliation_job_ids(dependent, stored.job, request.code_revision)
            active = tuple(
                item
                for item in self._jobs.list()
                if item.job.kind == "plan" and item.job.target_node_id == dependent.id
            )
            if len(active) > 1:
                msg = "dependent has multiple active plan jobs"
                raise ValueError(msg)
            if active:
                existing = active[0]
                if (
                    existing.job.job_id != job_id
                    or existing.job.claim_id is not None
                    or existing.job.attempt_id is not None
                ):
                    msg = "dependent reconciliation identity conflicts"
                    raise ValueError(msg)
                replacement = existing.job.model_copy(
                    update={"predecessor_job_ids": predecessors, "updated_at": request.finished_at}
                )
                participants.append(self._jobs.replacement_participant(replacement, existing.token))
                continue
            try:
                self._read_job(job_id)
            except FileNotFoundError:
                participants.append(
                    self._jobs.create_participant(
                        JobRecord(
                            schema_version=1,
                            job_id=job_id,
                            kind="plan",
                            priority=stored.job.priority,
                            created_at=request.finished_at,
                            updated_at=request.finished_at,
                            change_id=stored.job.change_id,
                            delivery_digest=stored.job.delivery_digest,
                            target_node_id=dependent.id,
                            predecessor_job_ids=predecessors,
                        )
                    )
                )
            else:
                msg = "dependent reconciliation identity conflicts"
                raise ValueError(msg)
        return tuple(participants)

    def _reconciliation_job_ids(self, dependent: object, accepted: JobRecord, code_revision: str) -> tuple[int, ...]:
        predecessor_ids: list[int] = []
        for predecessor_node_id in dependent.dependencies:
            if predecessor_node_id == accepted.target_node_id:
                predecessor_ids.append(accepted.job_id)
                continue
            current = self._current_accept_job(predecessor_node_id, code_revision)
            if current is not None:
                predecessor_ids.append(current.job_id)
        return tuple(predecessor_ids)

    def _reconciliation_predecessors(self, node_id: str, code_revision: str) -> StartJobResult | None:
        active_plan = next(
            (item.job for item in self._jobs.list() if item.job.kind == "plan" and item.job.target_node_id == node_id),
            None,
        )
        if active_plan is not None:
            return self._diagnostic(
                StartJobDiagnosticCode.PREDECESSOR_INVALID,
                "node has active reconciliation plan work",
                target=str(active_plan.job_id),
            )
        node = self._revision.resolve(node_id)
        for predecessor_node_id in node.dependencies:
            try:
                current = self._current_accept_job(predecessor_node_id, code_revision)
            except ValueError:
                return self._diagnostic(
                    StartJobDiagnosticCode.PREDECESSOR_INVALID,
                    "predecessor acceptance is ambiguous",
                    target=predecessor_node_id,
                )
            if current is None:
                return self._diagnostic(
                    StartJobDiagnosticCode.PREDECESSOR_INVALID,
                    "predecessor acceptance is unavailable",
                    target=predecessor_node_id,
                )
        return None

    def _current_accept_job(self, node_id: str, code_revision: str) -> JobRecord | None:
        current = tuple(
            item.job
            for item in self._jobs.list(archived=True)
            if item.job.kind == "accept"
            and item.job.target_node_id == node_id
            and item.job.receipt_id is not None
            and self._receipts.evaluate_currentness(item.job.receipt_id, self._history, code_revision).current
        )
        if len(current) > 1:
            msg = "predecessor acceptance is ambiguous"
            raise ValueError(msg)
        return current[0] if current else None

    def _prepare_plan(
        self,
        stored: StoredJob,
        request: FinishPlanRequest,
    ) -> (
        tuple[ChangeRevision, ReplacementTransactionParticipant, tuple[JobRecord, ...], ImpactClosure] | FinishJobResult
    ):
        job = stored.job
        plan = self._validate_node_plan(job.target_node_id, request.node_plan)
        if isinstance(plan, FinishJobResult):
            return plan
        packet_ids, dependencies, closures = plan
        if (
            len(request.build_job_ids) != len(packet_ids)
            or tuple(sorted(request.build_job_ids)) != request.build_job_ids
            or len(set(request.build_job_ids)) != len(packet_ids)
        ):
            return self._finish_diagnostic(
                FinishJobDiagnosticCode.NODE_PLAN_INVALID,
                "packet and build-job identities do not correspond",
            )
        all_job_ids = (*request.build_job_ids, request.accept_job_id)
        if any(job_id <= 0 or job_id == job.job_id for job_id in all_job_ids) or len(set(all_job_ids)) != len(
            all_job_ids
        ):
            return self._finish_diagnostic(
                FinishJobDiagnosticCode.NODE_PLAN_INVALID,
                "generated job identities are invalid",
            )
        for job_id in all_job_ids:
            try:
                self._read_job(job_id)
            except FileNotFoundError:
                continue
            return self._finish_diagnostic(
                FinishJobDiagnosticCode.NODE_PLAN_INVALID,
                "generated job identity already exists",
                target=str(job_id),
            )
        plan_participant = self._node_plan_participant(job.target_node_id, request.node_plan)
        digest = compute_node_plan_digest(self._revision, job.target_node_id, request.node_plan)
        by_packet = dict(zip(packet_ids, request.build_job_ids, strict=True))
        build_jobs = tuple(
            JobRecord(
                schema_version=1,
                job_id=job_id,
                kind="build",
                priority=job.priority,
                created_at=request.finished_at,
                updated_at=request.finished_at,
                change_id=job.change_id,
                delivery_digest=job.delivery_digest,
                target_node_id=job.target_node_id,
                node_plan_digest=digest,
                predecessor_job_ids=(job.job_id, *(by_packet[item] for item in dependencies[packet_id])),
            )
            for packet_id, job_id in zip(packet_ids, request.build_job_ids, strict=True)
        )
        accept_job = JobRecord(
            schema_version=1,
            job_id=request.accept_job_id,
            kind="accept",
            priority=job.priority,
            created_at=request.finished_at,
            updated_at=request.finished_at,
            change_id=job.change_id,
            delivery_digest=job.delivery_digest,
            target_node_id=job.target_node_id,
            node_plan_digest=digest,
            predecessor_job_ids=request.build_job_ids,
        )
        closure = self._union_closures(closures)
        return self._revision, plan_participant, (*build_jobs, accept_job), closure

    def _validate_node_plan(  # noqa: C901, PLR0911
        self, target: str, node_plan: Mapping[str, object]
    ) -> tuple[tuple[str, ...], dict[str, tuple[str, ...]], tuple[ImpactClosure, ...]] | FinishJobResult:
        packets = node_plan.get("packets")
        if not isinstance(packets, list | tuple) or not packets:
            return self._finish_diagnostic(
                FinishJobDiagnosticCode.NODE_PLAN_INVALID,
                "node plan must contain packets",
                target=target,
            )
        allowed_targets = self._allowed_packet_targets(target)
        escaped_reference = self._escaped_plan_reference(node_plan, allowed_targets)
        if escaped_reference is not None:
            return self._finish_diagnostic(
                FinishJobDiagnosticCode.NODE_PLAN_INVALID,
                "node plan references authority outside its delivery node",
                target=escaped_reference,
            )
        packet_ids: list[str] = []
        dependencies: dict[str, tuple[str, ...]] = {}
        closures: list[ImpactClosure] = []
        for packet in packets:
            if not isinstance(packet, Mapping):
                return self._finish_diagnostic(FinishJobDiagnosticCode.NODE_PLAN_INVALID, "packet must be a mapping")
            packet_id = packet.get("id")
            dependency_value = packet.get("dependencies", ())
            if (
                not isinstance(packet_id, str)
                or not _PACKET_ID.fullmatch(packet_id)
                or not packet_id.startswith(f"{target}-PK-")
                or packet_id in packet_ids
                or not isinstance(dependency_value, list | tuple)
                or not all(isinstance(item, str) for item in dependency_value)
            ):
                return self._finish_diagnostic(
                    FinishJobDiagnosticCode.NODE_PLAN_INVALID,
                    "packet identity or dependencies are invalid",
                    target=packet_id if isinstance(packet_id, str) else None,
                )
            try:
                closure = parse_impact_closure(
                    packet.get("impact_closure"),
                    declared_authority_targets=allowed_targets,
                )
            except ValueError as exc:
                return self._finish_diagnostic(
                    FinishJobDiagnosticCode.NODE_PLAN_INVALID,
                    str(exc),
                    target=packet_id,
                )
            packet_ids.append(packet_id)
            dependencies[packet_id] = tuple(dependency_value)
            closures.append(closure)
        packet_set = set(packet_ids)
        if any(dependency not in packet_set for items in dependencies.values() for dependency in items):
            return self._finish_diagnostic(
                FinishJobDiagnosticCode.NODE_PLAN_INVALID,
                "packet dependency escapes the node plan",
            )
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(packet_id: str) -> bool:
            if packet_id in visiting:
                return False
            if packet_id in visited:
                return True
            visiting.add(packet_id)
            valid = all(visit(item) for item in dependencies[packet_id])
            visiting.remove(packet_id)
            visited.add(packet_id)
            return valid

        if not all(visit(packet_id) for packet_id in packet_ids):
            return self._finish_diagnostic(FinishJobDiagnosticCode.NODE_PLAN_INVALID, "packet graph is cyclic")
        return tuple(packet_ids), dependencies, tuple(closures)

    def _allowed_packet_targets(self, target: str) -> set[str]:
        node = self._revision.resolve(target)
        return {
            target,
            node.proof,
            *node.owns,
            *node.supports,
            *node.modules,
            *node.produces,
            *node.consumes,
            *node.dependencies,
            *node.risks,
        }

    @classmethod
    def _escaped_plan_reference(cls, value: object, allowed_targets: set[str]) -> str | None:
        if isinstance(value, Mapping):
            for item in value.values():
                escaped = cls._escaped_plan_reference(item, allowed_targets)
                if escaped is not None:
                    return escaped
            return None
        if isinstance(value, list | tuple):
            for item in value:
                escaped = cls._escaped_plan_reference(item, allowed_targets)
                if escaped is not None:
                    return escaped
            return None
        if isinstance(value, str) and _STABLE_ID.fullmatch(value) and value not in allowed_targets:
            return value
        return None

    def _node_plan_participant(self, target: str, node_plan: Mapping[str, object]) -> ReplacementTransactionParticipant:
        return NodePlanStore(self._revision).prepare(target, node_plan)

    def _finish_closure(  # noqa: PLR0911
        self, job: JobRecord, request: FinishJobRequest
    ) -> ImpactClosure | FinishJobResult:
        node_plan = self._revision.read_node_plan(job.target_node_id)
        if not isinstance(node_plan, Mapping):
            return self._finish_diagnostic(
                FinishJobDiagnosticCode.AUTHORITY_STALE,
                "node plan is unavailable",
                target=job.target_node_id,
            )
        validated = self._validate_node_plan(job.target_node_id, node_plan)
        if isinstance(validated, FinishJobResult):
            return validated
        _packet_ids, _dependencies, closures = validated
        if job.kind == "build":
            sibling_ids = sorted(
                stored.job.job_id
                for stored in (*self._jobs.list(), *self._jobs.list(archived=True))
                if stored.job.kind == "build"
                and stored.job.target_node_id == job.target_node_id
                and stored.job.node_plan_digest == job.node_plan_digest
            )
            try:
                expected = closures[sibling_ids.index(job.job_id)]
            except ValueError, IndexError:
                return self._finish_diagnostic(
                    FinishJobDiagnosticCode.AUTHORITY_STALE,
                    "build job does not correspond to a packet",
                    target=str(job.job_id),
                )
            if request.impact_closure != expected:
                return self._finish_diagnostic(
                    FinishJobDiagnosticCode.EVIDENCE_INVALID,
                    "build impact closure differs from the canonical packet closure",
                    target=str(job.job_id),
                )
            return expected
        if job.kind == "accept":
            return self._union_closures(closures)
        authority_targets = tuple(sorted(entity.id for entity in self._revision.graph.iter_entities()))
        return ImpactClosure(paths=("/",), authority_targets=authority_targets)

    @staticmethod
    def _union_closures(closures: tuple[ImpactClosure, ...]) -> ImpactClosure:
        return ImpactClosure(
            paths=tuple(sorted({path for closure in closures for path in closure.paths})),
            authority_targets=tuple(sorted({target for closure in closures for target in closure.authority_targets})),
        )

    def _new_receipt_validity(
        self,
        revision: ChangeRevision,
        receipt: ReceiptRecord,
        code_revision: str,
        pending_node_plan: Mapping[str, object] | None = None,
    ) -> ReceiptValidity:
        local = evaluate_receipt_currentness(revision, receipt, pending_node_plan)
        if not local.current:
            return local
        assert receipt.impact_closure is not None
        return evaluate_code_revision_currency(self._history, code_revision, code_revision, receipt.impact_closure)

    @staticmethod
    def _success_event(job: JobRecord, request: FinishJobRequest) -> AttemptEvent:
        return AttemptEvent(
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
            timestamp=request.finished_at,
            kind="succeeded",
            evidence_ids=request.evidence_ids,
        )

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

    def _commit_start(
        self,
        stored: StoredJob,
        request: StartJobRequest,
        participants: tuple[ReplacementTransactionParticipant, ...],
    ) -> StartJobResult:
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
            (
                self._jobs.replacement_participant(replacement, stored.token),
                self._attempts.create_participant(event),
                *participants,
            ),
        ).commit()
        return StartJobResult(job=self._jobs.read(request.job_id), event=event)

    def _finalize(  # noqa: PLR0913
        self,
        request: ReleaseJobRequest | FailJobRequest,
        *,
        kind: str,
        timestamp: str,
        detail: str | None,
        evidence_ids: tuple[str, ...],
        participants: tuple[ReplacementTransactionParticipant, ...],
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
            (
                self._jobs.replacement_participant(replacement, stored.token),
                self._attempts.create_participant(event),
                *participants,
            ),
        ).commit()
        return self._jobs.read(request.job_id), event


__all__ = [
    "FailJobDiagnostic",
    "FailJobDiagnosticCode",
    "FailJobRequest",
    "FailJobResult",
    "FinishJobDiagnostic",
    "FinishJobDiagnosticCode",
    "FinishJobRequest",
    "FinishJobResult",
    "FinishPlanRequest",
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
