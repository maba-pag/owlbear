"""RUN-03 across R04 maintenance ownership: a real SDK step keeps its lease through a late deadline and late PID."""

import asyncio
import contextvars
import shutil
import time
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from owlbear_memory import MemoryCategory, MemoryEngine

from owlbear_delivery_next.change_contracts import tools
from owlbear_delivery_next.change_contracts.memory_curation_tools import MemoryCurationResult
from owlbear_delivery_next.change_contracts.models import StepKind
from owlbear_delivery_next.change_contracts.permissions import Policy
from owlbear_delivery_next.local_system import maintenance, processes
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.local_system.slots import Slots
from owlbear_delivery_next.machine_host import curation
from owlbear_delivery_next.runtimes import loop_owner, maintained, sdk_adapter, sdk_teardown
from owlbear_delivery_next.runtimes.session_result import Run
from owlbear_delivery_next.settings import config
from owlbear_delivery_next.settings.config import GlobalLayer
from owlbear_delivery_next.state_store import settings_carry
from owlbear_delivery_next.state_store.store import update_layer

OWNER = contextvars.ContextVar("owner", default="none")

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

    def __init__(self, clock, *, resistant, absent, payload=PAYLOAD, jump=2.0):
        self.clock, self.resistant, self.absent = clock, resistant, absent
        self.payload, self.jump = payload, jump
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
            self.clock.now += self.jump  # the valid result arrives after the session budget
            st = self.steps[0]
            (st.cfg.worktree / "owned.txt").write_text("the session's output")  # data the session owns
            _, accepted = st.gate.call(st.cfg.submit, self.payload.model_dump())
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

    def make(*, resistant, absent, payload=PAYLOAD, jump=2.0):
        world = World(clock, resistant=resistant, absent=absent, payload=payload, jump=jump)
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


def test_a_late_pid_from_a_delivered_in_bs_context_updates_only_a(tmp_path):
    owner = manager(Slots(lambda: 2))
    root_a, root_b = tmp_path / "a", tmp_path / "b"
    root_a.mkdir()
    root_b.mkdir()
    a_pids, late_child, b_pid = {ROOT: BIRTH[ROOT]}, {CHILD: BIRTH[CHILD]}, 5151
    callbacks = {}

    def run_a(bound):
        async def main():
            callbacks["a"] = bound.journal.event  # the run_owned callback that owns A's captured identity
            bound.journal.event({"event": "pids", "pids": dict(a_pids)})
            return Run(
                bound.session_id, ending="deadline", termination=processes.Termination(confirmed=False, unknown=(ROOT,))
            )

        return loop_owner.run(main())

    assert owner.slots.take("p", "pack:a", 1, 2) == 1
    held = maintained.run_owned(owner, cfg_for(root_a, []), run_a, project="p", slot="pack:a", kind="pack")
    assert held.termination.confirmed is False

    def run_b(bound):
        async def main():
            assert OWNER.get() == "b"  # B's admission context is live inside the real loop thread
            bound.journal.event({"event": "pids", "pids": {b_pid: 300.0}})
            callbacks["a"]({"event": "pids", "pids": dict(late_child)})  # A's delayed PID, delivered from B's context
            return Run(bound.session_id, ending="result", termination=processes.Termination(confirmed=True))

        return loop_owner.run(main())

    assert owner.slots.take("p", "pack:b", 1, 2) == 1
    token = OWNER.set("b")
    try:
        released = maintained.run_owned(owner, cfg_for(root_b, []), run_b, project="p", slot="pack:b", kind="pack")
    finally:
        OWNER.reset(token)

    assert released.termination.confirmed is True
    leases = {s["workspace"]: s for s in owner.read()["sessions"]}
    assert leases[str(root_a)]["state"] == "held"
    assert leases[str(root_b)]["state"] == "released"
    assert owner.records("p", "pack", "pack:a", {**a_pids, **late_child})  # A holds its own and its late PID
    assert not owner.records("p", "pack", "pack:a", {b_pid: 300.0})  # B's PID never lands on A
    assert owner.records("p", "pack", "pack:b", {b_pid: 300.0})
    assert not owner.records("p", "pack", "pack:b", late_child)  # A's late PID never lands on B
    assert not owner.retained(str(root_b))
    assert owner.retained(str(root_a))

    fresh = manager(Slots(lambda: 2, closed=True))
    fresh.slots.open()
    assert fresh.retained(str(root_a))
    assert owner.slots.take("p", "pack:c", 1, 2) == 1  # one of two slots is still A's; B's is free
    assert owner.slots.take("p", "pack:d", 1, 2) == 0  # the global quota keeps A's slot


def curator(root, **changes):
    """The curator role in Global, written by the production layer writer; a run's settings are never guessed."""
    if not DataRepo(root).global_path.exists():
        settings_carry.carry(DataRepo(root))

    def change(glob: GlobalLayer) -> GlobalLayer:
        agent = glob.agents.get("curator", config.Agent()).model_copy(update=changes)
        return glob.model_copy(update={"agents": glob.agents | {"curator": agent}})

    update_layer(DataRepo(root).global_path, GlobalLayer, change)


@pytest.mark.parametrize(("resistant", "absent", "held"), [(True, None, True), (False, False, False)])
def test_a_curation_worker_keeps_its_workspace_only_while_its_deadline_lease_is_held(
    bridge, shared_repo, resistant, absent, held
):
    make, _ = bridge
    data = shared_repo[0]
    folder = data / "shop" / "memory"
    folder.mkdir(parents=True)
    MemoryEngine(folder).save(
        title="Lesson", content="Lesson: what to know", categories=[MemoryCategory.PROCESS], confidence=0.8,
        source_agent="builder", scope_agents=[],
    )  # fmt: skip
    curator(data, subagents=False, minutes=1)  # one minute: the session budget the fake clock passes
    world = make(
        resistant=resistant,
        absent=absent,
        payload=MemoryCurationResult(summary="ok", entries=[]),
        jump=61.0,
    )
    slots = Slots(lambda: 1)
    owner = manager(slots)
    job = curation.Curation(slots, shared=lambda: DataRepo(data), ownership=owner)

    assert job.start("shop") == ["shop"]
    for _ in range(400):
        if world.accepted and job.working() == ([curation.LINGERING] if held else []):
            break
        time.sleep(0.02)
    assert job.working() == ([curation.LINGERING] if held else [])

    assert world.accepted == [False]  # the late valid result is never accepted
    [lease] = owner.read()["sessions"]
    workspace = Path(lease["workspace"])
    assert lease["state"] == ("held" if held else "released")
    assert owner.retained(str(workspace)) is held
    assert workspace.exists() is held  # the workspace survives only with the held lease
    assert (workspace / "owned.txt").exists() is held
    assert slots.counts(curation.SLOT)[2] == (1 if held else 0)
    if held:
        shutil.rmtree(workspace)  # the test's own leftover; production keeps it for the owner to reconcile
