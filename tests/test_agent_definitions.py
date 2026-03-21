"""Tests for core agent definition files — all 9 agents in the OwlBear inventory."""

from __future__ import annotations

from pathlib import Path

import pytest

from owlbear.core.agent_def import parse_agent_definition
from owlbear.core.agent_registry import AgentRegistry
from owlbear.core.roles import AgentRole

# Directory containing the shipped agent definitions.
AGENTS_DIR = Path(__file__).resolve().parent.parent / "src" / "owlbear" / "agents"

# Known toolset names that map to real Toolset classes.
KNOWN_TOOLSETS = frozenset(
    {
        "filesystem",
        "terminal",
        "ask_user",
        "browser",
        "delegation",
        "kanban",
        "knowledge",
        "web_search",
    }
)

# Expected metadata for each agent definition.
EXPECTED_AGENTS: dict[str, dict] = {
    "orchestrator": {
        "description": "Routes tasks to specialist agents and plans work",
        "role": "builder",
        "tools": ["delegation", "filesystem", "ask_user", "kanban", "terminal"],
        "skills": ["kanban-md", "kanban-based-development"],
        "max_delegation_depth": 5,
    },
    "kanban-planner": {
        "description": "Entry gate for all task creation + feature decomposition",
        "role": "builder",
        "tools": ["filesystem", "ask_user", "kanban"],
        "skills": ["kanban-md", "kanban-based-development", "project-definition"],
        "max_delegation_depth": 3,
    },
    "builder": {
        "description": "Implements code using TDD workflow",
        "role": "builder",
        "tools": ["filesystem", "terminal"],
        "skills": ["kanban-md", "tdd-workflow"],
        "max_delegation_depth": 2,
    },
    "researcher": {
        "description": "Investigates topics and produces structured findings",
        "role": "builder",
        "tools": ["filesystem", "browser", "web_search", "knowledge", "ask_user"],
        "skills": ["kanban-md"],
        "max_delegation_depth": 1,
    },
    "architect": {
        "description": "Review researched tasks, refine AC, approve for development",
        "role": "validator",
        "tools": ["filesystem", "kanban", "ask_user"],
        "skills": ["kanban-md"],
        "max_delegation_depth": 1,
    },
    "reviewer": {
        "description": "Read-only quality verification of code and tests",
        "role": "validator",
        "tools": ["filesystem", "terminal"],
        "skills": ["kanban-md", "code-review"],
        "max_delegation_depth": 0,
    },
    "writer": {
        "description": "Verifies and updates documentation",
        "role": "builder",
        "tools": ["filesystem", "terminal"],
        "skills": ["kanban-md", "docs-gate"],
        "max_delegation_depth": 0,
    },
    "auditor": {
        "description": "Verify done tasks, archive confirmed, commit + push",
        "role": "validator",
        "tools": ["filesystem", "terminal", "kanban", "ask_user"],
        "skills": ["kanban-md", "task-verification"],
        "max_delegation_depth": 0,
    },
    "curator": {
        "description": "Periodic knowledge graph maintenance and deduplication",
        "role": "builder",
        "tools": ["filesystem", "terminal", "knowledge"],
        "skills": ["kanban-md"],
        "max_delegation_depth": 0,
    },
}


class TestAgentDefinitionFiles:
    """All 9 .md files parse via parse_agent_definition() without error."""

    @pytest.mark.parametrize("agent_name", list(EXPECTED_AGENTS))
    def test_parse_without_error(self, agent_name: str) -> None:
        md_path = AGENTS_DIR / f"{agent_name}.md"
        assert md_path.exists(), f"Missing agent file: {md_path}"
        defn = parse_agent_definition(md_path)
        assert defn.name == agent_name

    @pytest.mark.parametrize("agent_name", list(EXPECTED_AGENTS))
    def test_description_matches(self, agent_name: str) -> None:
        defn = parse_agent_definition(AGENTS_DIR / f"{agent_name}.md")
        assert defn.description == EXPECTED_AGENTS[agent_name]["description"]

    @pytest.mark.parametrize("agent_name", list(EXPECTED_AGENTS))
    def test_tools_match(self, agent_name: str) -> None:
        defn = parse_agent_definition(AGENTS_DIR / f"{agent_name}.md")
        assert sorted(defn.tools) == sorted(EXPECTED_AGENTS[agent_name]["tools"])

    @pytest.mark.parametrize("agent_name", list(EXPECTED_AGENTS))
    def test_skills_match(self, agent_name: str) -> None:
        defn = parse_agent_definition(AGENTS_DIR / f"{agent_name}.md")
        assert defn.skills == EXPECTED_AGENTS[agent_name]["skills"]

    @pytest.mark.parametrize("agent_name", list(EXPECTED_AGENTS))
    def test_max_delegation_depth(self, agent_name: str) -> None:
        defn = parse_agent_definition(AGENTS_DIR / f"{agent_name}.md")
        assert defn.max_delegation_depth == EXPECTED_AGENTS[agent_name]["max_delegation_depth"]

    @pytest.mark.parametrize("agent_name", list(EXPECTED_AGENTS))
    def test_system_prompt_nonempty(self, agent_name: str) -> None:
        defn = parse_agent_definition(AGENTS_DIR / f"{agent_name}.md")
        lines = [ln for ln in defn.system_prompt.strip().splitlines() if ln.strip()]
        # orchestrator has routing tables + agent catalog + kanban pipeline (tasks #311, #312, #316)
        upper = 70 if agent_name == "orchestrator" else 25
        assert 10 <= len(lines) <= upper, (
            f"{agent_name} system prompt has {len(lines)} non-blank lines, expected 10-{upper}"
        )


