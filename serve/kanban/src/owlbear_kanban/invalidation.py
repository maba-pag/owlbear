"""Typed planning for receipt invalidation and corrective runtime work."""

from __future__ import annotations

import contextlib
from collections import deque
from enum import StrEnum
from typing import TYPE_CHECKING, Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from owlbear_kanban.finding import FindingClass, FindingId, FindingStore
from owlbear_kanban.jobs import JobDisposition, JobRecord, JobStore, StoredJob
from owlbear_kanban.receipt import ReceiptRecord, ReceiptStore
from owlbear_kanban.runtime_transaction import RuntimeTransaction, TransactionConflictError

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Mapping
    from pathlib import Path

    from owlbear_kanban.change import ChangeRevision

FindingTarget = Literal[
    "packet-implementation",
    "packet-local-proof",
    "packet-plan",
    "packet-dependency",
    "packet-proof-plan",
    "admitted-design-authority",
    "node-integration",
    "whole-change-integration",
]
CorrectiveJobKind = Literal["shape", "build"]
CorrectiveRouteKind = Literal[
    "build-repair",
    "node-shape-revision",
    "design-reentry",
    "node-integration-repair",
    "affected-node-correction",
]
InvalidationId = Annotated[
    str,
    StringConstraints(strict=True, pattern=r"^[A-Za-z0-9]+(?:[._-][A-Za-z0-9]+)*$"),
]


class _InvalidationModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class CorrectiveRouteRequest(_InvalidationModel):
    """One typed late finding presented to the corrective planner."""

    finding_id: FindingId
    finding_class: FindingClass
    target: FindingTarget
    target_node_ids: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _require_one_local_target(self) -> CorrectiveRouteRequest:
        if self.target != "whole-change-integration" and len(self.target_node_ids) != 1:
            msg = "local corrective findings must identify exactly one delivery node"
            raise ValueError(msg)
        if len(set(self.target_node_ids)) != len(self.target_node_ids):
            msg = "corrective target nodes must be unique"
            raise ValueError(msg)
        return self


class CorrectiveJobPlan(_InvalidationModel):
    """One minimum local job required by a corrective route."""

    kind: CorrectiveJobKind
    target_node_id: str
    through_shape_correction: bool = False


class CorrectiveRoute(_InvalidationModel):
    """Typed route and minimum local work for one late finding."""

    finding_id: FindingId
    finding_class: FindingClass
    route: CorrectiveRouteKind
    design_reentry: bool = False
    jobs: tuple[CorrectiveJobPlan, ...] = ()


class InvalidationRequest(_InvalidationModel):
    """One immutable supersession and corrective-work identity."""

    invalidation_id: InvalidationId
    supersession_receipt_id: InvalidationId
    invalidated_receipt_ids: tuple[InvalidationId, ...] = Field(min_length=1)
    routes: tuple[CorrectiveRoute, ...] = Field(min_length=1)
    corrective_job_ids: tuple[int, ...]
    issued_at: str = Field(min_length=1)
    code_revision: str = Field(min_length=1)
    priority: int = 0

    @model_validator(mode="after")
    def _validate_identity(self) -> InvalidationRequest:
        planned_jobs = sum(len(route.jobs) for route in self.routes)
        if len(self.corrective_job_ids) != planned_jobs:
            msg = "corrective job identities must correspond to planned jobs"
            raise ValueError(msg)
        if any(job_id <= 0 for job_id in self.corrective_job_ids) or len(set(self.corrective_job_ids)) != planned_jobs:
            msg = "corrective job identities must be unique positive IDs"
            raise ValueError(msg)
        if tuple(sorted(set(self.invalidated_receipt_ids))) != self.invalidated_receipt_ids:
            msg = "invalidated receipt identities must be sorted and unique"
            raise ValueError(msg)
        finding_ids = tuple(route.finding_id for route in self.routes)
        if len(set(finding_ids)) != len(finding_ids):
            msg = "corrective routes must identify distinct findings"
            raise ValueError(msg)
        return self


class InvalidationDiagnosticCode(StrEnum):
    """Stable public invalidation failure codes."""

    REFERENCE_INVALID = "ERR_INVALIDATION_REFERENCE"
    CONFLICT = "ERR_INVALIDATION_CONFLICT"
    ABORTED = "ERR_INVALIDATION_ABORTED"


class InvalidationDiagnostic(_InvalidationModel):
    code: InvalidationDiagnosticCode
    detail: str
    target: str | None = None


