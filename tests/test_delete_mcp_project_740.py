"""Failing tests for task #740: Delete mcp-project MCP server (redundant).

Covers (TDD RED phase — all tests must FAIL before builder implements #740):
  - AC1: serve/mcp-project/ directory removed
  - AC2: MCP server entry removed from .vscode/mcp.json and seed/.vscode/mcp.json
  - AC3: Agent definitions referencing owlbear-project tools updated
  - AC4: pyproject.toml updated (ruff.src and coverage.source_pkgs)
  - AC5: No remaining imports or references to mcp-project in config, skills, or tests

All tests fail on current HEAD because serve/mcp-project/ still exists and
all references are still wired throughout configs, skills, and test files.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).parent.parent


# ---------------------------------------------------------------------------
# AC1: serve/mcp-project/ directory removed
# ---------------------------------------------------------------------------


class TestFromAC_DirectoryRemoval:
    """AC1: serve/mcp-project/ and share/skills/h-mcp-project/ directories deleted."""

    def test_serve_mcp_project_dir_does_not_exist(self) -> None:
        """serve/mcp-project/ must be absent after deletion."""
        assert not (ROOT / "serve" / "mcp-project").exists(), (
            "serve/mcp-project/ still exists — builder must delete this directory"
        )

    def test_h_mcp_project_skill_dir_does_not_exist(self) -> None:
        """share/skills/h-mcp-project/ must be absent after deletion."""
        assert not (ROOT / "share" / "skills" / "h-mcp-project").exists(), (
            "share/skills/h-mcp-project/ still exists — builder must delete this directory"
        )


# ---------------------------------------------------------------------------
# AC2: MCP server entry removed from .vscode/mcp.json files
# ---------------------------------------------------------------------------


class TestFromAC_McpJsonCleanup:
    """AC2: `owlbear-project` server entry absent from both mcp.json configs."""

    def test_vscode_mcp_json_no_owlbear_project_entry(self) -> None:
        """.vscode/mcp.json must not contain an owlbear-project server entry."""
        mcp_json_path = ROOT / ".vscode" / "mcp.json"
        assert mcp_json_path.exists(), ".vscode/mcp.json not found"
        # The key may be at top level or nested under "servers"
        raw = mcp_json_path.read_text(encoding="utf-8")
        assert '"owlbear-project"' not in raw, (
            ".vscode/mcp.json still contains owlbear-project server entry"
        )

    def test_seed_vscode_mcp_json_no_owlbear_project_entry(self) -> None:
        """seed/.vscode/mcp.json must not contain an owlbear-project server entry."""
        mcp_json_path = ROOT / "seed" / ".vscode" / "mcp.json"
        assert mcp_json_path.exists(), "seed/.vscode/mcp.json not found"
        raw = mcp_json_path.read_text(encoding="utf-8")
        assert '"owlbear-project"' not in raw, (
            "seed/.vscode/mcp.json still contains owlbear-project server entry"
        )


# ---------------------------------------------------------------------------
# AC3: Agent definitions referencing owlbear-project tools updated
# ---------------------------------------------------------------------------


class TestFromAC_AgentToolCleanup:
    """AC3: No agent files reference owlbear-project/* tools."""

    def test_ideator_agent_no_owlbear_project_tool(self) -> None:
        """share/agents/ideator.agent.md must not list owlbear-project/* in its tool allowlist."""
        agent_path = ROOT / "share" / "agents" / "ideator.agent.md"
        assert agent_path.exists(), "ideator.agent.md not found"
        content = agent_path.read_text(encoding="utf-8")
        assert "owlbear-project/*" not in content, (
            "ideator.agent.md still references owlbear-project/* in tool allowlist"
        )


# ---------------------------------------------------------------------------
# AC4: pyproject.toml updated — ruff.src and coverage.source_pkgs
# ---------------------------------------------------------------------------


class TestFromAC_PyprojectCleanup:
    """AC4: pyproject.toml must not list mcp-project in ruff.src or coverage.source_pkgs."""

    def test_pyproject_ruff_src_excludes_mcp_project(self) -> None:
        """pyproject.toml [tool.ruff] src must not include serve/mcp-project/src."""
        content = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        assert "serve/mcp-project/src" not in content, (
            'pyproject.toml still has "serve/mcp-project/src" in tool.ruff.src'
        )

    def test_pyproject_coverage_excludes_owlbear_mcp_project(self) -> None:
        """pyproject.toml [tool.coverage.run] source_pkgs must not include owlbear_mcp_project."""
        content = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        assert "owlbear_mcp_project" not in content, (
            'pyproject.toml still has "owlbear_mcp_project" in tool.coverage.run.source_pkgs'
        )


# ---------------------------------------------------------------------------
# AC5: No remaining imports or references to mcp-project
# ---------------------------------------------------------------------------


class TestFromAC_NoRemainingReferences:
    """AC5: All configs, skills, and tests must be free of mcp-project references."""

    def test_r_architecture_standards_no_mcp_project_references(self) -> None:
        """r-architecture-standards SKILL.md must not reference mcp-project after deletion."""
        skill_path = ROOT / "share" / "skills" / "r-architecture-standards" / "SKILL.md"
        assert skill_path.exists(), "r-architecture-standards SKILL.md not found"
        content = skill_path.read_text(encoding="utf-8")
        assert "mcp-project" not in content, (
            "r-architecture-standards SKILL.md still references mcp-project — "
            "remove from package list, MCP server list, TOOLS_EXCLUDE table, "
            "handbook reference, and source map"
        )

    def test_error_prefix_test_no_owlbear_mcp_project_import(self) -> None:
        """tests/test_error_prefix_506.py must not import from owlbear_mcp_project."""
        test_path = ROOT / "tests" / "test_error_prefix_506.py"
        assert test_path.exists(), "test_error_prefix_506.py not found"
        content = test_path.read_text(encoding="utf-8")
        assert "owlbear_mcp_project" not in content, (
            "test_error_prefix_506.py still imports owlbear_mcp_project — "
            "remove TestFromAC_ErrorPrefixProject class and its imports"
        )

    def test_tools_exclude_test_no_owlbear_mcp_project_import(self) -> None:
        """tests/test_tools_exclude_493.py must not import from owlbear_mcp_project."""
        test_path = ROOT / "tests" / "test_tools_exclude_493.py"
        assert test_path.exists(), "test_tools_exclude_493.py not found"
        content = test_path.read_text(encoding="utf-8")
        assert "owlbear_mcp_project" not in content, (
            "test_tools_exclude_493.py still imports owlbear_mcp_project — "
            "remove mcp-project test classes and imports"
        )

    def test_mcp_server_conventions_test_no_owlbear_mcp_project_import(self) -> None:
        """tests/test_mcp_server_conventions_496.py must not import from owlbear_mcp_project."""
        test_path = ROOT / "tests" / "test_mcp_server_conventions_496.py"
        assert test_path.exists(), "test_mcp_server_conventions_496.py not found"
        content = test_path.read_text(encoding="utf-8")
        assert "owlbear_mcp_project" not in content, (
            "test_mcp_server_conventions_496.py still imports owlbear_mcp_project — "
            "remove mcp-project test classes and imports"
        )

    def test_monorepo_skeleton_test_no_mcp_project_class(self) -> None:
        """tests/test_monorepo_skeleton.py must not contain mcp-project skeleton tests."""
        test_path = ROOT / "tests" / "test_monorepo_skeleton.py"
        assert test_path.exists(), "test_monorepo_skeleton.py not found"
        content = test_path.read_text(encoding="utf-8")
        # The test methods test_mcp_project_pyproject_exists and
        # test_mcp_project_init_stub_exists must be removed.
        assert "test_mcp_project_pyproject_exists" not in content, (
            "test_monorepo_skeleton.py still contains test_mcp_project_pyproject_exists"
        )

    def test_monorepo_skeleton_test_no_owlbear_mcp_project_parametrize(self) -> None:
        """tests/test_monorepo_skeleton.py must not parametrize owlbear_mcp_project importability."""
        test_path = ROOT / "tests" / "test_monorepo_skeleton.py"
        assert test_path.exists(), "test_monorepo_skeleton.py not found"
        content = test_path.read_text(encoding="utf-8")
        assert "owlbear_mcp_project" not in content, (
            "test_monorepo_skeleton.py still parametrizes owlbear_mcp_project in importability check"
        )

    def test_package_boundary_test_no_owlbear_mcp_project_entry(self) -> None:
        """tests/test_package_boundary.py ALLOWED_IMPORTS must not include owlbear_mcp_project."""
        test_path = ROOT / "tests" / "test_package_boundary.py"
        assert test_path.exists(), "test_package_boundary.py not found"
        content = test_path.read_text(encoding="utf-8")
        # Match the exact dict entry pattern so we don't catch legitimate comments
        assert not re.search(r'"owlbear_mcp_project"\s*:', content), (
            'test_package_boundary.py still has "owlbear_mcp_project": ... in ALLOWED_IMPORTS'
        )

    def test_owlbear_system_instructions_no_mcp_project_reference(self) -> None:
        """owlbear-system.instructions.md must not list owlbear-project as an MCP server."""
        instructions_path = ROOT / "share" / "instructions" / "owlbear-system.instructions.md"
        assert instructions_path.exists(), "owlbear-system.instructions.md not found"
        content = instructions_path.read_text(encoding="utf-8")
        assert "mcp-project" not in content, (
            "owlbear-system.instructions.md still references mcp-project — "
            "update MCP server count/list to reflect removal"
        )

    def test_readme_no_mcp_project_references(self) -> None:
        """README.md must not reference mcp-project in directory table or MCP servers list."""
        readme_path = ROOT / "README.md"
        assert readme_path.exists(), "README.md not found"
        content = readme_path.read_text(encoding="utf-8")
        assert "mcp-project" not in content, (
            "README.md still references mcp-project — "
            "remove the serve/mcp-project/ row from the directory table "
            "and remove mcp-project from the MCP servers sentence"
        )

    def test_readme_consumer_no_mcp_project_references(self) -> None:
        """README-consumer.md must not reference mcp-project in the directory table."""
        readme_path = ROOT / "README-consumer.md"
        assert readme_path.exists(), "README-consumer.md not found"
        content = readme_path.read_text(encoding="utf-8")
        assert "mcp-project" not in content, (
            "README-consumer.md still references mcp-project — "
            "remove the serve/mcp-project/ row from the directory table"
        )

    def test_setup_guide_no_mcp_project_section(self) -> None:
        """setup/setup-guide.md must not contain the 'Configuring the project MCP server' section."""
        guide_path = ROOT / "setup" / "setup-guide.md"
        assert guide_path.exists(), "setup/setup-guide.md not found"
        content = guide_path.read_text(encoding="utf-8")
        assert "Configuring the project MCP server" not in content, (
            "setup/setup-guide.md still contains the 'Configuring the project MCP server' section — "
            "remove the entire section including the owlbear_mcp_project JSON example"
        )
        assert "owlbear_mcp_project" not in content, (
            "setup/setup-guide.md still references owlbear_mcp_project — "
            "remove the 'Configuring the project MCP server' section entirely"
        )
