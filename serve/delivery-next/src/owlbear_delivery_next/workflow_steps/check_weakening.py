"""Whether an agent's edit weakens a check or touches configuration reserved for the owner.

Shared by the design-pack CI repair (``impeccable_runs.pack_repair_edits``) and a stuck step's repair (#1066). The
weakening patterns (a deleted test, an added skip or early return, a removed assertion or test) are a quick filter,
not a proof. New suppressions and configuration (lint, format, CI workflow, hook or security) need the owner.
"""

from __future__ import annotations

import ast
import re
from collections import Counter
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable
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
    r"|\bbiome-ignore(?:-all|-start|-end)?(?:\s+[\w/()*-]+)*"
    r"|\beslint-disable(?:-next-line|-line)?(?:\s+[\w@/-]+(?:\s*,\s*[\w@/-]+)*)?"
    r"|@ts-(?:ignore|nocheck|expect-error)"
)
REMOVED = re.compile(r"\bassert|\bexpect\(|\bdef test|^\s*(it|test|describe)(\.\w+)?\(")  # a check it took out
DISABLING = re.compile(  # an added line that turns a test off without a suppression's words
    r"\b(it|test|describe)\.(skip|todo|only)\b|\bx(it|test|describe)\(|SkipTest|importorskip|__test__\s*=\s*False"
)
RETURN = re.compile(r"^\s*return\b")
BLOCK = re.compile(r"^\s*(async\s+)?def\s|\bfunction\b|=>|^\s*(it|test)(\.\w+)?\(")  # a function's first line
TEST = re.compile(r"^\s*(async\s+)?def\s+test|^\s*(it|test)(\.\w+)?\(")  # a test's first line
HUNK = re.compile(r"^@@ -\S+ \+(\d+)")
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


def weakened(run: Git, at: Path, head: str, path: str, how: str) -> tuple[str, str]:
    """How the staged edit of *path* (``how``: its new mode and status) weakens a check, and how it edits a test.

    The first is never applied; the second, an edit of an existing test that weakens nothing visible, is for review.
    Both are empty for any other edit.
    """
    if how.endswith("D"):
        return ("deleted test" if TESTS.search(path) else ""), ""
    lines = run(at, ["diff", "--cached", "--unified=0", head, "--", path]).splitlines()
    added = [x[1:] for x in lines if x.startswith("+") and not x.startswith("+++")]
    edited = how.endswith(("M", "T")) and bool(TESTS.search(path))  # an existing test file, its type changed too
    removed = [x[1:] for x in lines if x.startswith("-") and not x.startswith("---")] if edited else []
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
    """New directives, with their exact source lines; a kept directive on the corresponding old line is not new."""
    lines = run(at, ["diff", "--cached", "--unified=0", head, "--", path]).splitlines()
    removed: list[str] = []
    added: list[tuple[int, str]] = []
    found: list[str] = []

    def finish() -> None:
        for i, (number, text) in enumerate(added):
            old = _directives(removed[i]) if i < len(removed) else Counter()
            if _directives(text) - old:
                found.append(f"{path}:{number}: {text}")
        removed.clear()
        added.clear()

    number = 0
    for line in lines:
        if match := HUNK.match(line):
            finish()
            number = int(match[1])
        elif line.startswith("-") and not line.startswith("---"):
            removed.append(line[1:])
        elif line.startswith("+") and not line.startswith("+++"):
            added.append((number, line[1:]))
            number += 1
        else:
            finish()
    finish()
    return found


def _directives(line: str) -> Counter[str]:
    return Counter(re.sub(r"\s+", "", m[0]) for m in SUPPRESSIONS.finditer(line))


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
    for x in diff:
        if found := HUNK.match(x):
            line = int(found[1])
        elif x.startswith("+") and not x.startswith("+++"):
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
