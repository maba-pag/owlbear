"""Item 5 slice 4: automatic memory curation runs one curator session per memory folder of the shared repository."""

import threading
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from owlbear_memory import MemoryCategory, MemoryEngine

from owlbear_delivery_next.change_contracts import memory_curation_tools, tools
from owlbear_delivery_next.change_contracts.memory_curation_tools import Judged, MemoryCurationResult
from owlbear_delivery_next.local_system import maintenance, processes
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.local_system.processes import Termination
from owlbear_delivery_next.local_system.slots import Slots
from owlbear_delivery_next.machine_host import curation, registry
from owlbear_delivery_next.runtimes.session_result import Run
from owlbear_delivery_next.settings import config
from owlbear_delivery_next.settings.config import GlobalLayer
from owlbear_delivery_next.state_store import settings_carry, store
from owlbear_delivery_next.state_store.store import update_layer


def pending(folder: Path, title: str):
    return MemoryEngine(folder).save(
        title=title, content=f"{title}: what to know", categories=[MemoryCategory.PROCESS], confidence=0.8,
        source_agent="builder", scope_agents=[],
    )  # fmt: skip


@pytest.fixture
def root(shared_repo) -> Path:
    data = shared_repo[0]
    for name in ("owlbear", "shop", "memory"):  # "memory" is Global: never a folder to curate
        (data / name / "memory").mkdir(parents=True) if name != "memory" else (data / name).mkdir()
    (data / "decisions").mkdir()  # a folder without memory
    return data


def finished(job: curation.Curation) -> None:
    for _ in range(200):
        if not job.working():
            return
        time.sleep(0.02)
    pytest.fail("the curation did not finish")


def drained(job: curation.Curation) -> None:
    for _ in range(200):
        if job.worker is None:
            return
        time.sleep(0.02)
    pytest.fail("the curation queue did not drain")


def test_the_folders_are_the_shared_repositorys_project_memory_folders_owlbears_included(root) -> None:
    job = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root))
    got = job.read()
    assert [(f["folder"], f["state"]) for f in got["folders"]] == [("owlbear", "never"), ("shop", "never")]
    with pytest.raises(ValueError, match="no memory folder"):
        job.start("memory")


def test_a_run_curates_one_folder_as_the_curator_and_keeps_its_report_and_what_it_skipped(root) -> None:
    left, done = pending(root / "shop" / "memory", "Unsure lesson"), pending(root / "shop" / "memory", "Clear one")
    seen = []

    def run(cfg) -> Run:
        seen.append(cfg)
        report = MemoryCurationResult(summary="1 pruned, 1 skipped", entries=[
            Judged(entry_id=left.id, action="skipped", confidence=60, reason="only one project shows it"),
            Judged(entry_id=done.id, action="pruned", confidence=97),
        ])  # fmt: skip
        MemoryEngine(root / "shop" / "memory").delete(done.id, done.updated_at)
        return Run(cfg.session_id, ending="result", payload=report, termination=Termination(confirmed=True))

    job = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root), run=run)
    assert job.start("shop") == ["shop"]
    finished(job)

    (cfg,) = seen
    assert (cfg.role, cfg.memory, cfg.submit) == (tools.CURATOR, root / "shop" / "memory", memory_curation_tools.SUBMIT)
    assert "`shop`" in cfg.message
    assert cfg.policy.write is False
    shop = {f["folder"]: f for f in job.read()["folders"]}["shop"]
    assert (shop["state"], shop["summary"], [e["action"] for e in shop["entries"]]) == (
        "done", "1 pruned, 1 skipped", ["skipped", "pruned"]
    )  # fmt: skip
    assert shop["skipped"] == {left.id: left.revision}  # unchanged, an idle run passes it by


def test_a_run_without_a_report_or_while_fenced_fails_with_its_reason(root) -> None:
    def silent(cfg) -> Run:
        return Run(cfg.session_id, ending="error", detail="model unavailable", termination=Termination(confirmed=True))

    job = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root), run=silent)
    job.start("owlbear")
    finished(job)
    fenced = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root), run=silent, fenced=lambda: "updating")
    fenced.start("shop")
    finished(fenced)

    runs = {f["folder"]: f for f in fenced.read()["folders"]}
    assert (runs["owlbear"]["state"], "model unavailable" in runs["owlbear"]["reason"]) == ("failed", True)
    assert (runs["shop"]["state"], runs["shop"]["reason"]) == ("failed", "updating")


