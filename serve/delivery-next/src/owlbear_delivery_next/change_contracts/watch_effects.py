"""Shell effects as the watcher identifies them (W1b-1, design §3.6 slice 3): what one shell text writes or removes.

Pure: the text is read by ``watch_lexer``; the filesystem is only read, to resolve paths. Identified are only the
redirections that write a file, ``cat > FILE <<EOF`` among them, and a small verified core of programs and forms:
``touch [-c]``, ``mkdir [-p]``, ``rm [-rRf]``, ``rmdir``, ``unlink``, ``cp [-rRpf] SRC… DEST``,
``mv [-f] SRC… DEST`` and ``tee [-a]``. A few programs write no file but through their redirections (``cat``,
``echo``, ``printf``, ...).
Every other program, option or form is unresolved, unless the runtime marks that command read-only; such evidence
clears only its command's unresolved effect, never an identified target.

The working directory starts at the given one; a top-level ``cd LITERAL`` moves it, logically as ``cd -L`` does,
only for what follows it through ``&&``; after ``;``, a newline, ``||``, ``|`` or ``&`` following any ``cd`` it is
unknown, and so is it after a ``cd`` in a pipeline, in the background or with anything but one literal operand.
``$HOME``, ``$TMPDIR`` and ``~`` expand by the environment of their moment: an assignment, ``export``, ``unset``,
``declare`` and its kin, ``read`` or ``printf -v`` of one leaves it unknown for what follows, and a command's own
assignments and ``env`` changes reach the shells it starts. A nested ``sh -c`` script is read in its own context and
exports nothing, unless the shell may read startup input first. Under an unknown directory relative targets are
unresolved; absolute ones stay identified. Targets are canonical: parents resolved, the last component too where the
program opens the path (redirections, ``tee``, ``touch``, ``mkdir``), kept where it acts on the name itself (``rm``,
``rmdir``, ``unlink``, ``mv``'s sources). A ``cp`` or ``mv`` destination that is an existing symlink is unresolved.
The effects also say whether the text may change its shell's directory or environment for later calls. What the
watcher cannot name, it never calls clean: a setter's name that is not literal changes every watched variable, a
prefix assignment before a builtin changes its variable, and a command that cannot be named, ``eval``, ``source``,
``.`` or text not read at all may change the directory and every watched variable. Read-only evidence clears only
the unresolved write effect of a top-level command the lexer fully read: never a nested script's or a shell's, never
text the lexer could not read ("shell syntax not followed") and never a heredoc's command substitution.

"Unresolved" means the watcher cannot tell, not that something was written outside. The shell-state taint
over-approximates on purpose (a builtin's prefix assignment, a command it cannot name, text it cannot read). Each
shell's directory is assumed to start at the session's folder: a shell that moved before the watcher saw it is not
covered.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from itertools import pairwise
from pathlib import Path, PurePath
from typing import TYPE_CHECKING

from owlbear_delivery_next.change_contracts.watch_lexer import Command, Redirect, Script, UnfollowedError, Word, lex
from owlbear_delivery_next.local_system.shell_parse import ASSIGNMENT, NESTING, SHELLS, operand, scripts

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

SYNTAX = "shell syntax not followed"
HEREDOC = "heredoc runs a command substitution"
PROGRAM = "runs a program whose writes cannot be seen"
FORM = "an option or form the watcher does not follow"
CWD = "a relative target in an unknown working directory"
VARIABLE = "a target depends on a variable"
ENV = "an environment change the watcher does not follow"
PATTERN = "a target is a pattern"
LINK = "copy or move onto a symlink"
RECURSIVE = "a recursive copy may write through links inside its destination"
STARTUP = "a nested shell with startup input"
EARLIER_CWD = "an earlier command changed the shell's directory"
EARLIER_ENV = "an earlier command changed the shell's environment"
WATCHED = frozenset({"HOME", "TMPDIR", "BASH_ENV", "ENV"})  # what words expand by, or what a nested shell reads
DEVICES = frozenset({"/dev/null", "/dev/stdout", "/dev/stderr", "/dev/tty"})
SETTERS = frozenset({"export", "unset", "declare", "typeset", "local", "readonly", "read", "printf"})
QUIET = SETTERS | {"cat", "echo", "pwd", "true", "false", ":", "test", "[", "sleep", "set", "exit"}
WRAPPERS = frozenset({"builtin", "caffeinate", "command", "env", "exec", "ionice", "nice", "stdbuf", "timeout"})
WHOLE = frozenset({"eval", "source", "."})  # they run text the watcher does not see
CDS = frozenset({"cd", "pushd", "popd"})
BUILTINS = SETTERS | CDS | WHOLE | {":", "set", "exit", "true", "false", "echo", "pwd", "test", "[", "command",
    "builtin", "exec", "shift", "trap", "return", "break", "continue", "times", "wait", "alias", "unalias", "type",
    "hash", "umask", "ulimit", "getopts", "let", "kill", "jobs", "fg", "bg", "shopt", "enable"}  # fmt: skip
_PREFIXES = frozenset({"!", "time"})
_GLOBS = "*?[{"
_STARTUPS = frozenset({"--login", "--rcfile", "--init-file", "--interactive"})


@dataclass(frozen=True)
class Target:
    """One identified effect: a path written ("write") or removed ("remove"), canonical for its operation."""

    kind: str
    path: Path


@dataclass(frozen=True)
class Evidence:
    """The runtime's read-only evidence for one shell text, bound to its segments' text where it names them."""

    every: bool = False  # the runtime marks every command it parsed read-only
    segments: tuple[tuple[tuple[str, ...], bool], ...] = ()  # a segment's words and its identifier's mark
    marks: tuple[tuple[tuple[str, ...], bool], ...] = ()  # a command identifier's words and its mark

    def mark(self, words: Sequence[str]) -> bool | None:
        """The runtime's mark for a command: its segment's, else its identifiers' (a non-read-only one wins)."""
        exact = {read_only for w, read_only in self.segments if w == tuple(words)}
        if exact:
            return all(exact)
        found = {read_only for w, read_only in self.marks if w and tuple(words[: len(w)]) == w}
        if False in found:
            return False
        return True if True in found or self.every else None

    def covers(self, *candidates: Sequence[str]) -> bool:
        """Whether a command, by any of its spellings, is marked read-only and by none as not read-only."""
        found = [self.mark(c) for c in candidates]
        return False not in found and True in found


