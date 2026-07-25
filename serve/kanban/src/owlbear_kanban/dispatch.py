"""Dispatch logic for the owlbear kanban engine.

Provides pick_dispatchable() — a gate-filtered, priority/status-sorted list of
tasks ready for agent dispatch.

Rank maps use *execution priority* order, which is intentionally the inverse of
the config.yml display order:
    - PRIORITY_RANK: high=0 (highest) → low=2 (lowest)
        Config display order: low first, high last (opposite).
    - STATUS_RANK: collect=0 (highest) → shape=3 (lowest)
    Config display order: shape first, collect last (opposite).
"""

from __future__ import annotations

import hashlib
import os
import re
import warnings
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_kanban.engine import KanbanEngine
    from owlbear_kanban.models import Task
    from owlbear_kanban.native_runtime import (
        FailJobRequest,
        FailJobResult,
        FinishAcceptRequest,
        FinishJobRequest,
        FinishJobResult,
        FinishPlanRequest,
        NativeRuntime,
        RecoverExpiredClaimsRequest,
        RecoverExpiredClaimsResult,
        RejectAcceptRequest,
        RejectAcceptResult,
        RejectAuditRequest,
        RejectAuditResult,
        ReleaseJobRequest,
        ReleaseJobResult,
        StartJobRequest,
        StartJobResult,
    )
    from owlbear_kanban.proof_checkout import (
        ProofCheckout,
        ProofCheckoutManager,
        ProofCheckoutResult,
        ProofCheckoutSnapshot,
    )

from owlbear_kanban.attempts import AttemptStore
from owlbear_kanban.jobs import JobStore, StoredJob
from owlbear_kanban.native_runtime import (
    RejectAcceptDiagnosticCode,
    RejectAuditDiagnosticCode,
    StartJobDiagnosticCode,
)
from owlbear_kanban.runtime_transaction import ReplacementTransactionParticipant, TransactionConflictError
from owlbear_kanban.topology import PRODUCT_TOPOLOGY
from owlbear_kanban.yaml_rt import make_yaml

# ---------------------------------------------------------------------------
# Rank maps — execution priority (intentionally ≠ config display order)
# ---------------------------------------------------------------------------

PRIORITY_RANK: dict[str, int] = {
    "high": 0,
    "medium": 1,
    "low": 2,
}

STATUS_RANK: dict[str, int] = {
    "collect": 0,
    "verify": 1,
    "build": 2,
    "shape": 3,
}

# ---------------------------------------------------------------------------
# Gate constants
# ---------------------------------------------------------------------------

_AC_PATTERN = re.compile(r"(?m)^\s*(-\s|\d+\.\s)")

_CLARITY_STATUSES = frozenset({"build", "verify", "collect"})

_NON_IMPL_TAGS = PRODUCT_TOPOLOGY.non_impl_tags

_MAX_PRIORITY_RANK = max(PRIORITY_RANK.values())
_MAX_STATUS_RANK = max(STATUS_RANK.values())

_TERMINAL_STATUSES = frozenset({"archived"})

_COORDINATION_PATH = Path("dispatch") / "coordination.yaml"
_WriterKind = Literal["plan", "build"]
_ReaderKind = Literal["accept", "audit"]


class CoordinationHolder(BaseModel):
    """Identity and provenance of one active dispatch participant."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    job_id: int = Field(gt=0)
    kind: _WriterKind | _ReaderKind
    attempt_id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)
    actor_id: str = Field(min_length=1)
    process_id: str = Field(min_length=1)
    claimed_at: str = Field(min_length=1)


class WriterCoordination(BaseModel):
    """The singleton native writer/reader coordination record."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal[1] = 1
    writer: CoordinationHolder | None = None
    readers: tuple[CoordinationHolder, ...] = ()

    @field_validator("readers")
    @classmethod
    def _readers_are_sorted_and_unique(cls, readers: tuple[CoordinationHolder, ...]) -> tuple[CoordinationHolder, ...]:
        identities = tuple(holder.job_id for holder in readers)
        if identities != tuple(sorted(set(identities))):
            msg = "readers must be unique and sorted by job ID"
            raise ValueError(msg)
        if any(holder.kind not in ("accept", "audit") for holder in readers):
            msg = "readers must be accept or audit holders"
            raise ValueError(msg)
        return readers

    @model_validator(mode="after")
    def _participants_are_compatible(self) -> WriterCoordination:
        if self.writer is not None and self.writer.kind not in ("plan", "build"):
            msg = "writer must be a plan or build holder"
            raise ValueError(msg)
        if self.writer is not None and self.readers:
            msg = "writer coordination cannot include readers"
            raise ValueError(msg)
        return self


