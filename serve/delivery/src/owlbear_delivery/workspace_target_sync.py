"""Target synchronization, external-head adoption and promotion, and publication-baseline recovery."""

from __future__ import annotations

import hashlib
import os
from collections.abc import Callable
from itertools import pairwise
from typing import TYPE_CHECKING, Literal, Never

from owlbear_delivery.remote_git import run_remote_git
from owlbear_delivery.storage_io import locked_roots
from owlbear_delivery.workspace_models import (
    _COMMIT_PATTERN,
    _MERGE_COMMIT_MIN_PARENTS,
    _PORCELAIN_WORKTREE_STATUS_INDEX,
    AdoptExternalHead,
    BuilderHandoffSource,
    ChangeCoordination,
    ChangeExternalHeadAdoptionIntent,
    ChangeExternalHeadAdoptionReceipt,
    ChangeExternalHeadPromotionReceipt,
    ChangeTargetSyncAbortReceipt,
    ChangeTargetSyncConflictError,
    ChangeTargetSyncConflictState,
    ChangeTargetSyncReceipt,
    ChangeTargetSyncStaleError,
    ChangeWriter,
    IntegrationContext,
    OutOfBandHeadRecoveryReceipt,
    PreservationFenceError,
    PromoteExternalHead,
    PublicationBaselineRecoveryReceipt,
    PublicationBaselineUnavailableError,
    PublicationLock,
    RecoverOutOfBandHead,
    RecoverPublicationBaseline,
    SyncChangeWithTarget,
    TargetSyncConflictRequest,
    _coordination_conflict,
    _is_settled_finalizer_attention_sync,
    _workspace_failure,
)

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

_TARGET_SYNC_REF_PREFIX = "refs/owlbear/target-sync/"
_TARGET_OBSERVATION_REF_PREFIX = "refs/owlbear/target-observation/"
_ZERO_OID = "0" * 40


class _TargetSyncMixin:
    """Target synchronization, external-head adoption and promotion, and publication-baseline recovery."""

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
        """Fetch one exact target head and merge it only in the managed Change worktree.

        The fetch runs outside every lock into a private per-operation ref, so an unreachable remote
        cannot stall other Changes; the locks cover only the local merge, receipt and shared-ref CAS.
        """
        with self._coordinator.publication_lock(request.change_id):
            coordination = self._coordinator.show(request.change_id)
            previous_receipt = self._replay_target_sync_receipt(request, coordination)
            if previous_receipt is not None:
                return previous_receipt
            self._require_target_sync_start(request, coordination)
        source_ref, target_ref, _target_branch = self._target_refs()
        shared_before = self._resolve(target_ref, missing_ok=True)
        fetched_head, private_ref = self._fetch_target(source_ref, request)
        try:
            if fetched_head != request.expected_target:
                if shared_before is not None:
                    self._record_target_observation(shared_before, fetched_head)
                message = "target changed while it was fetched"
                raise ChangeTargetSyncStaleError(message)
            return self._merge_fetched_target(request, before_head_change, fetched_head, (target_ref, shared_before))
        finally:
            self._run_git("update-ref", "-d", private_ref, fetched_head, check=False)

    def _merge_fetched_target(
        self,
        request: SyncChangeWithTarget,
        before_head_change: Callable[[], None] | None,
        target_head: str,
        shared_target: tuple[str, str | None],
    ) -> ChangeTargetSyncReceipt:
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
            self._advance_shared_target_ref(*shared_target, target_head)
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
        result = run_remote_git(
            self._repository,
            ("fetch", "--no-tags", "--no-write-fetch-head", "--refmap=", self._remote, f"{source_ref}:{remote_ref}"),
            kind="read",
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

    def _fetch_target(self, source_ref: str, request: SyncChangeWithTarget) -> tuple[str, str]:
        # Hashing keeps legal IDs such as ``sync..1`` ref-safe and separates Changes that reuse one ID.
        key = hashlib.sha256(f"{request.change_id}\0{request.operation_id}".encode()).hexdigest()
        private_ref = f"{_TARGET_SYNC_REF_PREFIX}{key}"
        self._git("check-ref-format", private_ref)
        result = run_remote_git(
            self._repository,
            ("fetch", "--no-tags", "--no-write-fetch-head", "--refmap=", self._remote, f"+{source_ref}:{private_ref}"),
            kind="read",
        )
        if result.returncode != 0:
            _workspace_failure("configured target could not be fetched into its private target-sync ref")
        fetched_head = self._resolve(private_ref, missing_ok=True)
        if fetched_head is None:
            _workspace_failure("fetched private target-sync ref is unavailable")
        return fetched_head, private_ref

    def _target_observation_refs(self) -> tuple[str, str]:
        name = self._target_ref().removeprefix("refs/remotes/")
        return f"{_TARGET_OBSERVATION_REF_PREFIX}head/{name}", f"{_TARGET_OBSERVATION_REF_PREFIX}base/{name}"

    def _record_target_observation(self, shared: str, fetched_head: str) -> None:
        """Record a newer remote head for the engine while the shared remote-tracking ref stays unchanged.

        The observation applies only while the shared ref still holds ``shared``, so any later move of
        the shared ref, including an operator fetch, supersedes it.
        """
        head_ref, base_ref = self._target_observation_refs()
        transaction = f"update {head_ref} {fetched_head}\nupdate {base_ref} {shared}\n"
        self._git("update-ref", "--stdin", input_bytes=transaction.encode())

    def _advance_shared_target_ref(self, target_ref: str, observed: str | None, target_head: str) -> None:
        """Move the shared remote-tracking ref to the exact fetched head unless it moved since it was observed.

        The CAS ignores ancestry, so an exact sync after a remote rewind also rewinds the engine target.
        """
        if observed != target_head:
            self._run_git("update-ref", target_ref, target_head, observed or _ZERO_OID, check=False)
        head_ref, base_ref = self._target_observation_refs()
        self._run_git(
            "update-ref",
            "--stdin",
            input_bytes=f"delete {head_ref} {target_head}\ndelete {base_ref}\n".encode(),
            check=False,
        )

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
