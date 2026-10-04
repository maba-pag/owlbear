"""Read models, readiness derivation and operator views."""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
from typing import TYPE_CHECKING

from owlbear_delivery.application_models import (
    DeliveryEngineActionResult,
    DeliveryIntegrationAttentionStatus,
    DeliveryOperatorContext,
    DeliveryRetainedChangeWorktree,
    DeliveryRetainedWorktreeCleanupBlockReason,
    DeliveryRuntimeReconciliationError,
    DeliveryUnavailableChangeView,
    PortfolioReadView,
    _operator_claim,
    _operator_recovery_attention,
    _worker_stall_prompt,
    _WorkerStall,
)
from owlbear_delivery.application_support import (
    _MAX_CONTINUATION_JOURNAL_BYTES,
    _MAX_HEALTH_DIAGNOSTICS,
    _PUBLICATION_OBSERVATION_CACHE_SECONDS,
    _PUBLICATION_READBACK_FAILURE_CODES,
    _canonical_model_bytes,
    _checkpoint_operation_id,
    _health_detail,
    _health_diagnostic_key,
    _operating_scope,
    _timestamp,
)
from owlbear_delivery.change_workspace import (
    ChangeContinuationAction,
    ChangeCoordination,
    ChangeWorktreeAttentionCode,
    RetainedChangeWorktree,
)
from owlbear_delivery.delivery_contract_discovery import (
    DeliveryChangeObservation,
    contract_fingerprint,
)
from owlbear_delivery.delivery_runtime import (
    AdministrativeDeliveryMove,
    AdministrativeDeliveryMovePreview,
    AdministrativeDeliveryMoveResult,
    DeliveryChangeStage,
    DeliveryFinalizationInvalidationReceipt,
    DeliveryFinalizationReceipt,
    DeliveryFrontier,
    DeliveryIntegrationAttention,
    DeliveryIntegrationAttentionDisposition,
    DeliveryRequest,
    DeliveryRequestResolution,
    DeliveryRuntime,
    DeliveryRuntimeConflictError,
    DeliveryStage,
    DeliveryWorkerRole,
    OutcomeAuthorityBinding,
    derive_change_stage,
    integration_attention_disposition,
    is_change_terminal,
    parse_delivery_frontier,
)
from owlbear_delivery.draft_pull_request import (
    ObserveChangePublicationPullRequest,
    PublicationPullRequestObservationReceipt,
)
from owlbear_delivery.finalization_reports import (
    FinalizationAttempt,
    FinalizationReportError,
    FinalizationReportSnapshot,
    FinalizationReportStore,
    FinalizerSettlementReceipt,
)
from owlbear_delivery.merge_offer import MergeDecision, MergeFacts, MergeOfferAuthority, decide_merge
from owlbear_delivery.portfolio_operating import (
    DeliveryHealthDiagnostic,
    DeliveryHealthReason,
    DeliveryHealthResolution,
    DeliveryHealthStatus,
    DeliveryHealthView,
    PortfolioChangeAdmission,
    PortfolioChangeLifecycleStatus,
    PortfolioGuidanceFacts,
    PortfolioOperatingView,
    PortfolioWorkReference,
    PortfolioWorkScope,
    derive_portfolio_guidance,
)
from owlbear_delivery.publication_provider import (
    ObservePublicationChecks,
    PublicationMergeProvider,
    PublicationProviderError,
)
from owlbear_delivery.recovery import (
    DeliveryRetryAttemptView,
    RetryEpisodeKey,
    RetryEpisodeSummary,
    RetryFailureClass,
    RetryLedger,
    RetryLedgerConflictError,
    RetryLedgerCorruptError,
    RetryStopCode,
)
from owlbear_delivery.runtime_transaction import (
    TransactionPathError,
    contained_directory,
    read_contained,
)
from owlbear_delivery.storage_io import locked_roots
from owlbear_delivery.work_items import (
    ChangeGroupView,
    ChangePauseUnavailableReason,
    DeliveryIssuerState,
    DeliveryPortfolioSnapshot,
    DeliveryProgress,
    DeliveryReadiness,
    DeliveryReadinessBasis,
    WorkItemAction,
    WorkItemActionKind,
    WorkItemActivityState,
    WorkItemCardView,
    WorkItemDetailView,
    WorkItemNeed,
    WorkItemNextActor,
    WorkItemProjector,
    WorkItemPublicationPhase,
    WorkItemScope,
    WorkItemTargetSyncConflictView,
    WorkItemWorktreeCleanupView,
    WorkItemWorktreeRecoveryView,
    derive_delivery_progress,
    resolve_publication_phase,
)

if TYPE_CHECKING:
    from owlbear_delivery.acceptance import (
        CompletionReceipt,
    )
    from owlbear_delivery.work_items import WorkItemDetail, WorkItemProjection


