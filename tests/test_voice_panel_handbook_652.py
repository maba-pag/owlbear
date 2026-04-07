"""Tests for task #652: Create h-voice-panel/SKILL.md handbook.

Contract-level verification that share/skills/h-voice-panel/SKILL.md exists
with the required frontmatter and body content per the AC (including Architecture
Review amendments).

AC coverage:
  - AC1: share/skills/h-voice-panel/SKILL.md exists with valid YAML frontmatter;
         name: h-voice-panel, description matches spec, user-invocable: false
  - AC2: Characterizes each voice — domain, persona, and behavioral calibration
         guidance (tone/assertiveness) — for all 6 voices.
         NOTE: "temperature guidance" in AC2 was refined by Architecture Review
         to mean "behavioral calibration guidance (tone/assertiveness)", NOT LLM
         sampling temperature.
  - AC3: Documents invocation patterns — parallel batch and sequential deep-dive
  - AC4: Defines Critic-loop rules — when to challenge, qualitative convergence
         exit condition ("position is solid"), max rounds (≤5 cycles).
         NOTE: "convergence threshold" refined by Architecture Review to a
         qualitative exit condition, not a numeric threshold.
  - AC5: Covers disagreement resolution — surface to user, user decides
  - AC6: Covers Mediator synthesis rules — how voices merge into decisions
  - AC7: References all 6 voice agents by name

All tests FAIL on current HEAD because share/skills/h-voice-panel/SKILL.md
does not yet exist.
"""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
_SKILL_FILE = _REPO_ROOT / "share" / "skills" / "h-voice-panel" / "SKILL.md"

