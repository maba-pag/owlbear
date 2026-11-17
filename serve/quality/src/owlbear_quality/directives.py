"""Diff-based suppression detection used by repairs, preserving their whole-line matching."""

from __future__ import annotations

import re
from collections import Counter
from difflib import SequenceMatcher
from itertools import zip_longest
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from pathlib import Path

    type Git = Callable[[Path, list[str]], str]

HUNK = re.compile(r"^@@ -(\d+)(?:,\d+)? \+(\d+)")

SUPPRESSIONS = re.compile(
    r"\b(?:(?:ruff|flake8)\s*:\s*)?noqa(?:\s*:\s*[A-Z]+\d+(?:\s*,\s*[A-Z]+\d+)*)?"
    r"|\b(?:type|pyright):\s*ignore(?:\s*\[[^\]]*\])?"
    r"|\bpragma:\s*no\s*cover|\bfmt:\s*(?:off|skip)"
    r"|\bbiome-ignore(?:-all|-start)?(?![\w-])(?:\s+[\w/()*-]+)*"
    r"|\beslint-disable(?:-next-line|-line)?(?:\s+[\w@/-]+(?:\s*,\s*[\w@/-]+)*)?"
    r"|\bzizmor:\s*ignore\[[^\]]*\]"
    r"|\byamllint\s+disable(?:-line|-file)?(?:[ \t]+rule:[\w-]+)*"
    r"|\bmarkdownlint-disable(?:-next-line|-line|-file)?(?:[ \t]+[\w-]+)*"
    r"|\beditorconfig-checker-disable(?:-next-line|-line|-file)?(?![\w-])"
    r"|@ts-(?:ignore|nocheck|expect-error)"
)
TERMINATORS = re.compile(
    r"\bfmt:\s*on|\bbiome-ignore-end(?:\s+[\w/()*-]+)*"
    r"|\byamllint\s+enable(?:[ \t]+rule:[\w-]+)*"
    r"|\bmarkdownlint-enable(?:[ \t]+[\w-]+)*|\beditorconfig-checker-enable\b"
    r"|\beslint-enable(?:\s+[\w@/-]+(?:\s*,\s*[\w@/-]+)*)?"
)
ESLINT_OPENER = re.compile(r"/\*\s*(eslint-(?:disable(?:-next-line|-line)?|enable))\b")
ESLINT_BLOCK = re.compile(ESLINT_OPENER.pattern + r"(.*?)\*/", re.DOTALL)


def _hunks(lines: list[str]) -> Iterator[str]:
    within = False
    for line in lines:
        if line.startswith("diff --git "):
            within = False
        elif HUNK.match(line):
            within = True
        if within:
            yield line


def suppressions(run: Git, at: Path, head: str, path: str) -> list[str]:
    """Added directives or removed terminators, with exact lines; corresponding unchanged directives stay exempt."""
    lines = run(at, ["diff", "--cached", "--unified=0", head, "--", path]).splitlines()
    regular = ("100644 ", "100755 ")
    if not run(at, ["ls-files", "--stage", "--", path]).startswith(regular) or not (hunks := list(_hunks(lines))):
        return []
    removed: list[tuple[int, str]] = []
    added: list[tuple[int, str]] = []
    found = _scope_changes(run, at, head, path, created=not run(at, ["ls-tree", head, "--", path]).startswith(regular))

    def finish() -> None:
        found.extend(_suppression_edits(path, removed, added))
        removed.clear()
        added.clear()

    number = old_number = 0
    for line in hunks:
        if match := HUNK.match(line):
            finish()
            old_number, number = int(match[1]), int(match[2])
        elif line.startswith("-"):
            removed.append((old_number, line[1:]))
            old_number += 1
        elif line.startswith("+"):
            added.append((number, line[1:]))
            number += 1
        elif not line.startswith("\\"):
            finish()
    finish()
    return list(dict.fromkeys(found))


def _scope_changes(run: Git, at: Path, head: str, path: str, *, created: bool) -> list[str]:
    before = "" if created else run(at, ["show", f"{head}:{path}"])
    after = run(at, ["show", f":{path}"])
    found = _block_edits(path, before, after)
    if path.endswith(".py") and not _leading_ignores(before):
        found.extend(f"{path}:{number}: {text}" for number, text in _leading_ignores(after))
    return found


def _leading_ignores(source: str) -> list[tuple[int, str]]:
    found = []
    for number, text in enumerate(source.removeprefix("\ufeff").splitlines(), 1):
        if not text.strip():
            continue
        if not text.lstrip().startswith("#"):
            break
        if re.match(r"\s*#\s*type:\s*ignore\b", text):
            found.append((number, text))
    return found


