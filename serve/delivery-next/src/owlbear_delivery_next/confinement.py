"""The worker path policy: which paths a command reaches, and whether they stay inside the worktree (D4 §3.6)."""

from __future__ import annotations

import re
import shlex
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

DIR_OPTIONS = frozenset({"-C", "--prefix", "--cwd", "--dir", "--git-dir", "--work-tree"})
TEXT_OPTIONS = frozenset({"-e", "-F", "-m", "--regexp", "--message"})  # values are patterns or messages
PATTERN_FIRST = frozenset({"grep", "egrep", "fgrep", "rg", "sed", "awk"})  # first operand is a pattern or script
NULL_PATHS = frozenset({"/dev/null"})
_REDIRECT = re.compile(r"^\d*[<>]+&?")


def resolve(base: Path, path: str) -> Path:
    """Return path resolved against base, expanding the home directory."""
    p = Path(path).expanduser()
    return (p if p.is_absolute() else base / p).resolve()


def inside(root: Path, path: str, base: Path | None = None) -> bool:
    """Return whether path, resolved against base (default root), stays inside root."""
    try:
        return resolve(base or root, path).is_relative_to(root.resolve())
    except OSError, ValueError, RuntimeError:
        return False


def _texts(words: Sequence[str]) -> set[int]:
    """Indexes of arguments read as text, not paths: pattern and message values, a pattern operand, comments."""
    found: set[int] = set()
    operand = bool(words) and Path(words[0]).name in PATTERN_FIRST
    for i, word in enumerate(words[1:], 1):
        flag, eq, _ = word.partition("=")
        if i in found:
            continue
        if flag in TEXT_OPTIONS or re.fullmatch(r"-[a-zA-Z]*[eFm]", word):
            found.add(i if eq else i + 1)
            operand = False
        elif operand and not word.startswith("-"):
            found.add(i)
            operand = False
        elif word.startswith(("//", "/*")) and any(c.isspace() for c in word):  # a quoted comment
            found.add(i)
    return found


def outside(root: Path, base: Path, words: Sequence[str], *, mutating: bool) -> str | None:
    """Return a ``cd`` target, directory option or mutating path argument that lies outside the worktree."""
    if words[:1] == ["cd"]:
        return None if inside(root, target := (words[1:] or ["~"])[0], base) else target
    texts = _texts(words)
    for i, word in enumerate(words[1:], 1):
        flag, eq, value = word.partition("=")
        if flag in DIR_OPTIONS:
            value = value if eq else (words[i + 1 : i + 2] or [""])[0]
        elif i in texts:
            continue
        elif mutating and re.match(r"[/~]|\.\.(/|$)|.*/\.\./", value := _REDIRECT.sub("", value if eq else word)):
            value = "" if value in NULL_PATHS else value
        else:
            continue
        if value and not inside(root, value, base):
            return value
    return None


def escape(root: Path, directory: Path, command: str) -> str | None:
    """The worker path policy for a host-run command: an unparsable command or the path it reaches outside *root*."""
    try:
        words = shlex.split(command)
    except ValueError:
        return command
    return outside(root.resolve(), directory, words, mutating=True)
