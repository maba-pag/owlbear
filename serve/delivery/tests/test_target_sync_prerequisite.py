# ruff: noqa: SLF001
"""N13: a Builder's required target commit routes to an engine sync, never to a person."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError
from serve.delivery.tests.test_portfolio_application import (
    _advance_remote_target,
    _builder_retry_handoff_setup,
    _change_intent,
    _commit_reviewed_head,
    _continuation_request,
    _git,
    _portfolio,
    _reopen_portfolio,
    _seed_two_task_builder,
    _workspace_content_snapshot,
)

from owlbear_delivery import (
    BlockDelivery,
    DeliveryBuilderInvocationSettlement,
    DeliveryChangeIntentKind,
    DeliveryRequest,
    DeliveryRequestKind,
    DeliveryStage,
)
from owlbear_delivery.application_support import _checkpoint_error_detail
from owlbear_delivery.change_workspace import ChangeTargetSyncConflictError, ChangeTargetSyncStaleError
from owlbear_delivery.runtime_models import required_target_commit
from owlbear_delivery.work_items import WorkItemActionKind

_INCIDENT_CONFLICT_PATHS = (
    "serve/memory-mcp/README.md",
    "serve/memory-mcp/src/owlbear_memory_mcp/tools.py",
    "serve/memory-mcp/tests/test_server.py",
    "serve/memory/README.md",
    "serve/memory/src/owlbear_memory/__init__.py",
    "serve/memory/src/owlbear_memory/engine.py",
)


def test_bounded_conflict_detail_names_whole_paths_and_counts_the_rest() -> None:
    """A six-path conflict was cut mid-path by the 240-character retained detail bound."""
    error = ChangeTargetSyncConflictError("change-a", "operation-a", "a" * 40, _INCIDENT_CONFLICT_PATHS)
    detail = _checkpoint_error_detail(str(error), "fallback")

    assert detail == str(error)
    listed = detail.removeprefix("target synchronization requires conflict resolution: ").split(" (+")[0]
    shown = listed.split(", ")
    assert shown == list(_INCIDENT_CONFLICT_PATHS[: len(shown)])
    assert f"(+{6 - len(shown)} more of 6; full list in publication.target_sync_conflict)" in detail
    assert error.conflict_paths == _INCIDENT_CONFLICT_PATHS


def test_short_conflict_detail_lists_every_path_unchanged() -> None:
    error = ChangeTargetSyncConflictError("change-a", "operation-a", "a" * 40, ("a.txt", "b.txt"))

    assert str(error) == "target synchronization requires conflict resolution: a.txt, b.txt"


def _target_block(launch, branch_head: str, required: str) -> BlockDelivery:
    return BlockDelivery(
        action="block",
        outcome_id=launch.outcome_id,
        claim_id=launch.claim.claim_id,
        block_id="BLOCK-TARGET-SYNC",
        reason="The task needs a target commit the Change branch does not contain.",
        unblock_condition="The Change branch contains the required target commit.",
        expected_evidence=("A target-sync receipt whose merged head contains the commit.",),
        locators=(f"target-commit:{required}",),
        resume_commit=branch_head,
    )


def _settlement(launch, request: BlockDelivery) -> DeliveryBuilderInvocationSettlement:
    return DeliveryBuilderInvocationSettlement(
        change_id=launch.change_id,
        outcome_id=launch.outcome_id,
        claim_id=launch.claim.claim_id,
        attempt_id=launch.claim.attempt_id,
        task_id=launch.task_id,
        expected_last_reviewed_commit=launch.last_reviewed_commit,
        disposition="normal-return",
        request=request,
    )


def _with_remote_target(application, tmp_path: Path, *, fetch: bool = True) -> str:
    repository = application._workspace_manager.repository
    remote = tmp_path / "remote.git"
    subprocess.run(("git", "init", "--bare", "-b", "main", str(remote)), check=True, capture_output=True)  # noqa: S603, S607
    _git(repository, "remote", "add", "origin", str(remote))
    _git(repository, "push", "origin", "refs/heads/main:refs/heads/main")
    target_head = _advance_remote_target(tmp_path, remote)
    if fetch:
        _git(repository, "fetch", "origin")
    return target_head


def _blocked_for_target(tmp_path: Path, *, fetch: bool = True):
    now = ["2026-08-04T00:00:00Z"]
    application, runtime, coordinator, _state_root, launch, branch_head, before_workspace, _retry = (
        _builder_retry_handoff_setup(tmp_path, now)
    )
    target_head = _with_remote_target(application, tmp_path, fetch=fetch)
    settled = application.settle_worker_invocation(
        _settlement(launch, _target_block(launch, branch_head, target_head)),
        host_id=launch.claim.owner_id,
        session_id=launch.claim.process_id,
    )
    return application, runtime, coordinator, launch, branch_head, before_workspace, target_head, settled


def test_target_sync_block_needs_no_request_and_rejects_one() -> None:
    commit = "1" * 40
    request = DeliveryRequest(
        request_id="REQ-1", kind=DeliveryRequestKind.ACTION, outcome_id="OUT-001", summary="Sync it.", options=()
    )
    with pytest.raises(ValidationError, match="engine prerequisite"):
        BlockDelivery(
            action="block",
            outcome_id="OUT-001",
            claim_id="claim",
            block_id="BLOCK",
            reason="reason",
            unblock_condition="condition",
            expected_evidence=("evidence",),
            locators=(f"target-commit:{commit}",),
            request=request,
        )
    requestless = BlockDelivery(
        action="block",
        outcome_id="OUT-001",
        claim_id="claim",
        block_id="BLOCK",
        reason="reason",
        unblock_condition="condition",
        expected_evidence=("evidence",),
        locators=("locator",),
        resume_commit=commit,
    )
    with pytest.raises(ValidationError, match="target-commit locator"):
        DeliveryBuilderInvocationSettlement(
            change_id="change-a",
            outcome_id="OUT-001",
            claim_id="claim",
            attempt_id="attempt",
            task_id="TASK-001",
            expected_last_reviewed_commit=commit,
            disposition="normal-return",
            request=requestless,
        )


def test_builder_target_sync_block_offers_the_engine_sync_instead_of_a_request(tmp_path: Path) -> None:
    application, _runtime, coordinator, _launch, _head, _before, target_head, settled = _blocked_for_target(tmp_path)

    assert settled.requests == ()
    assert settled.block is not None
    assert settled.block.request_id is None
    assert required_target_commit(settled.block.locators) == target_head
    assert coordinator.show("change-a").writer.kind == "handoff"
    view = application.get_change("change-a")
    card = view.detail.card
    assert card.needs.value == "none"
    assert card.action.kind is WorkItemActionKind.SYNC_TARGET
    readiness = view.readiness
    assert readiness.operation is WorkItemActionKind.SYNC_TARGET
    assert readiness.executable
    assert readiness.next_actor.value == "agent"
    assert readiness.basis.target_head == target_head
    assert readiness.basis.candidate_head == coordinator.show("change-a").last_reviewed_commit


def test_sync_preserves_builder_work_clears_the_block_and_relaunches_the_task(tmp_path: Path) -> None:
    application, runtime, coordinator, launch, branch_head, _before, target_head, _settled = _blocked_for_target(
        tmp_path
    )
    worktree = launch.worktree_path
    attempt = launch.claim.attempt_id

    receipt = application.sync_change_with_target("change-a", target_head, "sync-n13")

    coordination = coordinator.show("change-a")
    assert coordination.writer is None
    assert coordination.builder_handoff is None
    assert coordination.dirty_worktree_quarantine is None
    assert coordination.last_reviewed_commit == receipt.merged_head
    assert _git(worktree, "status", "--porcelain=v1", "--untracked-files=all") == ""
    assert _git(worktree, "merge-base", "--is-ancestor", target_head, "HEAD") == ""
    assert _git(worktree, "rev-parse", f"refs/owlbear/attempts/change-a/{attempt}") == branch_head
    quarantine = f"refs/owlbear/quarantine/change-a/{attempt}"
    assert _git(worktree, "show", f"{quarantine}:product.txt") == "unstaged Builder work"
    assert _git(worktree, "show", f"{quarantine}:untracked.txt") == "untracked Builder work"
    index = f"refs/owlbear/quarantine-index/change-a/{attempt}"
    assert _git(worktree, "show", f"{index}:product.txt") == "staged Builder work"

    binding = runtime.show_binding("OUT-001")
    assert binding.builder_handoff_context is None
    assert binding.block is not None
    assert binding.block.resolved
    assert f"target-sync:{receipt.receipt_id}" in binding.block.resolution_locators
    assert binding.return_context is not None
    assert binding.return_context.preserved_commit == branch_head
    assert f"ref:{quarantine}" in binding.return_context.locators

    # The fixture has no branch publisher, so the continuation would first publish a checkpoint.
    acquired = application.acquire_frontier_work()
    assert acquired.failures == ()
    (relaunched,) = (item for item in acquired.launch_packages if item.change_id == "change-a")
    assert relaunched.task_id == launch.task_id
    assert relaunched.source_head == receipt.merged_head
    context = application.show_build_context(
        "change-a", "OUT-001", relaunched.claim.attempt_id, relaunched.claim.claim_id
    )
    assert context.return_context == binding.return_context


def test_continuation_releases_the_handoff_before_it_selects_the_sync(tmp_path: Path) -> None:
    application, _runtime, coordinator, launch, branch_head, _before, _target, _settled = _blocked_for_target(tmp_path)

    first = application.acquire_change_action(_continuation_request(application, "change-a"))

    assert first.launch is None
    assert coordinator.show("change-a").builder_handoff is None
    attempt = launch.claim.attempt_id
    assert _git(launch.worktree_path, "rev-parse", f"refs/owlbear/attempts/change-a/{attempt}") == branch_head
    assert application.get_change("change-a").readiness.operation is WorkItemActionKind.SYNC_TARGET


def test_released_target_sync_state_reloads(tmp_path: Path) -> None:
    application, runtime, _coordinator, _launch, _head, _before, _target, _settled = _blocked_for_target(tmp_path)
    application.acquire_change_action(_continuation_request(application, "change-a"))
    released = runtime.frontier_bytes()

    reopened, _coordinator2, _manager = _reopen_portfolio(
        tmp_path, application._target_root, {"change-a": runtime, "change-b": application._runtimes["change-b"]}
    )

    assert reopened._runtimes["change-a"].frontier_bytes() == released
    assert reopened.get_change("change-a").readiness.operation is WorkItemActionKind.SYNC_TARGET


def test_commit_the_target_lacks_stops_for_the_user(tmp_path: Path) -> None:
    now = ["2026-08-04T00:00:00Z"]
    application, _runtime, _coordinator, _state_root, launch, branch_head, _before, _retry = (
        _builder_retry_handoff_setup(tmp_path, now)
    )
    _with_remote_target(application, tmp_path)
    repository = application._workspace_manager.repository
    _git(repository, "checkout", "-q", "-b", "side", "main")
    (repository / "side.txt").write_text("side\n", encoding="utf-8")
    _git(repository, "add", "side.txt")
    _git(repository, "commit", "-q", "-m", "side commit")
    side = _git(repository, "rev-parse", "HEAD")
    _git(repository, "checkout", "-q", "main")
    application.settle_worker_invocation(
        _settlement(launch, _target_block(launch, branch_head, side)),
        host_id=launch.claim.owner_id,
        session_id=launch.claim.process_id,
    )

    readiness = application.get_change("change-a").readiness

    assert readiness.reason_code == "target-commit-missing"
    assert readiness.status == "blocked"
    assert not readiness.executable
    assert readiness.next_actor.value == "you"


def test_continuation_clears_a_block_a_completed_sync_left_behind(tmp_path: Path) -> None:
    application, runtime, _coordinator, _launch, _head, _before, target_head, _settled = _blocked_for_target(tmp_path)
    with patch.object(type(application), "_clear_satisfied_target_sync_blocks", return_value=False):
        receipt = application.sync_change_with_target("change-a", target_head, "sync-n13")
    assert not runtime.show_binding("OUT-001").block.resolved

    application.acquire_change_action(_continuation_request(application, "change-a"))

    block = runtime.show_binding("OUT-001").block
    assert block.resolved
    assert f"target-sync:{receipt.receipt_id}" in block.resolution_locators


def test_target_sync_conflict_keeps_the_block_until_the_merge_is_resolved(tmp_path: Path) -> None:
    application, runtime, _coordinator, _launch, _head, _before, target_head, _settled = _blocked_for_target(tmp_path)
    conflict = ChangeTargetSyncConflictError("change-a", "sync-n13", target_head, ("product.txt",))
    with (
        patch.object(application._workspace_manager, "sync_with_target", side_effect=conflict),
        pytest.raises(ChangeTargetSyncConflictError),
    ):
        application.sync_change_with_target("change-a", target_head, "sync-n13")

    assert runtime.change_disposition() is not None
    assert not runtime.show_binding("OUT-001").block.resolved
    application.acquire_change_action(_continuation_request(application, "change-a"))
    assert not runtime.show_binding("OUT-001").block.resolved


def test_requested_pause_keeps_the_target_sync_handoff(tmp_path: Path) -> None:
    application, _runtime, coordinator, _launch, _head, _before, _target, _settled = _blocked_for_target(tmp_path)
    _change_intent(application, "change-a", DeliveryChangeIntentKind.DEFER, "Hold the Change")

    application.acquire_change_action(_continuation_request(application, "change-a"))

    assert coordinator.show("change-a").builder_handoff is not None


def test_current_target_merge_fetches_an_unfetched_commit_then_merges_it(tmp_path: Path) -> None:
    application, runtime, _coordinator, _launch, _head, _before, target_head, _settled = _blocked_for_target(
        tmp_path, fetch=False
    )
    assert application.get_change("change-a").readiness.operation is WorkItemActionKind.SYNC_TARGET

    with pytest.raises(ChangeTargetSyncStaleError):
        application.sync_change_with_current_target("change-a", "sync-first")
    receipt = application.sync_change_with_current_target("change-a", "sync-second")

    assert receipt.target_head == target_head
    assert runtime.show_binding("OUT-001").block.resolved


def _two_task_builder_with_remote(tmp_path: Path, *, competing: str | None):
    """Accept TASK-001 on a reviewed edit, push the base, move only the remote target, then launch TASK-002."""
    application, runtimes, coordinator, state_root = _portfolio(
        tmp_path, {"change-a": DeliveryStage.IMPLEMENTATION, "change-b": DeliveryStage.PLANNING}
    )
    _commit_reviewed_head(application, coordinator.show("change-a"), "product.txt", "Change implementation\n", "edit")
    repository = application._workspace_manager.repository
    remote = tmp_path / "remote.git"
    subprocess.run(("git", "init", "--bare", "-b", "main", str(remote)), check=True, capture_output=True)  # noqa: S603, S607
    _git(repository, "remote", "add", "origin", str(remote))
    _git(repository, "push", "origin", "refs/heads/main:refs/heads/main")
    stale = _git(repository, "rev-parse", "refs/remotes/origin/main")
    target = _advance_remote_target(tmp_path, remote, product=competing)
    _completed, _original, _first, builder = _seed_two_task_builder(application, runtimes, coordinator, state_root)
    return application, runtimes["change-a"], builder, stale, target


def _build_context(application, builder):
    return application.show_build_context(
        builder.change_id, builder.outcome_id, builder.claim.attempt_id, builder.claim.claim_id
    )


def test_target_overlap_between_tasks_routes_the_next_task_through_the_target_sync(tmp_path: Path) -> None:
    application, runtime, builder, stale, target = _two_task_builder_with_remote(
        tmp_path, competing="Competing target edit\n"
    )
    repository = application._workspace_manager.repository
    files, index, refs = _workspace_content_snapshot(builder.worktree_path)

    overlap = _build_context(application, builder).target_overlap
    worktree_before = _workspace_content_snapshot(builder.worktree_path)
    assert worktree_before[:2] == (files, index)
    assert [ref for ref in worktree_before[2] if "target-observation" not in ref] == list(refs)

    assert overlap is not None
    assert (overlap.status, overlap.target_head, overlap.conflict_paths) == ("conflict", target, ("product.txt",))
    assert overlap.reviewed_head == builder.last_reviewed_commit
    assert _git(repository, "rev-parse", "refs/remotes/origin/main") == stale
    assert application._workspace_manager.observed_target_head() == target
    assert _git(repository, "for-each-ref", "refs/owlbear/target-overlap/") == ""

    # The Builder follows its context: no edits, only the existing target-sync block.
    application.settle_worker_invocation(
        _settlement(builder, _target_block(builder, builder.source_head, overlap.target_head)),
        host_id=builder.claim.owner_id,
        session_id=builder.claim.process_id,
    )
    assert _workspace_content_snapshot(builder.worktree_path) == worktree_before
    application.acquire_change_action(_continuation_request(application, "change-a"))
    readiness = application.get_change("change-a").readiness
    assert readiness.operation is WorkItemActionKind.SYNC_TARGET
    assert readiness.basis.target_head == target

    with pytest.raises(ChangeTargetSyncConflictError) as raised:
        application.sync_change_with_current_target("change-a", "sync-overlap")

    assert raised.value.conflict_paths == ("product.txt",)
    assert not runtime.show_binding("OUT-001").block.resolved
    assert application.get_change("change-a").readiness.prompt.startswith("/resolve-target-conflict change-a ")


def test_target_overlap_reports_a_clean_merge_and_never_counts_unknown_as_clean(tmp_path: Path) -> None:
    application, _runtime, builder, _stale, target = _two_task_builder_with_remote(tmp_path, competing=None)

    clean = _build_context(application, builder).target_overlap
    assert (clean.status, clean.target_head, clean.conflict_paths) == ("clean", target, ())

    repository = application._workspace_manager.repository
    _git(repository, "remote", "set-url", "origin", str(tmp_path / "missing.git"))
    unknown = _build_context(application, builder).target_overlap
    assert (unknown.status, unknown.target_head, unknown.conflict_paths) == ("unknown", None, ())


def test_target_overlap_is_not_probed_after_finalization(tmp_path: Path) -> None:
    application, runtime, builder, _stale, _target = _two_task_builder_with_remote(
        tmp_path, competing="Competing target edit\n"
    )
    with (
        patch.object(type(runtime), "finalization", return_value=object()),
        patch.object(application._workspace_manager, "probe_target_overlap") as probe,
    ):
        context = _build_context(application, builder)

    assert context.target_overlap is None
    assert not probe.called
