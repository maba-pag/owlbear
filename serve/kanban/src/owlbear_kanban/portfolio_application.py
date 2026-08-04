"""Deterministic portfolio acquisition and bounded worker context."""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Never

from pydantic import BaseModel, ConfigDict, Field, model_validator

from owlbear_kanban.change_workspace import (
    ChangeCoordination,
    ChangeWorkspaceManager,
    ChangeWriter,
    CoordinationConflictError,
    PortfolioCoordinator,
    WorkspaceRecoverySnapshot,
)
from owlbear_kanban.delivery_runtime import (
    ActivateDeliveryClaim,
    DeliveryActiveClaim,
    DeliveryChangeStage,
    DeliveryRecoveryAttention,
    DeliveryRequest,
    DeliveryReturnContext,
    DeliveryRuntime,
    DeliveryStage,
    DeliveryTaskDefinition,
    DeliveryTaskResult,
    DeliveryWorkerRole,
    OutcomeAuthorityBinding,
)
from owlbear_kanban.target_contract import DeliveryCommitment, DeliveryOutcome

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from owlbear_kanban.design_package import DesignPackageStore, VerifiedDesignPackage


class _ApplicationModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class DeliveryRolePolicy(_ApplicationModel):
    """Configured worker and reviewer policy for one mechanical stage role."""

    worker_role: DeliveryWorkerRole
    worker_agent: str = Field(min_length=1)
    worker_model: str = Field(min_length=1)
    reviewer_agent: str | None = None
    reviewer_model: str | None = None

    @model_validator(mode="after")
    def _validate_reviewer_policy(self) -> DeliveryRolePolicy:
        if (self.reviewer_agent is None) != (self.reviewer_model is None):
            message = "reviewer agent and model policy must be supplied together"
            raise ValueError(message)
        return self


class DeliveryLaunchPackage(_ApplicationModel):
    """Bounded identity and source locators for one named worker invocation."""

    change_id: str = Field(min_length=1)
    authority_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    plan_scope_id: str = Field(pattern=r"^SCOPE-[0-9]{3}$")
    task_id: str | None = None
    claim: DeliveryActiveClaim
    policy: DeliveryRolePolicy
    package_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    package_root: Path
    worktree_path: Path
    branch: str = Field(min_length=1)
    source_head: str = Field(pattern=r"^[0-9a-f]{40}$")
    integration_target: str = Field(min_length=1)
    last_reviewed_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    writer: ChangeWriter | None = None

    @model_validator(mode="after")
    def _validate_role_custody(self) -> DeliveryLaunchPackage:
        if self.policy.worker_role != self.claim.worker_role or self.task_id != self.claim.task_id:
            message = "launch policy and task identity must match the active claim"
            raise ValueError(message)
        if (self.claim.worker_role == DeliveryWorkerRole.BUILDER) != (self.writer is not None):
            message = "only Build launch packages carry writer custody"
            raise ValueError(message)
        if self.writer is not None and (
            self.writer.attempt_id != self.claim.attempt_id
            or self.writer.claim_id != self.claim.claim_id
            or self.writer.actor_id != self.claim.owner_id
            or self.writer.process_id != self.claim.process_id
        ):
            message = "writer custody must match the active claim"
            raise ValueError(message)
        return self


class DeliveryAcquisitionFailure(_ApplicationModel):
    """Bounded fail-closed preparation result, optionally tied to a started claim."""

    change_id: str = Field(min_length=1)
    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    attempt_id: str | None = None
    claim_id: str | None = None
    code: str = Field(min_length=1)
    detail: str = Field(min_length=1)
    retry_condition: str = Field(min_length=1)


class DeliveryAcquisitionResult(_ApplicationModel):
    """Launchable claims and unclaimed Integration-ready changes from one refresh."""

    launch_packages: tuple[DeliveryLaunchPackage, ...]
    integration_ready_change_ids: tuple[str, ...]
    failures: tuple[DeliveryAcquisitionFailure, ...] = ()


class DeliveryPlanContext(_ApplicationModel):
    """Plan authority and current same-outcome successor context."""

    launch: DeliveryLaunchPackage
    outcome: DeliveryOutcome
    commitments: tuple[DeliveryCommitment, ...]
    requests: tuple[DeliveryRequest, ...]
    return_context: DeliveryReturnContext | None = None


