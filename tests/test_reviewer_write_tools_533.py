"""Tests for task #533: reviewer tools list excludes write tools.

Static regression guard that parses agents/reviewer.agent.md YAML frontmatter
and asserts no tool in the tools list starts with 'edit/' (covers edit/createFile,
edit/editFiles, edit/createDirectory, edit/rename, and future additions).

This test is designed to PASS on the current codebase (reviewer already has no
write tools) and FAIL if write tools are ever added to the reviewer frontmatter.

AC coverage:
  - AC1: test file parses agents/reviewer.agent.md YAML frontmatter
  - AC2: no tool in tools list starts with 'edit/'
         (prefix matching catches all current and future write tool variants)
  - AC3: test runs in existing test suite (uv run pytest tests/test_reviewer_write_tools_533.py)
  - AC4: follows helper pattern from test_challenger_agent_467.py / test_code_reader_agent_307.py
"""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
_AGENT_FILE = _REPO_ROOT / "share" / "agents" / "reviewer.agent.md"


def _read_agent(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _extract_frontmatter(content: str) -> str:
    """Extract text between leading --- ... --- block."""
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    assert match is not None, (
        f"No valid YAML frontmatter (--- ... ---) found in {_AGENT_FILE.name}"
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


class TestFromAC_ReviewerWriteToolsExcluded:
    """AC1-AC4: agents/reviewer.agent.md must exist and must not contain write tools.

    This is a regression guard: tests PASS now and FAIL if write tools are added.
    """

    # --- AC1: file exists and frontmatter is parseable ---

    def test_reviewer_agent_file_exists(self) -> None:
        """AC1: agents/reviewer.agent.md must exist on disk."""
        assert _AGENT_FILE.is_file(), (
            "agents/reviewer.agent.md does not exist"
        )

    def test_reviewer_has_valid_yaml_frontmatter(self) -> None:
        """AC1: File must have a parseable --- ... --- YAML frontmatter block."""
        content = _read_agent(_AGENT_FILE)
        assert content.startswith("---\n"), (
            "agents/reviewer.agent.md must begin with '---' YAML frontmatter"
        )
        fm = _extract_frontmatter(content)
        assert fm.strip() != "", "Frontmatter block is empty"

    def test_reviewer_has_tools_key_in_frontmatter(self) -> None:
        """AC1: Frontmatter must contain a tools: key parseable by helper."""
        fm = _extract_frontmatter(_read_agent(_AGENT_FILE))
        tools = _extract_tools_from_frontmatter(fm)
        assert isinstance(tools, list), "tools must be a list"

    # --- AC2: no write tools in tools list ---

    def test_no_edit_prefix_tools(self) -> None:
        """AC2: No tool in tools list may start with 'edit/'.

        Regression guard: if any edit/* tool is added to the reviewer, this test
        will fail, alerting the team that the reviewer is no longer read-only.
        """
        fm = _extract_frontmatter(_read_agent(_AGENT_FILE))
        tools = _extract_tools_from_frontmatter(fm)
        write_tools = [t for t in tools if t.startswith("edit/")]
        assert write_tools == [], (
            f"reviewer.agent.md contains write tool(s): {write_tools!r}. "
            "Reviewer must be strictly read-only. Remove all edit/* tools."
        )

    def test_edit_create_file_excluded(self) -> None:
        """AC2: Specifically verifies edit/createFile is not in tools list."""
        fm = _extract_frontmatter(_read_agent(_AGENT_FILE))
        tools = _extract_tools_from_frontmatter(fm)
        assert "edit/createFile" not in tools, (
            "edit/createFile must not appear in reviewer tools"
        )

    def test_edit_edit_files_excluded(self) -> None:
        """AC2: Specifically verifies edit/editFiles is not in tools list."""
        fm = _extract_frontmatter(_read_agent(_AGENT_FILE))
        tools = _extract_tools_from_frontmatter(fm)
        assert "edit/editFiles" not in tools, (
            "edit/editFiles must not appear in reviewer tools"
        )

    def test_edit_create_directory_excluded(self) -> None:
        """AC2: Specifically verifies edit/createDirectory is not in tools list."""
        fm = _extract_frontmatter(_read_agent(_AGENT_FILE))
        tools = _extract_tools_from_frontmatter(fm)
        assert "edit/createDirectory" not in tools, (
            "edit/createDirectory must not appear in reviewer tools"
        )

    def test_edit_rename_excluded(self) -> None:
        """AC2: Specifically verifies edit/rename is not in tools list."""
        fm = _extract_frontmatter(_read_agent(_AGENT_FILE))
        tools = _extract_tools_from_frontmatter(fm)
        assert "edit/rename" not in tools, (
            "edit/rename must not appear in reviewer tools"
        )

    def test_no_edit_prefix_future_additions(self) -> None:
        """AC2 boundary: any future edit/* tool addition is caught by prefix check.

        This test expresses the SAME constraint as test_no_edit_prefix_tools but
        is explicitly named as the boundary/future-proof variant so that the
        intent is clear when the test suite is read as a specification.
        """
        fm = _extract_frontmatter(_read_agent(_AGENT_FILE))
        tools = _extract_tools_from_frontmatter(fm)
        violating = [t for t in tools if t.lower().startswith("edit/")]
        assert violating == [], (
            f"Reviewer tools contains 'edit/' prefix tool(s): {violating!r}. "
            "All edit/* tools are forbidden — the reviewer is strictly read-only."
        )
