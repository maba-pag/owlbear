# ruff: noqa: SLF001
"""Assembled and exhaustive proof of the N09-A1 programme progress projection."""

from __future__ import annotations

import hashlib
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
    _failure_request,
    _finalizer_settlement,
    _planning_decision_block,
    _policies,
    _portfolio,
    _task,
    _task_result,
    acceptance_budget_case,
    builder_transition_case,
    retain_contained_transition,
)
from serve.delivery.tests.test_worker_stall import _HOST, _WINDOW, _iso, _issuer_path, _Probe, _real_now

from owlbear_delivery import (
    CompletedHistoryCatalog,
    DeliveryBlock,
    DeliveryChangeIntent,
    DeliveryChangeIntentKind,
    DeliveryFrontier,
    DeliveryRequest,
    DeliveryRequestKind,
    DeliveryRequestOption,
    DeliveryStage,
    OutcomeAuthorityBinding,
    PortfolioApplication,
    PortfolioApplicationConfig,
    PortfolioApplicationDependencies,
    PortfolioApplicationHooks,
)
from owlbear_delivery.finalization_reports import FinalizationReportStore
from owlbear_delivery.merge_offer import MergeBlock, MergeBlockReason
from owlbear_delivery.publication_provider import PublicationProviderError, PublicationProviderFailureCode
from owlbear_delivery.recovery import DeliveryWorkerExclusionRequiredError, RetryLedger
from owlbear_delivery.work_items import (
    DeliveryProgress,
    DeliveryReadiness,
    DeliveryReadinessBasis,
    DeliveryReadinessReason,
    DeliverySituation,
    MergeAttemptSummary,
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


def _situation(progress: DeliveryProgress | None) -> str | None:
    return progress.situation if progress is not None else None


_IN_GITHUB_BLOCKS = frozenset(
    {
        MergeBlockReason.CAPABILITY_UNAVAILABLE,
        MergeBlockReason.QUEUE_REQUIRED,
        MergeBlockReason.STACKED,
        MergeBlockReason.METHOD_NOT_ALLOWED,
    }
)


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


def test_undispatched_builder_claim_with_live_issuer_is_with_agent(tmp_path: Path) -> None:
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
    assert (readiness.status, readiness.reason_code) == ("running", "active-custody")
    assert readiness.progress == DeliveryProgress(
        situation="with-agent",
        headline="Builder holds this step.",
        waiting_on="agent",
        since=view.card.activity.started_at,
    )
    assert view.card.next_step == "Claimed by Builder"
    assert view.change_progress == readiness.progress
    group = _group(application)
    assert group.progress == readiness.progress
    change = application.get_change("change-a")
    assert change.detail.change_progress == readiness.progress


def test_ready_planning_outcome_is_ready_for_next_step_with_continuation_prompt(tmp_path: Path) -> None:
    now = [_iso(_real_now())]
    application, *_rest = _progress_portfolio(tmp_path, {"change-a": DeliveryStage.PLANNING}, now)

    card = _card(application, "outcome:OUT-001")
    readiness = card.readiness
    assert readiness is not None
    assert (readiness.status, _situation(readiness.progress)) == ("ready", "ready-for-next-step")
    assert readiness.progress.headline == "Run the prompt in Copilot Chat to continue this Change."
    assert readiness.progress.waiting_on == "you"
    assert readiness.action is not None
    assert (readiness.action.kind, readiness.action.label) == (
        WorkItemActionKind.START_ORCHESTRATION,
        "Copy continuation prompt",
    )
    assert readiness.prompt is not None
    assert readiness.prompt.startswith("/continue-change change-a ")
    assert card.next_step == "Run the continuation prompt in Copilot Chat"
    change = application.get_change("change-a")
    assert change.readiness.progress == change.detail.change_progress == readiness.progress
    assert _group(application).progress == readiness.progress


@pytest.mark.parametrize("role", ["planner", "builder"])
def test_live_issuer_claim_is_with_agent_and_unknown_evidence_needs_attention(tmp_path: Path, role: str) -> None:
    now = [_iso(_real_now())]
    stage = DeliveryStage.PLANNING if role == "planner" else DeliveryStage.IMPLEMENTATION
    application, _runtimes, _coordinator, state_root, probe = _progress_portfolio(tmp_path, {"change-a": stage}, now)
    acquired = application.acquire_change_action(_continuation_request(application))
    if acquired.kind == "reconciled":
        acquired = application.acquire_change_action(_continuation_request(application))
    assert acquired.launch is not None, acquired
    claim = acquired.launch.claim

    alive = _card(application, "outcome:OUT-001")
    assert (alive.readiness.status, _situation(alive.readiness.progress)) == ("running", "with-agent")
    assert alive.readiness.progress.headline == f"{role.capitalize()} holds this step."
    assert alive.next_step == f"Claimed by {role.capitalize()}"

    probe.states[_HOST] = "unknown"
    unknown = _card(application, "outcome:OUT-001")
    assert (unknown.readiness.status, _situation(unknown.readiness.progress)) == ("running", "needs-attention")
    assert unknown.next_step == f"Claimed by {role.capitalize()}"
    assert _situation(_group(application).progress) == "needs-attention"
    assert _situation(application.get_change("change-a").detail.change_progress) == "needs-attention"

    probe.states[_HOST] = "alive"
    _issuer_path(state_root, "change-a", claim.attempt_id).unlink()
    missing = _card(application, "outcome:OUT-001")
    assert (missing.readiness.status, _situation(missing.readiness.progress)) == ("running", "needs-attention")


def test_finalizer_attempt_is_with_agent_or_needs_attention(tmp_path: Path) -> None:
    now = [_iso(_real_now())]
    application, _runtimes, _coordinator, _state_root, probe = _progress_portfolio(
        tmp_path, {"change-a": DeliveryStage.COMPLETED}, now
    )
    acquired = application.acquire_change_action(_continuation_request(application))
    assert acquired.finalization is not None, acquired

    publication = _card(application, "publication")
    assert (publication.readiness.status, publication.readiness.reason_code) == ("running", "active-custody")
    assert publication.readiness.progress.headline == "Finalizer holds this step."
    assert publication.readiness.progress.target_sync == "unavailable"
    assert publication.next_step == "Finalizer attempt held"
    assert _situation(application.get_change("change-a").detail.change_progress) == "with-agent"

    probe.states[_HOST] = "unknown"
    assert _situation(_card(application, "publication").readiness.progress) == "needs-attention"
    assert _situation(application.get_change("change-a").detail.change_progress) == "needs-attention"


def test_closed_issuing_window_waits_on_delivery_then_is_ready_for_next_step(tmp_path: Path) -> None:
    now = [_iso(_real_now())]
    application, _runtimes, _coordinator, _state_root, probe = _progress_portfolio(
        tmp_path, {"change-a": DeliveryStage.PLANNING}, now
    )
    _acquire_planning_claim(application)
    probe.states[_HOST] = "gone"
    probe.processes = ("node",)

    card = _card(application, "outcome:OUT-001")
    assert card.readiness.reason_code == "worker-stall-wait"
    assert card.readiness.progress.situation == "waiting-on-delivery"
    assert card.readiness.progress.waiting_on == "delivery"
    assert card.readiness.progress.next_eligible_at is None
    assert _group(application).progress == card.readiness.progress

    probe.processes = ()
    card = _card(application, "outcome:OUT-001")
    assert card.readiness.reason_code == "worker-stall-wait"
    assert card.readiness.progress.situation == "ready-for-next-step"
    assert card.readiness.next_eligible_at is not None
    assert card.readiness.progress.next_eligible_at == card.readiness.next_eligible_at


def test_pending_engine_action_is_ready_for_next_step_with_resume_prompt(tmp_path: Path) -> None:
    application, *_rest = _awaiting_acceptance_fixture(tmp_path, mark_ready=False)
    _engine_action(application)

    change = application.get_change("change-a")
    assert change.readiness.reason_code == "engine-action-pending"
    assert _situation(change.readiness.progress) == "ready-for-next-step"
    assert change.readiness.prompt.startswith("/continue-change change-a Resume the exact engine-selected operation")
    assert _situation(change.detail.change_progress) == "ready-for-next-step"
    assert _situation(_group(application).progress) == "ready-for-next-step"


def test_full_execution_capacity_waits_on_another_change(tmp_path: Path) -> None:
    now = [_iso(_real_now())]
    application, _runtimes, coordinator, _state_root, _probe = _progress_portfolio(
        tmp_path, {"change-a": DeliveryStage.PLANNING, "change-b": DeliveryStage.PLANNING}, now, capacity=1
    )
    held = application.acquire_change_action(_continuation_request(application, "change-a"))
    assert held.launch is not None, held

    waiting = _card(application, "outcome:OUT-001", "change-b")
    assert waiting.readiness.status == "ready"
    assert (_situation(waiting.readiness.progress), waiting.readiness.progress.waiting_on) == (
        "waiting-on-dependency",
        "change",
    )
    assert _group(application, "change-b").progress == waiting.readiness.progress
    assert application.get_change("change-b").detail.change_progress == waiting.readiness.progress

    with patch.object(coordinator, "list_registered", side_effect=OSError("occupancy unreadable")):
        unreadable = _card(application, "outcome:OUT-001", "change-b")
    assert _situation(unreadable.readiness.progress) == "ready-for-next-step"


def test_open_decision_request_is_your_decision(tmp_path: Path) -> None:
    now = [_iso(_real_now())]
    application, *_rest = _progress_portfolio(tmp_path, {"change-a": DeliveryStage.PLANNING}, now)
    claim = _acquire_planning_claim(application)
    application.transition_delivery("change-a", _planning_decision_block(claim.claim_id, 0))

    card = _card(application, "outcome:OUT-001")
    assert card.readiness.reason_code == "request-action"
    assert _situation(card.readiness.progress) == "your-decision"
    assert card.readiness.progress.headline.startswith("Decide: ")
    assert _group(application).progress == card.readiness.progress


def test_exhausted_same_task_builder_retry_is_your_decision(tmp_path: Path) -> None:
    application, _runtime, _contexts = _exhaust_builder_retry_with_distinct_codes(tmp_path)

    card = _card(application, "outcome:OUT-001")
    assert card.readiness.reason_code == "retry-exhausted"
    assert _situation(card.readiness.progress) == "your-decision"


def test_awaiting_merge_is_your_decision_and_exhausted_acceptance_names_the_block(tmp_path: Path) -> None:
    (tmp_path / "awaiting").mkdir()
    (tmp_path / "exhausted").mkdir()
    application, *_rest = _awaiting_acceptance_fixture(tmp_path / "awaiting")
    publication = _card(application, "publication")
    assert publication.publication_phase is WorkItemPublicationPhase.AWAITING_MERGE
    assert _situation(publication.readiness.progress) == "your-decision"
    assert application.get_change("change-a").detail.change_progress == publication.readiness.progress

    _first, _provider, _ledger, restart = acceptance_budget_case(tmp_path / "exhausted", exhausted=True)
    readiness = restart().get_change("change-a").readiness
    assert readiness.reason_code == "merge-blocked"
    assert readiness.merge_block is not None
    expected = "your-decision" if readiness.merge_block.reason in _IN_GITHUB_BLOCKS else "needs-attention"
    assert _situation(readiness.progress) == expected


def test_provider_backoff_on_a_chat_step_is_ready_for_next_step(tmp_path: Path) -> None:
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
    assert _situation(readiness.progress) == "ready-for-next-step"
    assert readiness.progress.next_eligible_at == readiness.next_eligible_at


def test_pause_and_resume_project_paused_then_restore(tmp_path: Path) -> None:
    now = [_iso(_real_now())]
    application, *_rest = _progress_portfolio(tmp_path, {"change-a": DeliveryStage.PLANNING}, now)
    digest = application.get_change("change-a").frontier_digest

    paused = application.set_change_intent(
        DeliveryChangeIntent(
            change_id="change-a", kind=DeliveryChangeIntentKind.DEFER, expected_frontier_digest=digest, reason="Hold"
        )
    )

    assert _situation(_group(application).progress) == "paused"
    assert {_situation(item.readiness.progress) for item in _group(application).items} == {"paused"}
    application.set_change_intent(
        DeliveryChangeIntent(
            change_id="change-a", kind=DeliveryChangeIntentKind.RESUME, expected_frontier_digest=paused.frontier_digest
        )
    )
    assert _situation(_group(application).progress) == "ready-for-next-step"


def test_accepted_completion_projects_done(tmp_path: Path) -> None:
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
    assert (_situation(change.readiness.progress), _situation(change.detail.change_progress)) == ("done", "done")
    assert change.readiness.progress.target_sync == "unnecessary"


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
    assert _situation(ready.detail.card.readiness.progress) == "done"
    assert _situation(ready.detail.change_progress) == "ready-for-next-step"
    assert _group(application).progress == ready.detail.change_progress

    acquired = application.acquire_change_action(_continuation_request(application))
    assert acquired.launch is not None, acquired
    assert acquired.launch.outcome_id == "OUT-002"
    probe.states[_HOST] = issuer
    expected = "with-agent" if issuer == "alive" else "needs-attention"

    held = application.get_change("change-a")
    assert held.detail.card.work_item_id == "OUT-001"
    assert _situation(held.detail.card.readiness.progress) == "done"
    assert _situation(held.detail.change_progress) == expected
    assert _situation(_group(application).progress) == expected
    assert _card(application, "outcome:OUT-002").next_step == "Claimed by Builder"


def test_contained_builder_transition_wins_change_activity(tmp_path: Path) -> None:
    application, runtimes, _coordinator, _state_root, _launch, transition = builder_transition_case(tmp_path, "block")
    retain_contained_transition(application, "change-a", transition)
    snapshot = application._delivery_snapshot(runtimes["change-a"])
    contained = _card(application, "outcome:OUT-001")
    assert contained.readiness.reason_code == "builder-transition-contained"
    assert _situation(contained.readiness.progress) == "needs-attention"
    running = contained.model_copy(
        update={
            "item_key": "outcome:OUT-002",
            "work_item_id": "OUT-002",
            "readiness": contained.readiness.model_copy(update={"status": "running", "reason_code": "active-custody"}),
        }
    )

    assert application._change_activity_card(snapshot, (running, contained)) == contained
    assert application.get_change("change-a").detail.change_progress == contained.readiness.progress


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
    assert first.readiness.reason_code == "dependency-wait"
    assert first.readiness.progress == DeliveryProgress(
        situation="waiting-on-dependency",
        headline="Waiting for OUT-002 to complete.",
        waiting_on="outcome",
        waiting_on_id="OUT-002",
    )
    sibling = _card(application, "outcome:OUT-002").readiness.progress
    assert _situation(sibling) == "ready-for-next-step"
    assert _group(application).progress == sibling
    assert application.get_change("change-a").detail.change_progress == sibling

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
    assert _situation(_card(application, "outcome:OUT-002").readiness.progress) == "needs-attention"
    assert application._change_activity_card(snapshot, cards).work_item_id == "OUT-001"
    assert _situation(_group(application).progress) == "waiting-on-dependency"


# Negative scenarios.


def test_unreadable_retry_ledger_needs_attention(tmp_path: Path) -> None:
    now = [_iso(_real_now())]
    application, _runtimes, _coordinator, state_root, _probe = _progress_portfolio(
        tmp_path, {"change-a": DeliveryStage.PLANNING}, now
    )
    summary = RetryLedger(state_root, "change-a").summary_path
    summary.parent.mkdir(parents=True, exist_ok=True)
    summary.write_bytes(b"{")

    readiness = _card(application, "outcome:OUT-001").readiness
    assert (readiness.reason_code, _situation(readiness.progress)) == ("retry-ledger-unavailable", "needs-attention")


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


def test_portfolio_always_projects_one_situation_and_no_start_labels(tmp_path: Path) -> None:
    now = [_iso(_real_now())]
    application, *_rest = _progress_portfolio(
        tmp_path, {"change-a": DeliveryStage.PLANNING, "change-b": DeliveryStage.IMPLEMENTATION}, now
    )
    application.acquire_change_action(_continuation_request(application, "change-b"))

    for group in application.list_work_item_groups():
        assert group.progress is not None
        for item in group.items:
            assert item.readiness.progress is not None
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

# reason -> (status, operation, executable, frontier lifecycle field, expected situation)
_EXPECTED: dict[str, tuple[str, WorkItemActionKind | None, bool, str | None, DeliverySituation]] = {
    "ready": ("ready", _START, True, None, "ready-for-next-step"),
    "design-attention": ("blocked", None, False, None, "your-decision"),
    "active-custody": ("running", None, False, None, "with-agent"),
    "builder-transition-contained": ("blocked", None, False, None, "needs-attention"),
    "retry-transition-contained": ("blocked", None, False, None, "needs-attention"),
    "finalization-failed": ("blocked", None, False, None, "needs-attention"),
    "claim-activation-failed": ("blocked", None, False, None, "needs-attention"),
    "coordination-unavailable": ("unavailable", None, False, None, "needs-attention"),
    "execution-occupancy-unavailable": ("unavailable", None, False, None, "needs-attention"),
    "engine-action-pending": ("running", None, False, None, "ready-for-next-step"),
    "engine-action-blocked": ("blocked", None, False, None, "needs-attention"),
    "engine-action-interrupted": ("blocked", None, False, None, "needs-attention"),
    "engine-action-failed": ("blocked", None, False, None, "needs-attention"),
    "engine-action-incomplete": ("blocked", None, False, None, "needs-attention"),
    "target-sync-required": ("waiting", None, False, None, "ready-for-next-step"),
    "claim-custody-unreconciled": ("blocked", None, False, None, "needs-attention"),
    "runtime-unavailable": ("unavailable", None, False, None, "needs-attention"),
    "dependency-wait": ("waiting", None, False, None, "waiting-on-dependency"),
    "request-action": ("ready", WorkItemActionKind.ANSWER_REQUEST, True, None, "needs-attention"),
    "change-paused": ("blocked", None, False, "change_deferral", "paused"),
    "change-terminal": ("complete", None, False, "change_completion", "done"),
    "outcome-complete": ("complete", None, False, None, "done"),
    "task-incomplete": ("waiting", None, False, None, "waiting-on-dependency"),
    "workspace-inspection-failed": ("unavailable", None, False, None, "needs-attention"),
    "workspace-dirty": ("blocked", None, False, None, "needs-attention"),
    "workspace-preflight-failed": ("blocked", None, False, None, "needs-attention"),
    "settled-attention-target-drift": ("blocked", None, False, None, "needs-attention"),
    "review-repair": ("blocked", None, False, None, "ready-for-next-step"),
    "publication-wait": ("waiting", None, False, None, "waiting-on-dependency"),
    "checkpoint-pending": ("waiting", None, False, None, "waiting-on-delivery"),
    "report-store-unavailable": ("ready", _START, True, None, "ready-for-next-step"),
    "retry-backoff": ("waiting", WorkItemActionKind.SYNC_TARGET, False, None, "ready-for-next-step"),
    "retry-exhausted": ("blocked", None, False, None, "needs-attention"),
    "acceptance-wait": ("waiting", WorkItemActionKind.OBSERVE_ACCEPTANCE, False, None, "your-decision"),
    "retry-containment": ("blocked", None, False, None, "needs-attention"),
    "retry-ledger-unavailable": ("unavailable", None, False, None, "needs-attention"),
    "worker-stall-wait": ("waiting", None, False, None, "waiting-on-delivery"),
    "merge-approval-required": ("waiting", None, False, None, "your-decision"),
    "merge-checking": ("waiting", None, False, None, "waiting-on-github"),
    "merge-blocked": ("blocked", None, False, None, "needs-attention"),
    "target-commit-missing": ("blocked", None, False, None, "needs-attention"),
    "checks-running": ("waiting", None, False, None, "waiting-on-github"),
    "provider-unavailable": ("waiting", None, False, None, "waiting-on-github"),
    "merge-in-progress": ("waiting", None, False, None, "waiting-on-github"),
    "merge-response-unknown": ("blocked", None, False, None, "needs-attention"),
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

    assert progress.situation == expected
    assert progress.headline.strip()


@pytest.mark.parametrize(
    ("issuer", "expected"),
    [
        (None, "with-agent"),
        ("alive", "with-agent"),
        ("gone", "ready-for-next-step"),
        ("unknown", "needs-attention"),
    ],
)
def test_running_custody_maps_issuer_evidence(issuer: str | None, expected: str) -> None:
    progress = derive_delivery_progress(
        _readiness("running", "active-custody"), _outcome_card(), _FRONTIER, issuer_state=issuer, holder="Builder"
    )
    assert progress.situation == expected
    if expected == "with-agent":
        assert (progress.headline, progress.waiting_on) == ("Builder holds this step.", "agent")


def test_capacity_and_retries_select_their_situations() -> None:
    ready = _readiness("ready", "ready", operation=_START, executable=True)
    capacity = derive_delivery_progress(ready, _outcome_card(), _FRONTIER, at_capacity=True)
    assert (capacity.situation, capacity.waiting_on) == ("waiting-on-dependency", "change")
    assert derive_delivery_progress(ready, _outcome_card(), _FRONTIER).situation == "ready-for-next-step"
    human = _readiness("ready", "ready", operation=_START, executable=True, next_actor=WorkItemNextActor.YOU)
    assert derive_delivery_progress(human, _outcome_card(), _FRONTIER).headline == "Next: Run."
    observe = _readiness("waiting", "retry-backoff", operation=WorkItemActionKind.OBSERVE_ACCEPTANCE).model_copy(
        update={"next_eligible_at": "2026-08-04T00:05:00Z"}
    )
    retrying = derive_delivery_progress(observe, _outcome_card(), _FRONTIER)
    assert (retrying.situation, retrying.waiting_on, retrying.next_eligible_at) == (
        "retrying-automatically",
        "delivery",
        "2026-08-04T00:05:00Z",
    )
    backoff = _readiness("waiting", "retry-backoff", operation=_START)
    assert derive_delivery_progress(backoff, _outcome_card(), _FRONTIER).situation == "ready-for-next-step"
    executable_checkpoint = _readiness(
        "ready", "checkpoint-pending", operation=WorkItemActionKind.RECONCILE_CHECKPOINT, executable=True
    )
    assert derive_delivery_progress(executable_checkpoint, _outcome_card(), _FRONTIER).situation == (
        "ready-for-next-step"
    )


def test_decision_requests_are_your_decision_and_action_requests_need_attention() -> None:
    readiness = _readiness("ready", "request-action", operation=WorkItemActionKind.ANSWER_REQUEST, executable=True)

    def request(kind: DeliveryRequestKind) -> DeliveryRequest:
        options = (DeliveryRequestOption(option_id="a", label="A"),) if kind is DeliveryRequestKind.DECISION else ()
        return DeliveryRequest(
            request_id="REQ-1", kind=kind, outcome_id="OUT-001", summary="Pick a store", options=options
        )

    decision = derive_delivery_progress(
        readiness, _outcome_card(), _FRONTIER, request=request(DeliveryRequestKind.DECISION)
    )
    action = derive_delivery_progress(
        readiness, _outcome_card(), _FRONTIER, request=request(DeliveryRequestKind.ACTION)
    )
    assert (decision.situation, decision.headline) == ("your-decision", "Decide: Pick a store")
    assert (action.situation, action.headline) == ("needs-attention", "Action needed: Pick a store")


def _publication(**updates: object) -> WorkItemCardView:
    return _outcome_card(
        item_key="publication",
        scope=WorkItemScope.CHANGE_PUBLICATION,
        stage=None,
        publication_phase=WorkItemPublicationPhase.AWAITING_MERGE,
        action=WorkItemAction(kind=WorkItemActionKind.OBSERVE_ACCEPTANCE, label="Check merge status"),
    ).model_copy(update=updates)


def test_awaiting_merge_publication_is_your_decision_unless_conflicted() -> None:
    publication = _publication()
    request = _readiness(
        "ready",
        "request-action",
        operation=WorkItemActionKind.OBSERVE_ACCEPTANCE,
        executable=True,
        next_actor=WorkItemNextActor.YOU,
    )
    awaiting = derive_delivery_progress(request, publication, _FRONTIER)
    assert (awaiting.situation, awaiting.target_sync) == ("your-decision", "unnecessary")
    conflicted = publication.model_copy(
        update={"action": publication.action.model_copy(update={"command": "/resolve-target-conflict change-a"})}
    )
    assert derive_delivery_progress(request, conflicted, _FRONTIER).situation == "ready-for-next-step"
    exhausted = _readiness("blocked", "retry-exhausted")
    assert derive_delivery_progress(exhausted, publication, _FRONTIER).situation == "needs-attention"
    merged = derive_delivery_progress(request, publication, _FRONTIER, merged_unrecorded=True)
    assert (merged.situation, merged.target_sync) == ("waiting-on-delivery", "unavailable")


@pytest.mark.parametrize(
    ("block", "situation", "target_sync"),
    [
        (MergeBlockReason.CONFLICTS, "ready-for-next-step", "required"),
        (MergeBlockReason.BEHIND, "ready-for-next-step", "required"),
        (MergeBlockReason.CAPABILITY_UNAVAILABLE, "your-decision", "unnecessary"),
        (MergeBlockReason.CHECKS_FAILED, "needs-attention", "unavailable"),
    ],
)
def test_merge_blocks_select_situation_and_target_sync(
    block: MergeBlockReason, situation: str, target_sync: str
) -> None:
    readiness = _readiness("blocked", "merge-blocked").model_copy(
        update={"merge_block": MergeBlock(reason=block, detail="blocked")}
    )
    progress = derive_delivery_progress(readiness, _publication(), _FRONTIER)
    assert (progress.situation, progress.target_sync) == (situation, target_sync)


def test_pre_finalization_sync_prerequisite_is_required() -> None:
    """Production keeps reason ``ready`` and swaps in the executable sync action (``_card_readiness``)."""
    readiness = _readiness("ready", "ready", operation=WorkItemActionKind.SYNC_TARGET, executable=True)
    publication = _publication(publication_phase=WorkItemPublicationPhase.READY_FOR_FINALIZATION)
    progress = derive_delivery_progress(readiness, publication, _FRONTIER)
    assert (progress.situation, progress.target_sync) == ("ready-for-next-step", "required")
    assert progress.headline == (
        "Run the prompt in Copilot Chat to merge the latest target into this Change; "
        "a conflict stops there for you to resolve."
    )


@pytest.mark.parametrize(
    ("paths", "where"),
    [(("web/Page.tsx",), " in web/Page.tsx"), (("a.py", "b.py"), " in 2 files"), ((), "")],
)
def test_preserved_sync_conflict_names_its_resolution_route(paths: tuple[str, ...], where: str) -> None:
    failed = _readiness("blocked", "engine-action-failed", next_actor=WorkItemNextActor.YOU)
    publication = _publication(publication_phase=WorkItemPublicationPhase.READY_FOR_FINALIZATION)
    progress = derive_delivery_progress(failed, publication, _FRONTIER, sync_conflict_paths=paths)
    assert (progress.situation, progress.waiting_on, progress.target_sync) == (
        "ready-for-next-step",
        "you",
        "unavailable",
    )
    assert progress.headline == (
        f"Merging the latest target stopped on a conflict{where}; resolve it with /resolve-target-conflict."
    )
    unrelated = derive_delivery_progress(failed, publication, _FRONTIER)
    assert unrelated.situation == "needs-attention"
    assert unrelated.headline == "A Delivery step failed; inspect the Change."
    outcome = derive_delivery_progress(failed, _outcome_card(), _FRONTIER, sync_conflict_paths=paths)
    assert (outcome.headline, outcome.target_sync) == (progress.headline, None)
    exhausted = _readiness("blocked", "retry-exhausted")
    other = derive_delivery_progress(exhausted, _outcome_card(), _FRONTIER, sync_conflict_paths=paths)
    assert other.situation == "needs-attention"


def test_resync_after_abort_says_it_merges_the_same_target_again() -> None:
    target = "a" * 40
    readiness = _readiness("ready", "ready", operation=WorkItemActionKind.SYNC_TARGET, executable=True).model_copy(
        update={"basis": DeliveryReadinessBasis(target_head=target)}
    )
    publication = _publication(publication_phase=WorkItemPublicationPhase.READY_FOR_FINALIZATION)
    again = derive_delivery_progress(readiness, publication, _FRONTIER, aborted_sync_target=target)
    assert (again.situation, again.target_sync) == ("ready-for-next-step", "required")
    assert again.headline.startswith("You aborted merging this target;")
    moved = derive_delivery_progress(readiness, publication, _FRONTIER, aborted_sync_target="b" * 40)
    assert moved.headline.startswith("Run the prompt in Copilot Chat to merge the latest target")
    waiting = derive_delivery_progress(readiness, publication, _FRONTIER, aborted_sync_target=target, at_capacity=True)
    assert waiting.situation == "waiting-on-dependency"
    backoff = readiness.model_copy(
        update={
            "status": "waiting",
            "reason_code": "retry-backoff",
            "executable": False,
            "action": None,
            "next_eligible_at": "2026-08-04T00:00:01Z",
        }
    )
    later = derive_delivery_progress(backoff, publication, _FRONTIER, aborted_sync_target=target)
    assert (later.situation, later.next_eligible_at) == ("ready-for-next-step", "2026-08-04T00:00:01Z")
    assert later.headline == (
        "You aborted merging this target; running the prompt once the retry time passes merges it again and "
        "keeps any conflict for you to resolve."
    )


def test_merge_attempt_waits_on_github_since_release_and_holds_target_sync() -> None:
    attempt = MergeAttemptSummary(
        approval_id="a" * 64,
        state="released",
        approved_head="b" * 40,
        pr_url="https://github.com/o/r/pull/1",
        released_at="2026-08-04T00:00:00Z",
    )
    readiness = _readiness("waiting", "merge-in-progress").model_copy(update={"merge_attempt": attempt})
    progress = derive_delivery_progress(readiness, _publication(), _FRONTIER)
    assert (progress.situation, progress.waiting_on, progress.since, progress.target_sync) == (
        "waiting-on-github",
        "github",
        "2026-08-04T00:00:00Z",
        "unavailable",
    )


def test_pause_request_shows_pausing_until_drained() -> None:
    running = _readiness("running", "active-custody")
    assert derive_delivery_progress(running, _outcome_card(), _FRONTIER, pause_requested=True).situation == "pausing"
    drained = derive_delivery_progress(running, _outcome_card(), _FRONTIER, pause_requested=True, pause_drained=True)
    assert drained.situation == "paused"


def test_abandonment_and_completion_are_terminal() -> None:
    complete = _readiness("complete", "change-terminal")
    abandoned = _FRONTIER.model_copy(update={"change_abandonment": _PRESENT})
    assert derive_delivery_progress(complete, _outcome_card(), abandoned).situation == "abandoned"
    assert derive_delivery_progress(complete, _outcome_card(), _FRONTIER).situation == "done"


def test_every_input_combination_projects_one_valid_situation() -> None:
    reasons = get_args(DeliveryReadinessReason)
    statuses = ("ready", "running", "waiting", "blocked", "unavailable", "complete")
    frontiers = (
        _FRONTIER,
        *(_FRONTIER.model_copy(update={field: _PRESENT}) for field in ("change_deferral", "change_completion")),
    )
    cards = (_outcome_card(), _publication())
    emitted = set()
    for reason, status, frontier, card, issuer, capacity in itertools.product(
        reasons, statuses, frontiers, cards, (None, "alive", "gone", "unknown"), (False, True)
    ):
        executable = status == "ready"
        readiness = _readiness(status, reason, operation=_START if executable else None, executable=executable)
        progress = derive_delivery_progress(readiness, card, frontier, issuer_state=issuer, at_capacity=capacity)
        assert progress.headline.strip()
        assert (progress.target_sync is None) == (card.scope is WorkItemScope.OUTCOME)
        emitted.add(progress.situation)
    assert emitted <= set(get_args(DeliverySituation))


# Server-derived Pause availability (F1/F2): each fixture's projection must equal defer acceptance.


class _Crash(BaseException):
    """Process death between two owner steps; no handler in the owner may observe it."""


def _quiescent_planning(tmp_path: Path):
    application, _runtimes, _coordinator, state_root, _probe = _progress_portfolio(
        tmp_path, {"change-a": DeliveryStage.PLANNING}, [_iso(_real_now())]
    )
    return application, state_root, None


def _planner_claim(tmp_path: Path):
    application, _runtimes, _coordinator, state_root, probe = _progress_portfolio(
        tmp_path, {"change-a": DeliveryStage.PLANNING}, [_iso(_real_now())]
    )
    _acquire_planning_claim(application)
    probe.states[_HOST] = "alive"
    assert _card(application, "outcome:OUT-001").readiness.reason_code == "active-custody"
    return application, state_root, "step-in-progress"


def _stalled_worker(tmp_path: Path):
    application, _runtimes, _coordinator, state_root, probe = _progress_portfolio(
        tmp_path, {"change-a": DeliveryStage.PLANNING}, [_iso(_real_now())]
    )
    _acquire_planning_claim(application)
    probe.states[_HOST] = "gone"
    probe.processes = ("node",)
    assert _card(application, "outcome:OUT-001").readiness.reason_code == "worker-stall-wait"
    return application, state_root, "step-in-progress"


def _contained_builder_transition(tmp_path: Path):
    application, _runtimes, _coordinator, state_root, _launch, transition = builder_transition_case(tmp_path, "block")
    retain_contained_transition(application, "change-a", transition)
    assert _card(application, "outcome:OUT-001").readiness.reason_code == "builder-transition-contained"
    return application, state_root, "step-in-progress"


def _active_finalizer(tmp_path: Path):
    application, _runtimes, _coordinator, state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.COMPLETED})
    acquired = application.acquire_change_action(_continuation_request(application))
    assert acquired.finalization is not None, acquired
    return application, state_root, "finalizer-custody"


