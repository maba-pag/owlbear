"""RED-phase tests for #1173 — P2-01: Engine sub-model accessor migration.

All tests FAIL until the builder migrates the ~59 engine.py access sites:
  - config.paths.tasks_dir   (was config.tasks_dir forwarding property)
  - config.paths.archive_dir (was config.archive_dir forwarding property)
  - config.pipeline.entry_status, .terminal_status, .wave_size,
    .claim_timeout, .default_priority, .statuses, .priorities
  - config.agents.agent_map, .agent_types, .agent_compatibility
  - config.policy.archival_reasons, .status_predicates
  - config.pipeline.default_priority (was config.defaults.priority)

Adds PipelineConfig.statuses and PipelineConfig.priorities fields to support
config.pipeline.statuses / config.pipeline.priorities access from the engine.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import owlbear_kanban.engine as _engine_mod
from owlbear_kanban import KanbanEngine
from owlbear_kanban.models import PipelineConfig

# Engine source loaded once at module level — all inspection tests use this.
_ENGINE_SOURCE = inspect.getsource(_engine_mod)

# ---------------------------------------------------------------------------
# Board fixture helpers
# ---------------------------------------------------------------------------

_GROUPED_CONFIG = """\
schema: grouped
statuses:
  - research
  - backlog
  - todo
  - done
priorities:
  - someday
  - important
  - critical
next_id: 1
activity_log: false
paths:
  tasks_dir: tasks
  archive_dir: archive
pipeline:
  entry_status: research
  terminal_status: done
  wave_size: 4
  claim_timeout: 1h
  default_priority: important
agents:
  agent_map:
    research: researcher
    backlog: architect
    todo: builder
    done: auditor
  agent_types: {}
  agent_compatibility: {}
policy:
  non_impl_tags: []
  archival_reasons:
    - completed
    - deprecated
    - dropped
    - duplicate
    - wontfix
  status_predicates: {}
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
    """AC1 — engine.py must reference sub-model paths for all 59 config access sites.

    Each test checks that the engine source contains the expected sub-model pattern.
    ALL tests FAIL in RED phase because engine.py currently uses forwarding properties.
    """

    # -- paths group ---------------------------------------------------------

    def test_engine_source_contains_paths_tasks_dir(self) -> None:
        """engine.py must access tasks_dir via config.paths.tasks_dir after migration."""
        assert "paths.tasks_dir" in _ENGINE_SOURCE, (
            "engine.py must contain 'paths.tasks_dir' — "
            "currently uses forwarding property config.tasks_dir"
        )

    def test_engine_source_contains_paths_archive_dir(self) -> None:
        """engine.py must access archive_dir via config.paths.archive_dir after migration."""
        assert "paths.archive_dir" in _ENGINE_SOURCE, (
            "engine.py must contain 'paths.archive_dir' — "
            "currently uses forwarding property config.archive_dir"
        )

    # -- pipeline group ------------------------------------------------------

    def test_engine_source_contains_pipeline_entry_status(self) -> None:
        """engine.py must access entry_status via config.pipeline.entry_status."""
        assert "pipeline.entry_status" in _ENGINE_SOURCE, (
            "engine.py must contain 'pipeline.entry_status' — "
            "currently uses forwarding property config.entry_status"
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
            "engine.py must contain 'pipeline.wave_size' — "
            "currently uses forwarding property config.wave_size"
        )

    def test_engine_source_contains_pipeline_claim_timeout(self) -> None:
        """engine.py must access claim_timeout via config.pipeline.claim_timeout."""
        assert "pipeline.claim_timeout" in _ENGINE_SOURCE, (
            "engine.py must contain 'pipeline.claim_timeout' — "
            "currently uses forwarding property config.claim_timeout"
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
            "engine.py must contain 'pipeline.statuses' — "
            "currently uses top-level forwarding config.statuses"
        )

    def test_engine_source_contains_pipeline_priorities(self) -> None:
        """engine.py must access priorities via config.pipeline.priorities after migration."""
        assert "pipeline.priorities" in _ENGINE_SOURCE, (
            "engine.py must contain 'pipeline.priorities' — "
            "currently uses top-level forwarding config.priorities"
        )

    # -- agents group --------------------------------------------------------

    def test_engine_source_contains_agents_agent_map(self) -> None:
        """engine.py must access agent_map via config.agents.agent_map."""
        assert "agents.agent_map" in _ENGINE_SOURCE, (
            "engine.py must contain 'agents.agent_map' — "
            "currently uses forwarding property config.agent_map"
        )

    def test_engine_source_contains_agents_agent_types(self) -> None:
        """engine.py must access agent_types via config.agents.agent_types."""
        assert "agents.agent_types" in _ENGINE_SOURCE, (
            "engine.py must contain 'agents.agent_types' — "
            "currently uses forwarding property config.agent_types"
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
    """AC2 — PipelineConfig must expose statuses/priorities for engine sub-model access.

    The engine migration (AC1) requires config.pipeline.statuses and
    config.pipeline.priorities to be valid attributes. PipelineConfig must grow
    these fields and the engine must use them.

    ALL tests FAIL in RED phase because PipelineConfig currently lacks statuses/priorities.
    """

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

    def test_engine_board_config_pipeline_statuses_returns_statuses_list(
        self, tmp_path: Path
    ) -> None:
        """board_config().pipeline.statuses must return the board statuses list."""
        kanban_dir = _make_board(tmp_path)
        engine = KanbanEngine(kanban_dir)
        cfg = engine.board_config()
        # Will raise AttributeError until PipelineConfig gains 'statuses' field.
        assert cfg.pipeline.statuses == ["research", "backlog", "todo", "done"], (  # type: ignore[attr-defined]
            f"board_config().pipeline.statuses must equal statuses list; got {cfg.pipeline!r}"
        )

    def test_engine_board_config_pipeline_priorities_returns_priorities_list(
        self, tmp_path: Path
    ) -> None:
        """board_config().pipeline.priorities must return the board priorities list."""
        kanban_dir = _make_board(tmp_path)
        engine = KanbanEngine(kanban_dir)
        cfg = engine.board_config()
        # Will raise AttributeError until PipelineConfig gains 'priorities' field.
        assert cfg.pipeline.priorities == ["someday", "important", "critical"], (  # type: ignore[attr-defined]
            f"board_config().pipeline.priorities must equal priorities list; got {cfg.pipeline!r}"
        )


# ---------------------------------------------------------------------------
# AC4 — Tests confirm no engine code path relies on forwarding properties
# ---------------------------------------------------------------------------


class TestFromAC_NoForwardingProperties:
    """AC4 — engine.py must contain NO forwarding property calls after migration.

    Each test asserts that the banned pattern is absent from engine source.
    ALL tests FAIL in RED phase because engine.py currently uses all of these
    forwarding properties extensively.

    Note: these tests scan the full module source including docstrings. If the
    builder uses patterns only in docstrings/comments, the test will still fail;
    the builder must update all occurrences.
    """

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
