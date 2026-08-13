"""Per-change writer coordination and Git workspace management."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from itertools import pairwise
from pathlib import Path
from typing import TYPE_CHECKING, Literal, Never

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

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
    from collections.abc import Callable, Iterator
    from contextlib import AbstractContextManager

_OCC_RETRY_LIMIT = 8
_PUBLICATION_LEASE_MAX_SECONDS = 600
_PUBLICATION_OPERATION_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
_CHANGE_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@dataclass(frozen=True)
class _RegisteredGitWorktree:
    """Parsed Git registration for one managed worktree path."""

    head: str | None
    branch: str | None
    locked: bool
    prunable: bool
    bare: bool


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


class ChangeWorktreeAttentionCode(StrEnum):
    """Typed evidence that one retained Change worktree needs reconciliation."""

    COORDINATION_MISSING = "coordination-missing"
    GIT_REGISTRATION_MISSING = "git-registration-missing"
    WORKTREE_MISSING = "worktree-missing"
    BRANCH_MISSING = "branch-missing"
    BRANCH_MISMATCH = "branch-mismatch"
    DETACHED = "detached"
    PRUNABLE = "prunable"
    BARE = "bare"
    COORDINATION_PATH_MISMATCH = "coordination-path-mismatch"


class RetainedChangeWorktree(_WorkspaceModel):
    """Read-only Git, filesystem, and coordination facts for one Change."""

    change_id: ChangeId
    worktree_path: Path
    branch: str = Field(min_length=1)
    branch_head: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    coordination_registered: bool
    git_registered: bool
    worktree_present: bool
    worktree_head: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    worktree_branch: str | None = None
    worktree_locked: bool = False
    worktree_prunable: bool = False
    worktree_bare: bool = False
    attention: tuple[ChangeWorktreeAttentionCode, ...] = ()
    writer: ChangeWriter | None = None
    publication_expiry: datetime | None = None


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


class IntegrationContext(_WorkspaceModel):
    """Exact source and target identities used to capture an Integration candidate."""

    change_id: ChangeId
    change_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    reviewed_change_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    integration_target: str = Field(min_length=1)
    target_head: str = Field(pattern=r"^[0-9a-f]{40}$")


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

    def acquisition_lock(self) -> AbstractContextManager[None]:
        """Serialize portfolio selection and staged claim preparation."""
        lock_root = self._state_root / "claims" / "acquisition-lock"
        return locked_roots((lock_root,))

    @contextmanager
    def publication_lock(self, change_id: str, *, blocking: bool = True) -> Iterator[PublicationLock]:
        """Serialize bounded publication attempts for one Change across processes."""
        self._coordination_path(change_id)
        namespace_root = self._state_root / "claims" / "publication-locks"
        lock_root = namespace_root / change_id
        with ExitStack() as child_locks:
            with locked_roots((namespace_root,), blocking=blocking):
                child_locks.enter_context(locked_roots((lock_root,), blocking=blocking))
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

    def list_registered(self) -> tuple[ChangeCoordination, ...]:
        """Return all registered Change coordination records in stable order."""
        if not self._coordination_root.exists():
            return ()
        if self._coordination_root.is_symlink() or not self._coordination_root.is_dir():
            _coordination_conflict("change coordination root is not a safe directory")
        records = []
        for path in sorted(self._coordination_root.iterdir(), key=lambda item: item.name):
            if path.name.startswith(".") or path.suffix != ".json":
                continue
            try:
                coordination = ChangeCoordination.model_validate_json(path.read_bytes())
            except OSError, ValidationError:
                _coordination_conflict(f"change coordination record is invalid: {path}")
            if path.stem != coordination.change_id:
                _coordination_conflict(f"change coordination record identity is invalid: {path}")
            records.append(coordination)
        return tuple(sorted(records, key=lambda item: item.change_id))

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
        self._register_worktree(worktree, branch, self._git)
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

    @classmethod
    def restore_worktree(cls, repository: Path, worktree: Path, branch: str) -> None:
        """Restore one absent managed worktree from its retained branch."""
        resolved_repository = repository.resolve()
        cls._register_worktree(
            worktree,
            branch,
            lambda *arguments: cls._run_managed_git(resolved_repository, *arguments),
        )

    @classmethod
    def remove_worktree(cls, repository: Path, worktree: Path) -> None:
        """Remove one managed worktree without forcing Git registration cleanup."""
        cls._run_managed_git(repository.resolve(), "worktree", "remove", str(worktree))

    @staticmethod
    def _run_managed_git(repository: Path, *arguments: str) -> str:
        result = subprocess.run(  # noqa: S603 - fixed Git executable and argument-vector invocation.
            (resolve_git_executable(), "-C", str(repository), *arguments),
            check=True,
            capture_output=True,
        )
        return result.stdout.decode().strip()

    @staticmethod
    def _register_worktree(worktree: Path, branch: str, git: Callable[..., str]) -> None:
        if worktree.exists():
            return
        worktree.parent.mkdir(parents=True, exist_ok=True)
        git("worktree", "add", str(worktree), branch)

    def show(self, change_id: str) -> ChangeCoordination:
        """Return current workspace coordination for transition validation."""
        return self._coordinator.show(change_id)

    def list_retained(self) -> tuple[RetainedChangeWorktree, ...]:
        """Inspect every retained Change worktree without changing Git or custody."""
        coordinations = {item.change_id: item for item in self._coordinator.list_registered()}
        registered = self._registered_worktrees()
        branch_heads = self._change_branch_heads()
        filesystem_ids = self._filesystem_change_ids()
        change_ids = sorted(set(coordinations) | set(registered) | set(branch_heads) | filesystem_ids)
        return tuple(
            self._retained_worktree(
                change_id,
                coordinations.get(change_id),
                registered.get(change_id),
                branch_heads.get(change_id),
            )
            for change_id in change_ids
        )

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
        self._register_worktree(worktree, coordination.branch, self._git)
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

    def _require_worktree(self, worktree: Path, branch: str, expected_head: str) -> None:
        if self._resolve("HEAD", cwd=worktree) != expected_head:
            _workspace_failure("change worktree head differs from its branch")
        current = self._git("-C", str(worktree), "branch", "--show-current")
        if current != branch:
            _workspace_failure("change worktree is attached to another branch")

    def _registered_worktrees(self) -> dict[str, _RegisteredGitWorktree]:
        completed = self._run_git("worktree", "list", "--porcelain", "-z")
        records: dict[str, _RegisteredGitWorktree] = {}
        for raw_record in completed.stdout.split(b"\0\0"):
            fields = tuple(field for field in raw_record.split(b"\0") if field)
            values = {field.partition(b" ")[0]: field.partition(b" ")[2] for field in fields}
            raw_path = values.get(b"worktree")
            if raw_path is None:
                continue
            path = Path(os.fsdecode(raw_path)).resolve()
            try:
                relative = path.relative_to(self._worktree_root)
            except ValueError:
                continue
            if len(relative.parts) != 1 or not _is_change_id(relative.name):
                continue
            change_id = relative.name
            if change_id in records:
                _workspace_failure(f"multiple Git worktrees are registered for Change {change_id}")
            records[change_id] = _RegisteredGitWorktree(
                head=_decode_optional(values.get(b"HEAD")),
                branch=_branch_name(values.get(b"branch")),
                locked=b"locked" in values,
                prunable=b"prunable" in values,
                bare=b"bare" in values,
            )
        return records

    def _change_branch_heads(self) -> dict[str, str]:
        prefix = "refs/heads/owlbear/change/"
        completed = self._run_git(
            "for-each-ref",
            "--format=%(refname)%00%(objectname)",
            "refs/heads/owlbear/change",
        )
        heads: dict[str, str] = {}
        for record in completed.stdout.splitlines():
            raw_ref, separator, raw_head = record.partition(b"\0")
            if not separator:
                continue
            ref = os.fsdecode(raw_ref)
            change_id = ref.removeprefix(prefix)
            if not ref.startswith(prefix) or not _is_change_id(change_id):
                continue
            heads[change_id] = os.fsdecode(raw_head)
        return heads

    def _filesystem_change_ids(self) -> set[str]:
        if not self._worktree_root.exists():
            return set()
        if self._worktree_root.is_symlink() or not self._worktree_root.is_dir():
            _workspace_failure("Change worktree root is not a safe directory")
        return {entry.name for entry in self._worktree_root.iterdir() if _is_change_id(entry.name)}

    @staticmethod
    def _worktree_present(expected_path: Path) -> bool:
        return expected_path.exists() and expected_path.is_dir() and not expected_path.is_symlink()

    @staticmethod
    def _coordination_attention(
        change_id: str,
        coordination: ChangeCoordination | None,
        expected_path: Path,
    ) -> set[ChangeWorktreeAttentionCode]:
        expected_branch = f"owlbear/change/{change_id}"
        if coordination is None:
            return {ChangeWorktreeAttentionCode.COORDINATION_MISSING}
        attention: set[ChangeWorktreeAttentionCode] = set()
        if coordination.branch != expected_branch:
            attention.add(ChangeWorktreeAttentionCode.BRANCH_MISMATCH)
        if coordination.worktree_path.resolve() != expected_path.resolve():
            attention.add(ChangeWorktreeAttentionCode.COORDINATION_PATH_MISMATCH)
        return attention

    @staticmethod
    def _registered_attention(
        registered: _RegisteredGitWorktree | None,
        expected_branch: str,
    ) -> set[ChangeWorktreeAttentionCode]:
        if registered is None:
            return {ChangeWorktreeAttentionCode.GIT_REGISTRATION_MISSING}
        attention: set[ChangeWorktreeAttentionCode] = set()
        if registered.bare:
            attention.add(ChangeWorktreeAttentionCode.BARE)
        if registered.prunable:
            attention.add(ChangeWorktreeAttentionCode.PRUNABLE)
        if registered.branch is None and not registered.bare:
            attention.add(ChangeWorktreeAttentionCode.DETACHED)
        elif registered.branch != expected_branch:
            attention.add(ChangeWorktreeAttentionCode.BRANCH_MISMATCH)
        return attention

    def _retained_attention(
        self,
        change_id: str,
        coordination: ChangeCoordination | None,
        registered: _RegisteredGitWorktree | None,
        branch_head: str | None,
        expected_path: Path,
    ) -> set[ChangeWorktreeAttentionCode]:
        expected_branch = f"owlbear/change/{change_id}"
        attention = self._coordination_attention(change_id, coordination, expected_path)
        attention.update(self._registered_attention(registered, expected_branch))
        worktree_present = self._worktree_present(expected_path)
        if not worktree_present:
            attention.add(ChangeWorktreeAttentionCode.WORKTREE_MISSING)
        if branch_head is None:
            attention.add(ChangeWorktreeAttentionCode.BRANCH_MISSING)
        return attention

    def _retained_worktree(
        self,
        change_id: str,
        coordination: ChangeCoordination | None,
        registered: _RegisteredGitWorktree | None,
        branch_head: str | None,
    ) -> RetainedChangeWorktree:
        expected_branch = f"owlbear/change/{change_id}"
        expected_path = self._worktree_root / change_id
        worktree_present = self._worktree_present(expected_path)
        attention = self._retained_attention(change_id, coordination, registered, branch_head, expected_path)
        return RetainedChangeWorktree(
            change_id=change_id,
            worktree_path=expected_path,
            branch=expected_branch,
            branch_head=branch_head,
            coordination_registered=coordination is not None,
            git_registered=registered is not None,
            worktree_present=worktree_present,
            worktree_head=registered.head if registered is not None else None,
            worktree_branch=registered.branch if registered is not None else None,
            worktree_locked=registered.locked if registered is not None else False,
            worktree_prunable=registered.prunable if registered is not None else False,
            worktree_bare=registered.bare if registered is not None else False,
            attention=tuple(code for code in ChangeWorktreeAttentionCode if code in attention),
            writer=coordination.writer if coordination is not None else None,
            publication_expiry=coordination.publication_expiry if coordination is not None else None,
        )

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


def _is_change_id(value: str) -> bool:
    return _CHANGE_ID_PATTERN.fullmatch(value) is not None


def _decode_optional(value: bytes | None) -> str | None:
    return None if value is None else os.fsdecode(value)


def _branch_name(value: bytes | None) -> str | None:
    branch = _decode_optional(value)
    return None if branch is None else branch.removeprefix("refs/heads/")
