"""Transactional admission of target semantic authority and initial plan work."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from owlbear_kanban.runtime_transaction import (
    ReplacementTransactionParticipant,
    RuntimeTransaction,
    TransactionConflictError,
    TransactionParticipant,
)
from owlbear_kanban.target_authority import AuthorityStatus, PlanScopeKind, TargetAuthority
from owlbear_kanban.target_runtime import TargetJob, TargetJobState, TargetRuntimeState


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


def _canonical_json(payload: object) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


def _model_content(model: BaseModel) -> bytes:
    return _canonical_json(model.model_dump(mode="json")) + b"\n"


__all__ = [
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
