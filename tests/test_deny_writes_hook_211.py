"""Tests for task #211: Add preToolUse read-only guard hook to reviewer agent (Phase 2).

Contract-level tests for:
1. scripts/hooks/deny-writes.ps1 script behavior (PowerShell, Windows only)
2. agents/reviewer.agent.md PreToolUse hooks frontmatter

Assumed PreToolUse stdin JSON format (VS Code hooks spec):
  {
    "tool_name": "<tool_name>",
    "tool_input": { ... }
  }

AC coverage:
  AC1a: agents/reviewer.agent.md frontmatter contains a hooks: section
  AC1b: hooks: section contains a PreToolUse entry
  AC1c: PreToolUse hook has type: command
  AC1d: PreToolUse hook command references deny-writes.ps1
  AC2a: scripts/hooks/deny-writes.ps1 exists at expected path
  AC2b: script file is non-empty
  AC2c: create_file → hookSpecificOutput.permissionDecision = "deny"
  AC2d: replace_string_in_file → permissionDecision = "deny"
  AC2e: multi_replace_string_in_file → permissionDecision = "deny"
  AC2f: apply_patch → permissionDecision = "deny"
  AC2g: create_directory → permissionDecision = "deny"
  AC3a: deny response is nested under hookSpecificOutput key
  AC3b: hookSpecificOutput.permissionDecisionReason is non-empty and mentions reviewer or read-only
  AC4a: read_file → returns empty JSON {}
  AC4b: semantic_search → returns empty JSON {}
  AC4c: unknown tool_name → returns empty JSON {}
  AC6:  reviewer.agent.md tools: list has no write tools (no conflict); hooks section must be present
  AC7:  reviewer.agent.md frontmatter parses as valid YAML and contains the hooks section
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).parent.parent
_SCRIPT_PATH = _REPO_ROOT / "scripts" / "hooks" / "deny-writes.ps1"
_REVIEWER_AGENT = _REPO_ROOT / ".github" / "agents" / "reviewer.agent.md"

# Write tools that the hook must deny (AC2)
_WRITE_TOOLS = [
    "create_file",
    "replace_string_in_file",
    "multi_replace_string_in_file",
    "apply_patch",
    "create_directory",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_hook(stdin_data: dict, *, timeout: int = 30) -> tuple[int, dict]:
    """Run deny-writes.ps1 with the given stdin JSON.

    Returns (exit_code, parsed_stdout_json).
    Raises FileNotFoundError if the script does not yet exist — this makes
    RED-phase failures explicit instead of silently returning {} on a missing script.
    """
    if not _SCRIPT_PATH.exists():
        msg = (
            f"deny-writes.ps1 not found at {_SCRIPT_PATH}. "
            "Builder must create scripts/hooks/deny-writes.ps1 to make these tests pass."
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


def _extract_frontmatter(content: str) -> str:
    """Return the YAML text between the first --- ... --- block."""
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    assert match is not None, (
        "No valid YAML frontmatter (--- ... ---) found in reviewer.agent.md"
    )
    return match.group(1)


# ---------------------------------------------------------------------------
# AC2a/AC2b — deny-writes.ps1 must exist
# ---------------------------------------------------------------------------


class TestFromAC_ScriptExists:
    """AC2a/AC2b: scripts/hooks/deny-writes.ps1 must be created by the builder."""

    def test_deny_writes_ps1_exists(self) -> None:
        """AC2a: scripts/hooks/deny-writes.ps1 must exist on disk."""
        assert _SCRIPT_PATH.exists(), (
            f"deny-writes.ps1 not found at {_SCRIPT_PATH}. "
            "Builder must create scripts/hooks/deny-writes.ps1."
        )

    def test_script_is_nonempty(self) -> None:
        """AC2b: script file must have content — an empty file is not a valid hook."""
        assert _SCRIPT_PATH.exists(), f"deny-writes.ps1 not found at {_SCRIPT_PATH}."
        assert _SCRIPT_PATH.stat().st_size > 0, (
            "deny-writes.ps1 exists but is empty — builder must implement it."
        )


# ---------------------------------------------------------------------------
# AC2/AC3/AC4 — script I/O behaviour (Windows/PowerShell required)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(sys.platform != "win32", reason="PowerShell hook requires Windows")
class TestFromAC_DenyWritesBehavior:
    """Script behaviour tests exercised via subprocess on Windows.

    All tests use _run_hook() which raises FileNotFoundError if the script
    does not yet exist — making RED-phase failures clear.
    """

    # --- AC4: non-write tools return {} ---

    def test_read_file_tool_returns_empty_json(self) -> None:
        """AC4a: tool_name='read_file' is not a write tool — must return {}."""
        _, output = _run_hook({"tool_name": "read_file", "tool_input": {}})
        assert output == {}

    def test_semantic_search_returns_empty_json(self) -> None:
        """AC4b: tool_name='semantic_search' is not a write tool — must return {}."""
        _, output = _run_hook({"tool_name": "semantic_search", "tool_input": {}})
        assert output == {}

    def test_unknown_tool_name_returns_empty_json(self) -> None:
        """AC4c: unknown/future tool_name values — must return {} (pass-through)."""
        _, output = _run_hook({"tool_name": "some_future_tool", "tool_input": {}})
        assert output == {}

    def test_run_in_terminal_returns_empty_json(self) -> None:
        """AC4: run_in_terminal is a known limitation — this hook cannot intercept
        terminal writes, so it must return {} (pass-through, not a deny)."""
        _, output = _run_hook({"tool_name": "run_in_terminal", "tool_input": {}})
        assert output == {}

    # --- AC2/AC3: write tools return hookSpecificOutput.permissionDecision = "deny" ---

    def test_create_file_returns_deny_decision(self) -> None:
        """AC2c + AC3a: create_file must be denied via hookSpecificOutput.permissionDecision."""
        _, output = _run_hook({"tool_name": "create_file", "tool_input": {}})
        assert "hookSpecificOutput" in output, (
            f"Expected 'hookSpecificOutput' key in response, got: {output!r}"
        )
        assert output["hookSpecificOutput"].get("permissionDecision") == "deny", (
            f"create_file must return permissionDecision='deny'. "
            f"Got: {output['hookSpecificOutput']!r}"
        )

    def test_replace_string_in_file_returns_deny_decision(self) -> None:
        """AC2d + AC3a: replace_string_in_file must be denied."""
        _, output = _run_hook({"tool_name": "replace_string_in_file", "tool_input": {}})
        assert "hookSpecificOutput" in output, (
            f"Expected 'hookSpecificOutput' key in response, got: {output!r}"
        )
        assert output["hookSpecificOutput"].get("permissionDecision") == "deny", (
            f"replace_string_in_file must return permissionDecision='deny'. "
            f"Got: {output['hookSpecificOutput']!r}"
        )

    def test_multi_replace_string_in_file_returns_deny_decision(self) -> None:
        """AC2e + AC3a: multi_replace_string_in_file must be denied."""
        _, output = _run_hook({"tool_name": "multi_replace_string_in_file", "tool_input": {}})
        assert "hookSpecificOutput" in output, (
            f"Expected 'hookSpecificOutput' key in response, got: {output!r}"
        )
        assert output["hookSpecificOutput"].get("permissionDecision") == "deny", (
            f"multi_replace_string_in_file must return permissionDecision='deny'. "
            f"Got: {output['hookSpecificOutput']!r}"
        )

    def test_apply_patch_returns_deny_decision(self) -> None:
        """AC2f + AC3a: apply_patch must be denied."""
        _, output = _run_hook({"tool_name": "apply_patch", "tool_input": {}})
        assert "hookSpecificOutput" in output, (
            f"Expected 'hookSpecificOutput' key in response, got: {output!r}"
        )
        assert output["hookSpecificOutput"].get("permissionDecision") == "deny", (
            f"apply_patch must return permissionDecision='deny'. "
            f"Got: {output['hookSpecificOutput']!r}"
        )

    def test_create_directory_returns_deny_decision(self) -> None:
        """AC2g + AC3a: create_directory must be denied (tool_name extrapolated from convention)."""
        _, output = _run_hook({"tool_name": "create_directory", "tool_input": {}})
        assert "hookSpecificOutput" in output, (
            f"Expected 'hookSpecificOutput' key in response, got: {output!r}"
        )
        assert output["hookSpecificOutput"].get("permissionDecision") == "deny", (
            f"create_directory must return permissionDecision='deny'. "
            f"Got: {output['hookSpecificOutput']!r}"
        )

    def test_deny_reason_mentions_reviewer_or_read_only(self) -> None:
        """AC3b: permissionDecisionReason must explain the reviewer is read-only."""
        _, output = _run_hook({"tool_name": "create_file", "tool_input": {}})
        assert "hookSpecificOutput" in output, (
            f"Expected 'hookSpecificOutput' key, got: {output!r}"
        )
        reason = output["hookSpecificOutput"].get("permissionDecisionReason", "")
        assert reason, "permissionDecisionReason must be non-empty"
        lower = reason.lower()
        assert "reviewer" in lower or "read-only" in lower or "read only" in lower, (
            f"permissionDecisionReason must explain the reviewer is read-only. "
            f"Got: {reason!r}"
        )

    def test_deny_reason_is_nonempty_for_all_write_tools(self) -> None:
        """AC3b boundary: every denied write tool must include a non-empty permissionDecisionReason."""
        for tool in _WRITE_TOOLS:
            _, output = _run_hook({"tool_name": tool, "tool_input": {}})
            hook_output = output.get("hookSpecificOutput", {})
            reason = hook_output.get("permissionDecisionReason", "")
            assert reason, (
                f"permissionDecisionReason must be non-empty for tool={tool!r}. "
                f"Got: {output!r}"
            )

    def test_stdout_is_valid_json_for_write_tool(self) -> None:
        """AC3: raw stdout must always be parseable JSON for a write tool call."""
        if not _SCRIPT_PATH.exists():
            pytest.fail(
                f"deny-writes.ps1 not found at {_SCRIPT_PATH}. "
                "Builder must create scripts/hooks/deny-writes.ps1."
            )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-File", str(_SCRIPT_PATH)],
            input=json.dumps({"tool_name": "create_file", "tool_input": {}}),
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
                f"Script stdout is not valid JSON for write tool: {stdout!r}\nError: {exc}"
            )
        assert isinstance(parsed, dict), (
            f"Output must be a JSON object, got: {parsed!r}"
        )

    def test_stdout_is_valid_json_for_non_write_tool(self) -> None:
        """AC4: raw stdout must always be parseable JSON (empty {}) for non-write tool."""
        if not _SCRIPT_PATH.exists():
            pytest.fail(
                f"deny-writes.ps1 not found at {_SCRIPT_PATH}. "
                "Builder must create scripts/hooks/deny-writes.ps1."
            )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-File", str(_SCRIPT_PATH)],
            input=json.dumps({"tool_name": "read_file", "tool_input": {}}),
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
                f"Script stdout is not valid JSON for non-write tool: {stdout!r}\nError: {exc}"
            )
        assert isinstance(parsed, dict), (
            f"Output must be a JSON object, got: {parsed!r}"
        )

    def test_empty_tool_name_returns_empty_json(self) -> None:
        """Edge: empty string tool_name is not a write tool — must return {}."""
        _, output = _run_hook({"tool_name": "", "tool_input": {}})
        assert output == {}

    def test_missing_tool_name_key_returns_empty_json(self) -> None:
        """Edge: stdin JSON with no tool_name key — script must not crash, returns {}."""
        _, output = _run_hook({"tool_input": {}})
        assert output == {}


# ---------------------------------------------------------------------------
# AC1 + AC6 + AC7 — reviewer.agent.md frontmatter
# ---------------------------------------------------------------------------


class TestFromAC_ReviewerAgentHooks:
    """reviewer.agent.md must gain a valid PreToolUse hooks: section."""

    def _frontmatter(self) -> str:
        content = _REVIEWER_AGENT.read_text(encoding="utf-8")
        return _extract_frontmatter(content)

    def test_frontmatter_has_hooks_section(self) -> None:
        """AC1a: reviewer.agent.md frontmatter must contain a hooks: key."""
        fm = self._frontmatter()
        assert re.search(r"^hooks:", fm, re.MULTILINE), (
            "reviewer.agent.md frontmatter is missing the 'hooks:' key. "
            "Builder must add a PreToolUse hooks section."
        )

    def test_frontmatter_has_pretooluse_entry(self) -> None:
        """AC1b: hooks: section must contain a PreToolUse entry."""
        fm = self._frontmatter()
        assert "PreToolUse" in fm, (
            "reviewer.agent.md frontmatter hooks: section is missing a PreToolUse entry."
        )

    def test_pretooluse_hook_type_is_command(self) -> None:
        """AC1c: PreToolUse hook must specify type: command."""
        fm = self._frontmatter()
        assert re.search(r"type:\s*command", fm), (
            "reviewer.agent.md PreToolUse hook must specify 'type: command'."
        )

    def test_pretooluse_hook_command_references_deny_writes(self) -> None:
        """AC1d: PreToolUse hook command: value must reference deny-writes.ps1."""
        fm = self._frontmatter()
        assert "deny-writes.ps1" in fm, (
            "reviewer.agent.md PreToolUse hook command must point to deny-writes.ps1."
        )

    def test_hooks_do_not_conflict_with_tools_list(self) -> None:
        """AC6: tools: list must have no write tools AND hooks section must be present.

        The hook is a secondary guard; the tools: list is the primary guard. Both must
        be present and consistent — no write tools in tools: list.
        """
        import yaml  # noqa: PLC0415

        fm = self._frontmatter()
        parsed = yaml.safe_load(fm)
        assert isinstance(parsed, dict), "Frontmatter must be a dict"
        # Fail if hooks not present yet (ensures this test fails pre-impl)
        assert "hooks" in parsed, (
            "Builder must add the hooks: section before this AC6 assertion is meaningful."
        )
        tools = parsed.get("tools", [])
        tools_str = str(tools).lower() if tools else ""
        found_write_tools = [t for t in _WRITE_TOOLS if t.lower() in tools_str]
        assert not found_write_tools, (
            f"reviewer.agent.md tools: list must not contain write tools: {found_write_tools}. "
            "The hooks: section is the secondary guard; the tools list is the primary guard."
        )

    def test_frontmatter_no_duplicate_keys(self) -> None:
        """AC7 (regression): reviewer.agent.md frontmatter must not gain duplicate YAML keys.

        This test fails pre-impl to satisfy RED-phase requirements by asserting that
        the hooks section is present, combining the duplicate-key check with AC1.
        """
        fm = self._frontmatter()
        # Fail if hooks not present yet
        assert "hooks:" in fm, (
            "Builder must add the hooks: section — no duplicate-key regression is meaningful "
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
            f"Duplicate YAML keys found in reviewer.agent.md frontmatter: {duplicates}"
        )

    def test_frontmatter_is_parseable_yaml_with_pretooluse_hook(self) -> None:
        """AC7: reviewer.agent.md frontmatter must parse as valid YAML after hook addition.

        Asserts both validity AND presence of the hooks/PreToolUse keys so this
        test fails pre-impl (no hooks yet) and passes once the builder is done.
        """
        import yaml  # noqa: PLC0415

        fm = self._frontmatter()
        try:
            parsed = yaml.safe_load(fm)
        except yaml.YAMLError as exc:
            pytest.fail(
                f"reviewer.agent.md frontmatter is not valid YAML: {exc}"
            )
        assert isinstance(parsed, dict), (
            f"Parsed YAML frontmatter must be a dict, got: {type(parsed)}"
        )
        # Compound check: hooks must be present for AC7 to be meaningful
        assert "hooks" in parsed, (
            "Frontmatter parsed successfully but is missing 'hooks:' key — "
            "builder must add the PreToolUse hooks section."
        )
        hooks = parsed["hooks"]
        assert "PreToolUse" in hooks, (
            f"hooks section must contain PreToolUse key, got: {hooks!r}"
        )