class DeliveryBuildContext(_ApplicationModel):
    """Build authority, predecessor results, and current source coordination."""

    launch: DeliveryLaunchPackage
    task: DeliveryTaskDefinition
    commitments: tuple[DeliveryCommitment, ...]
    predecessor_results: tuple[DeliveryTaskResult, ...]
    requests: tuple[DeliveryRequest, ...]
    return_context: DeliveryReturnContext | None = None
    recovery_attention: DeliveryRecoveryAttention | None = None


class DeliveryClaimRecoveryStatus(StrEnum):
    """Observable disposition of one exact-claim recovery request."""

    RECOVERED = "recovered"
    ATTENTION = "attention"


class DeliveryClaimRecoveryResult(_ApplicationModel):
    """Recovered claim state or retained typed repair attention."""

    status: DeliveryClaimRecoveryStatus
    change_id: str = Field(min_length=1)
    outcome_id: str = Field(pattern=r"^OUT-[0-9]{3}$")
    attempt_id: str = Field(min_length=1)
    claim_id: str = Field(min_length=1)
    preserved_commit: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    preserved_ref: str | None = None
    attention: DeliveryRecoveryAttention | None = None

    @model_validator(mode="after")
    def _validate_disposition(self) -> DeliveryClaimRecoveryResult:
        if (self.status == DeliveryClaimRecoveryStatus.ATTENTION) != (self.attention is not None):
            message = "only retained recovery requires repair attention"
            raise ValueError(message)
        return self


class PortfolioApplicationError(RuntimeError):
    """Portfolio preparation or scoped context validation failed closed."""

    code = "ERR_DELIVERY_PORTFOLIO"


class PortfolioApplicationConfig(_ApplicationModel):
    """Configured capacity, source root, and complete stage-role policy."""

    package_root: Path
    execution_capacity: int = Field(gt=0)
    role_policies: tuple[DeliveryRolePolicy, ...] = Field(min_length=3, max_length=3)

    @model_validator(mode="after")
    def _validate_roles(self) -> PortfolioApplicationConfig:
        roles = tuple(policy.worker_role for policy in self.role_policies)
        if set(roles) != set(DeliveryWorkerRole) or len(roles) != len(set(roles)):
            message = "role policy must define each worker role once"
            raise ValueError(message)
        return self


@dataclass(frozen=True)
class PortfolioApplicationDependencies:
    """Existing state owners composed by the portfolio application service."""

    package_store: DesignPackageStore
    coordinator: PortfolioCoordinator
    workspace_manager: ChangeWorkspaceManager


@dataclass(frozen=True)
class PortfolioApplicationHooks:
    """Nondeterministic identity and clock sources replaced only below public proof."""

    identity_factory: Callable[[], str]
    clock: Callable[[], str]


@dataclass(frozen=True)
class _Candidate:
    sort_key: tuple[int, int, int, str]
    change_id: str
    runtime: DeliveryRuntime
    binding: OutcomeAuthorityBinding
    task_id: str | None
    role: DeliveryWorkerRole


@dataclass(frozen=True)
class _PreparedSource:
    package: VerifiedDesignPackage
    coordination: ChangeCoordination
    source_head: str