class DispatchDiagnosticCode(StrEnum):
    """Enumerate stable dispatch coordination failure codes."""

    WRITER_CONFLICT = "ERR_DISPATCH_WRITER_CONFLICT"
    LEASE_STALE = "ERR_DISPATCH_LEASE_STALE"


class DispatchOmissionReason(StrEnum):
    """Explain why a persisted job is absent from a dispatch plan."""

    AUTHORITY_STALE = "authority-stale"
    PREDECESSOR_INVALID = "predecessor-invalid"
    REQUEST_PENDING = "request-pending"
    NOT_PENDING = "not-pending"
    CLAIMED = "claimed"
    BLOCKED = "blocked"
    UNSUPPORTED_KIND = "unsupported-kind"


class DispatchWaveEntry(BaseModel):
    """One dispatchable job with its exact agent profile."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    job_id: int = Field(gt=0)
    kind: _WriterKind | _ReaderKind
    agent_profile: Literal["planner", "builder", "acceptor", "auditor"]
    predecessor_job_ids: tuple[int, ...] = ()


class DispatchOmission(BaseModel):
    """A persisted job excluded from a dispatch plan."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    job_id: int = Field(gt=0)
    reason: DispatchOmissionReason


class DispatchPlan(BaseModel):
    """A deterministic, read-only dispatch plan for one candidate revision."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    waves: tuple[tuple[DispatchWaveEntry, ...], ...]
    omissions: tuple[DispatchOmission, ...]


class DispatchDiagnostic(BaseModel):
    """A coordination-specific runtime diagnostic."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    code: DispatchDiagnosticCode
    detail: str
    holder_job_ids: tuple[int, ...] = ()

    @field_validator("holder_job_ids")
    @classmethod
    def _holder_ids_are_sorted(cls, holder_job_ids: tuple[int, ...]) -> tuple[int, ...]:
        if holder_job_ids != tuple(sorted(set(holder_job_ids))):
            msg = "holder job IDs must be unique and sorted"
            raise ValueError(msg)
        return holder_job_ids


class _CoordinationStore:
    def __init__(self, work_root: Path) -> None:
        self._work_root = work_root

    def read(self) -> tuple[WriterCoordination, str]:
        path = self._work_root / _COORDINATION_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        empty = self._serialize(WriterCoordination())
        try:
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        except FileExistsError:
            pass
        else:
            with os.fdopen(descriptor, "wb") as output:
                output.write(empty)
                output.flush()
                os.fsync(output.fileno())
        content = path.read_bytes()
        try:
            parsed = make_yaml().load(content.decode("utf-8"))
            if isinstance(parsed, dict) and isinstance(parsed.get("readers"), list):
                parsed = dict(parsed) | {"readers": tuple(parsed["readers"])}
            coordination = WriterCoordination.model_validate(parsed)
        except (TypeError, UnicodeDecodeError, ValueError) as exc:
            message = "dispatch coordination is invalid"
            raise ValueError(message) from exc
        return coordination, hashlib.sha256(content).hexdigest()

    def replacement_participant(
        self,
        replacement: WriterCoordination,
        token: str,
    ) -> ReplacementTransactionParticipant:
        path = self._work_root / _COORDINATION_PATH
        current = path.read_bytes()
        if hashlib.sha256(current).hexdigest() != token:
            raise TransactionConflictError
        return ReplacementTransactionParticipant(
            self._work_root,
            _COORDINATION_PATH,
            current,
            self._serialize(replacement),
        )

    @staticmethod
    def _serialize(coordination: WriterCoordination) -> bytes:
        stream = StringIO()
        make_yaml(explicit_start=True).dump(coordination.model_dump(mode="json"), stream)
        return stream.getvalue().encode("utf-8")


