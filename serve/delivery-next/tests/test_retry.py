from datetime import UTC, datetime, timedelta

from owlbear_delivery_next import loop
from owlbear_delivery_next.loop import EPISODE_ASK, PAUSE, PAUSE_CAP, StepResult
from owlbear_delivery_next.models import (
    AnswerItem,
    Brief,
    Change,
    Criterion,
    ErrorKind,
    Exit,
    Plan,
    Score,
    Spend,
    Step,
    StepKind,
    Task,
    Waiting,
)
from owlbear_delivery_next.status import Activity, card, status

NOW = datetime(2026, 10, 10, 12, tzinfo=UTC)
K = StepKind
HTTP_503 = "HTTP 503 Service Unavailable"


def change(**fields) -> Change:
    return Change(
        slug="c1",
        brief=Brief(version=1, approved_version=1, criteria=[Criterion(id="AC-1", text="works")]),
        plan=Plan(tasks=[Task(id="t1", title="one", scope=["a"])]),
        step=Step(kind=K.BUILD, task="t1", started_at=NOW),
        **fields,
    )


def retry(kind: ErrorKind, reason: str, **fields) -> StepResult:
    return StepResult(exit=Exit.RETRY, cause=loop.cause_key(kind, K.BUILD, "sdk"), reason=reason, **fields)


def failing(n: int, reason: str = "test_a failed") -> StepResult:
    cause = loop.cause_key(ErrorKind.CHECKS, K.BUILD, "uv run pytest")
    return StepResult(exit=Exit.RETRY, cause=cause, reason=reason, score=Score(failing=n, findings=["test_a"]))


def test_transient_failures_never_exhaust_and_their_pauses_grow_to_the_cap():
    c, at, pauses = change(), NOW, []
    for _ in range(10):
        c = loop.apply(c, retry(ErrorKind.NETWORK, HTTP_503), at)
        assert (c.outcome.exit, c.outcome.waiting, c.step.kind) == (Exit.PENDING, Waiting.NETWORK, K.BUILD)
        pauses.append(c.outcome.wake_at - at)
        at = c.outcome.wake_at
    assert pauses == sorted(pauses)
    assert (pauses[0], pauses[-1]) == (PAUSE, PAUSE_CAP)
    assert all(b.count == 0 for b in c.budgets.causes.values())
    assert loop.episode(c).attempts == 10


def test_a_day_of_the_same_failure_asks_and_done_starts_a_new_episode():
    c = loop.apply(change(), retry(ErrorKind.NETWORK, HTTP_503), NOW)
    c = loop.apply(c, retry(ErrorKind.NETWORK, "HTTP 504 Service Unavailable"), NOW + EPISODE_ASK)  # numbers differ
    q = loop.open_question(c)
    assert c.outcome.exit == Exit.ASK
    assert [o.id for o in q.options] == ["done", "pause"]
    assert "Service Unavailable" in q.text
    c = loop.fold(c, [AnswerItem(at=NOW + EPISODE_ASK, question=q.id, option="done")], NOW + EPISODE_ASK)
    assert q.cause not in c.budgets.causes


def test_a_changed_failure_signature_restarts_the_episode():
    c = loop.apply(change(), retry(ErrorKind.NETWORK, HTTP_503), NOW)
    c = loop.apply(c, retry(ErrorKind.NETWORK, "connection reset by peer"), NOW + EPISODE_ASK)
    assert c.outcome.exit == Exit.PENDING
    assert (loop.episode(c).since, loop.episode(c).attempts) == (NOW + EPISODE_ASK, 1)


def test_the_same_delivery_defect_three_times_asks_with_the_error():
    c = change()
    for n in range(1, 3):
        c = loop.apply(c, retry(ErrorKind.TOOLING, f"submit tool rejected payload {n}"), NOW)
        assert c.outcome.exit == Exit.RETRY
    c = loop.apply(c, retry(ErrorKind.TOOLING, "submit tool rejected payload 3"), NOW)
    q = loop.open_question(c)
    assert c.outcome.exit == Exit.ASK
    assert "submit tool rejected payload" in q.text
    assert [o.id for o in q.options] == ["done", "pause"]


def test_identical_check_failures_replan_once_to_split_then_ask():
    c = change()
    for _ in range(loop.RETRY_LIMIT):
        c = loop.apply(c, failing(2), NOW)
        assert c.step.kind == K.BUILD
    c = loop.apply(c, failing(2), NOW)
    assert (c.outcome.exit, c.step.kind) == (Exit.BACK, K.PLAN)
    assert c.outcome.reason.startswith("re-plan to split the work")
    c.step = Step(kind=K.BUILD, task="t1")
    c = loop.apply(c, failing(2), NOW)
    assert c.outcome.exit == Exit.ASK


def test_fewer_failing_checks_reset_the_count():
    c = change()
    for _ in range(loop.RETRY_LIMIT):
        c = loop.apply(c, failing(2), NOW)
    c = loop.apply(c, failing(1), NOW)
    assert (c.outcome.exit, c.step.kind) == (Exit.RETRY, K.BUILD)
    assert c.budgets.causes[c.outcome.cause].count == 1


def test_a_new_commit_or_error_text_with_the_same_failing_check_is_not_progress():
    c = change()
    for sha in ("1a2b3c4d", "5e6f7a8b", "9c0d1e2f", "3a4b5c6d"):
        c = loop.apply(c, failing(2, f"test_a failed at {sha}"), NOW)
    assert (c.outcome.exit, c.step.kind) == (Exit.BACK, K.PLAN)


def test_quota_waits_for_its_reset_and_shows_credits_without_a_quota_question():
    c = change(spend=Spend(credits=12.5))
    c = loop.apply(c, retry(ErrorKind.CAPACITY, "quota exceeded", wake_at=NOW + timedelta(hours=3)), NOW)
    assert (c.outcome.exit, c.outcome.wake_at) == (Exit.PENDING, NOW + timedelta(hours=3))
    line = status(c, Activity(host_up=True), NOW + timedelta(minutes=5)).line
    assert "12.50 credits used" in line
    assert "next try at 15:00" in line
    assert "raise" not in line.lower()


def test_the_card_shows_the_episode_and_turns_quiet_after_an_hour():
    c = loop.apply(change(), retry(ErrorKind.NETWORK, HTTP_503), NOW)
    early = card(c, Activity(host_up=True), [], NOW + timedelta(minutes=1))
    late = card(c, Activity(host_up=True), [], NOW + timedelta(hours=2))
    assert "network failing for" in early["now"]
    assert "attempt 1" in early["now"]
    assert (early["quiet"], late["quiet"]) == (False, True)


def test_the_card_shows_the_latest_tool_call_only_when_newer_than_the_last_event():
    c, event = change(), {"event": "step", "at": (NOW + timedelta(seconds=10)).isoformat()}
    tool = {"tool": "bash", "summary": "ran uv run pytest", "at": (NOW + timedelta(seconds=20)).isoformat()}
    stale = tool | {"at": (NOW + timedelta(seconds=5)).isoformat()}
    assert "ran uv run pytest" in card(c, Activity(host_up=True), [event], NOW + timedelta(minutes=1), tool)["now"]
    assert "ran uv run pytest" not in card(c, Activity(host_up=True), [event], NOW + timedelta(minutes=1), stale)["now"]
