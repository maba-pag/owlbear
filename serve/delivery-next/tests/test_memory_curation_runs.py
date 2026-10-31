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
from owlbear_delivery_next.machine_host import curation, curation_snapshots, curation_tree
from owlbear_delivery_next.runtimes.session_result import Run
from owlbear_delivery_next.settings import config
from owlbear_delivery_next.settings.config import GlobalLayer
from owlbear_delivery_next.state_store import layers, registry, settings_carry, spend_ledger
from owlbear_delivery_next.state_store.curation_runs import Runs
from owlbear_delivery_next.state_store.store import update_layer


def pending(folder: Path, title: str):
    return MemoryEngine(folder).save(
        title=title, content=f"{title}: what to know", categories=[MemoryCategory.PROCESS], confidence=0.8,
        source_agent="builder", scope_agents=[],
    )  # fmt: skip


def layout(data: Path) -> Path:
    for name in ("owlbear", "shop", "memory"):  # "memory" is Global: never a folder to curate
        (data / name / "memory").mkdir(parents=True) if name != "memory" else (data / name).mkdir()
    (data / "decisions").mkdir()  # a folder without memory
    return data


@pytest.fixture
def repo(shared_repo) -> Path:
    """The shared repository's clone, for a run that publishes what it curated."""
    return layout(shared_repo[0])


@pytest.fixture
def root(repo) -> Path:
    """The same shared clone: every run works on a worktree of it (#746), even one that never reaches a commit."""
    return repo


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


def test_a_run_curates_one_folder_as_the_curator_and_keeps_its_report_and_what_it_skipped(repo) -> None:
    left, done = pending(repo / "shop" / "memory", "Unsure lesson"), pending(repo / "shop" / "memory", "Clear one")
    seen, places = [], []

    def run(cfg) -> Run:
        seen.append(cfg)
        places.append(spend_ledger.where())
        report = MemoryCurationResult(summary="1 pruned, 1 skipped", entries=[
            Judged(entry_id=left.id, action="skipped", confidence=60, reason="only one project shows it"),
            Judged(entry_id=done.id, action="pruned", confidence=97),
        ])  # fmt: skip
        MemoryEngine(cfg.memory).delete(done.id, done.updated_at)  # in the run's own worktree (#746)
        return Run(cfg.session_id, ending="result", payload=report, termination=Termination(confirmed=True))

    job = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(repo), run=run)
    assert job.start("shop") == ["shop"]
    finished(job)

    (cfg,) = seen
    assert (cfg.role, cfg.memory.parts[-2:], cfg.submit) == (
        tools.CURATOR,
        ("shop", "memory"),
        memory_curation_tools.SUBMIT,
    )
    assert not cfg.memory.is_relative_to(repo)
    assert not (repo / "shop" / "memory" / f"{done.id}.md").exists()  # the accepted deletion reached the checkout
    assert "`shop`" in cfg.message
    assert cfg.policy.write is False
    shop = {f["folder"]: f for f in job.read()["folders"]}["shop"]
    assert (shop["state"], shop["summary"], [e["action"] for e in shop["entries"]]) == (
        "done", "1 pruned, 1 skipped", ["skipped", "pruned"]
    )  # fmt: skip
    assert shop["skipped"] == {left.id: left.revision}  # unchanged, an idle run passes it by
    assert places == [spend_ledger.Where(project="shop", name="shop")]  # its spend counts for the folder's project


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


def test_a_report_whose_model_is_unproven_fails_publishes_nothing_and_leaves_its_entries_due(root, monkeypatch):
    """#675, TD-94: a curation run whose usage does not prove its model is refused like any unproven step."""
    pending(root / "shop" / "memory", "Unsure lesson")
    published = []
    monkeypatch.setattr(DataRepo, "publish", lambda _self, *args, **_kw: published.append(args) or "")

    def run(cfg) -> Run:
        return Run(cfg.session_id, ending="result", payload=MemoryCurationResult(summary="ok", entries=[]),
                   termination=Termination(confirmed=True), usage_unread="no gpt-x tokens in the usage")  # fmt: skip

    job = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root), run=run)
    job.start("shop")
    finished(job)
    shop = job.load().folders["shop"]
    assert (shop.state, shop.reason, shop.summary, shop.seen, published) == (
        "failed",
        f"ended result: the model is unknown: no gpt-x tokens in the usage; {curation_tree.NO_EDITS}",
        "", {}, [],
    )  # fmt: skip
    assert (job.due("shop"), job.slots.counts(curation.SLOT)[2]) == (True, 0)


def test_without_a_shared_repository_nothing_is_curated() -> None:
    job = curation.Curation(Slots(lambda: 1), shared=lambda: None)
    assert job.read() == {"available": False, "reason": curation.NO_SHARED, "folders": []}
    with pytest.raises(ValueError, match="no shared repository"):
        job.start("all")


def test_a_trigger_starts_only_folders_with_pending_entries_no_run_saw_and_as_its_own_setting_says(repo) -> None:
    """The merge and idle triggers: a skipped entry starts no run until it changes; each trigger's machine setting
    is off, on (not while paused, the default) or on even while paused (the owner, 2026-10-23)."""
    from owlbear_delivery_next.state_store import registry  # noqa: PLC0415

    left = pending(repo / "shop" / "memory", "Unsure lesson")
    report = MemoryCurationResult(
        summary="1 skipped", entries=[Judged(entry_id=left.id, action="skipped", confidence=50)]
    )
    runs = []

    def run(cfg) -> Run:
        runs.append(cfg.memory.parent.name)
        return Run(cfg.session_id, ending="result", payload=report, termination=Termination(confirmed=True))

    paused = [True]
    job = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(repo), run=run, paused=lambda: paused[0])
    assert (job.due("shop"), job.due("owlbear")) == (True, False)
    assert job.nudge(None, "idle") == []  # paused: "on" holds it
    paused[0] = False
    assert job.nudge(None, "idle") == ["shop"]
    finished(job)
    assert (job.due("shop"), job.nudge(["shop"], "merge")) == (False, [])  # unchanged: no other run

    MemoryEngine(repo / "shop" / "memory").edit(
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


def test_an_entry_saved_during_a_run_stays_due_and_a_trigger_meanwhile_runs_the_folder_once_more(repo) -> None:
    """Sol: only what the curator could see is marked seen; a merge during its run is not lost."""
    pending(repo / "shop" / "memory", "First lesson")
    runs = []

    def run(cfg) -> Run:
        runs.append(cfg.session_id)
        if len(runs) == 1:  # an agent saves while the curator runs, and its Change merges
            pending(repo / "shop" / "memory", "Saved meanwhile")
            assert job.nudge(["shop"], "merge") == []
        report = MemoryCurationResult(summary="judged", entries=[])
        return Run(cfg.session_id, ending="result", payload=report, termination=Termination(confirmed=True))

    job = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(repo), run=run)
    job.start("shop")
    finished(job)
    assert (len(runs), job.due("shop")) == (2, False)  # the follow-up saw it