class DispatchRuntime:
    """Coordinate native lifecycle mutations across global writer and reader holders."""

    def __init__(
        self,
        native: NativeRuntime,
        work_root: Path,
        proof_checkouts: ProofCheckoutManager | None = None,
    ) -> None:
        self._native = native
        self._jobs = JobStore(work_root)
        self._attempts = AttemptStore(work_root)
        self._coordination = _CoordinationStore(work_root)
        self._proof_checkouts = proof_checkouts

    def pick_waves(self, candidate_revision: str, size: int) -> DispatchPlan:
        """Plan current eligible jobs without granting any claim authority."""
        if size <= 0:
            msg = "wave size must be positive"
            raise ValueError(msg)
        eligible: list[DispatchWaveEntry] = []
        omissions: list[DispatchOmission] = []
        for stored in self._jobs.list():
            reason = self._omission_reason(stored, candidate_revision)
            if reason is not None:
                omissions.append(DispatchOmission(job_id=stored.job.job_id, reason=reason))
                continue
            agent_profile = {
                "plan": "planner",
                "build": "builder",
                "accept": "acceptor",
                "audit": "auditor",
            }.get(stored.job.kind)
            if agent_profile is None:
                omissions.append(
                    DispatchOmission(job_id=stored.job.job_id, reason=DispatchOmissionReason.UNSUPPORTED_KIND)
                )
                continue
            eligible.append(
                DispatchWaveEntry(
                    job_id=stored.job.job_id,
                    kind=stored.job.kind,
                    agent_profile=agent_profile,
                    predecessor_job_ids=stored.job.predecessor_job_ids,
                )
            )
        eligible.sort(key=self._delivery_topology_key)
        return DispatchPlan(waves=self._plan_waves(eligible, size), omissions=tuple(omissions))

    def _delivery_topology_key(self, entry: DispatchWaveEntry) -> tuple[int, int]:
        node_by_id = {node.id: node for node in self._native._revision.graph.nodes}  # noqa: SLF001
        pending = set(node_by_id)
        order: list[str] = []
        while pending:
            ready = sorted(node_id for node_id in pending if not (set(node_by_id[node_id].dependencies) & pending))
            if not ready:
                ready = sorted(pending)
            order.extend(ready)
            pending.difference_update(ready)
        return (order.index(self._jobs.read(entry.job_id).job.target_node_id), entry.job_id)

    def _omission_reason(self, stored: StoredJob, candidate_revision: str) -> DispatchOmissionReason | None:
        job = stored.job
        if job.claim_id is not None or job.attempt_id is not None:
            return DispatchOmissionReason.CLAIMED
        if job.block_id is not None:
            return DispatchOmissionReason.BLOCKED
        code = self._native._dispatch_eligibility(stored, candidate_revision)  # noqa: SLF001
        return {
            "ERR_START_AUTHORITY_STALE": DispatchOmissionReason.AUTHORITY_STALE,
            "ERR_START_PREDECESSOR_INVALID": DispatchOmissionReason.PREDECESSOR_INVALID,
            "ERR_START_REQUEST_PENDING": DispatchOmissionReason.REQUEST_PENDING,
            "ERR_START_TERMINAL": DispatchOmissionReason.NOT_PENDING,
            "ERR_START_ACTIVE_CLAIM": DispatchOmissionReason.CLAIMED,
        }.get(code)

    @staticmethod
    def _plan_waves(entries: list[DispatchWaveEntry], size: int) -> tuple[tuple[DispatchWaveEntry, ...], ...]:
        waves: list[tuple[DispatchWaveEntry, ...]] = []
        readers: list[DispatchWaveEntry] = []
        for entry in entries:
            if entry.kind in ("plan", "build"):
                if readers:
                    waves.extend(tuple(readers[index : index + size]) for index in range(0, len(readers), size))
                    readers = []
                waves.append((entry,))
            else:
                reader_ids = {reader.job_id for reader in readers}
                dependent = reader_ids.intersection(entry.predecessor_job_ids) or any(
                    entry.job_id in reader.predecessor_job_ids for reader in readers
                )
                if dependent:
                    waves.extend(tuple(readers[index : index + size]) for index in range(0, len(readers), size))
                    readers = []
                readers.append(entry)
        if readers:
            waves.extend(tuple(readers[index : index + size]) for index in range(0, len(readers), size))
        return tuple(waves)

    def start(self, request: StartJobRequest) -> StartJobResult | DispatchDiagnostic:
        """Claim an eligible job while enforcing global reader-writer coordination."""
        for _ in range(2):
            try:
                coordination, token = self._coordination.read()
                stale = self._stale_diagnostic(coordination)
                if stale is not None:
                    return stale
                stored = self._jobs.read(request.job_id)
                holder = self._holder(stored, request)
                conflict = self._start_conflict(coordination, holder)
                if conflict is not None:
                    return conflict
                replacement = self._with_holder(coordination, holder)
                participant = self._coordination.replacement_participant(replacement, token)
                return self._native._start_job(request, (participant,))  # noqa: SLF001
            except TransactionConflictError:
                continue
        coordination, _token = self._coordination.read()
        return self._conflict("coordination changed during start", coordination)

    def start_with_checkout(
        self, request: StartJobRequest
    ) -> tuple[StartJobResult | DispatchDiagnostic, ProofCheckout | ProofCheckoutResult | None]:
        """Prepare a reader checkout before claiming, then return it with the start result."""
        stored = self._jobs.read(request.job_id)
        if stored.job.kind not in ("accept", "audit") or self._proof_checkouts is None:
            return self.start(request), None
        checkout = self._proof_checkouts.existing(request.job_id)
        prepared = False
        if checkout is None:
            result = self._proof_checkouts.materialize(stored.job, request.candidate_revision)
            if result.checkout is None:
                return (
                    self._native._diagnostic(  # noqa: SLF001
                        StartJobDiagnosticCode.AUTHORITY_STALE,
                        "proof checkout setup failed",
                        lower_code=result.diagnostic.code.value if result.diagnostic else None,
                        target=str(request.job_id),
                    ),
                    result,
                )
            checkout = result.checkout
            prepared = True
        started = self.start(request)
        if isinstance(started, DispatchDiagnostic) or started.diagnostic is not None:
            if prepared:
                self._proof_checkouts.cleanup(request.job_id)
            return started, None
        return started, checkout

    def release(self, request: ReleaseJobRequest) -> ReleaseJobResult | DispatchDiagnostic:
        """Release an active claim and its coordination holder."""
        return self._finalize(request, "released")

    def fail(self, request: FailJobRequest) -> FailJobResult | DispatchDiagnostic:
        """Record a failed attempt and release its coordination holder."""
        return self._finalize(request, "failed")

    def finish_plan(self, request: FinishPlanRequest) -> FinishJobResult | DispatchDiagnostic:
        """Finish plan work and release its writer coordination holder."""
        return self._finish(request, "plan")

    def finish_build(self, request: FinishJobRequest) -> FinishJobResult | DispatchDiagnostic:
        """Finish build work and release its writer coordination holder."""
        return self._finish(request, "build")

    def finish_accept(self, request: FinishAcceptRequest) -> FinishJobResult | DispatchDiagnostic:
        """Clean the proof checkout and finish acceptance work."""
        if not self._cleanup_proof_checkout(request.job_id):
            return self._proof_cleanup_diagnostic(request.job_id)
        return self._finish(request, "accept", self._native._accept_participants)  # noqa: SLF001

    def reject_accept(self, request: RejectAcceptRequest) -> RejectAcceptResult | DispatchDiagnostic:
        """Reject acceptance, release its reader, and remove its proof checkout."""
        coordination, token = self._coordination.read()
        stale = self._stale_diagnostic(coordination)
        if stale is not None:
            return stale
        holder = self._find_holder(coordination, request.job_id)
        if holder is None:
            completed = self._attempts.read(request.attempt_id, 2).event
            if completed is None:
                return self._stale(coordination)
            return self._native.reject_accept(request)
        if not self._matches(holder, request):
            return self._native.reject_accept(request)
        snapshot, diagnostic = self._preserve_rejection_checkout(request)
        if diagnostic is not None:
            return diagnostic
        replacement = self._without_holder(coordination, holder)
        participant = self._coordination.replacement_participant(replacement, token)
        result = self._native._reject_accept(  # noqa: SLF001
            request,
            (participant,),
            before_commit=lambda: self._cleanup_proof_checkout(request.job_id),
        )
        return self._restore_rejection_checkout(request, result, snapshot)

    def reject_audit(self, request: RejectAuditRequest) -> RejectAuditResult | DispatchDiagnostic:
        """Reject an audit, release its reader, and remove its proof checkout."""
        coordination, token = self._coordination.read()
        stale = self._stale_diagnostic(coordination)
        if stale is not None:
            return stale
        holder = self._find_holder(coordination, request.job_id)
        if holder is None:
            completed = self._attempts.read(request.attempt_id, 2).event
            if completed is None:
                return self._stale(coordination)
            return self._native.reject_audit(request)
        if not self._matches(holder, request):
            return self._native.reject_audit(request)
        snapshot, diagnostic = self._preserve_rejection_checkout(request, audit=True)
        if diagnostic is not None:
            return diagnostic
        replacement = self._without_holder(coordination, holder)
        participant = self._coordination.replacement_participant(replacement, token)
        result = self._native._reject_audit(  # noqa: SLF001
            request,
            (participant,),
            before_commit=lambda: self._cleanup_proof_checkout(request.job_id),
        )
        return self._restore_rejection_checkout(request, result, snapshot, audit=True)

    def _preserve_rejection_checkout(
        self,
        request: RejectAcceptRequest | RejectAuditRequest,
        *,
        audit: bool = False,
    ) -> tuple[ProofCheckoutSnapshot | None, RejectAcceptResult | RejectAuditResult | None]:
        if self._proof_checkouts is None:
            return None, None
        checkout = self._proof_checkouts.existing(request.job_id)
        snapshot = self._proof_checkouts.snapshot(request.job_id)
        if checkout is not None and snapshot is None:
            if audit:
                return None, self._native._reject_audit_diagnostic(  # noqa: SLF001
                    RejectAuditDiagnosticCode.CLEANUP_FAILED,
                    "proof checkout authority could not be preserved",
                    target=str(request.job_id),
                )
            return None, self._native._reject_diagnostic(  # noqa: SLF001
                RejectAcceptDiagnosticCode.CLEANUP_FAILED,
                "proof checkout authority could not be preserved",
                target=str(request.job_id),
            )
        return snapshot, None

    def _restore_rejection_checkout(
        self,
        request: RejectAcceptRequest | RejectAuditRequest,
        result: RejectAcceptResult | RejectAuditResult,
        snapshot: ProofCheckoutSnapshot | None,
        *,
        audit: bool = False,
    ) -> RejectAcceptResult | RejectAuditResult:
        if (
            result.diagnostic is not None
            and snapshot is not None
            and self._proof_checkouts is not None
            and self._proof_checkouts.existing(request.job_id) is None
        ):
            try:
                restored = self._proof_checkouts.restore(self._jobs.read(request.job_id).job, snapshot)
            except FileNotFoundError, ValueError:
                restored = False
            if not restored:
                if audit:
                    return self._native._reject_audit_diagnostic(  # noqa: SLF001
                        RejectAuditDiagnosticCode.CLEANUP_FAILED,
                        "proof checkout restoration failed after rejected publication",
                        lower_code=result.diagnostic.code.value,
                        target=str(request.job_id),
                    )
                return self._native._reject_diagnostic(  # noqa: SLF001
                    RejectAcceptDiagnosticCode.CLEANUP_FAILED,
                    "proof checkout restoration failed after rejected publication",
                    lower_code=result.diagnostic.code.value,
                    target=str(request.job_id),
                )
        return result

    def finish_audit(self, request: FinishJobRequest) -> FinishJobResult | DispatchDiagnostic:
        """Clean the proof checkout and finish audit work."""
        if not self._cleanup_proof_checkout(request.job_id):
            return self._proof_cleanup_diagnostic(request.job_id)
        return self._finish(request, "audit")

    def recover_expired_claims(
        self, request: RecoverExpiredClaimsRequest
    ) -> RecoverExpiredClaimsResult | DispatchDiagnostic:
        """Recover expired claims and remove their coordination and proof state."""
        coordination, _token = self._coordination.read()
        stale = self._stale_diagnostic(coordination)
        if stale is not None:
            return stale

        def participant_for(stored: StoredJob, _started: object) -> tuple[ReplacementTransactionParticipant, ...]:
            current, token = self._coordination.read()
            holder = self._find_holder(current, stored.job.job_id)
            if holder is None:
                return ()
            return (self._coordination.replacement_participant(self._without_holder(current, holder), token),)

        result = self._native._recover_expired_claims(request, participant_for)  # noqa: SLF001
        for recovered in result.recovered:
            self._cleanup_proof_checkout(recovered.job.job.job_id)
        return result

    def _finalize(
        self,
        request: ReleaseJobRequest | FailJobRequest,
        kind: Literal["released", "failed"],
    ) -> ReleaseJobResult | FailJobResult | DispatchDiagnostic:
        coordination, token = self._coordination.read()
        stale = self._stale_diagnostic(coordination)
        if stale is not None:
            return stale
        holder = self._find_holder(coordination, request.job_id)
        participants: tuple[ReplacementTransactionParticipant, ...] = ()
        if holder is not None and self._matches(holder, request):
            replacement = self._without_holder(coordination, holder)
            participants = (self._coordination.replacement_participant(replacement, token),)
        if kind == "released":
            result = self._native._release_job(request, participants)  # noqa: SLF001
            if result.diagnostic is None:
                self._cleanup_proof_checkout(request.job_id)
            return result
        return self._native._fail_job(request, participants)  # noqa: SLF001

    def _cleanup_proof_checkout(self, job_id: int) -> bool:
        if self._proof_checkouts is None:
            return True
        self._proof_checkouts.cleanup(job_id)
        return not self._proof_checkouts.is_orphan(str(job_id))

    @staticmethod
    def _proof_cleanup_diagnostic(job_id: int) -> DispatchDiagnostic:
        return DispatchDiagnostic(
            code=DispatchDiagnosticCode.LEASE_STALE,
            detail="proof checkout cleanup left an orphaned checkout",
            holder_job_ids=(job_id,),
        )

    def _finish(
        self,
        request: FinishJobRequest,
        kind: _WriterKind | _ReaderKind,
        participant_factory: (
            Callable[[StoredJob, FinishJobRequest], tuple[ReplacementTransactionParticipant, ...]] | None
        ) = None,
    ) -> FinishJobResult | DispatchDiagnostic:
        coordination, token = self._coordination.read()
        stale = self._stale_diagnostic(coordination)
        if stale is not None:
            return stale
        holder = self._find_holder(coordination, request.job_id)
        participants: tuple[ReplacementTransactionParticipant, ...] = ()
        if holder is not None and self._matches(holder, request):
            replacement = self._without_holder(coordination, holder)
            participants = (self._coordination.replacement_participant(replacement, token),)
        return self._native._finish(  # noqa: SLF001
            request,
            kind,
            lambda stored, finish_request: (
                *participants,
                *(participant_factory(stored, finish_request) if participant_factory is not None else ()),
            ),
        )

    def _stale_diagnostic(self, coordination: WriterCoordination) -> DispatchDiagnostic | None:
        for holder in self._holders(coordination):
            try:
                stored = self._jobs.read(holder.job_id)
                started = self._attempts.read(holder.attempt_id, 1).event
            except FileNotFoundError, ValueError:
                return self._stale(coordination)
            job = stored.job
            if (
                job.kind != holder.kind
                or job.claim_id != holder.claim_id
                or job.attempt_id != holder.attempt_id
                or job.updated_at != holder.claimed_at
                or started is None
                or started.kind != "started"
                or started.job_id != holder.job_id
                or started.claim_id != holder.claim_id
                or started.actor_id != holder.actor_id
                or started.process_id != holder.process_id
                or started.timestamp != holder.claimed_at
            ):
                return self._stale(coordination)
        return None

    @staticmethod
    def _holder(stored: StoredJob, request: StartJobRequest) -> CoordinationHolder:
        return CoordinationHolder(
            job_id=request.job_id,
            kind=stored.job.kind,
            attempt_id=request.attempt_id,
            claim_id=request.claim_id,
            actor_id=request.actor_id,
            process_id=request.process_id,
            claimed_at=request.claimed_at,
        )

    def _start_conflict(
        self, coordination: WriterCoordination, holder: CoordinationHolder
    ) -> DispatchDiagnostic | None:
        existing = self._find_holder(coordination, holder.job_id)
        if existing is not None and existing == holder:
            return None
        if holder.kind in ("plan", "build") and self._holders(coordination):
            return self._conflict("a global participant already holds coordination", coordination)
        if holder.kind in ("accept", "audit") and coordination.writer is not None:
            return self._conflict("a writer already holds coordination", coordination)
        return None

    @staticmethod
    def _holders(coordination: WriterCoordination) -> tuple[CoordinationHolder, ...]:
        return ((coordination.writer,) if coordination.writer is not None else ()) + coordination.readers

    def _with_holder(self, coordination: WriterCoordination, holder: CoordinationHolder) -> WriterCoordination:
        if holder.kind in ("plan", "build"):
            return WriterCoordination(writer=holder)
        if holder in coordination.readers:
            return coordination
        readers = tuple(sorted((*coordination.readers, holder), key=lambda item: item.job_id))
        return WriterCoordination(readers=readers)

    def _without_holder(self, coordination: WriterCoordination, holder: CoordinationHolder) -> WriterCoordination:
        if coordination.writer == holder:
            return WriterCoordination()
        return WriterCoordination(readers=tuple(item for item in coordination.readers if item != holder))

    def _find_holder(self, coordination: WriterCoordination, job_id: int) -> CoordinationHolder | None:
        return next((holder for holder in self._holders(coordination) if holder.job_id == job_id), None)

    @staticmethod
    def _matches(holder: CoordinationHolder, request: object) -> bool:
        fields = ("job_id", "attempt_id", "claim_id", "actor_id", "process_id")
        return all(getattr(request, field) == getattr(holder, field) for field in fields)

    def _stale(self, coordination: WriterCoordination) -> DispatchDiagnostic:
        return DispatchDiagnostic(
            code=DispatchDiagnosticCode.LEASE_STALE,
            detail="persisted coordination does not match active job claim and started event",
            holder_job_ids=tuple(sorted(holder.job_id for holder in self._holders(coordination))),
        )

    def _conflict(self, detail: str, coordination: WriterCoordination) -> DispatchDiagnostic:
        return DispatchDiagnostic(
            code=DispatchDiagnosticCode.WRITER_CONFLICT,
            detail=detail,
            holder_job_ids=tuple(sorted(holder.job_id for holder in self._holders(coordination))),
        )


