"""The Decisions page's API and the chat tools on it: list, entry, the owner's actions, refusals (TD-419 slice 5a)."""

from __future__ import annotations

import asyncio
import subprocess
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

import pytest
from fastapi.testclient import TestClient

from owlbear_decisions import Decision, Link, LinkType, Origin, OwnerWords, Scope, State, new_id, write
from owlbear_decisions.validate import validate_repo
from owlbear_delivery_next.change_contracts.models import Brief, Change, Names, Plan, Step, StepKind, Task
from owlbear_delivery_next.commands import mcp_server
from owlbear_delivery_next.local_system.codebase import CURRENT
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.project_host import api
from owlbear_delivery_next.project_host.host import HostRecord
from owlbear_delivery_next.state_store import decision_actions, decision_store
from owlbear_delivery_next.state_store.store import Lock, Store
from owlbear_delivery_next.workflow_steps import decisions_gate

if TYPE_CHECKING:
    from pathlib import Path

AT = datetime(2026, 10, 21, 9, tzinfo=UTC)
PROJECT = "shop-site"
AUTH = {"authorization": "Bearer t"}
CHAT = AUTH | {"x-owlbear-use": "chat"}


class Host:
    wake = SimpleNamespace(set=lambda: None)
    record = HostRecord(url="http://127.0.0.1:9/", token="tok", pid=1, started_at=datetime.now(UTC), code=CURRENT)  # noqa: S106


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()  # noqa: S603, S607


def make(**changes) -> Decision:
    fields = {
        "id": new_id(), "title": "Notes live in SQLite", "statement": "Notes live in one SQLite table.",
        "scope": Scope.PROJECT, "project": PROJECT, "origin": Origin.AUTONOMOUS, "actor": "shaper",
        "state": State.IN_FORCE, "created_at": AT,
    }  # fmt: skip
    return Decision(**{**fields, **changes})


def decided(**changes) -> Decision:
    words = (OwnerWords(text="Keep it so.", date=AT.date()),)
    return make(origin=Origin.DECIDED, owner_words=words, **changes)


def worldwide(**changes) -> Decision:
    return make(scope=Scope.GLOBAL, project="", title="Pages are plain HTML", statement="No build step.", **changes)


def after(old: Decision, **changes) -> Decision:
    return make(links=(Link(type=LinkType.REPLACES, target=old.id),), **changes)


def seed(shared: DataRepo, *decisions: Decision) -> None:
    """Write *decisions* in their layers and publish them as one commit."""
    for d in decisions:
        write(d, shared.root if d.scope is Scope.GLOBAL else shared.root / d.project)
    git(shared.root, "add", "-A")
    git(shared.root, "commit", "-qm", "seed")
    git(shared.root, "push", "-q", "origin", "HEAD")


@pytest.fixture
def shared(shared_repo) -> DataRepo:
    repo = DataRepo(shared_repo[0])
    repo.claim(PROJECT, "github.com/acme/shop-site")
    return repo


@pytest.fixture
def store(tmp_path, shared) -> Store:
    return Store(tmp_path / "store", shared, PROJECT)


def client(store: Store, headers=AUTH) -> TestClient:
    return TestClient(api.create_app(store, "t", Host()), base_url="http://127.0.0.1", headers=headers)


@pytest.fixture
def owner(store) -> TestClient:
    return client(store)


def now(shared: DataRepo, decision_id: str) -> Decision:
    return decision_store.load(shared, PROJECT).snapshot.get(decision_id).decision


def act(c: TestClient, d: Decision, action: str, **body):
    return c.post(f"/api/next/decisions/{d.id}/{action}", json={"revision": d.revision, **body})


def listed(c: TestClient, **query) -> list[str]:
    return [d["title"] for d in c.get("/api/next/decisions", params=query).json()["decisions"]]


def test_without_a_shared_repository_the_tab_says_so(tmp_path):
    got = client(Store(tmp_path / "store")).get("/api/next/decisions").json()
    assert (got["available"], got["decisions"]) == (False, [])
    assert client(Store(tmp_path / "store"), headers={}).get("/api/next/decisions").status_code == 401


