"""Tests for task #546: Add apply_patch to #210 lint guard tool_name filter.

Contract-level tests verifying apply_patch is recognised and handled by
scripts/hooks/lint-changed.ps1.

NOTE — Pipeline violation: commit 68c6a55 added the implementation before the
architecture review and this test file existed. These tests serve as post-hoc
contract validation (confirmed by architect's process note in task body). Tests
are expected to PASS against the committed implementation; they act as regression
guards going forward.

AC coverage:
  AC1: edit_tools array in scripts/hooks/lint-changed.ps1 includes 'apply_patch'
  AC2: apply_patch with ruff-clean tool_input.filePath returns {}
  AC3: apply_patch with lint-error filePath returns non-empty systemMessage AND
       hookSpecificOutput.additionalContext
  AC4: apply_patch with nonexistent filePath returns {} (graceful degradation)
  AC5: apply_patch with missing/null filePath returns {} (graceful degradation)
  AC6: script exit code is never 2 for any apply_patch invocation
  AC7: all script stdout for apply_patch tool_name is valid JSON
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.slow

_REPO_ROOT = Path(__file__).parent.parent
_SCRIPT_PATH = _REPO_ROOT / ".owlbear" / "hooks" / "lint-changed.ps1"

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
    Raises FileNotFoundError if the script does not exist.
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
# AC1 -- apply_patch must appear in the edit_tools array
# ---------------------------------------------------------------------------


class TestFromAC_ApplyPatchFilter:
    """AC1: 'apply_patch' must be listed in the edit_tools array."""

    def test_apply_patch_in_edit_tools_array(self) -> None:
        """AC1: lint-changed.ps1 edit_tools array must contain the string 'apply_patch'."""
        assert _SCRIPT_PATH.exists(), (
            f"lint-changed.ps1 not found at {_SCRIPT_PATH}. Builder must implement scripts/hooks/lint-changed.ps1."
        )
        content = _SCRIPT_PATH.read_text(encoding="utf-8")
        assert "'apply_patch'" in content, (
            "edit_tools array in lint-changed.ps1 must include 'apply_patch'. "
            "Current script does not contain the string literal 'apply_patch'."
        )


# ---------------------------------------------------------------------------
# AC2-AC7 -- apply_patch runtime behaviour (Windows/PowerShell required)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(sys.platform != "win32", reason="PowerShell hook requires Windows")
class TestFromAC_ApplyPatchBehavior:
    """AC2-AC7: apply_patch tool_name I/O behaviour via subprocess."""

    # --- AC2: clean file -> {} ---

    def test_apply_patch_clean_file_returns_empty_json(self, tmp_path: Path) -> None:
        """AC2: apply_patch with a ruff-clean filePath returns {}."""
        clean_file = tmp_path / "clean_546.py"
        clean_file.write_text(_CLEAN_CONTENT, encoding="utf-8")
        _, output = _run_hook({"tool_name": "apply_patch", "tool_input": {"filePath": str(clean_file)}})
        assert output == {}, f"Expected {{}}, got {output!r}"

    # --- AC3: lint errors -> systemMessage + hookSpecificOutput.additionalContext ---

    def test_apply_patch_lint_errors_returns_system_message(self, tmp_path: Path) -> None:
        """AC3: apply_patch with lint-error file returns non-empty systemMessage."""
        bad_file = tmp_path / "bad_546a.py"
        bad_file.write_text(_LINT_ERROR_CONTENT, encoding="utf-8")
        _, output = _run_hook({"tool_name": "apply_patch", "tool_input": {"filePath": str(bad_file)}})
        assert "systemMessage" in output, f"Expected {{'systemMessage': '...'}}, got {output!r}"
        assert output["systemMessage"], "systemMessage must be non-empty ruff output"

    def test_apply_patch_lint_errors_returns_hook_specific_additional_context(self, tmp_path: Path) -> None:
        """AC3: apply_patch with lint errors returns hookSpecificOutput.additionalContext."""
        bad_file = tmp_path / "bad_546b.py"
        bad_file.write_text(_LINT_ERROR_CONTENT, encoding="utf-8")
        _, output = _run_hook({"tool_name": "apply_patch", "tool_input": {"filePath": str(bad_file)}})
        assert "hookSpecificOutput" in output, f"Expected hookSpecificOutput in response, got {output!r}"
        hook_output = output.get("hookSpecificOutput", {})
        assert "additionalContext" in hook_output, f"Expected hookSpecificOutput.additionalContext, got {hook_output!r}"
        assert hook_output["additionalContext"], "hookSpecificOutput.additionalContext must be non-empty ruff output"

    # --- AC4: nonexistent filePath -> {} ---

    def test_apply_patch_nonexistent_filepath_returns_empty_json(self) -> None:
        """AC4: apply_patch with nonexistent filePath returns {} (graceful degradation)."""
        _, output = _run_hook(
            {
                "tool_name": "apply_patch",
                "tool_input": {"filePath": "/nonexistent/no_such_file_546.py"},
            }
        )
        assert output == {}, f"Expected {{}}, got {output!r}"

    # --- AC5: missing / null filePath -> {} ---

    def test_apply_patch_missing_filepath_returns_empty_json(self) -> None:
        """AC5: apply_patch with no filePath field returns {} (graceful degradation)."""
        _, output = _run_hook({"tool_name": "apply_patch", "tool_input": {}})
        assert output == {}, f"Expected {{}}, got {output!r}"

    def test_apply_patch_null_filepath_returns_empty_json(self) -> None:
        """AC5: apply_patch with null filePath returns {} (graceful degradation)."""
        _, output = _run_hook({"tool_name": "apply_patch", "tool_input": {"filePath": None}})
        assert output == {}, f"Expected {{}}, got {output!r}"

    # --- AC6: exit code never 2 ---

    def test_apply_patch_exit_code_never_2_clean_file(self, tmp_path: Path) -> None:
        """AC6: apply_patch clean-file path -- exit code must never be 2."""
        clean_file = tmp_path / "clean_ec_546.py"
        clean_file.write_text(_CLEAN_CONTENT, encoding="utf-8")
        code, _ = _run_hook({"tool_name": "apply_patch", "tool_input": {"filePath": str(clean_file)}})
        assert code != 2, f"Script must never exit with code 2 (non-blocking design), got {code}"

    def test_apply_patch_exit_code_never_2_lint_errors(self, tmp_path: Path) -> None:
        """AC6: apply_patch lint-error path -- exit code must never be 2."""
        bad_file = tmp_path / "bad_ec_546.py"
        bad_file.write_text(_LINT_ERROR_CONTENT, encoding="utf-8")
        code, _ = _run_hook({"tool_name": "apply_patch", "tool_input": {"filePath": str(bad_file)}})
        assert code != 2, f"Lint errors must not block builder via exit code 2, got {code}"

    def test_apply_patch_exit_code_never_2_missing_filepath(self) -> None:
        """AC6: apply_patch missing-filePath path -- exit code must never be 2."""
        code, _ = _run_hook({"tool_name": "apply_patch", "tool_input": {}})
        assert code != 2, f"Script must never exit with code 2 for missing filePath, got {code}"

    # --- AC7: all stdout for apply_patch is valid JSON ---

    def test_apply_patch_stdout_is_valid_json_for_lint_errors(self, tmp_path: Path) -> None:
        """AC7: script stdout for apply_patch with lint errors is valid JSON."""
        if not _SCRIPT_PATH.exists():
            pytest.fail(f"lint-changed.ps1 not found at {_SCRIPT_PATH}.")
        bad_file = tmp_path / "bad_json_546.py"
        bad_file.write_text(_LINT_ERROR_CONTENT, encoding="utf-8")
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-File", str(_SCRIPT_PATH)],
            input=json.dumps({"tool_name": "apply_patch", "tool_input": {"filePath": str(bad_file)}}),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        stdout = result.stdout.strip()
        try:
            parsed = json.loads(stdout) if stdout else {}
        except json.JSONDecodeError as exc:
            pytest.fail(f"Script stdout is not valid JSON for apply_patch: {stdout!r}\nError: {exc}")
        assert isinstance(parsed, dict), f"Output must be a JSON object, got: {parsed!r}"

    def test_apply_patch_stdout_is_valid_json_for_clean_file(self, tmp_path: Path) -> None:
        """AC7: script stdout for apply_patch with clean file is valid JSON."""
        if not _SCRIPT_PATH.exists():
            pytest.fail(f"lint-changed.ps1 not found at {_SCRIPT_PATH}.")
        clean_file = tmp_path / "clean_json_546.py"
        clean_file.write_text(_CLEAN_CONTENT, encoding="utf-8")
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-File", str(_SCRIPT_PATH)],
            input=json.dumps({"tool_name": "apply_patch", "tool_input": {"filePath": str(clean_file)}}),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        stdout = result.stdout.strip()
        try:
            parsed = json.loads(stdout) if stdout else {}
        except json.JSONDecodeError as exc:
            pytest.fail(f"Script stdout is not valid JSON for apply_patch: {stdout!r}\nError: {exc}")
        assert isinstance(parsed, dict), f"Output must be a JSON object, got: {parsed!r}"