def test_one_folder_that_fails_never_strands_the_next_and_a_restart_ends_interrupted_runs(repo) -> None:
    def run(cfg) -> Run:
        if "owlbear" in cfg.session_id:
            broke = "the runtime broke"
            raise RuntimeError(broke)
        return Run(cfg.session_id, ending="result", payload=MemoryCurationResult(summary="ok", entries=[]),
                   termination=Termination(confirmed=True))  # fmt: skip

    job = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(repo), run=run)
    job.start("all")
    drained(job)
    states = {f["folder"]: (f["state"], f["reason"]) for f in job.read()["folders"]}
    assert states == {
        "owlbear": ("failed", "RuntimeError: the runtime broke"),
        "shop": ("failed", curation.LEFT),
    }
    assert job.slots.counts(curation.SLOT)[2] == 1

    job._save("shop", curation.FolderRun(state="running"))  # noqa: SLF001 - OwlBear stops while it runs
    again = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(repo))
    assert {f["folder"]: f["state"] for f in again.read()["folders"]}["shop"] == "failed"


def test_processes_that_may_still_run_keep_their_slot_and_the_machine_busy_until_they_are_gone(
    root, monkeypatch
) -> None:
    alive = [True]
    monkeypatch.setattr(processes, "alive", lambda _pid, _created: alive[0])
    published = []
    monkeypatch.setattr(DataRepo, "publish", lambda _self, *args, **_kw: published.append(args) or "")
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
    assert (job.load().folders["shop"].state, published) == ("failed", [])  # #675: a survivor's run is refused
    assert curation.Curation(Slots(lambda: 2), shared=lambda: DataRepo(root)).left == {4242: 1.0}
    alive[0] = False
    assert (job.working(), slots.counts(curation.SLOT)[2]) == ([], 0)


def _recorded(ran: list) -> object:
    def run(cfg) -> Run:
        ran.append(cfg.memory.parent.name)
        return Run(cfg.session_id, ending="result", payload=MemoryCurationResult(summary="ok", entries=[]),
                   termination=Termination(confirmed=True))  # fmt: skip

    return run


def test_a_curation_granted_its_slot_after_its_folder_moved_never_starts_on_the_old_name(root) -> None:
    """#678: a run queued before a rename and granted after it would curate a folder that is gone."""
    ran, slots = [], Slots(lambda: 1)
    assert slots.take(curation.SLOT, "another", 1, 1) == 1  # it waits for the only slot
    job = curation.Curation(slots, shared=lambda: DataRepo(root), run=_recorded(ran))
    with job.fence("shop") as busy:
        job.start("shop")
        (root / "shop").rename(root / "acme-shop")
    slots.give(curation.SLOT, "another")
    drained(job)
    shop = job.load().folders["shop"]
    assert (busy, ran, shop.state, shop.reason, slots.counts(curation.SLOT)[2]) == ("", [], "failed", curation.MOVED, 0)
    again = Slots(lambda: 1)
    restarted = curation.Curation(again, shared=lambda: DataRepo(root))  # a refusal, never an uncertain session
    assert (restarted.working(), again.counts(curation.SLOT)[2]) == ([], 0)


def test_a_curation_granted_its_slot_while_a_rename_holds_its_folder_never_starts(repo) -> None:
    ran = []
    job = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(repo), run=_recorded(ran))
    with job.fence("shop") as busy:
        job.start("shop")
        drained(job)
    held = job.load().folders["shop"]
    job.start("shop")
    drained(job)
    assert (busy, held.state, held.reason) == ("", "failed", curation.MOVED)
    assert (ran, job.load().folders["shop"].state) == (["shop"], "done")


def test_a_rename_waits_while_its_folders_curation_waits_or_any_runs_processes_may_still_run(repo, monkeypatch):
    """#678: a waiting run would start in the moved folder; a finished run's survivors name no folder."""
    alive = [True]
    monkeypatch.setattr(processes, "alive", lambda _pid, _created: alive[0])  # read as the ledger is made
    ran, slots = [], Slots(lambda: 1)
    assert slots.take(curation.SLOT, "another", 1, 1) == 1
    job = curation.Curation(slots, shared=lambda: DataRepo(repo), run=_recorded(ran))
    job.start("shop")
    with job.fence("shop") as waiting, job.fence("owlbear") as other:
        pass
    slots.give(curation.SLOT, "another")
    drained(job)
    assert (waiting, other, ran) == (curation.CURATING.format(folder="shop"), "", ["shop"])

    job.run = lambda cfg: Run(
        cfg.session_id, ending="result", payload=MemoryCurationResult(summary="ok", entries=[]), runtime_pid=4242,
        pids={4242: 1.0}, termination=Termination(confirmed=False, survivors=(4242,)),
    )  # fmt: skip
    job.start("shop")
    drained(job)
    with job.fence("shop") as own, job.fence("owlbear") as any_other:
        pass
    alive[0] = False
    with job.fence("shop") as gone:
        pass
    assert (own, any_other, gone) == (curation.LEFT_RENAME, curation.LEFT_RENAME, "")


def test_a_folder_that_cannot_be_listed_at_admission_gives_its_slot_back(root, monkeypatch) -> None:
    """Sol on #678: the admission check reads the disk after the grant; its failure never strands the slot."""
    ran, slots = [], Slots(lambda: 1)
    assert slots.take(curation.SLOT, "another", 1, 1) == 1
    job = curation.Curation(slots, shared=lambda: DataRepo(root), run=_recorded(ran))
    job.start("shop")

    def unreadable(_root):
        msg = "the shared repository is gone"
        raise OSError(msg)

    monkeypatch.setattr(curation, "folders", unreadable)
    slots.give(curation.SLOT, "another")
    drained(job)
    shop = job.load().folders["shop"]
    assert (ran, shop.state, shop.reason, slots.counts(curation.SLOT)[2]) == (
        [], "failed", "OSError: the shared repository is gone", 0
    )  # fmt: skip


def test_a_linked_memory_folder_is_never_curated(root) -> None:
    """Copilot on #587: a project folder whose memory links to Global or outside is not a folder to curate."""
    (root / "alias").mkdir()
    (root / "alias" / "memory").symlink_to(root / "memory")
    listed = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root)).read()["folders"]
    assert [f["folder"] for f in listed] == ["owlbear", "shop"]


def test_a_run_keeps_its_processes_on_file_while_it_runs_and_a_restart_holds_their_slot(repo, monkeypatch) -> None:
    """Copilot on #587: a host that stops mid-run leaves the session's processes known, their slot taken."""
    alive = [True]
    monkeypatch.setattr(processes, "alive", lambda _pid, _created: alive[0])
    on_file = []

    def run(cfg) -> Run:
        cfg.journal.event({"event": "pids", "pids": {"4242": None}})
        on_file.append(curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(repo)).load().left)
        return Run(cfg.session_id, ending="result", payload=MemoryCurationResult(summary="ok", entries=[]),
                   termination=Termination(confirmed=True))  # fmt: skip

    job = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(repo), run=run)
    job.start("shop")
    finished(job)
    assert (on_file, job.load().left) == ([{4242: None}], {})  # known while it ran, cleared once confirmed gone

    job._save("shop", curation.FolderRun(state="running"))  # noqa: SLF001 - the host stops mid-run
    runs = job.load()
    runs.left = {4242: None}
    job._write(runs)  # noqa: SLF001
    job.maintenance.path.unlink()  # synthetic pre-ledger installation, after every new-format lease ended
    slots = Slots(lambda: 1, closed=True)
    restarted = curation.Curation(slots, shared=lambda: DataRepo(repo))
    # the snapshot's PIDs and the running row each hold: nothing proves the PIDs are that row's session
    assert (slots.counts(curation.SLOT)[2], restarted.working()) == (2, [curation.LINGERING])
    alive[0] = False
    assert (restarted.working(), slots.counts(curation.SLOT)[2]) == ([curation.LINGERING], 2)


