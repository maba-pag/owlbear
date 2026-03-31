"""Tests for task #467: Create challenger.agent.md (adversarial pre-decision review subagent).

Contract-level verification that agents/challenger.agent.md exists with the
required frontmatter and body content per the AC.

AC coverage:
  - AC1:  agents/challenger.agent.md exists with valid YAML frontmatter
  - AC2:  Frontmatter name: challenger
  - AC3:  Frontmatter description: one-line adversarial pre-decision reasoning challenge
  - AC4:  Frontmatter argument-hint: contains all 6 input field placeholders
          (task_id, proposed_verdict, reasoning, ac_lines, codebase_evidence, research_doc)
  - AC5:  Frontmatter user-invocable: false
  - AC6:  Frontmatter disable-model-invocation: true
  - AC7:  Frontmatter model: Claude Opus 4.6 (copilot) — single string, NOT array
  - AC8:  Frontmatter tools: [read/readFile, read/viewImage, read/problems, search, vscode/memory]
          (canonical tool IDs, assign mode, read-only — no execute/*, edit/*, MCP globs)
  - AC9:  Frontmatter agents: []
  - AC10: <persona> section defines adversarial challenge role with NOT-validate,
          NOT-edit-files, and NOT-kanban constraints
  - AC11: Input contract table with 6 fields (task_id, proposed_verdict, reasoning,
          ac_lines, codebase_evidence, research_doc) with correct types and required/optional
  - AC12: Output contract with 6 sections: Challenges (severity: critical/moderate/minor),
          Blind Spots, Alternative Angles, Risk Assessment (low/medium/high),
          Confidence in Original (.0-1.0 float), Recommendation (proceed/reconsider/block)
  - AC13: Output is structured text only — no file edits, no kanban commands,
          no tool calls that modify state
"""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
_AGENT_FILE = _REPO_ROOT / "agents" / "challenger.agent.md"

_EXPECTED_TOOLS: frozenset[str] = frozenset(
    {"read/readFile", "read/viewImage", "read/problems", "search", "vscode/memory"}
)

_ARGUMENT_HINT_FIELDS: list[str] = [
    "task_id",
    "proposed_verdict",
    "reasoning",
    "ac_lines",
    "codebase_evidence",
    "research_doc",
]

_REQUIRED_INPUT_FIELDS: list[str] = [
    "task_id",
    "proposed_verdict",
    "reasoning",
    "ac_lines",
    "codebase_evidence",
]
_OPTIONAL_INPUT_FIELDS: list[str] = ["research_doc"]

_OUTPUT_SECTION_KEYWORDS: list[str] = [
    "Challenges",
    "Blind Spots",
    "Alternative Angles",
    "Risk Assessment",
    "Confidence in Original",
    "Recommendation",
]


def _read_agent(path: Path) -> str:
    return path.read_text(encoding="utf-8")


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


