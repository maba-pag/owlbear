"""Target sync, external heads, supersession, ready/review repair and checkpoint publication."""

from __future__ import annotations

import hashlib
import json
import subprocess
from contextlib import contextmanager, suppress
from typing import TYPE_CHECKING

from owlbear_delivery.application_lifecycle import (
    _READY_DRAIN_MUTATIONS,
    _SNAPSHOT_DRAIN_MUTATIONS,
    _SYNC_DRAIN_MUTATIONS,
)
from owlbear_delivery.application_models import (
    DeliveryAcquisitionFailure,
    DeliveryChangePublicationSupersessionReceipt,
    DeliveryCheckpointReconciliationResult,
    DeliveryRuntimeReconciliationError,
    PortfolioApplicationError,
    _PreEffectReadyObservationError,
    _PreparedCheckpointHead,
    _ReviewRepairAuthority,
    _SupersessionPublishContext,
)
from owlbear_delivery.application_support import (
    _CHECKPOINT_MISSING_HEAD_ERROR_CODE,
    _CHECKPOINT_REVIEW_ERROR_CODE,
    _canonical_model_bytes,
    _checkpoint_awaits_review,
    _checkpoint_error_code,
    _checkpoint_error_detail,
    _checkpoint_operation_id,
    _checkpoint_pull_request_title,
    _checkpoint_retry_ready,
    _checkpoint_summary,
    _failed_required_publication_checks,
    _publication_identity,
    _required_check_diagnostics,
    _timestamp,
)
from owlbear_delivery.change_publication import (
    ChangeBranchPublicationReceipt,
    ChangeBranchSupersessionReceipt,
    PublishChangeBranch,
    SupersedeChangeBranch,
)
from owlbear_delivery.change_workspace import (
    AdoptExternalHead,
    ChangeDirectOperation,
    ChangeExternalHeadAdoptionReceipt,
    ChangeExternalHeadPromotionReceipt,
    ChangePauseRequestedError,
    ChangeTargetSyncAbortReceipt,
    ChangeTargetSyncConflictError,
    ChangeTargetSyncReceipt,
    ChangeTargetSyncStaleError,
    PromoteExternalHead,
    PublicationBaselineUnavailableError,
    SyncChangeWithTarget,
    TargetSyncConflictRequest,
)
from owlbear_delivery.delivery_runtime import (
    DeliveryAcceptanceAttentionReason,
    DeliveryChangeDispositionKind,
    DeliveryChangePublicationHistory,
    DeliveryChangePublicationIdentity,
    DeliveryCheckpointPublicationState,
    DeliveryCheckpointTriggerKind,
    DeliveryFinalizationInvalidationReceipt,
    DeliveryFinalizationReceipt,
    DeliveryPendingCheckpoint,
    DeliveryPendingStatePublication,
    DeliveryRuntime,
    DeliveryRuntimeConflictError,
)
from owlbear_delivery.draft_pull_request import (
    CreateOrReconcileDraftPullRequest,
    DraftPullRequestPublicationHistory,
    DraftPullRequestPublicationReceipt,
    DraftPullRequestPublisher,
    DraftPullRequestSupersessionReceipt,
    MarkChangePullRequestReady,
    ObserveChangePublicationChecks,
    ObserveChangePublicationPullRequest,
    PublicationCheckObservationReceipt,
    PublicationPullRequestObservationReceipt,
    PullRequestReadyReceipt,
    ReadChangePublicationHistory,
    ReturnChangePullRequestToDraft,
    SupersedeDraftPullRequest,
    UpdateGeneratedPullRequestSummary,
)
from owlbear_delivery.publication_provider import (
    PublicationCheck,
    PublicationProviderError,
)
from owlbear_delivery.storage_io import locked_roots

if TYPE_CHECKING:
    from collections.abc import Iterator
    from datetime import datetime

    from owlbear_delivery.delivery_state import DeliveryStatePublisher
    from owlbear_delivery.workspace_models import ChangeDesignPackageSnapshotReceipt

# K2/K7 writes each started operator entry finishes under its own token.
_ADOPTION_WRITES = ("clear_ready_for_head_change", "capture_change_disposition", "record_external_head_adoption")
_FINALIZATION_HEAD_WRITES = (
    "reconcile_finalization_head",
    "capture_change_disposition",
    "reconcile_pull_request_draft_state",
    "record_external_head_promotion",
)


def _direct_operation(change_id: str, kind: str, operation_id: str, *request: str | None) -> ChangeDirectOperation:
    """Bind one direct entry's marker to its exact request (K2 direct markers)."""
    request_digest = hashlib.sha256(
        json.dumps([change_id, kind, operation_id, *request], separators=(",", ":")).encode()
    ).hexdigest()
    return ChangeDirectOperation(
        change_id=change_id,
        kind=kind,  # type: ignore[arg-type]
        operation_id=operation_id,
        request_digest=request_digest,
    )


def _snapshot_identity(operation_id: str, package_id: str, previous_head: str) -> str:
    """Bind a snapshot token to one snapshot operation, package and pre-snapshot head (K2 snapshot row)."""
    return f"{operation_id}:{package_id}:{previous_head}"


