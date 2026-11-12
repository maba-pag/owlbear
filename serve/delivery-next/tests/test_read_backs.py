"""The read-back queue (TD-427) and OwlBear's own scope (TD-435): who queues, the owner's answers, the checkpoints."""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient
from mcp.server.mcpserver.exceptions import ToolError

from owlbear_decisions import Decision, Origin, Scope, State, new_id, write
from owlbear_delivery_next.change_contracts.models import Brief, Change, Names, Plan, Step, StepKind, Task
from owlbear_delivery_next.change_flow import loop
from owlbear_delivery_next.commands import chat_client, mcp_server
from owlbear_delivery_next.local_system.codebase import CURRENT
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.project_host import api
from owlbear_delivery_next.project_host.host import HostRecord
from owlbear_delivery_next.state_store import decision_actions, decision_origin, decision_store
from owlbear_delivery_next.state_store.store import Lock, Store
from owlbear_delivery_next.workflow_steps import decisions_gate

AT = datetime(2026, 10, 21, 9, tzinfo=UTC)
PROJECT = "shop-site"
AUTH = {"authorization": "Bearer t"}
CHAT = AUTH | {"x-owlbear-use": "chat"}
TODAY = datetime.now(UTC).date().isoformat()


class Host:
    maintenance = None
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
def owner(store) -> Iterator[TestClient]:
    with client(store) as http:
        yield http


def now(shared: DataRepo, decision_id: str, project: str = PROJECT) -> Decision:
    return decision_store.load(shared, project).snapshot.get(decision_id).decision


def queue(c: TestClient, **query) -> list[dict[str, Any]]:
    return c.get("/api/next/decisions", params=query).json()["queue"]


@pytest.fixture
def chat(store, monkeypatch) -> Iterator[chat_client.Chat]:
    with client(store, CHAT) as http:
        tools = chat_client.Chat.__new__(chat_client.Chat)
        tools.repo, tools.home = Path(), store.root

        def call(method: str, path: str, body: object = None, timeout: float = 15.0,  # noqa: ARG001
                 headers: dict[str, str] | None = None) -> tuple[int, Any]:  # fmt: skip
            r = http.request(method, f"/api/next{path}", json=body, headers=headers)
            return r.status_code, r.json()

        tools.call = call
        monkeypatch.setitem(mcp_server._STATE, "chat", tools)  # noqa: SLF001 - the server's one chat
        yield tools


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
def test_queue_read_back_refuses_an_empty_why_an_unknown_kind_and_the_same_reason_twice(shared, owner):
    rule = make(origin=Origin.DECIDED, read_back=AT.date().isoformat(), inherited=True)
    put(shared, rule)
    head = shared.git("rev-parse", "HEAD").stdout.strip()

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
    assert shared.git("rev-parse", "HEAD").stdout.strip() == head

    newer = rule.model_copy(update={"rationale": "One table keeps backups simple."})
    write(newer, shared.root / PROJECT, rule.revision)
    stale = tool("queue_read_back", decision=rule.id, revision=rule.revision,
                 why="New data.", kind="safety").structured_content  # fmt: skip
    assert stale["saved"] is False
    assert stale["receipts"][0]["notice"] == (
        f"{rule.id} changed since it was read (now {newer.revision[:12]}); reload and decide again"
    )
    assert now(shared, rule.id) == newer
    assert shared.git("rev-parse", "HEAD").stdout.strip() == head

    first = tool("queue_read_back", decision=rule.id, revision=newer.revision, why="New data.", kind="uncertain")
    assert first.structured_content["saved"]
    held = now(shared, rule.id)
    assert (held.read_back, held.read_back_why, held.read_back_kind) == ("pending", "New data.", "uncertain")
    assert (held.origin, held.statement, held.state, held.inherited) == (
        rule.origin,
        rule.statement,
        rule.state,
        rule.inherited,
    )
    assert shared.git("log", "-1", "--format=%B").stdout.strip() == (
        f"decisions: queue-read-back {rule.id} (uncertain)"
    )
    head = shared.git("rev-parse", "HEAD").stdout.strip()
    again = tool("queue_read_back", decision=rule.id, revision=held.revision, why=" new  DATA. ",
                 kind="uncertain").structured_content  # fmt: skip
    assert (again["saved"], "already" in again["error"]) == (False, True)
    assert now(shared, rule.id) == held
    assert shared.git("rev-parse", "HEAD").stdout.strip() == head


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


def confirmed_reason(owner, shared, current, why, kind="uncertain"):
    """Queue and confirm through the real owner API."""
    ident = current.id
    queued = owner.post(
        f"/api/next/decisions/{ident}/queue-read-back",
        json={"revision": current.revision, "why": why, "kind": kind},
    )
    receipt = queued.json()
    assert receipt["saved"] is True
    revision = receipt["receipts"][0]["revision"]
    confirmed = owner.post(f"/api/next/decisions/{ident}/read-back", json={"revision": revision, "confirmed": True})
    assert confirmed.json()["saved"] is True
    return now(shared, ident)


