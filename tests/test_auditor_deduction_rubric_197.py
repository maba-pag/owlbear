"""Tests for task #197: Calibrate auditor confidence scoring with deduction rubric.

Contract-level verification that the deduction rubric and related content are
present in the target instruction files after the builder's changes.

AC coverage:
  - AC1: .github/skills/w-task-verification/SKILL.md Step 3 updated with deduction rubric
         (start at 1.0, deduct per criterion)
  - AC2: All 5 deduction criteria present with correct numeric values
  - AC3: agents/auditor.agent.md red-flags list updated with specific text
  - AC4: Channel B template in auditor.agent.md includes deduction breakdown
         (score is not just a number)
"""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
_SKILL_FILE = _REPO_ROOT / ".github" / "skills" / "w-task-verification" / "SKILL.md"
_AUDITOR_FILE = _REPO_ROOT / ".github" / "agents" / "auditor.agent.md"


class TestFromAC_DeductionRubricPresent:
    """AC1: Step 3 of task-verification SKILL.md must contain a deduction rubric."""

    def _skill_text(self) -> str:
        return _SKILL_FILE.read_text(encoding="utf-8")

    def _step3_section(self) -> str:
        """Extract the text of Step 3 from the skill file."""
        text = self._skill_text()
        # Extract from "## Step 3" up to the next "## Step"
        match = re.search(r"## Step 3.*?(?=\n## Step \d)", text, re.DOTALL)
        assert match is not None, (
            "## Step 3 section not found in .github/skills/w-task-verification/SKILL.md"
        )
        return match.group(0)

    def test_step3_has_deduction_rubric_heading_or_keyword(self) -> None:
        """Step 3 must describe a deduction rubric — 'deduction' or 'deduct' in section."""
        section = self._step3_section()
        found = "deduct" in section.lower() or "rubric" in section.lower()
        assert found, (
            "Step 3 in .github/skills/w-task-verification/SKILL.md has no mention of 'deduct' or "
            "'rubric' — AC1 requires a structured deduction rubric to be added"
        )

    def test_step3_rubric_starts_at_1_0(self) -> None:
        """Deduction rubric must instruct starting the score at 1.0, not assign freeform."""
        section = self._step3_section()
        # Must say "start at 1.0" or "starting.*1.0" or "begin.*1.0" — not just "1.0"
        # (the existing threshold table already has 1.0 as an entry, that's not the rubric)
        pattern = re.compile(
            r"start\s+at\s+1\.0|starting\s+(?:score\s+)?(?:at\s+)?1\.0|begin\s+(?:at\s+)?1\.0",
            re.IGNORECASE,
        )
        assert pattern.search(section), (
            "Step 3 rubric must contain 'start at 1.0' language — "
            "the AC specifies 'start at 1.0, deduct per criterion' as the rubric mechanism"
        )

    def test_step3_deduct_per_criterion_language(self) -> None:
        """Step 3 must instruct deducting per criterion (not freeform scoring)."""
        section = self._step3_section()
        # Accept any phrasing that conveys "deduct per criterion"
        pattern = re.compile(r"deduct\w*\s+per\s+\w+|per\s+\w+.*deduct", re.IGNORECASE)
        assert pattern.search(section), (
            "Step 3 lacks 'deduct per criterion' language — "
            "the rubric must specify deduction-based scoring, not freeform assignment"
        )


