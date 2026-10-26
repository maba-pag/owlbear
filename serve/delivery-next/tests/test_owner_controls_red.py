"""RED regressions for owner controls (items 2 and 5). Production code is deliberately unchanged here."""

import subprocess
from datetime import UTC, datetime

import pytest

from owlbear_delivery_next.change_contracts.inbox import IntentItem
from owlbear_delivery_next.change_contracts.models import Change, Names, Plan, Step, StepKind, Task
from owlbear_delivery_next.commands import runner
from owlbear_delivery_next.settings import config
from owlbear_delivery_next.state_store.database import StoreError
from owlbear_delivery_next.state_store.store import Store

NOW = datetime(2026, 10, 10, 12, tzinfo=UTC)

# Item 5: an inbox pause or abandon folds even when a settings layer is unreadable or invalid together.


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))  # the machine layer lives under this temporary home only
    for args in (
        ["init", "-q"],
        ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "i"],
    ):
        subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)  # noqa: S603, S607
    return Store.open(tmp_path)


def seed(store):
    c = Change(
        slug="c1",
        plan=Plan(tasks=[Task(id="t1", title="greet", checks=["npm test"])]),
        step=Step(kind=StepKind.BUILD, task="t1"),
        names=Names(worktree=str(store.root)),
    )
    with store.lock("c1") as lock:
        store.write(lock, c)


def fold(store, intent):
    store.put_inbox("c1", IntentItem(at=NOW, intent=intent))
    with store.lock("c1") as lock:
        return store.fold(lock, "c1", NOW)


def test_an_unreadable_machine_layer_still_folds_an_owner_pause(store):
    seed(store)
    store.machine_path.parent.mkdir(parents=True, exist_ok=True)
    store.machine_path.write_text("{not json")
    change_after, _ = fold(store, "pause")
    assert (change_after.intent.paused_at, store.read("c1").intent.paused_at) == (NOW, NOW)


def test_an_invalid_cross_layer_policy_still_folds_an_owner_abandon(store):
    seed(store)
    bad = config.Agent(max_rounds=3, max_findings=10, last_round_at=8, ask_owner_at=7)  # rounds do not hold together
    notice = store.save(
        store.config_path,
        config.Layer,
        lambda cur: cur.model_copy(update={"agents": {"shaper": bad}}),
        "owner",
        owner=True,
    )
    assert notice == ""  # the owner's policy is written, so the fold below meets the invalid policy
    with pytest.raises(StoreError, match="do not combine"):
        store.settings()  # the merged policy is invalid: the fold must still fold the owner's abandon over it
    change_after, _ = fold(store, "abandon")
    assert (change_after.intent.abandoned_at, store.read("c1").intent.abandoned_at) == (NOW, NOW)


def test_the_execution_boundary_reports_the_settings_fault_after_the_owner_pause_without_paid_work(store, monkeypatch):
    seed(store)
    store.machine_path.parent.mkdir(parents=True, exist_ok=True)
    store.machine_path.write_text("{not json")
    monkeypatch.setattr(runner, "_run", lambda *_a, **_k: pytest.fail("paid work must not start"))
    change_after, _ = fold(store, "pause")
    with store.lock("c1") as lock:
        runner._step(store, lock, change_after, Step(kind=StepKind.BUILD, task="t1"), store.root)  # noqa: SLF001
    stopped = store.read("c1")
    assert (stopped.intent.paused_at is not None, stopped.stop is not None) == (True, True)