@dataclass(frozen=True)
class Effects:
    """One shell text's identified targets and unresolved reasons, and what it may change for later calls."""

    targets: tuple[Target, ...] = ()
    unresolved: tuple[str, ...] = ()
    redirects: bool = False  # it redirects output into a file, identified or not
    moves: bool = False  # it may change its shell's directory
    changes: frozenset[str] = frozenset()  # the WATCHED variables it may change in its shell


@dataclass
class _Context:
    """Where a script runs: its directory and HOME/TMPDIR, each a path or the reason it is unknown."""

    cwd: Path | str
    env: dict[str, Path | str] = field(default_factory=dict)  # BASH_ENV and ENV are present once set

    def copy(self, cwd: Path | str | None = None, unknown: set[str] | frozenset[str] = frozenset()) -> _Context:
        return _Context(self.cwd if cwd is None else cwd, self.env | dict.fromkeys(unknown, ENV))


@dataclass(frozen=True)
class Shell:
    """Where a shell text starts: its directory, HOME and TMPDIR (None: not known), and what earlier calls changed."""

    cwd: Path
    home: Path
    tmp: Path | None = None
    drifted: bool = False  # an earlier call may have moved the shell from cwd
    changed: frozenset[str] = frozenset()  # the watched variables an earlier call may have changed


def effects(text: str, shell: Shell, evidence: Evidence | None = None) -> Effects:
    """The effects of shell *text* started as *shell* says, with the runtime's read-only *evidence*."""
    env: dict[str, Path | str] = {"HOME": shell.home, "TMPDIR": VARIABLE if shell.tmp is None else shell.tmp}
    start = _Context(EARLIER_CWD if shell.drifted else shell.cwd, env | dict.fromkeys(shell.changed, EARLIER_ENV))
    run = _Run(evidence or Evidence())
    try:
        run.script(lex(text), start)
    except UnfollowedError:  # text not read may change anything, whatever the runtime's read-only marks say
        return Effects((), (SYNTAX,), moves=True, changes=WATCHED)
    return Effects(
        tuple(dict.fromkeys(run.targets)), tuple(dict.fromkeys(run.unresolved)), run.redirects, run.moves,
        frozenset(run.changes),
    )  # fmt: skip


def _name(word: Word) -> str:
    """A command word's program name, after quote removal: ``'cd'`` is cd; ``.`` and ``/`` are their own."""
    return PurePath(word.text).name or word.text


def _real(path: Path) -> Path:
    return Path(os.path.realpath(path))


