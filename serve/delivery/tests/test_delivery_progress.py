# ruff: noqa: SLF001
"""Assembled and exhaustive proof of the N09-A1 programme progress projection."""

from __future__ import annotations

import itertools
from datetime import UTC, datetime
from pathlib import Path
from typing import get_args
from unittest.mock import patch

import pytest
from serve.delivery.tests import test_portfolio_application as portfolio_fixtures
from serve.delivery.tests.test_portfolio_application import (
    _acquire_planning_claim,
    _awaiting_acceptance_fixture,
    _canonical,
    _continuation_request,
    _engine_action,
    _execute_engine,
    _exhaust_builder_retry_with_distinct_codes,
    _planning_decision_block,
    _policies,
    _portfolio,
    _task,
    _task_result,
    acceptance_budget_case,
    builder_transition_case,
)
from serve.delivery.tests.test_worker_stall import _HOST, _WINDOW, _iso, _issuer_path, _Probe, _real_now

from owlbear_delivery import (
    CompletedHistoryCatalog,
    DeliveryBlock,
    DeliveryChangeIntent,
    DeliveryChangeIntentKind,
    DeliveryFrontier,
    DeliveryStage,
    OutcomeAuthorityBinding,
    PortfolioApplication,
    PortfolioApplicationConfig,
    PortfolioApplicationDependencies,
    PortfolioApplicationHooks,
)
from owlbear_delivery.publication_provider import PublicationProviderError, PublicationProviderFailureCode
from owlbear_delivery.recovery import DeliveryWorkerExclusionRequiredError, RetryLedger
from owlbear_delivery.work_items import (
    DeliveryProgress,
    DeliveryReadiness,
    DeliveryReadinessBasis,
    DeliveryReadinessReason,
    WorkItemAction,
    WorkItemActionKind,
    WorkItemActivity,
    WorkItemActivityState,
    WorkItemCardView,
    WorkItemNeed,
    WorkItemNextActor,
    WorkItemProgress,
    WorkItemProgressKind,
    WorkItemPublicationPhase,
    WorkItemScope,
    WorkItemStage,
    derive_delivery_progress,
)

_RESERVED = frozenset({"preparing", "working", "checking", "repairing", "needs-sign-in"})


def _progress_portfolio(
    tmp_path: Path,
    stages: dict[str, DeliveryStage],
    now: list[str],
    *,
    capacity: int = 3,
    include_independent: bool = False,
):
    """Assemble real Delivery owners; only window liveness and the worktree process table are fakes."""
    base, runtimes, coordinator, state_root = _portfolio(
        tmp_path,
        stages,
        execution_capacity=capacity,
        clock=lambda: now[0],
        include_independent=include_independent,
    )
    probe = _Probe()
    identities = (f"progress-{index:03}" for index in itertools.count(1))
    application = PortfolioApplication(
        dict(reversed(tuple(runtimes.items()))),
        PortfolioApplicationDependencies(
            target_root=state_root,
            package_store=base._package_store,
            authority_registry=base._authority_registry,
            coordinator=coordinator,
            workspace_manager=base._workspace_manager,
            completed_history_catalog=CompletedHistoryCatalog(state_root),
            issuer_window=_WINDOW,
            window_liveness_probe=probe,
            worktree_process_probe=probe,
        ),
        PortfolioApplicationConfig(
            package_root=tmp_path / "packages",
            execution_capacity=capacity,
            role_policies=_policies(),
        ),
        PortfolioApplicationHooks(identity_factory=lambda: next(identities), clock=lambda: now[0]),
    )
    return application, runtimes, coordinator, state_root, probe


def _rewrite_bindings(runtime, state_root: Path, updates: dict[str, dict[str, object]]) -> None:
    frontier = DeliveryFrontier.model_validate_json(runtime.frontier_bytes(), strict=True)
    bindings = tuple(binding.model_copy(update=updates.get(binding.outcome_id, {})) for binding in frontier.bindings)
    rewritten = DeliveryFrontier.model_validate(frontier.model_copy(update={"bindings": bindings}).model_dump())
    (state_root / "changes" / runtime.contract.change_id / "frontier.json").write_bytes(_canonical(rewritten))


