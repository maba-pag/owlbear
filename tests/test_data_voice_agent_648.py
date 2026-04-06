"""Tests for task #648: Create data-voice.agent.md (data quality domain voice).

Contract-level verification that share/agents/data-voice.agent.md exists with the
required frontmatter and body content per the AC and Architecture Review refinements.

AC coverage:
  - AC1:  share/agents/data-voice.agent.md exists with valid YAML frontmatter
  - AC2:  user-invocable: false
  - AC3:  model: Claude Opus 4.6 (copilot) configured
  - AC4:  Domain: data quality, validation, flows, schemas, ETL, analytics
  - AC5:  Reads: context.md, decisions.md, optionally research-notes.md
  - AC6:  Writes: voices/data-person.md, voices/data-person-debate.md
  - AC7:  Embedded Critic loop (same pattern as architect-voice)
  - AC8:  agents: [critic-voice] — sole subagent (Architecture Review tightening)
  Architecture Review AC additions (binding):
  - NewAC1: disable-model-invocation: true
  - NewAC2: tools: exactly 8 — [edit/createDirectory, edit/createFile, edit/editFiles,
            read/readFile, read/viewImage, search, vscode/memory, agent]
  - NewAC3: argument-hint: "Data: {problem and outcome context for data quality analysis}"
"""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
_AGENT_FILE = _REPO_ROOT / "share" / "agents" / "data-voice.agent.md"

