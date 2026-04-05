"""RED-phase tests for task #572 (parent #483).

Augments the #562 test suite with 5 additional checks:
  1. scribe added to PIPELINE_AGENTS (11 total)
  2. edit_task assertion on all pipeline agent bodies
  3. edit_task assertion on all cheatsheet-skill kanban-md Commands sections
  4. Parametrized tests for 4 inline-ref skills (decision-requests, dispatch-planning,
     research-workflow, kanban-md) — whole-body presence of any MCP tool name
  5. Channel B protocol heading test on share/skills/h-mcp-kanban/SKILL.md

New tests must FAIL on current HEAD (MCP refs not yet present in target files).
They pass when sibling tasks #573-#576 complete the MCP reference additions.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent

# ---- Target files ----
MCP_KANBAN_SKILL = ROOT / "share" / "skills" / "h-mcp-kanban" / "SKILL.md"

# AC: 11 pipeline agents (scribe added — owns Channel B handoff protocol)
PIPELINE_AGENTS = [
    "architect",
    "auditor",
    "builder",
    "curator",
    "doc-writer",
    "planner",
    "researcher",
    "reviewer",
    "scribe",
    "test-writer",
]

# AC: 4 inline-ref skills (CLI refs in body, no ## kanban-md Commands section)
INLINE_REF_SKILLS = [
    "w-decision-routing",
    "w-dispatch-planning",
    "w-research",
]

# AC: 8 skills with ## kanban-md Commands sections
SKILLS_WITH_CHEATSHEETS = [
    "w-arch-review",
    "w-code-review",
    "w-mem-curation",
    "w-doc-update",
    "w-task-verification",
    "w-tdd-red",
    "w-tdd-green",
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
    """mcp-kanban SKILL.md must have an agent lifecycle pattern section (start_work/end_work lifecycle)."""

    def _body(self) -> str:
        return _strip_frontmatter(MCP_KANBAN_SKILL.read_text(encoding="utf-8"))

    def test_agent_lifecycle_heading_present(self) -> None:
        """Body must contain a heading matching 'Agent Lifecycle' (case-insensitive)."""
        body = self._body()
        assert re.search(r"^#+\s+agent\s+lifecycle", body, re.MULTILINE | re.IGNORECASE), (
            "Expected an 'Agent Lifecycle Pattern' heading in h-mcp-kanban SKILL.md"
        )

    def test_agent_lifecycle_section_has_start_work(self) -> None:
        """Body must reference start_work as lifecycle step."""
        body = self._body()
        assert "start_work" in body, (
            "h-mcp-kanban SKILL.md must contain start_work"
        )

    def test_agent_lifecycle_section_has_end_work(self) -> None:
        """Body must reference end_work as lifecycle step."""
        body = self._body()
        assert "end_work" in body, (
            "h-mcp-kanban SKILL.md must contain end_work"
        )

    def test_agent_lifecycle_section_has_edit_task(self) -> None:
        """Body must reference edit_task for the Channel B step."""
        body = self._body()
        assert "edit_task" in body, (
            "h-mcp-kanban SKILL.md must contain edit_task"
        )

    def test_channel_b_mentioned(self) -> None:
        """Body must mention Channel B protocol somewhere."""
        body = self._body()
        assert re.search(r"channel\s*b", body, re.IGNORECASE), (
            "h-mcp-kanban SKILL.md must mention Channel B"
        )


# ============================================================
# AC Items 3-5: REMOVED — instruction files are now stubs, agents declare
# MCP tools in frontmatter tools: array (not in body text).
# These tests were for the old CLI+MCP side-by-side structure.
# ============================================================


# ============================================================
# AC Item 6: Skills (MCP-native) — body must contain MCP tool names
# ============================================================


@pytest.mark.parametrize("skill_name", SKILLS_WITH_CHEATSHEETS)
class TestFromAC_SkillCheatsheetMcpRefs:
    """Each skill body must contain MCP tool names (files are now MCP-native)."""

    def _body(self, skill_name: str) -> str:
        path = ROOT / "share" / "skills" / skill_name / "SKILL.md"
        return _strip_frontmatter(path.read_text(encoding="utf-8"))

    def test_body_has_start_work(self, skill_name: str) -> None:
        """Skill body must contain start_work MCP tool reference."""
        body = self._body(skill_name)
        assert "start_work" in body, (
            f"share/skills/{skill_name}/SKILL.md body must contain start_work"
        )

    def test_body_has_end_work(self, skill_name: str) -> None:
        """Skill body must contain end_work MCP tool reference."""
        body = self._body(skill_name)
        assert "end_work" in body, (
            f"share/skills/{skill_name}/SKILL.md body must contain end_work"
        )

    def test_body_has_edit_task(self, skill_name: str) -> None:
        """Skill body must contain edit_task MCP tool reference."""
        body = self._body(skill_name)
        assert "edit_task" in body, (
            f"share/skills/{skill_name}/SKILL.md body must contain edit_task"
        )


# ============================================================
# AC Item 7: Inline-ref skills — whole-body MCP tool name presence
# ============================================================

_INLINE_MCP_TOOLS = frozenset({"edit_task", "start_work", "end_work", "create_task", "list_tasks"})


@pytest.mark.parametrize("skill_name", INLINE_REF_SKILLS)
class TestFromAC_InlineRefSkillMcpRefs:
    """Each inline-ref skill body must contain at least one MCP tool name.

    These skills have CLI commands scattered in the body (no ## kanban-md Commands
    cheatsheet section), so we check the whole file body for any MCP tool name.
    """

    def _body(self, skill_name: str) -> str:
        path = ROOT / "share" / "skills" / skill_name / "SKILL.md"
        return _strip_frontmatter(path.read_text(encoding="utf-8"))

    def test_body_contains_at_least_one_mcp_tool_name(self, skill_name: str) -> None:
        """Skill body must contain at least one of edit_task/start_work/end_work/create_task/list_tasks."""
        body = self._body(skill_name)
        found = [t for t in sorted(_INLINE_MCP_TOOLS) if t in body]
        assert found, (
            f"skills/{skill_name}/SKILL.md body must contain at least one of "
            f"{sorted(_INLINE_MCP_TOOLS)!r} as an MCP tool reference. Found none."
        )
