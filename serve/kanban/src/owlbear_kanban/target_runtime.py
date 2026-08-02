"""Dormant target execution contracts and runtime kernel."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Literal, Never

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, TypeAdapter, model_validator

from owlbear_kanban.attempts import AttemptEvent, AttemptStore
from owlbear_kanban.change import ChangeId, Digest
from owlbear_kanban.runtime_transaction import (
    ReplacementTransactionParticipant,
    RuntimeTransaction,
    TransactionParticipant,
)
from owlbear_kanban.work_items import TaskProgress, WorkItemEvidence

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_kanban.target_authority import TargetAuthority

RuntimeId = Annotated[str, StringConstraints(strict=True, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")]
CommitSha = Annotated[str, StringConstraints(strict=True, pattern=r"^[0-9a-f]{40}$")]
TargetJobKind = Literal["plan", "build", "assembly"]


class TargetJobState(StrEnum):
    """Target job states without manually controlled cancellation."""

    PENDING = "pending"
    ACTIVE = "active"
    RETURNED = "returned"
    COMPLETED = "completed"


class ReturnLevel(StrEnum):
    """Typed correction destination for a failed claim."""

    IMPLEMENTATION_ATTEMPT = "implementation-attempt"
    TASK_PLAN = "task-plan"
    SOLUTION_PLAN = "solution-plan"
    DESIGN = "design"


class ReviewDisposition(StrEnum):
    """Independent disposition for one transformation claim."""

    ACCEPTABLE = "acceptable"
    REPAIR = "repair"
    RESTART = "restart"
    TASK_PLAN = "task-plan"
    SOLUTION_PLAN = "solution-plan"
    DESIGN = "design"


class _TargetModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class TargetJob(_TargetModel):
    """One immutable transformation identity with derived runtime state."""

    schema_version: Literal[1] = 1
    job_id: int = Field(gt=0)
    kind: TargetJobKind
    change_id: ChangeId
    authority_digest: Digest
    work_item_id: str = Field(min_length=1)
    plan_scope_id: str = Field(min_length=1)
    task_id: str | None = None
    predecessor_job_ids: tuple[int, ...] = ()
    created_at: str = Field(min_length=1)
    state: TargetJobState = TargetJobState.PENDING
    active_attempt_id: RuntimeId | None = None
    receipt_id: RuntimeId | None = None
    return_level: ReturnLevel | None = None
    excluded_reviewer_ids: tuple[RuntimeId, ...] = ()

    @model_validator(mode="after")
    def _validate_kind_and_state(self) -> TargetJob:
        if (self.kind == "build") != (self.task_id is not None):
            msg = "only build jobs require a task identity"
            raise ValueError(msg)
        if (self.state == TargetJobState.ACTIVE) != (self.active_attempt_id is not None):
            msg = "only active jobs require an attempt identity"
            raise ValueError(msg)
        if (self.state == TargetJobState.COMPLETED) != (self.receipt_id is not None):
            msg = "only completed jobs require a receipt identity"
            raise ValueError(msg)
        if (self.state == TargetJobState.RETURNED) != (self.return_level is not None):
            msg = "only returned jobs require a return level"
            raise ValueError(msg)
        return self


class StartTargetJobRequest(_TargetModel):
    """Claim one ready target job with an independent reviewer."""

    action: Literal["start"] = "start"
    job_id: int = Field(gt=0)
    attempt_id: RuntimeId
    claim_id: RuntimeId
    owner_id: RuntimeId
    reviewer_id: RuntimeId
    process_id: RuntimeId
    started_at: str = Field(min_length=1)
    lease_expires_at: str = Field(min_length=1)


class FinishTargetJobRequest(_TargetModel):
    """Submit candidate evidence and one independent review disposition."""

    action: Literal["finish"] = "finish"
    job_id: int = Field(gt=0)
    attempt_id: RuntimeId
    claim_id: RuntimeId
    owner_id: RuntimeId
    reviewer_id: RuntimeId
    review_id: RuntimeId
    receipt_id: RuntimeId | None = None
    candidate_commit: CommitSha
    reviewed_at: str = Field(min_length=1)
    disposition: ReviewDisposition
    claim: str = Field(min_length=1)
    evidence: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_receipt_identity(self) -> FinishTargetJobRequest:
        if (self.disposition == ReviewDisposition.ACCEPTABLE) != (self.receipt_id is not None):
            msg = "only acceptable reviews require a receipt identity"
            raise ValueError(msg)
        return self


class RecoverInterruptedTaskRequest(_TargetModel):
    """Recover one exact task only after its owning process is known dead."""

    action: Literal["recover-interrupted"] = "recover-interrupted"
    job_id: int = Field(gt=0)
    attempt_id: RuntimeId
    claim_id: RuntimeId
    process_id: RuntimeId
    recovered_at: str = Field(min_length=1)


class RespondToReviewRequest(_TargetModel):
    """Provide the single owner evidence response allowed for one disagreement."""

    action: Literal["respond-to-review"] = "respond-to-review"
    job_id: int = Field(gt=0)
    attempt_id: RuntimeId
    claim_id: RuntimeId
    owner_id: RuntimeId
    response_id: RuntimeId
    responded_at: str = Field(min_length=1)
    evidence: tuple[str, ...] = Field(min_length=1)


class ArbitrateTargetAttemptRequest(_TargetModel):
    """Record one final arbiter disposition for a concrete disagreement."""

    action: Literal["arbitrate"] = "arbitrate"
    job_id: int = Field(gt=0)
    attempt_id: RuntimeId
    claim_id: RuntimeId
    arbiter_id: RuntimeId
    decision_id: RuntimeId
    receipt_id: RuntimeId | None = None
    decided_at: str = Field(min_length=1)
    disposition: Literal["acceptable", "restart", "task-plan", "solution-plan", "design"]
    rationale: str = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_receipt_identity(self) -> ArbitrateTargetAttemptRequest:
        if (self.disposition == "acceptable") != (self.receipt_id is not None):
            msg = "only acceptable arbitration requires a receipt identity"
            raise ValueError(msg)
        return self


type TargetMutation = Annotated[
    StartTargetJobRequest
    | FinishTargetJobRequest
    | RecoverInterruptedTaskRequest
    | RespondToReviewRequest
    | ArbitrateTargetAttemptRequest,
    Field(discriminator="action"),
]
TARGET_MUTATION_ADAPTER = TypeAdapter(TargetMutation)


class TargetTask(_TargetModel):
    """One accepted task under a reviewed plan scope."""

    task_id: str = Field(min_length=1)
    work_item_id: str = Field(min_length=1)
    plan_scope_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    reviewed: bool = False
    build_receipt_id: RuntimeId | None = None

    @model_validator(mode="after")
    def _validate_reviewed_receipt(self) -> TargetTask:
        if self.reviewed != (self.build_receipt_id is not None):
            msg = "reviewed tasks require exactly one build receipt"
            raise ValueError(msg)
        return self


class TargetReview(_TargetModel):
    """One immutable reviewer decision nested beneath an attempt."""

    review_id: RuntimeId
    reviewer_id: RuntimeId
    candidate_commit: CommitSha
    reviewed_at: str = Field(min_length=1)
    disposition: ReviewDisposition
    claim: str = Field(min_length=1)
    evidence: tuple[str, ...] = Field(min_length=1)


class TargetEvidenceResponse(_TargetModel):
    """The sole owner evidence response permitted for one disagreement."""

    response_id: RuntimeId
    owner_id: RuntimeId
    responded_at: str = Field(min_length=1)
    evidence: tuple[str, ...] = Field(min_length=1)


class TargetArbiterDecision(_TargetModel):
    """One final isolated arbiter decision."""

    decision_id: RuntimeId
    arbiter_id: RuntimeId
    decided_at: str = Field(min_length=1)
    disposition: Literal["acceptable", "restart", "task-plan", "solution-plan", "design"]
    rationale: str = Field(min_length=1)


class TargetAttemptState(StrEnum):
    """Attempt states derived from immutable nested evidence."""

    ACTIVE = "active"
    REPAIR = "repair"
    RESTARTED = "restarted"
    RETURNED = "returned"
    CRASHED = "crashed"
    SUCCEEDED = "succeeded"


class TargetAttempt(_TargetModel):
    """One transformation attempt and its nested assurance evidence."""

    attempt_id: RuntimeId
    claim_id: RuntimeId
    job_id: int = Field(gt=0)
    owner_id: RuntimeId
    reviewer_id: RuntimeId
    process_id: RuntimeId
    started_at: str = Field(min_length=1)
    lease_expires_at: str = Field(min_length=1)
    state: TargetAttemptState = TargetAttemptState.ACTIVE
    reviews: tuple[TargetReview, ...] = ()
    evidence_response: TargetEvidenceResponse | None = None
    arbiter_decision: TargetArbiterDecision | None = None


class TargetRequestStatus(StrEnum):
    """Target request resolution state."""

    PENDING = "pending"
    RESOLVED = "resolved"


class TargetRequest(_TargetModel):
    """One request scoped to a commitment and semantic work item."""

    request_id: RuntimeId
    change_id: ChangeId
    authority_digest: Digest
    work_item_id: str = Field(min_length=1)
    commitment_id: str = Field(min_length=1)
    task_id: str | None = None
    created_at: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    status: TargetRequestStatus = TargetRequestStatus.PENDING
    resolved_at: str | None = None

    @model_validator(mode="after")
    def _validate_resolution(self) -> TargetRequest:
        if (self.status == TargetRequestStatus.RESOLVED) != (self.resolved_at is not None):
            msg = "resolved requests require a resolution timestamp"
            raise ValueError(msg)
        return self


class TargetReceipt(_TargetModel):
    """Immutable evidence closing one reviewed target transformation."""

    schema_version: Literal[1] = 1
    receipt_id: RuntimeId
    kind: TargetJobKind
    job_id: int = Field(gt=0)
    change_id: ChangeId
    authority_digest: Digest
    work_item_id: str = Field(min_length=1)
    plan_scope_id: str = Field(min_length=1)
    task_id: str | None = None
    attempt_id: RuntimeId
    candidate_commit: CommitSha
    reviewer_id: RuntimeId
    arbiter_id: RuntimeId | None = None
    issued_at: str = Field(min_length=1)
    claim: str = Field(min_length=1)
    evidence: tuple[str, ...] = Field(min_length=1)


class StartedTargetJob(_TargetModel):
    """One successfully claimed target job and its attempt."""

    job: TargetJob
    attempt: TargetAttempt


class FinishedTargetJob(_TargetModel):
    """One reviewed transition and its optional closing receipt."""

    job: TargetJob
    attempt: TargetAttempt
    receipt: TargetReceipt | None = None


class _ClosingEvidence(_TargetModel):
    disposition: ReviewDisposition
    receipt_id: str | None
    timestamp: str
    candidate_commit: str
    claim: str
    evidence: tuple[str, ...]
    arbiter_id: str | None = None


class _AttemptEventContext(_TargetModel):
    timestamp: str
    evidence_ids: tuple[str, ...] = ()
    detail: str | None = None


class TargetRuntimeState(_TargetModel):
    """One OCC-replaced target execution snapshot with immutable evidence links."""

    schema_version: Literal[1] = 1
    jobs: tuple[TargetJob, ...] = ()
    tasks: tuple[TargetTask, ...] = ()
    attempts: tuple[TargetAttempt, ...] = ()
    requests: tuple[TargetRequest, ...] = ()
    receipts: tuple[TargetReceipt, ...] = ()

    @model_validator(mode="after")
    def _validate_identities(self) -> TargetRuntimeState:
        _require_unique(self.jobs, "job_id", "job")
        _require_unique(self.tasks, "task_id", "task")
        _require_unique(self.attempts, "attempt_id", "attempt")
        _require_unique(self.requests, "request_id", "request")
        _require_unique(self.receipts, "receipt_id", "receipt")
        return self


class TargetRuntimeConflictError(RuntimeError):
    """Target runtime state conflicts with the requested transition."""

    code = "ERR_TARGET_RUNTIME_CONFLICT"


class TargetRuntimeReferenceError(ValueError):
    """Target runtime input references absent or stale authority."""

    code = "ERR_TARGET_RUNTIME_REFERENCE"


class TargetRecoveryError(RuntimeError):
    """Interrupted-task recovery could not prove the prior session dead."""

    code = "ERR_TARGET_RECOVERY_GUARD"


class _TargetRuntimeStore:
    """OCC replacement for mutable state plus immutable receipt and attempt files."""

    def __init__(self, work_root: Path) -> None:
        self._work_root = work_root
        self._state_path = work_root / "target-runtime" / "state.json"
        self._attempts = AttemptStore(work_root)
        work_root.mkdir(parents=True, exist_ok=True)

    def initialize(self, state: TargetRuntimeState) -> None:
        content = _state_content(state)
        if self._state_path.exists():
            if self._state_path.read_bytes() != content:
                _conflict("target runtime is already initialized differently")
            return
        self._commit(
            "initialize",
            (TransactionParticipant(self._work_root, Path("target-runtime/state.json"), content),),
        )

    def read(self) -> tuple[TargetRuntimeState, bytes]:
        try:
            content = self._state_path.read_bytes()
        except FileNotFoundError as exc:
            _reference("target runtime is not initialized", exc)
        return TargetRuntimeState.model_validate_json(content), content

    def replace(
        self,
        previous: bytes,
        state: TargetRuntimeState,
        *,
        receipt: TargetReceipt | None = None,
        attempt_events: tuple[AttemptEvent, ...] = (),
    ) -> None:
        participants: list[TransactionParticipant | ReplacementTransactionParticipant] = [
            ReplacementTransactionParticipant(
                self._work_root,
                Path("target-runtime/state.json"),
                previous,
                _state_content(state),
            )
        ]
        if receipt is not None:
            participants.append(
                TransactionParticipant(
                    self._work_root,
                    Path("target-runtime/receipts") / f"{receipt.receipt_id}.json",
                    _model_content(receipt),
                )
            )
        participants.extend(self._attempts.create_participant(event) for event in attempt_events)
        transaction_id = hashlib.sha256(b"".join(_participant_content(item) for item in participants)).hexdigest()
        self._commit(transaction_id, tuple(participants))

    def _commit(
        self,
        transaction_id: str,
        participants: tuple[TransactionParticipant | ReplacementTransactionParticipant, ...],
    ) -> None:
        RuntimeTransaction(self._work_root, f"target-{transaction_id}", participants).commit()


class TargetRuntime:
    """Persist and derive the dormant three-transformation target runtime."""

    def __init__(self, authority: TargetAuthority, work_root: Path) -> None:
        self._authority = authority
        self._authority_digest = hashlib.sha256(_model_content(authority)).hexdigest()
        self._store = _TargetRuntimeStore(work_root)

    @property
    def authority_digest(self) -> str:
        """Return the exact semantic authority identity consumed by this runtime."""
        return self._authority_digest

    def materialize(self, jobs: tuple[TargetJob, ...], tasks: tuple[TargetTask, ...] = ()) -> None:
        """Create an exact initial runtime snapshot, replaying only identical content."""
        self._validate_materialization(jobs, tasks)
        self._store.initialize(TargetRuntimeState(jobs=jobs, tasks=tasks))

    def show_job(self, job_id: int) -> TargetJob:
        """Return one current target job projection."""
        state, _previous = self._store.read()
        return _find(state.jobs, "job_id", job_id, "job")

    def show_attempt(self, attempt_id: str) -> TargetAttempt:
        """Return one attempt with nested review evidence."""
        state, _previous = self._store.read()
        return _find(state.attempts, "attempt_id", attempt_id, "attempt")

    def show_receipt(self, receipt_id: str) -> TargetReceipt:
        """Return one immutable target receipt."""
        state, _previous = self._store.read()
        return _find(state.receipts, "receipt_id", receipt_id, "receipt")

    def list_frontier(self) -> tuple[TargetJob, ...]:
        """Return pending dependency-ready jobs outside the blocked semantic slice."""
        state, _previous = self._store.read()
        completed = {job.job_id for job in state.jobs if job.state == TargetJobState.COMPLETED}
        blocked = self._blocked_work_items(state)
        ready = (
            job
            for job in state.jobs
            if job.state == TargetJobState.PENDING
            and job.work_item_id not in blocked
            and set(job.predecessor_job_ids) <= completed
        )
        return tuple(sorted(ready, key=lambda job: (job.created_at, job.job_id)))

    def create_request(self, request: TargetRequest) -> TargetRequest:
        """Persist one current-authority request without creating a global checkpoint."""
        state, previous = self._store.read()
        self._validate_request(request, state)
        existing = next((item for item in state.requests if item.request_id == request.request_id), None)
        if existing is not None:
            if existing != request:
                _conflict("request identity already contains different evidence")
            return existing
        updated = state.model_copy(update={"requests": (*state.requests, request)})
        self._store.replace(previous, updated)
        return request

    def resolve_request(self, request_id: str, resolved_at: str) -> TargetRequest:
        """Resolve one pending request while retaining its immutable semantic target."""
        state, previous = self._store.read()
        request = _find(state.requests, "request_id", request_id, "request")
        if request.status != TargetRequestStatus.PENDING:
            _conflict("request is already resolved")
        resolved = request.model_copy(update={"status": TargetRequestStatus.RESOLVED, "resolved_at": resolved_at})
        updated = state.model_copy(update={"requests": _replace(state.requests, request, resolved)})
        self._store.replace(previous, updated)
        return resolved

    def start_job(self, request: StartTargetJobRequest) -> StartedTargetJob:
        """Claim one ready transformation with its independent reviewer."""
        state, previous = self._store.read()
        job = _find(state.jobs, "job_id", request.job_id, "job")
        if job not in self.list_frontier():
            _conflict("job is not ready")
        self._validate_start_identity(state, job, request)
        attempt = TargetAttempt(
            attempt_id=request.attempt_id,
            claim_id=request.claim_id,
            job_id=job.job_id,
            owner_id=request.owner_id,
            reviewer_id=request.reviewer_id,
            process_id=request.process_id,
            started_at=request.started_at,
            lease_expires_at=request.lease_expires_at,
        )
        active = job.model_copy(update={"state": TargetJobState.ACTIVE, "active_attempt_id": request.attempt_id})
        updated = state.model_copy(
            update={"jobs": _replace(state.jobs, job, active), "attempts": (*state.attempts, attempt)}
        )
        self._store.replace(previous, updated, attempt_events=(self._attempt_event(job, attempt, "started"),))
        return StartedTargetJob(job=active, attempt=attempt)

    def finish_job(self, request: FinishTargetJobRequest) -> FinishedTargetJob:
        """Apply one nested independent review to an active attempt."""
        state, previous = self._store.read()
        job, attempt = self._active_attempt(state, request.job_id, request.attempt_id, request.claim_id)
        self._validate_review(state, attempt, request)
        review = TargetReview(
            review_id=request.review_id,
            reviewer_id=request.reviewer_id,
            candidate_commit=request.candidate_commit,
            reviewed_at=request.reviewed_at,
            disposition=request.disposition,
            claim=request.claim,
            evidence=request.evidence,
        )
        reviewed = attempt.model_copy(update={"reviews": (*attempt.reviews, review)})
        transition = self._review_transition(state, job, reviewed, request)
        self._store.replace(
            previous,
            transition[0],
            receipt=transition[3],
            attempt_events=(transition[4],) if transition[4] is not None else (),
        )
        return FinishedTargetJob(job=transition[1], attempt=transition[2], receipt=transition[3])

    def respond_to_review(self, request: RespondToReviewRequest) -> TargetAttempt:
        """Record the single evidence response before final arbitration."""
        state, previous = self._store.read()
        _job, attempt = self._active_attempt(state, request.job_id, request.attempt_id, request.claim_id)
        if attempt.owner_id != request.owner_id or attempt.state != TargetAttemptState.REPAIR:
            _conflict("attempt is not awaiting its owner's evidence response")
        if attempt.evidence_response is not None:
            _conflict("attempt already has its one evidence response")
        response = TargetEvidenceResponse(
            response_id=request.response_id,
            owner_id=request.owner_id,
            responded_at=request.responded_at,
            evidence=request.evidence,
        )
        responded = attempt.model_copy(update={"evidence_response": response})
        updated = state.model_copy(update={"attempts": _replace(state.attempts, attempt, responded)})
        self._store.replace(previous, updated)
        return responded

    def arbitrate(self, request: ArbitrateTargetAttemptRequest) -> FinishedTargetJob:
        """Apply the sole final arbiter decision for an unresolved attempt."""
        state, previous = self._store.read()
        job, attempt = self._active_attempt(state, request.job_id, request.attempt_id, request.claim_id)
        self._validate_arbitration(attempt, request)
        decision = TargetArbiterDecision(
            decision_id=request.decision_id,
            arbiter_id=request.arbiter_id,
            decided_at=request.decided_at,
            disposition=request.disposition,
            rationale=request.rationale,
        )
        arbitrated = attempt.model_copy(update={"arbiter_decision": decision})
        transition = self._arbiter_transition(state, job, arbitrated, request)
        self._store.replace(
            previous,
            transition[0],
            receipt=transition[3],
            attempt_events=(transition[4],),
        )
        return FinishedTargetJob(job=transition[1], attempt=transition[2], receipt=transition[3])

    def recover_expired_claims(self, recovered_at: str) -> tuple[TargetJob, ...]:
        """Recover every expired active attempt with deterministic crash evidence."""
        state, previous = self._store.read()
        recovered: list[TargetJob] = []
        events: list[AttemptEvent] = []
        updated = state
        for attempt in state.attempts:
            if attempt.state not in {TargetAttemptState.ACTIVE, TargetAttemptState.REPAIR}:
                continue
            if _timestamp(attempt.lease_expires_at) > _timestamp(recovered_at):
                continue
            updated, job, event = self._crash_attempt(updated, attempt, recovered_at, "claim expired")
            recovered.append(job)
            events.append(event)
        if recovered:
            self._store.replace(previous, updated, attempt_events=tuple(events))
        return tuple(recovered)

    def recover_interrupted_task(
        self,
        request: RecoverInterruptedTaskRequest,
        *,
        process_is_alive: Callable[[str], bool],
    ) -> TargetJob:
        """Recover one exact attempt only after its recorded process is proven dead."""
        state, previous = self._store.read()
        _job, attempt = self._active_attempt(state, request.job_id, request.attempt_id, request.claim_id)
        if attempt.process_id != request.process_id or process_is_alive(attempt.process_id):
            _recovery_failure("recorded owner process is not proven dead")
        updated, pending, event = self._crash_attempt(state, attempt, request.recovered_at, "owner process died")
        self._store.replace(previous, updated, attempt_events=(event,))
        return pending

    def work_item_evidence(self) -> WorkItemEvidence:
        """Project runtime records into the T1 evidence contract."""
        state, _previous = self._store.read()
        planned = tuple(
            job.plan_scope_id for job in state.jobs if job.kind == "plan" and job.state == TargetJobState.COMPLETED
        )
        assembly = tuple(
            job.plan_scope_id for job in state.jobs if job.kind == "assembly" and job.state == TargetJobState.COMPLETED
        )
        progress = tuple(
            TaskProgress(
                scope_id=scope_id,
                task_count=sum(task.plan_scope_id == scope_id for task in state.tasks),
                reviewed_task_count=sum(task.plan_scope_id == scope_id and task.reviewed for task in state.tasks),
            )
            for scope_id in sorted({task.plan_scope_id for task in state.tasks})
        )
        pending = tuple(
            request.work_item_id
            for request in state.requests
            if request.status == TargetRequestStatus.PENDING and request.authority_digest == self.authority_digest
        )
        return WorkItemEvidence(
            planned_scope_ids=planned,
            task_progress=progress,
            completed_assembly_scope_ids=assembly,
            pending_request_work_item_ids=pending,
        )

    def _validate_materialization(self, jobs: tuple[TargetJob, ...], tasks: tuple[TargetTask, ...]) -> None:
        work_items = {self._authority.change_id, *(item.outcome_id for item in self._authority.outcomes)}
        scopes = {item.scope_id: item for item in self._authority.task_plan_scopes}
        task_index = {item.task_id: item for item in tasks}
        for job in jobs:
            if job.change_id != self._authority.change_id or job.authority_digest != self.authority_digest:
                _reference("job authority identity is stale")
            if job.work_item_id not in work_items or job.plan_scope_id not in scopes:
                _reference("job target is absent from authority")
            if scopes[job.plan_scope_id].target_id != job.work_item_id:
                _reference("job scope does not own its work item")
            if job.kind == "build" and job.task_id not in task_index:
                _reference("build task is absent")
        for task in tasks:
            if task.work_item_id not in work_items or task.plan_scope_id not in scopes:
                _reference("task target is absent from authority")

    def _validate_request(self, request: TargetRequest, state: TargetRuntimeState) -> None:
        outcomes = {item.outcome_id for item in self._authority.outcomes}
        commitments = {item.commitment_id for item in self._authority.commitments}
        if request.change_id != self._authority.change_id or request.authority_digest != self.authority_digest:
            _reference("request authority identity is stale")
        if request.work_item_id not in outcomes or request.commitment_id not in commitments:
            _reference("request semantic target is absent")
        if request.task_id is not None:
            task = _find(state.tasks, "task_id", request.task_id, "task")
            if task.work_item_id != request.work_item_id:
                _reference("request task belongs to another work item")

    def _validate_start_identity(
        self, state: TargetRuntimeState, job: TargetJob, request: StartTargetJobRequest
    ) -> None:
        if request.owner_id == request.reviewer_id or request.reviewer_id in job.excluded_reviewer_ids:
            _conflict("reviewer is not independent for this attempt")
        if any(item.attempt_id == request.attempt_id for item in state.attempts):
            _conflict("attempt identity already exists")
        if any(item.claim_id == request.claim_id for item in state.attempts):
            _conflict("claim identity already exists")

    def _validate_review(
        self, state: TargetRuntimeState, attempt: TargetAttempt, request: FinishTargetJobRequest
    ) -> None:
        if attempt.owner_id != request.owner_id or attempt.reviewer_id != request.reviewer_id:
            _conflict("review does not match attempt ownership")
        if attempt.evidence_response is not None or attempt.arbiter_decision is not None:
            _conflict("review cycle is closed for arbitration")
        if attempt.state not in {TargetAttemptState.ACTIVE, TargetAttemptState.REPAIR}:
            _conflict("attempt does not accept another review")
        if any(review.review_id == request.review_id for item in state.attempts for review in item.reviews):
            _conflict("review identity already exists")

    def _validate_arbitration(self, attempt: TargetAttempt, request: ArbitrateTargetAttemptRequest) -> None:
        if attempt.state != TargetAttemptState.REPAIR or attempt.evidence_response is None:
            _conflict("attempt has no unresolved reviewed disagreement")
        if attempt.arbiter_decision is not None:
            _conflict("attempt already has a final arbiter decision")
        if request.arbiter_id in {attempt.owner_id, attempt.reviewer_id}:
            _conflict("arbiter must be isolated from owner and reviewer")

    def _active_attempt(
        self, state: TargetRuntimeState, job_id: int, attempt_id: str, claim_id: str
    ) -> tuple[TargetJob, TargetAttempt]:
        job = _find(state.jobs, "job_id", job_id, "job")
        attempt = _find(state.attempts, "attempt_id", attempt_id, "attempt")
        if (
            job.state != TargetJobState.ACTIVE
            or job.active_attempt_id != attempt.attempt_id
            or attempt.job_id != job.job_id
            or attempt.claim_id != claim_id
        ):
            _conflict("attempt does not own the active job claim")
        return job, attempt

    def _review_transition(
        self,
        state: TargetRuntimeState,
        job: TargetJob,
        attempt: TargetAttempt,
        request: FinishTargetJobRequest,
    ) -> tuple[TargetRuntimeState, TargetJob, TargetAttempt, TargetReceipt | None, AttemptEvent | None]:
        if request.disposition == ReviewDisposition.REPAIR:
            repairing = attempt.model_copy(update={"state": TargetAttemptState.REPAIR})
            updated = state.model_copy(update={"attempts": _replace(state.attempts, attempt, repairing)})
            return updated, job, repairing, None, None
        return self._close_attempt(
            state,
            job,
            attempt,
            _ClosingEvidence(
                disposition=request.disposition,
                receipt_id=request.receipt_id,
                timestamp=request.reviewed_at,
                candidate_commit=request.candidate_commit,
                claim=request.claim,
                evidence=request.evidence,
            ),
        )

    def _arbiter_transition(
        self,
        state: TargetRuntimeState,
        job: TargetJob,
        attempt: TargetAttempt,
        request: ArbitrateTargetAttemptRequest,
    ) -> tuple[TargetRuntimeState, TargetJob, TargetAttempt, TargetReceipt | None, AttemptEvent]:
        last_review = attempt.reviews[-1]
        disposition = ReviewDisposition(request.disposition)
        result = self._close_attempt(
            state,
            job,
            attempt,
            _ClosingEvidence(
                disposition=disposition,
                receipt_id=request.receipt_id,
                timestamp=request.decided_at,
                candidate_commit=last_review.candidate_commit,
                claim=last_review.claim,
                evidence=(*last_review.evidence, request.rationale),
                arbiter_id=request.arbiter_id,
            ),
        )
        if result[4] is None:
            _conflict("arbiter disposition must terminate the attempt")
        return result[0], result[1], result[2], result[3], result[4]

    def _close_attempt(
        self,
        state: TargetRuntimeState,
        job: TargetJob,
        attempt: TargetAttempt,
        closing: _ClosingEvidence,
    ) -> tuple[TargetRuntimeState, TargetJob, TargetAttempt, TargetReceipt | None, AttemptEvent]:
        if closing.disposition == ReviewDisposition.ACCEPTABLE:
            receipt = self._target_receipt(job, attempt, closing)
            closed_job = _completed_job(job, receipt.receipt_id)
            closed_attempt = attempt.model_copy(update={"state": TargetAttemptState.SUCCEEDED})
            tasks = self._review_task(state.tasks, job, receipt.receipt_id)
            event_kind: Literal["succeeded", "failed"] = "succeeded"
        elif closing.disposition == ReviewDisposition.RESTART:
            receipt = None
            closed_job = _restarted_job(job, attempt.reviewer_id)
            closed_attempt = attempt.model_copy(update={"state": TargetAttemptState.RESTARTED})
            tasks = state.tasks
            event_kind = "failed"
        else:
            receipt = None
            level = ReturnLevel(closing.disposition.value)
            closed_job = _returned_job(job, level)
            closed_attempt = attempt.model_copy(update={"state": TargetAttemptState.RETURNED})
            tasks = state.tasks
            event_kind = "failed"
        updated = state.model_copy(
            update={
                "jobs": _replace(state.jobs, job, closed_job),
                "tasks": tasks,
                "attempts": _replace(state.attempts, attempt, closed_attempt),
                "receipts": (*state.receipts, receipt) if receipt is not None else state.receipts,
            }
        )
        context = _AttemptEventContext(
            timestamp=closing.timestamp,
            evidence_ids=(receipt.receipt_id,) if receipt is not None else (),
        )
        event = self._attempt_event(job, closed_attempt, event_kind, context)
        return updated, closed_job, closed_attempt, receipt, event

    def _target_receipt(
        self,
        job: TargetJob,
        attempt: TargetAttempt,
        closing: _ClosingEvidence,
    ) -> TargetReceipt:
        if closing.receipt_id is None:
            _conflict("acceptable disposition requires a receipt identity")
        return TargetReceipt(
            receipt_id=closing.receipt_id,
            kind=job.kind,
            job_id=job.job_id,
            change_id=job.change_id,
            authority_digest=job.authority_digest,
            work_item_id=job.work_item_id,
            plan_scope_id=job.plan_scope_id,
            task_id=job.task_id,
            attempt_id=attempt.attempt_id,
            candidate_commit=closing.candidate_commit,
            reviewer_id=attempt.reviewer_id,
            arbiter_id=closing.arbiter_id,
            issued_at=closing.timestamp,
            claim=closing.claim,
            evidence=closing.evidence,
        )

    @staticmethod
    def _review_task(tasks: tuple[TargetTask, ...], job: TargetJob, receipt_id: str) -> tuple[TargetTask, ...]:
        if job.kind != "build" or job.task_id is None:
            return tasks
        task = _find(tasks, "task_id", job.task_id, "task")
        reviewed = task.model_copy(update={"reviewed": True, "build_receipt_id": receipt_id})
        return _replace(tasks, task, reviewed)

    def _crash_attempt(
        self, state: TargetRuntimeState, attempt: TargetAttempt, timestamp: str, detail: str
    ) -> tuple[TargetRuntimeState, TargetJob, AttemptEvent]:
        job = _find(state.jobs, "job_id", attempt.job_id, "job")
        pending = job.model_copy(update={"state": TargetJobState.PENDING, "active_attempt_id": None})
        crashed = attempt.model_copy(update={"state": TargetAttemptState.CRASHED})
        updated = state.model_copy(
            update={
                "jobs": _replace(state.jobs, job, pending),
                "attempts": _replace(state.attempts, attempt, crashed),
            }
        )
        context = _AttemptEventContext(timestamp=timestamp, detail=detail)
        return updated, pending, self._attempt_event(job, crashed, "crashed", context)

    def _attempt_event(
        self,
        job: TargetJob,
        attempt: TargetAttempt,
        kind: Literal["started", "failed", "crashed", "succeeded"],
        context: _AttemptEventContext | None = None,
    ) -> AttemptEvent:
        terminal = kind != "started"
        return AttemptEvent(
            schema_version=1,
            attempt_id=attempt.attempt_id,
            claim_id=attempt.claim_id,
            job_id=job.job_id,
            change_id=job.change_id,
            delivery_digest=job.authority_digest,
            target_node_id=job.work_item_id,
            actor_id=attempt.owner_id,
            process_id=attempt.process_id,
            sequence=2 if terminal else 1,
            timestamp=context.timestamp if context is not None else attempt.started_at,
            kind=kind,
            detail=context.detail if context is not None else None,
            evidence_ids=context.evidence_ids if context is not None else (),
        )

    def _blocked_work_items(self, state: TargetRuntimeState) -> set[str]:
        blocked = {
            request.work_item_id
            for request in state.requests
            if request.status == TargetRequestStatus.PENDING and request.authority_digest == self.authority_digest
        }
        changed = True
        while changed:
            expanded = {
                outcome.outcome_id for outcome in self._authority.outcomes if set(outcome.dependency_ids) & blocked
            }
            changed = not expanded <= blocked
            blocked.update(expanded)
        return blocked


def _require_unique(items: tuple[BaseModel, ...], field: str, label: str) -> None:
    identities = [getattr(item, field) for item in items]
    if len(identities) != len(set(identities)):
        msg = f"{label} identities must be unique"
        raise ValueError(msg)


def _find[ItemT: BaseModel](items: tuple[ItemT, ...], field: str, identity: object, label: str) -> ItemT:
    try:
        return next(item for item in items if getattr(item, field) == identity)
    except StopIteration as exc:
        _reference(f"{label} is missing: {identity}", exc)


def _replace[ItemT: BaseModel](items: tuple[ItemT, ...], current: ItemT, replacement: ItemT) -> tuple[ItemT, ...]:
    current_identity = _model_identity(current)
    for index, item in enumerate(items):
        if item == current or _model_identity(item) == current_identity:
            return (*items[:index], replacement, *items[index + 1 :])
    msg = "replacement target is missing"
    raise TargetRuntimeReferenceError(msg)


def _model_identity(model: BaseModel) -> tuple[str, object]:
    for field in ("job_id", "task_id", "attempt_id", "request_id", "receipt_id"):
        if hasattr(model, field):
            return field, getattr(model, field)
    msg = "model has no runtime identity"
    raise TargetRuntimeReferenceError(msg)


def _timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        _reference("runtime timestamps require an explicit timezone")
    return parsed


def _completed_job(job: TargetJob, receipt_id: str) -> TargetJob:
    return job.model_copy(
        update={"state": TargetJobState.COMPLETED, "active_attempt_id": None, "receipt_id": receipt_id}
    )


def _restarted_job(job: TargetJob, reviewer_id: str) -> TargetJob:
    excluded = tuple(sorted({*job.excluded_reviewer_ids, reviewer_id}))
    return job.model_copy(
        update={"state": TargetJobState.PENDING, "active_attempt_id": None, "excluded_reviewer_ids": excluded}
    )


def _returned_job(job: TargetJob, level: ReturnLevel) -> TargetJob:
    return job.model_copy(update={"state": TargetJobState.RETURNED, "active_attempt_id": None, "return_level": level})


def _conflict(detail: str) -> Never:
    raise TargetRuntimeConflictError(detail)


def _reference(detail: str, cause: Exception | None = None) -> Never:
    raise TargetRuntimeReferenceError(detail) from cause


def _recovery_failure(detail: str) -> Never:
    raise TargetRecoveryError(detail)


def _model_content(model: BaseModel) -> bytes:
    payload = model.model_dump(mode="json")
    return f"{json.dumps(payload, sort_keys=True, separators=(',', ':'))}\n".encode()


def _state_content(state: TargetRuntimeState) -> bytes:
    return _model_content(state)


def _participant_content(participant: TransactionParticipant | ReplacementTransactionParticipant) -> bytes:
    if isinstance(participant, ReplacementTransactionParticipant):
        return participant.replacement_content
    return participant.content
