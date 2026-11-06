"""Answers during the work, classed by their relayer (TD-461; decision-intent-build §2, slice 5).

A Change is shaped, picked and approved through the host API (`picking`), then waits on its builder's question. The
owner's answer comes from the Changes page or a lead chat as an event, a clarification or a brief change.
"""

import asyncio
import io
import urllib.error
import urllib.parse
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from owlbear_decisions import Decision, Origin, Scope, State, new_id
from owlbear_delivery_next.change_contracts import amend_tools, pick_tools, tools
from owlbear_delivery_next.change_contracts.inbox import AnswerItem, IntentItem
from owlbear_delivery_next.change_contracts.models import (
    Answer,
    Change,
    ErrorKind,
    Exit,
    Option,
    PersonCheck,
    Plan,
    Question,
    Step,
    StepKind,
    Task,
)
from owlbear_delivery_next.change_contracts.profile_record import Profile
from owlbear_delivery_next.change_flow import amending, answer_kinds, loop
from owlbear_delivery_next.commands import chat_client, cli, mcp_server, runner
from owlbear_delivery_next.local_system.codebase import CURRENT
from owlbear_delivery_next.local_system.processes import Termination
from owlbear_delivery_next.project_host import answers
from owlbear_delivery_next.project_host.host import HostRecord
from owlbear_delivery_next.runtimes import session_result, step_answers, step_decisions, step_input
from owlbear_delivery_next.runtimes.session_result import Run
from owlbear_delivery_next.state_store import decision_archive
from owlbear_delivery_next.state_store.store import Lock
from owlbear_delivery_next.workflow_steps import clarification

AT = datetime(2026, 10, 22, 9, tzinfo=UTC)
ASKED = "Which language does the greeting use?"
WORDS = "english i guess, most readers are in canada"  # the owner's words: never a decision
SAID = "The greeting is in English."  # his intent as he confirmed it
RECORD = HostRecord(url="http://127.0.0.1:9/", token="t", pid=1, started_at=AT, code=CURRENT)  # noqa: S106
DONE = Termination(confirmed=True)


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

    def __init__(
        self, picking, monkeypatch, *, session: str = "", stub: bool = True, options: tuple = (), **draft
    ) -> None:
        self.p = picking
        first = picking.put(rule())
        picking.save(**draft)
        assert picking.ask(1).status_code == 200
        picking.picks.append(pick_tools.PickResult(picked=[{"id": first.id}]))
        picking.verdicts.append(tools.ReviewResult(verdict="pass"))
        picking.step()
        assert picking.approve(1).status_code == 200
        c = picking.approved()
        c.plan = Plan(tasks=[Task(id="t1", title="Add farewell", scope=["packages/app"], checks=["cd . && true"])])
        c.step = Step(kind=StepKind.BUILD, task="t1", session=session or None)
        asked = Question(step=StepKind.BUILD, text=ASKED, options=list(options))
        c = loop.apply(c, loop.StepResult(exit=Exit.ASK, question=asked), AT)
        picking.store.write(Lock(picking.slug), c)
        self.qid = c.outcome.question
        self.held: list[tuple[list[str], Question | None]] = []

        def worker(_store, _lock, change, _repo) -> None:
            self.held.append((step_decisions.held(), answer_kinds.delivered_next(change)))

        if stub:
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
    assert (d.text, d.title, d.origin, d.id) == (SAID, ASKED, "decided", answer_kinds.decision_id(c, run.asked(c)))
    entry = f"- {d.id} (change, decided): {ASKED}: {SAID}"
    [(section, delivered)] = run.held  # the worker gets its answer with the decision in force
    assert (delivered.id, entry in section, WORDS in "\n".join(section)) == (run.qid, True, False)
    assert section[1:3] == [step_decisions.HEAD, entry]  # first among the Change's decisions

    run.step()  # the next step: no check again, the decision still in force

    assert (len(picking.pickers()), entry in run.held[-1][0]) == (2, True)
    [archived] = decision_archive._changed("shop-site", c, "stem", "merged")  # noqa: SLF001
    assert (archived["statement"], archived["title"], archived["scope"]) == (SAID, ASKED, Scope.CHANGE)
    assert archived["read_back"] == d.at.date().isoformat()  # read back when he confirmed it


