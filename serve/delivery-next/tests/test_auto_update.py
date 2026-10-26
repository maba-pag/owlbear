"""Updating by itself when idle (self-update build §7): clock-driven, with the versions and the update faked."""

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from owlbear_delivery_next.machine_host import app, auto_update, versions
from owlbear_delivery_next.machine_host.machine import Machine
from owlbear_delivery_next.machine_host.versions import Choice
from owlbear_delivery_next.project_host.host import HostRecord
from owlbear_delivery_next.state_store import registry

TOKEN = "t"  # noqa: S105 - a test host's token


class Clock:
    """Wall and monotonic time the test moves; a sleep moves only the wall clock."""

    def __init__(self) -> None:
        self.wall, self.mono = 1_000_000.0, 100.0

    def step(self, seconds: float, *, asleep: bool = False) -> None:
        self.wall += seconds
        if not asleep:
            self.mono += seconds


@pytest.fixture
def idle(monkeypatch) -> SimpleNamespace:
    """A running machine with nothing to do, v0.2 newer than it runs, and an update that only records its start."""
    looks: list[int] = []
    monkeypatch.setattr(versions, "target", lambda: looks.append(1) or Choice("v0.2", "c2"))
    clock = Clock()
    record = HostRecord(url="http://127.0.0.1:4321/", token=TOKEN, pid=1, started_at=datetime.now(UTC), code="c")
    machine = Machine(record, paused=False)
    machine.auto = auto_update.Auto(machine, wall=lambda: clock.wall, mono=lambda: clock.mono)
    started: list[bool] = []
    machine.updater.run_now = lambda *, auto=False: started.append(auto) or machine.updater.read()
    return SimpleNamespace(machine=machine, auto=machine.auto, clock=clock, started=started, looks=looks)


def settings(**values: bool) -> None:
    with registry.locked():
        saved = registry.load()
        saved.settings = saved.settings.model_copy(update=values)
        registry.save(saved)


def test_after_15_minutes_without_use_the_update_is_announced_for_2_minutes_then_runs(idle):
    idle.clock.step(auto_update.IDLE_FOR - 1)
    idle.auto.tick()
    assert (idle.auto.read(), idle.looks) == (None, [])  # not idle yet: nothing fetched either

    idle.clock.step(1)
    idle.auto.tick()
    assert idle.auto.read() == {"version": "v0.2", "left": 120}

    idle.clock.step(auto_update.ANNOUNCE - 1)
    idle.auto.tick()
    assert (idle.auto.read(), idle.started) == ({"version": "v0.2", "left": 1}, [])
    idle.clock.step(1)
    idle.auto.tick()
    assert (idle.auto.read(), idle.started) == (None, [True])  # an automatic update
    assert idle.looks == [1]  # one fetch for the whole of it, and only once idle


def test_postpone_or_any_use_cancels_the_announcement_and_starts_the_idle_time_again(idle):
    idle.clock.step(auto_update.IDLE_FOR)
    idle.auto.tick()
    assert idle.auto.read() is not None

    idle.auto.use()
    assert idle.auto.read() is None
    idle.clock.step(auto_update.ANNOUNCE)
    idle.auto.tick()
    assert (idle.auto.read(), idle.started) == (None, [])


def test_a_sleep_during_the_announcement_restarts_it(idle):
    idle.clock.step(auto_update.IDLE_FOR)
    idle.auto.tick()
    idle.clock.step(60)
    idle.auto.tick()
    idle.clock.step(3600, asleep=True)  # the lid closed for an hour

    idle.auto.tick()

    assert (idle.auto.read(), idle.started) == ({"version": "v0.2", "left": 120}, [])


def test_running_work_keeps_the_machine_from_being_idle(idle, monkeypatch):
    monkeypatch.setattr(idle.machine, "busy", lambda: ["p: c1: a running step (process 9)"])
    idle.clock.step(auto_update.IDLE_FOR * 2)

    idle.auto.tick()

    assert idle.auto.read() is None


