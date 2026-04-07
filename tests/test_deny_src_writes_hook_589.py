"""Tests for task #589: Add PreToolUse path guard hook to test-writer agent (Phase 3).

Contract-level tests for:
1. scripts/hooks/deny-src-writes.ps1 — allow-list path guard (tests/ only)
2. share/agents/test-writer.agent.md — PreToolUse hook + tools list edit

Assumed PreToolUse stdin JSON format (VS Code hooks spec):
  {
    "tool_name": "<tool_name>",
    "tool_input": { ... }
  }

Path extraction fields (AC1):
  - tool_input.filePath          (create_file, replace_string_in_file)
  - tool_input.dirPath           (create_directory)
  - tool_input.replacements[*].filePath  (multi_replace_string_in_file)

Allow-list rule (AC1): extracted path must start with "tests/" after normalizing \\ to /.
If ANY extracted path fails the allow-list, the script denies the call.

AC coverage:
  AC1a: script normalizes \\ to / before comparing paths
  AC1b: create_file with tests/ path → returns {} (allowed)
  AC1c: create_file with packages/ path → denied
  AC1d: replace_string_in_file with tests/ path → {} (allowed)
  AC1e: replace_string_in_file with packages/ path → denied
  AC1f: multi_replace with all tests/ paths → {} (allowed)
  AC1g: multi_replace with any non-tests/ path → denied
  AC1h: create_directory with tests/ dirPath → {} (allowed)
  AC1i: create_directory with packages/ dirPath → denied
  AC2a: create_file is a gated write tool
  AC2b: replace_string_in_file is a gated write tool
  AC2c: multi_replace_string_in_file is a gated write tool
  AC2d: create_directory is a gated write tool
  AC2e: apply_patch is NOT gated (returns {} for any path) — excluded per AC2
  AC2f: run_in_terminal returns {} (pass-through, not gated)
  AC2g: read_file returns {} (pass-through, not gated)
  AC2h: unknown future tool returns {} (pass-through)
  AC3a: test-writer.agent.md frontmatter contains hooks: section
  AC3b: hooks: section contains PreToolUse entry
  AC3c: PreToolUse hook has type: command
  AC3d: PreToolUse command references deny-src-writes.ps1
  AC4:  test-writer.agent.md tools list does not contain edit/rename
  AC5a: malformed stdin JSON → {}
  AC5b: empty tool_name → {}
  AC5c: missing tool_name key → {}
  AC5d: write tool with no paths in tool_input → {}
  AC5e: write tool with empty string filePath → {}
  AC6:  test-writer.agent.md frontmatter is valid YAML with hooks + no duplicate keys
  Boundary1: path starting with "tests" but not "tests/" → denied
  Boundary2: backslash path tests\\foo.py → normalized to tests/foo.py → allowed
  Boundary3: empty replacements array → {} (no paths extracted)
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
_SCRIPT_PATH = _REPO_ROOT / ".owlbear" / "hooks" / "deny-src-writes.ps1"
_AGENT_PATH = _REPO_ROOT / "share" / "agents" / "test-writer.agent.md"

# Write tools that the hook must gate (AC2); apply_patch is explicitly excluded
_GATED_WRITE_TOOLS = [
    "create_file",
    "replace_string_in_file",
    "multi_replace_string_in_file",
    "create_directory",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_hook(stdin_data: dict, *, timeout: int = 30) -> tuple[int, dict]:
    """Run deny-src-writes.ps1 with the given stdin JSON.

    Returns (exit_code, parsed_stdout_json).
    Raises FileNotFoundError if the script does not yet exist — makes
    RED-phase failures explicit rather than silently returning {}.
    """
    if not _SCRIPT_PATH.exists():
        msg = (
            f"deny-src-writes.ps1 not found at {_SCRIPT_PATH}. "
            "Builder must create scripts/hooks/deny-src-writes.ps1 to make these tests pass."
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
    return (
        output.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"
    )


def _extract_frontmatter(content: str) -> str:
    """Return the YAML text between the first --- ... --- block."""
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    assert match is not None, (
        "No valid YAML frontmatter (--- ... ---) found in test-writer.agent.md"
    )
    return match.group(1)


# ---------------------------------------------------------------------------
# Script existence — fails RED until builder creates the file
# ---------------------------------------------------------------------------


class TestFromAC_ScriptExists:
    """Script must be created at the expected path with content (AC prerequisite)."""

    def test_deny_src_writes_ps1_exists(self) -> None:
        """deny-src-writes.ps1 must exist on disk."""
        assert _SCRIPT_PATH.exists(), (
            f"deny-src-writes.ps1 not found at {_SCRIPT_PATH}. "
            "Builder must create scripts/hooks/deny-src-writes.ps1."
        )

    def test_script_is_nonempty(self) -> None:
        """Script file must have content — an empty file cannot implement the guard."""
        assert _SCRIPT_PATH.exists(), (
            f"deny-src-writes.ps1 not found at {_SCRIPT_PATH}."
        )
        assert _SCRIPT_PATH.stat().st_size > 0, (
            "deny-src-writes.ps1 exists but is empty — builder must implement it."
        )


# ---------------------------------------------------------------------------
# Path guard behaviour — Windows/PowerShell required
# ---------------------------------------------------------------------------


@pytest.mark.skipif(sys.platform != "win32", reason="PowerShell hook requires Windows")
class TestFromAC_PathGuardBehavior:
    """Behavioural tests via subprocess.  All fail RED because script doesn't exist."""

    # --- AC1b/AC1c: create_file path routing ---

    def test_create_file_tests_path_is_allowed(self) -> None:
        """AC1b: create_file with a tests/ path must return {} (allowed)."""
        _, output = _run_hook({
            "tool_name": "create_file",
            "tool_input": {"filePath": "tests/test_foo.py"},
        })
        assert output == {}, (
            f"create_file with tests/ path must return {{}} (allowed), got: {output!r}"
        )

    def test_create_file_packages_path_is_denied(self) -> None:
        """AC1c: create_file with a packages/ path must be denied."""
        _, output = _run_hook({
            "tool_name": "create_file",
            "tool_input": {"filePath": "packages/foo/bar.py"},
        })
        assert _is_denied(output), (
            f"create_file with packages/ path must be denied (allow-list), got: {output!r}"
        )

    def test_create_file_src_path_is_denied(self) -> None:
        """AC1c boundary: create_file with src/ path must also be denied."""
        _, output = _run_hook({
            "tool_name": "create_file",
            "tool_input": {"filePath": "src/module/impl.py"},
        })
        assert _is_denied(output), (
            f"create_file with src/ path must be denied, got: {output!r}"
        )

    # --- AC1a: backslash normalization ---

    def test_create_file_backslash_tests_path_is_allowed(self) -> None:
        """AC1a: backslash path tests\\foo.py must be normalized to tests/foo.py → allowed."""
        _, output = _run_hook({
            "tool_name": "create_file",
            "tool_input": {"filePath": "tests\\test_bar.py"},
        })
        assert output == {}, (
            f"Backslash tests\\ path should be normalized and allowed, got: {output!r}"
        )

    def test_create_file_backslash_packages_path_is_denied(self) -> None:
        """AC1a boundary: backslash packages\\ path must be denied after normalization."""
        _, output = _run_hook({
            "tool_name": "create_file",
            "tool_input": {"filePath": "packages\\foo\\bar.py"},
        })
        assert _is_denied(output), (
            f"Backslash packages\\ path must be denied after normalization, got: {output!r}"
        )

    # --- AC1d/AC1e: replace_string_in_file path routing ---

    def test_replace_string_in_file_tests_path_is_allowed(self) -> None:
        """AC1d: replace_string_in_file with tests/ filePath must return {}."""
        _, output = _run_hook({
            "tool_name": "replace_string_in_file",
            "tool_input": {"filePath": "tests/test_existing.py", "oldString": "x", "newString": "y"},
        })
        assert output == {}, (
            f"replace_string_in_file with tests/ path must be allowed, got: {output!r}"
        )

    def test_replace_string_in_file_packages_path_is_denied(self) -> None:
        """AC1e: replace_string_in_file with packages/ filePath must be denied."""
        _, output = _run_hook({
            "tool_name": "replace_string_in_file",
            "tool_input": {"filePath": "packages/foo/impl.py", "oldString": "x", "newString": "y"},
        })
        assert _is_denied(output), (
            f"replace_string_in_file with packages/ path must be denied, got: {output!r}"
        )

    # --- AC1f/AC1g: multi_replace_string_in_file — replacements array ---

    def test_multi_replace_all_tests_paths_is_allowed(self) -> None:
        """AC1f: all replacements pointing to tests/ must return {}."""
        _, output = _run_hook({
            "tool_name": "multi_replace_string_in_file",
            "tool_input": {
                "replacements": [
                    {"filePath": "tests/test_a.py", "oldString": "a", "newString": "b"},
                    {"filePath": "tests/test_b.py", "oldString": "c", "newString": "d"},
                ],
            },
        })
        assert output == {}, (
            f"multi_replace with all tests/ paths must be allowed, got: {output!r}"
        )

    def test_multi_replace_any_non_tests_path_is_denied(self) -> None:
        """AC1g: any replacement targeting non-tests/ must deny the whole call."""
        _, output = _run_hook({
            "tool_name": "multi_replace_string_in_file",
            "tool_input": {
                "replacements": [
                    {"filePath": "tests/test_a.py", "oldString": "a", "newString": "b"},
                    {"filePath": "packages/foo/impl.py", "oldString": "c", "newString": "d"},
                ],
            },
        })
        assert _is_denied(output), (
            f"multi_replace with any non-tests/ path must be denied, got: {output!r}"
        )

    # --- AC1h/AC1i: create_directory dirPath routing ---

    def test_create_directory_tests_dirpath_is_allowed(self) -> None:
        """AC1h: create_directory with tests/ dirPath must return {}."""
        _, output = _run_hook({
            "tool_name": "create_directory",
            "tool_input": {"dirPath": "tests/new_subdir"},
        })
        assert output == {}, (
            f"create_directory with tests/ dirPath must be allowed, got: {output!r}"
        )

    def test_create_directory_packages_dirpath_is_denied(self) -> None:
        """AC1i: create_directory with packages/ dirPath must be denied."""
        _, output = _run_hook({
            "tool_name": "create_directory",
            "tool_input": {"dirPath": "packages/new_module"},
        })
        assert _is_denied(output), (
            f"create_directory with packages/ dirPath must be denied, got: {output!r}"
        )

    # --- AC2e: apply_patch is NOT gated ---

    def test_apply_patch_is_not_gated_and_returns_empty_json(self) -> None:
        """AC2e: apply_patch is excluded from write-tools list — must return {} regardless of path."""
        _, output = _run_hook({
            "tool_name": "apply_patch",
            "tool_input": {"filePath": "packages/evil.py"},
        })
        assert output == {}, (
            f"apply_patch must not be gated (excluded per AC2) — must return {{}}, got: {output!r}"
        )

    # --- AC2f/AC2g/AC2h: non-write tool pass-through ---

    def test_run_in_terminal_returns_empty_json(self) -> None:
        """AC2f: run_in_terminal is opaque (known limitation) — must return {}."""
        _, output = _run_hook({"tool_name": "run_in_terminal", "tool_input": {}})
        assert output == {}

    def test_read_file_returns_empty_json(self) -> None:
        """AC2g: read_file is not a write tool — must return {}."""
        _, output = _run_hook({"tool_name": "read_file", "tool_input": {}})
        assert output == {}

    def test_unknown_tool_name_returns_empty_json(self) -> None:
        """AC2h: unknown/future tool_name values must pass through — return {}."""
        _, output = _run_hook({"tool_name": "some_future_tool", "tool_input": {}})
        assert output == {}

    # --- AC5: malformed/empty input safety ---

    def test_malformed_stdin_json_returns_empty_json(self) -> None:
        """AC5a: malformed stdin must not crash the script — returns {}."""
        if not _SCRIPT_PATH.exists():
            raise FileNotFoundError(
                f"deny-src-writes.ps1 not found at {_SCRIPT_PATH}."
            )
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
        assert output == {}, (
            f"Malformed JSON input must produce {{}} output, got: {output!r}"
        )

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
        _, output = _run_hook({
            "tool_name": "create_file",
            "tool_input": {"content": "hello"},
        })
        assert output == {}, (
            f"create_file with no filePath must return {{}} (nothing to deny), got: {output!r}"
        )

    def test_write_tool_with_empty_string_filepath_returns_empty_json(self) -> None:
        """AC5e: write tool with filePath='' — empty path → {} (pass-through)."""
        _, output = _run_hook({
            "tool_name": "create_file",
            "tool_input": {"filePath": ""},
        })
        assert output == {}, (
            f"create_file with empty filePath must return {{}} (pass-through), got: {output!r}"
        )

    # --- Boundary conditions ---

    def test_path_starting_with_tests_not_tests_slash_is_denied(self) -> None:
        """Boundary1: path 'testscripts/foo.py' starts with 'tests' but not 'tests/' → denied."""
        _, output = _run_hook({
            "tool_name": "create_file",
            "tool_input": {"filePath": "testscripts/foo.py"},
        })
        assert _is_denied(output), (
            f"Path 'testscripts/foo.py' must be denied (allow-list requires prefix 'tests/'). "
            f"Got: {output!r}"
        )

    def test_multi_replace_empty_replacements_returns_empty_json(self) -> None:
        """Boundary3: empty replacements array → no paths extracted → {} (pass-through)."""
        _, output = _run_hook({
            "tool_name": "multi_replace_string_in_file",
            "tool_input": {"replacements": []},
        })
        assert output == {}, (
            f"multi_replace with empty replacements must return {{}} (no paths to check), got: {output!r}"
        )

    # --- Deny response structure ---

    def test_deny_response_has_hook_specific_output_key(self) -> None:
        """AC deny structure: response must nest under hookSpecificOutput."""
        _, output = _run_hook({
            "tool_name": "create_file",
            "tool_input": {"filePath": "packages/evil.py"},
        })
        assert "hookSpecificOutput" in output, (
            f"Deny response must contain 'hookSpecificOutput' key, got: {output!r}"
        )

    def test_deny_reason_is_nonempty(self) -> None:
        """AC deny structure: permissionDecisionReason must be non-empty string."""
        _, output = _run_hook({
            "tool_name": "create_file",
            "tool_input": {"filePath": "packages/evil.py"},
        })
        reason = output.get("hookSpecificOutput", {}).get("permissionDecisionReason", "")
        assert reason, (
            f"permissionDecisionReason must be non-empty when denying a write, got: {output!r}"
        )

    def test_stdout_is_always_valid_json_for_allowed_call(self) -> None:
        """Contract: stdout must always be valid JSON — for allowed calls returns {}."""
        if not _SCRIPT_PATH.exists():
            raise FileNotFoundError(
                f"deny-src-writes.ps1 not found at {_SCRIPT_PATH}."
            )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-File", str(_SCRIPT_PATH)],
            input=json.dumps({"tool_name": "create_file", "tool_input": {"filePath": "tests/foo.py"}}),
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
            pytest.fail(
                f"Script stdout is not valid JSON for allowed call: {stdout!r}\nError: {exc}"
            )
        assert isinstance(parsed, dict), f"Output must be a JSON object, got: {parsed!r}"

    def test_stdout_is_always_valid_json_for_denied_call(self) -> None:
        """Contract: stdout must always be valid JSON — for denied calls returns deny object."""
        if not _SCRIPT_PATH.exists():
            raise FileNotFoundError(
                f"deny-src-writes.ps1 not found at {_SCRIPT_PATH}."
            )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-File", str(_SCRIPT_PATH)],
            input=json.dumps({"tool_name": "create_file", "tool_input": {"filePath": "packages/bad.py"}}),
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
            pytest.fail(
                f"Script stdout is not valid JSON for denied call: {stdout!r}\nError: {exc}"
            )
        assert isinstance(parsed, dict), f"Output must be a JSON object, got: {parsed!r}"


