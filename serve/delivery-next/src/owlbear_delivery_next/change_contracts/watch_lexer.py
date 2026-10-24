"""Shell text as the watcher reads it (W1b-1, design §3.6 slice 3): commands, their words and their redirections.

The watcher's own lexer, apart from the guard's (``shell_parse`` drops redirection targets). It scans characters
with their quote state: single and double quotes, backslashes, comments, and the expansions of ``$HOME``, ``$TMPDIR``
and ``~``, kept apart in each word so that the effect model expands them by the environment of their moment; other
variables are marked. Operators count only unquoted: ``;``, ``&&``, ``||``, ``|``, ``&`` and newline between
commands, and the redirections ``>``, ``>>``, ``>|``, ``&>``, ``N>``, ``N>>``, ``<`` and their kin. Every word keeps
whether any part of it was quoted. A heredoc's delimiter is its word after quote removal only, never expanded; its
body is consumed up to the delimiter line and never classified, and an unquoted body that runs a command
substitution is marked. Anything else structural (a command or process
substitution, a subshell, a group, a compound command's keyword, ANSI-C quoting) raises ``UnfollowedError``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

EXPANDED = frozenset({"HOME", "TMPDIR"})  # the variables a word keeps as expansions; any other one is marked
KEYWORDS = frozenset({"if", "then", "elif", "else", "fi", "for", "select", "while", "until", "do", "done", "case",
                      "esac", "function", "coproc", "[[", "]]", "{", "}"})  # fmt: skip
WRITES = frozenset({">", ">>", ">|", "&>", "&>>", "<>", ">&"})  # redirections that open their target for writing
_REDIRECT = re.compile(r"&>>|&>|>>|>\||>&|>|<<<|<<-|<<|<>|<&|<")
_OPERATORS = ("&&", "||", "|&", ";", "|", "&")
_NAME = re.compile(r"[A-Za-z_]\w*")
_BRACES = re.compile(r"\{[^{}]*(,|\.\.)[^{}]*\}|\[.+\]")  # a brace expansion or a bracket glob
_SPECIAL = "@*#?$!-0123456789"  # $@, $?, $1 ...: never a literal value


class UnfollowedError(ValueError):
    """Shell text the watcher does not follow; the whole call stays unresolved."""


@dataclass(frozen=True)
class Word:
    """One word after quote removal, its expansions of HOME and TMPDIR kept apart, and what else it holds."""

    text: str  # as written after quote removal: ``$HOME``, ``${TMPDIR}`` and ``~`` unexpanded
    quoted: bool = False  # any part was quoted or escaped
    expands: bool = False  # a variable other than HOME or TMPDIR, or ``~user``
    pattern: bool = False  # an unquoted glob or brace expansion
    parts: tuple[tuple[str, str], ...] = ()  # (variable, as written) for an expansion, ("", text) for a literal

    @property
    def literal(self) -> bool:
        """Whether the word is its text: no expansion at all."""
        return not self.expands and not any(name for name, _ in self.parts)


@dataclass(frozen=True)
class Redirect:
    """A redirection that opens its target for writing."""

    op: str
    target: Word


@dataclass
class Command:
    """One simple command: its words, its write redirections and the operators around it ("" at either end)."""

    words: list[Word] = field(default_factory=list)
    redirects: list[Redirect] = field(default_factory=list)
    before: str = ""
    after: str = ""
    reads: bool = False  # an input redirection, heredoc or here-string feeds it


@dataclass(frozen=True)
class Script:
    """Shell text read: its commands in order, and whether an unquoted heredoc body runs a command substitution."""

    commands: tuple[Command, ...]
    substituting: bool = False


def lex(text: str) -> Script:
    """The commands of *text*.

    Raises:
        UnfollowedError: The text holds a construct the watcher does not follow, or is not complete.
    """
    return _Lexer(text).script()


class _Lexer:
    """Reads shell text once, left to right."""

    def __init__(self, text: str) -> None:
        self.text = text
        self.commands: list[Command] = []
        self.command, self.before = Command(), ""
        self.chars: list[tuple[str, str]] | None = None  # the word being read, as Word.parts; None between words
        self.quoted = self.expands = self.globbing = self.braced = self.tilde = False  # braced: { or [ seen
        self.pending = ""  # a redirection operator waiting for its target
        self.heredocs: list[tuple[str, bool, bool]] = []  # delimiter, tabs stripped, body literal
        self.substituting = False
        self.handlers = {"'": self._single, '"': self._double, "\\": self._escape, "$": self._dollar,
                         "`": self._refuse, "(": self._refuse, ")": self._refuse, " ": self._blank,
                         "\t": self._blank, "\n": self._newline, "#": self._hash, ";": self._operator,
                         "&": self._operator, "|": self._operator, ">": self._redirect,
                         "<": self._redirect}  # fmt: skip

    def script(self) -> Script:
        i = 0
        while i < len(self.text):
            i = self.handlers.get(self.text[i], self._char)(i)
        self._end_command("")
        return Script(tuple(self.commands), self.substituting)

    def _add(self, chars: str, *, quoted: bool = False, name: str = "") -> None:
        if self.chars is None:
            self.chars = []
            self.tilde = chars.startswith("~") and not quoted and not name
        self.chars.append((name, chars))
        self.quoted = self.quoted or quoted

    def _char(self, i: int) -> int:
        ch = self.text[i]
        self.globbing = self.globbing or ch in "*?"
        self.braced = self.braced or ch in "{["
        self._add(ch)
        return i + 1

    def _refuse(self, _i: int) -> int:
        raise UnfollowedError

    def _blank(self, i: int) -> int:
        self._end_word()
        return i + 1

    def _hash(self, i: int) -> int:
        if self.chars is not None:
            return self._char(i)
        end = self.text.find("\n", i)
        return len(self.text) if end < 0 else end

    def _single(self, i: int) -> int:
        end = self.text.find("'", i + 1)
        if end < 0:
            raise UnfollowedError
        self._add(self.text[i + 1 : end], quoted=True)
        return end + 1

    def _double(self, i: int) -> int:
        self._add("", quoted=True)
        j = i + 1
        while j < len(self.text) and self.text[j] != '"':
            ch, nxt = self.text[j], self.text[j + 1 : j + 2]
            if ch == "`":
                raise UnfollowedError
            if ch == "$":
                j = self._dollar(j, quoted=True)
            elif ch == "\\" and nxt and nxt in '$`"\\\n':
                self._add("" if nxt == "\n" else nxt, quoted=True)
                j += 2
            else:
                self._add(ch, quoted=True)
                j += 1
        if j >= len(self.text):
            raise UnfollowedError
        return j + 1

    def _escape(self, i: int) -> int:
        nxt = self.text[i + 1 : i + 2]
        if nxt != "\n":
            self._add(nxt or "\\", quoted=True)
        return i + 2

    def _dollar(self, i: int, *, quoted: bool = False) -> int:
        nxt = self.text[i + 1 : i + 2]
        if nxt == "(" or (nxt and nxt in "'\"" and not quoted):  # substitution, arithmetic, $'...' or $"..."
            raise UnfollowedError
        if nxt == "{":
            end = self.text.find("}", i + 2)
            if end < 0:
                raise UnfollowedError
            return self._variable(self.text[i + 2 : end], self.text[i : end + 1], end + 1, quoted=quoted)
        if name := _NAME.match(self.text, i + 1):
            return self._variable(name.group(), "$" + name.group(), name.end(), quoted=quoted)
        if nxt and nxt in _SPECIAL:
            self.expands = True
            self._add(self.text[i : i + 2], quoted=quoted)
            return i + 2
        self._add("$", quoted=quoted)
        return i + 1

    def _variable(self, name: str, raw: str, end: int, *, quoted: bool) -> int:
        kept = name in EXPANDED
        self.expands = self.expands or not kept
        self._add(raw, quoted=quoted, name=name if kept else "")
        return end

    def _operator(self, i: int) -> int:
        if self.text.startswith("&>", i):
            return self._redirect(i)
        if self.text.startswith(";;", i) or self.text.startswith(";&", i):  # a case clause's end
            raise UnfollowedError
        op = next(o for o in _OPERATORS if self.text.startswith(o, i))
        self._end_command("|" if op == "|&" else op)
        return i + len(op)

    def _redirect(self, i: int) -> int:
        if self.chars is not None and not self.quoted and "".join(c for _, c in self.chars).isdigit():
            self.chars = None  # a file descriptor's number, not a word
        self._end_word()
        match = _REDIRECT.match(self.text, i)
        if self.pending or match is None:
            raise UnfollowedError
        self.pending = match.group()
        return match.end()

    def _newline(self, i: int) -> int:
        self._end_command("\n")
        return self._bodies(i + 1) if self.heredocs else i + 1

    def _bodies(self, i: int) -> int:
        """Skip each pending heredoc's body, up to its delimiter line; mark an unquoted one that substitutes."""
        for delimiter, strip, literal in self.heredocs:
            while i < len(self.text):
                end = self.text.find("\n", i)
                end = len(self.text) if end < 0 else end
                line, i = self.text[i:end], end + 1
                if (line.lstrip("\t") if strip else line) == delimiter:
                    break
                self.substituting = self.substituting or (not literal and ("$(" in line or "`" in line))
        self.heredocs = []
        return min(i, len(self.text))

    def _end_word(self) -> None:
        if self.chars is None:
            return
        parts, expands = self.chars, self.expands
        text = "".join(c for _, c in parts)
        if self.tilde and (text == "~" or text.startswith("~/")):  # ~ expands to $HOME
            parts = [("HOME", "~"), ("", parts[0][1][1:]), *parts[1:]]
        else:
            expands = expands or self.tilde  # ~user
        pattern = self.globbing or (self.braced and bool(_BRACES.search(text)))
        word = Word(text, self.quoted, expands, pattern, tuple(p for p in parts if p[0] or p[1]))
        self.chars, self.quoted, self.expands, self.globbing, self.braced = None, False, False, False, False
        if self.pending:
            self._target(word)
        elif not self.command.words and not word.quoted and word.text in KEYWORDS:
            raise UnfollowedError
        else:
            self.command.words.append(word)

    def _target(self, word: Word) -> None:
        op, self.pending = self.pending, ""
        self.command.reads = self.command.reads or op.startswith("<")
        if op in {"<<", "<<-"}:  # the delimiter: quote removal only
            self.heredocs.append((word.text, op == "<<-", word.quoted))
        elif op in WRITES and not (op == ">&" and (word.text.isdigit() or word.text == "-")):
            self.command.redirects.append(Redirect(op, word))

    def _end_command(self, op: str) -> None:
        self._end_word()
        if self.pending:
            raise UnfollowedError
        if self.command.words or self.command.redirects:
            self.command.before, self.command.after = self.before, op
            self.commands.append(self.command)
            self.command, self.before = Command(), op
        elif op not in {"\n", ""} or (not op and self.before in {"&&", "||", "|"}):  # an operator without a command
            raise UnfollowedError
