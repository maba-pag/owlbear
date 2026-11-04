"""Acting on an accepted Retro proposal (#716): each artefact made once, from what was accepted, and nothing unsafe."""

import dataclasses
import gzip
import json
import subprocess
from types import SimpleNamespace

import pytest
from owlbear_memory.engine import MemoryEngine
from owlbear_memory.models import MemoryState

from owlbear_delivery_next.commands import cli
from owlbear_delivery_next.github.owlbear_issues import OwlbearIssues
from owlbear_delivery_next.improvement import (
    assumptions,
    case_edits,
    case_intake,
    case_replay,
    cases,
    improvement_view,
    spotter,
)
from owlbear_delivery_next.improvement import proposal_apply as act
from owlbear_delivery_next.improvement import proposal_targets as targets
from owlbear_delivery_next.improvement import retro_proposals as props
from owlbear_delivery_next.improvement import retro_store as store
from owlbear_delivery_next.state_store import backlog
from owlbear_delivery_next.state_store.backlog import BacklogError

UNITS = {"f-1": "chg:p1:fix", "f-2": "chg:p2:fix", "f-3": "syn:scout-a", "f-4": "chg:p1:other"}
TEXT = {
    "title": "Check the export's week column",
    "body": "The builder said done before the week column held ISO weeks.",
}


class FakeGitHub:
    """The issues of one repository behind ``gh api``; every payload sent is kept."""

    def __init__(self):
        self.issues, self.sent, self.close_fails = [{"number": 1, "pull_request": {}, "body": "x"}], [], 0

    def __call__(self, argv, data, _timeout, _cwd, _env):
        method, endpoint = argv[argv.index("--method") + 1], next(a for a in argv if a.startswith("repos/"))
        body = json.loads(data) if data else None
        self.sent.append(body)
        if method == "GET":
            return self._done(self.issues[::-1] if "page=1" in endpoint else [])
        if method == "POST":
            n = len(self.issues) + 1
            self.issues.append(body | {"number": n, "html_url": f"https://github.com/o/r/issues/{n}", "state": "open"})
            return self._done(self.issues[-1])
        if self.close_fails:
            self.close_fails -= 1
            return subprocess.CompletedProcess((), 1, b"", b"HTTP 502: bad gateway (token ghp_" + b"a" * 36 + b")")
        issue = next(i for i in self.issues if endpoint.endswith(f"/issues/{i['number']}"))
        issue["state"] = "closed"
        return self._done(issue)

    @staticmethod
    def _done(value):
        return subprocess.CompletedProcess((), 0, json.dumps(value).encode(), b"")


class FakeBacklog:
    def __init__(self, folder, entries):
        self.folder, self.entries, self.repository = folder, entries, "o/shared"

    def read(self, *, fresh=False):
        assert fresh
        return {e.id: e for e in self.entries}, []

    def add(self, title, text, source, evidence=()):
        entry = SimpleNamespace(
            id=str(len(self.entries) + 1), title=title, text=text, source=source, evidence=list(evidence)
        )
        entry.folder = self.folder
        self.entries.append(entry)
        return entry, True


@pytest.fixture
def world(tmp_path, monkeypatch):
    monkeypatch.setattr(targets, "units_of", lambda: UNITS)
    places = {}
    for pid, name in (("p1", "alpha"), ("p2", "beta"), ("ps", "example")):
        (tmp_path / name).mkdir()
        places[pid] = targets.Place(folder=f"{name}-folder", clone=tmp_path / name)
    gh, entries, checks = FakeGitHub(), [], []
    seams = act.Seams(
        backlog=lambda folder: FakeBacklog(folder, entries),
        memory=MemoryEngine,
        issues=lambda: OwlbearIssues("o/r", tmp_path, runner=gh),
        case=act.intake,
        check=lambda cid: checks.append(cid) or f"r-{len(checks)}",
    )
    return SimpleNamespace(
        places=places, shared=tmp_path / "shared", gh=gh, entries=entries, checks=checks, seams=seams
    )


def _waiting(kind, target, findings, *, provenance="real", text=TEXT, **fields):
    pid = props.file(
        props.open_key(provenance, kind, target), findings, kind=kind, target=target, provenance=provenance, **fields
    )
    props.reviewed(pid, props.folded()[pid]["evidence"], {"verdict": "survive", "why": "holds", "publishable": text})
    return pid


