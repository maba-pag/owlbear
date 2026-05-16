"""Failing tests for task #1289: P2-05 — extract r-architecture-standards sections.

All tests must FAIL on the current codebase; they pass once the builder extracts the
Architecture Overview, Dependency Rules, and Domain Scope Map sections from
share/skills/r-architecture-standards/SKILL.md into the new
.owlbear/instructions/architecture.instructions.md.

AC coverage:
  AC1 (td:1) — test_architecture_instructions_file_exists,
                test_architecture_instructions_has_apply_to_serve
  AC2 (td:1) — test_architecture_instructions_has_architecture_overview_section,
                test_architecture_instructions_has_dependency_rules_section,
                test_architecture_instructions_has_domain_scope_map_section,
                test_architecture_instructions_overview_has_serve_paths,
                test_architecture_instructions_domain_scope_has_serve_paths
  AC3 (td:1) — test_r_arch_standards_no_architecture_overview_section,
                test_r_arch_standards_no_dependency_rules_section,
                test_r_arch_standards_no_domain_scope_map_section
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
_ARCH_INSTRUCTIONS = _REPO_ROOT / ".owlbear" / "instructions" / "architecture.instructions.md"
_ARCH_SKILL = _REPO_ROOT / "share" / "skills" / "r-architecture-standards" / "SKILL.md"


class TestFromAC_ArchInstructionsFile:
    """Verify .owlbear/instructions/architecture.instructions.md is created correctly. Task #1289."""

    # ---- AC1 (td:1): new file exists with correct frontmatter ----------------------------

    def test_architecture_instructions_file_exists(self) -> None:
        """The file .owlbear/instructions/architecture.instructions.md must exist on disk."""
        assert _ARCH_INSTRUCTIONS.exists(), (
            f"Expected {_ARCH_INSTRUCTIONS.relative_to(_REPO_ROOT)} to exist — file not yet created by builder"
        )

    def test_architecture_instructions_has_apply_to_serve(self) -> None:
        """architecture.instructions.md frontmatter must declare applyTo: \"serve/**\"."""
        assert _ARCH_INSTRUCTIONS.exists(), f"{_ARCH_INSTRUCTIONS.relative_to(_REPO_ROOT)} does not exist"
        content = _ARCH_INSTRUCTIONS.read_text(encoding="utf-8")
        assert 'applyTo: "serve/**"' in content, (
            'architecture.instructions.md must declare applyTo: "serve/**" in its frontmatter — not found'
        )

    # ---- AC2 (td:1): new file contains all three extracted sections ----------------------

    def test_architecture_instructions_has_architecture_overview_section(self) -> None:
        """architecture.instructions.md must contain the ## Architecture Overview section."""
        assert _ARCH_INSTRUCTIONS.exists(), f"{_ARCH_INSTRUCTIONS.relative_to(_REPO_ROOT)} does not exist"
        content = _ARCH_INSTRUCTIONS.read_text(encoding="utf-8")
        assert "## Architecture Overview" in content, (
            "architecture.instructions.md must contain '## Architecture Overview' section"
        )

    def test_architecture_instructions_has_dependency_rules_section(self) -> None:
        """architecture.instructions.md must contain the ## Dependency Rules section."""
        assert _ARCH_INSTRUCTIONS.exists(), f"{_ARCH_INSTRUCTIONS.relative_to(_REPO_ROOT)} does not exist"
        content = _ARCH_INSTRUCTIONS.read_text(encoding="utf-8")
        assert "## Dependency Rules" in content, (
            "architecture.instructions.md must contain '## Dependency Rules' section"
        )

    def test_architecture_instructions_has_domain_scope_map_section(self) -> None:
        """architecture.instructions.md must contain the ## Domain Scope Map section."""
        assert _ARCH_INSTRUCTIONS.exists(), f"{_ARCH_INSTRUCTIONS.relative_to(_REPO_ROOT)} does not exist"
        content = _ARCH_INSTRUCTIONS.read_text(encoding="utf-8")
        assert "## Domain Scope Map" in content, (
            "architecture.instructions.md must contain '## Domain Scope Map' section"
        )

    def test_architecture_instructions_overview_has_serve_paths(self) -> None:
        """Architecture Overview in the new file must reference serve/ paths, not workspace/.

        The shared skill uses workspace/ as a path-neutral form; the instructions file
        restores concrete serve/ paths for the owlbear-dev consumer.
        """
        assert _ARCH_INSTRUCTIONS.exists(), f"{_ARCH_INSTRUCTIONS.relative_to(_REPO_ROOT)} does not exist"
        content = _ARCH_INSTRUCTIONS.read_text(encoding="utf-8")
        assert "serve/mcp-kanban/" in content, (
            "architecture.instructions.md Architecture Overview must reference 'serve/mcp-kanban/' "
            "(serve/ paths restored from workspace/ form) — not found"
        )

    def test_architecture_instructions_domain_scope_has_serve_paths(self) -> None:
        """Domain Scope Map in the new file must reference serve/ paths, not workspace/.

        The shared skill uses workspace/ as a path-neutral form; the instructions file
        restores concrete serve/ paths for the owlbear-dev consumer.
        """
        assert _ARCH_INSTRUCTIONS.exists(), f"{_ARCH_INSTRUCTIONS.relative_to(_REPO_ROOT)} does not exist"
        content = _ARCH_INSTRUCTIONS.read_text(encoding="utf-8")
        assert "serve/knowledge/" in content, (
            "architecture.instructions.md Domain Scope Map must reference 'serve/knowledge/' "
            "(serve/ paths restored from workspace/ form) — not found"
        )


class TestFromAC_ArchSkillRetention:
    """Verify r-architecture-standards/SKILL.md no longer contains the extracted sections. Task #1289."""

    # ---- AC3 (td:1): shared skill must not contain the three extracted section headers ---

    def test_r_arch_standards_no_architecture_overview_section(self) -> None:
        """r-architecture-standards/SKILL.md must not contain ## Architecture Overview.

        This section is moved to .owlbear/instructions/architecture.instructions.md.
        """
        content = _ARCH_SKILL.read_text(encoding="utf-8")
        assert "## Architecture Overview" not in content, (
            "r-architecture-standards/SKILL.md still contains '## Architecture Overview' — "
            "section must be extracted to architecture.instructions.md"
        )

    def test_r_arch_standards_no_dependency_rules_section(self) -> None:
        """r-architecture-standards/SKILL.md must not contain ## Dependency Rules.

        This section is moved to .owlbear/instructions/architecture.instructions.md.
        """
        content = _ARCH_SKILL.read_text(encoding="utf-8")
        assert "## Dependency Rules" not in content, (
            "r-architecture-standards/SKILL.md still contains '## Dependency Rules' — "
            "section must be extracted to architecture.instructions.md"
        )

    def test_r_arch_standards_no_domain_scope_map_section(self) -> None:
        """r-architecture-standards/SKILL.md must not contain ## Domain Scope Map.

        This section is moved to .owlbear/instructions/architecture.instructions.md.
        """
        content = _ARCH_SKILL.read_text(encoding="utf-8")
        assert "## Domain Scope Map" not in content, (
            "r-architecture-standards/SKILL.md still contains '## Domain Scope Map' — "
            "section must be extracted to architecture.instructions.md"
        )
