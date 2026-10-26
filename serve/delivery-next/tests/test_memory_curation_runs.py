"""Item 5 slice 4: automatic memory curation runs one curator session per memory folder of the shared repository."""

import json
import threading
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from owlbear_memory import MemoryCategory, MemoryEngine

from owlbear_delivery_next.change_contracts import memory_curation_tools, tools
from owlbear_delivery_next.change_contracts.memory_curation_tools import Judged, MemoryCurationResult
from owlbear_delivery_next.local_system import local_home, maintenance, processes
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


def legacy_left_file(pids: dict[int, float | None], key: str = "") -> None:
    """An older host's ownership record: PIDs its run left, before any host has imported them."""
    path = local_home.root() / curation.STATE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(curation.Runs(left=pids, left_key=key).model_dump_json())


@pytest.mark.parametrize("lose_key", [False, True])
def test_a_legacy_pid_import_stays_bound_to_its_lease_across_a_restart_before_lingering(
    root, monkeypatch, lose_key
) -> None:
    """Review: an import's held lease is bound at import, so a restart before lingering() never holds the PIDs again."""
    monkeypatch.setattr(processes, "alive", lambda _pid, _created: False)
    legacy_left_file({4242: None})
    first = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root))  # imports the PIDs as a held lease
    if lose_key:  # the record lost its association: the import mark alone must still bind it
        path = local_home.root() / curation.STATE
        runs = curation.Runs.model_validate_json(path.read_text())
        runs.left_key = ""
        path.write_text(runs.model_dump_json())
    recovered_by_reboot(first)  # the owner rebooted
    slots = Slots(lambda: 1, closed=True)
    restarted = curation.Curation(slots, shared=lambda: DataRepo(root))  # before lingering() clears the snapshot
    sessions = restarted.maintenance.read()["sessions"]
    assert (restarted.maintenance.pending("curation"), len(sessions), sessions[0]["state"], restarted.left) == (
        False, 1, "recovered", {4242: None},
    )  # fmt: skip


def test_a_known_birth_after_a_recovered_legacy_import_is_held_and_its_start_runs_nothing(root, monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(processes, "alive", lambda _pid, _created: False)
    legacy_left_file({4242: None})
    recovered_by_reboot(curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root)))
    again = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root))
    again._pids({"event": "pids", "pids": {4242: time.time() + 3600}})  # noqa: SLF001 - born after the import ended

    def run(cfg) -> Run:
        calls.append(cfg.session_id)
        return Run(cfg.session_id, ending="result", payload=MemoryCurationResult(summary="ok", entries=[]))

    rebuilt = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root), run=run)
    assert (rebuilt.maintenance.pending("curation"), len(rebuilt.maintenance.read()["sessions"])) == (True, 2)
    rebuilt.start("shop")
    drained(rebuilt)
    assert calls == []


def test_a_newer_snapshot_binds_its_own_lease_after_a_failed_key_write(root, monkeypatch) -> None:
    """Review: a stale import mark never names another snapshot's lease; B's own durable lease is bound at restart."""
    monkeypatch.setattr(processes, "alive", lambda _pid, _created: False)
    legacy_left_file({4242: None})
    recovered_by_reboot(curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root)))  # A: 4242, recovered
    legacy_left_file({4343: None})  # a historical producer's newer snapshot, written without a key
    real_write = curation.Curation._write  # noqa: SLF001 - the runs record's own writer, wrapped to fail once
    failed: list[bool] = []

    def fail_once(self, runs) -> None:
        if not failed:
            failed.append(True)
            msg = "disk full"
            raise OSError(msg)  # B's lease is already durable; the runs record is not
        real_write(self, runs)

    monkeypatch.setattr(curation.Curation, "_write", fail_once)
    with pytest.raises(OSError, match="disk full"):
        curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root))
    monkeypatch.setattr(curation.Curation, "_write", real_write)
    restarted = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root))
    [held] = [s for s in json.loads(restarted.maintenance.path.read_text())["sessions"] if s["state"] == "held"]
    assert (restarted.left_key, restarted.maintenance.pending("curation")) == (held["slot"], True)
    booted = restarted.maintenance.boot
    restarted.maintenance.boot = lambda: booted() + 1  # the owner rebooted and recovers B
    restarted.maintenance.recover(held["id"], rebooted=True)
    slots = Slots(lambda: 1, closed=True)
    after = curation.Curation(slots, shared=lambda: DataRepo(root))  # before lingering() clears the unchanged snapshot
    assert (after.maintenance.pending("curation"), len(after.maintenance.read()["sessions"]), after.left_key) == (
        False, 2, held["slot"],
    )  # fmt: skip
    assert (slots.counts(curation.SLOT)[2], after.left) == (0, {4343: None})
    again = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root))
    again._pids({"event": "pids", "pids": {5555: 2.0}})  # noqa: SLF001 - a genuinely newer process
    calls: list[str] = []

    def run(cfg) -> Run:
        calls.append(cfg.session_id)
        return Run(cfg.session_id, ending="result", payload=MemoryCurationResult(summary="ok", entries=[]))

    later = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root), run=run)
    assert (later.maintenance.pending("curation"), len(later.maintenance.read()["sessions"])) == (True, 3)
    later.start("shop")
    drained(later)
    assert calls == []


