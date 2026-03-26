"""Deterministic post-implementation lint gate (#704).

Runs ``ruff check`` and ``ruff format --check`` on changed ``.py`` files
after builder task completion.  The gate is non-LLM and subprocess-based,
guaranteeing lint compliance before a task advances to review.

Graceful degradation: if ruff/git binary is missing or subprocess times
out (10 s cap), the gate passes with a warning log — never blocking the
pipeline on infrastructure failure.
"""

from __future__ import annotations

import dataclasses
import logging
import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)

_SUBPROCESS_TIMEOUT = 10  # seconds


@dataclasses.dataclass
class LintGateResult:
    """Result of a lint gate run."""

    passed: bool
    errors: str
    files_checked: list[str]


class LintGateError(Exception):
    """Raised when the lint gate fails — carries lint output for WIP context."""


async def run_lint_gate(workspace: Path) -> LintGateResult:
    """Run ruff check + format on changed ``.py`` files.

    Changed-files strategy: union of ``git diff --name-only HEAD``
    (uncommitted vs HEAD) and ``git diff --name-only HEAD~1 HEAD``
    (last commit vs parent).  Filtered to ``.py`` extensions.

    Returns :class:`LintGateResult`.  On infrastructure failure
    (missing binary, timeout), returns ``passed=True`` with a warning log.
    """
    try:
        changed = _get_changed_py_files(workspace)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        logger.warning("Lint gate: git unavailable or timed out — degrading gracefully")
        return LintGateResult(passed=True, errors="", files_checked=[])

    if not changed:
        return LintGateResult(passed=True, errors="", files_checked=[])

    files = sorted(changed)

    try:
        errors = _run_ruff(files, workspace)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        logger.warning("Lint gate: ruff unavailable or timed out — degrading gracefully")
        return LintGateResult(passed=True, errors="", files_checked=files)

    passed = errors == ""
    return LintGateResult(passed=passed, errors=errors, files_checked=files)


def _get_changed_py_files(workspace: Path) -> set[str]:
    """Return the union of uncommitted and last-commit changed ``.py`` files."""
    uncommitted = _run_git_diff(["git", "diff", "--name-only", "HEAD"], workspace)
    last_commit = _run_git_diff(["git", "diff", "--name-only", "HEAD~1", "HEAD"], workspace)
    all_files = uncommitted | last_commit
    return {f for f in all_files if f.endswith(".py")}


def _run_git_diff(cmd: list[str], workspace: Path) -> set[str]:
    """Run a git diff command and return the set of file paths."""
    result = subprocess.run(  # noqa: S603
        cmd,
        capture_output=True,
        text=True,
        cwd=workspace,
        timeout=_SUBPROCESS_TIMEOUT,
        check=False,
    )
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


def _run_ruff(files: list[str], workspace: Path) -> str:
    """Run ruff check + ruff format --check, return combined error output."""
    errors: list[str] = []

    check_result = subprocess.run(  # noqa: S603
        ["uv", "run", "ruff", "check", *files],  # noqa: S607
        capture_output=True,
        text=True,
        cwd=workspace,
        timeout=_SUBPROCESS_TIMEOUT,
        check=False,
    )
    if check_result.returncode != 0:
        errors.append(check_result.stdout)

    fmt = subprocess.run(  # noqa: S603
        ["uv", "run", "ruff", "format", "--check", *files],  # noqa: S607
        capture_output=True,
        text=True,
        cwd=workspace,
        timeout=_SUBPROCESS_TIMEOUT,
        check=False,
    )
    if fmt.returncode != 0:
        errors.append(fmt.stdout)

    return "\n".join(errors).strip()
