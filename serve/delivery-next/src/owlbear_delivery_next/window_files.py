"""Files a C+ step needs in its worktree: the window's model pin, the step's MCP relay and its agent (TD-36).

None of them reaches the agent's commits: an untracked file is listed in the clone's ``info/exclude``, a tracked
one is marked ``skip-worktree``; ``restore`` puts back what the step found.
"""

from __future__ import annotations

import contextlib
import json
import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next import preload, setup
from owlbear_delivery_next import tools as tool_specs

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from pathlib import Path

HARNESS, DEFAULT_MODEL = "chat.defaultToCopilotHarness", "chat.defaultModel"
SETTINGS, MCP = ".vscode/settings.json", ".mcp.json"
SERVER = "owlbear-step"  # a step's relay is SERVER-<inbox>: the host disables a name another session holds (P21)
RESULTS = (
    "Your result tools come from Delivery's `owlbear-step-…` MCP server: `submit_result`, `ask_question`, "
    "`report_wrong_premise` and `report_missing_tool`. Never push."
)

type Render = Callable[[str | None], str]


class SettingsError(ValueError):
    """A window file cannot be written safely."""


def _with_settings(old: str | None, model: str) -> str:
    """``old`` with the harness and model pinned; JSON with comments gets the keys after its opening brace."""
    try:
        current: Any = json.loads(old) if old is not None else {}
    except ValueError:
        current = None
    if isinstance(current, dict):
        return json.dumps(current | {HARNESS: True, DEFAULT_MODEL: model}, indent=2) + "\n"
    text = old or ""
    lines = text.splitlines(keepends=True)
    first = next((i for i, ln in enumerate(lines) if ln.strip() and not ln.lstrip().startswith("//")), None)
    if current is not None or first is None or not lines[first].lstrip().startswith("{"):
        raise SettingsError(f"{SETTINGS} is not a JSON object; set {DEFAULT_MODEL} by hand")  # noqa: EM102, TRY003
    if f'"{HARNESS}"' in text or f'"{DEFAULT_MODEL}"' in text:
        msg = f"{SETTINGS} pins the harness or model in a form Delivery can't edit"
        raise SettingsError(msg)
    at = sum(len(ln) for ln in lines[:first]) + lines[first].index("{") + 1
    pins = f'\n  "{HARNESS}": true,\n  "{DEFAULT_MODEL}": {json.dumps(model)},'
    return text[:at] + pins + text[at:]


def settings(model: str) -> Render:
    """The settings render for ``model``; auto and blank models are refused (TD-32)."""
    if not model.strip() or model.strip().lower() == "auto":
        raise SettingsError("the step model must be named; auto is never used (TD-32)")  # noqa: EM101, TRY003
    return lambda old: _with_settings(old, model)


def write_window_settings(folder: Path, model: str) -> None:
    """Pin the harness and model for the window of ``folder``; other settings are kept."""
    path = folder / SETTINGS
    text = settings(model)(path.read_text() if path.exists() else None)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


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
        args = ["-m", "owlbear_delivery_next.step_mcp", "--inbox", str(inbox)]
        own = {relay: {"type": "stdio", "command": sys.executable, "args": args, "tools": ["*"]}}
        if (server := preload.memory(memory)) is not None:
            own[memory_name] = {"type": "stdio", **server}
        return json.dumps({**data, "mcpServers": {**data.get("mcpServers", {}), **own}}, indent=2) + "\n"

    return render


def agent_name(role: str) -> str:
    """The window agent of a session role, unique to Delivery."""
    return f"owlbear-{role}"


def agent_path(role: str) -> str:
    """Where the window finds the role's agent."""
    return f".github/agents/{agent_name(role)}.agent.md"


