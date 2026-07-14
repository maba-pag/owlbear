"""Lint shortcuts — thin wrappers around pre-commit.

Commands
--------
uv run lint [FILE ...]
                   Explicit files, or staged files when omitted.
uv run lint-all    All files, default hooks.
uv run megalint    lint-all + MegaLinter (Docker) + TypeScript check — full CI parity.
uv run eslint-fix  ESLint --fix on Cockpit frontend (serve/cockpit/web).
uv run todo        Scan for ``> **TODO:**`` markers (warning only).

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

import os
import re
import subprocess
import sys
from pathlib import Path

LINT_HINT = (
    "\n"
    "\033[1;34m\u2139 Dev commands:\033[0m\n"
    "  \033[32muv run lint [FILE ...]\033[0m  explicit files, or staged files when omitted\n"
    "  \033[32muv run lint-all\033[0m         same as \033[32mlint\033[0m, all files\n"
    "  \033[32muv run megalint\033[0m         same as \033[32mlint-all\033[0m + MegaLinter + TypeScript\n"
    "  \033[32muv run eslint-fix\033[0m       ESLint --fix for frontend files\n"
    "  \033[32muv run todo\033[0m             scan for TODO markers (warning only)\n"
    "  \033[32muv run pytest\033[0m           Python tests (tests/ + serve/*/tests/)\n"
    "  \033[32mnpm test\033[0m                Cockpit frontend tests (run from serve/cockpit/web)\n"
)

COCKPIT_WEB = "serve/cockpit/web"


def _run(args: list[str], *, hint: str = "") -> None:
    rc = subprocess.call(["pre-commit", *args])  # noqa: S603, S607
    if hint:
        sys.stderr.write(hint + "\n")
    raise SystemExit(rc)


def lint() -> None:
    """Run default hooks on explicit files, or staged files when omitted."""
    files = sys.argv[1:]
    args = ["run", "--files", *files] if files else ["run"]
    _run(args, hint=LINT_HINT)


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
    rc = subprocess.call(
        ["npx", "eslint", "src/", "--fix"],  # noqa: S607
        cwd=web_dir,
    )
    sys.stderr.write(LINT_HINT + "\n")
    raise SystemExit(rc)


# ── TODO marker scan ──────────────────────────────────────────

_TODO_RE = re.compile(r"^> \*\*TODO:\*\*", re.MULTILINE)
_SKIP_DIRS = frozenset(
    {
        ".git",
        "node_modules",
        ".venv",
        "dist",
        "__pycache__",
        "build",
        ".egg-info",
        "megalinter-reports",
        "test-results",
        "scratch",
    }
)


def todo_check() -> None:
    """Scan for ``> **TODO:**`` markers (warning only, exit 0)."""
    hits: list[str] = []
    _walk_todo(".", hits)
    if hits:
        print(  # noqa: T201
            f"\033[1;33m\u26a0 {len(hits)} TODO marker(s):\033[0m"
        )
        for h in hits:
            print(f"  {h}")  # noqa: T201
    else:
        print("\033[32m\u2713 No TODO markers found\033[0m")  # noqa: T201
    if not os.environ.get("PRE_COMMIT"):
        sys.stderr.write(LINT_HINT + "\n")


def _walk_todo(root: str, hits: list[str]) -> None:
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        for f in filenames:
            _scan_todo(str(Path(dirpath) / f), hits)


def _scan_todo(path: str, hits: list[str]) -> None:
    try:
        with Path(path).open(encoding="utf-8", errors="replace") as fh:
            for i, line in enumerate(fh, 1):
                if _TODO_RE.search(line):
                    hits.append(f"{path}:{i}: {line.rstrip()}")
    except OSError:
        pass