# ---------------------------------------------------------------------------
# test-writer.agent.md frontmatter — AC3, AC4, AC6
# ---------------------------------------------------------------------------


class TestFromAC_TestWriterAgentHooks:
    """test-writer.agent.md must gain a PreToolUse hook and lose edit/rename."""

    def _content(self) -> str:
        assert _AGENT_PATH.exists(), f"Agent file not found at {_AGENT_PATH}"
        return _AGENT_PATH.read_text(encoding="utf-8")

    def _frontmatter(self) -> str:
        return _extract_frontmatter(self._content())

    # --- AC3: hooks section ---

    def test_frontmatter_has_hooks_section(self) -> None:
        """AC3a: test-writer.agent.md frontmatter must contain a hooks: key."""
        fm = self._frontmatter()
        assert re.search(r"^hooks:", fm, re.MULTILINE), (
            "test-writer.agent.md frontmatter is missing the 'hooks:' key. "
            "Builder must add a PreToolUse hooks section."
        )

    def test_frontmatter_has_pretooluse_entry(self) -> None:
        """AC3b: hooks: section must contain a PreToolUse entry."""
        fm = self._frontmatter()
        assert "PreToolUse" in fm, (
            "test-writer.agent.md hooks: section is missing a PreToolUse entry."
        )

    def test_pretooluse_hook_type_is_command(self) -> None:
        """AC3c: PreToolUse hook must specify type: command."""
        fm = self._frontmatter()
        assert re.search(r"type:\s*command", fm), (
            "test-writer.agent.md PreToolUse hook must specify 'type: command'."
        )

    def test_pretooluse_hook_command_references_deny_src_writes(self) -> None:
        """AC3d: PreToolUse hook command must reference deny-src-writes.ps1."""
        fm = self._frontmatter()
        assert "deny-src-writes.ps1" in fm, (
            "test-writer.agent.md PreToolUse hook command must point to deny-src-writes.ps1."
        )

    # --- AC4: edit/rename removed from tools list ---

    def test_tools_list_does_not_contain_edit_rename(self) -> None:
        """AC4: edit/rename must be removed from test-writer tools to prevent bypass."""
        fm = self._frontmatter()
        # Check raw frontmatter text — edit/rename is a compound entry
        assert "edit/rename" not in fm, (
            "test-writer.agent.md tools list must not contain 'edit/rename'. "
            "Builder must remove it to prevent bypass of the path guard."
        )

    # --- AC6: valid YAML frontmatter ---

    def test_frontmatter_is_parseable_yaml_with_pretooluse_hook(self) -> None:
        """AC6: frontmatter must parse as valid YAML and contain hooks after builder changes."""
        import yaml  # noqa: PLC0415

        fm = self._frontmatter()
        try:
            parsed = yaml.safe_load(fm)
        except yaml.YAMLError as exc:
            pytest.fail(
                f"test-writer.agent.md frontmatter is not valid YAML: {exc}"
            )
        assert isinstance(parsed, dict), (
            f"Parsed YAML frontmatter must be a dict, got: {type(parsed)}"
        )
        # Compound check: hooks must be present (causes RED-phase failure until builder acts)
        assert "hooks" in parsed, (
            "Frontmatter parsed but missing 'hooks:' key — "
            "builder must add the PreToolUse hooks section."
        )
        hooks = parsed["hooks"]
        assert "PreToolUse" in hooks, (
            f"hooks section must contain PreToolUse key, got: {hooks!r}"
        )

    def test_frontmatter_no_duplicate_keys(self) -> None:
        """AC6 regression: frontmatter must not gain duplicate YAML keys after edit."""
        fm = self._frontmatter()
        # Fail pre-impl by checking hooks: is present first
        assert "hooks:" in fm, (
            "Builder must add the hooks: section — no duplicate-key check is meaningful "
            "before the hook is added."
        )
        top_level_keys = re.findall(r"^([a-zA-Z][a-zA-Z0-9_-]*):", fm, re.MULTILINE)
        seen: set[str] = set()
        duplicates: list[str] = []
        for key in top_level_keys:
            if key in seen:
                duplicates.append(key)
            seen.add(key)
        assert not duplicates, (
            f"Duplicate YAML keys found in test-writer.agent.md frontmatter: {duplicates}"
        )


