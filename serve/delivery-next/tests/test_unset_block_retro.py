"""Retro starts no run of a unit whose project has a setting unset or unreadable (#808), on a two-project machine.

Only ``retro_review.asked`` is faked. The stores, chat logs, settings and the machine's ``blocked`` seam are real.
"""

from __future__ import annotations

import gzip
import json
import os
import subprocess
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from owlbear_delivery_next.change_contracts.models import Brief, Change, Criterion, Exit, Names, Outcome
from owlbear_delivery_next.improvement import chatlogs, retro_store, retro_units, spotter
from owlbear_delivery_next.local_system import codebase, data_place, maintenance
from owlbear_delivery_next.local_system.slots import Slots
from owlbear_delivery_next.machine_host import retro_block
from owlbear_delivery_next.machine_host.machine import Machine
from owlbear_delivery_next.machine_host.project import Project
from owlbear_delivery_next.machine_host.retro_inputs import failed_grading
from owlbear_delivery_next.machine_host.retro_job import RetroJob, Seams
from owlbear_delivery_next.project_host.host import HostRecord
from owlbear_delivery_next.settings import config
from owlbear_delivery_next.settings.config import Layer, Prefs
from owlbear_delivery_next.state_store import machine_settings, registry
from owlbear_delivery_next.state_store.store import Store

GAP = "prefs.ci_poll_seconds"
UNSET = f"settings unset: {GAP}; fill them in on the Settings page"
UNSET_PDS = "settings unset: machine.update_check_hours_pds; fill them in on the Settings page"
RECORDS = "records-2026-01-01.jsonl"


class Asker:
    """``retro_review.asked``: each call costs a credit and grades every record it is shown, finding nothing."""

    def __init__(self) -> None:
        self.calls = 0

    async def __call__(self, message, meter, _role, **_how):
        self.calls += 1
        share = meter.part()
        share.call(1.0)
        share.ended(1.0, confirmed=True)
        shown = json.loads(message.split("```json\n")[-1].rsplit("\n```", 1)[0]).get("records", ())
        return json.dumps({"findings": [], "grades": [{"record": r["id"], "grade": "worth-it"} for r in shown]})


def _git(root: Path) -> None:
    for args in (["init", "-q"], ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty",
                                  "-m", "i"]):  # fmt: skip
        subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)  # noqa: S603, S607


def _layer(st: Store, prefs: Prefs | None) -> None:
    assert st.save(st.config_path, Layer, lambda la: la.model_copy(update={"prefs": prefs}), "t", owner=True) == ""


def _register(m: Machine, pid: str, root: Path) -> Store:
    """*root* registered on machine *m* as *pid* and loaded, with its real store."""
    root.mkdir(parents=True, exist_ok=True)
    _git(root)
    p = Project(registry.Project(id=pid, path=str(root), added_at=datetime.now(UTC)))
    p.state, p.store = "loaded", Store.open(root)
    m.projects[pid] = p
    return p.store


def _finished(st: Store, pid: str) -> None:
    """A Change of *pid* finished now, with one captured session and one Spotter record of it."""
    place, sid = str(st.root / "wt"), f"s-{pid}"
    with (chatlogs.root() / "manifest.jsonl").open("a") as out:
        out.write(json.dumps({"event": "started", "session": sid, "worktree": place, "role": "builder"}) + "\n")
    folder = retro_units.folder(sid)
    folder.mkdir(parents=True)
    turns = [("user.message", "add the week column"), ("assistant.message", "Added; the tests pass.")]
    log = "".join(json.dumps({"type": t, "data": {"content": c}}) + "\n" for t, c in turns)
    (folder / "log.jsonl.gz").write_bytes(gzip.compress(log.encode()))
    (folder / "sidecar.json").write_text(json.dumps({"session": sid, "provisional": False, "outputs": []}))
    _record(f"rec-{pid}", pid, sid, "2026-01-01T00:00:00+00:00")
    change = Change(
        slug="fix-it", finished_at=datetime.now(UTC), names=Names(worktree=place),
        brief=Brief(outcome="a week column", criteria=[Criterion(id="c1", text="weeks are ISO")]),
        outcome=Outcome(exit=Exit.DONE, at=datetime.now(UTC)),
    )  # fmt: skip
    with st.lock("fix-it") as lock:
        st.write(lock, change)


