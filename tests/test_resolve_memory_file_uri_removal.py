"""Failing tests for task #80: Replace unsupported vscode/resolveMemoryFileUri tool in curator.

Covers:
  - curator.agent.md tool list no longer includes vscode/resolveMemoryFileUri
  - No .agent.md file anywhere in the workspace references vscode/resolveMemoryFileUri
  - docs/research/agent-md-format.md section 4 table row for vscode/resolveMemoryFileUri
    shows REMOVED status, not NO

All tests fail on current HEAD because curator.agent.md lists vscode/resolveMemoryFileUri
at line 10, and agent-md-format.md section 4 still records the tool availability as "NO".
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
CURATOR_AGENT = ROOT / "share" / "agents" / "curator.agent.md"
AGENTS_DIR = ROOT / "share" / "agents"
AGENT_MD_FORMAT_DOC = ROOT / "docs" / "research" / "agent-md-format.md"

UNSUPPORTED_TOOL = "vscode/resolveMemoryFileUri"


def _read_frontmatter(path: Path) -> str:
    """Return the YAML frontmatter block from an .agent.md file."""
    content = path.read_text(encoding="utf-8")
    match = re.search(r"\A---\n(.*?)\n---", content, re.DOTALL)
    if match is None:
        raise ValueError(f"No YAML frontmatter found in {path}")
    return match.group(1)


def _find_table_row(doc_path: Path, cell_text: str) -> str | None:
    """Return the first markdown table row that contains cell_text, or None."""
    for line in doc_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("|") and cell_text in line:
            return line
    return None


class TestFromAC_CuratorToolListCleanup:
    """AC: Remove vscode/resolveMemoryFileUri from curator.agent.md tool list (AC1 & AC2)."""

    def test_curator_agent_md_tool_list_excludes_resolve_memory_file_uri(self) -> None:
        """curator.agent.md YAML frontmatter must not list vscode/resolveMemoryFileUri.

        Fails until the line is removed from the tools block in the frontmatter.
        """
        frontmatter = _read_frontmatter(CURATOR_AGENT)
        assert UNSUPPORTED_TOOL not in frontmatter, (
            f"curator.agent.md still lists the unsupported tool {UNSUPPORTED_TOOL!r}. "
            "Remove this entry from the tools block."
        )

    def test_no_agent_md_file_references_resolve_memory_file_uri(self) -> None:
        """No .agent.md file in agents/ may reference vscode/resolveMemoryFileUri.

        Verifies AC2: grep across the agents directory returns zero matches.
        Fails as long as curator.agent.md (or any other agent) contains the tool name.
        """
        offending: list[str] = []
        for agent_file in sorted(AGENTS_DIR.glob("*.agent.md")):
            if UNSUPPORTED_TOOL in agent_file.read_text(encoding="utf-8"):
                offending.append(agent_file.name)
        assert offending == [], (
            f"The following .agent.md files still reference {UNSUPPORTED_TOOL!r}: "
            f"{offending}. Remove all occurrences."
        )


class TestFromAC_AgentMdFormatDocUpdate:
    """AC: Update docs/research/agent-md-format.md section 4 table to show REMOVED (AC4)."""

    def test_section4_table_row_shows_removed_status(self) -> None:
        """The vscode/resolveMemoryFileUri row in the section 4 table must show 'REMOVED'.

        Fails until the Available column is updated from 'NO' to 'REMOVED ...'.
        """
        row = _find_table_row(AGENT_MD_FORMAT_DOC, UNSUPPORTED_TOOL)
        assert row is not None, (
            f"No table row containing {UNSUPPORTED_TOOL!r} found in {AGENT_MD_FORMAT_DOC}."
        )
        assert "REMOVED" in row, (
            f"Row for {UNSUPPORTED_TOOL!r} does not contain 'REMOVED'. "
            f"Current row: {row!r}. Update the Available column to 'REMOVED ...'."
        )

    def test_section4_table_row_not_still_marked_no(self) -> None:
        """The vscode/resolveMemoryFileUri row must not have 'NO' as its primary status.

        Current state: '| ... | — | NO — not documented ...'
        Required state: '| ... | — | REMOVED ...'
        Fails until the Available column is changed away from 'NO'.
        """
        row = _find_table_row(AGENT_MD_FORMAT_DOC, UNSUPPORTED_TOOL)
        assert row is not None, (
            f"No table row containing {UNSUPPORTED_TOOL!r} found in {AGENT_MD_FORMAT_DOC}."
        )
        # The third pipe-separated column must not start with 'NO'
        # Row format: | col1 | col2 | col3 |
        columns = [c.strip() for c in row.strip("|").split("|")]
        assert len(columns) >= 3, f"Expected 3+ columns in row, got: {row!r}"
        availability_col = columns[2]
        assert not availability_col.startswith("NO"), (
            f"Available column for {UNSUPPORTED_TOOL!r} still starts with 'NO': "
            f"{availability_col!r}. Change it to 'REMOVED ...'."
        )
