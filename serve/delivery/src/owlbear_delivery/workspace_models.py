"""Change workspace records, receipts, errors and pure helpers."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Annotated, Literal, Never, NotRequired, Protocol, Self, TypedDict, Unpack

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from owlbear_delivery.identities import ChangeId
from owlbear_delivery.runtime_transaction import (
    ReplacementTransactionParticipant,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from owlbear_delivery.recovery import (
        RecoveryIntent,
    )

if TYPE_CHECKING:
    from owlbear_delivery.workspace_coordination import (
        PortfolioCoordinator,
    )


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


class ChangePauseRequest(_WorkspaceModel):
    """Durable user Pause policy retained beside custody until it drains into a deferral."""

    request_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    change_id: ChangeId
    reason: str = Field(min_length=1)
    requested_at: str = Field(min_length=1)

    @classmethod
    def create(cls, *, change_id: str, reason: str, requested_at: str) -> Self:
        """Create the deterministic request for one Pause intent."""
        values = {"change_id": change_id, "reason": reason, "requested_at": requested_at}
        return cls(request_id=_pause_request_digest(values), **values)

    @model_validator(mode="after")
    def _validate_identity(self) -> Self:
        datetime.fromisoformat(self.requested_at)
        values = {"change_id": self.change_id, "reason": self.reason, "requested_at": self.requested_at}
        if self.request_id != _pause_request_digest(values):
            message = "Change pause request identity is invalid"
            raise ValueError(message)
        return self


def _pause_request_digest(values: dict[str, str]) -> str:
    return hashlib.sha256(json.dumps(values, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class ChangeDirectOperation(_WorkspaceModel):
    """Drain and replay evidence for one direct engine-owned effect entry; never custody."""

    schema_version: Literal[1] = 1
    change_id: ChangeId
    kind: Literal["sync-target", "mark-ready"]
    operation_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
    request_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    @property
    def marker_name(self) -> str:
        """Return the marker directory bound to this kind and operation identity."""
        return direct_operation_marker_name(self.kind, self.operation_id)


def direct_operation_marker_name(kind: str, operation_id: str) -> str:
    """Name the direct marker directory ``direct-<sha256(kind:operation_id)>``."""
    return f"direct-{hashlib.sha256(f'{kind}:{operation_id}'.encode()).hexdigest()}"


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

    schema_version: Literal[2] = 2
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
    pause_request: ChangePauseRequest | None = Field(default=None, exclude_if=lambda value: value is None)

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
    def _validate_pause_request(self) -> Self:
        if self.pause_request is not None and self.pause_request.change_id != self.change_id:
            message = "Change pause request does not match its Change"
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


class DesignPackageSnapshotEditedError(RuntimeError):
    """Package paths hold bytes an interrupted snapshot did not write; restoring them would lose edits."""

    code = "ERR_DESIGN_PACKAGE_SNAPSHOT_EDITED"
    retry_safe = False

    def __init__(self, change_id: str, paths: tuple[str, ...]) -> None:
        self.change_id = change_id
        self.paths = paths
        super().__init__(f"Design package paths changed after the interrupted snapshot: {', '.join(paths)}")


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


class ChangePauseRequestedError(CoordinationConflictError):
    """A durable Pause request refuses new custody or a new effect start (K3)."""

    code = "ERR_DELIVERY_CHANGE_PAUSE_REQUESTED"

    def __init__(self, detail: str = "Change pause requested") -> None:
        super().__init__(detail)


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


def recovery_authority_content(coordination: ChangeCoordination) -> bytes:
    """Return coordination bytes as recovery authority: v1 shape, without Pause policy (K4)."""
    payload = coordination.model_dump(mode="json")
    payload.pop("pause_request", None)
    payload["schema_version"] = 1
    return f"{json.dumps(payload, sort_keys=True, separators=(',', ':'))}\n".encode()


def recovery_authority_digest(coordination: ChangeCoordination) -> str:
    """Hash recovery authority so a Pause write or clear never invalidates an issued journal."""
    return hashlib.sha256(recovery_authority_content(coordination)).hexdigest()


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
