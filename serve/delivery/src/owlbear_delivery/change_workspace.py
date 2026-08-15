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
from typing import TYPE_CHECKING, Literal, Never, Self

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

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
_MERGE_COMMIT_MIN_PARENTS = 2
_PORCELAIN_WORKTREE_STATUS_INDEX = 1


@dataclass(frozen=True)
class _RegisteredGitWorktree:
    """Parsed Git registration for one managed worktree path."""

    path: Path
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


class _ChangeWorktreeCleanupRecord(_WorkspaceModel):
    """Identity-bound record for one exact Change worktree cleanup."""

    schema_version: Literal[1] = 1
    cleanup_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    change_id: ChangeId
    branch: str = Field(min_length=1)
    worktree_path: Path
    branch_head: str = Field(pattern=r"^[0-9a-f]{40}$")

    @model_validator(mode="after")
    def _validate_identity(self) -> Self:
        identity = "\0".join((self.change_id, self.branch, str(self.worktree_path), self.branch_head)).encode()
        if self.cleanup_id != hashlib.sha256(identity).hexdigest():
            message = "Change worktree cleanup identity is invalid"
            raise ValueError(message)
        return self

    @classmethod
    def create(
        cls,
        *,
        change_id: str,
        branch: str,
        worktree_path: Path,
        branch_head: str,
    ) -> Self:
        identity = "\0".join((change_id, branch, str(worktree_path), branch_head)).encode()
        return cls(
            cleanup_id=hashlib.sha256(identity).hexdigest(),
            change_id=change_id,
            branch=branch,
            worktree_path=worktree_path,
            branch_head=branch_head,
        )


class ChangeWorktreeCleanupIntent(_ChangeWorktreeCleanupRecord):
    """Durable intent to remove one exact managed Change worktree."""


class ChangeWorktreeCleanup(_ChangeWorktreeCleanupRecord):
    """Durable proof that one exact Change worktree was removed."""


class SyncChangeWithTarget(_WorkspaceModel):
    """Exact preconditions for one target synchronization attempt."""

    change_id: ChangeId
    expected_target: str = Field(pattern=r"^[0-9a-f]{40}$")
    operation_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class AdoptExternalHead(_WorkspaceModel):
    """Exact preconditions for adopting one remote Change descendant."""

    change_id: ChangeId
    expected_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    adopted_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    operation_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")

    @model_validator(mode="after")
    def _validate_head_movement(self) -> Self:
        if self.expected_head == self.adopted_head:
            message = "external Change head adoption requires head movement"
            raise ValueError(message)
        return self


class PromoteExternalHead(_WorkspaceModel):
    """Exact authority request for promoting one adopted external Change head."""

    change_id: ChangeId
    expected_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    operation_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class ChangeExternalHeadAdoptionIntent(_WorkspaceModel):
    """Durable intent retained across one external Change-head adoption attempt."""

    schema_version: Literal[1] = 1
    operation_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
    change_id: ChangeId
    branch: str = Field(min_length=1)
    expected_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    adopted_head: str = Field(pattern=r"^[0-9a-f]{40}$")

    @classmethod
    def create(cls, request: AdoptExternalHead, branch: str) -> Self:
        """Create one exact operation intent from the validated adoption request."""
        return cls(
            operation_id=request.operation_id,
            change_id=request.change_id,
            branch=branch,
            expected_head=request.expected_head,
            adopted_head=request.adopted_head,
        )


class TargetSyncConflictRequest(_WorkspaceModel):
    """Exact target and operation identity for one preserved merge conflict."""

    change_id: ChangeId
    target_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    operation_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class ChangeTargetSyncReceipt(_WorkspaceModel):
    """Durable evidence for one exact target merge in a managed Change worktree."""

    schema_version: Literal[1] = 1
    receipt_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    operation_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
    change_id: ChangeId
    integration_target: str = Field(min_length=1)
    expected_target: str = Field(pattern=r"^[0-9a-f]{40}$")
    target_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    change_head_before: str = Field(pattern=r"^[0-9a-f]{40}$")
    merged_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    merge_commit: bool

    @classmethod
    def create(  # noqa: PLR0913
        cls,
        *,
        operation_id: str,
        change_id: str,
        integration_target: str,
        expected_target: str,
        target_head: str,
        change_head_before: str,
        merged_head: str,
        merge_commit: bool,
    ) -> Self:
        """Create a content-addressed receipt from one completed target merge."""
        values = {
            "operation_id": operation_id,
            "change_id": change_id,
            "integration_target": integration_target,
            "expected_target": expected_target,
            "target_head": target_head,
            "change_head_before": change_head_before,
            "merged_head": merged_head,
            "merge_commit": merge_commit,
        }
        candidate = cls.model_construct(receipt_id="0" * 64, **values)
        return cls(receipt_id=_target_sync_digest(candidate), **values)

    @model_validator(mode="after")
    def _validate_receipt(self) -> Self:
        if self.expected_target != self.target_head:
            message = "target synchronization receipt names a different fetched target"
            raise ValueError(message)
        if self.receipt_id != _target_sync_digest(self):
            message = "target synchronization receipt identity is invalid"
            raise ValueError(message)
        return self


class ChangeTargetSyncConflictState(_WorkspaceModel):
    """Durable identity of one preserved target merge conflict."""

    schema_version: Literal[1] = 1
    conflict_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    operation_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
    change_id: ChangeId
    target_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    change_head_before: str = Field(pattern=r"^[0-9a-f]{40}$")
    conflict_paths: tuple[str, ...] = ()

    @field_validator("conflict_paths", mode="before")
    @classmethod
    def _normalize_conflict_paths(cls, value: object) -> object:
        return tuple(value) if isinstance(value, list) else value

    @classmethod
    def create(
        cls,
        *,
        operation_id: str,
        change_id: str,
        target_head: str,
        change_head_before: str,
        conflict_paths: tuple[str, ...],
    ) -> Self:
        """Create deterministic evidence for one preserved merge state."""
        values = {
            "operation_id": operation_id,
            "change_id": change_id,
            "target_head": target_head,
            "change_head_before": change_head_before,
            "conflict_paths": conflict_paths,
        }
        candidate = cls.model_construct(conflict_id="0" * 64, **values)
        return cls(conflict_id=_target_sync_conflict_digest(candidate), **values)

    @model_validator(mode="after")
    def _validate_state(self) -> Self:
        if self.conflict_id != _target_sync_conflict_digest(self):
            message = "target synchronization conflict identity is invalid"
            raise ValueError(message)
        return self


class ChangeTargetSyncAbortReceipt(_WorkspaceModel):
    """Content-addressed evidence that one target merge was explicitly aborted."""

    schema_version: Literal[1] = 1
    receipt_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    operation_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
    change_id: ChangeId
    target_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    restored_head: str = Field(pattern=r"^[0-9a-f]{40}$")

    @classmethod
    def create(
        cls,
        *,
        operation_id: str,
        change_id: str,
        target_head: str,
        restored_head: str,
    ) -> Self:
        """Create deterministic evidence for one restored reviewed boundary."""
        values = {
            "operation_id": operation_id,
            "change_id": change_id,
            "target_head": target_head,
            "restored_head": restored_head,
        }
        candidate = cls.model_construct(receipt_id="0" * 64, **values)
        return cls(receipt_id=_target_sync_abort_digest(candidate), **values)

    @model_validator(mode="after")
    def _validate_receipt(self) -> Self:
        if self.receipt_id != _target_sync_abort_digest(self):
            message = "target synchronization abort identity is invalid"
            raise ValueError(message)
        return self


class ChangeExternalHeadAdoptionReceipt(_WorkspaceModel):
    """Content-addressed evidence that one remote Change descendant was adopted."""

    schema_version: Literal[1] = 1
    receipt_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    operation_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
    change_id: ChangeId
    branch: str = Field(min_length=1)
    expected_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    adopted_head: str = Field(pattern=r"^[0-9a-f]{40}$")

    @classmethod
    def create(
        cls,
        *,
        operation_id: str,
        change_id: str,
        branch: str,
        expected_head: str,
        adopted_head: str,
    ) -> Self:
        """Create deterministic evidence for one adopted remote Change head."""
        values = {
            "operation_id": operation_id,
            "change_id": change_id,
            "branch": branch,
            "expected_head": expected_head,
            "adopted_head": adopted_head,
        }
        candidate = cls.model_construct(receipt_id="0" * 64, **values)
        return cls(receipt_id=_external_head_adoption_digest(candidate), **values)

    @model_validator(mode="after")
    def _validate_receipt(self) -> Self:
        if self.expected_head == self.adopted_head:
            message = "external Change head adoption requires head movement"
            raise ValueError(message)
        if self.receipt_id != _external_head_adoption_digest(self):
            message = "external Change head adoption receipt identity is invalid"
            raise ValueError(message)
        return self