def test_the_list_filters_by_scope_state_origin_topic_read_back_and_text(owner, shared):
    seed(shared, make(title="Notes in SQLite", topic="storage"), worldwide(origin=Origin.DECIDED, owner_words=(
        OwnerWords(text="No build.", date=AT.date()),), read_back="2026-10-20"),
        make(title="Tags are free text", statement="Any tag.", state=State.DRAFT),
        make(title="Old export", state=State.WITHDRAWN))  # fmt: skip

    assert sorted(listed(owner, where="project")) == ["Notes in SQLite", "Tags are free text"]
    assert listed(owner, where="global") == ["Pages are plain HTML"]
    assert len(listed(owner)) == 3
    assert "Old export" in listed(owner, retired="true")
    assert listed(owner, state="withdrawn") == ["Old export"]
    assert listed(owner, origin="decided") == ["Pages are plain HTML"]
    assert listed(owner, topic="storage") == ["Notes in SQLite"]
    assert listed(owner, read_back="done") == ["Pages are plain HTML"]
    assert listed(owner, text="sqlite") == ["Notes in SQLite"]
    assert owner.get("/api/next/decisions").json()["topics"] == ["storage"]


def test_an_entry_shows_provenance_links_both_ways_history_and_the_changes_that_pinned_it(owner, store, shared):
    old = make(title="Notes in a file", state=State.REPLACED)
    rule = after(old, title="Notes in SQLite", source="chat")
    seed(shared, old, rule)
    brief = Brief(version=1, approved_version=1, challenged=1, approved_at=AT, title="Notes", scope=["web"])
    plan = Plan(tasks=[Task(id="t1", title="Show notes", scope=["web"], checks=["true"])])
    c = Change(slug="c1", brief=brief, plan=plan, names=Names(branch="owlbear/c1", target="main"),
               step=Step(kind=StepKind.BUILD, task="t1"))  # fmt: skip
    store.write(Lock("c1"), c.model_copy(update={"decisions_baseline": decisions_gate.pinned(store, c, AT)[0]}))

    got = owner.get(f"/api/next/decisions/{rule.id}").json()
    back = owner.get(f"/api/next/decisions/{old.id}").json()

    assert (got["origin"], got["actor"], got["source"]) == ("autonomous", "shaper", "chat")
    assert got["revision"] == rule.revision
    assert [(link["type"], link["id"], link["state"]) for link in got["links"]] == [("replaces", old.id, "replaced")]
    assert [(link["type"], link["id"]) for link in back["linked_from"]] == [("replaces", rule.id)]
    assert [h["subject"] for h in got["history"]] == ["seed"]
    assert [(p["slug"], p["applies"], p["revision"]) for p in got["changes"]] == [("c1", True, rule.revision)]
    assert owner.get(f"/api/next/decisions/{new_id()}").status_code == 404


def test_the_owner_replaces_a_decision_with_his_successor_and_gets_its_receipts(owner, shared, shared_repo):
    old = make()
    seed(shared, old)

    got = act(owner, old, "replace", statement="Notes live in Postgres.", words="Use Postgres.", reason="It grew.")
    got = got.json()

    new_id_ = got["receipts"][0]["id"]
    new = now(shared, new_id_)
    assert got["saved"] is True
    assert [(r["id"], r["saved"], r["committed"], r["published"]) for r in got["receipts"]] == [
        (new.id, True, True, True), (old.id, True, True, True)]  # fmt: skip
    assert got["receipts"][0]["active"] is True
    assert (new.state, new.origin) == (State.IN_FORCE, Origin.DECIDED)
    assert [w.text for w in new.owner_words] == ["Use Postgres."]
    assert new.links == (Link(type=LinkType.REPLACES, target=old.id),)
    assert (new.title, new.actor, new.rationale) == (old.title, "owner", "Why it changed: It grew.")
    assert now(shared, old.id).state is State.REPLACED  # kept, never deleted
    assert git(shared_repo[1], "log", "-1", "--format=%s", "main").startswith(f"decisions: {new.id} replaces {old.id}")
    one_commit = git(shared_repo[1], "show", "--name-only", "--format=", "main").splitlines()
    assert sorted(one_commit) == sorted(f"{PROJECT}/decisions/{d.id}.md" for d in (old, new))