def test_an_unreadable_record_naming_left_processes_stops_the_restart_and_stays_as_it_was(root) -> None:
    """#674: only a missing record is empty; one that cannot be read keeps its evidence and the host does not start.

    #801: the refusal names the file, the parser's whole text and the way out.
    """
    path = local_home.root() / curation.STATE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{"folders": {}, "left": {"4242": "not a birth time"}}\n')  # e.g. an older or newer format
    before, slots = path.read_bytes(), Slots(lambda: 1)
    with pytest.raises(ValueError, match="validation error") as parsed:
        Runs.model_validate_json(before)
    with pytest.raises(maintenance.MaintenanceError, match="ownership record") as refused:
        curation.Curation(slots, shared=lambda: DataRepo(root))
    assert (path.read_bytes(), slots.counts(curation.SLOT)[2]) == (before, 0)
    said = str(refused.value)
    assert str(path) in said
    assert str(parsed.value) in said  # whole and contiguous, pydantic's "For further information" tail included
    assert "aside" in said


def test_a_record_that_cannot_be_opened_stops_the_restart_naming_it_and_the_way_out(root) -> None:
    """#801: an OSError names the file, the system's whole text and the way out; what stands in its place stays."""
    path = local_home.root() / curation.STATE
    path.mkdir(parents=True)  # a folder where the file belongs: reading it is an OSError
    slots = Slots(lambda: 1)
    with pytest.raises(OSError, match="directory") as opened:
        path.read_text()
    with pytest.raises(maintenance.MaintenanceError, match="ownership record") as refused:
        curation.Curation(slots, shared=lambda: DataRepo(root))
    assert (list(path.iterdir()), slots.counts(curation.SLOT)[2]) == ([], 0)
    said = str(refused.value)
    assert str(path) in said
    assert str(opened.value) in said
    assert "aside" in said


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


def test_a_sweep_paused_before_it_gives_a_slot_back_never_costs_a_successor_its_reservation(repo, monkeypatch) -> None:
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

    job = curation.Curation(slots, shared=lambda: DataRepo(repo), run=run)
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


def test_an_explicit_reboot_recovery_is_the_gate_and_reused_pids_never_block_a_new_admission(repo, monkeypatch) -> None:
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

    job = curation.Curation(slots, shared=lambda: DataRepo(repo), run=run, ownership=ledger)
    job.start("shop")
    drained(job)
    assert job.working() == [curation.LINGERING]
    (session,) = ledger.read()["sessions"]

    boot[0] = 2.0  # the owner confirmed a reboot since the failed session
    ledger.recover(session["id"], rebooted=True)
    assert job.working() == []
    restarted = curation.Curation(slots, shared=lambda: DataRepo(repo), run=run, ownership=ledger)
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


def test_an_unkeyed_unknown_row_is_never_taken_for_a_lease_merely_because_it_began_within_its_times(root) -> None:
    """Review on 4e95: a time window is no identity. An unkeyed unknown row, even one an earlier build of this host
    wrote while its own lease began inside it, is held under its own lease once, and its start runs nothing."""
    first = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root))
    t0 = datetime(2026, 10, 25, 0, 0, 10, tzinfo=UTC)
    unkeyed_2bf_row(first, t0)
    lease = first.maintenance.begin(
        curation.SLOT, "curate:shop:2bf0000000000000", "curation", "", now=t0 + timedelta(seconds=1)
    )
    first.maintenance.failed(lease, RuntimeError("synthetic unconfirmed runtime"))
    for _ in range(2):
        restarted = curation.Curation(
            Slots(lambda: 1, closed=True), shared=lambda: DataRepo(root), run=lambda _cfg: pytest.fail("it ran")
        )
        sessions = restarted.maintenance.read()["sessions"]
        own = restarted.load().folders["shop"].key
        assert ([s["state"] for s in sessions], own != "curate:shop:2bf0000000000000") == (["held", "held"], True)
    restarted.start("shop")
    drained(restarted)
    assert restarted.load().folders["shop"].reason == curation.LEFT


def test_an_unkeyed_unknown_row_is_held_anew_once_after_the_lease_within_its_times_was_recovered(root) -> None:
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
        assert ([s["state"] for s in sessions], again.maintenance.pending("curation")) == (["recovered", "held"], True)


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
    """The owner reboots and recovers every session still held; with one held, that one."""
    booted = job.maintenance.boot
    job.maintenance.boot = lambda: booted() + 1  # the computer rebooted since the run was left
    for session in job.maintenance.read()["sessions"]:
        if session["state"] == "held":
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
    calls: list[str] = []
    job = survived_run(root, monkeypatch, birth=None)
    recovered_by_reboot(job)
    without_ended_at(job)
    again = curation.Curation(Slots(lambda: 2), shared=lambda: DataRepo(root))
    again._pids({"event": "pids", "pids": {4242: time.time() + 3600}})  # noqa: SLF001 - no end bound to prove it
    rebuilt = curation.Curation(Slots(lambda: 2), shared=lambda: DataRepo(root), run=never_runs(calls))
    assert (rebuilt.maintenance.pending("curation"), len(rebuilt.maintenance.read()["sessions"])) == (True, 2)
    rebuilt.start("shop")
    drained(rebuilt)
    assert calls == []  # the public start runs nothing for it


def test_an_active_unknown_birth_still_covers_a_later_known_birth_without_a_second_hold(root, monkeypatch) -> None:
    survived_run(root, monkeypatch, birth=None)  # the run's lease stays active: its process survived
    again = curation.Curation(Slots(lambda: 2), shared=lambda: DataRepo(root))
    again._pids({"event": "pids", "pids": {4242: time.time() + 3600}})  # noqa: SLF001
    rebuilt = curation.Curation(Slots(lambda: 2), shared=lambda: DataRepo(root))
    assert (rebuilt.maintenance.pending("curation"), len(rebuilt.maintenance.read()["sessions"])) == (True, 1)


def test_a_known_birth_after_a_settled_runs_end_is_held_not_covered_by_its_unknown_birth(root, monkeypatch) -> None:
    """The settled run's PID had an unknown birth; a later known birth after it ended is another process."""
    calls: list[str] = []
    job = survived_run(root, monkeypatch, birth=None)
    recovered_by_reboot(job)
    again = curation.Curation(Slots(lambda: 2), shared=lambda: DataRepo(root))
    again._pids({"event": "pids", "pids": {4242: time.time() + 3600}})  # noqa: SLF001 - born after the run ended
    rebuilt = curation.Curation(Slots(lambda: 2), shared=lambda: DataRepo(root), run=never_runs(calls))
    assert (rebuilt.maintenance.pending("curation"), len(rebuilt.maintenance.read()["sessions"])) == (True, 2)
    rebuilt.start("shop")
    drained(rebuilt)
    assert calls == []  # the public start runs nothing while that contradiction is held


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
    calls: list[str] = []
    rebuilt = after_reboot(root, reboot, run=never_runs(calls))
    assert (rebuilt.maintenance.pending("curation"), [s["state"] for s in rebuilt.maintenance.read()["sessions"]]) == (
        True, ["held", "held"],
    )  # fmt: skip
    rebuilt.start("shop")
    drained(rebuilt)
    assert calls == []  # the public start runs nothing while a reboot contradiction is held


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


