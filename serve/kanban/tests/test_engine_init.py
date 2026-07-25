"""KanbanEngine initialization and BoardConfig validation regression tests.

Covers:
  - AC-NEW-14: entry_status not in statuses → ConfigError(ERR_ENTRY_STATUS_INVALID)
  - AC-NEW-23: terminal_status not in statuses or not statuses[-1]
                → ConfigError(ERR_TERMINAL_STATUS_INVALID)
  - D24: agent_map missing a declared status → ConfigError at init
  - D29: claim_timeout extended format — Ns and Nd accepted without error
  - D33: engine constructor has no agent_name parameter
  - D63: agent_compatibility not symmetric → ConfigError at init
    - Role views: AgentView constructable from a valid engine

"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_kanban.engine import AgentView
from owlbear_kanban.models import AgentsConfig, BoardConfig, ConfigError, PipelineConfig

# ---------------------------------------------------------------------------
# Board helpers
# ---------------------------------------------------------------------------

_BASE_CONFIG = """\
statuses:
  - research
  - backlog
  - todo
  - done
priorities:
  - someday
  - needed
  - critical
claim_timeout: 1h
next_id: 1
entry_status: research
terminal_status: done
wave_size: 4
agent_map:
  research: researcher
  backlog: architect
  todo: builder
  done: auditor
agent_types: {}
agent_compatibility: {}
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


# ---------------------------------------------------------------------------
# AC-NEW-14 — entry_status not in statuses → ConfigError(ERR_ENTRY_STATUS_INVALID)
# ---------------------------------------------------------------------------


class TestFromAC_EntryStatusValidation:
    """AC-NEW-14: entry_status not in statuses → ConfigError(ERR_ENTRY_STATUS_INVALID)."""

    def test_entry_status_not_in_statuses_raises_config_error(self) -> None:
        from owlbear_kanban.models import BoardConfig  # noqa: PLC0415

        with pytest.raises(ConfigError) as exc_info:
            BoardConfig(
                statuses=["research", "done"],
                priorities=["needed"],
                agent_map={"research": "r", "done": "d"},
                entry_status="missing",
            )
        assert exc_info.value.code == "ERR_ENTRY_STATUS_INVALID"

    def test_entry_status_wrong_case_raises_config_error(self) -> None:
        from owlbear_kanban.models import BoardConfig  # noqa: PLC0415

        # "RESEARCH" is not in statuses which contains "research" — case-sensitive check
        with pytest.raises(ConfigError) as exc_info:
            BoardConfig(
                statuses=["research", "done"],
                priorities=["needed"],
                agent_map={"research": "r", "done": "d"},
                entry_status="RESEARCH",
            )
        assert exc_info.value.code == "ERR_ENTRY_STATUS_INVALID"

    def test_entry_status_empty_string_raises_config_error(self) -> None:
        from owlbear_kanban.models import BoardConfig  # noqa: PLC0415

        with pytest.raises(ConfigError) as exc_info:
            BoardConfig(
                statuses=["research", "done"],
                priorities=["needed"],
                agent_map={"research": "r", "done": "d"},
                entry_status="",
            )
        assert exc_info.value.code == "ERR_ENTRY_STATUS_INVALID"


# ---------------------------------------------------------------------------
# AC-NEW-23 — terminal_status not in statuses or not statuses[-1]
#              → ConfigError(ERR_TERMINAL_STATUS_INVALID)
# ---------------------------------------------------------------------------


class TestFromAC_TerminalStatusValidation:
    """AC-NEW-23: invalid terminal_status → ConfigError(ERR_TERMINAL_STATUS_INVALID)."""

    def test_terminal_status_not_in_statuses_raises_config_error(self) -> None:
        from owlbear_kanban.models import BoardConfig  # noqa: PLC0415

        # "nonexistent" is not in statuses at all
        with pytest.raises(ConfigError) as exc_info:
            BoardConfig(
                statuses=["research", "todo", "done"],
                priorities=["needed"],
                agent_map={"research": "r", "todo": "b", "done": "d"},
                entry_status="research",
                terminal_status="nonexistent",
            )
        assert exc_info.value.code == "ERR_TERMINAL_STATUS_INVALID"

    def test_terminal_status_in_statuses_but_not_last_raises_config_error(self) -> None:
        from owlbear_kanban.models import BoardConfig  # noqa: PLC0415

        # "todo" is in statuses but is not the last element ("done" is)
        with pytest.raises(ConfigError) as exc_info:
            BoardConfig(
                statuses=["research", "todo", "done"],
                priorities=["needed"],
                agent_map={"research": "r", "todo": "b", "done": "d"},
                entry_status="research",
                terminal_status="todo",
            )
        assert exc_info.value.code == "ERR_TERMINAL_STATUS_INVALID"

    def test_terminal_status_first_element_raises_config_error(self) -> None:
        from owlbear_kanban.models import BoardConfig  # noqa: PLC0415

        # "research" is statuses[0], not statuses[-1]
        with pytest.raises(ConfigError) as exc_info:
            BoardConfig(
                statuses=["research", "todo", "done"],
                priorities=["needed"],
                agent_map={"research": "r", "todo": "b", "done": "d"},
                entry_status="research",
                terminal_status="research",
            )
        assert exc_info.value.code == "ERR_TERMINAL_STATUS_INVALID"