def agent(role: str, inbox: Path, memory: Path | None = None) -> Render:
    """The role's agent from the package prose, renamed for the window, with its tools, skills and result note.

    Its tools are the role's, under the same names as in the SDK runtime (the window runs the same harness), with
    memory served by this step's memory server or left out, plus the result tools of this step's relay; the window
    offers nothing else, neither its own question tool nor the owner's MCP tools (TD-69, runtime research P19, P23).
    """
    meta, body = preload.agent_file(role)
    relay, memory_name = names(inbox)
    served = preload.memory(memory) is not None
    own = [
        name.replace(f"{preload.MEMORY}/", f"{memory_name}/", 1)
        for name in preload.tools(role)
        if served or not name.startswith(f"{preload.MEMORY}/")
    ]
    tools = ", ".join([*own, *(f"{relay}/{s.name}" for s in tool_specs.SPECS)])
    skills = ", ".join(preload.REQUIRED.get(role, ()))
    head = f"---\nname: {agent_name(role)}\ndescription: {meta['description']}\ntools: [{tools}]\n"
    return lambda _old: f"{head}skills: [{skills}]\n---\n\n{body.strip()}\n\n{RESULTS}\n"


def names(inbox: Path) -> tuple[str, str]:
    """The step's relay and memory server names; unique, since the host disables a name another session holds (P21)."""
    return f"{SERVER}-{inbox.stem[:16]}", f"{preload.MEMORY}-{inbox.stem[:16]}"


def skill_path(name: str) -> str:
    """Where the window's runtime finds one of Delivery's worker skills: among the worktree's project skills."""
    return f".github/skills/{name}/SKILL.md"


def skills(role: str) -> list[tuple[str, Render]]:
    """The role's worker skills to place, as the package ships them; a missing one refuses the step."""
    if gaps := preload.missing(role):
        raise SettingsError(f"Delivery's worker skills are missing: {', '.join(gaps)}")  # noqa: EM102, TRY003
    texts = {name: preload.text(name) for name in preload.REQUIRED.get(role, ())}
    return [(skill_path(name), lambda _old, t=text: t) for name, text in texts.items()]


@dataclass(frozen=True)
class Placed:
    """One file a step wrote and what it found there."""

    rel: str
    tracked: bool
    old: str | None  # an untracked file's content before the step; None when it did not exist
    made: tuple[str, ...] = ()  # folders the placement created, deepest first


def _git(folder: Path, *args: str) -> None:
    code, text = setup.probe_in(folder)(["git", *args])
    if code:
        raise SettingsError(f"git {' '.join(args[:2])}: {text[:200] or f'exit {code}'}")  # noqa: EM102, TRY003


def _skipped(folder: Path, rel: str) -> bool:
    """Marked ``skip-worktree``: an earlier step of Delivery's that did not end cleanly placed it."""
    return setup.probe_in(folder)(["git", "ls-files", "-v", "--", rel])[1].startswith("S ")


def place(folder: Path, rel: str, render: Render) -> Placed:
    """Write ``rel`` in ``folder`` without following a link, and keep it out of every commit."""
    path = folder / rel
    if part := setup.linked_part(folder, path):
        raise SettingsError(f"{part} is a symbolic link; Delivery writes nothing through it")  # noqa: EM102, TRY003
    tracked = not setup.untracked(folder, path)
    if tracked and not _skipped(folder, rel) and setup.probe_in(folder)(["git", "diff", "--quiet", "--", rel])[0]:
        raise SettingsError(f"{rel} has local edits; Delivery never overwrites them")  # noqa: EM102, TRY003
    old = path.read_text() if path.is_file() else None
    text = render(old)
    made = tuple(str(d.relative_to(folder)) for d in path.parents if d.is_relative_to(folder) and not d.exists())
    path.parent.mkdir(parents=True, exist_ok=True)
    if tracked:
        _git(folder, "update-index", "--skip-worktree", "--", rel)
    else:
        setup.exclude(folder, path)
    setup.replace_text(path, text)
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
                setup.replace_text(path, p.old)
            for d in p.made:
                with contextlib.suppress(OSError):  # a folder something else filled stays
                    (folder / d).rmdir()
        except (OSError, SettingsError) as exc:
            problems.append(f"{p.rel}: {exc}")
    return problems
