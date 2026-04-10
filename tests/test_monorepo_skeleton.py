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

pytestmark = pytest.mark.slow

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
        """Root pyproject.toml must declare workspace members = ['serve/*'] (renamed from packages/*)."""
        content = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        assert "serve/*" in content, "workspace members 'serve/*' not declared in ROOT/pyproject.toml"

    # -- packages/orchestrator --

    def test_orchestrator_pyproject_exists(self) -> None:
        """serve/orchestrator/pyproject.toml must exist."""
        assert (ROOT / "serve" / "orchestrator" / "pyproject.toml").exists()

    def test_orchestrator_init_stub_exists(self) -> None:
        """serve/orchestrator/src/owlbear/__init__.py stub must exist."""
        assert (ROOT / "serve" / "orchestrator" / "src" / "owlbear" / "__init__.py").exists()

    # -- serve/knowledge --

    def test_knowledge_pyproject_exists(self) -> None:
        """serve/knowledge/pyproject.toml must exist."""
        assert (ROOT / "serve" / "knowledge" / "pyproject.toml").exists()

    def test_knowledge_init_stub_exists(self) -> None:
        """serve/knowledge/src/owlbear_knowledge/__init__.py stub must exist."""
        assert (ROOT / "serve" / "knowledge" / "src" / "owlbear_knowledge" / "__init__.py").exists()

    # -- serve/mcp-kanban --

    def test_mcp_kanban_pyproject_exists(self) -> None:
        """serve/mcp-kanban/pyproject.toml must exist."""
        assert (ROOT / "serve" / "mcp-kanban" / "pyproject.toml").exists()

    def test_mcp_kanban_init_stub_exists(self) -> None:
        """serve/mcp-kanban/src/owlbear_mcp_kanban/__init__.py stub must exist."""
        assert (ROOT / "serve" / "mcp-kanban" / "src" / "owlbear_mcp_kanban" / "__init__.py").exists()

    # -- serve/mcp-knowledge --

    def test_mcp_knowledge_pyproject_exists(self) -> None:
        """serve/mcp-knowledge/pyproject.toml must exist."""
        assert (ROOT / "serve" / "mcp-knowledge" / "pyproject.toml").exists()

    def test_mcp_knowledge_init_stub_exists(self) -> None:
        """serve/mcp-knowledge/src/owlbear_mcp_knowledge/__init__.py stub must exist."""
        assert (ROOT / "serve" / "mcp-knowledge" / "src" / "owlbear_mcp_knowledge" / "__init__.py").exists()


# ---------------------------------------------------------------------------
# AC: Directory structure
# ---------------------------------------------------------------------------


class TestFromAC_DirectoryStructure:
    """AC: Transition placeholder dirs and support dirs at repo root."""

    def test_agents_dir_has_readme(self) -> None:
        """share/agents/ must contain a README.md placeholder."""
        assert (ROOT / "share" / "agents" / "README.md").exists(), "ROOT/share/agents/README.md not found"

    def test_skills_dir_has_readme(self) -> None:
        """share/skills/ must contain a README.md placeholder."""
        assert (ROOT / "share" / "skills" / "README.md").exists(), "ROOT/share/skills/README.md not found"

    def test_instructions_dir_has_readme(self) -> None:
        """share/instructions/ must contain a README.md placeholder."""
        assert (ROOT / "share" / "instructions" / "README.md").exists(), "ROOT/share/instructions/README.md not found"

    def test_setup_init_exists(self) -> None:
        """setup/init.py must exist (scripts/setup.py was deleted in #609 AC7)."""
        assert (ROOT / "setup" / "init.py").exists(), "ROOT/setup/init.py not found"

    def test_data_knowledge_general_gitkeep_exists(self) -> None:
        """store/knowledge/general/ must exist and contain a .gitkeep sentinel."""
        assert (ROOT / "store" / "knowledge" / "general" / ".gitkeep").exists(), (
            "ROOT/store/knowledge/general/.gitkeep not found"
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
        assert result.returncode == 0, f"uv sync --all-extras failed:\n{result.stderr.decode(errors='replace')}"

    @pytest.mark.parametrize(
        "module",
        [
            "owlbear",
            "owlbear_knowledge",
            "owlbear_mcp_kanban",
            "owlbear_mcp_knowledge",
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
        assert result.returncode == 0, f"import {module} failed:\n{result.stderr.decode(errors='replace')}"


# ---------------------------------------------------------------------------
# AC: Config updates
# ---------------------------------------------------------------------------


class TestFromAC_ConfigUpdates:
    """AC: .gitignore patterns, bandit target, VS Code location settings."""

    # -- .gitignore --

    def test_gitignore_has_serve_dist_pattern(self) -> None:
        """.gitignore must contain serve/*/dist/ ignore pattern."""
        content = (ROOT / ".gitignore").read_text(encoding="utf-8")
        assert "serve/*/dist/" in content, "serve/*/dist/ not found in .gitignore"

    def test_gitignore_has_store_knowledge_db_pattern(self) -> None:
        """.gitignore must contain store/knowledge/*.db ignore pattern."""
        content = (ROOT / ".gitignore").read_text(encoding="utf-8")
        assert "store/knowledge/*.db" in content, "store/knowledge/*.db not found in .gitignore"

    # -- .pre-commit-config.yaml bandit --

    def test_precommit_bandit_targets_serve_not_src(self) -> None:
        """.pre-commit-config.yaml bandit hook must target -r serve/, not -r src/."""
        content = (ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
        # Find bandit block
        bandit_block_match = re.search(r"- id: bandit\n((?:\s+.*\n)*)", content)
        assert bandit_block_match, "bandit hook not found in .pre-commit-config.yaml"
        bandit_block = bandit_block_match.group(0)
        assert "serve/" in bandit_block, "bandit hook does not target serve/ in .pre-commit-config.yaml"
        assert "src/" not in bandit_block, "bandit hook still targets src/ in .pre-commit-config.yaml"

    # -- .vscode/settings.json --

    def _read_vscode_settings(self) -> dict:  # type: ignore[type-arg]
        """Return parsed .vscode/settings.json."""
        return json.loads((ROOT / ".vscode" / "settings.json").read_text(encoding="utf-8"))

    def test_vscode_settings_has_agent_locations(self) -> None:
        """chat.agentFilesLocations must exist pointing to share/agents/ (five-tier restructure)."""
        settings = self._read_vscode_settings()
        assert "chat.agentFilesLocations" in settings, "chat.agentFilesLocations must be set to point to share/agents/"

    def test_vscode_settings_has_skills_locations(self) -> None:
        """chat.agentSkillsLocations must exist pointing to share/skills/ (five-tier restructure)."""
        settings = self._read_vscode_settings()
        assert "chat.agentSkillsLocations" in settings, (
            "chat.agentSkillsLocations must be set to point to share/skills/"
        )

    def test_vscode_settings_has_instructions_locations(self) -> None:
        """chat.instructionsFilesLocations must exist pointing to share/instructions/ (five-tier restructure)."""
        settings = self._read_vscode_settings()
        assert "chat.instructionsFilesLocations" in settings, (
            "chat.instructionsFilesLocations must be set to point to share/instructions/"
        )
