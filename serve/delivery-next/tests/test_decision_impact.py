"""A change of mind's impact report and its grouped fixes (TD-428, TD-419 slice 5b part 2)."""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient

from owlbear_decisions import Applicability, Decision, Link, LinkType, Origin, Scope, State, new_id, write
from owlbear_delivery_next.change_contracts.decision_records import DecisionBaseline, Said
from owlbear_delivery_next.change_contracts.models import Change, Step, StepKind
from owlbear_delivery_next.local_system import local_home
from owlbear_delivery_next.local_system.codebase import CURRENT
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.machine_host import app, project
from owlbear_delivery_next.machine_host.machine import Machine
from owlbear_delivery_next.project_host import api
from owlbear_delivery_next.project_host.host import Host, HostRecord
from owlbear_delivery_next.state_store import decision_fixes, decision_impact, decision_store, decision_sync
from owlbear_delivery_next.state_store.backlog import Backlog
from owlbear_delivery_next.state_store.decision_actions import Refused
from owlbear_delivery_next.state_store.decision_impact import ACCEPTED, REMOTE, Impact, Place, Report
from owlbear_delivery_next.state_store.store import Store

if TYPE_CHECKING:
    from pathlib import Path

AT = datetime(2026, 10, 21, 9, tzinfo=UTC)
PROJECT, OTHER = "shop-site", "blog"
AUTH = {"authorization": "Bearer t"}
CHAT = AUTH | {"x-owlbear-use": "chat"}