def _seen(pid, w):
    snap = props.folded()[pid]
    return props.token(snap, act.destination(snap, w.places, w.shared, UNITS))


def _accept(pid, w):
    act.decide(pid, "accepted", _seen(pid, w), "owner", places=w.places, shared_root=w.shared)
    return act.apply(pid, w.seams)


def _record(rid):
    record = {"id": rid, "at": "2026-01-01T00:00:00+00:00", "look": "handoff", "call": "c", "category": "none"}
    record |= {"project": "p1", "change": "fix", "step": "build", "session": "s-1"}
    with (spotter.root() / "records-2026-01-01.jsonl").open("a") as out:
        out.write(json.dumps(record) + "\n")
    (spotter.root() / "cards" / f"{rid}.json.gz").write_bytes(gzip.compress(b'{"moment": {}}'))


def test_a_backlog_entry_lands_in_the_project_its_change_unit_names_once(world):
    agents = world.places["p2"].clone / ".github" / "agents"
    agents.mkdir(parents=True)
    (agents / "exporter.agent.md").write_text("exports")
    (world.places["p1"].clone / ".github").symlink_to(world.places["p2"].clone / ".github")  # same files, other id
    pid = _waiting("agent-change", "agent:exporter", ["f-2"])

    done = _accept(pid, world)

    assert done["apply_state"] == "done", done["failures"]
    (entry,) = world.entries
    assert (entry.folder, entry.title, entry.source) == ("beta-folder", TEXT["title"], "retro")
    assert entry.evidence == ["f-2", f"retro-proposal:{pid}"]  # last: the backlog keeps an entry's newest refs
    assert act.apply(pid, world.seams)["applied"] == done["applied"]
    assert len(world.entries) == 1


def test_a_historical_synthetic_proposal_cannot_be_redirected_or_applied(world):
    pid = _waiting("agent-change", "agent:exporter", ["f-3"], provenance="synthetic")
    with pytest.raises(store.RetroError, match=r"synthetic Retro.*retired"):
        act.decide(pid, "redirected", _seen(pid, world), "owner", places=world.places, shared_root=world.shared,
                   direction="change it")  # fmt: skip

    snapshot = {"destination": {"kind": "backlog", "folder": "alpha-folder"},
                "publishable": TEXT, "findings": ["f-3"], "provenance": "synthetic"}  # fmt: skip
    props.transition(pid, "accepted", "owner", snapshot=snapshot)
    with pytest.raises(store.RetroError, match=r"synthetic Retro.*retired"):
        act.apply(pid, world.seams)
    assert world.entries == []


def test_a_synthetic_proposal_remains_visible_but_cannot_be_accepted(world):
    pid = _waiting("agent-change", "agent:exporter", ["f-3"], provenance="synthetic")
    [shown] = improvement_view.proposals({}, world.shared)
    assert shown["id"] == pid
    with pytest.raises(store.RetroError, match=r"synthetic Retro.*retired"):
        act.decide(pid, "accepted", _seen(pid, world), "owner", places=world.places, shared_root=world.shared)
    assert world.entries == []


def test_a_lesson_is_a_pending_memory_in_its_projects_folder_scoped_to_its_agent(world):
    pid = _waiting("lesson", "agent:owlbear-builder", ["f-1"])

    done = _accept(pid, world)

    assert done["apply_state"] == "done", done["failures"]
    folder = world.shared / "alpha-folder" / "memory"
    (memory,) = MemoryEngine(folder).get_entries()
    assert (memory.title, memory.content, memory.state) == (TEXT["title"], TEXT["body"], MemoryState.PENDING)
    assert (memory.source_agent, memory.scope_agents, memory.recommended) == ("retro", ["builder"], "project")
    assert done["applied"][0]["artefact"] | {"ref": ""} == {
        "kind": "memory",
        "where": str(folder),
        "ref": "",
        "link": "",
    }


def test_an_owlbear_change_is_one_issue_in_its_repository_carrying_the_marker(world):
    pid = _waiting("delivery-change", "delivery:hand-off", ["f-1"])

    done = _accept(pid, world)
    act.apply(pid, world.seams)

    made = [i for i in world.gh.issues if "pull_request" not in i]
    assert [(i["title"], i["state"]) for i in made] == [(TEXT["title"], "open")]
    assert f"<!-- retro-proposal:{pid} -->" in made[0]["body"]
    assert done["applied"][0]["artefact"]["link"] == "https://github.com/o/r/issues/2"


