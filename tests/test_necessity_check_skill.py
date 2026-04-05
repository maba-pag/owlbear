"""Tests for task #196 — Add necessity check to code-review skill critical checks.

Verifies that:
- share/skills/w-code-review/SKILL.md gains a "### 6.6 Necessity check" section
- agents/reviewer.agent.md gains a new red-flag entry about feature additions
"""

from __future__ import annotations

from pathlib import Path

SKILL_FILE = Path(__file__).parent.parent / "share" / "skills" / "w-code-review" / "SKILL.md"
REVIEWER_AGENT_FILE = Path(__file__).parent.parent / "share" / "agents" / "reviewer.agent.md"


def _extract_section(content: str, section_start_idx: int) -> str:
    """Extract a section's text up to the next heading.

    Args:
        content: Full file content.
        section_start_idx: Character index where the section header begins.

    Returns:
        Text of the section from the header to the start of the next heading.
    """
    section = content[section_start_idx:]
    next_heading = section.find("\n##", 4)
    if next_heading == -1:
        return section
    return section[:next_heading]


class TestFromAC_NecessityCheckSection:
    """Tests for AC line 1: share/skills/w-code-review/SKILL.md must gain ### 6.6 Necessity check."""

    # ------------------------------------------------------------------ happy path

    def test_section_66_exists(self) -> None:
        """'### 6.6 Necessity check' must be present in the skill file."""
        content = SKILL_FILE.read_text(encoding="utf-8")
        assert "### 6.6 Necessity check" in content

    def test_section_66_is_after_section_65(self) -> None:
        """Section 6.6 must appear after section 6.5 in the file."""
        content = SKILL_FILE.read_text(encoding="utf-8")
        idx_65 = content.find("### 6.5")
        idx_66 = content.find("### 6.6 Necessity check")
        assert idx_65 != -1, "Section 6.5 must exist as anchor"
        assert idx_66 != -1, "Section 6.6 must exist"
        assert idx_66 > idx_65, "Section 6.6 must appear after section 6.5"

    def test_section_66_inside_step_6_pass_1(self) -> None:
        """Section 6.6 must be inside Step 6 (Pass 1: CRITICAL checks)."""
        content = SKILL_FILE.read_text(encoding="utf-8")
        # Step 6 header and Pass-2 header bracket the section
        idx_step6 = content.find("## Step 6")
        idx_step7 = content.find("## Step 7")
        idx_66 = content.find("### 6.6 Necessity check")
        assert idx_step6 != -1, "Step 6 must exist"
        assert idx_step7 != -1, "Step 7 must exist"
        assert idx_66 != -1, "Section 6.6 must exist"
        assert idx_step6 < idx_66 < idx_step7, (
            "Section 6.6 must be between Step 6 and Step 7"
        )

    # -------------------------------------------------------------- conditional gate

    def test_section_66_has_conditional_gate(self) -> None:
        """Section 6.6 must use the '> **Conditional:**' blockquote gate pattern."""
        content = SKILL_FILE.read_text(encoding="utf-8")
        idx_66 = content.find("### 6.6 Necessity check")
        assert idx_66 != -1, "Section 6.6 must exist"
        section_66 = _extract_section(content, idx_66)
        assert "> **Conditional:**" in section_66

    def test_section_66_conditional_triggers_on_new_capability(self) -> None:
        """Conditional gate must name the triggering additions (dependency, integration, tool, server, external capability)."""
        content = SKILL_FILE.read_text(encoding="utf-8")
        idx_66 = content.find("### 6.6 Necessity check")
        assert idx_66 != -1, "Section 6.6 must exist"
        section_66 = _extract_section(content, idx_66)
        trigger_terms = [
            "dependency",
            "integration",
            "tool",
            "server",
            "external capability",
        ]
        assert any(t in section_66 for t in trigger_terms), (
            f"Conditional gate must name at least one of: {trigger_terms}"
        )

    def test_section_66_conditional_excludes_bug_fixes(self) -> None:
        """Conditional gate must explicitly exclude bug fixes from triggering."""
        content = SKILL_FILE.read_text(encoding="utf-8")
        idx_66 = content.find("### 6.6 Necessity check")
        assert idx_66 != -1, "Section 6.6 must exist"
        section_66 = _extract_section(content, idx_66)
        assert "bug fix" in section_66 or "bug fixes" in section_66, (
            "Conditional gate must exclude bug fixes"
        )

    def test_section_66_conditional_excludes_refactors(self) -> None:
        """Conditional gate must explicitly exclude refactors from triggering."""
        content = SKILL_FILE.read_text(encoding="utf-8")
        idx_66 = content.find("### 6.6 Necessity check")
        assert idx_66 != -1, "Section 6.6 must exist"
        section_66 = _extract_section(content, idx_66)
        assert "refactor" in section_66, "Conditional gate must exclude refactors"

    # --------------------------------------------------------------- three questions

    def test_section_66_has_three_numbered_questions(self) -> None:
        """Section 6.6 must enumerate exactly three reviewer questions."""
        content = SKILL_FILE.read_text(encoding="utf-8")
        idx_66 = content.find("### 6.6 Necessity check")
        assert idx_66 != -1, "Section 6.6 must exist"
        section_66 = _extract_section(content, idx_66)
        # Accept any canonical numbering: (1)/(2)/(3) or 1./2./3.
        has_three = (
            "(1)" in section_66 and "(2)" in section_66 and "(3)" in section_66
        ) or (
            "1." in section_66 and "2." in section_66 and "3." in section_66
        )
        assert has_three, (
            "Section 6.6 must contain three numbered questions — (1)/(2)/(3) or 1./2./3."
        )

    def test_section_66_question_1_about_ide_runtime_extension(self) -> None:
        """Question 1 must ask whether the IDE, runtime, or installed extension already provides the capability."""
        content = SKILL_FILE.read_text(encoding="utf-8")
        idx_66 = content.find("### 6.6 Necessity check")
        assert idx_66 != -1, "Section 6.6 must exist"
        section_66 = _extract_section(content, idx_66)
        has_ide = "IDE" in section_66
        has_runtime = "runtime" in section_66
        has_extension = "extension" in section_66
        assert has_ide or has_runtime, (
            "Question 1 must mention 'IDE' or 'runtime'"
        )
        assert has_extension, "Question 1 must mention 'extension'"

    def test_section_66_question_2_about_existing_project_tooling(self) -> None:
        """Question 2 must ask whether existing project tooling already solves the need."""
        content = SKILL_FILE.read_text(encoding="utf-8")
        idx_66 = content.find("### 6.6 Necessity check")
        assert idx_66 != -1, "Section 6.6 must exist"
        section_66 = _extract_section(content, idx_66)
        assert "project tooling" in section_66 or (
            "existing" in section_66 and "tooling" in section_66
        ), "Question 2 must mention 'project tooling' or 'existing … tooling'"

    def test_section_66_question_3_about_presumptive_feature(self) -> None:
        """Question 3 must ask about presumptive features (building for speculated future need)."""
        content = SKILL_FILE.read_text(encoding="utf-8")
        idx_66 = content.find("### 6.6 Necessity check")
        assert idx_66 != -1, "Section 6.6 must exist"
        section_66 = _extract_section(content, idx_66)
        assert "presumptive" in section_66, (
            "Question 3 must use the word 'presumptive'"
        )

    # --------------------------------------------------------- fail-if-yes contract

    def test_section_66_instructs_fail_with_evidence_if_yes(self) -> None:
        """Section 6.6 must tell the reviewer to FAIL with evidence when yes to any question."""
        content = SKILL_FILE.read_text(encoding="utf-8")
        idx_66 = content.find("### 6.6 Necessity check")
        assert idx_66 != -1, "Section 6.6 must exist"
        section_66 = _extract_section(content, idx_66)
        assert "FAIL" in section_66, "Section 6.6 must instruct FAIL"
        assert "evidence" in section_66, "Section 6.6 must require evidence when failing"

    def test_section_66_cites_existing_provider_in_fail_instruction(self) -> None:
        """The FAIL instruction must reference citing the existing provider."""
        content = SKILL_FILE.read_text(encoding="utf-8")
        idx_66 = content.find("### 6.6 Necessity check")
        assert idx_66 != -1, "Section 6.6 must exist"
        section_66 = _extract_section(content, idx_66)
        assert "provider" in section_66 or "provides" in section_66, (
            "FAIL instruction must mention the existing provider"
        )

    # --------------------------------------------------------- boundary: no section 6.7+

    def test_no_section_67_introduced(self) -> None:
        """Task scopes to 6.6 only; no 6.7 or higher should appear unless pre-existing."""
        content = SKILL_FILE.read_text(encoding="utf-8")
        # 6.6 should exist (validated above) and 6.7 should NOT be introduced by this change
        # We only forbid 6.7 if 6.6 doesn't exist yet as a proxy for the file not having been touched
        idx_66 = content.find("### 6.6 Necessity check")
        assert idx_66 != -1, "Section 6.6 must exist after builder's change"
        idx_67 = content.find("### 6.7")
        assert idx_67 == -1, "Section 6.7 must not be introduced; only 6.6 is in scope"


