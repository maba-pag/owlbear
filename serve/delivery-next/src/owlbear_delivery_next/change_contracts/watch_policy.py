"""The watcher's report-only policy (W1a, W1b-1; design §3.2, TD-46, TD-50, TD-365): what one tool call may write.

A call yields *identified targets* and an *unresolved effect*, each on its own. Identified targets are the paths the
runtime says a call writes: a file tool's path, a write request's path and the before and after paths of its file
edits; and a shell call's effects as ``watch_effects`` identifies them in each of its permission requests' command
text from the request's resolved working directory, else in its start's command from the session's folder (the
fallback, marked on the outcome), where an earlier call's change of the shell's directory or of HOME and TMPDIR
leaves what depends on it unresolved. Read tools and read requests yield nothing. What the shell effects leave open is
unresolved, each reason once; the runtime's read-only evidence clears only the unresolved effect of the commands it
covers, never an identified target, and a write redirection the runtime reports but the watcher does not see stays
unresolved. No verdict is a rule's yet: an identified target outside is "outside write (not judged yet)". Reasoning
text is never judged (TD-55).

Where a target lies, first match wins: the session's own folder, then this Change's own state (Delivery's, TD-46),
are not reported; another Change's worktree or state and the project's main checkout with its Git folder are, even
under an exempt root; then temporary folders, tool caches and Delivery's own state are not (TD-46); anything else is.
Paths are canonical: ``~`` and ``$TMPDIR`` expanded, relative ones taken from the session's folder, symlinks resolved;
a shell effect's path as its operation opens it (a removal keeps its last component).
"""

from __future__ import annotations

import os
import shlex
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.change_contracts import watch_effects

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

WRITERS = frozenset({"create", "edit", "write", "write_file", "str_replace_editor", "apply_patch", "multi_edit"})
SHELLS = frozenset({"bash", "powershell", "shell", "write_bash"})
OUTSIDE = "outside write (not judged yet)"
SHELL = "shell effects not classified yet"  # a shell call without command text, or another shell's
REDIRECT = "a redirection the watcher does not see"
UNREAD = frozenset({"powershell", "write_bash"})  # not bash text: what they run is not read
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
    full_command_text: str = ""  # a shell request's command as given
    command_segments: tuple[tuple[str, str], ...] = ()  # the runtime's segments: each one's text and identifier
    commands: tuple[tuple[str, bool], ...] = ()  # the runtime's commands: identifier and whether read-only
    possible_paths: tuple[str, ...] = ()
    resolved_paths: tuple[tuple[str, str], ...] = ()
    resolved_working_directory: str = ""  # "" when the runtime names none


@dataclass(frozen=True)
class Call:
    """What is known of one tool call: its start, if seen, and every permission request for it."""

    tool: str = ""
    arguments: Any = None
    redirect: bool = False  # the start event's shell info says it redirects output into a file
    asked: tuple[Asked, ...] = ()
    moved: bool = False  # an earlier call of its shell may have changed the shell's directory
    changed: frozenset[str] = frozenset()  # the watched variables an earlier call of its shell may have changed


@dataclass(frozen=True)
class Outcome:
    """One call's effects outside: identified targets and an unresolved effect, either or both; none is inside."""

    targets: tuple[str, ...] = ()
    unresolved: str = ""  # its reasons, each once, joined by "; "
    assumed_cwd: bool = False  # a shell text was read from the session's folder: the runtime named no directory
    moves: bool = False  # it may change its shell's directory for later calls
    changes: frozenset[str] = frozenset()  # the watched variables it may change for later calls

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
    seen = [canonical(p, own, places) for p in written]
    shell = _shell_effects(call, own, places) if _shell(call) else _Shelled()
    targets = tuple(dict.fromkeys(str(p) for p in [*seen, *shell.paths] if reported(p, own, places)))
    reasons = "; ".join(dict.fromkeys(shell.reasons)) or (NO_PATH if call.tool in WRITERS and not written else "")
    return Outcome(targets, reasons, shell.assumed, shell.moves, frozenset(shell.changes))


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


@dataclass
class _Shelled:
    """A shell call's effects over all its texts."""

    paths: list[Path] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    assumed: bool = False
    moves: bool = False
    changes: set[str] = field(default_factory=set)


def _shell_effects(call: Call, own: Path, places: Places) -> _Shelled:
    """Each shell request's text from its resolved directory, else the start's command from *own* (assumed).

    From *own*, an earlier call that may have moved the shell leaves relative targets unresolved; an earlier change
    of HOME or TMPDIR leaves their expansions unresolved wherever the text runs.
    """
    if call.tool in UNREAD:  # what it runs is not read; written to a shell, it may change anything there
        moves = call.tool == "write_bash"
        return _Shelled(reasons=[SHELL], moves=moves, changes=set(watch_effects.WATCHED) if moves else set())
    args = call.arguments if isinstance(call.arguments, dict) else {}
    command = args.get("command") if isinstance(args.get("command"), str) else ""
    shell = _Shelled()
    for asked in [a for a in call.asked if a.kind == "shell"] or [Asked("shell")]:
        text, folder = asked.full_command_text or command, asked.resolved_working_directory
        if not text:
            shell.reasons.append(SHELL)
            continue
        shell.assumed = shell.assumed or not folder
        cwd = canonical(folder, own, places) if folder else own
        start = watch_effects.Shell(cwd, places.home, places.tmp, call.moved and not folder, call.changed)
        found = watch_effects.effects(text, start, evidence(asked))
        shell.paths += [t.path for t in found.targets]
        shell.reasons += found.unresolved
        shell.moves, shell.changes = shell.moves or found.moves, shell.changes | found.changes
        if (asked.redirect or call.redirect) and not found.redirects and watch_effects.SYNTAX not in found.unresolved:
            shell.reasons.append(REDIRECT)
    return shell


def evidence(asked: Asked) -> watch_effects.Evidence:
    """A shell request's read-only evidence, each mark bound to its segment's text where the runtime names one.

    An identifier marked both ways is not read-only; one marked not read-only is never covered by a shorter one.
    """
    marks: dict[str, bool] = {}
    for identifier, read_only in asked.commands:
        marks[identifier] = marks.get(identifier, True) and read_only
    bound = [(text, marks[identifier]) for text, identifier in asked.command_segments if identifier in marks]
    segments = tuple((w, read_only) for text, read_only in bound if (w := _words(text)))
    named = tuple((w, read_only) for identifier, read_only in marks.items() if (w := _words(identifier)))
    return watch_effects.Evidence(asked.read_only and all(marks.values()), segments, named)


def _words(text: str) -> tuple[str, ...]:
    try:
        return tuple(shlex.split(text))
    except ValueError:
        return ()
