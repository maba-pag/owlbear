"""Retro's runs that judge no unit (#716): a redirected proposal's redraft and a finding's follow-up."""

import contextlib
import json
import uuid
from types import SimpleNamespace

import pytest

from owlbear_delivery_next.improvement import assumptions, cases, followups, retro_judge, spotter
from owlbear_delivery_next.improvement import proposal_apply as act
from owlbear_delivery_next.improvement import proposal_targets as targets
from owlbear_delivery_next.improvement import retro_proposals as props
from owlbear_delivery_next.improvement import retro_store as store
from owlbear_delivery_next.local_system import maintenance
from owlbear_delivery_next.local_system.slots import Slots
from owlbear_delivery_next.machine_host import cases_job, retro_job
from owlbear_delivery_next.machine_host.retro_inputs import where
from owlbear_delivery_next.machine_host.retro_job import RetroJob, Seams
from owlbear_delivery_next.state_store import machine_settings

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


class FakeBacklog:
    """One backlog view of *folder* over the shared *entries*."""

    def __init__(self, folder, entries):
        self.folder, self.entries, self.repository = folder, entries, "o/shared"

    def read(self, *, fresh=False):
        assert fresh
        return {e.id: e for e in self.entries}, []

    def add(self, title, text, source, evidence=()):
        entry = SimpleNamespace(id=str(len(self.entries) + 1), title=title, text=text, source=source,
                                evidence=list(evidence), folder=self.folder)  # fmt: skip
        self.entries.append(entry)
        return entry, True


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
    """Projects p1 and the sandbox, registered; their backlogs; findings of p1's Change fix and of a synthetic unit."""
    projects, places = {}, {}
    for pid, name in (("p1", "alpha"), ("ps", targets.SANDBOX)):
        (tmp_path / name).mkdir()
        projects[pid] = (SimpleNamespace(name=f"{name}-folder", root=tmp_path / name), tmp_path / name)
        places[pid] = targets.Place(f"{name}-folder", tmp_path / name)
    entries = []
    monkeypatch.setattr(followups, "backlog", lambda folder: FakeBacklog(folder, entries))
    store.add_findings(
        [
            _finding("rf-1", "chg:p1:fix", what=f"pushed with {SECRET}, mailed a@b.example from /Users/someone/x"),
            _finding("rf-2", "chg:p1:fix"),
            _finding("rf-s", "syn:scout-a", provenance="synthetic"),
        ]
    )
    return SimpleNamespace(projects=projects, places=places, entries=entries, shared=tmp_path / "shared")


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
def test_a_redirect_is_redrafted_in_one_paid_call_and_comes_back_waiting_for_the_owner(world):
    other = props.file(props.open_key("real", "lesson", "agent:builder"), ["rf-1"], kind="lesson", provenance="real")
    pid = _redirected()

    _job(model := Model(_redraft()), world.projects).tick(0.0)

    [run] = _runs()
    assert (run["unit"], run["mode"], run["result"], run["calls"]) == (f"proposal:{pid}", "redraft", "judged", 1)
    sent = json.loads(model.messages[0].split("```json\n")[-1].rsplit("\n```", 1)[0])
    assert sent["direction"] == "aim it at the reviewer, not the builder"
    assert (sent["provenance"], sent["assumptions"], sent["prior_review"]["why"]) == (
        "real",
        ["retro-segments"],
        "holds",
    )
    new = props.folded()[props.folded()[pid]["redraft"]]
    assert (new["state"], new["prior"], new["target"], new["findings"]) == ("waiting", pid, "agent:reviewer", ["rf-2"])
    assert (new["applied"], props.folded()[other]["state"]) == ([], "drafted")  # nothing published, nothing else paid


@pytest.mark.usefixtures("said")
def test_a_redraft_retro_review_rejects_is_rejected_with_its_reason(world):
    pid = _redirected()

    _job(Model(_redraft("reject", why="the findings do not share it", publishable={})), world.projects).tick(0)

    new = props.folded()[props.folded()[pid]["redraft"]]
    assert (new["state"], new["why"]) == ("rejected", "the findings do not share it")


