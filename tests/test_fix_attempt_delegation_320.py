"""Tests for task #320: fix-attempt delegation flow contract.

Contract-level verification that w-tdd-green/SKILL.md and builder.agent.md
document the builder→fix-attempt delegation flow per the refined AC.

Testing approach: pure contract tests on Markdown skill/agent files using
regex/string assertions — the same established pattern as test_fix_attempt_agent_318.py
(S1) and test_quality_runner_wiring.py (S2).

AC coverage:
  - AC1:  w-tdd-green SKILL.md documents retry_hint construction with three explicit
          components: error output extraction, failing test identification, and verbal
          diagnosis (Reflexion-style per fix-attempt input contract)
  - AC2:  Builder delegation prompt in w-tdd-green includes all 5 fix-attempt input
          contract fields (task_id, test_file, source_files, retry_hint,
          error_summary), cross-referenced against fix-attempt.agent.md
  - AC3:  w-tdd-green documents delegation after exactly 2 failures (not 1, not 3):
          initial → same-context retry → fix-attempt. Fixed sequence, no skip.
  - AC4:  FIXED result triggers re-verification (pytest + ruff); on pass → Step 7;
          on re-verify failure → reject with diagnosis-based target (todo or backlog)
  - AC5:  FAILED result Channel B notes must name the two specific attempt sources
          (same-context retry and fix-attempt) — generic 'both attempts' is
          insufficient for a builder without context
  - AC6:  w-tdd-green Step 6.3 must document fix-attempt's agents-array dependency
          as a prerequisite so the builder catches wiring failures early

Note on RED phase: task #319 implemented Steps 6.1-6.3 in w-tdd-green SKILL.md.
9 tests target specific content gaps that remain after that implementation.
Passing tests (already-satisfied behavior) were removed per TDD RED rules.
"""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
_SKILL_FILE = _REPO_ROOT / ".github" / "skills" / "w-tdd-green" / "SKILL.md"
_BUILDER_FILE = _REPO_ROOT / ".github" / "agents" / "builder.agent.md"
_FIX_ATTEMPT_FILE = _REPO_ROOT / ".github" / "agents" / "fix-attempt.agent.md"

def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _extract_delegation_section(skill_content: str) -> str:
    """Extract the Step 6.3 (fix-attempt delegation) section of the skill."""
    match = re.search(
        r"(### Step 6\.3.*?)(?=^## |\Z)",
        skill_content,
        re.DOTALL | re.MULTILINE,
    )
    assert match is not None, (
        "Step 6.3 (fix-attempt delegation) section not found in w-tdd-green SKILL.md"
    )
    return match.group(1)


# ---------------------------------------------------------------------------
# AC1: retry_hint construction — three explicit components
# ---------------------------------------------------------------------------


class TestFromAC_RetryHintConstruction:
    """AC1: w-tdd-green SKILL.md documents retry_hint construction with three
    explicit components per the fix-attempt input contract: error output extraction,
    failing test identification, and Reflexion-style verbal diagnosis.
    """

    def test_retry_hint_guidance_documents_error_output_extraction(self) -> None:
        """AC1: retry_hint guidance in Step 6.3 must explicitly reference error
        output as source material for the hint (not generic 'what went wrong').
        Extracting specific output is a distinct component from verbal diagnosis.
        """
        delegation = _extract_delegation_section(_read(_SKILL_FILE))
        # Locate the retry_hint field description
        match = re.search(r"retry_hint\s*:(.*?)(?=\n\s*\w+_\w+\s*:|```|\n##)", delegation, re.DOTALL)
        assert match is not None, "retry_hint field not found in Step 6.3 delegation prompt"
        hint_text = match.group(1)
        has_error_output = bool(re.search(
            r"\berror\b.{0,50}\boutput\b|\boutput\b.{0,50}\berror\b"
            r"|\bextract\b.{0,50}\berror\b|\berror\b.{0,50}\bextract\b",
            hint_text,
            re.IGNORECASE | re.DOTALL,
        ))
        assert has_error_output, (
            "retry_hint guidance must explicitly reference error output extraction "
            "as a construction component — e.g. 'extract specific errors from output'. "
            f"Current text: {hint_text.strip()!r}"
        )

    def test_retry_hint_guidance_documents_failing_test_identification(self) -> None:
        """AC1: retry_hint guidance must explicitly reference identifying which
        specific tests failed as a component of hint construction. 'What went wrong'
        is insufficient — the hint must name the failing tests.
        """
        delegation = _extract_delegation_section(_read(_SKILL_FILE))
        match = re.search(r"retry_hint\s*:(.*?)(?=\n\s*\w+_\w+\s*:|```|\n##)", delegation, re.DOTALL)
        assert match is not None, "retry_hint field not found in Step 6.3 delegation prompt"
        hint_text = match.group(1)
        has_test_identification = bool(re.search(
            r"\bfailing test\b|\bidentif\w+.*test\b|\bwhich test\b|\bspecific test.*fail\b",
            hint_text,
            re.IGNORECASE | re.DOTALL,
        ))
        assert has_test_identification, (
            "retry_hint guidance must explicitly reference failing test identification "
            "— builder must name the failing test(s) in the hint, not just describe "
            "'what went wrong'. "
            f"Current text: {hint_text.strip()!r}"
        )


