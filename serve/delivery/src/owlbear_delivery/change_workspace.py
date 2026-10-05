"""Per-change writer coordination and Git workspace management."""

from __future__ import annotations

import errno
import hashlib
import os
import re
import stat
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Literal

from owlbear_delivery.git_executable import resolve_git_executable
from owlbear_delivery.recovery import (
    DeliveryWorkerExclusionRequiredError,
    RecoveryIntent,
    RecoveryReceipt,
    is_canonical_admitted_path,
)
from owlbear_delivery.runtime_transaction import (
    ReplacementTransactionParticipant,
    RuntimeTransaction,
    TransactionParticipant,
)

# Consumer import surface kept at this module path.
from owlbear_delivery.workspace_coordination import (  # noqa: TC001
    PortfolioCoordinator,
)
from owlbear_delivery.workspace_models import (  # noqa: F401
    _INDEX_PATH_LENGTH_MASK,
    _MAX_PRESERVED_FILE_BYTES,
    _MAX_RESTORATION_STAGING_ARTIFACTS,
    _MAX_RESTORATION_STAGING_BYTES,
    _MIN_INDEX_BYTES,
    AdoptExternalHead,
    BuilderHandoffMetadata,
    BuilderHandoffSource,
    CapacityLedger,
    ChangeBuilderHandoff,
    ChangeContinuationAction,
    ChangeCoordination,
    ChangeDesignPackageSnapshotIntent,
    ChangeDesignPackageSnapshotReceipt,
    ChangeDirectOperation,
    ChangeExternalHeadAdoptionReceipt,
    ChangeExternalHeadPromotionReceipt,
    ChangeFinalizationAttempt,
    ChangeFinalizationAttention,
    ChangePauseRequest,
    ChangePauseRequestedError,
    ChangeTargetSyncAbortReceipt,
    ChangeTargetSyncConflictError,
    ChangeTargetSyncConflictState,
    ChangeTargetSyncReceipt,
    ChangeTargetSyncStaleError,
    ChangeWorktreeAttentionCode,
    ChangeWorktreeAttentionError,
    ChangeWorktreeCleanup,
    ChangeWorktreeCleanupIntent,
    ChangeWriter,
    CoordinationConflictError,
    DesignReturnWorkspaceError,
    DirtyWorktreeQuarantineReceipt,
    FinalizerAcquisition,
    IntegrationContext,
    OutOfBandHeadRecoveryReceipt,
    PreparedBuilderHandoff,
    PreservationEntry,
    PreservationFenceError,
    PreservationPathProvenance,
    PreservationProvenanceEvidence,
    PreservationProvenanceProvider,
    PreservationRejectedError,
    PromoteExternalHead,
    PublicationBaselineRecoveryReceipt,
    PublicationBaselineUnavailableError,
    PublicationLease,
    PublicationLock,
    RecoverOutOfBandHead,
    RecoverPublicationBaseline,
    RetainedChangeWorktree,
    SyncChangeWithTarget,
    TargetSyncConflictRequest,
    UnavailablePreservationProvenanceProvider,
    WorkspaceRecoverySnapshot,
    WorktreePreservationReceipt,
    WriterIdentity,
    _branch_name,
    _contains_private_index_metadata,
    _coordination_conflict,
    _decode_optional,
    _directory_identity_tuple,
    _is_change_id,
    _open_directory_no_follow,
    _path_is_contained,
    _preservation_file_identity,
    _PreservedPathState,
    _RegisteredGitWorktree,
    _reject_symlink_ancestors,
    _require_directory_identity,
    _require_worktree_directory,
    _validate_relative_preservation_path,
    _workspace_failure,
)
from owlbear_delivery.workspace_preservation import (
    _PreservationMixin,
)
from owlbear_delivery.workspace_snapshots import (
    _SnapshotMixin,
)
from owlbear_delivery.workspace_target_sync import (
    _TargetSyncMixin,
)
from owlbear_delivery.workspace_worktree_state import (
    _WorktreeStateMixin,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

_ACTIVITY_WALK_MAX_ENTRIES = 200_000
_ACTIVITY_WALK_SECONDS = 5.0


class ChangeWorkspaceManager(_WorktreeStateMixin, _PreservationMixin, _SnapshotMixin, _TargetSyncMixin):
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
        """Read the engine target without fetching or changing it.

        A stale target sync records the newer remote head it fetched, bound to the shared remote-tracking
        ref's value at that fetch's start; the engine selects it while the shared ref still holds that value
        (see ``_record_target_observation``). This read takes no lock: while a ref transaction is being
        applied it can see part of it and briefly return a shared value instead of a recording; a read after
        the transaction sees its result.
        """
        self._require_preservation_environment()
        observations = self._target_observations()
        shared = self._resolve(self._target_ref())
        prefix = self._target_observation_ref(shared)
        heads = [head for ref, head in observations.items() if ref.startswith(prefix)]
        return heads[0] if len(heads) == 1 else shared

    def prepare_runtime_custody_guard(
        self,
        change_id: str,
        *,
        expected_finalization_attention: ChangeFinalizationAttention | None = None,
        operation: str | None = None,
        mutation_class: Literal["completion", "owner-drain", "pause-gated"] = "pause-gated",
    ) -> ReplacementTransactionParticipant:
        """Join current workspace custody and Pause policy to the caller's runtime transaction."""
        return self._coordinator.prepare_runtime_custody_guard(
            change_id,
            expected_finalization_attention=expected_finalization_attention,
            operation=operation,
            mutation_class=mutation_class,
        )

    def record_pause_request(self, request: ChangePauseRequest, expected_frontier_digest: str) -> ChangePauseRequest:
        """Record one custody-neutral Pause request (K1)."""
        return self._coordinator.record_pause_request(request, expected_frontier_digest)

    def clear_pause_request(self, change_id: str, expected_frontier_digest: str) -> ChangePauseRequest | None:
        """Clear one Pause request through the same frontier-bound admission (K1)."""
        return self._coordinator.clear_pause_request(change_id, expected_frontier_digest)

    def prepare_pause_request_clear(
        self, change_id: str, request: ChangePauseRequest
    ) -> ReplacementTransactionParticipant:
        """Join one request's removal to its conversion, completion or abandonment transaction."""
        return self._coordinator.prepare_pause_request_clear(change_id, request)

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

    def worker_process_roots(self, change_id: str) -> tuple[Path, Path]:
        """Return the registered Change worktree and its own Git administration directory."""
        worktree = self._registered_worker_worktree(change_id)
        return worktree, self._resolve_managed_index(worktree).administration

    def _registered_worker_worktree(self, change_id: str) -> Path:
        coordination = self._coordinator.show(change_id)
        worktree = self._canonical_worktree_path(change_id, coordination.worktree_path)
        registration = self._registered_worktrees_all().get(worktree.resolve())
        if registration is None or registration.branch != coordination.branch:
            msg = "worker worktree registration does not match its Change"
            raise PreservationRejectedError(msg)
        return worktree

    def observe_worktree_activity(self, change_id: str) -> datetime:
        """Return the newest change time of a registered Change worktree without refreshing Git state.

        Every non-ignored directory and entry counts, so nested deletions are visible. Git's collapsed
        ignored entries count only by their own times: writes deeper inside an ignored directory (tool
        caches, environments) are not observed. Raises when any observation is unreadable, unsafe,
        exceeds its bound or changes before the walk completes; callers must treat that as active.
        """
        coordination = self._coordinator.show(change_id)
        worktree = self._registered_worker_worktree(change_id)
        ignored = self._ignored_inventory_paths(
            self._preservation_git(
                "status", "--porcelain=v1", "-z", "--ignored=matching", "--untracked-files=normal", cwd=worktree
            ).stdout
        )
        started = time.time_ns()
        observed: dict[Path, _ActivityStamp] = {}
        newest = _worktree_tree_activity_ns(worktree, ignored, observed)
        managed_index = self._resolve_managed_index(worktree)
        roots = (managed_index.administration, managed_index.common_directory)
        head = self._resolved_git_path(worktree, "HEAD", roots)
        reference = self._resolved_git_path(worktree, f"refs/heads/{coordination.branch}", roots, missing_ok=True)
        if reference is None:
            reference = self._resolved_git_path(worktree, "packed-refs", roots)
        for path in (managed_index.path, managed_index.administration, head, reference):
            observed[path] = _activity_stamp(path.lstat())
            newest = max(newest, observed[path].times)
        # Any sampled entry that changed or vanished since it was read invalidates the walk.
        for path, stamp in observed.items():
            try:
                current = _activity_stamp(path.lstat())
            except FileNotFoundError:
                current = None
            if current != stamp:
                msg = "worktree changed while its activity was observed"
                raise PreservationRejectedError(msg)
        if newest >= started:
            newest = max(newest, time.time_ns())
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
    def require_preservation_environment() -> None:
        """Reject inherited Git repository and index overrides before custody reads."""
        ChangeWorkspaceManager._require_preservation_environment()

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
    def _has_ignored_inventory(status: bytes) -> bool:
        return bool(ChangeWorkspaceManager._ignored_inventory_paths(status))

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

    @staticmethod
    def _require_private_staging_readback(
        staged: _PreservedPathState | None,
        expected: _PreservedPathState,
    ) -> None:
        if staged is None or staged.identity is None or not ChangeWorkspaceManager._same_state(staged, expected):
            msg = "private restoration staging failed readback"
            raise PreservationFenceError(msg)

    @staticmethod
    def _dirty_paths(status: bytes) -> tuple[str, ...]:
        return ChangeWorkspaceManager._preservation_status_paths(status)

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

    def release_design_return(
        self, change_id: str, handoff: ChangeBuilderHandoff, lock: PublicationLock
    ) -> ReplacementTransactionParticipant:
        """Capture one retained Design-return handoff under refs, reset to the reviewed head, prepare release.

        Capture order (N04 §1.7): attempt ref, index tree ref, quarantine ref, receipt; reset only after it.
        """
        self._coordinator._require_publication_lock(lock, change_id)  # noqa: SLF001
        coordination = self._coordinator.show(change_id)
        if coordination.builder_handoff != handoff:
            _coordination_conflict("Design return release requires its exact retained Builder handoff")
        if not self._design_return_captured(coordination, handoff):
            self._capture_design_return(coordination, handoff, lock)
        worktree = coordination.worktree_path
        self._git("reset", "--hard", coordination.last_reviewed_commit, cwd=worktree)
        self._git("clean", "-fd", cwd=worktree)
        if self._worktree_change_paths(worktree):
            _workspace_failure("Design return release did not clean the managed worktree")
        self._require_worktree(change_id, worktree, coordination.branch, coordination.last_reviewed_commit)
        return self._coordinator._prepare_design_return_release(change_id, handoff, lock)  # noqa: SLF001

    def _design_return_captured(self, coordination: ChangeCoordination, handoff: ChangeBuilderHandoff) -> bool:
        """Recognize a complete Design-return capture; False when capture has not completed (N04 §1.7)."""
        change_id = coordination.change_id
        attempt_id = handoff.original_writer.attempt_id
        preserved = self._resolve(f"refs/owlbear/attempts/{change_id}/{attempt_id}", missing_ok=True)
        branch_head = self._resolve(coordination.branch)
        receipt = coordination.dirty_worktree_quarantine
        if receipt is None:
            # A clean handoff needs no receipt: it is captured once its head is preserved and the branch reset.
            return (
                preserved == handoff.branch_head
                and branch_head == coordination.last_reviewed_commit
                and not self._worktree_change_paths(coordination.worktree_path)
            )
        index_ref = f"refs/owlbear/quarantine-index/{change_id}/{attempt_id}"
        index_tree = self._git("rev-parse", "--verify", "--quiet", index_ref, check=False)
        if preserved != handoff.branch_head or not index_tree:
            _workspace_failure("Design return quarantine receipt lacks its preservation refs")
        self._require_design_return_index(coordination, index_tree, branch_head)
        try:
            self._prepare_dirty_worktree_quarantine(
                coordination=coordination,
                worktree=coordination.worktree_path,
                branch_head=branch_head,
                quarantine_ref=f"refs/owlbear/quarantine/{change_id}/{attempt_id}",
                operation_id=f"design-return-{handoff.settlement_id}",
                attempt_id=attempt_id,
                claim_id=handoff.original_writer.claim_id,
                index_tree=index_tree,
            )
        except CoordinationConflictError:
            raise
        except RuntimeError as exc:
            raise DesignReturnWorkspaceError.workspace_changed() from exc
        return True

    def _capture_design_return(
        self, coordination: ChangeCoordination, handoff: ChangeBuilderHandoff, lock: PublicationLock
    ) -> None:
        """Preserve head, index and worktree without changing the worktree or the managed index."""
        change_id = coordination.change_id
        attempt_id = handoff.original_writer.attempt_id
        try:
            metadata = self._capture_builder_handoff_metadata(coordination)
        except PreservationFenceError as exc:
            raise DesignReturnWorkspaceError.workspace_changed() from exc
        if metadata.fingerprint != handoff.metadata_fingerprint or metadata.branch_head != handoff.branch_head:
            raise DesignReturnWorkspaceError.workspace_changed()
        worktree = coordination.worktree_path
        if self._preservation_git("ls-files", "--unmerged", cwd=worktree).stdout:
            raise DesignReturnWorkspaceError.unmerged_index()
        attempt_ref = f"refs/owlbear/attempts/{change_id}/{attempt_id}"
        preserved = self._resolve(attempt_ref, missing_ok=True)
        if preserved is None:
            self._git("update-ref", attempt_ref, handoff.branch_head, "0" * 40)
        elif preserved != handoff.branch_head:
            _workspace_failure("attempt history ref names another rejected head")
        if not self._worktree_change_paths(worktree):
            return
        index_tree = self._preserve_index_tree(worktree, f"refs/owlbear/quarantine-index/{change_id}/{attempt_id}")
        if not self._quarantine_paths(worktree, handoff.branch_head, index_tree):
            return  # Only staged differences: the index tree ref holds them all.
        self._prepare_dirty_worktree_quarantine(
            coordination=coordination,
            worktree=worktree,
            branch_head=handoff.branch_head,
            quarantine_ref=f"refs/owlbear/quarantine/{change_id}/{attempt_id}",
            operation_id=f"design-return-{handoff.settlement_id}",
            attempt_id=attempt_id,
            claim_id=handoff.original_writer.claim_id,
            lock=lock,
            index_tree=index_tree,
        )

    def _require_design_return_index(self, coordination: ChangeCoordination, captured: str, branch_head: str) -> None:
        """Refuse an index that is neither the captured tree nor, after the reset, the reviewed tree."""
        worktree = coordination.worktree_path
        try:
            if self._preservation_git("ls-files", "--unmerged", cwd=worktree).stdout:
                raise DesignReturnWorkspaceError.unmerged_index()
            current = self._managed_index_tree(worktree)
        except DesignReturnWorkspaceError:
            raise
        except RuntimeError as exc:
            raise DesignReturnWorkspaceError.workspace_changed() from exc
        allowed = {captured}
        if branch_head == coordination.last_reviewed_commit:
            allowed.add(self._git("rev-parse", f"{branch_head}^{{tree}}"))
        if current not in allowed:
            raise DesignReturnWorkspaceError.workspace_changed()

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


@dataclass(frozen=True)
class _ActivityStamp:
    identity: tuple[int, int, int]
    modified: int
    changed: int

    @property
    def times(self) -> int:
        # ctime also covers tools that restore old modification times.
        return max(self.modified, self.changed)


def _activity_stamp(metadata: os.stat_result) -> _ActivityStamp:
    return _ActivityStamp(
        (metadata.st_dev, metadata.st_ino, stat.S_IFMT(metadata.st_mode)), metadata.st_mtime_ns, metadata.st_ctime_ns
    )


@dataclass
class _ActivityWalkBudget:
    entries: int
    deadline: float

    def consume(self) -> None:
        self.entries -= 1
        if self.entries < 0 or time.monotonic() >= self.deadline:
            msg = "worktree activity walk exceeded its entry or time bound"
            raise PreservationRejectedError(msg)


def _worktree_tree_activity_ns(worktree: Path, ignored: frozenset[str], observed: dict[Path, _ActivityStamp]) -> int:
    """Return the newest mtime/ctime in the worktree, excluding its top-level `.git` and ignored subtrees.

    Records every sampled entry's stamp in `observed` so the caller can revalidate them after the walk.
    """
    budget = _ActivityWalkBudget(_ACTIVITY_WALK_MAX_ENTRIES, time.monotonic() + _ACTIVITY_WALK_SECONDS)
    descriptor = os.open(worktree, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        return _directory_activity_ns(descriptor, budget, (worktree, ""), ignored, observed)
    finally:
        os.close(descriptor)


def _directory_activity_ns(
    descriptor: int,
    budget: _ActivityWalkBudget,
    location: tuple[Path, str],
    ignored: frozenset[str],
    observed: dict[Path, _ActivityStamp],
) -> int:
    directory, prefix = location
    observed[directory] = _activity_stamp(os.fstat(descriptor))
    newest = observed[directory].times
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
            # Files are retained too: an in-place overwrite changes the file without touching its directory.
            entry_stamp = _activity_stamp(entry.stat(follow_symlinks=False))
            observed[directory / entry.name] = entry_stamp
            newest = max(newest, entry_stamp.times)
    for name in directories:
        # O_NOFOLLOW fails closed if the directory was swapped for a symlink after listing.
        child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
        try:
            newest = max(
                newest,
                _directory_activity_ns(child, budget, (directory / name, f"{prefix}{name}/"), ignored, observed),
            )
        finally:
            os.close(child)
    return newest
