"""Lint shortcuts — thin wrappers around pre-commit."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ESLINT_HINT = "\n\033[36m\u2139 Fixable ESLint issues? Run: uv run eslint-fix\033[0m"

COCKPIT_WEB = "serve/cockpit/web"


def _run(args: list[str], *, hint: str = "") -> None:
    rc = subprocess.call(["pre-commit", *args])  # noqa: S603, S607
    if hint:
        sys.stderr.write(hint + "\n")
    raise SystemExit(rc)


def lint() -> None:
    """Staged files, default hooks (same as git commit)."""
    _run(["run"])


def lint_all() -> None:
    """All files, default hooks."""
    _run(["run", "--all-files"], hint=ESLINT_HINT)


def megalint() -> None:
    """All manual-stage hooks (MegaLinter + typecheck) — full CI parity."""
    _run(["run", "--all-files", "--hook-stage", "manual"], hint=ESLINT_HINT)


def eslint_fix() -> None:
    """Run ESLint with --fix on Cockpit frontend sources."""
    web_dir = Path(COCKPIT_WEB)
    if not web_dir.is_dir():
        sys.stderr.write(f"Error: {COCKPIT_WEB} not found\n")
        raise SystemExit(1)
    raise SystemExit(
        subprocess.call(
            ["npx", "eslint", "src/", "--fix"],  # noqa: S607
            cwd=web_dir,
        )
    )
