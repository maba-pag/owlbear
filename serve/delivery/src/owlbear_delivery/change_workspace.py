"""Per-change writer coordination and Git workspace management."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from contextlib import contextmanager
from datetime import UTC, datetime
from enum import StrEnum
from itertools import pairwise
from pathlib import Path
from typing import TYPE_CHECKING, Literal, Never

from pydantic import BaseModel, ConfigDict, Field, model_validator

from owlbear_delivery.delivery_runtime import (
    DeliveryIntegrationAttention,
    DeliveryIntegrationAttentionCode,
    DeliveryIntegrationCandidate,
    DeliveryIntegrationRepair,
    DeliveryIntegrationRepairAuthorityAttention,
)
from owlbear_delivery.git_executable import resolve_git_executable
from owlbear_delivery.identities import ChangeId
from owlbear_delivery.runtime_transaction import (
    ReplacementTransactionParticipant,
    RuntimeTransaction,
    TransactionConflictError,
    TransactionParticipant,
)
from owlbear_delivery.storage_io import locked_roots

if TYPE_CHECKING:
    from collections.abc import Iterator
    from contextlib import AbstractContextManager

_TREE_ENTRY_PARTS = 3
_OCC_RETRY_LIMIT = 8
_PUBLICATION_LEASE_MAX_SECONDS = 600
_PUBLICATION_OPERATION_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")


class _WorkspaceModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class WriterIdentity(_WorkspaceModel):
    """Actor identity supplied when portfolio dispatch grants one writer."""

    attempt_id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)
    actor_id: str = Field(min_length=1)
    process_id: str = Field(min_length=1)
    claimed_at: str = Field(min_length=1)


class ChangeWriter(WriterIdentity):
    """One active writer bound to a target transformation."""

    job_id: int = Field(gt=0)
    kind: Literal["plan", "build", "repair"]


class PublicationLease(_WorkspaceModel):
    """Expiring custody for one exact Change publication attempt."""

    operation_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
    owner_id: str = Field(min_length=1)
    expires_at: str = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_expiry(self) -> PublicationLease:
        _publication_timestamp(self.expires_at)
        return self


class PublicationLock:
    """Active proof that one coordinator holds one Change publication lock."""

    __slots__ = ("_active", "_coordinator", "change_id")

    def __init__(self, coordinator: PortfolioCoordinator, change_id: str) -> None:
        self._coordinator = coordinator
        self.change_id = change_id
        self._active = True

    def close(self) -> None:
        """Invalidate this guard after its descriptor lock is released."""
        self._active = False

    def owns(self, coordinator: PortfolioCoordinator, change_id: str) -> bool:
        """Return whether this guard actively owns the named coordinator lock."""
        return self._active and self._coordinator is coordinator and self.change_id == change_id


class ChangeCoordination(_WorkspaceModel):
    """One OCC-guarded writable workspace record per change."""

    schema_version: Literal[1] = 1
    change_id: ChangeId
    branch: str = Field(min_length=1)
    worktree_path: Path
    integration_target: str = Field(min_length=1)
    target_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    last_reviewed_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    writer: ChangeWriter | None = None
    publication_lease: PublicationLease | None = None

    @model_validator(mode="before")
    @classmethod
    def _discard_retired_publication_reservation(cls, value: object) -> object:
        if not isinstance(value, dict) or "publication_operation_id" not in value:
            return value
        migrated: dict[object, object] = dict(value)
        migrated.pop("publication_operation_id", None)
        migrated.pop("publication_expires_at", None)
        return migrated

    @property
    def publication_expiry(self) -> datetime | None:
        """Return the normalized lease expiry when publication owns this Change."""
        if self.publication_lease is None:
            return None
        return _publication_timestamp(self.publication_lease.expires_at)


class WorkspaceRecoverySnapshot(_WorkspaceModel):
    """Read-only Git and custody state used to decide exact-claim recovery."""

    change_id: ChangeId
    worktree_path: Path
    branch: str = Field(min_length=1)
    branch_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    worktree_head: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    worktree_branch: str | None = None
    last_reviewed_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    preserved_commit: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    clean: bool
    reviewed_ancestor: bool
    preserved_reviewed_ancestor: bool
    writer: ChangeWriter | None = None


class CapacityLedger(_WorkspaceModel):
    """Global writer capacity without serializing independent changes."""

    schema_version: Literal[1] = 1
    capacity: int = Field(gt=0)
    change_ids: tuple[ChangeId, ...] = ()

    @model_validator(mode="after")
    def _validate_holders(self) -> CapacityLedger:
        if self.change_ids != tuple(sorted(set(self.change_ids))):
            msg = "capacity holders must be unique and sorted"
            raise ValueError(msg)
        if len(self.change_ids) > self.capacity:
            msg = "capacity holders exceed the global limit"
            raise ValueError(msg)
        return self


class IntegrationFinding(_WorkspaceModel):
    """Immutable evidence that integration requires solution planning."""

    finding_id: str = Field(min_length=1)
    change_id: ChangeId
    change_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    target_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    integration_target: str = Field(min_length=1)
    detail: str = Field(min_length=1)


class IntegrationResult(_WorkspaceModel):
    """Contain either one reviewed merge commit or one integration finding."""

    merge_commit: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    finding: IntegrationFinding | None = None

    @model_validator(mode="after")
    def _require_one_result(self) -> IntegrationResult:
        if (self.merge_commit is None) == (self.finding is None):
            msg = "integration requires either a merge commit or a finding"
            raise ValueError(msg)
        return self


class IntegrationRepairCandidate(_WorkspaceModel):
    """Exact claim-bound commit and merge proof for one Integration repair."""

    change_id: ChangeId
    attention_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    attempt_id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)
    source_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    target_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    candidate_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    merged_tree: str = Field(pattern=r"^[0-9a-f]{40}$")
    changed_paths: tuple[str, ...] = Field(min_length=1)


class AtomicIntegrationResult(_WorkspaceModel):
    """One committed candidate or typed previsibility Integration failure."""

    target_commit: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    code: DeliveryIntegrationAttentionCode | None = None
    diagnostics: tuple[str, ...] = ()
    replayed: bool = False

    @model_validator(mode="after")
    def _require_one_result(self) -> AtomicIntegrationResult:
        if (self.target_commit is None) == (self.code is None):
            message = "atomic Integration requires a commit or typed failure"
            raise ValueError(message)
        if self.code is not None and not self.diagnostics:
            message = "atomic Integration failure requires diagnostics"
            raise ValueError(message)
        return self


class AtomicIntegrationPreparation(_WorkspaceModel):
    """Detached candidate proof result awaiting package-guarded target CAS."""

    change_id: ChangeId
    candidate_commit: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    candidate_ref: str | None = None
    change_head: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    integration_target: str | None = None
    target_head: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    result: AtomicIntegrationResult | None = None

    @model_validator(mode="after")
    def _validate_preparation(self) -> AtomicIntegrationPreparation:
        candidate_parts = (
            self.candidate_commit,
            self.candidate_ref,
            self.change_head,
            self.integration_target,
            self.target_head,
        )
        prepared = all(part is not None for part in candidate_parts)
        if prepared == (self.result is not None):
            message = "Integration preparation requires a candidate or terminal result"
            raise ValueError(message)
        return self


class ExternalCompletionProposal(_WorkspaceModel):
    """Detached completion-only commit for an externally integrated change."""

    change_id: ChangeId
    proposal_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    proposal_ref: str = Field(min_length=1)
    target_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    completion_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    completion_path: str = Field(min_length=1)


class IntegrationContext(_WorkspaceModel):
    """Exact source and target identities used to capture an Integration candidate."""

    change_id: ChangeId
    change_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    reviewed_change_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    integration_target: str = Field(min_length=1)
    target_head: str = Field(pattern=r"^[0-9a-f]{40}$")


class FinalizationTargetProvenance(StrEnum):
    """Source class for the target identity used by Change finalization."""

    CACHED_REMOTE_TRACKING = "cached-remote-tracking"


class FinalizationTargetContext(_WorkspaceModel):
    """Remote-tracking target identity used only by Change finalization."""

    remote: str = Field(min_length=1)
    target_branch: str = Field(min_length=1)
    target_ref: str = Field(min_length=1)
    target_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    target_provenance: FinalizationTargetProvenance
    target_observed_at: datetime

    @model_validator(mode="after")
    def _validate_observation_time(self) -> FinalizationTargetContext:
        if self.target_observed_at.tzinfo is None:
            message = "finalization target observation time must include a timezone"
            raise ValueError(message)
        return self


class CoordinationConflictError(RuntimeError):
    """A per-change writer or global capacity slot is unavailable."""

    code = "ERR_TARGET_COORDINATION_CONFLICT"


class PortfolioCoordinator:
    """Atomically coordinate independent per-change writers and global capacity."""

    def __init__(self, state_root: Path, capacity: int) -> None:
        self._state_root = state_root
        self._coordination_root = state_root / "claims" / "changes"
        self._ledger_path = state_root / "capacity.json"
        self._capacity = capacity
        state_root.mkdir(parents=True, exist_ok=True)
        RuntimeTransaction.recover_all(state_root)
        self._initialize_ledger()

    def integration_lock(self) -> AbstractContextManager[None]:
        """Serialize shared integration-target mutations across portfolio writers."""
        lock_root = self._state_root / "claims" / "integration-lock"
        return locked_roots((lock_root,))

    def acquisition_lock(self) -> AbstractContextManager[None]:
        """Serialize portfolio selection and staged claim preparation."""
        lock_root = self._state_root / "claims" / "acquisition-lock"
        return locked_roots((lock_root,))

    @contextmanager
    def publication_lock(self, change_id: str, *, blocking: bool = True) -> Iterator[PublicationLock]:
        """Serialize bounded publication attempts for one Change across processes."""
        self._coordination_path(change_id)
        lock_root = self._state_root / "claims" / "publication-locks" / change_id
        with locked_roots((lock_root,), blocking=blocking):
            lock = PublicationLock(self, change_id)
            try:
                yield lock
            finally:
                lock.close()

    def writer_capacity_available(self) -> bool:
        """Return whether another Build writer can be reserved."""
        ledger = CapacityLedger.model_validate_json(self._ledger_path.read_bytes())
        return len(ledger.change_ids) < ledger.capacity

    def register(self, coordination: ChangeCoordination) -> ChangeCoordination:
        """Create one replayable per-change coordination record."""
        path = self._coordination_path(coordination.change_id)
        content = _model_content(coordination)
        if path.exists():
            existing = ChangeCoordination.model_validate_json(path.read_bytes())
            if existing != coordination:
                _coordination_conflict("change workspace is already registered differently")
            return existing
        self._commit(
            f"register-{coordination.change_id}",
            (TransactionParticipant(self._state_root, path.relative_to(self._state_root), content),),
        )
        return coordination

    def show(self, change_id: str) -> ChangeCoordination:
        """Return one current per-change coordination record."""
        path = self._coordination_path(change_id)
        try:
            return ChangeCoordination.model_validate_json(path.read_bytes())
        except FileNotFoundError as exc:
            msg = f"change workspace is not registered: {change_id}"
            raise CoordinationConflictError(msg) from exc

    def acquire(self, change_id: str, writer: ChangeWriter) -> ChangeCoordination:
        """Atomically bind one writer and one global capacity slot."""
        coordination = self.show(change_id)
        publication_expiry = coordination.publication_expiry
        if publication_expiry is not None and publication_expiry > datetime.now(UTC):
            _coordination_conflict("change already has an active writer")
        with self.publication_lock(change_id):
            return self._acquire(change_id, writer)

    def _acquire(self, change_id: str, writer: ChangeWriter) -> ChangeCoordination:
        coordination_path = self._coordination_path(change_id)
        coordination_bytes = coordination_path.read_bytes()
        coordination = ChangeCoordination.model_validate_json(coordination_bytes)
        ledger_bytes = self._ledger_path.read_bytes()
        ledger = CapacityLedger.model_validate_json(ledger_bytes)
        publication_expiry = coordination.publication_expiry
        publication_active = publication_expiry is not None and publication_expiry > datetime.now(UTC)
        if coordination.writer is not None or publication_active or change_id in ledger.change_ids:
            _coordination_conflict("change already has an active writer")
        if len(ledger.change_ids) >= ledger.capacity:
            _coordination_conflict("global writer capacity is exhausted")
        claimed = coordination.model_copy(
            update={
                "writer": writer,
                "publication_lease": None,
            }
        )
        occupied = ledger.model_copy(update={"change_ids": tuple(sorted((*ledger.change_ids, change_id)))})
        participants = (
            _replacement(self._state_root, coordination_path, coordination_bytes, claimed),
            _replacement(self._state_root, self._ledger_path, ledger_bytes, occupied),
        )
        try:
            self._commit(f"acquire-{change_id}-{writer.claim_id}", participants)
        except TransactionConflictError as exc:
            msg = "writer coordination changed concurrently"
            raise CoordinationConflictError(msg) from exc
        return claimed

    def release(self, change_id: str, claim_id: str) -> ChangeCoordination:
        """Release one exact writer and its capacity slot."""
        for _attempt in range(_OCC_RETRY_LIMIT):
            coordination_path = self._coordination_path(change_id)
            coordination_bytes = coordination_path.read_bytes()
            coordination = ChangeCoordination.model_validate_json(coordination_bytes)
            ledger_bytes = self._ledger_path.read_bytes()
            ledger = CapacityLedger.model_validate_json(ledger_bytes)
            if coordination.writer is None and change_id not in ledger.change_ids:
                return coordination
            if coordination.writer is None or coordination.writer.claim_id != claim_id:
                _coordination_conflict("writer claim does not own the change workspace")
            released = coordination.model_copy(update={"writer": None})
            available = ledger.model_copy(
                update={"change_ids": tuple(item for item in ledger.change_ids if item != change_id)}
            )
            participants = (
                _replacement(self._state_root, coordination_path, coordination_bytes, released),
                _replacement(self._state_root, self._ledger_path, ledger_bytes, available),
            )
            try:
                self._commit(f"release-{change_id}-{claim_id}", participants)
            except TransactionConflictError:
                continue
            return released
        return _coordination_conflict("writer coordination remained concurrent")

    def update(self, coordination: ChangeCoordination) -> ChangeCoordination:
        """OCC-replace one registered per-change record without touching capacity."""
        existing = self.show(coordination.change_id)
        if existing.publication_lease is not None and existing != coordination:
            _coordination_conflict("workspace update cannot change a reserved publication boundary")
        with self.publication_lock(coordination.change_id):
            return self._update(coordination)

    def _update(self, coordination: ChangeCoordination) -> ChangeCoordination:
        path = self._coordination_path(coordination.change_id)
        previous = path.read_bytes()
        existing = ChangeCoordination.model_validate_json(previous)
        if existing.writer != coordination.writer or existing.publication_lease != coordination.publication_lease:
            _coordination_conflict("workspace update cannot change ownership")
        if existing.publication_lease is not None and existing != coordination:
            _coordination_conflict("workspace update cannot change a reserved publication boundary")
        participant = _replacement(self._state_root, path, previous, coordination)
        try:
            self._commit(f"update-{coordination.change_id}", (participant,))
        except TransactionConflictError as exc:
            msg = "change workspace changed concurrently"
            raise CoordinationConflictError(msg) from exc
        return coordination

    def reserve_publication(
        self,
        change_id: str,
        lease: PublicationLease,
        lock: PublicationLock,
        *,
        now: str,
    ) -> ChangeCoordination:
        """Reserve one idle Change for an exact replayable publication operation."""
        self._require_publication_lock(lock, change_id)
        now_value = self._publication_timestamp(now)
        expires_value = self._publication_timestamp(lease.expires_at)
        if expires_value <= now_value:
            msg = "publication reservation expiry must be in the future"
            raise ValueError(msg)
        if (expires_value - now_value).total_seconds() > _PUBLICATION_LEASE_MAX_SECONDS:
            msg = "publication reservation exceeds the maximum duration"
            raise ValueError(msg)
        path = self._coordination_path(change_id)
        previous = path.read_bytes()
        coordination = ChangeCoordination.model_validate_json(previous)
        existing_lease = coordination.publication_lease
        existing_expiry = coordination.publication_expiry
        same_owner = existing_lease is not None and existing_lease.owner_id == lease.owner_id
        expired = existing_expiry is not None and existing_expiry <= now_value
        if coordination.writer is not None or (existing_lease is not None and not same_owner and not expired):
            _coordination_conflict("change already has active ownership")
        reserved = coordination.model_copy(update={"publication_lease": lease})
        operation_digest = hashlib.sha256(lease.operation_id.encode()).hexdigest()
        try:
            self._commit(
                f"reserve-publication-{change_id}-{operation_digest}",
                (_replacement(self._state_root, path, previous, reserved),),
            )
        except TransactionConflictError as exc:
            msg = "change ownership changed during publication reservation"
            raise CoordinationConflictError(msg) from exc
        return reserved

    def release_publication(
        self,
        change_id: str,
        operation_id: str,
        owner_id: str,
        lock: PublicationLock,
    ) -> ChangeCoordination:
        """Release one exact publication reservation without changing reviewed state."""
        self._require_publication_lock(lock, change_id)
        self._validate_publication_operation_id(operation_id)
        if not owner_id:
            msg = "publication owner identity is invalid"
            raise ValueError(msg)
        for _attempt in range(_OCC_RETRY_LIMIT):
            path = self._coordination_path(change_id)
            previous = path.read_bytes()
            coordination = ChangeCoordination.model_validate_json(previous)
            lease = coordination.publication_lease
            if lease is None or lease.operation_id != operation_id or lease.owner_id != owner_id:
                _coordination_conflict("publication operation does not own the change workspace")
            released = coordination.model_copy(update={"publication_lease": None})
            operation_digest = hashlib.sha256(operation_id.encode()).hexdigest()
            try:
                self._commit(
                    f"release-publication-{change_id}-{operation_digest}",
                    (_replacement(self._state_root, path, previous, released),),
                )
            except TransactionConflictError:
                continue
            return released
        return _coordination_conflict("publication ownership remained concurrent")

    @staticmethod
    def _validate_publication_operation_id(operation_id: str) -> None:
        if _PUBLICATION_OPERATION_PATTERN.fullmatch(operation_id) is None:
            msg = "publication operation identity is invalid"
            raise ValueError(msg)

    def _require_publication_lock(self, lock: PublicationLock, change_id: str) -> None:
        if not lock.owns(self, change_id):
            msg = "active publication lock does not own the Change"
            raise ValueError(msg)

    @staticmethod
    def _publication_timestamp(value: str) -> datetime:
        return _publication_timestamp(value)

    def publish_finding(self, finding: IntegrationFinding) -> IntegrationFinding:
        """Publish one immutable integration finding inside target evidence."""
        relative = Path("claims/integration-findings") / f"{finding.finding_id}.json"
        self._commit(
            f"finding-{finding.finding_id}",
            (TransactionParticipant(self._state_root, relative, _model_content(finding)),),
        )
        return finding

    def admit_integration_repair(
        self,
        repair: DeliveryIntegrationRepair | DeliveryIntegrationRepairAuthorityAttention,
        participants: tuple[ReplacementTransactionParticipant, ...],
    ) -> None:
        """Atomically advance reviewed workspace and runtime attention boundaries."""
        transaction_id = hashlib.sha256(_model_content(repair)).hexdigest()
        self._commit(f"integration-repair-{transaction_id}", participants)

    def integration_repair_replacements(
        self,
        previous: ChangeCoordination,
        replacement: ChangeCoordination,
        claim_id: str,
    ) -> tuple[ReplacementTransactionParticipant, ReplacementTransactionParticipant]:
        """Prepare OCC replacements for reviewed-boundary advance and writer release."""
        path = self._coordination_path(previous.change_id)
        previous_bytes = path.read_bytes()
        if ChangeCoordination.model_validate_json(previous_bytes) != previous:
            _coordination_conflict("workspace changed during Integration repair validation")
        ledger_bytes = self._ledger_path.read_bytes()
        ledger = CapacityLedger.model_validate_json(ledger_bytes)
        if previous.writer is None or previous.writer.claim_id != claim_id:
            _coordination_conflict("repair claim does not own the change workspace")
        if previous.change_id not in ledger.change_ids:
            _coordination_conflict("repair writer does not hold global capacity")
        released = replacement.model_copy(update={"writer": None})
        available = ledger.model_copy(
            update={"change_ids": tuple(item for item in ledger.change_ids if item != previous.change_id)}
        )
        return (
            _replacement(self._state_root, path, previous_bytes, released),
            _replacement(self._state_root, self._ledger_path, ledger_bytes, available),
        )

    def _initialize_ledger(self) -> None:
        initial = CapacityLedger(capacity=self._capacity)
        if self._ledger_path.exists():
            existing_bytes = self._ledger_path.read_bytes()
            existing = CapacityLedger.model_validate_json(existing_bytes)
            if existing.capacity != self._capacity:
                if len(existing.change_ids) > self._capacity:
                    _coordination_conflict("active writers exceed configured writer capacity")
                updated = existing.model_copy(update={"capacity": self._capacity})
                self._commit(
                    "reconfigure-capacity",
                    (_replacement(self._state_root, self._ledger_path, existing_bytes, updated),),
                )
            return
        self._commit(
            "initialize-capacity",
            (
                TransactionParticipant(
                    self._state_root,
                    self._ledger_path.relative_to(self._state_root),
                    _model_content(initial),
                ),
            ),
        )

    def _coordination_path(self, change_id: str) -> Path:
        if not change_id or any(character not in "abcdefghijklmnopqrstuvwxyz0123456789-" for character in change_id):
            msg = "change identity is not a safe coordination path"
            raise ValueError(msg)
        return self._coordination_root / f"{change_id}.json"

    def _commit(
        self,
        transaction_id: str,
        participants: tuple[TransactionParticipant | ReplacementTransactionParticipant, ...],
    ) -> None:
        RuntimeTransaction(self._state_root, f"portfolio-{transaction_id}", participants).commit()


class ChangeWorkspaceManager:
    """Own one warm writable Git worktree and non-rewriting integration per change."""

    def __init__(
        self,
        repository: Path,
        worktree_root: Path,
        coordinator: PortfolioCoordinator,
        integration_target: str,
        remote: str = "origin",
    ) -> None:
        self._repository = repository.resolve()
        self._worktree_root = worktree_root.resolve()
        self._coordinator = coordinator
        self._integration_target = integration_target
        self._remote = remote
        self._git("check-ref-format", f"refs/heads/{integration_target}")

    @property
    def repository(self) -> Path:
        """Return the engine-owned repository used for managed Change reads."""
        return self._repository

    def create(
        self,
        change_id: str,
        *,
        recovery_reviewed_head: str | None = None,
    ) -> ChangeCoordination:
        """Create or replay one warm branch and worktree from the configured target."""
        try:
            existing = self._coordinator.show(change_id)
        except CoordinationConflictError:
            existing = None
        if existing is not None:
            if existing.integration_target != self._integration_target:
                _workspace_failure("registered workspace uses another integration target")
            if recovery_reviewed_head is not None and recovery_reviewed_head != existing.last_reviewed_commit:
                _coordination_conflict("recovery reviewed head differs from registered workspace authority")
            self._require_worktree(
                existing.worktree_path,
                existing.branch,
                self._resolve(existing.branch),
            )
            return existing
        branch = f"owlbear/change/{change_id}"
        self._git("check-ref-format", f"refs/heads/{branch}")
        worktree = self._worktree_root / change_id
        target_head = self._resolve(self._integration_target)
        branch_head = self._resolve(branch, missing_ok=True)
        if branch_head is None:
            if recovery_reviewed_head is not None:
                _coordination_conflict("recovery reviewed head requires an existing Change branch")
            self._git("branch", branch, target_head)
            branch_head = target_head
            last_reviewed_commit = target_head
        else:
            if recovery_reviewed_head is None:
                _coordination_conflict("existing Change branch requires an exact recovery reviewed head")
            self._require_ancestor(recovery_reviewed_head, branch_head)
            last_reviewed_commit = recovery_reviewed_head
        self._register_worktree(worktree, branch)
        self._require_worktree(worktree, branch, branch_head)
        coordination = ChangeCoordination(
            change_id=change_id,
            branch=branch,
            worktree_path=worktree,
            integration_target=self._integration_target,
            target_head=target_head,
            last_reviewed_commit=last_reviewed_commit,
        )
        return self._coordinator.register(coordination)

    def validate_recovery(self, change_id: str, recovery_reviewed_head: str | None) -> None:
        """Require exact reviewed authority when coordination is missing for a surviving branch."""
        try:
            existing = self._coordinator.show(change_id)
        except CoordinationConflictError:
            existing = None
        if existing is not None:
            if recovery_reviewed_head is not None and recovery_reviewed_head != existing.last_reviewed_commit:
                _coordination_conflict("recovery reviewed head differs from registered workspace authority")
            return
        branch = f"owlbear/change/{change_id}"
        branch_head = self._resolve(branch, missing_ok=True)
        if branch_head is None:
            if recovery_reviewed_head is not None:
                _coordination_conflict("recovery reviewed head requires an existing Change branch")
            return
        if recovery_reviewed_head is None:
            _coordination_conflict("existing Change branch requires an exact recovery reviewed head")
        self._require_ancestor(recovery_reviewed_head, branch_head)

    def record_reviewed(self, change_id: str, commit: str) -> ChangeCoordination:
        """Advance the recorded reviewed boundary to an exact branch ancestor."""
        coordination = self._coordinator.show(change_id)
        branch_head = self._resolve(coordination.branch)
        self._require_ancestor(commit, branch_head)
        updated = coordination.model_copy(update={"last_reviewed_commit": commit})
        return self._coordinator.update(updated)

    def _register_worktree(self, worktree: Path, branch: str) -> None:
        if worktree.exists():
            return
        worktree.parent.mkdir(parents=True, exist_ok=True)
        self._git("worktree", "add", str(worktree), branch)

    def show(self, change_id: str) -> ChangeCoordination:
        """Return current workspace coordination for transition validation."""
        return self._coordinator.show(change_id)

    def refresh_integration_target(self, change_id: str) -> ChangeCoordination:
        """Persist the current target head at an operational Git boundary."""
        coordination = self._coordinator.show(change_id)
        target_head = self._resolve(coordination.integration_target)
        if target_head == coordination.target_head:
            return coordination
        return self._coordinator.update(coordination.model_copy(update={"target_head": target_head}))

    def integration_context(self, change_id: str) -> IntegrationContext:
        """Return exact source and target heads without mutating either reference."""
        coordination = self._coordinator.show(change_id)
        return IntegrationContext(
            change_id=coordination.change_id,
            change_head=self._resolve(coordination.branch),
            reviewed_change_head=coordination.last_reviewed_commit,
            integration_target=coordination.integration_target,
            target_head=self._resolve(coordination.integration_target),
        )

    def finalization_target_context(self, change_id: str) -> FinalizationTargetContext:
        """Return the configured remote-tracking target identity without fetching or mutation."""
        coordination = self._coordinator.show(change_id)
        target_ref = f"refs/remotes/{self._remote}/{coordination.integration_target}"
        target_head = self._resolve(target_ref)
        local_target_head = self._resolve(coordination.integration_target)
        if local_target_head != target_head:
            _coordination_conflict(
                "finalization target authority diverges between local target and cached remote-tracking ref"
            )
        return FinalizationTargetContext(
            remote=self._remote,
            target_branch=coordination.integration_target,
            target_ref=target_ref,
            target_head=target_head,
            target_provenance=FinalizationTargetProvenance.CACHED_REMOTE_TRACKING,
            target_observed_at=datetime.now(UTC),
        )

    def integration_repair_replacement(
        self,
        repair: DeliveryIntegrationRepair,
        claim_id: str,
    ) -> tuple[ReplacementTransactionParticipant, ReplacementTransactionParticipant]:
        """Validate one additive conflict repair and prepare its reviewed-boundary update."""
        coordination = self._coordinator.show(repair.change_id)
        self._require_integration_repair_identities(coordination, repair, claim_id)
        self._require_integration_repair_worktree(coordination, repair)
        repaired_tree = self._require_additive_conflict_repair(repair)
        self._require_unchanged_completed_history(repair.prior_target_head, repaired_tree)
        updated = coordination.model_copy(update={"last_reviewed_commit": repair.reviewed_repair_commit})
        return self._coordinator.integration_repair_replacements(coordination, updated, claim_id)

    def create_integration_repair_candidate(
        self,
        attention: DeliveryIntegrationAttention,
        writer: ChangeWriter,
    ) -> IntegrationRepairCandidate:
        """Commit and prove one conflict-path repair under exact writer custody."""
        coordination = self._coordinator.show(attention.change_id)
        if coordination.writer != writer or writer.kind != "repair":
            _coordination_conflict("Integration repair candidate requires exact repair writer custody")
        if (
            attention.code != DeliveryIntegrationAttentionCode.MERGE_CONFLICT
            or coordination.integration_target != attention.integration_target
            or coordination.target_head != attention.target_head
            or coordination.last_reviewed_commit != attention.change_head
            or self._resolve(coordination.integration_target) != attention.target_head
        ):
            _workspace_failure("Integration repair candidate does not match current attention")

        branch_head = self._resolve(coordination.branch)
        if branch_head == attention.change_head:
            self._require_worktree(coordination.worktree_path, coordination.branch, branch_head)
            changed_paths = self._worktree_changed_paths(coordination.worktree_path)
            conflict_paths = self._integration_conflict_paths(attention.target_head, attention.change_head)
            if changed_paths != conflict_paths:
                _workspace_failure(
                    "Integration repair candidate may change only original conflict paths; all must be resolved"
                )
            path_arguments = tuple(sorted(os.fsdecode(path) for path in changed_paths))
            self._git("add", "--all", "--", *path_arguments, cwd=coordination.worktree_path)
            resolution_tree = self._git("write-tree", cwd=coordination.worktree_path)
            tree = self._resolved_integration_repair_tree(
                attention.target_head,
                attention.change_head,
                resolution_tree,
                conflict_paths,
            )
            candidate_commit = self._git(
                "commit-tree",
                tree,
                "-p",
                attention.change_head,
                "-p",
                attention.target_head,
                "-m",
                f"Repair Integration for {attention.change_id}",
                cwd=coordination.worktree_path,
            )
            self._git(
                "update-ref",
                f"refs/heads/{coordination.branch}",
                candidate_commit,
                attention.change_head,
            )
            self._git("reset", "--hard", candidate_commit, cwd=coordination.worktree_path)
        else:
            candidate_commit = branch_head

        merged_tree, changed_paths = self._require_integration_repair_candidate(
            coordination,
            attention,
            candidate_commit,
        )
        return IntegrationRepairCandidate(
            change_id=coordination.change_id,
            attention_id=attention.attention_id,
            attempt_id=writer.attempt_id,
            claim_id=writer.claim_id,
            source_head=attention.change_head,
            target_head=attention.target_head,
            candidate_commit=candidate_commit,
            merged_tree=merged_tree,
            changed_paths=tuple(sorted(os.fsdecode(path) for path in changed_paths)),
        )

    def integration_repair_authority_replacements(
        self,
        request: DeliveryIntegrationRepairAuthorityAttention,
        claim_id: str,
    ) -> tuple[ReplacementTransactionParticipant, ReplacementTransactionParticipant]:
        """Require a restored reviewed source and prepare exact repair-writer release."""
        coordination = self._coordinator.show(request.change_id)
        if (
            coordination.writer is None
            or coordination.writer.claim_id != claim_id
            or coordination.writer.kind != "repair"
        ):
            _coordination_conflict("repair authority attention requires exact repair writer custody")
        self.reviewed_source_head(request.change_id)
        return self._coordinator.integration_repair_replacements(coordination, coordination, claim_id)

    def _require_integration_repair_identities(
        self,
        coordination: ChangeCoordination,
        repair: DeliveryIntegrationRepair,
        claim_id: str,
    ) -> None:
        if (
            coordination.writer is None
            or coordination.writer.claim_id != claim_id
            or coordination.writer.kind != "repair"
        ):
            _coordination_conflict("Integration repair requires exact repair writer custody")
        if (
            coordination.change_id != repair.change_id
            or coordination.integration_target != repair.integration_target
            or coordination.integration_target != self._integration_target
            or coordination.last_reviewed_commit != repair.prior_change_head
        ):
            _workspace_failure("Integration repair does not match workspace identities")
        if self._resolve(coordination.integration_target) != repair.prior_target_head:
            _workspace_failure("Integration repair target head is stale")
        if self._resolve(coordination.branch) != repair.reviewed_repair_commit:
            _workspace_failure("reviewed repair commit is not the current change branch head")

    def _require_integration_repair_worktree(
        self,
        coordination: ChangeCoordination,
        repair: DeliveryIntegrationRepair,
    ) -> None:
        self._require_worktree(
            coordination.worktree_path,
            coordination.branch,
            repair.reviewed_repair_commit,
        )
        if self._git("-C", str(coordination.worktree_path), "status", "--porcelain"):
            _workspace_failure("Integration repair requires a clean change worktree")
        parents = self._git(
            "rev-list",
            "--parents",
            "-n",
            "1",
            repair.reviewed_repair_commit,
        ).split()
        if parents != [repair.reviewed_repair_commit, repair.prior_change_head, repair.prior_target_head]:
            _workspace_failure("Integration repair must have the exact source and target parents")

    def _require_additive_conflict_repair(self, repair: DeliveryIntegrationRepair) -> str:
        conflict_paths = self._integration_conflict_paths(
            repair.prior_target_head,
            repair.prior_change_head,
        )
        completed_root = b".owlbear/completed"
        if any(path == completed_root or path.startswith(completed_root + b"/") for path in conflict_paths):
            _workspace_failure("Integration repair cannot mutate completed history")
        candidate_tree = self._git("rev-parse", f"{repair.reviewed_repair_commit}^{{tree}}")
        repaired_tree = self._resolved_integration_repair_tree(
            repair.prior_target_head,
            repair.prior_change_head,
            candidate_tree,
            conflict_paths,
        )
        if repaired_tree != candidate_tree:
            _workspace_failure("Integration repair changes paths outside the original conflict")
        return repaired_tree

    def _require_integration_repair_candidate(
        self,
        coordination: ChangeCoordination,
        attention: DeliveryIntegrationAttention,
        candidate_commit: str,
    ) -> tuple[str, set[bytes]]:
        self._require_worktree(coordination.worktree_path, coordination.branch, candidate_commit)
        if self._git("status", "--porcelain", cwd=coordination.worktree_path):
            _workspace_failure("Integration repair candidate requires a clean change worktree")
        parents = self._git("rev-list", "--parents", "-n", "1", candidate_commit).split()
        if parents != [candidate_commit, attention.change_head, attention.target_head]:
            _workspace_failure("Integration repair candidate must have the exact source and target parents")
        conflict_paths = self._integration_conflict_paths(attention.target_head, attention.change_head)
        candidate_tree = self._git("rev-parse", f"{candidate_commit}^{{tree}}")
        repaired_tree = self._resolved_integration_repair_tree(
            attention.target_head,
            attention.change_head,
            candidate_tree,
            conflict_paths,
        )
        if repaired_tree != candidate_tree:
            _workspace_failure("Integration repair candidate changes paths outside the original conflict")
        self._require_unchanged_completed_history(attention.target_head, candidate_tree)
        return candidate_tree, conflict_paths

    def _worktree_changed_paths(self, worktree: Path) -> set[bytes]:
        tracked = self._run_git("diff", "--name-only", "-z", "HEAD", cwd=worktree).stdout
        untracked = self._run_git("ls-files", "--others", "--exclude-standard", "-z", cwd=worktree).stdout
        return {path for path in (*tracked.split(b"\0"), *untracked.split(b"\0")) if path}

    def _require_unchanged_completed_history(self, target_head: str, repaired_tree: str) -> None:
        target_tree = self._git("rev-parse", f"{target_head}^{{tree}}")
        completed_path = (b".owlbear", b"completed")
        if self._tree_entries_at_path(repaired_tree, completed_path) != self._tree_entries_at_path(
            target_tree,
            completed_path,
        ):
            _workspace_failure("Integration repair merge mutates completed history")

    def reviewed_source_head(self, change_id: str) -> str:
        """Return one clean warm source head anchored at its reviewed boundary."""
        coordination = self._coordinator.show(change_id)
        branch_head = self._resolve(coordination.branch)
        if branch_head != coordination.last_reviewed_commit:
            _workspace_failure("change branch differs from its reviewed source boundary")
        self._require_worktree(coordination.worktree_path, coordination.branch, branch_head)
        if self._git("-C", str(coordination.worktree_path), "status", "--porcelain"):
            _workspace_failure("change source worktree is not clean")
        return branch_head

    def validate_finalization_head(
        self,
        change_id: str,
        exact_head: str,
        promoted_commits: tuple[str, ...],
    ) -> ChangeCoordination:
        """Require one unclaimed clean reviewed head containing every promoted Task commit."""
        coordination = self._coordinator.show(change_id)
        if coordination.writer is not None:
            _workspace_failure("Delivery finalization cannot overlap an active Change writer")
        if self.reviewed_source_head(change_id) != exact_head:
            _workspace_failure("Delivery finalization head differs from the reviewed Change head")
        for predecessor, successor in pairwise(promoted_commits):
            self._require_ancestor(predecessor, successor)
        for promoted_commit in promoted_commits:
            self._require_ancestor(promoted_commit, exact_head)
        return coordination

    def observed_change_head(self, change_id: str) -> str:
        """Read the current managed Change branch head without mutating any checkout."""
        coordination = self._coordinator.show(change_id)
        return self._resolve(coordination.branch)

    def recovery_snapshot(self, change_id: str, attempt_id: str) -> WorkspaceRecoverySnapshot:
        """Inspect exact recovery state without changing the branch, worktree, or custody."""
        coordination = self._coordinator.show(change_id)
        branch_head = self._resolve(coordination.branch)
        attempt_ref = f"refs/owlbear/attempts/{change_id}/{attempt_id}"
        self._git("check-ref-format", attempt_ref)
        preserved = self._resolve(attempt_ref, missing_ok=True)
        worktree_head = None
        worktree_branch = None
        clean = False
        if coordination.worktree_path.exists():
            worktree_head = self._resolve("HEAD", cwd=coordination.worktree_path)
            worktree_branch = self._git(
                "-C",
                str(coordination.worktree_path),
                "branch",
                "--show-current",
            )
            clean = not self._git("-C", str(coordination.worktree_path), "status", "--porcelain")
        return WorkspaceRecoverySnapshot(
            change_id=change_id,
            worktree_path=coordination.worktree_path,
            branch=coordination.branch,
            branch_head=branch_head,
            worktree_head=worktree_head,
            worktree_branch=worktree_branch,
            last_reviewed_commit=coordination.last_reviewed_commit,
            preserved_commit=preserved,
            clean=clean,
            reviewed_ancestor=self._is_ancestor(
                coordination.last_reviewed_commit,
                branch_head,
                cwd=self._repository,
            ),
            preserved_reviewed_ancestor=(
                preserved is None
                or self._is_ancestor(
                    coordination.last_reviewed_commit,
                    preserved,
                    cwd=self._repository,
                )
            ),
            writer=coordination.writer,
        )

    def validate_writer_head(self, change_id: str, claim_id: str, commit: str) -> ChangeCoordination:
        """Validate one writer-owned clean branch-head commit without mutation."""
        coordination = self._coordinator.show(change_id)
        if coordination.writer is None or coordination.writer.claim_id != claim_id:
            _coordination_conflict("writer claim does not own the change workspace")
        branch_head = self._resolve(coordination.branch)
        if branch_head != commit:
            _workspace_failure("candidate commit is not the current change branch head")
        self._require_ancestor(coordination.last_reviewed_commit, commit)
        self._require_worktree(coordination.worktree_path, coordination.branch, commit)
        if self._git("-C", str(coordination.worktree_path), "status", "--porcelain"):
            _workspace_failure("candidate commit requires a clean change worktree")
        return coordination

    def complete_reviewed(self, change_id: str, claim_id: str, commit: str) -> ChangeCoordination:
        """Replayably advance one completed boundary and release exact writer custody."""
        coordination = self._coordinator.show(change_id)
        if coordination.writer is None:
            if coordination.last_reviewed_commit == commit and self._resolve(coordination.branch) == commit:
                return coordination
            _coordination_conflict("completed writer state does not match the candidate commit")
        self.validate_writer_head(change_id, claim_id, commit)
        self.record_reviewed(change_id, commit)
        return self._coordinator.release(change_id, claim_id)

    def release_writer_at_head(self, change_id: str, claim_id: str, commit: str) -> ChangeCoordination:
        """Replayably release one writer while retaining its clean branch head."""
        coordination = self._coordinator.show(change_id)
        if coordination.writer is None:
            if self._resolve(coordination.branch) == commit:
                return coordination
            _coordination_conflict("released writer state does not match the resume commit")
        self.validate_writer_head(change_id, claim_id, commit)
        return self._coordinator.release(change_id, claim_id)

    def restart(self, change_id: str, attempt_id: str, rejected_head: str) -> ChangeCoordination:
        """Preserve a rejected head and restore the change to its reviewed boundary."""
        coordination = self._coordinator.show(change_id)
        branch_head = self._resolve(coordination.branch)
        worktree = coordination.worktree_path
        attempt_ref = f"refs/owlbear/attempts/{change_id}/{attempt_id}"
        self._git("check-ref-format", attempt_ref)
        preserved = self._resolve(attempt_ref, missing_ok=True)
        if preserved is not None and preserved != rejected_head:
            _workspace_failure("attempt history ref names another rejected head")
        if coordination.writer is None:
            return self._validate_released_restart(coordination, rejected_head, branch_head, preserved)
        self._prepare_active_restart(
            coordination,
            attempt_id,
            rejected_head,
        )
        self._register_worktree(worktree, coordination.branch)
        self._require_worktree(worktree, coordination.branch, coordination.last_reviewed_commit)
        return self._coordinator.release(change_id, coordination.writer.claim_id)

    def _validate_released_restart(
        self,
        coordination: ChangeCoordination,
        rejected_head: str,
        branch_head: str,
        preserved: str | None,
    ) -> ChangeCoordination:
        if preserved != rejected_head or branch_head != coordination.last_reviewed_commit:
            _coordination_conflict("released restart state does not match the rejected head")
        self._require_worktree(
            coordination.worktree_path,
            coordination.branch,
            coordination.last_reviewed_commit,
        )
        return coordination

    def _prepare_active_restart(
        self,
        coordination: ChangeCoordination,
        attempt_id: str,
        rejected_head: str,
    ) -> None:
        branch_head = self._resolve(coordination.branch)
        attempt_ref = f"refs/owlbear/attempts/{coordination.change_id}/{attempt_id}"
        preserved = self._resolve(attempt_ref, missing_ok=True)
        if coordination.writer is None or coordination.writer.attempt_id != attempt_id:
            _coordination_conflict("restart attempt does not own the change writer")
        if branch_head not in {rejected_head, coordination.last_reviewed_commit}:
            _workspace_failure("change branch is outside the recoverable restart states")
        if preserved is None:
            if branch_head != rejected_head:
                _workspace_failure("rejected head is not the current change branch")
            self._git("update-ref", attempt_ref, rejected_head, "0" * 40)
        if branch_head != rejected_head:
            return
        if coordination.worktree_path.exists():
            self._require_worktree(coordination.worktree_path, coordination.branch, rejected_head)
            if self._git("-C", str(coordination.worktree_path), "status", "--porcelain"):
                _workspace_failure("restart requires a clean committed change worktree")
            self._git("reset", "--hard", coordination.last_reviewed_commit, cwd=coordination.worktree_path)
            return
        self._git(
            "update-ref",
            f"refs/heads/{coordination.branch}",
            coordination.last_reviewed_commit,
            rejected_head,
        )

    def prepare_integration_candidate(
        self,
        candidate: DeliveryIntegrationCandidate,
    ) -> AtomicIntegrationPreparation:
        """Build and anchor detached Git objects without publishing the target."""
        preflight = self._preflight_integration(candidate)
        if isinstance(preflight, AtomicIntegrationResult):
            return AtomicIntegrationPreparation(change_id=candidate.change_id, result=preflight)
        coordination, change_head, target_head = preflight
        candidate_tree = self._integration_candidate_tree(candidate, change_head, target_head)
        if isinstance(candidate_tree, AtomicIntegrationResult):
            return AtomicIntegrationPreparation(change_id=candidate.change_id, result=candidate_tree)
        candidate_ref = self._integration_candidate_ref(candidate.change_id)
        candidate_commit = self._anchored_integration_commit(
            candidate,
            candidate_tree,
            target_head,
            change_head,
            candidate_ref,
        )
        return AtomicIntegrationPreparation(
            change_id=candidate.change_id,
            candidate_commit=candidate_commit,
            candidate_ref=candidate_ref,
            change_head=change_head,
            integration_target=coordination.integration_target,
            target_head=target_head,
        )

    def prepare_external_completion_proposal(
        self,
        candidate: DeliveryIntegrationCandidate,
    ) -> ExternalCompletionProposal | AtomicIntegrationResult:
        """Anchor a completion-only proposal without moving the Integration target."""
        preflight = self._preflight_external_completion(candidate)
        if isinstance(preflight, AtomicIntegrationResult):
            return preflight
        target_head = preflight
        try:
            target_tree = self._git("rev-parse", f"{target_head}^{{tree}}")
            proposal_tree = self._replace_tree_path(
                target_tree,
                tuple(candidate.completion_path.split("/")),
                candidate.package_tree,
            )
            self._require_unchanged_completed_siblings(proposal_tree, target_head, candidate.change_id)
        except ValueError as exc:
            return AtomicIntegrationResult(
                code=DeliveryIntegrationAttentionCode.COMPLETED_HISTORY_MUTATED,
                diagnostics=(str(exc),),
            )
        proposal_ref = f"refs/owlbear/external-completion-proposals/{candidate.change_id}"
        current = self._resolve(proposal_ref, missing_ok=True)
        if current is not None and self._external_completion_proposal_matches(
            current,
            candidate,
            proposal_tree,
            target_head,
        ):
            proposal_commit = current
        else:
            proposal_commit = self._write_external_completion_proposal(candidate, proposal_tree, target_head)
            self._git("update-ref", proposal_ref, proposal_commit, current or "0" * 40)
        return ExternalCompletionProposal(
            change_id=candidate.change_id,
            proposal_commit=proposal_commit,
            proposal_ref=proposal_ref,
            target_head=target_head,
            completion_id=candidate.completion_id,
            completion_path=candidate.completion_path,
        )

    def _preflight_external_completion(
        self,
        candidate: DeliveryIntegrationCandidate,
    ) -> str | AtomicIntegrationResult:
        coordination = self._coordinator.show(candidate.change_id)
        change_head = self._resolve(coordination.branch)
        target_head = self._resolve(coordination.integration_target)
        identity_diagnostics = self._integration_identity_diagnostics(coordination, candidate)
        if identity_diagnostics:
            result: str | AtomicIntegrationResult = AtomicIntegrationResult(
                code=DeliveryIntegrationAttentionCode.TARGET_IDENTITY_MISMATCH,
                diagnostics=identity_diagnostics,
            )
        elif candidate.target_head != target_head:
            result = AtomicIntegrationResult(
                code=DeliveryIntegrationAttentionCode.TARGET_CAS_LOST,
                diagnostics=("integration target changed after proposal capture",),
            )
        elif (replayed_commit := self._published_completion_commit(candidate)) is not None:
            result = AtomicIntegrationResult(target_commit=replayed_commit, replayed=True)
        elif change_head != coordination.last_reviewed_commit or change_head != candidate.reviewed_change_head:
            result = AtomicIntegrationResult(
                code=DeliveryIntegrationAttentionCode.REVIEWED_BOUNDARY_MISMATCH,
                diagnostics=("change branch head differs from its reviewed boundary",),
            )
        elif not self._is_ancestor(change_head, target_head, cwd=self._repository):
            result = AtomicIntegrationResult(
                code=DeliveryIntegrationAttentionCode.REVIEWED_BOUNDARY_MISMATCH,
                diagnostics=("integration target does not contain the reviewed change",),
            )
        else:
            self._require_worktree(coordination.worktree_path, coordination.branch, change_head)
            result = (
                AtomicIntegrationResult(
                    code=DeliveryIntegrationAttentionCode.REVIEWED_WORKTREE_DIRTY,
                    diagnostics=("change worktree is not clean at its reviewed boundary",),
                )
                if self._git("-C", str(coordination.worktree_path), "status", "--porcelain")
                else target_head
            )
        return result

    def validate_prepared_integration(
        self,
        preparation: AtomicIntegrationPreparation,
    ) -> AtomicIntegrationResult | None:
        """Revalidate one prepared candidate without publishing its target."""
        if preparation.result is not None:
            return preparation.result
        if (
            preparation.candidate_commit is None
            or preparation.candidate_ref is None
            or preparation.change_head is None
            or preparation.integration_target is None
            or preparation.target_head is None
        ):
            _workspace_failure("Integration preparation is incomplete")
        if self._resolve(preparation.candidate_ref, missing_ok=True) != preparation.candidate_commit:
            return AtomicIntegrationResult(
                code=DeliveryIntegrationAttentionCode.REVIEWED_BOUNDARY_MISMATCH,
                diagnostics=("anchored Integration candidate moved after verification",),
            )
        coordination = self._coordinator.show(preparation.change_id)
        if coordination.integration_target != preparation.integration_target:
            return AtomicIntegrationResult(
                code=DeliveryIntegrationAttentionCode.TARGET_IDENTITY_MISMATCH,
                diagnostics=("registered Integration target changed after candidate validation",),
            )
        if self._resolve(coordination.integration_target) != preparation.target_head:
            return AtomicIntegrationResult(
                code=DeliveryIntegrationAttentionCode.TARGET_CAS_LOST,
                diagnostics=("integration target changed after candidate validation",),
            )
        reviewed_diagnostics = self._reviewed_preparation_diagnostics(coordination, preparation.change_head)
        if not reviewed_diagnostics:
            return None
        code = (
            DeliveryIntegrationAttentionCode.REVIEWED_WORKTREE_DIRTY
            if reviewed_diagnostics == ("warm change worktree became dirty after candidate validation",)
            else DeliveryIntegrationAttentionCode.REVIEWED_BOUNDARY_MISMATCH
        )
        return AtomicIntegrationResult(code=code, diagnostics=reviewed_diagnostics)

    def discard_integration_candidate(self, preparation: AtomicIntegrationPreparation) -> None:
        """Delete one exact terminal candidate ref without touching another preparation."""
        if preparation.candidate_commit is None or preparation.candidate_ref is None:
            return
        current = self._resolve(preparation.candidate_ref, missing_ok=True)
        if current is None:
            return
        if current != preparation.candidate_commit:
            return
        self._git("update-ref", "-d", preparation.candidate_ref, preparation.candidate_commit)

    def discard_external_completion_proposal(
        self,
        candidate: DeliveryIntegrationCandidate,
        target_commit: str,
    ) -> None:
        """Delete the exact merged completion proposal ref without moving its target."""
        proposal_ref = f"refs/owlbear/external-completion-proposals/{candidate.change_id}"
        proposal_commit = self._resolve(proposal_ref, missing_ok=True)
        if proposal_commit is None:
            return
        if not self._is_ancestor(proposal_commit, target_commit, cwd=self._repository):
            return
        if self._completion_identity(proposal_commit, candidate.completion_path) != candidate.completion_id:
            return
        self._git("update-ref", "-d", proposal_ref, proposal_commit)

    def discard_stale_integration_candidate(self, change_id: str) -> None:
        """Delete any candidate ref owned by a terminally replayed change."""
        reference = self._integration_candidate_ref(change_id)
        current = self._resolve(reference, missing_ok=True)
        if current is not None:
            self._git("update-ref", "-d", reference, current)

    def _reviewed_preparation_diagnostics(
        self,
        coordination: ChangeCoordination,
        expected_head: str,
    ) -> tuple[str, ...]:
        if self._resolve(coordination.branch) != expected_head or coordination.last_reviewed_commit != expected_head:
            return ("change branch moved after candidate validation",)
        worktree = coordination.worktree_path
        if not worktree.exists():
            return ("warm change worktree disappeared after candidate validation",)
        if self._resolve("HEAD", cwd=worktree) != expected_head:
            return ("warm change worktree head moved after candidate validation",)
        if self._git("-C", str(worktree), "branch", "--show-current") != coordination.branch:
            return ("warm change worktree changed branches after candidate validation",)
        if self._git("-C", str(worktree), "status", "--porcelain"):
            return ("warm change worktree became dirty after candidate validation",)
        return ()

    def _preflight_integration(
        self,
        candidate: DeliveryIntegrationCandidate,
    ) -> AtomicIntegrationResult | tuple[ChangeCoordination, str, str]:
        coordination = self._coordinator.show(candidate.change_id)
        change_head = self._resolve(coordination.branch)
        target_head = self._resolve(coordination.integration_target)
        identity_diagnostics = self._integration_identity_diagnostics(
            coordination,
            candidate,
        )
        if identity_diagnostics:
            return AtomicIntegrationResult(
                code=DeliveryIntegrationAttentionCode.TARGET_IDENTITY_MISMATCH,
                diagnostics=identity_diagnostics,
            )
        if candidate.target_head != target_head:
            return AtomicIntegrationResult(
                code=DeliveryIntegrationAttentionCode.TARGET_CAS_LOST,
                diagnostics=("integration target changed after candidate capture",),
            )
        replayed_commit = self._published_completion_commit(candidate)
        if replayed_commit is not None:
            return AtomicIntegrationResult(target_commit=replayed_commit, replayed=True)
        if change_head != coordination.last_reviewed_commit or change_head != candidate.reviewed_change_head:
            return AtomicIntegrationResult(
                code=DeliveryIntegrationAttentionCode.REVIEWED_BOUNDARY_MISMATCH,
                diagnostics=("change branch head differs from its reviewed boundary",),
            )
        self._require_worktree(coordination.worktree_path, coordination.branch, change_head)
        if self._git("-C", str(coordination.worktree_path), "status", "--porcelain"):
            return AtomicIntegrationResult(
                code=DeliveryIntegrationAttentionCode.REVIEWED_WORKTREE_DIRTY,
                diagnostics=("change worktree is not clean at its reviewed boundary",),
            )
        return coordination, change_head, target_head

    def _integration_candidate_tree(
        self,
        candidate: DeliveryIntegrationCandidate,
        change_head: str,
        target_head: str,
    ) -> AtomicIntegrationResult | str:
        product_tree, merge_diagnostics = self._merge_tree(target_head, change_head)
        if product_tree is None:
            return AtomicIntegrationResult(
                code=DeliveryIntegrationAttentionCode.MERGE_CONFLICT,
                diagnostics=merge_diagnostics,
            )
        try:
            self._require_unchanged_completed_siblings(product_tree, target_head, candidate.change_id)
            publication_tree = self._replace_tree_path(
                product_tree,
                tuple(candidate.completion_path.split("/")),
                candidate.package_tree,
            )
        except ValueError as exc:
            return AtomicIntegrationResult(
                code=DeliveryIntegrationAttentionCode.COMPLETED_HISTORY_MUTATED,
                diagnostics=(str(exc),),
            )
        return publication_tree

    def _require_unchanged_completed_siblings(
        self,
        candidate_tree: str,
        target_head: str,
        change_id: str,
    ) -> None:
        completed_path = (b".owlbear", b"completed")
        target_tree = self._git("rev-parse", f"{target_head}^{{tree}}")
        target_entries = self._tree_entries_at_path(target_tree, completed_path)
        candidate_entries = self._tree_entries_at_path(candidate_tree, completed_path)
        current_leaf = change_id.encode()
        target_entries.pop(current_leaf, None)
        candidate_entries.pop(current_leaf, None)
        if candidate_entries != target_entries:
            message = "reviewed change mutates sibling completed history"
            raise ValueError(message)

    def cleanup_integrated_worktree(
        self,
        change_id: str,
        completion_path: str,
        completion_id: str,
    ) -> None:
        """Remove clean warm-worktree residue keyed by committed package identity."""
        coordination = self._coordinator.show(change_id)
        target_head = self._resolve(coordination.integration_target)
        if self._completion_identity(target_head, completion_path) != completion_id:
            _workspace_failure("target does not contain the committed completion identity")
        if not coordination.worktree_path.exists():
            return
        change_head = self._resolve(coordination.branch)
        self._require_worktree(coordination.worktree_path, coordination.branch, change_head)
        if change_head != coordination.last_reviewed_commit:
            _workspace_failure("warm worktree differs from its reviewed boundary")
        if self._git("-C", str(coordination.worktree_path), "status", "--porcelain"):
            _workspace_failure("warm worktree cleanup requires a clean source boundary")
        self._git("worktree", "remove", str(coordination.worktree_path))

    def _integration_identity_diagnostics(
        self,
        coordination: ChangeCoordination,
        candidate: DeliveryIntegrationCandidate,
    ) -> tuple[str, ...]:
        diagnostics = []
        if coordination.integration_target != self._integration_target:
            diagnostics.append("registered Integration target differs from the workspace manager")
        if candidate.integration_target != coordination.integration_target:
            diagnostics.append("candidate names another Integration target")
        if candidate.change_id != coordination.change_id:
            diagnostics.append("candidate source identity differs from the registered change")
        return tuple(diagnostics)

    def _merge_tree(self, target_head: str, change_head: str) -> tuple[str | None, tuple[str, ...]]:
        if target_head == change_head or self._is_ancestor(target_head, change_head, cwd=self._repository):
            return self._git("rev-parse", f"{change_head}^{{tree}}"), ()
        result = self._run_git("merge-tree", "--write-tree", target_head, change_head, check=False)
        output = result.stdout.decode().strip()
        if result.returncode == 0:
            return output.splitlines()[0], ()
        diagnostics = tuple(line for line in (*output.splitlines()[1:], *result.stderr.decode().splitlines()) if line)
        return None, diagnostics or ("reviewed product tree conflicts with the Integration target",)

    def _integration_conflict_paths(self, target_head: str, change_head: str) -> set[bytes]:
        result = self._run_git("merge-tree", "--write-tree", "-z", target_head, change_head, check=False)
        if result.returncode == 0:
            _workspace_failure("Integration repair requires an existing merge conflict")
        records = tuple(record for record in result.stdout.split(b"\0") if record)
        paths = set()
        for record in records:
            metadata, separator, path = record.partition(b"\t")
            parts = metadata.split()
            if separator and len(parts) == _TREE_ENTRY_PARTS and parts[2] in {b"1", b"2", b"3"}:
                paths.add(path)
        if not paths:
            _workspace_failure("Integration conflict paths could not be identified")
        return paths

    def _resolved_integration_repair_tree(
        self,
        target_head: str,
        change_head: str,
        resolution_tree: str,
        conflict_paths: set[bytes],
    ) -> str:
        result = self._run_git("merge-tree", "--write-tree", target_head, change_head, check=False)
        output = result.stdout.decode().splitlines()
        if result.returncode == 0 or not output:
            _workspace_failure("Integration repair requires an existing merge conflict")
        tree = output[0]
        for path in sorted(conflict_paths):
            parts = tuple(path.split(b"/"))
            replacement = self._tree_entry_at_path(resolution_tree, parts)
            tree = self._replace_tree_entry(tree, parts, replacement)
        return tree

    def _tree_entry_at_path(self, tree: str, path: tuple[bytes, ...]) -> bytes | None:
        for part in path[:-1]:
            existing = self._tree_entries(tree).get(part)
            if existing is None:
                return None
            metadata = existing.split(b"\t", 1)[0].split()
            if len(metadata) != _TREE_ENTRY_PARTS or metadata[1] != b"tree":
                return None
            tree = metadata[2].decode()
        return self._tree_entries(tree).get(path[-1])

    def _replace_tree_entry(self, tree: str, path: tuple[bytes, ...], replacement: bytes | None) -> str:
        entries = self._tree_entries(tree)
        name = path[0]
        if len(path) == 1:
            if replacement is None:
                entries.pop(name, None)
            else:
                entries[name] = replacement
        else:
            existing = entries.get(name)
            if existing is None:
                child = self._git("mktree", input_bytes=b"")
            else:
                metadata = existing.split(b"\t", 1)[0].split()
                if len(metadata) != _TREE_ENTRY_PARTS or metadata[1] != b"tree":
                    _workspace_failure(f"Integration conflict parent is not a tree: {os.fsdecode(name)}")
                child = metadata[2].decode()
            child = self._replace_tree_entry(child, path[1:], replacement)
            entries[name] = b"040000 tree " + child.encode() + b"\t" + name
        content = b"\0".join(entries[key] for key in sorted(entries)) + b"\0"
        return self._git("mktree", "-z", input_bytes=content)

    def _changed_paths(self, parent: str, child: str) -> set[bytes]:
        result = self._run_git(
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "-r",
            "-z",
            parent,
            child,
        )
        return {path for path in result.stdout.split(b"\0") if path}

    def _replace_tree_path(self, tree: str, path: tuple[str, ...], replacement_tree: str) -> str:
        if not path or any(not part or part in {".", ".."} for part in path):
            message = "completion path must be a contained nonempty Git path"
            raise ValueError(message)
        name = path[0].encode()
        entries = self._tree_entries(tree)
        existing = entries.get(name)
        if len(path) == 1:
            entries[name] = b"040000 tree " + replacement_tree.encode() + b"\t" + name
        else:
            if existing is None:
                child = self._git("mktree", input_bytes=b"")
            else:
                metadata = existing.split(b"\t", 1)[0].split()
                if len(metadata) != _TREE_ENTRY_PARTS or metadata[1] != b"tree":
                    message = f"completed-history path component is not a tree: {path[0]}"
                    raise ValueError(message)
                child = metadata[2].decode()
            replacement = self._replace_tree_path(child, path[1:], replacement_tree)
            entries[name] = b"040000 tree " + replacement.encode() + b"\t" + name
        content = b"\0".join(entries[key] for key in sorted(entries)) + b"\0"
        return self._git("mktree", "-z", input_bytes=content)

    def _tree_entries(self, tree: str) -> dict[bytes, bytes]:
        content = self._run_git("ls-tree", "-z", tree).stdout
        records = tuple(record for record in content.split(b"\0") if record)
        return {record.split(b"\t", 1)[1]: record for record in records}

    def _tree_entries_at_path(self, tree: str, path: tuple[bytes, ...]) -> dict[bytes, bytes]:
        for part in path:
            existing = self._tree_entries(tree).get(part)
            if existing is None:
                return {}
            metadata = existing.split(b"\t", 1)[0].split()
            if len(metadata) != _TREE_ENTRY_PARTS or metadata[1] != b"tree":
                message = f"completed-history path component is not a tree: {part.decode()}"
                raise ValueError(message)
            tree = metadata[2].decode()
        return self._tree_entries(tree)

    def _write_integration_commit(
        self,
        candidate: DeliveryIntegrationCandidate,
        tree: str,
        target_head: str,
        change_head: str,
    ) -> str:
        arguments = ["commit-tree", tree, "-p", target_head]
        if change_head != target_head:
            arguments.extend(("-p", change_head))
        arguments.extend(("-m", f"Integrate {candidate.change_id} ({candidate.candidate_id})"))
        return self._git(*arguments)

    def _anchored_integration_commit(
        self,
        candidate: DeliveryIntegrationCandidate,
        tree: str,
        target_head: str,
        change_head: str,
        reference: str,
    ) -> str:
        current = self._resolve(reference, missing_ok=True)
        if current is not None and self._integration_commit_matches(
            current,
            candidate,
            tree,
            target_head,
            change_head,
        ):
            return current
        commit = self._write_integration_commit(candidate, tree, target_head, change_head)
        self._git("update-ref", reference, commit, current or "0" * 40)
        return commit

    def _write_external_completion_proposal(
        self,
        candidate: DeliveryIntegrationCandidate,
        tree: str,
        target_head: str,
    ) -> str:
        return self._git(
            "commit-tree",
            tree,
            "-p",
            target_head,
            "-m",
            f"Complete externally integrated {candidate.change_id} ({candidate.candidate_id})",
        )

    def _external_completion_proposal_matches(
        self,
        commit: str,
        candidate: DeliveryIntegrationCandidate,
        tree: str,
        target_head: str,
    ) -> bool:
        parents = self._git("rev-list", "--parents", "-n", "1", commit).split()
        return (
            self._git("rev-parse", f"{commit}^{{tree}}") == tree
            and parents == [commit, target_head]
            and self._git("show", "-s", "--format=%B", commit).strip()
            == f"Complete externally integrated {candidate.change_id} ({candidate.candidate_id})"
        )

    def _integration_commit_matches(
        self,
        commit: str,
        candidate: DeliveryIntegrationCandidate,
        tree: str,
        target_head: str,
        change_head: str,
    ) -> bool:
        parents = self._git("rev-list", "--parents", "-n", "1", commit).split()
        expected_parents = [target_head] if change_head == target_head else [target_head, change_head]
        return (
            self._resolve(f"{commit}^{{tree}}") == tree
            and parents == [commit, *expected_parents]
            and self._git("show", "-s", "--format=%B", commit).strip()
            == f"Integrate {candidate.change_id} ({candidate.candidate_id})"
        )

    @staticmethod
    def _integration_candidate_ref(change_id: str) -> str:
        return f"refs/owlbear/integration-candidates/{change_id}"

    def _published_completion_commit(self, candidate: DeliveryIntegrationCandidate) -> str | None:
        target_head = self._resolve(candidate.integration_target)
        if self._completion_identity(target_head, candidate.completion_path) != candidate.completion_id:
            return None
        commit = self._git(
            "log",
            "-1",
            "--format=%H",
            candidate.integration_target,
            "--",
            f"{candidate.completion_path}/completion.json",
        )
        return commit or target_head

    def _completion_identity(self, commit: str, completion_path: str) -> str | None:
        result = self._run_git(
            "show",
            f"{commit}:{completion_path}/completion.json",
            check=False,
        )
        if result.returncode != 0:
            return None
        return hashlib.sha256(result.stdout).hexdigest()

    def integrate(self, change_id: str, reviewed_commits: tuple[str, ...]) -> IntegrationResult:
        """Reject the retired local target Integration operation."""
        del change_id, reviewed_commits
        _workspace_failure("local target Integration is disabled; external acceptance is required")

    def _publish_integration_finding(
        self,
        coordination: ChangeCoordination,
        change_head: str,
        target_head: str,
    ) -> IntegrationFinding:
        identity = hashlib.sha256(f"{coordination.change_id}:{change_head}:{target_head}".encode()).hexdigest()[:16]
        finding = IntegrationFinding(
            finding_id=f"integration-{identity}",
            change_id=coordination.change_id,
            change_head=change_head,
            target_head=target_head,
            integration_target=coordination.integration_target,
            detail="Change and integration target conflict; accepted change-level composition authority is required.",
        )
        return self._coordinator.publish_finding(finding)

    def _require_worktree(self, worktree: Path, branch: str, expected_head: str) -> None:
        if self._resolve("HEAD", cwd=worktree) != expected_head:
            _workspace_failure("change worktree head differs from its branch")
        current = self._git("-C", str(worktree), "branch", "--show-current")
        if current != branch:
            _workspace_failure("change worktree is attached to another branch")

    def _require_ancestor(self, commit: str, descendant: str) -> None:
        if not self._is_ancestor(commit, descendant, cwd=self._repository):
            _workspace_failure("reviewed commit is not an ancestor of the change head")

    @staticmethod
    def _is_ancestor(ancestor: str, descendant: str, *, cwd: Path) -> bool:
        result = subprocess.run(  # noqa: S603 - fixed Git executable and argument-vector invocation.
            (resolve_git_executable(), "-C", str(cwd), "merge-base", "--is-ancestor", ancestor, descendant),
            check=False,
            capture_output=True,
        )
        return result.returncode == 0

    def _resolve(self, revision: str, *, cwd: Path | None = None, missing_ok: bool = False) -> str | None:
        try:
            return self._git("rev-parse", "--verify", f"{revision}^{{commit}}", cwd=cwd)
        except subprocess.CalledProcessError:
            if missing_ok:
                return None
            raise

    def _git(
        self,
        *arguments: str,
        cwd: Path | None = None,
        check: bool = True,
        input_bytes: bytes | None = None,
    ) -> str:
        result = self._run_git(*arguments, cwd=cwd, check=check, input_bytes=input_bytes)
        return result.stdout.decode().strip()

    def _run_git(
        self,
        *arguments: str,
        cwd: Path | None = None,
        check: bool = True,
        input_bytes: bytes | None = None,
    ) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(  # noqa: S603 - fixed Git executable and argument-vector invocation.
            (resolve_git_executable(), "-C", str(cwd or self._repository), *arguments),
            check=check,
            capture_output=True,
            input=input_bytes,
        )


def _replacement(
    root: Path,
    path: Path,
    previous: bytes,
    replacement: BaseModel,
) -> ReplacementTransactionParticipant:
    return ReplacementTransactionParticipant(
        root,
        path.relative_to(root),
        previous,
        _model_content(replacement),
    )


def _model_content(model: BaseModel) -> bytes:
    payload = model.model_dump(mode="json")
    return f"{json.dumps(payload, sort_keys=True, separators=(',', ':'))}\n".encode()


def _coordination_conflict(detail: str) -> Never:
    raise CoordinationConflictError(detail)


def _publication_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        msg = "publication reservation timestamp requires a timezone"
        raise ValueError(msg)
    return parsed.astimezone(UTC)


def _workspace_failure(detail: str) -> Never:
    raise RuntimeError(detail)
