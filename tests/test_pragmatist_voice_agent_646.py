"""Tests for task #646: Create pragmatist-voice.agent.md (pure synthesis subagent).

Contract-level verification that share/agents/pragmatist-voice.agent.md exists with the
required frontmatter and body content per the AC and binding architecture refinements.

AC coverage:
  - AC1:  share/agents/pragmatist-voice.agent.md exists with valid YAML frontmatter
  - AC2:  user-invocable: false set
  - AC3:  model: Claude Opus 4.6 (copilot) configured (NOT GPT -- same family as other voices)
  - AC4:  Reads context.md, decisions.md, AND all voices/*.md results from Working Directory
  - AC5:  Writes synthesis.md (requires write tool; does NOT write any other files)
  - AC6:  Identifies convergences, disagreements, and produces recommendation with
          confidence score (0.0-1.0) per architecture refinement R5
  - AC7:  Flags disagreements with attribution; resolution is NOT done algorithmically --
          leaves resolution to the user
  - AC8:  Does NOT read debate logs, user conversation, raw research, or input files

Binding architecture refinements (adopted AC expansions):
  - R1:  disable-model-invocation: true (follows critic-voice pattern)
  - R2:  tools: [read/readFile, edit/createFile, search, vscode/memory] (exactly 4)
  - R3:  agents: [] (leaf subagent, no nesting)
  - R4:  argument-hint: "Synthesize: {working directory path}"
  - R5:  confidence score required in synthesis.md output contract
  - R6:  debate log exclusion encoded in persona + critical_rules sections
"""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
_AGENT_FILE = _REPO_ROOT / "share" / "agents" / "pragmatist-voice.agent.md"

