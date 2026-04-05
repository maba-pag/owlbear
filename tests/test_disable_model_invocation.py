"""Tests for task #38: Add disable-model-invocation to pipeline-only agents.

AC contract under test:
1. disable-model-invocation: true in YAML frontmatter of exactly 8 pipeline agents
   (planner, researcher, architect, test-writer, builder, reviewer, writer, auditor)
2. disable-model-invocation NOT present in orchestrator, kanban-planner, curator
3. No other changes to any agent file beyond the single YAML line addition
4. Orchestrator agents array unchanged (still lists all 10 subagents)
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
AGENTS_DIR = ROOT / "share" / "agents"

# The 8 pipeline agents that MUST have disable-model-invocation: true
PIPELINE_AGENTS = [
    "planner",
    "researcher",
    "architect",
    "test-writer",
    "builder",
    "reviewer",
    "writer",
    "auditor",
]

# The 3 agents that MUST NOT have disable-model-invocation
NON_PIPELINE_AGENTS = [
    "orchestrator",
    "planner",
    "curator",
]


def _get_frontmatter(path: Path) -> str:
    """Return the YAML frontmatter text between the first pair of --- delimiters."""
    content = path.read_text(encoding="utf-8")
    match = re.search(r"\A---\n(.*?)\n---", content, re.DOTALL)
    if match is None:
        raise ValueError(f"No frontmatter found in {path}")
    return match.group(1)


def _agent_path(name: str) -> Path:
    return AGENTS_DIR / f"{name}.agent.md"


class TestFromAC_PipelineAgentsHaveFlag:
    """AC1: disable-model-invocation: true must appear in all 8 pipeline agent frontmatters."""

    def test_planner_has_disable_model_invocation_true(self) -> None:
        """planner.agent.md frontmatter must contain 'disable-model-invocation: true'."""
        fm = _get_frontmatter(_agent_path("planner"))
        assert "disable-model-invocation: true" in fm

    def test_researcher_has_disable_model_invocation_true(self) -> None:
        """researcher.agent.md frontmatter must contain 'disable-model-invocation: true'."""
        fm = _get_frontmatter(_agent_path("researcher"))
        assert "disable-model-invocation: true" in fm

    def test_architect_has_disable_model_invocation_true(self) -> None:
        """architect.agent.md frontmatter must contain 'disable-model-invocation: true'."""
        fm = _get_frontmatter(_agent_path("architect"))
        assert "disable-model-invocation: true" in fm

    def test_test_writer_has_disable_model_invocation_true(self) -> None:
        """test-writer.agent.md frontmatter must contain 'disable-model-invocation: true'."""
        fm = _get_frontmatter(_agent_path("test-writer"))
        assert "disable-model-invocation: true" in fm

    def test_builder_has_disable_model_invocation_true(self) -> None:
        """builder.agent.md frontmatter must contain 'disable-model-invocation: true'."""
        fm = _get_frontmatter(_agent_path("builder"))
        assert "disable-model-invocation: true" in fm

    def test_reviewer_has_disable_model_invocation_true(self) -> None:
        """reviewer.agent.md frontmatter must contain 'disable-model-invocation: true'."""
        fm = _get_frontmatter(_agent_path("reviewer"))
        assert "disable-model-invocation: true" in fm

    def test_writer_has_disable_model_invocation_true(self) -> None:
        """writer.agent.md frontmatter must contain 'disable-model-invocation: true'."""
        fm = _get_frontmatter(_agent_path("writer"))
        assert "disable-model-invocation: true" in fm

    def test_auditor_has_disable_model_invocation_true(self) -> None:
        """auditor.agent.md frontmatter must contain 'disable-model-invocation: true'."""
        fm = _get_frontmatter(_agent_path("auditor"))
        assert "disable-model-invocation: true" in fm

    def test_total_pipeline_agents_with_flag_equals_eight(self) -> None:
        """Exactly 8 pipeline agents must have disable-model-invocation: true — no more, no less."""
        count = sum(
            1
            for name in PIPELINE_AGENTS
            if "disable-model-invocation: true" in _get_frontmatter(_agent_path(name))
        )
        assert count == 8, f"Expected 8 pipeline agents with flag, got {count}"


class TestFromAC_NonPipelineAgentsNoFlag:
    """AC2: orchestrator, kanban-planner, and curator must NOT have disable-model-invocation."""

    def test_orchestrator_does_not_have_flag(self) -> None:
        """orchestrator.agent.md frontmatter must NOT contain disable-model-invocation."""
        fm = _get_frontmatter(_agent_path("orchestrator"))
        assert "disable-model-invocation" not in fm

    def test_kanban_planner_does_not_have_flag(self) -> None:
        """kanban-planner.agent.md frontmatter must NOT contain disable-model-invocation."""
        fm = _get_frontmatter(_agent_path("planner"))
        assert "disable-model-invocation" not in fm

    def test_curator_does_not_have_flag(self) -> None:
        """curator.agent.md frontmatter must NOT contain disable-model-invocation."""
        fm = _get_frontmatter(_agent_path("curator"))
        assert "disable-model-invocation" not in fm

    def test_no_non_pipeline_agent_has_flag(self) -> None:
        """None of the three non-pipeline agents may acquire disable-model-invocation."""
        for name in NON_PIPELINE_AGENTS:
            fm = _get_frontmatter(_agent_path(name))
            assert "disable-model-invocation" not in fm, (
                f"{name}.agent.md must NOT have disable-model-invocation"
            )


class TestFromAC_NoExtraChanges:
    """AC3: No field beyond disable-model-invocation may be added, removed, or modified."""

    # --- Pipeline agent invariants ---

    def test_planner_preserves_name_field(self) -> None:
        fm = _get_frontmatter(_agent_path("planner"))
        assert "name: planner" in fm

    def test_planner_preserves_user_invocable_false(self) -> None:
        fm = _get_frontmatter(_agent_path("planner"))
        assert "user-invocable: false" in fm

    def test_researcher_preserves_name_field(self) -> None:
        fm = _get_frontmatter(_agent_path("researcher"))
        assert "name: researcher" in fm

    def test_researcher_preserves_user_invocable_false(self) -> None:
        fm = _get_frontmatter(_agent_path("researcher"))
        assert "user-invocable: false" in fm

    def test_architect_preserves_name_field(self) -> None:
        fm = _get_frontmatter(_agent_path("architect"))
        assert "name: architect" in fm

    def test_architect_preserves_user_invocable_false(self) -> None:
        fm = _get_frontmatter(_agent_path("architect"))
        assert "user-invocable: false" in fm

    def test_test_writer_preserves_name_field(self) -> None:
        fm = _get_frontmatter(_agent_path("test-writer"))
        assert "name: test-writer" in fm

    def test_test_writer_preserves_user_invocable_false(self) -> None:
        fm = _get_frontmatter(_agent_path("test-writer"))
        assert "user-invocable: false" in fm

    def test_builder_preserves_name_field(self) -> None:
        fm = _get_frontmatter(_agent_path("builder"))
        assert "name: builder" in fm

    def test_builder_preserves_user_invocable_false(self) -> None:
        fm = _get_frontmatter(_agent_path("builder"))
        assert "user-invocable: false" in fm

    def test_reviewer_preserves_name_field(self) -> None:
        fm = _get_frontmatter(_agent_path("reviewer"))
        assert "name: reviewer" in fm

    def test_reviewer_preserves_user_invocable_false(self) -> None:
        fm = _get_frontmatter(_agent_path("reviewer"))
        assert "user-invocable: false" in fm

    def test_writer_preserves_name_field(self) -> None:
        fm = _get_frontmatter(_agent_path("writer"))
        assert "name: writer" in fm

    def test_writer_preserves_user_invocable_false(self) -> None:
        fm = _get_frontmatter(_agent_path("writer"))
        assert "user-invocable: false" in fm

    def test_auditor_preserves_name_field(self) -> None:
        fm = _get_frontmatter(_agent_path("auditor"))
        assert "name: auditor" in fm

    def test_auditor_preserves_user_invocable_false(self) -> None:
        fm = _get_frontmatter(_agent_path("auditor"))
        assert "user-invocable: false" in fm

    # --- Non-pipeline agent invariants ---

    def test_orchestrator_preserves_user_invocable_true(self) -> None:
        fm = _get_frontmatter(_agent_path("orchestrator"))
        assert "user-invocable: true" in fm

    def test_kanban_planner_preserves_user_invocable_true(self) -> None:
        fm = _get_frontmatter(_agent_path("planner"))
        assert "user-invocable: true" in fm

    def test_curator_preserves_user_invocable_true(self) -> None:
        fm = _get_frontmatter(_agent_path("curator"))
        assert "user-invocable: true" in fm

    # --- Cross-cutting invariants ---

    def test_all_agents_have_name_field(self) -> None:
        """Every agent file must still have a name: field matching its filename stem."""
        for name in PIPELINE_AGENTS + NON_PIPELINE_AGENTS:
            fm = _get_frontmatter(_agent_path(name))
            assert f"name: {name}" in fm, (
                f"name field missing or wrong in {name}.agent.md"
            )

    def test_all_agents_have_description_field(self) -> None:
        """Every agent file must still have a non-empty description: field."""
        for name in PIPELINE_AGENTS + NON_PIPELINE_AGENTS:
            fm = _get_frontmatter(_agent_path(name))
            assert "description:" in fm, (
                f"description field missing from {name}.agent.md"
            )

    def test_flag_value_is_boolean_true_not_string(self) -> None:
        """The flag value must be the YAML boolean true, not a quoted string 'true'."""
        for name in PIPELINE_AGENTS:
            fm = _get_frontmatter(_agent_path(name))
            if "disable-model-invocation" in fm:
                # Reject quoted variants: "true" or 'true'
                assert 'disable-model-invocation: "true"' not in fm, (
                    f"{name}: flag value must be boolean true, not quoted string"
                )
                assert "disable-model-invocation: 'true'" not in fm, (
                    f"{name}: flag value must be boolean true, not single-quoted string"
                )


class TestFromAC_OrchestratorAgentsArrayUnchanged:
    """AC4: Orchestrator agents array must still list all 10 subagents, unchanged."""

    _EXPECTED_SUBAGENTS = frozenset({
        "planner",
        "planner",
        "researcher",
        "architect",
        "test-writer",
        "builder",
        "reviewer",
        "writer",
        "auditor",
        "curator",
    })

    def _orchestrator_frontmatter(self) -> str:
        return _get_frontmatter(_agent_path("orchestrator"))

    def test_orchestrator_agents_block_present(self) -> None:
        """Orchestrator frontmatter must contain an agents: block."""
        fm = self._orchestrator_frontmatter()
        assert "agents:" in fm

    def test_orchestrator_lists_kanban_planner(self) -> None:
        fm = self._orchestrator_frontmatter()
        assert "- kanban-planner" in fm

    def test_orchestrator_lists_planner(self) -> None:
        fm = self._orchestrator_frontmatter()
        assert "- planner" in fm

    def test_orchestrator_lists_researcher(self) -> None:
        fm = self._orchestrator_frontmatter()
        assert "- researcher" in fm

    def test_orchestrator_lists_architect(self) -> None:
        fm = self._orchestrator_frontmatter()
        assert "- architect" in fm

    def test_orchestrator_lists_test_writer(self) -> None:
        fm = self._orchestrator_frontmatter()
        assert "- test-writer" in fm

    def test_orchestrator_lists_builder(self) -> None:
        fm = self._orchestrator_frontmatter()
        assert "- builder" in fm

    def test_orchestrator_lists_reviewer(self) -> None:
        fm = self._orchestrator_frontmatter()
        assert "- reviewer" in fm

    def test_orchestrator_lists_writer(self) -> None:
        fm = self._orchestrator_frontmatter()
        assert "- writer" in fm

    def test_orchestrator_lists_auditor(self) -> None:
        fm = self._orchestrator_frontmatter()
        assert "- auditor" in fm

    def test_orchestrator_lists_curator(self) -> None:
        fm = self._orchestrator_frontmatter()
        assert "- curator" in fm

    def test_orchestrator_lists_exactly_ten_subagents(self) -> None:
        """The agents array must list exactly 10 subagents — no entry added or removed."""
        fm = self._orchestrator_frontmatter()
        entries = re.findall(r"^\s*-\s+(\S+)", fm, re.MULTILINE)
        agent_entries = [e for e in entries if e in self._EXPECTED_SUBAGENTS]
        assert len(agent_entries) == 10, (
            f"Expected 10 subagents in orchestrator agents array, found {len(agent_entries)}: {agent_entries}"
        )