# ---------------------------------------------------------------------------
# Builder-discovered tests — security fix (review pass #1)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(sys.platform != "win32", reason="PowerShell hook requires Windows")
class TestBuilderDiscovered:
    """Reviewer-identified security bypass: path with /tests/ sub-segment must be denied.

    Before fix: $isInTests used `-or ($normalized -match '/tests/')` which allowed
    paths like `packages/tests/evil.py` to bypass the allow-list guard.
    After fix: only `$normalized.StartsWith('tests/')` is used.
    """

    def test_packages_tests_subdir_path_is_denied(self) -> None:
        """packages/tests/evil.py must be denied — /tests/ sub-segment bypass removed."""
        _, output = _run_hook({
            "tool_name": "create_file",
            "tool_input": {"filePath": "packages/tests/evil.py"},
        })
        assert _is_denied(output), (
            f"packages/tests/evil.py must be denied (allow-list: prefix 'tests/' only). "
            f"Got: {output!r}"
        )

    def test_src_lib_tests_subdir_path_is_denied(self) -> None:
        """src/lib/tests/backdoor.py must also be denied — /tests/ sub-segment bypass removed."""
        _, output = _run_hook({
            "tool_name": "create_file",
            "tool_input": {"filePath": "src/lib/tests/backdoor.py"},
        })
        assert _is_denied(output), (
            f"src/lib/tests/backdoor.py must be denied (allow-list: prefix 'tests/' only). "
            f"Got: {output!r}"
        )
