"""Answers during the work, classed by their relayer (TD-461; decision-intent-build §2, slice 5).

A Change is shaped, picked and approved through the host API (`picking`), then waits on its builder's question. The
owner's answer comes from the Changes page or a lead chat as an event, a clarification or a brief change.
"""

import asyncio
import io
import urllib.error
import urllib.parse
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from owlbear_decisions import Decision, Origin, Scope, State, new_id
from owlbear_delivery_next.change_contracts import pick_tools, tools
from owlbear_delivery_next.change_contracts.models import ErrorKind, Exit, Plan, Question, Step, StepKind, Task
from owlbear_delivery_next.change_flow import answer_kinds, loop
from owlbear_delivery_next.commands import mcp_server, runner
from owlbear_delivery_next.local_system.codebase import CURRENT
from owlbear_delivery_next.project_host import answers
from owlbear_delivery_next.project_host.host import HostRecord
from owlbear_delivery_next.runtimes import step_decisions, step_input
from owlbear_delivery_next.state_store import decision_archive
from owlbear_delivery_next.state_store.store import Lock
from owlbear_delivery_next.workflow_steps import clarification

AT = datetime(2026, 10, 22, 9, tzinfo=UTC)
ASKED = "Which language does the greeting use?"
WORDS = "english i guess, most readers are in canada"  # the owner's words: never a decision
SAID = "The greeting is in English."  # his intent as he confirmed it
RECORD = HostRecord(url="http://127.0.0.1:9/", token="t", pid=1, started_at=AT, code=CURRENT)  # noqa: S106


def rule() -> Decision:
    return Decision(
        id=new_id(), title="Pages are plain HTML", statement="The pages are plain HTML with no build step.",
        scope=Scope.PROJECT, project="shop-site", origin=Origin.APPROVED, actor="shaper", state=State.IN_FORCE,
        created_at=AT, topic="pages",
    )  # fmt: skip


def verdict(*, changes: bool = False, why: str = "It settles a detail the brief leaves open.") -> object:
    return pick_tools.ClarificationResult(changes_brief=changes, why=why)


class Asking:
    """A Change approved on a pick, at its build step, waiting on its builder's question; each worker run recorded."""

    def __init__(self, picking, monkeypatch) -> None:
        self.p = picking
        first = picking.put(rule())
        picking.save()
        assert picking.ask(1).status_code == 200
        picking.picks.append(pick_tools.PickResult(picked=[{"id": first.id}]))
        picking.verdicts.append(tools.ReviewResult(verdict="pass"))
        picking.step()
        assert picking.approve(1).status_code == 200
        c = picking.approved()
        c.plan = Plan(tasks=[Task(id="t1", title="Add farewell", scope=["packages/app"], checks=["true"])])
        c.step = Step(kind=StepKind.BUILD, task="t1")
        c = loop.apply(c, loop.StepResult(exit=Exit.ASK, question=Question(step=StepKind.BUILD, text=ASKED)), AT)
        picking.store.write(Lock(picking.slug), c)
        self.qid = c.outcome.question
        self.held: list[tuple[list[str], Question | None]] = []

        def worker(_store, _lock, change, _repo) -> None:
            self.held.append((step_decisions.held(), answer_kinds.delivered_next(change)))

        monkeypatch.setattr(runner, "_agent", worker)

    def answer(self, question: str = "", **body):
        url = f"/api/next/changes/{self.p.slug}/answers"
        return self.p.http.post(url, json={"question": question or self.qid, **body})

    def fold(self, at: datetime | None = None):
        return self.p.store.fold(Lock(self.p.slug), self.p.slug, at or datetime.now(UTC))

    def step(self, at: datetime | None = None):
        c, step = self.fold(at)
        runner._step(self.p.store, Lock(self.p.slug), c, step, self.p.repo)  # noqa: SLF001
        return self.p.change()

    def asked(self, c) -> Question:
        return next(q for q in c.questions if q.id == self.qid)


def inbox(picking) -> int:
    with picking.store.db.read() as db:
        return db.execute("SELECT count(*) FROM inbox").fetchone()[0]


def test_an_event_is_delivered_as_before_with_its_class_in_the_history(picking, monkeypatch):
    run = Asking(picking, monkeypatch)
    assert run.answer(kind="event", option=None, text=WORDS).json() == {"accepted": "answer"}

    c = run.step()

    [(_, delivered)] = run.held
    assert (delivered.id, delivered.answer.kind, delivered.answer.text) == (run.qid, "event", WORDS)
    assert (c.decisions, len(picking.pickers())) == ([], 1)  # no decision, no check
    said = [e for e in picking.store.events(picking.slug) if e.get("event") == "answer"]
    assert [(e["question"], e["class"]) for e in said] == [(run.qid, "event")]


