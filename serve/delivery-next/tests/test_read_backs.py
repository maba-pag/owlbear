"""The read-back queue (TD-427) and OwlBear's own scope (TD-435): who queues, the owner's answers, the checkpoints."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient
from mcp.server.mcpserver.exceptions import ToolError

from owlbear_decisions import Applicability, Decision, Origin, Scope, State, new_id, write
from owlbear_delivery_next.change_contracts.models import Brief, Change, Exit, Names, Plan, Step, StepKind, Task
from owlbear_delivery_next.commands import mcp_server
from owlbear_delivery_next.local_system.codebase import CURRENT
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.project_host import api
from owlbear_delivery_next.project_host.host import HostRecord
from owlbear_delivery_next.state_store import decision_store
from owlbear_delivery_next.state_store.store import Lock, Store
from owlbear_delivery_next.workflow_steps import decisions_gate

AT = datetime(2026, 10, 21, 9, tzinfo=UTC)
PROJECT = "shop-site"
AUTH = {"authorization": "Bearer t"}
CHAT = AUTH | {"x-owlbear-use": "chat"}
TODAY = datetime.now(UTC).date().isoformat()


class Host:
    wake = SimpleNamespace(set=lambda: None)
    record = HostRecord(url="http://127.0.0.1:9/", token="tok", pid=1, started_at=datetime.now(UTC), code=CURRENT)  # noqa: S106

    def activity(self, _slug: str) -> Any:
        from owlbear_delivery_next.change_flow.status import Activity  # noqa: PLC0415

        return Activity(host_up=True)


def make(**changes) -> Decision:
    fields = {
        "id": new_id(), "title": "Notes live in SQLite", "statement": "Notes live in one SQLite table.",
        "scope": Scope.PROJECT, "project": PROJECT, "origin": Origin.AUTONOMOUS, "actor": "shaper",
        "state": State.IN_FORCE, "created_at": AT,
    }  # fmt: skip
    return Decision(**{**fields, **changes})


def waiting(kind: str, why: str = "The vendor changed its terms.", **changes) -> Decision:
    return make(read_back="pending", read_back_why=why, read_back_kind=kind, **changes)


def put(shared: DataRepo, *decisions: Decision) -> None:
    for d in decisions:
        write(d, shared.root if d.scope is Scope.GLOBAL else shared.root / d.project)


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


def now(shared: DataRepo, decision_id: str, project: str = PROJECT) -> Decision:
    return decision_store.load(shared, project).snapshot.get(decision_id).decision


def queue(c: TestClient, **query) -> list[dict[str, Any]]:
    return c.get("/api/next/decisions", params=query).json()["queue"]


@pytest.fixture
def chat(store, monkeypatch) -> mcp_server.Chat:
    http = client(store, CHAT)
    tools = mcp_server.Chat.__new__(mcp_server.Chat)
    tools.store = store

    def call(method: str, path: str, body: object = None) -> tuple[int, Any]:
        r = http.request(method, f"/api/next{path}", json=body)
        return r.status_code, r.json()

    tools.call = call
    monkeypatch.setitem(mcp_server._STATE, "chat", tools)  # noqa: SLF001 - the server's one chat
    return tools


def tool(name: str, **args: object):
    return asyncio.run(mcp_server.mcp.call_tool(name, args))


def test_the_queue_leads_the_list_by_kind_then_oldest_and_a_conflict_queues_itself(owner, shared):
    later = AT + timedelta(days=1)
    gap, doubt = waiting("improvement", created_at=AT), waiting("uncertain", created_at=later)
    flagged, quiet = make(conflict=True, created_at=later), make(title="Tags are free text")
    put(shared, gap, doubt, flagged, quiet)

    got = queue(owner)

    assert [(q["id"], q["kind"], q["derived"]) for q in got] == [
        (flagged.id, "blocked", True), (doubt.id, "uncertain", False), (gap.id, "improvement", False)]  # fmt: skip
    assert now(shared, flagged.id) == flagged  # derived: nothing written
    assert got[1]["why"] == "The vendor changed its terms."


@pytest.mark.usefixtures("chat")
def test_queue_read_back_sets_pending_with_why_and_kind_and_never_touches_origin_wording_or_state(shared):
    rule = make(origin=Origin.DECIDED, read_back=AT.date().isoformat(), inherited=True)
    put(shared, rule)

    got = tool("queue_read_back", decision=rule.id, revision=rule.revision, why="A second team now edits notes.",
               kind="uncertain")  # fmt: skip

    assert got.structured_content["saved"] is True
    held = now(shared, rule.id)
    assert (held.read_back, held.read_back_why, held.read_back_kind) == ("pending", "A second team now edits notes.",
                                                                       "uncertain")  # fmt: skip
    assert (held.origin, held.statement, held.state, held.inherited) == (
        rule.origin, rule.statement, rule.state, rule.inherited)  # fmt: skip
    said = shared.git("log", "-1", "--format=%B").stdout.strip()
    assert said == f"decisions: queue-read-back {rule.id} (uncertain)"  # the reason stays in the file only


@pytest.mark.usefixtures("chat")
def test_queue_read_back_refuses_an_empty_why_an_unknown_kind_and_the_same_reason_twice(shared, owner):
    rule = make()
    put(shared, rule)

    with pytest.raises(ToolError, match="at least 1 character"):
        tool("queue_read_back", decision=rule.id, revision=rule.revision, why="", kind="uncertain")
    with pytest.raises(ToolError, match="kind"):
        tool("queue_read_back", decision=rule.id, revision=rule.revision, why="New data.", kind="someday")
    with pytest.raises(ToolError, match="revision"):
        tool("queue_read_back", decision=rule.id, why="New data.", kind="uncertain")
    blank = owner.post(f"/api/next/decisions/{rule.id}/queue-read-back",
                       json={"why": "  ", "kind": "safety", "revision": rule.revision})  # fmt: skip
    unread = owner.post(f"/api/next/decisions/{rule.id}/queue-read-back", json={"why": "New data.", "kind": "safety"})
    assert (blank.status_code, unread.status_code) == (422, 422)
    assert now(shared, rule.id) == rule

    first = tool("queue_read_back", decision=rule.id, revision=rule.revision, why="New data.", kind="uncertain")
    assert first.structured_content["saved"]
    held = now(shared, rule.id)
    again = tool("queue_read_back", decision=rule.id, revision=held.revision, why=" new  DATA. ",
                 kind="uncertain").structured_content  # fmt: skip
    assert (again["saved"], "already" in again["error"]) == (False, True)
    assert now(shared, rule.id) == held


@pytest.mark.usefixtures("chat")
def test_queue_read_back_against_a_stale_revision_is_refused_and_writes_nothing(shared):
    rule = make()
    put(shared, rule)
    newer = rule.model_copy(update={"rationale": "One table keeps backups simple."})
    write(newer, shared.root / PROJECT, rule.revision)

    got = tool("queue_read_back", decision=rule.id, revision=rule.revision, why="New data.", kind="safety")

    said = got.structured_content
    assert said["saved"] is False
    assert "changed since it was read" in said["receipts"][0]["notice"]
    assert now(shared, rule.id) == newer


def test_still_right_records_the_date_keeps_the_reason_answered_and_keeps_origin(owner, shared):
    rule = waiting("blocked", origin=Origin.APPROVED)
    put(shared, rule)

    said = owner.post(f"/api/next/decisions/{rule.id}/read-back", json={"revision": rule.revision,
                                                                          "confirmed": True}).json()  # fmt: skip

    assert said["saved"] is True
    held = now(shared, rule.id)
    assert (held.read_back, held.read_back_why, held.read_back_kind) == (TODAY, rule.read_back_why, "blocked")
    assert (held.origin, held.statement, held.state) == (Origin.APPROVED, rule.statement, State.IN_FORCE)
    assert held.rule_revision == rule.rule_revision
    assert queue(owner) == []
    same = owner.post(f"/api/next/decisions/{rule.id}/queue-read-back", json={
        "why": rule.read_back_why, "kind": "blocked", "revision": held.revision})  # fmt: skip
    assert (same.status_code, "already" in same.json()["detail"]) == (409, True)  # consent stands
    other = owner.post(f"/api/next/decisions/{rule.id}/queue-read-back", json={
        "why": "The law changed.", "kind": "safety", "revision": held.revision})  # fmt: skip
    assert other.json()["saved"] is True


def test_the_reason_answered_yesterday_is_not_queued_again_today_and_a_new_one_is(owner, shared):
    yesterday = (datetime.now(UTC).date() - timedelta(days=1)).isoformat()
    rule = make(read_back=yesterday, read_back_why="The vendor changed its terms.", read_back_kind="blocked")
    put(shared, rule)

    def ask(why: str) -> Any:
        body = {"why": why, "kind": "uncertain", "revision": now(shared, rule.id).revision}
        return owner.post(f"/api/next/decisions/{rule.id}/queue-read-back", json=body)

    same = ask("the vendor  changed its TERMS.")
    assert (same.status_code, "already" in same.json()["detail"]) == (409, True)
    assert now(shared, rule.id) == rule
    assert ask("The vendor was bought.").json()["saved"] is True
    held = now(shared, rule.id)
    assert (held.read_back, held.read_back_why, held.read_back_kind) == ("pending", "The vendor was bought.",
                                                                       "uncertain")  # fmt: skip


def test_ignore_for_now_writes_nothing_keeps_the_rule_in_force_and_moves_it_last(owner, shared, store):
    first, second = waiting("safety", created_at=AT), waiting("improvement", created_at=AT + timedelta(days=1))
    put(shared, first, second)

    chat = client(store, CHAT).post(f"/api/next/decisions/{first.id}/ignore-read-back",
                                    json={"revision": first.revision})  # fmt: skip
    done = owner.post(f"/api/next/decisions/{first.id}/ignore-read-back", json={"revision": first.revision})

    assert chat.status_code == 403
    assert done.json()["ignored"] == first.id
    assert now(shared, first.id) == first
    assert decision_store.load(shared, PROJECT).snapshot.active(first.id) is True
    assert [(q["id"], q["ignored"]) for q in queue(owner)] == [(second.id, False), (first.id, True)]


def awaiting(scope: tuple[str, ...] = ("web",)) -> Change:
    brief = Brief(version=2, approved_version=None, title="Notes", outcome="Notes show.", scope=list(scope))
    return Change(slug="notes", brief=brief, step=Step(kind=StepKind.SHAPE))


def test_the_approval_view_shows_at_most_three_applying_read_backs_and_counts_the_rest(owner, shared, store):
    applying = [waiting(k, created_at=AT + timedelta(minutes=i)) for i, k in
                enumerate(("improvement", "safety", "uncertain", "blocked"))]  # fmt: skip
    elsewhere = waiting("safety", applies_to=Applicability(paths=("api/**",)))
    put(shared, *applying, elsewhere)
    store.write(Lock("notes"), awaiting())

    got = owner.get("/api/next/changes/notes").json()["brief"]["read_backs"]

    assert [i["kind"] for i in got["items"]] == ["safety", "blocked", "uncertain"]
    assert elsewhere.id not in {i["id"] for i in got["items"]}
    assert got["more"] == 1
    approved = awaiting().model_copy(update={"brief": awaiting().brief.model_copy(update={"approved_version": 2})})
    store.write(Lock("notes"), approved)
    assert owner.get("/api/next/changes/notes").json()["brief"]["read_backs"] is None


def test_the_gate_question_lists_at_most_three_applying_read_backs_and_never_blocks_on_them(tmp_path, shared):
    rule = make(title="Pages are plain HTML", statement="No build step.")
    put(shared, rule, *(waiting(k) for k in ("safety", "blocked", "uncertain", "improvement")))
    brief = Brief(version=1, approved_version=1, challenged=1, approved_at=AT, title="Notes", scope=["web"])
    plan = Plan(tasks=[Task(id="t1", title="Show notes", scope=["web"], checks=["true"])])
    c = Change(slug="c1", brief=brief, plan=plan, names=Names(branch="owlbear/c1", target="main"),
               step=Step(kind=StepKind.BUILD, task="t1"))  # fmt: skip
    store = Store(tmp_path / "gate", shared, PROJECT)
    c = c.model_copy(update={"decisions_baseline": decisions_gate.pinned(store, c, AT)[0]})

    assert decisions_gate.check_step(store, c, AT).result is None  # read-backs alone never stop a step
    write(rule.model_copy(update={"state": State.WITHDRAWN}), shared.root / PROJECT, rule.revision)
    asked = decisions_gate.check_step(store, c, AT).result

    assert asked.exit is Exit.ASK
    lines = asked.question.text.splitlines()
    assert decisions_gate.WAITING in lines
    assert sum(line.startswith(("- safety", "- blocked", "- uncertain", "- improvement")) for line in lines) == 3
    assert "1 more wait on the Decisions page." in lines


def test_the_owlbear_scope_lists_owlbears_and_global_decisions_and_the_owner_acts_on_them(owner, shared):
    ours, wide, mine = make(project="owlbear", title="Lint once"), make(scope=Scope.GLOBAL, project=""), make()
    put(shared, ours, wide, mine)

    listed = owner.get("/api/next/decisions", params={"where": "owlbear"}).json()
    entry = owner.get(f"/api/next/decisions/{ours.id}", params={"where": "owlbear"})
    missing = owner.get(f"/api/next/decisions/{ours.id}")
    done = owner.post(f"/api/next/decisions/{ours.id}/withdraw", params={"where": "owlbear"},
                      json={"revision": ours.revision, "reason": "Linting moved to CI."})  # fmt: skip

    assert listed["project"] == "owlbear"
    assert {d["id"] for d in listed["decisions"]} == {ours.id, wide.id}
    assert (entry.status_code, missing.status_code) == (200, 404)
    assert done.json()["saved"] is True
    assert now(shared, ours.id, "owlbear").state is State.WITHDRAWN
    assert not (shared.root / PROJECT / "decisions" / f"{ours.id}.md").exists()