@pytest.mark.parametrize(
    ("paused", "values", "announced"),
    [
        (False, {"update_when_idle": False}, False),
        (True, {"update_while_paused": False}, False),
        (True, {"update_while_paused": True}, True),
    ],
)
def test_the_machine_settings_decide_whether_it_updates_by_itself(idle, paused, values, announced):
    """TD-288: Update when idle and Update while paused; Run updates now is never held by them."""
    settings(**values)
    idle.machine.paused = paused
    idle.clock.step(auto_update.IDLE_FOR)

    idle.auto.tick()

    assert (idle.auto.read() is not None) == announced


def test_nothing_is_announced_while_owlbear_stops_when_idle_or_without_a_newer_version(idle, monkeypatch):
    idle.machine.ending = True
    idle.clock.step(auto_update.IDLE_FOR)
    idle.auto.tick()
    assert idle.auto.read() is None

    idle.machine.ending = False
    monkeypatch.setattr(versions, "target", lambda: None)
    idle.auto.next_look = 0
    idle.auto.tick()
    assert idle.auto.read() is None


def test_reads_never_count_as_use_but_changes_page_words_and_chat_calls_do(idle):
    client = TestClient(app.create(idle.machine), base_url="http://127.0.0.1")
    auth = {"authorization": f"Bearer {TOKEN}"}
    idle.clock.step(10)
    start = idle.auto.last_use

    client.get("/api/next/projects", headers=auth)  # a poll
    assert idle.auto.last_use == start
    client.post("/api/next/seen", headers={"authorization": "Bearer wrong"})  # no token: nobody's use
    assert idle.auto.last_use == start
    client.post("/api/next/seen", headers=auth)
    assert idle.auto.last_use == idle.clock.mono
    idle.clock.step(10)
    client.get("/p/0123456789abcdef/api/next/changes", headers=auth | {"x-owlbear-use": "chat"})
    assert idle.auto.last_use == idle.clock.mono


def test_the_machines_answer_carries_the_announcement(idle):
    idle.clock.step(auto_update.IDLE_FOR)
    idle.auto.tick()
    client = TestClient(app.create(idle.machine), base_url="http://127.0.0.1")

    listed = client.get("/api/next/projects", headers={"authorization": f"Bearer {TOKEN}"}).json()

    assert listed["announce"] == {"version": "v0.2", "left": 120}


def test_the_clock_set_back_restarts_the_announcement_too(idle):
    idle.clock.step(auto_update.IDLE_FOR)
    idle.auto.tick()
    idle.clock.step(60)
    idle.auto.tick()
    idle.clock.wall -= 600  # the wall clock corrected backwards

    idle.auto.tick()

    assert idle.auto.read() == {"version": "v0.2", "left": 120}


def test_a_version_that_failed_its_tries_is_not_announced_again(idle):
    idle.machine.updater.attempts["v0.2"] = 3
    idle.clock.step(auto_update.IDLE_FOR)

    idle.auto.tick()

    assert idle.auto.read() is None


def test_an_automatic_update_gives_way_to_use_to_its_settings_and_to_new_work_a_manual_one_does_not(idle):
    """TD-301: the owner's use or his settings end an automatic update; Run updates now waits on (TD-353)."""
    u, m = idle.machine.updater, idle.machine
    u.auto, u.uses = True, m.auto.uses
    assert u._cancelled() == ""  # noqa: SLF001
    assert u._cancelled(working=True) == "postponed: work started"  # noqa: SLF001
    m.auto.use()
    assert u._cancelled() == "postponed: you used OwlBear"  # noqa: SLF001
    u.uses = m.auto.uses
    settings(update_when_idle=False)
    assert u._cancelled() == "postponed: updating by itself is off now"  # noqa: SLF001
    u.auto = False
    assert u._cancelled(working=True) == ""  # noqa: SLF001
