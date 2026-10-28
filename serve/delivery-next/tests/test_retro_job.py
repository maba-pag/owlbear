"""Retro's job in the machine host (#715): leases per paid call, recovery, triggers, eligibility and pruning."""

import asyncio
import gzip
import json
import os
import threading
import time
import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from owlbear_delivery_next.change_contracts.models import Brief, Change, Criterion, Exit, Inputs, Names, Outcome, Review
from owlbear_delivery_next.improvement import cases, chatlogs, retro_evidence, retro_store, retro_units, spotter
from owlbear_delivery_next.improvement import retro_proposals as props
from owlbear_delivery_next.improvement import retro_synthetic as syn
from owlbear_delivery_next.local_system import codebase, maintenance, processes
from owlbear_delivery_next.local_system.slots import Slots
from owlbear_delivery_next.machine_host import cases_job, retro_job
from owlbear_delivery_next.machine_host.auto_update import IDLE_FOR
from owlbear_delivery_next.machine_host.machine import Machine
from owlbear_delivery_next.machine_host.retro_inputs import Running
from owlbear_delivery_next.machine_host.retro_job import LINGERING, RetroJob, Seams
from owlbear_delivery_next.project_host.host import HostRecord
from owlbear_delivery_next.runtimes import spotter_look
from owlbear_delivery_next.runtimes.session_result import Run
from owlbear_delivery_next.state_store import machine_settings


def _owner(*, closed=False):
    return maintenance.Maintenance(Slots(lambda: 2, closed=closed), boot=lambda: 10.0, observe=lambda *_: False)


def test_a_retro_lease_is_begun_persisted_finished_and_reloaded_under_its_own_kind():
    owner = _owner()
    assert owner.slots.take("retro", "retro:b-1", 1, 1) == 1
    lease = owner.begin("retro", "retro:b-1", "retro", "")
    assert owner.holding("retro") == ["retro"]
    owner.finished(lease, Run("x", termination=processes.Termination(confirmed=True)))
    again = _owner(closed=True)
    assert again.holding("retro") == []
    assert [(s["kind"], s["state"]) for s in again.read()["sessions"]] == [("retro", "released")]


def test_a_dead_owners_retro_lease_reloads_held_with_its_slot():
    owner = _owner()
    assert owner.slots.take("retro", "retro:b-2", 1, 1) == 1
    owner.begin("retro", "retro:b-2", "retro", "")
    restarted = _owner(closed=True)
    restarted.slots.open()
    assert restarted.holding("retro") == ["retro"]
    assert restarted.slots.take("retro", "retro:b-3", 1, 1) == 0


class Dead(BaseException):
    """The host died here: nothing after it runs, no ``finally`` of the job's own included."""


def _die(*_a, **_k):
    raise Dead


def _evidence(message):
    return json.loads(message.split("```json\n")[-1].rsplit("\n```", 1)[0])


class Asker:
    """``retro_review.asked``: each call costs *cost* credits and grades every record it is shown, finding nothing."""

    def __init__(self, cost=1.0, during=None):
        self.cost, self.during, self.seen, self.messages = cost, during, [], []

    async def __call__(self, message, meter, _role, *, agent, seconds):
        assert seconds == 60.0
        self.seen.append(agent)
        self.messages.append(message)
        if self.during:
            self.during(len(self.seen))
        share = meter.part()
        share.call(self.cost)
        share.ended(self.cost, confirmed=True)
        grades = [{"record": r["id"], "grade": "worth-it"} for r in _evidence(message).get("records", ())]
        return json.dumps({"findings": [], "grades": grades})


@pytest.fixture
def said(monkeypatch):
    """The machine's settings as the job reads them, its limit and its roles."""
    found = SimpleNamespace(retro_after_change="off", retro_when_idle="off", enrolled_chats=[], limit=125.0)
    monkeypatch.setattr(machine_settings, "current", lambda: found)
    monkeypatch.setattr(cases_job, "limits", lambda: {"retro": found.limit})
    monkeypatch.setattr(retro_job, "session", lambda _agent: (None, 60.0))
    return found