def test_an_unclassed_answer_or_an_unconfirmed_clarification_is_refused_and_nothing_is_stored(picking, monkeypatch):
    run = Asking(picking, monkeypatch)
    refused = [
        ({}, answers.UNCLASSED),
        ({"kind": "clarification", "statement": SAID}, answers.UNCONFIRMED),  # not read back
        ({"kind": "clarification", "confirmed": True}, answers.UNCONFIRMED),
        ({"kind": "clarification", "statement": "One.\nTwo.\nThree.", "confirmed": True}, answers.UNCONFIRMED),
        ({"kind": "event", "statement": SAID}, "only a clarification has a statement"),
    ]
    for body, why in refused:
        r = run.answer(text=WORDS, **body)
        assert (r.status_code, r.json()["detail"]) == (422, why)
    assert inbox(picking) == 0
    assert loop.open_question(run.p.change()).id == run.qid


def test_a_confirmed_clarification_within_the_brief_becomes_a_change_decision_in_force_at_once(picking, monkeypatch):
    run = Asking(picking, monkeypatch)
    assert run.answer(kind="clarification", text=WORDS, statement=f"  {SAID} ", confirmed=True).status_code == 200
    picking.picks.append(verdict())

    c = run.step()

    checker = picking.pickers()[-1]
    assert (checker.job, checker.model, checker.effort) == (clarification.LABEL, "gpt-6.1-sol", "medium")
    assert (checker.submit, checker.role) == (pick_tools.CLARIFY, tools.PICKER)  # its verdict is its only tool
    assert all(x in checker.message for x in (SAID, ASKED, "farewell(name) says goodbye", "packages/app"))
    assert WORDS not in checker.message  # the statement he confirmed, never his words
    [d] = c.decisions
    assert (d.text, d.title, d.origin, d.id) == (SAID, ASKED, "decided", clarification.decision_id(c, run.asked(c)))
    entry = f"- {d.id} (change, decided): {ASKED}: {SAID}"
    [(section, delivered)] = run.held  # the worker gets its answer with the decision in force
    assert (delivered.id, entry in section, WORDS in "\n".join(section)) == (run.qid, True, False)
    assert section[1:3] == [step_decisions.HEAD, entry]  # first among the Change's decisions

    run.step()  # the next step: no check again, the decision still in force

    assert (len(picking.pickers()), entry in run.held[-1][0]) == (2, True)
    [archived] = decision_archive._changed("shop-site", c, "stem", "merged")  # noqa: SLF001
    assert (archived["statement"], archived["title"], archived["scope"]) == (SAID, ASKED, Scope.CHANGE)
    assert archived["read_back"] == d.at.date().isoformat()  # read back when he confirmed it


def test_a_clarification_the_check_finds_changing_the_brief_stops_the_work_undelivered_and_undecided(
    picking, monkeypatch
):
    run = Asking(picking, monkeypatch)
    said = run.answer(kind="clarification", text=WORDS, statement="It greets in French too.", confirmed=True)
    assert said.status_code == 200
    picking.picks.append(verdict(changes=True, why="A French greeting is an outcome the brief lacks."))

    c = run.step()

    assert (run.held, c.decisions) == ([], [])
    q = loop.open_question(c)
    assert (q.cause, [o.id for o in q.options]) == (f"scope:build:brief-change:{run.qid}", ["within", "stop"])
    assert "A French greeting is an outcome the brief lacks." in q.text
    assert (run.asked(c).answer.kind, answer_kinds.delivered_next(c)) == ("brief_change", None)
    assert WORDS not in "\n".join(step_input.brief(c))  # no later role reads it either
    assert loop.next_step(c, AT) is None  # nothing runs while the owner decides


