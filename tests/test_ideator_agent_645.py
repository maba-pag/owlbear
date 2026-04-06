"""Tests for task #645: Create ideator.agent.md (Mediator).

Contract-level verification that share/agents/ideator.agent.md exists with the
required frontmatter and body content per the AC (including Architecture Review
amendments).

AC coverage:
  - AC1:  share/agents/ideator.agent.md exists with valid YAML frontmatter
  - AC2:  user-invocable: true with argument-hint containing key ideation phrase
  - AC3:  model: Claude Opus 4.6 (copilot) configured
  - AC4:  Persona implements Mediator behavior: single user-facing voice throughout 6 moments
  - AC5:  Investigator mode for Moments 1-3 (problem mining, outcome shaping)
  - AC6:  Facilitative mode for Moments 4-6 (presenting synthesis, decisions, Brief)
  - AC7:  Transparent-by-default at all decision points (tier, voice selection,
          loop-back, Brief approval)
  - AC8:  Entry point logic: creates Working Directory, reads input/, detects new
          vs. existing project
  - AC9:  Invokes critic-voice at moment boundaries (after M1, M2, M4, M5)
  - AC10: Invokes research subagent for M3 landscape scan
  - AC11: Invokes domain voices between M3 and M4 (parallel runSubagent)
  - AC12: Invokes pragmatist-voice for synthesis
  - AC13: Reads only summary files (context.md, decisions.md, synthesis.md) -- never debates
  - AC14: Writes context.md incrementally, decisions.md after user choices, brief.md at approval
  - AC15: Handoff: creates parent kanban task with Brief content, invokes planner for subtasks
  - AC16: Tool access per Architecture Review amendment: edit/createDirectory,
          edit/createFile, edit/editFiles, read/readFile, read/viewImage, search,
          owlbear-kanban/create_task, owlbear-kanban/list_tasks,
          owlbear-kanban/show_task, owlbear-project/*, owlbear-knowledge/search-knowledge,
          vscode/memory, owlbear-memory/*, agent.
          No vscode/askQuestions (blanket ban enforced by #123).
  - AC17: Agents list (amended): critic-voice, pragmatist-voice, architect-voice,
          data-voice, enduser-voice, security-voice, planner, Explore
  - NewAC: disable-model-invocation must NOT be present or must be false
           (user-invocable agent, matching orchestrator/planner pattern)
"""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
_AGENT_FILE = _REPO_ROOT / "share" / "agents" / "ideator.agent.md"

_REQUIRED_TOOLS: frozenset[str] = frozenset(
    {
        "edit/createDirectory",
        "edit/createFile",
        "edit/editFiles",
        "read/readFile",
        "read/viewImage",
        "search",
        "owlbear-kanban/create_task",
        "owlbear-kanban/list_tasks",
        "owlbear-kanban/show_task",
        "owlbear-project/*",
        "owlbear-knowledge/search-knowledge",
        "vscode/memory",
        "owlbear-memory/*",
        "agent",
    }
)

_REQUIRED_AGENTS: frozenset[str] = frozenset(
    {
        "critic-voice",
        "pragmatist-voice",
        "architect-voice",
        "data-voice",
        "enduser-voice",
        "security-voice",
        "planner",
        "Explore",
    }
)

_FORBIDDEN_TOOLS: frozenset[str] = frozenset(
    {
        "vscode/askQuestions",
        "owlbear-kanban/pick_tasks",
        "owlbear-kanban/move_task",
        "owlbear-kanban/edit_task",
        "owlbear-kanban/start_work",
        "owlbear-kanban/end_work",
    }
)


def _read_agent() -> str:
    return _AGENT_FILE.read_text(encoding="utf-8")


def _extract_frontmatter(content: str) -> str:
    """Extract text between leading --- ... --- block."""
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    assert match is not None, (
        f"No valid YAML frontmatter (--- ... ---) found in {_AGENT_FILE.name}"
    )
    return match.group(1)


def _extract_body(content: str) -> str:
    """Extract text after the closing --- of frontmatter."""
    match = re.match(r"^---\n.*?\n---\n(.*)", content, re.DOTALL)
    assert match is not None, (
        f"No body content found after frontmatter in {_AGENT_FILE.name}"
    )
    return match.group(1)


