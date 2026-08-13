from __future__ import annotations

import hashlib
import itertools
import json
import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from threading import Event
from unittest.mock import Mock, patch, sentinel

import pytest

from owlbear_delivery import (
    AdministrativeDeliveryMove,
    CapacityLedger,
    ChangeBranchPublicationReceipt,
    ChangeBranchPublisher,
    AdvanceDelivery,
    BlockDelivery,
    CompletedHistoryCatalog,
    ChangeWorkspaceManager,
    ChangeWriter,
    CompletionReceipt,
    CoordinationConflictError,
    DeliveryApplicationLoadError,
    DeliveryCommitment,
    DeliveryCommitmentClass,
    DeliveryAdmissionConflictError,
    DeliveryAdmissionRequest,
    DeliveryAuthorityRegistry,
    DeliveryClaimRecoveryResult,
    DeliveryClaimRecoveryStatus,
    DeliveryChangeStage,
    DeliveryContract,
    DeliveryCheckpointPublicationState,
    DeliveryCheckpointTrigger,
    DeliveryCheckpointTriggerKind,
    DeliveryFinalizationInvalidationReceipt,
    DeliveryFinalizationReceipt,
    DeliveryFrontier,
    DeliveryIntegrationAttention,
    DeliveryIntegrationAttentionCode,
    DeliveryIntegrationRepair,
    DeliveryIntegrationRepairAuthorityAttention,
    DeliveryIntegrationRepairReview,
    DeliveryObservation,
    DeliveryObservationReceipt,
    DeliveryOutcome,
    DeliveryPendingCheckpoint,
    DeliveryPlanScope,
    DeliveryRequest,
    DeliveryRequestKind,
    DeliveryRequestOption,
    DeliveryRequestResolution,
    DeliveryReview,
    DeliveryReviewReceipt,
    DeliveryRolePolicy,
    DeliveryRuntime,
    DeliveryRuntimeConflictError,
    DeliveryStage,
    DeliveryStartupConfig,
    DeliveryTaskDefinition,
    DeliveryTaskResult,
    DeliveryWorkerRole,
    FinalizationVerificationScope,
    FinalizeDeliveryChange,
    DesignPackageManifest,
    DesignPackageConflictError,
    DesignPackageStore,
    DraftPullRequestPublicationReceipt,
    CreateOrReconcileDraftPullRequest,
    DraftPullRequestPublisher,
    MarkChangePullRequestReady,
    GeneratedPullRequestSummaryReceipt,
    OutcomeAuthorityBinding,
    ObserveChangePublicationChecks,
    PortfolioApplication,
    PortfolioApplicationConfig,
    PortfolioApplicationDependencies,
    PortfolioApplicationError,
    PortfolioApplicationHooks,
    PortfolioCoordinator,
    PublicationCheckSnapshot,
    PublishDeliveryPlan,
    PublishDeliveryResult,
    RetryDelivery,
    load_delivery_application,
)
from owlbear_delivery.integration_verification import (
    INTEGRATION_VERIFICATION_PROFILE_PATH,
)
from owlbear_delivery.publication_provider import (
    PublicationProviderError,
    PublicationProviderFailureCode,
    PublicationPullRequest,
    PublicationRepository,
)
from owlbear_delivery.runtime_transaction import RuntimeTransaction


