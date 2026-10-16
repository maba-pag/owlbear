from datetime import UTC, datetime, timedelta

import pytest

from owlbear_delivery_next.models import (
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
from owlbear_delivery_next.spend import ModelSpend, Spend
from owlbear_delivery_next.status import Activity, Status, card, status

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


def test_a_done_change_whose_pull_back_left_the_target_behind_says_so_and_offers_pull():
    behind = Pullback(state="behind", reason="local main is behind: main is checked out in 2 worktrees", at=NOW)
    done = build(finished_at=NOW, names=Names(target="main", pr=13), pullback=behind)
    assert status(done, Activity(host_up=True), NOW) == Status(
        "Done · merged PR #13 · local main is behind: main is checked out in 2 worktrees",
        "Pull on the Changes page",
        "you",
    )
    pulled = done.model_copy(update={"pullback": Pullback(state="updated", at=NOW)})
    assert status(pulled, Activity(host_up=True), NOW) == Status("Done · merged PR #13", None, "delivery")


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
        (
            build(outcome=Outcome(exit=Exit.ASK, cause="liveness:build:usage-unread", reason="no usage", at=NOW)),
            Activity(host_up=True),
            Status("Build 2/2 · stopped: no usage", "Run this step again", "you"),
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


def test_a_resumed_session_adds_only_the_growth_of_its_cumulative_usage():
    spend = Spend().plus({"credits": 2.0, "models": {"gpt": {"credits": 2.0, "tokens": 10}}}, "s1")
    spend = spend.plus({"credits": 5.0, "models": {"gpt": {"credits": 5.0, "tokens": 25}}}, "s1")
    spend = spend.plus({"credits": 1.0, "models": {"gpt": {"credits": 1.0, "tokens": 4}}}, "s2")
    assert (spend.credits, spend.models["gpt"]) == (6.0, ModelSpend(credits=6.0, tokens=29))
    assert Spend.model_validate_json(spend.model_dump_json()) == spend  # the last reports survive a restart


def test_a_missing_or_lower_usage_field_keeps_the_sessions_high_water_mark():
    spend = Spend()
    for used, tokens in ((2.0, 10), (None, None), (5.0, 25)):
        spend = spend.plus({"credits": used, "models": {"gpt": {"credits": used, "tokens": tokens}}}, "s1")
    assert (spend.credits, spend.models["gpt"]) == (5.0, ModelSpend(credits=5.0, tokens=25))
    spend = Spend()
    for used in (5.0, 3.0, 5.0):
        spend = spend.plus({"credits": used, "models": {"gpt": {"credits": used, "tokens": 9}}}, "s1")
    assert (spend.credits, spend.models["gpt"]) == (5.0, ModelSpend(credits=5.0, tokens=9))


def test_each_token_kind_adds_up_like_the_total_across_a_resumed_session():
    def report(n: int) -> dict:
        kinds = {"tokens": 11 * n, "input": 10 * n, "output": n, "cache_read": 6 * n, "cache_write": 3 * n}
        return {"credits": float(n), "models": {"opus": {"credits": float(n), **kinds}}}

    spend = Spend().plus(report(1), "s1").plus(report(3), "s1").plus(report(2), "s2")
    want = ModelSpend(credits=5.0, tokens=55, input=50, output=5, cache_read=30, cache_write=15)
    assert spend.models["opus"] == want


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
        "now": "Build 2/2 · called `submit_result` 40 s ago",
        "step_time": "5 min",
        "quiet": False,
        "credits": {"change": 3.0, "step": 0.75, "unknown": 0},
        "overlaps": [],
    }


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