class TestRegistryScanAgentsDir:
    """AgentRegistry.scan() on agents dir loads all 9 definitions."""

    def test_scan_loads_all_nine(self) -> None:
        from pydantic_ai.toolsets import FunctionToolset

        registry = AgentRegistry(
            AGENTS_DIR,
            lambda _name: FunctionToolset(),
            default_model="test",
        )
        registry.scan()
        assert len(registry.definitions) == 9
        assert set(registry.definitions) == set(EXPECTED_AGENTS)

    def test_get_kanban_planner_returns_agent_with_resolved_tools(self) -> None:
        from pydantic_ai import Agent
        from pydantic_ai.toolsets import FunctionToolset

        resolved_tools: list[str] = []

        def tracking_resolver(name: str) -> FunctionToolset:
            resolved_tools.append(name)
            return FunctionToolset()

        registry = AgentRegistry(
            AGENTS_DIR,
            tracking_resolver,
            default_model="test",
        )
        registry.scan()
        agent = registry.get("kanban-planner")

        assert isinstance(agent, Agent)
        assert sorted(resolved_tools) == [
            "ask_user",
            "filesystem",
            "kanban",
        ]


class TestRoleValues:
    """Each definition's role is a valid AgentRole enum member."""

    @pytest.mark.parametrize("agent_name", list(EXPECTED_AGENTS))
    def test_role_is_valid_enum(self, agent_name: str) -> None:
        defn = parse_agent_definition(AGENTS_DIR / f"{agent_name}.md")
        role = AgentRole(defn.role)
        assert isinstance(role, AgentRole)

    def test_reviewer_is_validator(self) -> None:
        defn = parse_agent_definition(AGENTS_DIR / "reviewer.md")
        assert AgentRole(defn.role) is AgentRole.VALIDATOR

    def test_architect_is_validator(self) -> None:
        defn = parse_agent_definition(AGENTS_DIR / "architect.md")
        assert AgentRole(defn.role) is AgentRole.VALIDATOR

    def test_auditor_is_validator(self) -> None:
        defn = parse_agent_definition(AGENTS_DIR / "auditor.md")
        assert AgentRole(defn.role) is AgentRole.VALIDATOR

    def test_writer_is_validator(self) -> None:
        defn = parse_agent_definition(AGENTS_DIR / "writer.md")
        assert AgentRole(defn.role) is AgentRole.VALIDATOR

    @pytest.mark.parametrize(
        "agent_name",
        ["orchestrator", "kanban-planner", "builder", "researcher"],
    )
    def test_builders(self, agent_name: str) -> None:
        defn = parse_agent_definition(AGENTS_DIR / f"{agent_name}.md")
        assert AgentRole(defn.role) is AgentRole.BUILDER


class TestToolsetNames:
    """Each definition's tools list contains only known toolset names."""

    @pytest.mark.parametrize("agent_name", list(EXPECTED_AGENTS))
    def test_tools_are_known(self, agent_name: str) -> None:
        defn = parse_agent_definition(AGENTS_DIR / f"{agent_name}.md")
        unknown = set(defn.tools) - KNOWN_TOOLSETS
        assert not unknown, f"{agent_name} has unknown tools: {unknown}"


class TestAgentsDirConfig:
    """agents_dir in OwlBearSettings resolves to the agents directory."""

    def test_agents_dir_exists_in_settings(self) -> None:
        from owlbear.config import OwlBearSettings

        settings = OwlBearSettings()
        assert hasattr(settings, "agents_dir")
        assert isinstance(settings.agents_dir, Path)

    def test_agents_dir_default_value(self) -> None:
        from owlbear.config import OwlBearSettings

        settings = OwlBearSettings()
        expected = Path(__file__).resolve().parent.parent / "src" / "owlbear" / "agents"
        assert settings.agents_dir.resolve() == expected