def test_a_then_b_confirmation_remembers_a_after_real_shared_clone_and_host_reload(
    owner, shared, shared_repo, tmp_path
):
    rule = make(origin=Origin.APPROVED)
    put(shared, rule)
    first = confirmed_reason(owner, shared, rule, "The vendor changed its terms.", kind="blocked")
    assert (first.read_back, first.read_back_why, first.read_back_kind) == (
        TODAY,
        "The vendor changed its terms.",
        "blocked",
    )
    assert (first.origin, first.statement, first.state) == (Origin.APPROVED, rule.statement, State.IN_FORCE)
    assert first.rule_revision == rule.rule_revision
    assert queue(owner) == []
    confirmed_reason(owner, shared, first, "A second team now uses notes.")
    other_path = tmp_path / "other-data"
    copied = shared.git("clone", "-q", str(shared_repo[1]), str(other_path))
    assert copied.returncode == 0, copied.stderr
    other = DataRepo(other_path)
    for key, value in (("user.name", "t"), ("user.email", "t@example.com")):
        assert other.git("config", key, value).returncode == 0
    with client(Store(tmp_path / "other-host", other, PROJECT)) as other_owner:
        before = now(other, rule.id)

        repeated = other_owner.post(
            f"/api/next/decisions/{rule.id}/queue-read-back",
            json={"revision": before.revision, "why": "  the VENDOR  changed its TERMS. ", "kind": "safety"},
        )

        assert repeated.status_code == 409
        assert "already" in repeated.json()["detail"]
        assert now(other, rule.id) == before
        stale = other_owner.post(
            f"/api/next/decisions/{rule.id}/queue-read-back",
            json={"revision": first.revision, "why": "A new regulation now covers notes.", "kind": "safety"},
        )
        assert stale.json()["saved"] is False
        assert now(other, rule.id) == before
        fresh = other_owner.post(
            f"/api/next/decisions/{rule.id}/queue-read-back",
            json={"revision": before.revision, "why": "A new regulation now covers notes.", "kind": "safety"},
        )
        assert fresh.json()["saved"] is True
        current = now(other, rule.id)
        assert current.read_back_settled == ("the vendor changed its terms.", "a second team now uses notes.")
        assert current.rule_revision == rule.rule_revision


@pytest.mark.parametrize("pending", [False, True])
def test_origin_only_correction_preserves_prior_consent_without_confirming_pending_reason(owner, shared, pending):
    # As the owner API leaves it: A confirmed, then B queued; B pending, or replaced by C, queued and confirmed.
    latest = {"read_back": "pending", "read_back_why": "A second team now uses notes.", "read_back_kind": "blocked"}
    if not pending:
        latest = {"read_back": TODAY, "read_back_why": "A third team now uses notes.", "read_back_kind": "uncertain"}
    rule = make(origin=Origin.DECIDED, read_back_settled=("the vendor changed its terms.",), **latest)
    put(shared, rule)
    current = now(shared, rule.id)
    receipts = decision_origin.correct_origin(
        shared,
        PROJECT,
        current.id,
        current.revision,
        origin=Origin.APPROVED,
        reason="It came with an approved proposal, not an owner choice.",
        confirmed=True,
        by="owner",
    )
    successor = now(shared, receipts[0].id)
    assert successor.id != rule.id
    assert successor.read_back == current.read_back
    repeated = owner.post(
        f"/api/next/decisions/{successor.id}/queue-read-back",
        json={"revision": successor.revision, "why": "THE VENDOR changed its terms.", "kind": "safety"},
    )
    assert repeated.status_code == 409
    assert now(shared, successor.id) == successor


@pytest.mark.parametrize("mutation", ["replace", "promote"])
def test_a_changed_rule_does_not_inherit_settled_reasons(owner, shared, mutation):
    # As the owner API leaves it after confirming A, then B: B answered today, A's normalized reason settled.
    rule = make(read_back=TODAY, read_back_why="A second team now uses notes.", read_back_kind="uncertain",
                read_back_settled=("the vendor changed its terms.",))  # fmt: skip
    put(shared, rule)
    current = now(shared, rule.id)
    if mutation == "replace":
        receipts = decision_actions.replace(
            shared,
            PROJECT,
            current.id,
            current.revision,
            title="Notes live in PostgreSQL",
            statement="Notes live in one PostgreSQL table.",
            rationale="",
            reason="The owner changed the storage rule.",
            redecided=True,
        )
    else:
        receipts = decision_actions.promote(
            shared, PROJECT, current.id, current.revision, reason="The rule now applies across projects."
        )
    new = now(shared, receipts[0].id)
    queued = owner.post(
        f"/api/next/decisions/{new.id}/queue-read-back",
        json={"revision": new.revision, "why": "The vendor changed its terms.", "kind": "uncertain"},
    )
    assert queued.json()["saved"] is True