def test_replacing_an_exception_keeps_its_exception_to_link(owner, shared):
    wide = worldwide()
    seed(shared, wide)
    mine = now(shared, act(owner, wide, "exception", statement="Build here.").json()["receipts"][0]["id"])

    got = act(owner, mine, "replace", statement="Build here, minified.", reason="Smaller pages.", redecide=True).json()

    new = now(shared, got["receipts"][0]["id"])
    assert got["saved"] is True
    assert new.links == (Link(type=LinkType.REPLACES, target=mine.id), Link(type=LinkType.EXCEPTION_TO, target=wide.id))
    assert got["receipts"][0]["active"] is True


@pytest.mark.parametrize("action", ["replace", "withdraw", "activate", "promote", "keep", "propose"])
def test_a_supersession_without_a_reason_is_refused_and_writes_nothing(owner, store, shared, action):
    old = make(state=State.REPLACED) if action == "keep" else make()
    rule = after(old, state=State.DRAFT) if action == "activate" else after(old, conflict=True)
    seed(shared, old, *([rule] if action in {"activate", "keep"} else []))
    head = git(shared.root, "rev-parse", "HEAD")
    target = rule if action in {"activate", "keep"} else old
    body = {"revisions": {rule.id: rule.revision}} if action == "keep" else {"revision": target.revision}
    body |= {"statement": "Other.", "reason": "  "} if action == "replace" else {}
    if action == "propose":
        got = client(store, CHAT).post("/api/next/decisions/propose",
                                       json={"title": "x", "statement": "x", "replaces": old.id})  # fmt: skip
    else:
        got = owner.post(f"/api/next/decisions/{target.id}/{action}", json=body)

    assert got.status_code == 422
    assert "say why" in got.json()["detail"]
    assert git(shared.root, "rev-parse", "HEAD") == head


def test_a_withdrawal_and_a_promotion_record_why(owner, shared):
    rule, source = make(rationale="Small data."), make(title="Tags", statement="Free tags.")
    seed(shared, rule, source)

    act(owner, rule, "withdraw", reason="No notes any more.")
    wide = now(shared, act(owner, source, "promote", reason="Every project wants it.").json()["receipts"][0]["id"])

    assert now(shared, rule.id).rationale == "Small data.\n\nWhy it was withdrawn: No notes any more."
    assert wide.rationale == "Why it changed: Every project wants it."
    assert "No notes any more." in git(shared.root, "log", "--format=%s")


def test_a_stale_revision_is_refused_by_its_receipt_and_nothing_is_written(owner, shared):
    old = make()
    seed(shared, old)
    head = git(shared.root, "rev-parse", "HEAD")

    got = owner.post(f"/api/next/decisions/{old.id}/replace",
                     json={"revision": "0" * 64, "statement": "Other.", "reason": "r"})  # fmt: skip

    assert got.status_code == 200
    assert (got.json()["saved"], got.json()["receipts"][0]["saved"]) == (False, False)
    assert "changed since it was read" in got.json()["receipts"][0]["notice"]
    assert (git(shared.root, "rev-parse", "HEAD"), now(shared, old.id).state) == (head, State.IN_FORCE)


def test_replacing_or_withdrawing_a_decided_decision_needs_the_owners_re_decision(owner, shared):
    rule = decided()
    seed(shared, rule)

    refused = act(owner, rule, "replace", statement="Notes live in Postgres.", reason="r")
    kept = act(owner, rule, "withdraw", reason="moot")
    redecided = act(owner, rule, "replace", statement="Notes live in Postgres.", redecide=True, reason="r")

    assert (refused.status_code, kept.status_code) == (409, 409)
    assert "re-decide" in refused.json()["detail"]
    assert redecided.json()["saved"] is True
    assert now(shared, rule.id).state is State.REPLACED


