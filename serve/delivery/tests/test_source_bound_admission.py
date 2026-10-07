from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from owlbear_delivery import (
    ActivateDeliveryClaim,
    AdvanceDelivery,
    ChangeTargetSyncReceipt,
    DeliveryAcceptanceRef,
    DeliveryActiveClaim,
    DeliveryAdmissionConflictError,
    DeliveryAdmissionRequest,
    DeliveryAuthorityRegistry,
    DeliveryChangeDeferral,
    DeliveryChangePublicationHistory,
    DeliveryChangePublicationIdentity,
    DeliveryChangeStage,
    DeliveryCheckpointTrigger,
    DeliveryCheckpointTriggerKind,
    DeliveryCommandResult,
    DeliveryConfirmationScope,
    DeliveryContract,
    DeliveryFrontier,
    DeliveryManualProcedureResult,
    DeliveryObservation,
    DeliveryObservationReceipt,
    DeliveryPendingCheckpoint,
    DeliveryPendingStatePublication,
    DeliveryRequest,
    DeliveryRequestKind,
    DeliveryRequestOption,
    DeliveryRequestResolution,
    DeliveryReturnContext,
    DeliveryReview,
    DeliveryReviewReceipt,
    DeliveryRuntime,
    DeliveryRuntimeConflictError,
    DeliveryStage,
    DeliveryTaskDefinition,
    DeliveryTaskResult,
    DeliveryWorkerRole,
    DesignPackageManifest,
    DesignPackageStore,
    OutcomeAuthorityBinding,
    PublishDeliveryPlan,
)
from owlbear_delivery.acceptance import (
    CompletionDisplayMetadata,
    CompletionEvidence,
    CompletionPullRequestIdentity,
    CompletionReceipt,
    CompletionReceiptStore,
)
from owlbear_delivery.acceptance_criteria import acceptance_criteria
from owlbear_delivery.evidence import evaluate_acceptance_evidence, observation_gaps
from owlbear_delivery.git_executable import resolve_git_executable

if TYPE_CHECKING:
    from collections.abc import Callable

_GIT = resolve_git_executable()


