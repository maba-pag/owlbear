"""Memory curation starts no run for a folder whose project has a setting unset or unreadable (#808).

The shared repository, its settings layers, this machine's settings and the slots are real; only the curator session
(``Curation(run=…)``) is recorded instead of started.
"""

from __future__ import annotations

import time

import pytest
from owlbear_memory import MemoryCategory, MemoryEngine

from owlbear_delivery_next.change_contracts.memory_curation_tools import MemoryCurationResult
from owlbear_delivery_next.local_system import local_home
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.local_system.processes import Termination
from owlbear_delivery_next.local_system.slots import Slots
from owlbear_delivery_next.machine_host import curation, curation_block, curation_snapshots
from owlbear_delivery_next.runtimes.session_result import Run
from owlbear_delivery_next.settings import config
from owlbear_delivery_next.settings.config import Layer, Prefs
from owlbear_delivery_next.state_store import machine_settings, work_block
from owlbear_delivery_next.state_store.curation_runs import FolderRun
from owlbear_delivery_next.state_store.layers import layered
from owlbear_delivery_next.state_store.store import MACHINE_SETTINGS, update_layer

GAP = "prefs.ci_poll_seconds"
UNSET = f"settings unset: {GAP}; fill them in on the Settings page"
HELD = "a-change"


def _pending(shared: DataRepo, folder: str, title: str) -> None:
    MemoryEngine(shared.root / folder / "memory").save(
        title=title, content=f"{title}: what to know", categories=[MemoryCategory.PROCESS], confidence=0.8,
        source_agent="builder", scope_agents=[],
    )  # fmt: skip


def _poll(shared: DataRepo, folder: str, seconds: int | None) -> None:
    """*folder*'s own project layer sets the CI poll interval, or leaves it to the unset layers below."""
    prefs = Prefs(ci_poll_seconds=seconds) if seconds else None
    update_layer(shared.project_path(folder), Layer, lambda la: la.model_copy(update={"prefs": prefs}))


def _missing(shared: DataRepo, folder: str) -> list[str]:
    return layered(shared.global_path, shared.project_path(folder), local_home.root() / MACHINE_SETTINGS).missing


def _row(job: curation.Curation, folder: str) -> FolderRun:
    return job.load().folders[folder]


def _drained(job: curation.Curation) -> None:
    for _ in range(500):
        if job.worker is None:
            return
        time.sleep(0.02)
    pytest.fail("the curation queue did not drain")


class Curator:
    """The curator runtime: records each folder it is started for and judges nothing."""

    def __init__(self) -> None:
        self.folders: list[str] = []

    def __call__(self, cfg) -> Run:
        self.folders.append(cfg.memory.parent.name)
        return Run(cfg.session_id, ending="result", payload=MemoryCurationResult(summary="ok", entries=[]),
                   termination=Termination(confirmed=True))  # fmt: skip


@pytest.fixture
def shared(shared_repo, monkeypatch) -> DataRepo:
    """Folders ``a`` and ``b`` of the shared repository; A's layer leaves the CI poll interval unset, B's sets it."""
    prefs = config.BASE.prefs.model_copy(update={"ci_poll_seconds": None})
    monkeypatch.setattr(config, "BASE", config.BASE.model_copy(update={"prefs": prefs}))
    repo = DataRepo(shared_repo[0])
    for folder in ("a", "b"):
        (repo.root / folder / "memory").mkdir(parents=True)
    _poll(repo, "a", None)
    _poll(repo, "b", 20)
    assert (_missing(repo, "a"), _missing(repo, "b"), machine_settings.current().missing) == ([GAP], [], [])
    return repo


def test_only_the_unblocked_folder_curates_and_the_blocked_one_runs_once_its_setting_is_set(shared) -> None:
    curator = Curator()
    job = curation.Curation(Slots(lambda: 1), shared=lambda: shared, run=curator)
    _poll(shared, "a", 20)  # both may run: each gets a finished run that saw its entry
    for folder in ("a", "b"):
        _pending(shared, folder, "First lesson")
    job.start(curation.ALL)
    _drained(job)
    seen = _row(job, "a").seen
    assert (sorted(curator.folders), len(seen)) == (["a", "b"], 1)

    _poll(shared, "a", None)
    for folder in ("a", "b"):
        _pending(shared, folder, "Second lesson")
    assert job.nudge(None, "idle") == ["a", "b"]  # both due; A is refused at its turn
    _drained(job)
    job.start("a")
    _drained(job)
    job.start(curation.ALL)
    _drained(job)
    a = _row(job, "a")
    assert curator.folders == ["a", "b", "b", "b"]
    assert (a.state, a.reason, a.seen, a.ended_at == a.started_at) == ("failed", UNSET, seen, True)
    assert job.due("a")
    blocked = {f["folder"]: f["blocked"] for f in job.read()["folders"]}
    assert (blocked["a"], blocked["b"]) == (UNSET, "")

    _poll(shared, "a", 20)
    assert job.queue == []  # A's refused request has left; no manual request waits
    assert job.nudge(None, "idle") == ["a"]
    _drained(job)
    assert (curator.folders[-1], _row(job, "a").state) == ("a", "done")


