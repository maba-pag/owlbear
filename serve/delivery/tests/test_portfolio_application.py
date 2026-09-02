# ruff: noqa: SLF001

from __future__ import annotations

import hashlib
import itertools
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Event
from typing import Literal
from unittest.mock import Mock, patch, sentinel

import pytest

from owlbear_delivery import (
    ActivateDeliveryClaim,
    AdministrativeDeliveryMove,
    AdvanceDelivery,
    BlockDelivery,
    CapacityLedger,
    ChangeBranchPublicationReceipt,
    ChangeBranchPublisher,
    ChangeBranchSupersessionReceipt,
    ChangeExternalHeadAdoptionReceipt,
    ChangeTargetSyncAbortReceipt,
    ChangeTargetSyncConflictError,
    ChangeTargetSyncConflictState,
    ChangeTargetSyncReceipt,
    ChangeWorkspaceManager,
    ChangeWorktreeAttentionCode,
    ChangeWorktreeAttentionError,
    ChangeWriter,
    CompletedHistoryCatalog,
    CompletionReceipt,
    CoordinationConflictError,
    CreateOrReconcileDraftPullRequest,
    DeliveryAcceptanceAttentionReason,
    DeliveryAcceptanceWaitingError,
    DeliveryActiveClaim,
    DeliveryAdmissionConflictError,
    DeliveryAdmissionReceipt,
    DeliveryAdmissionRequest,
    DeliveryApplicationLoadError,
    DeliveryAuthorityRegistry,
    DeliveryBlock,
    DeliveryChangeDispositionBusyError,
    DeliveryChangePublicationIdentity,
    DeliveryChangeStage,
    DeliveryChangeWorktreeCleanup,
    DeliveryChangeWorktreeRecovery,
    DeliveryCheckpointPublicationState,
    DeliveryCheckpointTrigger,
    DeliveryCheckpointTriggerKind,
    DeliveryClaimRecoveryStatus,
    DeliveryCommitment,
    DeliveryCommitmentClass,
    DeliveryContract,
    DeliveryFinalizationInvalidationReceipt,
    DeliveryFinalizationReceipt,
    DeliveryFrontier,
    DeliveryHostConfig,
    DeliveryIntegrationAttention,
    DeliveryIntegrationAttentionCode,
    DeliveryObservation,
    DeliveryObservationReceipt,
    DeliveryOutcome,
    DeliveryPendingCheckpoint,
    DeliveryPlanScope,
    DeliveryRequest,
    DeliveryRequestKind,
    DeliveryRequestOption,
    DeliveryRequestResolution,
    DeliveryRetainedWorktreeCleanupBlockReason,
    DeliveryReview,
    DeliveryReviewReceipt,
    DeliveryRolePolicy,
    DeliveryRuntime,
    DeliveryRuntimeConflictError,
    DeliveryRuntimeMigrationError,
    DeliveryStage,
    DeliveryStartupConfig,
    DeliveryTaskDefinition,
    DeliveryTaskResult,
    DeliveryWorkerRole,
    DesignPackageConflictError,
    DesignPackageManifest,
    DesignPackageStore,
    DraftPullRequestPublicationHistory,
    DraftPullRequestPublicationReceipt,
    DraftPullRequestPublisher,
    DraftPullRequestSupersessionReceipt,
    FinalizeDeliveryChange,
    GeneratedPullRequestSummaryReceipt,
    MarkChangePullRequestReady,
    ObserveChangePublicationChecks,
    ObserveChangePublicationPullRequest,
    OutcomeAuthorityBinding,
    PortfolioApplication,
    PortfolioApplicationConfig,
    PortfolioApplicationDependencies,
    PortfolioApplicationError,
    PortfolioApplicationHooks,
    PortfolioCoordinator,
    PublicationBaselineUnavailableError,
    PublicationCheck,
    PublicationCheckBlockingState,
    PublicationCheckKind,
    PublicationCheckSnapshot,
    PublicationLease,
    PublishChangeBranch,
    PublishDeliveryPlan,
    PublishDeliveryResult,
    PullRequestReadyReceipt,
    ReadChangePublicationCheckObservations,
    ReadChangePublicationHistory,
    RetryDelivery,
    WorkspaceRecoverySnapshot,
    classify_publication_check,
    load_delivery_application,
)
from owlbear_delivery.delivery_contract_discovery import (
    DeliveryDiscoveryErrorCode,
    contract_fingerprint,
    discover_persisted_changes,
)
from owlbear_delivery.portfolio_application import (
    DeliveryRuntimeReconciliationError,
    _required_check_diagnostics,
)
from owlbear_delivery.publication_provider import (
    PublicationProviderError,
    PublicationProviderFailureCode,
    PublicationPullRequest,
    PublicationRepository,
)
from owlbear_delivery.runtime_transaction import RuntimeTransaction
from owlbear_delivery.storage_io import locked_roots
from owlbear_delivery_github import GitHubCliPublicationProvider

_USER_CHECKOUT_STATES = (
    "clean",
    "modified",
    "staged",
    "untracked",
    "conflicted",
    "detached",
    "mid-merge",
    "mid-rebase",
)