def test_without_a_shared_repository_nothing_is_curated() -> None:
    job = curation.Curation(Slots(lambda: 1), shared=lambda: None)
    assert job.read() == {"available": False, "reason": curation.NO_SHARED, "folders": []}
    with pytest.raises(ValueError, match="no shared repository"):
        job.start("all")


def test_a_trigger_starts_only_folders_with_pending_entries_no_run_saw_and_as_its_own_setting_says(root) -> None:
    """The merge and idle triggers: a skipped entry starts no run until it changes; each trigger's machine setting
    is off, on (not while paused, the default) or on even while paused (the owner, 2026-10-23)."""
    from owlbear_delivery_next.machine_host import registry  # noqa: PLC0415

    left = pending(root / "shop" / "memory", "Unsure lesson")
    report = MemoryCurationResult(
        summary="1 skipped", entries=[Judged(entry_id=left.id, action="skipped", confidence=50)]
    )
    runs = []

    def run(cfg) -> Run:
        runs.append(cfg.memory.parent.name)
        return Run(cfg.session_id, ending="result", payload=report, termination=Termination(confirmed=True))

    paused = [True]
    job = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root), run=run, paused=lambda: paused[0])
    assert (job.due("shop"), job.due("owlbear")) == (True, False)
    assert job.nudge(None, "idle") == []  # paused: "on" holds it
    paused[0] = False
    assert job.nudge(None, "idle") == ["shop"]
    finished(job)
    assert (job.due("shop"), job.nudge(["shop"], "merge")) == (False, [])  # unchanged: no other run

    MemoryEngine(root / "shop" / "memory").edit(
        left.id, {"content": "Unsure lesson: now with evidence"}, left.updated_at
    )
    saved = registry.load()
    chosen = {"curate_after_merge": "paused", "curate_when_idle": "off"}
    registry.configure(saved.settings.model_copy(update=chosen), registry.revision(saved.settings))
    assert job.nudge(["shop"], "idle") == []  # idle curation off
    paused[0] = True
    assert job.nudge(["shop"], "merge") == ["shop"]  # changed, and the merge runs it while paused
    finished(job)
    assert runs == ["shop", "shop"]


def test_an_entry_saved_during_a_run_stays_due_and_a_trigger_meanwhile_runs_the_folder_once_more(root) -> None:
    """Sol: only what the curator could see is marked seen; a merge during its run is not lost."""
    pending(root / "shop" / "memory", "First lesson")
    runs = []

    def run(cfg) -> Run:
        runs.append(cfg.session_id)
        if len(runs) == 1:  # an agent saves while the curator runs, and its Change merges
            pending(root / "shop" / "memory", "Saved meanwhile")
            assert job.nudge(["shop"], "merge") == []
        report = MemoryCurationResult(summary="judged", entries=[])
        return Run(cfg.session_id, ending="result", payload=report, termination=Termination(confirmed=True))

    job = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root), run=run)
    job.start("shop")
    finished(job)
    assert (len(runs), job.due("shop")) == (2, False)  # the follow-up saw it


def test_one_folder_that_fails_never_strands_the_next_and_a_restart_ends_interrupted_runs(root) -> None:
    def run(cfg) -> Run:
        if "owlbear" in cfg.session_id:
            broke = "the runtime broke"
            raise RuntimeError(broke)
        return Run(cfg.session_id, ending="result", payload=MemoryCurationResult(summary="ok", entries=[]),
                   termination=Termination(confirmed=True))  # fmt: skip

    job = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root), run=run)
    job.start("all")
    drained(job)
    states = {f["folder"]: (f["state"], f["reason"]) for f in job.read()["folders"]}
    assert states == {
        "owlbear": ("failed", "RuntimeError: the runtime broke"),
        "shop": ("failed", curation.LEFT),
    }
    assert job.slots.counts(curation.SLOT)[2] == 1

    job._save("shop", curation.FolderRun(state="running"))  # noqa: SLF001 - OwlBear stops while it runs
    again = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root))
    assert {f["folder"]: f["state"] for f in again.read()["folders"]}["shop"] == "failed"


