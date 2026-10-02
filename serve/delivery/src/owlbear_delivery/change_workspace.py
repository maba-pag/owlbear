"""Per-change writer coordination and Git workspace management."""

from __future__ import annotations

import errno
import hashlib
import json
import os
import re
import secrets
import stat
import subprocess
import tempfile
import time
from collections.abc import Callable
from contextlib import ExitStack, contextmanager, suppress
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from itertools import pairwise
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Annotated, Literal, Never, NotRequired, Protocol, Self, TypedDict, Unpack

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from owlbear_delivery.git_executable import resolve_git_executable
from owlbear_delivery.identities import ChangeId
from owlbear_delivery.recovery import (
    DeliveryWorkerExclusionRequiredError,
    RecoveryEvidence,
    RecoveryIntent,
    RecoveryReceipt,
    digest,
    encoded,
    is_canonical_admitted_path,
    journal_path,
    read_record,
)
from owlbear_delivery.runtime_transaction import (
    ContainedWriteLimits,
    ReplacementTransactionParticipant,
    RuntimeTransaction,
    TransactionConflictError,
    TransactionParticipant,
    contained_directory,
    read_contained,
    write_contained,
)
from owlbear_delivery.storage_io import locked_roots

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator, Mapping
    from contextlib import AbstractContextManager

_OCC_RETRY_LIMIT = 8
_PUBLICATION_LEASE_MAX_SECONDS = 600
_PUBLICATION_OPERATION_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
_CHANGE_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_MERGE_COMMIT_MIN_PARENTS = 2
_PORCELAIN_WORKTREE_STATUS_INDEX = 1
_PORCELAIN_WORKTREE_STATUS_PREFIX_LENGTH = 4
_DESIGN_PACKAGE_NAMES = ("authority.json", "design.md", "intent.md", "manifest.json")
_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_PARENT_COUNT = 2
_INDEX_RECORD_FIELD_COUNT = 3
_INDEX_OBJECT_ID_LENGTHS = frozenset({40, 64})
_MIN_INDEX_BYTES = 32
_INDEX_PATH_LENGTH_MASK = 0x0FFF
_CACHE_TREE_COUNT_FIELDS = 2
_ASCII_DIGIT_MIN = 48
_ASCII_DIGIT_MAX = 57
_MAX_PRESERVED_PATHS = 256
_ACTIVITY_WALK_MAX_ENTRIES = 200_000
_ACTIVITY_WALK_SECONDS = 5.0
_MAX_PRESERVED_PATH_LENGTH = 4096
_MAX_PRESERVED_FILE_BYTES = 16 * 1024 * 1024
_MAX_PRESERVED_TOTAL_BYTES = 64 * 1024 * 1024
_RESTORATION_STAGE_PATTERN = re.compile(r"^stage-[0-9a-f]{32}$")
_RESTORATION_RECORD_TEMPORARY_PATTERN = re.compile(r"^\.tmp-[0-9a-f]{24}$")
_RESTORATION_RECORD_TEMPORARY_MODE = stat.S_IRUSR | stat.S_IWUSR
_MAX_RESTORATION_INCOMPLETE_ARTIFACTS = 256
_MAX_RESTORATION_STAGING_ARTIFACTS = 256
_MAX_RESTORATION_STAGING_BYTES = _MAX_PRESERVED_TOTAL_BYTES
_MAX_RESTORATION_STAGING_ATTEMPTS = 8
_PRESERVATION_FILE_IDENTITY_FIELDS = 8
_PRESERVATION_INDEX_METADATA_FIELDS = 4
_FILE_PERMISSION_MASK = 0o7777
_GIT_MODE_GITLINK = 0o160000
_GIT_MODE_TREE = 0o040000
_GIT_MODE_SYMLINK = 0o120000
_PRIVATE_INDEX_MARKERS = (".env", "credential", "password", "passwd", "secret", "token", "private")
_PRESERVATION_ENV_OVERRIDES = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_COMMON_DIR",
)
_PRIVATE_PATH_MARKERS = frozenset(
    {
        ".aws",
        ".docker",
        ".env",
        ".git-credentials",
        ".npmrc",
        ".pypirc",
        ".ssh",
        "credentials",
        "credential",
        "id_dsa",
        "id_ecdsa",
        "id_ed25519",
        "id_rsa",
        "password",
        "passwd",
        "private",
        "secret",
        "secrets",
        "token",
    }
)


def _contains_private_index_metadata(content: bytes) -> bool:
    lowered = content.lower()
    return any(marker.encode() in lowered for marker in _PRIVATE_INDEX_MARKERS)


@dataclass(frozen=True)
class _RegisteredGitWorktree:
    """Parsed Git registration for one managed worktree path."""

    path: Path
    head: str | None
    branch: str | None
    locked: bool
    prunable: bool
    bare: bool


@dataclass(frozen=True)
class _ManagedIndexIdentity:
    """Descriptor and Git-resolved identity for one registered worktree index."""

    path: Path
    administration: Path
    common_directory: Path
    device: int
    inode: int
    mode: int
    link_count: int


@dataclass(frozen=True)
class BuilderHandoffMetadata:
    """Metadata-only identity of one dirty-capable registered Change workspace."""

    change_id: str
    branch: str
    worktree_path: Path
    last_reviewed_commit: str
    branch_head: str
    registration: _RegisteredGitWorktree
    managed_index: _ManagedIndexIdentity
    index_digest: str
    status_digest: str
    path_metadata: tuple[tuple[str, str, tuple[int, int, int, int, int, int, int, int] | None], ...]

    @property
    def fingerprint(self) -> str:
        """Return the complete metadata identity without persisting file contents."""
        payload = {
            "change_id": self.change_id,
            "branch": self.branch,
            "worktree_path": str(self.worktree_path),
            "last_reviewed_commit": self.last_reviewed_commit,
            "branch_head": self.branch_head,
            "registration": {
                "path": str(self.registration.path),
                "head": self.registration.head,
                "branch": self.registration.branch,
                "locked": self.registration.locked,
                "prunable": self.registration.prunable,
                "bare": self.registration.bare,
            },
            "managed_index": {
                "path": str(self.managed_index.path),
                "administration": str(self.managed_index.administration),
                "common_directory": str(self.managed_index.common_directory),
                "device": self.managed_index.device,
                "inode": self.managed_index.inode,
                "mode": self.managed_index.mode,
                "link_count": self.managed_index.link_count,
                "digest": self.index_digest,
            },
            "status_digest": self.status_digest,
            "path_metadata": [
                [path, kind, list(identity) if identity is not None else None]
                for path, kind, identity in self.path_metadata
            ],
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
        ).hexdigest()


class PreservationPathProvenance(BaseModel):
    """Trusted producer classification for one exact dirty path."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    path: str = Field(min_length=1, max_length=_MAX_PRESERVED_PATH_LENGTH)
    disposition: Literal["useful", "disposable", "foreign", "ambiguous", "private"]
    producer_id: str = Field(min_length=1, max_length=256)
    before_kind: Literal["absent", "regular", "symlink"] | None = None
    before_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    before_mode: int | None = Field(default=None, ge=0)

    @field_validator("path")
    @classmethod
    def _validate_path(cls, value: str) -> str:
        _validate_relative_preservation_path(value)
        return value

    @model_validator(mode="after")
    def _validate_before_state(self) -> Self:
        if self.before_kind is None:
            if self.before_digest is not None or self.before_mode is not None:
                raise ValueError("legacy provenance state cannot carry before-state facts")  # noqa: EM101, TRY003
            return self
        if (self.before_kind == "absent") != (self.before_digest is None):
            raise ValueError("provenance absent state must not carry a content digest")  # noqa: EM101, TRY003
        if self.before_kind == "absent" and self.before_mode is not None:
            raise ValueError("provenance absent state must not carry a mode")  # noqa: EM101, TRY003
        if self.before_kind != "absent" and (self.before_digest is None or self.before_mode is None):
            raise ValueError("provenance present state requires digest and mode")  # noqa: EM101, TRY003
        return self


class PreservationProvenanceEvidence(BaseModel):
    """Owner evidence binding exact paths to a producer and index/head boundary."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    evidence_id: str = Field(min_length=1, max_length=256)
    change_id: ChangeId | None = None
    recovery_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    worktree_path: Path | None = None
    workspace_fingerprint: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    exact_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    index_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    task_id: str | None = Field(default=None, min_length=1, max_length=256)
    task_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    paths: tuple[PreservationPathProvenance, ...] = Field(default=(), max_length=_MAX_PRESERVED_PATHS)

    @field_validator("paths", mode="before")
    @classmethod
    def _normalize_paths(cls, value: object) -> object:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def _validate_evidence(self) -> Self:
        path_names = tuple(item.path for item in self.paths)
        if path_names != tuple(sorted(set(path_names))):
            raise ValueError("preservation provenance paths must be sorted and unique")  # noqa: EM101, TRY003
        if (self.task_id is None) != (self.task_digest is None):
            raise ValueError("preservation provenance task identity requires id and digest")  # noqa: EM101, TRY003
        if self.paths and self.task_id is None:
            raise ValueError("dirty-path provenance requires task identity")  # noqa: EM101, TRY003
        return self


class PreservationProvenanceProvider(Protocol):
    """Trusted owner seam that can identify producers before raw bytes are copied."""

    def classify(  # noqa: PLR0913 - exact evidence binds the full owner/index boundary.
        self,
        *,
        change_id: str,
        intent: RecoveryIntent,
        recovery_id: str,
        worktree_path: Path,
        current_metadata: tuple[tuple[str, str, int | None], ...],
        exact_head: str,
        index_digest: str,
        index_entries: tuple[tuple[str, int, int, str], ...],
        head_entries: tuple[tuple[str, int, str], ...],
        paths: tuple[str, ...],
    ) -> PreservationProvenanceEvidence | None:
        """Return independent producer evidence, or ``None`` when unavailable."""
        ...

    def verify(  # noqa: PLR0913 - reverify the full persisted owner boundary.
        self,
        *,
        change_id: str,
        intent: RecoveryIntent,
        evidence: PreservationProvenanceEvidence,
        recovery_id: str,
        worktree_path: Path,
        current_metadata: tuple[tuple[str, str, int | None], ...],
        exact_head: str,
        index_digest: str,
        index_entries: tuple[tuple[str, int, int, str], ...],
        head_entries: tuple[tuple[str, int, str], ...],
        paths: tuple[str, ...],
    ) -> PreservationProvenanceEvidence | None:
        """Reverify persisted producer evidence against the current exact boundary."""
        ...


class UnavailablePreservationProvenanceProvider:
    """Default boundary: missing producer evidence cannot authorize raw custody."""

    def classify(  # noqa: PLR0913 - mirror the trusted provider boundary.
        self,
        *,
        change_id: str,
        intent: RecoveryIntent,
        recovery_id: str,
        worktree_path: Path,
        current_metadata: tuple[tuple[str, str, int | None], ...],
        exact_head: str,
        index_digest: str,
        index_entries: tuple[tuple[str, int, int, str], ...],
        head_entries: tuple[tuple[str, int, str], ...],
        paths: tuple[str, ...],
    ) -> None:
        """Return no evidence until a trusted producer is configured."""
        _ = (
            change_id,
            intent,
            recovery_id,
            worktree_path,
            current_metadata,
            exact_head,
            index_digest,
            index_entries,
            head_entries,
            paths,
        )

    def verify(  # noqa: PLR0913 - mirror the trusted verification boundary.
        self,
        *,
        change_id: str,
        intent: RecoveryIntent,
        evidence: PreservationProvenanceEvidence,
        recovery_id: str,
        worktree_path: Path,
        current_metadata: tuple[tuple[str, str, int | None], ...],
        exact_head: str,
        index_digest: str,
        index_entries: tuple[tuple[str, int, int, str], ...],
        head_entries: tuple[tuple[str, int, str], ...],
        paths: tuple[str, ...],
    ) -> None:
        """Return no independent verification until a trusted producer is configured."""
        _ = (
            change_id,
            intent,
            evidence,
            recovery_id,
            worktree_path,
            current_metadata,
            exact_head,
            index_digest,
            index_entries,
            head_entries,
            paths,
        )


@dataclass(frozen=True)
class _PreservedPathState:
    """Raw state for one path, held only while an owner-private write is prepared."""

    kind: Literal["absent", "regular", "symlink"]
    content: bytes | None
    mode: int | None
    identity: tuple[int, int, int, int, int, int, int, int] | None = None


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
    kind: Literal["plan", "build", "repair", "finalize", "handoff", "finalization-attention"]


class ChangeBuilderHandoff(_WorkspaceModel):
    """Settled Builder identity retained as non-executing workspace custody."""

    change_id: ChangeId
    settlement_id: str = Field(min_length=1, max_length=256)
    original_task_id: str = Field(min_length=1, max_length=256)
    original_writer: ChangeWriter
    last_reviewed_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    branch_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    metadata_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _validate_original_writer(self) -> Self:
        if self.original_writer.kind != "build":
            message = "Builder handoff requires the exact original Builder writer"
            raise ValueError(message)
        return self


@dataclass(frozen=True)
class PreparedBuilderHandoff:
    """Captured Builder handoff and its uncommitted coordination participant."""

    handoff: ChangeBuilderHandoff
    metadata: BuilderHandoffMetadata
    participant: ReplacementTransactionParticipant


@dataclass(frozen=True)
class BuilderHandoffSource:
    """Exact source fence for a retained Builder handoff or its active successor."""

    settlement_id: str
    original_task_id: str
    branch_head: str
    last_reviewed_commit: str
    metadata_fingerprint: str
    retained_handoff: ChangeBuilderHandoff | None = None


class ChangeFinalizationAttempt(_WorkspaceModel):
    """Durable finalizer custody and exact inputs, completed by its owning receipt."""

    writer: ChangeWriter
    contract_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    frontier_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    exact_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    target_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    finished_at: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def _validate_writer(self) -> Self:
        if self.writer.kind != "finalize":
            message = "finalization attempts require finalizer custody"
            raise ValueError(message)
        return self


class ChangeFinalizationAttention(_WorkspaceModel):
    """Passive, receipt-backed custody after a normally returned failed Finalizer."""

    change_id: ChangeId
    receipt_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    attempt_id: str = Field(min_length=1)
    report_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    outcome: Literal["proof-failed", "review-failed", "ended-without-report"]
    expected_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    expected_reviewed_base: str = Field(pattern=r"^[0-9a-f]{40}$")
    finished_at: str = Field(min_length=1)
    workspace_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    workspace_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    workspace_paths: tuple[str, ...] = Field(default=(), max_length=32)

    @field_validator("workspace_paths", mode="before")
    @classmethod
    def _normalize_workspace_paths(cls, value: object) -> object:
        return tuple(value) if isinstance(value, list) else value


@dataclass(frozen=True)
class FinalizerAcquisition:
    """Exact clean-workspace fence and issuance hook for one Finalizer attempt."""

    attempt: ChangeFinalizationAttempt
    expected_attention: ChangeFinalizationAttention | None
    expected_workspace_fingerprint: str | None
    promoted_commits: tuple[str, ...]
    before_acquire: Callable[[], None] | None = None


class ChangeContinuationAction(_WorkspaceModel):
    """Exact engine operation retained independently of a host response."""

    operation_id: str = Field(pattern=r"^continue-[0-9a-f]{64}$")
    change_id: ChangeId
    kind: Literal["reconcile-checkpoint", "sync-target", "mark-ready", "observe-acceptance"]
    contract_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    frontier_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    exact_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    target_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    finalization_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    host_id: str = Field(min_length=1, max_length=128)
    session_id: str = Field(min_length=1, max_length=128)
    acquired_at: str = Field(min_length=1)
    finished_at: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def _validate_finalization(self) -> Self:
        if self.kind in {"mark-ready", "observe-acceptance"} and self.finalization_id is None:
            message = "provider continuation requires exact finalization identity"
            raise ValueError(message)
        return self


def _is_settled_finalizer_attention_sync(
    coordination: ChangeCoordination,
    action: ChangeContinuationAction,
) -> bool:
    attention = coordination.finalization_attention
    attempt = coordination.finalization_attempt
    attention_writer = (
        attempt.writer.model_copy(update={"kind": "finalization-attention"}) if attempt is not None else None
    )
    exact_action = (
        attempt is not None
        and attempt.finished_at is not None
        and action.finalization_id is None
        and coordination.dirty_worktree_quarantine is None
        and action.change_id == coordination.change_id
        and action.kind == "sync-target"
        and action.contract_digest == attempt.contract_digest
        and action.frontier_digest == attempt.frontier_digest
        and action.exact_head == attempt.exact_head == coordination.last_reviewed_commit
        and action.target_head != attempt.target_head
    )
    if not exact_action:
        return False
    return (
        attention is not None
        and coordination.writer == attention_writer
        and not attention.workspace_paths
        and attention.attempt_id == attempt.writer.attempt_id
        and attention.expected_head == attempt.exact_head
        and attention.workspace_head == attempt.exact_head
        and attention.expected_reviewed_base == coordination.last_reviewed_commit
    )


class _ChangeWorktreeCleanupRecord(_WorkspaceModel):
    """Identity-bound record for one exact Change worktree cleanup."""

    schema_version: Literal[1, 2] = 1
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


class RecoverPublicationBaseline(_WorkspaceModel):
    """Exact explicit authority for one previously unknown publication baseline."""

    change_id: ChangeId
    expected_change_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    publication_base_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    operation_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class RecoverOutOfBandHead(_WorkspaceModel):
    """Exact authority for preserving one out-of-band Change head."""

    change_id: ChangeId
    expected_reviewed_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    expected_remote_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    expected_branch_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    operation_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class PublicationBaselineRecoveryReceipt(_WorkspaceModel):
    """Content-addressed evidence for one explicit recovery of an unknown baseline."""

    schema_version: Literal[1] = 1
    receipt_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    operation_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
    change_id: ChangeId
    expected_change_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    publication_base_head: str = Field(pattern=r"^[0-9a-f]{40}$")

    @classmethod
    def create(
        cls,
        *,
        operation_id: str,
        change_id: str,
        expected_change_head: str,
        publication_base_head: str,
    ) -> Self:
        """Create deterministic evidence for one accepted baseline authority."""
        values = {
            "operation_id": operation_id,
            "change_id": change_id,
            "expected_change_head": expected_change_head,
            "publication_base_head": publication_base_head,
        }
        candidate = cls.model_construct(receipt_id="0" * 64, **values)
        return cls(receipt_id=_publication_baseline_recovery_digest(candidate), **values)

    @model_validator(mode="after")
    def _validate_receipt(self) -> Self:
        if self.receipt_id != _publication_baseline_recovery_digest(self):
            message = "publication baseline recovery receipt identity is invalid"
            raise ValueError(message)
        return self


class OutOfBandHeadRecoveryReceipt(_WorkspaceModel):
    """Content-addressed evidence for preserving and restoring an out-of-band head."""

    schema_version: Literal[1] = 1
    receipt_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    operation_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
    change_id: ChangeId
    branch: str = Field(min_length=1)
    worktree_path: Path
    expected_reviewed_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    expected_remote_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    observed_branch_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    preserved_ref: str = Field(min_length=1)
    preserved_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    restored_head: str = Field(pattern=r"^[0-9a-f]{40}$")

    @classmethod
    def create(  # noqa: PLR0913 - recovery evidence binds each exact workspace identity.
        cls,
        *,
        operation_id: str,
        change_id: str,
        branch: str,
        worktree_path: Path,
        expected_reviewed_head: str,
        expected_remote_head: str,
        observed_branch_head: str,
        preserved_ref: str,
        preserved_head: str,
        restored_head: str,
    ) -> Self:
        """Create deterministic evidence for one restored reviewed boundary."""
        values = {
            "operation_id": operation_id,
            "change_id": change_id,
            "branch": branch,
            "worktree_path": worktree_path,
            "expected_reviewed_head": expected_reviewed_head,
            "expected_remote_head": expected_remote_head,
            "observed_branch_head": observed_branch_head,
            "preserved_ref": preserved_ref,
            "preserved_head": preserved_head,
            "restored_head": restored_head,
        }
        candidate = cls.model_construct(receipt_id="0" * 64, **values)
        return cls(receipt_id=_out_of_band_head_recovery_digest(candidate), **values)

    @model_validator(mode="after")
    def _validate_receipt(self) -> Self:
        if self.receipt_id != _out_of_band_head_recovery_digest(self):
            message = "out-of-band head recovery receipt identity is invalid"
            raise ValueError(message)
        return self