def _git(repository: Path, *arguments: str) -> str:
    return subprocess.run(  # noqa: S603
        (_GIT, "-C", str(repository), *arguments),
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    path = tmp_path / "repository"
    path.mkdir()
    _git(path, "init", "-b", "product")
    _git(path, "config", "user.name", "Source Admission Test")
    _git(path, "config", "user.email", "source-admission@example.invalid")
    (path / "product.txt").write_text("product\n", encoding="utf-8")
    _git(path, "add", "product.txt")
    _git(path, "commit", "-m", "product baseline")
    return path


def _commitment(identity: str, statement: str) -> str:
    return f"""```yaml target-contract
kind: commitment
id: {identity}
class: agreed-path
provenance: source admission test
statement: {statement}
```
"""


def _outcome(
    identity: str,
    commitment: str,
    dependencies: tuple[str, ...] = (),
) -> str:
    dependency_list = ", ".join(dependencies)
    return f"""```yaml target-contract
kind: outcome
id: {identity}
title: Result {identity}
promise: Deliver {identity}.
acceptance: ["AC-{identity[4:]}: {identity} is observable."]
commitments: [{commitment}]
dependencies: [{dependency_list}]
```
"""


def _sources(*, first_statement: str = "Keep the first result stable.") -> tuple[bytes, bytes]:
    intent = "\n".join(
        (
            "# Source-Bound Change\n",
            _commitment("COM-001", first_statement),
            _commitment("COM-002", "Keep the dependent result stable."),
            _outcome("OUT-001", "COM-001"),
            _outcome("OUT-002", "COM-002", ("OUT-001",)),
        )
    )
    design = "\n".join(
        (
            "# Source-Bound Architecture\n",
            _commitment("COM-003", "Keep the independent result stable."),
            _outcome("OUT-003", "COM-003"),
        )
    )
    return intent.encode(), design.encode()


def _request(package_store: DesignPackageStore) -> DeliveryAdmissionRequest:
    package = package_store.read_verified("source-bound-change")
    authored_manifest = DesignPackageManifest.from_content(
        "source-bound-change",
        package.intent_bytes,
        package.design_bytes,
    )
    return DeliveryAdmissionRequest(
        change_id="source-bound-change",
        expected_package_id=hashlib.sha256(authored_manifest.canonical_bytes()).hexdigest(),
        active_claim_ids=(),
    )


def test_admission_rejects_stale_approved_package_before_publication(
    repository: Path,
    tmp_path: Path,
) -> None:
    active_root = tmp_path / "active"
    target_root = tmp_path / "target"
    package_store = DesignPackageStore(active_root, repository)
    intent_bytes, design_bytes = _sources()
    package = package_store.create("source-bound-change", intent_bytes, design_bytes)
    package_store.revise(
        "source-bound-change",
        package.package_id,
        intent_bytes + b"\nRevised after approval.\n",
        design_bytes,
    )
    registry = DeliveryAuthorityRegistry(target_root, package_store, integration_target="product")

    with pytest.raises(DeliveryAdmissionConflictError, match="Design package changed before admission"):
        registry.admit(
            DeliveryAdmissionRequest(
                change_id="source-bound-change",
                expected_package_id=package.package_id,
                active_claim_ids=(),
            )
        )

    assert not (target_root / "changes/source-bound-change").exists()


def _retain_completion(target_root: Path, change_id: str) -> dict[Path, bytes]:
    digest = hashlib.sha256(change_id.encode()).hexdigest()
    receipt = CompletionReceipt.create(
        CompletionEvidence(
            change_id=change_id,
            finalization_receipt_id=digest,
            finalized_change_head=digest[:40],
            repository_identity="example/project",
            pull_request_identity=CompletionPullRequestIdentity(number=7, node_id="PR_node_7"),
            accepted_target_ref="product",
            accepted_merge_commit=digest[-40:],
            merged_at=datetime(2026, 8, 11, 12, tzinfo=UTC),
            acceptance_observation_id=digest,
            check_observation_ids=(digest,),
            review_receipt_ids=(digest,),
            completed_at=datetime(2026, 8, 11, 13, tzinfo=UTC),
        )
    )
    display = CompletionDisplayMetadata.create(
        change_id=change_id,
        completion_id=receipt.completion_id,
        title="Earlier delivery",
        outcome_titles=("Earlier result",),
        outcome_promises=("Deliver the earlier result.",),
    )
    store = CompletionReceiptStore(target_root)
    retained = {}
    for participant in (store.participant(receipt), store.display_participant(display)):
        destination = participant.destination()
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(participant.content)
        retained[destination] = participant.content
    return retained


@pytest.mark.parametrize("malformed", [False, True])
def test_first_admission_refuses_change_id_with_completed_history(
    repository: Path,
    tmp_path: Path,
    *,
    malformed: bool,
) -> None:
    active_root = tmp_path / "active"
    target_root = tmp_path / "target"
    package_store = DesignPackageStore(active_root, repository)
    package_store.create("source-bound-change", *_sources())
    retained = _retain_completion(target_root, "source-bound-change")
    if malformed:
        display = target_root / "completions/source-bound-change/display.json"
        display.unlink()
        del retained[display]
    registry = DeliveryAuthorityRegistry(target_root, package_store, integration_target="product")

    with pytest.raises(DeliveryAdmissionConflictError, match="already has completed history"):
        registry.admit(_request(package_store))

    assert not (target_root / "changes/source-bound-change").exists()
    assert not _git(repository, "for-each-ref", "refs/owlbear/packages/source-bound-change")
    assert {path: path.read_bytes() for path in retained} == retained


def _canonical(model: DeliveryFrontier) -> bytes:
    return (json.dumps(model.model_dump(mode="json"), sort_keys=True, separators=(",", ":")) + "\n").encode()


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
            procedure="source-bound admission fixture validation",
            result=DeliveryCommandResult(exit_status=0),
            observer_or_runner_identity="pytest",
            observed_at=observed_at,
        )
    )
    review = DeliveryReviewReceipt.create(
        DeliveryReview(
            review_mode="task",
            exact_commit=completed_commit,
            author_id="Source admission test author",
            reviewer_id="Source admission test reviewer",
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


def test_admission_recovers_receipt_last_publication_and_replays_exact_sources(
    repository: Path,
    tmp_path: Path,
) -> None:
    active_root = tmp_path / "active"
    target_root = tmp_path / "target"
    intent_bytes, design_bytes = _sources()
    package_store = DesignPackageStore(active_root, repository)
    package_store.create("source-bound-change", intent_bytes, design_bytes)

    def interrupt(stage: str) -> None:
        if stage == "after-first-publication":
            message = "receipt-last interruption"
            raise RuntimeError(message)

    interrupted = DeliveryAuthorityRegistry(
        target_root,
        package_store,
        integration_target="product",
        failure=interrupt,
    )
    with pytest.raises(RuntimeError, match="receipt-last interruption"):
        interrupted.admit(_request(package_store))

    delivery_root = target_root / "changes/source-bound-change"
    assert (delivery_root / "contract.json").is_file()
    assert not (delivery_root / "admission.json").exists()

    registry = DeliveryAuthorityRegistry(target_root, package_store, integration_target="product")
    recovered = registry.admit(_request(package_store))
    replayed = registry.admit(_request(package_store))

    assert recovered.replayed is True
    assert replayed == recovered
    assert recovered.receipt.checkpoint_commit == _git(
        repository,
        "rev-parse",
        "refs/owlbear/packages/source-bound-change",
    )
    assert tuple(binding.outcome_id for binding in recovered.frontier.bindings) == (
        "OUT-001",
        "OUT-002",
        "OUT-003",
    )
    assert all(binding.task_ids == binding.result_ids == () for binding in recovered.frontier.bindings)
    assert not (target_root / "delivery/changes/source-bound-change").exists()


def test_admission_preserves_staged_user_checkout_outside_declared_package_path(
    repository: Path,
    user_checkout_snapshot,
) -> None:
    active_root = repository / ".owlbear/delivery/packages"
    target_root = repository / ".owlbear/delivery/runtime"
    package_store = DesignPackageStore(active_root, repository)
    intent_bytes, design_bytes = _sources()
    package_store.create("source-bound-change", intent_bytes, design_bytes)
    _git(repository, "add", ".owlbear/delivery/packages")
    _git(repository, "commit", "-m", "author source-bound package")
    (repository / "product.txt").write_text("staged user work\n", encoding="utf-8")
    _git(repository, "add", "product.txt")
    (repository / "untracked-user.txt").write_text("untracked user work\n", encoding="utf-8")
    before = user_checkout_snapshot(
        repository,
        ("refs/owlbear/packages/source-bound-change",),
        (
            ".owlbear/delivery/packages/source-bound-change",
            ".owlbear/delivery/runtime",
        ),
    )

    registry = DeliveryAuthorityRegistry(target_root, package_store, integration_target="product")
    result = registry.admit(_request(package_store))
    replayed = registry.admit(_request(package_store))

    assert replayed.replayed is True
    assert result.receipt.checkpoint_commit == _git(
        repository,
        "rev-parse",
        "refs/owlbear/packages/source-bound-change",
    )
    before.assert_unchanged(repository)


def test_rejected_package_validation_cannot_publish_during_later_recovery(
    repository: Path,
    tmp_path: Path,
) -> None:
    active_root = tmp_path / "active"
    intent_bytes, design_bytes = _sources()
    store = DesignPackageStore(active_root, repository)
    created = store.create("source-bound-change", intent_bytes, design_bytes)

    def reject(_intent: bytes, _design: bytes, _contract: bytes) -> None:
        message = "contract mismatch"
        raise RuntimeError(message)

    with pytest.raises(RuntimeError, match="contract mismatch"):
        store.publish_contract(
            "source-bound-change",
            created.package_id,
            b'{"rejected":true}\n',
            reject,
        )

    store.checkpoint("source-bound-change")
    verified = store.read_verified("source-bound-change")
    assert verified.authority_bytes == b""
    assert not list((active_root / "transactions").glob("*.yaml"))


def _write_revision(active_root: Path, contract_bytes: bytes, intent: bytes, design: bytes) -> None:
    package_root = active_root / "source-bound-change"
    (package_root / "intent.md").write_bytes(intent)
    (package_root / "design.md").write_bytes(design)
    manifest = DesignPackageManifest.from_content("source-bound-change", intent, design, contract_bytes)
    (package_root / "manifest.json").write_bytes(manifest.canonical_bytes())


def _activate(
    registry: DeliveryAuthorityRegistry,
    package_store: DesignPackageStore,
    frontier_bytes: bytes,
    snapshot_head: str = "4" * 40,
):
    request = _request(package_store).model_copy(
        update={"expected_frontier_digest": hashlib.sha256(frontier_bytes).hexdigest()}
    )
    return registry.activate_revision(request, snapshot=lambda: snapshot_head, base_frontier_digest="0" * 64)


def test_revision_replans_changed_outcomes_and_keeps_change_state(
    repository: Path,
    tmp_path: Path,
) -> None:
    active_root = tmp_path / "active"
    target_root = tmp_path / "target"
    package_store = DesignPackageStore(active_root, repository)
    package_store.create("source-bound-change", *_sources())
    registry = DeliveryAuthorityRegistry(target_root, package_store, integration_target="product")
    first = registry.admit(_request(package_store))
    populated_bindings = []
    for index, binding in enumerate(first.frontier.bindings, start=1):
        task = DeliveryTaskDefinition(
            task_id=f"TASK-{index:03}",
            outcome_id=binding.outcome_id,
            plan_scope_id=binding.plan_scope_id,
            title=f"Produce result {index}",
            result=f"Result {index}",
            commitment_ids=(),
            dependency_ids=(),
            required_outputs=("Reviewed commit",),
            maintained_surfaces=("serve/delivery",),
            constraints=(),
            exclusions=(),
            acceptance_observations=("Result is bound",),
            proof_boundaries=("Delivery runtime",),
        )
        result = _task_result(
            f"RESULT-{index:03}",
            "source-bound-change",
            first.contract_digest,
            task,
            f"{index}" * 40,
        )
        populated_bindings.append(
            OutcomeAuthorityBinding(
                outcome_id=binding.outcome_id,
                plan_scope_id=binding.plan_scope_id,
                stage=DeliveryStage.IMPLEMENTATION,
                tasks=(task,),
                results=(result,),
            )
        )
    pending = DeliveryPendingCheckpoint(
        head="3" * 40,
        triggers=(
            DeliveryCheckpointTrigger(kind=DeliveryCheckpointTriggerKind.FIRST_PROMOTED_TASK),
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
    publication = DeliveryChangePublicationIdentity(
        change_id="source-bound-change", repository="example/project", number=7, node_id="PR_7", head_sha="2" * 40
    )
    populated = DeliveryFrontier(
        bindings=tuple(populated_bindings),
        published_head="2" * 40,
        pending_checkpoint=pending,
        change_publication_history=DeliveryChangePublicationHistory(
            change_id="source-bound-change", publications=(publication,)
        ),
        target_sync_receipt=ChangeTargetSyncReceipt.create(
            operation_id="sync-1",
            change_id="source-bound-change",
            integration_target="product",
            expected_target="5" * 40,
            target_head="5" * 40,
            change_head_before="1" * 40,
            merged_head="2" * 40,
            merge_commit=True,
        ),
        change_deferral=DeliveryChangeDeferral.create(
            change_id="source-bound-change",
            prior_stage=DeliveryChangeStage.BUILDING,
            deferred_at=datetime(2026, 8, 11, 13, tzinfo=UTC),
            reason="Revise the requirements",
        ),
    )
    delivery_root = target_root / "changes/source-bound-change"
    populated_bytes = _canonical(populated)
    (delivery_root / "frontier.json").write_bytes(populated_bytes)
    _write_revision(active_root, first.contract_bytes, *_sources(first_statement="Change the first result behavior."))

    revised = _activate(registry, package_store, populated_bytes)

    assert revised.carry_forward is not None
    assert revised.carry_forward.preserved_outcome_ids == ("OUT-003",)
    assert revised.carry_forward.invalidated_outcome_ids == ("OUT-001", "OUT-002")
    bindings = {binding.outcome_id: binding for binding in revised.frontier.bindings}
    assert bindings["OUT-003"] == populated.bindings[2]
    for outcome_id, previous in zip(("OUT-001", "OUT-002"), populated.bindings[:2], strict=True):
        assert bindings[outcome_id].stage is DeliveryStage.PLANNING
        assert bindings[outcome_id].tasks == previous.tasks
        assert bindings[outcome_id].results == previous.results
        assert bindings[outcome_id].return_context == DeliveryReturnContext(
            target=DeliveryStage.PLANNING,
            reason="requirement revision",
            locators=(outcome_id,),
            source_boundary=revised.contract_digest,
        )
    unchanged = {"bindings", "pending_checkpoint", "change_deferral", "finalization_invalidation"}
    assert revised.frontier.model_dump(exclude=unchanged) == populated.model_dump(exclude=unchanged)
    assert revised.frontier.change_deferral is None
    assert revised.frontier.pending_checkpoint == DeliveryPendingCheckpoint(
        head="4" * 40, triggers=(pending.triggers[0], pending.triggers[2])
    )
    history = delivery_root / "revisions" / f"{first.contract_digest}-{hashlib.sha256(populated_bytes).hexdigest()}"
    assert (history / "frontier.json").read_bytes() == populated_bytes
    assert (history / "contract.json").read_bytes() == first.contract_bytes
    marker = DeliveryPendingStatePublication.model_validate_json(
        (delivery_root / "state-publication.json").read_bytes()
    )
    assert marker == DeliveryPendingStatePublication.pending(
        "0" * 64, hashlib.sha256((delivery_root / "frontier.json").read_bytes()).hexdigest()
    )
    assert registry.admit(
        _request(package_store).model_copy(
            update={"expected_frontier_digest": hashlib.sha256(populated_bytes).hexdigest()}
        )
    ).replayed


def test_revision_rejects_active_claims_and_direct_admission_before_mutation(repository: Path, tmp_path: Path) -> None:
    active_root = tmp_path / "active"
    target_root = tmp_path / "target"
    package_store = DesignPackageStore(active_root, repository)
    package_store.create("source-bound-change", *_sources())
    registry = DeliveryAuthorityRegistry(target_root, package_store, integration_target="product")
    first = registry.admit(_request(package_store))
    _write_revision(active_root, first.contract_bytes, *_sources(first_statement="Changed behavior."))
    frontier_bytes = _canonical(first.frontier)
    snapshots: list[str] = []

    with pytest.raises(DeliveryAdmissionConflictError, match="active claims block"):
        registry.activate_revision(
            _request(package_store).model_copy(
                update={
                    "active_claim_ids": ("active-claim",),
                    "expected_frontier_digest": hashlib.sha256(frontier_bytes).hexdigest(),
                }
            ),
            snapshot=lambda: snapshots.append("called") or "4" * 40,
            base_frontier_digest="0" * 64,
        )
    with pytest.raises(DeliveryAdmissionConflictError, match="only through revision activation"):
        registry.admit(_request(package_store))

    assert snapshots == []
    assert (target_root / "changes/source-bound-change/contract.json").read_bytes() == first.contract_bytes
    assert not (target_root / "changes/source-bound-change/revisions").exists()
    assert package_store.read_verified("source-bound-change").authority_bytes == first.contract_bytes


def _evidence_sources(
    second: str = "AC-002: The second criterion holds.", *, extra: bool = False
) -> tuple[bytes, bytes]:
    acceptance = ", ".join(
        f'"{item}"'
        for item in ("AC-001: The first criterion holds.", second, *(("AC-004: Optional.",) if extra else ()))
    )
    intent = f"""# Source-Bound Change

{_commitment("COM-001", "Keep the first result stable.")}
```yaml target-contract
kind: outcome
id: OUT-001
title: Result OUT-001
promise: Deliver OUT-001.
acceptance: [{acceptance}]
commitments: [COM-001]
dependencies: []
```

{_commitment("COM-003", "Keep the independent result stable.")}
{_outcome("OUT-003", "COM-003")}
"""
    return intent.encode(), b"# Source-Bound Architecture\n"


def _task(task_id: str, outcome_id: str, scope_id: str, commitments: tuple[str, ...], dependencies=()):
    return DeliveryTaskDefinition(
        task_id=task_id,
        outcome_id=outcome_id,
        plan_scope_id=scope_id,
        title=f"Produce {task_id}",
        result=f"Result {task_id}",
        commitment_ids=commitments,
        dependency_ids=dependencies,
        required_outputs=("Reviewed commit",),
        maintained_surfaces=("serve/delivery",),
        constraints=(),
        exclusions=(),
        acceptance_observations=("Result is bound",),
        proof_boundaries=("Delivery runtime",),
    )


def _seeded_revision(  # noqa: PLR0913 - one admitted, seeded and activated revision.
    repository: Path,
    tmp_path: Path,
    tasks: tuple[DeliveryTaskDefinition, ...],
    completed: int,
    revised_sources: tuple[bytes, bytes],
    *,
    initial_sources: tuple[bytes, bytes] | None = None,
    seed: Callable[[OutcomeAuthorityBinding, DeliveryContract], OutcomeAuthorityBinding] = lambda binding, _: binding,
):
    """Admit evidence sources, seed OUT-001 with ``completed`` results, then activate ``revised_sources``."""
    active_root = tmp_path / "active"
    target_root = tmp_path / "target"
    package_store = DesignPackageStore(active_root, repository)
    package_store.create("source-bound-change", *(initial_sources or _evidence_sources()))
    registry = DeliveryAuthorityRegistry(target_root, package_store, integration_target="product")
    first = registry.admit(_request(package_store))
    results = tuple(
        _task_result(f"RESULT-{task.task_id}", "source-bound-change", first.contract_digest, task, "1" * 40)
        for task in tasks[:completed]
    )
    binding = seed(
        first.frontier.bindings[0].model_copy(
            update={"stage": DeliveryStage.IMPLEMENTATION, "tasks": tasks, "results": results}
        ),
        first.contract,
    )
    frontier_bytes = _canonical(first.frontier.model_copy(update={"bindings": (binding, *first.frontier.bindings[1:])}))
    (target_root / "changes/source-bound-change/frontier.json").write_bytes(frontier_bytes)
    _write_revision(active_root, first.contract_bytes, *revised_sources)
    revised = _activate(registry, package_store, frontier_bytes)
    return revised, DeliveryRuntime(target_root, revised.contract)


@pytest.mark.parametrize(
    ("revised_commitment", "kept"),
    [("COM-001", ("TASK-001", "TASK-002", "TASK-003")), ("COM-009", ("TASK-002",))],
    ids=["commitments-survive", "commitment-removed"],
)
def test_replanned_outcome_keeps_completed_work_whose_commitments_survive(
    repository: Path, tmp_path: Path, revised_commitment: str, kept: tuple[str, ...]
) -> None:
    tasks = (
        _task("TASK-001", "OUT-001", "SCOPE-001", ("COM-001",)),
        _task("TASK-002", "OUT-001", "SCOPE-001", ()),
        _task("TASK-003", "OUT-001", "SCOPE-001", (), ("TASK-001",)),
        _task("TASK-004", "OUT-001", "SCOPE-001", ()),
    )
    intent, design = _evidence_sources("AC-002: The second criterion changed.")
    intent = intent.replace(b"COM-001", revised_commitment.encode())

    revised, _runtime = _seeded_revision(repository, tmp_path, tasks, 3, (intent, design))

    binding = revised.frontier.bindings[0]
    assert binding.stage is DeliveryStage.PLANNING
    assert binding.task_ids == kept
    assert tuple(result.task_id for result in binding.results) == kept
    assert binding.return_context is not None
    assert binding.return_context.locators == ("AC-002",)


def test_replanned_outcome_planning_preserves_completed_tasks_and_completes_without_delta(
    repository: Path, tmp_path: Path
) -> None:
    completed = _task("TASK-001", "OUT-001", "SCOPE-001", ("COM-001",))
    _revised, runtime = _seeded_revision(
        repository, tmp_path, (completed,), 1, _evidence_sources(), initial_sources=_evidence_sources(extra=True)
    )
    claim = DeliveryActiveClaim(
        attempt_id="attempt-1",
        claim_id="claim-1",
        owner_id="owner",
        process_id="process",
        started_at="2026-08-11T12:00:00+00:00",
        worker_role=DeliveryWorkerRole.PLANNER,
    )
    runtime.activate_claim(ActivateDeliveryClaim(outcome_id="OUT-001", claim=claim))
    added = _task("TASK-002", "OUT-001", "SCOPE-001", ())
    for tasks in ((completed.model_copy(update={"title": "Altered"}), added), (added,)):
        with pytest.raises(DeliveryRuntimeConflictError, match="preserve completed task definitions"):
            runtime.publish_plan(PublishDeliveryPlan(outcome_id="OUT-001", claim_id="claim-1", tasks=tasks))

    candidate = runtime.publish_plan(PublishDeliveryPlan(outcome_id="OUT-001", claim_id="claim-1", tasks=(completed,)))
    advanced = runtime.transition(
        AdvanceDelivery(action="advance", outcome_id="OUT-001", claim_id="claim-1", output=candidate.output)
    )

    assert advanced.stage is DeliveryStage.COMPLETED
    assert advanced.task_ids == ("TASK-001",)
    assert tuple(result.task_id for result in advanced.results) == ("TASK-001",)


def test_revision_keeps_unchanged_criterion_evidence_and_scoped_confirmation(repository: Path, tmp_path: Path) -> None:
    task = _task("TASK-001", "OUT-001", "SCOPE-001", ("COM-001",))
    confirmed = {
        "result": DeliveryManualProcedureResult(assessment="passed"),
        "provenance": "human-confirmed",
        "request_id": "REQ-CONFIRM",
    }

    def record(procedure: str, covers: tuple[DeliveryAcceptanceRef, ...], **changes: object):
        values: dict[str, object] = {
            "change_id": "source-bound-change",
            "task_or_finalization_id": task.task_id,
            "exact_commit": "1" * 40,
            "observation_kind": "pytest",
            "procedure": procedure,
            "result": DeliveryCommandResult(exit_status=0),
            "observer_or_runner_identity": "pytest",
            "observed_at": datetime(2026, 8, 11, 12, tzinfo=UTC),
            "covers": covers,
        }
        return DeliveryObservationReceipt.create(DeliveryObservation(**(values | changes)))

    def seed(binding: OutcomeAuthorityBinding, contract: DeliveryContract) -> OutcomeAuthorityBinding:
        first, second = (criterion.ref for criterion in acceptance_criteria(contract)[:2])
        request = DeliveryRequest(
            request_id="REQ-CONFIRM",
            kind=DeliveryRequestKind.DECISION,
            outcome_id="OUT-001",
            summary="Confirm both criteria",
            options=tuple(DeliveryRequestOption(option_id=item, label=item) for item in ("passed", "failed")),
            applies_to=DeliveryConfirmationScope(kind="confirm-check", acceptance=(first, second), procedure="manual"),
            resolution=DeliveryRequestResolution(selected_option_id="passed", provenance="user-confirmed"),
        )
        observations = (record("uv run pytest", (first,)), record("manual", (first, second), **confirmed))
        (result,) = binding.results
        return binding.model_copy(
            update={"results": (result.model_copy(update={"observations": observations}),), "requests": (request,)}
        )

    revised, runtime = _seeded_revision(
        repository, tmp_path, (task,), 1, _evidence_sources("AC-002: The second criterion changed."), seed=seed
    )

    criteria = acceptance_criteria(runtime.contract)
    coverage = evaluate_acceptance_evidence(runtime.contract, revised.frontier).criteria
    reconfirmation = observation_gaps(
        record("manual", (criteria[1].ref,), **confirmed), revised.frontier, criteria, "OUT-001"
    )

    assert revised.frontier.bindings[0].requests[0].request_id == "REQ-CONFIRM"
    assert {item.acceptance_id: item.status for item in coverage} == {
        "AC-001": "covered",
        "AC-002": "uncovered",
        "AC-003": "uncovered",
    }
    assert [gap.reason for gap in reconfirmation] == ["request-not-applicable"]
