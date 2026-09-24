"""Exact, host-verified recovery authority; no caller assertion grants custody."""

# Retry metadata uses explicit bounded validation messages at its public boundary.
# ruff: noqa: EM101, TRY003

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Literal, Protocol, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from owlbear_delivery.runtime_transaction import (
    ReplacementTransactionParticipant,
    RuntimeTransaction,
    TransactionConflictError,
    TransactionParticipant,
)

if TYPE_CHECKING:
    from collections.abc import Callable

_MAX_RECORD_BYTES = 65_536
_DIGEST_LENGTH = 64
MAX_RECOVERY_INTENTS = 256
_MAX_PROVENANCE_VALUE_LENGTH = 512
_MAX_REPAIR_BINDINGS = 256
MAX_ADMITTED_PATH_LENGTH = 4096
_ADMITTED_AUTHORITY_FIELDS = frozenset(
    {"admitted_task_id", "admitted_task_digest", "admitted_task_scope", "admitted_paths"}
)
ADMITTED_PATH_CHARS = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._/@+-"
)


class _RecoveryModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class RecoveryInvocationRequest(_RecoveryModel):
    """Engine-issued identity and complete managed-resource boundary sent to a host."""

    change_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    owner_id: str = Field(min_length=1, max_length=128)
    attempt_id: str = Field(min_length=1, max_length=128)
    outcome_id: str | None = None
    kind: Literal["claim", "finalizer", "mark-ready", "reconcile-checkpoint", "sync-target", "observe-acceptance"]
    contract_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    exact_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    target_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    branch: str = Field(min_length=1, max_length=256)
    worktree: str = Field(min_length=1, max_length=4096)
    repository: str = Field(min_length=1, max_length=4096)
    runtime_root: str = Field(min_length=1, max_length=4096)
    integration_target: str = Field(min_length=1, max_length=256)
    publication_repository: str | None = Field(default=None, max_length=256)
    mutation_channels: tuple[
        Literal[
            "managed-filesystem",
            "shared-git-metadata-and-refs",
            "git-remotes",
            "delivery-runtime",
            "publication-provider",
        ],
        ...,
    ] = (
        "managed-filesystem",
        "shared-git-metadata-and-refs",
        "git-remotes",
        "delivery-runtime",
        "publication-provider",
    )


class RecoveryInvocation(_RecoveryModel):
    """Host registration, not a reinterpretation of a dispatch PID/session string."""

    schema_version: Literal[1] = 1
    request: RecoveryInvocationRequest
    host_instance: str = Field(min_length=1, max_length=128)
    host_generation: str = Field(min_length=1, max_length=128)
    invocation_id: str = Field(min_length=1, max_length=256)


def is_canonical_admitted_path(value: str) -> bool:
    """Return whether a path is safe to persist as an admitted workspace path."""
    parsed = PurePosixPath(value)
    return (
        bool(value)
        and len(value) <= MAX_ADMITTED_PATH_LENGTH
        and value == parsed.as_posix()
        and not parsed.is_absolute()
        and parsed.parts
        and not any(part in {"", ".", ".."} for part in parsed.parts)
        and "\\" not in value
        and "\x00" not in value
        and value.isprintable()
        and all(character in ADMITTED_PATH_CHARS for character in value)
    )


def _scope_contains_path(scope: str, path: str) -> bool:
    scope_parts = PurePosixPath(scope).parts
    path_parts = PurePosixPath(path).parts
    return len(path_parts) >= len(scope_parts) and path_parts[: len(scope_parts)] == scope_parts


class RecoveryIntent(_RecoveryModel):
    """Immutable proposed recovery of one captured owner; never a release capability."""

    schema_version: Literal[1] = 1
    invocation: RecoveryInvocation
    frontier_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    coordination_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    exact_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    target_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    workspace_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    owner_record: str = Field(min_length=1, max_length=16384)
    failure_id: str | None = Field(default=None, max_length=128)
    effect_receipt_id: str | None = Field(default=None, max_length=128)
    engine_result_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    proposal_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    # These are engine-derived custody facts.  They remain optional for the
    # older A-only journal records, but preservation must reject a record that
    # does not carry both proofs.
    maintained_surfaces: tuple[str, ...] = ()
    last_write_provenance: tuple[str, ...] = ()
    # D03-C authority for raw preservation is narrower than the historical
    # provenance fields above: one active Builder task and the exact paths it
    # admitted.  These fields are intentionally optional for older journals.
    admitted_task_id: str | None = Field(default=None, min_length=1, max_length=256)
    admitted_task_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    admitted_task_scope: tuple[str, ...] = Field(default=(), max_length=256)
    admitted_paths: tuple[str, ...] = Field(default=(), max_length=256)
    kind: Literal["clean-claim", "clean-finalizer", "ready-readback"]

    @model_validator(mode="after")
    def _validate_provenance(self) -> Self:
        for values, label in (
            (self.maintained_surfaces, "maintained surfaces"),
            (self.last_write_provenance, "last-write provenance"),
        ):
            if len(values) != len(set(values)) or any(
                not value or len(value) > _MAX_PROVENANCE_VALUE_LENGTH or not value.isprintable()
                for value in values
            ):
                message = f"{label} must contain bounded unique values"
                raise ValueError(message)
        for values, label in (
            (self.admitted_task_scope, "admitted task scope"),
            (self.admitted_paths, "admitted paths"),
        ):
            if values != tuple(sorted(set(values))) or any(
                not value
                or not is_canonical_admitted_path(value)
                for value in values
            ):
                message = f"{label} must contain sorted, unique relative paths"
                raise ValueError(message)
        if (self.admitted_task_id is None) != (self.admitted_task_digest is None):
            message = "admitted task identity requires both task id and digest"
            raise ValueError(message)
        if self.admitted_task_id is not None and not self.admitted_task_scope:
            message = "admitted task identity requires a non-empty exact path scope"
            raise ValueError(message)
        if self.admitted_task_id is None and (self.admitted_task_scope or self.admitted_paths):
            message = "admitted paths require an admitted task identity"
            raise ValueError(message)
        if not all(
            any(_scope_contains_path(scope, path) for scope in self.admitted_task_scope)
            for path in self.admitted_paths
        ):
            message = "admitted paths must be within the admitted task scope"
            raise ValueError(message)
        return self

    @property
    def recovery_id(self) -> str:
        """Return the content-addressed journal identity (not evidence authenticity)."""
        return digest(encoded(self))

    @property
    def uses_legacy_encoding(self) -> bool:
        """Whether this journal predates the D03-C provenance fields."""
        return not {
            "maintained_surfaces",
            "last_write_provenance",
        }.intersection(self.model_fields_set) and not _ADMITTED_AUTHORITY_FIELDS.intersection(
            self.model_fields_set
        )

    def authority_matches(self, other: RecoveryIntent) -> bool:
        """Compare a re-captured authority without changing a legacy identity."""
        if self.uses_legacy_encoding:
            if other.uses_legacy_encoding:
                return encoded(self) == encoded(other)
            return _legacy_intent_bytes(self) == _legacy_intent_bytes(other)
        if self._has_legacy_provenance_only():
            if self._has_admitted_authority(other):
                return _without_admitted_authority_bytes(self) == _without_admitted_authority_bytes(other)
            return encoded(self) == encoded(other)
        if other.uses_legacy_encoding or other._has_legacy_provenance_only():
            return False
        return encoded(self) == encoded(other)

    def _has_legacy_provenance_only(self) -> bool:
        return bool({"maintained_surfaces", "last_write_provenance"}.intersection(self.model_fields_set)) and not (
            _ADMITTED_AUTHORITY_FIELDS.intersection(self.model_fields_set)
        )

    @staticmethod
    def _has_admitted_authority(intent: RecoveryIntent) -> bool:
        return bool(_ADMITTED_AUTHORITY_FIELDS.intersection(intent.model_fields_set))


class RecoveryEvidenceReference(_RecoveryModel):
    """Opaque reference resolved exclusively by the configured host owner."""

    reference: str = Field(min_length=1, max_length=256)


class RecoveryEvidence(_RecoveryModel):
    """Owner-verified whole-invocation closure or restart-durable enforced exclusion."""

    schema_version: Literal[1] = 1
    reference: RecoveryEvidenceReference
    recovery_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    invocation: RecoveryInvocation
    status: Literal["closed", "excluded", "still-running", "unknown", "unavailable"]
    scope: Literal["invocation-all-descendants-all-tool-jobs"] = "invocation-all-descendants-all-tool-jobs"