# ---------------------------------------------------------------------------
# AC2: delegation prompt — all 5 input contract fields cross-referenced
# ---------------------------------------------------------------------------


class TestFromAC_InputContractValidation:
    """AC2: Builder delegation prompt in w-tdd-green includes all 5 fix-attempt
    input contract fields, cross-referenced against fix-attempt.agent.md.
    """

    def test_delegation_section_cross_references_fix_attempt_agent_file(self) -> None:
        """AC2: Step 6.3 must cross-reference fix-attempt.agent.md (or the input
        contract) by name so the builder can verify field alignment without context-switching.
        Implicit field inclusion without a reference is insufficient.
        """
        delegation = _extract_delegation_section(_read(_SKILL_FILE))
        has_agent_file_ref = bool(re.search(
            r"fix-attempt\.agent\.md|fix-attempt input contract|Input Contract",
            delegation,
            re.IGNORECASE,
        ))
        assert has_agent_file_ref, (
            "Step 6.3 must cross-reference 'fix-attempt.agent.md' or 'Input Contract' "
            "by name so the builder can verify field alignment. "
            "Current section has the fields but no explicit cross-reference."
        )


# ---------------------------------------------------------------------------
# AC3: delegation threshold — exactly 2, fixed sequence, no skip
# ---------------------------------------------------------------------------


class TestFromAC_DelegationThreshold:
    """AC3: w-tdd-green documents delegation after exactly 2 failures (not 1, not 3):
    initial → same-context retry → fix-attempt. Fixed sequence, no skip.
    """

    def test_delegation_threshold_stated_as_exactly_two_failures(self) -> None:
        """AC3: Skill must state the threshold is exactly 2 failures with exclusionary
        language — 'not 1, not 3' is the requirement; 'no more than 2' is insufficient.
        """
        delegation = _extract_delegation_section(_read(_SKILL_FILE))
        # Check for "exactly 2" or numeric exclusion language
        has_exact_two = bool(re.search(
            r"exactly\s+2\b|exactly\s+two\b|not\s+1\b.*not\s+3\b"
            r"|not\s+1.*failure|not\s+after\s+1\b|not\s+after\s+one\b",
            delegation,
            re.IGNORECASE | re.DOTALL,
        ))
        assert has_exact_two, (
            "Step 6.3 must document threshold as 'exactly 2' failures with exclusionary "
            "language (e.g. 'not 1, not 3') so builder cannot misread the cap. "
            "The refinement requires unambiguous threshold statement."
        )


# ---------------------------------------------------------------------------
# AC4: FIXED result handling — re-verify pytest + ruff, reject on reverify failure
# ---------------------------------------------------------------------------


class TestFromAC_FixedResultHandling:
    """AC4: FIXED result from fix-attempt triggers re-verification (pytest + ruff);
    on pass → continue to Step 7; on re-verify failure → reject with diagnosis-based
    target (todo or backlog).
    """

    def test_fixed_reverification_mentions_pytest_explicitly(self) -> None:
        """AC4: Re-verification after FIXED must explicitly require pytest — not
        just 'Quality-Runner'. The builder needs to know the concrete tool to run.
        """
        delegation = _extract_delegation_section(_read(_SKILL_FILE))
        fixed_match = re.search(r"FIXED.*?(?=FAILED|\Z)", delegation, re.DOTALL | re.IGNORECASE)
        assert fixed_match is not None, "FIXED verdict row not found in Step 6.3"
        fixed_text = fixed_match.group(0)
        assert "pytest" in fixed_text.lower(), (
            "FIXED result re-verification must explicitly mention 'pytest' — "
            "Quality-Runner alone is insufficient; the builder needs the concrete tool. "
            f"FIXED section: {fixed_text.strip()!r}"
        )

    def test_fixed_reverification_mentions_ruff_explicitly(self) -> None:
        """AC4: Re-verification after FIXED must also require ruff (lint). A fix
        that passes tests but fails lint is not verified. Both tools are required.
        """
        delegation = _extract_delegation_section(_read(_SKILL_FILE))
        fixed_match = re.search(r"FIXED.*?(?=FAILED|\Z)", delegation, re.DOTALL | re.IGNORECASE)
        assert fixed_match is not None, "FIXED verdict row not found in Step 6.3"
        fixed_text = fixed_match.group(0)
        assert "ruff" in fixed_text.lower(), (
            "FIXED result re-verification must explicitly mention 'ruff' — "
            "lint verification is required alongside pytest. "
            f"FIXED section: {fixed_text.strip()!r}"
        )

    def test_fixed_reverify_failure_triggers_explicit_reject(self) -> None:
        """AC4: When FIXED re-verification still fails, the skill must explicitly
        call for end_work(outcome='reject') — not just 'treat as FAILED' (which
        requires the builder to cross-reference an implicit fallback path).
        """
        delegation = _extract_delegation_section(_read(_SKILL_FILE))
        fixed_match = re.search(r"FIXED.*?(?=FAILED|\Z)", delegation, re.DOTALL | re.IGNORECASE)
        assert fixed_match is not None, "FIXED verdict row not found in Step 6.3"
        fixed_text = fixed_match.group(0)
        # "treat as FAILED" is an indirect reference; the AC requires explicit reject call
        has_explicit_reject = bool(re.search(
            r"\breject\b|end_work.*reject|outcome.*reject",
            fixed_text,
            re.IGNORECASE,
        ))
        assert has_explicit_reject, (
            "FIXED-but-still-failing path must explicitly state the reject outcome — "
            "'treat as FAILED' is an indirect reference that forces builder to "
            "cross-reference the FAILED row. AC4 requires the reject action to be "
            "callable from the FIXED result path without redirection. "
            f"FIXED section: {fixed_text.strip()!r}"
        )


