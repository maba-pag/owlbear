"""Failing tests for task #36: Rename todo tool reference to todos in all .agent.md files.

Covers AC1: all 11 .github/agents/*.agent.md files must list 'todos' (not 'todo')
in their YAML frontmatter tools key. Tests handle both inline and multi-line array
formats found in the codebase.

All tests fail on current HEAD because files currently list 'todo', not 'todos'.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
AGENTS_DIR = ROOT / ".github" / "agents"

# All 11 agent files in .github/agents/ — full list per AC
AGENT_MD_FILES: list[str] = [
    "architect.agent.md",
    "auditor.agent.md",
    "builder.agent.md",
    "curator.agent.md",
    "kanban-planner.agent.md",
    "orchestrator.agent.md",
    "planner.agent.md",
    "researcher.agent.md",
    "reviewer.agent.md",
    "test-writer.agent.md",
    "writer.agent.md",
]


def _extract_frontmatter_tools(file_path: Path) -> list[str]:
    """Return the list of tool names from YAML frontmatter 'tools:' key.

    Handles both forms found in the codebase:
      - multi-line:  tools:\\n  [\\n    name,\\n  ]
      - inline:      tools: [name1, name2]
    """
    text = file_path.read_text(encoding="utf-8")
    # Capture everything between the first --- and second --- markers
    fm_match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not fm_match:
        return []
    frontmatter = fm_match.group(1)
    # Match the tools: key and its bracket-delimited list value (any whitespace between)
    tools_match = re.search(r"^tools:\s*(\[.*?\])", frontmatter, re.MULTILINE | re.DOTALL)
    if not tools_match:
        return []
    tools_block = tools_match.group(1)
    # Extract individual token names — word chars, slashes, dots (e.g. vscode/memory)
    return re.findall(r"[\w/.]+", tools_block)


class TestFromAC_AgentMdToolRename:
    """AC: All 11 .agent.md files in .github/agents/ reference 'todos' (not 'todo') in tools list."""

    @pytest.mark.parametrize("filename", AGENT_MD_FILES)
    def test_tools_list_contains_todos(self, filename: str) -> None:
        """YAML frontmatter tools list must include 'todos' for every agent file."""
        file_path = AGENTS_DIR / filename
        tools = _extract_frontmatter_tools(file_path)
        assert "todos" in tools, (
            f"{filename}: expected 'todos' in tools, got {tools!r}"
        )

    @pytest.mark.parametrize("filename", AGENT_MD_FILES)
    def test_tools_list_has_no_bare_todo(self, filename: str) -> None:
        """YAML frontmatter tools list must NOT contain bare 'todo' (only 'todos' is valid)."""
        file_path = AGENTS_DIR / filename
        tools = _extract_frontmatter_tools(file_path)
        assert "todo" not in tools, (
            f"{filename}: bare 'todo' still present in tools list (rename not applied): {tools!r}"
        )