def _complete_first_outcome(application: PortfolioApplication, runtime, state_root: Path) -> None:
    commit = application._workspace_manager.show(runtime.contract.change_id).last_reviewed_commit
    result = _task_result("RESULT-001", runtime.contract.change_id, runtime.authority_digest, _task(), commit)
    _rewrite_bindings(runtime, state_root, {"OUT-001": {"stage": DeliveryStage.COMPLETED, "results": (result,)}})


def _card(application: PortfolioApplication, item_key: str, change_id: str = "change-a") -> WorkItemCardView:
    return application.show_work_item_view(change_id, item_key).card


def _group(application: PortfolioApplication, change_id: str = "change-a"):
    return next(group for group in application.list_work_item_groups() if group.change_id == change_id)


def _record_tree(root: Path) -> dict[str, bytes]:
    return {str(path.relative_to(root)): path.read_bytes() for path in sorted(root.rglob("*")) if path.is_file()}


# Assembled positive scenarios.


def test_undispatched_builder_claim_with_live_issuer_shows_neutral_custody(tmp_path: Path) -> None:
    now = [_iso(_real_now())]
    application, _runtimes, _coordinator, _state_root, probe = _progress_portfolio(
        tmp_path, {"change-a": DeliveryStage.IMPLEMENTATION}, now
    )
    acquired = application.acquire_change_action(_continuation_request(application, "change-a"))
    assert acquired.launch is not None, acquired
    probe.states[_HOST] = "alive"

    view = application.show_work_item_view("change-a", "outcome:OUT-001")
    readiness = view.card.readiness
    assert readiness is not None
    assert (readiness.status, readiness.reason_code, readiness.progress) == ("running", "active-custody", None)
    assert view.card.next_step == "Claimed by Builder"
    assert view.change_progress is None
    group = _group(application)
    assert group.progress is None
    change = application.get_change("change-a")
    assert change.detail.change_progress is None
    assert change.readiness is not None
    assert change.readiness.progress is None
    observed = {group.progress, change.detail.change_progress, *(item.readiness.progress for item in group.items)}
    assert not observed & _RESERVED


def test_ready_planning_outcome_waits_for_chat_with_continuation_prompt(tmp_path: Path) -> None:
    now = [_iso(_real_now())]
    application, *_rest = _progress_portfolio(tmp_path, {"change-a": DeliveryStage.PLANNING}, now)

    card = _card(application, "outcome:OUT-001")
    readiness = card.readiness
    assert readiness is not None
    assert (readiness.status, readiness.progress) == ("ready", "waiting-for-chat")
    assert readiness.action is not None
    assert (readiness.action.kind, readiness.action.label) == (
        WorkItemActionKind.START_ORCHESTRATION,
        "Copy continuation prompt",
    )
    assert readiness.prompt is not None
    assert readiness.prompt.startswith("/continue-change change-a ")
    assert card.next_step == "Run the continuation prompt in Copilot Chat"
    change = application.get_change("change-a")
    assert (change.readiness.progress, change.detail.change_progress) == ("waiting-for-chat", "waiting-for-chat")
    assert _group(application).progress == "waiting-for-chat"