class RecoveryReceipt(_RecoveryModel):
    """Completed recovery, distinct from success of the original failed action."""

    schema_version: Literal[1] = 1
    recovery_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    evidence: RecoveryEvidence
    stages: tuple[Literal["proposed"], Literal["excluded"], Literal["reconciled"], Literal["completed"]] = (
        "proposed",
        "excluded",
        "reconciled",
        "completed",
    )
    preservation: Literal["clean-no-restoration"] = "clean-no-restoration"
    owner_effect: Literal["no-workspace-effect", "ready-receipt-readback"]
    owner_observation_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    finished_at: str = Field(min_length=1, max_length=64)

    @model_validator(mode="after")
    def _completed_evidence(self) -> Self:
        if (
            self.evidence.recovery_id != self.recovery_id
            or self.evidence.status not in {"closed", "excluded"}
            or (self.owner_effect == "ready-receipt-readback") != (self.owner_observation_id is not None)
        ):
            raise DeliveryWorkerExclusionRequiredError
        return self


class RecoveryEvidenceProvider(Protocol):
    """Trusted engine dependency, never a transport-supplied acknowledgement.

    Registration must bind the issued identity before dispatch. Verification resolves an
    opaque reference independently, covers the complete dynamically-created writer/job
    graph and forbids resuming the invocation. `excluded` additionally promises actual
    exclusion from every resource/channel in the request, durable across all restarts
    until closure. A cancellation request, observed PID exit or reacquired lock is not
    verification. Providers must return unknown when they cannot uphold this contract.
    """

    def register(self, request: RecoveryInvocationRequest) -> RecoveryInvocation | None:
        """Register an engine-issued invocation before dispatch."""
        ...

    def verify(self, reference: RecoveryEvidenceReference, intent: RecoveryIntent) -> RecoveryEvidence:
        """Resolve current evidence using the same opaque reference across restarts.

        Identity remains stable when exclusion advances to closure. Lost evidence is
        unknown/unavailable, never a replacement reference or reconstructed provenance.
        """
        ...


class UnavailableRecoveryEvidenceProvider:
    """Default host boundary: no evidence, no release."""

    def register(self, request: RecoveryInvocationRequest) -> None:
        """Do not manufacture host provenance for an issued invocation."""

    def verify(self, reference: RecoveryEvidenceReference, intent: RecoveryIntent) -> RecoveryEvidence:
        """Return unavailable without consulting caller identity strings."""
        return RecoveryEvidence(
            reference=reference, recovery_id=intent.recovery_id, invocation=intent.invocation, status="unavailable"
        )


def encoded(model: BaseModel) -> bytes:
    """Canonical immutable journal bytes."""
    if isinstance(model, RecoveryIntent):
        if model.uses_legacy_encoding:
            return _legacy_intent_bytes(model)
        if not _ADMITTED_AUTHORITY_FIELDS.intersection(model.model_fields_set):
            return _without_admitted_authority_bytes(model)
    return (model.model_dump_json() + "\n").encode()


def _legacy_intent_bytes(intent: RecoveryIntent) -> bytes:
    return (
        intent.model_dump_json(
            exclude={
                "maintained_surfaces",
                "last_write_provenance",
                "admitted_task_id",
                "admitted_task_digest",
                "admitted_task_scope",
                "admitted_paths",
            },
        )
        + "\n"
    ).encode()


def _without_admitted_authority_bytes(intent: RecoveryIntent) -> bytes:
    return (
        intent.model_dump_json(
            exclude={
                "admitted_task_id",
                "admitted_task_digest",
                "admitted_task_scope",
                "admitted_paths",
            }
        )
        + "\n"
    ).encode()


def digest(content: bytes) -> str:
    """Hash exact persisted bytes."""
    return hashlib.sha256(content).hexdigest()


def invocation_path(invocation: RecoveryInvocationRequest) -> Path:
    """Locate an exact issued owner without accepting caller-authored path segments."""
    return Path("changes") / invocation.change_id / "invocations" / f"{digest(invocation.owner_id.encode())}.json"


def journal_path(change_id: str, recovery_id: str, name: str) -> Path:
    """Build contained journal paths from validated identities."""
    if not change_id or any(char not in "abcdefghijklmnopqrstuvwxyz0123456789-" for char in change_id):
        raise DeliveryWorkerExclusionRequiredError
    if len(recovery_id) != _DIGEST_LENGTH or any(char not in "0123456789abcdef" for char in recovery_id):
        raise DeliveryWorkerExclusionRequiredError
    if name not in {"intent", "evidence", "receipt"}:
        raise DeliveryWorkerExclusionRequiredError
    return Path("changes") / change_id / "recovery-receipts" / recovery_id / f"{name}.json"


def publish_record(root: Path, path: Path, model: BaseModel) -> None:
    """Publish immutable authority using the existing durable transaction owner."""
    RuntimeTransaction(
        root, f"recovery-{digest(str(path).encode())}", (TransactionParticipant(root, path, encoded(model)),)
    ).commit()


def read_record(root: Path, relative: Path) -> bytes:
    """Read only bounded contained recovery metadata, never a symlink target."""
    path = root / relative
    if relative.is_absolute() or root.resolve() not in path.resolve().parents:
        raise DeliveryWorkerExclusionRequiredError
    if any((root / Path(*relative.parts[:index])).is_symlink() for index in range(1, len(relative.parts) + 1)):
        raise DeliveryWorkerExclusionRequiredError
    with path.open("rb") as stream:
        content = stream.read(_MAX_RECORD_BYTES + 1)
    if len(content) > _MAX_RECORD_BYTES:
        raise DeliveryWorkerExclusionRequiredError
    return content


def verify_evidence(
    provider: RecoveryEvidenceProvider, reference: RecoveryEvidenceReference, intent: RecoveryIntent
) -> RecoveryEvidence:
    """Validate the configured owner's response, never deserialize a caller's proof."""
    try:
        evidence = provider.verify(reference, intent)
    except (OSError, RuntimeError, ValueError) as exc:
        raise DeliveryWorkerExclusionRequiredError from exc
    if (
        not isinstance(evidence, RecoveryEvidence)
        or evidence.reference != reference
        or evidence.recovery_id != intent.recovery_id
        or evidence.invocation != intent.invocation
        or evidence.scope != "invocation-all-descendants-all-tool-jobs"
        or evidence.status not in {"closed", "excluded"}
    ):
        raise DeliveryWorkerExclusionRequiredError
    return evidence


class DeliveryWorkerExclusionRequiredError(RuntimeError):
    """Custody cannot be released without exact host-owned exclusion evidence."""

    code = "ERR_DELIVERY_WORKER_EXCLUSION_REQUIRED"

    def __init__(self) -> None:
        super().__init__(
            "Custody and files are unchanged. Recovery requires supported worker exclusion "
            "covering the invocation, all descendant writers and outstanding tool jobs, with "
            "no ability to resume, or restart-durable exclusion from every managed filesystem, "
            "Git and mutation resource. Timeout and caller confirmation are not evidence."
        )


class RetryFailureClass(StrEnum):
    """Failure classes with deliberately small, persisted retry policies."""

    MECHANICAL = "mechanical-repair"
    TRANSIENT = "transient-read"
    ACCEPTANCE = "acceptance-wait"
    CONTAINED = "contained"


class RetryStopCode(StrEnum):
    """Stable stop reasons that do not depend on provider error prose."""

    EXHAUSTED = "retry-exhausted"
    ACCEPTANCE_WAIT = "acceptance-wait"
    CONTAINMENT = "retry-containment"
    BACKOFF = "retry-backoff"