@pytest.mark.usefixtures("said")
def test_a_redraft_filed_but_not_reviewed_is_reviewed_from_its_kept_answer_without_a_new_call(world, monkeypatch):
    pid = _redirected()
    reviewed, model = props.reviewed, Model(_redraft())

    def stopped(*_a, **_k):
        msg = "the host stopped"
        raise RuntimeError(msg)

    monkeypatch.setattr(props, "reviewed", stopped)
    job = _job(model, world.projects)
    job.tick(0.0)
    child = props.folded()[pid]["redraft"]
    assert props.folded()[child]["state"] == "drafted"

    monkeypatch.setattr(props, "reviewed", reviewed)
    store.request("owner", redraft=pid)
    job.tick(1.0)
    assert (props.folded()[pid]["redraft"], props.folded()[child]["state"]) == (child, "waiting")
    assert len(model.messages) == 1


@pytest.mark.usefixtures("said")
def test_an_unusable_redraft_stops_files_nothing_and_redraft_again_succeeds_once(world):
    pid = _redirected()
    job = _job(Model("not json", _redraft(), _redraft()), world.projects)

    job.tick(0.0)
    assert (_runs()[0]["result"], props.folded()[pid]["redraft"]) == (
        "stopped: an answer was not valid against its schema",
        "",
    )

    store.request("owner", redraft=pid)
    job.tick(1.0)
    first = props.folded()[pid]["redraft"]
    store.request("owner", redraft=pid)
    job.tick(2.0)
    assert (props.folded()[pid]["redraft"], [r["calls"] for r in _runs()]) == (first, [1, 1, 0])
    assert sum(p.get("redraft_of") == pid for p in props.folded().values()) == 1


def test_a_redraft_cut_at_its_limit_files_nothing_and_keeps_its_spend(said, world):
    said.limit = 1.0
    pid = _redirected()

    _job(Model(_redraft()), world.projects).tick(0.0)

    [run] = _runs()
    assert (run["result"], run["spent"], props.folded()[pid]["redraft"]) == (
        "stopped: an answer was cut off at the credit limit", 1.0, "")  # fmt: skip


@pytest.mark.usefixtures("said")
def test_a_synthetic_spotter_case_redraft_stays_synthetic_keeps_its_record_and_accepted_makes_its_case(world):
    pid = _redirected("spotter-case", "look:handoff", ("rf-s",), "synthetic", record="syn-scout-a-1", call="none")

    _job(Model(_redraft(call="hand-off-fitness")), world.projects).tick(0.0)

    new = props.folded()[props.folded()[pid]["redraft"]]
    assert (new["provenance"], new["kind"], new["record"], new["call"]) == (
        "synthetic", "spotter-case", "syn-scout-a-1", "hand-off-fitness")  # fmt: skip
    dest = act.destination(new, world.places, world.shared, targets.units_of())
    act.decide(new["id"], "accepted", props.token(new, dest), "owner", places=world.places, shared_root=world.shared)
    checks = []
    seams = act.Seams(lambda _f: None, None, None, act.intake, lambda cid: checks.append(cid) or "r-1")
    done = act.apply(new["id"], seams)
    assert done["apply_state"] == "done", done["failures"]
    assert cases.fact(checks[0])["provenance"]["record"]["id"] == "syn-scout-a-1"


@pytest.mark.usefixtures("said")
def test_a_lessons_redraft_body_fits_a_memory_refs_included(world):
    pid = _redirected("lesson", "agent:owlbear-builder")

    _job(Model(_redraft(publishable={"title": "t", "body": "w" * 1_400})), world.projects).tick(0.0)

    new = props.folded()[props.folded()[pid]["redraft"]]
    body = new["publishable"]["body"]
    assert len(body) <= targets.MEMORY
    assert body.endswith(f"Refs: {new['id']}, rf-2")
    assert len(retro_judge.settled({"id": "x", "kind": "agent-change", "findings": []}, _redraft(
        publishable={"title": "t", "body": "w" * 1_400}))["publishable"]["body"]) > targets.MEMORY  # fmt: skip


# Follow-ups


@pytest.mark.usefixtures("said")
def test_a_follow_up_is_minimised_masked_saved_in_its_changes_project_once_and_never_twice(world):
    first = followups.request("rf-1", "owner", world.places, followups.backlog)
    assert set(first) == {"queued"}

    _job(model := Model(TEXT), world.projects).tick(0.0)

    assert SECRET not in model.messages[0]
    [entry] = world.entries
    assert (entry.folder, entry.source, entry.evidence) == ("alpha-folder", "retro", ["followup:rf-1"])
    assert (entry.title, entry.text) == (TEXT["title"], f"{TEXT['body']}\n\nRefs: rf-1")
    assert followups.request("rf-1", "owner", world.places, followups.backlog)["entry"]["id"] == entry.id
    assert len(world.entries) == 1