def _extract_tools_from_frontmatter(fm: str) -> list[str]:
    """Parse tools from YAML frontmatter (inline or multiline bracket syntax)."""
    match = re.search(r"^tools:\s*\[([^\]]*)\]", fm, re.MULTILINE)
    if not match:
        match = re.search(r"^tools:\s*\n\s*\[([^\]]*)\]", fm, re.MULTILINE)
    assert match is not None, (
        "tools: key not found or not in bracket syntax in frontmatter"
    )
    raw = match.group(1)
    return [t.strip().strip("'\"") for t in raw.split(",") if t.strip()]


def _extract_agents_from_frontmatter(fm: str) -> list[str]:
    """Parse agents from YAML frontmatter (inline bracket or block-list)."""
    bracket_match = re.search(r"^agents:\s*\[([^\]]*)\]", fm, re.MULTILINE)
    if bracket_match:
        raw = bracket_match.group(1)
        return [a.strip().strip("'\"") for a in raw.split(",") if a.strip()]
    block_match = re.search(r"^agents:\s*\n((?:[ \t]+-[ \t]+\S.*\n?)+)", fm, re.MULTILINE)
    if block_match:
        lines = block_match.group(1).splitlines()
        return [re.sub(r"^[ \t]+-[ \t]+", "", line).strip() for line in lines if line.strip()]
    return []


# ---------------------------------------------------------------------------
# Class 1: Frontmatter structure and key field values
# ---------------------------------------------------------------------------


