from datetime import UTC, datetime, timedelta

import pytest

from owlbear_delivery_next.change_contracts.models import (
    Change,
    ErrorKind,
    Exit,
    Intent,
    Names,
    Outcome,
    Plan,
    Pullback,
    Step,
    StepKind,
    Stop,
    Task,
    Waiting,
)
from owlbear_delivery_next.change_contracts.spend import ModelSpend, Spend
from owlbear_delivery_next.change_flow.status import Activity, Status, card, status

NOW = datetime(2026, 10, 10, 12, tzinfo=UTC)
PLAN = Plan(tasks=[Task(id="t1", title="parser"), Task(id="t2", title="rate limiter")])
STOP = Stop(kind=ErrorKind.POLICY, reason="model blocked", action="Allow the model", actor="admin", resume="ok", at=NOW)


def build(**fields) -> Change:
    return Change(slug="c1", plan=PLAN, step=Step(kind=StepKind.BUILD, task="t2", started_at=NOW - timedelta(hours=1)),
                  **fields)  # fmt: skip


# the builder's session opened for the step: its stage is its own work (#718)
WORKING = ({"at": (NOW - timedelta(minutes=50)).isoformat(timespec="seconds"), "session": "b1", "role": "builder",
            "event": "session", "id": "b1", "resumed": False},)  # fmt: skip


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


def test_a_done_change_whose_pull_back_left_the_target_behind_says_so_and_offers_pull():
    behind = Pullback(state="behind", reason="local main is behind: main is checked out in 2 worktrees", at=NOW)
    done = build(finished_at=NOW, names=Names(target="main", pr=13), pullback=behind)
    assert status(done, Activity(host_up=True), NOW) == Status(
        "Done · merged PR #13 · local main is behind: main is checked out in 2 worktrees",
        "Pull on the Changes page",
        "you",
        error=True,
    )
    pulled = done.model_copy(update={"pullback": Pullback(state="updated", at=NOW)})
    assert status(pulled, Activity(host_up=True), NOW) == Status("Done · merged PR #13", None, "delivery")