class ChangeExternalHeadPromotionReceipt(_WorkspaceModel):
    """Content-addressed evidence that one adopted Change head gained review authority."""

    schema_version: Literal[1] = 1
    receipt_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    operation_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
    change_id: ChangeId
    branch: str = Field(min_length=1)
    adoption_receipt_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    promoted_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    provenance: Literal["explicit", "finalization"]

    @classmethod
    def create(  # noqa: PLR0913
        cls,
        *,
        operation_id: str,
        change_id: str,
        branch: str,
        adoption_receipt_id: str,
        promoted_head: str,
        provenance: Literal["explicit", "finalization"],
    ) -> Self:
        """Create deterministic evidence for one promoted adopted Change head."""
        values = {
            "operation_id": operation_id,
            "change_id": change_id,
            "branch": branch,
            "adoption_receipt_id": adoption_receipt_id,
            "promoted_head": promoted_head,
            "provenance": provenance,
        }
        candidate = cls.model_construct(receipt_id="0" * 64, **values)
        return cls(receipt_id=_external_head_promotion_digest(candidate), **values)

    @model_validator(mode="after")
    def _validate_receipt(self) -> Self:
        if self.receipt_id != _external_head_promotion_digest(self):
            message = "external Change head promotion receipt identity is invalid"
            raise ValueError(message)
        return self


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
    target_sync_receipt: ChangeTargetSyncReceipt | None = None
    target_sync_conflict: ChangeTargetSyncConflictState | None = None
    target_sync_abort_receipt: ChangeTargetSyncAbortReceipt | None = None
    external_head_adoption_intent: ChangeExternalHeadAdoptionIntent | None = None
    external_head_adoption_receipt: ChangeExternalHeadAdoptionReceipt | None = None
    external_head_adoption_receipts: tuple[ChangeExternalHeadAdoptionReceipt, ...] = ()
    external_head_promotion_receipt: ChangeExternalHeadPromotionReceipt | None = None
    external_head_promotion_receipts: tuple[ChangeExternalHeadPromotionReceipt, ...] = ()
    worktree_cleanup_intent: ChangeWorktreeCleanupIntent | None = None
    worktree_cleanup: ChangeWorktreeCleanup | None = None

    @model_validator(mode="before")
    @classmethod
    def _discard_retired_publication_reservation(cls, value: object) -> object:
        if not isinstance(value, dict) or "publication_operation_id" not in value:
            return value
        migrated: dict[object, object] = dict(value)
        migrated.pop("publication_operation_id", None)
        migrated.pop("publication_expires_at", None)
        return migrated

    @field_validator("external_head_adoption_receipts", mode="before")
    @classmethod
    def _normalize_external_head_adoption_receipts(cls, value: object) -> object:
        return tuple(value) if isinstance(value, list) else value

    @field_validator("external_head_promotion_receipts", mode="before")
    @classmethod
    def _normalize_external_head_promotion_receipts(cls, value: object) -> object:
        return tuple(value) if isinstance(value, list) else value

    @property
    def publication_expiry(self) -> datetime | None:
        """Return the normalized lease expiry when publication owns this Change."""
        if self.publication_lease is None:
            return None
        return _publication_timestamp(self.publication_lease.expires_at)

    @model_validator(mode="after")
    def _validate_target_sync_receipt(self) -> Self:
        if self.target_sync_receipt is not None and self.target_sync_receipt.change_id != self.change_id:
            message = "target synchronization receipt does not match its Change"
            raise ValueError(message)
        if self.target_sync_abort_receipt is not None and self.target_sync_abort_receipt.change_id != self.change_id:
            message = "target synchronization abort receipt does not match its Change"
            raise ValueError(message)
        if (
            self.external_head_adoption_receipt is not None
            and self.external_head_adoption_receipt.change_id != self.change_id
        ):
            message = "external Change head adoption receipt does not match its Change"
            raise ValueError(message)
        if (
            self.external_head_adoption_intent is not None
            and self.external_head_adoption_intent.change_id != self.change_id
        ):
            message = "external Change head adoption intent does not match its Change"
            raise ValueError(message)
        if any(receipt.change_id != self.change_id for receipt in self.external_head_adoption_receipts):
            message = "external Change head adoption history does not match its Change"
            raise ValueError(message)
        operation_ids = tuple(receipt.operation_id for receipt in self.external_head_adoption_receipts)
        if len(operation_ids) != len(set(operation_ids)):
            message = "external Change head adoption history must contain unique operations"
            raise ValueError(message)
        self._validate_external_head_promotion_receipts()
        if self.target_sync_conflict is not None and self.target_sync_conflict.change_id != self.change_id:
            message = "target synchronization conflict does not match its Change"
            raise ValueError(message)
        if self.target_sync_receipt is not None and self.target_sync_conflict is not None:
            message = "target synchronization receipt and conflict cannot coexist"
            raise ValueError(message)
        if self.target_sync_abort_receipt is not None and self.target_sync_conflict is not None:
            message = "target synchronization abort receipt and conflict cannot coexist"
            raise ValueError(message)
        return self

    def _validate_external_head_promotion_receipts(self) -> None:
        if (
            self.external_head_promotion_receipt is not None
            and self.external_head_promotion_receipt.change_id != self.change_id
        ):
            message = "external Change head promotion receipt does not match its Change"
            raise ValueError(message)
        if any(receipt.change_id != self.change_id for receipt in self.external_head_promotion_receipts):
            message = "external Change head promotion history does not match its Change"
            raise ValueError(message)
        operation_ids = tuple(receipt.operation_id for receipt in self.external_head_promotion_receipts)
        if len(operation_ids) != len(set(operation_ids)):
            message = "external Change head promotion history must contain unique operations"
            raise ValueError(message)


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
    LOCKED = "locked"
    WORKTREE_DIRTY = "worktree-dirty"
    OWNERSHIP_AMBIGUOUS = "ownership-ambiguous"
    UNEXPECTED_FILESYSTEM_STATE = "unexpected-filesystem-state"
    WORKTREE_HEAD_MISMATCH = "worktree-head-mismatch"


class RetainedChangeWorktree(_WorkspaceModel):
    """Read-only Git, filesystem, and coordination facts for one Change."""

    change_id: ChangeId
    worktree_path: Path
    branch: str = Field(min_length=1)
    branch_head: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    last_reviewed_commit: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
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


class ChangeWorktreeAttentionError(RuntimeError):
    """A retained Change worktree requires explicit reconciliation."""

    code = "ERR_TARGET_WORKTREE_ATTENTION"
    retry_safe = False

    def __init__(self, change_id: str, attention: tuple[ChangeWorktreeAttentionCode, ...]) -> None:
        self.change_id = change_id
        self.attention = attention
        detail = ", ".join(code.value for code in attention)
        super().__init__(f"Change worktree requires attention: {detail}")


class ChangeTargetSyncConflictError(RuntimeError):
    """A target merge entered a preserved conflict state in the Change worktree."""

    code = "ERR_TARGET_SYNC_CONFLICT"
    retry_safe = False

    def __init__(
        self,
        change_id: str,
        operation_id: str,
        target_head: str,
        conflict_paths: tuple[str, ...],
    ) -> None:
        self.change_id = change_id
        self.operation_id = operation_id
        self.target_head = target_head
        self.conflict_paths = conflict_paths
        detail = ", ".join(conflict_paths) if conflict_paths else "unclassified paths"
        super().__init__(f"target synchronization requires conflict resolution: {detail}")


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


class CapacityConfigurationConflictError(CoordinationConflictError):
    """Configured writer capacity is below the active holder count."""

    def __init__(self, active_holders: int, configured_capacity: int) -> None:
        self.active_holders = active_holders
        self.configured_capacity = configured_capacity
        super().__init__(f"active writers exceed configured writer capacity: {active_holders} > {configured_capacity}")


