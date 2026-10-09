"""N13: a target-sync release survives restarts at its capture and release boundaries (default loader)."""

from __future__ import annotations

from pathlib import Path

import pytest
from serve.delivery.tests.test_delivery_state import (
    _authored_package_id,
    _Crash,
    _design_return_crash,
    _git,
    _repository,
    _revision_sources,
)

from owlbear_delivery import (
    BlockDelivery,
    DeliveryAdmissionRequest,
    DeliveryBuilderInvocationSettlement,
    DeliveryFrontier,
    DeliveryStage,
    DeliveryTaskDefinition,
    DeliveryWorkerRole,
    PortfolioApplication,
)
from owlbear_delivery.delivery_application_loader import (
    DeliveryStartupConfig,
    close_delivery_application,
    load_delivery_application,
)
from owlbear_delivery.delivery_runtime import _model_content
from owlbear_delivery.work_items import WorkItemActionKind

_CHANGE_ID = "target-sync"


def _advance_target(tmp_path: Path, remote: Path) -> str:
    clone = tmp_path / "target-clone"
    _git(tmp_path, "clone", "-q", str(remote), str(clone))
    _git(clone, "config", "user.name", "Target")
    _git(clone, "config", "user.email", "target@example.invalid")
    (clone / "target.txt").write_text("target\n", encoding="utf-8")
    _git(clone, "add", "target.txt")
    _git(clone, "commit", "-q", "-m", "advance target")
    _git(clone, "push", "-q", "origin", "HEAD:refs/heads/main")
    return _git(clone, "rev-parse", "HEAD")


def _blocked_on_target(tmp_path: Path) -> tuple[PortfolioApplication, DeliveryStartupConfig, Path, object, str, str]:
    """Publish one Change whose Builder, holding committed and dirty work, needs a newer target commit."""
    repository, remote, _initial = _repository(tmp_path)
    _git(repository, "config", "url." + str(remote) + ".insteadOf", "https://github.com/example/project.git")
    _git(repository, "remote", "set-url", "origin", "https://github.com/example/project.git")
    config = DeliveryStartupConfig(
        schema_version=2,
        remote="origin",
        target_branch="main",
        github_repository="example/project",
        delivery_state_branch="owlbear/delivery-state",
    )
    application = load_delivery_application(config, workspace_root=repository)
    application.create_design_session(_CHANGE_ID, _revision_sources("AC-002: Retained."), b"# Architecture\n")
    admitted = application.admit_delivery_change(
        DeliveryAdmissionRequest(
            change_id=_CHANGE_ID,
            expected_package_id=_authored_package_id(application, _CHANGE_ID),
            active_claim_ids=(),
        )
    )
    runtime = application._runtimes[_CHANGE_ID]  # noqa: SLF001
    application._publish_delivery_state(_CHANGE_ID, runtime, "target-sync-first-state")  # noqa: SLF001
    task = DeliveryTaskDefinition(
        task_id="TASK-001",
        outcome_id="OUT-001",
        plan_scope_id=admitted.frontier.bindings[0].plan_scope_id,
        title="Implement on the newer target",
        result="Make the launch observable.",
        commitment_ids=("COM-001",),
        dependency_ids=(),
        required_outputs=("Launch implementation",),
        maintained_surfaces=("serve/delivery",),
        constraints=("The target commit must be an ancestor first.",),
        exclusions=("Do not rewrite target history.",),
        acceptance_observations=("The launch is observable.",),
        proof_boundaries=("DeliveryRuntime.transition",),
    )
    frontier = DeliveryFrontier.model_validate_json(runtime.frontier_bytes(), strict=True)
    seeded = frontier.model_copy(
        update={
            "bindings": (
                frontier.bindings[0].model_copy(update={"stage": DeliveryStage.IMPLEMENTATION, "tasks": (task,)}),
            ),
            "pending_checkpoint": None,
            "published_head": application._coordinator.show(_CHANGE_ID).last_reviewed_commit,  # noqa: SLF001
        }
    )
    runtime._replace_content(runtime.frontier_bytes(), _model_content(seeded))  # noqa: SLF001
    application._publish_delivery_state(_CHANGE_ID, runtime, "target-sync-seeded-state")  # noqa: SLF001
    target = _advance_target(tmp_path, remote)
    _git(repository, "fetch", "-q", "origin", "refs/heads/main:refs/remotes/origin/main")
    builder = application.acquire_frontier_work().launch_packages[0]
    worktree = builder.worktree_path
    (worktree / "committed.txt").write_text("committed Builder bytes\n", encoding="utf-8")
    _git(worktree, "add", "committed.txt")
    _git(worktree, "commit", "-q", "-m", "Builder work")
    branch_head = _git(worktree, "rev-parse", "HEAD")
    (worktree / "staged.txt").write_text("staged Builder bytes\n", encoding="utf-8")
    _git(worktree, "add", "staged.txt")
    (worktree / "staged.txt").write_text("unstaged Builder bytes\n", encoding="utf-8")
    (worktree / "untracked.txt").write_text("untracked Builder bytes\n", encoding="utf-8")
    application.settle_worker_invocation(
        DeliveryBuilderInvocationSettlement(
            change_id=_CHANGE_ID,
            outcome_id="OUT-001",
            claim_id=builder.claim.claim_id,
            attempt_id=builder.claim.attempt_id,
            task_id=builder.task_id,
            expected_last_reviewed_commit=builder.last_reviewed_commit,
            disposition="normal-return",
            request=BlockDelivery(
                action="block",
                outcome_id="OUT-001",
                claim_id=builder.claim.claim_id,
                block_id="BLOCK-TARGET",
                reason="The task needs the newer target commit.",
                unblock_condition="The Change contains the target commit.",
                expected_evidence=("A target-sync receipt.",),
                locators=(f"target-commit:{target}",),
                resume_commit=branch_head,
            ),
        ),
        host_id=builder.claim.owner_id,
        session_id=builder.claim.process_id,
    )
    return application, config, repository, builder, branch_head, target


