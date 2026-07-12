"""Authority-boundary regressions for project instructions and shared skills."""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
_SKILLS_ROOT = _REPO_ROOT / "share" / "skills"
_COPILOT_INSTRUCTIONS = _REPO_ROOT / ".github" / "copilot-instructions.md"

_ARTIFACT_PLACEMENT_HEADING = "## OwlBear-Managed Artifact Placement"
_PROJECT_LAYOUT_HEADING = "## Project Layout"


class TestProjectInstructionAuthorityBoundary:
    """Keep portable OwlBear behavior out of local project instructions."""

    def test_workspace_governance_owns_owlbear_artifact_placement(self) -> None:
        """Workspace governance owns placement for OwlBear-managed artifacts."""
        skill_file = _SKILLS_ROOT / "r-workspace-governance" / "SKILL.md"
        assert skill_file.exists(), f"Expected {skill_file.relative_to(_REPO_ROOT)} to exist"
        content = skill_file.read_text(encoding="utf-8")

        assert _ARTIFACT_PLACEMENT_HEADING in content
        for managed_path in (".owlbear/scratch/", ".owlbear/research/", ".owlbear/doc-index.md"):
            assert managed_path in content

    def test_python_conventions_remain_project_agnostic(self) -> None:
        """Language conventions must not define one project's package layout."""
        skill_file = _SKILLS_ROOT / "h-python-conventions" / "SKILL.md"
        assert skill_file.exists(), f"Expected {skill_file.relative_to(_REPO_ROOT)} to exist"
        content = skill_file.read_text(encoding="utf-8")

        assert _PROJECT_LAYOUT_HEADING not in content
        for heading_fragment in ("Package Management", "Code Style", "Testing"):
            assert heading_fragment in content

    def test_copilot_instructions_contain_project_facts_only(self) -> None:
        """Local instructions keep the concrete map without portable policy sections."""
        assert _COPILOT_INSTRUCTIONS.exists(), f"Expected {_COPILOT_INSTRUCTIONS.relative_to(_REPO_ROOT)} to exist"
        content = _COPILOT_INSTRUCTIONS.read_text(encoding="utf-8")

        assert "## Directory Structure" in content
        assert "serve/*/src/" in content
        assert "\n## File Placement" not in content
        assert f"\n{_PROJECT_LAYOUT_HEADING}" not in content
        for portable_command in ("uv run indexes", "doc-index", "py-index", "ts-index", "test-root"):
            assert portable_command not in content

    def test_codebase_orientation_owns_discovery_tools(self) -> None:
        """The shared orientation handbook owns portable discovery behavior."""
        skill_file = _SKILLS_ROOT / "h-codebase-orientation" / "SKILL.md"
        content = skill_file.read_text(encoding="utf-8")

        for tool in (" indexes {project-root}", "doc-index", "py-index", "ts-index", "test-root", "Semble"):
            assert tool in content