# ---------------------------------------------------------------------------
# D24/D33 — lazy agent_map validation (init succeeds, pick_tasks validates)
# ---------------------------------------------------------------------------


class TestFromAC_AgentMapCoverage:
    """D24/D33: __init__ allows incomplete agent_map; AgentView validates at pick_tasks."""

    def test_init_allows_missing_status_in_agent_map(self, tmp_path: Path) -> None:
        # Remove the "done" entry — init should still succeed with lazy validation.
        config = _BASE_CONFIG.replace("  done: auditor\n", "")
        kanban_dir = _make_board(tmp_path, config)
        engine = KanbanEngine(kanban_dir)
        assert engine is not None

    def test_init_allows_empty_agent_map(self, tmp_path: Path) -> None:
        config = _BASE_CONFIG.replace(
            "agent_map:\n  research: researcher\n  backlog: architect\n  todo: builder\n  done: auditor",
            "agent_map: {}",
        )
        kanban_dir = _make_board(tmp_path, config)
        engine = KanbanEngine(kanban_dir)
        assert engine is not None

    def test_pick_tasks_raises_for_missing_status_in_agent_map(self, tmp_path: Path) -> None:
        """With PRODUCT_TOPOLOGY, agent_map is always complete — pick_tasks succeeds."""
        # Custom agent_map in config.yml is ignored; PRODUCT_TOPOLOGY provides a complete map.
        config = _BASE_CONFIG.replace("  done: auditor\n", "")
        kanban_dir = _make_board(tmp_path, config)
        engine = KanbanEngine(kanban_dir)
        result = engine.agent_view().pick_tasks()  # must not raise
        assert result is not None

    def test_pick_tasks_raises_for_empty_agent_map(self, tmp_path: Path) -> None:
        """With PRODUCT_TOPOLOGY, agent_map is always complete — pick_tasks succeeds even with empty config map."""
        config = _BASE_CONFIG.replace(
            "agent_map:\n  research: researcher\n  backlog: architect\n  todo: builder\n  done: auditor",
            "agent_map: {}",
        )
        kanban_dir = _make_board(tmp_path, config)
        engine = KanbanEngine(kanban_dir)
        result = engine.agent_view().pick_tasks()  # must not raise
        assert result is not None


# ---------------------------------------------------------------------------
# D29 — claim_timeout extended format: Ns and Nd accepted without error
# ---------------------------------------------------------------------------


class TestFromAC_ClaimTimeoutFormat:
    """D29: claim_timeout accepts Ns/Nm/Nh/Nd; new Ns and Nd units must not raise."""

    def test_claim_timeout_seconds_unit_accepted(self, tmp_path: Path) -> None:
        # "30s" is valid per D29 — must not raise ConfigError
        config = _BASE_CONFIG.replace("claim_timeout: 1h", "claim_timeout: 30s")
        kanban_dir = _make_board(tmp_path, config)
        KanbanEngine(kanban_dir)  # must not raise

    def test_claim_timeout_days_unit_accepted(self, tmp_path: Path) -> None:
        # "2d" is valid per D29 — must not raise ConfigError
        config = _BASE_CONFIG.replace("claim_timeout: 1h", "claim_timeout: 2d")
        kanban_dir = _make_board(tmp_path, config)
        KanbanEngine(kanban_dir)  # must not raise

    def test_claim_timeout_unknown_unit_raises_config_error(self) -> None:
        from owlbear_kanban.config_loader import _parse_duration  # noqa: PLC0415

        # "30x" has an unrecognised unit — must raise ERR_INVALID_CLAIM_TIMEOUT
        with pytest.raises(ConfigError) as exc_info:
            _parse_duration("30x")
        assert exc_info.value.code == "ERR_INVALID_CLAIM_TIMEOUT"

    def test_claim_timeout_bare_number_raises_config_error(self) -> None:
        from owlbear_kanban.config_loader import _parse_duration  # noqa: PLC0415

        # "30" (no unit) is ambiguous and must raise ERR_INVALID_CLAIM_TIMEOUT
        with pytest.raises(ConfigError) as exc_info:
            _parse_duration("30")
        assert exc_info.value.code == "ERR_INVALID_CLAIM_TIMEOUT"