def test_a_clarification_the_check_finds_changing_the_brief_starts_its_amendment_undelivered_and_undecided(
    picking, monkeypatch
):
    run = Asking(picking, monkeypatch)
    said = run.answer(kind="clarification", text=WORDS, statement="It greets in French too.", confirmed=True)
    assert said.status_code == 200
    picking.picks.append(verdict(changes=True, why="A French greeting is an outcome the brief lacks."))

    c = run.step()

    assert (run.held, c.decisions, loop.open_question(c)) == ([], [], None)
    (a,) = c.amendments
    assert (a.source, a.question, c.amending.phase) == ("answer", run.qid, "prepare")  # the shaper prepares it next
    assert "A French greeting is an outcome the brief lacks." in a.reason
    assert (run.asked(c).answer.kind, answer_kinds.delivered_next(c)) == ("brief_change", None)
    assert WORDS not in "\n".join(step_input.brief(c))  # no later role reads it either


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


FRENCH = amend_tools.CandidateResult(
    items=[{"field": "criterion", "text": "farewell('Ada') also says 'Au revoir, Ada!'", "why": "he wants French"}]
)
MORE = amend_tools.VerdictResult(verdict="weaker", reasons="a new outcome", beyond="it adds French to every page")


def amended(run: Asking) -> Question:
    """His brief_change answer through the amendment path: the shaper's candidate, its challenge, his question."""
    assert run.answer(kind="brief_change", text=WORDS).status_code == 200
    run.p.verdicts += [FRENCH, MORE]
    run.step()
    return loop.open_question(run.step())


def test_a_brief_change_runs_its_amendment_and_declining_it_within_the_brief_reopens_the_question(picking, monkeypatch):
    run = Asking(picking, monkeypatch)

    q = amended(run)

    assert (amending.owned(q), loop.ordinary(q), "Beyond your answer: it adds French" in q.text) == (
        ("A1", "decide"),
        False,
        True,
    )
    assert [cfg.role for cfg in picking.told[-2:]] == ["shaper", "challenger"]
    assert (run.held, answer_kinds.delivered_next(picking.change())) == ([], None)  # no worker, nothing delivered
    assert run.answer(q.id, kind="event", option="within").json()["detail"] == "only a worker's question takes a kind"
    assert run.answer(q.id).status_code == 422  # one of its options
    assert run.answer(q.id, option="within", channel="chat").status_code == 403  # a Changes-page decision
    assert run.answer(q.id, option="within").status_code == 422  # his reason goes to the work
    assert run.answer(q.id, option="within", text="English only").status_code == 200

    c, _ = run.fold()

    reopened = loop.open_question(c)
    assert (reopened.id, reopened.answer, loop.ordinary(reopened)) == (run.qid, None, True)
    assert (c.amendments[0].state, c.amendments[0].declined, c.brief.version) == ("declined", "English only", 1)
    assert any("English only" in line for line in step_answers.answered(c))  # his reason goes to the work
    assert run.answer(kind="event", text="English").status_code == 200
    run.step()
    [(_, delivered)] = run.held
    assert delivered.answer.text == "English"


def test_a_reopened_question_does_not_show_an_answer_dropped_before_a_later_one_applied(picking, monkeypatch):
    """#791's notice stays beside a question only until an answer to it applies, even when it opens again."""
    run = Asking(picking, monkeypatch)
    dropped = {"event": "answer-not-applied", "at": AT.isoformat(), "question": run.qid, "reason": "it was settled"}
    picking.store.log(Lock(picking.slug), picking.slug, dropped)
    assert run.answer(amended(run).id, option="within", text="English only").status_code == 200

    run.fold()

    detail = picking.http.get(f"/api/next/changes/{picking.slug}").json()
    assert (detail["question"]["id"], detail["question"]["dropped"]) == (run.qid, None)


