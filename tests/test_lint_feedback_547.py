"""Tests for task #547: Add model-facing lint feedback via additionalContext.

Contract tests for the NEW output shape of scripts/hooks/lint-changed.ps1.
When ruff finds errors the script must now emit:
  {
    "systemMessage": "<ruff output>",
    "hookSpecificOutput": {
      "hookEventName": "PostToolUse",
      "additionalContext": "<ruff output>"
    }
  }
When ruff finds no errors: returns {}.

AC coverage:
  AC1: lint errors → JSON contains hookSpecificOutput key
  AC2: hookSpecificOutput.hookEventName == "PostToolUse"
  AC3: hookSpecificOutput.additionalContext contains ruff output (non-empty)
  AC4: systemMessage and additionalContext contain the same text (no dual formatting)
  AC5: clean file → {} (no hookSpecificOutput)
  AC6: non-edit tool → {} (no hookSpecificOutput)
  AC7: systemMessage preserved alongside hookSpecificOutput (existing behaviour unchanged)
  AC8: all three edit tools produce hookSpecificOutput on lint errors
  AC9: missing file path → {} (no hookSpecificOutput, non-blocking)
  AC10: exit code never 2 even when hookSpecificOutput is emitted
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.slow

_REPO_ROOT = Path(__file__).parent.parent
_SCRIPT_PATH = _REPO_ROOT / "scripts" / "hooks" / "lint-changed.ps1"

# A Python source that reliably generates an F401 unused-import ruff error.
_LINT_ERROR_CONTENT = "import os\n"

# A Python source that is ruff-clean under the project's ruff config.
_CLEAN_CONTENT = "x: int = 1\n"


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _run_hook(stdin_data: dict, *, timeout: int = 30) -> tuple[int, dict]:
    """Run lint-changed.ps1 with the given stdin JSON.

    Returns (exit_code, parsed_stdout_json).
    Raises FileNotFoundError if the script does not exist — keeps RED failures
    explicit rather than silently succeeding on a missing script.
    """
    if not _SCRIPT_PATH.exists():
        msg = f"lint-changed.ps1 not found at {_SCRIPT_PATH}. Builder must create scripts/hooks/lint-changed.ps1."
        raise FileNotFoundError(msg)

    result = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-File", str(_SCRIPT_PATH)],
        input=json.dumps(stdin_data),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    stdout = result.stdout.strip()
    try:
        output = json.loads(stdout) if stdout else {}
    except json.JSONDecodeError:
        output = {"_raw": stdout}
    return result.returncode, output


# ---------------------------------------------------------------------------
# Windows-only behaviour tests
# ---------------------------------------------------------------------------


@pytest.mark.skipif(sys.platform != "win32", reason="PowerShell hook requires Windows")
class TestFromAC_LintFeedbackStructure:
    """Verify the new hookSpecificOutput shape added by task #547."""

    # --- AC1: hookSpecificOutput key present on lint errors ---

    def test_create_file_lint_errors_returns_hook_specific_output(self, tmp_path: Path) -> None:
        """AC1: create_file with ruff errors → output must contain hookSpecificOutput key."""
        bad_file = tmp_path / "bad_547a.py"
        bad_file.write_text(_LINT_ERROR_CONTENT, encoding="utf-8")
        _, output = _run_hook({"tool_name": "create_file", "tool_input": {"filePath": str(bad_file)}})
        assert "hookSpecificOutput" in output, (
            f"Expected 'hookSpecificOutput' key when ruff finds errors, got: {output!r}"
        )

    def test_replace_string_in_file_lint_errors_returns_hook_specific_output(self, tmp_path: Path) -> None:
        """AC8: replace_string_in_file with ruff errors → hookSpecificOutput present."""
        bad_file = tmp_path / "bad_547b.py"
        bad_file.write_text(_LINT_ERROR_CONTENT, encoding="utf-8")
        _, output = _run_hook(
            {
                "tool_name": "replace_string_in_file",
                "tool_input": {"filePath": str(bad_file)},
            }
        )
        assert "hookSpecificOutput" in output, (
            f"replace_string_in_file must return hookSpecificOutput on lint errors, got: {output!r}"
        )

    def test_multi_replace_lint_errors_returns_hook_specific_output(self, tmp_path: Path) -> None:
        """AC8: multi_replace_string_in_file with ruff errors → hookSpecificOutput present."""
        bad_file = tmp_path / "bad_547c.py"
        bad_file.write_text(_LINT_ERROR_CONTENT, encoding="utf-8")
        _, output = _run_hook(
            {
                "tool_name": "multi_replace_string_in_file",
                "tool_input": {"replacements": [{"filePath": str(bad_file)}]},
            }
        )
        assert "hookSpecificOutput" in output, (
            f"multi_replace_string_in_file must return hookSpecificOutput on lint errors, got: {output!r}"
        )

    # --- AC2: hookEventName == "PostToolUse" ---

    def test_hook_specific_output_event_name_is_post_tool_use(self, tmp_path: Path) -> None:
        """AC2: hookSpecificOutput.hookEventName must equal 'PostToolUse'."""
        bad_file = tmp_path / "bad_547d.py"
        bad_file.write_text(_LINT_ERROR_CONTENT, encoding="utf-8")
        _, output = _run_hook({"tool_name": "create_file", "tool_input": {"filePath": str(bad_file)}})
        hso = output.get("hookSpecificOutput", {})
        assert hso.get("hookEventName") == "PostToolUse", (
            f"hookSpecificOutput.hookEventName must be 'PostToolUse', got: {hso!r}"
        )

    # --- AC3: additionalContext is non-empty ruff output ---

    def test_hook_specific_output_additional_context_is_nonempty(self, tmp_path: Path) -> None:
        """AC3: hookSpecificOutput.additionalContext must be non-empty ruff output."""
        bad_file = tmp_path / "bad_547e.py"
        bad_file.write_text(_LINT_ERROR_CONTENT, encoding="utf-8")
        _, output = _run_hook({"tool_name": "create_file", "tool_input": {"filePath": str(bad_file)}})
        hso = output.get("hookSpecificOutput", {})
        additional_context = hso.get("additionalContext", "")
        assert additional_context, f"hookSpecificOutput.additionalContext must be non-empty ruff output, got: {hso!r}"

    # --- AC4 / boundary: systemMessage and additionalContext are identical ---

    def test_system_message_and_additional_context_are_identical(self, tmp_path: Path) -> None:
        """AC4: systemMessage and additionalContext must contain the same text (no dual formatting)."""
        bad_file = tmp_path / "bad_547f.py"
        bad_file.write_text(_LINT_ERROR_CONTENT, encoding="utf-8")
        _, output = _run_hook({"tool_name": "create_file", "tool_input": {"filePath": str(bad_file)}})
        system_msg = output.get("systemMessage", "")
        additional_context = output.get("hookSpecificOutput", {}).get("additionalContext", "")
        assert system_msg == additional_context, (
            f"systemMessage and additionalContext must be identical (same ruff output, no dual formatting).\n"
            f"systemMessage: {system_msg!r}\n"
            f"additionalContext: {additional_context!r}"
        )

    # --- AC7: both systemMessage and hookSpecificOutput present together ---

    def test_lint_errors_output_has_both_system_message_and_hook_specific_output(self, tmp_path: Path) -> None:
        """AC7: output must contain BOTH systemMessage and hookSpecificOutput keys together."""
        bad_file = tmp_path / "bad_547g.py"
        bad_file.write_text(_LINT_ERROR_CONTENT, encoding="utf-8")
        _, output = _run_hook({"tool_name": "create_file", "tool_input": {"filePath": str(bad_file)}})
        assert "systemMessage" in output, f"Output must contain systemMessage when ruff finds errors. Got: {output!r}"
        assert "hookSpecificOutput" in output, (
            f"Output must contain hookSpecificOutput when ruff finds errors. Got: {output!r}"
        )
