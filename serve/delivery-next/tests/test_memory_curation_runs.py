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


def test_a_trigger_starts_only_folders_with_pending_entries_no_run_saw_and_while_paused_only_when_allowed(root) -> None:
    """The merge and idle triggers: a skipped entry starts no run until it changes; Pause holds them unless the
    machine's "Curate memory while paused" is on (the owner, 2026-10-22)."""
    from owlbear_delivery_next.machine_host import registry  # noqa: PLC0415

    left = pending(root / "shop" / "memory", "Unsure lesson")
    report = MemoryCurationResult(
        summary="1 skipped", entries=[Judged(entry_id=left.id, action="skipped", confidence=50)]
    )
    runs = []

    def run(cfg) -> Run:
        runs.append(cfg.memory.parent.name)
        return Run(cfg.session_id, ending="result", payload=report, termination=Termination(confirmed=True))

    job = curation.Curation(Slots(lambda: 1), shared=lambda: DataRepo(root), run=run)
    assert (job.due("shop"), job.due("owlbear")) == (True, False)
    assert job.nudge(None, paused=True) == []  # paused, the switch off by default
    assert job.nudge(None, paused=False) == ["shop"]
    finished(job)
    assert (job.due("shop"), job.nudge(["shop"], paused=False)) == (False, [])  # unchanged: no other run

    MemoryEngine(root / "shop" / "memory").edit(
        left.id, {"content": "Unsure lesson: now with evidence"}, left.updated_at
    )
    saved = registry.load()
    registry.configure(
        saved.settings.model_copy(update={"curate_while_paused": True}), registry.revision(saved.settings)
    )
    assert job.nudge(["shop"], paused=True) == ["shop"]  # changed, and allowed while paused
    finished(job)
    assert runs == ["shop", "shop"]