def _record(rid: str, pid: str, sid: str, at: str) -> None:
    record = {"id": rid, "at": at, "look": "handoff", "call": rid, "cutoff": 2, "category": "none", "project": pid}
    with (spotter.root() / RECORDS).open("a") as out:
        out.write(json.dumps(record | {"change": "fix-it", "step": "build", "session": sid}) + "\n")
    (spotter.root() / "cards" / f"{rid}.json.gz").write_bytes(gzip.compress(b"{}"))


def _chat(sid: str, cwd: Path) -> None:
    """A quiet chat *sid* whose workspace is *cwd*."""
    log = chatlogs.state() / sid / "events.jsonl"
    log.parent.mkdir(parents=True)
    (log.parent / "workspace.yaml").write_text(f"cwd: {cwd}\n")
    said = [("user.message", "fix the export"), ("assistant.message", "Fixed; the export tests pass.")]
    log.write_text("".join(json.dumps({"type": t, "data": {"content": c}}) + "\n" for t, c in said))
    at = (datetime.now(UTC) - timedelta(days=2)).timestamp()
    os.utime(log, (at, at))


@pytest.fixture
def machine():
    m = Machine(HostRecord(url="http://x/", token=uuid.uuid4().hex, pid=1, started_at=datetime.now(UTC),
                           code=codebase.CURRENT))  # fmt: skip
    try:
        yield m
    finally:
        m.stop_all()


@pytest.fixture
def gap(monkeypatch) -> str:
    """The CI poll interval unset under every project's layer; this machine's settings complete."""
    prefs = config.BASE.prefs.model_copy(update={"ci_poll_seconds": None})
    monkeypatch.setattr(config, "BASE", config.BASE.model_copy(update={"prefs": prefs}))
    return GAP


@pytest.fixture
def a_b(tmp_path, machine, monkeypatch, gap) -> tuple[Store, Store]:
    """A leaves the gap unset, B sets it; each has a finished Change and quiet enrolled chats, one in A's subfolder."""
    for d in (chatlogs.root(), spotter.root() / "cards"):
        d.mkdir(parents=True, exist_ok=True)
    retro_store.update(lambda t: t.update(watermark=(datetime.now(UTC) - timedelta(days=3)).isoformat()))
    a, b = _register(machine, "pa", tmp_path / "a"), _register(machine, "pb", tmp_path / "b")
    _layer(b, Prefs(ci_poll_seconds=20))
    for st, pid in ((a, "pa"), (b, "pb")):
        _finished(st, pid)
    (tmp_path / "a" / "sub").mkdir()
    for sid, cwd in (("ca", tmp_path / "a"), ("ca-sub", tmp_path / "a" / "sub"), ("cb", tmp_path / "b")):
        _chat(sid, cwd)
    folders = [str(tmp_path / "a"), str(tmp_path / "b")]
    monkeypatch.setattr(machine_settings, "BASE", machine_settings.BASE.model_copy(update={"enrolled_chats": folders}))
    assert (a.settings().missing, b.settings().missing, machine_settings.current().missing) == ([gap], [], [])
    return a, b


def _job(m: Machine, said: list[str], asker: Asker | None = None) -> RetroJob:
    slots = Slots(lambda: 1)
    owner = maintenance.Maintenance(slots, boot=lambda: 10.0, observe=lambda *_: False)
    slots.open()
    seams = Seams(say=said.append, asked=asker or Asker(), idle=lambda: True, projects=m.retro.seams.projects,
                  blocked=m.retro.seams.blocked)  # fmt: skip
    return RetroJob(slots, seams, owner)


def _runs() -> list[tuple[str, str, str, str]]:
    return [(r["unit"], r["trigger"], r.get("mode", ""), r["result"]) for r in retro_store.run_states().values()]