def test_a_second_reversal_is_the_owners_re_decision_only(owner, store, shared):
    chat = client(store, CHAT)
    first = make()
    seed(shared, first)
    proposal = {"title": "Notes", "statement": "Postgres.", "replaces": first.id, "reason": "r"}
    proposed = chat.post("/api/next/decisions/propose", json=proposal).json()
    draft = now(shared, proposed["receipts"][0]["id"])
    assert act(owner, draft, "activate", reason="r").json()["saved"] is True  # the first reversal: his approval
    second = now(shared, draft.id)
    assert (second.state, second.origin) == (State.IN_FORCE, Origin.APPROVED)

    again = {"title": "Notes", "statement": "A file.", "replaces": second.id, "reason": "r"}
    refused = chat.post("/api/next/decisions/propose", json=again)
    worded = chat.post("/api/next/decisions/propose", json=again | {"words": "Go back to a file."}).json()
    unworded = after(second, state=State.DRAFT, statement="A JSON file.")
    seed(shared, unworded)
    unconfirmed = act(owner, unworded, "activate", reason="r")
    confirmed = act(owner, unworded, "activate", redecide=True, reason="r").json()

    assert refused.status_code == 409
    assert "second reversal" in refused.json()["detail"]
    assert now(shared, worded["receipts"][0]["id"]).state is State.DRAFT  # in his words, still his to activate
    assert unconfirmed.status_code == 409
    assert confirmed["saved"] is True
    assert now(shared, unworded.id).origin is Origin.DECIDED
    assert decision_actions.reversals({d.id: d for d in (first, second)}, now(shared, unworded.id)) == 2


@pytest.mark.parametrize("action", ["replace", "withdraw", "activate", "promote", "exception", "keep"])
def test_a_chat_tool_never_takes_the_owners_actions(store, shared, action):
    rule = make(state=State.DRAFT) if action == "activate" else make()
    seed(shared, rule)
    body = {"revision": rule.revision, "statement": "x"} if action in {"replace", "exception"} else {}
    body = {"revisions": {rule.id: rule.revision}} if action == "keep" else body or {"revision": rule.revision}

    got = client(store, CHAT).post(f"/api/next/decisions/{rule.id}/{action}", json=body)

    assert got.status_code == 403
    assert now(shared, rule.id) == rule


def test_a_chat_proposal_is_always_a_draft_and_never_replaces_a_decided_or_global_one(store, shared):
    chat, rule, wide = client(store, CHAT), decided(), worldwide()
    seed(shared, rule, wide)

    plain = chat.post("/api/next/decisions/propose", json={"title": "Tags", "statement": "Tags are free."}).json()
    worded = chat.post("/api/next/decisions/propose", json={"title": "Tags", "statement": "Tags are free.",
                                                             "words": "Free tags."}).json()  # fmt: skip
    on_decided = chat.post("/api/next/decisions/propose", json={"title": "x", "statement": "x", "replaces": rule.id})
    on_global = chat.post("/api/next/decisions/propose", json={"title": "x", "statement": "x", "replaces": wide.id})

    one, two = now(shared, plain["receipts"][0]["id"]), now(shared, worded["receipts"][0]["id"])
    assert (one.state, one.origin) == (State.DRAFT, Origin.AUTONOMOUS)
    assert (two.state, two.origin) == (State.DRAFT, Origin.DECIDED)
    assert plain["receipts"][0]["active"] is False
    assert (on_decided.status_code, on_global.status_code) == (409, 422)


def test_promotion_makes_a_linked_global_successor_and_keeps_the_source(owner, shared):
    source = decided()
    seed(shared, source)

    got = act(owner, source, "promote", reason="Every project.").json()

    wide = now(shared, got["receipts"][0]["id"])
    kept = now(shared, source.id)
    assert got["saved"] is True
    assert (wide.scope, wide.state, wide.origin, wide.owner_words) == (
        Scope.GLOBAL, State.IN_FORCE, Origin.DECIDED, source.owner_words)  # fmt: skip
    assert wide.links == (Link(type=LinkType.PROMOTED_FROM, target=source.id),)
    assert (kept.state, kept.statement) == (State.REPLACED, source.statement)
    assert validate_repo(shared.root) == []
    assert act(owner, wide, "promote", reason="r").status_code == 422  # nothing is wider than Global
    assert decision_actions.reversals({source.id: source}, after(wide)) == 1  # lineage carries over


