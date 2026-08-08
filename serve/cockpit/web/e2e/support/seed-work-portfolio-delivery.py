# ruff: noqa: INP001
"""Seed real Delivery owners and completed history for assembled Work E2E."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from pydantic import BaseModel

from owlbear_delivery.change_workspace import ChangeWorkspaceManager, PortfolioCoordinator
from owlbear_delivery.delivery_application_loader import DeliveryStartupConfig
from owlbear_delivery.delivery_runtime import (
    DeliveryActiveClaim,
    DeliveryBlock,
    DeliveryFrontier,
    DeliveryIntegrationAttention,
    DeliveryIntegrationAttentionCode,
    DeliveryRequest,
    DeliveryRequestKind,
    DeliveryRequestOption,
    DeliveryReturnContext,
    DeliveryStage,
    DeliveryTaskDefinition,
    DeliveryTaskResult,
    DeliveryWorkerRole,
    OutcomeAuthorityBinding,
)
from owlbear_delivery.design_package import CompletionPackageManifest, DesignPackageManifest
from owlbear_delivery.target_contract import (
    DeliveryCommitment,
    DeliveryCommitmentClass,
    DeliveryContract,
    DeliveryOutcome,
    DeliveryPlanScope,
)


def _git(repository: Path, *arguments: str) -> str:
    return subprocess.run(  # noqa: S603 - fixed executable and fixture-owned arguments.
        ("git", "-C", str(repository), *arguments),  # noqa: S607
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _canonical(value: object) -> bytes:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    elif isinstance(value, (list, tuple)):
        value = [item.model_dump(mode="json") if isinstance(item, BaseModel) else item for item in value]
    return f"{json.dumps(value, sort_keys=True, separators=(',', ':'))}\n".encode()


def _outcome(identity: str, title: str, promise: str, dependencies: tuple[str, ...] = ()) -> DeliveryOutcome:
    return DeliveryOutcome(
        outcome_id=identity,
        title=title,
        promise=promise,
        acceptance=(f"Observe {title}.",),
        commitment_ids=("COM-001",),
        dependency_ids=dependencies,
    )


def _contract(change_id: str, title: str, outcomes: tuple[DeliveryOutcome, ...]) -> DeliveryContract:
    intent = f"intent for {change_id}\n".encode()
    design = f"design for {change_id}\n".encode()
    return DeliveryContract(
        change_id=change_id,
        title=title,
        commitments=(
            DeliveryCommitment(
                commitment_id="COM-001",
                commitment_class=DeliveryCommitmentClass.AGREED_PATH,
                provenance="assembled E2E fixture",
                statement="Keep Delivery state observable and bounded.",
            ),
        ),
        outcomes=outcomes,
        plan_scopes=tuple(
            DeliveryPlanScope(scope_id=f"SCOPE-{index:03}", outcome_id=outcome.outcome_id)
            for index, outcome in enumerate(outcomes, start=1)
        ),
        source_bindings=(
            {"source_name": "intent.md", "sha256": hashlib.sha256(intent).hexdigest()},
            {"source_name": "design.md", "sha256": hashlib.sha256(design).hexdigest()},
        ),
    )


def _task(outcome_id: str, index: int) -> DeliveryTaskDefinition:
    return DeliveryTaskDefinition(
        task_id=f"TASK-{index:03}",
        outcome_id=outcome_id,
        plan_scope_id=f"SCOPE-{index:03}",
        title=f"Build {outcome_id}",
        result=f"Reviewed result for {outcome_id}.",
        commitment_ids=("COM-001",),
        dependency_ids=(),
        required_outputs=("Reviewed implementation",),
        maintained_surfaces=("serve/cockpit/web",),
        constraints=("Preserve bounded Delivery state.",),
        exclusions=("No orchestration internals.",),
        acceptance_observations=(f"{outcome_id} is observable.",),
        proof_boundaries=("assembled Cockpit",),
    )


def _result(contract: DeliveryContract, task: DeliveryTaskDefinition, head: str) -> DeliveryTaskResult:
    return DeliveryTaskResult(
        result_id=f"result-{task.task_id.lower()}",
        change_id=contract.change_id,
        authority_digest=hashlib.sha256(_canonical(contract)).hexdigest(),
        task_id=task.task_id,
        task_digest=task.digest,
        completed_commit=head,
    )


def _current_bindings(contract: DeliveryContract, head: str) -> tuple[OutcomeAuthorityBinding, ...]:
    build_task = _task("OUT-002", 2)
    assembly_task = _task("OUT-003", 3)
    completed_task = _task("OUT-005", 5)
    return (
        OutcomeAuthorityBinding(
            outcome_id="OUT-001",
            plan_scope_id="SCOPE-001",
            stage=DeliveryStage.PLANNING,
            block=DeliveryBlock(
                block_id="block-release-mode",
                reason="Release mode needs a decision",
                unblock_condition="Select one bounded mode",
                expected_evidence=("Selected release mode",),
                locators=("request:release-mode",),
                request_id="request-release-mode",
            ),
            requests=(
                DeliveryRequest(
                    request_id="request-release-mode",
                    kind=DeliveryRequestKind.DECISION,
                    outcome_id="OUT-001",
                    summary="Choose release mode",
                    options=(
                        DeliveryRequestOption(option_id="safe", label="Safe rollout"),
                        DeliveryRequestOption(option_id="fast", label="Fast rollout"),
                    ),
                ),
            ),
        ),
        OutcomeAuthorityBinding(
            outcome_id="OUT-002",
            plan_scope_id="SCOPE-002",
            stage=DeliveryStage.IMPLEMENTATION,
            tasks=(build_task,),
        ),
        OutcomeAuthorityBinding(
            outcome_id="OUT-003",
            plan_scope_id="SCOPE-003",
            stage=DeliveryStage.ASSEMBLY,
            assembly_required=True,
            tasks=(assembly_task,),
            results=(_result(contract, assembly_task, head),),
        ),
        OutcomeAuthorityBinding(
            outcome_id="OUT-004",
            plan_scope_id="SCOPE-004",
            stage=DeliveryStage.DESIGN,
            return_context=DeliveryReturnContext(
                target=DeliveryStage.DESIGN,
                reason="The admitted release-note authority changed.",
                locators=("request:release-notes-authority",),
                source_boundary="design:release-notes-v2",
            ),
        ),
        OutcomeAuthorityBinding(
            outcome_id="OUT-005",
            plan_scope_id="SCOPE-005",
            stage=DeliveryStage.COMPLETED,
            tasks=(completed_task,),
            results=(_result(contract, completed_task, head),),
        ),
        OutcomeAuthorityBinding(
            outcome_id="OUT-006",
            plan_scope_id="SCOPE-006",
            stage=DeliveryStage.PLANNING,
        ),
    )


def _write_current_delivery(target_root: Path, head: str) -> None:
    outcomes = (
        _outcome("OUT-001", "Choose release mode", "Resolve the bounded release decision."),
        _outcome("OUT-002", "Build operator controls", "Ship exact Delivery controls."),
        _outcome("OUT-003", "Assemble release", "Compose reviewed Delivery outputs."),
        _outcome("OUT-004", "Plan release notes", "Prepare bounded release notes."),
        _outcome("OUT-005", "Publish operator guide", "Publish the reviewed operator guide."),
        _outcome("OUT-006", "Verify dependent rollout", "Wait for operator controls.", ("OUT-002",)),
    )
    contract = _contract("work-e2e", "Work portfolio E2E", outcomes)
    frontier = DeliveryFrontier(
        bindings=_current_bindings(contract, head),
    )
    change_root = target_root / "delivery/changes" / contract.change_id
    change_root.mkdir(parents=True, exist_ok=True)
    (change_root / "contract.json").write_bytes(_canonical(contract))
    (change_root / "frontier.json").write_bytes(_canonical(frontier))


def _write_repair_delivery(target_root: Path, head: str) -> None:
    contract = _contract(
        "repair-e2e",
        "Repair release",
        (_outcome("OUT-001", "Verify repaired release", "Publish the reviewed repair."),),
    )
    task = _task("OUT-001", 1)
    frontier = DeliveryFrontier(
        bindings=(
            OutcomeAuthorityBinding(
                outcome_id="OUT-001",
                plan_scope_id="SCOPE-001",
                stage=DeliveryStage.COMPLETED,
                tasks=(task,),
                results=(_result(contract, task, head),),
            ),
        ),
        integration_attention=DeliveryIntegrationAttention(
            attention_id=hashlib.sha256(b"repair-e2e-integration-attention").hexdigest(),
            code=DeliveryIntegrationAttentionCode.MERGE_CONFLICT,
            change_id=contract.change_id,
            change_head=head,
            target_head=head,
            integration_target="main",
            diagnostics=(
                f"100644 {'1' * 40} 1\tproduct.txt",
                f"100644 {'2' * 40} 2\tproduct.txt",
                f"100644 {'3' * 40} 3\tproduct.txt",
                "CONFLICT (content): Merge conflict in product.txt",
            ),
            retry_condition="Admit the independently reviewed repair.",
        ),
        integration_repair_claim=DeliveryActiveClaim(
            attempt_id="repair-attempt-work-e2e",
            claim_id="repair-claim-work-e2e",
            owner_id="repair-owner-work-e2e",
            process_id="repair-process-work-e2e",
            started_at="2026-08-04T12:05:00Z",
            worker_role=DeliveryWorkerRole.INTEGRATION_REPAIRER,
        ),
    )
    change_root = target_root / "delivery/changes" / contract.change_id
    change_root.mkdir(parents=True, exist_ok=True)
    (change_root / "contract.json").write_bytes(_canonical(contract))
    (change_root / "frontier.json").write_bytes(_canonical(frontier))


def _completion_content(change_id: str, title: str, reviewed_head: str) -> dict[str, bytes]:
    intent = f"intent for completed {change_id}\n".encode()
    design = f"design for completed {change_id}\n".encode()
    contract = _contract(change_id, title, (_outcome("OUT-001", f"Ship {title}", "Publish verified work."),))
    authority = _canonical(contract)
    task = _task("OUT-001", 1)
    result = _result(contract, task, reviewed_head)
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
    runtime = _canonical(frontier)
    results = _canonical((result,))
    package = DesignPackageManifest.from_content(change_id, intent, design, authority)
    completion = CompletionPackageManifest(
        change_id=change_id,
        package_id=hashlib.sha256(package.canonical_bytes()).hexdigest(),
        authority_digest=hashlib.sha256(authority).hexdigest(),
        runtime_sha256=hashlib.sha256(runtime).hexdigest(),
        result_history_sha256=hashlib.sha256(results).hexdigest(),
        reviewed_change_head=reviewed_head,
        integration_target="main",
        completion_path=f".owlbear/completed/{change_id}",
    )
    return {
        "authority.json": authority,
        "completion.json": completion.canonical_bytes(),
        "design.md": design,
        "intent.md": intent,
        "manifest.json": package.canonical_bytes(),
        "results.json": results,
        "runtime.json": runtime,
    }


def _publish_completion(repository: Path, change_id: str, title: str, reviewed_head: str) -> str:
    package_root = repository / ".owlbear/completed" / change_id
    package_root.mkdir(parents=True)
    for name, content in _completion_content(change_id, title, reviewed_head).items():
        (package_root / name).write_bytes(content)
    _git(repository, "add", str(package_root.relative_to(repository)))
    _git(repository, "commit", "-m", f"complete {change_id}")
    return _git(repository, "rev-parse", "HEAD")


def _seed_repository(repository: Path) -> str:
    repository.mkdir(exist_ok=True)
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.name", "Work Portfolio E2E")
    _git(repository, "config", "user.email", "work-portfolio@example.invalid")
    (repository / "product.txt").write_text("baseline\n", encoding="utf-8")
    _git(repository, "add", "product.txt")
    _git(repository, "commit", "-m", "baseline")
    baseline = _git(repository, "rev-parse", "HEAD")
    first = _publish_completion(repository, "completed-alpha", "Alpha delivery", baseline)
    return _publish_completion(repository, "completed-beta", "Beta search", first)


def _write_config(workspace: Path) -> None:
    config = DeliveryStartupConfig(schema_version=1, integration_target="main")
    path = workspace / ".owlbear/delivery/config.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(config.model_dump_json(by_alias=True), encoding="utf-8")


def seed_delivery(workspace: Path) -> None:
    """Seed canonical current and completed Delivery data below the real application."""
    repository = workspace
    target_root = workspace / ".owlbear/target"
    worktrees = workspace / ".owlbear/worktrees"
    head = _seed_repository(repository)
    _write_current_delivery(target_root, head)
    _write_repair_delivery(target_root, head)
    coordinator = PortfolioCoordinator(target_root, capacity=2)
    workspace_manager = ChangeWorkspaceManager(repository, worktrees, coordinator, "main")
    workspace_manager.create("work-e2e")
    workspace_manager.create("repair-e2e")
    _write_config(workspace)


def main() -> None:
    """Parse the fixture root and seed Delivery state."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    arguments = parser.parse_args()
    seed_delivery(arguments.workspace.resolve())


if __name__ == "__main__":
    main()
