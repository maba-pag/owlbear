"""Tests for task #318: Create fix-attempt.agent.md with assign-mode tools.

Contract-level verification that share/agents/fix-attempt.agent.md exists with
the required frontmatter and body content per the AC.

AC coverage:
  - AC1:  share/agents/fix-attempt.agent.md exists with valid YAML frontmatter
          and a <persona> section in the body
  - AC2:  Frontmatter: user-invocable: false, disable-model-invocation: true,
          agents: [], model: [Claude Sonnet 4.6 (copilot), GPT-5.3-Codex (copilot)]
  - AC3:  Assigned tools (exactly 9): vscode/memory, execute/runInTerminal,
          execute/getTerminalOutput, execute/awaitTerminal, execute/killTerminal,
          read/readFile, edit/editFiles, edit/createFile, search
  - AC4:  Output contract documents FIXED/FAILED verdict + files_changed + evidence
          (Channel A style)
  - AC5:  Input contract (in workflow section) documents all 5 fields: task_id,
          test_file, source_files, retry_hint, error_summary
  - AC6:  Max 1 internal retry documented (fix-attempt IS the fresh perspective)
  - AC7:  No owlbear-kanban/* tools — never touches kanban board (tool exclusion +
          body constraint)
  - AC8:  validate_agents.py passes on the new file (no unknown/banned tool names)
  - AC9:  hooks.PostToolUse runs lint-changed.ps1 (same as builder.agent.md)
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
_AGENT_FILE = _REPO_ROOT / "share" / "agents" / "fix-attempt.agent.md"
_BUILDER_FILE = _REPO_ROOT / "share" / "agents" / "builder.agent.md"
_VALIDATE_SCRIPT = _REPO_ROOT / "scripts" / "validate_agents.py"

_EXPECTED_TOOLS: frozenset[str] = frozenset(
    {
        "vscode/memory",
        "execute/runInTerminal",
        "execute/getTerminalOutput",
        "execute/awaitTerminal",
        "execute/killTerminal",
        "read/readFile",
        "edit/editFiles",
        "edit/createFile",
        "search",
    }
)

_INPUT_CONTRACT_FIELDS: list[str] = [
    "task_id",
    "test_file",
    "source_files",
    "retry_hint",
    "error_summary",
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
    """Parse tools from YAML frontmatter (handles inline and next-line bracket syntax)."""
    match = re.search(r"^tools:\s*\[([^\]]*)\]", fm, re.MULTILINE)
    if not match:
        match = re.search(r"^tools:\s*\n\s*\[([^\]]*)\]", fm, re.MULTILINE)
    assert match is not None, (
        "tools: key not found or not in bracket syntax in frontmatter"
    )
    raw = match.group(1)
    return [t.strip().strip("'\"") for t in raw.split(",") if t.strip()]


class TestFromAC_FixAttemptFrontmatter:
    """AC1-3, AC7, AC9: share/agents/fix-attempt.agent.md must exist with correct frontmatter."""

    # --- AC1: file exists with valid frontmatter ---

    def test_file_exists(self) -> None:
        """AC1: share/agents/fix-attempt.agent.md must exist on disk."""
        assert _AGENT_FILE.is_file(), (
            "fix-attempt.agent.md does not exist — builder must create it"
        )

    def test_has_valid_yaml_frontmatter(self) -> None:
        """AC1: File must start with --- ... --- YAML frontmatter block."""
        content = _read_agent(_AGENT_FILE)
        assert content.startswith("---\n"), (
            "fix-attempt.agent.md must begin with '---' YAML frontmatter"
        )
        fm = _extract_frontmatter(content)
        assert fm.strip() != "", "Frontmatter block is empty"

    # --- AC2: required scalar frontmatter fields ---

    def test_user_invocable_false(self) -> None:
        """AC2: user-invocable must be 'false'."""
        fm = _extract_frontmatter(_read_agent(_AGENT_FILE))
        match = re.search(r"^user-invocable:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "user-invocable: key not found in frontmatter"
        assert match.group(1).strip() == "false", (
            f"user-invocable must be 'false', got '{match.group(1).strip()}'"
        )

    def test_disable_model_invocation_true(self) -> None:
        """AC2: disable-model-invocation must be 'true'."""
        fm = _extract_frontmatter(_read_agent(_AGENT_FILE))
        match = re.search(r"^disable-model-invocation:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "disable-model-invocation: key not found in frontmatter"
        assert match.group(1).strip() == "true", (
            f"disable-model-invocation must be 'true', got '{match.group(1).strip()}'"
        )

    def test_agents_is_empty_list(self) -> None:
        """AC2: agents must be empty list []."""
        fm = _extract_frontmatter(_read_agent(_AGENT_FILE))
        match = re.search(r"^agents:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "agents: key not found in frontmatter"
        assert match.group(1).strip() == "[]", (
            f"agents must be '[]', got '{match.group(1).strip()}'"
        )

    def test_model_matches_builder(self) -> None:
        """AC2: model must match builder.agent.md (same role tier)."""
        builder_fm = _extract_frontmatter(_read_agent(_BUILDER_FILE))
        builder_match = re.search(r"^model:\s*(.+)$", builder_fm, re.MULTILINE)
        assert builder_match is not None, "Could not read model from builder.agent.md"
        expected = builder_match.group(1).strip()

        agent_fm = _extract_frontmatter(_read_agent(_AGENT_FILE))
        agent_match = re.search(r"^model:\s*(.+)$", agent_fm, re.MULTILINE)
        assert agent_match is not None, "model: key not found in fix-attempt frontmatter"
        assert agent_match.group(1).strip() == expected, (
            f"model must match builder ('{expected}'), "
            f"got '{agent_match.group(1).strip()}'"
        )

    def test_model_contains_claude_sonnet_46(self) -> None:
        """AC2: model must include Claude Sonnet 4.6 (copilot)."""
        fm = _extract_frontmatter(_read_agent(_AGENT_FILE))
        match = re.search(r"^model:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "model: key not found in frontmatter"
        assert "Claude Sonnet 4.6" in match.group(1), (
            "model must include 'Claude Sonnet 4.6 (copilot)'"
        )

    def test_model_contains_gpt_codex(self) -> None:
        """AC2: model must include GPT-5.3-Codex (copilot)."""
        fm = _extract_frontmatter(_read_agent(_AGENT_FILE))
        match = re.search(r"^model:\s*(.+)$", fm, re.MULTILINE)
        assert match is not None, "model: key not found in frontmatter"
        assert "GPT-5.3-Codex" in match.group(1), (
            "model must include 'GPT-5.3-Codex (copilot)'"
        )

    # --- AC3: tools — assign mode, exactly 9 specific tools ---

    def test_tools_exactly_9(self) -> None:
        """AC3: tools list must contain exactly 9 entries."""
        fm = _extract_frontmatter(_read_agent(_AGENT_FILE))
        tools = _extract_tools_from_frontmatter(fm)
        assert len(tools) == 9, (
            f"Expected exactly 9 tools, got {len(tools)}: {tools}"
        )

    def test_tools_are_correct_set(self) -> None:
        """AC3: tools must be the exact 9 specified in AC."""
        fm = _extract_frontmatter(_read_agent(_AGENT_FILE))
        tools = set(_extract_tools_from_frontmatter(fm))
        assert tools == _EXPECTED_TOOLS, (
            f"Tools mismatch.\n  Missing: {_EXPECTED_TOOLS - tools}\n"
            f"  Extra: {tools - _EXPECTED_TOOLS}"
        )

    # --- AC7: no kanban tools (enforced by tool exclusion) ---

    def test_no_kanban_tools_in_frontmatter(self) -> None:
        """AC7: owlbear-kanban/* must not appear in the tools list."""
        fm = _extract_frontmatter(_read_agent(_AGENT_FILE))
        assert "owlbear-kanban" not in fm, (
            "fix-attempt must not include owlbear-kanban/* — never touches kanban board"
        )

    def test_no_memory_mcp_tools_in_frontmatter(self) -> None:
        """Implied by task note: owlbear-memory/* must not appear (short-lived repair agent)."""
        fm = _extract_frontmatter(_read_agent(_AGENT_FILE))
        assert "owlbear-memory" not in fm, (
            "fix-attempt must not include owlbear-memory/* — memory ops are builder concern"
        )

    # --- AC9: PostToolUse hook ---

    def test_posttooluse_hook_present(self) -> None:
        """AC9: hooks.PostToolUse must be defined (same as builder.agent.md)."""
        content = _read_agent(_AGENT_FILE)
        assert "PostToolUse" in content, (
            "fix-attempt.agent.md must define a PostToolUse hook"
        )

    def test_posttooluse_hook_references_lint_script(self) -> None:
        """AC9: PostToolUse hook must run lint-changed.ps1."""
        content = _read_agent(_AGENT_FILE)
        assert "lint-changed.ps1" in content, (
            "PostToolUse hook must reference lint-changed.ps1 (same as builder.agent.md)"
        )


class TestFromAC_FixAttemptBody:
    """AC1, AC4-8: fix-attempt.agent.md body must document persona, contracts, and constraints."""

    # --- AC1: persona section ---

    def test_body_has_persona_section(self) -> None:
        """AC1: Body must include a <persona> section defining the role."""
        body = _extract_body(_read_agent(_AGENT_FILE))
        assert "<persona>" in body, (
            "fix-attempt.agent.md body must contain a <persona> section"
        )

    # --- AC4: output contract — FIXED/FAILED + files_changed + evidence ---

    def test_output_contract_has_fixed_verdict(self) -> None:
        """AC4: Output contract must document FIXED verdict."""
        body = _extract_body(_read_agent(_AGENT_FILE))
        assert "FIXED" in body, (
            "body must document FIXED as an output verdict (Channel A style)"
        )

    def test_output_contract_has_failed_verdict(self) -> None:
        """AC4: Output contract must document FAILED verdict."""
        body = _extract_body(_read_agent(_AGENT_FILE))
        assert "FAILED" in body, (
            "body must document FAILED as an output verdict (Channel A style)"
        )

    def test_output_contract_mentions_files_changed(self) -> None:
        """AC4: Output contract must reference files_changed."""
        body = _extract_body(_read_agent(_AGENT_FILE))
        assert "files_changed" in body, (
            "body output contract must document files_changed field"
        )

    def test_output_contract_mentions_evidence(self) -> None:
        """AC4: Output contract must reference evidence."""
        body = _extract_body(_read_agent(_AGENT_FILE))
        assert "evidence" in body, (
            "body output contract must reference evidence (Channel A style)"
        )

    # --- AC5: input contract — all 5 fields documented ---

    def test_input_contract_has_task_id(self) -> None:
        """AC5: Input contract must document task_id field."""
        body = _extract_body(_read_agent(_AGENT_FILE))
        assert "task_id" in body, (
            "body workflow section must document 'task_id' input field"
        )

    def test_input_contract_has_test_file(self) -> None:
        """AC5: Input contract must document test_file field."""
        body = _extract_body(_read_agent(_AGENT_FILE))
        assert "test_file" in body, (
            "body workflow section must document 'test_file' input field"
        )

    def test_input_contract_has_source_files(self) -> None:
        """AC5: Input contract must document source_files field."""
        body = _extract_body(_read_agent(_AGENT_FILE))
        assert "source_files" in body, (
            "body workflow section must document 'source_files' input field"
        )

    def test_input_contract_has_retry_hint(self) -> None:
        """AC5: Input contract must document retry_hint field."""
        body = _extract_body(_read_agent(_AGENT_FILE))
        assert "retry_hint" in body, (
            "body workflow section must document 'retry_hint' input field"
        )

    def test_input_contract_has_error_summary(self) -> None:
        """AC5: Input contract must document error_summary field."""
        body = _extract_body(_read_agent(_AGENT_FILE))
        assert "error_summary" in body, (
            "body workflow section must document 'error_summary' input field"
        )

    # --- AC6: max 1 internal retry ---

    def test_body_documents_max_one_retry(self) -> None:
        """AC6: Body must document that only 1 internal retry is allowed."""
        body = _extract_body(_read_agent(_AGENT_FILE))
        # Accept "1 retry", "one retry", "max 1", "single retry", etc.
        has_retry_limit = bool(
            re.search(r"\b1\s+retry\b|\bone\s+retry\b|\bmax\s+1\b|\bsingle\s+retry\b|\b1\s+attempt\b", body, re.IGNORECASE)
        )
        assert has_retry_limit, (
            "body must document that max 1 internal retry is permitted"
        )

    # --- AC7: no kanban commands in body ---

    def test_body_prohibits_kanban(self) -> None:
        """AC7: Body must state that kanban board is not touched."""
        body = _extract_body(_read_agent(_AGENT_FILE))
        # Accept "never touches kanban", "no kanban", "not touch kanban", etc.
        has_kanban_constraint = bool(
            re.search(r"kanban", body, re.IGNORECASE)
        )
        assert has_kanban_constraint, (
            "body must document the no-kanban constraint (AC7)"
        )

    # --- AC8: validate_agents.py passes ---

    def test_validate_agents_passes(self) -> None:
        """AC8: validate_agents.py must report zero errors for fix-attempt.agent.md."""
        assert _AGENT_FILE.is_file(), (
            "fix-attempt.agent.md does not exist — cannot run validate_agents.py"
        )
        result = subprocess.run(
            [sys.executable, str(_VALIDATE_SCRIPT), str(_AGENT_FILE)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"validate_agents.py reported errors:\n{result.stderr.strip()}"
        )