def _job(asker, state=None, *, restarted=False, projects=None):
    state = state or SimpleNamespace(paused=False, fence="", idle=False)
    slots = Slots(lambda: 1, closed=restarted)
    owner = maintenance.Maintenance(slots, boot=lambda: 10.0, observe=lambda *_: False)  # its leases reloaded
    slots.open()
    seams = Seams(
        fenced=lambda: state.fence,
        paused=lambda: state.paused,
        asked=asker,
        idle=lambda: state.idle,
        projects=lambda: projects or {},
    )
    return RetroJob(slots, seams, owner)


def _runs():
    return list(retro_store.run_states().values())


def _large():
    return syn.specs("large")[0]


def _chat(tmp_path, sid, *, quiet_days=2):
    """A chat log of *sid* in the enrolled folder, quiet for *quiet_days*."""
    folder = tmp_path / "enrolled"
    folder.mkdir(exist_ok=True)
    log = chatlogs.state() / sid / "events.jsonl"
    log.parent.mkdir(parents=True)
    (log.parent / "workspace.yaml").write_text(f"cwd: {folder}\n")
    said = [("user.message", "fix the export"), ("assistant.message", "Fixed; the export tests pass.")]
    log.write_text("".join(json.dumps({"type": t, "data": {"content": c}}) + "\n" for t, c in said))
    at = (datetime.now(UTC) - timedelta(days=quiet_days)).timestamp()
    os.utime(log, (at, at))
    return str(folder)


def _finished_change(tmp_path):
    """A finished Change of project p1 with one captured builder session and one Spotter record of it."""
    place, sid = str(tmp_path / "wt" / "fix-it"), "s-build"
    chatlogs.root().mkdir(parents=True, exist_ok=True)
    (chatlogs.root() / "manifest.jsonl").write_text(
        json.dumps({"event": "started", "session": sid, "worktree": place, "role": "builder"}) + "\n"
    )
    folder = retro_units.folder(sid)
    folder.mkdir(parents=True)
    turns = [("user.message", "add the week column"), ("assistant.message", "Added; the tests pass.")]
    log = "".join(json.dumps({"type": t, "data": {"content": c}}) + "\n" for t, c in turns)
    (folder / "log.jsonl.gz").write_bytes(gzip.compress(log.encode()))
    (folder / "sidecar.json").write_text(json.dumps({"session": sid, "provisional": False, "outputs": []}))
    record = {"id": "rec-c", "at": "2026-01-01T00:00:00+00:00", "look": "handoff", "call": "c", "cutoff": 2}
    record |= {"category": "none", "project": "p1", "change": "fix-it", "step": "build", "session": sid}
    (spotter.root() / "records-2026-01-01.jsonl").write_text(json.dumps(record) + "\n")
    (spotter.root() / "cards" / "rec-c.json.gz").write_bytes(gzip.compress(b"{}"))
    change = Change(
        slug="fix-it",
        finished_at=datetime.now(UTC),
        names=Names(worktree=place),
        brief=Brief(outcome="a week column in the export", criteria=[Criterion(id="c1", text="weeks are ISO")]),
        reviews=[Review(commit="abc", inputs=Inputs(), verdict="fix", findings=["the week starts on Sunday"])],
        outcome=Outcome(exit=Exit.DONE, at=datetime.now(UTC)),
    )
    st = SimpleNamespace(
        root=tmp_path / "p1", name="p1", slugs=lambda: ["fix-it"], read=lambda _s: change, events=lambda _s: []
    )
    return {"p1": (st, None)}