class TestFromAC_ChallengerFrontmatter:
    """AC1-AC9: agents/challenger.agent.md must exist with correct frontmatter."""

    # --- AC1: file exists with valid frontmatter ---

    def test_file_exists(self) -> None:
        """AC1: agents/challenger.agent.md must exist on disk."""
        assert _AGENT_FILE.is_file(), (
            "agents/challenger.agent.md does not exist — builder must create it"
        )

    def test_has_valid_yaml_frontmatter(self) -> None:
        """AC1: File must start with --- ... --- YAML frontmatter block."""
        content = _read_agent(_AGENT_FILE)
        assert content.startswith("---\n"), (
            "agents/challenger.agent.md must begin with '---' YAML frontmatter"
        )
        fm = _extract_frontmatter(content)
        assert fm.strip() != "", "Frontmatter block is empty"

    # --- AC2: name ---

    def test_name_is_challenger(self) -> None:
        """AC2: name field must be exactly 'challenger'."""
        fm = _extract_frontmatter(_read_agent(_AGENT_FILE))
        match = re.search(r"^name:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "name: key not found in frontmatter"
        assert match.group(1).strip() == "challenger", (
            f"name must be 'challenger', got '{match.group(1).strip()}'"
        )

    # --- AC3: description ---

    def test_description_exists(self) -> None:
        """AC3: description: key must be present."""
        fm = _extract_frontmatter(_read_agent(_AGENT_FILE))
        match = re.search(r"^description:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "description: key not found in frontmatter"
        assert match.group(1).strip() != "", "description: value is empty"

    def test_description_mentions_adversarial(self) -> None:
        """AC3: description must convey adversarial challenge role."""
        fm = _extract_frontmatter(_read_agent(_AGENT_FILE))
        match = re.search(r"^description:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "description: key not found in frontmatter"
        desc = match.group(1).strip().lower()
        assert "adversarial" in desc or "challenge" in desc, (
            f"description must mention 'adversarial' or 'challenge', got: '{desc}'"
        )

    def test_description_is_one_line(self) -> None:
        """AC3: description must be a single line (not multiline YAML block)."""
        fm = _extract_frontmatter(_read_agent(_AGENT_FILE))
        # One-line: the value comes directly after 'description: '
        match = re.search(r"^description:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "description: must be a one-line value, not a block"

    # --- AC4: argument-hint ---

    def test_argument_hint_exists(self) -> None:
        """AC4: argument-hint: key must be present."""
        fm = _extract_frontmatter(_read_agent(_AGENT_FILE))
        match = re.search(r"^argument-hint:", fm, re.MULTILINE)
        assert match is not None, "argument-hint: key not found in frontmatter"

    def test_argument_hint_contains_task_id(self) -> None:
        """AC4: argument-hint must contain task_id placeholder."""
        fm = _extract_frontmatter(_read_agent(_AGENT_FILE))
        hint_match = re.search(r"^argument-hint:\s*(.+)$", fm, re.MULTILINE)
        assert hint_match is not None, "argument-hint: value not found"
        assert "task_id" in hint_match.group(1), (
            "argument-hint must include 'task_id' field placeholder"
        )

    def test_argument_hint_contains_proposed_verdict(self) -> None:
        """AC4: argument-hint must contain proposed_verdict placeholder."""
        fm = _extract_frontmatter(_read_agent(_AGENT_FILE))
        hint_match = re.search(r"^argument-hint:\s*(.+)$", fm, re.MULTILINE)
        assert hint_match is not None, "argument-hint: value not found"
        assert "proposed_verdict" in hint_match.group(1), (
            "argument-hint must include 'proposed_verdict' field placeholder"
        )

    def test_argument_hint_contains_reasoning(self) -> None:
        """AC4: argument-hint must contain reasoning placeholder."""
        fm = _extract_frontmatter(_read_agent(_AGENT_FILE))
        hint_match = re.search(r"^argument-hint:\s*(.+)$", fm, re.MULTILINE)
        assert hint_match is not None, "argument-hint: value not found"
        assert "reasoning" in hint_match.group(1), (
            "argument-hint must include 'reasoning' field placeholder"
        )

    def test_argument_hint_contains_ac_lines(self) -> None:
        """AC4: argument-hint must contain ac_lines placeholder."""
        fm = _extract_frontmatter(_read_agent(_AGENT_FILE))
        hint_match = re.search(r"^argument-hint:\s*(.+)$", fm, re.MULTILINE)
        assert hint_match is not None, "argument-hint: value not found"
        assert "ac_lines" in hint_match.group(1), (
            "argument-hint must include 'ac_lines' field placeholder"
        )

    def test_argument_hint_contains_codebase_evidence(self) -> None:
        """AC4: argument-hint must contain codebase_evidence placeholder."""
        fm = _extract_frontmatter(_read_agent(_AGENT_FILE))
        hint_match = re.search(r"^argument-hint:\s*(.+)$", fm, re.MULTILINE)
        assert hint_match is not None, "argument-hint: value not found"
        assert "codebase_evidence" in hint_match.group(1), (
            "argument-hint must include 'codebase_evidence' field placeholder"
        )

    def test_argument_hint_contains_research_doc(self) -> None:
        """AC4: argument-hint must contain research_doc placeholder."""
        fm = _extract_frontmatter(_read_agent(_AGENT_FILE))
        hint_match = re.search(r"^argument-hint:\s*(.+)$", fm, re.MULTILINE)
        assert hint_match is not None, "argument-hint: value not found"
        assert "research_doc" in hint_match.group(1), (
            "argument-hint must include 'research_doc' field placeholder"
        )

    # --- AC5: user-invocable ---

    def test_user_invocable_false(self) -> None:
        """AC5: user-invocable must be 'false'."""
        fm = _extract_frontmatter(_read_agent(_AGENT_FILE))
        match = re.search(r"^user-invocable:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "user-invocable: key not found in frontmatter"
        assert match.group(1).strip() == "false", (
            f"user-invocable must be 'false', got '{match.group(1).strip()}'"
        )

    # --- AC6: disable-model-invocation ---

    def test_disable_model_invocation_true(self) -> None:
        """AC6: disable-model-invocation must be 'true'."""
        fm = _extract_frontmatter(_read_agent(_AGENT_FILE))
        match = re.search(r"^disable-model-invocation:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "disable-model-invocation: key not found in frontmatter"
        assert match.group(1).strip() == "true", (
            f"disable-model-invocation must be 'true', got '{match.group(1).strip()}'"
        )

    # --- AC7: model — single string Claude Opus 4.6, NOT an array ---

    def test_model_is_opus_46(self) -> None:
        """AC7: model must be 'Claude Opus 4.6 (copilot)'."""
        fm = _extract_frontmatter(_read_agent(_AGENT_FILE))
        match = re.search(r"^model:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "model: key not found in frontmatter"
        model_val = match.group(1).strip()
        assert "Opus 4.6" in model_val, (
            f"model must contain 'Opus 4.6', got '{model_val}'"
        )

    def test_model_is_single_string_not_array(self) -> None:
        """AC7: model must be a single string (not an array like code-reader)."""
        fm = _extract_frontmatter(_read_agent(_AGENT_FILE))
        match = re.search(r"^model:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "model: key not found in frontmatter"
        model_val = match.group(1).strip()
        assert not model_val.startswith("["), (
            f"model must be a single string, not an array — got '{model_val}'"
        )

    def test_model_is_copilot_provider(self) -> None:
        """AC7: model must specify the copilot provider."""
        fm = _extract_frontmatter(_read_agent(_AGENT_FILE))
        match = re.search(r"^model:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "model: key not found in frontmatter"
        model_val = match.group(1).strip()
        assert "copilot" in model_val.lower(), (
            f"model must specify '(copilot)' provider, got '{model_val}'"
        )

    # --- AC8: tools ---

    def test_tools_key_exists(self) -> None:
        """AC8: tools: key must be present in frontmatter."""
        fm = _extract_frontmatter(_read_agent(_AGENT_FILE))
        match = re.search(r"^tools:", fm, re.MULTILINE)
        assert match is not None, "tools: key not found in frontmatter"

    def test_tools_exactly_five(self) -> None:
        """AC8: tools list must contain exactly 5 entries."""
        fm = _extract_frontmatter(_read_agent(_AGENT_FILE))
        tools = _extract_tools_from_frontmatter(fm)
        assert len(tools) == 5, (
            f"Expected exactly 5 tools, got {len(tools)}: {tools}"
        )

    def test_tools_are_correct_set(self) -> None:
        """AC8: tools must be: read/readFile, read/viewImage, read/problems, search, vscode/memory."""
        fm = _extract_frontmatter(_read_agent(_AGENT_FILE))
        tools = frozenset(_extract_tools_from_frontmatter(fm))
        assert tools == _EXPECTED_TOOLS, (
            f"Tools mismatch.\n"
            f"  Expected: {sorted(_EXPECTED_TOOLS)}\n"
            f"  Got:      {sorted(tools)}\n"
            f"  Missing:  {sorted(_EXPECTED_TOOLS - tools)}\n"
            f"  Extra:    {sorted(tools - _EXPECTED_TOOLS)}"
        )

    def test_no_execute_tools(self) -> None:
        """AC8: no execute/* tools allowed (read-only agent)."""
        fm = _extract_frontmatter(_read_agent(_AGENT_FILE))
        tools = _extract_tools_from_frontmatter(fm)
        found = [t for t in tools if t.startswith("execute/")]
        assert found == [], f"Forbidden execute/* tools found: {found}"

    def test_no_edit_tools(self) -> None:
        """AC8: no edit/* tools allowed (read-only agent)."""
        fm = _extract_frontmatter(_read_agent(_AGENT_FILE))
        tools = _extract_tools_from_frontmatter(fm)
        found = [t for t in tools if t.startswith("edit/")]
        assert found == [], f"Forbidden edit/* tools found: {found}"

    def test_no_mcp_glob_tools(self) -> None:
        """AC8: no MCP glob tools (e.g., owlbear-kanban/*) — read-only, no state mutation."""
        fm = _extract_frontmatter(_read_agent(_AGENT_FILE))
        tools = _extract_tools_from_frontmatter(fm)
        known_prefixes = {"read", "execute", "edit", "search", "vscode", "web", "browser", "agent"}
        found = [
            t for t in tools
            if "*" in t or (
                "/" in t and t.split("/")[0] not in known_prefixes
            )
        ]
        assert found == [], f"Forbidden MCP glob or unknown-prefix tools found: {found}"

    # --- AC9: agents: [] ---

    def test_agents_is_empty_list(self) -> None:
        """AC9: agents must be empty list [] — leaf subagent, no nesting."""
        fm = _extract_frontmatter(_read_agent(_AGENT_FILE))
        match = re.search(r"^agents:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "agents: key not found in frontmatter"
        assert match.group(1).strip() == "[]", (
            f"agents must be '[]' (leaf subagent), got '{match.group(1).strip()}'"
        )


class TestFromAC_ChallengerPersona:
    """AC10: <persona> section must define adversarial challenge role with read-only constraints."""

    def _body(self) -> str:
        return _extract_body(_read_agent(_AGENT_FILE))

    def test_persona_tag_exists(self) -> None:
        """AC10: body must contain a <persona> XML tag section."""
        body = self._body()
        assert "<persona>" in body, (
            "Body must contain a <persona> section"
        )

    def test_persona_closing_tag_exists(self) -> None:
        """AC10: persona section must be properly closed with </persona>."""
        body = self._body()
        assert "</persona>" in body, (
            "Body must contain a closing </persona> tag"
        )

    def test_persona_mentions_weaknesses(self) -> None:
        """AC10: persona must describe role as finding weaknesses in reasoning."""
        body = self._body()
        persona_match = re.search(r"<persona>(.*?)</persona>", body, re.DOTALL)
        assert persona_match is not None, "<persona>...</persona> block not found"
        persona = persona_match.group(1).lower()
        assert "weakness" in persona or "weak" in persona or "flaw" in persona, (
            "Persona must describe finding weaknesses/flaws in reasoning"
        )

    def test_persona_mentions_blind_spots(self) -> None:
        """AC10: persona must reference surfacing blind spots."""
        body = self._body()
        persona_match = re.search(r"<persona>(.*?)</persona>", body, re.DOTALL)
        assert persona_match is not None, "<persona>...</persona> block not found"
        persona = persona_match.group(1).lower()
        assert "blind spot" in persona or "blind_spot" in persona or "oversight" in persona, (
            "Persona must reference surfacing blind spots or oversights"
        )

    def test_persona_mentions_counter_arguments(self) -> None:
        """AC10: persona must reference identifying counter-arguments."""
        body = self._body()
        persona_match = re.search(r"<persona>(.*?)</persona>", body, re.DOTALL)
        assert persona_match is not None, "<persona>...</persona> block not found"
        persona = persona_match.group(1).lower()
        assert (
            "counter" in persona
            or "alternative" in persona
            or "challenge" in persona
        ), (
            "Persona must reference counter-arguments, alternatives, or challenges"
        )

    def test_persona_not_validate_constraint(self) -> None:
        """AC10: persona must explicitly state agent does NOT validate/confirm original analysis."""
        body = self._body()
        persona_match = re.search(r"<persona>(.*?)</persona>", body, re.DOTALL)
        assert persona_match is not None, "<persona>...</persona> block not found"
        persona = persona_match.group(1).lower()
        # Must say it does not validate or confirm
        assert (
            "not validate" in persona
            or "not confirm" in persona
            or "never validate" in persona
            or "never confirm" in persona
            or "do not validate" in persona
            or "do not confirm" in persona
            or "does not validate" in persona
            or "does not confirm" in persona
        ), (
            "Persona must explicitly state agent does NOT validate/confirm the original analysis"
        )

    def test_persona_not_edit_files_constraint(self) -> None:
        """AC10: persona must explicitly state agent does NOT edit files."""
        body = self._body()
        persona_match = re.search(r"<persona>(.*?)</persona>", body, re.DOTALL)
        assert persona_match is not None, "<persona>...</persona> block not found"
        persona = persona_match.group(1).lower()
        assert (
            "not edit" in persona
            or "never edit" in persona
            or "do not edit" in persona
            or "does not edit" in persona
            or "read-only" in persona
            or "read only" in persona
        ), (
            "Persona must explicitly state agent does NOT edit files (read-only constraint)"
        )

    def test_persona_not_kanban_constraint(self) -> None:
        """AC10: persona must explicitly state agent does NOT edit kanban tasks."""
        body = self._body()
        persona_match = re.search(r"<persona>(.*?)</persona>", body, re.DOTALL)
        assert persona_match is not None, "<persona>...</persona> block not found"
        persona = persona_match.group(1).lower()
        assert (
            "kanban" in persona
            or "task" in persona
        ), (
            "Persona must reference kanban tasks in the read-only constraints"
        )
        # Must say it doesn't edit kanban or tasks
        assert (
            "not edit" in persona
            or "never edit" in persona
            or "do not edit" in persona
            or "does not edit" in persona
            or "no kanban" in persona
            or "not modify" in persona
            or "never modify" in persona
        ), (
            "Persona must state it does NOT edit/modify kanban tasks"
        )


class TestFromAC_ChallengerInputContract:
    """AC11: Input contract table must define 6 fields with correct types and required/optional."""

    def _body(self) -> str:
        return _extract_body(_read_agent(_AGENT_FILE))

    def test_input_contract_section_exists(self) -> None:
        """AC11: body must contain an Input Contract section."""
        body = self._body()
        assert re.search(r"input contract", body, re.IGNORECASE), (
            "Body must contain an 'Input Contract' section"
        )

    def test_input_field_task_id_present(self) -> None:
        """AC11: input contract must include task_id field."""
        body = self._body()
        assert "task_id" in body, "Input contract must define 'task_id' field"

    def test_input_field_task_id_is_string_type(self) -> None:
        """AC11: task_id must be typed as string."""
        body = self._body()
        # Look for task_id row containing 'string'
        assert re.search(r"task_id\s*[|,].*string", body, re.IGNORECASE), (
            "Input contract must declare task_id as type 'string'"
        )

    def test_input_field_task_id_is_required(self) -> None:
        """AC11: task_id must be marked required."""
        body = self._body()
        assert re.search(r"task_id\s*[|,].*yes", body, re.IGNORECASE), (
            "Input contract must mark task_id as required (yes)"
        )

    def test_input_field_proposed_verdict_present(self) -> None:
        """AC11: input contract must include proposed_verdict field."""
        body = self._body()
        assert "proposed_verdict" in body, (
            "Input contract must define 'proposed_verdict' field"
        )

    def test_input_field_proposed_verdict_is_string_and_required(self) -> None:
        """AC11: proposed_verdict must be typed string, required."""
        body = self._body()
        assert re.search(r"proposed_verdict\s*[|,].*string", body, re.IGNORECASE), (
            "Input contract must declare proposed_verdict as type 'string'"
        )
        assert re.search(r"proposed_verdict\s*[|,].*yes", body, re.IGNORECASE), (
            "Input contract must mark proposed_verdict as required (yes)"
        )

    def test_input_field_reasoning_present(self) -> None:
        """AC11: input contract must include reasoning field."""
        body = self._body()
        assert "reasoning" in body, "Input contract must define 'reasoning' field"

    def test_input_field_reasoning_is_string_and_required(self) -> None:
        """AC11: reasoning must be typed string, required."""
        body = self._body()
        assert re.search(r"reasoning\s*[|,].*string", body, re.IGNORECASE), (
            "Input contract must declare reasoning as type 'string'"
        )
        assert re.search(r"reasoning\s*[|,].*yes", body, re.IGNORECASE), (
            "Input contract must mark reasoning as required (yes)"
        )

    def test_input_field_ac_lines_present(self) -> None:
        """AC11: input contract must include ac_lines field."""
        body = self._body()
        assert "ac_lines" in body, "Input contract must define 'ac_lines' field"

    def test_input_field_ac_lines_is_string_array_and_required(self) -> None:
        """AC11: ac_lines must be typed string[], required."""
        body = self._body()
        assert re.search(r"ac_lines\s*[|,].*string", body, re.IGNORECASE), (
            "Input contract must declare ac_lines as type 'string[]'"
        )
        assert re.search(r"ac_lines\s*[|,].*yes", body, re.IGNORECASE), (
            "Input contract must mark ac_lines as required (yes)"
        )

    def test_input_field_codebase_evidence_present(self) -> None:
        """AC11: input contract must include codebase_evidence field."""
        body = self._body()
        assert "codebase_evidence" in body, (
            "Input contract must define 'codebase_evidence' field"
        )

    def test_input_field_codebase_evidence_is_string_and_required(self) -> None:
        """AC11: codebase_evidence must be typed string, required."""
        body = self._body()
        assert re.search(r"codebase_evidence\s*[|,].*string", body, re.IGNORECASE), (
            "Input contract must declare codebase_evidence as type 'string'"
        )
        assert re.search(r"codebase_evidence\s*[|,].*yes", body, re.IGNORECASE), (
            "Input contract must mark codebase_evidence as required (yes)"
        )

    def test_input_field_research_doc_present(self) -> None:
        """AC11: input contract must include research_doc field."""
        body = self._body()
        assert "research_doc" in body, "Input contract must define 'research_doc' field"

    def test_input_field_research_doc_is_optional(self) -> None:
        """AC11: research_doc must be marked optional (not required)."""
        body = self._body()
        # research_doc row should contain 'no' for required column
        assert re.search(r"research_doc\s*[|,].*no", body, re.IGNORECASE), (
            "Input contract must mark research_doc as optional (no)"
        )

    def test_input_has_exactly_six_fields(self) -> None:
        """AC11: input contract must define exactly 6 fields."""
        body = self._body()
        found_fields = [f for f in _ARGUMENT_HINT_FIELDS if f in body]
        assert len(found_fields) == 6, (
            f"Expected all 6 input contract fields, found only: {found_fields}"
        )


class TestFromAC_ChallengerOutputContract:
    """AC12-AC13: Output contract must define 6 sections with correct value types.
    Output must be structured text only — no state mutations."""

    def _body(self) -> str:
        return _extract_body(_read_agent(_AGENT_FILE))

    def test_output_contract_section_exists(self) -> None:
        """AC12: body must contain an Output Contract section."""
        body = self._body()
        assert re.search(r"output contract", body, re.IGNORECASE), (
            "Body must contain an 'Output Contract' section"
        )

    def test_output_section_challenges(self) -> None:
        """AC12: output contract must define a Challenges section."""
        body = self._body()
        assert re.search(r"\bChallenges\b", body), (
            "Output contract must define a 'Challenges' section"
        )

    def test_output_challenges_severity_values(self) -> None:
        """AC12: Challenges section must specify critical/moderate/minor severity values."""
        body = self._body()
        assert "critical" in body.lower(), (
            "Output contract must specify 'critical' as a severity value for Challenges"
        )
        assert "moderate" in body.lower(), (
            "Output contract must specify 'moderate' as a severity value for Challenges"
        )
        assert "minor" in body.lower(), (
            "Output contract must specify 'minor' as a severity value for Challenges"
        )

    def test_output_section_blind_spots(self) -> None:
        """AC12: output contract must define a Blind Spots section."""
        body = self._body()
        assert re.search(r"blind spots?", body, re.IGNORECASE), (
            "Output contract must define a 'Blind Spots' section"
        )

    def test_output_section_alternative_angles(self) -> None:
        """AC12: output contract must define an Alternative Angles section."""
        body = self._body()
        assert re.search(r"alternative angles?", body, re.IGNORECASE), (
            "Output contract must define an 'Alternative Angles' section"
        )

    def test_output_section_risk_assessment(self) -> None:
        """AC12: output contract must define a Risk Assessment section."""
        body = self._body()
        assert re.search(r"risk assessment", body, re.IGNORECASE), (
            "Output contract must define a 'Risk Assessment' section"
        )

    def test_output_risk_overall_values(self) -> None:
        """AC12: Risk Assessment must specify low/medium/high overall values."""
        body = self._body()
        # All three severity levels must appear in context of risk
        assert re.search(r"low", body, re.IGNORECASE), (
            "Output contract must specify 'low' as a Risk Assessment overall value"
        )
        assert re.search(r"medium", body, re.IGNORECASE), (
            "Output contract must specify 'medium' as a Risk Assessment overall value"
        )
        assert re.search(r"high", body, re.IGNORECASE), (
            "Output contract must specify 'high' as a Risk Assessment overall value"
        )

    def test_output_section_confidence_in_original(self) -> None:
        """AC12: output contract must define a Confidence in Original section."""
        body = self._body()
        assert re.search(r"confidence in original", body, re.IGNORECASE), (
            "Output contract must define a 'Confidence in Original' section"
        )

    def test_output_confidence_is_float_range(self) -> None:
        """AC12: Confidence in Original must specify a .0-1.0 float range."""
        body = self._body()
        # Must mention float or decimal-point notation for the 0-1 range
        assert re.search(r"\.0.*1\.0|0\.0.*1\.0|float", body), (
            "Output contract must specify Confidence in Original as a .0-1.0 float"
        )

    def test_output_section_recommendation(self) -> None:
        """AC12: output contract must define a Recommendation section."""
        body = self._body()
        assert re.search(r"\bRecommendation\b", body), (
            "Output contract must define a 'Recommendation' section"
        )

    def test_output_recommendation_proceed_value(self) -> None:
        """AC12: Recommendation must specify 'proceed' as a valid value."""
        body = self._body()
        assert re.search(r"\bproceed\b", body, re.IGNORECASE), (
            "Output contract must specify 'proceed' as a Recommendation value"
        )

    def test_output_recommendation_reconsider_value(self) -> None:
        """AC12: Recommendation must specify 'reconsider' as a valid value."""
        body = self._body()
        assert re.search(r"\breconsider\b", body, re.IGNORECASE), (
            "Output contract must specify 'reconsider' as a Recommendation value"
        )

    def test_output_recommendation_block_value(self) -> None:
        """AC12: Recommendation must specify 'block' as a valid value."""
        body = self._body()
        assert re.search(r"\bblock\b", body, re.IGNORECASE), (
            "Output contract must specify 'block' as a Recommendation value"
        )

    def test_output_no_file_operations_command(self) -> None:
        """AC13: output section must not instruct creating or editing files."""
        body = self._body()
        # Look for the output contract section specifically
        output_match = re.search(
            r"(?:output contract|output section)(.*?)(?:\n#{1,3} |\Z)",
            body,
            re.DOTALL | re.IGNORECASE,
        )
        if output_match:
            output_section = output_match.group(1).lower()
            assert "create_file" not in output_section, (
                "Output section must not reference create_file — structured text only"
            )
            assert "edit_file" not in output_section, (
                "Output section must not reference edit_file — structured text only"
            )

    def test_output_structured_text_only_stated(self) -> None:
        """AC13: body must state that output is structured text only."""
        body = self._body()
        assert re.search(
            r"structured text|text only|no file|read.only|no.*(edit|modify|create)",
            body,
            re.IGNORECASE,
        ), (
            "Body must state that output is structured text only with no state mutations"
        )