def test_processes_that_may_still_run_keep_their_slot_and_the_machine_busy_until_they_are_gone(
    root, monkeypatch
) -> None:
    alive = [True]
    monkeypatch.setattr(processes, "alive", lambda _pid, _created: alive[0])
    slots = Slots(lambda: 2)

    def run(cfg) -> Run:
        return Run(cfg.session_id, ending="result", payload=MemoryCurationResult(summary="ok", entries=[]),
                   runtime_pid=4242, pids={4242: 1.0},
                   termination=Termination(confirmed=False, survivors=(4242,)))  # fmt: skip

    job = curation.Curation(slots, shared=lambda: DataRepo(root), run=run)
    job.start("shop")
    for _ in range(200):
        if job.queue == []:
            break
        time.sleep(0.02)
    assert (job.working(), slots.counts(curation.SLOT)[2]) == ([curation.LINGERING], 1)
    assert curation.Curation(Slots(lambda: 2), shared=lambda: DataRepo(root)).left == {4242: 1.0}
    alive[0] = False
    assert (job.working(), slots.counts(curation.SLOT)[2]) == ([], 0)


def test_a_linked_memory_folder_is_never_curated(root) -> None:
    """Copilot on #587: a project folder whose memory links to Global or outside is not a folder to curate."""
    (root / "alias").mkdir()
    (root / "alias" / "memory").symlink_to(root / "memory")
    listed = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root)).read()["folders"]
    assert [f["folder"] for f in listed] == ["owlbear", "shop"]


def test_a_run_keeps_its_processes_on_file_while_it_runs_and_a_restart_holds_their_slot(root, monkeypatch) -> None:
    """Copilot on #587: a host that stops mid-run leaves the session's processes known, their slot taken."""
    alive = [True]
    monkeypatch.setattr(processes, "alive", lambda _pid, _created: alive[0])
    on_file = []

    def run(cfg) -> Run:
        cfg.journal.event({"event": "pids", "pids": {"4242": None}})
        on_file.append(curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root)).load().left)
        return Run(cfg.session_id, ending="result", payload=MemoryCurationResult(summary="ok", entries=[]),
                   termination=Termination(confirmed=True))  # fmt: skip

    job = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root), run=run)
    job.start("shop")
    finished(job)
    assert (on_file, job.load().left) == ([{4242: None}], {})  # known while it ran, cleared once confirmed gone

    job._save("shop", curation.FolderRun(state="running"))  # noqa: SLF001 - the host stops mid-run
    runs = job.load()
    runs.left = {4242: None}
    job._write(runs)  # noqa: SLF001
    job.maintenance.path.unlink()  # synthetic pre-ledger installation, after every new-format lease ended
    slots = Slots(lambda: 1, closed=True)
    restarted = curation.Curation(slots, shared=lambda: DataRepo(root))
    assert (slots.counts(curation.SLOT)[2], restarted.working()) == (1, [curation.LINGERING])
    alive[0] = False
    assert (restarted.working(), slots.counts(curation.SLOT)[2]) == ([curation.LINGERING], 1)


def test_pids_left_after_an_earlier_empty_import_are_held_before_they_can_be_cleared(root, monkeypatch) -> None:
    """Review F1: an import already recorded must not let a later host's PIDs be cleared as history."""
    monkeypatch.setattr(processes, "alive", lambda _pid, _created: False)
    first = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root))  # records the file's empty import
    runs = first.load()
    runs.left = {4242: None}
    first._write(runs)  # noqa: SLF001 - a later host's PIDs, written after that import
    slots = Slots(lambda: 1, closed=True)
    restarted = curation.Curation(slots, shared=lambda: DataRepo(root))
    assert (restarted.working(), slots.counts(curation.SLOT)[2], restarted.left) == (
        [curation.LINGERING],
        1,
        {4242: None},
    )


def test_a_keyless_running_row_after_an_earlier_empty_import_gets_conservative_ownership_before_it_is_failed(
    root, monkeypatch
) -> None:
    """Review F1: a running row with no lease key must be held before the constructor rewrites it."""
    monkeypatch.setattr(processes, "alive", lambda _pid, _created: False)
    first = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root))
    first.load()  # records the file's empty import
    first._save("shop", curation.FolderRun(state="running"))  # noqa: SLF001 - a host stopped mid-run, keyless
    slots = Slots(lambda: 1, closed=True)
    restarted = curation.Curation(slots, shared=lambda: DataRepo(root))
    shop = {f["folder"]: f for f in restarted.read()["folders"]}["shop"]
    assert (shop["state"], slots.counts(curation.SLOT)[2]) == ("failed", 1)
    restarted_again = curation.Curation(slots, shared=lambda: DataRepo(root))
    assert slots.counts(curation.SLOT)[2] == 1, "a restart duplicated the keyless row's hold"
    assert restarted_again.read()["folders"]


