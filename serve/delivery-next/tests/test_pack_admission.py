"""A design pack session's slot follows its maintenance ownership, not the return of its runner."""

import subprocess
from datetime import UTC, datetime

import pytest

from owlbear_delivery_next.change_contracts import tools
from owlbear_delivery_next.change_contracts.models import StepKind
from owlbear_delivery_next.change_contracts.permissions import Policy
from owlbear_delivery_next.local_system import maintenance, processes
from owlbear_delivery_next.local_system.slots import Slots
from owlbear_delivery_next.pack_runs import pack_job, pack_run
from owlbear_delivery_next.pack_runs.scratch import scratch
from owlbear_delivery_next.project_host import session_slots
from owlbear_delivery_next.project_host.host import Host
from owlbear_delivery_next.runtimes import sdk_adapter
from owlbear_delivery_next.runtimes.session_result import Run
from owlbear_delivery_next.state_store.store import Store
from owlbear_delivery_next.workflow_steps import sessions

AT = datetime(2026, 10, 25, tzinfo=UTC)


def host_with(tmp_path, slots):
    path = tmp_path / "repo"
    path.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=path, check=True, capture_output=True)  # noqa: S607
    store = Store.open(path)
    host = Host(store, tmp_path / "host", spawn=lambda _s: None, scan=lambda *_a: {}, group=lambda _g: {})
    host.slots = slots
    host.maintenance = maintenance.Maintenance(slots, boot=lambda: 10.0, observe=lambda *_args: False)
    return host, store


def session(root):
    return sdk_adapter.Session(
        kind=StepKind.REVIEW,
        worktree=root,
        session_id="pack-update",
        message="Update the pack",
        resume=False,
        policy=Policy(root),
        observe=lambda: tools.Worktree("", ""),
        checks=(),
        model="synthetic-model",
    )


def test_unknown_pack_session_keeps_its_slot_and_blocks_its_successor(tmp_path):
    slots = Slots(lambda: 1)
    host, store = host_with(tmp_path, slots)
    unknown = Run(
        "synthetic",
        termination=processes.Termination(confirmed=False, problems=("request task pending",)),
    )
    job = pack_job.Job(store, pack_job.Live(update=lambda _store, _cfg: unknown))
    session_slots.packed(host, job)

    root = tmp_path / "wt"
    root.mkdir()
    assert job.live.update(store, session(root)) is unknown

    project = session_slots.project(host)
    assert slots.take(project, "successor", 1, 1) == 0
    assert host.maintenance.pending(kind="pack")


def test_an_unknown_pack_workspace_outlives_its_job_until_its_processes_are_proven_gone(tmp_path):
    host, store = host_with(tmp_path, Slots(lambda: 2))
    job = pack_job.Job(store, pack_job.Live())
    session_slots.packed(host, job)
    job.state |= {"state": "running", "run": "run-one", "workspace": str(job.workspace)}
    job.workspace.mkdir(parents=True)

    ident = host.maintenance.begin(session_slots.project(host), "pack:one", "pack", str(job.workspace))
    host.maintenance.failed(ident, RuntimeError("the session ended without a result"))
    job._finish("failed", "the update ended")  # noqa: SLF001 - the update's own end, as the run calls it
    assert job.workspace.is_dir()


def test_a_proven_pack_workspace_is_removed_when_its_job_ends(tmp_path):
    host, store = host_with(tmp_path, Slots(lambda: 2))
    job = pack_job.Job(store, pack_job.Live())
    session_slots.packed(host, job)
    job.state |= {"state": "running", "run": "run-two", "workspace": str(job.workspace)}
    job.workspace.mkdir(parents=True)

    ident = host.maintenance.begin(session_slots.project(host), "pack:two", "pack", str(job.workspace))
    host.maintenance.finished(ident, Run("synthetic", termination=processes.Termination(confirmed=True)))
    job._finish("failed", "the update ended")  # noqa: SLF001 - the update's own end, as the run calls it
    assert not job.workspace.exists()


