"""Acting on an accepted Retro proposal (#716): each artefact made once, from what was accepted, and nothing unsafe."""

import gzip
import json
import subprocess
from types import SimpleNamespace

import pytest
from owlbear_memory.engine import MemoryEngine
from owlbear_memory.models import MemoryState

from owlbear_delivery_next.commands import cli
from owlbear_delivery_next.github.owlbear_issues import OwlbearIssues
from owlbear_delivery_next.improvement import assumptions, case_intake, cases, spotter
from owlbear_delivery_next.improvement import proposal_apply as act
from owlbear_delivery_next.improvement import proposal_targets as targets
from owlbear_delivery_next.improvement import retro_proposals as props
from owlbear_delivery_next.improvement import retro_store as store

UNITS = {"f-1": "chg:p1:fix", "f-2": "chg:p2:fix", "f-3": "syn:scout-a", "f-4": "chg:p1:other"}
TEXT = {
    "title": "Check the export's week column",
    "body": "The builder said done before the week column held ISO weeks.",
}


class FakeGitHub:
    """The issues of one repository behind ``gh api``; every payload sent is kept."""

    def __init__(self):
        self.issues, self.sent, self.close_fails = [{"number": 1, "pull_request": {}, "body": "x"}], [], 0

    def __call__(self, argv, data, _timeout, _cwd):
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
    for pid, name in (("p1", "alpha"), ("p2", "beta"), ("ps", targets.SANDBOX)):
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
    assert entry.evidence == [f"retro-proposal:{pid}", "f-2"]
    assert act.apply(pid, world.seams)["applied"] == done["applied"]
    assert len(world.entries) == 1


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


def test_a_synthetic_case_rests_on_its_assumption_and_the_reset_leaves_it_out(world):
    pid = _waiting("spotter-case", "look:sample", ["f-3"], provenance="synthetic", record="syn-scout-a-1", call="none")
    cid = _accept(pid, world)["applied"][0]["artefact"]["ref"]
    assert cases.fact(cid)["assumption"] == assumptions.RETRO_SYNTHETIC
    assert cid in cases.current()["cases"]

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


def test_a_synthetic_issue_is_closed_on_retry_and_the_reset_lists_it_once(world, capsys):
    pid = _waiting("delivery-change", "delivery:hand-off", ["f-3"], provenance="synthetic")
    world.gh.close_fails = 1

    failed = _accept(pid, world)

    assert failed["apply_state"] == "failed"
    assert "ghp_" not in failed["failures"][0]["error"]
    assert "502" in failed["failures"][0]["error"]
    sent = len(world.gh.sent)
    done = act.apply(pid, world.seams)
    assert world.gh.sent[sent:] == [{"state": "closed", "state_reason": "not_planned"}]  # the issue made, not sought
    made = [i for i in world.gh.issues if "pull_request" not in i]
    assert [(i["title"], i["state"]) for i in made] == [(f"[synthetic] {TEXT['title']}", "closed")]
    assert done["apply_state"] == "done"
    assert act.apply(pid, world.seams)["applied"] == done["applied"]
    assert cli.main(["improvement", "reset"]) == 0
    listed = capsys.readouterr().out
    assert listed.count("synthetic issue in o/r: #2 https://github.com/o/r/issues/2") == 1, listed


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