def test_a_finished_change_is_planned_then_judged_against_its_brief_and_reviews_with_its_records_graded(said, tmp_path):
    projects, said.retro_after_change = _finished_change(tmp_path), "on"
    retro_store.update(lambda t: t.update(watermark=(datetime.now(UTC) - timedelta(days=1)).isoformat()))
    assert retro_evidence.plan("chg:p1:fix-it", projects)["judge_batches"] == 1

    _job(asker := Asker(), projects=projects).tick(0.0)

    [run] = _runs()
    assert (run["unit"], run["trigger"], run["result"]) == ("chg:p1:fix-it", "change", "judged")
    assert [g["grade"] for g in retro_store.grades(unit="chg:p1:fix-it")] == ["worth-it"]
    later = _evidence(asker.messages[0])["parts"][0]["later"]
    assert "its brief: a week column" in later
    assert "finding: the week starts on Sunday" in later


# Interruptions, gates F1, H1 and J2


@pytest.mark.parametrize("when", ["after its session, before its settled line", "during its session"])
@pytest.mark.usefixtures("said")
def test_a_call_interrupted_unsettled_ends_its_run_stopped_on_restore_and_nothing_more_is_asked(when):
    first = Asker()
    job = _job(first)
    retro_store.request("owner", synthetic="large")
    with pytest.MonkeyPatch.context() as dying:
        if when == "during its session":
            first.during = _die
            dying.setattr(job, "_released", lambda _lease: False)  # dead: its lease is never finished
        else:
            dying.setattr(retro_store, "keep", _die)
        with pytest.raises(Dead):
            job.tick(0.0)

    again = _job(later := Asker(), restarted=True)
    again.tick(1.0)

    [run] = _runs()
    assert (run["result"], later.seen) == ("stopped: unknown spend after an interruption", [])
    [rev] = retro_store.units(synthetic=True)[syn.unit_id(_large())]["revisions"]
    assert rev["state"] == "stopped"
    assert again.lingering() is (when == "during its session")
    assert again.working() == ([LINGERING] if again.lingering() else [])


def test_a_run_interrupted_between_settled_calls_resumes_on_what_is_left_of_its_limit(said):
    said.limit = 1.5
    first, calls = Asker(), []
    real = retro_store.run_event

    def dies_at_the_second_call(run, event, **fields):
        calls.extend([event] if event == "inflight" else [])
        if len(calls) == 2:
            raise Dead
        real(run, event, **fields)

    retro_store.request("owner", synthetic="large")
    with pytest.MonkeyPatch.context() as dying:
        dying.setattr(retro_store, "run_event", dies_at_the_second_call)
        with pytest.raises(Dead):
            _job(first).tick(0.0)

    _job(later := Asker(), restarted=True).tick(1.0)

    [run] = _runs()
    assert (first.seen, later.seen) == (["retro"], ["retro"])  # the first batch replayed, not asked again
    assert run["result"] == "stopped: an answer was cut off at the credit limit"
    assert (run["spent"], run["calls"]) == (2.0, 2)


# Eligibility at the call, gate J3


def test_a_chat_unenrolled_while_its_button_run_waits_for_a_slot_is_refused_unread(said, tmp_path, monkeypatch):
    said.enrolled_chats = [_chat(tmp_path, "c1")]
    job = _job(asker := Asker())
    assert job.slots.take("retro", "other", 1, 1) == 1
    real = job.slots.take

    def take(share, key, *args, **kwargs):
        got = real(share, key, *args, **kwargs)
        if key.startswith("retro:open") and not got:  # queued behind "other": unenrolled, then granted
            said.enrolled_chats = []
            job.slots.give("retro", "other")
        return got

    monkeypatch.setattr(job.slots, "take", take)
    retro_store.request("owner", chat="c1")
    job.tick(0.0)

    [run] = _runs()
    assert (run["result"], asker.seen) == ("refused: it is not an enrolled chat", [])
    assert not retro_units.folder("c1").exists()


