"""Permission decisions for one step's worker session: allow list, denials and their reasons (D4 §3.6)."""

from __future__ import annotations

import itertools
import re
import shlex
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next import tools
from owlbear_delivery_next.confinement import GIT_OUTPUT, NULL_PATHS, git_subcommand, inside, outside, resolve

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

DENIED = ("git push", "git config", "git -c", "gh", "sudo")
VALUE_FLAGS = "mFCctSuo"  # short options of git commit and push that take a value
GIT_READ_ONLY = frozenset(("log", "show", "diff", "status", "blame", "grep", "ls-files", "rev-parse"))
_HARMLESS = re.compile(r"\d*>>?\s*/dev/null\b|\d*>&\d+")  # discarded output or a descriptor copy


@dataclass(frozen=True)
class Policy:
    """Allow list of one step kind; every other request is denied and logged (D4 §3.6)."""

    root: Path
    commands: tuple[str, ...]
    write: bool = True
    checks: tuple[tuple[str, str], ...] = ()  # the profile's (package directory, check command) pairs


@dataclass(frozen=True)
class Request:
    """The parts of a permission request the policy judges; shell commands carry the runtime's read-only flag."""

    kind: str
    commands: tuple[tuple[str, bool], ...] = ()
    paths: tuple[str, ...] = ()
    urls: bool = False
    tool: str = ""


def metachars(text: str) -> set[str]:
    """Shell operators of *text* outside quotes, and command substitution outside single quotes."""
    found: set[str] = set()
    quote, escaped = "", False
    for i, ch in enumerate(text):
        if escaped or (ch == "\\" and quote != "'"):
            escaped = not escaped
        elif quote == "'":
            quote = "" if ch == "'" else quote
        elif ch == "`" or text.startswith("$(", i):
            found.add("`" if ch == "`" else "$(")
        elif quote:
            quote = "" if ch == '"' else quote
        elif ch in "'\"":
            quote = ch
        elif ch in ";|&<>":
            found.add(ch)
    return found


def _prefixed(text: str, prefixes: Sequence[str]) -> bool:
    words = text.split()
    if words[:2] == ["git", "--no-pager"] and words[2:3] and words[2] in GIT_READ_ONLY:
        words = ["git", *words[2:]]
    return any(words[: len(p.split())] == p.split() for p in prefixes)


def _package_check(text: str, checks: Sequence[tuple[str, str]], root: Path | None) -> bool:
    """``cd <package> && <check>`` and nothing more, the package resolving inside *root* to a profile package."""
    head, _, tail = text.partition("&&")
    cd = head.split()
    if root is None or len(cd) != 2 or metachars(head) or metachars(tail):  # noqa: PLR2004 - ``cd`` and its target
        return False
    target, rest = resolve(root, cd[1]), tail.split()
    return target.is_relative_to(root.resolve()) and any(
        target == resolve(root, p) and rest[: len(c.split())] == c.split() for p, c in checks
    )


def allowed(
    text: str, prefixes: Sequence[str], checks: Sequence[tuple[str, str]] = (), root: Path | None = None
) -> bool:
    """Whether *text* starts with the words of one of *prefixes*: the one allow-list rule for commands.

    ``git --no-pager <read-only subcommand>`` counts as that subcommand when it is allowed. The tail may hold
    no shell operator or substitution except a redirect to ``/dev/null`` or a descriptor, so a prefix cannot
    smuggle a second command. ``cd <package> && <check>`` is allowed when *checks* names that check for the
    package directory *cd* resolves to inside *root*.
    """
    if text.split()[:1] == ["cd"] and "&&" in text:
        return _package_check(text, checks, root)
    return not metachars(_HARMLESS.sub("", text)) and _prefixed(text, prefixes)


def _read_only_write(text: str, words: Sequence[str]) -> str | None:
    """The redirect or git option by which a command would write in a read-only step."""
    if ">" in metachars(text):
        return "a redirect"
    sub = git_subcommand(words)
    for w in words[1:] if sub else ():
        flag = w.partition("=")[0]
        if flag in {"--output", "--ext-diff"} or (flag == "-o" and sub in GIT_OUTPUT):
            return w
    return None


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


def _reach(policy: Policy, base: Path, words: Sequence[str], *, read_only: bool) -> tuple[str | None, Path]:
    """The first place outside the worktree each ``&&`` part reaches, and the directory the command ends in."""
    for part in (list(g) for amp, g in itertools.groupby(words, lambda w: w == "&&") if not amp):
        if (reached := outside(policy.root, base, part, mutating=not read_only)) is not None:
            return str(reached), base
        base = resolve(base, part[1]) if part[:1] == ["cd"] and len(part) > 1 else base
    return None, base


def _shell(policy: Policy, req: Request) -> str | None:  # noqa: PLR0911 - one reason per check
    if req.urls:
        return "shell commands that reach URLs are not allowed"
    base = policy.root
    if out := next((p for p in req.paths if p not in NULL_PATHS and not inside(policy.root, p)), None):
        return f"the command reaches {out}, outside the worktree"
    for text, read_only in req.commands or (("", False),):
        try:
            words = shlex.split(text)
        except ValueError:
            return f"`{text}` cannot be parsed"
        if flag := _bypass(words):
            return f"`{text}` uses {flag}, which skips hooks or signing or forces history"
        reached, base = _reach(policy, base, words, read_only=read_only)
        if reached is not None:
            return f"`{text}` reaches {reached}, outside the worktree"
        if not policy.write and (flag := _read_only_write(text, words)):
            return f"`{text}` uses {flag}, which writes in a read-only step"
        if _prefixed(text, DENIED):
            return f"`{text}` is denied"
        if not (allowed(text, policy.commands, policy.checks, policy.root) or read_only):
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