def test_a_run_unconfirmed_without_processes_to_watch_retains_its_slot_and_says_so(root) -> None:
    slots = Slots(lambda: 1)

    def run(cfg) -> Run:
        return Run(cfg.session_id, ending="error", detail="runtime PID unknown",
                   termination=Termination(confirmed=False))  # fmt: skip

    job = curation.Curation(slots, shared=lambda: DataRepo(root), run=run)
    job.start("shop")
    drained(job)
    shop = {f["folder"]: f for f in job.read()["folders"]}["shop"]
    assert (shop["state"], curation.UNKNOWN in shop["reason"], slots.counts(curation.SLOT)[2]) == ("failed", True, 1)
    assert slots.take("another-project", "c1", 1, 1) == 0


def test_a_run_waiting_for_a_slot_never_starts_once_an_update_or_a_stop_fences_it(root) -> None:
    slots, fence = Slots(lambda: 1), [""]
    assert slots.take("0123456789abcdef", "a-change", 1, 1) == 1  # a project's step holds the only slot
    job = curation.Curation(slots, shared=lambda: DataRepo(root), run=lambda _cfg: pytest.fail("it ran"),
                            fenced=lambda: fence[0])  # fmt: skip
    job.start("shop")
    time.sleep(0.2)
    fence[0] = "an update runs"
    slots.give("0123456789abcdef", "a-change")
    finished(job)
    shop = {f["folder"]: f for f in job.read()["folders"]}["shop"]
    assert (shop["state"], shop["reason"], slots.counts(curation.SLOT)[2]) == ("failed", "an update runs", 0)


def test_a_sweep_paused_before_it_gives_a_slot_back_never_costs_a_successor_its_reservation(root, monkeypatch) -> None:
    """Review on 552d02b: the sweep releases the ledger, then gives; a successor admitted meanwhile keeps the slot."""
    alive = [True]
    monkeypatch.setattr(processes, "alive", lambda _pid, _created: alive[0])
    slots, calls = Slots(lambda: 1), []
    entered, finish, reached, release = threading.Event(), threading.Event(), threading.Event(), threading.Event()

    def run(cfg) -> Run:
        calls.append(cfg.session_id)
        if len(calls) == 1:
            return Run(cfg.session_id, ending="result", payload=MemoryCurationResult(summary="ok", entries=[]),
                       runtime_pid=4242, pids={4242: 1.0},
                       termination=Termination(confirmed=False, survivors=(4242,)))  # fmt: skip
        entered.set()
        finish.wait(5)
        return Run(cfg.session_id, ending="result", payload=MemoryCurationResult(summary="ok", entries=[]),
                   termination=Termination(confirmed=True))  # fmt: skip

    job = curation.Curation(slots, shared=lambda: DataRepo(root), run=run)
    job.start("shop")
    drained(job)
    alive[0] = False
    give, paused = slots.give, [True]

    def gate(project: str, key: str) -> None:
        if paused[0]:
            paused[0] = False
            reached.set()
            release.wait(5)
        give(project, key)

    monkeypatch.setattr(slots, "give", gate)
    sweeper = threading.Thread(target=job.maintenance.sweep)
    sweeper.start()
    try:
        assert reached.wait(5)
        job.start("shop")
        assert not entered.wait(0.2)  # the old reservation still holds the only slot
        release.set()
        sweeper.join(5)
        assert entered.wait(5)
        assert (slots.counts(curation.SLOT)[2], slots.take("another-project", "c1", 1, 1)) == (1, 0)
    finally:
        release.set()
        finish.set()
        sweeper.join(5)
    finished(job)
    assert {f["folder"]: f["state"] for f in job.read()["folders"]}["shop"] == "done"