def test_automatic_runs_start_only_for_the_project_whose_settings_are_set_and_once_it_is_set(a_b, machine):
    a, _ = a_b
    said: list[str] = []
    job = _job(machine, said)
    job.tick(0.0)
    job.tick(1.0)
    assert {u for u, *_ in _runs()} == {"chg:pb:fix-it", "chat:cb"}, "A did not start"
    for uid in ("chg:pa:fix-it", "chat:ca", "chat:ca-sub"):
        assert said.count(f"Retro does not run {uid}: {UNSET}") == 1

    _layer(a, Prefs(ci_poll_seconds=20))
    job.tick(2.0)
    assert {u for u, *_ in _runs()} >= {"chg:pa:fix-it", "chat:ca", "chat:ca-sub"}
    assert "Retro may run chg:pa:fix-it again" in said


def test_late_records_of_a_blocked_project_wait_and_its_button_records_a_plain_refusal(a_b, machine):
    a, _ = a_b
    _layer(a, Prefs(ci_poll_seconds=20))
    job = _job(machine, said := [])
    job.tick(0.0)
    assert ("chg:pa:fix-it", "change", "judge", "judged") in _runs()
    _layer(a, None)
    _record("rec-late", "pa", "s-pa", "2026-01-01T00:01:00+00:00")
    before = len(_runs())
    job.tick(1.0)
    assert len(_runs()) == before  # the late pass skips A's late record
    retro_store.request("owner", change="pa:fix-it")
    job.tick(2.0)
    assert _runs()[before:] == [("chg:pa:fix-it", "button", "judge", f"refused: {UNSET}")]
    assert failed_grading() == set()
    assert said.count(f"Retro does not run chg:pa:fix-it: {UNSET}") == 1

    _layer(a, Prefs(ci_poll_seconds=20))
    job.tick(3.0)
    assert _runs()[before + 1 :] == [("chg:pa:fix-it", "change", "grade-only", "judged")]
    assert "rec-late" in retro_store.graded()


@pytest.mark.parametrize("reverse", [False, True], ids=["parent-first", "child-first"])
@pytest.mark.parametrize("blocked", ["parent", "child"])
@pytest.mark.usefixtures("gap")
def test_a_chat_in_a_nested_project_belongs_to_the_innermost(tmp_path, machine, blocked, reverse):
    parent = _register(machine, "pp", tmp_path / "p")
    child = _register(machine, "pc", tmp_path / "p" / "c")
    _layer(child if blocked == "parent" else parent, Prefs(ci_poll_seconds=20))
    _chat("cn", tmp_path / "p" / "c" / "deep")
    if reverse:
        machine.projects = dict(reversed(machine.projects.items()))
    assert machine.retro.seams.blocked("chat:cn") == ("" if blocked == "parent" else UNSET)


def test_units_of_an_unloaded_or_unknown_project_wait_and_others_follow_this_machine(tmp_path, machine, monkeypatch):
    failed = Project(registry.Project(id="pf", path=str(tmp_path / "f"), added_at=datetime.now(UTC)))
    failed.state = machine.projects.setdefault("pf", failed).state = "failed"
    _chat("cx", tmp_path / "elsewhere")
    blocked = machine.retro.seams.blocked
    assert blocked("chg:pf:fix-it") == "its project is failed"
    assert blocked("chg:pz:fix-it") == "its project is not registered"
    assert (blocked("chat:cx"), blocked("syn:large")) == ("", "")
    assert blocked("chat:unknown").startswith("settings can't be read: ")
    update = {"update_check_hours_pds": None}
    monkeypatch.setattr(machine_settings, "BASE", machine_settings.BASE.model_copy(update=update))
    assert blocked("chat:cx") == blocked("syn:large") == UNSET_PDS


def test_the_button_on_a_synthetic_unit_records_a_refusal_when_global_is_unreadable(tmp_path, machine, monkeypatch):
    shared = tmp_path / "data"
    shared.mkdir()
    (shared / data_place.DataRepo(shared).global_path.name).write_text("{not json")
    monkeypatch.setenv(data_place.VIEW, str(shared))
    retro_store.request("owner", synthetic="large")
    _job(machine, []).tick(0.0)
    [(unit, trigger, mode, result)] = _runs()
    assert (unit.startswith("syn:"), trigger, mode) == (True, "button", "judge")
    assert result.startswith("refused: settings can't be read: ")
    assert retro_block.block(unit, []) == result.removeprefix("refused: ")
