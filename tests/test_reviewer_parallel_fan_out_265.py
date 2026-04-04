"""Tests for task #265: Enable parallel fan-out in reviewer agent — detailed contract.

AC contract under test (build on #437's structural baseline — all these FAIL before #265):
1. reviewer.agent.md subagents table: quality-runner row with exact When + Example
2. w-code-review SKILL.md Step 2.5: runSubagent invocations with step mapping for both agents
3. Step 2.5 Quality-Runner dispatch: full 5-field input contract (mode, task_id, test_paths,
   coverage_modules, lint_paths)
4. Step 2.5 Code-Reader dispatch: runSubagent format with full 4-field contract
5. Step 8: synthesis paragraph references unified AC compliance table + cross-walk
6. Automatic FAIL triggers documented (MISSING/WEAK from Code-Reader, QR test failure)
7. Sequential fallback on execution error with Channel B note format
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
REVIEWER_AGENT = ROOT / ".github" / "agents" / "reviewer.agent.md"
CODE_REVIEW_SKILL = ROOT / ".github" / "skills" / "w-code-review" / "SKILL.md"


def _get_subagents_block(content: str) -> str:
    """Return the text between <subagents> and </subagents> tags."""
    match = re.search(r"<subagents>(.*?)</subagents>", content, re.DOTALL)
    if match is None:
        return ""
    return match.group(1)


def _get_step_section(content: str, step_heading_prefix: str) -> str:
    """Return content of a '## Step N.N' section until the next '## ' heading."""
    escaped = re.escape(step_heading_prefix)
    start_match = re.search(rf"^## {escaped}[^\n]*$", content, re.MULTILINE)
    if start_match is None:
        return ""
    start = start_match.end()
    next_match = re.search(r"^##\s+", content[start:], re.MULTILINE)
    if next_match is None:
        return content[start:]
    return content[start : start + next_match.start()]


class TestFromAC_ReviewerParallelFanOutDetailed:
    """Detailed behavioral requirements for parallel fan-out wiring (#265).

    Precondition: basic structural changes from #437 are in place (quality-runner in
    agents: list, Step 2.5 heading, Step 8 keyword). These tests target the detailed
    content that #437 did not cover — all fail before the #265 builder implements them.
    """

    # --- AC 1: subagents table quality-runner entry with When + Example ---

    def test_reviewer_subagents_table_has_quality_runner_row(self) -> None:
        """reviewer.agent.md <subagents> table must contain a quality-runner row."""
        content = REVIEWER_AGENT.read_text(encoding="utf-8")
        subagents = _get_subagents_block(content)
        assert subagents, "No <subagents> block found in reviewer.agent.md"
        assert "quality-runner" in subagents, (
            "reviewer.agent.md subagents table must contain an entry for quality-runner. "
            f"Current subagents block:\n{subagents}"
        )

    def test_reviewer_subagents_table_quality_runner_when_exact_text(self) -> None:
        """quality-runner When column must be 'Implementation reviews requiring test/lint/coverage evidence'."""
        content = REVIEWER_AGENT.read_text(encoding="utf-8")
        subagents = _get_subagents_block(content)
        assert "Implementation reviews requiring test/lint/coverage evidence" in subagents, (
            "quality-runner subagents When must be "
            "'Implementation reviews requiring test/lint/coverage evidence'. "
            f"Current subagents block:\n{subagents}"
        )

    # --- AC 2: Step 2.5 uses runSubagent invocation format for both agents ---

    def test_step_2_5_quality_runner_dispatch_uses_runsubagent_format(self) -> None:
        """Step 2.5 must contain an 'agentName: quality-runner' runSubagent invocation."""
        content = CODE_REVIEW_SKILL.read_text(encoding="utf-8")
        section = _get_step_section(content, "Step 2.5")
        assert section, "## Step 2.5 section not found in w-code-review SKILL.md"
        assert "agentName: quality-runner" in section, (
            "Step 2.5 must use runSubagent agentName: quality-runner format "
            f"(current uses inline shorthand). Step 2.5 content:\n{section[:500]}"
        )

    def test_step_2_5_code_reader_dispatch_uses_runsubagent_format(self) -> None:
        """Step 2.5 must contain an 'agentName: code-reader' runSubagent invocation."""
        content = CODE_REVIEW_SKILL.read_text(encoding="utf-8")
        section = _get_step_section(content, "Step 2.5")
        assert section, "## Step 2.5 section not found in w-code-review SKILL.md"
        assert "agentName: code-reader" in section, (
            "Step 2.5 must use runSubagent agentName: code-reader format "
            f"(current uses inline 'code-reader: Analyze:' shorthand). Step 2.5:\n{section[:500]}"
        )

    def test_step_2_5_quality_runner_maps_to_steps_3_through_5(self) -> None:
        """Step 2.5 must indicate that Quality-Runner handles steps 3 through 5."""
        content = CODE_REVIEW_SKILL.read_text(encoding="utf-8")
        section = _get_step_section(content, "Step 2.5")
        has_mapping = bool(
            re.search(r"steps?\s*3[-\u2013]5", section, re.IGNORECASE)
            or (
                re.search(r"\bstep\s*3\b", section, re.IGNORECASE)
                and re.search(r"\bstep\s*5\b", section, re.IGNORECASE)
            )
        )
        assert has_mapping, (
            "Step 2.5 must map Quality-Runner to steps 3\u20135 (tests, lint, coverage). "
            f"Step 2.5 content:\n{section[:500]}"
        )

    def test_step_2_5_code_reader_maps_to_steps_6_and_7(self) -> None:
        """Step 2.5 must indicate that Code-Reader handles steps 6 and 7."""
        content = CODE_REVIEW_SKILL.read_text(encoding="utf-8")
        section = _get_step_section(content, "Step 2.5")
        has_mapping = bool(
            re.search(r"steps?\s*6[-\u2013]7", section, re.IGNORECASE)
            or re.search(r"6\.\d[-\u2013]6\.\d", section)  # "6.0-6.6"
            or re.search(r"7\.[1-4]", section)             # "7.1" through "7.4"
            or (
                re.search(r"\bstep\s*6\b", section, re.IGNORECASE)
                and re.search(r"\bstep\s*7\b", section, re.IGNORECASE)
            )
        )
        assert has_mapping, (
            "Step 2.5 must map Code-Reader to steps 6 and 7 (code reading, AC compliance). "
            f"Step 2.5 content:\n{section[:500]}"
        )

    # --- AC 3: Quality-Runner dispatch has full 5-field input contract ---

    def test_step_2_5_quality_runner_input_contract_has_all_five_fields(self) -> None:
        """Step 2.5 QR dispatch must specify all 5 fields: mode, task_id, test_paths, coverage_modules, lint_paths."""
        content = CODE_REVIEW_SKILL.read_text(encoding="utf-8")
        section = _get_step_section(content, "Step 2.5")
        required_fields = ["mode", "task_id", "test_paths", "coverage_modules", "lint_paths"]
        missing = [f for f in required_fields if f not in section]
        assert not missing, (
            f"Step 2.5 Quality-Runner dispatch is missing fields: {missing}. "
            f"Current Step 2.5 only has: {{task_id, changed_files}}. Full content:\n{section[:500]}"
        )

    # --- AC 4: Code-Reader dispatch in runSubagent format with full contract ---

    def test_step_2_5_code_reader_dispatch_full_contract_in_runsubagent_format(self) -> None:
        """Step 2.5 CR dispatch must use agentName: code-reader with ac_lines, changed_files, test_files fields."""
        content = CODE_REVIEW_SKILL.read_text(encoding="utf-8")
        section = _get_step_section(content, "Step 2.5")
        # agentName format is what distinguishes this from the current inline shorthand
        assert "agentName: code-reader" in section, (
            "Code-Reader dispatch in Step 2.5 must use runSubagent format (agentName: code-reader), "
            f"not the current inline 'code-reader: Analyze:' shorthand. Step 2.5:\n{section[:500]}"
        )
        required_cr_fields = ["ac_lines", "changed_files", "test_files"]
        missing = [f for f in required_cr_fields if f not in section]
        assert not missing, (
            f"Code-Reader dispatch in Step 2.5 missing contract fields: {missing}"
        )

    # --- AC 5: Step 8 synthesis references AC compliance table and cross-walk ---

    def test_step_8_synthesis_references_ac_compliance_table(self) -> None:
        """Step 8 must describe merging subagent reports into a unified AC compliance table."""
        content = CODE_REVIEW_SKILL.read_text(encoding="utf-8")
        section = _get_step_section(content, "Step 8")
        lower = section.lower()
        assert "ac compliance" in lower or "compliance table" in lower, (
            "Step 8 synthesis must reference a unified AC compliance table. "
            f"Current Step 8 (first 400 chars):\n{section[:400]}"
        )

    def test_step_8_synthesis_references_cross_walk(self) -> None:
        """Step 8 must describe cross-walking Code-Reader AC coverage with Quality-Runner test results."""
        content = CODE_REVIEW_SKILL.read_text(encoding="utf-8")
        section = _get_step_section(content, "Step 8")
        lower = section.lower()
        has_crosswalk = "cross-walk" in lower or "crosswalk" in lower or "cross walk" in lower
        assert has_crosswalk, (
            "Step 8 synthesis must describe cross-walking Code-Reader AC coverage "
            f"with Quality-Runner test pass/fail per AC line. Current Step 8:\n{section[:400]}"
        )

    # --- AC 6: Automatic FAIL triggers documented ---

    def test_step_2_5_or_step_8_documents_code_reader_missing_weak_fail_trigger(self) -> None:
        """Step 2.5 or Step 8 must document automatic FAIL for MISSING or WEAK Code-Reader findings."""
        content = CODE_REVIEW_SKILL.read_text(encoding="utf-8")
        combined = _get_step_section(content, "Step 2.5") + _get_step_section(content, "Step 8")
        has_trigger = bool(
            re.search(r"(MISSING|WEAK).{0,120}(code[- ]reader|fail)", combined, re.IGNORECASE)
            or re.search(r"(code[- ]reader).{0,120}(MISSING|WEAK)", combined, re.IGNORECASE)
        )
        assert has_trigger, (
            "Step 2.5 or Step 8 must document that MISSING or WEAK from Code-Reader = automatic FAIL. "
            "Neither section currently documents this trigger."
        )

    def test_step_2_5_or_step_8_documents_quality_runner_test_failure_fail_trigger(self) -> None:
        """Step 2.5 or Step 8 must document automatic FAIL for test failure from Quality-Runner."""
        content = CODE_REVIEW_SKILL.read_text(encoding="utf-8")
        combined = _get_step_section(content, "Step 2.5") + _get_step_section(content, "Step 8")
        has_trigger = bool(
            re.search(r"quality[- ]runner.{0,100}fail", combined, re.IGNORECASE)
            or re.search(r"fail.{0,100}quality[- ]runner", combined, re.IGNORECASE)
        )
        assert has_trigger, (
            "Step 2.5 or Step 8 must document automatic FAIL when Quality-Runner reports a test failure. "
            "Neither section currently documents this trigger."
        )

    # --- AC 7: Sequential fallback on execution error with Channel B note ---

    def test_step_2_5_fallback_triggers_on_execution_error(self) -> None:
        """Step 2.5 fallback must trigger on execution error (crash/timeout/exception), not just unavailability."""
        content = CODE_REVIEW_SKILL.read_text(encoding="utf-8")
        section = _get_step_section(content, "Step 2.5")
        lower = section.lower()
        has_execution_error = "execution error" in lower or (
            "crash" in lower and "timeout" in lower
        )
        assert has_execution_error, (
            "Step 2.5 fallback must trigger on execution error (crash, timeout, exception), "
            "not on 'unavailable'. "
            "Current Step 2.5 says: 'If a subagent is unavailable, proceed solo...'"
        )

    def test_step_2_5_fallback_channel_b_note_format(self) -> None:
        """Step 2.5 must document Channel B fallback note 'Parallel fan-out failed: ... Fell back to sequential.'"""
        content = CODE_REVIEW_SKILL.read_text(encoding="utf-8")
        section = _get_step_section(content, "Step 2.5")
        lower = section.lower()
        has_fallback_note = "fell back to sequential" in lower or "parallel fan-out failed" in lower
        assert has_fallback_note, (
            "Step 2.5 must document Channel B fallback note: "
            "'Parallel fan-out failed: {reason}. Fell back to sequential.' "
            "Current Step 2.5 says: 'proceed solo and note the gap' \u2014 missing required format."
        )