def test_the_curator_helper_writes_global_only_through_the_atomic_layer_writer(repo, monkeypatch) -> None:
    settings_carry.carry(DataRepo(repo))
    written = []
    real = layers.atomic_write
    monkeypatch.setattr(layers, "atomic_write", lambda path, text: (written.append(path), real(path, text)))
    curator(repo, model="model-z")
    assert written == [DataRepo(repo).global_path]


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


def test_curate_now_takes_over_a_waiting_automatic_request_and_runs_only_once(repo) -> None:
    slots, paused, ran = Slots(lambda: 1), [False], []
    assert slots.take(HELD, "a-change", 1, 1) == 1
    job = curation.Curation(slots, shared=lambda: DataRepo(repo), run=recording(ran), paused=lambda: paused[0])
    pending(repo / "shop" / "memory", "Lesson")
    assert job.nudge(None, "idle") == ["shop"]
    paused[0] = True
    assert job.start("shop") == []  # the waiting request is coalesced: no second run is queued
    assert job.queue == ["shop"]
    slots.give(HELD, "a-change")
    finished(job)
    assert (len(ran), folder_run(job, "shop")["state"]) == (1, "done")


def test_curate_now_landing_after_an_automatic_refusal_but_before_the_worker_retires_it_still_runs(repo) -> None:
    slots, paused, ran = Slots(lambda: 1), [False], []
    assert slots.take(HELD, "a-change", 1, 1) == 1
    job = curation.Curation(slots, shared=lambda: DataRepo(repo), run=recording(ran), paused=lambda: paused[0])
    pending(repo / "shop" / "memory", "Lesson")
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


def test_curate_now_bypasses_the_automatic_switch_and_pause_but_never_a_fence(repo) -> None:
    configure_machine(curate_when_idle="off", curate_after_merge="off")
    ran = []
    job = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(repo), run=recording(ran),
                            paused=lambda: True)  # fmt: skip
    job.start("shop")
    finished(job)
    assert (len(ran), folder_run(job, "shop")["state"]) == (1, "done")

    fenced = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(repo), run=recording(ran),
                               fenced=lambda: "an update runs")  # fmt: skip
    fenced.start("owlbear")
    finished(fenced)
    assert (len(ran), folder_run(fenced, "owlbear")["reason"]) == (1, "an update runs")


@pytest.mark.parametrize(("setting", "may"), [(True, True), (False, False)])
def test_the_curator_session_starts_subagents_only_as_its_role_setting_allows(repo, setting, may, user_on) -> None:
    curator(repo, subagents=setting)
    seen = []
    job = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(repo), run=recording(seen))
    job.start("shop")
    finished(job)
    assert [(cfg.subagents, cfg.user) for cfg in seen] == [(may, user_on)]


def test_a_curator_whose_subagent_setting_is_unset_never_starts(repo, monkeypatch) -> None:
    settings_carry.carry(DataRepo(repo))
    monkeypatch.setattr(config, "BASE", None)  # no built-in value may fill the unset setting
    curator(repo, subagents=None)
    job = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(repo),
                            run=lambda _cfg: pytest.fail("it ran"))  # fmt: skip
    job.start("shop")
    finished(job)
    shop = folder_run(job, "shop")
    assert (shop["state"], "agents.curator.subagents" in shop["reason"]) == ("failed", True)


def test_a_waiting_request_takes_the_role_settings_in_force_at_its_grant(repo) -> None:
    slots, seen = Slots(lambda: 1), []
    curator(repo, model="model-a", minutes=1)
    assert slots.take(HELD, "a-change", 1, 1) == 1
    job = curation.Curation(slots, shared=lambda: DataRepo(repo), run=lambda cfg: _record(cfg, seen))
    job.start("shop")
    curator(repo, model="model-b", minutes=5)  # changed while the request waits for its slot
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


def main_refusal(at: datetime, pids: dict[int, float | None], reason: str = curation.LEFT) -> None:
    """What main's ``_one`` leaves when it refuses before any session, as while its PIDs may run: the folder's row
    failed with its reason, ending as it starts; ``left`` kept as it was. It cannot read a keyed record, so the file is
    written afresh. With another *reason*, the same shape is any other row main writes ending as it starts."""
    row = {"state": "failed", "started_at": at.isoformat(), "ended_at": at.isoformat(), "summary": "",
           "reason": reason, "entries": [], "skipped": {}, "seen": {}}  # fmt: skip
    path = local_home.root() / curation.STATE
    path.write_text(json.dumps({"folders": {"shop": row}, "left": {str(p): b for p, b in pids.items()}}))


def test_main_refusals_after_its_session_keep_its_one_hold_and_only_a_later_session_is_held_anew(root) -> None:
    """Review turn 26: a refusal before any session is no new session, so repeated ones never grow the holds.

    After the owner's recovery the same refusals resurrect nothing; a later generic failure with the same PID and an
    unknown birth has its own window, so it is held anew.
    """
    calls: list[str] = []
    t0 = datetime.now(UTC) - timedelta(hours=3)
    main_session_row(t0, {4242: None})
    first = curation.Curation(Slots(lambda: 2), shared=lambda: DataRepo(root), run=never_runs(calls))
    a, r = ledger_on_disk()["sessions"]  # the snapshot's PIDs and the failure's row, each its own hold
    assert (bool(a["generation"]), r["generation"]) == (True, "")
    for n in range(1, 4):
        main_refusal(t0 + timedelta(minutes=n), {4242: None})
        again = curation.Curation(Slots(lambda: 2), shared=lambda: DataRepo(root), run=never_runs(calls))
        assert ([s["id"] for s in ledger_on_disk()["sessions"]], again.left_key, again.left) == (
            [a["id"], r["id"]], a["slot"], {4242: None},
        )  # fmt: skip
        assert again.working() == [curation.LINGERING]
    recovered_by_reboot(first)
    for n in range(4, 6):
        main_refusal(t0 + timedelta(minutes=n), {4242: None})
        after = curation.Curation(Slots(lambda: 2), shared=lambda: DataRepo(root), run=never_runs(calls))
        assert (after.maintenance.pending("curation"), [s["state"] for s in ledger_on_disk()["sessions"]]) == (
            False, ["recovered", "recovered"],
        )  # fmt: skip
    main_session_row(t0 + timedelta(hours=1), {4242: None})  # main's later session failed: same PID, birth unknown
    later = curation.Curation(Slots(lambda: 2), shared=lambda: DataRepo(root), run=never_runs(calls))
    assert ([s["state"] for s in ledger_on_disk()["sessions"]], later.left_key not in {a["slot"], r["slot"]}) == (
        ["recovered", "recovered", "held", "held"], True,
    )  # fmt: skip
    main_refusal(t0 + timedelta(hours=2), {4242: None})  # its own refusals keep those holds as they are
    curation.Curation(Slots(lambda: 2), shared=lambda: DataRepo(root), run=never_runs(calls))
    assert ([s["state"] for s in ledger_on_disk()["sessions"]], calls) == (
        ["recovered", "recovered", "held", "held"], [],
    )  # fmt: skip