def test_stopping_the_change_over_a_brief_change_abandons_it(picking, monkeypatch):
    run = Asking(picking, monkeypatch)
    assert run.answer(amended(run).id, option="stop").status_code == 200

    c, _ = run.fold()

    assert (c.intent.abandoned_at is not None, c.step.kind, run.held) == (True, StepKind.CLEANUP, [])
    assert (c.amendments[0].state, c.amendments[0].choice, c.brief.version) == ("declined", "stop", 1)


def test_a_brief_change_that_says_no_more_than_his_answer_applies_without_another_question(picking, monkeypatch):
    run = Asking(picking, monkeypatch)
    assert run.answer(kind="brief_change", text=WORDS).status_code == 200
    picking.verdicts += [FRENCH, amend_tools.VerdictResult(verdict="weaker", reasons="French is what he asked for")]
    run.step()

    c = run.step()

    (a,) = c.amendments
    assert (a.state, a.level, loop.open_question(c), c.brief.version) == ("applied", "decided", None, 2)
    assert (c.step.kind, run.held) == (StepKind.PLAN, [])  # his amendment replans the task on the new version


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
    chat = chat_client.Chat.__new__(chat_client.Chat)
    chat.repo, chat.home = picking.repo, picking.store.root
    monkeypatch.setattr(chat_client.Chat, "record", lambda _self: RECORD)
    monkeypatch.setattr(chat_client, "_LOCAL", Loopback(picking.http))
    monkeypatch.setitem(mcp_server._STATE, "chat", chat)  # noqa: SLF001 - the server's one chat
    [tool] = [t for t in asyncio.run(mcp_server.mcp.list_tools()) if t.name == "answer_question"]
    assert sorted(tool.input_schema["required"]) == ["kind", "question"]
    assert {"statement", "confirmed"} <= set(tool.input_schema["properties"])

    def said(**args: object) -> dict:
        return asyncio.run(mcp_server.mcp.call_tool("answer_question", {"question": f"c1.{run.qid}", **args}))

    unread = said(kind="clarification", text=WORDS, statement=SAID).structured_content
    assert (unread["answered"], unread["detail"], inbox(picking)) == (False, answers.UNCONFIRMED, 0)
    done = said(kind="clarification", text=WORDS, statement=SAID, confirmed=True).structured_content
    assert done == {"answered": True, "accepted": "answer"}

    c, _ = run.fold()

    a = run.asked(c).answer
    assert (a.kind, a.statement, a.channel, a.text) == ("clarification", SAID, "chat", WORDS)


def failed_check(run: Asking):
    """The clarification answered and its check failed once: the Change waits to check it again."""
    assert run.answer(kind="clarification", text=WORDS, statement=SAID, confirmed=True).status_code == 200
    run.p.picks.append("error")
    return run.step()


def test_a_clarification_still_unchecked_after_the_network_gate_is_checked_before_any_worker_runs(picking, monkeypatch):
    run = Asking(picking, monkeypatch)
    c = failed_check(run)
    assert all(x not in "\n".join(step_input.brief(c)) for x in (ASKED, WORDS, SAID))  # no role reads it unchecked
    cause = c.outcome.cause
    c.budgets.causes[cause] = c.budgets.causes[cause].model_copy(update={"since": c.outcome.at - timedelta(days=2)})
    picking.store.write(Lock(picking.slug), c)
    picking.picks.append("error")
    gate = loop.open_question(run.step(c.outcome.wake_at))  # a day of failures asks the owner
    assert (gate.cause, run.answer(gate.id, option="done").status_code) == (cause, 200)
    picking.picks.append(verdict())

    c = run.step()

    assert ([d.text for d in c.decisions], len(picking.pickers())) == ([SAID], 4)  # checked before the worker
    [(section, delivered)] = run.held
    assert (delivered.id, any(SAID in line for line in section)) == (gate.id, True)


