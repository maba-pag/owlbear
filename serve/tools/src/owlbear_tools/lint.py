"""Lint shortcuts — thin wrappers around pre-commit.

Commands
--------
uv run lint        Staged files, default hooks (= git commit).
uv run lint-all    All files, default hooks.
uv run megalint    lint-all + MegaLinter (Docker) + TypeScript check — full CI parity.
uv run eslint-fix  ESLint --fix on Cockpit frontend (serve/cockpit/web).

Default hooks (lint / lint-all)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Hook                       Auto-fix  Tool
─────────────────────────  ────────  ────
trailing-whitespace        yes       pre-commit-hooks
end-of-file-fixer          yes       pre-commit-hooks
check-yaml                 no        pre-commit-hooks
check-merge-conflict       no        pre-commit-hooks
check-added-large-files    no        pre-commit-hooks
ruff (lint)                yes       ruff
ruff-format                yes       ruff
yamllint                   no        yamllint
shellcheck                 no        shellcheck
actionlint                 no        actionlint
markdownlint-cli2          yes       markdownlint-cli2 --fix
editorconfig-checker       no        editorconfig-checker
eslint (Cockpit frontend)  no        eslint  (use eslint-fix for --fix)
validate-skills            no        custom (.owlbear/scripts)
validate-agents            no        custom (.owlbear/scripts)

Manual-stage hooks (megalint)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Hook                       Auto-fix  Tool
─────────────────────────  ────────  ────
megalinter                 no        MegaLinter v9.5 Docker (cupcake)
typecheck-frontend         no        TypeScript check (tsc --noEmit, whole-project)
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

LINT_HINT = (
    "\n"
    "\033[1;34m\u2139 Lint commands:\033[0m\n"
    "  \033[32muv run lint\033[0m        all linters, auto-fix: ruff + markdownlint, staged files only\n"
    "  \033[32muv run lint-all\033[0m    same as \033[32mlint\033[0m, all files\n"
    "  \033[32muv run megalint\033[0m    same as \033[32mlint-all\033[0m + MegaLinter + TypeScript\n"
    "  \033[32muv run eslint-fix\033[0m  ESLint --fix for frontend files\n"
)

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
    _run(["run", "--all-files"], hint=LINT_HINT)


def megalint() -> None:
    """All manual-stage hooks (MegaLinter + typecheck) — full CI parity."""
    _run(["run", "--all-files", "--hook-stage", "manual"], hint=LINT_HINT)


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