def rebooted(job: curation.Curation) -> None:
    booted = job.maintenance.boot
    job.maintenance.boot = lambda: booted() + 1


def unmatched_snapshot_after_held_import(root, monkeypatch, pids: dict[int, float | None]) -> curation.Curation:
    """An unrecovered import A is held; a boot change, then a new snapshot B with no key the held lease records."""
    monkeypatch.setattr(processes, "alive", lambda _pid, _created: False)
    legacy_left_file({4242: None})
    first = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root))  # A held
    rebooted(first)
    runs = first.load()
    runs.left = pids
    first._write(runs)  # noqa: SLF001 - the historical producer writes the newer, unmatched snapshot B
    return curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root))  # the constructor holds B


def test_an_unmatched_snapshot_is_held_while_an_older_unrecovered_import_stays_held(root, monkeypatch) -> None:
    """Review: the older held lease never hides B; B keeps its own hold and key through restart and lingering."""
    restarted = unmatched_snapshot_after_held_import(root, monkeypatch, {4343: None})
    sessions = restarted.maintenance.read()["sessions"]
    assert (len(sessions), [s["state"] for s in sessions]) == (2, ["held", "held"])
    rebooted(restarted)
    restarted.maintenance.recover(sessions[0]["id"], rebooted=True)  # the owner recovers A only
    slots = Slots(lambda: 1, closed=True)
    last = curation.Curation(slots, shared=lambda: DataRepo(root))
    assert (last.working(), slots.counts(curation.SLOT)[2], last.left) == (
        [curation.LINGERING], 1, {4343: None},
    )  # fmt: skip


def test_an_unmatched_snapshot_is_released_only_by_its_own_recovery(root, monkeypatch) -> None:
    restarted = unmatched_snapshot_after_held_import(root, monkeypatch, {4343: None})
    sessions = restarted.maintenance.read()["sessions"]
    rebooted(restarted)
    restarted.maintenance.recover(sessions[1]["id"], rebooted=True)  # the owner recovers B
    slots = Slots(lambda: 1, closed=True)
    last = curation.Curation(slots, shared=lambda: DataRepo(root))
    assert (last.working(), slots.counts(curation.SLOT)[2]) == ([curation.LINGERING], 1)  # only A is still held


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
    first.maintenance.path.unlink(missing_ok=True)  # a pre-ledger installation
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
    first.maintenance.path.unlink(missing_ok=True)
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