def _masked_finalizer(tmp_path: Path):
    """F1: a reported Finalizer failure with an unreadable retry ledger still holds active custody."""
    application, _runtimes, coordinator, state_root = _portfolio(tmp_path, {"change-a": DeliveryStage.COMPLETED})
    acquired = application.acquire_change_action(_continuation_request(application))
    assert acquired.finalization is not None, acquired
    attempt = acquired.finalization.attempt
    application.report_finalization_failure(_failure_request(application, attempt_key=attempt.writer.attempt_id))
    summary = RetryLedger(state_root, "change-a").summary_path
    summary.parent.mkdir(parents=True, exist_ok=True)
    summary.write_bytes(b"{")
    assert _card(application, "publication").readiness.reason_code == "retry-ledger-unavailable"
    assert coordinator.show("change-a").writer.kind == "finalize"
    return application, state_root, "finalizer-custody"


def _passive_finalizer_attention(tmp_path: Path):
    """F2: settled Finalizer attention is passive custody that the defer intent explicitly accepts."""
    now = ["2026-08-04T00:00:00Z"]
    application, _runtimes, coordinator, state_root = _portfolio(
        tmp_path, {"change-a": DeliveryStage.COMPLETED}, clock=lambda: now[0]
    )
    acquired = application.acquire_change_action(_continuation_request(application))
    assert acquired.finalization is not None, acquired
    attempt = acquired.finalization.attempt
    report = application.report_finalization_failure(
        _failure_request(application, attempt_key=attempt.writer.attempt_id)
    )
    application.settle_finalizer_invocation(_finalizer_settlement(application, attempt, report))
    FinalizationReportStore(state_root, "change-a").retire(attempt.exact_head, attempt.contract_digest)
    now[0] = "2026-08-04T00:00:01Z"
    assert coordinator.show("change-a").writer.kind == "finalization-attention"
    assert _card(application, "publication").readiness.reason_code == "finalization-failed"
    return application, state_root, None


