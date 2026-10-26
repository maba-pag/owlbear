"""Queue and merge settings faults (review 5645306493 finding 2; 5645756524 finding 6).

The queue step runs against a fake GitHub that records every call; the store, the settings resolution and the claim
are the real ones. A missing merge method or poll interval must never leave a queued PR behind a question.
"""

import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

from owlbear_delivery_next.change_contracts.models import Change, Exit, Names, Plan, Step, StepKind, Task
from owlbear_delivery_next.change_contracts.profile_record import Profile, ProfileEntry
from owlbear_delivery_next.github.provider import (
    EnqueueResult,
    EnqueueStatus,
    FailureCode,
    MergeMethod,
    MergeRequest,
    MergeResult,
    MergeStatus,
    ProviderError,
    PullRequest,
    QueueEntry,
    QueueState,
)
from owlbear_delivery_next.settings import config, profile
from owlbear_delivery_next.settings.config import Layer, Prefs, SettingsUnset, pref
from owlbear_delivery_next.state_store.store import Store
from owlbear_delivery_next.workflow_steps import merge, queue
from owlbear_delivery_next.workflow_steps.engine import Ctx

NOW = datetime(2026, 10, 10, 12, tzinfo=UTC)
HEAD, MERGED_SHA = "a" * 40, "b" * 40
REPOSITORY = "acme/app"


def confirmed(value: str) -> ProfileEntry:
    return ProfileEntry(state="known", value=value, evidence=f"{profile.CONFIRMED}; owner")


PROFILE = Profile(entries={profile.REPO: confirmed(REPOSITORY)})


@pytest.fixture
def store(tmp_path: Path, monkeypatch) -> Store:
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setattr(config, "BASE", None)  # no test base layer may supply the unset values
    for args in (
        ["init", "-q"],
        ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "i"],
    ):
        subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)  # noqa: S603, S607
    return Store.open(tmp_path)


def set_prefs(store: Store, **values) -> None:
    """The owner's preference edit: an owner-intent save, asserted to publish and to be the effective value."""
    notice = store.save(
        store.config_path, Layer, lambda cur: cur.model_copy(update={"prefs": Prefs(**values)}), "owner", owner=True
    )
    assert notice == ""
    assert store.read_config().prefs == Prefs(**values)


def pr(*, merged: bool = False) -> PullRequest:
    return PullRequest(
        repository=REPOSITORY,
        number=7,
        node_id="PR_7",
        url="https://github.com/acme/app/pull/7",
        head_branch="feature",
        head_sha=HEAD,
        base_branch="main",
        draft=False,
        state="closed" if merged else "open",
        merged=merged,
    )


class FakeGitHub:
    """Synthetic GitHub: a queue entry, a dequeue that may fail or leave the entry in place, a merge boundary."""

    def __init__(self, *, queued: bool = False) -> None:
        self.current = pr()
        self.entry = QueueEntry(state="QUEUED", position=1, enqueued_at=NOW) if queued else None
        self.enqueued: list[str] = []
        self.dequeues = 0
        self.dequeue_error: ProviderError | None = None
        self.dequeue_keeps_entry = False
        self.requests: list[MergeRequest] = []
        self.on_request = None

    def read_pull_request(self, _repository: str, _number: int) -> PullRequest:
        return self.current

    def read_queue(self, _repository: str, _number: int) -> QueueState:
        return QueueState(merged=False, open=True, head_sha=HEAD, entry=self.entry)

    def enqueue(self, _pr: PullRequest, expected_head: str) -> EnqueueResult:
        self.enqueued.append(expected_head)
        self.entry = QueueEntry(state="QUEUED", position=1, enqueued_at=NOW)
        return EnqueueResult(status=EnqueueStatus.ENQUEUED, queued_at=NOW)

    def dequeue(self, _pr: PullRequest) -> None:
        self.dequeues += 1
        if self.dequeue_error is not None:
            raise self.dequeue_error
        if not self.dequeue_keeps_entry:
            self.entry = None

    def request_merge(self, req: MergeRequest) -> MergeResult:
        self.requests.append(req)
        if self.on_request is not None:
            self.on_request()
        self.current = pr(merged=True).model_copy(update={"merge_commit_sha": MERGED_SHA})
        return MergeResult(status=MergeStatus.MERGED, sha=MERGED_SHA)


def gate(ctx, c, _pr, _rules):
    """The real merge method read, nothing else: the production gate's first settings read."""
    pref(ctx.store.settings(), "merge_method")
    return c, None


def change(store: Store, tmp: Path) -> Change:
    c = Change(
        slug="c1",
        plan=Plan(tasks=[Task(id="t1", title="one", scope=["a"])]),
        step=Step(kind=StepKind.MERGE),
        names=Names(pr=7, branch="feature", target="main", worktree=str(tmp)),
    )
    with store.lock("c1") as lock:
        store.write(lock, c)
    return c


def ctx_for(store: Store, gh: FakeGitHub, tmp: Path) -> Ctx:
    return Ctx(store=store, lock=None, repo=tmp, profile=PROFILE, gh=gh, now=NOW)