@pytest.mark.parametrize("boundary", [None, "after-capture", "before-release"])
def test_target_sync_release_preserves_builder_work_across_restart(tmp_path: Path, boundary: str | None) -> None:
    application, config, repository, builder, branch_head, target = _blocked_on_target(tmp_path)
    worktree, attempt_id = builder.worktree_path, builder.claim.attempt_id
    close_delivery_application(application)
    application = load_delivery_application(config, workspace_root=repository)
    health = application.delivery_health()
    assert health.status.value == "healthy", health
    view = application.show_work_item_view(_CHANGE_ID, "outcome:OUT-001")
    assert view.card.action.kind is WorkItemActionKind.SYNC_TARGET
    if boundary is not None:
        with _design_return_crash(application, boundary), pytest.raises(_Crash):
            application.sync_change_with_target(_CHANGE_ID, target, "sync-target-n13")
        close_delivery_application(application)
        application = load_delivery_application(config, workspace_root=repository)
        health = application.delivery_health()
        assert health.status.value == "healthy", health

    receipt = application.sync_change_with_target(_CHANGE_ID, target, "sync-target-n13")

    runtime = application._runtimes[_CHANGE_ID]  # noqa: SLF001
    coordination = application._coordinator.show(_CHANGE_ID)  # noqa: SLF001
    binding = runtime.show_binding("OUT-001")
    assert (coordination.writer, coordination.builder_handoff) == (None, None)
    assert binding.block is not None
    assert binding.block.resolved
    assert binding.return_context.preserved_commit == branch_head
    assert _git(repository, "merge-base", "--is-ancestor", target, receipt.merged_head) == ""
    assert _git(worktree, "status", "--porcelain", "--untracked-files=all") == ""
    attempt, index, quarantine = (
        f"refs/owlbear/{kind}/{_CHANGE_ID}/{attempt_id}" for kind in ("attempts", "quarantine-index", "quarantine")
    )
    assert _git(repository, "rev-parse", attempt) == branch_head
    assert _git(repository, "show", f"{attempt}:committed.txt") == "committed Builder bytes"
    assert _git(repository, "show", f"{index}:staged.txt") == "staged Builder bytes"
    assert _git(repository, "show", f"{quarantine}:staged.txt") == "unstaged Builder bytes"
    assert _git(repository, "show", f"{quarantine}:untracked.txt") == "untracked Builder bytes"
    close_delivery_application(application)

    application = load_delivery_application(config, workspace_root=repository)
    health = application.delivery_health()
    assert health.status.value == "healthy", health
    launches = application.acquire_frontier_work().launch_packages
    assert [(launch.task_id, launch.claim.worker_role, launch.source_head) for launch in launches] == [
        ("TASK-001", DeliveryWorkerRole.BUILDER, receipt.merged_head)
    ]
    close_delivery_application(application)