class TestFromAC_DeductionCriteriaValues:
    """AC2: All 5 deduction criteria must be present with the correct numeric values."""

    def _skill_text(self) -> str:
        return _SKILL_FILE.read_text(encoding="utf-8")

    def test_deduction_minus_02_for_ac_line_no_evidence(self) -> None:
        """-.02 deduction must be specified for each AC line lacking specific evidence."""
        text = self._skill_text()
        # Look for -.02 (as text) near AC-related language
        pattern = re.compile(
            r"[-]\.02.*(?:AC\s*line|no\s+.*evidence|specific\s+evidence)"
            r"|(?:AC\s*line|no\s+.*evidence|specific\s+evidence).*[-]\.02",
            re.IGNORECASE | re.DOTALL,
        )
        assert pattern.search(text), (
            "Deduction criteria '-.02 per AC line with no specific evidence' "
            "not found in .github/skills/w-task-verification/SKILL.md (AC2)"
        )

    def test_deduction_minus_05_for_lint_issues(self) -> None:
        """-.05 deduction must be specified for lint issues."""
        text = self._skill_text()
        pattern = re.compile(
            r"[-]\.05.*lint|lint.*[-]\.05",
            re.IGNORECASE,
        )
        assert pattern.search(text), (
            "Deduction criteria '-.05 for lint issues' "
            "not found in .github/skills/w-task-verification/SKILL.md (AC2)"
        )

    def test_deduction_minus_03_for_low_ac_quality(self) -> None:
        """-.03 deduction must be specified for AC quality score 3 or below."""
        text = self._skill_text()
        pattern = re.compile(
            r"[-]\.03.*(?:AC\s*quality|quality\s*score)|(?:AC\s*quality|quality\s*score).*[-]\.03",
            re.IGNORECASE | re.DOTALL,
        )
        assert pattern.search(text), (
            "Deduction criteria '-.03 for AC quality score at 3 or below' "
            "not found in .github/skills/w-task-verification/SKILL.md (AC2)"
        )

    def test_deduction_minus_02_for_missing_reviewer_evidence(self) -> None:
        """-.02 deduction must be specified for missing reviewer evidence section."""
        text = self._skill_text()
        pattern = re.compile(
            r"[-]\.02.*(?:reviewer|review\s+evidence|missing.*evidence)"
            r"|(?:reviewer|review\s+evidence|missing.*evidence).*[-]\.02",
            re.IGNORECASE | re.DOTALL,
        )
        assert pattern.search(text), (
            "Deduction criteria '-.02 for missing reviewer evidence section' "
            "not found in .github/skills/w-task-verification/SKILL.md (AC2)"
        )

    def test_deduction_minus_05_for_full_suite_test_failures(self) -> None:
        """-.05 deduction must be specified for full-suite test failures."""
        text = self._skill_text()
        pattern = re.compile(
            r"[-]\.05.*(?:test\s+fail|full.suite|suite.*fail)"
            r"|(?:test\s+fail|full.suite|suite.*fail).*[-]\.05",
            re.IGNORECASE | re.DOTALL,
        )
        assert pattern.search(text), (
            "Deduction criteria '-.05 for full-suite test failures in task scope' "
            "not found in .github/skills/w-task-verification/SKILL.md (AC2)"
        )

    def test_all_five_deduction_values_present(self) -> None:
        """All five deduction values (-.02, -.02, -.03, -.05, -.05) must appear in Step 3."""
        text = self._skill_text()
        step3_match = re.search(r"## Step 3.*?(?=\n## Step \d)", text, re.DOTALL)
        assert step3_match is not None, "## Step 3 section not found"
        section = step3_match.group(0)

        minus_02_count = len(re.findall(r"[-]\.02", section))
        minus_03_count = len(re.findall(r"[-]\.03", section))
        minus_05_count = len(re.findall(r"[-]\.05", section))

        assert minus_02_count >= 2, (
            f"Step 3 has {minus_02_count} occurrence(s) of -.02 but needs at least 2 "
            "(one for AC line with no evidence, one for missing reviewer evidence)"
        )
        assert minus_03_count >= 1, (
            f"Step 3 has {minus_03_count} occurrence(s) of -.03 but needs at least 1 "
            "(for AC quality score ≤ 3)"
        )
        assert minus_05_count >= 2, (
            f"Step 3 has {minus_05_count} occurrence(s) of -.05 but needs at least 2 "
            "(one for lint issues, one for full-suite test failures)"
        )