def _kept(path: Path) -> Path:
    """*path* with its parents resolved and its last component kept, unless that is ``.`` or ``..``."""
    return _real(path) if path.name in {"", ".", ".."} else _real(path.parent) / path.name


class _Run:
    """The effects found so far in one shell text and the scripts it nests."""

    def __init__(self, evidence: Evidence) -> None:
        self.evidence, self.depth = evidence, 0
        self.targets: list[Target] = []
        self.unresolved: list[str] = []
        self.redirects = self.moves = False
        self.changes: set[str] = set()

    def script(self, script: Script, ctx: _Context) -> None:
        """Every command of *script* in order; a ``cd`` moves the directory only for what follows through ``&&``."""
        if script.substituting:
            self.unresolved.append(HEREDOC)
        moved = False
        for command in script.commands:
            if moved and command.before != "&&":
                ctx.cwd = CWD  # the cd may have failed, or run apart
            for redirect in command.redirects:
                self._redirect(redirect, ctx)
            moved = self._command(command, ctx) or moved

    def _redirect(self, redirect: Redirect, ctx: _Context) -> None:
        self.redirects = True
        text = redirect.target.text
        if text not in DEVICES and not text.startswith("/dev/fd/"):
            self._target(redirect.target, ctx, "write", follow=True)

    def changed(self, name: str, ctx: _Context) -> None:
        """A watched variable set or unset in this context: unknown for what follows; a top-level one is kept."""
        if name in WATCHED:
            ctx.env[name] = ENV
            if not self.depth:
                self.changes.add(name)

    def taint(self, ctx: _Context) -> None:
        """A command the watcher cannot name, or one running unseen text: it may move the shell and change any
        watched variable, for the rest of the script and, at the top level, for later calls."""  # noqa: D205, D209
        ctx.cwd = CWD
        for name in WATCHED:
            self.changed(name, ctx)
        self.moves = self.moves or not self.depth

    def _command(self, command: Command, ctx: _Context) -> bool:
        """Classify one command in *ctx*, which it may change; whether it may have changed the directory."""
        words = command.words
        start = next((i for i, w in enumerate(words) if w.text not in _PREFIXES and not ASSIGNMENT.match(w.text)), -1)
        start = len(words) if start < 0 else start
        assigned = {w.text.split("=", 1)[0] for w in words[:start] if ASSIGNMENT.match(w.text)}
        if start == len(words) or _name(words[start]) in BUILTINS:
            for name in assigned:  # assignments alone stay in the shell; a builtin may keep or read them
                self.changed(name, ctx)
            if start == len(words):
                return False
        at, chdir, scoped = self._unwrapped(words, start)
        if at >= len(words):
            return False
        program = words[at:] if at >= 0 else words[start:]
        name = _name(program[0])
        top = not self.depth and name not in SHELLS  # evidence is for the top level's own commands only
        covered = top and self.evidence.covers(*([w.text for w in ws] for ws in (words, words[start:], program)))
        if at < 0 or not program[0].literal or program[0].pattern or name in WHOLE:
            self.taint(ctx)  # an unknown command, or text not read: eval, source, .
            if name in WHOLE and not covered:
                raise UnfollowedError
            self.unresolved += [] if covered else [PROGRAM]
            return True
        if name in CDS:
            self.moves = self.moves or not self.depth
            alone = at == start and command.before not in {"|", "||"} and command.after not in {"|", "&"}
            ctx.cwd = self._cd(program, ctx) if alone and name == "cd" else CWD
            return True
        if name in SETTERS:
            self._setters(name, program, ctx)
        known = len(self.unresolved)
        self._program(name, program, ctx.copy(CWD if chdir else None), (assigned | scoped) & WATCHED, command)
        if covered:
            del self.unresolved[known:]  # evidence clears its command's unresolved effects, never a target
        return False

    def _program(self, name: str, program: list[Word], here: _Context, scoped: set[str], command: Command) -> None:
        if name in SHELLS:
            self._nested(program, here, scoped, fed=command.reads or command.before == "|")
        elif (core := CORE.get(name)) is not None:
            core(self, program[1:], here)
        elif name not in QUIET:
            self.unresolved.append(PROGRAM)

    def _setters(self, name: str, program: list[Word], ctx: _Context) -> None:
        """``export``, ``unset``, ``declare`` and kin, ``read`` and ``printf -v``: the names they set or unset."""
        args = [w.text for w in program[1:]]
        if name == "printf":
            dests = [b for a, b in pairwise(args) if a == "-v"]
            dests += [a[2:] for a in args if a.startswith("-v") and a[2:]]
        else:  # every operand, and an option's value too: a name it cannot tell is any name
            dests = [a for a in args if not a.startswith("-") or "$" in a]
        for dest in dests:
            name, _, value = dest.partition("=")
            for mentioned in WATCHED if "$" in name else {name, value}:  # a value: declare -n's referent
                self.changed(mentioned, ctx)

    def _unwrapped(self, words: list[Word], i: int) -> tuple[int, bool, set[str]]:
        """Where the wrapped program starts (none: ``len(words)``; not followed: -1), and the wrappers' changes."""
        chdir, scoped = False, set()
        texts = [w.text for w in words]
        for _ in range(NESTING + 1):
            name = PurePath(texts[i]).name if i < len(words) else ""
            if name not in WRAPPERS or not words[i].literal:
                break
            if name == "command" and texts[i + 1 : i + 2] in (["-v"], ["-V"]):
                return len(words), chdir, scoped  # names a program without running it
            k = operand(texts, i)
            if name == "env":
                split, moves, names = _env(texts[i + 1 : k])
                if split:
                    return -1, chdir, scoped
                chdir, scoped = chdir or moves, scoped | names
            i = k
        return i, chdir, scoped

    def _cd(self, program: list[Word], ctx: _Context) -> Path | str:
        """The logical directory a lone, literal ``cd`` moves to, ``..`` taken from the path as written (``cd -L``)."""
        args = program[1:]
        if not args:
            return ctx.env.get("HOME", ENV)
        arg = args[0]
        if len(args) > 1 or arg.pattern or arg.text.startswith("-") or not arg.text:
            return CWD
        text, reason = self.value(arg, ctx)
        if reason:
            return CWD if reason == VARIABLE else reason
        path = Path(text)
        if not path.is_absolute() and isinstance(ctx.cwd, str):
            return ctx.cwd
        return Path(os.path.normpath(path if path.is_absolute() else ctx.cwd / path))

    def _nested(self, program: list[Word], ctx: _Context, scoped: set[str], *, fed: bool) -> None:
        """A shell's ``-c`` script in its own context; unresolved when it runs a file, its input or startup input."""
        found = scripts([w.text for w in program])
        if not found:
            self.unresolved.append(PROGRAM)
            return
        options = [w.text for w in program[1:] if w.text != found[0]]
        if fed or {"BASH_ENV", "ENV"} & (scoped | ctx.env.keys()) or _startup(PurePath(program[0].text).name, options):
            self.unresolved.append(STARTUP)
            return
        word = next((w for w in program[1:] if w.text == found[0]), None)
        if word is None or not word.literal or self.depth >= NESTING:
            raise UnfollowedError
        self.depth += 1
        self.script(lex(found[0]), ctx.copy(unknown=scoped))
        self.depth -= 1

    def value(self, word: Word, ctx: _Context) -> tuple[str, str]:
        """*word* with HOME and TMPDIR expanded by *ctx*; else "" and the reason it is not known."""
        if word.expands:
            return "", VARIABLE
        out = []
        for name, raw in word.parts:
            found = ctx.env.get(name, VARIABLE) if name else raw
            if name and isinstance(found, str):
                return "", found
            out.append(str(found))
        return "".join(out), ""

    def options(self, args: Sequence[Word], allowed: str) -> list[Word] | None:
        """The operands of a command whose options are all among *allowed*' letters; None (unresolved) otherwise."""
        operands, ended = [], False
        for word in args:
            if not ended and word.text == "--":
                ended = True
            elif not ended and word.text.startswith("-") and len(word.text) > 1:
                if not word.literal or word.text.startswith("--") or not set(word.text[1:]) <= set(allowed):
                    self.unresolved.append(FORM)
                    return None
            else:
                operands.append(word)
        return operands

    def path(self, word: Word, ctx: _Context, *, follow: bool) -> Path | None:
        """*word*'s canonical path, the last component resolved if *follow*; None (unresolved) when not known."""
        text, reason = self.value(word, ctx)
        if not reason and word.pattern and (follow or any(c in text.rpartition("/")[0] for c in _GLOBS)):
            reason = PATTERN  # a removal's last component may be a pattern: it never follows a link
        if not reason and not Path(text).is_absolute() and isinstance(ctx.cwd, str):
            reason = ctx.cwd
        if reason:
            self.unresolved.append(reason)
            return None
        path = Path(text) if Path(text).is_absolute() else Path(ctx.cwd) / text
        return _real(path) if follow or text.endswith("/") else _kept(path)

    def _target(self, word: Word, ctx: _Context, kind: str, *, follow: bool) -> None:
        if (path := self.path(word, ctx, follow=follow)) is not None:
            self.targets.append(Target(kind, path))

    def each(self, args: Sequence[Word], ctx: _Context, allowed: str, kind: str) -> None:
        """Every operand of a command taking only *allowed* options, as one *kind* of target."""
        for word in self.options(args, allowed) or ():
            self._target(word, ctx, kind, follow=kind == "write")

    def copy(self, args: Sequence[Word], ctx: _Context, *, move: bool) -> None:
        """``cp`` or ``mv``: the destination written, a move's sources removed."""
        operands = self.options(args, "f" if move else "rRpf")
        if operands is None or not operands[1:]:
            return
        *sources, dest = operands
        for source in sources if move else ():
            self._target(source, ctx, "remove", follow=False)
        if not move and any(w.text.startswith("-") and set(w.text[1:]) & {"r", "R"} for w in args):
            self.unresolved.append(RECURSIVE)
        if dest.pattern and not dest.expands:
            self.unresolved.append(PATTERN)
            return
        if (base := self.path(dest, ctx, follow=False)) is None:
            return
        if base.is_symlink():
            self.unresolved.append(LINK)
        elif base.is_dir() or len(sources) > 1 or dest.text.endswith("/"):
            for source in sources:
                self._into(base, source, ctx, move=move)
        else:
            self.targets.append(Target("write", base))

    def _into(self, base: Path, source: Word, ctx: _Context, *, move: bool) -> None:
        """One source copied or moved into the directory *base*: ``base/name``, or *base* for a copy of contents."""
        text, reason = self.value(source, ctx)
        if reason or source.pattern:
            self.unresolved.append(reason or PATTERN)
            return
        name = PurePath(text).name
        if not move and (text.endswith("/") or name in {"", ".", ".."}):
            self.targets.append(Target("write", base))  # BSD cp copies a trailing slash's contents into base
            return
        if (path := base / name).is_symlink():
            self.unresolved.append(LINK)
        else:
            self.targets.append(Target("write", path))


