"""Built-in subagents (TD-129): monitoring per subagent and the experiment's one allowed `explore`, by event replay."""

import dataclasses
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from owlbear_delivery_next.change_contracts.models import Brief, Change, ErrorKind, Exit, StepKind
from owlbear_delivery_next.change_contracts.permissions import Policy
from owlbear_delivery_next.change_contracts.tools import Worktree
from owlbear_delivery_next.local_system.processes import Termination
from owlbear_delivery_next.runtimes import sdk_adapter, session_result
from owlbear_delivery_next.runtimes.session_result import Run
from owlbear_delivery_next.settings import config
from owlbear_delivery_next.state_store.store import Lock, Store
from owlbear_delivery_next.workflow_steps import sessions

PLANNER, HELPER = "claude-opus-5.5", "claude-haiku-5.5"


def step(
    tmp_path, *, kind: StepKind = StepKind.PLAN, explore: bool = True, role: str = "", limit: float | None = None
) -> sdk_adapter._Step:
    log: list[dict] = []
    cfg = sdk_adapter.Session(
        kind, tmp_path, "s1", "m", resume=False, policy=Policy(tmp_path), observe=lambda: Worktree("a", "a"),
        checks=(), model=PLANNER, explore=explore, role=role, journal=sdk_adapter.Journal(event=log.append),
        credit_limit=limit,
    )  # fmt: skip
    st = sdk_adapter._Step(cfg, SimpleNamespace(call_soon_threadsafe=lambda *_: None))  # noqa: SLF001
    st.events = log
    return st


def event(kind: str, **data: object) -> SimpleNamespace:
    return SimpleNamespace(type=SimpleNamespace(value=kind), data=SimpleNamespace(**data))


def started(cid: str, name: str = "explore", model: str = HELPER) -> SimpleNamespace:
    return event("subagent.started", tool_call_id=cid, agent_name=name, model=model)


def usage(parent: str | None, nano: float | None, model: str = HELPER) -> SimpleNamespace:
    billed = None if nano is None else SimpleNamespace(total_nano_aiu=nano)
    return event("assistant.usage", model=model, parent_tool_call_id=parent, is_auto=False, copilot_usage=billed)


def test_an_enabled_planner_runs_one_explore_and_each_of_its_calls_is_counted(tmp_path):
    st = step(tmp_path)
    assert "explore" not in st.options()["excluded_builtin_agents"]
    assert "task" in st.options()["custom_agents"][0]["tools"]  # the launcher, or explore can never start (live)
    for ev in (
        started("c1"),
        event("assistant.message", content="", model=HELPER, parent_tool_call_id="c1"),
        usage("c1", 2.5e9),
        usage("c1", 0.5e9),
        event(
            "subagent.completed",
            tool_call_id="c1",
            agent_name="explore",
            model=HELPER,
            total_tokens=900,
            total_tool_calls=4,
            duration=timedelta(seconds=12),
        ),
    ):
        st.on_event(ev)
    assert st.gate.done is False  # nothing voided the step
    (seen,) = st.watch.report()
    assert (seen["agent"], seen["outcome"], seen["tokens"], seen["tool_calls"], seen["seconds"]) == (
        "explore", "completed", 900, 4, 12.0
    )  # fmt: skip
    assert (seen["credits"], seen["credits_known"], seen["calls"], seen["models"]) == (3.0, True, 2, [HELPER])
    assert st.watch.child_models() == {HELPER}  # its model may appear in the session's usage
    assert [e["event"] for e in st.events if e["event"].startswith("subagent")] == ["subagent-started", "subagent"]


def test_a_call_whose_credits_are_not_reported_is_unknown_not_zero(tmp_path):
    st = step(tmp_path)
    st.on_event(started("c1"))
    st.on_event(usage("c1", None))
    (seen,) = st.watch.report()
    assert (seen["credits"], seen["credits_known"], seen["outcome"]) == (0.0, False, "unfinished")


@pytest.mark.parametrize(
    ("events", "detail"),
    [
        ([started("c1"), started("c2")], "explore started while another runs; one at a time"),
        ([started("c1", "general-purpose")], "a subagent started: general-purpose; no subagent may run"),
        ([started("c1", "research")], "a subagent started: research; no subagent may run"),
        ([started("c1", model="auto")], "wrong model: a subagent ran on auto"),
        ([usage("c9", 1e9, PLANNER)], "a subagent ran; no subagent may run"),  # a parent nobody started
    ],
)
def test_anything_beyond_one_explore_still_voids_the_step(tmp_path, events, detail):
    st = step(tmp_path)
    for ev in events:
        st.on_event(ev)
    assert (st.run.ending, st.run.detail) == ("error", detail)