@pytest.mark.parametrize("role", ["planner", "builder"])
def test_live_issuer_claim_is_neutral_custody_and_unknown_evidence_needs_decision(tmp_path: Path, role: str) -> None:
    now = [_iso(_real_now())]
    stage = DeliveryStage.PLANNING if role == "planner" else DeliveryStage.IMPLEMENTATION
    application, _runtimes, _coordinator, state_root, probe = _progress_portfolio(tmp_path, {"change-a": stage}, now)
    acquired = application.acquire_change_action(_continuation_request(application))
    if acquired.kind == "reconciled":
        acquired = application.acquire_change_action(_continuation_request(application))
    assert acquired.launch is not None, acquired
    claim = acquired.launch.claim

    alive = _card(application, "outcome:OUT-001")
    assert (alive.readiness.status, alive.readiness.progress) == ("running", None)
    assert alive.next_step == f"Claimed by {role.capitalize()}"

    probe.states[_HOST] = "unknown"
    unknown = _card(application, "outcome:OUT-001")
    assert (unknown.readiness.status, unknown.readiness.progress) == ("running", "needs-decision")
    assert unknown.next_step == f"Claimed by {role.capitalize()}"
    assert _group(application).progress == "needs-decision"
    assert application.get_change("change-a").detail.change_progress == "needs-decision"

    probe.states[_HOST] = "alive"
    _issuer_path(state_root, "change-a", claim.attempt_id).unlink()
    missing = _card(application, "outcome:OUT-001")
    assert (missing.readiness.status, missing.readiness.progress) == ("running", "needs-decision")


def test_finalizer_attempt_shows_held_custody_or_decision(tmp_path: Path) -> None:
    now = [_iso(_real_now())]
    application, _runtimes, _coordinator, _state_root, probe = _progress_portfolio(
        tmp_path, {"change-a": DeliveryStage.COMPLETED}, now
    )
    acquired = application.acquire_change_action(_continuation_request(application))
    assert acquired.finalization is not None, acquired

    publication = _card(application, "publication")
    assert (publication.readiness.status, publication.readiness.reason_code) == ("running", "active-custody")
    assert publication.readiness.progress is None
    assert publication.next_step == "Finalizer attempt held"
    assert application.get_change("change-a").detail.change_progress is None

    probe.states[_HOST] = "unknown"
    assert _card(application, "publication").readiness.progress == "needs-decision"
    assert application.get_change("change-a").detail.change_progress == "needs-decision"


def test_closed_issuing_window_waits_for_chat(tmp_path: Path) -> None:
    now = [_iso(_real_now())]
    application, _runtimes, _coordinator, _state_root, probe = _progress_portfolio(
        tmp_path, {"change-a": DeliveryStage.PLANNING}, now
    )
    _acquire_planning_claim(application)
    probe.states[_HOST] = "gone"
    probe.processes = ("node",)

    card = _card(application, "outcome:OUT-001")
    assert (card.readiness.reason_code, card.readiness.progress) == ("worker-stall-wait", "waiting-for-chat")
    assert _group(application).progress == "waiting-for-chat"


def test_pending_engine_action_waits_for_chat_with_resume_prompt(tmp_path: Path) -> None:
    application, *_rest = _awaiting_acceptance_fixture(tmp_path, mark_ready=False)
    _engine_action(application)

    change = application.get_change("change-a")
    assert (change.readiness.reason_code, change.readiness.progress) == ("engine-action-pending", "waiting-for-chat")
    assert change.readiness.prompt.startswith("/continue-change change-a Resume the exact engine-selected operation")
    assert change.detail.change_progress == "waiting-for-chat"
    assert _group(application).progress == "waiting-for-chat"


def test_full_execution_capacity_waits_for_another_change(tmp_path: Path) -> None:
    now = [_iso(_real_now())]
    application, _runtimes, coordinator, _state_root, _probe = _progress_portfolio(
        tmp_path, {"change-a": DeliveryStage.PLANNING, "change-b": DeliveryStage.PLANNING}, now, capacity=1
    )
    held = application.acquire_change_action(_continuation_request(application, "change-a"))
    assert held.launch is not None, held

    waiting = _card(application, "outcome:OUT-001", "change-b")
    assert (waiting.readiness.status, waiting.readiness.progress) == ("ready", "waiting-for-change")
    assert _group(application, "change-b").progress == "waiting-for-change"
    assert application.get_change("change-b").detail.change_progress == "waiting-for-change"

    with patch.object(coordinator, "list_registered", side_effect=OSError("occupancy unreadable")):
        unreadable = _card(application, "outcome:OUT-001", "change-b")
    assert unreadable.readiness.progress == "waiting-for-chat"


