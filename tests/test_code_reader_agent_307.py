"""Tests for task #307: Create Code-Reader subagent (agent.md).

Contract-level verification that agents/code-reader.agent.md exists with the
required frontmatter and body content per the AC.

AC coverage:
  - AC1:  agents/code-reader.agent.md exists with valid YAML frontmatter
  - AC2:  name: code-reader
  - AC3:  user-invocable: false
  - AC4:  disable-model-invocation: true
  - AC5:  agents: []
  - AC6:  model: [Claude Sonnet 4.6 (copilot), GPT-5.4 (copilot)] (matches reviewer)
  - AC7:  tools (assign mode, exactly 5): read/readFile, read/viewImage,
          read/problems, search, vscode/memory
  - AC8:  No execute/*, edit/*, agent, web, browser, or MCP tools in tools array
  - AC9:  Body contains procedures for code-review skill steps 6.0-6.6 and 7.1-7.4
  - AC10: Body documents input contract: task_id, ac_lines, changed_files, test_files
  - AC11: Body defines 8-section output contract: test_writer_audit, security_review,
          test_integrity, test_quality, data_safety, test_gaps, necessity_check,
          informational
  - AC12: Body includes persona establishing read-only adversarial analysis role
"""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
_AGENT_FILE = _REPO_ROOT / "share" / "agents" / "code-reader.agent.md"
_REVIEWER_FILE = _REPO_ROOT / "share" / "agents" / "reviewer.agent.md"

_EXPECTED_TOOLS: frozenset[str] = frozenset(
    {"read/readFile", "read/viewImage", "read/problems", "search", "vscode/memory"}
)
_FORBIDDEN_STANDALONE: frozenset[str] = frozenset({"agent", "web", "browser"})


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
    """Parse tools from YAML frontmatter (handles inline and next-line bracket syntax)."""
    # Match: "tools: [...]" or "tools:\n  [...]"
    match = re.search(r"^tools:\s*\[([^\]]*)\]", fm, re.MULTILINE)
    if not match:
        match = re.search(r"^tools:\s*\n\s*\[([^\]]*)\]", fm, re.MULTILINE)
    assert match is not None, (
        "tools: key not found or not in bracket syntax in frontmatter"
    )
    raw = match.group(1)
    return [t.strip().strip("'\"") for t in raw.split(",") if t.strip()]