class ChangeTargetSyncReceipt(_WorkspaceModel):
    """Durable evidence for one exact target merge in a managed Change worktree."""

    schema_version: Literal[2] = 2
    receipt_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    operation_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
    change_id: ChangeId
    integration_target: str = Field(min_length=1)
    expected_target: str = Field(pattern=r"^[0-9a-f]{40}$")
    target_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    change_head_before: str = Field(pattern=r"^[0-9a-f]{40}$")
    merged_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    merge_commit: bool
    review_required: bool = False

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
        review_required: bool = False,
    ) -> Self:
        """Create a content-addressed receipt from one completed target merge."""
        values = {
            "schema_version": 2,
            "operation_id": operation_id,
            "change_id": change_id,
            "integration_target": integration_target,
            "expected_target": expected_target,
            "target_head": target_head,
            "change_head_before": change_head_before,
            "merged_head": merged_head,
            "merge_commit": merge_commit,
            "review_required": review_required,
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
    """Content-addressed evidence that one remote Change descendant was adopted or observed."""

    schema_version: Literal[2] = 2
    receipt_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    operation_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
    change_id: ChangeId
    branch: str = Field(min_length=1)
    expected_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    adopted_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    provenance: Literal["fast-forward", "observed"]

    @classmethod
    def create(  # noqa: PLR0913 - adoption receipt binds each exact provenance input.
        cls,
        *,
        operation_id: str,
        change_id: str,
        branch: str,
        expected_head: str,
        adopted_head: str,
        provenance: Literal["fast-forward", "observed"] = "fast-forward",
    ) -> Self:
        """Create deterministic evidence for one adopted remote Change head."""
        values = {
            "schema_version": 2,
            "operation_id": operation_id,
            "change_id": change_id,
            "branch": branch,
            "expected_head": expected_head,
            "adopted_head": adopted_head,
            "provenance": provenance,
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


class ChangeDesignPackageSnapshotIntent(_WorkspaceModel):
    """Durable intent for one admitted Design package snapshot."""

    schema_version: Literal[1] = 1
    intent_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    operation_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
    change_id: ChangeId
    package_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    branch: str = Field(min_length=1)
    worktree_path: Path
    expected_head: str = Field(pattern=r"^[0-9a-f]{40}$")

    @classmethod
    def create(  # noqa: PLR0913 - snapshot identity requires each workspace input.
        cls,
        *,
        operation_id: str,
        change_id: str,
        package_id: str,
        branch: str,
        worktree_path: Path,
        expected_head: str,
    ) -> Self:
        """Create deterministic intent for one managed package snapshot."""
        values = {
            "operation_id": operation_id,
            "change_id": change_id,
            "package_id": package_id,
            "branch": branch,
            "worktree_path": worktree_path,
            "expected_head": expected_head,
        }
        candidate = cls.model_construct(intent_id="0" * 64, **values)
        return cls(intent_id=_design_package_snapshot_intent_digest(candidate), **values)

    @model_validator(mode="after")
    def _validate_identity(self) -> Self:
        if self.intent_id != _design_package_snapshot_intent_digest(self):
            message = "Design package snapshot intent identity is invalid"
            raise ValueError(message)
        return self


class ChangeDesignPackageSnapshotReceipt(_WorkspaceModel):
    """Exact reviewed Change-branch commit containing one admitted Design package."""

    schema_version: Literal[1] = 1
    receipt_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    operation_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
    change_id: ChangeId
    package_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    branch: str = Field(min_length=1)
    worktree_path: Path
    previous_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    snapshot_head: str = Field(pattern=r"^[0-9a-f]{40}$")

    @classmethod
    def create(  # noqa: PLR0913 - snapshot identity requires each workspace input.
        cls,
        *,
        operation_id: str,
        change_id: str,
        package_id: str,
        branch: str,
        worktree_path: Path,
        previous_head: str,
        snapshot_head: str,
    ) -> Self:
        """Create deterministic receipt for one managed package snapshot commit."""
        values = {
            "operation_id": operation_id,
            "change_id": change_id,
            "package_id": package_id,
            "branch": branch,
            "worktree_path": worktree_path,
            "previous_head": previous_head,
            "snapshot_head": snapshot_head,
        }
        candidate = cls.model_construct(receipt_id="0" * 64, **values)
        return cls(receipt_id=_design_package_snapshot_digest(candidate), **values)

    @model_validator(mode="after")
    def _validate_identity(self) -> Self:
        if self.receipt_id != _design_package_snapshot_digest(self):
            message = "Design package snapshot receipt identity is invalid"
            raise ValueError(message)
        return self


class DirtyWorktreeQuarantineReceipt(_WorkspaceModel):
    """Content-addressed evidence that one dirty Builder worktree was preserved."""

    schema_version: Literal[1] = 1
    receipt_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    operation_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
    change_id: ChangeId
    attempt_id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)
    branch: str = Field(min_length=1)
    worktree_path: Path
    base_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    quarantine_ref: str = Field(min_length=1)
    quarantine_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    paths: tuple[str, ...] = Field(min_length=1)

    @field_validator("paths", mode="before")
    @classmethod
    def _normalize_paths(cls, value: object) -> object:
        return tuple(value) if isinstance(value, list) else value

    @field_validator("paths")
    @classmethod
    def _validate_paths(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if value != tuple(sorted(set(value))) or any(
            not path or Path(path).is_absolute() or ".." in Path(path).parts for path in value
        ):
            message = "dirty worktree quarantine paths must be unique, sorted, and relative"
            raise ValueError(message)
        return value

    @classmethod
    def create(  # noqa: PLR0913 - quarantine identity requires each exact workspace input.
        cls,
        *,
        operation_id: str,
        change_id: str,
        attempt_id: str,
        claim_id: str,
        branch: str,
        worktree_path: Path,
        base_head: str,
        quarantine_ref: str,
        quarantine_commit: str,
        paths: tuple[str, ...],
    ) -> Self:
        """Create deterministic evidence for one preserved dirty worktree."""
        values = {
            "operation_id": operation_id,
            "change_id": change_id,
            "attempt_id": attempt_id,
            "claim_id": claim_id,
            "branch": branch,
            "worktree_path": worktree_path,
            "base_head": base_head,
            "quarantine_ref": quarantine_ref,
            "quarantine_commit": quarantine_commit,
            "paths": paths,
        }
        candidate = cls.model_construct(receipt_id="0" * 64, schema_version=1, **values)
        return cls(receipt_id=_quarantine_digest(candidate), **values)

    @model_validator(mode="after")
    def _validate_identity(self) -> Self:
        if self.receipt_id != _quarantine_digest(self):
            message = "dirty worktree quarantine receipt identity is invalid"
            raise ValueError(message)
        return self


class PreservationEntry(_WorkspaceModel):
    """Opaque metadata for one exact worktree path in a private preservation."""

    path: str = Field(min_length=1)
    before_kind: Literal["absent", "regular", "symlink"]
    after_kind: Literal["absent", "regular", "symlink"]
    before_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    after_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    before_mode: int | None = Field(default=None, ge=0)
    after_mode: int | None = Field(default=None, ge=0)
    before_object: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    after_object: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    provenance: PreservationPathProvenance | None = None
    # Device, inode, link count, size, mode, legacy atime slot, mtime and ctime.
    # New captures zero the atime slot; old captures retain it only as metadata.
    # Ordinary reads (including readlink) must not invalidate either version.
    before_identity: tuple[int, int, int, int, int, int, int, int] | None = None

    @field_validator("path")
    @classmethod
    def _validate_path(cls, value: str) -> str:
        _validate_relative_preservation_path(value)
        return value

    @model_validator(mode="after")
    def _validate_content(self) -> Self:
        if (self.before_kind == "absent") != (self.before_digest is None):
            msg = "absent before paths cannot have preserved content"
            raise ValueError(msg)
        if (self.after_kind == "absent") != (self.after_digest is None):
            msg = "absent after paths cannot have preserved content"
            raise ValueError(msg)
        if self.before_kind == "absent" and self.before_identity is not None:
            msg = "absent before paths cannot have filesystem identity"
            raise ValueError(msg)
        if self.before_kind != "absent" and self.before_identity is None:
            msg = "present before paths require filesystem identity"
            raise ValueError(msg)
        if self.before_identity is not None and any(value < 0 for value in self.before_identity):
            msg = "preserved filesystem identity values must be non-negative"
            raise ValueError(msg)
        if self.before_kind != "absent" and (self.before_mode is None or self.before_object is None):
            msg = "present before paths require mode and private content"
            raise ValueError(msg)
        if self.after_kind != "absent" and (self.after_mode is None or self.after_object is None):
            msg = "present after paths require mode and private content"
            raise ValueError(msg)
        return self

    @field_validator("before_identity", mode="before")
    @classmethod
    def _normalize_identity(cls, value: object) -> object:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def _validate_provenance(self) -> Self:
        if self.provenance is not None and self.provenance.path != self.path:
            raise ValueError("preservation path provenance does not match its path")  # noqa: EM101, TRY003
        return self


class _WorktreePreservationReceiptFields(TypedDict):
    preservation_id: str
    recovery_id: str
    change_id: str
    branch: str
    worktree_path: Path
    branch_head: str
    reviewed_head: str
    target_head: str
    integration_target: str
    frontier_digest: str
    coordination_digest: str
    repository: Path
    runtime_root: Path
    worktree_device: int
    worktree_inode: int
    worktree_mode: int
    worktree_links: int
    repository_device: int
    repository_inode: int
    common_device: int
    common_inode: int
    administration_device: int
    administration_inode: int
    runtime_device: int
    runtime_inode: int
    index_path: Path
    administration: Path
    common_directory: Path
    maintained_surfaces: tuple[str, ...]
    last_write_provenance: tuple[str, ...]
    index_digest: str
    index_size: int
    paths: tuple[PreservationEntry, ...]
    provenance: NotRequired[PreservationProvenanceEvidence | None]


class WorktreePreservationReceipt(_WorkspaceModel):
    """Content-addressed public receipt for owner-only raw preservation evidence."""

    schema_version: Literal[1] = 1
    receipt_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    preservation_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    recovery_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    change_id: ChangeId
    branch: str = Field(min_length=1)
    worktree_path: Path
    branch_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    reviewed_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    target_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    integration_target: str = Field(min_length=1, max_length=256)
    frontier_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    coordination_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    repository: Path
    runtime_root: Path
    worktree_device: int = Field(ge=0)
    worktree_inode: int = Field(ge=0)
    worktree_mode: int = Field(ge=0)
    worktree_links: int = Field(ge=1)  # Observation only; restoring directories changes this count.
    repository_device: int = Field(ge=0)
    repository_inode: int = Field(ge=0)
    common_device: int = Field(ge=0)
    common_inode: int = Field(ge=0)
    administration_device: int = Field(ge=0)
    administration_inode: int = Field(ge=0)
    runtime_device: int = Field(ge=0)
    runtime_inode: int = Field(ge=0)
    index_path: Path
    administration: Path
    common_directory: Path
    maintained_surfaces: tuple[str, ...] = Field(min_length=1, max_length=256)
    last_write_provenance: tuple[str, ...] = Field(min_length=1, max_length=256)
    index_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    index_size: int = Field(ge=1, le=_MAX_PRESERVED_TOTAL_BYTES)
    paths: tuple[PreservationEntry, ...] = Field(max_length=_MAX_PRESERVED_PATHS)
    provenance: PreservationProvenanceEvidence | None = None
    storage_ref: str = Field(min_length=1)

    @field_validator("paths", mode="before")
    @classmethod
    def _normalize_paths(cls, value: object) -> object:
        return tuple(value) if isinstance(value, list) else value

    @field_validator("maintained_surfaces", "last_write_provenance", mode="before")
    @classmethod
    def _normalize_provenance(cls, value: object) -> object:
        return tuple(value) if isinstance(value, list) else value

    @model_validator(mode="after")
    def _validate_identity(self) -> Self:
        path_names = tuple(entry.path for entry in self.paths)
        if path_names != tuple(sorted(path_names)) or len(path_names) != len(set(path_names)):
            msg = "preserved paths must be sorted and unique"
            raise ValueError(msg)
        if self.maintained_surfaces != tuple(sorted(set(self.maintained_surfaces))):
            msg = "preserved maintained surfaces must be sorted and unique"
            raise ValueError(msg)
        if self.last_write_provenance != tuple(sorted(set(self.last_write_provenance))):
            msg = "preserved last-write provenance must be sorted and unique"
            raise ValueError(msg)
        if self.provenance is not None and tuple(item.path for item in self.provenance.paths) != path_names:
            raise ValueError("preservation provenance must cover every preserved path exactly")  # noqa: EM101, TRY003
        expected_storage = f"changes/{self.change_id}/recovery-receipts/{self.recovery_id}/preservation"
        if self.storage_ref != expected_storage:
            msg = "preservation storage reference is not engine-owned"
            raise ValueError(msg)
        if self.receipt_id != _preservation_receipt_digest(self):
            msg = "worktree preservation receipt identity is invalid"
            raise ValueError(msg)
        return self

    @classmethod
    def create(cls, **fields: Unpack[_WorktreePreservationReceiptFields]) -> Self:
        """Create a content-addressed receipt from captured workspace facts."""
        values = {
            **fields,
            "provenance": fields.get("provenance"),
            "storage_ref": f"changes/{fields['change_id']}/recovery-receipts/{fields['recovery_id']}/preservation",
        }
        candidate = cls.model_construct(receipt_id="0" * 64, schema_version=1, **values)
        return cls(receipt_id=_preservation_receipt_digest(candidate), **values)


def _preservation_receipt_from_payload(payload: object) -> WorktreePreservationReceipt:
    if not isinstance(payload, dict):
        raise TypeError
    return WorktreePreservationReceipt.model_validate_json(json.dumps(payload.get("receipt")))


def _preservation_manifest_payload(content: bytes) -> dict[str, object]:
    payload = json.loads(content)
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ValueError
    return payload


@dataclass(frozen=True)
class _WorktreeRestorationContext:
    expected: _PreservedPathState
    operation_id: str
    receipt: WorktreePreservationReceipt
    worktree: Path


@dataclass(frozen=True)
class _WorktreeRestorationStage:
    temporary: str
    temporary_relative: str
    source: str | None
    identity: tuple[int, int, int, int, int, int, int, int] | None


@dataclass(frozen=True)
class _WorktreeRestorationStageCandidate:
    temporary: str
    temporary_relative: str
    staging_record: tuple[str, tuple[int, int, int, int, int, int, int, int]] | None
    source: str | None
    identity: tuple[int, int, int, int, int, int, int, int] | None


class PreservationRejectedError(RuntimeError):
    """The exact workspace cannot be privately preserved without unsafe assumptions."""

    code = "ERR_WORKSPACE_PRESERVATION_REJECTED"


class PreservationFenceError(RuntimeError):
    """A preservation identity changed before or during an exact-path replay."""

    code = "ERR_WORKSPACE_PRESERVATION_FENCE"


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
    publication_base_head: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    publication_baseline_recovery: PublicationBaselineRecoveryReceipt | None = None
    last_reviewed_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    design_package_snapshot_intent: ChangeDesignPackageSnapshotIntent | None = None
    design_package_snapshot: ChangeDesignPackageSnapshotReceipt | None = None
    writer: ChangeWriter | None = None
    builder_handoff: ChangeBuilderHandoff | None = None
    finalization_attempt: ChangeFinalizationAttempt | None = None
    finalization_attention: ChangeFinalizationAttention | None = None
    continuation_action: ChangeContinuationAction | None = None
    recovery_owner_id: str | None = Field(default=None, min_length=1, max_length=128)
    recovery_exclusions: tuple[Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")], ...] = Field(
        default=(), max_length=256
    )
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
    dirty_worktree_quarantine: DirtyWorktreeQuarantineReceipt | None = None
    out_of_band_head_recovery: OutOfBandHeadRecoveryReceipt | None = None

    @model_validator(mode="before")
    @classmethod
    def _discard_retired_publication_reservation(cls, value: object) -> object:
        if not isinstance(value, dict) or (
            "publication_operation_id" not in value and "blocked_implementation_recovery" not in value
        ):
            return value
        migrated: dict[object, object] = dict(value)
        migrated.pop("publication_operation_id", None)
        migrated.pop("publication_expires_at", None)
        migrated.pop("blocked_implementation_recovery", None)
        return migrated

    @model_validator(mode="before")
    @classmethod
    def _discard_stale_target_sync_receipt(cls, value: object) -> object:
        if not isinstance(value, dict) or value.get("target_sync_conflict") is None:
            return value
        if value.get("target_sync_receipt") is None:
            return value
        migrated: dict[object, object] = dict(value)
        migrated["target_sync_receipt"] = None
        return migrated

    @field_validator("external_head_adoption_receipts", mode="before")
    @classmethod
    def _normalize_external_head_adoption_receipts(cls, value: object) -> object:
        return tuple(value) if isinstance(value, list) else value

    @field_validator("external_head_promotion_receipts", mode="before")
    @classmethod
    def _normalize_external_head_promotion_receipts(cls, value: object) -> object:
        return tuple(value) if isinstance(value, list) else value

    @field_validator("recovery_exclusions", mode="before")
    @classmethod
    def _normalize_recovery_exclusions(cls, value: object) -> object:
        return tuple(value) if isinstance(value, list) else value

    @property
    def publication_expiry(self) -> datetime | None:
        """Return the normalized lease expiry when publication owns this Change."""
        if self.publication_lease is None:
            return None
        return _publication_timestamp(self.publication_lease.expires_at)

    @model_validator(mode="after")
    def _validate_finalization_custody(self) -> Self:
        action = self.continuation_action
        retained_attention_sync = action is not None and _is_settled_finalizer_attention_sync(self, action)
        if action is not None and (
            action.change_id != self.change_id
            or (action.finished_at is None and self.writer is not None and not retained_attention_sync)
        ):
            message = "continuation action requires its exact exclusive Change custody"
            raise ValueError(message)
        attempt = self.finalization_attempt
        if attempt is not None and attempt.finished_at is None:
            if self.writer != attempt.writer or self.publication_lease is not None:
                message = "unfinished finalization must retain its exact exclusive writer"
                raise ValueError(message)
        elif self.writer is not None and self.writer.kind == "finalize":
            message = "finalizer custody requires an unfinished attempt"
            raise ValueError(message)
        return self

    @model_validator(mode="after")
    def _validate_builder_handoff(self) -> Self:
        handoff = self.builder_handoff
        if handoff is None:
            if self.writer is not None and self.writer.kind == "handoff":
                message = "Builder handoff writer requires its settlement association"
                raise ValueError(message)
            return self
        if handoff.change_id != self.change_id:
            message = "Builder handoff does not match its Change"
            raise ValueError(message)
        expected_writer = handoff.original_writer.model_copy(update={"kind": "handoff"})
        if self.writer != expected_writer or self.last_reviewed_commit != handoff.last_reviewed_commit:
            message = "Builder handoff does not match its retained workspace custody"
            raise ValueError(message)
        if any(
            (
                self.publication_lease,
                self.worktree_cleanup_intent,
                self.worktree_cleanup,
                self.dirty_worktree_quarantine,
                self.target_sync_conflict,
                self.external_head_adoption_intent,
            )
        ):
            message = "Builder handoff cannot overlap another Change operation"
            raise ValueError(message)
        return self

    @model_validator(mode="after")
    def _validate_finalization_attention(self) -> Self:
        attention = self.finalization_attention
        writer = self.writer
        if attention is None:
            if writer is not None and writer.kind == "finalization-attention":
                message = "Finalizer attention writer requires its immutable settlement receipt"
                raise ValueError(message)
            return self
        attempt = self.finalization_attempt
        if (
            attention.change_id != self.change_id
            or writer is None
            or attempt is None
            or attempt.finished_at != attention.finished_at
            or writer != attempt.writer.model_copy(update={"kind": "finalization-attention"})
            or attention.attempt_id != attempt.writer.attempt_id
            or attention.expected_head != attempt.exact_head
            or attention.expected_reviewed_base != self.last_reviewed_commit
            or attention.workspace_head != attention.expected_head
            or any(
                (
                    self.builder_handoff,
                    self.publication_lease,
                    self.continuation_action is not None
                    and self.continuation_action.finished_at is None
                    and not _is_settled_finalizer_attention_sync(self, self.continuation_action),
                    self.recovery_owner_id,
                    self.worktree_cleanup_intent,
                    self.worktree_cleanup,
                    self.dirty_worktree_quarantine,
                    self.target_sync_conflict,
                    self.external_head_adoption_intent,
                )
            )
        ):
            message = "Finalizer attention does not match its ended attempt and retained workspace custody"
            raise ValueError(message)
        return self

    @model_validator(mode="after")
    def _validate_target_sync_receipt(self) -> Self:
        if self.target_sync_receipt is not None and self.target_sync_receipt.change_id != self.change_id:
            message = "target synchronization receipt does not match its Change"
            raise ValueError(message)
        if self.target_sync_abort_receipt is not None and self.target_sync_abort_receipt.change_id != self.change_id:
            message = "target synchronization abort receipt does not match its Change"
            raise ValueError(message)
        self._validate_publication_baseline_recovery()
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
        self._validate_design_package_snapshot()
        self._validate_dirty_worktree_quarantine()
        self._validate_out_of_band_head_recovery()
        return self

    def _validate_design_package_snapshot(self) -> None:
        if (
            self.design_package_snapshot_intent is not None
            and self.design_package_snapshot_intent.change_id != self.change_id
        ):
            message = "Design package snapshot intent does not match its Change"
            raise ValueError(message)
        if self.design_package_snapshot is not None and self.design_package_snapshot.change_id != self.change_id:
            message = "Design package snapshot receipt does not match its Change"
            raise ValueError(message)

    def _validate_dirty_worktree_quarantine(self) -> None:
        receipt = self.dirty_worktree_quarantine
        if receipt is None:
            return
        if receipt.change_id != self.change_id:
            message = "dirty worktree quarantine receipt does not match its Change"
            raise ValueError(message)
        if receipt.branch != self.branch:
            message = "dirty worktree quarantine receipt does not match its branch"
            raise ValueError(message)
        if receipt.worktree_path != self.worktree_path:
            message = "dirty worktree quarantine receipt does not match its worktree"
            raise ValueError(message)
        expected_ref = f"refs/owlbear/quarantine/{receipt.change_id}/{receipt.attempt_id}"
        if receipt.quarantine_ref != expected_ref:
            message = "dirty worktree quarantine receipt ref does not match its attempt"
            raise ValueError(message)
        if self.writer is not None and (
            self.writer.attempt_id != receipt.attempt_id or self.writer.claim_id != receipt.claim_id
        ):
            message = "dirty worktree quarantine receipt does not match active writer custody"
            raise ValueError(message)

    def _validate_out_of_band_head_recovery(self) -> None:
        receipt = self.out_of_band_head_recovery
        if receipt is None:
            return
        if receipt.change_id != self.change_id:
            message = "out-of-band head recovery receipt does not match its Change"
            raise ValueError(message)
        if receipt.branch != self.branch:
            message = "out-of-band head recovery receipt does not match its branch"
            raise ValueError(message)
        if receipt.worktree_path != self.worktree_path:
            message = "out-of-band head recovery receipt does not match its worktree"
            raise ValueError(message)
        expected_ref = f"refs/owlbear/recovery/{receipt.change_id}/{receipt.operation_id}"
        if receipt.preserved_ref != expected_ref:
            message = "out-of-band head recovery receipt ref does not match its operation"
            raise ValueError(message)

    def _validate_publication_baseline_recovery(self) -> None:
        receipt = self.publication_baseline_recovery
        if receipt is not None and receipt.change_id != self.change_id:
            message = "publication baseline recovery receipt does not match its Change"
            raise ValueError(message)
        if receipt is not None and self.publication_base_head != receipt.publication_base_head:
            message = "publication baseline recovery receipt does not match its baseline"
            raise ValueError(message)

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
    quarantine_ref: str | None = None
    quarantine_commit: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
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


class PublicationBaselineUnavailableError(RuntimeError):
    """A publication summary cannot be derived from known baseline authority."""

    code = "ERR_PUBLICATION_BASELINE_UNAVAILABLE"
    retry_safe = False

    def __init__(self, change_id: str, detail: str) -> None:
        self.change_id = change_id
        self.detail = detail
        super().__init__(detail)


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
    """Current writer-capacity payload."""

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
    """A per-change writer slot is unavailable."""

    code = "ERR_TARGET_COORDINATION_CONFLICT"


class ChangeTargetSyncStaleError(CoordinationConflictError):
    """The target fetch changed its expected head before any Change mutation."""


class PortfolioCoordinator:
    """Atomically coordinate independent per-change writers."""

    def __init__(self, state_root: Path) -> None:
        self._state_root = state_root
        self._coordination_root = state_root / "coordination" / "changes"
        self._continuation_owner: ContextVar[str | None] = ContextVar("continuation_owner", default=None)
        self._verified_exclusions: set[tuple[int, str]] = set()
        state_root.mkdir(parents=True, exist_ok=True)
        RuntimeTransaction.recover_all(state_root)

    def recover_pending_transactions(self) -> None:
        """Complete pending coordinator transactions before reading ownership state."""
        RuntimeTransaction.recover_all(self._state_root)

    @property
    def runtime_root(self) -> Path:
        """Return the shared transaction and recovery root."""
        return self._state_root.resolve()

    def acquisition_lock(self) -> AbstractContextManager[None]:
        """Serialize portfolio selection and staged claim preparation."""
        lock_root = self._state_root / "claims" / "acquisition-lock"
        return locked_roots((lock_root,))

    @contextmanager
    def publication_lock(self, change_id: str, *, blocking: bool = True) -> Iterator[PublicationLock]:
        """Serialize bounded publication attempts for one Change across processes."""
        with self.recovery_lock(change_id, blocking=blocking):
            lock = PublicationLock(self, change_id)
            try:
                self.require_continuation_access(change_id)
                yield lock
            finally:
                lock.close()

    @contextmanager
    def recovery_lock(self, change_id: str, *, blocking: bool = True) -> Iterator[None]:
        """Lock exact custody for observation/CAS, without granting effect-entry access."""
        self._coordination_path(change_id)
        namespace_root = self._state_root / "claims" / "publication-locks"
        lock_root = namespace_root / change_id
        with ExitStack() as child_locks:
            with locked_roots((namespace_root,), blocking=blocking):
                child_locks.enter_context(locked_roots((lock_root,), blocking=blocking))
            yield

    def recovery_coordination_bytes(self, change_id: str, owner_id: str) -> bytes:
        """Capture the exact fenced coordination bytes that intent publication will CAS."""
        coordination, _previous = self._read_coordination(change_id)
        if (
            coordination.builder_handoff is not None
            or coordination.finalization_attention is not None
            or coordination.recovery_owner_id not in {None, owner_id}
        ):
            raise DeliveryWorkerExclusionRequiredError
        return _model_content(coordination.model_copy(update={"recovery_owner_id": owner_id}))

    def record_recovery_intent(self, intent: RecoveryIntent) -> None:
        """Atomically fence ordinary writers and persist intent without releasing custody."""
        request = intent.invocation.request
        _coordination, previous = self._read_coordination(request.change_id)
        replacement = self.recovery_coordination_bytes(request.change_id, request.owner_id)
        frontier_path = Path("changes") / request.change_id / "frontier.json"
        frontier = (self._state_root / frontier_path).read_bytes()
        if digest(replacement) != intent.coordination_digest or digest(frontier) != intent.frontier_digest:
            raise DeliveryWorkerExclusionRequiredError
        self._commit(
            f"propose-recovery-{intent.recovery_id}",
            (
                ReplacementTransactionParticipant(
                    self._state_root,
                    self._coordination_path(request.change_id).relative_to(self._state_root),
                    previous,
                    replacement,
                ),
                TransactionParticipant(
                    self._state_root, journal_path(request.change_id, intent.recovery_id, "intent"), encoded(intent)
                ),
                ReplacementTransactionParticipant(self._state_root, frontier_path, frontier, frontier),
            ),
        )

    def prepare_recovery_release(
        self, intent: RecoveryIntent, receipt: RecoveryReceipt
    ) -> ReplacementTransactionParticipant:
        """Prepare only the journal-verified exact release for the runtime transaction."""
        request = intent.invocation.request
        coordination, previous = self._read_coordination(request.change_id)
        if coordination.builder_handoff is not None or coordination.finalization_attention is not None:
            raise DeliveryWorkerExclusionRequiredError
        if (
            digest(previous) != intent.coordination_digest
            or coordination.recovery_owner_id != request.owner_id
            or receipt.recovery_id != intent.recovery_id
            or receipt.evidence.recovery_id != intent.recovery_id
            or receipt.evidence.invocation != intent.invocation
            or receipt.evidence.status not in {"closed", "excluded"}
            or (self._state_root / journal_path(request.change_id, intent.recovery_id, "intent")).read_bytes()
            != encoded(intent)
            or (self._state_root / journal_path(request.change_id, intent.recovery_id, "evidence")).read_bytes()
            != encoded(receipt.evidence)
        ):
            raise DeliveryWorkerExclusionRequiredError
        changes = {"recovery_owner_id": None}
        if receipt.evidence.status == "excluded":
            changes["recovery_exclusions"] = (*coordination.recovery_exclusions, intent.recovery_id)
        if intent.kind == "ready-readback":
            action = coordination.continuation_action
            if action is None or action.operation_id != request.owner_id or action.finished_at is not None:
                raise DeliveryWorkerExclusionRequiredError
            changes["continuation_action"] = action.model_copy(update={"finished_at": receipt.finished_at})
        else:
            writer = coordination.writer
            if writer is not None:
                if writer.claim_id != request.owner_id or writer.attempt_id != request.attempt_id:
                    raise DeliveryWorkerExclusionRequiredError
                changes["writer"] = None
            if intent.kind == "clean-finalizer":
                attempt = coordination.finalization_attempt
                if writer is None or attempt is None or attempt.writer != writer or attempt.finished_at is not None:
                    raise DeliveryWorkerExclusionRequiredError
                changes["finalization_attempt"] = attempt.model_copy(update={"finished_at": receipt.finished_at})
        return _replacement(
            self._state_root,
            self._coordination_path(request.change_id),
            previous,
            coordination.model_copy(update=changes),
        )

    def prepare_finalization_repair_release(
        self, change_id: str, attempt_id: str, finished_at: str
    ) -> TransactionParticipant | ReplacementTransactionParticipant:
        """Join one failed finalizer's custody release to a repair transaction.

        Recovery A may have already released the failed finalizer before its private
        preservation is captured.  In that case retain an exact no-op participant
        rather than reopening or silently replacing the completed attempt.
        """
        coordination, previous = self._read_coordination(change_id)
        self.require_no_pending_recovery(change_id)
        self._require_continuation_coordination(coordination)
        writer = coordination.writer
        attempt = coordination.finalization_attempt
        if (
            writer is None
            and attempt is not None
            and attempt.writer.attempt_id == attempt_id
            and attempt.finished_at is not None
        ):
            return TransactionParticipant(
                self._state_root,
                self._coordination_path(change_id).relative_to(self._state_root),
                previous,
            )
        if (
            writer is None
            or writer.kind != "finalize"
            or writer.attempt_id != attempt_id
            or attempt is None
            or attempt.writer != writer
            or attempt.finished_at is not None
        ):
            raise DeliveryWorkerExclusionRequiredError
        updated = coordination.model_copy(
            update={
                "writer": None,
                "finalization_attempt": attempt.model_copy(update={"finished_at": finished_at}),
            }
        )
        return _replacement(
            self._state_root,
            self._coordination_path(change_id),
            previous,
            updated,
        )

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
        return self._read_coordination(change_id)[0]

    def coordination_bytes(self, change_id: str) -> bytes:
        """Return the exact current coordination bytes for an OCC fence."""
        return self._read_coordination(change_id)[1]

    def require_continuation_access(self, change_id: str) -> None:
        """Refuse mutations outside the fixed executor while an action retains custody."""
        self._require_continuation_coordination(self.show(change_id))

    def _require_continuation_coordination(self, coordination: ChangeCoordination) -> None:
        self.require_no_pending_recovery(coordination.change_id)
        action = coordination.continuation_action
        if action is not None and action.finished_at is None and self._continuation_owner.get() != action.operation_id:
            _coordination_conflict(f"Change retains continuation action custody: {action.operation_id}")

    def require_no_pending_recovery(self, change_id: str) -> None:
        """Keep every normal mutation behind an unfinished recovery's custody fence."""
        coordination = self.show(change_id)
        if coordination.recovery_owner_id is not None or not self.recovery_exclusions_verified(coordination):
            raise DeliveryWorkerExclusionRequiredError

    def recovery_exclusions_verified(self, coordination: ChangeCoordination) -> bool:
        """Require fresh process-local verification of every restart-durable exclusion."""
        return all(
            (os.getpid(), recovery_id) in self._verified_exclusions for recovery_id in coordination.recovery_exclusions
        )

    def recovery_verification_recorded(self, recovery_id: str) -> bool:
        """Return whether this process verified one closed or excluded recovery."""
        return (os.getpid(), recovery_id) in self._verified_exclusions

    def record_verified_exclusion(self, recovery_id: str) -> None:
        """Remember the application owner's verification, never a persisted timestamp."""
        self._verified_exclusions.add((os.getpid(), recovery_id))

    def forget_verified_exclusion(self, recovery_id: str) -> None:
        """Fail closed while a previously accepted exclusion is being revalidated."""
        self._verified_exclusions.discard((os.getpid(), recovery_id))

    def executing_continuation(self, change_id: str) -> bool:
        """Report whether this call context owns the retained fixed operation."""
        action = self.show(change_id).continuation_action
        return (
            action is not None and action.finished_at is None and self._continuation_owner.get() == action.operation_id
        )

    @contextmanager
    def continuation_execution(self, action: ChangeContinuationAction) -> Iterator[None]:
        """Authorize only this call context to run one retained deterministic owner."""
        if self.show(action.change_id).continuation_action != action or action.finished_at is not None:
            _coordination_conflict("continuation execution does not match retained custody")
        token = self._continuation_owner.set(action.operation_id)
        try:
            yield
        finally:
            self._continuation_owner.reset(token)

    def continuation_record_path(self, change_id: str, operation_id: str, *, result: bool = False) -> Path:
        """Locate an immutable action intent or exact result in existing Change state."""
        self._coordination_path(change_id)
        if re.fullmatch(r"continue-[0-9a-f]{64}", operation_id) is None:
            _coordination_conflict("invalid continuation operation identity")
        return (
            self._state_root
            / "changes"
            / change_id
            / "action-receipts"
            / operation_id
            / ("result.json" if result else "intent.json")
        )

    def acquire_continuation_action(self, action: ChangeContinuationAction) -> None:
        """CAS-bind exact frontier custody and immutable intent in one transaction."""
        with self.publication_lock(action.change_id):
            coordination, previous = self._read_coordination(action.change_id)
            self.require_continuation_access(action.change_id)
            attention_sync = _is_settled_finalizer_attention_sync(coordination, action)
            if (coordination.writer is not None and not attention_sync) or coordination.publication_lease is not None:
                _coordination_conflict("continuation cannot overlap active ownership")
            if coordination.worktree_cleanup_intent is not None or coordination.worktree_cleanup is not None:
                _coordination_conflict("continuation cannot overlap worktree cleanup")
            frontier_path = self._state_root / "changes" / action.change_id / "frontier.json"
            frontier = frontier_path.read_bytes()
            if hashlib.sha256(frontier).hexdigest() != action.frontier_digest:
                _coordination_conflict("continuation frontier changed before acquisition")
            retained = coordination.model_copy(update={"continuation_action": action})
            intent_path = self.continuation_record_path(action.change_id, action.operation_id)
            self._commit(
                action.operation_id,
                (
                    _replacement(self._state_root, self._coordination_path(action.change_id), previous, retained),
                    ReplacementTransactionParticipant(
                        self._state_root, frontier_path.relative_to(self._state_root), frontier, frontier
                    ),
                    TransactionParticipant(
                        self._state_root, intent_path.relative_to(self._state_root), _model_content(action)
                    ),
                ),
            )

    def continuation_action_started(self, action: ChangeContinuationAction) -> bool:
        """Read exact effect-entry evidence without creating it."""
        self.require_continuation_access(action.change_id)
        return self.continuation_start_recorded(action)

    def continuation_start_recorded(self, action: ChangeContinuationAction) -> bool:
        """Read one action's identity-checked effect-entry marker without a mutation guard."""
        path = self.continuation_record_path(action.change_id, action.operation_id).with_name("started.json")
        try:
            content = path.read_bytes()
        except FileNotFoundError:
            return False
        if content != _model_content(action):
            _coordination_conflict("continuation start identity differs from retained custody")
        return True

    def start_continuation_action(self, action: ChangeContinuationAction) -> bool:
        """Record effect entry; an interrupted call is not permission for another effect."""
        if self.continuation_action_started(action):
            return False
        path = self.continuation_record_path(action.change_id, action.operation_id).with_name("started.json")
        self._commit(
            f"start-{action.operation_id}",
            (TransactionParticipant(self._state_root, path.relative_to(self._state_root), _model_content(action)),),
        )
        return True

    def finish_continuation_action(
        self, action: ChangeContinuationAction, result: bytes, finished_at: str, *, release: bool
    ) -> None:
        """Persist exact result with custody release, or retain custody on a blocked effect."""
        self.require_continuation_access(action.change_id)
        coordination, previous = self._read_coordination(action.change_id)
        if coordination.continuation_action != action:
            _coordination_conflict("continuation result does not match retained custody")
        retained = action.model_copy(update={"finished_at": finished_at}) if release else action
        result_path = self.continuation_record_path(action.change_id, action.operation_id, result=True)
        self._commit(
            f"result-{action.operation_id}",
            (
                _replacement(
                    self._state_root,
                    self._coordination_path(action.change_id),
                    previous,
                    coordination.model_copy(update={"continuation_action": retained}),
                ),
                TransactionParticipant(self._state_root, result_path.relative_to(self._state_root), result),
            ),
        )

    def find_registered(self, change_id: str) -> ChangeCoordination | None:
        """Distinguish genuine absence from unreadable or invalid coordination."""
        try:
            return self.show(change_id)
        except CoordinationConflictError as exc:
            if not isinstance(exc.__cause__, FileNotFoundError):
                raise
            return None

    def _read_coordination(self, change_id: str) -> tuple[ChangeCoordination, bytes]:
        path = self._coordination_path(change_id)
        try:
            content = path.read_bytes()
            coordination = ChangeCoordination.model_validate_json(content)
        except FileNotFoundError as exc:
            msg = f"change workspace is not registered: {change_id}"
            raise CoordinationConflictError(msg) from exc
        except (OSError, ValidationError) as exc:
            msg = f"change coordination record is unreadable or invalid: {change_id}"
            raise CoordinationConflictError(msg) from exc
        if coordination.change_id != change_id:
            _coordination_conflict(f"change coordination record identity is invalid: {change_id}")
        return coordination, content

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
            except (OSError, ValidationError):
                _coordination_conflict(f"change coordination record is invalid: {path}")
            if path.stem != coordination.change_id:
                _coordination_conflict(f"change coordination record identity is invalid: {path}")
            records.append(coordination)
        return tuple(sorted(records, key=lambda item: item.change_id))

    def acquire(
        self,
        change_id: str,
        writer: ChangeWriter,
        *,
        finalization_attempt: ChangeFinalizationAttempt | None = None,
    ) -> ChangeCoordination:
        """Atomically bind one writer to a Change."""
        coordination = self.show(change_id)
        publication_expiry = coordination.publication_expiry
        if publication_expiry is not None and publication_expiry > datetime.now(UTC):
            _coordination_conflict("change already has an active writer")
        with self.publication_lock(change_id):
            return self._acquire(
                change_id,
                writer,
                finalization_attempt=finalization_attempt,
            )

    @staticmethod
    def _validate_finalizer_attention_retry(
        coordination: ChangeCoordination,
        writer: ChangeWriter,
        finalization_attempt: ChangeFinalizationAttempt | None,
        expected_finalization_attention: ChangeFinalizationAttention | None,
    ) -> bool:
        if expected_finalization_attention is None:
            return False
        prior_attempt = coordination.finalization_attempt
        expected_attention_writer = (
            prior_attempt.writer.model_copy(update={"kind": "finalization-attention"})
            if prior_attempt is not None
            else None
        )
        if (
            prior_attempt is None
            or prior_attempt.finished_at is None
            or coordination.finalization_attention != expected_finalization_attention
            or coordination.writer != expected_attention_writer
            or expected_finalization_attention.attempt_id != prior_attempt.writer.attempt_id
            or expected_finalization_attention.expected_head != prior_attempt.exact_head
            or expected_finalization_attention.expected_reviewed_base != coordination.last_reviewed_commit
            or prior_attempt.writer.attempt_id == writer.attempt_id
            or prior_attempt.writer.claim_id == writer.claim_id
            or finalization_attempt is None
            or finalization_attempt.contract_digest != prior_attempt.contract_digest
            or finalization_attempt.frontier_digest != prior_attempt.frontier_digest
            or finalization_attempt.exact_head != prior_attempt.exact_head
            or finalization_attempt.target_head != prior_attempt.target_head
        ):
            _coordination_conflict("finalizer retry does not match its retained attention")
        return True

    def _acquire(
        self,
        change_id: str,
        writer: ChangeWriter,
        *,
        finalization_attempt: ChangeFinalizationAttempt | None = None,
        expected_finalization_attention: ChangeFinalizationAttention | None = None,
    ) -> ChangeCoordination:
        if writer.kind in {"handoff", "finalization-attention"}:
            _coordination_conflict("passive workspace custody is not an executable writer")
        if (writer.kind == "finalize") != (finalization_attempt is not None) or (
            finalization_attempt is not None
            and (finalization_attempt.writer != writer or finalization_attempt.finished_at is not None)
        ):
            _coordination_conflict("finalizer acquisition requires its exact unfinished attempt")
        self.require_continuation_access(change_id)
        coordination_path = self._coordination_path(change_id)
        coordination_bytes = coordination_path.read_bytes()
        coordination = ChangeCoordination.model_validate_json(coordination_bytes)
        publication_expiry = coordination.publication_expiry
        publication_active = publication_expiry is not None and publication_expiry > datetime.now(UTC)
        attention_retry = self._validate_finalizer_attention_retry(
            coordination,
            writer,
            finalization_attempt,
            expected_finalization_attention,
        )
        if (
            (coordination.writer is not None and not attention_retry)
            or publication_active
            or coordination.worktree_cleanup_intent is not None
            or coordination.worktree_cleanup is not None
        ):
            _coordination_conflict("change already has an active writer")
        claimed = coordination.model_copy(
            update={
                "writer": writer,
                "finalization_attempt": finalization_attempt or coordination.finalization_attempt,
                "publication_lease": None,
                "finalization_attention": None if attention_retry else coordination.finalization_attention,
                "dirty_worktree_quarantine": (coordination.dirty_worktree_quarantine if attention_retry else None),
            }
        )
        participants = [_replacement(self._state_root, coordination_path, coordination_bytes, claimed)]
        if finalization_attempt is not None:
            frontier_path = self._state_root / "changes" / change_id / "frontier.json"
            frontier_bytes = frontier_path.read_bytes()
            if hashlib.sha256(frontier_bytes).hexdigest() != finalization_attempt.frontier_digest:
                _coordination_conflict("finalization frontier changed before acquisition")
            participants.append(
                ReplacementTransactionParticipant(
                    self._state_root, frontier_path.relative_to(self._state_root), frontier_bytes, frontier_bytes
                )
            )
        try:
            self._commit(
                f"acquire-{change_id}-{writer.claim_id}",
                tuple(participants),
            )
        except TransactionConflictError as exc:
            msg = "writer coordination changed concurrently"
            raise CoordinationConflictError(msg) from exc
        return claimed

    def release(self, change_id: str, claim_id: str) -> ChangeCoordination:
        """Release one exact writer."""
        self.require_continuation_access(change_id)
        for _attempt in range(_OCC_RETRY_LIMIT):
            coordination_path = self._coordination_path(change_id)
            coordination_bytes = coordination_path.read_bytes()
            coordination = ChangeCoordination.model_validate_json(coordination_bytes)
            self._require_continuation_coordination(coordination)
            if coordination.writer is None:
                return coordination
            if (
                coordination.writer.kind in {"handoff", "finalization-attention"}
                or coordination.builder_handoff is not None
                or coordination.finalization_attention is not None
            ):
                _coordination_conflict("passive workspace custody cannot be released as a worker claim")
            if coordination.writer is None or coordination.writer.claim_id != claim_id:
                _coordination_conflict("writer claim does not own the change workspace")
            if coordination.writer.kind == "finalize":
                _coordination_conflict("finalizer custody requires atomic finalization completion")
            released = coordination.model_copy(update={"writer": None})
            try:
                self._commit(
                    f"release-{change_id}-{claim_id}",
                    (_replacement(self._state_root, coordination_path, coordination_bytes, released),),
                )
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
        """OCC-replace one registered per-change record without changing ownership."""
        existing = self.show(coordination.change_id)
        if existing.publication_lease is not None and existing != coordination:
            _coordination_conflict("workspace update cannot change a reserved publication boundary")
        if lock is not None:
            self._require_publication_lock(lock, coordination.change_id)
            return self._update(coordination)
        with self.publication_lock(coordination.change_id):
            return self._update(coordination)

    def _update(self, coordination: ChangeCoordination) -> ChangeCoordination:
        self.require_continuation_access(coordination.change_id)
        path = self._coordination_path(coordination.change_id)
        previous = path.read_bytes()
        existing = ChangeCoordination.model_validate_json(previous)
        self._validate_coordination_ownership_update(existing, coordination)
        if existing.publication_lease is not None and existing != coordination:
            _coordination_conflict("workspace update cannot change a reserved publication boundary")
        baseline_changed = existing.publication_base_head != coordination.publication_base_head
        baseline_recovered_explicitly = (
            existing.publication_base_head is None
            and coordination.publication_base_head is not None
            and coordination.publication_baseline_recovery is not None
        )
        if baseline_changed and not baseline_recovered_explicitly:
            _coordination_conflict("publication baseline requires explicit recovery")
        if (
            existing.publication_baseline_recovery is not None
            and existing.publication_baseline_recovery != coordination.publication_baseline_recovery
        ):
            _coordination_conflict("publication baseline recovery authority cannot be replaced")
        if (
            existing.publication_baseline_recovery is None
            and coordination.publication_baseline_recovery is not None
            and existing.publication_base_head is not None
        ):
            _coordination_conflict("publication baseline recovery authority cannot be added")
        if existing.dirty_worktree_quarantine is not None and (
            existing.dirty_worktree_quarantine != coordination.dirty_worktree_quarantine
        ):
            _coordination_conflict("dirty worktree quarantine authority cannot be replaced")
        if existing.dirty_worktree_quarantine is None and coordination.dirty_worktree_quarantine is not None:
            receipt = coordination.dirty_worktree_quarantine
            writer = coordination.writer
            if writer is None or writer.attempt_id != receipt.attempt_id or writer.claim_id != receipt.claim_id:
                _coordination_conflict("dirty worktree quarantine authority requires matching writer custody")
        self._validate_out_of_band_head_recovery_update(existing, coordination)
        participant = _replacement(self._state_root, path, previous, coordination)
        try:
            self._commit(f"update-{coordination.change_id}", (participant,))
        except TransactionConflictError as exc:
            msg = "change workspace changed concurrently"
            raise CoordinationConflictError(msg) from exc
        return coordination

    def _validate_coordination_ownership_update(
        self,
        existing: ChangeCoordination,
        replacement: ChangeCoordination,
    ) -> None:
        if existing.builder_handoff is not None and existing != replacement:
            _coordination_conflict("workspace update cannot mutate retained Builder handoff custody")
        action = existing.continuation_action
        receipt = replacement.target_sync_receipt
        conflict = replacement.target_sync_conflict
        sync_outcome_matches = action is not None and (
            (
                receipt is not None
                and receipt.operation_id == action.operation_id
                and receipt.expected_target == action.target_head
                and receipt.change_head_before == action.exact_head
                and receipt.merged_head == replacement.last_reviewed_commit
            )
            or (
                conflict is not None
                and conflict.operation_id == action.operation_id
                and conflict.target_head == action.target_head
                and conflict.change_head_before == action.exact_head
                and conflict.change_id == action.change_id
            )
        )
        attention_sync_release = (
            action is not None
            and self.executing_continuation(existing.change_id)
            and action.finished_at is None
            and action == replacement.continuation_action
            and _is_settled_finalizer_attention_sync(existing, action)
            and replacement.writer is None
            and replacement.finalization_attention is None
            and sync_outcome_matches
        )
        ownership_changed = (
            existing.writer != replacement.writer
            or existing.finalization_attention != replacement.finalization_attention
        )
        if (
            (ownership_changed and not attention_sync_release)
            or existing.builder_handoff != replacement.builder_handoff
            or existing.recovery_owner_id != replacement.recovery_owner_id
            or existing.recovery_exclusions != replacement.recovery_exclusions
            or existing.publication_lease != replacement.publication_lease
            or existing.continuation_action != replacement.continuation_action
        ):
            _coordination_conflict("workspace update cannot change ownership")

    @staticmethod
    def _validate_out_of_band_head_recovery_update(
        existing: ChangeCoordination,
        replacement: ChangeCoordination,
    ) -> None:
        if existing.out_of_band_head_recovery is not None and (
            existing.out_of_band_head_recovery != replacement.out_of_band_head_recovery
        ):
            _coordination_conflict("out-of-band head recovery authority cannot be replaced")

    def prepare_reviewed_boundary(
        self,
        coordination: ChangeCoordination,
        reviewed_head: str,
        lock: PublicationLock,
    ) -> ReplacementTransactionParticipant | None:
        """Prepare a reviewed-boundary replacement for a shared Delivery transaction."""
        self._require_publication_lock(lock, coordination.change_id)
        path = self._coordination_path(coordination.change_id)
        previous = path.read_bytes()
        existing = ChangeCoordination.model_validate_json(previous)
        if existing != coordination:
            _coordination_conflict("change workspace changed during finalization preparation")
        if existing.builder_handoff is not None:
            _coordination_conflict("finalization cannot advance a retained Builder handoff boundary")
        if existing.last_reviewed_commit == reviewed_head:
            return None
        updated = existing.model_copy(update={"last_reviewed_commit": reviewed_head})
        return _replacement(self._state_root, path, previous, updated)

    def prepare_finalization_completion(
        self,
        coordination: ChangeCoordination,
        reviewed_head: str,
        finished_at: str,
        lock: PublicationLock,
    ) -> ReplacementTransactionParticipant:
        """Join custody release and reviewed-boundary advancement to the receipt transaction."""
        self._require_publication_lock(lock, coordination.change_id)
        path = self._coordination_path(coordination.change_id)
        previous = path.read_bytes()
        existing = ChangeCoordination.model_validate_json(previous)
        attempt = existing.finalization_attempt
        if existing != coordination or attempt is None or attempt.finished_at is not None:
            _coordination_conflict("finalization custody changed during completion")
        updated = existing.model_copy(
            update={
                "writer": None,
                "last_reviewed_commit": reviewed_head,
                "finalization_attempt": attempt.model_copy(update={"finished_at": finished_at}),
            }
        )
        return _replacement(self._state_root, path, previous, updated)

    def prepare_finalization_attention(
        self,
        change_id: str,
        writer: ChangeWriter,
        attention: ChangeFinalizationAttention,
        lock: PublicationLock,
    ) -> ReplacementTransactionParticipant:
        """Prepare one exact normal-return failure as passive, receipt-backed custody."""
        self._require_publication_lock(lock, change_id)
        self.require_no_pending_recovery(change_id)
        path = self._coordination_path(change_id)
        previous = path.read_bytes()
        existing = ChangeCoordination.model_validate_json(previous)
        attempt = existing.finalization_attempt
        if (
            existing.writer != writer
            or writer.kind != "finalize"
            or attempt is None
            or attempt.writer != writer
            or attempt.finished_at is not None
            or attention.change_id != change_id
            or attention.attempt_id != writer.attempt_id
        ):
            _coordination_conflict("Finalizer settlement does not match the exact active workspace attempt")
        updated = existing.model_copy(
            update={
                "writer": writer.model_copy(update={"kind": "finalization-attention"}),
                "finalization_attempt": attempt.model_copy(update={"finished_at": attention.finished_at}),
                "finalization_attention": attention,
            }
        )
        try:
            ChangeCoordination.model_validate(updated.model_dump(mode="python"))
        except ValidationError as exc:
            _coordination_conflict("Finalizer settlement does not form valid passive workspace custody")
            raise AssertionError from exc
        return _replacement(self._state_root, path, previous, updated)

    def prepare_runtime_custody_guard(
        self,
        change_id: str,
        *,
        expected_finalization_attention: ChangeFinalizationAttention | None = None,
    ) -> ReplacementTransactionParticipant:
        """Fence a runtime mutation against concurrent finalizer acquisition."""
        self.require_continuation_access(change_id)
        path = self._coordination_path(change_id)
        coordination, previous = self._read_coordination(change_id)
        self._require_continuation_coordination(coordination)
        attempt = coordination.finalization_attempt
        if expected_finalization_attention is None and (
            (coordination.writer is not None and coordination.writer.kind == "finalize")
            or coordination.finalization_attention is not None
        ):
            _coordination_conflict("mutation cannot overlap active or retained Finalizer custody")
        if expected_finalization_attention is not None and (
            coordination.finalization_attention != expected_finalization_attention
            or attempt is None
            or attempt.finished_at != expected_finalization_attention.finished_at
            or coordination.writer != attempt.writer.model_copy(update={"kind": "finalization-attention"})
        ):
            _coordination_conflict("finalization attention changed during a passive Change intent")
        return ReplacementTransactionParticipant(
            self._state_root, path.relative_to(self._state_root), previous, previous
        )

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
        self.require_continuation_access(change_id)
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

    def _prepare_builder_handoff(
        self,
        coordination: ChangeCoordination,
        handoff: ChangeBuilderHandoff,
        lock: PublicationLock,
    ) -> ReplacementTransactionParticipant:
        """Prepare the exact build-writer replacement for a shared settlement transaction."""
        self._require_publication_lock(lock, coordination.change_id)
        self.require_no_pending_recovery(coordination.change_id)
        path = self._coordination_path(coordination.change_id)
        previous = path.read_bytes()
        existing = ChangeCoordination.model_validate_json(previous)
        if existing != coordination or existing.builder_handoff is not None:
            _coordination_conflict("Change workspace changed during Builder handoff preparation")
        if (
            existing.writer is None
            or existing.writer != handoff.original_writer
            or existing.writer.kind != "build"
            or handoff.change_id != coordination.change_id
            or handoff.last_reviewed_commit != existing.last_reviewed_commit
        ):
            _coordination_conflict("Builder handoff does not match the exact active build writer")
        updated = existing.model_copy(
            update={
                "writer": existing.writer.model_copy(update={"kind": "handoff"}),
                "builder_handoff": handoff,
            }
        )
        return _replacement(self._state_root, path, previous, updated)

    def _prepare_builder_handoff_acquisition(
        self,
        change_id: str,
        writer: ChangeWriter,
        handoff: ChangeBuilderHandoff,
        metadata: BuilderHandoffMetadata,
        lock: PublicationLock,
    ) -> ReplacementTransactionParticipant:
        """Prepare exact handoff consumption for a shared claim-activation transaction."""
        self._require_publication_lock(lock, change_id)
        self.require_no_pending_recovery(change_id)
        coordination, previous = self._read_coordination(change_id)
        retained = coordination.builder_handoff
        expected_handoff_writer = (
            None if retained is None else retained.original_writer.model_copy(update={"kind": "handoff"})
        )
        if (
            retained != handoff
            or coordination.writer != expected_handoff_writer
            or writer.kind != "build"
            or writer.attempt_id == handoff.original_writer.attempt_id
            or writer.claim_id == handoff.original_writer.claim_id
            or metadata.change_id != change_id
            or metadata.branch != coordination.branch
            or metadata.worktree_path != coordination.worktree_path
            or metadata.last_reviewed_commit != handoff.last_reviewed_commit
            or metadata.branch_head != handoff.branch_head
            or metadata.fingerprint != handoff.metadata_fingerprint
            or coordination.last_reviewed_commit != handoff.last_reviewed_commit
            or coordination.publication_lease is not None
            or coordination.worktree_cleanup_intent is not None
            or coordination.worktree_cleanup is not None
            or coordination.dirty_worktree_quarantine is not None
        ):
            _coordination_conflict("Builder handoff does not match the exact settlement, task, and workspace")
        claimed = coordination.model_copy(update={"writer": writer, "builder_handoff": None})
        return _replacement(self._state_root, self._coordination_path(change_id), previous, claimed)


class ChangeWorkspaceManager:
    """Own one warm writable Git worktree and non-rewriting integration per change."""

    def __init__(  # noqa: PLR0913, PLR0917 - construction binds repository, worktree, target and owner evidence.
        self,
        repository: Path,
        worktree_root: Path,
        coordinator: PortfolioCoordinator,
        integration_target: str,
        remote: str = "origin",
        preservation_provenance_provider: PreservationProvenanceProvider | None = None,
    ) -> None:
        self._require_preservation_environment()
        self._repository = repository.resolve()
        if worktree_root.is_symlink() or (worktree_root.exists() and not worktree_root.is_dir()):
            _workspace_failure("Change worktree root is not a safe directory")
        self._worktree_root = worktree_root.resolve()
        self._coordinator = coordinator
        self._integration_target = integration_target
        self._remote = remote
        self._preservation_provenance_provider = (
            preservation_provenance_provider or UnavailablePreservationProvenanceProvider()
        )
        self._git("check-ref-format", self._target_ref())

    @property
    def repository(self) -> Path:
        """Return the engine-owned repository used for managed Change reads."""
        return self._repository

    @property
    def runtime_root(self) -> Path:
        """Return the coordinator's transaction root for runtime assembly validation."""
        return self._coordinator.runtime_root

    def _target_ref(self) -> str:
        if self._integration_target.startswith("refs/remotes/"):
            return self._integration_target
        return f"refs/remotes/{self._remote}/{self._integration_target}"

    def observed_target_head(self) -> str:
        """Read the current engine target ref without fetching or changing it."""
        self._require_preservation_environment()
        return self._resolve(self._target_ref())

    def prepare_runtime_custody_guard(
        self,
        change_id: str,
        *,
        expected_finalization_attention: ChangeFinalizationAttention | None = None,
    ) -> ReplacementTransactionParticipant:
        """Join current workspace custody to the caller's runtime transaction."""
        return self._coordinator.prepare_runtime_custody_guard(
            change_id,
            expected_finalization_attention=expected_finalization_attention,
        )

    def prepare_recovery_release(
        self, intent: RecoveryIntent, receipt: RecoveryReceipt
    ) -> ReplacementTransactionParticipant:
        """Join exact recovered custody to its immutable completion receipt."""
        return self._coordinator.prepare_recovery_release(intent, receipt)

    def prepare_finalization_repair_release(
        self, change_id: str, attempt_id: str, finished_at: str
    ) -> TransactionParticipant | ReplacementTransactionParticipant:
        """Join a failed finalizer's exact release to a repair transaction."""
        return self._coordinator.prepare_finalization_repair_release(change_id, attempt_id, finished_at)

    def prepare_builder_handoff(
        self,
        change_id: str,
        writer: ChangeWriter,
        settlement_id: str,
        original_task_id: str,
        lock: PublicationLock,
    ) -> PreparedBuilderHandoff:
        """Prepare metadata-only handoff custody without committing its participant."""
        self._coordinator._require_publication_lock(lock, change_id)  # noqa: SLF001
        self._coordinator.require_no_pending_recovery(change_id)
        coordination = self._coordinator.show(change_id)
        if writer.kind != "build" or coordination.writer != writer or coordination.builder_handoff is not None:
            _coordination_conflict("Builder handoff requires the exact active build writer")
        if (
            coordination.publication_lease is not None
            or (coordination.finalization_attempt is not None and coordination.finalization_attempt.finished_at is None)
            or (coordination.continuation_action is not None and coordination.continuation_action.finished_at is None)
            or coordination.worktree_cleanup_intent is not None
            or coordination.worktree_cleanup is not None
            or coordination.dirty_worktree_quarantine is not None
            or coordination.target_sync_conflict is not None
            or coordination.external_head_adoption_intent is not None
        ):
            _coordination_conflict("Builder handoff cannot overlap another Change operation")
        metadata = self._capture_builder_handoff_metadata(coordination)
        handoff = ChangeBuilderHandoff(
            change_id=change_id,
            settlement_id=settlement_id,
            original_task_id=original_task_id,
            original_writer=writer,
            last_reviewed_commit=coordination.last_reviewed_commit,
            branch_head=metadata.branch_head,
            metadata_fingerprint=metadata.fingerprint,
        )
        participant = self._coordinator._prepare_builder_handoff(coordination, handoff, lock)  # noqa: SLF001
        return PreparedBuilderHandoff(handoff=handoff, metadata=metadata, participant=participant)

    def acquire(
        self,
        change_id: str,
        writer: ChangeWriter,
        *,
        handoff: ChangeBuilderHandoff | None = None,
        handoff_task_id: str | None = None,
        finalizer: FinalizerAcquisition | None = None,
    ) -> ChangeCoordination:
        """Acquire ordinary writer custody or consume one revalidated exact Builder handoff."""
        if finalizer is not None:
            return self._acquire_finalizer(change_id, writer, finalizer)
        coordination = self._coordinator.show(change_id)
        if coordination.builder_handoff is None:
            if handoff is not None:
                _coordination_conflict("Builder handoff is no longer retained by the Change")
            return self._coordinator.acquire(change_id, writer)
        if handoff is None or handoff != coordination.builder_handoff or handoff_task_id != handoff.original_task_id:
            _coordination_conflict("Builder handoff settlement or original task identity differs")
        with self._coordinator.publication_lock(change_id) as lock:
            participant = self.prepare_builder_handoff_acquisition(
                change_id, writer, handoff, lock, task_id=handoff_task_id
            )
            RuntimeTransaction(
                self.runtime_root, f"acquire-builder-handoff-{change_id}-{writer.claim_id}", (participant,)
            ).commit()
            return self._coordinator.show(change_id)

    def _acquire_finalizer(
        self,
        change_id: str,
        writer: ChangeWriter,
        finalizer: FinalizerAcquisition,
    ) -> ChangeCoordination:
        if (
            writer.kind != "finalize"
            or writer != finalizer.attempt.writer
            or finalizer.expected_workspace_fingerprint is None
        ):
            _coordination_conflict("Finalizer acquisition requires its exact clean workspace fingerprint")
        with self._coordinator.publication_lock(change_id):
            current = self._coordinator.show(change_id)
            self._coordinator._validate_finalizer_attention_retry(  # noqa: SLF001
                current,
                writer,
                finalizer.attempt,
                finalizer.expected_attention,
            )
            if current.builder_handoff is not None:
                _coordination_conflict("only a new Builder claim can consume Builder handoff custody")
            captured, head, fingerprint, paths, reason = self.capture_finalization_workspace(
                change_id, finalizer.promoted_commits
            )
            target_head = self.observed_target_head()
            expected_reason = "active-custody" if finalizer.expected_attention is not None else None
            if (
                current != captured
                or head != finalizer.attempt.exact_head
                or fingerprint != finalizer.expected_workspace_fingerprint
                or paths
                or reason != expected_reason
                or target_head != finalizer.attempt.target_head
            ):
                _coordination_conflict("Finalizer workspace changed before acquisition")
            if finalizer.before_acquire is not None:
                finalizer.before_acquire()
            return self._coordinator._acquire(  # noqa: SLF001 - manager validates the clean workspace under this lock.
                change_id,
                writer,
                finalization_attempt=finalizer.attempt,
                expected_finalization_attention=finalizer.expected_attention,
            )

    def prepare_builder_handoff_acquisition(
        self,
        change_id: str,
        writer: ChangeWriter,
        handoff: ChangeBuilderHandoff,
        lock: PublicationLock,
        *,
        task_id: str,
    ) -> ReplacementTransactionParticipant:
        """Prepare a same-task handoff replacement without activating a claim independently."""
        self._coordinator._require_publication_lock(lock, change_id)  # noqa: SLF001
        self._coordinator.require_no_pending_recovery(change_id)
        coordination = self._coordinator.show(change_id)
        if coordination.builder_handoff != handoff or task_id != handoff.original_task_id:
            _coordination_conflict("Builder handoff changed or belongs to another task")
        if writer.kind != "build":
            _coordination_conflict("only a new Builder claim can consume Builder handoff custody")
        metadata = self._capture_builder_handoff_metadata(coordination)
        if metadata.fingerprint != handoff.metadata_fingerprint:
            message = "Builder handoff workspace metadata changed before acquisition"
            raise PreservationFenceError(message)
        return self._coordinator._prepare_builder_handoff_acquisition(  # noqa: SLF001
            change_id, writer, handoff, metadata, lock
        )

    def _capture_builder_handoff_metadata(self, coordination: ChangeCoordination) -> BuilderHandoffMetadata:
        self._require_preservation_environment()
        self._coordinator.require_no_pending_recovery(coordination.change_id)
        handoff = coordination.builder_handoff
        expected_writer = (
            handoff.original_writer.model_copy(update={"kind": "handoff"})
            if handoff is not None
            else coordination.writer
        )
        if (
            coordination.writer != expected_writer
            or expected_writer is None
            or expected_writer.kind not in {"build", "handoff"}
            or coordination.publication_lease is not None
            or coordination.worktree_cleanup_intent is not None
            or coordination.worktree_cleanup is not None
            or coordination.dirty_worktree_quarantine is not None
            or coordination.target_sync_conflict is not None
            or coordination.external_head_adoption_intent is not None
        ):
            _coordination_conflict("Builder handoff workspace is not under exact exclusive custody")
        captured, head, status, paths, reason = self.capture_recovery_workspace_metadata(
            coordination.change_id, (), ignored_is_dirty=False
        )
        if captured != coordination:
            _coordination_conflict("Change custody changed during Builder handoff metadata capture")
        if reason not in {None, "workspace-dirty"}:
            message = "Builder handoff workspace failed metadata preflight"
            raise PreservationFenceError(message)
        if not self._is_ancestor(coordination.last_reviewed_commit, head, cwd=self._repository):
            message = "Builder handoff head is not descended from the reviewed boundary"
            raise PreservationFenceError(message)
        return self._capture_builder_handoff_metadata_details(coordination, head, status, paths)

    def _capture_builder_handoff_metadata_details(
        self,
        coordination: ChangeCoordination,
        head: str,
        status: bytes,
        paths: tuple[str, ...],
    ) -> BuilderHandoffMetadata:
        worktree = self._canonical_worktree_path(coordination.change_id, coordination.worktree_path)
        self._require_worktree(coordination.change_id, worktree, coordination.branch, head)
        registration = self._registered_worktrees_all().get(worktree.resolve())
        if registration is None or registration.head != head or registration.branch != coordination.branch:
            message = "Builder handoff worktree registration changed"
            raise PreservationFenceError(message)
        current_status = self._preservation_git(
            "status", "--porcelain=v1", "-z", "--untracked-files=all", cwd=worktree
        ).stdout
        if current_status != status:
            message = "Builder handoff worktree status changed during metadata capture"
            raise PreservationFenceError(message)
        managed_index = self._resolve_managed_index(worktree)
        index_bytes = self._read_managed_index(managed_index)
        if self._resolve_managed_index(worktree) != managed_index:
            message = "Builder handoff managed index changed during metadata capture"
            raise PreservationFenceError(message)
        index_digest = hashlib.sha256(index_bytes).hexdigest()
        status_digest = hashlib.sha256(status).hexdigest()
        path_metadata = tuple((path, *self._read_worktree_handoff_metadata(worktree, path)) for path in paths)
        return BuilderHandoffMetadata(
            change_id=coordination.change_id,
            branch=coordination.branch,
            worktree_path=worktree,
            last_reviewed_commit=coordination.last_reviewed_commit,
            branch_head=head,
            registration=registration,
            managed_index=managed_index,
            index_digest=index_digest,
            status_digest=status_digest,
            path_metadata=path_metadata,
        )

    def observe_worktree_activity(self, change_id: str) -> datetime:
        """Return the newest change time of a registered Change worktree without refreshing Git state.

        Every non-ignored directory and entry counts, so nested deletions are visible. Git's collapsed
        ignored entries count only by their own times: writes deeper inside an ignored directory (tool
        caches, environments) are not observed. Raises when any observation is unreadable, unsafe or
        exceeds its bound; callers must treat that as active.
        """
        coordination = self._coordinator.show(change_id)
        worktree = self._canonical_worktree_path(change_id, coordination.worktree_path)
        registration = self._registered_worktrees_all().get(worktree.resolve())
        if registration is None or registration.branch != coordination.branch:
            msg = "worker worktree registration does not match its Change"
            raise PreservationRejectedError(msg)
        ignored = self._ignored_inventory_paths(
            self._preservation_git(
                "status", "--porcelain=v1", "-z", "--ignored=matching", "--untracked-files=normal", cwd=worktree
            ).stdout
        )
        newest = _worktree_tree_activity_ns(worktree, ignored)
        managed_index = self._resolve_managed_index(worktree)
        newest = max(newest, _activity_ns(managed_index.path), _activity_ns(managed_index.administration))
        roots = (managed_index.administration, managed_index.common_directory)
        newest = max(newest, _activity_ns(self._resolved_git_path(worktree, "HEAD", roots)))
        reference = self._resolved_git_path(worktree, f"refs/heads/{coordination.branch}", roots, missing_ok=True)
        if reference is None:
            reference = self._resolved_git_path(worktree, "packed-refs", roots)
        newest = max(newest, _activity_ns(reference))
        return datetime.fromtimestamp(newest / 1_000_000_000, tz=UTC)

    def _resolved_git_path(
        self,
        worktree: Path,
        name: str,
        roots: tuple[Path, ...],
        *,
        missing_ok: bool = False,
    ) -> Path | None:
        path = Path(
            self._preservation_git("rev-parse", "--path-format=absolute", "--git-path", name, cwd=worktree)
            .stdout.decode()
            .strip()
        )
        if not path.is_absolute() or ".." in path.parts or not any(_path_is_contained(root, path) for root in roots):
            msg = "Git resolved an unexpected worktree administration path"
            raise PreservationRejectedError(msg)
        if path.with_name(f"{path.name}.lock").exists():
            msg = "Git administration path is locked by an active operation"
            raise PreservationRejectedError(msg)
        if missing_ok and not path.exists() and not path.is_symlink():
            return None
        _reject_symlink_ancestors(path)
        return path

    def ensure(
        self,
        change_id: str,
        *,
        recovery_reviewed_head: str | None = None,
    ) -> ChangeCoordination:
        """Ensure one healthy warm branch and worktree without repairing degraded state."""
        self._require_preservation_environment()
        if not _is_change_id(change_id):
            msg = "change identity is not a safe worktree identity"
            raise ValueError(msg)
        existing = self._coordinator.find_registered(change_id)
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
            publication_base_head=target_head,
            last_reviewed_commit=last_reviewed_commit,
        )
        return self._coordinator.register(coordination)

    def recover(self, change_id: str, recovery_reviewed_head: str) -> ChangeCoordination:
        """Recreate one absent managed Change worktree from exact reviewed authority."""
        self._require_preservation_environment()
        if not _is_change_id(change_id):
            msg = "change identity is not a safe worktree identity"
            raise ValueError(msg)
        if re.fullmatch(r"[0-9a-f]{40}", recovery_reviewed_head) is None:
            msg = "recovery reviewed head is not a valid commit identity"
            raise ValueError(msg)
        existing = self._coordinator.find_registered(change_id)
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
        self._require_preservation_environment()
        if not _is_change_id(change_id):
            msg = "change identity is not a safe worktree identity"
            raise ValueError(msg)
        existing = self._coordinator.find_registered(change_id)
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

    def recover_out_of_band_head(  # noqa: C901, PLR0912 - recovery binds exact staged Git states.
        self,
        request: RecoverOutOfBandHead,
    ) -> OutOfBandHeadRecoveryReceipt:
        """Preserve an out-of-band head and restore the managed branch to review authority."""
        self._require_preservation_environment()
        with self._coordinator.publication_lock(request.change_id) as lock:
            coordination = self._coordinator.show(request.change_id)
            if coordination.writer is not None or coordination.publication_lease is not None:
                _coordination_conflict("out-of-band head recovery cannot overlap active Change custody")
            existing = coordination.out_of_band_head_recovery
            if existing is not None:
                if (
                    existing.operation_id != request.operation_id
                    or existing.expected_reviewed_head != request.expected_reviewed_head
                    or existing.expected_remote_head != request.expected_remote_head
                    or existing.observed_branch_head != request.expected_branch_head
                ):
                    _coordination_conflict("out-of-band head recovery request differs from its receipt")
                if self._resolve(existing.preserved_ref) != existing.preserved_head:
                    _coordination_conflict("out-of-band head recovery evidence is missing")
                self._require_worktree(
                    request.change_id,
                    coordination.worktree_path,
                    coordination.branch,
                    existing.restored_head,
                )
                return existing
            if coordination.last_reviewed_commit != request.expected_reviewed_head:
                _coordination_conflict("out-of-band head recovery requires the current reviewed boundary")
            branch_head = self._resolve(coordination.branch)
            if branch_head not in {request.expected_branch_head, request.expected_reviewed_head}:
                _coordination_conflict("out-of-band head recovery branch head changed")
            preserved_ref = f"refs/owlbear/recovery/{request.change_id}/{request.operation_id}"
            self._git("check-ref-format", preserved_ref)
            preserved = self._resolve(preserved_ref, missing_ok=True)
            if branch_head == request.expected_reviewed_head:
                if preserved != request.expected_branch_head:
                    _coordination_conflict("out-of-band head recovery evidence is missing")
            else:
                self._require_ancestor(request.expected_reviewed_head, branch_head)
            worktree_head = self._resolve("HEAD", cwd=coordination.worktree_path, missing_ok=True)
            if branch_head == request.expected_reviewed_head and worktree_head == request.expected_branch_head:
                self._require_clean_worktree(
                    coordination.worktree_path,
                    operation="out-of-band head recovery",
                )
            else:
                self._require_worktree(
                    request.change_id,
                    coordination.worktree_path,
                    coordination.branch,
                    branch_head,
                )
                self._require_clean_worktree(
                    coordination.worktree_path,
                    operation="out-of-band head recovery",
                )
            if preserved is None:
                self._git("update-ref", preserved_ref, branch_head, "0" * 40)
                preserved = branch_head
            elif preserved != request.expected_branch_head:
                _coordination_conflict("out-of-band head recovery ref names another branch head")
            if branch_head != request.expected_reviewed_head:
                self._git(
                    "update-ref",
                    f"refs/heads/{coordination.branch}",
                    request.expected_reviewed_head,
                    branch_head,
                )
                self._git(
                    "reset",
                    "--hard",
                    request.expected_reviewed_head,
                    cwd=coordination.worktree_path,
                )
            elif worktree_head != request.expected_reviewed_head:
                self._git(
                    "reset",
                    "--hard",
                    request.expected_reviewed_head,
                    cwd=coordination.worktree_path,
                )
            else:
                self._require_worktree(
                    request.change_id,
                    coordination.worktree_path,
                    coordination.branch,
                    request.expected_reviewed_head,
                )
            receipt = OutOfBandHeadRecoveryReceipt.create(
                operation_id=request.operation_id,
                change_id=request.change_id,
                branch=coordination.branch,
                worktree_path=coordination.worktree_path,
                expected_reviewed_head=request.expected_reviewed_head,
                expected_remote_head=request.expected_remote_head,
                observed_branch_head=branch_head,
                preserved_ref=preserved_ref,
                preserved_head=preserved,
                restored_head=request.expected_reviewed_head,
            )
            self._coordinator.update(
                coordination.model_copy(update={"out_of_band_head_recovery": receipt}),
                lock=lock,
            )
            return receipt

    def prepare_finalization_boundary(
        self,
        change_id: str,
        exact_head: str,
        promoted_commits: tuple[str, ...],
        lock: PublicationLock,
        *,
        completion: tuple[str, str] | None = None,
    ) -> ReplacementTransactionParticipant | None:
        """Prepare a reviewed-boundary advance for one clean finalization head."""
        current = self._coordinator.show(change_id)
        attempt = current.finalization_attempt
        active = attempt is not None and attempt.finished_at is None
        if active and (
            completion is None
            or attempt.writer.attempt_id != completion[0]
            or attempt.exact_head != exact_head
            or attempt.target_head != self.observed_target_head()
        ):
            _coordination_conflict("finalization attempt or target head changed")
        coordination = self.validate_finalization_head(
            change_id, exact_head, promoted_commits, expected_writer=attempt.writer if active else None
        )
        adoption = coordination.external_head_adoption_receipt
        if active:
            reviewed_head = (
                coordination.last_reviewed_commit
                if adoption is not None and adoption.adopted_head == exact_head
                else exact_head
            )
            return self._coordinator.prepare_finalization_completion(coordination, reviewed_head, completion[1], lock)
        if coordination.last_reviewed_commit == exact_head or (
            adoption is not None and adoption.adopted_head == exact_head
        ):
            return None
        return self._coordinator.prepare_reviewed_boundary(coordination, exact_head, lock)

    def snapshot_design_package(
        self,
        change_id: str,
        package_id: str,
        package_files: Mapping[str, bytes],
        operation_id: str,
        expected_existing_receipt_id: str | None = None,
    ) -> ChangeDesignPackageSnapshotReceipt:
        """Commit one verified admitted Design package on its managed Change branch."""
        if set(package_files) != set(_DESIGN_PACKAGE_NAMES):
            _workspace_failure("Design package snapshot must contain the canonical package files")
        if not _DIGEST_PATTERN.fullmatch(package_id):
            _workspace_failure("Design package snapshot identity is invalid")
        with self._coordinator.publication_lock(change_id) as lock:
            coordination = self._coordinator.show(change_id)
            existing = coordination.design_package_snapshot
            if existing is not None:
                if existing.package_id == package_id:
                    self._validate_design_package_snapshot_replay(existing, package_id)
                    return existing
                if expected_existing_receipt_id != existing.receipt_id:
                    _coordination_conflict("Design package snapshot differs from the expected receipt")
                return self._replace_design_package_snapshot(
                    coordination,
                    package_id,
                    package_files,
                    operation_id,
                    lock=lock,
                )
            intent = coordination.design_package_snapshot_intent
            branch_head = self._resolve(coordination.branch)
            if intent is None:
                if branch_head != coordination.last_reviewed_commit:
                    _workspace_failure("Design package snapshot requires the reviewed Change branch head")
                intent = ChangeDesignPackageSnapshotIntent.create(
                    operation_id=operation_id,
                    change_id=change_id,
                    package_id=package_id,
                    branch=coordination.branch,
                    worktree_path=coordination.worktree_path,
                    expected_head=branch_head,
                )
                coordination = self._coordinator.update(
                    coordination.model_copy(update={"design_package_snapshot_intent": intent}),
                    lock=lock,
                )
            elif intent.operation_id != operation_id or intent.package_id != package_id:
                _coordination_conflict("Design package snapshot intent differs from the request")
            snapshot_head = self._commit_design_package_snapshot(coordination, intent, package_files, branch_head)
            receipt = ChangeDesignPackageSnapshotReceipt.create(
                operation_id=operation_id,
                change_id=change_id,
                package_id=package_id,
                branch=coordination.branch,
                worktree_path=coordination.worktree_path,
                previous_head=intent.expected_head,
                snapshot_head=snapshot_head,
            )
            current = self._coordinator.show(change_id)
            updated = current.model_copy(
                update={
                    "design_package_snapshot_intent": None,
                    "design_package_snapshot": receipt,
                    "last_reviewed_commit": snapshot_head,
                }
            )
            self._coordinator.update(updated, lock=lock)
            return receipt

    def _replace_design_package_snapshot(
        self,
        coordination: ChangeCoordination,
        package_id: str,
        package_files: Mapping[str, bytes],
        operation_id: str,
        *,
        lock: PublicationLock,
    ) -> ChangeDesignPackageSnapshotReceipt:
        """Replace one exact package snapshot after an admitted Design revision."""
        existing = coordination.design_package_snapshot
        if existing is None:
            _coordination_conflict("Design package snapshot replacement requires an existing snapshot")
        if coordination.writer is not None:
            _coordination_conflict("Design package snapshot replacement cannot overlap an active writer")
        branch_head = self._resolve(coordination.branch)
        intent = coordination.design_package_snapshot_intent
        if intent is None:
            if branch_head != existing.snapshot_head:
                _workspace_failure("Design package snapshot branch moved before replacement")
            intent = ChangeDesignPackageSnapshotIntent.create(
                operation_id=operation_id,
                change_id=coordination.change_id,
                package_id=package_id,
                branch=coordination.branch,
                worktree_path=coordination.worktree_path,
                expected_head=existing.snapshot_head,
            )
            coordination = self._coordinator.update(
                coordination.model_copy(update={"design_package_snapshot_intent": intent}),
                lock=lock,
            )
        elif intent.operation_id != operation_id or intent.package_id != package_id:
            _coordination_conflict("Design package snapshot replacement intent differs from the request")
        snapshot_head = self._commit_design_package_snapshot(coordination, intent, package_files, branch_head)
        receipt = ChangeDesignPackageSnapshotReceipt.create(
            operation_id=operation_id,
            change_id=coordination.change_id,
            package_id=package_id,
            branch=coordination.branch,
            worktree_path=coordination.worktree_path,
            previous_head=intent.expected_head,
            snapshot_head=snapshot_head,
        )
        current = self._coordinator.show(coordination.change_id)
        updated = current.model_copy(
            update={
                "design_package_snapshot_intent": None,
                "design_package_snapshot": receipt,
                "last_reviewed_commit": snapshot_head,
            }
        )
        self._coordinator.update(updated, lock=lock)
        return receipt

    def _validate_design_package_snapshot_replay(
        self,
        receipt: ChangeDesignPackageSnapshotReceipt,
        package_id: str,
    ) -> None:
        if receipt.package_id != package_id:
            _coordination_conflict("Design package snapshot differs from the request")
        self._require_worktree(
            receipt.change_id,
            receipt.worktree_path,
            receipt.branch,
            receipt.snapshot_head,
        )
        self._require_clean_worktree(receipt.worktree_path)

    def _commit_design_package_snapshot(
        self,
        coordination: ChangeCoordination,
        intent: ChangeDesignPackageSnapshotIntent,
        package_files: Mapping[str, bytes],
        branch_head: str | None,
    ) -> str:
        worktree = coordination.worktree_path
        relative_paths = tuple(
            f".owlbear/delivery/packages/{coordination.change_id}/{name}" for name in _DESIGN_PACKAGE_NAMES
        )
        existing = {
            name: self._read_optional_worktree_file(worktree / relative_path)
            for name, relative_path in zip(_DESIGN_PACKAGE_NAMES, relative_paths, strict=True)
        }
        if branch_head == intent.expected_head and self._package_files_match_commit(
            intent.expected_head,
            relative_paths,
            existing,
            package_files,
        ):
            return intent.expected_head
        if branch_head != intent.expected_head:
            return self._replay_design_package_snapshot(coordination, intent, package_files, branch_head)
        self._require_worktree(coordination.change_id, worktree, coordination.branch, intent.expected_head)
        self._require_clean_worktree(worktree)
        committed = False
        try:
            self._write_design_package_files(worktree, relative_paths, package_files)
            self._git("add", "-f", "--", *relative_paths, cwd=worktree)
            message = f"chore: snapshot admitted Design package ({coordination.change_id}, {intent.operation_id})"
            result = self._run_git(
                "commit",
                "--only",
                "-m",
                message,
                "--",
                *relative_paths,
                cwd=worktree,
                check=False,
            )
            if result.returncode != 0:
                _workspace_failure("Design package snapshot could not be committed")
            committed = True
        except Exception:
            if not committed:
                self._restore_worktree_files(worktree, relative_paths, existing)
            raise
        else:
            snapshot_head = self._resolve("HEAD", cwd=worktree)
            if snapshot_head is None:
                _workspace_failure("Design package snapshot commit has no resolvable head")
            self._require_clean_worktree(worktree)
            current = {
                name: self._read_optional_worktree_file(worktree / relative_path)
                for name, relative_path in zip(_DESIGN_PACKAGE_NAMES, relative_paths, strict=True)
            }
            if not self._package_files_match_commit(snapshot_head, relative_paths, current, package_files):
                _workspace_failure("Design package snapshot committed unexpected package bytes")
            changed = self._git(
                "diff-tree",
                "--no-commit-id",
                "--name-only",
                "-r",
                snapshot_head,
                cwd=worktree,
            ).splitlines()
            if not changed or not set(changed).issubset(set(relative_paths)):
                _workspace_failure("Design package snapshot committed an unexpected path")
            return snapshot_head

    def _replay_design_package_snapshot(
        self,
        coordination: ChangeCoordination,
        intent: ChangeDesignPackageSnapshotIntent,
        package_files: Mapping[str, bytes],
        branch_head: str,
    ) -> str:
        """Recover a package snapshot after its commit succeeded before receipt storage."""
        if not self._is_direct_child(intent.expected_head, branch_head):
            _workspace_failure("Design package snapshot branch changed before its commit")
        self._require_clean_worktree(coordination.worktree_path)
        relative_paths = tuple(
            f".owlbear/delivery/packages/{coordination.change_id}/{name}" for name in _DESIGN_PACKAGE_NAMES
        )
        existing = {
            name: self._read_optional_worktree_file(coordination.worktree_path / relative_path)
            for name, relative_path in zip(_DESIGN_PACKAGE_NAMES, relative_paths, strict=True)
        }
        if not self._package_files_match_commit(branch_head, relative_paths, existing, package_files):
            _workspace_failure("Design package snapshot commit does not match its package")
        message = f"chore: snapshot admitted Design package ({coordination.change_id}, {intent.operation_id})"
        if self._git("log", "-1", "--format=%s", branch_head, cwd=coordination.worktree_path) != message:
            _workspace_failure("Design package snapshot branch commit is not replayable")
        return branch_head

    def _package_files_match_commit(
        self,
        commit: str,
        relative_paths: tuple[str, ...],
        existing: Mapping[str, bytes | None],
        package_files: Mapping[str, bytes],
    ) -> bool:
        tracked = self._git("ls-tree", "-r", "--name-only", commit, "--", *relative_paths).splitlines()
        return set(tracked) == set(relative_paths) and all(
            self._git_blob_bytes(commit, relative_path) == package_files[name] and existing[name] == package_files[name]
            for name, relative_path in zip(_DESIGN_PACKAGE_NAMES, relative_paths, strict=True)
        )

    def _git_blob_bytes(self, commit: str, relative_path: str) -> bytes:
        result = self._run_git("show", f"{commit}:{relative_path}", check=False)
        return result.stdout if result.returncode == 0 else b""

    def _is_direct_child(self, parent: str, commit: str) -> bool:
        parents = self._git("rev-list", "--parents", "-n", "1", commit).split()
        return len(parents) == _COMMIT_PARENT_COUNT and parents[1] == parent

    @staticmethod
    def _read_optional_worktree_file(path: Path) -> bytes | None:
        if path.is_symlink() or (path.exists() and not path.is_file()):
            _workspace_failure("Design package snapshot path is unsafe")
        return path.read_bytes() if path.exists() else None

    @staticmethod
    def _write_design_package_files(
        worktree: Path,
        relative_paths: tuple[str, ...],
        package_files: Mapping[str, bytes],
    ) -> None:
        for name, relative_path in zip(_DESIGN_PACKAGE_NAMES, relative_paths, strict=True):
            path = worktree / relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(package_files[name])

    def _restore_worktree_files(
        self,
        worktree: Path,
        relative_paths: tuple[str, ...],
        existing: Mapping[str, bytes | None],
    ) -> None:
        self._git("reset", "HEAD", "--", *relative_paths, cwd=worktree, check=False)
        for name, relative_path in zip(_DESIGN_PACKAGE_NAMES, relative_paths, strict=True):
            path = worktree / relative_path
            previous = existing[name]
            if previous is None:
                path.unlink(missing_ok=True)
            else:
                path.write_bytes(previous)

    @classmethod
    def restore_worktree(cls, repository: Path, worktree: Path, branch: str) -> None:
        """Restore one absent managed worktree from its retained branch."""
        cls._require_preservation_environment()
        resolved_repository = repository.resolve()
        cls._register_worktree(
            worktree,
            branch,
            lambda *arguments: cls._run_managed_git(resolved_repository, *arguments),
        )

    @classmethod
    def remove_worktree(cls, repository: Path, worktree: Path, *, force: bool = False) -> None:
        """Remove one managed worktree through Git's registration-aware operation."""
        cls._require_preservation_environment()
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

    def inspect_retained(self, change_id: str, coordination: ChangeCoordination) -> RetainedChangeWorktree:
        """Inspect one retained Change worktree without enumerating other coordination records."""
        if coordination.change_id != change_id:
            _coordination_conflict("Change workspace inspection identity does not match coordination")
        return self._retained_worktree(
            change_id,
            coordination,
            self._registered_worktrees().get(change_id),
            self._change_branch_heads().get(change_id),
            include_content_attention=True,
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
        if coordination.recovery_owner_id is not None:
            raise DeliveryWorkerExclusionRequiredError
        if coordination.continuation_action is not None and coordination.continuation_action.finished_at is None:
            _coordination_conflict("Change worktree recovery cannot overlap retained engine custody")
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
        self._require_preservation_environment()
        coordination = self._coordinator.show(change_id)
        target_head = self._resolve(self._target_ref())
        if target_head == coordination.target_head:
            return coordination
        return self._coordinator.update(coordination.model_copy(update={"target_head": target_head}))

    def recover_publication_baseline(
        self,
        change_id: str,
        expected_change_head: str,
        publication_base_head: str,
        operation_id: str,
    ) -> PublicationBaselineRecoveryReceipt:
        """Persist one explicitly confirmed baseline for publication authority."""
        self._require_preservation_environment()
        if _COMMIT_PATTERN.fullmatch(expected_change_head) is None:
            message = "expected Change head is not an exact commit identity"
            raise ValueError(message)
        if _COMMIT_PATTERN.fullmatch(publication_base_head) is None:
            message = "publication baseline is not an exact commit identity"
            raise ValueError(message)
        request = RecoverPublicationBaseline(
            change_id=change_id,
            expected_change_head=expected_change_head,
            publication_base_head=publication_base_head,
            operation_id=operation_id,
        )
        with self._coordinator.publication_lock(change_id) as lock:
            coordination = self._coordinator.show(change_id)
            if coordination.writer is not None or coordination.publication_lease is not None:
                _coordination_conflict("publication baseline recovery requires an idle Change")
            existing = coordination.publication_baseline_recovery
            candidate = PublicationBaselineRecoveryReceipt.create(**request.model_dump())
            if existing is not None:
                if existing == candidate:
                    return existing
                _coordination_conflict("publication baseline recovery operation already has different authority")
            if coordination.publication_base_head is not None:
                _coordination_conflict("publication baseline is already known")
            branch_head = self._resolve(coordination.branch)
            if branch_head != expected_change_head or coordination.last_reviewed_commit != expected_change_head:
                _coordination_conflict("publication baseline recovery head is stale")
            self._require_worktree(change_id, coordination.worktree_path, coordination.branch, expected_change_head)
            self._require_clean_worktree(coordination.worktree_path)
            baseline = self._resolve(publication_base_head, missing_ok=True)
            if baseline is None:
                raise PublicationBaselineUnavailableError(change_id, "publication baseline commit cannot be resolved")
            if not self._is_ancestor(baseline, expected_change_head, cwd=self._repository):
                raise PublicationBaselineUnavailableError(
                    change_id,
                    "publication baseline is not an ancestor of the reviewed Change head",
                )
            self._coordinator.update(
                coordination.model_copy(
                    update={
                        "publication_base_head": baseline,
                        "publication_baseline_recovery": candidate,
                    }
                ),
                lock=lock,
            )
            return candidate

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
        action = coordination.continuation_action
        attention_sync = (
            self._coordinator.executing_continuation(request.change_id)
            and action is not None
            and action.operation_id == request.operation_id
            and action.target_head == request.expected_target
            and _is_settled_finalizer_attention_sync(coordination, action)
        )
        updates = {"target_sync_receipt": None, "target_sync_conflict": conflict}
        if attention_sync:
            updates.update({"writer": None, "finalization_attention": None})
        self._coordinator.update(coordination.model_copy(update=updates), lock=lock)
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
    ) -> bool:
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
        action = coordination.continuation_action
        attention_sync = (
            self._coordinator.executing_continuation(request.change_id)
            and action is not None
            and action.operation_id == request.operation_id
            and action.target_head == request.expected_target
            and _is_settled_finalizer_attention_sync(coordination, action)
        )
        if coordination.writer is not None and not attention_sync:
            _coordination_conflict("target synchronization cannot overlap an active writer")
        if coordination.publication_lease is not None:
            _coordination_conflict("target synchronization cannot overlap a publication lease")
        branch_head = self._resolve(coordination.branch)
        if branch_head != coordination.last_reviewed_commit:
            _coordination_conflict("target synchronization requires the reviewed Change head")
        return attention_sync

    def sync_with_target(
        self,
        request: SyncChangeWithTarget,
        before_head_change: Callable[[], None] | None = None,
    ) -> ChangeTargetSyncReceipt:
        """Fetch one exact target head and merge it only in the managed Change worktree."""
        with (
            locked_roots((self._coordinator.runtime_root / "coordination" / "target-sync-lock",)),
            self._coordinator.publication_lock(request.change_id) as lock,
        ):
            coordination = self._coordinator.show(request.change_id)
            previous_receipt = self._replay_target_sync_receipt(request, coordination)
            if previous_receipt is not None:
                return previous_receipt
            attention_sync = self._require_target_sync_start(request, coordination)
            branch_head = self._resolve(coordination.branch)
            self._require_worktree(
                request.change_id,
                coordination.worktree_path,
                coordination.branch,
                branch_head,
            )
            merge_head = self._resolve("MERGE_HEAD", cwd=coordination.worktree_path, missing_ok=True)
            if merge_head is not None and merge_head != request.expected_target:
                _coordination_conflict("preserved target synchronization conflict target differs from the request")
            if merge_head is not None:
                self._persist_target_sync_conflict(
                    request,
                    coordination,
                    lock,
                    merge_head,
                    branch_head,
                )
            if self._git(
                "--no-optional-locks",
                "status",
                "--porcelain=v1",
                "-z",
                "--untracked-files=all",
                cwd=coordination.worktree_path,
            ):
                _workspace_failure("target synchronization requires a clean Change worktree")
            source_ref, _target_ref, target_branch = self._target_refs()
            target_head = self._fetch_target(source_ref, target_branch, request.expected_target)
            branch_head = self._resolve(coordination.branch)
            self._require_worktree(
                request.change_id,
                coordination.worktree_path,
                coordination.branch,
                branch_head,
            )
            if (
                not self._is_ancestor(target_head, branch_head, cwd=coordination.worktree_path)
                and before_head_change is not None
            ):
                before_head_change()
            merge = self._run_git(
                "merge",
                "--no-edit",
                "--",
                target_head,
                cwd=coordination.worktree_path,
                check=False,
            )
            if merge.returncode != 0:
                merge_head = self._resolve("MERGE_HEAD", cwd=coordination.worktree_path, missing_ok=True)
                if merge_head is not None:
                    self._persist_target_sync_conflict(
                        request,
                        coordination,
                        lock,
                        merge_head,
                        branch_head,
                    )
                _workspace_failure("target synchronization merge failed")
            merged_head = self._resolve(coordination.branch)
            inherited_review_requirement = (
                coordination.target_sync_receipt.review_required
                if coordination.target_sync_receipt is not None
                else False
            )
            receipt = ChangeTargetSyncReceipt.create(
                operation_id=request.operation_id,
                change_id=request.change_id,
                integration_target=coordination.integration_target,
                expected_target=request.expected_target,
                target_head=target_head,
                change_head_before=branch_head,
                merged_head=merged_head,
                merge_commit=self._is_merge_commit(merged_head, coordination.worktree_path),
                review_required=inherited_review_requirement or attention_sync,
            )
            updates = {
                "target_head": target_head,
                "target_sync_conflict": None,
                "target_sync_receipt": receipt,
                "target_sync_abort_receipt": None,
                "last_reviewed_commit": merged_head,
            }
            if attention_sync:
                updates.update({"writer": None, "finalization_attention": None})
            self._coordinator.update(
                coordination.model_copy(update=updates),
                lock=lock,
            )
            return receipt

    def adopt_external_head(
        self,
        request: AdoptExternalHead,
        before_head_change: Callable[[], None] | None = None,
    ) -> ChangeExternalHeadAdoptionReceipt:
        """Adopt one exact descendant from the remote Change branch without advancing review authority."""
        with self._coordinator.publication_lock(request.change_id) as lock:
            coordination = self._coordinator.show(request.change_id)
            replayed = self._replay_external_head_adoption(request, coordination)
            if replayed is not None:
                return replayed
            coordination = self._prepare_external_head_adoption(request, coordination)

            branch_head = self._resolve(coordination.branch)
            if branch_head == request.adopted_head:
                provenance: Literal["fast-forward", "observed"] = "fast-forward"
                if coordination.external_head_adoption_intent is None:
                    self._fetch_external_head(coordination.branch, request.adopted_head)
                    provenance = "observed"
                self._require_ancestor(request.expected_head, branch_head)
                self._require_worktree(
                    request.change_id,
                    coordination.worktree_path,
                    coordination.branch,
                    branch_head,
                )
                self._require_clean_worktree(
                    coordination.worktree_path,
                    operation="external Change-head adoption",
                )
                return self._complete_external_head_adoption(
                    request,
                    coordination,
                    lock,
                    provenance=provenance,
                )
            if branch_head != request.expected_head:
                _coordination_conflict(
                    "external Change head adoption requires the managed Change branch to equal either "
                    f"the reviewed head {request.expected_head} or requested adopted head "
                    f"{request.adopted_head}; observed branch head is {branch_head}"
                )
            return self._fast_forward_external_head(request, coordination, lock, before_head_change)

    def _prepare_external_head_adoption(
        self,
        request: AdoptExternalHead,
        coordination: ChangeCoordination,
    ) -> ChangeCoordination:
        self._require_external_head_adoption_start(coordination, request)
        intent = coordination.external_head_adoption_intent
        expected_intent = ChangeExternalHeadAdoptionIntent.create(request, coordination.branch)
        if intent is not None:
            if intent != expected_intent:
                _coordination_conflict("external Change head adoption intent differs from the request")
            return coordination
        current = coordination.external_head_adoption_receipt
        if (
            current is not None
            and current.operation_id != request.operation_id
            and current.expected_head == request.expected_head
            and current.adopted_head == request.adopted_head
        ):
            _coordination_conflict("external Change head adoption was already recorded for the requested head")
        if request.expected_head != coordination.last_reviewed_commit:
            _coordination_conflict("external Change head adoption requires the reviewed branch head")
        self._require_ancestor(coordination.last_reviewed_commit, request.expected_head)
        branch_head = self._resolve(coordination.branch)
        self._require_worktree(
            request.change_id,
            coordination.worktree_path,
            coordination.branch,
            branch_head,
        )
        self._require_clean_worktree(
            coordination.worktree_path,
            operation="external Change-head adoption",
        )
        return coordination

    def _fast_forward_external_head(
        self,
        request: AdoptExternalHead,
        coordination: ChangeCoordination,
        lock: PublicationLock,
        before_head_change: Callable[[], None] | None,
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
        if before_head_change is not None:
            before_head_change()
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
        self._require_clean_worktree(
            coordination.worktree_path,
            operation="external Change-head adoption",
        )
        return self._complete_external_head_adoption(
            request,
            coordination,
            lock,
            adopted_head,
            provenance="fast-forward",
        )

    def _complete_external_head_adoption(
        self,
        request: AdoptExternalHead,
        coordination: ChangeCoordination,
        lock: PublicationLock,
        adopted_head: str | None = None,
        provenance: Literal["fast-forward", "observed"] = "fast-forward",
    ) -> ChangeExternalHeadAdoptionReceipt:
        receipt = ChangeExternalHeadAdoptionReceipt.create(
            operation_id=request.operation_id,
            change_id=request.change_id,
            branch=coordination.branch,
            expected_head=request.expected_head,
            adopted_head=adopted_head or request.adopted_head,
            provenance=provenance,
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
        self._require_clean_worktree(
            coordination.worktree_path,
            operation="external Change-head adoption",
        )
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

    def _require_external_head_adoption_start(
        self,
        coordination: ChangeCoordination,
        request: AdoptExternalHead,
    ) -> None:
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
            if branch_head not in {request.expected_head, request.adopted_head}:
                _coordination_conflict(
                    "external Change head adoption requires the managed Change branch to equal either "
                    f"the reviewed head {request.expected_head} or requested adopted head "
                    f"{request.adopted_head}; observed branch head is {branch_head}"
                )

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
                review_required=True,
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

    def repository_automation_paths(self, change_id: str, exact_head: str) -> tuple[str, ...]:
        """Return repository automation paths changed since the publication baseline."""
        coordination = self._coordinator.show(change_id)
        if _COMMIT_PATTERN.fullmatch(exact_head) is None:
            _workspace_failure("automation summary head is not an exact commit identity")
        baseline = (
            None
            if coordination.publication_base_head is None
            else self._resolve(coordination.publication_base_head, missing_ok=True)
        )
        if baseline is None:
            raise PublicationBaselineUnavailableError(
                change_id,
                "publication automation summary requires an explicitly known baseline",
            )
        resolved_head = self._resolve(exact_head, missing_ok=True)
        if resolved_head is None:
            raise PublicationBaselineUnavailableError(change_id, "published Change head cannot be resolved")
        if resolved_head != exact_head:
            _workspace_failure("automation summary head does not resolve to the requested commit")
        if not self._is_ancestor(baseline, resolved_head, cwd=self._repository):
            raise PublicationBaselineUnavailableError(
                change_id,
                "publication baseline is not an ancestor of the published Change head",
            )
        result = self._run_git(
            "diff",
            "--no-ext-diff",
            "--no-textconv",
            "--no-renames",
            "--name-only",
            "-z",
            baseline,
            resolved_head,
            "--",
            ".github/workflows",
            ":(glob)**/action.yml",
            ":(glob)**/action.yaml",
            check=False,
        )
        if result.returncode != 0:
            _workspace_failure("repository automation paths could not be derived")
        paths = {path for path in result.stdout.split(b"\0") if path}
        return tuple(os.fsdecode(path) for path in sorted(paths))

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
            message = "target changed while it was fetched"
            raise ChangeTargetSyncStaleError(message)
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

    def _require_clean_worktree(self, worktree: Path, *, operation: str = "target synchronization") -> None:
        if self._git("-C", str(worktree), "status", "--porcelain=v1").strip():
            _workspace_failure(f"{operation} worktree is not clean")

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

    def source_head(
        self,
        change_id: str,
        *,
        require_clean: bool = True,
        builder_handoff_source: BuilderHandoffSource | None = None,
    ) -> str:
        """Return one source head at the reviewed or durably adopted boundary."""
        coordination = self._coordinator.show(change_id)
        if builder_handoff_source is not None:
            return self._builder_handoff_source_head(coordination, builder_handoff_source)
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
        if require_clean and self._git("-C", str(coordination.worktree_path), "status", "--porcelain"):
            _workspace_failure("change source worktree is not clean")
        return branch_head

    def _builder_handoff_source_head(
        self,
        coordination: ChangeCoordination,
        source: BuilderHandoffSource,
    ) -> str:
        retained = source.retained_handoff
        if retained is None:
            if (
                coordination.builder_handoff is not None
                or coordination.writer is None
                or (coordination.writer.kind != "build")
            ):
                _coordination_conflict("active Builder handoff source has no exact successor writer")
            if coordination.last_reviewed_commit != source.last_reviewed_commit:
                _coordination_conflict("active Builder handoff reviewed boundary changed")
            branch_head = self._resolve(coordination.branch)
            if not (
                self._is_ancestor(source.branch_head, branch_head, cwd=self._repository)
                and self._is_ancestor(source.last_reviewed_commit, branch_head, cwd=self._repository)
            ):
                message = "active Builder handoff branch no longer descends from its captured boundary"
                raise PreservationFenceError(message)
            worktree = self._canonical_worktree_path(coordination.change_id, coordination.worktree_path)
            self._require_worktree(coordination.change_id, worktree, coordination.branch, branch_head)
            registration = self._registered_worktrees_all().get(worktree.resolve())
            if registration is None or registration.head != branch_head or registration.branch != coordination.branch:
                message = "active Builder handoff worktree registration changed"
                raise PreservationFenceError(message)
            return branch_head
        if (
            coordination.builder_handoff != retained
            or retained.settlement_id != source.settlement_id
            or retained.original_task_id != source.original_task_id
            or retained.last_reviewed_commit != source.last_reviewed_commit
            or retained.branch_head != source.branch_head
            or retained.metadata_fingerprint != source.metadata_fingerprint
        ):
            _coordination_conflict("Builder handoff source differs from its retained exact task")
        metadata = self._capture_builder_handoff_metadata(coordination)
        if (
            metadata.branch_head != source.branch_head
            or metadata.last_reviewed_commit != source.last_reviewed_commit
            or metadata.fingerprint != source.metadata_fingerprint
        ):
            message = "Builder handoff workspace metadata changed before source preparation"
            raise PreservationFenceError(message)
        return metadata.branch_head

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
        *,
        expected_writer: ChangeWriter | None = None,
    ) -> ChangeCoordination:
        """Require one unclaimed clean reviewed head containing every promoted Task commit."""
        coordination = self._coordinator.show(change_id)
        if coordination.writer != expected_writer:
            _workspace_failure("Delivery finalization cannot overlap an active Change writer")
        if coordination.publication_lease is not None:
            _workspace_failure("Delivery finalization cannot overlap a publication lease")
        if coordination.external_head_adoption_intent is not None:
            _coordination_conflict("Delivery finalization cannot overlap external Change-head adoption")
        if coordination.worktree_cleanup_intent is not None or coordination.worktree_cleanup is not None:
            _coordination_conflict("Delivery finalization cannot overlap Change worktree cleanup")
        if coordination.dirty_worktree_quarantine is not None:
            _coordination_conflict("Delivery finalization cannot use a quarantined Change worktree")
        branch_head = self._resolve(coordination.branch)
        if branch_head != exact_head:
            _workspace_failure("Delivery finalization head differs from the current Change branch")
        if not self._is_ancestor(coordination.last_reviewed_commit, exact_head, cwd=self._repository):
            _workspace_failure("Delivery finalization head is not a descendant of the reviewed Change head")
        self._require_worktree(
            change_id,
            coordination.worktree_path,
            coordination.branch,
            exact_head,
        )
        self._require_clean_worktree(coordination.worktree_path)
        for predecessor, successor in pairwise(promoted_commits):
            self._require_ancestor(predecessor, successor)
        for promoted_commit in promoted_commits:
            self._require_ancestor(promoted_commit, exact_head)
        return coordination

    def capture_finalization_workspace(
        self,
        change_id: str,
        promoted_commits: tuple[str, ...],
    ) -> tuple[ChangeCoordination, str, str, tuple[str, ...], str | None]:
        """Capture bounded workspace facts without changing checkout or custody."""
        self._require_preservation_environment()
        coordination = self._coordinator.show(change_id)
        head = self.observed_change_head(change_id)
        self._require_worktree(change_id, coordination.worktree_path, coordination.branch, head)
        status = self._run_git(
            "status",
            "--porcelain=v1",
            "-z",
            "--untracked-files=all",
            cwd=coordination.worktree_path,
            environment={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
        ).stdout
        paths = self._dirty_paths(status)
        fingerprint = hashlib.sha256(head.encode() + b"\0" + status)
        fingerprint.update(self._run_git("diff", "HEAD", "--binary", cwd=coordination.worktree_path).stdout)
        for relative in paths:
            try:
                metadata = (coordination.worktree_path / relative).lstat()
            except FileNotFoundError:
                fingerprint.update(repr((relative, "absent")).encode())
            else:
                fingerprint.update(
                    repr(
                        (relative, metadata.st_mode, metadata.st_size, metadata.st_mtime_ns, metadata.st_ctime_ns)
                    ).encode()
                )
        reason = self._captured_finalization_guard(coordination, head, promoted_commits)
        return coordination, head, fingerprint.hexdigest(), paths, reason or ("workspace-dirty" if status else None)

    def capture_recovery_workspace(
        self,
        change_id: str,
        promoted_commits: tuple[str, ...],
        *,
        expected_paths: tuple[str, ...] | None = None,
        expected_scope_details: tuple[tuple[str, ...], dict[str, str]] | None = None,
    ) -> tuple[ChangeCoordination, str, str, tuple[str, ...], str | None]:
        """Inspect retained custody without exempting damaged or dirty workspace state."""
        coordination, head, status, paths, reason = self.capture_recovery_workspace_metadata(
            change_id, promoted_commits
        )
        ignored = self._run_git(
            "status",
            "--porcelain=v1",
            "-z",
            "--ignored=matching",
            "--untracked-files=normal",
            cwd=coordination.worktree_path,
            environment={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
        ).stdout
        ignored_inventory = self._has_ignored_inventory(ignored)
        if ignored_inventory and expected_paths is not None:
            raise DeliveryWorkerExclusionRequiredError
        if expected_paths is not None and paths != expected_paths:
            raise DeliveryWorkerExclusionRequiredError
        if expected_paths is not None:
            self._validate_recovery_path_containment(coordination.worktree_path, expected_paths)
        self._validate_recovery_scope(coordination.worktree_path, expected_scope_details)
        fingerprint_hex = self._recovery_workspace_fingerprint(
            coordination.worktree_path,
            head,
            status,
            paths,
            expected_paths,
        )
        return (
            coordination,
            head,
            fingerprint_hex,
            paths,
            reason or ("workspace-dirty" if status or ignored_inventory else None),
        )

    @staticmethod
    def _validate_recovery_scope(
        worktree: Path,
        expected_scope_details: tuple[tuple[str, ...], dict[str, str]] | None,
    ) -> None:
        if expected_scope_details is None:
            return
        scope, expected_kinds = expected_scope_details
        for relative in scope:
            if not is_canonical_admitted_path(relative):
                raise DeliveryWorkerExclusionRequiredError
            candidate = worktree
            try:
                for part in PurePosixPath(relative).parts:
                    candidate /= part
                    metadata = candidate.lstat()
                    if stat.S_ISLNK(metadata.st_mode):
                        raise DeliveryWorkerExclusionRequiredError
            except FileNotFoundError:
                actual_kind = expected_kinds[relative]
            else:
                actual_kind = "directory" if stat.S_ISDIR(metadata.st_mode) else "file"
            if actual_kind != expected_kinds[relative]:
                raise DeliveryWorkerExclusionRequiredError

    def _recovery_workspace_fingerprint(
        self,
        worktree: Path,
        head: str,
        status: bytes,
        paths: tuple[str, ...],
        expected_paths: tuple[str, ...] | None,
    ) -> str:
        fingerprint = hashlib.sha256(head.encode() + b"\0" + status)
        if expected_paths:
            # Admission has fenced the path set; keep the content read inside that fence.
            fingerprint.update(
                self._run_git(
                    "diff",
                    "HEAD",
                    "--binary",
                    "--",
                    *(f":(literal){path}" for path in expected_paths),
                    cwd=worktree,
                ).stdout
            )
        for relative in paths:
            try:
                metadata = (worktree / relative).lstat()
            except FileNotFoundError:
                fingerprint.update(repr((relative, "absent")).encode())
            else:
                fingerprint.update(
                    repr(
                        (relative, metadata.st_mode, metadata.st_size, metadata.st_mtime_ns, metadata.st_ctime_ns)
                    ).encode()
                )
        # The admission caller supplies the exact path set only after checking
        # the active task scope.  Read those paths now, rather than during the
        # metadata-only preflight, so untracked bytes participate in the
        # persisted authority fingerprint without widening the read boundary.
        if expected_paths is not None:
            for relative in paths:
                state = self._read_worktree_state(worktree, relative)
                fingerprint.update(
                    repr(
                        (
                            relative,
                            state.kind,
                            state.mode,
                            state.identity,
                            digest(state.content) if state.content is not None else None,
                        )
                    ).encode()
                )
        return fingerprint.hexdigest()

    def capture_recovery_workspace_metadata(
        self, change_id: str, promoted_commits: tuple[str, ...], *, ignored_is_dirty: bool = True
    ) -> tuple[ChangeCoordination, str, bytes, tuple[str, ...], str | None]:
        """Capture recovery status and custody facts without reading dirty content.

        Builder handoff passes `ignored_is_dirty=False`: ignored caches stay in place, unpreserved and unfenced.
        """
        self._require_preservation_environment()
        coordination = self._coordinator.show(change_id)
        head = self.observed_change_head(change_id)
        self._require_worktree(change_id, coordination.worktree_path, coordination.branch, head)
        status = self._run_git(
            "status",
            "--porcelain=v1",
            "-z",
            "--untracked-files=all",
            cwd=coordination.worktree_path,
            environment={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
        ).stdout
        paths = self._dirty_paths(status)
        reason = self._captured_finalization_guard(coordination, head, promoted_commits)
        if ignored_is_dirty and self._has_ignored_inventory(
            self._run_git(
                "status",
                "--porcelain=v1",
                "-z",
                "--ignored=matching",
                "--untracked-files=normal",
                cwd=coordination.worktree_path,
                environment={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
            ).stdout
        ):
            return coordination, head, status, paths, reason or "workspace-dirty"
        if reason == "active-custody" and coordination.publication_lease is None:
            reason = self._captured_finalization_guard(
                coordination.model_copy(update={"writer": None}), head, promoted_commits
            )
        return coordination, head, status, paths, reason or ("workspace-dirty" if status else None)

    def baseline_scope_kinds(self, worktree: Path, head: str, scopes: tuple[str, ...]) -> dict[str, str]:
        """Classify missing task surfaces from the exact reviewed tree."""
        self._require_preservation_environment()
        kinds: dict[str, str] = {}
        for scope in scopes:
            output = self._run_git("ls-tree", "-z", head, "--", scope, cwd=worktree).stdout
            if not output:
                kinds[scope] = "missing"
                continue
            fields = output.split(b"\t", 1)[0].split()
            if not fields:
                raise DeliveryWorkerExclusionRequiredError
            mode = fields[0]
            if mode == b"040000":
                kinds[scope] = "directory"
            elif mode == b"120000":
                raise DeliveryWorkerExclusionRequiredError
            else:
                kinds[scope] = "file"
        return kinds

    def capture_preservation(  # noqa: C901, PLR0912, PLR0915 - capture keeps each fence in one transaction.
        self,
        change_id: str,
        recovery_id: str,
    ) -> WorktreePreservationReceipt:
        """Capture exact dirty paths and the managed index before any private write.

        This is deliberately independent of the legacy commit quarantine.  It reads the
        registered worktree's real index through Git, rejects unsafe/private material
        before creating the preservation directory, and stores raw bytes only below the
        owner-private recovery receipt.
        """
        self._require_preservation_identity(recovery_id)
        self._require_preservation_environment()
        coordination = self._coordinator.show(change_id)
        intent, _recovery = self._require_preservation_authority(change_id, recovery_id, coordination)
        branch_head = self._resolve(coordination.branch)
        if branch_head != intent.exact_head:
            msg = "Change branch head does not match the verified recovery boundary"
            raise PreservationFenceError(msg)
        worktree = self._canonical_worktree_path(change_id, coordination.worktree_path)
        self._require_worktree(change_id, worktree, coordination.branch, branch_head)
        target_head = self.observed_target_head()
        if target_head != intent.target_head:
            msg = "integration target moved since verified recovery"
            raise PreservationFenceError(msg)
        frontier_bytes = self._read_frontier_bytes(change_id)
        coordination_bytes = self._coordinator.coordination_bytes(change_id)
        worktree_identity = self._directory_identity(worktree, "registered worktree")
        repository_identity = self._directory_identity(self._repository, "managed repository")
        index = self._resolve_managed_index(worktree)
        common_identity = self._directory_identity(index.common_directory, "Git common directory")
        administration_identity = self._directory_identity(index.administration, "Git administration directory")
        runtime_identity = self._directory_identity(self.runtime_root, "runtime root")
        # Classify the complete dirty-path inventory before reading any raw
        # index or worktree bytes into the private preservation store.
        staged = self._preservation_git(
            "diff",
            "--cached",
            "--quiet",
            "--ignore-submodules",
            "--",
            cwd=worktree,
            check=False,
        )
        if staged.returncode == 1:
            msg = "pre-existing staged content is not eligible for raw recovery"
            raise PreservationRejectedError(msg)
        if staged.returncode != 0:
            msg = "managed index state could not be compared with the exact HEAD"
            raise PreservationRejectedError(msg)
        status = self._preservation_git(
            "status",
            "--porcelain=v1",
            "-z",
            "--ignored=matching",
            "--untracked-files=all",
            cwd=worktree,
        ).stdout
        paths = self._preservation_status_paths(status)
        if len(paths) > _MAX_PRESERVED_PATHS:
            msg = "changed path count exceeds the bounded preservation policy"
            raise PreservationRejectedError(msg)
        self._require_admitted_paths(intent, paths)
        self._validate_private_paths(paths)

        index_bytes = self._read_managed_index(index)
        self._validate_private_content(index_bytes)
        shared_index = self._preservation_git(
            "rev-parse",
            "--shared-index-path",
            cwd=worktree,
            check=False,
        )
        if shared_index.returncode not in (0, 128):
            msg = "managed index split-state could not be established"
            raise PreservationRejectedError(msg)
        if shared_index.returncode == 0 and shared_index.stdout.strip():
            msg = "split-index dependencies require containment"
            raise PreservationRejectedError(msg)
        index_records = self._index_entry_records(worktree)
        entries = tuple((path, mode, stage) for path, mode, stage, _object_id in index_records)
        self._validate_index_entries(entries)
        head_entries = self._head_entries(worktree, branch_head)
        index_path_names = self._validate_index_extensions(
            index_bytes,
            expected_entries=index_records,
            head_entries=head_entries,
        )
        if len(index_bytes) > _MAX_PRESERVED_FILE_BYTES:
            msg = "managed Git index exceeds the per-file preservation limit"
            raise PreservationRejectedError(msg)
        index_bytes_digest = hashlib.sha256(index_bytes).hexdigest()
        current_metadata = tuple((path, *self._read_worktree_metadata(worktree, path)) for path in paths)
        provenance = self._classify_preservation(
            change_id=change_id,
            intent=intent,
            recovery_id=recovery_id,
            worktree_path=worktree,
            current_metadata=current_metadata,
            exact_head=branch_head,
            index_digest=index_bytes_digest,
            index_entries=index_records,
            head_entries=head_entries,
            paths=paths,
        )
        self._validate_index_path_names(index_path_names)
        raw_states: dict[str, tuple[_PreservedPathState, _PreservedPathState]] = {}
        total = len(index_bytes)
        for path in paths:
            self._validate_preservation_path(worktree, path)
            current = self._read_worktree_state(worktree, path)
            baseline = self._read_head_state(worktree, branch_head, path)
            for state in (current, baseline):
                if state.content is not None:
                    self._validate_private_content(state.content)
                    if len(state.content) > _MAX_PRESERVED_FILE_BYTES:
                        msg = "a preserved file exceeds the per-file limit"
                        raise PreservationRejectedError(msg)
                    total += len(state.content)
            raw_states[path] = (current, baseline)
        self._validate_provenance_states(provenance, {path: state[0] for path, state in raw_states.items()})
        if total > _MAX_PRESERVED_TOTAL_BYTES:
            msg = "raw preservation exceeds the total bounded limit"
            raise PreservationRejectedError(msg)
        reread_states = {path: self._read_worktree_state(worktree, path) for path in paths}
        if any(not self._same_state(reread_states[path], raw_states[path][0]) for path in paths):
            msg = "worktree path bytes or metadata changed during preservation capture"
            raise PreservationFenceError(msg)
        self._validate_provenance_states(
            provenance,
            {path: reread_states[path] for path in paths},
        )
        # Recheck the complete authority, manifest inputs, and every root descriptor after
        # the complete read and before the first preservation write.
        current_coordination = self._coordinator.show(change_id)
        current_intent, current_recovery = self._require_preservation_authority(
            change_id, recovery_id, current_coordination
        )
        if (
            current_intent != intent
            or current_recovery != _recovery
            or self._coordinator.coordination_bytes(change_id) != coordination_bytes
            or self._read_frontier_bytes(change_id) != frontier_bytes
            or self.observed_target_head() != target_head
            or self._directory_identity(worktree, "registered worktree")[:3] != worktree_identity[:3]
            or self._directory_identity(self._repository, "managed repository") != repository_identity
            or self._directory_identity(self.runtime_root, "runtime root") != runtime_identity
        ):
            msg = "preservation authority or root descriptor changed during capture"
            raise PreservationFenceError(msg)
        self._require_worktree(change_id, worktree, coordination.branch, branch_head)
        current_index = self._resolve_managed_index(worktree)
        current_common = self._directory_identity(current_index.common_directory, "Git common directory")
        current_administration = self._directory_identity(current_index.administration, "Git administration directory")
        if (
            current_index != index
            or current_common != common_identity
            or current_administration != administration_identity
            or self._read_managed_index(current_index) != index_bytes
        ):
            msg = "managed index changed during preservation capture"
            raise PreservationFenceError(msg)
        if self._resolve(coordination.branch) != branch_head:
            msg = "Change branch moved during preservation capture"
            raise PreservationFenceError(msg)
        current_shared_index = self._preservation_git(
            "rev-parse",
            "--shared-index-path",
            cwd=worktree,
            check=False,
        )
        if (
            current_shared_index.returncode != shared_index.returncode
            or current_shared_index.stdout != shared_index.stdout
        ):
            msg = "managed index split state changed during preservation capture"
            raise PreservationFenceError(msg)
        current_staged = self._preservation_git(
            "diff",
            "--cached",
            "--quiet",
            "--ignore-submodules",
            "--",
            cwd=worktree,
            check=False,
        )
        if current_staged.returncode != staged.returncode:
            msg = "managed index content changed during preservation capture"
            raise PreservationFenceError(msg)
        current_status = self._preservation_git(
            "status",
            "--porcelain=v1",
            "-z",
            "--ignored=matching",
            "--untracked-files=all",
            cwd=worktree,
        ).stdout
        if current_status != status:
            msg = "worktree path inventory changed during preservation capture"
            raise PreservationFenceError(msg)
        final_states = {path: self._read_worktree_state(worktree, path) for path in paths}
        if any(not self._same_state(final_states[path], raw_states[path][0]) for path in paths):
            msg = "worktree path bytes or metadata changed before preservation write"
            raise PreservationFenceError(msg)
        self._validate_provenance_states(provenance, final_states)
        final_metadata = tuple((path, final_states[path].kind, final_states[path].mode) for path in paths)

        entries_meta: list[PreservationEntry] = []
        objects: dict[str, bytes] = {index_bytes_digest: index_bytes}
        provenance_by_path = {item.path: item for item in provenance.paths}
        for path in paths:
            current, baseline = raw_states[path]
            before_object = self._preservation_object_name(current.content)
            after_object = self._preservation_object_name(baseline.content)
            if current.content is not None:
                objects[before_object] = current.content
            if baseline.content is not None:
                objects[after_object] = baseline.content
            entries_meta.append(
                PreservationEntry(
                    path=path,
                    before_kind=current.kind,
                    after_kind=baseline.kind,
                    before_digest=self._state_digest(current),
                    after_digest=self._state_digest(baseline),
                    before_mode=current.mode,
                    after_mode=baseline.mode,
                    before_object=before_object if current.content is not None else None,
                    after_object=after_object if baseline.content is not None else None,
                    before_identity=current.identity,
                    provenance=provenance_by_path[path],
                )
            )
        preservation_material = [
            recovery_id.encode(),
            change_id.encode(),
            index_bytes,
            status,
            json.dumps(provenance.model_dump(mode="json"), sort_keys=True, separators=(",", ":")).encode(),
        ]
        for entry in entries_meta:
            preservation_material.extend(
                (
                    entry.path.encode(),
                    entry.before_kind.encode(),
                    entry.after_kind.encode(),
                    (entry.before_digest or "").encode(),
                    (entry.after_digest or "").encode(),
                    repr(entry.before_mode).encode(),
                    repr(entry.after_mode).encode(),
                    repr(entry.before_identity).encode(),
                    json.dumps(
                        entry.provenance.model_dump(mode="json") if entry.provenance is not None else None,
                        sort_keys=True,
                        separators=(",", ":"),
                    ).encode(),
                )
            )
        preservation_id = hashlib.sha256(b"\0".join(preservation_material)).hexdigest()
        receipt = WorktreePreservationReceipt.create(
            preservation_id=preservation_id,
            recovery_id=recovery_id,
            change_id=change_id,
            branch=coordination.branch,
            worktree_path=worktree,
            branch_head=branch_head,
            reviewed_head=coordination.last_reviewed_commit,
            target_head=target_head,
            integration_target=coordination.integration_target,
            frontier_digest=digest(frontier_bytes),
            coordination_digest=digest(coordination_bytes),
            repository=self._repository,
            runtime_root=self.runtime_root,
            worktree_device=worktree_identity[0],
            worktree_inode=worktree_identity[1],
            worktree_mode=worktree_identity[2],
            worktree_links=worktree_identity[3],
            repository_device=repository_identity[0],
            repository_inode=repository_identity[1],
            common_device=common_identity[0],
            common_inode=common_identity[1],
            administration_device=administration_identity[0],
            administration_inode=administration_identity[1],
            runtime_device=runtime_identity[0],
            runtime_inode=runtime_identity[1],
            index_path=index.path,
            administration=index.administration,
            common_directory=index.common_directory,
            maintained_surfaces=intent.maintained_surfaces,
            last_write_provenance=intent.last_write_provenance,
            index_digest=index_bytes_digest,
            index_size=len(index_bytes),
            paths=tuple(sorted(entries_meta, key=lambda item: item.path)),
            provenance=provenance,
        )
        self._reverify_preservation_provenance(
            change_id=change_id,
            intent=current_intent,
            evidence=provenance,
            recovery_id=recovery_id,
            worktree_path=worktree,
            current_metadata=final_metadata,
            exact_head=branch_head,
            index_digest=index_bytes_digest,
            index_entries=index_records,
            head_entries=head_entries,
            paths=paths,
        )
        self._write_preservation_store(
            receipt,
            objects,
            index=index,
        )
        self._verify_preservation_store(receipt, objects)
        return receipt

    # The explicit aliases keep the owner operation discoverable without creating a
    # second implementation or a second authority identity.
    capture_raw_preservation = capture_preservation

    def verify_preservation(
        self,
        change_id: str,
        preservation_id: str,
    ) -> WorktreePreservationReceipt:
        """Verify private preservation evidence and current registration without mutation."""
        self._require_preservation_identity(preservation_id)
        self._require_preservation_environment()
        receipt, index_metadata, inventory = self._read_preservation_manifest(change_id, preservation_id)
        if receipt.change_id != change_id or receipt.preservation_id != preservation_id:
            msg = "preservation identity does not match its private manifest"
            raise PreservationFenceError(msg)
        self._verify_preservation_fences(
            change_id,
            receipt,
            index_metadata,
            allow_legacy_provenance=True,
        )
        objects: dict[str, bytes] = {}
        for object_name in inventory:
            content = self._read_private_preservation_object(receipt, object_name)
            if hashlib.sha256(content).hexdigest() != object_name:
                msg = "private preservation object failed verification"
                raise PreservationFenceError(msg)
            objects[object_name] = content
        self._verify_preservation_store(receipt, objects, allow_legacy_index_extensions=True)
        return receipt

    def restore_preservation(  # noqa: C901, PLR0912, PLR0915 - restoration keeps each exact fence in one transaction.
        self,
        change_id: str,
        preservation_id: str,
        *,
        paths: tuple[str, ...] | None = None,
    ) -> WorktreePreservationReceipt:
        """Restore only recorded paths, retaining private evidence on any fence failure."""
        self._require_preservation_identity(preservation_id)
        self._require_preservation_environment()
        receipt, index_metadata, inventory = self._read_preservation_manifest(change_id, preservation_id)
        provenance_by_path = (
            {item.path: item for item in receipt.provenance.paths} if receipt.provenance is not None else {}
        )
        if paths is None:
            selected = tuple(
                entry.path
                for entry in receipt.paths
                if provenance_by_path.get(entry.path) is not None
                and provenance_by_path[entry.path].disposition == "disposable"
            )
        else:
            selected = tuple(paths)
            if selected != tuple(sorted(set(selected))) or not set(selected) <= {entry.path for entry in receipt.paths}:
                msg = "restoration paths must be an exact subset of the preservation"
                raise PreservationRejectedError(msg)
            if any(provenance_by_path.get(path) is None for path in selected):
                raise PreservationRejectedError("restoration provenance is unavailable")  # noqa: EM101, TRY003
            if any(provenance_by_path[path].disposition != "disposable" for path in selected):
                raise PreservationRejectedError(  # noqa: TRY003
                    "only proven disposable paths may be restored automatically"  # noqa: EM101
                )
        worktree, _index = self._verify_preservation_fences(change_id, receipt, index_metadata, selected_paths=selected)
        objects = {
            object_name: self._read_private_preservation_object(receipt, object_name) for object_name in inventory
        }
        if (
            len(objects[receipt.index_digest]) != receipt.index_size
            or hashlib.sha256(objects[receipt.index_digest]).hexdigest() != receipt.index_digest
        ):
            msg = "private preservation index object failed verification"
            raise PreservationFenceError(msg)
        self._verify_preservation_store(receipt, objects)
        entries = {entry.path: entry for entry in receipt.paths}
        expected_states = {
            path: self._state_from_entry(entry, before=True, receipt=receipt) for path, entry in entries.items()
        }
        desired_states = {
            path: self._state_from_entry(entry, before=False, receipt=receipt) for path, entry in entries.items()
        }
        for path in entries:
            self._validate_preservation_path(worktree, path)
        # A process can die after replacing the target but before unlinking the
        # owner-private source.  Let the inventory fence authenticate and
        # remove that exact co-link before ordinary strict reads below.
        self._verify_preservation_fences(change_id, receipt, index_metadata, selected_paths=selected)
        current_states = {path: self._read_worktree_state(worktree, path) for path in entries}
        if any(
            not self._same_state(current_states[path], expected_states[path])
            and not self._same_state(current_states[path], desired_states[path])
            for path in entries
        ):
            changed = next(
                path
                for path in entries
                if not self._same_state(current_states[path], expected_states[path])
                and not self._same_state(current_states[path], desired_states[path])
            )
            msg = f"path identity changed before restoration: {changed}"
            raise PreservationFenceError(msg)
        # Recheck the complete manifest and every path before the first effect.
        self._verify_preservation_fences(change_id, receipt, index_metadata, selected_paths=selected)
        current_states = {path: self._read_worktree_state(worktree, path) for path in entries}
        if any(
            not self._same_state(current_states[path], expected_states[path])
            and not self._same_state(current_states[path], desired_states[path])
            for path in entries
        ):
            msg = "preservation path inventory changed before restoration"
            raise PreservationFenceError(msg)
        with self._restoration_attempt(receipt, selected) as operation_id:
            for path in selected:
                record_name = f"paths/{digest(path.encode())}"
                record = entries[path].model_dump(mode="json")
                self._write_restoration_record(receipt, operation_id, f"{record_name}/intent.json", record)
                self._verify_preservation_fences(change_id, receipt, index_metadata, selected_paths=selected)
                current_states = {item: self._read_worktree_state(worktree, item) for item in entries}
                if any(
                    not self._same_state(current_states[item], expected_states[item])
                    and not self._same_state(current_states[item], desired_states[item])
                    for item in entries
                ):
                    msg = "preservation path inventory changed during restoration"
                    raise PreservationFenceError(msg)
                current = current_states[path]
                desired = desired_states[path]
                if not self._same_state(current, desired):
                    if not self._same_state(current, expected_states[path]):
                        msg = f"path identity changed before restoration: {path}"
                        raise PreservationFenceError(msg)
                    self._write_worktree_state(
                        path,
                        desired,
                        _WorktreeRestorationContext(expected_states[path], operation_id, receipt, worktree),
                    )
                if not self._same_state(self._read_worktree_state(worktree, path), desired):
                    msg = f"path identity changed during restoration: {path}"
                    raise PreservationFenceError(msg)
                self._cleanup_restoration_staging_source(receipt, operation_id, path)
                self._sync_restored_path(worktree, path, desired)
                self._write_restoration_record(receipt, operation_id, f"{record_name}/result.json", record)
            self._verify_preservation_fences(change_id, receipt, index_metadata, selected_paths=selected)
            final_states = {path: self._read_worktree_state(worktree, path) for path in selected}
            if any(not self._same_state(final_states[path], desired_states[path]) for path in selected):
                msg = "preservation restore did not reach every requested path"
                raise PreservationFenceError(msg)
        return receipt

    restore_raw_preservation = restore_preservation

    @contextmanager
    def _restoration_attempt(self, receipt: WorktreePreservationReceipt, selected: tuple[str, ...]) -> Iterator[str]:
        record = {"preservation_receipt_id": receipt.receipt_id, "paths": selected}
        operation_id = digest(json.dumps(record, sort_keys=True, separators=(",", ":")).encode())
        self._write_restoration_record(receipt, operation_id, "intent.json", record)
        try:
            yield operation_id
            self._write_restoration_record(receipt, operation_id, "result.json", record)
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError):
            with suppress(OSError, ValueError, RuntimeError, subprocess.SubprocessError):
                self._write_restoration_record(
                    receipt, operation_id, "failure.json", {"code": "restoration-interrupted"}
                )
            raise

    def _write_restoration_record(
        self, receipt: WorktreePreservationReceipt, operation_id: str, name: str, payload: dict[str, object]
    ) -> None:
        relative = Path(receipt.storage_ref) / "restoration" / operation_id / Path(name).parent
        content = (json.dumps({"schema_version": 1, **payload}, sort_keys=True, separators=(",", ":")) + "\n").encode()
        root_fd = os.open(self.runtime_root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            with contained_directory(root_fd, relative, create=True) as parent_fd:
                record_path = Path(name).name
                write_contained(parent_fd, Path(record_path), content)
                if read_contained(parent_fd, Path(record_path), limit=len(content)) != content:
                    msg = "private restoration record failed readback"
                    raise PreservationFenceError(msg)
                descriptor = os.open(record_path, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent_fd)
                try:
                    os.fsync(descriptor)
                    os.fsync(parent_fd)
                finally:
                    os.close(descriptor)
        finally:
            os.close(root_fd)

    @staticmethod
    def _sync_restored_path(worktree: Path, path: str, state: _PreservedPathState) -> None:
        """Establish durability again after a response lost beyond the path effect."""
        relative = PurePosixPath(path)
        parent_fd = _open_worktree_parent(worktree, relative.parts[:-1], create=False)
        try:
            if state.kind == "regular":
                descriptor = os.open(relative.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent_fd)
                try:
                    os.fsync(descriptor)
                finally:
                    os.close(descriptor)
            os.fsync(parent_fd)
        finally:
            os.close(parent_fd)

    def _require_preservation_identity(self, recovery_id: str) -> None:
        if not _DIGEST_PATTERN.fullmatch(recovery_id):
            msg = "recovery identity is not an engine-issued digest"
            raise PreservationRejectedError(msg)

    def _require_preservation_authority(
        self,
        change_id: str,
        recovery_id: str,
        coordination: ChangeCoordination,
    ) -> tuple[RecoveryIntent, RecoveryReceipt]:
        """Require a completed, host-verified A recovery before raw custody."""
        if (
            coordination.recovery_owner_id is not None
            or coordination.writer is not None
            or coordination.publication_lease is not None
            or (coordination.continuation_action is not None and coordination.continuation_action.finished_at is None)
        ):
            raise DeliveryWorkerExclusionRequiredError
        try:
            intent = RecoveryIntent.model_validate_json(
                read_record(self.runtime_root, journal_path(change_id, recovery_id, "intent"))
            )
            receipt = RecoveryReceipt.model_validate_json(
                read_record(self.runtime_root, journal_path(change_id, recovery_id, "receipt"))
            )
            recorded_evidence = RecoveryEvidence.model_validate_json(
                read_record(self.runtime_root, journal_path(change_id, recovery_id, "evidence"))
            )
        except (OSError, TypeError, ValueError) as exc:
            raise DeliveryWorkerExclusionRequiredError from exc
        if (
            intent.recovery_id != recovery_id
            or intent.invocation.request.change_id != change_id
            or receipt.recovery_id != recovery_id
            or receipt.evidence.recovery_id != recovery_id
            or receipt.evidence.status not in {"closed", "excluded"}
            or receipt.evidence != recorded_evidence
            or recorded_evidence.invocation != intent.invocation
            or not intent.maintained_surfaces
            or not intent.last_write_provenance
        ):
            raise DeliveryWorkerExclusionRequiredError
        verified = (
            receipt.evidence.status == "excluded"
            and recovery_id in coordination.recovery_exclusions
            and self._coordinator.recovery_exclusions_verified(coordination)
        ) or (receipt.evidence.status == "closed" and self._coordinator.recovery_verification_recorded(recovery_id))
        if not verified:
            raise DeliveryWorkerExclusionRequiredError
        request = intent.invocation.request
        try:
            worktree = self._canonical_worktree_path(change_id, coordination.worktree_path)
            request_worktree = Path(request.worktree).resolve()
            request_repository = Path(request.repository).resolve()
            request_runtime = Path(request.runtime_root).resolve()
        except (OSError, RuntimeError, ValueError) as exc:
            raise DeliveryWorkerExclusionRequiredError from exc
        if (
            request.branch != coordination.branch
            or request_worktree != worktree
            or request_repository != self._repository
            or request_runtime != self.runtime_root
            or request.integration_target != coordination.integration_target
            or request.target_head != self.observed_target_head()
            or intent.exact_head != self._resolve(coordination.branch)
        ):
            msg = "verified recovery authority no longer matches the managed workspace"
            raise PreservationFenceError(msg)
        return intent, receipt

    def _classify_preservation(  # noqa: PLR0913 - preserve each exact evidence input at the gate.
        self,
        *,
        change_id: str,
        intent: RecoveryIntent,
        recovery_id: str,
        worktree_path: Path,
        current_metadata: tuple[tuple[str, str, int | None], ...],
        exact_head: str,
        index_digest: str,
        index_entries: tuple[tuple[str, int, int, str], ...],
        head_entries: tuple[tuple[str, int, str], ...],
        paths: tuple[str, ...],
    ) -> PreservationProvenanceEvidence:
        """Ask the configured owner for exact producer classifications before copying bytes."""
        try:
            evidence = self._preservation_provenance_provider.classify(
                change_id=change_id,
                intent=intent,
                recovery_id=recovery_id,
                worktree_path=worktree_path,
                current_metadata=current_metadata,
                exact_head=exact_head,
                index_digest=index_digest,
                index_entries=index_entries,
                head_entries=head_entries,
                paths=paths,
            )
            if evidence is not None and not isinstance(evidence, PreservationProvenanceEvidence):
                evidence = PreservationProvenanceEvidence.model_validate(evidence)
        except (AttributeError, OSError, RuntimeError, TypeError, ValueError) as exc:
            raise PreservationRejectedError("trusted path provenance is unavailable") from exc  # noqa: EM101, TRY003
        if evidence is None:
            raise PreservationRejectedError("trusted path provenance is unavailable")  # noqa: EM101, TRY003
        self._validate_preservation_provenance(
            intent,
            evidence=evidence,
            change_id=change_id,
            recovery_id=recovery_id,
            worktree_path=worktree_path,
            exact_head=exact_head,
            index_digest=index_digest,
            paths=paths,
        )
        return evidence

    @staticmethod
    def _validate_preservation_provenance(  # noqa: PLR0913 - validation binds each exact owner boundary.
        intent: RecoveryIntent,
        *,
        evidence: PreservationProvenanceEvidence | None,
        change_id: str,
        recovery_id: str,
        worktree_path: Path,
        exact_head: str,
        index_digest: str,
        paths: tuple[str, ...],
    ) -> None:
        """Require exact producer evidence; task scope and hashes are not substitutes."""
        if (
            evidence is None
            or evidence.change_id != change_id
            or evidence.recovery_id != recovery_id
            or evidence.worktree_path != worktree_path
            or evidence.workspace_fingerprint != intent.workspace_fingerprint
            or evidence.exact_head != exact_head
            or evidence.index_digest != index_digest
            or tuple(item.path for item in evidence.paths) != paths
            or (paths and (intent.admitted_task_id is None or intent.admitted_task_digest is None))
            or (
                paths
                and (evidence.task_id != intent.admitted_task_id or evidence.task_digest != intent.admitted_task_digest)
            )
            or any(item.disposition not in {"useful", "disposable"} for item in evidence.paths)
            or any(not item.producer_id for item in evidence.paths)
        ):
            raise PreservationRejectedError(  # noqa: TRY003
                "path provenance is foreign, ambiguous, private, or stale"  # noqa: EM101
            )

    @staticmethod
    def _validate_provenance_states(
        evidence: PreservationProvenanceEvidence,
        states: dict[str, _PreservedPathState],
    ) -> None:
        """Require independently produced before-state facts to match the bytes just read."""
        for item in evidence.paths:
            state = states.get(item.path)
            if state is None:
                raise PreservationRejectedError(  # noqa: TRY003
                    "path provenance does not cover the captured worktree state"  # noqa: EM101
                )
            if (
                item.before_kind != state.kind
                or item.before_digest != ChangeWorkspaceManager._state_digest(state)
                or item.before_mode != state.mode
            ):
                raise PreservationFenceError(  # noqa: TRY003
                    "captured bytes or metadata do not match trusted path provenance"  # noqa: EM101
                )

    def _reverify_preservation_provenance(  # noqa: PLR0913 - reverify the complete persisted owner boundary.
        self,
        *,
        change_id: str,
        intent: RecoveryIntent,
        evidence: PreservationProvenanceEvidence,
        recovery_id: str,
        worktree_path: Path,
        current_metadata: tuple[tuple[str, str, int | None], ...],
        exact_head: str,
        index_digest: str,
        index_entries: tuple[tuple[str, int, int, str], ...],
        head_entries: tuple[tuple[str, int, str], ...],
        paths: tuple[str, ...],
    ) -> None:
        """Reverify immutable producer evidence instead of trusting private manifest bytes alone."""
        try:
            verified = self._preservation_provenance_provider.verify(
                change_id=change_id,
                intent=intent,
                evidence=evidence,
                recovery_id=recovery_id,
                worktree_path=worktree_path,
                current_metadata=current_metadata,
                exact_head=exact_head,
                index_digest=index_digest,
                index_entries=index_entries,
                head_entries=head_entries,
                paths=paths,
            )
            if verified is not None and not isinstance(verified, PreservationProvenanceEvidence):
                verified = PreservationProvenanceEvidence.model_validate(verified)
        except (AttributeError, OSError, RuntimeError, TypeError, ValueError) as exc:
            raise PreservationRejectedError(  # noqa: TRY003
                "trusted path provenance could not be reverified"  # noqa: EM101
            ) from exc
        if verified is None or verified != evidence:
            raise PreservationRejectedError(  # noqa: TRY003
                "trusted path provenance could not be reverified"  # noqa: EM101
            )
        self._validate_preservation_provenance(
            intent,
            evidence=verified,
            change_id=change_id,
            recovery_id=recovery_id,
            worktree_path=worktree_path,
            exact_head=exact_head,
            index_digest=index_digest,
            paths=paths,
        )

    @staticmethod
    def _require_admitted_paths(intent: RecoveryIntent, paths: tuple[str, ...]) -> None:
        """Reject dirty paths outside the persisted active-task admission before raw reads."""
        if not set(paths) <= set(intent.admitted_paths):
            if intent.admitted_task_id is None:
                msg = "dirty paths require an admitted Builder task"
                raise PreservationRejectedError(msg)
            msg = "dirty paths fall outside the admitted task path authority"
            raise PreservationRejectedError(msg)

    @staticmethod
    def _validate_recovery_path_containment(worktree: Path, paths: tuple[str, ...]) -> None:
        """Reject unsupported admitted paths or symlinked ancestors before Git reads content."""
        if paths != tuple(sorted(set(paths))) or any(not is_canonical_admitted_path(path) for path in paths):
            raise DeliveryWorkerExclusionRequiredError
        for path in paths:
            try:
                ChangeWorkspaceManager._validate_preservation_path(worktree, path)
            except (OSError, PreservationRejectedError) as exc:
                raise DeliveryWorkerExclusionRequiredError from exc

    @staticmethod
    def _directory_identity(path: Path, label: str) -> tuple[int, int, int, int]:
        """Pin one owner directory without following a substituted ancestor."""
        try:
            _reject_symlink_ancestors(path)
            metadata = path.lstat()
        except (FileNotFoundError, OSError) as exc:
            msg = f"{label} is unavailable"
            raise PreservationRejectedError(msg) from exc
        if not stat.S_ISDIR(metadata.st_mode) or metadata.st_nlink < 1:
            msg = f"{label} is not a directory"
            raise PreservationRejectedError(msg)
        return (
            metadata.st_dev,
            metadata.st_ino,
            stat.S_IMODE(metadata.st_mode),
            metadata.st_nlink,
        )

    def _read_frontier_bytes(self, change_id: str) -> bytes:
        root_fd = os.open(self.runtime_root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            content = read_contained(
                root_fd,
                Path("changes") / change_id / "frontier.json",
                limit=65_536,
            )
        finally:
            os.close(root_fd)
        if content is None:
            msg = "Delivery frontier is missing"
            raise PreservationRejectedError(msg)
        return content

    def _verify_preservation_fences(
        self,
        change_id: str,
        receipt: WorktreePreservationReceipt,
        index_metadata: tuple[int, int, int, int],
        *,
        selected_paths: tuple[str, ...] = (),
        allow_legacy_provenance: bool = False,
    ) -> tuple[Path, _ManagedIndexIdentity]:
        """Revalidate every durable identity before a read or exact-path effect."""
        coordination = self._coordinator.show(change_id)
        intent, _recovery = self._require_preservation_authority(change_id, receipt.recovery_id, coordination)
        recorded_paths = tuple(entry.path for entry in receipt.paths)
        checked_paths = tuple(sorted(set(recorded_paths) | set(selected_paths)))
        if checked_paths:
            if intent.admitted_task_id is None:
                msg = "preservation receipt lacks admitted Builder task authority"
                raise PreservationRejectedError(msg)
            self._require_admitted_paths(intent, checked_paths)
        worktree = self._canonical_worktree_path(change_id, coordination.worktree_path)
        if (
            receipt.change_id != change_id
            or receipt.branch != coordination.branch
            or receipt.worktree_path != worktree
            or receipt.reviewed_head != coordination.last_reviewed_commit
            or receipt.integration_target != coordination.integration_target
            or receipt.repository != self._repository
            or receipt.runtime_root != self.runtime_root
            or receipt.maintained_surfaces != intent.maintained_surfaces
            or receipt.last_write_provenance != intent.last_write_provenance
        ):
            msg = "preservation authority no longer matches its registered roots"
            raise PreservationFenceError(msg)
        if receipt.provenance is not None or not allow_legacy_provenance:
            provenance = receipt.provenance
            self._validate_preservation_provenance(
                intent,
                evidence=provenance,
                change_id=change_id,
                recovery_id=receipt.recovery_id,
                worktree_path=worktree,
                exact_head=receipt.branch_head,
                index_digest=receipt.index_digest,
                paths=recorded_paths,
            )
        branch_head = self._resolve(coordination.branch)
        if branch_head != receipt.branch_head or branch_head != intent.exact_head:
            msg = "Change branch head changed since preservation"
            raise PreservationFenceError(msg)
        if self.observed_target_head() != receipt.target_head or receipt.target_head != intent.target_head:
            msg = "integration target changed since preservation"
            raise PreservationFenceError(msg)
        frontier = self._read_frontier_bytes(change_id)
        if digest(frontier) != receipt.frontier_digest:
            msg = "Delivery frontier changed since preservation"
            raise PreservationFenceError(msg)
        if digest(self._coordinator.coordination_bytes(change_id)) != receipt.coordination_digest:
            msg = "Change coordination changed since preservation"
            raise PreservationFenceError(msg)
        index = self._verify_preservation_roots(change_id, receipt, worktree)
        index_bytes = self._verify_index_metadata(index, receipt.index_digest, index_metadata)
        # A process can die after replacing the worktree path but before unlinking
        # its owner-private staging source.  Authenticate and clean that exact
        # co-link before the strict provenance metadata read below.
        self._verify_preservation_inventory(worktree, receipt)
        if receipt.provenance is not None:
            index_records = self._index_entry_records(worktree)
            entries = tuple((path, mode, stage) for path, mode, stage, _object_id in index_records)
            self._validate_index_entries(entries)
            head_entries = self._head_entries(worktree, branch_head)
            index_path_names = self._validate_index_extensions(
                index_bytes,
                expected_entries=index_records,
                head_entries=head_entries,
            )
            self._reverify_preservation_provenance(
                change_id=change_id,
                intent=intent,
                evidence=receipt.provenance,
                recovery_id=receipt.recovery_id,
                worktree_path=worktree,
                current_metadata=tuple(
                    (path, *self._read_worktree_metadata(worktree, path)) for path in recorded_paths
                ),
                exact_head=branch_head,
                index_digest=receipt.index_digest,
                index_entries=index_records,
                head_entries=head_entries,
                paths=recorded_paths,
            )
            self._validate_index_path_names(index_path_names)
            self._verify_index_metadata(index, receipt.index_digest, index_metadata)
        self._verify_preservation_inventory(worktree, receipt)
        return worktree, index

    def _verify_preservation_roots(
        self,
        change_id: str,
        receipt: WorktreePreservationReceipt,
        worktree: Path,
    ) -> _ManagedIndexIdentity:
        self._require_worktree(change_id, worktree, receipt.branch, receipt.branch_head)
        worktree_identity = self._directory_identity(worktree, "registered worktree")
        repository_identity = self._directory_identity(self._repository, "managed repository")
        runtime_identity = self._directory_identity(self.runtime_root, "runtime root")
        if (
            worktree_identity[:3]
            != (
                receipt.worktree_device,
                receipt.worktree_inode,
                receipt.worktree_mode,
            )
            or repository_identity[:2] != (receipt.repository_device, receipt.repository_inode)
            or runtime_identity[:2] != (receipt.runtime_device, receipt.runtime_inode)
        ):
            msg = "preservation root descriptor changed"
            raise PreservationFenceError(msg)
        index = self._resolve_managed_index(worktree)
        common_identity = self._directory_identity(index.common_directory, "Git common directory")
        administration_identity = self._directory_identity(index.administration, "Git administration directory")
        if (
            index.path != receipt.index_path
            or index.administration != receipt.administration
            or index.common_directory != receipt.common_directory
            or common_identity[:2] != (receipt.common_device, receipt.common_inode)
            or administration_identity[:2] != (receipt.administration_device, receipt.administration_inode)
        ):
            msg = "Git common directory identity changed"
            raise PreservationFenceError(msg)
        return index

    def _verify_preservation_inventory(self, worktree: Path, receipt: WorktreePreservationReceipt) -> None:
        status = self._preservation_git(
            "status", "--porcelain=v1", "-z", "--ignored=matching", "--untracked-files=all", cwd=worktree
        ).stdout
        known_paths = {entry.path for entry in receipt.paths}
        authorized_staging = self._authorized_restoration_staging(receipt, worktree)
        if not set(self._preservation_status_paths(status)) <= known_paths | authorized_staging:
            msg = "worktree path inventory expanded after preservation"
            raise PreservationFenceError(msg)

    def _authorized_restoration_staging(  # noqa: C901, PLR0912, PLR0915 - validate every durable staging fence.
        self,
        receipt: WorktreePreservationReceipt,
        worktree: Path,
    ) -> set[str]:
        """Return only operation-owned staging paths that are durably journaled and byte-exact."""
        relative = Path(receipt.storage_ref) / "restoration"
        root_fd = os.open(self.runtime_root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        authorized: set[str] = set()
        entries_by_path = {entry.path: entry for entry in receipt.paths}
        try:
            try:
                with contained_directory(root_fd, relative) as restoration_fd:
                    with os.scandir(restoration_fd) as operations:
                        operation_entries = tuple(operations)
                    if any(not item.is_dir(follow_symlinks=False) for item in operation_entries):
                        msg = "restoration journal operation inventory is malformed"
                        raise PreservationFenceError(msg)
                    operation_names = tuple(sorted(item.name for item in operation_entries))
                    if len(operation_names) > _MAX_PRESERVED_PATHS:
                        msg = "restoration journal exceeds its bounded operation inventory"
                        raise PreservationFenceError(msg)
                    for operation_id in operation_names:
                        if not _DIGEST_PATTERN.fullmatch(operation_id):
                            msg = "restoration journal operation identity is malformed"
                            raise PreservationFenceError(msg)
                        intent_bytes = read_contained(
                            restoration_fd,
                            Path(operation_id) / "intent.json",
                            limit=_MAX_PRESERVED_TOTAL_BYTES,
                        )
                        if intent_bytes is None:
                            with (
                                contained_directory(restoration_fd, Path(operation_id)) as operation_fd,
                                os.scandir(operation_fd) as incomplete_entries,
                            ):
                                incomplete_size = 0
                                for incomplete_count, entry in enumerate(incomplete_entries, start=1):
                                    if incomplete_count > _MAX_RESTORATION_INCOMPLETE_ARTIFACTS:
                                        message = "restoration operation intent is missing with artifacts"
                                        raise PreservationFenceError(message)
                                    try:
                                        metadata = entry.stat(follow_symlinks=False)
                                    except OSError as exc:
                                        message = "restoration operation intent is missing with artifacts"
                                        raise PreservationFenceError(message) from exc
                                    if (
                                        _RESTORATION_RECORD_TEMPORARY_PATTERN.fullmatch(entry.name) is None
                                        or not stat.S_ISREG(metadata.st_mode)
                                        or metadata.st_nlink != 1
                                        or stat.S_IMODE(metadata.st_mode) != _RESTORATION_RECORD_TEMPORARY_MODE
                                        or metadata.st_size < 0
                                        or metadata.st_size > _MAX_PRESERVED_TOTAL_BYTES
                                    ):
                                        message = "restoration operation intent is missing with artifacts"
                                        raise PreservationFenceError(message)
                                    incomplete_size += metadata.st_size
                                    if incomplete_size > _MAX_PRESERVED_TOTAL_BYTES:
                                        message = "restoration operation intent is missing with artifacts"
                                        raise PreservationFenceError(message)
                            for path in entries_by_path:
                                staging_path = str(
                                    PurePosixPath(path).parent / _preservation_temporary_name(operation_id, path)
                                )
                                self._validate_preservation_path(worktree, staging_path)
                                try:
                                    (worktree / PurePosixPath(staging_path)).lstat()
                                except FileNotFoundError:
                                    continue
                                message = "restoration operation intent is missing with worktree exposure"
                                raise PreservationFenceError(message)
                            continue
                        try:
                            operation_payload = json.loads(intent_bytes)
                        except json.JSONDecodeError as exc:
                            msg = "restoration operation intent is malformed"
                            raise PreservationFenceError(msg) from exc
                        if not isinstance(operation_payload, dict) or operation_payload.get("schema_version") != 1:
                            msg = "restoration operation intent is malformed"
                            raise PreservationFenceError(msg)
                        if set(operation_payload) != {"schema_version", "preservation_receipt_id", "paths"}:
                            msg = "restoration operation intent is malformed"
                            raise PreservationFenceError(msg)
                        if operation_payload["preservation_receipt_id"] != receipt.receipt_id:
                            msg = "restoration operation authority does not match its receipt"
                            raise PreservationFenceError(msg)
                        selected_raw = operation_payload["paths"]
                        if (
                            not isinstance(selected_raw, list)
                            or any(not isinstance(path, str) for path in selected_raw)
                            or selected_raw != sorted(set(selected_raw))
                            or not set(selected_raw) <= entries_by_path.keys()
                        ):
                            msg = "restoration operation paths are malformed"
                            raise PreservationFenceError(msg)
                        operation_record = {
                            "preservation_receipt_id": receipt.receipt_id,
                            "paths": selected_raw,
                        }
                        expected_operation_id = digest(
                            json.dumps(operation_record, sort_keys=True, separators=(",", ":")).encode()
                        )
                        if operation_id != expected_operation_id:
                            msg = "restoration operation identity is invalid"
                            raise PreservationFenceError(msg)
                        for path in selected_raw:
                            entry_bytes = read_contained(
                                restoration_fd,
                                Path(operation_id) / "paths" / digest(path.encode()) / "intent.json",
                                limit=_MAX_PRESERVED_TOTAL_BYTES,
                            )
                            if entry_bytes is None:
                                staging_path = str(
                                    PurePosixPath(path).parent / _preservation_temporary_name(operation_id, path)
                                )
                                self._validate_preservation_path(worktree, staging_path)
                                try:
                                    (worktree / PurePosixPath(staging_path)).lstat()
                                except FileNotFoundError:
                                    continue
                                msg = "restoration path intent is missing"
                                raise PreservationFenceError(msg)
                            try:
                                entry_payload = json.loads(entry_bytes)
                            except json.JSONDecodeError as exc:
                                msg = "restoration path intent is malformed"
                                raise PreservationFenceError(msg) from exc
                            if not isinstance(entry_payload, dict) or entry_payload.get("schema_version") != 1:
                                msg = "restoration path intent is malformed"
                                raise PreservationFenceError(msg)
                            entry_payload = {
                                key: value for key, value in entry_payload.items() if key != "schema_version"
                            }
                            try:
                                recorded_entry = PreservationEntry.model_validate(entry_payload)
                            except (TypeError, ValueError) as exc:
                                msg = "restoration path intent is malformed"
                                raise PreservationFenceError(msg) from exc
                            if recorded_entry != entries_by_path[path]:
                                msg = "restoration path intent does not match its receipt"
                                raise PreservationFenceError(msg)
                            staging_record = read_contained(
                                restoration_fd,
                                Path(operation_id) / "paths" / digest(path.encode()) / "staging.json",
                                limit=_MAX_PRESERVED_TOTAL_BYTES,
                            )
                            if staging_record is not None:
                                try:
                                    staging_payload = json.loads(staging_record)
                                except json.JSONDecodeError as exc:
                                    msg = "restoration staging identity is malformed"
                                    raise PreservationFenceError(msg) from exc
                                if (
                                    not isinstance(staging_payload, dict)
                                    or set(staging_payload)
                                    != {
                                        "schema_version",
                                        "preservation_receipt_id",
                                        "operation_id",
                                        "path",
                                        "source",
                                        "identity",
                                    }
                                    or staging_payload.get("schema_version") != 1
                                    or staging_payload.get("preservation_receipt_id") != receipt.receipt_id
                                    or staging_payload.get("operation_id") != operation_id
                                    or staging_payload.get("path") != path
                                ):
                                    msg = "restoration staging identity is invalid"
                                    raise PreservationFenceError(msg)
                                source = staging_payload.get("source")
                                if not isinstance(source, str) or not _RESTORATION_STAGE_PATTERN.fullmatch(source):
                                    msg = "restoration staging source is malformed"
                                    raise PreservationFenceError(msg)
                                identity = staging_payload.get("identity")
                                if (
                                    not isinstance(identity, list)
                                    or len(identity) != _PRESERVATION_FILE_IDENTITY_FIELDS
                                    or any(type(value) is not int or value < 0 for value in identity)
                                ):
                                    msg = "restoration staging identity is malformed"
                                    raise PreservationFenceError(msg)
                                source_relative = (
                                    Path(receipt.storage_ref)
                                    / "restoration"
                                    / operation_id
                                    / "paths"
                                    / digest(path.encode())
                                    / source
                                )
                            else:
                                source = None
                                identity = None
                                source_relative = None
                            if recorded_entry.after_kind == "absent":
                                if staging_record is not None:
                                    msg = "unexpected restoration staging for absent path"
                                    raise PreservationFenceError(msg)
                                continue
                            try:
                                desired_state = self._state_from_entry(
                                    recorded_entry,
                                    before=False,
                                    receipt=receipt,
                                )
                                expected_state = self._state_from_entry(
                                    recorded_entry,
                                    before=True,
                                    receipt=receipt,
                                )
                                source_state = (
                                    self._read_private_staging_state(root_fd, source_relative)
                                    if source_relative is not None
                                    else None
                                )
                            except (OSError, PreservationRejectedError, PreservationFenceError, ValueError) as exc:
                                message = "owned restoration staging type or bytes are invalid"
                                raise PreservationFenceError(message) from exc
                            if source_state is not None:
                                if (
                                    identity is None
                                    or source_state.identity is None
                                    or not _same_staging_identity(tuple(identity), source_state.identity)
                                ):
                                    msg = "restoration staging owner identity changed"
                                    raise PreservationFenceError(msg)
                                if not self._same_state(source_state, desired_state):
                                    msg = "owned restoration staging bytes or type changed"
                                    raise PreservationFenceError(msg)
                            staging_path = str(
                                PurePosixPath(path).parent / _preservation_temporary_name(operation_id, path)
                            )
                            self._validate_preservation_path(worktree, staging_path)
                            try:
                                (worktree / PurePosixPath(staging_path)).lstat()
                            except FileNotFoundError as exc:
                                if identity is not None:
                                    try:
                                        if source_state is None:
                                            target_state = self._read_worktree_state(worktree, path)
                                        else:
                                            target_state = self._read_worktree_state(
                                                worktree,
                                                path,
                                                expected_staging_identity=tuple(identity),
                                            )
                                    except (
                                        OSError,
                                        PreservationRejectedError,
                                        PreservationFenceError,
                                        ValueError,
                                    ) as exc:
                                        message = "restoration staging target identity is invalid"
                                        raise PreservationFenceError(message) from exc
                                    if source_state is not None and self._same_state(target_state, desired_state):
                                        if target_state.identity is None or not _same_staging_identity(
                                            tuple(identity), target_state.identity
                                        ):
                                            message = "restoration staging owner identity changed"
                                            raise PreservationFenceError(message) from None
                                        self._remove_private_staging(
                                            receipt,
                                            operation_id,
                                            path,
                                            source,
                                            tuple(identity),
                                        )
                                    elif not self._same_state(target_state, expected_state) and not self._same_state(
                                        target_state, desired_state
                                    ):
                                        msg = "restoration staging identity has no artifact"
                                        raise PreservationFenceError(msg) from exc
                                continue
                            if identity is None:
                                msg = "restoration staging identity is missing"
                                raise PreservationFenceError(msg)
                            try:
                                staging_state = self._read_worktree_state(
                                    worktree,
                                    staging_path,
                                    expected_staging_identity=tuple(identity),
                                )
                            except (OSError, PreservationRejectedError, PreservationFenceError, ValueError) as exc:
                                message = "owned restoration staging type or bytes are invalid"
                                raise PreservationFenceError(message) from exc
                            if staging_state.identity is None or not _same_staging_identity(
                                tuple(identity), staging_state.identity
                            ):
                                msg = "restoration staging owner identity changed"
                                raise PreservationFenceError(msg)
                            if not self._same_state(staging_state, desired_state):
                                msg = "owned restoration staging bytes or type changed"
                                raise PreservationFenceError(msg)
                            authorized.add(staging_path)
            except FileNotFoundError:
                return authorized
        finally:
            os.close(root_fd)
        return authorized

    @staticmethod
    def _require_preservation_environment() -> None:
        inherited = tuple(name for name in _PRESERVATION_ENV_OVERRIDES if name in os.environ)
        if inherited:
            msg = "inherited Git repository/index overrides are not accepted"
            raise PreservationRejectedError(msg)

    @staticmethod
    def require_preservation_environment() -> None:
        """Reject inherited Git repository and index overrides before custody reads."""
        ChangeWorkspaceManager._require_preservation_environment()

    def _preservation_git(
        self,
        *arguments: str,
        cwd: Path,
        check: bool = True,
    ) -> subprocess.CompletedProcess[bytes]:
        environment = {**os.environ, "GIT_OPTIONAL_LOCKS": "0"}
        return self._run_git(
            "--no-optional-locks",
            *arguments,
            cwd=cwd,
            check=check,
            environment=environment,
        )

    def _resolve_managed_index(self, worktree: Path) -> _ManagedIndexIdentity:
        self._require_preservation_environment()
        index = Path(
            self._preservation_git(
                "rev-parse",
                "--path-format=absolute",
                "--git-path",
                "index",
                cwd=worktree,
            )
            .stdout.decode()
            .strip()
        )
        administration = Path(
            self._preservation_git(
                "rev-parse",
                "--path-format=absolute",
                "--absolute-git-dir",
                cwd=worktree,
            )
            .stdout.decode()
            .strip()
        )
        common = Path(
            self._preservation_git(
                "rev-parse",
                "--path-format=absolute",
                "--git-common-dir",
                cwd=worktree,
            )
            .stdout.decode()
            .strip()
        )
        repository_common = Path(
            self._preservation_git(
                "rev-parse",
                "--path-format=absolute",
                "--git-common-dir",
                cwd=self._repository,
            )
            .stdout.decode()
            .strip()
        )
        if (
            not index.is_absolute()
            or not administration.is_absolute()
            or not common.is_absolute()
            or not repository_common.is_absolute()
            or index.parent != administration
            or common != common.resolve()
            or administration != administration.resolve()
            or index != index.resolve()
            or repository_common != repository_common.resolve()
            or common != repository_common
            or not _path_is_contained(common, administration)
        ):
            msg = "Git resolved an unexpected worktree administration path"
            raise PreservationRejectedError(msg)
        _reject_symlink_ancestors(index)
        _reject_symlink_ancestors(administration)
        _reject_symlink_ancestors(common)
        lock = index.with_name(f"{index.name}.lock")
        try:
            lock.lstat()
        except FileNotFoundError:
            pass
        else:
            msg = "managed Git index is locked"
            raise PreservationRejectedError(msg)
        try:
            metadata = index.lstat()
        except FileNotFoundError as exc:
            msg = "managed Git index is missing"
            raise PreservationRejectedError(msg) from exc
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            msg = "managed Git index is not a single regular file"
            raise PreservationRejectedError(msg)
        return _ManagedIndexIdentity(
            path=index,
            administration=administration,
            common_directory=common,
            device=metadata.st_dev,
            inode=metadata.st_ino,
            mode=stat.S_IMODE(metadata.st_mode),
            link_count=metadata.st_nlink,
        )

    @staticmethod
    def _read_managed_index(identity: _ManagedIndexIdentity) -> bytes:
        descriptor = os.open(identity.path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            before = os.fstat(descriptor)
            if (
                not stat.S_ISREG(before.st_mode)
                or before.st_nlink != 1
                or (before.st_dev, before.st_ino) != (identity.device, identity.inode)
                or before.st_size > _MAX_PRESERVED_TOTAL_BYTES
            ):
                msg = "managed Git index metadata changed"
                raise PreservationRejectedError(msg)
            content = os.read(descriptor, before.st_size + 1)
            after = os.fstat(descriptor)
        finally:
            os.close(descriptor)
        if len(content) != before.st_size or (
            before.st_dev,
            before.st_ino,
            before.st_mode,
            before.st_nlink,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
        ) != (
            after.st_dev,
            after.st_ino,
            after.st_mode,
            after.st_nlink,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        ):
            msg = "managed Git index changed while it was read"
            raise PreservationFenceError(msg)
        return content

    def _verify_index_metadata(
        self,
        identity: _ManagedIndexIdentity,
        expected_digest: str,
        metadata: tuple[int, int, int, int],
    ) -> bytes:
        if (identity.mode, identity.device, identity.inode, identity.link_count) != metadata:
            msg = "managed Git index identity changed"
            raise PreservationFenceError(msg)
        content = self._read_managed_index(identity)
        if hashlib.sha256(content).hexdigest() != expected_digest:
            msg = "managed Git index digest changed"
            raise PreservationFenceError(msg)
        return content

    def _index_entries(self, worktree: Path) -> tuple[tuple[str, int, int], ...]:
        return tuple((path, mode, stage) for path, mode, stage, _object_id in self._index_entry_records(worktree))

    def _index_entry_records(self, worktree: Path) -> tuple[tuple[str, int, int, str], ...]:
        output = self._preservation_git("ls-files", "--sparse", "--stage", "-z", cwd=worktree).stdout
        result: list[tuple[str, int, int, str]] = []
        for record in output.split(b"\0"):
            if not record:
                continue
            header, separator, raw_path = record.partition(b"\t")
            fields = header.split()
            if (
                not separator
                or len(fields) != _INDEX_RECORD_FIELD_COUNT
                or len(fields[1]) not in _INDEX_OBJECT_ID_LENGTHS
            ):
                msg = "managed index inventory is malformed"
                raise PreservationRejectedError(msg)
            try:
                mode = int(fields[0], 8)
                stage = int(fields[2])
                object_id = fields[1].decode("ascii")
                path = os.fsdecode(raw_path)
            except (UnicodeError, ValueError) as exc:
                msg = "managed index inventory is not canonical"
                raise PreservationRejectedError(msg) from exc
            if any(character not in "0123456789abcdef" for character in object_id):
                raise PreservationRejectedError("managed index inventory is not canonical")  # noqa: EM101, TRY003
            result.append((path, mode, stage, object_id))
        return tuple(result)

    def _head_entries(self, worktree: Path, head: str) -> tuple[tuple[str, int, str], ...]:
        output = self._preservation_git("ls-tree", "-r", "-z", "--full-tree", head, cwd=worktree).stdout
        result: list[tuple[str, int, str]] = []
        for record in output.split(b"\0"):
            if not record:
                continue
            header, separator, raw_path = record.partition(b"\t")
            fields = header.split()
            if (
                not separator
                or len(fields) != _INDEX_RECORD_FIELD_COUNT
                or len(fields[2]) not in _INDEX_OBJECT_ID_LENGTHS
            ):
                raise PreservationRejectedError("reviewed HEAD inventory is malformed")  # noqa: EM101, TRY003
            try:
                mode = int(fields[0], 8)
                object_id = fields[2].decode("ascii")
                path = os.fsdecode(raw_path)
            except (UnicodeError, ValueError) as exc:
                raise PreservationRejectedError(  # noqa: TRY003
                    "reviewed HEAD inventory is not canonical"  # noqa: EM101
                ) from exc
            if fields[1] not in {b"blob", b"commit"} or any(
                character not in "0123456789abcdef" for character in object_id
            ):
                raise PreservationRejectedError("reviewed HEAD inventory is not canonical")  # noqa: EM101, TRY003
            result.append((path, mode, object_id))
        return tuple(result)

    @staticmethod
    def _validate_index_entries(entries: tuple[tuple[str, int, int], ...]) -> None:
        for path, mode, stage in entries:
            if stage != 0:
                msg = "unmerged index entries require containment"
                raise PreservationRejectedError(msg)
            if mode in {_GIT_MODE_GITLINK, _GIT_MODE_TREE}:
                msg = "submodule or sparse-index entries require containment"
                raise PreservationRejectedError(msg)
            if mode not in {0o100644, 0o100755, 0o120000}:
                msg = "unsupported managed index entry type"
                raise PreservationRejectedError(msg)
            _validate_relative_preservation_path(path)

    @staticmethod
    def _validate_index_extensions(  # noqa: C901, PLR0912, PLR0915 - parse each index boundary explicitly.
        content: bytes,
        *,
        expected_entries: tuple[tuple[str, int, int, str], ...] | None = None,
        head_entries: tuple[tuple[str, int, str], ...] | None = None,
    ) -> tuple[str, ...]:
        """Accept only self-contained index extensions with no private path cache."""
        if len(content) < _MIN_INDEX_BYTES or content[:4] != b"DIRC":
            raise PreservationRejectedError("managed index header is invalid")  # noqa: EM101, TRY003
        ChangeWorkspaceManager._validate_private_content(content)
        version = int.from_bytes(content[4:8], "big")
        entry_count = int.from_bytes(content[8:12], "big")
        if version not in {2, 3}:
            raise PreservationRejectedError(  # noqa: TRY003
                "managed index version is outside the v1 boundary"  # noqa: EM101
            )
        cursor = 12
        checksum_start = len(content) - 20
        if hashlib.sha1(content[:checksum_start], usedforsecurity=False).digest() != content[checksum_start:]:
            raise PreservationRejectedError("managed index checksum is invalid")  # noqa: EM101, TRY003
        records: list[tuple[str, int, int, str]] = []
        for _index in range(entry_count):
            if cursor + 62 > checksum_start:
                raise PreservationRejectedError("managed index entry table is truncated")  # noqa: EM101, TRY003
            entry_start = cursor
            mode = int.from_bytes(content[cursor + 24 : cursor + 28], "big")
            object_id = content[cursor + 40 : cursor + 60].hex()
            flags = int.from_bytes(content[cursor + 60 : cursor + 62], "big")
            if flags & 0xC000:
                raise PreservationRejectedError(  # noqa: TRY003
                    "managed index extended entries require containment"  # noqa: EM101
                )
            cursor += 62
            if flags & _INDEX_PATH_LENGTH_MASK < _INDEX_PATH_LENGTH_MASK:
                path_end = cursor + (flags & _INDEX_PATH_LENGTH_MASK)
                if path_end >= checksum_start or content[path_end] != 0:
                    raise PreservationRejectedError("managed index entry path is malformed")  # noqa: EM101, TRY003
                raw_path = content[cursor:path_end]
                cursor = path_end + 1
            else:
                try:
                    path_end = content.index(b"\0", cursor, checksum_start)
                except ValueError as exc:
                    raise PreservationRejectedError(  # noqa: TRY003
                        "managed index entry path is unterminated"  # noqa: EM101
                    ) from exc
                raw_path = content[cursor:path_end]
                cursor = path_end + 1
            try:
                path = os.fsdecode(raw_path)
            except UnicodeError as exc:
                raise PreservationRejectedError(  # noqa: TRY003
                    "managed index entry path is not canonical"  # noqa: EM101
                ) from exc
            _validate_relative_preservation_path(path)
            stage = (flags >> 12) & 0x3
            if mode not in {0o100644, 0o100755, 0o120000} or stage != 0:
                raise PreservationRejectedError(  # noqa: TRY003
                    "managed index entry requires containment"  # noqa: EM101
                )
            records.append((path, mode, stage, object_id))
            aligned_cursor = entry_start + ((cursor - entry_start + 7) & ~7)
            if aligned_cursor > checksum_start or any(content[cursor:aligned_cursor]):
                raise PreservationRejectedError("managed index entry padding is malformed")  # noqa: EM101, TRY003
            cursor = aligned_cursor
        if expected_entries is not None and tuple(records) != expected_entries:
            raise PreservationRejectedError(  # noqa: TRY003
                "managed index entries do not match Git inventory"  # noqa: EM101
            )
        if (
            head_entries is not None
            and tuple((path, mode, object_id) for path, mode, _stage, object_id in records) != head_entries
        ):
            raise PreservationRejectedError(  # noqa: TRY003
                "managed index entries do not match reviewed HEAD"  # noqa: EM101
            )
        path_names = [path for path, _mode, _stage, _object_id in records]
        while cursor < checksum_start:
            if cursor + 8 > checksum_start:
                raise PreservationRejectedError(  # noqa: TRY003
                    "managed index extension header is truncated"  # noqa: EM101
                )
            extension = content[cursor : cursor + 4]
            size = int.from_bytes(content[cursor + 4 : cursor + 8], "big")
            cursor += 8
            if extension != b"TREE" or cursor + size > checksum_start:
                raise PreservationRejectedError(  # noqa: TRY003
                    "managed index extension requires containment"  # noqa: EM101
                )
            extension_content = content[cursor : cursor + size]
            path_names.extend(ChangeWorkspaceManager._validate_index_tree_extension(extension_content))
            cursor += size
        if cursor != checksum_start:
            raise PreservationRejectedError(  # noqa: TRY003
                "managed index extension table is malformed"  # noqa: EM101
            )
        return tuple(path_names)

    @staticmethod
    def _validate_legacy_index_extensions(
        content: bytes,
    ) -> None:
        """Keep pre-provenance index receipts inspectable without new capture authority."""
        if len(content) < _MIN_INDEX_BYTES or content[:4] != b"DIRC":
            msg = "managed index header is invalid"
            raise PreservationRejectedError(msg)
        if _contains_private_index_metadata(content):
            msg = "managed index contains private metadata"
            raise PreservationRejectedError(msg)
        version = int.from_bytes(content[4:8], "big")
        entry_count = int.from_bytes(content[8:12], "big")
        if version not in {2, 3}:
            msg = "managed index version is outside the v1 boundary"
            raise PreservationRejectedError(msg)
        checksum_start = len(content) - 20
        cursor = ChangeWorkspaceManager._skip_legacy_index_entries(content, entry_count, checksum_start)
        ChangeWorkspaceManager._validate_legacy_index_extension_table(content, cursor, checksum_start)

    @staticmethod
    def _skip_legacy_index_entries(content: bytes, entry_count: int, checksum_start: int) -> int:
        cursor = 12
        for _index in range(entry_count):
            if cursor + 62 > checksum_start:
                msg = "managed index entry table is truncated"
                raise PreservationRejectedError(msg)
            entry_start = cursor
            flags = int.from_bytes(content[cursor + 60 : cursor + 62], "big")
            cursor += 62
            if flags & _INDEX_PATH_LENGTH_MASK < _INDEX_PATH_LENGTH_MASK:
                path_end = cursor + (flags & _INDEX_PATH_LENGTH_MASK)
                if path_end >= checksum_start or content[path_end] != 0:
                    msg = "managed index entry path is malformed"
                    raise PreservationRejectedError(msg)
                cursor = path_end + 1
            else:
                try:
                    path_end = content.index(b"\0", cursor, checksum_start)
                except ValueError as exc:
                    msg = "managed index entry path is unterminated"
                    raise PreservationRejectedError(msg) from exc
                cursor = path_end + 1
            cursor = entry_start + ((cursor - entry_start + 7) & ~7)
        return cursor

    @staticmethod
    def _validate_legacy_index_extension_table(content: bytes, cursor: int, checksum_start: int) -> None:
        known = {b"TREE", b"REUC", b"EOIE", b"IEOT"}
        while cursor < checksum_start:
            if cursor + 8 > checksum_start:
                msg = "managed index extension header is truncated"
                raise PreservationRejectedError(msg)
            extension = content[cursor : cursor + 4]
            size = int.from_bytes(content[cursor + 4 : cursor + 8], "big")
            cursor += 8
            if extension not in known or cursor + size > checksum_start:
                msg = "managed index extension requires containment"
                raise PreservationRejectedError(msg)
            extension_content = content[cursor : cursor + size]
            if _contains_private_index_metadata(extension_content):
                msg = "managed index extension contains private metadata"
                raise PreservationRejectedError(msg)
            cursor += size
        if cursor != checksum_start:
            msg = "managed index extension table is malformed"
            raise PreservationRejectedError(msg)

    @staticmethod
    def _validate_index_tree_extension(  # noqa: C901 - parse each cache-tree record and subtree boundary explicitly.
        content: bytes,
    ) -> tuple[str, ...]:
        """Validate cache-tree records instead of treating extension bytes as trusted paths."""
        if not content:
            raise PreservationRejectedError("managed Git cache-tree extension is empty")  # noqa: EM101, TRY003
        cursor = 0
        paths: list[str] = []
        pending_nodes = [1]
        while pending_nodes:
            if pending_nodes[-1] == 0:
                pending_nodes.pop()
                continue
            pending_nodes[-1] -= 1
            try:
                path_end = content.index(b"\0", cursor)
            except ValueError as exc:
                raise PreservationRejectedError(  # noqa: TRY003
                    "managed Git cache-tree path is unterminated"  # noqa: EM101
                ) from exc
            raw_path = content[cursor:path_end]
            cursor = path_end + 1
            try:
                path = os.fsdecode(raw_path)
            except UnicodeError as exc:
                raise PreservationRejectedError(  # noqa: TRY003
                    "managed Git cache-tree path is not canonical"  # noqa: EM101
                ) from exc
            if path:
                _validate_relative_preservation_path(path)
                paths.append(path)
            try:
                line_end = content.index(b"\n", cursor)
            except ValueError as exc:
                raise PreservationRejectedError(  # noqa: TRY003
                    "managed Git cache-tree record is unterminated"  # noqa: EM101
                ) from exc
            counts = content[cursor:line_end].split(b" ")
            if len(counts) != _CACHE_TREE_COUNT_FIELDS or any(
                not item
                or (item.startswith(b"-") and len(item) == 1)
                or any(byte < _ASCII_DIGIT_MIN or byte > _ASCII_DIGIT_MAX for byte in item.removeprefix(b"-"))
                for item in counts
            ):
                raise PreservationRejectedError(  # noqa: TRY003
                    "managed Git cache-tree counts are malformed"  # noqa: EM101
                )
            entry_count = int(counts[0])
            subtree_count = int(counts[1])
            if entry_count < -1 or subtree_count < 0:
                raise PreservationRejectedError(  # noqa: TRY003
                    "managed Git cache-tree counts are malformed"  # noqa: EM101
                )
            cursor = line_end + 1
            if entry_count >= 0:
                if cursor + 20 > len(content):
                    raise PreservationRejectedError(  # noqa: TRY003
                        "managed Git cache-tree object is truncated"  # noqa: EM101
                    )
                cursor += 20
            pending_nodes.append(subtree_count)
        if cursor != len(content):
            raise PreservationRejectedError(  # noqa: TRY003
                "managed Git cache-tree subtree count is malformed"  # noqa: EM101
            )
        return tuple(paths)

    @staticmethod
    def _validate_index_path_names(paths: tuple[str, ...]) -> None:
        """Apply conservative index-name screening only after the exact index boundary is trusted."""
        for path in paths:
            _validate_relative_preservation_path(path)
            components = {component.casefold() for component in PurePosixPath(path).parts}
            if any(
                component in _PRIVATE_PATH_MARKERS
                or component.startswith(
                    (
                        ".env.",
                        "id_rsa.",
                        "id_ed25519.",
                        "id_ecdsa.",
                        "credential.",
                        "credentials.",
                        "password.",
                        "passwd.",
                        "private.",
                        "secret.",
                        "secrets.",
                        "token.",
                    )
                )
                for component in components
            ):
                raise PreservationRejectedError(  # noqa: TRY003
                    "private or secret-like index path requires containment"  # noqa: EM101
                )

    @staticmethod
    def _preservation_status_paths(status: bytes) -> tuple[str, ...]:
        if status and not status.endswith(b"\0"):
            msg = "Git returned an unterminated worktree status"
            raise PreservationRejectedError(msg)
        paths: set[str] = set()
        records = status.split(b"\0")
        index = 0
        while index < len(records):
            record = records[index]
            index += 1
            if not record:
                continue
            if len(record) < _PORCELAIN_WORKTREE_STATUS_PREFIX_LENGTH:
                msg = "Git returned a malformed worktree status"
                raise PreservationRejectedError(msg)
            code = record[:2].decode("ascii", errors="strict")
            if code == "!!":
                msg = "ignored worktree content requires containment"
                raise PreservationRejectedError(msg)
                continue
            paths.add(os.fsdecode(record[3:]))
            if "R" in code or "C" in code:
                if index >= len(records) or not records[index]:
                    msg = "Git returned an incomplete rename status"
                    raise PreservationRejectedError(msg)
                paths.add(os.fsdecode(records[index]))
                index += 1
        return tuple(sorted(paths))

    @staticmethod
    def _has_ignored_inventory(status: bytes) -> bool:
        return bool(ChangeWorkspaceManager._ignored_inventory_paths(status))

    @staticmethod
    def _ignored_inventory_paths(status: bytes) -> frozenset[str]:
        """Return Git's collapsed ignored paths; ignored directories keep their trailing slash."""
        if status and not status.endswith(b"\0"):
            msg = "Git returned an unterminated worktree status"
            raise PreservationRejectedError(msg)
        records = status.split(b"\0")
        index = 0
        ignored: set[str] = set()
        while index < len(records):
            record = records[index]
            index += 1
            if not record:
                continue
            if len(record) < _PORCELAIN_WORKTREE_STATUS_PREFIX_LENGTH:
                msg = "Git returned a malformed worktree status"
                raise PreservationRejectedError(msg)
            code = record[:2].decode("ascii", errors="strict")
            if code == "!!":
                ignored.add(os.fsdecode(record[3:]))
                continue
            if "R" in code or "C" in code:
                if index >= len(records) or not records[index]:
                    msg = "Git returned an incomplete rename status"
                    raise PreservationRejectedError(msg)
                index += 1
        return frozenset(ignored)

    @staticmethod
    def _validate_private_paths(paths: tuple[str, ...]) -> None:
        for path in paths:
            _validate_relative_preservation_path(path)
            components = {component.casefold() for component in PurePosixPath(path).parts}
            if any(
                component in _PRIVATE_PATH_MARKERS
                or component.startswith(
                    (
                        "private.",
                        "private-",
                        "private_",
                        ".env.",
                        "id_rsa.",
                        "id_ed25519.",
                        "id_ecdsa.",
                    )
                )
                or any(marker in component for marker in ("credential", "password", "secret", "token"))
                for component in components
            ):
                msg = "private or secret-like path requires containment"
                raise PreservationRejectedError(msg)

    @staticmethod
    def _validate_private_content(content: bytes) -> None:
        """Reject high-confidence credential material before private storage."""
        lowered = content.lower()
        markers = (
            b"-----begin ",
            b"private key-----",
            b"aws_secret_access_key=",
            b"aws_access_key_id=",
            b"github_pat_",
            b"ghp_",
            b"xoxb-",
            b"xoxp-",
        )
        if any(marker in lowered for marker in markers):
            msg = "private or secret-like content requires containment"
            raise PreservationRejectedError(msg)

    @staticmethod
    def _validate_preservation_path(worktree: Path, path: str) -> None:
        _validate_relative_preservation_path(path)
        candidate = worktree / PurePosixPath(path)
        current = worktree
        for component in PurePosixPath(path).parts[:-1]:
            current = current / component
            try:
                metadata = current.lstat()
                if stat.S_ISLNK(metadata.st_mode):
                    msg = "external symlink traversal is not permitted"
                    raise PreservationRejectedError(msg)
                if not stat.S_ISDIR(metadata.st_mode):
                    msg = "worktree path ancestor is not a directory"
                    raise PreservationRejectedError(msg)
            except FileNotFoundError:
                break
        if candidate.is_dir() and not candidate.is_symlink():
            msg = "directory paths require bounded file inventory"
            raise PreservationRejectedError(msg)

    @staticmethod
    def _verify_worktree_ancestors(
        ancestors: tuple[tuple[Path, tuple[int, int, int]], ...],
        path: str,
    ) -> None:
        message = f"worktree ancestor changed while reading: {path}"
        for ancestor, expected in ancestors:
            try:
                current = ancestor.lstat()
            except FileNotFoundError as exc:
                raise PreservationFenceError(message) from exc
            if (
                stat.S_ISLNK(current.st_mode)
                or not stat.S_ISDIR(current.st_mode)
                or _directory_identity_tuple(current) != expected
            ):
                raise PreservationFenceError(message)

    @staticmethod
    def _open_worktree_read_parent(
        worktree: Path,
        parts: tuple[str, ...],
        path: str,
    ) -> tuple[int, tuple[tuple[Path, tuple[int, int, int]], ...]] | None:
        root_changed = f"worktree root changed while reading: {path}"
        ancestor_changed = f"worktree ancestor changed while reading: {path}"
        try:
            root_metadata = worktree.lstat()
        except FileNotFoundError:
            return None
        _require_worktree_directory(
            root_metadata,
            symlink_message="worktree root is not a directory",
            non_directory_message="worktree root is not a directory",
        )
        root_identity = _directory_identity_tuple(root_metadata)
        parent_fd = _open_directory_no_follow(
            worktree,
            dir_fd=None,
            missing_message=root_changed,
            unsafe_message="worktree root cannot be opened without following links",
        )
        ancestors = [(worktree, root_identity)]
        try:
            _require_directory_identity(os.fstat(parent_fd), root_identity, root_changed)
            current = worktree
            for part in parts:
                current /= part
                try:
                    metadata = current.lstat()
                except FileNotFoundError:
                    ChangeWorkspaceManager._verify_worktree_ancestors(tuple(ancestors), path)
                    try:
                        os.close(parent_fd)
                    finally:
                        parent_fd = -1
                    return None
                _require_worktree_directory(
                    metadata,
                    symlink_message="external symlink traversal is not permitted",
                    non_directory_message="worktree path ancestor is not a directory",
                )
                expected = _directory_identity_tuple(metadata)
                successor = _open_directory_no_follow(
                    part,
                    dir_fd=parent_fd,
                    missing_message=ancestor_changed,
                    unsafe_message="worktree path ancestor cannot be opened safely",
                    changed_errnos=(errno.ELOOP, errno.ENOTDIR),
                )
                try:
                    opened = os.fstat(successor)
                    _require_directory_identity(opened, expected, ancestor_changed)
                except BaseException:
                    os.close(successor)
                    raise
                os.close(parent_fd)
                parent_fd = successor
                ancestors.append((current, expected))
            return parent_fd, tuple(ancestors)
        except BaseException:
            if parent_fd >= 0:
                os.close(parent_fd)
            raise

    @staticmethod
    def _read_worktree_metadata(worktree: Path, path: str) -> tuple[str, int | None]:
        """Read only safe type/mode metadata for the owner lookup boundary."""
        ChangeWorkspaceManager._validate_preservation_path(worktree, path)
        relative = PurePosixPath(path)
        opened = ChangeWorkspaceManager._open_worktree_read_parent(worktree, relative.parts[:-1], path)
        if opened is None:
            return "absent", None
        parent_fd, ancestors = opened
        try:
            try:
                metadata = os.stat(relative.name, dir_fd=parent_fd, follow_symlinks=False)
            except FileNotFoundError:
                ChangeWorkspaceManager._verify_worktree_ancestors(ancestors, path)
                return "absent", None
            ChangeWorkspaceManager._verify_worktree_ancestors(ancestors, path)
            if stat.S_ISLNK(metadata.st_mode):
                return "symlink", 0o777
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
                raise PreservationRejectedError(  # noqa: TRY003
                    "special or multiply-linked worktree path requires containment"  # noqa: EM101
                )
            if metadata.st_size > _MAX_PRESERVED_FILE_BYTES:
                raise PreservationRejectedError(  # noqa: TRY003
                    "worktree path exceeds the per-file preservation limit"  # noqa: EM101
                )
            return "regular", stat.S_IMODE(metadata.st_mode)
        finally:
            os.close(parent_fd)

    @staticmethod
    def _read_worktree_handoff_metadata(
        worktree: Path,
        path: str,
    ) -> tuple[str, tuple[int, int, int, int, int, int, int, int] | None]:
        """Read safe path stat identity without opening or copying dirty content."""
        _validate_relative_preservation_path(path)
        relative = PurePosixPath(path)
        opened = ChangeWorkspaceManager._open_worktree_read_parent(worktree, relative.parts[:-1], path)
        if opened is None:
            return "absent", None
        parent_fd, ancestors = opened
        try:
            try:
                metadata = os.stat(relative.name, dir_fd=parent_fd, follow_symlinks=False)
            except FileNotFoundError:
                ChangeWorkspaceManager._verify_worktree_ancestors(ancestors, path)
                return "absent", None
            ChangeWorkspaceManager._verify_worktree_ancestors(ancestors, path)
            if stat.S_ISDIR(metadata.st_mode):
                kind = "directory"
            elif stat.S_ISREG(metadata.st_mode):
                kind = "regular"
            elif stat.S_ISLNK(metadata.st_mode):
                kind = "symlink"
            else:
                kind = "special"
            return kind, _preservation_file_identity(metadata)
        finally:
            os.close(parent_fd)

    @staticmethod
    def _read_worktree_leaf(
        parent_fd: int,
        name: str,
        path: str,
        metadata: os.stat_result,
        expected_staging_identity: tuple[int, int, int, int, int, int, int, int] | None,
    ) -> _PreservedPathState:
        changed_message = f"worktree path changed while it was read: {path}"
        identity = _preservation_file_identity(metadata)
        mode = stat.S_IMODE(metadata.st_mode)
        containment_message = "special or multiply-linked worktree path requires containment"
        size_message = "worktree path exceeds the per-file preservation limit"
        if stat.S_ISLNK(metadata.st_mode):
            content = os.fsencode(os.readlink(name, dir_fd=parent_fd))
            after = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
            if not _same_preservation_identity(_preservation_file_identity(after), identity):
                raise PreservationFenceError(changed_message)
            return _PreservedPathState("symlink", content, 0o777, identity)
        if not stat.S_ISREG(metadata.st_mode):
            raise PreservationRejectedError(containment_message)
        if metadata.st_nlink != 1 and (
            expected_staging_identity is None or not _same_staging_identity(expected_staging_identity, identity)
        ):
            raise PreservationRejectedError(containment_message)
        if metadata.st_size > _MAX_PRESERVED_FILE_BYTES:
            raise PreservationRejectedError(size_message)
        try:
            descriptor = os.open(
                name,
                os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                dir_fd=parent_fd,
            )
        except FileNotFoundError as exc:
            raise PreservationFenceError(changed_message) from exc
        except OSError as exc:
            if exc.errno == errno.ELOOP:
                raise PreservationFenceError(changed_message) from exc
            raise
        try:
            content = os.read(descriptor, metadata.st_size + 1)
            after = os.fstat(descriptor)
        finally:
            os.close(descriptor)
        if len(content) != metadata.st_size or not _same_preservation_identity(
            _preservation_file_identity(after), identity
        ):
            raise PreservationFenceError(changed_message)
        return _PreservedPathState("regular", content, mode, identity)

    @staticmethod
    def _read_worktree_state(
        worktree: Path,
        path: str,
        *,
        expected_staging_identity: tuple[int, int, int, int, int, int, int, int] | None = None,
    ) -> _PreservedPathState:
        _validate_relative_preservation_path(path)
        relative = PurePosixPath(path)
        opened = ChangeWorkspaceManager._open_worktree_read_parent(worktree, relative.parts[:-1], path)
        if opened is None:
            return _PreservedPathState("absent", None, None)
        parent_fd, ancestors = opened
        try:
            try:
                metadata = os.stat(relative.name, dir_fd=parent_fd, follow_symlinks=False)
            except FileNotFoundError:
                ChangeWorkspaceManager._verify_worktree_ancestors(ancestors, path)
                return _PreservedPathState("absent", None, None)
            state = ChangeWorkspaceManager._read_worktree_leaf(
                parent_fd,
                relative.name,
                path,
                metadata,
                expected_staging_identity,
            )
            ChangeWorkspaceManager._verify_worktree_ancestors(ancestors, path)
            return state
        finally:
            os.close(parent_fd)

    def _read_head_state(self, worktree: Path, head: str, path: str) -> _PreservedPathState:
        output = self._preservation_git("ls-tree", "-z", head, "--", path, cwd=worktree).stdout
        if not output:
            return _PreservedPathState("absent", None, None)
        record = output.rstrip(b"\0")
        header, separator, raw_path = record.partition(b"\t")
        fields = header.split()
        if not separator or len(fields) != _INDEX_RECORD_FIELD_COUNT or os.fsdecode(raw_path) != path:
            msg = "HEAD path inventory is malformed"
            raise PreservationRejectedError(msg)
        try:
            mode = int(fields[0], 8)
            object_id = fields[2].decode("ascii")
        except (UnicodeError, ValueError) as exc:
            msg = "HEAD path inventory is malformed"
            raise PreservationRejectedError(msg) from exc
        if mode == _GIT_MODE_GITLINK:
            msg = "submodule path requires containment"
            raise PreservationRejectedError(msg)
        if mode not in {0o100644, 0o100755, 0o120000}:
            msg = "HEAD path has an unsupported type"
            raise PreservationRejectedError(msg)
        content = self._preservation_git("cat-file", "blob", object_id, cwd=worktree).stdout
        if mode == _GIT_MODE_SYMLINK:
            return _PreservedPathState("symlink", content, 0o777)
        return _PreservedPathState("regular", content, stat.S_IMODE(mode))

    @staticmethod
    def _state_digest(state: _PreservedPathState) -> str | None:
        return None if state.content is None else hashlib.sha256(state.content).hexdigest()

    @staticmethod
    def _preservation_object_name(content: bytes | None) -> str:
        return "0" * 64 if content is None else hashlib.sha256(content).hexdigest()

    def _write_preservation_store(
        self,
        receipt: WorktreePreservationReceipt,
        objects: dict[str, bytes],
        *,
        index: _ManagedIndexIdentity,
    ) -> None:
        relative = Path("changes") / receipt.change_id / "recovery-receipts" / receipt.recovery_id / "preservation"
        root_fd = os.open(self.runtime_root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            with contained_directory(root_fd, relative, create=True) as preservation_fd:
                os.fchmod(preservation_fd, 0o700)
                for object_name, content in objects.items():
                    object_path = Path("objects") / f"{object_name}.raw"
                    write_contained(
                        preservation_fd,
                        object_path,
                        content,
                        limits=ContainedWriteLimits(
                            max_content_bytes=_MAX_PRESERVED_FILE_BYTES,
                            max_temporary_bytes=_MAX_PRESERVED_TOTAL_BYTES,
                        ),
                    )
                manifest = {
                    "schema_version": 1,
                    "receipt": receipt.model_dump(mode="json"),
                    "index_mode": index.mode,
                    "index_device": index.device,
                    "index_inode": index.inode,
                    "index_links": index.link_count,
                    "objects": tuple(sorted(objects)),
                }
                write_contained(
                    preservation_fd,
                    Path("manifest.json"),
                    (json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n").encode(),
                )
        finally:
            os.close(root_fd)

    def _verify_preservation_store(
        self,
        receipt: WorktreePreservationReceipt,
        objects: dict[str, bytes],
        *,
        allow_legacy_index_extensions: bool = False,
    ) -> None:
        loaded, _metadata, inventory = self._read_preservation_manifest(receipt.change_id, receipt.preservation_id)
        if loaded != receipt:
            msg = "private preservation manifest does not match its receipt"
            raise PreservationFenceError(msg)
        if tuple(sorted(objects)) != inventory:
            msg = "private preservation object inventory changed"
            raise PreservationFenceError(msg)
        self._validate_private_paths(tuple(entry.path for entry in receipt.paths))
        for object_name, content in objects.items():
            if object_name == receipt.index_digest:
                if allow_legacy_index_extensions and receipt.provenance is None:
                    self._validate_legacy_index_extensions(content)
                else:
                    self._validate_index_extensions(content)
            else:
                self._validate_private_content(content)
            stored = self._read_private_preservation_object(receipt, object_name)
            if stored != content or hashlib.sha256(stored).hexdigest() != object_name:
                msg = "private preservation object failed verification"
                raise PreservationFenceError(msg)

    def _preservation_storage_relative(self, change_id: str, preservation_id: str) -> Path:
        """Find one private preservation by its receipt identity without following links."""
        root_fd = os.open(self.runtime_root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        base = Path("changes") / change_id / "recovery-receipts"
        try:
            with contained_directory(root_fd, base) as receipts_fd:
                with os.scandir(receipts_fd) as scanner:
                    entries = tuple(sorted(scanner, key=lambda item: item.name))
                if len(entries) > _MAX_PRESERVED_PATHS:
                    msg = "private preservation inventory exceeds its bound"
                    raise PreservationRejectedError(msg)
                for entry in entries:
                    if not _DIGEST_PATTERN.fullmatch(entry.name) or not entry.is_dir(follow_symlinks=False):
                        msg = "private preservation inventory is malformed"
                        raise PreservationRejectedError(msg)
                    relative = base / entry.name / "preservation"
                    try:
                        with contained_directory(root_fd, relative) as preservation_fd:
                            content = read_contained(
                                preservation_fd,
                                Path("manifest.json"),
                                limit=_MAX_PRESERVED_TOTAL_BYTES,
                            )
                    except FileNotFoundError:
                        continue
                    if content is None:
                        continue
                    try:
                        receipt = _preservation_receipt_from_payload(json.loads(content))
                    except (TypeError, ValueError, json.JSONDecodeError) as exc:
                        msg = "private preservation manifest is malformed"
                        raise PreservationRejectedError(msg) from exc
                    if receipt.change_id == change_id and receipt.preservation_id == preservation_id:
                        return relative
        except FileNotFoundError as exc:
            msg = "private preservation inventory is missing"
            raise PreservationRejectedError(msg) from exc
        finally:
            os.close(root_fd)
        msg = "private preservation receipt is absent"
        raise PreservationRejectedError(msg)

    def _read_preservation_manifest(
        self,
        change_id: str,
        preservation_id: str,
    ) -> tuple[WorktreePreservationReceipt, tuple[int, int, int, int], tuple[str, ...]]:
        self._require_preservation_identity(preservation_id)
        relative = self._preservation_storage_relative(change_id, preservation_id)
        root_fd = os.open(self.runtime_root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            with contained_directory(root_fd, relative) as preservation_fd:
                content = read_contained(preservation_fd, Path("manifest.json"), limit=_MAX_PRESERVED_TOTAL_BYTES)
                if content is None:
                    msg = "private preservation manifest is missing"
                    raise PreservationRejectedError(msg)
                try:
                    payload = _preservation_manifest_payload(content)
                    receipt = _preservation_receipt_from_payload(payload)
                except (TypeError, ValueError, json.JSONDecodeError) as exc:
                    msg = "private preservation manifest is malformed"
                    raise PreservationRejectedError(msg) from exc
                try:
                    metadata = tuple(
                        int(payload.get(key)) for key in ("index_mode", "index_device", "index_inode", "index_links")
                    )
                except (TypeError, ValueError) as exc:
                    msg = "private preservation index metadata is malformed"
                    raise PreservationRejectedError(msg) from exc
                if (
                    len(metadata) != _PRESERVATION_INDEX_METADATA_FIELDS
                    or metadata[0] < 0
                    or metadata[0] > _FILE_PERMISSION_MASK
                    or metadata[1] < 0
                    or metadata[2] < 0
                    or metadata[3] < 1
                ):
                    msg = "private preservation index metadata is malformed"
                    raise PreservationRejectedError(msg)
                objects = payload.get("objects")
                if (
                    not isinstance(objects, list)
                    or len(objects) > (_MAX_PRESERVED_PATHS * 2) + 1
                    or any(not isinstance(item, str) or not re.fullmatch(r"[0-9a-f]{64}", item) for item in objects)
                    or objects != sorted(set(objects))
                ):
                    msg = "private preservation object inventory is malformed"
                    raise PreservationRejectedError(msg)
                if receipt.index_digest not in objects:
                    msg = "private preservation index object is missing"
                    raise PreservationRejectedError(msg)
                expected_objects = {
                    receipt.index_digest,
                    *(
                        object_name
                        for entry in receipt.paths
                        for object_name in (entry.before_object, entry.after_object)
                        if object_name is not None
                    ),
                }
                if tuple(objects) != tuple(sorted(expected_objects)):
                    msg = "private preservation object inventory does not match its manifest"
                    raise PreservationRejectedError(msg)
                return receipt, metadata, tuple(objects)
        finally:
            os.close(root_fd)

    def _read_private_preservation_object(self, receipt: WorktreePreservationReceipt, object_name: str) -> bytes:
        relative = Path("changes") / receipt.change_id / "recovery-receipts" / receipt.recovery_id / "preservation"
        root_fd = os.open(self.runtime_root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            with contained_directory(root_fd, relative) as preservation_fd:
                content = read_contained(
                    preservation_fd,
                    Path("objects") / f"{object_name}.raw",
                    limit=_MAX_PRESERVED_FILE_BYTES,
                )
                if content is None:
                    msg = "private preservation object is missing"
                    raise PreservationRejectedError(msg)
                return content
        finally:
            os.close(root_fd)

    def _state_from_entry(
        self,
        entry: PreservationEntry,
        *,
        before: bool,
        receipt: WorktreePreservationReceipt,
    ) -> _PreservedPathState:
        kind = entry.before_kind if before else entry.after_kind
        object_name = entry.before_object if before else entry.after_object
        mode = entry.before_mode if before else entry.after_mode
        identity = entry.before_identity if before else None
        if kind == "absent":
            return _PreservedPathState("absent", None, None)
        if object_name is None or mode is None:
            msg = "private preservation entry is incomplete"
            raise PreservationRejectedError(msg)
        content = self._read_private_preservation_object(receipt, object_name)
        expected = entry.before_digest if before else entry.after_digest
        if expected is None or hashlib.sha256(content).hexdigest() != expected:
            msg = "private preservation object digest changed"
            raise PreservationFenceError(msg)
        return _PreservedPathState(kind, content, mode, identity)

    @staticmethod
    def _read_private_staging_state(
        root_fd: int,
        relative: Path | None,
    ) -> _PreservedPathState | None:
        """Read an owner-private stage without following links or trusting its name."""
        if relative is None:
            return None
        with contained_directory(root_fd, relative.parent) as parent_fd:
            try:
                metadata = os.stat(relative.name, dir_fd=parent_fd, follow_symlinks=False)
            except FileNotFoundError:
                return None
            identity = _preservation_file_identity(metadata)
            if stat.S_ISLNK(metadata.st_mode):
                content = os.fsencode(os.readlink(relative.name, dir_fd=parent_fd))
                after = os.stat(relative.name, dir_fd=parent_fd, follow_symlinks=False)
                if not _same_staging_identity(_preservation_file_identity(after), identity):
                    msg = "private restoration staging changed while it was read"
                    raise PreservationFenceError(msg)
                return _PreservedPathState("symlink", content, 0o777, identity)
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink < 1:
                msg = "private restoration staging is not a regular file"
                raise PreservationRejectedError(msg)
            descriptor = os.open(
                relative.name,
                os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                dir_fd=parent_fd,
            )
            try:
                observed = os.fstat(descriptor)
                if not _same_staging_identity(_preservation_file_identity(observed), identity):
                    msg = "private restoration staging changed while it was opened"
                    raise PreservationFenceError(msg)
                with os.fdopen(descriptor, "rb", closefd=False) as handle:
                    content = handle.read(_MAX_PRESERVED_FILE_BYTES + 1)
                after = os.fstat(descriptor)
            finally:
                os.close(descriptor)
            if len(content) > _MAX_PRESERVED_FILE_BYTES:
                msg = "private restoration staging exceeds its bound"
                raise PreservationRejectedError(msg)
            if not _same_staging_identity(_preservation_file_identity(after), identity):
                msg = "private restoration staging changed while it was read"
                raise PreservationFenceError(msg)
            return _PreservedPathState("regular", content, stat.S_IMODE(metadata.st_mode), identity)

    @staticmethod
    def _private_staging_artifact_size(entry: os.DirEntry[str], parent_fd: int) -> int:
        is_stage = _RESTORATION_STAGE_PATTERN.fullmatch(entry.name) is not None
        is_temporary = _RESTORATION_RECORD_TEMPORARY_PATTERN.fullmatch(entry.name) is not None
        if not is_stage and not is_temporary:
            msg = "private restoration staging inventory is malformed"
            raise PreservationFenceError(msg)
        try:
            metadata = entry.stat(follow_symlinks=False)
        except OSError as exc:
            msg = "private restoration staging inventory is unavailable"
            raise PreservationFenceError(msg) from exc
        if is_temporary and (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_nlink != 1
            or stat.S_IMODE(metadata.st_mode) != _RESTORATION_RECORD_TEMPORARY_MODE
        ):
            msg = "private restoration staging temporary is not an owner-private regular file"
            raise PreservationFenceError(msg)
        if is_stage and (
            not (stat.S_ISREG(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode)) or metadata.st_nlink < 1
        ):
            msg = "private restoration staging artifact is not a file"
            raise PreservationFenceError(msg)
        size = metadata.st_size
        if stat.S_ISLNK(metadata.st_mode):
            try:
                size = len(os.fsencode(os.readlink(entry.name, dir_fd=parent_fd)))
            except OSError as exc:
                msg = "private restoration staging link is unreadable"
                raise PreservationFenceError(msg) from exc
        if size < 0 or size > _MAX_PRESERVED_FILE_BYTES:
            msg = "private restoration staging artifact exceeds its bound"
            raise PreservationFenceError(msg)
        return size

    @staticmethod
    def _validate_private_staging_inventory(parent_fd: int, additional_bytes: int) -> None:
        """Bound retained stages before allocating another markerless artifact."""
        if additional_bytes < 0 or additional_bytes > _MAX_PRESERVED_FILE_BYTES:
            msg = "private restoration staging artifact exceeds its bound"
            raise PreservationFenceError(msg)
        try:
            with os.scandir(parent_fd) as scanned:
                stage_count = 0
                stage_bytes = 0
                for entry in scanned:
                    if entry.name in {"intent.json", "result.json", "staging.json"}:
                        continue
                    size = ChangeWorkspaceManager._private_staging_artifact_size(entry, parent_fd)
                    stage_count += 1
                    stage_bytes += size
                    if (
                        stage_count >= _MAX_RESTORATION_STAGING_ARTIFACTS
                        or stage_bytes > _MAX_RESTORATION_STAGING_BYTES - additional_bytes
                    ):
                        msg = "private restoration staging exceeds its retained bound"
                        raise PreservationFenceError(msg)
        except OSError as exc:
            msg = "private restoration staging inventory is unavailable"
            raise PreservationFenceError(msg) from exc

    def _create_private_staging(
        self,
        receipt: WorktreePreservationReceipt,
        operation_id: str,
        path: str,
        state: _PreservedPathState,
    ) -> tuple[str, _PreservedPathState]:
        """Create a private stage before exposing any artifact to the worktree."""
        if state.kind == "absent" or state.content is None:
            msg = "private restoration staging content is missing"
            raise PreservationRejectedError(msg)
        relative = Path(operation_id) / "paths" / digest(path.encode())
        root_fd = os.open(self.runtime_root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            with contained_directory(
                root_fd,
                Path(receipt.storage_ref) / "restoration" / relative,
                create=True,
            ) as parent_fd:
                self._validate_private_staging_inventory(parent_fd, len(state.content))
                for _attempt in range(_MAX_RESTORATION_STAGING_ATTEMPTS):
                    source = f"stage-{secrets.token_hex(16)}"
                    created = False
                    staged: _PreservedPathState | None = None
                    try:
                        if state.kind == "symlink":
                            os.symlink(os.fsdecode(state.content), source, dir_fd=parent_fd)
                            created = True
                            os.fsync(parent_fd)
                        else:
                            descriptor = os.open(
                                source,
                                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                                0o600,
                                dir_fd=parent_fd,
                            )
                            created = True
                            try:
                                with os.fdopen(descriptor, "wb", closefd=False) as handle:
                                    handle.write(state.content)
                                    handle.flush()
                                os.fchmod(descriptor, state.mode or 0o644)
                                os.fsync(descriptor)
                            finally:
                                os.close(descriptor)
                            os.fsync(parent_fd)
                        staged = self._read_private_staging_state(
                            root_fd,
                            Path(receipt.storage_ref) / "restoration" / relative / source,
                        )
                        self._require_private_staging_readback(staged, state)
                    except FileExistsError:
                        continue
                    except BaseException:
                        if created and staged is not None and staged.identity is not None:
                            with suppress(OSError):
                                current = self._read_private_staging_state(
                                    root_fd,
                                    Path(receipt.storage_ref) / "restoration" / relative / source,
                                )
                                if (
                                    current is not None
                                    and current.identity is not None
                                    and _same_staging_identity(staged.identity, current.identity)
                                ):
                                    os.unlink(source, dir_fd=parent_fd)
                                    os.fsync(parent_fd)
                        raise
                    else:
                        return source, staged
                msg = "private restoration staging name allocation exhausted"
                raise PreservationFenceError(msg)
        finally:
            os.close(root_fd)

    @staticmethod
    def _require_private_staging_readback(
        staged: _PreservedPathState | None,
        expected: _PreservedPathState,
    ) -> None:
        if staged is None or staged.identity is None or not ChangeWorkspaceManager._same_state(staged, expected):
            msg = "private restoration staging failed readback"
            raise PreservationFenceError(msg)

    def _read_restoration_staging_record(
        self,
        receipt: WorktreePreservationReceipt,
        operation_id: str,
        path: str,
    ) -> tuple[str, tuple[int, int, int, int, int, int, int, int]] | None:
        record_relative = (
            Path(receipt.storage_ref) / "restoration" / operation_id / "paths" / digest(path.encode()) / "staging.json"
        )
        root_fd = os.open(self.runtime_root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            content = read_contained(root_fd, record_relative, limit=_MAX_PRESERVED_TOTAL_BYTES)
        finally:
            os.close(root_fd)
        if content is None:
            return None
        try:
            payload = json.loads(content)
        except json.JSONDecodeError as exc:
            msg = "restoration staging identity is malformed"
            raise PreservationFenceError(msg) from exc
        if (
            not isinstance(payload, dict)
            or set(payload)
            != {
                "schema_version",
                "preservation_receipt_id",
                "operation_id",
                "path",
                "source",
                "identity",
            }
            or payload.get("schema_version") != 1
            or payload.get("preservation_receipt_id") != receipt.receipt_id
            or payload.get("operation_id") != operation_id
            or payload.get("path") != path
        ):
            msg = "restoration staging identity is invalid"
            raise PreservationFenceError(msg)
        source = payload.get("source")
        identity = payload.get("identity")
        if (
            not isinstance(source, str)
            or not _RESTORATION_STAGE_PATTERN.fullmatch(source)
            or not isinstance(identity, list)
            or len(identity) != _PRESERVATION_FILE_IDENTITY_FIELDS
            or any(type(value) is not int or value < 0 for value in identity)
        ):
            msg = "restoration staging identity is malformed"
            raise PreservationFenceError(msg)
        return source, tuple(identity)

    def _remove_private_staging(
        self,
        receipt: WorktreePreservationReceipt,
        operation_id: str,
        path: str,
        source: str,
        identity: tuple[int, int, int, int, int, int, int, int],
    ) -> None:
        if not _RESTORATION_STAGE_PATTERN.fullmatch(source):
            msg = "restoration staging source is malformed"
            raise PreservationFenceError(msg)
        relative = Path(receipt.storage_ref) / "restoration" / operation_id / "paths" / digest(path.encode()) / source
        root_fd = os.open(self.runtime_root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            with contained_directory(root_fd, relative.parent) as parent_fd:
                staged = self._read_private_staging_state(root_fd, relative)
                if staged is None:
                    return
                if staged.identity is None or not _same_staging_identity(identity, staged.identity):
                    msg = "restoration staging owner identity changed"
                    raise PreservationFenceError(msg)
                os.unlink(source, dir_fd=parent_fd)
                os.fsync(parent_fd)
        finally:
            os.close(root_fd)

    def _cleanup_restoration_staging_source(
        self,
        receipt: WorktreePreservationReceipt,
        operation_id: str,
        path: str,
    ) -> None:
        record = self._read_restoration_staging_record(receipt, operation_id, path)
        if record is not None:
            source, identity = record
            self._remove_private_staging(receipt, operation_id, path, source, identity)

    @staticmethod
    def _same_state(left: _PreservedPathState, right: _PreservedPathState) -> bool:
        return (
            left.kind == right.kind
            and left.content == right.content
            and left.mode == right.mode
            and (
                left.identity is None
                or right.identity is None
                or _same_preservation_identity(left.identity, right.identity)
            )
        )

    def _write_worktree_state(
        self,
        path: str,
        state: _PreservedPathState,
        restoration: _WorktreeRestorationContext,
    ) -> None:
        worktree = restoration.worktree
        self._validate_preservation_path(worktree, path)
        relative = PurePosixPath(path)
        name = relative.name
        if not self._same_state(self._read_worktree_state(worktree, path), restoration.expected):
            msg = f"path identity changed before restoration: {path}"
            raise PreservationFenceError(msg)
        parent_fd = _open_worktree_parent(worktree, relative.parts[:-1])
        try:
            if not self._same_state(self._read_worktree_state(worktree, path), restoration.expected):
                msg = f"path identity changed before restoration: {path}"
                raise PreservationFenceError(msg)
            if state.kind == "absent":
                try:
                    os.unlink(name, dir_fd=parent_fd)
                except FileNotFoundError:
                    return
                os.fsync(parent_fd)
                return
            stage = self._prepare_worktree_restoration_stage(worktree, path, state, parent_fd, restoration)
            if not self._same_state(self._read_worktree_state(worktree, path), restoration.expected):
                msg = f"path identity changed before restoration: {path}"
                raise PreservationFenceError(msg)
            os.replace(stage.temporary, name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
            os.fsync(parent_fd)
            if stage.source is not None and stage.identity is not None:
                self._remove_private_staging(
                    restoration.receipt,
                    restoration.operation_id,
                    path,
                    stage.source,
                    stage.identity,
                )
        finally:
            os.close(parent_fd)

    def _prepare_worktree_restoration_stage(
        self,
        worktree: Path,
        path: str,
        state: _PreservedPathState,
        parent_fd: int,
        restoration: _WorktreeRestorationContext,
    ) -> _WorktreeRestorationStage:
        receipt = restoration.receipt
        operation_id = restoration.operation_id
        if receipt.runtime_device != receipt.worktree_device:
            msg = "private restoration staging requires one filesystem"
            raise PreservationFenceError(msg)
        temporary = _preservation_temporary_name(operation_id, path)
        temporary_relative = str(PurePosixPath(path).parent / temporary)
        staging_record = self._read_restoration_staging_record(receipt, operation_id, path)
        candidate = _WorktreeRestorationStageCandidate(
            temporary,
            temporary_relative,
            staging_record,
            staging_record[0] if staging_record is not None else None,
            staging_record[1] if staging_record is not None else None,
        )
        try:
            (worktree / PurePosixPath(temporary_relative)).lstat()
        except FileNotFoundError:
            return self._create_worktree_restoration_stage(path, state, parent_fd, restoration, candidate)
        if candidate.identity is None:
            msg = f"restoration staging identity is missing: {path}"
            raise PreservationFenceError(msg)
        temporary_state = self._read_worktree_state(
            worktree,
            temporary_relative,
            expected_staging_identity=candidate.identity,
        )
        if temporary_state.identity is None or not _same_staging_identity(candidate.identity, temporary_state.identity):
            msg = f"restoration staging owner identity changed: {path}"
            raise PreservationFenceError(msg)
        if not self._same_state(temporary_state, state):
            msg = f"owned restoration staging changed before replay: {path}"
            raise PreservationFenceError(msg)
        return _WorktreeRestorationStage(
            candidate.temporary, candidate.temporary_relative, candidate.source, candidate.identity
        )

    def _create_worktree_restoration_stage(
        self,
        path: str,
        state: _PreservedPathState,
        parent_fd: int,
        restoration: _WorktreeRestorationContext,
        candidate: _WorktreeRestorationStageCandidate,
    ) -> _WorktreeRestorationStage:
        source_relative, staging_source, staging_identity = self._private_restoration_staging_source(
            path,
            state,
            restoration,
            candidate,
        )
        self._link_private_restoration_stage(source_relative, candidate.temporary, parent_fd)
        temporary_state = self._read_worktree_state(
            restoration.worktree,
            candidate.temporary_relative,
            expected_staging_identity=staging_identity,
        )
        if (
            temporary_state.identity is None
            or staging_identity is None
            or not _same_staging_identity(staging_identity, temporary_state.identity)
        ):
            msg = f"restoration staging owner identity changed: {path}"
            raise PreservationFenceError(msg)
        if not self._same_state(temporary_state, state):
            msg = f"owned restoration staging changed before replay: {path}"
            raise PreservationFenceError(msg)
        return _WorktreeRestorationStage(
            candidate.temporary, candidate.temporary_relative, staging_source, staging_identity
        )

    def _private_restoration_staging_source(
        self,
        path: str,
        state: _PreservedPathState,
        restoration: _WorktreeRestorationContext,
        candidate: _WorktreeRestorationStageCandidate,
    ) -> tuple[Path, str, tuple[int, int, int, int, int, int, int, int]]:
        receipt = restoration.receipt
        operation_id = restoration.operation_id
        source_state: _PreservedPathState | None = None
        if candidate.source is not None:
            source_relative = (
                Path(receipt.storage_ref)
                / "restoration"
                / operation_id
                / "paths"
                / digest(path.encode())
                / candidate.source
            )
            root_fd = os.open(self.runtime_root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                source_state = self._read_private_staging_state(root_fd, source_relative)
            finally:
                os.close(root_fd)
            if source_state is not None:
                if source_state.identity is None or candidate.identity is None:
                    msg = f"restoration staging identity is missing: {path}"
                    raise PreservationFenceError(msg)
                if not _same_staging_identity(candidate.identity, source_state.identity):
                    msg = f"restoration staging owner identity changed: {path}"
                    raise PreservationFenceError(msg)
                if not self._same_state(source_state, state):
                    msg = f"owned restoration staging changed before replay: {path}"
                    raise PreservationFenceError(msg)
        staging_source = candidate.source
        staging_identity = candidate.identity
        if source_state is None:
            if candidate.staging_record is not None:
                msg = f"restoration staging source is missing: {path}"
                raise PreservationFenceError(msg)
            staging_source, source_state = self._create_private_staging(
                receipt,
                operation_id,
                path,
                state,
            )
            if source_state.identity is None:
                msg = f"private restoration staging identity is unavailable: {path}"
                raise PreservationFenceError(msg)
            staging_identity = source_state.identity
            record_name = f"paths/{digest(path.encode())}"
            self._write_restoration_record(
                receipt,
                operation_id,
                f"{record_name}/staging.json",
                {
                    "preservation_receipt_id": receipt.receipt_id,
                    "operation_id": operation_id,
                    "path": path,
                    "source": staging_source,
                    "identity": list(staging_identity),
                },
            )
        return (
            Path(receipt.storage_ref) / "restoration" / operation_id / "paths" / digest(path.encode()) / staging_source,
            staging_source,
            staging_identity,
        )

    def _link_private_restoration_stage(self, source_relative: Path, temporary: str, parent_fd: int) -> None:
        root_fd = os.open(self.runtime_root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            with contained_directory(root_fd, source_relative.parent) as source_parent_fd:
                os.link(
                    source_relative.name,
                    temporary,
                    src_dir_fd=source_parent_fd,
                    dst_dir_fd=parent_fd,
                    follow_symlinks=False,
                )
                os.fsync(source_parent_fd)
        except OSError as exc:
            if exc.errno == errno.EXDEV:
                msg = "private restoration staging cannot cross filesystems"
                raise PreservationFenceError(msg) from exc
            raise
        finally:
            os.close(root_fd)
        os.fsync(parent_fd)

    @staticmethod
    def _dirty_paths(status: bytes) -> tuple[str, ...]:
        return ChangeWorkspaceManager._preservation_status_paths(status)

    def _captured_finalization_guard(
        self,
        coordination: ChangeCoordination,
        head: str,
        promoted_commits: tuple[str, ...],
    ) -> str | None:
        self._require_preservation_environment()
        if coordination.writer is not None or coordination.publication_lease is not None:
            return "active-custody"
        if any(
            (
                coordination.external_head_adoption_intent,
                coordination.worktree_cleanup_intent,
                coordination.worktree_cleanup,
                coordination.dirty_worktree_quarantine,
            )
        ):
            return "workspace-preflight-failed"
        ancestors = (coordination.last_reviewed_commit, *promoted_commits)
        if any(not self._is_ancestor(commit, head, cwd=self._repository) for commit in ancestors):
            return "workspace-preflight-failed"
        if any(
            not self._is_ancestor(predecessor, successor, cwd=self._repository)
            for predecessor, successor in pairwise(promoted_commits)
        ):
            return "workspace-preflight-failed"
        return None

    def observed_change_head(self, change_id: str) -> str:
        """Read the current managed Change branch head without mutating any checkout."""
        self._require_preservation_environment()
        coordination = self._coordinator.show(change_id)
        return self._resolve(coordination.branch)

    def recovery_snapshot(self, change_id: str, attempt_id: str) -> WorkspaceRecoverySnapshot:
        """Inspect exact recovery state without changing the branch, worktree, or custody."""
        self._require_preservation_environment()
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
            clean = not self._git("--no-optional-locks", "-C", str(coordination.worktree_path), "status", "--porcelain")
        quarantine = coordination.dirty_worktree_quarantine
        return WorkspaceRecoverySnapshot(
            change_id=change_id,
            worktree_path=coordination.worktree_path,
            branch=coordination.branch,
            branch_head=branch_head,
            worktree_head=worktree_head,
            worktree_branch=worktree_branch,
            last_reviewed_commit=coordination.last_reviewed_commit,
            preserved_commit=preserved,
            quarantine_ref=quarantine.quarantine_ref if quarantine is not None else None,
            quarantine_commit=quarantine.quarantine_commit if quarantine is not None else None,
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

    def quarantine_dirty_worktree(
        self,
        change_id: str,
        attempt_id: str,
        claim_id: str,
        operation_id: str,
    ) -> DirtyWorktreeQuarantineReceipt:
        """Preserve a dirty Builder worktree as an isolated commit before cleanup."""
        coordination = self._coordinator.show(change_id)
        writer = coordination.writer
        if (
            coordination.builder_handoff is not None
            or coordination.finalization_attention is not None
            or (writer is not None and writer.kind in {"handoff", "finalization-attention"})
        ):
            _coordination_conflict("passive workspace custody cannot quarantine preserved content")
        if writer is None or writer.attempt_id != attempt_id or writer.claim_id != claim_id:
            _coordination_conflict("dirty worktree quarantine requires matching writer custody")
        worktree = coordination.worktree_path
        branch_head = self._resolve(coordination.branch)
        self._require_worktree(change_id, worktree, coordination.branch, branch_head)
        quarantine_ref = f"refs/owlbear/quarantine/{change_id}/{attempt_id}"
        self._git("check-ref-format", quarantine_ref)
        receipt = self._prepare_dirty_worktree_quarantine(
            coordination=coordination,
            worktree=worktree,
            branch_head=branch_head,
            quarantine_ref=quarantine_ref,
            operation_id=operation_id,
            attempt_id=attempt_id,
            claim_id=claim_id,
        )
        if self._resolve(coordination.branch) != branch_head:
            _workspace_failure("change branch moved while dirty worktree was being quarantined")
        self._git("reset", "--hard", branch_head, cwd=worktree)
        self._git("clean", "-fd", cwd=worktree)
        if self._git("status", "--porcelain=v1", "-z", "--untracked-files=all", cwd=worktree):
            _workspace_failure("dirty worktree quarantine did not clean the managed worktree")
        return receipt

    def _prepare_dirty_worktree_quarantine(  # noqa: PLR0913, PLR0917
        self,
        coordination: ChangeCoordination,
        worktree: Path,
        branch_head: str,
        quarantine_ref: str,
        operation_id: str,
        attempt_id: str,
        claim_id: str,
    ) -> DirtyWorktreeQuarantineReceipt:
        current = self._coordinator.show(coordination.change_id)
        existing_receipt = current.dirty_worktree_quarantine
        if existing_receipt is not None:
            if (
                existing_receipt.operation_id != operation_id
                or existing_receipt.attempt_id != attempt_id
                or existing_receipt.claim_id != claim_id
                or existing_receipt.quarantine_ref != quarantine_ref
            ):
                _coordination_conflict("dirty worktree quarantine already has different authority")
            if not self._quarantine_base_matches_current(coordination, branch_head, existing_receipt):
                _workspace_failure("dirty worktree quarantine base moved outside the recoverable restart state")
            existing_commit = self._resolve(existing_receipt.quarantine_ref)
            if existing_commit != existing_receipt.quarantine_commit:
                _workspace_failure("dirty worktree quarantine ref does not match its receipt")
            self._verify_quarantine_commit(
                existing_receipt.quarantine_commit,
                existing_receipt.base_head,
                existing_receipt.paths,
                existing_receipt.operation_id,
            )
            self._verify_worktree_matches_quarantine(worktree, existing_receipt)
            return existing_receipt

        paths = self._worktree_change_paths(worktree)
        receipt_base_head = branch_head
        existing = self._resolve(quarantine_ref, missing_ok=True)
        if existing is None:
            if not paths:
                _coordination_conflict("dirty worktree quarantine requires changed content")
            quarantine_commit = self._quarantine_commit(worktree, branch_head, paths, operation_id)
            self._git("update-ref", quarantine_ref, quarantine_commit, "0" * 40)
        else:
            quarantine_commit = existing
            quarantine_base = self._quarantine_commit_parent(quarantine_commit)
            paths = self._quarantine_commit_paths(quarantine_commit, quarantine_base)
            self._verify_quarantine_commit(quarantine_commit, quarantine_base, paths, operation_id)
            replay_receipt = DirtyWorktreeQuarantineReceipt.create(
                operation_id=operation_id,
                change_id=coordination.change_id,
                attempt_id=attempt_id,
                claim_id=claim_id,
                branch=coordination.branch,
                worktree_path=worktree,
                base_head=quarantine_base,
                quarantine_ref=quarantine_ref,
                quarantine_commit=quarantine_commit,
                paths=paths,
            )
            if not self._quarantine_base_matches_current(coordination, branch_head, replay_receipt):
                _workspace_failure("dirty worktree quarantine base moved outside the recoverable restart state")
            self._verify_worktree_matches_quarantine(worktree, replay_receipt)
            receipt_base_head = quarantine_base
        receipt = DirtyWorktreeQuarantineReceipt.create(
            operation_id=operation_id,
            change_id=coordination.change_id,
            attempt_id=attempt_id,
            claim_id=claim_id,
            branch=coordination.branch,
            worktree_path=worktree,
            base_head=receipt_base_head,
            quarantine_ref=quarantine_ref,
            quarantine_commit=quarantine_commit,
            paths=paths,
        )
        self._coordinator.update(current.model_copy(update={"dirty_worktree_quarantine": receipt}))
        return receipt

    def verify_dirty_worktree_quarantine(
        self,
        change_id: str,
        attempt_id: str,
        claim_id: str,
        operation_id: str,
    ) -> DirtyWorktreeQuarantineReceipt:
        """Verify preserved dirty-worktree evidence after workspace cleanup and writer release."""
        coordination = self._coordinator.show(change_id)
        receipt = coordination.dirty_worktree_quarantine
        if receipt is None:
            _coordination_conflict("dirty worktree quarantine receipt is missing")
        if receipt.operation_id != operation_id or receipt.attempt_id != attempt_id or receipt.claim_id != claim_id:
            _coordination_conflict("dirty worktree quarantine receipt does not match the recovery claim")
        branch_head = self._resolve(coordination.branch)
        if self._resolve(receipt.quarantine_ref) != receipt.quarantine_commit:
            _workspace_failure("dirty worktree quarantine ref does not match its receipt")
        if not self._quarantine_base_matches_current(coordination, branch_head, receipt):
            _workspace_failure("dirty worktree quarantine base moved outside the recoverable restart state")
        self._verify_quarantine_commit(
            receipt.quarantine_commit,
            receipt.base_head,
            receipt.paths,
            receipt.operation_id,
        )
        self._require_worktree(change_id, coordination.worktree_path, coordination.branch, branch_head)
        if self._git("status", "--porcelain=v1", "-z", "--untracked-files=all", cwd=coordination.worktree_path):
            _workspace_failure("dirty worktree quarantine evidence requires a clean managed worktree")
        return receipt

    def _quarantine_base_matches_current(
        self,
        coordination: ChangeCoordination,
        branch_head: str,
        receipt: DirtyWorktreeQuarantineReceipt,
    ) -> bool:
        if receipt.base_head == branch_head:
            return True
        if branch_head != coordination.last_reviewed_commit:
            return False
        attempt_ref = f"refs/owlbear/attempts/{coordination.change_id}/{receipt.attempt_id}"
        preserved = self._resolve(attempt_ref, missing_ok=True)
        return preserved == receipt.base_head and self._is_ancestor(
            coordination.last_reviewed_commit,
            receipt.base_head,
            cwd=self._repository,
        )

    def _worktree_change_paths(self, worktree: Path) -> tuple[str, ...]:
        status = self._run_git(
            "status",
            "--porcelain=v1",
            "-z",
            "--untracked-files=all",
            cwd=worktree,
        ).stdout
        if status and not status.endswith(b"\0"):
            _workspace_failure("Git returned an unterminated dirty worktree status")
        paths: set[str] = set()
        records = status.split(b"\0")
        index = 0
        while index < len(records):
            record = records[index]
            index += 1
            if not record:
                continue
            if len(record) < _PORCELAIN_WORKTREE_STATUS_PREFIX_LENGTH:
                _workspace_failure("Git returned an invalid dirty worktree status record")
            status_code = record[:2].decode("ascii")
            paths.add(os.fsdecode(record[3:]))
            if "R" in status_code or "C" in status_code:
                if index >= len(records) or not records[index]:
                    _workspace_failure("Git returned an incomplete rename status record")
                paths.add(os.fsdecode(records[index]))
                index += 1
        return tuple(sorted(paths))

    def _verify_worktree_matches_quarantine(
        self,
        worktree: Path,
        receipt: DirtyWorktreeQuarantineReceipt,
    ) -> None:
        current_paths = self._worktree_change_paths(worktree)
        if not set(current_paths).issubset(receipt.paths):
            _workspace_failure("dirty worktree changed after quarantine preservation")
        if not current_paths:
            return
        self._verify_worktree_paths_match_commit(
            worktree,
            receipt.base_head,
            current_paths,
            receipt.quarantine_commit,
        )

    def _verify_worktree_paths_match_commit(
        self,
        worktree: Path,
        base_head: str,
        paths: tuple[str, ...],
        commit: str,
    ) -> None:
        tree = self._worktree_tree(worktree, base_head, paths)
        result = self._run_git(
            "--literal-pathspecs",
            "diff",
            "--no-ext-diff",
            "--no-textconv",
            "--quiet",
            commit,
            tree,
            "--",
            *paths,
            check=False,
        )
        if result.returncode != 0:
            _workspace_failure("dirty worktree content changed after quarantine preservation")

    def _worktree_tree(self, worktree: Path, base_head: str, paths: tuple[str, ...]) -> str:
        index_fd, index_path = tempfile.mkstemp(prefix="owlbear-quarantine-index-")
        os.close(index_fd)
        Path(index_path).unlink()
        environment = {**os.environ, "GIT_INDEX_FILE": index_path}
        try:
            self._run_git("read-tree", base_head, cwd=worktree, environment=environment)
            self._run_git(
                "--literal-pathspecs",
                "add",
                "--all",
                "--",
                *paths,
                cwd=worktree,
                environment=environment,
            )
            return self._run_git("write-tree", cwd=worktree, environment=environment).stdout.decode().strip()
        finally:
            Path(index_path).unlink(missing_ok=True)

    def _quarantine_commit(
        self,
        worktree: Path,
        base_head: str,
        paths: tuple[str, ...],
        operation_id: str,
    ) -> str:
        index_fd, index_path = tempfile.mkstemp(prefix="owlbear-quarantine-index-")
        os.close(index_fd)
        Path(index_path).unlink()
        environment = {**os.environ, "GIT_INDEX_FILE": index_path}
        try:
            tree = self._worktree_tree(worktree, base_head, paths)
            commit = (
                self._run_git(
                    "commit-tree",
                    tree,
                    "-p",
                    base_head,
                    "-m",
                    _quarantine_commit_message(operation_id),
                    cwd=worktree,
                    environment={
                        **environment,
                        "GIT_AUTHOR_NAME": "OwlBear",
                        "GIT_AUTHOR_EMAIL": "owlbear@localhost",
                        "GIT_COMMITTER_NAME": "OwlBear",
                        "GIT_COMMITTER_EMAIL": "owlbear@localhost",
                    },
                )
                .stdout.decode()
                .strip()
            )
            self._verify_quarantine_commit(commit, base_head, paths, operation_id)
            return commit
        finally:
            Path(index_path).unlink(missing_ok=True)

    def _verify_quarantine_commit(
        self,
        commit: str,
        base_head: str,
        paths: tuple[str, ...],
        operation_id: str,
    ) -> None:
        parents = self._git("rev-list", "--parents", "-n", "1", commit).split()
        if parents != [commit, base_head]:
            _workspace_failure("quarantine commit does not have the exact reviewed worktree parent")
        message = self._git("show", "-s", "--format=%B", commit).rstrip()
        if message != _quarantine_commit_message(operation_id):
            _workspace_failure("quarantine commit does not belong to the recovery operation")
        changed = self._quarantine_commit_paths(commit, base_head)
        if changed != paths:
            _workspace_failure("quarantine commit does not contain the complete dirty worktree")

    def _quarantine_commit_paths(self, commit: str, base_head: str) -> tuple[str, ...]:
        return tuple(
            sorted(
                os.fsdecode(path)
                for path in self._run_git(
                    "diff",
                    "--no-ext-diff",
                    "--no-textconv",
                    "--no-renames",
                    "--name-only",
                    "-z",
                    base_head,
                    commit,
                ).stdout.split(b"\0")
                if path
            )
        )

    def _quarantine_commit_parent(self, commit: str) -> str:
        parents = self._git("rev-list", "--parents", "-n", "1", commit).split()
        if len(parents) != _COMMIT_PARENT_COUNT:
            _workspace_failure("quarantine commit does not have exactly one parent")
        return parents[1]

    def validate_writer_head(self, change_id: str, claim_id: str, commit: str) -> ChangeCoordination:
        """Validate one writer-owned clean branch-head commit without mutation."""
        coordination = self._coordinator.show(change_id)
        if coordination.writer is None or coordination.writer.claim_id != claim_id:
            _coordination_conflict("writer claim does not own the change workspace")
        if coordination.writer.kind == "handoff":
            _coordination_conflict("ended Builder handoff cannot validate a writer result")
        if coordination.writer.kind == "finalize":
            raise DeliveryWorkerExclusionRequiredError
        branch_head = self._resolve(coordination.branch)
        if branch_head != commit:
            _workspace_failure("candidate commit is not the current change branch head")
        self._require_ancestor(coordination.last_reviewed_commit, commit)
        self._require_worktree(change_id, coordination.worktree_path, coordination.branch, commit)
        if self._git("--no-optional-locks", "-C", str(coordination.worktree_path), "status", "--porcelain"):
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
        with self._coordinator.publication_lock(change_id):
            coordination = self._coordinator.show(change_id)
            if coordination.writer is not None and coordination.writer.kind == "handoff":
                _coordination_conflict("ended Builder handoff cannot restart its preserved worktree")
            if coordination.writer is not None and coordination.writer.kind == "finalize":
                raise DeliveryWorkerExclusionRequiredError
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
        if self._external_head_promotion_covers_adoption(coordination, receipt):
            return
        if branch_head == coordination.last_reviewed_commit or self._is_ancestor(
            receipt.adopted_head,
            branch_head,
            cwd=self._repository,
        ):
            _coordination_conflict(
                "cannot restart across an unpromoted external Change head; promote the adopted head first"
            )

    def _external_head_promotion_covers_adoption(
        self,
        coordination: ChangeCoordination,
        adoption: ChangeExternalHeadAdoptionReceipt,
    ) -> bool:
        promotion = coordination.external_head_promotion_receipt
        return (
            promotion is not None
            and promotion.change_id == coordination.change_id
            and promotion.branch == coordination.branch
            and promotion.adoption_receipt_id == adoption.receipt_id
            and promotion.promoted_head == adoption.adopted_head
            and self._is_ancestor(
                promotion.promoted_head,
                coordination.last_reviewed_commit,
                cwd=self._repository,
            )
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
        if preserved is None:
            self._git("update-ref", attempt_ref, rejected_head, "0" * 40)
        if coordination.worktree_path.exists():
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
        completed = self._run_git("--no-optional-locks", "worktree", "list", "--porcelain", "-z")
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
        except (OSError, subprocess.SubprocessError, ValueError):
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
        except (OSError, subprocess.SubprocessError, ValueError):
            return {ChangeWorktreeAttentionCode.UNEXPECTED_FILESYSTEM_STATE}
        return {ChangeWorktreeAttentionCode.WORKTREE_DIRTY} if status else set()

    def _change_branch_heads(self) -> dict[str, str]:
        prefix = "refs/heads/owlbear/change/"
        completed = self._run_git(
            "--no-optional-locks",
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
        ChangeWorkspaceManager._require_preservation_environment()
        result = subprocess.run(  # noqa: S603 - fixed Git executable and argument-vector invocation.
            (resolve_git_executable(), "-C", str(cwd), "merge-base", "--is-ancestor", ancestor, descendant),
            check=False,
            capture_output=True,
            timeout=10,
        )
        if result.returncode not in (0, 1):
            result.check_returncode()
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
        environment: Mapping[str, str] | None = None,
    ) -> str:
        result = self._run_git(
            *arguments,
            cwd=cwd,
            check=check,
            input_bytes=input_bytes,
            environment=environment,
        )
        return result.stdout.decode().strip()

    def _run_git(
        self,
        *arguments: str,
        cwd: Path | None = None,
        check: bool = True,
        input_bytes: bytes | None = None,
        environment: Mapping[str, str] | None = None,
    ) -> subprocess.CompletedProcess[bytes]:
        self._require_preservation_environment()
        command = arguments
        while command[:1] in (("-C",), ("--no-optional-locks",)):
            command = command[2:] if command[0] == "-C" else command[1:]
        inspection = command[:1] in (
            ("status",),
            ("diff",),
            ("rev-parse",),
            ("ls-files",),
            ("ls-tree",),
            ("cat-file",),
        ) or command[:2] in (
            ("branch", "--show-current"),
            ("worktree", "list"),
        )
        return subprocess.run(  # noqa: S603 - fixed Git executable and argument-vector invocation.
            (resolve_git_executable(), "-C", str(cwd or self._repository), *arguments),
            check=check,
            capture_output=True,
            input=input_bytes,
            env=dict(environment) if environment is not None else None,
            timeout=10 if inspection else None,
        )


def _directory_identity_tuple(metadata: os.stat_result) -> tuple[int, int, int]:
    return metadata.st_dev, metadata.st_ino, stat.S_IMODE(metadata.st_mode)


def _require_worktree_directory(
    metadata: os.stat_result,
    *,
    symlink_message: str,
    non_directory_message: str,
) -> None:
    if stat.S_ISLNK(metadata.st_mode):
        raise PreservationRejectedError(symlink_message)
    if not stat.S_ISDIR(metadata.st_mode):
        raise PreservationRejectedError(non_directory_message)


def _require_directory_identity(
    metadata: os.stat_result,
    expected: tuple[int, int, int],
    message: str,
) -> None:
    if _directory_identity_tuple(metadata) != expected:
        raise PreservationFenceError(message)


def _open_directory_no_follow(
    path: Path | str,
    *,
    dir_fd: int | None,
    missing_message: str,
    unsafe_message: str,
    changed_errnos: tuple[int, ...] = (),
) -> int:
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        if dir_fd is None:
            return os.open(path, flags)
        return os.open(path, flags, dir_fd=dir_fd)
    except FileNotFoundError as exc:
        raise PreservationFenceError(missing_message) from exc
    except OSError as exc:
        if exc.errno in changed_errnos:
            raise PreservationFenceError(missing_message) from exc
        raise PreservationRejectedError(unsafe_message) from exc


def _preservation_file_identity(
    metadata: os.stat_result,
) -> tuple[int, int, int, int, int, int, int, int]:
    """Return descriptor metadata used to fence a captured worktree preimage."""
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_nlink,
        metadata.st_size,
        stat.S_IMODE(metadata.st_mode),
        0,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def _same_preservation_identity(
    left: tuple[int, int, int, int, int, int, int, int],
    right: tuple[int, int, int, int, int, int, int, int],
) -> bool:
    """Compare stable metadata without invalidating evidence after ordinary reads."""
    return left[:5] == right[:5] and left[6:] == right[6:]


def _same_staging_identity(
    left: tuple[int, int, int, int, int, int, int, int],
    right: tuple[int, int, int, int, int, int, int, int],
) -> bool:
    """Compare an owner inode while allowing its expected hard-link transition."""
    stable = left[:2] == right[:2] and left[3:5] == right[3:5] and left[6] == right[6]
    ctime_transition = left[7] == right[7] or {left[2], right[2]} == {1, 2}
    return stable and ctime_transition


def _validate_relative_preservation_path(path: str) -> None:
    parsed = PurePosixPath(path)
    if (
        not path
        or len(path) > _MAX_PRESERVED_PATH_LENGTH
        or parsed.is_absolute()
        or parsed.parts == (".",)
        or ".." in parsed.parts
        or str(parsed) != path
        or "\\" in path
        or "\x00" in path
        or not path.isprintable()
    ):
        msg = "preserved path is not a normalized relative path"
        raise PreservationRejectedError(msg)


def _path_is_contained(root: Path, candidate: Path) -> bool:
    try:
        candidate.relative_to(root)
    except ValueError:
        return False
    return True


def _reject_symlink_ancestors(path: Path) -> None:
    current = Path(path.anchor)
    for component in path.parts[1:]:
        current /= component
        try:
            metadata = current.lstat()
        except FileNotFoundError as exc:
            msg = f"Git administration path is missing: {current}"
            raise PreservationRejectedError(msg) from exc
        if stat.S_ISLNK(metadata.st_mode):
            msg = f"Git administration path contains a symlink: {current}"
            raise PreservationRejectedError(msg)


def _activity_ns(path: Path) -> int:
    # ctime also covers tools that restore old modification times.
    metadata = path.lstat()
    return max(metadata.st_mtime_ns, metadata.st_ctime_ns)


@dataclass
class _ActivityWalkBudget:
    entries: int
    deadline: float

    def consume(self) -> None:
        self.entries -= 1
        if self.entries < 0 or time.monotonic() >= self.deadline:
            msg = "worktree activity walk exceeded its entry or time bound"
            raise PreservationRejectedError(msg)


def _worktree_tree_activity_ns(worktree: Path, ignored: frozenset[str]) -> int:
    """Return the newest mtime/ctime in the worktree, excluding its top-level `.git` and ignored subtrees."""
    budget = _ActivityWalkBudget(_ACTIVITY_WALK_MAX_ENTRIES, time.monotonic() + _ACTIVITY_WALK_SECONDS)
    descriptor = os.open(worktree, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        return _directory_activity_ns(descriptor, budget, "", ignored)
    finally:
        os.close(descriptor)


def _directory_activity_ns(descriptor: int, budget: _ActivityWalkBudget, prefix: str, ignored: frozenset[str]) -> int:
    metadata = os.fstat(descriptor)
    newest = max(metadata.st_mtime_ns, metadata.st_ctime_ns)
    directories: list[str] = []
    with os.scandir(descriptor) as entries:
        for entry in entries:
            if not prefix and entry.name == ".git":
                continue
            budget.consume()
            if entry.is_dir(follow_symlinks=False) and f"{prefix}{entry.name}/" not in ignored:
                directories.append(entry.name)
                continue
            # An ignored directory's own times still reveal entries created or removed directly inside it.
            entry_metadata = entry.stat(follow_symlinks=False)
            newest = max(newest, entry_metadata.st_mtime_ns, entry_metadata.st_ctime_ns)
    for name in directories:
        # O_NOFOLLOW fails closed if the directory was swapped for a symlink after listing.
        child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
        try:
            newest = max(newest, _directory_activity_ns(child, budget, f"{prefix}{name}/", ignored))
        finally:
            os.close(child)
    return newest


def _open_worktree_parent(worktree: Path, parts: tuple[str, ...], *, create: bool = True) -> int:
    """Open the directory chain, stopping at its nearest existing ancestor when requested."""
    descriptor = os.open(worktree, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in parts:
            try:
                successor = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
            except FileNotFoundError:
                if not create:
                    break
                os.mkdir(part, mode=0o755, dir_fd=descriptor)
                os.fsync(descriptor)
                successor = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = successor
    except BaseException:
        os.close(descriptor)
        raise
    else:
        return descriptor


def _preservation_temporary_name(operation_id: str, path: str) -> str:
    """Bind a worktree staging name to one durable restoration operation and path."""
    return f".owlbear-preserve-{operation_id}-{hashlib.sha256(path.encode()).hexdigest()[:16]}"


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


def _publication_baseline_recovery_digest(receipt: PublicationBaselineRecoveryReceipt) -> str:
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


def _design_package_snapshot_intent_digest(intent: ChangeDesignPackageSnapshotIntent) -> str:
    payload = intent.model_dump(mode="json", exclude={"intent_id"})
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _design_package_snapshot_digest(receipt: ChangeDesignPackageSnapshotReceipt) -> str:
    payload = receipt.model_dump(mode="json", exclude={"receipt_id"})
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _quarantine_digest(receipt: DirtyWorktreeQuarantineReceipt) -> str:
    payload = receipt.model_dump(mode="json", exclude={"receipt_id"})
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _preservation_receipt_digest(  # noqa: C901, PLR0912 - preserve legacy receipt encoding.
    receipt: WorktreePreservationReceipt,
) -> str:
    payload = receipt.model_dump(mode="json", exclude={"receipt_id"})
    if "provenance" not in receipt.model_fields_set:
        payload.pop("provenance", None)
    elif receipt.provenance is not None:
        evidence_payload = payload.get("provenance")
        if isinstance(evidence_payload, dict):
            for field in ("change_id", "recovery_id", "worktree_path", "workspace_fingerprint"):
                if field not in receipt.provenance.model_fields_set:
                    evidence_payload.pop(field, None)
            evidence_paths = evidence_payload.get("paths")
            if isinstance(evidence_paths, list):
                for item_payload, item in zip(evidence_paths, receipt.provenance.paths, strict=True):
                    if isinstance(item_payload, dict):
                        for field in ("before_kind", "before_digest", "before_mode"):
                            if field not in item.model_fields_set:
                                item_payload.pop(field, None)
    if "paths" in payload:
        for item, entry in zip(payload["paths"], receipt.paths, strict=True):
            if "provenance" not in entry.model_fields_set:
                item.pop("provenance", None)
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _out_of_band_head_recovery_digest(receipt: OutOfBandHeadRecoveryReceipt) -> str:
    payload = receipt.model_dump(mode="json", exclude={"receipt_id"})
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _quarantine_commit_message(operation_id: str) -> str:
    return f"chore: quarantine dirty Builder worktree ({operation_id})"


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
