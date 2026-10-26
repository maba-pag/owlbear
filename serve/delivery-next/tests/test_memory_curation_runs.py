"""Item 5 slice 4: automatic memory curation runs one curator session per memory folder of the shared repository."""

import time
from pathlib import Path

import pytest
from owlbear_memory import MemoryCategory, MemoryEngine

from owlbear_delivery_next.change_contracts import memory_curation_tools, tools
from owlbear_delivery_next.change_contracts.memory_curation_tools import Judged, MemoryCurationResult
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.local_system.processes import Termination
from owlbear_delivery_next.local_system.slots import Slots
from owlbear_delivery_next.machine_host import curation
from owlbear_delivery_next.runtimes.session_result import Run
from owlbear_delivery_next.settings import config
from owlbear_delivery_next.settings.config import GlobalLayer
from owlbear_delivery_next.state_store import registry, settings_carry, store
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
    from owlbear_delivery_next.state_store import registry  # noqa: PLC0415

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
    finished(job)
    states = {f["folder"]: (f["state"], f["reason"]) for f in job.read()["folders"]}
    assert states == {"owlbear": ("failed", "RuntimeError: the runtime broke"), "shop": ("done", "")}

    job._save("shop", curation.FolderRun(state="running"))  # noqa: SLF001 - OwlBear stops while it runs
    again = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root))
    assert {f["folder"]: f["state"] for f in again.read()["folders"]}["shop"] == "failed"


def test_processes_that_may_still_run_keep_their_slot_and_the_machine_busy_until_they_are_gone(
    root, monkeypatch
) -> None:
    alive = [True]
    monkeypatch.setattr(curation.processes, "alive", lambda _pid, _created: alive[0])
    slots = Slots(lambda: 2)

    def run(cfg) -> Run:
        return Run(cfg.session_id, ending="result", payload=MemoryCurationResult(summary="ok", entries=[]),
                   termination=Termination(confirmed=False, survivors=(4242,)))  # fmt: skip

    job = curation.Curation(slots, shared=lambda: DataRepo(root), run=run)
    job.start("shop")
    for _ in range(200):
        if job.queue == []:
            break
        time.sleep(0.02)
    assert (job.working(), slots.counts(curation.SLOT)[2]) == ([curation.LINGERING], 1)
    assert curation.Curation(Slots(lambda: 2), shared=lambda: DataRepo(root)).left == {4242: None}  # kept on file
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
    monkeypatch.setattr(curation.processes, "alive", lambda _pid, _created: alive[0])
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
    slots = Slots(lambda: 1, closed=True)
    restarted = curation.Curation(slots, shared=lambda: DataRepo(root))
    assert (slots.counts(curation.SLOT)[2], restarted.working()) == (1, [curation.LINGERING])
    alive[0] = False
    assert (restarted.working(), slots.counts(curation.SLOT)[2]) == ([], 0)


def test_a_run_unconfirmed_without_processes_to_watch_gives_its_slot_back_and_says_so(root) -> None:
    slots = Slots(lambda: 1)

    def run(cfg) -> Run:
        return Run(cfg.session_id, ending="error", detail="runtime PID unknown",
                   termination=Termination(confirmed=False))  # fmt: skip

    job = curation.Curation(slots, shared=lambda: DataRepo(root), run=run)
    job.start("shop")
    finished(job)
    shop = {f["folder"]: f for f in job.read()["folders"]}["shop"]
    assert (shop["state"], curation.UNKNOWN in shop["reason"], slots.counts(curation.SLOT)[2]) == ("failed", True, 0)


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
