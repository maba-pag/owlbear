"""Shell text as the permission guard reads it: each command's words, its standard input and where it sits.

The lexer splits shell text at unquoted operators and into subshells, substitutions and process substitutions, whose
commands it lists too. It reads here-documents and here-strings as a command's input, never as commands, and marks
the words a shell expands at run time. ``shell_programs`` finds the programs a command's words run.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Self

_REDIRECTION = re.compile(r"&?[<>]+[&|]?")
_OPENERS = frozenset(
    {"{", "case", "for", "function", "if", "select", "until", "while"}
)  # words that start a compound command
_CLOSERS = frozenset({"}", "done", "esac", "fi"})
_SPECIAL = frozenset("@*#?$!-0123456789")  # $@, $1, ...: parameters without a name
_BLANK = " \t\n;&|<>()"  # what ends a here-document's delimiter word
_BODY_ESCAPE = re.compile(r"\\([$`\\\n])")  # escapes an unquoted here-document's body loses


class Word(str):  # noqa: SLOT000 - a str subclass can hold attributes only in a __dict__
    """One shell word after quote removal, and what the shell does to it before running it."""

    expanded: bool  # it holds an expansion the shell fills in at run time: $x, ${x}, $(...), `...`
    tilde: bool  # it starts with an unquoted ~, which the shell turns into the home folder

    def __new__(cls, value: str = "", *, expanded: bool = False, tilde: bool = False) -> Self:
        """A word with *value* as its text."""
        word = super().__new__(cls, value)
        word.expanded, word.tilde = expanded, tilde
        return word


@dataclass
class Input:
    """One input redirection of a command: the descriptor it feeds and where from."""

    fd: int
    kind: str  # file (<), here (<<), string (<<<) or dup (<&), whose source the guard can't see
    word: Word


@dataclass
class Command:
    """One simple command of shell text, with what its standard input is and where it runs."""

    words: list[Word]
    raw: str  # its own text, redirections included and here-document bodies not
    inputs: list[Input] = field(default_factory=list)
    opaque_stdin: bool = False  # its input comes from a pipe, a process substitution or its group's redirection
    top_level: bool = True  # it runs in the text's own shell, surely: not in a subshell, substitution, compound
    # command, pipeline or background job, and not after && or ||

    def stdin(self) -> Input | None:
        """The redirection that is the command's standard input: the last one on descriptor 0, as in bash."""
        return next((i for i in reversed(self.inputs) if i.fd == 0), None)


@dataclass
class _Level:
    """The command being read at one nesting level of shell text."""

    depth: int
    opaque: bool  # its commands read input from outside the text: a pipe or an output process substitution
    arith: bool = False  # inside (( )): < and > are operators, never redirections
    words: list[Word] = field(default_factory=list)
    inputs: list[Input] = field(default_factory=list)
    word: str | None = None
    expanded: bool = False
    tilde: bool = False
    quote: str = ""
    redirect: tuple[int, str] | None = None  # the next word is a redirection's target: its descriptor and kind
    out: bool = False  # it redirects output, a write even with no words: `(...) > f`
    start: int | None = None
    piped: bool = False  # the next command reads the previous one's output
    conditional: bool = False  # the next commands run only as && or || decides

    def add(self, chars: str) -> None:
        self.word = (self.word or "") + chars

    def end_word(self) -> None:
        if self.word is None:
            return
        word = Word(self.word, expanded=self.expanded, tilde=self.tilde)
        if self.redirect is None:
            self.words.append(word)
        else:
            fd, kind = self.redirect
            if kind != "out":
                self.inputs.append(Input(fd, kind, word))
            self.redirect = None
        self.word, self.expanded, self.tilde = None, False, False

    def descriptor(self, default: int) -> int:
        """The descriptor written right before a redirection operator, which it consumes, else *default*."""
        if self.word is not None and self.word.isdigit():
            fd, self.word = int(self.word), None
            return fd
        self.end_word()
        return default