class InvalidationOutcome(_InvalidationModel):
    """Published invalidation closure and deterministic identities."""

    invalidation_id: InvalidationId
    supersession_receipt: ReceiptRecord
    affected_receipt_ids: tuple[str, ...]
    affected_job_ids: tuple[int, ...]
    superseded_jobs: tuple[StoredJob, ...]
    corrective_jobs: tuple[StoredJob, ...]


class InvalidationResult(_InvalidationModel):
    outcome: InvalidationOutcome | None = None
    diagnostic: InvalidationDiagnostic | None = None

    @model_validator(mode="after")
    def _require_one_result(self) -> InvalidationResult:
        if (self.outcome is None) == (self.diagnostic is None):
            msg = "invalidation result needs exactly one outcome"
            raise ValueError(msg)
        return self


def plan_corrective_route(request: CorrectiveRouteRequest) -> CorrectiveRoute:
    """Return the authority-defined minimum corrective route for one finding."""
    node_id = request.target_node_ids[0]
    common = {"finding_id": request.finding_id, "finding_class": request.finding_class}
    if request.target in {"packet-implementation", "packet-local-proof"}:
        return CorrectiveRoute(
            **common,
            route="build-repair",
            jobs=(CorrectiveJobPlan(kind="build", target_node_id=node_id),),
        )
    if request.target in {"packet-plan", "packet-dependency", "packet-proof-plan"}:
        return CorrectiveRoute(
            **common,
            route="node-shape-revision",
            jobs=(CorrectiveJobPlan(kind="shape", target_node_id=node_id),),
        )
    if request.target == "admitted-design-authority":
        return CorrectiveRoute(**common, route="design-reentry", design_reentry=True)
    if request.target == "node-integration":
        return CorrectiveRoute(
            **common,
            route="node-integration-repair",
            jobs=(
                CorrectiveJobPlan(
                    kind="shape",
                    target_node_id=node_id,
                    through_shape_correction=True,
                ),
            ),
        )
    jobs = tuple(
        CorrectiveJobPlan(kind="shape", target_node_id=target_node_id, through_shape_correction=True)
        for target_node_id in request.target_node_ids
    )
    return CorrectiveRoute(**common, route="affected-node-correction", jobs=jobs)