def _env(options: Sequence[str]) -> tuple[bool, bool, set[str]]:
    """``env``'s words before its command: whether it splits a string, changes directory, and what it changes."""
    short = [o for o in options if o[:1] == "-" and o[1:2] not in {"-", ""}]
    split = any(o.startswith("--s") for o in options) or any("S" in o for o in short)
    chdir = any(o.startswith("--c") for o in options) or any("C" in o for o in short)
    names: set[str] = set()
    if "--ignore-environment" in options or any("i" in o.split("u", 1)[0] for o in short):
        names |= {"HOME", "TMPDIR"}  # cleared
    for k, o in enumerate(options):
        if ASSIGNMENT.match(o):
            names.add(o.split("=", 1)[0])
        elif o in {"-u", "--unset"}:
            names.add(options[k + 1] if k + 1 < len(options) else "")
        elif o.startswith(("--unset=", "-u")):
            names.add(o.removeprefix("--unset=").removeprefix("-u"))
    return split, chdir, names & WATCHED


def _startup(shell: str, options: Sequence[str]) -> bool:
    """Whether a shell reads startup files first: zsh and fish always, others when login or interactive."""
    if shell in {"zsh", "fish"}:
        return True
    short = [o for o in options if o.startswith("-") and not o.startswith("--")]
    return any(o.split("=", 1)[0] in _STARTUPS for o in options) or any({"l", "i"} & set(o[1:]) for o in short)


CORE: dict[str, Callable[[_Run, Sequence[Word], _Context], None]] = {
    "touch": lambda run, args, ctx: run.each(args, ctx, "c", "write"),
    "mkdir": lambda run, args, ctx: run.each(args, ctx, "p", "write"),
    "tee": lambda run, args, ctx: run.each(args, ctx, "a", "write"),
    "rm": lambda run, args, ctx: run.each(args, ctx, "rRf", "remove"),
    "rmdir": lambda run, args, ctx: run.each(args, ctx, "", "remove"),
    "unlink": lambda run, args, ctx: run.each(args, ctx, "", "remove"),
    "cp": lambda run, args, ctx: run.copy(args, ctx, move=False),
    "mv": lambda run, args, ctx: run.copy(args, ctx, move=True),
}
