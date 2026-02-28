"""Tests for core agent definition files — orchestrator, coder, reviewer, researcher, writer."""

from __future__ import annotations

from pathlib import Path

import pytest

from owlbear.core.agent_def import parse_agent_definition
from owlbear.core.agent_registry import AgentRegistry
from owlbear.core.roles import AgentRole

# Directory containing the shipped agent definitions.
AGENTS_DIR = Path(__file__).resolve().parent.parent / "src" / "owlbear" / "agents"

# Known toolset names that map to real Toolset classes.
KNOWN_TOOLSETS = frozenset({"filesystem", "terminal", "ask_user", "browser", "delegation"})

# Expected metadata for each agent definition.
EXPECTED_AGENTS: dict[str, dict] = {
    "orchestrator": {
        "description": "Routes tasks to specialist agents and plans work",
        "role": "builder",
        "tools": ["delegation", "filesystem", "ask_user"],
        "skills": ["kanban-md", "kanban-based-development"],
        "max_delegation_depth": 5,
    },
    "coder": {
        "description": "Implements code using TDD workflow",
        "role": "builder",
        "tools": ["filesystem", "terminal"],
        "skills": ["kanban-md"],
        "max_delegation_depth": 2,
    },
    "reviewer": {
        "description": "Read-only quality verification of code and tests",
        "role": "validator",
        "tools": ["filesystem", "terminal"],
        "skills": ["kanban-md"],
        "max_delegation_depth": 0,
    },
    "researcher": {
        "description": "Investigates topics and produces structured findings",
        "role": "validator",
        "tools": ["filesystem", "browser"],
        "skills": [],
        "max_delegation_depth": 1,
    },
    "writer": {
        "description": "Verifies and updates documentation",
        "role": "builder",
        "tools": ["filesystem"],
        "skills": ["kanban-md"],
        "max_delegation_depth": 0,
    },
}


class TestAgentDefinitionFiles:
    """All 5 .md files parse via parse_agent_definition() without error."""

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
        assert 10 <= len(lines) <= 25, (
            f"{agent_name} system prompt has {len(lines)} non-blank lines, expected 10-25"
        )


class TestRegistryScanAgentsDir:
    """AgentRegistry.scan() on agents dir loads all 5 definitions."""

    def test_scan_loads_all_five(self) -> None:
        from pydantic_ai.toolsets import FunctionToolset

        registry = AgentRegistry(
            AGENTS_DIR,
            lambda _name: FunctionToolset(),
            default_model="test",
        )
        registry.scan()
        assert len(registry.definitions) == 5
        assert set(registry.definitions) == set(EXPECTED_AGENTS)


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

    def test_researcher_is_validator(self) -> None:
        defn = parse_agent_definition(AGENTS_DIR / "researcher.md")
        assert AgentRole(defn.role) is AgentRole.VALIDATOR

    @pytest.mark.parametrize("agent_name", ["orchestrator", "coder", "writer"])
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
