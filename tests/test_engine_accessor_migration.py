"""Engine accessor migration regression tests.

Promoted from archived task-scoped suites for tasks #1173 and #1174.
"""

from __future__ import annotations

import inspect
import re
from pathlib import Path

import owlbear_kanban.engine as _engine_mod
from owlbear_kanban import KanbanEngine
from owlbear_kanban.models import PipelineConfig

# Provenance: promoted from task-scoped suites for tasks #1173 and #1174.

# Engine source loaded once at module level — all inspection tests use this.
_ENGINE_SOURCE = inspect.getsource(_engine_mod)


def _strip_string_literals(src: str) -> str:
    """Return source with string literal contents removed.

    Used to avoid false-positive matches inside user_message strings
    (e.g. "config.statuses must contain…") when scanning for banned
    code-level accessor patterns.
    """
    out = re.sub(r'""".*?"""', '""""""', src, flags=re.DOTALL)
    out = re.sub(r"'''.*?'''", "''''''", out, flags=re.DOTALL)
    out = re.sub(r'"(?:[^"\\]|\\.)*"', '""', out)
    return re.sub(r"'(?:[^'\\]|\\.)*'", "''", out)


# Engine source with string literal contents removed — code-level accessor checks only.
_CODE_SOURCE = _strip_string_literals(_ENGINE_SOURCE)

# ---------------------------------------------------------------------------
# Board fixture helpers
# ---------------------------------------------------------------------------

_GROUPED_CONFIG = """\
next_id: 1
"""


