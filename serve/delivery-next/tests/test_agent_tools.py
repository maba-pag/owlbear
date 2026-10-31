"""TD-69/TD-70/TD-72: each worker role is offered only the tools its agent file names, and the project's owlbear-memory
in the shared repository."""

import json
from pathlib import Path
from types import SimpleNamespace

from copilot.generated.session_events import PermissionRequestMemory, PermissionRequestMemoryAction

from owlbear_delivery_next.change_contracts import tools
from owlbear_delivery_next.change_contracts.models import StepKind
from owlbear_delivery_next.change_contracts.permissions import Policy
from owlbear_delivery_next.change_contracts.tools import Worktree
from owlbear_delivery_next.change_contracts.user_config import UserConfig
from owlbear_delivery_next.local_system import preload
from owlbear_delivery_next.runtimes import sdk_adapter, subagents

ROLES = ("builder", "planner", "reviewer", "challenger", "design-judge")
SDK_TOOLS = {  # the runtime's built-in tools, the same for every model (tools.list, runtime research P24)
    *("bash", "read_bash", "list_bash", "stop_bash", "view", "create", "edit", "glob", "grep", "web_fetch"),
    *("task", "read_agent", "list_agents", "write_agent"),
}
MEMORY_TOOLS = {"recall_memory", "save_memory", "assess_memories"}
COPILOT_MEMORY = {"store_memory", "vote_memory"}  # the runtime's own, with memory on (D-01M69EQN3KZE2QSBPH1CMDFK22)
RESULT_TOOLS = [s.name for s in tools.SPECS]


FIELDS = {
    "kind": StepKind.BUILD,
    "worktree": Path(),
    "session_id": "s1",
    "message": "m",
    "resume": False,
    "policy": Policy(Path()),
    "observe": lambda: Worktree("a" * 40, "b" * 40),
    "checks": (),
    "model": "gpt-6-luna",
}


def options(**kw) -> dict:
    loop = SimpleNamespace(call_soon_threadsafe=lambda *_: None)
    return sdk_adapter._Step(sdk_adapter.Session(**(FIELDS | kw)), loop).options()  # noqa: SLF001


def test_each_agent_names_only_tools_both_runtimes_know() -> None:
    for role in ROLES:
        names = preload.tools(role)
        assert names
        for name in names:
            server, _, tool = name.partition("/")
            assert name in SDK_TOOLS | COPILOT_MEMORY or (server == preload.MEMORY and tool in MEMORY_TOOLS)


def test_only_the_builder_writes_files_and_every_role_recalls_memory() -> None:
    for role in ROLES:
        names = set(preload.tools(role))
        assert bool(names & {"create", "edit"}) == (role == "builder")
        assert f"{preload.MEMORY}/recall_memory" in names
        assert (f"{preload.MEMORY}/save_memory" in names) == (role in {"builder", "planner"})


def test_the_sdk_agent_is_offered_its_own_tools_and_the_result_tools() -> None:
    for kind, role in sdk_adapter.ROLES.items():  # every step's own worker may look decisions up (TD-456)
        assert sdk_adapter.agent(kind)["tools"] == [*preload.tools(role), *RESULT_TOOLS, tools.LOOKUP]
    reviewer = [*preload.tools("reviewer"), *RESULT_TOOLS, tools.LOOKUP]
    assert options(kind=StepKind.REVIEW)["custom_agents"][0]["tools"] == reviewer


def test_the_projects_memory_folder_and_global_memory_are_given_to_the_memory_server(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)  # the agent list comes from the package, not the folder the host runs in
    mine = tmp_path / "shop-site" / "memory"
    server = options(memory=mine)["mcp_servers"][preload.MEMORY]
    agents = set(server["env"].pop(preload.MEMORY_AGENTS).split(","))
    assert server["args"] == ["-m", preload.MEMORY_MODULE]
    assert server["env"] == {preload.MEMORY_DIR: str(mine), preload.MEMORY_GLOBAL: str(tmp_path / "memory")}
    assert {
        "builder",
        "curator",
        "challenger",
        "shaper",
        "spotter",
        "knowledge-ingestor",
        "knowledge-enricher",
    } <= agents
    assert not any(name.startswith("owlbear-") for name in agents)


def test_without_a_memory_folder_or_the_memory_server_the_agents_go_on_without_memory(tmp_path, monkeypatch) -> None:
    assert options()["mcp_servers"] == {}
    assert options()["enable_file_hooks"] is False  # the project's agent hooks stay off too (TD-142)
    monkeypatch.setattr(preload, "find_spec", lambda _name: None)
    assert options(memory=tmp_path)["mcp_servers"] == {}


def test_a_step_loads_only_its_role_and_delivery_skills_never_discovered_or_bundled_ones() -> None:
    """TD-167, TD-274, TD-134: discovery stays off explicitly, so an SDK default can never turn project agents on."""
    got = options()
    assert (got["enable_config_discovery"], got["included_builtin_skills"]) == (False, [])
    assert [a["name"] for a in got["custom_agents"]] == ["owlbear-builder"]
    assert all(Path(d).parent == preload.directory() for d in got["skill_directories"])


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


def test_a_copilot_memory_save_passes_only_with_the_switch_on_for_a_role_that_lists_it() -> None:
    """D-01M69EBRBBW97001KZ43C0BJM1, D-01M69EQN3KZE2QSBPH1CMDFK22: the runtime's own memory requests, as sent."""
    fact = "OB847-SENTINEL fact text"

    def asked(kind: StepKind, action: PermissionRequestMemoryAction | None, *, on: bool) -> tuple[str, list]:
        events = []
        user = UserConfig(instructions=False, skills=False, memory=on)
        journal = sdk_adapter.Journal(events.append)
        cfg = sdk_adapter.Session(**(FIELDS | {"kind": kind, "user": user, "journal": journal}))
        st = sdk_adapter._Step(cfg, SimpleNamespace(call_soon_threadsafe=lambda *_: None))  # noqa: SLF001
        request = PermissionRequestMemory(fact=fact, action=action, subject="testing", citations="a.py:1")
        return type(st.permission(request, None)).__name__, events

    store, vote = PermissionRequestMemoryAction.STORE, PermissionRequestMemoryAction.VOTE
    assert asked(StepKind.BUILD, store, on=True)[0] == "PermissionDecisionApproveOnce"
    assert asked(StepKind.BUILD, vote, on=True)[0] == "PermissionDecisionApproveOnce"
    for refused in (asked(StepKind.BUILD, store, on=False), asked(StepKind.REVIEW, store, on=True),
                    asked(StepKind.BUILD, None, on=True)):  # fmt: skip
        assert refused[0] == "PermissionDecisionReject"
        denied = [e for e in refused[1] if e["event"] == "denied"]
        assert denied
        assert fact not in json.dumps(denied)  # Delivery's own log never holds the fact


def test_each_role_is_offered_only_its_own_agent_and_the_builtins_follow_its_setting() -> None:
    for kind, role in sdk_adapter.ROLES.items():
        off, on = options(kind=kind), options(kind=kind, subagents=True)
        for offered in (off, on):
            assert [(a["name"], a["infer"]) for a in offered["custom_agents"]] == [(f"owlbear-{role}", False)]
        assert (off["excluded_builtin_agents"], on["excluded_builtin_agents"]) == (list(subagents.BUILTINS), [])
        granted = [o["custom_agents"][0]["tools"] for o in (off, on)]
        assert [subagents.LAUNCHER in g for g in granted] == [False, True]
    assert "general-purpose" in subagents.BUILTINS