def survived_run(root, monkeypatch, pid: int = 4242, birth: float | None = 1.0) -> curation.Curation:
    """A run whose process survives it: its PIDs are kept on the run's own lease and on the ledger's ``left``."""
    monkeypatch.setattr(processes, "alive", lambda _pid, _created: True)

    def run(cfg) -> Run:
        return Run(cfg.session_id, ending="result", payload=MemoryCurationResult(summary="ok", entries=[]),
                   runtime_pid=pid, pids={pid: birth},
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


def without_ended_at(job: curation.Curation) -> None:
    """Serialize the recovered ledger as it would be written without an end time, which the schema allows."""
    path = job.maintenance.path
    data = json.loads(path.read_text())
    for session in data["sessions"]:
        session.pop("ended_at", None)
    path.write_text(json.dumps(data))


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


def test_a_recovered_lease_without_an_end_time_is_not_covered_by_a_later_known_birth(root, monkeypatch) -> None:
    job = survived_run(root, monkeypatch, birth=None)
    recovered_by_reboot(job)
    without_ended_at(job)
    again = curation.Curation(Slots(lambda: 2), shared=lambda: DataRepo(root))
    again._pids({"event": "pids", "pids": {4242: time.time() + 3600}})  # noqa: SLF001 - no end bound to prove it
    rebuilt = curation.Curation(Slots(lambda: 2), shared=lambda: DataRepo(root))
    assert (rebuilt.maintenance.pending("curation"), len(rebuilt.maintenance.read()["sessions"])) == (True, 2)


def test_the_public_start_runs_nothing_for_a_recovered_lease_without_an_end_time(root, monkeypatch) -> None:
    calls: list[str] = []
    job = survived_run(root, monkeypatch, birth=None)
    recovered_by_reboot(job)
    without_ended_at(job)
    curation.Curation(Slots(lambda: 2), shared=lambda: DataRepo(root))._pids(  # noqa: SLF001
        {"event": "pids", "pids": {4242: time.time() + 3600}}
    )

    def run(cfg) -> Run:
        calls.append(cfg.session_id)
        return Run(cfg.session_id, ending="result", payload=MemoryCurationResult(summary="ok", entries=[]))

    rebuilt = curation.Curation(Slots(lambda: 2), shared=lambda: DataRepo(root), run=run)
    rebuilt.start("shop")
    drained(rebuilt)
    assert calls == []


def test_an_active_unknown_birth_still_covers_a_later_known_birth_without_a_second_hold(root, monkeypatch) -> None:
    survived_run(root, monkeypatch, birth=None)  # the run's lease stays active: its process survived
    again = curation.Curation(Slots(lambda: 2), shared=lambda: DataRepo(root))
    again._pids({"event": "pids", "pids": {4242: time.time() + 3600}})  # noqa: SLF001
    rebuilt = curation.Curation(Slots(lambda: 2), shared=lambda: DataRepo(root))
    assert (rebuilt.maintenance.pending("curation"), len(rebuilt.maintenance.read()["sessions"])) == (True, 1)


def test_a_known_birth_after_a_settled_runs_end_is_held_not_covered_by_its_unknown_birth(root, monkeypatch) -> None:
    """The settled run's PID had an unknown birth; a later known birth after it ended is another process."""
    job = survived_run(root, monkeypatch, birth=None)
    recovered_by_reboot(job)
    again = curation.Curation(Slots(lambda: 2), shared=lambda: DataRepo(root))
    again._pids({"event": "pids", "pids": {4242: time.time() + 3600}})  # noqa: SLF001 - born after the run ended
    rebuilt = curation.Curation(Slots(lambda: 2), shared=lambda: DataRepo(root))
    assert (rebuilt.maintenance.pending("curation"), len(rebuilt.maintenance.read()["sessions"])) == (True, 2)


def test_the_public_start_runs_nothing_while_that_contradiction_is_held(root, monkeypatch) -> None:
    calls: list[str] = []
    job = survived_run(root, monkeypatch, birth=None)
    recovered_by_reboot(job)
    curation.Curation(Slots(lambda: 2), shared=lambda: DataRepo(root))._pids(  # noqa: SLF001
        {"event": "pids", "pids": {4242: time.time() + 3600}}
    )

    def run(cfg) -> Run:
        calls.append(cfg.session_id)
        return Run(cfg.session_id, ending="result", payload=MemoryCurationResult(summary="ok", entries=[]))

    rebuilt = curation.Curation(Slots(lambda: 2), shared=lambda: DataRepo(root), run=run)
    rebuilt.start("shop")
    drained(rebuilt)
    assert calls == []


def test_a_known_birth_before_a_settled_runs_end_is_still_that_recovered_run(root, monkeypatch) -> None:
    job = survived_run(root, monkeypatch, birth=None)
    recovered_by_reboot(job)
    again = curation.Curation(Slots(lambda: 2), shared=lambda: DataRepo(root))
    again._pids({"event": "pids", "pids": {4242: time.time() - 3600}})  # noqa: SLF001 - born while the run ran
    rebuilt = curation.Curation(Slots(lambda: 2), shared=lambda: DataRepo(root))
    assert (rebuilt.maintenance.pending("curation"), len(rebuilt.maintenance.read()["sessions"])) == (False, 1)


def after_reboot(root, boot: float, run=None) -> curation.Curation:
    """A host started after the computer rebooted at *boot*: its ledger judges leases against that boot."""
    slots = Slots(lambda: 2)
    ownership = maintenance.Maintenance(slots, boot=lambda: boot)
    return curation.Curation(slots, shared=lambda: DataRepo(root), run=run, ownership=ownership)


def test_a_held_unknown_birth_keeps_its_hold_when_a_known_birth_after_a_reboot_is_written(root, monkeypatch) -> None:
    """A held lease A (PID 4242, unknown birth) predates a reboot; a later known birth is a new process, held as B."""
    job = survived_run(root, monkeypatch, birth=None)
    reboot = job.maintenance.boot() + 100
    job._pids({"event": "pids", "pids": {4242: reboot + 10}})  # noqa: SLF001 - the historical producer after the boot
    rebuilt = after_reboot(root, reboot)
    assert (rebuilt.maintenance.pending("curation"), [s["state"] for s in rebuilt.maintenance.read()["sessions"]]) == (
        True, ["held", "held"],
    )  # fmt: skip


def test_the_public_start_runs_nothing_while_a_reboot_contradiction_is_held(root, monkeypatch) -> None:
    calls: list[str] = []
    job = survived_run(root, monkeypatch, birth=None)
    reboot = job.maintenance.boot() + 100
    job._pids({"event": "pids", "pids": {4242: reboot + 10}})  # noqa: SLF001

    def run(cfg) -> Run:
        calls.append(cfg.session_id)
        return Run(cfg.session_id, ending="result", payload=MemoryCurationResult(summary="ok", entries=[]))

    rebuilt = after_reboot(root, reboot, run=run)
    rebuilt.start("shop")
    drained(rebuilt)
    assert calls == []


def test_a_known_birth_before_the_reboot_is_still_the_held_lease_unchanged(root, monkeypatch) -> None:
    """The unchanged pre-boot snapshot keeps covering its lease: nothing is held again."""
    job = survived_run(root, monkeypatch, birth=None)
    reboot = job.maintenance.boot() + 100
    job._pids({"event": "pids", "pids": {4242: job.maintenance.boot() + 1}})  # noqa: SLF001 - born before the reboot
    rebuilt = after_reboot(root, reboot)
    assert (rebuilt.maintenance.pending("curation"), len(rebuilt.maintenance.read()["sessions"])) == (True, 1)


def test_a_recovered_settled_lease_is_not_covered_by_a_known_birth_after_a_later_reboot(root, monkeypatch) -> None:
    """A recovered lease A with a known birth after the new boot is a new process, not A's own."""
    job = survived_run(root, monkeypatch, birth=None)
    recovered_by_reboot(job)
    reboot = job.maintenance.boot() + 100
    job._pids({"event": "pids", "pids": {4242: reboot + 10}})  # noqa: SLF001
    rebuilt = after_reboot(root, reboot)
    assert (rebuilt.maintenance.pending("curation"), len(rebuilt.maintenance.read()["sessions"])) == (True, 2)


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


def test_a_keyless_snapshot_reusing_a_recovered_runs_pid_and_unknown_birth_is_held_anew(root, monkeypatch) -> None:
    """A later legacy snapshot with no key is not the recovered run's process: it gets its own hold and no SDK."""
    job = survived_run(root, monkeypatch, birth=None)
    recovered_by_reboot(job)
    legacy_left_file({4242: None})
    calls: list[str] = []

    def run(cfg) -> Run:
        calls.append(cfg.session_id)
        return pytest.fail("ran")

    rebuilt = curation.Curation(Slots(lambda: 2), shared=lambda: DataRepo(root), run=run)
    assert (rebuilt.maintenance.pending("curation"), len(rebuilt.maintenance.read()["sessions"])) == (True, 2)
    rebuilt.start("shop")
    drained(rebuilt)
    assert calls == []


def test_a_keyless_snapshot_is_released_only_by_its_own_recovery_across_a_restart(root, monkeypatch) -> None:
    job = survived_run(root, monkeypatch, birth=None)
    recovered_by_reboot(job)
    legacy_left_file({4242: None})
    held = curation.Curation(Slots(lambda: 2), shared=lambda: DataRepo(root))
    [*_, newer] = held.maintenance.read()["sessions"]
    booted = held.maintenance.boot
    held.maintenance.boot = lambda: booted() + 1  # the computer rebooted since the keyless snapshot was held
    held.maintenance.recover(newer["id"], rebooted=True)
    for _ in range(2):
        again = curation.Curation(Slots(lambda: 2), shared=lambda: DataRepo(root))
        assert (again.maintenance.pending("curation"), len(again.maintenance.read()["sessions"])) == (False, 2)


def test_a_retry_after_a_failed_write_of_an_adopted_unknown_row_reuses_its_one_lease(root) -> None:
    """The lease is created after the row ended, so the retry must find it by the row's own mark, not its window."""
    first = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root))
    first.maintenance.path.unlink(missing_ok=True)
    older_unknown_run(first, datetime.now(UTC) - timedelta(minutes=5))

    def fail(*_args: object) -> None:
        msg = "synthetic write failure"
        raise OSError(msg)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(curation.Curation, "_write", fail)
        with pytest.raises(OSError, match="synthetic write failure"):
            curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root))
    retry = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root))
    [session] = retry.maintenance.read()["sessions"]
    assert session["state"] == "held"
    assert retry.maintenance.held(curation.SLOT, retry.load().folders["shop"].key) is True
    assert retry.maintenance.pending("curation") is True


