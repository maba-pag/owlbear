"""Files a C+ step needs in its worktree: the window's model pin, the step's MCP relay and its agent (TD-36).

None of them reaches the agent's commits: an untracked file is listed in the clone's ``info/exclude``, a tracked
one is marked ``skip-worktree``; ``restore`` puts back what the step found.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from importlib.resources import files
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next import setup

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from pathlib import Path

HARNESS, DEFAULT_MODEL = "chat.defaultToCopilotHarness", "chat.defaultModel"
SETTINGS, MCP = ".vscode/settings.json", ".mcp.json"
SERVER = "owlbear-step"
RESULTS = (
    "Your result tools come from the `owlbear-step` MCP server: `submit_result`, `ask_question` and "
    "`report_wrong_premise`. Never push, and never write outside this folder."
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


def mcp(inbox: Path) -> Render:
    """``.mcp.json`` with the step's relay added; the project's own servers stay."""

    def render(old: str | None) -> str:
        try:
            data = json.loads(old) if old else {}
        except ValueError as exc:
            raise SettingsError(f"{MCP} is not plain JSON") from exc  # noqa: EM102, TRY003
        if not isinstance(data, dict) or not isinstance(data.get("mcpServers", {}), dict):
            raise SettingsError(f"{MCP} has no mcpServers object")  # noqa: EM102, TRY003
        args = ["-m", "owlbear_delivery_next.step_mcp", "--inbox", str(inbox)]
        server = {"type": "stdio", "command": sys.executable, "args": args, "tools": ["*"]}
        return json.dumps({**data, "mcpServers": {**data.get("mcpServers", {}), SERVER: server}}, indent=2) + "\n"

    return render


def agent_name(role: str) -> str:
    """The window agent of a session role, unique to Delivery."""
    return f"owlbear-{role}"


def agent_path(role: str) -> str:
    """Where the window finds the role's agent."""
    return f".github/agents/{agent_name(role)}.agent.md"


def agent(role: str) -> Render:
    """The role's agent from the package prose, renamed for the window, with the result-tool note."""
    text = files("owlbear_delivery_next").joinpath("agents", f"{role}.md").read_text(encoding="utf-8")
    _, front, body = text.split("---", 2)
    meta = dict(line.split(":", 1) for line in front.strip().splitlines())
    head = f"---\nname: {agent_name(role)}\ndescription: {meta['description'].strip()}\n---\n"
    return lambda _old: f"{head}\n{body.strip()}\n\n{RESULTS}\n"


@dataclass(frozen=True)
class Placed:
    """One file a step wrote and what it found there."""

    rel: str
    tracked: bool
    old: str | None  # an untracked file's content before the step; None when it did not exist


def _git(folder: Path, *args: str) -> None:
    code, text = setup.probe_in(folder)(["git", *args])
    if code:
        raise SettingsError(f"git {' '.join(args[:2])}: {text[:200]}")  # noqa: EM102, TRY003


def place(folder: Path, rel: str, render: Render) -> Placed:
    """Write ``rel`` in ``folder`` without following a link, and keep it out of every commit."""
    path = folder / rel
    if part := setup.linked_part(folder, path):
        raise SettingsError(f"{part} is a symbolic link; Delivery writes nothing through it")  # noqa: EM102, TRY003
    tracked = not setup.untracked(folder, path)
    old = path.read_text() if path.is_file() else None
    text = render(old)
    path.parent.mkdir(parents=True, exist_ok=True)
    if tracked:
        _git(folder, "update-index", "--skip-worktree", "--", rel)
    else:
        setup.exclude(folder, path)
    setup.replace_text(path, text)
    return Placed(rel, tracked, None if tracked else old)


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
        except (OSError, SettingsError) as exc:
            problems.append(f"{p.rel}: {exc}")
    return problems
