"""Retro's runs that judge no unit (#716): a redirected proposal's redraft and a finding's follow-up."""

import contextlib
import json
import threading
import uuid
from types import SimpleNamespace

import pytest

from owlbear_delivery_next.improvement import assumptions, followups, retro_judge, spotter
from owlbear_delivery_next.improvement import proposal_apply as act
from owlbear_delivery_next.improvement import proposal_targets as targets
from owlbear_delivery_next.improvement import retro_proposals as props
from owlbear_delivery_next.improvement import retro_store as store
from owlbear_delivery_next.local_system import maintenance
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.local_system.slots import Slots
from owlbear_delivery_next.machine_host import cases_job, retro_job
from owlbear_delivery_next.machine_host.retro_inputs import where
from owlbear_delivery_next.machine_host.retro_job import RetroJob, Seams
from owlbear_delivery_next.state_store import backlog_issues, machine_settings
from owlbear_delivery_next.state_store.backlog import Backlog, BacklogError

SECRET = "ghp_" + "c" * 36
TEXT = {"title": "Check the week column", "body": "The builder said done before the week column held ISO weeks."}


class Model:
    """``retro_review.asked``: each call costs *cost* and answers the next of *answers*; every message is kept."""

    def __init__(self, *answers, cost=1.0):
        self.answers, self.cost, self.messages = list(answers), cost, []

    async def __call__(self, message, meter, _role, *, agent, seconds):
        assert (agent, seconds) == ("retro-review", 60.0)
        self.messages.append(message)
        share = meter.part()
        share.call(self.cost)
        share.ended(self.cost, confirmed=True)
        said = self.answers.pop(0)
        return said if isinstance(said, str) else json.dumps(said)


def _job(model, projects):
    slots = Slots(lambda: 1)
    owner = maintenance.Maintenance(slots, boot=lambda: 10.0, observe=lambda *_: False)
    slots.open()
    return RetroJob(slots, Seams(asked=model, projects=lambda: projects), owner)


def _record(rid):
    record = {"id": rid, "at": "2026-01-01T00:00:00+00:00", "look": "handoff", "call": "c", "category": "none"}
    record |= {"project": "p1", "change": "fix", "step": "build", "session": "s-1"}
    (spotter.root() / "records-2026-01-01.jsonl").write_text(json.dumps(record) + "\n")


@pytest.fixture
def said(monkeypatch):
    found = SimpleNamespace(retro_after_change="off", retro_when_idle="off", enrolled_chats=[], limit=125.0)
    monkeypatch.setattr(machine_settings, "current", lambda: found)
    monkeypatch.setattr(cases_job, "limits", lambda: {"retro": found.limit})
    monkeypatch.setattr(retro_job, "session", lambda _agent: (None, 60.0))
    return found


@pytest.fixture
def world(tmp_path, monkeypatch):
    """A real project and native historical findings, without publication setup."""
    clone = tmp_path / "alpha"
    clone.mkdir()
    projects = {"p1": (SimpleNamespace(name="alpha-folder", root=clone), clone)}
    places = {"p1": targets.Place("alpha-folder", clone)}
    folders = []

    def unexpected(folder):
        folders.append(folder)
        pytest.fail("this refusal or redraft must not reach Backlog")

    monkeypatch.setattr(followups, "backlog", unexpected)
    store.add_findings(
        [
            _finding("rf-1", "chg:p1:fix", what=f"pushed with {SECRET}, mailed a@b.example from /Users/someone/x"),
            _finding("rf-2", "chg:p1:fix"),
            _finding("rf-s", "syn:scout-a", provenance="synthetic"),
        ]
    )
    return SimpleNamespace(projects=projects, places=places, backlog_folders=folders)


@pytest.fixture
def native_backlog(world, shared_repo, github, monkeypatch):
    """The actual private issue store; only the provider transport is replaced."""
    assert github.visibility == "private"
    shared = DataRepo(shared_repo[0])

    def backlog(folder):
        world.backlog_folders.append(folder)
        return Backlog(shared, folder)

    monkeypatch.setattr(followups, "backlog", backlog)
    return Backlog(shared, "alpha-folder")


def _finding(fid, unit, provenance="real", what="it said done early"):
    change = unit.split(":", 1)[1] if unit.startswith("chg:") else ""
    return {"id": fid, "unit": unit, "change": change, "provenance": provenance, "what": what, "mechanism": "early"}


def _redirected(kind="agent-change", target="agent:exporter", findings=("rf-2",), provenance="real", **fields):
    pid = props.file(props.open_key(provenance, kind, target), findings, kind=kind, target=target,
                     provenance=provenance, assumptions=["retro-segments"], **fields)  # fmt: skip
    props.reviewed(pid, props.folded()[pid]["evidence"], {"verdict": "survive", "why": "holds", "publishable": TEXT})
    props.transition(pid, "redirected", "owner", direction="aim it at the reviewer, not the builder")
    store.request("owner", redraft=pid)
    return pid


