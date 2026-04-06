"""Tests for task #650: Create security-voice.agent.md.

Contract-level verification that share/agents/security-voice.agent.md exists with the
required frontmatter and body content per the AC and binding Architecture Review
refinements.

AC coverage:
  - AC1:  share/agents/security-voice.agent.md exists with valid YAML frontmatter
  - AC2:  user-invocable: false
  - AC3:  model: Claude Opus 4.6 (copilot) configured
  - AC4:  Domain: access control, data safety, trust boundaries, compliance
  - AC5:  Reads: context.md, decisions.md, optionally research-notes.md
  - AC6:  Writes: voices/security.md, voices/security-debate.md
  - AC7:  Embedded Critic loop (same pattern as architect-voice)
  - AC8:  Agents list includes critic-voice
  Architecture Review AC additions (binding):
  - AC9:  disable-model-invocation: true set
  - AC10: Tool set exactly 8: [edit/createDirectory, edit/createFile, edit/editFiles,
          read/readFile, read/viewImage, search, vscode/memory, agent]
  - AC11: argument-hint field present — e.g. "Security: {problem and outcome context
          for security analysis}"
"""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
_AGENT_FILE = _REPO_ROOT / "share" / "agents" / "security-voice.agent.md"

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


class TestFromAC_SecurityVoiceFrontmatter:
    """AC1-AC3, AC9-AC11, AC8: share/agents/security-voice.agent.md must exist with correct frontmatter."""

    # ---- AC1: file exists with valid YAML frontmatter -----------------------

    def test_file_exists(self) -> None:
        """AC1: security-voice.agent.md must exist at share/agents/security-voice.agent.md."""
        assert _AGENT_FILE.is_file(), (
            "share/agents/security-voice.agent.md does not exist -- builder must create it"
        )

    def test_file_starts_with_frontmatter_delimiter(self) -> None:
        """AC1: File must begin with YAML frontmatter --- delimiter."""
        content = _read_agent()
        assert content.startswith("---\n"), (
            "security-voice.agent.md must begin with '---' to open YAML frontmatter"
        )

    def test_frontmatter_block_is_non_empty(self) -> None:
        """AC1: Frontmatter block between --- delimiters must not be empty."""
        fm = _extract_frontmatter(_read_agent())
        assert fm.strip() != "", "Frontmatter block is empty"

    def test_name_is_security_voice(self) -> None:
        """AC1: name field must match the file stem 'security-voice'."""
        fm = _extract_frontmatter(_read_agent())
        match = re.search(r"^name:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "name: key not found in frontmatter"
        assert match.group(1).strip() == "security-voice", (
            f"name must be 'security-voice', got '{match.group(1).strip()}'"
        )

    def test_description_exists_and_non_empty(self) -> None:
        """AC1: description: key must be present and non-empty."""
        fm = _extract_frontmatter(_read_agent())
        match = re.search(r"^description:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "description: key not found in frontmatter"
        assert match.group(1).strip() != "", "description: value is empty"

    def test_description_references_security_domain(self) -> None:
        """AC4: description must convey security/access-control/trust domain."""
        fm = _extract_frontmatter(_read_agent())
        match = re.search(r"^description:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "description: key not found in frontmatter"
        desc = match.group(1).strip().lower()
        assert any(
            kw in desc
            for kw in (
                "security",
                "access control",
                "trust",
                "compliance",
                "owasp",
                "safety",
                "data safety",
                "boundary",
            )
        ), (
            f"description must reference security domain "
            f"(security/access-control/trust/compliance), got: '{desc}'"
        )

    # ---- AC2: user-invocable: false -----------------------------------------

    def test_user_invocable_false(self) -> None:
        """AC2: user-invocable must be 'false' -- security-voice is a subagent-only voice."""
        fm = _extract_frontmatter(_read_agent())
        match = re.search(r"^user-invocable:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "user-invocable: key not found in frontmatter"
        assert match.group(1).strip() == "false", (
            f"user-invocable must be 'false', got '{match.group(1).strip()}'"
        )

    # ---- AC3: model: Claude Opus 4.6 (copilot) ------------------------------

    def test_model_contains_claude_opus_46(self) -> None:
        """AC3: model must specify Claude Opus 4.6."""
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

    def test_model_is_copilot_provider(self) -> None:
        """AC3: model must specify the (copilot) provider."""
        fm = _extract_frontmatter(_read_agent())
        match = re.search(r"^model:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "model: key not found in frontmatter"
        assert "copilot" in match.group(1).strip().lower(), (
            f"model must specify '(copilot)' provider, got '{match.group(1).strip()}'"
        )

    def test_model_is_single_string_not_array(self) -> None:
        """AC3: model must be a simple string, not a fallback array."""
        fm = _extract_frontmatter(_read_agent())
        match = re.search(r"^model:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "model: key not found in frontmatter"
        assert not match.group(1).strip().startswith("["), (
            f"model must be a single string, not a fallback array, got '{match.group(1).strip()}'"
        )

    def test_model_is_not_gpt_family(self) -> None:
        """AC3: model must NOT be GPT -- only critic-voice uses GPT for model diversity."""
        fm = _extract_frontmatter(_read_agent())
        match = re.search(r"^model:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "model: key not found in frontmatter"
        model_val = match.group(1).strip().lower()
        assert "gpt" not in model_val, (
            "model must not be GPT family -- security-voice uses Claude Opus 4.6; "
            "only critic-voice uses GPT for model diversity"
        )

    # ---- AC9: disable-model-invocation: true --------------------------------

    def test_disable_model_invocation_true(self) -> None:
        """AC9: disable-model-invocation must be 'true' -- standard for subagent-only voices."""
        fm = _extract_frontmatter(_read_agent())
        match = re.search(r"^disable-model-invocation:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "disable-model-invocation: key not found in frontmatter"
        assert match.group(1).strip() == "true", (
            f"disable-model-invocation must be 'true', got '{match.group(1).strip()}'"
        )

    # ---- AC10: tools: exactly 8 entries -------------------------------------

    def test_tools_key_exists(self) -> None:
        """AC10: tools: key must be present in frontmatter."""
        fm = _extract_frontmatter(_read_agent())
        assert re.search(r"^tools:", fm, re.MULTILINE), (
            "tools: key not found in frontmatter"
        )

    def test_tools_exactly_eight(self) -> None:
        """AC10: tools list must contain exactly 8 entries per Architecture Review binding."""
        fm = _extract_frontmatter(_read_agent())
        tools = _extract_tools_from_frontmatter(fm)
        assert len(tools) == 8, (
            f"Expected exactly 8 tools (per AC10 binding), got {len(tools)}: {tools}"
        )

    def test_tools_are_correct_set(self) -> None:
        """AC10: tools must be exactly the 8-tool architect-voice-mirrored set."""
        fm = _extract_frontmatter(_read_agent())
        tools = frozenset(_extract_tools_from_frontmatter(fm))
        assert tools == _EXPECTED_TOOLS, (
            f"Tools mismatch.\n"
            f"  Expected: {sorted(_EXPECTED_TOOLS)}\n"
            f"  Got:      {sorted(tools)}\n"
            f"  Missing:  {sorted(_EXPECTED_TOOLS - tools)}\n"
            f"  Extra:    {sorted(tools - _EXPECTED_TOOLS)}"
        )

    def test_tools_includes_agent_tool(self) -> None:
        """AC7/AC10: agent tool must be present to enable Critic loop invocation."""
        fm = _extract_frontmatter(_read_agent())
        tools = _extract_tools_from_frontmatter(fm)
        assert "agent" in tools, (
            "tools must include 'agent' to invoke critic-voice in the Critic loop (AC7/AC10)"
        )

    def test_tools_includes_write_tools(self) -> None:
        """AC6/AC10: edit/* write tools must be present to write voice output files."""
        fm = _extract_frontmatter(_read_agent())
        tools = _extract_tools_from_frontmatter(fm)
        write_tools = [t for t in tools if t.startswith("edit/")]
        assert write_tools, (
            "At least one edit/* tool must be present to write voices/security*.md output files (AC6)"
        )

    def test_no_execute_tools(self) -> None:
        """AC10: No execute/* tools -- security-voice is an analysis agent, not a pipeline executor."""
        fm = _extract_frontmatter(_read_agent())
        tools = _extract_tools_from_frontmatter(fm)
        found = [t for t in tools if t.startswith("execute/")]
        assert found == [], (
            f"Forbidden execute/* tools found: {found}. "
            "security-voice must not run terminal commands."
        )

    def test_no_kanban_tools(self) -> None:
        """AC10: No owlbear-kanban/* tools -- security-voice is a domain voice, not a pipeline agent."""
        fm = _extract_frontmatter(_read_agent())
        tools = _extract_tools_from_frontmatter(fm)
        found = [t for t in tools if "kanban" in t]
        assert found == [], (
            f"Forbidden kanban tools found: {found}. "
            "security-voice must not access kanban (domain voice, not pipeline agent)."
        )

    def test_no_vscode_ask_questions_tool(self) -> None:
        """Cross-cutting: vscode/askQuestions is forbidden in non-user-invocable agents."""
        fm = _extract_frontmatter(_read_agent())
        tools = _extract_tools_from_frontmatter(fm)
        assert "vscode/askQuestions" not in tools, (
            "vscode/askQuestions is forbidden in non-user-invocable agents (blanket ban)"
        )

    # ---- AC11: argument-hint field ------------------------------------------

    def test_argument_hint_exists(self) -> None:
        """AC11: argument-hint: key must be present in frontmatter."""
        fm = _extract_frontmatter(_read_agent())
        assert re.search(r"^argument-hint:", fm, re.MULTILINE), (
            "argument-hint: key not found in frontmatter (Architecture Review binding)"
        )

    def test_argument_hint_starts_with_security(self) -> None:
        """AC11: argument-hint must start with 'Security:' per h-agent-structure naming convention."""
        fm = _extract_frontmatter(_read_agent())
        hint_match = re.search(r"^argument-hint:\s*(.+)$", fm, re.MULTILINE)
        assert hint_match is not None, "argument-hint: value not found"
        hint = hint_match.group(1).strip().strip("\"'")
        assert hint.startswith("Security:"), (
            f"argument-hint must start with 'Security: ' -- "
            f"AC11: 'Security: {{problem and outcome context for security analysis}}', "
            f"got: '{hint}'"
        )

    def test_argument_hint_references_security_or_problem_context(self) -> None:
        """AC11: argument-hint must describe the security analysis invocation context."""
        fm = _extract_frontmatter(_read_agent())
        hint_match = re.search(r"^argument-hint:\s*(.+)$", fm, re.MULTILINE)
        assert hint_match is not None, "argument-hint: value not found"
        hint = hint_match.group(1).strip().lower()
        assert any(
            kw in hint
            for kw in ("security", "problem", "context", "outcome", "analysis")
        ), (
            f"argument-hint must describe security analysis context "
            f"(security/problem/context/outcome/analysis), "
            f"got: '{hint_match.group(1).strip()}'"
        )

    # ---- AC8: agents: includes critic-voice ---------------------------------

    def test_agents_key_exists(self) -> None:
        """AC8: agents: key must be present in frontmatter."""
        fm = _extract_frontmatter(_read_agent())
        assert re.search(r"^agents:", fm, re.MULTILINE), (
            "agents: key not found in frontmatter"
        )

    def test_agents_includes_critic_voice(self) -> None:
        """AC8: agents list must include 'critic-voice' for Critic loop invocation."""
        fm = _extract_frontmatter(_read_agent())
        agents = _extract_agents_from_frontmatter(fm)
        assert "critic-voice" in agents, (
            f"agents must include 'critic-voice' (AC8). Found: {agents}"
        )

    def test_agents_list_is_not_empty(self) -> None:
        """AC8: agents list must not be empty -- critic-voice is required."""
        fm = _extract_frontmatter(_read_agent())
        agents = _extract_agents_from_frontmatter(fm)
        assert len(agents) > 0, (
            "agents list must not be empty -- at minimum critic-voice must be present (AC8)"
        )


# ---------------------------------------------------------------------------
# Class 2: Domain, persona, and security practitioner role
# ---------------------------------------------------------------------------


class TestFromAC_SecurityVoiceDomainAndPersona:
    """AC4, AC5: Domain voice for security; persona must express access-control and trust boundary lens."""

    def _body(self) -> str:
        return _extract_body(_read_agent())

    # ---- AC4: Domain — access control, data safety, trust boundaries, compliance ----

    def test_persona_section_exists(self) -> None:
        """AC4: body must contain a <persona> XML tag section."""
        body = self._body()
        assert "<persona>" in body, "Body must contain a <persona> section"

    def test_persona_section_closed(self) -> None:
        """AC4: <persona> section must be properly closed with </persona>."""
        body = self._body()
        assert "</persona>" in body, "Body must contain a closing </persona> tag"

    def test_persona_references_security_practitioner_role(self) -> None:
        """AC4: Persona must frame the agent as a security or threat-modelling practitioner."""
        body = self._body()
        persona_match = re.search(r"<persona>(.*?)</persona>", body, re.DOTALL)
        assert persona_match is not None, "<persona>...</persona> block not found"
        persona = persona_match.group(1).lower()
        assert any(
            kw in persona
            for kw in (
                "security",
                "threat",
                "owasp",
                "attack",
                "trust",
                "access control",
                "adversar",
            )
        ), (
            "Persona must frame the agent as a security practitioner "
            "(security/threat/owasp/attack/trust/access control) (AC4)"
        )

    def test_body_mentions_access_control(self) -> None:
        """AC4: Body must reference access control as a core domain concern."""
        body = self._body()
        assert re.search(r"access.control|authorization|authz", body, re.IGNORECASE), (
            "Body must mention 'access control' or 'authorization' -- "
            "AC4 domain: access control, data safety, trust boundaries, compliance"
        )

    def test_body_mentions_data_safety_or_trust_boundaries(self) -> None:
        """AC4: Body must reference data safety or trust boundaries."""
        body = self._body()
        assert re.search(r"data.safety|trust.boundar|trust boundary|blast.radius", body, re.IGNORECASE), (
            "Body must mention 'data safety', 'trust boundary/boundaries', or 'blast radius' -- "
            "AC4 domain: data safety, trust boundaries"
        )

    def test_body_mentions_compliance(self) -> None:
        """AC4: Body must reference compliance as a domain concern."""
        body = self._body()
        assert re.search(r"complian", body, re.IGNORECASE), (
            "Body must mention 'compliance' -- AC4 domain includes compliance"
        )

    def test_body_mentions_owasp_or_least_privilege(self) -> None:
        """AC4/Context: Body must reference OWASP awareness or least-privilege principle."""
        body = self._body()
        assert re.search(r"owasp|least.privilege|defense.in.depth|least privilege", body, re.IGNORECASE), (
            "Body must mention 'OWASP', 'least privilege', or 'defense-in-depth' -- "
            "research doc: 'OWASP awareness, blast radius thinking, defense-in-depth, least privilege'"
        )

    # ---- AC5: Reads context.md, decisions.md, optionally research-notes.md ----

    def test_reads_context_md(self) -> None:
        """AC5: Body must reference reading context.md as an input."""
        body = self._body()
        assert "context.md" in body, (
            "Body must reference 'context.md' as an input file (AC5)"
        )

    def test_reads_decisions_md(self) -> None:
        """AC5: Body must reference reading decisions.md as an input."""
        body = self._body()
        assert "decisions.md" in body, (
            "Body must reference 'decisions.md' as an input file (AC5)"
        )

    def test_reads_research_notes_md(self) -> None:
        """AC5: Body must reference research-notes.md as an optional input."""
        body = self._body()
        assert "research-notes.md" in body, (
            "Body must reference 'research-notes.md' as an optional input file (AC5)"
        )


# ---------------------------------------------------------------------------
# Class 3: Output contract — writes voices/security.md and voices/security-debate.md
# ---------------------------------------------------------------------------


class TestFromAC_SecurityVoiceOutputContract:
    """AC6: Writes voices/security.md and voices/security-debate.md."""

    def _body(self) -> str:
        return _extract_body(_read_agent())

    def test_writes_security_md(self) -> None:
        """AC6: Body must reference writing voices/security.md as final position output."""
        body = self._body()
        assert re.search(r"voices/security\.md|security\.md", body, re.IGNORECASE), (
            "Body must reference 'voices/security.md' as the output file for final position (AC6)"
        )

    def test_writes_security_debate_md(self) -> None:
        """AC6: Body must reference writing voices/security-debate.md as Critic dialogue log."""
        body = self._body()
        assert re.search(r"security-debate\.md|security_debate\.md", body, re.IGNORECASE), (
            "Body must reference 'voices/security-debate.md' as the Critic dialogue log output (AC6)"
        )

    def test_both_output_files_referenced(self) -> None:
        """AC6: Both output files (security.md and security-debate.md) must be referenced."""
        body = self._body()
        assert re.search(r"voices/security\.md|security\.md", body, re.IGNORECASE), (
            "Body must reference voices/security.md as final position output (AC6)"
        )
        assert re.search(r"security-debate\.md|security_debate\.md", body, re.IGNORECASE), (
            "Body must reference voices/security-debate.md as Critic dialogue log (AC6)"
        )

    def test_output_implies_write_action(self) -> None:
        """AC6: Body must describe writing or creating the output files (not just listing them)."""
        body = self._body()
        assert re.search(r"writ|creat|output|publish|save", body, re.IGNORECASE), (
            "Body must describe writing/creating output -- AC6: security-voice writes two output files"
        )


# ---------------------------------------------------------------------------
# Class 4: Critic loop protocol
# ---------------------------------------------------------------------------


class TestFromAC_SecurityVoiceCriticLoop:
    """AC7: Embedded Critic loop — invokes critic-voice, up to 5 cycles, per spec S12."""

    def _body(self) -> str:
        return _extract_body(_read_agent())

    def test_critic_loop_section_or_reference_exists(self) -> None:
        """AC7: Body must describe or reference the Critic loop (Voice Reasoning Cycle)."""
        body = self._body()
        assert re.search(
            r"critic.{0,30}loop|voice reasoning cycle|reasoning cycle|critic loop",
            body,
            re.IGNORECASE,
        ), (
            "Body must describe the Critic loop or Voice Reasoning Cycle (AC7 / spec S12)"
        )

    def test_critic_loop_invokes_critic_voice(self) -> None:
        """AC7: Body must reference invoking critic-voice as part of the loop."""
        body = self._body()
        assert re.search(r"critic.voice", body, re.IGNORECASE), (
            "Body must reference 'critic-voice' as the subagent invoked in the Critic loop (AC7)"
        )

    def test_critic_loop_up_to_five_cycles(self) -> None:
        """AC7: Body must specify up to 5 cycles as the loop cap per spec S12."""
        body = self._body()
        assert re.search(
            r"\b5\b.*cycle|cycle.*\b5\b|five.{0,15}cycle|up to 5",
            body,
            re.IGNORECASE,
        ), (
            "Body must specify 'up to 5 cycles' as the Critic loop cap per spec S12 (AC7)"
        )

    def test_critic_loop_exit_condition_mentioned(self) -> None:
        """AC7: Body must state a loop exit condition (position solid or cycle cap)."""
        body = self._body()
        assert re.search(
            r"solid|cap|exit|no (more|further) challenge|position (is|accepted|confirmed)",
            body,
            re.IGNORECASE,
        ), (
            "Body must describe a Critic loop exit condition -- "
            "'position is solid' or cycle cap reached (AC7 / spec S12)"
        )

    def test_critic_loop_current_position_passed(self) -> None:
        """AC7: Body must describe passing the current position to critic-voice."""
        body = self._body()
        assert re.search(r"current position|position", body, re.IGNORECASE), (
            "Body must describe passing the current position to critic-voice in the loop (AC7)"
        )