class RetryEpisodeKey(_RecoveryModel):
    """Stable semantic identity for one bounded failure episode.

    Operation IDs, host/session IDs, acceptance observation IDs and failure text are
    intentionally not fields on this model.  They are aliases/history, never new
    retry identities.
    """

    schema_version: Literal[1] = 1
    change_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    action_kind: str = Field(min_length=1, max_length=128)
    exact_head: str = Field(min_length=1, max_length=128)
    target_head: str | None = Field(default=None, max_length=128)
    finalization_id: str | None = Field(default=None, max_length=256)
    contract_digest: str | None = Field(default=None, max_length=128)
    outcome_id: str | None = Field(default=None, max_length=128)
    task_lineage: str | None = Field(default=None, max_length=256)
    procedure_class: str | None = Field(default=None, max_length=256)
    original_candidate: str | None = Field(default=None, max_length=256)

    @classmethod
    def engine(
        cls,
        change_id: str,
        action_kind: str,
        exact_head: str,
        target_head: str | None = None,
        finalization_id: str | None = None,
    ) -> RetryEpisodeKey:
        """Create the engine identity named by the D03-B contract."""
        return cls(
            change_id=change_id,
            action_kind=action_kind,
            exact_head=exact_head,
            target_head=target_head,
            finalization_id=finalization_id,
        )

    @classmethod
    def worker(  # noqa: PLR0913 - the worker identity is intentionally fully bound.
        cls,
        change_id: str,
        action_kind: str,
        exact_head: str,
        *,
        contract_digest: str,
        outcome_id: str,
        task_lineage: str,
        procedure_class: str,
        original_candidate: str,
        target_head: str | None = None,
        finalization_id: str | None = None,
    ) -> RetryEpisodeKey:
        """Create a worker/check identity while retaining the engine identity fields."""
        return cls(
            change_id=change_id,
            action_kind=action_kind,
            exact_head=exact_head,
            target_head=target_head,
            finalization_id=finalization_id,
            contract_digest=contract_digest,
            outcome_id=outcome_id,
            task_lineage=task_lineage,
            procedure_class=procedure_class,
            original_candidate=original_candidate,
        )

    @property
    def engine_key(self) -> tuple[str, str, str, str | None, str | None]:
        """Return the exact engine semantic tuple, excluding worker aliases."""
        return (self.change_id, self.action_kind, self.exact_head, self.target_head, self.finalization_id)

    @property
    def identity(self) -> str:
        """Return a content identity suitable for durable episode directories."""
        return digest(
            (
                self.model_dump_json(
                    exclude={
                        "schema_version",
                    }
                )
                + "\n"
            ).encode()
        )


class RetryEpisodeAlias(_RecoveryModel):
    """Bounded history that points at an episode without changing its identity."""

    alias_kind: Literal["operation", "session", "commit", "task", "report", "failure-code", "observation", "label"]
    value: str = Field(min_length=1, max_length=256)
    observed_at: str = Field(min_length=1, max_length=64)


class RetryAttempt(_RecoveryModel):
    """One immutable reservation record.

    The record is never rewritten after reservation.  Completion is represented by a
    separate immutable outcome record and the CAS summary.
    """

    schema_version: Literal[1] = 1
    attempt_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$", max_length=256)
    episode_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    key: RetryEpisodeKey
    failure_class: RetryFailureClass
    kind: Literal["original", "repair", "observation"]
    automatic: bool = True
    reserved_at: str = Field(min_length=1, max_length=64)
    operation_alias: str | None = Field(default=None, max_length=256)


class RetryAttemptOutcome(_RecoveryModel):
    """Immutable result attached to a prior reservation."""

    schema_version: Literal[1] = 1
    attempt_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$", max_length=256)
    episode_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    status: Literal["failed", "succeeded", "waiting", "contained"]
    observed_at: str = Field(min_length=1, max_length=64)
    failure_code: str | None = Field(default=None, max_length=128)
    failure_detail: str | None = Field(default=None, max_length=240)
    next_eligible_at: str | None = Field(default=None, max_length=64)
    stop_code: RetryStopCode | None = None


class RetryRepairBinding(_RecoveryModel):
    """Durable linkage from a Builder repair reservation back to its failed action."""

    schema_version: Literal[1] = 1
    binding_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    change_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    episode_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    original_attempt_id: str = Field(min_length=1, max_length=256)
    repair_attempt_id: str = Field(min_length=1, max_length=256)
    repair_task_id: str = Field(min_length=1, max_length=256)
    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    created_at: str = Field(min_length=1, max_length=64)

    @classmethod
    def create(
        cls,
        *,
        change_id: str,
        episode_id: str,
        original_attempt_id: str,
        repair_attempt_id: str,
        repair_task_id: str,
        outcome_id: str,
        created_at: str,
    ) -> RetryRepairBinding:
        values = {
            "change_id": change_id,
            "episode_id": episode_id,
            "original_attempt_id": original_attempt_id,
            "repair_attempt_id": repair_attempt_id,
            "repair_task_id": repair_task_id,
            "outcome_id": outcome_id,
            "created_at": created_at,
        }
        candidate = cls.model_construct(binding_id="0" * _DIGEST_LENGTH, **values)
        binding_id = digest((candidate.model_dump_json(exclude={"binding_id"}) + "\n").encode())
        return cls(binding_id=binding_id, **values)

    @model_validator(mode="after")
    def _validate_identity(self) -> Self:
        expected = digest((self.model_dump_json(exclude={"binding_id"}) + "\n").encode())
        if self.binding_id != expected:
            raise ValueError("retry repair binding identity does not match its content")
        return self


class RetryOwnerResult(_RecoveryModel):
    """Exact result evidence committed by the owner with its authority change."""

    schema_version: Literal[1] = 1
    attempt_id: str
    episode_id: str
    accepted: bool
    observed_at: str
    failure_code: str = "worker-blocked"
    accepted_progress: bool = True
    repair_outcome_id: str | None = Field(default=None, pattern=r"^OUT-[0-9]{3}$")
    repair_task_id: str | None = Field(default=None, min_length=1, max_length=256)
    completed_commit: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")

    @model_validator(mode="after")
    def _validate_repair_acceptance(self) -> Self:
        repair_fields = (self.repair_outcome_id, self.repair_task_id, self.completed_commit)
        if not self.accepted and (not self.accepted_progress or any(value is not None for value in repair_fields)):
            raise ValueError("rejected retry owner result cannot carry repair acceptance")
        if self.accepted and self.repair_task_id is None:
            if not self.accepted_progress or any(value is not None for value in repair_fields):
                raise ValueError("ordinary accepted retry owner result must reset its episode")
        elif self.accepted and (
            self.accepted_progress
            or self.repair_outcome_id is None
            or self.completed_commit is None
        ):
            raise ValueError("repair owner result must identify accepted progress without reset")
        return self


class RetryEpisodeSummary(_RecoveryModel):
    """CAS-projected state for one semantic episode."""

    episode_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    key: RetryEpisodeKey
    failure_class: RetryFailureClass
    policy_version: int = Field(default=1, ge=1)
    attempt_ids: tuple[str, ...] = ()
    outcome_ids: tuple[str, ...] = ()
    accepted_attempt_ids: tuple[str, ...] = ()
    aliases: tuple[RetryEpisodeAlias, ...] = ()
    total_attempts: int = Field(default=0, ge=0)
    repair_attempts: int = Field(default=0, ge=0)
    observation_attempts: int = Field(default=0, ge=0)
    explicit_observations: int = Field(default=0, ge=0)
    last_status: Literal["reserved", "failed", "succeeded", "waiting", "contained"] | None = None
    last_failure_at: str | None = Field(default=None, max_length=64)
    next_eligible_at: str | None = Field(default=None, max_length=64)
    stop_code: RetryStopCode | None = None
    reset_count: int = Field(default=0, ge=0)
    legacy_failures: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def _validate_identity(self) -> Self:
        if self.episode_id != self.key.identity:
            raise ValueError("retry episode identity does not match its semantic key")
        if len(set(self.attempt_ids)) != len(self.attempt_ids):
            raise ValueError("retry attempt identities must be unique")
        if len(set(self.outcome_ids)) != len(self.outcome_ids):
            raise ValueError("retry outcome identities must be unique")
        return self


class RetryLedgerSummary(_RecoveryModel):
    """Versioned current retry projection guarded by expected-byte replacement."""

    schema_version: Literal[1] = 1
    change_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    version: int = Field(default=0, ge=0)
    updated_at: str | None = Field(default=None, max_length=64)
    episodes: tuple[RetryEpisodeSummary, ...] = ()

    @classmethod
    def empty(cls, change_id: str) -> RetryLedgerSummary:
        """Return an empty authority projection for one Change."""
        return cls(change_id=change_id)

    @model_validator(mode="after")
    def _validate_episodes(self) -> Self:
        if any(episode.key.change_id != self.change_id for episode in self.episodes):
            raise ValueError("retry episode belongs to another Change")
        identities = tuple(episode.episode_id for episode in self.episodes)
        if len(set(identities)) != len(identities):
            raise ValueError("retry episode identities must be unique")
        return self


class RetryReservation(_RecoveryModel):
    """Result of an atomic reserve-before-effect decision."""

    episode_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    attempt_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$", max_length=256)
    allowed: bool
    replayed: bool = False
    reason_code: str
    attempts: int = Field(default=0, ge=0)
    next_eligible_at: str | None = Field(default=None, max_length=64)
    stop_code: RetryStopCode | None = None


class RetryBudgetExhaustedError(RuntimeError):
    """The durable episode has reached a fixed stop condition."""

    code = "ERR_DELIVERY_RETRY_EXHAUSTED"


class RetryLedgerCorruptError(RuntimeError):
    """Retry metadata is unreadable or incompatible and must fail closed."""

    code = "ERR_DELIVERY_RETRY_LEDGER_CORRUPT"