def _redraft(verdict="survive", **more):
    return {"cause": "review", "target": "agent:reviewer", "mechanism": "missed the week check", "assumptions": [],
            "verdict": verdict, "why": "the findings carry it", "risks": [], "publishable": TEXT} | more  # fmt: skip


def _runs():
    return list(store.run_states().values())


# Redrafts


@pytest.mark.usefixtures("said")
def test_redraft_journey(world, monkeypatch):
    other = props.file(props.open_key("real", "lesson", "agent:builder"), ["rf-1"], kind="lesson", provenance="real")
    pid = _redirected()

    job = _job(model := Model("not json", _redraft()), world.projects)
    job.tick(0.0)
    assert (_runs()[0]["result"], props.folded()[pid]["redraft"]) == (
        "stopped: an answer was not valid against its schema",
        "",
    )
    assert len(props.folded()) == 2
    assert all(p["applied"] == [] for p in props.folded().values())
    reviewed = props.reviewed

    def stopped(*_a, **_k):
        msg = "the host stopped"
        raise RuntimeError(msg)

    store.request("owner", redraft=pid)
    monkeypatch.setattr(props, "reviewed", stopped)
    job.tick(1.0)
    child = props.folded()[pid]["redraft"]
    assert props.folded()[child]["state"] == "drafted"
    second = _runs()[1]
    assert (second["unit"], second["mode"], second["calls"], second["spent"]) == (f"proposal:{pid}", "redraft", 1, 1.0)
    assert second["result"] == "failed: RuntimeError: the host stopped"
    kept = store.saved(store.lines("batches.jsonl")[-1]["key"])
    assert kept["answer"] == _redraft()
    assert props.folded()[child]["applied"] == []
    sent = json.loads(model.messages[1].split("```json\n")[-1].rsplit("\n```", 1)[0])
    assert sent["direction"] == "aim it at the reviewer, not the builder"
    assert (sent["provenance"], sent["assumptions"], sent["prior_review"]["why"]) == (
        "real",
        ["retro-segments"],
        "holds",
    )
    monkeypatch.setattr(props, "reviewed", reviewed)
    store.request("owner", redraft=pid)
    job.tick(2.0)
    assert props.folded()[pid]["redraft"] == child
    new = props.folded()[child]
    assert (new["state"], new["prior"], new["target"], new["findings"]) == ("waiting", pid, "agent:reviewer", ["rf-2"])
    assert (new["applied"], props.folded()[other]["state"]) == ([], "drafted")  # nothing published, nothing else paid
    store.request("owner", redraft=pid)
    job.tick(3.0)
    assert (props.folded()[pid]["redraft"], [r["calls"] for r in _runs()]) == (child, [1, 1, 0, 0])
    assert [r["result"] for r in _runs()][2:] == ["judged", "judged"]
    assert len(model.messages) == 2
    assert sum(p.get("redraft_of") == pid for p in props.folded().values()) == 1
    assert world.backlog_folders == []


@pytest.mark.usefixtures("said")
def test_a_redraft_retro_review_rejects_is_rejected_with_its_reason(world):
    pid = _redirected()

    _job(Model(_redraft("reject", why="the findings do not share it", publishable={})), world.projects).tick(0)

    new = props.folded()[props.folded()[pid]["redraft"]]
    assert (new["state"], new["why"]) == ("rejected", "the findings do not share it")


@pytest.mark.parametrize("mode", ["redraft", "followup"])
def test_credit_cut_publishes_nothing(said, world, request, mode):
    said.limit = 1.0
    pid = _redirected() if mode == "redraft" else ""
    native = request.getfixturevalue("native_backlog") if mode == "followup" else None
    if mode == "followup":
        followups.request("rf-2", "owner", world.places, followups.backlog)

    _job(Model(_redraft() if mode == "redraft" else TEXT), world.projects).tick(0.0)

    [run] = _runs()
    assert (run["result"], run["spent"]) == ("stopped: an answer was cut off at the credit limit", 1.0)
    assert store.queued() == []
    if native is not None:
        assert native.entries() == []
    else:
        assert world.backlog_folders == []
    if pid:
        assert props.folded()[pid]["redraft"] == ""
    assert all(p["applied"] == [] for p in props.folded().values())