def test_a_folder_with_no_project_layer_curates_though_project_settings_are_unset(shared) -> None:
    (shared.root / "c" / "memory").mkdir(parents=True)  # no project behind it (D-01M6A32JGMSYG3HQ58HF4QAB1T)
    layers = (shared.project_path("a").exists(), shared.project_path("c").exists())
    assert (layers, _missing(shared, "c")) == ((True, False), [GAP])
    curator = Curator()
    job = curation.Curation(Slots(lambda: 1), shared=lambda: shared, run=curator)
    for folder in ("a", "c"):
        _pending(shared, folder, "First lesson")
    job.start("a")
    job.start("c")
    _drained(job)
    blocked = {f["folder"]: f["blocked"] for f in job.read()["folders"]}
    assert (curator.folders, _row(job, "c").state, blocked["a"], blocked["c"]) == (["c"], "done", UNSET, "")


def test_a_setting_cleared_while_the_request_waits_for_its_slot_refuses_it_at_the_grant(shared) -> None:
    slots, curator = Slots(lambda: 1), Curator()
    assert slots.take(HELD, "a-step", 1, 1) == 1  # a project's step holds the only slot
    job = curation.Curation(slots, shared=lambda: shared, run=curator)
    job.start("b")
    _poll(shared, "b", None)  # cleared while B waits
    slots.give(HELD, "a-step")
    _drained(job)
    b = _row(job, "b")
    assert (curator.folders, b.state, b.reason) == ([], "failed", UNSET)
    assert slots.take(HELD, "after", 1, 1) == 1  # the refusal gave the slot back


def test_a_blocked_row_read_back_after_a_restart_is_a_refusal_and_holds_nothing(shared) -> None:
    job = curation.Curation(Slots(lambda: 1), shared=lambda: shared, run=Curator())
    job.start("a")
    _drained(job)
    a = _row(job, "a")
    assert (curation_snapshots.refused(a), curation.legacy_uncertain(a)) == (True, False)

    curator = Curator()
    restarted = curation.Curation(Slots(lambda: 1), shared=lambda: shared, run=curator)
    assert (_row(restarted, "a").reason, restarted.lingering()) == (UNSET, False)
    restarted.start("b")
    _drained(restarted)
    assert curator.folders == ["b"]


def test_an_unreadable_global_refuses_every_folder_and_keeps_what_the_last_run_saw(shared) -> None:
    curator = Curator()
    job = curation.Curation(Slots(lambda: 1), shared=lambda: shared, run=curator)
    _pending(shared, "b", "First lesson")
    job.start("b")
    _drained(job)
    seen = _row(job, "b").seen
    assert len(seen) == 1

    shared.global_path.write_text("{not json")
    job.start("b")
    _drained(job)
    b = _row(job, "b")
    assert curator.folders == ["b"]
    assert (b.state, b.reason.startswith(work_block.UNREADABLE), b.seen) == ("failed", True, seen)
    assert (curation_snapshots.refused(b), b.ended_at == b.started_at) == (True, True)
    restarted = curation.Curation(Slots(lambda: 1), shared=lambda: shared, run=curator)
    assert (_row(restarted, "b").reason, restarted.lingering()) == (b.reason, False)


def test_an_unset_update_check_interval_on_this_machine_blocks_every_folder(shared, request) -> None:
    request.getfixturevalue("intervals_unset")  # after the premise, which has this machine's settings complete
    unset = machine_settings.current().missing
    assert set(unset) == {f"update_check_hours_{k}" for k in ("owlbear", "pds", "impeccable")}
    curator = Curator()
    job = curation.Curation(Slots(lambda: 1), shared=lambda: shared, run=curator)
    job.start("b")
    _drained(job)
    assert curator.folders == []
    assert all(f"machine.{k}" in _row(job, "b").reason for k in unset)
    assert curation_block.blocked(shared, "b") == _row(job, "b").reason
    assert all(f"machine.{k}" in curation_block.blocked(shared, "no-layer") for k in unset)  # a folder without one too