class RetryLedgerConflictError(RuntimeError):
    """A concurrent ledger writer changed the expected current summary."""

    code = "ERR_DELIVERY_RETRY_LEDGER_CONFLICT"


class RetryLedger:
    """Durable, Change-scoped retry authority.

    It deliberately owns only bounded retry accounting.  It does not release
    Delivery custody, perform provider writes, or turn an unknown effect into a
    retry-safe result.
    """

    schema_version = 1
    policy_version = 1
    mechanical_repairs = 2
    transient_attempts = 3
    acceptance_observations = 3
    backoff_seconds = (1, 2)

    def __init__(
        self,
        runtime_root: Path,
        change_id: str,
        *,
        clock: Callable[[], datetime | str] | None = None,
    ) -> None:
        if not change_id or any(char not in "abcdefghijklmnopqrstuvwxyz0123456789-" for char in change_id):
            raise ValueError("invalid Change identity")
        self.runtime_root = runtime_root.resolve()
        self.change_id = change_id
        self._clock = clock or (lambda: datetime.now(UTC))
        self._directory = Path("changes") / change_id / "retry-ledger"
        self._summary_path = self._directory / "current.json"
        self._attempts_path = self._directory / "attempts"
        self._outcomes_path = self._directory / "outcomes"
        self._repair_bindings_path = self._directory / "repair-bindings"

    @property
    def summary_path(self) -> Path:
        """Return the contained current-summary path for diagnostics/tests."""
        return self.runtime_root / self._summary_path

    def read(self) -> RetryLedgerSummary:
        """Read the current summary without creating or mutating ledger state."""
        try:
            content = self.summary_path.read_bytes()
        except FileNotFoundError:
            return RetryLedgerSummary.empty(self.change_id)
        except OSError as exc:
            raise RetryLedgerCorruptError from exc
        try:
            summary = RetryLedgerSummary.model_validate_json(content, strict=False)
        except (TypeError, ValueError) as exc:
            raise RetryLedgerCorruptError from exc
        if summary.change_id != self.change_id:
            raise RetryLedgerCorruptError
        return summary

    current = read

    def episode(self, key: RetryEpisodeKey) -> RetryEpisodeSummary | None:
        """Return one episode by semantic identity."""
        if key.change_id != self.change_id:
            raise ValueError("retry key belongs to another Change")
        return _matching_episode(self.read(), key)

    def import_legacy_failures(
        self,
        key: RetryEpisodeKey,
        count: int,
        *,
        now: datetime | str,
        existing_attempt: tuple[str, str] | None = None,
    ) -> RetryEpisodeSummary | None:
        """Carry a binding's historical failures forward, never as a new allowance."""
        if count <= 0:
            return self.episode(key)
        summary, previous = self._read_with_bytes()
        current = _matching_episode(summary, key)
        if current is not None and current.failure_class is not RetryFailureClass.MECHANICAL:
            message = "legacy worker counters conflict with the episode failure class"
            raise RetryLedgerConflictError(message)
        adopt = existing_attempt is not None and (current is None or existing_attempt[0] not in current.attempt_ids)
        if current is not None and (current.reset_count > 0 or (current.legacy_failures >= count and not adopt)):
            return current
        observed = _retry_time(now)
        if current is None:
            current = RetryEpisodeSummary(episode_id=key.identity, key=key, failure_class=RetryFailureClass.MECHANICAL)
        total = current.total_attempts + max(0, count - current.legacy_failures) + int(adopt)
        exhausted = total >= self.mechanical_repairs + 1
        next_times = tuple(
            value
            for value in (
                current.next_eligible_at,
                None if exhausted else _retry_timestamp(observed + timedelta(seconds=2)),
            )
            if value is not None
        )
        next_eligible_at = max(next_times, key=_retry_time) if next_times else None
        attempt = (
            RetryAttempt(
                attempt_id=existing_attempt[0],
                episode_id=current.episode_id,
                key=current.key,
                failure_class=RetryFailureClass.MECHANICAL,
                kind="repair",
                reserved_at=_retry_timestamp(observed),
                operation_alias=existing_attempt[1],
            )
            if adopt
            else None
        )
        episode = current.model_copy(
            update={
                "total_attempts": total,
                "repair_attempts": max(0, total - 1),
                "legacy_failures": max(count, current.legacy_failures),
                "attempt_ids": (*current.attempt_ids, attempt.attempt_id) if attempt else current.attempt_ids,
                "last_status": (
                    "contained"
                    if current.stop_code is RetryStopCode.CONTAINMENT or current.last_status == "contained"
                    else "reserved"
                    if attempt is not None or _pending_attempts(current)
                    else "failed"
                ),
                "last_failure_at": current.last_failure_at or _retry_timestamp(observed),
                "next_eligible_at": next_eligible_at,
                "stop_code": current.stop_code or (RetryStopCode.EXHAUSTED if exhausted else None),
            }
        )
        self._commit_summary(
            previous,
            summary.model_copy(
                update={
                    "version": summary.version + 1,
                    "updated_at": _retry_timestamp(observed),
                    "episodes": _replace_episode(summary.episodes, episode),
                }
            ),
            RetryAttempt if attempt is not None else None,
            attempt,
        )
        return episode

    def owner_result_participants(
        self,
        attempt_id: str,
        *,
        accepted: bool,
        now: datetime | str,
        failure_code: str = "worker-blocked",
        accepted_progress: bool = True,
        repair_outcome_id: str | None = None,
        repair_task_id: str | None = None,
        completed_commit: str | None = None,
    ) -> tuple[TransactionParticipant, ...]:
        """Prepare evidence for the owner's transaction, not a separate accounting write."""
        episode = _episode_for_attempt(self.read(), attempt_id)
        if episode is None:
            return ()
        result = RetryOwnerResult(
            attempt_id=attempt_id,
            episode_id=episode.episode_id,
            accepted=accepted,
            observed_at=_retry_timestamp(_retry_time(now)),
            failure_code=failure_code,
            accepted_progress=accepted_progress,
            repair_outcome_id=repair_outcome_id,
            repair_task_id=repair_task_id,
            completed_commit=completed_commit,
        )
        return (
            TransactionParticipant(
                self.runtime_root, self._directory / "owner-results" / f"{attempt_id}.json", encoded(result)
            ),
        )

    def repair_binding_participant(
        self,
        *,
        original_attempt_id: str,
        repair_attempt_id: str,
        repair_task_id: str,
        outcome_id: str,
        now: datetime | str,
        allow_settled: bool = False,
    ) -> TransactionParticipant:
        """Prepare an immutable repair-to-original link for the owning transaction."""
        summary, _previous = self._read_with_bytes()
        episode = _episode_for_attempt(summary, repair_attempt_id)
        if episode is None or original_attempt_id not in episode.attempt_ids:
            raise RetryLedgerConflictError("repair attempts do not share one retry episode")
        original = self._read_attempt(original_attempt_id)
        repair = self._read_attempt(repair_attempt_id)
        if (
            original.episode_id != episode.episode_id
            or repair.episode_id != episode.episode_id
            or original.key != episode.key
            or repair.key != episode.key
            or original.kind != "original"
            or repair.kind != "repair"
            or original.failure_class is not RetryFailureClass.MECHANICAL
            or repair.failure_class is not RetryFailureClass.MECHANICAL
            or digest(f"{original_attempt_id}:failed".encode()) not in episode.outcome_ids
            or (not allow_settled and repair_attempt_id not in _pending_attempts(episode))
        ):
            raise RetryLedgerConflictError("repair-to-original link does not match retry authority")
        binding = RetryRepairBinding.create(
            change_id=self.change_id,
            episode_id=episode.episode_id,
            original_attempt_id=original_attempt_id,
            repair_attempt_id=repair_attempt_id,
            repair_task_id=repair_task_id,
            outcome_id=outcome_id,
            created_at=_retry_timestamp(_retry_time(now)),
        )
        relative = self._repair_bindings_path / f"{binding.binding_id}.json"
        try:
            existing = RetryRepairBinding.model_validate_json(read_record(self.runtime_root, relative))
        except FileNotFoundError:
            existing = None
        except (OSError, TypeError, ValueError) as exc:
            raise RetryLedgerCorruptError from exc
        if allow_settled and existing is None:
            raise RetryLedgerConflictError("completed repair is missing its durable repair link")
        if existing is not None and existing != binding:
            raise RetryLedgerConflictError("repair-to-original link conflicts with existing authority")
        return TransactionParticipant(self.runtime_root, relative, encoded(binding))

    def repair_bindings(self) -> tuple[RetryRepairBinding, ...]:
        """Read bounded immutable repair links, never treating task IDs as authority."""
        try:
            RuntimeTransaction.recover_all(self.runtime_root)
        except (OSError, RuntimeError, ValueError) as exc:
            raise RetryLedgerCorruptError from exc
        directory = self.runtime_root / self._repair_bindings_path
        try:
            paths = tuple(sorted(directory.iterdir(), key=lambda item: item.name))
        except FileNotFoundError:
            return ()
        except OSError as exc:
            raise RetryLedgerCorruptError from exc
        if len(paths) > _MAX_REPAIR_BINDINGS:
            raise RetryLedgerCorruptError
        bindings = []
        for path in paths:
            if not path.is_file() or path.name != f"{path.stem}.json" or len(path.stem) != _DIGEST_LENGTH:
                raise RetryLedgerCorruptError
            try:
                binding = RetryRepairBinding.model_validate_json(
                    read_record(self.runtime_root, path.relative_to(self.runtime_root))
                )
            except (OSError, TypeError, ValueError) as exc:
                raise RetryLedgerCorruptError from exc
            if binding.binding_id != path.stem or binding.change_id != self.change_id:
                raise RetryLedgerCorruptError
            self._validate_repair_binding(binding)
            bindings.append(binding)
        return tuple(bindings)

    def repair_binding_for_attempt(
        self,
        attempt_id: str,
        *,
        outcome_id: str | None = None,
    ) -> RetryRepairBinding | None:
        """Resolve a repair reservation through its durable binding."""
        matches = tuple(
            binding
            for binding in self.repair_bindings()
            if binding.repair_attempt_id == attempt_id
            and (outcome_id is None or binding.outcome_id == outcome_id)
        )
        if len(matches) > 1:
            raise RetryLedgerCorruptError
        return matches[0] if matches else None

    def record_repair_owner_result(self, result: RetryOwnerResult) -> RetryEpisodeSummary:
        """Consume one exact repair-task result without resetting its failed episode."""
        if (
            not result.accepted
            or result.accepted_progress
            or result.repair_outcome_id is None
            or result.repair_task_id is None
            or result.completed_commit is None
        ):
            raise RetryLedgerConflictError("repair owner result is not an accepted no-reset result")
        summary, previous = self._read_with_bytes()
        episode = _episode_for_attempt(summary, result.attempt_id)
        if episode is None or episode.episode_id != result.episode_id:
            raise RetryLedgerConflictError("repair owner result is not bound to its retry episode")
        matches = tuple(
            binding
            for binding in self.repair_bindings()
            if binding.repair_attempt_id == result.attempt_id
        )
        if len(matches) != 1:
            raise RetryLedgerConflictError("repair owner result has no unique durable repair binding")
        binding = matches[0]
        self._validate_repair_binding(binding, summary)
        if (
            binding.episode_id != result.episode_id
            or binding.outcome_id != result.repair_outcome_id
            or binding.repair_task_id != result.repair_task_id
        ):
            raise RetryLedgerConflictError("repair owner result identity conflicts with its durable receipt")
        success_id = digest(f"{result.attempt_id}:succeeded".encode())
        if (
            digest(f"{result.attempt_id}:failed".encode()) in episode.outcome_ids
            or digest(f"{result.attempt_id}:contained".encode()) in episode.outcome_ids
        ):
            raise RetryLedgerConflictError("repair owner result arrived after a terminal non-success outcome")
        aliases = episode.aliases
        if not any(alias.alias_kind == "commit" and alias.value == result.completed_commit for alias in aliases):
            aliases = (
                *aliases,
                RetryEpisodeAlias(
                    alias_kind="commit",
                    value=result.completed_commit,
                    observed_at=result.observed_at,
                ),
            )
        if success_id in episode.outcome_ids and aliases == episode.aliases:
            return episode
        updated = episode.model_copy(
            update={
                "outcome_ids": (
                    (*episode.outcome_ids, success_id) if success_id not in episode.outcome_ids else episode.outcome_ids
                ),
                "aliases": aliases,
                "last_status": "succeeded",
                "next_eligible_at": None,
                "stop_code": None,
            }
        )
        outcome = (
            RetryAttemptOutcome(
                attempt_id=result.attempt_id,
                episode_id=episode.episode_id,
                status="succeeded",
                observed_at=result.observed_at,
            )
            if success_id not in episode.outcome_ids
            else None
        )
        self._commit_summary(
            previous,
            summary.model_copy(
                update={
                    "version": summary.version + 1,
                    "updated_at": result.observed_at,
                    "episodes": _replace_episode(summary.episodes, updated),
                }
            ),
            RetryAttemptOutcome if outcome is not None else None,
            outcome,
            outcome_id=success_id if outcome is not None else None,
        )
        return updated

    def record_repair_acceptance(self, result: RetryOwnerResult) -> RetryEpisodeSummary:
        """Compatibility name for exact owner-result repair settlement."""
        return self.record_repair_owner_result(result)

    def reconcile_owner_results(self) -> None:
        """Finish accounting from exact durable receipts, without caller replay or refund."""
        for episode in self.read().episodes:
            for attempt_id in _pending_attempts(episode):
                path = self.runtime_root / self._directory / "owner-results" / f"{attempt_id}.json"
                try:
                    result = RetryOwnerResult.model_validate_json(path.read_bytes())
                except FileNotFoundError:
                    continue
                attempt = self._read_attempt(attempt_id)
                if result.attempt_id != attempt_id or result.episode_id != episode.episode_id:
                    raise RetryLedgerCorruptError
                if (
                    attempt.episode_id != episode.episode_id
                    or attempt.attempt_id != attempt_id
                    or attempt.key != episode.key
                ):
                    raise RetryLedgerCorruptError
                if result.repair_task_id is not None:
                    self.record_repair_owner_result(result)
                elif result.accepted:
                    self.record_success(
                        attempt_id,
                        now=result.observed_at,
                        accepted_progress=result.accepted_progress,
                    )
                else:
                    self.record_failure(attempt_id, failure_code=result.failure_code, now=result.observed_at)

    def pending_attempts(self) -> tuple[RetryAttempt, ...]:
        """Read unresolved immutable reservations for exact owner reconciliation."""
        pending = []
        for episode in self.read().episodes:
            for attempt_id in _pending_attempts(episode):
                attempt = RetryAttempt.model_validate_json(
                    read_record(self.runtime_root, self._attempts_path / f"{attempt_id}.json")
                )
                if (
                    attempt.episode_id != episode.episode_id
                    or attempt.attempt_id != attempt_id
                    or attempt.key != episode.key
                ):
                    raise RetryLedgerCorruptError
                pending.append(attempt)
        return tuple(pending)

    def reserve(  # noqa: C901, PLR0912, PLR0913, PLR0911, PLR0915 - bounded retry policy.
        self,
        key: RetryEpisodeKey,
        *,
        failure_class: RetryFailureClass | str,
        now: datetime | str | None = None,
        attempt_id: str | None = None,
        automatic: bool = True,
        original: bool = False,
        operation_alias: str | None = None,
        resume_attempt_id: str | None = None,
    ) -> RetryReservation:
        """Reserve one attempt atomically before dispatch/effect entry.

        Reusing an existing attempt ID is an idempotent replay and does not
        consume another allowance.
        """
        if key.change_id != self.change_id:
            raise ValueError("retry key belongs to another Change")
        policy = _retry_failure_class(failure_class)
        observed = _retry_time(now if now is not None else self._clock())
        summary, previous = self._read_with_bytes()
        current = _matching_episode(summary, key)
        requested_key = key
        if resume_attempt_id is not None:
            links = tuple(item for item in self.repair_bindings() if item.original_attempt_id == resume_attempt_id)
            if not links:
                raise RetryLedgerConflictError("original action has no completed repair link")
            linked = links[0]
            linked_episode = _episode_for_attempt(summary, linked.repair_attempt_id)
            if (
                linked_episode is None
                or linked_episode.episode_id != linked.episode_id
                or any(item.episode_id != linked.episode_id for item in links)
                or linked_episode.key.change_id != key.change_id
                or linked_episode.key.action_kind != key.action_kind
                or linked_episode.key.target_head != key.target_head
            ):
                raise RetryLedgerConflictError("replacement action does not match the repaired episode")
            if current is not None and current.episode_id != linked.episode_id:
                raise RetryLedgerConflictError("replacement action does not match the repaired episode")
            if current is None:
                current = linked_episode
        if current is not None:
            key = current.key
        if current is not None and current.failure_class is not policy:
            raise RetryLedgerConflictError("retry episode changed failure class")
        if original and current is not None:
            raise RetryLedgerConflictError("original retry attempt already exists for this episode")
        if current is not None and attempt_id is not None and attempt_id in current.attempt_ids:
            return RetryReservation(
                episode_id=current.episode_id,
                attempt_id=attempt_id,
                allowed=True,
                replayed=True,
                reason_code="retry-replayed",
                attempts=current.total_attempts,
                next_eligible_at=current.next_eligible_at,
                stop_code=current.stop_code,
            )
        if current is not None and _pending_attempts(current):
            if current.stop_code is not RetryStopCode.CONTAINMENT:
                contained = current.model_copy(
                    update={
                        "last_status": "contained",
                        "stop_code": RetryStopCode.CONTAINMENT,
                    }
                )
                self._commit_summary(
                    previous,
                    summary.model_copy(
                        update={
                            "version": summary.version + 1,
                            "updated_at": _retry_timestamp(observed),
                            "episodes": _replace_episode(summary.episodes, contained),
                        }
                    ),
                )
                current = contained
            return RetryReservation(
                episode_id=current.episode_id,
                allowed=False,
                reason_code=RetryStopCode.CONTAINMENT.value,
                attempts=current.total_attempts,
                stop_code=RetryStopCode.CONTAINMENT,
            )
        explicit_acceptance = (
            policy is RetryFailureClass.ACCEPTANCE
            and not automatic
            and current is not None
            and current.stop_code is RetryStopCode.ACCEPTANCE_WAIT
            and current.explicit_observations == 0
        )
        if policy is RetryFailureClass.ACCEPTANCE and not automatic and not explicit_acceptance:
            return RetryReservation(
                episode_id=key.identity,
                allowed=False,
                reason_code=RetryStopCode.ACCEPTANCE_WAIT.value,
                attempts=current.total_attempts if current else 0,
                stop_code=RetryStopCode.ACCEPTANCE_WAIT,
            )
        if (
            current is not None
            and current.next_eligible_at is not None
            and observed < _retry_time(current.next_eligible_at)
            and not explicit_acceptance
        ):
            return RetryReservation(
                episode_id=current.episode_id,
                allowed=False,
                reason_code=RetryStopCode.BACKOFF.value,
                attempts=current.total_attempts,
                next_eligible_at=current.next_eligible_at,
                stop_code=RetryStopCode.BACKOFF,
            )
        if current is not None and current.stop_code is not None and not explicit_acceptance:
            return RetryReservation(
                episode_id=current.episode_id,
                allowed=False,
                reason_code=current.stop_code.value,
                attempts=current.total_attempts,
                next_eligible_at=current.next_eligible_at,
                stop_code=current.stop_code,
            )

        first = current is None or current.total_attempts == 0
        kind = "observation" if policy is RetryFailureClass.ACCEPTANCE else "original" if first else "repair"
        total = current.total_attempts if current else 0
        repairs = current.repair_attempts if current else 0
        observations = current.observation_attempts if current else 0
        explicit_observations = current.explicit_observations if current else 0
        if policy is RetryFailureClass.CONTAINED and automatic:
            return RetryReservation(
                episode_id=key.identity,
                allowed=False,
                reason_code=RetryStopCode.CONTAINMENT.value,
                attempts=total,
                stop_code=RetryStopCode.CONTAINMENT,
            )
        if policy is RetryFailureClass.MECHANICAL and not first and not original and repairs >= self.mechanical_repairs:
            return RetryReservation(
                episode_id=key.identity,
                allowed=False,
                reason_code=RetryStopCode.EXHAUSTED.value,
                attempts=total,
                stop_code=RetryStopCode.EXHAUSTED,
            )
        if policy is RetryFailureClass.TRANSIENT and total >= self.transient_attempts:
            return RetryReservation(
                episode_id=key.identity,
                allowed=False,
                reason_code=RetryStopCode.EXHAUSTED.value,
                attempts=total,
                stop_code=RetryStopCode.EXHAUSTED,
            )
        if policy is RetryFailureClass.ACCEPTANCE and automatic and observations >= self.acceptance_observations:
            return RetryReservation(
                episode_id=key.identity,
                allowed=False,
                reason_code=RetryStopCode.ACCEPTANCE_WAIT.value,
                attempts=total,
                stop_code=RetryStopCode.ACCEPTANCE_WAIT,
            )
        if policy is RetryFailureClass.ACCEPTANCE and not automatic and explicit_observations >= 1:
            return RetryReservation(
                episode_id=key.identity,
                allowed=False,
                reason_code=RetryStopCode.ACCEPTANCE_WAIT.value,
                attempts=total,
                stop_code=RetryStopCode.ACCEPTANCE_WAIT,
            )

        if attempt_id is None:
            seed = f"{key.identity}:{kind}:{total + 1}:{observed.isoformat()}"
            reserved_id = digest(seed.encode())
            existing_attempts = set(current.attempt_ids if current is not None else ())
            collision = 0
            while reserved_id in existing_attempts:
                collision += 1
                reserved_id = digest(f"{seed}:{collision}".encode())
        else:
            reserved_id = attempt_id
        aliases = current.aliases if current else ()
        if requested_key != key:
            aliases = (
                *aliases,
                RetryEpisodeAlias(
                    alias_kind="commit",
                    value=requested_key.exact_head,
                    observed_at=_retry_timestamp(observed),
                ),
            )
        if operation_alias is not None and not any(
            alias.alias_kind == "operation" and alias.value == operation_alias for alias in aliases
        ):
            aliases = (
                *aliases,
                RetryEpisodeAlias(
                    alias_kind="operation",
                    value=operation_alias,
                    observed_at=_retry_timestamp(observed),
                ),
            )
        attempt = RetryAttempt(
            attempt_id=reserved_id,
            episode_id=key.identity,
            key=key,
            failure_class=policy,
            kind=kind,
            automatic=automatic,
            reserved_at=_retry_timestamp(observed),
            operation_alias=operation_alias,
        )
        updated = RetryEpisodeSummary(
            episode_id=key.identity,
            key=key,
            failure_class=policy,
            policy_version=self.policy_version,
            attempt_ids=(*current.attempt_ids, reserved_id) if current else (reserved_id,),
            outcome_ids=current.outcome_ids if current else (),
            accepted_attempt_ids=current.accepted_attempt_ids if current else (),
            aliases=aliases,
            total_attempts=total + (1 if policy is not RetryFailureClass.ACCEPTANCE or automatic else 0),
            repair_attempts=repairs + (1 if kind == "repair" else 0),
            observation_attempts=observations + (1 if kind == "observation" else 0),
            explicit_observations=explicit_observations
            + (1 if policy is RetryFailureClass.ACCEPTANCE and not automatic else 0),
            last_status="reserved",
            last_failure_at=current.last_failure_at if current else None,
            next_eligible_at=current.next_eligible_at if current else None,
            stop_code=(
                None
                if policy is RetryFailureClass.ACCEPTANCE and not automatic
                else current.stop_code
                if current
                else None
            ),
            reset_count=current.reset_count if current else 0,
            legacy_failures=current.legacy_failures if current else 0,
        )
        self._commit_summary(
            previous,
            summary.model_copy(
                update={
                    "version": summary.version + 1,
                    "updated_at": _retry_timestamp(observed),
                    "episodes": _replace_episode(summary.episodes, updated),
                }
            ),
            RetryAttempt,
            attempt,
        )
        return RetryReservation(
            episode_id=key.identity,
            attempt_id=reserved_id,
            allowed=True,
            reason_code="retry-reserved",
            attempts=updated.total_attempts,
            next_eligible_at=updated.next_eligible_at,
            stop_code=updated.stop_code,
        )

    def record_failure(
        self,
        reservation: RetryReservation | str,
        *,
        failure_code: str,
        failure_detail: str | None = None,
        now: datetime | str | None = None,
    ) -> RetryEpisodeSummary:
        """Persist one bounded failure outcome and its next eligible time."""
        attempt_id = reservation.attempt_id if isinstance(reservation, RetryReservation) else reservation
        if not attempt_id:
            raise ValueError("failure requires a reserved attempt")
        observed = _retry_time(now if now is not None else self._clock())
        summary, previous = self._read_with_bytes()
        episode = _episode_for_attempt(summary, attempt_id)
        if episode is None:
            raise RetryLedgerConflictError("attempt is not part of the current retry summary")
        outcome_id = digest(f"{attempt_id}:failed".encode())
        if outcome_id in episode.outcome_ids or digest(f"{attempt_id}:succeeded".encode()) in episode.outcome_ids:
            return episode
        delay_index = (
            episode.repair_attempts
            if episode.failure_class is RetryFailureClass.MECHANICAL
            else episode.total_attempts - 1
        )
        delay = self.backoff_seconds[min(delay_index, len(self.backoff_seconds) - 1)]
        next_at = observed + timedelta(seconds=delay)
        attempts_limit_reached = (
            episode.failure_class is RetryFailureClass.MECHANICAL and episode.repair_attempts >= self.mechanical_repairs
        ) or (
            episode.failure_class is RetryFailureClass.TRANSIENT and episode.total_attempts >= self.transient_attempts
        )
        acceptance_limit_reached = (
            episode.failure_class is RetryFailureClass.ACCEPTANCE
            and episode.observation_attempts >= self.acceptance_observations
        )
        stop = (
            RetryStopCode.ACCEPTANCE_WAIT
            if acceptance_limit_reached
            else RetryStopCode.EXHAUSTED
            if attempts_limit_reached
            else None
        )
        status = "waiting" if acceptance_limit_reached else "failed"
        outcome = RetryAttemptOutcome(
            attempt_id=attempt_id,
            episode_id=episode.episode_id,
            status=status,
            observed_at=_retry_timestamp(observed),
            failure_code=failure_code,
            failure_detail=failure_detail,
            next_eligible_at=None if stop is not None else _retry_timestamp(next_at),
            stop_code=stop,
        )
        updated = episode.model_copy(
            update={
                "outcome_ids": (*episode.outcome_ids, outcome_id),
                "last_status": status,
                "last_failure_at": _retry_timestamp(observed),
                "next_eligible_at": None if stop is not None else _retry_timestamp(next_at),
                "stop_code": stop,
            }
        )
        self._commit_summary(
            previous,
            summary.model_copy(
                update={
                    "version": summary.version + 1,
                    "updated_at": _retry_timestamp(observed),
                    "episodes": _replace_episode(summary.episodes, updated),
                }
            ),
            RetryAttemptOutcome,
            outcome,
            outcome_id=outcome_id,
        )
        return updated

    def record_success(
        self,
        reservation: RetryReservation | str,
        *,
        now: datetime | str | None = None,
        accepted_progress: bool = False,
    ) -> RetryEpisodeSummary:
        """Record an accepted attempt without erasing its immutable history."""
        attempt_id = reservation.attempt_id if isinstance(reservation, RetryReservation) else reservation
        if not attempt_id:
            raise ValueError("success requires a reserved attempt")
        observed = _retry_time(now if now is not None else self._clock())
        summary, previous = self._read_with_bytes()
        episode = _episode_for_attempt(summary, attempt_id)
        if episode is None:
            raise RetryLedgerConflictError("attempt is not part of the current retry summary")
        outcome_id = digest(f"{attempt_id}:succeeded".encode())
        if (
            outcome_id in episode.outcome_ids
            or digest(f"{attempt_id}:failed".encode()) in episode.outcome_ids
            or digest(f"{attempt_id}:contained".encode()) in episode.outcome_ids
        ):
            return episode
        outcome = RetryAttemptOutcome(
            attempt_id=attempt_id,
            episode_id=episode.episode_id,
            status="succeeded",
            observed_at=_retry_timestamp(observed),
        )
        updated = episode.model_copy(
            update={
                "outcome_ids": (*episode.outcome_ids, outcome_id),
                "last_status": "succeeded",
                "next_eligible_at": None,
                "stop_code": None,
            }
        )
        if accepted_progress:
            updated = updated.model_copy(
                update={
                    "accepted_attempt_ids": (*episode.accepted_attempt_ids, attempt_id),
                    "total_attempts": 0,
                    "repair_attempts": 0,
                    "observation_attempts": 0,
                    "explicit_observations": 0,
                    "last_status": None,
                    "last_failure_at": None,
                    "reset_count": episode.reset_count + 1,
                }
            )
        elif (
            episode.failure_class is RetryFailureClass.ACCEPTANCE
            and episode.observation_attempts >= self.acceptance_observations
        ):
            updated = updated.model_copy(update={"last_status": "waiting", "stop_code": RetryStopCode.ACCEPTANCE_WAIT})
        self._commit_summary(
            previous,
            summary.model_copy(
                update={
                    "version": summary.version + 1,
                    "updated_at": _retry_timestamp(observed),
                    "episodes": _replace_episode(summary.episodes, updated),
                }
            ),
            RetryAttemptOutcome,
            outcome,
            outcome_id=outcome_id,
        )
        return updated

    def record_accepted_progress(
        self,
        reservation: RetryReservation | str,
        *,
        now: datetime | str | None = None,
    ) -> RetryEpisodeSummary:
        """Record accepted progress and reset only that episode's current budget."""
        return self.record_success(reservation, now=now, accepted_progress=True)

    def attempt_for_operation(self, operation: str) -> str | None:
        """Resolve an exact issued worker operation through immutable reservations."""
        for episode in self.read().episodes:
            for attempt_id in episode.attempt_ids:
                attempt = RetryAttempt.model_validate_json(
                    read_record(self.runtime_root, self._attempts_path / f"{attempt_id}.json")
                )
                if attempt.episode_id != episode.episode_id or attempt.attempt_id != attempt_id:
                    raise RetryLedgerCorruptError
                if attempt.operation_alias == operation:
                    return attempt_id
        return None

    def record_recovery_release(
        self,
        reservation: RetryReservation | str,
        *,
        now: datetime | str | None = None,
    ) -> RetryEpisodeSummary:
        """Record verified release of an interrupted reservation without replenishing counts."""
        attempt_id = reservation.attempt_id if isinstance(reservation, RetryReservation) else reservation
        if not attempt_id:
            raise ValueError("recovery release requires a reserved attempt")
        observed = _retry_time(now if now is not None else self._clock())
        summary, previous = self._read_with_bytes()
        episode = _episode_for_attempt(summary, attempt_id)
        if episode is None:
            raise RetryLedgerConflictError("attempt is not part of the current retry summary")
        outcome_id = digest(f"{attempt_id}:contained".encode())
        if (
            outcome_id in episode.outcome_ids
            or digest(f"{attempt_id}:failed".encode()) in episode.outcome_ids
            or digest(f"{attempt_id}:succeeded".encode()) in episode.outcome_ids
        ):
            return episode
        outcome = RetryAttemptOutcome(
            attempt_id=attempt_id,
            episode_id=episode.episode_id,
            status="contained",
            observed_at=_retry_timestamp(observed),
        )
        stop_code = None if episode.stop_code is RetryStopCode.CONTAINMENT else episode.stop_code
        updated = episode.model_copy(
            update={
                "outcome_ids": (*episode.outcome_ids, outcome_id),
                "last_status": "succeeded",
                "next_eligible_at": episode.next_eligible_at,
                "stop_code": stop_code,
            }
        )
        self._commit_summary(
            previous,
            summary.model_copy(
                update={
                    "version": summary.version + 1,
                    "updated_at": _retry_timestamp(observed),
                    "episodes": _replace_episode(summary.episodes, updated),
                }
            ),
            RetryAttemptOutcome,
            outcome,
            outcome_id=outcome_id,
        )
        return updated

    def record_recovery_release_for_outcome(
        self,
        outcome_id: str,
        *,
        now: datetime | str | None = None,
    ) -> tuple[RetryEpisodeSummary, ...]:
        """Release pending worker reservations for one exact outcome without resetting budgets."""
        summary, _ = self._read_with_bytes()
        attempts = tuple(
            attempt_id
            for episode in summary.episodes
            if episode.key.outcome_id == outcome_id
            for attempt_id in _pending_attempts(episode)
        )
        return tuple(self.record_recovery_release(attempt_id, now=now) for attempt_id in attempts)

    def record_alias(
        self,
        key: RetryEpisodeKey,
        *,
        alias_kind: Literal["operation", "session", "commit", "task", "report", "failure-code", "observation", "label"],
        value: str,
        now: datetime | str | None = None,
    ) -> RetryEpisodeSummary:
        """Retain a renamed operation/report/commit as history for the same episode."""
        observed = _retry_time(now if now is not None else self._clock())
        summary, previous = self._read_with_bytes()
        episode = next((item for item in summary.episodes if item.episode_id == key.identity), None)
        if episode is None:
            raise RetryLedgerConflictError("cannot alias an unknown retry episode")
        alias = RetryEpisodeAlias(alias_kind=alias_kind, value=value, observed_at=_retry_timestamp(observed))
        if alias in episode.aliases:
            return episode
        updated = episode.model_copy(update={"aliases": (*episode.aliases, alias)})
        self._commit_summary(
            previous,
            summary.model_copy(
                update={
                    "version": summary.version + 1,
                    "updated_at": _retry_timestamp(observed),
                    "episodes": _replace_episode(summary.episodes, updated),
                }
            ),
        )
        return updated

    def reset(
        self,
        key: RetryEpisodeKey,
        *,
        accepted_progress: bool,
        now: datetime | str | None = None,
    ) -> RetryEpisodeSummary:
        """Reset only one episode after caller-provided accepted progress."""
        if not accepted_progress:
            raise ValueError("retry reset requires accepted progress for the affected episode")
        observed = _retry_time(now if now is not None else self._clock())
        summary, previous = self._read_with_bytes()
        episode = next((item for item in summary.episodes if item.episode_id == key.identity), None)
        if episode is None:
            raise RetryLedgerConflictError("cannot reset an unknown retry episode")
        updated = episode.model_copy(
            update={
                "attempt_ids": episode.attempt_ids,
                "outcome_ids": episode.outcome_ids,
                "total_attempts": 0,
                "repair_attempts": 0,
                "observation_attempts": 0,
                "explicit_observations": 0,
                "last_status": None,
                "last_failure_at": None,
                "next_eligible_at": None,
                "stop_code": None,
                "reset_count": episode.reset_count + 1,
            }
        )
        self._commit_summary(
            previous,
            summary.model_copy(
                update={
                    "version": summary.version + 1,
                    "updated_at": _retry_timestamp(observed),
                    "episodes": _replace_episode(summary.episodes, updated),
                }
            ),
        )
        return updated

    def _read_attempt(self, attempt_id: str) -> RetryAttempt:
        try:
            attempt = RetryAttempt.model_validate_json(
                read_record(self.runtime_root, self._attempts_path / f"{attempt_id}.json")
            )
        except (OSError, TypeError, ValueError) as exc:
            raise RetryLedgerCorruptError from exc
        if attempt.attempt_id != attempt_id:
            raise RetryLedgerCorruptError
        return attempt

    def _validate_repair_binding(
        self,
        binding: RetryRepairBinding,
        summary: RetryLedgerSummary | None = None,
    ) -> None:
        """Require an immutable repair link to match the ledger's attempt authority."""
        episode = _episode_for_attempt(summary or self.read(), binding.repair_attempt_id)
        if episode is None or episode.episode_id != binding.episode_id:
            raise RetryLedgerCorruptError
        original = self._read_attempt(binding.original_attempt_id)
        repair = self._read_attempt(binding.repair_attempt_id)
        if (
            original.episode_id != episode.episode_id
            or repair.episode_id != episode.episode_id
            or original.key != episode.key
            or repair.key != episode.key
            or original.kind != "original"
            or repair.kind != "repair"
            or original.failure_class is not RetryFailureClass.MECHANICAL
            or repair.failure_class is not RetryFailureClass.MECHANICAL
            or digest(f"{binding.original_attempt_id}:failed".encode()) not in episode.outcome_ids
        ):
            raise RetryLedgerCorruptError

    def _read_with_bytes(self) -> tuple[RetryLedgerSummary, bytes | None]:
        try:
            RuntimeTransaction.recover_all(self.runtime_root)
        except (OSError, RuntimeError, ValueError) as exc:
            raise RetryLedgerCorruptError from exc
        try:
            previous = self.summary_path.read_bytes()
        except FileNotFoundError:
            return RetryLedgerSummary.empty(self.change_id), None
        except OSError as exc:
            raise RetryLedgerCorruptError from exc
        try:
            summary = RetryLedgerSummary.model_validate_json(previous, strict=False)
        except (TypeError, ValueError) as exc:
            raise RetryLedgerCorruptError from exc
        if summary.change_id != self.change_id:
            raise RetryLedgerCorruptError
        return summary, previous

    def _commit_summary(
        self,
        previous: bytes | None,
        summary: RetryLedgerSummary,
        record_type: type[RetryAttempt | RetryAttemptOutcome] | None = None,
        record: RetryAttempt | RetryAttemptOutcome | None = None,
        *,
        outcome_id: str | None = None,
    ) -> None:
        participants: list[TransactionParticipant | ReplacementTransactionParticipant] = []
        if record_type is RetryAttempt and isinstance(record, RetryAttempt):
            relative = self._attempts_path / f"{record.attempt_id}.json"
            content = encoded(record)
            participants.append(TransactionParticipant(self.runtime_root, relative, content))
        elif record_type is RetryAttemptOutcome and isinstance(record, RetryAttemptOutcome):
            identity = outcome_id or digest(encoded(record))
            relative = self._outcomes_path / f"{identity}.json"
            content = encoded(record)
            participants.append(TransactionParticipant(self.runtime_root, relative, content))
        summary_content = encoded(summary)
        if previous is None:
            participants.append(TransactionParticipant(self.runtime_root, self._summary_path, summary_content))
        else:
            participants.append(
                ReplacementTransactionParticipant(
                    self.runtime_root,
                    self._summary_path,
                    previous,
                    summary_content,
                )
            )
        transaction_id = digest(
            b"retry-ledger\0"
            + (previous or b"")
            + b"\0"
            + b"\0".join(
                participant.content
                if isinstance(participant, TransactionParticipant)
                else participant.replacement_content
                for participant in participants
            )
        )
        try:
            RuntimeTransaction(self.runtime_root, f"retry-ledger-{transaction_id}", tuple(participants)).commit()
        except TransactionConflictError as exc:
            raise RetryLedgerConflictError from exc