@pytest.mark.usefixtures("said")
def test_a_queued_synthetic_spotter_case_redraft_is_refused_without_a_call(world):
    pid = _redirected("spotter-case", "look:handoff", ("rf-s",), "synthetic", record="syn-scout-a-1", call="none")
    model = Model(_redraft(call="hand-off-fitness"))

    _job(model, world.projects).tick(0.0)

    [run] = _runs()
    assert (run["result"], model.messages, props.folded()[pid]["redraft"]) == (
        f"refused: {store.SYNTHETIC_RETIRED}", [], "")  # fmt: skip
    assert (world.backlog_folders, store.queued()) == ([], [])


def test_a_lessons_redraft_body_fits_a_memory_refs_included():
    pid = props.file("real|lesson|builder", ["rf-2"], kind="lesson", provenance="real")
    new = props.folded()[pid]
    body = retro_judge.settled(new, _redraft(publishable={"title": "t", "body": "w" * 1_400}))["publishable"]["body"]
    assert len(body) <= targets.MEMORY
    assert body.endswith(f"Refs: {new['id']}, rf-2")
    assert len(retro_judge.settled({"id": "x", "kind": "agent-change", "findings": []}, _redraft(
        publishable={"title": "t", "body": "w" * 1_400}))["publishable"]["body"]) > targets.MEMORY  # fmt: skip


# Follow-ups


@pytest.mark.usefixtures("said")
def test_followup_journey(world, native_backlog, github):
    first = followups.request("rf-1", "owner", world.places, followups.backlog)
    assert set(first) == {"queued"}

    _job(model := Model(TEXT), world.projects).tick(0.0)

    assert SECRET not in model.messages[0]
    [entry] = native_backlog.entries()
    assert (entry.origin, entry.source, entry.evidence) == ("alpha-folder", "retro", ["followup:rf-1"])
    [issue] = github.issues.values()
    assert backlog_issues.fields(issue)["origin"] == "alpha-folder"
    assert (entry.title, entry.text) == (TEXT["title"], f"{TEXT['body']}\n\nRefs: rf-1")
    assert followups.request("rf-1", "owner", world.places, followups.backlog)["entry"]["id"] == entry.id
    assert len(native_backlog.entries()) == 1
    assert [r["calls"] for r in _runs()] == [1]
    assert len([c for c in github.calls if c[:2] == ("POST", "repos/acme/owlbear-data/issues")]) == 1
    assert set(world.backlog_folders) == {"alpha-folder"}


@pytest.mark.usefixtures("said")
def test_a_spotter_records_follow_up_lands_in_its_project_and_an_unsafe_minimised_text_is_refused(
    world, native_backlog
):
    rid = uuid.uuid4().hex[:12]  # as the Spotter names its records
    _record(rid)
    followups.request(rid, "owner", world.places, followups.backlog)
    unsafe = {"title": "seen", "body": f"from /Users/someone/x by a@b.example with {SECRET}"}

    _job(Model(unsafe), world.projects).tick(0.0)

    assert native_backlog.entries() == []
    assert _runs()[0]["result"] == "stopped: an answer was not valid against its schema"  # kept as an attempt only
    followups.request(rid, "owner", world.places, followups.backlog)
    _job(Model(TEXT), world.projects).tick(1.0)
    [entry] = native_backlog.entries()
    assert (entry.origin, entry.source, entry.evidence) == ("alpha-folder", "spotter", [f"followup:{rid}"])


@pytest.mark.usefixtures("said")
def test_a_follow_up_a_reviewed_proposal_already_worded_is_saved_at_once_unless_unsafe(world, native_backlog):
    for fid, text in (("rf-2", TEXT), ("rf-1", {"title": "t", "body": f"mail a@b.example {SECRET}"})):
        pid = props.file(props.open_key("real", "agent-change", fid), [fid], kind="agent-change", provenance="real")
        props.reviewed(pid, props.folded()[pid]["evidence"], {"verdict": "survive", "publishable": text})

    saved = followups.request("rf-2", "owner", world.places, followups.backlog)

    assert saved["entry"]["title"] == TEXT["title"]
    with pytest.raises(store.RetroError, match="holds a credential, an email address"):
        followups.request("rf-1", "owner", world.places, followups.backlog)
    assert (len(native_backlog.entries()), store.queued(), _runs()) == (1, [], [])


def test_the_owners_writes_count_in_what_a_stop_or_an_update_waits_for(world):
    job = _job(Model(TEXT), world.projects)

    with act.admitted("applying proposal rp-1", contextlib.nullcontext(), lambda: None):
        assert job.working() == ["Improvement: applying proposal rp-1"]

    assert job.working() == []