def _block_edits(path: str, before: str, after: str) -> list[str]:
    old, new = list(ESLINT_BLOCK.finditer(before)), list(ESLINT_BLOCK.finditer(after))
    matcher = SequenceMatcher(None, [m[0] for m in old], [m[0] for m in new], autojunk=False)
    positions = _source_positions(before, after) if old and new else {}
    found = []
    for _, start, end, new_start, new_end in matcher.get_opcodes():
        for left, right in zip_longest(old[start:end], new[new_start:new_end]):
            if right and _introduced(_block_text(left), _block_text(right)):
                found.extend(_block_evidence(path, after, right, ""))
            if left and _introduced(_block_text(right), _block_text(left), TERMINATORS):
                found.extend(_block_evidence(path, before, left, "removes a suppression terminator: "))
            if left and right and _block_moved(before, after, left, right, positions):
                found.extend(_block_evidence(path, after, right, "broadens suppression scope: "))
    return found


def _source_positions(before: str, after: str) -> dict[int, int]:
    old, new = [
        [(number, text.strip()) for number, text in enumerate(_block_source(source)) if text.strip()]
        for source in (before, after)
    ]
    matcher = SequenceMatcher(None, [text for _, text in old], [text for _, text in new], autojunk=False)
    positions = {}
    for _, start, end, new_start, new_end in matcher.get_opcodes():
        for (number, _), (new_number, _) in zip(old[start:end], new[new_start:new_end], strict=False):
            positions[number] = new_number
    return positions


def _block_source(source: str) -> list[str]:
    return ESLINT_BLOCK.sub(lambda match: "\n" * match[0].count("\n"), source).splitlines()


def _block_moved(before: str, after: str, left: re.Match[str], right: re.Match[str], positions: dict[int, int]) -> bool:
    if left[1] != right[1]:
        return False
    old, new = before.count("\n", 0, left.start()), after.count("\n", 0, right.start())
    if left[1] == "eslint-disable":
        return any(number < old and current >= new for number, current in positions.items())
    if left[1] == "eslint-enable":
        return any(number >= old and current < new for number, current in positions.items())
    if left[1] == "eslint-disable-next-line":
        old, new = old + left[0].count("\n") + 1, new + right[0].count("\n") + 1
    lines = _block_source(after)
    return new < len(lines) and bool(lines[new].strip()) and positions.get(old) != new


def _block_text(match: re.Match[str] | None) -> str:
    if match is None:
        return ""
    rules = re.sub(r"(?m)^[ \t]*\*[ \t]?", "", match[2])
    rules = re.split(r"\s--(?:\s|$)", rules, maxsplit=1)[0]
    rules = re.sub(r"\s+", " ", rules).strip()
    return f"{match[1]} {rules}"


def _block_evidence(path: str, source: str, match: re.Match[str], reason: str) -> list[str]:
    first = source.count("\n", 0, match.start())
    lines = source.splitlines()[first : first + match[0].count("\n") + 1]
    return [f"{path}:{number}: {reason}{text}" for number, text in enumerate(lines, first + 1)]


def _suppression_edits(path: str, removed: list[tuple[int, str]], added: list[tuple[int, str]]) -> list[str]:
    found = []
    before = [_source(text) for _, text in removed]
    after = [_source(text) for _, text in added]
    for _, start, end, new_start, new_end in SequenceMatcher(None, before, after, autojunk=False).get_opcodes():
        pairs = zip_longest(removed[start:end], added[new_start:new_end], fillvalue=(0, ""))
        for (old_number, old), (number, text) in pairs:
            before_line, after_line = ESLINT_OPENER.sub("", old), ESLINT_OPENER.sub("", text)
            if _introduced(before_line, after_line):
                found.append(f"{path}:{number}: {text}")
            if _introduced(after_line, before_line, TERMINATORS):
                found.append(f"{path}:{old_number}: removes a suppression terminator: {old}")
    return found


def _source(line: str) -> str:
    if match := SUPPRESSIONS.search(line):
        return re.sub(r"\s*(?:#|//|/\*)\s*$", "", line[: match.start()]).strip()
    return line.strip()


def _introduced(before: str, after: str, pattern: re.Pattern[str] = SUPPRESSIONS) -> bool:
    old = _directives(before, pattern)
    return any(token.rpartition(":")[0] not in old for token in _directives(after, pattern) - old)


def _directives(line: str, pattern: re.Pattern[str] = SUPPRESSIONS) -> Counter[str]:
    found = []
    for match in pattern.finditer(line):
        found.extend(_directive_rules(re.sub(r"\s+", "", match[0])))
    return Counter(found)


def _directive_rules(token: str) -> list[str]:
    if token.startswith(("type:ignore[", "pyright:ignore[")):
        token = token.replace("[", ":", 1).removesuffix("]")
    if "noqa:" in token or token.startswith(("type:ignore:", "pyright:ignore:")):
        family, _, rules = token.rpartition(":")
        return [f"{family}:{rule}" for rule in rules.split(",")]
    if match := re.match(r"eslint-(?:disable(?:-next-line|-line)?|enable)", token):
        family, rules = match[0], token[match.end() :]
        return [f"{family}:{rule}" for rule in rules.split(",")] if rules else [token]
    return [token]