def test_a_clarification_asked_at_one_step_is_checked_before_a_worker_of_another(picking, monkeypatch):
    run = Asking(picking, monkeypatch)
    c = failed_check(run)
    c.step, c.outcome = Step(kind=StepKind.REVIEW, mode="final"), None  # e.g. a restarted final review
    picking.store.write(Lock(picking.slug), c)
    picking.picks.append(verdict())

    c = run.step()

    assert ([d.text for d in c.decisions], len(run.held)) == ([SAID], 1)
    assert f"- {ASKED}: {SAID}" in "\n".join(step_input.brief(c))  # once checked, as he confirmed it


def first_messages(picking, monkeypatch) -> list:
    """The configurations of the workers the runner starts, each stopped after its first message."""
    told = []

    async def worker(cfg):
        if cfg.role == tools.PICKER:
            return await picking.run(cfg)
        told.append(cfg)
        return Run(cfg.session_id, "error", detail="stopped after its first message", termination=DONE)

    monkeypatch.setattr(runner.sdk_adapter, "run", worker)
    return told


def quoted(lines: list[str]) -> str:
    """The answer's lines as a resumed session reads them."""
    return "\n".join(f"> {line}" if line else ">" for line in lines)


def listed(lines: list[str]) -> str:
    """The answer's lines as a fresh session's answers so far list them."""
    return "\n".join([f"- {ASKED}: {lines[0]}", *(f"  {line}" if line else "" for line in lines[1:])])


@pytest.mark.parametrize("session", ["c1-build-t1-asked", ""])  # resumed into the asking session, or a fresh one
def test_a_worker_receives_a_checked_clarification_as_the_confirmed_statement_never_the_owners_words(
    picking, monkeypatch, session
):
    run, told = Asking(picking, monkeypatch, session=session, stub=False), first_messages(picking, monkeypatch)
    said = [SAID, "It says Hello, never Hi."]  # a confirmed statement may hold two lines
    body = {"kind": "clarification", "text": WORDS, "statement": "\n".join(said), "confirmed": True}
    assert run.answer(**body).status_code == 200
    picking.picks.append(verdict())

    run.step()

    cfg = told[0]
    assert (cfg.resume, quoted(said) in cfg.message) == ((True, True) if session else (False, False))
    assert session or listed(said) in cfg.message  # a fresh session's answers so far
    assert all(WORDS not in m for m in (cfg.message, cfg.fresh))


@pytest.mark.parametrize("session", ["c1-build-t1-asked", ""])
def test_a_worker_receives_a_long_answer_whole_with_its_line_breaks(picking, monkeypatch, session):
    run, told = Asking(picking, monkeypatch, session=session, stub=False), first_messages(picking, monkeypatch)
    said = [
        "    greet(name) stays as it is",
        "",
        " ".join(["Background."] * 40),
        "Essential: end with an exclamation mark.",
    ]
    assert len("\n".join(said[:3])) > 400  # the essential line comes after the old cut
    assert run.answer(kind="event", option=None, text="\n".join(said)).status_code == 200

    run.step()

    cfg = told[0]
    assert cfg.resume == bool(session)
    assert (quoted(said) if session else listed(said)) in cfg.message


def test_the_check_reads_the_approved_brief_decisions_and_catches_a_clarification_against_one(picking, monkeypatch):
    german = "The greeting is in German only."
    shaped = {"question": "Which language may a greeting use?", "answer": german, "origin": "decided"}
    run, checks = Asking(picking, monkeypatch, decisions=[shaped]), []

    async def judge(cfg):
        if cfg.job != clarification.LABEL:
            return await picking.run(cfg)
        checks.append(cfg.message)
        said = verdict(changes=german in cfg.message, why="It contradicts the German-only decision.")
        return Run(cfg.session_id, "result", said, usage=picking.USAGE, termination=DONE)

    monkeypatch.setattr(runner.sdk_adapter, "run", judge)
    assert run.answer(kind="clarification", text=WORDS, statement=SAID, confirmed=True).status_code == 200

    c = run.step()

    assert (c.decisions, run.held, [a.source for a in c.amendments]) == ([], [], ["answer"])
    [said] = checks
    assert all(x in said for x in ("Changes what a page shows: no", "UI states:", "Person checks:"))


