"""Tests for P1-03: cross-reference updates for agent-ecosystem.instructions.md applyTo extension.

Verifies that the applyTo field in agent-ecosystem.instructions.md is extended to include
.owlbear/ paths, and that the maintained mirrors in share/README.md and
h-agent-structure/SKILL.md reflect the new scope.

AC coverage:
- AC1: agent-ecosystem.instructions.md YAML applyTo includes .owlbear/ paths (td:1)
- AC2: share/README.md stubs table mirrors .owlbear/ paths (td:1)
- AC3: h-agent-structure SKILL.md stubs table mirrors .owlbear/ paths (td:1)
"""

from __future__ import annotations

from pathlib import Path

_EXPECTED_OWLBEAR_PATHS = [
    ".owlbear/agents/**",
    ".owlbear/skills/**",
    ".owlbear/instructions/**",
    ".owlbear/prompts/**",
]

_FULL_APPLY_TO = (
    "share/agents/**,share/skills/**,share/instructions/**,share/prompts/**,"
    ".owlbear/agents/**,.owlbear/skills/**,.owlbear/instructions/**,.owlbear/prompts/**"
)


class TestFromAC_ApplyToExtension:
    """Agent ecosystem applyTo scope is extended and mirrored in maintained locations."""

    def test_agent_ecosystem_instructions_apply_to_includes_owlbear_paths(self, project_root: Path) -> None:
        """AC1: agent-ecosystem.instructions.md YAML applyTo field includes all .owlbear/ paths."""
        stub = project_root / "share" / "instructions" / "agent-ecosystem.instructions.md"
        content = stub.read_text(encoding="utf-8")
        for path in _EXPECTED_OWLBEAR_PATHS:
            assert path in content, (
                f"agent-ecosystem.instructions.md applyTo must include {path!r}.\n"
                f"Current applyTo is missing .owlbear/ paths — needs extension per AC1."
            )

    def test_readme_instruction_stubs_table_mirrors_owlbear_paths(self, project_root: Path) -> None:
        """AC2: share/README.md stubs table agent-ecosystem.instructions.md row mirrors AC1 applyTo."""
        readme = project_root / "share" / "README.md"
        content = readme.read_text(encoding="utf-8")
        # Find the row for agent-ecosystem.instructions.md in the stubs table
        lines = content.splitlines()
        agent_eco_rows = [line for line in lines if "agent-ecosystem.instructions.md" in line]
        assert agent_eco_rows, "share/README.md must have a row for agent-ecosystem.instructions.md in the stubs table."
        row = agent_eco_rows[0]
        assert ".owlbear/agents/**" in row, (
            "share/README.md stubs table agent-ecosystem.instructions.md row must include "
            ".owlbear/agents/** to mirror the AC1 applyTo extension.\n"
            f"Current row: {row!r}"
        )

    def test_h_agent_structure_stubs_table_mirrors_owlbear_paths(self, project_root: Path) -> None:
        """AC3: h-agent-structure SKILL.md stubs table agent-ecosystem.instructions.md row mirrors AC1."""
        skill = project_root / "share" / "skills" / "h-agent-structure" / "SKILL.md"
        content = skill.read_text(encoding="utf-8")
        lines = content.splitlines()
        agent_eco_rows = [line for line in lines if "agent-ecosystem.instructions.md" in line]
        assert agent_eco_rows, "h-agent-structure SKILL.md must have a row for agent-ecosystem.instructions.md."
        row = agent_eco_rows[0]
        assert ".owlbear/agents/**" in row, (
            "h-agent-structure SKILL.md stubs table agent-ecosystem.instructions.md row must include "
            ".owlbear/agents/** to mirror the AC1 applyTo extension.\n"
            f"Current row: {row!r}"
        )

    def test_agent_ecosystem_instructions_apply_to_yaml_field_contains_owlbear_paths(self, project_root: Path) -> None:
        """AC1 (exact): YAML applyTo: field equals _FULL_APPLY_TO — not just subset membership."""
        stub = project_root / "share" / "instructions" / "agent-ecosystem.instructions.md"
        content = stub.read_text(encoding="utf-8")
        lines = content.splitlines()
        # Extract applyTo value from YAML frontmatter only
        in_frontmatter = False
        apply_to_value: str | None = None
        for line in lines:
            if line.strip() == "---":
                if not in_frontmatter:
                    in_frontmatter = True
                    continue
                break
            if in_frontmatter and line.startswith("applyTo:"):
                apply_to_value = line.split("applyTo:", 1)[1].strip().strip('"')
                break
        assert apply_to_value is not None, (
            "agent-ecosystem.instructions.md YAML frontmatter must contain an applyTo: field.\n"
            "The .owlbear/ extension cannot be validated without it."
        )
        assert apply_to_value == _FULL_APPLY_TO, (
            "YAML applyTo field must equal the full canonical value (both share/ and .owlbear/ halves).\n"
            f"Expected: {_FULL_APPLY_TO!r}\n"
            f"Got:      {apply_to_value!r}"
        )

    def test_readme_stubs_row_mirrors_all_owlbear_paths(self, project_root: Path) -> None:
        """AC2 (exact): share/README.md stubs row contains full _FULL_APPLY_TO value, including share/ prefixes."""
        readme = project_root / "share" / "README.md"
        content = readme.read_text(encoding="utf-8")
        lines = content.splitlines()
        agent_eco_rows = [line for line in lines if "agent-ecosystem.instructions.md" in line]
        assert agent_eco_rows, "share/README.md must have a row for agent-ecosystem.instructions.md in the stubs table."
        row = agent_eco_rows[0]
        assert _FULL_APPLY_TO in row, (
            "share/README.md stubs row must contain the full canonical applyTo value "
            "(both share/ and .owlbear/ halves — partial .owlbear/-only mirrors are insufficient).\n"
            f"Expected substring: {_FULL_APPLY_TO!r}\n"
            f"Current row: {row!r}"
        )

    def test_h_agent_structure_stubs_row_mirrors_all_owlbear_paths(self, project_root: Path) -> None:
        """AC3 (exact): h-agent-structure stubs row contains full _FULL_APPLY_TO value, including share/ prefixes."""
        skill = project_root / "share" / "skills" / "h-agent-structure" / "SKILL.md"
        content = skill.read_text(encoding="utf-8")
        lines = content.splitlines()
        agent_eco_rows = [line for line in lines if "agent-ecosystem.instructions.md" in line]
        assert agent_eco_rows, "h-agent-structure SKILL.md must have a row for agent-ecosystem.instructions.md."
        row = agent_eco_rows[0]
        assert _FULL_APPLY_TO in row, (
            "h-agent-structure SKILL.md stubs row must contain the full canonical applyTo value "
            "(both share/ and .owlbear/ halves — partial .owlbear/-only mirrors are insufficient).\n"
            f"Expected substring: {_FULL_APPLY_TO!r}\n"
            f"Current row: {row!r}"
        )
