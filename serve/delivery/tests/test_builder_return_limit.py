"""N12-B: a Builder return limit routes to a preserving Design revision (I5)."""

from __future__ import annotations

import hashlib
from pathlib import Path
from unittest.mock import patch

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
    DeliveryAdmissionRequest,
    DeliveryBuilderInvocationSettlement,
    DeliveryChangeIntent,
    DeliveryChangeIntentKind,
    DeliveryFrontier,
    DeliveryRuntimeConflictError,
    DeliveryStage,
    DeliveryStatePublisher,
    DeliveryTaskDefinition,
    DeliveryWorkerRole,
    PortfolioApplication,
    ReturnDelivery,
)
from owlbear_delivery.delivery_admission import DeliveryRevisionError
from owlbear_delivery.delivery_application_loader import (
    DeliveryStartupConfig,
    close_delivery_application,
    load_delivery_application,
)
from owlbear_delivery.delivery_runtime import _model_content
from owlbear_delivery.recovery import RetryLedger
from owlbear_delivery.work_items import WorkItemActionKind

_CHANGE_ID = "return-limit"


def _published_planning_return(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, limited: bool, pause: bool = True
) -> tuple[PortfolioApplication, DeliveryStartupConfig, Path, object, str]:
    """Publish one Change, return its Builder to Planning with committed and dirty work, then Pause it.

    ``limited`` lowers the return bound to one, so this single return reaches the return limit.
    """
    if limited:
        monkeypatch.setattr(RetryLedger, "builder_planning_returns", 1)
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
    application._publish_delivery_state(_CHANGE_ID, runtime, "return-limit-first-state")  # noqa: SLF001
    task = DeliveryTaskDefinition(
        task_id="TASK-001",
        outcome_id="OUT-001",
        plan_scope_id=admitted.frontier.bindings[0].plan_scope_id,
        title="Implement the launch",
        result="Make the launch observable.",
        commitment_ids=("COM-001",),
        dependency_ids=(),
        required_outputs=("Launch implementation",),
        maintained_surfaces=("serve/delivery",),
        constraints=("Use the reviewed branch.",),
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
    application._publish_delivery_state(_CHANGE_ID, runtime, "return-limit-seeded-state")  # noqa: SLF001
    builder = application.acquire_frontier_work().launch_packages[0]
    worktree = builder.worktree_path
    (worktree / "committed.txt").write_text("committed Builder bytes\n", encoding="utf-8")
    _git(worktree, "add", "committed.txt")
    _git(worktree, "commit", "-m", "Builder work")
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
            request=ReturnDelivery(
                action="return",
                outcome_id="OUT-001",
                claim_id=builder.claim.claim_id,
                target=DeliveryStage.PLANNING,
                reason="The task needs a clarified plan.",
                locators=("TASK-001",),
                preserved_commit=branch_head,
                attempt_id=builder.claim.attempt_id,
            ),
        ),
        host_id=builder.claim.owner_id,
        session_id=builder.claim.process_id,
    )
    if not pause:
        return application, config, repository, builder, branch_head
    application.set_change_intent(
        DeliveryChangeIntent(
            change_id=_CHANGE_ID,
            kind=DeliveryChangeIntentKind.DEFER,
            expected_frontier_digest=hashlib.sha256(runtime.frontier_bytes()).hexdigest(),
            reason="Revise requirements",
        )
    )
    assert runtime.change_deferral() is not None
    return application, config, repository, builder, branch_head


def _revise(application: PortfolioApplication) -> object:
    package_id = application.read_design_session(_CHANGE_ID).package_id
    return application.revise_design_session(
        _CHANGE_ID, package_id, _revision_sources("AC-002: Revised."), b"# Architecture\n"
    )


def _custody(application: PortfolioApplication, repository: Path, worktree: Path) -> tuple[object, ...]:
    return (
        _git(worktree, "ls-files", "--stage"),
        _git(repository, "for-each-ref", "refs/owlbear"),
        application._coordinator.show(_CHANGE_ID),  # noqa: SLF001
        application._runtimes[_CHANGE_ID].frontier_bytes(),  # noqa: SLF001
    )


