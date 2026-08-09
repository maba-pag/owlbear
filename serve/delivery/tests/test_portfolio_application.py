from __future__ import annotations

import hashlib
import itertools
import json
import os
import subprocess
from collections.abc import Callable
from pathlib import Path
from unittest.mock import patch

import pytest

from owlbear_delivery import (
    AdministrativeDeliveryMove,
    AtomicIntegrationPreparation,
    CapacityLedger,
    AdvanceDelivery,
    BlockDelivery,
    CompletedHistoryCatalog,
    ChangeWorkspaceManager,
    ChangeWriter,
    CoordinationConflictError,
    DeliveryApplicationLoadError,
    DeliveryCommitment,
    DeliveryCommitmentClass,
    DeliveryAdmissionConflictError,
    DeliveryAdmissionRequest,
    DeliveryAuthorityRegistry,
    DeliveryClaimRecoveryResult,
    DeliveryClaimRecoveryStatus,
    DeliveryContract,
    DeliveryFrontier,
    DeliveryIntegrationAttentionCode,
    DeliveryIntegrationCandidate,
    DeliveryIntegrationRepair,
    DeliveryIntegrationRepairAuthorityAttention,
    DeliveryIntegrationRepairReview,
    DeliveryOutcome,
    DeliveryPlanScope,
    DeliveryRequest,
    DeliveryRequestKind,
    DeliveryRequestOption,
    DeliveryRequestResolution,
    DeliveryRolePolicy,
    DeliveryRuntime,
    DeliveryRuntimeConflictError,
    DeliveryStage,
    DeliveryStartupConfig,
    DeliveryTaskDefinition,
    DeliveryTaskResult,
    DeliveryWorkerRole,
    DesignPackageManifest,
    DesignPackageConflictError,
    DesignPackageStore,
    OutcomeAuthorityBinding,
    PortfolioApplication,
    PortfolioApplicationConfig,
    PortfolioApplicationDependencies,
    PortfolioApplicationError,
    PortfolioApplicationHooks,
    PortfolioCoordinator,
    PublishDeliveryPlan,
    PublishDeliveryResult,
    RetryDelivery,
    load_delivery_application,
)
from owlbear_delivery.integration_verification import (
    IntegrationVerificationReceipt,
    IntegrationVerificationStatus,
    IntegrationVerifier,
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


def _runtime(
    state_root: Path,
    contract: DeliveryContract,
    manager: ChangeWorkspaceManager,
    stage: DeliveryStage,
    completed_commit: str,
) -> DeliveryRuntime:
    task = _task()
    authority_digest = hashlib.sha256(_canonical(contract)).hexdigest()
    has_task = stage in {DeliveryStage.IMPLEMENTATION, DeliveryStage.ASSEMBLY, DeliveryStage.COMPLETED}
    has_result = stage in {DeliveryStage.ASSEMBLY, DeliveryStage.COMPLETED}
    result = DeliveryTaskResult(
        result_id="RESULT-001",
        change_id=contract.change_id,
        authority_digest=authority_digest,
        task_id=task.task_id,
        task_digest=task.digest,
        completed_commit=completed_commit,
    )
    frontier = DeliveryFrontier(
        bindings=(
            OutcomeAuthorityBinding(
                outcome_id="OUT-001",
                plan_scope_id="SCOPE-001",
                stage=stage,
                assembly_required=stage == DeliveryStage.ASSEMBLY,
                tasks=(task,) if has_task else (),
                results=(result,) if has_result else (),
            ),
        )
    )
    path = state_root / "delivery" / "changes" / contract.change_id / "frontier.json"
    path.parent.mkdir(parents=True)
    path.write_bytes(_canonical(frontier))
    return DeliveryRuntime(state_root, contract, workspace_manager=manager)


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
            worker_role=DeliveryWorkerRole.ASSEMBLY_REVIEWER,
            worker_agent="build-reviewer",
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
        schema_version=1,
        integration_target="main",
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
    return repository


def _portfolio(  # noqa: PLR0913
    tmp_path: Path,
    stages: dict[str, DeliveryStage],
    *,
    writer_capacity: int = 1,
    execution_capacity: int = 3,
    candidate_proof: Callable[[DeliveryIntegrationCandidate, str], tuple[str, ...]] | None = None,
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

    class CallbackVerifier:
        def verify(
            self,
            candidate: DeliveryIntegrationCandidate,
            preparation: AtomicIntegrationPreparation,
        ) -> IntegrationVerificationReceipt:
            assert preparation.candidate_commit is not None
            diagnostics = (
                candidate_proof(candidate, preparation.candidate_commit)
                if candidate_proof is not None
                else ("candidate proof dependency is not configured",)
            )
            return IntegrationVerificationReceipt(
                request_id=candidate.candidate_id,
                candidate_commit=preparation.candidate_commit,
                profile_digest="0" * 64,
                status=(IntegrationVerificationStatus.FAILED if diagnostics else IntegrationVerificationStatus.PASSED),
                diagnostics=diagnostics,
            )

    application = PortfolioApplication(
        dict(reversed(tuple(runtimes.items()))),
        PortfolioApplicationDependencies(
            target_root=state_root,
            package_store=store,
            authority_registry=authority_registry,
            coordinator=coordinator,
            workspace_manager=manager,
            integration_verifier=CallbackVerifier(),
            completed_history_catalog=CompletedHistoryCatalog(repository, "main"),
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


def test_delivery_loader_composes_validated_owners_from_authorized_root(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    target_root = repository / ".owlbear/target"
    application = load_delivery_application(
        _startup_config(),
        workspace_root=repository,
        authorized_target_root=target_root,
    )
    assert application.list_work_items() == ()
    assert isinstance(application._integration_verifier, IntegrationVerifier)  # noqa: SLF001
    assert (target_root / "target-runtime/capacity.json").is_file()


def test_delivery_loader_rejects_unauthorized_root_before_owner_mutation(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    target_root = repository / ".owlbear/target"
    with pytest.raises(DeliveryApplicationLoadError) as exc_info:
        load_delivery_application(
            _startup_config(),
            workspace_root=repository,
            authorized_target_root=tmp_path / "other-target",
        )
    assert exc_info.value.field == "target_root"
    assert not target_root.exists()


def test_delivery_loader_rejects_git_and_state_identity_before_composition(tmp_path: Path) -> None:
    non_repository = tmp_path / "not-a-repository"
    non_repository.mkdir()
    target_root = non_repository / ".owlbear/target"
    with pytest.raises(DeliveryApplicationLoadError) as git_error:
        load_delivery_application(
            _startup_config(),
            workspace_root=non_repository,
            authorized_target_root=target_root,
        )
    assert git_error.value.field == "repository_root"
    assert not target_root.exists()

    repository = _repository(tmp_path / "valid")
    state_root = repository / ".owlbear/target"
    change_root = state_root / "delivery/changes/change-a"
    change_root.mkdir(parents=True)
    contract = _contract("change-b", b"intent\n", b"design\n")
    (change_root / "contract.json").write_bytes(_canonical(contract))
    with pytest.raises(DeliveryApplicationLoadError) as state_error:
        load_delivery_application(
            _startup_config(),
            workspace_root=repository,
            authorized_target_root=state_root,
        )
    assert state_error.value.field == "target_root"
    assert not (state_root / "target-runtime").exists()

    runtime_repository = _repository(tmp_path / "invalid-runtime")
    runtime_root = runtime_repository / ".owlbear/target"
    runtime_change = runtime_root / "delivery/changes/change-a"
    runtime_change.mkdir(parents=True)
    valid_contract = _contract("change-a", b"intent\n", b"design\n")
    (runtime_change / "contract.json").write_bytes(_canonical(valid_contract))
    (runtime_change / "frontier.json").write_bytes(b"not-json\n")
    with pytest.raises(DeliveryApplicationLoadError) as runtime_error:
        load_delivery_application(
            _startup_config(),
            workspace_root=runtime_repository,
            authorized_target_root=runtime_root,
        )
    assert runtime_error.value.field == "target_root"
    assert not (runtime_root / "target-runtime").exists()


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
    assert not (state_root / "delivery/changes/composed-delivery").exists()

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

    delivery_root = state_root / "delivery/changes/composed-delivery"
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
        result=DeliveryTaskResult(
            result_id="RESULT-PUBLIC",
            change_id="change-b",
            authority_digest=runtimes["change-b"].authority_digest,
            task_id=build_task.task_id,
            task_digest=build_task.digest,
            completed_commit=completed_commit,
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


def test_integration_queries_are_stable_bounded_and_read_only(tmp_path: Path) -> None:
    application, runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {
            "change-b": DeliveryStage.COMPLETED,
            "change-a": DeliveryStage.COMPLETED,
            "change-c": DeliveryStage.PLANNING,
        },
    )
    before = {change_id: runtime.frontier_bytes() for change_id, runtime in runtimes.items()}

    assert application.list_integration_ready_changes() == ("change-a", "change-b")
    assert application.show_integration_attention("change-a") is None
    assert {change_id: runtime.frontier_bytes() for change_id, runtime in runtimes.items()} == before
    assert all(runtime.active_claims() == () for runtime in runtimes.values())

    failed = application.integrate_ready_change("change-a")
    assert failed.attention is not None
    attention_bytes = runtimes["change-a"].frontier_bytes()
    assert application.show_integration_attention("change-a") == failed.attention
    assert runtimes["change-a"].frontier_bytes() == attention_bytes


def test_work_item_queries_resolve_live_target_once_per_portfolio_capture(
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
    assert resolved == ["change-b", "change-b"]
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


def _prepare_reviewed_integration_repair(tmp_path: Path):
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
        candidate_proof=lambda _candidate, _commit: (),
    )
    _target_before, reviewed = _review_product_change(coordinator, "change-a", "change side\n")
    repository = tmp_path / "repository"
    (repository / "product.txt").write_text("target side\n", encoding="utf-8")
    _git(repository, "add", "product.txt")
    _git(repository, "commit", "-m", "concurrent target")
    target_head = _git(repository, "rev-parse", "main")
    failed = application.integrate_ready_change("change-a")
    assert failed.attention is not None
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
        attention_id=failed.attention.attention_id,
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


def test_acquisition_returns_bounded_stage_packages_and_unclaimed_integration(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {
            "change-d": DeliveryStage.COMPLETED,
            "change-c": DeliveryStage.ASSEMBLY,
            "change-b": DeliveryStage.IMPLEMENTATION,
            "change-a": DeliveryStage.PLANNING,
        },
    )

    acquired = application.acquire_frontier_work()

    assert tuple(package.change_id for package in acquired.launch_packages) == (
        "change-a",
        "change-b",
        "change-c",
    )
    assert tuple(package.claim.worker_role for package in acquired.launch_packages) == (
        DeliveryWorkerRole.PLANNER,
        DeliveryWorkerRole.BUILDER,
        DeliveryWorkerRole.ASSEMBLY_REVIEWER,
    )
    assert acquired.integration_ready_change_ids == ("change-d",)
    assert acquired.failures == ()
    assert runtimes["change-d"].active_claims() == ()
    assert coordinator.show("change-a").writer is None
    assert coordinator.show("change-b").writer is not None
    assert coordinator.show("change-c").writer is None
    ledger = CapacityLedger.model_validate_json((state_root / "target-runtime/capacity.json").read_bytes())
    assert ledger.change_ids == ("change-b",)

    plan_package, build_package, assembly_package = acquired.launch_packages
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
    assert assembly_package.writer is None
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
    ledger = CapacityLedger.model_validate_json((state_root / "target-runtime/capacity.json").read_bytes())
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
    ledger = CapacityLedger.model_validate_json((state_root / "target-runtime/capacity.json").read_bytes())
    assert ledger.change_ids == ("change-a",)


@pytest.mark.parametrize("stage", [DeliveryStage.PLANNING, DeliveryStage.ASSEMBLY])
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
    ledger = CapacityLedger.model_validate_json((state_root / "target-runtime/capacity.json").read_bytes())
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
    ledger = CapacityLedger.model_validate_json((state_root / "target-runtime/capacity.json").read_bytes())
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
    ledger = CapacityLedger.model_validate_json((state_root / "target-runtime/capacity.json").read_bytes())
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
    ledger = CapacityLedger.model_validate_json((state_root / "target-runtime/capacity.json").read_bytes())
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
    ledger = CapacityLedger.model_validate_json((state_root / "target-runtime/capacity.json").read_bytes())
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
    ledger = CapacityLedger.model_validate_json((state_root / "target-runtime/capacity.json").read_bytes())
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
    ledger = CapacityLedger.model_validate_json((state_root / "target-runtime/capacity.json").read_bytes())
    assert ledger.change_ids == ("change-a",)


def test_integration_publishes_product_and_package_once_then_replays_cleanup(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
        candidate_proof=lambda _candidate, _commit: (),
    )
    target_before, reviewed = _review_product_change(coordinator, "change-a", "reviewed product\n")
    active_root = tmp_path / "packages/change-a"
    active_bytes = {path.name: path.read_bytes() for path in active_root.iterdir()}
    worktree_path = coordinator.show("change-a").worktree_path

    published = application.integrate_ready_change("change-a")

    assert published.completion is not None
    target_commit = published.completion.target_commit
    assert _git(tmp_path / "repository", "rev-parse", "main") == target_commit
    assert _git(tmp_path / "repository", "show", f"{target_commit}:product.txt") == "reviewed product"
    assert _git(tmp_path / "repository", "rev-list", "--parents", "-n", "1", target_commit).split() == [
        target_commit,
        target_before,
        reviewed,
    ]
    completion_root = ".owlbear/completed/change-a"
    completed_names = _git(
        tmp_path / "repository",
        "ls-tree",
        "--name-only",
        f"{target_commit}:{completion_root}",
    ).split()
    assert set(completed_names) == {
        "authority.json",
        "completion.json",
        "design.md",
        "intent.md",
        "manifest.json",
        "results.json",
        "runtime.json",
    }
    assert runtimes["change-a"].change_stage().value == "completed"
    assert not _git_ref_exists(tmp_path / "repository", "refs/owlbear/integration-candidates/change-a")
    assert not (tmp_path / "packages/change-a").exists()
    assert not coordinator.show("change-a").worktree_path.exists()

    active_root.mkdir()
    for name, content in active_bytes.items():
        (active_root / name).write_bytes(content)
    _git(tmp_path / "repository", "worktree", "add", str(worktree_path), coordinator.show("change-a").branch)

    replayed = application.integrate_ready_change("change-a")

    assert replayed.replayed
    assert replayed.completion == published.completion
    assert _git(tmp_path / "repository", "rev-parse", "main") == target_commit
    assert not active_root.exists()
    assert not worktree_path.exists()


def test_integration_replay_cleans_candidate_ref_after_runtime_publication_crash(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
        candidate_proof=lambda _candidate, _commit: (),
    )
    _review_product_change(coordinator, "change-a", "reviewed product\n")
    repository = tmp_path / "repository"
    reference = "refs/owlbear/integration-candidates/change-a"

    with (
        patch.object(
            runtimes["change-a"],
            "publish_integration_completion",
            side_effect=DeliveryRuntimeConflictError("injected runtime publication crash"),
        ),
        pytest.raises(DeliveryRuntimeConflictError, match="injected runtime publication crash"),
    ):
        application.integrate_ready_change("change-a")

    assert _git_ref_exists(repository, reference)

    replayed = application.integrate_ready_change("change-a")

    assert replayed.replayed
    assert replayed.completion is not None
    assert not _git_ref_exists(repository, reference)


def test_integration_proof_failure_retains_heads_and_publishes_attention(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    target_before, reviewed = _review_product_change(coordinator, "change-a", "reviewed product\n")

    failed = application.integrate_ready_change("change-a")

    assert failed.attention is not None
    assert failed.attention.code == DeliveryIntegrationAttentionCode.CANDIDATE_PROOF_FAILED
    assert failed.attention.retry_condition == (
        "Correct the Integration profile or failing candidate verification step, "
        "then re-run Integration through Delivery orchestration."
    )
    assert failed.attention.change_head == reviewed
    assert failed.attention.target_head == target_before
    assert _git(tmp_path / "repository", "rev-parse", "main") == target_before
    assert _git(tmp_path / "repository", "rev-parse", coordinator.show("change-a").branch) == reviewed
    assert runtimes["change-a"].change_stage().value == "integration"
    assert not _git_ref_exists(tmp_path / "repository", "refs/owlbear/integration-candidates/change-a")
    assert (tmp_path / "packages/change-a").is_dir()
    assert not _git(coordinator.show("change-a").worktree_path, "status", "--porcelain")


def test_integration_target_identity_mismatch_is_typed_attention(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
        candidate_proof=lambda _candidate, _commit: (),
    )
    repository = tmp_path / "repository"
    target_head = _git(repository, "rev-parse", "main")
    _git(repository, "branch", "other-target", target_head)
    coordination = coordinator.show("change-a")
    coordinator.update(coordination.model_copy(update={"integration_target": "other-target"}))

    failed = application.integrate_ready_change("change-a")

    assert failed.attention is not None
    assert failed.attention.code == DeliveryIntegrationAttentionCode.TARGET_IDENTITY_MISMATCH
    assert _git(repository, "rev-parse", "main") == target_head
    assert _git(repository, "rev-parse", "other-target") == target_head
    assert runtimes["change-a"].change_stage().value == "integration"


def test_semantic_only_integration_preserves_product_and_sibling_completed_tree(tmp_path: Path) -> None:
    application, _runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED, "change-b": DeliveryStage.COMPLETED},
        candidate_proof=lambda _candidate, _commit: (),
    )
    repository = tmp_path / "repository"
    first = application.integrate_ready_change("change-a")
    assert first.completion is not None
    first_commit = first.completion.target_commit
    product_blob = _git(repository, "rev-parse", f"{first_commit}:product.txt")
    sibling_tree = _git(repository, "rev-parse", f"{first_commit}:.owlbear/completed/change-a")

    second = application.integrate_ready_change("change-b")

    assert second.completion is not None
    second_commit = second.completion.target_commit
    assert _git(repository, "rev-parse", f"{second_commit}:product.txt") == product_blob
    assert _git(repository, "rev-parse", f"{second_commit}:.owlbear/completed/change-a") == sibling_tree
    assert _git(repository, "rev-parse", f"{second_commit}:.owlbear/completed/change-b")


def test_completed_history_queries_are_bounded_and_separate_from_active_projections(tmp_path: Path) -> None:
    application, _runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED, "change-b": DeliveryStage.COMPLETED},
        candidate_proof=lambda _candidate, _commit: (),
    )
    repository = tmp_path / "repository"
    application.integrate_ready_change("change-a")
    application.integrate_ready_change("change-b")
    target_before = _git(repository, "rev-parse", "main")

    first = application.search_completed_changes("delivery", limit=1)
    second = application.search_completed_changes("delivery", first.next_cursor, 1)
    shown = application.show_completed_change("change-b", second.records[0].completion_id)

    assert tuple(item.change_id for item in (*first.records, *second.records)) == ("change-a", "change-b")
    assert shown == second.records[0]
    assert application.list_completed_changes(limit=100).records == (*first.records, *second.records)
    assert application.list_work_items() == ()
    assert application.list_integration_ready_changes() == ()
    assert "intent prose sentinel" not in shown.model_dump_json()
    assert _git(repository, "rev-parse", "main") == target_before


def test_integration_rejects_reviewed_sibling_completed_history_mutation(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED, "change-b": DeliveryStage.COMPLETED},
        candidate_proof=lambda _candidate, _commit: (),
    )
    repository = tmp_path / "repository"
    sibling = application.integrate_ready_change("change-b")
    assert sibling.completion is not None
    target_head = sibling.completion.target_commit
    coordination = coordinator.show("change-a")
    _git(coordination.worktree_path, "reset", "--hard", target_head)
    sibling_completion = coordination.worktree_path / ".owlbear/completed/change-b/completion.json"
    sibling_completion.write_text('{"mutated":true}\n', encoding="utf-8")
    _git(coordination.worktree_path, "add", str(sibling_completion))
    _git(coordination.worktree_path, "commit", "-m", "mutate sibling completion")
    reviewed = _git(coordination.worktree_path, "rev-parse", "HEAD")
    coordinator.update(coordination.model_copy(update={"last_reviewed_commit": reviewed}))
    completed_binding = runtimes["change-a"].show_binding("OUT-001")

    failed = application.integrate_ready_change("change-a")

    assert failed.attention is not None
    assert failed.attention.code == DeliveryIntegrationAttentionCode.COMPLETED_HISTORY_MUTATED
    assert _git(repository, "rev-parse", "main") == target_head
    assert runtimes["change-a"].show_binding("OUT-001") == completed_binding
    assert runtimes["change-a"].change_stage().value == "integration"
    assert (tmp_path / "packages/change-a").is_dir()


def test_integration_merge_conflict_retains_clean_heads_and_typed_attention(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
        candidate_proof=lambda _candidate, _commit: (),
    )
    _target_before, reviewed = _review_product_change(coordinator, "change-a", "change side\n")
    repository = tmp_path / "repository"
    (repository / "product.txt").write_text("target side\n", encoding="utf-8")
    _git(repository, "add", "product.txt")
    _git(repository, "commit", "-m", "concurrent target")
    target_head = _git(repository, "rev-parse", "main")

    failed = application.integrate_ready_change("change-a")

    assert failed.attention is not None
    assert failed.attention.code == DeliveryIntegrationAttentionCode.MERGE_CONFLICT
    assert failed.attention.change_head == reviewed
    assert failed.attention.target_head == target_head
    assert _git(repository, "rev-parse", "main") == target_head
    assert _git(repository, "rev-parse", coordinator.show("change-a").branch) == reviewed
    assert not _git(coordinator.show("change-a").worktree_path, "status", "--porcelain")
    assert runtimes["change-a"].change_stage().value == "integration"
    acquired = application.acquire_frontier_work()
    assert acquired.integration_ready_change_ids == ()
    assert len(acquired.repair_launch_packages) == 1
    repair_launch = acquired.repair_launch_packages[0]
    assert repair_launch.attention == failed.attention
    assert (
        application.show_integration_repair_context(
            repair_launch.change_id,
            repair_launch.claim.attempt_id,
            repair_launch.claim.claim_id,
        ).launch
        == repair_launch
    )
    assert acquired.integration_attention == ()
    integration_card = next(item for item in application.list_work_items() if item.work_item_id == "change-a")
    operator = application.show_operator_context("change-a", "change-a")
    assert (integration_card.scope, integration_card.attention.value, integration_card.next_action) == (
        "change-integration",
        "agent",
        "Repair in progress",
    )
    assert operator.integration_attention is not None
    assert operator.integration_attention.disposition.value == "repair-required"
    assert operator.integration_attention.retry_condition == (
        "Admit a reviewed Integration repair for this attention, then retry Integration."
    )

    (repository / "after-attention.txt").write_text("target advanced\n", encoding="utf-8")
    _git(repository, "add", "after-attention.txt")
    _git(repository, "commit", "-m", "advance target after attention")
    refreshed = application.acquire_frontier_work()
    assert refreshed.integration_ready_change_ids == ("change-a",)
    assert refreshed.integration_attention == ()
    assert len(refreshed.repair_recoveries) == 1
    assert refreshed.repair_recoveries[0].claim_id == repair_launch.claim.claim_id
    assert runtimes["change-a"].integration_repair_claim() is None
    assert coordinator.show("change-a").writer is None


def test_target_advance_projects_stale_conflict_as_queued_retry_without_refresh(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
        candidate_proof=lambda _candidate, _commit: (),
    )
    _target_before, _reviewed = _review_product_change(coordinator, "change-a", "change side\n")
    repository = tmp_path / "repository"
    (repository / "product.txt").write_text("target side\n", encoding="utf-8")
    _git(repository, "add", "product.txt")
    _git(repository, "commit", "-m", "concurrent target")
    failed = application.integrate_ready_change("change-a")
    assert failed.attention is not None
    persisted_target = coordinator.show("change-a").target_head

    (repository / "after-attention.txt").write_text("target advanced\n", encoding="utf-8")
    _git(repository, "add", "after-attention.txt")
    _git(repository, "commit", "-m", "advance target after attention")

    view = application.portfolio_read_view()
    integration = view.groups[0].items[-1]

    assert integration.progress.label == "Awaiting retry against current target"
    assert integration.action.kind is not None
    assert integration.action.kind.value == "retry-integration"
    assert tuple(item.change_id for item in view.operating.queued_for_orchestration) == ("change-a",)
    assert tuple(item.kind.value for item in view.operating.guidance) == ("start-orchestration",)
    assert application.list_integration_ready_changes() == ("change-a",)
    assert application.list_integration_attention() == ()
    assert runtimes["change-a"].integration_attention() == failed.attention
    assert coordinator.show("change-a").target_head == persisted_target


def test_reviewed_integration_repair_advances_boundary_and_retries_publication(tmp_path: Path) -> None:
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

    retried = application.integrate_ready_change("change-a")

    assert retried.completion is not None
    assert _git(repository, "show", f"{retried.completion.target_commit}:product.txt") == "target side"


def test_repair_authority_attention_releases_claim_and_is_not_reacquired(tmp_path: Path) -> None:
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
        candidate_proof=lambda _candidate, _commit: (),
    )
    _target_before, reviewed = _review_product_change(coordinator, "change-a", "change side\n")
    repository = tmp_path / "repository"
    (repository / "product.txt").write_text("target side\n", encoding="utf-8")
    _git(repository, "add", "product.txt")
    _git(repository, "commit", "-m", "concurrent target")
    failed = application.integrate_ready_change("change-a")
    acquired = application.acquire_frontier_work()
    launch = acquired.repair_launch_packages[0]

    attention = application.publish_integration_repair_authority_attention(
        launch.claim.attempt_id,
        launch.claim.claim_id,
        DeliveryIntegrationRepairAuthorityAttention(
            attention_id=launch.attention.attention_id,
            change_id="change-a",
            reason="The admitted authorities require incompatible public behavior.",
            locators=("product.txt",),
        ),
    )

    assert failed.attention is not None
    assert attention.code == DeliveryIntegrationAttentionCode.REPAIR_AUTHORITY
    assert attention.change_head == reviewed
    assert runtimes["change-a"].integration_repair_claim() is None
    assert coordinator.show("change-a").writer is None
    assert (
        CapacityLedger.model_validate_json((state_root / "target-runtime/capacity.json").read_bytes()).change_ids == ()
    )
    refreshed = application.acquire_frontier_work()
    assert refreshed.repair_launch_packages == ()
    assert refreshed.integration_ready_change_ids == ()
    assert refreshed.integration_attention[0].code == DeliveryIntegrationAttentionCode.REPAIR_AUTHORITY


def test_repair_authority_attention_preserves_claim_when_worktree_is_dirty(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
        candidate_proof=lambda _candidate, _commit: (),
    )
    _review_product_change(coordinator, "change-a", "change side\n")
    repository = tmp_path / "repository"
    (repository / "product.txt").write_text("target side\n", encoding="utf-8")
    _git(repository, "add", "product.txt")
    _git(repository, "commit", "-m", "concurrent target")
    application.integrate_ready_change("change-a")
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

    coordination_path = state_root / "target-runtime/coordination/change-a.json"
    frontier_path = state_root / "delivery/changes/change-a/frontier.json"
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


def test_interrupted_integration_repair_admission_converges_before_retry(tmp_path: Path) -> None:
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
    assert _git(repository, "rev-parse", "main") == repair.prior_target_head
    assert _file_bytes(package_root) == package_before

    retried = application.integrate_ready_change("change-a")

    assert retried.completion is not None


def test_integration_target_cas_loss_publishes_attention_without_own_commit(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    concurrent_head = ""

    def advance_target(_candidate: DeliveryIntegrationCandidate, _commit: str) -> tuple[str, ...]:
        nonlocal concurrent_head
        (repository / "concurrent.txt").write_text("concurrent\n", encoding="utf-8")
        _git(repository, "add", "concurrent.txt")
        _git(repository, "commit", "-m", "concurrent target")
        concurrent_head = _git(repository, "rev-parse", "HEAD")
        return ()

    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
        candidate_proof=advance_target,
    )
    target_before, reviewed = _review_product_change(coordinator, "change-a", "reviewed product\n")

    failed = application.integrate_ready_change("change-a")

    assert failed.attention is not None
    assert failed.attention.code == DeliveryIntegrationAttentionCode.TARGET_CAS_LOST
    assert failed.attention.target_head == target_before
    assert _git(repository, "rev-parse", "main") == concurrent_head
    assert _git(repository, "rev-parse", coordinator.show("change-a").branch) == reviewed
    assert runtimes["change-a"].change_stage().value == "integration"
    assert (tmp_path / "packages/change-a").is_dir()


def test_integration_rejects_revision_pending_and_source_mutation_before_visibility(tmp_path: Path) -> None:
    application, runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
        candidate_proof=lambda _candidate, _commit: (),
    )
    repository = tmp_path / "repository"
    target_head = _git(repository, "rev-parse", "main")
    package_root = tmp_path / "packages/change-a"
    intent_bytes = (package_root / "intent.md").read_bytes()
    design_bytes = (package_root / "design.md").read_bytes()
    authority_bytes = (package_root / "authority.json").read_bytes()
    revised_authority = b'{"revision":"pending"}\n'
    (package_root / "authority.json").write_bytes(revised_authority)
    pending_manifest = DesignPackageManifest.from_content(
        "change-a",
        intent_bytes,
        design_bytes,
        revised_authority,
    )
    (package_root / "manifest.json").write_bytes(pending_manifest.canonical_bytes())

    revision_pending = application.integrate_ready_change("change-a")

    assert revision_pending.attention is not None
    assert revision_pending.attention.code == DeliveryIntegrationAttentionCode.REVISION_PENDING
    assert _git(repository, "rev-parse", "main") == target_head

    changed_intent = b"changed intent\n"
    (package_root / "authority.json").write_bytes(authority_bytes)
    (package_root / "intent.md").write_bytes(changed_intent)
    mutated_manifest = DesignPackageManifest.from_content(
        "change-a",
        changed_intent,
        design_bytes,
        authority_bytes,
    )
    (package_root / "manifest.json").write_bytes(mutated_manifest.canonical_bytes())

    source_mutated = application.integrate_ready_change("change-a")

    assert source_mutated.attention is not None
    assert source_mutated.attention.code == DeliveryIntegrationAttentionCode.PACKAGE_MUTATED
    assert _git(repository, "rev-parse", "main") == target_head
    assert runtimes["change-a"].change_stage().value == "integration"