def test_an_issue_search_that_reads_every_page_without_the_marker_makes_none(world, tmp_path):
    asked = []

    def full(argv, _data, _timeout, _cwd, _env):  # every page is full and none carries the marker
        asked.append(argv[argv.index("--method") + 1])
        page = [{"number": n, "body": "other", "html_url": "u", "state": "open"} for n in range(100)]
        return subprocess.CompletedProcess((), 0, json.dumps(page).encode(), b"")

    pid = _waiting("delivery-change", "delivery:hand-off", ["f-1"])
    world.seams = dataclasses.replace(world.seams, issues=lambda: OwlbearIssues("o/r", tmp_path, runner=full))
    _accept(pid, world)

    snap = props.folded()[pid]
    assert (snap["apply_state"], asked) == ("failed", ["GET"] * 10)  # unsure the issue is absent: none is made
    assert "find_issue" in snap["failures"][0]["error"]


def test_a_failure_longer_than_any_cut_is_kept_whole_and_masked(world, whole_error):
    token = "ghp_" + "a" * 36

    class Unreachable(FakeBacklog):
        def read(self, *, fresh=False):  # noqa: ARG002 - the backlog's signature
            raise BacklogError(502, f"{whole_error}\n(token {token})")

    agents = world.places["p2"].clone / ".github" / "agents"
    agents.mkdir(parents=True)
    (agents / "exporter.agent.md").write_text("exports")
    pid = _waiting("agent-change", "agent:exporter", ["f-2"])
    world.seams = dataclasses.replace(world.seams, backlog=lambda folder: Unreachable(folder, []))

    done = _accept(pid, world)

    assert done["apply_state"] == "failed"
    assert [f["error"] for f in done["failures"]] == [f"BacklogError: {whole_error}\n(token ***)"]


def test_a_spotter_case_becomes_a_candidate_with_its_check_queued(world):
    _record("rec-1")
    other = case_intake.from_record("rec-1", "none", "another call", "cli")  # the same record, made by hand
    pid = _waiting("spotter-case", "look:handoff", ["f-1"], record="rec-1", call="hand-off-fitness")

    done = _accept(pid, world)

    assert [a["step"] for a in done["applied"]] == ["created", "done"]
    cid = done["applied"][0]["artefact"]["ref"]
    assert (cid != other, cases.current()["cases"][cid]["call"]) == (True, "hand-off-fitness")
    assert cases.current()["cases"][cid]["stage"] == "candidate"
    assert cases.fact(cid)["provenance"]["record"]["id"] == "rec-1"
    assert world.checks == [cid]


# lost: the host ended after promoting, before the result; stopped: it ended before promoting; running: this host's
# job runs it now; left: an ended host left it taken, not yet recorded stopped
@pytest.mark.parametrize("result", ["kept", "lost", "stopped", "running", "left"])
def test_a_retried_case_reuses_the_check_that_promoted_it_and_asks_again_after_one_stopped(world, monkeypatch, result):
    _record("rec-1")
    pid = _waiting("spotter-case", "look:handoff", ["f-1"], record="rec-1", call="hand-off-fitness")
    live: list[str] = []
    seams = dataclasses.replace(world.seams, check=lambda cid: case_edits.check_request([cid], act.BY),
                                live=lambda: live[0] if live else "")  # fmt: skip
    act.decide(pid, "accepted", _seen(pid, world), "owner", places=world.places, shared_root=world.shared)
    kept = props.outcome

    def stopped(proposal, kind, **fields):
        if fields.get("step") == "done":
            msg = "the host stopped"
            raise OSError(msg)
        kept(proposal, kind, **fields)

    monkeypatch.setattr(props, "outcome", stopped)
    assert act.apply(pid, seams)["apply_state"] == "failed"
    [asked] = case_replay.queued()
    cid = next(iter(asked["ids"]))
    assert case_replay.take(asked["id"])
    if result in {"kept", "lost"}:
        cur = cases.current()
        review = {"by": "retro-review", "at": cases.now(), "note": "it holds", "content": asked["ids"][cid]}
        promoted = {**cur["cases"][cid], "stage": "test", "review": review}
        cases.commit(cur["n"], {cid: promoted}, "retro-review", "check: it holds")
    if result == "kept":
        cases.append("runs.jsonl", {"id": asked["id"], "kind": "check", "reviews": {cid: {"result": "supported"}}})
        case_replay.done(asked["id"])
    elif result in {"lost", "stopped"}:
        assert [r["id"] for r in case_replay.interrupted()] == [asked["id"]]
    elif result == "running":
        live.append(asked["id"])
    monkeypatch.setattr(props, "outcome", kept)

    done = act.apply(pid, seams)

    check = done["applied"][-1]["artefact"]["check"]
    if result in {"stopped", "left"}:
        assert [q["id"] for q in case_replay.queued()] == [check]  # asked again
    else:
        assert check == asked["id"]
        assert case_replay.queued() == []
    assert done["apply_state"] == "done"