def git(cwd: Path, *args: str) -> str:
    who = ["-c", "user.name=t", "-c", "user.email=t@example.com"]
    return subprocess.run(["git", *who, *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()  # noqa: S603, S607


def make(**changes) -> Decision:
    fields = {
        "id": new_id(), "title": "Notes live in SQLite", "statement": "Notes live in one SQLite table.",
        "scope": Scope.PROJECT, "project": PROJECT, "origin": Origin.AUTONOMOUS, "actor": "shaper",
        "state": State.IN_FORCE, "created_at": AT,
    }  # fmt: skip
    return Decision(**{**fields, **changes})


def pair(paths: tuple[str, ...] = (), rationale: str = "", **scope) -> tuple[Decision, Decision]:
    """An old rule, replaced, and its successor in force."""
    old = make(state=State.REPLACED, applies_to=Applicability(paths=paths), **scope)
    new = make(title="Notes live in Postgres", statement="Notes live in Postgres.", rationale=rationale,
               links=(Link(type=LinkType.REPLACES, target=old.id),), applies_to=old.applies_to, **scope)  # fmt: skip
    return old, new


def publish(shared: DataRepo, *decisions: Decision, records: dict[str, dict] | None = None) -> None:
    for d in decisions:
        write(d, shared.root if d.scope is Scope.GLOBAL else shared.root / d.project)
    for name, record in (records or {}).items():
        path = shared.root / PROJECT / "changes" / f"{name}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record))
    git(shared.root, "add", "-A")
    git(shared.root, "commit", "-qm", "seed")
    git(shared.root, "push", "-q", "origin", "HEAD")


def clone(tmp_path: Path, name: str, files: list[str], *, origin: bool = True) -> Path:
    """A project checkout, pushed to a local bare remote whose default branch ``origin/HEAD`` names."""
    path = tmp_path / name
    git(tmp_path, "init", "-q", "-b", "main", str(path))
    for f in files:
        (path / f).parent.mkdir(parents=True, exist_ok=True)
        (path / f).write_text("x\n")
    git(path, "add", "-A")
    git(path, "commit", "-qm", "start", "--allow-empty")
    if origin:
        git(tmp_path, "init", "-q", "--bare", "-b", "main", str(tmp_path / f"{name}.git"))
        git(path, "remote", "add", "origin", str(tmp_path / f"{name}.git"))
        git(path, "push", "-q", "-u", "origin", "main")
        git(path, "remote", "set-head", "origin", "main")
    return path


def merged(decision_id: str) -> dict:
    return {"slug": "c1", "outcome": "merged", "pr": {"number": 7, "url": "https://github.com/acme/shop/pull/7"},
            "brief": {"title": "Notes", "decisions": [{"id": decision_id}]}, "decisions_applied": []}  # fmt: skip


@pytest.fixture
def shared(shared_repo) -> DataRepo:
    repo = DataRepo(shared_repo[0])
    repo.claim(PROJECT, "github.com/acme/shop-site")
    repo.claim(OTHER, "github.com/acme/blog")
    return repo


@pytest.fixture
def store(tmp_path, shared) -> Store:
    return Store(tmp_path / "store", shared, PROJECT)


def verdicts(report) -> dict[str, tuple[str, str]]:
    return {i.project: (i.status, i.why) for i in report.projects}


def test_merge_history_confirms_built_effect_from_a_merged_record_and_from_a_baseline(tmp_path, shared, store):
    old, new = pair(paths=("notes/**",))
    publish(shared, old, new, records={"20261020-090000-c1": merged(old.id),
                                       "20261020-100000-c2": merged(old.id) | {"outcome": "abandoned"}})  # fmt: skip
    repo = clone(tmp_path, "shop", ["notes/db.py", "tests/test_notes.py"])
    by_record = decision_impact.report(shared, PROJECT, new.id, [Place(PROJECT, repo, store)])
    [only] = by_record.projects
    assert (only.status, only.changes) == ("confirmed", (
        {"slug": "c1", "title": "Notes", "pr": "https://github.com/acme/shop/pull/7", "from": "merged"},))  # fmt: skip
    assert only.paths == ("notes/db.py",)  # its matching files stay evidence

    other = make(title="Tags", statement="Tags.", applies_to=Applicability(paths=("tags/**",)), state=State.REPLACED)
    later = make(title="Tags 2", statement="Tags two.", links=(Link(type=LinkType.REPLACES, target=other.id),))
    publish(shared, other, later)
    with store.lock("c3") as lock:
        said = {other.id: Said(title=other.title, statement=other.statement)}
        pin = DecisionBaseline(commit="c", at=AT, revisions={other.id: other.rule_revision}, said=said)
        store.write(lock, Change(slug="c3", step=Step(kind=StepKind.BUILD), decisions_baseline=pin))
    by_pin = decision_impact.report(shared, PROJECT, later.id, [Place(PROJECT, repo, store)])
    assert verdicts(by_pin)[PROJECT][0] == "confirmed"
    assert [c["slug"] for c in by_pin.projects[0].changes] == ["c3"]


def test_path_selectors_without_matching_files_are_unaffected_and_whole_project_rules_unknown(tmp_path, shared, store):
    scoped, scoped_new = pair(paths=("web/**",))
    whole, whole_new = pair()
    publish(shared, scoped, scoped_new, whole, whole_new)
    repo = clone(tmp_path, "shop", ["src/app.py", "README.md"])
    here = [Place(PROJECT, repo, store)]

    assert verdicts(decision_impact.report(shared, PROJECT, scoped_new.id, here))[PROJECT] == (
        "unaffected", "no file matches its paths here, at HEAD or on the remote, and no Change applied it")  # fmt: skip
    assert verdicts(decision_impact.report(shared, PROJECT, whole_new.id, here))[PROJECT] == (
        "unknown", decision_impact.WHOLE)  # fmt: skip
    gone = make(state=State.WITHDRAWN, applies_to=Applicability(paths=("src/**",)))
    publish(shared, gone)
    withdrawn = decision_impact.report(shared, PROJECT, gone.id, here)
    assert (withdrawn.new, withdrawn.effect, verdicts(withdrawn)[PROJECT][0]) == (None, "withdrawn", "unknown")
    with pytest.raises(Refused, match="replaced no decision"):
        decision_impact.report(shared, PROJECT, scoped.id, here)


def test_an_unavailable_project_stays_unknown_and_says_why(tmp_path, shared, store):
    old, new = pair(paths=("src/**",))
    publish(shared, old, new, records={"20261020-090000-c1": merged(old.id)})
    unserved = decision_impact.report(shared, PROJECT, new.id, [])
    broken = decision_impact.report(shared, PROJECT, new.id, [Place(PROJECT, tmp_path / "gone", store)])
    assert verdicts(unserved)[PROJECT] == ("unknown", "shop-site's repository is not a project this host serves")
    assert unserved.projects[0].changes[0]["slug"] == "c1"  # the merged record is still evidence
    assert verdicts(broken)[PROJECT][0] == "unknown"
    assert "cannot" in verdicts(broken)[PROJECT][1]


def test_a_global_change_covers_every_known_project_and_owlbears_folder(tmp_path, shared):
    old, new = pair(paths=("web/**",), scope=Scope.GLOBAL, project="")
    (shared.root / "owlbear").mkdir()
    write(make(project="owlbear", title="Lint once", statement="Linted once."), shared.root / "owlbear")
    publish(shared, old, new)
    places = [Place(PROJECT, clone(tmp_path, "shop", ["web/a.js"])), Place(OTHER, clone(tmp_path, "blog", ["a.md"]))]

    report = decision_impact.report(shared, PROJECT, new.id, places)

    assert {k: v[0] for k, v in verdicts(report).items()} == {
        PROJECT: "unknown", OTHER: "unaffected", "owlbear": "unknown"}  # fmt: skip
    assert verdicts(report)["owlbear"][1] == "OwlBear's repository is not a project this host serves"


def test_evidence_is_capped_and_test_files_are_named(tmp_path, shared, store):
    old, new = pair(paths=("src/**", "tests/**"))
    publish(shared, old, new)
    files = [f"src/m{n:02}.py" for n in range(55)] + ["tests/test_a.py", "src/test_b.py"]
    shown = decision_impact.shown(decision_impact.report(shared, PROJECT, new.id, [
        Place(PROJECT, clone(tmp_path, "shop", files), store)]))  # fmt: skip
    [p] = shown["projects"]
    assert (len(p["paths"]), p["more"], p["tests"], p["more_tests"]) == (50, 7, ["src/test_b.py", "tests/test_a.py"], 0)
    assert (shown["old"]["id"], shown["new"]["id"], shown["effect"], shown["fixes"]) == (
        old.id, new.id, "unknown", True)  # fmt: skip
    assert "treated as forbidding" in shown["divergence"]


def client(store: Store, repo: Path | None = None, headers=AUTH) -> TestClient:
    record = HostRecord(url="http://127.0.0.1:9/", token="tok", pid=1, started_at=datetime.now(UTC), code=CURRENT)  # noqa: S106
    host = SimpleNamespace(wake=SimpleNamespace(set=lambda: None), repo=repo, record=record)
    return TestClient(api.create_app(store, "t", host), base_url="http://127.0.0.1", headers=headers)


def successor(shared: DataRepo, old_id: str) -> Decision:
    view = decision_store.load(shared, PROJECT).snapshot
    return next(e.decision for e in view.entries if any(link.target == old_id for link in e.decision.links))


@pytest.mark.parametrize("case", [("wording", "wording"), ("forbids", "forbids"), ("", "unknown")])
def test_the_owner_marks_a_replacement_and_its_successor_records_it(tmp_path, shared, store, github, case):
    effect, said = case
    old = make(rationale="Effect on existing work: wording only")  # an inherited mark never counts
    publish(shared, old)
    body = {"revision": old.revision, "statement": "Notes live in Postgres.", "reason": "Scale.", "effect": effect,
            "confirmed": True}  # fmt: skip
    assert client(store).post(f"/api/next/decisions/{old.id}/replace", json=body).json()["saved"]
    new = successor(shared, old.id)
    assert (decision_impact.effect(new), new.rationale.count("Effect on existing work")) == (said, int(bool(effect)))
    assert github.issues == {}  # activating or replacing schedules nothing
    got = client(store, clone(tmp_path, "shop", [])).post(
        f"/api/next/decisions/{new.id}/schedule-fixes?folder={PROJECT}", json={"revision": new.revision}
    )
    if effect == "wording":
        assert (got.status_code, "wording-only" in got.json()["detail"], github.issues) == (422, True, {})
    else:
        assert [e["project"] for e in got.json()["entries"]] == [PROJECT]


def test_scheduling_makes_one_grouped_entry_per_project_with_revisions_and_a_checklist(tmp_path, shared, github):
    old, new = pair(paths=("web/**", "api/**"), scope=Scope.GLOBAL, project="")
    publish(shared, old, new)
    spread = [f"web/p{n}.js" for n in range(15)] + [f"api/r{n}.py" for n in range(10)]
    places = [Place(PROJECT, clone(tmp_path, "shop", ["web/a.js"])), Place(OTHER, clone(tmp_path, "blog", spread)),
              Place("tools", clone(tmp_path, "tools", ["x.md"]))]  # fmt: skip
    report = decision_impact.report(shared, PROJECT, new.id, places)

    made = decision_fixes.schedule(shared, report, new.revision)

    assert [(m["project"], m["title"]) for m in made] == [
        (PROJECT, f"Apply decision {new.id} in {PROJECT}: Notes live in Postgres"),
        (OTHER, f"Apply decision {new.id} in {OTHER} (web/): Notes live in Postgres"),
        (OTHER, f"Apply decision {new.id} in {OTHER} (api/): Notes live in Postgres"),
    ]  # the unaffected project gets none
    first = github.issues[1]
    assert f"Old rule \u201c{old.title}\u201d: {old.statement}" in first["body"]
    assert f"New rule \u201c{new.title}\u201d: {new.statement}" in first["body"]
    assert f"({old.id}" not in first["body"].split("Tick each item")[0]  # its readable head names titles
    assert "- [ ] web/a.js" in first["body"]
    assert f"decision {new.id} revision {new.revision}" in first["body"]  # the evidence list
    assert "**Projects:** shop-site" in first["body"]
    assert github.issues[2]["body"].split("<!--")[0].count("- [ ] web/") == 15  # its readable part
    again = decision_fixes.schedule(shared, report, new.revision)
    assert (len(github.issues), [m["new"] for m in again]) == (3, [False, False, False])  # reconciled, not repeated
    with pytest.raises(Refused, match="changed since"):
        decision_fixes.schedule(shared, report, old.revision)


def test_areas_split_at_most_five_ways():
    paths = [f"{folder}/f{n}.py" for folder in "abcdefg" for n in range(4)]
    assert [area for area, _ in decision_fixes.areas(paths)] == ["a/", "b/", "c/", "d/", "other folders"]
    assert decision_fixes.areas(["a/1", "b/2"]) == [("", ["a/1", "b/2"])]


def test_only_the_owner_schedules_fixes_and_accepts_existing_code(tmp_path, shared, store, github):
    old, new = pair()
    publish(shared, old, new, records={"20261020-090000-c1": merged(old.id)})
    repo = clone(tmp_path, "shop", ["a.py"])
    base = f"/api/next/decisions/{new.id}"
    chat = client(store, repo, CHAT)
    shown = chat.get(f"{base}/impact?folder={PROJECT}").json()  # a chat reads the report
    accept = {"revision": new.revision, "project": PROJECT, "reason": "Old notes stay in SQLite."}
    refused = [chat.post(f"{base}/schedule-fixes?folder={PROJECT}", json={"revision": new.revision}).status_code,
               chat.post(f"{base}/accept-existing?folder={PROJECT}", json=accept).status_code]  # fmt: skip
    assert (shown["projects"][0]["status"], refused, github.issues) == ("confirmed", [403, 403], {})

    owner = client(store, repo)
    assert owner.post(f"{base}/accept-existing?folder={PROJECT}", json=accept | {"reason": ""}).status_code == 422
    kept = owner.post(f"{base}/accept-existing?folder={PROJECT}", json=accept).json()
    assert kept["saved"]
    after = owner.get(f"{base}/impact?folder={PROJECT}").json()
    held = decision_store.load(shared, PROJECT).snapshot.get(after["projects"][0]["accepted"]).decision
    assert (held.origin, held.links, held.source) == (
        Origin.DECIDED, (Link(type=LinkType.REFINES, target=new.id),), decision_impact.ACCEPTED)  # fmt: skip
    kept_code = f"Code in {PROJECT} built before \u201c{new.title}\u201d stays as it is; new work follows it."
    assert held.statement == kept_code
    assert git(shared.root, "log", "-1", "--format=%B") == f"decisions: accept-existing {new.id} ({PROJECT})"
    assert after["fixes"] is False
    nothing = owner.post(f"{base}/schedule-fixes?folder={PROJECT}", json={"revision": new.revision})
    assert (nothing.status_code, github.issues) == (409, {})
    assert owner.get(f"/api/next/decisions/{new.id}/impact?folder=..").status_code == 422


def test_the_machine_host_reports_on_every_project_it_serves(tmp_path, shared, monkeypatch):
    """Like the pinning Changes of every loaded project (slice 5a), a Global rule's impact covers them all."""
    (local_home.root() / "data.json").write_text(json.dumps({"repository": str(shared.root)}))
    monkeypatch.setattr(project.readiness, "ready", lambda _store, _repo: [])
    monkeypatch.setattr(Host, "_spawn", lambda _self, slug: pytest.fail(f"no runner starts here ({slug})"))
    old, new = pair(paths=("web/**",), scope=Scope.GLOBAL, project="")
    publish(shared, old, new)
    record = HostRecord(url="http://127.0.0.1:9/", token="t", pid=1, started_at=datetime.now(UTC), code=CURRENT)  # noqa: S106
    machine = Machine(record)
    try:
        http = TestClient(app.create(machine), base_url="http://127.0.0.1", headers=AUTH)
        for name, files in ((PROJECT, ["web/a.js"]), (OTHER, ["notes.md"])):
            path, url = clone(tmp_path, name, files), f"git@github.com:acme/{name}.git"
            git(path, "remote", "set-url", "origin", url)  # the project's identity; Git fetches the local remote
            git(path, "config", f"url.{tmp_path / name}.git.insteadOf", url)
            assert http.post("/api/next/projects", json={"path": str(path)}).status_code == 200
        base = f"/api/next/decisions/{new.id}"
        got = http.get(f"{base}/impact?folder={PROJECT}").json()
        chat = http.post(f"{base}/schedule-fixes?folder={PROJECT}", json={"revision": new.revision},
                         headers={"x-owlbear-use": "chat"})  # fmt: skip
    finally:
        machine.stop_all()
    assert {p["project"]: p["status"] for p in got["projects"]} == {PROJECT: "unknown", OTHER: "unaffected"}
    assert chat.status_code == 403


def test_untracked_unpushed_and_remote_files_count_and_an_unconfirmed_remote_is_never_unaffected(
    tmp_path, shared, store
):
    old, new = pair(paths=("web/**",))
    publish(shared, old, new)

    def seen(repo: Path) -> tuple[str, str, tuple[str, ...]]:
        [only] = decision_impact.report(shared, PROJECT, new.id, [Place(PROJECT, repo, store)]).projects
        return only.status, only.why, only.paths

    repo = clone(tmp_path, "shop", ["src/app.py"])
    assert seen(repo)[0] == "unaffected"
    (repo / "web").mkdir()
    (repo / "web" / "new.js").write_text("x\n")
    assert seen(repo)[::2] == ("unknown", ("web/new.js",))  # untracked
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "local")
    git(repo, "rm", "-q", "web/new.js")  # gone from the working tree, still in the unpushed commit at HEAD
    assert seen(repo)[::2] == ("unknown", ("web/new.js",))

    fresh, peer = clone(tmp_path, "blog", ["src/app.py"]), tmp_path / "peer"
    git(tmp_path, "clone", "-q", str(tmp_path / "blog.git"), str(peer))
    (peer / "web").mkdir()
    (peer / "web" / "pushed.js").write_text("x\n")
    git(peer, "add", "-A")
    git(peer, "commit", "-qm", "elsewhere")
    git(peer, "push", "-q")
    assert seen(fresh)[::2] == ("unknown", ("web/pushed.js",))  # only on the remote: fetched first

    cut = clone(tmp_path, "cut", ["src/app.py"])
    git(cut, "remote", "set-url", "origin", str(tmp_path / "missing.git"))  # the fetch fails
    for unconfirmed in (cut, clone(tmp_path, "solo", ["src/app.py"], origin=False)):  # the second has no remote
        status, why, _ = seen(unconfirmed)
        assert (status, why.startswith(REMOTE)) == ("unknown", True)


def test_older_or_unreadable_change_records_cannot_prove_a_project_unaffected(tmp_path, shared, store):
    old, new = pair(paths=("web/**",))
    publish(shared, old, new, records={"20261019-090000-c0": merged("D-ELSE") | {"slug": "c0"}})
    here = [Place(PROJECT, clone(tmp_path, "shop", ["src/app.py"]), store)]
    changes = shared.root / PROJECT / "changes"
    assert verdicts(decision_impact.report(shared, PROJECT, new.id, here))[PROJECT][0] == "unaffected"

    older = merged("D-ELSE") | {"slug": "c1"}
    del older["decisions_applied"]
    (changes / "20261020-090000-c1.json").write_text(json.dumps(older))
    [impact] = decision_impact.report(shared, PROJECT, new.id, here).projects
    assert (impact.status, impact.why, impact.incomplete) == (
        "unknown", "1 finished-Change record(s) cannot rule out that it was applied",
        ("20261020-090000-c1.json: merged, but records no decisions it applied",))  # fmt: skip

    (changes / "20261020-100000-c2.json").write_text("{not json")
    shown = decision_impact.shown(decision_impact.report(shared, PROJECT, new.id, here))
    [p] = shown["projects"]
    assert (p["status"], p["incomplete"]) == ("unknown", [
        "20261020-090000-c1.json: merged, but records no decisions it applied",
        "20261020-100000-c2.json: cannot be read (JSONDecodeError)"])  # fmt: skip


def test_keeping_existing_code_is_refused_when_the_rule_changed_after_the_report_was_read(
    tmp_path, shared_repo, shared, store
):
    old, new = pair()
    publish(shared, old, new, records={"20261020-090000-c1": merged(old.id)})
    report = decision_impact.report(shared, PROJECT, new.id, [Place(PROJECT, clone(tmp_path, "shop", []), store)])
    peer = tmp_path / "peer"
    git(tmp_path, "clone", "-q", str(shared_repo[1]), str(peer))
    write(new.model_copy(update={"state": State.WITHDRAWN}), peer / PROJECT, new.revision)
    git(peer, "add", "-A")
    git(peer, "commit", "-qm", "withdrawn elsewhere")
    git(peer, "push", "-q")
    pushed = git(peer, "rev-parse", "HEAD")

    with pytest.raises(Refused, match="no longer the rule in force"):
        decision_fixes.accept(shared, report, PROJECT, new.revision, "Old notes stay.")

    assert not [e for e in decision_store.whole(shared)[0].values() if e.decision.source == ACCEPTED]
    assert git(shared.root, "ls-remote", "origin", "HEAD").split()[0] == pushed  # nothing published
    assert git(shared.root, "status", "--porcelain") == ""


def test_keeping_existing_code_is_taken_back_when_the_rule_changed_between_catch_up_and_push(
    tmp_path, shared_repo, shared, store, monkeypatch
):
    old, new = pair()
    publish(shared, old, new, records={"20261020-090000-c1": merged(old.id)})
    report = decision_impact.report(shared, PROJECT, new.id, [Place(PROJECT, clone(tmp_path, "shop", []), store)])
    peer, caught_up = tmp_path / "peer", decision_sync.catch_up
    git(tmp_path, "clone", "-q", str(shared_repo[1]), str(peer))

    def overtaken(repo: DataRepo, until: float) -> str:
        said = caught_up(repo, until)
        monkeypatch.setattr(decision_sync, "catch_up", caught_up)
        write(new.model_copy(update={"state": State.WITHDRAWN}), peer / PROJECT, new.revision)
        git(peer, "commit", "-qam", "withdrawn after the catch-up")
        git(peer, "push", "-q")
        return said

    monkeypatch.setattr(decision_sync, "catch_up", overtaken)
    with pytest.raises(Refused, match="no longer the rule in force"):
        decision_fixes.accept(shared, report, PROJECT, new.revision, "Old notes stay.")

    pushed = git(peer, "rev-parse", "HEAD")
    assert not [e for e in decision_store.whole(shared)[0].values() if e.decision.source == ACCEPTED]
    assert git(shared.root, "ls-remote", "origin", "HEAD").split()[0] == pushed  # nothing published
    assert git(shared.root, "rev-parse", "HEAD") == pushed  # the acceptance commit taken back, then rebased
    assert git(shared.root, "status", "--porcelain") == ""


def test_scheduling_again_reconciles_the_same_entry_keeping_ticks_and_its_grouping(tmp_path, shared, store, github):
    old, new = pair(paths=("notes/**", "web/**"))
    publish(shared, old, new)
    repo = clone(tmp_path, "shop", ["notes/a.py", "notes/b.py"])

    def schedule() -> list[dict]:
        report = decision_impact.report(shared, PROJECT, new.id, [Place(PROJECT, repo, store)])
        return decision_fixes.schedule(shared, report, new.revision)

    def checks(number: int) -> list[str]:
        return [line for line in github.issues[number]["body"].split("<!--")[0].splitlines() if line.startswith("- [")]

    [first] = schedule()
    number = int(first["id"])
    issue = github.issues[number]
    issue["body"] = issue["body"].replace("- [ ] notes/a.py", "- [x] notes/a.py", 1)  # ticked on GitHub
    (repo / "notes" / "c.py").write_text("x\n")
    [second] = schedule()
    assert (second["id"], second["new"], second["added"], len(github.issues)) == (first["id"], False, 1, 1)
    assert checks(number) == ["- [x] notes/a.py", "- [ ] notes/b.py", "- [ ] notes/c.py"]
    body = github.issues[number]["body"]
    assert f"Old rule \u201c{old.title}\u201d: {old.statement}" in body
    assert f"New rule \u201c{new.title}\u201d: {new.statement}" in body

    (repo / "web").mkdir()
    for n in range(30):  # past the split threshold, spread over two folders: the project's entry keeps them all
        (repo / "web" / f"p{n:02}.js").write_text("x\n")
    (repo / "notes" / "c.py").unlink()  # no longer found: stays listed
    third = schedule()
    assert ([m["id"] for m in third], len(github.issues)) == ([first["id"]], 1)
    assert checks(number)[:3] == ["- [x] notes/a.py", "- [ ] notes/b.py", "- [ ] notes/c.py"]
    assert checks(number)[3:] == [f"- [ ] web/p{n:02}.js" for n in range(30)]


def test_a_long_checklist_takes_numbered_entries_listing_every_item_up_to_a_cap(shared, github, monkeypatch):
    old, new = pair(paths=("src/**",))
    publish(shared, old, new)
    paths = tuple(f"src/{'m' * 60}{n:04}.py" for n in range(400))  # one folder: no split by area
    impact = Impact(PROJECT, "unknown", "400 files match", (), paths)

    made = decision_fixes.schedule(shared, Report(old, new, "forbids", (impact,)), new.revision)

    n = len(made)
    assert 1 < n <= decision_fixes.PARTS
    title = f"Apply decision {new.id} in {PROJECT} (part {{}} of {n}): Notes live in Postgres"
    assert [m["title"] for m in made] == [title.format(k) for k in range(1, n + 1)]
    texts = [Backlog(shared, PROJECT).current(m["id"]).text for m in made]
    assert max(map(len, texts)) <= 4000
    assert [k for t in texts for k, _, _ in decision_fixes.checklist(t)] == list(paths)  # each once, in order

    monkeypatch.setattr(decision_fixes, "PARTS", 2)
    other, later = pair(paths=("src/**",))
    publish(shared, other, later)
    wide = Impact(PROJECT, "unknown", "400 files match", (), paths)
    with pytest.raises(Refused, match=r"needs .* backlog entries, more than 2"):
        decision_fixes.schedule(shared, Report(other, later, "forbids", (wide,)), later.revision)
    assert len(github.issues) == n  # nothing written
