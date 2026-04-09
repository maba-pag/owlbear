"""Tests for task #685: Add scratch-only-allow write hook to quality-runner agent.

Contract-level tests for:
1. .owlbear/hooks/deny-scratch-only-writes.ps1 — allow-list path guard (.owlbear/scratch/ only)
2. share/agents/quality-runner.agent.md — PreToolUse hook frontmatter configuration

Assumed PreToolUse stdin JSON format (VS Code hooks spec):
  {
    "tool_name": "<tool_name>",
    "tool_input": { ... }
  }

Path extraction fields:
  - tool_input.filePath          (create_file, replace_string_in_file)
  - tool_input.dirPath           (create_directory)
  - tool_input.replacements[*].filePath  (multi_replace_string_in_file)
  - tool_input.files[*]          (editFiles — string or object with filePath)

Allow-list rule: extracted path must match regex `(^|/)\\.owlbear/scratch/` after
normalizing \\ to / (handles both absolute and relative paths). Must NOT use StartsWith.

AC coverage:
  AC1a: .owlbear/hooks/deny-scratch-only-writes.ps1 exists on disk
  AC1b: script is non-empty (has content)
  AC2a: create_file with relative .owlbear/scratch/ path → {} (allowed)
  AC2b: create_file with absolute path containing .owlbear/scratch/ → {} (allowed)
  AC2c: backslash-normalized .owlbear\\scratch\\ path → {} (allowed)
  AC3a: create_file with src/ path → denied
  AC3b: create_file with tests/ path → denied
  AC3c: create_file with .owlbear/hooks/ path → denied (not scratch)
  AC3d: deny response contains descriptive permissionDecisionReason
  AC3e: deny response nests under hookSpecificOutput key
  AC4a: create_file is a gated write tool
  AC4b: replace_string_in_file is a gated write tool
  AC4c: multi_replace_string_in_file is a gated write tool
  AC4d: apply_patch is a gated write tool
  AC4e: create_directory is a gated write tool
  AC4f: editFiles is a gated write tool
  AC5a: malformed JSON input → {}
  AC5b: empty tool_name → {}
  AC5c: missing tool_name key → {}
  AC5d: write tool with no path fields in tool_input → {}
  AC5e: write tool with empty string filePath → {}
  AC5f: run_in_terminal returns {} (non-write pass-through)
  AC5g: read_file returns {} (non-write pass-through)
  AC5h: unknown future tool_name returns {}
  AC6a: quality-runner.agent.md frontmatter contains hooks: section
  AC6b: hooks: section contains PreToolUse entry
  AC6c: PreToolUse hook has type: command
  AC6d: PreToolUse command references deny-scratch-only-writes.ps1
  AC6e: frontmatter is valid parseable YAML with hooks key
  AC6f: frontmatter has no duplicate top-level YAML keys
  Boundary1: .owlbear/scratch without trailing slash → denied (regex requires /)
  Boundary2: .owlbear/scratchpad/ path → denied (not scratch/)
  Boundary3: empty replacements array → {} (no paths extracted)
  Boundary4: multi_replace with one scratch path + one non-scratch path → denied
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.slow

_REPO_ROOT = Path(__file__).parent.parent
_SCRIPT_PATH = _REPO_ROOT / ".owlbear" / "hooks" / "deny-scratch-only-writes.ps1"
_AGENT_PATH = _REPO_ROOT / "share" / "agents" / "quality-runner.agent.md"

# All write tools that the hook must gate (AC4)
_GATED_WRITE_TOOLS = [
    "create_file",
    "replace_string_in_file",
    "multi_replace_string_in_file",
    "apply_patch",
    "create_directory",
    "editFiles",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_hook(stdin_data: dict, *, timeout: int = 30) -> tuple[int, dict]:
    """Run deny-scratch-only-writes.ps1 with the given stdin JSON.

    Returns (exit_code, parsed_stdout_json).
    Raises FileNotFoundError if the script does not yet exist — makes
    RED-phase failures explicit rather than silently returning {}.
    """
    if not _SCRIPT_PATH.exists():
        msg = (
            f"deny-scratch-only-writes.ps1 not found at {_SCRIPT_PATH}. "
            "Builder must create .owlbear/hooks/deny-scratch-only-writes.ps1 to make these tests pass."
        )
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


def _is_denied(output: dict) -> bool:
    """Return True if the hook response contains a deny permissionDecision."""
    return output.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"


def _extract_frontmatter(content: str) -> str:
    """Return the YAML text between the first --- ... --- block."""
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    assert match is not None, "No valid YAML frontmatter (--- ... ---) found in quality-runner.agent.md"
    return match.group(1)


# ---------------------------------------------------------------------------
# Script existence — AC1 — fails RED until builder creates the file
# ---------------------------------------------------------------------------


class TestFromAC_ScriptExists:
    """Script must be created at the expected path with content (AC1)."""

    def test_deny_scratch_only_writes_ps1_exists(self) -> None:
        """AC1a: deny-scratch-only-writes.ps1 must exist on disk."""
        assert _SCRIPT_PATH.exists(), (
            f"deny-scratch-only-writes.ps1 not found at {_SCRIPT_PATH}. "
            "Builder must create .owlbear/hooks/deny-scratch-only-writes.ps1."
        )

    def test_script_is_nonempty(self) -> None:
        """AC1b: Script file must have content — an empty file cannot implement the guard."""
        assert _SCRIPT_PATH.exists(), f"deny-scratch-only-writes.ps1 not found at {_SCRIPT_PATH}."
        assert _SCRIPT_PATH.stat().st_size > 0, (
            "deny-scratch-only-writes.ps1 exists but is empty — builder must implement it."
        )


# ---------------------------------------------------------------------------
# Path guard behaviour — AC2, AC3, AC4 — Windows/PowerShell required
# ---------------------------------------------------------------------------


@pytest.mark.skipif(sys.platform != "win32", reason="PowerShell hook requires Windows")
class TestFromAC_ScratchPathGuardBehavior:
    """Behavioural tests via subprocess.  All fail RED because script doesn't exist."""

    # --- AC2: scratch paths are allowed ---

    def test_create_file_scratch_relative_path_is_allowed(self) -> None:
        """AC2a: create_file with relative .owlbear/scratch/ path must return {} (allowed)."""
        _, output = _run_hook(
            {
                "tool_name": "create_file",
                "tool_input": {"filePath": ".owlbear/scratch/pytest-output-123.txt"},
            }
        )
        assert output == {}, f"create_file with .owlbear/scratch/ path must return {{}} (allowed), got: {output!r}"

    def test_create_file_scratch_nested_file_is_allowed(self) -> None:
        """AC2a: create_file with nested .owlbear/scratch/ path must be allowed."""
        _, output = _run_hook(
            {
                "tool_name": "create_file",
                "tool_input": {"filePath": ".owlbear/scratch/sub/output.txt"},
            }
        )
        assert output == {}, f"create_file with nested scratch path must return {{}} (allowed), got: {output!r}"

    def test_create_file_absolute_scratch_path_is_allowed(self) -> None:
        """AC2b: create_file with absolute path containing .owlbear/scratch/ must be allowed.

        e.g. C:\\Users\\user\\owlbear\\.owlbear\\scratch\\file.txt
        normalizes to C:/Users/user/owlbear/.owlbear/scratch/file.txt
        regex (^|/)\\.owlbear/scratch/ matches via the / before .owlbear
        """
        abs_path = str(_REPO_ROOT / ".owlbear" / "scratch" / "pytest-output-42.txt")
        _, output = _run_hook(
            {
                "tool_name": "create_file",
                "tool_input": {"filePath": abs_path},
            }
        )
        assert output == {}, f"create_file with absolute scratch path must return {{}} (allowed), got: {output!r}"

    def test_create_file_backslash_scratch_path_is_allowed(self) -> None:
        """AC2c: backslash path .owlbear\\scratch\\file.txt must be normalized → allowed."""
        _, output = _run_hook(
            {
                "tool_name": "create_file",
                "tool_input": {"filePath": ".owlbear\\scratch\\pytest-output-99.txt"},
            }
        )
        assert output == {}, f"Backslash .owlbear\\\\scratch\\\\ path should be normalized and allowed, got: {output!r}"

    # --- AC3: non-scratch paths are denied ---

    def test_create_file_src_path_is_denied(self) -> None:
        """AC3a: create_file with src/ path must be denied."""
        _, output = _run_hook(
            {
                "tool_name": "create_file",
                "tool_input": {"filePath": "src/module/impl.py"},
            }
        )
        assert _is_denied(output), f"create_file with src/ path must be denied, got: {output!r}"

    def test_create_file_tests_path_is_denied(self) -> None:
        """AC3b: create_file with tests/ path must be denied (not .owlbear/scratch/)."""
        _, output = _run_hook(
            {
                "tool_name": "create_file",
                "tool_input": {"filePath": "tests/test_foo.py"},
            }
        )
        assert _is_denied(output), f"create_file with tests/ path must be denied, got: {output!r}"

    def test_create_file_owlbear_hooks_path_is_denied(self) -> None:
        """AC3c: create_file targeting .owlbear/hooks/ must be denied (not scratch)."""
        _, output = _run_hook(
            {
                "tool_name": "create_file",
                "tool_input": {"filePath": ".owlbear/hooks/evil.ps1"},
            }
        )
        assert _is_denied(output), f"create_file with .owlbear/hooks/ path must be denied, got: {output!r}"

    def test_create_file_root_path_is_denied(self) -> None:
        """AC3: create_file with a project root path must be denied."""
        _, output = _run_hook(
            {
                "tool_name": "create_file",
                "tool_input": {"filePath": "README.md"},
            }
        )
        assert _is_denied(output), f"create_file with root README.md path must be denied, got: {output!r}"

    def test_deny_response_has_hook_specific_output_key(self) -> None:
        """AC3e: deny response must nest under hookSpecificOutput key."""
        _, output = _run_hook(
            {
                "tool_name": "create_file",
                "tool_input": {"filePath": "src/evil.py"},
            }
        )
        assert "hookSpecificOutput" in output, f"Deny response must contain 'hookSpecificOutput' key, got: {output!r}"

    def test_deny_reason_is_nonempty(self) -> None:
        """AC3d: permissionDecisionReason must be non-empty string when denying."""
        _, output = _run_hook(
            {
                "tool_name": "create_file",
                "tool_input": {"filePath": "src/evil.py"},
            }
        )
        reason = output.get("hookSpecificOutput", {}).get("permissionDecisionReason", "")
        assert reason, f"permissionDecisionReason must be non-empty when denying a write, got: {output!r}"

    # --- AC4a: create_file is gated ---

    def test_create_file_non_scratch_is_gated(self) -> None:
        """AC4a: create_file is a gated write tool — non-scratch path must be denied."""
        _, output = _run_hook(
            {
                "tool_name": "create_file",
                "tool_input": {"filePath": "packages/foo/bar.py"},
            }
        )
        assert _is_denied(output), f"create_file is a gated write tool — packages/ path must be denied, got: {output!r}"

    # --- AC4b: replace_string_in_file is gated ---

    def test_replace_string_in_file_scratch_path_is_allowed(self) -> None:
        """AC4b allow: replace_string_in_file with scratch filePath must return {}."""
        _, output = _run_hook(
            {
                "tool_name": "replace_string_in_file",
                "tool_input": {
                    "filePath": ".owlbear/scratch/output.txt",
                    "oldString": "old",
                    "newString": "new",
                },
            }
        )
        assert output == {}, f"replace_string_in_file with scratch path must be allowed, got: {output!r}"

    def test_replace_string_in_file_non_scratch_is_denied(self) -> None:
        """AC4b deny: replace_string_in_file with non-scratch filePath must be denied."""
        _, output = _run_hook(
            {
                "tool_name": "replace_string_in_file",
                "tool_input": {
                    "filePath": "src/module/impl.py",
                    "oldString": "x",
                    "newString": "y",
                },
            }
        )
        assert _is_denied(output), f"replace_string_in_file with src/ path must be denied, got: {output!r}"

    # --- AC4c: multi_replace_string_in_file is gated ---

    def test_multi_replace_all_scratch_paths_is_allowed(self) -> None:
        """AC4c allow: multi_replace with all .owlbear/scratch/ replacements must return {}."""
        _, output = _run_hook(
            {
                "tool_name": "multi_replace_string_in_file",
                "tool_input": {
                    "replacements": [
                        {
                            "filePath": ".owlbear/scratch/a.txt",
                            "oldString": "a",
                            "newString": "b",
                        },
                        {
                            "filePath": ".owlbear/scratch/b.txt",
                            "oldString": "c",
                            "newString": "d",
                        },
                    ],
                },
            }
        )
        assert output == {}, f"multi_replace with all scratch paths must be allowed, got: {output!r}"

    def test_multi_replace_any_non_scratch_path_is_denied(self) -> None:
        """AC4c deny: any replacement targeting non-scratch path must deny the whole call."""
        _, output = _run_hook(
            {
                "tool_name": "multi_replace_string_in_file",
                "tool_input": {
                    "replacements": [
                        {
                            "filePath": ".owlbear/scratch/a.txt",
                            "oldString": "a",
                            "newString": "b",
                        },
                        {
                            "filePath": "src/module/impl.py",
                            "oldString": "c",
                            "newString": "d",
                        },
                    ],
                },
            }
        )
        assert _is_denied(output), f"multi_replace with any non-scratch path must be denied, got: {output!r}"

    # --- AC4d: apply_patch is gated ---

    def test_apply_patch_scratch_path_is_allowed(self) -> None:
        """AC4d allow: apply_patch to a scratch filePath must return {}."""
        _, output = _run_hook(
            {
                "tool_name": "apply_patch",
                "tool_input": {"filePath": ".owlbear/scratch/output.txt"},
            }
        )
        assert output == {}, f"apply_patch to scratch/ path must be allowed, got: {output!r}"

    def test_apply_patch_non_scratch_is_denied(self) -> None:
        """AC4d deny: apply_patch to a non-scratch filePath must be denied."""
        _, output = _run_hook(
            {
                "tool_name": "apply_patch",
                "tool_input": {"filePath": "src/evil.py"},
            }
        )
        assert _is_denied(output), f"apply_patch to src/ path must be denied (gated write tool), got: {output!r}"

    # --- AC4e: create_directory is gated ---

    def test_create_directory_scratch_dirpath_is_allowed(self) -> None:
        """AC4e allow: create_directory with .owlbear/scratch/ dirPath must return {}."""
        _, output = _run_hook(
            {
                "tool_name": "create_directory",
                "tool_input": {"dirPath": ".owlbear/scratch/sub"},
            }
        )
        assert output == {}, f"create_directory with scratch dirPath must be allowed, got: {output!r}"

    def test_create_directory_non_scratch_is_denied(self) -> None:
        """AC4e deny: create_directory with non-scratch dirPath must be denied."""
        _, output = _run_hook(
            {
                "tool_name": "create_directory",
                "tool_input": {"dirPath": "packages/new_module"},
            }
        )
        assert _is_denied(output), f"create_directory with packages/ dirPath must be denied, got: {output!r}"

    # --- AC4f: editFiles is gated ---

    def test_edit_files_scratch_path_is_allowed(self) -> None:
        """AC4f allow: editFiles targeting a scratch path must return {}."""
        _, output = _run_hook(
            {
                "tool_name": "editFiles",
                "tool_input": {"files": [".owlbear/scratch/output.txt"]},
            }
        )
        assert output == {}, f"editFiles with scratch path must be allowed, got: {output!r}"

    def test_edit_files_non_scratch_is_denied(self) -> None:
        """AC4f deny: editFiles targeting a non-scratch path must be denied."""
        _, output = _run_hook(
            {
                "tool_name": "editFiles",
                "tool_input": {"files": ["src/evil.py"]},
            }
        )
        assert _is_denied(output), f"editFiles with src/ path must be denied, got: {output!r}"

    # --- AC5: safety edge cases and non-write pass-through ---

    def test_malformed_stdin_json_returns_empty_json(self) -> None:
        """AC5a: malformed stdin must not crash the script — returns {}."""
        if not _SCRIPT_PATH.exists():
            raise FileNotFoundError(f"deny-scratch-only-writes.ps1 not found at {_SCRIPT_PATH}.")
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-File", str(_SCRIPT_PATH)],
            input="not-valid-json{{{",
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        stdout = result.stdout.strip()
        try:
            output = json.loads(stdout) if stdout else {}
        except json.JSONDecodeError:
            output = {"_raw": stdout}
        assert output == {}, f"Malformed JSON input must produce {{}} output, got: {output!r}"

    def test_empty_tool_name_returns_empty_json(self) -> None:
        """AC5b: empty string tool_name is not gated — must return {}."""
        _, output = _run_hook({"tool_name": "", "tool_input": {}})
        assert output == {}

    def test_missing_tool_name_key_returns_empty_json(self) -> None:
        """AC5c: stdin JSON with no tool_name key — must not crash, returns {}."""
        _, output = _run_hook({"tool_input": {}})
        assert output == {}

    def test_write_tool_with_no_paths_returns_empty_json(self) -> None:
        """AC5d: write tool with no path fields in tool_input → {} (nothing to deny)."""
        _, output = _run_hook(
            {
                "tool_name": "create_file",
                "tool_input": {"content": "hello"},
            }
        )
        assert output == {}, f"create_file with no filePath must return {{}} (nothing to deny), got: {output!r}"

    def test_write_tool_with_empty_string_filepath_returns_empty_json(self) -> None:
        """AC5e: write tool with filePath='' — empty path → {} (pass-through)."""
        _, output = _run_hook(
            {
                "tool_name": "create_file",
                "tool_input": {"filePath": ""},
            }
        )
        assert output == {}, f"create_file with empty filePath must return {{}} (pass-through), got: {output!r}"

    def test_run_in_terminal_returns_empty_json(self) -> None:
        """AC5f: run_in_terminal is not a write tool — must return {}."""
        _, output = _run_hook({"tool_name": "run_in_terminal", "tool_input": {}})
        assert output == {}

    def test_read_file_returns_empty_json(self) -> None:
        """AC5g: read_file is not a write tool — must return {}."""
        _, output = _run_hook({"tool_name": "read_file", "tool_input": {}})
        assert output == {}

    def test_unknown_tool_name_returns_empty_json(self) -> None:
        """AC5h: unknown/future tool_name values must pass through — return {}."""
        _, output = _run_hook({"tool_name": "some_future_tool", "tool_input": {}})
        assert output == {}

    # --- Output contract ---

    def test_stdout_is_always_valid_json_for_allowed_call(self) -> None:
        """Contract: stdout must always be valid JSON — for allowed calls returns {}."""
        if not _SCRIPT_PATH.exists():
            raise FileNotFoundError(f"deny-scratch-only-writes.ps1 not found at {_SCRIPT_PATH}.")
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-File", str(_SCRIPT_PATH)],
            input=json.dumps(
                {
                    "tool_name": "create_file",
                    "tool_input": {"filePath": ".owlbear/scratch/output.txt"},
                }
            ),
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
            pytest.fail(f"Script stdout is not valid JSON for allowed call: {stdout!r}\nError: {exc}")
        assert isinstance(parsed, dict), f"Output must be a JSON object, got: {parsed!r}"

    def test_stdout_is_always_valid_json_for_denied_call(self) -> None:
        """Contract: stdout must always be valid JSON — for denied calls returns deny object."""
        if not _SCRIPT_PATH.exists():
            raise FileNotFoundError(f"deny-scratch-only-writes.ps1 not found at {_SCRIPT_PATH}.")
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-File", str(_SCRIPT_PATH)],
            input=json.dumps(
                {
                    "tool_name": "create_file",
                    "tool_input": {"filePath": "src/evil.py"},
                }
            ),
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
            pytest.fail(f"Script stdout is not valid JSON for denied call: {stdout!r}\nError: {exc}")
        assert isinstance(parsed, dict), f"Output must be a JSON object, got: {parsed!r}"

    # --- Boundary conditions ---

    def test_owlbear_scratch_without_trailing_slash_is_denied(self) -> None:
        """Boundary1: '.owlbear/scratch' without trailing slash must be denied.

        Regex (^|/)\\.owlbear/scratch/ requires the trailing slash — this is a boundary
        condition where the segment exists but the pattern does not match.
        """
        _, output = _run_hook(
            {
                "tool_name": "create_file",
                "tool_input": {"filePath": ".owlbear/scratch"},
            }
        )
        assert _is_denied(output), (
            f"'.owlbear/scratch' without trailing slash must be denied "
            f"(regex requires slash after 'scratch'). Got: {output!r}"
        )

    def test_owlbear_scratchpad_path_is_denied(self) -> None:
        """Boundary2: '.owlbear/scratchpad/file.txt' must be denied — 'scratch/' not matched."""
        _, output = _run_hook(
            {
                "tool_name": "create_file",
                "tool_input": {"filePath": ".owlbear/scratchpad/file.txt"},
            }
        )
        assert _is_denied(output), f"'.owlbear/scratchpad/' must be denied (not .owlbear/scratch/). Got: {output!r}"

    def test_multi_replace_empty_replacements_returns_empty_json(self) -> None:
        """Boundary3: empty replacements array → no paths extracted → {} (pass-through)."""
        _, output = _run_hook(
            {
                "tool_name": "multi_replace_string_in_file",
                "tool_input": {"replacements": []},
            }
        )
        assert output == {}, (
            f"multi_replace with empty replacements must return {{}} (no paths to check), got: {output!r}"
        )

    def test_multi_replace_scratch_and_non_scratch_path_is_denied(self) -> None:
        """Boundary4: mixed scratch + non-scratch in multi_replace → whole call denied."""
        _, output = _run_hook(
            {
                "tool_name": "multi_replace_string_in_file",
                "tool_input": {
                    "replacements": [
                        {
                            "filePath": ".owlbear/scratch/output.txt",
                            "oldString": "a",
                            "newString": "b",
                        },
                        {
                            "filePath": "src/module/impl.py",
                            "oldString": "c",
                            "newString": "d",
                        },
                    ],
                },
            }
        )
        assert _is_denied(output), f"multi_replace mixing scratch and non-scratch paths must be denied. Got: {output!r}"


