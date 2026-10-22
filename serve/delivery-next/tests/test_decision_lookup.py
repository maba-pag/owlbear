"""The decision lookup (TD-456, TD-459): workers in SDK and window steps and lead chats ask the picker, which reads the
complete list. A failed lookup says failed, never "none apply"; a lookup attaches nothing to the Change.
"""

import asyncio
import io
import json
import urllib.error
import urllib.parse
from datetime import UTC, datetime
from types import SimpleNamespace

from fastapi.testclient import TestClient
from mcp import types

from owlbear_decisions import Decision, Origin, Scope, State, new_id, write
from owlbear_delivery_next.change_contracts import pick_tools, tools
from owlbear_delivery_next.change_contracts.models import Plan, Step, StepKind, Task
from owlbear_delivery_next.change_flow import loop
from owlbear_delivery_next.commands import mcp_server, runner, step_mcp
from owlbear_delivery_next.local_system import codebase
from owlbear_delivery_next.local_system.data_repo import DataRepo
from owlbear_delivery_next.local_system.processes import Termination
from owlbear_delivery_next.machine_host import app
from owlbear_delivery_next.machine_host.machine import Machine
from owlbear_delivery_next.project_host.host import HostRecord
from owlbear_delivery_next.runtimes import sdk_adapter
from owlbear_delivery_next.runtimes.results import Gate
from owlbear_delivery_next.runtimes.session_result import Run
from owlbear_delivery_next.runtimes.step_inbox import Inbox
from owlbear_delivery_next.state_store.store import Lock
from owlbear_delivery_next.workflow_steps import lookup, sessions

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


def building(picking, *chosen: Decision) -> None:
    """A Change approved on a pick of *chosen*, then at its build step."""
    picking.save()
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
    chat = mcp_server.Chat.__new__(mcp_server.Chat)
    chat.repo, chat.store = picking.repo, picking.store
    opener = Loopback(picking.http)
    monkeypatch.setattr(mcp_server.Chat, "record", lambda _self: RECORD)
    monkeypatch.setattr(mcp_server, "_LOCAL", opener)
    monkeypatch.setitem(mcp_server._STATE, "chat", chat)  # noqa: SLF001 - the server's one chat
    picking.picks += [picked(general.id), "error"]

    found, failed = chat_tool("lookup_decisions", question=QUESTION), chat_tool("lookup_decisions", question=QUESTION)

    assert [(d["id"], d["scope"]) for d in found["decisions"]] == [(general.id, "global")]
    assert failed["failed"].startswith("its session ended error")
    assert opener.waited == [pick_tools.WAIT] * 2
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
        monkeypatch.setattr(mcp_server.OwlBear, "record", lambda _self: RECORD)
        monkeypatch.setattr(mcp_server, "_LOCAL", opener)
        monkeypatch.setitem(mcp_server._STATE, "chat", mcp_server.OwlBear(tmp_path))  # noqa: SLF001

        found = chat_tool("lookup_decisions", question=QUESTION)
    finally:
        machine.stop_all()

    assert [d["id"] for d in found["decisions"]] == [own.id]
    assert opener.waited == [pick_tools.WAIT]
    [cfg] = told
    assert (cfg.role, own.id in cfg.message, general.id in cfg.message, project.id in cfg.message) == (
        tools.PICKER, True, True, False
    )  # fmt: skip
