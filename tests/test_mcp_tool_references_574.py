"""RED-phase tests for task #574.

Targets r-pipeline-protocol/SKILL.md (v2 target after v2 refactor deleted
instructions/agent-common.instructions.md).

Tests verify that the builder adds MCP tool callouts to 6 sections:
  1. Resolved Decision Pre-flight  → show_task
  2. Follow-up Task Quality        → create_task
  3. Channel B                     → append_body + timestamp parameter syntax
  4. Blocking Convention           → edit_task(unblock=True)
  5. Handoff                       → edit_task(append_body=...)
  6. Reading Rules                 → show_task

All 8 tests must FAIL on current HEAD (MCP notes not yet added by the builder).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
PIPELINE_PROTOCOL = ROOT / "share" / "skills" / "r-pipeline-protocol" / "SKILL.md"


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


class TestFromAC_PipelineProtocolMcpPointers:
    """r-pipeline-protocol/SKILL.md must have MCP callout notes in 6 sections.

    Channel B already names edit_task; these tests verify the builder expands
    it with append_body/timestamp parameter syntax and adds show_task / create_task
    / edit_task(unblock) callouts to the 5 other sections.
    """

    def _section(self, pattern: str) -> str | None:
        body = _strip_frontmatter(PIPELINE_PROTOCOL.read_text(encoding="utf-8"))
        return _get_section_content(body, pattern)

    # ---- Explicit Channel B parameter tests (2) ----

    def test_channel_b_has_append_body_param(self) -> None:
        """Channel B MCP callout must reference the append_body parameter."""
        section = self._section(r"Channel B")
        assert section is not None, (
            "Channel B section not found in r-pipeline-protocol/SKILL.md"
        )
        assert "append_body" in section, (
            "Channel B section must contain 'append_body' parameter syntax "
            "(e.g. edit_task(append_body=..., timestamp=True)). "
            "The existing pointer only names edit_task — it must be expanded."
        )

    def test_channel_b_has_timestamp_param(self) -> None:
        """Channel B MCP callout must reference the timestamp parameter."""
        section = self._section(r"Channel B")
        assert section is not None, (
            "Channel B section not found in r-pipeline-protocol/SKILL.md"
        )
        assert "timestamp" in section, (
            "Channel B section must contain 'timestamp' parameter syntax "
            "(e.g. edit_task(append_body=..., timestamp=True)). "
            "The existing pointer only names edit_task — it must be expanded."
        )

    # ---- Parametrized section MCP tool tests (6) ----

    @pytest.mark.parametrize(
        ("section_pattern", "expected_tool", "label"),
        [
            # AC item 1 — Resolved Decision Pre-flight: add show_task MCP note
            ("Resolved Decision", "show_task", "resolved-decision->show_task"),
            # AC item 2 — Follow-up Task Quality: add create_task MCP note
            ("Follow-up Task Quality", "create_task", "followup-task-quality->create_task"),
            # AC item 3 — Channel B: expand edit_task pointer with append_body param syntax
            ("Channel B", "append_body", "channel-b->append_body"),
            # AC item 4 — Blocking Convention: add edit_task(unblock=True) alongside end_work
            ("Blocking Convention", "unblock", "blocking-convention->unblock"),
            # AC item 5 — Handoff: add edit_task(append_body=...) MCP note
            ("Handoff", "edit_task", "handoff->edit_task"),
            # AC item 6 — Reading Rules: add show_task MCP note for agent task-body reads
            ("Reading Rules", "show_task", "reading-rules->show_task"),
        ],
        ids=[
            "resolved-decision->show_task",
            "followup-task-quality->create_task",
            "channel-b->append_body",
            "blocking-convention->unblock",
            "handoff->edit_task",
            "reading-rules->show_task",
        ],
    )
    def test_section_has_mcp_tool(
        self, section_pattern: str, expected_tool: str, label: str
    ) -> None:
        """Each r-pipeline-protocol section must contain its required MCP tool name."""
        body = _strip_frontmatter(PIPELINE_PROTOCOL.read_text(encoding="utf-8"))
        section = _get_section_content(body, section_pattern)
        assert section is not None, (
            f"Section matching '{section_pattern}' not found in "
            f"r-pipeline-protocol/SKILL.md"
        )
        assert expected_tool in section, (
            f"[{label}] Section matching '{section_pattern}' must contain "
            f"'{expected_tool}' as an MCP callout. "
            f"The builder must add a '> **MCP equivalent:** ...' note to this section."
        )
