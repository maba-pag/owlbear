"""RUN-03 across R04 maintenance ownership: a real SDK step keeps its lease through a late deadline and late PID."""

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from owlbear_delivery_next.change_contracts import tools
from owlbear_delivery_next.change_contracts.models import StepKind
from owlbear_delivery_next.change_contracts.permissions import Policy
from owlbear_delivery_next.local_system import maintenance, processes
from owlbear_delivery_next.local_system.slots import Slots
from owlbear_delivery_next.runtimes import loop_owner, maintained, sdk_adapter, sdk_teardown

ROOT, CHILD = 4242, 4343
BIRTH = {ROOT: 111.0, CHILD: 112.0}
AT = datetime(2026, 10, 25, tzinfo=UTC)
PAYLOAD = tools.BuildResult(summary="No edit was needed", checks=[])


class Clock:
    def __init__(self):
        self.now = 1000.0

    def monotonic(self):
        return self.now


class World:
    """Synthetic SDK transport: the request ignores cancellation and reports a child PID only after teardown starts."""

    def __init__(self, clock, *, resistant, absent):
        self.clock, self.resistant, self.absent = clock, resistant, absent
        self.live, self.steps, self.signals, self.accepted = {}, [], [], []
        self.cancels = 0
        self.release = None

    async def start(self):
        self.release = asyncio.Event()
        self.live[ROOT] = BIRTH[ROOT]

    async def stop(self):
        self.live.pop(ROOT, None)
        self.release.set()

    async def create_session(self, **_opts):
        return self.session

    async def listing(self):
        if not self.accepted:  # teardown's own tasks.list must not submit a second result
            self.clock.now += 2.0  # the valid result arrives after the one-second session budget
            st = self.steps[0]
            _, accepted = st.gate.call(st.cfg.submit, PAYLOAD.model_dump())
            self.accepted.append(accepted)
        if self.resistant:
            while True:
                try:
                    await self.release.wait()
                    break
                except asyncio.CancelledError:
                    self.cancels += 1
        return SimpleNamespace(tasks=[SimpleNamespace(id="child", pid=CHILD, status="running")])

    async def cancel(self, _request):
        return None

    async def disconnect(self):
        return None

    def alive(self, pid, _created):
        return ROOT in self.live if pid == ROOT else self.absent

    def kill(self, recorded, sig):
        self.signals.append((sig, dict(recorded)))
        return []


@pytest.fixture
def bridge(tmp_path, monkeypatch):
    clock = Clock()
    monkeypatch.setattr(sdk_adapter, "time", clock)
    monkeypatch.setattr(sdk_adapter, "POLL", 0.001)
    monkeypatch.setattr(sdk_teardown, "SETTLE", 0)
    monkeypatch.setattr(sdk_teardown, "GRACE", 0)
    monkeypatch.setattr(sdk_teardown, "STOP_CALL", 0.01)
    monkeypatch.setattr(sdk_adapter._Step, "record_tree", lambda _self: None)  # noqa: SLF001
    monkeypatch.setattr(sdk_adapter.preload, "missing", lambda *_a, **_k: [])
    monkeypatch.setattr(processes, "started", lambda pid: BIRTH.get(pid, 1.0))
    monkeypatch.setattr(sdk_adapter, "cli_path", lambda: "fake-copilot")
    monkeypatch.setattr(sdk_adapter, "RuntimeConnection", SimpleNamespace(for_stdio=lambda **_: None))

    async def usage(_session, _model):
        return {}

    monkeypatch.setattr(sdk_adapter, "usage_read", usage)
    original = sdk_adapter._Step.__init__  # noqa: SLF001
    steps = []

    def spy(st, cfg, loop):
        original(st, cfg, loop)
        steps.append(st)

    monkeypatch.setattr(sdk_adapter._Step, "__init__", spy)  # noqa: SLF001

    def make(*, resistant, absent):
        world = World(clock, resistant=resistant, absent=absent)
        world.steps = steps
        world.session = SimpleNamespace(
            rpc=SimpleNamespace(tasks=SimpleNamespace(list=world.listing, cancel=world.cancel)),
            send=lambda *_a, **_k: asyncio.sleep(0),
            get_events=lambda: asyncio.sleep(0, result=[]),
            disconnect=world.disconnect,
        )
        client = SimpleNamespace(
            start=world.start,
            stop=world.stop,
            create_session=world.create_session,
            _cli_process=SimpleNamespace(pid=ROOT),
        )
        monkeypatch.setattr(sdk_adapter, "CopilotClient", lambda **_: client)
        monkeypatch.setattr(processes, "alive", world.alive)
        monkeypatch.setattr(processes, "kill", world.kill)
        return world

    return make, tmp_path


def manager(slots, *, observe=lambda *_a: None):
    return maintenance.Maintenance(slots, boot=lambda: 10.0, observe=observe)


def cfg_for(root, events):
    return sdk_adapter.Session(
        kind=StepKind.BUILD,
        worktree=root,
        session_id="synthetic-run03",
        message="Synthetic work",
        resume=False,
        policy=Policy(root),
        observe=lambda: tools.Worktree("a" * 40, "b" * 40),
        checks=(),
        model="synthetic-model",
        limit=1.0,
        journal=sdk_adapter.Journal(event=events.append),
    )


def run_through_maintenance(owner, cfg):
    def execute(bound):
        return loop_owner.run(sdk_adapter.run(bound))

    return maintained.run_owned(owner, cfg, execute, project="p", slot="pack:one", kind="pack")


def test_an_expired_budget_during_a_resistant_rpc_keeps_one_held_lease_through_a_late_pid(bridge):
    make, tmp_path = bridge
    world = make(resistant=True, absent=None)  # the late child's termination stays unknown
    root = tmp_path / "workspace"
    root.mkdir()
    events = []
    owner = manager(Slots(lambda: 1))
    assert owner.slots.take("p", "pack:one", 1, 1) == 1

    done = run_through_maintenance(owner, cfg_for(root, events))

    assert world.accepted == [False]
    assert done.ending == "deadline"
    assert done.payload is None
    assert done.termination.confirmed is False
    assert world.cancels >= 1
    assert world.signals == []
    assert any(e.get("event") == "pids" and str(CHILD) in e["pids"] for e in events)
    [lease] = owner.read()["sessions"]
    assert lease["state"] == "held"
    assert lease["workspace"] == str(root)
    assert owner.records("p", "pack", "pack:one", {ROOT: BIRTH[ROOT], CHILD: BIRTH[CHILD]})
    assert root.exists()

    fresh = manager(Slots(lambda: 1, closed=True), observe=lambda *_a: None)
    fresh.slots.open()
    assert fresh.slots.counts("p") == (1, 1, 1)
    assert fresh.retained(str(root))
    fresh.sweep()
    assert fresh.slots.counts("p") == (1, 1, 1)
    assert fresh.slots.take("other", "c1", 1, 1) == 0


def test_identity_aware_absence_after_a_deadline_releases_the_slot(bridge):
    make, tmp_path = bridge
    world = make(resistant=False, absent=False)  # both recorded identities are observed gone
    root = tmp_path / "workspace"
    root.mkdir()
    owner = manager(Slots(lambda: 1))
    assert owner.slots.take("p", "pack:one", 1, 1) == 1

    done = run_through_maintenance(owner, cfg_for(root, []))

    assert world.accepted == [False]
    assert done.ending == "deadline"
    assert done.termination.confirmed is True
    assert world.signals == []
    assert owner.read()["sessions"][0]["state"] == "released"
    assert owner.slots.counts("p") == (0, 1, 0)
    assert not owner.retained(str(root))
