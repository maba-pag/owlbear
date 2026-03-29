"""Failing tests for task #188: Fix stale .github/agents/ paths in v1-era test files.

Verifies that the 4 targeted test files no longer contain stale .github/agents/
path references or deprecated test methods after the builder applies the AC changes.

All tests fail on current HEAD because the stale references and the deprecated
method still exist in the test files.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parent.parent

TEST_RENAME_TODO = ROOT / "tests" / "test_rename_todo_to_todos.py"
TEST_AGENT_PORT_V2 = ROOT / "tests" / "test_agent_port_v2.py"
TEST_RESOLVE_MEMORY = ROOT / "tests" / "test_resolve_memory_file_uri_removal.py"
TEST_MONOREPO = ROOT / "tests" / "test_monorepo_skeleton.py"


class TestFromAC_StaleAgentsPathFixes:
    """AC: 4 v1-era test files must not contain stale .github/agents/ references or methods."""

    def test_rename_todo_agents_dir_uses_root_agents(self) -> None:
        """test_rename_todo_to_todos.py AGENTS_DIR must point to ROOT/agents, not ROOT/.github/agents.

        AC1: AGENTS_DIR = ROOT / ".github" / "agents" must become AGENTS_DIR = ROOT / "agents".
        Fails until the AGENTS_DIR assignment and any surrounding comments referencing
        .github/agents/ (L3, L20, L59) are updated.
        """
        content = TEST_RENAME_TODO.read_text(encoding="utf-8")
        stale_lines = [
            (i + 1, line.strip())
            for i, line in enumerate(content.splitlines())
            if ".github" in line
        ]
        assert stale_lines == [], (
            f"test_rename_todo_to_todos.py still references .github at: {stale_lines}. "
            "Update AGENTS_DIR to ROOT / 'agents' and fix all related comments."
        )

    def test_agent_port_v2_github_agents_dir_variable_removed(self) -> None:
        """test_agent_port_v2.py must not define GITHUB_AGENTS_DIR.

        AC2: remove GITHUB_AGENTS_DIR = ROOT / '.github' / 'agents' (L18).
        Its purpose is moot once #166 deletes the .github/agents/ directory.
        Fails until this variable declaration is removed.
        """
        content = TEST_AGENT_PORT_V2.read_text(encoding="utf-8")
        assert "GITHUB_AGENTS_DIR" not in content, (
            "test_agent_port_v2.py still defines GITHUB_AGENTS_DIR. "
            "Remove this variable — the .github/agents/ directory is deleted by #166."
        )

    def test_agent_port_v2_v1_cleanup_class_removed(self) -> None:
        """test_agent_port_v2.py must not contain the TestFromAC_V1Cleanup class.

        AC2: remove class TestFromAC_V1Cleanup (L307-318). This class tested that
        .github/agents/ was empty after the port, but #166 deletes the directory
        entirely, making the class redundant and misleading.
        Fails until the entire class is removed.
        """
        content = TEST_AGENT_PORT_V2.read_text(encoding="utf-8")
        assert "TestFromAC_V1Cleanup" not in content, (
            "test_agent_port_v2.py still contains class TestFromAC_V1Cleanup. "
            "Remove this class (the directory is deleted by #166, not just emptied)."
        )

    def test_resolve_memory_docstring_no_github_agents(self) -> None:
        """test_resolve_memory_file_uri_removal.py must not mention .github/agents/ anywhere.

        AC3: the docstring at L58 reads 'No .agent.md file in .github/agents/ may reference…'.
        It must be updated to reference 'agents/' (the correct current location).
        Note: AGENTS_DIR at L20 is already correct — only the docstring is stale.
        Fails until the L58 docstring is updated.
        """
        content = TEST_RESOLVE_MEMORY.read_text(encoding="utf-8")
        stale_lines = [
            (i + 1, line.strip())
            for i, line in enumerate(content.splitlines())
            if ".github/agents" in line
        ]
        assert stale_lines == [], (
            f"test_resolve_memory_file_uri_removal.py still references .github/agents/ "
            f"at: {stale_lines}. Update the docstring to use 'agents/'."
        )

    def test_monorepo_github_agents_method_removed(self) -> None:
        """test_monorepo_skeleton.py must not define test_vscode_settings_agent_files_locations_github_agents.

        AC4: remove this test method (L257-261). It asserts that .github/agents appears
        in chat.agentFilesLocations, which directly contradicts #166 (removes .github/agents).
        Fails until the method is deleted from the class.
        """
        content = TEST_MONOREPO.read_text(encoding="utf-8")
        assert "test_vscode_settings_agent_files_locations_github_agents" not in content, (
            "test_monorepo_skeleton.py still contains "
            "test_vscode_settings_agent_files_locations_github_agents. "
            "Remove this method — it contradicts #166 which removes .github/agents."
        )
