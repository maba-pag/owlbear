"""The decision lookup (TD-456, TD-459): workers in SDK and window steps and lead chats ask the picker, which reads the
complete list. A failed lookup says failed, never "none apply"; a lookup attaches nothing to the Change.
"""

import asyncio
import io
import json
import threading
import time
import urllib.error
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from mcp import types

from owlbear_decisions import Decision, Link, LinkType, Origin, Scope, State, new_id, write
from owlbear_decisions.models import STATEMENT_LIMIT
from owlbear_delivery_next.change_contracts import pick_tools, tools
from owlbear_delivery_next.change_contracts.decision_records import Decision as ChangeDecision
from owlbear_delivery_next.change_contracts.decision_records import Pick
from owlbear_delivery_next.change_contracts.models import Plan, Step, StepKind, Task
from owlbear_delivery_next.change_flow import loop
from owlbear_delivery_next.commands import chat_client, mcp_server, runner, step_mcp
from owlbear_delivery_next.local_system import codebase
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.local_system.processes import Termination
from owlbear_delivery_next.machine_host import app
from owlbear_delivery_next.machine_host.machine import Machine
from owlbear_delivery_next.project_host.host import HostRecord
from owlbear_delivery_next.runtimes import sdk_adapter, step_decisions
from owlbear_delivery_next.runtimes.results import Gate
from owlbear_delivery_next.runtimes.session_result import Run
from owlbear_delivery_next.runtimes.step_inbox import Inbox
from owlbear_delivery_next.state_store import decision_archive, decision_store
from owlbear_delivery_next.state_store.store import Lock
from owlbear_delivery_next.workflow_steps import decisions_gate, lookup, pick, sessions

AT = datetime(2026, 10, 22, 9, tzinfo=UTC)
PROJECT = "shop-site"
QUESTION = "May the farewell page load a web font from a CDN?"
DONE = Termination(confirmed=True)
RECORD = HostRecord(url="http://127.0.0.1:9/", token="t", pid=1, started_at=AT, code=codebase.CURRENT)  # noqa: S106


def make(**changes) -> Decision:
    fields = {
        "id": new_id(), "title": "Pages are plain HTML", "statement": "The pages are plain HTML with no build step.",
        "scope": Scope.PROJECT, "project": PROJECT, "origin": Origin.APPROVED, "actor": "shaper",
        "state": State.IN_FORCE, "created_at": AT, "topic": "pages",
    }  # fmt: skip
    return Decision(**{**fields, **changes})


def fonts(**changes) -> Decision:
    return make(title="Fonts are local", topic="fonts", statement="Pages load no font from a CDN.", **changes)


def picked(*ids: str) -> pick_tools.PickResult:
    return pick_tools.PickResult(picked=[{"id": i, "note": "it governs the work"} for i in ids])


def building(picking, *chosen: Decision, **draft) -> None:
    """A Change approved on a pick of *chosen*, then at its build step."""
    picking.save(**draft)
    assert picking.ask(1).status_code == 200
    picking.picks.append(picked(*(d.id for d in chosen)))
    picking.verdicts.append(tools.ReviewResult(verdict="pass"))
    picking.step()
    assert picking.approve(1).status_code == 200
    c = picking.approved()
    c.plan = Plan(tasks=[Task(id="t1", title="Add farewell", scope=["packages/app"], checks=["true"])])
    c.step = Step(kind=StepKind.BUILD, task="t1")
    picking.store.write(Lock(picking.slug), c)


def build(picking):
    c = picking.change()
    runner._step(picking.store, Lock(picking.slug), c, loop.next_step(c, AT), picking.repo)  # noqa: SLF001
    return picking.change()


def asked(question: str = QUESTION) -> types.CallToolRequestParams:
    return types.CallToolRequestParams(name=tools.LOOKUP, arguments={"question": question})


def relayed(inbox, params: types.CallToolRequestParams) -> types.CallToolResult:
    call = step_mcp.relay(inbox)._request_handlers["tools/call"].handler  # noqa: SLF001 - the relay's own handler
    return asyncio.run(call(None, params))