def test_an_explicit_reboot_recovery_is_the_gate_and_reused_pids_never_block_a_new_admission(root, monkeypatch) -> None:
    """Review on 552d02b: after the owner confirms a reboot, PIDs kept as history must not block forever."""
    alive, boot, calls = [True], [1.0], []
    monkeypatch.setattr(processes, "alive", lambda _pid, _created: alive[0])
    slots = Slots(lambda: 1)
    ledger = maintenance.Maintenance(slots, boot=lambda: boot[0], observe=lambda _pid, _created: alive[0])

    def run(cfg) -> Run:
        calls.append(cfg.session_id)
        if len(calls) == 1:
            cfg.journal.event({"event": "pids", "pids": {"4242": None}})  # a reused PID now alive, identity unknown
            return Run(cfg.session_id, ending="error", detail="runtime PID unknown",
                       termination=Termination(confirmed=False, survivors=(4242,)))  # fmt: skip
        return Run(cfg.session_id, ending="result", payload=MemoryCurationResult(summary="ok", entries=[]),
                   termination=Termination(confirmed=True))  # fmt: skip

    job = curation.Curation(slots, shared=lambda: DataRepo(root), run=run, ownership=ledger)
    job.start("shop")
    drained(job)
    assert job.working() == [curation.LINGERING]
    (session,) = ledger.read()["sessions"]

    boot[0] = 2.0  # the owner confirmed a reboot since the failed session
    ledger.recover(session["id"], rebooted=True)
    assert job.working() == []
    restarted = curation.Curation(slots, shared=lambda: DataRepo(root), run=run, ownership=ledger)
    assert restarted.working() == []

    job.start("shop")
    finished(job)
    assert {f["folder"]: f["state"] for f in job.read()["folders"]}["shop"] == "done"
    with pytest.raises(LookupError):
        ledger.finished(session["id"], Run(session["id"], ending="result", termination=Termination(confirmed=True)))
    recovered = next(s for s in ledger.read()["sessions"] if s["id"] == session["id"])
    assert (recovered["state"], Path(session["workspace"]).is_dir(), ledger.retained(session["workspace"])) == (
        "recovered", True, True,
    )  # fmt: skip


def older_unknown_run(job: curation.Curation, started: datetime) -> None:
    """The record an older host left: failed with its termination unknown, no PID map and no ledger key."""
    reason = f"ended error: {curation.UNKNOWN}; synthetic unconfirmed runtime"
    job._save("shop", curation.FolderRun(state="failed", started_at=started, ended_at=started, reason=reason))  # noqa: SLF001


@pytest.mark.parametrize("ledger", ["empty", "imported"])
def test_an_older_hosts_unknown_curation_run_holds_one_slot_at_restart_and_its_start_never_runs(root, ledger) -> None:
    first = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root))
    first.maintenance.path.unlink()  # a pre-ledger installation
    if ledger == "imported":  # the old source was imported already, by an earlier adoption of the same file
        first.maintenance._save(maintenance.Ledger(imported=[str(first.path())]))  # noqa: SLF001
    older_unknown_run(first, datetime.now(UTC))
    slots = Slots(lambda: 1, closed=True)
    calls: list[str] = []
    restarted = curation.Curation(
        slots, shared=lambda: DataRepo(root), run=lambda cfg: calls.append(cfg.session_id) or pytest.fail("it ran")
    )
    assert slots.counts(curation.SLOT)[2] == 1
    restarted.start("shop")
    drained(restarted)
    shop = {f["folder"]: f for f in restarted.read()["folders"]}["shop"]
    assert (calls, shop["reason"], slots.counts(curation.SLOT)[2]) == ([], curation.LEFT, 1)


def test_a_recovered_older_unknown_curation_run_stays_released_across_repeated_restarts(root) -> None:
    first = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root))
    first.maintenance.path.unlink()
    older_unknown_run(first, datetime.now(UTC))
    adopted = curation.Curation(Slots(lambda: 1, closed=True), shared=lambda: DataRepo(root))
    [session] = adopted.maintenance.read()["sessions"]
    booted = adopted.maintenance.boot
    adopted.maintenance.boot = lambda: booted() + 1  # the computer rebooted since the failed session
    adopted.maintenance.recover(session["id"], rebooted=True)
    for _ in range(2):
        again = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root))
        assert (again.maintenance.pending("curation"), len(again.maintenance.read()["sessions"])) == (False, 1)


def unkeyed_2bf_row(job: curation.Curation, started: datetime) -> None:
    """The 2bf producer's row: failed unknown, its window open from its start, no FolderRun.key."""
    reason = f"ended error: {curation.UNKNOWN}; synthetic unconfirmed runtime"
    job._save(  # noqa: SLF001
        "shop",
        curation.FolderRun(state="failed", started_at=started, ended_at=started + timedelta(seconds=3), reason=reason),
    )