@pytest.mark.parametrize(
    "reason",
    ["RuntimeError: synthetic SDK failure", "an update to v9 is being installed"],
    ids=["generic-failure-same-clock", "unrecognised-refusal"],
)
def test_a_row_ending_as_it_starts_without_a_known_refusal_reason_is_held_anew(root, reason) -> None:
    """Review turn 27: equal times prove no refusal. main's generic failure, when the clock gave its session's start
    and end one value, or a refusal text not known for certain, is session evidence: B is held under its own key, its
    PIDs kept, and a new start runs nothing."""
    t0 = datetime.now(UTC) - timedelta(hours=2)
    main_session_row(t0, {4242: None})
    first = curation.Curation(Slots(lambda: 2), shared=lambda: DataRepo(root))  # imports A: its PIDs and its row
    a, _row = ledger_on_disk()["sessions"]
    recovered_by_reboot(first)
    assert first.working() == []
    main_refusal(t0 + timedelta(hours=1), {4242: None}, reason)  # main's later row: same PID, birth unknown
    calls: list[str] = []
    rebuilt = curation.Curation(Slots(lambda: 2), shared=lambda: DataRepo(root), run=never_runs(calls))
    assert ([s["state"] for s in ledger_on_disk()["sessions"]], rebuilt.left_key != a["slot"], rebuilt.left) == (
        ["recovered", "recovered", "held", "held"], True, {4242: None},
    )  # fmt: skip
    assert rebuilt.load().left_key == rebuilt.left_key
    rebuilt.start("shop")
    drained(rebuilt)
    assert (calls, rebuilt.load().folders["shop"].reason) == ([], curation.LEFT)


def test_a_row_in_a_state_no_producer_writes_is_never_taken_for_a_known_snapshot(root) -> None:
    """Fail closed: a dated row in an unknown state is evidence, so it is held anew rather than read as a refusal."""
    t0 = datetime.now(UTC) - timedelta(hours=1)
    main_session_row(t0, {4242: None})
    curation.Curation(Slots(lambda: 2), shared=lambda: DataRepo(root))
    path = local_home.root() / curation.STATE
    at = (t0 + timedelta(minutes=1)).isoformat()
    row = {"state": "paused", "started_at": at, "ended_at": at, "summary": "", "reason": "", "entries": [],
           "skipped": {}, "seen": {}}  # fmt: skip
    path.write_text(json.dumps({"folders": {"shop": row}, "left": {"4242": None}}))
    curation.Curation(Slots(lambda: 2), shared=lambda: DataRepo(root))
    assert [s["state"] for s in ledger_on_disk()["sessions"]] == ["held", "held", "held", "held"]


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
    first = curation.Curation(Slots(lambda: 2), shared=lambda: DataRepo(root))  # imports A: its PIDs and its row
    a, r = ledger_on_disk()["sessions"]
    if a_state == "recovered":
        recovered_by_reboot(first)
        assert (first.working(), first.load().left) == ([], {})  # A's snapshot is cleared as history
    main_session_row(t0 + timedelta(hours=1), {4242: None})  # B: main ran again; the PID is reused, birth unknown
    calls: list[str] = []
    rebuilt = curation.Curation(Slots(lambda: 2), shared=lambda: DataRepo(root), run=never_runs(calls))
    sessions = {s["slot"]: s for s in ledger_on_disk()["sessions"]}
    b = rebuilt.left_key
    assert (len(sessions), b not in {a["slot"], r["slot"]}, sessions[b]["state"], sessions[a["slot"]]["state"]) == (
        4, True, "held", a_state,
    )  # fmt: skip
    assert (rebuilt.load().left_key, rebuilt.left) == (b, {4242: None})
    if a_state == "held":
        rebooted(rebuilt)
        for own in (a, r):  # the owner recovers A only: its PIDs and its row
            rebuilt.maintenance.recover(own["id"], rebooted=True)
    assert rebuilt.working() == [curation.LINGERING]
    rebuilt.start("shop")
    drained(rebuilt)
    assert (calls, rebuilt.load().folders["shop"].reason, rebuilt.load().left) == ([], curation.LEFT, {4242: None})
    restarted = curation.Curation(Slots(lambda: 2), shared=lambda: DataRepo(root), run=never_runs(calls))
    assert (len(ledger_on_disk()["sessions"]), restarted.left_key, restarted.maintenance.pending("curation")) == (
        4, b, True,
    )  # fmt: skip
    recovered_by_reboot(restarted)  # B's own: its PIDs and its row
    assert (restarted.working(), restarted.load().left, calls) == ([], {}, [])


def test_an_unchanged_main_snapshot_keeps_its_leases_across_a_lost_write_and_after_its_recovery(root) -> None:
    """Control: main's running row and PIDs, read again after a lost write or once recovered, keep their own leases.

    Nothing proves the PIDs are the running row's session, so each holds; the same observation never adds a third.
    """
    t0 = datetime.now(UTC) - timedelta(hours=1)
    main_session_row(t0, {4242: None}, running=True)  # main stopped mid-run
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(curation.Curation, "_write", lost_write)
        with pytest.raises(OSError, match="synthetic runs write failure"):
            curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root))
    snapshot, row = ledger_on_disk()["sessions"]  # both durable before the runs record could be written
    ids = [snapshot["id"], row["id"]]
    retry = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root))
    assert ([s["id"] for s in ledger_on_disk()["sessions"]], retry.left_key) == (ids, snapshot["slot"])
    assert retry.load().folders["shop"].key == row["slot"]  # the running row is its own lease again
    recovered_by_reboot(retry)
    main_session_row(t0, {4242: None}, running=True)  # the identical observation, written again without our keys
    again = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root))
    assert (again.maintenance.pending("curation"), [s["id"] for s in ledger_on_disk()["sessions"]]) == (False, ids)
    assert (again.left_key, again.load().folders["shop"].key) == (snapshot["slot"], row["slot"])
    assert (again.working(), again.load().left) == ([], {})


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


def main_row(reason: str, started: datetime, ended: datetime | None, state: str = "failed", summary: str = "") -> None:
    """One row main's producer left with no PIDs on file, written afresh as it cannot read a keyed record."""
    row = {"state": state, "started_at": started.isoformat(), "ended_at": ended.isoformat() if ended else None,
           "summary": summary, "reason": reason, "entries": [], "skipped": {}, "seen": {}}  # fmt: skip
    path = local_home.root() / curation.STATE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"folders": {"shop": row}, "left": {}}))


def ledger_sessions() -> list[dict]:
    path = local_home.root() / maintenance.FILE
    return json.loads(path.read_text())["sessions"] if path.exists() else []