def test_a_workers_lookup_in_an_sdk_step_reads_the_complete_list_answers_whole_and_counts_its_spend(
    picking, monkeypatch
):
    rule, other = picking.put(make()), picking.put(fonts())
    building(picking, rule)
    picking.picks += [picked(other.id), "error"]
    said = []

    async def run(cfg):
        if cfg.role == tools.PICKER:
            return await picking.run(cfg)
        step = sdk_adapter._Step(cfg, asyncio.get_running_loop())  # noqa: SLF001
        (tool,) = [t for t in step.tools() if t.name == tools.LOOKUP]
        assert tool.is_terminal is False  # the worker's turn goes on
        for _ in range(2):
            reply = await tool.handler(SimpleNamespace(arguments={"question": QUESTION}))
            said.append(json.loads(reply.text_result_for_llm))
        return Run(cfg.session_id, "error", detail="stopped after its lookups", termination=DONE)

    monkeypatch.setattr(runner.sdk_adapter, "run", run)

    c = build(picking)

    answer, failed = said
    whole = {"id": other.id, "title": other.title, "statement": other.statement, "scope": "project"}
    assert answer == {"decisions": [whole | {"origin": "approved", "note": "it governs the work"}]}
    assert failed["failed"].startswith("its session ended error")  # never an empty answer
    picker = picking.pickers()[1]
    assert (len(picking.pickers()), picker.model, picker.effort) == (3, "gpt-6.1-sol", "medium")
    assert all(x in picker.message for x in (QUESTION, rule.id, other.id, "Title: Add farewell"))
    assert picker.limit <= pick_tools.LIMIT
    assert c.spend.credits == 12.0  # the shaping pick and the answered lookup
    assert set(c.decisions_baseline.said) == {rule.id}  # a lookup answers; it attaches nothing
    exits = [e["exit"] for e in picking.store.events(picking.slug) if e.get("kind") == lookup.LABEL]
    assert exits == ["ok", "failed"]


def test_a_workers_lookup_in_a_window_step_goes_through_the_relay_with_a_picks_timeout(picking, monkeypatch):
    rule, other = picking.put(make()), picking.put(fonts())
    building(picking, rule)
    picking.picks.append(picked(other.id))
    waited, said, real = [], [], step_mcp._LOCAL  # noqa: SLF001

    class Opener:
        def open(self, request, timeout):
            waited.append(timeout)
            return real.open(request, timeout=timeout)

    def window(cfg, inbox):
        gate = Gate(cfg, Run(cfg.session_id, runtime="window"), lambda **_e: None, lambda: None)
        with Inbox(gate, inbox):
            names = [t["name"] for t in step_mcp.forward(inbox, "GET", "/tools")["tools"]]
            done = relayed(inbox, asked())
        said.append((names, done.is_error, json.loads(done.content[0].text)))
        return Run(cfg.session_id, "error", detail="stopped after its lookup", termination=DONE, runtime="window")

    monkeypatch.setattr(sessions, "in_window", lambda _profile: True)
    monkeypatch.setattr(sessions.vscode_adapter, "run", window)
    monkeypatch.setattr(step_mcp, "_LOCAL", Opener())

    c = build(picking)

    [(names, error, answer)] = said
    assert tools.LOOKUP in names
    assert (error, [d["id"] for d in answer["decisions"]]) == (False, [other.id])
    assert waited == [step_mcp.TIMEOUT, pick_tools.WAIT]  # a pick's time, not a result check's
    assert c.spend.credits == 12.0
    assert set(c.decisions_baseline.said) == {rule.id}


def test_a_window_lookup_still_running_when_the_window_delivers_keeps_its_spend(picking, monkeypatch):
    rule, other = picking.put(make()), picking.put(fonts())
    building(picking, rule)
    picking.picks.append(picked(other.id))
    started, release, said, asking = threading.Event(), threading.Event(), [], []

    async def blocked(cfg):
        started.set()
        await asyncio.to_thread(release.wait, 10)
        return await picking.run(cfg)

    def window(cfg, inbox):
        gate = Gate(cfg, Run(cfg.session_id, runtime="window"), lambda **_e: None, lambda: None)
        with Inbox(gate, inbox):
            asking.append(threading.Thread(target=lambda: said.append(relayed(inbox, asked()))))
            asking[0].start()
            assert started.wait(10)
            gate.finish("error", None, "stopped while its lookup runs")
        cfg.journal.delivered()  # the runner's Change is replaced by a copy while the lookup runs
        release.set()
        return Run(cfg.session_id, "error", detail="stopped", termination=DONE, runtime="window")

    monkeypatch.setattr(runner.sdk_adapter, "run", blocked)
    monkeypatch.setattr(sessions, "in_window", lambda _profile: True)
    monkeypatch.setattr(sessions.vscode_adapter, "run", window)

    c = build(picking)
    asking[0].join(10)

    assert [d["id"] for d in json.loads(said[0].content[0].text)["decisions"]] == [other.id]
    assert c.spend.credits == 12.0  # the shaping pick and the lookup that ended after the delivery