def test_a_2bf_unkeyed_unknown_curation_run_is_correlated_with_its_held_generation_without_a_second_lease(root) -> None:
    """The 2bf producer began its lease inside the run's own window and wrote no FolderRun.key."""
    first = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root))
    t0 = datetime(2026, 10, 25, 0, 0, 10, tzinfo=UTC)
    unkeyed_2bf_row(first, t0)
    lease = first.maintenance.begin(
        curation.SLOT, "curate:shop:2bf0000000000000", "curation", "", now=t0 + timedelta(seconds=1)
    )
    first.maintenance.failed(lease, RuntimeError("synthetic unconfirmed runtime"))
    slots = Slots(lambda: 1, closed=True)
    restarted = curation.Curation(slots, shared=lambda: DataRepo(root), run=lambda _cfg: pytest.fail("it ran"))
    assert restarted.load().folders["shop"].key == "curate:shop:2bf0000000000000"
    restarted.start("shop")
    drained(restarted)
    sessions = restarted.maintenance.read()["sessions"]
    assert (len(sessions), sessions[0]["id"] == lease, slots.counts(curation.SLOT)[2]) == (1, True, 1)


def test_a_2bf_unkeyed_recovered_curation_generation_stays_recovered_across_restarts(root) -> None:
    first = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root))
    t0 = datetime(2026, 10, 25, 0, 0, 10, tzinfo=UTC)
    unkeyed_2bf_row(first, t0)
    lease = first.maintenance.begin(
        curation.SLOT, "curate:shop:2bf0000000000001", "curation", "", now=t0 + timedelta(seconds=1)
    )
    first.maintenance.failed(lease, RuntimeError("synthetic unconfirmed runtime"))
    booted = first.maintenance.boot
    first.maintenance.boot = lambda: booted() + 1  # the computer rebooted since the failed session
    first.maintenance.recover(lease, rebooted=True)
    for _ in range(2):
        again = curation.Curation(Slots(lambda: 1, closed=True), shared=lambda: DataRepo(root))
        sessions = again.maintenance.read()["sessions"]
        assert (len(sessions), sessions[0]["state"], again.maintenance.pending("curation")) == (1, "recovered", False)


@pytest.mark.parametrize("unrelated", ["recovered", "held"])
def test_an_unrelated_earlier_curation_generation_never_covers_a_later_unkeyed_2bf_row(root, unrelated) -> None:
    """Same folder and slot prefix; the earlier lease began before this row, so it is its own generation."""
    first = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root))
    early = datetime(2026, 10, 25, 0, 0, 0, tzinfo=UTC)
    old = first.maintenance.begin(curation.SLOT, "curate:shop:2bf00000000000aa", "curation", "", now=early)
    first.maintenance.failed(old, RuntimeError("synthetic unconfirmed runtime"))
    if unrelated == "recovered":
        booted = first.maintenance.boot
        first.maintenance.boot = lambda: booted() + 1
        first.maintenance.recover(old, rebooted=True)
    later = datetime(2026, 10, 25, 0, 0, 20, tzinfo=UTC)
    unkeyed_2bf_row(first, later)  # the row's start and window lie after the earlier lease began
    slots = Slots(lambda: 1, closed=True)
    calls: list[str] = []
    restarted = curation.Curation(
        slots, shared=lambda: DataRepo(root), run=lambda cfg: calls.append(cfg.session_id) or pytest.fail("it ran")
    )
    sessions = {s["id"]: s for s in restarted.maintenance.read()["sessions"]}
    stamped = restarted.load().folders["shop"].key
    assert (sorted(s["state"] for s in sessions.values()), stamped != old, sessions[old]["state"]) == (
        ["held", unrelated] if unrelated == "recovered" else ["held", "held"],
        True,
        unrelated,
    )
    restarted.start("shop")
    drained(restarted)
    assert calls == []


def survived_run(root, monkeypatch, pid: int = 4242) -> curation.Curation:
    """A run whose process survives it: its PIDs are kept on the run's own lease and on the ledger's ``left``."""
    monkeypatch.setattr(processes, "alive", lambda _pid, _created: True)

    def run(cfg) -> Run:
        return Run(cfg.session_id, ending="result", payload=MemoryCurationResult(summary="ok", entries=[]),
                   runtime_pid=pid, pids={pid: 1.0},
                   termination=Termination(confirmed=False, survivors=(pid,)))  # fmt: skip

    job = curation.Curation(Slots(lambda: 2), shared=lambda: DataRepo(root), run=run)
    job.start("shop")
    drained(job)
    return job


def recovered_by_reboot(job: curation.Curation) -> None:
    [session] = job.maintenance.read()["sessions"]
    booted = job.maintenance.boot
    job.maintenance.boot = lambda: booted() + 1  # the computer rebooted since the run was left
    job.maintenance.recover(session["id"], rebooted=True)