def test_the_cli_answer_needs_the_class_and_a_clarification_its_confirmed_statement(picking, monkeypatch, capsys):
    run = Asking(picking, monkeypatch)
    monkeypatch.setattr(cli.Store, "open", lambda *_a, **_k: picking.store)

    def said(*args: str) -> int:
        asked = ["--repo", str(picking.repo), "answer", picking.slug, "--question", run.qid, "--text", WORDS]
        return cli.main([*asked, *args])

    clarified = ("--kind", "clarification", "--statement", SAID)
    assert (said(), said(*clarified), inbox(picking)) == (1, 1, 0)
    assert answers.UNCLASSED in capsys.readouterr().err
    assert said(*clarified, "--confirmed") == 0

    a = run.asked(run.fold()[0]).answer
    assert (a.kind, a.statement, a.text) == ("clarification", SAID, WORDS)


def test_the_cli_refuses_an_option_the_question_does_not_offer_and_queues_nothing(picking, monkeypatch, capsys):
    """#676: the console runs the Changes page's checks before it writes; a refused answer leaves the inbox empty."""
    run = Asking(picking, monkeypatch, options=(Option(id="en", label="English"),))
    monkeypatch.setattr(cli.Store, "open", lambda *_a, **_k: picking.store)

    def said(option: str) -> int:
        return cli.main(["--repo", str(picking.repo), "answer", picking.slug, "--question", run.qid,
                         "--option", option, "--kind", "event"])  # fmt: skip

    assert (said("de"), inbox(picking)) == (1, 0)
    assert "option de is not one of ['en']" in capsys.readouterr().err
    assert (said("en"), inbox(picking)) == (0, 1)
    shown = capsys.readouterr().out
    assert (ASKED in shown, f"{run.qid} option en: English" in shown) == (True, True)


WAITING = "already has an answer waiting to be applied; this one was not queued"


def test_a_second_answer_before_the_fold_is_refused_and_the_first_one_holds(picking, monkeypatch):
    """#791: two answers to one question sent before the runner folds; the second is refused, never dropped silently."""
    run = Asking(picking, monkeypatch, options=(Option(id="en", label="English"), Option(id="de", label="German")))
    assert run.answer(option="en", kind="event").status_code == 200

    second = run.answer(option="de", kind="event")

    refused = (second.status_code, second.json().get("detail"), inbox(picking))
    assert refused == (409, f"question {run.qid} {WAITING}", 1)
    c, _ = run.fold()
    assert (run.asked(c).answer.option, inbox(picking)) == ("en", 0)
    said = [e for e in picking.store.events(picking.slug) if e.get("event") in {"answer", "answer-not-applied"}]
    assert [(e["event"], e["question"]) for e in said] == [("answer", run.qid)]
    late = run.answer(option="de", kind="event")
    assert (late.status_code, late.json()["detail"]) == (409, f"question {run.qid} is not open")


def test_the_cli_refuses_a_second_answer_while_one_waits_and_queues_nothing(picking, monkeypatch, capsys):
    run = Asking(picking, monkeypatch)
    monkeypatch.setattr(cli.Store, "open", lambda *_a, **_k: picking.store)
    assert run.answer(kind="event", text=WORDS).status_code == 200

    code = cli.main(["--repo", str(picking.repo), "answer", picking.slug, "--question", run.qid, "--text", "again",
                     "--kind", "event"])  # fmt: skip

    assert (code, inbox(picking)) == (1, 1)
    assert f"not answered: question {run.qid} {WAITING}" in capsys.readouterr().err


def test_the_chat_tool_reports_a_second_answer_as_not_answered(picking, monkeypatch):
    run = Asking(picking, monkeypatch)
    chat = chat_client.Chat.__new__(chat_client.Chat)
    chat.repo, chat.home = picking.repo, picking.store.root
    monkeypatch.setattr(chat_client.Chat, "record", lambda _self: RECORD)
    monkeypatch.setattr(chat_client, "_LOCAL", Loopback(picking.http))
    monkeypatch.setitem(mcp_server._STATE, "chat", chat)  # noqa: SLF001 - the server's one chat
    assert run.answer(kind="event", text=WORDS).status_code == 200

    args = {"question": f"c1.{run.qid}", "kind": "event", "text": "again"}
    out = asyncio.run(mcp_server.mcp.call_tool("answer_question", args)).structured_content

    assert (out["answered"], out.get("error"), inbox(picking)) == (False, f"question {run.qid} {WAITING}", 1)