def test_a_workers_lookup_lists_the_changes_own_decisions_whole(picking, monkeypatch):
    answer = " ".join(["Farewells use the first name only and never the family name,"] * 6)
    drafted = {"question": "Which name does a farewell use?", "answer": answer, "origin": "decided"}
    building(picking, decisions=[drafted])
    picking.picks.clear()  # nothing was in force to pick from
    own = picking.change().brief.decisions[0]
    picking.picks.append(picked(own.id))
    said = []

    async def run(cfg):
        if cfg.role == tools.PICKER:
            return await picking.run(cfg)
        step = sdk_adapter._Step(cfg, asyncio.get_running_loop())  # noqa: SLF001
        (tool,) = [t for t in step.tools() if t.name == tools.LOOKUP]
        reply = await tool.handler(SimpleNamespace(arguments={"question": QUESTION}))
        said.append(json.loads(reply.text_result_for_llm))
        return Run(cfg.session_id, "error", detail="stopped after its lookup", termination=DONE)

    monkeypatch.setattr(runner.sdk_adapter, "run", run)

    build(picking)

    whole = {"id": own.id, "title": own.question, "statement": answer, "scope": "change", "origin": "decided"}
    assert said == [{"decisions": [whole | {"note": "it governs the work"}]}]
    assert all(x in picking.pickers()[0].message for x in (own.id, answer))


def test_a_workers_lookup_lists_a_clarification_confirmed_during_the_work_once(picking, monkeypatch):
    building(picking, picking.put(make()))
    c = picking.change()
    clarified = ChangeDecision(
        id=new_id(), title="Which language does the greeting use?", text="The greeting is in English.",
        origin="decided", at=AT,
    )  # fmt: skip
    c.decisions += [clarified, clarified.model_copy()]  # the same id twice: listed once
    picking.store.write(Lock(picking.slug), c)
    picking.picks.append(picked(clarified.id))
    said = []

    async def run(cfg):
        if cfg.role == tools.PICKER:
            return await picking.run(cfg)
        step = sdk_adapter._Step(cfg, asyncio.get_running_loop())  # noqa: SLF001
        (tool,) = [t for t in step.tools() if t.name == tools.LOOKUP]
        said.append(
            json.loads((await tool.handler(SimpleNamespace(arguments={"question": QUESTION}))).text_result_for_llm)
        )
        return Run(cfg.session_id, "error", detail="stopped after its lookup", termination=DONE)

    monkeypatch.setattr(runner.sdk_adapter, "run", run)

    build(picking)

    whole = {"id": clarified.id, "title": clarified.title, "statement": clarified.text, "scope": "change"}
    assert said == [{"decisions": [whole | {"origin": "decided", "note": "it governs the work"}]}]
    assert picking.pickers()[-1].message.count(f"{clarified.id} |") == 1


class Blocked:
    """A lookup's work that waits until released, counting how many run at once."""

    def __init__(self, done: Run) -> None:
        self.done, self.release, self.entered, self.running, self.most = done, threading.Event(), [], 0, 0

    def __call__(self, *_args):
        self.running += 1
        self.most = max(self.most, self.running)
        self.entered.append(1)
        self.release.wait(10)
        self.running -= 1
        return {"decisions": []}, self.done


def until(ready) -> None:
    end = time.monotonic() + 10
    while not ready():
        assert time.monotonic() < end
        time.sleep(0.01)


def test_a_second_lookup_while_one_runs_is_refused_as_busy(monkeypatch):
    work, logged = Blocked(Run("look", "result")), []
    monkeypatch.setattr(lookup, "worker", work)
    monkeypatch.setattr(lookup.sessions, "logged", lambda *a: logged.append(a))
    asked_ = lookup.Asked(None, None, lambda: "change")
    question = pick_tools.Question(question=QUESTION)
    with ThreadPoolExecutor(2) as pool:
        first = pool.submit(asked_, question)
        until(lambda: asked_.admitted == 1 and work.entered)
        assert json.loads(asked_(question)) == {"failed": lookup.BUSY}  # one picker beside the step's session
        work.release.set()
        assert json.loads(first.result(10)) == {"decisions": []}
    assert (work.most, logged) == (1, [])  # spend counts when the step settles