_EXPECTED_TOOLS: frozenset[str] = frozenset(
    {
        "edit/createDirectory",
        "edit/createFile",
        "edit/editFiles",
        "read/readFile",
        "read/viewImage",
        "search",
        "vscode/memory",
        "agent",
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
    """Parse tools from YAML frontmatter (handles inline bracket syntax)."""
    match = re.search(r"^tools:\s*\[([^\]]*)\]", fm, re.MULTILINE)
    if not match:
        match = re.search(r"^tools:\s*\n\s*\[([^\]]*)\]", fm, re.MULTILINE)
    assert match is not None, (
        "tools: key not found or not in bracket syntax in frontmatter"
    )
    raw = match.group(1)
    return [t.strip().strip("'\"") for t in raw.split(",") if t.strip()]


class TestFromAC_DataVoiceFrontmatter:
    """AC1-AC3, NewAC1-NewAC3, AC8: share/agents/data-voice.agent.md must exist with correct frontmatter."""

    # --- AC1: file exists with valid YAML frontmatter ---

    def test_file_exists(self) -> None:
        """AC1: data-voice.agent.md must exist on disk."""
        assert _AGENT_FILE.is_file(), (
            "share/agents/data-voice.agent.md does not exist -- builder must create it"
        )

    def test_has_valid_yaml_frontmatter(self) -> None:
        """AC1: File must start with --- ... --- YAML frontmatter block."""
        content = _read_agent()
        assert content.startswith("---\n"), (
            "data-voice.agent.md must begin with '---' YAML frontmatter"
        )
        fm = _extract_frontmatter(content)
        assert fm.strip() != "", "Frontmatter block is empty"

    # --- name (implied by file naming convention) ---

    def test_name_is_data_voice(self) -> None:
        """Implied: name field must match file stem 'data-voice'."""
        fm = _extract_frontmatter(_read_agent())
        match = re.search(r"^name:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "name: key not found in frontmatter"
        assert match.group(1).strip() == "data-voice", (
            f"name must be 'data-voice', got '{match.group(1).strip()}'"
        )

    # --- description (implied) ---

    def test_description_exists(self) -> None:
        """Implied: description: key must be present and non-empty."""
        fm = _extract_frontmatter(_read_agent())
        match = re.search(r"^description:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "description: key not found in frontmatter"
        assert match.group(1).strip() != "", "description: value is empty"

    def test_description_mentions_data_domain(self) -> None:
        """Implied: description must reference data quality, validation, or schema domain."""
        fm = _extract_frontmatter(_read_agent())
        match = re.search(r"^description:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "description: key must be present"
        desc = match.group(1).strip().lower()
        assert any(
            kw in desc
            for kw in ("data", "schema", "validation", "etl", "analytics", "quality")
        ), (
            f"description must mention data domain (data/schema/validation/etl/analytics/quality), "
            f"got: '{match.group(1).strip()}'"
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

    # --- NewAC1: disable-model-invocation: true ---

    def test_disable_model_invocation_true(self) -> None:
        """NewAC1: disable-model-invocation must be 'true' (standard for non-user-invocable voice agents)."""
        fm = _extract_frontmatter(_read_agent())
        match = re.search(r"^disable-model-invocation:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "disable-model-invocation: key not found in frontmatter"
        assert match.group(1).strip() == "true", (
            f"disable-model-invocation must be 'true', got '{match.group(1).strip()}'"
        )

    # --- AC3: model: Claude Opus 4.6 (copilot) ---

    def test_model_is_claude_opus_46(self) -> None:
        """AC3: model must reference Claude Opus 4.6."""
        fm = _extract_frontmatter(_read_agent())
        match = re.search(r"^model:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "model: key not found in frontmatter"
        model_val = match.group(1).strip()
        assert re.search(r"claude", model_val, re.IGNORECASE), (
            f"model must reference 'Claude', got '{model_val}'"
        )
        assert re.search(r"opus", model_val, re.IGNORECASE), (
            f"model must reference 'Opus', got '{model_val}'"
        )
        assert re.search(r"4\.6", model_val), (
            f"model must reference version '4.6', got '{model_val}'"
        )

    def test_model_is_single_string_not_array(self) -> None:
        """AC3: model must be a single string (not a fallback array)."""
        fm = _extract_frontmatter(_read_agent())
        match = re.search(r"^model:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "model: key not found in frontmatter"
        assert not match.group(1).strip().startswith("["), (
            f"model must be a single string, not a fallback array, got '{match.group(1).strip()}'"
        )

    def test_model_is_copilot_provider(self) -> None:
        """AC3: model must specify the copilot provider."""
        fm = _extract_frontmatter(_read_agent())
        match = re.search(r"^model:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "model: key not found in frontmatter"
        assert "copilot" in match.group(1).strip().lower(), (
            f"model must specify '(copilot)' provider, got '{match.group(1).strip()}'"
        )

    # --- NewAC2: tools (exact 8-tool set) ---

    def test_tools_key_exists(self) -> None:
        """NewAC2: tools: key must be present in frontmatter."""
        fm = _extract_frontmatter(_read_agent())
        assert re.search(r"^tools:", fm, re.MULTILINE), (
            "tools: key not found in frontmatter"
        )

    def test_tools_exactly_eight(self) -> None:
        """NewAC2: tools list must contain exactly 8 entries."""
        fm = _extract_frontmatter(_read_agent())
        tools = _extract_tools_from_frontmatter(fm)
        assert len(tools) == 8, (
            f"Expected exactly 8 tools, got {len(tools)}: {tools}"
        )

    def test_tools_are_correct_set(self) -> None:
        """NewAC2: tools must be exactly the 8-tool set matching architect-voice pattern."""
        fm = _extract_frontmatter(_read_agent())
        tools = frozenset(_extract_tools_from_frontmatter(fm))
        assert tools == _EXPECTED_TOOLS, (
            f"Tools mismatch.\n"
            f"  Expected: {sorted(_EXPECTED_TOOLS)}\n"
            f"  Got:      {sorted(tools)}\n"
            f"  Missing:  {sorted(_EXPECTED_TOOLS - tools)}\n"
            f"  Extra:    {sorted(tools - _EXPECTED_TOOLS)}"
        )

    def test_no_vscode_ask_questions_tool(self) -> None:
        """Cross-cutting: vscode/askQuestions is forbidden in non-user-invocable agents (#123)."""
        fm = _extract_frontmatter(_read_agent())
        tools = _extract_tools_from_frontmatter(fm)
        assert "vscode/askQuestions" not in tools, (
            "vscode/askQuestions is forbidden -- blanket ban enforced by #123 "
            "for non-user-invocable agents"
        )

    def test_includes_agent_tool(self) -> None:
        """NewAC2: 'agent' tool must be present to support critic-voice subagent invocation."""
        fm = _extract_frontmatter(_read_agent())
        tools = _extract_tools_from_frontmatter(fm)
        assert "agent" in tools, (
            "tools must include 'agent' to allow critic-voice subagent invocation"
        )

    def test_includes_edit_tools(self) -> None:
        """NewAC2: edit/* tools must be present to write voice output files."""
        fm = _extract_frontmatter(_read_agent())
        tools = _extract_tools_from_frontmatter(fm)
        edit_tools = [t for t in tools if t.startswith("edit/")]
        assert len(edit_tools) >= 1, (
            "At least one edit/* tool required to write voices/data-person*.md output files"
        )

    # --- AC8 tightened: agents: [critic-voice] ---

    def test_agents_key_exists(self) -> None:
        """AC8: agents: key must be present in frontmatter."""
        fm = _extract_frontmatter(_read_agent())
        assert re.search(r"^agents:", fm, re.MULTILINE), (
            "agents: key not found in frontmatter"
        )

    def test_agents_contains_critic_voice(self) -> None:
        """AC8: agents must include 'critic-voice'."""
        fm = _extract_frontmatter(_read_agent())
        match = re.search(r"^agents:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "agents: key not found in frontmatter"
        assert "critic-voice" in match.group(1), (
            f"agents must contain 'critic-voice', got '{match.group(1).strip()}'"
        )

    def test_agents_is_only_critic_voice(self) -> None:
        """AC8 tightened: agents must be exactly [critic-voice] — sole subagent."""
        fm = _extract_frontmatter(_read_agent())
        match = re.search(r"^agents:\s*\[([^\]]*)\]", fm, re.MULTILINE)
        assert match is not None, "agents: key not found or not in bracket syntax"
        raw = match.group(1)
        entries = [e.strip().strip("'\"") for e in raw.split(",") if e.strip()]
        assert entries == ["critic-voice"], (
            f"agents must be exactly ['critic-voice'] (sole subagent), got {entries}"
        )

    # --- NewAC3: argument-hint ---

    def test_argument_hint_exists(self) -> None:
        """NewAC3: argument-hint: key must be present."""
        fm = _extract_frontmatter(_read_agent())
        assert re.search(r"^argument-hint:", fm, re.MULTILINE), (
            "argument-hint: key not found in frontmatter"
        )

    def test_argument_hint_starts_with_data(self) -> None:
        """NewAC3: argument-hint must start with 'Data:' per h-agent-structure naming convention."""
        fm = _extract_frontmatter(_read_agent())
        match = re.search(r"^argument-hint:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "argument-hint: value not found"
        hint = match.group(1).strip().strip("\"'")
        assert hint.startswith("Data:"), (
            f"argument-hint must start with 'Data:', got: '{hint}'"
        )

    def test_argument_hint_mentions_data_quality_context(self) -> None:
        """NewAC3: argument-hint must reference data quality, problem, or context for invocation guidance."""
        fm = _extract_frontmatter(_read_agent())
        match = re.search(r"^argument-hint:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "argument-hint: value not found"
        hint = match.group(1).strip().lower()
        assert any(kw in hint for kw in ("data", "quality", "context", "problem")), (
            f"argument-hint must reference data quality/context, got: '{match.group(1).strip()}'"
        )


class TestFromAC_DataVoicePersonaAndDomain:
    """AC4: Domain persona must express strong data quality, validation, ETL, schema opinions."""

    def _body(self) -> str:
        return _extract_body(_read_agent())

    # --- AC4: domain coverage ---

    def test_persona_section_exists(self) -> None:
        """AC4: body must contain a <persona> XML tag section."""
        body = self._body()
        assert "<persona>" in body, "Body must contain a <persona> section"

    def test_persona_closing_tag_exists(self) -> None:
        """AC4: persona section must be properly closed."""
        body = self._body()
        assert "</persona>" in body, "Body must contain a closing </persona> tag"

    def test_persona_mentions_schema(self) -> None:
        """AC4: persona must reference 'schema' as a core data domain concern."""
        body = self._body()
        persona_match = re.search(r"<persona>(.*?)</persona>", body, re.DOTALL)
        assert persona_match is not None, "<persona>...</persona> block not found"
        persona = persona_match.group(1).lower()
        assert "schema" in persona, (
            "Persona must mention 'schema' -- AC4 domain includes schemas; "
            "spec §7: 'Schema is the contract.'"
        )

    def test_persona_mentions_validation(self) -> None:
        """AC4: persona must reference validation as a domain concern."""
        body = self._body()
        assert re.search(r"validat", body, re.IGNORECASE), (
            "Body must mention validation -- AC4: domain includes 'validation'"
        )

    def test_persona_mentions_data_quality_or_integrity(self) -> None:
        """AC4: persona must reference data quality or data integrity."""
        body = self._body()
        assert re.search(r"data quality|data integrity|quality", body, re.IGNORECASE), (
            "Body must mention 'data quality' or 'data integrity' -- AC4 primary domain"
        )

    def test_persona_mentions_etl_or_pipeline(self) -> None:
        """AC4: persona must reference ETL or pipeline as domain concern."""
        body = self._body()
        assert re.search(r"\betl\b|pipeline|flow", body, re.IGNORECASE), (
            "Body must mention 'ETL', 'pipeline', or 'flow' -- AC4: domain includes ETL, flows"
        )

    def test_persona_has_strong_opinions(self) -> None:
        """AC4: persona must express strong, opinionated stance (matching spec §7 'NaN propagation' tone)."""
        body = self._body()
        persona_match = re.search(r"<persona>(.*?)</persona>", body, re.DOTALL)
        assert persona_match is not None, "<persona>...</persona> block not found"
        persona = persona_match.group(1)
        assert re.search(
            r"opinion|opinionated|strong|\"[A-Z]|must|enemy|contract|strict",
            persona,
            re.IGNORECASE,
        ), (
            "Persona must express strong, opinionated stances about data quality "
            "-- spec §7 tone: 'Schema is the contract. Validate between steps.'"
        )


class TestFromAC_DataVoiceIOContract:
    """AC5, AC6: Agent must specify correct read inputs and write outputs."""

    def _body(self) -> str:
        return _extract_body(_read_agent())

    # --- AC5: reads context.md, decisions.md, optionally research-notes.md ---

    def test_reads_context_md(self) -> None:
        """AC5: body must reference reading context.md."""
        body = self._body()
        assert "context.md" in body, (
            "Body must reference 'context.md' -- AC5: reads context.md from Working Directory"
        )

    def test_reads_decisions_md(self) -> None:
        """AC5: body must reference reading decisions.md."""
        body = self._body()
        assert "decisions.md" in body, (
            "Body must reference 'decisions.md' -- AC5: reads decisions.md from Working Directory"
        )

    def test_mentions_research_notes_md(self) -> None:
        """AC5: body must mention research-notes.md (as optional input)."""
        body = self._body()
        assert "research-notes.md" in body, (
            "Body must mention 'research-notes.md' -- AC5: optionally reads research-notes.md"
        )

    # --- AC6: writes voices/data-person.md, voices/data-person-debate.md ---

    def test_writes_data_person_md(self) -> None:
        """AC6: body must reference writing voices/data-person.md as output."""
        body = self._body()
        assert "data-person.md" in body, (
            "Body must reference 'data-person.md' -- "
            "AC6: writes voices/data-person.md (final position)"
        )

    def test_writes_data_person_debate_md(self) -> None:
        """AC6: body must reference writing voices/data-person-debate.md as output."""
        body = self._body()
        assert "data-person-debate.md" in body, (
            "Body must reference 'data-person-debate.md' -- "
            "AC6: writes voices/data-person-debate.md (Critic debate log)"
        )

    def test_output_paths_in_voices_directory(self) -> None:
        """AC6: output files must be placed in voices/ directory, not root Working Directory."""
        body = self._body()
        assert re.search(r"voices/data-person", body), (
            "Output file paths must be prefixed with 'voices/' -- "
            "AC6: writes to voices/data-person.md and voices/data-person-debate.md"
        )

    def test_debate_log_is_separate_from_final_position(self) -> None:
        """AC6: two distinct output files — final position (.md) and debate log (-debate.md)."""
        body = self._body()
        assert "data-person.md" in body, (
            "voices/data-person.md (final position) must be referenced in body"
        )
        assert "data-person-debate.md" in body, (
            "voices/data-person-debate.md (Critic debate log) must be referenced in body"
        )


class TestFromAC_DataVoiceCriticLoop:
    """AC7, AC8: Embedded Critic loop must follow the architect-voice pattern."""

    def _body(self) -> str:
        return _extract_body(_read_agent())

    # --- AC7: embedded Critic loop ---

    def test_critic_loop_section_or_cycle_mentioned(self) -> None:
        """AC7: body must describe a Critic loop or reasoning cycle."""
        body = self._body()
        assert re.search(
            r"critic.{0,30}loop|reasoning cycle|embedded.{0,30}critic|critic.{0,20}cycle",
            body,
            re.IGNORECASE,
        ), (
            "Body must describe an embedded Critic loop or reasoning cycle -- "
            "AC7: 'Embedded Critic loop (same pattern as architect-voice)'"
        )

    def test_critic_voice_invocation_mentioned_in_body(self) -> None:
        """AC7, AC8: body must reference invoking critic-voice."""
        body = self._body()
        assert "critic-voice" in body, (
            "Body must reference 'critic-voice' invocation -- "
            "AC7: Embedded Critic loop; AC8: agents list"
        )

    def test_voice_reasoning_cycle_section_exists(self) -> None:
        """AC7: body must contain a section describing the Voice Reasoning Cycle."""
        body = self._body()
        assert re.search(
            r"Voice Reasoning Cycle|Reasoning Cycle|reasoning cycle",
            body,
            re.IGNORECASE,
        ), (
            "Body must contain a 'Voice Reasoning Cycle' section -- "
            "AC7: architecture review specifies read context → form opinion → "
            "Critic loop → publish hardened position"
        )

    def test_critic_loop_max_cycles_bounded(self) -> None:
        """AC7: Critic loop must be bounded (≤5 cycles per Architecture Review guidance)."""
        body = self._body()
        assert re.search(
            r"[1-5]\s*cycle|≤\s*5|max.{0,10}[1-5]|up to\s+[1-5]|at most\s+[1-5]",
            body,
            re.IGNORECASE,
        ), (
            "Body must bound the Critic loop cycles (≤5) -- "
            "Architecture Review guidance: 'embedded Critic loop (≤5 cycles)'"
        )

    def test_publish_hardened_position(self) -> None:
        """AC7: cycle must end by publishing a hardened/final position to output files."""
        body = self._body()
        assert re.search(
            r"harden|final.{0,20}position|publish.{0,20}position|commit.{0,20}position|"
            r"position.{0,20}hardened|position.{0,20}final",
            body,
            re.IGNORECASE,
        ), (
            "Body must describe publishing a hardened position after the Critic loop -- "
            "AC7: Voice Reasoning Cycle ends with 'publish hardened position'"
        )