def test_the_button_never_reads_one_of_owlbears_own_sessions(said, tmp_path):
    said.enrolled_chats = [_chat(tmp_path, "c2")]
    chatlogs.root().mkdir(parents=True, exist_ok=True)
    with (chatlogs.root() / "manifest.jsonl").open("a") as out:
        out.write(json.dumps({"event": "started", "session": "c2", "worktree": "/w"}) + "\n")
    retro_store.request("owner", chat="c2")
    _job(asker := Asker()).tick(0.0)

    [run] = _runs()
    assert run["result"].startswith("refused: ")
    assert (asker.seen, retro_units.folder("c2").exists()) == ([], False)


# Triggers, switches, the fence, drain and an unconfirmed end, gate H8


def test_idle_means_no_other_work_for_a_while_retros_own_run_aside():
    m = SimpleNamespace(auto=SimpleNamespace(mono=lambda: 10_000.0, last_use=0.0), updating=False, ending=False)
    m.slots, m.paused, m.lock, m.say, m.projects, m.work = Slots(lambda: 1), False, threading.Lock(), str, {}, []
    m.maintenance = maintenance.Maintenance(m.slots, boot=lambda: 10.0, observe=lambda *_: False)
    m.busy = lambda: m.work
    job = RetroJob.attach(m, str)
    m.work = ["p: builder of x"]
    assert not job.seams.idle()
    m.work, job.running = ["Retro: chat:c1"], "chat:c1"
    assert job.seams.idle()
    m.auto.last_use = 10_000.0 - IDLE_FOR + 1
    assert not job.seams.idle()


@pytest.mark.parametrize(
    "case",
    [("off", False, True, False), ("on", True, True, False), ("paused", True, True, True), ("on", False, False, False)],
)
def test_chats_are_looked_for_only_when_their_switch_allows_it_and_owlbear_is_idle(said, monkeypatch, case):
    switch, paused, idle, looked = case
    said.retro_when_idle, seen = switch, []
    monkeypatch.setattr(retro_units, "due_chats", lambda *_a, **_k: seen.append("looked") or [])
    _job(Asker(), SimpleNamespace(paused=paused, fence="", idle=idle)).tick(0.0)
    assert bool(seen) is looked


def test_an_enrolled_chat_is_judged_once_owlbear_is_idle(said, tmp_path):
    said.enrolled_chats, said.retro_when_idle = [_chat(tmp_path, "c3")], "on"
    old = (datetime.now(UTC) - timedelta(days=3)).isoformat()
    retro_store.update(lambda t: t.update(watermark=old))
    state = SimpleNamespace(paused=False, fence="", idle=False)  # a builder works
    job = _job(asker := Asker(), state)
    job.tick(0.0)
    assert _runs() == []
    state.idle = True
    job.tick(1.0)
    [run] = _runs()
    assert (run["unit"], run["trigger"], run["result"]) == ("chat:c3", "idle", "judged")
    assert asker.seen
    assert retro_store.units()["chat:c3"]["revisions"][-1]["state"] == "judged"


def test_a_late_record_whose_grade_only_run_failed_waits_for_the_button_which_grades_it(said, tmp_path):
    said.retro_after_change, projects = "on", _finished_change(tmp_path)
    job = _job(asker := Asker(), projects=projects)
    job.tick(0.0)
    late = {"id": "rec-d", "at": "2026-01-01T00:01:00+00:00", "look": "handoff", "call": "d", "cutoff": 2}
    late |= {"category": "none", "project": "p1", "change": "fix-it", "step": "build", "session": "s-build"}
    with (spotter.root() / "records-2026-01-01.jsonl").open("a") as out:
        out.write(json.dumps(late) + "\n")

    def broken(_n):
        msg = "the session broke"
        raise RuntimeError(msg)

    asker.during = broken
    job.tick(1.0)
    job.tick(2.0)
    assert [(r["mode"], r["result"].split(":")[0]) for r in _runs()] == [("judge", "judged"), ("grade-only", "stopped")]
    asker.during = None
    retro_store.request("owner", change="p1:fix-it")
    job.tick(3.0)
    assert [(r["mode"], r["trigger"], r["result"]) for r in _runs()][2:] == [("grade-only", "button", "judged")]
    assert "rec-d" in retro_store.graded()