def run_queue(store: Store, gh: FakeGitHub, tmp: Path):
    with store.lock("c1") as lock:
        ctx = ctx_for(store, gh, tmp)
        ctx.lock = lock
        return queue.run(ctx, store.read("c1"), gh.current, None, gate)


def test_a_valid_method_with_an_unset_poll_interval_asks_before_anything_is_queued(store, tmp_path):
    set_prefs(store, merge_method="squash")
    change(store, tmp_path)
    gh = FakeGitHub()
    with pytest.raises(SettingsUnset, match="ci_poll_seconds"):
        run_queue(store, gh, tmp_path)
    assert gh.enqueued == []
    assert store.read("c1").queue is None  # no remote entry and no claim


@pytest.mark.parametrize(
    "failure",
    ["dequeue-error", "still-queued"],
)
def test_an_uncertain_withdrawal_with_the_poll_interval_unset_keeps_the_barrier_and_asks_nothing(
    store, tmp_path, failure
):
    set_prefs(store, merge_method="squash")
    change(store, tmp_path)
    gh = FakeGitHub(queued=True)
    if failure == "dequeue-error":
        gh.dequeue_error = ProviderError(FailureCode.UNAVAILABLE, "dequeue", "connection reset", retry_safe=False)
    else:
        gh.dequeue_keeps_entry = True

    c, result = run_queue(store, gh, tmp_path)

    assert result.question is None
    assert result.exit != Exit.ASK
    assert gh.entry is not None  # GitHub still queues the PR: nothing was unqueued optimistically
    assert c.queue is not None  # the local claim is retained for the loop to persist; GitHub still has the entry
    assert gh.enqueued == []  # no second send


def test_a_confirmed_withdrawal_then_asks_the_poll_interval_on_a_fresh_store(store, tmp_path):
    set_prefs(store, merge_method="squash")
    change(store, tmp_path)
    gh = FakeGitHub(queued=True)
    with pytest.raises(SettingsUnset, match="ci_poll_seconds"):
        run_queue(store, gh, tmp_path)
    assert gh.dequeues == 1
    assert gh.entry is None
    fresh = Store.open(tmp_path)
    assert fresh.read("c1").queue is None  # the cleared claim is durable; no stale queue resurrection


def test_a_valid_poll_interval_keeps_the_queued_pr_pending_as_before(store, tmp_path):
    set_prefs(store, merge_method="squash", ci_poll_seconds=45)
    change(store, tmp_path)
    gh = FakeGitHub(queued=True)
    _, result = run_queue(store, gh, tmp_path)
    assert result.question is None
    assert result.exit == Exit.PENDING
    assert "merge queue" in result.reason


@pytest.mark.parametrize("method", [None, MergeMethod.REBASE.value])
def test_an_owner_change_during_the_merge_leaves_the_submitted_method_and_completes(store, tmp_path, method):
    set_prefs(store, merge_method="squash")
    c = change(store, tmp_path)
    gh = FakeGitHub()
    gh.on_request = lambda: set_prefs(store, merge_method=method)  # the owner edits the preference mid-call

    with store.lock("c1") as lock:
        ctx = ctx_for(store, gh, tmp_path)
        ctx.lock = lock
        result = merge.submit(ctx, c, pr())

    assert [r.method for r in gh.requests] == [MergeMethod.SQUASH]  # the method sent, not the mutable preference
    assert result.exit == Exit.DONE, result.reason
    assert "squash" in result.reason


def run_and_keep(store: Store, gh: FakeGitHub, tmp: Path):
    """One queue pass whose changed claim is saved, as the step loop saves it."""
    with store.lock("c1") as lock:
        ctx = ctx_for(store, gh, tmp)
        ctx.lock = lock
        c, result = queue.run(ctx, store.read("c1"), gh.current, None, gate)
        store.write(lock, c)
        return result


def test_an_owned_untraced_attempt_with_the_poll_unset_waits_then_withdraws_before_asking(store, tmp_path):
    set_prefs(store, merge_method="squash", ci_poll_seconds=45)
    change(store, tmp_path)
    gh = FakeGitHub()
    assert run_and_keep(store, gh, tmp_path).exit == Exit.PENDING  # Delivery enqueues, the claim is saved
    assert gh.enqueued == [HEAD]

    gh.entry = None  # GitHub shows no trace of the attempt yet
    set_prefs(store, merge_method="squash")  # the poll interval is now unset
    waiting = run_and_keep(store, gh, tmp_path)
    assert waiting.question is None
    assert waiting.exit == Exit.PENDING
    assert gh.dequeues == 0
    assert gh.enqueued == [HEAD]  # no question, no second send, nothing withdrawn

    gh.entry = QueueEntry(state="QUEUED", position=1, enqueued_at=NOW)  # the attempt appears later
    with pytest.raises(SettingsUnset, match="ci_poll_seconds"):
        run_queue(store, gh, tmp_path)
    assert gh.dequeues == 1
    assert gh.entry is None  # confirmed withdrawal came before the settings question
