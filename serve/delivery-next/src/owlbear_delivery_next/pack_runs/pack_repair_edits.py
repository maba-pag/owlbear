"""An agent's CI repair of the design pack pull request: what in its change stops for the owner (``pack_repair``).

Lint, format, CI workflow, hook or security configuration is held: the owner may push it. A weakened test (a deleted
test file, an added skip, suppression or early return, a removed assertion or test) and protected pack content only an
update may change are never pushed. Every other edit of an existing test file waits for the owner's review of its
diff: the patterns are a quick filter, no proof that a test still checks as much.
"""

from __future__ import annotations

import re
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, Any

from owlbear_delivery_next.pack_runs import pack_gates, pack_rounds
from owlbear_delivery_next.pack_runs.pack_repair_content import protected, updater_path

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear_delivery_next.design_packs import pack_git
    from owlbear_delivery_next.pack_runs.pack_repair import Repair

CONFIG_PREFIXES = (".github/", ".vscode/", ".husky/", ".githooks/")
CONFIG_DIRS = frozenset({"hooks"})
CONFIG_FILES = frozenset({
    "pyproject.toml", "uv.lock", "conftest.py", "package.json", "package-lock.json", "biome.json", "biome.jsonc",
    ".pre-commit-config.yaml", "ruff.toml", ".ruff.toml", "pytest.ini", "tox.ini", "setup.cfg", ".coveragerc",
    ".editorconfig", ".gitattributes", ".gitignore", ".markdownlint-cli2.jsonc", ".yamllint.yml", ".coderabbit.yaml",
    "renovate.json", ".nvmrc", ".python-version", ".mcp.json", ".snyk", "CODEOWNERS", "SECURITY.md",
    "test_linter_formatter_policy.py",
})  # fmt: skip
WEAKENING = re.compile(
    r"noqa|type:\s*ignore|pyright:\s*ignore|pragma:\s*no\s*cover|fmt:\s*(off|skip)|biome-ignore|eslint-disable"
    r"|@ts-(ignore|nocheck|expect-error)|pytest\.mark\.(skip|xfail)|pytest\.(skip|xfail)\(|unittest\.skip"
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
TESTS = re.compile(r"(^|/)(tests?/|test_[^/]*\.py$|[^/]*_test\.py$|[^/]*\.test\.[mc]?[jt]sx?$)")


def config(run: str, r: Repair) -> dict[str, Any]:
    """The owner's question about a held repair: a weakened check is never pushed, other holds he may let through."""
    made, said = r.commit[:12], f"The agent said: {r.summary}"
    config = f"; it also changes configuration: {', '.join(r.held[:10])}" if r.held else ""
    if r.refused:
        text = (f"The agent's CI repair {made} weakens a check or changes what only an update may: "
                f"{', '.join(r.refused[:10])}. Delivery pushed nothing and never pushes it. Try again without it, or "
                f"discard? {said}")  # fmt: skip
        options = [pack_rounds.RETRY, pack_rounds.DISCARD]
    elif r.reviewed:
        text = (f"The agent's CI repair {made} changes tests: {', '.join(r.reviewed[:10])}{config}. Delivery's "
                "pattern check found no known weakening, but cannot tell that the tests still check as much: review "
                f"its diff. Nothing was pushed. Push it, or discard? {said}")  # fmt: skip
        options = [pack_rounds.PUSH_REVIEWED, pack_rounds.DISCARD]
    else:
        text = (f"The agent's CI repair {made} changes {', '.join(r.held[:10])}: lint, format, CI workflow, hook or "
                f"security configuration. Delivery pushed nothing. Push it as it is, try again without it, or discard? "
                f"{said}")  # fmt: skip
        options = [pack_rounds.PUSH_CONFIG, pack_rounds.RETRY, pack_rounds.DISCARD]
    q = pack_rounds.question(f"{run}:repair-config:{made}", "repair-config", text, [], commit=r.commit,
                             paths=[*r.refused, *r.reviewed, *r.held], diff=r.diff)  # fmt: skip
    q["options"] = pack_rounds.published(options, opened=True)
    return q


def staged(run: pack_git.Git, at: Path, head: str) -> list[tuple[str, str]]:
    """Everything the agent changed against *head*, staged: each repository path with its new mode and status."""
    run(at, ["reset", "--quiet", "--soft", head])  # whatever it may have committed is its change all the same
    run(at, ["add", "--all"])
    raw = run(at, ["diff", "--cached", "--raw", "--no-renames", "-z", head]).split("\0")
    changed = []
    for meta, path in zip(raw[0::2], raw[1::2], strict=False):
        fields = meta.lstrip(":").split()
        changed.append((path, f"{fields[1]} {fields[-1]}"))  # the new mode and the status letter
    return changed


def held(  # noqa: PLR0913 - the copy, its head, the change, and the package with its pinned skills
    run: pack_git.Git, at: Path, head: str, changed: list[tuple[str, str]], *, package: str, skills: list[str]
) -> tuple[list[str], ...]:
    """What in the change stops for the owner: its configuration, what is never pushed and its other test edits.

    The weakening patterns (a deleted test, an added skip, suppression or early return, a removed assertion or test)
    are a quick filter, not a proof; every other edit of an existing test file is held for the owner's review.
    """
    held = [p for p, how in changed if _configured(p) or how.split()[0] in LINKS]
    refused = [f"{p} (deleted test)" for p, how in changed if how.endswith("D") and TESTS.search(p)]
    refused += [
        f"{p} (pack content only an update may change)"
        for p, how in changed
        if protected(package, p) and not pack_gates.allowed(updater_path(package, p), not how.endswith("D"), skills)
    ]
    reviewed = []
    for path, how in changed:
        if how.endswith("D"):
            continue
        lines = run(at, ["diff", "--cached", "--unified=0", head, "--", path]).splitlines()
        added = [x[1:] for x in lines if x.startswith("+") and not x.startswith("+++")]
        edited = how.endswith("M") and bool(TESTS.search(path))  # an existing test file: a new one may be pushed
        removed = [x[1:] for x in lines if x.startswith("-") and not x.startswith("---")] if edited else []
        if any(WEAKENING.search(x) for x in added):
            refused.append(f"{path} (adds a suppression or skip)")
        elif edited and (any(DISABLING.search(x) for x in added) or _returns_early(at / path, lines)):
            refused.append(f"{path} (disables a test)")
        elif any(REMOVED.search(x) for x in removed):
            refused.append(f"{path} (removes an assertion or test)")
        elif edited:
            reviewed.append(f"{path} ({'removes lines from' if removed else 'changes'} a test)")
    return held, refused, reviewed


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


def _configured(path: str) -> bool:
    """Whether *path* is lint, format, CI workflow, hook or security configuration."""
    p = PurePosixPath(path)
    return path.startswith(CONFIG_PREFIXES) or p.name in CONFIG_FILES or bool(CONFIG_DIRS & set(p.parts[:-1]))
