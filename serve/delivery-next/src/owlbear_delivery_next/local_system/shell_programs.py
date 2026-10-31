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

_PREFIX_WORDS = frozenset({"!", "{", "do", "elif", "else", "if", "then", "until", "while"})  # time: see head()
ASSIGNMENT = re.compile(r"[A-Za-z_]\w*=")
SHELLS = frozenset({"ash", "bash", "dash", "fish", "ksh", "sh", "zsh"})
_STARTUP = frozenset({"--rcfile", "--init-file"})  # options naming a file an interactive shell runs first
_EXEC = frozenset({"-exec", "-execdir", "-ok", "-okdir"})  # find's actions that run a command up to ; or +
_IN_PLACE = frozenset({"-execdir", "-okdir"})  # find's actions that run in each match's folder
NESTING = 3  # scripts inside scripts beyond this are refused unread
_WRAPPED = 8  # wrapper programs inside wrapper programs beyond this are refused unread
_WRAPPED_UNREAD = f"runs wrapper programs more than {_WRAPPED} deep"
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
_HEAD = 4096  # bytes of a program file read to tell a script from a binary
_ESCAPES = {"t": "\t", "n": "\n", "v": "\v", "f": "\f", "r": "\r", "'": "'", '"': '"', "\\": "\\", "$": "$", "#": "#"}
_VARIABLE = re.compile(r"\$\{[A-Za-z_]\w*\}")
_SPLIT_UNREAD = "uses env -S with text the guard can't read"
_SPLIT_BUILT = "uses env -S with text built at run time; write it out"


class UnreadableError(ValueError):
    """Text the guard can't read, its reason the message."""


@dataclass(frozen=True)
class Run:
    """One program a command runs, from its name on, with what it runs with."""

    words: list[Word] = field(default_factory=list)
    env: dict[str, Word] = field(default_factory=dict)  # variables the command and its wrappers set for it
    launchers: tuple[Word, ...] = ()  # the wrapper programs it was started through, outermost first
    chdir: bool = False  # it runs in another folder: env -C, find -execdir
    replaced: str | None = None  # text xargs -I or find -exec replaces at run time, such as {}
    from_input: bool = False  # xargs adds operands it reads from its input
    removed: frozenset[str] = frozenset()  # variables env -u removed from what it inherited; * for env -i


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


def head(words: Sequence[str], i: int = 0) -> int:
    """The index of the word a command runs, after control words, assignments and time with its options."""
    while i < len(words):
        if words[i] == "time":
            i += 1
            while i < len(words) and words[i].startswith("-"):
                i += 1
        elif words[i] == "function":  # function NAME { body: the body's first command
            i += 2
        elif words[i] in _PREFIX_WORDS or ASSIGNMENT.match(words[i]):
            i += 1
        else:
            break
    return min(i, len(words))


def lookup(words: Sequence[str], i: int) -> bool:
    """Whether the ``command`` at ``words[i]`` only names a program (-v, -V, -pv, -p -v), running nothing."""
    j = i + 1
    while j < len(words) and words[j].startswith("-") and words[j] != "-":
        if words[j] == "--":
            break
        if set(words[j][1:]) & {"v", "V"}:
            return True
        j += 1
    return False


def builtin(words: Sequence[str]) -> int:
    """The index of the builtin a command runs, past ``command`` or ``builtin`` and their options too.

    The index of ``command`` itself for a lookup (command -v unset ...), which runs nothing.
    """
    i = head(words)
    while i < len(words) - 1 and words[i] in {"command", "builtin"}:
        if words[i] == "command" and lookup(words, i):
            return i
        i += 1
        while i < len(words) - 1 and words[i].startswith("-"):
            i += 1
    return i