def test_a_settled_runs_pids_are_not_held_again_when_rebuilt_after_its_recovery(root, monkeypatch) -> None:
    """Reconstruction runs without an intervening working() or lingering(), so the same PIDs stay released."""
    job = survived_run(root, monkeypatch)
    recovered_by_reboot(job)
    again = curation.Curation(Slots(lambda: 2), shared=lambda: DataRepo(root))
    sessions = again.maintenance.read()["sessions"]
    assert (again.maintenance.pending("curation"), len(sessions), sessions[0]["state"], again.left) == (
        False, 1, "recovered", {4242: 1.0},
    )  # fmt: skip


def test_repeated_rebuilds_while_the_survivor_is_held_add_no_duplicate_hold(root, monkeypatch) -> None:
    survived_run(root, monkeypatch)
    for _ in range(2):
        again = curation.Curation(Slots(lambda: 2), shared=lambda: DataRepo(root))
        assert (again.maintenance.pending("curation"), len(again.maintenance.read()["sessions"])) == (True, 1)


def test_pids_a_later_snapshot_records_are_held_and_never_borrow_the_recovered_run(root, monkeypatch) -> None:
    job = survived_run(root, monkeypatch)
    recovered_by_reboot(job)
    again = curation.Curation(Slots(lambda: 2), shared=lambda: DataRepo(root))
    again._pids({"event": "pids", "pids": {"5555": 2.0}})  # noqa: SLF001 - a process the earlier run never recorded
    later = curation.Curation(Slots(lambda: 2), shared=lambda: DataRepo(root))
    assert (later.maintenance.pending("curation"), len(later.maintenance.read()["sessions"])) == (True, 2)


def test_a_new_unknown_curation_run_is_not_imported_again_at_restart(root) -> None:
    def run(cfg) -> Run:
        return Run(cfg.session_id, ending="error", detail="runtime PID unknown",
                   termination=Termination(confirmed=False))  # fmt: skip

    job = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root), run=run)
    job.start("shop")
    drained(job)
    slots = Slots(lambda: 1, closed=True)
    restarted = curation.Curation(slots, shared=lambda: DataRepo(root))
    assert (slots.counts(curation.SLOT)[2], len(restarted.maintenance.read()["sessions"])) == (1, 1)


HELD = "0123456789abcdef"


def quiet(cfg) -> Run:
    return Run(cfg.session_id, ending="result", payload=MemoryCurationResult(summary="ok", entries=[]),
               termination=Termination(confirmed=True))  # fmt: skip


def recording(seen: list) -> callable:
    def run(cfg) -> Run:
        seen.append(cfg)
        return quiet(cfg)

    return run


def folder_run(job: curation.Curation, name: str) -> dict:
    return {f["folder"]: f for f in job.read()["folders"]}[name]


def configure_machine(**chosen) -> None:
    saved = registry.load()
    registry.configure(saved.settings.model_copy(update=chosen), registry.revision(saved.settings))


def curator(root: Path, **changes) -> None:
    """Change the curator role in Global, where a role's model, effort, minutes and subagents are set.

    Written by the same locked, atomic writer as production, so a reader never sees a half-written Global file.
    """
    shared = DataRepo(root)
    if not shared.global_path.exists():
        settings_carry.carry(shared)

    def change(glob: GlobalLayer) -> GlobalLayer:
        agent = glob.agents.get("curator", config.Agent()).model_copy(update=changes)
        return glob.model_copy(update={"agents": glob.agents | {"curator": agent}})

    update_layer(shared.global_path, GlobalLayer, change)


def test_the_curator_helper_writes_global_only_through_the_atomic_layer_writer(root, monkeypatch) -> None:
    settings_carry.carry(DataRepo(root))
    written = []
    real = store.atomic_write
    monkeypatch.setattr(store, "atomic_write", lambda path, text: (written.append(path), real(path, text)))
    curator(root, model="model-z")
    assert written == [DataRepo(root).global_path]


def test_a_queued_automatic_request_starts_only_if_its_trigger_still_allows_it_at_its_slot(root) -> None:
    slots, paused, ran = Slots(lambda: 1), [False], []
    assert slots.take(HELD, "a-change", 1, 1) == 1  # a project's step holds the only slot
    job = curation.Curation(slots, shared=lambda: DataRepo(root), run=recording(ran), paused=lambda: paused[0])
    pending(root / "shop" / "memory", "Lesson")
    assert job.nudge(None, "idle") == ["shop"]
    paused[0] = True  # the owner pauses while the request waits
    slots.give(HELD, "a-change")
    finished(job)
    assert (ran, folder_run(job, "shop")["state"], folder_run(job, "shop")["reason"]) == (
        [], "failed", curation.PAUSED
    )  # fmt: skip
    assert job.due("shop")  # still due: the next allowed trigger runs it