def test_a_steps_settlement_rejects_later_lookups_waits_for_the_running_one_and_counts_its_spend(monkeypatch):
    work, logged, change = Blocked(Run("look", "result")), [], ["taken at the start"]
    monkeypatch.setattr(lookup, "worker", work)
    monkeypatch.setattr(lookup.sessions, "logged", lambda _s, _l, c, done, fields: logged.append((c, done, fields)))
    asked_ = lookup.Asked(None, None, lambda: change[0])
    question = pick_tools.Question(question=QUESTION)
    with ThreadPoolExecutor(2) as pool:
        running = pool.submit(asked_, question)
        until(lambda: asked_.admitted == 1 and work.entered)
        change[0] = "the runner's now"  # a window's delivery replaced it
        settling = pool.submit(asked_.settled, lambda: "the step's run")
        until(lambda: not asked_.open)
        assert json.loads(asked_(question)) == {"failed": lookup.ENDED}
        assert not settling.done()  # the running lookup is waited for
        work.release.set()
        assert settling.result(10) == "the step's run"
        assert json.loads(running.result(10)) == {"decisions": []}  # admitted before settlement: answered
    assert (len(work.entered), logged) == (1, [("the runner's now", work.done, {"kind": lookup.LABEL, "exit": "ok"})])


def host_lookup(picking) -> dict:
    return picking.http.post("/api/next/decisions/lookup", json={"question": QUESTION}).json()


def test_a_hosts_lead_chat_lookups_run_one_at_a_time_and_a_waiting_one_gives_up(picking, monkeypatch):
    work = Blocked(Run("look", "result", termination=DONE))
    monkeypatch.setattr(lookup, "chat", work)
    monkeypatch.setattr(lookup, "SLOT_WAIT", 0.05)
    with ThreadPoolExecutor(1) as pool:
        first = pool.submit(host_lookup, picking)
        until(lambda: work.entered)
        assert host_lookup(picking) == {"failed": lookup.BUSY}
        work.release.set()
        assert first.result(10) == {"decisions": []}
    assert (host_lookup(picking), work.most) == ({"decisions": []}, 1)


def test_a_lead_chats_lookup_whose_processes_are_not_confirmed_gone_holds_the_next_until_a_rescan(picking, monkeypatch):
    picking.put(make())
    left, alive = Termination(confirmed=False, survivors=(4242,)), [True]

    async def run(cfg):
        picking.told.append(cfg)
        return Run(cfg.session_id, "result", picked(), termination=left, pids={4242: 1.0})

    monkeypatch.setattr(sdk_adapter, "run", run)
    monkeypatch.setattr(lookup.processes, "alive", lambda pid, _created: alive[0] if pid == 4242 else False)

    first, held = host_lookup(picking), host_lookup(picking)
    alive[0] = False
    rescanned = host_lookup(picking)

    assert first["failed"].startswith("its pick cannot be trusted")
    assert held == {"failed": lookup.LEFT}
    assert rescanned["failed"].startswith("its pick cannot be trusted")  # it ran: the processes were seen gone
    assert len(picking.pickers()) == 2


def test_a_lookup_the_relay_gets_no_answer_for_is_failed_not_a_stopped_step(tmp_path):
    lost = relayed(tmp_path / "gone.json", asked())
    assert (lost.is_error, json.loads(lost.content[0].text)) == (
        True,
        {"failed": "Delivery gave no answer to the lookup"},
    )
    gone = relayed(tmp_path / "gone.json", types.CallToolRequestParams(name="submit_result", arguments={}))
    assert gone.content[0].text == step_mcp.NOT_RUNNING


class Answer(io.BytesIO):
    def __init__(self, data: bytes, status: int) -> None:
        super().__init__(data)
        self.status = status


class Loopback:
    """The chat server's opener, answered in-process by a host; it keeps each request's timeout."""

    def __init__(self, http: TestClient) -> None:
        self.http, self.waited = http, []

    def open(self, request, timeout):
        self.waited.append(timeout)
        url = urllib.parse.urlsplit(request.full_url)
        r = self.http.request(request.get_method(), f"{url.path}?{url.query}", content=request.data,
                              headers=dict(request.header_items()))  # fmt: skip
        if r.status_code >= 400:
            raise urllib.error.HTTPError(request.full_url, r.status_code, "", r.headers, io.BytesIO(r.content))
        return Answer(r.content, r.status_code)