def test_an_answer_checked_against_an_older_read_is_refused_once_another_was_applied(picking, monkeypatch):
    """The queue checks the stored question again, not the copy its caller read before another answer was applied."""
    run = Asking(picking, monkeypatch)
    before = picking.change()
    assert run.answer(kind="event", text=WORDS).status_code == 200
    run.fold()

    item = answers.answer_item(picking.store, before, answers.AnswerBody(question=run.qid, kind="event", text="again"))

    assert isinstance(item, AnswerItem)  # the older read still shows the question open
    assert (picking.store.put_answer(picking.slug, item), inbox(picking)) == (f"question {run.qid} is not open", 0)


@pytest.mark.parametrize(
    ("options", "first", "why"),
    [
        ((), True, "is no longer open"),
        ((Option(id="ok", label="Accept", next="accept"),), False,
         "is settled only by one of its options, a reconsideration by a note"),
    ],
    ids=["already-answered", "no-option-chosen"],
)  # fmt: skip
def test_a_queued_answer_the_fold_does_not_apply_leaves_an_activity_line(picking, monkeypatch, options, first, why):
    """#791: an answer that reached the inbox but settles nothing is named in the activity, never dropped silently."""
    run = Asking(picking, monkeypatch, options=options)
    if first:
        assert run.answer(kind="event", text=WORDS).status_code == 200
        run.fold()
    picking.store.put_inbox(picking.slug, AnswerItem(at=AT, question=run.qid, text="again", classed="event"))

    c, _ = run.fold()

    dropped = [e for e in picking.store.events(picking.slug) if e.get("event") == "answer-not-applied"]
    assert [(e["question"], e["reason"]) for e in dropped] == [(run.qid, f"question {run.qid} {why}")]
    kept = run.asked(c).answer
    assert (kept and kept.text, inbox(picking)) == (WORDS if first else None, 0)


MOVED = "no longer waits on an answer:"


def moved_on(run: Asking, how: str) -> str:
    """The Change stops waiting on the worker's question: the owner changes its intent, or its PR went elsewhere.

    Returns why an answer to it is refused."""
    if how == "change":
        run.p.store.put_inbox(run.p.slug, IntentItem(at=AT, intent="change", text="a different greeting"))
        c, _ = run.fold()
        assert (c.step.kind, c.outcome) == (StepKind.SHAPE, None)
        return f"question {run.qid} {MOVED} its intent changed"
    c, _ = run.p.store.fold(Lock(run.p.slug), run.p.slug, datetime.now(UTC), pr_state="misdelivered")
    assert (c.step.kind, c.outcome.question == run.qid) == (StepKind.BUILD, False)
    return f"question {run.qid} {MOVED} it waits on question {c.outcome.question} now"


@pytest.mark.parametrize("how", ["change", "misdelivered"])
def test_an_answer_to_a_question_the_change_no_longer_waits_on_is_refused_and_queues_nothing(picking, monkeypatch, how):
    """#914: checked against the stored Change, not the caller's read taken while the question still gated."""
    run = Asking(picking, monkeypatch)
    body = answers.AnswerBody(question=run.qid, kind="event", text=WORDS)
    item = answers.answer_item(picking.store, picking.change(), body)
    why = moved_on(run, how)

    assert isinstance(item, AnswerItem)
    assert (picking.store.put_answer(picking.slug, item), inbox(picking)) == (why, 0)
    late = run.answer(kind="event", text=WORDS)
    refused = (late.status_code, late.json()["detail"], inbox(picking), run.asked(picking.change()).answer)
    assert refused == (409, why, 0, None)