class TestFromAC_AuditorRedFlagEntry:
    """AC3: auditor.agent.md red-flags list must include the specific calibration warning."""

    def _auditor_text(self) -> str:
        return _AUDITOR_FILE.read_text(encoding="utf-8")

    def test_red_flags_contains_95_to_97_warning(self) -> None:
        """Red-flags must warn about scores between .95 and .97 without deduction calculation."""
        text = self._auditor_text()
        # AC3 specifies exact phrasing: 'Your confidence score is between .95 and .97
        # without explicit deduction calculation'
        assert ".95 and .97" in text, (
            "agents/auditor.agent.md does not contain the required red-flag text "
            "mentioning confidence score between .95 and .97 (AC3)"
        )

    def test_red_flag_requires_explicit_deduction_calculation(self) -> None:
        """Red-flag entry must reference 'explicit deduction calculation'."""
        text = self._auditor_text()
        pattern = re.compile(
            r"explicit\s+deduction\s+calculation",
            re.IGNORECASE,
        )
        assert pattern.search(text), (
            "agents/auditor.agent.md does not contain 'explicit deduction calculation' "
            "in the red-flags section (AC3)"
        )

    def test_red_flag_in_red_flags_section(self) -> None:
        """The deduction calibration warning must appear under a red-flags section."""
        text = self._auditor_text()
        # Find the red-flags section and check the new text is within it
        red_flags_match = re.search(
            r"[Rr]ed\s+flags.*?(?=\n##\s|\Z)", text, re.DOTALL
        )
        assert red_flags_match is not None, (
            "No 'Red flags' section found in agents/auditor.agent.md"
        )
        section = red_flags_match.group(0)
        assert ".95 and .97" in section, (
            "The confidence score .95-.97 warning is not inside the red-flags section "
            "— it must be placed within the existing red-flags list (AC3)"
        )


class TestFromAC_DeductionBreakdownInOutput:
    """AC4: auditor Channel B template must include a deduction breakdown, not just a number."""

    def _auditor_text(self) -> str:
        return _AUDITOR_FILE.read_text(encoding="utf-8")

    def test_channel_b_template_has_deduction_breakdown_field(self) -> None:
        """Channel B Audit template must include a 'Deduction breakdown' field."""
        text = self._auditor_text()
        pattern = re.compile(
            r"[Dd]eduction\s+breakdown|[Dd]eductions?:",
            re.IGNORECASE,
        )
        assert pattern.search(text), (
            "agents/auditor.agent.md Channel B template does not include a deduction "
            "breakdown field — AC4 requires score to be accompanied by breakdown, "
            "not just a number"
        )

    def test_confidence_line_accompanied_by_breakdown(self) -> None:
        """Confidence and deduction breakdown must appear together in the Audit template block."""
        text = self._auditor_text()
        # Find the Channel B Audit template block (between the code fences)
        # and check both Confidence and Deduction appear within 10 lines of each other
        audit_block_match = re.search(
            r"## Audit\b.*?```",
            text,
            re.DOTALL,
        )
        assert audit_block_match is not None, (
            "Could not find '## Audit' template block in agents/auditor.agent.md"
        )
        block = audit_block_match.group(0)
        has_confidence = bool(re.search(r"[Cc]onfidence", block))
        has_breakdown = bool(
            re.search(r"[Dd]eduction\s+breakdown|[Dd]eductions?:", block, re.IGNORECASE)
        )
        assert has_confidence, (
            "Confidence field missing from ## Audit template block in auditor.agent.md"
        )
        assert has_breakdown, (
            "Deduction breakdown field missing from ## Audit template block — "
            "AC4 requires breakdown alongside the confidence score, not just a number"
        )

    def test_no_bare_confidence_score_without_breakdown_instruction(self) -> None:
        """The audit output section must not show confidence as a lone number field."""
        text = self._auditor_text()
        # The old template had exactly: "### Confidence: {.XX}" with nothing around it.
        # After the change, it must have a deduction breakdown nearby.
        # Check that the Confidence line is NOT completely isolated (i.e., breakdown is nearby).
        confidence_match = re.search(
            r"### Confidence.*?\n(.*?)\n",
            text,
            re.DOTALL,
        )
        if confidence_match is None:
            # If the template format changed, that's acceptable
            return
        surrounding_lines = text[
            max(0, confidence_match.start() - 200): confidence_match.end() + 200
        ]
        has_breakdown = bool(
            re.search(
                r"[Dd]eduction\s+breakdown|[Dd]eductions?:",
                surrounding_lines,
                re.IGNORECASE,
            )
        )
        assert has_breakdown, (
            "The '### Confidence' line in auditor.agent.md has no deduction breakdown "
            "within 200 characters — AC4 requires breakdown alongside the score"
        )