@pytest.mark.usefixtures("said")
def test_the_button_runs_while_paused_and_switched_off_but_never_through_the_fence():
    state = SimpleNamespace(paused=True, fence="curation is running", idle=False)
    job = _job(asker := Asker(), state)
    rid = retro_store.request("owner", synthetic="verify-a")
    job.tick(0.0)
    assert ([r["id"] for r in retro_store.queued()], asker.seen, _runs()) == ([rid], [], [])
    state.fence = ""
    job.tick(1.0)
    [run] = _runs()
    assert (run["trigger"], run["result"], retro_store.queued()) == ("button", "judged", [])


@pytest.mark.usefixtures("said")
def test_drain_cancels_the_running_call_and_keeps_how_its_run_ended(monkeypatch):
    started = threading.Event()

    async def slow(_message, meter, _role, **_kw):
        share = meter.part()
        share.call(1.0)
        started.set()
        try:
            await asyncio.sleep(60)
        finally:
            share.ended(1.0, confirmed=True)

    monkeypatch.setattr(retro_job, "EVERY", 0.01)
    job, stopping = _job(slow), threading.Event()
    retro_store.request("owner", synthetic="verify-a")
    job.start(stopping, time.monotonic)
    assert started.wait(10)
    stopping.set()
    assert job.drain(10)
    [run] = _runs()
    assert (run["result"], run["spent"]) == ("stopped: OwlBear stopped", 1.0)
    assert not job.lingering()


@pytest.mark.usefixtures("said")
def test_an_unconfirmed_runtime_end_keeps_its_lease_and_ends_the_run_at_its_next_call():
    job = _job(asker := Asker(during=lambda _n: spotter_look.UNENDED.get().append("retro-session")))
    retro_store.request("owner", synthetic="large")
    job.tick(0.0)
    [run] = _runs()
    assert (run["result"], asker.seen) == ("stopped: runtime end unconfirmed", ["retro"])
    assert job.working() == [LINGERING]
    retro_store.request("owner", synthetic="verify-a")
    job.tick(1.0)
    assert (len(_runs()), len(retro_store.queued())) == (1, 1)  # no Retro call starts until Maintenance recovers it


def test_the_machine_waits_for_retros_running_run():
    now = datetime.now(UTC)
    m = Machine(HostRecord(url="http://x/", token=uuid.uuid4().hex, pid=1, started_at=now, code=codebase.CURRENT))
    try:
        m.retro.running = "syn:large"
        assert "Retro: syn:large" in m.left()
        assert "Retro: syn:large" in m.busy()
    finally:
        m.retro.running = ""
        m.stop_all()


def test_an_idle_run_waits_at_its_next_call_once_owlbear_is_busy_and_goes_on_when_idle_again(said, monkeypatch):
    said.retro_when_idle = "on"
    state = SimpleNamespace(paused=False, fence="", idle=True)
    asker = Asker(during=lambda n: n == 1 and setattr(state, "idle", False))  # a builder starts after its first call
    due = iter([[{"unit": syn.unit_id(_large()), "rev": "", "mode": "judge"}]])
    monkeypatch.setattr(retro_units, "due_chats", lambda *_a, **_k: next(due, []))

    def chat(uid, trigger, *args, **kwargs):  # the synthetic unit, as if an enrolled chat
        return Running(uid, trigger, *args, **({"provenance": "synthetic", "spec": "large"} | kwargs))

    monkeypatch.setattr(retro_job, "Running", chat)
    job = _job(asker, state)
    job.tick(0.0)
    [run] = _runs()
    assert (run["state"], run["why"], run["calls"], len(asker.seen)) == ("waiting", "OwlBear is not idle", 1, 1)

    job.tick(1.0)
    assert (retro_store.run_states()[run["id"]]["state"], len(asker.seen)) == ("waiting", 1)

    state.idle = True
    job.tick(2.0)
    run = retro_store.run_states()[run["id"]]
    assert (run["result"], run["trigger"], run["calls"]) == ("judged", "idle", 2)