def test_integration_revalidates_package_after_candidate_proof_before_target_cas(tmp_path: Path) -> None:
    package_root = tmp_path / "packages/change-a"

    def mutate_package(_candidate: DeliveryIntegrationCandidate, _commit: str) -> tuple[str, ...]:
        (package_root / "design.md").write_text("mutated during proof\n", encoding="utf-8")
        return ()

    application, runtimes, _coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
        candidate_proof=mutate_package,
    )
    repository = tmp_path / "repository"
    target_head = _git(repository, "rev-parse", "main")

    failed = application.integrate_ready_change("change-a")

    assert failed.attention is not None
    assert failed.attention.code == DeliveryIntegrationAttentionCode.PACKAGE_MUTATED
    assert _git(repository, "rev-parse", "main") == target_head
    assert runtimes["change-a"].change_stage().value == "integration"


def test_integration_revalidates_reviewed_branch_after_candidate_proof(tmp_path: Path) -> None:
    worktree: Path | None = None

    def advance_change(_candidate: DeliveryIntegrationCandidate, _commit: str) -> tuple[str, ...]:
        assert worktree is not None
        (worktree / "late.txt").write_text("late change\n", encoding="utf-8")
        _git(worktree, "add", "late.txt")
        _git(worktree, "commit", "-m", "unreviewed late change")
        return ()

    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
        candidate_proof=advance_change,
    )
    worktree = coordinator.show("change-a").worktree_path
    repository = tmp_path / "repository"
    target_head = _git(repository, "rev-parse", "main")

    failed = application.integrate_ready_change("change-a")

    assert failed.attention is not None
    assert failed.attention.code == DeliveryIntegrationAttentionCode.REVIEWED_BOUNDARY_MISMATCH
    assert _git(repository, "rev-parse", "main") == target_head
    assert runtimes["change-a"].change_stage().value == "integration"


def test_integration_reports_dirty_reviewed_worktree_separately(tmp_path: Path) -> None:
    application, runtimes, coordinator, _state_root = _portfolio(
        tmp_path,
        {"change-a": DeliveryStage.COMPLETED},
    )
    worktree = coordinator.show("change-a").worktree_path
    repository = tmp_path / "repository"
    target_head = _git(repository, "rev-parse", "main")
    (worktree / "uncommitted.txt").write_text("uncommitted\n", encoding="utf-8")

    failed = application.integrate_ready_change("change-a")

    assert failed.attention is not None
    assert failed.attention.code == DeliveryIntegrationAttentionCode.REVIEWED_WORKTREE_DIRTY
    assert failed.attention.diagnostics == ("change worktree is not clean at its reviewed boundary",)
    assert _git(repository, "rev-parse", "main") == target_head
    assert runtimes["change-a"].change_stage().value == "integration"