class TestFromAC_CodeReaderFrontmatter:
    """AC1-AC8: agents/code-reader.agent.md must exist with correct frontmatter."""

    # --- AC1: file exists with valid frontmatter ---

    def test_file_exists(self) -> None:
        """AC1: agents/code-reader.agent.md must exist on disk."""
        assert _AGENT_FILE.is_file(), (
            "agents/code-reader.agent.md does not exist — builder must create it"
        )

    def test_has_valid_yaml_frontmatter(self) -> None:
        """AC1: File must start with --- ... --- YAML frontmatter block."""
        content = _read_agent(_AGENT_FILE)
        assert content.startswith("---\n"), (
            "agents/code-reader.agent.md must begin with '---' YAML frontmatter"
        )
        fm = _extract_frontmatter(content)
        assert fm.strip() != "", "Frontmatter block is empty"

    # --- AC2-AC5: required scalar fields ---

    def test_name_is_code_reader(self) -> None:
        """AC2: name field must be exactly 'code-reader'."""
        fm = _extract_frontmatter(_read_agent(_AGENT_FILE))
        match = re.search(r"^name:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "name: key not found in frontmatter"
        assert match.group(1).strip() == "code-reader", (
            f"name must be 'code-reader', got '{match.group(1).strip()}'"
        )

    def test_user_invocable_false(self) -> None:
        """AC3: user-invocable must be 'false'."""
        fm = _extract_frontmatter(_read_agent(_AGENT_FILE))
        match = re.search(r"^user-invocable:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "user-invocable: key not found in frontmatter"
        assert match.group(1).strip() == "false", (
            f"user-invocable must be 'false', got '{match.group(1).strip()}'"
        )

    def test_disable_model_invocation_true(self) -> None:
        """AC4: disable-model-invocation must be 'true'."""
        fm = _extract_frontmatter(_read_agent(_AGENT_FILE))
        match = re.search(r"^disable-model-invocation:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "disable-model-invocation: key not found in frontmatter"
        assert match.group(1).strip() == "true", (
            f"disable-model-invocation must be 'true', got '{match.group(1).strip()}'"
        )

    def test_agents_is_empty_list(self) -> None:
        """AC5: agents must be empty list []."""
        fm = _extract_frontmatter(_read_agent(_AGENT_FILE))
        match = re.search(r"^agents:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "agents: key not found in frontmatter"
        assert match.group(1).strip() == "[]", (
            f"agents must be '[]', got '{match.group(1).strip()}'"
        )

    # --- AC6: model matches reviewer ---

    def test_model_matches_reviewer(self) -> None:
        """AC6: model must match reviewer.agent.md exactly."""
        reviewer_fm = _extract_frontmatter(_read_agent(_REVIEWER_FILE))
        reviewer_match = re.search(r"^model:\s*(.+)$", reviewer_fm, re.MULTILINE)
        assert reviewer_match is not None, "Could not read model from reviewer.agent.md"
        expected = reviewer_match.group(1).strip()

        agent_fm = _extract_frontmatter(_read_agent(_AGENT_FILE))
        agent_match = re.search(r"^model:\s*(.+)$", agent_fm, re.MULTILINE)
        assert agent_match is not None, "model: key not found in code-reader frontmatter"
        assert agent_match.group(1).strip() == expected, (
            f"model must match reviewer ('{expected}'), "
            f"got '{agent_match.group(1).strip()}'"
        )

    # --- AC7: tools — assign mode, exactly 5 specific tools ---

    def test_tools_exactly_5(self) -> None:
        """AC7: tools list must contain exactly 5 entries."""
        fm = _extract_frontmatter(_read_agent(_AGENT_FILE))
        tools = _extract_tools_from_frontmatter(fm)
        assert len(tools) == 5, (
            f"Expected exactly 5 tools, got {len(tools)}: {tools}"
        )

    def test_tools_are_correct_set(self) -> None:
        """AC7: tools must be: read/readFile, read/viewImage, read/problems, search, vscode/memory."""
        fm = _extract_frontmatter(_read_agent(_AGENT_FILE))
        tools = frozenset(_extract_tools_from_frontmatter(fm))
        assert tools == _EXPECTED_TOOLS, (
            f"Tools mismatch.\n"
            f"  Expected: {sorted(_EXPECTED_TOOLS)}\n"
            f"  Got:      {sorted(tools)}\n"
            f"  Missing:  {sorted(_EXPECTED_TOOLS - tools)}\n"
            f"  Extra:    {sorted(tools - _EXPECTED_TOOLS)}"
        )

    # --- AC8: forbidden tools must be absent ---

    def test_no_execute_tools(self) -> None:
        """AC8: no execute/* tools allowed."""
        fm = _extract_frontmatter(_read_agent(_AGENT_FILE))
        tools = _extract_tools_from_frontmatter(fm)
        found = [t for t in tools if t.startswith("execute/")]
        assert found == [], f"Forbidden execute/* tools found: {found}"

    def test_no_edit_tools(self) -> None:
        """AC8: no edit/* tools allowed."""
        fm = _extract_frontmatter(_read_agent(_AGENT_FILE))
        tools = _extract_tools_from_frontmatter(fm)
        found = [t for t in tools if t.startswith("edit/")]
        assert found == [], f"Forbidden edit/* tools found: {found}"

    def test_no_forbidden_standalone_tools(self) -> None:
        """AC8: no 'agent', 'web', or 'browser' standalone tools allowed."""
        fm = _extract_frontmatter(_read_agent(_AGENT_FILE))
        tools = frozenset(_extract_tools_from_frontmatter(fm))
        found = sorted(tools & _FORBIDDEN_STANDALONE)
        assert not found, f"Forbidden standalone tools found: {found}"

    def test_no_mcp_glob_tools(self) -> None:
        """AC8: no MCP glob tools (e.g., 'owlbear-kanban/*') allowed."""
        fm = _extract_frontmatter(_read_agent(_AGENT_FILE))
        tools = _extract_tools_from_frontmatter(fm)
        found = [t for t in tools if "*" in t or (
            "/" in t and t.split("/")[0] not in {"read", "execute", "edit", "search", "vscode", "web", "browser", "agent"}
        )]
        assert found == [], f"Forbidden MCP glob or unknown-prefix tools found: {found}"


class TestFromAC_CodeReaderBody:
    """AC9-AC12: agents/code-reader.agent.md body must contain required content."""

    def _body(self) -> str:
        return _extract_body(_read_agent(_AGENT_FILE))

    # --- AC9: body covers code-review skill critical steps 6.0-6.6 ---

    def test_body_covers_critical_step_6_0(self) -> None:
        """AC9: body references step 6.0 (test-writer audit)."""
        body = self._body()
        assert "6.0" in body, (
            "Body does not reference code-review step 6.0 (test-writer audit)"
        )

    def test_body_covers_critical_step_6_1(self) -> None:
        """AC9: body references step 6.1 (security review)."""
        body = self._body()
        assert "6.1" in body, (
            "Body does not reference code-review step 6.1 (security review)"
        )

    def test_body_covers_critical_step_6_2(self) -> None:
        """AC9: body references step 6.2 (test integrity)."""
        body = self._body()
        assert "6.2" in body, (
            "Body does not reference code-review step 6.2 (test integrity)"
        )

    def test_body_covers_critical_step_6_3(self) -> None:
        """AC9: body references step 6.3 (test quality)."""
        body = self._body()
        assert "6.3" in body, (
            "Body does not reference code-review step 6.3 (test quality)"
        )

    def test_body_covers_critical_step_6_4(self) -> None:
        """AC9: body references step 6.4 (data safety)."""
        body = self._body()
        assert "6.4" in body, (
            "Body does not reference code-review step 6.4 (data safety)"
        )

    def test_body_covers_critical_step_6_5(self) -> None:
        """AC9: body references step 6.5 (implementation-aware test gap analysis)."""
        body = self._body()
        assert "6.5" in body, (
            "Body does not reference code-review step 6.5 (test gap analysis)"
        )

    def test_body_covers_critical_step_6_6(self) -> None:
        """AC9: body references step 6.6 (necessity check)."""
        body = self._body()
        assert "6.6" in body, (
            "Body does not reference code-review step 6.6 (necessity check)"
        )

    # --- AC9: body covers informational steps 7.1-7.4 ---

    def test_body_covers_informational_step_7_1(self) -> None:
        """AC9: body references step 7.1 (code reading)."""
        body = self._body()
        assert "7.1" in body, (
            "Body does not reference code-review step 7.1 (code reading)"
        )

    def test_body_covers_informational_step_7_2(self) -> None:
        """AC9: body references step 7.2 (documentation)."""
        body = self._body()
        assert "7.2" in body, (
            "Body does not reference code-review step 7.2 (documentation)"
        )

    def test_body_covers_informational_step_7_3(self) -> None:
        """AC9: body references step 7.3 (minor test improvements)."""
        body = self._body()
        assert "7.3" in body, (
            "Body does not reference code-review step 7.3 (minor test improvements)"
        )

    def test_body_covers_informational_step_7_4(self) -> None:
        """AC9: body references step 7.4 (code structure)."""
        body = self._body()
        assert "7.4" in body, (
            "Body does not reference code-review step 7.4 (code structure)"
        )

    # --- AC10: body documents input contract ---

    def test_body_input_contract_has_task_id(self) -> None:
        """AC10: body documents 'task_id' input field."""
        assert "task_id" in self._body(), (
            "Body does not document 'task_id' in the input contract"
        )

    def test_body_input_contract_has_ac_lines(self) -> None:
        """AC10: body documents 'ac_lines' input field."""
        assert "ac_lines" in self._body(), (
            "Body does not document 'ac_lines' in the input contract"
        )

    def test_body_input_contract_has_changed_files(self) -> None:
        """AC10: body documents 'changed_files' input field."""
        assert "changed_files" in self._body(), (
            "Body does not document 'changed_files' in the input contract"
        )

    def test_body_input_contract_has_test_files(self) -> None:
        """AC10: body documents 'test_files' input field."""
        assert "test_files" in self._body(), (
            "Body does not document 'test_files' in the input contract"
        )

    # --- AC11: body defines 8-section output contract ---

    def test_body_output_contract_test_writer_audit(self) -> None:
        """AC11: body defines 'test_writer_audit' output section."""
        assert "test_writer_audit" in self._body(), (
            "Body does not define 'test_writer_audit' in the output contract"
        )

    def test_body_output_contract_security_review(self) -> None:
        """AC11: body defines 'security_review' output section."""
        assert "security_review" in self._body(), (
            "Body does not define 'security_review' in the output contract"
        )

    def test_body_output_contract_test_integrity(self) -> None:
        """AC11: body defines 'test_integrity' output section."""
        assert "test_integrity" in self._body(), (
            "Body does not define 'test_integrity' in the output contract"
        )

    def test_body_output_contract_test_quality(self) -> None:
        """AC11: body defines 'test_quality' output section."""
        assert "test_quality" in self._body(), (
            "Body does not define 'test_quality' in the output contract"
        )

    def test_body_output_contract_data_safety(self) -> None:
        """AC11: body defines 'data_safety' output section."""
        assert "data_safety" in self._body(), (
            "Body does not define 'data_safety' in the output contract"
        )

    def test_body_output_contract_test_gaps(self) -> None:
        """AC11: body defines 'test_gaps' output section."""
        assert "test_gaps" in self._body(), (
            "Body does not define 'test_gaps' in the output contract"
        )

    def test_body_output_contract_necessity_check(self) -> None:
        """AC11: body defines 'necessity_check' output section."""
        assert "necessity_check" in self._body(), (
            "Body does not define 'necessity_check' in the output contract"
        )

    def test_body_output_contract_informational(self) -> None:
        """AC11: body defines 'informational' output section."""
        assert "informational" in self._body(), (
            "Body does not define 'informational' in the output contract"
        )

    # --- AC12: body includes read-only adversarial persona ---

    def test_body_has_readonly_persona(self) -> None:
        """AC12: body persona must include a read-only constraint."""
        body = self._body()
        has_readonly = "read-only" in body.lower() or "read only" in body.lower()
        assert has_readonly, (
            "Body does not include a 'read-only' constraint in the persona (AC12)"
        )

    def test_body_has_adversarial_persona(self) -> None:
        """AC12: body persona must be adversarial (analytical, not helpful)."""
        body = self._body()
        assert "adversarial" in body.lower(), (
            "Body does not include an adversarial analysis persona (AC12)"
        )
