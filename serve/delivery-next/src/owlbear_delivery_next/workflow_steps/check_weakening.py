"""Whether an agent's edit weakens a check or touches configuration reserved for the owner.

Shared by the design-pack CI repair (``impeccable_runs.pack_repair_edits``) and a stuck step's repair (#1066). The
weakening patterns (a deleted test, an added skip or early return, a removed assertion or test) are a quick filter,
not a proof. New suppressions and configuration (lint, format, CI workflow, hook or security) need the owner.
"""

from __future__ import annotations

import ast
import re
from collections import Counter
from difflib import SequenceMatcher
from itertools import takewhile, zip_longest
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from pathlib import Path

    type Git = Callable[[Path, list[str]], str]

CONFIG_PREFIXES = (".github/", ".vscode/", ".husky/", ".githooks/")
CONFIG_DIRS = frozenset({"hooks"})
CONFIG_FILES = frozenset({
    "pyproject.toml", "uv.lock", "conftest.py", "package.json", "package-lock.json", "biome.json", "biome.jsonc",
    ".pre-commit-config.yaml", "ruff.toml", ".ruff.toml", "pytest.ini", "tox.ini", "setup.cfg", ".coveragerc",
    ".editorconfig", ".gitattributes", ".gitignore", ".markdownlint-cli2.jsonc", ".yamllint.yml",
    "renovate.json", ".nvmrc", ".python-version", ".mcp.json", ".snyk", "CODEOWNERS", "SECURITY.md",
    "test_linter_formatter_policy.py",
})  # fmt: skip
WEAKENING = re.compile(r"pytest\.mark\.(skip|xfail)|pytest\.(skip|xfail)\(|unittest\.skip")
SUPPRESSIONS = re.compile(
    r"\b(?:(?:ruff|flake8)\s*:\s*)?noqa(?:\s*:\s*[A-Z]+\d+(?:\s*,\s*[A-Z]+\d+)*)?"
    r"|\b(?:type|pyright):\s*ignore(?:\s*\[[^\]]*\])?"
    r"|\bpragma:\s*no\s*cover|\bfmt:\s*(?:off|skip)"
    r"|\bbiome-ignore(?:-all|-start)?(?![\w-])(?:\s+[\w/()*-]+)*"
    r"|\beslint-disable(?:-next-line|-line)?(?:\s+[\w@/-]+(?:\s*,\s*[\w@/-]+)*)?"
    r"|@ts-(?:ignore|nocheck|expect-error)"
)
TERMINATORS = re.compile(
    r"\bfmt:\s*on|\bbiome-ignore-end(?:\s+[\w/()*-]+)*"
    r"|\beslint-enable(?:\s+[\w@/-]+(?:\s*,\s*[\w@/-]+)*)?"
)
ESLINT_OPENER = re.compile(r"/\*\s*(eslint-(?:disable(?:-next-line|-line)?|enable))\b")
ESLINT_BLOCK = re.compile(ESLINT_OPENER.pattern + r"(.*?)\*/", re.DOTALL)
REMOVED = re.compile(r"\bassert|\bexpect\(|\bdef test|^\s*(it|test|describe)(\.\w+)?\(")  # a check it took out
DISABLING = re.compile(  # an added line that turns a test off without a suppression's words
    r"\b(it|test|describe)\.(skip|todo|only)\b|\bx(it|test|describe)\(|SkipTest|importorskip|__test__\s*=\s*False"
)
RETURN = re.compile(r"^\s*return\b")
BLOCK = re.compile(r"^\s*(async\s+)?def\s|\bfunction\b|=>|^\s*(it|test)(\.\w+)?\(")  # a function's first line
TEST = re.compile(r"^\s*(async\s+)?def\s+test|^\s*(it|test)(\.\w+)?\(")  # a test's first line
HUNK = re.compile(r"^@@ -(\d+)(?:,\d+)? \+(\d+)")
LINKS = frozenset({"120000", "160000"})  # a symbolic link or a submodule: never pushed without the owner
LINTERS = re.compile(r"^\.(?:eslintrc|prettierrc|stylelintrc)|^(?:eslint|prettier|stylelint)\.config\.\w+$")
TESTS = re.compile(r"(^|/)(tests?/|test_[^/]*\.py$|[^/]*_test\.py$|[^/]*\.test\.[mc]?[jt]sx?$)")


def staged(run: Git, at: Path, head: str) -> list[tuple[str, str]]:
    """Everything the agent changed against *head*, staged: each repository path with its new mode and status."""
    run(at, ["reset", "--quiet", "--soft", head])  # whatever it may have committed is its change all the same
    run(at, ["add", "--all"])
    raw = run(at, ["diff", "--cached", "--raw", "--no-renames", "-z", head]).split("\0")
    changed = []
    for meta, path in zip(raw[0::2], raw[1::2], strict=False):
        fields = meta.lstrip(":").split()
        changed.append((path, f"{fields[1]} {fields[-1]}"))  # the new mode and the status letter
    return changed


