"""Tests for task #196: Add necessity check to code-review skill critical checks.

AC contract under test:
1. share/skills/w-code-review/SKILL.md: new section "### 6.6 Necessity check" inserted after
   existing 6.5, inside Step 6 (Pass 1: CRITICAL checks). Content includes:
   (a) Conditional gate using "> **Conditional:**" pattern, applied when task adds a
       new dependency/integration/tool/server/external capability; NOT triggered by
       bug fixes, refactors, renames, config tweaks, or test improvements.
   (b) Three questions: (1) IDE/runtime/extension already provides this?
       (2) Existing project tooling already solves this? (3) Presumptive feature?
   (c) If yes to any question: FAIL with evidence citing the existing provider.
2. agents/reviewer.agent.md: one new entry in "Red flags -- STOP and reassess" list:
   "You are about to PASS a feature addition without checking if the environment
   already provides it"
3. No other files modified (verified at review time via get_changed_files).
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
CODE_REVIEW_SKILL = ROOT / "share" / "skills" / "w-code-review" / "SKILL.md"
REVIEWER_AGENT = ROOT / "share" / "agents" / "reviewer.agent.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# AC 1: Section 6.6 Necessity check — structure
# ---------------------------------------------------------------------------


class TestFromAC_NecessityCheckSection:
    """AC 1: share/skills/w-code-review/SKILL.md must contain the new 6.6 section with
    correct placement and structural requirements."""

    def test_section_heading_exists(self) -> None:
        """Section '### 6.6 Necessity check' must appear in the skill file."""
        content = _read(CODE_REVIEW_SKILL)
        assert "### 6.6 Necessity check" in content, (
            "Expected '### 6.6 Necessity check' heading in share/skills/w-code-review/SKILL.md"
        )

    def test_section_66_appears_after_section_65(self) -> None:
        """Section 6.6 must appear after section 6.5 in the file (not before)."""
        content = _read(CODE_REVIEW_SKILL)
        pos_65 = content.find("### 6.5")
        pos_66 = content.find("### 6.6 Necessity check")
        assert pos_65 != -1, "Section 6.5 must exist as anchor for placement"
        assert pos_66 != -1, "Section 6.6 must exist"
        assert pos_66 > pos_65, (
            "Section 6.6 must appear after section 6.5 in the file"
        )

    def test_section_66_is_inside_step6_critical_checks(self) -> None:
        """Section 6.6 must be inside Step 6 (Pass 1: CRITICAL checks), not Step 7."""
        content = _read(CODE_REVIEW_SKILL)
        step6_marker = "## Step 6"
        step7_marker = "## Step 7"
        pos_step6 = content.find(step6_marker)
        pos_step7 = content.find(step7_marker)
        pos_66 = content.find("### 6.6 Necessity check")
        assert pos_step6 != -1, "Step 6 heading must exist"
        assert pos_66 != -1, "Section 6.6 must exist"
        assert pos_66 > pos_step6, "Section 6.6 must appear after '## Step 6'"
        if pos_step7 != -1:
            assert pos_66 < pos_step7, (
                "Section 6.6 must appear before '## Step 7' (inside Pass 1 checks)"
            )

    def test_no_phantom_section_67_added(self) -> None:
        """Builder must add only 6.6 — no extra 6.7 section should appear."""
        content = _read(CODE_REVIEW_SKILL)
        assert "### 6.7" not in content, (
            "No section 6.7 should exist — only 6.6 was requested by this task"
        )


# ---------------------------------------------------------------------------
# AC 1a: Conditional gate pattern
# ---------------------------------------------------------------------------


class TestFromAC_NecessityCheckConditionalGate:
    """AC 1(a): Section 6.6 must use the existing '> **Conditional:**' gate pattern
    and specify correct trigger and non-trigger conditions."""

    def test_conditional_gate_pattern_used(self) -> None:
        """Section 6.6 must use the '> **Conditional:**' pattern."""
        content = _read(CODE_REVIEW_SKILL)
        pos_66 = content.find("### 6.6 Necessity check")
        assert pos_66 != -1, "Section 6.6 must exist"
        # Look for the Conditional marker after section 6.6 heading
        section_text = _get_section_66_text(content)
        assert "> **Conditional:**" in section_text, (
            "Section 6.6 must use the '> **Conditional:**' gate pattern"
        )

    def test_gate_triggers_on_new_dependency(self) -> None:
        """Conditional gate must specify 'dependency' as a trigger."""
        section_text = _get_section_66_text(_read(CODE_REVIEW_SKILL))
        assert "dependency" in section_text.lower(), (
            "Conditional gate must list 'dependency' as a trigger condition"
        )

    def test_gate_triggers_on_new_tool(self) -> None:
        """Conditional gate must specify 'tool' as a trigger."""
        section_text = _get_section_66_text(_read(CODE_REVIEW_SKILL))
        # 'tool' appears in trigger context (not just 'tooling' in non-trigger)
        assert "tool" in section_text.lower(), (
            "Conditional gate must list 'tool' or 'tooling' as a trigger condition"
        )

    def test_gate_triggers_on_integration_or_server(self) -> None:
        """Conditional gate must specify 'integration' or 'server' as a trigger."""
        section_text = _get_section_66_text(_read(CODE_REVIEW_SKILL))
        text_lower = section_text.lower()
        assert "integration" in text_lower or "server" in text_lower, (
            "Conditional gate must list 'integration' and/or 'server' as trigger conditions"
        )

    def test_gate_not_triggered_by_bug_fix(self) -> None:
        """Conditional gate must explicitly exclude bug fixes."""
        section_text = _get_section_66_text(_read(CODE_REVIEW_SKILL))
        text_lower = section_text.lower()
        assert "bug fix" in text_lower or "bug fixes" in text_lower, (
            "Conditional gate must state it does NOT apply to bug fixes"
        )

    def test_gate_not_triggered_by_refactor_or_rename(self) -> None:
        """Conditional gate must explicitly exclude refactors and renames."""
        section_text = _get_section_66_text(_read(CODE_REVIEW_SKILL))
        text_lower = section_text.lower()
        assert "refactor" in text_lower or "rename" in text_lower, (
            "Conditional gate must state it does NOT apply to refactors/renames"
        )

    def test_gate_not_triggered_by_test_improvements(self) -> None:
        """Conditional gate must explicitly exclude test improvements."""
        section_text = _get_section_66_text(_read(CODE_REVIEW_SKILL))
        text_lower = section_text.lower()
        assert "test" in text_lower, (
            "Conditional gate must state it does NOT apply to test improvements"
        )


# ---------------------------------------------------------------------------
# AC 1b: Three questions
# ---------------------------------------------------------------------------


class TestFromAC_NecessityCheckQuestions:
    """AC 1(b): Section 6.6 must contain all three required reviewer questions."""

    def test_question_ide_runtime_extension(self) -> None:
        """Section 6.6 must ask whether the IDE, runtime, or extension already provides this."""
        section_text = _get_section_66_text(_read(CODE_REVIEW_SKILL))
        text_lower = section_text.lower()
        # AC specifies: "Does the IDE, runtime, or an installed extension already provide this?"
        assert "ide" in text_lower or ("runtime" in text_lower and "extension" in text_lower), (
            "Section 6.6 must ask whether the IDE, runtime, or an installed extension "
            "already provides the capability"
        )

    def test_question_existing_project_tooling(self) -> None:
        """Section 6.6 must ask whether existing project tooling already solves this."""
        section_text = _get_section_66_text(_read(CODE_REVIEW_SKILL))
        text_lower = section_text.lower()
        assert "tooling" in text_lower and "already" in text_lower, (
            "Section 6.6 must ask whether existing project tooling already solves this need"
        )

    def test_question_presumptive_feature(self) -> None:
        """Section 6.6 must ask whether this is a presumptive feature."""
        section_text = _get_section_66_text(_read(CODE_REVIEW_SKILL))
        text_lower = section_text.lower()
        assert "presumptive" in text_lower, (
            "Section 6.6 must ask whether this is a presumptive feature "
            "(building for speculated future need)"
        )

    def test_three_questions_present(self) -> None:
        """Section 6.6 must contain at least three numbered or bulleted questions."""
        section_text = _get_section_66_text(_read(CODE_REVIEW_SKILL))
        # Look for numbered items (1), (2), (3) or three question marks as evidence of 3 questions
        import re
        question_marks = section_text.count("?")
        numbered_items = re.findall(r"\(?[123]\)?[\.\)]", section_text)
        assert question_marks >= 3 or len(numbered_items) >= 3, (
            "Section 6.6 must contain at least three distinct reviewer questions"
        )


# ---------------------------------------------------------------------------
# AC 1c: FAIL outcome
# ---------------------------------------------------------------------------


class TestFromAC_NecessityCheckFailOutcome:
    """AC 1(c): Section 6.6 must describe FAIL outcome for 'yes' answers."""

    def test_fail_outcome_specified(self) -> None:
        """Section 6.6 must say FAIL when any question is answered yes."""
        section_text = _get_section_66_text(_read(CODE_REVIEW_SKILL))
        assert "FAIL" in section_text, (
            "Section 6.6 must specify FAIL as the outcome when any question is answered yes"
        )

    def test_fail_requires_evidence_citing_provider(self) -> None:
        """FAIL outcome must require citing the existing provider as evidence."""
        section_text = _get_section_66_text(_read(CODE_REVIEW_SKILL))
        text_lower = section_text.lower()
        assert "evidence" in text_lower or "citing" in text_lower or "provider" in text_lower, (
            "FAIL outcome in section 6.6 must cite the existing provider as evidence"
        )

    def test_yes_to_any_triggers_fail(self) -> None:
        """FAIL must be triggered if YES to ANY (not all) of the three questions."""
        section_text = _get_section_66_text(_read(CODE_REVIEW_SKILL))
        text_lower = section_text.lower()
        assert "any" in text_lower, (
            "Section 6.6 must state FAIL applies if yes to ANY (not all) questions"
        )


# ---------------------------------------------------------------------------
# AC 2: reviewer.agent.md red-flag entry
# ---------------------------------------------------------------------------


class TestFromAC_ReviewerRedFlag:
    """AC 2: agents/reviewer.agent.md must have a new red-flag entry for
    feature additions without necessity check."""

    def test_red_flag_entry_exists(self) -> None:
        """Red-flag: 'about to PASS a feature addition without checking if
        the environment already provides it' must be in reviewer.agent.md."""
        content = _read(REVIEWER_AGENT)
        # Test the key phrases that make this entry unique
        assert "feature addition" in content.lower() and "environment" in content.lower(), (
            "Expected a red-flag entry about PASS-ing a feature addition without "
            "checking if the environment already provides it"
        )

    def test_red_flag_is_in_red_flags_section(self) -> None:
        """The new entry must appear under 'Red flags -- STOP and reassess'."""
        content = _read(REVIEWER_AGENT)
        red_flags_pos = content.find("Red flags -- STOP and reassess")
        assert red_flags_pos != -1, "'Red flags -- STOP and reassess' section must exist"
        # Find the feature-addition entry after the red-flags heading
        feature_flag_pos = content.lower().find("feature addition", red_flags_pos)
        assert feature_flag_pos != -1, (
            "Feature addition red-flag entry must appear after "
            "'Red flags -- STOP and reassess' heading"
        )

    def test_red_flag_mentions_pass_verb(self) -> None:
        """The red-flag entry must specifically warn about issuing a PASS."""
        content = _read(REVIEWER_AGENT)
        red_flags_pos = content.find("Red flags -- STOP and reassess")
        # Extract the section starting from red flags heading to find the new entry
        section = content[red_flags_pos:]
        feature_flag_pos = section.lower().find("feature addition")
        assert feature_flag_pos != -1, "Feature addition entry not found in red-flags section"
        # Check PASS is mentioned near the feature addition entry (within 200 chars)
        surrounding = section[max(0, feature_flag_pos - 50): feature_flag_pos + 200]
        assert "PASS" in surrounding, (
            "Red-flag entry must mention PASS (warning about issuing a PASS verdict)"
        )

    def test_only_one_new_red_flag_added(self) -> None:
        """AC specifies exactly one new red-flag entry — verify count didn't explode.
        Current count is 16; new count must be exactly 17."""
        content = _read(REVIEWER_AGENT)
        red_flags_pos = content.find("Red flags -- STOP and reassess")
        assert red_flags_pos != -1, "'Red flags -- STOP and reassess' section must exist"
        # Find end of section (next </ or ## or end of file)
        import re
        section_end = re.search(r"\n(##|</)", content[red_flags_pos:])
        if section_end:
            section = content[red_flags_pos: red_flags_pos + section_end.start()]
        else:
            section = content[red_flags_pos:]
        # Count bullet items (lines starting with "- ")
        bullet_count = len(re.findall(r"^\s*- ", section, re.MULTILINE))
        assert bullet_count == 17, (
            f"Expected exactly 17 red-flag entries (16 original + 1 new), got {bullet_count}"
        )


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _get_section_66_text(content: str) -> str:
    """Extract the text of section 6.6 from the skill file content.

    Returns everything from '### 6.6 Necessity check' up to the next
    '### 6.' heading or end of file.
    """
    start = content.find("### 6.6 Necessity check")
    if start == -1:
        pytest.fail(
            "Section '### 6.6 Necessity check' not found in share/skills/w-code-review/SKILL.md"
        )
    # Find the next section heading after 6.6
    next_section = content.find("### 6.", start + 1)
    step7 = content.find("## Step 7", start)
    # Take whichever boundary comes first
    candidates = [pos for pos in [next_section, step7] if pos != -1]
    end = min(candidates) if candidates else len(content)
    return content[start:end]