def test_ignore_for_now_writes_nothing_keeps_the_rule_in_force_and_moves_it_last(owner, shared, store):
    first = waiting("safety", why="The vendor changed its terms.", created_at=AT)
    second = waiting("improvement", created_at=AT + timedelta(days=1))
    put(shared, first, second)

    chat = client(store, CHAT).post(f"/api/next/decisions/{first.id}/ignore-read-back",
                                    json={"revision": first.revision})  # fmt: skip
    done = owner.post(f"/api/next/decisions/{first.id}/ignore-read-back", json={"revision": first.revision})

    assert chat.status_code == 403
    assert done.json()["ignored"] == first.id
    assert now(shared, first.id) == first
    assert decision_store.load(shared, PROJECT).snapshot.active(first.id) is True
    assert [(q["id"], q["ignored"]) for q in queue(owner)] == [(second.id, False), (first.id, True)]
    current = confirmed_reason(owner, shared, first, "A second team now uses notes.")
    again = owner.post(
        f"/api/next/decisions/{first.id}/queue-read-back",
        json={"revision": current.revision, "why": "The vendor changed its terms.", "kind": "safety"},
    )
    assert again.json()["saved"] is True


def awaiting(scope: tuple[str, ...] = ("web",)) -> Change:
    brief = Brief(version=2, approved_version=None, title="Notes", outcome="Notes show.", scope=list(scope))
    return Change(slug="notes", brief=brief, step=Step(kind=StepKind.SHAPE))


def test_the_approval_view_shows_at_most_three_applying_read_backs_and_counts_the_rest(owner, shared, store):
    applying = [waiting(k, created_at=AT + timedelta(minutes=i)) for i, k in
                enumerate(("improvement", "safety", "uncertain", "blocked"))]  # fmt: skip
    other = "20261021-090000-other"  # another Change's own decision is not in force for this one
    elsewhere = waiting("safety", scope=Scope.CHANGE, change=other)
    put(shared, *applying)
    write(elsewhere, shared.root / PROJECT / "changes" / other)
    store.write(Lock("notes"), awaiting())

    got = owner.get("/api/next/changes/notes").json()["brief"]["read_backs"]

    assert [i["kind"] for i in got["items"]] == ["safety", "blocked", "uncertain"]
    assert elsewhere.id not in {i["id"] for i in got["items"]}
    assert got["more"] == 1
    approved = awaiting().model_copy(update={"brief": awaiting().brief.model_copy(update={"approved_version": 2})})
    store.write(Lock("notes"), approved)
    assert owner.get("/api/next/changes/notes").json()["brief"]["read_backs"] is None


def test_read_backs_never_block_a_step_or_its_adoption_of_changed_decisions(tmp_path, shared):
    rule = make(title="Pages are plain HTML", statement="No build step.")
    put(shared, rule, *(waiting(k) for k in ("safety", "blocked", "uncertain", "improvement")))
    brief = Brief(version=1, approved_version=1, challenged=1, approved_at=AT, title="Notes", scope=["web"])
    plan = Plan(tasks=[Task(id="t1", title="Show notes", scope=["web"], checks=["true"])])
    c = Change(slug="c1", brief=brief, plan=plan, names=Names(branch="owlbear/c1", target="main"),
               step=Step(kind=StepKind.BUILD, task="t1"))  # fmt: skip
    store = Store(tmp_path / "gate", shared, PROJECT)
    pinned = decisions_gate.pinned(store, c, AT, decisions_gate.loaded(store))[0]
    c = c.model_copy(update={"decisions_baseline": pinned})

    assert decisions_gate.check_step(store, c, AT).result is None  # read-backs alone never stop a step
    write(rule.model_copy(update={"state": State.WITHDRAWN}), shared.root / PROJECT, rule.revision)
    gate = decisions_gate.check_step(store, c, AT)

    assert (gate.result, gate.pinned, gate.change.questions) == (None, True, [])
    assert rule.id not in gate.change.decisions_baseline.revisions
    assert f"no longer in force: {rule.id}" in "\n".join(gate.adopted)
    assert decisions_gate.WAITING not in gate.adopted
    assert loop.next_step(gate.change, AT) == c.step
    pending = decisions_gate.waiting(store, decisions_gate.loaded(store), gate.change)
    assert [q.kind for q in pending] == ["safety", "blocked", "uncertain", "improvement"]


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