def _reservation_only_retry_containment(tmp_path: Path):
    """F2: a crash after the retry reservation but before continuation custody leaves no custody."""
    application, _runtime, _provider, _state, _head, state_root = _awaiting_acceptance_fixture(
        tmp_path, mark_ready=False
    )
    assert application.acquire_change_action(_continuation_request(application)).kind == "reconciled"
    with (
        patch.object(application, "_register_recovery_invocation", side_effect=_Crash),
        pytest.raises(_Crash),
    ):
        application.acquire_change_action(_continuation_request(application))
    assert RetryLedger(state_root, "change-a").read().episodes[0].last_status == "reserved"
    assert application._workspace_manager.show("change-a").continuation_action is None
    assert _card(application, "publication").readiness.reason_code == "retry-containment"
    return application, state_root, None


def _pending_engine_action(tmp_path: Path):
    application, _runtime, _provider, _state, _head, state_root = _awaiting_acceptance_fixture(
        tmp_path, mark_ready=False
    )
    _engine_action(application)
    assert application.get_change("change-a").readiness.reason_code == "engine-action-pending"
    return application, state_root, "step-in-progress"


def _interrupted_engine_action(tmp_path: Path):
    application, _runtime, _provider, _state, _head, state_root = _awaiting_acceptance_fixture(
        tmp_path, mark_ready=False
    )
    action = _engine_action(application)
    with application._coordinator.continuation_execution(action):
        application._coordinator.start_continuation_action(action)
    assert _execute_engine(application, action).reason_code == "engine-action-interrupted"
    assert application.get_change("change-a").readiness.reason_code == "engine-action-interrupted"
    return application, state_root, "step-in-progress"