# ---------------------------------------------------------------------------
# AC5: FAILED result handling — Channel B notes must name both attempt sources
# ---------------------------------------------------------------------------


class TestFromAC_FailedResultHandling:
    """AC5: FAILED result from fix-attempt triggers reject with diagnosis-based
    routing. The Channel B note requirement must explicitly name the two specific
    attempt sources (same-context retry and fix-attempt) — generic 'both attempts'
    is insufficient for a builder without context on which notes to record.
    """

    def test_failed_channel_b_notes_explicitly_name_both_attempt_sources(self) -> None:
        """AC5: The Channel B note instruction in the FAILED row must name both
        attempt sources explicitly: the same-context retry (Step 6.2) and the
        fix-attempt (Step 6.3). 'Diagnosis from both attempts' is generic — the
        builder needs to know exactly which notes to write from each source.
        """
        delegation = _extract_delegation_section(_read(_SKILL_FILE))
        failed_match = re.search(
            r"FAILED.*?(?=^>|\Z)", delegation, re.DOTALL | re.MULTILINE
        )
        assert failed_match is not None, "FAILED verdict row not found in Step 6.3"
        failed_text = failed_match.group(0)
        names_same_context = bool(re.search(
            r"same.context|step\s*6\.2|step\s*6\s*\.\s*2",
            failed_text,
            re.IGNORECASE,
        ))
        names_fix_attempt_diag = bool(re.search(
            r"fix.attempt.{0,40}diagnos|diagnos.{0,40}fix.attempt",
            failed_text,
            re.IGNORECASE | re.DOTALL,
        ))
        assert names_same_context, (
            "FAILED Channel B note requirement must reference the 'same-context' attempt "
            "(Step 6.2) by name — 'both attempts' is too generic. "
            f"FAILED section: {failed_text.strip()!r}"
        )
        assert names_fix_attempt_diag, (
            "FAILED Channel B note requirement must reference 'fix-attempt' diagnosis "
            "by name — 'both attempts' is too generic. "
            f"FAILED section: {failed_text.strip()!r}"
        )


# ---------------------------------------------------------------------------
# AC6: builder wiring prerequisite documented in the skill
# ---------------------------------------------------------------------------


class TestFromAC_BuilderWiring:
    """AC6: w-tdd-green Step 6.3 must document that fix-attempt must be in the
    builder's agents array as a prerequisite — not just invoke it silently.
    Without this, the builder has no warning when the wiring is broken.
    """

    def test_skill_documents_fix_attempt_prerequisite_in_delegation_section(self) -> None:
        """AC6: Step 6.3 must explicitly state that fix-attempt must be present in
        the builder's agents array as a prerequisite for delegation. Invoking an
        unlisted agent fails silently; the skill must warn the builder to verify the
        wiring before invoking.
        """
        delegation = _extract_delegation_section(_read(_SKILL_FILE))
        has_prerequisite = bool(re.search(
            r"agents\b.{0,80}fix.attempt|fix.attempt.{0,80}\bagents\b"
            r"|fix.attempt.{0,40}must be|ensure.{0,40}fix.attempt"
            r"|fix.attempt.{0,40}listed|prerequisite.{0,60}fix.attempt"
            r"|fix.attempt.{0,60}prerequisite|fix.attempt.{0,40}included"
            r"|agents.{0,40}array.{0,80}fix.attempt",
            delegation,
            re.IGNORECASE | re.DOTALL,
        ))
        assert has_prerequisite, (
            "Step 6.3 must state fix-attempt must be in builder's agents array as a "
            "prerequisite for delegation. Without this, the builder has no warning "
            "when the wiring is broken. Current section invokes fix-attempt without "
            "documenting the agents-array dependency."
        )