def test_curate_now_takes_over_a_waiting_automatic_request_and_runs_only_once(root) -> None:
    slots, paused, ran = Slots(lambda: 1), [False], []
    assert slots.take(HELD, "a-change", 1, 1) == 1
    job = curation.Curation(slots, shared=lambda: DataRepo(root), run=recording(ran), paused=lambda: paused[0])
    pending(root / "shop" / "memory", "Lesson")
    assert job.nudge(None, "idle") == ["shop"]
    paused[0] = True
    assert job.start("shop") == []  # the waiting request is coalesced: no second run is queued
    assert job.queue == ["shop"]
    slots.give(HELD, "a-change")
    finished(job)
    assert (len(ran), folder_run(job, "shop")["state"]) == (1, "done")


def test_curate_now_landing_after_an_automatic_refusal_but_before_the_worker_retires_it_still_runs(root) -> None:
    slots, paused, ran = Slots(lambda: 1), [False], []
    assert slots.take(HELD, "a-change", 1, 1) == 1
    job = curation.Curation(slots, shared=lambda: DataRepo(root), run=recording(ran), paused=lambda: paused[0])
    pending(root / "shop" / "memory", "Lesson")
    assert job.nudge(None, "idle") == ["shop"]
    paused[0] = True
    saved, raced = job._save, []  # noqa: SLF001 - the interleaving is gated on the refusal's own save

    def save_then_race(folder: str, run: curation.FolderRun) -> None:
        saved(folder, run)
        if run.state == "failed" and run.reason == curation.PAUSED and not raced:
            raced.append(job.start(folder))  # Curate now lands in the gap before the worker retires the folder

    job._save = save_then_race  # noqa: SLF001
    slots.give(HELD, "a-change")
    finished(job)
    assert (raced, len(ran), folder_run(job, "shop")["state"]) == ([[]], 1, "done")


def test_curate_now_bypasses_the_automatic_switch_and_pause_but_never_a_fence(root) -> None:
    configure_machine(curate_when_idle="off", curate_after_merge="off")
    ran = []
    job = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root), run=recording(ran),
                            paused=lambda: True)  # fmt: skip
    job.start("shop")
    finished(job)
    assert (len(ran), folder_run(job, "shop")["state"]) == (1, "done")

    fenced = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root), run=recording(ran),
                               fenced=lambda: "an update runs")  # fmt: skip
    fenced.start("owlbear")
    finished(fenced)
    assert (len(ran), folder_run(fenced, "owlbear")["reason"]) == (1, "an update runs")


@pytest.mark.parametrize(("setting", "may"), [(True, True), (False, False)])
def test_the_curator_session_starts_subagents_only_as_its_role_setting_allows(root, setting, may) -> None:
    curator(root, subagents=setting)
    seen = []
    job = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root), run=recording(seen))
    job.start("shop")
    finished(job)
    assert [cfg.subagents for cfg in seen] == [may]


def test_a_curator_whose_subagent_setting_is_unset_never_starts(root, monkeypatch) -> None:
    settings_carry.carry(DataRepo(root))
    monkeypatch.setattr(config, "BASE", None)  # no built-in value may fill the unset setting
    curator(root, subagents=None)
    job = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root),
                            run=lambda _cfg: pytest.fail("it ran"))  # fmt: skip
    job.start("shop")
    finished(job)
    shop = folder_run(job, "shop")
    assert (shop["state"], "agents.curator.subagents" in shop["reason"]) == ("failed", True)


def test_a_waiting_request_takes_the_role_settings_in_force_at_its_grant(root) -> None:
    slots, seen = Slots(lambda: 1), []
    curator(root, model="model-a", minutes=1)
    assert slots.take(HELD, "a-change", 1, 1) == 1
    job = curation.Curation(slots, shared=lambda: DataRepo(root), run=lambda cfg: _record(cfg, seen))
    job.start("shop")
    curator(root, model="model-b", minutes=5)  # changed while the request waits for its slot
    slots.give(HELD, "a-change")
    finished(job)
    assert [model for model, _limit in seen] == ["model-b"]


def _record(cfg, seen: list) -> Run:
    seen.append((cfg.model, cfg.limit))
    return quiet(cfg)