# ---------------------------------------------------------------------------
# quality-runner.agent.md frontmatter — AC6
# ---------------------------------------------------------------------------


class TestFromAC_QualityRunnerAgentHooks:
    """quality-runner.agent.md must gain a PreToolUse hook referencing deny-scratch-only-writes.ps1."""

    def _content(self) -> str:
        assert _AGENT_PATH.exists(), f"Agent file not found at {_AGENT_PATH}"
        return _AGENT_PATH.read_text(encoding="utf-8")

    def _frontmatter(self) -> str:
        return _extract_frontmatter(self._content())

    def test_frontmatter_has_hooks_section(self) -> None:
        """AC6a: quality-runner.agent.md frontmatter must contain a hooks: key."""
        fm = self._frontmatter()
        assert re.search(r"^hooks:", fm, re.MULTILINE), (
            "quality-runner.agent.md frontmatter is missing the 'hooks:' key. "
            "Builder must add a PreToolUse hooks section."
        )

    def test_frontmatter_has_pretooluse_entry(self) -> None:
        """AC6b: hooks: section must contain a PreToolUse entry."""
        fm = self._frontmatter()
        assert "PreToolUse" in fm, "quality-runner.agent.md hooks: section is missing a PreToolUse entry."

    def test_pretooluse_hook_type_is_command(self) -> None:
        """AC6c: PreToolUse hook must specify type: command."""
        fm = self._frontmatter()
        assert re.search(r"type:\s*command", fm), (
            "quality-runner.agent.md PreToolUse hook must specify 'type: command'."
        )

    def test_pretooluse_hook_command_references_deny_scratch_only_writes(self) -> None:
        """AC6d: PreToolUse hook command must reference deny-scratch-only-writes.ps1."""
        fm = self._frontmatter()
        assert "deny-scratch-only-writes.ps1" in fm, (
            "quality-runner.agent.md PreToolUse hook command must point to deny-scratch-only-writes.ps1."
        )

    def test_frontmatter_is_parseable_yaml_with_pretooluse_hook(self) -> None:
        """AC6e: frontmatter must parse as valid YAML and contain hooks after builder changes."""
        import yaml  # noqa: PLC0415

        fm = self._frontmatter()
        try:
            parsed = yaml.safe_load(fm)
        except yaml.YAMLError as exc:
            pytest.fail(f"quality-runner.agent.md frontmatter is not valid YAML: {exc}")
        assert isinstance(parsed, dict), f"Parsed YAML frontmatter must be a dict, got: {type(parsed)}"
        assert "hooks" in parsed, (
            "Frontmatter parsed but missing 'hooks:' key — builder must add the PreToolUse hooks section."
        )
        hooks = parsed["hooks"]
        assert "PreToolUse" in hooks, f"hooks section must contain PreToolUse key, got: {hooks!r}"

    def test_frontmatter_no_duplicate_keys(self) -> None:
        """AC6f: frontmatter must not gain duplicate YAML keys after edit."""
        fm = self._frontmatter()
        # Fail pre-impl by checking hooks: is present first
        assert "hooks:" in fm, (
            "Builder must add the hooks: section — no duplicate-key check is meaningful before the hook is added."
        )
        top_level_keys = re.findall(r"^([a-zA-Z][a-zA-Z0-9_-]*):", fm, re.MULTILINE)
        seen: set[str] = set()
        duplicates: list[str] = []
        for key in top_level_keys:
            if key in seen:
                duplicates.append(key)
            seen.add(key)
        assert not duplicates, f"Duplicate YAML keys found in quality-runner.agent.md frontmatter: {duplicates}"