def test_main_generic_failure_before_its_first_pid_is_held_by_its_row_through_a_lost_key_write_and_recovery(
    root,
) -> None:
    """Review 4373677385: main entered the SDK, which raised before any PID was recorded; nothing proves it ended.

    The row's lease and its association are one save, so a lost key write is repaired; after the owner's recovery the
    same row resurrects nothing, and a genuinely new row without PIDs is held again.
    """
    t0 = datetime.now(UTC) - timedelta(hours=2)
    main_session_row(t0, {})  # main's ``_work`` row: RuntimeError, dated, no key, no PIDs
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(curation.Curation, "_write", lost_write)
        with pytest.raises(OSError, match="synthetic runs write failure"):
            curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root))
    [b] = ledger_sessions()
    calls: list[str] = []
    retry = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root), run=never_runs(calls))
    assert ([s["id"] for s in ledger_sessions()], b["state"], retry.load().folders["shop"].key) == (
        [b["id"]], "held", b["slot"],
    )  # fmt: skip
    assert (retry.working(), retry.left) == ([curation.LINGERING], {})
    retry.start("shop")
    drained(retry)
    assert (calls, retry.load().folders["shop"].reason) == ([], curation.LEFT)
    rebooted(retry)
    retry.maintenance.recover(b["id"], rebooted=True)
    main_session_row(t0, {})  # the same row, its key lost again
    again = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root), run=never_runs(calls))
    assert (again.maintenance.pending("curation"), [s["id"] for s in ledger_sessions()]) == (False, [b["id"]])
    assert again.load().folders["shop"].key == b["slot"]
    main_session_row(t0 + timedelta(hours=1), {})  # main's later session failed the same way
    later = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root), run=never_runs(calls))
    assert ([s["state"] for s in ledger_sessions()], later.working(), calls) == (
        ["recovered", "held"], [curation.LINGERING], [],
    )  # fmt: skip


UNSET_MODEL = "settings unset: agents.curator.model; fill them in on the Settings page"


@pytest.mark.parametrize(
    ("reason", "after", "state"),
    [
        (curation.LEFT, 0, "failed"),  # each fixed refusal is one of curation_snapshots.REFUSALS
        (curation.NO_SHARED, 0, "failed"),  # REFUSALS copies its text: a reworded constant must break this
        ("stopping", 0, "waiting"),
        (UNSET_MODEL, 0, "failed"),
        (UNSET_MODEL, 2, "failed"),  # found again by the session's own check, before the SDK
        ("agents.curator.subagents is unset", 0, "failed"),
    ],
)
def test_a_known_refusal_main_writes_before_any_session_holds_nothing(root, reason, after, state) -> None:
    t0 = datetime.now(UTC) - timedelta(hours=1)
    main_row(reason, t0, t0 + timedelta(seconds=after), state)
    job = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root))
    assert (ledger_sessions(), job.working(), job.maintenance.pending("curation")) == ([], [], False)


@pytest.mark.parametrize(
    ("reason", "start", "end", "state"),
    [
        ("RuntimeError: synthetic SDK failure", 0, 0, "failed"),  # one clock value for its start and end
        ("RuntimeError: synthetic SDK failure", 3600, 3630, "failed"),  # dated in the future
        (curation.INTERRUPTED, 0, None, "failed"),  # a running row a restart ended
        (curation.INTERRUPTED, 0, 30, "failed"),  # a waiting copy a restart ended: its end proves nothing
        ("RuntimeError: synthetic SDK failure", 0, 30, "waiting"),  # main's queued copy of a generic failure
        (UNSET_MODEL, 10, 0, "failed"),  # ends before it starts: no shape main writes
        (curation.LEFT, 0, 5, "failed"),  # a fixed refusal that took time: no shape main writes
        ("", 0, 30, "failed"),  # no reason is no refusal
        ("", 0, 0, "paused"),
    ],
)
def test_a_dated_failure_no_known_shape_explains_is_held_fail_closed(root, reason, start, end, state) -> None:
    t0 = datetime.now(UTC) - timedelta(minutes=30)
    main_row(reason, t0 + timedelta(seconds=start), None if end is None else t0 + timedelta(seconds=end), state)
    calls: list[str] = []
    job = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root), run=never_runs(calls))
    assert ([s["state"] for s in ledger_sessions()], job.working()) == (["held"], [curation.LINGERING])
    job.start("shop")
    drained(job)
    assert calls == []


@pytest.mark.parametrize("copy", ["waiting", "interrupted"])
def test_a_queued_copy_of_mains_failure_before_its_first_pid_keeps_one_hold_through_restarts_and_recovery(
    root, copy
) -> None:
    """Review on b4: main's ``start`` copies the failed row as waiting, and main's restart then ends it interrupted.

    Both still show the generic failure's session times, and the waiting one its reason; neither end proves the
    session ended. It is held once, through a lost key write and further restarts, starts nothing, and after the
    owner's recovery the same copy resurrects nothing.
    """
    t0 = datetime.now(UTC) - timedelta(hours=2)
    reason = "RuntimeError: synthetic SDK failure" if copy == "waiting" else curation.INTERRUPTED
    main_row(reason, t0, t0 + timedelta(seconds=30), "waiting" if copy == "waiting" else "failed")
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(curation.Curation, "_write", lost_write)
        with pytest.raises(OSError, match="synthetic runs write failure"):
            curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root))
    [b] = ledger_sessions()
    calls: list[str] = []
    for _ in range(2):
        again = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root), run=never_runs(calls))
        assert ([s["id"] for s in ledger_sessions()], again.load().folders["shop"].key) == ([b["id"]], b["slot"])
    assert again.load().folders["shop"].reason == curation.INTERRUPTED
    again.start("shop")
    drained(again)
    assert (calls, again.load().folders["shop"].reason) == ([], curation.LEFT)
    rebooted(again)
    again.maintenance.recover(b["id"], rebooted=True)
    main_row(reason, t0, t0 + timedelta(seconds=30), "waiting" if copy == "waiting" else "failed")  # key lost again
    after = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root), run=never_runs(calls))
    assert ([s["state"] for s in ledger_sessions()], after.working(), calls) == (["recovered"], [], [])


@pytest.mark.parametrize(
    ("reason", "state", "summary", "dated"),
    [
        ("", "waiting", "", False),  # queued, never started
        (curation.LEFT, "waiting", "", True),  # a copy of a known refusal
        ("ended error: no report was submitted", "waiting", "", True),  # a copy of a judged SDK return
        ("", "waiting", "2 promoted", True),  # a copy of a finished run's report
        (curation.INTERRUPTED, "failed", "2 promoted", True),  # its copy after main's restart
    ],
)
def test_a_queued_copy_that_still_proves_no_unproven_session_holds_nothing_across_restarts(
    root, reason, state, summary, dated
) -> None:
    t0 = datetime.now(UTC) - timedelta(hours=1)
    main_row(reason, t0, t0 if reason == curation.LEFT else t0 + timedelta(seconds=30), state, summary)
    if not dated:
        path = local_home.root() / curation.STATE
        runs = json.loads(path.read_text())
        runs["folders"]["shop"] |= {"started_at": None, "ended_at": None}
        path.write_text(json.dumps(runs))
    for _ in range(3):  # this host's own rewrite of the copy is judged again at each restart
        job = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root))
        assert (ledger_sessions(), job.working(), job.load().folders["shop"].state) == ([], [], "failed")


def snapshot_receipt_from_8ad(*, recovered: bool) -> maintenance.Lease:
    """What 8ad's constructor left for main's generic failure with PIDs: a snapshot lease that saw the row, the
    record's ``left_key`` naming it, and no association marked for the row itself."""
    main_session_row(datetime(2026, 10, 25, 1, 0, tzinfo=UTC), {4242: None})
    path = local_home.root() / curation.STATE
    runs = curation.Runs.model_validate_json(path.read_text())
    ledger = maintenance.Maintenance(Slots(lambda: 1))
    snapshot, seen = curation_snapshots.observed(runs), curation_snapshots.sessions(runs)
    lease = ledger.adopt_uncertain(
        f"{path}#left", curation.SLOT, "curation", workspace="", generation=snapshot, pids=runs.left,
        covers=curation_snapshots.same_snapshot(curation.SLOT, snapshot, seen), observed=seen,
    )  # fmt: skip
    runs.left_key = lease.slot
    path.write_text(runs.model_dump_json(indent=2))  # the record as 8ad wrote it, its row unkeyed
    if recovered:
        booted = ledger.boot
        ledger.boot = lambda: booted() + 1  # the owner rebooted and recovered it under 8ad
        ledger.recover(lease.id, rebooted=True)
    return lease


