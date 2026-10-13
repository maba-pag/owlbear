"""TD-69/TD-70/TD-72: each worker role is offered only the tools its agent file names, in both runtimes, and the
project's owlbear-memory in the shared repository."""

import json
from pathlib import Path
from types import SimpleNamespace

from owlbear_delivery_next import preload, sdk_adapter, tools
from owlbear_delivery_next import window_files as wf
from owlbear_delivery_next.models import StepKind
from owlbear_delivery_next.permissions import Policy
from owlbear_delivery_next.tools import Worktree

ROLES = ("builder", "planner", "reviewer")
SDK_TOOLS = {  # the runtime's built-in tools, the same for every model (tools.list, runtime research P24)
    *("bash", "read_bash", "list_bash", "stop_bash", "view", "create", "edit", "glob", "grep", "web_fetch"),
    *("task", "read_agent", "list_agents", "write_agent"),
}
MEMORY_TOOLS = {"recall_memory", "save_memory", "assess_memories"}
RESULT_TOOLS = [s.name for s in tools.SPECS]


INBOX = Path("/s/0123456789abcdef0123.json")
FIELDS = {
    "kind": StepKind.BUILD,
    "worktree": Path(),
    "session_id": "s1",
    "message": "m",
    "resume": False,
    "policy": Policy(Path(), ()),
    "observe": lambda: Worktree("a" * 40, "b" * 40),
    "checks": (),
    "model": "gpt-6-luna",
}


def options(**kw) -> dict:
    loop = SimpleNamespace(call_soon_threadsafe=lambda *_: None)
    return sdk_adapter._Step(sdk_adapter.Session(**(FIELDS | kw)), loop).options()  # noqa: SLF001


def window_names(role: str, memory: Path | None = None) -> list[str]:
    head = wf.agent(role, INBOX, memory)(None).split("---")[1]
    line = next(ln for ln in head.splitlines() if ln.startswith("tools: ["))
    return line.removeprefix("tools: [").removesuffix("]").split(", ")


def test_each_agent_names_only_tools_both_runtimes_know() -> None:
    for role in ROLES:
        names = preload.tools(role)
        assert names
        for name in names:
            server, _, tool = name.partition("/")
            assert name in SDK_TOOLS or (server == preload.MEMORY and tool in MEMORY_TOOLS)


def test_only_the_builder_writes_files_and_every_role_recalls_memory() -> None:
    for role in ROLES:
        names = set(preload.tools(role))
        assert bool(names & {"create", "edit"}) == (role == "builder")
        assert f"{preload.MEMORY}/recall_memory" in names
    assert f"{preload.MEMORY}/save_memory" not in preload.tools("reviewer")


def test_the_sdk_agent_is_offered_its_own_tools_and_the_result_tools() -> None:
    for kind, role in sdk_adapter.ROLES.items():
        assert sdk_adapter.agent(kind)["tools"] == [*preload.tools(role), *RESULT_TOOLS]
    assert options(kind=StepKind.REVIEW)["custom_agents"][0]["tools"] == [*preload.tools("reviewer"), *RESULT_TOOLS]


def test_the_projects_memory_folder_is_given_to_the_memory_server(tmp_path) -> None:
    server = options(memory=tmp_path)["mcp_servers"][preload.MEMORY]
    assert server["args"] == ["-m", preload.MEMORY_MODULE]
    assert server["env"] == {preload.MEMORY_DIR: str(tmp_path)}


def test_without_a_memory_folder_or_the_memory_server_the_agents_go_on_without_memory(tmp_path, monkeypatch) -> None:
    assert options()["mcp_servers"] == {}
    monkeypatch.setattr(preload, "find_spec", lambda _name: None)
    assert options(memory=tmp_path)["mcp_servers"] == {}
    assert list(json.loads(wf.mcp(INBOX, tmp_path)(None))["mcpServers"]) == [wf.names(INBOX)[0]]


def test_the_sdk_approves_only_the_mcp_tools_the_role_is_offered(tmp_path) -> None:
    def asked(kind: StepKind, server: str, tool: str) -> str:
        cfg = sdk_adapter.Session(**(FIELDS | {"kind": kind, "memory": tmp_path}))
        st = sdk_adapter._Step(cfg, SimpleNamespace(call_soon_threadsafe=lambda *_: None))  # noqa: SLF001
        request = SimpleNamespace(kind="mcp", server_name=server, tool_name=f"{server}-{tool}", read_only=False)
        return type(st.permission(request, None)).__name__

    assert asked(StepKind.BUILD, preload.MEMORY, "save_memory") == "PermissionDecisionApproveOnce"
    assert asked(StepKind.PLAN, preload.MEMORY, "save_memory") == "PermissionDecisionApproveOnce"
    assert asked(StepKind.REVIEW, preload.MEMORY, "save_memory") == "PermissionDecisionReject"
    assert asked(StepKind.BUILD, preload.MEMORY, "curate_memories") == "PermissionDecisionReject"
    assert asked(StepKind.BUILD, "uv", "uv-init") == "PermissionDecisionReject"


def test_the_window_agent_offers_the_same_tools_and_this_steps_servers_tools(tmp_path) -> None:
    relay, memory = wf.names(INBOX)
    servers = json.loads(wf.mcp(INBOX, tmp_path)(None))["mcpServers"]
    assert list(servers) == [relay, memory]  # unique to the step: the host disables a name another holds (P21)
    assert servers[memory]["env"] == {preload.MEMORY_DIR: str(tmp_path)}
    assert servers[memory]["args"] == ["-m", preload.MEMORY_MODULE]
    for role in ROLES:  # the window runs the same harness, which offered exactly these names live (TD-69)
        own = [n.replace(f"{preload.MEMORY}/", f"{memory}/") for n in preload.tools(role)]
        assert window_names(role, tmp_path) == [*own, *(f"{relay}/{t}" for t in RESULT_TOOLS)]


def test_a_window_without_a_memory_folder_gets_no_memory_server_and_no_memory_tools() -> None:
    assert list(json.loads(wf.mcp(INBOX)(None))["mcpServers"]) == [wf.names(INBOX)[0]]
    for role in ROLES:
        assert not [n for n in window_names(role) if "memory" in n]
        assert [n for n in window_names(role) if "/" not in n] == [n for n in preload.tools(role) if "/" not in n]


def test_the_window_agent_names_the_relay_its_step_configures(tmp_path) -> None:
    inbox = tmp_path / "0123456789abcdef0123.json"
    (server,) = json.loads(wf.mcp(inbox)(None))["mcpServers"]
    assert server == wf.names(inbox)[0]
    assert f"{server}/submit_result" in wf.agent("planner", inbox)(None)