# Canonical names of all 6 voice agents (from share/agents/)
_ALL_VOICE_AGENTS: frozenset[str] = frozenset(
    {
        "critic-voice",
        "architect-voice",
        "data-voice",
        "enduser-voice",
        "security-voice",
        "pragmatist-voice",
    }
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_skill() -> str:
    return _SKILL_FILE.read_text(encoding="utf-8")


def _extract_frontmatter(content: str) -> str:
    """Extract text between leading --- ... --- block."""
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    assert match is not None, (
        f"No valid YAML frontmatter (--- ... ---) found in {_SKILL_FILE.name}"
    )
    return match.group(1)


def _extract_body(content: str) -> str:
    """Extract text after the closing --- of frontmatter."""
    match = re.match(r"^---\n.*?\n---\n(.*)", content, re.DOTALL)
    assert match is not None, (
        f"No body content found after frontmatter in {_SKILL_FILE.name}"
    )
    return match.group(1)


# ---------------------------------------------------------------------------
# TestFromAC_VoicePanelFrontmatter — AC1
# ---------------------------------------------------------------------------


class TestFromAC_VoicePanelFrontmatter:
    """AC1: share/skills/h-voice-panel/SKILL.md must exist with correct frontmatter."""

    def test_file_exists(self) -> None:
        """AC1: h-voice-panel/SKILL.md must exist on disk."""
        assert _SKILL_FILE.is_file(), (
            "share/skills/h-voice-panel/SKILL.md does not exist — builder must create it"
        )

    def test_has_valid_yaml_frontmatter(self) -> None:
        """AC1: File must start with a --- ... --- YAML frontmatter block."""
        content = _read_skill()
        assert content.startswith("---\n"), (
            "h-voice-panel/SKILL.md must begin with '---' YAML frontmatter"
        )
        fm = _extract_frontmatter(content)
        assert fm.strip() != "", "Frontmatter block must not be empty"

    def test_name_is_h_voice_panel(self) -> None:
        """AC1: name field must be 'h-voice-panel' matching the directory convention."""
        fm = _extract_frontmatter(_read_skill())
        match = re.search(r"^name:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "name: key not found in frontmatter"
        assert match.group(1).strip() == "h-voice-panel", (
            f"Expected name: h-voice-panel, got {match.group(1).strip()!r}"
        )

    def test_description_present_and_non_empty(self) -> None:
        """AC1: description field must be present and non-empty."""
        fm = _extract_frontmatter(_read_skill())
        match = re.search(r'^description:\s*"?(.+?)"?\s*$', fm, re.MULTILINE)
        assert match is not None, "description: key not found in frontmatter"
        assert match.group(1).strip() != "", "description must not be empty"

    def test_description_identifies_voice_panel_handbook(self) -> None:
        """AC1: description must identify this as a handbook about the voice panel."""
        fm = _extract_frontmatter(_read_skill())
        match = re.search(r'^description:\s*"?(.+?)"?\s*$', fm, re.MULTILINE)
        assert match is not None, "description: key not found in frontmatter"
        desc = match.group(1).lower()
        assert "voice" in desc, (
            f"description must reference 'voice', got: {match.group(1)!r}"
        )
        assert "panel" in desc, (
            f"description must reference 'panel', got: {match.group(1)!r}"
        )

    def test_user_invocable_is_false(self) -> None:
        """AC1: user-invocable must be false — this is a machine-read reference skill."""
        fm = _extract_frontmatter(_read_skill())
        match = re.search(r"^user-invocable:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "user-invocable: key not found in frontmatter"
        assert match.group(1).strip().lower() == "false", (
            f"Expected user-invocable: false, got {match.group(1).strip()!r}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_VoiceCharacterizations — AC2
# ---------------------------------------------------------------------------


class TestFromAC_VoiceCharacterizations:
    """AC2: Handbook must characterize each voice with domain, persona, and
    behavioral calibration guidance (tone/assertiveness).

    Architecture Review amendment: 'temperature guidance' in AC2 means
    behavioral calibration (assertiveness/tone), not LLM sampling temperature.
    """

    def test_voice_roster_section_exists(self) -> None:
        """AC2: A Voice Roster (or Voice Characterizations) section must exist."""
        body = _extract_body(_read_skill())
        assert re.search(r"##.*voice.*(roster|characterization)", body, re.IGNORECASE), (
            "Body must contain a voice roster/characterization section (## Voice Roster "
            "or similar)"
        )

    def test_all_six_voices_characterized(self) -> None:
        """AC2: All 6 voices must appear in the characterization section."""
        body = _extract_body(_read_skill()).lower()
        for voice_name in _ALL_VOICE_AGENTS:
            assert voice_name.lower() in body, (
                f"Voice '{voice_name}' not found in SKILL.md body — all 6 must be characterized"
            )

    def test_domain_concept_covered_in_characterizations(self) -> None:
        """AC2: Voice characterizations must describe each voice's domain."""
        body = _extract_body(_read_skill()).lower()
        assert "domain" in body, (
            "Body must include 'domain' to characterize each voice's area of expertise"
        )

    def test_persona_concept_covered_in_characterizations(self) -> None:
        """AC2: Voice characterizations must include persona description."""
        body = _extract_body(_read_skill()).lower()
        assert "persona" in body, (
            "Body must include 'persona' to characterize each voice's personality"
        )

    def test_behavioral_calibration_guidance_present(self) -> None:
        """AC2: Behavioral calibration guidance (tone/assertiveness) must be documented.

        Architecture Review: AC2 'temperature guidance' = behavioral calibration
        (assertiveness level), not LLM sampling temperature. At minimum, assert
        'assertiveness' OR 'behavioral' appears (spec language).
        """
        body = _extract_body(_read_skill()).lower()
        assert "assertiveness" in body or "behavioral" in body or "calibration" in body, (
            "Body must document behavioral calibration / assertiveness guidance per "
            "Architecture Review amendment to AC2"
        )

    def test_critic_characterized_as_adversarial(self) -> None:
        """AC2: Critic voice characterized as adversarial challenger."""
        body = _extract_body(_read_skill()).lower()
        assert "adversarial" in body or "aggressive" in body or "challenge" in body, (
            "Critic characterization must indicate adversarial / challenging stance"
        )

    def test_pragmatist_characterized_as_neutral_synthesizer(self) -> None:
        """AC2: Pragmatist voice characterized as neutral synthesis voice."""
        body = _extract_body(_read_skill()).lower()
        assert "neutral" in body or "synthesis" in body or "synthesize" in body, (
            "Pragmatist characterization must indicate neutral synthesizer role"
        )


# ---------------------------------------------------------------------------
# TestFromAC_InvocationPatterns — AC3
# ---------------------------------------------------------------------------


class TestFromAC_InvocationPatterns:
    """AC3: Handbook must document invocation patterns — parallel batch and
    sequential deep-dive.
    """

    def test_invocation_patterns_section_exists(self) -> None:
        """AC3: An Invocation Patterns section must be present."""
        body = _extract_body(_read_skill())
        assert re.search(r"##.*invocation.*pattern", body, re.IGNORECASE), (
            "Body must contain an invocation patterns section (## Invocation Patterns or similar)"
        )

    def test_parallel_batch_pattern_documented(self) -> None:
        """AC3: Parallel batch invocation pattern must be documented."""
        body = _extract_body(_read_skill()).lower()
        assert "parallel" in body, (
            "Invocation patterns must document parallel batch invocation"
        )

    def test_sequential_deep_dive_pattern_documented(self) -> None:
        """AC3: Sequential deep-dive invocation pattern must be documented."""
        body = _extract_body(_read_skill()).lower()
        assert "sequential" in body or "deep-dive" in body or "deep dive" in body, (
            "Invocation patterns must document sequential deep-dive invocation"
        )


# ---------------------------------------------------------------------------
# TestFromAC_CriticLoopRules — AC4
# ---------------------------------------------------------------------------


class TestFromAC_CriticLoopRules:
    """AC4: Handbook must define Critic-loop rules — when to challenge, qualitative
    convergence exit condition, and max rounds.

    Architecture Review amendment: 'convergence threshold' = qualitative Critic
    exit condition ("position is solid" OR 5 cycles reached), NOT a numeric threshold.
    """

    def test_critic_loop_section_exists(self) -> None:
        """AC4: A Critic Loop (or Critic-loop Protocol) section must exist."""
        body = _extract_body(_read_skill())
        assert re.search(r"##.*critic.*(loop|protocol|rule)", body, re.IGNORECASE), (
            "Body must contain a Critic Loop / Critic-loop Protocol section"
        )

    def test_when_to_challenge_documented(self) -> None:
        """AC4: Rules for when the Critic should be invoked must be documented."""
        body = _extract_body(_read_skill()).lower()
        # The spec defines challenge trigger as after each voice response
        assert "challenge" in body or "when to" in body or "trigger" in body, (
            "Critic-loop rules must document when to invoke the Critic"
        )

    def test_qualitative_exit_condition_documented(self) -> None:
        """AC4: Qualitative Critic exit condition must be documented.

        Architecture Review: 'position is solid' is the canonical exit phrase from
        the spec. The Critic says this after honest examination to exit the loop.
        """
        body = _extract_body(_read_skill())
        assert "position is solid" in body.lower() or "solid" in body.lower(), (
            "Critic-loop rules must document the qualitative exit condition "
            "('position is solid') per Architecture Review amendment to AC4"
        )

    def test_max_rounds_documented(self) -> None:
        """AC4: Maximum number of Critic-loop cycles must be documented (≤5 per spec §12)."""
        body = _extract_body(_read_skill())
        # The spec says ≤5 cycles. Test for the number 5 appearing near cycle/round context.
        assert "5" in body or "five" in body.lower(), (
            "Critic-loop rules must document the maximum cycle count (5 per spec §12)"
        )

    def test_do_not_manufacture_objections_rule_present(self) -> None:
        """AC4: The mandatory Critic instruction 'do not manufacture objections' must be present."""
        body = _extract_body(_read_skill()).lower()
        assert "manufacture" in body or "do not manufacture" in body, (
            "Critic-loop rules must include the 'do not manufacture objections' instruction "
            "from spec §12 — this is a mandatory Critic prompt constraint"
        )


# ---------------------------------------------------------------------------
# TestFromAC_DisagreementResolution — AC5
# ---------------------------------------------------------------------------


class TestFromAC_DisagreementResolution:
    """AC5: Handbook must cover disagreement resolution — surface to user,
    user decides.
    """

    def test_disagreement_resolution_section_exists(self) -> None:
        """AC5: A Disagreement Resolution section must be present."""
        body = _extract_body(_read_skill())
        assert re.search(r"##.*disagreement", body, re.IGNORECASE), (
            "Body must contain a Disagreement Resolution section"
        )

    def test_surface_to_user_documented(self) -> None:
        """AC5: Resolution rule must state that disagreements are surfaced to the user."""
        body = _extract_body(_read_skill()).lower()
        assert "surface" in body or "present to" in body or "report to" in body, (
            "Disagreement resolution must document surfacing disagreements to the user"
        )

    def test_user_decides_documented(self) -> None:
        """AC5: Resolution rule must state that the user makes the final decision."""
        body = _extract_body(_read_skill()).lower()
        assert "user decides" in body or "user's decision" in body or "user resolves" in body or (
            "left to the user" in body
        ), (
            "Disagreement resolution must state that resolution is the user's decision"
        )


# ---------------------------------------------------------------------------
# TestFromAC_MediatorSynthesisRules — AC6
# ---------------------------------------------------------------------------


class TestFromAC_MediatorSynthesisRules:
    """AC6: Handbook must cover Mediator synthesis rules — how voices merge
    into decisions.
    """

    def test_synthesis_rules_section_exists(self) -> None:
        """AC6: A Synthesis Rules section must be present."""
        body = _extract_body(_read_skill())
        assert re.search(r"##.*synthesis.*(rule|rules)", body, re.IGNORECASE), (
            "Body must contain a Synthesis Rules section (## Synthesis Rules or similar)"
        )

    def test_mediator_role_in_synthesis_documented(self) -> None:
        """AC6: Synthesis rules must describe the Mediator's role in merging voices."""
        body = _extract_body(_read_skill()).lower()
        assert "mediator" in body, (
            "Synthesis rules must reference the Mediator's role in merging voice outputs"
        )

    def test_convergence_or_merge_mechanics_documented(self) -> None:
        """AC6: How voices converge / merge into decisions must be documented."""
        body = _extract_body(_read_skill()).lower()
        assert "convergence" in body or "merge" in body or "consolidat" in body, (
            "Synthesis rules must describe how voice outputs are merged or converged"
        )

    def test_pragmatist_synthesis_role_documented(self) -> None:
        """AC6: Pragmatist-voice role in synthesis must be documented."""
        body = _extract_body(_read_skill()).lower()
        # pragmatist produces the synthesis summary for the Mediator
        assert "pragmatist" in body, (
            "Synthesis rules must reference pragmatist-voice's role in producing synthesis"
        )


# ---------------------------------------------------------------------------
# TestFromAC_VoiceAgentReferences — AC7
# ---------------------------------------------------------------------------


class TestFromAC_VoiceAgentReferences:
    """AC7: Handbook must reference all 6 voice agents by their canonical name."""

    def test_critic_voice_referenced_by_name(self) -> None:
        """AC7: critic-voice must be referenced by name in the handbook."""
        body = _extract_body(_read_skill())
        assert "critic-voice" in body, (
            "'critic-voice' not found in SKILL.md body — all voice agents must be referenced"
        )

    def test_architect_voice_referenced_by_name(self) -> None:
        """AC7: architect-voice must be referenced by name in the handbook."""
        body = _extract_body(_read_skill())
        assert "architect-voice" in body, (
            "'architect-voice' not found in SKILL.md body"
        )

    def test_data_voice_referenced_by_name(self) -> None:
        """AC7: data-voice must be referenced by name in the handbook."""
        body = _extract_body(_read_skill())
        assert "data-voice" in body, (
            "'data-voice' not found in SKILL.md body"
        )

    def test_enduser_voice_referenced_by_name(self) -> None:
        """AC7: enduser-voice must be referenced by name in the handbook."""
        body = _extract_body(_read_skill())
        assert "enduser-voice" in body, (
            "'enduser-voice' not found in SKILL.md body"
        )

    def test_security_voice_referenced_by_name(self) -> None:
        """AC7: security-voice must be referenced by name in the handbook."""
        body = _extract_body(_read_skill())
        assert "security-voice" in body, (
            "'security-voice' not found in SKILL.md body"
        )

    def test_pragmatist_voice_referenced_by_name(self) -> None:
        """AC7: pragmatist-voice must be referenced by name in the handbook."""
        body = _extract_body(_read_skill())
        assert "pragmatist-voice" in body, (
            "'pragmatist-voice' not found in SKILL.md body"
        )

    def test_all_six_voices_referenced(self) -> None:
        """AC7: All 6 canonical voice agent names must be present (aggregate check)."""
        body = _extract_body(_read_skill())
        missing = [v for v in _ALL_VOICE_AGENTS if v not in body]
        assert not missing, (
            f"The following voice agents are not referenced by name: {missing!r}"
        )


# ---------------------------------------------------------------------------
# TestFromAC_VoiceSelectionLogic — Post-challenge addition (8th section)
# ---------------------------------------------------------------------------


class TestFromAC_VoiceSelectionLogic:
    """Voice selection logic section — added after challanger identified gap.

    The research doc's content-split table explicitly assigns the 'detailed
    signal table' to h-voice-panel, not w-ideation. This section must exist
    in the handbook body.
    """

    def test_voice_selection_section_exists(self) -> None:
        """Voice selection logic section must be present per post-challenge addition."""
        body = _extract_body(_read_skill())
        assert re.search(r"##.*voice.*(selection|select)", body, re.IGNORECASE), (
            "Body must contain a Voice Selection section — added after challenger "
            "identified gap in the original 7-section outline"
        )

    def test_voice_selection_covers_multiple_voices(self) -> None:
        """Voice selection table/logic must address multiple voices, not just one."""
        body = _extract_body(_read_skill()).lower()
        # At least 3 distinct voice names must appear near selection context —
        # use a broad count check on all voice names in body
        present_count = sum(1 for v in _ALL_VOICE_AGENTS if v in body)
        assert present_count >= 3, (
            f"Voice selection logic covers only {present_count} voice(s); "
            "must address at least 3 of the 6 voices"
        )