@pytest.mark.parametrize("intent", ["change", "abandon"])
def test_an_answer_queued_after_a_change_of_intent_is_not_applied(picking, monkeypatch, intent):
    """#914: the fold applies the intent first, so the answer behind it in the same batch reaches no question."""
    run = Asking(picking, monkeypatch)
    item = AnswerItem(at=AT, question=run.qid, text=WORDS, classed="event")
    picking.store.put_inbox(picking.slug, IntentItem(at=AT, intent=intent, text="a different greeting"))
    assert picking.store.put_answer(picking.slug, item) is None

    c, _ = run.fold()

    said = [(e["event"], e.get("reason")) for e in picking.store.events(picking.slug)
            if e.get("event") in {"answer", "answer-not-applied"}]  # fmt: skip
    why = "the Change was abandoned" if intent == "abandon" else "its intent changed"
    assert said == [("answer-not-applied", f"question {run.qid} {MOVED} {why}")]
    assert (run.asked(c).answer, inbox(picking)) == (None, 0)


def test_the_cli_refuses_an_answer_the_change_no_longer_waits_on(picking, monkeypatch, capsys):
    run = Asking(picking, monkeypatch)
    monkeypatch.setattr(cli.Store, "open", lambda *_a, **_k: picking.store)
    why = moved_on(run, "change")

    code = cli.main(["--repo", str(picking.repo), "answer", picking.slug, "--question", run.qid, "--text", WORDS,
                     "--kind", "event"])  # fmt: skip

    assert (code, inbox(picking)) == (1, 0)
    assert f"not answered: {why}" in capsys.readouterr().err


def test_the_chat_tool_reports_an_answer_the_change_no_longer_waits_on_as_not_answered(picking, monkeypatch):
    run = Asking(picking, monkeypatch)
    chat = chat_client.Chat.__new__(chat_client.Chat)
    chat.repo, chat.home = picking.repo, picking.store.root
    monkeypatch.setattr(chat_client.Chat, "record", lambda _self: RECORD)
    monkeypatch.setattr(chat_client, "_LOCAL", Loopback(picking.http))
    monkeypatch.setitem(mcp_server._STATE, "chat", chat)  # noqa: SLF001 - the server's one chat
    why = moved_on(run, "change")

    args = {"question": f"c1.{run.qid}", "kind": "event", "text": WORDS}
    out = asyncio.run(mcp_server.mcp.call_tool("answer_question", args)).structured_content

    assert (out["answered"], out.get("error"), inbox(picking)) == (False, why, 0)


@pytest.mark.parametrize("held", ["paused", "change-at-merge"])
def test_a_question_the_change_still_waits_on_takes_its_answer(picking, monkeypatch, held):
    """A pause, or a change of intent at the merge step (which waits for the merge), leaves the question waiting."""
    run = Asking(picking, monkeypatch)
    if held == "change-at-merge":
        c = picking.change()
        c.step = Step(kind=StepKind.MERGE)
        picking.store.write(Lock(picking.slug), c)
    intent = "pause" if held == "paused" else "change"
    picking.store.put_inbox(picking.slug, IntentItem(at=AT, intent=intent, text="later"))
    run.fold()

    assert run.answer(kind="event", text=WORDS).status_code == 200
    c, step = run.fold()
    assert (run.asked(c).answer.text, inbox(picking)) == (WORDS, 0)
    if held == "paused":
        assert step is None  # nothing runs until Resume


def test_a_replacement_check_session_is_told_the_owners_pending_answer(tmp_path):
    question = Question(
        id="q1",
        step=StepKind.CHECK,
        text=ASKED,
        options=[Option(id="en", label="English")],
        answer=Answer(option="en", at=AT),
    )
    check = PersonCheck(id="p1", steps=["open the page"])
    task = Task(id="p1", title="Check the page")
    change = Change(
        slug="greet",
        questions=[question],
        checks=[check],
        plan=Plan(tasks=[task]),
        step=Step(kind=StepKind.CHECK, task="p1"),
    )

    parts = step_input.session(change, Profile(), tmp_path, {})

    assert f"- {ASKED}: English" in parts.message


STOPPED = "The Spotter stopped this step for irreversible harm: it would force-push over main."


