"""Failing RED-phase tests for task #562 (parent #483).

Validates that MCP tool references exist alongside CLI in all target files:
  - skills/mcp-kanban/SKILL.md — agent workflow pattern section
  - instructions/agent-common.instructions.md — Channel B and task coordination sections
  - instructions/research-docs.instructions.md — MCP syntax alongside CLI kanban refs
  - 10 pipeline agent .agent.md files — MCP tool examples in body text
  - 8 skill SKILL.md files with ## kanban-md Commands — MCP tool rows alongside CLI

All tests must FAIL on current HEAD (zero MCP refs in target files).
They pass when sibling tasks #563-#566 complete the MCP reference additions.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent

# ---- Target files ----
MCP_KANBAN_SKILL = ROOT / "skills" / "mcp-kanban" / "SKILL.md"
AGENT_COMMON = ROOT / "instructions" / "agent-common.instructions.md"
RESEARCH_DOCS = ROOT / "instructions" / "research-docs.instructions.md"

# AC: 10 pipeline agents (scribe excluded — utility agent, no pipeline stage ownership)
PIPELINE_AGENTS = [
    "architect",
    "auditor",
    "builder",
    "curator",
    "kanban-planner",
    "planner",
    "researcher",
    "reviewer",
    "test-writer",
    "writer",
]

# AC: 8 skills with ## kanban-md Commands sections
SKILLS_WITH_CHEATSHEETS = [
    "arch-review",
    "code-review",
    "curation-workflow",
    "docs-gate",
    "task-decomposition",
    "task-verification",
    "tdd-red",
    "tdd-workflow",
]


# ---- Helpers ----


def _strip_frontmatter(text: str) -> str:
    """Return body text after stripping YAML frontmatter (--- ... ---\\n)."""
    match = re.match(r"\A---\n.*?\n---\n?", text, re.DOTALL)
    if match:
        return text[match.end():]
    return text


def _get_section_content(body: str, section_pattern: str) -> str | None:
    """Extract content from a heading matching section_pattern to next same-or-higher heading.

    Returns the full section text (including the matched heading line) or None
    if no matching heading is found.
    """
    lines = body.splitlines()
    heading_level: int | None = None
    collecting = False
    section_lines: list[str] = []

    for line in lines:
        if not collecting:
            hm = re.match(r"^(#+)\s+", line)
            if hm and re.search(section_pattern, line, re.IGNORECASE):
                heading_level = len(hm.group(1))
                collecting = True
                section_lines.append(line)
        else:
            hm = re.match(r"^(#+)\s+", line)
            if hm and len(hm.group(1)) <= heading_level:  # type: ignore[operator]
                break
            section_lines.append(line)

    return "\n".join(section_lines) if collecting else None


# ============================================================
# AC Item 2: mcp-kanban SKILL.md — agent workflow pattern section
# ============================================================


class TestFromAC_McpKanbanSkillWorkflowPattern:
    """mcp-kanban SKILL.md must gain an agent workflow pattern section (start_work/end_work lifecycle)."""

    def _body(self) -> str:
        return _strip_frontmatter(MCP_KANBAN_SKILL.read_text(encoding="utf-8"))

    def test_agent_workflow_heading_present(self) -> None:
        """Body must contain a heading matching 'Agent Workflow' (case-insensitive)."""
        body = self._body()
        assert re.search(r"^#+\s+agent\s+workflow", body, re.MULTILINE | re.IGNORECASE), (
            "Expected an '## Agent Workflow' heading in skills/mcp-kanban/SKILL.md body"
        )

    def test_agent_workflow_section_has_start_work(self) -> None:
        """Agent workflow section must reference start_work as lifecycle step."""
        section = _get_section_content(self._body(), r"agent\s+workflow")
        assert section is not None, "Agent Workflow section not found in mcp-kanban SKILL.md"
        assert "start_work" in section, (
            "Agent Workflow section must contain start_work"
        )

    def test_agent_workflow_section_has_end_work(self) -> None:
        """Agent workflow section must reference end_work as lifecycle step."""
        section = _get_section_content(self._body(), r"agent\s+workflow")
        assert section is not None, "Agent Workflow section not found in mcp-kanban SKILL.md"
        assert "end_work" in section, (
            "Agent Workflow section must contain end_work"
        )

    def test_agent_workflow_section_has_edit_task(self) -> None:
        """Agent workflow section must reference edit_task for the Channel B step."""
        section = _get_section_content(self._body(), r"agent\s+workflow")
        assert section is not None, "Agent Workflow section not found in mcp-kanban SKILL.md"
        assert "edit_task" in section, (
            "Agent Workflow section must contain edit_task (Channel B intermediate step)"
        )


# ============================================================
# AC Item 3: agent-common.instructions.md — MCP syntax in Channel B and task coordination
# ============================================================


class TestFromAC_AgentCommonMcpSyntax:
    """agent-common.instructions.md must have MCP tool syntax in Channel B and task coordination sections."""

    def _body(self) -> str:
        return _strip_frontmatter(AGENT_COMMON.read_text(encoding="utf-8"))

    def test_channel_b_section_has_edit_task(self) -> None:
        """Channel B section must contain edit_task MCP tool reference."""
        section = _get_section_content(self._body(), r"Channel B")
        assert section is not None, "Channel B section not found in agent-common.instructions.md"
        assert "edit_task" in section, (
            "Channel B section must contain edit_task MCP tool reference"
        )

    def test_channel_b_section_has_end_work(self) -> None:
        """Channel B section must contain end_work MCP tool reference."""
        section = _get_section_content(self._body(), r"Channel B")
        assert section is not None, "Channel B section not found in agent-common.instructions.md"
        assert "end_work" in section, (
            "Channel B section must contain end_work MCP tool reference"
        )

    def test_task_coordination_section_has_start_work(self) -> None:
        """Task coordination section must contain start_work MCP tool reference."""
        section = _get_section_content(self._body(), r"Task coordination")
        assert section is not None, (
            "Task coordination section not found in agent-common.instructions.md"
        )
        assert "start_work" in section, (
            "Task coordination section must contain start_work MCP tool reference"
        )

    def test_task_coordination_section_has_end_work(self) -> None:
        """Task coordination section must contain end_work MCP tool reference."""
        section = _get_section_content(self._body(), r"Task coordination")
        assert section is not None, (
            "Task coordination section not found in agent-common.instructions.md"
        )
        assert "end_work" in section, (
            "Task coordination section must contain end_work MCP tool reference"
        )


# ============================================================
# AC Item 4: research-docs.instructions.md — MCP syntax alongside CLI kanban refs
# ============================================================


class TestFromAC_ResearchDocsMcpSyntax:
    """research-docs.instructions.md must contain MCP syntax where CLI kanban references exist."""

    def _body(self) -> str:
        return _strip_frontmatter(RESEARCH_DOCS.read_text(encoding="utf-8"))

    def test_has_create_task_mcp_tool(self) -> None:
        """File must contain create_task MCP tool reference alongside kanban-md create CLI."""
        body = self._body()
        assert "create_task" in body, (
            "research-docs.instructions.md must contain create_task MCP equivalent "
            "alongside existing kanban-md create CLI reference"
        )

    def test_has_start_work_reference(self) -> None:
        """File must contain start_work MCP tool reference."""
        body = self._body()
        assert "start_work" in body, (
            "research-docs.instructions.md must contain start_work MCP tool reference"
        )

    def test_has_end_work_reference(self) -> None:
        """File must contain end_work MCP tool reference."""
        body = self._body()
        assert "end_work" in body, (
            "research-docs.instructions.md must contain end_work MCP tool reference"
        )


# ============================================================
# AC Item 5: Pipeline agent .agent.md — MCP tool examples in body text
# ============================================================


@pytest.mark.parametrize("agent_name", PIPELINE_AGENTS)
class TestFromAC_PipelineAgentMcpBodyRefs:
    """Each pipeline agent .agent.md must contain MCP tool examples in body text (not just tools: YAML)."""

    def _agent_body(self, agent_name: str) -> str:
        path = ROOT / "agents" / f"{agent_name}.agent.md"
        return _strip_frontmatter(path.read_text(encoding="utf-8"))

    def test_agent_body_has_start_work(self, agent_name: str) -> None:
        """Agent body text must contain start_work MCP tool reference."""
        body = self._agent_body(agent_name)
        assert "start_work" in body, (
            f"agents/{agent_name}.agent.md body must contain start_work MCP tool reference"
        )

    def test_agent_body_has_end_work(self, agent_name: str) -> None:
        """Agent body text must contain end_work MCP tool reference."""
        body = self._agent_body(agent_name)
        assert "end_work" in body, (
            f"agents/{agent_name}.agent.md body must contain end_work MCP tool reference"
        )


# ============================================================
# AC Item 6: Skill ## kanban-md Commands sections — MCP tool rows alongside CLI
# ============================================================


@pytest.mark.parametrize("skill_name", SKILLS_WITH_CHEATSHEETS)
class TestFromAC_SkillCheatsheetMcpRefs:
    """Each skill with ## kanban-md Commands must have MCP tool rows/columns alongside CLI."""

    def _kanban_commands_section(self, skill_name: str) -> str | None:
        path = ROOT / "skills" / skill_name / "SKILL.md"
        body = _strip_frontmatter(path.read_text(encoding="utf-8"))
        return _get_section_content(body, r"kanban-md Commands")

    def test_kanban_commands_section_has_start_work(self, skill_name: str) -> None:
        """## kanban-md Commands section must contain start_work MCP tool reference."""
        section = self._kanban_commands_section(skill_name)
        assert section is not None, (
            f"## kanban-md Commands section not found in skills/{skill_name}/SKILL.md"
        )
        assert "start_work" in section, (
            f"skills/{skill_name}/SKILL.md ## kanban-md Commands must contain start_work"
        )

    def test_kanban_commands_section_has_end_work(self, skill_name: str) -> None:
        """## kanban-md Commands section must contain end_work MCP tool reference."""
        section = self._kanban_commands_section(skill_name)
        assert section is not None, (
            f"## kanban-md Commands section not found in skills/{skill_name}/SKILL.md"
        )
        assert "end_work" in section, (
            f"skills/{skill_name}/SKILL.md ## kanban-md Commands must contain end_work"
        )
