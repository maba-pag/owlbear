from datetime import UTC, datetime, timedelta

import pytest

from owlbear_delivery_next.models import (
    Change,
    ErrorKind,
    Exit,
    Intent,
    Outcome,
    Plan,
    Step,
    StepKind,
    Stop,
    Task,
    Waiting,
)
from owlbear_delivery_next.status import Activity, Status, status

NOW = datetime(2026, 10, 10, 12, tzinfo=UTC)
PLAN = Plan(tasks=[Task(id="t1", title="parser"), Task(id="t2", title="rate limiter")])
STOP = Stop(kind=ErrorKind.POLICY, reason="model blocked", action="Allow the model", actor="admin", resume="ok", at=NOW)


def build(**fields) -> Change:
    return Change(slug="c1", plan=PLAN, step=Step(kind=StepKind.BUILD, task="t2"), **fields)


ASKING = build(outcome=Outcome(exit=Exit.ASK, reason="which key?", who="you", at=NOW))
CI = Outcome(
    exit=Exit.PENDING, waiting=Waiting.CI, who="github", reason="2 of 5 running", at=NOW - timedelta(minutes=1)
)
PUBLISHING = Change(slug="c1", step=Step(kind=StepKind.FOLLOW), outcome=CI)
STOPPED = build(stop=STOP, outcome=Outcome(exit=Exit.STOP, who="admin", at=NOW))


@pytest.mark.parametrize("change", [ASKING, PUBLISHING, STOPPED, build()])
def test_host_down_overlays_every_unfinished_change(change):
    assert status(change, Activity(host_up=False), NOW) == Status(
        f"{status(change, Activity(host_up=True), NOW).line.split(' · ')[0]} · Delivery is not running",
        "Start Delivery",
        "you",
    )
    failed = status(change, Activity(host_up=False, start_failure=STOP), NOW)
    assert (failed.action, failed.actor) == ("Allow the model", "admin")


def test_finished_change_is_not_overlaid():
    done = build(finished_at=NOW)
    assert status(done, Activity(host_up=False), NOW).action is None


@pytest.mark.parametrize(
    ("change", "activity", "expected"),
    [
        (ASKING, Activity(host_up=True), Status("Build 2/2 · waiting for you: which key?", "Answer", "you")),
        (STOPPED, Activity(host_up=True), Status("Build 2/2 · stopped: model blocked", "Allow the model", "admin")),
        (
            PUBLISHING,
            Activity(host_up=True),
            Status("Publish · waiting for CI: 2 of 5 running (checked 1 min ago)", None, "github"),
        ),
        (
            build(),
            Activity(host_up=True, runner_alive=True, last_event_at=NOW - timedelta(seconds=40)),
            Status("Build 2/2 · implementing: rate limiter · builder active 40 s ago", None, "delivery"),
        ),
        (
            build(),
            Activity(host_up=True, runner_alive=True, last_event_at=NOW - timedelta(minutes=12)),
            Status("Build 2/2 · implementing: rate limiter · no activity for 12 min", None, "delivery"),
        ),
        (
            build(),
            Activity(host_up=True, holder_pid=4242),
            Status("Build 2/2 · not running: waiting for process 4242 to end", None, "delivery"),
        ),
        (
            build(intent=Intent(hold=True)),
            Activity(host_up=True, runner_alive=True),
            Status("Build 2/2 · holding for your change: finishing build", None, "delivery"),
        ),
        (
            build(outcome=Outcome(exit=Exit.RETRY, denial="docker compose up", at=NOW)),
            Activity(host_up=True, runner_alive=True, last_event_at=NOW),
            Status("Build 2/2 · implementing: rate limiter · last denied: docker compose up", None, "delivery"),
        ),
    ],
)
def test_first_matching_rule_gives_line_action_and_actor(change, activity, expected):
    assert status(change, activity, NOW) == expected


def test_pause_wins_over_a_question():
    paused = ASKING.model_copy(deep=True)
    paused.intent.paused_at = NOW - timedelta(days=2)
    assert status(paused, Activity(host_up=True), NOW) == Status(
        "Build 2/2 · paused by you 2 days ago", "Resume", "you"
    )
