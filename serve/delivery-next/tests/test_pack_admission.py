"""An Impeccable session's slot follows its maintenance ownership, not the return of its runner."""

import functools
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from owlbear_delivery_next.change_contracts import tools
from owlbear_delivery_next.change_contracts.models import StepKind
from owlbear_delivery_next.change_contracts.permissions import Policy
from owlbear_delivery_next.github.gh import GhProvider
from owlbear_delivery_next.github.provider import PullRequest
from owlbear_delivery_next.impeccable_runs import pack_admission, pack_job, pack_run, pack_state
from owlbear_delivery_next.impeccable_runs.scratch import scratch
from owlbear_delivery_next.local_system import maintenance, processes
from owlbear_delivery_next.local_system.slots import Slots
from owlbear_delivery_next.project_host import session_slots
from owlbear_delivery_next.project_host.host import Host
from owlbear_delivery_next.runtimes import sdk_adapter
from owlbear_delivery_next.runtimes.session_result import Run
from owlbear_delivery_next.state_store import pack_run_record, project_home, registry
from owlbear_delivery_next.state_store.store import Store
from owlbear_delivery_next.workflow_steps import sessions

AT = datetime(2026, 10, 25, tzinfo=UTC)


def host_with(tmp_path, slots):
    path = tmp_path / "repo"
    path.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=path, check=True, capture_output=True)  # noqa: S607
    store = Store.open(path)
    host = Host(store, tmp_path / "host", spawn=lambda _s: None, members=lambda _ids: {})
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
        job._claim(job._alone)  # noqa: SLF001 - the claim a starting run takes


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


def registered(tmp_path, records: dict[str, str]) -> None:
    """Projects in this machine's registry (under the isolated HOME), each with its run record's text, if any."""
    projects = [registry.Project(id=n, path=str(tmp_path / n), added_at=AT) for n in records]
    with registry.locked():
        registry.save(registry.Machine(projects=projects))
    for name, text in records.items():
        if text:
            project_home.home(name).mkdir(parents=True)
            (project_home.home(name) / pack_job.FILE).write_text(text)


def waiting(run: str) -> str:
    return json.dumps(pack_state.blank() | {"state": "waiting", "run": run})


def pull(number: int, head: str) -> PullRequest:
    return PullRequest(
        repository="maba-pag/owlbear", number=number, node_id=f"N{number}", head_branch=head, head_sha="a" * 40,
        url=f"https://github.com/maba-pag/owlbear/pull/{number}", base_branch="main", draft=False, state="open",
        merged=False,
    )  # fmt: skip


@pytest.mark.parametrize(
    ("records", "said"),
    [({"gamma": "{"}, "the Impeccable run record of gamma cannot be read"),
     ({"alpha": waiting("a"), "gamma": waiting("g")}, "Impeccable updates wait in alpha, gamma")],
    ids=["unreadable", "two-waiting"],
)  # fmt: skip
def test_an_unreadable_or_second_waiting_record_elsewhere_refuses_a_fresh_start_by_name(tmp_path, records, said):
    registered(tmp_path, {"beta": "", **records})
    github = SimpleNamespace(open_pull_requests=lambda *_a: ())
    job = pack_job.Job(Store(project_home.home("beta"), None, "beta"), pack_job.Live(github=lambda _root: github))
    with pytest.raises(pack_job.Busy, match=said):
        job.start()
    assert not (job.store.root / pack_job.FILE).exists()


def test_a_waiting_run_goes_on_only_as_itself_alone_and_with_no_pack_pull_request_but_its_own(tmp_path):
    registered(tmp_path, {"alpha": waiting("r-alpha"), "gamma": ""})
    root = project_home.home("alpha")
    version = pack_run_record.observed(root)[1]
    own = SimpleNamespace(open_pull_requests=lambda *_a: (pull(1, "pack/r-alpha"),))
    resumed = functools.partial(pack_admission.resumed, root, "alpha", version=version, github=own)

    resumed(run="r-alpha", branch="pack/r-alpha")  # its own pull request: it goes on
    with pytest.raises(pack_admission.Refused, match="record changed"):
        resumed(run="r-other", branch="pack/r-alpha")
    with pytest.raises(pack_admission.Refused, match="another Impeccable pull request is open"):
        resumed(run="r-alpha", branch="")  # before its publication, any pack pull request competes
    project_home.home("gamma").mkdir(parents=True)
    (project_home.home("gamma") / pack_job.FILE).write_text(waiting("r-gamma"))
    with pytest.raises(pack_admission.Refused, match="also open in gamma"):
        resumed(run="r-alpha", branch="pack/r-alpha")


def page(nodes: list[dict], total: int, cursor: str = "") -> dict:
    info = {"hasNextPage": bool(cursor), "endCursor": cursor or None}
    return {"data": {"repository": {"pullRequests": {"totalCount": total, "pageInfo": info, "nodes": nodes}}}}


def node(number: int, head: str, *, fork: bool = False) -> dict:
    return {"id": f"N{number}", "number": number, "url": f"https://github.com/maba-pag/owlbear/pull/{number}",
            "headRefName": head, "headRefOid": "a" * 40, "baseRefName": "main", "isDraft": False,
            "isCrossRepository": fork}  # fmt: skip


def served(pages: list[dict], cursors: list) -> GhProvider:
    """``gh`` answering each GraphQL page in turn, recording the cursor each request asked from."""

    def server(argv, body, _timeout, _cwd):
        assert "graphql" in argv
        cursors.append(json.loads(body)["variables"]["after"])
        return subprocess.CompletedProcess(argv, 0, json.dumps(pages.pop(0)).encode(), b"")

    return GhProvider(Path("/nowhere"), runner=server)


def test_open_pack_pull_requests_are_read_to_the_last_page_and_a_list_cut_short_refuses_a_start(tmp_path):
    """GitHub matches only an exact head, so every open pull request is paged through and matched by prefix here."""
    cursors: list = []
    whole = [page([node(1, "pack/a"), node(2, "feature")], 4, "c1"), page([node(3, "pack/b", fork=True),
             node(4, "pack/c")], 4)]  # fmt: skip
    found = served(whole, cursors).open_pull_requests("maba-pag/owlbear", "pack/")
    assert ([p.number for p in found], cursors) == ([1, 4], [None, "c1"])

    cut = served([page([node(1, "pack/a")], 2)], [])  # GitHub counts two; its only page lists one
    job = pack_job.Job(Store(tmp_path / "store"), pack_job.Live(github=lambda _root: cut))
    with pytest.raises(pack_job.Busy, match="read 1 of 2 open pull requests"):
        job.start()
    assert (job.read()["state"], (job.store.root / pack_job.FILE).exists()) == ("idle", False)