def test_a_recovered_row_lease_is_not_duplicated_by_a_restart_and_a_new_row_holds_again(root) -> None:
    first = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root))
    first.maintenance.path.unlink(missing_ok=True)
    older_unknown_run(first, datetime.now(UTC) - timedelta(minutes=5))
    adopted = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root))
    [session] = adopted.maintenance.read()["sessions"]
    booted = adopted.maintenance.boot
    adopted.maintenance.boot = lambda: booted() + 1
    adopted.maintenance.recover(session["id"], rebooted=True)
    again = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root))
    assert (again.maintenance.pending("curation"), len(again.maintenance.read()["sessions"])) == (False, 1)
    older_unknown_run(again, datetime.now(UTC) - timedelta(minutes=1))
    newer = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root))
    assert (newer.maintenance.pending("curation"), len(newer.maintenance.read()["sessions"])) == (True, 2)


def main_session_row(started: datetime, pids: dict[int, float | None], *, running: bool = False) -> None:
    """What main's producer leaves after a session: it cannot read a keyed record, so it writes its own afresh.

    The row is the generic-exception failure ``_work`` writes, or the running row of a host stopped mid-run; ``left``
    holds the PIDs its journal kept, their births unknown. It knows no lease key.
    """
    row = {
        "state": "running" if running else "failed",
        "started_at": started.isoformat(),
        "ended_at": None if running else (started + timedelta(seconds=30)).isoformat(),
        "summary": "",
        "reason": "" if running else "RuntimeError: synthetic SDK failure",
        "entries": [],
        "skipped": {},
        "seen": {},
    }
    path = local_home.root() / curation.STATE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"folders": {"shop": row}, "left": {str(p): b for p, b in pids.items()}}))


