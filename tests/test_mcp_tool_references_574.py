"""RED-phase tests for task #574.

Extends TestFromAC_AgentCommonMcpSyntax (#572) with:
  1. Channel B parameter syntax expansion — edit_task(append_body=..., timestamp=True)
  2. Parametrized tests for the 9 agent-common.instructions.md sections that require
     MCP alternative notes (one expected tool per section entry).

New tests must FAIL on current HEAD (MCP notes not yet added by the builder).
They pass when the #574 builder adds MCP callouts to each section.

Section-to-tool mapping (from AC):
  1. Task coordination callout      → edit_task, show_task, create_task, move_task
  2. Handoff / blocked              → edit_task
  3. Blocking convention            → edit_task
  4. Resolved decision pre-flight   → show_task
  5. Follow-up task quality         → create_task
  6. Placeholder rejection          → create_task
  7. Tool and terminal discipline   → show_task
  8. Loop detection                 → edit_task
  9. Reading rules                  → show_task
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
AGENT_COMMON = ROOT / "instructions" / "agent-common.instructions.md"


# ---- Helpers (mirrors test_mcp_tool_references_483.py) ----


def _strip_frontmatter(text: str) -> str:
    """Return body text after stripping YAML frontmatter (--- ... ---\\n)."""
    match = re.match(r"\A---\n.*?\n---\n?", text, re.DOTALL)
    if match:
        return text[match.end() :]
    return text


def _get_section_content(body: str, section_pattern: str) -> str | None:
    """Extract content from a heading matching section_pattern to the next same-or-higher heading."""
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
# AC: Channel B section — expand existing MCP callout with parameter syntax
# ============================================================


class TestFromAC_AgentCommonChannelBParamSyntax:
    """Channel B section must expand its MCP callout to show edit_task parameter syntax.

    The existing callout only mentions edit_task by name. The AC requires it to
    show specific parameter syntax: edit_task(append_body=..., timestamp=True).
    """

    def _channel_b_section(self) -> str | None:
        body = _strip_frontmatter(AGENT_COMMON.read_text(encoding="utf-8"))
        return _get_section_content(body, r"Channel B")

    def test_channel_b_has_append_body_param(self) -> None:
        """Channel B MCP callout must reference the append_body parameter."""
        section = self._channel_b_section()
        assert section is not None, (
            "Channel B section not found in agent-common.instructions.md"
        )
        assert "append_body" in section, (
            "Channel B section must contain 'append_body' parameter syntax "
            "(e.g. edit_task(append_body=..., timestamp=True)). "
            "The existing callout only names edit_task — it must be expanded."
        )

    def test_channel_b_has_timestamp_param(self) -> None:
        """Channel B MCP callout must reference the timestamp parameter."""
        section = self._channel_b_section()
        assert section is not None, (
            "Channel B section not found in agent-common.instructions.md"
        )
        assert "timestamp" in section, (
            "Channel B section must contain 'timestamp' parameter syntax "
            "(e.g. edit_task(append_body=..., timestamp=True)). "
            "The existing callout only names edit_task — it must be expanded."
        )


# ============================================================
# AC: 9 sections — each must contain its required MCP tool reference
# ============================================================

# Each entry: (section_pattern, expected_tool_name, test_id)
# section_pattern is matched case-insensitively against heading lines.
# Section 1 requires 4 new tools; sections 2-9 require 1 tool each.
_SECTION_MCP_REQUIREMENTS: list[tuple[str, str, str]] = [
    # Section 1 — Task coordination callout expansion (add 4 tools alongside start_work/end_work)
    ("Task coordination", "edit_task", "task-coordination->edit_task"),
    ("Task coordination", "show_task", "task-coordination->show_task"),
    ("Task coordination", "create_task", "task-coordination->create_task"),
    ("Task coordination", "move_task", "task-coordination->move_task"),
    # Section 2 — Handoff / blocked: MCP alternative for handoff CLI code block
    (r"Handoff", "edit_task", "handoff-blocked->edit_task"),
    # Section 3 — Blocking convention: pointer to mcp-kanban for edit_task block/unblock
    (r"Blocking convention", "edit_task", "blocking-convention->edit_task"),
    # Section 4 — Resolved decision pre-flight: show_task as MCP alternative to kanban-md show
    (r"Resolved decision", "show_task", "resolved-decision->show_task"),
    # Section 5 — Follow-up task quality / Subtask creation: create_task as MCP alternative
    (r"Follow-up task quality", "create_task", "followup-task-quality->create_task"),
    # Section 6 — Placeholder and unscoped task rejection: create_task alongside kanban-md create
    (r"Placeholder", "create_task", "placeholder-rejection->create_task"),
    # Section 7 — Tool and terminal discipline: show_task as MCP alternative to kanban-md show
    (r"Tool and terminal discipline", "show_task", "tool-terminal-discipline->show_task"),
    # Section 8 — Loop detection and retry discipline: edit_task with block/release params
    (r"Loop detection", "edit_task", "loop-detection->edit_task"),
    # Section 9 — Reading rules: show_task as MCP alternative to kanban\kanban-md.exe show
    (r"Reading rules", "show_task", "reading-rules->show_task"),
]


@pytest.mark.parametrize(
    ("section_pattern", "expected_tool", "label"),
    _SECTION_MCP_REQUIREMENTS,
    ids=[label for _, _, label in _SECTION_MCP_REQUIREMENTS],
)
class TestFromAC_AgentCommonSectionMcpNotes:
    """Each of the 9 agent-common.instructions.md sections must contain its required MCP tool name.

    These tests verify that the builder added MCP alternative notes (callout blocks or inline
    pointers) to each CLI-heavy section. Tests are contract-level: they check for the presence
    of the required MCP tool name, not the exact callout format.
    """

    def test_section_has_mcp_tool(
        self, section_pattern: str, expected_tool: str, label: str
    ) -> None:
        """Section must contain the required MCP tool name."""
        body = _strip_frontmatter(AGENT_COMMON.read_text(encoding="utf-8"))
        section = _get_section_content(body, section_pattern)
        assert section is not None, (
            f"Section matching '{section_pattern}' not found in "
            f"instructions/agent-common.instructions.md"
        )
        assert expected_tool in section, (
            f"[{label}] Section matching '{section_pattern}' must contain MCP tool "
            f"'{expected_tool}' as an MCP alternative note. "
            f"The builder must add a callout block or inline pointer to this section."
        )