# ---------------------------------------------------------------------------
# Gate predicates
# ---------------------------------------------------------------------------


def _claim_is_active(task: Task, timeout: timedelta) -> bool:
    """Return True if the task's claim has not expired."""
    if not task.claimed_at:
        return False
    claimed_dt = datetime.fromisoformat(task.claimed_at)
    if claimed_dt.tzinfo is None:
        claimed_dt = claimed_dt.replace(tzinfo=UTC)
    return datetime.now(tz=UTC) < claimed_dt + timeout


def _passes_clarity_gate(task: Task) -> bool:
    """Return True if the task passes the clarity gate.

    Gate applies to build/verify/collect tasks:
    - PASS if the structured ac field has entries
    - PASS if body contains a bullet or numbered list item
    - FAIL if body is empty or prose-only with no structured AC
    """
    if task.status not in _CLARITY_STATUSES:
        return True
    if task.ac:
        return True
    body: str = task.body or ""
    return bool(_AC_PATTERN.search(body))


def _passes_dependency_gate(task: Task, active_ids: frozenset[int]) -> bool:
    """Return True if all depends_on IDs are resolved (not in active tasks).

    A dependency is met when its task ID is absent from the active task set
    (i.e. archived or purged).  Any dependency still present in the tasks
    directory — regardless of status, including ``done`` — is considered unmet.
    """
    deps: list[int] = task.depends_on or []
    if not deps:
        return True
    return not any(dep_id in active_ids for dep_id in deps)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def pick_dispatchable(engine: KanbanEngine, *, limit: int = 25, tag: str = "") -> list[Task]:
    """Return a gate-filtered, sorted list of dispatchable tasks.

    Reads full Task objects (including body) directly from the filesystem so
    that gate predicates execute against the actual task body, not the
    body-stripped TaskSummary returned by engine.list_tasks().

    Gates applied (in order):
    1. Terminal status exclusion — archived/done tasks are excluded.
    2. Blocked exclusion — blocked=True tasks are excluded.
    3. Dependency gate — tasks whose depends_on IDs are still active are excluded.
    4. Claimed exclusion — tasks with an active (non-expired) claim are excluded.
    5. Tag filter — when tag is non-empty, only tasks carrying that tag pass.
    6. Clarity gate — build/verify/collect tasks need at least one bullet/numbered AC line.

    Results are sorted by (PRIORITY_RANK, STATUS_RANK) ascending and capped at limit.

    Args:
        engine: KanbanEngine instance providing filesystem access.
        limit:  Maximum number of tasks to return. Defaults to 25.
        tag:    If non-empty, only include tasks tagged with this value.

    Returns:
        Sorted, capped list of Task instances.
    """
    warnings.warn(
        "pick_dispatchable() is deprecated; use AgentView.pick_tasks() instead",
        DeprecationWarning,
        stacklevel=2,
    )

    tasks: list[Task] = []
    for path in sorted(engine._tasks_dir.glob("*.md")):  # noqa: SLF001
        task_id = path.stem.split("-", 1)[0]
        if not task_id.isdigit():
            continue
        tasks.append(engine.show_task(task_id))

    active_ids: frozenset[int] = frozenset(t.id for t in tasks if t.id is not None)
    claim_timeout = engine._parse_claim_timeout()  # noqa: SLF001

    passing: list[Task] = []
    for task in tasks:
        if task.status in _TERMINAL_STATUSES:
            continue
        if task.blocked:
            continue
        if not _passes_dependency_gate(task, active_ids):
            continue
        if _claim_is_active(task, claim_timeout):
            continue
        if tag and tag not in (task.tags or []):
            continue
        if not _passes_clarity_gate(task):
            continue
        passing.append(task)

    passing.sort(
        key=lambda t: (
            PRIORITY_RANK.get(t.priority or "", _MAX_PRIORITY_RANK + 1),
            STATUS_RANK.get(t.status or "", _MAX_STATUS_RANK + 1),
        )
    )

    return passing[:limit]
