"""TD-99/TD-106/TD-108/TD-111: each role has its own agent file, whose tools section explains exactly what it is
granted, whose prose names only granted tools, and which each runtime offers only what that runtime may run."""

import asyncio
import re
from collections.abc import Sequence
from importlib.resources import files
from pathlib import Path
from types import SimpleNamespace

import pytest

from owlbear_delivery_next import mcp_server, preload, prompts, roles, sdk_adapter, sessions, setup, tools
from owlbear_delivery_next import window_files as wf
from owlbear_delivery_next.config import Layer, resolve
from owlbear_delivery_next.models import StepKind
from owlbear_delivery_next.permissions import Policy
from owlbear_delivery_next.results import Gate
from owlbear_delivery_next.session_result import Run

AGENTS = ("builder", "planner", "reviewer", "challenger", "designer")
PENDING = {"preparer"}  # check preparation runs as the builder until the TD-96 preparation contract exists
CHAT = "shaper"  # the owner's chat agent, checked with the chat (TD-93), not a worker role
SDK_TOOLS = {  # the SDK runtime's built-in tools (tools.list, runtime research P24)
    *("bash", "read_bash", "list_bash", "stop_bash", "view", "create", "edit", "glob", "grep", "web_fetch"),
    *("task", "read_agent", "list_agents", "write_agent"),
}
MEMORY_TOOLS = {"recall_memory", "save_memory", "assess_memories"}
CHAT_TOOLS = {"save_brief", "save_visual_check", "show_status", "answer_question"}  # the owner chat's server
WINDOW_TOOLS = {"ask_user"}  # a window chat's structured question (live probe, TD-109)
VOCABULARY = SDK_TOOLS | MEMORY_TOOLS | CHAT_TOOLS | WINDOW_TOOLS | {s.name for s in tools.SPECS}
VOCABULARY |= {tools.FIRST_LOOK, tools.SCAN_DESIGN}
ALIASES = (f"{preload.MEMORY}/", f"{setup.SERVER}/")  # a server's tool is named bare or as <server>/<tool>
SHAPER_TOOLS = [  # the names a window chat's agent file grants, each verified live (TD-109)
    *("view", "glob", "grep", "web_fetch", "ask_user", "owlbear-memory/recall_memory", "owlbear-memory/save_memory"),
    *(f"{setup.SERVER}/{name}" for name in ("save_brief", "save_visual_check", "show_status", "answer_question")),
]
VERBS = "submit|report|ask|recall|save|assess|scan|read|list|write|stop"
LOOKALIKE = re.compile(rf"(?:{VERBS})_[a-z_]+|[a-z_]+_(?:bash|agents?|memory|memories)")  # unknown: a tool typo
NOT_GRANTED = "Not granted:"
INBOX = Path("/s/0123456789abcdef0123.json")


def bare(name: str) -> str:
    return next((name.removeprefix(a) for a in ALIASES if name.startswith(a)), name)


def ticks(text: str) -> set[str]:
    return {bare(t) for t in re.findall(r"`([^`\n]+)`", text)}


def entries(body: str) -> list[str]:
    """The ``<tools>`` section's entries, one per tool or family, continuation lines joined."""
    section = body.split("<tools>", 1)[1].split("</tools>", 1)[0] if "<tools>" in body else ""
    return [" ".join(e.split()) for e in re.split(r"\n- ", "\n" + section.strip()) if e.strip()]


def forbidden(body: str) -> set[str]:
    return {t for e in entries(body) if e.startswith(NOT_GRANTED) for t in ticks(e)}


def entry(body: str, name: str) -> str:
    return next(e for e in entries(body) if name in ticks(e) and not e.startswith(NOT_GRANTED))


def prose(body: str) -> str:
    """The body without its Not granted entry, the one place a forbidden tool may be named."""
    kept, skip = [], False
    for line in body.splitlines():
        skip = line.startswith(f"- {NOT_GRANTED}") or (skip and line.startswith("  "))
        kept += [] if skip else [line]
    return "\n".join(kept)