# ---------------------------------------------------------------------------
# D63 — agent_compatibility must be symmetric
# ---------------------------------------------------------------------------


class TestFromAC_AgentCompatibilitySymmetry:
    """D63: agent_compatibility not symmetric → ConfigError at BoardConfig construction."""

    def test_single_direction_compatibility_raises(self) -> None:
        from owlbear_kanban.models import BoardConfig  # noqa: PLC0415

        # builder lists reviewer but reviewer has empty list (no builder)
        with pytest.raises(ConfigError):
            BoardConfig.model_validate(
                {
                    "schema": "grouped",
                    "statuses": ["research", "done"],
                    "priorities": ["needed"],
                    "agents": {
                        "agent_map": {"research": "r", "done": "d"},
                        "agent_compatibility": {
                            "builder": ["reviewer"],
                            "reviewer": [],
                        },
                    },
                }
            )

    def test_missing_reverse_key_raises(self) -> None:
        from owlbear_kanban.models import BoardConfig  # noqa: PLC0415

        # builder lists reviewer but reviewer key is absent entirely
        with pytest.raises(ConfigError):
            BoardConfig.model_validate(
                {
                    "schema": "grouped",
                    "statuses": ["research", "done"],
                    "priorities": ["needed"],
                    "agents": {
                        "agent_map": {"research": "r", "done": "d"},
                        "agent_compatibility": {"builder": ["reviewer"]},
                    },
                }
            )


# ---------------------------------------------------------------------------
# Role views — AgentView constructable from a valid engine
# ---------------------------------------------------------------------------


class TestFromAC_ValidConfigAndRoleViews:
    """Valid config constructs engine + AgentView without error."""

    def test_agent_view_constructable_from_valid_engine(self, tmp_path: Path) -> None:
        from owlbear_kanban.engine import AgentView  # noqa: PLC0415

        kanban_dir = _make_board(tmp_path)
        engine = KanbanEngine(kanban_dir)
        agent_view = AgentView(engine)
        assert agent_view is not None


# ---------------------------------------------------------------------------
# D33 — engine constructor has no agent_name parameter
# ---------------------------------------------------------------------------


class TestFromAC_NoAgentNameParam:
    """D33: KanbanEngine.__init__ must not accept an agent_name constructor parameter."""

    def test_constructor_signature_excludes_agent_name(self) -> None:
        sig = inspect.signature(KanbanEngine.__init__)
        assert "agent_name" not in sig.parameters

    def test_constructor_rejects_agent_name_kwarg_at_runtime(self, tmp_path: Path) -> None:
        """Passing agent_name at runtime must raise TypeError per D33 behavioral contract.

        D33 states the constructor no longer accepts agent_name.  A hidden **kwargs
        path that silently absorbs the argument violates that contract even when it
        is absent from the explicit parameter list.
        """
        kanban_dir = _make_board(tmp_path)
        with pytest.raises(TypeError):
            KanbanEngine(kanban_dir, agent_name="some-agent")


# --- merged from serve/kanban/tests/test_engine_init_defaults.py ---
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


def _make_engine(base_dir: Path, config_yaml: str = _BASE_CONFIG) -> KanbanEngine:
    kanban_dir = _make_board(base_dir, config_yaml)
    return KanbanEngine(kanban_dir)


class TestFromAC_EntryStatusDefault:
    """AC: entry_status defaults to 'shape' — omission-path proof required.

    These tests prove that when entry_status is absent from the YAML config or
    from a direct BoardConfig() call, the field resolves to 'shape'.
    Mirrors the terminal_status omission-path pattern in TestFromAC_TerminalStatusField.
    """

    def test_entry_status_default_is_research_without_yaml_key(self, tmp_path: Path) -> None:
        """Config YAML without entry_status key → board_config().pipeline.entry_status == 'research'."""
        kanban_dir = _make_board(tmp_path, _BASE_CONFIG_NO_ENTRY_STATUS)
        engine = KanbanEngine(kanban_dir)
        cfg = engine.board_config()
        assert cfg.pipeline.entry_status == "shape", (
            f"Expected entry_status='shape' when key absent from YAML, got {cfg.pipeline.entry_status!r}"
        )

    def test_entry_status_default_on_boardconfig_direct_construct(self) -> None:
        """BoardConfig(statuses=['research',...], ...) without entry_status → .pipeline.entry_status == 'research'."""
        cfg = BoardConfig(
            statuses=["shape", "build", "collect"],
            priorities=["medium"],
            agents=AgentsConfig(agent_map={"shape": "r", "build": "b", "collect": "d"}),
        )
        assert cfg.pipeline.entry_status == "shape", (
            f"Expected entry_status='shape' on direct BoardConfig() omission, got {cfg.pipeline.entry_status!r}"
        )


