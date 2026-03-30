"""Tests for task #166: Delete .github/agents/ and clean stale settings.

Contract-level verification that .github/agents/ references are removed
from affected files after cleanup.

AC coverage:
  - AC1: .github/agents/ directory is deleted
  - AC2: .vscode/settings.json chat.agentFilesLocations has no .github/agents entry
  - AC3/AC4: scripts/setup.py has no .github/agents or .github/instructions references
             (covered by existing tests in test_setup_script.py — not duplicated here)
  - AC5/AC6: test_setup_script.py test methods renamed
             (already completed by task #186 pipeline — not duplicated here)

Both active tests fail against the pre-cleanup state (current HEAD) and pass once
task #166 is complete.
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent


class TestFromAC_GithubAgentsDirDeleted:
    """AC1: .github/agents/ directory must not exist after cleanup."""

    def test_github_agents_directory_does_not_exist(self) -> None:
        """.github/agents/ must be entirely deleted — no subdirectory, no files."""
        assert not (_REPO_ROOT / ".github" / "agents").exists(), (
            ".github/agents/ directory still exists — task #166 must delete it entirely"
        )


class TestFromAC_VscodeSettingsNoDualPath:
    """AC2: .vscode/settings.json must not reference .github/agents in agentFilesLocations."""

    def _settings_text(self) -> str:
        return (_REPO_ROOT / ".vscode" / "settings.json").read_text(encoding="utf-8")

    def test_settings_json_no_github_agents_entry(self) -> None:
        """chat.agentFilesLocations in .vscode/settings.json must not include .github/agents."""
        content = self._settings_text()
        assert ".github/agents" not in content, (
            ".vscode/settings.json still contains a .github/agents entry "
            "(line 33) — must be removed as part of task #166 cleanup"
        )