def chat_tool(name: str, **args: object) -> dict:
    return asyncio.run(mcp_server.mcp.call_tool(name, args)).structured_content


def test_a_lead_chats_lookup_through_the_project_host_waits_past_fifteen_seconds_and_a_failure_says_failed(
    picking, monkeypatch
):
    rule, general = picking.put(make()), picking.put(fonts(scope=Scope.GLOBAL, project=""))
    chat = chat_client.Chat.__new__(chat_client.Chat)
    chat.repo, chat.home = picking.repo, picking.store.root
    opener = Loopback(picking.http)
    monkeypatch.setattr(chat_client.Chat, "record", lambda _self: RECORD)
    monkeypatch.setattr(chat_client, "_LOCAL", opener)
    monkeypatch.setitem(mcp_server._STATE, "chat", chat)  # noqa: SLF001 - the server's one chat
    picking.picks += [picked(general.id), "error"]

    found, failed = chat_tool("lookup_decisions", question=QUESTION), chat_tool("lookup_decisions", question=QUESTION)

    assert [(d["id"], d["scope"]) for d in found["decisions"]] == [(general.id, "global")]
    assert failed["failed"].startswith("its session ended error")
    assert opener.waited == [15.0, pick_tools.WAIT, pick_tools.WAIT]  # the host's chat contract is asked once first
    assert pick_tools.WAIT > 15  # the chat's other calls wait 15 seconds
    message = picking.pickers()[0].message
    assert all(x in message for x in (QUESTION, rule.id, general.id))
    assert "## The work" not in message  # no Change: no brief


def test_a_lead_chats_lookup_in_owlbears_workspace_goes_through_the_machine_hosts_mount(
    tmp_path, shared_repo, monkeypatch
):
    shared = DataRepo(shared_repo[0])
    own, general = make(project="owlbear"), fonts(scope=Scope.GLOBAL, project="")
    project = make(title="Invoices are PDF", statement="Invoices are sent as PDF.")
    for d, folder in ((own, "owlbear"), (general, ""), (project, PROJECT)):
        (shared.root / folder).mkdir(exist_ok=True)
        write(d, shared.root / folder)
    monkeypatch.setenv("OWLBEAR_DATA", str(shared.root))
    told = []

    async def run(cfg):
        told.append(cfg)
        return Run(cfg.session_id, "result", picked(own.id), usage={"credits": 6.0}, termination=DONE)

    monkeypatch.setattr(sdk_adapter, "run", run)
    machine = Machine(RECORD)
    try:
        opener = Loopback(
            TestClient(app.create(machine), base_url="http://127.0.0.1", headers={"authorization": "Bearer t"})
        )
        monkeypatch.setattr(chat_client.OwlBear, "record", lambda _self: RECORD)
        monkeypatch.setattr(chat_client, "_LOCAL", opener)
        monkeypatch.setitem(mcp_server._STATE, "chat", chat_client.OwlBear(tmp_path))  # noqa: SLF001

        found = chat_tool("lookup_decisions", question=QUESTION)
    finally:
        machine.stop_all()

    assert [d["id"] for d in found["decisions"]] == [own.id]
    assert opener.waited == [15.0, pick_tools.WAIT]  # the host's chat contract first
    [cfg] = told
    assert (cfg.role, own.id in cfg.message, general.id in cfg.message, project.id in cfg.message) == (
        tools.PICKER, True, True, False
    )  # fmt: skip


def unresolved_rule(kind, scope=Scope.PROJECT):
    bad = fonts(conflict=kind == "conflict", scope=scope, project="" if scope is Scope.GLOBAL else PROJECT)
    return (
        bad
        if kind == "conflict"
        else bad.model_copy(
            update={"links": (Link(type=LinkType.REFINES, target=bad.id),)},
        )
    )