class _PublicationMixin:
    """Target sync, external heads, supersession, ready/review repair and checkpoint publication."""

    def observe_change_publication_checks(
        self,
        change_id: str,
    ) -> PublicationCheckObservationReceipt:
        """Observe provider checks at the exact durable published Change head."""
        if self._draft_pull_request_publisher is None:
            message = "draft pull-request publication is not configured"
            raise PortfolioApplicationError(message)
        published_head = self._runtime(change_id).checkpoint_publication_state().published_head
        if published_head is None:
            message = "Change has no reconciled checkpoint publication"
            raise PortfolioApplicationError(message)
        return self._draft_pull_request_publisher.observe_checks(
            ObserveChangePublicationChecks(change_id=change_id, published_head=published_head)
        )

    def sync_change_with_target(
        self,
        change_id: str,
        expected_target: str,
        operation_id: str,
    ) -> ChangeTargetSyncReceipt:
        """Fetch and merge one exact target head through the managed Change worktree."""
        runtime = self._runtime(change_id, for_mutation=True)
        request = SyncChangeWithTarget(
            change_id=change_id,
            expected_target=expected_target,
            operation_id=operation_id,
        )
        with self._engine_checkpoint_lock(change_id):
            self._require_target_sync_change_mutable(runtime)
            self._require_no_review_repair(runtime, "target synchronization")
            if runtime.change_disposition() is not None:
                self._fail("target synchronization requires Change attention resolution first")
            if runtime.active_claims() or runtime.integration_repair_claim() is not None:
                self._fail("target synchronization cannot overlap an active Delivery claim")
            direct = (
                None
                if self._coordinator.executing_continuation(change_id)
                else _direct_operation(change_id, "sync-target", operation_id, expected_target)
            )
            with self._owner_drain_authority(
                change_id, f"sync-target:{operation_id}", *_SYNC_DRAIN_MUTATIONS, publishes_checkpoint=True
            ):
                receipt = self._sync_change_with_target_owned(change_id, runtime, request, direct)
                self._finish_direct_operation(direct)
            self._try_convert_pause_request(change_id, runtime)
            return receipt

    def _finish_direct_operation(self, direct: ChangeDirectOperation | None) -> None:
        """Write ``finished.json`` before a direct entry returns, when its own start marker exists."""
        if direct is not None and self._coordinator.direct_operation_state(direct) == "started":
            self._coordinator.finish_direct_operation(direct)

    def _sync_change_with_target_owned(
        self,
        change_id: str,
        runtime: DeliveryRuntime,
        request: SyncChangeWithTarget,
        direct: ChangeDirectOperation | None,
    ) -> ChangeTargetSyncReceipt:
        operation_id = request.operation_id
        try:
            receipt = self._workspace_manager.sync_with_target(
                request,
                before_head_change=lambda: self._return_publication_to_draft_before_head_change(
                    change_id,
                    runtime,
                    operation_id,
                ),
                direct_operation=direct,
            )
        except ChangeTargetSyncStaleError:
            raise
        except ChangePauseRequestedError:
            raise
        except ChangeTargetSyncConflictError as exc:
            history = runtime.publication_history()
            runtime.capture_target_sync_conflict(
                exc.operation_id,
                exc.target_head,
                _timestamp(self._clock()),
                (
                    "target synchronization merge conflict",
                    *tuple(f"conflict-path:{path}" for path in exc.conflict_paths),
                ),
                publication_identity=history.current if history is not None else None,
            )
            self._publish_attention_best_effort(
                change_id,
                runtime,
                f"target-sync-attention-{exc.operation_id}",
            )
            self._finish_direct_operation(direct)
            raise
        except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as exc:
            self._fail("target synchronization could not be completed", exc)
        finalization = runtime.finalization()
        proof = runtime.target_sync_receipt()
        if (
            finalization is not None
            and receipt.merged_head == finalization.exact_head
            and (proof is None or proof.target_head != receipt.target_head)
        ):
            # Strict proof: a new target returns the PR to draft even when the Change head is unchanged.
            self._return_publication_to_draft_before_head_change(change_id, runtime, operation_id)
        runtime.record_target_sync(receipt, _timestamp(self._clock()))
        self._publish_target_sync_branch(change_id, runtime, receipt.merged_head)
        self._publish_delivery_state(change_id, runtime, f"target-sync-{receipt.receipt_id}")
        self._acknowledge_published_target_sync_checkpoint(runtime, receipt.merged_head)
        return receipt

    def sync_change_with_current_target(
        self,
        change_id: str,
        operation_id: str,
    ) -> ChangeTargetSyncReceipt:
        """Bind the current remote-tracking target and perform one exact sync operation."""
        try:
            expected_target = self._workspace_manager.integration_context(change_id).target_head
        except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as exc:
            self._fail("target synchronization target head is unavailable", exc)
        return self.sync_change_with_target(change_id, expected_target, operation_id)

    def adopt_external_head(
        self,
        change_id: str,
        expected_head: str,
        adopted_head: str,
        operation_id: str,
    ) -> ChangeExternalHeadAdoptionReceipt:
        """Adopt one exact remote Change descendant through managed workspace custody."""
        runtime = self._runtime(change_id, for_mutation=True)
        request = AdoptExternalHead(
            change_id=change_id,
            expected_head=expected_head,
            adopted_head=adopted_head,
            operation_id=operation_id,
        )
        with (
            locked_roots((self._checkpoint_lock_root(change_id),)),
            self._operator_start(change_id, f"adopt:{operation_id}", *_ADOPTION_WRITES),
        ):
            self._require_external_head_adoption_change_mutable(runtime)
            self._require_no_review_repair(runtime, "external Change head adoption")
            if runtime.change_disposition() is not None:
                self._fail("external Change head adoption requires Change attention resolution first")
            if runtime.active_claims() or runtime.integration_repair_claim() is not None:
                self._fail("external Change head adoption cannot overlap an active Delivery claim")
            publication_identity = runtime.change_disposition_publication()
            if publication_identity is None:
                ready = runtime.ready_receipt()
                if ready is not None:
                    publication_identity = DeliveryChangePublicationIdentity(
                        change_id=ready.change_id,
                        repository=ready.repository,
                        number=ready.number,
                        node_id=ready.node_id,
                        head_sha=ready.head_sha,
                    )
            demoted = False

            def demote_before_head_change() -> None:
                nonlocal demoted
                self._return_publication_to_draft_before_head_change(
                    change_id,
                    runtime,
                    operation_id,
                )
                demoted = True

            try:
                receipt = self._workspace_manager.adopt_external_head(
                    request,
                    before_head_change=demote_before_head_change,
                )
            except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as exc:
                if demoted:
                    with suppress(DeliveryRuntimeConflictError):
                        runtime.capture_publication_attention(
                            _timestamp(self._clock()),
                            (
                                "external-head-adoption-movement-failed",
                                f"external-head-adoption-operation:{operation_id}",
                                f"expected-head:{expected_head}",
                                f"adopted-head:{adopted_head}",
                            ),
                            publication_identity=publication_identity,
                        )
                        self._publish_attention_best_effort(
                            change_id,
                            runtime,
                            f"adoption-attention-{operation_id}",
                        )
                self._fail("external Change head could not be adopted", exc)
            runtime.record_external_head_adoption(receipt, _timestamp(self._clock()))
            self._publish_delivery_state(change_id, runtime, f"adoption-{receipt.receipt_id}")
            return receipt

    def adopt_external_head_after_acceptance_attention(
        self,
        change_id: str,
        expected_disposition_id: str,
        expected_head: str,
        adopted_head: str,
        operation_id: str,
    ) -> ChangeExternalHeadAdoptionReceipt:
        """Adopt one moved open PR head after exact acceptance-attention validation."""
        publisher = self._draft_pull_request_publisher
        if publisher is None:
            self._fail("acceptance head adoption requires a publication provider")
        runtime = self._runtime(change_id, for_mutation=True)
        request = AdoptExternalHead(
            change_id=change_id,
            expected_head=expected_head,
            adopted_head=adopted_head,
            operation_id=operation_id,
        )
        with (
            locked_roots((self._checkpoint_lock_root(change_id),)),
            self._operator_start(change_id, f"adopt:{operation_id}", *_ADOPTION_WRITES, "resolve_change_disposition"),
        ):
            disposition = runtime.change_disposition()
            if (
                disposition is None
                or disposition.disposition_id != expected_disposition_id
                or disposition.kind != DeliveryChangeDispositionKind.ACCEPTANCE_ATTENTION
                or disposition.acceptance_reason != DeliveryAcceptanceAttentionReason.HEAD_MOVED
            ):
                self._fail("acceptance head adoption requires matching head-moved attention")
            publication = runtime.change_disposition_publication()
            if publication is None or publication.head_sha != adopted_head:
                self._fail("acceptance head adoption does not match observed pull-request authority")
            coordination = self._workspace_manager.show(change_id)
            if coordination.last_reviewed_commit != expected_head:
                self._fail("acceptance head adoption expected head differs from the reviewed boundary")
            if runtime.active_claims() or runtime.integration_repair_claim() is not None:
                self._fail("acceptance head adoption cannot overlap an active Delivery claim")
            observation = publisher.observe_pull_request(ObserveChangePublicationPullRequest(change_id=change_id))
            if observation is None or observation.snapshot.state != "open" or observation.snapshot.merged:
                self._fail("acceptance head adoption requires an open unmerged pull request")
            if observation.snapshot.head_sha != adopted_head:
                self._fail("acceptance head adoption pull-request head changed")
            try:
                receipt = self._workspace_manager.adopt_external_head(
                    request,
                    before_head_change=lambda: self._return_publication_to_draft_before_head_change(
                        change_id,
                        runtime,
                        operation_id,
                        finalization_id=(
                            runtime.finalization_invalidation().finalization_id
                            if runtime.finalization_invalidation() is not None
                            else None
                        ),
                    ),
                )
            except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as exc:
                self._fail("external Change head could not be adopted", exc)
            resolved_at = _timestamp(self._clock())
            runtime.resolve_change_disposition(expected_disposition_id, resolved_at)
            runtime.record_external_head_adoption(receipt, resolved_at)
            self._publish_delivery_state(change_id, runtime, f"adoption-{receipt.receipt_id}")
            return receipt

    def promote_external_head(
        self,
        change_id: str,
        expected_head: str,
        operation_id: str,
    ) -> ChangeExternalHeadPromotionReceipt:
        """Promote one exact adopted head before granting Builder authority."""
        runtime = self._runtime(change_id, for_mutation=True)
        with (
            locked_roots((self._checkpoint_lock_root(change_id),)),
            self._operator_start(change_id, f"promote:{operation_id}", "record_external_head_promotion"),
        ):
            self._require_external_head_promotion_change_mutable(runtime)
            self._require_no_review_repair(runtime, "external Change head promotion")
            if runtime.change_disposition() is not None:
                self._fail("external Change-head promotion requires Change attention resolution first")
            if runtime.active_claims() or runtime.integration_repair_claim() is not None:
                self._fail("external Change-head promotion cannot overlap an active Delivery claim")
            request = PromoteExternalHead(
                change_id=change_id,
                expected_head=expected_head,
                operation_id=operation_id,
            )
            coordination = self._workspace_manager.show(change_id)
            promotion = coordination.external_head_promotion_receipt
            runtime_promotion = runtime.external_head_promotion_receipt()
            if promotion != runtime_promotion and (
                promotion is None or promotion.operation_id != operation_id or promotion.promoted_head != expected_head
            ):
                self._fail("external Change-head promotion requires reconciled promotion evidence")
            adoption = coordination.external_head_adoption_receipt
            if adoption is None or runtime.external_head_adoption_receipt() != adoption:
                self._fail("external Change-head promotion requires reconciled adoption evidence")
            try:
                promoted = self._workspace_manager.promote_external_head(request)
            except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as exc:
                self._fail("external Change head could not be promoted", exc)
            if promoted is None:
                self._fail("external Change-head promotion has no adopted head to promote")
            runtime.record_external_head_promotion(promoted, _timestamp(self._clock()))
            self._publish_delivery_state(change_id, runtime, f"promotion-{promoted.receipt_id}")
            return promoted

    def abort_target_sync_conflict(
        self,
        change_id: str,
        expected_disposition_id: str,
        target_head: str,
        operation_id: str,
    ) -> ChangeTargetSyncAbortReceipt:
        """Abort one exact preserved target merge and clear its attention."""
        runtime = self._runtime(change_id, for_mutation=True)
        with (
            locked_roots((self._checkpoint_lock_root(change_id),)),
            self._operator_start(change_id, f"target-sync-abort:{operation_id}", "record_target_sync_abort"),
        ):
            disposition = runtime.change_disposition()
            attention_active = disposition is not None
            if attention_active:
                runtime.validate_target_sync_conflict(expected_disposition_id, operation_id)
                self._require_target_sync_change_mutable(runtime)
            else:
                resolution = runtime.change_disposition_resolution()
                if resolution is None or resolution.disposition_id != expected_disposition_id:
                    runtime.validate_target_sync_conflict(expected_disposition_id, operation_id)
            if runtime.active_claims() or runtime.integration_repair_claim() is not None:
                self._fail("target synchronization conflict exit cannot overlap an active Delivery claim")
            request = TargetSyncConflictRequest(
                change_id=change_id,
                target_head=target_head,
                operation_id=operation_id,
            )
            try:
                receipt = self._workspace_manager.abort_target_sync_conflict(request)
            except (OSError, subprocess.SubprocessError, ValueError) as exc:
                self._fail("target synchronization conflict could not be aborted", exc)
            if attention_active:
                resolution = runtime.record_target_sync_abort(
                    expected_disposition_id,
                    operation_id,
                    _timestamp(self._clock()),
                )
                self._publish_delivery_state(change_id, runtime, f"target-sync-abort-{resolution.resolution_id}")
            return receipt

    def resolve_target_sync_conflict(
        self,
        change_id: str,
        expected_disposition_id: str,
        target_head: str,
        operation_id: str,
    ) -> ChangeTargetSyncReceipt:
        """Record one exact semantic target merge and clear its attention."""
        runtime = self._runtime(change_id, for_mutation=True)
        request = TargetSyncConflictRequest(
            change_id=change_id,
            target_head=target_head,
            operation_id=operation_id,
        )
        with (
            locked_roots((self._checkpoint_lock_root(change_id),)),
            self._operator_start(
                change_id,
                f"target-sync-resolve:{operation_id}",
                "record_resolved_target_sync",
                publishes_checkpoint=True,
            ),
        ):
            existing = runtime.target_sync_receipt()
            if existing is not None:
                return self._replay_target_sync_resolution(
                    runtime,
                    existing,
                    expected_disposition_id,
                    request,
                )
            return self._record_target_sync_resolution(
                runtime,
                expected_disposition_id,
                request,
            )

    def _replay_target_sync_resolution(
        self,
        runtime: DeliveryRuntime,
        existing: ChangeTargetSyncReceipt,
        expected_disposition_id: str,
        request: TargetSyncConflictRequest,
    ) -> ChangeTargetSyncReceipt:
        if existing.operation_id != request.operation_id or existing.target_head != request.target_head:
            self._fail("target synchronization resolution identity differs from runtime evidence")
        if runtime.change_disposition() is not None:
            runtime.validate_target_sync_conflict(expected_disposition_id, request.operation_id)
        else:
            resolution = runtime.change_disposition_resolution()
            if resolution is None or resolution.disposition_id != expected_disposition_id:
                self._fail("target synchronization resolution attention identity differs from runtime evidence")
        receipt = self._resolve_target_sync_workspace(request)
        if receipt != existing:
            self._fail("target synchronization resolution differs from runtime evidence")
        resolution = runtime.change_disposition_resolution()
        if resolution is not None:
            checkpoint = runtime.checkpoint_publication_state()
            if checkpoint.published_head != receipt.merged_head:
                self._publish_target_sync_branch(request.change_id, runtime, receipt.merged_head)
            self._publish_delivery_state(
                request.change_id,
                runtime,
                f"target-sync-resolution-{resolution.resolution_id}",
            )
            self._acknowledge_published_target_sync_checkpoint(runtime, receipt.merged_head)
        return receipt

    def _record_target_sync_resolution(
        self,
        runtime: DeliveryRuntime,
        expected_disposition_id: str,
        request: TargetSyncConflictRequest,
    ) -> ChangeTargetSyncReceipt:
        runtime.validate_target_sync_conflict(expected_disposition_id, request.operation_id)
        self._require_target_sync_change_mutable(runtime)
        if runtime.active_claims() or runtime.integration_repair_claim() is not None:
            self._fail("target synchronization conflict exit cannot overlap an active Delivery claim")
        receipt = self._resolve_target_sync_workspace(request)
        receipt = runtime.record_resolved_target_sync(
            receipt,
            expected_disposition_id,
            request.operation_id,
            _timestamp(self._clock()),
        )
        resolution = runtime.change_disposition_resolution()
        if resolution is None:
            self._fail("target synchronization resolution did not record attention resolution")
        self._publish_target_sync_branch(request.change_id, runtime, receipt.merged_head)
        self._publish_delivery_state(
            request.change_id,
            runtime,
            f"target-sync-resolution-{resolution.resolution_id}",
        )
        self._acknowledge_published_target_sync_checkpoint(runtime, receipt.merged_head)
        return receipt

    def _resolve_target_sync_workspace(
        self,
        request: TargetSyncConflictRequest,
    ) -> ChangeTargetSyncReceipt:
        try:
            return self._workspace_manager.resolve_target_sync_conflict(request)
        except (OSError, subprocess.SubprocessError, ValueError) as exc:
            self._fail("target synchronization conflict could not be resolved", exc)

    def supersede_publication(
        self,
        change_id: str,
        expected_publication_id: str,
        operation_id: str,
    ) -> DeliveryChangePublicationSupersessionReceipt:
        """Publish one successor branch and PR for an exact publication attention."""
        if self._change_branch_publisher is None or self._draft_pull_request_publisher is None:
            self._fail("publication supersession is not configured")
        runtime = self._runtime(change_id, for_mutation=True)
        with locked_roots((self._checkpoint_lock_root(change_id),)):
            self._require_fresh_target_sync_review(runtime)
            runtime_history, predecessor, replay_head = self._read_supersession_context(
                runtime,
                change_id,
                expected_publication_id,
                operation_id,
            )

            try:
                superseding_head = self._workspace_manager.reviewed_source_head(change_id)
            except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as exc:
                self._fail("publication supersession requires a clean reviewed Change head", exc)
            if replay_head is not None and superseding_head != replay_head:
                self._fail("publication supersession replay requires the stored successor head")

            with self._owner_drain_authority(
                change_id, f"lease:{operation_id}", publishes_checkpoint=True, requires_lease=True
            ) as lease_authority:
                git_receipt, provider_receipt = self._publish_supersession(
                    runtime,
                    _SupersessionPublishContext(
                        change_id=change_id,
                        expected_publication_id=expected_publication_id,
                        operation_id=operation_id,
                        predecessor=predecessor,
                        superseding_head=superseding_head,
                        target_branch=self._draft_pull_request_publisher.target_branch,
                    ),
                )
                # The lease owner finishes its own successor binding after its push (K2 lease row).
                lease_authority.permit("mutation", "record_publication_successor", "reconcile_finalization_head")
                finalization = runtime.finalization()
                if finalization is not None and finalization.exact_head != superseding_head:
                    runtime.reconcile_finalization_head(superseding_head, _timestamp(self._clock()))
                updated_history = self._bind_supersession_successor(
                    runtime,
                    runtime_history,
                    predecessor,
                    provider_receipt,
                )
                self._publish_delivery_state(
                    change_id, runtime, f"supersession-{provider_receipt.successor_publication.receipt_id}"
                )
            self._try_convert_pause_request(change_id, runtime)
            return DeliveryChangePublicationSupersessionReceipt.create(
                operation_id=operation_id,
                predecessor_publication_id=expected_publication_id,
                git_supersession=git_receipt,
                provider_supersession=provider_receipt,
                publication_history=updated_history,
            )

    def supersede_current_publication(
        self,
        change_id: str,
        operation_id: str,
    ) -> DeliveryChangePublicationSupersessionReceipt:
        """Resolve the current provider publication before starting one successor operation."""
        publisher = self._draft_pull_request_publisher
        if publisher is None:
            self._fail("publication supersession is not configured")
        self._require_fresh_target_sync_review(self._runtime(change_id, for_mutation=True))
        try:
            superseding_head = self._workspace_manager.reviewed_source_head(change_id)
            self._workspace_manager.repository_automation_paths(change_id, superseding_head)
        except PublicationBaselineUnavailableError:
            raise
        except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as exc:
            self._fail("publication supersession requires a clean reviewed Change head", exc)
        provider_history = publisher.read_publication_history(ReadChangePublicationHistory(change_id=change_id))
        if provider_history is None:
            self._fail("publication supersession requires current provider publication history")
        return self.supersede_publication(change_id, provider_history.current_receipt_id, operation_id)

    def _read_supersession_context(
        self,
        runtime: DeliveryRuntime,
        change_id: str,
        expected_publication_id: str,
        operation_id: str,
    ) -> tuple[DeliveryChangePublicationHistory, DraftPullRequestPublicationReceipt, str | None]:
        disposition = runtime.change_disposition()
        if disposition is None or disposition.kind != DeliveryChangeDispositionKind.PUBLICATION_ATTENTION:
            self._fail("publication supersession requires current publication attention")
        runtime_history = runtime.publication_history()
        if runtime_history is None:
            self._fail("publication supersession requires current runtime publication history")
        if runtime.change_disposition_publication() != runtime_history.current:
            self._fail("publication attention does not retain the current runtime publication")
        publisher = self._draft_pull_request_publisher
        if publisher is None:
            self._fail("publication supersession is not configured")
        provider_history = publisher.read_publication_history(ReadChangePublicationHistory(change_id=change_id))
        if provider_history is None:
            self._fail("publication supersession requires current provider publication history")
        predecessor = next(
            (
                publication
                for publication in provider_history.publications
                if publication.receipt_id == expected_publication_id
            ),
            None,
        )
        if predecessor is None:
            self._fail("expected publication identity is not in provider publication history")
        replay_head = self._validate_supersession_history(
            runtime_history,
            provider_history,
            predecessor,
            expected_publication_id,
            operation_id,
        )
        if predecessor.base_branch != publisher.target_branch:
            self._fail("publication predecessor targets a different integration branch")
        return runtime_history, predecessor, replay_head

    def _validate_supersession_history(
        self,
        runtime_history: DeliveryChangePublicationHistory,
        provider_history: DraftPullRequestPublicationHistory,
        predecessor: DraftPullRequestPublicationReceipt,
        expected_publication_id: str,
        operation_id: str,
    ) -> str | None:
        predecessor_identity = _publication_identity(predecessor)
        provider_current = provider_history.publications[-1]
        provider_current_identity = _publication_identity(provider_current)
        if provider_current.receipt_id == expected_publication_id:
            if runtime_history.current != predecessor_identity:
                self._fail("runtime and provider publication predecessors differ")
            return None
        if (
            provider_current.operation_id != operation_id
            or provider_history.predecessor_receipt_ids[-1] != expected_publication_id
            or runtime_history.current not in (predecessor_identity, provider_current_identity)
        ):
            self._fail("provider publication history has a different current successor")
        return provider_current.head_sha

    def _publish_supersession(
        self,
        runtime: DeliveryRuntime,
        context: _SupersessionPublishContext,
    ) -> tuple[ChangeBranchSupersessionReceipt, DraftPullRequestSupersessionReceipt]:
        branch_publisher = self._change_branch_publisher
        provider_publisher = self._draft_pull_request_publisher
        if branch_publisher is None or provider_publisher is None:
            self._fail("publication supersession is not configured")
        package = self._package_store.read_verified(context.change_id)
        self._validate_package_authority(runtime, package)
        automation_paths = self._workspace_manager.repository_automation_paths(
            context.change_id,
            context.superseding_head,
        )
        git_receipt = branch_publisher.supersede(
            SupersedeChangeBranch(
                change_id=context.change_id,
                expected_published_branch=context.predecessor.head_branch,
                expected_published_head=context.predecessor.head_sha,
                superseding_head=context.superseding_head,
                operation_id=context.operation_id,
            )
        )
        self._validate_git_supersession(
            git_receipt,
            context,
        )
        provider_receipt = provider_publisher.supersede(
            SupersedeDraftPullRequest(
                change_id=context.change_id,
                operation_id=context.operation_id,
                expected_predecessor_receipt_id=context.expected_publication_id,
                predecessor_branch=context.predecessor.head_branch,
                predecessor_head=context.predecessor.head_sha,
                successor_branch=git_receipt.successor_branch,
                superseding_head=context.superseding_head,
                title=_checkpoint_pull_request_title(runtime),
                generated_summary=_checkpoint_summary(
                    runtime,
                    package,
                    None,
                    context.superseding_head,
                    automation_paths,
                    supersedes_publication_id=context.expected_publication_id,
                ),
            )
        )
        self._validate_provider_supersession(
            provider_receipt,
            git_receipt,
            context,
        )
        return git_receipt, provider_receipt

    def _bind_supersession_successor(
        self,
        runtime: DeliveryRuntime,
        runtime_history: DeliveryChangePublicationHistory,
        predecessor: DraftPullRequestPublicationReceipt,
        provider_receipt: DraftPullRequestSupersessionReceipt,
    ) -> DeliveryChangePublicationHistory:
        predecessor_identity = _publication_identity(predecessor)
        successor_identity = _publication_identity(provider_receipt.successor_publication)
        if runtime_history.current == successor_identity:
            return runtime_history
        if runtime_history.current != predecessor_identity:
            self._fail("runtime publication history cannot bind the provider successor")
        return runtime.record_publication_successor(predecessor_identity, successor_identity)

    @staticmethod
    def _validate_git_supersession(
        receipt: ChangeBranchSupersessionReceipt,
        context: _SupersessionPublishContext,
    ) -> None:
        if (
            receipt.change_id != context.change_id
            or receipt.predecessor_branch != context.predecessor.head_branch
            or receipt.predecessor_head != context.predecessor.head_sha
            or receipt.superseding_head != context.superseding_head
        ):
            message = "Git supersession receipt does not match provider publication authority"
            raise PortfolioApplicationError(message)

    @staticmethod
    def _validate_provider_supersession(
        receipt: DraftPullRequestSupersessionReceipt,
        git_receipt: ChangeBranchSupersessionReceipt,
        context: _SupersessionPublishContext,
    ) -> None:
        if (
            receipt.change_id != context.change_id
            or receipt.predecessor_receipt_id != context.expected_publication_id
            or receipt.predecessor_branch != git_receipt.predecessor_branch
            or receipt.predecessor_head != git_receipt.predecessor_head
            or receipt.successor_branch != git_receipt.successor_branch
            or receipt.superseding_head != git_receipt.superseding_head
            or receipt.base_branch != context.target_branch
        ):
            message = "provider supersession receipt does not match Git publication authority"
            raise PortfolioApplicationError(message)

    def mark_change_ready(
        self,
        change_id: str,
        request: MarkChangePullRequestReady,
    ) -> PullRequestReadyReceipt:
        """Mark the exact finalized and fully published Change pull request ready."""
        if self._draft_pull_request_publisher is None:
            message = "draft pull-request publication is not configured"
            raise PortfolioApplicationError(message)
        runtime = self._runtime(change_id, for_mutation=True)
        with self._engine_checkpoint_lock(change_id):
            if runtime.change_disposition() is not None:
                message = "pull-request readiness requires current Change attention resolution"
                raise PortfolioApplicationError(message)
            finalization = runtime.finalization()
            publication = runtime.checkpoint_publication_state()
            if (
                finalization is None
                or request.change_id != change_id
                or request.finalization_id != finalization.finalization_id
                or request.exact_head != finalization.exact_head
            ):
                message = "pull-request ready request does not match current finalization authority"
                raise PortfolioApplicationError(message)
            if publication.published_head != finalization.exact_head or publication.pending_checkpoint is not None:
                message = "pull-request readiness requires the reconciled final checkpoint"
                raise PortfolioApplicationError(message)
            direct = (
                None
                if self._coordinator.executing_continuation(change_id)
                else _direct_operation(
                    change_id, "mark-ready", request.operation_id, request.finalization_id, request.exact_head
                )
            )
            if direct is not None and self._coordinator.direct_operation_state(direct) == "finished":
                # Replay after finished.json: the existing replay answers and no token is granted (§1.6).
                return self._mark_change_ready_owned(change_id, runtime, request, finalization)
            if direct is not None:
                self._coordinator.start_direct_operation(direct)
            with self._owner_drain_authority(change_id, f"mark-ready:{request.operation_id}", *_READY_DRAIN_MUTATIONS):
                ready = self._mark_change_ready_owned(change_id, runtime, request, finalization)
                self._finish_direct_operation(direct)
            self._try_convert_pause_request(change_id, runtime)
            return ready

    def _mark_change_ready_owned(
        self,
        change_id: str,
        runtime: DeliveryRuntime,
        request: MarkChangePullRequestReady,
        finalization: DeliveryFinalizationReceipt,
    ) -> PullRequestReadyReceipt:
        publisher = self._draft_pull_request_publisher
        if publisher is None:
            message = "draft pull-request publication is not configured"
            raise PortfolioApplicationError(message)
        existing_ready = runtime.ready_receipt()
        if (
            existing_ready is not None
            and existing_ready.finalization_id == finalization.finalization_id
            and existing_ready.head_sha == finalization.exact_head
        ):
            receipt = publisher.mark_ready(request)
            ready = runtime.mark_awaiting_merge(receipt)
            self._publish_delivery_state(change_id, runtime, f"ready-{ready.receipt_id}")
            return ready
        try:
            observation, failures = self._observe_required_checks_for_ready(
                change_id,
                finalization.exact_head,
            )
        except PublicationProviderError as exc:
            if not exc.retry_safe:
                raise
            raise _PreEffectReadyObservationError(
                exc.code,
                exc.operation,
                str(exc),
                retry_safe=True,
            ) from exc
        receipt = publisher.mark_ready(request)
        ready = runtime.mark_awaiting_merge(receipt)
        if failures:
            self._record_required_check_attention(runtime, observation, failures, ready)
        self._publish_delivery_state(change_id, runtime, f"ready-{ready.receipt_id}")
        return ready

    def _observe_required_checks_for_ready(
        self,
        change_id: str,
        exact_head: str,
    ) -> tuple[PublicationCheckObservationReceipt, tuple[PublicationCheck, ...]]:
        """Observe provider-required checks without gating the pull-request ready state."""
        publisher = self._draft_pull_request_publisher
        if publisher is None:
            message = "draft pull-request publication is not configured"
            raise PortfolioApplicationError(message)
        observation = publisher.observe_checks(
            ObserveChangePublicationChecks(change_id=change_id, published_head=exact_head)
        )
        failures = _failed_required_publication_checks(observation.snapshot)
        return observation, failures

    @staticmethod
    def _record_required_check_attention(
        runtime: DeliveryRuntime,
        observation: PublicationCheckObservationReceipt,
        failures: tuple[PublicationCheck, ...],
        ready: PullRequestReadyReceipt,
    ) -> None:
        """Retain failing provider-required checks after the PR is ready."""
        runtime.capture_publication_attention(
            observation.observed_at,
            _required_check_diagnostics(observation.snapshot, observation.observation_id, failures),
            publication_identity=DeliveryChangePublicationIdentity(
                change_id=ready.change_id,
                repository=ready.repository,
                number=ready.number,
                node_id=ready.node_id,
                head_sha=ready.head_sha,
            ),
        )

    def mark_current_change_ready(self, change_id: str) -> PullRequestReadyReceipt:
        """Mark the current exact finalization ready without caller-supplied authority."""
        finalization = self._runtime(change_id).finalization()
        if finalization is None:
            message = "pull-request readiness requires current finalization authority"
            raise PortfolioApplicationError(message)
        return self.mark_change_ready(
            change_id,
            MarkChangePullRequestReady(
                change_id=change_id,
                operation_id=f"ready-{finalization.finalization_id}",
                finalization_id=finalization.finalization_id,
                exact_head=finalization.exact_head,
            ),
        )

    def prepare_review_repair(self, change_id: str) -> DeliveryFinalizationInvalidationReceipt:
        """Return an open Change pull request to draft before external review repair."""
        publisher = self._draft_pull_request_publisher
        if publisher is None:
            message = "review repair requires a publication provider"
            raise PortfolioApplicationError(message)
        runtime = self._runtime(change_id, for_mutation=True)
        with (
            locked_roots((self._checkpoint_lock_root(change_id),)),
            self._operator_start(change_id, "review-repair", "prepare_review_repair"),
        ):
            authority = self._review_repair_authority(runtime)
            observation = self._observe_review_repair_pull_request(change_id, publisher, authority)
            replayed = self._replay_review_repair(change_id, publisher, authority, observation)
            if replayed is not None:
                return replayed
            if not observation.snapshot.draft:
                publisher.return_to_draft(
                    ReturnChangePullRequestToDraft(
                        change_id=change_id,
                        operation_id=f"review-repair-draft-{authority.expected_finalization_id}",
                        finalization_id=authority.expected_finalization_id,
                        exact_head=authority.expected_head,
                    )
                )
            invalidation = runtime.prepare_review_repair(
                authority.expected_finalization_id,
                _timestamp(self._clock()),
            )
            self._publish_delivery_state(change_id, runtime, f"review-repair-{invalidation.invalidation_id}")
            return invalidation

    @staticmethod
    def _review_repair_authority(runtime: DeliveryRuntime) -> _ReviewRepairAuthority:
        """Validate local review-repair authority and return its exact publication fence."""
        if runtime.change_disposition() is not None:
            message = "review repair requires current Change attention resolution"
            raise PortfolioApplicationError(message)
        invalidation = runtime.finalization_invalidation()
        finalization = runtime.finalization()
        if finalization is None and (invalidation is None or invalidation.reason != "review-repair"):
            message = "review repair requires current finalization authority"
            raise PortfolioApplicationError(message)
        if runtime.merged_pull_request_latch() is not None:
            message = "merged Change cannot be reopened for review repair"
            raise PortfolioApplicationError(message)
        ready = runtime.ready_receipt()
        publication = runtime.publication_history()
        expected_finalization_id = (
            invalidation.finalization_id if invalidation is not None else finalization.finalization_id
        )
        expected_head = invalidation.expected_head if invalidation is not None else finalization.exact_head
        if ready is not None and (ready.finalization_id != expected_finalization_id or ready.head_sha != expected_head):
            message = "review repair ready authority does not match finalization"
            raise PortfolioApplicationError(message)
        if finalization is None and ready is not None:
            message = "review repair cannot replay with ready authority"
            raise PortfolioApplicationError(message)
        identity = ready if ready is not None else None if publication is None else publication.current
        if identity is None:
            message = "review repair requires current publication identity"
            raise PortfolioApplicationError(message)
        return _ReviewRepairAuthority(
            invalidation=invalidation,
            expected_finalization_id=expected_finalization_id,
            expected_head=expected_head,
            repository=identity.repository,
            number=identity.number,
            node_id=identity.node_id,
        )

    def _require_no_review_repair(self, runtime: DeliveryRuntime, operation: str) -> None:
        """Reject Change head movement while external review repair owns the boundary."""
        invalidation = runtime.finalization_invalidation()
        if invalidation is not None and invalidation.reason == "review-repair":
            self._fail(f"{operation} requires review repair to be aborted or finalized first")

    @staticmethod
    def _observe_review_repair_pull_request(
        change_id: str,
        publisher: DraftPullRequestPublisher,
        authority: _ReviewRepairAuthority,
    ) -> PublicationPullRequestObservationReceipt:
        """Observe the bound open pull request at the exact review-repair head."""
        observation = publisher.observe_pull_request(ObserveChangePublicationPullRequest(change_id=change_id))
        if observation is None:
            message = "review repair requires a bound pull request"
            raise PortfolioApplicationError(message)
        snapshot = observation.snapshot
        if (
            snapshot.repository != publisher.repository
            or snapshot.repository != authority.repository
            or snapshot.number != authority.number
            or snapshot.node_id != authority.node_id
            or snapshot.base_branch != publisher.target_branch
            or snapshot.head_sha != authority.expected_head
            or snapshot.state != "open"
            or snapshot.merged
        ):
            message = "review repair requires an open pull request at the finalized head"
            raise PortfolioApplicationError(message)
        return observation

    @staticmethod
    def _replay_review_repair(
        change_id: str,
        publisher: DraftPullRequestPublisher,
        authority: _ReviewRepairAuthority,
        observation: PublicationPullRequestObservationReceipt,
    ) -> DeliveryFinalizationInvalidationReceipt | None:
        """Replay an existing review-repair fence without duplicating provider state changes."""
        invalidation = authority.invalidation
        if invalidation is None:
            return None
        if invalidation.reason != "review-repair" or invalidation.finalization_id != authority.expected_finalization_id:
            message = "review repair finalization invalidation is not replayable"
            raise PortfolioApplicationError(message)
        if not observation.snapshot.draft:
            publisher.return_to_draft(
                ReturnChangePullRequestToDraft(
                    change_id=change_id,
                    operation_id=f"review-repair-draft-{authority.expected_finalization_id}",
                    finalization_id=authority.expected_finalization_id,
                    exact_head=authority.expected_head,
                )
            )
        return invalidation

    def _reconcile_finalization_head_locked(
        self,
        change_id: str,
        runtime: DeliveryRuntime,
        *,
        observation: PublicationPullRequestObservationReceipt | None = None,
        acceptance_reason: DeliveryAcceptanceAttentionReason | None = None,
    ) -> DeliveryFinalizationReceipt | DeliveryFinalizationInvalidationReceipt | None:
        """Retain or invalidate finalization while the Change checkpoint lock is held."""
        if runtime.completion_receipt() is not None:
            finalization = runtime.finalization()
            if finalization is not None:
                self._promote_finalized_external_head(change_id, finalization.exact_head)
            return finalization
        finalization = runtime.finalization()
        ready = runtime.ready_receipt()
        if observation is None:
            observation = (
                None
                if self._draft_pull_request_publisher is None
                else self._draft_pull_request_publisher.observe_pull_request(
                    ObserveChangePublicationPullRequest(change_id=change_id)
                )
            )
        observed_head = (
            self._workspace_manager.observed_change_head(change_id)
            if observation is None
            else observation.snapshot.head_sha
        )
        if (
            finalization is not None
            and ready is not None
            and observation is not None
            and observed_head != finalization.exact_head
        ):
            publisher = self._draft_pull_request_publisher
            if publisher is None:
                self._fail("finalization reconciliation requires a publication provider")
            publisher.return_to_draft(
                ReturnChangePullRequestToDraft(
                    change_id=change_id,
                    operation_id=f"return-draft-{ready.finalization_id}",
                    finalization_id=ready.finalization_id,
                    exact_head=observation.snapshot.head_sha,
                )
            )
            if acceptance_reason is not None:
                runtime.capture_acceptance_attention(
                    observation,
                    ("provider pull request head differs from finalized Change head",),
                    reason=acceptance_reason,
                )
        result = runtime.reconcile_finalization_head(observed_head, _timestamp(self._clock()))
        if isinstance(result, DeliveryFinalizationReceipt):
            self._promote_finalized_external_head(change_id, result.exact_head)
        if not isinstance(result, DeliveryFinalizationInvalidationReceipt) and observation is not None:
            runtime.reconcile_pull_request_draft_state(
                provider_draft=observation.snapshot.draft,
                observed_at=observation.observed_at,
                observation_id=observation.observation_id,
            )
        return result

    def reconcile_finalization_head(
        self,
        change_id: str,
    ) -> DeliveryFinalizationReceipt | DeliveryFinalizationInvalidationReceipt | None:
        """Retain or invalidate finalization from the engine-derived Change branch head."""
        runtime = self._runtime(change_id, for_mutation=True)
        with (
            locked_roots((self._checkpoint_lock_root(change_id),)),
            self._operator_start(change_id, "finalization-head-reconciliation", *_FINALIZATION_HEAD_WRITES),
        ):
            before_frontier = runtime.frontier_bytes()
            before_coordination = self._workspace_manager.show(change_id)
            result = self._reconcile_finalization_head_locked(change_id, runtime)
            if (
                runtime.frontier_bytes() != before_frontier
                or self._workspace_manager.show(change_id) != before_coordination
            ):
                operation_suffix = (
                    result.invalidation_id
                    if isinstance(result, DeliveryFinalizationInvalidationReceipt)
                    else result.finalization_id
                    if isinstance(result, DeliveryFinalizationReceipt)
                    else "state"
                )
                self._publish_delivery_state(
                    change_id,
                    runtime,
                    f"finalization-reconciliation-{operation_suffix}",
                )
            return result

    def reconcile_change_checkpoint(self, change_id: str) -> DeliveryCheckpointReconciliationResult:
        """Reconcile one durable checkpoint without accepting caller-supplied external fences."""
        if self._change_branch_publisher is None or self._draft_pull_request_publisher is None:
            message = "checkpoint publication is not configured"
            raise PortfolioApplicationError(message)
        runtime = self._runtime(change_id, for_mutation=True)
        with self._engine_checkpoint_lock(change_id):
            current = runtime.checkpoint_publication_state()
            pending = current.pending_checkpoint
            if pending is not None and not _checkpoint_retry_ready(pending, _timestamp(self._clock())):
                return DeliveryCheckpointReconciliationResult(
                    change_id=change_id,
                    attempted_head=pending.head,
                    state=current,
                    reconciled=False,
                    error_code=pending.last_error_code,
                    error_detail=pending.last_error_detail or "Checkpoint retry is waiting for its next eligible time.",
                )
            with self._checkpoint_owner_authority(change_id, runtime):
                result = self._reconcile_change_checkpoint_with_failure_recording(change_id, runtime)
            self._try_convert_pause_request(change_id, runtime)
            return result

    def _reconcile_change_checkpoint_with_failure_recording(
        self,
        change_id: str,
        runtime: DeliveryRuntime,
    ) -> DeliveryCheckpointReconciliationResult:
        """Reconcile one checkpoint and retain bounded failure evidence for retries."""
        try:
            return self._reconcile_change_checkpoint_or_paused(change_id, runtime)
        except (
            PublicationProviderError,
            PublicationBaselineUnavailableError,
            DeliveryRuntimeConflictError,
            OSError,
            RuntimeError,
            subprocess.SubprocessError,
            ValueError,
        ) as exc:
            state = runtime.checkpoint_publication_state()
            pending = state.pending_checkpoint
            if pending is not None:
                with suppress(DeliveryRuntimeConflictError):
                    runtime.record_checkpoint_failure(
                        pending,
                        _timestamp(self._clock()),
                        _checkpoint_error_code(exc),
                        _checkpoint_error_detail(
                            str(exc),
                            "Checkpoint reconciliation failed; the pending checkpoint was retained.",
                        ),
                    )
            raise

    def reconcile_pending_checkpoints(
        self,
        *,
        limit: int = 8,
    ) -> tuple[DeliveryCheckpointReconciliationResult, ...]:
        """Drain a bounded set of pending checkpoints without failing sibling Changes."""
        if self._change_branch_publisher is None or self._draft_pull_request_publisher is None:
            return ()
        if limit < 1:
            message = "checkpoint reconciliation limit must be positive"
            raise ValueError(message)
        self._reconcile_runtimes()
        self._sweep_completed_change_worktrees()
        now = _timestamp(self._clock())
        pending_change_ids = tuple(
            change_id
            for change_id, runtime in sorted(self._runtimes.items())
            if (
                (pending := runtime.checkpoint_publication_state().pending_checkpoint) is not None
                and pending.head is not None
                and not _checkpoint_awaits_review(runtime)
                and _checkpoint_retry_ready(pending, now)
            )
        )[:limit]
        results = []
        for change_id in pending_change_ids:
            runtime = self._runtimes.get(change_id)
            if runtime is None:
                continue
            try:
                with locked_roots((self._checkpoint_lock_root(change_id),), blocking=False):
                    current = runtime.checkpoint_publication_state()
                    pending = current.pending_checkpoint
                    if pending is None or not _checkpoint_retry_ready(pending, now):
                        continue
                    # K5: failure recording and conversion stay inside the checkpoint lock.
                    results.append(self._reconcile_pending_checkpoint_locked(change_id, runtime, now))
                    self._try_convert_pause_request(change_id, runtime)
            except BlockingIOError:
                state = runtime.checkpoint_publication_state()
                results.append(
                    DeliveryCheckpointReconciliationResult(
                        change_id=change_id,
                        state=state,
                        reconciled=False,
                        error_code="ERR_DELIVERY_CHECKPOINT_BUSY",
                        error_detail="Checkpoint reconciliation is already in progress.",
                    )
                )
        return tuple(results)

    def _reconcile_pending_checkpoint_locked(
        self,
        change_id: str,
        runtime: DeliveryRuntime,
        now: datetime,
    ) -> DeliveryCheckpointReconciliationResult:
        try:
            with self._checkpoint_owner_authority(change_id, runtime):
                return self._reconcile_change_checkpoint_or_paused(change_id, runtime)
        except (
            PublicationProviderError,
            PublicationBaselineUnavailableError,
            DeliveryRuntimeConflictError,
            OSError,
            RuntimeError,
            subprocess.SubprocessError,
            ValueError,
        ) as exc:
            state = runtime.checkpoint_publication_state()
            pending = state.pending_checkpoint
            error_code = _checkpoint_error_code(exc)
            error_detail = _checkpoint_error_detail(
                str(exc),
                "Checkpoint reconciliation failed; the pending checkpoint was retained.",
            )
            if pending is not None:
                with suppress(DeliveryRuntimeConflictError):
                    state = runtime.record_checkpoint_failure(
                        pending,
                        now,
                        error_code,
                        error_detail,
                    )
            return DeliveryCheckpointReconciliationResult(
                change_id=change_id,
                attempted_head=pending.head if pending else None,
                state=state,
                reconciled=False,
                error_code=error_code,
                error_detail=error_detail,
            )

    def _reconcile_change_checkpoint_or_paused(
        self,
        change_id: str,
        runtime: DeliveryRuntime,
    ) -> DeliveryCheckpointReconciliationResult:
        """Run one reconciliation; a start refused by Pause is not a checkpoint failure (K3)."""
        refusal: ChangePauseRequestedError | None = None
        if (
            self._coordinator.pause_request(change_id) is not None
            and self._coordinator.current_drain_authority(change_id) is None
        ):
            # No marker, lease, snapshot or replay owner: a new publication start under a request.
            refusal = ChangePauseRequestedError()
        else:
            try:
                return self._reconcile_change_checkpoint(change_id, runtime)
            except ChangePauseRequestedError as exc:
                refusal = exc
        state = runtime.checkpoint_publication_state()
        return DeliveryCheckpointReconciliationResult(
            change_id=change_id,
            attempted_head=state.pending_checkpoint.head if state.pending_checkpoint else None,
            state=state,
            reconciled=False,
            error_code=refusal.code,
            error_detail=str(refusal),
        )

    @contextmanager
    def _checkpoint_owner_authority(self, change_id: str, runtime: DeliveryRuntime) -> Iterator[None]:
        """Hold this reconciliation's K2 token until it returns (snapshot, handoff or lease row).

        Snapshot custody rebuilds from its durable intent, un-anchored receipt or handoff (a)-(b) and binds
        that exact snapshot. A first-task snapshot not yet started binds only the intent this call commits
        under K3. Any other checkpoint takes the lease row: its token is inert until its own lease commits.
        """
        evidence = self._snapshot_owner_evidence(change_id, runtime)
        if evidence is None:
            state = runtime.checkpoint_publication_state()
            pending = state.pending_checkpoint
            if not (
                pending is not None
                and state.published_head is None
                and any(item.kind == DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK for item in pending.triggers)
            ):
                with self._owner_drain_authority(
                    change_id, "lease:checkpoint", publishes_checkpoint=True, requires_lease=True
                ):
                    yield
                return
            with self._owner_drain_authority(change_id, "snapshot:new", *_SNAPSHOT_DRAIN_MUTATIONS):
                yield
            return
        _kind, snapshot_head = evidence
        coordination = self._coordinator.show(change_id)
        intent = coordination.design_package_snapshot_intent
        receipt = coordination.design_package_snapshot
        if intent is not None:
            owner = intent.operation_id
            identity = _snapshot_identity(intent.operation_id, intent.package_id, intent.expected_head)
        else:
            owner = receipt.operation_id
            identity = _snapshot_identity(receipt.operation_id, receipt.package_id, receipt.previous_head)
        with self._owner_drain_authority(change_id, f"snapshot:{owner}", *_SNAPSHOT_DRAIN_MUTATIONS) as authority:
            authority.permit("snapshot", identity)
            if snapshot_head is not None:
                authority.permit("reserve", _checkpoint_operation_id("branch", change_id, snapshot_head))
            yield

    def _bind_snapshot_owner(
        self,
        change_id: str,
        before: ChangeDesignPackageSnapshotReceipt | None,
        snapshot: ChangeDesignPackageSnapshotReceipt,
    ) -> None:
        """K2 snapshot row: under a request, continue only the exact snapshot this token owns."""
        authority = self._coordinator.current_drain_authority(change_id)
        if authority is None or not authority.owner.startswith("snapshot:"):
            return
        identity = _snapshot_identity(snapshot.operation_id, snapshot.package_id, snapshot.previous_head)
        committed_here = before is None or before.receipt_id != snapshot.receipt_id
        if authority.owner == "snapshot:new" and committed_here and not authority.permits.get("snapshot"):
            authority.permit("snapshot", identity)
        if not authority.allows("snapshot", identity):
            if self._coordinator.pause_request(change_id) is not None:
                raise ChangePauseRequestedError
            return
        authority.permit("reserve", _checkpoint_operation_id("branch", change_id, snapshot.snapshot_head))

    def _reconcile_change_checkpoint(  # noqa: C901
        self,
        change_id: str,
        runtime: DeliveryRuntime,
    ) -> DeliveryCheckpointReconciliationResult:
        initial = runtime.checkpoint_publication_state()
        pending = initial.pending_checkpoint
        if pending is None:
            finalization = runtime.finalization()
            if finalization is not None and initial.published_head != finalization.exact_head:
                raise DeliveryRuntimeReconciliationError(
                    change_id,
                    "published checkpoint does not match the finalized Change head; "
                    "reconcile finalization before retrying publication",
                )
            return DeliveryCheckpointReconciliationResult(
                change_id=change_id,
                attempted_head=None,
                state=initial,
                reconciled=True,
            )
        if pending.head is None:
            return DeliveryCheckpointReconciliationResult(
                change_id=change_id,
                attempted_head=None,
                state=initial,
                reconciled=False,
                error_code=_CHECKPOINT_MISSING_HEAD_ERROR_CODE,
                error_detail=(
                    "Checkpoint publication is waiting for a reviewed Change head after authority invalidation."
                ),
            )

        target_sync = runtime.target_sync_receipt()
        if target_sync is not None and target_sync.review_required and runtime.finalization() is None:
            return DeliveryCheckpointReconciliationResult(
                change_id=change_id,
                attempted_head=None,
                state=initial,
                reconciled=False,
                error_code=_CHECKPOINT_REVIEW_ERROR_CODE,
                error_detail="Checkpoint publication awaits fresh finalization review after target synchronization.",
            )

        head = pending.head
        try:
            automation_paths = self._workspace_manager.repository_automation_paths(change_id, head)
        except PublicationBaselineUnavailableError:
            with suppress(DeliveryRuntimeConflictError):
                runtime.capture_publication_attention(
                    _timestamp(self._clock()),
                    ("publication-baseline-unavailable", f"exact-head:{head}"),
                )
            raise
        prepared = self._prepare_checkpoint_head(
            change_id,
            runtime,
            initial,
            pending,
        )
        if prepared.finalization_invalidated:
            return DeliveryCheckpointReconciliationResult(
                change_id=change_id,
                attempted_head=prepared.head,
                state=prepared.state,
                reconciled=False,
            )
        initial = prepared.state
        pending = prepared.pending
        head = prepared.head
        first_checkpoint = prepared.first_checkpoint
        package = self._package_store.read_verified(change_id)
        self._validate_package_authority(runtime, package)
        summary = _checkpoint_summary(runtime, package, pending, head, automation_paths)
        pull_request_title = _checkpoint_pull_request_title(runtime)
        branch_receipt = self._publish_checkpoint_branch(change_id, initial, head)
        if initial.published_head != head:
            state = runtime.record_checkpoint_branch_publication(initial, branch_receipt.published_head)
        else:
            state = runtime.checkpoint_publication_state()

        current = state.pending_checkpoint
        if current is None or current.head is None or not set(pending.triggers) <= set(current.triggers):
            return DeliveryCheckpointReconciliationResult(
                change_id=change_id,
                attempted_head=head,
                branch_publication=branch_receipt,
                state=state,
                reconciled=False,
            )

        draft_receipt = None
        # Provider entries continue only for an owner that started before any request (K2, K3).
        self._require_publication_drain(change_id, runtime)
        if first_checkpoint:
            draft_receipt = self._draft_pull_request_publisher.publish(
                CreateOrReconcileDraftPullRequest(
                    change_id=change_id,
                    operation_id=_checkpoint_operation_id("pull-request", change_id, head, summary),
                    published_head=head,
                    title=pull_request_title,
                    generated_summary=summary,
                )
            )
            runtime.record_publication_identity(
                DeliveryChangePublicationIdentity(
                    change_id=draft_receipt.change_id,
                    repository=draft_receipt.repository,
                    number=draft_receipt.number,
                    node_id=draft_receipt.node_id,
                    head_sha=draft_receipt.head_sha,
                )
            )
        summary_receipt = self._draft_pull_request_publisher.update_generated_summary(
            UpdateGeneratedPullRequestSummary(
                change_id=change_id,
                operation_id=_checkpoint_operation_id("summary", change_id, head, summary),
                published_head=head,
                generated_summary=summary,
            )
        )
        history = runtime.publication_history()
        if history is not None:
            runtime.record_publication_identity(
                history.current.model_copy(
                    update={
                        "repository": summary_receipt.repository,
                        "number": summary_receipt.number,
                        "head_sha": summary_receipt.head_sha,
                    }
                )
            )
        self._publish_delivery_state(
            change_id,
            runtime,
            _checkpoint_operation_id("state", change_id, head),
        )
        state = runtime.checkpoint_publication_state()
        if state.pending_checkpoint is not None and state.published_head == head:
            state = runtime.acknowledge_checkpoint_publication(pending, head)
        return DeliveryCheckpointReconciliationResult(
            change_id=change_id,
            attempted_head=head,
            branch_publication=branch_receipt,
            draft_pull_request=draft_receipt,
            generated_summary=summary_receipt,
            state=state,
            reconciled=state.pending_checkpoint is None,
        )

    def _publish_checkpoint_branch(
        self,
        change_id: str,
        checkpoint: DeliveryCheckpointPublicationState,
        head: str,
    ) -> ChangeBranchPublicationReceipt:
        """Publish one exact checkpoint head through the managed Change branch."""
        publisher = self._change_branch_publisher
        if publisher is None:
            self._fail("Change branch publication is not configured")
        pending = checkpoint.pending_checkpoint
        if pending is None or pending.head != head:
            self._fail("Change branch publication does not match the pending checkpoint")
        operation_id = _checkpoint_operation_id("branch", change_id, head)
        authority = self._coordinator.current_drain_authority(change_id)
        if authority is not None and authority.publishes_checkpoint:
            # K2 bound bookkeeping: only an owner whose row names it may reserve, and only the queued head.
            authority.permit("reserve", operation_id)
        return publisher.publish(
            PublishChangeBranch(
                change_id=change_id,
                expected_remote_head=checkpoint.published_head,
                expected_published_head=head,
                operation_id=operation_id,
            )
        )

    def _publish_target_sync_branch(
        self,
        change_id: str,
        runtime: DeliveryRuntime,
        merged_head: str,
    ) -> ChangeBranchPublicationReceipt | None:
        """Publish a target-sync head before its portable Delivery snapshot."""
        if self._change_branch_publisher is None:
            return None
        checkpoint = runtime.checkpoint_publication_state()
        branch_receipt = self._publish_checkpoint_branch(change_id, checkpoint, merged_head)
        runtime.record_checkpoint_branch_publication(checkpoint, branch_receipt.published_head)
        return branch_receipt

    @staticmethod
    def _acknowledge_published_target_sync_checkpoint(runtime: DeliveryRuntime, published_head: str) -> None:
        checkpoint = runtime.checkpoint_publication_state()
        pending = checkpoint.pending_checkpoint
        if pending is not None and pending.head == published_head and checkpoint.published_head == published_head:
            runtime.acknowledge_checkpoint_publication(pending, published_head)

    def _prepare_checkpoint_head(
        self,
        change_id: str,
        runtime: DeliveryRuntime,
        initial: DeliveryCheckpointPublicationState,
        pending: DeliveryPendingCheckpoint,
    ) -> _PreparedCheckpointHead:
        """Prepare the exact first checkpoint head and its pull-request boundary."""
        first_checkpoint = any(
            trigger.kind
            in {
                DeliveryCheckpointTriggerKind.ADMITTED_DESIGN,
                DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK,
            }
            for trigger in pending.triggers
        )
        first_task_checkpoint = any(
            trigger.kind == DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK for trigger in pending.triggers
        )
        if first_task_checkpoint and initial.published_head is None:
            package = self._package_store.read_verified(change_id)
            self._validate_package_authority(runtime, package)
            before = self._coordinator.show(change_id).design_package_snapshot
            snapshot = self._workspace_manager.snapshot_design_package(
                change_id,
                package.package_id,
                {
                    "authority.json": package.authority_bytes,
                    "design.md": package.design_bytes,
                    "intent.md": package.intent_bytes,
                    "manifest.json": package.manifest.canonical_bytes(),
                },
                _checkpoint_operation_id("package", change_id, pending.head, package.package_id),
            )
            self._bind_snapshot_owner(change_id, before, snapshot)
            if snapshot.snapshot_head != pending.head:
                runtime.record_design_package_snapshot(initial, snapshot)
                initial = runtime.checkpoint_publication_state()
                pending = initial.pending_checkpoint
                if pending is None or pending.head is None:
                    self._fail("Design package snapshot removed the pending checkpoint")
                if runtime.finalization() is not None:
                    runtime.reconcile_finalization_head(snapshot.snapshot_head, _timestamp(self._clock()))
                    return _PreparedCheckpointHead(
                        state=runtime.checkpoint_publication_state(),
                        pending=pending,
                        head=snapshot.snapshot_head,
                        first_checkpoint=first_checkpoint,
                        finalization_invalidated=True,
                    )
        if pending.head is None:
            self._fail("checkpoint preparation removed the pending head")
        return _PreparedCheckpointHead(
            state=initial,
            pending=pending,
            head=pending.head,
            first_checkpoint=first_checkpoint,
        )

    def _replay_pending_state_publications(
        self, selected_change_id: str | None = None
    ) -> tuple[DeliveryAcquisitionFailure, ...]:
        """Replay durable local state publications before exposing new claims."""
        failures = []
        for change_id, runtime in sorted(
            self._runtimes.items()
            if selected_change_id is None
            else ((selected_change_id, self._runtimes[selected_change_id]),)
        ):
            failure = self._replay_pending_state_publication(change_id, runtime)
            if failure is not None:
                failures.append(failure)
        return tuple(failures)

    def _replay_pending_state_publication(
        self, change_id: str, runtime: DeliveryRuntime
    ) -> DeliveryAcquisitionFailure | None:
        context = self._pending_state_publication_context(change_id, runtime)
        if context is None:
            return None
        if isinstance(context, DeliveryAcquisitionFailure):
            return context
        pending, current_digest, publisher = context
        if publisher is None:
            return self._handle_unpublished_pending_state(
                change_id,
                runtime,
                pending,
                current_digest,
            )
        if current_digest != pending.frontier_digest:
            reconciled = self._reconcile_pending_state_publication(
                change_id,
                runtime,
                pending,
                current_digest,
                publisher,
            )
            if isinstance(reconciled, DeliveryAcquisitionFailure):
                return reconciled
            pending, current_digest = reconciled
        try:
            remote_head = self._pending_publication_remote_head(
                change_id,
                pending,
                current_frontier_digest=current_digest,
            )
            bound = pending.transition_request_digest or pending.base_frontier_digest
            with self._owner_drain_authority(
                change_id, f"replay:{pending.frontier_digest}", bound=bound, publishes_checkpoint=True
            ):
                self._publish_delivery_state(
                    change_id,
                    runtime,
                    f"replay-state-{pending.frontier_digest}",
                    expected_remote_head=remote_head,
                )
        except (OSError, RuntimeError, subprocess.SubprocessError, TypeError, ValueError) as exc:
            return DeliveryAcquisitionFailure(
                change_id=change_id,
                outcome_id="OUT-000",
                code=getattr(exc, "code", PortfolioApplicationError.code),
                detail=str(exc),
                retry_condition="Retry Delivery-state publication replay.",
            )
        return None

    def _pending_state_publication_context(
        self, change_id: str, runtime: DeliveryRuntime
    ) -> tuple[DeliveryPendingStatePublication, str, DeliveryStatePublisher | None] | DeliveryAcquisitionFailure | None:
        try:
            pending = runtime.pending_state_publication()
        except (OSError, RuntimeError, ValueError) as exc:
            return DeliveryAcquisitionFailure(
                change_id=change_id,
                outcome_id="OUT-000",
                code=getattr(exc, "code", PortfolioApplicationError.code),
                detail=f"Delivery-state publication intent is invalid: {exc}",
                retry_condition="Repair the local Delivery-state publication intent.",
            )
        if pending is None:
            return None
        if change_id in self._runtime_reconciliation_errors:
            return DeliveryAcquisitionFailure(
                change_id=change_id,
                outcome_id="OUT-000",
                code=PortfolioApplicationError.code,
                detail=self._runtime_reconciliation_errors[change_id],
                retry_condition="Resolve the retained Delivery reconciliation attention.",
            )
        if pending.base_frontier_digest is None:
            return DeliveryAcquisitionFailure(
                change_id=change_id,
                outcome_id="OUT-000",
                code=PortfolioApplicationError.code,
                detail="Pending Delivery-state publication lacks its pre-mutation frontier boundary.",
                retry_condition="Repair the local Delivery-state publication intent.",
            )
        return (
            pending,
            hashlib.sha256(runtime.frontier_bytes()).hexdigest(),
            self._delivery_state_publisher,
        )

    def _handle_unpublished_pending_state(
        self,
        change_id: str,
        runtime: DeliveryRuntime,
        pending: DeliveryPendingStatePublication,
        current_digest: str,
    ) -> DeliveryAcquisitionFailure | None:
        if current_digest == pending.frontier_digest:
            runtime.acknowledge_pending_publication(current_digest)
            return None
        return DeliveryAcquisitionFailure(
            change_id=change_id,
            outcome_id="OUT-000",
            code=PortfolioApplicationError.code,
            detail="Delivery-state publication publisher is unavailable; pending publication is retained.",
            retry_condition="Restore the Delivery-state publisher before replaying publication.",
        )

    def _reconcile_pending_state_publication(
        self,
        change_id: str,
        runtime: DeliveryRuntime,
        pending: DeliveryPendingStatePublication,
        current_digest: str,
        publisher: DeliveryStatePublisher,
    ) -> tuple[DeliveryPendingStatePublication, str] | DeliveryAcquisitionFailure:
        try:
            inventory = publisher.read_snapshot_inventory()
            snapshot = next(
                (item for item in inventory.snapshots if item.change_id == change_id),
                None,
            )
            remote_digest = (
                None if snapshot is None else hashlib.sha256(_canonical_model_bytes(snapshot.frontier)).hexdigest()
            )
        except (OSError, RuntimeError, subprocess.SubprocessError, TypeError, ValueError) as exc:
            return DeliveryAcquisitionFailure(
                change_id=change_id,
                outcome_id="OUT-000",
                code=getattr(exc, "code", PortfolioApplicationError.code),
                detail=str(exc),
                retry_condition="Retry Delivery-state publication replay.",
            )
        if remote_digest == pending.frontier_digest:
            runtime.reanchor_pending_publication(pending.frontier_digest)
            pending = runtime.pending_state_publication()
            if pending is not None:
                current_digest = hashlib.sha256(runtime.frontier_bytes()).hexdigest()
        elif remote_digest == current_digest:
            runtime.reanchor_pending_publication(current_digest)
            pending = runtime.pending_state_publication()
            if pending is not None:
                current_digest = hashlib.sha256(runtime.frontier_bytes()).hexdigest()
        if pending is not None and current_digest == pending.frontier_digest:
            return pending, current_digest
        return DeliveryAcquisitionFailure(
            change_id=change_id,
            outcome_id="OUT-000",
            code=PortfolioApplicationError.code,
            detail="Pending Delivery-state publication does not match the current frontier.",
            retry_condition="Reconcile the local frontier and its pending publication intent.",
        )

    def _pending_publication_remote_head(
        self,
        change_id: str,
        pending: DeliveryPendingStatePublication,
        current_frontier_digest: str | None = None,
    ) -> str:
        """Return the remote state head only when its snapshot matches the pending base."""
        publisher = self._delivery_state_publisher
        if publisher is None:
            self._fail("pending Delivery-state publication has no configured publisher")
        inventory = publisher.read_snapshot_inventory()
        snapshot = next(
            (item for item in inventory.snapshots if item.change_id == change_id),
            None,
        )
        if inventory.remote_head is None or snapshot is None:
            self._fail("remote Delivery snapshot is unavailable for pending replay")
        remote_digest = hashlib.sha256(_canonical_model_bytes(snapshot.frontier)).hexdigest()
        if remote_digest not in {pending.base_frontier_digest, current_frontier_digest}:
            self._fail("remote Delivery snapshot no longer matches the pending publication base")
        return inventory.remote_head
