"""Files a C+ step needs in its worktree: the window's pins, the step's MCP relay, its agent and hooks off (TD-36).

The window settings pin the harness and model and keep the owner's VS Code MCP servers from starting
(``chat.mcp.access``); ``.github/copilot/settings.local.json`` turns every repository, user and plugin hook off
(``disableAllHooks``), since VS Code's own hook setting does not reach the harness (window-step gate, item 8).

None of them reaches the agent's commits: an untracked file is listed in the clone's ``info/exclude``, a tracked
one is marked ``skip-worktree``; ``restore`` puts back what the step found. The owner's own folder gets only the
harness key, for as long as a shaping chat takes to open (TD-83).
"""

from __future__ import annotations

import contextlib
import json
import re
import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.change_contracts import tools as tool_specs
from owlbear_delivery_next.local_system import git_files, preload, text_files

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from pathlib import Path

HARNESS, DEFAULT_MODEL = "chat.defaultToCopilotHarness", "chat.defaultModel"
HARNESS_LINE = f'\n  "{HARNESS}": true'  # the one line Delivery adds to an owner's settings
HARNESS_ADDED = re.compile(re.escape(HARNESS_LINE) + ",?")
MCP_ACCESS = "chat.mcp.access"  # "none": the owner's VS Code MCP servers stay off; the step's .mcp.json still loads
SETTINGS, MCP = ".vscode/settings.json", ".mcp.json"
HOOKS, NO_HOOKS = ".github/copilot/settings.local.json", "disableAllHooks"
SERVER = "owlbear-step"  # a step's relay is SERVER-<inbox>: the host disables a name another session holds (P21)

type Render = Callable[[str | None], str]


def tools_note(role: str, *, ui: bool = False, judging: bool = False) -> str:
    """The window agent's closing note, naming exactly the Delivery tools its step's relay offers the role."""
    *rest, last = (f"`{name}`" for name in tool_specs.results(role, ui=ui, judging=judging))
    return f"Delivery's tools come from its `owlbear-step-…` MCP server: {', '.join(rest)} and {last}. Never push."


class SettingsError(ValueError):
    """A window file cannot be written safely."""


def _opening(text: str) -> int | None:
    """Just after the opening brace of ``text``'s object, past leading comments; None when it is no object."""
    lines = text.splitlines(keepends=True)
    first = next((i for i, ln in enumerate(lines) if ln.strip() and not ln.lstrip().startswith("//")), None)
    if first is None or not lines[first].lstrip().startswith("{"):
        return None
    return sum(len(ln) for ln in lines[:first]) + lines[first].index("{") + 1


def _strict(data: dict[str, Any], rel: str) -> str:
    """``data`` as strict JSON; NaN or infinity, which Python reads but JSON readers refuse, refuse the step."""
    try:
        return json.dumps(data, indent=2, allow_nan=False) + "\n"
    except ValueError as exc:
        msg = f"{rel} holds a number JSON cannot carry; Delivery writes nothing"
        raise SettingsError(msg) from exc


def _plain_json(text: str) -> str:
    """JSON with comments as plain JSON: comments and trailing commas outside strings go."""
    out: list[str] = []
    i, comma = 0, None  # comma: where in ``out`` the last comma outside a string went, until something follows it
    while i < len(text):
        c = text[i]
        if c == '"':
            end = i + 1
            while end < len(text) and text[end] != '"':
                end += 2 if text[end] == "\\" else 1
            out.append(text[i : end + 1])
            i, comma = end + 1, None
        elif text.startswith("//", i):
            end = text.find("\n", i)
            i = len(text) if end < 0 else end
        elif text.startswith("/*", i):
            end = text.find("*/", i + 2)
            i = len(text) if end < 0 else end + 2
        else:
            if c in "}]" and comma is not None:
                out[comma] = ""
            if not c.isspace():
                comma = len(out) if c == "," else None
            out.append(c)
            i += 1
    return "".join(out)


def _with_settings(old: str | None, model: str) -> str:
    """``old`` with the harness and model pinned; JSON with comments gets the keys after its opening brace."""
    try:
        current: Any = json.loads(old) if old is not None else {}
    except ValueError:
        current = None
    if isinstance(current, dict):
        return _strict(current | {HARNESS: True, DEFAULT_MODEL: model, MCP_ACCESS: "none"}, SETTINGS)
    text = old or ""
    if current is not None or (at := _opening(text)) is None:
        raise SettingsError(f"{SETTINGS} is not a JSON object; set {DEFAULT_MODEL} by hand")  # noqa: EM102, TRY003
    try:
        decoded = json.loads(_plain_json(text))
    except ValueError:
        decoded = None
    if not isinstance(decoded, dict):
        raise SettingsError(f"{SETTINGS} is not a JSON object; set {DEFAULT_MODEL} by hand")  # noqa: EM102, TRY003
    _strict(decoded, SETTINGS)  # the owner's text stays, so it must already be strict JSON
    if {HARNESS, DEFAULT_MODEL, MCP_ACCESS} & set(decoded):  # decoded, so an escaped spelling cannot hide one
        msg = f"{SETTINGS} pins the harness, model or MCP access in a form Delivery can't edit"
        raise SettingsError(msg)
    pins = f'\n  "{HARNESS}": true,\n  "{DEFAULT_MODEL}": {json.dumps(model)},\n  "{MCP_ACCESS}": "none",'
    return text[:at] + pins + text[at:]