def test_a_case_whose_making_went_unrecorded_is_found_again_after_a_check_promoted_it(world, monkeypatch):
    _record("rec-1")
    pid = _waiting("spotter-case", "look:handoff", ["f-1"], record="rec-1", call="hand-off-fitness")
    act.decide(pid, "accepted", _seen(pid, world), "owner", places=world.places, shared_root=world.shared)
    kept = props.outcome

    def unrecorded(proposal, kind, **fields):
        if fields.get("step") == "created":
            msg = "the disk was full"
            raise OSError(msg)
        kept(proposal, kind, **fields)

    monkeypatch.setattr(props, "outcome", unrecorded)
    assert act.apply(pid, world.seams)["apply_state"] == "failed"
    [cid] = cases.current()["cases"]
    rid = case_edits.check_request([cid], "cli")  # the owner checks it by hand: it holds
    cur = cases.current()
    content = case_replay.queued()[0]["ids"][cid]
    review = {"by": "retro-review", "at": cases.now(), "note": "it holds", "content": content}
    cases.commit(cur["n"], {cid: {**cur["cases"][cid], "stage": "test", "review": review}}, "retro-review", "it holds")
    assert case_replay.take(rid)
    cases.append("runs.jsonl", {"id": rid, "kind": "check", "reviews": {cid: {"result": "supported"}}})
    case_replay.done(rid)
    monkeypatch.setattr(props, "outcome", kept)

    done = act.apply(pid, world.seams)

    assert (done["apply_state"], done["applied"][0]["artefact"]["ref"], done["applied"][-1]["artefact"]["check"]) == (
        "done", cid, rid)  # fmt: skip
    assert (list(cases.current()["cases"]), world.checks) == ([cid], [])


def test_a_synthetic_case_rests_on_its_assumption_and_the_reset_leaves_it_out():
    assumptions.ensure(assumptions.RETRO_SYNTHETIC)
    cid = cases.freeze({"intent": {"task": "historical"}}, {"source": "synthetic",
                       "assumption": assumptions.RETRO_SYNTHETIC})  # fmt: skip
    cases.commit(cases.current()["n"], {cid: {"stage": "candidate", "call": "none", "why": "historical"}},
                 "owner", "historical case")  # fmt: skip
    assert cases.fact(cid)["assumption"] == assumptions.RETRO_SYNTHETIC
    [shown] = [c for c in improvement_view.spotter_cases()["cases"] if c["id"] == cid]
    assert f"assumption {assumptions.RETRO_SYNTHETIC}" in shown["marks"]

    cases.reset()

    assert cid not in cases.current()["cases"]


def test_a_retry_after_a_lost_response_makes_nothing_twice_from_what_was_accepted(world, monkeypatch):
    pid = _waiting("delivery-change", "delivery:hand-off", ["f-1"])
    act.decide(pid, "accepted", _seen(pid, world), "owner", places=world.places, shared_root=world.shared)
    props.reviewed(pid, "later", {"verdict": "survive", "publishable": {"title": "grown", "body": "grown body"}})
    kept = props.outcome
    lost = iter([True])

    def flaky(proposal, kind, **fields):
        if kind == "applied" and next(lost, False):
            msg = "the answer was lost"
            raise OSError(msg)
        kept(proposal, kind, **fields)

    monkeypatch.setattr(props, "outcome", flaky)
    assert act.apply(pid, world.seams)["apply_state"] == "failed"

    done = act.apply(pid, world.seams)

    assert done["apply_state"] == "done"
    assert [i["title"] for i in world.gh.issues if "pull_request" not in i] == [TEXT["title"]]