def test_open_request_needs_decision(tmp_path: Path) -> None:
    now = [_iso(_real_now())]
    application, *_rest = _progress_portfolio(tmp_path, {"change-a": DeliveryStage.PLANNING}, now)
    claim = _acquire_planning_claim(application)
    application.transition_delivery("change-a", _planning_decision_block(claim.claim_id, 0))

    card = _card(application, "outcome:OUT-001")
    assert (card.readiness.reason_code, card.readiness.progress) == ("request-action", "needs-decision")
    assert _group(application).progress == "needs-decision"


def test_exhausted_retry_needs_decision(tmp_path: Path) -> None:
    application, _runtime, _contexts = _exhaust_builder_retry_with_distinct_codes(tmp_path)

    card = _card(application, "outcome:OUT-001")
    assert (card.readiness.reason_code, card.readiness.progress) == ("retry-exhausted", "needs-decision")


def test_awaiting_merge_and_acceptance_wait_are_ready_to_merge(tmp_path: Path) -> None:
    (tmp_path / "awaiting").mkdir()
    (tmp_path / "exhausted").mkdir()
    application, *_rest = _awaiting_acceptance_fixture(tmp_path / "awaiting")
    publication = _card(application, "publication")
    assert publication.publication_phase is WorkItemPublicationPhase.AWAITING_MERGE
    assert publication.readiness.progress == "ready-to-merge"
    assert application.get_change("change-a").detail.change_progress == "ready-to-merge"

    _first, _provider, _ledger, restart = acceptance_budget_case(tmp_path / "exhausted", exhausted=True)
    readiness = restart().get_change("change-a").readiness
    assert (readiness.reason_code, readiness.progress) == ("acceptance-wait", "ready-to-merge")


def test_provider_backoff_waits_for_service(tmp_path: Path) -> None:
    now = {"value": "2026-08-04T00:00:00Z"}
    application, _runtime, provider, _state, _head, _state_root = _awaiting_acceptance_fixture(
        tmp_path, mark_ready=False, clock=lambda: now["value"]
    )
    action = _engine_action(application)
    provider.read_pull_request.side_effect = PublicationProviderError(
        PublicationProviderFailureCode.UNAVAILABLE, "read_pull_request", "provider unavailable", retry_safe=True
    )
    assert _execute_engine(application, action).kind == "blocked"

    readiness = application.get_change("change-a").readiness
    assert (readiness.reason_code, readiness.operation) == ("retry-backoff", WorkItemActionKind.MARK_READY)
    assert readiness.progress == "waiting-for-service"


def test_pause_and_resume_project_paused_then_restore(tmp_path: Path) -> None:
    now = [_iso(_real_now())]
    application, *_rest = _progress_portfolio(tmp_path, {"change-a": DeliveryStage.PLANNING}, now)
    digest = application.get_change("change-a").frontier_digest

    paused = application.set_change_intent(
        DeliveryChangeIntent(
            change_id="change-a", kind=DeliveryChangeIntentKind.DEFER, expected_frontier_digest=digest, reason="Hold"
        )
    )

    assert _group(application).progress == "paused"
    assert {item.readiness.progress for item in _group(application).items} == {"paused"}
    application.set_change_intent(
        DeliveryChangeIntent(
            change_id="change-a", kind=DeliveryChangeIntentKind.RESUME, expected_frontier_digest=paused.frontier_digest
        )
    )
    assert _group(application).progress == "waiting-for-chat"


def test_accepted_completion_projects_completed(tmp_path: Path) -> None:
    application, _runtime, _provider, state, _head, _state_root = _awaiting_acceptance_fixture(tmp_path)
    state["pull_request"] = state["pull_request"].model_copy(
        update={
            "state": "closed",
            "merged": True,
            "merge_commit_sha": "f" * 40,
            "merged_at": datetime(2026, 8, 3, 14, tzinfo=UTC),
            "merged_by_login": "octocat",
        }
    )
    application.observe_acceptance("change-a")

    change = application.get_change("change-a")
    assert (change.readiness.progress, change.detail.change_progress) == ("completed", "completed")


# Change activity selection (C1-C5).