@pytest.mark.usefixtures("said")
def test_a_spotter_records_follow_up_lands_in_its_project_and_an_unsafe_minimised_text_is_refused(world):
    rid = uuid.uuid4().hex[:12]  # as the Spotter names its records
    _record(rid)
    followups.request(rid, "owner", world.places, followups.backlog)
    unsafe = {"title": "seen", "body": f"from /Users/someone/x by a@b.example with {SECRET}"}

    _job(Model(unsafe), world.projects).tick(0.0)

    assert world.entries == []
    assert _runs()[0]["result"] == "stopped: an answer was not valid against its schema"  # kept as an attempt only
    followups.request(rid, "owner", world.places, followups.backlog)
    _job(Model(TEXT), world.projects).tick(1.0)
    [entry] = world.entries
    assert (entry.folder, entry.source, entry.evidence) == ("alpha-folder", "spotter", [f"followup:{rid}"])


@pytest.mark.usefixtures("said")
def test_a_follow_up_a_reviewed_proposal_already_worded_is_saved_at_once_unless_unsafe(world):
    for fid, text in (("rf-2", TEXT), ("rf-1", {"title": "t", "body": f"mail a@b.example {SECRET}"})):
        pid = props.file(props.open_key("real", "agent-change", fid), [fid], kind="agent-change", provenance="real")
        props.reviewed(pid, props.folded()[pid]["evidence"], {"verdict": "survive", "publishable": text})

    saved = followups.request("rf-2", "owner", world.places, followups.backlog)

    assert saved["entry"]["title"] == TEXT["title"]
    with pytest.raises(store.RetroError, match="holds a credential, an email address"):
        followups.request("rf-1", "owner", world.places, followups.backlog)
    assert (len(world.entries), store.queued(), _runs()) == (1, [], [])


def test_the_owners_writes_count_in_what_a_stop_or_an_update_waits_for(world):
    job = _job(Model(TEXT), world.projects)

    with act.admitted("applying proposal rp-1", contextlib.nullcontext(), lambda: None):
        assert job.working() == ["Improvement: applying proposal rp-1"]

    assert job.working() == []


def test_a_follow_up_of_a_finding_a_reset_retired_is_refused_with_nothing_saved_or_queued(world):
    store.add_findings([_finding("rf-r", "chg:p1:fix") | {"assumptions": [assumptions.RETRO_SEGMENTS]}])
    pid = props.file(props.open_key("real", "agent-change", "rf-r"), ["rf-r"], kind="agent-change", provenance="real",
                     assumptions=[assumptions.RETRO_SEGMENTS])  # fmt: skip
    props.reviewed(pid, props.folded()[pid]["evidence"], {"verdict": "survive", "publishable": TEXT})
    assumptions.reset()

    with pytest.raises(store.RetroError, match="rests on a retired assumption"):
        followups.request("rf-r", "owner", world.places, followups.backlog)
    assert (world.entries, store.queued(), followups.reusable("rf-r")) == ([], [], None)


def test_a_follow_up_cut_at_its_limit_saves_nothing_and_a_synthetic_one_goes_only_to_the_sandbox(said, world):
    said.limit = 1.0
    followups.request("rf-2", "owner", world.places, followups.backlog)
    _job(Model(TEXT), world.projects).tick(0.0)
    [run] = _runs()
    assert (run["result"], run["spent"], world.entries) == (
        "stopped: an answer was cut off at the credit limit",
        1.0,
        [],
    )

    said.limit = 125.0
    followups.request("rf-s", "owner", world.places, followups.backlog)
    _job(Model(TEXT), world.projects).tick(1.0)
    assert [(e.folder, e.evidence) for e in world.entries] == [(f"{targets.SANDBOX}-folder", ["followup:rf-s"])]
    assert world.entries[0].title.startswith("[synthetic] ")  # never the same title as a real entry
    with pytest.raises(store.RetroError, match="only to the sandbox"):
        followups.subject("rf-s", {"p1": world.places["p1"]})


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
