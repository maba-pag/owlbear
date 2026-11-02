"""One shell word as the guard reads it, and the quote and expansion ends the lexer finds in shell text."""

from __future__ import annotations

import re
from typing import Self

_GLOB = re.compile(r"[*?]|\[.*\]|\{[^}]*(?:,|\.\.)[^}]*\}")  # *, ?, [...], {a,b} and {1..3}


class Word(str):  # noqa: SLOT000 - a str subclass can hold attributes only in a __dict__
    """One shell word after quote removal, and what the shell does to it before running it."""

    expanded: bool  # it holds an expansion the shell fills in at run time: $x, ${x}, $(...), `...`
    tilde: bool  # it starts with an unquoted ~, which the shell turns into the home folder
    pattern: bool  # it holds an unquoted glob or brace the shell expands into file names or several words

    def __new__(cls, value: str = "", *, expanded: bool = False, tilde: bool = False, pattern: bool = False) -> Self:
        """A word with *value* as its text."""
        word = super().__new__(cls, value)
        word.expanded, word.tilde, word.pattern = expanded, tilde, pattern
        return word


def globbed(plain: str) -> bool:
    """Whether a word's unquoted text, its quoted and escaped characters blanked out, holds a glob or a brace."""
    return _GLOB.search(plain) is not None


def continued(line: str) -> bool:
    """Whether a line ends in an unescaped backslash, which joins it to the next."""
    return (len(line) - len(line.rstrip("\\"))) % 2 == 1


def arithmetic_end(text: str, i: int) -> int | None:
    """The index after the )) closing the $(( before *i*, or None: then it is $( ( ... ) ...), as bash reads it."""
    depth = 0
    while i < len(text):
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            if depth == 0:
                return i + 2 if text.startswith("))", i) else None
            depth -= 1
        i += 1
    return None


def single_end(text: str, i: int) -> int:
    """The index after the '...' or $'...' at *i*."""
    if text[i] == "$":
        return ansi_c_end(text, i + 2)
    if (end := text.find("'", i + 1)) < 0:
        raise ValueError
    return end + 1


def ansi_c_end(text: str, i: int) -> int:
    """The index after the quote closing the $'...' whose text starts at *i*; a backslash escapes the next character.

    Raises:
        ValueError: It is not closed.
    """
    while i < len(text) and text[i] != "'":
        i += 2 if text[i] == "\\" else 1
    if i >= len(text):
        raise ValueError
    return i + 1