def test_a_historical_synthetic_issue_is_listed_by_reset_once_without_another_write(world, capsys):
    pid = _waiting("delivery-change", "delivery:hand-off", ["f-3"], provenance="synthetic")
    snapshot = {"destination": {"kind": "issue", "synthetic": True}, "provenance": "synthetic"}
    props.transition(pid, "accepted", "owner", snapshot=snapshot)
    art = {"kind": "issue", "where": "o/r", "ref": "#2", "link": "https://github.com/o/r/issues/2"}
    props.outcome(pid, "applied", step="created", artefact=art)
    props.outcome(pid, "applied", step="closed", artefact=art)
    with pytest.raises(store.RetroError, match=r"synthetic Retro.*retired"):
        act.apply(pid, world.seams)
    assert world.gh.sent == []
    assert cli.main(["improvement", "reset"]) == 0
    listed = capsys.readouterr().out
    assert listed.count("synthetic issue in o/r: #2 https://github.com/o/r/issues/2") == 1, listed


def test_a_reset_retired_proposal_and_a_partial_synthetic_issue_make_nothing(world):
    real = _waiting("agent-change", "agent:exporter", ["f-1"], assumptions=[assumptions.RETRO_SEGMENTS])
    act.decide(real, "accepted", _seen(real, world), "owner", places=world.places, shared_root=world.shared)
    synthetic = _waiting("delivery-change", "delivery:hand-off", ["f-3"], provenance="synthetic",
                         assumptions=[assumptions.RETRO_SYNTHETIC])  # fmt: skip
    snapshot = {"destination": {"kind": "issue", "synthetic": True}, "provenance": "synthetic"}
    props.transition(synthetic, "accepted", "owner", snapshot=snapshot)
    props.outcome(synthetic, "applied", step="created",
                  artefact={"kind": "issue", "where": "o/r", "ref": "#2"})  # fmt: skip

    assumptions.reset()

    with pytest.raises(store.RetroError, match="rests on a retired assumption"):
        act.apply(real, world.seams)
    with pytest.raises(store.RetroError, match=r"synthetic Retro.*retired"):
        act.apply(synthetic, world.seams)
    assert (world.entries, world.gh.sent) == ([], [])
    assert props.folded()[synthetic]["applied"][0]["artefact"]["ref"] == "#2"


def test_unsafe_text_fails_with_nothing_sent_or_written(world):
    leaky = {"title": "Ask jane@example.com", "body": "Token ghp_" + "b" * 36 + " in /Users/jane/notes"}
    pid = _waiting("delivery-change", "delivery:hand-off", ["f-1"], text=leaky)

    done = _accept(pid, world)

    assert done["apply_state"] == "failed"
    error = done["failures"][0]["error"]
    assert all(said in error for said in ("a credential", "an email address", "a home path")), error
    assert "jane" not in error
    assert world.gh.sent == []
    assert world.entries == []


@pytest.mark.parametrize("change", ["re-review", "destination", "text"])
def test_a_decision_on_a_stale_view_is_refused_with_nothing_written(world, change):
    pid = _waiting("lesson", "agent:builder", ["f-1"])
    token = _seen(pid, world)
    if change == "destination":
        del world.places["p1"]
    else:
        props.file(props.open_key("real", "lesson", "agent:builder"), ["f-1", "f-4"])
        text = TEXT if change == "re-review" else {"title": "other", "body": "other"}
        props.reviewed(
            pid, props.folded()[pid]["evidence"], {"verdict": "survive", "why": "again", "publishable": text}
        )
    before = store.lines(props.FILE)

    with pytest.raises(store.RetroError, match="changed since it was shown"):
        act.decide(pid, "accepted", token, "owner", places=world.places, shared_root=world.shared)

    assert store.lines(props.FILE) == before


def test_a_redirect_needs_a_direction_and_queues_one_redraft(world):
    pid = _waiting("lesson", "agent:builder", ["f-1"])
    with pytest.raises(act.Refused):
        act.decide(pid, "redirected", _seen(pid, world), "owner", places=world.places, shared_root=world.shared)

    after = act.decide(
        pid,
        "redirected",
        _seen(pid, world),
        "owner",
        places=world.places,
        shared_root=world.shared,
        direction="shorter",
    )

    assert (after["state"], after["direction"]) == ("redirected", "shorter")
    assert [r["redraft"] for r in store.queued()] == [pid]