@pytest.mark.parametrize("recovered", [False, True], ids=["held", "recovered"])
def test_an_8ad_snapshot_receipt_keeps_its_lease_and_a_row_it_only_saw_is_held_once_alone(root, recovered) -> None:
    """Review 4376886156: a row the snapshot lease saw is no proof that it is the session behind those PIDs.

    The snapshot keeps its one lease, held or recovered; the row gets its own hold once, never again on a restart.
    """
    lease = snapshot_receipt_from_8ad(recovered=recovered)
    calls: list[str] = []
    for _ in range(2):
        again = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root), run=never_runs(calls))
        snapshot, row = ledger_sessions()
        kept = "recovered" if recovered else "held"
        assert (snapshot["id"], snapshot["state"], row["state"]) == (lease.id, kept, "held")
        assert (again.load().folders["shop"].key, again.left_key) == (row["slot"], lease.slot)
        assert again.maintenance.pending("curation") is True
    main_session_row(datetime(2026, 10, 25, 2, 0, tzinfo=UTC), {4242: None})  # main's later session, same PID
    later = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root), run=never_runs(calls))
    states = [s["state"] for s in ledger_sessions()]
    assert (states, later.load().folders["shop"].key not in {lease.slot, row["slot"]}) == (
        ["recovered" if recovered else "held", "held", "held", "held"], True,
    )  # fmt: skip
    later.start("shop")
    drained(later)
    assert calls == []


GENERIC = "RuntimeError: synthetic SDK failure"


@pytest.mark.parametrize("recovered", [False, True], ids=["held", "recovered"])
def test_a_later_failure_stamped_with_the_same_start_after_a_clock_rollback_is_held_anew(root, recovered) -> None:
    """Review on d520: a row's mark names its lease only while that lease records the row's own evidence.

    main's failure before its first PID is held as A. After the clock went back, main's later failure starts at the
    same moment but ends at another, with no key and no PIDs: it is another run, held as B, and nothing starts.
    """
    t0 = datetime.now(UTC) - timedelta(hours=2)
    main_row(GENERIC, t0, t0 + timedelta(seconds=30))
    first = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root))
    [a] = ledger_sessions()
    if recovered:
        rebooted(first)
        first.maintenance.recover(a["id"], rebooted=True)
    main_row(GENERIC, t0, t0 + timedelta(seconds=60))  # the same start, its own end
    calls: list[str] = []
    for _ in range(2):
        later = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root), run=never_runs(calls))
        sessions = ledger_sessions()
        assert [s["state"] for s in sessions] == ["recovered" if recovered else "held", "held"]
        assert later.load().folders["shop"].key == sessions[1]["slot"] != a["slot"]
    later.start("shop")
    drained(later)
    assert (calls, later.load().folders["shop"].reason) == ([], curation.LEFT)
    main_row(GENERIC, t0, t0 + timedelta(seconds=30))  # A's own row again, its key lost: still A, nothing new
    again = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root), run=never_runs(calls))
    assert (len(ledger_sessions()), again.load().folders["shop"].key) == (2, a["slot"])


def owned_failure_before_any_pid(root: Path, *, lost: bool) -> tuple[dict, curation.FolderRun]:
    """This host's own run whose SDK call raises before any PID: its lease A held, its rows naming A's key.

    With *lost*, the failure's own row never reached the file: the running row written before the SDK remains.
    """

    def raises(_cfg) -> Run:
        msg = "synthetic SDK failure before the first PID"
        raise RuntimeError(msg)

    job = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root), run=raises)
    job.start("shop")
    drained(job)
    [a] = ledger_sessions()
    row = job.load().folders["shop"]
    failure = "RuntimeError: synthetic SDK failure before the first PID"
    assert (a["state"], row.key, row.reason) == ("held", a["slot"], failure)
    if lost:
        job._save("shop", curation.FolderRun(state="running", started_at=row.started_at, key=row.key))  # noqa: SLF001
    return a, row


@pytest.mark.parametrize(
    ("recovered", "lost"), [(False, False), (True, True)], ids=["held-final-row", "recovered-lost-final-row"]
)
def test_mains_later_failure_starting_when_an_owned_run_started_is_held_anew_and_the_owned_run_keeps_one_lease(
    root, recovered, lost
) -> None:
    """Review on 4e95: this host's run is found by its admission key, never by its row's times.

    After a clock rollback main's later failure starts at the same moment with another end, no key and no PIDs: it
    is another run, held as B, and nothing starts. The owned run keeps its one lease, held or recovered, whether its
    failure's row or only its running row reached the file.
    """
    a, row = owned_failure_before_any_pid(root, lost=lost)
    calls: list[str] = []
    state = "recovered" if recovered else "held"
    for _ in range(2):  # restarts with the owned run's own rows: no second lease
        again = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root), run=never_runs(calls))
        assert [(s["id"], s["state"]) for s in ledger_sessions()] == [(a["id"], "held")]
        assert again.load().folders["shop"].key == a["slot"]
    if recovered:
        rebooted(again)
        again.maintenance.recover(a["id"], rebooted=True)
        after = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root), run=never_runs(calls))
        assert (after.maintenance.pending("curation"), len(ledger_sessions())) == (False, 1)
    main_row(GENERIC, row.started_at, row.started_at + timedelta(seconds=60))  # main's B: same start, its own end
    for _ in range(2):
        later = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root), run=never_runs(calls))
        sessions = ledger_sessions()
        assert (sessions[0]["id"], sessions[0]["state"]) == (a["id"], state)
        assert ([s["state"] for s in sessions[1:]], later.load().folders["shop"].key) == (["held"], sessions[1]["slot"])
    later.start("shop")
    drained(later)
    assert (calls, later.load().folders["shop"].reason) == ([], curation.LEFT)


@pytest.mark.parametrize("state", ["waiting", "failed"])
def test_a_dateless_queued_row_never_started_holds_nothing(root, state) -> None:
    """Control: a queued row with no times, or the one a restart ended from it, started no session."""
    path = local_home.root() / curation.STATE
    path.parent.mkdir(parents=True, exist_ok=True)
    reason = "" if state == "waiting" else curation.INTERRUPTED
    row = {"state": state, "started_at": None, "ended_at": None, "summary": "", "reason": reason, "entries": [],
           "skipped": {}, "seen": {}}  # fmt: skip
    path.write_text(json.dumps({"folders": {"shop": row}, "left": {}}))
    for _ in range(2):
        job = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root))
        assert (ledger_sessions(), job.working()) == ([], [])