def _git(repository: Path, *arguments: str) -> str:
    return subprocess.run(  # noqa: S603
        ("git", "-C", str(repository), *arguments),  # noqa: S607
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _git_ref_exists(repository: Path, reference: str) -> bool:
    return (
        subprocess.run(  # noqa: S603
            ("git", "-C", str(repository), "rev-parse", "--verify", reference),  # noqa: S607
            check=False,
            capture_output=True,
        ).returncode
        == 0
    )


def _commit_reviewed_head(application, coordination, filename: str, content: str, message: str) -> str:
    (coordination.worktree_path / filename).write_text(content, encoding="utf-8")
    _git(coordination.worktree_path, "add", filename)
    _git(coordination.worktree_path, "commit", "-m", message)
    head = _git(coordination.worktree_path, "rev-parse", "HEAD")
    application._workspace_manager.record_reviewed("change-a", head)
    return head


def _commit_local_descendant(coordination, filename: str = "local-repair.txt") -> str:
    (coordination.worktree_path / filename).write_text("local repair\n", encoding="utf-8")
    _git(coordination.worktree_path, "add", filename)
    _git(coordination.worktree_path, "commit", "-m", "local repair")
    return _git(coordination.worktree_path, "rev-parse", "HEAD")


def _canonical(model) -> bytes:
    return (json.dumps(model.model_dump(mode="json"), sort_keys=True, separators=(",", ":")) + "\n").encode()


def _receipt_id(payload: dict[str, object]) -> str:
    content = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(content.encode()).hexdigest()


def _branch_receipt(head: str, expected: str | None = None) -> ChangeBranchPublicationReceipt:
    return ChangeBranchPublicationReceipt(
        receipt_id="1" * 64,
        operation_id="branch-operation",
        change_id="change-a",
        remote="origin",
        branch="owlbear/change/change-a",
        target_branch="main",
        expected_remote_head=expected,
        published_head=head,
    )


def _requested_branch_receipt(request: PublishChangeBranch) -> ChangeBranchPublicationReceipt:
    assert request.expected_published_head is not None
    return _branch_receipt(request.expected_published_head, request.expected_remote_head)


def _draft_receipt(
    head: str,
    *,
    number: int = 7,
    operation_id: str = "pull-request-operation",
    head_branch: str = "owlbear/change/change-a",
) -> DraftPullRequestPublicationReceipt:
    payload = {
        "schema_version": 1,
        "operation_id": operation_id,
        "change_id": "change-a",
        "repository": "example/project",
        "number": number,
        "node_id": f"PR_{number}",
        "head_branch": head_branch,
        "head_sha": head,
        "base_branch": "main",
        "provider_evidence_digest": "2" * 64,
    }
    return DraftPullRequestPublicationReceipt(receipt_id=_receipt_id(payload), **payload)


def _draft_history(
    publications: tuple[DraftPullRequestPublicationReceipt, ...],
    predecessor_receipt_ids: tuple[str | None, ...],
) -> DraftPullRequestPublicationHistory:
    payload = {
        "schema_version": 1,
        "change_id": "change-a",
        "publications": tuple(publication.model_dump(mode="json") for publication in publications),
        "predecessor_receipt_ids": predecessor_receipt_ids,
        "current_receipt_id": publications[-1].receipt_id,
    }
    return DraftPullRequestPublicationHistory(
        history_id=_receipt_id(payload),
        publications=publications,
        predecessor_receipt_ids=predecessor_receipt_ids,
        current_receipt_id=publications[-1].receipt_id,
        change_id="change-a",
    )


def _summary_receipt(head: str, *, number: int = 7) -> GeneratedPullRequestSummaryReceipt:
    payload = {
        "schema_version": 1,
        "operation_id": "summary-operation",
        "change_id": "change-a",
        "repository": "example/project",
        "number": number,
        "head_sha": head,
        "body_digest": "3" * 64,
        "provider_evidence_digest": "4" * 64,
    }
    return GeneratedPullRequestSummaryReceipt(receipt_id=_receipt_id(payload), **payload)


def _contract(change_id: str, intent: bytes, design: bytes) -> DeliveryContract:
    return DeliveryContract(
        change_id=change_id,
        title=f"Delivery {change_id}",
        commitments=(
            DeliveryCommitment(
                commitment_id="COM-001",
                commitment_class=DeliveryCommitmentClass.AGREED_PATH,
                provenance="accepted design",
                statement="Keep acquisition deterministic.",
            ),
        ),
        outcomes=(
            DeliveryOutcome(
                outcome_id="OUT-001",
                title="Acquire work",
                promise="Return one bounded launch package.",
                acceptance=("The launch is observable.",),
                commitment_ids=("COM-001",),
                dependency_ids=(),
            ),
        ),
        plan_scopes=(DeliveryPlanScope(scope_id="SCOPE-001", outcome_id="OUT-001"),),
        source_bindings=(
            {"source_name": "intent.md", "sha256": hashlib.sha256(intent).hexdigest()},
            {"source_name": "design.md", "sha256": hashlib.sha256(design).hexdigest()},
        ),
    )


def _admission_receipt(
    contract: DeliveryContract,
    frontier: DeliveryFrontier,
    checkpoint_commit: str,
) -> DeliveryAdmissionReceipt:
    source_bindings = [item.model_dump(mode="json") for item in contract.source_bindings]
    payload = {
        "schema_version": 1,
        "change_id": contract.change_id,
        "contract_digest": contract_fingerprint(contract),
        "source_bindings_digest": hashlib.sha256(
            json.dumps(source_bindings, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "integration_target": "main",
        "checkpoint_commit": checkpoint_commit,
        "frontier_ids": tuple(binding.plan_scope_id for binding in frontier.bindings),
    }
    return DeliveryAdmissionReceipt(receipt_id=_receipt_id(payload), **payload)


def _task() -> DeliveryTaskDefinition:
    return DeliveryTaskDefinition(
        task_id="TASK-001",
        outcome_id="OUT-001",
        plan_scope_id="SCOPE-001",
        title="Implement acquisition",
        result="One transport-free acquisition service.",
        commitment_ids=("COM-001",),
        dependency_ids=(),
        required_outputs=("Bounded launch package",),
        maintained_surfaces=("serve/delivery/src/owlbear_delivery/portfolio_application.py",),
        constraints=("Separate execution and writer capacity.",),
        exclusions=("Do not expose portfolio inventory.",),
        acceptance_observations=("The public acquisition result names the active claim.",),
        proof_boundaries=("PortfolioApplication.acquire_frontier_work",),
    )


def _task_result(
    result_id: str,
    change_id: str,
    authority_digest: str,
    task: DeliveryTaskDefinition,
    completed_commit: str,
) -> DeliveryTaskResult:
    observed_at = datetime(2026, 8, 11, 12, tzinfo=UTC)
    observation = DeliveryObservationReceipt.create(
        DeliveryObservation(
            change_id=change_id,
            task_or_finalization_id=task.task_id,
            exact_commit=completed_commit,
            observation_kind="pytest",
            command_or_procedure="PortfolioApplication fixture validation",
            exit_status_or_artifact_locator="exit:0",
            observer_or_runner_identity="pytest",
            observed_at=observed_at,
        )
    )
    review = DeliveryReviewReceipt.create(
        DeliveryReview(
            exact_commit=completed_commit,
            author_id="Portfolio test author",
            reviewer_id="Portfolio test reviewer",
            evidence=("The exact fixture commit satisfies task authority.",),
            reviewed_at=observed_at,
        )
    )
    return DeliveryTaskResult(
        result_id=result_id,
        change_id=change_id,
        authority_digest=authority_digest,
        task_id=task.task_id,
        task_digest=task.digest,
        completed_commit=completed_commit,
        observations=(observation,),
        review=review,
    )


def _finalization_request(
    change_id: str,
    exact_head: str,
) -> FinalizeDeliveryChange:
    operation_id = f"finalize-{change_id}"
    observed_at = datetime(2026, 8, 11, 13, tzinfo=UTC)
    observations = (
        DeliveryObservationReceipt.create(
            DeliveryObservation(
                change_id=change_id,
                task_or_finalization_id=operation_id,
                exact_commit=exact_head,
                observation_kind="finalization-observation",
                command_or_procedure="Portfolio finalization exact-head check",
                exit_status_or_artifact_locator="observed:clean-reviewed-head",
                observer_or_runner_identity="Portfolio test observer",
                observed_at=observed_at,
            )
        ),
    )
    review = DeliveryReviewReceipt.create(
        DeliveryReview(
            exact_commit=exact_head,
            author_id="Portfolio finalization author",
            reviewer_id="Portfolio finalization reviewer",
            evidence=("The exact Change head satisfies finalization authority.",),
            reviewed_at=observed_at,
        )
    )
    return FinalizeDeliveryChange(
        operation_id=operation_id,
        exact_head=exact_head,
        observations=observations,
        review=review,
    )


def _runtime(
    state_root: Path,
    contract: DeliveryContract,
    manager: ChangeWorkspaceManager,
    stage: DeliveryStage,
    completed_commit: str,
) -> DeliveryRuntime:
    task = _task()
    authority_digest = hashlib.sha256(_canonical(contract)).hexdigest()
    has_task = stage in {DeliveryStage.IMPLEMENTATION, DeliveryStage.COMPLETED}
    has_result = stage == DeliveryStage.COMPLETED
    result = _task_result(
        "RESULT-001",
        contract.change_id,
        authority_digest,
        task,
        completed_commit,
    )
    frontier = DeliveryFrontier(
        bindings=(
            OutcomeAuthorityBinding(
                outcome_id="OUT-001",
                plan_scope_id="SCOPE-001",
                stage=stage,
                tasks=(task,) if has_task else (),
                results=(result,) if has_result else (),
            ),
        )
    )
    path = state_root / "changes" / contract.change_id / "frontier.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_canonical(frontier))
    return DeliveryRuntime(state_root, contract, workspace_manager=manager)


def _set_checkpoint(
    runtime: DeliveryRuntime,
    state_root: Path,
    pending: DeliveryPendingCheckpoint,
    *,
    published_head: str | None = None,
) -> Path:
    path = state_root / f"changes/{runtime.contract.change_id}/frontier.json"
    frontier = DeliveryFrontier.model_validate_json(runtime.frontier_bytes())
    path.write_bytes(
        _canonical(frontier.model_copy(update={"published_head": published_head, "pending_checkpoint": pending}))
    )
    return path


def _policies() -> tuple[DeliveryRolePolicy, ...]:
    return (
        DeliveryRolePolicy(
            worker_role=DeliveryWorkerRole.PLANNER,
            worker_agent="planner",
            reviewer_agent="planner-challenger",
        ),
        DeliveryRolePolicy(
            worker_role=DeliveryWorkerRole.BUILDER,
            worker_agent="builder",
            reviewer_agent="build-reviewer",
        ),
    )


def _startup_config() -> DeliveryStartupConfig:
    return DeliveryStartupConfig(
        schema_version=2,
        remote="origin",
        target_branch="main",
        github_repository="example/project",
    )


def _repository(tmp_path: Path) -> Path:
    repository = tmp_path / "repository"
    repository.mkdir(parents=True)
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.name", "Loader Test")
    _git(repository, "config", "user.email", "loader@example.invalid")
    (repository / "product.txt").write_text("baseline\n", encoding="utf-8")
    _git(repository, "add", "product.txt")
    _git(repository, "commit", "-m", "baseline")
    _git(repository, "update-ref", "refs/remotes/origin/main", "HEAD")
    _git(repository, "remote", "add", "origin", "https://github.com/example/project.git")
    _git(repository, "update-ref", "refs/remotes/origin/main", "HEAD")
    return repository


def _advance_remote_target(tmp_path: Path, remote: Path, *, product: str | None = None) -> str:
    target_repository = tmp_path / "target-repository"
    _git(tmp_path, "clone", str(remote), str(target_repository))
    _git(target_repository, "config", "user.name", "Target User")
    _git(target_repository, "config", "user.email", "target@example.invalid")
    target_file = target_repository / ("product.txt" if product is not None else "target.txt")
    target_file.write_text(product if product is not None else "target\n", encoding="utf-8")
    _git(target_repository, "add", target_file.name)
    _git(target_repository, "commit", "-m", "advance target")
    _git(target_repository, "push", "origin", "HEAD:refs/heads/main")
    return _git(target_repository, "rev-parse", "HEAD")


def _publish_external_change_head(
    tmp_path: Path,
    repository: Path,
    branch: str,
    base_head: str,
) -> str:
    remote = tmp_path / "external-change-remote.git"
    _git(tmp_path, "init", "--bare", "-b", branch, str(remote))
    _git(repository, "remote", "add", "origin", str(remote))
    _git(repository, "push", "origin", f"{base_head}:refs/heads/{branch}")
    external = tmp_path / "external-change-repository"
    _git(tmp_path, "clone", str(remote), str(external))
    _git(external, "checkout", "-b", "external", base_head)
    _git(external, "config", "user.name", "External User")
    _git(external, "config", "user.email", "external@example.invalid")
    (external / "external.txt").write_text("external\n", encoding="utf-8")
    _git(external, "add", "external.txt")
    _git(external, "commit", "-m", "external Change update")
    adopted = _git(external, "rev-parse", "HEAD")
    _git(external, "push", "origin", f"{adopted}:refs/heads/{branch}")
    return adopted


def _portfolio(
    tmp_path: Path,
    stages: dict[str, DeliveryStage],
    *,
    execution_capacity: int = 3,
    clock: Callable[[], str] = lambda: "2026-08-04T00:00:00Z",
):
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.name", "Portfolio Test")
    _git(repository, "config", "user.email", "portfolio@example.invalid")
    (repository / "product.txt").write_text("baseline\n", encoding="utf-8")
    _git(repository, "add", "product.txt")
    _git(repository, "commit", "-m", "baseline")
    _git(repository, "update-ref", "refs/remotes/origin/main", "HEAD")
    state_root = tmp_path / "state"
    package_root = tmp_path / "packages"
    coordinator = PortfolioCoordinator(state_root)
    manager = ChangeWorkspaceManager(repository, tmp_path / "worktrees", coordinator, "main")
    store = DesignPackageStore(package_root, repository)
    authority_registry = DeliveryAuthorityRegistry(state_root, store, integration_target="main")
    runtimes = {}
    for change_id, stage in stages.items():
        intent = f"intent prose sentinel {change_id}\n".encode()
        design = f"design prose sentinel {change_id}\n".encode()
        contract = _contract(change_id, intent, design)
        package = store.create(change_id, intent, design)
        store.publish_contract(change_id, package.package_id, _canonical(contract), lambda *_content: None)
        coordination = manager.ensure(change_id)
        runtime = _runtime(state_root, contract, manager, stage, coordination.last_reviewed_commit)
        runtimes[change_id] = runtime
        frontier = DeliveryFrontier.model_validate_json(runtime.frontier_bytes())
        (state_root / "changes" / change_id / "contract.json").write_bytes(_canonical(contract))
        (state_root / "changes" / change_id / "admission.json").write_bytes(
            _canonical(_admission_receipt(contract, frontier, coordination.last_reviewed_commit))
        )
    identities = (f"identity-{index:03}" for index in itertools.count(1))

    application = PortfolioApplication(
        dict(reversed(tuple(runtimes.items()))),
        PortfolioApplicationDependencies(
            target_root=state_root,
            package_store=store,
            authority_registry=authority_registry,
            coordinator=coordinator,
            workspace_manager=manager,
            completed_history_catalog=CompletedHistoryCatalog(repository, "main", "main", state_root),
        ),
        PortfolioApplicationConfig(
            package_root=package_root,
            execution_capacity=execution_capacity,
            role_policies=_policies(),
        ),
        PortfolioApplicationHooks(
            identity_factory=lambda: next(identities),
            clock=clock,
        ),
    )
    return application, runtimes, coordinator, state_root


def _seed_loader_composed_completed_change(tmp_path: Path) -> tuple[Path, Path]:
    repository = _repository(tmp_path)
    runtime_root = repository / ".owlbear/delivery/runtime"
    package_root = repository / ".owlbear/delivery/packages"
    worktree_root = repository / ".owlbear/delivery/worktrees"
    coordinator = PortfolioCoordinator(runtime_root)
    manager = ChangeWorkspaceManager(repository, worktree_root, coordinator, "main", "origin")
    store = DesignPackageStore(package_root, repository, transaction_root=runtime_root)
    intent = b"loader-composed intent\n"
    design = b"loader-composed design\n"
    contract = _contract("change-a", intent, design)
    package = store.create("change-a", intent, design)
    store.publish_contract("change-a", package.package_id, _canonical(contract), lambda *_content: None)
    coordination = manager.ensure("change-a")
    runtime = _runtime(
        runtime_root,
        contract,
        manager,
        DeliveryStage.COMPLETED,
        coordination.last_reviewed_commit,
    )
    frontier = DeliveryFrontier.model_validate_json(runtime.frontier_bytes())
    change_root = runtime_root / "changes" / "change-a"
    (change_root / "contract.json").write_bytes(_canonical(contract))
    (change_root / "admission.json").write_bytes(
        _canonical(_admission_receipt(contract, frontier, coordination.last_reviewed_commit))
    )
    return repository, runtime_root


def _reopen_portfolio(
    tmp_path: Path,
    state_root: Path,
    runtimes: dict[str, DeliveryRuntime],
    *,
    clock: Callable[[], str] | None = None,
) -> tuple[PortfolioApplication, PortfolioCoordinator, ChangeWorkspaceManager]:
    repository = tmp_path / "repository"
    package_root = tmp_path / "packages"
    coordinator = PortfolioCoordinator(state_root)
    manager = ChangeWorkspaceManager(repository, tmp_path / "worktrees", coordinator, "main")
    store = DesignPackageStore(package_root, repository)
    authority_registry = DeliveryAuthorityRegistry(state_root, store, integration_target="main")
    hooks = (
        None if clock is None else PortfolioApplicationHooks(identity_factory=lambda: str(uuid.uuid4()), clock=clock)
    )
    reopened_runtimes = {
        change_id: DeliveryRuntime(state_root, runtime.contract, workspace_manager=manager)
        for change_id, runtime in runtimes.items()
    }
    application = PortfolioApplication(
        reopened_runtimes,
        PortfolioApplicationDependencies(
            target_root=state_root,
            package_store=store,
            authority_registry=authority_registry,
            coordinator=coordinator,
            workspace_manager=manager,
            completed_history_catalog=CompletedHistoryCatalog(repository, "main", "main", state_root),
        ),
        PortfolioApplicationConfig(
            package_root=package_root,
            execution_capacity=3,
            role_policies=_policies(),
        ),
        hooks,
    )
    return application, coordinator, manager


def _shared_acquisition_command() -> str:
    return r"""
import json
import sys
import time
from contextlib import contextmanager
from pathlib import Path

from owlbear_delivery import (
    ChangeWorkspaceManager,
    CompletedHistoryCatalog,
    DeliveryAuthorityRegistry,
    DeliveryRolePolicy,
    DeliveryRuntime,
    DeliveryWorkerRole,
    DesignPackageStore,
    PortfolioApplication,
    PortfolioApplicationConfig,
    PortfolioApplicationDependencies,
    PortfolioCoordinator,
)
from owlbear_delivery.delivery_contract_discovery import discover_persisted_changes

state_root, repository, package_root, worktree_root, barrier_root = map(Path, sys.argv[1:6])
worker_id = sys.argv[6]
coordinator = PortfolioCoordinator(state_root)
workspace_manager = ChangeWorkspaceManager(repository, worktree_root, coordinator, "main")
package_store = DesignPackageStore(package_root, repository)
authority_registry = DeliveryAuthorityRegistry(state_root, package_store, integration_target="main")
observations = discover_persisted_changes(state_root)
runtimes = {
    observation.change_id: DeliveryRuntime(state_root, observation.contract, workspace_manager=workspace_manager)
    for observation in observations
    if observation.contract is not None
}
policies = (
    DeliveryRolePolicy(
        worker_role=DeliveryWorkerRole.PLANNER,
        worker_agent="planner",
        reviewer_agent="planner-challenger",
    ),
    DeliveryRolePolicy(
        worker_role=DeliveryWorkerRole.BUILDER,
        worker_agent="builder",
        reviewer_agent="build-reviewer",
    ),
)
application = PortfolioApplication(
    runtimes,
    PortfolioApplicationDependencies(
        target_root=state_root,
        package_store=package_store,
        authority_registry=authority_registry,
        coordinator=coordinator,
        workspace_manager=workspace_manager,
        completed_history_catalog=CompletedHistoryCatalog(repository, "main", "main", state_root),
    ),
    PortfolioApplicationConfig(package_root=package_root, execution_capacity=3, role_policies=policies),
)
(barrier_root / f"ready-{worker_id}").write_text("ready", encoding="ascii")
while not (barrier_root / "go").exists():
    time.sleep(0.01)
original_lock = coordinator.acquisition_lock
original_reconcile = application._reconcile_runtimes
lock_marker = barrier_root / f"lock-{worker_id}"
outside_marker = barrier_root / f"outside-{worker_id}"

@contextmanager
def observed_lock():
    with original_lock():
        lock_marker.write_text("locked", encoding="ascii")
        try:
            yield
        finally:
            active = [
                claim
                for observation in discover_persisted_changes(state_root)
                if observation.frontier is not None
                for binding in observation.frontier.bindings
                for claim in (binding.active_claim,)
                if claim is not None
            ]
            (barrier_root / f"inside-{worker_id}.json").write_text(
                json.dumps({"count": len(active), "roles": sorted(claim.worker_role.value for claim in active)}),
                encoding="utf-8",
            )
            lock_marker.unlink(missing_ok=True)

def reconcile():
    location = "inside" if lock_marker.exists() else "outside"
    (barrier_root / f"reconcile-{worker_id}-{location}").write_text("reconciled", encoding="ascii")
    return original_reconcile()

coordinator.acquisition_lock = observed_lock
application._reconcile_runtimes = reconcile
result = application.acquire_frontier_work()
(barrier_root / f"result-{worker_id}.json").write_text(
    json.dumps({"launches": len(result.launch_packages)}),
    encoding="utf-8",
)
"""


def _wait_for_files(paths: tuple[Path, ...], timeout: float = 10) -> None:
    deadline = time.monotonic() + timeout
    while not all(path.exists() for path in paths):
        if time.monotonic() >= deadline:
            message = f"timed out waiting for {paths}"
            raise TimeoutError(message)
        time.sleep(0.01)


def test_shared_acquisition_serializes_reconciliation_and_bounds_claims(tmp_path: Path) -> None:
    _application, _runtimes, _coordinator, state_root = _portfolio(
        tmp_path,
        {
            "change-a": DeliveryStage.PLANNING,
            "change-b": DeliveryStage.IMPLEMENTATION,
            "change-c": DeliveryStage.IMPLEMENTATION,
        },
        execution_capacity=3,
    )
    repository = tmp_path / "repository"
    package_root = tmp_path / "packages"
    worktree_root = tmp_path / "worktrees"
    barrier_root = tmp_path / "acquisition-barrier"
    barrier_root.mkdir()
    source_root = Path(__file__).resolve().parents[1] / "src"
    python_path = os.pathsep.join(filter(None, (str(source_root), os.environ.get("PYTHONPATH"))))
    processes = [
        subprocess.Popen(  # noqa: S603
            (
                sys.executable,
                "-c",
                _shared_acquisition_command(),
                str(state_root),
                str(repository),
                str(package_root),
                str(worktree_root),
                str(barrier_root),
                worker_id,
            ),
            cwd=repository,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env={**os.environ, "PYTHONPATH": python_path},
        )
        for worker_id in ("one", "two")
    ]
    outputs: list[tuple[str, str]] = []
    try:
        _wait_for_files(tuple(barrier_root / f"ready-{worker_id}" for worker_id in ("one", "two")))
        (barrier_root / "go").write_text("go", encoding="ascii")
        outputs = [process.communicate(timeout=30) for process in processes]
    finally:
        for process in processes:
            if process.poll() is None:
                process.kill()
            if process.returncode is None:
                process.communicate()

    for process, (_stdout, stderr) in zip(processes, outputs, strict=False):
        assert process.returncode == 0, stderr
    assert all((barrier_root / f"reconcile-{worker_id}-inside").is_file() for worker_id in ("one", "two"))
    assert not list(barrier_root.glob("reconcile-*-outside"))
    inside = [
        json.loads((barrier_root / f"inside-{worker_id}.json").read_text(encoding="utf-8"))
        for worker_id in ("one", "two")
    ]
    assert all(item["count"] <= 3 for item in inside)
    launches = [
        json.loads((barrier_root / f"result-{worker_id}.json").read_text(encoding="utf-8"))["launches"]
        for worker_id in ("one", "two")
    ]
    assert sorted(launches) == [0, 3]
    active_claims = [
        binding.active_claim
        for observation in discover_persisted_changes(state_root)
        if observation.frontier is not None
        for binding in observation.frontier.bindings
        if binding.active_claim is not None
    ]
    assert len(active_claims) == 3
    assert {claim.worker_role for claim in active_claims} == {
        DeliveryWorkerRole.PLANNER,
        DeliveryWorkerRole.BUILDER,
    }


def test_acquisition_returns_preclaim_attention_and_refreshes_snapshot_cache(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {
            "change-a": DeliveryStage.PLANNING,
            "change-b": DeliveryStage.COMPLETED,
        },
        execution_capacity=1,
    )
    completed = coordinator.show("change-b")
    original_activate = application._activate_candidate
    reconciliation = Mock(wraps=application._reconcile_runtimes)

    def activate(candidate, source):
        launch = original_activate(candidate, source)
        _publish_merge_conflict_attention(
            runtimes,
            state_root,
            "change-b",
            completed.last_reviewed_commit,
            completed.target_head,
        )
        return launch

    with (
        patch.object(application, "_activate_candidate", side_effect=activate),
        patch.object(application, "_reconcile_runtimes", new=reconciliation),
    ):
        acquired = application.acquire_frontier_work()

    assert tuple(package.change_id for package in acquired.launch_packages) == ("change-a",)
    assert acquired.integration_attention == ()
    assert reconciliation.call_count == 1
    assert application._runtime_snapshots["change-b"].frontier.integration_attention is not None


def test_acquisition_charges_noncomposable_change_from_persisted_claims(tmp_path: Path) -> None:
    application, runtimes, _coordinator, state_root = _portfolio(
        tmp_path,
        {
            "change-a": DeliveryStage.PLANNING,
        },
        execution_capacity=1,
    )
    _admit_discovery_change(application, "blocked-change")
    blocked_runtime = runtimes.get("blocked-change", application._runtimes["blocked-change"])
    claim = application._new_claim(DeliveryWorkerRole.PLANNER, None)
    blocked_runtime.activate_claim(ActivateDeliveryClaim(outcome_id="OUT-001", claim=claim))
    (state_root / "changes/blocked-change/contract.json").unlink()

    acquired = application.acquire_frontier_work()

    assert acquired.launch_packages == ()
    assert runtimes["change-a"].active_claims() == ()
    observation = next(item for item in application._discovered_changes.values() if item.change_id == "blocked-change")
    assert observation.frontier is not None
    assert sum(binding.active_claim is not None for binding in observation.frontier.bindings) == 1
    assert application._runtime_reconciliation_errors["blocked-change"]


def test_acquisition_uses_maximum_observed_occupancy_once_per_change(tmp_path: Path) -> None:
    application, runtimes, _coordinator, state_root = _portfolio(
        tmp_path,
        {
            "change-a": DeliveryStage.PLANNING,
            "change-b": DeliveryStage.PLANNING,
        },
        execution_capacity=3,
    )
    claims = tuple(
        DeliveryActiveClaim(
            attempt_id=f"attempt-{index}",
            claim_id=f"claim-{index}",
            owner_id=f"owner-{index}",
            process_id=f"process-{index}",
            started_at="2026-08-04T00:00:00Z",
            worker_role=DeliveryWorkerRole.PLANNER,
        )
        for index in range(3)
    )
    invalid_frontier = DeliveryFrontier(
        bindings=tuple(
            OutcomeAuthorityBinding(
                outcome_id=f"OUT-{index + 1:03}",
                plan_scope_id=f"SCOPE-{index + 1:03}",
                active_claim=claim,
            )
            for index, claim in enumerate(claims)
        )
    )
    (state_root / "changes/change-a/frontier.json").write_bytes(_canonical(invalid_frontier))

    with patch.object(
        runtimes["change-a"],
        "active_claims",
        return_value=(("OUT-001", claims[0]), ("OUT-002", claims[1])),
    ):
        acquired = application.acquire_frontier_work()

    assert acquired.launch_packages == ()
    assert application._execution_occupancy() == 3


def test_finalization_uses_managed_head_and_invalidates_observed_drift(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    coordination = coordinator.show("change-a")
    exact_head = coordination.last_reviewed_commit
    request = _finalization_request("change-a", exact_head)

    receipt = application.finalize_change("change-a", request)

    assert isinstance(receipt, DeliveryFinalizationReceipt)
    assert application.finalize_change("change-a", request) == receipt
    assert runtimes["change-a"].change_stage() == DeliveryChangeStage.FINALIZED
    assert application.list_integration_attention() == ()
    publication = application.show_change_checkpoint_publication("change-a")
    assert publication.pending_checkpoint is not None
    assert publication.pending_checkpoint.head == exact_head

    (coordination.worktree_path / "external.txt").write_text("external head drift\n", encoding="utf-8")
    _git(coordination.worktree_path, "add", "external.txt")
    _git(coordination.worktree_path, "commit", "-m", "simulate external head drift")
    observed_head = _git(coordination.worktree_path, "rev-parse", "HEAD")

    invalidation = application.reconcile_finalization_head("change-a")

    assert isinstance(invalidation, DeliveryFinalizationInvalidationReceipt)
    assert invalidation.expected_head == exact_head
    assert invalidation.observed_head == observed_head
    assert runtimes["change-a"].change_stage() == DeliveryChangeStage.BUILDING
    assert application.list_integration_attention() == ()


def test_finalization_admits_clean_local_descendant_and_advances_reviewed_boundary(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    coordination = coordinator.show("change-a")
    initial = coordination.last_reviewed_commit
    exact_head = _commit_local_descendant(coordination)

    context = application.show_finalization_context("change-a")

    assert context.ready_for_finalization is True
    assert context.change_head == exact_head
    assert context.reviewed_change_head == initial
    request = _finalization_request("change-a", exact_head)
    finalization = application.finalize_change("change-a", request)

    assert finalization.exact_head == exact_head
    assert coordinator.show("change-a").last_reviewed_commit == exact_head
    assert runtimes["change-a"].finalization() == finalization
    pending = runtimes["change-a"].checkpoint_publication_state().pending_checkpoint
    assert pending is not None
    assert pending.head == exact_head
    assert application.finalize_change("change-a", request) == finalization


def test_local_descendant_does_not_grant_builder_authority(tmp_path: Path) -> None:
    application, _runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    coordination = coordinator.show("change-a")
    initial = coordination.last_reviewed_commit
    _commit_local_descendant(coordination)

    acquired = application.acquire_frontier_work()

    assert acquired.launch_packages == ()
    assert len(acquired.failures) == 1
    assert "reviewed" in acquired.failures[0].detail
    assert coordinator.show("change-a").last_reviewed_commit == initial


def test_finalization_admits_local_descendant_after_promoted_external_ancestor(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    coordination = coordinator.show("change-a")
    initial = coordination.last_reviewed_commit
    adopted = _publish_external_change_head(
        tmp_path,
        application._workspace_manager.repository,
        coordination.branch,
        initial,
    )
    application.adopt_external_head("change-a", initial, adopted, "adopt-before-local-finalization")
    application.promote_external_head("change-a", adopted, "promote-before-local-finalization")
    exact_head = _commit_local_descendant(coordination, "local-after-adoption.txt")

    finalization = application.finalize_change("change-a", _finalization_request("change-a", exact_head))

    assert finalization.exact_head == exact_head
    assert coordinator.show("change-a").last_reviewed_commit == exact_head
    promotion = coordinator.show("change-a").external_head_promotion_receipt
    assert promotion is not None
    assert promotion.promoted_head == adopted
    assert runtimes["change-a"].finalization() == finalization


def test_finalization_replays_atomic_local_boundary_after_interruption(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    coordination = coordinator.show("change-a")
    initial = coordination.last_reviewed_commit
    exact_head = _commit_local_descendant(coordination, "local-replay.txt")
    request = _finalization_request("change-a", exact_head)
    original_commit = RuntimeTransaction.commit

    def interrupt_after_frontier(transaction: RuntimeTransaction) -> None:
        def interrupt(stage: str) -> None:
            if stage == "after-first-publication":
                message = "simulated finalization interruption"
                raise RuntimeError(message)

        original_commit(transaction, failure=interrupt)

    with (
        patch.object(RuntimeTransaction, "commit", interrupt_after_frontier),
        pytest.raises(RuntimeError, match="simulated finalization interruption"),
    ):
        application.finalize_change("change-a", request)

    assert coordinator.show("change-a").last_reviewed_commit == initial
    assert tuple((state_root / "transactions").glob("*.yaml"))

    replayed = application.finalize_change("change-a", request)

    assert replayed == runtimes["change-a"].finalization()
    assert coordinator.show("change-a").last_reviewed_commit == exact_head
    assert not tuple((state_root / "transactions").glob("*.yaml"))


@pytest.mark.parametrize("user_state", _USER_CHECKOUT_STATES)
def test_finalization_preserves_user_checkout_states(
    tmp_path: Path,
    user_state: str,
    user_checkout_snapshot,
    prepare_user_checkout_state,
    seed_user_checkout_metadata,
) -> None:
    application, _runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    repository = application._workspace_manager.repository
    seed_user_checkout_metadata(repository)
    prepare_user_checkout_state(repository, user_state)
    before = user_checkout_snapshot(repository, ("refs/heads/owlbear/change/change-a",))
    exact_head = coordinator.show("change-a").last_reviewed_commit
    request = _finalization_request("change-a", exact_head)

    receipt = application.finalize_change("change-a", request)
    replayed = application.finalize_change("change-a", request)

    assert replayed == receipt
    assert receipt.exact_head == exact_head
    before.assert_unchanged(repository)


def test_application_binds_target_sync_receipt_and_invalidates_finalization(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    exact_head = coordinator.show("change-a").last_reviewed_commit
    finalization = application.finalize_change("change-a", _finalization_request("change-a", exact_head))
    receipt = ChangeTargetSyncReceipt.create(
        operation_id="sync-change-a",
        change_id="change-a",
        integration_target="main",
        expected_target="2" * 40,
        target_head="2" * 40,
        change_head_before=exact_head,
        merged_head="3" * 40,
        merge_commit=True,
    )

    with patch.object(application._workspace_manager, "sync_with_target", return_value=receipt) as sync:
        assert application.sync_change_with_target("change-a", "2" * 40, "sync-change-a") == receipt

    request = sync.call_args.args[0]
    assert request.change_id == "change-a"
    assert request.expected_target == "2" * 40
    assert request.operation_id == "sync-change-a"
    assert runtimes["change-a"].target_sync_receipt() == receipt
    assert runtimes["change-a"].finalization() is None
    assert runtimes["change-a"].finalization_invalidation().finalization_id == finalization.finalization_id


def test_application_binds_external_head_adoption_without_advancing_reviewed_authority(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    coordination = coordinator.show("change-a")
    expected_head = coordination.last_reviewed_commit
    finalization = application.finalize_change("change-a", _finalization_request("change-a", expected_head))
    receipt = ChangeExternalHeadAdoptionReceipt.create(
        operation_id="adopt-change-a",
        change_id="change-a",
        branch=coordination.branch,
        expected_head=expected_head,
        adopted_head="5" * 40,
    )

    with patch.object(application._workspace_manager, "adopt_external_head", return_value=receipt) as adopt:
        assert application.adopt_external_head("change-a", expected_head, "5" * 40, "adopt-change-a") == receipt

    request = adopt.call_args.args[0]
    assert request.change_id == "change-a"
    assert request.expected_head == expected_head
    assert request.adopted_head == "5" * 40
    assert request.operation_id == "adopt-change-a"
    assert coordinator.show("change-a").last_reviewed_commit == expected_head
    assert runtimes["change-a"].external_head_adoption_receipt() == receipt
    assert runtimes["change-a"].finalization() is None
    invalidation = runtimes["change-a"].finalization_invalidation()
    assert invalidation is not None
    assert invalidation.finalization_id == finalization.finalization_id
    publication = runtimes["change-a"].checkpoint_publication_state()
    assert publication.pending_checkpoint is not None
    assert publication.pending_checkpoint.head == "5" * 40


def test_application_binds_observed_external_head_without_granting_review_authority(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    coordination = coordinator.show("change-a")
    expected_head = coordination.last_reviewed_commit
    repository = tmp_path / "repository"
    adopted = _publish_external_change_head(tmp_path, repository, coordination.branch, expected_head)
    _git(
        repository,
        "fetch",
        "origin",
        f"refs/heads/{coordination.branch}:refs/remotes/origin/{coordination.branch}",
    )
    _git(coordination.worktree_path, "merge", "--ff-only", adopted)

    receipt = application.adopt_external_head("change-a", expected_head, adopted, "observe-change-a")

    assert receipt.provenance == "observed"
    assert runtimes["change-a"].external_head_adoption_receipt() == receipt
    assert coordinator.show("change-a").last_reviewed_commit == expected_head
    assert runtimes["change-a"].checkpoint_publication_state().pending_checkpoint is not None


def test_application_requires_adopted_head_promotion_before_build_acquisition(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    initial = coordinator.show("change-a").last_reviewed_commit
    branch = coordinator.show("change-a").branch
    adopted = _publish_external_change_head(tmp_path, application._workspace_manager.repository, branch, initial)

    application.adopt_external_head("change-a", initial, adopted, "adopt-for-acquisition")
    blocked = application.acquire_frontier_work()

    assert blocked.launch_packages == ()
    assert len(blocked.failures) == 1
    assert "explicit promotion" in blocked.failures[0].detail
    assert coordinator.show("change-a").last_reviewed_commit == initial

    promoted = application.promote_external_head("change-a", adopted, "promote-for-acquisition")
    assert promoted.promoted_head == adopted
    acquired = application.acquire_frontier_work()

    assert acquired.failures == ()
    assert len(acquired.launch_packages) == 1
    launch = acquired.launch_packages[0]
    assert launch.source_head == adopted
    assert launch.last_reviewed_commit == adopted
    assert runtimes["change-a"].external_head_adoption_receipt().adopted_head == adopted


def test_finalization_replay_promotes_an_adopted_head_after_runtime_commit(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    initial = coordinator.show("change-a").last_reviewed_commit
    branch = coordinator.show("change-a").branch
    adopted = _publish_external_change_head(tmp_path, application._workspace_manager.repository, branch, initial)
    application.adopt_external_head("change-a", initial, adopted, "adopt-for-finalization")
    request = _finalization_request("change-a", adopted)

    with (
        patch.object(
            application,
            "_promote_finalized_external_head",
            side_effect=RuntimeError("simulated promotion crash"),
        ),
        pytest.raises(RuntimeError, match="simulated promotion crash"),
    ):
        application.finalize_change("change-a", request)

    assert runtimes["change-a"].finalization() is not None
    assert coordinator.show("change-a").last_reviewed_commit == initial
    replayed = application.reconcile_finalization_head("change-a")

    assert replayed == runtimes["change-a"].finalization()
    assert coordinator.show("change-a").last_reviewed_commit == adopted


def test_finalization_replay_repairs_runtime_promotion_after_workspace_commit(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    initial = coordinator.show("change-a").last_reviewed_commit
    branch = coordinator.show("change-a").branch
    adopted = _publish_external_change_head(tmp_path, application._workspace_manager.repository, branch, initial)
    application.adopt_external_head("change-a", initial, adopted, "adopt-for-finalization-repair")
    request = _finalization_request("change-a", adopted)

    with (
        patch.object(
            runtimes["change-a"],
            "record_external_head_promotion",
            side_effect=RuntimeError("simulated runtime promotion crash"),
        ),
        pytest.raises(PortfolioApplicationError, match="finalization could not promote"),
    ):
        application.finalize_change("change-a", request)

    workspace_promotion = coordinator.show("change-a").external_head_promotion_receipt
    assert workspace_promotion is not None
    assert runtimes["change-a"].external_head_promotion_receipt() is None

    application.reconcile_finalization_head("change-a")

    assert runtimes["change-a"].external_head_promotion_receipt() == workspace_promotion


def test_finalization_replay_skips_reconciled_promotion_after_worktree_loss(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    initial = coordinator.show("change-a").last_reviewed_commit
    branch = coordinator.show("change-a").branch
    adopted = _publish_external_change_head(tmp_path, application._workspace_manager.repository, branch, initial)
    application.adopt_external_head("change-a", initial, adopted, "adopt-for-idempotent-replay")
    request = _finalization_request("change-a", adopted)
    finalization = application.finalize_change("change-a", request)

    shutil.rmtree(coordinator.show("change-a").worktree_path)

    with patch.object(
        application._workspace_manager,
        "promote_external_head",
        side_effect=AssertionError("reconciled finalization must not re-enter workspace promotion"),
    ):
        assert application.finalize_change("change-a", request) == finalization

    assert runtimes["change-a"].external_head_promotion_receipt() is not None


def test_finalization_after_builder_child_does_not_repromote_adopted_ancestor(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    initial = coordinator.show("change-a").last_reviewed_commit
    branch = coordinator.show("change-a").branch
    adopted = _publish_external_change_head(tmp_path, application._workspace_manager.repository, branch, initial)
    application.adopt_external_head("change-a", initial, adopted, "adopt-for-builder")
    application.promote_external_head("change-a", adopted, "promote-for-builder")

    launch = application.acquire_frontier_work().launch_packages[0]
    task = runtimes["change-a"].show_binding("OUT-001").tasks[0]
    builder_file = launch.worktree_path / "builder.txt"
    builder_file.write_text("builder child\n", encoding="utf-8")
    _git(launch.worktree_path, "add", builder_file.name)
    _git(launch.worktree_path, "commit", "-m", "builder child")
    child = _git(launch.worktree_path, "rev-parse", "HEAD")
    result = application.publish_delivery_result(
        "change-a",
        PublishDeliveryResult(
            outcome_id="OUT-001",
            claim_id=launch.claim.claim_id,
            result=_task_result(
                "RESULT-BUILDER-CHILD",
                "change-a",
                runtimes["change-a"].authority_digest,
                task,
                child,
            ),
        ),
    )
    application.transition_delivery(
        "change-a",
        AdvanceDelivery(
            outcome_id="OUT-001",
            claim_id=launch.claim.claim_id,
            output=result.output,
        ),
    )

    assert coordinator.show("change-a").last_reviewed_commit == child
    with patch.object(
        application._workspace_manager,
        "promote_external_head",
        side_effect=AssertionError("finalization must not re-promote a reviewed Builder child"),
    ):
        finalization = application.finalize_change("change-a", _finalization_request("change-a", child))

    assert finalization.exact_head == child


def test_application_promotes_only_reconciled_adoption_evidence(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    initial = coordinator.show("change-a").last_reviewed_commit
    branch = coordinator.show("change-a").branch
    adopted = _publish_external_change_head(tmp_path, application._workspace_manager.repository, branch, initial)
    application.adopt_external_head("change-a", initial, adopted, "adopt-for-promotion")

    promoted = application.promote_external_head("change-a", adopted, "promote-for-promotion")
    replayed = application.promote_external_head("change-a", adopted, "promote-for-promotion")

    assert promoted == replayed
    assert promoted.change_id == "change-a"
    assert promoted.promoted_head == adopted
    assert coordinator.show("change-a").last_reviewed_commit == adopted
    assert runtimes["change-a"].external_head_adoption_receipt().adopted_head == adopted


def test_application_acquires_after_real_target_sync_at_the_merged_head(tmp_path: Path) -> None:
    application, _runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    repository = application._workspace_manager.repository
    remote = tmp_path / "remote.git"
    subprocess.run(("git", "init", "--bare", "-b", "main", str(remote)), check=True, capture_output=True)  # noqa: S603, S607
    _git(repository, "remote", "add", "origin", str(remote))
    _git(repository, "push", "origin", "refs/heads/main:refs/heads/main")
    target_head = _advance_remote_target(tmp_path, remote)

    receipt = application.sync_change_with_target("change-a", target_head, "sync-change-a")
    acquired = application.acquire_frontier_work()

    assert acquired.failures == ()
    assert len(acquired.launch_packages) == 1
    assert acquired.launch_packages[0].source_head == receipt.merged_head
    assert application._workspace_manager.reviewed_source_head("change-a") == receipt.merged_head


def test_target_sync_demotes_ready_pull_request_before_moving_managed_branch(tmp_path: Path) -> None:
    application, runtime, provider, state, exact_head, _state_root = _awaiting_acceptance_fixture(tmp_path)
    repository = application._workspace_manager.repository
    remote = tmp_path / "target-remote.git"
    subprocess.run(("git", "init", "--bare", "-b", "main", str(remote)), check=True, capture_output=True)  # noqa: S603, S607
    _git(repository, "remote", "add", "origin", str(remote))
    _git(repository, "push", "origin", "refs/heads/main:refs/heads/main")
    target_head = _advance_remote_target(tmp_path, remote)
    coordination = application._workspace_manager.show("change-a")
    draft_transition_heads: list[tuple[str, str, bool]] = []
    original_transition = provider.set_pull_request_draft_state.side_effect

    def observe_transition(request):
        draft_transition_heads.append(
            (
                _git(repository, "rev-parse", coordination.branch),
                request.expected_head_sha,
                request.draft,
            )
        )
        return original_transition(request)

    provider.set_pull_request_draft_state.side_effect = observe_transition

    receipt = application.sync_change_with_target("change-a", target_head, "sync-before-branch-move")

    assert draft_transition_heads == [(exact_head, exact_head, True)]
    assert _git(repository, "rev-parse", coordination.branch) == receipt.merged_head
    assert state["pull_request"].draft is True
    assert runtime.ready_receipt() is None


def test_external_head_adoption_demotes_ready_pull_request_before_moving_managed_branch(tmp_path: Path) -> None:
    application, runtime, provider, state, exact_head, _state_root = _awaiting_acceptance_fixture(tmp_path)
    repository = application._workspace_manager.repository
    coordination = application._workspace_manager.show("change-a")
    adopted_head = _publish_external_change_head(tmp_path, repository, coordination.branch, exact_head)
    draft_transition_heads: list[tuple[str, str, bool]] = []
    original_transition = provider.set_pull_request_draft_state.side_effect

    def observe_transition(request):
        draft_transition_heads.append(
            (
                _git(repository, "rev-parse", coordination.branch),
                request.expected_head_sha,
                request.draft,
            )
        )
        return original_transition(request)

    provider.set_pull_request_draft_state.side_effect = observe_transition

    receipt = application.adopt_external_head(
        "change-a",
        exact_head,
        adopted_head,
        "adopt-before-branch-move",
    )

    assert draft_transition_heads == [(exact_head, exact_head, True)]
    assert _git(repository, "rev-parse", coordination.branch) == adopted_head
    assert state["pull_request"].draft is True
    assert runtime.ready_receipt() is None
    assert receipt.adopted_head == adopted_head


def test_external_head_adoption_retains_attention_after_demotion_then_movement_failure(tmp_path: Path) -> None:
    application, runtime, provider, state, exact_head, _state_root = _awaiting_acceptance_fixture(tmp_path)
    repository = application._workspace_manager.repository
    coordination = application._workspace_manager.show("change-a")
    adopted_head = _publish_external_change_head(tmp_path, repository, coordination.branch, exact_head)
    provider.set_pull_request_draft_state.reset_mock()
    original_run_git = application._workspace_manager._run_git

    def fail_merge(*arguments: str, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        if arguments and arguments[0] == "merge":
            return subprocess.CompletedProcess(arguments, 1, b"", b"fast-forward failed")
        return original_run_git(*arguments, **kwargs)

    with (
        patch.object(application._workspace_manager, "_run_git", side_effect=fail_merge),
        pytest.raises(PortfolioApplicationError, match="external Change head could not be adopted"),
    ):
        application.adopt_external_head("change-a", exact_head, adopted_head, "adopt-after-demotion")

    attention = runtime.change_disposition()
    assert attention is not None
    assert attention.kind.value == "publication-attention"
    assert attention.diagnostics[:2] == (
        "external-head-adoption-movement-failed",
        "external-head-adoption-operation:adopt-after-demotion",
    )
    assert runtime.ready_receipt() is None
    assert state["pull_request"].draft is True


def test_provider_demotion_failure_prevents_target_sync_branch_movement(tmp_path: Path) -> None:
    application, runtime, provider, _state, exact_head, _state_root = _awaiting_acceptance_fixture(tmp_path)
    repository = application._workspace_manager.repository
    remote = tmp_path / "target-failure-remote.git"
    subprocess.run(("git", "init", "--bare", "-b", "main", str(remote)), check=True, capture_output=True)  # noqa: S603, S607
    _git(repository, "remote", "add", "origin", str(remote))
    _git(repository, "push", "origin", "refs/heads/main:refs/heads/main")
    target_head = _advance_remote_target(tmp_path, remote)
    branch = application._workspace_manager.show("change-a").branch
    provider.set_pull_request_draft_state.side_effect = PublicationProviderError(
        PublicationProviderFailureCode.UNAVAILABLE,
        "return_to_draft",
        "provider unavailable",
        retry_safe=True,
    )

    with pytest.raises(PortfolioApplicationError, match="target synchronization could not be completed"):
        application.sync_change_with_target("change-a", target_head, "sync-provider-failure")

    assert _git(repository, "rev-parse", branch) == exact_head
    assert runtime.ready_receipt() is not None


def test_application_captures_target_sync_conflict_as_publication_attention(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    exact_head = coordinator.show("change-a").last_reviewed_commit
    finalization = application.finalize_change("change-a", _finalization_request("change-a", exact_head))

    with (
        patch.object(
            application._workspace_manager,
            "sync_with_target",
            side_effect=ChangeTargetSyncConflictError(
                "change-a",
                "sync-change-a",
                "2" * 40,
                ("product.txt",),
            ),
        ),
        pytest.raises(ChangeTargetSyncConflictError) as raised,
    ):
        application.sync_change_with_target("change-a", "2" * 40, "sync-change-a")

    assert raised.value.code == "ERR_TARGET_SYNC_CONFLICT"
    assert raised.value.conflict_paths == ("product.txt",)
    attention = runtimes["change-a"].change_disposition()
    assert attention is not None
    assert attention.kind.value == "publication-attention"
    assert attention.diagnostics == (
        "target-sync-operation:sync-change-a",
        "target synchronization merge conflict",
        "conflict-path:product.txt",
    )
    assert runtimes["change-a"].finalization() is None
    assert runtimes["change-a"].finalization_invalidation().finalization_id == finalization.finalization_id
    assert runtimes["change-a"].finalization_invalidation().reason == "target-sync-conflict"


@pytest.mark.parametrize("lifecycle", [DeliveryChangeStage.DEFERRED, DeliveryChangeStage.ABANDONED])
def test_target_sync_rejects_terminal_or_deferred_change_before_workspace_mutation(
    tmp_path: Path,
    lifecycle: DeliveryChangeStage,
) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    if lifecycle is DeliveryChangeStage.DEFERRED:
        application.defer_change("change-a", "Wait before target synchronization")
    else:
        application.abandon_change("change-a", "Stop before target synchronization")
    before = coordinator.show("change-a")

    with (
        patch.object(application._workspace_manager, "sync_with_target") as workspace_sync,
        pytest.raises(PortfolioApplicationError, match="requires a mutable Change"),
    ):
        application.sync_change_with_target("change-a", "2" * 40, "sync-lifecycle")

    assert not workspace_sync.called
    assert coordinator.show("change-a") == before
    assert runtimes["change-a"].change_stage() is lifecycle


def test_application_aborts_target_sync_conflict_and_resolves_exact_attention(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    exact_head = coordinator.show("change-a").last_reviewed_commit
    disposition = runtimes["change-a"].capture_target_sync_conflict(
        "sync-abort",
        "2" * 40,
        datetime.now(UTC),
        ("target synchronization merge conflict",),
    )
    receipt = ChangeTargetSyncAbortReceipt.create(
        operation_id="sync-abort",
        change_id="change-a",
        target_head="2" * 40,
        restored_head=exact_head,
    )

    with patch.object(application._workspace_manager, "abort_target_sync_conflict", return_value=receipt):
        assert (
            application.abort_target_sync_conflict(
                "change-a",
                disposition.disposition_id,
                "2" * 40,
                "sync-abort",
            )
            == receipt
        )

    assert runtimes["change-a"].change_disposition() is None
    assert runtimes["change-a"].change_disposition_resolution().disposition_id == disposition.disposition_id


def test_resolving_change_attention_fails_fast_when_checkpoint_is_busy(tmp_path: Path) -> None:
    application, runtimes, _coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    disposition = runtimes["change-a"].capture_publication_attention(
        datetime(2026, 8, 11, 16, tzinfo=UTC),
        ("provider unavailable",),
    )

    with (
        patch("owlbear_delivery.portfolio_application._ATTENTION_RESOLUTION_LOCK_TIMEOUT_SECONDS", 0.0),
        locked_roots((state_root / "publications/checkpoints/locks/change-a",)),
        pytest.raises(DeliveryChangeDispositionBusyError, match="already in progress"),
    ):
        application.resolve_change_disposition("change-a", disposition.disposition_id)

    assert runtimes["change-a"].change_disposition() == disposition


def test_resolving_change_attention_retries_short_checkpoint_contention(tmp_path: Path) -> None:
    application, runtimes, _coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    disposition = runtimes["change-a"].capture_publication_attention(
        datetime(2026, 8, 11, 16, tzinfo=UTC),
        ("provider unavailable",),
    )
    lock = locked_roots((state_root / "publications/checkpoints/locks/change-a",))
    lock.__enter__()
    released = False

    def release_lock(_delay: float) -> None:
        nonlocal released
        lock.__exit__(None, None, None)
        released = True

    try:
        with patch("owlbear_delivery.portfolio_application.time.sleep", side_effect=release_lock) as sleep:
            resolution = application.resolve_change_disposition("change-a", disposition.disposition_id)
        sleep.assert_called_once()
    finally:
        if not released:
            lock.__exit__(None, None, None)

    assert resolution.disposition_id == disposition.disposition_id
    assert runtimes["change-a"].change_disposition() is None


def test_application_records_semantic_target_resolution_with_exact_runtime_receipt(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    exact_head = coordinator.show("change-a").last_reviewed_commit
    finalization = application.finalize_change("change-a", _finalization_request("change-a", exact_head))
    disposition = runtimes["change-a"].capture_target_sync_conflict(
        "sync-resolve",
        "2" * 40,
        datetime.now(UTC),
        ("target synchronization merge conflict",),
    )
    receipt = ChangeTargetSyncReceipt.create(
        operation_id="sync-resolve",
        change_id="change-a",
        integration_target="main",
        expected_target="2" * 40,
        target_head="2" * 40,
        change_head_before=exact_head,
        merged_head="3" * 40,
        merge_commit=True,
    )

    with patch.object(application._workspace_manager, "resolve_target_sync_conflict", return_value=receipt):
        assert (
            application.resolve_target_sync_conflict(
                "change-a",
                disposition.disposition_id,
                "2" * 40,
                "sync-resolve",
            )
            == receipt
        )

    assert runtimes["change-a"].change_disposition() is None
    assert runtimes["change-a"].target_sync_receipt() == receipt
    assert runtimes["change-a"].finalization() is None
    assert runtimes["change-a"].finalization_invalidation().finalization_id == finalization.finalization_id


def test_resolved_target_merge_requires_fresh_finalization_before_checkpoint_publication(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    repository = application._workspace_manager.repository
    remote = tmp_path / "resolved-merge-remote.git"
    subprocess.run(("git", "init", "--bare", "-b", "main", str(remote)), check=True, capture_output=True)  # noqa: S603, S607
    _git(repository, "remote", "add", "origin", str(remote))
    _git(repository, "push", "origin", "refs/heads/main:refs/heads/main")
    target_head = _advance_remote_target(tmp_path, remote, product="target\n")
    coordination = coordinator.show("change-a")
    (coordination.worktree_path / "product.txt").write_text("change\n", encoding="utf-8")
    _git(coordination.worktree_path, "add", "product.txt")
    _git(coordination.worktree_path, "commit", "-m", "change branch edit")
    reviewed_head = _git(coordination.worktree_path, "rev-parse", "HEAD")
    application._workspace_manager.record_reviewed("change-a", reviewed_head)

    with pytest.raises(ChangeTargetSyncConflictError):
        application.sync_change_with_target("change-a", target_head, "sync-resolved-merge")

    disposition = runtimes["change-a"].change_disposition()
    assert disposition is not None
    (coordination.worktree_path / "product.txt").write_text("resolved\n", encoding="utf-8")
    _git(coordination.worktree_path, "add", "product.txt")
    receipt = application.resolve_target_sync_conflict(
        "change-a",
        disposition.disposition_id,
        target_head,
        "sync-resolved-merge",
    )
    application._change_branch_publisher = Mock()
    application._draft_pull_request_publisher = Mock()

    result = application.reconcile_change_checkpoint("change-a")

    assert receipt.review_required is True
    assert receipt.schema_version == 2
    assert runtimes["change-a"].finalization() is None
    assert result.reconciled is False
    assert result.state.pending_checkpoint is not None
    assert result.state.pending_checkpoint.head == receipt.merged_head
    application._change_branch_publisher.publish.assert_not_called()
    application._draft_pull_request_publisher.publish.assert_not_called()


@pytest.mark.parametrize("operation", ["abort_target_sync_conflict", "resolve_target_sync_conflict"])
def test_target_sync_conflict_exit_rejects_deferred_change_before_workspace_mutation(
    tmp_path: Path,
    operation: str,
) -> None:
    application, runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    runtime = runtimes["change-a"]
    disposition = runtime.capture_target_sync_conflict(
        "sync-deferred",
        "2" * 40,
        datetime.now(UTC),
        ("target synchronization merge conflict",),
    )
    application.defer_change("change-a", "Wait before resolving the preserved merge")

    with (
        patch.object(application._workspace_manager, operation) as workspace_exit,
        pytest.raises(PortfolioApplicationError, match="requires a mutable Change"),
    ):
        getattr(application, operation)(
            "change-a",
            disposition.disposition_id,
            "2" * 40,
            "sync-deferred",
        )

    assert not workspace_exit.called
    assert runtime.change_stage() is DeliveryChangeStage.DEFERRED


@pytest.mark.parametrize("operation", ["abort_target_sync_conflict", "resolve_target_sync_conflict"])
def test_target_sync_conflict_exit_rejects_abandoned_change_before_workspace_mutation(
    tmp_path: Path,
    operation: str,
) -> None:
    application, runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    runtime = runtimes["change-a"]
    disposition = runtime.capture_target_sync_conflict(
        "sync-abandoned",
        "2" * 40,
        datetime.now(UTC),
        ("target synchronization merge conflict",),
    )
    application.abandon_change("change-a", "Stop the unresolved Change")

    with (
        patch.object(application._workspace_manager, operation) as workspace_exit,
        pytest.raises(DeliveryRuntimeConflictError, match="target synchronization"),
    ):
        getattr(application, operation)(
            "change-a",
            disposition.disposition_id,
            "2" * 40,
            "sync-abandoned",
        )

    assert not workspace_exit.called
    assert runtime.change_stage() is DeliveryChangeStage.ABANDONED


def test_abandoning_preserved_target_sync_conflict_surfaces_cleanup_attention(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    repository = application._workspace_manager.repository
    remote = tmp_path / "remote.git"
    subprocess.run(("git", "init", "--bare", "-b", "main", str(remote)), check=True, capture_output=True)  # noqa: S603, S607
    _git(repository, "remote", "add", "origin", str(remote))
    _git(repository, "push", "origin", "refs/heads/main:refs/heads/main")
    target_head = _advance_remote_target(tmp_path, remote, product="target\n")
    coordination = coordinator.show("change-a")
    (coordination.worktree_path / "product.txt").write_text("change\n", encoding="utf-8")
    _git(coordination.worktree_path, "add", "product.txt")
    _git(coordination.worktree_path, "commit", "-m", "change branch edit")
    application._workspace_manager.record_reviewed(
        "change-a",
        _git(coordination.worktree_path, "rev-parse", "HEAD"),
    )

    with pytest.raises(ChangeTargetSyncConflictError):
        application.sync_change_with_target("change-a", target_head, "sync-abandoned-cleanup")

    application.abandon_change("change-a", "Stop the unresolved Change")

    with pytest.raises(ChangeWorktreeAttentionError) as raised:
        application.cleanup_abandoned_change_worktree("change-a")

    assert ChangeWorktreeAttentionCode.WORKTREE_DIRTY in raised.value.attention
    assert runtimes["change-a"].change_stage() is DeliveryChangeStage.ABANDONED
    assert coordination.worktree_path.exists()


@pytest.mark.parametrize("remove_worktree", [False, True])
def test_abandoned_target_sync_conflict_can_be_discarded_and_cleaned(
    tmp_path: Path,
    remove_worktree: bool,  # noqa: FBT001 - pytest parametrization supplies this boolean positionally.
) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    repository = application._workspace_manager.repository
    remote = tmp_path / "discard-merge-remote.git"
    subprocess.run(("git", "init", "--bare", "-b", "main", str(remote)), check=True, capture_output=True)  # noqa: S603, S607
    _git(repository, "remote", "add", "origin", str(remote))
    _git(repository, "push", "origin", "refs/heads/main:refs/heads/main")
    target_head = _advance_remote_target(tmp_path, remote, product="target\n")
    coordination = coordinator.show("change-a")
    (coordination.worktree_path / "product.txt").write_text("change\n", encoding="utf-8")
    _git(coordination.worktree_path, "add", "product.txt")
    _git(coordination.worktree_path, "commit", "-m", "change branch edit")
    application._workspace_manager.record_reviewed(
        "change-a",
        _git(coordination.worktree_path, "rev-parse", "HEAD"),
    )

    with pytest.raises(ChangeTargetSyncConflictError):
        application.sync_change_with_target("change-a", target_head, "sync-discard-cleanup")
    application.abandon_change("change-a", "Stop the unresolved Change")
    if remove_worktree:
        _git(repository, "worktree", "remove", "--force", str(coordination.worktree_path))

    receipt = application.cleanup_abandoned_change_worktree_after_target_sync_discard(
        "change-a",
        confirmed_discard=True,
    )

    assert receipt.change_id == "change-a"
    assert not coordination.worktree_path.exists()
    assert _git_ref_exists(repository, coordination.branch)
    assert runtimes["change-a"].change_stage() is DeliveryChangeStage.ABANDONED
    assert coordinator.show("change-a").target_sync_conflict is None
    assert coordinator.show("change-a").target_sync_abort_receipt is not None
    assert application.list_retained_change_worktrees() == ()


def test_finalization_context_uses_managed_change_head(tmp_path: Path) -> None:
    application, _runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    change_head = coordinator.show("change-a").last_reviewed_commit

    context = application.show_finalization_context("change-a")

    assert context.change_head == change_head
    assert context.reviewed_change_head == change_head
    assert context.publication_phase.value == "ready-for-finalization"


def test_finalization_context_reports_existing_exact_finalization_head(tmp_path: Path) -> None:
    application, _runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    exact_head = coordinator.show("change-a").last_reviewed_commit
    request = _finalization_request("change-a", exact_head)
    receipt = application.finalize_change("change-a", request)

    context = application.show_finalization_context("change-a")

    assert context.finalization_id == receipt.finalization_id
    assert context.finalized_head == exact_head
    assert context.change_head == exact_head


def test_finalization_rejects_change_head_drift_before_persistence(tmp_path: Path) -> None:
    application, runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    coordination = application._workspace_manager.show("change-a")
    exact_head = coordination.last_reviewed_commit
    request = _finalization_request("change-a", exact_head)
    (coordination.worktree_path / "unreviewed.txt").write_text("unreviewed\n", encoding="utf-8")
    _git(coordination.worktree_path, "add", "unreviewed.txt")
    _git(coordination.worktree_path, "commit", "-m", "unreviewed Change head")

    with pytest.raises(PortfolioApplicationError, match="finalization"):
        application.finalize_change("change-a", request)

    assert runtimes["change-a"].finalization() is None


def test_finalization_rejects_exact_head_mismatch(tmp_path: Path) -> None:
    application, runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    exact_head = runtimes["change-a"].bindings()[0].results[0].completed_commit
    request = _finalization_request("change-a", exact_head).model_copy(
        update={"exact_head": "f" * 40},
    )

    with pytest.raises(PortfolioApplicationError, match="current Change head"):
        application.finalize_change("change-a", request)

    assert runtimes["change-a"].finalization() is None


def _fail_once_then_set_draft_state(pull_requests: list[PublicationPullRequest]):
    failures_remaining = 1

    def transition(request):
        nonlocal failures_remaining
        if failures_remaining:
            failures_remaining -= 1
            raise PublicationProviderError(
                PublicationProviderFailureCode.UNAVAILABLE,
                "set_pull_request_draft_state",
                "provider unavailable",
                retry_safe=True,
            )
        pull_requests[0] = pull_requests[0].model_copy(update={"draft": request.draft})
        return pull_requests[0]

    return transition


def test_finalization_invalidates_provider_pull_request_head_drift(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    exact_head = coordinator.show("change-a").last_reviewed_commit
    receipt = application.finalize_change("change-a", _finalization_request("change-a", exact_head))
    provider = Mock()
    provider.read_repository.return_value = PublicationRepository(
        repository="example/project",
        default_branch="main",
    )
    provider.find_pull_request.return_value = None
    pull_requests: list[PublicationPullRequest] = []

    def create_pull_request(request):
        pull_request = PublicationPullRequest(
            repository=request.repository,
            number=7,
            node_id="PR_node_7",
            head_branch=request.head_branch,
            head_sha=request.head_sha,
            base_branch=request.base_branch,
            title=request.title,
            body=request.body,
            draft=True,
            state="open",
            merged=False,
        )
        pull_requests.append(pull_request)
        return pull_request

    provider.create_draft_pull_request.side_effect = create_pull_request
    publisher = DraftPullRequestPublisher(
        provider,
        repository="example/project",
        target_branch="main",
        state_root=tmp_path / "pull-requests",
    )
    publisher.publish(
        CreateOrReconcileDraftPullRequest(
            change_id="change-a",
            operation_id="create-change-a",
            published_head=exact_head,
            title="Change A",
            generated_summary="Finalized Change A.",
        )
    )
    provider.read_pull_request.side_effect = lambda _repository, _number: pull_requests[0]
    provider.observe_checks.return_value = PublicationCheckSnapshot(
        repository="example/project",
        number=7,
        head_sha=exact_head,
        checks=(),
    )

    def set_draft_state(request):
        pull_requests[0] = pull_requests[0].model_copy(update={"draft": request.draft})
        return pull_requests[0]

    provider.set_pull_request_draft_state.side_effect = set_draft_state
    application._draft_pull_request_publisher = publisher
    checkpoint = runtimes["change-a"].checkpoint_publication_state()
    assert checkpoint.pending_checkpoint is not None
    ready_request = MarkChangePullRequestReady(
        change_id="change-a",
        operation_id="ready-change-a",
        finalization_id=receipt.finalization_id,
        exact_head=exact_head,
    )

    with pytest.raises(PortfolioApplicationError, match="reconciled final checkpoint"):
        application.mark_change_ready("change-a", ready_request)

    assert provider.set_pull_request_draft_state.call_count == 0
    runtimes["change-a"].record_checkpoint_branch_publication(checkpoint, exact_head)
    runtimes["change-a"].acknowledge_checkpoint_publication(checkpoint.pending_checkpoint, exact_head)

    ready = application.mark_current_change_ready("change-a")

    assert (
        ready.finalization_id,
        runtimes["change-a"].change_stage(),
        application.list_integration_attention(),
    ) == (receipt.finalization_id, DeliveryChangeStage.AWAITING_MERGE, ())
    assert pull_requests[0].draft is False
    provider.observe_checks.assert_called_once()
    pull_requests[0] = pull_requests[0].model_copy(update={"head_sha": "f" * 40})
    provider.set_pull_request_draft_state.side_effect = _fail_once_then_set_draft_state(pull_requests)

    with pytest.raises(PublicationProviderError) as exc_info:
        application.reconcile_finalization_head("change-a")

    assert exc_info.value.code is PublicationProviderFailureCode.UNAVAILABLE
    assert runtimes["change-a"].finalization() == receipt
    assert runtimes["change-a"].ready_receipt() == ready
    assert runtimes["change-a"].change_stage() == DeliveryChangeStage.AWAITING_MERGE
    assert pull_requests[0].draft is False

    invalidation = application.reconcile_finalization_head("change-a")

    assert isinstance(invalidation, DeliveryFinalizationInvalidationReceipt)
    assert invalidation.finalization_id == receipt.finalization_id
    assert invalidation.expected_head == exact_head
    assert invalidation.observed_head == "f" * 40
    assert application._workspace_manager.observed_change_head("change-a") == exact_head
    assert runtimes["change-a"].change_stage() == DeliveryChangeStage.BUILDING
    assert pull_requests[0].draft is True
    assert provider.set_pull_request_draft_state.call_count == 3


def _awaiting_acceptance_fixture(
    tmp_path: Path,
    *,
    checks: tuple[PublicationCheck, ...] | Callable[[str], tuple[PublicationCheck, ...]] = (),
    mark_ready: bool = True,
    record_publication_identity: bool = True,
):
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    runtime = runtimes["change-a"]
    exact_head = coordinator.show("change-a").last_reviewed_commit
    application.finalize_change(
        "change-a",
        _finalization_request("change-a", exact_head),
    )
    state = {
        "pull_request": PublicationPullRequest(
            repository="example/project",
            number=7,
            node_id="PR_node_7",
            head_branch="owlbear/change/change-a",
            head_sha=exact_head,
            base_branch="main",
            title="Change A",
            body=(
                "<!-- owlbear-change:change-a -->\n\n"
                "<!-- owlbear-generated:start -->\n"
                "Finalized Change A.\n"
                "<!-- owlbear-generated:end -->\n"
            ),
            draft=True,
            state="open",
            merged=False,
        )
    }
    provider = Mock()
    provider.read_repository.return_value = PublicationRepository(
        repository="example/project",
        default_branch="main",
    )
    provider.find_pull_request.return_value = None
    provider.create_draft_pull_request.side_effect = lambda _request: state["pull_request"]
    provider.read_pull_request.side_effect = lambda _repository, _number: state["pull_request"]
    observed_checks = checks(exact_head) if callable(checks) else checks
    provider.observe_checks.return_value = PublicationCheckSnapshot(
        repository="example/project",
        number=7,
        head_sha=exact_head,
        checks=observed_checks,
    )

    def set_draft_state(request):
        state["pull_request"] = state["pull_request"].model_copy(update={"draft": request.draft})
        return state["pull_request"]

    provider.set_pull_request_draft_state.side_effect = set_draft_state
    publisher = DraftPullRequestPublisher(
        provider,
        repository="example/project",
        target_branch="main",
        state_root=tmp_path / "pull-requests",
    )
    publisher.publish(
        CreateOrReconcileDraftPullRequest(
            change_id="change-a",
            operation_id="create-change-a",
            published_head=exact_head,
            title="Change A",
            generated_summary="Finalized Change A.",
        )
    )
    application._draft_pull_request_publisher = publisher
    checkpoint = runtime.checkpoint_publication_state()
    assert checkpoint.pending_checkpoint is not None
    runtime.record_checkpoint_branch_publication(checkpoint, exact_head)
    runtime.acknowledge_checkpoint_publication(checkpoint.pending_checkpoint, exact_head)
    if record_publication_identity:
        runtime.record_publication_identity(
            DeliveryChangePublicationIdentity(
                change_id="change-a",
                repository="example/project",
                number=7,
                node_id="PR_node_7",
                head_sha=exact_head,
            )
        )
    if not mark_ready:
        return application, runtime, provider, state, exact_head, _state_root
    ready = application.mark_current_change_ready("change-a")
    assert ready.head_sha == exact_head
    return application, runtime, provider, state, exact_head, _state_root


@pytest.mark.parametrize(
    ("kind", "status", "conclusion"),
    [
        (PublicationCheckKind.CHECK_RUN, "completed", "failure"),
        (PublicationCheckKind.STATUS_CONTEXT, "error", "error"),
        (PublicationCheckKind.CHECK_RUN, "completed", None),
        (PublicationCheckKind.CHECK_RUN, "completed", "provider-added-failure"),
    ],
)
def test_mark_change_ready_captures_required_check_failure(
    tmp_path: Path,
    kind: PublicationCheckKind,
    status: str,
    conclusion: str | None,
) -> None:
    application, runtime, provider, _state, exact_head, _state_root = _awaiting_acceptance_fixture(
        tmp_path,
        checks=lambda head: (
            PublicationCheck(
                check_id="check-failure",
                kind=kind,
                name="unit tests",
                head_sha=head,
                status=status,
                conclusion=conclusion,
                required=True,
            ),
        ),
        mark_ready=False,
    )

    ready = application.mark_current_change_ready("change-a")

    disposition = runtime.change_disposition()
    assert disposition is not None
    observations = application._draft_pull_request_publisher.read_check_observations(
        ReadChangePublicationCheckObservations(
            change_id="change-a",
            repository="example/project",
            number=7,
            exact_commit=exact_head,
        )
    )
    assert len(observations) == 1
    observation_id = observations[0].observation_id
    assert disposition.diagnostics[:4] == (
        "required-publication-check-failure",
        f"exact-head:{exact_head}",
        f"check-observation:{observation_id}",
        "failing-required-checks:1",
    )
    assert runtime.change_disposition_publication() == runtime.publication_history().current
    assert ready.head_sha == exact_head
    assert runtime.ready_receipt() == ready
    assert provider.set_pull_request_draft_state.call_count == 1
    assert tuple(observation.observation_id for observation in observations) == (observation_id,)


@pytest.mark.parametrize(
    ("kind", "status", "conclusion", "required"),
    [
        (PublicationCheckKind.CHECK_RUN, "queued", None, True),
        (PublicationCheckKind.CHECK_RUN, "completed", "neutral", True),
        (PublicationCheckKind.CHECK_RUN, "completed", "skipped", True),
        (PublicationCheckKind.CHECK_RUN, "completed", "failure", False),
    ],
)
def test_mark_change_ready_does_not_gate_on_pending_or_nonblocking_checks(
    tmp_path: Path,
    kind: PublicationCheckKind,
    status: str,
    conclusion: str | None,
    required: bool,  # noqa: FBT001 - pytest parametrization supplies this boolean positionally.
) -> None:
    application, runtime, provider, _state, exact_head, _state_root = _awaiting_acceptance_fixture(
        tmp_path,
        checks=lambda head: (
            PublicationCheck(
                check_id="check-nonblocking",
                kind=kind,
                name="optional check",
                head_sha=head,
                status=status,
                conclusion=conclusion,
                required=required,
            ),
        ),
        mark_ready=False,
    )

    ready = application.mark_current_change_ready("change-a")

    assert ready.head_sha == exact_head
    assert runtime.change_disposition() is None
    assert runtime.change_stage() == DeliveryChangeStage.AWAITING_MERGE
    assert provider.set_pull_request_draft_state.call_count == 1


@pytest.mark.parametrize(
    ("status", "conclusion", "required", "expected"),
    [
        ("completed", "failure", True, PublicationCheckBlockingState.BLOCKING),
        ("queued", None, True, PublicationCheckBlockingState.REQUIRED_PENDING),
        ("completed", None, True, PublicationCheckBlockingState.BLOCKING),
        ("completed", "neutral", True, PublicationCheckBlockingState.NOT_BLOCKING),
        ("completed", "failure", False, PublicationCheckBlockingState.NOT_BLOCKING),
    ],
)
def test_classify_publication_check_preserves_ready_semantics(
    status: str,
    conclusion: str | None,
    required: Literal[True, False],
    expected: PublicationCheckBlockingState,
) -> None:
    check = PublicationCheck(
        check_id="check-classification",
        kind=PublicationCheckKind.CHECK_RUN,
        name="classification",
        head_sha="a" * 40,
        status=status,
        conclusion=conclusion,
        required=required,
    )

    assert classify_publication_check(check) is expected


def test_required_check_attention_records_after_ready_without_preexisting_publication_identity(tmp_path: Path) -> None:
    application, runtime, provider, _state, _exact_head, _state_root = _awaiting_acceptance_fixture(
        tmp_path,
        checks=lambda head: (
            PublicationCheck(
                check_id="check-failure",
                kind=PublicationCheckKind.CHECK_RUN,
                name="unit tests",
                head_sha=head,
                status="completed",
                conclusion="failure",
                required=True,
            ),
        ),
        mark_ready=False,
        record_publication_identity=False,
    )

    ready = application.mark_current_change_ready("change-a")

    assert runtime.change_disposition() is not None
    assert runtime.ready_receipt() == ready
    assert provider.set_pull_request_draft_state.call_count == 1


def test_mark_change_ready_publishes_ready_authority_to_delivery_state(tmp_path: Path) -> None:
    application, runtime, _provider, _state, _exact_head, _state_root = _awaiting_acceptance_fixture(
        tmp_path,
        mark_ready=False,
    )
    state_publisher = Mock()
    application._delivery_state_publisher = state_publisher

    ready = application.mark_current_change_ready("change-a")

    state_publisher.publish.assert_called_once()
    publication = state_publisher.publish.call_args.kwargs
    assert publication["change_id"] == "change-a"
    assert publication["operation_id"] == f"ready-{ready.receipt_id}"
    assert publication["runtime"] is runtime
    assert publication["runtime"].ready_receipt() == ready


def test_reconcile_acceptance_publishes_new_attention_authority(tmp_path: Path) -> None:
    application, runtime, _provider, state, _exact_head, _state_root = _awaiting_acceptance_fixture(tmp_path)
    state_publisher = Mock()
    application._delivery_state_publisher = state_publisher
    state["pull_request"] = state["pull_request"].model_copy(update={"state": "closed"})

    outcomes = application.reconcile_awaiting_acceptance(("change-a",))

    assert outcomes[0].status.value == "attention"
    disposition = runtime.change_disposition()
    assert disposition is not None
    state_publisher.publish.assert_called_once()
    publication = state_publisher.publish.call_args.kwargs
    assert publication["change_id"] == "change-a"
    assert publication["operation_id"] == f"acceptance-attention-{disposition.disposition_id}"
    assert publication["runtime"] is runtime


def test_required_check_attention_retries_with_stable_diagnostics_after_resolution(tmp_path: Path) -> None:
    application, runtime, _provider, _state, _exact_head, _state_root = _awaiting_acceptance_fixture(
        tmp_path,
        checks=lambda head: (
            PublicationCheck(
                check_id="check-failure",
                kind=PublicationCheckKind.CHECK_RUN,
                name="unit\ntests",
                head_sha=head,
                status="completed",
                conclusion="failure",
                required=True,
            ),
        ),
        mark_ready=False,
    )

    ready = application.mark_current_change_ready("change-a")
    first = runtime.change_disposition()
    assert first is not None
    assert runtime.ready_receipt() == ready

    application.resolve_change_disposition("change-a", first.disposition_id)

    replayed = application.mark_current_change_ready("change-a")

    assert replayed == ready
    assert runtime.change_disposition() is None
    assert _provider.observe_checks.call_count == 1


def test_mark_change_ready_replays_existing_ready_without_reobserving_checks(tmp_path: Path) -> None:
    application, runtime, provider, _state, exact_head, _state_root = _awaiting_acceptance_fixture(tmp_path)
    first = runtime.ready_receipt()
    assert first is not None
    observed_calls = provider.observe_checks.call_count
    draft_state_calls = provider.set_pull_request_draft_state.call_count
    provider.observe_checks.return_value = PublicationCheckSnapshot(
        repository="example/project",
        number=7,
        head_sha=exact_head,
        checks=(
            PublicationCheck(
                check_id="check-failure",
                kind=PublicationCheckKind.CHECK_RUN,
                name="unit tests",
                head_sha=exact_head,
                status="completed",
                conclusion="failure",
                required=True,
            ),
        ),
    )

    replayed = application.mark_current_change_ready("change-a")

    assert replayed == first
    assert provider.observe_checks.call_count == observed_calls
    assert provider.set_pull_request_draft_state.call_count == draft_state_calls
    assert runtime.change_stage() == DeliveryChangeStage.AWAITING_MERGE
    assert runtime.change_disposition() is None

    with pytest.raises(DeliveryRuntimeConflictError, match="already awaiting merge"):
        application.mark_change_ready(
            "change-a",
            MarkChangePullRequestReady(
                change_id="change-a",
                operation_id="different-ready-operation",
                finalization_id=first.finalization_id,
                exact_head=exact_head,
            ),
        )

    assert provider.observe_checks.call_count == observed_calls
    assert provider.set_pull_request_draft_state.call_count == draft_state_calls
    assert runtime.ready_receipt() == first
    assert runtime.change_disposition() is None


def test_required_check_diagnostics_are_sorted_and_sanitized() -> None:
    head = "a" * 40
    checks = (
        PublicationCheck(
            check_id="check-zeta",
            kind=PublicationCheckKind.CHECK_RUN,
            name="zeta\ncheck",
            head_sha=head,
            status="completed",
            conclusion="failure",
            required=True,
        ),
        PublicationCheck(
            check_id="check-alpha",
            kind=PublicationCheckKind.STATUS_CONTEXT,
            name="alpha",
            head_sha=head,
            status="error",
            conclusion="error",
            required=True,
        ),
    )
    snapshot = PublicationCheckSnapshot(
        repository="example/project",
        number=7,
        head_sha=head,
        checks=checks,
    )

    diagnostics = _required_check_diagnostics(snapshot, "b" * 64, checks)

    assert diagnostics == (
        "required-publication-check-failure",
        f"exact-head:{head}",
        f"check-observation:{'b' * 64}",
        "failing-required-checks:2",
        "required-check:check-alpha:name=alpha:status=error:conclusion=error",
        "required-check:check-zeta:name=zeta check:status=completed:conclusion=failure",
    )


def test_required_check_diagnostics_cap_reports_truncation() -> None:
    head = "a" * 40
    checks = tuple(
        PublicationCheck(
            check_id=f"check-{index:02d}",
            kind=PublicationCheckKind.CHECK_RUN,
            name=f"check {index:02d}",
            head_sha=head,
            status="completed",
            conclusion="failure",
            required=True,
        )
        for index in range(9)
    )
    snapshot = PublicationCheckSnapshot(
        repository="example/project",
        number=7,
        head_sha=head,
        checks=checks,
    )

    diagnostics = _required_check_diagnostics(snapshot, "b" * 64, checks)

    assert len(diagnostics) == 4 + 8 + 1
    assert diagnostics[-1] == "required-checks-truncated:1"


def test_observe_change_publication_checks_remains_read_only_for_required_failure(tmp_path: Path) -> None:
    application, runtime, provider, _state, _exact_head, _state_root = _awaiting_acceptance_fixture(
        tmp_path,
        checks=lambda head: (
            PublicationCheck(
                check_id="check-failure",
                kind=PublicationCheckKind.CHECK_RUN,
                name="unit tests",
                head_sha=head,
                status="completed",
                conclusion="failure",
                required=True,
            ),
        ),
        mark_ready=False,
    )

    observation = application.observe_change_publication_checks("change-a")

    assert observation.snapshot.checks[0].conclusion == "failure"
    assert runtime.change_disposition() is None
    assert provider.set_pull_request_draft_state.call_count == 0


def test_reconcile_awaiting_acceptance_isolated_provider_matrix(tmp_path: Path) -> None:
    application, runtime, provider, state, exact_head, _state_root = _awaiting_acceptance_fixture(tmp_path)

    waiting = application.reconcile_awaiting_acceptance(("change-a",))
    assert waiting[0].status.value == "waiting"
    assert runtime.change_disposition() is None

    provider.read_pull_request.side_effect = PublicationProviderError(
        PublicationProviderFailureCode.UNAVAILABLE,
        "read_pull_request",
        "GitHub is unavailable",
        retry_safe=True,
    )
    unavailable = application.reconcile_awaiting_acceptance(("change-a",))
    assert unavailable[0].status.value == "provider-unavailable"
    assert unavailable[0].code == "unavailable"
    provider.read_pull_request.side_effect = lambda _repository, _number: state["pull_request"]

    state["pull_request"] = state["pull_request"].model_copy(
        update={
            "head_sha": exact_head,
            "state": "closed",
            "merged": True,
            "merge_commit_sha": "f" * 40,
            "merged_at": datetime(2026, 8, 3, 14, tzinfo=UTC),
            "merged_by_login": "octocat",
        }
    )
    completed = application.reconcile_awaiting_acceptance(("change-a",))
    assert completed[0].status.value == "completed"
    assert completed[0].completion_id is not None
    assert runtime.completion_receipt() is not None


def test_prepare_review_repair_returns_ready_pull_request_to_draft(tmp_path: Path) -> None:
    application, runtime, provider, state, exact_head, _state_root = _awaiting_acceptance_fixture(tmp_path)
    provider.set_pull_request_draft_state.reset_mock()

    invalidation = application.prepare_review_repair("change-a")

    assert invalidation.reason == "review-repair"
    assert invalidation.expected_head == invalidation.observed_head == exact_head
    assert runtime.finalization() is None
    assert runtime.ready_receipt() is None
    assert state["pull_request"].draft is True
    provider.set_pull_request_draft_state.assert_called_once()
    assert provider.set_pull_request_draft_state.call_args.args[0].draft is True
    assert application.prepare_review_repair("change-a") == invalidation
    assert provider.set_pull_request_draft_state.call_count == 1


def test_prepare_review_repair_accepts_pull_request_already_in_draft(tmp_path: Path) -> None:
    application, runtime, provider, state, exact_head, _state_root = _awaiting_acceptance_fixture(
        tmp_path,
        mark_ready=False,
    )

    invalidation = application.prepare_review_repair("change-a")

    assert invalidation.expected_head == invalidation.observed_head == exact_head
    assert runtime.finalization() is None
    assert state["pull_request"].draft is True
    assert provider.set_pull_request_draft_state.call_count == 0


def test_prepare_review_repair_rejects_merged_pull_request(tmp_path: Path) -> None:
    application, runtime, provider, state, _exact_head, _state_root = _awaiting_acceptance_fixture(tmp_path)
    state["pull_request"] = state["pull_request"].model_copy(
        update={
            "state": "closed",
            "merged": True,
            "merge_commit_sha": "f" * 40,
            "merged_at": datetime(2026, 8, 3, 23, tzinfo=UTC),
            "merged_by_login": "octocat",
        }
    )
    provider.set_pull_request_draft_state.reset_mock()

    with pytest.raises(PortfolioApplicationError, match="open pull request at the finalized head"):
        application.prepare_review_repair("change-a")

    assert runtime.finalization() is not None
    assert runtime.ready_receipt() is not None
    assert provider.set_pull_request_draft_state.call_count == 0


def test_prepare_review_repair_rejects_provider_head_mismatch(tmp_path: Path) -> None:
    application, runtime, _provider, state, exact_head, _state_root = _awaiting_acceptance_fixture(tmp_path)
    state["pull_request"] = state["pull_request"].model_copy(update={"head_sha": "f" * 40})

    with pytest.raises(PortfolioApplicationError, match="open pull request at the finalized head"):
        application.prepare_review_repair("change-a")

    assert runtime.finalization() is not None
    assert runtime.finalization().exact_head == exact_head
    assert runtime.ready_receipt() is not None


def test_prepare_review_repair_preserves_authority_when_draft_transition_fails(tmp_path: Path) -> None:
    application, runtime, provider, _state, _exact_head, _state_root = _awaiting_acceptance_fixture(tmp_path)
    provider.set_pull_request_draft_state.reset_mock()
    provider.set_pull_request_draft_state.side_effect = PublicationProviderError(
        PublicationProviderFailureCode.UNAVAILABLE,
        "return_to_draft",
        "GitHub is unavailable",
        retry_safe=True,
    )

    with pytest.raises(PublicationProviderError, match="GitHub is unavailable"):
        application.prepare_review_repair("change-a")

    assert runtime.finalization() is not None
    assert runtime.ready_receipt() is not None


def test_prepare_review_repair_does_not_mutate_provider_with_existing_attention(tmp_path: Path) -> None:
    application, runtime, provider, state, _exact_head, _state_root = _awaiting_acceptance_fixture(tmp_path)
    runtime.capture_publication_attention(
        datetime(2026, 8, 11, 16, tzinfo=UTC),
        ("provider check failed",),
    )
    provider.set_pull_request_draft_state.reset_mock()
    provider.observe_pull_request.reset_mock()

    with pytest.raises(PortfolioApplicationError, match="current Change attention resolution"):
        application.prepare_review_repair("change-a")

    assert state["pull_request"].draft is False
    provider.observe_pull_request.assert_not_called()
    provider.set_pull_request_draft_state.assert_not_called()
    assert runtime.finalization() is not None
    assert runtime.ready_receipt() is not None


def test_abort_review_repair_is_replayable_with_original_identity(tmp_path: Path) -> None:
    application, runtime, provider, state, _exact_head, _state_root = _awaiting_acceptance_fixture(tmp_path)
    invalidation = application.prepare_review_repair("change-a")
    provider.read_pull_request.reset_mock()
    provider.set_pull_request_draft_state.reset_mock()

    marker = application.abort_review_repair("change-a", invalidation.invalidation_id)

    assert marker.reason == "review-repair-aborted"
    assert marker.source_invalidation_id == invalidation.invalidation_id
    assert runtime.finalization() is None
    assert runtime.ready_receipt() is None
    assert state["pull_request"].draft is True
    provider.set_pull_request_draft_state.assert_not_called()

    provider.read_pull_request.reset_mock()
    replayed = application.abort_review_repair("change-a", invalidation.invalidation_id)

    assert replayed == marker
    provider.read_pull_request.assert_not_called()


def test_abort_review_repair_rejects_provider_failure_without_runtime_mutation(tmp_path: Path) -> None:
    application, runtime, provider, state, _exact_head, _state_root = _awaiting_acceptance_fixture(tmp_path)
    invalidation = application.prepare_review_repair("change-a")
    provider.read_pull_request.reset_mock()
    provider.read_pull_request.side_effect = PublicationProviderError(
        PublicationProviderFailureCode.UNAVAILABLE,
        "read_pull_request",
        "GitHub is unavailable",
        retry_safe=True,
    )

    with pytest.raises(PublicationProviderError, match="GitHub is unavailable"):
        application.abort_review_repair("change-a", invalidation.invalidation_id)

    current = runtime.finalization_invalidation()
    assert current is not None
    assert current.reason == "review-repair"
    assert current.invalidation_id == invalidation.invalidation_id
    assert state["pull_request"].draft is True


def test_abort_review_repair_rejects_after_a_repair_commit(tmp_path: Path) -> None:
    application, runtime, provider, state, exact_head, _state_root = _awaiting_acceptance_fixture(tmp_path)
    invalidation = application.prepare_review_repair("change-a")
    coordination = application._workspace_manager.show("change-a")
    repaired_head = _commit_reviewed_head(
        application,
        coordination,
        "review-fix.txt",
        "review fix\n",
        "address review feedback",
    )
    provider.read_pull_request.reset_mock()

    with pytest.raises(PortfolioApplicationError, match="no repair commit"):
        application.abort_review_repair("change-a", invalidation.invalidation_id)

    assert repaired_head != exact_head
    assert runtime.finalization_invalidation() == invalidation
    provider.read_pull_request.assert_not_called()
    assert state["pull_request"].head_sha == exact_head


@pytest.mark.parametrize(
    "operation",
    ["sync", "adopt", "promote"],
)
def test_review_repair_fences_external_head_mutations_before_workspace_side_effects(
    tmp_path: Path,
    operation: str,
) -> None:
    application, runtime, provider, state, exact_head, _state_root = _awaiting_acceptance_fixture(tmp_path)
    application.prepare_review_repair("change-a")
    provider.set_pull_request_draft_state.reset_mock()
    provider.update_pull_request.reset_mock()
    workspace_method = {
        "sync": "sync_with_target",
        "adopt": "adopt_external_head",
        "promote": "promote_external_head",
    }[operation]
    operation_call = {
        "sync": lambda: application.sync_change_with_target("change-a", "2" * 40, "sync-during-review-repair"),
        "adopt": lambda: application.adopt_external_head(
            "change-a",
            exact_head,
            "5" * 40,
            "adopt-during-review-repair",
        ),
        "promote": lambda: application.promote_external_head(
            "change-a",
            exact_head,
            "promote-during-review-repair",
        ),
    }[operation]

    with (
        patch.object(application._workspace_manager, workspace_method) as workspace_operation,
        pytest.raises(
            PortfolioApplicationError,
            match="review repair",
        ),
    ):
        operation_call()

    workspace_operation.assert_not_called()
    provider.set_pull_request_draft_state.assert_not_called()
    provider.update_pull_request.assert_not_called()
    assert state["pull_request"].head_sha == exact_head
    assert runtime.finalization_invalidation() is not None
    assert runtime.finalization_invalidation().reason == "review-repair"


def test_review_repair_commit_can_be_refinalized_published_and_marked_ready(tmp_path: Path) -> None:
    application, runtime, provider, state, exact_head, _state_root = _awaiting_acceptance_fixture(tmp_path)
    invalidation = application.prepare_review_repair("change-a")
    coordination = application._workspace_manager.show("change-a")
    repaired_head = _commit_reviewed_head(
        application,
        coordination,
        "review-fix.txt",
        "review fix\n",
        "address review feedback",
    )
    provider.observe_checks.return_value = PublicationCheckSnapshot(
        repository="example/project",
        number=7,
        head_sha=repaired_head,
        checks=(),
    )

    def update_summary(request):
        state["pull_request"] = state["pull_request"].model_copy(update={"body": request.body})
        return state["pull_request"]

    provider.update_pull_request.side_effect = update_summary
    branch_publisher = Mock()

    def publish_branch(request: PublishChangeBranch) -> ChangeBranchPublicationReceipt:
        state["pull_request"] = state["pull_request"].model_copy(update={"head_sha": repaired_head})
        return _requested_branch_receipt(request)

    branch_publisher.publish.side_effect = publish_branch
    application._change_branch_publisher = branch_publisher

    assert state["pull_request"].head_sha == exact_head
    finalization = application.finalize_change(
        "change-a",
        _finalization_request("change-a", repaired_head),
    )

    assert invalidation.expected_head == exact_head
    assert finalization.finalization_id != invalidation.finalization_id
    assert runtime.finalization_invalidation() is None
    assert state["pull_request"].head_sha == exact_head
    result = application.reconcile_change_checkpoint("change-a")

    assert result.reconciled is True
    assert result.state.pending_checkpoint is None
    assert result.state.published_head == repaired_head
    assert runtime.finalization() == finalization
    assert state["pull_request"].head_sha == repaired_head
    assert state["pull_request"].draft is True
    branch_publisher.publish.assert_called_once()

    ready = application.mark_current_change_ready("change-a")

    assert ready.head_sha == repaired_head
    assert state["pull_request"].draft is False
    assert runtime.change_stage() == DeliveryChangeStage.AWAITING_MERGE


def test_reconcile_awaiting_acceptance_repairs_open_head_drift(tmp_path: Path) -> None:
    application, runtime, provider, state, _exact_head, _state_root = _awaiting_acceptance_fixture(tmp_path)
    provider.set_pull_request_draft_state.reset_mock()

    state["pull_request"] = state["pull_request"].model_copy(update={"head_sha": "f" * 40})
    moved = application.reconcile_awaiting_acceptance(("change-a",))

    assert moved[0].status.value == "head-moved"
    assert moved[0].code == "ERR_DELIVERY_ACCEPTANCE_HEAD_MOVED"
    assert runtime.change_stage() == DeliveryChangeStage.ACCEPTANCE_ATTENTION
    assert runtime.finalization() is None
    assert runtime.finalization_invalidation() is not None
    assert runtime.ready_receipt() is None
    disposition = runtime.change_disposition()
    assert disposition is not None
    assert disposition.acceptance_reason is DeliveryAcceptanceAttentionReason.HEAD_MOVED
    assert state["pull_request"].draft is True
    provider.set_pull_request_draft_state.assert_called_once()


def test_reconcile_awaiting_acceptance_skips_a_busy_change_without_provider_io(tmp_path: Path) -> None:
    application, _runtime, provider, _state, _exact_head, state_root = _awaiting_acceptance_fixture(tmp_path)
    lock_root = state_root / "publications/checkpoints/locks/change-a"
    provider_calls = provider.read_pull_request.call_count

    with locked_roots((lock_root,)):
        outcomes = application.reconcile_awaiting_acceptance(("change-a",))

    assert outcomes[0].status.value == "skipped"
    assert outcomes[0].code == "ERR_DELIVERY_RECONCILIATION_BUSY"
    assert provider.read_pull_request.call_count == provider_calls


def test_reconcile_awaiting_acceptance_ignores_ineligible_changes(tmp_path: Path) -> None:
    application, _runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.PLANNING},
    )

    assert application.reconcile_awaiting_acceptance() == ()


@pytest.mark.parametrize("user_state", _USER_CHECKOUT_STATES)
def test_observe_acceptance_preserves_user_checkout_states(
    tmp_path: Path,
    user_state: str,
    user_checkout_snapshot,
    prepare_user_checkout_state,
    seed_user_checkout_metadata,
) -> None:
    application, runtime, _provider, state, _exact_head, _state_root = _awaiting_acceptance_fixture(tmp_path)
    repository = application._workspace_manager.repository
    seed_user_checkout_metadata(repository)
    prepare_user_checkout_state(repository, user_state)
    before = user_checkout_snapshot(repository, ("refs/heads/owlbear/change/change-a",))
    state["pull_request"] = state["pull_request"].model_copy(
        update={
            "state": "closed",
            "merged": True,
            "merge_commit_sha": "f" * 40,
            "merged_at": datetime(2026, 8, 3, 23, tzinfo=UTC),
            "merged_by_login": "octocat",
        }
    )

    receipt = application.observe_acceptance("change-a")
    replayed = application.observe_acceptance("change-a")

    assert isinstance(receipt, CompletionReceipt)
    assert replayed == receipt
    assert receipt.accepted_merge_commit == "f" * 40
    assert runtime.change_stage() == DeliveryChangeStage.COMPLETED
    before.assert_unchanged(repository)


def test_github_provider_acceptance_rejects_incomplete_evidence_and_replays_completion(tmp_path: Path) -> None:
    application, runtime, provider, _state, exact_head, _state_root = _awaiting_acceptance_fixture(tmp_path)
    provider_calls_before_acceptance = provider.read_pull_request.call_count
    merge_oid = "e" * 40
    merged_at = "2026-08-03T23:00:00Z"
    rest_response = {
        "number": 7,
        "node_id": "PR_node_7",
        "head": {"ref": "owlbear/change/change-a", "sha": exact_head},
        "base": {"ref": "main", "sha": "b" * 40},
        "title": "Change A",
        "body": (
            "<!-- owlbear-change:change-a -->\n\n"
            "<!-- owlbear-generated:start -->\n"
            "Finalized Change A.\n"
            "<!-- owlbear-generated:end -->\n"
        ),
        "draft": False,
        "state": "closed",
        "merged": True,
        "merge_commit_sha": None,
        "merged_at": merged_at,
        "merged_by": {"login": "octocat"},
    }
    graphql_response = {
        "data": {
            "repository": {
                "nameWithOwner": "example/project",
                "pullRequest": {
                    "number": 7,
                    "headRefOid": exact_head,
                    "baseRefName": "main",
                    "merged": True,
                    "mergedAt": merged_at,
                    "mergeCommit": {"oid": merge_oid},
                },
            },
        },
    }
    incomplete_graphql_response = {
        "data": {
            "repository": {
                "nameWithOwner": "example/project",
                "pullRequest": {
                    "number": 7,
                    "headRefOid": exact_head,
                    "baseRefName": "main",
                    "merged": True,
                    "mergedAt": merged_at,
                    "mergeCommit": None,
                },
            },
        },
    }

    def completed(payload: object) -> subprocess.CompletedProcess[bytes]:
        return subprocess.CompletedProcess(
            args=(),
            returncode=0,
            stdout=json.dumps(payload).encode(),
            stderr=b"",
        )

    runner = Mock(
        side_effect=(
            completed(rest_response),
            completed(incomplete_graphql_response),
            completed(rest_response),
            completed(graphql_response),
        )
    )
    github_provider = GitHubCliPublicationProvider(runner=runner)
    provider.read_pull_request.side_effect = github_provider.read_pull_request

    with pytest.raises(PublicationProviderError) as exc_info:
        application.observe_acceptance("change-a")

    assert exc_info.value.code is PublicationProviderFailureCode.INVALID_RESPONSE
    assert exc_info.value.retry_safe is True
    assert runtime.completion_receipt() is None
    assert runtime.change_stage() == DeliveryChangeStage.AWAITING_MERGE
    assert provider.read_pull_request.call_count == provider_calls_before_acceptance + 1
    assert runner.call_count == 2

    receipt = application.observe_acceptance("change-a")

    assert isinstance(receipt, CompletionReceipt)
    assert receipt.accepted_merge_commit == merge_oid
    assert receipt.finalized_change_head == exact_head
    assert receipt.accepted_merge_commit != receipt.finalized_change_head
    assert runtime.completion_receipt() == receipt
    assert runtime.change_stage() == DeliveryChangeStage.COMPLETED
    provider_calls_after_completion = provider.read_pull_request.call_count
    runner_calls_after_completion = runner.call_count

    replayed = application.observe_acceptance("change-a")

    assert replayed == receipt
    assert provider.read_pull_request.call_count == provider_calls_after_completion
    assert runner.call_count == runner_calls_after_completion


def test_observe_acceptance_completes_once_and_replays_without_provider_io(  # noqa: PLR0915 - scenario covers full replay lifecycle.
    tmp_path: Path,
    user_checkout_snapshot,
) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    repository = tmp_path / "repository"
    runtime = runtimes["change-a"]
    exact_head = coordinator.show("change-a").last_reviewed_commit
    finalization = application.finalize_change(
        "change-a",
        _finalization_request("change-a", exact_head),
    )
    pull_request = PublicationPullRequest(
        repository="example/project",
        number=7,
        node_id="PR_node_7",
        head_branch="owlbear/change/change-a",
        head_sha=exact_head,
        base_branch="main",
        title="Change A",
        body=(
            "<!-- owlbear-change:change-a -->\n\n"
            "<!-- owlbear-generated:start -->\n"
            "Finalized Change A.\n"
            "<!-- owlbear-generated:end -->\n"
        ),
        draft=True,
        state="open",
        merged=False,
    )
    provider = Mock()
    provider.read_repository.return_value = PublicationRepository(
        repository="example/project",
        default_branch="main",
    )
    provider.find_pull_request.return_value = None
    provider.create_draft_pull_request.side_effect = lambda _request: pull_request
    provider.read_pull_request.side_effect = lambda _repository, _number: pull_request
    provider.observe_checks.return_value = PublicationCheckSnapshot(
        repository="example/project",
        number=7,
        head_sha=exact_head,
        checks=(),
    )

    def set_draft_state(request):
        nonlocal pull_request
        pull_request = pull_request.model_copy(update={"draft": request.draft})
        return pull_request

    provider.set_pull_request_draft_state.side_effect = set_draft_state
    publisher = DraftPullRequestPublisher(
        provider,
        repository="example/project",
        target_branch="main",
        state_root=tmp_path / "pull-requests",
    )
    publisher.publish(
        CreateOrReconcileDraftPullRequest(
            change_id="change-a",
            operation_id="create-change-a",
            published_head=exact_head,
            title="Change A",
            generated_summary="Finalized Change A.",
        )
    )
    application._draft_pull_request_publisher = publisher
    checkpoint = runtime.checkpoint_publication_state()
    assert checkpoint.pending_checkpoint is not None
    runtime.record_checkpoint_branch_publication(checkpoint, exact_head)
    runtime.acknowledge_checkpoint_publication(checkpoint.pending_checkpoint, exact_head)
    application.mark_change_ready(
        "change-a",
        MarkChangePullRequestReady(
            change_id="change-a",
            operation_id="ready-change-a",
            finalization_id=finalization.finalization_id,
            exact_head=exact_head,
        ),
    )
    user_checkout_before = user_checkout_snapshot(repository)
    with pytest.raises(DeliveryAcceptanceWaitingError, match="still open and unmerged"):
        application.observe_acceptance("change-a")
    assert runtime.change_disposition() is None
    pull_request = pull_request.model_copy(update={"state": "closed"})
    with pytest.raises(PortfolioApplicationError, match="does not satisfy acceptance authority"):
        application.observe_acceptance("change-a")
    disposition = runtime.change_disposition()
    assert disposition is not None
    assert disposition.kind.value == "acceptance-attention"
    assert disposition.acceptance_reason is DeliveryAcceptanceAttentionReason.CLOSED_UNMERGED
    assert runtime.ready_receipt() is None
    with pytest.raises(PortfolioApplicationError, match="requires attention resolution"):
        application.observe_acceptance("change-a")
    assert application.resolve_change_disposition("change-a", disposition.disposition_id).disposition_id == (
        disposition.disposition_id
    )

    pull_request = pull_request.model_copy(update={"state": "open", "draft": True})
    assert application.reconcile_finalization_head("change-a") == finalization
    application.mark_current_change_ready("change-a")
    pull_request = pull_request.model_copy(
        update={
            "state": "closed",
            "merged": True,
            "merge_commit_sha": "f" * 40,
            "merged_at": datetime(2026, 8, 3, 23, tzinfo=UTC),
            "merged_by_login": "octocat",
        }
    )

    merged_observation = publisher.observe_pull_request(ObserveChangePublicationPullRequest(change_id="change-a"))
    assert merged_observation is not None
    original_latch = runtime.latch_merged_pull_request(merged_observation)
    pull_request = pull_request.model_copy(update={"state": "open", "merged": False, "merged_at": None})
    with pytest.raises(PortfolioApplicationError, match="regressed from the established merged observation"):
        application.observe_acceptance("change-a")
    disposition = runtime.change_disposition()
    assert disposition is not None
    assert disposition.kind.value == "acceptance-attention"
    assert disposition.acceptance_reason is DeliveryAcceptanceAttentionReason.LATCH_REGRESSION
    assert runtime.merged_pull_request_latch() == original_latch
    assert runtime.ready_receipt() is None

    application.resolve_change_disposition("change-a", disposition.disposition_id)
    pull_request = pull_request.model_copy(update={"draft": True})
    assert application.reconcile_finalization_head("change-a") == finalization
    application.mark_change_ready(
        "change-a",
        MarkChangePullRequestReady(
            change_id="change-a",
            operation_id="ready-after-acceptance-regression",
            finalization_id=finalization.finalization_id,
            exact_head=exact_head,
        ),
    )
    pull_request = pull_request.model_copy(
        update={
            "state": "closed",
            "merged": True,
            "merge_commit_sha": "f" * 40,
            "merged_at": datetime(2026, 8, 3, 23, tzinfo=UTC),
            "merged_by_login": "octocat",
        }
    )

    receipt = application.observe_acceptance("change-a")
    provider_calls = provider.read_pull_request.call_count
    replayed = application.observe_acceptance("change-a")
    reconciled = application.reconcile_finalization_head("change-a")

    assert isinstance(receipt, CompletionReceipt)
    assert replayed == receipt
    assert reconciled == finalization
    assert provider.read_pull_request.call_count == provider_calls
    assert runtime.change_stage() == DeliveryChangeStage.COMPLETED
    assert application.list_work_items() == ()
    assert application.list_integration_attention() == ()
    assert receipt.accepted_merge_commit == "f" * 40
    assert receipt.check_observation_ids
    assert receipt.review_receipt_ids == (finalization.review.review_id,)
    retained = application.list_retained_change_worktrees()
    assert len(retained) == 1
    assert retained[0].cleanup_eligible is True
    assert retained[0].cleanup_blocked_reason is None
    user_checkout_before.assert_unchanged(repository)


def test_change_lifecycle_dispositions_delegate_through_application_lock(tmp_path: Path) -> None:
    application, runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    runtime = runtimes["change-a"]

    deferral = application.defer_change("change-a", "Wait for user review")
    assert runtime.change_deferral() == deferral
    assert runtime.change_stage() == DeliveryChangeStage.DEFERRED

    assert application.resume_change("change-a") == deferral
    assert runtime.change_stage() == DeliveryChangeStage.BUILDING

    abandonment = application.abandon_change("change-a", "User stopped the Change")
    assert abandonment.prior_stage == DeliveryChangeStage.BUILDING
    assert runtime.change_stage() == DeliveryChangeStage.ABANDONED
    retained = application.list_retained_change_worktrees()
    assert retained[0].cleanup_eligible is True
    assert retained[0].cleanup_blocked_reason is None


@pytest.mark.parametrize("user_state", _USER_CHECKOUT_STATES)
def test_abandoned_change_worktree_cleanup_preserves_branch_and_replays_receipt(
    tmp_path: Path,
    user_state: str,
    user_checkout_snapshot,
    prepare_user_checkout_state,
    seed_user_checkout_metadata,
) -> None:
    application, runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    repository = application._workspace_manager.repository
    seed_user_checkout_metadata(repository)
    prepare_user_checkout_state(repository, user_state)
    coordination = application._workspace_manager.show("change-a")
    before = user_checkout_snapshot(repository, ("refs/heads/owlbear/change/change-a",))
    application.abandon_change("change-a", "User stopped the Change")

    receipt = application.cleanup_abandoned_change_worktree("change-a")

    assert isinstance(receipt, DeliveryChangeWorktreeCleanup)
    assert receipt.change_id == "change-a"
    assert not coordination.worktree_path.exists()
    assert _git_ref_exists(application._workspace_manager.repository, coordination.branch)
    assert runtimes["change-a"].change_stage() == DeliveryChangeStage.ABANDONED
    assert application.cleanup_abandoned_change_worktree("change-a") == receipt
    assert application.list_retained_change_worktrees() == ()
    before.assert_unchanged(repository)


def test_change_worktree_recovery_recreates_missing_worktree_and_replays_receipt(tmp_path: Path) -> None:
    application, _runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    coordination = application._workspace_manager.show("change-a")
    shutil.rmtree(coordination.worktree_path)

    receipt = application.recover_change_worktree(
        "change-a",
        coordination.last_reviewed_commit,
        confirmed_recovery=True,
    )

    assert isinstance(receipt, DeliveryChangeWorktreeRecovery)
    assert receipt.change_id == "change-a"
    assert receipt.branch_head == coordination.last_reviewed_commit
    assert receipt.recovery_reviewed_head == coordination.last_reviewed_commit
    assert receipt.worktree_path.is_dir()
    assert (
        application.recover_change_worktree(
            "change-a",
            coordination.last_reviewed_commit,
            confirmed_recovery=True,
        )
        == receipt
    )


def test_change_worktree_recovery_rejects_active_writer(tmp_path: Path) -> None:
    application, _runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    coordination = coordinator.show("change-a")
    writer = ChangeWriter(
        attempt_id="attempt-change-a",
        claim_id="claim-change-a",
        actor_id="builder",
        process_id="process-change-a",
        claimed_at="2026-08-04T00:00:00Z",
        job_id=1,
        kind="build",
    )
    coordinator.acquire("change-a", writer)
    shutil.rmtree(coordination.worktree_path)

    with pytest.raises(CoordinationConflictError, match="recovery cannot overlap an active writer"):
        application.recover_change_worktree(
            "change-a",
            coordination.last_reviewed_commit,
            confirmed_recovery=True,
        )


def test_change_worktree_recovery_requires_exact_reviewed_head(tmp_path: Path) -> None:
    application, _runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    coordination = application._workspace_manager.show("change-a")
    shutil.rmtree(coordination.worktree_path)

    with pytest.raises(CoordinationConflictError, match="recovery reviewed head differs"):
        application.recover_change_worktree(
            "change-a",
            "a" * 40,
            confirmed_recovery=True,
        )

    assert not coordination.worktree_path.exists()


def test_change_worktree_recovery_rebuilds_missing_coordination_without_target_mutation(tmp_path: Path) -> None:
    application, _runtimes, _coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    coordination = application._workspace_manager.show("change-a")
    target_head = _git(application._workspace_manager.repository, "rev-parse", "HEAD")
    (state_root / "coordination/changes/change-a.json").unlink()
    shutil.rmtree(coordination.worktree_path)

    receipt = application.recover_change_worktree(
        "change-a",
        coordination.last_reviewed_commit,
        confirmed_recovery=True,
    )

    assert receipt.recovery_reviewed_head == coordination.last_reviewed_commit
    assert application._workspace_manager.show("change-a").last_reviewed_commit == coordination.last_reviewed_commit
    assert _git(application._workspace_manager.repository, "rev-parse", "HEAD") == target_head


def test_change_worktree_recovery_rejects_active_publication_lease(tmp_path: Path) -> None:
    application, _runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    coordination = coordinator.show("change-a")
    now = datetime.now(UTC)
    with coordinator.publication_lock("change-a") as lock:
        coordinator.reserve_publication(
            "change-a",
            PublicationLease(
                operation_id="recovery-publication",
                owner_id="recovery-owner",
                expires_at=(now + timedelta(minutes=5)).isoformat(),
            ),
            lock,
            now=now.isoformat(),
        )
    shutil.rmtree(coordination.worktree_path)

    with pytest.raises(CoordinationConflictError, match="active publication lease"):
        application.recover_change_worktree(
            "change-a",
            coordination.last_reviewed_commit,
            confirmed_recovery=True,
        )

    assert not coordination.worktree_path.exists()


def test_change_worktree_cleanup_requires_terminal_authority(tmp_path: Path) -> None:
    application, _runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )

    with pytest.raises(PortfolioApplicationError, match="requires an abandoned or completed Change"):
        application.cleanup_change_worktree("change-a")


def test_abandoned_change_worktree_cleanup_surfaces_lost_worktree_attention(tmp_path: Path) -> None:
    application, _runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    coordination = application._workspace_manager.show("change-a")
    application.abandon_change("change-a", "User stopped the Change")
    _git(
        application._workspace_manager.repository,
        "worktree",
        "remove",
        "--force",
        str(coordination.worktree_path),
    )

    with pytest.raises(ChangeWorktreeAttentionError) as raised:
        application.cleanup_abandoned_change_worktree("change-a")

    assert ChangeWorktreeAttentionCode.WORKTREE_MISSING in raised.value.attention


def test_retained_inventory_turns_completion_conflict_into_typed_attention(tmp_path: Path) -> None:
    application, runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    runtime = runtimes["change-a"]

    with patch.object(
        runtime,
        "completion_receipt",
        side_effect=DeliveryRuntimeConflictError("completion receipt is inconsistent"),
    ):
        row = application.list_retained_change_worktrees()[0]

    assert row.cleanup_eligible is False
    assert row.cleanup_blocked_reason is DeliveryRetainedWorktreeCleanupBlockReason.COMPLETION_STATE_INCONSISTENT


def test_retained_inventory_blocks_active_writer_and_publication_lease(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    runtime = runtimes["change-a"]
    with (
        patch.object(runtime, "change_stage", return_value=DeliveryChangeStage.COMPLETED),
        patch.object(runtime, "completion_receipt", return_value=object()),
    ):
        writer = ChangeWriter(
            attempt_id="attempt-change-a",
            claim_id="claim-change-a",
            actor_id="builder",
            process_id="process-change-a",
            claimed_at="2026-08-04T00:00:00Z",
            job_id=1,
            kind="build",
        )
        coordinator.acquire("change-a", writer)
        writer_row = application.list_retained_change_worktrees()[0]
        assert writer_row.cleanup_blocked_reason is DeliveryRetainedWorktreeCleanupBlockReason.ACTIVE_WRITER

    released = coordinator.release("change-a", "claim-change-a")
    assert released.writer is None
    with coordinator.publication_lock("change-a") as lock:
        coordinator.reserve_publication(
            "change-a",
            PublicationLease(
                operation_id="publication-change-a",
                owner_id="owner-change-a",
                expires_at="2026-08-04T00:05:00Z",
            ),
            lock,
            now="2026-08-04T00:00:00Z",
        )
    with (
        patch.object(runtime, "change_stage", return_value=DeliveryChangeStage.COMPLETED),
        patch.object(runtime, "completion_receipt", return_value=object()),
    ):
        lease_row = application.list_retained_change_worktrees()[0]

    assert lease_row.cleanup_blocked_reason is DeliveryRetainedWorktreeCleanupBlockReason.ACTIVE_PUBLICATION_LEASE


def test_retained_inventory_reports_orphans_nonterminal_and_worktree_attention(tmp_path: Path) -> None:
    application, runtimes, _coordinator, state_root = _portfolio(
        tmp_path,
        {
            "change-a": DeliveryStage.PLANNING,
            "change-b": DeliveryStage.COMPLETED,
            "change-c": DeliveryStage.PLANNING,
        },
    )
    shutil.rmtree(state_root / "changes/change-a")
    attention_coordination = application._workspace_manager.show("change-b")
    _git(
        application._workspace_manager.repository,
        "worktree",
        "remove",
        "--force",
        str(attention_coordination.worktree_path),
    )
    runtime = runtimes["change-b"]
    with (
        patch.object(runtime, "change_stage", return_value=DeliveryChangeStage.COMPLETED),
        patch.object(runtime, "completion_receipt", return_value=object()),
    ):
        rows = application.list_retained_change_worktrees()

    by_id = {row.change_id: row for row in rows}
    assert by_id["change-a"].orphan is True
    assert by_id["change-a"].cleanup_blocked_reason is DeliveryRetainedWorktreeCleanupBlockReason.ORPHAN
    assert by_id["change-b"].orphan is False
    assert by_id["change-b"].cleanup_blocked_reason is DeliveryRetainedWorktreeCleanupBlockReason.WORKTREE_ATTENTION
    assert ChangeWorktreeAttentionCode.WORKTREE_MISSING in by_id["change-b"].attention
    assert by_id["change-c"].cleanup_blocked_reason is DeliveryRetainedWorktreeCleanupBlockReason.NONTERMINAL


def test_portfolio_operating_view_recommends_creation_when_no_work_exists(tmp_path: Path) -> None:
    application, _runtimes, _coordinator, _state_root = _portfolio(tmp_path, {})

    view = application.portfolio_operating_view()

    assert view.unfinished_change_count == 0
    assert tuple(item.kind.value for item in view.guidance) == ("create-change",)


def test_portfolio_operating_view_recommends_resuming_unadmitted_design(tmp_path: Path) -> None:
    application, _runtimes, _coordinator, _state_root = _portfolio(tmp_path, {})
    application.create_design_session("draft-change", b"intent\n", b"design\n")

    view = application.portfolio_operating_view()

    assert view.unfinished_change_count == 0
    assert view.statuses[0].change_id == "draft-change"
    assert view.statuses[0].admission.value == "unadmitted"
    assert view.statuses[0].stage == DeliveryChangeStage.DESIGN
    assert view.statuses[0].actionable_runtime is False
    assert view.statuses[0].diagnostic_code is None
    assert view.statuses[0].diagnostic_detail is None
    assert view.draft_design_change_ids == ("draft-change",)
    assert tuple(item.kind.value for item in view.guidance) == ("resume-design",)


def test_portfolio_reader_reconciles_admitted_change_after_warm_start(tmp_path: Path) -> None:
    reader, _reader_runtimes, _reader_coordinator, state_root = _portfolio(tmp_path, {})
    writer, _writer_coordinator, _writer_manager = _reopen_portfolio(tmp_path, state_root, {})
    intent = b"""# Admitted Delivery

```yaml target-contract
kind: commitment
id: COM-001
class: agreed-path
provenance: characterization
statement: Preserve source-bound admission.
```

```yaml target-contract
kind: outcome
id: OUT-001
title: Observe admission
promise: Make persisted admission observable.
acceptance: [Admission is observable.]
commitments: [COM-001]
dependencies: []
```
"""
    writer.create_design_session("admitted-change", intent, b"# Architecture\n")
    admitted = writer.admit_delivery_change(DeliveryAdmissionRequest(change_id="admitted-change", active_claim_ids=()))

    delivery_root = state_root / "changes" / "admitted-change"
    persisted_frontier = DeliveryFrontier.model_validate_json((delivery_root / "frontier.json").read_bytes())
    persisted_receipt = json.loads((delivery_root / "admission.json").read_bytes())
    assert persisted_frontier == admitted.frontier
    assert persisted_receipt["receipt_id"] == admitted.receipt.receipt_id

    view = reader.portfolio_read_view()

    assert tuple(group.change_id for group in view.groups) == ("admitted-change",)
    assert tuple(item.work_item_id for item in view.groups[0].items) == (
        *tuple(outcome.outcome_id for outcome in admitted.contract.outcomes),
        "admitted-change",
    )
    assert view.groups[0].outcome_total == len(admitted.contract.outcomes)
    assert view.groups[0].outcome_completed == 0
    assert view.operating.unfinished_change_count == 1
    assert view.operating.statuses[0].change_id == "admitted-change"
    assert view.operating.statuses[0].admission.value == "admitted"
    assert view.operating.statuses[0].stage == DeliveryChangeStage.BUILDING
    assert view.operating.statuses[0].actionable_runtime is True
    assert view.operating.statuses[0].diagnostic_code is None
    assert view.groups[0].items[0].progress.label == "Task plan not published"
    assert view.operating.draft_design_change_ids == ()
    assert view.operating.design_required_change_ids == ()
    assert tuple(item.kind.value for item in view.operating.guidance) == ("start-orchestration",)


def test_warm_reader_reconciles_change_admitted_by_second_application(tmp_path: Path) -> None:
    reader, _reader_runtimes, _reader_coordinator, state_root = _portfolio(tmp_path, {})
    reader.portfolio_read_view()
    writer, writer_coordinator, writer_manager = _reopen_portfolio(tmp_path, state_root, {})
    intent = b"""# Admitted Delivery

```yaml target-contract
kind: commitment
id: COM-001
class: agreed-path
provenance: characterization
statement: Preserve source-bound admission.
```

```yaml target-contract
kind: outcome
id: OUT-001
title: Observe admission
promise: Make persisted admission observable.
acceptance: [Admission is observable.]
commitments: [COM-001]
dependencies: []
```
"""
    writer.create_design_session("late-change", intent, b"# Architecture\n")
    admitted = writer.admit_delivery_change(DeliveryAdmissionRequest(change_id="late-change", active_claim_ids=()))
    exact_head = writer_coordinator.show("late-change").last_reviewed_commit
    _runtime(state_root, admitted.contract, writer_manager, DeliveryStage.COMPLETED, exact_head)
    finalization = writer.finalize_change("late-change", _finalization_request("late-change", exact_head))
    writer_runtime = writer._runtimes["late-change"]
    writer_runtime.record_publication_identity(
        DeliveryChangePublicationIdentity(
            change_id="late-change",
            repository="example/project",
            number=7,
            node_id="PR_node_7",
            head_sha=exact_head,
        )
    )
    ready_payload = {
        "schema_version": 1,
        "operation_id": "ready-late-change",
        "change_id": "late-change",
        "finalization_id": finalization.finalization_id,
        "repository": "example/project",
        "number": 7,
        "node_id": "PR_node_7",
        "head_sha": exact_head,
        "draft": False,
        "observed_at": datetime(2026, 8, 11, 14, tzinfo=UTC),
        "provider_evidence_digest": "5" * 64,
    }
    writer_runtime.mark_awaiting_merge(
        PullRequestReadyReceipt(
            receipt_id=_receipt_id({**ready_payload, "observed_at": "2026-08-11T14:00:00Z"}),
            **ready_payload,
        )
    )

    outcomes = reader.reconcile_awaiting_acceptance()

    assert len(outcomes) == 1
    assert outcomes[0].change_id == "late-change"
    assert outcomes[0].status.value == "provider-unavailable"


def test_portfolio_reader_replaces_changed_runtime_without_active_claim(tmp_path: Path) -> None:
    application, _runtimes, _coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.PLANNING},
    )
    application.portfolio_read_view()
    previous_runtime = application._runtimes["change-a"]
    contract_path = state_root / "changes/change-a/contract.json"
    frontier_path = state_root / "changes/change-a/frontier.json"
    current_frontier = DeliveryFrontier.model_validate_json(frontier_path.read_bytes())
    replacement = previous_runtime.contract.model_copy(update={"title": "Replacement authority \u00e9"})
    contract_path.write_bytes(_canonical(replacement))
    (state_root / "changes/change-a/admission.json").write_bytes(
        _canonical(
            _admission_receipt(
                replacement,
                current_frontier,
                _coordinator.show("change-a").last_reviewed_commit,
            )
        )
    )
    before = _file_bytes(state_root)

    view = application.portfolio_read_view()

    assert application._runtimes["change-a"] is not previous_runtime
    assert view.groups[0].title == "Replacement authority \u00e9"
    assert _file_bytes(state_root) == before


def test_portfolio_reader_defers_active_runtime_replacement_and_blocks_mutation(tmp_path: Path) -> None:
    application, _runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.PLANNING},
    )
    application.acquire_frontier_work()
    previous_runtime = application._runtimes["change-a"]
    contract_path = state_root / "changes/change-a/contract.json"
    frontier_path = state_root / "changes/change-a/frontier.json"
    current_frontier = DeliveryFrontier.model_validate_json(frontier_path.read_bytes())
    replacement = previous_runtime.contract.model_copy(update={"title": "Active replacement"})
    contract_path.write_bytes(_canonical(replacement))
    (state_root / "changes/change-a/admission.json").write_bytes(
        _canonical(_admission_receipt(replacement, current_frontier, coordinator.show("change-a").last_reviewed_commit))
    )

    view = application.portfolio_read_view()

    assert application._runtimes["change-a"] is previous_runtime
    assert view.groups[0].title == previous_runtime.contract.title
    with pytest.raises(DeliveryRuntimeReconciliationError) as exc_info:
        application.defer_change("change-a", "runtime replacement requires reconciliation")
    assert exc_info.value.code == "ERR_DELIVERY_RUNTIME_RECONCILIATION"
    assert exc_info.value.retry_safe is True


@pytest.mark.parametrize("mutation", ["malformed", "mid-write"])
def test_portfolio_reader_retains_prior_runtime_and_blocks_mutation_for_unavailable_entry(
    tmp_path: Path,
    mutation: str,
) -> None:
    application, _runtimes, _coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.PLANNING},
    )
    application.portfolio_read_view()
    previous_runtime = application._runtimes["change-a"]
    frontier_path = state_root / "changes/change-a/frontier.json"
    if mutation == "malformed":
        frontier_path.write_bytes(b"not-json\n")
    else:
        frontier_path.unlink()
    before = _file_bytes(state_root)

    view = application.portfolio_read_view()

    assert application._runtimes["change-a"] is previous_runtime
    assert view.groups[0].title == previous_runtime.contract.title
    assert view.operating.unfinished_change_count == 1
    assert view.operating.draft_design_change_ids == ()
    status = next(item for item in view.operating.statuses if item.change_id == "change-a")
    assert status.admission.value == "admitted"
    assert status.actionable_runtime is False
    assert status.diagnostic_code == "runtime_unavailable"
    assert status.diagnostic_detail is not None
    assert len(status.diagnostic_detail) <= 240
    assert application._discovered_changes["change-a"].diagnostic_code == "runtime_unavailable"
    with pytest.raises(DeliveryRuntimeReconciliationError) as exc_info:
        application.defer_change("change-a", "runtime entry requires retry")
    assert exc_info.value.retry_safe is True
    assert _file_bytes(state_root) == before


def test_portfolio_operating_view_counts_design_reentry_as_intervention(tmp_path: Path) -> None:
    application, _runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.DESIGN},
    )

    view = application.portfolio_operating_view()

    assert tuple(item.item_key for item in view.interventions) == ("outcome:OUT-001",)
    assert view.statuses[0].admission.value == "admitted"
    assert view.statuses[0].stage == DeliveryChangeStage.DESIGN
    assert view.statuses[0].actionable_runtime is True
    assert view.design_required_change_ids == ("change-a",)
    assert view.draft_design_change_ids == ()
    assert tuple(item.kind.value for item in view.guidance) == ("intervene", "resume-design")


def test_portfolio_operating_view_recommends_orchestration_for_unclaimed_work(tmp_path: Path) -> None:
    application, _runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.PLANNING, "change-b": DeliveryStage.PLANNING},
    )

    view = application.portfolio_operating_view()

    assert len(view.queued_for_orchestration) == 2
    assert tuple(item.kind.value for item in view.guidance) == ("start-orchestration",)


def test_portfolio_claim_suppresses_second_orchestration_recommendation(tmp_path: Path) -> None:
    application, _runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.PLANNING, "change-b": DeliveryStage.PLANNING},
        execution_capacity=1,
    )
    acquired = application.acquire_frontier_work()
    assert len(acquired.launch_packages) == 1

    view = application.portfolio_operating_view()

    assert len(view.claimed) == 1
    assert len(view.queued_for_orchestration) == 1
    assert tuple(item.kind.value for item in view.guidance) == ("work-underway",)


def test_portfolio_keeps_deferred_change_visible_without_orchestration_queue(tmp_path: Path) -> None:
    application, _runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.PLANNING},
    )
    application.defer_change("change-a", "wait for user review")

    view = application.portfolio_read_view()

    assert tuple(group.lifecycle.value for group in view.groups) == ("deferred",)
    assert view.operating.unfinished_change_count == 1
    assert view.operating.queued_for_orchestration == ()
    assert tuple(item.kind.value for item in view.operating.guidance) == ("intervene",)


def test_portfolio_projects_change_checkpoint_publication_state(tmp_path: Path) -> None:
    application, runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.PLANNING},
    )

    state = application.show_change_checkpoint_publication("change-a")

    assert state == runtimes["change-a"].checkpoint_publication_state()
    assert state.change_id == "change-a"
    assert state.published_head is None
    assert state.pending_checkpoint is None


def test_reconcile_first_checkpoint_publishes_branch_creates_pr_and_drains(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    head = coordinator.show("change-a").last_reviewed_commit
    pending = DeliveryPendingCheckpoint(
        head=head,
        triggers=(
            DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK),
            DeliveryCheckpointTrigger(
                kind=DeliveryCheckpointTriggerKind.VERIFIED_OUTCOME,
                outcome_id="OUT-001",
            ),
        ),
    )
    _set_checkpoint(runtimes["change-a"], state_root, pending)
    branch_publisher = Mock()
    branch_publisher.publish.side_effect = _requested_branch_receipt
    pull_request_publisher = Mock()
    pull_request_publisher.publish.side_effect = lambda request: _draft_receipt(request.published_head)
    pull_request_publisher.update_generated_summary.side_effect = lambda request: _summary_receipt(
        request.published_head
    )
    application._change_branch_publisher = branch_publisher
    application._draft_pull_request_publisher = pull_request_publisher

    result = application.reconcile_change_checkpoint("change-a")
    replayed = application.reconcile_change_checkpoint("change-a")

    assert result.reconciled
    snapshot = coordinator.show("change-a").design_package_snapshot
    assert snapshot is not None
    assert result.state.published_head == snapshot.snapshot_head
    assert result.state.pending_checkpoint is None
    assert replayed.reconciled
    assert replayed.attempted_head is None
    assert branch_publisher.publish.call_count == 1
    assert pull_request_publisher.publish.call_count == 1
    assert pull_request_publisher.update_generated_summary.call_count == 1
    request = pull_request_publisher.publish.call_args.args[0]
    assert request.published_head == snapshot.snapshot_head
    assert "## Goal" in request.generated_summary
    assert "## Intent" in request.generated_summary
    assert "## Promised Outcomes" in request.generated_summary
    assert "Promised result: Return one bounded launch package." in request.generated_summary
    assert "Outcome `OUT-001` verified" in request.generated_summary
    assert "Outcomes complete: 1 of 1" in request.generated_summary
    history = runtimes["change-a"].publication_history()
    assert history is not None
    assert history.current.number == 7
    assert history.current.head_sha == snapshot.snapshot_head


def test_background_checkpoint_failure_persists_error_and_waits_before_retry(tmp_path: Path) -> None:
    current = [datetime(2026, 8, 4, tzinfo=UTC)]

    def clock() -> str:
        return current[0].isoformat()

    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
        clock=clock,
    )
    head = coordinator.show("change-a").last_reviewed_commit
    pending = DeliveryPendingCheckpoint(
        head=head,
        triggers=(
            DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.VERIFIED_OUTCOME, outcome_id="OUT-001"),
        ),
    )
    _set_checkpoint(runtimes["change-a"], state_root, pending)
    branch_publisher = Mock()
    branch_publisher.publish.side_effect = PublicationProviderError(
        PublicationProviderFailureCode.UNAVAILABLE,
        "publish_change_branch",
        "Provider unavailable while publishing the Change branch.",
        retry_safe=True,
    )
    application._change_branch_publisher = branch_publisher
    application._draft_pull_request_publisher = Mock()

    first = application.reconcile_pending_checkpoints()

    assert len(first) == 1
    assert first[0].error_code == PublicationProviderFailureCode.UNAVAILABLE
    recorded = first[0].state.pending_checkpoint
    assert recorded is not None
    assert recorded.attempt_count == 1
    assert recorded.last_attempted_at == current[0]
    assert recorded.last_error_detail == "Provider unavailable while publishing the Change branch."
    assert application.reconcile_pending_checkpoints() == ()

    current[0] += timedelta(seconds=5)
    second = application.reconcile_pending_checkpoints()

    assert len(second) == 1
    assert second[0].state.pending_checkpoint is not None
    assert second[0].state.pending_checkpoint.attempt_count == 2
    assert branch_publisher.publish.call_count == 2


def test_background_checkpoint_selection_excludes_review_required_merge(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    head = coordinator.show("change-a").last_reviewed_commit
    target_sync = ChangeTargetSyncReceipt.create(
        operation_id="review-required-sync",
        change_id="change-a",
        integration_target="main",
        expected_target="2" * 40,
        target_head="2" * 40,
        change_head_before=head,
        merged_head=head,
        merge_commit=False,
        review_required=True,
    )
    pending = DeliveryPendingCheckpoint(
        head=head,
        triggers=(DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.EXPLICIT),),
    )
    path = state_root / "changes/change-a/frontier.json"
    frontier = DeliveryFrontier.model_validate_json(runtimes["change-a"].frontier_bytes())
    path.write_bytes(
        _canonical(frontier.model_copy(update={"target_sync_receipt": target_sync, "pending_checkpoint": pending}))
    )
    branch_publisher = Mock()
    application._change_branch_publisher = branch_publisher
    application._draft_pull_request_publisher = Mock()

    result = application.reconcile_pending_checkpoints()

    assert result == ()
    branch_publisher.publish.assert_not_called()


def test_reconcile_checkpoint_reports_bounded_escaped_automation_paths(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    head = coordinator.show("change-a").last_reviewed_commit
    pending = DeliveryPendingCheckpoint(
        head=head,
        triggers=(DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK),),
    )
    _set_checkpoint(runtimes["change-a"], state_root, pending)
    branch_publisher = Mock()
    branch_publisher.publish.side_effect = _requested_branch_receipt
    pull_request_publisher = Mock()
    pull_request_publisher.publish.side_effect = lambda request: _draft_receipt(request.published_head)
    pull_request_publisher.update_generated_summary.side_effect = lambda request: _summary_receipt(
        request.published_head
    )
    application._change_branch_publisher = branch_publisher
    application._draft_pull_request_publisher = pull_request_publisher
    long_path = ".github/workflows/" + ("x" * 300) + ".yml"

    with patch.object(
        application._workspace_manager,
        "repository_automation_paths",
        return_value=(".github/workflows/<run>`\nname.yml", long_path),
    ):
        result = application.reconcile_change_checkpoint("change-a")

    assert result.reconciled
    create_request = pull_request_publisher.publish.call_args.args[0]
    update_request = pull_request_publisher.update_generated_summary.call_args.args[0]
    summary = create_request.generated_summary
    assert summary == update_request.generated_summary
    assert "### Repository automation changed" in summary
    assert "<code>.github/workflows/&lt;run&gt;&#96;\\nname.yml</code>" in summary
    assert "x" * 300 not in summary
    assert summary.count("<code>") == 2


def test_reconcile_checkpoint_retains_attention_when_publication_baseline_is_unknown(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    head = coordinator.show("change-a").last_reviewed_commit
    pending = DeliveryPendingCheckpoint(
        head=head,
        triggers=(DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK),),
    )
    _set_checkpoint(runtimes["change-a"], state_root, pending)
    coordination = coordinator.show("change-a")
    payload = coordination.model_dump(mode="json")
    payload.pop("publication_base_head")
    (state_root / "coordination/changes/change-a.json").write_text(json.dumps(payload), encoding="utf-8")
    branch_publisher = Mock()
    pull_request_publisher = Mock()
    application._change_branch_publisher = branch_publisher
    application._draft_pull_request_publisher = pull_request_publisher

    with pytest.raises(PublicationBaselineUnavailableError):
        application.reconcile_change_checkpoint("change-a")

    assert branch_publisher.publish.call_count == 0
    assert pull_request_publisher.publish.call_count == 0
    assert pull_request_publisher.update_generated_summary.call_count == 0
    retained = runtimes["change-a"].change_disposition()
    assert retained is not None
    assert retained.kind.value == "publication-attention"
    retained = runtimes["change-a"].checkpoint_publication_state().pending_checkpoint
    assert retained is not None
    assert retained.head == pending.head
    assert retained.triggers == pending.triggers
    assert retained.attempt_count == 1
    assert retained.last_error_code == "ERR_PUBLICATION_BASELINE_UNAVAILABLE"
    assert retained.last_error_detail is not None


def test_reconcile_checkpoint_preserves_baseline_error_when_attention_conflicts(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    head = coordinator.show("change-a").last_reviewed_commit
    pending = DeliveryPendingCheckpoint(
        head=head,
        triggers=(DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK),),
    )
    _set_checkpoint(runtimes["change-a"], state_root, pending)
    coordination = coordinator.show("change-a")
    payload = coordination.model_dump(mode="json")
    payload.pop("publication_base_head")
    (state_root / "coordination/changes/change-a.json").write_text(json.dumps(payload), encoding="utf-8")
    runtimes["change-a"].capture_publication_attention(
        datetime(2026, 8, 12, tzinfo=UTC),
        ("existing-publication-attention",),
    )
    branch_publisher = Mock()
    pull_request_publisher = Mock()
    application._change_branch_publisher = branch_publisher
    application._draft_pull_request_publisher = pull_request_publisher

    with pytest.raises(PublicationBaselineUnavailableError):
        application.reconcile_change_checkpoint("change-a")

    assert branch_publisher.publish.call_count == 0
    assert pull_request_publisher.publish.call_count == 0
    retained = runtimes["change-a"].change_disposition()
    assert retained is not None
    assert retained.diagnostics == ("existing-publication-attention",)


def test_recover_publication_baseline_requires_confirmation_and_preserves_attention(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    coordination = coordinator.show("change-a")
    payload = coordination.model_dump(mode="json")
    payload.pop("publication_base_head")
    (state_root / "coordination/changes/change-a.json").write_text(json.dumps(payload), encoding="utf-8")
    runtime = runtimes["change-a"]
    attention = runtime.capture_publication_attention(
        datetime(2026, 8, 12, tzinfo=UTC),
        ("publication-baseline-unavailable",),
    )

    with pytest.raises(PortfolioApplicationError, match="explicit confirmation"):
        application.recover_publication_baseline(
            "change-a",
            coordination.last_reviewed_commit,
            coordination.target_head,
            "recover-baseline",
        )

    receipt = application.recover_publication_baseline(
        "change-a",
        coordination.last_reviewed_commit,
        coordination.target_head,
        "recover-baseline",
        confirmed_recovery=True,
    )

    assert receipt.change_id == "change-a"
    assert coordinator.show("change-a").publication_base_head == coordination.target_head
    assert runtime.change_disposition() == attention


def test_supersede_current_publication_preflights_baseline_before_provider_history(tmp_path: Path) -> None:
    application, _runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    coordination = coordinator.show("change-a")
    payload = coordination.model_dump(mode="json")
    payload.pop("publication_base_head")
    (state_root / "coordination/changes/change-a.json").write_text(json.dumps(payload), encoding="utf-8")
    provider = Mock()
    application._draft_pull_request_publisher = provider

    with pytest.raises(PublicationBaselineUnavailableError):
        application.supersede_current_publication("change-a", "supersede-current")

    provider.read_publication_history.assert_not_called()


def test_later_checkpoint_reports_cumulative_automation_paths(
    tmp_path: Path,
) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    coordination = coordinator.show("change-a")
    workflow_directory = coordination.worktree_path / ".github/workflows"
    workflow_directory.mkdir(parents=True)
    first_head = _commit_reviewed_head(
        application,
        coordination,
        ".github/workflows/first.yml",
        "name: first\n",
        "first automation checkpoint",
    )
    first_pending = DeliveryPendingCheckpoint(
        head=first_head,
        triggers=(DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK),),
    )
    _set_checkpoint(runtimes["change-a"], state_root, first_pending)
    branch_publisher = Mock()
    branch_publisher.publish.side_effect = _requested_branch_receipt
    pull_request_publisher = Mock()
    pull_request_publisher.publish.side_effect = lambda request: _draft_receipt(request.published_head)
    pull_request_publisher.update_generated_summary.side_effect = lambda request: _summary_receipt(
        request.published_head
    )
    application._change_branch_publisher = branch_publisher
    application._draft_pull_request_publisher = pull_request_publisher

    application.reconcile_change_checkpoint("change-a")

    second_head = _commit_reviewed_head(
        application,
        coordination,
        ".github/workflows/second.yml",
        "name: second\n",
        "second automation checkpoint",
    )
    second_pending = DeliveryPendingCheckpoint(
        head=second_head,
        triggers=(
            DeliveryCheckpointTrigger(
                kind=DeliveryCheckpointTriggerKind.VERIFIED_OUTCOME,
                outcome_id="OUT-001",
            ),
        ),
    )
    first_snapshot = coordinator.show("change-a").design_package_snapshot
    assert first_snapshot is not None
    _set_checkpoint(runtimes["change-a"], state_root, second_pending, published_head=first_snapshot.snapshot_head)
    branch_publisher.publish.side_effect = None
    branch_publisher.publish.return_value = _branch_receipt(second_head, first_snapshot.snapshot_head)
    pull_request_publisher.update_generated_summary.return_value = _summary_receipt(second_head)

    result = application.reconcile_change_checkpoint("change-a")

    assert result.reconciled
    summary = pull_request_publisher.update_generated_summary.call_args.args[0].generated_summary
    assert "<code>.github/workflows/first.yml</code>" in summary
    assert "<code>.github/workflows/second.yml</code>" in summary


def test_supersede_publication_binds_git_provider_and_runtime_history(  # noqa: PLR0915 - scenario covers provider history.
    tmp_path: Path,
) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    runtime = runtimes["change-a"]
    coordination = coordinator.show("change-a")
    predecessor_head = coordination.last_reviewed_commit
    predecessor = _draft_receipt(predecessor_head)
    predecessor_identity = DeliveryChangePublicationIdentity(
        change_id="change-a",
        repository=predecessor.repository,
        number=predecessor.number,
        node_id=predecessor.node_id,
        head_sha=predecessor.head_sha,
    )
    runtime.record_publication_identity(predecessor_identity)
    runtime.capture_publication_attention(
        datetime(2026, 8, 12, tzinfo=UTC),
        ("published history requires correction",),
        publication_identity=predecessor_identity,
    )

    (coordination.worktree_path / ".github/workflows").mkdir(parents=True)
    (coordination.worktree_path / ".github/workflows/successor.yml").write_text("successor\n", encoding="utf-8")
    _git(coordination.worktree_path, "add", ".github/workflows/successor.yml")
    _git(coordination.worktree_path, "commit", "-m", "successor publication")
    superseding_head = _git(coordination.worktree_path, "rev-parse", "HEAD")
    application._workspace_manager.record_reviewed("change-a", superseding_head)

    operation_id = "supersede-change-a"
    successor_branch = "owlbear/change/change-a+s1"
    git_receipt = ChangeBranchSupersessionReceipt(
        receipt_id="5" * 64,
        operation_id=operation_id,
        change_id="change-a",
        remote="origin",
        predecessor_branch=predecessor.head_branch,
        predecessor_head=predecessor.head_sha,
        successor_branch=successor_branch,
        superseding_head=superseding_head,
        target_branch="main",
    )
    successor = _draft_receipt(
        superseding_head,
        number=8,
        operation_id=operation_id,
        head_branch=successor_branch,
    )
    provider_payload = {
        "schema_version": 1,
        "operation_id": operation_id,
        "change_id": "change-a",
        "predecessor_receipt_id": predecessor.receipt_id,
        "predecessor_branch": predecessor.head_branch,
        "predecessor_head": predecessor.head_sha,
        "successor_receipt_id": successor.receipt_id,
        "successor_branch": successor.head_branch,
        "superseding_head": successor.head_sha,
        "repository": successor.repository,
        "successor_number": successor.number,
        "successor_node_id": successor.node_id,
        "base_branch": successor.base_branch,
        "provider_evidence_digest": successor.provider_evidence_digest,
        "predecessor_publication": predecessor.model_dump(mode="json"),
        "successor_publication": successor.model_dump(mode="json"),
    }
    provider_receipt = DraftPullRequestSupersessionReceipt(
        receipt_id=_receipt_id(provider_payload),
        **provider_payload,
    )
    initial_provider_history = _draft_history((predecessor,), (None,))
    successor_provider_history = _draft_history((predecessor, successor), (None, predecessor.receipt_id))
    branch_publisher = Mock()
    branch_publisher.supersede.return_value = git_receipt
    pull_request_publisher = Mock()
    pull_request_publisher.target_branch = "main"
    pull_request_publisher.read_publication_history.side_effect = (
        initial_provider_history,
        successor_provider_history,
        successor_provider_history,
    )
    pull_request_publisher.supersede.return_value = provider_receipt
    application._change_branch_publisher = branch_publisher
    application._draft_pull_request_publisher = pull_request_publisher

    receipt = application.supersede_publication("change-a", predecessor.receipt_id, operation_id)
    replayed = application.supersede_publication("change-a", predecessor.receipt_id, operation_id)

    assert receipt == replayed
    assert (receipt.git_supersession, receipt.provider_supersession) == (git_receipt, provider_receipt)
    assert receipt.publication_history.current.number == 8
    assert len(receipt.publication_history.publications) == 2
    assert runtimes["change-a"].publication_history() == receipt.publication_history
    assert branch_publisher.supersede.call_count == 2
    assert pull_request_publisher.supersede.call_count == 2
    git_request = branch_publisher.supersede.call_args.args[0]
    assert git_request.expected_published_branch == predecessor.head_branch
    assert git_request.expected_published_head == predecessor.head_sha
    assert git_request.superseding_head == superseding_head
    provider_request = pull_request_publisher.supersede.call_args.args[0]
    assert provider_request.expected_predecessor_receipt_id == predecessor.receipt_id
    assert provider_request.successor_branch == successor_branch
    assert provider_request.superseding_head == superseding_head
    assert "## Goal" in provider_request.generated_summary
    assert "## Intent" in provider_request.generated_summary
    assert "## Promised Outcomes" in provider_request.generated_summary
    assert (
        f"Publication supersedes provider publication `{predecessor.receipt_id}`" in provider_request.generated_summary
    )
    assert "### Repository automation changed" in provider_request.generated_summary
    assert "<code>.github/workflows/successor.yml</code>" in provider_request.generated_summary

    _commit_reviewed_head(application, coordination, "later.txt", "later\n", "later reviewed head")

    with pytest.raises(PortfolioApplicationError, match="replay requires the stored successor head"):
        application.supersede_publication("change-a", predecessor.receipt_id, operation_id)

    assert (branch_publisher.supersede.call_count, pull_request_publisher.supersede.call_count) == (2, 2)


def test_supersede_current_publication_resolves_provider_receipt_before_delegating(tmp_path: Path) -> None:
    application, _runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    predecessor = _draft_receipt("3" * 40)
    provider = Mock()
    provider.read_publication_history.return_value = _draft_history((predecessor,), (None,))
    application._draft_pull_request_publisher = provider
    expected = object()

    with patch.object(application, "supersede_publication", return_value=expected) as supersede:
        result = application.supersede_current_publication("change-a", "supersede-current")

    assert result is expected
    provider.read_publication_history.assert_called_once_with(ReadChangePublicationHistory(change_id="change-a"))
    supersede.assert_called_once_with("change-a", predecessor.receipt_id, "supersede-current")


def test_supersede_publication_requires_attention_bound_to_runtime_publication(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    runtime = runtimes["change-a"]
    predecessor_head = coordinator.show("change-a").last_reviewed_commit
    predecessor = _draft_receipt(predecessor_head)
    runtime.record_publication_identity(
        DeliveryChangePublicationIdentity(
            change_id="change-a",
            repository=predecessor.repository,
            number=predecessor.number,
            node_id=predecessor.node_id,
            head_sha=predecessor.head_sha,
        )
    )
    runtime.capture_publication_attention(
        datetime(2026, 8, 12, tzinfo=UTC),
        ("published history requires correction",),
    )
    branch_publisher = Mock()
    pull_request_publisher = Mock()
    pull_request_publisher.target_branch = "main"
    application._change_branch_publisher = branch_publisher
    application._draft_pull_request_publisher = pull_request_publisher

    with pytest.raises(PortfolioApplicationError, match="attention does not retain"):
        application.supersede_publication("change-a", predecessor.receipt_id, "supersede-change-a")

    branch_publisher.supersede.assert_not_called()
    pull_request_publisher.read_publication_history.assert_not_called()
    assert runtime.publication_history() is not None
    assert len(runtime.publication_history().publications) == 1


def test_supersede_publication_preserves_finalization_when_provider_fails(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    runtime = runtimes["change-a"]
    predecessor_head = coordinator.show("change-a").last_reviewed_commit
    finalization = application.finalize_change("change-a", _finalization_request("change-a", predecessor_head))
    predecessor = _draft_receipt(predecessor_head)
    predecessor_identity = DeliveryChangePublicationIdentity(
        change_id="change-a",
        repository=predecessor.repository,
        number=predecessor.number,
        node_id=predecessor.node_id,
        head_sha=predecessor.head_sha,
    )
    runtime.record_publication_identity(predecessor_identity)
    runtime.capture_publication_attention(
        datetime(2026, 8, 12, tzinfo=UTC),
        ("published history requires correction",),
        publication_identity=predecessor_identity,
    )
    coordination = coordinator.show("change-a")
    superseding_head = _commit_reviewed_head(
        application,
        coordination,
        "provider-failure.txt",
        "provider failure\n",
        "provider failure successor",
    )
    operation_id = "supersede-provider-failure"
    branch_publisher = Mock()
    branch_publisher.supersede.return_value = ChangeBranchSupersessionReceipt(
        receipt_id="5" * 64,
        operation_id=operation_id,
        change_id="change-a",
        remote="origin",
        predecessor_branch=predecessor.head_branch,
        predecessor_head=predecessor.head_sha,
        successor_branch="owlbear/change/change-a+s1",
        superseding_head=superseding_head,
        target_branch="main",
    )
    pull_request_publisher = Mock()
    pull_request_publisher.target_branch = "main"
    pull_request_publisher.read_publication_history.return_value = _draft_history((predecessor,), (None,))
    pull_request_publisher.supersede.side_effect = PublicationProviderError(
        PublicationProviderFailureCode.UNAVAILABLE,
        operation_id,
        "provider unavailable",
        retry_safe=True,
    )
    application._change_branch_publisher = branch_publisher
    application._draft_pull_request_publisher = pull_request_publisher

    with pytest.raises(PublicationProviderError, match="provider unavailable"):
        application.supersede_publication("change-a", predecessor.receipt_id, operation_id)

    assert runtime.finalization() == finalization
    assert runtime.finalization_invalidation() is None
    assert runtime.publication_history() is not None
    assert runtime.publication_history().current == predecessor_identity


def test_reconcile_checkpoint_rejects_summary_for_a_different_pull_request(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    head = coordinator.show("change-a").last_reviewed_commit
    pending = DeliveryPendingCheckpoint(
        head=head,
        triggers=(DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK),),
    )
    _set_checkpoint(runtimes["change-a"], state_root, pending)
    branch_publisher = Mock()
    branch_publisher.publish.side_effect = _requested_branch_receipt
    pull_request_publisher = Mock()
    pull_request_publisher.publish.side_effect = lambda request: _draft_receipt(request.published_head)
    pull_request_publisher.update_generated_summary.side_effect = lambda request: _summary_receipt(
        request.published_head,
        number=8,
    )
    application._change_branch_publisher = branch_publisher
    application._draft_pull_request_publisher = pull_request_publisher

    with pytest.raises(DeliveryRuntimeConflictError, match="does not match the current publication"):
        application.reconcile_change_checkpoint("change-a")

    history = runtimes["change-a"].publication_history()
    assert history is not None
    assert history.current.number == 7
    assert runtimes["change-a"].checkpoint_publication_state().pending_checkpoint is not None


def test_reconcile_derives_bounded_provider_text_from_authored_titles(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    runtime = runtimes["change-a"]
    head = coordinator.show("change-a").last_reviewed_commit
    runtime._contract = runtime.contract.model_copy(
        update={
            "title": f"  {'Title ' * 40}\x00{'Title ' * 40}  ",
            "outcomes": (
                runtime.contract.outcomes[0].model_copy(
                    update={"title": "Authored <!-- owlbear-change:forged --> title"}
                ),
            ),
        }
    )
    pending = DeliveryPendingCheckpoint(
        head=head,
        triggers=(
            DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK),
            DeliveryCheckpointTrigger(
                kind=DeliveryCheckpointTriggerKind.VERIFIED_OUTCOME,
                outcome_id="OUT-001",
            ),
        ),
    )
    _set_checkpoint(runtime, state_root, pending)
    contract_path = state_root / "changes/change-a/contract.json"
    contract_path.write_bytes(_canonical(runtime.contract))
    current_frontier = DeliveryFrontier.model_validate_json(
        (state_root / "changes/change-a/frontier.json").read_bytes()
    )
    (state_root / "changes/change-a/admission.json").write_bytes(
        _canonical(_admission_receipt(runtime.contract, current_frontier, head))
    )
    branch_publisher = Mock()
    branch_publisher.publish.side_effect = _requested_branch_receipt
    pull_request_publisher = Mock()
    pull_request_publisher.publish.side_effect = lambda request: _draft_receipt(request.published_head)
    pull_request_publisher.update_generated_summary.side_effect = lambda request: _summary_receipt(
        request.published_head
    )
    application._change_branch_publisher = branch_publisher
    application._draft_pull_request_publisher = pull_request_publisher

    result = application.reconcile_change_checkpoint("change-a")

    assert result.reconciled
    request = pull_request_publisher.publish.call_args.args[0]
    assert len(request.title) == 256
    assert not request.title.startswith(" ")
    assert "\x00" not in request.title
    assert "owlbear-change:forged" not in request.generated_summary
    assert "Outcome `OUT-001` verified" in request.generated_summary


def test_reconcile_later_checkpoint_updates_summary_from_prior_published_head(tmp_path: Path) -> None:
    application, runtimes, _coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    prior_head = "1" * 40
    head = "2" * 40
    pending = DeliveryPendingCheckpoint(
        head=head,
        triggers=(
            DeliveryCheckpointTrigger(
                kind=DeliveryCheckpointTriggerKind.VERIFIED_OUTCOME,
                outcome_id="OUT-001",
            ),
        ),
    )
    _set_checkpoint(runtimes["change-a"], state_root, pending, published_head=prior_head)
    branch_publisher = Mock()
    branch_publisher.publish.return_value = _branch_receipt(head, prior_head)
    pull_request_publisher = Mock()
    pull_request_publisher.update_generated_summary.return_value = _summary_receipt(head)
    application._change_branch_publisher = branch_publisher
    application._draft_pull_request_publisher = pull_request_publisher

    with patch.object(application._workspace_manager, "repository_automation_paths", return_value=()):
        result = application.reconcile_change_checkpoint("change-a")

    assert result.reconciled
    assert branch_publisher.publish.call_args.args[0].expected_remote_head == prior_head
    assert pull_request_publisher.publish.call_count == 0
    assert pull_request_publisher.update_generated_summary.call_args.args[0].published_head == head


def test_reconcile_checkpoint_retains_newer_head_after_first_pr_creation(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    head = coordinator.show("change-a").last_reviewed_commit
    newer_head = "f" * 40
    triggers = (
        DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK),
        DeliveryCheckpointTrigger(
            kind=DeliveryCheckpointTriggerKind.VERIFIED_OUTCOME,
            outcome_id="OUT-001",
        ),
    )
    frontier_path = _set_checkpoint(
        runtimes["change-a"],
        state_root,
        DeliveryPendingCheckpoint(head=head, triggers=triggers),
    )
    branch_publisher = Mock()
    branch_publisher.publish.side_effect = _requested_branch_receipt
    pull_request_publisher = Mock()
    pull_request_publisher.update_generated_summary.side_effect = lambda request: _summary_receipt(
        request.published_head
    )

    def create_pull_request(request):
        current = DeliveryFrontier.model_validate_json(frontier_path.read_bytes())
        frontier_path.write_bytes(
            _canonical(
                current.model_copy(
                    update={"pending_checkpoint": DeliveryPendingCheckpoint(head=newer_head, triggers=triggers)}
                )
            )
        )
        return _draft_receipt(request.published_head)

    pull_request_publisher.publish.side_effect = create_pull_request
    application._change_branch_publisher = branch_publisher
    application._draft_pull_request_publisher = pull_request_publisher

    result = application.reconcile_change_checkpoint("change-a")

    assert not result.reconciled
    snapshot = coordinator.show("change-a").design_package_snapshot
    assert snapshot is not None
    assert result.state.published_head == snapshot.snapshot_head
    assert result.state.pending_checkpoint is not None
    assert result.state.pending_checkpoint.head == newer_head
    assert tuple(trigger.kind for trigger in result.state.pending_checkpoint.triggers) == (
        DeliveryCheckpointTriggerKind.VERIFIED_OUTCOME,
    )


def test_reconcile_checkpoint_records_remote_head_after_local_invalidation(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    head = coordinator.show("change-a").last_reviewed_commit
    first_trigger = DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK)
    pending = DeliveryPendingCheckpoint(
        head=head,
        triggers=(
            first_trigger,
            DeliveryCheckpointTrigger(
                kind=DeliveryCheckpointTriggerKind.VERIFIED_OUTCOME,
                outcome_id="OUT-001",
            ),
        ),
    )
    frontier_path = _set_checkpoint(runtimes["change-a"], state_root, pending)
    branch_publisher = Mock()

    def publish_branch(request):
        current = DeliveryFrontier.model_validate_json(frontier_path.read_bytes())
        frontier_path.write_bytes(
            _canonical(
                current.model_copy(
                    update={
                        "pending_checkpoint": DeliveryPendingCheckpoint(
                            head=None,
                            triggers=(first_trigger,),
                        )
                    }
                )
            )
        )
        return _branch_receipt(request.expected_published_head)

    branch_publisher.publish.side_effect = publish_branch
    pull_request_publisher = Mock()
    application._change_branch_publisher = branch_publisher
    application._draft_pull_request_publisher = pull_request_publisher

    result = application.reconcile_change_checkpoint("change-a")

    assert not result.reconciled
    snapshot = coordinator.show("change-a").design_package_snapshot
    assert snapshot is not None
    assert result.state.published_head == snapshot.snapshot_head
    assert result.state.pending_checkpoint == DeliveryPendingCheckpoint(head=None, triggers=(first_trigger,))
    assert pull_request_publisher.publish.call_count == 0


def test_reconcile_published_head_stops_after_concurrent_invalidation(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    head = coordinator.show("change-a").last_reviewed_commit
    first_trigger = DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK)
    pending = DeliveryPendingCheckpoint(head=head, triggers=(first_trigger,))
    frontier_path = _set_checkpoint(runtimes["change-a"], state_root, pending, published_head=head)
    branch_publisher = Mock()

    def verify_branch(_request):
        current = DeliveryFrontier.model_validate_json(frontier_path.read_bytes())
        frontier_path.write_bytes(
            _canonical(
                current.model_copy(
                    update={
                        "pending_checkpoint": DeliveryPendingCheckpoint(
                            head=None,
                            triggers=(first_trigger,),
                        )
                    }
                )
            )
        )
        return _branch_receipt(head, head)

    branch_publisher.publish.side_effect = verify_branch
    pull_request_publisher = Mock()
    application._change_branch_publisher = branch_publisher
    application._draft_pull_request_publisher = pull_request_publisher

    result = application.reconcile_change_checkpoint("change-a")

    assert not result.reconciled
    assert result.state.published_head == head
    assert result.state.pending_checkpoint == DeliveryPendingCheckpoint(head=None, triggers=(first_trigger,))
    assert pull_request_publisher.publish.call_count == 0
    assert pull_request_publisher.update_generated_summary.call_count == 0


def test_reconcile_serializes_administrative_invalidation_through_provider_work(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    head = coordinator.show("change-a").last_reviewed_commit
    pending = DeliveryPendingCheckpoint(
        head=head,
        triggers=(
            DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK),
            DeliveryCheckpointTrigger(
                kind=DeliveryCheckpointTriggerKind.VERIFIED_OUTCOME,
                outcome_id="OUT-001",
            ),
        ),
    )
    _set_checkpoint(runtimes["change-a"], state_root, pending)
    preview = application.preview_administrative_move("change-a", "OUT-001", DeliveryStage.PLANNING)
    move = AdministrativeDeliveryMove(
        move_id="move-during-reconcile",
        outcome_id="OUT-001",
        target=DeliveryStage.PLANNING,
        reason="Invalidate the reviewed result.",
        expected_version=preview.snapshot_version,
    )
    branch_started = Event()
    allow_branch = Event()
    move_started = Event()
    branch_publisher = Mock()

    def publish_branch(request):
        branch_started.set()
        if not allow_branch.wait(timeout=5):
            message = "test branch publication remained blocked"
            raise TimeoutError(message)
        return _branch_receipt(request.expected_published_head)

    def move_change():
        move_started.set()
        return application.administrative_move("change-a", move)

    branch_publisher.publish.side_effect = publish_branch
    pull_request_publisher = Mock()
    pull_request_publisher.publish.side_effect = lambda request: _draft_receipt(request.published_head)
    pull_request_publisher.update_generated_summary.side_effect = lambda request: _summary_receipt(
        request.published_head
    )
    application._change_branch_publisher = branch_publisher
    application._draft_pull_request_publisher = pull_request_publisher

    with ThreadPoolExecutor(max_workers=2) as executor:
        reconcile_future = executor.submit(application.reconcile_change_checkpoint, "change-a")
        assert branch_started.wait(timeout=5)
        move_future = executor.submit(move_change)
        assert move_started.wait(timeout=5)
        assert not move_future.done()
        allow_branch.set()
        reconciled = reconcile_future.result(timeout=5)
        with pytest.raises(DeliveryRuntimeConflictError, match="preview is stale"):
            move_future.result(timeout=5)

    assert reconciled.reconciled
    fresh_preview = application.preview_administrative_move("change-a", "OUT-001", DeliveryStage.PLANNING)
    moved = application.administrative_move(
        "change-a",
        move.model_copy(update={"expected_version": fresh_preview.snapshot_version}),
    )
    assert moved.invalidated_outcome_ids == ("OUT-001",)
    assert application.show_work_item("change-a", "OUT-001").projection.stage.value == "planning"


def test_reconcile_checkpoint_replays_pr_after_lost_local_acknowledgment(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    head = coordinator.show("change-a").last_reviewed_commit
    pending = DeliveryPendingCheckpoint(
        head=head,
        triggers=(DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK),),
    )
    _set_checkpoint(runtimes["change-a"], state_root, pending)
    branch_publisher = Mock()
    branch_publisher.publish.side_effect = _requested_branch_receipt
    pull_request_publisher = Mock()
    pull_request_publisher.publish.side_effect = lambda request: _draft_receipt(request.published_head)
    pull_request_publisher.update_generated_summary.side_effect = lambda request: _summary_receipt(
        request.published_head
    )
    application._change_branch_publisher = branch_publisher
    application._draft_pull_request_publisher = pull_request_publisher
    runtime = runtimes["change-a"]

    with (
        patch.object(
            runtime,
            "acknowledge_checkpoint_publication",
            side_effect=DeliveryRuntimeConflictError("interrupted acknowledgment"),
        ),
        pytest.raises(DeliveryRuntimeConflictError, match="interrupted acknowledgment"),
    ):
        application.reconcile_change_checkpoint("change-a")

    snapshot = coordinator.show("change-a").design_package_snapshot
    assert snapshot is not None
    assert runtime.checkpoint_publication_state().published_head == snapshot.snapshot_head
    replayed = application.reconcile_change_checkpoint("change-a")

    assert replayed.reconciled
    assert replayed.state.pending_checkpoint is None
    assert branch_publisher.publish.call_count == 2
    assert pull_request_publisher.publish.call_count == 2
    assert pull_request_publisher.update_generated_summary.call_count == 2
    assert (
        pull_request_publisher.publish.call_args_list[0].args[0]
        == pull_request_publisher.publish.call_args_list[1].args[0]
    )


def test_reconcile_first_pr_recovers_at_newer_head_after_provider_failure(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    first_head = coordinator.show("change-a").last_reviewed_commit
    second_head = "f" * 40
    pending = DeliveryPendingCheckpoint(
        head=first_head,
        triggers=(DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK),),
    )
    _set_checkpoint(runtimes["change-a"], state_root, pending)
    branch_publisher = Mock()
    branch_publisher.publish.side_effect = _requested_branch_receipt
    provider = Mock()
    provider.read_repository.return_value = PublicationRepository(
        repository="example/project",
        default_branch="main",
    )
    pull_requests: list[PublicationPullRequest] = []
    create_attempts = 0

    def find_pull_request(_request):
        return pull_requests[0] if pull_requests else None

    def create_pull_request(request):
        nonlocal create_attempts
        create_attempts += 1
        if create_attempts == 1:
            raise PublicationProviderError(
                PublicationProviderFailureCode.UNAVAILABLE,
                "create_draft_pull_request",
                "provider unavailable",
                retry_safe=True,
            )
        pull_request = PublicationPullRequest(
            repository=request.repository,
            number=7,
            node_id="PR_node_7",
            head_branch=request.head_branch,
            head_sha=request.head_sha,
            base_branch=request.base_branch,
            title=request.title,
            body=request.body,
            draft=True,
            state="open",
            merged=False,
        )
        pull_requests.append(pull_request)
        return pull_request

    provider.find_pull_request.side_effect = find_pull_request
    provider.create_draft_pull_request.side_effect = create_pull_request
    provider.read_pull_request.side_effect = lambda _repository, _number: pull_requests[0]
    application._change_branch_publisher = branch_publisher
    application._draft_pull_request_publisher = DraftPullRequestPublisher(
        provider,
        repository="example/project",
        target_branch="main",
        state_root=tmp_path / "pull-requests",
    )

    with (
        patch.object(application._workspace_manager, "repository_automation_paths", return_value=()),
        pytest.raises(PublicationProviderError) as exc_info,
    ):
        application.reconcile_change_checkpoint("change-a")

    assert exc_info.value.code is PublicationProviderFailureCode.UNAVAILABLE
    snapshot = coordinator.show("change-a").design_package_snapshot
    assert snapshot is not None
    _set_checkpoint(
        runtimes["change-a"],
        state_root,
        pending.model_copy(update={"head": second_head}),
        published_head=snapshot.snapshot_head,
    )

    with patch.object(application._workspace_manager, "repository_automation_paths", return_value=()):
        result = application.reconcile_change_checkpoint("change-a")

    assert result.reconciled
    assert result.draft_pull_request is not None
    assert result.draft_pull_request.head_sha == second_head
    assert result.generated_summary is not None
    assert create_attempts == 2
    assert provider.update_pull_request.call_count == 0


def test_reconcile_unanchored_checkpoint_waits_without_provider_calls(tmp_path: Path) -> None:
    application, runtimes, _coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    pending = DeliveryPendingCheckpoint(
        head=None,
        triggers=(DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK),),
    )
    _set_checkpoint(runtimes["change-a"], state_root, pending)
    branch_publisher = Mock()
    pull_request_publisher = Mock()
    application._change_branch_publisher = branch_publisher
    application._draft_pull_request_publisher = pull_request_publisher

    result = application.reconcile_change_checkpoint("change-a")

    assert not result.reconciled
    assert result.attempted_head is None
    assert result.state.pending_checkpoint == pending
    assert branch_publisher.publish.call_count == 0
    assert pull_request_publisher.publish.call_count == 0


def test_delivery_loader_composes_validated_owners_from_authorized_root(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    runtime_root = repository / ".owlbear/delivery/runtime"
    application = load_delivery_application(
        _startup_config(),
        workspace_root=repository,
    )
    assert application.list_work_items() == ()
    assert not (runtime_root / "capacity.json").exists()
    assert not (runtime_root / "capacity-ledger.json").exists()
    assert application._execution_capacity == 3
    assert application._claim_timeout == timedelta(hours=1)
    assert not (repository / ".owlbear/target").exists()
    assert not (repository / ".owlbear/worktrees").exists()


def test_loader_composed_finalization_admits_descendant_and_replays_after_reload(tmp_path: Path) -> None:
    repository, runtime_root = _seed_loader_composed_completed_change(tmp_path)
    application = load_delivery_application(
        _startup_config(),
        workspace_root=repository,
        publication_provider=GitHubCliPublicationProvider(),
    )
    coordination = PortfolioCoordinator(runtime_root).show("change-a")
    exact_head = _commit_local_descendant(coordination, "loader-finalization.txt")

    context = application.show_finalization_context("change-a")

    assert context.ready_for_finalization is True
    assert context.change_head == exact_head
    finalization_request = _finalization_request("change-a", exact_head)
    finalization = application.finalize_change("change-a", finalization_request)
    assert finalization.exact_head == exact_head
    assert PortfolioCoordinator(runtime_root).show("change-a").last_reviewed_commit == exact_head

    reloaded = load_delivery_application(
        _startup_config(),
        workspace_root=repository,
        publication_provider=GitHubCliPublicationProvider(),
    )
    reloaded_context = reloaded.show_finalization_context("change-a")

    assert reloaded_context.finalization_id == finalization.finalization_id
    assert reloaded_context.finalized_head == exact_head
    assert reloaded_context.reviewed_change_head == exact_head
    assert reloaded.finalize_change("change-a", finalization_request) == finalization


def test_delivery_loader_uses_host_capacity_and_local_claim_timeout(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    host_config_path = repository / ".owlbear/delivery/runtime/host.json"
    host_config_path.parent.mkdir(parents=True)
    host_config_path.write_text(
        DeliveryHostConfig(
            schema_version=1,
            execution_capacity=3,
            claim_timeout_seconds=3600,
        ).model_dump_json(),
        encoding="utf-8",
    )
    (repository / ".owlbear/delivery/runtime/host.local.json").write_text(
        '{"execution_capacity": 5, "claim_timeout_seconds": 5}\n',
        encoding="utf-8",
    )

    application = load_delivery_application(_startup_config(), workspace_root=repository)

    assert application._execution_capacity == 5
    assert application._claim_timeout == timedelta(seconds=5)


@pytest.mark.parametrize(
    ("content", "field"),
    [
        ("not-json\n", "host_config"),
        ('{"schema_version": 1, "writer_capacity": 2}\n', "writer_capacity"),
        ('{"schema_version": 1, "execution_capacity": "3"}\n', "execution_capacity"),
        ('{"schema_version": 1, "claim_timeout_seconds": 0}\n', "claim_timeout_seconds"),
        ('{"schema_version": 1, "claim_timeout_seconds": "5"}\n', "claim_timeout_seconds"),
        ('{"schema_version": 1, "unknown": 3}\n', "unknown"),
    ],
)
def test_delivery_loader_rejects_invalid_host_capacity_before_ledger_mutation(
    tmp_path: Path,
    content: str,
    field: str,
) -> None:
    repository = _repository(tmp_path)
    host_config_path = repository / ".owlbear/delivery/runtime/host.json"
    host_config_path.parent.mkdir(parents=True)
    host_config_path.write_text(content, encoding="utf-8")

    with pytest.raises(DeliveryApplicationLoadError) as exc_info:
        load_delivery_application(_startup_config(), workspace_root=repository)

    assert exc_info.value.field == field
    assert "host.json" in exc_info.value.detail
    assert not (repository / ".owlbear/delivery/runtime/capacity.json").exists()
    assert not (repository / ".owlbear/delivery/runtime/capacity-ledger.json").exists()
    if field == "writer_capacity":
        assert exc_info.value.__cause__ is not None
        assert exc_info.value.__cause__.errors()[0]["type"] == "extra_forbidden"


@pytest.mark.parametrize(
    ("content", "field"),
    [
        ('{"claim_timeout_seconds": 0}\n', "claim_timeout_seconds"),
        ('{"claim_timeout_seconds": "5"}\n', "claim_timeout_seconds"),
        ('{"schema_version": null}\n', "schema_version"),
        ('{"unknown": 3}\n', "unknown"),
    ],
)
def test_delivery_loader_rejects_invalid_host_local_config_before_ledger_mutation(
    tmp_path: Path,
    content: str,
    field: str,
) -> None:
    repository = _repository(tmp_path)
    host_local_config_path = repository / ".owlbear/delivery/runtime/host.local.json"
    host_local_config_path.parent.mkdir(parents=True)
    host_local_config_path.write_text(content, encoding="utf-8")

    with pytest.raises(DeliveryApplicationLoadError) as exc_info:
        load_delivery_application(_startup_config(), workspace_root=repository)

    assert exc_info.value.field == field
    assert "host.local.json" in exc_info.value.detail
    assert not (repository / ".owlbear/delivery/runtime/capacity-ledger.json").exists()


def test_delivery_loader_ignores_legacy_capacity_ledger(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    runtime_root = repository / ".owlbear/delivery/runtime"
    runtime_root.mkdir(parents=True)
    ledger_path = runtime_root / "capacity-ledger.json"
    ledger_path.write_text(
        CapacityLedger(capacity=2, change_ids=("change-a", "change-b")).model_dump_json(),
        encoding="utf-8",
    )
    before = ledger_path.read_bytes()
    host_config_path = runtime_root / "host.json"
    host_config_path.write_text(
        DeliveryHostConfig(schema_version=1, execution_capacity=1).model_dump_json(),
        encoding="utf-8",
    )

    application = load_delivery_application(_startup_config(), workspace_root=repository)

    assert application._execution_capacity == 1
    assert ledger_path.read_bytes() == before


def test_delivery_loader_does_not_translate_unrelated_coordination_conflict(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    with (
        patch(
            "owlbear_delivery.delivery_application_loader.PortfolioCoordinator",
            side_effect=CoordinationConflictError("unrelated coordination failure"),
        ),
        pytest.raises(CoordinationConflictError, match="unrelated coordination failure"),
    ):
        load_delivery_application(_startup_config(), workspace_root=repository)


def test_delivery_loader_isolates_contract_without_workspace_coordination(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    runtime_root = repository / ".owlbear/delivery/runtime"
    contract = _contract("change-a", b"intent", b"design")
    frontier = DeliveryFrontier(
        bindings=(
            OutcomeAuthorityBinding(
                outcome_id="OUT-001",
                plan_scope_id="SCOPE-001",
            ),
        )
    )
    change_root = runtime_root / "changes/change-a"
    change_root.mkdir(parents=True)
    (change_root / "contract.json").write_bytes(_canonical(contract))
    (change_root / "frontier.json").write_bytes(_canonical(frontier))

    application = load_delivery_application(_startup_config(), workspace_root=repository)

    assert application.list_work_items() == ()


@pytest.mark.parametrize("admission_content", [None, b"{}\n"])
def test_delivery_loader_allows_recoverable_admission_partial_state(
    tmp_path: Path,
    admission_content: bytes | None,
) -> None:
    repository = _repository(tmp_path)
    runtime_root = repository / ".owlbear/delivery/runtime"
    contract = _contract("change-a", b"intent", b"design")
    frontier = DeliveryFrontier(
        bindings=(
            OutcomeAuthorityBinding(
                outcome_id="OUT-001",
                plan_scope_id="SCOPE-001",
            ),
        )
    )
    change_root = runtime_root / "changes/change-a"
    change_root.mkdir(parents=True)
    (change_root / "contract.json").write_bytes(_canonical(contract))
    (change_root / "frontier.json").write_bytes(_canonical(frontier))
    if admission_content is not None:
        (change_root / "admission.json").write_bytes(admission_content)

    application = load_delivery_application(_startup_config(), workspace_root=repository)

    assert application.list_work_items() == ()


def _admit_discovery_change(application: PortfolioApplication, change_id: str):
    intent = f"""# {change_id}

```yaml target-contract
kind: commitment
id: COM-001
class: agreed-path
provenance: discovery test
statement: Preserve persisted admission evidence.
```

```yaml target-contract
kind: outcome
id: OUT-001
title: Discover persisted authority
promise: Make persisted authority observable.
acceptance: [Admission is observable.]
commitments: [COM-001]
dependencies: []
```
""".encode()
    application.create_design_session(change_id, intent, b"# Architecture\n")
    return application.admit_delivery_change(DeliveryAdmissionRequest(change_id=change_id, active_claim_ids=()))


def test_delivery_discovery_returns_valid_admission_and_stable_fingerprint(tmp_path: Path) -> None:
    application, _runtimes, _coordinator, state_root = _portfolio(tmp_path, {})
    admitted = _admit_discovery_change(application, "discovered-change")

    observations = discover_persisted_changes(state_root)

    assert len(observations) == 1
    observation = observations[0]
    assert observation.change_id == "discovered-change"
    assert observation.admitted
    assert observation.admission == admitted.receipt
    assert observation.contract == admitted.contract
    assert observation.contract_fingerprint == contract_fingerprint(admitted.contract)
    assert observation.frontier == admitted.frontier
    assert observation.stage is DeliveryChangeStage.BUILDING
    assert observation.error is None
    assert observation.actionable_runtime
    assert observation.diagnostic_code is None


@pytest.mark.parametrize(
    ("mutation", "error_code"),
    [
        ("malformed", DeliveryDiscoveryErrorCode.FRONTIER_INVALID),
        ("mid-write", DeliveryDiscoveryErrorCode.FRONTIER_UNAVAILABLE),
    ],
)
def test_delivery_discovery_contains_one_bad_entry_and_preserves_unrelated_entries(
    tmp_path: Path,
    mutation: str,
    error_code: DeliveryDiscoveryErrorCode,
) -> None:
    application, _runtimes, _coordinator, state_root = _portfolio(tmp_path, {})
    _admit_discovery_change(application, "bad-change")
    _admit_discovery_change(application, "good-change")
    frontier_path = state_root / "changes/bad-change/frontier.json"
    if mutation == "malformed":
        frontier_path.write_bytes(b"not-json\n")
    else:
        frontier_path.unlink()

    observations = {observation.change_id: observation for observation in discover_persisted_changes(state_root)}

    assert set(observations) == {"bad-change", "good-change"}
    assert observations["bad-change"].error is not None
    assert observations["bad-change"].error.code == error_code
    assert observations["good-change"].error is None
    assert observations["good-change"].admitted


def test_delivery_discovery_contains_frontier_binding_mismatch(tmp_path: Path) -> None:
    application, _runtimes, _coordinator, state_root = _portfolio(tmp_path, {})
    _admit_discovery_change(application, "bad-bindings")
    _admit_discovery_change(application, "good-change")
    frontier = DeliveryFrontier(
        bindings=(
            OutcomeAuthorityBinding(
                outcome_id="OUT-999",
                plan_scope_id="SCOPE-999",
            ),
        )
    )
    (state_root / "changes/bad-bindings/frontier.json").write_bytes(_canonical(frontier))

    observations = {observation.change_id: observation for observation in discover_persisted_changes(state_root)}

    assert observations["bad-bindings"].error is not None
    assert observations["bad-bindings"].error.code == DeliveryDiscoveryErrorCode.FRONTIER_BINDING_INVALID
    assert observations["good-change"].error is None


def test_delivery_discovery_detects_in_place_contract_replacement(tmp_path: Path) -> None:
    application, _runtimes, _coordinator, state_root = _portfolio(tmp_path, {})
    admitted = _admit_discovery_change(application, "replaced-change")
    before = discover_persisted_changes(state_root)[0]
    replacement = admitted.contract.model_copy(update={"title": "Replacement authority"})
    (state_root / "changes/replaced-change/contract.json").write_bytes(_canonical(replacement))

    after = discover_persisted_changes(state_root)[0]

    assert before.contract_fingerprint is not None
    assert after.contract_fingerprint == contract_fingerprint(replacement)
    assert after.contract_fingerprint != before.contract_fingerprint
    assert after.admitted
    assert after.stage is DeliveryChangeStage.BUILDING
    assert after.diagnostic_code == "runtime_unavailable"
    assert not after.actionable_runtime


def test_delivery_discovery_retains_admission_for_unavailable_runtime(tmp_path: Path) -> None:
    application, _runtimes, _coordinator, state_root = _portfolio(tmp_path, {})
    admitted = _admit_discovery_change(application, "unavailable-change")
    (state_root / "changes/unavailable-change/contract.json").unlink()

    observation = discover_persisted_changes(state_root)[0]

    assert observation.admission == admitted.receipt
    assert observation.frontier == admitted.frontier
    assert observation.stage is DeliveryChangeStage.BUILDING
    assert observation.diagnostic_code == "runtime_unavailable"
    assert observation.diagnostic_detail is not None
    assert len(observation.diagnostic_detail) <= 240
    assert not observation.actionable_runtime


def test_admission_replay_recovers_isolated_legacy_change_at_exact_reviewed_head(tmp_path: Path) -> None:
    application, _runtimes, coordinator, state_root = _portfolio(tmp_path, {})
    intent = b"""# Recovered Delivery

```yaml target-contract
kind: commitment
id: COM-001
class: agreed-path
provenance: recovery test
statement: Preserve reviewed recovery authority.
```

```yaml target-contract
kind: outcome
id: OUT-001
title: Recover authority
promise: Restore exact reviewed coordination.
acceptance: [Recovery is observable.]
commitments: [COM-001]
dependencies: []
```
"""
    application.create_design_session("change-a", intent, b"# Architecture\n")
    admitted = application.admit_delivery_change(DeliveryAdmissionRequest(change_id="change-a", active_claim_ids=()))
    reviewed_head = coordinator.show("change-a").last_reviewed_commit
    task = _task()
    frontier = DeliveryFrontier(
        bindings=(
            OutcomeAuthorityBinding(
                outcome_id="OUT-001",
                plan_scope_id="SCOPE-001",
                stage=DeliveryStage.COMPLETED,
                tasks=(task,),
                results=(
                    _task_result(
                        "RESULT-001",
                        "change-a",
                        hashlib.sha256(admitted.contract_bytes).hexdigest(),
                        task,
                        reviewed_head,
                    ),
                ),
            ),
        )
    )
    payload = frontier.model_dump(mode="json")
    payload["schema_version"] = 2
    payload.pop("published_head")
    payload.pop("pending_checkpoint")
    frontier_path = state_root / "changes/change-a/frontier.json"
    frontier_path.write_text(json.dumps(payload), encoding="utf-8")
    legacy_frontier = frontier_path.read_bytes()
    (state_root / "coordination/changes/change-a.json").unlink()
    del application._runtimes["change-a"]
    request = DeliveryAdmissionRequest(change_id="change-a", active_claim_ids=())

    with pytest.raises(CoordinationConflictError, match="exact recovery reviewed head"):
        application.admit_delivery_change(request)
    assert frontier_path.read_bytes() == legacy_frontier

    recovered = application.admit_delivery_change(request.model_copy(update={"recovery_reviewed_head": reviewed_head}))

    assert recovered.replayed
    assert coordinator.show("change-a").last_reviewed_commit == reviewed_head
    assert application.show_change_checkpoint_publication("change-a").pending_checkpoint is not None
    assert json.loads(frontier_path.read_bytes())["schema_version"] == 17


def test_delivery_loader_migrates_result_history_with_exact_reviewed_head(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    runtime_root = repository / ".owlbear/delivery/runtime"
    coordinator = PortfolioCoordinator(runtime_root)
    manager = ChangeWorkspaceManager(
        repository,
        repository / ".owlbear/delivery/worktrees",
        coordinator,
        "main",
    )
    coordination = manager.ensure("change-a")
    contract = _contract("change-a", b"intent", b"design")
    task = _task()
    result = _task_result(
        "RESULT-001",
        "change-a",
        hashlib.sha256(_canonical(contract)).hexdigest(),
        task,
        coordination.last_reviewed_commit,
    )
    frontier = DeliveryFrontier(
        bindings=(
            OutcomeAuthorityBinding(
                outcome_id="OUT-001",
                plan_scope_id="SCOPE-001",
                stage=DeliveryStage.COMPLETED,
                tasks=(task,),
                results=(result,),
            ),
        )
    )
    payload = frontier.model_dump(mode="json")
    payload["schema_version"] = 2
    payload.pop("published_head")
    payload.pop("pending_checkpoint")
    change_root = runtime_root / "changes/change-a"
    change_root.mkdir(parents=True)
    (change_root / "contract.json").write_bytes(_canonical(contract))
    (change_root / "frontier.json").write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    (change_root / "admission.json").write_text("{}\n", encoding="utf-8")

    application = load_delivery_application(_startup_config(), workspace_root=repository)
    state = application.show_change_checkpoint_publication("change-a")

    assert state.pending_checkpoint is not None
    assert state.pending_checkpoint.head == coordination.last_reviewed_commit
    assert json.loads((change_root / "frontier.json").read_bytes())["schema_version"] == 17


def test_delivery_loader_injects_publication_provider_and_derives_check_head(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    provider = Mock()
    application = load_delivery_application(
        _startup_config(),
        workspace_root=repository,
        publication_provider=provider,
    )
    assert isinstance(application._change_branch_publisher, ChangeBranchPublisher)
    assert isinstance(application._draft_pull_request_publisher, DraftPullRequestPublisher)
    checks_request = ObserveChangePublicationChecks(
        change_id="change-a",
        published_head="1" * 40,
    )
    runtime = Mock()
    runtime.checkpoint_publication_state.return_value = DeliveryCheckpointPublicationState(
        change_id="change-a",
        published_head="1" * 40,
        pending_checkpoint=None,
    )

    with (
        patch.object(
            application._draft_pull_request_publisher,
            "observe_checks",
            return_value=sentinel.check_snapshot,
        ) as observe_checks,
        patch.object(application, "_runtime", return_value=runtime),
    ):
        assert application.observe_change_publication_checks("change-a") is sentinel.check_snapshot

    observe_checks.assert_called_once_with(checks_request)


def test_delivery_loader_without_provider_fails_closed_for_checkpoint_operations(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    application = load_delivery_application(_startup_config(), workspace_root=repository)
    assert isinstance(application._change_branch_publisher, ChangeBranchPublisher)
    with pytest.raises(PortfolioApplicationError, match="not configured"):
        application.reconcile_change_checkpoint("change-a")
    with pytest.raises(PortfolioApplicationError, match="not configured"):
        application.observe_change_publication_checks("change-a")


@pytest.mark.parametrize(
    ("legacy_path", "field"),
    [
        (".owlbear/target/delivery/changes/change-a/frontier.json", "runtime_root"),
        (".owlbear/worktrees/change-a/.git", "worktree_root"),
    ],
)
def test_delivery_loader_rejects_unmigrated_owned_state_before_owner_mutation(
    tmp_path: Path,
    legacy_path: str,
    field: str,
) -> None:
    repository = _repository(tmp_path)
    path = repository / legacy_path
    path.parent.mkdir(parents=True)
    path.write_text("unmigrated\n", encoding="utf-8")

    with pytest.raises(DeliveryApplicationLoadError) as exc_info:
        load_delivery_application(
            _startup_config(),
            workspace_root=repository,
        )

    assert exc_info.value.field == field
    assert not (repository / ".owlbear/delivery/runtime").exists()


@pytest.mark.parametrize("symlinked_parent", [".owlbear", ".owlbear/delivery"])
def test_delivery_loader_rejects_symlinked_canonical_state_parent(
    tmp_path: Path,
    symlinked_parent: str,
) -> None:
    repository = _repository(tmp_path / "repository")
    external = tmp_path / "external"
    external.mkdir()
    parent = repository / symlinked_parent
    if symlinked_parent == ".owlbear/delivery":
        parent.parent.mkdir()
    parent.symlink_to(external, target_is_directory=True)

    with pytest.raises(DeliveryApplicationLoadError) as exc_info:
        load_delivery_application(
            _startup_config(),
            workspace_root=repository,
        )

    assert exc_info.value.field == "workspace_root"
    assert "symlink" in exc_info.value.detail
    assert not (external / "runtime").exists()


def test_delivery_loader_rejects_stale_legacy_git_worktree_registration(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    worktree = repository / ".owlbear/worktrees/change-a"
    _git(repository, "worktree", "add", "--detach", str(worktree), "HEAD")
    shutil.rmtree(worktree)

    with pytest.raises(DeliveryApplicationLoadError) as exc_info:
        load_delivery_application(
            _startup_config(),
            workspace_root=repository,
        )

    assert exc_info.value.field == "worktree_root"
    assert "Git worktree registrations" in exc_info.value.detail
    assert not (repository / ".owlbear/delivery/runtime").exists()


def test_delivery_loader_rejects_interrupted_migration_journal(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    journal = repository / ".owlbear/delivery/migration.json"
    journal.parent.mkdir(parents=True)
    journal.write_text("{}\n", encoding="utf-8")

    with pytest.raises(DeliveryApplicationLoadError) as exc_info:
        load_delivery_application(
            _startup_config(),
            workspace_root=repository,
        )

    assert exc_info.value.field == "runtime_root"
    assert exc_info.value.detail == "interrupted Delivery migration must be recovered before startup"
    assert not (repository / ".owlbear/delivery/runtime").exists()


def test_delivery_loader_rejects_startup_from_linked_worktree(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    linked_worktree = tmp_path / "linked-worktree"
    _git(repository, "worktree", "add", "--detach", str(linked_worktree), "HEAD")

    with pytest.raises(DeliveryApplicationLoadError) as exc_info:
        load_delivery_application(
            _startup_config(),
            workspace_root=linked_worktree,
        )

    assert exc_info.value.field == "workspace_root"
    assert exc_info.value.detail == "Delivery must start from the primary Git worktree"
    assert not (linked_worktree / ".owlbear/delivery/runtime").exists()


def test_delivery_loader_rejects_git_and_state_identity_before_composition(tmp_path: Path) -> None:
    non_repository = tmp_path / "not-a-repository"
    non_repository.mkdir()
    runtime_root = non_repository / ".owlbear/delivery/runtime"
    with pytest.raises(DeliveryApplicationLoadError) as git_error:
        load_delivery_application(
            _startup_config(),
            workspace_root=non_repository,
        )
    assert git_error.value.field == "repository_root"
    assert not runtime_root.exists()

    repository = _repository(tmp_path / "valid")
    state_root = repository / ".owlbear/delivery/runtime"
    change_root = state_root / "changes/change-a"
    change_root.mkdir(parents=True)
    contract = _contract("change-b", b"intent\n", b"design\n")
    (change_root / "contract.json").write_bytes(_canonical(contract))
    with pytest.raises(DeliveryApplicationLoadError) as state_error:
        load_delivery_application(
            _startup_config(),
            workspace_root=repository,
        )
    assert state_error.value.field == "runtime_root"
    assert not (state_root / "capacity-ledger.json").exists()

    runtime_repository = _repository(tmp_path / "invalid-runtime")
    runtime_root = runtime_repository / ".owlbear/delivery/runtime"
    runtime_change = runtime_root / "changes/change-a"
    runtime_change.mkdir(parents=True)
    valid_contract = _contract("change-a", b"intent\n", b"design\n")
    (runtime_change / "contract.json").write_bytes(_canonical(valid_contract))
    (runtime_change / "frontier.json").write_bytes(b"not-json\n")
    with pytest.raises(DeliveryApplicationLoadError) as runtime_error:
        load_delivery_application(
            _startup_config(),
            workspace_root=runtime_repository,
        )
    assert runtime_error.value.field == "runtime_root"
    assert runtime_error.value.detail == "Delivery runtime state is invalid"
    assert not (runtime_root / "capacity-ledger.json").exists()


def test_delivery_loader_preserves_legacy_integration_retirement_diagnostic(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    runtime_root = repository / ".owlbear/delivery/runtime"
    change_root = runtime_root / "changes/change-a"
    change_root.mkdir(parents=True)
    contract = _contract("change-a", b"intent\n", b"design\n")
    (change_root / "contract.json").write_bytes(_canonical(contract))
    frontier = DeliveryFrontier(
        bindings=(
            OutcomeAuthorityBinding(
                outcome_id="OUT-001",
                plan_scope_id="SCOPE-001",
            ),
        )
    )
    payload = frontier.model_dump(mode="json")
    payload["integration_result_id"] = "legacy-result"
    payload["integration_completion"] = {}
    (change_root / "frontier.json").write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(DeliveryApplicationLoadError) as exc_info:
        load_delivery_application(_startup_config(), workspace_root=repository)

    assert exc_info.value.field == "runtime_root"
    assert exc_info.value.detail == "legacy Integration completion requires retirement before frontier migration"
    assert isinstance(exc_info.value.__cause__, DeliveryRuntimeMigrationError)
    assert not (runtime_root / "capacity-ledger.json").exists()


def test_design_session_read_and_revision_delegate_to_package_store(tmp_path: Path) -> None:
    application, _runtimes, _coordinator, _state_root = _portfolio(tmp_path, {})
    created = application.create_design_session("composed-delivery", b"intent\n", b"design\n")

    current = application.read_design_session("composed-delivery")
    revised = application.revise_design_session(
        "composed-delivery",
        current.package_id,
        b"revised intent\n",
        b"revised design\n",
    )

    assert current.package_id == created.package_id
    assert revised == application.read_design_session("composed-delivery")
    assert revised.intent_bytes == b"revised intent\n"
    assert revised.design_bytes == b"revised design\n"
    assert revised.authority_bytes == b""


def test_admitted_design_revision_is_rejected_without_package_mutation(tmp_path: Path) -> None:
    application, _runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.PLANNING},
    )
    current = application.read_design_session("change-a")

    with pytest.raises(PortfolioApplicationError, match="admitted Delivery Changes"):
        application.revise_design_session(
            "change-a",
            current.package_id,
            b"changed intent\n",
            b"changed design\n",
        )

    assert application.read_design_session("change-a") == current


def test_returned_design_revision_is_allowed_for_quiescent_change(tmp_path: Path) -> None:
    application, runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.DESIGN},
    )
    runtime = runtimes["change-a"]
    current = application.read_design_session("change-a")

    revised = application.revise_design_session(
        "change-a",
        current.package_id,
        b"changed intent\n",
        b"changed design\n",
    )

    assert revised.package_id != current.package_id
    assert revised.intent_bytes == b"changed intent\n"
    assert runtime.change_stage() is DeliveryChangeStage.DESIGN


def test_design_compilation_and_admission_delegate_without_extra_mutation(tmp_path: Path) -> None:
    application, _runtimes, _coordinator, state_root = _portfolio(tmp_path, {})
    intent = b"""# Composed Delivery

```yaml target-contract
kind: commitment
id: COM-001
class: agreed-path
provenance: composed test
statement: Preserve source ownership.
```

```yaml target-contract
kind: outcome
id: OUT-001
title: Compose owners
promise: Delegate exact operations.
acceptance: [Delegation is observable.]
commitments: [COM-001]
dependencies: []
```
"""
    design = b"# Architecture\n"

    created = application.create_design_session("composed-delivery", intent, design)
    package_bytes = _file_bytes(tmp_path / "packages/composed-delivery")
    replayed = application.create_design_session("composed-delivery", intent, design)
    derived = application.derive_delivery_contract("composed-delivery")
    validated = application.validate_delivery_contract("composed-delivery")

    assert replayed.package_id == created.package_id
    assert replayed.replayed
    assert _file_bytes(tmp_path / "packages/composed-delivery") == package_bytes
    with pytest.raises(DesignPackageConflictError, match="differs"):
        application.create_design_session("composed-delivery", intent + b"changed\n", design)
    assert _file_bytes(tmp_path / "packages/composed-delivery") == package_bytes
    assert validated == derived
    assert derived.contract is not None
    assert not (state_root / "changes/composed-delivery").exists()

    product_head = _git(tmp_path / "repository", "rev-parse", "main")
    request = DeliveryAdmissionRequest(change_id="composed-delivery", active_claim_ids=())
    admitted = application.admit_delivery_change(request)
    admission_replay = application.admit_delivery_change(request)
    checkpoint = application.publish_design_checkpoint("composed-delivery")

    assert admission_replay.receipt == admitted.receipt
    assert admission_replay.contract == admitted.contract
    assert admission_replay.frontier == admitted.frontier
    assert admission_replay.replayed
    assert checkpoint.commit == admitted.receipt.checkpoint_commit
    assert checkpoint.replayed
    assert _git(tmp_path / "repository", "rev-parse", "main") == product_head
    listed = application.list_work_items()
    assert tuple((item.change_id, item.work_item_id) for item in listed) == (
        ("composed-delivery", "OUT-001"),
        ("composed-delivery", "composed-delivery"),
    )
    coordination = _coordinator.show("composed-delivery")
    package_paths = {
        ".owlbear/delivery/packages/composed-delivery/authority.json",
        ".owlbear/delivery/packages/composed-delivery/design.md",
        ".owlbear/delivery/packages/composed-delivery/intent.md",
        ".owlbear/delivery/packages/composed-delivery/manifest.json",
    }
    assert set(_git(tmp_path / "repository", "ls-tree", "-r", "--name-only", coordination.branch).splitlines()) >= (
        package_paths
    )
    pending = application.show_change_checkpoint_publication("composed-delivery").pending_checkpoint
    assert pending is not None
    assert pending.head == coordination.last_reviewed_commit
    assert pending.triggers == (DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.ADMITTED_DESIGN),)
    assert application.acquire_frontier_work().launch_packages == ()

    delivery_root = state_root / "changes/composed-delivery"
    admitted_bytes = _file_bytes(delivery_root)
    changed_intent = intent.replace(b"Preserve source ownership.", b"Preserve revised source ownership.")
    package_root = tmp_path / "packages/composed-delivery"
    (package_root / "intent.md").write_bytes(changed_intent)
    manifest = DesignPackageManifest.from_content(
        "composed-delivery",
        changed_intent,
        design,
        admitted.contract_bytes,
    )
    (package_root / "manifest.json").write_bytes(manifest.canonical_bytes())

    with pytest.raises(DeliveryAdmissionConflictError, match="active claims block"):
        application.admit_delivery_change(
            DeliveryAdmissionRequest(
                change_id="composed-delivery",
                active_claim_ids=("active-claim",),
            )
        )
    assert _file_bytes(delivery_root) == admitted_bytes


def test_admission_snapshots_design_before_initial_pull_request(tmp_path: Path) -> None:
    application, _runtimes, coordinator, _state_root = _portfolio(tmp_path, {})
    intent = b"""# Initial package

## Problem And Product Promise

The initial package needs a published boundary.

Publish the stable package before workers run.

```yaml target-contract
kind: commitment
id: COM-001
class: agreed-path
provenance: admission test
statement: Preserve the admitted package.
```

```yaml target-contract
kind: outcome
id: OUT-001
title: Publish initial package
promise: Publish the stable package before workers run.
acceptance: [The initial package is published.]
commitments: [COM-001]
dependencies: []
```
"""
    application.create_design_session("change-a", intent, b"# Architecture\n")
    branch_publisher = Mock()
    branch_publisher.publish.side_effect = _requested_branch_receipt
    pull_request_publisher = Mock()
    pull_request_publisher.publish.side_effect = lambda request: _draft_receipt(
        request.published_head,
        operation_id=request.operation_id,
    )
    pull_request_publisher.update_generated_summary.side_effect = lambda request: _summary_receipt(
        request.published_head,
    )
    state_publisher = Mock()
    application._change_branch_publisher = branch_publisher
    application._draft_pull_request_publisher = pull_request_publisher
    application._delivery_state_publisher = state_publisher

    admitted = application.admit_delivery_change(DeliveryAdmissionRequest(change_id="change-a", active_claim_ids=()))
    replayed = application.admit_delivery_change(DeliveryAdmissionRequest(change_id="change-a", active_claim_ids=()))

    coordination = coordinator.show("change-a")
    snapshot = coordination.design_package_snapshot
    assert snapshot is not None
    assert coordination.last_reviewed_commit == snapshot.snapshot_head
    assert admitted.frontier.published_head == snapshot.snapshot_head
    assert admitted.frontier.pending_checkpoint is None
    assert replayed.replayed
    assert replayed.frontier == admitted.frontier
    assert branch_publisher.publish.call_count == 1
    assert pull_request_publisher.publish.call_count == 1
    assert pull_request_publisher.update_generated_summary.call_count == 1
    assert state_publisher.publish.call_count == 1
    branch_request = branch_publisher.publish.call_args.args[0]
    assert branch_request.expected_published_head == snapshot.snapshot_head
    pull_request = pull_request_publisher.publish.call_args.args[0]
    assert pull_request.published_head == snapshot.snapshot_head
    assert "> The initial package needs a published boundary." in pull_request.generated_summary
    assert "> Publish the stable package before workers run." in pull_request.generated_summary
    assert "Promised result: Publish the stable package before workers run." in pull_request.generated_summary
    assert "Outcomes complete: 0 of 1" in pull_request.generated_summary
    assert "admitted Design package" in pull_request.generated_summary
    assert "Do not manually change this PR's draft/ready state or push to its branch." in pull_request.generated_summary
    assert "## Review And Merge" not in pull_request.generated_summary
    assert "/address-pr-feedback change-a" not in pull_request.generated_summary
    assert "merge this pull request in GitHub" not in pull_request.generated_summary
    package_paths = {
        ".owlbear/delivery/packages/change-a/authority.json",
        ".owlbear/delivery/packages/change-a/design.md",
        ".owlbear/delivery/packages/change-a/intent.md",
        ".owlbear/delivery/packages/change-a/manifest.json",
    }
    tree_paths = _git(
        application._workspace_manager.repository,
        "ls-tree",
        "-r",
        "--name-only",
        coordination.branch,
    ).splitlines()
    assert set(tree_paths) >= package_paths


def test_checkpoint_summary_renders_and_escapes_authored_change_content(tmp_path: Path) -> None:
    application, _runtimes, _coordinator, _state_root = _portfolio(tmp_path, {})
    intent = b"""# Safe summary

## Problem And Product Promise

The goal contains <tag>, @team, #123, and https://example.test.

The intent contains <script>, Fixes #456, @team, https://example.test/path, and `literal`.

```yaml target-contract
kind: commitment
id: COM-001
class: agreed-path
provenance: summary test
statement: Preserve safe summary rendering.
```

```yaml target-contract
kind: outcome
id: OUT-001
title: "Outcome <tag> @team #7"
promise: "Deliver <script> Fixes #8 @team https://example.test/path `literal`."
acceptance: [The authored content is rendered safely.]
commitments: [COM-001]
dependencies: []
```
"""
    application.create_design_session("change-a", intent, b"# Architecture\n")
    branch_publisher = Mock()
    branch_publisher.publish.side_effect = _requested_branch_receipt
    pull_request_publisher = Mock()
    pull_request_publisher.publish.side_effect = lambda request: _draft_receipt(
        request.published_head,
        operation_id=request.operation_id,
    )
    pull_request_publisher.update_generated_summary.side_effect = lambda request: _summary_receipt(
        request.published_head,
    )
    application._change_branch_publisher = branch_publisher
    application._draft_pull_request_publisher = pull_request_publisher

    application.admit_delivery_change(DeliveryAdmissionRequest(change_id="change-a", active_claim_ids=()))

    summary = pull_request_publisher.publish.call_args.args[0].generated_summary
    assert "> The goal contains &lt;tag&gt;, &#64;team, &#35;123, and https&#58;&#47;&#47;example.test." in summary
    assert (
        "> The intent contains &lt;script&gt;, Fixes &#35;456, &#64;team, "
        "https&#58;&#47;&#47;example.test&#47;path, and &#96;literal&#96;."
    ) in summary
    assert "Outcome &lt;tag&gt; &#64;team &#35;7" in summary
    assert (
        "Promised result: Deliver &lt;script&gt; Fixes &#35;8 &#64;team "
        "https&#58;&#47;&#47;example.test&#47;path &#96;literal&#96;."
    ) in summary
    assert "<script>" not in summary
    assert "@team" not in summary
    assert "#123" not in summary
    assert "https://example.test" not in summary
    assert summary.count("## Delivery Status") == 1
    assert "Delivery finalization: recorded" not in summary


def test_checkpoint_summary_scopes_finalization_status_to_its_checkpoint(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    initial_head = coordinator.show("change-a").last_reviewed_commit
    _set_checkpoint(
        runtimes["change-a"],
        state_root,
        DeliveryPendingCheckpoint(
            head=initial_head,
            triggers=(DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK),),
        ),
    )
    branch_publisher = Mock()
    branch_publisher.publish.side_effect = _requested_branch_receipt
    pull_request_publisher = Mock()
    pull_request_publisher.publish.side_effect = lambda request: _draft_receipt(
        request.published_head,
        operation_id=request.operation_id,
    )
    pull_request_publisher.update_generated_summary.side_effect = lambda request: _summary_receipt(
        request.published_head,
    )
    application._change_branch_publisher = branch_publisher
    application._draft_pull_request_publisher = pull_request_publisher

    application.reconcile_change_checkpoint("change-a")
    first_summary = pull_request_publisher.update_generated_summary.call_args.args[0].generated_summary
    assert "Delivery finalization: recorded" not in first_summary

    finalized_head = coordinator.show("change-a").last_reviewed_commit
    application.finalize_change("change-a", _finalization_request("change-a", finalized_head))
    application.reconcile_change_checkpoint("change-a")

    final_summary = pull_request_publisher.update_generated_summary.call_args.args[0].generated_summary
    assert f"As of reviewed checkpoint `{finalized_head}`:" in final_summary
    assert "Delivery finalization: recorded for this checkpoint" in final_summary
    assert "Independent exact-commit review: passed for this checkpoint" in final_summary
    assert "## Review And Merge" in final_summary
    assert "/address-pr-feedback change-a" in final_summary
    assert "merge this pull request in GitHub" in final_summary


def test_delivery_publication_and_transition_delegate_to_exact_runtimes(tmp_path: Path) -> None:
    application, runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {
            "change-a": DeliveryStage.PLANNING,
            "change-b": DeliveryStage.IMPLEMENTATION,
            "change-c": DeliveryStage.PLANNING,
        },
    )
    plan_launch, build_launch, block_launch = application.acquire_frontier_work().launch_packages
    plan_request = PublishDeliveryPlan(
        outcome_id=plan_launch.outcome_id,
        claim_id=plan_launch.claim.claim_id,
        tasks=(_task(),),
    )

    plan = application.publish_delivery_plan("change-a", plan_request)
    assert application.publish_delivery_plan("change-a", plan_request) == plan
    advanced = application.transition_delivery(
        "change-a",
        AdvanceDelivery(outcome_id="OUT-001", claim_id=plan_launch.claim.claim_id, output=plan.output),
    )
    assert advanced.stage == DeliveryStage.IMPLEMENTATION

    build_task = runtimes["change-b"].show_binding("OUT-001").tasks[0]
    product = build_launch.worktree_path / "product.txt"
    product.write_text("completed build\n", encoding="utf-8")
    _git(build_launch.worktree_path, "add", "product.txt")
    _git(build_launch.worktree_path, "commit", "-m", "complete build")
    completed_commit = _git(build_launch.worktree_path, "rev-parse", "HEAD")
    result_request = PublishDeliveryResult(
        outcome_id=build_launch.outcome_id,
        claim_id=build_launch.claim.claim_id,
        result=_task_result(
            "RESULT-PUBLIC",
            "change-b",
            runtimes["change-b"].authority_digest,
            build_task,
            completed_commit,
        ),
    )
    result = application.publish_delivery_result("change-b", result_request)
    assert application.publish_delivery_result("change-b", result_request) == result

    request = DeliveryRequest(
        request_id="request-public",
        kind=DeliveryRequestKind.DECISION,
        outcome_id="OUT-001",
        summary="Choose the exact source.",
        options=(DeliveryRequestOption(option_id="local", label="Local source"),),
    )
    blocked = application.transition_delivery(
        "change-c",
        BlockDelivery(
            outcome_id="OUT-001",
            claim_id=block_launch.claim.claim_id,
            block_id="block-public",
            reason="A source decision is required.",
            unblock_condition="The source is selected.",
            expected_evidence=("Selected source",),
            locators=("COM-001",),
            request=request,
        ),
    )
    assert blocked.requests == (request,)
    assert blocked.block is not None
    assert blocked.block.request_id == request.request_id


def test_work_item_queries_do_not_resolve_integration_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    application, _runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-b": DeliveryStage.COMPLETED, "change-a": DeliveryStage.PLANNING},
    )
    resolved = []
    integration_context = application._workspace_manager.integration_context

    def record_resolution(change_id: str):
        resolved.append(change_id)
        return integration_context(change_id)

    monkeypatch.setattr(application._workspace_manager, "integration_context", record_resolution)

    listed = application.list_work_items()
    shown = application.show_work_item("change-a", "OUT-001")
    grouped = application.list_work_item_groups()
    detailed = application.show_work_item_view("change-a", "outcome:OUT-001")
    serialized = json.dumps(
        {
            "listed": [item.model_dump(mode="json") for item in listed],
            "shown": shown.model_dump(mode="json"),
        }
    )

    assert tuple((item.change_id, item.work_item_id) for item in listed) == (
        ("change-a", "OUT-001"),
        ("change-b", "OUT-001"),
        ("change-b", "change-b"),
    )
    assert shown.acceptance == ("The launch is observable.",)
    assert grouped[0].change_id == "change-a"
    assert detailed.card.work_item_id == "OUT-001"
    assert resolved == []
    assert "internal semantic body sentinel" not in serialized
    assert "internal completion body sentinel" not in serialized


def test_abandoned_publication_detail_projects_cleanup_eligibility(tmp_path: Path) -> None:
    application, runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )

    application.abandon_change("change-a", "User stopped the Change")

    detail = application.show_work_item_view("change-a", "publication")

    assert runtimes["change-a"].change_stage() == DeliveryChangeStage.ABANDONED
    assert detail.publication is not None
    assert detail.publication.worktree_cleanup is not None
    assert detail.publication.worktree_cleanup.eligible is True
    assert detail.publication.worktree_cleanup.blocked_reason is None
    assert detail.publication.worktree_cleanup.completion_id is None


def test_abandoned_change_is_removed_from_current_work_portfolio(tmp_path: Path) -> None:
    application, _runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )

    application.abandon_change("change-a", "User stopped the Change")

    assert application.list_work_item_groups() == ()
    assert application.portfolio_operating_view().statuses == ()


def test_publication_detail_projects_preserved_target_sync_conflict(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    reviewed_head = coordinator.show("change-a").last_reviewed_commit
    conflict = ChangeTargetSyncConflictState.create(
        operation_id="sync-view",
        change_id="change-a",
        target_head="2" * 40,
        change_head_before=reviewed_head,
        conflict_paths=("src/app.py", "tests/test_app.py"),
    )
    runtimes["change-a"].capture_target_sync_conflict(
        "sync-view",
        "2" * 40,
        datetime.now(UTC),
        ("target synchronization merge conflict", "conflict-path:src/app.py"),
    )
    coordinator.update(coordinator.show("change-a").model_copy(update={"target_sync_conflict": conflict}))

    detail = application.show_work_item_view("change-a", "publication")

    assert detail.publication is not None
    assert detail.publication.target_sync_conflict is not None
    assert detail.publication.target_sync_conflict.model_dump() == {
        "conflict_id": conflict.conflict_id,
        "operation_id": conflict.operation_id,
        "target_head": conflict.target_head,
        "change_head_before": conflict.change_head_before,
        "conflict_paths": conflict.conflict_paths,
    }


def test_dirty_abandoned_publication_detail_blocks_cleanup(tmp_path: Path) -> None:
    application, _runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    application.abandon_change("change-a", "User stopped the Change")
    (coordinator.show("change-a").worktree_path / "notes.txt").write_text("keep me\n", encoding="utf-8")

    detail = application.show_work_item_view("change-a", "publication")

    assert detail.publication is not None
    assert detail.publication.worktree_cleanup is not None
    assert detail.publication.worktree_cleanup.eligible is False
    assert detail.publication.worktree_cleanup.blocked_reason == "worktree-attention"


def test_change_level_legacy_context_requires_completed_building_change(tmp_path: Path) -> None:
    completed_root = tmp_path / "completed"
    completed_root.mkdir()
    completed_application, _runtimes, _coordinator, _state_root = _portfolio(
        completed_root,
        {"change-a": DeliveryStage.COMPLETED},
    )

    context = completed_application.show_operator_context("change-a", "change-a")

    assert context.stage == DeliveryStage.COMPLETED
    assert completed_application.acquire_frontier_work().launch_packages == ()
    assert completed_application.portfolio_operating_view().queued_for_orchestration == ()

    in_flight_root = tmp_path / "in-flight"
    in_flight_root.mkdir()
    in_flight_application, _runtimes, _coordinator, _state_root = _portfolio(
        in_flight_root,
        {"change-a": DeliveryStage.PLANNING},
    )
    with pytest.raises(PortfolioApplicationError, match="legacy attention context"):
        in_flight_application.show_operator_context("change-a", "change-a")


def test_operator_request_resolution_updates_context_and_resumed_plan(tmp_path: Path) -> None:
    application, runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.PLANNING},
    )
    launch = application.acquire_frontier_work().launch_packages[0]
    context = application.show_operator_context("change-a", "OUT-001")
    serialized_claim = context.active_claim.model_dump(mode="json") if context.active_claim else {}
    assert serialized_claim == {
        "attempt_id": launch.claim.attempt_id,
        "claim_id": launch.claim.claim_id,
        "started_at": launch.claim.started_at,
        "worker_role": "planner",
        "task_id": None,
    }
    assert not {"owner_id", "process_id", "output", "reviewer_id"} & serialized_claim.keys()
    before = runtimes["change-a"].frontier_bytes()
    with pytest.raises(DeliveryRuntimeConflictError, match="execution identity"):
        application.recover_claim("change-a", "OUT-001", "stale-attempt", launch.claim.claim_id)
    assert runtimes["change-a"].frontier_bytes() == before

    request = DeliveryRequest(
        request_id="request-operator",
        kind=DeliveryRequestKind.DECISION,
        outcome_id="OUT-001",
        summary="Choose the source.",
        options=(DeliveryRequestOption(option_id="local", label="Use local source"),),
    )
    application.transition_delivery(
        "change-a",
        BlockDelivery(
            outcome_id="OUT-001",
            claim_id=launch.claim.claim_id,
            block_id="block-operator",
            reason="A decision is required.",
            unblock_condition="The source is selected.",
            expected_evidence=("Selected source",),
            locators=("COM-001",),
            request=request,
        ),
    )
    pending = application.show_operator_context("change-a", "OUT-001")
    assert pending.block is not None
    assert not pending.block.resolved
    resolved = application.resolve_request(
        "change-a",
        request.request_id,
        DeliveryRequestResolution(selected_option_id="local", response_text="Use the checked-in source."),
    )
    assert resolved.resolution is not None
    current = application.show_operator_context("change-a", "OUT-001")
    assert current.block is not None
    assert current.block.resolved
    resumed = application.acquire_frontier_work().launch_packages[0]
    plan_context = application.show_plan_context(
        "change-a",
        "OUT-001",
        resumed.claim.attempt_id,
        resumed.claim.claim_id,
    )
    assert plan_context.requests[0].resolution == resolved.resolution


def test_resolved_implementation_block_reacquires_from_reviewed_boundary(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    launch = application.acquire_frontier_work().launch_packages[0]
    reviewed_head = coordinator.show("change-a").last_reviewed_commit
    candidate_path = launch.worktree_path / "candidate.txt"
    candidate_path.write_text("preserved Builder candidate\n", encoding="utf-8")
    _git(launch.worktree_path, "add", candidate_path.name)
    _git(launch.worktree_path, "commit", "-m", "preserve Builder candidate")
    candidate_head = _git(launch.worktree_path, "rev-parse", "HEAD")
    request = DeliveryRequest(
        request_id="request-implementation",
        kind=DeliveryRequestKind.ACTION,
        outcome_id="OUT-001",
        summary="Repair the external runtime prerequisite.",
    )

    blocked = application.transition_delivery(
        "change-a",
        BlockDelivery(
            outcome_id="OUT-001",
            claim_id=launch.claim.claim_id,
            block_id="block-implementation",
            reason="The external runtime prerequisite is unavailable.",
            unblock_condition="The prerequisite is repaired.",
            expected_evidence=("Successful implementation proof",),
            locators=("TASK-001",),
            request=request,
            resume_commit=candidate_head,
        ),
    )

    assert blocked.block is not None
    assert blocked.block.resume_commit == candidate_head
    assert blocked.active_claim is None
    coordination = coordinator.show("change-a")
    assert coordination.last_reviewed_commit == reviewed_head
    assert coordination.writer is None
    assert _git(launch.worktree_path, "rev-parse", "HEAD") == reviewed_head
    assert (
        _git(
            launch.worktree_path,
            "rev-parse",
            f"refs/owlbear/attempts/change-a/{launch.claim.attempt_id}",
        )
        == candidate_head
    )

    resolved = application.resolve_request(
        "change-a",
        request.request_id,
        DeliveryRequestResolution(response_text="The prerequisite is repaired."),
    )
    resumed = application.acquire_frontier_work().launch_packages

    assert len(resumed) == 1
    resumed_launch = resumed[0]
    assert resumed_launch.claim.claim_id != launch.claim.claim_id
    assert resumed_launch.source_head == reviewed_head
    assert resumed_launch.last_reviewed_commit == reviewed_head
    build_context = application.show_build_context(
        "change-a",
        resumed_launch.outcome_id,
        resumed_launch.claim.attempt_id,
        resumed_launch.claim.claim_id,
    )
    assert build_context.requests[0].resolution == resolved.resolution
    assert runtimes["change-a"].show_binding("OUT-001").active_claim_id == resumed_launch.claim.claim_id


def test_recover_legacy_released_implementation_block_reanchors_candidate(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    launch = application.acquire_frontier_work().launch_packages[0]
    reviewed_head = coordinator.show("change-a").last_reviewed_commit
    candidate_path = launch.worktree_path / "candidate.txt"
    candidate_path.write_text("legacy blocked candidate\n", encoding="utf-8")
    _git(launch.worktree_path, "add", candidate_path.name)
    _git(launch.worktree_path, "commit", "-m", "legacy blocked candidate")
    candidate_head = _git(launch.worktree_path, "rev-parse", "HEAD")
    request = DeliveryRequest(
        request_id="request-legacy-implementation",
        kind=DeliveryRequestKind.ACTION,
        outcome_id="OUT-001",
        summary="Repair the legacy runtime prerequisite.",
        resolution=DeliveryRequestResolution(response_text="The prerequisite is repaired."),
    )
    application._workspace_manager.release_writer_at_head(
        "change-a",
        launch.claim.claim_id,
        candidate_head,
    )
    frontier = DeliveryFrontier.model_validate_json(runtimes["change-a"].frontier_bytes())
    block = DeliveryBlock(
        block_id="block-legacy-implementation",
        reason="The legacy runtime prerequisite is unavailable.",
        unblock_condition="The prerequisite is repaired.",
        expected_evidence=("Successful implementation proof",),
        locators=("TASK-001",),
        request_id=request.request_id,
        resolution_note=request.resolution.response_text,
        resolution_locators=(request.request_id,),
        resume_commit=candidate_head,
    )
    binding = frontier.bindings[0].model_copy(update={"active_claim": None, "block": block, "requests": (request,)})
    (state_root / "changes/change-a/frontier.json").write_bytes(
        _canonical(frontier.model_copy(update={"bindings": (binding,)}))
    )

    receipt = application.recover_blocked_implementation(
        "change-a",
        "OUT-001",
        candidate_head,
        reviewed_head,
        "recover-legacy-implementation",
        confirmed_recovery=True,
    )

    assert receipt.expected_resume_commit == candidate_head
    assert receipt.reviewed_head == reviewed_head
    assert _git(launch.worktree_path, "rev-parse", "HEAD") == reviewed_head
    assert _git(launch.worktree_path, "rev-parse", receipt.preserved_ref) == candidate_head
    resumed = application.acquire_frontier_work().launch_packages
    assert len(resumed) == 1
    assert resumed[0].source_head == reviewed_head


def test_requestless_clear_requires_evidence_and_exact_outcome(tmp_path: Path) -> None:
    application, runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.PLANNING},
    )
    launch = application.acquire_frontier_work().launch_packages[0]
    application.transition_delivery(
        "change-a",
        BlockDelivery(
            outcome_id="OUT-001",
            claim_id=launch.claim.claim_id,
            block_id="block-manual",
            reason="Verification is pending.",
            unblock_condition="Verification is recorded.",
            expected_evidence=("Verification locator",),
            locators=("RESULT-001",),
        ),
    )
    before = runtimes["change-a"].frontier_bytes()
    with pytest.raises(ValueError, match="operator note and locators"):
        application.clear_block("change-a", "OUT-001", "block-manual", "Verified.", ())
    assert runtimes["change-a"].frontier_bytes() == before
    cleared = application.clear_block(
        "change-a",
        "OUT-001",
        "block-manual",
        "Verified.",
        ("RESULT-001",),
    )
    assert cleared.block is not None
    assert cleared.block.resolved


def test_administrative_move_updates_live_projection_and_rejects_same_stage(tmp_path: Path) -> None:
    application, runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    assert application.show_work_item("change-a", "OUT-001").projection.stage.value == "completed"
    preview = application.preview_administrative_move("change-a", "OUT-001", DeliveryStage.PLANNING)
    move = AdministrativeDeliveryMove(
        move_id="move-operator",
        outcome_id="OUT-001",
        target=DeliveryStage.PLANNING,
        reason="Operator evidence invalidated the reviewed result.",
        expected_version=preview.snapshot_version,
    )
    result = application.administrative_move("change-a", move)
    assert result.invalidated_outcome_ids == ("OUT-001",)
    assert application.show_work_item("change-a", "OUT-001").projection.stage.value == "planning"
    before = runtimes["change-a"].frontier_bytes()
    with pytest.raises(DeliveryRuntimeConflictError, match="earlier stage"):
        application.preview_administrative_move("change-a", "OUT-001", DeliveryStage.PLANNING)
    assert runtimes["change-a"].frontier_bytes() == before


def _review_product_change(coordinator: PortfolioCoordinator, change_id: str, content: str) -> tuple[str, str]:
    coordination = coordinator.show(change_id)
    target_head = _git(coordination.worktree_path, "rev-parse", coordination.integration_target)
    (coordination.worktree_path / "product.txt").write_text(content, encoding="utf-8")
    _git(coordination.worktree_path, "add", "product.txt")
    _git(coordination.worktree_path, "commit", "-m", f"reviewed {change_id}")
    reviewed = _git(coordination.worktree_path, "rev-parse", "HEAD")
    coordinator.update(coordination.model_copy(update={"last_reviewed_commit": reviewed}))
    return target_head, reviewed


def _publish_merge_conflict_attention(
    runtimes: dict[str, DeliveryRuntime],
    state_root: Path,
    change_id: str,
    change_head: str,
    target_head: str,
) -> DeliveryIntegrationAttention:
    attention = DeliveryIntegrationAttention(
        attention_id="a" * 64,
        code=DeliveryIntegrationAttentionCode.MERGE_CONFLICT,
        change_id=change_id,
        change_head=change_head,
        target_head=target_head,
        integration_target="main",
        diagnostics=("merge conflict",),
        retry_condition=(
            "Repair admission is retired; resolve the retained attention or recover the exact legacy claim."
        ),
    )
    runtime = runtimes[change_id]
    frontier_path = state_root / "changes" / change_id / "frontier.json"
    frontier = DeliveryFrontier.model_validate_json(runtime.frontier_bytes())
    frontier_path.write_bytes(_canonical(frontier.model_copy(update={"integration_attention": attention})))
    return attention


def _activate_legacy_integration_repair(
    application: PortfolioApplication,
    runtimes: dict[str, DeliveryRuntime],
    coordinator: PortfolioCoordinator,
    state_root: Path,
    change_id: str,
):
    claim = application._new_claim(DeliveryWorkerRole.INTEGRATION_REPAIRER, None)
    runtime = runtimes[change_id]
    frontier_path = state_root / "changes" / change_id / "frontier.json"
    frontier = DeliveryFrontier.model_validate_json(runtime.frontier_bytes())
    frontier_path.write_bytes(_canonical(frontier.model_copy(update={"integration_repair_claim": claim})))
    writer = ChangeWriter(
        attempt_id=claim.attempt_id,
        claim_id=claim.claim_id,
        actor_id=claim.owner_id,
        process_id=claim.process_id,
        claimed_at=claim.started_at,
        job_id=1,
        kind="repair",
    )
    coordination = coordinator.acquire(change_id, writer)
    assert coordination.writer == writer
    return claim


def test_acquisition_does_not_create_integration_repair_claim(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    _target_before, reviewed = _review_product_change(coordinator, "change-a", "change side\n")
    repository = tmp_path / "repository"
    (repository / "product.txt").write_text("target side\n", encoding="utf-8")
    _git(repository, "add", "product.txt")
    _git(repository, "commit", "-m", "concurrent target")
    _git(repository, "update-ref", "refs/remotes/origin/main", "HEAD")
    target_head = _git(repository, "rev-parse", "main")
    application._workspace_manager.refresh_integration_target("change-a")
    _publish_merge_conflict_attention(runtimes, state_root, "change-a", reviewed, target_head)

    acquired = application.acquire_frontier_work()

    assert acquired.integration_attention[0].code == DeliveryIntegrationAttentionCode.MERGE_CONFLICT
    assert runtimes["change-a"].integration_repair_claim() is None
    assert coordinator.show("change-a").writer is None


def test_acquisition_does_not_refresh_target_head(tmp_path: Path) -> None:
    application, _runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    initial_target = coordinator.show("change-a").target_head
    repository = tmp_path / "repository"
    (repository / "product.txt").write_text("target side\n", encoding="utf-8")
    _git(repository, "add", "product.txt")
    _git(repository, "commit", "-m", "concurrent target")
    _git(repository, "update-ref", "refs/remotes/origin/main", "HEAD")

    application.acquire_frontier_work()

    assert coordinator.show("change-a").target_head == initial_target


def _prepare_legacy_integration_repair(tmp_path: Path):
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    _target_before, reviewed = _review_product_change(coordinator, "change-a", "change side\n")
    repository = tmp_path / "repository"
    (repository / "product.txt").write_text("target side\n", encoding="utf-8")
    _git(repository, "add", "product.txt")
    _git(repository, "commit", "-m", "concurrent target")
    _git(repository, "update-ref", "refs/remotes/origin/main", "HEAD")
    target_head = _git(repository, "rev-parse", "main")
    application._workspace_manager.refresh_integration_target("change-a")
    _publish_merge_conflict_attention(runtimes, state_root, "change-a", reviewed, target_head)
    claim = _activate_legacy_integration_repair(application, runtimes, coordinator, state_root, "change-a")
    return application, runtimes, coordinator, state_root, reviewed, claim


def test_repair_recovery_preserves_worktree_without_reacquisition(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root, reviewed, first_claim = _prepare_legacy_integration_repair(
        tmp_path
    )
    worktree = coordinator.show("change-a").worktree_path
    directory_fd = os.open(worktree, os.O_RDONLY)
    try:
        original_directory = os.fstat(directory_fd)

        recovered = application.recover_integration_repair_claim(
            "change-a",
            first_claim.attempt_id,
            first_claim.claim_id,
        )
        acquired = application.acquire_frontier_work()

        assert recovered.preserved_commit == reviewed
        assert os.path.samestat(worktree.stat(), original_directory)
        assert _git(worktree, "rev-parse", "HEAD") == reviewed
        assert acquired.launch_packages == ()
        assert acquired.integration_attention[0].code == DeliveryIntegrationAttentionCode.MERGE_CONFLICT
        assert runtimes["change-a"].integration_repair_claim() is None
    finally:
        os.close(directory_fd)


def _file_bytes(root: Path) -> dict[str, bytes]:
    return {str(path.relative_to(root)): path.read_bytes() for path in root.rglob("*") if path.is_file()}


def test_acquisition_returns_bounded_stage_packages_without_integration_work(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {
            "change-d": DeliveryStage.COMPLETED,
            "change-b": DeliveryStage.IMPLEMENTATION,
            "change-a": DeliveryStage.PLANNING,
        },
    )

    acquired = application.acquire_frontier_work()

    assert tuple(package.change_id for package in acquired.launch_packages) == (
        "change-a",
        "change-b",
    )
    assert tuple(package.claim.worker_role for package in acquired.launch_packages) == (
        DeliveryWorkerRole.PLANNER,
        DeliveryWorkerRole.BUILDER,
    )
    assert acquired.failures == ()
    assert runtimes["change-d"].active_claims() == ()
    assert coordinator.show("change-a").writer is None
    assert coordinator.show("change-b").writer is not None
    assert not (state_root / "capacity.json").exists()

    plan_package, build_package = acquired.launch_packages
    plan_context = application.show_plan_context(
        plan_package.change_id,
        plan_package.outcome_id,
        plan_package.claim.attempt_id,
        plan_package.claim.claim_id,
    )
    build_context = application.show_build_context(
        build_package.change_id,
        build_package.outcome_id,
        build_package.claim.attempt_id,
        build_package.claim.claim_id,
    )
    assert plan_context.outcome.outcome_id == "OUT-001"
    assert build_context.task.task_id == "TASK-001"
    assert build_context.task_digest == build_context.task.digest
    assert build_context.model_dump(mode="json")["task_digest"] == build_context.task.digest
    with pytest.raises(DeliveryRuntimeConflictError, match="execution identity"):
        application.show_plan_context(
            plan_package.change_id,
            plan_package.outcome_id,
            "stale-attempt",
            plan_package.claim.claim_id,
        )
    serialized = "".join(json.dumps(model.model_dump(mode="json")) for model in (acquired, plan_context, build_context))
    for residue in ("intent prose sentinel", "design prose sentinel", '"reviews"', '"receipts"'):
        assert residue not in serialized.lower()


def test_writer_failure_leaves_started_exact_claim_without_false_launch(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {
            "change-a": DeliveryStage.IMPLEMENTATION,
            "change-b": DeliveryStage.PLANNING,
        },
    )
    (tmp_path / "packages/change-b/intent.md").write_text("mutated source\n", encoding="utf-8")

    with patch.object(coordinator, "acquire", side_effect=CoordinationConflictError("injected writer failure")):
        acquired = application.acquire_frontier_work()

    assert acquired.launch_packages == ()
    assert len(acquired.failures) == 2
    failure = acquired.failures[0]
    active = runtimes["change-a"].active_claims()
    assert active[0][1].attempt_id == failure.attempt_id
    assert active[0][1].claim_id == failure.claim_id
    assert runtimes["change-b"].active_claims() == ()
    assert coordinator.show("change-a").writer is None
    recovered = application.recover_claim(
        "change-a",
        "OUT-001",
        failure.attempt_id,
        failure.claim_id,
    )
    assert recovered.status == DeliveryClaimRecoveryStatus.RECOVERED
    assert runtimes["change-a"].active_claims() == ()
    assert not (state_root / "capacity.json").exists()


def test_acquisition_recovers_expired_planning_claim_at_inclusive_boundary(tmp_path: Path) -> None:
    now = ["2026-08-04T00:00:00Z"]
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.PLANNING},
        clock=lambda: now[0],
    )
    first = application.acquire_frontier_work().launch_packages[0]

    now[0] = "2026-08-04T00:59:59Z"
    live = application.acquire_frontier_work()

    assert live.launch_packages == ()
    assert live.failures == ()
    assert runtimes["change-a"].active_claims() == (("OUT-001", first.claim),)

    now[0] = "2026-08-04T01:00:00Z"
    recovered = application.acquire_frontier_work()

    assert recovered.failures == ()
    assert len(recovered.recoveries) == 1
    assert recovered.recoveries[0].status == DeliveryClaimRecoveryStatus.RECOVERED
    assert recovered.recoveries[0].claim_id == first.claim.claim_id
    replacement = recovered.launch_packages[0]
    assert replacement.claim.claim_id != first.claim.claim_id
    assert runtimes["change-a"].active_claims() == (("OUT-001", replacement.claim),)
    assert coordinator.show("change-a").writer is None
    assert not (state_root / "capacity.json").exists()


def test_acquisition_recovers_expired_clean_builder_claim_and_relaunches(tmp_path: Path) -> None:
    now = ["2026-08-04T00:00:00Z"]
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
        clock=lambda: now[0],
    )
    first = application.acquire_frontier_work().launch_packages[0]
    (first.worktree_path / "product.txt").write_text("attempt\n", encoding="utf-8")
    _git(first.worktree_path, "add", "product.txt")
    _git(first.worktree_path, "commit", "-m", "attempt commit")
    attempt_commit = _git(first.worktree_path, "rev-parse", "HEAD")

    now[0] = "2026-08-04T01:00:00Z"
    recovered = application.acquire_frontier_work()

    assert recovered.failures == ()
    assert len(recovered.recoveries) == 1
    assert recovered.recoveries[0].preserved_commit == attempt_commit
    assert recovered.recoveries[0].preserved_ref == (f"refs/owlbear/attempts/change-a/{first.claim.attempt_id}")
    assert _git(first.worktree_path, "rev-parse", recovered.recoveries[0].preserved_ref) == attempt_commit
    replacement = recovered.launch_packages[0]
    assert replacement.claim.claim_id != first.claim.claim_id
    assert replacement.writer is not None
    assert replacement.writer.claim_id == replacement.claim.claim_id
    assert runtimes["change-a"].active_claims() == (("OUT-001", replacement.claim),)
    assert coordinator.show("change-a").writer == replacement.writer
    assert _git(first.worktree_path, "rev-parse", "HEAD") == first.last_reviewed_commit


def test_acquisition_recovers_expired_dirty_builder_claim_and_relaunches(tmp_path: Path) -> None:
    now = ["2026-08-04T00:00:00Z"]
    application, _runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
        clock=lambda: now[0],
    )
    first = application.acquire_frontier_work().launch_packages[0]
    product = first.worktree_path / "product.txt"
    product.write_text("uncommitted attempt\n", encoding="utf-8")

    now[0] = "2026-08-04T01:00:00Z"
    recovered = application.acquire_frontier_work()

    assert recovered.failures == ()
    assert len(recovered.recoveries) == 1
    recovery = recovered.recoveries[0]
    assert recovery.status == DeliveryClaimRecoveryStatus.RECOVERED
    assert recovery.quarantine_commit is not None
    assert recovery.quarantine_ref == f"refs/owlbear/quarantine/change-a/{first.claim.attempt_id}"
    assert _git(first.worktree_path, "rev-parse", recovery.quarantine_ref) == recovery.quarantine_commit
    replacement = recovered.launch_packages[0]
    assert replacement.claim.claim_id != first.claim.claim_id
    assert replacement.writer is not None
    assert coordinator.show("change-a").writer == replacement.writer
    assert _git(first.worktree_path, "status", "--porcelain") == ""
    assert _git(first.worktree_path, "rev-parse", "HEAD") == first.last_reviewed_commit


def test_expired_claim_recovery_failure_does_not_block_independent_change(tmp_path: Path) -> None:
    now = ["2026-08-04T00:00:00Z"]
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {
            "change-a": DeliveryStage.IMPLEMENTATION,
            "change-b": DeliveryStage.PLANNING,
        },
        execution_capacity=2,
        clock=lambda: now[0],
    )
    initial = application.acquire_frontier_work()
    initial_by_change = {package.change_id: package for package in initial.launch_packages}

    now[0] = "2026-08-04T01:00:00Z"
    original_snapshot = application._workspace_manager.recovery_snapshot

    def fail_change_a(change_id: str, attempt_id: str) -> WorkspaceRecoverySnapshot:
        if change_id == "change-a":
            raise subprocess.CalledProcessError(1, ("git", "status"))
        return original_snapshot(change_id, attempt_id)

    with patch.object(application._workspace_manager, "recovery_snapshot", side_effect=fail_change_a):
        recovered = application.acquire_frontier_work()

    assert tuple(package.change_id for package in recovered.launch_packages) == ("change-b",)
    assert len(recovered.failures) == 1
    assert recovered.failures[0].change_id == "change-a"
    assert recovered.failures[0].claim_id == initial_by_change["change-a"].claim.claim_id
    assert len(recovered.recoveries) == 1
    assert recovered.recoveries[0].change_id == "change-b"
    assert runtimes["change-a"].active_claims()
    assert runtimes["change-b"].active_claims()[0][1].claim_id != initial_by_change["change-b"].claim.claim_id
    assert coordinator.show("change-a").writer == initial_by_change["change-a"].writer


def test_malformed_claim_timestamp_does_not_block_independent_change(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {
            "change-a": DeliveryStage.PLANNING,
            "change-b": DeliveryStage.PLANNING,
        },
        execution_capacity=2,
        clock=lambda: "2026-08-04T01:00:00Z",
    )
    initial = application.acquire_frontier_work()
    initial_by_change = {package.change_id: package for package in initial.launch_packages}
    application.recover_claim(
        "change-b",
        initial_by_change["change-b"].outcome_id,
        initial_by_change["change-b"].claim.attempt_id,
        initial_by_change["change-b"].claim.claim_id,
    )
    malformed_path = state_root / "changes/change-a/frontier.json"
    malformed = json.loads(malformed_path.read_bytes())
    malformed["bindings"][0]["active_claim"]["started_at"] = "not-a-timestamp"
    malformed_path.write_bytes((json.dumps(malformed, sort_keys=True, separators=(",", ":")) + "\n").encode())

    recovered = application.acquire_frontier_work()

    assert tuple(package.change_id for package in recovered.launch_packages) == ("change-b",)
    assert len(recovered.failures) == 1
    failure = recovered.failures[0]
    assert failure.change_id == "change-a"
    assert failure.outcome_id == "OUT-001"
    assert failure.claim_id == initial_by_change["change-a"].claim.claim_id
    assert runtimes["change-a"].active_claims()
    assert coordinator.show("change-a").writer is None


def test_execution_capacity_allows_independent_builders_and_planners(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {
            "change-a": DeliveryStage.IMPLEMENTATION,
            "change-b": DeliveryStage.IMPLEMENTATION,
            "change-c": DeliveryStage.PLANNING,
        },
        execution_capacity=3,
    )

    acquired = application.acquire_frontier_work()

    assert tuple(package.change_id for package in acquired.launch_packages) == ("change-a", "change-b", "change-c")
    assert acquired.failures == ()
    assert all(runtimes[change_id].active_claims() for change_id in ("change-a", "change-b", "change-c"))
    assert coordinator.show("change-a").writer is not None
    assert coordinator.show("change-b").writer is not None
    assert coordinator.show("change-c").writer is None
    assert not (state_root / "capacity.json").exists()


@pytest.mark.parametrize("stage", [DeliveryStage.PLANNING])
def test_read_only_claim_recovery_removes_only_exact_runtime_claim(tmp_path: Path, stage: DeliveryStage) -> None:
    application, runtimes, coordinator, state_root = _portfolio(tmp_path, {"change-a": stage})
    package = application.acquire_frontier_work().launch_packages[0]

    recovered = application.recover_claim(
        package.change_id,
        package.outcome_id,
        package.claim.attempt_id,
        package.claim.claim_id,
    )

    assert recovered.status == DeliveryClaimRecoveryStatus.RECOVERED
    assert recovered.preserved_commit is None
    assert runtimes["change-a"].active_claims() == ()
    assert coordinator.show("change-a").writer is None
    assert not (state_root / "capacity.json").exists()


def test_acquisition_leaves_active_planning_claim_occupied_across_instances(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.PLANNING},
    )
    interrupted = application.acquire_frontier_work().launch_packages[0]
    before_coordination = coordinator.show("change-a")
    assert not (state_root / "capacity.json").exists()

    reopened, _reopened_coordinator, _reopened_manager = _reopen_portfolio(
        tmp_path,
        state_root,
        runtimes,
        clock=lambda: "2026-08-04T00:00:00Z",
    )
    resumed = reopened.acquire_frontier_work()

    assert resumed.launch_packages == ()
    assert runtimes["change-a"].active_claims() == (("OUT-001", interrupted.claim),)
    assert coordinator.show("change-a") == before_coordination
    assert not (state_root / "capacity.json").exists()


def test_acquisition_leaves_dirty_build_claim_and_custody_unchanged(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    interrupted = application.acquire_frontier_work().launch_packages[0]
    (interrupted.worktree_path / "product.txt").write_text("uncommitted attempt\n", encoding="utf-8")
    before_coordination = coordinator.show("change-a")
    assert not (state_root / "capacity.json").exists()

    resumed = application.acquire_frontier_work()

    assert resumed.launch_packages == ()
    assert runtimes["change-a"].active_claims() == (("OUT-001", interrupted.claim),)
    assert runtimes["change-a"].show_binding("OUT-001").recovery_attention is None
    assert coordinator.show("change-a") == before_coordination
    assert not (state_root / "capacity.json").exists()
    assert (interrupted.worktree_path / "product.txt").read_text(encoding="utf-8") == "uncommitted attempt\n"


def test_clean_build_recovery_replays_after_workspace_reset(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    package = application.acquire_frontier_work().launch_packages[0]
    worktree = package.worktree_path
    (worktree / "product.txt").write_text("attempt\n", encoding="utf-8")
    _git(worktree, "add", "product.txt")
    _git(worktree, "commit", "-m", "attempt commit")
    attempt_commit = _git(worktree, "rev-parse", "HEAD")

    with (
        patch.object(runtimes["change-a"], "remove_active_claim", side_effect=RuntimeError("injected after reset")),
        pytest.raises(RuntimeError, match="injected"),
    ):
        application.recover_claim(
            package.change_id,
            package.outcome_id,
            package.claim.attempt_id,
            package.claim.claim_id,
        )

    assert _git(worktree, "rev-parse", "HEAD") == package.last_reviewed_commit
    assert coordinator.show("change-a").writer is None
    assert (
        _git(
            worktree,
            "rev-parse",
            f"refs/owlbear/attempts/change-a/{package.claim.attempt_id}",
        )
        == attempt_commit
    )

    recovered = application.recover_claim(
        package.change_id,
        package.outcome_id,
        package.claim.attempt_id,
        package.claim.claim_id,
    )

    assert recovered.status == DeliveryClaimRecoveryStatus.RECOVERED
    assert recovered.preserved_commit == attempt_commit
    assert runtimes["change-a"].active_claims() == ()
    assert not (state_root / "capacity.json").exists()
    with pytest.raises(DeliveryRuntimeConflictError, match="active claim"):
        runtimes["change-a"].transition(RetryDelivery(outcome_id="OUT-001", claim_id=package.claim.claim_id))


@pytest.mark.parametrize("interruption", ["attempt-ref", "worktree-reset"])
def test_clean_build_recovery_replays_each_workspace_interruption(tmp_path: Path, interruption: str) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    package = application.acquire_frontier_work().launch_packages[0]
    product = package.worktree_path / "product.txt"
    product.write_text("attempt\n", encoding="utf-8")
    _git(package.worktree_path, "add", "product.txt")
    _git(package.worktree_path, "commit", "-m", "attempt commit")
    rejected = _git(package.worktree_path, "rev-parse", "HEAD")
    manager = application._workspace_manager
    original_git = manager._git

    def interrupt_after_git(*arguments: str, **kwargs) -> str:
        result = original_git(*arguments, **kwargs)
        checks = {
            "attempt-ref": arguments[:2]
            == ("update-ref", f"refs/owlbear/attempts/change-a/{package.claim.attempt_id}"),
            "worktree-reset": arguments[:2] == ("reset", "--hard"),
        }
        if checks[interruption]:
            message = "injected workspace interruption"
            raise RuntimeError(message)
        return result

    with (
        patch.object(manager, "_git", side_effect=interrupt_after_git),
        pytest.raises(RuntimeError, match="injected workspace interruption"),
    ):
        application.recover_claim(
            package.change_id,
            package.outcome_id,
            package.claim.attempt_id,
            package.claim.claim_id,
        )

    recovered = application.recover_claim(
        package.change_id,
        package.outcome_id,
        package.claim.attempt_id,
        package.claim.claim_id,
    )

    assert recovered.status == DeliveryClaimRecoveryStatus.RECOVERED
    assert recovered.preserved_commit == rejected
    assert _git(package.worktree_path, "rev-parse", "HEAD") == package.last_reviewed_commit
    assert runtimes["change-a"].active_claims() == ()
    assert coordinator.show("change-a").writer is None
    assert not (state_root / "capacity.json").exists()


def test_dirty_build_recovery_preserves_bytes_releases_custody_and_relaunches(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    package = application.acquire_frontier_work().launch_packages[0]
    product = package.worktree_path / "product.txt"
    product.write_text("uncommitted attempt\n", encoding="utf-8")
    branch_head = _git(package.worktree_path, "rev-parse", "HEAD")

    recovered = application.recover_claim(
        package.change_id,
        package.outcome_id,
        package.claim.attempt_id,
        package.claim.claim_id,
    )

    assert recovered.status == DeliveryClaimRecoveryStatus.RECOVERED
    assert recovered.quarantine_commit is not None
    assert recovered.quarantine_ref == f"refs/owlbear/quarantine/change-a/{package.claim.attempt_id}"
    assert _git(package.worktree_path, "rev-parse", recovered.quarantine_ref) == recovered.quarantine_commit
    assert _git(package.worktree_path, "status", "--porcelain") == ""
    assert _git(package.worktree_path, "rev-parse", "HEAD") == package.last_reviewed_commit
    assert runtimes["change-a"].active_claims() == ()
    assert coordinator.show("change-a").writer is None
    assert _git(package.worktree_path, "show", f"{recovered.quarantine_commit}:product.txt") == "uncommitted attempt"
    assert product.read_text(encoding="utf-8") == "baseline\n"
    relaunched = application.acquire_frontier_work().launch_packages[0]
    assert relaunched.claim.claim_id != package.claim.claim_id
    assert relaunched.writer is not None
    assert _git(package.worktree_path, "rev-parse", "HEAD") == branch_head


def test_dirty_build_recovery_replays_after_workspace_cleanup(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    package = application.acquire_frontier_work().launch_packages[0]
    dirty_file = package.worktree_path / "uncommitted.txt"
    dirty_file.write_text("preserve me\n", encoding="utf-8")
    with (
        patch.object(runtimes["change-a"], "remove_active_claim", side_effect=RuntimeError("injected after cleanup")),
        pytest.raises(RuntimeError, match="injected after cleanup"),
    ):
        application.recover_claim(
            package.change_id,
            package.outcome_id,
            package.claim.attempt_id,
            package.claim.claim_id,
        )

    interrupted = coordinator.show("change-a")
    quarantine = interrupted.dirty_worktree_quarantine
    assert quarantine is not None
    assert _git(package.worktree_path, "status", "--porcelain") == ""
    assert _git(package.worktree_path, "rev-parse", "HEAD") == package.last_reviewed_commit
    assert runtimes["change-a"].active_claims() == (("OUT-001", package.claim),)
    assert coordinator.show("change-a").writer is None

    recovered = application.recover_claim(
        package.change_id,
        package.outcome_id,
        package.claim.attempt_id,
        package.claim.claim_id,
    )

    assert recovered.status == DeliveryClaimRecoveryStatus.RECOVERED
    assert recovered.quarantine_commit == quarantine.quarantine_commit
    assert recovered.quarantine_ref == quarantine.quarantine_ref
    assert runtimes["change-a"].active_claims() == ()
    assert coordinator.show("change-a").writer is None
    relaunched = application.acquire_frontier_work().launch_packages[0]
    assert relaunched.claim.claim_id != package.claim.claim_id
    assert relaunched.writer is not None


def test_dirty_build_recovery_replays_after_restart_before_writer_release(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    package = application.acquire_frontier_work().launch_packages[0]
    worktree = package.worktree_path
    (worktree / "product.txt").write_text("attempt\n", encoding="utf-8")
    _git(worktree, "add", "product.txt")
    _git(worktree, "commit", "-m", "attempt commit")
    rejected = _git(worktree, "rev-parse", "HEAD")
    (worktree / "uncommitted.bin").write_bytes(b"preserve\x00\xff")

    with (
        patch.object(coordinator, "release", side_effect=CoordinationConflictError("injected before release")),
        pytest.raises(CoordinationConflictError, match="injected before release"),
    ):
        application.recover_claim(
            package.change_id,
            package.outcome_id,
            package.claim.attempt_id,
            package.claim.claim_id,
        )

    interrupted = coordinator.show("change-a")
    quarantine = interrupted.dirty_worktree_quarantine
    assert quarantine is not None
    assert quarantine.base_head == rejected
    assert interrupted.writer == package.writer
    assert _git(worktree, "rev-parse", "HEAD") == package.last_reviewed_commit

    recovered = application.recover_claim(
        package.change_id,
        package.outcome_id,
        package.claim.attempt_id,
        package.claim.claim_id,
    )

    assert recovered.status == DeliveryClaimRecoveryStatus.RECOVERED
    assert recovered.quarantine_commit == quarantine.quarantine_commit
    assert runtimes["change-a"].active_claims() == ()
    assert coordinator.show("change-a").writer is None


def test_dirty_build_recovery_retains_custody_when_preservation_fails(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    package = application.acquire_frontier_work().launch_packages[0]
    dirty_file = package.worktree_path / "uncommitted.bin"
    dirty_file.write_bytes(b"preserve\x00\xff")

    with patch.object(
        application._workspace_manager,
        "quarantine_dirty_worktree",
        side_effect=RuntimeError("injected preservation failure"),
    ):
        retained = application.recover_claim(
            package.change_id,
            package.outcome_id,
            package.claim.attempt_id,
            package.claim.claim_id,
        )

    assert retained.status == DeliveryClaimRecoveryStatus.ATTENTION
    assert retained.attention is not None
    assert retained.attention.custody_retained
    assert "injected preservation failure" in retained.attention.reason
    assert dirty_file.read_bytes() == b"preserve\x00\xff"
    assert runtimes["change-a"].active_claims() == (("OUT-001", package.claim),)
    assert coordinator.show("change-a").writer == package.writer
    assert not (state_root / "capacity.json").exists()
    assert coordinator.show("change-a").dirty_worktree_quarantine is None


def test_mismatched_build_custody_retains_current_writer_and_attention(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    package = application.acquire_frontier_work().launch_packages[0]
    coordinator.release("change-a", package.claim.claim_id)
    mismatched = ChangeWriter(
        attempt_id="other-attempt",
        claim_id="other-claim",
        actor_id="other-owner",
        process_id="other-process",
        claimed_at="2026-08-04T00:01:00Z",
        job_id=2,
        kind="build",
    )
    coordinator.acquire("change-a", mismatched)

    retained = application.recover_claim(
        package.change_id,
        package.outcome_id,
        package.claim.attempt_id,
        package.claim.claim_id,
    )

    assert retained.status == DeliveryClaimRecoveryStatus.ATTENTION
    assert retained.attention is not None
    assert retained.attention.writer_claim_id == mismatched.claim_id
    assert runtimes["change-a"].active_claims()[0][1] == package.claim
    assert coordinator.show("change-a").writer == mismatched
    assert not (state_root / "capacity.json").exists()