def test_a_check_that_fails_waits_and_runs_again_never_taken_for_a_pass(picking, monkeypatch):
    run = Asking(picking, monkeypatch)
    assert run.answer(kind="clarification", text=WORDS, statement=SAID, confirmed=True).status_code == 200
    picking.picks.append("error")

    c = run.step()

    assert (run.held, c.decisions, c.stop) == ([], [], None)
    assert (c.outcome.exit, c.outcome.cause) == (Exit.PENDING, f"{ErrorKind.NETWORK}:build:{clarification.LABEL}")
    assert c.outcome.reason.startswith(clarification.FAILED)
    assert loop.next_step(c, c.outcome.at) is None  # it waits
    picking.picks.append(verdict())

    c = run.step(c.outcome.wake_at)

    assert ([d.text for d in c.decisions], len(run.held), len(picking.pickers())) == ([SAID], 1, 3)


def test_a_brief_change_stops_the_work_and_answering_within_the_brief_reopens_the_question(picking, monkeypatch):
    run = Asking(picking, monkeypatch)
    assert run.answer(kind="brief_change", text=WORDS).status_code == 200

    c = run.step()

    q = loop.open_question(c)
    assert (answer_kinds.owned(q), loop.ordinary(q), "not built yet" in q.text) == (True, False, True)
    assert (run.held, len(picking.pickers()), answer_kinds.delivered_next(c)) == ([], 1, None)  # no check, no worker
    assert run.answer(q.id, kind="event", option="within").json()["detail"] == "only a worker's question takes a kind"
    assert run.answer(q.id).status_code == 422  # one of its options
    assert run.answer(q.id, option="within", channel="chat").status_code == 403  # a Changes-page decision
    assert run.answer(q.id, option="within").status_code == 200

    c, _ = run.fold()

    reopened = loop.open_question(c)
    assert (reopened.id, reopened.answer, loop.ordinary(reopened)) == (run.qid, None, True)
    assert run.answer(kind="event", text="English").status_code == 200
    run.step()
    [(_, delivered)] = run.held
    assert delivered.answer.text == "English"


def test_stopping_the_change_over_a_brief_change_abandons_it(picking, monkeypatch):
    run = Asking(picking, monkeypatch)
    assert run.answer(kind="brief_change", text=WORDS).status_code == 200
    q = loop.open_question(run.step())
    assert run.answer(q.id, option="stop").status_code == 200

    c, _ = run.fold()

    assert (c.intent.abandoned_at is not None, c.step.kind, run.held) == (True, StepKind.CLEANUP, [])


class Reply(io.BytesIO):
    def __init__(self, data: bytes, status: int) -> None:
        super().__init__(data)
        self.status = status


class Loopback:
    """The chat server's opener, answered in-process by the host."""

    def __init__(self, http: TestClient) -> None:
        self.http = http

    def open(self, request, timeout):  # noqa: ARG002 - the opener's signature
        url = urllib.parse.urlsplit(request.full_url)
        r = self.http.request(request.get_method(), f"{url.path}?{url.query}", content=request.data,
                              headers=dict(request.header_items()))  # fmt: skip
        if r.status_code >= 400:
            raise urllib.error.HTTPError(request.full_url, r.status_code, "", r.headers, io.BytesIO(r.content))
        return Reply(r.content, r.status_code)


def test_the_chat_tool_takes_the_kind_and_passes_only_a_confirmed_statement(picking, monkeypatch):
    run = Asking(picking, monkeypatch)
    chat = mcp_server.Chat.__new__(mcp_server.Chat)
    chat.repo, chat.store = picking.repo, picking.store
    monkeypatch.setattr(mcp_server.Chat, "record", lambda _self: RECORD)
    monkeypatch.setattr(mcp_server, "_LOCAL", Loopback(picking.http))
    monkeypatch.setitem(mcp_server._STATE, "chat", chat)  # noqa: SLF001 - the server's one chat
    [tool] = [t for t in asyncio.run(mcp_server.mcp.list_tools()) if t.name == "answer_question"]
    assert (sorted(tool.input_schema["required"]), "read a clarification back" in tool.description) == (
        ["kind", "question"],
        True,
    )

    def said(**args: object) -> dict:
        return asyncio.run(mcp_server.mcp.call_tool("answer_question", {"question": f"c1.{run.qid}", **args}))

    unread = said(kind="clarification", text=WORDS, statement=SAID).structured_content
    assert (unread["answered"], unread["detail"], inbox(picking)) == (False, answers.UNCONFIRMED, 0)
    done = said(kind="clarification", text=WORDS, statement=SAID, confirmed=True).structured_content
    assert done == {"answered": True, "accepted": "answer"}

    c, _ = run.fold()

    a = run.asked(c).answer
    assert (a.kind, a.statement, a.channel, a.text) == ("clarification", SAID, "chat", WORDS)