def ledger_on_disk() -> dict:
    return json.loads((local_home.root() / maintenance.FILE).read_text())


def never_runs(calls: list[str]):
    def run(cfg) -> Run:
        calls.append(cfg.session_id)
        return pytest.fail("no SDK session starts")

    return run


def lost_write(*_args: object) -> None:
    msg = "synthetic runs write failure"
    raise OSError(msg)


@pytest.mark.parametrize("a_state", ["recovered", "held"])
def test_a_later_main_failure_row_reusing_an_imported_runs_pid_is_its_own_hold_and_starts_nothing(
    root, a_state
) -> None:
    """Review 4373338504: A's one-time import never names B, a later keyless row's snapshot of the same PID.

    B's row has its own times, so it is another producer observation: B is held under its own lease and key before
    lingering() could clear it, recovering A never releases it, and only B's own recovery does.
    """
    t0 = datetime.now(UTC) - timedelta(hours=2)
    main_session_row(t0, {4242: None})
    first = curation.Curation(Slots(lambda: 2), shared=lambda: DataRepo(root))  # imports A
    [a] = ledger_on_disk()["sessions"]
    if a_state == "recovered":
        recovered_by_reboot(first)
        assert (first.working(), first.load().left) == ([], {})  # A's snapshot is cleared as history
    main_session_row(t0 + timedelta(hours=1), {4242: None})  # B: main ran again; the PID is reused, birth unknown
    calls: list[str] = []
    rebuilt = curation.Curation(Slots(lambda: 2), shared=lambda: DataRepo(root), run=never_runs(calls))
    sessions = {s["slot"]: s for s in ledger_on_disk()["sessions"]}
    b = rebuilt.left_key
    assert (len(sessions), b != a["slot"], sessions[b]["state"], sessions[a["slot"]]["state"]) == (
        2, True, "held", a_state,
    )  # fmt: skip
    assert (rebuilt.load().left_key, rebuilt.left) == (b, {4242: None})
    if a_state == "held":
        rebooted(rebuilt)
        rebuilt.maintenance.recover(a["id"], rebooted=True)  # the owner recovers A only
    assert rebuilt.working() == [curation.LINGERING]
    rebuilt.start("shop")
    drained(rebuilt)
    assert (calls, rebuilt.load().folders["shop"].reason, rebuilt.load().left) == ([], curation.LEFT, {4242: None})
    restarted = curation.Curation(Slots(lambda: 2), shared=lambda: DataRepo(root), run=never_runs(calls))
    assert (len(ledger_on_disk()["sessions"]), restarted.left_key, restarted.maintenance.pending("curation")) == (
        2, b, True,
    )  # fmt: skip
    rebooted(restarted)
    restarted.maintenance.recover(sessions[b]["id"], rebooted=True)
    assert (restarted.working(), restarted.load().left, calls) == ([], {}, [])