class PortfolioApplication:
    """Compose Delivery runtimes, source packages, and warm workspace custody."""

    def __init__(
        self,
        runtimes: Mapping[str, DeliveryRuntime],
        dependencies: PortfolioApplicationDependencies,
        config: PortfolioApplicationConfig,
        hooks: PortfolioApplicationHooks | None = None,
    ) -> None:
        if set(runtimes) != {runtime.contract.change_id for runtime in runtimes.values()}:
            message = "runtime mapping keys must match admitted change identities"
            raise ValueError(message)
        self._runtimes = dict(runtimes)
        self._package_store = dependencies.package_store
        self._package_root = config.package_root.resolve()
        self._coordinator = dependencies.coordinator
        self._workspace_manager = dependencies.workspace_manager
        self._execution_capacity = config.execution_capacity
        self._policies = {policy.worker_role: policy for policy in config.role_policies}
        self._identity_factory = hooks.identity_factory if hooks else lambda: str(uuid.uuid4())
        self._clock = (
            hooks.clock
            if hooks
            else lambda: datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        )

    def acquire_frontier_work(self) -> DeliveryAcquisitionResult:
        """Start stable ready claims and reserve writer custody only for Build."""
        with self._coordinator.acquisition_lock():
            integration_ready = tuple(
                change_id
                for change_id, runtime in sorted(self._runtimes.items())
                if runtime.change_stage() == DeliveryChangeStage.INTEGRATION
            )
            occupied = sum(len(runtime.active_claims()) for runtime in self._runtimes.values())
            available = max(self._execution_capacity - occupied, 0)
            launches: list[DeliveryLaunchPackage] = []
            failures: list[DeliveryAcquisitionFailure] = []
            for candidate in self._candidates():
                if available == 0:
                    break
                if candidate.role == DeliveryWorkerRole.BUILDER and not self._coordinator.writer_capacity_available():
                    continue
                source = self._prepare_source(
                    candidate.change_id,
                    candidate.runtime,
                    candidate.binding.outcome_id,
                )
                if isinstance(source, DeliveryAcquisitionFailure):
                    failures.append(source)
                    continue
                coordination = source.coordination
                claim = self._new_claim(candidate.role, candidate.task_id)
                candidate.runtime.activate_claim(
                    ActivateDeliveryClaim(outcome_id=candidate.binding.outcome_id, claim=claim)
                )
                available -= 1
                writer = None
                if candidate.role == DeliveryWorkerRole.BUILDER:
                    try:
                        coordination = self._coordinator.acquire(
                            candidate.change_id,
                            ChangeWriter(
                                attempt_id=claim.attempt_id,
                                claim_id=claim.claim_id,
                                actor_id=claim.owner_id,
                                process_id=claim.process_id,
                                claimed_at=claim.started_at,
                                job_id=1,
                                kind="build",
                            ),
                        )
                    except CoordinationConflictError as exc:
                        failures.append(
                            DeliveryAcquisitionFailure(
                                change_id=candidate.change_id,
                                outcome_id=candidate.binding.outcome_id,
                                attempt_id=claim.attempt_id,
                                claim_id=claim.claim_id,
                                code=exc.code,
                                detail=str(exc),
                                retry_condition="Remove the exact failed claim after reconciling writer custody.",
                            )
                        )
                        continue
                    writer = coordination.writer
                launches.append(self._launch_package(candidate, claim, source, writer))
            return DeliveryAcquisitionResult(
                launch_packages=tuple(launches),
                integration_ready_change_ids=integration_ready,
                failures=tuple(failures),
            )

    def show_plan_context(
        self,
        change_id: str,
        outcome_id: str,
        attempt_id: str,
        claim_id: str,
    ) -> DeliveryPlanContext:
        """Project exact same-outcome Planning authority for one active claim."""
        runtime = self._runtime(change_id)
        binding = runtime.require_active_claim(outcome_id, attempt_id, claim_id)
        if binding.stage != DeliveryStage.PLANNING:
            self._fail("active claim is not Planning work")
        launch = self._current_launch(change_id, runtime, binding)
        outcome = self._outcome(runtime, outcome_id)
        return DeliveryPlanContext(
            launch=launch,
            outcome=outcome,
            commitments=self._commitments(runtime, outcome.commitment_ids),
            requests=binding.requests,
            return_context=binding.return_context,
        )

    def show_build_context(
        self,
        change_id: str,
        outcome_id: str,
        attempt_id: str,
        claim_id: str,
    ) -> DeliveryBuildContext:
        """Project exact task and predecessor authority for one active Build claim."""
        runtime = self._runtime(change_id)
        binding = runtime.require_active_claim(outcome_id, attempt_id, claim_id)
        if binding.stage != DeliveryStage.IMPLEMENTATION or binding.active_task_id is None:
            self._fail("active claim is not Build work")
        launch = self._current_launch(change_id, runtime, binding)
        task = next(item for item in binding.tasks if item.task_id == binding.active_task_id)
        predecessor_task_ids = set(task.dependency_ids)
        outcome = self._outcome(runtime, outcome_id)
        dependency_outcomes = set(outcome.dependency_ids)
        predecessor_results = tuple(
            result
            for candidate in runtime.contract.outcomes
            for result in runtime.show_binding(candidate.outcome_id).results
            if result.task_id in predecessor_task_ids or candidate.outcome_id in dependency_outcomes
        )
        return DeliveryBuildContext(
            launch=launch,
            task=task,
            commitments=self._commitments(runtime, task.commitment_ids),
            predecessor_results=predecessor_results,
            requests=binding.requests,
            return_context=binding.return_context,
            recovery_attention=binding.recovery_attention,
        )

    def recover_claim(
        self,
        change_id: str,
        outcome_id: str,
        attempt_id: str,
        claim_id: str,
    ) -> DeliveryClaimRecoveryResult:
        """Remove one exact failed claim or retain deterministic Build repair attention."""
        with self._coordinator.acquisition_lock():
            runtime = self._runtime(change_id)
            binding = runtime.require_active_claim(outcome_id, attempt_id, claim_id)
            claim = binding.active_claim
            if claim is None:
                self._fail("outcome has no active claim")
            if claim.worker_role != DeliveryWorkerRole.BUILDER:
                runtime.remove_active_claim(outcome_id, attempt_id, claim_id)
                return self._recovered(change_id, outcome_id, attempt_id, claim_id)
            snapshot = self._workspace_manager.recovery_snapshot(change_id, attempt_id)
            if snapshot.writer is None:
                if self._released_recovery_matches(snapshot):
                    runtime.remove_active_claim(outcome_id, attempt_id, claim_id)
                    return self._recovered(
                        change_id,
                        outcome_id,
                        attempt_id,
                        claim_id,
                        snapshot.preserved_commit,
                    )
                return self._retain_recovery_attention(runtime, outcome_id, claim, snapshot)
            if not self._active_recovery_matches(snapshot, attempt_id, claim_id):
                return self._retain_recovery_attention(runtime, outcome_id, claim, snapshot)
            rejected_head = snapshot.branch_head
            self._workspace_manager.restart(change_id, attempt_id, rejected_head)
            runtime.remove_active_claim(outcome_id, attempt_id, claim_id)
            return self._recovered(
                change_id,
                outcome_id,
                attempt_id,
                claim_id,
                rejected_head,
            )

    def _candidates(self) -> tuple[_Candidate, ...]:
        candidates = []
        for change_id, runtime in self._runtimes.items():
            if runtime.active_claims() or runtime.change_stage() != DeliveryChangeStage.ACTIVE_DELIVERY:
                continue
            claimable = set(runtime.claimable_outcome_ids())
            ranked = []
            for outcome_index, outcome in enumerate(runtime.contract.outcomes):
                if outcome.outcome_id not in claimable:
                    continue
                binding = runtime.show_binding(outcome.outcome_id)
                task_id = None
                task_index = 0
                if binding.stage == DeliveryStage.IMPLEMENTATION:
                    task_ids = runtime.claimable_task_ids(outcome.outcome_id)
                    if not task_ids:
                        continue
                    task_id = task_ids[0]
                    task_index = binding.task_ids.index(task_id)
                role = {
                    DeliveryStage.PLANNING: DeliveryWorkerRole.PLANNER,
                    DeliveryStage.IMPLEMENTATION: DeliveryWorkerRole.BUILDER,
                    DeliveryStage.ASSEMBLY: DeliveryWorkerRole.ASSEMBLY_REVIEWER,
                }[binding.stage]
                ranked.append(
                    _Candidate(
                        sort_key=(
                            self._dependency_depth(runtime, outcome.outcome_id),
                            outcome_index,
                            task_index,
                            change_id,
                        ),
                        change_id=change_id,
                        runtime=runtime,
                        binding=binding,
                        task_id=task_id,
                        role=role,
                    )
                )
            if ranked:
                candidates.append(min(ranked, key=lambda item: item.sort_key))
        return tuple(sorted(candidates, key=lambda item: item.sort_key))

    def _prepare_source(
        self,
        change_id: str,
        runtime: DeliveryRuntime,
        outcome_id: str,
    ) -> _PreparedSource | DeliveryAcquisitionFailure:
        try:
            package = self._package_store.read_verified(change_id)
            self._validate_package_authority(runtime, package)
            coordination = self._workspace_manager.show(change_id)
            source_head = self._workspace_manager.reviewed_source_head(change_id)
        except (OSError, RuntimeError, ValueError) as exc:
            return DeliveryAcquisitionFailure(
                change_id=change_id,
                outcome_id=outcome_id,
                code=getattr(exc, "code", PortfolioApplicationError.code),
                detail=str(exc),
                retry_condition="Restore the admitted package and clean reviewed source boundary.",
            )
        return _PreparedSource(package, coordination, source_head)

    def _current_launch(
        self,
        change_id: str,
        runtime: DeliveryRuntime,
        binding: OutcomeAuthorityBinding,
    ) -> DeliveryLaunchPackage:
        source = self._prepare_source(change_id, runtime, binding.outcome_id)
        if isinstance(source, DeliveryAcquisitionFailure):
            self._fail(source.detail)
        claim = binding.active_claim
        if claim is None:
            self._fail("outcome has no active claim")
        writer = source.coordination.writer if claim.worker_role == DeliveryWorkerRole.BUILDER else None
        candidate = _Candidate((0, 0, 0, change_id), change_id, runtime, binding, claim.task_id, claim.worker_role)
        return self._launch_package(candidate, claim, source, writer)

    def _launch_package(
        self,
        candidate: _Candidate,
        claim: DeliveryActiveClaim,
        source: _PreparedSource,
        writer: ChangeWriter | None,
    ) -> DeliveryLaunchPackage:
        return DeliveryLaunchPackage(
            change_id=candidate.change_id,
            authority_digest=candidate.runtime.authority_digest,
            outcome_id=candidate.binding.outcome_id,
            plan_scope_id=candidate.binding.plan_scope_id,
            task_id=candidate.task_id,
            claim=claim,
            policy=self._policies[candidate.role],
            package_id=source.package.package_id,
            package_root=self._package_root / candidate.change_id,
            worktree_path=source.coordination.worktree_path,
            branch=source.coordination.branch,
            source_head=source.source_head,
            integration_target=source.coordination.integration_target,
            last_reviewed_commit=source.coordination.last_reviewed_commit,
            writer=writer,
        )

    def _new_claim(self, role: DeliveryWorkerRole, task_id: str | None) -> DeliveryActiveClaim:
        return DeliveryActiveClaim(
            attempt_id=self._identity_factory(),
            claim_id=self._identity_factory(),
            owner_id=self._identity_factory(),
            process_id=self._identity_factory(),
            started_at=self._clock(),
            worker_role=role,
            task_id=task_id,
        )

    @staticmethod
    def _released_recovery_matches(snapshot: WorkspaceRecoverySnapshot) -> bool:
        return (
            snapshot.clean
            and snapshot.branch_head == snapshot.last_reviewed_commit
            and snapshot.worktree_head == snapshot.last_reviewed_commit
            and snapshot.worktree_branch == snapshot.branch
        )

    @staticmethod
    def _active_recovery_matches(
        snapshot: WorkspaceRecoverySnapshot,
        attempt_id: str,
        claim_id: str,
    ) -> bool:
        writer = snapshot.writer
        return (
            writer is not None
            and writer.attempt_id == attempt_id
            and writer.claim_id == claim_id
            and snapshot.clean
            and snapshot.worktree_head == snapshot.branch_head
            and snapshot.worktree_branch == snapshot.branch
            and snapshot.reviewed_ancestor
            and snapshot.preserved_commit in {None, snapshot.branch_head}
        )

    def _retain_recovery_attention(
        self,
        runtime: DeliveryRuntime,
        outcome_id: str,
        claim: DeliveryActiveClaim,
        snapshot: WorkspaceRecoverySnapshot,
    ) -> DeliveryClaimRecoveryResult:
        attention = DeliveryRecoveryAttention(
            attempt_id=claim.attempt_id,
            claim_id=claim.claim_id,
            reason=self._recovery_reason(snapshot, claim),
            worktree_path=str(snapshot.worktree_path),
            branch_head=snapshot.branch_head,
            worktree_head=snapshot.worktree_head,
            last_reviewed_commit=snapshot.last_reviewed_commit,
            writer_claim_id=snapshot.writer.claim_id if snapshot.writer is not None else None,
            custody_retained=snapshot.writer is not None,
            retry_condition="Restore a clean recorded worktree and reconcile exact writer custody.",
        )
        runtime.publish_recovery_attention(outcome_id, attention)
        return DeliveryClaimRecoveryResult(
            status=DeliveryClaimRecoveryStatus.ATTENTION,
            change_id=runtime.contract.change_id,
            outcome_id=outcome_id,
            attempt_id=claim.attempt_id,
            claim_id=claim.claim_id,
            attention=attention,
        )

    @staticmethod
    def _recovery_reason(snapshot: WorkspaceRecoverySnapshot, claim: DeliveryActiveClaim) -> str:
        writer = snapshot.writer
        if writer is None:
            return "Build source is outside the reviewed boundary without writer custody."
        if writer.attempt_id != claim.attempt_id or writer.claim_id != claim.claim_id:
            return "Build claim does not match recorded writer custody."
        if not snapshot.clean:
            return "Build worktree contains uncommitted changes."
        if snapshot.worktree_branch != snapshot.branch or snapshot.worktree_head != snapshot.branch_head:
            return "Build worktree does not match its recorded branch head."
        if not snapshot.reviewed_ancestor:
            return "Build branch does not descend from its reviewed boundary."
        return "Build attempt history ref conflicts with the current branch head."

    @staticmethod
    def _recovered(
        change_id: str,
        outcome_id: str,
        attempt_id: str,
        claim_id: str,
        preserved_commit: str | None = None,
    ) -> DeliveryClaimRecoveryResult:
        return DeliveryClaimRecoveryResult(
            status=DeliveryClaimRecoveryStatus.RECOVERED,
            change_id=change_id,
            outcome_id=outcome_id,
            attempt_id=attempt_id,
            claim_id=claim_id,
            preserved_commit=preserved_commit,
            preserved_ref=(f"refs/owlbear/attempts/{change_id}/{attempt_id}" if preserved_commit is not None else None),
        )

    def _validate_package_authority(self, runtime: DeliveryRuntime, package: VerifiedDesignPackage) -> None:
        if hashlib.sha256(package.authority_bytes).hexdigest() != runtime.authority_digest:
            self._fail("active package authority does not match the Delivery runtime")
        source_digests = {binding.source_name: binding.sha256 for binding in runtime.contract.source_bindings}
        if source_digests != {
            "intent.md": package.manifest.intent_sha256,
            "design.md": package.manifest.design_sha256,
        }:
            self._fail("active package sources do not match admitted Delivery bindings")

    def _dependency_depth(self, runtime: DeliveryRuntime, outcome_id: str) -> int:
        dependencies = {outcome.outcome_id: outcome.dependency_ids for outcome in runtime.contract.outcomes}

        def depth(current: str) -> int:
            return 0 if not dependencies[current] else 1 + max(depth(item) for item in dependencies[current])

        return depth(outcome_id)

    def _runtime(self, change_id: str) -> DeliveryRuntime:
        try:
            return self._runtimes[change_id]
        except KeyError as exc:
            self._fail(f"Delivery runtime is absent: {change_id}", exc)

    @staticmethod
    def _outcome(runtime: DeliveryRuntime, outcome_id: str) -> DeliveryOutcome:
        return next(item for item in runtime.contract.outcomes if item.outcome_id == outcome_id)

    @staticmethod
    def _commitments(runtime: DeliveryRuntime, commitment_ids: tuple[str, ...]) -> tuple[DeliveryCommitment, ...]:
        selected = set(commitment_ids)
        return tuple(item for item in runtime.contract.commitments if item.commitment_id in selected)

    @staticmethod
    def _fail(message: str, cause: Exception | None = None) -> Never:
        raise PortfolioApplicationError(message) from cause


__all__ = [
    "DeliveryAcquisitionFailure",
    "DeliveryAcquisitionResult",
    "DeliveryBuildContext",
    "DeliveryClaimRecoveryResult",
    "DeliveryClaimRecoveryStatus",
    "DeliveryLaunchPackage",
    "DeliveryPlanContext",
    "DeliveryRolePolicy",
    "PortfolioApplication",
    "PortfolioApplicationConfig",
    "PortfolioApplicationDependencies",
    "PortfolioApplicationError",
    "PortfolioApplicationHooks",
]
