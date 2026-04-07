"""Tests for task #651: Create w-ideation/SKILL.md workflow.

Contract-level verification that share/skills/w-ideation/SKILL.md exists with the
required frontmatter and body content per the AC (including Architecture Review
amendments).

AC coverage:
  - AC1: share/skills/w-ideation/SKILL.md exists with valid YAML frontmatter
         (name: w-ideation, user-invocable: false, non-empty description)
  - AC2: Documents the 6-moment process flow (M1-M6) with Step 0 for setup and
         entry/exit criteria per moment (Architecture Review corrected M0-M5 → M1-M6)
  - AC3: Defines deliberation flow: Mediator → Voice panel → Critic loop → convergence
  - AC4: Specifies Blackboard contract: Working Directory layout, file ownership,
         read/write rules
  - AC5: Covers Brief artifact structure and handoff to pipeline
  - AC6: Covers adaptive depth (trivial → tiers 1-3) decision rules
  - AC7: Covers re-entry protocol (returning to existing Working Dir)
  - AC8: References all voice agents by name
"""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
_SKILL_FILE = _REPO_ROOT / "share" / "skills" / "w-ideation" / "SKILL.md"

# Voice agents that MUST be referenced by name per AC8
# Source: ideator.agent.md agents: list and spec section 7
_REQUIRED_VOICE_AGENTS: frozenset[str] = frozenset(
    {
        "critic-voice",
        "pragmatist-voice",
        "architect-voice",
        "data-voice",
        "enduser-voice",
        "security-voice",
    }
)


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
# TestFromAC_SkillFileAndFrontmatter (AC1)
# ---------------------------------------------------------------------------