def test_an_unchanged_main_snapshot_keeps_its_one_lease_across_a_lost_write_and_after_its_recovery(root) -> None:
    """Control: main's running row and PIDs, read again after a lost write or once recovered, are one generation."""
    t0 = datetime.now(UTC) - timedelta(hours=1)
    main_session_row(t0, {4242: None}, running=True)  # main stopped mid-run
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(curation.Curation, "_write", lost_write)
        with pytest.raises(OSError, match="synthetic runs write failure"):
            curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root))
    [lease] = ledger_on_disk()["sessions"]  # durable before the runs record could be written
    retry = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root))
    assert ([s["id"] for s in ledger_on_disk()["sessions"]], retry.left_key) == ([lease["id"]], lease["slot"])
    assert retry.load().folders["shop"].key == lease["slot"]  # the running row is that same generation
    recovered_by_reboot(retry)
    main_session_row(t0, {4242: None}, running=True)  # the identical observation, written again without our keys
    again = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root))
    assert (again.maintenance.pending("curation"), len(ledger_on_disk()["sessions"]), again.left_key) == (
        False, 1, lease["slot"],
    )  # fmt: skip
    assert (again.load().folders["shop"].key, again.working(), again.load().left) == (lease["slot"], [], {})


def test_an_adopted_unknown_row_keeps_its_one_lease_through_a_lost_key_write_its_recovery_and_a_restart(root) -> None:
    """Review 4373338555: the row's lease and its association are one save, so the lost key write is repaired.

    The lease begins after the row ended, so no window could find it again; a later row with its own start is held anew.
    """
    first = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root))
    first.maintenance.path.unlink(missing_ok=True)
    started = datetime.now(UTC) - timedelta(minutes=5)
    older_unknown_run(first, started)
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(curation.Curation, "_write", lost_write)
        with pytest.raises(OSError, match="synthetic runs write failure"):
            curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root))
    on_disk = ledger_on_disk()
    [b] = on_disk["sessions"]
    assert (b["state"], [m for m in on_disk["imported"] if m.endswith(f":slot:{b['slot']}")] != []) == ("held", True)
    assert first.load().folders["shop"].key == ""  # the key write was lost
    retry = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root))
    assert ([s["id"] for s in ledger_on_disk()["sessions"]], retry.load().folders["shop"].key) == ([b["id"]], b["slot"])
    rebooted(retry)
    retry.maintenance.recover(b["id"], rebooted=True)
    older_unknown_run(retry, started)  # the same row, its key lost again before any clearing
    again = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root))
    sessions = [s["id"] for s in ledger_on_disk()["sessions"]]
    assert (again.maintenance.pending("curation"), sessions) == (False, [b["id"]])
    assert again.load().folders["shop"].key == b["slot"]
    older_unknown_run(again, started + timedelta(minutes=2))  # a later unknown run
    calls: list[str] = []
    later = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root), run=never_runs(calls))
    assert (later.maintenance.pending("curation"), len(ledger_on_disk()["sessions"])) == (True, 2)
    later.start("shop")
    drained(later)
    assert calls == []