def _git(repository: Path, *arguments: str) -> str:
    return subprocess.run(
        ("git", "-C", str(repository), *arguments),
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _git_ref_exists(repository: Path, reference: str) -> bool:
    return (
        subprocess.run(
            ("git", "-C", str(repository), "rev-parse", "--verify", reference),
            check=False,
            capture_output=True,
        ).returncode
        == 0
    )


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


def _draft_receipt(head: str) -> DraftPullRequestPublicationReceipt:
    payload = {
        "schema_version": 1,
        "operation_id": "pull-request-operation",
        "change_id": "change-a",
        "repository": "example/project",
        "number": 7,
        "node_id": "PR_7",
        "head_branch": "owlbear/change/change-a",
        "head_sha": head,
        "base_branch": "main",
        "provider_evidence_digest": "2" * 64,
    }
    return DraftPullRequestPublicationReceipt(receipt_id=_receipt_id(payload), **payload)


def _summary_receipt(head: str) -> GeneratedPullRequestSummaryReceipt:
    payload = {
        "schema_version": 1,
        "operation_id": "summary-operation",
        "change_id": "change-a",
        "repository": "example/project",
        "number": 7,
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
    application: PortfolioApplication,
    change_id: str,
    exact_head: str,
    *,
    script: str = "pass",
) -> FinalizeDeliveryChange:
    repository = application._workspace_manager.repository  # noqa: SLF001 - test authority setup.
    profile_path = repository / INTEGRATION_VERIFICATION_PROFILE_PATH
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    profile_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "pass_environment": [],
                "steps": [
                    {
                        "step_id": "finalization-check",
                        "argv": [sys.executable, "-c", script],
                        "cwd": ".",
                        "timeout_seconds": 5,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    _git(repository, "add", INTEGRATION_VERIFICATION_PROFILE_PATH)
    _git(repository, "commit", "-m", "add finalization verification authority")
    target_head = _git(repository, "rev-parse", "main")
    _git(repository, "update-ref", "refs/remotes/origin/main", target_head)
    context = application.show_finalization_context(change_id)
    proof = application.run_finalization_verification(change_id)
    operation_id = f"finalize-{change_id}"
    observed_at = datetime(2026, 8, 11, 13, tzinfo=UTC)
    observations = tuple(
        DeliveryObservationReceipt.create(
            DeliveryObservation(
                change_id=change_id,
                task_or_finalization_id=operation_id,
                step_id=step.step_id,
                exact_commit=exact_head,
                observation_kind="engine-finalization-proof",
                command_or_procedure=" ".join(step.argv),
                exit_status_or_artifact_locator="exit:0",
                observer_or_runner_identity="engine",
                observed_at=observed_at,
            )
        )
        for step in proof.steps
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
        verification_run_id=proof.run_id,
        target_ref=context.target_ref,
        target_head=context.target_head,
        target_provenance=context.target_provenance,
        target_observed_at=proof.target_observed_at,
        proof_scope=proof.proof_scope,
        profile_digest=context.profile_digest,
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
    path.parent.mkdir(parents=True)
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
        DeliveryRolePolicy(
            worker_role=DeliveryWorkerRole.INTEGRATION_REPAIRER,
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


def _portfolio(  # noqa: PLR0913
    tmp_path: Path,
    stages: dict[str, DeliveryStage],
    *,
    writer_capacity: int = 1,
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
    state_root = tmp_path / "state"
    package_root = tmp_path / "packages"
    coordinator = PortfolioCoordinator(state_root, capacity=writer_capacity)
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
        coordination = manager.create(change_id)
        runtimes[change_id] = _runtime(state_root, contract, manager, stage, coordination.last_reviewed_commit)
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


def test_finalization_uses_managed_head_and_invalidates_observed_drift(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    coordination = coordinator.show("change-a")
    exact_head = coordination.last_reviewed_commit
    request = _finalization_request(application, "change-a", exact_head)

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
    assert runtimes["change-a"].change_stage() == DeliveryChangeStage.ACTIVE_DELIVERY
    assert application.list_integration_attention() == ()


def test_finalization_context_binds_profile_to_engine_resolved_target(tmp_path: Path) -> None:
    application, _runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    repository = tmp_path / "repository"
    profile_path = repository / INTEGRATION_VERIFICATION_PROFILE_PATH
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    profile_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "pass_environment": ["PATH"],
                "steps": [
                    {
                        "step_id": "target-tests",
                        "argv": ["python", "-m", "pytest"],
                        "cwd": ".",
                        "timeout_seconds": 60,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    _git(repository, "add", INTEGRATION_VERIFICATION_PROFILE_PATH)
    _git(repository, "commit", "-m", "add target verification authority")
    target_head = _git(repository, "rev-parse", "main")
    _git(repository, "update-ref", "refs/remotes/origin/main", target_head)
    change_head = coordinator.show("change-a").last_reviewed_commit

    context = application.show_finalization_context("change-a")

    assert context.change_head == change_head
    assert context.reviewed_change_head == change_head
    assert context.target_branch == "main"
    assert context.target_ref == "refs/remotes/origin/main"
    assert context.target_head == target_head
    assert context.proof_scope is FinalizationVerificationScope.CHANGE_HEAD_PROFILE
    assert context.profile.steps[0].step_id == "target-tests"
    assert context.profile_digest == hashlib.sha256(profile_path.read_bytes()).hexdigest()
    assert context.publication_phase.value == "ready-for-finalization"


def test_finalization_context_reports_existing_exact_finalization_head(tmp_path: Path) -> None:
    application, _runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    exact_head = coordinator.show("change-a").last_reviewed_commit
    request = _finalization_request(application, "change-a", exact_head)
    receipt = application.finalize_change("change-a", request)

    context = application.show_finalization_context("change-a")

    assert context.finalization_id == receipt.finalization_id
    assert context.finalized_head == exact_head
    assert context.change_head == exact_head
    assert context.target_provenance.value == "cached-remote-tracking"
    assert context.proof_scope is FinalizationVerificationScope.CHANGE_HEAD_PROFILE
    proof = application._finalization_verification_store.read(request.verification_run_id)  # noqa: SLF001
    assert proof is not None
    assert proof.target_provenance.value == "cached-remote-tracking"
    assert proof.proof_scope is FinalizationVerificationScope.CHANGE_HEAD_PROFILE
    assert proof.target_observed_at == request.target_observed_at
    assert receipt.target_provenance == "cached-remote-tracking"
    assert receipt.target_observed_at == request.target_observed_at


def test_finalization_rejects_divergent_local_and_cached_target(tmp_path: Path) -> None:
    application, runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    repository = application._workspace_manager.repository  # noqa: SLF001 - test authority setup.
    profile_path = repository / INTEGRATION_VERIFICATION_PROFILE_PATH
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    profile_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "pass_environment": [],
                "steps": [
                    {
                        "step_id": "finalization-check",
                        "argv": [sys.executable, "-c", "pass"],
                        "cwd": ".",
                        "timeout_seconds": 5,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    _git(repository, "add", INTEGRATION_VERIFICATION_PROFILE_PATH)
    _git(repository, "commit", "-m", "add finalization verification authority")
    cached_target = _git(repository, "rev-parse", "main")
    _git(repository, "update-ref", "refs/remotes/origin/main", cached_target)
    (repository / "local-only-target.txt").write_text("local target moved\n", encoding="utf-8")
    _git(repository, "add", "local-only-target.txt")
    _git(repository, "commit", "-m", "move local target only")

    with pytest.raises(PortfolioApplicationError, match="finalization context"):
        application.show_finalization_context("change-a")

    assert runtimes["change-a"].finalization() is None


def test_finalization_rejects_target_move_after_engine_proof(tmp_path: Path) -> None:
    application, runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    exact_head = runtimes["change-a"].bindings()[0].results[0].completed_commit
    request = _finalization_request(application, "change-a", exact_head)
    repository = application._workspace_manager.repository  # noqa: SLF001 - test authority setup.
    (repository / "target-moved.txt").write_text("target moved\n", encoding="utf-8")
    _git(repository, "add", "target-moved.txt")
    _git(repository, "commit", "-m", "move target after proof")
    _git(repository, "update-ref", "refs/remotes/origin/main", "main")

    with pytest.raises(PortfolioApplicationError, match="current target authority"):
        application.finalize_change("change-a", request)

    assert runtimes["change-a"].finalization() is None


def test_finalization_rejects_target_authority_mismatch(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    exact_head = coordinator.show("change-a").last_reviewed_commit
    request = _finalization_request(application, "change-a", exact_head).model_copy(update={"target_head": "f" * 40})

    with pytest.raises(PortfolioApplicationError, match="current target authority"):
        application.finalize_change("change-a", request)

    assert runtimes["change-a"].finalization() is None


def test_finalization_rejects_missing_engine_proof_receipt(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    exact_head = coordinator.show("change-a").last_reviewed_commit
    request = _finalization_request(application, "change-a", exact_head).model_copy(
        update={"verification_run_id": "d" * 64}
    )

    with pytest.raises(PortfolioApplicationError, match="persisted engine proof run"):
        application.finalize_change("change-a", request)

    assert runtimes["change-a"].finalization() is None


def test_finalization_rejects_failed_engine_proof(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    exact_head = coordinator.show("change-a").last_reviewed_commit
    request = _finalization_request(application, "change-a", exact_head, script="raise SystemExit(1)")

    with pytest.raises(PortfolioApplicationError, match="passing engine proof run"):
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
    receipt = application.finalize_change("change-a", _finalization_request(application, "change-a", exact_head))
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
    application._draft_pull_request_publisher = publisher  # noqa: SLF001
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
    assert application._workspace_manager.observed_change_head("change-a") == exact_head  # noqa: SLF001
    assert runtimes["change-a"].change_stage() == DeliveryChangeStage.ACTIVE_DELIVERY
    assert pull_requests[0].draft is True
    assert provider.set_pull_request_draft_state.call_count == 3


def test_observe_acceptance_completes_once_and_replays_without_provider_io(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    runtime = runtimes["change-a"]
    exact_head = coordinator.show("change-a").last_reviewed_commit
    finalization = application.finalize_change(
        "change-a",
        _finalization_request(application, "change-a", exact_head),
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
    application._draft_pull_request_publisher = publisher  # noqa: SLF001
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
    assert view.draft_design_change_ids == ("draft-change",)
    assert tuple(item.kind.value for item in view.guidance) == ("resume-design",)


def test_portfolio_operating_view_counts_design_reentry_as_intervention(tmp_path: Path) -> None:
    application, _runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.DESIGN},
    )

    view = application.portfolio_operating_view()

    assert tuple(item.item_key for item in view.interventions) == ("outcome:OUT-001",)
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
    branch_publisher.publish.return_value = _branch_receipt(head)
    pull_request_publisher = Mock()
    pull_request_publisher.publish.return_value = _draft_receipt(head)
    pull_request_publisher.update_generated_summary.return_value = _summary_receipt(head)
    application._change_branch_publisher = branch_publisher  # noqa: SLF001
    application._draft_pull_request_publisher = pull_request_publisher  # noqa: SLF001

    result = application.reconcile_change_checkpoint("change-a")
    replayed = application.reconcile_change_checkpoint("change-a")

    assert result.reconciled
    assert result.state.published_head == head
    assert result.state.pending_checkpoint is None
    assert replayed.reconciled
    assert replayed.attempted_head is None
    assert branch_publisher.publish.call_count == 1
    assert pull_request_publisher.publish.call_count == 1
    assert pull_request_publisher.update_generated_summary.call_count == 1
    request = pull_request_publisher.publish.call_args.args[0]
    assert request.published_head == head
    assert "Verified Outcome `OUT-001`" in request.generated_summary


def test_reconcile_derives_bounded_provider_text_from_authored_titles(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    runtime = runtimes["change-a"]
    head = coordinator.show("change-a").last_reviewed_commit
    runtime._contract = runtime.contract.model_copy(  # noqa: SLF001
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
    branch_publisher = Mock()
    branch_publisher.publish.return_value = _branch_receipt(head)
    pull_request_publisher = Mock()
    pull_request_publisher.publish.return_value = _draft_receipt(head)
    pull_request_publisher.update_generated_summary.return_value = _summary_receipt(head)
    application._change_branch_publisher = branch_publisher  # noqa: SLF001
    application._draft_pull_request_publisher = pull_request_publisher  # noqa: SLF001

    result = application.reconcile_change_checkpoint("change-a")

    assert result.reconciled
    request = pull_request_publisher.publish.call_args.args[0]
    assert len(request.title) == 256
    assert not request.title.startswith(" ")
    assert "\x00" not in request.title
    assert "owlbear-change:forged" not in request.generated_summary
    assert "Verified Outcome `OUT-001`" in request.generated_summary


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
    application._change_branch_publisher = branch_publisher  # noqa: SLF001
    application._draft_pull_request_publisher = pull_request_publisher  # noqa: SLF001

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
    branch_publisher.publish.return_value = _branch_receipt(head)
    pull_request_publisher = Mock()
    pull_request_publisher.update_generated_summary.return_value = _summary_receipt(head)

    def create_pull_request(_request):
        current = DeliveryFrontier.model_validate_json(frontier_path.read_bytes())
        frontier_path.write_bytes(
            _canonical(
                current.model_copy(
                    update={"pending_checkpoint": DeliveryPendingCheckpoint(head=newer_head, triggers=triggers)}
                )
            )
        )
        return _draft_receipt(head)

    pull_request_publisher.publish.side_effect = create_pull_request
    application._change_branch_publisher = branch_publisher  # noqa: SLF001
    application._draft_pull_request_publisher = pull_request_publisher  # noqa: SLF001

    result = application.reconcile_change_checkpoint("change-a")

    assert not result.reconciled
    assert result.state.published_head == head
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

    def publish_branch(_request):
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
        return _branch_receipt(head)

    branch_publisher.publish.side_effect = publish_branch
    pull_request_publisher = Mock()
    application._change_branch_publisher = branch_publisher  # noqa: SLF001
    application._draft_pull_request_publisher = pull_request_publisher  # noqa: SLF001

    result = application.reconcile_change_checkpoint("change-a")

    assert not result.reconciled
    assert result.state.published_head == head
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
    application._change_branch_publisher = branch_publisher  # noqa: SLF001
    application._draft_pull_request_publisher = pull_request_publisher  # noqa: SLF001

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

    def publish_branch(_request):
        branch_started.set()
        if not allow_branch.wait(timeout=5):
            message = "test branch publication remained blocked"
            raise TimeoutError(message)
        return _branch_receipt(head)

    def move_change():
        move_started.set()
        return application.administrative_move("change-a", move)

    branch_publisher.publish.side_effect = publish_branch
    pull_request_publisher = Mock()
    pull_request_publisher.publish.return_value = _draft_receipt(head)
    pull_request_publisher.update_generated_summary.return_value = _summary_receipt(head)
    application._change_branch_publisher = branch_publisher  # noqa: SLF001
    application._draft_pull_request_publisher = pull_request_publisher  # noqa: SLF001

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
    branch_publisher.publish.return_value = _branch_receipt(head)
    pull_request_publisher = Mock()
    pull_request_publisher.publish.return_value = _draft_receipt(head)
    pull_request_publisher.update_generated_summary.return_value = _summary_receipt(head)
    application._change_branch_publisher = branch_publisher  # noqa: SLF001
    application._draft_pull_request_publisher = pull_request_publisher  # noqa: SLF001
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

    assert runtime.checkpoint_publication_state().published_head == head
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
    branch_publisher.publish.side_effect = (
        _branch_receipt(first_head),
        _branch_receipt(second_head, first_head),
    )
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
    application._change_branch_publisher = branch_publisher  # noqa: SLF001
    application._draft_pull_request_publisher = DraftPullRequestPublisher(  # noqa: SLF001
        provider,
        repository="example/project",
        target_branch="main",
        state_root=tmp_path / "pull-requests",
    )

    with pytest.raises(PublicationProviderError) as exc_info:
        application.reconcile_change_checkpoint("change-a")

    assert exc_info.value.code is PublicationProviderFailureCode.UNAVAILABLE
    _set_checkpoint(
        runtimes["change-a"],
        state_root,
        pending.model_copy(update={"head": second_head}),
        published_head=first_head,
    )

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
    application._change_branch_publisher = branch_publisher  # noqa: SLF001
    application._draft_pull_request_publisher = pull_request_publisher  # noqa: SLF001

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
    assert (runtime_root / "capacity.json").is_file()
    assert not (repository / ".owlbear/target").exists()
    assert not (repository / ".owlbear/worktrees").exists()


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
    (state_root / "claims/changes/change-a.json").unlink()
    del application._runtimes["change-a"]  # noqa: SLF001
    request = DeliveryAdmissionRequest(change_id="change-a", active_claim_ids=())

    with pytest.raises(CoordinationConflictError, match="exact recovery reviewed head"):
        application.admit_delivery_change(request)
    assert frontier_path.read_bytes() == legacy_frontier

    recovered = application.admit_delivery_change(request.model_copy(update={"recovery_reviewed_head": reviewed_head}))

    assert recovered.replayed
    assert coordinator.show("change-a").last_reviewed_commit == reviewed_head
    assert application.show_change_checkpoint_publication("change-a").pending_checkpoint is not None
    assert json.loads(frontier_path.read_bytes())["schema_version"] == 8


def test_delivery_loader_migrates_result_history_with_exact_reviewed_head(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    runtime_root = repository / ".owlbear/delivery/runtime"
    coordinator = PortfolioCoordinator(runtime_root, capacity=1)
    manager = ChangeWorkspaceManager(
        repository,
        repository / ".owlbear/delivery/worktrees",
        coordinator,
        "main",
    )
    coordination = manager.create("change-a")
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

    application = load_delivery_application(_startup_config(), workspace_root=repository)
    state = application.show_change_checkpoint_publication("change-a")

    assert state.pending_checkpoint is not None
    assert state.pending_checkpoint.head == coordination.last_reviewed_commit
    assert json.loads((change_root / "frontier.json").read_bytes())["schema_version"] == 8


def test_delivery_loader_injects_publication_provider_and_derives_check_head(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    provider = Mock()
    application = load_delivery_application(
        _startup_config(),
        workspace_root=repository,
        publication_provider=provider,
    )
    assert isinstance(application._change_branch_publisher, ChangeBranchPublisher)  # noqa: SLF001
    assert isinstance(application._draft_pull_request_publisher, DraftPullRequestPublisher)  # noqa: SLF001
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
            application._draft_pull_request_publisher,  # noqa: SLF001
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
    assert isinstance(application._change_branch_publisher, ChangeBranchPublisher)  # noqa: SLF001
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
    assert not (state_root / "capacity.json").exists()

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
    assert not (runtime_root / "capacity.json").exists()


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
    assert tuple((item.change_id, item.work_item_id) for item in listed) == (("composed-delivery", "OUT-001"),)
    launch = application.acquire_frontier_work().launch_packages[0]
    assert launch.change_id == "composed-delivery"
    assert launch.outcome_id == "OUT-001"
    assert launch.claim.worker_role == DeliveryWorkerRole.PLANNER

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
    integration_context = application._workspace_manager.integration_context  # noqa: SLF001

    def record_resolution(change_id: str):  # noqa: ANN202
        resolved.append(change_id)
        return integration_context(change_id)

    monkeypatch.setattr(application._workspace_manager, "integration_context", record_resolution)  # noqa: SLF001

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
        retry_condition="Admit a reviewed Integration repair for this attention, then retry Integration.",
    )
    runtimes[change_id].publish_integration_attention(attention)
    return attention


def _prepare_reviewed_integration_repair(tmp_path: Path):
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    _target_before, reviewed = _review_product_change(coordinator, "change-a", "change side\n")
    repository = tmp_path / "repository"
    (repository / "product.txt").write_text("target side\n", encoding="utf-8")
    _git(repository, "add", "product.txt")
    _git(repository, "commit", "-m", "concurrent target")
    target_head = _git(repository, "rev-parse", "main")
    attention = _publish_merge_conflict_attention(runtimes, "change-a", reviewed, target_head)
    acquired = application.acquire_frontier_work()
    assert len(acquired.repair_launch_packages) == 1
    launch = acquired.repair_launch_packages[0]
    worktree = coordinator.show("change-a").worktree_path
    (worktree / "product.txt").write_text("target side\n", encoding="utf-8")
    candidate = application.create_integration_repair_candidate(
        "change-a",
        launch.claim.attempt_id,
        launch.claim.claim_id,
    )
    repair_commit = candidate.candidate_commit
    repair = DeliveryIntegrationRepair(
        attention_id=attention.attention_id,
        change_id="change-a",
        integration_target="main",
        prior_change_head=reviewed,
        prior_target_head=target_head,
        reviewed_repair_commit=repair_commit,
        owner_id=launch.claim.owner_id,
        review=DeliveryIntegrationRepairReview(
            review_id="repair-review-001",
            reviewer_id="independent-reviewer",
            candidate_commit=repair_commit,
        ),
    )
    return application, runtimes, coordinator, state_root, repair, launch.claim


def test_repair_recovery_preserves_worktree_for_next_claim(tmp_path: Path) -> None:
    application, _runtimes, coordinator, _state_root, repair, first_claim = _prepare_reviewed_integration_repair(
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
        assert len(acquired.repair_launch_packages) == 1
        second_launch = acquired.repair_launch_packages[0]
        context = application.show_integration_repair_context(
            "change-a",
            second_launch.claim.attempt_id,
            second_launch.claim.claim_id,
        )

        assert recovered.preserved_commit == repair.reviewed_repair_commit
        assert os.path.samestat(worktree.stat(), original_directory)
        assert context.launch == second_launch
    finally:
        os.close(directory_fd)


def test_repair_candidate_rejects_mismatched_claim(tmp_path: Path) -> None:
    application, _runtimes, coordinator, _state_root, repair, claim = _prepare_reviewed_integration_repair(tmp_path)

    with pytest.raises(DeliveryRuntimeConflictError, match="execution identity"):
        application.create_integration_repair_candidate(
            "change-a",
            claim.attempt_id,
            "another-claim",
        )

    assert _git(coordinator.show("change-a").worktree_path, "rev-parse", "HEAD") == repair.reviewed_repair_commit


def test_repair_candidate_rejects_mismatched_writer_custody(tmp_path: Path) -> None:
    application, _runtimes, coordinator, _state_root, repair, claim = _prepare_reviewed_integration_repair(tmp_path)
    coordination = coordinator.show("change-a")
    assert coordination.writer is not None
    coordinator.release("change-a", claim.claim_id)
    coordinator.acquire(
        "change-a",
        coordination.writer.model_copy(update={"actor_id": "another-builder"}),
    )

    with pytest.raises(PortfolioApplicationError, match="exact active writer custody"):
        application.create_integration_repair_candidate(
            "change-a",
            claim.attempt_id,
            claim.claim_id,
        )

    assert _git(coordination.worktree_path, "rev-parse", "HEAD") == repair.reviewed_repair_commit


def _with_reviewed_commit(repair: DeliveryIntegrationRepair, commit: str) -> DeliveryIntegrationRepair:
    return repair.model_copy(
        update={
            "reviewed_repair_commit": commit,
            "review": repair.review.model_copy(update={"candidate_commit": commit}),
        }
    )


def _file_bytes(root: Path) -> dict[str, bytes]:
    return {str(path.relative_to(root)): path.read_bytes() for path in root.rglob("*") if path.is_file()}


def _invalid_integration_repair(
    invalid_case: str,
    repair: DeliveryIntegrationRepair,
    worktree: Path,
) -> DeliveryIntegrationRepair:
    identity_updates = {
        "stale-attention": {"attention_id": "0" * 64},
        "change-identity": {"change_id": "change-b"},
        "target-identity": {"integration_target": "other-target"},
        "stale-change-head": {"prior_change_head": "0" * 40},
        "stale-target-head": {"prior_target_head": "0" * 40},
    }
    if invalid_case in identity_updates:
        return repair.model_copy(update=identity_updates[invalid_case])
    if invalid_case == "multi-commit":
        (worktree / "second.txt").write_text("second\n", encoding="utf-8")
        _git(worktree, "add", "second.txt")
        _git(worktree, "commit", "-m", "second repair commit")
        return _with_reviewed_commit(repair, _git(worktree, "rev-parse", "HEAD"))
    if invalid_case == "non-child":
        _git(worktree, "reset", "--hard", repair.prior_target_head)
        (worktree / "non-child.txt").write_text("non-child\n", encoding="utf-8")
        _git(worktree, "add", "non-child.txt")
        _git(worktree, "commit", "-m", "unrelated repair ancestry")
        return _with_reviewed_commit(repair, _git(worktree, "rev-parse", "HEAD"))
    if invalid_case == "dirty-worktree":
        (worktree / "dirty.txt").write_text("dirty\n", encoding="utf-8")
    elif invalid_case == "detached-worktree":
        _git(worktree, "checkout", "--detach", repair.reviewed_repair_commit)
    elif invalid_case == "branch-head-mismatch":
        (worktree / "later.txt").write_text("later\n", encoding="utf-8")
        _git(worktree, "add", "later.txt")
        _git(worktree, "commit", "-m", "move branch after review")
    elif invalid_case in {"completed-history", "non-conflict-path"}:
        _git(worktree, "reset", "--hard", repair.prior_change_head)
        (worktree / "product.txt").write_text("target side\n", encoding="utf-8")
        extra = (
            worktree / ".owlbear/completed/change-z/results.json"
            if invalid_case == "completed-history"
            else worktree / "unrelated.txt"
        )
        extra.parent.mkdir(parents=True, exist_ok=True)
        extra.write_text("changed\n", encoding="utf-8")
        _git(worktree, "add", "product.txt", str(extra))
        _git(worktree, "commit", "-m", f"invalid {invalid_case} repair")
        return _with_reviewed_commit(repair, _git(worktree, "rev-parse", "HEAD"))
    return repair


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
    ledger = CapacityLedger.model_validate_json((state_root / "capacity.json").read_bytes())
    assert ledger.change_ids == ("change-b",)

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
    ledger = CapacityLedger.model_validate_json((state_root / "capacity.json").read_bytes())
    assert ledger.change_ids == ()


def test_writer_capacity_skips_blocked_build_but_launches_read_only_work(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {
            "change-a": DeliveryStage.IMPLEMENTATION,
            "change-b": DeliveryStage.IMPLEMENTATION,
            "change-c": DeliveryStage.PLANNING,
        },
        writer_capacity=1,
    )

    acquired = application.acquire_frontier_work()

    assert tuple(package.change_id for package in acquired.launch_packages) == ("change-a", "change-c")
    assert acquired.failures == ()
    assert runtimes["change-b"].active_claims() == ()
    assert coordinator.show("change-b").writer is None
    ledger = CapacityLedger.model_validate_json((state_root / "capacity.json").read_bytes())
    assert ledger.change_ids == ("change-a",)


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
    ledger = CapacityLedger.model_validate_json((state_root / "capacity.json").read_bytes())
    assert ledger.change_ids == ()


def test_acquisition_recovers_interrupted_planning_claim_before_relaunch(tmp_path: Path) -> None:
    application, runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.PLANNING},
    )
    interrupted = application.acquire_frontier_work().launch_packages[0]

    resumed = application.acquire_frontier_work()

    assert resumed.recoveries == (
        DeliveryClaimRecoveryResult(
            status=DeliveryClaimRecoveryStatus.RECOVERED,
            change_id=interrupted.change_id,
            outcome_id=interrupted.outcome_id,
            attempt_id=interrupted.claim.attempt_id,
            claim_id=interrupted.claim.claim_id,
        ),
    )
    assert len(resumed.launch_packages) == 1
    replacement = resumed.launch_packages[0]
    assert replacement.claim.claim_id != interrupted.claim.claim_id
    assert runtimes["change-a"].active_claims() == (("OUT-001", replacement.claim),)


def test_expired_claim_recovery_respects_lease_and_releases_writer(tmp_path: Path) -> None:
    current_time = ["2026-08-04T00:00:00Z"]
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
        clock=lambda: current_time[0],
    )
    interrupted = application.acquire_frontier_work().launch_packages[0]

    current_time[0] = "2026-08-04T00:29:59Z"
    assert application.recover_expired_claims().recoveries == ()
    assert runtimes["change-a"].active_claims() == (("OUT-001", interrupted.claim),)

    current_time[0] = "2026-08-04T00:30:00Z"
    recovered = application.recover_expired_claims()

    assert recovered.recoveries == (
        DeliveryClaimRecoveryResult(
            status=DeliveryClaimRecoveryStatus.RECOVERED,
            change_id=interrupted.change_id,
            outcome_id=interrupted.outcome_id,
            attempt_id=interrupted.claim.attempt_id,
            claim_id=interrupted.claim.claim_id,
            preserved_commit=interrupted.last_reviewed_commit,
            preserved_ref=f"refs/owlbear/attempts/change-a/{interrupted.claim.attempt_id}",
        ),
    )
    assert runtimes["change-a"].active_claims() == ()
    assert coordinator.show("change-a").writer is None
    ledger = CapacityLedger.model_validate_json((state_root / "capacity.json").read_bytes())
    assert ledger.change_ids == ()


def test_acquisition_retains_dirty_interrupted_build_as_attention(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    interrupted = application.acquire_frontier_work().launch_packages[0]
    (interrupted.worktree_path / "product.txt").write_text("uncommitted attempt\n", encoding="utf-8")

    resumed = application.acquire_frontier_work()

    assert resumed.launch_packages == ()
    assert len(resumed.recoveries) == 1
    recovery = resumed.recoveries[0]
    assert recovery.status == DeliveryClaimRecoveryStatus.ATTENTION
    assert recovery.claim_id == interrupted.claim.claim_id
    assert recovery.attention is not None
    assert recovery.attention.custody_retained
    assert runtimes["change-a"].active_claims() == (("OUT-001", interrupted.claim),)
    assert coordinator.show("change-a").writer == interrupted.writer
    ledger = CapacityLedger.model_validate_json((state_root / "capacity.json").read_bytes())
    assert ledger.change_ids == ("change-a",)


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
    ledger = CapacityLedger.model_validate_json((state_root / "capacity.json").read_bytes())
    assert ledger.change_ids == ()
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
    ledger = CapacityLedger.model_validate_json((state_root / "capacity.json").read_bytes())
    assert ledger.change_ids == ()


def test_dirty_build_recovery_retains_bytes_claim_custody_and_attention(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.IMPLEMENTATION},
    )
    package = application.acquire_frontier_work().launch_packages[0]
    product = package.worktree_path / "product.txt"
    product.write_text("uncommitted attempt\n", encoding="utf-8")
    branch_head = _git(package.worktree_path, "rev-parse", "HEAD")

    retained = application.recover_claim(
        package.change_id,
        package.outcome_id,
        package.claim.attempt_id,
        package.claim.claim_id,
    )

    assert retained.status == DeliveryClaimRecoveryStatus.ATTENTION
    assert retained.attention is not None
    assert retained.attention.custody_retained
    assert retained.attention.branch_head == branch_head
    assert product.read_text(encoding="utf-8") == "uncommitted attempt\n"
    assert runtimes["change-a"].active_claims()[0][1] == package.claim
    assert runtimes["change-a"].show_binding("OUT-001").recovery_attention == retained.attention
    assert coordinator.show("change-a").writer == package.writer
    ledger = CapacityLedger.model_validate_json((state_root / "capacity.json").read_bytes())
    assert ledger.change_ids == ("change-a",)


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
    ledger = CapacityLedger.model_validate_json((state_root / "capacity.json").read_bytes())
    assert ledger.change_ids == ("change-a",)


def test_reviewed_integration_repair_advances_boundary_without_local_completion(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root, repair, claim = _prepare_reviewed_integration_repair(tmp_path)
    repository = tmp_path / "repository"
    target_head = repair.prior_target_head
    repair_commit = repair.reviewed_repair_commit
    package_bytes = {path.name: path.read_bytes() for path in (tmp_path / "packages/change-a").iterdir()}
    completed_binding = runtimes["change-a"].show_binding("OUT-001")

    admitted = application.admit_reviewed_integration_repair(claim.attempt_id, claim.claim_id, repair)

    assert admitted == repair
    assert coordinator.show("change-a").last_reviewed_commit == repair_commit
    assert runtimes["change-a"].integration_attention() is None
    assert runtimes["change-a"].change_stage().value == "integration"
    assert runtimes["change-a"].show_binding("OUT-001") == completed_binding
    assert _git(repository, "rev-parse", "main") == target_head
    assert {path.name: path.read_bytes() for path in (tmp_path / "packages/change-a").iterdir()} == package_bytes


def test_repair_authority_attention_releases_claim_and_is_not_reacquired(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    _target_before, reviewed = _review_product_change(coordinator, "change-a", "change side\n")
    repository = tmp_path / "repository"
    (repository / "product.txt").write_text("target side\n", encoding="utf-8")
    _git(repository, "add", "product.txt")
    _git(repository, "commit", "-m", "concurrent target")
    target_head = _git(repository, "rev-parse", "main")
    merge_attention = _publish_merge_conflict_attention(runtimes, "change-a", reviewed, target_head)
    acquired = application.acquire_frontier_work()
    launch = acquired.repair_launch_packages[0]

    attention = application.publish_integration_repair_authority_attention(
        launch.claim.attempt_id,
        launch.claim.claim_id,
        DeliveryIntegrationRepairAuthorityAttention(
            attention_id=merge_attention.attention_id,
            change_id="change-a",
            reason="The admitted authorities require incompatible public behavior.",
            locators=("product.txt",),
        ),
    )

    assert attention.code == DeliveryIntegrationAttentionCode.REPAIR_AUTHORITY
    assert attention.change_head == reviewed
    assert runtimes["change-a"].integration_repair_claim() is None
    assert coordinator.show("change-a").writer is None
    assert CapacityLedger.model_validate_json((state_root / "capacity.json").read_bytes()).change_ids == ()
    refreshed = application.acquire_frontier_work()
    assert refreshed.repair_launch_packages == ()
    assert refreshed.integration_attention[0].code == DeliveryIntegrationAttentionCode.REPAIR_AUTHORITY


def test_repair_authority_attention_preserves_claim_when_worktree_is_dirty(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    _target_before, reviewed = _review_product_change(coordinator, "change-a", "change side\n")
    repository = tmp_path / "repository"
    (repository / "product.txt").write_text("target side\n", encoding="utf-8")
    _git(repository, "add", "product.txt")
    _git(repository, "commit", "-m", "concurrent target")
    target_head = _git(repository, "rev-parse", "main")
    _publish_merge_conflict_attention(runtimes, "change-a", reviewed, target_head)
    launch = application.acquire_frontier_work().repair_launch_packages[0]
    (launch.worktree_path / "owned-edit.txt").write_text("uncommitted\n", encoding="utf-8")
    request = DeliveryIntegrationRepairAuthorityAttention(
        attention_id=launch.attention.attention_id,
        change_id="change-a",
        reason="The admitted authorities conflict.",
        locators=("product.txt",),
    )

    with pytest.raises(RuntimeError, match="worktree is not clean"):
        application.publish_integration_repair_authority_attention(
            launch.claim.attempt_id,
            launch.claim.claim_id,
            request,
        )

    assert runtimes["change-a"].integration_repair_claim() == launch.claim
    assert coordinator.show("change-a").writer == launch.writer
    assert runtimes["change-a"].integration_attention() == launch.attention


@pytest.mark.parametrize(
    "invalid_case",
    [
        "stale-attention",
        "change-identity",
        "target-identity",
        "stale-change-head",
        "stale-target-head",
        "multi-commit",
        "non-child",
        "dirty-worktree",
        "detached-worktree",
        "branch-head-mismatch",
        "completed-history",
        "non-conflict-path",
    ],
)
def test_reviewed_integration_repair_rejection_preserves_all_state(
    tmp_path: Path,
    invalid_case: str,
) -> None:
    application, runtimes, coordinator, state_root, repair, claim = _prepare_reviewed_integration_repair(tmp_path)
    coordination = coordinator.show("change-a")
    worktree = coordination.worktree_path
    repository = tmp_path / "repository"
    repair = _invalid_integration_repair(invalid_case, repair, worktree)

    coordination_path = state_root / "claims/changes/change-a.json"
    frontier_path = state_root / "changes/change-a/frontier.json"
    package_root = tmp_path / "packages/change-a"
    persisted_before = (coordination_path.read_bytes(), frontier_path.read_bytes())
    refs_before = (
        _git(repository, "rev-parse", "main"),
        _git(repository, "rev-parse", coordination.branch),
        _git(worktree, "rev-parse", "HEAD"),
        _git(worktree, "status", "--porcelain"),
    )
    package_before = _file_bytes(package_root)
    binding_before = runtimes["change-a"].show_binding("OUT-001")
    attention_before = runtimes["change-a"].integration_attention()

    with pytest.raises(RuntimeError):
        application.admit_reviewed_integration_repair(claim.attempt_id, claim.claim_id, repair)

    assert (coordination_path.read_bytes(), frontier_path.read_bytes()) == persisted_before
    assert (
        _git(repository, "rev-parse", "main"),
        _git(repository, "rev-parse", coordination.branch),
        _git(worktree, "rev-parse", "HEAD"),
        _git(worktree, "status", "--porcelain"),
    ) == refs_before
    assert _file_bytes(package_root) == package_before
    assert runtimes["change-a"].show_binding("OUT-001") == binding_before
    assert runtimes["change-a"].integration_attention() == attention_before


@pytest.mark.parametrize("invalid_review", ["missing", "commit-mismatch", "not-independent"])
def test_integration_repair_requires_exact_independent_review_binding(invalid_review: str) -> None:
    payload = {
        "attention_id": "a" * 64,
        "change_id": "change-a",
        "integration_target": "main",
        "prior_change_head": "b" * 40,
        "prior_target_head": "c" * 40,
        "reviewed_repair_commit": "d" * 40,
        "owner_id": "repair-builder",
        "review": {
            "review_id": "review-001",
            "reviewer_id": "independent-reviewer",
            "candidate_commit": "d" * 40,
        },
    }
    if invalid_review == "missing":
        payload.pop("review")
    elif invalid_review == "commit-mismatch":
        payload["review"]["candidate_commit"] = "e" * 40
    else:
        payload["review"]["reviewer_id"] = payload["owner_id"]

    with pytest.raises(ValueError):
        DeliveryIntegrationRepair.model_validate(payload)


def test_interrupted_integration_repair_admission_converges_without_local_retry(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root, repair, claim = _prepare_reviewed_integration_repair(tmp_path)
    repository = tmp_path / "repository"
    package_root = tmp_path / "packages/change-a"
    package_before = _file_bytes(package_root)
    original_commit = RuntimeTransaction.commit

    def interrupt(stage: str) -> None:
        if stage == "after-first-publication":
            message = "interrupted repair admission"
            raise RuntimeError(message)

    def commit_with_interruption(transaction: RuntimeTransaction) -> None:
        original_commit(transaction, failure=interrupt)

    with (
        patch.object(RuntimeTransaction, "commit", commit_with_interruption),
        pytest.raises(
            RuntimeError,
            match="interrupted repair admission",
        ),
    ):
        application.admit_reviewed_integration_repair(claim.attempt_id, claim.claim_id, repair)

    assert coordinator.show("change-a").last_reviewed_commit == repair.reviewed_repair_commit
    assert runtimes["change-a"].integration_attention() is None
    assert runtimes["change-a"].integration_repair_claim() is None
    assert coordinator.show("change-a").writer is None
    assert _git(repository, "rev-parse", "main") == repair.prior_target_head
    assert _file_bytes(package_root) == package_before