def settings(model: str) -> Render:
    """The settings render for ``model``; auto and blank models are refused (TD-32)."""
    if not model.strip() or model.strip().lower() == "auto":
        raise SettingsError("the step model must be named; auto is never used (TD-32)")  # noqa: EM101, TRY003
    return lambda old: _with_settings(old, model)


def hooks_off(old: str | None) -> str:
    """The repository's local Copilot settings with every hook off; its other settings stay."""
    try:
        data = json.loads(old) if old and old.strip() else {}
    except ValueError as exc:
        msg = f"{HOOKS} is not plain JSON; Delivery cannot turn its hooks off"
        raise SettingsError(msg) from exc
    if not isinstance(data, dict):
        raise SettingsError(f"{HOOKS} is not a JSON object; Delivery cannot turn its hooks off")  # noqa: EM102, TRY003
    return _strict(data | {NO_HOOKS: True}, HOOKS)


def write_window_settings(folder: Path, model: str) -> None:
    """Pin the harness and model for the window of ``folder``; other settings are kept."""
    path = folder / SETTINGS
    text = settings(model)(path.read_text() if path.exists() else None)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


@dataclass(frozen=True)
class Added:
    """Delivery's harness line in an owner's settings, and whether Delivery made the file and its folder."""

    file: bool
    folder: bool


def add_harness(folder: Path) -> Added | None:
    """Add the harness key to the owner's ``folder`` settings, every other byte kept; None when they name it already.

    Nothing else changes in the owner's folder, git metadata included: each turn Delivery sends names its model.
    """
    path = folder / SETTINGS
    if part := text_files.linked_part(folder, path):
        raise SettingsError(f"{part} is a symbolic link; Delivery writes nothing through it")  # noqa: EM102, TRY003
    try:
        old = path.read_text()
    except FileNotFoundError:
        made = not path.parent.exists()
        path.parent.mkdir(exist_ok=True)
        with path.open("x") as f:  # never over a file the owner just created
            f.write("{" + HARNESS_LINE + "\n}\n")
        return Added(file=True, folder=made)
    if f'"{HARNESS}"' in old:
        return None
    if (at := _opening(old)) is None:
        raise SettingsError(f"{SETTINGS} is not a JSON object; set {HARNESS} by hand")  # noqa: EM102, TRY003
    comma = "" if old[at:].lstrip().startswith("}") else ","
    text_files.replace_text(path, old[:at] + HARNESS_LINE + comma + old[at:])
    return Added(file=False, folder=False)


def remove_harness(folder: Path, added: Added) -> str:
    """Take Delivery's harness line out again, keeping what the owner changed meanwhile; what failed, or ''."""
    path = folder / SETTINGS
    try:
        rest, found = HARNESS_ADDED.subn("", path.read_text(), count=1)
        if not found:
            return ""
        if added.file and rest == "{\n}\n":
            path.unlink()
            if added.folder:
                with contextlib.suppress(OSError):  # a folder the owner filled meanwhile stays
                    path.parent.rmdir()
        else:
            text_files.replace_text(path, rest)
    except FileNotFoundError:
        return ""
    except OSError as exc:
        return f"could not remove {HARNESS} from {SETTINGS} ({exc}); remove it by hand"
    return ""


def mcp(inbox: Path, memory: Path | None = None) -> Render:
    """``.mcp.json`` with the step's servers added; the project's own servers stay."""

    def render(old: str | None) -> str:
        try:
            data = json.loads(old) if old else {}
        except ValueError as exc:
            raise SettingsError(f"{MCP} is not plain JSON") from exc  # noqa: EM102, TRY003
        if not isinstance(data, dict) or not isinstance(data.get("mcpServers", {}), dict):
            raise SettingsError(f"{MCP} has no mcpServers object")  # noqa: EM102, TRY003
        relay, memory_name = names(inbox)
        args = ["-m", "owlbear_delivery_next", "step-mcp", "--inbox", str(inbox)]
        own = {relay: {"type": "stdio", "command": sys.executable, "args": args, "tools": ["*"]}}
        if (server := preload.memory(memory)) is not None:
            own[memory_name] = {"type": "stdio", **server}
        return _strict({**data, "mcpServers": {**data.get("mcpServers", {}), **own}}, MCP)

    return render


def agent_name(role: str) -> str:
    """The window agent of a session role, unique to Delivery."""
    return f"owlbear-{role}"


def agent_path(role: str) -> str:
    """Where the window finds the role's agent."""
    return f".github/agents/{agent_name(role)}.agent.md"