@pytest.mark.parametrize("boundary", ["worker", "chat"])
@pytest.mark.parametrize("invalid", ["conflict", "link"])
@pytest.mark.parametrize("with_active", [False, True])
@pytest.mark.parametrize("scope", [Scope.PROJECT, Scope.GLOBAL])
def test_unresolved_scoped_authority_fails_the_whole_lookup_without_running_a_picker(
    picking,
    boundary,
    invalid,
    with_active,
    scope,
):
    active = picking.put(make()) if with_active else None
    if boundary == "worker":
        building(picking, *((active,) if active else ()))
    bad = unresolved_rule(invalid, scope)
    picking.put(bad)
    picking.picks.clear()
    picking.picks.append(picked(*([active.id] if active else []), bad.id))
    before = len(picking.pickers())

    if boundary == "worker":
        answer, done = lookup.worker(picking.store, Lock(picking.slug), picking.change(), QUESTION)
    else:
        answer, done = lookup.chat(picking.shared, PROJECT, QUESTION, picking.store.settings)

    assert answer.get("failed"), answer
    assert "decisions" not in answer
    assert {row["id"] for row in answer["unresolved"]} == {bad.id}
    assert all(set(row) == {"id", "title", "scope", "reason"} and row["reason"] for row in answer["unresolved"])
    assert done is None
    assert len(picking.pickers()) == before


@pytest.mark.parametrize("boundary", ["worker", "chat"])
def test_no_selected_rule_is_still_an_empty_success_when_all_scoped_authority_is_valid(picking, boundary):
    active = picking.put(make())
    if boundary == "worker":
        building(picking, active)
    picking.picks.append(picked())
    if boundary == "worker":
        answer, done = lookup.worker(picking.store, Lock(picking.slug), picking.change(), QUESTION)
    else:
        answer, done = lookup.chat(picking.shared, PROJECT, QUESTION, picking.store.settings)
    assert answer == {"decisions": []}
    assert done is not None


@pytest.mark.parametrize(
    "consumer",
    ["message", "judged", "worker", "chat", "boundary", "context", "baseline", "differences"],
)
def test_a_real_published_shaping_rules_binding_suffix_survives_every_consumer(picking, consumer):
    suffix = "Never retain payment-card numbers."
    text = "Notes use one table, sorted by date, with a header row and no merged cells. " * 4 + suffix
    assert STATEMENT_LIMIT < text.index(suffix) < len(text) <= 500
    building(
        picking,
        decisions=[
            {
                "question": "How are the notes stored?",
                "answer": text,
                "origin": "decided",
                "scope": "project",
            }
        ],
    )
    c = picking.change()
    rule_id = c.brief.decisions[0].id
    view = decision_store.load(picking.shared, PROJECT)
    rule = view.snapshot.get(rule_id).decision
    assert len(rule.statement) <= STATEMENT_LIMIT
    assert suffix not in rule.statement
    assert text in rule.rationale
    picking.picks.clear()
    picking.picks.append(picked(rule_id))

    if consumer == "message":
        assert text in pick.message(None, [rule], "")
    elif consumer == "judged":
        result = Run("picker", "result", picked(rule_id), termination=DONE)
        assert pick.judged(result, [rule], Pick(version=0)).decisions[0].statement == text
    elif consumer == "worker":
        answer, _ = lookup.worker(picking.store, Lock(picking.slug), c, QUESTION)
        assert answer["decisions"][0]["statement"] == text
        assert text in picking.pickers()[-1].message
    elif consumer == "chat":
        answer, _ = lookup.chat(picking.shared, PROJECT, QUESTION, picking.store.settings)
        assert answer["decisions"][0]["statement"] == text
        assert text in picking.pickers()[-1].message
    elif consumer == "boundary":
        chosen, why = pick.reassessed(picking.store, Lock(picking.slug), c, [rule], picking.shared.root)
        assert why == ""
        assert [d.id for d in chosen] == [rule_id]
        assert text in picking.pickers()[-1].message
    elif consumer == "context":
        assert text in step_decisions.entry(rule)
    elif consumer == "baseline":
        assert decisions_gate.baseline(view, c, AT).said[rule_id].statement == text
    else:
        before = decisions_gate.baseline(view, c, AT)
        updated = text.replace(suffix, "Payment-card numbers must be deleted immediately.")
        write(
            rule.model_copy(update={"rationale": rule.rationale.replace(text, updated)}),
            picking.shared.root / PROJECT,
            expected_revision=rule.revision,
        )
        current = decision_store.load(picking.shared, PROJECT)
        after = decisions_gate.baseline(current, c, AT)
        lines = "\n".join(decisions_gate.differences(current.snapshot, before, after))
        assert text in lines
        assert updated in lines