@pytest.mark.parametrize("issuer", ["alive", "unknown"])
def test_change_activity_follows_second_outcome_not_first_completed_card(tmp_path: Path, issuer: str) -> None:
    now = [_iso(_real_now())]
    application, runtimes, _coordinator, state_root, probe = _progress_portfolio(
        tmp_path, {"change-a": DeliveryStage.IMPLEMENTATION}, now, include_independent=True
    )
    _complete_first_outcome(application, runtimes["change-a"], state_root)

    ready = application.get_change("change-a")
    assert ready.detail.card.work_item_id == "OUT-001"
    assert ready.detail.card.readiness.progress == "completed"
    assert ready.detail.change_progress == "waiting-for-chat"
    assert _group(application).progress == "waiting-for-chat"

    acquired = application.acquire_change_action(_continuation_request(application))
    assert acquired.launch is not None, acquired
    assert acquired.launch.outcome_id == "OUT-002"
    probe.states[_HOST] = issuer
    expected = None if issuer == "alive" else "needs-decision"

    held = application.get_change("change-a")
    assert held.detail.card.work_item_id == "OUT-001"
    assert held.detail.card.readiness.progress == "completed"
    assert held.detail.change_progress == expected
    assert _group(application).progress == expected
    assert _card(application, "outcome:OUT-002").next_step == "Claimed by Builder"


def test_contained_builder_transition_wins_change_activity(tmp_path: Path) -> None:
    application, runtimes, _coordinator, _state_root, _launch, transition = builder_transition_case(tmp_path, "block")
    with pytest.raises(DeliveryWorkerExclusionRequiredError):
        application.transition_delivery("change-a", transition)
    snapshot = application._delivery_snapshot(runtimes["change-a"])
    contained = _card(application, "outcome:OUT-001")
    assert (contained.readiness.reason_code, contained.readiness.progress) == ("builder-transition-contained", None)
    running = contained.model_copy(
        update={
            "item_key": "outcome:OUT-002",
            "work_item_id": "OUT-002",
            "readiness": contained.readiness.model_copy(
                update={"status": "running", "reason_code": "active-custody", "progress": "needs-decision"}
            ),
        }
    )

    assert application._change_activity_card(snapshot, (running, contained)) == contained
    assert application.get_change("change-a").detail.change_progress is None


@pytest.fixture
def dependency_first_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    original = portfolio_fixtures._contract

    def dependent_first(*args, **kwargs):
        contract = original(*args, **kwargs)
        first, second = contract.outcomes
        dependent = first.model_copy(update={"dependency_ids": ("OUT-002",)})
        return contract.model_copy(update={"outcomes": (dependent, second)})

    monkeypatch.setattr(portfolio_fixtures, "_contract", dependent_first)


@pytest.mark.usefixtures("dependency_first_contract")
def test_dependency_first_declaration_follows_runnable_sibling(tmp_path: Path) -> None:
    now = [_iso(_real_now())]
    application, runtimes, _coordinator, state_root, _probe = _progress_portfolio(
        tmp_path, {"change-a": DeliveryStage.IMPLEMENTATION}, now, include_independent=True
    )
    first = _card(application, "outcome:OUT-001")
    assert (first.readiness.reason_code, first.readiness.progress) == ("dependency-wait", None)
    assert _card(application, "outcome:OUT-002").readiness.progress == "waiting-for-chat"
    assert _group(application).progress == "waiting-for-chat"
    assert application.get_change("change-a").detail.change_progress == "waiting-for-chat"

    block = DeliveryBlock(
        block_id="blocked-sibling",
        reason="Sibling needs evidence.",
        unblock_condition="Evidence supplied.",
        expected_evidence=("evidence",),
        locators=("SCOPE-002",),
    )
    _rewrite_bindings(runtimes["change-a"], state_root, {"OUT-002": {"block": block}})
    snapshot = application._delivery_snapshot(runtimes["change-a"])
    cards = application._read_projector(snapshot).group_view().items

    assert runtimes["change-a"].claimable_outcome_ids() == ()
    assert _card(application, "outcome:OUT-002").readiness.progress == "needs-decision"
    assert application._change_activity_card(snapshot, cards).work_item_id == "OUT-001"
    assert _group(application).progress is None