class TestFromAC_IdeatorFrontmatter:
    """AC1-AC3, AC16-AC17, NewAC: ideator.agent.md must exist with correct frontmatter."""

    # ---- AC1: file exists with valid YAML frontmatter -----------------------

    def test_file_exists(self) -> None:
        """AC1: ideator.agent.md must exist at share/agents/ideator.agent.md."""
        assert _AGENT_FILE.is_file(), (
            "share/agents/ideator.agent.md does not exist -- builder must create it"
        )

    def test_file_starts_with_frontmatter_delimiter(self) -> None:
        """AC1: File must begin with YAML frontmatter ---."""
        content = _read_agent()
        assert content.startswith("---\n"), (
            "ideator.agent.md must begin with --- to open YAML frontmatter"
        )

    def test_frontmatter_block_is_non_empty(self) -> None:
        """AC1: Frontmatter block between --- delimiters must not be empty."""
        fm = _extract_frontmatter(_read_agent())
        assert fm.strip() != "", "Frontmatter block is empty"

    def test_name_is_ideator(self) -> None:
        """Implied: name field must be ideator matching the file stem."""
        fm = _extract_frontmatter(_read_agent())
        match = re.search(r"^name:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "name: key not found in frontmatter"
        assert match.group(1).strip() == "ideator", (
            f"name must be 'ideator', got '{match.group(1).strip()}'"
        )

    def test_description_exists_and_non_empty(self) -> None:
        """Implied: description: must be present and non-empty."""
        fm = _extract_frontmatter(_read_agent())
        match = re.search(r"^description:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "description: key not found in frontmatter"
        assert match.group(1).strip() != "", "description: value is empty"

    def test_description_references_ideation_or_mediator(self) -> None:
        """Implied: description should convey ideation/mediator/thinking companion role."""
        fm = _extract_frontmatter(_read_agent())
        match = re.search(r"^description:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "description: key not found in frontmatter"
        desc = match.group(1).strip().lower()
        assert any(
            kw in desc
            for kw in ("idea", "mediator", "thinking", "companion", "feature", "problem")
        ), (
            f"description must reference ideation/mediator/thinking role, got: '{desc}'"
        )

    # ---- AC2: user-invocable: true + argument-hint --------------------------

    def test_user_invocable_true(self) -> None:
        """AC2: user-invocable must be true."""
        fm = _extract_frontmatter(_read_agent())
        match = re.search(r"^user-invocable:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "user-invocable: key not found in frontmatter"
        assert match.group(1).strip() == "true", (
            f"user-invocable must be 'true', got '{match.group(1).strip()}'"
        )

    def test_argument_hint_exists(self) -> None:
        """AC2: argument-hint: key must be present."""
        fm = _extract_frontmatter(_read_agent())
        assert re.search(r"^argument-hint:", fm, re.MULTILINE), (
            "argument-hint: key not found in frontmatter"
        )

    def test_argument_hint_mentions_idea_or_problem_or_feature(self) -> None:
        """AC2: argument-hint must mention idea, problem, or feature per AC spec."""
        fm = _extract_frontmatter(_read_agent())
        hint_match = re.search(r"^argument-hint:\s*(.+)$", fm, re.MULTILINE)
        assert hint_match is not None, "argument-hint: value not found"
        hint = hint_match.group(1).strip().lower()
        assert "idea" in hint or "problem" in hint or "feature" in hint, (
            f"argument-hint must contain 'idea', 'problem', or 'feature', got: '{hint}'"
        )

    def test_argument_hint_references_briefs_input_directory(self) -> None:
        """AC2: argument-hint must reference .owlbear/briefs input or equivalent."""
        fm = _extract_frontmatter(_read_agent())
        hint_match = re.search(r"^argument-hint:\s*(.+)$", fm, re.MULTILINE)
        assert hint_match is not None, "argument-hint: value not found"
        hint = hint_match.group(1).strip()
        assert "briefs" in hint or "input" in hint or ".owlbear" in hint, (
            f"argument-hint must reference the briefs input directory, got: '{hint}'"
        )

    # ---- AC3: model: Claude Opus 4.6 (copilot) ------------------------------

    def test_model_contains_claude_opus_46(self) -> None:
        """AC3: model must specify Claude Opus 4.6."""
        fm = _extract_frontmatter(_read_agent())
        match = re.search(r"^model:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "model: key not found in frontmatter"
        model_val = match.group(1).strip()
        assert re.search(r"opus.{0,5}4\.6", model_val, re.IGNORECASE) or re.search(
            r"claude.{0,15}opus", model_val, re.IGNORECASE
        ), (
            f"model must contain 'Claude Opus 4.6', got '{model_val}'"
        )

    def test_model_is_copilot_provider(self) -> None:
        """AC3: model must specify the (copilot) provider."""
        fm = _extract_frontmatter(_read_agent())
        match = re.search(r"^model:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "model: key not found in frontmatter"
        assert "copilot" in match.group(1).strip().lower(), (
            f"model must specify (copilot) provider, got '{match.group(1).strip()}'"
        )

    def test_model_is_single_string_not_array(self) -> None:
        """AC3: model must be a simple string, not a fallback array."""
        fm = _extract_frontmatter(_read_agent())
        match = re.search(r"^model:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "model: key not found in frontmatter"
        assert not match.group(1).strip().startswith("["), (
            f"model must be a single string, not a fallback array, got '{match.group(1).strip()}'"
        )

    # ---- NewAC: disable-model-invocation must NOT be true -------------------

    def test_disable_model_invocation_not_set_or_false(self) -> None:
        """NewAC: disable-model-invocation must not be true -- ideator is user-invocable."""
        fm = _extract_frontmatter(_read_agent())
        match = re.search(r"^disable-model-invocation:\s*(.+)$", fm, re.MULTILINE)
        if match is not None:
            value = match.group(1).strip()
            assert value != "true", (
                "disable-model-invocation must not be 'true' for a user-invocable agent "
                "(matches orchestrator and planner pattern)"
            )

    # ---- AC16: tools exact set -----------------------------------------------

    def test_tools_key_exists(self) -> None:
        """AC16: tools: key must be present in frontmatter."""
        fm = _extract_frontmatter(_read_agent())
        assert re.search(r"^tools:", fm, re.MULTILINE), (
            "tools: key not found in frontmatter"
        )

    def test_tools_contain_all_required(self) -> None:
        """AC16: tools must include every required tool from the Architecture Review amendment."""
        fm = _extract_frontmatter(_read_agent())
        tools = frozenset(_extract_tools_from_frontmatter(fm))
        missing = _REQUIRED_TOOLS - tools
        assert not missing, (
            f"Required tools missing from frontmatter:\n"
            f"  Missing: {sorted(missing)}\n"
            f"  Present: {sorted(tools)}"
        )

    def test_tools_count_is_fourteen(self) -> None:
        """AC16: tools list must contain exactly 14 entries per Architecture Review amendment."""
        fm = _extract_frontmatter(_read_agent())
        tools = _extract_tools_from_frontmatter(fm)
        assert len(tools) == 14, (
            f"Expected exactly 14 tools (per AC16 amendment), got {len(tools)}: {tools}"
        )

    def test_no_ask_questions_tool(self) -> None:
        """AC16: vscode/askQuestions must NOT be in tools (blanket ban, task #123)."""
        fm = _extract_frontmatter(_read_agent())
        tools = _extract_tools_from_frontmatter(fm)
        assert "vscode/askQuestions" not in tools, (
            "vscode/askQuestions is banned across all agents (test #123 / AC16 amendment)"
        )

    def test_no_pipeline_kanban_tools(self) -> None:
        """AC16: Pipeline-only kanban tools must not be present (ideator is not a pipeline agent)."""
        fm = _extract_frontmatter(_read_agent())
        tools = _extract_tools_from_frontmatter(fm)
        found = [t for t in tools if t in _FORBIDDEN_TOOLS]
        assert not found, (
            f"Forbidden pipeline-only tools found: {found}. "
            "Ideator uses create_task/list_tasks/show_task only (T3 support, not T1/T2 pipeline)."
        )

    def test_tools_include_agent_tool(self) -> None:
        """AC16: agent tool must be present to enable subagent dispatch (voice invocation)."""
        fm = _extract_frontmatter(_read_agent())
        tools = _extract_tools_from_frontmatter(fm)
        assert "agent" in tools, (
            "tools must include 'agent' for voice subagent dispatch (AC16 + AC11 requirement)"
        )

    def test_tools_include_kanban_create(self) -> None:
        """AC15/AC16: owlbear-kanban/create_task required for Brief handoff."""
        fm = _extract_frontmatter(_read_agent())
        tools = _extract_tools_from_frontmatter(fm)
        assert "owlbear-kanban/create_task" in tools, (
            "owlbear-kanban/create_task must be in tools for Brief-to-kanban handoff (AC15)"
        )

    def test_tools_include_knowledge_search(self) -> None:
        """AC16: owlbear-knowledge/search-knowledge required for M3 landscape scan support."""
        fm = _extract_frontmatter(_read_agent())
        tools = _extract_tools_from_frontmatter(fm)
        assert "owlbear-knowledge/search-knowledge" in tools, (
            "owlbear-knowledge/search-knowledge must be in tools (first-of-kind namespace, AC16)"
        )

    def test_tools_include_owlbear_project_wildcard(self) -> None:
        """AC16: owlbear-project/* required for project context reading."""
        fm = _extract_frontmatter(_read_agent())
        tools = _extract_tools_from_frontmatter(fm)
        assert "owlbear-project/*" in tools, (
            "owlbear-project/* must be in tools (first-of-kind namespace, AC16)"
        )

    def test_no_execute_tools(self) -> None:
        """AC16: No execute/* tools -- ideator is an ideation agent, not a pipeline executor."""
        fm = _extract_frontmatter(_read_agent())
        tools = _extract_tools_from_frontmatter(fm)
        found = [t for t in tools if t.startswith("execute/")]
        assert not found, (
            f"Forbidden execute/* tools found: {found}. "
            "Ideator must not run terminal commands."
        )

    # ---- AC17: agents list --------------------------------------------------

    def test_agents_key_exists(self) -> None:
        """AC17: agents: key must be present in frontmatter."""
        fm = _extract_frontmatter(_read_agent())
        assert re.search(r"^agents:", fm, re.MULTILINE), (
            "agents: key not found in frontmatter"
        )

    def test_agents_contain_all_required(self) -> None:
        """AC17 (amended): agents list must include all 8 required voice agents."""
        fm = _extract_frontmatter(_read_agent())
        agents = frozenset(_extract_agents_from_frontmatter(fm))
        missing = _REQUIRED_AGENTS - agents
        assert not missing, (
            f"Required agents missing from frontmatter:\n"
            f"  Missing: {sorted(missing)}\n"
            f"  Present: {sorted(agents)}"
        )

    def test_agents_count_is_eight(self) -> None:
        """AC17 (amended): agents list must contain exactly 8 entries."""
        fm = _extract_frontmatter(_read_agent())
        agents = _extract_agents_from_frontmatter(fm)
        assert len(agents) == 8, (
            f"Expected exactly 8 agents (per AC17 amendment), got {len(agents)}: {agents}"
        )

    def test_agents_includes_explore(self) -> None:
        """AC17 (amended): Explore must be in agents list (added for M3 landscape scan)."""
        fm = _extract_frontmatter(_read_agent())
        agents = _extract_agents_from_frontmatter(fm)
        assert "Explore" in agents, (
            "agents must include 'Explore' (added by Architecture Review for M3 scan)"
        )

    def test_agents_includes_pragmatist_voice(self) -> None:
        """AC12/AC17: pragmatist-voice must be in agents list for synthesis invocation."""
        fm = _extract_frontmatter(_read_agent())
        agents = _extract_agents_from_frontmatter(fm)
        assert "pragmatist-voice" in agents, (
            "agents must include 'pragmatist-voice' for synthesis (AC12)"
        )

    def test_agents_includes_planner(self) -> None:
        """AC15/AC17: planner must be in agents list for Brief handoff."""
        fm = _extract_frontmatter(_read_agent())
        agents = _extract_agents_from_frontmatter(fm)
        assert "planner" in agents, (
            "agents must include 'planner' for Brief-to-kanban handoff (AC15)"
        )


# ---------------------------------------------------------------------------
# Class 2: Persona and behavioral modes
# ---------------------------------------------------------------------------


class TestFromAC_IdeatorPersona:
    """AC4-AC7: Mediator persona with dual-mode behavior and transparency."""

    def _body(self) -> str:
        return _extract_body(_read_agent())

    # ---- AC4: Mediator persona, single user-facing voice --------------------

    def test_persona_section_exists(self) -> None:
        """AC4: body must contain a <persona> XML tag section."""
        assert "<persona>" in self._body(), "Body must contain a <persona> section"

    def test_persona_section_closed(self) -> None:
        """AC4: <persona> section must be properly closed with </persona>."""
        assert "</persona>" in self._body(), "Body must contain a closing </persona> tag"

    def test_persona_references_mediator_role(self) -> None:
        """AC4: Persona must frame the agent as a Mediator."""
        body = self._body()
        persona_match = re.search(r"<persona>(.*?)</persona>", body, re.DOTALL)
        assert persona_match is not None, "<persona>...</persona> block not found"
        persona = persona_match.group(1).lower()
        assert "mediator" in persona or "single voice" in persona or "guide" in persona, (
            "Persona must frame the agent as a Mediator or single guiding voice (AC4)"
        )

    def test_body_references_six_moments(self) -> None:
        """AC4: Body must reference the 6-moment conversation structure."""
        body = self._body()
        assert re.search(
            r"6 moment|six moment|6-moment", body, re.IGNORECASE
        ) or (re.search(r"\bM1\b", body) and re.search(r"\bM6\b", body)), (
            "Body must reference the 6-moment structure (Mediator manages all 6 moments)"
        )

    # ---- AC5: Investigator mode for Moments 1-3 ----------------------------

    def test_investigator_mode_mentioned(self) -> None:
        """AC5: Body must mention Investigator mode for moments 1-3."""
        body = self._body()
        assert re.search(r"investigat", body, re.IGNORECASE), (
            "Body must describe Investigator mode (AC5: M1-M3 problem mining)"
        )

    def test_body_mentions_problem_mining_or_outcome_shaping(self) -> None:
        """AC5: Body must describe problem mining or outcome shaping for M1-M3."""
        body = self._body()
        assert re.search(
            r"problem.{0,20}(mining|discover|understand|defin)|"
            r"outcome.{0,20}shap|"
            r"(mining|shaping|discover).{0,20}(problem|outcome|goal)",
            body,
            re.IGNORECASE,
        ), (
            "Body must describe problem mining or outcome shaping (AC5: Investigator mode M1-M3)"
        )

    def test_moments_1_and_3_referenced(self) -> None:
        """AC5: Moments 1 and 3 must be explicitly referenced to define Investigator scope."""
        body = self._body()
        assert re.search(r"M1|Moment 1|moment one", body, re.IGNORECASE), (
            "Body must reference Moment 1 to define Investigator mode start (AC5)"
        )
        assert re.search(r"M3|Moment 3|moment three", body, re.IGNORECASE), (
            "Body must reference Moment 3 to define Investigator mode end (AC5)"
        )

    # ---- AC6: Facilitative mode for Moments 4-6 ----------------------------

    def test_facilitative_mode_mentioned(self) -> None:
        """AC6: Body must mention Facilitative mode for moments 4-6."""
        body = self._body()
        assert re.search(r"facilitat", body, re.IGNORECASE), (
            "Body must describe Facilitative mode (AC6: M4-M6 synthesis/decisions/Brief)"
        )

    def test_moments_4_and_6_referenced(self) -> None:
        """AC6: Moments 4 and 6 must be explicitly referenced to define Facilitative scope."""
        body = self._body()
        assert re.search(r"M4|Moment 4|moment four", body, re.IGNORECASE), (
            "Body must reference Moment 4 to define Facilitative mode start (AC6)"
        )
        assert re.search(r"M6|Moment 6|moment six", body, re.IGNORECASE), (
            "Body must reference Moment 6 to define Facilitative mode end (AC6)"
        )

    def test_body_mentions_synthesis_or_decisions_or_brief(self) -> None:
        """AC6: Body must reference synthesis, decisions, or Brief production in M4-M6."""
        body = self._body()
        assert re.search(r"synthesis|decisions|brief\.md|brief approval", body, re.IGNORECASE), (
            "Body must mention synthesis, decisions, or Brief in facilitative context (AC6)"
        )

    # ---- AC7: Transparent-by-default ----------------------------------------

    def test_transparent_by_default_mentioned(self) -> None:
        """AC7: Body must require transparency at decision points."""
        body = self._body()
        assert re.search(
            r"transparent|transparency|explicit.{0,20}decision|"
            r"narrat.{0,20}(decision|choice|tier|select)",
            body,
            re.IGNORECASE,
        ), (
            "Body must describe transparent-by-default behavior at decision points (AC7)"
        )

    def test_body_mentions_tier_detection(self) -> None:
        """AC7: Body must reference investment tier detection (transparency point 1)."""
        body = self._body()
        assert re.search(r"\btier\b", body, re.IGNORECASE), (
            "Body must mention tier (investment tier detection is a transparency point, AC7)"
        )

    def test_body_mentions_brief_approval_step(self) -> None:
        """AC7/AC14: Body must reference Brief approval as a transparency checkpoint."""
        body = self._body()
        assert re.search(r"brief.{0,30}(approv|confirm|review)", body, re.IGNORECASE), (
            "Body must mention Brief approval (transparency point + write trigger, AC7/AC14)"
        )


# ---------------------------------------------------------------------------
# Class 3: Entry point and working directory logic
# ---------------------------------------------------------------------------


class TestFromAC_IdeatorEntryPoint:
    """AC8: Working Directory creation, input/ reading, new vs. existing project detection."""

    def _body(self) -> str:
        return _extract_body(_read_agent())

    def test_working_directory_mentioned(self) -> None:
        """AC8: Body must reference creating a Working Directory."""
        body = self._body()
        assert re.search(r"working dir", body, re.IGNORECASE), (
            "Body must mention Working Directory creation (AC8 entry point logic)"
        )

    def test_input_dir_mentioned(self) -> None:
        """AC8: Body must reference reading from input/ directory."""
        body = self._body()
        assert re.search(r"input/|input dir|\.owlbear/briefs", body, re.IGNORECASE), (
            "Body must reference reading from input/ directory (AC8)"
        )

    def test_new_vs_existing_project_detection_mentioned(self) -> None:
        """AC8: Body must describe logic distinguishing new from existing projects."""
        body = self._body()
        assert re.search(
            r"new.{0,20}project|existing.{0,20}project|"
            r"(detect|identify).{0,30}(project|existing)|"
            r"project.{0,20}(exist|new|type)",
            body,
            re.IGNORECASE,
        ), (
            "Body must describe new vs. existing project detection (AC8 entry point logic)"
        )

    def test_briefs_directory_path_referenced(self) -> None:
        """AC8: Body must reference the .owlbear/briefs/ Working Directory path."""
        body = self._body()
        assert re.search(r"\.owlbear.{0,10}briefs|briefs.{0,10}draft", body, re.IGNORECASE), (
            "Body must reference .owlbear/briefs/ as the Working Directory path (AC8)"
        )


# ---------------------------------------------------------------------------
# Class 4: Voice orchestration and subagent invocation
# ---------------------------------------------------------------------------


class TestFromAC_IdeatorVoiceOrchestration:
    """AC9-AC12: critic-voice at boundaries, research M3, parallel domain voices, pragmatist."""

    def _body(self) -> str:
        return _extract_body(_read_agent())

    # ---- AC9: critic-voice at moment boundaries (M1, M2, M4, M5) -----------

    def test_critic_voice_invocation_mentioned(self) -> None:
        """AC9: Body must describe invoking critic-voice."""
        body = self._body()
        assert "critic-voice" in body or re.search(r"critic.{0,10}voice", body, re.IGNORECASE), (
            "Body must describe invoking critic-voice (AC9)"
        )

    def test_critic_voice_at_moment_boundaries(self) -> None:
        """AC9: Body must associate critic-voice invocation with moment boundaries."""
        body = self._body()
        has_critic = bool(
            "critic-voice" in body or re.search(r"critic.{0,10}voice", body, re.IGNORECASE)
        )
        has_boundary = bool(
            re.search(r"after M[1245]|M[1245].{0,30}critic|boundary", body, re.IGNORECASE)
        )
        assert has_critic, (
            "Body must mention critic-voice (AC9)"
        )
        assert has_boundary, (
            "Body must associate critic-voice with moment boundaries after M1/M2/M4/M5 (AC9)"
        )

    # ---- AC10: research subagent for M3 -------------------------------------

    def test_research_subagent_mentioned_for_m3(self) -> None:
        """AC10: Body must instruct invoking research subagent or Explore for M3 landscape scan."""
        body = self._body()
        assert re.search(
            r"(research|explore).{0,40}(M3|moment.?3|landscape|scan)|"
            r"(M3|moment.?3).{0,40}(research|explore|landscape|scan)",
            body,
            re.IGNORECASE,
        ), (
            "Body must describe invoking a research subagent (Explore) for M3 landscape scan (AC10)"
        )

    def test_landscape_scan_mentioned(self) -> None:
        """AC10: Body must mention landscape scan as the M3 research purpose."""
        body = self._body()
        assert re.search(r"landscape|scan|survey|market|space", body, re.IGNORECASE), (
            "Body must mention landscape scan purpose for M3 (AC10)"
        )

    # ---- AC11: parallel domain voice invocation M3-M4 ----------------------

    def test_domain_voices_parallel_invocation(self) -> None:
        """AC11: Body must describe parallel domain voice invocation between M3 and M4."""
        body = self._body()
        assert re.search(r"parallel|concurrent|simultaneously", body, re.IGNORECASE), (
            "Body must describe parallel domain voice invocation between M3 and M4 (AC11)"
        )

    def test_body_references_domain_voices_between_m3_and_m4(self) -> None:
        """AC11: Domain voices are invoked between M3 and M4 (voice deliberation phase)."""
        body = self._body()
        has_voices = bool(
            re.search(r"domain.{0,20}voice|voice.{0,20}deliberat", body, re.IGNORECASE)
        )
        has_m3_m4 = bool(
            re.search(r"M3.{0,50}M4|between.*M3.*M4|after M3|before M4", body, re.IGNORECASE)
        )
        assert has_voices or has_m3_m4, (
            "Body must place domain voice invocations between M3 and M4 (AC11)"
        )

    # ---- AC12: pragmatist-voice for synthesis -------------------------------

    def test_pragmatist_voice_mentioned(self) -> None:
        """AC12: Body must describe invoking pragmatist-voice for synthesis."""
        body = self._body()
        assert (
            "pragmatist-voice" in body
            or re.search(r"pragmatist.{0,10}voice", body, re.IGNORECASE)
        ), (
            "Body must describe invoking pragmatist-voice (AC12)"
        )

    def test_pragmatist_voice_for_synthesis(self) -> None:
        """AC12: pragmatist-voice must be associated with synthesis role."""
        body = self._body()
        has_pragmatist = "pragmatist" in body.lower()
        has_synthesis = bool(re.search(r"synthes", body, re.IGNORECASE))
        assert has_pragmatist, (
            "Body must mention pragmatist-voice (AC12)"
        )
        assert has_synthesis, (
            "Body must mention synthesis (AC12)"
        )


# ---------------------------------------------------------------------------
# Class 5: Context economy and read discipline
# ---------------------------------------------------------------------------


class TestFromAC_IdeatorContextEconomy:
    """AC13: Reads only summary files; never debates; context window discipline."""

    def _body(self) -> str:
        return _extract_body(_read_agent())

    def test_context_md_mentioned(self) -> None:
        """AC13: Body must reference context.md as a read target."""
        body = self._body()
        assert "context.md" in body, (
            "Body must reference context.md (AC13: reads only summary files)"
        )

    def test_decisions_md_mentioned(self) -> None:
        """AC13: Body must reference decisions.md as a read target."""
        body = self._body()
        assert "decisions.md" in body, (
            "Body must reference decisions.md (AC13: reads only summary files)"
        )

    def test_synthesis_md_mentioned(self) -> None:
        """AC13: Body must reference synthesis.md as a read target."""
        body = self._body()
        assert "synthesis.md" in body, (
            "Body must reference synthesis.md (AC13: reads only summary files)"
        )

    def test_reads_only_summary_files_not_debates(self) -> None:
        """AC13: Body must state that Mediator reads only summaries, never debates."""
        body = self._body()
        assert re.search(
            r"(only|never).{0,30}(summary|debate|deliberat|read.*raw)|"
            r"(summary|summaries).{0,30}(only|never.*raw)|"
            r"never.{0,30}(debate|deliberat|raw)|"
            r"context window.{0,30}(economy|discipline)",
            body,
            re.IGNORECASE,
        ), (
            "Body must state Mediator reads only summary files, never debates (AC13)"
        )


# ---------------------------------------------------------------------------
# Class 6: Write contract and handoff
# ---------------------------------------------------------------------------


class TestFromAC_IdeatorWriteAndHandoff:
    """AC14-AC15: context.md, decisions.md, brief.md writes; kanban handoff; planner."""

    def _body(self) -> str:
        return _extract_body(_read_agent())

    # ---- AC14: incremental writes -------------------------------------------

    def test_context_md_incremental_write_mentioned(self) -> None:
        """AC14: Body must describe writing context.md incrementally."""
        body = self._body()
        assert re.search(
            r"context\.md.{0,40}(incremental|updat|append|writ)|"
            r"(increment|updat|append).{0,30}context\.md",
            body,
            re.IGNORECASE,
        ), (
            "Body must describe writing context.md incrementally (AC14)"
        )

    def test_decisions_md_after_user_choices(self) -> None:
        """AC14: Body must link decisions.md writes to user choices."""
        body = self._body()
        assert re.search(
            r"decisions\.md.{0,40}(after|user.{0,15}choice|user.{0,15}select)|"
            r"(user.{0,15}choice|user.{0,15}select|decision).{0,40}decisions\.md",
            body,
            re.IGNORECASE,
        ), (
            "Body must state decisions.md is written after user choices (AC14)"
        )

    def test_brief_md_at_approval_mentioned(self) -> None:
        """AC14: Body must describe writing brief.md at approval."""
        body = self._body()
        assert re.search(
            r"brief\.md.{0,50}(approv|confirm|final)|"
            r"(approv|confirm|final).{0,50}brief\.md",
            body,
            re.IGNORECASE,
        ), (
            "Body must describe writing brief.md upon approval (AC14)"
        )

    # ---- AC15: kanban handoff and planner invocation ------------------------

    def test_handoff_creates_kanban_task(self) -> None:
        """AC15: Body must describe creating a kanban task as part of the handoff."""
        body = self._body()
        assert re.search(
            r"creat.{0,20}(kanban|task).{0,20}(brief|handoff|planner)|"
            r"(brief|handoff).{0,40}(kanban|task)|"
            r"create_task",
            body,
            re.IGNORECASE,
        ), (
            "Body must describe creating a kanban task as part of the Brief handoff (AC15)"
        )

    def test_planner_invoked_for_subtasks(self) -> None:
        """AC15: Body must describe invoking planner to decompose Brief into subtasks."""
        body = self._body()
        assert re.search(
            r"planner.{0,40}(subtask|decompos|task)|"
            r"(subtask|decompos).{0,30}planner",
            body,
            re.IGNORECASE,
        ), (
            "Body must describe invoking planner for subtask decomposition (AC15)"
        )

    def test_brief_content_in_kanban_task(self) -> None:
        """AC15: Body must state the kanban task contains the Brief content."""
        body = self._body()
        assert re.search(
            r"brief.{0,30}content|content.{0,30}brief|brief.{0,30}task.{0,30}bod",
            body,
            re.IGNORECASE,
        ), (
            "Body must state kanban task is created with Brief content (AC15)"
        )