class CapacityLedgerConflictError(CoordinationConflictError):
    """The host capacity ledger changed during startup reconfiguration."""

    def __init__(self) -> None:
        super().__init__("host capacity ledger changed concurrently")


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
        if (
            coordination.writer is not None
            or publication_active
            or coordination.worktree_cleanup_intent is not None
            or coordination.worktree_cleanup is not None
            or change_id in ledger.change_ids
        ):
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

    def update(
        self,
        coordination: ChangeCoordination,
        *,
        lock: PublicationLock | None = None,
    ) -> ChangeCoordination:
        """OCC-replace one registered per-change record without touching capacity."""
        existing = self.show(coordination.change_id)
        if existing.publication_lease is not None and existing != coordination:
            _coordination_conflict("workspace update cannot change a reserved publication boundary")
        if lock is not None:
            self._require_publication_lock(lock, coordination.change_id)
            return self._update(coordination)
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
        if (
            coordination.writer is not None
            or coordination.worktree_cleanup_intent is not None
            or coordination.worktree_cleanup is not None
            or (existing_lease is not None and not same_owner and not expired)
        ):
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
                    raise CapacityConfigurationConflictError(len(existing.change_ids), self._capacity)
                updated = existing.model_copy(update={"capacity": self._capacity})
                try:
                    self._commit(
                        "reconfigure-capacity",
                        (_replacement(self._state_root, self._ledger_path, existing_bytes, updated),),
                    )
                except TransactionConflictError as exc:
                    raise CapacityLedgerConflictError from exc
            return
        try:
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
        except TransactionConflictError as exc:
            raise CapacityLedgerConflictError from exc

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
        if worktree_root.is_symlink() or (worktree_root.exists() and not worktree_root.is_dir()):
            _workspace_failure("Change worktree root is not a safe directory")
        self._worktree_root = worktree_root.resolve()
        self._coordinator = coordinator
        self._integration_target = integration_target
        self._remote = remote
        self._git("check-ref-format", self._target_ref())

    @property
    def repository(self) -> Path:
        """Return the engine-owned repository used for managed Change reads."""
        return self._repository

    def _target_ref(self) -> str:
        if self._integration_target.startswith("refs/remotes/"):
            return self._integration_target
        return f"refs/remotes/{self._remote}/{self._integration_target}"

    def ensure(
        self,
        change_id: str,
        *,
        recovery_reviewed_head: str | None = None,
    ) -> ChangeCoordination:
        """Ensure one healthy warm branch and worktree without repairing degraded state."""
        if not _is_change_id(change_id):
            msg = "change identity is not a safe worktree identity"
            raise ValueError(msg)
        try:
            existing = self._coordinator.show(change_id)
        except CoordinationConflictError:
            existing = None
        if existing is not None:
            self._validate_existing_coordination(existing, recovery_reviewed_head)
            self._validate_existing_worktree(existing)
            self._require_worktree(
                change_id,
                existing.worktree_path,
                existing.branch,
                self._resolve(existing.branch),
            )
            return existing
        branch = f"owlbear/change/{change_id}"
        self._git("check-ref-format", f"refs/heads/{branch}")
        worktree = self._worktree_root / change_id
        target_head = self._resolve(self._target_ref())
        branch_head = self._resolve(branch, missing_ok=True)
        if branch_head is None:
            if recovery_reviewed_head is not None:
                _coordination_conflict("recovery reviewed head requires an existing Change branch")
            self._validate_unregistered_worktree(change_id, recovery_reviewed_head, branch_head)
            self._git("branch", branch, target_head)
            branch_head = target_head
            last_reviewed_commit = target_head
        else:
            if recovery_reviewed_head is None:
                _coordination_conflict("existing Change branch requires an exact recovery reviewed head")
            self._require_ancestor(recovery_reviewed_head, branch_head)
            self._validate_unregistered_worktree(change_id, recovery_reviewed_head, branch_head)

            last_reviewed_commit = recovery_reviewed_head
        if not self._worktree_present(worktree):
            self._register_worktree(worktree, branch, self._git)
        self._require_worktree(change_id, worktree, branch, branch_head)
        coordination = ChangeCoordination(
            change_id=change_id,
            branch=branch,
            worktree_path=worktree,
            integration_target=self._integration_target,
            target_head=target_head,
            last_reviewed_commit=last_reviewed_commit,
        )
        return self._coordinator.register(coordination)

    def recover(self, change_id: str, recovery_reviewed_head: str) -> ChangeCoordination:
        """Recreate one absent managed Change worktree from exact reviewed authority."""
        if not _is_change_id(change_id):
            msg = "change identity is not a safe worktree identity"
            raise ValueError(msg)
        if re.fullmatch(r"[0-9a-f]{40}", recovery_reviewed_head) is None:
            msg = "recovery reviewed head is not a valid commit identity"
            raise ValueError(msg)
        try:
            existing = self._coordinator.show(change_id)
        except CoordinationConflictError:
            existing = None
        expected_branch = f"owlbear/change/{change_id}"
        expected_path = self._worktree_root / change_id
        branch = expected_branch
        if existing is not None:
            self._validate_existing_coordination(existing, recovery_reviewed_head)
            self._require_recovery_authority(existing)
            expected_path = self._canonical_worktree_path(change_id, existing.worktree_path)
            branch = existing.branch
            if branch != expected_branch:
                self._raise_worktree_attention(change_id, {ChangeWorktreeAttentionCode.BRANCH_MISMATCH})
        branch_head = self._resolve(branch, missing_ok=True)
        if branch_head is None:
            self._raise_worktree_attention(change_id, {ChangeWorktreeAttentionCode.BRANCH_MISSING})
        self._require_ancestor(recovery_reviewed_head, branch_head)
        registrations = self._registered_worktrees_all()
        self._raise_worktree_attention(
            change_id,
            self._recovery_attention(expected_path, expected_branch, registrations, branch_head),
        )
        if not expected_path.exists():
            registered = registrations.get(expected_path)
            if registered is not None:
                self.remove_worktree(self._repository, expected_path)
                registrations = self._registered_worktrees_all()
                if expected_path in registrations or any(
                    record.branch == expected_branch for record in registrations.values()
                ):
                    self._raise_worktree_attention(
                        change_id,
                        {ChangeWorktreeAttentionCode.OWNERSHIP_AMBIGUOUS},
                    )
            self.restore_worktree(self._repository, expected_path, expected_branch)
        return self.ensure(change_id, recovery_reviewed_head=recovery_reviewed_head)

    def _validate_existing_coordination(
        self,
        coordination: ChangeCoordination,
        recovery_reviewed_head: str | None,
    ) -> None:
        if coordination.integration_target != self._integration_target:
            _workspace_failure("registered workspace uses another integration target")
        if coordination.worktree_cleanup is not None:
            _coordination_conflict("Change worktree has already been cleaned up")
        if recovery_reviewed_head is not None and recovery_reviewed_head != coordination.last_reviewed_commit:
            _coordination_conflict("recovery reviewed head differs from registered workspace authority")

    def validate_recovery(self, change_id: str, recovery_reviewed_head: str | None) -> None:
        """Require exact reviewed authority when coordination is missing for a surviving branch."""
        if not _is_change_id(change_id):
            msg = "change identity is not a safe worktree identity"
            raise ValueError(msg)
        try:
            existing = self._coordinator.show(change_id)
        except CoordinationConflictError:
            existing = None
        if existing is not None:
            if recovery_reviewed_head is not None and recovery_reviewed_head != existing.last_reviewed_commit:
                _coordination_conflict("recovery reviewed head differs from registered workspace authority")
            self._validate_existing_worktree(existing)
            return
        branch = f"owlbear/change/{change_id}"
        branch_head = self._resolve(branch, missing_ok=True)
        if branch_head is None:
            if recovery_reviewed_head is not None:
                _coordination_conflict("recovery reviewed head requires an existing Change branch")
            self._validate_unregistered_worktree(change_id, recovery_reviewed_head, branch_head)
            return
        if recovery_reviewed_head is None:
            _coordination_conflict("existing Change branch requires an exact recovery reviewed head")
        self._require_ancestor(recovery_reviewed_head, branch_head)
        self._validate_unregistered_worktree(change_id, recovery_reviewed_head, branch_head)

    def record_reviewed(self, change_id: str, commit: str) -> ChangeCoordination:
        """Advance the recorded reviewed boundary to an exact branch ancestor."""
        coordination = self._coordinator.show(change_id)
        self._require_ancestor(coordination.last_reviewed_commit, commit)
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
    def remove_worktree(cls, repository: Path, worktree: Path, *, force: bool = False) -> None:
        """Remove one managed worktree through Git's registration-aware operation."""
        arguments = ["worktree", "remove"]
        if force:
            arguments.append("--force")
        arguments.append(str(worktree))
        cls._run_managed_git(repository.resolve(), *arguments)

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
        change_ids = set(coordinations) | set(registered) | set(branch_heads) | filesystem_ids
        cleaned = {
            change_id
            for change_id, coordination in coordinations.items()
            if coordination.worktree_cleanup is not None
            and change_id not in registered
            and change_id not in filesystem_ids
        }
        change_ids = sorted(change_ids - cleaned)
        return tuple(
            self._retained_worktree(
                change_id,
                coordinations.get(change_id),
                registered.get(change_id),
                branch_heads.get(change_id),
                include_content_attention=True,
            )
            for change_id in change_ids
        )

    def cleanup(self, change_id: str) -> ChangeWorktreeCleanup:
        """Remove one exact managed Change worktree while retaining its branch and receipt."""
        coordination = self._coordinator.show(change_id)
        if coordination.worktree_cleanup is not None:
            return coordination.worktree_cleanup
        expected_path = self._worktree_root / change_id
        intent = coordination.worktree_cleanup_intent
        if intent is None:
            attention = self._cleanup_attention(change_id, coordination, expected_path)
            self._raise_worktree_attention(change_id, attention)
            self._require_cleanup_authority(coordination)
            branch_head = self._resolve(coordination.branch)
            intent = ChangeWorktreeCleanupIntent.create(
                change_id=change_id,
                branch=coordination.branch,
                worktree_path=expected_path,
                branch_head=branch_head,
            )
            coordination = self._coordinator.update(coordination.model_copy(update={"worktree_cleanup_intent": intent}))
        else:
            self._raise_worktree_attention(
                change_id,
                self._cleanup_intent_attention(change_id, coordination, expected_path, intent),
            )
            self._require_cleanup_authority(coordination)
            branch_head = self._resolve(coordination.branch, missing_ok=True)
            if branch_head is None:
                self._raise_worktree_attention(
                    change_id,
                    {ChangeWorktreeAttentionCode.BRANCH_MISSING},
                )
            if branch_head != intent.branch_head:
                self._raise_worktree_attention(
                    change_id,
                    {ChangeWorktreeAttentionCode.WORKTREE_HEAD_MISMATCH},
                )
            registrations = self._registered_worktrees_all()
            if self._cleanup_replay_complete(expected_path, intent.branch, registrations):
                return self._record_cleanup_receipt(coordination, intent)

        self._raise_worktree_attention(
            change_id,
            self._cleanup_attention(change_id, coordination, expected_path),
        )
        self.remove_worktree(self._repository, expected_path)
        registrations = self._registered_worktrees_all()
        if not self._cleanup_replay_complete(expected_path, intent.branch, registrations):
            attention = {ChangeWorktreeAttentionCode.UNEXPECTED_FILESYSTEM_STATE}
            if any(record.branch == intent.branch for record in registrations.values()):
                attention.add(ChangeWorktreeAttentionCode.OWNERSHIP_AMBIGUOUS)
            self._raise_worktree_attention(change_id, attention)
        return self._record_cleanup_receipt(coordination, intent)

    @staticmethod
    def _require_cleanup_authority(coordination: ChangeCoordination) -> None:
        if coordination.writer is not None:
            _coordination_conflict("Change worktree cleanup cannot overlap an active writer")
        if coordination.publication_expiry is not None and coordination.publication_expiry > datetime.now(UTC):
            _coordination_conflict("Change worktree cleanup cannot overlap an active publication lease")

    @staticmethod
    def _require_recovery_authority(coordination: ChangeCoordination) -> None:
        if coordination.writer is not None:
            _coordination_conflict("Change worktree recovery cannot overlap an active writer")
        if coordination.publication_expiry is not None and coordination.publication_expiry > datetime.now(UTC):
            _coordination_conflict("Change worktree recovery cannot overlap an active publication lease")

    def _cleanup_intent_attention(
        self,
        change_id: str,
        coordination: ChangeCoordination,
        expected_path: Path,
        intent: ChangeWorktreeCleanupIntent,
    ) -> set[ChangeWorktreeAttentionCode]:
        attention: set[ChangeWorktreeAttentionCode] = set()
        if intent.change_id != change_id:
            attention.add(ChangeWorktreeAttentionCode.OWNERSHIP_AMBIGUOUS)
        if intent.branch != coordination.branch:
            attention.add(ChangeWorktreeAttentionCode.BRANCH_MISMATCH)
        if intent.worktree_path.resolve() != expected_path.resolve():
            attention.add(ChangeWorktreeAttentionCode.COORDINATION_PATH_MISMATCH)
        return attention

    @staticmethod
    def _recovery_attention(
        expected_path: Path,
        expected_branch: str,
        registrations: dict[Path, _RegisteredGitWorktree],
        branch_head: str,
    ) -> set[ChangeWorktreeAttentionCode]:
        attention: set[ChangeWorktreeAttentionCode] = set()
        if expected_path.is_symlink() or (expected_path.exists() and not expected_path.is_dir()):
            attention.add(ChangeWorktreeAttentionCode.UNEXPECTED_FILESYSTEM_STATE)
        path_record = registrations.get(expected_path)
        branch_records = [record for record in registrations.values() if record.branch == expected_branch]
        if len(branch_records) > 1 or (branch_records and branch_records[0] is not path_record):
            attention.add(ChangeWorktreeAttentionCode.OWNERSHIP_AMBIGUOUS)
        if expected_path.exists() and path_record is None:
            attention.add(ChangeWorktreeAttentionCode.GIT_REGISTRATION_MISSING)
        if path_record is not None:
            registered_attention = ChangeWorkspaceManager._cleanup_registered_record_attention(
                path_record,
                expected_branch,
                branch_head,
            )
            if not expected_path.exists():
                registered_attention.discard(ChangeWorktreeAttentionCode.PRUNABLE)
            attention.update(registered_attention)
        return attention

    @staticmethod
    def _cleanup_replay_complete(
        expected_path: Path,
        expected_branch: str,
        registrations: dict[Path, _RegisteredGitWorktree],
    ) -> bool:
        if expected_path.is_symlink() or expected_path.exists() or expected_path in registrations:
            return False
        return not any(record.branch == expected_branch for record in registrations.values())

    def _record_cleanup_receipt(
        self,
        coordination: ChangeCoordination,
        intent: ChangeWorktreeCleanupIntent,
    ) -> ChangeWorktreeCleanup:
        receipt = ChangeWorktreeCleanup.create(
            change_id=intent.change_id,
            branch=intent.branch,
            worktree_path=intent.worktree_path,
            branch_head=intent.branch_head,
        )
        self._coordinator.update(
            coordination.model_copy(
                update={
                    "worktree_cleanup_intent": None,
                    "worktree_cleanup": receipt,
                }
            )
        )
        return receipt

    def refresh_integration_target(self, change_id: str) -> ChangeCoordination:
        """Persist the current target head at an operational Git boundary."""
        coordination = self._coordinator.show(change_id)
        target_head = self._resolve(self._target_ref())
        if target_head == coordination.target_head:
            return coordination
        return self._coordinator.update(coordination.model_copy(update={"target_head": target_head}))

    def _replay_target_sync_receipt(
        self,
        request: SyncChangeWithTarget,
        coordination: ChangeCoordination,
    ) -> ChangeTargetSyncReceipt | None:
        receipt = coordination.target_sync_receipt
        if receipt is None or receipt.operation_id != request.operation_id:
            return None
        if (
            receipt.expected_target != request.expected_target
            or coordination.last_reviewed_commit != receipt.merged_head
        ):
            _coordination_conflict("target synchronization operation inputs differ from its receipt")
        self._require_worktree(
            request.change_id,
            coordination.worktree_path,
            coordination.branch,
            receipt.merged_head,
        )
        return receipt

    def _persist_target_sync_conflict(
        self,
        request: SyncChangeWithTarget,
        coordination: ChangeCoordination,
        lock: PublicationLock,
        target_head: str,
        change_head_before: str,
    ) -> Never:
        conflict = ChangeTargetSyncConflictState.create(
            operation_id=request.operation_id,
            change_id=request.change_id,
            target_head=target_head,
            change_head_before=change_head_before,
            conflict_paths=self._unmerged_paths(coordination.worktree_path),
        )
        self._coordinator.update(
            coordination.model_copy(update={"target_sync_conflict": conflict}),
            lock=lock,
        )
        raise ChangeTargetSyncConflictError(
            request.change_id,
            request.operation_id,
            target_head,
            conflict.conflict_paths,
        )

    def _require_target_sync_start(
        self,
        request: SyncChangeWithTarget,
        coordination: ChangeCoordination,
    ) -> None:
        conflict = coordination.target_sync_conflict
        if conflict is not None:
            if conflict.operation_id != request.operation_id or conflict.target_head != request.expected_target:
                _coordination_conflict("target synchronization conflict identity differs from the request")
            raise ChangeTargetSyncConflictError(
                request.change_id,
                conflict.operation_id,
                conflict.target_head,
                conflict.conflict_paths,
            )
        if (
            coordination.target_sync_abort_receipt is not None
            and coordination.target_sync_abort_receipt.operation_id == request.operation_id
        ):
            _coordination_conflict("target synchronization operation was explicitly aborted")
        if coordination.writer is not None:
            _coordination_conflict("target synchronization cannot overlap an active writer")
        if coordination.publication_lease is not None:
            _coordination_conflict("target synchronization cannot overlap a publication lease")
        branch_head = self._resolve(coordination.branch)
        if branch_head != coordination.last_reviewed_commit:
            _coordination_conflict("target synchronization requires the reviewed Change head")

    def sync_with_target(self, request: SyncChangeWithTarget) -> ChangeTargetSyncReceipt:
        """Fetch one exact target head and merge it only in the managed Change worktree."""
        with self._coordinator.publication_lock(request.change_id) as lock:
            coordination = self._coordinator.show(request.change_id)
            previous_receipt = self._replay_target_sync_receipt(request, coordination)
            if previous_receipt is not None:
                return previous_receipt
            self._require_target_sync_start(request, coordination)
            branch_head = self._resolve(coordination.branch)
            self._require_worktree(
                request.change_id,
                coordination.worktree_path,
                coordination.branch,
                branch_head,
            )
            merge_head = self._resolve("MERGE_HEAD", cwd=coordination.worktree_path, missing_ok=True)
            if merge_head is not None:
                if merge_head != request.expected_target:
                    _coordination_conflict("preserved target synchronization conflict target differs from the request")
                self._persist_target_sync_conflict(request, coordination, lock, merge_head, branch_head)
            if self._git(
                "--no-optional-locks",
                "status",
                "--porcelain=v1",
                "-z",
                "--untracked-files=all",
                cwd=coordination.worktree_path,
            ):
                _workspace_failure("target synchronization requires a clean Change worktree")
            source_ref, target_ref, target_branch = self._target_refs()
            target_head = self._fetch_target(source_ref, target_branch, request.expected_target)
            branch_head = self._resolve(coordination.branch)
            self._require_worktree(
                request.change_id,
                coordination.worktree_path,
                coordination.branch,
                branch_head,
            )
            merge = self._run_git(
                "merge",
                "--no-edit",
                "--",
                target_ref,
                cwd=coordination.worktree_path,
                check=False,
            )
            if merge.returncode != 0:
                merge_head = self._resolve("MERGE_HEAD", cwd=coordination.worktree_path, missing_ok=True)
                if merge_head is not None:
                    self._persist_target_sync_conflict(request, coordination, lock, merge_head, branch_head)
                _workspace_failure("target synchronization merge failed")
            merged_head = self._resolve(coordination.branch)
            receipt = ChangeTargetSyncReceipt.create(
                operation_id=request.operation_id,
                change_id=request.change_id,
                integration_target=coordination.integration_target,
                expected_target=request.expected_target,
                target_head=target_head,
                change_head_before=branch_head,
                merged_head=merged_head,
                merge_commit=self._is_merge_commit(merged_head, coordination.worktree_path),
            )
            self._coordinator.update(
                coordination.model_copy(
                    update={
                        "target_head": target_head,
                        "target_sync_conflict": None,
                        "target_sync_receipt": receipt,
                        "target_sync_abort_receipt": None,
                        "last_reviewed_commit": merged_head,
                    }
                ),
                lock=lock,
            )
            return receipt

    def adopt_external_head(self, request: AdoptExternalHead) -> ChangeExternalHeadAdoptionReceipt:
        """Adopt one exact descendant from the remote Change branch without advancing review authority."""
        with self._coordinator.publication_lock(request.change_id) as lock:
            coordination = self._coordinator.show(request.change_id)
            replayed = self._replay_external_head_adoption(request, coordination)
            if replayed is not None:
                return replayed
            coordination = self._prepare_external_head_adoption(request, coordination)

            branch_head = self._resolve(coordination.branch)
            if branch_head == request.adopted_head:
                self._require_ancestor(request.expected_head, branch_head)
                self._require_worktree(
                    request.change_id,
                    coordination.worktree_path,
                    coordination.branch,
                    branch_head,
                )
                self._require_clean_worktree(coordination.worktree_path)
                return self._complete_external_head_adoption(request, coordination, lock)
            if branch_head != request.expected_head:
                _coordination_conflict("Change branch head differs from the adoption request")
            return self._fast_forward_external_head(request, coordination, lock)

    def _prepare_external_head_adoption(
        self,
        request: AdoptExternalHead,
        coordination: ChangeCoordination,
    ) -> ChangeCoordination:
        self._require_external_head_adoption_start(coordination)
        intent = coordination.external_head_adoption_intent
        expected_intent = ChangeExternalHeadAdoptionIntent.create(request, coordination.branch)
        if intent is not None:
            if intent != expected_intent:
                _coordination_conflict("external Change head adoption intent differs from the request")
            return coordination
        branch_head = self._resolve(coordination.branch)
        if branch_head != request.expected_head:
            _coordination_conflict("Change branch head differs from the adoption request")
        if request.expected_head != coordination.last_reviewed_commit:
            _coordination_conflict("external Change head adoption requires the reviewed branch head")
        self._require_ancestor(coordination.last_reviewed_commit, request.expected_head)
        self._require_worktree(
            request.change_id,
            coordination.worktree_path,
            coordination.branch,
            request.expected_head,
        )
        self._require_clean_worktree(coordination.worktree_path)
        return coordination

    def _fast_forward_external_head(
        self,
        request: AdoptExternalHead,
        coordination: ChangeCoordination,
        lock: PublicationLock,
    ) -> ChangeExternalHeadAdoptionReceipt:
        remote_ref = self._fetch_external_head(coordination.branch, request.adopted_head)
        if not self._is_ancestor(request.expected_head, request.adopted_head, cwd=self._repository):
            _workspace_failure("adopted Change head is not a descendant of the expected head")
        intent = coordination.external_head_adoption_intent
        if intent is None:
            intent = ChangeExternalHeadAdoptionIntent.create(request, coordination.branch)
            coordination = self._coordinator.update(
                coordination.model_copy(update={"external_head_adoption_intent": intent}),
                lock=lock,
            )
        merge = self._run_git(
            "merge",
            "--ff-only",
            "--",
            remote_ref,
            cwd=coordination.worktree_path,
            check=False,
        )
        if merge.returncode != 0:
            _workspace_failure("external Change head could not be adopted with a fast-forward")
        adopted_head = self._resolve(coordination.branch)
        if adopted_head != request.adopted_head:
            _workspace_failure("adopted Change worktree head differs from the requested head")
        self._require_worktree(
            request.change_id,
            coordination.worktree_path,
            coordination.branch,
            adopted_head,
        )
        self._require_clean_worktree(coordination.worktree_path)
        return self._complete_external_head_adoption(request, coordination, lock, adopted_head)

    def _complete_external_head_adoption(
        self,
        request: AdoptExternalHead,
        coordination: ChangeCoordination,
        lock: PublicationLock,
        adopted_head: str | None = None,
    ) -> ChangeExternalHeadAdoptionReceipt:
        receipt = ChangeExternalHeadAdoptionReceipt.create(
            operation_id=request.operation_id,
            change_id=request.change_id,
            branch=coordination.branch,
            expected_head=request.expected_head,
            adopted_head=adopted_head or request.adopted_head,
        )
        history = coordination.external_head_adoption_receipts
        if receipt.operation_id not in {item.operation_id for item in history}:
            history = (*history, receipt)
        self._coordinator.update(
            coordination.model_copy(
                update={
                    "external_head_adoption_intent": None,
                    "external_head_adoption_receipt": receipt,
                    "external_head_adoption_receipts": history,
                    "external_head_promotion_receipt": None,
                }
            ),
            lock=lock,
        )
        return receipt

    def _replay_external_head_adoption(
        self,
        request: AdoptExternalHead,
        coordination: ChangeCoordination,
    ) -> ChangeExternalHeadAdoptionReceipt | None:
        receipt = self._external_head_adoption_receipt(coordination, request.operation_id)
        if receipt is None:
            return None
        if (
            receipt.expected_head != request.expected_head
            or receipt.adopted_head != request.adopted_head
            or receipt.branch != coordination.branch
        ):
            _coordination_conflict("external Change head adoption inputs differ from its receipt")
        self._require_worktree(
            request.change_id,
            coordination.worktree_path,
            coordination.branch,
            receipt.adopted_head,
        )
        self._require_clean_worktree(coordination.worktree_path)
        return receipt

    @staticmethod
    def _external_head_adoption_receipt(
        coordination: ChangeCoordination,
        operation_id: str,
    ) -> ChangeExternalHeadAdoptionReceipt | None:
        receipts = coordination.external_head_adoption_receipts
        current = coordination.external_head_adoption_receipt
        if current is not None and current.operation_id not in {receipt.operation_id for receipt in receipts}:
            receipts = (*receipts, current)
        return next((receipt for receipt in receipts if receipt.operation_id == operation_id), None)

    def _require_external_head_adoption_start(self, coordination: ChangeCoordination) -> None:
        if coordination.writer is not None:
            _coordination_conflict("external Change head adoption cannot overlap an active writer")
        if coordination.publication_lease is not None:
            _coordination_conflict("external Change head adoption cannot overlap a publication lease")
        if coordination.worktree_cleanup_intent is not None or coordination.worktree_cleanup is not None:
            _coordination_conflict("external Change head adoption cannot overlap worktree cleanup")
        if coordination.target_sync_conflict is not None:
            _coordination_conflict("external Change head adoption cannot overlap a target synchronization conflict")
        if coordination.external_head_adoption_intent is None:
            branch_head = self._resolve(coordination.branch)
            if branch_head != coordination.last_reviewed_commit:
                _coordination_conflict("external Change head adoption requires the reviewed branch head")

    def _fetch_external_head(self, branch: str, expected_head: str) -> str:
        source_ref = f"refs/heads/{branch}"
        remote_ref = f"refs/remotes/{self._remote}/{branch}"
        self._git("check-ref-format", source_ref)
        self._git("check-ref-format", remote_ref)
        result = self._run_git(
            "fetch",
            "--no-tags",
            "--no-write-fetch-head",
            "--refmap=",
            self._remote,
            f"{source_ref}:{remote_ref}",
            check=False,
        )
        if result.returncode != 0:
            _workspace_failure("remote Change branch could not be fetched into its remote-tracking ref")
        adopted_head = self._resolve(remote_ref, missing_ok=True)
        if adopted_head is None:
            _workspace_failure("fetched remote Change branch is unavailable")
        if adopted_head != expected_head:
            _coordination_conflict("remote Change branch differs from the adoption request")
        return remote_ref

    def _replay_target_sync_abort(
        self,
        request: TargetSyncConflictRequest,
        coordination: ChangeCoordination,
    ) -> ChangeTargetSyncAbortReceipt | None:
        receipt = coordination.target_sync_abort_receipt
        if receipt is None or receipt.operation_id != request.operation_id:
            return None
        if receipt.target_head != request.target_head:
            _coordination_conflict("target synchronization abort inputs differ from its receipt")
        self._require_worktree(
            request.change_id,
            coordination.worktree_path,
            coordination.branch,
            receipt.restored_head,
        )
        self._require_clean_worktree(coordination.worktree_path)
        if self._resolve("MERGE_HEAD", cwd=coordination.worktree_path, missing_ok=True) is not None:
            _workspace_failure("target synchronization abort receipt has unresolved merge state")
        return receipt

    def _require_target_sync_exit_custody(self, coordination: ChangeCoordination, operation: str) -> None:
        if coordination.writer is not None:
            _coordination_conflict(f"target synchronization {operation} cannot overlap an active writer")
        if coordination.publication_lease is not None:
            _coordination_conflict(f"target synchronization {operation} cannot overlap a publication lease")

    def _require_target_sync_conflict(
        self,
        coordination: ChangeCoordination,
        request: TargetSyncConflictRequest,
    ) -> ChangeTargetSyncConflictState:
        conflict = coordination.target_sync_conflict
        if conflict is None:
            _coordination_conflict("target synchronization has no preserved conflict for this exit")
        if conflict.operation_id != request.operation_id or conflict.target_head != request.target_head:
            _coordination_conflict("target synchronization conflict identity differs from the request")
        return conflict

    def _abort_preserved_target_merge(self, worktree: Path, target_head: str) -> None:
        merge_head = self._resolve("MERGE_HEAD", cwd=worktree, missing_ok=True)
        if merge_head is None:
            return
        if merge_head != target_head:
            _coordination_conflict("target synchronization conflict target differs from the request")
        result = self._run_git("merge", "--abort", cwd=worktree, check=False)
        if result.returncode != 0:
            _workspace_failure("target synchronization conflict could not be aborted")

    def abort_target_sync_conflict(
        self,
        request: TargetSyncConflictRequest,
    ) -> ChangeTargetSyncAbortReceipt:
        """Abort one exact preserved target merge and restore the reviewed boundary."""
        with self._coordinator.publication_lock(request.change_id) as lock:
            coordination = self._coordinator.show(request.change_id)
            replayed = self._replay_target_sync_abort(request, coordination)
            if replayed is not None:
                return replayed
            if coordination.target_sync_receipt is not None:
                _coordination_conflict("target synchronization already has completed receipt evidence")
            self._require_target_sync_exit_custody(coordination, "abort")
            conflict = self._require_target_sync_conflict(coordination, request)
            restored_head = conflict.change_head_before
            if restored_head != coordination.last_reviewed_commit:
                _workspace_failure("target synchronization conflict is outside the reviewed boundary")
            if self._resolve(coordination.branch) != restored_head:
                _workspace_failure("target synchronization conflict branch moved outside the reviewed boundary")
            self._require_worktree(
                request.change_id,
                coordination.worktree_path,
                coordination.branch,
                restored_head,
            )
            self._abort_preserved_target_merge(coordination.worktree_path, request.target_head)
            self._require_worktree(
                request.change_id,
                coordination.worktree_path,
                coordination.branch,
                restored_head,
            )
            self._require_clean_worktree(coordination.worktree_path)
            if self._resolve("MERGE_HEAD", cwd=coordination.worktree_path, missing_ok=True) is not None:
                _workspace_failure("target synchronization conflict remains active after abort")
            receipt = ChangeTargetSyncAbortReceipt.create(
                operation_id=request.operation_id,
                change_id=request.change_id,
                target_head=request.target_head,
                restored_head=restored_head,
            )
            self._coordinator.update(
                coordination.model_copy(
                    update={
                        "target_sync_conflict": None,
                        "target_sync_abort_receipt": receipt,
                    }
                ),
                lock=lock,
            )
            return receipt

    def _replay_target_sync_resolution(
        self,
        request: TargetSyncConflictRequest,
        coordination: ChangeCoordination,
    ) -> ChangeTargetSyncReceipt | None:
        receipt = coordination.target_sync_receipt
        if receipt is None or receipt.operation_id != request.operation_id:
            return None
        if receipt.target_head != request.target_head:
            _coordination_conflict("target synchronization resolution inputs differ from its receipt")
        self._require_worktree(
            request.change_id,
            coordination.worktree_path,
            coordination.branch,
            receipt.merged_head,
        )
        self._require_clean_worktree(coordination.worktree_path)
        return receipt

    def _commit_target_sync_resolution(
        self,
        request: TargetSyncConflictRequest,
        coordination: ChangeCoordination,
        conflict: ChangeTargetSyncConflictState,
    ) -> str:
        worktree = coordination.worktree_path
        merge_head = self._resolve("MERGE_HEAD", cwd=worktree, missing_ok=True)
        if merge_head is not None:
            if merge_head != request.target_head:
                _coordination_conflict("target synchronization conflict target differs from the request")
            self._require_worktree(
                request.change_id,
                worktree,
                coordination.branch,
                conflict.change_head_before,
            )
            if self._unmerged_paths(worktree):
                _workspace_failure("target synchronization conflict still has unresolved paths")
            self._require_no_unstaged_changes(worktree)
            result = self._run_git("commit", "--no-edit", cwd=worktree, check=False)
            if result.returncode != 0:
                _workspace_failure("target synchronization conflict could not be committed")
        elif self._resolve(coordination.branch) == conflict.change_head_before:
            _workspace_failure("target synchronization conflict has not been resolved")
        return self._resolve(coordination.branch)

    def resolve_target_sync_conflict(
        self,
        request: TargetSyncConflictRequest,
    ) -> ChangeTargetSyncReceipt:
        """Commit or validate one exact semantic conflict resolution."""
        with self._coordinator.publication_lock(request.change_id) as lock:
            coordination = self._coordinator.show(request.change_id)
            replayed = self._replay_target_sync_resolution(request, coordination)
            if replayed is not None:
                return replayed
            if coordination.target_sync_abort_receipt is not None:
                _coordination_conflict("target synchronization conflict was already aborted")
            self._require_target_sync_exit_custody(coordination, "resolution")
            conflict = self._require_target_sync_conflict(coordination, request)
            change_head_before = conflict.change_head_before
            if change_head_before != coordination.last_reviewed_commit:
                _workspace_failure("target synchronization conflict is outside the reviewed boundary")
            merged_head = self._commit_target_sync_resolution(request, coordination, conflict)
            self._require_worktree(
                request.change_id,
                coordination.worktree_path,
                coordination.branch,
                merged_head,
            )
            self._require_clean_worktree(coordination.worktree_path)
            if self._resolve("MERGE_HEAD", cwd=coordination.worktree_path, missing_ok=True) is not None:
                _workspace_failure("target synchronization conflict remains active after resolution")
            parents = self._git("rev-list", "--parents", "-n", "1", merged_head, cwd=coordination.worktree_path).split()
            if parents[1:] != [change_head_before, request.target_head]:
                _workspace_failure("target synchronization resolution is not an exact merge of the requested heads")
            receipt = ChangeTargetSyncReceipt.create(
                operation_id=request.operation_id,
                change_id=request.change_id,
                integration_target=coordination.integration_target,
                expected_target=request.target_head,
                target_head=request.target_head,
                change_head_before=change_head_before,
                merged_head=merged_head,
                merge_commit=True,
            )
            self._coordinator.update(
                coordination.model_copy(
                    update={
                        "target_head": request.target_head,
                        "target_sync_conflict": None,
                        "target_sync_receipt": receipt,
                        "target_sync_abort_receipt": None,
                        "last_reviewed_commit": merged_head,
                    }
                ),
                lock=lock,
            )
            return receipt

    def integration_context(self, change_id: str) -> IntegrationContext:
        """Return exact source and target heads without mutating either reference."""
        coordination = self._coordinator.show(change_id)
        return IntegrationContext(
            change_id=coordination.change_id,
            change_head=self._resolve(coordination.branch),
            reviewed_change_head=coordination.last_reviewed_commit,
            integration_target=coordination.integration_target,
            target_head=self._resolve(self._target_ref()),
        )

    def _target_refs(self) -> tuple[str, str, str]:
        target_ref = self._target_ref()
        remote_prefix = f"refs/remotes/{self._remote}/"
        if not target_ref.startswith(remote_prefix):
            _workspace_failure("configured target ref does not belong to the configured remote")
        target_branch = target_ref.removeprefix(remote_prefix)
        source_ref = f"refs/heads/{target_branch}"
        self._git("check-ref-format", source_ref)
        return source_ref, target_ref, target_branch

    def _fetch_target(self, source_ref: str, target_branch: str, expected_target: str) -> str:
        remote_target_ref = f"refs/remotes/{self._remote}/{target_branch}"
        result = self._run_git(
            "fetch",
            "--no-tags",
            "--no-write-fetch-head",
            "--refmap=",
            self._remote,
            f"{source_ref}:{remote_target_ref}",
            check=False,
        )
        if result.returncode != 0:
            _workspace_failure("configured target could not be fetched into its remote-tracking ref")
        target_head = self._resolve(remote_target_ref, missing_ok=True)
        if target_head is None:
            _workspace_failure("fetched target remote-tracking ref is unavailable")
        if target_head != expected_target:
            _coordination_conflict("target changed while it was fetched")
        return target_head

    def _unmerged_paths(self, worktree: Path) -> tuple[str, ...]:
        result = self._run_git(
            "diff",
            "--name-only",
            "--diff-filter=U",
            "-z",
            cwd=worktree,
            check=False,
        )
        if result.returncode != 0:
            return ()
        return tuple(os.fsdecode(path) for path in result.stdout.split(b"\0") if path)

    def _require_clean_worktree(self, worktree: Path) -> None:
        if self._git("-C", str(worktree), "status", "--porcelain=v1").strip():
            _workspace_failure("target synchronization worktree is not clean")

    def _require_no_unstaged_changes(self, worktree: Path) -> None:
        status = self._git("-C", str(worktree), "status", "--porcelain=v1")
        if any(
            line.startswith("??")
            or (len(line) > _PORCELAIN_WORKTREE_STATUS_INDEX and line[_PORCELAIN_WORKTREE_STATUS_INDEX] != " ")
            for line in status.splitlines()
        ):
            _workspace_failure("target synchronization resolution has unstaged or untracked changes")

    def _is_merge_commit(self, commit: str, worktree: Path) -> bool:
        parents = self._git("rev-list", "--parents", "-n", "1", commit, cwd=worktree).split()
        return len(parents) > _MERGE_COMMIT_MIN_PARENTS

    def reviewed_source_head(self, change_id: str) -> str:
        """Return one clean warm source head anchored at its reviewed boundary."""
        coordination = self._coordinator.show(change_id)
        branch_head = self._resolve(coordination.branch)
        if branch_head != coordination.last_reviewed_commit:
            _workspace_failure("change branch differs from its reviewed source boundary")
        self._require_worktree(change_id, coordination.worktree_path, coordination.branch, branch_head)
        if self._git("-C", str(coordination.worktree_path), "status", "--porcelain"):
            _workspace_failure("change source worktree is not clean")
        return branch_head

    def source_head(self, change_id: str) -> str:
        """Return one clean source head at the reviewed or durably adopted boundary."""
        coordination = self._coordinator.show(change_id)
        if coordination.external_head_adoption_intent is not None:
            _coordination_conflict("external Change head adoption requires operation replay")
        branch_head = self._resolve(coordination.branch)
        if branch_head != coordination.last_reviewed_commit:
            receipt = coordination.external_head_adoption_receipt
            if receipt is None or receipt.adopted_head != branch_head:
                _workspace_failure("change branch differs from its reviewed source boundary")
            self._require_ancestor(coordination.last_reviewed_commit, branch_head)
        self._require_worktree(
            change_id,
            coordination.worktree_path,
            coordination.branch,
            branch_head,
        )
        if self._git("-C", str(coordination.worktree_path), "status", "--porcelain"):
            _workspace_failure("change source worktree is not clean")
        return branch_head

    def promote_external_head(
        self,
        request: PromoteExternalHead,
        *,
        provenance: Literal["explicit", "finalization"] = "explicit",
    ) -> ChangeExternalHeadPromotionReceipt | None:
        """Grant review authority to one exact adopted head and retain its receipt."""
        with self._coordinator.publication_lock(request.change_id) as lock:
            coordination = self._coordinator.show(request.change_id)
            if coordination.external_head_adoption_intent is not None:
                _coordination_conflict("external Change head adoption requires operation replay")
            replayed = self._replay_external_head_promotion(request, coordination)
            if replayed is not None:
                return replayed
            if coordination.writer is not None:
                _coordination_conflict("external Change head promotion cannot overlap an active writer")
            current_promotion = coordination.external_head_promotion_receipt
            handled, finalization_promotion = self._reconcile_finalization_promotion(
                request,
                coordination,
                provenance,
                current_promotion,
            )
            if handled:
                return finalization_promotion
            adoption = coordination.external_head_adoption_receipt
            if adoption is None:
                if (
                    provenance == "finalization"
                    and coordination.last_reviewed_commit == request.expected_head
                    and self._resolve(coordination.branch) == request.expected_head
                ):
                    return None
                _coordination_conflict("exact head is not an adopted external Change head")
            if adoption.adopted_head != request.expected_head:
                _coordination_conflict("exact head is not the current adopted Change head")
            branch_head = self._resolve(coordination.branch)
            if branch_head != request.expected_head:
                _workspace_failure("adopted Change head differs from the requested reviewed head")
            self._require_ancestor(coordination.last_reviewed_commit, request.expected_head)
            self._require_worktree(
                request.change_id,
                coordination.worktree_path,
                coordination.branch,
                request.expected_head,
            )
            self._require_clean_worktree(coordination.worktree_path)
            if any(
                item.promoted_head == request.expected_head for item in coordination.external_head_promotion_receipts
            ):
                _coordination_conflict("exact adopted Change head was already promoted by another operation")
            receipt = ChangeExternalHeadPromotionReceipt.create(
                operation_id=request.operation_id,
                change_id=request.change_id,
                branch=coordination.branch,
                adoption_receipt_id=adoption.receipt_id,
                promoted_head=request.expected_head,
                provenance=provenance,
            )
            history = coordination.external_head_promotion_receipts
            self._coordinator.update(
                coordination.model_copy(
                    update={
                        "last_reviewed_commit": request.expected_head,
                        "external_head_promotion_receipt": receipt,
                        "external_head_promotion_receipts": (*history, receipt),
                    }
                ),
                lock=lock,
            )
            return receipt

    def _reconcile_finalization_promotion(
        self,
        request: PromoteExternalHead,
        coordination: ChangeCoordination,
        provenance: Literal["explicit", "finalization"],
        current_promotion: ChangeExternalHeadPromotionReceipt | None,
    ) -> tuple[bool, ChangeExternalHeadPromotionReceipt | None]:
        if provenance != "finalization" or coordination.last_reviewed_commit != request.expected_head:
            return False, None
        if current_promotion is not None:
            if current_promotion.promoted_head != request.expected_head:
                _coordination_conflict("finalization head differs from existing promotion evidence")
            self._require_worktree(
                request.change_id,
                coordination.worktree_path,
                coordination.branch,
                request.expected_head,
            )
            self._require_clean_worktree(coordination.worktree_path)
            return True, current_promotion
        if self._resolve(coordination.branch) == request.expected_head:
            return True, None
        return False, None

    def _replay_external_head_promotion(
        self,
        request: PromoteExternalHead,
        coordination: ChangeCoordination,
    ) -> ChangeExternalHeadPromotionReceipt | None:
        receipt = next(
            (
                item
                for item in coordination.external_head_promotion_receipts
                if item.operation_id == request.operation_id
            ),
            None,
        )
        if receipt is None:
            return None
        if receipt.promoted_head != request.expected_head or receipt.branch != coordination.branch:
            _coordination_conflict("external Change head promotion inputs differ from its receipt")
        branch_head = self._resolve(coordination.branch)
        self._require_ancestor(receipt.promoted_head, branch_head)
        self._require_worktree(
            request.change_id,
            coordination.worktree_path,
            coordination.branch,
            branch_head,
        )
        self._require_clean_worktree(coordination.worktree_path)
        return receipt

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
        if self.source_head(change_id) != exact_head:
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
        self._require_worktree(change_id, coordination.worktree_path, coordination.branch, commit)
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
        self._reject_unpromoted_adoption_restart(coordination, branch_head)
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
        if not self._worktree_present(worktree):
            self._register_worktree(worktree, coordination.branch, self._git)
        self._require_worktree(
            change_id,
            worktree,
            coordination.branch,
            coordination.last_reviewed_commit,
        )
        return self._coordinator.release(change_id, coordination.writer.claim_id)

    def _reject_unpromoted_adoption_restart(
        self,
        coordination: ChangeCoordination,
        branch_head: str,
    ) -> None:
        receipt = coordination.external_head_adoption_receipt
        if receipt is None or receipt.adopted_head == coordination.last_reviewed_commit:
            return
        if branch_head == coordination.last_reviewed_commit or self._is_ancestor(
            receipt.adopted_head,
            branch_head,
            cwd=self._repository,
        ):
            _coordination_conflict(
                "cannot restart across an unpromoted external Change head; promote the adopted head first"
            )

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
            coordination.change_id,
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
            self._require_worktree(
                coordination.change_id,
                coordination.worktree_path,
                coordination.branch,
                rejected_head,
            )
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

    def _require_worktree(self, change_id: str, worktree: Path, branch: str, expected_head: str) -> None:
        expected_path = self._canonical_worktree_path(change_id, worktree)
        registered = self._registered_worktrees().get(change_id)
        attention = self._registered_attention(registered, branch)
        if not self._worktree_present(expected_path):
            attention.add(ChangeWorktreeAttentionCode.WORKTREE_MISSING)
        self._raise_worktree_attention(change_id, attention)
        if registered is None or registered.head != expected_head:
            _workspace_failure("registered Change worktree head differs from its branch")
        if self._resolve("HEAD", cwd=expected_path) != expected_head:
            _workspace_failure("change worktree head differs from its branch")
        current = self._git("-C", str(expected_path), "branch", "--show-current")
        if current != branch:
            _workspace_failure("change worktree is attached to another branch")

    def _validate_existing_worktree(self, coordination: ChangeCoordination) -> None:
        retained = self._retained_worktree(
            coordination.change_id,
            coordination,
            self._registered_worktrees().get(coordination.change_id),
            self._change_branch_heads().get(coordination.change_id),
        )
        self._raise_worktree_attention(coordination.change_id, set(retained.attention))

    def _validate_unregistered_worktree(
        self,
        change_id: str,
        recovery_reviewed_head: str | None,
        branch_head: str | None,
    ) -> None:
        registered = self._registered_worktrees().get(change_id)
        worktree_present = self._worktree_present(self._worktree_root / change_id)
        retained = self._retained_worktree(change_id, None, registered, branch_head)
        attention = set(retained.attention)
        attention.discard(ChangeWorktreeAttentionCode.COORDINATION_MISSING)
        if branch_head is None and registered is None and not worktree_present:
            return
        self._raise_worktree_attention(change_id, attention)
        if branch_head is None or recovery_reviewed_head is None:
            _coordination_conflict("existing Change worktree requires exact recovery authority")
        self._require_worktree(change_id, self._worktree_root / change_id, f"owlbear/change/{change_id}", branch_head)

    def _canonical_worktree_path(self, change_id: str, worktree: Path) -> Path:
        expected_path = self._worktree_root / change_id
        if worktree.is_symlink() or worktree.resolve() != expected_path.resolve():
            raise ChangeWorktreeAttentionError(
                change_id,
                (ChangeWorktreeAttentionCode.COORDINATION_PATH_MISMATCH,),
            )
        return expected_path

    @staticmethod
    def _raise_worktree_attention(
        change_id: str,
        attention: set[ChangeWorktreeAttentionCode],
    ) -> None:
        if attention:
            ordered = tuple(code for code in ChangeWorktreeAttentionCode if code in attention)
            raise ChangeWorktreeAttentionError(change_id, ordered)

    def _registered_worktrees(self) -> dict[str, _RegisteredGitWorktree]:
        records = {}
        for path, record in self._registered_worktrees_all().items():
            try:
                relative = path.relative_to(self._worktree_root)
            except ValueError:
                continue
            if len(relative.parts) != 1 or not _is_change_id(relative.name):
                continue
            change_id = relative.name
            if change_id in records:
                _workspace_failure(f"multiple Git worktrees are registered for Change {change_id}")
            records[change_id] = record
        return records

    def _registered_worktrees_all(self) -> dict[Path, _RegisteredGitWorktree]:
        completed = self._run_git("worktree", "list", "--porcelain", "-z")
        records: dict[Path, _RegisteredGitWorktree] = {}
        for raw_record in completed.stdout.split(b"\0\0"):
            fields = tuple(field for field in raw_record.split(b"\0") if field)
            values = {field.partition(b" ")[0]: field.partition(b" ")[2] for field in fields}
            raw_path = values.get(b"worktree")
            if raw_path is None:
                continue
            path = Path(os.fsdecode(raw_path)).resolve()
            if path in records:
                _workspace_failure(f"multiple Git worktrees are registered for path {path}")
            records[path] = _RegisteredGitWorktree(
                path=path,
                head=_decode_optional(values.get(b"HEAD")),
                branch=_branch_name(values.get(b"branch")),
                locked=b"locked" in values,
                prunable=b"prunable" in values,
                bare=b"bare" in values,
            )
        return records

    def _cleanup_attention(
        self,
        change_id: str,
        coordination: ChangeCoordination,
        expected_path: Path,
    ) -> set[ChangeWorktreeAttentionCode]:
        expected_branch = f"owlbear/change/{change_id}"
        attention = self._coordination_attention(change_id, coordination, expected_path)
        if coordination.branch != expected_branch:
            attention.add(ChangeWorktreeAttentionCode.BRANCH_MISMATCH)
        branch_head = self._resolve(coordination.branch, missing_ok=True)
        if branch_head is None:
            attention.add(ChangeWorktreeAttentionCode.BRANCH_MISSING)
        attention.update(self._cleanup_filesystem_attention(expected_path))
        registrations = self._registered_worktrees_all()
        attention.update(
            self._cleanup_registration_attention(expected_path, expected_branch, registrations, branch_head)
        )
        return attention

    @staticmethod
    def _cleanup_filesystem_attention(expected_path: Path) -> set[ChangeWorktreeAttentionCode]:
        if expected_path.is_symlink() or (expected_path.exists() and not expected_path.is_dir()):
            return {ChangeWorktreeAttentionCode.UNEXPECTED_FILESYSTEM_STATE}
        if not expected_path.exists():
            return {ChangeWorktreeAttentionCode.WORKTREE_MISSING}
        return set()

    def _cleanup_registration_attention(
        self,
        expected_path: Path,
        expected_branch: str,
        registrations: dict[Path, _RegisteredGitWorktree],
        branch_head: str | None,
    ) -> set[ChangeWorktreeAttentionCode]:
        attention: set[ChangeWorktreeAttentionCode] = set()
        path_records = [record for path, record in registrations.items() if path == expected_path]
        branch_records = [record for record in registrations.values() if record.branch == expected_branch]
        if len(path_records) != 1:
            attention.add(
                ChangeWorktreeAttentionCode.GIT_REGISTRATION_MISSING
                if not path_records
                else ChangeWorktreeAttentionCode.OWNERSHIP_AMBIGUOUS
            )
        if (
            len(branch_records) != 1
            or (not path_records and branch_records)
            or (path_records and branch_records[0] is not path_records[0])
        ):
            attention.add(ChangeWorktreeAttentionCode.OWNERSHIP_AMBIGUOUS)
        if not path_records:
            return attention
        registered = path_records[0]
        attention.update(self._cleanup_registered_record_attention(registered, expected_branch, branch_head))
        if self._worktree_present(expected_path) and branch_head is not None:
            attention.update(self._cleanup_head_attention(expected_path, branch_head))
            attention.update(self._cleanup_content_attention(expected_path))
        return attention

    @staticmethod
    def _cleanup_registered_record_attention(
        registered: _RegisteredGitWorktree,
        expected_branch: str,
        branch_head: str | None,
    ) -> set[ChangeWorktreeAttentionCode]:
        attention: set[ChangeWorktreeAttentionCode] = set()
        if registered.branch != expected_branch:
            attention.add(ChangeWorktreeAttentionCode.BRANCH_MISMATCH)
        if registered.locked:
            attention.add(ChangeWorktreeAttentionCode.LOCKED)
        if registered.prunable:
            attention.add(ChangeWorktreeAttentionCode.PRUNABLE)
        if registered.bare:
            attention.add(ChangeWorktreeAttentionCode.BARE)
        if registered.branch is None and not registered.bare:
            attention.add(ChangeWorktreeAttentionCode.DETACHED)
        if branch_head is not None and registered.head != branch_head:
            attention.add(ChangeWorktreeAttentionCode.WORKTREE_HEAD_MISMATCH)
        return attention

    def _cleanup_head_attention(
        self,
        expected_path: Path,
        branch_head: str,
    ) -> set[ChangeWorktreeAttentionCode]:
        try:
            actual_head = self._resolve("HEAD", cwd=expected_path)
        except OSError, subprocess.SubprocessError, ValueError:
            return {ChangeWorktreeAttentionCode.UNEXPECTED_FILESYSTEM_STATE}
        return {ChangeWorktreeAttentionCode.WORKTREE_HEAD_MISMATCH} if actual_head != branch_head else set()

    def _cleanup_content_attention(self, expected_path: Path) -> set[ChangeWorktreeAttentionCode]:
        try:
            status = self._git(
                "--no-optional-locks",
                "status",
                "--porcelain=v1",
                "--untracked-files=all",
                cwd=expected_path,
            )
        except OSError, subprocess.SubprocessError, ValueError:
            return {ChangeWorktreeAttentionCode.UNEXPECTED_FILESYSTEM_STATE}
        return {ChangeWorktreeAttentionCode.WORKTREE_DIRTY} if status else set()

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
        *,
        include_content_attention: bool = False,
    ) -> RetainedChangeWorktree:
        expected_branch = f"owlbear/change/{change_id}"
        expected_path = self._worktree_root / change_id
        worktree_present = self._worktree_present(expected_path)
        attention = self._retained_attention(
            change_id,
            coordination,
            registered,
            branch_head,
            expected_path,
        )
        if include_content_attention and worktree_present and registered is not None and branch_head is not None:
            attention.update(self._cleanup_content_attention(expected_path))
        return RetainedChangeWorktree(
            change_id=change_id,
            worktree_path=expected_path,
            branch=expected_branch,
            branch_head=branch_head,
            last_reviewed_commit=coordination.last_reviewed_commit if coordination is not None else None,
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


def _target_sync_digest(receipt: ChangeTargetSyncReceipt) -> str:
    payload = receipt.model_dump(mode="json", exclude={"receipt_id"})
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _target_sync_conflict_digest(conflict: ChangeTargetSyncConflictState) -> str:
    payload = conflict.model_dump(mode="json", exclude={"conflict_id"})
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _target_sync_abort_digest(receipt: ChangeTargetSyncAbortReceipt) -> str:
    payload = receipt.model_dump(mode="json", exclude={"receipt_id"})
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _external_head_adoption_digest(receipt: ChangeExternalHeadAdoptionReceipt) -> str:
    payload = receipt.model_dump(mode="json", exclude={"receipt_id"})
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _external_head_promotion_digest(receipt: ChangeExternalHeadPromotionReceipt) -> str:
    payload = receipt.model_dump(mode="json", exclude={"receipt_id"})
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


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
