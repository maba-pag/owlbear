"""Shell text as the permission guard reads it: each command's words, and the commands and scripts they run.

The lexer splits shell text at unquoted operators and into subshells and substitutions. A command's program is
found through prefixes, assignments and wrapper programs (env, xargs, timeout, find -exec, ...); a nested shell's
-c script and eval's arguments are handed back as text to be judged again.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import PurePath
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

_REDIRECTION = re.compile(r"&?[<>]+[&|]?")
_PREFIX_WORDS = frozenset({"!", "{", "do", "elif", "else", "if", "then", "time", "until", "while"})
ASSIGNMENT = re.compile(r"[A-Za-z_]\w*=")
SHELLS = frozenset({"ash", "bash", "dash", "fish", "ksh", "sh", "zsh"})
_SHELL_VALUES = frozenset({"-o", "+o", "-O", "+O", "--rcfile", "--init-file"})  # shell options taking a value
_EXEC = frozenset({"-exec", "-execdir", "-ok", "-okdir"})  # find's actions that run a command up to ; or +
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
    "xargs": ("IEdLnPsa", frozenset({"--arg-file", "--delimiter", "--max-args", "--max-procs", "--max-chars",
                                     "--process-slot-var"}), 0),
}  # fmt: skip
_LOOKUP = frozenset({"-v", "-V"})  # command -v names a program without running it


@dataclass
class _Level:
    """The command being read at one nesting level of shell text."""

    words: list[str] = field(default_factory=list)
    word: str | None = None
    quote: str = ""
    redirect: bool = False  # the next word is a redirection's target, not an argument

    def add(self, chars: str) -> None:
        self.word = (self.word or "") + chars

    def end_word(self) -> None:
        if self.word is not None:
            if not self.redirect:
                self.words.append(self.word)
            self.redirect = False
        self.word = None

    def end_command(self, commands: list[list[str]]) -> None:
        self.end_word()
        if self.words:
            commands.append(self.words)
        self.words, self.redirect = [], False


class _Lexer:
    """Splits shell text into each command's words at unquoted operators and newlines, and into substitutions."""

    def __init__(self, text: str) -> None:
        self.text = text
        self.commands: list[list[str]] = []

    def level(self, i: int, close: str = "") -> int:
        """Read text[i:] up to the unquoted *close*, or to the end without one; return the index after it.

        Raises:
            ValueError: A quote, subshell or substitution is not closed.
        """
        s = _Level()
        while i < len(self.text) and (s.quote or self.text[i] != close):
            i = self._step(s, i)
        if s.quote or (close and i >= len(self.text)):
            raise ValueError
        s.end_command(self.commands)
        return i + 1

    def _step(self, s: _Level, i: int) -> int:
        text, ch = self.text, self.text[i]
        if s.quote == "'" or (s.quote and ch == '"'):
            if ch == s.quote:
                s.quote = ""
            else:
                s.add(ch)
            return i + 1
        if ch == "\\":
            nxt = text[i + 1 : i + 2]
            if nxt != "\n":
                s.add(nxt if not s.quote or nxt in '"\\`$' else ch + nxt)
            return i + 2
        if ch == "`" or text.startswith("$(", i):
            s.add("$")  # the substitution's commands are checked on their own
            return self.level(i + 1, "`") if ch == "`" else self.level(i + 2, ")")
        if s.quote:
            s.add(ch)
            return i + 1
        return self._unquoted(s, i)

    def _unquoted(self, s: _Level, i: int) -> int:
        text, ch = self.text, self.text[i]
        if ch in "'\"":
            s.quote = ch
            s.add("")
        elif ch == "#" and s.word is None:
            end = text.find("\n", i)
            return len(text) if end < 0 else end
        elif match := _REDIRECTION.match(text, i):
            if s.word is not None and s.word.isdigit():
                s.word = None  # a file descriptor
            s.end_word()
            s.redirect = True
            return match.end()
        elif ch == "(":
            s.end_command(self.commands)
            return self.level(i + 1, ")")
        elif ch in ";&|\n)":
            s.end_command(self.commands)
        elif ch in " \t":
            s.end_word()
        else:
            s.add(ch)
        return i + 1


def commands(text: str) -> list[list[str]]:
    """The words of each command in *text*, including those of subshells and command substitutions.

    Raises:
        ValueError: The text cannot be parsed.
    """
    lexer = _Lexer(text)
    lexer.level(0)
    return lexer.commands


def programs(words: Sequence[str], depth: int = 0) -> list[Sequence[str]]:
    """Each command one command's words run, from its program on: through prefixes, assignments and wrappers."""
    i = next((i for i, w in enumerate(words) if w not in _PREFIX_WORDS and not ASSIGNMENT.match(w)), len(words))
    if i == len(words):
        return []
    name = PurePath(words[i]).name
    if name == "find":
        starts = [j + 1 for j, w in enumerate(words) if w in _EXEC and j + 1 < len(words)]
        ends = [next((k for k in range(j, len(words)) if words[k] in {";", "+"}), len(words)) for j in starts]
        return [p for j, k in zip(starts, ends, strict=True) if k > j for p in programs(words[j:k], depth + 1)]
    if name == "command" and words[i + 1 : i + 2] and words[i + 1] in _LOOKUP:
        return []
    if name in _WRAPPERS and depth < NESTING:
        return programs(words[operand(words, i) :], depth + 1)
    return [words[i:]]


def operand(words: Sequence[str], i: int) -> int:
    """The index of the command the wrapper at ``words[i]`` runs: after its options, their values and operands."""
    name = PurePath(words[i]).name
    values, longs, skip = _WRAPPERS[name]
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
        elif name == "env" and ASSIGNMENT.match(w):
            k += 1
        else:
            break
    return k + skip


def _shell_script(words: Sequence[str]) -> str | None:
    """The -c script of one shell command (its program first), or None when it runs a file or reads its input."""
    script, i = False, 1
    while i < len(words):
        w = words[i]
        if w == "--":
            i += 1
            break
        if w in _SHELL_VALUES:
            i += 2
        elif w.startswith(("-", "+")) and w not in {"-", "+"}:
            script = script or (not w.startswith("--") and "c" in w[1:])
            i += 1
        else:
            break
    return words[i] if script and i < len(words) else None


def scripts(words: Sequence[str]) -> list[str]:
    """The shell text a command hands on: each shell's -c script, and eval's arguments."""
    found = []
    for prog in programs(words):
        name = PurePath(prog[0]).name
        if name == "eval":
            rest = list(prog[1:])
            found.append(" ".join(rest[1:] if rest[:1] == ["--"] else rest))
        elif name in SHELLS and (script := _shell_script(prog)) is not None:
            found.append(script)
    return found