@pytest.mark.parametrize("invalid", ["conflict", "link"])
def test_a_running_workers_sdk_tool_reports_new_unresolved_authority_without_picker_spend(
    picking,
    monkeypatch,
    invalid,
):
    rule = picking.put(make())
    building(picking, rule)
    said, bad = [], unresolved_rule(invalid)

    async def run(cfg):
        if cfg.role == tools.PICKER:
            return await picking.run(cfg)
        picking.put(bad)
        step = sdk_adapter._Step(cfg, asyncio.get_running_loop())  # noqa: SLF001
        (tool,) = [t for t in step.tools() if t.name == tools.LOOKUP]
        reply = await tool.handler(SimpleNamespace(arguments={"question": QUESTION}))
        said.append(json.loads(reply.text_result_for_llm))
        return Run(cfg.session_id, "error", detail="stopped after lookup", termination=DONE)

    monkeypatch.setattr(runner.sdk_adapter, "run", run)
    c = build(picking)
    (answer,) = said
    assert answer["failed"]
    assert "decisions" not in answer
    assert {row["id"] for row in answer["unresolved"]} == {bad.id}
    assert len(picking.pickers()) == 1  # the shaping pick only; lookup consumed no SDK session
    assert c.spend.credits == 6.0


@pytest.mark.parametrize("invalid", ["conflict", "link"])
def test_a_lead_chats_mcp_tool_preserves_failed_authority_and_unresolved_ids(picking, monkeypatch, invalid):
    picking.put(make())
    bad = picking.put(unresolved_rule(invalid))
    chat = chat_client.Chat.__new__(chat_client.Chat)
    chat.repo, chat.home = picking.repo, picking.store.root
    monkeypatch.setattr(chat_client.Chat, "record", lambda _self: RECORD)
    monkeypatch.setattr(chat_client, "_LOCAL", Loopback(picking.http))
    monkeypatch.setitem(mcp_server._STATE, "chat", chat)  # noqa: SLF001

    answer = chat_tool("lookup_decisions", question=QUESTION)

    assert answer["failed"]
    assert "decisions" not in answer
    assert {row["id"] for row in answer["unresolved"]} == {bad.id}
    assert picking.pickers() == []


@pytest.mark.parametrize(
    ("statement", "rationale"),
    [
        ("Keep this rule's\noriginal formatting.", "Whole wording: unrelated rationale"),
        ("Keep this rule\u2026", "Whole wording: a different prefix does not restore that rule"),
    ],
)
def test_whole_binding_text_does_not_promote_unrelated_rationale_or_reformat_ordinary_rules(statement, rationale):
    rule = make(statement=statement, rationale=rationale)
    assert decision_archive.whole(rule) == statement


@pytest.mark.parametrize("boundary", ["worker", "chat"])
def test_unresolved_authority_in_another_project_does_not_block_a_valid_scoped_lookup(picking, boundary):
    active = picking.put(make())
    if boundary == "worker":
        building(picking, active)
    folder = picking.shared.root / "elsewhere"
    folder.mkdir()
    write(make(project="elsewhere", conflict=True), folder)
    picking.picks.append(picked(active.id))

    if boundary == "worker":
        answer, done = lookup.worker(picking.store, Lock(picking.slug), picking.change(), QUESTION)
    else:
        answer, done = lookup.chat(picking.shared, PROJECT, QUESTION, picking.store.settings)

    assert [row["id"] for row in answer["decisions"]] == [active.id]
    assert "failed" not in answer
    assert done is not None


@pytest.mark.parametrize("boundary", ["worker", "chat"])
@pytest.mark.parametrize("invalid", ["conflict", "link"])
def test_a_new_lookup_runs_after_the_owner_resolves_the_invalid_authority(picking, boundary, invalid):
    active = picking.put(make())
    if boundary == "worker":
        building(picking, active)
    bad = picking.put(unresolved_rule(invalid))

    def run():
        if boundary == "worker":
            return lookup.worker(picking.store, Lock(picking.slug), picking.change(), QUESTION)
        return lookup.chat(picking.shared, PROJECT, QUESTION, picking.store.settings)

    failed, done = run()
    assert failed["failed"]
    assert done is None
    write(
        bad.model_copy(update={"conflict": False, "links": ()}),
        picking.shared.root / PROJECT,
        expected_revision=bad.revision,
    )
    picking.picks.clear()
    picking.picks.append(picked(active.id, bad.id))
    answer, done = run()
    assert {row["id"] for row in answer["decisions"]} == {active.id, bad.id}
    assert "failed" not in answer
    assert done is not None
