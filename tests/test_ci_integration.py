"""Failing tests for task #44: scripts/validate_skills.py auto-discovery.

The pre-commit hook (``.pre-commit-config.yaml``) invokes::

    python scripts/validate_skills.py

with no positional arguments (``pass_filenames: false``, no ``args:`` field).

Currently ``main()`` returns exit 1 with a usage message when no args are given.
The script must instead auto-discover and validate all ``.github/skills/*/SKILL.md``
directories, exiting 0 when all pass (AC2(a) + AC4).

AC items ALREADY satisfied (codebase + test_validate_skills.py):
  - AC1:  skills-ref==0.1.1 in pyproject.toml dev deps
  - AC2(b-e): filter logic, stderr output, exit codes with explicit paths
  - AC3:  .pre-commit-config.yaml has repo: local / validate-skills hook

Gap covered by THIS file:
  - AC2(a): script discovers .github/skills/* when called with no arguments
  - AC4: running with no args (as pre-commit does) exits 0 for a clean project
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parent.parent
_SCRIPT = _PROJECT_ROOT / "scripts" / "validate_skills.py"
_SKILLS_DIR = _PROJECT_ROOT / ".github" / "skills"


class TestFromAC_ScriptAutoDiscovery:
    """AC2(a)+AC4: script discovers .github/skills/* and exits 0 when invoked with no args.

    The pre-commit hook ``entry: python scripts/validate_skills.py`` with
    ``pass_filenames: false`` calls the script with zero positional arguments.
    Currently the script exits 1 (usage error); it must auto-discover skills instead.
    """

    def test_no_args_exits_zero_when_all_skills_valid(self) -> None:
        """AC4: script exits 0 with no args from project root (all .github/skills/* pass)."""
        result = subprocess.run(
            [sys.executable, str(_SCRIPT)],
            capture_output=True,
            cwd=str(_PROJECT_ROOT),
        )
        assert result.returncode == 0, (
            f"Script exited {result.returncode} with no args; expected 0 (auto-discover).\n"
            f"stderr: {result.stderr.decode(errors='replace')}"
        )

    def test_no_args_produces_no_stderr_output(self) -> None:
        """AC4: no validation errors means stderr is empty when script auto-discovers."""
        result = subprocess.run(
            [sys.executable, str(_SCRIPT)],
            capture_output=True,
            cwd=str(_PROJECT_ROOT),
        )
        stderr = result.stderr.decode(errors="replace").strip()
        assert not stderr, f"Unexpected stderr (expected empty for valid skills): {stderr!r}"

    def test_no_args_does_not_print_usage_message(self) -> None:
        """AC2(a): script must not emit a usage/help message when called with no args."""
        result = subprocess.run(
            [sys.executable, str(_SCRIPT)],
            capture_output=True,
            cwd=str(_PROJECT_ROOT),
        )
        stderr = result.stderr.decode(errors="replace")
        assert "usage" not in stderr.lower(), (
            f"Script printed usage error instead of auto-discovering skills:\n{stderr}"
        )

    def test_no_args_exit_code_matches_explicit_skill_dirs(self) -> None:
        """AC2(a): exit code with no args equals exit code when all 21 dirs passed explicitly."""
        skill_dirs = sorted(str(d) for d in _SKILLS_DIR.iterdir() if d.is_dir())
        explicit = subprocess.run(
            [sys.executable, str(_SCRIPT), *skill_dirs],
            capture_output=True,
            cwd=str(_PROJECT_ROOT),
        )
        auto = subprocess.run(
            [sys.executable, str(_SCRIPT)],
            capture_output=True,
            cwd=str(_PROJECT_ROOT),
        )
        assert auto.returncode == explicit.returncode, (
            f"Auto-discovery exit {auto.returncode} != "
            f"explicit-args exit {explicit.returncode}.\n"
            f"Auto stderr: {auto.stderr.decode(errors='replace')!r}"
        )
