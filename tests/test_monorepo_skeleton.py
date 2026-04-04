"""Failing tests for task #7: Create monorepo skeleton.

Covers:
  - Package structure: root pyproject.toml + six per-package pyproject.toml/__init__.py stubs
  - Directory structure: agents/, skills/, instructions/, scripts/, data/knowledge/general/
  - Build verification: uv sync, package importability, uv.lock existence
  - Config updates: .gitignore patterns, bandit target, VS Code settings keys

All tests fail on current HEAD because the monorepo scaffold does not exist yet.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent


# ---------------------------------------------------------------------------
# AC: Package structure
# ---------------------------------------------------------------------------


class TestFromAC_PackageStructure:
    """AC: Root pyproject.toml and per-package pyproject.toml / __init__.py stubs."""

    def test_root_pyproject_toml_exists(self) -> None:
        """Root pyproject.toml must be present (uv workspace root)."""
        assert (ROOT / "pyproject.toml").exists(), "ROOT/pyproject.toml not found"

    def test_root_pyproject_declares_workspace_members(self) -> None:
        """Root pyproject.toml must declare workspace members = ['packages/*']."""
        content = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        assert "packages/*" in content, (
            "workspace members 'packages/*' not declared in ROOT/pyproject.toml"
        )

    # -- packages/orchestrator --

    def test_orchestrator_pyproject_exists(self) -> None:
        """packages/orchestrator/pyproject.toml must exist."""
        assert (ROOT / "packages" / "orchestrator" / "pyproject.toml").exists()

    def test_orchestrator_init_stub_exists(self) -> None:
        """packages/orchestrator/src/owlbear/__init__.py stub must exist."""
        assert (
            ROOT / "packages" / "orchestrator" / "src" / "owlbear" / "__init__.py"
        ).exists()

    # -- packages/knowledge --

    def test_knowledge_pyproject_exists(self) -> None:
        """packages/knowledge/pyproject.toml must exist."""
        assert (ROOT / "packages" / "knowledge" / "pyproject.toml").exists()

    def test_knowledge_init_stub_exists(self) -> None:
        """packages/knowledge/src/owlbear_knowledge/__init__.py stub must exist."""
        assert (
            ROOT
            / "packages"
            / "knowledge"
            / "src"
            / "owlbear_knowledge"
            / "__init__.py"
        ).exists()

    # -- packages/mcp-kanban --

    def test_mcp_kanban_pyproject_exists(self) -> None:
        """packages/mcp-kanban/pyproject.toml must exist."""
        assert (ROOT / "packages" / "mcp-kanban" / "pyproject.toml").exists()

    def test_mcp_kanban_init_stub_exists(self) -> None:
        """packages/mcp-kanban/src/owlbear_mcp_kanban/__init__.py stub must exist."""
        assert (
            ROOT
            / "packages"
            / "mcp-kanban"
            / "src"
            / "owlbear_mcp_kanban"
            / "__init__.py"
        ).exists()

    # -- packages/mcp-knowledge --

    def test_mcp_knowledge_pyproject_exists(self) -> None:
        """packages/mcp-knowledge/pyproject.toml must exist."""
        assert (ROOT / "packages" / "mcp-knowledge" / "pyproject.toml").exists()

    def test_mcp_knowledge_init_stub_exists(self) -> None:
        """packages/mcp-knowledge/src/owlbear_mcp_knowledge/__init__.py stub must exist."""
        assert (
            ROOT
            / "packages"
            / "mcp-knowledge"
            / "src"
            / "owlbear_mcp_knowledge"
            / "__init__.py"
        ).exists()

    # -- packages/mcp-project --

    def test_mcp_project_pyproject_exists(self) -> None:
        """packages/mcp-project/pyproject.toml must exist."""
        assert (ROOT / "packages" / "mcp-project" / "pyproject.toml").exists()

    def test_mcp_project_init_stub_exists(self) -> None:
        """packages/mcp-project/src/owlbear_mcp_project/__init__.py stub must exist."""
        assert (
            ROOT
            / "packages"
            / "mcp-project"
            / "src"
            / "owlbear_mcp_project"
            / "__init__.py"
        ).exists()


# ---------------------------------------------------------------------------
# AC: Directory structure
# ---------------------------------------------------------------------------


class TestFromAC_DirectoryStructure:
    """AC: Transition placeholder dirs and support dirs at repo root."""

    def test_agents_dir_has_readme(self) -> None:
        """agents/ at repo root must contain a README.md placeholder."""
        assert (ROOT / ".github" / "agents" / "README.md").exists(), (
            "ROOT/agents/README.md not found"
        )

    def test_skills_dir_has_readme(self) -> None:
        """skills/ at repo root must contain a README.md placeholder."""
        assert (ROOT / ".github" / "skills" / "README.md").exists(), (
            "ROOT/skills/README.md not found"
        )

    def test_instructions_dir_has_readme(self) -> None:
        """instructions/ at repo root must contain a README.md placeholder."""
        assert (ROOT / ".github" / "instructions" / "README.md").exists(), (
            "ROOT/instructions/README.md not found"
        )

    def test_scripts_setup_placeholder_exists(self) -> None:
        """scripts/setup.py placeholder must exist."""
        assert (ROOT / "scripts" / "setup.py").exists(), (
            "ROOT/scripts/setup.py not found"
        )

    def test_data_knowledge_general_gitkeep_exists(self) -> None:
        """data/knowledge/general/ must exist and contain a .gitkeep sentinel."""
        assert (ROOT / "data" / "knowledge" / "general" / ".gitkeep").exists(), (
            "ROOT/data/knowledge/general/.gitkeep not found"
        )


# ---------------------------------------------------------------------------
# AC: Build verification
# ---------------------------------------------------------------------------


class TestFromAC_BuildVerification:
    """AC: uv sync, package importability, uv.lock committed."""

    def test_uv_lock_exists(self) -> None:
        """uv.lock must be present at repo root (reproducible builds)."""
        assert (ROOT / "uv.lock").exists(), "uv.lock not found at repo root"

    def test_uv_sync_succeeds(self) -> None:
        """uv sync --all-extras must exit 0 (empty packages, zero errors)."""
        result = subprocess.run(
            ["uv", "sync", "--all-extras"],
            cwd=ROOT,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0, (
            f"uv sync --all-extras failed:\n{result.stderr.decode(errors='replace')}"
        )

    @pytest.mark.parametrize(
        "module",
        [
            "owlbear",
            "owlbear_knowledge",
            "owlbear_mcp_kanban",
            "owlbear_mcp_knowledge",
            "owlbear_mcp_project",
        ],
    )
    def test_package_importable(self, module: str) -> None:
        """Each stub package must be importable via 'uv run python -c import MODULE'."""
        result = subprocess.run(
            ["uv", "run", "python", "-c", f"import {module}"],
            cwd=ROOT,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0, (
            f"import {module} failed:\n{result.stderr.decode(errors='replace')}"
        )


# ---------------------------------------------------------------------------
# AC: Config updates
# ---------------------------------------------------------------------------


class TestFromAC_ConfigUpdates:
    """AC: .gitignore patterns, bandit target, VS Code location settings."""

    # -- .gitignore --

    def test_gitignore_has_packages_dist_pattern(self) -> None:
        """.gitignore must contain packages/*/dist/ ignore pattern."""
        content = (ROOT / ".gitignore").read_text(encoding="utf-8")
        assert "packages/*/dist/" in content, "packages/*/dist/ not found in .gitignore"

    def test_gitignore_has_data_knowledge_db_pattern(self) -> None:
        """.gitignore must contain data/knowledge/*.db ignore pattern."""
        content = (ROOT / ".gitignore").read_text(encoding="utf-8")
        assert "data/knowledge/*.db" in content, (
            "data/knowledge/*.db not found in .gitignore"
        )

    # -- .pre-commit-config.yaml bandit --

    def test_precommit_bandit_targets_packages_not_src(self) -> None:
        """.pre-commit-config.yaml bandit hook must target -r packages/, not -r src/."""
        content = (ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
        # Find bandit block
        bandit_block_match = re.search(r"- id: bandit\n((?:\s+.*\n)*)", content)
        assert bandit_block_match, "bandit hook not found in .pre-commit-config.yaml"
        bandit_block = bandit_block_match.group(0)
        assert "packages/" in bandit_block, (
            "bandit hook does not target packages/ in .pre-commit-config.yaml"
        )
        assert "src/" not in bandit_block, (
            "bandit hook still targets src/ in .pre-commit-config.yaml"
        )

    # -- .vscode/settings.json --

    def _read_vscode_settings(self) -> dict:  # type: ignore[type-arg]
        """Return parsed .vscode/settings.json."""
        return json.loads(
            (ROOT / ".vscode" / "settings.json").read_text(encoding="utf-8")
        )

    def test_vscode_settings_no_custom_agent_locations(self) -> None:
        """chat.agentFilesLocations must not exist — .github/ is the default discovery path."""
        settings = self._read_vscode_settings()
        assert "chat.agentFilesLocations" not in settings, (
            "chat.agentFilesLocations should be removed — .github/agents/ is default"
        )

    def test_vscode_settings_no_custom_skills_locations(self) -> None:
        """chat.agentSkillsLocations must not exist — .github/ is the default discovery path."""
        settings = self._read_vscode_settings()
        assert "chat.agentSkillsLocations" not in settings, (
            "chat.agentSkillsLocations should be removed — .github/skills/ is default"
        )

    def test_vscode_settings_no_custom_instructions_locations(self) -> None:
        """chat.instructionsFilesLocations must not exist — .github/ is the default discovery path."""
        settings = self._read_vscode_settings()
        assert "chat.instructionsFilesLocations" not in settings, (
            "chat.instructionsFilesLocations should be removed — .github/instructions/ is default"
        )
