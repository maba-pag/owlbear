"""Permission decisions for one step's worker session: allow list, denials and their reasons (D4 §3.6)."""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next import tools
from owlbear_delivery_next.confinement import inside, outside, resolve

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

DENIED = ("git push", "git config", "git -c", "gh", "sudo")
VALUE_FLAGS = "mFCctSuo"  # short options of git commit and push that take a value


@dataclass(frozen=True)
class Policy:
    """Allow list of one step kind; every other request is denied and logged (D4 §3.6)."""

    root: Path
    commands: tuple[str, ...]
    write: bool = True


@dataclass(frozen=True)
class Request:
    """The parts of a permission request the policy judges; shell commands carry the runtime's read-only flag."""

    kind: str
    commands: tuple[tuple[str, bool], ...] = ()
    paths: tuple[str, ...] = ()
    urls: bool = False
    tool: str = ""


def allowed(text: str, prefixes: Sequence[str]) -> bool:
    """Whether *text* starts with the words of one of *prefixes*: the one allow-list rule for commands."""
    words = text.split()
    return any(words[: len(p.split())] == p.split() for p in prefixes)


def _bypass(words: Sequence[str]) -> str | None:
    """Return the flag of a git command that skips hooks or signing, or forces a push."""
    sub = next((w for w in words if w in {"commit", "push"}), "") if words[:1] == ["git"] else None
    for w in words[1:] if sub is not None else ():
        short = re.fullmatch(r"-([a-zA-Z]+)", w)  # a cluster sets a flag only before an option taking a value
        flags = re.split(f"[{VALUE_FLAGS}]", short[1])[0] if short else ""
        if w in {"--no-verify", "--no-gpg-sign"} or (sub == "commit" and "n" in flags):
            return w
        if sub == "push" and (w.startswith(("--force", "+")) or "f" in flags):
            return w
    return None


def _shell(policy: Policy, req: Request) -> str | None:  # noqa: PLR0911 - one reason per check
    if req.urls:
        return "shell commands that reach URLs are not allowed"
    base = policy.root
    for text, read_only in req.commands or (("", False),):
        try:
            words = shlex.split(text)
        except ValueError:
            return f"`{text}` cannot be parsed"
        if flag := _bypass(words):
            return f"`{text}` uses {flag}, which skips hooks or signing or forces history"
        if (reached := outside(policy.root, base, words, mutating=not read_only)) is not None:
            return f"`{text}` reaches {reached}, outside the worktree"
        base = resolve(base, words[1]) if words[:1] == ["cd"] and len(words) > 1 else base
        if allowed(text, DENIED):
            return f"`{text}` is denied"
        if not (allowed(text, policy.commands) or (read_only and all(inside(policy.root, p) for p in req.paths))):
            return f"`{text}` is not in this step's allow list"
    return None


def decide(policy: Policy, req: Request) -> str | None:
    """Return None to allow, or the denial reason the agent and the activity log see."""
    if req.kind == "custom-tool":
        return None if req.tool in {s.name for s in tools.SPECS} else f"tool {req.tool} is not allowed"
    if req.kind in {"read", "write"}:
        if req.kind == "write" and not policy.write:
            return "writes are not allowed in this step"
        out = [p for p in req.paths if not inside(policy.root, p)]
        return f"{req.kind} outside the worktree: {out[0]}" if out else None if req.paths else "no path"
    return _shell(policy, req) if req.kind == "shell" else f"{req.kind} requests are not allowed in this step"


def view(r: Any) -> Request:  # noqa: ANN401 - one of the SDK's permission request classes
    """Normalise one SDK permission request into a Request."""
    kind = getattr(r, "kind", type(r).__name__)
    if kind == "shell":
        ro = tuple(c.identifier for c in r.commands if c.read_only)
        texts = [s.full_command_text for s in r.command_segments or ()] or [c.identifier for c in r.commands]
        commands = tuple((t, allowed(t, ro)) for t in texts or [r.full_command_text])
        return Request(kind, commands, tuple(r.possible_paths or ()), bool(r.possible_urls))
    if kind in {"read", "write"}:
        path = r.resolved_path or getattr(r, "path", None) or getattr(r, "file_name", "")
        return Request(kind, paths=(path,) if path else ())
    return Request(kind, tool=getattr(r, "tool_name", ""))
