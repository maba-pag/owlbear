"""RED-phase tests for KanbanEngine init + BoardConfig validation (task #1068).

Covers:
  - D65: BoardConfig.terminal_status must be a declared field with default "done"
  - D37: BoardConfig.archival_reasons must be a frozenset (not list)
        - AgentView method surface: list_tasks, show_task, pick_tasks, create_task,
                edit_task, start_work, end_work — methods are implemented on the agent facade
    - CockpitView method surface: list_tasks, show_task, edit_task, move_task,
                release_task, board_config — methods are implemented on the cockpit facade

These RED tests established initial contracts for init/config behavior and
role-view method surfaces in owlbear_kanban.engine / owlbear_kanban.models.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_kanban.engine import AgentView
from owlbear_kanban.models import AgentsConfig, BoardConfig

# ---------------------------------------------------------------------------
# Board helpers
# ---------------------------------------------------------------------------

_BASE_CONFIG = """\
schema: grouped
statuses:
  - research
  - backlog
  - todo
  - done
priorities:
  - someday
  - needed
  - critical
next_id: 1
paths:
    tasks_dir: tasks
    archive_dir: archive
pipeline:
    entry_status: research
    terminal_status: done
    wave_size: 4
    claim_timeout: 1h
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
    archival_reasons: [completed, deprecated, dropped, duplicate, wontfix]
    status_predicates: {}
"""

# Same config but without the entry_status key — should default to "research"
_BASE_CONFIG_NO_ENTRY_STATUS = """\
schema: grouped
statuses:
  - research
  - backlog
  - todo
  - done
priorities:
  - someday
  - needed
  - critical
next_id: 1
paths:
    tasks_dir: tasks
    archive_dir: archive
pipeline:
    terminal_status: done
    wave_size: 4
    claim_timeout: 1h
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
    archival_reasons: [completed, deprecated, dropped, duplicate, wontfix]
    status_predicates: {}
"""

# Same config but without the terminal_status key — should default to "done"
_BASE_CONFIG_NO_TERMINAL_STATUS = """\
schema: grouped
statuses:
  - research
  - backlog
  - todo
  - done
priorities:
  - someday
  - needed
  - critical
next_id: 1
paths:
    tasks_dir: tasks
    archive_dir: archive
pipeline:
    entry_status: research
    wave_size: 4
    claim_timeout: 1h
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
    archival_reasons: [completed, deprecated, dropped, duplicate, wontfix]
    status_predicates: {}