def test_allowing_what_the_spotter_stopped_amends_the_brief_and_leaves_the_project_decision(picking, monkeypatch):
    """#717: "Allow it" runs a brief amendment: a Change-scoped exception, never an edit of the project decision."""
    run = Asking(picking, monkeypatch)
    project = {p: p.read_text() for p in picking.shared.root.rglob("*.md")}
    stopped = Run("s", ending="spotter-ask", detail=STOPPED, termination=DONE)
    c = loop.apply(picking.change(), session_result.to_result(stopped, StepKind.BUILD, AT), AT)
    picking.store.write(Lock(picking.slug), c)
    assert run.answer(c.outcome.question, option="allow").status_code == 200
    run.fold()
    exception = {"field": "decision", "question": "May this Change force-push over main?",
                 "text": "Yes, for this Change only", "why": "the owner allowed it"}  # fmt: skip
    said = amend_tools.VerdictResult(verdict="weaker", reasons="it allows what the project forbids")
    picking.verdicts += [amend_tools.CandidateResult(items=[exception]), said]

    run.step()
    c = run.step()

    (a,) = c.amendments
    assert (a.source, a.state, a.level, loop.open_question(c), run.held) == ("allow", "applied", "decided", None, [])
    assert STOPPED in a.reason
    made = [(d.answer, d.scope, d.origin) for d in c.brief.decisions if d.question.startswith("May this Change")]
    assert made == [("Yes, for this Change only", "change", "decided")]
    assert {p: p.read_text() for p in picking.shared.root.rglob("*.md")} == project
    run.step()
    [(_, delivered)] = run.held
    assert delivered is None or delivered.answer.option != "allow"  # the worker never receives the allow answer


@pytest.mark.parametrize("field", ["detail", "usage_unread"])
def test_a_check_that_fails_waits_with_its_whole_reason(picking, monkeypatch, whole_error, field):
    run = Asking(picking, monkeypatch)
    assert run.answer(kind="clarification", text=WORDS, statement=SAID, confirmed=True).status_code == 200

    async def failed(cfg):
        ending, payload = ("error", None) if field == "detail" else ("result", verdict())
        return Run(cfg.session_id, ending, payload, termination=Termination(confirmed=True), **{field: whole_error})

    monkeypatch.setattr(runner.sdk_adapter, "run", failed)

    c = run.step()

    why = (
        f"its session ended error: {whole_error}"
        if field == "detail"
        else f"its verdict cannot be trusted: {whole_error}"
    )
    assert (c.outcome.exit, c.outcome.reason) == (Exit.PENDING, f"{clarification.FAILED}: {why}")


@pytest.mark.parametrize("case", ["ending", "usage"])
def test_an_unverified_session_end_says_its_problems_whole(picking, monkeypatch, whole_error, case):
    run = Asking(picking, monkeypatch)
    assert run.answer(kind="clarification", text=WORDS, statement=SAID, confirmed=True).status_code == 200
    left = Termination(confirmed=False, unknown=(9,), problems=(f"disconnect failed: RuntimeError: {whole_error}",))
    seen = []

    async def unverified(cfg):
        seen.append(cfg.session_id)
        if case == "ending":
            return Run(cfg.session_id, "error", None, detail="the runtime did not start", termination=left)
        return Run(cfg.session_id, "result", verdict(), usage_unread="the usage was not read", termination=left)

    monkeypatch.setattr(runner.sdk_adapter, "run", unverified)

    c = run.step()

    why = f"termination unverified: processes 9 still present; disconnect failed: RuntimeError: {whole_error}"
    said = (
        f"its session ended error: the runtime did not start; {why}"
        if case == "ending"
        else f"its verdict cannot be trusted: the usage was not read; {why}"
    )
    assert (c.outcome.exit, c.outcome.reason) == (Exit.PENDING, f"{clarification.FAILED}: {said}")
    steps = [e for e in picking.store.events(picking.slug) if e.get("session") in seen]
    ended = {"confirmed": False, "survivors": [], "unknown": [9], "problems": list(left.problems)}
    assert [(e["termination"], e["reason"]) for e in steps] == [(ended, why)]