class TestFromAC_SkillFileAndFrontmatter:
    """AC1: share/skills/w-ideation/SKILL.md must exist with valid YAML frontmatter."""

    def test_skill_file_exists(self) -> None:
        """AC1: SKILL.md must exist at share/skills/w-ideation/SKILL.md."""
        assert _SKILL_FILE.is_file(), (
            f"share/skills/w-ideation/SKILL.md does not exist -- builder must create it. "
            f"Checked: {_SKILL_FILE}"
        )

    def test_file_starts_with_frontmatter_delimiter(self) -> None:
        """AC1: file must begin with YAML frontmatter opening ---."""
        content = _read_skill()
        assert content.startswith("---\n"), (
            "w-ideation/SKILL.md must begin with --- to open YAML frontmatter"
        )

    def test_frontmatter_closing_delimiter_present(self) -> None:
        """AC1: frontmatter block must be closed with ---."""
        content = _read_skill()
        lines = content.splitlines()
        closing = [i for i, line in enumerate(lines[1:], start=1) if line == "---"]
        assert closing, "No closing --- delimiter found for YAML frontmatter"

    def test_name_is_w_ideation(self) -> None:
        """AC1: name: field in frontmatter must be w-ideation."""
        fm = _extract_frontmatter(_read_skill())
        match = re.search(r"^name:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "name: key not found in frontmatter"
        assert match.group(1).strip() == "w-ideation", (
            f"name must be 'w-ideation', got '{match.group(1).strip()}'"
        )

    def test_user_invocable_false(self) -> None:
        """AC1: user-invocable must be false (pipeline-only skill)."""
        fm = _extract_frontmatter(_read_skill())
        match = re.search(r"^user-invocable:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "user-invocable: key not found in frontmatter"
        assert match.group(1).strip() == "false", (
            f"user-invocable must be 'false', got '{match.group(1).strip()}'"
        )

    def test_description_key_present(self) -> None:
        """AC1: description: key must be present in frontmatter."""
        fm = _extract_frontmatter(_read_skill())
        assert re.search(r"^description:", fm, re.MULTILINE) is not None, (
            "description: key not found in frontmatter"
        )

    def test_description_is_non_empty(self) -> None:
        """AC1: description: value must not be empty."""
        fm = _extract_frontmatter(_read_skill())
        match = re.search(r'^description:\s*["\']?(.+?)["\']?\s*$', fm, re.MULTILINE)
        assert match is not None, "description: value is empty or missing"
        assert match.group(1).strip() not in ("", '""', "''"), (
            "description: value is empty"
        )

    def test_description_references_ideation_or_workflow(self) -> None:
        """AC1: description should convey the ideation/workflow nature of this skill."""
        fm = _extract_frontmatter(_read_skill())
        match = re.search(r'^description:\s*["\']?(.+?)["\']?\s*$', fm, re.MULTILINE)
        assert match is not None, "description: value is missing"
        desc = match.group(1).strip().lower()
        assert any(
            kw in desc
            for kw in ("ideation", "workflow", "process", "moment", "thinking", "brief")
        ), (
            f"description must reference ideation/workflow nature, got: '{desc}'"
        )

    def test_frontmatter_block_is_non_empty(self) -> None:
        """AC1: frontmatter block between --- delimiters must not be empty."""
        fm = _extract_frontmatter(_read_skill())
        assert fm.strip() != "", "Frontmatter block is empty"


# ---------------------------------------------------------------------------
# TestFromAC_SixMomentProcess (AC2)
# ---------------------------------------------------------------------------


class TestFromAC_SixMomentProcess:
    """AC2: SKILL.md must document the 6-moment process flow (M1-M6) with Step 0
    for setup and entry/exit criteria per moment.
    Architecture Review corrected AC wording: M1-M6 + Step 0 (not M0-M5).
    """

    def test_step_0_setup_present(self) -> None:
        """AC2: Step 0 (setup/entry logic) must be documented."""
        body = _extract_body(_read_skill())
        assert re.search(r"step\s+0", body, re.IGNORECASE) is not None, (
            "Step 0 (setup) section not found in SKILL.md body"
        )

    def test_moment_1_present(self) -> None:
        """AC2: M1 (Moment 1 / Step 1) must be documented."""
        body = _extract_body(_read_skill())
        # Match "M1", "Moment 1", "Step 1", "## Step 1", "### M1", etc.
        assert re.search(r"\b(M1|Moment\s+1|Step\s+1)\b", body, re.IGNORECASE) is not None, (
            "M1/Moment 1/Step 1 not found in SKILL.md body"
        )

    def test_moment_2_present(self) -> None:
        """AC2: M2 (Moment 2 / Step 2) must be documented."""
        body = _extract_body(_read_skill())
        assert re.search(r"\b(M2|Moment\s+2|Step\s+2)\b", body, re.IGNORECASE) is not None, (
            "M2/Moment 2/Step 2 not found in SKILL.md body"
        )

    def test_moment_3_present(self) -> None:
        """AC2: M3 (Moment 3 / Step 3) must be documented."""
        body = _extract_body(_read_skill())
        assert re.search(r"\b(M3|Moment\s+3|Step\s+3)\b", body, re.IGNORECASE) is not None, (
            "M3/Moment 3/Step 3 not found in SKILL.md body"
        )

    def test_moment_4_present(self) -> None:
        """AC2: M4 (Moment 4 / Step 4) must be documented."""
        body = _extract_body(_read_skill())
        assert re.search(r"\b(M4|Moment\s+4|Step\s+4)\b", body, re.IGNORECASE) is not None, (
            "M4/Moment 4/Step 4 not found in SKILL.md body"
        )

    def test_moment_5_present(self) -> None:
        """AC2: M5 (Moment 5 / Step 5) must be documented."""
        body = _extract_body(_read_skill())
        assert re.search(r"\b(M5|Moment\s+5|Step\s+5)\b", body, re.IGNORECASE) is not None, (
            "M5/Moment 5/Step 5 not found in SKILL.md body"
        )

    def test_moment_6_present(self) -> None:
        """AC2: M6 (Moment 6 / Step 6) must be documented."""
        body = _extract_body(_read_skill())
        assert re.search(r"\b(M6|Moment\s+6|Step\s+6)\b", body, re.IGNORECASE) is not None, (
            "M6/Moment 6/Step 6 not found in SKILL.md body"
        )

    def test_six_numbered_steps_or_moments_present(self) -> None:
        """AC2: all six moments (M1-M6) must each appear in SKILL.md."""
        body = _extract_body(_read_skill())
        found: list[str] = []
        for n in range(1, 7):
            pat = rf"\b(M{n}|Moment\s+{n}|Step\s+{n})\b"
            if re.search(pat, body, re.IGNORECASE):
                found.append(str(n))
        assert len(found) == 6, (
            f"Expected all 6 moments (1-6) to be present, found only: {found}"
        )

    def test_entry_or_exit_criteria_present(self) -> None:
        """AC2: entry and/or exit criteria must be documented for the moments."""
        body = _extract_body(_read_skill())
        assert re.search(
            r"\b(entry|exit)\s+(criteria|condition|gate|check)", body, re.IGNORECASE
        ) is not None, (
            "No entry/exit criteria language found in SKILL.md body — "
            "per AC2 each moment must document entry/exit criteria"
        )

    def test_m0_header_not_used(self) -> None:
        """AC2 (Architecture Review correction): M0 as a moment header must NOT be used;
        setup is Step 0, moments are M1-M6."""
        body = _extract_body(_read_skill())
        # M0 as a standalone moment/step label (not embedded in URLs or long phrases)
        assert re.search(r"^#+\s*(M0|Moment\s+0)\b", body, re.MULTILINE) is None, (
            "M0/Moment 0 must NOT be used as a step header — "
            "Architecture Review corrected this to M1-M6 + Step 0 for setup"
        )

    def test_investigator_mode_documented(self) -> None:
        """AC2: Investigator mode (M1-M3) must be documented in the process flow."""
        body = _extract_body(_read_skill())
        assert re.search(r"investigator", body, re.IGNORECASE) is not None, (
            "'Investigator' mode not mentioned in SKILL.md — must document M1-M3 mode"
        )

    def test_facilitative_mode_documented(self) -> None:
        """AC2: Facilitative mode (M4-M6) must be documented in the process flow."""
        body = _extract_body(_read_skill())
        assert re.search(r"facilitat", body, re.IGNORECASE) is not None, (
            "'Facilitative' mode not mentioned in SKILL.md — must document M4-M6 mode"
        )


# ---------------------------------------------------------------------------
# TestFromAC_DeliberationFlow (AC3)
# ---------------------------------------------------------------------------


class TestFromAC_DeliberationFlow:
    """AC3: SKILL.md must define the deliberation flow:
    Mediator → Voice panel → Critic loop → convergence.
    """

    def test_deliberation_flow_references_mediator(self) -> None:
        """AC3: deliberation flow must mention the Mediator role."""
        body = _extract_body(_read_skill())
        assert re.search(r"\bmediator\b", body, re.IGNORECASE) is not None, (
            "'Mediator' not found in SKILL.md body — must be referenced in deliberation flow"
        )

    def test_deliberation_flow_references_voice_panel(self) -> None:
        """AC3: deliberation flow must mention the voice panel."""
        body = _extract_body(_read_skill())
        assert re.search(
            r"\b(voice\s+panel|domain\s+voice|voice\s+deliberation)\b",
            body,
            re.IGNORECASE,
        ) is not None, (
            "Voice panel / domain voices not referenced in SKILL.md deliberation flow"
        )

    def test_deliberation_flow_references_critic_loop(self) -> None:
        """AC3: deliberation flow must describe the Critic loop (adversarial refinement)."""
        body = _extract_body(_read_skill())
        assert re.search(r"\bcritic\b", body, re.IGNORECASE) is not None, (
            "'Critic' not referenced in SKILL.md — must document Critic loop in deliberation flow"
        )
        assert re.search(r"\b(loop|cycle|refine|adversar|challenge)\b", body, re.IGNORECASE) is not None, (
            "Critic loop/cycle/refinement not described in SKILL.md"
        )

    def test_deliberation_flow_references_convergence_or_synthesis(self) -> None:
        """AC3: deliberation flow must reference convergence or synthesis as the endpoint."""
        body = _extract_body(_read_skill())
        assert re.search(r"\b(convergence|synthesis|synthesize|converge)\b", body, re.IGNORECASE) is not None, (
            "Convergence/synthesis endpoint not mentioned in SKILL.md deliberation flow"
        )

    def test_parallelism_of_voice_invocation_mentioned(self) -> None:
        """AC3: deliberation flow must note that domain voices are invoked in parallel."""
        body = _extract_body(_read_skill())
        assert re.search(r"\b(parallel|concurrent|simultaneously)\b", body, re.IGNORECASE) is not None, (
            "Parallel invocation of domain voices not mentioned in SKILL.md"
        )

    def test_pragmatist_synthesis_documented(self) -> None:
        """AC3: deliberation flow must mention pragmatist synthesis (synthesis.md production)."""
        body = _extract_body(_read_skill())
        assert re.search(r"\bpragmatist\b", body, re.IGNORECASE) is not None, (
            "'Pragmatist' not mentioned in SKILL.md — must document pragmatist synthesis step"
        )

    def test_synthesis_md_file_referenced(self) -> None:
        """AC3: the synthesis.md file that carries deliberation output must be referenced."""
        body = _extract_body(_read_skill())
        assert "synthesis.md" in body, (
            "'synthesis.md' not referenced in SKILL.md — "
            "this is the convergence artifact produced by the deliberation flow"
        )


# ---------------------------------------------------------------------------
# TestFromAC_BlackboardContract (AC4)
# ---------------------------------------------------------------------------


class TestFromAC_BlackboardContract:
    """AC4: SKILL.md must specify the Blackboard contract — Working Directory layout,
    file ownership, and read/write rules.
    """

    def test_blackboard_or_working_directory_section_present(self) -> None:
        """AC4: a Blackboard or Working Directory section must exist."""
        body = _extract_body(_read_skill())
        assert re.search(
            r"\b(blackboard|working\s+dir(?:ectory)?)\b", body, re.IGNORECASE
        ) is not None, (
            "No Blackboard/Working Directory section found in SKILL.md"
        )

    def test_context_md_in_working_directory_layout(self) -> None:
        """AC4: context.md must be listed in the Working Directory layout."""
        body = _extract_body(_read_skill())
        assert "context.md" in body, (
            "'context.md' not found in SKILL.md — must be listed in Working Directory layout"
        )

    def test_decisions_md_in_working_directory_layout(self) -> None:
        """AC4: decisions.md must be listed in the Working Directory layout."""
        body = _extract_body(_read_skill())
        assert "decisions.md" in body, (
            "'decisions.md' not found in SKILL.md — must be listed in Working Directory layout"
        )

    def test_brief_md_in_working_directory_layout(self) -> None:
        """AC4: brief.md must be listed in the Working Directory layout."""
        body = _extract_body(_read_skill())
        assert "brief.md" in body, (
            "'brief.md' not found in SKILL.md — must be listed in Working Directory layout"
        )

    def test_research_notes_md_in_working_directory_layout(self) -> None:
        """AC4: research-notes.md must be listed in the Working Directory layout."""
        body = _extract_body(_read_skill())
        assert "research-notes.md" in body, (
            "'research-notes.md' not found in SKILL.md — "
            "must be listed in Working Directory layout"
        )

    def test_voices_directory_structure_mentioned(self) -> None:
        """AC4: voices/ subdirectory (domain voice outputs) must be in Working Dir layout."""
        body = _extract_body(_read_skill())
        assert re.search(r"voices/", body) is not None, (
            "'voices/' subdirectory not mentioned in SKILL.md Working Directory layout"
        )

    def test_file_ownership_or_read_write_rules_present(self) -> None:
        """AC4: file ownership (who reads/writes each file) must be specified."""
        body = _extract_body(_read_skill())
        # Table with reads/writes, or ownership language
        assert re.search(r"\b(reads|writes|ownership|read/write|owns)\b", body, re.IGNORECASE) is not None, (
            "File ownership / read-write rules not found in SKILL.md Blackboard section"
        )

    def test_mediator_reads_only_summary_files_rule(self) -> None:
        """AC4: must state the Mediator's context economy rule — reads only summary files."""
        body = _extract_body(_read_skill())
        # The spec is explicit: mediator reads only context.md, decisions.md, synthesis.md
        assert re.search(
            r"mediator.{0,100}(only|context\.md|summary)", body, re.IGNORECASE | re.DOTALL
        ) is not None, (
            "Mediator read-only-summaries rule not documented in SKILL.md"
        )

    def test_working_directory_path_pattern_documented(self) -> None:
        """AC4: the .owlbear/briefs/ path for Working Directories must be documented."""
        body = _extract_body(_read_skill())
        assert re.search(r"\.owlbear/briefs", body) is not None, (
            "'.owlbear/briefs' path not found in SKILL.md — "
            "Working Directory location must be specified"
        )


# --------------------------------------------------------------------------
# TestFromAC_BriefArtifact (AC5)
# ---------------------------------------------------------------------------


class TestFromAC_BriefArtifact:
    """AC5: SKILL.md must cover the Brief artifact structure and handoff to pipeline."""

    def test_brief_artifact_section_present(self) -> None:
        """AC5: a Brief artifact section must exist."""
        body = _extract_body(_read_skill())
        assert re.search(
            r"\bbrief\b.{0,60}(artifact|structure|template|section)", body, re.IGNORECASE
        ) is not None or re.search(r"^#+.*brief", body, re.IGNORECASE | re.MULTILINE) is not None, (
            "No Brief artifact section found in SKILL.md"
        )

    def test_brief_contains_problem_field(self) -> None:
        """AC5: Brief structure must include a Problem field/section."""
        body = _extract_body(_read_skill())
        assert re.search(r"##\s*Problem|^Problem$|\*\*Problem\*\*|Problem:", body, re.MULTILINE) is not None, (
            "'Problem' field not found in Brief structure section of SKILL.md"
        )

    def test_brief_contains_outcomes_field(self) -> None:
        """AC5: Brief structure must include an Outcomes field/section."""
        body = _extract_body(_read_skill())
        assert re.search(r"##\s*Outcome|^Outcomes$|\*\*Outcomes?\*\*|Outcomes?:", body, re.MULTILINE) is not None, (
            "'Outcomes' field not found in Brief structure section of SKILL.md"
        )

    def test_brief_contains_approach_field(self) -> None:
        """AC5: Brief structure must include an Approach field/section."""
        body = _extract_body(_read_skill())
        assert re.search(r"##\s*Approach|^Approach$|\*\*Approach\*\*|Approach:", body, re.MULTILINE) is not None, (
            "'Approach' field not found in Brief structure section of SKILL.md"
        )

    def test_brief_contains_scope_field(self) -> None:
        """AC5: Brief structure must include a Scope field/section."""
        body = _extract_body(_read_skill())
        assert re.search(r"##\s*Scope|^Scope$|\*\*Scope\*\*|Scope:", body, re.MULTILINE) is not None, (
            "'Scope' field not found in Brief structure section of SKILL.md"
        )

    def test_brief_contains_investment_tier_field(self) -> None:
        """AC5: Brief structure must include an Investment Tier field."""
        body = _extract_body(_read_skill())
        assert re.search(r"investment\s+tier|tier:", body, re.IGNORECASE) is not None, (
            "'Investment Tier' not found in SKILL.md Brief structure"
        )

    def test_handoff_to_pipeline_documented(self) -> None:
        """AC5: handoff from Brief to pipeline (kanban task creation) must be documented."""
        body = _extract_body(_read_skill())
        assert re.search(
            r"\b(handoff|hand-off|hand off|pipeline|kanban|planner)\b", body, re.IGNORECASE
        ) is not None, (
            "Pipeline handoff (kanban task creation) not mentioned in SKILL.md"
        )

    def test_brief_file_location_documented(self) -> None:
        """AC5: brief.md file name or location must be referenced."""
        body = _extract_body(_read_skill())
        assert "brief.md" in body, (
            "'brief.md' not referenced in SKILL.md Brief artifact section"
        )


# ---------------------------------------------------------------------------
# TestFromAC_AdaptiveDepth (AC6)
# ---------------------------------------------------------------------------


class TestFromAC_AdaptiveDepth:
    """AC6: SKILL.md must cover adaptive depth — calibration rules from trivial to tiers 1-3."""

    def test_adaptive_depth_section_present(self) -> None:
        """AC6: an adaptive depth section or heading must exist."""
        body = _extract_body(_read_skill())
        assert re.search(
            r"\badaptive\s+depth\b|\bdepth\s+calibrat|\btier\s+calibrat",
            body,
            re.IGNORECASE,
        ) is not None, (
            "No adaptive depth section found in SKILL.md"
        )

    def test_trivial_or_skip_path_documented(self) -> None:
        """AC6: trivial/skip path (bypassing voice deliberation) must be documented."""
        body = _extract_body(_read_skill())
        assert re.search(r"\b(trivial|skip|bypass|compress)\b", body, re.IGNORECASE) is not None, (
            "Trivial/skip path not documented in SKILL.md adaptive depth section"
        )

    def test_tiers_documented(self) -> None:
        """AC6: investment tiers must be documented (Scratch/Tool/Shared/Production, or T1/T2/T3)."""
        body = _extract_body(_read_skill())
        # Accept either the named tiers or T1/T2/T3 notation
        has_named_tiers = re.search(
            r"\b(scratch|tool|shared|production)\b", body, re.IGNORECASE
        ) is not None
        has_tier_notation = re.search(r"\bT[123]\b", body) is not None
        assert has_named_tiers or has_tier_notation, (
            "Investment tiers (Scratch/Tool/Shared/Production or T1/T2/T3) "
            "not found in SKILL.md adaptive depth section"
        )

    def test_depth_calibration_rules_use_table_or_list(self) -> None:
        """AC6: depth calibration rules must use a table or structured list (per spec §9)."""
        body = _extract_body(_read_skill())
        # Tables use | and lists use - or numbered items
        assert re.search(r"\|.+\|", body) is not None or re.search(
            r"^[-*]\s", body, re.MULTILINE
        ) is not None, (
            "Adaptive depth calibration rules must be in table or list form — "
            "no table or list found in SKILL.md"
        )

    def test_high_tier_full_depth_path_documented(self) -> None:
        """AC6: high investment tier path (full depth) must be documented."""
        body = _extract_body(_read_skill())
        assert re.search(
            r"\b(full\s+depth|all\s+voice|high\s+tier|production|shared|novel)\b",
            body,
            re.IGNORECASE,
        ) is not None, (
            "High-investment-tier / full-depth path not documented in adaptive depth section"
        )

    def test_transparency_statement_present(self) -> None:
        """AC6: SKILL.md must require the Mediator to announce depth calibration to user."""
        body = _extract_body(_read_skill())
        assert re.search(r"\b(transparen|announc|tell|narrat|state)\b", body, re.IGNORECASE) is not None, (
            "Mediator transparency requirement not found in SKILL.md — "
            "must tell user how depth is being calibrated"
        )


# ---------------------------------------------------------------------------
# TestFromAC_ReEntryProtocol (AC7)
# ---------------------------------------------------------------------------


class TestFromAC_ReEntryProtocol:
    """AC7: SKILL.md must cover re-entry protocol for returning to an existing Working Dir."""

    def test_re_entry_section_present(self) -> None:
        """AC7: a re-entry section or heading must exist."""
        body = _extract_body(_read_skill())
        assert re.search(
            r"\b(re-?entry|re-?enter|return(?:ing)?\s+to\s+existing|mid.?execution|returning)\b",
            body,
            re.IGNORECASE,
        ) is not None, (
            "No re-entry / returning-to-existing section found in SKILL.md"
        )

    def test_re_entry_loads_working_directory(self) -> None:
        """AC7: re-entry must load the existing Working Directory."""
        body = _extract_body(_read_skill())
        assert re.search(
            r"(load|read|existing)\s+(working\s+dir|working\s+directory|briefs|context\.md)",
            body,
            re.IGNORECASE,
        ) is not None, (
            "Re-entry protocol does not mention loading the existing Working Directory"
        )

    def test_re_entry_loads_board_state(self) -> None:
        """AC7: re-entry must check current board/kanban state."""
        body = _extract_body(_read_skill())
        assert re.search(
            r"\b(board|kanban|task|current\s+state)\b", body, re.IGNORECASE
        ) is not None, (
            "Re-entry protocol does not mention loading board/kanban state"
        )

    def test_re_entry_enters_at_relevant_moment(self) -> None:
        """AC7: re-entry must re-enter at the relevant moment (M1 or M4 depending on scope)."""
        body = _extract_body(_read_skill())
        assert re.search(
            r"(re-?enter|enter)\s+at.{0,30}(moment|M[14]|step)",
            body,
            re.IGNORECASE,
        ) is not None or re.search(
            r"(relevant\s+moment|appropriate\s+moment|M1\s+or\s+M4|M4\s+or\s+M1)",
            body,
            re.IGNORECASE,
        ) is not None, (
            "Re-entry protocol does not specify entering at the relevant moment"
        )

    def test_re_entry_handles_obsolete_tasks(self) -> None:
        """AC7: re-entry must describe handling changed direction (archives/updates tasks)."""
        body = _extract_body(_read_skill())
        assert re.search(
            r"\b(obsolete|archive|update|changed\s+direction|new\s+task)\b",
            body,
            re.IGNORECASE,
        ) is not None, (
            "Re-entry protocol does not describe handling obsolete tasks or changed direction"
        )


# ---------------------------------------------------------------------------
# TestFromAC_VoiceAgentReferences (AC8)
# ---------------------------------------------------------------------------


class TestFromAC_VoiceAgentReferences:
    """AC8: SKILL.md must reference all voice agents by name."""

    def test_critic_voice_referenced(self) -> None:
        """AC8: critic-voice must be referenced by name."""
        body = _extract_body(_read_skill())
        assert "critic-voice" in body, (
            "'critic-voice' not referenced in SKILL.md — AC8 requires all voice agents by name"
        )

    def test_pragmatist_voice_referenced(self) -> None:
        """AC8: pragmatist-voice must be referenced by name."""
        body = _extract_body(_read_skill())
        assert "pragmatist-voice" in body, (
            "'pragmatist-voice' not referenced in SKILL.md — AC8 requires all voice agents by name"
        )

    def test_architect_voice_referenced(self) -> None:
        """AC8: architect-voice must be referenced by name."""
        body = _extract_body(_read_skill())
        assert "architect-voice" in body, (
            "'architect-voice' not referenced in SKILL.md — AC8 requires all voice agents by name"
        )

    def test_data_voice_referenced(self) -> None:
        """AC8: data-voice must be referenced by name."""
        body = _extract_body(_read_skill())
        assert "data-voice" in body, (
            "'data-voice' not referenced in SKILL.md — AC8 requires all voice agents by name"
        )

    def test_enduser_voice_referenced(self) -> None:
        """AC8: enduser-voice must be referenced by name."""
        body = _extract_body(_read_skill())
        assert "enduser-voice" in body, (
            "'enduser-voice' not referenced in SKILL.md — AC8 requires all voice agents by name"
        )

    def test_security_voice_referenced(self) -> None:
        """AC8: security-voice must be referenced by name."""
        body = _extract_body(_read_skill())
        assert "security-voice" in body, (
            "'security-voice' not referenced in SKILL.md — AC8 requires all voice agents by name"
        )

    def test_all_required_voice_agents_referenced(self) -> None:
        """AC8: summary test — all 6 required voice agents must appear in SKILL.md."""
        body = _extract_body(_read_skill())
        missing = [agent for agent in sorted(_REQUIRED_VOICE_AGENTS) if agent not in body]
        assert not missing, (
            f"The following voice agents are missing from SKILL.md: {missing}"
        )

    def test_no_unnamed_placeholder_for_voices(self) -> None:
        """AC8: voice agents must be named explicitly, not as '[voice name]' placeholders."""
        body = _extract_body(_read_skill())
        # If placeholder text [voice name] or [agent name] exists, the spec is incomplete
        assert re.search(r"\[voice\s+name\]|\[agent\s+name\]", body, re.IGNORECASE) is None, (
            "Placeholder '[voice name]' found in SKILL.md — agents must be named explicitly"
        )