def test_return_limit_card_routes_to_a_design_revision(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    application, _config, _repository_root, _builder, _branch_head = _published_planning_return(
        tmp_path, monkeypatch, limited=True, pause=False
    )
    binding = application._runtimes[_CHANGE_ID].show_binding("OUT-001")  # noqa: SLF001
    assert binding.block is not None
    assert binding.block.block_id.startswith("builder-return-limit-")

    card = application.show_work_item_view(_CHANGE_ID, "outcome:OUT-001").card

    assert card.action.kind is WorkItemActionKind.RESUME_DESIGN
    assert (card.action.label, card.action.command) == ("Revise Design", f"/design {_CHANGE_ID}")
    assert card.readiness is not None
    assert card.readiness.reason_code == "design-attention"
    assert card.readiness.executable is False
    assert card.readiness.prompt is not None
    assert "Pause the Change" in card.readiness.prompt
    assert application.acquire_frontier_work().launch_packages == ()
    close_delivery_application(application)


@pytest.mark.parametrize("boundary", [None, "after-capture", "before-release"])
def test_return_limit_revision_preserves_builder_work_across_restart(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, boundary: str | None
) -> None:
    application, config, repository, builder, branch_head = _published_planning_return(
        tmp_path, monkeypatch, limited=True
    )
    worktree, attempt_id = builder.worktree_path, builder.claim.attempt_id
    retained = application._runtimes[_CHANGE_ID].show_binding("OUT-001")  # noqa: SLF001
    if boundary is not None:
        with _design_return_crash(application, boundary), pytest.raises(_Crash):
            _revise(application)
        close_delivery_application(application)
        application = load_delivery_application(config, workspace_root=repository)
        health = application.delivery_health()
        assert health.status.value == "healthy", health

    _revise(application)

    runtime = application._runtimes[_CHANGE_ID]  # noqa: SLF001
    coordination = application._coordinator.show(_CHANGE_ID)  # noqa: SLF001
    released = runtime.show_binding("OUT-001")
    assert released == retained.model_copy(update={"builder_handoff_context": None, "block": None})
    assert released.stage is DeliveryStage.PLANNING
    assert released.return_context is not None
    assert released.return_context.preserved_commit == branch_head
    assert (coordination.writer, coordination.builder_handoff) == (None, None)
    assert runtime.pending_state_publication() is None
    assert _git(worktree, "rev-parse", "HEAD") == builder.last_reviewed_commit
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
    runtime = application._runtimes[_CHANGE_ID]  # noqa: SLF001

    activated = application.admit_change(
        DeliveryAdmissionRequest(
            change_id=_CHANGE_ID,
            expected_package_id=_authored_package_id(application, _CHANGE_ID),
            active_claim_ids=(),
            expected_frontier_digest=hashlib.sha256(runtime.frontier_bytes()).hexdigest(),
            expected_design_package_snapshot_receipt_id=coordination.design_package_snapshot.receipt_id,
        )
    )

    replanned = activated.frontier.bindings[0]
    assert replanned.stage is DeliveryStage.PLANNING
    assert replanned.return_context is not None
    assert replanned.return_context.preserved_commit == branch_head
    launches = application.acquire_frontier_work().launch_packages
    assert [(launch.outcome_id, launch.claim.worker_role) for launch in launches] == [
        ("OUT-001", DeliveryWorkerRole.PLANNER)
    ]
    close_delivery_application(application)


def test_return_limit_refuses_clearance_and_the_attempt_grant(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    application, _config, _repository_root, _builder, _branch_head = _published_planning_return(
        tmp_path, monkeypatch, limited=True, pause=False
    )
    runtime = application._runtimes[_CHANGE_ID]  # noqa: SLF001
    block = runtime.show_binding("OUT-001").block
    assert block is not None
    before = runtime.frontier_bytes()

    with pytest.raises(DeliveryRuntimeConflictError, match="exact exhausted Builder block"):
        runtime.grant_builder_attempt("OUT-001", block.block_id)
    with pytest.raises(DeliveryRuntimeConflictError):
        application.clear_block(_CHANGE_ID, "OUT-001", block.block_id, "Operator verified.", ("TASK-001",))

    assert runtime.frontier_bytes() == before
    close_delivery_application(application)


def test_return_limit_revision_waits_for_its_release_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    application, config, repository, _builder, branch_head = _published_planning_return(
        tmp_path, monkeypatch, limited=True
    )
    retained = application._runtimes[_CHANGE_ID].show_binding("OUT-001")  # noqa: SLF001
    before = application.read_design_session(_CHANGE_ID).package_id
    unavailable = patch.object(DeliveryStatePublisher, "publish", side_effect=RuntimeError("provider unavailable"))
    with unavailable, pytest.raises(DeliveryRevisionError, match="publication-pending"):
        _revise(application)
    released = retained.model_copy(update={"builder_handoff_context": None, "block": None})
    assert application._runtimes[_CHANGE_ID].show_binding("OUT-001") == released  # noqa: SLF001
    close_delivery_application(application)
    with unavailable:
        application = load_delivery_application(config, workspace_root=repository)
        assert application._runtimes[_CHANGE_ID].show_binding("OUT-001") == released  # noqa: SLF001
        with pytest.raises(DeliveryRevisionError, match="publication-pending"):
            _revise(application)
    assert application.read_design_session(_CHANGE_ID).package_id == before

    _revise(application)

    runtime = application._runtimes[_CHANGE_ID]  # noqa: SLF001
    assert runtime.pending_state_publication() is None
    assert runtime.show_binding("OUT-001").return_context.preserved_commit == branch_head
    close_delivery_application(application)


def test_planning_return_below_the_limit_still_refuses_revision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    application, _config, repository, builder, _branch_head = _published_planning_return(
        tmp_path, monkeypatch, limited=False
    )
    assert application._runtimes[_CHANGE_ID].show_binding("OUT-001").block is None  # noqa: SLF001
    before = _custody(application, repository, builder.worktree_path)

    with pytest.raises(DeliveryRevisionError, match="custody-retained"):
        _revise(application)

    assert _custody(application, repository, builder.worktree_path) == before
    close_delivery_application(application)


@pytest.mark.parametrize("tamper", ["forged-clearance", "legacy-block-id"])
def test_default_loader_refuses_a_return_limit_block_that_differs_from_its_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, tamper: str
) -> None:
    application, config, repository, _builder, _branch_head = _published_planning_return(
        tmp_path, monkeypatch, limited=True, pause=False
    )
    close_delivery_application(application)
    frontier_path = repository / ".owlbear/delivery/runtime/changes" / _CHANGE_ID / "frontier.json"
    frontier = DeliveryFrontier.model_validate_json(frontier_path.read_bytes(), strict=True)
    binding = frontier.bindings[0]
    assert binding.block is not None
    block = (
        binding.block.model_copy(update={"resolution_note": "Forged clearance.", "resolution_locators": ("TASK-001",)})
        if tamper == "forged-clearance"
        else binding.block.model_copy(
            update={"block_id": binding.block.block_id.replace("builder-return-limit-", "builder-planning-route-")}
        )
    )
    frontier_path.write_bytes(
        _model_content(frontier.model_copy(update={"bindings": (binding.model_copy(update={"block": block}),)}))
    )
    before = frontier_path.read_bytes()

    health = load_delivery_application(config, workspace_root=repository).delivery_health()

    assert health.status.value == "attention"
    assert [item.change_id for item in health.diagnostics] == [_CHANGE_ID]
    assert frontier_path.read_bytes() == before


def test_return_limit_replay_refuses_an_index_restaged_after_capture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    application, config, repository, builder, _branch_head = _published_planning_return(
        tmp_path, monkeypatch, limited=True
    )
    worktree = builder.worktree_path
    with _design_return_crash(application, "after-capture"), pytest.raises(_Crash):
        _revise(application)
    (worktree / "staged.txt").write_text("restaged bytes\n", encoding="utf-8")
    _git(worktree, "add", "staged.txt")
    (worktree / "staged.txt").write_text("unstaged Builder bytes\n", encoding="utf-8")
    close_delivery_application(application)
    application = load_delivery_application(config, workspace_root=repository)
    before = _custody(application, repository, worktree)

    with pytest.raises(DeliveryRevisionError, match="design-return-workspace-changed"):
        _revise(application)

    assert _custody(application, repository, worktree) == before
    assert _git(worktree, "show", ":staged.txt") == "restaged bytes"
    close_delivery_application(application)