# Negative scenarios.


def test_unreadable_retry_ledger_keeps_unavailable_readiness_without_progress(tmp_path: Path) -> None:
    now = [_iso(_real_now())]
    application, _runtimes, _coordinator, state_root, _probe = _progress_portfolio(
        tmp_path, {"change-a": DeliveryStage.PLANNING}, now
    )
    summary = RetryLedger(state_root, "change-a").summary_path
    summary.parent.mkdir(parents=True, exist_ok=True)
    summary.write_bytes(b"{")

    readiness = _card(application, "outcome:OUT-001").readiness
    assert (readiness.reason_code, readiness.progress) == ("retry-ledger-unavailable", None)


def test_progress_reads_create_no_delivery_record(tmp_path: Path) -> None:
    now = [_iso(_real_now())]
    application, _runtimes, _coordinator, state_root, probe = _progress_portfolio(
        tmp_path, {"change-a": DeliveryStage.PLANNING, "change-b": DeliveryStage.PLANNING}, now, capacity=1
    )
    assert application.acquire_change_action(_continuation_request(application, "change-a")).launch is not None
    before = _record_tree(state_root)

    for state in ("alive", "unknown", "gone"):
        probe.states[_HOST] = state
        application.list_work_items()
        application.portfolio_read_view()
        for change_id in ("change-a", "change-b"):
            application.get_change(change_id)
            application.show_work_item_view(change_id, "outcome:OUT-001")

    assert _record_tree(state_root) == before


def test_portfolio_never_emits_reserved_or_start_labels(tmp_path: Path) -> None:
    now = [_iso(_real_now())]
    application, *_rest = _progress_portfolio(
        tmp_path, {"change-a": DeliveryStage.PLANNING, "change-b": DeliveryStage.IMPLEMENTATION}, now
    )
    application.acquire_change_action(_continuation_request(application, "change-b"))

    for group in application.list_work_item_groups():
        assert group.progress not in _RESERVED
        for item in group.items:
            assert item.readiness.progress not in _RESERVED
            labels = (item.action.label, item.readiness.action.label if item.readiness.action else None)
            assert not any(label and "Start" in label for label in labels)


# Exhaustive pure mapping (plan section 1.4).

_BASIS = DeliveryReadinessBasis()


def _outcome_card(**updates: object) -> WorkItemCardView:
    card = WorkItemCardView(
        item_key="outcome:OUT-001",
        work_item_id="OUT-001",
        change_id="change-a",
        scope=WorkItemScope.OUTCOME,
        title="Outcome",
        stage=WorkItemStage.IMPLEMENTATION,
        needs=WorkItemNeed.NONE,
        next_actor=WorkItemNextActor.AGENT,
        next_step="Next",
        activity=WorkItemActivity(state=WorkItemActivityState.READY),
        progress=WorkItemProgress(kind=WorkItemProgressKind.TASKS, label="Tasks"),
        action=WorkItemAction(),
    )
    return card.model_copy(update=updates)


def _readiness(
    status: str,
    reason: str,
    *,
    operation: WorkItemActionKind | None = None,
    executable: bool = False,
    next_actor: WorkItemNextActor = WorkItemNextActor.AGENT,
) -> DeliveryReadiness:
    return DeliveryReadiness(
        status=status,
        reason_code=reason,
        operation=operation,
        executable=executable,
        next_actor=next_actor,
        basis=_BASIS,
        action=WorkItemAction(kind=operation, label="Run") if executable and operation is not None else None,
    )


_START = WorkItemActionKind.START_ORCHESTRATION
_FRONTIER = DeliveryFrontier(
    bindings=(OutcomeAuthorityBinding(outcome_id="OUT-001", plan_scope_id="SCOPE-001", stage=DeliveryStage.PLANNING),)
)
# The projection reads only lifecycle presence; any non-None value stands for the record.
_PRESENT = object()