def _retry_failure_class(value: RetryFailureClass | str) -> RetryFailureClass:
    try:
        return value if isinstance(value, RetryFailureClass) else RetryFailureClass(value)
    except ValueError:
        aliases = {
            "mechanical": RetryFailureClass.MECHANICAL,
            "builder": RetryFailureClass.MECHANICAL,
            "check": RetryFailureClass.MECHANICAL,
            "transient": RetryFailureClass.TRANSIENT,
            "acceptance": RetryFailureClass.ACCEPTANCE,
            "contained": RetryFailureClass.CONTAINED,
        }
        try:
            return aliases[value]
        except KeyError as exc:
            message = f"unknown retry failure class: {value}"
            raise ValueError(message) from exc


def _retry_time(value: datetime | str) -> datetime:
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("retry clock must be an ISO timestamp") from exc
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("retry clock must be timezone-aware")
    return value.astimezone(UTC)


def _retry_timestamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _replace_episode(
    episodes: tuple[RetryEpisodeSummary, ...],
    replacement: RetryEpisodeSummary,
) -> tuple[RetryEpisodeSummary, ...]:
    if any(item.episode_id == replacement.episode_id for item in episodes):
        return tuple(replacement if item.episode_id == replacement.episode_id else item for item in episodes)
    return (*episodes, replacement)


