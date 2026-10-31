"""The programs one shell command runs: through prefixes, assignments and wrapper programs.

Wrapper programs (env, xargs, timeout, find -exec, ...) run the command in their arguments; each program found keeps
the environment, launchers and context it runs with, which decide what a shell among them reads.
"""

from __future__ import annotations

import codecs
import re
import stat
from dataclasses import dataclass, field, replace
from pathlib import PurePath
from typing import TYPE_CHECKING

from owlbear_delivery_next.local_system.shell_parse import Word

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

_PREFIX_WORDS = frozenset({"!", "{", "do", "elif", "else", "if", "then", "time", "until", "while"})
ASSIGNMENT = re.compile(r"[A-Za-z_]\w*=")
SHELLS = frozenset({"ash", "bash", "dash", "fish", "ksh", "sh", "zsh"})
_SHELL_VALUES = frozenset({"-o", "+o", "-O", "+O"})  # shell options taking a value
_STARTUP = frozenset({"--rcfile", "--init-file"})  # options naming a file an interactive shell runs first
_EXEC = frozenset({"-exec", "-execdir", "-ok", "-okdir"})  # find's actions that run a command up to ; or +
_IN_PLACE = frozenset({"-execdir", "-okdir"})  # find's actions that run in each match's folder
NESTING = 3  # scripts inside scripts beyond this are refused unread
# Programs that run the command in their arguments: short options taking a value, long ones taking a value (unless
# attached with =), and the operands before the command (timeout's duration, flock's file).
_WRAPPERS: dict[str, tuple[str, frozenset[str], int]] = {
    "builtin": ("", frozenset(), 0),
    "caffeinate": ("tw", frozenset(), 0),
    "command": ("", frozenset(), 0),
    "env": ("uCS", frozenset({"--unset", "--chdir", "--split-string"}), 0),
    "exec": ("a", frozenset(), 0),
    "flock": ("wE", frozenset({"--wait", "--timeout", "--conflict-exit-code"}), 1),
    "ionice": ("cnpPu", frozenset({"--class", "--classdata", "--pid", "--pgid", "--uid"}), 0),
    "nice": ("n", frozenset({"--adjustment"}), 0),
    "nohup": ("", frozenset(), 0),
    "stdbuf": ("ioe", frozenset({"--input", "--output", "--error"}), 0),
    "sudo": ("ugCDhpURrtT", frozenset({"--user", "--group", "--close-from", "--chdir", "--host", "--prompt",
                                       "--role", "--type", "--other-user", "--command-timeout"}), 0),
    "timeout": ("sk", frozenset({"--signal", "--kill-after"}), 1),
    "watch": ("n", frozenset({"--interval"}), 0),
    "xargs": ("IEdLnPsaJ", frozenset({"--arg-file", "--delimiter", "--max-args", "--max-procs", "--max-chars",
                                      "--process-slot-var"}), 0),
}  # fmt: skip
_LOOKUP = frozenset({"-v", "-V"})  # command -v names a program without running it
_HEAD = 4096  # bytes of a program file read to tell a script from a binary


@dataclass(frozen=True)
class Run:
    """One program a command runs, from its name on, with what it runs with."""

    words: list[Word] = field(default_factory=list)
    env: dict[str, Word] = field(default_factory=dict)  # variables the command and its wrappers set for it
    launchers: tuple[Word, ...] = ()  # the wrapper programs it was started through, outermost first
    chdir: bool = False  # it runs in another folder: env -C, find -execdir
    replaced: str | None = None  # text xargs -I or find -exec replaces at run time, such as {}
    from_input: bool = False  # xargs adds operands it reads from its input


def name(word: str) -> str:
    """The program a word names, without its folder; ``.`` stays ``.``."""
    return PurePath(word).name or word


def assignments(words: Sequence[Word]) -> dict[str, Word]:
    """The variables the assignment words among *words* set, each value keeping whether it is expanded."""
    found = {}
    for w in words:
        if ASSIGNMENT.match(w):
            key, _, value = w.partition("=")
            found[key] = Word(value, expanded=getattr(w, "expanded", False) or value.startswith("~"))
    return found


def runs(words: Sequence[Word], depth: int = 0, context: Run | None = None) -> list[Run]:
    """Each program one command's words run, through prefixes, assignments and wrappers."""
    context = context or Run()
    i = next((i for i, w in enumerate(words) if w not in _PREFIX_WORDS and not ASSIGNMENT.match(w)), len(words))
    if i == len(words):
        return []
    here = replace(context, env={**context.env, **assignments(words[:i])})
    program = name(words[i])
    if program == "find":
        return _found(words, i, depth, here)
    if program == "command" and words[i + 1 : i + 2] and words[i + 1] in _LOOKUP:
        return []
    if program in _WRAPPERS and depth < NESTING:
        return _wrapped(words, i, depth, here)
    return [replace(here, words=list(words[i:]))]


