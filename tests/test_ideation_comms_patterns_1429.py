"""Failing tests for task #1429: P1-01 — Communication Patterns section in h-ideation/SKILL.md.

All tests FAIL on the current codebase (section does not exist yet); they pass once
the builder adds the new ## Communication Patterns section per the task AC.

AC coverage:
  AC1  — test_communication_patterns_section_exists
  AC2  — test_vocabulary_table_header_present,
          test_vocabulary_table_all_entries,
          test_vocabulary_table_minimum_row_count,
          test_vocabulary_table_three_columns
  AC3  — test_repeated_mention_rule_stated
  AC4  — test_narration_principles_subsection_exists,
          test_narration_principles_six_keywords,
          test_narration_principles_six_bullets
  AC5  — test_transition_patterns_table_exists,
          test_transition_patterns_six_rows
  AC6  — test_boundary_heuristic_table_exists,
          test_boundary_heuristic_four_rows
  AC7  — test_depth_control_table_exists,
          test_depth_control_three_disclosure_levels
  AC8  — test_six_before_markers,
          test_six_after_markers,
          test_before_after_pairs_balanced
  AC9  — test_m35_o15_not_in_directive_guidance
  AC10 — test_section_after_handoff_contract,
          test_section_before_cross_references
"""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
_SKILL_FILE = _REPO_ROOT / "share" / "skills" / "h-ideation" / "SKILL.md"

# All 17 internal names required in the vocabulary table per the brief.
_VOCABULARY_ENTRIES = (
    "ideation-architect",
    "ideation-data",
    "ideation-enduser",
    "ideation-security",
    "ideation-critic",
    "ideation-simplifier",
    "ideation-firstprinciples",
    "ideation-pragmatist",
    "M1 / Understanding",
    "M2 / Outcomes",
    "M3 / Landscape",
    "M3.5 / Design It Twice",
    "M4 / Decision",
    "M5 / Brief",
    "M6 / Handoff",
    "O15",
    "Investment Tier",
)

# Keywords anchoring the 6 Narration Principles from the brief.
_NARRATION_PRINCIPLE_KEYWORDS = (
    "Results, not mechanisms",
    "Conditional gates are never announced",
    "Purpose before process",
    "visible with context",       # "Labels stay visible with context (D4)"
    "Attribution by name",        # "Attribution by name with explanation (D6)"
    "Compliance is explanation",  # "Compliance is explanation quality"
)

# Disclosure Ladder level names required in the Depth-Control table.
_DISCLOSURE_LADDER_LEVELS = (
    "Default Summary",
    "Concrete Specifics",
    "Inline Verbatim Evidence",
)


def _extract_section(content: str, heading: str) -> str | None:
    """Return the body of a ## or ### heading up to the next same-or-higher heading.

    Returns None if the heading is not found.
    """
    pattern = re.compile(
        rf"(?m)^{re.escape(heading)}\b(.*?)(?=\n#+\s|\Z)",
        re.DOTALL,
    )
    m = pattern.search(content)
    return m.group(1) if m else None


def _count_table_data_rows(section_text: str, header_col: str) -> int:
    """Count data rows in a Markdown table, excluding header and separator rows.

    ``header_col`` is a substring unique to the header row (used to skip it).
    """
    data_rows = []
    for line in section_text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        # Skip separator row (---|---| style)
        if re.match(r"^\|[-| :]+\|$", stripped):
            continue
        # Skip header row
        if header_col in stripped:
            continue
        data_rows.append(stripped)
    return len(data_rows)


class TestFromAC_CommunicationPatternsSection:
    """AC1 — ## Communication Patterns section must exist in h-ideation/SKILL.md."""

    def test_communication_patterns_section_exists(self) -> None:
        """## Communication Patterns heading must be present in h-ideation/SKILL.md."""
        content = _SKILL_FILE.read_text(encoding="utf-8")
        assert "## Communication Patterns" in content, (
            "h-ideation/SKILL.md is missing the '## Communication Patterns' section"
        )