def audit(granted: Sequence[str], body: str) -> list[str]:
    """What breaks the alignment of one agent's grants, its tools section and its prose."""
    grants = {bare(g) for g in granted}
    explained = {t for e in entries(body) if not e.startswith(NOT_GRANTED) for t in ticks(e) & VOCABULARY}
    named = ticks(prose(body))
    problems = [f"granted, not explained in <tools>: {n}" for n in sorted(grants - explained)]
    problems += [f"explained in <tools>, not granted: {n}" for n in sorted(explained - grants)]
    problems += [f"named in prose, not granted: {n}" for n in sorted((named & VOCABULARY) - grants)]
    problems += [f"unknown tool name: {n}" for n in sorted(n for n in named - VOCABULARY if LOOKALIKE.fullmatch(n))]
    return problems + [f"listed as not granted, but granted: {n}" for n in sorted(forbidden(body) & grants)]


def granted(role: str) -> list[str]:
    return [*preload.tools(role), *tools.results(role, ui=True), *tools.results(role, ui=False)]


def test_every_worker_role_has_its_own_agent_file_or_is_explicitly_pending() -> None:
    folder = files("owlbear_delivery_next").joinpath("agents")
    for role in set(roles.DEFAULTS) - {CHAT}:
        assert folder.joinpath(f"{role}.md").is_file() == (role not in PENDING), role
    assert set(AGENTS) == set(roles.DEFAULTS) - PENDING - {CHAT}
    assert {r for k, r in roles.SESSIONS.items() if "challenge" in k} == {"challenger"}


@pytest.mark.parametrize("role", AGENTS)
def test_each_agent_explains_exactly_its_grants_and_names_only_granted_tools(role) -> None:
    _, body = preload.agent_file(role)
    assert audit(granted(role), body) == []


@pytest.mark.parametrize("role", AGENTS)
def test_conditional_tools_say_their_condition_and_the_window_drops_sdk_only_ones(role, tmp_path) -> None:
    _, body = preload.agent_file(role)
    for name in set(tools.results(role, ui=True)) - set(tools.results(role, ui=False)):
        assert "UI Changes only" in entry(body, name)
    sdk_only = [n for n in preload.tools(role) if n in wf.SDK_ONLY]
    for name in sdk_only:
        assert "SDK runs only" in entry(body, name)
    window = wf.agent(role, INBOX, tmp_path, ui=True)(None)
    offered = {n.split("/")[-1] for n in window.split("tools: [", 1)[1].split("]", 1)[0].split(", ")}
    assert offered == {bare(n) for n in preload.tools(role) if n not in wf.SDK_ONLY} | {*tools.results(role, ui=True)}
    assert set(sdk_only) <= set(sdk_adapter.agent(StepKind.REVIEW, role=role)["tools"])
    note = window.rsplit("\n\n", 1)[1]
    assert ticks(note) & VOCABULARY == set(tools.results(role, ui=True))


def test_the_planner_alone_keeps_subagents_and_only_in_sdk_runs() -> None:
    assert {r for r in AGENTS if set(preload.tools(r)) & {"task", "read_agent", "list_agents", "write_agent"}} == {
        "planner"
    }
    assert set(preload.tools("planner")) & {"task", "read_agent", "list_agents", "write_agent"} == wf.SDK_ONLY


def test_judges_are_never_offered_or_told_of_a_question() -> None:
    for role in AGENTS:
        asks = tools.ASK.name in tools.results(role)
        assert asks == (role not in {"challenger", "designer"}), role
        assert (tools.ASK.name in wf.tools_note(role)) == asks
        assert (tools.ASK.name in prompts.reminder(role)) == asks