"""


def _make_board(base_dir: Path, config_yaml: str = _BASE_CONFIG) -> Path:
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(config_yaml, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


def _make_engine(base_dir: Path, config_yaml: str = _BASE_CONFIG) -> KanbanEngine:
    kanban_dir = _make_board(base_dir, config_yaml)
    return KanbanEngine(kanban_dir)


# ---------------------------------------------------------------------------
# AC line 3 — entry_status defaults to "research" (omission-path proof)
# ---------------------------------------------------------------------------


class TestFromAC_EntryStatusDefault:
    """AC: entry_status defaults to 'research' — omission-path proof required.

    These tests prove that when entry_status is absent from the YAML config or
    from a direct BoardConfig() call, the field resolves to 'research'.
    Mirrors the terminal_status omission-path pattern in TestFromAC_TerminalStatusField.
    """

    def test_entry_status_default_is_research_without_yaml_key(
        self, tmp_path: Path
    ) -> None:
        """Config YAML without entry_status key → board_config().entry_status == 'research'."""
        kanban_dir = _make_board(tmp_path, _BASE_CONFIG_NO_ENTRY_STATUS)
        engine = KanbanEngine(kanban_dir)
        cfg = engine.board_config()
        assert cfg.entry_status == "research", (
            f"Expected entry_status='research' when key absent from YAML, got {cfg.entry_status!r}"
        )

    def test_entry_status_default_on_boardconfig_direct_construct(self) -> None:
        """BoardConfig(statuses=['research',...], ...) without entry_status → .entry_status == 'research'."""
        cfg = BoardConfig(
            statuses=["research", "backlog", "done"],
            priorities=["needed"],
            agents=AgentsConfig(
                agent_map={"research": "r", "backlog": "b", "done": "d"}
            ),
        )
        assert cfg.entry_status == "research", (
            f"Expected entry_status='research' on direct BoardConfig() omission, got {cfg.entry_status!r}"
        )


# ---------------------------------------------------------------------------
# D65 — terminal_status declared as a BoardConfig field with default "done"
# ---------------------------------------------------------------------------


class TestFromAC_TerminalStatusField:
    """D65: BoardConfig.terminal_status must be a declared field (not model_extra) with default 'done'."""

    def test_terminal_status_is_declared_model_field(self) -> None:
        """terminal_status must appear in BoardConfig.model_fields, not model_extra."""
        assert "terminal_status" in BoardConfig.model_fields, (
            "terminal_status is not a declared BoardConfig field — it must be declared "
            "with default='done' per D65"
        )

    def test_terminal_status_default_is_done_without_yaml_key(
        self, tmp_path: Path
    ) -> None:
        """Config YAML without terminal_status key → board_config().terminal_status == 'done'."""
        kanban_dir = _make_board(tmp_path, _BASE_CONFIG_NO_TERMINAL_STATUS)
        engine = KanbanEngine(kanban_dir)
        cfg = engine.board_config()
        # Without a declared field, this raises AttributeError — test expects "done"
        assert cfg.terminal_status == "done"

    def test_terminal_status_default_on_boardconfig_direct_construct(self) -> None:
        """BoardConfig(statuses=[...'done'], ...) without terminal_status → .terminal_status == 'done'."""
        cfg = BoardConfig(
            statuses=["research", "backlog", "done"],
            priorities=["needed"],
            agents=AgentsConfig(
                agent_map={"research": "r", "backlog": "b", "done": "d"}
            ),
        )
        assert cfg.terminal_status == "done"

    def test_terminal_status_engine_init_succeeds_without_yaml_key(
        self, tmp_path: Path
    ) -> None:
        """Engine init with no terminal_status in YAML must not raise — default 'done' == statuses[-1]."""
        kanban_dir = _make_board(tmp_path, _BASE_CONFIG_NO_TERMINAL_STATUS)
        # Must not raise ConfigError — declared default "done" equals statuses[-1] "done"
        engine = KanbanEngine(kanban_dir)
        assert engine.board_config().terminal_status == "done"


# ---------------------------------------------------------------------------
# D37 — archival_reasons must be a frozenset (frozen literal)
# ---------------------------------------------------------------------------


class TestFromAC_ArchivalReasonsFrozenSet:
    """D37: BoardConfig.archival_reasons must be frozenset[str], not list[str]."""

    def test_archival_reasons_type_is_frozenset(self, tmp_path: Path) -> None:
        """board_config().archival_reasons must be a frozenset instance."""
        engine = _make_engine(tmp_path)
        cfg = engine.board_config()
        assert isinstance(cfg.archival_reasons, frozenset), (
            f"Expected frozenset, got {type(cfg.archival_reasons).__name__}"
        )

    def test_archival_reasons_default_contains_standard_five_reasons(
        self, tmp_path: Path
    ) -> None:
        """Default archival_reasons frozenset == the 5 standard values."""
        engine = _make_engine(tmp_path)
        cfg = engine.board_config()
        expected = frozenset(
            {"completed", "deprecated", "dropped", "duplicate", "wontfix"}
        )
        assert cfg.archival_reasons == expected

    def test_archival_reasons_is_frozenset_on_boardconfig_direct(self) -> None:
        """BoardConfig without explicit archival_reasons → field default is frozenset."""
        cfg = BoardConfig(
            statuses=["research", "done"],
            priorities=["needed"],
            agents=AgentsConfig(agent_map={"research": "r", "done": "d"}),
        )
        assert isinstance(cfg.archival_reasons, frozenset)

    def test_archival_reasons_yaml_list_coerced_to_frozenset(
        self, tmp_path: Path
    ) -> None:
        """archival_reasons from YAML list is converted to frozenset at load time."""
        config = _BASE_CONFIG.replace(
            "archival_reasons: [completed, deprecated, dropped, duplicate, wontfix]",
            "archival_reasons: [completed, dropped]",
        )
        engine = _make_engine(tmp_path, config)
        cfg = engine.board_config()
        assert isinstance(cfg.archival_reasons, frozenset)
        assert cfg.archival_reasons == frozenset({"completed", "dropped"})


# ---------------------------------------------------------------------------
# AgentView method stubs (now real implementations from B-05/B-06)
# ---------------------------------------------------------------------------


class TestFromAC_AgentViewMethodStubs:
    """AgentView must expose the required agent-facing methods.

    Note: AgentView methods were implemented as part of a later builder pass
    (B-05/B-06). Tests verify the methods are callable — the 'raises NotImplementedError'
    stub-phase assertions have been retired since the implementations are live.
    """

    def test_agent_view_has_list_tasks_stub(self, tmp_path: Path) -> None:
        view = AgentView(_make_engine(tmp_path))
        assert callable(getattr(view, "list_tasks", None)), (
            "AgentView.list_tasks missing"
        )

    def test_agent_view_has_show_task_stub(self, tmp_path: Path) -> None:
        view = AgentView(_make_engine(tmp_path))
        assert callable(getattr(view, "show_task", None)), "AgentView.show_task missing"

    def test_agent_view_has_pick_tasks_stub(self, tmp_path: Path) -> None:
        view = AgentView(_make_engine(tmp_path))
        assert callable(getattr(view, "pick_tasks", None)), (
            "AgentView.pick_tasks missing"
        )

    def test_agent_view_has_create_task_stub(self, tmp_path: Path) -> None:
        view = AgentView(_make_engine(tmp_path))
        assert callable(getattr(view, "create_task", None)), (
            "AgentView.create_task missing"
        )

    def test_agent_view_has_edit_task_stub(self, tmp_path: Path) -> None:
        view = AgentView(_make_engine(tmp_path))
        assert callable(getattr(view, "edit_task", None)), "AgentView.edit_task missing"

    def test_agent_view_has_start_work_stub(self, tmp_path: Path) -> None:
        view = AgentView(_make_engine(tmp_path))
        assert callable(getattr(view, "start_work", None)), (
            "AgentView.start_work missing"
        )

    def test_agent_view_has_end_work_stub(self, tmp_path: Path) -> None:
        view = AgentView(_make_engine(tmp_path))
        assert callable(getattr(view, "end_work", None)), "AgentView.end_work missing"


# ---------------------------------------------------------------------------
# Role-view accessor on KanbanEngine (engine.agent_view)
# ---------------------------------------------------------------------------


class TestFromAC_RoleViewAccessors:
    """AC: AgentView constructed at init and accessible via engine accessor."""

    def test_engine_agent_view_returns_agent_view_instance(
        self, tmp_path: Path
    ) -> None:
        """engine.agent_view() must return an AgentView instance."""
        engine = _make_engine(tmp_path)
        view = engine.agent_view()
        assert isinstance(view, AgentView), (
            f"engine.agent_view() must return AgentView, got {type(view).__name__}"
        )

    def test_engine_agent_view_same_instance_across_calls(self, tmp_path: Path) -> None:
        """engine.agent_view() must return the same cached instance on repeated calls."""
        engine = _make_engine(tmp_path)
        assert engine.agent_view() is engine.agent_view(), (
            "engine.agent_view() must return the same cached AgentView instance"
        )

    def test_engine_agent_view_has_engine_reference(self, tmp_path: Path) -> None:
        """AgentView returned by engine.agent_view() must hold a reference to the engine."""
        engine = _make_engine(tmp_path)
        view = engine.agent_view()
        assert view.engine is engine, (
            "AgentView.engine must reference the engine that constructed it"
        )


# ---------------------------------------------------------------------------
# BoardConfig direct model validation (model-level semantic invariants — D29, D24, D63)
# ---------------------------------------------------------------------------


class TestFromAC_BoardConfigDirectValidation:
    """AC: BoardConfig is Pydantic model with all fields validated at init.

    Tests that semantic invariants are enforced when constructing BoardConfig
    directly (not via engine or YAML load), verifying the model_validator path.
    """

    def test_boardconfig_entry_status_not_in_statuses_raises(self) -> None:
        """Direct BoardConfig() with entry_status not in statuses → ConfigError."""
        from owlbear_kanban.models import ConfigError

        with pytest.raises(ConfigError) as exc_info:
            BoardConfig(
                statuses=["research", "done"],
                priorities=["needed"],
                agents=AgentsConfig(agent_map={"research": "r", "done": "d"}),
                entry_status="missing",
            )
        assert "ERR_ENTRY_STATUS_INVALID" in exc_info.value.code

    def test_boardconfig_terminal_status_not_last_raises(self) -> None:
        """Direct BoardConfig() with terminal_status != statuses[-1] → ConfigError."""
        from owlbear_kanban.models import ConfigError

        with pytest.raises(ConfigError) as exc_info:
            BoardConfig(
                statuses=["research", "todo", "done"],
                priorities=["needed"],
                agents=AgentsConfig(
                    agent_map={"research": "r", "todo": "b", "done": "d"}
                ),
                terminal_status="todo",  # not last
            )
        assert "ERR_TERMINAL_STATUS_INVALID" in exc_info.value.code

    def test_boardconfig_incomplete_agent_map_raises(self) -> None:
        """Direct BoardConfig() with agent_map missing a status → ConfigError (D24)."""
        from owlbear_kanban.models import ConfigError

        with pytest.raises(ConfigError):
            BoardConfig(
                statuses=["research", "backlog", "done"],
                priorities=["needed"],
                agents=AgentsConfig(
                    agent_map={"research": "r", "done": "d"}
                ),  # "backlog" missing
            )

    def test_boardconfig_invalid_claim_timeout_raises(self) -> None:
        """Direct BoardConfig() with unparseable claim_timeout → ConfigError (D29)."""
        from owlbear_kanban.models import ConfigError

        with pytest.raises(ConfigError) as exc_info:
            BoardConfig(
                statuses=["research", "done"],
                priorities=["needed"],
                agents=AgentsConfig(agent_map={"research": "r", "done": "d"}),
                claim_timeout="bad_format",
            )
        assert "ERR_INVALID_CLAIM_TIMEOUT" in exc_info.value.code

    def test_boardconfig_asymmetric_agent_compatibility_raises(self) -> None:
        """Direct BoardConfig() with non-symmetric agent_compatibility → ConfigError (D63)."""
        from owlbear_kanban.models import ConfigError

        with pytest.raises(ConfigError):
            BoardConfig(
                statuses=["research", "done"],
                priorities=["needed"],
                agents=AgentsConfig(
                    agent_map={"research": "r", "done": "d"},
                    agent_compatibility={
                        "builder": ["reviewer"]
                    },  # reviewer not reciprocating
                ),
            )