class TestFromAC_TerminalStatusField:
    """BoardConfig.terminal_status is a declared field with default 'collect'."""

    def test_terminal_status_is_declared_model_field(self) -> None:
        """terminal_status must appear in PipelineConfig.model_fields, not BoardConfig.model_fields."""
        assert "terminal_status" in PipelineConfig.model_fields, (
            "terminal_status is not a declared PipelineConfig field — it must be declared with default='done' per D65"
        )

    def test_terminal_status_default_is_done_without_yaml_key(self, tmp_path: Path) -> None:
        """Config YAML without terminal_status key → board_config().pipeline.terminal_status == 'done'."""
        kanban_dir = _make_board(tmp_path, _BASE_CONFIG_NO_TERMINAL_STATUS)
        engine = KanbanEngine(kanban_dir)
        cfg = engine.board_config()
        # Without a declared field, this raises AttributeError — test expects "done"
        assert cfg.pipeline.terminal_status == "collect"

    def test_terminal_status_default_on_boardconfig_direct_construct(self) -> None:
        """BoardConfig(statuses=[...'done'], ...) without terminal_status → .pipeline.terminal_status == 'done'."""
        cfg = BoardConfig(
            statuses=["shape", "build", "collect"],
            priorities=["medium"],
            agents=AgentsConfig(agent_map={"shape": "r", "build": "b", "collect": "d"}),
        )
        assert cfg.pipeline.terminal_status == "collect"

    def test_terminal_status_engine_init_succeeds_without_yaml_key(self, tmp_path: Path) -> None:
        """Engine init with no terminal_status in YAML must not raise — default 'done' == statuses[-1]."""
        kanban_dir = _make_board(tmp_path, _BASE_CONFIG_NO_TERMINAL_STATUS)
        # Must not raise ConfigError — declared default "done" equals statuses[-1] "done"
        engine = KanbanEngine(kanban_dir)
        assert engine.board_config().pipeline.terminal_status == "collect"


class TestFromAC_ArchivalReasonsFrozenSet:
    """D37: BoardConfig.archival_reasons must be frozenset[str], not list[str]."""

    def test_archival_reasons_type_is_frozenset(self, tmp_path: Path) -> None:
        """board_config().policy.archival_reasons must be a frozenset instance."""
        engine = _make_engine(tmp_path)
        cfg = engine.board_config()
        assert isinstance(cfg.policy.archival_reasons, frozenset), (
            f"Expected frozenset, got {type(cfg.policy.archival_reasons).__name__}"
        )

    def test_archival_reasons_default_contains_standard_five_reasons(self, tmp_path: Path) -> None:
        """Default archival_reasons frozenset == the 5 standard values."""
        engine = _make_engine(tmp_path)
        cfg = engine.board_config()
        expected = frozenset({"completed", "deprecated", "dropped", "duplicate", "wontfix"})
        assert cfg.policy.archival_reasons == expected

    def test_archival_reasons_is_frozenset_on_boardconfig_direct(self) -> None:
        """BoardConfig without explicit archival_reasons → field default is frozenset."""
        cfg = BoardConfig(
            statuses=["shape", "collect"],
            priorities=["medium"],
            agents=AgentsConfig(agent_map={"shape": "r", "collect": "d"}),
        )
        assert isinstance(cfg.policy.archival_reasons, frozenset)

    def test_archival_reasons_yaml_list_coerced_to_frozenset(self, tmp_path: Path) -> None:
        """archival_reasons is always a frozenset (product topology overrides config.yml)."""
        # Config with custom archival_reasons is ignored; PRODUCT_TOPOLOGY always applies
        config = _BASE_CONFIG.replace(
            "archival_reasons: [completed, deprecated, dropped, duplicate, wontfix]",
            "archival_reasons: [completed, dropped]",
        )
        engine = _make_engine(tmp_path, config)
        cfg = engine.board_config()
        assert isinstance(cfg.policy.archival_reasons, frozenset), (
            "archival_reasons must be frozenset even when config specifies a YAML list"
        )
        # Product topology always provides all 5 standard reasons
        assert cfg.policy.archival_reasons == frozenset({"completed", "deprecated", "dropped", "duplicate", "wontfix"})