class TestFromAC_VocabularyTable:
    """AC2 — Vocabulary table with all entries from the brief (≥17 data rows, 3 columns)."""

    def test_vocabulary_table_header_present(self) -> None:
        """Vocabulary table must have 'Internal Name' as the first column header."""
        content = _SKILL_FILE.read_text(encoding="utf-8")
        section = _extract_section(content, "## Communication Patterns")
        assert section is not None, "## Communication Patterns section not found"
        assert "Internal Name" in section, (
            "Vocabulary table missing 'Internal Name' column header inside "
            "## Communication Patterns"
        )

    def test_vocabulary_table_all_entries(self) -> None:
        """All 17 internal names from the brief must appear in the file."""
        content = _SKILL_FILE.read_text(encoding="utf-8")
        missing = [entry for entry in _VOCABULARY_ENTRIES if entry not in content]
        assert not missing, (
            f"h-ideation/SKILL.md missing vocabulary entries: {missing}"
        )

    def test_vocabulary_table_minimum_row_count(self) -> None:
        """Vocabulary table must have at least 17 data rows."""
        content = _SKILL_FILE.read_text(encoding="utf-8")
        section = _extract_section(content, "## Communication Patterns")
        assert section is not None, "## Communication Patterns section not found"
        row_count = _count_table_data_rows(section, "Internal Name")
        assert row_count >= 17, (
            f"Vocabulary table has {row_count} data row(s); expected ≥17"
        )

    def test_vocabulary_table_three_columns(self) -> None:
        """Every vocabulary data row must have exactly 3 pipe-separated columns."""
        content = _SKILL_FILE.read_text(encoding="utf-8")
        section = _extract_section(content, "## Communication Patterns")
        assert section is not None, "## Communication Patterns section not found"

        violations: list[str] = []
        for line in section.splitlines():
            stripped = line.strip()
            if not stripped.startswith("|"):
                continue
            if re.match(r"^\|[-| :]+\|$", stripped):  # separator
                continue
            if "Internal Name" in stripped:  # header row
                continue
            cols = [c.strip() for c in stripped.strip("|").split("|")]
            if len(cols) != 3:
                violations.append(f"  {stripped!r} → {len(cols)} column(s)")

        assert not violations, (
            "Vocabulary table rows with wrong column count:\n" + "\n".join(violations)
        )


class TestFromAC_RepeatedMentionRule:
    """AC3 — 'Repeated-mention rule' must be stated in the section."""

    def test_repeated_mention_rule_stated(self) -> None:
        """'Repeated-mention rule' phrase must appear in h-ideation/SKILL.md."""
        content = _SKILL_FILE.read_text(encoding="utf-8")
        assert "Repeated-mention rule" in content, (
            "h-ideation/SKILL.md missing the 'Repeated-mention rule' statement"
        )


class TestFromAC_NarrationPrinciples:
    """AC4 — Narration Principles subsection with 6 bullet points from the brief."""

    def test_narration_principles_subsection_exists(self) -> None:
        """'Narration Principles' subsection heading must be present."""
        content = _SKILL_FILE.read_text(encoding="utf-8")
        assert "Narration Principles" in content, (
            "h-ideation/SKILL.md missing 'Narration Principles' subsection"
        )

    def test_narration_principles_six_keywords(self) -> None:
        """All 6 narration principle anchor keywords from the brief must be present."""
        content = _SKILL_FILE.read_text(encoding="utf-8")
        missing = [kw for kw in _NARRATION_PRINCIPLE_KEYWORDS if kw not in content]
        assert not missing, (
            f"Narration Principles missing required keywords: {missing}"
        )

    def test_narration_principles_six_bullets(self) -> None:
        """The Narration Principles subsection must contain exactly 6 list bullets."""
        content = _SKILL_FILE.read_text(encoding="utf-8")
        subsection = _extract_section(content, "### Narration Principles")
        if subsection is None:
            # Try without ### in case it's formatted differently
            subsection = _extract_section(content, "#### Narration Principles")
        assert subsection is not None, (
            "'Narration Principles' subsection not found under ## Communication Patterns"
        )
        bullets = [
            ln for ln in subsection.splitlines() if ln.strip().startswith("- ")
        ]
        assert len(bullets) == 6, (
            f"Narration Principles has {len(bullets)} bullet(s); expected exactly 6"
        )