def main_rows(rows: dict[str, tuple[datetime, str]], pids: dict[int, float | None]) -> None:
    """main's record after sessions in several folders, each failing with *reason*, and the PIDs its journal kept."""
    folders = {
        name: {"state": "failed", "started_at": at.isoformat(), "ended_at": (at + timedelta(seconds=30)).isoformat(),
               "summary": "", "reason": reason, "entries": [], "skipped": {}, "seen": {}}
        for name, (at, reason) in rows.items()
    }  # fmt: skip
    path = local_home.root() / curation.STATE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"folders": folders, "left": {str(p): b for p, b in pids.items()}}))


@pytest.mark.parametrize("b_pids", [{4242: None}, {}], ids=["b-with-pids", "both-unknown"])
def test_two_uncertain_sessions_each_keep_a_slot_so_another_project_gets_none(root, b_pids) -> None:
    """Review 4376886156: main's failure A before any PID, then B in another folder, failing with or without PIDs.

    Neither row is proved to be the session behind the PIDs, nor each other's: each holds its own slot. At two slots
    another project gets none, and recovering A leaves B's holds. A restart adds no further hold.
    """
    t0 = datetime.now(UTC) - timedelta(hours=1)
    main_rows({"owlbear": (t0, GENERIC), "shop": (t0 + timedelta(minutes=5), GENERIC)}, b_pids)
    slots = Slots(lambda: 2)
    calls: list[str] = []
    job = curation.Curation(slots, shared=lambda: DataRepo(root), run=never_runs(calls))
    held_slots = 3 if b_pids else 2  # with PIDs on file, their snapshot holds too
    a_slot = job.load().folders["owlbear"].key
    assert (slots.counts(curation.SLOT)[2], slots.take("other", "probe", 1, 1)) == (held_slots, 0)
    again = curation.Curation(Slots(lambda: 2), shared=lambda: DataRepo(root), run=never_runs(calls))
    assert (len(ledger_sessions()), again.load().folders["owlbear"].key) == (held_slots, a_slot)
    a = next(s for s in ledger_sessions() if s["slot"] == a_slot)
    rebooted(again)
    again.maintenance.recover(a["id"], rebooted=True)  # the owner recovers A only
    left = held_slots - 1
    assert ([s["state"] for s in ledger_sessions()].count("held"), again.slots.take("other", "probe", 1, 1)) == (
        left, 1 if left < 2 else 0,
    )  # fmt: skip
    again.start("shop")
    drained(again)
    assert calls == []


def rows_keyed_to_their_snapshot_as_1a174_left(*, recovered: bool) -> maintenance.Lease:
    """1a174's constructor on main's A (failure before any PID) and B (failure with PIDs): one snapshot lease S that
    recorded both rows and marked them, and both rows' cached keys naming S. Built through the ledger API it used."""
    t0 = datetime(2026, 10, 25, 1, 0, tzinfo=UTC)
    main_rows({"owlbear": (t0, GENERIC), "shop": (t0 + timedelta(minutes=5), GENERIC)}, {4242: None})
    path = local_home.root() / curation.STATE
    runs = curation.Runs.model_validate_json(path.read_text())
    ledger = maintenance.Maintenance(Slots(lambda: 2))
    snapshot, seen = curation_snapshots.observed(runs), curation_snapshots.sessions(runs)
    rows = {curation_snapshots.window(n, r) for n, r in runs.folders.items()}
    lease = ledger.adopt_uncertain(
        f"{path}#left", curation.SLOT, "curation", workspace="", generation=snapshot, pids=runs.left,
        covers=curation_snapshots.same_snapshot(curation.SLOT, snapshot, seen), observed=tuple(sorted({*seen, *rows})),
        marks=tuple(f"{path}#{curation_snapshots.window(n, r)}" for n, r in runs.folders.items()),
    )  # fmt: skip
    runs.left_key = lease.slot
    runs.folders = {n: r.model_copy(update={"key": lease.slot}) for n, r in runs.folders.items()}
    path.write_text(runs.model_dump_json(indent=2))
    if recovered:
        booted = ledger.boot
        ledger.boot = lambda: booted() + 1
        ledger.recover(lease.id, rebooted=True)
    return lease


@pytest.mark.parametrize("recovered", [False, True], ids=["snapshot-held", "snapshot-recovered"])
def test_rows_an_earlier_build_keyed_to_their_snapshot_are_judged_again_and_each_held(root, recovered) -> None:
    """Review on 31d: a cached key naming a snapshot's lease owns no row, so each row gets its own hold.

    At two slots another project gets none and no session starts; restarts keep the same leases and keys.
    """
    s = rows_keyed_to_their_snapshot_as_1a174_left(recovered=recovered)
    calls: list[str] = []
    slots = Slots(lambda: 2)
    job = curation.Curation(slots, shared=lambda: DataRepo(root), run=never_runs(calls))
    keys = {n: job.load().folders[n].key for n in ("owlbear", "shop")}
    sessions = {x["slot"]: x for x in ledger_sessions()}
    assert (sessions[s.slot]["state"], s.slot in keys.values(), len(set(keys.values()))) == (
        "recovered" if recovered else "held", False, 2,
    )  # fmt: skip
    assert [sessions[k]["state"] for k in keys.values()] == ["held", "held"]
    assert (slots.counts(curation.SLOT)[2], slots.take("other", "probe", 1, 1)) == (2 if recovered else 3, 0)
    for _ in range(2):
        again = curation.Curation(Slots(lambda: 2), shared=lambda: DataRepo(root), run=never_runs(calls))
        assert ({n: again.load().folders[n].key for n in keys}, len(ledger_sessions())) == (keys, 3)
    again.start("shop")
    drained(again)
    assert (calls, again.load().folders["shop"].reason) == ([], curation.LEFT)


def test_a_true_admission_key_and_a_rows_own_import_key_stay_as_they_are() -> None:
    """Control: only a key that proves its row stays: this host's admission, even one whose lease never began, or
    the row's own import; a snapshot's lease or another row's lease does not."""
    t0 = datetime(2026, 10, 25, 1, 0, tzinfo=UTC)
    row = curation.FolderRun(state="failed", started_at=t0, ended_at=t0 + timedelta(seconds=30), reason=GENERIC)
    own = maintenance.Lease(
        id="a" * 32, project=curation.SLOT, slot="curate:shop:1", kind="curation", workspace="/tmp/w",  # noqa: S108
        started_at=t0, boot=1.0, owner_pid=1, owner_created=None,
    )  # fmt: skip
    window = curation_snapshots.window("shop", row)
    imported = own.model_copy(update={"slot": "pack:legacy-r", "workspace": "", "observed": [window]})
    snapshot = imported.model_copy(update={"slot": "pack:legacy-s", "generation": "g"})
    keyed = lambda key: row.model_copy(update={"key": key})  # noqa: E731
    owns = curation_snapshots.owns_row
    assert owns(curation.SLOT, own, "shop", keyed("curate:shop:1")) is True
    assert owns(curation.SLOT, None, "shop", keyed("curate:shop:2")) is True  # admitted, never began: no session
    assert owns(curation.SLOT, imported, "shop", keyed("pack:legacy-r")) is True
    assert owns(curation.SLOT, snapshot, "shop", keyed("pack:legacy-s")) is False
    assert owns(curation.SLOT, None, "shop", keyed("pack:legacy-x")) is False
    other = imported.model_copy(update={"observed": [curation_snapshots.window("owlbear", row)]})
    assert owns(curation.SLOT, other, "shop", keyed("pack:legacy-r")) is False