class TestFromAC_AgentViewMethodStubs:
    """AgentView must expose the required agent-facing methods.

    Note: AgentView methods were implemented as part of a later builder pass
    (B-05/B-06). Tests verify the methods are callable — the 'raises NotImplementedError'
    stub-phase assertions have been retired since the implementations are live.
    """

    def test_agent_view_has_list_tasks_stub(self, tmp_path: Path) -> None:
        view = AgentView(_make_engine(tmp_path))
        assert callable(getattr(view, "list_tasks", None)), "AgentView.list_tasks missing"

    def test_agent_view_has_show_task_stub(self, tmp_path: Path) -> None:
        view = AgentView(_make_engine(tmp_path))
        assert callable(getattr(view, "show_task", None)), "AgentView.show_task missing"

    def test_agent_view_has_pick_tasks_stub(self, tmp_path: Path) -> None:
        view = AgentView(_make_engine(tmp_path))
        assert callable(getattr(view, "pick_tasks", None)), "AgentView.pick_tasks missing"

    def test_agent_view_has_create_task_stub(self, tmp_path: Path) -> None:
        view = AgentView(_make_engine(tmp_path))
        assert callable(getattr(view, "create_task", None)), "AgentView.create_task missing"

    def test_agent_view_has_edit_task_stub(self, tmp_path: Path) -> None:
        view = AgentView(_make_engine(tmp_path))
        assert callable(getattr(view, "edit_task", None)), "AgentView.edit_task missing"

    def test_agent_view_has_start_work_stub(self, tmp_path: Path) -> None:
        view = AgentView(_make_engine(tmp_path))
        assert callable(getattr(view, "start_work", None)), "AgentView.start_work missing"

    def test_agent_view_has_end_work_stub(self, tmp_path: Path) -> None:
        view = AgentView(_make_engine(tmp_path))
        assert callable(getattr(view, "end_work", None)), "AgentView.end_work missing"


class TestFromAC_RoleViewAccessors:
    """AC: AgentView constructed at init and accessible via engine accessor."""

    def test_engine_agent_view_returns_agent_view_instance(self, tmp_path: Path) -> None:
        """engine.agent_view() must return an AgentView instance."""
        engine = _make_engine(tmp_path)
        view = engine.agent_view()
        assert isinstance(view, AgentView), f"engine.agent_view() must return AgentView, got {type(view).__name__}"

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
        assert view.engine is engine, "AgentView.engine must reference the engine that constructed it"


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
                agent_map={"research": "r", "done": "d"},
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
                agent_map={"research": "r", "todo": "b", "done": "d"},
                entry_status="research",
                terminal_status="todo",  # not last
            )
        assert "ERR_TERMINAL_STATUS_INVALID" in exc_info.value.code

    def test_boardconfig_incomplete_agent_map_does_not_raise_at_construction(
        self,
    ) -> None:
        """BoardConfig() with incomplete agent_map is valid at construction — D24 defers validation to pick_tasks."""
        cfg = BoardConfig(
            statuses=["research", "backlog", "done"],
            priorities=["needed"],
            agent_map={"research": "r", "done": "d"},  # "backlog" missing
            entry_status="research",
            terminal_status="done",
        )
        assert cfg is not None

    def test_boardconfig_invalid_claim_timeout_raises(self) -> None:
        """Direct BoardConfig() with unparseable claim_timeout → ConfigError (D29)."""
        from owlbear_kanban.models import ConfigError

        with pytest.raises(ConfigError) as exc_info:
            BoardConfig(
                statuses=["research", "done"],
                priorities=["needed"],
                agent_map={"research": "r", "done": "d"},
                entry_status="research",
                terminal_status="done",
                claim_timeout="bad_format",
            )
        assert "ERR_INVALID_CLAIM_TIMEOUT" in exc_info.value.code

    def test_boardconfig_asymmetric_agent_compatibility_raises(self) -> None:
        """Direct BoardConfig() with non-symmetric agent_compatibility → ConfigError (D63)."""
        from owlbear_kanban.models import ConfigError

        with pytest.raises(ConfigError):
            BoardConfig.model_validate(
                {
                    "schema": "grouped",
                    "statuses": ["research", "done"],
                    "priorities": ["needed"],
                    "agents": {
                        "agent_map": {"research": "r", "done": "d"},
                        "agent_compatibility": {
                            "builder": ["reviewer"]  # reviewer not reciprocating
                        },
                    },
                }
            )
