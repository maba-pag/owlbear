"""Failing tests for task #38: Add disable-model-invocation to pipeline-only agents.

Covers:
  AC1: disable-model-invocation: true in YAML frontmatter of exactly 8 pipeline agents
       (planner, researcher, architect, test-writer, builder, reviewer, writer, auditor)
  AC2: disable-model-invocation absent from orchestrator, kanban-planner, curator
  AC3: No other changes to agent files beyond the single YAML line addition (spot-checks)
  AC4: Orchestrator agents array unchanged (still lists all 10 subagents)

RED phase:
  - TestFromAC_PipelineAgentDisableFlag (8 parametrized): all FAIL on current HEAD
    because no agent file currently has disable-model-invocation in its frontmatter.
  - TestFromAC_ExactEightAgentsHaveFlag: FAILS on current HEAD (0 != 8)
  - TestFromAC_NonPipelineAgentNoFlag (3 parametrized): invariant guard—PASS on
    current HEAD and must continue to PASS after builder's changes; will FAIL if
    builder accidentally adds the flag to a non-pipeline agent.
  - TestFromAC_OrchestratorAgentsArrayUnchanged: invariant guard—PASS on current HEAD;
    will FAIL if builder removes or alters any entry in the orchestrator agents list.
  - TestFromAC_NoOtherChanges: invariant guard—spot-checks that existing key frontmatter
    fields are not disturbed; will FAIL if builder inadvertently alters other fields.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
AGENTS_DIR = ROOT / ".github" / "agents"

# AC1: exactly these 8 agents must receive disable-model-invocation: true
PIPELINE_AGENTS: list[str] = [
    "planner",
    "researcher",
    "architect",
    "test-writer",
    "builder",
    "reviewer",
    "writer",
    "auditor",
]

# AC2: these 3 agents must NOT have the flag
NON_PIPELINE_AGENTS: list[str] = [
    "orchestrator",
    "kanban-planner",
    "curator",
]

# AC4: orchestrator agents list must still contain all 10 of these entries
ORCHESTRATOR_EXPECTED_SUBAGENTS: list[str] = [
    "kanban-planner",
    "planner",
    "researcher",
    "architect",
    "test-writer",
    "builder",
    "reviewer",
    "writer",
    "auditor",
    "curator",
]


def _read_frontmatter(agent_name: str) -> str:
    """Return the YAML frontmatter content (between --- delimiters) of an agent file."""
    path = AGENTS_DIR / f"{agent_name}.agent.md"
    content = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    assert match, f"No YAML frontmatter block found in {path.name}"
    return match.group(1)


def _parse_orchestrator_agents_list(frontmatter: str) -> list[str]:
    """Extract agent names from the 'agents:' multi-line list in YAML frontmatter."""
    match = re.search(r"^agents:\s*\n((?:  - .+\n?)+)", frontmatter, re.MULTILINE)
    assert match, "Could not find 'agents:' list in orchestrator frontmatter"
    return [
        line.strip().lstrip("- ").strip()
        for line in match.group(1).splitlines()
        if line.strip()
    ]


class TestFromAC_PipelineAgentDisableFlag:
    """AC1: disable-model-invocation: true must appear in frontmatter of all 8 pipeline agents.

    All 8 tests FAIL on current HEAD — no agent file currently has the flag.
    """

    @pytest.mark.parametrize("agent_name", PIPELINE_AGENTS)
    def test_has_disable_model_invocation_true(self, agent_name: str) -> None:
        """Pipeline agent frontmatter must contain 'disable-model-invocation: true'."""
        frontmatter = _read_frontmatter(agent_name)
        assert "disable-model-invocation: true" in frontmatter, (
            f"{agent_name}.agent.md is missing 'disable-model-invocation: true' "
            f"in its YAML frontmatter"
        )


class TestFromAC_ExactEightAgentsHaveFlag:
    """AC1 (exact-count guard): Exactly 8 of the 11 agent files must have the flag.

    FAILS on current HEAD (0 files have the flag, expected 8).
    """

    def test_total_agents_with_flag_equals_eight(self) -> None:
        """Total count of agent files with 'disable-model-invocation: true' must equal 8."""
        all_agents = PIPELINE_AGENTS + NON_PIPELINE_AGENTS
        count = sum(
            1
            for agent in all_agents
            if "disable-model-invocation: true" in _read_frontmatter(agent)
        )
        assert count == 8, (
            f"Expected exactly 8 agent files with 'disable-model-invocation: true', "
            f"found {count}"
        )


class TestFromAC_NonPipelineAgentNoFlag:
    """AC2: disable-model-invocation must be absent from orchestrator, kanban-planner, curator.

    Invariant guard: PASSES on current HEAD (flag not present anywhere yet).
    Will FAIL if builder accidentally adds the flag to a non-pipeline agent.
    """

    @pytest.mark.parametrize("agent_name", NON_PIPELINE_AGENTS)
    def test_does_not_have_disable_model_invocation(self, agent_name: str) -> None:
        """Non-pipeline agent frontmatter must NOT contain 'disable-model-invocation'."""
        frontmatter = _read_frontmatter(agent_name)
        assert "disable-model-invocation" not in frontmatter, (
            f"{agent_name}.agent.md must NOT have 'disable-model-invocation' "
            f"in its YAML frontmatter (it is not a pipeline-only agent)"
        )


class TestFromAC_OrchestratorAgentsArrayUnchanged:
    """AC4: Orchestrator agents array must still list all 10 subagents unchanged.

    Invariant guard: PASSES on current HEAD.
    Will FAIL if builder accidentally removes or adds agents to the orchestrator list.
    """

    def _get_frontmatter(self) -> str:
        return _read_frontmatter("orchestrator")

    def test_orchestrator_has_exactly_ten_subagents(self) -> None:
        """Orchestrator agents list must contain exactly 10 entries."""
        agents = _parse_orchestrator_agents_list(self._get_frontmatter())
        assert len(agents) == 10, (
            f"Expected 10 entries in orchestrator agents list, found {len(agents)}: {agents}"
        )

    @pytest.mark.parametrize("expected_subagent", ORCHESTRATOR_EXPECTED_SUBAGENTS)
    def test_orchestrator_agents_list_contains(self, expected_subagent: str) -> None:
        """Each of the 10 expected subagents must still appear in the orchestrator agents list."""
        agents = _parse_orchestrator_agents_list(self._get_frontmatter())
        assert expected_subagent in agents, (
            f"'{expected_subagent}' is missing from orchestrator agents list. "
            f"Current list: {agents}"
        )


class TestFromAC_NoOtherChanges:
    """AC3: No changes to agent files beyond the single 'disable-model-invocation: true' line.

    Spot-checks that existing key frontmatter fields are preserved in all 8 pipeline agents.
    Invariant guard: PASSES on current HEAD.
    Will FAIL if builder inadvertently alters other frontmatter fields.
    """

    @pytest.mark.parametrize("agent_name", PIPELINE_AGENTS)
    def test_pipeline_agent_user_invocable_false_preserved(
        self, agent_name: str
    ) -> None:
        """Pipeline agents must retain their existing 'user-invocable: false' field."""
        frontmatter = _read_frontmatter(agent_name)
        assert "user-invocable: false" in frontmatter, (
            f"{agent_name}.agent.md lost its 'user-invocable: false' field — "
            f"no other changes should be made beyond adding disable-model-invocation"
        )

    @pytest.mark.parametrize("agent_name", PIPELINE_AGENTS)
    def test_pipeline_agent_name_field_preserved(self, agent_name: str) -> None:
        """Pipeline agent files must still have their name: field intact."""
        frontmatter = _read_frontmatter(agent_name)
        assert f"name: {agent_name}" in frontmatter, (
            f"{agent_name}.agent.md is missing its 'name: {agent_name}' field"
        )

    @pytest.mark.parametrize("agent_name", NON_PIPELINE_AGENTS)
    def test_non_pipeline_agent_name_field_preserved(self, agent_name: str) -> None:
        """Non-pipeline agent files must still have their name: field intact."""
        frontmatter = _read_frontmatter(agent_name)
        assert f"name: {agent_name}" in frontmatter, (
            f"{agent_name}.agent.md is missing its 'name: {agent_name}' field"
        )
