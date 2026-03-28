"""Failing tests for task #108: Grant vscode/askQuestions to user-invocable agents.

Covers:
  - orchestrator.agent.md tools list includes vscode/askQuestions
  - kanban-planner.agent.md tools list includes vscode/askQuestions
  - curator.agent.md tools list includes vscode/askQuestions
  - No pipeline-only agent (builder, reviewer, writer, test-writer, auditor,
    planner, architect, researcher) has vscode/askQuestions in its tools list

AC1-AC3 tests fail on current HEAD: none of the user-invocable agents list
vscode/askQuestions yet.
AC4 exclusivity tests pass on current HEAD (guardrail: pipeline agents must
never gain this tool, even after the builder adds it to user-invocable agents).
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parent.parent
AGENTS_DIR = ROOT / "agents"

TOOL_NAME = "vscode/askQuestions"


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


class TestFromAC_UserInvocableAgentsHaveAskQuestions:
    """AC1-AC3: orchestrator, kanban-planner, and curator must list vscode/askQuestions."""

    def test_orchestrator_tools_include_ask_questions(self) -> None:
        """orchestrator.agent.md must include vscode/askQuestions in its tools block.

        Fails until the builder adds vscode/askQuestions to tools in
        agents/orchestrator.agent.md frontmatter.
        """
        frontmatter = _read_frontmatter(AGENTS_DIR / "orchestrator.agent.md")
        assert TOOL_NAME in frontmatter, (
            f"orchestrator.agent.md does not list {TOOL_NAME!r} in its tools block. "
            "Add it to allow the orchestrator to ask the user questions."
        )

    def test_kanban_planner_tools_include_ask_questions(self) -> None:
        """kanban-planner.agent.md must include vscode/askQuestions in its tools block.

        Fails until the builder adds vscode/askQuestions to tools in
        agents/kanban-planner.agent.md frontmatter.
        """
        frontmatter = _read_frontmatter(AGENTS_DIR / "kanban-planner.agent.md")
        assert TOOL_NAME in frontmatter, (
            f"kanban-planner.agent.md does not list {TOOL_NAME!r} in its tools block. "
            "Add it to allow the kanban-planner to ask the user questions."
        )

    def test_curator_tools_include_ask_questions(self) -> None:
        """curator.agent.md must include vscode/askQuestions in its tools block.

        Fails until the builder adds vscode/askQuestions to tools in
        agents/curator.agent.md frontmatter.
        """
        frontmatter = _read_frontmatter(AGENTS_DIR / "curator.agent.md")
        assert TOOL_NAME in frontmatter, (
            f"curator.agent.md does not list {TOOL_NAME!r} in its tools block. "
            "Add it to allow the curator to ask the user questions."
        )


class TestFromAC_PipelineAgentsExcludeAskQuestions:
    """AC4: No pipeline-only agent may include vscode/askQuestions in its tools list."""

    def test_builder_does_not_have_ask_questions(self) -> None:
        """builder.agent.md must not list vscode/askQuestions."""
        frontmatter = _read_frontmatter(AGENTS_DIR / "builder.agent.md")
        assert TOOL_NAME not in frontmatter, (
            f"builder.agent.md must not list {TOOL_NAME!r}. "
            "Pipeline agents are not permitted to ask user questions."
        )

    def test_reviewer_does_not_have_ask_questions(self) -> None:
        """reviewer.agent.md must not list vscode/askQuestions."""
        frontmatter = _read_frontmatter(AGENTS_DIR / "reviewer.agent.md")
        assert TOOL_NAME not in frontmatter, (
            f"reviewer.agent.md must not list {TOOL_NAME!r}. "
            "Pipeline agents are not permitted to ask user questions."
        )

    def test_writer_does_not_have_ask_questions(self) -> None:
        """writer.agent.md must not list vscode/askQuestions."""
        frontmatter = _read_frontmatter(AGENTS_DIR / "writer.agent.md")
        assert TOOL_NAME not in frontmatter, (
            f"writer.agent.md must not list {TOOL_NAME!r}. "
            "Pipeline agents are not permitted to ask user questions."
        )

    def test_test_writer_does_not_have_ask_questions(self) -> None:
        """test-writer.agent.md must not list vscode/askQuestions."""
        frontmatter = _read_frontmatter(AGENTS_DIR / "test-writer.agent.md")
        assert TOOL_NAME not in frontmatter, (
            f"test-writer.agent.md must not list {TOOL_NAME!r}. "
            "Pipeline agents are not permitted to ask user questions."
        )

    def test_auditor_does_not_have_ask_questions(self) -> None:
        """auditor.agent.md must not list vscode/askQuestions."""
        frontmatter = _read_frontmatter(AGENTS_DIR / "auditor.agent.md")
        assert TOOL_NAME not in frontmatter, (
            f"auditor.agent.md must not list {TOOL_NAME!r}. "
            "Pipeline agents are not permitted to ask user questions."
        )

    def test_planner_does_not_have_ask_questions(self) -> None:
        """planner.agent.md must not list vscode/askQuestions."""
        frontmatter = _read_frontmatter(AGENTS_DIR / "planner.agent.md")
        assert TOOL_NAME not in frontmatter, (
            f"planner.agent.md must not list {TOOL_NAME!r}. "
            "Pipeline agents are not permitted to ask user questions."
        )

    def test_architect_does_not_have_ask_questions(self) -> None:
        """architect.agent.md must not list vscode/askQuestions."""
        frontmatter = _read_frontmatter(AGENTS_DIR / "architect.agent.md")
        assert TOOL_NAME not in frontmatter, (
            f"architect.agent.md must not list {TOOL_NAME!r}. "
            "Pipeline agents are not permitted to ask user questions."
        )

    def test_researcher_does_not_have_ask_questions(self) -> None:
        """researcher.agent.md must not list vscode/askQuestions."""
        frontmatter = _read_frontmatter(AGENTS_DIR / "researcher.agent.md")
        assert TOOL_NAME not in frontmatter, (
            f"researcher.agent.md must not list {TOOL_NAME!r}. "
            "Pipeline agents are not permitted to ask user questions."
        )