_PAUSE_FIXTURES = {
    "quiescent-planning": _quiescent_planning,
    "planner-claim": _planner_claim,
    "stalled-worker": _stalled_worker,
    "contained-builder-transition": _contained_builder_transition,
    "active-finalizer": _active_finalizer,
    "masked-finalizer": _masked_finalizer,
    "passive-finalizer-attention": _passive_finalizer_attention,
    "reservation-only-retry-containment": _reservation_only_retry_containment,
    "pending-engine-action": _pending_engine_action,
    "interrupted-engine-action": _interrupted_engine_action,
}


def _pause_views(application: PortfolioApplication) -> set[tuple[bool, str | None]]:
    group = _group(application)
    views = [group, application.get_change("change-a").detail]
    views.extend(application.show_work_item_view("change-a", item.item_key) for item in group.items)
    return {(view.pause_available, view.pause_unavailable_reason) for view in views}


def _pause_admitted(application: PortfolioApplication) -> str | None:
    """Return the N09-A2 admission outcome: ``deferral`` (converted), ``request`` (draining) or None."""
    runtime = application._runtimes["change-a"]
    before = runtime.frontier_bytes()
    try:
        result = application.set_change_intent(
            DeliveryChangeIntent(
                change_id="change-a",
                kind=DeliveryChangeIntentKind.DEFER,
                expected_frontier_digest=hashlib.sha256(before).hexdigest(),
                reason="Pause availability probe",
            )
        )
    except RuntimeError, OSError:
        assert runtime.frontier_bytes() == before
        assert runtime.change_deferral() is None
        return None
    if runtime.change_deferral() is not None:
        assert result.receipt == runtime.change_deferral()
        return "deferral"
    assert runtime.frontier_bytes() == before
    assert result.receipt == application._coordinator.pause_request("change-a")
    return "request"