@pytest.mark.parametrize(
    ("change", "activity", "expected"),
    [
        (ASKING, Activity(host_up=True), Status("Build 2/2 · waiting for you: which key?", "Answer", "you")),
        (
            STOPPED,
            Activity(host_up=True),
            Status("Build 2/2 · stopped: model blocked", "Allow the model", "admin", error=True, stopped=True),
        ),
        (
            PUBLISHING,
            Activity(host_up=True),
            Status("Publish · waiting for CI: 2 of 5 running (checked 1 min ago)", None, "github"),
        ),
        (
            build(),
            Activity(host_up=True, runner_alive=True, last_event_at=NOW - timedelta(seconds=40), events=WORKING),
            Status("Build 2/2 · implementing: rate limiter · builder active 40 s ago", None, "delivery"),
        ),
        (
            build(),
            Activity(host_up=True, runner_alive=True, last_event_at=NOW - timedelta(minutes=12), events=WORKING),
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
            Activity(host_up=True, runner_alive=True, last_event_at=NOW, events=WORKING),
            Status("Build 2/2 · implementing: rate limiter · last denied: docker compose up", None, "delivery"),
        ),
        (
            build(outcome=Outcome(exit=Exit.ASK, cause="liveness:build:usage-unread", reason="no usage", at=NOW)),
            Activity(host_up=True),
            Status("Build 2/2 · stopped: no usage", "Run this step again", "you", error=True, stopped=True),
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


def test_spend_accumulates_every_usage_report_by_model():
    spend = Spend()
    for model in ("gpt", "gpt", "opus"):
        spend = spend.plus({"credits": 0.5, "models": {model: {"credits": 0.5, "tokens": 100}}})
    spend = spend.plus({"error": "TimeoutError"})
    assert spend == Spend(
        credits=1.5, models={"gpt": ModelSpend(credits=1.0, tokens=200), "opus": ModelSpend(credits=0.5, tokens=100)}
    )


def test_resumed_usage_keeps_each_high_water_mark_across_reload_and_adds_distinct_sessions():
    def report(n: int | None) -> dict:
        weights = {"tokens": 11, "input": 10, "output": 1, "cache_read": 6, "cache_write": 3}
        kinds = {key: None if n is None else weight * n for key, weight in weights.items()}
        used = None if n is None else float(n)
        return {"credits": used, "models": {"gpt": {"credits": used, **kinds}}}

    spend = Spend().plus(report(2), "s1")
    assert (spend.credits, spend.models["gpt"]) == (
        2.0,
        ModelSpend(credits=2.0, tokens=22, input=20, output=2, cache_read=12, cache_write=6),
    )
    spend = spend.plus(report(None), "s1")
    assert (spend.credits, spend.models["gpt"].tokens) == (2.0, 22)
    spend = spend.plus(report(5), "s1")
    grown = ModelSpend(credits=5.0, tokens=55, input=50, output=5, cache_read=30, cache_write=15)
    assert (spend.credits, spend.models["gpt"]) == (5.0, grown)
    spend = Spend.model_validate_json(spend.model_dump_json())
    spend = spend.plus(report(3), "s1").plus(report(5), "s1")
    assert (spend.credits, spend.models["gpt"]) == (5.0, grown)
    spend = spend.plus(report(1), "s2")
    assert (spend.credits, spend.models["gpt"]) == (
        6.0,
        ModelSpend(credits=6.0, tokens=66, input=60, output=6, cache_read=36, cache_write=18),
    )
    assert Spend.model_validate_json(spend.model_dump_json()) == spend


def running(started: datetime) -> Change:
    return Change(
        slug="c1", plan=PLAN, step=Step(kind=StepKind.BUILD, task="t2", started_at=started), spend=Spend(credits=3.0)
    )


def test_card_shows_the_last_event_step_time_and_credits():
    events = [
        {"at": (NOW - timedelta(minutes=30)).isoformat(), "event": "step", "usage": {"credits": 2.0}},
        {"at": (NOW - timedelta(minutes=3)).isoformat(), "event": "step", "usage": {"credits": 0.75}},
        {"at": (NOW - timedelta(seconds=40)).isoformat(), "event": "tool", "tool": "submit_result", "accepted": True},
    ]
    alive = Activity(host_up=True, runner_alive=True, last_event_at=NOW - timedelta(seconds=40))
    out = card(running(NOW - timedelta(minutes=5)), alive, events, NOW)
    assert out == {
        "now": "Build 2/2 · submitted its result 40 s ago",
        "step_time": "5 min",
        "quiet": False,
        "credits": {"change": 3.0, "step": 0.75, "unknown": 0},
        "overlaps": [],
        "decisions": [],
    }


@pytest.mark.parametrize(
    ("event", "tool", "said"),
    [
        ({"event": "step", "kind": "build", "exit": "stop"}, None, "building stopped"),
        ({"event": "step", "kind": "plan-challenge", "exit": "odd"}, None, "plan challenge ended"),
        ({"event": "tool", "tool": "edit", "accepted": False}, None, "called edit (refused)"),
        (None, {"tool": "submit_result", "summary": "submit_result"}, "submitted its result"),
        (None, {"tool": "edit", "summary": "edit hero.css"}, "edit hero.css"),
    ],
)
def test_the_card_names_its_last_event_in_plain_words(event, tool, said):
    at = (NOW - timedelta(seconds=40)).isoformat()
    events, live = ([event | {"at": at}] if event else []), (tool | {"at": at} if tool else None)
    out = card(running(NOW - timedelta(minutes=5)), Activity(host_up=True), events, NOW, live)
    assert out["now"] == f"Build 2/2 · {said} 40 s ago"


def test_a_recent_now_line_of_the_current_step_keeps_the_card_from_turning_quiet():
    c = running(NOW - timedelta(hours=1))
    alive = Activity(host_up=True, runner_alive=True, last_event_at=NOW - timedelta(minutes=30))
    recent = {"tool": "bash", "summary": "ran uv", "at": (NOW - timedelta(minutes=1)).isoformat()}
    stale = recent | {"at": (NOW - timedelta(hours=2)).isoformat()}
    assert card(c, alive, [], NOW, recent)["quiet"] is False
    assert card(c, alive, [], NOW, stale)["quiet"] is True
    assert card(c, alive, [], NOW)["quiet"] is True


@pytest.mark.parametrize(
    ("silent", "quiet"), [(timedelta(minutes=10), False), (timedelta(minutes=10, seconds=1), True)]
)
def test_card_is_quiet_only_past_the_step_kind_threshold_while_running(silent, quiet):
    c = running(NOW - timedelta(hours=1))
    alive = Activity(host_up=True, runner_alive=True, last_event_at=NOW - silent)
    assert card(c, alive, [], NOW)["quiet"] is quiet
    assert card(c, Activity(host_up=True, last_event_at=NOW - silent), [], NOW)["quiet"] is False
    assert card(PUBLISHING, Activity(host_up=True), [], NOW)["quiet"] is False


TRIED, FAILED = "tooling:build:sdk", " · last try failed: "
ALIVE = Activity(host_up=True, runner_alive=True, last_event_at=NOW, events=WORKING)
LINES = [
    (ALIVE, "implementing: rate limiter · builder active 0 s ago", FAILED),
    (Activity(host_up=True, holder_pid=4242), "not running: waiting for process 4242 to end", FAILED),
    (Activity(host_up=True, waiting_slot="2 of 2 busy"), "waiting for a session slot (2 of 2 busy)", FAILED),
    (Activity(host_up=True), "not running: starting builder", FAILED),
    (Activity(host_up=True), f"retrying: {TRIED} (1 of 3) at 12:05", " · "),
]  # fmt: skip


@pytest.mark.parametrize(("activity", "line", "joined"), LINES)
@pytest.mark.parametrize("said", [True, False])
def test_a_retry_says_its_last_failed_try_whole(activity, line, joined, said, whole_error):
    waking = line.endswith("12:05")
    reason = f"RuntimeError: {whole_error}" if said else ""
    o = Outcome(
        exit=Exit.RETRY, cause=TRIED, reason=reason, at=NOW, wake_at=NOW + timedelta(minutes=5 if waking else -1)
    )
    expected = f"Build 2/2 · {line}{joined}{reason}" if said else f"Build 2/2 · {line}"
    assert status(build(outcome=o), activity, NOW).line == expected


def _ev(minutes: float, event: str, **more) -> dict:
    """An event of the builder's session as the SDK runtime journals it (#718)."""
    return {"at": (NOW - timedelta(minutes=minutes)).isoformat(timespec="seconds"), "session": "b1",
            "role": "builder", "event": event, **more}  # fmt: skip


OPENED = _ev(4, "session", id="b1", resumed=False)
REFUSED = _ev(1, "tool", tool="submit_result", accepted=False, errors=["ruff: F401"])


@pytest.mark.parametrize(
    ("events", "said"),
    [
        ((), "starting"),
        ((OPENED,), "implementing"),
        ((OPENED, REFUSED), "fixing its refused result"),
        ((OPENED, REFUSED, _ev(0.5, "tool", tool="submit_result", accepted=True)), "handing in its result"),
    ],
)
def test_a_running_steps_line_says_its_stage_from_its_sessions_events(events, said):
    """#718: the step started five minutes ago; its stage follows its session's events, and nothing else changes."""
    alive = Activity(host_up=True, runner_alive=True, last_event_at=NOW - timedelta(seconds=30), events=events)
    line = status(running(NOW - timedelta(minutes=5)), alive, NOW).line
    assert line == f"Build 2/2 · {said}: rate limiter · builder active 30 s ago"


@pytest.mark.parametrize(
    ("change", "expected"),
    [
        (ASKING, "Build 2/2 · waiting for you: which key?"),
        (STOPPED, "Build 2/2 · stopped: model blocked"),
        (build(intent=Intent(hold=True)), "Build 2/2 · holding for your change: finishing build"),
        (build(intent=Intent(paused_at=NOW)), "Build 2/2 · pausing: finishing build"),
    ],
)
def test_a_stage_never_overrides_an_earlier_rule(change, expected):
    started = change.model_copy(update={"step": change.step.model_copy(update={"started_at": NOW})})
    events = tuple(e | {"at": NOW.isoformat()} for e in (OPENED, REFUSED))  # alone they would say "fixing"
    alive = Activity(host_up=True, runner_alive=STOPPED is not change, events=events)
    assert status(started, alive, NOW).line == expected