class InvalidationRuntime:
    """Compute and atomically publish minimum invalidation closure."""

    def __init__(self, revision: ChangeRevision, work_root: Path) -> None:
        self._revision = revision
        self._work_root = work_root
        self._receipts = ReceiptStore(revision)
        self._jobs = JobStore(work_root)
        self._findings = FindingStore(work_root)
        RuntimeTransaction.recover_all(work_root, roots=(work_root, revision.source_dir))

    def apply(  # noqa: PLR0911 - stable public outcomes return at each mutation boundary.
        self,
        request: InvalidationRequest,
        *,
        failure: Callable[[str], None] | None = None,
    ) -> InvalidationResult:
        """Apply one invalidation identity, returning exact replay or stable failure."""
        try:
            receipt_records = self._receipt_records()
            existing_identity = next(
                (
                    receipt
                    for receipt in receipt_records.values()
                    if receipt.kind == "supersession"
                    and receipt.payload.get("invalidation_id") == request.invalidation_id
                ),
                None,
            )
            if existing_identity is not None and existing_identity.receipt_id != request.supersession_receipt_id:
                return self._diagnostic(InvalidationDiagnosticCode.CONFLICT, "invalidation identity conflicts")
            self._validate_request_references(request, receipt_records)
            affected_receipts = _receipt_closure(request.invalidated_receipt_ids, receipt_records)
            all_jobs = (*self._jobs.list(), *self._jobs.list(archived=True))
            affected_jobs = _job_closure(affected_receipts, all_jobs)
            superseded = tuple(
                item
                for item in self._jobs.list()
                if item.job.job_id in affected_jobs
                and (
                    item.job.disposition is JobDisposition.PENDING
                    or item.job.superseded_by_receipt_id == request.supersession_receipt_id
                )
            )
            pending = tuple(item for item in superseded if item.job.disposition is JobDisposition.PENDING)
            supersession_value = self._supersession_value(request, affected_receipts, receipt_records)
            corrective = self._corrective_jobs(request)
            replay = self._replay(request, supersession_value, affected_receipts, affected_jobs, superseded, corrective)
            if replay is not None:
                return replay
            participants = [
                self._receipts.create_participant(request.supersession_receipt_id, supersession_value)[1],
                *(self._jobs.replacement_participant(self._superseded(item, request), item.token) for item in pending),
                *(self._jobs.create_participant(job) for job in corrective),
            ]
            transaction = RuntimeTransaction(
                self._work_root,
                f"invalidation-{request.invalidation_id}",
                tuple(participants),
            )
            try:
                transaction.commit(failure=failure)
            except TransactionConflictError:
                with contextlib.suppress(TransactionConflictError):
                    transaction.abort()
                return self._diagnostic(InvalidationDiagnosticCode.CONFLICT, "invalidation identity conflicts")
            except Exception:  # noqa: BLE001 - any injected live-operation failure must abort prepared state.
                try:
                    transaction.abort()
                except TransactionConflictError:
                    return self._diagnostic(InvalidationDiagnosticCode.CONFLICT, "invalidation abort conflicts")
                return self._diagnostic(InvalidationDiagnosticCode.ABORTED, "invalidation publication aborted")
            return self._outcome(request, affected_receipts, affected_jobs, pending, corrective)
        except (FileNotFoundError, TypeError, ValueError) as exc:
            return self._diagnostic(InvalidationDiagnosticCode.REFERENCE_INVALID, str(exc))

    @staticmethod
    def _diagnostic(code: InvalidationDiagnosticCode, detail: str) -> InvalidationResult:
        return InvalidationResult(diagnostic=InvalidationDiagnostic(code=code, detail=detail))

    def _receipt_records(self) -> dict[str, ReceiptRecord]:
        results = self._receipts.list()
        if any(result.receipt is None for result in results):
            msg = "receipt storage contains invalid records"
            raise ValueError(msg)
        return {result.receipt.receipt_id: result.receipt for result in results if result.receipt is not None}

    def _validate_request_references(
        self,
        request: InvalidationRequest,
        receipts: Mapping[str, ReceiptRecord],
    ) -> None:
        for receipt_id in request.invalidated_receipt_ids:
            receipt = receipts.get(receipt_id)
            if receipt is None or receipt.kind in {"admission", "supersession"}:
                msg = f"invalidated receipt is not a current purpose receipt: {receipt_id}"
                raise ValueError(msg)
        for route in request.routes:
            result = self._findings.read(route.finding_id)
            finding = result.finding
            if (
                finding is None
                or finding.change_id != self._revision.change_id
                or finding.delivery_digest != self._revision.delivery_digest
                or finding.finding_class != route.finding_class
            ):
                msg = f"corrective route finding is invalid: {route.finding_id}"
                raise ValueError(msg)

    def _supersession_value(
        self,
        request: InvalidationRequest,
        affected: tuple[str, ...],
        receipts: Mapping[str, ReceiptRecord],
    ) -> dict[str, object]:
        closures = tuple(receipts[receipt_id].impact_closure for receipt_id in affected)
        if any(closure is None for closure in closures):
            msg = "affected receipt has no impact closure"
            raise ValueError(msg)
        paths = sorted({path for closure in closures if closure is not None for path in closure.paths})
        targets = sorted(
            {target for closure in closures if closure is not None for target in closure.authority_targets}
        )
        return {
            "schema_version": 1,
            "kind": "supersession",
            "receipt_id": request.supersession_receipt_id,
            "change_id": self._revision.change_id,
            "delivery_digest": self._revision.delivery_digest,
            "issued_at": request.issued_at,
            "impact_closure": {"paths": paths, "authority_targets": targets},
            "invalidation_id": request.invalidation_id,
            "invalidated_receipt_ids": list(affected),
            "corrective_finding_ids": sorted(route.finding_id for route in request.routes),
            "corrective_job_ids": list(request.corrective_job_ids),
            "predecessor_receipt_ids": list(request.invalidated_receipt_ids),
            "evidence": {"finding_ids": sorted(route.finding_id for route in request.routes)},
            "code_revision": request.code_revision,
        }

    def _corrective_jobs(self, request: InvalidationRequest) -> tuple[JobRecord, ...]:
        planned = tuple((route.finding_id, job) for route in request.routes for job in route.jobs)
        jobs: list[JobRecord] = []
        for job_id, (finding_id, plan) in zip(request.corrective_job_ids, planned, strict=True):
            job = JobRecord(
                schema_version=1,
                job_id=job_id,
                kind=plan.kind,
                priority=request.priority,
                created_at=request.issued_at,
                updated_at=request.issued_at,
                change_id=self._revision.change_id,
                delivery_digest=self._revision.delivery_digest,
                target_node_id=plan.target_node_id,
                finding_id=finding_id,
                receipt_id=request.supersession_receipt_id,
            )
            jobs.append(job)
        return tuple(jobs)

    @staticmethod
    def _superseded(stored: StoredJob, request: InvalidationRequest) -> JobRecord:
        return stored.job.model_copy(
            update={
                "claim_id": None,
                "attempt_id": None,
                "updated_at": request.issued_at,
                "superseded_by_receipt_id": request.supersession_receipt_id,
                "disposition": JobDisposition.SUPERSEDED,
            }
        )

    def _replay(  # noqa: PLR0913 - replay compares the complete prepared identity.
        self,
        request: InvalidationRequest,
        receipt_value: Mapping[str, object],
        affected_receipts: tuple[str, ...],
        affected_jobs: tuple[int, ...],
        active: tuple[StoredJob, ...],
        corrective: tuple[JobRecord, ...],
    ) -> InvalidationResult | None:
        existing = self._receipts.read(request.supersession_receipt_id).receipt
        if existing is None:
            return None
        expected = ReceiptRecord.from_mapping(receipt_value)
        if existing != expected:
            return self._diagnostic(InvalidationDiagnosticCode.CONFLICT, "invalidation identity conflicts")
        try:
            stored_corrective = tuple(self._jobs.read(job.job_id) for job in corrective)
        except FileNotFoundError:
            return self._diagnostic(InvalidationDiagnosticCode.CONFLICT, "corrective identity is incomplete")
        if tuple(item.job for item in stored_corrective) != corrective:
            return self._diagnostic(InvalidationDiagnosticCode.CONFLICT, "corrective identity conflicts")
        superseded = tuple(self._jobs.read(item.job.job_id) for item in active)
        if any(
            item.job.disposition is not JobDisposition.SUPERSEDED
            or item.job.superseded_by_receipt_id != request.supersession_receipt_id
            for item in superseded
        ):
            return self._diagnostic(InvalidationDiagnosticCode.CONFLICT, "stale job disposition conflicts")
        return InvalidationResult(
            outcome=InvalidationOutcome(
                invalidation_id=request.invalidation_id,
                supersession_receipt=existing,
                affected_receipt_ids=affected_receipts,
                affected_job_ids=affected_jobs,
                superseded_jobs=superseded,
                corrective_jobs=stored_corrective,
            )
        )

    def _outcome(
        self,
        request: InvalidationRequest,
        affected_receipts: tuple[str, ...],
        affected_jobs: tuple[int, ...],
        active: tuple[StoredJob, ...],
        corrective: tuple[JobRecord, ...],
    ) -> InvalidationResult:
        receipt = self._receipts.read(request.supersession_receipt_id).receipt
        if receipt is None:
            msg = "supersession receipt was not published"
            raise RuntimeError(msg)
        return InvalidationResult(
            outcome=InvalidationOutcome(
                invalidation_id=request.invalidation_id,
                supersession_receipt=receipt,
                affected_receipt_ids=affected_receipts,
                affected_job_ids=affected_jobs,
                superseded_jobs=tuple(self._jobs.read(item.job.job_id) for item in active),
                corrective_jobs=tuple(self._jobs.read(job.job_id) for job in corrective),
            )
        )


