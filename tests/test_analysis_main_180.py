"""RED-phase tests for owlbear_orchestrator.analysis.__main__ (task #180).

Tests that __main__.py exists, is runnable via `python -m owlbear_orchestrator.analysis`,
and correctly delegates to _cli.main() with the right exit codes.

All tests fail on current HEAD: __main__.py does not exist yet.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.slow


class TestFromAC_MainEntrypoint:
    """AC: `python -m owlbear_orchestrator.analysis` executes __main__.py which calls _cli.main()."""

    def test_main_module_exists(self) -> None:
        """AC: __main__.py must exist at owlbear_orchestrator.analysis.__main__."""
        spec = importlib.util.find_spec("owlbear_orchestrator.analysis.__main__")
        assert spec is not None, "__main__.py not found in owlbear_orchestrator.analysis package"

    def test_module_run_exit_0_on_success(self, tmp_path: Path) -> None:
        """AC: exit code 0 on success; empty audit dir returns no proposals."""
        result = subprocess.run(
            [sys.executable, "-m", "owlbear_orchestrator.analysis", "--audit-dir", str(tmp_path)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Expected exit 0, got {result.returncode}. stderr={result.stderr!r}"

    def test_module_run_no_proposals_json(self, tmp_path: Path) -> None:
        """AC: no proposals with json format prints []; __main__ delegates to _cli.main()."""
        result = subprocess.run(
            [sys.executable, "-m", "owlbear_orchestrator.analysis", "--audit-dir", str(tmp_path)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Expected exit 0, got {result.returncode}"
        assert result.stdout.strip() == "[]", f"Expected '[]' on stdout, got: {result.stdout!r}"

    def test_module_run_no_proposals_markdown(self, tmp_path: Path) -> None:
        """AC: no proposals with markdown format prints 'No analysis proposals.'"""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "owlbear_orchestrator.analysis",
                "--audit-dir",
                str(tmp_path),
                "--format",
                "markdown",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Expected exit 0, got {result.returncode}"
        assert result.stdout.strip() == "No analysis proposals.", (
            f"Expected 'No analysis proposals.', got: {result.stdout!r}"
        )

    def test_module_run_exit_1_on_error_with_stderr_message(self, tmp_path: Path) -> None:
        """AC: exit code 1 on error; error message written to stderr (not stdout).

        Triggers by placing an invalid JSONL file in the audit dir, causing analyze()
        to raise JSONDecodeError → _cli.main() catches it and returns 1.
        """
        (tmp_path / "bad.jsonl").write_text("not valid json\n")
        result = subprocess.run(
            [sys.executable, "-m", "owlbear_orchestrator.analysis", "--audit-dir", str(tmp_path)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1, f"Expected exit 1, got {result.returncode}"
        assert "Error:" in result.stderr, f"Expected 'Error:' in stderr, got: {result.stderr!r}"
        assert result.stdout == "", f"Expected empty stdout on error, got: {result.stdout!r}"

    def test_module_run_stdout_is_valid_json(self, tmp_path: Path) -> None:
        """AC: --format json (default) produces valid JSON array on stdout."""
        result = subprocess.run(
            [sys.executable, "-m", "owlbear_orchestrator.analysis", "--audit-dir", str(tmp_path)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Expected exit 0, got {result.returncode}"
        parsed = json.loads(result.stdout.strip())
        assert isinstance(parsed, list), f"Expected JSON list, got {type(parsed)}"