@pytest.mark.parametrize("fixture", sorted(_PAUSE_FIXTURES))
def test_pause_is_available_under_any_custody_and_drains_or_converts(tmp_path: Path, fixture: str) -> None:
    """N09-A2 §1.11 K1: Pause admits under every custody; only drained custody converts at once."""
    application, state_root, custody = _PAUSE_FIXTURES[fixture](tmp_path)
    before = _record_tree(state_root)

    observed = _pause_views(application)

    assert _record_tree(state_root) == before
    assert observed == {(True, None)}
    expected = "deferral" if custody is None else "request"
    assert _pause_admitted(application) == expected
    if expected == "deferral":
        assert _pause_views(application) == {(False, "change-inactive")}
    else:
        assert _pause_views(application) == {(False, "pause-requested")}
        assert _group(application).pause_requested is True
        assert application.get_change("change-a").pause_requested is True


def test_unreadable_coordination_refuses_pause(tmp_path: Path) -> None:
    application, state_root, _custody = _quiescent_planning(tmp_path)
    snapshot = application._delivery_snapshot(application._runtimes["change-a"])
    (state_root / "coordination/changes/change-a.json").write_bytes(b"{")
    assert application._pause_unavailable_reason(snapshot) == "state-unavailable"
    assert _pause_admitted(application) is None


def test_recovery_fence_does_not_refuse_pause_admission(tmp_path: Path) -> None:
    application, *_rest = _quiescent_planning(tmp_path)
    snapshot = application._delivery_snapshot(application._runtimes["change-a"])
    with patch.object(
        application._coordinator, "require_no_pending_recovery", side_effect=DeliveryWorkerExclusionRequiredError
    ):
        assert application._pause_unavailable_reason(snapshot) is None
        assert _pause_admitted(application) == "deferral"
