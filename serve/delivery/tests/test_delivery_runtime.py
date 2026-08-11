from __future__ import annotations

import json
import hashlib
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from owlbear_delivery import (
    DELIVERY_TRANSITION_ADAPTER,
    ActivateDeliveryClaim,
    AdministrativeDeliveryMove,
    AdvanceDelivery,
    BlockDelivery,
    ChangeWorkspaceManager,
    ChangeWriter,
    DeliveryActiveClaim,
    DeliveryChangeStage,
    DeliveryCheckpointTrigger,
    DeliveryCheckpointTriggerKind,
    DeliveryContract,
    DeliveryFrontier,
    DeliveryIntegrationAttention,
    DeliveryIntegrationAttentionCode,
    DeliveryIntegrationCompletion,
    DeliveryIntegrationAttentionDisposition,
    DeliveryOutcome,
    DeliveryOutputKind,
    DeliveryOutputReference,
    DeliveryPendingCheckpoint,
    DeliveryPlanScope,
    DeliveryRequest,
    DeliveryRequestKind,
    DeliveryRequestOption,
    DeliveryRequestResolution,
    DeliveryRuntime,
    DeliveryRuntimeConflictError,
    DeliveryRuntimeReferenceError,
    DeliveryStage,
    DeliveryTaskDefinition,
    DeliveryTaskResult,
    DeliveryWorkerRole,
    OutcomeAuthorityBinding,
    PortfolioCoordinator,
    PublishDeliveryPlan,
    PublishDeliveryResult,
    PublishDeliveryOutput,
    RetryDelivery,
    ReturnDelivery,
    integration_attention_disposition,
)
from owlbear_delivery.delivery_runtime import parse_delivery_frontier


def test_integration_attention_codes_have_one_operational_disposition() -> None:
    expected = {
        DeliveryIntegrationAttentionCode.MERGE_CONFLICT: DeliveryIntegrationAttentionDisposition.REPAIR_REQUIRED,
        DeliveryIntegrationAttentionCode.TARGET_CAS_LOST: DeliveryIntegrationAttentionDisposition.RETRYABLE,
    }

    assert {code: integration_attention_disposition(code) for code in DeliveryIntegrationAttentionCode} == {
        code: expected.get(code, DeliveryIntegrationAttentionDisposition.OPERATOR_REQUIRED)
        for code in DeliveryIntegrationAttentionCode
    }


def _contract() -> DeliveryContract:
    outcomes = (
        DeliveryOutcome(
            outcome_id="OUT-001",
            title="Foundation",
            promise="Deliver the foundation.",
            acceptance=("Foundation is observable.",),
            commitment_ids=(),
            dependency_ids=(),
        ),
        DeliveryOutcome(
            outcome_id="OUT-002",
            title="Dependent",
            promise="Deliver the dependent result.",
            acceptance=("Dependent result is observable.",),
            commitment_ids=(),
            dependency_ids=("OUT-001",),
        ),
        DeliveryOutcome(
            outcome_id="OUT-003",
            title="Independent",
            promise="Deliver the independent result.",
            acceptance=("Independent result is observable.",),
            commitment_ids=(),
            dependency_ids=(),
        ),
    )
    return DeliveryContract(
        change_id="delivery-runtime",
        title="Delivery runtime",
        commitments=(),
        outcomes=outcomes,
        plan_scopes=tuple(
            DeliveryPlanScope(scope_id=f"SCOPE-{index:03}", outcome_id=outcome.outcome_id)
            for index, outcome in enumerate(outcomes, start=1)
        ),
        source_bindings=(
            {"source_name": "intent.md", "sha256": "a" * 64},
            {"source_name": "design.md", "sha256": "b" * 64},
        ),
    )


def _canonical(model: DeliveryFrontier) -> bytes:
    return (json.dumps(model.model_dump(mode="json"), sort_keys=True, separators=(",", ":")) + "\n").encode()


def _runtime(
    tmp_path: Path,
    *,
    stages: tuple[DeliveryStage, DeliveryStage, DeliveryStage] = (
        DeliveryStage.PLANNING,
        DeliveryStage.PLANNING,
        DeliveryStage.PLANNING,
    ),
) -> DeliveryRuntime:
    contract = _contract()
    authority_digest = hashlib.sha256(
        (json.dumps(contract.model_dump(mode="json"), sort_keys=True, separators=(",", ":")) + "\n").encode()
    ).hexdigest()
    bindings = []
    for index, stage in enumerate(stages, start=1):
        task = _task(f"TASK-{index:03}", outcome_id=f"OUT-{index:03}")
        results = (
            (
                DeliveryTaskResult(
                    result_id=f"RESULT-{index:03}",
                    change_id="delivery-runtime",
                    authority_digest=authority_digest,
                    task_id=task.task_id,
                    task_digest=task.digest,
                    completed_commit=f"{index}" * 40,
                ),
            )
            if stage == DeliveryStage.COMPLETED
            else ()
        )
        bindings.append(
            OutcomeAuthorityBinding(
                outcome_id=f"OUT-{index:03}",
                plan_scope_id=f"SCOPE-{index:03}",
                stage=stage,
                tasks=(task,) if stage not in {DeliveryStage.DESIGN, DeliveryStage.PLANNING} else (),
                results=results,
            )
        )
    frontier = DeliveryFrontier(bindings=tuple(bindings))
    path = tmp_path / "changes/delivery-runtime/frontier.json"
    path.parent.mkdir(parents=True)
    path.write_bytes(_canonical(frontier))
    return DeliveryRuntime(tmp_path, contract)