def _make_board(base_dir: Path, config_yaml: str = _GROUPED_CONFIG) -> Path:
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(config_yaml, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


# ---------------------------------------------------------------------------
# AC1 — Tests validate engine methods use sub-model access paths
# ---------------------------------------------------------------------------


class TestFromAC_SubmodelAccessPaths:
    """AC1 — engine.py must reference sub-model paths for all config access sites."""

    # -- paths group ---------------------------------------------------------

    def test_engine_source_contains_paths_tasks_dir(self) -> None:
        """engine.py must access tasks_dir via config.paths.tasks_dir after migration."""
        assert "paths.tasks_dir" in _ENGINE_SOURCE, (
            "engine.py must contain 'paths.tasks_dir' — currently uses forwarding property config.tasks_dir"
        )

    def test_engine_source_contains_paths_archive_dir(self) -> None:
        """engine.py must access archive_dir via config.paths.archive_dir after migration."""
        assert "paths.archive_dir" in _ENGINE_SOURCE, (
            "engine.py must contain 'paths.archive_dir' — currently uses forwarding property config.archive_dir"
        )

    # -- pipeline group ------------------------------------------------------

    def test_engine_source_contains_pipeline_entry_status(self) -> None:
        """engine.py must access entry_status via config.pipeline.entry_status."""
        assert "pipeline.entry_status" in _ENGINE_SOURCE, (
            "engine.py must contain 'pipeline.entry_status' — currently uses forwarding property config.entry_status"
        )

    def test_engine_source_contains_pipeline_terminal_status(self) -> None:
        """engine.py must access terminal_status via config.pipeline.terminal_status."""
        assert "pipeline.terminal_status" in _ENGINE_SOURCE, (
            "engine.py must contain 'pipeline.terminal_status' — "
            "currently uses forwarding property config.terminal_status"
        )

    def test_engine_source_contains_pipeline_wave_size(self) -> None:
        """engine.py must access wave_size via config.pipeline.wave_size."""
        assert "pipeline.wave_size" in _ENGINE_SOURCE, (
            "engine.py must contain 'pipeline.wave_size' — currently uses forwarding property config.wave_size"
        )

    def test_engine_source_contains_pipeline_claim_timeout(self) -> None:
        """engine.py must access claim_timeout via config.pipeline.claim_timeout."""
        assert "pipeline.claim_timeout" in _ENGINE_SOURCE, (
            "engine.py must contain 'pipeline.claim_timeout' — currently uses forwarding property config.claim_timeout"
        )

    def test_engine_source_contains_pipeline_default_priority(self) -> None:
        """engine.py must access default_priority via config.pipeline.default_priority."""
        assert "pipeline.default_priority" in _ENGINE_SOURCE, (
            "engine.py must contain 'pipeline.default_priority' — "
            "currently uses config.defaults.priority (old defaults sub-model)"
        )

    def test_engine_source_contains_pipeline_statuses(self) -> None:
        """engine.py must access statuses via config.pipeline.statuses after migration."""
        assert "pipeline.statuses" in _ENGINE_SOURCE, (
            "engine.py must contain 'pipeline.statuses' — currently uses top-level forwarding config.statuses"
        )

    def test_engine_source_contains_pipeline_priorities(self) -> None:
        """engine.py must access priorities via config.pipeline.priorities after migration."""
        assert "pipeline.priorities" in _ENGINE_SOURCE, (
            "engine.py must contain 'pipeline.priorities' — currently uses top-level forwarding config.priorities"
        )

    # -- agents group --------------------------------------------------------

    def test_engine_source_contains_agents_agent_map(self) -> None:
        """engine.py must access agent_map via config.agents.agent_map."""
        assert "agents.agent_map" in _ENGINE_SOURCE, (
            "engine.py must contain 'agents.agent_map' — currently uses forwarding property config.agent_map"
        )

    def test_engine_source_contains_agents_agent_types(self) -> None:
        """engine.py must access agent_types via config.agents.agent_types."""
        assert "agents.agent_types" in _ENGINE_SOURCE, (
            "engine.py must contain 'agents.agent_types' — currently uses forwarding property config.agent_types"
        )

    def test_engine_source_contains_agents_agent_compatibility(self) -> None:
        """engine.py must access agent_compatibility via config.agents.agent_compatibility."""
        assert "agents.agent_compatibility" in _ENGINE_SOURCE, (
            "engine.py must contain 'agents.agent_compatibility' — "
            "currently uses forwarding property config.agent_compatibility"
        )

    # -- policy group --------------------------------------------------------

    def test_engine_source_contains_policy_archival_reasons(self) -> None:
        """engine.py must access archival_reasons via config.policy.archival_reasons."""
        assert "policy.archival_reasons" in _ENGINE_SOURCE, (
            "engine.py must contain 'policy.archival_reasons' — "
            "currently uses forwarding property config.archival_reasons"
        )

    def test_engine_source_contains_policy_status_predicates(self) -> None:
        """engine.py must access status_predicates via config.policy.status_predicates."""
        assert "policy.status_predicates" in _ENGINE_SOURCE, (
            "engine.py must contain 'policy.status_predicates' — "
            "currently uses forwarding property config.status_predicates"
        )


# ---------------------------------------------------------------------------
# AC2 — Engine test fixtures construct BoardConfig with grouped sub-model format
# ---------------------------------------------------------------------------


class TestFromAC_GroupedFixtures:
    """AC2 — PipelineConfig must expose statuses and priorities for engine access."""

    def test_pipeline_config_has_statuses_field(self) -> None:
        """PipelineConfig must declare a 'statuses' field to support pipeline.statuses access."""
        fields = PipelineConfig.model_fields
        assert "statuses" in fields, (
            f"PipelineConfig must have 'statuses' field for config.pipeline.statuses access; "
            f"current fields: {list(fields)}"
        )

    def test_pipeline_config_has_priorities_field(self) -> None:
        """PipelineConfig must declare a 'priorities' field to support pipeline.priorities access."""
        fields = PipelineConfig.model_fields
        assert "priorities" in fields, (
            f"PipelineConfig must have 'priorities' field for config.pipeline.priorities access; "
            f"current fields: {list(fields)}"
        )

    def test_engine_board_config_pipeline_statuses_returns_statuses_list(self, tmp_path: Path) -> None:
        """board_config().pipeline.statuses must return the board statuses list."""
        kanban_dir = _make_board(tmp_path)
        engine = KanbanEngine(kanban_dir)
        cfg = engine.board_config()
        assert cfg.pipeline.statuses == ["research", "backlog", "todo", "done"], (  # type: ignore[attr-defined]
            f"board_config().pipeline.statuses must equal statuses list; got {cfg.pipeline!r}"
        )

    def test_engine_board_config_pipeline_priorities_returns_priorities_list(self, tmp_path: Path) -> None:
        """board_config().pipeline.priorities must return the board priorities list."""
        kanban_dir = _make_board(tmp_path)
        engine = KanbanEngine(kanban_dir)
        cfg = engine.board_config()
        assert cfg.pipeline.priorities == ["someday", "important", "critical"], (  # type: ignore[attr-defined]
            f"board_config().pipeline.priorities must equal priorities list; got {cfg.pipeline!r}"
        )


# ---------------------------------------------------------------------------
# AC4 — Tests confirm no engine code path relies on forwarding properties
# ---------------------------------------------------------------------------


class TestFromAC_NoForwardingProperties:
    """AC4 — engine.py must contain no forwarding property calls after migration."""

    # -- paths group ---------------------------------------------------------

    def test_no_raw_tasks_dir_forwarding_call(self) -> None:
        """engine.py must not call config.tasks_dir; use config.paths.tasks_dir instead."""
        assert "config.tasks_dir" not in _ENGINE_SOURCE, (
            "engine.py still calls forwarding property 'config.tasks_dir' — "
            "migrate all sites to 'config.paths.tasks_dir'"
        )

    def test_no_raw_archive_dir_forwarding_call(self) -> None:
        """engine.py must not call config.archive_dir; use config.paths.archive_dir instead."""
        assert "config.archive_dir" not in _ENGINE_SOURCE, (
            "engine.py still calls forwarding property 'config.archive_dir' — "
            "migrate all sites to 'config.paths.archive_dir'"
        )

    # -- pipeline group ------------------------------------------------------

    def test_no_raw_entry_status_forwarding_call(self) -> None:
        """engine.py must not call config.entry_status; use config.pipeline.entry_status."""
        assert "config.entry_status" not in _ENGINE_SOURCE, (
            "engine.py still calls forwarding property 'config.entry_status' — "
            "migrate all sites to 'config.pipeline.entry_status'"
        )

    def test_no_raw_terminal_status_forwarding_call(self) -> None:
        """engine.py must not call config.terminal_status; use config.pipeline.terminal_status."""
        assert "config.terminal_status" not in _ENGINE_SOURCE, (
            "engine.py still calls forwarding property 'config.terminal_status' — "
            "migrate all sites to 'config.pipeline.terminal_status'"
        )

    def test_no_raw_wave_size_forwarding_call(self) -> None:
        """engine.py must not call config.wave_size; use config.pipeline.wave_size."""
        assert "config.wave_size" not in _ENGINE_SOURCE, (
            "engine.py still calls forwarding property 'config.wave_size' — "
            "migrate all sites to 'config.pipeline.wave_size'"
        )

    def test_no_raw_claim_timeout_forwarding_call(self) -> None:
        """engine.py must not call config.claim_timeout; use config.pipeline.claim_timeout."""
        assert "config.claim_timeout" not in _ENGINE_SOURCE, (
            "engine.py still calls forwarding property 'config.claim_timeout' — "
            "migrate all sites to 'config.pipeline.claim_timeout'"
        )

    def test_no_defaults_priority_access(self) -> None:
        """engine.py must not access config.defaults.priority; use config.pipeline.default_priority."""
        assert "config.defaults" not in _ENGINE_SOURCE, (
            "engine.py still accesses 'config.defaults.priority' (old defaults sub-model) — "
            "migrate to 'config.pipeline.default_priority'"
        )

    # -- agents group --------------------------------------------------------

    def test_no_raw_agent_map_forwarding_call(self) -> None:
        """engine.py must not call config.agent_map; use config.agents.agent_map."""
        assert "config.agent_map" not in _ENGINE_SOURCE, (
            "engine.py still calls forwarding property 'config.agent_map' — "
            "migrate all sites to 'config.agents.agent_map'"
        )

    def test_no_raw_agent_types_forwarding_call(self) -> None:
        """engine.py must not call config.agent_types; use config.agents.agent_types."""
        assert "config.agent_types" not in _ENGINE_SOURCE, (
            "engine.py still calls forwarding property 'config.agent_types' — "
            "migrate all sites to 'config.agents.agent_types'"
        )

    def test_no_raw_agent_compatibility_forwarding_call(self) -> None:
        """engine.py must not call config.agent_compatibility; use config.agents.agent_compatibility."""
        assert "config.agent_compatibility" not in _ENGINE_SOURCE, (
            "engine.py still calls forwarding property 'config.agent_compatibility' — "
            "migrate all sites to 'config.agents.agent_compatibility'"
        )

    # -- policy group --------------------------------------------------------

    def test_no_raw_archival_reasons_forwarding_call(self) -> None:
        """engine.py must not call config.archival_reasons; use config.policy.archival_reasons."""
        assert "config.archival_reasons" not in _ENGINE_SOURCE, (
            "engine.py still calls forwarding property 'config.archival_reasons' — "
            "migrate all sites to 'config.policy.archival_reasons'"
        )

    def test_no_raw_status_predicates_forwarding_call(self) -> None:
        """engine.py must not call config.status_predicates; use config.policy.status_predicates."""
        assert "config.status_predicates" not in _ENGINE_SOURCE, (
            "engine.py still calls forwarding property 'config.status_predicates' — "
            "migrate all sites to 'config.policy.status_predicates'"
        )

    # -- missing patterns from prior cycle (AC3 exhaustive list) ------------

    def test_no_raw_default_priority_forwarding_call(self) -> None:
        """engine.py must not call config.default_priority; use config.pipeline.default_priority."""
        assert "config.default_priority" not in _ENGINE_SOURCE, (
            "engine.py contains 'config.default_priority' — migrate to 'config.pipeline.default_priority'"
        )

    def test_no_raw_statuses_forwarding_call(self) -> None:
        """engine.py must contain zero code-level config.statuses calls after migration."""
        code_hits = _CODE_SOURCE.count("config.statuses")
        assert code_hits == 0, (
            f"engine.py still has {code_hits} code-level 'config.statuses' accessor(s) — "
            "remove the duplicate dead lines at ~2962 and ~3043 "
            "(valid_statuses / statuses already reassigned from config.pipeline.statuses)"
        )

    def test_no_raw_priorities_forwarding_call(self) -> None:
        """engine.py must contain zero code-level config.priorities calls after migration."""
        code_hits = _CODE_SOURCE.count("config.priorities")
        assert code_hits == 0, (
            f"engine.py still has {code_hits} code-level 'config.priorities' accessor(s) — "
            "migrate all sites to 'config.pipeline.priorities'"
        )

    def test_no_raw_non_impl_tags_forwarding_call(self) -> None:
        """engine.py must not call config.non_impl_tags; use config.policy.non_impl_tags."""
        assert "config.non_impl_tags" not in _ENGINE_SOURCE, (
            "engine.py contains 'config.non_impl_tags' — migrate to 'config.policy.non_impl_tags'"
        )


# ---------------------------------------------------------------------------
# AC4 — Regression gate: grouped pattern count must stay >= 50
# ---------------------------------------------------------------------------


class TestFromAC_GroupedRegressionGate:
    """AC4 — engine.py must retain a high count of grouped config accessor patterns."""

    def test_grouped_pattern_count_meets_regression_threshold(self) -> None:
        """Total occurrences of paths./pipeline./agents./policy. in engine source >= 50."""
        pattern = re.compile(r"(?:paths|pipeline|agents|policy)\.")
        count = len(pattern.findall(_ENGINE_SOURCE))
        assert count >= 50, (
            f"engine.py contains only {count} grouped accessor pattern occurrence(s) — "
            "expected >= 50; a mass-revert of the sub-model migration may have occurred"
        )


_KANBAN_TESTS = Path(__file__).parent.parent / "serve" / "kanban" / "tests"

_ENGINE_COVERAGE_FILE = _KANBAN_TESTS / "test_engine_coverage_1068.py"
_ENGINE_INIT_FILE = _KANBAN_TESTS / "test_engine_init_1068.py"
_ENGINE_END_WORK_FILE = _KANBAN_TESTS / "test_engine_end_work_1077.py"
_ENGINE_CREATE_EDIT_FILE = _KANBAN_TESTS / "test_engine_create_edit_1070.py"
_ENGINE_READS_FILE = _KANBAN_TESTS / "test_engine_reads_1069.py"
_ENGINE_PICK_TASKS_FILE = _KANBAN_TESTS / "test_engine_pick_tasks_1074.py"


# ---------------------------------------------------------------------------
# AC3 — Engine test YAML fixtures must use grouped schema format
# ---------------------------------------------------------------------------


class TestFromAC_FixtureGroupedYaml:
    """AC3 — engine test YAML config strings must contain 'schema: grouped'."""

    def test_engine_coverage_base_config_uses_grouped_schema(self) -> None:
        """test_engine_coverage_1068.py must contain 'schema: grouped' in its YAML config."""
        src = _ENGINE_COVERAGE_FILE.read_text(encoding="utf-8")
        assert "schema: grouped" in src, (
            "test_engine_coverage_1068.py: _BASE_CONFIG still uses flat config format; "
            "must be migrated to 'schema: grouped' with pipeline/agents/policy sub-sections"
        )

    def test_engine_init_base_config_uses_grouped_schema(self) -> None:
        """test_engine_init_1068.py must contain 'schema: grouped' in its YAML config."""
        src = _ENGINE_INIT_FILE.read_text(encoding="utf-8")
        assert "schema: grouped" in src, (
            "test_engine_init_1068.py: _BASE_CONFIG still uses flat config format; "
            "must be migrated to 'schema: grouped' with pipeline/agents/policy sub-sections"
        )

    def test_engine_end_work_base_config_uses_grouped_schema(self) -> None:
        """test_engine_end_work_1077.py must contain 'schema: grouped' in its YAML config."""
        src = _ENGINE_END_WORK_FILE.read_text(encoding="utf-8")
        assert "schema: grouped" in src, (
            "test_engine_end_work_1077.py: _BASE_CONFIG still uses flat config format; "
            "must be migrated to 'schema: grouped' with pipeline/agents/policy sub-sections"
        )

    def test_engine_create_edit_base_config_uses_grouped_schema(self) -> None:
        """test_engine_create_edit_1070.py must contain 'schema: grouped' in its YAML config."""
        src = _ENGINE_CREATE_EDIT_FILE.read_text(encoding="utf-8")
        assert "schema: grouped" in src, (
            "test_engine_create_edit_1070.py: _BASE_CONFIG still uses flat config format; "
            "must be migrated to 'schema: grouped' with pipeline/agents/policy sub-sections"
        )

    def test_engine_reads_base_config_uses_grouped_schema(self) -> None:
        """test_engine_reads_1069.py must contain 'schema: grouped' in its YAML config."""
        src = _ENGINE_READS_FILE.read_text(encoding="utf-8")
        assert "schema: grouped" in src, (
            "test_engine_reads_1069.py: _BASE_CONFIG still uses flat config format; "
            "must be migrated to 'schema: grouped' with pipeline/agents/policy sub-sections"
        )

    def test_engine_pick_tasks_base_config_uses_grouped_schema(self) -> None:
        """test_engine_pick_tasks_1074.py must contain 'schema: grouped' in its YAML config."""
        src = _ENGINE_PICK_TASKS_FILE.read_text(encoding="utf-8")
        assert "schema: grouped" in src, (
            "test_engine_pick_tasks_1074.py: _BASE_CONFIG still uses flat config format; "
            "must be migrated to 'schema: grouped' with pipeline/agents/policy sub-sections"
        )

    def test_engine_coverage_config_has_pipeline_section(self) -> None:
        """test_engine_coverage_1068.py _BASE_CONFIG must contain 'pipeline:' sub-section."""
        src = _ENGINE_COVERAGE_FILE.read_text(encoding="utf-8")
        assert "pipeline:" in src, (
            "test_engine_coverage_1068.py: _BASE_CONFIG lacks 'pipeline:' sub-section; "
            "entry_status/terminal_status/wave_size/claim_timeout must move under pipeline:"
        )

    def test_engine_coverage_config_has_agents_section(self) -> None:
        """test_engine_coverage_1068.py _BASE_CONFIG must contain 'agents:' sub-section."""
        src = _ENGINE_COVERAGE_FILE.read_text(encoding="utf-8")
        assert "agents:" in src, (
            "test_engine_coverage_1068.py: _BASE_CONFIG lacks 'agents:' sub-section; "
            "agent_map/agent_types/agent_compatibility must move under agents:"
        )

    def test_engine_init_config_has_pipeline_section(self) -> None:
        """test_engine_init_1068.py _BASE_CONFIG must contain 'pipeline:' sub-section."""
        src = _ENGINE_INIT_FILE.read_text(encoding="utf-8")
        assert "pipeline:" in src, (
            "test_engine_init_1068.py: _BASE_CONFIG lacks 'pipeline:' sub-section; "
            "entry_status/terminal_status/wave_size must move under pipeline:"
        )

    def test_engine_init_config_has_agents_section(self) -> None:
        """test_engine_init_1068.py _BASE_CONFIG must contain 'agents:' sub-section."""
        src = _ENGINE_INIT_FILE.read_text(encoding="utf-8")
        assert "agents:" in src, (
            "test_engine_init_1068.py: _BASE_CONFIG lacks 'agents:' sub-section; "
            "agent_map/agent_types/agent_compatibility must move under agents:"
        )


# ---------------------------------------------------------------------------
# AC3 — Direct BoardConfig() construction must use sub-model args
# ---------------------------------------------------------------------------


class TestFromAC_FixtureDirectConstruction:
    """AC3 — direct BoardConfig() calls must use grouped sub-model construction."""

    def test_engine_coverage_imports_agents_config(self) -> None:
        """test_engine_coverage_1068.py must import AgentsConfig for grouped construction."""
        src = _ENGINE_COVERAGE_FILE.read_text(encoding="utf-8")
        assert "AgentsConfig" in src, (
            "test_engine_coverage_1068.py does not import AgentsConfig; "
            "_make_valid_config() still uses flat 'agent_map=' kwarg — "
            "migrate to 'agents=AgentsConfig(agent_map=...)'"
        )

    def test_engine_init_imports_agents_config(self) -> None:
        """test_engine_init_1068.py must import AgentsConfig for grouped construction."""
        src = _ENGINE_INIT_FILE.read_text(encoding="utf-8")
        assert "AgentsConfig" in src, (
            "test_engine_init_1068.py does not import AgentsConfig; "
            "direct BoardConfig() calls still use flat 'agent_map=' kwarg — "
            "migrate all call sites to 'agents=AgentsConfig(agent_map=...)'"
        )

    def test_engine_coverage_make_valid_config_uses_agents_submodel(self) -> None:
        """test_engine_coverage_1068.py _make_valid_config must use agents=AgentsConfig(...)."""
        src = _ENGINE_COVERAGE_FILE.read_text(encoding="utf-8")
        assert "agents=AgentsConfig(" in src, (
            "test_engine_coverage_1068.py: _make_valid_config() still calls "
            "BoardConfig(agent_map=...) — must use agents=AgentsConfig(agent_map=...)"
        )

    def test_engine_init_boardconfig_calls_use_agents_submodel(self) -> None:
        """test_engine_init_1068.py direct BoardConfig() calls must use agents=AgentsConfig(...)."""
        src = _ENGINE_INIT_FILE.read_text(encoding="utf-8")
        assert "agents=AgentsConfig(" in src, (
            "test_engine_init_1068.py: BoardConfig() call sites still use flat "
            "'agent_map=' kwarg — migrate all to agents=AgentsConfig(agent_map=...)"
        )


# ---------------------------------------------------------------------------
# AC3 — Predicate YAML in str.replace() expansions must be correctly nested
# ---------------------------------------------------------------------------


class TestFromAC_PredicateYamlNesting:
    """AC3 — predicate YAML replacements must nest keys under status_predicates."""

    def test_create_edit_predicate_research_indentation_is_correct(self) -> None:
        """test_engine_create_edit_1070.py: 'research:' must be at 8-space indent in the string literal."""
        src = _ENGINE_CREATE_EDIT_FILE.read_text(encoding="utf-8")
        assert '"        research:' in src, (
            "test_engine_create_edit_1070.py: predicate replacement string has 'research:' "
            "at only 4-space indent — in grouped schema this makes it a sibling of "
            "'status_predicates:' rather than a child; fix the string literal to use 8-space indent"
        )

    def test_end_work_predicate_review_indentation_is_correct(self) -> None:
        """test_engine_end_work_1077.py: 'review:' must be at 8-space indent in the string literal."""
        src = _ENGINE_END_WORK_FILE.read_text(encoding="utf-8")
        assert '"        review:' in src, (
            "test_engine_end_work_1077.py: predicate replacement string has 'review:' "
            "at only 4-space indent — in grouped schema this makes it a sibling of "
            "'status_predicates:' rather than a child; fix the string literal to use 8-space indent"
        )

    def test_create_edit_predicate_not_at_sibling_indent(self) -> None:
        """test_engine_create_edit_1070.py: 4-space 'research:' (sibling indent) must be absent."""
        src = _ENGINE_CREATE_EDIT_FILE.read_text(encoding="utf-8")
        assert '"    research:' not in src, (
            "test_engine_create_edit_1070.py: predicate replacement still uses 4-space "
            "indent for 'research:' — this produces malformed YAML in grouped schema "
            "where status_predicates: is itself at 4-space indent under policy:"
        )

    def test_end_work_predicate_not_at_sibling_indent(self) -> None:
        """test_engine_end_work_1077.py: 4-space 'review:' (sibling indent) must be absent."""
        src = _ENGINE_END_WORK_FILE.read_text(encoding="utf-8")
        assert '"    review:' not in src, (
            "test_engine_end_work_1077.py: predicate replacement still uses 4-space "
            "indent for 'review:' — this produces malformed YAML in grouped schema "
            "where status_predicates: is itself at 4-space indent under policy:"
        )


# ---------------------------------------------------------------------------
# AC5 (td:2) — TestFromAC_ValidateEngineConfig mutation sites use sub-model paths
# ---------------------------------------------------------------------------


class TestFromAC_MutationSubModelPaths:
    """AC5 — mutation sites in TestFromAC_ValidateEngineConfig must use sub-model paths."""

    def test_pipeline_entry_status_mutation_uses_submodel(self) -> None:
        """config.pipeline.entry_status = ... must appear in test_engine_coverage_1068.py."""
        src = _ENGINE_COVERAGE_FILE.read_text(encoding="utf-8")
        assert "config.pipeline.entry_status =" in src, (
            "test_engine_coverage_1068.py: mutation site still uses forwarding property "
            "'config.entry_status =' — migrate to 'config.pipeline.entry_status ='"
        )

    def test_pipeline_terminal_status_mutation_uses_submodel(self) -> None:
        """config.pipeline.terminal_status = ... must appear in test_engine_coverage_1068.py."""
        src = _ENGINE_COVERAGE_FILE.read_text(encoding="utf-8")
        assert "config.pipeline.terminal_status =" in src, (
            "test_engine_coverage_1068.py: mutation site still uses forwarding property "
            "'config.terminal_status =' — migrate to 'config.pipeline.terminal_status ='"
        )

    def test_pipeline_claim_timeout_mutation_uses_submodel(self) -> None:
        """config.pipeline.claim_timeout = ... must appear in test_engine_coverage_1068.py."""
        src = _ENGINE_COVERAGE_FILE.read_text(encoding="utf-8")
        assert "config.pipeline.claim_timeout =" in src, (
            "test_engine_coverage_1068.py: mutation site still uses forwarding property "
            "'config.claim_timeout =' — migrate to 'config.pipeline.claim_timeout ='"
        )

    def test_agents_agent_map_mutation_uses_submodel(self) -> None:
        """config.agents.agent_map = ... must appear in test_engine_coverage_1068.py."""
        src = _ENGINE_COVERAGE_FILE.read_text(encoding="utf-8")
        assert "config.agents.agent_map =" in src, (
            "test_engine_coverage_1068.py: mutation site still uses forwarding property "
            "'config.agent_map =' — migrate to 'config.agents.agent_map ='"
        )

    def test_agents_agent_compatibility_mutation_uses_submodel(self) -> None:
        """config.agents.agent_compatibility = ... must appear in test_engine_coverage_1068.py."""
        src = _ENGINE_COVERAGE_FILE.read_text(encoding="utf-8")
        assert "config.agents.agent_compatibility =" in src, (
            "test_engine_coverage_1068.py: mutation site still uses forwarding property "
            "'config.agent_compatibility =' — migrate to 'config.agents.agent_compatibility ='"
        )

    def test_no_flat_entry_status_mutation(self) -> None:
        """config.entry_status = ... must not appear in test_engine_coverage_1068.py."""
        src = _ENGINE_COVERAGE_FILE.read_text(encoding="utf-8")
        assert "config.entry_status =" not in src, (
            "test_engine_coverage_1068.py: forwarding property mutation 'config.entry_status =' "
            "is still present — this raises AttributeError at runtime; migrate to "
            "'config.pipeline.entry_status ='"
        )

    def test_no_flat_terminal_status_mutation(self) -> None:
        """config.terminal_status = ... must not appear in test_engine_coverage_1068.py."""
        src = _ENGINE_COVERAGE_FILE.read_text(encoding="utf-8")
        assert "config.terminal_status =" not in src, (
            "test_engine_coverage_1068.py: forwarding property mutation 'config.terminal_status =' "
            "is still present — this raises AttributeError at runtime; migrate to "
            "'config.pipeline.terminal_status ='"
        )

    def test_no_flat_agent_map_mutation(self) -> None:
        """config.agent_map = ... must not appear in test_engine_coverage_1068.py."""
        src = _ENGINE_COVERAGE_FILE.read_text(encoding="utf-8")
        assert "config.agent_map =" not in src, (
            "test_engine_coverage_1068.py: forwarding property mutation 'config.agent_map =' "
            "is still present — this raises AttributeError at runtime; migrate to "
            "'config.agents.agent_map ='"
        )

    def test_no_flat_claim_timeout_mutation(self) -> None:
        """config.claim_timeout = ... must not appear in test_engine_coverage_1068.py."""
        src = _ENGINE_COVERAGE_FILE.read_text(encoding="utf-8")
        assert "config.claim_timeout =" not in src, (
            "test_engine_coverage_1068.py: forwarding property mutation 'config.claim_timeout =' "
            "is still present — this raises AttributeError at runtime; migrate to "
            "'config.pipeline.claim_timeout ='"
        )

    def test_no_flat_agent_compatibility_mutation(self) -> None:
        """config.agent_compatibility = ... must not appear in test_engine_coverage_1068.py."""
        src = _ENGINE_COVERAGE_FILE.read_text(encoding="utf-8")
        assert "config.agent_compatibility =" not in src, (
            "test_engine_coverage_1068.py: forwarding property mutation 'config.agent_compatibility =' "
            "is still present — this raises AttributeError at runtime; migrate to "
            "'config.agents.agent_compatibility ='"
        )

    def test_all_five_submodel_mutation_patterns_present(self) -> None:
        """All five sub-model mutation patterns must be present together in test_engine_coverage_1068.py."""
        src = _ENGINE_COVERAGE_FILE.read_text(encoding="utf-8")
        patterns = [
            "config.pipeline.entry_status =",
            "config.pipeline.terminal_status =",
            "config.pipeline.claim_timeout =",
            "config.agents.agent_map =",
            "config.agents.agent_compatibility =",
        ]
        missing = [pattern for pattern in patterns if pattern not in src]
        assert not missing, (
            f"test_engine_coverage_1068.py: {len(missing)} sub-model mutation pattern(s) not yet migrated: {missing}"
        )