def _found(words: Sequence[Word], i: int, depth: int, context: Run) -> list[Run]:
    """The commands find's -exec actions run, with each match's path replacing {}."""
    starts = [j + 1 for j, w in enumerate(words) if w in _EXEC and j + 1 < len(words)]
    found = []
    for j in starts:
        k = next((k for k in range(j, len(words)) if words[k] in {";", "+"}), len(words))
        if k > j:
            sub = replace(context, launchers=(*context.launchers, words[i]), replaced="{}")
            found += runs(words[j:k], depth + 1, replace(sub, chdir=sub.chdir or words[j - 1] in _IN_PLACE))
    return found


def _wrapped(words: Sequence[Word], i: int, depth: int, context: Run) -> list[Run]:
    k = operand(words, i)
    sub = replace(context, launchers=(*context.launchers, words[i]))
    match name(words[i]):
        case "env":
            env = {**sub.env, **assignments(words[i + 1 : k])}
            sub = replace(sub, env=env, chdir=sub.chdir or _env_chdir(words, i, k))
        case "xargs":
            sub = replace(sub, from_input=True, replaced=_replacement(words, i, k) or sub.replaced)
    return runs(words[k:], depth + 1, sub)


def _env_chdir(words: Sequence[Word], i: int, k: int) -> bool:
    return any(w.startswith("--chdir") or (re.fullmatch(r"-[^-]*C.*", w) is not None) for w in words[i + 1 : k])


def _replacement(words: Sequence[Word], i: int, k: int) -> str | None:
    """The text xargs replaces with each input line (-I, -J, -i, --replace), if any."""
    for j in range(i + 1, k):
        w = words[j]
        if w in {"-I", "-J"}:
            return words[j + 1] if j + 1 < k else None
        if w in {"-i", "--replace"}:
            return "{}"
        if w.startswith("--replace="):
            return w.partition("=")[2]
        if w.startswith(("-I", "-J", "-i")):
            return w[2:]
    return None


def operand(words: Sequence[Word], i: int) -> int:
    """The index of the command the wrapper at ``words[i]`` runs: after its options, their values and operands."""
    program = name(words[i])
    values, longs, skip = _WRAPPERS[program]
    k = i + 1
    while k < len(words):
        w = words[k]
        if w == "--":
            k += 1
            break
        if w.startswith("--"):
            k += 2 if w in longs else 1  # --name=value is one word
        elif w.startswith("-") and len(w) > 1:
            at = next((j for j, ch in enumerate(w[1:], 1) if ch in values), None)
            k += 2 if at == len(w) - 1 else 1  # a value option last in its cluster takes the next word
        elif program == "env" and ASSIGNMENT.match(w):
            k += 1
        else:
            break
    return k + skip


@dataclass(frozen=True)
class ShellArgs:
    """What one shell invocation runs: a -c script, a script file, or its standard input, after its startup files."""

    script: Word | None = None
    operand: Word | None = None
    reads_stdin: bool = False
    startup: tuple[Word, ...] = ()


def shell_args(words: Sequence[Word]) -> ShellArgs:
    """Read a shell's options (its program first): its -c script, its script operand, or -s and no operand."""
    command = stdin = False
    startup: list[Word] = []
    i = 1
    while i < len(words):
        w = words[i]
        if w == "--":
            i += 1
            break
        if w in _STARTUP:
            startup += words[i + 1 : i + 2]
            i += 2
        elif w in _SHELL_VALUES:
            i += 2
        elif w.startswith(("-", "+")) and w not in {"-", "+"}:
            command = command or (not w.startswith("--") and "c" in w[1:])
            stdin = stdin or (not w.startswith("--") and "s" in w[1:])
            i += 1
        else:
            break
    rest = words[i:]
    if command:
        return ShellArgs(script=rest[0] if rest else None, startup=tuple(startup))
    if stdin or not rest:
        return ShellArgs(reads_stdin=True, startup=tuple(startup))
    return ShellArgs(operand=rest[0], startup=tuple(startup))


def _regular(path: Path) -> None:
    """Refuse anything but a regular file before opening it: a FIFO or a device would block or never end.

    Raises:
        OSError: The path is missing or not a regular file.
    """
    if not stat.S_ISREG(path.stat().st_mode):
        raise OSError(0, "it is not a regular file", str(path))


def read_script(path: Path) -> str:
    """The text of the script file at *path*.

    Raises:
        OSError: It is missing, unreadable or not a regular file.
        UnicodeDecodeError: It is not UTF-8 text.
    """
    _regular(path)
    return path.read_bytes().decode("utf-8")


def shebang(path: Path) -> list[Word] | None:
    """The interpreter a program file runs with, as the words before its path; None for a binary.

    A text file without #! runs as a shell script, as the shell does when the system can't run it. The rest of a #!
    line after the interpreter is one argument, as Linux passes it.

    Raises:
        OSError: It is missing, unreadable or not a regular file.
    """
    _regular(path)
    with path.open("rb") as file:
        head = file.read(_HEAD)
    if head.startswith(b"#!"):
        line = head[2:].split(b"\n", 1)[0].decode("utf-8", "replace").strip()
        interpreter, _, rest = line.partition(" ")
        return [Word(w) for w in (interpreter, rest.strip()) if w]
    if b"\0" in head:
        return None
    try:
        codecs.getincrementaldecoder("utf-8")().decode(head, final=False)  # a character cut at the end is fine
    except UnicodeDecodeError:
        return None
    return [Word("sh")]
