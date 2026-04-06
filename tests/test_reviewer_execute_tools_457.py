"""Tests for task #457: Remove execute/* tools from reviewer agent.

AC contract under test:
1. reviewer.agent.md tools list contains no execute/* entries
   (change-detecting -- FAIL before #457 implementation)
2. reviewer.agent.md tools list does not contain read/terminalLastCommand
   (change-detecting -- FAIL before #457 implementation)
3. reviewer.agent.md tools list retains exactly the 8 required entries:
   vscode/memory, read/problems, read/readFile, read/viewImage, agent, search,
   owlbear-kanban/*, owlbear-memory/*
   (regression guard -- PASSES throughout)
4. w-code-review/SKILL.md references MCP kanban tools (start_work, end_work,
   show_task, edit_task) for task operations
   (regression guard -- PASSES throughout)
5. Neither code-review/SKILL.md nor w-code-review/SKILL.md references
   kanban-md.exe terminal commands
   (regression guard -- PASSES throughout)
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
REVIEWER_AGENT = ROOT / "share" / "agents" / "reviewer.agent.md"
W_CODE_REVIEW_SKILL = ROOT / "share" / "skills" / "w-code-review" / "SKILL.md"
CODE_REVIEW_SKILL = ROOT / "share" / "skills" / "code-review" / "SKILL.md"

# The 8 tool entries that must remain after #457 removes execute/* and terminalLastCommand
REQUIRED_TOOLS: list[str] = [
    "vscode/memory",
    "read/problems",
    "read/readFile",
    "read/viewImage",
    "agent",
    "search",
    "owlbear-kanban/*",
    "owlbear-memory/*",
]

# The 7 execute/* tool entries that must be removed by #457
EXECUTE_TOOLS_TO_REMOVE: list[str] = [
    "execute/testFailure",
    "execute/getTerminalOutput",
    "execute/awaitTerminal",
    "execute/killTerminal",
    "execute/createAndRunTask",
    "execute/runInTerminal",
    "execute/runTests",
]

# MCP kanban tools that must be referenced in w-code-review/SKILL.md
MCP_KANBAN_TOOLS: list[str] = ["start_work", "end_work", "show_task", "edit_task"]


def _get_frontmatter(path: Path) -> str:
    """Return the YAML frontmatter text between the first pair of --- delimiters."""
    content = path.read_text(encoding="utf-8")
    match = re.search(r"\A---\n(.*?)\n---", content, re.DOTALL)
    if match is None:
        raise ValueError(f"No frontmatter found in {path}")
    return match.group(1)


def _parse_yaml_inline_list(frontmatter: str, field: str) -> list[str]:
    """Parse an inline YAML list from frontmatter for the given field name.

    Handles both same-line syntax (field: [a, b]) and next-line syntax:
        field:
          [a, b]
    """
    pattern = rf"^{field}:\s*(?:\n\s*)?\[(.+?)\]"
    match = re.search(pattern, frontmatter, re.MULTILINE | re.DOTALL)
    if match is None:
        return []
    raw = match.group(1)
    entries = [entry.strip().strip("'\"") for entry in raw.split(",")]
    return [e for e in entries if e]


class TestFromAC_ReviewerNoExecuteTools:
    """AC1: reviewer.agent.md tools list must not contain any execute/* entries.

    Change-detecting -- FAIL before #457 implementation, PASS after.
    """

    def test_tools_contains_no_execute_test_failure(self) -> None:
        """execute/testFailure must be removed from reviewer tools."""
        fm = _get_frontmatter(REVIEWER_AGENT)
        tools = _parse_yaml_inline_list(fm, "tools")
        assert "execute/testFailure" not in tools, (
            "reviewer.agent.md tools still contains execute/testFailure -- "
            "must be removed by #457."
        )

    def test_tools_contains_no_execute_get_terminal_output(self) -> None:
        """execute/getTerminalOutput must be removed from reviewer tools."""
        fm = _get_frontmatter(REVIEWER_AGENT)
        tools = _parse_yaml_inline_list(fm, "tools")
        assert "execute/getTerminalOutput" not in tools, (
            "reviewer.agent.md tools still contains execute/getTerminalOutput -- "
            "must be removed by #457."
        )

    def test_tools_contains_no_execute_await_terminal(self) -> None:
        """execute/awaitTerminal must be removed from reviewer tools."""
        fm = _get_frontmatter(REVIEWER_AGENT)
        tools = _parse_yaml_inline_list(fm, "tools")
        assert "execute/awaitTerminal" not in tools, (
            "reviewer.agent.md tools still contains execute/awaitTerminal -- "
            "must be removed by #457."
        )

    def test_tools_contains_no_execute_kill_terminal(self) -> None:
        """execute/killTerminal must be removed from reviewer tools."""
        fm = _get_frontmatter(REVIEWER_AGENT)
        tools = _parse_yaml_inline_list(fm, "tools")
        assert "execute/killTerminal" not in tools, (
            "reviewer.agent.md tools still contains execute/killTerminal -- "
            "must be removed by #457."
        )

    def test_tools_contains_no_execute_create_and_run_task(self) -> None:
        """execute/createAndRunTask must be removed from reviewer tools."""
        fm = _get_frontmatter(REVIEWER_AGENT)
        tools = _parse_yaml_inline_list(fm, "tools")
        assert "execute/createAndRunTask" not in tools, (
            "reviewer.agent.md tools still contains execute/createAndRunTask -- "
            "must be removed by #457."
        )

    def test_tools_contains_no_execute_run_in_terminal(self) -> None:
        """execute/runInTerminal must be removed from reviewer tools."""
        fm = _get_frontmatter(REVIEWER_AGENT)
        tools = _parse_yaml_inline_list(fm, "tools")
        assert "execute/runInTerminal" not in tools, (
            "reviewer.agent.md tools still contains execute/runInTerminal -- "
            "must be removed by #457."
        )

    def test_tools_contains_no_execute_run_tests(self) -> None:
        """execute/runTests must be removed from reviewer tools."""
        fm = _get_frontmatter(REVIEWER_AGENT)
        tools = _parse_yaml_inline_list(fm, "tools")
        assert "execute/runTests" not in tools, (
            "reviewer.agent.md tools still contains execute/runTests -- "
            "must be removed by #457."
        )

    def test_tools_contains_no_execute_wildcard_entries(self) -> None:
        """No execute/* entries of any kind may remain in reviewer tools."""
        fm = _get_frontmatter(REVIEWER_AGENT)
        tools = _parse_yaml_inline_list(fm, "tools")
        execute_tools = [t for t in tools if t.startswith("execute/")]
        assert execute_tools == [], (
            f"reviewer.agent.md tools still contains execute/* entries: {execute_tools}. "
            "All 7 execute/* tools must be removed by #457."
        )


class TestFromAC_ReviewerNoTerminalLastCommand:
    """AC2: reviewer.agent.md tools list must not contain read/terminalLastCommand.

    Change-detecting -- FAIL before #457 implementation, PASS after.
    """

    def test_tools_does_not_contain_terminal_last_command(self) -> None:
        """read/terminalLastCommand must be removed from reviewer tools."""
        fm = _get_frontmatter(REVIEWER_AGENT)
        tools = _parse_yaml_inline_list(fm, "tools")
        assert "read/terminalLastCommand" not in tools, (
            "reviewer.agent.md tools still contains read/terminalLastCommand -- "
            "must be removed by #457."
        )


class TestFromAC_ReviewerRetainsRequiredTools:
    """AC3: reviewer.agent.md must retain all 8 required tool entries after #457.

    Regression guard -- PASSES throughout (before and after #457).
    """

    def test_tools_retains_vscode_memory(self) -> None:
        fm = _get_frontmatter(REVIEWER_AGENT)
        tools = _parse_yaml_inline_list(fm, "tools")
        assert "vscode/memory" in tools, (
            "reviewer.agent.md tools missing required entry: vscode/memory."
        )

    def test_tools_retains_read_problems(self) -> None:
        fm = _get_frontmatter(REVIEWER_AGENT)
        tools = _parse_yaml_inline_list(fm, "tools")
        assert "read/problems" in tools, (
            "reviewer.agent.md tools missing required entry: read/problems."
        )

    def test_tools_retains_read_read_file(self) -> None:
        fm = _get_frontmatter(REVIEWER_AGENT)
        tools = _parse_yaml_inline_list(fm, "tools")
        assert "read/readFile" in tools, (
            "reviewer.agent.md tools missing required entry: read/readFile."
        )

    def test_tools_retains_read_view_image(self) -> None:
        fm = _get_frontmatter(REVIEWER_AGENT)
        tools = _parse_yaml_inline_list(fm, "tools")
        assert "read/viewImage" in tools, (
            "reviewer.agent.md tools missing required entry: read/viewImage."
        )

    def test_tools_retains_agent(self) -> None:
        fm = _get_frontmatter(REVIEWER_AGENT)
        tools = _parse_yaml_inline_list(fm, "tools")
        assert "agent" in tools, (
            "reviewer.agent.md tools missing required entry: agent."
        )

    def test_tools_retains_search(self) -> None:
        fm = _get_frontmatter(REVIEWER_AGENT)
        tools = _parse_yaml_inline_list(fm, "tools")
        assert "search" in tools, (
            "reviewer.agent.md tools missing required entry: search."
        )

    def test_tools_retains_owlbear_kanban_wildcard(self) -> None:
        fm = _get_frontmatter(REVIEWER_AGENT)
        tools = _parse_yaml_inline_list(fm, "tools")
        assert "owlbear-kanban/*" in tools, (
            "reviewer.agent.md tools missing required entry: owlbear-kanban/*."
        )

    def test_tools_retains_owlbear_memory_wildcard(self) -> None:
        fm = _get_frontmatter(REVIEWER_AGENT)
        tools = _parse_yaml_inline_list(fm, "tools")
        assert "owlbear-memory/*" in tools, (
            "reviewer.agent.md tools missing required entry: owlbear-memory/*."
        )

    def test_all_8_required_tools_present(self) -> None:
        """Aggregate guard: all 8 required entries must be present simultaneously."""
        fm = _get_frontmatter(REVIEWER_AGENT)
        tools = _parse_yaml_inline_list(fm, "tools")
        missing = [t for t in REQUIRED_TOOLS if t not in tools]
        assert not missing, (
            f"reviewer.agent.md tools missing required entries: {missing}. "
            f"Current tools: {tools}"
        )


class TestFromAC_WCodeReviewSkillMcpKanbanTools:
    """AC4: w-code-review/SKILL.md must reference MCP kanban tools for task operations.

    Regression guard -- PASSES throughout.
    """

    def test_w_code_review_skill_has_start_work(self) -> None:
        content = W_CODE_REVIEW_SKILL.read_text(encoding="utf-8")
        assert "start_work" in content, (
            "w-code-review/SKILL.md does not reference 'start_work'. "
            "MCP kanban tools must be used for all task operations."
        )

    def test_w_code_review_skill_has_end_work(self) -> None:
        content = W_CODE_REVIEW_SKILL.read_text(encoding="utf-8")
        assert "end_work" in content, (
            "w-code-review/SKILL.md does not reference 'end_work'. "
            "MCP kanban tools must be used for all task operations."
        )

    def test_w_code_review_skill_has_show_task(self) -> None:
        content = W_CODE_REVIEW_SKILL.read_text(encoding="utf-8")
        assert "show_task" in content, (
            "w-code-review/SKILL.md does not reference 'show_task'. "
            "MCP kanban tools must be used for all task operations."
        )

    def test_w_code_review_skill_has_edit_task(self) -> None:
        content = W_CODE_REVIEW_SKILL.read_text(encoding="utf-8")
        assert "edit_task" in content, (
            "w-code-review/SKILL.md does not reference 'edit_task'. "
            "MCP kanban tools must be used for all task operations."
        )


class TestFromAC_SkillsNoKanbanMdExe:
    """AC5: code-review/SKILL.md and w-code-review/SKILL.md must not reference kanban-md.exe.

    Regression guard -- PASSES throughout.
    """

    def test_code_review_skill_has_no_kanban_md_exe(self) -> None:
        content = CODE_REVIEW_SKILL.read_text(encoding="utf-8")
        assert "kanban-md.exe" not in content, (
            "code-review/SKILL.md references 'kanban-md.exe' -- legacy terminal command. "
            "All kanban operations must use MCP tools."
        )

    def test_w_code_review_skill_has_no_kanban_md_exe(self) -> None:
        content = W_CODE_REVIEW_SKILL.read_text(encoding="utf-8")
        assert "kanban-md.exe" not in content, (
            "w-code-review/SKILL.md references 'kanban-md.exe' -- legacy terminal command. "
            "All kanban operations must use MCP tools."
        )


def _extract_fallback_section_n(content: str, n: int) -> str:
    """Extract the Nth (0-indexed) 'Fallback: Quality-Runner Unavailable' section body.

    Returns the text from immediately after the heading up to the next heading
    (any ## level).  Returns an empty string if the Nth section does not exist.
    """
    parts = re.split(r"#### Fallback: Quality-Runner Unavailable", content)
    if n + 1 >= len(parts):
        return ""
    section = parts[n + 1]
    stop = re.search(r"\n##", section)
    if stop:
        section = section[: stop.start()]
    return section


class TestFromAC_WCodeReviewFallbackBlockInstruction:
    """AC4: w-code-review/SKILL.md fallback sections (Steps 2, 3, 4) must not contain
    uv run terminal commands and must include a BLOCK instruction via end_work.

    Change-detecting -- FAIL before #457 implementation when uv run commands are
    still present and the BLOCK instruction is absent.
    """

    def test_step2_fallback_has_no_uv_run_commands(self) -> None:
        """Step 2 fallback must not contain uv run terminal commands."""
        content = W_CODE_REVIEW_SKILL.read_text(encoding="utf-8")
        section = _extract_fallback_section_n(content, 0)
        assert "uv run" not in section, (
            "w-code-review/SKILL.md Step 2 fallback still contains 'uv run' terminal "
            "commands. #457 must replace them with a BLOCK instruction."
        )

    def test_step2_fallback_has_block_instruction(self) -> None:
        """Step 2 fallback must include an end_work BLOCK instruction."""
        content = W_CODE_REVIEW_SKILL.read_text(encoding="utf-8")
        section = _extract_fallback_section_n(content, 0)
        has_block = 'outcome="block"' in section or "outcome='block'" in section
        assert has_block, (
            "w-code-review/SKILL.md Step 2 fallback missing BLOCK instruction "
            '(end_work(outcome="block", ...)). #457 must add it.'
        )

    def test_step3_fallback_has_no_uv_run_commands(self) -> None:
        """Step 3 fallback must not contain uv run terminal commands."""
        content = W_CODE_REVIEW_SKILL.read_text(encoding="utf-8")
        section = _extract_fallback_section_n(content, 1)
        assert "uv run" not in section, (
            "w-code-review/SKILL.md Step 3 fallback still contains 'uv run' terminal "
            "commands. #457 must replace them with a BLOCK instruction."
        )

    def test_step3_fallback_has_block_instruction(self) -> None:
        """Step 3 fallback must include an end_work BLOCK instruction."""
        content = W_CODE_REVIEW_SKILL.read_text(encoding="utf-8")
        section = _extract_fallback_section_n(content, 1)
        has_block = 'outcome="block"' in section or "outcome='block'" in section
        assert has_block, (
            "w-code-review/SKILL.md Step 3 fallback missing BLOCK instruction "
            '(end_work(outcome="block", ...)). #457 must add it.'
        )

    def test_step4_fallback_has_no_uv_run_commands(self) -> None:
        """Step 4 fallback must not contain uv run terminal commands."""
        content = W_CODE_REVIEW_SKILL.read_text(encoding="utf-8")
        section = _extract_fallback_section_n(content, 2)
        assert "uv run" not in section, (
            "w-code-review/SKILL.md Step 4 fallback still contains 'uv run' terminal "
            "commands. #457 must replace them with a BLOCK instruction."
        )

    def test_step4_fallback_has_block_instruction(self) -> None:
        """Step 4 fallback must include an end_work BLOCK instruction."""
        content = W_CODE_REVIEW_SKILL.read_text(encoding="utf-8")
        section = _extract_fallback_section_n(content, 2)
        has_block = 'outcome="block"' in section or "outcome='block'" in section
        assert has_block, (
            "w-code-review/SKILL.md Step 4 fallback missing BLOCK instruction "
            '(end_work(outcome="block", ...)). #457 must add it.'
        )


class TestFromAC_CodeReviewFallbackBlockInstruction:
    """AC5: code-review/SKILL.md fallback section must not contain uv run terminal
    commands and must include a BLOCK instruction via end_work.

    Change-detecting -- FAIL before #457 implementation.
    """

    def test_fallback_has_no_uv_run_commands(self) -> None:
        """code-review fallback must not contain uv run terminal commands."""
        content = CODE_REVIEW_SKILL.read_text(encoding="utf-8")
        section = _extract_fallback_section_n(content, 0)
        assert "uv run" not in section, (
            "code-review/SKILL.md fallback still contains 'uv run' terminal commands. "
            "#457 must replace them with a BLOCK instruction."
        )

    def test_fallback_has_block_instruction(self) -> None:
        """code-review fallback must include an end_work BLOCK instruction."""
        content = CODE_REVIEW_SKILL.read_text(encoding="utf-8")
        section = _extract_fallback_section_n(content, 0)
        has_block = 'outcome="block"' in section or "outcome='block'" in section
        assert has_block, (
            "code-review/SKILL.md fallback missing BLOCK instruction "
            '(end_work(outcome="block", ...)). #457 must add it.'
        )
