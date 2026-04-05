"""Failing tests for task #123: Revert vscode/askQuestions from all agents.

Covers:
  - No .agent.md file in agents/ contains vscode/askQuestions in YAML frontmatter
    tools (broad guard — AC1)
  - orchestrator.agent.md specifically excludes vscode/askQuestions (AC2)
  - kanban-planner.agent.md specifically excludes vscode/askQuestions (AC2)
  - curator.agent.md specifically excludes vscode/askQuestions (AC2)

Tests fail on current HEAD: kanban-planner.agent.md and curator.agent.md still
list vscode/askQuestions in their frontmatter tools.
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
AGENTS_DIR = ROOT / "share" / "agents"

TOOL_NAME = "vscode/askQuestions"

_all_agent_files = sorted(AGENTS_DIR.glob("*.agent.md"))


def _read_frontmatter(path: Path) -> str:
    """Return the YAML frontmatter block (between the two --- delimiters).

    Args:
        path: Path to an .agent.md file.

    Returns:
        The raw frontmatter string, or empty string if none found.
    """
    content = path.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return ""
    end = content.find("---", 3)
    if end == -1:
        return ""
    return content[3:end]


class TestFromAC_NoAgentHasAskQuestions:
    """AC1: No .agent.md file in agents/ may contain vscode/askQuestions in its tools."""

    @pytest.mark.parametrize(
        "agent_file",
        _all_agent_files,
        ids=[f.name for f in _all_agent_files],
    )
    def test_no_agent_has_ask_questions(self, agent_file: Path) -> None:
        """Every agent file must not list vscode/askQuestions in YAML frontmatter tools.

        Fails on current HEAD for kanban-planner.agent.md and curator.agent.md,
        which still contain vscode/askQuestions.
        """
        frontmatter = _read_frontmatter(agent_file)
        assert TOOL_NAME not in frontmatter, (
            f"{agent_file.name} must not list {TOOL_NAME!r} in its tools block. "
            "vscode/askQuestions must be removed from all agents (revert of #108)."
        )


class TestFromAC_SpecificAgentsExcludeAskQuestions:
    """AC2: orchestrator, kanban-planner, and curator specifically exclude askQuestions."""

    def test_orchestrator_does_not_have_ask_questions(self) -> None:
        """orchestrator.agent.md must not include vscode/askQuestions in its tools block.

        Regression guard: orchestrator.agent.md already has askQuestions removed;
        this test ensures it is never re-introduced.
        """
        frontmatter = _read_frontmatter(AGENTS_DIR / "orchestrator.agent.md")
        assert TOOL_NAME not in frontmatter, (
            f"orchestrator.agent.md must not list {TOOL_NAME!r} in its tools block. "
            "Remove it to complete the revert of #108."
        )

    def test_kanban_planner_does_not_have_ask_questions(self) -> None:
        """kanban-planner.agent.md must not include vscode/askQuestions in its tools block.

        Fails on current HEAD: kanban-planner.agent.md still lists vscode/askQuestions.
        """
        frontmatter = _read_frontmatter(AGENTS_DIR / "kanban-planner.agent.md")
        assert TOOL_NAME not in frontmatter, (
            f"kanban-planner.agent.md must not list {TOOL_NAME!r} in its tools block. "
            "Remove it to complete the revert of #108."
        )

    def test_curator_does_not_have_ask_questions(self) -> None:
        """curator.agent.md must not include vscode/askQuestions in its tools block.

        Fails on current HEAD: curator.agent.md still lists vscode/askQuestions.
        """
        frontmatter = _read_frontmatter(AGENTS_DIR / "curator.agent.md")
        assert TOOL_NAME not in frontmatter, (
            f"curator.agent.md must not list {TOOL_NAME!r} in its tools block. "
            "Remove it to complete the revert of #108."
        )