class TestFromAC_TransitionPatterns:
    """AC5 — Transition Patterns table with exactly 6 data rows."""

    def test_transition_patterns_table_exists(self) -> None:
        """'Transition Patterns' table heading must be present."""
        content = _SKILL_FILE.read_text(encoding="utf-8")
        assert "Transition Patterns" in content, (
            "h-ideation/SKILL.md missing 'Transition Patterns' table"
        )

    def test_transition_patterns_six_rows(self) -> None:
        """Transition Patterns table must have exactly 6 data rows."""
        content = _SKILL_FILE.read_text(encoding="utf-8")
        subsection = _extract_section(content, "### Transition Patterns")
        if subsection is None:
            subsection = _extract_section(content, "#### Transition Patterns")
        assert subsection is not None, (
            "'Transition Patterns' subsection not found"
        )
        row_count = _count_table_data_rows(subsection, "Transition")
        assert row_count == 6, (
            f"Transition Patterns table has {row_count} data row(s); expected exactly 6"
        )


class TestFromAC_BoundaryHeuristic:
    """AC6 — Boundary Heuristic table with exactly 4 data rows."""

    def test_boundary_heuristic_table_exists(self) -> None:
        """'Boundary Heuristic' table heading must be present."""
        content = _SKILL_FILE.read_text(encoding="utf-8")
        assert "Boundary Heuristic" in content, (
            "h-ideation/SKILL.md missing 'Boundary Heuristic' table"
        )

    def test_boundary_heuristic_four_rows(self) -> None:
        """Boundary Heuristic table must have exactly 4 data rows."""
        content = _SKILL_FILE.read_text(encoding="utf-8")
        subsection = _extract_section(content, "### Boundary Heuristic")
        if subsection is None:
            subsection = _extract_section(content, "#### Boundary Heuristic")
        assert subsection is not None, (
            "'Boundary Heuristic' subsection not found"
        )
        row_count = _count_table_data_rows(subsection, "Situation")
        assert row_count == 4, (
            f"Boundary Heuristic table has {row_count} data row(s); expected exactly 4"
        )


class TestFromAC_DepthControlVerbalCues:
    """AC7 — Depth-Control Verbal Cues table with 3 Disclosure Ladder levels."""

    def test_depth_control_table_exists(self) -> None:
        """'Depth-Control Verbal Cues' table heading must be present."""
        content = _SKILL_FILE.read_text(encoding="utf-8")
        assert "Depth-Control Verbal Cues" in content, (
            "h-ideation/SKILL.md missing 'Depth-Control Verbal Cues' table"
        )

    def test_depth_control_three_disclosure_levels(self) -> None:
        """All three Disclosure Ladder level names must appear in the file."""
        content = _SKILL_FILE.read_text(encoding="utf-8")
        missing = [lvl for lvl in _DISCLOSURE_LADDER_LEVELS if lvl not in content]
        assert not missing, (
            f"Depth-Control Verbal Cues table missing Disclosure Ladder levels: {missing}"
        )

    def test_depth_control_three_rows(self) -> None:
        """Depth-Control Verbal Cues table must have exactly 3 data rows."""
        content = _SKILL_FILE.read_text(encoding="utf-8")
        subsection = _extract_section(content, "### Depth-Control Verbal Cues")
        if subsection is None:
            subsection = _extract_section(content, "#### Depth-Control Verbal Cues")
        assert subsection is not None, (
            "'Depth-Control Verbal Cues' subsection not found"
        )
        row_count = _count_table_data_rows(subsection, "Level")
        assert row_count == 3, (
            f"Depth-Control Verbal Cues table has {row_count} data row(s); expected exactly 3"
        )