def test_a_misaligned_agent_fails_naming_the_unexplained_grant_and_the_prose_only_tool() -> None:
    body = "\n<tools>\n\n- Reading: `view`: open files.\n- Results: `submit_result`.\n\n</tools>\n\n"
    body += "Use `edit` to fix it.\n"
    problems = audit(["view", "grep", "submit_result"], body)
    assert problems == ["granted, not explained in <tools>: grep", "named in prose, not granted: edit"]
    assert audit(["view", "submit_result"], body.replace("`edit`", "`save_breif`")) == ["unknown tool name: save_breif"]
    assert audit(["view", "submit_result"], body.replace("`edit`", "`save_brief`")) == [
        "named in prose, not granted: save_brief"
    ]


def test_worker_skills_may_name_tools_but_never_grant_them() -> None:
    skills = sorted(p for p in preload.directory().glob("*/SKILL.md"))
    assert {p.parent.name for p in skills} >= {n for r in AGENTS for n in preload.required(r, ui=True)}
    for path in skills:
        head = path.read_text(encoding="utf-8").split("---", 2)[1]
        assert not [ln for ln in head.splitlines() if ln.split(":", 1)[0].strip() == "tools"], path.parent.name


def _session(label: str, **fields) -> sdk_adapter.Session:
    base = {
        "kind": StepKind.REVIEW,
        "worktree": Path(),
        "session_id": "",
        "message": label,
        "resume": False,
        "policy": Policy(Path(), write=False),
        "observe": lambda: tools.Worktree("h", "h"),
        "checks": (),
    }
    return sdk_adapter.Session(**(base | fields))


class _Made(Exception):  # noqa: N818 - stops the round once its sessions are built
    pass


@pytest.mark.parametrize(
    ("label", "role"),
    [("plan-challenge", "challenger"), ("brief-challenge", "challenger"), (StepKind.REVIEW, "reviewer")],
)
def test_a_judge_runs_as_its_labels_role_in_both_runtimes(label, role, monkeypatch) -> None:
    built: list[sdk_adapter.Session] = []

    def isolated(_store, _lock, _change, source, make, _go, **_kw):
        built.extend(make(source))
        raise _Made

    monkeypatch.setattr(sessions, "isolated", isolated)
    store = SimpleNamespace(read_profile=lambda: None)
    with pytest.raises(_Made):
        sessions.judges(store, SimpleNamespace(slug="c1"), None, Path(), lambda _at: [(label, _session(label))],
                        resolve(None, Layer()))  # fmt: skip
    (cfg,) = built
    assert sdk_adapter.role_of(cfg) == role
    opts = sdk_adapter._Step(cfg, SimpleNamespace(call_soon_threadsafe=lambda *_: None)).options()  # noqa: SLF001
    assert opts["agent"] == role
    assert opts["custom_agents"][0]["skills"] == list(preload.REQUIRED[role])
    offered = {t.name for t in opts["tools"]}
    assert offered == {s.name for s in Gate(cfg, Run("s"), lambda **_: None, lambda: None).specs}
    assert (tools.ASK.name in offered) == (role == "reviewer")
    assert wf.agent_path(sdk_adapter.role_of(cfg)) == f".github/agents/owlbear-{role}.agent.md"


def shaper_file() -> tuple[dict[str, str], list[str], str]:
    text = files("owlbear_delivery_next").joinpath("chat_agents", setup.SHAPER).read_text(encoding="utf-8")
    _, front, body = text.split("---", 2)
    meta = {k.strip(): v.strip() for k, v in (line.split(":", 1) for line in front.strip().splitlines())}
    return meta, [n.strip() for n in meta["tools"].strip("[]").split(",")], body


def test_the_shaper_grants_the_live_verified_tools_and_explains_exactly_them() -> None:
    meta, grants, body = shaper_file()
    assert (meta["name"], meta["skills"]) == ("owlbear-shaper", "[delivery]")
    assert grants == SHAPER_TOOLS
    assert audit(grants, body) == []
    assert forbidden(body) == {"bash", "edit", "create"}  # no terminal, no edit (TD-109)
    assert {t.name for t in asyncio.run(mcp_server.mcp.list_tools())} == CHAT_TOOLS
    assert len(body.splitlines()) <= 130
