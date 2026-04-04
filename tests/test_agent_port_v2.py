"""Failing tests for task #96: Port agents to agent-md v2 location.

Verifies that all 11 .agent.md files are ported from .github/agents/ to
agents/, with updated tool names (todos not todo), correct agents: fields,
and v1 cleanup (.github/agents/ empty of .agent.md files).

All tests fail on current HEAD: agents/ only contains README.md and
.github/agents/ still holds all 11 .agent.md files.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
AGENTS_DIR = ROOT / ".github" / "agents"

# The 9 leaf agents — no sub-agents of their own
LEAF_AGENTS = [
    "architect",
    "auditor",
    "builder",
    "curator",
    "planner",
    "planner",
    "reviewer",
    "test-writer",
    "writer",
]

# All pipeline agent names (used to verify exclusivity checks)
ALL_AGENT_NAMES = [
    "architect",
    "auditor",
    "builder",
    "curator",
    "planner",
    "orchestrator",
    "planner",
    "researcher",
    "reviewer",
    "test-writer",
    "writer",
]


def _read_frontmatter(path: Path) -> str:
    """Extract YAML frontmatter text (between the two --- delimiters)."""
    content = path.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return ""
    end = content.find("---", 3)
    if end == -1:
        return ""
    return content[3:end]


# ---------------------------------------------------------------------------
# AC: All 11 .agent.md files exist in agents/ directory
# ---------------------------------------------------------------------------


class TestFromAC_AgentFilesExist:
    """All 11 agents must be present in agents/ after the port."""

    def test_architect_exists(self) -> None:
        assert (AGENTS_DIR / "architect.agent.md").is_file()

    def test_auditor_exists(self) -> None:
        assert (AGENTS_DIR / "auditor.agent.md").is_file()

    def test_builder_exists(self) -> None:
        assert (AGENTS_DIR / "builder.agent.md").is_file()

    def test_curator_exists(self) -> None:
        assert (AGENTS_DIR / "curator.agent.md").is_file()

    def test_kanban_planner_exists(self) -> None:
        assert (AGENTS_DIR / "kanban-planner.agent.md").is_file()

    def test_orchestrator_exists(self) -> None:
        assert (AGENTS_DIR / "orchestrator.agent.md").is_file()

    def test_planner_exists(self) -> None:
        assert (AGENTS_DIR / "planner.agent.md").is_file()

    def test_researcher_exists(self) -> None:
        assert (AGENTS_DIR / "researcher.agent.md").is_file()

    def test_reviewer_exists(self) -> None:
        assert (AGENTS_DIR / "reviewer.agent.md").is_file()

    def test_test_writer_exists(self) -> None:
        assert (AGENTS_DIR / "test-writer.agent.md").is_file()

    def test_writer_exists(self) -> None:
        assert (AGENTS_DIR / "doc-writer.agent.md").is_file()


# ---------------------------------------------------------------------------
# AC: Each file contains 'todos' (not 'todo') in the tools: list
# ---------------------------------------------------------------------------


class TestFromAC_AgentToolsTodos:
    """tools: list must use 'todos' — old 'todo' token must not appear."""

    def _assert_todos_not_todo(self, name: str) -> None:
        path = AGENTS_DIR / f"{name}.agent.md"
        assert path.is_file(), f"agents/{name}.agent.md does not exist"
        fm = _read_frontmatter(path)
        assert re.search(r"\btodos\b", fm), f"{name}: 'todos' not found in frontmatter tools"
        assert not re.search(r"\btodo\b", fm), f"{name}: old 'todo' still present in frontmatter"

    def test_architect_todos(self) -> None:
        self._assert_todos_not_todo("architect")

    def test_auditor_todos(self) -> None:
        self._assert_todos_not_todo("auditor")

    def test_builder_todos(self) -> None:
        self._assert_todos_not_todo("builder")

    def test_curator_todos(self) -> None:
        self._assert_todos_not_todo("curator")

    def test_kanban_planner_todos(self) -> None:
        self._assert_todos_not_todo("planner")

    def test_orchestrator_todos(self) -> None:
        self._assert_todos_not_todo("orchestrator")

    def test_planner_todos(self) -> None:
        self._assert_todos_not_todo("planner")

    def test_researcher_todos(self) -> None:
        self._assert_todos_not_todo("researcher")

    def test_reviewer_todos(self) -> None:
        self._assert_todos_not_todo("reviewer")

    def test_test_writer_todos(self) -> None:
        self._assert_todos_not_todo("test-writer")

    def test_writer_todos(self) -> None:
        self._assert_todos_not_todo("writer")


# ---------------------------------------------------------------------------
# AC: curator.agent.md does NOT contain resolveMemoryFileUri in tools: list
# ---------------------------------------------------------------------------


class TestFromAC_CuratorNoResolveMemoryFileUri:
    """curator must not register the removed resolveMemoryFileUri tool."""

    def test_curator_tools_no_resolve_memory_file_uri(self) -> None:
        path = AGENTS_DIR / "curator.agent.md"
        assert path.is_file(), "agents/curator.agent.md does not exist"
        fm = _read_frontmatter(path)
        assert "resolveMemoryFileUri" not in fm

    def test_curator_file_no_resolve_memory_file_uri_anywhere(self) -> None:
        """resolveMemoryFileUri must not appear anywhere in curator.agent.md."""
        path = AGENTS_DIR / "curator.agent.md"
        assert path.is_file(), "agents/curator.agent.md does not exist"
        content = path.read_text(encoding="utf-8")
        assert "resolveMemoryFileUri" not in content


# ---------------------------------------------------------------------------
# AC: researcher.agent.md contains microsoft/markitdown/* in tools: list
# ---------------------------------------------------------------------------


class TestFromAC_ResearcherMarkitdown:
    """researcher must declare microsoft/markitdown/* in its tools: list."""

    def test_researcher_has_markitdown_tool(self) -> None:
        path = AGENTS_DIR / "researcher.agent.md"
        assert path.is_file(), "agents/researcher.agent.md does not exist"
        fm = _read_frontmatter(path)
        assert "microsoft/markitdown/*" in fm

    def test_researcher_markitdown_in_tools_section(self) -> None:
        path = AGENTS_DIR / "researcher.agent.md"
        assert path.is_file(), "agents/researcher.agent.md does not exist"
        fm = _read_frontmatter(path)
        assert re.search(r"\btools\s*:", fm), "tools: key missing in researcher frontmatter"
        # microsoft/markitdown/* must be within the tools block (before next top-level key)
        tools_match = re.search(r"tools\s*:(.*?)(?=\n\S|\Z)", fm, re.DOTALL)
        assert tools_match is not None, "Could not locate tools: section in researcher frontmatter"
        assert "microsoft/markitdown/*" in tools_match.group(1)


# ---------------------------------------------------------------------------
# AC: orchestrator.agent.md agents: field includes Explore
# ---------------------------------------------------------------------------


class TestFromAC_OrchestratorAgentsExplore:
    """orchestrator agents: list must include the Explore agent."""

    def test_orchestrator_has_agents_field(self) -> None:
        path = AGENTS_DIR / "orchestrator.agent.md"
        assert path.is_file(), "agents/orchestrator.agent.md does not exist"
        fm = _read_frontmatter(path)
        assert re.search(r"\bagents\s*:", fm), "agents: field missing from orchestrator frontmatter"

    def test_orchestrator_agents_includes_explore(self) -> None:
        path = AGENTS_DIR / "orchestrator.agent.md"
        assert path.is_file(), "agents/orchestrator.agent.md does not exist"
        fm = _read_frontmatter(path)
        # Explore must appear after the agents: key
        agents_match = re.search(r"agents\s*:(.*?)(?=\n\S|\Z)", fm, re.DOTALL)
        assert agents_match is not None, "Could not locate agents: section"
        assert "Explore" in agents_match.group(1), (
            "Explore not found in orchestrator agents: section"
        )


# ---------------------------------------------------------------------------
# AC: researcher.agent.md agents: field is [Explore] (exactly one entry)
# ---------------------------------------------------------------------------


class TestFromAC_ResearcherAgentsExploreOnly:
    """researcher agents: must be exactly [Explore] — no other agents."""

    def test_researcher_has_agents_field(self) -> None:
        path = AGENTS_DIR / "researcher.agent.md"
        assert path.is_file(), "agents/researcher.agent.md does not exist"
        fm = _read_frontmatter(path)
        assert re.search(r"\bagents\s*:", fm), "agents: field missing from researcher frontmatter"

    def test_researcher_agents_contains_explore(self) -> None:
        path = AGENTS_DIR / "researcher.agent.md"
        assert path.is_file(), "agents/researcher.agent.md does not exist"
        fm = _read_frontmatter(path)
        agents_match = re.search(r"agents\s*:(.*?)(?=\n\S|\Z)", fm, re.DOTALL)
        assert agents_match is not None, "Could not locate agents: section"
        assert "Explore" in agents_match.group(1)

    def test_researcher_agents_no_other_pipeline_agents(self) -> None:
        """agents: field must contain only Explore — no pipeline agent names."""
        path = AGENTS_DIR / "researcher.agent.md"
        assert path.is_file(), "agents/researcher.agent.md does not exist"
        fm = _read_frontmatter(path)
        agents_match = re.search(r"agents\s*:(.*?)(?=\n\S|\Z)", fm, re.DOTALL)
        assert agents_match is not None, "Could not locate agents: section"
        agents_section = agents_match.group(1)
        unexpected = [a for a in ALL_AGENT_NAMES if a in agents_section]
        assert not unexpected, f"researcher agents: contains unexpected entries: {unexpected}"


# ---------------------------------------------------------------------------
# AC: 9 leaf agents have agents: [] (empty list)
# ---------------------------------------------------------------------------


class TestFromAC_LeafAgentsEmptyList:
    """Leaf agents must declare agents: [] — they dispatch no sub-agents."""

    def _assert_agents_empty(self, name: str) -> None:
        path = AGENTS_DIR / f"{name}.agent.md"
        assert path.is_file(), f"agents/{name}.agent.md does not exist"
        fm = _read_frontmatter(path)
        assert re.search(r"\bagents\s*:", fm), f"{name}: agents: field missing"
        # Must be inline empty list
        agents_match = re.search(r"agents\s*:\s*(\[.*?\])", fm)
        assert agents_match is not None, f"{name}: agents: not in inline [] format"
        assert agents_match.group(1) == "[]", (
            f"{name}: agents: is not empty list, got {agents_match.group(1)!r}"
        )

    def test_architect_agents_empty(self) -> None:
        self._assert_agents_empty("architect")

    def test_auditor_agents_empty(self) -> None:
        self._assert_agents_empty("auditor")

    def test_builder_agents_empty(self) -> None:
        self._assert_agents_empty("builder")

    def test_curator_agents_empty(self) -> None:
        self._assert_agents_empty("curator")

    def test_kanban_planner_agents_empty(self) -> None:
        self._assert_agents_empty("planner")

    def test_planner_agents_empty(self) -> None:
        self._assert_agents_empty("planner")

    def test_reviewer_agents_empty(self) -> None:
        self._assert_agents_empty("reviewer")

    def test_test_writer_agents_empty(self) -> None:
        self._assert_agents_empty("test-writer")

    def test_writer_agents_empty(self) -> None:
        self._assert_agents_empty("writer")