def test_an_exception_is_recorded_to_a_global_decision_only(owner, shared):
    wide, local = worldwide(), make()
    seed(shared, wide, local)

    refused = act(owner, local, "exception", statement="Here too.")
    got = act(owner, wide, "exception", statement="This project builds its pages.", words="Build them here.").json()

    mine = now(shared, got["receipts"][0]["id"])
    assert refused.status_code == 422
    assert (mine.scope, mine.project) == (Scope.PROJECT, PROJECT)
    assert (mine.origin, mine.state) == (Origin.DECIDED, State.IN_FORCE)
    assert mine.links == (Link(type=LinkType.EXCEPTION_TO, target=wide.id),)
    assert now(shared, wide.id).state is State.IN_FORCE


def test_resolving_a_conflict_leaves_exactly_one_successor_in_force(owner, shared):
    old = make(state=State.REPLACED)
    ours, theirs = after(old, title="Ours", conflict=True), after(old, title="Theirs", conflict=True)
    seed(shared, old, ours, theirs)

    calm = act(owner, old, "keep")
    stale = owner.post(f"/api/next/decisions/{ours.id}/keep",
                       json={"revisions": {ours.id: ours.revision}, "reason": "r"})  # fmt: skip
    both = {ours.id: ours.revision, theirs.id: theirs.revision}
    got = owner.post(f"/api/next/decisions/{ours.id}/keep", json={"revisions": both, "reason": "Ours is simpler."})
    got = got.json()

    assert calm.status_code == 422  # a malformed body: keep names revisions by id
    assert stale.json()["saved"] is False
    assert got["saved"] is True
    view = decision_store.load(shared, PROJECT).snapshot
    assert [e.decision.title for e in view.entries if e.decision.state is State.IN_FORCE] == ["Ours"]
    assert (view.get(theirs.id).decision.state, view.get(ours.id).decision.conflict) == (State.WITHDRAWN, False)
    assert view.get(theirs.id).decision.rationale == f"Why it was withdrawn: {ours.id} was kept: Ours is simpler."
    assert view.active(ours.id)
    assert owner.post(f"/api/next/decisions/{ours.id}/keep", json={"revisions": {}, "reason": "r"}).status_code == 409


def test_a_read_back_records_its_date_and_never_changes_the_origin(store, shared):
    rule, gone = make(), make(state=State.WITHDRAWN)
    seed(shared, rule, gone)

    got = act(client(store, CHAT), rule, "read-back", answer="Still right.").json()

    read = now(shared, rule.id)
    assert got["saved"] is True
    assert (read.read_back, read.origin, read.statement) == (
        datetime.now(UTC).date().isoformat(), Origin.AUTONOMOUS, rule.statement)  # fmt: skip
    assert "(chat): Still right." in git(shared.root, "log", "-1", "--format=%s")
    assert act(client(store, CHAT), gone, "read-back", answer="x").status_code == 409


def test_withdrawing_a_draft_or_a_decision_in_force_keeps_it_in_history(owner, shared):
    draft, rule = make(state=State.DRAFT), make(title="Exports are CSV")
    seed(shared, draft, rule)

    assert act(owner, draft, "withdraw", reason="Not needed.").json()["saved"] is True
    assert act(owner, rule, "withdraw", reason="No exports any more.").json()["saved"] is True

    assert (now(shared, draft.id).state, now(shared, rule.id).state) == (State.WITHDRAWN, State.WITHDRAWN)
    assert listed(owner) == []
    assert len(listed(owner, retired="true")) == 2


@pytest.fixture
def chat(store, monkeypatch) -> mcp_server.Chat:
    """The chat tools of a clone whose host answers in-process, every call marked as the chat's."""
    http = client(store, CHAT)
    tools = mcp_server.Chat.__new__(mcp_server.Chat)
    tools.store = store

    def call(method: str, path: str, body: object = None) -> tuple[int, Any]:
        r = http.request(method, f"/api/next{path}", json=body)
        return r.status_code, r.json()

    tools.call = call
    monkeypatch.setitem(mcp_server._STATE, "chat", tools)  # noqa: SLF001 - the server's one chat
    return tools


