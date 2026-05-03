"""Tests for P1-03: cross-reference updates for agent-ecosystem.instructions.md applyTo extension.

Verifies that the applyTo field in agent-ecosystem.instructions.md is extended to include
.owlbear/ paths, and that all mirror copies (share/README.md, h-agent-structure SKILL.md,
share/WIRING.md Table 2, share/WIRING.md Gap Analysis) reflect the new scope.

AC coverage:
- AC1: agent-ecosystem.instructions.md YAML applyTo includes .owlbear/ paths (td:1)
- AC2: share/README.md stubs table mirrors .owlbear/ paths (td:1)
- AC3: h-agent-structure SKILL.md stubs table mirrors .owlbear/ paths (td:1)
- AC4: WIRING.md Table 2 agent-ecosystem.instructions row includes .owlbear/ scope (td:1)
- AC5: WIRING.md Gap Analysis agent-ecosystem.instructions notes reflect .owlbear/ scope (td:1)
"""

from __future__ import annotations

from pathlib import Path

_EXPECTED_OWLBEAR_PATHS = [
    ".owlbear/agents/**",
    ".owlbear/skills/**",
    ".owlbear/instructions/**",
    ".owlbear/prompts/**",
]


class TestFromAC_ApplyToExtension:
    """AC1-AC5: agent-ecosystem.instructions.md applyTo extended and mirrored in all locations."""

    def test_agent_ecosystem_instructions_apply_to_includes_owlbear_paths(
        self, project_root: Path
    ) -> None:
        """AC1: agent-ecosystem.instructions.md YAML applyTo field includes all .owlbear/ paths."""
        stub = (
            project_root
            / "share"
            / "instructions"
            / "agent-ecosystem.instructions.md"
        )
        content = stub.read_text(encoding="utf-8")
        for path in _EXPECTED_OWLBEAR_PATHS:
            assert path in content, (
                f"agent-ecosystem.instructions.md applyTo must include {path!r}.\n"
                f"Current applyTo is missing .owlbear/ paths — needs extension per AC1."
            )

    def test_readme_instruction_stubs_table_mirrors_owlbear_paths(
        self, project_root: Path
    ) -> None:
        """AC2: share/README.md stubs table agent-ecosystem.instructions.md row mirrors AC1 applyTo."""
        readme = project_root / "share" / "README.md"
        content = readme.read_text(encoding="utf-8")
        # Find the row for agent-ecosystem.instructions.md in the stubs table
        lines = content.splitlines()
        agent_eco_rows = [
            line for line in lines if "agent-ecosystem.instructions.md" in line
        ]
        assert agent_eco_rows, (
            "share/README.md must have a row for agent-ecosystem.instructions.md in the stubs table."
        )
        row = agent_eco_rows[0]
        assert ".owlbear/agents/**" in row, (
            "share/README.md stubs table agent-ecosystem.instructions.md row must include "
            ".owlbear/agents/** to mirror the AC1 applyTo extension.\n"
            f"Current row: {row!r}"
        )

    def test_h_agent_structure_stubs_table_mirrors_owlbear_paths(
        self, project_root: Path
    ) -> None:
        """AC3: h-agent-structure SKILL.md stubs table agent-ecosystem.instructions.md row mirrors AC1."""
        skill = (
            project_root
            / "share"
            / "skills"
            / "h-agent-structure"
            / "SKILL.md"
        )
        content = skill.read_text(encoding="utf-8")
        lines = content.splitlines()
        agent_eco_rows = [
            line for line in lines if "agent-ecosystem.instructions.md" in line
        ]
        assert agent_eco_rows, (
            "h-agent-structure SKILL.md must have a row for agent-ecosystem.instructions.md."
        )
        row = agent_eco_rows[0]
        assert ".owlbear/agents/**" in row, (
            "h-agent-structure SKILL.md stubs table agent-ecosystem.instructions.md row must include "
            ".owlbear/agents/** to mirror the AC1 applyTo extension.\n"
            f"Current row: {row!r}"
        )

    def test_wiring_table2_agent_ecosystem_row_includes_owlbear_scope(
        self, project_root: Path
    ) -> None:
        """AC4: WIRING.md Table 2 agent-ecosystem.instructions Seldom column mentions .owlbear/ files."""
        wiring = project_root / "share" / "WIRING.md"
        content = wiring.read_text(encoding="utf-8")
        lines = content.splitlines()
        # Table 2 row has "agent-ecosystem.instructions" and the backtick-quoted applyTo value
        table2_rows = [
            line
            for line in lines
            if "agent-ecosystem.instructions" in line and "applyTo:" in line
        ]
        assert table2_rows, (
            "WIRING.md Table 2 must have an agent-ecosystem.instructions row with an applyTo reference."
        )
        row = table2_rows[0]
        assert ".owlbear/" in row, (
            "WIRING.md Table 2 agent-ecosystem.instructions row must include .owlbear/ scope "
            "in the Seldom column description or abbreviated applyTo.\n"
            f"Current row: {row!r}"
        )

    def test_wiring_gap_analysis_agent_ecosystem_notes_mention_owlbear(
        self, project_root: Path
    ) -> None:
        """AC5: WIRING.md Gap Analysis agent-ecosystem.instructions notes reflect .owlbear/ scope."""
        wiring = project_root / "share" / "WIRING.md"
        content = wiring.read_text(encoding="utf-8")
        lines = content.splitlines()
        # Gap Analysis row has "agent-ecosystem.instructions" but not "applyTo:"
        gap_rows = [
            line
            for line in lines
            if "agent-ecosystem.instructions" in line and "applyTo:" not in line
        ]
        assert gap_rows, (
            "WIRING.md Gap Analysis must have a row for agent-ecosystem.instructions."
        )
        assert any(".owlbear/" in row for row in gap_rows), (
            "WIRING.md Gap Analysis agent-ecosystem.instructions notes must reflect .owlbear/ scope.\n"
            f"Current rows: {gap_rows!r}"
        )