def _output(claim_id: str, stage: DeliveryStage) -> DeliveryOutputReference:
    return DeliveryOutputReference(
        output_id=f"output-{stage.value}",
        claim_id=claim_id,
        stage=stage,
        kind=DeliveryOutputKind(stage.value),
        digest="c" * 64,
    )


def _activate(
    runtime: DeliveryRuntime,
    outcome_id: str,
    claim_id: str,
    *,
    task_id: str | None = None,
):
    stage = runtime.show_binding(outcome_id).stage
    role = {
        DeliveryStage.PLANNING: DeliveryWorkerRole.PLANNER,
        DeliveryStage.IMPLEMENTATION: DeliveryWorkerRole.BUILDER,
    }[stage]
    return runtime.activate_claim(
        ActivateDeliveryClaim(
            outcome_id=outcome_id,
            claim=DeliveryActiveClaim(
                attempt_id=f"attempt-{claim_id}",
                claim_id=claim_id,
                owner_id=f"owner-{claim_id}",
                process_id=f"process-{claim_id}",
                started_at="2026-08-04T00:00:00Z",
                worker_role=role,
                task_id=task_id,
            ),
        )
    )


def _claim_with_output(runtime: DeliveryRuntime, outcome_id: str, claim_id: str) -> DeliveryOutputReference:
    binding = runtime.show_binding(outcome_id)
    task_id = runtime.claimable_task_ids(outcome_id)[0] if binding.stage == DeliveryStage.IMPLEMENTATION else None
    claimed = _activate(runtime, outcome_id, claim_id, task_id=task_id)
    output = _output(claim_id, claimed.stage)
    runtime.publish_output(PublishDeliveryOutput(outcome_id=outcome_id, claim_id=claim_id, output=output))
    return output


def test_integration_repair_claim_is_change_scoped_and_exact(tmp_path: Path) -> None:
    runtime = _runtime(
        tmp_path,
        stages=(DeliveryStage.COMPLETED, DeliveryStage.COMPLETED, DeliveryStage.COMPLETED),
    )
    runtime.publish_integration_attention(
        DeliveryIntegrationAttention(
            attention_id="a" * 64,
            code=DeliveryIntegrationAttentionCode.MERGE_CONFLICT,
            change_id="delivery-runtime",
            change_head="1" * 40,
            target_head="2" * 40,
            integration_target="main",
            diagnostics=("merge conflict",),
            retry_condition="Admit an independently reviewed repair.",
        )
    )
    claim = DeliveryActiveClaim(
        attempt_id="repair-attempt",
        claim_id="repair-claim",
        owner_id="repair-owner",
        process_id="repair-process",
        started_at="2026-08-04T00:00:00Z",
        worker_role=DeliveryWorkerRole.INTEGRATION_REPAIRER,
    )

    assert runtime.activate_integration_repair_claim(claim) == claim
    assert runtime.require_integration_repair_claim("repair-attempt", "repair-claim") == claim
    with pytest.raises(DeliveryRuntimeConflictError, match="already claimed"):
        runtime.activate_integration_repair_claim(claim)
    with pytest.raises(DeliveryRuntimeConflictError, match="execution identity"):
        runtime.require_integration_repair_claim("other-attempt", "repair-claim")
    assert runtime.remove_integration_repair_claim("repair-attempt", "repair-claim") == claim
    assert runtime.integration_repair_claim() is None


def _task(
    task_id: str,
    *,
    outcome_id: str = "OUT-001",
    dependency_ids: tuple[str, ...] = (),
) -> DeliveryTaskDefinition:
    plan_scope_id = outcome_id.replace("OUT", "SCOPE")
    return DeliveryTaskDefinition(
        task_id=task_id,
        outcome_id=outcome_id,
        plan_scope_id=plan_scope_id,
        title=f"Produce {task_id}",
        result="One bounded implementation result.",
        commitment_ids=(),
        dependency_ids=dependency_ids,
        required_outputs=("Reviewed source commit",),
        maintained_surfaces=("serve/delivery/src/owlbear_delivery/delivery_runtime.py",),
        constraints=("Keep schema-v2 state isolated.",),
        exclusions=("Do not edit bootstrap runtime.",),
        acceptance_observations=("The public runtime exposes the completed result binding.",),
        proof_boundaries=("Focused DeliveryRuntime behavior test",),
    )