def _receipt_closure(roots: Iterable[str], receipts: Mapping[str, ReceiptRecord]) -> tuple[str, ...]:
    affected = set(roots)
    queue = deque(sorted(affected))
    while queue:
        current = queue.popleft()
        for receipt in receipts.values():
            predecessors = receipt.payload.get("predecessor_receipt_ids") or ()
            if receipt.kind != "supersession" and receipt.receipt_id not in affected and current in predecessors:
                affected.add(receipt.receipt_id)
                queue.append(receipt.receipt_id)
    return tuple(sorted(affected))


def _job_closure(affected_receipts: tuple[str, ...], jobs: tuple[StoredJob, ...]) -> tuple[int, ...]:
    by_id = {item.job.job_id: item.job for item in jobs}
    affected = {
        job_id
        for job_id, job in by_id.items()
        if job.receipt_id in affected_receipts
        or any(
            by_id.get(predecessor) and by_id[predecessor].receipt_id in affected_receipts
            for predecessor in job.predecessor_job_ids
        )
    }
    queue = deque(sorted(affected))
    while queue:
        current = queue.popleft()
        for job in by_id.values():
            if job.job_id not in affected and current in job.predecessor_job_ids:
                affected.add(job.job_id)
                queue.append(job.job_id)
    return tuple(sorted(affected))


__all__ = [
    "CorrectiveJobPlan",
    "CorrectiveRoute",
    "CorrectiveRouteRequest",
    "InvalidationDiagnostic",
    "InvalidationDiagnosticCode",
    "InvalidationOutcome",
    "InvalidationRequest",
    "InvalidationResult",
    "InvalidationRuntime",
    "plan_corrective_route",
]