# reason -> (status, operation, executable, frontier lifecycle field, expected progress)
_EXPECTED: dict[str, tuple[str, WorkItemActionKind | None, bool, str | None, DeliveryProgress | None]] = {
    "ready": ("ready", _START, True, None, "waiting-for-chat"),
    "design-attention": ("blocked", None, False, None, "needs-decision"),
    "active-custody": ("running", None, False, None, None),
    "builder-transition-contained": ("blocked", None, False, None, None),
    "retry-transition-contained": ("blocked", None, False, None, None),
    "finalization-failed": ("blocked", None, False, None, None),
    "claim-activation-failed": ("blocked", None, False, None, None),
    "coordination-unavailable": ("unavailable", None, False, None, None),
    "execution-occupancy-unavailable": ("unavailable", None, False, None, None),
    "engine-action-pending": ("running", None, False, None, "waiting-for-chat"),
    "engine-action-blocked": ("blocked", None, False, None, None),
    "engine-action-interrupted": ("blocked", None, False, None, None),
    "engine-action-failed": ("blocked", None, False, None, None),
    "engine-action-incomplete": ("blocked", None, False, None, None),
    "target-sync-required": ("waiting", None, False, None, "waiting-for-chat"),
    "claim-custody-unreconciled": ("blocked", None, False, None, None),
    "runtime-unavailable": ("unavailable", None, False, None, None),
    "dependency-wait": ("waiting", None, False, None, None),
    "request-action": ("ready", WorkItemActionKind.ANSWER_REQUEST, True, None, "needs-decision"),
    "change-paused": ("blocked", None, False, "change_deferral", "paused"),
    "change-terminal": ("complete", None, False, "change_completion", "completed"),
    "task-incomplete": ("waiting", None, False, None, None),
    "workspace-inspection-failed": ("unavailable", None, False, None, None),
    "workspace-dirty": ("blocked", None, False, None, None),
    "workspace-preflight-failed": ("blocked", None, False, None, None),
    "settled-attention-target-drift": ("blocked", None, False, None, "needs-decision"),
    "review-repair": ("blocked", None, False, None, "waiting-for-chat"),
    "publication-wait": ("waiting", None, False, None, "waiting-for-service"),
    "checkpoint-pending": ("waiting", None, False, None, "waiting-for-service"),
    "report-store-unavailable": ("ready", _START, True, None, None),
    "retry-backoff": ("waiting", WorkItemActionKind.SYNC_TARGET, False, None, "waiting-for-service"),
    "retry-exhausted": ("blocked", None, False, None, "needs-decision"),
    "acceptance-wait": ("waiting", WorkItemActionKind.OBSERVE_ACCEPTANCE, False, None, "ready-to-merge"),
    "retry-containment": ("blocked", None, False, None, None),
    "retry-ledger-unavailable": ("unavailable", None, False, None, None),
    "worker-stall-wait": ("waiting", None, False, None, "waiting-for-chat"),
}


def test_every_readiness_reason_has_an_explicit_progress_mapping() -> None:
    assert set(_EXPECTED) == set(get_args(DeliveryReadinessReason))


@pytest.mark.parametrize("reason", sorted(_EXPECTED))
def test_readiness_reason_maps_to_programme_progress(reason: str) -> None:
    status, operation, executable, lifecycle, expected = _EXPECTED[reason]
    frontier = _FRONTIER if lifecycle is None else _FRONTIER.model_copy(update={lifecycle: _PRESENT})

    progress = derive_delivery_progress(
        _readiness(status, reason, operation=operation, executable=executable), _outcome_card(), frontier
    )

    assert progress == expected


@pytest.mark.parametrize(
    ("issuer", "expected"), [(None, None), ("alive", None), ("gone", "waiting-for-chat"), ("unknown", "needs-decision")]
)
def test_running_custody_maps_issuer_evidence_without_active_labels(issuer: str | None, expected: str | None) -> None:
    progress = derive_delivery_progress(
        _readiness("running", "active-custody"), _outcome_card(), _FRONTIER, issuer_state=issuer
    )
    assert progress == expected