def agent(  # noqa: PLR0913 - the role, its inbox and memory, and what its job adds
    role: str, inbox: Path, memory: Path | None = None, *, ui: bool = False, judging: bool = False, job: str = ""
) -> Render:
    """The role's agent from the package prose, renamed for the window, with its tools, skills and result note.

    Its tools are the role's, under the same names as in the SDK runtime (the window runs the same harness), with
    memory served by this step's memory server or left out, plus the result tools of this step's
    relay; the window offers nothing else, neither its own question tool nor the owner's MCP tools (TD-69, runtime
    research P19, P23).
    """
    meta, body = preload.agent_file(role)
    relay, memory_name = names(inbox)
    served = preload.memory(memory) is not None
    own = [
        name.replace(f"{preload.MEMORY}/", f"{memory_name}/", 1)
        for name in preload.tools(role)
        if served or not name.startswith(f"{preload.MEMORY}/")
    ]
    tools = ", ".join([*own, *(f"{relay}/{name}" for name in tool_specs.results(role, ui=ui, judging=judging))])
    skills = ", ".join(preload.required(role, ui=ui, job=job))
    head = f"---\nname: {agent_name(role)}\ndescription: {meta['description']}\ntools: [{tools}]\n"
    note = tools_note(role, ui=ui, judging=judging)
    return lambda _old: f"{head}skills: [{skills}]\n---\n\n{body.strip()}\n\n{note}\n"


def names(inbox: Path) -> tuple[str, str]:
    """The step's relay and memory server names; unique, since the host disables a name another session holds (P21)."""
    return f"{SERVER}-{inbox.stem[:16]}", f"{preload.MEMORY}-{inbox.stem[:16]}"


def skill_path(name: str) -> str:
    """Where the window's runtime finds one of Delivery's worker skills: among the worktree's project skills."""
    return f".github/skills/{name}/SKILL.md"


def skills(role: str, *, ui: bool = False, job: str = "") -> list[tuple[str, Render]]:
    """The role's worker skills to place, as the package ships them; a missing one refuses the step."""
    if gaps := preload.missing(role, ui=ui, job=job):
        raise SettingsError(f"Delivery's worker skills are missing: {', '.join(gaps)}")  # noqa: EM102, TRY003
    texts = {name: preload.text(name) for name in preload.required(role, ui=ui, job=job)}
    return [(skill_path(name), lambda _old, t=text: t) for name, text in texts.items()]


@dataclass(frozen=True)
class Placed:
    """One file a step wrote and what it found there."""

    rel: str
    tracked: bool
    old: str | None  # an untracked file's content before the step; None when it did not exist
    made: tuple[str, ...] = ()  # folders the placement created, deepest first


def _git(folder: Path, *args: str) -> None:
    code, text = git_files.probe_in(folder)(["git", *args])
    if code:
        raise SettingsError(f"git {' '.join(args[:2])}: {text[:200] or f'exit {code}'}")  # noqa: EM102, TRY003


def _skipped(folder: Path, rel: str) -> bool:
    """Marked ``skip-worktree``: an earlier step of Delivery's that did not end cleanly placed it."""
    return git_files.probe_in(folder)(["git", "ls-files", "-v", "--", rel])[1].startswith("S ")


def place(folder: Path, rel: str, render: Render) -> Placed:
    """Write ``rel`` in ``folder`` without following a link, and keep it out of every commit."""
    path = folder / rel
    if part := text_files.linked_part(folder, path):
        raise SettingsError(f"{part} is a symbolic link; Delivery writes nothing through it")  # noqa: EM102, TRY003
    tracked = not git_files.untracked(folder, path)
    if tracked and not _skipped(folder, rel) and git_files.probe_in(folder)(["git", "diff", "--quiet", "--", rel])[0]:
        raise SettingsError(f"{rel} has local edits; Delivery never overwrites them")  # noqa: EM102, TRY003
    old = path.read_text() if path.is_file() else None
    text = render(old)
    made = tuple(str(d.relative_to(folder)) for d in path.parents if d.is_relative_to(folder) and not d.exists())
    path.parent.mkdir(parents=True, exist_ok=True)
    if tracked:
        _git(folder, "update-index", "--skip-worktree", "--", rel)
    else:
        git_files.exclude(folder, path)
    text_files.replace_text(path, text)
    return Placed(rel, tracked, None if tracked else old, made)


def restore(folder: Path, placed: Sequence[Placed]) -> list[str]:
    """Undo each placement, newest first; return what could not be restored."""
    problems: list[str] = []
    for p in reversed(placed):
        path = folder / p.rel
        try:
            if p.tracked:
                _git(folder, "update-index", "--no-skip-worktree", "--", p.rel)
                _git(folder, "restore", "--worktree", "--", p.rel)
            elif p.old is None:
                path.unlink(missing_ok=True)
            else:
                text_files.replace_text(path, p.old)
            for d in p.made:
                with contextlib.suppress(OSError):  # a folder something else filled stays
                    (folder / d).rmdir()
        except (OSError, SettingsError) as exc:
            problems.append(f"{p.rel}: {exc}")
    return problems