class TestFromAC_BeforeAfterExamples:
    """AC8 — Exactly 6 before/after example pairs in the Communication Patterns section."""

    def _get_section(self) -> str:
        content = _SKILL_FILE.read_text(encoding="utf-8")
        section = _extract_section(content, "## Communication Patterns")
        assert section is not None, "## Communication Patterns section not found"
        return section

    def test_six_before_markers(self) -> None:
        """Communication Patterns section must contain exactly 6 '**Before:**' markers."""
        section = self._get_section()
        count = len(re.findall(r"\*\*Before:\*\*", section))
        assert count == 6, (
            f"Found {count} '**Before:**' marker(s) in Communication Patterns; expected 6"
        )

    def test_six_after_markers(self) -> None:
        """Communication Patterns section must contain exactly 6 '**After:**' markers."""
        section = self._get_section()
        count = len(re.findall(r"\*\*After:\*\*", section))
        assert count == 6, (
            f"Found {count} '**After:**' marker(s) in Communication Patterns; expected 6"
        )

    def test_before_after_pairs_balanced(self) -> None:
        """Before and After marker counts must be equal (each example is a pair)."""
        section = self._get_section()
        before_count = len(re.findall(r"\*\*Before:\*\*", section))
        after_count = len(re.findall(r"\*\*After:\*\*", section))
        assert before_count == after_count, (
            f"Before/After pair counts are unbalanced: "
            f"{before_count} Before vs {after_count} After"
        )


class TestFromAC_JargonGuard:
    """AC9 — Within Communication Patterns, M3.5 and O15 appear only in appropriate places.

    Permitted locations inside the section:
      - Table rows (lines starting with |) — vocabulary table entries
      - Lines inside a **Before:** example block
      - Section/subsection headings (lines starting with #)

    Any other occurrence is a jargon-laundering violation: the agent is being instructed
    to SAY an internal protocol code, which the section explicitly prohibits.
    """

    def test_m35_o15_not_in_directive_guidance(self) -> None:
        """Inside ## Communication Patterns, M3.5 and O15 must not appear in guidance prose.

        Equivalent to: grep -n 'M3\\.5\\|O15' share/skills/h-ideation/SKILL.md
        with all hits inside example 'Before:' blocks, vocabulary table rows, or headings.
        """
        content = _SKILL_FILE.read_text(encoding="utf-8")
        section = _extract_section(content, "## Communication Patterns")
        assert section is not None, "## Communication Patterns section not found"

        violations: list[tuple[int, str]] = []
        in_before_block = False

        for lineno, line in enumerate(section.splitlines(), start=1):
            stripped = line.strip()

            # Track entry into a **Before:** block
            if "**Before:**" in stripped:
                in_before_block = True
            # **After:** or a blank line exits the Before block
            elif "**After:**" in stripped or stripped == "":
                in_before_block = False

            is_table_row = stripped.startswith("|")
            is_heading = stripped.startswith("#")

            if re.search(r"\bM3\.5\b|\bO15\b", line) and not in_before_block and not is_table_row and not is_heading:
                violations.append((lineno, stripped))

        assert not violations, (
            "In ## Communication Patterns, M3.5 / O15 appear outside permitted contexts "
            "(Before: blocks, vocabulary table rows, headings):\n"
            + "\n".join(f"  line {ln}: {txt!r}" for ln, txt in violations)
        )


class TestFromAC_SectionPlacement:
    """AC10 — Section appears after existing shared rules, before workflow-specific content."""

    def test_section_after_handoff_contract(self) -> None:
        """## Communication Patterns must appear after ## Handoff Contract."""
        content = _SKILL_FILE.read_text(encoding="utf-8")
        handoff_pos = content.find("## Handoff Contract")
        comm_pos = content.find("## Communication Patterns")

        assert handoff_pos != -1, "## Handoff Contract not found in h-ideation/SKILL.md"
        assert comm_pos != -1, "## Communication Patterns not found in h-ideation/SKILL.md"
        assert comm_pos > handoff_pos, (
            "## Communication Patterns must come AFTER ## Handoff Contract; "
            f"found at offset {comm_pos} vs Handoff Contract at {handoff_pos}"
        )

    def test_section_before_cross_references(self) -> None:
        """## Communication Patterns must appear before ## Cross-References."""
        content = _SKILL_FILE.read_text(encoding="utf-8")
        comm_pos = content.find("## Communication Patterns")
        cross_pos = content.find("## Cross-References")

        assert comm_pos != -1, "## Communication Patterns not found in h-ideation/SKILL.md"
        assert cross_pos != -1, "## Cross-References not found in h-ideation/SKILL.md"
        assert comm_pos < cross_pos, (
            "## Communication Patterns must come BEFORE ## Cross-References; "
            f"found at offset {comm_pos} vs Cross-References at {cross_pos}"
        )
