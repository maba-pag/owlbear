"""#718: a running step's stage from its sessions' events, as the SDK runtime journals them, without a model."""

from datetime import UTC, datetime, timedelta

import pytest

from owlbear_delivery_next.change_contracts.models import VISUAL, Change, Exit, Outcome, Step, StepKind
from owlbear_delivery_next.change_flow import step_stages

START = datetime(2026, 11, 2, 12, 0, 0, 400000, tzinfo=UTC)  # a step starts within a second; events have seconds


def at(seconds: float) -> str:
    return (START + timedelta(seconds=seconds)).isoformat(timespec="seconds")


def ev(s: float, event: str, sid: str = "b1", role: str = "builder", **more) -> dict:
    """One event as ``_Step.log`` writes it once the session opened."""
    return {"at": at(s), "session": sid, "role": role, "event": event, **more}


def opened(s: float, sid: str = "b1", role: str = "builder") -> dict:
    return ev(s, "session", sid, role, id=sid, resumed=False)


def result(s: float, *, ok: bool, tool: str = "submit_result", sid: str = "b1", role: str = "builder") -> dict:
    return ev(s, "tool", sid, role, tool=tool, accepted=ok, errors=[] if ok else ["lint"])


def ended(s: float, sid: str = "b1", role: str = "builder") -> dict:
    return ev(s, "ended", sid, role, ending="result")


def step(kind: StepKind, task: str | None = "t1", started: datetime | None = START, **fields) -> Change:
    return Change(slug="c1", step=Step(kind=kind, task=task, started_at=started), **fields)


BUILD, PLAN, CHECK = step(StepKind.BUILD), step(StepKind.PLAN, None), step(StepKind.CHECK, VISUAL)
PICKED = [opened(3, "p1", "picker"), result(9, ok=True, sid="p1", role="picker")]  # a picker's own submit_result
PREVIOUS = [opened(-30, "r0", "reviewer"), result(-1, ok=True, sid="r0", role="reviewer"), ended(0, "r0", "reviewer")]
CHALLENGED = Outcome(exit=Exit.RETRY, reason="plan challenge: …", challenged=True, at=START)


@pytest.mark.parametrize(
    ("change", "events", "own", "stage"),
    [
        (BUILD, [], "builder", "starting"),
        (BUILD, [{"at": at(1), "event": "pids", "session": "b1", "pids": {"9": 1.0}}], "builder", "starting"),
        (BUILD, [*PREVIOUS, {"at": at(0), "event": "step", "session": "r0", "kind": "review"}], "builder", "starting"),
        (BUILD, [opened(1)], "builder", None),
        (BUILD, [opened(1), ev(5, "tool", tool="lookup_decisions", accepted=True)], "builder", None),
        (BUILD, [opened(1), result(20, ok=False)], "builder", "fixing its refused result"),
        (BUILD, [opened(1), result(20, ok=False), result(30, ok=True)], "builder", "handing in its result"),
        (BUILD, [opened(1), result(20, ok=True), ended(25)], "builder", "recording the result"),
        (BUILD, [opened(1), *PICKED], "builder", "checking decisions"),
        (BUILD, [opened(1), *PICKED, ended(10, "p1", "picker")], "builder", None),
        (BUILD, [opened(1), ev(2, "tool", tool="ask_question", accepted=True), ended(3)], "builder",
         "recording the result"),
        (step(StepKind.REVIEW), [opened(1, "r1", "reviewer"), result(9, ok=True, sid="r1", role="reviewer")],
         "reviewer", "handing in its verdict"),
        (step(StepKind.REVIEW), [opened(1, "r1", "reviewer"), result(9, ok=False, sid="r1", role="reviewer")],
         "reviewer", "correcting its refused result"),
        (PLAN, [opened(1, "pl", "planner"), result(9, ok=True, sid="pl", role="planner")], "planner",
         "handing in the plan"),
        (PLAN, [opened(1, "pl", "planner"), result(9, ok=True, sid="pl", role="planner"), ended(10, "pl", "planner"),
                opened(12, "ch", "challenger")], "planner", "challenging the plan"),
        (step(StepKind.PLAN, None, outcome=CHALLENGED), [opened(1, "pl", "planner")], "planner",
         "revising for the challenge's findings"),
        (step(StepKind.SHAPE, None), [opened(1, "p1", "picker")], "reviewer", "checking decisions"),
        (step(StepKind.SHAPE, None), [opened(1, "ch", "challenger")], "reviewer", "challenging the brief"),
        (BUILD, [ev(2, "tool", sid="c2", role="challenger", tool="lookup_decisions", accepted=True)], "builder",
         "challenging"),  # a run whose opening the store trimmed keeps its role
        (step(StepKind.BUILD, "curate"), [opened(1, "tc", "test-curator")], "builder", "curating the tests"),
        (CHECK, [opened(1, "pr", "preparer")], "preparer", None),
        (CHECK, [opened(1, "v1", "reviewer"), opened(1, "d1", "design-judge"), ended(40, "d1", "design-judge")],
         "preparer", "judging: 1 done, 1 running"),
        (step(StepKind.TESTS), [opened(1, "s1", "test-reviewer"), opened(1, "s2", "test-reviewer"),
                                ended(30, "s1", "test-reviewer")], "test reviewer", "reviewing tests: 1 running"),
        (step(StepKind.BUILD, started=None), [opened(1)], "builder", None),
        (step(StepKind.FOLLOW, None), [opened(1)], "delivery", None),
    ],
)  # fmt: skip
def test_the_stage_follows_the_steps_own_sessions(change, events, own, stage):
    assert step_stages.of(change, events, own) == stage


def test_a_session_resumed_for_the_step_counts_its_new_run_only():
    """An answer or a repair chance resumes the session under its id: its run before this step no longer counts."""
    before = [opened(-300), ev(-200, "tool", tool="ask_question", accepted=True), ended(-199)]
    assert step_stages.of(BUILD, before, "builder") == "starting"
    resumed = [*before, ev(2, "session", id="b1", resumed=True)]
    assert step_stages.of(BUILD, resumed, "builder") is None
    assert step_stages.of(BUILD, [*resumed, result(9, ok=False)], "builder") == "fixing its refused result"