def tool(name: str, **args: object) -> dict[str, Any]:
    result = asyncio.run(mcp_server.mcp.call_tool(name, args))
    assert result.is_error is False, result.content
    return result.structured_content


@pytest.mark.usefixtures("chat")
def test_find_decisions_matches_text_scope_and_retired_ones_with_the_revision_a_read_back_names(shared):
    rule, wide, gone = make(), worldwide(), make(title="Old export", statement="CSV.", state=State.WITHDRAWN)
    seed(shared, rule, wide, gone)

    found = tool("find_decisions", text="sqlite")
    everything = tool("find_decisions", where="project", include_retired=True)

    assert found["found"] is True
    assert [(d["id"], d["revision"]) for d in found["decisions"]] == [(rule.id, rule.revision)]
    assert set(found["decisions"][0]) == set(mcp_server.SHORT)
    assert [d["title"] for d in tool("find_decisions", where="global")["decisions"]] == [wide.title]
    assert {d["id"] for d in everything["decisions"]} == {rule.id, gone.id}
    assert everything["more"] == 0


@pytest.mark.usefixtures("chat")
def test_find_decisions_counts_what_it_leaves_out(shared, monkeypatch):
    seed(shared, make(), make(title="Tags", statement="Free."), make(title="Exports", statement="CSV."))
    monkeypatch.setattr(mcp_server, "FOUND", 2)
    got = tool("find_decisions")
    assert (len(got["decisions"]), got["more"]) == (2, 1)


@pytest.mark.usefixtures("chat")
def test_record_decision_is_always_a_draft_decided_only_in_the_owners_words(shared):
    plain = tool("record_decision", title="Tags", statement="Tags are free text.")
    worded = tool("record_decision", title="Tags", statement="Tags are free text.", owner_words="Free tags, yes.")

    one, two = now(shared, plain["receipts"][0]["id"]), now(shared, worded["receipts"][0]["id"])
    assert plain["saved"] is True
    assert (one.state, one.origin, one.actor) == (State.DRAFT, Origin.AUTONOMOUS, "chat")
    assert (two.state, two.origin) == (State.DRAFT, Origin.DECIDED)
    assert [w.text for w in two.owner_words] == ["Free tags, yes."]
    assert "decisions_page" in plain


@pytest.mark.usefixtures("chat")
def test_record_decision_never_replaces_a_decided_decision(shared):
    rule = decided()
    seed(shared, rule)
    got = tool("record_decision", title="Notes", statement="Postgres.", replaces=rule.id, owner_words="Postgres.")
    assert got["saved"] is False
    assert "re-decides it on the Decisions page" in got["error"]
    assert now(shared, rule.id) == rule


@pytest.mark.usefixtures("chat")
def test_record_decision_says_why_a_draft_replaces_one(shared):
    rule = make()
    seed(shared, rule)
    bare = tool("record_decision", title="Notes", statement="Postgres.", replaces=rule.id)
    got = tool("record_decision", title="Notes", statement="Postgres.", replaces=rule.id, rationale="It grew.")
    assert (bare["saved"], "say why" in bare["error"]) == (False, True)
    assert now(shared, got["receipts"][0]["id"]).rationale == "Why it changed: It grew."


@pytest.mark.usefixtures("chat")
def test_read_back_decision_records_the_date_and_a_stale_revision_is_refused(shared):
    rule = make()
    seed(shared, rule)

    stale = tool("read_back_decision", decision=rule.id, revision="0" * 64, answer="Still right.")
    got = tool("read_back_decision", decision=rule.id, revision=rule.revision, answer="Still right.")

    assert (stale["saved"], got["saved"]) == (False, True)
    assert now(shared, rule.id).read_back == datetime.now(UTC).date().isoformat()


def test_the_tools_say_why_when_the_host_is_down(chat):
    chat.call = lambda *_a, **_k: (503, {"error": "the host is not running"})
    assert tool("find_decisions") == {"found": False, "error": "the host is not running"}
    assert tool("record_decision", title="x", statement="x")["error"] == "the host is not running"