# A paused run and the button, gate L3


def test_a_paused_automatic_run_waits_while_the_button_runs_and_is_taken_over_with_its_spend(said, monkeypatch):
    said.retro_after_change = "on"
    state = SimpleNamespace(paused=False, fence="", idle=False)
    asker = Asker(during=lambda n: n == 1 and setattr(state, "paused", True))  # paused after its first call
    due = iter([[{"unit": syn.unit_id(_large()), "rev": "", "mode": "judge"}]])
    monkeypatch.setattr(retro_units, "due_changes", lambda *_a, **_k: next(due, []))

    def automatic(uid, trigger, *args, **kwargs):  # the synthetic unit, as if a finished Change
        return Running(uid, trigger, *args, **({"provenance": "synthetic", "spec": "large"} | kwargs))

    monkeypatch.setattr(retro_job, "Running", automatic)
    job = _job(asker, state)
    job.tick(0.0)
    [paused] = _runs()
    assert (paused["state"], paused["why"], paused["spent"], paused["calls"]) == (
        "waiting",
        "OwlBear is paused",
        1.0,
        1,
    )

    retro_store.request("owner", synthetic="verify-a")
    job.tick(1.0)
    other = next(r for r in _runs() if r["id"] != paused["id"])
    assert (other["result"], retro_store.run_states()[paused["id"]]["state"]) == ("judged", "waiting")

    state.fence = "curation is running"
    retro_store.request("owner", synthetic="large")
    job.tick(2.0)
    assert len(retro_store.queued()) == 1
    state.fence = ""
    job.tick(3.0)
    run = retro_store.run_states()[paused["id"]]
    assert (run["result"], run["trigger"], run["spent"], run["calls"]) == ("judged", "button", 2.0, 2)
    assert (len(_runs()), state.paused) == (2, True)
    graded = retro_store.grades(synthetic=True, unit=syn.unit_id(_large()))
    assert len(graded) == len(_large()["records"])


# Pruning, gate H4


@pytest.mark.usefixtures("said")
def test_pruning_keeps_every_capture_something_rests_on_and_removes_a_judged_unreferenced_one():
    old = (datetime.now(UTC) - timedelta(days=40)).isoformat()
    for sid in ("s-find", "s-case", "s-prop", "c-two", "s-ctl"):
        retro_units.folder(sid).mkdir(parents=True)
        (retro_units.folder(sid) / "log.jsonl.gz").write_bytes(b"x")
    judged = [{"rev": "r1", "state": "judged"}]

    def unit(sid, kind="change", revisions=judged):
        return {"kind": kind, "sessions": [sid], "provenance": "real", "judged_at": old, "revisions": revisions}

    r1 = {"rev": "r1", "state": "judged", "sha256": retro_units.fingerprint("c-two")["sha256"]}
    found = {"chg:p:find": unit("s-find"), "chg:p:case": unit("s-case"), "chg:p:prop": unit("s-prop")}
    found |= {"chat:c-two": unit("c-two", "chat", [r1, {"rev": "r2", "state": "open"}]), "chg:p:ctl": unit("s-ctl")}
    retro_store.update(lambda t: t["units"].update(found))
    retro_store.add_findings(
        [{"id": "f1", "unit": "chg:p:find", "sessions": ["s-find"]}, {"id": "f2", "unit": "chg:p:prop"}]
    )
    assert props.file("k", ["f2"], kind="lesson")
    cases.place().mkdir(parents=True)
    (cases.place() / "c-1.json").write_text(json.dumps({"provenance": {"record": {"session": "s-case"}}}))

    _job(Asker()).tick(0.0)

    kept = sorted(p.name for p in retro_units.folder("s-ctl").parent.iterdir() if not p.name.startswith("."))
    assert kept == ["c-two", "s-case", "s-find", "s-prop"]