def runs(words: Sequence[Word], depth: int = 0, context: Run | None = None) -> list[Run]:
    """Each program one command's words run, through prefixes, assignments and wrappers."""
    context = context or Run()
    i = head(words)
    if i == len(words):
        return []
    here = replace(context, env={**context.env, **assignments(words[:i])})
    if getattr(words[i], "expanded", False):  # a wrapper's name built at run time may be anything
        return [replace(here, words=list(words[i:]))]
    program = name(words[i])
    if program == "find":
        return _found(words, i, depth, here)
    if words[i] == "command" and lookup(words, i):  # it runs nothing, but the launchers before it run
        return [replace(here, words=[here.launchers[-1]], launchers=here.launchers[:-1])] if here.launchers else []
    if program in _WRAPPERS:
        if depth >= _WRAPPED:
            raise UnreadableError(_WRAPPED_UNREAD)
        return _wrapped(words, i, depth, here)
    return [replace(here, words=list(words[i:]))]


def leafless(words: Sequence[Word]) -> Run | None:
    """A command whose wrappers run nothing (env ./env, find .): its launchers by path, its last one the program.

    None for a lookup (command -v) alone, which runs nothing.
    """
    i, launchers = head(words), []
    while i < len(words) and name(words[i]) in _WRAPPERS:
        if words[i] == "command" and lookup(words, i):  # runs() gives the launchers before it
            return None
        launchers.append(words[i])
        i = operand(words, i)
    program = words[i] if i < len(words) else launchers.pop() if launchers else Word()
    return Run(words=[program, *words[i + 1 :]], launchers=tuple(launchers))


def _found(words: Sequence[Word], i: int, depth: int, context: Run) -> list[Run]:
    """The commands find's -exec actions run, with each match's path replacing {}."""
    found = []
    for j in (j + 1 for j, w in enumerate(words) if w in _EXEC and j + 1 < len(words)):
        k = next((k for k in range(j, len(words)) if words[k] in {";", "+"}), len(words))
        sub = replace(context, launchers=(*context.launchers, words[i]), replaced="{}")
        found += runs(words[j:k], depth + 1, replace(sub, chdir=sub.chdir or words[j - 1] in _IN_PLACE))
    return found


def _wrapped(words: Sequence[Word], i: int, depth: int, context: Run) -> list[Run]:
    k = operand(words, i)
    sub = replace(context, launchers=(*context.launchers, words[i]))
    match name(words[i]):
        case "env":
            split, k = _env_split(words, i, k)  # env's own options end with its -S string
            cleared, unset = _env_removals(words, i, k)
            kept = {} if cleared else {key: v for key, v in sub.env.items() if key not in unset}
            env = {**kept, **assignments(words[i + 1 : k])}
            removed = sub.removed | unset | ({"*"} if cleared else set())
            sub = replace(sub, env=env, chdir=sub.chdir or _env_chdir(words, i, k), removed=frozenset(removed))
            if split is not None:  # its words go where it stood, before the rest, and env reads them again
                return runs([Word("env"), *split, *words[k:]], depth + 1, sub)
        case "xargs":
            sub = replace(sub, from_input=True, replaced=_replacement(words, i, k) or sub.replaced)
    return runs(words[k:], depth + 1, sub)


def _env_split(words: Sequence[Word], i: int, k: int) -> tuple[list[Word] | None, int]:
    """The words env -S gives among the options of the env at ``words[i]``, or None, and where those options end.

    They end right after the string, as env splices its words in place, or at *k* without one.
    """
    found: list[Word] | None = None
    j = i + 1
    while j < k and found is None:
        w, value = words[j], None
        if w.startswith("--split-string"):
            value, j = (_part(w, w.partition("=")[2]), j + 1) if "=" in w else (_at(words, j + 1), j + 2)
        elif w.startswith("-") and not w.startswith("--") and (at := _valued(w)):
            rest = _part(w, w[at + 1 :])
            given, j = (rest, j + 1) if rest else (_at(words, j + 1), j + 2)
            value = given if w[at] == "S" else None
        else:
            j += 1
        if value is not None:
            if value.expanded:  # the outer shell filled it in: what env splits is built at run time
                raise UnreadableError(_SPLIT_BUILT)
            found = split_string(value)
    return found, (j if found is not None else k)