class _ReadinessViewsMixin:
    """Read models, readiness derivation and operator views."""

    def list_integration_attention(self) -> tuple[DeliveryIntegrationAttentionStatus, ...]:
        """List non-retryable Integration attention in stable identity order."""
        return self._integration_attention_statuses(self._portfolio_snapshots())

    def _integration_attention_statuses(
        self,
        snapshots: tuple[DeliveryPortfolioSnapshot, ...],
    ) -> tuple[DeliveryIntegrationAttentionStatus, ...]:
        """Project Integration attention from an already captured portfolio."""
        statuses = []
        for snapshot in snapshots:
            attention = snapshot.frontier.integration_attention
            if (
                attention is None
                or snapshot.frontier.integration_repair_claim is not None
                or self._integration_attention_is_superseded(snapshot.contract.change_id, attention)
            ):
                continue
            disposition = integration_attention_disposition(attention.code)
            if disposition == DeliveryIntegrationAttentionDisposition.RETRYABLE:
                continue
            statuses.append(
                DeliveryIntegrationAttentionStatus(
                    change_id=snapshot.contract.change_id,
                    code=attention.code,
                    disposition=disposition,
                    retry_condition=attention.retry_condition,
                )
            )
        return tuple(statuses)

    def _integration_attention_is_superseded(
        self,
        change_id: str,
        attention: DeliveryIntegrationAttention,
    ) -> bool:
        try:
            context = self._workspace_manager.integration_context(change_id)
        except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as exc:
            self._fail(f"current Integration target is unavailable for {change_id}", exc)
        return attention.target_head != context.target_head

    def show_integration_attention(self, change_id: str) -> DeliveryIntegrationAttention | None:
        """Return current typed Integration attention without mutating runtime state."""
        return self._runtime(change_id).integration_attention()

    def list_work_items(self) -> tuple[WorkItemProjection, ...]:
        """List bounded work-item projections in stable portfolio order."""
        projections = []
        for snapshot in self._portfolio_snapshots():
            if snapshot.contract.change_id in self._runtime_reconciliation_errors:
                continue
            if not self._is_work_portfolio_visible(snapshot):
                continue
            projections.extend(self._read_projector(snapshot).list_items())
        return tuple(
            sorted(
                projections,
                key=lambda item: (
                    item.stage.value == "completed",
                    item.change_id,
                    item.work_item_id,
                ),
            )
        )

    def list_work_item_groups(self) -> tuple[ChangeGroupView, ...]:
        """List grouped Cockpit views from exact per-change snapshots."""
        return tuple(
            self._read_projector(snapshot).group_view()
            for snapshot in self._portfolio_snapshots()
            if snapshot.contract.change_id not in self._runtime_reconciliation_errors
            if self._is_work_portfolio_visible(snapshot)
        )

    def list_changes(self) -> PortfolioReadView:
        """Return current grouped Change state and operating guidance."""
        return self.portfolio_read_view()

    def portfolio_read_view(self) -> PortfolioReadView:
        """Return grouped work and operating facts from one immutable capture."""
        snapshots = self._portfolio_snapshots()
        groups = tuple(
            self._read_projector(snapshot).group_view()
            for snapshot in snapshots
            if snapshot.contract.change_id not in self._runtime_reconciliation_errors
            if self._is_work_portfolio_visible(snapshot)
        )
        return PortfolioReadView(
            groups=groups,
            operating=self._portfolio_operating_view(snapshots, groups),
            health=self._delivery_health_view(inspect_workspaces=False),
            unavailable_changes=tuple(
                self._unavailable_change(change_id)
                for change_id, observation in sorted(self._discovered_changes.items())
                if not observation.actionable_runtime or change_id in self._runtime_reconciliation_errors
            ),
        )

    def portfolio_operating_view(self) -> PortfolioOperatingView:
        """Return portfolio-wide operating facts and advisory session guidance."""
        snapshots = self._portfolio_snapshots()
        groups = tuple(
            WorkItemProjector(snapshot).group_view()
            for snapshot in snapshots
            if snapshot.contract.change_id not in self._runtime_reconciliation_errors
            if self._is_work_portfolio_visible(snapshot)
        )
        return self._portfolio_operating_view(snapshots, groups)

    def delivery_health(self, change_id: str | None = None) -> DeliveryHealthView:
        """Return bounded diagnostics for state excluded from Delivery authority."""
        self._reconcile_runtimes()
        return self._delivery_health_view(scoped_change_id=change_id)

    def _delivery_health_view(
        self, *, scoped_change_id: str | None = None, inspect_workspaces: bool = True
    ) -> DeliveryHealthView:
        diagnostics: list[DeliveryHealthDiagnostic] = [
            *self._startup_health_diagnostics,
        ]
        diagnosed_change_ids = {diagnostic.change_id for diagnostic in diagnostics if diagnostic.change_id is not None}
        for change_id, runtime in sorted(self._runtimes.items()):
            if inspect_workspaces and change_id not in diagnosed_change_ids:
                out_of_band = self._out_of_band_head_diagnostic(change_id)
                if out_of_band is not None:
                    diagnostics.append(out_of_band)
                    diagnosed_change_ids.add(change_id)
            marker_path = f".owlbear/delivery/runtime/changes/{change_id}/state-publication.json"
            try:
                pending = runtime.pending_state_publication()
            except (OSError, RuntimeError, ValueError) as exc:
                diagnostics.append(
                    DeliveryHealthDiagnostic(
                        source="local-runtime",
                        code="state-publication-invalid",
                        detail=_health_detail(
                            f"Delivery-state publication intent is invalid: {exc}",
                            "Delivery-state publication intent is invalid.",
                        ),
                        change_id=change_id,
                        path=marker_path,
                        reason=DeliveryHealthReason.STATE_PUBLICATION_INVALID,
                        resolution=DeliveryHealthResolution.AUTHORITY_GAP,
                    )
                )
            else:
                if pending is not None and self._delivery_state_publisher is not None:
                    diagnostics.append(
                        DeliveryHealthDiagnostic(
                            source="local-runtime",
                            code="state-publication-pending",
                            detail="Delivery-state publication is pending replay.",
                            change_id=change_id,
                            path=marker_path,
                            retry_safe=True,
                            reason=DeliveryHealthReason.STATE_PUBLICATION_PENDING,
                            resolution=DeliveryHealthResolution.RETRY,
                        )
                    )
        diagnostics.extend(
            DeliveryHealthDiagnostic(
                source="local-runtime",
                code=observation.diagnostic_code or "runtime-unavailable",
                detail=_health_detail(
                    observation.diagnostic_detail,
                    "Persisted Delivery state is unavailable.",
                ),
                change_id=observation.change_id,
                path=f".owlbear/delivery/runtime/changes/{observation.change_id}",
                reason=DeliveryHealthReason.RUNTIME_UNAVAILABLE,
                resolution=DeliveryHealthResolution.AUTHORITY_GAP,
            )
            for observation in self._discovered_changes.values()
            if observation.error is not None
            and not any(diagnostic.change_id == observation.change_id for diagnostic in diagnostics)
        )
        diagnostic_change_ids = {diagnostic.change_id for diagnostic in diagnostics if diagnostic.change_id is not None}
        diagnostics.extend(
            DeliveryHealthDiagnostic(
                source="runtime-reconciliation",
                code="runtime-reconciliation-required",
                detail=_health_detail(detail, "Delivery runtime reconciliation is required."),
                change_id=change_id,
                reason=DeliveryHealthReason.RUNTIME_RECONCILIATION_REQUIRED,
                resolution=DeliveryHealthResolution.AUTHORITY_GAP,
            )
            for change_id, detail in self._runtime_reconciliation_errors.items()
            if change_id not in diagnostic_change_ids
        )
        unique = {_health_diagnostic_key(diagnostic): diagnostic for diagnostic in diagnostics}
        ordered = tuple(
            sorted(
                unique.values(),
                key=lambda item: (
                    item.change_id or "",
                    item.source,
                    item.code,
                    item.path or "",
                ),
            )
        )
        if scoped_change_id is not None:
            ordered = tuple(item for item in ordered if item.change_id is None or item.change_id == scoped_change_id)
        bounded = ordered[:_MAX_HEALTH_DIAGNOSTICS]
        return DeliveryHealthView(
            status=DeliveryHealthStatus.ATTENTION if bounded else DeliveryHealthStatus.HEALTHY,
            diagnostics=bounded,
        )

    def _out_of_band_head_diagnostic(self, change_id: str) -> DeliveryHealthDiagnostic | None:
        """Report a clean local Change head that has no Delivery adoption evidence."""
        try:
            coordination = self._workspace_manager.show(change_id)
            if coordination.writer is not None or coordination.external_head_adoption_receipt is not None:
                return None
            observed_head = self._workspace_manager.observed_change_head(change_id)
        except OSError, RuntimeError, subprocess.SubprocessError, ValueError:
            return None
        if observed_head == coordination.last_reviewed_commit:
            return None
        return DeliveryHealthDiagnostic(
            source="local-runtime",
            code="local-change-head-out-of-band",
            detail="Local Change branch is outside its reviewed Delivery boundary without adoption evidence.",
            change_id=change_id,
            reason=DeliveryHealthReason.LOCAL_CHANGE_HEAD_OUT_OF_BAND,
            resolution=DeliveryHealthResolution.AUTHORITY_GAP,
            expected_head=coordination.last_reviewed_commit,
            observed_local_head=observed_head,
        )

    def _portfolio_operating_view(
        self,
        snapshots: tuple[DeliveryPortfolioSnapshot, ...],
        groups: tuple[ChangeGroupView, ...],
    ) -> PortfolioOperatingView:
        verified_package_ids = {package.change_id for package in self._package_store.list_verified()}
        health_change_ids = tuple(
            diagnostic.change_id for diagnostic in self._startup_health_diagnostics if diagnostic.change_id is not None
        )
        status_ids = sorted((*verified_package_ids, *self._discovered_changes, *health_change_ids))
        change_statuses = tuple(
            status
            for status in (
                self._change_lifecycle_status(change_id, self._discovered_changes.get(change_id))
                for change_id in dict.fromkeys(status_ids)
            )
            if status.stage not in {DeliveryChangeStage.COMPLETED, DeliveryChangeStage.ABANDONED}
            or not status.actionable_runtime
        )
        draft_design_ids = tuple(status.change_id for status in change_statuses if not status.admitted)
        design_required_ids = tuple(
            status.change_id
            for status in change_statuses
            if status.admitted and status.stage == DeliveryChangeStage.DESIGN
        )
        operational_snapshots = tuple(
            snapshot for snapshot in snapshots if snapshot.contract.change_id not in self._runtime_reconciliation_errors
        )
        claimed = self._claimed_work(operational_snapshots)
        queued = self._queued_work(operational_snapshots)
        operational_groups = tuple(
            group for group in groups if group.change_id not in self._runtime_reconciliation_errors
        )
        interventions = tuple(
            PortfolioWorkReference(
                change_id=item.change_id,
                item_key=item.item_key,
                scope=_operating_scope(item.scope),
            )
            for group in operational_groups
            for item in group.items
            if item.needs == WorkItemNeed.YOU
        )
        dependency_waits = tuple(
            PortfolioWorkReference(
                change_id=item.change_id,
                item_key=item.item_key,
                scope=_operating_scope(item.scope),
            )
            for group in operational_groups
            for item in group.items
            if item.needs == WorkItemNeed.DEPENDENCY
        )
        snapshot_ids = {snapshot.contract.change_id for snapshot in operational_snapshots}
        unavailable_frontiers = tuple(
            observation.frontier
            for change_id, observation in sorted(self._discovered_changes.items())
            if (observation.admitted and change_id not in snapshot_ids and observation.frontier is not None)
        )
        unfinished_runtime_count = sum(
            not is_change_terminal(snapshot.frontier) for snapshot in operational_snapshots
        ) + sum(not is_change_terminal(frontier) for frontier in unavailable_frontiers)
        unfinished_runtime_count += len(
            {
                diagnostic.change_id
                for diagnostic in self._delivery_health_view().diagnostics
                if diagnostic.change_id is not None
            }
            - snapshot_ids
            - set(self._discovered_changes)
        )
        unfinished_runtime_count += len(
            {
                change_id
                for change_id in self._runtime_reconciliation_errors
                if change_id not in snapshot_ids
                and change_id in self._discovered_changes
                and self._discovered_changes[change_id].frontier is None
            }
        )
        unfinished_change_count = unfinished_runtime_count
        completed_change_count = sum(
            snapshot.frontier.change_completion is not None for snapshot in operational_snapshots
        ) + sum(frontier.change_completion is not None for frontier in unavailable_frontiers)
        design_change_ids = tuple(dict.fromkeys((*draft_design_ids, *design_required_ids)))
        guidance = derive_portfolio_guidance(
            PortfolioGuidanceFacts(
                unfinished_change_count=unfinished_change_count,
                design_change_ids=design_change_ids,
                claimed=claimed,
                queued=queued,
                interventions=interventions,
                dependency_waits=dependency_waits,
            )
        )
        return PortfolioOperatingView(
            unfinished_change_count=unfinished_change_count,
            completed_change_count=completed_change_count,
            statuses=change_statuses,
            draft_design_change_ids=draft_design_ids,
            design_required_change_ids=design_required_ids,
            claimed=claimed,
            queued_for_orchestration=queued,
            interventions=interventions,
            dependency_waits=dependency_waits,
            guidance=guidance,
        )

    def _change_lifecycle_status(
        self,
        change_id: str,
        observation: DeliveryChangeObservation | None,
    ) -> PortfolioChangeLifecycleStatus:
        reconciliation_error = self._runtime_reconciliation_errors.get(change_id)
        health_diagnostic = next(
            (diagnostic for diagnostic in self._startup_health_diagnostics if diagnostic.change_id == change_id),
            None,
        )
        if observation is None or not observation.admitted:
            if health_diagnostic is not None:
                return PortfolioChangeLifecycleStatus(
                    change_id=change_id,
                    admission=PortfolioChangeAdmission.ADMITTED,
                    stage=None,
                    actionable_runtime=False,
                    diagnostic_code=health_diagnostic.code,
                    diagnostic_detail=_health_detail(
                        health_diagnostic.detail,
                        "Delivery state requires reconciliation.",
                    ),
                )
            return PortfolioChangeLifecycleStatus(
                change_id=change_id,
                admission=PortfolioChangeAdmission.UNADMITTED,
                stage=DeliveryChangeStage.DESIGN,
                actionable_runtime=False,
            )
        diagnostic_code = observation.diagnostic_code
        diagnostic_detail = observation.diagnostic_detail
        if diagnostic_code is None and reconciliation_error is not None:
            diagnostic_code = "runtime-reconciliation-required"
        if diagnostic_detail is None and reconciliation_error is not None:
            diagnostic_detail = reconciliation_error
        return PortfolioChangeLifecycleStatus(
            change_id=change_id,
            admission=PortfolioChangeAdmission.ADMITTED,
            stage=observation.stage,
            actionable_runtime=observation.actionable_runtime and reconciliation_error is None,
            diagnostic_code=diagnostic_code,
            diagnostic_detail=_health_detail(diagnostic_detail, "Delivery state requires reconciliation")
            if diagnostic_detail is not None
            else None,
        )

    def _claimed_work(
        self,
        snapshots: tuple[DeliveryPortfolioSnapshot, ...],
    ) -> tuple[PortfolioWorkReference, ...]:
        claimed = []
        for snapshot in snapshots:
            if snapshot.contract.change_id in self._runtime_reconciliation_errors:
                continue
            claimed.extend(
                PortfolioWorkReference(
                    change_id=snapshot.contract.change_id,
                    item_key=f"outcome:{binding.outcome_id}",
                    scope=PortfolioWorkScope.OUTCOME,
                )
                for binding in snapshot.frontier.bindings
                if binding.active_claim is not None
            )
        return tuple(claimed)

    def _queued_work(
        self,
        snapshots: tuple[DeliveryPortfolioSnapshot, ...],
    ) -> tuple[PortfolioWorkReference, ...]:
        return self._queued_outcome_work(snapshots)

    def _queued_outcome_work(
        self,
        snapshots: tuple[DeliveryPortfolioSnapshot, ...],
    ) -> tuple[PortfolioWorkReference, ...]:
        ranked = tuple(
            candidate for snapshot in snapshots if (candidate := self._queued_outcome_candidate(snapshot)) is not None
        )
        return tuple(item[4] for item in sorted(ranked, key=lambda item: item[:4]))

    def _queued_outcome_candidate(
        self,
        snapshot: DeliveryPortfolioSnapshot,
    ) -> tuple[int, int, int, str, PortfolioWorkReference] | None:
        if (
            snapshot.contract.change_id in self._runtime_reconciliation_errors
            or self._snapshot_change_stage(snapshot) != DeliveryChangeStage.BUILDING
            or snapshot.frontier.change_disposition is not None
            or self._snapshot_has_active_claims(snapshot)
        ):
            return None
        completed = {
            binding.outcome_id for binding in snapshot.frontier.bindings if binding.stage == DeliveryStage.COMPLETED
        }
        bindings = {binding.outcome_id: binding for binding in snapshot.frontier.bindings}
        ranked = []
        for outcome_index, outcome in enumerate(snapshot.contract.outcomes):
            binding = bindings[outcome.outcome_id]
            if (
                binding.stage in {DeliveryStage.DESIGN, DeliveryStage.COMPLETED}
                or binding.active_claim is not None
                or (binding.block is not None and not binding.block.resolved)
                or not set(outcome.dependency_ids) <= completed
            ):
                continue
            task_index = self._snapshot_task_index(binding)
            if task_index is None:
                continue
            ranked.append(
                (
                    self._snapshot_dependency_depth(snapshot, outcome.outcome_id),
                    outcome_index,
                    task_index,
                    snapshot.contract.change_id,
                    PortfolioWorkReference(
                        change_id=snapshot.contract.change_id,
                        item_key=f"outcome:{outcome.outcome_id}",
                        scope=PortfolioWorkScope.OUTCOME,
                    ),
                )
            )
        return min(ranked, key=lambda item: item[:4]) if ranked else None

    @staticmethod
    def _snapshot_task_index(binding: OutcomeAuthorityBinding) -> int | None:
        if binding.stage != DeliveryStage.IMPLEMENTATION:
            return 0
        completed = {result.task_id for result in binding.results}
        task = next(
            (item for item in binding.tasks if item.task_id not in completed and set(item.dependency_ids) <= completed),
            None,
        )
        return binding.task_ids.index(task.task_id) if task is not None else None

    def show_work_item(self, change_id: str, work_item_id: str) -> WorkItemDetail:
        """Show bounded semantic detail from one exact change projector."""
        try:
            return self._work_item_projector(self._runtime(change_id)).show(work_item_id)
        except KeyError as exc:
            if work_item_id == "publication":
                self._fail(
                    "work item identity is invalid for MCP publication lookup: "
                    f"use Change ID '{change_id}' as work_item_id",
                    exc,
                )
            self._fail(f"work item is absent: {work_item_id}", exc)

    def show_work_item_view(self, change_id: str, item_key: str) -> WorkItemDetailView | DeliveryUnavailableChangeView:
        """Show semantic and operator detail from one exact snapshot."""
        self._reconcile_runtimes()
        observation = self._discovered_changes.get(change_id)
        if observation is not None and not observation.actionable_runtime:
            return self._unavailable_change(change_id)
        runtime = self._runtime(change_id)
        return self._captured_detail(runtime, self._work_item_projector(runtime), item_key)

    def _captured_detail(
        self,
        runtime: DeliveryRuntime,
        projector: WorkItemProjector,
        item_key: str,
    ) -> WorkItemDetailView:
        change_id = runtime.contract.change_id
        try:
            view = projector.show_view(item_key)
        except (KeyError, StopIteration) as exc:
            self._fail(f"work item is absent: {item_key}", exc)
        if view.publication is None:
            return view
        try:
            coordination = self._workspace_manager.show(change_id)
        except OSError, RuntimeError, ValueError:
            unavailable = self._unavailable_change(change_id, "coordination-unavailable")
            return view.model_copy(update={"readiness": unavailable.readiness})
        conflict = coordination.target_sync_conflict
        conflict_view = (
            WorkItemTargetSyncConflictView(
                conflict_id=conflict.conflict_id,
                operation_id=conflict.operation_id,
                target_head=conflict.target_head,
                change_head_before=conflict.change_head_before,
                conflict_paths=conflict.conflict_paths,
            )
            if conflict is not None
            else None
        )
        publication = view.publication.model_copy(update={"target_sync_conflict": conflict_view})
        if view.readiness is not None:
            ready = view.readiness.executable and view.readiness.operation is WorkItemActionKind.FINALIZE
            publication = publication.model_copy(
                update={
                    "ready_for_finalization": ready,
                    "readiness_diagnostics": () if ready else (view.readiness.reason_code,),
                }
            )
        if coordination.worktree_cleanup is None and (
            publication.phase
            in {
                WorkItemPublicationPhase.ABANDONED,
                WorkItemPublicationPhase.ACCEPTANCE_OBSERVED,
            }
            or not coordination.worktree_path.exists()
        ):
            retained = self._workspace_manager.inspect_retained(change_id, coordination)
            publication = publication.model_copy(
                update={
                    "worktree_cleanup": self._worktree_cleanup_view(runtime, retained),
                    "worktree_recovery": self._worktree_recovery_view(retained),
                }
            )
        return view.model_copy(update={"publication": publication})

    def show_operator_context(self, change_id: str, outcome_id: str) -> DeliveryOperatorContext:
        """Show current bounded operator state from one exact runtime binding."""
        runtime = self._runtime(change_id)
        binding = runtime.show_binding(outcome_id)
        return DeliveryOperatorContext(
            change_id=change_id,
            outcome_id=outcome_id,
            stage=binding.stage,
            block=binding.block,
            requests=binding.requests,
            active_claim=_operator_claim(binding.active_claim),
            return_context=binding.return_context,
            recovery_attention=_operator_recovery_attention(binding.recovery_attention),
            retry_diagnostic=binding.retry_diagnostic,
        )

    def resolve_request(
        self,
        change_id: str,
        request_id: str,
        resolution: DeliveryRequestResolution,
    ) -> DeliveryRequest:
        """Persist one request resolution by delegating to the owning runtime."""
        with self._coordinator.acquisition_lock():
            runtime = self._runtime(change_id, for_mutation=True)
            with locked_roots((self._checkpoint_lock_root(change_id),)):
                self._import_legacy_worker_budgets(runtime)
                resolved = runtime.resolve_request(request_id, resolution)
                self._record_retry_release(runtime, outcome_id=resolved.outcome_id)
                self._publish_delivery_state(
                    change_id,
                    runtime,
                    _checkpoint_operation_id("request-resolution", change_id, request_id),
                )
                return resolved

    def clear_block(
        self,
        change_id: str,
        outcome_id: str,
        block_id: str,
        operator_note: str,
        locators: tuple[str, ...],
    ) -> OutcomeAuthorityBinding:
        """Clear a requestless same-stage block with operator evidence via runtime."""
        with self._coordinator.acquisition_lock():
            runtime = self._runtime(change_id, for_mutation=True)
            with locked_roots((self._checkpoint_lock_root(change_id),)):
                self._import_legacy_worker_budgets(runtime)
                binding = runtime.unblock(outcome_id, block_id, operator_note, locators)
                self._record_retry_release(runtime, outcome_id=outcome_id)
                self._publish_delivery_state(
                    change_id,
                    runtime,
                    _checkpoint_operation_id("block-resolution", change_id, outcome_id, block_id),
                )
                return binding

    def administrative_move(
        self,
        change_id: str,
        request: AdministrativeDeliveryMove,
    ) -> AdministrativeDeliveryMoveResult:
        """Delegate an authorized operator backward movement to the owning runtime."""
        with self._coordinator.acquisition_lock():
            runtime = self._runtime(change_id, for_mutation=True)
            with locked_roots((self._checkpoint_lock_root(change_id),)):
                self._import_legacy_worker_budgets(runtime)
                result = runtime.administrative_move(request)
                self._publish_delivery_state(
                    change_id,
                    runtime,
                    _checkpoint_operation_id("administrative-move", change_id, request.move_id),
                )
                return result

    def preview_administrative_move(
        self,
        change_id: str,
        outcome_id: str,
        target: DeliveryStage,
    ) -> AdministrativeDeliveryMovePreview:
        """Preview one exact backward movement without mutating authority."""
        return self._runtime(change_id).preview_administrative_move(outcome_id, target)

    def _work_item_projector(self, runtime: DeliveryRuntime) -> WorkItemProjector:
        return self._read_projector(self._delivery_snapshot(runtime))

    def _settled_attention_workspace_guidance(self, change_id: str, reason: str | None) -> str | None:
        if reason not in {"workspace-dirty", "workspace-preflight-failed"}:
            return None
        try:
            coordination = self._workspace_manager.show(change_id)
        except OSError, RuntimeError, ValueError:
            return None
        attention = coordination.finalization_attention
        writer = coordination.writer
        if (
            attention is None
            or writer is None
            or writer.kind != "finalization-attention"
            or writer.attempt_id != attention.attempt_id
        ):
            return None
        return (
            "Settled Finalizer attention retains dirty or stale workspace evidence. Preserve its failure "
            "report, settlement receipt, and retry history; workspace cleanup or a changed fingerprint "
            "does not authorize retry. Defer or abandon this Change until a supported repair is available. "
            f"Inspect read-only with /inspect-change {change_id}."
        )

    def _read_projector(self, snapshot: DeliveryPortfolioSnapshot) -> WorkItemProjector:
        cards = WorkItemProjector(snapshot).group_view().items
        basis = DeliveryReadinessBasis(
            contract_digest=contract_fingerprint(snapshot.contract),
            frontier_digest=snapshot.version,
            candidate_head=snapshot.frontier.finalization.exact_head if snapshot.frontier.finalization else None,
        )
        merge = self._merge_decision(snapshot)
        basis, workspace_reason, readiness_guidance = self._capture_action_basis(snapshot, cards, basis, merge)
        if readiness_guidance is None:
            readiness_guidance = self._settled_attention_workspace_guidance(
                snapshot.contract.change_id, workspace_reason
            )
        try:
            reports = FinalizationReportStore(self._target_root, snapshot.contract.change_id).read()
        except FinalizationReportError:
            reports = None
        basis = basis.model_copy(update={"diagnostic_sequence": reports.sequence if reports is not None else None})
        decisions = tuple(
            self._with_finalization_report(self._card_readiness(snapshot, card, basis, workspace_reason), reports)
            for card in cards
        )
        decisions = tuple(
            self._with_merge_readiness(snapshot, card, decision, merge, workspace_reason)
            for card, decision in zip(cards, decisions, strict=True)
        )
        decisions = tuple(
            self._with_retry_readiness(snapshot, card, decision)
            for card, decision in zip(cards, decisions, strict=True)
        )
        decisions = self._with_worker_stall_readiness(snapshot, cards, decisions)
        pause_requested, pause_drained = self._pause_request_state(snapshot)
        if pause_requested:
            decisions = self._with_pause_request_readiness(snapshot, cards, decisions)
        decisions, card_guidance = self._with_progress(
            snapshot, cards, decisions, readiness_guidance, pause_drained=pause_drained
        )
        return WorkItemProjector(
            snapshot,
            decisions,
            readiness_guidance=card_guidance,
            change_progress=("paused" if pause_drained else self._change_activity_progress(snapshot, cards, decisions)),
            pause_unavailable_reason=self._pause_unavailable_reason(snapshot),
            pause_requested=pause_requested,
        )

    def _pause_request_state(self, snapshot: DeliveryPortfolioSnapshot) -> tuple[bool, bool]:
        """Return (request recorded, custody drained) read-only; unreadable custody is never drained (§1.5)."""
        change_id = snapshot.contract.change_id
        try:
            coordination = self._workspace_manager.show(change_id)
        except OSError, RuntimeError, ValueError:
            return False, False
        if coordination.pause_request is None:
            return False, False
        runtime = self._runtimes.get(change_id)
        try:
            drained = runtime is not None and self._custody_drained(change_id, runtime, coordination)
        except OSError, RuntimeError, ValueError:
            drained = False
        return True, drained

    def _with_pause_request_readiness(
        self,
        snapshot: DeliveryPortfolioSnapshot,
        cards: tuple[WorkItemCardView, ...],
        decisions: tuple[DeliveryReadiness, ...],
    ) -> tuple[DeliveryReadiness, ...]:
        """§1.5/I7: a request refuses every new start, so no new-work action stays executable.

        Retained-owner, containment and recovery readiness is not executable and keeps its guidance.
        """
        return tuple(
            decision.model_copy(
                update={
                    "status": "blocked",
                    "reason_code": "change-paused",
                    "executable": False,
                    "action": None,
                    "prompt": self._readiness_prompt(snapshot, card, "change-paused", executable=False),
                }
            )
            if decision.executable
            else decision
            for card, decision in zip(cards, decisions, strict=True)
        )

    def _pause_unavailable_reason(self, snapshot: DeliveryPortfolioSnapshot) -> ChangePauseUnavailableReason | None:
        """A2: Pause admits under any custody (§1.11 K1); only inactive, unreadable or already-requested refuse."""
        change_id = snapshot.contract.change_id
        runtime = self._runtimes.get(change_id)
        frontier = snapshot.frontier
        if (
            frontier.change_deferral is not None
            or frontier.change_abandonment is not None
            or (frontier.change_completion is not None)
        ):
            return "change-inactive"
        if runtime is None or change_id in self._runtime_reconciliation_errors:
            return "state-unavailable"
        try:
            coordination = self._workspace_manager.show(change_id)
        except OSError, RuntimeError, ValueError:
            return "state-unavailable"
        if coordination.pause_request is not None:
            return "pause-requested"
        return None

    def _with_progress(
        self,
        snapshot: DeliveryPortfolioSnapshot,
        cards: tuple[WorkItemCardView, ...],
        decisions: tuple[DeliveryReadiness, ...],
        guidance: str | None,
        *,
        pause_drained: bool = False,
    ) -> tuple[tuple[DeliveryReadiness, ...], tuple[str | None, ...]]:
        """Project progress from final readiness plus read-only issuer and occupancy evidence."""
        at_capacity: bool | None = None
        updated: list[DeliveryReadiness] = []
        card_guidance: list[str | None] = []
        for card, decision in zip(cards, decisions, strict=True):
            issuer_state: DeliveryIssuerState | None = None
            custody: str | None = None
            if decision.status == "running" and decision.reason_code == "active-custody":
                issuer_state, custody = self._custody_evidence(snapshot, card)
            capacity = False
            if (
                decision.reason_code == "ready"
                and decision.executable
                and decision.next_actor is WorkItemNextActor.AGENT
            ):
                if at_capacity is None:
                    at_capacity = self._other_changes_fill_capacity(snapshot.contract.change_id)
                capacity = at_capacity
            progress = derive_delivery_progress(
                decision,
                card,
                snapshot.frontier,
                issuer_state=issuer_state,
                at_capacity=capacity,
                pause_drained=pause_drained,
            )
            updated.append(decision.model_copy(update={"progress": progress}))
            card_guidance.append(custody if custody is not None else guidance)
        return tuple(updated), tuple(card_guidance)

    def _custody_evidence(
        self, snapshot: DeliveryPortfolioSnapshot, card: WorkItemCardView
    ) -> tuple[DeliveryIssuerState | None, str | None]:
        """Return issuer evidence and neutral custody copy for a held Planner, Builder or Finalizer step."""
        change_id = snapshot.contract.change_id
        claims = tuple(
            (binding.outcome_id, binding.active_claim)
            for binding in snapshot.frontier.bindings
            if binding.active_claim is not None
            and (card.scope is WorkItemScope.CHANGE_PUBLICATION or binding.outcome_id == card.work_item_id)
        )
        if claims:
            states = {
                self._claim_issuer_state(
                    change_id, outcome_id, claim.attempt_id, claim.claim_id, claim.worker_role.value
                )
                for outcome_id, claim in claims
            }
            roles = ", ".join(dict.fromkeys(claim.worker_role.value.capitalize() for _outcome, claim in claims))
            state: DeliveryIssuerState = "unknown" if "unknown" in states else "alive" if "alive" in states else "gone"
            return state, f"Claimed by {roles}"
        if card.scope is not WorkItemScope.CHANGE_PUBLICATION or snapshot.frontier.integration_repair_claim is not None:
            return None, None
        try:
            attempt = self._active_finalizer_writer_attempt(change_id)
        except OSError, RuntimeError, ValueError:
            return None, None
        if attempt is None:
            return None, None
        writer = attempt.writer
        state = self._claim_issuer_state(change_id, None, writer.attempt_id, writer.claim_id, "finalizer")
        return state, "Finalizer attempt held"

    def _claim_issuer_state(
        self, change_id: str, outcome_id: str | None, attempt_id: str, claim_id: str, role: str
    ) -> DeliveryIssuerState:
        """Read the recorded issuing window; any missing, mismatched or unreadable evidence is unknown."""
        try:
            issuer = self._read_claim_issuer(change_id, attempt_id)
        except OSError, RuntimeError, ValueError:
            return "unknown"
        if (
            issuer is None
            or issuer.window is None
            or (issuer.change_id, issuer.outcome_id, issuer.claim_id, issuer.role)
            != (change_id, outcome_id, claim_id, role)
        ):
            return "unknown"
        return self._window_liveness_probe.window_state(issuer.window)

    def _other_changes_fill_capacity(self, change_id: str) -> bool:
        """Report capacity held by other Changes; unreadable occupancy never claims a capacity wait."""
        try:
            occupancy = self._execution_occupancy_by_change()
        except DeliveryRuntimeConflictError, OSError, RuntimeError, ValueError:
            return False
        return sum(count for owner, count in occupancy.items() if owner != change_id) >= self._execution_capacity

    def _change_activity_progress(
        self,
        snapshot: DeliveryPortfolioSnapshot,
        cards: tuple[WorkItemCardView, ...],
        decisions: tuple[DeliveryReadiness, ...],
    ) -> DeliveryProgress | None:
        frontier = snapshot.frontier
        if frontier.change_completion is not None:
            return "completed"
        if frontier.change_abandonment is not None:
            return None
        if frontier.change_deferral is not None:
            return "paused"
        current = tuple(
            card.model_copy(update={"readiness": decision}) for card, decision in zip(cards, decisions, strict=True)
        )
        activity = self._change_activity_card(snapshot, current)
        return activity.readiness.progress if activity is not None and activity.readiness is not None else None

    def _change_activity_card(
        self, snapshot: DeliveryPortfolioSnapshot, cards: tuple[WorkItemCardView, ...]
    ) -> WorkItemCardView | None:
        """Choose the card carrying Change activity: containment, current ownership, next eligible, publication."""
        if not cards:
            return None
        if (
            any(card.readiness and card.readiness.reason_code == "builder-transition-contained" for card in cards)
            or self._repair_proposal(snapshot) is not None
        ):
            return self._selected_change_card(snapshot, cards)
        owned = next(
            (
                card
                for card in cards
                if card.readiness is not None
                and (
                    card.readiness.status == "running"
                    or card.readiness.reason_code in {"engine-action-pending", "worker-stall-wait"}
                )
            ),
            None,
        )
        if owned is not None:
            return owned
        runtime = self._runtimes.get(snapshot.contract.change_id)
        try:
            claimable = set(runtime.claimable_outcome_ids()) if runtime is not None else set()
        except OSError, RuntimeError, ValueError:
            claimable = set()
        outcome_cards = {card.work_item_id: card for card in cards if card.scope is WorkItemScope.OUTCOME}
        ranked = sorted(
            (self._snapshot_dependency_depth(snapshot, outcome.outcome_id), index, outcome.outcome_id)
            for index, outcome in enumerate(snapshot.contract.outcomes)
            if outcome.outcome_id in claimable and outcome.outcome_id in outcome_cards
        )
        if ranked:
            return outcome_cards[ranked[0][2]]
        unfinished = next(
            (
                card
                for card in outcome_cards.values()
                if card.readiness is not None and card.readiness.status != "complete"
            ),
            None,
        )
        if unfinished is not None:
            return unfinished
        return next((card for card in cards if card.scope is WorkItemScope.CHANGE_PUBLICATION), None)

    def _derive_finalization_retry_identity(  # noqa: PLR0913 - identity inputs mirror both read and acquire fences.
        self,
        change_id: str,
        *,
        finalization: DeliveryFinalizationReceipt | None,
        invalidation: DeliveryFinalizationInvalidationReceipt | None,
        coordination: ChangeCoordination | None = None,
        retry_ledger: RetryLedger | None = None,
        recover_transactions: bool = True,
    ) -> tuple[str | None, str | None, RetryEpisodeKey | None]:
        """Resolve finalizer retry identity and any linked original attempt without mutation."""
        finalization_id = (
            finalization.finalization_id
            if finalization is not None
            else (
                invalidation.finalization_id
                if invalidation is not None and invalidation.reason == "review-repair"
                else None
            )
        )
        resume_attempt_id = None
        retry_key: RetryEpisodeKey | None = None
        if finalization is None:
            coordination = coordination or self._workspace_manager.show(change_id)
            prior_finalization = coordination.finalization_attempt
            if prior_finalization is not None and prior_finalization.finished_at is not None:
                ledger = retry_ledger or RetryLedger(self._target_root, change_id, clock=self._clock)
                repair_binding = ledger.repair_binding_for_original_attempt(
                    prior_finalization.writer.attempt_id,
                    recover_transactions=recover_transactions,
                )
                if repair_binding is not None:
                    resume_attempt_id = prior_finalization.writer.attempt_id
                    repair_episode = ledger.episode_for_attempt(repair_binding.repair_attempt_id)
                    if repair_episode is None:
                        message = "repair binding episode is unavailable"
                        raise RetryLedgerConflictError(message)
                    finalization_id = repair_episode.key.finalization_id
                else:
                    failed_episode = ledger.episode_for_attempt(prior_finalization.writer.attempt_id)
                    if failed_episode is not None:
                        if (
                            failed_episode.key.action_kind != WorkItemActionKind.FINALIZE.value
                            or failed_episode.failure_class is not RetryFailureClass.MECHANICAL
                        ):
                            message = "finished Finalizer attempt is bound to a different retry episode"
                            raise RetryLedgerConflictError(message)
                        if failed_episode.settled_failure(prior_finalization.writer.attempt_id):
                            retry_key = failed_episode.key
                            finalization_id = retry_key.finalization_id
        return finalization_id, resume_attempt_id, retry_key

    def _settled_attention_exhausted_finalizer_episode(
        self,
        change_id: str,
        retry_ledger: RetryLedger,
    ) -> RetryEpisodeSummary | None:
        coordination = self._workspace_manager.show(change_id)
        attention = coordination.finalization_attention
        if attention is None:
            return None
        prior_finalization = coordination.finalization_attempt
        episode = retry_ledger.episode_for_attempt(attention.attempt_id)
        if (
            prior_finalization is None
            or prior_finalization.finished_at is None
            or prior_finalization.writer.attempt_id != attention.attempt_id
            or episode is None
            or episode.key.action_kind != WorkItemActionKind.FINALIZE.value
            or episode.failure_class is not RetryFailureClass.MECHANICAL
            or not episode.settled_failure(attention.attempt_id)
        ):
            message = "settled Finalizer attention has no matching failed retry episode"
            raise RetryLedgerConflictError(message)
        return episode if episode.stop_code is RetryStopCode.EXHAUSTED else None

    def _retry_readiness_key(
        self,
        snapshot: DeliveryPortfolioSnapshot,
        card: WorkItemCardView,
        decision: DeliveryReadiness,
        exact_head: str,
        binding: OutcomeAuthorityBinding | None,
    ) -> RetryEpisodeKey | None:
        action = decision.operation
        if action is None:
            return None
        if (
            card.scope is WorkItemScope.OUTCOME
            and card.work_item_id != snapshot.contract.change_id
            and binding is not None
        ):
            outcome = next((item for item in snapshot.contract.outcomes if item.outcome_id == card.work_item_id), None)
            if outcome is not None:
                role = (
                    DeliveryWorkerRole.BUILDER
                    if binding.stage is DeliveryStage.IMPLEMENTATION
                    else DeliveryWorkerRole.PLANNER
                )
                completed = {result.task_id for result in binding.results}
                handoff_context = binding.builder_handoff_context
                task_lineage = (
                    next(
                        (
                            task.task_id
                            for task in binding.tasks
                            if task.task_id not in completed
                            and set(task.dependency_ids) <= completed
                            and (handoff_context is None or task.task_id == handoff_context.original_task_id)
                        ),
                        card.work_item_id,
                    )
                    if role is DeliveryWorkerRole.BUILDER
                    else card.work_item_id
                )
                return RetryEpisodeKey.worker(
                    snapshot.contract.change_id,
                    f"{role.value}-claim",
                    exact_head,
                    contract_digest=contract_fingerprint(snapshot.contract),
                    outcome_id=card.work_item_id,
                    task_lineage=task_lineage,
                    procedure_class=role.value,
                    original_candidate=(
                        binding.candidate.digest
                        if binding.candidate is not None
                        else binding.result_candidate.digest
                        if binding.result_candidate is not None
                        else card.work_item_id
                    ),
                )
        if action is WorkItemActionKind.FINALIZE:
            finalization_id, _resume_attempt_id, retry_key = self._derive_finalization_retry_identity(
                snapshot.contract.change_id,
                finalization=snapshot.frontier.finalization,
                invalidation=snapshot.frontier.finalization_invalidation,
                recover_transactions=False,
            )
            if retry_key is not None:
                return retry_key
        else:
            finalization_id = (
                snapshot.frontier.finalization.finalization_id if snapshot.frontier.finalization is not None else None
            )
        return RetryEpisodeKey.engine(
            snapshot.contract.change_id,
            action.value,
            exact_head,
            decision.basis.target_head,
            finalization_id,
        )

    def _with_worker_stall_readiness(
        self,
        snapshot: DeliveryPortfolioSnapshot,
        cards: tuple[WorkItemCardView, ...],
        decisions: tuple[DeliveryReadiness, ...],
    ) -> tuple[DeliveryReadiness, ...]:
        """Replace running readiness for claims whose issuing window is gone with the exact leftover-work wait."""
        stalls = self._observed_worker_stalls(snapshot)
        try:
            finalizer = self._finalizer_stall(snapshot.contract.change_id)
        except OSError, RuntimeError, ValueError:
            finalizer = None
        if not stalls and finalizer is None:
            return decisions
        frontier = snapshot.frontier
        active = sum(binding.active_claim is not None for binding in frontier.bindings)
        change_stalled = finalizer is not None or (len(stalls) == active and frontier.integration_repair_claim is None)
        observed = ((finalizer[1],) if finalizer is not None else ()) + tuple(stalls.values())
        eligible = tuple(stall.eligible_at for stall in observed)
        change_stall = _WorkerStall(
            eligible_at=None if None in eligible else max(eligible),
            quiet=False,
            # Every stall of one Change scans the same worktree; repeat counts would overstate it.
            active_processes=next((stall.active_processes for stall in observed if stall.active_processes), ()),
        )
        updated: list[DeliveryReadiness] = []
        for card, decision in zip(cards, decisions, strict=True):
            if card.scope is WorkItemScope.OUTCOME and card.work_item_id in stalls:
                stall = stalls[card.work_item_id]
            elif card.scope is WorkItemScope.CHANGE_PUBLICATION and change_stalled:
                stall = change_stall
            else:
                updated.append(decision)
                continue
            if decision.status != "running":
                updated.append(decision)
                continue
            eligible_at = stall.eligible_at
            updated.append(
                decision.model_copy(
                    update={
                        "status": "waiting",
                        "reason_code": "worker-stall-wait",
                        "executable": False,
                        "action": None,
                        "next_actor": WorkItemNextActor.AGENT,
                        "next_eligible_at": (
                            eligible_at.isoformat().replace("+00:00", "Z") if eligible_at is not None else None
                        ),
                        "prompt": _worker_stall_prompt(snapshot.contract.change_id, stall),
                    }
                )
            )
        return tuple(updated)

    def _with_retry_readiness(  # noqa: C901, PLR0912 - maps one persisted policy to the shared readiness contract.
        self,
        snapshot: DeliveryPortfolioSnapshot,
        card: WorkItemCardView,
        decision: DeliveryReadiness,
    ) -> DeliveryReadiness:
        """Overlay durable retry state without creating or mutating a ledger on read."""
        action = decision.operation
        if action is None:
            return decision
        if decision.status == "running":
            return decision
        binding = (
            next((item for item in snapshot.frontier.bindings if item.outcome_id == card.work_item_id), None)
            if card.scope is WorkItemScope.OUTCOME
            else None
        )
        handoff_attempt_id = None
        if (
            binding is not None
            and binding.block is not None
            and not binding.block.resolved
            and binding.block.request_id is None
            and not any(request.resolution is None for request in binding.requests)
            and binding.builder_handoff_context is not None
        ):
            handoff_attempt_id = binding.builder_handoff_context.attempt_id
        exact_head = decision.basis.candidate_head or decision.basis.source_head
        if (
            handoff_attempt_id is None
            and exact_head is None
            and binding is not None
            and binding.block is not None
            and binding.builder_handoff_context is not None
            and binding.block.block_id == f"builder-attempt-limit-{binding.builder_handoff_context.settlement_id}"
        ):
            exact_head = binding.builder_handoff_context.last_reviewed_commit
        if exact_head is None and handoff_attempt_id is None:
            return decision
        failure_class = (
            RetryFailureClass.ACCEPTANCE
            if action is WorkItemActionKind.OBSERVE_ACCEPTANCE
            else RetryFailureClass.TRANSIENT
            if action
            in {
                WorkItemActionKind.MARK_READY,
                WorkItemActionKind.SYNC_TARGET,
                WorkItemActionKind.OBSERVE_ACCEPTANCE,
            }
            else RetryFailureClass.MECHANICAL
        )
        episode: RetryEpisodeSummary | None = None
        history: tuple[DeliveryRetryAttemptView, ...] = ()
        try:
            retry_ledger = RetryLedger(self._target_root, snapshot.contract.change_id, clock=self._clock)
            if action is WorkItemActionKind.SYNC_TARGET:
                episode = self._settled_attention_exhausted_finalizer_episode(snapshot.contract.change_id, retry_ledger)
                if episode is not None:
                    failure_class = episode.failure_class
            if episode is None:
                if handoff_attempt_id is not None:
                    episode = retry_ledger.episode_for_attempt(handoff_attempt_id)
                elif exact_head is not None:
                    key = self._retry_readiness_key(snapshot, card, decision, exact_head, binding)
                    if key is not None:
                        episode = retry_ledger.episode(key)
            if episode is not None and (
                episode.failure_class is not failure_class
                or (handoff_attempt_id is not None and episode.stop_code is not RetryStopCode.EXHAUSTED)
            ):
                episode = None
            if episode is not None:
                history = retry_ledger.attempt_history(episode)
        except OSError, RetryLedgerConflictError, RetryLedgerCorruptError, RuntimeError, ValueError:
            unavailable = decision.model_copy(
                update={
                    "status": "unavailable",
                    "reason_code": "retry-ledger-unavailable",
                    "executable": False,
                    "action": None,
                    "stop_reason": "retry-ledger-unavailable",
                }
            )
            return self._with_engine_action_prompt(snapshot.contract.change_id, unavailable)
        if episode is None:
            return decision
        updates: dict[str, object] = {
            "attempts": episode.total_attempts,
            "next_eligible_at": episode.next_eligible_at,
            "stop_reason": episode.stop_code.value if episode.stop_code is not None else None,
            "retry_history": history,
        }
        backoff_active = episode.next_eligible_at is not None and _timestamp(self._clock()) < _timestamp(
            episode.next_eligible_at
        )
        if backoff_active:
            updates.update(
                {
                    "status": "waiting",
                    "reason_code": "retry-backoff",
                    "executable": False,
                    "action": None,
                    "next_actor": WorkItemNextActor.AGENT,
                }
            )
        elif episode.last_status in {"reserved", "contained"}:
            updates.update(
                {
                    "status": "blocked",
                    "reason_code": "retry-containment",
                    "executable": False,
                    "action": None,
                    "next_actor": WorkItemNextActor.NONE,
                    "stop_reason": RetryStopCode.CONTAINMENT.value,
                }
            )
        elif episode.stop_code is RetryStopCode.EXHAUSTED:
            updates.update(
                {
                    "status": "blocked",
                    "reason_code": "retry-exhausted",
                    "operation": None,
                    "executable": False,
                    "action": None,
                    "next_actor": WorkItemNextActor.AGENT,
                }
            )
        elif episode.stop_code is RetryStopCode.ACCEPTANCE_WAIT:
            updates.update(
                {
                    "status": "waiting",
                    "reason_code": "acceptance-wait",
                    "executable": False,
                    "action": None,
                    "next_actor": WorkItemNextActor.YOU,
                }
            )
        elif episode.stop_code is RetryStopCode.CONTAINMENT:
            updates.update(
                {
                    "status": "blocked",
                    "reason_code": "retry-containment",
                    "executable": False,
                    "action": None,
                    "next_actor": WorkItemNextActor.NONE,
                }
            )
        return self._with_engine_action_prompt(snapshot.contract.change_id, decision.model_copy(update=updates))

    @classmethod
    def _with_engine_action_prompt(cls, change_id: str, readiness: DeliveryReadiness) -> DeliveryReadiness:
        prompt = cls._engine_action_prompt(
            change_id,
            readiness.reason_code,
            executable=readiness.executable,
        )
        return readiness.model_copy(update={"prompt": prompt})

    def _settled_attention_sync_reason(
        self,
        snapshot: DeliveryPortfolioSnapshot,
        reason: str | None,
    ) -> str | None:
        if reason != "settled-attention-target-drift":
            return reason
        if (
            not self._supports_finalization(snapshot.frontier)
            or self._change_branch_publisher is None
            or self._draft_pull_request_publisher is None
        ):
            return reason
        return "target-sync-required"

    def _capture_action_basis(  # noqa: C901 - one ordered row per workspace and target state.
        self,
        snapshot: DeliveryPortfolioSnapshot,
        cards: tuple[WorkItemCardView, ...],
        basis: DeliveryReadinessBasis,
        merge: MergeDecision | None = None,
    ) -> tuple[DeliveryReadinessBasis, str | None, str | None]:
        try:
            coordination = self._workspace_manager.show(snapshot.contract.change_id)
        except OSError, RuntimeError, ValueError:
            return basis, "coordination-unavailable", None
        if not self._coordinator.recovery_exclusions_verified(coordination):
            return basis, "coordination-unavailable", None
        action = coordination.continuation_action
        basis = basis.model_copy(update={"continuation_id": action.operation_id if action else None})
        if action is not None and action.finished_at is None:
            reason, guidance = self._continuation_journal_readiness(action)
            return basis, reason, guidance
        needs_workspace = self._supports_finalization(snapshot.frontier) or any(
            card.action.kind
            in {
                WorkItemActionKind.FINALIZE,
                WorkItemActionKind.RECONCILE_CHECKPOINT,
                WorkItemActionKind.MARK_READY,
                WorkItemActionKind.OBSERVE_ACCEPTANCE,
            }
            for card in cards
        )
        if needs_workspace and not self._snapshot_has_active_claims(snapshot):
            basis, reason = self._capture_readiness_workspace(snapshot, basis)
            reason = self._settled_attention_sync_reason(snapshot, reason)
            sync = snapshot.frontier.target_sync_receipt
            pending = snapshot.frontier.pending_checkpoint
            if (
                reason is None
                and self._supports_finalization(snapshot.frontier)
                and self._change_branch_publisher is not None
            ):
                if pending is not None and pending.head is not None and snapshot.frontier.published_head is None:
                    reason = "checkpoint-pending"
                elif sync is None or sync.target_head != basis.target_head:
                    reason = "target-sync-required"
            elif reason is None and merge is not None and merge.reason == "target-sync-required":
                # U3(a): a finalized Change syncs to the provider's target head, not the unfetched local ref.
                basis = basis.model_copy(update={"target_head": merge.target_head})
                reason = "target-sync-required"
            return basis, reason, None
        if any(
            self._captured_action(snapshot.frontier, card).kind is WorkItemActionKind.START_ORCHESTRATION
            for card in cards
        ):
            basis = basis.model_copy(update={"source_head": coordination.last_reviewed_commit})
        if any(
            binding.active_claim is not None
            and binding.active_claim.worker_role is DeliveryWorkerRole.BUILDER
            and (
                coordination.writer is None
                or coordination.writer.kind != "build"
                or coordination.writer.claim_id != binding.active_claim.claim_id
                or coordination.writer.attempt_id != binding.active_claim.attempt_id
            )
            for binding in snapshot.frontier.bindings
        ):
            return basis, "claim-custody-unreconciled", None
        return basis, None, None

    @staticmethod
    def _read_continuation_journal(operation_fd: int, name: str) -> bytes | None:
        """Read one bounded contained journal without following links."""
        try:
            return read_contained(operation_fd, Path(name), limit=_MAX_CONTINUATION_JOURNAL_BYTES)
        except OSError, TransactionPathError:
            return b""

    def _continuation_journal_readiness(  # noqa: C901, PLR0911, PLR0912 - each journal state fails closed distinctly.
        self, action: ChangeContinuationAction
    ) -> tuple[str, str | None]:
        """Classify retained engine custody from exact journals without reconciling it."""
        intent_path = self._coordinator.continuation_record_path(action.change_id, action.operation_id)

        try:
            root_fd = os.open(self._coordinator.runtime_root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        except OSError:
            return "engine-action-blocked", None
        try:
            relative_intent = intent_path.relative_to(self._coordinator.runtime_root)
            with contained_directory(root_fd, relative_intent.parent) as operation_fd:
                intent = self._read_continuation_journal(operation_fd, "intent.json")
                if intent in {None, b""}:
                    return "engine-action-blocked", None
                try:
                    original = ChangeContinuationAction.model_validate_json(intent)
                except TypeError, ValueError:
                    return "engine-action-blocked", None
                if original != action.model_copy(update={"finished_at": None}):
                    return "engine-action-blocked", None

                result = self._read_continuation_journal(operation_fd, "result.json")
                if result is None:
                    started = self._read_continuation_journal(operation_fd, "started.json")
                    if started is None:
                        return "engine-action-pending", None
                    if started == _canonical_model_bytes(action):
                        return (
                            "engine-action-interrupted",
                            (
                                "The Delivery engine owner has no exact authoritative result/readback. Preserve "
                                "custody and journals; verified host/worker closure and settlement of all descendant "
                                "writers and jobs is required before resume; do not retry or infer termination."
                            ),
                        )
                    return "engine-action-blocked", None

                if result == b"":
                    return "engine-action-blocked", None
                started = self._read_continuation_journal(operation_fd, "started.json")
                if started is not None and (started == b"" or started != _canonical_model_bytes(action)):
                    return "engine-action-blocked", None
                try:
                    recorded = DeliveryEngineActionResult.model_validate_json(result)
                except TypeError, ValueError:
                    return "engine-action-blocked", None
                if (
                    recorded.action != original
                    or recorded.action.operation_id != action.operation_id
                    or recorded.action.change_id != action.change_id
                ):
                    return "engine-action-blocked", None
                if recorded.kind != "blocked":
                    return "engine-action-blocked", None
                if recorded.reason_code == "engine-action-interrupted":
                    return (
                        recorded.reason_code,
                        (
                            "The Delivery engine owner has no exact authoritative result/readback. Preserve custody "
                            "and journals; verified host/worker closure and settlement of all descendant writers and "
                            "jobs is required before resume; do not retry or infer termination."
                        ),
                    )
                if recorded.failure is None:
                    return recorded.reason_code, None
                if recorded.failure.code in _PUBLICATION_READBACK_FAILURE_CODES:
                    guidance = (
                        "The publication owner has a recorded provider/readback failure; no exact authoritative "
                        "publication readback is available. Preserve custody and journals; the publication owner "
                        "must resolve this condition before resume; do not retry or release custody."
                    )
                else:
                    state = (
                        "recorded failure"
                        if recorded.reason_code == "engine-action-failed"
                        else "recorded incomplete result"
                    )
                    guidance = (
                        f"The Delivery engine owner has a {state}; its exact authoritative result/readback is "
                        "retained. Preserve custody and journals; the engine owner must resolve this condition "
                        "before resume; do not retry or release custody."
                    )
                return recorded.reason_code, guidance
        except OSError, TransactionPathError, ValueError:
            return "engine-action-blocked", None
        finally:
            os.close(root_fd)

    @staticmethod
    def _with_finalization_report(
        decision: DeliveryReadiness,
        reports: FinalizationReportSnapshot | None,
    ) -> DeliveryReadiness:
        if reports is None:
            return decision.model_copy(
                update={
                    "reason_code": "report-store-unavailable"
                    if decision.reason_code == "ready"
                    else decision.reason_code,
                    "checks_state": "passed" if decision.checks_state == "passed" else "unknown",
                }
            )
        if not reports.reports:
            return decision
        report = reports.reports[-1]
        current = (
            report.request.expected_change_head == decision.basis.candidate_head
            and report.request.expected_contract_digest == decision.basis.contract_digest
            and decision.checks_state != "passed"
        )
        updates = {
            "last_attempt": FinalizationAttempt(report=report, applicability="current" if current else "historical")
        }
        if current and decision.reason_code not in {"workspace-dirty", "workspace-inspection-failed"}:
            updates["checks_state"] = report.request.checks_state
        if current and decision.executable and decision.operation is WorkItemActionKind.FINALIZE:
            updates["action"] = decision.action.model_copy(update={"label": "Retry verification"})
        return decision.model_copy(update=updates)

    def _finalizer_attention_retry_reason(
        self,
        snapshot: DeliveryPortfolioSnapshot,
        basis: DeliveryReadinessBasis,
        workspace: tuple[ChangeCoordination, str, str, tuple[str, ...], str | None],
        reports: FinalizationReportSnapshot,
        receipt: FinalizerSettlementReceipt | None,
    ) -> str | None:
        coordination, head, fingerprint, paths, workspace_reason = workspace
        attention = coordination.finalization_attention
        attempt = coordination.finalization_attempt
        if attention is None:
            return "finalization-failed"
        if paths or attention.workspace_paths:
            return "workspace-dirty"
        if (
            head != attention.expected_head
            or head != attention.workspace_head
            or fingerprint != attention.workspace_fingerprint
        ):
            return "workspace-preflight-failed"
        report = next((item for item in reports.reports if item.report_id == attention.report_id), None)
        if (
            attempt is None
            or attempt.finished_at is None
            or receipt is None
            or not self._finalizer_attention_matches_receipt(coordination, receipt)
            or reports.current_report_id != attention.report_id
            or report is None
            or report != receipt.report
            or attempt.contract_digest != basis.contract_digest
            or attempt.contract_digest != contract_fingerprint(snapshot.contract)
            or attempt.frontier_digest != basis.frontier_digest
            or attempt.frontier_digest != snapshot.version
            or attempt.exact_head != head
            or attempt.writer.attempt_id != attention.attempt_id
            or report.request.attempt_key != attention.attempt_id
            or report.request.expected_change_head != head
            or report.request.expected_reviewed_head != coordination.last_reviewed_commit
            or report.request.expected_contract_digest != attempt.contract_digest
            or report.request.expected_frontier_digest != attempt.frontier_digest
        ):
            return "finalization-failed"
        if attempt.target_head != basis.target_head:
            return "settled-attention-target-drift"
        return workspace_reason if workspace_reason not in {None, "active-custody"} else None

    def _capture_readiness_workspace(
        self,
        snapshot: DeliveryPortfolioSnapshot,
        basis: DeliveryReadinessBasis,
    ) -> tuple[DeliveryReadinessBasis, str | None]:
        try:
            coordination = self._workspace_manager.show(snapshot.contract.change_id)
            basis = basis.model_copy(
                update={
                    "reviewed_head": coordination.last_reviewed_commit,
                    "target_head": self._workspace_manager.observed_target_head(),
                }
            )
            if (
                coordination.writer is not None
                and coordination.writer.kind not in {"finalize", "finalization-attention"}
            ) or coordination.publication_lease is not None:
                return basis, "active-custody"
            coordination, head, fingerprint, _paths, reason = self._workspace_manager.capture_finalization_workspace(
                snapshot.contract.change_id,
                tuple(result.completed_commit for binding in snapshot.frontier.bindings for result in binding.results),
            )
            basis = basis.model_copy(update={"candidate_head": head, "workspace_fingerprint": fingerprint})
            if coordination.writer is not None and coordination.writer.kind in {
                "finalize",
                "finalization-attention",
            }:
                reports = FinalizationReportStore(self._target_root, snapshot.contract.change_id).read()
                if coordination.writer.kind == "finalization-attention":
                    receipt = self._read_finalizer_settlement_receipt(
                        snapshot.contract.change_id, coordination.writer.attempt_id
                    )
                    return basis, self._finalizer_attention_retry_reason(
                        snapshot,
                        basis,
                        (coordination, head, fingerprint, _paths, reason),
                        reports,
                        receipt,
                    )
                if any(report.request.attempt_key == coordination.writer.attempt_id for report in reports.reports):
                    return basis, "finalization-failed"
            invalidation = snapshot.frontier.finalization_invalidation
            if invalidation and invalidation.reason == "review-repair" and head == invalidation.expected_head:
                reason = "review-repair"
        except FinalizationReportError:
            return basis, "report-store-unavailable"
        except OSError, RuntimeError, subprocess.SubprocessError, ValueError:
            return basis, "workspace-inspection-failed"
        return basis, reason

    @staticmethod
    def _supports_finalization(frontier: DeliveryFrontier) -> bool:
        return (
            frontier.finalization is None
            and frontier.change_completion is None
            and frontier.change_abandonment is None
            and frontier.change_deferral is None
            and frontier.change_disposition is None
            and frontier.integration_repair_claim is None
            and all(
                binding.stage is DeliveryStage.COMPLETED
                and binding.active_claim is None
                and binding.recovery_attention is None
                and not any(request.resolution is None for request in binding.requests)
                and (binding.block is None or binding.block.resolved)
                and tuple(result.task_id for result in binding.results) == binding.task_ids
                for binding in frontier.bindings
            )
        )

    @classmethod
    def _captured_action(cls, frontier: DeliveryFrontier, card: WorkItemCardView) -> WorkItemAction:
        if card.scope is WorkItemScope.CHANGE_PUBLICATION and cls._supports_finalization(frontier):
            return WorkItemAction(
                kind=WorkItemActionKind.FINALIZE, label="Finalize Change", command=f"/finalize-change {card.change_id}"
            )
        if card.action.kind is WorkItemActionKind.FINALIZE or (
            card.scope is WorkItemScope.OUTCOME
            and card.stage is not None
            and card.stage.value == DeliveryStage.DESIGN.value
        ):
            return WorkItemAction()
        if (
            card.scope is WorkItemScope.OUTCOME
            and card.stage is not None
            and card.stage.value in {"planning", "implementation"}
            and card.needs is WorkItemNeed.NONE
            and card.activity.state is WorkItemActivityState.READY
            and card.action.kind is WorkItemActionKind.NONE
        ):
            return WorkItemAction(kind=WorkItemActionKind.START_ORCHESTRATION, label="Copy continuation prompt")
        return card.action

    @staticmethod
    def _action_prerequisites(operation: WorkItemActionKind | None, workspace_reason: str | None) -> tuple[str, str]:
        if operation in {
            WorkItemActionKind.FINALIZE,
            WorkItemActionKind.RECONCILE_CHECKPOINT,
            WorkItemActionKind.SYNC_TARGET,
            WorkItemActionKind.MARK_READY,
            WorkItemActionKind.OBSERVE_ACCEPTANCE,
        } and workspace_reason not in {None, "target-sync-required", "checkpoint-pending"}:
            return ("unavailable" if workspace_reason == "workspace-inspection-failed" else "blocked"), workspace_reason
        if operation is None:
            return "waiting", "publication-wait"
        return "ready", "ready"

    @classmethod
    def _engine_action_prompt(cls, change_id: str, reason: str, *, executable: bool) -> str | None:
        if executable:
            return (
                f"/continue-change {change_id} reread get_change and pass its readiness basis unchanged to "
                "acquire_change_action; declare only capabilities this session can dispatch and execute only the "
                "acquired operation. Yield on busy, waiting, and human; do not dispatch siblings or infer progress."
            )
        if reason in {"retry-exhausted", "settled-attention-target-drift"}:
            diagnosis = (
                "Diagnose the exhausted retry episode read-only. Preserve its block and attempt history; do not clear "
                "the block, retry, dispatch, or reset the budget. Any new attempt requires approved current authority."
                if reason == "retry-exhausted"
                else "Diagnose settled Finalizer attention after the target head changed. Read-only: preserve the "
                "retained attention, failure report, receipt, and retry history. Do not synchronize the target, retry "
                "finalization, clear the block, or reset the budget; stop for owner direction before any new attempt."
            )
            return f"/inspect-change {change_id} {diagnosis}"
        if reason == "engine-action-pending":
            return (
                f"/continue-change {change_id} Resume the exact engine-selected operation after rereading "
                "readiness; do not replace it or infer closure."
            )
        if reason in {"retry-transition-contained", "builder-transition-contained"}:
            if reason == "retry-transition-contained":
                diagnostic = (
                    "The refused RetryDelivery remains in the existing work-item retry diagnostic; "
                    "the claim owner remains active. Make no MCP calls and query no additional "
                    "Delivery authority. Keep it read-only: preserve the claim, stage, any existing "
                    "managed workspace, inspected files, and retry budget; do not retry, unblock, "
                    "restart, release, edit, repair, or dispatch a replacement. Resume requires "
                    "verified host worker-exclusion and settlement through a supported owner path; "
                    "this inspection establishes neither."
                )
            else:
                diagnostic = (
                    "The refused transition remains in the existing work-item recovery view; "
                    "the current claim owner remains on its card. Do not query for additional "
                    "Delivery authority. The submitted block or return was refused because host "
                    "worker-exclusion evidence is missing. Keep it read-only: preserve custody, "
                    "stage, worktree, inspected files, and retry budget; do not answer, unblock, "
                    "restart, release, edit, repair, or dispatch a replacement. Resume requires "
                    "verified host exclusion and settlement through a supported recovery path; "
                    "this diagnostic does not establish that such a capability is available."
                )
            return (
                f"/repair-delivery Inspect only Change {change_id} using the bounded offline "
                f"`delivery-diagnose inspect --change-id {change_id}` operation. "
                f"{diagnostic}"
            )
        if reason == "engine-action-interrupted":
            return (
                f"/continue-change {change_id} only after the Delivery engine owner verifies host/worker closure "
                "and settles all descendant writers and jobs; preserve custody and journals, and do not retry or "
                "infer termination."
            )
        prompt: str | None = None
        if reason in {
            "active-custody",
            "claim-activation-failed",
            "claim-custody-unreconciled",
            "coordination-unavailable",
            "engine-action-failed",
            "engine-action-incomplete",
            "engine-action-blocked",
        }:
            prompt = (
                f"/repair-delivery Diagnose Change {change_id} read-only; preserve existing custody and journals. "
                "This does not repair authority or prove host/worker closure. Do not stop a worker, retry, release "
                "custody, or dispatch a replacement. The responsible owner must establish any missing authority "
                "through a supported path before Delivery can resume; this diagnostic does not supply that authority."
            )
        return prompt

    @staticmethod
    def _user_action_readiness(card: WorkItemCardView, operation: WorkItemActionKind | None) -> tuple[str, str]:
        if (
            card.scope is WorkItemScope.OUTCOME
            and card.stage is not None
            and card.stage.value == DeliveryStage.DESIGN.value
        ):
            return "blocked", "design-attention"
        return ("ready" if operation else "blocked"), "request-action"

    @classmethod
    def _readiness_prompt(
        cls,
        snapshot: DeliveryPortfolioSnapshot,
        card: WorkItemCardView,
        reason: str,
        *,
        executable: bool,
    ) -> str | None:
        if reason != "design-attention":
            return cls._engine_action_prompt(snapshot.contract.change_id, reason, executable=executable)
        binding = next(item for item in snapshot.frontier.bindings if item.outcome_id == card.work_item_id)
        return cls._design_attention_prompt(snapshot.contract.change_id, binding)

    @classmethod
    def _card_readiness(
        cls,
        snapshot: DeliveryPortfolioSnapshot,
        card: WorkItemCardView,
        basis: DeliveryReadinessBasis,
        workspace_reason: str | None,
    ) -> DeliveryReadiness:
        frontier = snapshot.frontier
        finalization = card.scope is WorkItemScope.CHANGE_PUBLICATION and cls._supports_finalization(frontier)
        action = cls._captured_action(frontier, card)
        prerequisites = {
            "target-sync-required": WorkItemAction(kind=WorkItemActionKind.SYNC_TARGET, label="Synchronize target"),
            "checkpoint-pending": WorkItemAction(
                kind=WorkItemActionKind.RECONCILE_CHECKPOINT, label="Publish checkpoint"
            ),
        }
        action = prerequisites.get(workspace_reason, action) if finalization else action
        operation = action.kind if action.kind is not WorkItemActionKind.NONE else None
        status, reason = "ready", "ready"
        retry_contained = any(
            binding.retry_diagnostic is not None
            and (card.scope is WorkItemScope.CHANGE_PUBLICATION or binding.outcome_id == card.work_item_id)
            for binding in frontier.bindings
        )
        builder_contained = any(
            binding.recovery_attention is not None
            and binding.recovery_attention.diagnostic_transition is not None
            and (card.scope is WorkItemScope.CHANGE_PUBLICATION or binding.outcome_id == card.work_item_id)
            for binding in frontier.bindings
        )
        contained = retry_contained or builder_contained
        if contained or workspace_reason in {
            "engine-action-pending",
            "engine-action-interrupted",
            "engine-action-failed",
            "engine-action-incomplete",
            "engine-action-blocked",
        }:
            status = "running" if not contained and workspace_reason == "engine-action-pending" else "blocked"
            reason = (
                "retry-transition-contained"
                if retry_contained
                else "builder-transition-contained"
                if builder_contained
                else workspace_reason
            )
            operation = None if contained else operation
        elif workspace_reason == "coordination-unavailable":
            status, reason = "unavailable", workspace_reason
        elif workspace_reason == "claim-custody-unreconciled":
            status, reason = "blocked", workspace_reason
        elif (
            card.activity.state is WorkItemActivityState.WORKING
            or (
                card.scope is WorkItemScope.CHANGE_PUBLICATION
                and (any(binding.active_claim for binding in frontier.bindings) or frontier.integration_repair_claim)
            )
            or (card.scope is WorkItemScope.CHANGE_PUBLICATION and workspace_reason == "active-custody")
        ):
            status, reason = "running", "active-custody"
        elif frontier.change_completion is not None or frontier.change_abandonment is not None:
            status, reason = "complete", "change-terminal"
        elif frontier.change_deferral is not None:
            status, reason = ("ready" if operation else "blocked"), "change-paused"
        elif card.scope is WorkItemScope.OUTCOME and card.stage is not None and card.stage.value == "completed":
            status, reason = "complete", "change-terminal"
        elif card.needs is WorkItemNeed.DEPENDENCY:
            status, reason = "waiting", "dependency-wait"
        elif card.needs is WorkItemNeed.YOU and not finalization:
            status, reason = cls._user_action_readiness(card, operation)
        else:
            status, reason = cls._action_prerequisites(operation, workspace_reason)
        executable = status == "ready" and operation is not None
        prompt = cls._readiness_prompt(snapshot, card, reason, executable=executable)
        return DeliveryReadiness(
            status=status,
            operation=operation,
            executable=executable,
            next_actor=WorkItemNextActor.AGENT if finalization else card.next_actor,
            reason_code=reason,
            checks_state="passed" if frontier.finalization is not None else "not-run",
            basis=basis,
            action=action if executable else None,
            prompt=prompt,
        )

    @staticmethod
    def _design_attention_prompt(change_id: str, binding: OutcomeAuthorityBinding) -> str:
        return_context = binding.return_context
        if return_context is None:
            evidence = "No return context is recorded; do not infer a missing decision or evidence."
        else:
            locators = ", ".join(return_context.locators)
            evidence = (
                f"Outcome: {binding.outcome_id}. Delivery stage: {binding.stage.value}. "
                f"Return reason: {return_context.reason}. Source locators: {locators}. "
                f"Preserved commit: {return_context.preserved_commit or 'unavailable'}. "
                f"Completed boundary: {return_context.completed_boundary or 'unavailable'}."
            )
        if binding.builder_handoff_context is None:
            return (
                f"/design {change_id} Resume the existing Design session and assess its verified intent, Design "
                f"and persisted return evidence. {evidence} Require explicit user approval before revision "
                "or re-admission; this attention does not approve or admit a Design revision."
            )
        return (
            f"/inspect-change {change_id} Inspect the existing verified intent, Design and persisted return "
            f"evidence read-only. {evidence} Settlement only cleared the Builder claim and "
            "retained a passive workspace handoff; it does not approve or admit a Design revision or grant access "
            "to the managed worktree. Re-admission is unavailable while this handoff is retained; its correction "
            "is separate D04 work. Preserve the worktree. Only read-only inspection, defer or abandon is "
            "supported here; user approval does not bypass the retained-handoff admission fence."
        )

    def _worktree_cleanup_view(
        self, runtime: DeliveryRuntime, retained: RetainedChangeWorktree
    ) -> WorkItemWorktreeCleanupView:
        projection = self._retained_change_worktree_view(retained)
        try:
            completion = runtime.completion_receipt()
        except OSError, ValueError, DeliveryRuntimeConflictError:
            completion = None
        return WorkItemWorktreeCleanupView(
            eligible=projection.cleanup_eligible,
            blocked_reason=projection.cleanup_blocked_reason.value
            if projection.cleanup_blocked_reason is not None
            else None,
            completion_id=completion.completion_id if completion is not None else None,
        )

    def _worktree_recovery_view(
        self,
        retained: RetainedChangeWorktree,
    ) -> WorkItemWorktreeRecoveryView | None:
        if ChangeWorktreeAttentionCode.WORKTREE_MISSING not in retained.attention:
            return None
        allowed_attention = {
            ChangeWorktreeAttentionCode.COORDINATION_MISSING,
            ChangeWorktreeAttentionCode.GIT_REGISTRATION_MISSING,
            ChangeWorktreeAttentionCode.PRUNABLE,
            ChangeWorktreeAttentionCode.WORKTREE_MISSING,
        }
        blocked_reason: str | None = None
        if retained.writer is not None:
            blocked_reason = DeliveryRetainedWorktreeCleanupBlockReason.ACTIVE_WRITER.value
        elif retained.publication_expiry is not None and retained.publication_expiry > _timestamp(self._clock()):
            blocked_reason = DeliveryRetainedWorktreeCleanupBlockReason.ACTIVE_PUBLICATION_LEASE.value
        elif any(code not in allowed_attention for code in retained.attention):
            blocked_reason = DeliveryRetainedWorktreeCleanupBlockReason.WORKTREE_ATTENTION.value
        elif retained.last_reviewed_commit is None:
            blocked_reason = "reviewed-head-unavailable"
        return WorkItemWorktreeRecoveryView(
            eligible=blocked_reason is None,
            blocked_reason=blocked_reason,
            recovery_reviewed_head=retained.last_reviewed_commit,
        )

    def _portfolio_snapshots(self) -> tuple[DeliveryPortfolioSnapshot, ...]:
        self._reconcile_runtimes()
        return self._capture_portfolio_snapshots()

    def _capture_portfolio_snapshots(self) -> tuple[DeliveryPortfolioSnapshot, ...]:
        """Capture current runtime snapshots without rediscovering persisted Changes."""
        snapshots: list[DeliveryPortfolioSnapshot] = []
        retained_snapshots: dict[str, DeliveryPortfolioSnapshot] = {}
        for change_id, runtime in sorted(self._runtimes.items()):
            try:
                snapshot = self._delivery_snapshot(runtime)
            except OSError, RuntimeError, ValueError:
                snapshot = self._runtime_snapshots.get(change_id)
                if snapshot is None:
                    continue
                self._runtime_reconciliation_errors.setdefault(
                    change_id,
                    "Delivery runtime snapshot could not be refreshed.",
                )
            retained_snapshots[change_id] = snapshot
            snapshots.append(snapshot)
        self._runtime_snapshots = retained_snapshots
        return tuple(snapshots)

    def _execution_occupancy(self) -> int:
        """Count the largest observed active outcome claim set once per Change."""
        return sum(self._execution_occupancy_by_change().values())

    def _execution_occupancy_by_change(self) -> dict[str, int]:
        """Return the largest observed execution occupancy of each Change."""
        occupancy: dict[str, int] = {}
        for change_id, observation in self._discovered_changes.items():
            frontier = observation.frontier
            if frontier is None and change_id not in self._runtimes:
                raise DeliveryRuntimeReconciliationError(change_id, "execution occupancy is unknown")
            if frontier is not None:
                occupancy[change_id] = sum(binding.active_claim is not None for binding in frontier.bindings)
        for change_id, runtime in self._runtimes.items():
            try:
                active_count = len(runtime.active_claims())
            except OSError, RuntimeError, ValueError:
                active_count = self._persisted_claim_occupancy(change_id)
            occupancy[change_id] = max(occupancy.get(change_id, 0), active_count)
        try:
            registered = self._coordinator.list_registered()
            for change_id in self._runtimes.keys() | self._discovered_changes.keys():
                self._coordinator.show(change_id)
        except (OSError, RuntimeError, ValueError) as exc:
            raise DeliveryRuntimeReconciliationError(None, f"execution custody is unknown: {exc}") from exc
        for coordination in registered:
            if self._writer_occupies_execution_slot(coordination) or (
                coordination.continuation_action is not None and coordination.continuation_action.finished_at is None
            ):
                occupancy[coordination.change_id] = max(occupancy.get(coordination.change_id, 0), 1)
        return occupancy

    def _writer_occupies_execution_slot(
        self,
        coordination: ChangeCoordination,
        runtime: DeliveryRuntime | None = None,
    ) -> bool:
        """Count every live or unverified writer, excluding only an exact settled handoff."""
        writer = coordination.writer
        if writer is None:
            return False
        if writer.kind == "finalization-attention":
            try:
                receipt = self._read_finalizer_settlement_receipt(coordination.change_id, writer.attempt_id)
            except OSError, RuntimeError, ValueError:
                return True
            return not self._finalizer_attention_matches_receipt(coordination, receipt)
        if writer.kind != "handoff" or coordination.builder_handoff is None:
            return True
        runtime = runtime or self._runtimes.get(coordination.change_id)
        return runtime is None or self._settled_builder_handoff_binding(coordination, runtime) is None

    @staticmethod
    def _settled_builder_handoff_binding(
        coordination: ChangeCoordination,
        runtime: DeliveryRuntime,
    ) -> OutcomeAuthorityBinding | None:
        """Return only a frontier binding corroborating the exact ended workspace handoff."""
        handoff = coordination.builder_handoff
        writer = coordination.writer
        if (
            handoff is None
            or writer is None
            or writer.kind != "handoff"
            or writer != handoff.original_writer.model_copy(update={"kind": "handoff"})
        ):
            return None
        try:
            bindings = runtime.bindings()
        except (OSError, RuntimeError, ValueError) as exc:
            raise DeliveryRuntimeReconciliationError(
                coordination.change_id, "Builder handoff frontier authority is unavailable"
            ) from exc
        for binding in bindings:
            context = binding.builder_handoff_context
            if (
                binding.active_claim is None
                and context is not None
                and context.settlement_id == handoff.settlement_id
                and context.outcome_id == binding.outcome_id
                and context.original_task_id == handoff.original_task_id
                and context.attempt_id == handoff.original_writer.attempt_id
                and context.last_reviewed_commit == handoff.last_reviewed_commit
                and context.branch_head == handoff.branch_head
                and context.metadata_fingerprint == handoff.metadata_fingerprint
            ):
                return binding
        return None

    def _claimable_handoff_binding(
        self,
        coordination: ChangeCoordination,
        runtime: DeliveryRuntime,
        claimable_outcome_ids: set[str],
    ) -> OutcomeAuthorityBinding | None:
        handoff = coordination.builder_handoff
        if handoff is None:
            return None
        try:
            binding = self._settled_builder_handoff_binding(coordination, runtime)
        except OSError, RuntimeError, ValueError:
            return None
        context = binding.builder_handoff_context if binding is not None else None
        if (
            binding is None
            or binding.outcome_id not in claimable_outcome_ids
            or context is None
            or context.settlement_id != handoff.settlement_id
            or context.outcome_id != binding.outcome_id
            or context.original_task_id != handoff.original_task_id
            or not (
                (binding.stage == DeliveryStage.PLANNING and context.route == "same-outcome-planner")
                or (binding.stage == DeliveryStage.IMPLEMENTATION and context.route == "same-task")
            )
        ):
            return None
        return binding

    def _persisted_claim_occupancy(self, change_id: str) -> int:
        """Count structurally valid custody without admitting incompatible runtime authority."""
        try:
            path = self._target_root / "changes" / change_id / "frontier.json"
            frontier = parse_delivery_frontier(path.read_bytes())[0]
        except (OSError, RuntimeError, ValueError) as exc:
            raise DeliveryRuntimeReconciliationError(change_id, "execution occupancy is unreadable") from exc
        return sum(binding.active_claim is not None for binding in frontier.bindings)

    def _delivery_snapshot(
        self, runtime: DeliveryRuntime, *, observe_publication: bool = True
    ) -> DeliveryPortfolioSnapshot:
        frontier_bytes = runtime.frontier_bytes()
        frontier = parse_delivery_frontier(frontier_bytes)[0]
        change_id = runtime.contract.change_id
        cached = self._publication_observation_cache.get(change_id)
        observation = cached[2] if cached is not None and cached[1] == frontier.published_head else None
        if observe_publication:
            observation = self._publication_observation(change_id, frontier)
        return DeliveryPortfolioSnapshot.capture(
            runtime.contract,
            frontier_bytes,
            publication_observation=observation,
            merge_facts=self._merge_facts(change_id, frontier, observation, refresh=observe_publication),
        )

    def _merge_facts(
        self,
        change_id: str,
        frontier: DeliveryFrontier,
        observation: PublicationPullRequestObservationReceipt | None,
        *,
        refresh: bool,
    ) -> MergeFacts | None:
        """Read offer facts for an open awaiting-merge PR; failures are never cached (D8)."""
        publisher = self._draft_pull_request_publisher
        ready = frontier.ready
        if (
            publisher is None
            or ready is None
            or observation is None
            or observation.snapshot.state != "open"
            or resolve_publication_phase(frontier) is not WorkItemPublicationPhase.AWAITING_MERGE
        ):
            return None
        now = time.monotonic()
        cached = self._merge_facts_cache.get(change_id)
        if cached is not None and cached[1] == ready.receipt_id and (not refresh or cached[0] > now):
            return cached[2]
        if not refresh:
            return None
        provider = publisher.provider
        if not isinstance(provider, PublicationMergeProvider):
            facts = MergeFacts(capable=False)
        else:
            try:
                facts = MergeFacts(
                    capable=True,
                    evidence=provider.read_merge_evidence(ready.repository, ready.number),
                    settings=provider.read_merge_settings(ready.repository, publisher.target_branch),
                    checks=provider.observe_checks(
                        ObservePublicationChecks(
                            repository=ready.repository, number=ready.number, expected_head_sha=ready.head_sha
                        )
                    ),
                    target_head=provider.read_branch_head(ready.repository, publisher.target_branch).head_sha,
                )
            except OSError, PublicationProviderError, RuntimeError, subprocess.SubprocessError, ValueError:
                return None
        self._merge_facts_cache[change_id] = (now + _PUBLICATION_OBSERVATION_CACHE_SECONDS, ready.receipt_id, facts)
        return facts

    def _merge_decision(self, snapshot: DeliveryPortfolioSnapshot) -> MergeDecision | None:
        """Classify an open awaiting-merge PR at the finalized head; other states stay with acceptance."""
        frontier = snapshot.frontier
        finalization, ready = frontier.finalization, frontier.ready
        publisher = self._draft_pull_request_publisher
        if (
            publisher is None
            or finalization is None
            or ready is None
            or frontier.change_disposition is not None
            or resolve_publication_phase(frontier) is not WorkItemPublicationPhase.AWAITING_MERGE
        ):
            return None
        observation = snapshot.publication_observation
        if observation is None:
            return MergeDecision(reason="provider-unavailable")
        # Mergeability lives on the receipt; the persisted snapshot excludes it.
        pull_request = observation.snapshot.model_copy(
            update={"mergeable": observation.mergeable, "merge_state_status": observation.merge_state_status}
        )
        if pull_request.merged or pull_request.state != "open" or pull_request.head_sha != finalization.exact_head:
            return None
        sync = frontier.target_sync_receipt
        authority = MergeOfferAuthority(
            repository=ready.repository,
            number=ready.number,
            node_id=ready.node_id,
            target_branch=publisher.target_branch,
            exact_head=finalization.exact_head,
            finalization_id=finalization.finalization_id,
            ready_receipt_id=ready.receipt_id,
            observation_count=len(finalization.observations),
            review_id=finalization.review.review_id,
            proof_target=sync.target_head if sync is not None else None,
        )
        return decide_merge(authority, pull_request, snapshot.merge_facts)

    @classmethod
    def _with_merge_readiness(
        cls,
        snapshot: DeliveryPortfolioSnapshot,
        card: WorkItemCardView,
        decision: DeliveryReadiness,
        merge: MergeDecision | None,
        workspace_reason: str | None,
    ) -> DeliveryReadiness:
        """L2: an open awaiting-merge PR shows its real wait, block, offer or strict-proof sync route."""
        if (
            merge is None
            or card.scope is not WorkItemScope.CHANGE_PUBLICATION
            or decision.reason_code != "request-action"
            or decision.operation is not WorkItemActionKind.OBSERVE_ACCEPTANCE
        ):
            return decision
        if merge.reason == "target-sync-required" and workspace_reason == "target-sync-required":
            action = WorkItemAction(kind=WorkItemActionKind.SYNC_TARGET, label="Synchronize target")
            updates: dict[str, object] = {
                "status": "ready",
                "operation": WorkItemActionKind.SYNC_TARGET,
                "executable": True,
                "action": action,
                "next_actor": WorkItemNextActor.AGENT,
                "reason_code": "target-sync-required",
            }
        elif merge.reason == "target-sync-required":
            updates = {
                "status": "blocked",
                "operation": None,
                "executable": False,
                "action": None,
                "next_actor": WorkItemNextActor.AGENT,
                "reason_code": workspace_reason or "target-sync-required",
            }
        else:
            updates = {
                "status": "blocked" if merge.reason == "merge-blocked" else "waiting",
                "operation": None,
                "executable": False,
                "action": None,
                "next_actor": (
                    WorkItemNextActor.YOU
                    if merge.reason in {"merge-approval-required", "merge-blocked"}
                    else WorkItemNextActor.NONE
                ),
                "reason_code": merge.reason,
                "merge_offer": merge.offer,
                "merge_block": merge.block,
            }
        updated = decision.model_copy(update=updates)
        return updated.model_copy(
            update={"prompt": cls._readiness_prompt(snapshot, card, updated.reason_code, executable=updated.executable)}
        )

    def _publication_observation(
        self,
        change_id: str,
        frontier: DeliveryFrontier,
    ) -> PublicationPullRequestObservationReceipt | None:
        publisher = self._draft_pull_request_publisher
        history = frontier.change_publication_history
        published_head = frontier.published_head
        if publisher is None or history is None or published_head is None or history.current.head_sha != published_head:
            return None
        now = time.monotonic()
        cached = self._publication_observation_cache.get(change_id)
        if cached is not None and cached[0] > now and cached[1] == published_head:
            return cached[2]
        try:
            observation = publisher.observe_pull_request(ObserveChangePublicationPullRequest(change_id=change_id))
        except OSError, PublicationProviderError, RuntimeError, subprocess.SubprocessError, ValueError:
            observation = None
        if isinstance(observation, PublicationPullRequestObservationReceipt):
            snapshot = observation.snapshot
            publication = history.current
            if (
                observation.change_id != change_id
                or snapshot.repository != publication.repository
                or snapshot.number != publication.number
                or snapshot.node_id != publication.node_id
                or snapshot.head_sha != published_head
            ):
                observation = None
        else:
            observation = None
        self._publication_observation_cache[change_id] = (
            now + _PUBLICATION_OBSERVATION_CACHE_SECONDS,
            published_head,
            observation,
        )
        return observation

    def _retained_change_worktree_view(
        self,
        retained: RetainedChangeWorktree,
    ) -> DeliveryRetainedChangeWorktree:
        runtime = self._runtimes.get(retained.change_id)
        lifecycle: DeliveryChangeStage | None = None
        completion: CompletionReceipt | None = None
        completion_state_inconsistent = False
        if runtime is not None:
            try:
                lifecycle = runtime.change_stage()
            except OSError, ValueError, DeliveryRuntimeConflictError:
                completion_state_inconsistent = True
            if not completion_state_inconsistent:
                try:
                    completion = runtime.completion_receipt()
                except OSError, ValueError, DeliveryRuntimeConflictError:
                    completion_state_inconsistent = True
        reason = self._retained_cleanup_block_reason(
            retained,
            runtime,
            lifecycle,
            completion,
            completion_state_inconsistent=completion_state_inconsistent,
        )
        return DeliveryRetainedChangeWorktree(
            change_id=retained.change_id,
            worktree_path=retained.worktree_path,
            branch=retained.branch,
            branch_head=retained.branch_head,
            recovery_reviewed_head=retained.last_reviewed_commit,
            coordination_registered=retained.coordination_registered,
            git_registered=retained.git_registered,
            worktree_present=retained.worktree_present,
            worktree_head=retained.worktree_head,
            worktree_branch=retained.worktree_branch,
            worktree_locked=retained.worktree_locked,
            worktree_prunable=retained.worktree_prunable,
            worktree_bare=retained.worktree_bare,
            attention=retained.attention,
            lifecycle=lifecycle,
            orphan=runtime is None,
            cleanup_eligible=reason is None,
            cleanup_blocked_reason=reason,
        )

    def _retained_cleanup_block_reason(
        self,
        retained: RetainedChangeWorktree,
        runtime: DeliveryRuntime | None,
        lifecycle: DeliveryChangeStage | None,
        completion: CompletionReceipt | None,
        *,
        completion_state_inconsistent: bool,
    ) -> DeliveryRetainedWorktreeCleanupBlockReason | None:
        reason: DeliveryRetainedWorktreeCleanupBlockReason | None = None
        if runtime is None:
            reason = DeliveryRetainedWorktreeCleanupBlockReason.ORPHAN
        elif completion_state_inconsistent:
            reason = DeliveryRetainedWorktreeCleanupBlockReason.COMPLETION_STATE_INCONSISTENT
        elif completion is None and lifecycle != DeliveryChangeStage.ABANDONED:
            reason = DeliveryRetainedWorktreeCleanupBlockReason.NONTERMINAL
        elif retained.writer is not None:
            reason = DeliveryRetainedWorktreeCleanupBlockReason.ACTIVE_WRITER
        elif retained.publication_expiry is not None and retained.publication_expiry > _timestamp(self._clock()):
            reason = DeliveryRetainedWorktreeCleanupBlockReason.ACTIVE_PUBLICATION_LEASE
        elif retained.attention:
            reason = DeliveryRetainedWorktreeCleanupBlockReason.WORKTREE_ATTENTION
        return reason

    @staticmethod
    def _snapshot_change_stage(snapshot: DeliveryPortfolioSnapshot) -> DeliveryChangeStage:
        return derive_change_stage(snapshot.frontier)

    @staticmethod
    def _is_work_portfolio_visible(snapshot: DeliveryPortfolioSnapshot) -> bool:
        return snapshot.frontier.change_abandonment is None and not is_change_terminal(snapshot.frontier)

    @staticmethod
    def _snapshot_has_active_claims(snapshot: DeliveryPortfolioSnapshot) -> bool:
        return any(binding.active_claim is not None for binding in snapshot.frontier.bindings)

    @staticmethod
    def _snapshot_dependency_depth(snapshot: DeliveryPortfolioSnapshot, outcome_id: str) -> int:
        dependencies = {outcome.outcome_id: outcome.dependency_ids for outcome in snapshot.contract.outcomes}

        def depth(current: str) -> int:
            return 0 if not dependencies[current] else 1 + max(depth(item) for item in dependencies[current])

        return depth(outcome_id)