def test_two_savers_of_one_follow_up_with_different_text_make_one_entry(world, native_backlog, github, monkeypatch):
    both = threading.Barrier(2, timeout=1)  # each saver reads the backlog before either adds, unless one waits
    shown = Backlog.read

    def read(self, *, fresh=False):
        found = shown(self, fresh=fresh)
        with contextlib.suppress(threading.BrokenBarrierError):
            both.wait()
        return found

    monkeypatch.setattr(Backlog, "read", read)
    subj = followups.subject("rf-2", world.places)
    errors = []

    def save(title):
        try:
            followups.save(subj, {"title": title, "body": "b"}, followups.backlog)
        except Exception as exc:
            errors.append(exc)
            raise

    savers = [threading.Thread(target=save, args=(t,)) for t in ("Minimised by a run", "Reviewed proposal text")]
    for saver in savers:
        saver.start()
    for saver in savers:
        saver.join(10)

    assert not any(saver.is_alive() for saver in savers)
    assert errors == []
    monkeypatch.setattr(Backlog, "read", shown)
    assert [e.evidence for e in native_backlog.entries()] == [["followup:rf-2"]]
    assert len([c for c in github.calls if c[:2] == ("POST", "repos/acme/owlbear-data/issues")]) == 1


def test_a_follow_up_of_a_finding_a_reset_retired_is_refused_with_nothing_saved_or_queued(world):
    store.add_findings([_finding("rf-r", "chg:p1:fix") | {"assumptions": [assumptions.RETRO_SEGMENTS]}])
    pid = props.file(props.open_key("real", "agent-change", "rf-r"), ["rf-r"], kind="agent-change", provenance="real",
                     assumptions=[assumptions.RETRO_SEGMENTS])  # fmt: skip
    props.reviewed(pid, props.folded()[pid]["evidence"], {"verdict": "survive", "publishable": TEXT})
    assumptions.reset()
    before = {p.name: p.read_bytes() for p in store.place().iterdir() if p.is_file()}

    with pytest.raises(store.RetroError) as exc:
        followups.request("rf-r", "owner", world.places, followups.backlog)
    assert str(exc.value) == "finding rf-r is hidden: it rests on a retired assumption, so nothing follows it up"
    assert (world.backlog_folders, store.queued(), followups.reusable("rf-r")) == ([], [], None)
    assert {p.name: p.read_bytes() for p in store.place().iterdir() if p.is_file()} == before


def test_historical_followup_is_refused(world):
    before = {p.name: p.read_bytes() for p in store.place().iterdir() if p.is_file()}
    with pytest.raises(store.RetroError) as exc:
        followups.request("rf-s", "owner", world.places, followups.backlog)
    assert str(exc.value) == store.SYNTHETIC_RETIRED
    assert (world.backlog_folders, store.queued(), _runs()) == ([], [], [])
    assert {p.name: p.read_bytes() for p in store.place().iterdir() if p.is_file()} == before


@pytest.mark.usefixtures("said")
@pytest.mark.parametrize("site", ["its backlog", "its subject"])
def test_a_follow_up_whose_backlog_or_subject_cannot_be_reached_keeps_its_whole_reason(
    world, native_backlog, monkeypatch, whole_error, site
):
    def unreachable(*_args, **_kwargs):
        exc = BacklogError(502, whole_error) if site == "its backlog" else store.RetroError(whole_error)
        exc.add_note("GitHub answered while the shared repository moved")
        raise exc

    monkeypatch.setattr(Backlog, "add", unreachable)
    followups.request("rf-2", "owner", world.places, followups.backlog)
    if site == "its subject":  # asked for, then its subject became unreadable before the run
        monkeypatch.setattr(followups, "subject", unreachable)
    _job(Model(TEXT), world.projects).tick(0.0)
    [run] = _runs()
    whole = f"{whole_error}\nGitHub answered while the shared repository moved"
    said = (f"stopped: the backlog could not be reached (BacklogError: {whole})" if site == "its backlog" else
            f"refused: RetroError: {whole}")  # fmt: skip
    assert (run["result"], native_backlog.entries()) == (said, [])


def test_a_follow_ups_spend_counts_for_its_change_and_an_unscoped_ones_machine_wide(world):
    store.add_findings([_finding("rf-c", "chat:s-1")])
    pid = props.file(props.open_key("real", "lesson", "x"), ["rf-1", "rf-2"], kind="lesson", provenance="real")

    assert (where("finding:rf-1", world.projects).project, where("finding:rf-1", world.projects).change) == (
        "alpha-folder", "fix")  # fmt: skip
    assert where(f"proposal:{pid}", world.projects).change == "fix"
    assert where("finding:rf-c", world.projects).project == ""
    mixed = props.file(props.open_key("real", "lesson", "y"), ["rf-1", "rf-c"], kind="lesson", provenance="real")
    assert where(f"proposal:{mixed}", world.projects) == where("finding:rf-c", world.projects)  # no Change shared
    assert where("finding:unknown", world.projects).project == ""