def test_a_legacy_running_updater_root_is_adopted_before_it_can_be_deleted(tmp_path):
    host, store = host_with(tmp_path, Slots(lambda: 2))
    legacy = store.root / pack_run.UPDATER
    legacy.mkdir(parents=True)
    job = pack_job.Job(store, pack_job.Live())
    job.state |= {"state": "running", "run": "pre-ledger"}  # written before per-run workspaces existed
    session_slots.packed(host, job)

    assert legacy.is_dir()
    assert host.maintenance.pending(kind="pack")


def test_an_unproven_challenger_scratch_outlives_its_call_and_a_proven_one_is_removed(tmp_path):
    host, store = host_with(tmp_path, Slots(lambda: 2))
    unknown = Run("synthetic", termination=processes.Termination(confirmed=False, problems=("request task pending",)))
    proven = Run("synthetic", termination=processes.Termination(confirmed=True))
    results = iter([unknown, proven])
    job = pack_job.Job(store, pack_job.Live(challenge=lambda _store, _cfg: next(results)))
    session_slots.packed(host, job)

    with scratch("owlbear-pack-", job.keeps) as unproven:
        assert job.live.challenge(store, session(unproven)) is unknown
    with scratch("owlbear-pack-", job.keeps) as done:
        assert job.live.challenge(store, session(done)) is proven

    assert unproven.is_dir()
    assert not done.exists()


def test_the_machine_pack_lock_stays_blocked_while_a_pack_lease_is_unproven(tmp_path):
    host, store = host_with(tmp_path, Slots(lambda: 2))
    job = pack_job.Job(store, pack_job.Live())
    session_slots.packed(host, job)
    ident = host.maintenance.begin(session_slots.project(host), "pack:three", "pack", str(tmp_path / "w"))
    host.maintenance.failed(ident, RuntimeError("the session ended without a result"))

    with pytest.raises(pack_job.Busy):
        job._claim()  # noqa: SLF001 - the claim a starting run takes


def usage_unread(termination: processes.Termination | None) -> sessions.UsageUnreadError:
    """What ``sessions.run``, the default updater and challenger, raises when the model check could not run."""
    run = Run("pack-update", ending="result", termination=termination, usage_unread="the model's use was unread")
    return sessions.UsageUnreadError(run, "pack-update")


@pytest.mark.parametrize("live", ["update", "challenge"])
def test_a_usage_unread_session_confirmed_gone_releases_its_slot_and_still_raises(tmp_path, live):
    """Review 5655440664: the error carries a run whose processes were confirmed gone; that proof is kept.

    The slot goes back with no reboot, the next pack session is admitted, and the same error still reaches the caller.
    """
    slots = Slots(lambda: 1)
    host, store = host_with(tmp_path, slots)
    raised = usage_unread(processes.Termination(confirmed=True))

    def gated(_store, _cfg):
        raise raised

    job = pack_job.Job(store, pack_job.Live(**{live: gated}))
    session_slots.packed(host, job)
    root = tmp_path / "wt"
    root.mkdir()
    with pytest.raises(sessions.UsageUnreadError) as caught:
        getattr(job.live, live)(store, session(root))
    assert caught.value is raised
    [lease] = host.maintenance.read()["sessions"]
    project = session_slots.project(host)
    assert (lease["state"], host.maintenance.pending("pack"), slots.counts(project)[2]) == ("released", False, 0)
    assert slots.take(project, "successor", 1, 1) == 1


@pytest.mark.parametrize(
    "raised",
    [usage_unread(processes.Termination(confirmed=False, problems=("request task pending",))), usage_unread(None),
     RuntimeError("no run returned")],
    ids=["usage-unread-unconfirmed", "usage-unread-no-termination", "generic"],
)  # fmt: skip
def test_a_session_error_without_confirmed_termination_still_holds_its_slot(tmp_path, raised):
    slots = Slots(lambda: 1)
    host, store = host_with(tmp_path, slots)

    def gated(_store, _cfg):
        raise raised

    job = pack_job.Job(store, pack_job.Live(update=gated))
    session_slots.packed(host, job)
    root = tmp_path / "wt"
    root.mkdir()
    with pytest.raises(type(raised)):
        job.live.update(store, session(root))
    [lease] = host.maintenance.read()["sessions"]
    assert (lease["state"], host.maintenance.pending("pack")) == ("held", True)
    assert slots.take(session_slots.project(host), "successor", 1, 1) == 0
