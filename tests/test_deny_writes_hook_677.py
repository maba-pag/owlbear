"""Tests for task #677: Add deny-writes hook to read-only agents (auditor, code-reader, challenger).

Contract-level tests for:
1. auditor.agent.md frontmatter contains a valid PreToolUse hooks section
2. code-reader.agent.md frontmatter contains a valid PreToolUse hooks section
3. challenger.agent.md frontmatter contains a valid PreToolUse hooks section
4. deny-writes.ps1 comment and permissionDecisionReason are generalized (no agent name)

AC coverage:
  AC1: auditor.agent.md frontmatter contains hooks: with PreToolUse entry (type: command, deny-writes.ps1)
  AC2: code-reader.agent.md frontmatter contains hooks: with PreToolUse entry (type: command, deny-writes.ps1)
  AC3: challenger.agent.md frontmatter contains hooks: with PreToolUse entry (type: command, deny-writes.ps1)
  AC4a: .owlbear/hooks/deny-writes.ps1 comment header does not reference a specific agent name
  AC4b+AC4c: .owlbear/hooks/deny-writes.ps1 permissionDecisionReason contains "read-only" AND does not contain "reviewer"
  AC4d: seed/.owlbear/hooks/deny-writes.ps1 comment header does not reference a specific agent name
  AC4e+AC4f: seed/.owlbear/hooks/deny-writes.ps1 permissionDecisionReason contains "read-only" AND does not contain "reviewer"
  AC6:  Each agent's frontmatter parses as valid YAML containing a hooks.PreToolUse section
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.slow

_REPO_ROOT = Path(__file__).parent.parent
_SCRIPT_PATH = _REPO_ROOT / ".owlbear" / "hooks" / "deny-writes.ps1"
_SEED_SCRIPT_PATH = _REPO_ROOT / "seed" / ".owlbear" / "hooks" / "deny-writes.ps1"
_AUDITOR_AGENT = _REPO_ROOT / "share" / "agents" / "auditor.agent.md"
_CODE_READER_AGENT = _REPO_ROOT / "share" / "agents" / "code-reader.agent.md"
_CHALLENGER_AGENT = _REPO_ROOT / "share" / "agents" / "challenger.agent.md"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_frontmatter(content: str, agent_path: str) -> str:
    """Return the YAML text between the first --- ... --- block."""
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    assert match is not None, (
        f"No valid YAML frontmatter (--- ... ---) found in {agent_path}"
    )
    return match.group(1)


# ---------------------------------------------------------------------------
# AC1 — auditor.agent.md frontmatter
# ---------------------------------------------------------------------------


class TestFromAC_AuditorAgentHooks:
    """AC1: auditor.agent.md must contain a valid PreToolUse hooks section referencing deny-writes.ps1."""

    def _frontmatter(self) -> str:
        content = _AUDITOR_AGENT.read_text(encoding="utf-8")
        return _extract_frontmatter(content, str(_AUDITOR_AGENT))

    def test_frontmatter_has_hooks_section(self) -> None:
        """AC1: auditor.agent.md frontmatter must contain a hooks: key."""
        fm = self._frontmatter()
        assert re.search(r"^hooks:", fm, re.MULTILINE), (
            "auditor.agent.md frontmatter is missing the 'hooks:' key. "
            "Builder must add a PreToolUse hooks section."
        )

    def test_frontmatter_has_pretooluse_entry(self) -> None:
        """AC1: hooks: section must contain a PreToolUse entry."""
        fm = self._frontmatter()
        assert "PreToolUse" in fm, (
            "auditor.agent.md frontmatter hooks: section is missing a PreToolUse entry."
        )

    def test_pretooluse_hook_type_is_command(self) -> None:
        """AC1: PreToolUse hook must specify type: command."""
        fm = self._frontmatter()
        assert re.search(r"type:\s*command", fm), (
            "auditor.agent.md PreToolUse hook must specify 'type: command'."
        )

    def test_pretooluse_hook_command_references_deny_writes(self) -> None:
        """AC1: PreToolUse hook command must reference deny-writes.ps1."""
        fm = self._frontmatter()
        assert "deny-writes.ps1" in fm, (
            "auditor.agent.md PreToolUse hook command must point to deny-writes.ps1."
        )

    def test_frontmatter_is_parseable_yaml_with_pretooluse_hook(self) -> None:
        """AC6: auditor.agent.md frontmatter must parse as valid YAML with hooks.PreToolUse."""
        import yaml  # noqa: PLC0415

        fm = self._frontmatter()
        try:
            parsed = yaml.safe_load(fm)
        except yaml.YAMLError as exc:
            pytest.fail(f"auditor.agent.md frontmatter is not valid YAML: {exc}")
        assert isinstance(parsed, dict), (
            f"Parsed YAML frontmatter must be a dict, got: {type(parsed)}"
        )
        assert "hooks" in parsed, (
            "Frontmatter parsed successfully but is missing 'hooks:' key — "
            "builder must add the PreToolUse hooks section."
        )
        hooks = parsed["hooks"]
        assert "PreToolUse" in hooks, (
            f"hooks section must contain PreToolUse key, got: {hooks!r}"
        )

    def test_pretooluse_hook_references_owlbear_hooks_path(self) -> None:
        """AC1: hook command must reference the .owlbear/hooks/ path."""
        fm = self._frontmatter()
        assert ".owlbear/hooks/deny-writes.ps1" in fm, (
            "auditor.agent.md PreToolUse hook must specifically reference "
            "'.owlbear/hooks/deny-writes.ps1' (not a different path)."
        )


# ---------------------------------------------------------------------------
# AC2 — code-reader.agent.md frontmatter
# ---------------------------------------------------------------------------


class TestFromAC_CodeReaderAgentHooks:
    """AC2: code-reader.agent.md must contain a valid PreToolUse hooks section referencing deny-writes.ps1."""

    def _frontmatter(self) -> str:
        content = _CODE_READER_AGENT.read_text(encoding="utf-8")
        return _extract_frontmatter(content, str(_CODE_READER_AGENT))

    def test_frontmatter_has_hooks_section(self) -> None:
        """AC2: code-reader.agent.md frontmatter must contain a hooks: key."""
        fm = self._frontmatter()
        assert re.search(r"^hooks:", fm, re.MULTILINE), (
            "code-reader.agent.md frontmatter is missing the 'hooks:' key. "
            "Builder must add a PreToolUse hooks section."
        )

    def test_frontmatter_has_pretooluse_entry(self) -> None:
        """AC2: hooks: section must contain a PreToolUse entry."""
        fm = self._frontmatter()
        assert "PreToolUse" in fm, (
            "code-reader.agent.md frontmatter hooks: section is missing a PreToolUse entry."
        )

    def test_pretooluse_hook_type_is_command(self) -> None:
        """AC2: PreToolUse hook must specify type: command."""
        fm = self._frontmatter()
        assert re.search(r"type:\s*command", fm), (
            "code-reader.agent.md PreToolUse hook must specify 'type: command'."
        )

    def test_pretooluse_hook_command_references_deny_writes(self) -> None:
        """AC2: PreToolUse hook command must reference deny-writes.ps1."""
        fm = self._frontmatter()
        assert "deny-writes.ps1" in fm, (
            "code-reader.agent.md PreToolUse hook command must point to deny-writes.ps1."
        )

    def test_frontmatter_is_parseable_yaml_with_pretooluse_hook(self) -> None:
        """AC6: code-reader.agent.md frontmatter must parse as valid YAML with hooks.PreToolUse."""
        import yaml  # noqa: PLC0415

        fm = self._frontmatter()
        try:
            parsed = yaml.safe_load(fm)
        except yaml.YAMLError as exc:
            pytest.fail(f"code-reader.agent.md frontmatter is not valid YAML: {exc}")
        assert isinstance(parsed, dict), (
            f"Parsed YAML frontmatter must be a dict, got: {type(parsed)}"
        )
        assert "hooks" in parsed, (
            "Frontmatter parsed successfully but is missing 'hooks:' key — "
            "builder must add the PreToolUse hooks section."
        )
        hooks = parsed["hooks"]
        assert "PreToolUse" in hooks, (
            f"hooks section must contain PreToolUse key, got: {hooks!r}"
        )

    def test_pretooluse_hook_references_owlbear_hooks_path(self) -> None:
        """AC2: hook command must reference the .owlbear/hooks/ path."""
        fm = self._frontmatter()
        assert ".owlbear/hooks/deny-writes.ps1" in fm, (
            "code-reader.agent.md PreToolUse hook must specifically reference "
            "'.owlbear/hooks/deny-writes.ps1' (not a different path)."
        )


# ---------------------------------------------------------------------------
# AC3 — challenger.agent.md frontmatter
# ---------------------------------------------------------------------------


class TestFromAC_ChallengerAgentHooks:
    """AC3: challenger.agent.md must contain a valid PreToolUse hooks section referencing deny-writes.ps1."""

    def _frontmatter(self) -> str:
        content = _CHALLENGER_AGENT.read_text(encoding="utf-8")
        return _extract_frontmatter(content, str(_CHALLENGER_AGENT))

    def test_frontmatter_has_hooks_section(self) -> None:
        """AC3: challenger.agent.md frontmatter must contain a hooks: key."""
        fm = self._frontmatter()
        assert re.search(r"^hooks:", fm, re.MULTILINE), (
            "challenger.agent.md frontmatter is missing the 'hooks:' key. "
            "Builder must add a PreToolUse hooks section."
        )

    def test_frontmatter_has_pretooluse_entry(self) -> None:
        """AC3: hooks: section must contain a PreToolUse entry."""
        fm = self._frontmatter()
        assert "PreToolUse" in fm, (
            "challenger.agent.md frontmatter hooks: section is missing a PreToolUse entry."
        )

    def test_pretooluse_hook_type_is_command(self) -> None:
        """AC3: PreToolUse hook must specify type: command."""
        fm = self._frontmatter()
        assert re.search(r"type:\s*command", fm), (
            "challenger.agent.md PreToolUse hook must specify 'type: command'."
        )

    def test_pretooluse_hook_command_references_deny_writes(self) -> None:
        """AC3: PreToolUse hook command must reference deny-writes.ps1."""
        fm = self._frontmatter()
        assert "deny-writes.ps1" in fm, (
            "challenger.agent.md PreToolUse hook command must point to deny-writes.ps1."
        )

    def test_frontmatter_is_parseable_yaml_with_pretooluse_hook(self) -> None:
        """AC6: challenger.agent.md frontmatter must parse as valid YAML with hooks.PreToolUse."""
        import yaml  # noqa: PLC0415

        fm = self._frontmatter()
        try:
            parsed = yaml.safe_load(fm)
        except yaml.YAMLError as exc:
            pytest.fail(f"challenger.agent.md frontmatter is not valid YAML: {exc}")
        assert isinstance(parsed, dict), (
            f"Parsed YAML frontmatter must be a dict, got: {type(parsed)}"
        )
        assert "hooks" in parsed, (
            "Frontmatter parsed successfully but is missing 'hooks:' key — "
            "builder must add the PreToolUse hooks section."
        )
        hooks = parsed["hooks"]
        assert "PreToolUse" in hooks, (
            f"hooks section must contain PreToolUse key, got: {hooks!r}"
        )

    def test_pretooluse_hook_references_owlbear_hooks_path(self) -> None:
        """AC3: hook command must reference the .owlbear/hooks/ path."""
        fm = self._frontmatter()
        assert ".owlbear/hooks/deny-writes.ps1" in fm, (
            "challenger.agent.md PreToolUse hook must specifically reference "
            "'.owlbear/hooks/deny-writes.ps1' (not a different path)."
        )


# ---------------------------------------------------------------------------
# AC4 — deny-writes.ps1 must use generalized (agent-agnostic) message
# ---------------------------------------------------------------------------


class TestFromAC_GeneralizedHookMessage:
    """AC4: deny-writes.ps1 in both .owlbear/ and seed/ must use generic phrasing
    that does not reference a specific agent name."""

    def test_main_script_comment_does_not_reference_reviewer(self) -> None:
        """AC4a: .owlbear/hooks/deny-writes.ps1 comment header must not say 'reviewer'."""
        assert _SCRIPT_PATH.exists(), f"deny-writes.ps1 not found at {_SCRIPT_PATH}."
        content = _SCRIPT_PATH.read_text(encoding="utf-8")
        # Extract the first line comment header
        first_line = content.splitlines()[0]
        assert "reviewer" not in first_line.lower(), (
            f"deny-writes.ps1 comment header still references 'reviewer': {first_line!r}. "
            "Builder must generalize the comment header to not name a specific agent."
        )

    def test_main_script_reason_does_not_contain_reviewer(self) -> None:
        """AC4c: .owlbear/hooks/deny-writes.ps1 permissionDecisionReason must not say 'reviewer'."""
        assert _SCRIPT_PATH.exists(), f"deny-writes.ps1 not found at {_SCRIPT_PATH}."
        content = _SCRIPT_PATH.read_text(encoding="utf-8")
        # Find the permissionDecisionReason line
        reason_match = re.search(r"permissionDecisionReason\s*=\s*['\"](.+?)['\"]", content)
        assert reason_match is not None, (
            "deny-writes.ps1 does not contain a permissionDecisionReason assignment — "
            "builder must ensure the script retains this field."
        )
        reason_text = reason_match.group(1)
        assert "reviewer" not in reason_text.lower(), (
            f"permissionDecisionReason still contains 'reviewer': {reason_text!r}. "
            "Builder must generalize to generic phrasing (e.g., 'This agent is read-only.')."
        )

    def test_main_script_reason_contains_read_only_and_not_reviewer(self) -> None:
        """AC4b+AC4c compound: permissionDecisionReason must contain 'read-only' AND not 'reviewer'."""
        assert _SCRIPT_PATH.exists(), f"deny-writes.ps1 not found at {_SCRIPT_PATH}."
        content = _SCRIPT_PATH.read_text(encoding="utf-8")
        reason_match = re.search(r"permissionDecisionReason\s*=\s*['\"](.+?)['\"]", content)
        assert reason_match is not None, (
            "deny-writes.ps1 does not contain a permissionDecisionReason assignment."
        )
        reason_text = reason_match.group(1)
        assert "read-only" in reason_text.lower() or "read only" in reason_text.lower(), (
            f"permissionDecisionReason must use generic 'read-only' phrasing, got: {reason_text!r}."
        )
        assert "reviewer" not in reason_text.lower(), (
            f"permissionDecisionReason must be generalized — must not name 'reviewer': {reason_text!r}."
        )

    def test_seed_script_comment_does_not_reference_reviewer(self) -> None:
        """AC4d: seed/.owlbear/hooks/deny-writes.ps1 comment header must not say 'reviewer'."""
        assert _SEED_SCRIPT_PATH.exists(), (
            f"seed deny-writes.ps1 not found at {_SEED_SCRIPT_PATH}."
        )
        content = _SEED_SCRIPT_PATH.read_text(encoding="utf-8")
        first_line = content.splitlines()[0]
        assert "reviewer" not in first_line.lower(), (
            f"seed/deny-writes.ps1 comment header still references 'reviewer': {first_line!r}. "
            "Builder must generalize the seed copy to match the main copy."
        )

    def test_seed_script_reason_does_not_contain_reviewer(self) -> None:
        """AC4f: seed/.owlbear/hooks/deny-writes.ps1 permissionDecisionReason must not say 'reviewer'."""
        assert _SEED_SCRIPT_PATH.exists(), (
            f"seed deny-writes.ps1 not found at {_SEED_SCRIPT_PATH}."
        )
        content = _SEED_SCRIPT_PATH.read_text(encoding="utf-8")
        reason_match = re.search(r"permissionDecisionReason\s*=\s*['\"](.+?)['\"]", content)
        assert reason_match is not None, (
            "seed/deny-writes.ps1 does not contain a permissionDecisionReason assignment."
        )
        reason_text = reason_match.group(1)
        assert "reviewer" not in reason_text.lower(), (
            f"seed permissionDecisionReason still contains 'reviewer': {reason_text!r}. "
            "Builder must update the seed copy to match the generalized main hook."
        )

    def test_seed_script_reason_contains_read_only_and_not_reviewer(self) -> None:
        """AC4e+AC4f compound: seed permissionDecisionReason must contain 'read-only' AND not 'reviewer'."""
        assert _SEED_SCRIPT_PATH.exists(), (
            f"seed deny-writes.ps1 not found at {_SEED_SCRIPT_PATH}."
        )
        content = _SEED_SCRIPT_PATH.read_text(encoding="utf-8")
        reason_match = re.search(r"permissionDecisionReason\s*=\s*['\"](.+?)['\"]", content)
        assert reason_match is not None, (
            "seed/deny-writes.ps1 does not contain a permissionDecisionReason assignment."
        )
        reason_text = reason_match.group(1)
        assert "read-only" in reason_text.lower() or "read only" in reason_text.lower(), (
            f"seed permissionDecisionReason must use generic 'read-only' phrasing, got: {reason_text!r}."
        )
        assert "reviewer" not in reason_text.lower(), (
            f"seed permissionDecisionReason must be generalized — must not name 'reviewer': {reason_text!r}."
        )

    @pytest.mark.skipif(sys.platform != "win32", reason="PowerShell hook requires Windows")
    def test_runtime_reason_does_not_contain_reviewer(self) -> None:
        """AC4 (runtime): deny-writes.ps1 runtime output must not mention 'reviewer'."""
        import json  # noqa: PLC0415
        import subprocess  # noqa: PLC0415

        if not _SCRIPT_PATH.exists():
            pytest.fail(f"deny-writes.ps1 not found at {_SCRIPT_PATH}.")
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
            output = json.loads(stdout) if stdout else {}
        except json.JSONDecodeError:
            output = {"_raw": stdout}
        reason = output.get("hookSpecificOutput", {}).get("permissionDecisionReason", "")
        assert "reviewer" not in reason.lower(), (
            f"Runtime permissionDecisionReason still contains 'reviewer': {reason!r}. "
            "Builder must update the script message to generic phrasing."
        )
