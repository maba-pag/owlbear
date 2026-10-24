"""The watcher's report-only policy (W1a; design §3.2, TD-46, TD-50, TD-365): what one tool call may write outside.

A call yields *identified targets* and an *unresolved effect*, each on its own. Identified targets are the paths the
runtime says a call writes: a file tool's path, a write request's path and the before and after paths of its file
edits. Read tools and read requests yield nothing. A shell call's effects are not classified yet, so every one is
unresolved unless the runtime marks each of its parsed commands read-only and it redirects no output into a file;
that evidence clears only the shell effect, never a write path. No verdict is a rule's yet: an identified target
outside is "outside write (not judged yet)". Reasoning text is never judged (TD-55).

Where a target lies, first match wins: the session's own folder, then this Change's own state (Delivery's, TD-46),
are not reported; another Change's worktree or state and the project's main checkout with its Git folder are, even
under an exempt root; then temporary folders, tool caches and Delivery's own state are not (TD-46); anything else is.
Paths are canonical: ``~`` and ``$TMPDIR`` expanded, relative ones taken from the session's folder, symlinks resolved.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

WRITERS = frozenset({"create", "edit", "write", "write_file", "str_replace_editor", "apply_patch", "multi_edit"})
SHELLS = frozenset({"bash", "powershell", "shell", "write_bash"})
OUTSIDE = "outside write (not judged yet)"
SHELL = "shell effects not classified yet"
NO_PATH = "file edit without a path"
CACHES = ("TMPDIR", "XDG_CACHE_HOME", "UV_CACHE_DIR", "PIP_CACHE_DIR", "npm_config_cache", "PLAYWRIGHT_BROWSERS_PATH")
_TMP = ("$TMPDIR", "${TMPDIR}")


@dataclass(frozen=True)
class Asked:
    """One permission request for a call, as the runtime parsed it."""

    kind: str
    paths: tuple[str, ...] = ()  # a write request's paths, its file edits' before and after paths among them
    read_only: bool = False  # a shell request whose every parsed command the runtime marks read-only
    redirect: bool = False  # a shell request that redirects output into a file


@dataclass(frozen=True)
class Call:
    """What is known of one tool call: its start, if seen, and every permission request for it."""

    tool: str = ""
    arguments: Any = None
    redirect: bool = False  # the start event's shell info says it redirects output into a file
    asked: tuple[Asked, ...] = ()


@dataclass(frozen=True)
class Outcome:
    """One call's effects outside: identified targets and an unresolved effect, either or both; none is inside."""

    targets: tuple[str, ...] = ()
    unresolved: str = ""

    @property
    def inside(self) -> bool:
        """Nothing to report."""
        return not self.targets and not self.unresolved

    @property
    def verdict(self) -> str:
        """The report's verdict; an unresolved effect beside identified targets stays on the report."""
        return OUTSIDE if self.targets else f"unresolved ({self.unresolved})" if self.unresolved else ""


@dataclass(frozen=True)
class Places:
    """The roots one session's targets are judged by, besides its own folder; canonical once ``resolved``."""

    guarded: tuple[Path, ...] = ()  # the worktrees folder, every Change's state, the main checkout and its Git folder
    mine: tuple[Path, ...] = ()  # this Change's own state, inside a guarded root
    exempt: tuple[Path, ...] = ()  # TD-46: temporary folders, tool caches, Delivery's own state
    home: Path = field(default_factory=Path.home)
    tmp: Path | None = None  # the expanded ``$TMPDIR``

    def resolved(self) -> Places:
        """The same places with every root canonical, so targets compare with them."""
        return Places(
            tuple(_real(p) for p in self.guarded), tuple(_real(p) for p in self.mine),
            tuple(_real(p) for p in self.exempt), self.home, self.tmp,
        )  # fmt: skip


def exempt(home: Path, env: Mapping[str, str]) -> tuple[Path, ...]:
    """TD-46's never-judged roots besides Delivery's state: temporary folders and the user's tool caches."""
    roots = [Path("/tmp"), Path("/private/var/folders")]  # noqa: S108 - compared with, never written
    roots += [home / ".cache", home / "Library" / "Caches", home / ".npm"]  # uv, pip and Playwright's lie in these
    roots += [Path(env[k]) for k in CACHES if env.get(k)]
    return tuple(dict.fromkeys(roots))


def judge(call: Call, own: Path, places: Places) -> Outcome:
    """One call's effects outside *own*, the session's canonical folder, by *places* (resolved)."""
    written = list(_written(call))
    seen = (canonical(p, own, places) for p in written)
    targets = tuple(dict.fromkeys(str(p) for p in seen if reported(p, own, places)))
    if _shell(call) and not _read_only(call):
        return Outcome(targets, SHELL)
    return Outcome(targets, NO_PATH if call.tool in WRITERS and not written else "")


def reported(path: Path, own: Path, places: Places) -> bool:
    """Whether a canonical write target is reported, by the first root it lies under."""
    if path.is_relative_to(own) or any(path.is_relative_to(m) for m in places.mine):
        return False
    if any(path.is_relative_to(g) for g in places.guarded):
        return True
    return not any(path.is_relative_to(e) for e in places.exempt)


def canonical(text: str, cwd: Path, places: Places) -> Path:
    """*text* as an absolute path: ``~`` and ``$TMPDIR`` expanded, relative to *cwd*, symlinks resolved."""
    if text == "~" or text.startswith("~/"):
        text = str(places.home) + text[1:]
    for name in _TMP:
        if places.tmp is not None and (text == name or text.startswith(f"{name}/")):
            text = str(places.tmp) + text[len(name) :]
    return _real(cwd / text)


def _real(path: Path) -> Path:
    return Path(os.path.realpath(path))


def _written(call: Call) -> Iterator[str]:
    if call.tool in WRITERS and isinstance(args := call.arguments, dict):
        yield from (args[k] for k in ("path", "file_path") if isinstance(args.get(k), str) and args[k])
    for asked in call.asked:
        if asked.kind == "write":
            yield from (p for p in asked.paths if p)


def _shell(call: Call) -> bool:
    return call.tool in SHELLS or any(a.kind == "shell" for a in call.asked)


def _read_only(call: Call) -> bool:
    """Positive evidence only: every shell request is read-only without a redirection, and the start says none."""
    shells = [a for a in call.asked if a.kind == "shell"]
    return bool(shells) and not call.redirect and all(a.read_only and not a.redirect for a in shells)