def _matching_episode(summary: RetryLedgerSummary, key: RetryEpisodeKey) -> RetryEpisodeSummary | None:
    exact = next((item for item in summary.episodes if item.episode_id == key.identity), None)
    if key.outcome_id is None:
        if exact is not None:
            return exact
        candidates = tuple(
            item
            for item in summary.episodes
            if item.total_attempts
            and item.key.action_kind == key.action_kind
            and item.key.target_head == key.target_head
            and item.key.finalization_id == key.finalization_id
            and any(alias.alias_kind == "commit" and alias.value == key.exact_head for alias in item.aliases)
        )
        if len(candidates) > 1:
            raise RetryLedgerConflictError("multiple engine retry episodes cover this commit alias")
        return candidates[0] if candidates else None
    candidates = tuple(
        item
        for item in summary.episodes
        if item.total_attempts
        and item.key.action_kind == key.action_kind
        and item.key.contract_digest == key.contract_digest
        and item.key.outcome_id == key.outcome_id
        and item.key.procedure_class == key.procedure_class
        and (
            item.key.task_lineage == key.task_lineage
            or any(alias.alias_kind == "task" and alias.value == key.task_lineage for alias in item.aliases)
        )
    )
    if len(candidates) > 1:
        raise RetryLedgerConflictError("multiple unresolved retry episodes cover this action")
    return candidates[0] if candidates else exact


def _episode_for_attempt(summary: RetryLedgerSummary, attempt_id: str) -> RetryEpisodeSummary | None:
    return next((episode for episode in summary.episodes if attempt_id in episode.attempt_ids), None)


def _pending_attempts(episode: RetryEpisodeSummary) -> tuple[str, ...]:
    """Return reservations without a durable terminal outcome."""
    return tuple(
        attempt_id
        for attempt_id in episode.attempt_ids
        if digest(f"{attempt_id}:failed".encode()) not in episode.outcome_ids
        and digest(f"{attempt_id}:succeeded".encode()) not in episode.outcome_ids
        and digest(f"{attempt_id}:contained".encode()) not in episode.outcome_ids
    )
