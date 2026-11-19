"""Directive identities bind an exception to its file, rules and covered code, not its line number."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

from owlbear_quality import trees
from owlbear_quality.comments import comments as source_comments
from owlbear_quality.directives import SUPPRESSIONS, TERMINATORS

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path


@dataclass(frozen=True)
class Directive:
    """One copy of a directive and the exact code its identity covers."""

    path: str
    line: int
    directive: str
    code: str
    identity: str


@dataclass(frozen=True)
class Addition:
    """Copies of an identity in head beyond the count in base, with all candidate places in head."""

    identity: str
    count: int
    places: tuple[Directive, ...]


def _statement(number: int, statements: list[tuple[int, int]], *, following: bool = False) -> tuple[int, int] | None:
    return next(((a, b) for a, b in statements if a <= number <= b or (following and a >= number)), None)


def _terminator(token: str) -> str:
    if token.startswith("fmt:"):
        return r"fmt:\s*on"
    if token.startswith("biome-ignore-start"):
        return r"biome-ignore-end"
    if token.startswith("eslint-disable"):
        return r"eslint-enable"
    if token.startswith("yamllint"):
        return r"yamllint\s+enable"
    for family in ("markdownlint", "editorconfig-checker"):
        if token.startswith(family):
            return rf"{family}-enable"
    return ""


def _kind(token: str, number: int, lines: list[str], statements: list[tuple[int, int]]) -> str:
    if (
        "-file" in token
        or "-all" in token
        or "@ts-nocheck" in token
        or re.match(r"(?:ruff|flake8)\s*:", token)
        or (
            token.startswith("type:")
            and lines[number - 1].lstrip().startswith("#")
            and not any(a < number for a, _ in statements)
        )
    ):
        return "file"
    if (
        "next-line" in token
        or token.startswith(("@ts-ignore", "@ts-expect-error"))
        or (token.startswith("biome-ignore") and not token.startswith(("biome-ignore-start", "biome-ignore-all")))
    ):
        return "next"
    if token.startswith("yamllint") and "-line" in token:
        return "next" if lines[number - 1].lstrip().startswith("#") else "line"
    if "-line" in token or "skip" in token or "noqa" in token or token.startswith(("type:", "pyright:")):
        return "line"
    if _terminator(token):
        return "block"
    return "file"


def _rules(token: str) -> set[str]:
    family = re.match(
        r"(?:eslint|markdownlint)-(?:disable|enable)|yamllint\s+(?:disable|enable)"
        r"|biome-ignore-(?:start|end)",
        token,
    )
    return set(re.split(r"[,\s]+", token[family.end() :].strip())) - {""} if family else set()


def _block_end(token: str, number: int, comments: dict[int, str], length: int) -> int:
    pending = _rules(token)
    for line, text in comments.items():
        if line <= number:
            continue
        for match in TERMINATORS.finditer(text):
            if not re.match(_terminator(token), match[0]):
                continue
            enabled = _rules(match[0])
            if not enabled:
                return line
            if pending:
                pending -= enabled
                if not pending:
                    return line
    return length + 1


def _covered(
    token: str,
    number: int,
    lines: list[str],
    comments: dict[int, str],
    statements: list[tuple[int, int]],
) -> str:
    kind = _kind(token, number, lines, statements)
    if kind == "file":
        return "".join(lines)
    if kind == "block":
        end = _block_end(token, number, comments, len(lines))
        return "".join(lines[number - 1 : end - 1])
    at = number + (kind == "next")
    span = _statement(at, statements, following=kind == "next")
    if span:
        return "".join(lines[span[0] - 1 : span[1]])
    if token.startswith(("editorconfig-checker", "yamllint", "markdownlint")):
        return "".join(lines[at - 1 : at])
    return "".join(lines)


def directives(path: str, source: str) -> list[Directive]:
    """Inventory one source text; Python directives must be comment tokens."""
    if "\0" in source or not SUPPRESSIONS.search(source):
        return []
    comments, statements = source_comments(path, source)
    lines = source.splitlines(keepends=True)
    found = []
    for number, comment in comments.items():
        for match in SUPPRESSIONS.finditer(comment):
            token = match[0].strip()
            if number != 1 and token.startswith(("yamllint disable-file", "editorconfig-checker-disable-file")):
                continue
            code = _covered(token, number, lines, comments, statements)
            content = json.dumps([path, token, code], ensure_ascii=False)
            identity = hashlib.sha256(content.encode()).hexdigest()
            found.append(Directive(path, number, token, code, identity))
    return found


def inventory(root: Path, paths: Iterable[str]) -> list[Directive]:
    """Every directive in the given regular files of a working tree."""
    return [
        d
        for path in paths
        if (root / path).is_file() and not (root / path).is_symlink()
        for d in directives(path, (root / path).read_bytes().decode("utf-8", errors="replace"))
    ]


def _at(run: trees.Git, repo: Path, tree: dict[str, str], paths: set[str]) -> list[Directive]:
    return [d for path, oid in tree.items() if path in paths for d in directives(path, trees.blob(run, repo, oid))]


def added(run: trees.Git, repo: Path, base: str, head: str) -> list[Addition]:
    """Count new copies from immutable commits, reporting the head's places, never reading the index."""
    old, new = trees.files(run, repo, base), trees.files(run, repo, head)
    paths = {path for path in old.keys() | new.keys() if old.get(path) != new.get(path)}
    before = Counter(d.identity for d in _at(run, repo, old, paths))
    after = defaultdict(list)
    for directive in _at(run, repo, new, paths):
        after[directive.identity].append(directive)
    return [
        Addition(key, len(places) - before[key], tuple(places))
        for key, places in after.items()
        if len(places) > before[key]
    ]
