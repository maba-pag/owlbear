"""RED-phase tests for #1174 — P2-02: Migrate engine.py accessors to sub-model paths.

Focuses on AC3: Engine test fixtures use grouped config format.
AC1, AC2, AC4 are covered by test_engine_accessor_migration_1173.py (written for the
TDD RED phase that this build task depends on).

These tests FAIL until the builder migrates engine test fixture YAML configs from flat
format to 'schema: grouped' with sub-model sections, and updates direct BoardConfig()
constructions to use AgentsConfig/PipelineConfig sub-models.

Engine test files in scope (serve/kanban/tests/test_engine_*.py):
  - test_engine_coverage_1068.py — _BASE_CONFIG flat; _make_valid_config uses agent_map=
  - test_engine_init_1068.py    — _BASE_CONFIG flat; direct BoardConfig() uses agent_map=
  - test_engine_end_work_1077.py — _BASE_CONFIG flat
  - test_engine_create_edit_1070.py — _BASE_CONFIG flat
  - test_engine_reads_1069.py   — _BASE_CONFIG flat
  - test_engine_pick_tasks_1074.py — _BASE_CONFIG flat
"""

from __future__ import annotations

from pathlib import Path

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
    """AC3 — engine test YAML config strings must contain 'schema: grouped'.

    Each engine test file defines a _BASE_CONFIG YAML string used to write
    config.yml for test boards.  After migration the YAML must open with
    'schema: grouped' and nest config values under paths/pipeline/agents/policy
    sub-sections instead of listing them at the top level.

    ALL tests FAIL in RED phase because every engine test file currently uses
    flat config format with no 'schema: grouped' marker.
    """

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

    # -- sub-section presence checks for the primary file -------------------

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
    """AC3 — engine test files with direct BoardConfig() calls must use sub-model construction.

    test_engine_coverage_1068.py contains _make_valid_config() which calls
    BoardConfig(agent_map=...) — a flat-kwarg construction.  After migration it
    must use AgentsConfig(agent_map=...) passed as the 'agents=' argument.

    test_engine_init_1068.py has several direct BoardConfig(agent_map=...) call
    sites in its AC tests.  After migration all must use AgentsConfig sub-model.

    ALL tests FAIL in RED phase because neither file imports AgentsConfig.
    """

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
