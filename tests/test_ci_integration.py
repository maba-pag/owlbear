"""Failing tests for task #44: scripts/validate_skills.py auto-discovery.

The pre-commit hook (``.pre-commit-config.yaml``) invokes::

    python scripts/validate_skills.py

with no positional arguments (``pass_filenames: false``, no ``args:`` field).

Currently ``main()`` returns exit 1 with a usage message when no args are given.
The script must instead auto-discover and validate all ``share/skills/*/SKILL.md``
directories, exiting 0 when all pass (AC2(a) + AC4).

AC items ALREADY satisfied (codebase + test_validate_skills.py):
  - AC1:  skills-ref==0.1.1 in pyproject.toml dev deps
  - AC2(b-e): filter logic, stderr output, exit codes with explicit paths
  - AC3:  .pre-commit-config.yaml has repo: local / validate-skills hook

Gap covered by THIS file:
  - AC2(a): script discovers share/skills/* when called with no arguments
  - AC4: running with no args (as pre-commit does) exits 0 for a clean project
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parent.parent
_SCRIPT = _PROJECT_ROOT / "scripts" / "validate_skills.py"
_SKILLS_DIR = _PROJECT_ROOT / "share" / "skills"


class TestFromAC_ScriptAutoDiscovery:
    """AC2(a)+AC4: script discovers share/skills/* and exits 0 when invoked with no args.

    The pre-commit hook ``entry: python scripts/validate_skills.py`` with
    ``pass_filenames: false`` calls the script with zero positional arguments.
    Currently the script exits 1 (usage error); it must auto-discover skills instead.
    """

    def test_no_args_exits_zero_when_all_skills_valid(self) -> None:
        """AC4: script exits 0 with no args from project root (all share/skills/* pass)."""
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


class TestFromAC_ScriptRelativePath:
    """AC2(a): auto-discovery uses script-relative path, NOT CWD-based.

    Path(__file__).parent.parent / 'skills' must be used so the script works
    when invoked from any working directory (e.g. from a pre-commit hook run
    inside a sub-directory or temp directory).
    """

    def test_no_args_succeeds_from_non_project_root_cwd(self, tmp_path: Path) -> None:
        """AC2(a): script exits 0 when called with no args from an arbitrary CWD.

        If path resolution were CWD-based, running from tmp_path (no skills/ there)
        would either fail to find skills or find nothing. Script-relative resolution
        always finds the project's skills/ regardless of CWD.
        """
        result = subprocess.run(
            [sys.executable, str(_SCRIPT)],
            capture_output=True,
            cwd=str(tmp_path),
        )
        assert result.returncode == 0, (
            f"Script failed when invoked from non-project CWD {tmp_path}.\n"
            f"If this fails it means path resolution is CWD-based, not script-relative.\n"
            f"stderr: {result.stderr.decode(errors='replace')}"
        )