def test_capacity_and_service_retries_select_their_waits() -> None:
    ready = _readiness("ready", "ready", operation=_START, executable=True)
    assert derive_delivery_progress(ready, _outcome_card(), _FRONTIER, at_capacity=True) == "waiting-for-change"
    assert derive_delivery_progress(ready, _outcome_card(), _FRONTIER) == "waiting-for-chat"
    human = _readiness("ready", "ready", operation=_START, executable=True, next_actor=WorkItemNextActor.YOU)
    assert derive_delivery_progress(human, _outcome_card(), _FRONTIER) is None
    for operation in (WorkItemActionKind.SYNC_TARGET, WorkItemActionKind.MARK_READY):
        backoff = _readiness("waiting", "retry-backoff", operation=operation)
        assert derive_delivery_progress(backoff, _outcome_card(), _FRONTIER) == "waiting-for-service"
    backoff = _readiness("waiting", "retry-backoff", operation=_START)
    assert derive_delivery_progress(backoff, _outcome_card(), _FRONTIER) == "waiting-for-chat"
    executable_checkpoint = _readiness(
        "ready", "checkpoint-pending", operation=WorkItemActionKind.RECONCILE_CHECKPOINT, executable=True
    )
    assert derive_delivery_progress(executable_checkpoint, _outcome_card(), _FRONTIER) is None


def test_awaiting_merge_publication_is_ready_to_merge_unless_conflicted() -> None:
    publication = _outcome_card(
        item_key="publication",
        scope=WorkItemScope.CHANGE_PUBLICATION,
        stage=None,
        publication_phase=WorkItemPublicationPhase.AWAITING_MERGE,
        action=WorkItemAction(kind=WorkItemActionKind.OBSERVE_ACCEPTANCE, label="Check merge status"),
    )
    request = _readiness(
        "ready",
        "request-action",
        operation=WorkItemActionKind.OBSERVE_ACCEPTANCE,
        executable=True,
        next_actor=WorkItemNextActor.YOU,
    )
    assert derive_delivery_progress(request, publication, _FRONTIER) == "ready-to-merge"
    conflicted = publication.model_copy(
        update={"action": publication.action.model_copy(update={"command": "/resolve-target-conflict change-a"})}
    )
    assert derive_delivery_progress(request, conflicted, _FRONTIER) == "needs-decision"
    exhausted = _readiness("blocked", "retry-exhausted")
    assert derive_delivery_progress(exhausted, publication, _FRONTIER) == "needs-decision"


def test_abandonment_has_no_progress_and_completion_wins() -> None:
    complete = _readiness("complete", "change-terminal")
    abandoned = _FRONTIER.model_copy(update={"change_abandonment": _PRESENT})
    assert derive_delivery_progress(complete, _outcome_card(), abandoned) is None
    assert derive_delivery_progress(complete, _outcome_card(), _FRONTIER) == "completed"


def test_reserved_progress_keys_are_never_emitted() -> None:
    reasons = get_args(DeliveryReadinessReason)
    statuses = ("ready", "running", "waiting", "blocked", "unavailable", "complete")
    frontiers = (
        _FRONTIER,
        *(_FRONTIER.model_copy(update={field: _PRESENT}) for field in ("change_deferral", "change_completion")),
    )
    cards = (_outcome_card(), _outcome_card(publication_phase=WorkItemPublicationPhase.AWAITING_MERGE))
    emitted = set()
    for reason, status, frontier, card, issuer, capacity in itertools.product(
        reasons, statuses, frontiers, cards, (None, "alive", "gone", "unknown"), (False, True)
    ):
        executable = status == "ready"
        readiness = _readiness(status, reason, operation=_START if executable else None, executable=executable)
        emitted.add(derive_delivery_progress(readiness, card, frontier, issuer_state=issuer, at_capacity=capacity))
    assert not emitted & _RESERVED
    assert emitted - {None} <= set(get_args(DeliveryProgress)) - _RESERVED
