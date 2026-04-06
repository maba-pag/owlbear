"""Tests for task #644: Create critic-voice.agent.md (adversarial position challenger).

Contract-level verification that share/agents/critic-voice.agent.md exists with the
required frontmatter and body content per the AC.

AC coverage:
  - AC1:  share/agents/critic-voice.agent.md exists with valid YAML frontmatter
  - AC2:  user-invocable: false set
  - AC3:  model: GPT-5.4 (copilot) as sole model -- not a fallback array, genuine
          model diversity (different model family from all other voices)
  - AC4:  System prompt is purely adversarial: challenges positions, never proposes
          alternatives
  - AC5:  Prompt includes exit behavior: "If position is solid after honest
          examination, say so and exit. Do not manufacture objections."
  - AC6:  Agent receives voice's current position via prompt, reads context.md
          from Working Directory
  - AC7:  Returns adversarial challenges to the invoking voice -- no direct file
          writes; read-only tools only
  - AC8:  Designed for dual-scope invocation: argument-hint and prompt handle both
          standalone (Mediator) and embedded (domain voice) contexts from a single
          generic input; no scope-specific configuration or branching required
  - AC9:  disable-model-invocation: true set
  - AC10: tools: [read/readFile, read/viewImage, read/problems, search, vscode/memory]
  - AC11: agents: []
"""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
_AGENT_FILE = _REPO_ROOT / "share" / "agents" / "critic-voice.agent.md"