def _valued(cluster: str) -> int | None:
    """The index of the first option taking a value in an env option cluster (-u, -C, -S), if any."""
    return next((p for p, ch in enumerate(cluster[1:], 1) if ch in "uCS"), None)


def _part(word: Word, text: str) -> Word:
    """Part of a word, still marked as the shell expands the word."""
    return Word(text, expanded=getattr(word, "expanded", False))


def _at(words: Sequence[Word], j: int) -> Word:
    return words[j] if j < len(words) else Word()


def split_string(text: str) -> list[Word]:
    r"""Split an env -S string as env does: quotes, escapes, \_ and \c; ${NAME} marks its word expanded.

    Raises:
        UnreadableError: It holds a quote left open, an escape env doesn't define or a $ other than ${NAME}.
    """
    splitter = _Splitter(text)
    i = 0
    while 0 <= i < len(text):
        i = splitter.step(i)
    if splitter.quote:
        raise UnreadableError(_SPLIT_UNREAD)
    splitter.flush()
    return splitter.words


@dataclass
class _Splitter:
    """The words an env -S string splits into so far, and the word being read."""

    text: str
    words: list[Word] = field(default_factory=list)
    current: str | None = None
    expanded: bool = False
    quote: str = ""

    def add(self, chars: str) -> None:
        self.current = (self.current or "") + chars

    def flush(self) -> None:
        if self.current is not None:
            self.words.append(Word(self.current, expanded=self.expanded))
        self.current, self.expanded = None, False

    def step(self, i: int) -> int:
        """Read the character at *i*; return the next index, or -1 where the string ends early."""
        ch = self.text[i]
        if self.quote == "'":
            return self._single(ch, i)
        if ch == "\\":
            return self._escape(i)
        if ch == "$":
            if not (match := _VARIABLE.match(self.text, i)):
                raise UnreadableError(_SPLIT_UNREAD)
            self.add(match[0])
            self.expanded = True
            return match.end()
        if self.quote == '"':
            self.quote = "" if ch == '"' else self.quote
            if self.quote:
                self.add(ch)
        elif ch in "'\"":
            self.quote = ch
            self.add("")
        elif ch in " \t\n\r\f\v":
            self.flush()
        elif ch == "#" and self.current is None:
            return -1
        else:
            self.add(ch)
        return i + 1

    def _single(self, ch: str, i: int) -> int:
        if ch == "\\" and (nxt := self.text[i + 1 : i + 2]) in {"\\", "'"}:  # env's only escapes in single quotes
            self.add(nxt)
            return i + 2
        if ch == "'":
            self.quote = ""
        else:
            self.add(ch)
        return i + 1

    def _escape(self, i: int) -> int:
        nxt = self.text[i + 1 : i + 2]
        if nxt == "c":
            return -1
        if nxt == "_" and not self.quote:
            self.flush()
        elif nxt == "_":
            self.add(" ")
        elif nxt in _ESCAPES:
            self.add(_ESCAPES[nxt])
        else:
            raise UnreadableError(_SPLIT_UNREAD)
        return i + 2