class TestFromAC_ReviewerAgentRedFlag:
    """Tests for AC line 2: agents/reviewer.agent.md must gain a new red-flag entry."""

    # ------------------------------------------------------------------ happy path

    def test_new_red_flag_entry_exists(self) -> None:
        """The exact red-flag sentence must appear in the reviewer agent file."""
        content = REVIEWER_AGENT_FILE.read_text(encoding="utf-8")
        expected = (
            "You are about to PASS a feature addition without checking if "
            "the environment already provides it"
        )
        assert expected in content, (
            f"reviewer.agent.md must contain: {expected!r}"
        )

    def test_new_red_flag_is_inside_red_flags_section(self) -> None:
        """The new entry must appear after the 'Red flags — STOP and reassess' heading."""
        content = REVIEWER_AGENT_FILE.read_text(encoding="utf-8")
        red_flags_idx = content.find("Red flags \u2014 STOP and reassess")
        # Also try ASCII dash variant for robustness
        if red_flags_idx == -1:
            red_flags_idx = content.find("Red flags -- STOP and reassess")
        assert red_flags_idx != -1, "Red flags section must exist in reviewer.agent.md"
        flag_text = (
            "You are about to PASS a feature addition without checking if "
            "the environment already provides it"
        )
        flag_idx = content.find(flag_text)
        assert flag_idx != -1, "New red-flag entry must exist"
        assert flag_idx > red_flags_idx, (
            "New entry must appear after the 'Red flags — STOP and reassess' heading"
        )

    # ------------------------------------------------------------------ edge cases

    def test_red_flag_is_bullet_list_item(self) -> None:
        """The new entry must be formatted as a bullet list item (starts with '- ')."""
        content = REVIEWER_AGENT_FILE.read_text(encoding="utf-8")
        flag_text = (
            "You are about to PASS a feature addition without checking if "
            "the environment already provides it"
        )
        flag_idx = content.find(flag_text)
        assert flag_idx != -1, "New red-flag entry must exist"
        # Walk backwards to the start of the line
        line_start = content.rfind("\n", 0, flag_idx) + 1
        line = content[line_start : flag_idx + len(flag_text)]
        assert line.lstrip().startswith("- "), (
            "Red-flag entry must be a bullet list item starting with '- '"
        )