_EXPECTED_TOOLS: frozenset[str] = frozenset(
    {"read/readFile", "read/viewImage", "read/problems", "search", "vscode/memory"}
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


class TestFromAC_CriticVoiceFrontmatter:
    """AC1-AC3, AC9-AC11: share/agents/critic-voice.agent.md must exist with correct frontmatter."""

    # --- AC1: file exists with valid YAML frontmatter ---

    def test_file_exists(self) -> None:
        """AC1: critic-voice.agent.md must exist on disk."""
        assert _AGENT_FILE.is_file(), (
            "share/agents/critic-voice.agent.md does not exist -- builder must create it"
        )

    def test_has_valid_yaml_frontmatter(self) -> None:
        """AC1: File must start with --- ... --- YAML frontmatter block."""
        content = _read_agent()
        assert content.startswith("---\n"), (
            "critic-voice.agent.md must begin with '---' YAML frontmatter"
        )
        fm = _extract_frontmatter(content)
        assert fm.strip() != "", "Frontmatter block is empty"

    # --- name (implied by file naming convention) ---

    def test_name_is_critic_voice(self) -> None:
        """Implied: name field must match file stem 'critic-voice'."""
        fm = _extract_frontmatter(_read_agent())
        match = re.search(r"^name:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "name: key not found in frontmatter"
        assert match.group(1).strip() == "critic-voice", (
            f"name must be 'critic-voice', got '{match.group(1).strip()}'"
        )

    # --- description (implied) ---

    def test_description_exists(self) -> None:
        """Implied: description: key must be present and non-empty."""
        fm = _extract_frontmatter(_read_agent())
        match = re.search(r"^description:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "description: key not found in frontmatter"
        assert match.group(1).strip() != "", "description: value is empty"

    def test_description_is_one_line(self) -> None:
        """Implied: description must be a single inline value."""
        fm = _extract_frontmatter(_read_agent())
        match = re.search(r"^description:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "description: must be a one-line inline value"

    def test_description_mentions_adversarial_or_critic(self) -> None:
        """Implied: description must convey adversarial challenge or critic role."""
        fm = _extract_frontmatter(_read_agent())
        match = re.search(r"^description:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "description: key not found in frontmatter"
        desc = match.group(1).strip().lower()
        assert "adversarial" in desc or "challenge" in desc or "critic" in desc, (
            f"description must mention 'adversarial', 'challenge', or 'critic', got: '{desc}'"
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

    # --- AC9: disable-model-invocation: true ---

    def test_disable_model_invocation_true(self) -> None:
        """AC9: disable-model-invocation must be 'true'."""
        fm = _extract_frontmatter(_read_agent())
        match = re.search(r"^disable-model-invocation:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "disable-model-invocation: key not found in frontmatter"
        assert match.group(1).strip() == "true", (
            f"disable-model-invocation must be 'true', got '{match.group(1).strip()}'"
        )

    # --- AC3: model: GPT-5.4 (copilot) -- sole string, not array ---

    def test_model_contains_gpt54(self) -> None:
        """AC3: model must reference GPT-5.4 for genuine model diversity."""
        fm = _extract_frontmatter(_read_agent())
        match = re.search(r"^model:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "model: key not found in frontmatter"
        model_val = match.group(1).strip()
        assert re.search(r"gpt.?5\.4", model_val, re.IGNORECASE), (
            f"model must contain 'GPT-5.4' (genuine model diversity requirement), got '{model_val}'"
        )

    def test_model_is_single_string_not_array(self) -> None:
        """AC3: model must be a single string (not a fallback array like '[..., ...]')."""
        fm = _extract_frontmatter(_read_agent())
        match = re.search(r"^model:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "model: key not found in frontmatter"
        model_val = match.group(1).strip()
        assert not model_val.startswith("["), (
            f"model must be a single string, not a fallback array -- got '{model_val}'"
        )

    def test_model_is_copilot_provider(self) -> None:
        """AC3: model must specify the copilot provider."""
        fm = _extract_frontmatter(_read_agent())
        match = re.search(r"^model:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "model: key not found in frontmatter"
        assert "copilot" in match.group(1).strip().lower(), (
            f"model must specify '(copilot)' provider, got '{match.group(1).strip()}'"
        )

    def test_model_is_not_claude_or_opus(self) -> None:
        """AC3: model must NOT be Claude/Opus -- architectural requirement is GPT family."""
        fm = _extract_frontmatter(_read_agent())
        match = re.search(r"^model:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "model: key not found in frontmatter"
        model_val = match.group(1).strip().lower()
        assert "claude" not in model_val, (
            "model must not be Claude -- model diversity requires a different model family from other voices"
        )
        assert "opus" not in model_val, (
            "model must not reference Opus -- Opus is the model used by all other voices"
        )

    # --- AC10: tools ---

    def test_tools_key_exists(self) -> None:
        """AC10: tools: key must be present in frontmatter."""
        fm = _extract_frontmatter(_read_agent())
        assert re.search(r"^tools:", fm, re.MULTILINE), (
            "tools: key not found in frontmatter"
        )

    def test_tools_exactly_five(self) -> None:
        """AC10: tools list must contain exactly 5 entries."""
        fm = _extract_frontmatter(_read_agent())
        tools = _extract_tools_from_frontmatter(fm)
        assert len(tools) == 5, (
            f"Expected exactly 5 tools, got {len(tools)}: {tools}"
        )

    def test_tools_are_correct_set(self) -> None:
        """AC10: tools must be exactly: read/readFile, read/viewImage, read/problems, search, vscode/memory."""
        fm = _extract_frontmatter(_read_agent())
        tools = frozenset(_extract_tools_from_frontmatter(fm))
        assert tools == _EXPECTED_TOOLS, (
            f"Tools mismatch.\n"
            f"  Expected: {sorted(_EXPECTED_TOOLS)}\n"
            f"  Got:      {sorted(tools)}\n"
            f"  Missing:  {sorted(_EXPECTED_TOOLS - tools)}\n"
            f"  Extra:    {sorted(tools - _EXPECTED_TOOLS)}"
        )

    def test_no_execute_tools(self) -> None:
        """AC7/AC10: no execute/* tools -- Critic is read-only, no command execution."""
        fm = _extract_frontmatter(_read_agent())
        tools = _extract_tools_from_frontmatter(fm)
        found = [t for t in tools if t.startswith("execute/")]
        assert found == [], f"Forbidden execute/* tools found: {found}"

    def test_no_edit_tools(self) -> None:
        """AC7/AC10: no edit/* tools -- Critic must not write or edit files."""
        fm = _extract_frontmatter(_read_agent())
        tools = _extract_tools_from_frontmatter(fm)
        found = [t for t in tools if t.startswith("edit/")]
        assert found == [], f"Forbidden edit/* tools found: {found}"

    def test_no_mcp_glob_tools(self) -> None:
        """AC7/AC10: no MCP glob tools (e.g., owlbear-kanban/*) -- no state mutation."""
        fm = _extract_frontmatter(_read_agent())
        tools = _extract_tools_from_frontmatter(fm)
        known_prefixes = {"read", "execute", "edit", "search", "vscode", "web", "browser", "agent"}
        found = [
            t for t in tools
            if "*" in t or (
                "/" in t and t.split("/")[0] not in known_prefixes
            )
        ]
        assert found == [], f"Forbidden MCP glob or unknown-prefix tools found: {found}"

    # --- AC11: agents: [] ---

    def test_agents_is_empty_list(self) -> None:
        """AC11: agents must be empty list [] -- leaf subagent, no nesting."""
        fm = _extract_frontmatter(_read_agent())
        match = re.search(r"^agents:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "agents: key not found in frontmatter"
        assert match.group(1).strip() == "[]", (
            f"agents must be '[]' (leaf subagent), got '{match.group(1).strip()}'"
        )

    # --- argument-hint (AC6 / AC8 implied) ---

    def test_argument_hint_exists(self) -> None:
        """AC6/AC8: argument-hint: key must be present to describe invocation."""
        fm = _extract_frontmatter(_read_agent())
        assert re.search(r"^argument-hint:", fm, re.MULTILINE), (
            "argument-hint: key not found in frontmatter"
        )

    def test_argument_hint_generic_covers_both_scopes(self) -> None:
        """AC8: argument-hint must use a generic placeholder ('position', 'claim', or 'critique')
        rather than scope-specific fields -- single hint handles both Mediator and voice invocations.
        """
        fm = _extract_frontmatter(_read_agent())
        hint_match = re.search(r"^argument-hint:\s*(.+)$", fm, re.MULTILINE)
        assert hint_match is not None, "argument-hint: value not found"
        hint = hint_match.group(1).strip().lower()
        assert "position" in hint or "critique" in hint or "claim" in hint, (
            f"argument-hint must contain 'position', 'critique', or 'claim' to cover both "
            f"Mediator and voice invocation scopes, got: '{hint_match.group(1).strip()}'"
        )


class TestFromAC_CriticVoicePromptBehavior:
    """AC4-AC5: System prompt must be purely adversarial with explicit exit behavior."""

    def _body(self) -> str:
        return _extract_body(_read_agent())

    # --- AC4: purely adversarial, never proposes alternatives ---

    def test_persona_section_exists(self) -> None:
        """AC4: body must contain a <persona> XML tag section."""
        body = self._body()
        assert "<persona>" in body, "Body must contain a <persona> section"

    def test_persona_closing_tag_exists(self) -> None:
        """AC4: persona section must be properly closed."""
        body = self._body()
        assert "</persona>" in body, "Body must contain a closing </persona> tag"

    def test_persona_adversarial_challenge_role(self) -> None:
        """AC4: persona must frame the Critic as adversarial challenger of positions."""
        body = self._body()
        persona_match = re.search(r"<persona>(.*?)</persona>", body, re.DOTALL)
        assert persona_match is not None, "<persona>...</persona> block not found"
        persona = persona_match.group(1).lower()
        assert "challenge" in persona or "adversarial" in persona or "critic" in persona, (
            "Persona must frame the Critic as an adversarial challenger"
        )

    def test_persona_challenges_positions_not_pipeline_decisions(self) -> None:
        """AC4: Critic challenges positions (ideation domain), not pipeline decisions."""
        body = self._body()
        assert re.search(r"position|stance|claim|argument", body, re.IGNORECASE), (
            "Body must describe challenging positions, claims, or arguments -- "
            "Critic operates in ideation domain, not pipeline-decision domain"
        )

    def test_persona_never_proposes_alternatives(self) -> None:
        """AC4: Prompt must explicitly state Critic does NOT propose alternatives or solutions."""
        body = self._body()
        assert re.search(
            r"not propose|never propose|do not propose|no alternative|"
            r"not suggest|never suggest|do not suggest|"
            r"never present.{0,30}(case|solution|answer)|"
            r"not.{0,20}(your own|alternatives|solutions)",
            body,
            re.IGNORECASE,
        ), (
            "Prompt must state Critic does NOT propose alternatives -- "
            "AC4: 'purely adversarial: challenges positions, never proposes alternatives'"
        )

    # --- AC5: exit behavior ---

    def test_exit_behavior_solid_present(self) -> None:
        """AC5: Prompt must contain 'solid' (from 'If position is solid...') exit clause."""
        body = self._body()
        assert re.search(r"\bsolid\b", body, re.IGNORECASE), (
            "Prompt must contain 'solid' as part of the exit-behavior clause -- "
            "AC5: 'If position is solid after honest examination, say so and exit.'"
        )

    def test_exit_behavior_honest_examination(self) -> None:
        """AC5: Prompt must reference 'honest examination' in exit clause."""
        body = self._body()
        assert re.search(
            r"honest.{0,20}examination|honest.{0,20}review|genuine.{0,20}examination",
            body,
            re.IGNORECASE,
        ), (
            "Prompt must contain 'honest examination' or equivalent -- "
            "AC5: 'If position is solid after honest examination, say so and exit.'"
        )

    def test_exit_behavior_allow_clean_exit(self) -> None:
        """AC5: Prompt must allow Critic to exit cleanly when no genuine issues found."""
        body = self._body()
        assert re.search(
            r"\bexit\b|\bsay so\b|no issue|no genuine|nothing to challenge",
            body,
            re.IGNORECASE,
        ), (
            "Prompt must allow a clean exit when position is solid -- "
            "AC5: '...say so and exit.'"
        )

    def test_exit_behavior_no_manufacture_objections(self) -> None:
        """AC5: Prompt must explicitly forbid manufacturing objections."""
        body = self._body()
        assert re.search(r"manufactur", body, re.IGNORECASE), (
            "Prompt must contain 'manufacture' to forbid manufacturing objections -- "
            "AC5: 'Do not manufacture objections.'"
        )


class TestFromAC_CriticVoiceContextAndScope:
    """AC6, AC8: Agent reads context.md from Working Directory; handles dual-scope invocation."""

    def _body(self) -> str:
        return _extract_body(_read_agent())

    # --- AC6: receives position via prompt, reads context.md from Working Directory ---

    def test_context_md_mentioned(self) -> None:
        """AC6: Body must instruct reading context.md from Working Directory."""
        body = self._body()
        assert "context.md" in body, (
            "Body must reference 'context.md' -- "
            "AC6: agent reads context.md from Working Directory"
        )

    def test_working_directory_mentioned(self) -> None:
        """AC6: Body must reference 'Working Directory' as source of context."""
        body = self._body()
        assert re.search(r"working dir", body, re.IGNORECASE), (
            "Body must mention 'Working Directory' as the source of context.md -- "
            "AC6: 'reads context.md from Working Directory'"
        )

    def test_position_input_described_in_body(self) -> None:
        """AC6: Body must describe receiving the invoker's current position as input."""
        body = self._body()
        assert re.search(r"position|claim|stance", body, re.IGNORECASE), (
            "Body must describe receiving the invoker's position or claim as input -- "
            "AC6: 'Agent receives voice's current position via prompt'"
        )

    # --- AC8: dual-scope, no scope-specific configuration ---

    def test_dual_scope_no_scope_specific_frontmatter(self) -> None:
        """AC8: No 'scope:' field in frontmatter -- scope determined by input context only."""
        fm = _extract_frontmatter(_read_agent())
        assert "scope:" not in fm, (
            "Frontmatter must not contain a 'scope:' field -- "
            "AC8: no scope-specific configuration required"
        )

    def test_dual_scope_describes_both_mediator_and_voice(self) -> None:
        """AC8: Body must describe both Mediator standalone and domain voice invocation scopes."""
        body = self._body()
        has_mediator = re.search(r"mediator|standalone|meta.?level", body, re.IGNORECASE)
        assert has_mediator, (
            "Body must describe Mediator standalone scope "
            "(keyword: 'mediator', 'standalone', or 'meta-level') -- "
            "AC8: dual-scope invocation via single prompt handler"
        )
        has_voice = re.search(r"voice|domain|embedded", body, re.IGNORECASE)
        assert has_voice, (
            "Body must describe domain voice embedded scope "
            "(keyword: 'voice', 'domain', or 'embedded') -- "
            "AC8: dual-scope invocation via single prompt handler"
        )


class TestFromAC_CriticVoiceOutputContract:
    """AC7: Output is adversarial challenges only -- no state mutations, no file writes."""

    def _body(self) -> str:
        return _extract_body(_read_agent())

    def test_no_file_writes_stated_in_body(self) -> None:
        """AC7: Body must explicitly state Critic does not write or create files."""
        body = self._body()
        assert re.search(
            r"no.{0,25}(file.{0,10}(write|edit|creat))|"
            r"(never|not|no).{0,20}(write|edit|creat).{0,20}file|"
            r"read.?only",
            body,
            re.IGNORECASE,
        ), (
            "Body must state Critic does NOT write/edit/create files -- "
            "AC7: 'no direct file writes'"
        )

    def test_no_kanban_commands_stated(self) -> None:
        """AC7: Body must state no kanban commands or state mutations."""
        body = self._body()
        assert re.search(
            r"no.{0,25}kanban|kanban.{0,25}(no\b|not|never)|"
            r"no.{0,25}state.{0,20}mutation|"
            r"(never|not|no).{0,25}(modify|alter|change|update).{0,25}(state|kanban|task)",
            body,
            re.IGNORECASE,
        ), (
            "Body must state Critic does NOT issue kanban commands or mutate state -- "
            "AC7: returns challenges only, no side effects"
        )

    def test_output_returns_challenges(self) -> None:
        """AC7: Output contract must describe returning challenges/findings to the invoker."""
        body = self._body()
        assert re.search(r"challenge|finding|objection|weakness|critique", body, re.IGNORECASE), (
            "Body must describe output type as challenges, findings, or objections -- "
            "AC7: 'Returns adversarial challenges to the invoking voice'"
        )

    def test_critical_rules_section_exists(self) -> None:
        """AC7: Must have a critical_rules or equivalent constraints section."""
        body = self._body()
        assert re.search(r"<critical_rules>|## critical rule|critical rule", body, re.IGNORECASE), (
            "Body must have a <critical_rules> or 'Critical Rules' section to enforce "
            "read-only constraint -- AC7: no direct file writes"
        )