def _env_removals(words: Sequence[Word], i: int, k: int) -> tuple[bool, set[str]]:
    """Whether the env at ``words[i]`` clears its environment (-i), and the variables it unsets (-u NAME)."""
    cleared, unset, j = False, set(), i + 1
    while j < k:
        w = words[j]
        if w in {"-", "-i", "--ignore-environment"}:
            cleared = True
        elif w.startswith("--unset"):
            unset.add(w.partition("=")[2] or _at(words, j + 1))
            j += 0 if "=" in w else 1
        elif w.startswith("-") and not w.startswith("--") and (at := _valued(w)) is not None:
            cleared = cleared or "i" in w[1:at]
            if w[at] == "u":
                unset.add(w[at + 1 :] or _at(words, j + 1))
            j += 0 if w[at + 1 :] else 1
        elif w.startswith("-") and not w.startswith("--"):
            cleared = cleared or "i" in w[1:]
        j += 1
    return cleared, unset


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
        if w == "-" and program == "env":  # env -: an empty environment
            k += 1
        elif w.startswith("--"):
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
    operand: Word | None = None  # None with no script: it reads its standard input
    startup: tuple[Word, ...] = ()
    own_startup: bool = False  # it reads startup files of its own: zsh, fish, an interactive or login bash or sh
    reads: frozenset[str] = frozenset()  # the startup variables it reads: BASH_ENV (bash -c), ENV (an interactive sh)


def shell_args(words: Sequence[Word]) -> ShellArgs:
    """Read a shell's options (its program first): its -c script, its script operand, or -s and no operand."""
    command = stdin = False
    startup: list[Word] = []
    flags: set[str] = set()  # short option letters and long options given
    i = 1
    while i < len(words):
        w = words[i]
        if w == "--":
            i += 1
            break
        if w in _STARTUP:
            startup += words[i + 1 : i + 2]
            i += 2
        elif w.startswith(("-", "+")) and w not in {"-", "+"}:
            short = "" if w.startswith("--") else w[1:]
            values = words[i + 1 : i + 1 + sum(ch in "oO" for ch in short)]  # -o and -O take a word each, -eco too
            plus = w.startswith("+")
            reverse = {"reversed"} if "posix" in values or (plus and "i" in short) else set()  # not followed
            flags |= {w} if not short else reverse if plus else set(short) | reverse
            command, stdin = command or "c" in short, stdin or "s" in short
            i += 1 + len(values)
        else:
            break
    rest = words[i:]
    shell, interactive = name(words[0]), "i" in flags
    own = _own_startup(shell, flags | ({"--rcfile"} if startup else set()))
    reads = frozenset(
        {"BASH_ENV", "ENV"} if "reversed" in flags  # a mode turned off again: read every one it may read
        else {"BASH_ENV"} if shell == "bash" and not interactive and "--posix" not in flags
        else {"ENV"} if interactive and (shell != "bash" or "--posix" in flags) else set()
    )  # fmt: skip
    rc = tuple(startup) if interactive or "reversed" in flags else ()  # --rcfile only when interactive
    if command:
        return ShellArgs(script=rest[0] if rest else None, startup=rc, own_startup=own, reads=reads)
    return ShellArgs(operand=None if stdin or not rest else rest[0], startup=rc, own_startup=own, reads=reads)


def _own_startup(shell: str, flags: set[str]) -> bool:
    """Whether a shell started with *flags* reads startup files from the home folder that no option names."""
    match shell:
        case "zsh":  # .zshenv always, unless -f
            return "f" not in flags and "--no-rcs" not in flags
        case "fish":
            return "N" not in flags and "--no-config" not in flags
        case "bash":
            interactive = "i" in flags and not flags & {"--norc", "--rcfile"}
            return interactive or (("l" in flags or "--login" in flags) and "--noprofile" not in flags)
    return "l" in flags or "--login" in flags  # a login sh, dash, ksh reads ~/.profile


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
        line = head[2:].split(b"\n", 1)[0].decode("utf-8", "replace").split(None, 1)
        return [Word(w.strip()) for w in line] or [Word("sh")]  # an empty #!: the shell runs it
    if b"\0" in head:
        return None
    try:
        codecs.getincrementaldecoder("utf-8")().decode(head, final=False)  # a character cut at the end is fine
    except UnicodeDecodeError as error:  # no NUL byte: bash still runs it as a script, which can't be read
        raise OSError(0, "it is not UTF-8 text", str(path)) from error
    return [Word("sh")]