class _Lexer:
    """Splits shell text into its commands at unquoted operators and newlines, and into substitutions."""

    def __init__(self, text: str) -> None:
        self.text = text
        self.commands: list[Command] = []
        self.pending: list[tuple[Input, str, bool, bool]] = []  # here-documents whose body starts at the next line
        self.blocks: list[tuple[int, bool]] = []  # open compound commands: first command and whether input is opaque
        self.group: tuple[int, int] | None = None  # the commands of the subshell that just closed
        self.defined = False  # an empty () just closed: a function's body may follow

    def level(self, i: int, close: str = "", depth: int = 0, *, opaque: bool = False, arith: bool = False) -> int:
        """Read text[i:] up to the unquoted *close*, or to the end without one; return the index after it.

        Raises:
            ValueError: A quote, subshell or substitution is not closed.
        """
        s = _Level(depth, opaque, arith)
        while i < len(self.text) and (s.quote or self.text[i] != close):
            i = self._step(s, i)
        if s.quote or (close and i >= len(self.text)):
            raise ValueError
        self.close(s, i)
        return i + 1

    def close(self, s: _Level, i: int) -> bool:
        """End the command being read at index *i*, keeping it when it has words or input; return whether it did."""
        s.end_word()
        kept = bool(s.words or s.inputs or s.out)
        if kept:
            self._keep(s, i)
            s.piped = False
        s.words, s.inputs, s.redirect, s.start, s.out = [], [], None, None, False
        return kept

    def _keep(self, s: _Level, i: int) -> None:
        first = s.words[0] if s.words else ""
        body = first == "function" or (first == "{" and self.defined)  # its input is its caller's, unknown here
        opaque = s.opaque or s.piped or body or any(o for _, o in self.blocks)
        top = s.depth == 0 and not self.blocks and not s.piped and not s.conditional
        command = Command(s.words, self.text[s.start or 0 : i], s.inputs, opaque, top)
        if first in _CLOSERS and self.blocks:
            start, _ = self.blocks.pop()
            if command.stdin():  # `done < f`: the loop's commands read it
                self._opaque(start)
        elif not s.words and command.stdin() and self.group:  # `(sh) < f`
            self._opaque(*self.group)
        self.commands.append(command)
        self.group, self.defined = None, False
        if first in _OPENERS:
            self.blocks.append((len(self.commands) - 1, opaque))

    def _opaque(self, start: int, end: int | None = None) -> None:
        for command in self.commands[start:end]:
            command.opaque_stdin = True

    def _step(self, s: _Level, i: int) -> int:
        text, ch = self.text, self.text[i]
        if s.start is None and ch not in " \t\n":
            s.start = i
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
        if ch in {"$", "`"} and (end := self._expansion(s, i)) is not None:
            return end
        if s.quote:
            s.add(ch)
            return i + 1
        return self._unquoted(s, i)

    def _expansion(self, s: _Level, i: int) -> int | None:
        """Lex the expansion at *i* and return the index after it, or None for $name, only marked expanded.

        $((, $[, ${, $( and backquotes are lexed whole; $name's characters are added as usual.
        """
        text = self.text
        if text.startswith("$((", i):
            return self._arithmetic(s, i + 3) if self._arithmetic_closes(i + 3) else self._substitution(s, i)
        if text.startswith("$[", i):
            return self._arithmetic(s, i + 2, close="]")
        if text.startswith("${", i):
            return self._braced(s, i)
        if text[i] == "`" or text.startswith("$(", i):
            return self._substitution(s, i)
        nxt = text[i + 1 : i + 2]
        named = bool(nxt) and (nxt in "{_" or nxt.isalnum() or nxt in _SPECIAL)
        if named or (nxt and nxt in "'\"" and not s.quote):  # $'...' and $"...": decoded or translated by the shell
            s.expanded = True
        return None

    def _substitution(self, s: _Level, i: int) -> int:
        """A $(...) or backquoted substitution: its commands are checked on their own, with their command's input."""
        s.add("$")
        s.expanded = True
        opaque = s.opaque or s.piped or any(o for _, o in self.blocks)
        if self.text[i] == "`":
            return self.level(i + 1, "`", s.depth + 1, opaque=opaque)
        return self.level(i + 2, ")", s.depth + 1, opaque=opaque)

    def _arithmetic_closes(self, i: int) -> bool:
        """Whether the $(( before *i* closes with )) as arithmetic; else it is $( ( ... ) ...), as bash reads it."""
        depth = 0
        while i < len(self.text):
            ch = self.text[i]
            if ch == "(":
                depth += 1
            elif ch == ")":
                if depth == 0:
                    return self.text[i + 1 : i + 2] == ")"
                depth -= 1
            i += 1
        return False

    def _arithmetic(self, s: _Level, i: int, close: str = ")") -> int:
        """Skip an arithmetic expansion's operators, where < and > never redirect, but lex its substitutions."""
        s.add("$")
        s.expanded = True
        opener, depth = ("(", 2) if close == ")" else ("[", 1)
        while i < len(self.text):
            if self.text.startswith("$((", i):
                i = self._arithmetic(s, i + 3)
            elif self.text.startswith("$(", i) or self.text[i] == "`":
                i = self._substitution(s, i)
            else:
                depth += {opener: 1, close: -1}.get(self.text[i], 0)
                i += 1
                if depth == 0:
                    return i
        raise ValueError

    def _braced(self, s: _Level, i: int) -> int:
        """A ${...} expansion: < and > in it never redirect; its substitutions are lexed."""
        j = self._brace_end(s, i)
        s.add(self.text[i:j])
        s.expanded = True
        return j

    def _brace_end(self, s: _Level, i: int) -> int:
        """The index after the ${...} at *i*; each nested ${...} keeps its own quotes."""
        text, j, depth, quoted = self.text, i + 2, 1, False
        while j < len(text) and depth:
            if text[j] == "\\":
                j += 2
            elif text.startswith("$((", j) and self._arithmetic_closes(j + 3):
                j = self._arithmetic(_Level(s.depth, s.opaque, piped=s.piped), j + 3)
            elif text[j] == "'" and s.quote != '"' and not quoted:  # in "${x:-'...'}" a single quote is a character
                if (end := text.find("'", j + 1)) < 0:
                    raise ValueError
                j = end + 1
            elif text[j] == '"':  # a quote inside ${...}: a } in it doesn't close the expansion
                quoted, j = not quoted, j + 1
            elif text.startswith("$(", j) or text[j] == "`":
                j = self._substitution(_Level(s.depth, s.opaque, piped=s.piped), j)
            elif text.startswith("${", j):
                j = self._brace_end(s, j)
            else:
                depth, j = depth - (text[j] == "}" and not quoted), j + 1
        if depth or quoted:
            raise ValueError
        return j

    def _unquoted(self, s: _Level, i: int) -> int:  # noqa: C901, PLR0911 - one branch per shell operator
        text, ch = self.text, self.text[i]
        if ch in "'\"":
            s.quote = ch
            s.add("")
        elif ch == "#" and s.word is None:
            end = text.find("\n", i)
            return len(text) if end < 0 else end
        elif s.arith and ch in "<>":  # (( 1 << x )): an operator
            s.add(ch)
        elif text.startswith(("<(", ">("), i):
            return self._process(s, i)
        elif text.startswith("<<", i):
            return self._here(s, i)
        elif match := _REDIRECTION.match(text, i):
            op = match[0]
            fd = s.descriptor(0 if op.lstrip("&").startswith("<") else 1)
            dup = op == "<&" or (op == ">&" and fd == 0)  # 0>&3 feeds stdin from fd 3 too
            s.redirect = (fd, "dup" if dup else "file" if op in {"<", "<>"} else "out")
            s.out = s.out or s.redirect[1] == "out"
            return match.end()
        elif ch == "(":
            return self._subshell(s, i)
        elif ch == "|":
            return self._pipe(s, i)
        elif ch in ";&\n)":
            return self._separator(s, i)
        elif ch in " \t":
            s.end_word()
        else:
            if ch == "~" and s.word is None:
                s.tilde = True
            s.add(ch)
        return i + 1

    def _separator(self, s: _Level, i: int) -> int:
        """End a command at ;, &, &&, a newline or an unmatched ), reading here-document bodies after a newline."""
        kept = self.close(s, i)
        if self.text.startswith("&&", i):
            s.conditional = True
            return i + 2
        if kept and self.text[i] == "&":  # a background job runs in a subshell
            self.commands[-1].top_level = False
        s.conditional = False
        if self.text[i] == "\n" and self.pending:
            return self._bodies(i + 1)
        return i + 1

    def _pipe(self, s: _Level, i: int) -> int:
        kept = self.close(s, i)
        if self.text.startswith("||", i):
            s.conditional = True
            return i + 2
        if kept:  # each part of a pipeline runs in a subshell
            self.commands[-1].top_level = False
        s.piped = True
        return i + 2 if self.text.startswith("|&", i) else i + 1

    def _subshell(self, s: _Level, i: int) -> int:
        body = self.defined and not s.words  # f() (...): a function's body, whose input is its caller's
        opaque = s.opaque or s.piped or body or any(o for _, o in self.blocks)
        self.close(s, i)
        s.piped = False
        start = len(self.commands)
        arith = s.arith or self.text.startswith("((", i)  # an arithmetic command, also in for ((...))
        end = self.level(i + 1, ")", s.depth + 1, opaque=opaque, arith=arith)
        self.group = (start, len(self.commands))
        self.defined = start == len(self.commands)
        return end

    def _process(self, s: _Level, i: int) -> int:
        """A process substitution: its commands are lexed, and the word standing for it is built at run time."""
        inherited = s.opaque or s.piped or any(o for _, o in self.blocks)  # <(sh) reads its command's input
        end = self.level(i + 2, ")", s.depth + 1, opaque=inherited or self.text[i] == ">")  # >(sh) reads the output
        s.add("<(…)")
        s.expanded = True
        return end

    def _here(self, s: _Level, i: int) -> int:
        """A here-string's word, or a here-document whose body starts at the next unquoted newline."""
        fd = s.descriptor(0)
        if self.text.startswith("<<<", i):
            s.redirect = (fd, "string")
            return i + 3
        strip = self.text.startswith("<<-", i)
        end, delimiter, literal = self._delimiter(i + (3 if strip else 2))
        given = Input(fd, "here", Word())
        s.inputs.append(given)
        self.pending.append((given, delimiter, strip, literal))
        return end

    def _delimiter(self, i: int) -> tuple[int, str, bool]:
        """A here-document's delimiter word: its index after, its text, and whether any of it was quoted."""
        text = self.text
        while i < len(text) and text[i] in " \t":
            i += 1
        out, quote, literal = "", "", False
        while i < len(text) and (quote or text[i] not in _BLANK or text.startswith("\\\n", i)):
            ch = text[i]
            if ch == "\\" and text[i + 1 : i + 2] == "\n" and quote != "'":  # a line continuation
                i += 2
            elif quote:
                out, quote, i = self._quoted(out, quote, i)
            elif ch == "$" and text[i + 1 : i + 2] in {"'", '"'}:  # $'...' or $"...": not read
                raise ValueError
            elif ch in "'\"":
                quote, literal, i = ch, True, i + 1
            elif ch == "\\":
                out, literal, i = out + text[i + 1 : i + 2], True, i + 2
            else:
                out, i = out + ch, i + 1
        if quote or not (out or literal):
            raise ValueError
        return i, out, literal

    def _quoted(self, out: str, quote: str, i: int) -> tuple[str, str, int]:
        """One character of a quoted delimiter part: the text so far, the quote still open, and the next index."""
        ch, nxt = self.text[i], self.text[i + 1 : i + 2]
        if quote == '"' and ch == "\\" and nxt and nxt in '$`"\\\n':
            return out + nxt, quote, i + 2
        if ch == quote:
            return out, "", i + 1
        return out + ch, quote, i + 1

    def _bodies(self, i: int) -> int:
        """Read each pending here-document's body from index *i*; an unquoted body's substitutions are lexed."""
        pending, self.pending = self.pending, []
        for given, delimiter, strip, literal in pending:
            lines, start, end = [], i, len(self.text)
            while i < len(self.text):
                stop = self.text.find("\n", i)
                stop = len(self.text) if stop < 0 else stop
                while not literal and _continued(self.text[i:stop]) and stop < len(self.text):  # EO\ + F is EOF
                    nxt = self.text.find("\n", stop + 1)
                    stop = len(self.text) if nxt < 0 else nxt
                line = self.text[i:stop].replace("\\\n", "") if not literal else self.text[i:stop]
                line = line.lstrip("\t") if strip else line
                if line == delimiter:
                    end, i = i, stop + 1
                    break
                lines.append(line)
                i = stop + 1
            body = "".join(f"{line}\n" for line in lines)
            if not literal and "\\\n" in self.text[start:end]:  # its substitutions span joined lines: not read
                raise ValueError
            if not literal:  # the shell removes these backslashes before handing the body on
                body = _BODY_ESCAPE.sub(lambda m: m[1] if m[1] != "\n" else "", body)
            found = len(self.commands)
            owner = next((k for k, c in enumerate(self.commands) if any(i is given for i in c.inputs)), None)
            opaque = owner is not None and self.commands[owner].opaque_stdin
            given.word = Word(body, expanded=not literal and self._expansions(start, end, opaque=opaque))
            if owner is not None:  # the shell runs the body's substitutions before the command it feeds
                self.commands[owner:] = self.commands[found:] + self.commands[owner:found]
        return min(i, len(self.text))

    def _expansions(self, i: int, end: int, *, opaque: bool) -> bool:
        """Lex the substitutions in text[i:end] as commands; return whether it holds any expansion."""
        found, text = False, self.text
        while i < end:
            if text[i] == "\\":
                i += 2
            elif text.startswith("$(", i) or text[i] == "`":
                found, i = True, self._step(_Level(1, opaque=opaque), i)
            else:
                found = found or (text[i] == "$" and text[i + 1 : i + 2] not in ("", " ", "\n", "\t"))
                i += 1
        return found


def _continued(line: str) -> bool:
    """Whether a line ends in an unescaped backslash, which joins it to the next."""
    return (len(line) - len(line.rstrip("\\"))) % 2 == 1


def parse(text: str) -> list[Command]:
    """Each command in *text*, including those of subshells, substitutions and process substitutions.

    Raises:
        ValueError: The text cannot be parsed.
    """
    lexer = _Lexer(text)
    lexer.level(0)
    if lexer.pending:
        lexer._bodies(len(text))  # noqa: SLF001 - here-documents the text ends inside
    return lexer.commands