def test_plan_publication_is_idempotent_and_promotes_dependency_order(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    _activate(runtime, "OUT-001", "claim-001")
    request = PublishDeliveryPlan(
        outcome_id="OUT-001",
        claim_id="claim-001",
        tasks=(_task("TASK-001"), _task("TASK-002", dependency_ids=("TASK-001",))),
    )

    candidate = runtime.publish_plan(request)
    replayed = runtime.publish_plan(request)

    assert replayed == candidate
    assert runtime.show_binding("OUT-001").stage == DeliveryStage.PLANNING
    assert runtime.show_binding("OUT-001").tasks == ()

    promoted = runtime.transition(AdvanceDelivery(outcome_id="OUT-001", claim_id="claim-001", output=candidate.output))

    assert promoted.tasks == request.tasks
    assert promoted.candidate is None
    assert promoted.stage == DeliveryStage.IMPLEMENTATION
    assert runtime.claimable_task_ids("OUT-001") == ("TASK-001",)


def test_runtime_migrates_reducible_assembly_metadata_transactionally(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    path = tmp_path / "changes/delivery-runtime/frontier.json"
    payload = json.loads(runtime.frontier_bytes())
    payload["schema_version"] = 1
    for binding in payload["bindings"]:
        binding["assembly_required"] = False
    path.write_text(json.dumps(payload), encoding="utf-8")

    migrated = DeliveryRuntime(tmp_path, _contract())
    canonical = json.loads(migrated.frontier_bytes())

    assert canonical["schema_version"] == 3
    assert all("assembly_required" not in binding for binding in canonical["bindings"])
    assert json.loads(path.read_bytes()) == canonical


def test_runtime_migrates_schema_two_checkpoint_state_transactionally(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    path = tmp_path / "changes/delivery-runtime/frontier.json"
    payload = json.loads(runtime.frontier_bytes())
    payload["schema_version"] = 2
    payload.pop("published_head")
    payload.pop("pending_checkpoint")
    path.write_text(json.dumps(payload), encoding="utf-8")

    migrated = DeliveryRuntime(tmp_path, _contract())
    canonical = json.loads(migrated.frontier_bytes())

    assert canonical["schema_version"] == 3
    assert canonical["published_head"] is None
    assert canonical["pending_checkpoint"] is None
    assert json.loads(path.read_bytes()) == canonical


def test_schema_two_result_history_backfills_checkpoint_at_exact_reviewed_head(tmp_path: Path) -> None:
    runtime = _runtime(
        tmp_path,
        stages=(DeliveryStage.COMPLETED, DeliveryStage.COMPLETED, DeliveryStage.PLANNING),
    )
    payload = json.loads(runtime.frontier_bytes())
    payload["schema_version"] = 2
    payload.pop("published_head")
    payload.pop("pending_checkpoint")

    migrated, _canonical_bytes = parse_delivery_frontier(
        json.dumps(payload).encode(),
        migration_reviewed_head="f" * 40,
        require_checkpoint_backfill=True,
    )

    assert migrated.pending_checkpoint is not None
    assert migrated.pending_checkpoint.head == "f" * 40
    assert tuple((trigger.kind, trigger.outcome_id) for trigger in migrated.pending_checkpoint.triggers) == (
        (DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK, None),
        (DeliveryCheckpointTriggerKind.VERIFIED_OUTCOME, "OUT-001"),
        (DeliveryCheckpointTriggerKind.VERIFIED_OUTCOME, "OUT-002"),
    )


@pytest.mark.parametrize(
    ("stage", "assembly_required_value"),
    [("planning", "true"), ("assembly", "false")],
)
def test_runtime_rejects_irreducible_assembly_authority(
    tmp_path: Path,
    stage: str,
    assembly_required_value: str,
) -> None:
    runtime = _runtime(tmp_path)
    path = tmp_path / "changes/delivery-runtime/frontier.json"
    payload = json.loads(runtime.frontier_bytes())
    payload["schema_version"] = 1
    payload["bindings"][0]["stage"] = stage
    payload["bindings"][0]["assembly_required"] = assembly_required_value == "true"
    original = json.dumps(payload).encode()
    path.write_bytes(original)

    with pytest.raises(DeliveryRuntimeReferenceError, match="missing or invalid"):
        DeliveryRuntime(tmp_path, _contract())

    assert path.read_bytes() == original


def test_plan_publication_rejects_unresolved_or_cyclic_graph_without_mutation(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    _activate(runtime, "OUT-001", "claim-001")
    before = runtime.frontier_bytes()

    with pytest.raises(DeliveryRuntimeReferenceError, match="dependency"):
        runtime.publish_plan(
            PublishDeliveryPlan(
                outcome_id="OUT-001",
                claim_id="claim-001",
                tasks=(_task("TASK-001", dependency_ids=("TASK-404",)),),
            )
        )
    assert runtime.frontier_bytes() == before

    with pytest.raises(DeliveryRuntimeConflictError, match="acyclic"):
        runtime.publish_plan(
            PublishDeliveryPlan(
                outcome_id="OUT-001",
                claim_id="claim-001",
                tasks=(
                    _task("TASK-001", dependency_ids=("TASK-002",)),
                    _task("TASK-002", dependency_ids=("TASK-001",)),
                ),
            )
        )
    assert runtime.frontier_bytes() == before


def _git(repository: Path, *arguments: str) -> str:
    return subprocess.run(
        ("git", "-C", str(repository), *arguments),
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _workspace(tmp_path: Path):
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.name", "Delivery Runtime Test")
    _git(repository, "config", "user.email", "delivery-runtime@example.invalid")
    (repository / "product.txt").write_text("base\n", encoding="utf-8")
    _git(repository, "add", "product.txt")
    _git(repository, "commit", "-m", "baseline")
    state_root = tmp_path / "state"
    coordinator = PortfolioCoordinator(state_root, capacity=1)
    manager = ChangeWorkspaceManager(repository, tmp_path / "worktrees", coordinator, "main")
    coordination = manager.create("delivery-runtime")
    return state_root, coordinator, manager, coordination


def _publish_task_result(
    runtime: DeliveryRuntime,
    coordinator: PortfolioCoordinator,
    coordination,
    *,
    job_id: int,
    outcome_id: str = "OUT-001",
):
    task_id = runtime.claimable_task_ids(outcome_id)[0]
    attempt_id = f"attempt-{job_id:03}"
    claim_id = f"claim-{job_id:03}"
    coordinator.acquire(
        "delivery-runtime",
        ChangeWriter(
            attempt_id=attempt_id,
            claim_id=claim_id,
            actor_id=f"builder-{job_id:03}",
            process_id=f"process-{job_id:03}",
            claimed_at=f"2026-08-04T00:0{job_id}:00Z",
            job_id=job_id,
            kind="build",
        ),
    )
    _activate(runtime, outcome_id, claim_id, task_id=task_id)
    (coordination.worktree_path / "product.txt").write_text(f"{task_id}\n", encoding="utf-8")
    _git(coordination.worktree_path, "add", "product.txt")
    _git(coordination.worktree_path, "commit", "-m", f"complete {task_id}")
    completed_commit = _git(coordination.worktree_path, "rev-parse", "HEAD")
    task = next(item for item in runtime.show_binding(outcome_id).tasks if item.task_id == task_id)
    result = DeliveryTaskResult(
        result_id=f"RESULT-{job_id:03}",
        change_id="delivery-runtime",
        authority_digest=runtime.authority_digest,
        task_id=task.task_id,
        task_digest=task.digest,
        completed_commit=completed_commit,
    )
    candidate = runtime.publish_result(PublishDeliveryResult(outcome_id=outcome_id, claim_id=claim_id, result=result))
    return result, candidate, completed_commit, claim_id


def _plan_single_task(runtime: DeliveryRuntime, outcome_id: str, task: DeliveryTaskDefinition) -> None:
    claim_id = f"plan-{outcome_id}"
    _activate(runtime, outcome_id, claim_id)
    plan = runtime.publish_plan(
        PublishDeliveryPlan(
            outcome_id=outcome_id,
            claim_id=claim_id,
            tasks=(task,),
        )
    )
    runtime.transition(AdvanceDelivery(outcome_id=outcome_id, claim_id=claim_id, output=plan.output))


def test_first_task_checkpoint_is_change_wide_and_one_task_outcomes_coalesce(tmp_path: Path) -> None:
    state_root, coordinator, manager, coordination = _workspace(tmp_path)
    frontier = DeliveryFrontier(
        bindings=tuple(
            OutcomeAuthorityBinding(
                outcome_id=f"OUT-{index:03}",
                plan_scope_id=f"SCOPE-{index:03}",
            )
            for index in range(1, 4)
        )
    )
    frontier_path = state_root / "changes/delivery-runtime/frontier.json"
    frontier_path.parent.mkdir(parents=True)
    frontier_path.write_bytes(_canonical(frontier))
    runtime = DeliveryRuntime(state_root, _contract(), workspace_manager=manager)

    for index in (1, 3):
        outcome_id = f"OUT-{index:03}"
        task_id = f"TASK-{index:03}"
        _plan_single_task(runtime, outcome_id, _task(task_id, outcome_id=outcome_id))
        _result, candidate, _commit, claim_id = _publish_task_result(
            runtime,
            coordinator,
            coordination,
            job_id=index,
            outcome_id=outcome_id,
        )
        runtime.transition(AdvanceDelivery(outcome_id=outcome_id, claim_id=claim_id, output=candidate.output))

    pending = runtime.checkpoint_publication_state().pending_checkpoint
    assert pending is not None
    assert tuple((trigger.kind, trigger.outcome_id) for trigger in pending.triggers) == (
        (DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK, None),
        (DeliveryCheckpointTriggerKind.VERIFIED_OUTCOME, "OUT-001"),
        (DeliveryCheckpointTriggerKind.VERIFIED_OUTCOME, "OUT-003"),
    )

    preview = runtime.preview_administrative_move("OUT-001", DeliveryStage.PLANNING)
    runtime.administrative_move(
        AdministrativeDeliveryMove(
            move_id="move-checkpoint-reanchor",
            outcome_id="OUT-001",
            target=DeliveryStage.PLANNING,
            reason="Replace invalidated foundation authority.",
            expected_version=preview.snapshot_version,
        )
    )
    unanchored = runtime.checkpoint_publication_state().pending_checkpoint
    assert unanchored is not None
    assert unanchored.head is None
    assert tuple((trigger.kind, trigger.outcome_id) for trigger in unanchored.triggers) == (
        (DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK, None),
        (DeliveryCheckpointTriggerKind.VERIFIED_OUTCOME, "OUT-003"),
    )

    _plan_single_task(runtime, "OUT-001", _task("TASK-004", outcome_id="OUT-001"))
    _result, candidate, reviewed_head, claim_id = _publish_task_result(
        runtime,
        coordinator,
        coordination,
        job_id=4,
    )
    runtime.transition(AdvanceDelivery(outcome_id="OUT-001", claim_id=claim_id, output=candidate.output))
    reanchored = runtime.checkpoint_publication_state().pending_checkpoint
    assert reanchored is not None
    assert reanchored.head == reviewed_head
    assert tuple((trigger.kind, trigger.outcome_id) for trigger in reanchored.triggers) == (
        (DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK, None),
        (DeliveryCheckpointTriggerKind.VERIFIED_OUTCOME, "OUT-003"),
        (DeliveryCheckpointTriggerKind.VERIFIED_OUTCOME, "OUT-001"),
    )


def test_pending_checkpoint_rejects_duplicate_first_task_trigger() -> None:
    with pytest.raises(ValueError, match="unique per scope"):
        DeliveryPendingCheckpoint(
            head="1" * 40,
            triggers=(
                DeliveryCheckpointTrigger(
                    kind=DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK,
                ),
                DeliveryCheckpointTrigger(
                    kind=DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK,
                ),
            ),
        )


def test_build_advance_binds_compact_result_and_releases_writer(tmp_path: Path) -> None:
    state_root, coordinator, manager, coordination = _workspace(tmp_path)
    frontier = DeliveryFrontier(
        bindings=tuple(
            OutcomeAuthorityBinding(
                outcome_id=f"OUT-{index:03}",
                plan_scope_id=f"SCOPE-{index:03}",
            )
            for index in range(1, 4)
        )
    )
    frontier_path = state_root / "changes/delivery-runtime/frontier.json"
    frontier_path.parent.mkdir(parents=True)
    frontier_path.write_bytes(_canonical(frontier))
    runtime = DeliveryRuntime(state_root, _contract(), workspace_manager=manager)
    _activate(runtime, "OUT-001", "plan-claim")
    plan = runtime.publish_plan(
        PublishDeliveryPlan(
            outcome_id="OUT-001",
            claim_id="plan-claim",
            tasks=(
                _task("TASK-001"),
                _task("TASK-002", dependency_ids=("TASK-001",)),
                _task("TASK-003", dependency_ids=("TASK-002",)),
            ),
        )
    )
    runtime.transition(AdvanceDelivery(outcome_id="OUT-001", claim_id="plan-claim", output=plan.output))
    result, candidate, completed_commit, first_claim = _publish_task_result(
        runtime,
        coordinator,
        coordination,
        job_id=1,
    )

    advance = AdvanceDelivery(outcome_id="OUT-001", claim_id=first_claim, output=candidate.output)
    with (
        patch.object(runtime, "_replace", side_effect=RuntimeError("injected after workspace completion")),
        pytest.raises(RuntimeError, match="injected"),
    ):
        runtime.transition(advance)
    assert coordinator.show("delivery-runtime").last_reviewed_commit == completed_commit
    assert coordinator.show("delivery-runtime").writer is None

    advanced = runtime.transition(advance)

    assert advanced.results == (result,)
    assert advanced.stage == DeliveryStage.IMPLEMENTATION
    assert runtime.claimable_task_ids("OUT-001") == ("TASK-002",)
    assert coordinator.show("delivery-runtime").last_reviewed_commit == completed_commit
    assert coordinator.show("delivery-runtime").writer is None
    assert json.loads(runtime.frontier_bytes())["bindings"][0]["results"] == [result.model_dump(mode="json")]
    first_checkpoint = runtime.checkpoint_publication_state()
    assert first_checkpoint.published_head is None
    assert first_checkpoint.pending_checkpoint is not None
    assert first_checkpoint.pending_checkpoint.head == completed_commit
    assert tuple(trigger.kind for trigger in first_checkpoint.pending_checkpoint.triggers) == (
        DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK,
    )

    second_result, second_candidate, second_commit, second_claim = _publish_task_result(
        runtime,
        coordinator,
        coordination,
        job_id=2,
    )

    second_advance = runtime.transition(
        AdvanceDelivery(
            outcome_id="OUT-001",
            claim_id=second_claim,
            output=second_candidate.output,
        )
    )

    assert second_advance.stage == DeliveryStage.IMPLEMENTATION
    middle_checkpoint = runtime.checkpoint_publication_state()
    assert middle_checkpoint.pending_checkpoint is not None
    assert middle_checkpoint.pending_checkpoint.head == second_commit
    assert tuple(trigger.kind for trigger in middle_checkpoint.pending_checkpoint.triggers) == (
        DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK,
    )
    third_result, third_candidate, _third_commit, third_claim = _publish_task_result(
        runtime,
        coordinator,
        coordination,
        job_id=3,
    )

    completed = runtime.transition(
        AdvanceDelivery(
            outcome_id="OUT-001",
            claim_id=third_claim,
            output=third_candidate.output,
        )
    )

    assert completed.stage == DeliveryStage.COMPLETED
    assert completed.results == (result, second_result, third_result)
    completed_checkpoint = runtime.checkpoint_publication_state()
    assert completed_checkpoint.pending_checkpoint is not None
    assert completed_checkpoint.pending_checkpoint.head == third_result.completed_commit
    assert tuple(trigger.kind for trigger in completed_checkpoint.pending_checkpoint.triggers) == (
        DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK,
        DeliveryCheckpointTriggerKind.VERIFIED_OUTCOME,
    )
    serialized = runtime.frontier_bytes().decode()
    for residue in (
        "reviewer-sentinel",
        "model-sentinel",
        "command-sentinel",
        "passing-report-sentinel",
        "review-evidence-sentinel",
    ):
        assert residue not in serialized


def _active_second_task(tmp_path: Path):
    state_root, coordinator, manager, coordination = _workspace(tmp_path)
    initial = _git(coordination.worktree_path, "rev-parse", "HEAD")
    contract = _contract()
    authority_digest = hashlib.sha256(
        (json.dumps(contract.model_dump(mode="json"), sort_keys=True, separators=(",", ":")) + "\n").encode()
    ).hexdigest()
    tasks = (_task("TASK-001"), _task("TASK-002", dependency_ids=("TASK-001",)))
    first_result = DeliveryTaskResult(
        result_id="RESULT-001",
        change_id="delivery-runtime",
        authority_digest=authority_digest,
        task_id="TASK-001",
        task_digest=tasks[0].digest,
        completed_commit=initial,
    )
    frontier = DeliveryFrontier(
        bindings=(
            OutcomeAuthorityBinding(
                outcome_id="OUT-001",
                plan_scope_id="SCOPE-001",
                stage=DeliveryStage.IMPLEMENTATION,
                tasks=tasks,
                results=(first_result,),
            ),
            OutcomeAuthorityBinding(outcome_id="OUT-002", plan_scope_id="SCOPE-002"),
            OutcomeAuthorityBinding(outcome_id="OUT-003", plan_scope_id="SCOPE-003"),
        )
    )
    frontier_path = state_root / "changes/delivery-runtime/frontier.json"
    frontier_path.parent.mkdir(parents=True)
    frontier_path.write_bytes(_canonical(frontier))
    runtime = DeliveryRuntime(state_root, contract, workspace_manager=manager)
    coordinator.acquire(
        "delivery-runtime",
        ChangeWriter(
            attempt_id="attempt-002",
            claim_id="claim-002",
            actor_id="builder-002",
            process_id="process-002",
            claimed_at="2026-08-04T00:00:00Z",
            job_id=2,
            kind="build",
        ),
    )
    _activate(runtime, "OUT-001", "claim-002", task_id="TASK-002")
    (coordination.worktree_path / "product.txt").write_text("unreviewed task two\n", encoding="utf-8")
    _git(coordination.worktree_path, "add", "product.txt")
    _git(coordination.worktree_path, "commit", "-m", "unreviewed task two")
    attempt_commit = _git(coordination.worktree_path, "rev-parse", "HEAD")
    return runtime, coordinator, coordination, initial, attempt_commit, first_result, tasks


@pytest.mark.parametrize("instruction", ["retry", "planning", "design", "block"])
def test_implementation_nonadvance_persists_only_consumed_successor_state(
    tmp_path: Path,
    instruction: str,
) -> None:
    runtime, coordinator, coordination, initial, attempt_commit, first_result, tasks = _active_second_task(tmp_path)
    requests = {
        "retry": RetryDelivery(
            outcome_id="OUT-001",
            claim_id="claim-002",
            abandoned_commit=attempt_commit,
            attempt_id="attempt-002",
        ),
        "planning": ReturnDelivery(
            outcome_id="OUT-001",
            claim_id="claim-002",
            target=DeliveryStage.PLANNING,
            reason="The remaining task authority is incomplete.",
            locators=("TASK-002",),
            preserved_commit=attempt_commit,
            attempt_id="attempt-002",
        ),
        "design": ReturnDelivery(
            outcome_id="OUT-001",
            claim_id="claim-002",
            target=DeliveryStage.DESIGN,
            reason="The admitted outcome meaning is insufficient.",
            locators=("OUT-001",),
            preserved_commit=attempt_commit,
            attempt_id="attempt-002",
        ),
        "block": BlockDelivery(
            outcome_id="OUT-001",
            claim_id="claim-002",
            block_id="block-002",
            reason="External evidence is unavailable.",
            unblock_condition="The evidence is supplied.",
            expected_evidence=("External result",),
            locators=("TASK-002",),
            request=DeliveryRequest(
                request_id="request-002",
                kind=DeliveryRequestKind.ACTION,
                outcome_id="OUT-001",
                summary="Supply the external result.",
            ),
            resume_commit=attempt_commit,
        ),
    }

    with (
        patch.object(runtime, "_replace", side_effect=RuntimeError("injected after workspace reconciliation")),
        pytest.raises(RuntimeError, match="injected"),
    ):
        runtime.transition(requests[instruction])

    result = runtime.transition(requests[instruction])
    current = coordinator.show("delivery-runtime")

    assert result.active_claim_id is None
    assert current.writer is None
    assert current.last_reviewed_commit == initial
    if instruction == "retry":
        assert result.tasks == tasks
        assert result.results == (first_result,)
        assert result.return_context is None
        assert _git(coordination.worktree_path, "rev-parse", "HEAD") == initial
        assert (
            _git(coordination.worktree_path, "rev-parse", "refs/owlbear/attempts/delivery-runtime/attempt-002")
            == attempt_commit
        )
    elif instruction == "planning":
        assert result.stage == DeliveryStage.PLANNING
        assert result.tasks == (tasks[0],)
        assert result.results == (first_result,)
        assert result.return_context is not None
        assert result.return_context.preserved_commit == attempt_commit
        assert _git(coordination.worktree_path, "rev-parse", "HEAD") == initial
    elif instruction == "design":
        assert result.stage == DeliveryStage.DESIGN
        assert result.tasks == result.results == ()
        assert result.return_context is not None
        assert result.return_context.completed_boundary == initial
        assert _git(coordination.worktree_path, "rev-parse", "HEAD") == initial
    else:
        assert result.stage == DeliveryStage.IMPLEMENTATION
        assert result.tasks == tasks
        assert result.results == (first_result,)
        assert result.block is not None
        assert result.block.resume_commit == attempt_commit
        assert _git(coordination.worktree_path, "rev-parse", "HEAD") == attempt_commit


@pytest.mark.parametrize(
    ("stage", "transition", "expected_stage"),
    [
        (DeliveryStage.PLANNING, "block", DeliveryStage.PLANNING),
    ],
)
def test_worker_transition_routes_canonical_stage_and_rejects_stale_or_review_input(
    tmp_path: Path,
    stage: DeliveryStage,
    transition: str,
    expected_stage: DeliveryStage,
) -> None:
    runtime = _runtime(tmp_path, stages=(stage, DeliveryStage.PLANNING, DeliveryStage.PLANNING))
    output = _claim_with_output(runtime, "OUT-001", "claim-001")

    request = {
        "advance": AdvanceDelivery(outcome_id="OUT-001", claim_id="claim-001", output=output),
        "retry": RetryDelivery(outcome_id="OUT-001", claim_id="claim-001"),
        "return": ReturnDelivery(
            outcome_id="OUT-001",
            claim_id="claim-001",
            target=DeliveryStage.PLANNING,
            reason="The task authority needs revision.",
            locators=("TASK-001",),
        ),
        "block": BlockDelivery(
            outcome_id="OUT-001",
            claim_id="claim-001",
            block_id="block-001",
            reason="External evidence is unavailable.",
            unblock_condition="The evidence is supplied.",
            expected_evidence=("External result",),
            locators=("RESULT-001",),
        ),
    }[transition]
    result = runtime.transition(request)

    assert result.stage == expected_stage
    before = runtime.frontier_bytes()
    with pytest.raises(DeliveryRuntimeConflictError, match="active claim"):
        runtime.transition(request)
    assert runtime.frontier_bytes() == before
    with pytest.raises(ValidationError):
        DELIVERY_TRANSITION_ADAPTER.validate_python(
            {
                "action": "advance",
                "outcome_id": "OUT-001",
                "claim_id": "claim-002",
                "output": _output("claim-002", expected_stage).model_dump(mode="json"),
                "reviewer_id": "reviewer-001",
                "disposition": "acceptable",
            }
        )
    assert runtime.frontier_bytes() == before


def test_request_resolution_and_requestless_unblock_preserve_stage_and_answer(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    _activate(runtime, "OUT-001", "claim-001")
    request = DeliveryRequest(
        request_id="request-001",
        kind=DeliveryRequestKind.DECISION,
        outcome_id="OUT-001",
        summary="Choose the bounded source.",
        options=(
            DeliveryRequestOption(option_id="local", label="Use local source"),
            DeliveryRequestOption(option_id="remote", label="Use remote source"),
        ),
    )
    runtime.transition(
        BlockDelivery(
            outcome_id="OUT-001",
            claim_id="claim-001",
            block_id="block-001",
            reason="A bounded decision is required.",
            unblock_condition="The source is selected.",
            expected_evidence=("Selected source",),
            locators=("COM-001",),
            request=request,
        )
    )

    resolved = runtime.resolve_request(
        "request-001",
        DeliveryRequestResolution(selected_option_id="local", response_text="Use the checked-in copy."),
    )

    assert resolved.resolution is not None
    assert resolved.resolution.selected_option_id == "local"
    assert resolved.resolution.response_text == "Use the checked-in copy."
    assert runtime.show_binding("OUT-001").stage == DeliveryStage.PLANNING
    assert runtime.claimable_outcome_ids() == ("OUT-001", "OUT-003")

    _activate(runtime, "OUT-003", "claim-003")
    runtime.transition(
        BlockDelivery(
            outcome_id="OUT-003",
            claim_id="claim-003",
            block_id="block-003",
            reason="Manual verification is pending.",
            unblock_condition="Verification is recorded.",
            expected_evidence=("Verification locator",),
            locators=("RESULT-003",),
        )
    )
    runtime.unblock("OUT-003", "block-003", "Verification completed.", ("RESULT-003",))
    assert runtime.show_binding("OUT-003").stage == DeliveryStage.PLANNING
    assert "OUT-003" in runtime.claimable_outcome_ids()


def test_implementation_block_requires_bounded_user_request(tmp_path: Path) -> None:
    runtime, coordinator, _coordination, _initial, attempt_commit, _first_result, _tasks = _active_second_task(tmp_path)
    before = runtime.frontier_bytes()

    with pytest.raises(DeliveryRuntimeConflictError, match="bounded user request"):
        runtime.transition(
            BlockDelivery(
                outcome_id="OUT-001",
                claim_id="claim-002",
                block_id="build-context-tool-unavailable",
                reason="Required live Build context is unavailable.",
                unblock_condition="The Build context tool is available.",
                expected_evidence=("Successful Build context lookup",),
                locators=("TASK-002",),
                resume_commit=attempt_commit,
            )
        )

    assert runtime.frontier_bytes() == before
    assert coordinator.show("delivery-runtime").writer is not None


def test_administrative_backward_move_invalidates_completed_dependents_only(tmp_path: Path) -> None:
    runtime = _runtime(
        tmp_path,
        stages=(DeliveryStage.COMPLETED, DeliveryStage.COMPLETED, DeliveryStage.COMPLETED),
    )
    path = tmp_path / "changes/delivery-runtime/frontier.json"
    frontier = DeliveryFrontier.model_validate_json(runtime.frontier_bytes())
    pending = DeliveryPendingCheckpoint(
        head="3" * 40,
        triggers=(
            DeliveryCheckpointTrigger(
                kind=DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK,
            ),
            DeliveryCheckpointTrigger(
                kind=DeliveryCheckpointTriggerKind.VERIFIED_OUTCOME,
                outcome_id="OUT-001",
            ),
            DeliveryCheckpointTrigger(
                kind=DeliveryCheckpointTriggerKind.VERIFIED_OUTCOME,
                outcome_id="OUT-003",
            ),
        ),
    )
    path.write_bytes(_canonical(frontier.model_copy(update={"pending_checkpoint": pending})))
    runtime = DeliveryRuntime(tmp_path, _contract())
    assert runtime.change_stage() == DeliveryChangeStage.INTEGRATION
    before = runtime.frontier_bytes()
    preview = runtime.preview_administrative_move("OUT-001", DeliveryStage.PLANNING)

    assert preview.invalidated_outcome_ids == ("OUT-001", "OUT-002")
    assert preview.snapshot_version == hashlib.sha256(before).hexdigest()
    assert runtime.frontier_bytes() == before

    result = runtime.administrative_move(
        AdministrativeDeliveryMove(
            move_id="move-001",
            outcome_id="OUT-001",
            target=DeliveryStage.PLANNING,
            reason="The foundation result was invalidated by operator evidence.",
            expected_version=preview.snapshot_version,
        )
    )

    assert result.invalidated_outcome_ids == ("OUT-001", "OUT-002")
    assert runtime.show_binding("OUT-001").stage == DeliveryStage.PLANNING
    assert runtime.show_binding("OUT-002").stage == DeliveryStage.PLANNING
    assert runtime.show_binding("OUT-003").stage == DeliveryStage.COMPLETED
    assert runtime.show_binding("OUT-003").result_ids == ("RESULT-003",)
    retained = runtime.checkpoint_publication_state().pending_checkpoint
    assert retained is not None
    assert retained.head is None
    assert retained.triggers == (pending.triggers[0], pending.triggers[2])
    assert runtime.change_stage() == DeliveryChangeStage.ACTIVE_DELIVERY


def test_administrative_move_retires_integration_attention(tmp_path: Path) -> None:
    runtime = _runtime(
        tmp_path,
        stages=(DeliveryStage.COMPLETED, DeliveryStage.COMPLETED, DeliveryStage.COMPLETED),
    )
    runtime.publish_integration_attention(
        DeliveryIntegrationAttention(
            attention_id="a" * 64,
            code=DeliveryIntegrationAttentionCode.REPAIR_AUTHORITY,
            change_id="delivery-runtime",
            change_head="1" * 40,
            target_head="2" * 40,
            integration_target="main",
            diagnostics=("The repair exceeded admitted authority.",),
            retry_condition="Move the change to an earlier stage.",
        )
    )

    runtime.administrative_move(
        AdministrativeDeliveryMove(
            move_id="move-001",
            outcome_id="OUT-001",
            target=DeliveryStage.PLANNING,
            reason="Revise the admitted authority.",
            expected_version=hashlib.sha256(runtime.frontier_bytes()).hexdigest(),
        )
    )

    assert runtime.integration_attention() is None
    assert runtime.change_stage() == DeliveryChangeStage.ACTIVE_DELIVERY


def test_administrative_move_rejects_active_integration_repair(tmp_path: Path) -> None:
    runtime = _runtime(
        tmp_path,
        stages=(DeliveryStage.COMPLETED, DeliveryStage.COMPLETED, DeliveryStage.COMPLETED),
    )
    runtime.publish_integration_attention(
        DeliveryIntegrationAttention(
            attention_id="a" * 64,
            code=DeliveryIntegrationAttentionCode.MERGE_CONFLICT,
            change_id="delivery-runtime",
            change_head="1" * 40,
            target_head="2" * 40,
            integration_target="main",
            diagnostics=("merge conflict",),
            retry_condition="Admit an independently reviewed repair.",
        )
    )
    runtime.activate_integration_repair_claim(
        DeliveryActiveClaim(
            attempt_id="repair-attempt",
            claim_id="repair-claim",
            owner_id="repair-owner",
            process_id="repair-process",
            started_at="2026-08-04T00:00:00Z",
            worker_role=DeliveryWorkerRole.INTEGRATION_REPAIRER,
        )
    )
    before = runtime.frontier_bytes()

    with pytest.raises(DeliveryRuntimeConflictError, match="active Integration repair claim"):
        runtime.administrative_move(
            AdministrativeDeliveryMove(
                move_id="move-001",
                outcome_id="OUT-001",
                target=DeliveryStage.PLANNING,
                reason="Revise the admitted authority.",
                expected_version=hashlib.sha256(runtime.frontier_bytes()).hexdigest(),
            )
        )

    assert runtime.frontier_bytes() == before


def test_administrative_move_rejects_completed_integration(tmp_path: Path) -> None:
    runtime = _runtime(
        tmp_path,
        stages=(DeliveryStage.COMPLETED, DeliveryStage.COMPLETED, DeliveryStage.COMPLETED),
    )
    runtime.publish_integration_completion(
        DeliveryIntegrationCompletion(
            completion_id="a" * 64,
            candidate_id="b" * 64,
            package_id="c" * 64,
            target_commit="1" * 40,
            completion_path=".owlbear/completed/delivery-runtime.json",
        )
    )
    before = runtime.frontier_bytes()

    with pytest.raises(DeliveryRuntimeConflictError, match="completed Integration"):
        runtime.administrative_move(
            AdministrativeDeliveryMove(
                move_id="move-001",
                outcome_id="OUT-001",
                target=DeliveryStage.PLANNING,
                reason="Revise the admitted authority.",
                expected_version=hashlib.sha256(runtime.frontier_bytes()).hexdigest(),
            )
        )

    assert runtime.frontier_bytes() == before


def test_administrative_move_preserves_active_dependent_claim(tmp_path: Path) -> None:
    runtime = _runtime(
        tmp_path,
        stages=(DeliveryStage.COMPLETED, DeliveryStage.IMPLEMENTATION, DeliveryStage.COMPLETED),
    )
    _activate(runtime, "OUT-002", "claim-002", task_id="TASK-002")
    active_dependent = runtime.show_binding("OUT-002")

    result = runtime.administrative_move(
        AdministrativeDeliveryMove(
            move_id="move-001",
            outcome_id="OUT-001",
            target=DeliveryStage.PLANNING,
            reason="The foundation result was invalidated by operator evidence.",
            expected_version=hashlib.sha256(runtime.frontier_bytes()).hexdigest(),
        )
    )

    assert result.invalidated_outcome_ids == ("OUT-001",)
    assert runtime.show_binding("OUT-002") == active_dependent


def test_administrative_move_rejects_a_stale_preview(tmp_path: Path) -> None:
    runtime = _runtime(
        tmp_path,
        stages=(DeliveryStage.COMPLETED, DeliveryStage.COMPLETED, DeliveryStage.COMPLETED),
    )
    preview = runtime.preview_administrative_move("OUT-001", DeliveryStage.PLANNING)
    runtime.publish_integration_attention(
        DeliveryIntegrationAttention(
            attention_id="a" * 64,
            code=DeliveryIntegrationAttentionCode.REPAIR_AUTHORITY,
            change_id="delivery-runtime",
            change_head="1" * 40,
            target_head="2" * 40,
            integration_target="main",
            diagnostics=("Authority changed.",),
            retry_condition="Move backward.",
        )
    )

    with pytest.raises(DeliveryRuntimeConflictError, match="preview is stale"):
        runtime.administrative_move(
            AdministrativeDeliveryMove(
                move_id="move-stale",
                outcome_id="OUT-001",
                target=DeliveryStage.PLANNING,
                reason="Use stale evidence.",
                expected_version=preview.snapshot_version,
            )
        )
