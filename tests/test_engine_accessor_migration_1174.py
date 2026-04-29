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


# ---------------------------------------------------------------------------
# AC3 — Predicate YAML in str.replace() expansions must be correctly nested
# ---------------------------------------------------------------------------


class TestFromAC_PredicateYamlNesting:
    """AC3 — predicate YAML replacements in test fixtures must nest keys under status_predicates:.

    In grouped schema, policy.status_predicates: sits at 4-space indent (under policy:).
    Predicate keys (research:, review:) must be 4 MORE spaces deep (8 total) so they
    are children of status_predicates:, not siblings.

    Current str.replace() replacement strings use 4-space indent for predicate keys —
    in grouped schema that makes them siblings of status_predicates:.

    ALL tests FAIL in RED phase because the replacement strings still use 4-space indent.
    """

    def test_create_edit_predicate_research_indentation_is_correct(self) -> None:
        """test_engine_create_edit_1070.py: 'research:' must be at 8-space indent in the string literal."""
        src = _ENGINE_CREATE_EDIT_FILE.read_text(encoding="utf-8")
        # In grouped schema, status_predicates: is at 4-space indent under policy:;
        # predicate keys must be 4 more spaces = 8-space indent inside the string literal.
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
    """AC5 (td:2) — mutation sites in TestFromAC_ValidateEngineConfig must use sub-model paths.

    test_engine_coverage_1068.py lines 246-276 mutate config fields via forwarding
    properties (config.entry_status = ...).  Those properties are read-only @property
    with no setter — assignments raise AttributeError at runtime.

    After migration all five mutation sites must use sub-model paths:
      config.pipeline.entry_status      config.pipeline.terminal_status
      config.pipeline.claim_timeout     config.agents.agent_map
      config.agents.agent_compatibility

    Happy-path tests: sub-model patterns ARE present. FAIL currently (absent).
    Edge-case tests:  forwarding-property patterns are ABSENT. FAIL currently (present).
    Boundary test:    all five sub-model patterns present simultaneously.
    """

    # --- Happy path: sub-model mutation patterns are present ---

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

    # --- Edge case: forwarding-property mutation patterns are absent ---

    def test_no_flat_entry_status_mutation(self) -> None:
        """config.entry_status = ... must NOT appear in test_engine_coverage_1068.py."""
        src = _ENGINE_COVERAGE_FILE.read_text(encoding="utf-8")
        assert "config.entry_status =" not in src, (
            "test_engine_coverage_1068.py: forwarding property mutation 'config.entry_status =' "
            "is still present — this raises AttributeError at runtime; migrate to "
            "'config.pipeline.entry_status ='"
        )

    def test_no_flat_terminal_status_mutation(self) -> None:
        """config.terminal_status = ... must NOT appear in test_engine_coverage_1068.py."""
        src = _ENGINE_COVERAGE_FILE.read_text(encoding="utf-8")
        assert "config.terminal_status =" not in src, (
            "test_engine_coverage_1068.py: forwarding property mutation 'config.terminal_status =' "
            "is still present — this raises AttributeError at runtime; migrate to "
            "'config.pipeline.terminal_status ='"
        )

    def test_no_flat_agent_map_mutation(self) -> None:
        """config.agent_map = ... must NOT appear in test_engine_coverage_1068.py."""
        src = _ENGINE_COVERAGE_FILE.read_text(encoding="utf-8")
        assert "config.agent_map =" not in src, (
            "test_engine_coverage_1068.py: forwarding property mutation 'config.agent_map =' "
            "is still present — this raises AttributeError at runtime; migrate to "
            "'config.agents.agent_map ='"
        )

    def test_no_flat_claim_timeout_mutation(self) -> None:
        """config.claim_timeout = ... must NOT appear in test_engine_coverage_1068.py."""
        src = _ENGINE_COVERAGE_FILE.read_text(encoding="utf-8")
        assert "config.claim_timeout =" not in src, (
            "test_engine_coverage_1068.py: forwarding property mutation 'config.claim_timeout =' "
            "is still present — this raises AttributeError at runtime; migrate to "
            "'config.pipeline.claim_timeout ='"
        )

    def test_no_flat_agent_compatibility_mutation(self) -> None:
        """config.agent_compatibility = ... must NOT appear in test_engine_coverage_1068.py."""
        src = _ENGINE_COVERAGE_FILE.read_text(encoding="utf-8")
        assert "config.agent_compatibility =" not in src, (
            "test_engine_coverage_1068.py: forwarding property mutation 'config.agent_compatibility =' "
            "is still present — this raises AttributeError at runtime; migrate to "
            "'config.agents.agent_compatibility ='"
        )

    # --- Boundary: all five sub-model mutation patterns present simultaneously ---

    def test_all_five_submodel_mutation_patterns_present(self) -> None:
        """All 5 sub-model mutation patterns must be present together in test_engine_coverage_1068.py."""
        src = _ENGINE_COVERAGE_FILE.read_text(encoding="utf-8")
        patterns = [
            "config.pipeline.entry_status =",
            "config.pipeline.terminal_status =",
            "config.pipeline.claim_timeout =",
            "config.agents.agent_map =",
            "config.agents.agent_compatibility =",
        ]
        missing = [p for p in patterns if p not in src]
        assert not missing, (
            f"test_engine_coverage_1068.py: {len(missing)} sub-model mutation pattern(s) "
            f"not yet migrated: {missing}"
        )