def _hunks(lines: list[str]) -> Iterator[str]:
    within = False
    for line in lines:
        if line.startswith("diff --git "):
            within = False
        elif HUNK.match(line):
            within = True
        if within:
            yield line


def weakened(run: Git, at: Path, head: str, path: str, how: str) -> tuple[str, str]:
    """How the staged edit of *path* (``how``: its new mode and status) weakens a check, and how it edits a test.

    The first is never applied; the second, an edit of an existing test that weakens nothing visible, is for review.
    Both are empty for any other edit.
    """
    if how.endswith("D"):
        return ("deleted test" if TESTS.search(path) else ""), ""
    lines = run(at, ["diff", "--cached", "--unified=0", head, "--", path]).splitlines()
    added = [x[1:] for x in _hunks(lines) if x.startswith("+")]
    edited = how.endswith(("M", "T")) and bool(TESTS.search(path))  # an existing test file, its type changed too
    removed = [x[1:] for x in _hunks(lines) if x.startswith("-")] if edited else []
    cut = any(REMOVED.search(x) for x in removed)
    same = cut and _same_code(run, at, head, path)  # only reformatted: no check went
    if any(WEAKENING.search(x) for x in added):
        return "adds a skip or xfail", ""
    if edited and (any(DISABLING.search(x) for x in added) or _returns_early(at / path, lines)):
        return "disables a test", ""
    if cut and not same:
        return "removes an assertion or test", ""
    if edited:
        return "", "reformats" if same else "removes lines from" if removed else "changes"
    return "", ""


def suppressions(run: Git, at: Path, head: str, path: str) -> list[str]:
    """Added directives or removed terminators, with exact lines; corresponding unchanged directives stay exempt."""
    lines = run(at, ["diff", "--cached", "--unified=0", head, "--", path]).splitlines()
    headers = list(takewhile(lambda line: not HUNK.match(line), lines))
    if "+++ /dev/null" in headers or not (hunks := list(_hunks(lines))):
        return []
    removed: list[tuple[int, str]] = []
    added: list[tuple[int, str]] = []
    found = _scope_changes(run, at, head, path, created="--- /dev/null" in headers)

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
    if not run(at, ["ls-files", "--stage", "--", path]).startswith(("100644 ", "100755 ")):
        return []
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
    found = []
    for _, start, end, new_start, new_end in matcher.get_opcodes():
        for left, right in zip_longest(old[start:end], new[new_start:new_end]):
            if right and _introduced(_block_text(left), _block_text(right)):
                found.extend(_block_evidence(path, after, right, ""))
            if left and _introduced(_block_text(right), _block_text(left), TERMINATORS):
                found.extend(_block_evidence(path, before, left, "removes a suppression terminator: "))
    return found


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


def configured(path: str) -> bool:
    """Whether *path* is lint, format, CI workflow, hook or security configuration."""
    p = PurePosixPath(path)
    configs = p.name in CONFIG_FILES or bool(LINTERS.search(p.name))
    return path.startswith(CONFIG_PREFIXES) or configs or bool(CONFIG_DIRS & set(p.parts[:-1]))


def _same_code(run: Git, at: Path, head: str, path: str) -> bool:
    """Whether a Python test file's edit only reformats it: its syntax tree is unchanged, so no check went."""
    if not path.endswith(".py"):
        return False
    try:
        old, new = run(at, ["show", f"{head}:{path}"]), (at / path).read_text("utf-8")
        return ast.dump(ast.parse(old)) == ast.dump(ast.parse(new))
    except SyntaxError, ValueError, OSError:
        return False


def _returns_early(file: Path, diff: list[str]) -> bool:
    """Whether an added ``return`` line of the zero-context *diff* lies in a test function of the new *file*."""
    text = file.read_text("utf-8", errors="replace").splitlines()
    line = 0
    for x in _hunks(diff):
        if found := HUNK.match(x):
            line = int(found[2])
        elif x.startswith("+"):
            if RETURN.match(x[1:]) and _in_test(text, line - 1):
                return True
            line += 1
    return False


def _in_test(text: list[str], at: int) -> bool:
    """Whether line *at* of *text* lies in a test function: the first function around it, by indentation, is one."""
    indent = len(text[at]) - len(text[at].lstrip()) if 0 <= at < len(text) else 0
    for line in reversed(text[:at]):
        here = len(line) - len(line.lstrip())
        if not line.strip() or here >= indent:
            continue
        indent = here
        if BLOCK.search(line):
            return bool(TEST.search(line))
    return False
