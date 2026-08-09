"""Transactional admission of target semantic authority and initial plan work."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from owlbear_delivery.delivery_runtime import DeliveryFrontier, OutcomeAuthorityBinding
from owlbear_delivery.runtime_transaction import (
    ReplacementTransactionParticipant,
    RuntimeTransaction,
    TransactionConflictError,
    TransactionParticipant,
)
from owlbear_delivery.storage_io import locked_roots
from owlbear_delivery.target_authority import AuthorityStatus, PlanScopeKind, TargetAuthority
from owlbear_delivery.target_contract import (
    DeliveryCompilationDiagnostic,
    DeliveryContract,
    DeliveryOutcome,
    compile_delivery_contract,
)
from owlbear_delivery.target_runtime import TargetJob, TargetJobState, TargetRuntimeState

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_delivery.design_package import DesignPackageStore


class TargetAdmissionError(RuntimeError):
    """Base error for target semantic admission."""

    code = "ERR_TARGET_ADMISSION"


class TargetAdmissionValidationError(TargetAdmissionError):
    """Candidate authority or evidence is incomplete."""

    code = "ERR_TARGET_ADMISSION_VALIDATION"


class TargetAdmissionConflictError(TargetAdmissionError):
    """An admitted target identity already contains different bytes."""

    code = "ERR_TARGET_ADMISSION_CONFLICT"


class TargetAdmissionReferenceError(TargetAdmissionError):
    """One admitted target authority cannot be found or read."""

    code = "ERR_TARGET_ADMISSION_REFERENCE"


class _AdmissionModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class TargetChallengeEntry(_AdmissionModel):
    """One source-grounded challenge result for an authority identity."""

    subject_id: str = Field(min_length=1)
    disposition: Literal["pass", "warning"]
    evidence: str = Field(min_length=1)


class TargetAdmissionCandidate(_AdmissionModel):
    """One complete target authority with pre-approval gate evidence."""

    authority: TargetAuthority
    challenge: tuple[TargetChallengeEntry, ...] = Field(min_length=1)
    baseline: tuple[str, ...] = Field(min_length=1)
    known_limits: tuple[str, ...]
    prepared_at: str = Field(min_length=1)


class TargetAdmissionRequest(_AdmissionModel):
    """Explicit approval for one exact validated target candidate."""

    candidate: TargetAdmissionCandidate
    approved_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    approved_by: str = Field(min_length=1)
    approved_at: str = Field(min_length=1)


class TargetAdmissionAssessment(_AdmissionModel):
    """Deterministic admission assessment for one target candidate."""

    authority_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    initial_jobs: tuple[TargetJob, ...]
    warning_subject_ids: tuple[str, ...]


class TargetAdmissionReceipt(_AdmissionModel):
    """Immutable evidence that one semantic authority became executable."""

    schema_version: Literal[1] = 1
    receipt_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    change_id: str = Field(min_length=1)
    authority_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    approved_by: str = Field(min_length=1)
    approved_at: str = Field(min_length=1)
    initial_job_ids: tuple[int, ...]
    warning_subject_ids: tuple[str, ...]
    known_limits: tuple[str, ...]

    @model_validator(mode="after")
    def validate_receipt_id(self) -> TargetAdmissionReceipt:
        """Require the receipt ID to bind every immutable field."""
        payload = self.model_dump(mode="json", exclude={"receipt_id"})
        if self.receipt_id != hashlib.sha256(_canonical_json(payload)).hexdigest():
            msg = "target admission receipt identity does not match its content"
            raise ValueError(msg)
        return self


class TargetAdmissionResult(_AdmissionModel):
    """Published target authority, initial execution state, and receipt."""

    authority: TargetAuthority
    runtime_state: TargetRuntimeState
    receipt: TargetAdmissionReceipt
    replayed: bool


class DeliveryAdmissionValidationError(TargetAdmissionError):
    """Source-bound Delivery authority cannot be compiled or validated."""

    code = "ERR_DELIVERY_ADMISSION_VALIDATION"

    def __init__(
        self,
        message: str,
        diagnostics: tuple[DeliveryCompilationDiagnostic, ...] = (),
    ) -> None:
        super().__init__(message)
        self.diagnostics = diagnostics


class DeliveryAdmissionConflictError(TargetAdmissionError):
    """Source-bound Delivery publication conflicts with durable state."""

    code = "ERR_DELIVERY_ADMISSION_CONFLICT"


class DeliveryAdmissionRequest(_AdmissionModel):
    """Explicit quiescence evidence for one source-bound admission call."""

    change_id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    active_claim_ids: tuple[str, ...]

    @model_validator(mode="after")
    def _validate_claims(self) -> DeliveryAdmissionRequest:
        if len(self.active_claim_ids) != len(set(self.active_claim_ids)) or any(
            not claim_id for claim_id in self.active_claim_ids
        ):
            msg = "active claim identities must be nonempty and unique"
            raise ValueError(msg)
        return self


class RevisionCarryForward(_AdmissionModel):
    """Outcome identities preserved or invalidated by one semantic revision."""

    preserved_outcome_ids: tuple[str, ...]
    invalidated_outcome_ids: tuple[str, ...]


class DeliveryAdmissionReceipt(_AdmissionModel):
    """Minimal receipt making one source-bound contract executable."""

    schema_version: Literal[1] = 1
    receipt_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    change_id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    contract_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_bindings_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    integration_target: str = Field(min_length=1)
    checkpoint_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    frontier_ids: tuple[str, ...]

    @model_validator(mode="after")
    def _validate_receipt_id(self) -> DeliveryAdmissionReceipt:
        payload = self.model_dump(mode="json", exclude={"receipt_id"})
        if self.receipt_id != hashlib.sha256(_canonical_json(payload)).hexdigest():
            msg = "Delivery admission receipt identity does not match its content"
            raise ValueError(msg)
        return self


class DeliveryAdmissionResult(_AdmissionModel):
    """One published source-bound contract, frontier, receipt, and revision result."""

    contract: DeliveryContract
    contract_bytes: bytes
    contract_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    frontier: DeliveryFrontier
    receipt: DeliveryAdmissionReceipt
    carry_forward: RevisionCarryForward | None = None
    replayed: bool


class _CurrentDelivery(_AdmissionModel):
    contract: DeliveryContract | None = None
    contract_bytes: bytes | None = None
    frontier: DeliveryFrontier | None = None
    frontier_bytes: bytes | None = None
    receipt: DeliveryAdmissionReceipt | None = None
    receipt_bytes: bytes | None = None
    partial_content: tuple[bytes | None, ...] = ()

    @property
    def is_partial(self) -> bool:
        return bool(self.partial_content)


class _CompiledDelivery(_AdmissionModel):
    package_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    contract: DeliveryContract
    canonical_bytes: bytes
    digest: str = Field(pattern=r"^[0-9a-f]{64}$")


_DELIVERY_NAMES = ("contract.json", "frontier.json", "admission.json")


class DeliveryAuthorityRegistry:
    """Compile and transactionally publish isolated schema-v2 Delivery authority."""

    def __init__(
        self,
        target_root: Path,
        package_store: DesignPackageStore,
        *,
        integration_target: str,
        failure: Callable[[str], None] | None = None,
    ) -> None:
        if not integration_target:
            msg = "integration target is required"
            raise ValueError(msg)
        self._target_root = target_root.resolve()
        self._package_store = package_store
        self._integration_target = integration_target
        self._failure = failure

    def admit(self, request: DeliveryAdmissionRequest) -> DeliveryAdmissionResult:
        """Publish or revise authority derived from the exact active package sources."""
        lock_root = self._target_root / "delivery-locks" / request.change_id
        with locked_roots((lock_root,)):
            compiled = self._compile_package(request.change_id)
            current = self._read_current(request.change_id)
            self._validate_current(request, current)
            checkpoint_commit = self._publish_package_contract(request.change_id, compiled)
            frontier, carry_forward = _delivery_frontier(compiled.contract, current)
            receipt = _delivery_receipt(
                compiled.contract,
                compiled.digest,
                frontier,
                self._integration_target,
                checkpoint_commit,
            )
            if current is not None and _is_delivery_replay(current, compiled.canonical_bytes, frontier, receipt):
                return _delivery_result(compiled, frontier, receipt, carry_forward, replayed=True)

            participants, resumed = self._delivery_participants(
                request.change_id,
                compiled.canonical_bytes,
                frontier,
                receipt,
                current,
            )
            transaction = RuntimeTransaction(
                self._target_root,
                f"delivery-admit-{request.change_id}-{compiled.digest}",
                participants,
            )
            try:
                transaction.commit(failure=self._failure)
            except TransactionConflictError as exc:
                message = f"Delivery authority is already admitted differently: {request.change_id}"
                raise DeliveryAdmissionConflictError(message) from exc
            return _delivery_result(compiled, frontier, receipt, carry_forward, replayed=resumed)

    def _compile_package(self, change_id: str) -> _CompiledDelivery:
        package = self._package_store.read_verified(change_id)
        compiled = compile_delivery_contract(change_id, package.intent_bytes, package.design_bytes)
        if compiled.diagnostics:
            message = "authored Specification does not compile"
            raise DeliveryAdmissionValidationError(message, compiled.diagnostics)
        if compiled.contract is None or compiled.canonical_bytes is None or compiled.digest is None:
            message = "compiler returned incomplete Delivery authority"
            raise DeliveryAdmissionValidationError(message)
        return _CompiledDelivery(
            package_id=package.package_id,
            contract=compiled.contract,
            canonical_bytes=compiled.canonical_bytes,
            digest=compiled.digest,
        )

    def _validate_current(
        self,
        request: DeliveryAdmissionRequest,
        current: _CurrentDelivery | None,
    ) -> None:
        if current is not None and request.active_claim_ids:
            message = f"active claims block Delivery authority revision: {request.change_id}"
            raise DeliveryAdmissionConflictError(message)
        if (
            current is not None
            and not current.is_partial
            and current.receipt is not None
            and current.receipt.integration_target != self._integration_target
        ):
            message = f"Delivery authority names another integration target: {request.change_id}"
            raise DeliveryAdmissionConflictError(message)

    def _publish_package_contract(self, change_id: str, compiled: _CompiledDelivery) -> str:
        def validate_sources(intent_bytes: bytes, design_bytes: bytes, contract_bytes: bytes) -> None:
            validation = compile_delivery_contract(change_id, intent_bytes, design_bytes)
            if (
                validation.diagnostics
                or validation.digest != compiled.digest
                or validation.canonical_bytes != contract_bytes
            ):
                message = "package sources changed before contract publication"
                raise DeliveryAdmissionValidationError(message, validation.diagnostics)
            if self._failure is not None:
                self._failure("before-package-publication")

        self._package_store.publish_contract(
            change_id,
            compiled.package_id,
            compiled.canonical_bytes,
            validate_sources,
        )
        return self._package_store.checkpoint(change_id).commit

    def _read_current(self, change_id: str) -> _CurrentDelivery | None:
        root = self._target_root / "delivery" / "changes" / change_id
        paths = tuple(root / name for name in _DELIVERY_NAMES)
        existing = tuple(path.exists() for path in paths)
        if not any(existing):
            return None
        if existing != (True, True, True):
            return _CurrentDelivery(
                partial_content=tuple(path.read_bytes() if path.exists() else None for path in paths)
            )
        try:
            contract_bytes, frontier_bytes, receipt_bytes = (path.read_bytes() for path in paths)
            return _CurrentDelivery(
                contract=DeliveryContract.model_validate_json(contract_bytes),
                contract_bytes=contract_bytes,
                frontier=DeliveryFrontier.model_validate_json(frontier_bytes),
                frontier_bytes=frontier_bytes,
                receipt=DeliveryAdmissionReceipt.model_validate_json(receipt_bytes),
                receipt_bytes=receipt_bytes,
            )
        except (OSError, ValueError) as exc:
            message = f"Delivery authority is missing or invalid: {change_id}"
            raise DeliveryAdmissionConflictError(message) from exc

    def _delivery_participants(
        self,
        change_id: str,
        contract_bytes: bytes,
        frontier: DeliveryFrontier,
        receipt: DeliveryAdmissionReceipt,
        current: _CurrentDelivery | None,
    ) -> tuple[tuple[TransactionParticipant | ReplacementTransactionParticipant, ...], bool]:
        relative_root = Path("delivery") / "changes" / change_id
        relative_paths = tuple(relative_root / name for name in _DELIVERY_NAMES)
        replacements = (contract_bytes, _model_content(frontier), _model_content(receipt))
        if current is None or current.is_partial:
            return (
                tuple(
                    TransactionParticipant(self._target_root, path, content)
                    for path, content in zip(relative_paths, replacements, strict=True)
                ),
                current is not None,
            )
        if current.contract_bytes is None or current.frontier_bytes is None or current.receipt_bytes is None:
            raise DeliveryAdmissionConflictError
        previous = (current.contract_bytes, current.frontier_bytes, current.receipt_bytes)
        history_root = relative_root / "revisions" / _digest(current.contract_bytes)
        history = tuple(
            TransactionParticipant(self._target_root, history_root / name, content)
            for name, content in zip(_DELIVERY_NAMES, previous, strict=True)
        )
        active = tuple(
            ReplacementTransactionParticipant(self._target_root, path, expected, replacement)
            for path, expected, replacement in zip(relative_paths, previous, replacements, strict=True)
        )
        return (*history, *active), False


class TargetAuthorityRegistry:
    """Own admitted target authorities below one receipt-authorized target root."""

    def __init__(self, target_root: Path) -> None:
        self._target_root = target_root.resolve()

    def list_authorities(self) -> tuple[TargetAuthority, ...]:
        """List every admitted target authority in stable change order."""
        changes_root = self._target_root / "changes"
        if not changes_root.exists():
            return ()
        authorities = [self._read_authority(path) for path in sorted(changes_root.iterdir()) if path.is_dir()]
        return tuple(sorted(authorities, key=lambda item: item.change_id))

    def show_authority(self, change_id: str) -> TargetAuthority:
        """Return one admitted target authority."""
        return self._read_authority(self._target_root / "changes" / change_id)

    def validate(self, candidate: TargetAdmissionCandidate) -> TargetAdmissionAssessment:
        """Validate evidence coverage and derive deterministic initial plan jobs."""
        authority = candidate.authority
        expected = {
            authority.change_id,
            *(item.commitment_id for item in authority.commitments),
            *(item.outcome_id for item in authority.outcomes),
            *(item.scope_id for item in authority.task_plan_scopes),
        }
        actual = [item.subject_id for item in candidate.challenge]
        if len(actual) != len(set(actual)) or set(actual) != expected:
            missing = sorted(expected - set(actual))
            unexpected = sorted(set(actual) - expected)
            detail = f"challenge coverage differs; missing={missing}, unexpected={unexpected}"
            raise TargetAdmissionValidationError(detail)
        digest = _authority_digest(authority)
        jobs = _initial_jobs(authority, digest, candidate.prepared_at)
        warnings = tuple(sorted(item.subject_id for item in candidate.challenge if item.disposition == "warning"))
        return TargetAdmissionAssessment(
            authority_digest=digest,
            initial_jobs=jobs,
            warning_subject_ids=warnings,
        )

    def admit(self, request: TargetAdmissionRequest) -> TargetAdmissionResult:
        """Atomically publish or revise target authority and its plan frontier."""
        assessment = self.validate(request.candidate)
        if request.approved_digest != assessment.authority_digest:
            msg = "approval does not name the validated target authority"
            raise TargetAdmissionValidationError(msg)
        authority = request.candidate.authority
        state = TargetRuntimeState(jobs=assessment.initial_jobs)
        receipt = _receipt(request, assessment)
        relative_root = Path("changes") / authority.change_id
        content = (
            _model_content(authority),
            _model_content(state),
            _model_content(receipt),
        )
        participants, replayed = self._publication_participants(relative_root, content)
        if replayed:
            current_state = TargetRuntimeState.model_validate_json(
                (self._target_root / relative_root / "target-runtime/state.json").read_bytes()
            )
            return TargetAdmissionResult(
                authority=authority,
                runtime_state=current_state,
                receipt=receipt,
                replayed=True,
            )
        transaction_id = f"admit-{authority.change_id}-{assessment.authority_digest}"
        try:
            RuntimeTransaction(self._target_root, transaction_id, participants).commit()
        except TransactionConflictError as exc:
            msg = f"target authority is already admitted differently: {authority.change_id}"
            raise TargetAdmissionConflictError(msg) from exc
        return TargetAdmissionResult(authority=authority, runtime_state=state, receipt=receipt, replayed=replayed)

    def _publication_participants(
        self,
        relative_root: Path,
        content: tuple[bytes, bytes, bytes],
    ) -> tuple[tuple[TransactionParticipant | ReplacementTransactionParticipant, ...], bool]:
        relative_paths = (
            relative_root / "authority.json",
            relative_root / "target-runtime/state.json",
            relative_root / "admission.json",
        )
        destinations = tuple(self._target_root / path for path in relative_paths)
        existing = tuple(path.exists() for path in destinations)
        if not any(existing):
            return tuple(
                TransactionParticipant(self._target_root, path, replacement)
                for path, replacement in zip(relative_paths, content, strict=True)
            ), False
        if existing not in ((True, True, False), (True, True, True)):
            msg = f"target authority publication is incomplete: {relative_root.name}"
            raise TargetAdmissionConflictError(msg)
        current = tuple(
            path.read_bytes() if present else None for path, present in zip(destinations, existing, strict=True)
        )
        if current[0] == content[0] and current[2] == content[2]:
            return (), True
        return self._revision_participants(relative_paths, current, content), False

    def _revision_participants(
        self,
        relative_paths: tuple[Path, Path, Path],
        current: tuple[bytes | None, bytes | None, bytes | None],
        replacements: tuple[bytes, bytes, bytes],
    ) -> tuple[TransactionParticipant | ReplacementTransactionParticipant, ...]:
        authority_content, state_content, _receipt_content = current
        if authority_content is None or state_content is None:
            raise TargetAdmissionConflictError
        state = TargetRuntimeState.model_validate_json(state_content)
        if any(job.state == TargetJobState.ACTIVE for job in state.jobs):
            msg = f"active target work blocks authority revision: {relative_paths[0].parts[1]}"
            raise TargetAdmissionConflictError(msg)
        previous_digest = hashlib.sha256(authority_content).hexdigest()
        history_root = relative_paths[0].parent / "revisions" / previous_digest
        history_names = ("authority.json", "state.json", "admission.json")
        history = tuple(
            TransactionParticipant(self._target_root, history_root / name, value)
            for name, value in zip(history_names, current, strict=True)
            if value is not None
        )
        replacements_participants = tuple(
            ReplacementTransactionParticipant(self._target_root, path, expected, replacement)
            if expected is not None
            else TransactionParticipant(self._target_root, path, replacement)
            for path, expected, replacement in zip(relative_paths, current, replacements, strict=True)
        )
        return (*history, *replacements_participants)

    def _read_authority(self, change_root: Path) -> TargetAuthority:
        if change_root.is_symlink() or change_root.resolve().parent != (self._target_root / "changes").resolve():
            msg = f"target authority path is unsafe: {change_root.name}"
            raise TargetAdmissionReferenceError(msg)
        try:
            return TargetAuthority.model_validate_json((change_root / "authority.json").read_bytes())
        except (OSError, ValueError) as exc:
            msg = f"target authority is missing or invalid: {change_root.name}"
            raise TargetAdmissionReferenceError(msg) from exc


def _initial_jobs(authority: TargetAuthority, digest: str, created_at: str) -> tuple[TargetJob, ...]:
    active_outcomes = tuple(item for item in authority.outcomes if item.status == AuthorityStatus.ACTIVE)
    if not active_outcomes:
        msg = "target admission requires at least one active outcome"
        raise TargetAdmissionValidationError(msg)
    outcome_scopes = tuple(item for item in authority.task_plan_scopes if item.kind == PlanScopeKind.OUTCOME)
    scopes = {item.target_id: item for item in outcome_scopes}
    if len(scopes) != len(outcome_scopes):
        msg = "each outcome requires exactly one task plan scope"
        raise TargetAdmissionValidationError(msg)
    outcome_ids = {item.outcome_id for item in active_outcomes}
    if set(scopes) != outcome_ids:
        missing = sorted(outcome_ids - set(scopes))
        unexpected = sorted(set(scopes) - outcome_ids)
        detail = f"active outcome plan scopes differ; missing={missing}, unexpected={unexpected}"
        raise TargetAdmissionValidationError(detail)
    job_ids = {item.outcome_id: index for index, item in enumerate(active_outcomes, start=1)}
    jobs = []
    for outcome in active_outcomes:
        if any(reference not in job_ids for reference in outcome.dependency_ids):
            msg = f"active outcome depends on inactive outcome: {outcome.outcome_id}"
            raise TargetAdmissionValidationError(msg)
        jobs.append(
            TargetJob(
                job_id=job_ids[outcome.outcome_id],
                kind="plan",
                change_id=authority.change_id,
                authority_digest=digest,
                work_item_id=outcome.outcome_id,
                plan_scope_id=scopes[outcome.outcome_id].scope_id,
                predecessor_job_ids=tuple(job_ids[item] for item in outcome.dependency_ids),
                created_at=created_at,
            )
        )
    return tuple(jobs)


def _receipt(request: TargetAdmissionRequest, assessment: TargetAdmissionAssessment) -> TargetAdmissionReceipt:
    payload = {
        "schema_version": 1,
        "change_id": request.candidate.authority.change_id,
        "authority_digest": assessment.authority_digest,
        "approved_by": request.approved_by,
        "approved_at": request.approved_at,
        "initial_job_ids": tuple(item.job_id for item in assessment.initial_jobs),
        "warning_subject_ids": assessment.warning_subject_ids,
        "known_limits": request.candidate.known_limits,
    }
    receipt_id = hashlib.sha256(_canonical_json(payload)).hexdigest()
    return TargetAdmissionReceipt(receipt_id=receipt_id, **payload)


def _authority_digest(authority: TargetAuthority) -> str:
    return hashlib.sha256(_model_content(authority)).hexdigest()


def _delivery_frontier(
    contract: DeliveryContract,
    current: _CurrentDelivery | None,
) -> tuple[DeliveryFrontier, RevisionCarryForward | None]:
    scopes = {scope.outcome_id: scope.scope_id for scope in contract.plan_scopes}
    empty = {
        outcome.outcome_id: OutcomeAuthorityBinding(
            outcome_id=outcome.outcome_id,
            plan_scope_id=scopes[outcome.outcome_id],
        )
        for outcome in contract.outcomes
    }
    if current is None or current.is_partial:
        return DeliveryFrontier(bindings=tuple(empty.values())), None
    if current.contract is None or current.frontier is None:
        raise DeliveryAdmissionConflictError
    _validate_delivery_frontier(current.contract, current.frontier)
    if current.contract == contract:
        return current.frontier, None
    invalidated = _invalidated_outcomes(current.contract, contract)
    previous_bindings = {binding.outcome_id: binding for binding in current.frontier.bindings}
    bindings = tuple(
        previous_bindings[outcome.outcome_id] if outcome.outcome_id not in invalidated else empty[outcome.outcome_id]
        for outcome in contract.outcomes
    )
    preserved = tuple(outcome.outcome_id for outcome in contract.outcomes if outcome.outcome_id not in invalidated)
    ordered_invalidated = tuple(
        outcome_id
        for outcome_id in (
            *(outcome.outcome_id for outcome in contract.outcomes),
            *(outcome.outcome_id for outcome in current.contract.outcomes),
        )
        if outcome_id in invalidated
    )
    return DeliveryFrontier(bindings=bindings), RevisionCarryForward(
        preserved_outcome_ids=preserved,
        invalidated_outcome_ids=tuple(dict.fromkeys(ordered_invalidated)),
    )


def _invalidated_outcomes(previous: DeliveryContract, replacement: DeliveryContract) -> set[str]:
    previous_outcomes = {outcome.outcome_id: outcome for outcome in previous.outcomes}
    replacement_outcomes = {outcome.outcome_id: outcome for outcome in replacement.outcomes}
    invalidated = {
        outcome_id
        for outcome_id in previous_outcomes.keys() | replacement_outcomes.keys()
        if outcome_id not in previous_outcomes
        or outcome_id not in replacement_outcomes
        or _outcome_projection(previous, previous_outcomes[outcome_id])
        != _outcome_projection(replacement, replacement_outcomes[outcome_id])
    }
    dependencies = {
        outcome.outcome_id: set(outcome.dependency_ids) for outcome in (*previous.outcomes, *replacement.outcomes)
    }
    while True:
        dependents = {outcome_id for outcome_id, dependency_ids in dependencies.items() if dependency_ids & invalidated}
        expanded = invalidated | dependents
        if expanded == invalidated:
            return invalidated
        invalidated = expanded


def _outcome_projection(contract: DeliveryContract, outcome: DeliveryOutcome) -> tuple[object, ...]:
    commitments = {item.commitment_id: item for item in contract.commitments}
    return (
        outcome,
        tuple(commitments[commitment_id] for commitment_id in outcome.commitment_ids),
    )


def _validate_delivery_frontier(contract: DeliveryContract, frontier: DeliveryFrontier) -> None:
    expected = tuple((scope.outcome_id, scope.scope_id) for scope in contract.plan_scopes)
    actual = tuple((binding.outcome_id, binding.plan_scope_id) for binding in frontier.bindings)
    if actual != expected:
        msg = "Delivery frontier does not match its admitted contract"
        raise DeliveryAdmissionConflictError(msg)


def _delivery_receipt(
    contract: DeliveryContract,
    contract_digest: str,
    frontier: DeliveryFrontier,
    integration_target: str,
    checkpoint_commit: str,
) -> DeliveryAdmissionReceipt:
    source_bindings = [item.model_dump(mode="json") for item in contract.source_bindings]
    payload = {
        "schema_version": 1,
        "change_id": contract.change_id,
        "contract_digest": contract_digest,
        "source_bindings_digest": _digest(_canonical_json(source_bindings)),
        "integration_target": integration_target,
        "checkpoint_commit": checkpoint_commit,
        "frontier_ids": tuple(binding.plan_scope_id for binding in frontier.bindings),
    }
    return DeliveryAdmissionReceipt(
        receipt_id=_digest(_canonical_json(payload)),
        **payload,
    )


def _is_delivery_replay(
    current: _CurrentDelivery,
    contract_bytes: bytes,
    frontier: DeliveryFrontier,
    receipt: DeliveryAdmissionReceipt,
) -> bool:
    return (
        not current.is_partial
        and current.contract_bytes == contract_bytes
        and current.frontier == frontier
        and current.receipt == receipt
    )


def _delivery_result(
    compiled: _CompiledDelivery,
    frontier: DeliveryFrontier,
    receipt: DeliveryAdmissionReceipt,
    carry_forward: RevisionCarryForward | None,
    *,
    replayed: bool,
) -> DeliveryAdmissionResult:
    return DeliveryAdmissionResult(
        contract=compiled.contract,
        contract_bytes=compiled.canonical_bytes,
        contract_digest=compiled.digest,
        frontier=frontier,
        receipt=receipt,
        carry_forward=carry_forward,
        replayed=replayed,
    )


def _digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _canonical_json(payload: object) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


def _model_content(model: BaseModel) -> bytes:
    return _canonical_json(model.model_dump(mode="json")) + b"\n"


__all__ = [
    "DeliveryAdmissionConflictError",
    "DeliveryAdmissionReceipt",
    "DeliveryAdmissionRequest",
    "DeliveryAdmissionResult",
    "DeliveryAdmissionValidationError",
    "DeliveryAuthorityRegistry",
    "DeliveryFrontier",
    "OutcomeAuthorityBinding",
    "RevisionCarryForward",
    "TargetAdmissionAssessment",
    "TargetAdmissionCandidate",
    "TargetAdmissionConflictError",
    "TargetAdmissionError",
    "TargetAdmissionReceipt",
    "TargetAdmissionReferenceError",
    "TargetAdmissionRequest",
    "TargetAdmissionResult",
    "TargetAdmissionValidationError",
    "TargetAuthorityRegistry",
    "TargetChallengeEntry",
]