@pytest.mark.parametrize(
    ("kind", "role", "explore"),
    [
        (StepKind.PLAN, "", False),  # the setting is off
        (StepKind.BUILD, "", True),  # never a builder
        (StepKind.REVIEW, "", True),
        (StepKind.REVIEW, "challenger", True),  # nor a judge
        (StepKind.PLAN, "challenger", True),  # a plan challenge runs with the planner's step kind
    ],
)
def test_only_an_enabled_planner_may_start_one(tmp_path, kind, role, explore):
    st = step(tmp_path, kind=kind, explore=explore, role=role)
    assert "explore" in st.options()["excluded_builtin_agents"]
    assert "task" not in st.options()["custom_agents"][0]["tools"]
    st.on_event(started("c1"))
    assert (st.run.ending, st.run.detail) == ("error", "a subagent started: explore; no subagent may run")


def test_a_hard_credit_limit_reaches_the_runtime(tmp_path):
    assert step(tmp_path).options()["session_limits"] is None  # no limit unless an experiment's ledger sets one
    assert step(tmp_path, limit=30.0).options()["session_limits"] == {"max_ai_credits": 30.0}


@pytest.mark.parametrize(
    ("ending", "used", "limit", "expected"),
    [
        ("no-result", 31.14, 30.0, ("credit-limit", "credit limit reached: 31.14 of 30 (ended no-result)")),  # live
        ("deadline", 30.0, 30.0, ("credit-limit", "credit limit reached: 30.00 of 30 (ended deadline: step deadline)")),
        ("no-result", 29.9, 30.0, ("no-result", "")),  # under the limit: an ordinary silent end
        ("no-result", 31.14, None, ("no-result", "")),  # no limit set
        ("no-result", None, 30.0, ("no-result", "")),  # credits unread: nothing is claimed
        ("result", 31.14, 30.0, ("result", "")),  # a result within the last call stands
    ],
)
def test_a_step_ending_silently_at_its_limit_is_reported_as_the_limit(ending, used, limit, expected):
    run = Run("s1", ending=ending, usage={"credits": used}, detail="step deadline" if ending == "deadline" else "")
    session_result.limit_reached(run, limit)
    assert (run.ending, run.detail) == expected


def test_a_reached_limit_stops_for_the_owner_and_is_never_waited_out_as_a_quota():
    run = Run("s1", ending="no-result", usage={"credits": 31.14}, termination=Termination(confirmed=True))
    run.quota = True  # even when the runtime's words also looked like an exhausted quota
    session_result.limit_reached(run, 30.0)
    result = session_result.to_result(run, StepKind.PLAN, datetime(2026, 10, 16, tzinfo=UTC))
    assert (result.exit, result.stop.kind if result.stop else None, result.wake_at) == (
        Exit.STOP, ErrorKind.POLICY, None
    )  # fmt: skip


def test_the_experiment_is_off_by_default_and_a_project_off_overrides_a_global_on():
    assert config.resolve(None, config.Layer()).explore is False
    on = config.GlobalLayer(explore=True)
    assert config.resolve(on, config.Layer()).explore is True
    resolved = config.resolve(on, config.Layer(explore=False))
    assert (resolved.explore, resolved.sources["explore"]) == (False, "project")


def test_the_breakdown_rides_on_the_step_event_and_never_adds_to_the_spend(tmp_path):
    store, change = Store(tmp_path / "store"), Change(slug="c1", brief=Brief(version=1))
    store.write(Lock("c1"), change)
    usage_ = {
        "credits": 4.0,
        "models": {PLANNER: {"credits": 1.0, "tokens": 10}, HELPER: {"credits": 3.0, "tokens": 9}},
    }
    run = Run("s1", "result", usage=usage_, termination=Termination(confirmed=True))
    run = dataclasses.replace(run, subagents=[{"call": "c1", "agent": "explore", "credits": 3.0}])
    sessions.logged(store, Lock("c1"), change, run, {"kind": StepKind.PLAN, "exit": "done"})
    (logged,) = [e for e in store.events("c1") if e.get("event") == "step"]
    assert logged["subagents"] == [{"call": "c1", "agent": "explore", "credits": 3.0}]
    assert store.read("c1").spend.credits == 4.0  # the session's own total, its subagent's share inside it