_EXPECTED_TOOLS: frozenset[str] = frozenset(
    {"read/readFile", "edit/createFile", "search", "vscode/memory"}
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
    """Parse tools from YAML frontmatter (handles inline bracket syntax)."""
    match = re.search(r"^tools:\s*\[([^\]]*)\]", fm, re.MULTILINE)
    if not match:
        match = re.search(r"^tools:\s*\n\s*\[([^\]]*)\]", fm, re.MULTILINE)
    assert match is not None, (
        "tools: key not found or not in bracket syntax in frontmatter"
    )
    raw = match.group(1)
    return [t.strip().strip("'\"") for t in raw.split(",") if t.strip()]


class TestFromAC_PragmatistVoiceFrontmatter:
    """AC1-AC3, R1-R4: share/agents/pragmatist-voice.agent.md must exist with correct frontmatter."""

    # --- AC1: file exists with valid YAML frontmatter ---

    def test_file_exists(self) -> None:
        """AC1: pragmatist-voice.agent.md must exist on disk."""
        assert _AGENT_FILE.is_file(), (
            "share/agents/pragmatist-voice.agent.md does not exist -- builder must create it"
        )

    def test_has_valid_yaml_frontmatter(self) -> None:
        """AC1: File must start with --- ... --- YAML frontmatter block."""
        content = _read_agent()
        assert content.startswith("---\n"), (
            "pragmatist-voice.agent.md must begin with '---' YAML frontmatter"
        )
        fm = _extract_frontmatter(content)
        assert fm.strip() != "", "Frontmatter block is empty"

    # --- name (implied by file naming convention) ---

    def test_name_is_pragmatist_voice(self) -> None:
        """Implied: name field must match file stem 'pragmatist-voice'."""
        fm = _extract_frontmatter(_read_agent())
        match = re.search(r"^name:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "name: key not found in frontmatter"
        assert match.group(1).strip() == "pragmatist-voice", (
            f"name must be 'pragmatist-voice', got '{match.group(1).strip()}'"
        )

    # --- description (implied) ---

    def test_description_exists(self) -> None:
        """Implied: description: key must be present and non-empty."""
        fm = _extract_frontmatter(_read_agent())
        match = re.search(r"^description:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "description: key not found in frontmatter"
        assert match.group(1).strip() != "", "description: value is empty"

    def test_description_is_one_line(self) -> None:
        """Implied: description must be a single inline value (not multi-line)."""
        fm = _extract_frontmatter(_read_agent())
        match = re.search(r"^description:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "description: must be a one-line inline value"

    def test_description_mentions_synthesis_or_pragmatist(self) -> None:
        """Implied: description must convey synthesis or pragmatist role."""
        fm = _extract_frontmatter(_read_agent())
        match = re.search(r"^description:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "description: key not found in frontmatter"
        desc = match.group(1).strip().lower()
        assert any(kw in desc for kw in ("synthesis", "synthesize", "pragmatist", "convergence")), (
            f"description must mention 'synthesis', 'synthesize', 'pragmatist', or 'convergence', "
            f"got: '{desc}'"
        )

    # --- AC2: user-invocable: false ---

    def test_user_invocable_false(self) -> None:
        """AC2: user-invocable must be 'false'."""
        fm = _extract_frontmatter(_read_agent())
        match = re.search(r"^user-invocable:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "user-invocable: key not found in frontmatter"
        assert match.group(1).strip() == "false", (
            f"user-invocable must be 'false', got '{match.group(1).strip()}'"
        )

    # --- R1: disable-model-invocation: true ---

    def test_disable_model_invocation_true(self) -> None:
        """R1: disable-model-invocation must be 'true' (follows critic-voice pattern)."""
        fm = _extract_frontmatter(_read_agent())
        match = re.search(r"^disable-model-invocation:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "disable-model-invocation: key not found in frontmatter"
        assert match.group(1).strip() == "true", (
            f"disable-model-invocation must be 'true', got '{match.group(1).strip()}'"
        )

    # --- AC3: model: Claude Opus 4.6 (copilot) ---

    def test_model_contains_claude_opus(self) -> None:
        """AC3: model must reference Claude Opus 4.6 -- NOT GPT (all voices except Critic use Claude)."""
        fm = _extract_frontmatter(_read_agent())
        match = re.search(r"^model:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "model: key not found in frontmatter"
        model_val = match.group(1).strip()
        assert re.search(r"claude", model_val, re.IGNORECASE), (
            f"model must reference 'Claude' (Pragmatist uses Claude Opus 4.6 per spec s7), "
            f"got '{model_val}'"
        )
        assert re.search(r"opus", model_val, re.IGNORECASE), (
            f"model must reference 'Opus' (Claude Opus 4.6), got '{model_val}'"
        )

    def test_model_version_is_46(self) -> None:
        """AC3: model version must be 4.6 specifically."""
        fm = _extract_frontmatter(_read_agent())
        match = re.search(r"^model:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "model: key not found in frontmatter"
        model_val = match.group(1).strip()
        assert re.search(r"4\.6", model_val), (
            f"model version must be '4.6' (Claude Opus 4.6), got '{model_val}'"
        )

    def test_model_is_copilot_provider(self) -> None:
        """AC3: model must specify the copilot provider."""
        fm = _extract_frontmatter(_read_agent())
        match = re.search(r"^model:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "model: key not found in frontmatter"
        assert "copilot" in match.group(1).strip().lower(), (
            f"model must specify '(copilot)' provider, got '{match.group(1).strip()}'"
        )

    def test_model_is_single_string_not_array(self) -> None:
        """AC3: model must be a single string (not a fallback array)."""
        fm = _extract_frontmatter(_read_agent())
        match = re.search(r"^model:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "model: key not found in frontmatter"
        model_val = match.group(1).strip()
        assert not model_val.startswith("["), (
            f"model must be a single string, not a fallback array -- got '{model_val}'"
        )

    def test_model_is_not_gpt_family(self) -> None:
        """AC3: model must NOT be GPT -- only critic-voice uses GPT for model diversity."""
        fm = _extract_frontmatter(_read_agent())
        match = re.search(r"^model:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "model: key not found in frontmatter"
        model_val = match.group(1).strip().lower()
        assert "gpt" not in model_val, (
            "model must not be GPT family -- Pragmatist uses Claude Opus 4.6 per spec s7; "
            "only Critic uses GPT for model diversity"
        )

    # --- R2: tools (exactly 4: read/readFile, edit/createFile, search, vscode/memory) ---

    def test_tools_key_exists(self) -> None:
        """R2: tools: key must be present in frontmatter."""
        fm = _extract_frontmatter(_read_agent())
        assert re.search(r"^tools:", fm, re.MULTILINE), (
            "tools: key not found in frontmatter"
        )

    def test_tools_exactly_four(self) -> None:
        """R2: tools list must contain exactly 4 entries."""
        fm = _extract_frontmatter(_read_agent())
        tools = _extract_tools_from_frontmatter(fm)
        assert len(tools) == 4, (
            f"Expected exactly 4 tools, got {len(tools)}: {tools}"
        )

    def test_tools_are_correct_set(self) -> None:
        """R2: tools must be exactly: read/readFile, edit/createFile, search, vscode/memory."""
        fm = _extract_frontmatter(_read_agent())
        tools = frozenset(_extract_tools_from_frontmatter(fm))
        assert tools == _EXPECTED_TOOLS, (
            f"Tools mismatch.\n"
            f"  Expected: {sorted(_EXPECTED_TOOLS)}\n"
            f"  Got:      {sorted(tools)}\n"
            f"  Missing:  {sorted(_EXPECTED_TOOLS - tools)}\n"
            f"  Extra:    {sorted(tools - _EXPECTED_TOOLS)}"
        )

    def test_has_create_file_tool_for_synthesis_write(self) -> None:
        """R2/AC5: edit/createFile tool required -- Pragmatist writes synthesis.md."""
        fm = _extract_frontmatter(_read_agent())
        tools = _extract_tools_from_frontmatter(fm)
        assert "edit/createFile" in tools, (
            "edit/createFile tool must be present -- Pragmatist writes synthesis.md (AC5)"
        )

    def test_no_execute_tools(self) -> None:
        """R2: no execute/* tools -- Pragmatist does not run commands."""
        fm = _extract_frontmatter(_read_agent())
        tools = _extract_tools_from_frontmatter(fm)
        found = [t for t in tools if t.startswith("execute/")]
        assert found == [], f"Forbidden execute/* tools found: {found}"

    def test_no_kanban_mcp_tools(self) -> None:
        """R2: no owlbear-kanban/* tools -- Pragmatist does not touch the kanban board."""
        fm = _extract_frontmatter(_read_agent())
        tools = _extract_tools_from_frontmatter(fm)
        found = [t for t in tools if "kanban" in t.lower()]
        assert found == [], f"Forbidden kanban MCP tools found: {found}"

    def test_no_edit_files_tool(self) -> None:
        """R2: edit/editFiles must NOT be present (only edit/createFile allowed for loop-back safety)."""
        fm = _extract_frontmatter(_read_agent())
        tools = _extract_tools_from_frontmatter(fm)
        assert "edit/editFiles" not in tools, (
            "edit/editFiles must not be present -- Mediator clears Working Dir before "
            "re-invocation (spec s12 Phase 5); only edit/createFile is needed"
        )

    # --- R3: agents: [] ---

    def test_agents_is_empty_list(self) -> None:
        """R3: agents must be empty list [] -- leaf subagent, does not invoke other agents."""
        fm = _extract_frontmatter(_read_agent())
        match = re.search(r"^agents:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "agents: key not found in frontmatter"
        assert match.group(1).strip() == "[]", (
            f"agents must be '[]' (leaf subagent), got '{match.group(1).strip()}'"
        )

    # --- R4: argument-hint ---

    def test_argument_hint_exists(self) -> None:
        """R4: argument-hint: key must be present in frontmatter."""
        fm = _extract_frontmatter(_read_agent())
        assert re.search(r"^argument-hint:", fm, re.MULTILINE), (
            "argument-hint: key not found in frontmatter"
        )

    def test_argument_hint_starts_with_synthesize(self) -> None:
        """R4: argument-hint must begin with 'Synthesize' per h-agent-structure standard."""
        fm = _extract_frontmatter(_read_agent())
        hint_match = re.search(r"^argument-hint:\s*(.+)$", fm, re.MULTILINE)
        assert hint_match is not None, "argument-hint: value not found"
        hint = hint_match.group(1).strip()
        assert hint.lower().startswith("synthesize"), (
            f"argument-hint must start with 'Synthesize' -- "
            f"R4: 'Synthesize: {{working directory path}}', got: '{hint}'"
        )

    def test_argument_hint_references_working_directory(self) -> None:
        """R4: argument-hint must reference a working directory path placeholder."""
        fm = _extract_frontmatter(_read_agent())
        hint_match = re.search(r"^argument-hint:\s*(.+)$", fm, re.MULTILINE)
        assert hint_match is not None, "argument-hint: value not found"
        hint = hint_match.group(1).strip().lower()
        assert "working" in hint or "dir" in hint or "path" in hint, (
            f"argument-hint must reference a working directory path -- "
            f"R4: 'Synthesize: {{working directory path}}', got: '{hint_match.group(1).strip()}'"
        )


class TestFromAC_PragmatistVoiceInputContract:
    """AC4: Reads context.md, decisions.md, AND all voices/*.md from Working Directory."""

    def _body(self) -> str:
        return _extract_body(_read_agent())

    def test_context_md_referenced_in_body(self) -> None:
        """AC4: Body must instruct reading context.md from Working Directory."""
        body = self._body()
        assert "context.md" in body, (
            "Body must reference 'context.md' -- "
            "AC4: Pragmatist reads context.md from Working Directory"
        )

    def test_decisions_md_referenced_in_body(self) -> None:
        """AC4: Body must instruct reading decisions.md from Working Directory."""
        body = self._body()
        assert "decisions.md" in body, (
            "Body must reference 'decisions.md' -- "
            "AC4: Pragmatist reads decisions.md from Working Directory"
        )

    def test_voices_directory_or_pattern_referenced(self) -> None:
        """AC4: Body must reference reading all voices/*.md results."""
        body = self._body()
        assert re.search(r"voices/|\*.md|voices \*|all voices", body, re.IGNORECASE), (
            "Body must reference reading all voices/*.md results -- "
            "AC4: 'Reads: context.md, decisions.md, ALL voices/*.md results'"
        )

    def test_working_directory_referenced_in_body(self) -> None:
        """AC4: Body must reference 'Working Directory' as the source of input files."""
        body = self._body()
        assert re.search(r"working dir", body, re.IGNORECASE), (
            "Body must mention 'Working Directory' as source of input files -- "
            "AC4 context: Pragmatist invoked post-deliberation with Working Dir path"
        )

    def test_reads_all_voices_not_selective(self) -> None:
        """AC4: Body must convey reading ALL voice results (not selective subset)."""
        body = self._body()
        assert re.search(
            r"\ball\b.{0,30}voice|\ball voices\b|voices.{0,10}\ball\b",
            body,
            re.IGNORECASE,
        ), (
            "Body must convey reading ALL voice results (not a selective subset) -- "
            "AC4: 'ALL voices/*.md results'"
        )


class TestFromAC_PragmatistVoiceSynthesisOutput:
    """AC5-AC7: Writes synthesis.md; identifies convergences/disagreements; flags attribution."""

    def _body(self) -> str:
        return _extract_body(_read_agent())

    # --- AC5: Writes synthesis.md ---

    def test_synthesis_md_output_referenced(self) -> None:
        """AC5: Body must reference writing synthesis.md."""
        body = self._body()
        assert "synthesis.md" in body, (
            "Body must reference 'synthesis.md' as the output file -- "
            "AC5: 'Writes: synthesis.md'"
        )

    def test_synthesis_write_intent_present(self) -> None:
        """AC5: Body must describe writing or creating synthesis.md (not just reading it)."""
        body = self._body()
        assert re.search(r"writ|creat|output|publish", body, re.IGNORECASE), (
            "Body must describe writing/creating an output file -- "
            "AC5: Pragmatist writes synthesis.md"
        )

    # --- AC6: Identifies convergences, disagreements, produces recommendation ---

    def test_convergences_mentioned_in_body(self) -> None:
        """AC6: Body must reference 'convergence' or 'agreement' found across voices."""
        body = self._body()
        assert re.search(r"converge|agreement|align|shared", body, re.IGNORECASE), (
            "Body must mention convergences (areas of agreement across voices) -- "
            "AC6: 'Identifies convergences, disagreements'"
        )

    def test_disagreements_mentioned_in_body(self) -> None:
        """AC6: Body must reference 'disagreement', 'tension', or 'conflict' between voices."""
        body = self._body()
        assert re.search(r"disagree|tension|conflict|diverge", body, re.IGNORECASE), (
            "Body must mention disagreements between voices -- "
            "AC6: 'Identifies convergences, disagreements'"
        )

    def test_recommendation_mentioned_in_body(self) -> None:
        """AC6: Body must instruct producing a recommendation."""
        body = self._body()
        assert re.search(r"recommend", body, re.IGNORECASE), (
            "Body must describe producing a recommendation -- "
            "AC6: 'produces recommendation'"
        )

    def test_confidence_score_required_in_output(self) -> None:
        """AC6 / R5: Recommendation must include a confidence score (0.0-1.0) in synthesis output."""
        body = self._body()
        assert re.search(
            r"confidence.{0,30}(score|0\.0|1\.0|float|0-1)|"
            r"(0\.0.{0,10}1\.0).{0,30}confidence",
            body,
            re.IGNORECASE,
        ), (
            "Synthesis output contract must require a confidence score (0.0-1.0) -- "
            "R5: 'recommendation must include confidence score (0.0-1.0)'"
        )

    # --- AC7: Flags disagreements with attribution; NOT resolved algorithmically ---

    def test_attribution_mentioned_in_body(self) -> None:
        """AC7: Body must describe flagging disagreements with attribution (which voice disagreed)."""
        body = self._body()
        assert re.search(r"attribution|attribute|which voice|source voice|named", body, re.IGNORECASE), (
            "Body must reference attribution for disagreements -- "
            "AC7: 'Flags disagreements with attribution'"
        )

    def test_no_algorithmic_resolution_defers_to_user(self) -> None:
        """AC7: Body must NOT claim Pragmatist resolves disagreements; resolution is user's job."""
        body = self._body()
        assert re.search(
            r"user.{0,30}(resolv|decid|choos)|"
            r"not.{0,20}resolv|do not resolv|never resolv|"
            r"resolution.{0,30}user|leave.{0,20}(to user|for user)",
            body,
            re.IGNORECASE,
        ), (
            "Body must state that disagreement resolution is the user's job, not Pragmatist's -- "
            "AC7: 'NOT resolved algorithmically -- resolution is user's job'"
        )

    def test_persona_section_exists(self) -> None:
        """AC7 / R6: Body must contain a <persona> section encoding the synthesis role."""
        body = self._body()
        assert "<persona>" in body, (
            "Body must contain a <persona> opening tag -- "
            "R6: debate log exclusion encoded in persona + critical_rules"
        )
        assert "</persona>" in body, (
            "Body must contain a </persona> closing tag -- "
            "R6: debate log exclusion encoded in persona + critical_rules"
        )


class TestFromAC_PragmatistVoiceExclusions:
    """AC8 / R6: Pragmatist must NOT read debate logs, user conversation, raw research, input files."""

    def _body(self) -> str:
        return _extract_body(_read_agent())

    def test_debate_logs_excluded_in_body(self) -> None:
        """AC8 / R6: Body must explicitly prohibit reading debate logs."""
        body = self._body()
        assert re.search(
            r"not.{0,30}(debate|debate log)|"
            r"(debate|debate log).{0,30}(not|never|exclude|prohibit|do not)|"
            r"no.{0,10}debate",
            body,
            re.IGNORECASE,
        ), (
            "Body must explicitly exclude debate logs from reads -- "
            "AC8: 'Does NOT read debate logs'; R6: encode in persona + critical_rules"
        )

    def test_raw_research_excluded_in_body(self) -> None:
        """AC8: Body must explicitly prohibit reading raw research files."""
        body = self._body()
        assert re.search(
            r"not.{0,30}(raw research|research doc|input file)|"
            r"(raw research|research doc).{0,30}(not|never|exclude)|"
            r"no.{0,10}(raw|research)",
            body,
            re.IGNORECASE,
        ), (
            "Body must explicitly exclude raw research from reads -- "
            "AC8: 'Does NOT read ... raw research'"
        )

    def test_input_files_excluded_in_body(self) -> None:
        """AC8: Body must explicitly prohibit reading user input files."""
        body = self._body()
        assert re.search(
            r"not.{0,30}input.{0,20}file|"
            r"input.{0,20}file.{0,30}(not|never|exclude)|"
            r"no.{0,10}input file",
            body,
            re.IGNORECASE,
        ), (
            "Body must explicitly exclude input files from reads -- "
            "AC8: 'Does NOT read ... input files'"
        )

    def test_critical_rules_section_exists(self) -> None:
        """R6: Body must contain a <critical_rules> section to formally encode exclusions."""
        body = self._body()
        assert "<critical_rules>" in body, (
            "Body must contain a <critical_rules> section -- "
            "R6: debate log exclusion encoded in persona + critical_rules"
        )

    def test_reads_only_permitted_summary_files(self) -> None:
        """AC8: Body must constrain reads to context.md, decisions.md, and voices/*.md only."""
        body = self._body()
        assert re.search(
            r"context\.md.{0,40}decisions\.md|decisions\.md.{0,40}context\.md",
            body,
            re.IGNORECASE,
        ), (
            "Body must describe the constrained read set (context.md + decisions.md + voices) "
            "rather than unconstrained file access -- "
            "AC8: only summary files allowed; debate logs, raw research, inputs forbidden"
        )
