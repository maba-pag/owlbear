"""Failing tests for task #118: Fix copilotMemory.enabled discrepancy in workspace settings.

AC:
  1. .vscode/settings.json contains github.copilot.chat.copilotMemory.enabled: false
  2. File remains valid JSON after the change
  3. No other settings are modified
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SETTINGS_PATH = Path(__file__).parent.parent / ".vscode" / "settings.json"

# Snapshot of top-level key count captured from pre-fix state (2026-03-29).
# The fix changes one value only — no keys may be added or removed.
_EXPECTED_KEY_COUNT = 68

# Subset of settings that must remain at known-correct values after the fix.
_PRESERVED_SETTINGS: dict[str, Any] = {
    "chat.autopilot.enabled": True,
    "chat.agent.maxRequests": 99999,
    "github.copilot.chat.agent.autoFix": True,
    "github.copilot.chat.agent.currentEditorContext.enabled": False,
    "github.copilot.chat.executionSubagent.enabled": True,
    "github.copilot.chat.executionSubagent.toolCallLimit": 50,
    "github.copilot.chat.githubMcpServer.enabled": True,
    "github.copilot.chat.searchSubagent.enabled": True,
    "github.copilot.chat.searchSubagent.toolCallLimit": 50,
    "github.copilot.chat.tools.memory.enabled": True,
    "github.copilot.chat.newWorkspaceCreation.enabled": False,
}


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def vscode_settings() -> dict[str, Any]:
    """Load and return .vscode/settings.json as a dict."""
    return json.loads(_SETTINGS_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestFromAC_CopilotMemorySetting:
    """Contract tests for #118: copilotMemory.enabled must be set to false.

    All tests include a direct assertion on the target setting so they fail
    before the builder applies the fix.
    """

    def test_copilot_memory_enabled_is_false(
        self, vscode_settings: dict[str, Any]
    ) -> None:
        """AC1: github.copilot.chat.copilotMemory.enabled must be false."""
        assert vscode_settings["github.copilot.chat.copilotMemory.enabled"] is False

    def test_settings_file_is_valid_json_and_memory_disabled(
        self, vscode_settings: dict[str, Any]
    ) -> None:
        """AC1+AC2: file is parseable JSON and the memory key holds the correct value.

        The fixture performs the parse; reaching this line proves valid JSON.
        The memory-disabled assertion makes this test fail before the fix.
        """
        assert isinstance(vscode_settings, dict)
        assert vscode_settings.get("github.copilot.chat.copilotMemory.enabled") is False

    def test_no_settings_removed_after_fix(
        self, vscode_settings: dict[str, Any]
    ) -> None:
        """AC3+AC1: top-level key count must remain at 68; no keys added or removed.

        The memory-disabled assertion makes this test fail before the fix.
        """
        assert len(vscode_settings) == _EXPECTED_KEY_COUNT
        assert vscode_settings["github.copilot.chat.copilotMemory.enabled"] is False

    def test_non_memory_settings_values_unchanged(
        self, vscode_settings: dict[str, Any]
    ) -> None:
        """AC3+AC1: unchanged settings retain their pre-fix values.

        Verifies the fix is surgical — only copilotMemory.enabled changes.
        The memory-disabled assertion makes this test fail before the fix.
        """
        for key, expected in _PRESERVED_SETTINGS.items():
            assert vscode_settings[key] == expected, (
                f"Setting {key!r} was accidentally modified"
            )
        assert vscode_settings["github.copilot.chat.copilotMemory.enabled"] is False
