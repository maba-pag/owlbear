"""RED-phase failing tests for product-topology constant and engine refactor (#1439).

AC coverage:
  AC1 (td:1): importable PRODUCT_TOPOLOGY constant in owlbear_kanban.topology with
              17 canonical categories (statuses x7, priorities x5, entry_status,
              terminal_status, default_priority, claim_timeout, wave_size, agent_map,
              non_impl_tags, archival_reasons, activity_log, tasks_dir, archive_dir,
              decisions_dir, status_predicates, agent_types, agent_compatibility)
  AC2 (td:2): KanbanEngine initialises from board dir with no config.yml;
              board_config() matches product constant; next_id defaults to 1
  AC3 (td:2): config.yml topology overrides ignored by KanbanEngine.board_config()
              and AgentView methods across all 17 topology categories
  AC4 (td:2): load_config absent → no FileNotFoundError; save_config writes only
              next_id; board_config attribute paths preserved; dispatch._NON_IMPL_TAGS
              references product constant; frontmatter validates against product topology
"""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

import pytest
import yaml

from owlbear_kanban import KanbanEngine
from owlbear_kanban.config_loader import load_config
from owlbear_kanban.corruption import (
    ERR_CORRUPT_INVALID_STATUS,
    CorruptionError,
)
from owlbear_kanban.models import BoardConfig
from owlbear_kanban.storage import save_config

# ---------------------------------------------------------------------------
# Expected product-topology values  (derived from config.yml + dispatch.py)
# ---------------------------------------------------------------------------

_EXPECTED_STATUSES = [
    "research",
    "backlog",
    "todo",
    "in-progress",
    "review",
    "docs",
    "done",
]
_EXPECTED_PRIORITIES = [
    "someday",
    "nice-to-have",
    "important",
    "needed",
    "critical",
]
_EXPECTED_ENTRY_STATUS = "research"
_EXPECTED_TERMINAL_STATUS = "done"
_EXPECTED_DEFAULT_PRIORITY = "important"
_EXPECTED_CLAIM_TIMEOUT = "1h"
_EXPECTED_WAVE_SIZE = 4
_EXPECTED_AGENT_MAP = {
    "research": "researcher",
    "backlog": "architect",
    "todo": "test-writer",
    "in-progress": "builder",
    "review": "reviewer",
    "docs": "doc-writer",
    "done": "auditor",
}
_EXPECTED_NON_IMPL_TAGS = frozenset(
    {
        "research",
        "docs",
        "type:config",
        "type:docs",
        "test",
        "type:test",
        "agent",
        "quality",
        "type:user-action",
    }
)
_EXPECTED_ARCHIVAL_REASONS = frozenset({"completed", "deprecated", "dropped", "duplicate", "wontfix"})
_EXPECTED_TASKS_DIR = "tasks"
_EXPECTED_ARCHIVE_DIR = "archive"
_EXPECTED_DECISIONS_DIR = "decisions"


# ---------------------------------------------------------------------------
# Board construction helpers
# ---------------------------------------------------------------------------


def _write_base_config(board: Path, **overrides: Any) -> None:
    """Write a complete, valid grouped-schema config.yml with optional field overrides.

    Uses product-topology values as defaults so every generated config is
    immediately valid for engine initialisation.  Pass keyword args to override
    any top-level or nested field.
    """
    data: dict[str, Any] = {
        "schema": "grouped",
        "statuses": list(_EXPECTED_STATUSES),
        "priorities": list(_EXPECTED_PRIORITIES),
        "next_id": 1,
        "activity_log": True,
        "paths": {
            "tasks_dir": _EXPECTED_TASKS_DIR,
            "archive_dir": _EXPECTED_ARCHIVE_DIR,
        },
        "pipeline": {
            "entry_status": _EXPECTED_ENTRY_STATUS,
            "terminal_status": _EXPECTED_TERMINAL_STATUS,
            "wave_size": _EXPECTED_WAVE_SIZE,
            "claim_timeout": _EXPECTED_CLAIM_TIMEOUT,
            "default_priority": _EXPECTED_DEFAULT_PRIORITY,
        },
        "agents": {
            "agent_map": dict(_EXPECTED_AGENT_MAP),
            "agent_types": {},
            "agent_compatibility": {},
        },
        "policy": {
            "non_impl_tags": [],
            "archival_reasons": sorted(_EXPECTED_ARCHIVAL_REASONS),
            "status_predicates": {},
        },
    }
    # Apply overrides with simple dict-merge for nested keys
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(data.get(key), dict):
            data[key] = {**data[key], **value}
        else:
            data[key] = value
    (board / "config.yml").write_text(yaml.dump(data), encoding="utf-8")


def _make_no_config_board(tmp_path: Path) -> Path:
    """Board with tasks/, archive/, decisions/ subdirectories but no config.yml."""
    board = tmp_path / "board"
    board.mkdir()
    (board / "tasks").mkdir()
    (board / "archive").mkdir()
    (board / "decisions").mkdir()
    return board


def _make_board_with_override(tmp_path: Path, **overrides: Any) -> Path:
    """Board with config.yml that overrides specified topology fields."""
    board = tmp_path / "board"
    board.mkdir()
    (board / "tasks").mkdir()
    (board / "archive").mkdir()
    (board / "decisions").mkdir()
    _write_base_config(board, **overrides)
    return board


def _write_task_file(
    tasks_dir: Path,
    *,
    task_id: int,
    status: str,
    priority: str,
    title: str = "Test task",
) -> Path:
    """Write a minimal valid task frontmatter file to tasks_dir."""
    filename = f"{task_id}-test-task.md"
    now = "2026-01-01T00:00:00+00:00"
    content = (
        "---\n"
        f"id: {task_id}\n"
        f"title: {title!r}\n"
        f"status: {status}\n"
        f"priority: {priority}\n"
        f"created: {now}\n"
        f"updated: {now}\n"
        "tags: []\n"
        "depends_on: []\n"
        "blocked: false\n"
        "---\n"
        "Body text.\n"
    )
    path = tasks_dir / filename
    path.write_text(content, encoding="utf-8")
    return path


# ===========================================================================
# AC1: product-topology constant — existence and canonical values
# ===========================================================================


class TestTopologyConstant:
    """AC1: one importable PRODUCT_TOPOLOGY constant with 17 canonical categories."""

    def test_topology_module_is_importable(self) -> None:
        """owlbear_kanban.topology module must exist and import without errors."""
        mod = importlib.import_module("owlbear_kanban.topology")
        assert mod is not None

    def test_product_topology_constant_exists(self) -> None:
        """PRODUCT_TOPOLOGY name must be exported from owlbear_kanban.topology."""
        mod = importlib.import_module("owlbear_kanban.topology")
        assert hasattr(mod, "PRODUCT_TOPOLOGY")

    def test_statuses_has_7_values(self) -> None:
        mod = importlib.import_module("owlbear_kanban.topology")
        assert len(mod.PRODUCT_TOPOLOGY.statuses) == 7

    def test_statuses_match_canonical_list(self) -> None:
        mod = importlib.import_module("owlbear_kanban.topology")
        assert list(mod.PRODUCT_TOPOLOGY.statuses) == _EXPECTED_STATUSES

    def test_priorities_has_5_values(self) -> None:
        mod = importlib.import_module("owlbear_kanban.topology")
        assert len(mod.PRODUCT_TOPOLOGY.priorities) == 5

    def test_priorities_match_canonical_list(self) -> None:
        mod = importlib.import_module("owlbear_kanban.topology")
        assert list(mod.PRODUCT_TOPOLOGY.priorities) == _EXPECTED_PRIORITIES

    def test_entry_status_is_research(self) -> None:
        mod = importlib.import_module("owlbear_kanban.topology")
        assert mod.PRODUCT_TOPOLOGY.entry_status == _EXPECTED_ENTRY_STATUS

    def test_terminal_status_is_done(self) -> None:
        mod = importlib.import_module("owlbear_kanban.topology")
        assert mod.PRODUCT_TOPOLOGY.terminal_status == _EXPECTED_TERMINAL_STATUS

    def test_default_priority_is_important(self) -> None:
        mod = importlib.import_module("owlbear_kanban.topology")
        assert mod.PRODUCT_TOPOLOGY.default_priority == _EXPECTED_DEFAULT_PRIORITY

    def test_claim_timeout_is_1h(self) -> None:
        mod = importlib.import_module("owlbear_kanban.topology")
        assert mod.PRODUCT_TOPOLOGY.claim_timeout == _EXPECTED_CLAIM_TIMEOUT

    def test_wave_size_is_4(self) -> None:
        mod = importlib.import_module("owlbear_kanban.topology")
        assert mod.PRODUCT_TOPOLOGY.wave_size == _EXPECTED_WAVE_SIZE

    def test_agent_map_has_entry_per_status(self) -> None:
        mod = importlib.import_module("owlbear_kanban.topology")
        agent_map = mod.PRODUCT_TOPOLOGY.agent_map
        assert set(agent_map.keys()) == set(_EXPECTED_STATUSES)

    def test_agent_map_matches_canonical(self) -> None:
        mod = importlib.import_module("owlbear_kanban.topology")
        assert dict(mod.PRODUCT_TOPOLOGY.agent_map) == _EXPECTED_AGENT_MAP

    def test_non_impl_tags_matches_dispatch(self) -> None:
        """non_impl_tags must equal the dispatch._NON_IMPL_TAGS set."""
        mod = importlib.import_module("owlbear_kanban.topology")
        assert frozenset(mod.PRODUCT_TOPOLOGY.non_impl_tags) == _EXPECTED_NON_IMPL_TAGS

    def test_archival_reasons_contains_canonical_set(self) -> None:
        mod = importlib.import_module("owlbear_kanban.topology")
        assert frozenset(mod.PRODUCT_TOPOLOGY.archival_reasons) == _EXPECTED_ARCHIVAL_REASONS

    def test_activity_log_is_true(self) -> None:
        mod = importlib.import_module("owlbear_kanban.topology")
        assert mod.PRODUCT_TOPOLOGY.activity_log is True

    def test_tasks_dir_is_tasks(self) -> None:
        mod = importlib.import_module("owlbear_kanban.topology")
        assert mod.PRODUCT_TOPOLOGY.tasks_dir == _EXPECTED_TASKS_DIR

    def test_archive_dir_is_archive(self) -> None:
        mod = importlib.import_module("owlbear_kanban.topology")
        assert mod.PRODUCT_TOPOLOGY.archive_dir == _EXPECTED_ARCHIVE_DIR

    def test_decisions_dir_is_decisions(self) -> None:
        mod = importlib.import_module("owlbear_kanban.topology")
        assert mod.PRODUCT_TOPOLOGY.decisions_dir == _EXPECTED_DECISIONS_DIR

    def test_status_predicates_is_empty(self) -> None:
        mod = importlib.import_module("owlbear_kanban.topology")
        assert dict(mod.PRODUCT_TOPOLOGY.status_predicates) == {}

    def test_agent_types_is_empty(self) -> None:
        mod = importlib.import_module("owlbear_kanban.topology")
        assert dict(mod.PRODUCT_TOPOLOGY.agent_types) == {}

    def test_agent_compatibility_is_empty(self) -> None:
        mod = importlib.import_module("owlbear_kanban.topology")
        assert dict(mod.PRODUCT_TOPOLOGY.agent_compatibility) == {}


# ===========================================================================
# AC2: KanbanEngine initialises without config.yml
# ===========================================================================


class TestEngineNoConfig:
    """AC2: KanbanEngine works from board dir with no config.yml."""

    def test_engine_init_without_config_yml_does_not_raise(self, tmp_path: Path) -> None:
        """KanbanEngine(kanban_dir) must not raise when config.yml is absent."""
        board = _make_no_config_board(tmp_path)
        # Currently raises FileNotFoundError from load_config — will FAIL (RED)
        engine = KanbanEngine(board)
        assert engine is not None

    def test_board_config_statuses_match_product_constant(self, tmp_path: Path) -> None:
        """board_config().statuses must equal product-topology statuses."""
        board = _make_no_config_board(tmp_path)
        engine = KanbanEngine(board)
        config = engine.board_config()
        assert config.statuses == _EXPECTED_STATUSES

    def test_board_config_priorities_match_product_constant(self, tmp_path: Path) -> None:
        """board_config().priorities must equal product-topology priorities."""
        board = _make_no_config_board(tmp_path)
        engine = KanbanEngine(board)
        config = engine.board_config()
        assert config.priorities == _EXPECTED_PRIORITIES

    def test_board_config_pipeline_entry_status_matches_product_constant(self, tmp_path: Path) -> None:
        """board_config().pipeline.entry_status must equal product-topology entry_status."""
        board = _make_no_config_board(tmp_path)
        engine = KanbanEngine(board)
        config = engine.board_config()
        assert config.pipeline.entry_status == _EXPECTED_ENTRY_STATUS

    def test_board_config_agents_agent_map_matches_product_constant(self, tmp_path: Path) -> None:
        """board_config().agents.agent_map must equal product-topology agent_map."""
        board = _make_no_config_board(tmp_path)
        engine = KanbanEngine(board)
        config = engine.board_config()
        assert dict(config.agents.agent_map) == _EXPECTED_AGENT_MAP

    def test_board_config_next_id_defaults_to_1(self, tmp_path: Path) -> None:
        """board_config().next_id must be 1 when config.yml is absent."""
        board = _make_no_config_board(tmp_path)
        engine = KanbanEngine(board)
        config = engine.board_config()
        assert config.next_id == 1

    def test_board_config_activity_log_is_true_per_product_constant(self, tmp_path: Path) -> None:
        """board_config().activity_log must be True (product constant) without config.yml."""
        board = _make_no_config_board(tmp_path)
        engine = KanbanEngine(board)
        config = engine.board_config()
        assert config.activity_log is True


# ===========================================================================
# AC3: config.yml topology overrides are ignored
# ===========================================================================


class TestOverridesIgnored:
    """AC3: KanbanEngine.board_config() and AgentView expose product-constant values
    even when config.yml specifies different topology values."""

    def test_statuses_override_in_config_is_ignored(self, tmp_path: Path) -> None:
        """board_config().statuses must be product-constant despite config override."""
        # Override with a strict subset — still valid per STATUS_RANK
        board = _make_board_with_override(
            tmp_path,
            statuses=["research", "todo", "done"],
            pipeline={
                "entry_status": "research",
                "terminal_status": "done",
                "wave_size": 4,
                "claim_timeout": "1h",
                "default_priority": "important",
            },
            agents={
                "agent_map": {"research": "r", "todo": "b", "done": "a"},
                "agent_types": {},
                "agent_compatibility": {},
            },
        )
        engine = KanbanEngine(board)
        config = engine.board_config()
        # Currently returns ["research", "todo", "done"] → assertion FAILS (RED)
        assert config.statuses == _EXPECTED_STATUSES

    def test_priorities_override_in_config_is_ignored(self, tmp_path: Path) -> None:
        """board_config().priorities must be product-constant despite config override."""
        board = _make_board_with_override(
            tmp_path,
            priorities=["important", "critical"],
            pipeline={
                "entry_status": "research",
                "terminal_status": "done",
                "wave_size": 4,
                "claim_timeout": "1h",
                "default_priority": "important",
            },
        )
        engine = KanbanEngine(board)
        config = engine.board_config()
        # Currently returns ["important", "critical"] → assertion FAILS (RED)
        assert config.priorities == _EXPECTED_PRIORITIES

    def test_entry_status_override_in_config_is_ignored(self, tmp_path: Path) -> None:
        """pipeline.entry_status must be product-constant despite config override."""
        board = _make_board_with_override(
            tmp_path,
            pipeline={"entry_status": "todo"},
        )
        engine = KanbanEngine(board)
        config = engine.board_config()
        # Currently returns "todo" → assertion FAILS (RED)
        assert config.pipeline.entry_status == _EXPECTED_ENTRY_STATUS

    def test_terminal_status_override_in_config_is_ignored(self, tmp_path: Path) -> None:
        """pipeline.terminal_status must be product-constant despite config override."""
        board = _make_board_with_override(
            tmp_path,
            pipeline={"terminal_status": "review"},
        )
        engine = KanbanEngine(board)
        config = engine.board_config()
        # Currently returns "review" → assertion FAILS (RED)
        assert config.pipeline.terminal_status == _EXPECTED_TERMINAL_STATUS

    def test_wave_size_override_in_config_is_ignored(self, tmp_path: Path) -> None:
        """pipeline.wave_size must be product-constant despite config override."""
        board = _make_board_with_override(tmp_path, pipeline={"wave_size": 8})
        engine = KanbanEngine(board)
        config = engine.board_config()
        # Currently returns 8 → assertion FAILS (RED)
        assert config.pipeline.wave_size == _EXPECTED_WAVE_SIZE

    def test_claim_timeout_override_in_config_is_ignored(self, tmp_path: Path) -> None:
        """pipeline.claim_timeout must be product-constant despite config override."""
        board = _make_board_with_override(tmp_path, pipeline={"claim_timeout": "2h"})
        engine = KanbanEngine(board)
        config = engine.board_config()
        # Currently returns "2h" → assertion FAILS (RED)
        assert config.pipeline.claim_timeout == _EXPECTED_CLAIM_TIMEOUT

    def test_default_priority_override_in_config_is_ignored(self, tmp_path: Path) -> None:
        """pipeline.default_priority must be product-constant despite config override."""
        board = _make_board_with_override(tmp_path, pipeline={"default_priority": "critical"})
        engine = KanbanEngine(board)
        config = engine.board_config()
        # Currently returns "critical" → assertion FAILS (RED)
        assert config.pipeline.default_priority == _EXPECTED_DEFAULT_PRIORITY

    def test_agent_map_override_in_config_is_ignored(self, tmp_path: Path) -> None:
        """agents.agent_map must be product-constant despite config override."""
        custom_map = dict.fromkeys(_EXPECTED_STATUSES, "custom-agent")
        board = _make_board_with_override(
            tmp_path,
            agents={
                "agent_map": custom_map,
                "agent_types": {},
                "agent_compatibility": {},
            },
        )
        engine = KanbanEngine(board)
        config = engine.board_config()
        # Currently returns custom_map → assertion FAILS (RED)
        assert dict(config.agents.agent_map) == _EXPECTED_AGENT_MAP

    def test_non_impl_tags_override_in_config_is_ignored(self, tmp_path: Path) -> None:
        """policy.non_impl_tags must be product-constant despite config override."""
        board = _make_board_with_override(
            tmp_path,
            policy={
                "non_impl_tags": ["type:custom-tag"],
                "archival_reasons": sorted(_EXPECTED_ARCHIVAL_REASONS),
                "status_predicates": {},
            },
        )
        engine = KanbanEngine(board)
        config = engine.board_config()
        # Currently returns ["type:custom-tag"] → assertion FAILS (RED)
        assert frozenset(config.policy.non_impl_tags) == _EXPECTED_NON_IMPL_TAGS

    def test_archival_reasons_override_in_config_is_ignored(self, tmp_path: Path) -> None:
        """policy.archival_reasons must be product-constant despite config override."""
        board = _make_board_with_override(
            tmp_path,
            policy={
                "non_impl_tags": [],
                "archival_reasons": ["completed"],  # subset only
                "status_predicates": {},
            },
        )
        engine = KanbanEngine(board)
        config = engine.board_config()
        # Currently returns frozenset({"completed"}) → assertion FAILS (RED)
        assert frozenset(config.policy.archival_reasons) == _EXPECTED_ARCHIVAL_REASONS

    def test_activity_log_override_in_config_is_ignored(self, tmp_path: Path) -> None:
        """activity_log must be True per product constant, ignoring config False."""
        board = _make_board_with_override(tmp_path, activity_log=False)
        engine = KanbanEngine(board)
        config = engine.board_config()
        # Currently returns False → assertion FAILS (RED)
        assert config.activity_log is True

    def test_tasks_dir_override_in_config_is_ignored(self, tmp_path: Path) -> None:
        """paths.tasks_dir must be product-constant despite config override."""
        board = _make_board_with_override(tmp_path, paths={"tasks_dir": "custom-tasks", "archive_dir": "archive"})
        # Also create the custom-tasks directory so engine can validate path containment
        (board / "custom-tasks").mkdir(exist_ok=True)
        engine = KanbanEngine(board)
        config = engine.board_config()
        # Currently returns "custom-tasks" → assertion FAILS (RED)
        assert config.paths.tasks_dir == _EXPECTED_TASKS_DIR

    def test_archive_dir_override_in_config_is_ignored(self, tmp_path: Path) -> None:
        """paths.archive_dir must be product-constant despite config override."""
        board = _make_board_with_override(tmp_path, paths={"tasks_dir": "tasks", "archive_dir": "custom-archive"})
        (board / "custom-archive").mkdir(exist_ok=True)
        engine = KanbanEngine(board)
        config = engine.board_config()
        # Currently returns "custom-archive" → assertion FAILS (RED)
        assert config.paths.archive_dir == _EXPECTED_ARCHIVE_DIR

    def test_agent_types_override_in_config_is_ignored(self, tmp_path: Path) -> None:
        """agents.agent_types must be empty per product constant despite config override."""
        board = _make_board_with_override(
            tmp_path,
            agents={
                "agent_map": dict(_EXPECTED_AGENT_MAP),
                "agent_types": {"custom-type": "custom"},
                "agent_compatibility": {},
            },
        )
        engine = KanbanEngine(board)
        config = engine.board_config()
        # Currently returns {"custom-type": "custom"} → assertion FAILS (RED)
        assert config.agents.agent_types == {}

    def test_agent_compatibility_override_in_config_is_ignored(self, tmp_path: Path) -> None:
        """agents.agent_compatibility must be empty per product constant despite config override."""
        board = _make_board_with_override(
            tmp_path,
            agents={
                "agent_map": dict(_EXPECTED_AGENT_MAP),
                "agent_types": {},
                "agent_compatibility": {
                    "builder": ["reviewer"],
                    "reviewer": ["builder"],
                },
            },
        )
        engine = KanbanEngine(board)
        config = engine.board_config()
        # Currently returns {"builder": [...], "reviewer": [...]} → assertion FAILS (RED)
        assert config.agents.agent_compatibility == {}

    def test_status_predicates_override_in_config_is_ignored(self, tmp_path: Path) -> None:
        """policy.status_predicates must be empty per product constant despite config override."""
        board = _make_board_with_override(
            tmp_path,
            policy={
                "non_impl_tags": [],
                "archival_reasons": sorted(_EXPECTED_ARCHIVAL_REASONS),
                "status_predicates": {"research": "some_predicate"},
            },
        )
        engine = KanbanEngine(board)
        config = engine.board_config()
        # Currently returns {"research": "some_predicate"} → assertion FAILS (RED)
        assert config.policy.status_predicates == {}

    def test_agent_view_list_tasks_uses_product_statuses_not_config(self, tmp_path: Path) -> None:
        """AgentView.list_tasks(status=...) must use product statuses for validation.

        Override config to only have 3 statuses; then call list_tasks with a
        product-topology status not in the override (e.g. 'in-progress').  After
        the refactor this must succeed; currently it would raise ValidationError
        because the override config does not include 'in-progress'.
        """
        board = _make_board_with_override(
            tmp_path,
            statuses=["research", "todo", "done"],
            pipeline={
                "entry_status": "research",
                "terminal_status": "done",
                "wave_size": 4,
                "claim_timeout": "1h",
                "default_priority": "important",
            },
            agents={
                "agent_map": {"research": "r", "todo": "b", "done": "a"},
                "agent_types": {},
                "agent_compatibility": {},
            },
        )
        engine = KanbanEngine(board)
        av = engine.agent_view()
        # "in-progress" is a product-topology status but absent from the override config.
        # After refactor: succeeds (returns empty list — no tasks).
        # Currently: raises ValidationError (ERR_INVALID_STATUS) → test FAILS (RED)
        result = av.list_tasks(status="in-progress")
        assert result is not None

    def test_agent_view_create_task_uses_product_entry_status_not_config(self, tmp_path: Path) -> None:
        """AgentView.create_task places new tasks at product entry_status, ignoring config.

        Config override sets entry_status='todo'; product constant is 'research'.
        After refactor: task.status == 'research'.
        Before refactor: task.status == 'todo' → assertion FAILS (RED).
        """
        board = _make_board_with_override(
            tmp_path,
            pipeline={"entry_status": "todo"},
        )
        engine = KanbanEngine(board)
        av = engine.agent_view()
        result = av.create_task(title="Entry status test task")
        # After refactor: product entry_status='research'
        # Before refactor: config entry_status='todo' → assertion FAILS (RED)
        assert result.status == _EXPECTED_ENTRY_STATUS

    def test_agent_view_pick_tasks_agent_map_uses_product_constant_not_config(self, tmp_path: Path) -> None:
        """AgentView.pick_tasks assigns agent from product agent_map, not config override.

        Config override maps all statuses to 'custom-agent'; product constant maps
        'research' to 'researcher'. After refactor: dispatched entry has agent='researcher'.
        Before refactor: agent='custom-agent' → assertion FAILS (RED).
        """
        custom_map = dict.fromkeys(_EXPECTED_STATUSES, "custom-agent")
        board = _make_board_with_override(
            tmp_path,
            agents={
                "agent_map": custom_map,
                "agent_types": {},
                "agent_compatibility": {},
            },
        )
        tasks_dir = board / "tasks"
        now = "2026-01-01T00:00:00+00:00"
        # tag=research (non_impl_tag) → passes TDD gate; bullet → passes clarity gate
        task_content = (
            "---\n"
            "id: 1\n"
            "title: 'Dispatch test'\n"
            "status: research\n"
            "priority: important\n"
            f"created: {now}\n"
            f"updated: {now}\n"
            "tags: [research]\n"
            "depends_on: []\n"
            "blocked: false\n"
            "---\n"
            "- AC: verify agent dispatch uses product constant\n"
        )
        (tasks_dir / "1-dispatch-test.md").write_text(task_content, encoding="utf-8")
        engine = KanbanEngine(board)
        av = engine.agent_view()
        result = av.pick_tasks()
        # After refactor: agent for 'research' = 'researcher' (product constant)
        # Before refactor: agent = 'custom-agent' (config override) → FAILS (RED)
        assert len(result.waves) == 1
        assert result.waves[0].tasks[0].agent == _EXPECTED_AGENT_MAP["research"]

    def test_agent_view_move_task_terminal_status_uses_product_constant_not_config(self, tmp_path: Path) -> None:
        """AgentView.move_task resolves can_mark_completed against product terminal_status.

        Config override sets terminal_status='review'; product constant is 'done'.
        A task at status='done' must be archivable with reason='completed' because
        it is at the product terminal status.
        After refactor: succeeds (can_mark_completed=True).
        Before refactor: can_mark_completed=False (config says terminal='review')
        → raises ERR_COMPLETED_REQUIRES_DONE → assertion FAILS (RED).
        """
        board = _make_board_with_override(
            tmp_path,
            pipeline={"terminal_status": "review"},
        )
        tasks_dir = board / "tasks"
        now = "2026-01-01T00:00:00+00:00"
        task_content = (
            "---\n"
            "id: 1\n"
            "title: 'Terminal status test'\n"
            "status: done\n"
            "priority: important\n"
            f"created: {now}\n"
            f"updated: {now}\n"
            "tags: []\n"
            "depends_on: []\n"
            "blocked: false\n"
            "---\n"
            "Body.\n"
        )
        (tasks_dir / "1-terminal-test.md").write_text(task_content, encoding="utf-8")
        engine = KanbanEngine(board)
        av = engine.agent_view()
        # After refactor: terminal_status='done' (product constant) → can_mark_completed=True
        # Before refactor: terminal_status='review' (config) → can_mark_completed=False
        #   → validate_archival raises ERR_COMPLETED_REQUIRES_DONE → FAILS (RED)
        result = av.move_task(1, "archived", archival_reason="completed")
        assert result.status == "archived"


# ===========================================================================
# AC4: load_config, save_config, attribute paths, dispatch ref, frontmatter
# ===========================================================================


class TestLoadSaveAndDispatch:
    """AC4: load_config/save_config behaviour, backward-compat paths, dispatch ref,
    and frontmatter validation all use the product-topology constant."""

    # --- load_config without config.yml ---

    def test_load_config_absent_does_not_raise(self, tmp_path: Path) -> None:
        """load_config must not raise FileNotFoundError when config.yml is absent."""
        board = _make_no_config_board(tmp_path)
        # Currently raises FileNotFoundError → test FAILS (RED)
        config = load_config(board)
        assert config is not None

    def test_load_config_absent_returns_product_statuses(self, tmp_path: Path) -> None:
        """load_config on absent config.yml returns product-topology statuses."""
        board = _make_no_config_board(tmp_path)
        config = load_config(board)
        assert config.statuses == _EXPECTED_STATUSES

    def test_load_config_absent_returns_product_priorities(self, tmp_path: Path) -> None:
        """load_config on absent config.yml returns product-topology priorities."""
        board = _make_no_config_board(tmp_path)
        config = load_config(board)
        assert config.priorities == _EXPECTED_PRIORITIES

    def test_load_config_absent_next_id_defaults_to_1(self, tmp_path: Path) -> None:
        """load_config on absent config.yml returns next_id == 1."""
        board = _make_no_config_board(tmp_path)
        config = load_config(board)
        assert config.next_id == 1

    def test_load_config_with_next_id_file_reads_next_id(self, tmp_path: Path) -> None:
        """load_config reads next_id from config.yml when file is present."""
        board = _make_no_config_board(tmp_path)
        (board / "config.yml").write_text("next_id: 99\n", encoding="utf-8")
        config = load_config(board)
        assert config.next_id == 99

    # --- save_config writes only next_id ---

    def test_save_config_output_has_no_statuses_key(self, tmp_path: Path) -> None:
        """save_config must NOT write 'statuses' to config.yml."""
        board = tmp_path / "board"
        board.mkdir()
        config = BoardConfig(
            statuses=list(_EXPECTED_STATUSES),
            priorities=list(_EXPECTED_PRIORITIES),
            next_id=5,
        )
        save_config(config, board)
        data = yaml.safe_load((board / "config.yml").read_text(encoding="utf-8"))
        # Currently save_config writes statuses → 'statuses' IS present → FAILS (RED)
        assert "statuses" not in data

    def test_save_config_output_has_no_agent_map_key(self, tmp_path: Path) -> None:
        """save_config must NOT write 'agent_map' or 'agents' topology to config.yml."""
        board = tmp_path / "board"
        board.mkdir()
        config = BoardConfig(
            statuses=list(_EXPECTED_STATUSES),
            priorities=list(_EXPECTED_PRIORITIES),
            next_id=7,
        )
        save_config(config, board)
        raw = yaml.safe_load((board / "config.yml").read_text(encoding="utf-8"))
        # Currently writes nested 'agents' → assertion FAILS (RED)
        assert "agents" not in raw
        assert "agent_map" not in raw

    def test_save_config_output_contains_only_next_id_key(self, tmp_path: Path) -> None:
        """After save_config, config.yml must contain next_id and no topology fields."""
        board = tmp_path / "board"
        board.mkdir()
        config = BoardConfig(
            statuses=list(_EXPECTED_STATUSES),
            priorities=list(_EXPECTED_PRIORITIES),
            next_id=3,
        )
        save_config(config, board)
        raw = yaml.safe_load((board / "config.yml").read_text(encoding="utf-8")) or {}
        # next_id must be present (allocate_next_id depends on it)
        assert raw.get("next_id") == 3
        # Topology keys that must NOT appear:
        topology_keys = {
            "statuses",
            "priorities",
            "paths",
            "pipeline",
            "agents",
            "policy",
            "activity_log",
            "agent_map",
            "non_impl_tags",
        }
        present_topology_keys = topology_keys & set(raw.keys())
        # Currently all topology keys are present → assertion FAILS (RED)
        assert not present_topology_keys, f"save_config wrote topology fields: {present_topology_keys}"

    # --- board_config attribute paths preserved ---

    def test_board_config_statuses_attribute_path_accessible(self, tmp_path: Path) -> None:
        """board_config().statuses must be accessible (backward-compat path)."""
        board = _make_no_config_board(tmp_path)
        engine = KanbanEngine(board)
        config = engine.board_config()
        # Currently engine init fails → FAILS (RED); after fix: passes
        assert isinstance(config.statuses, list)

    def test_board_config_pipeline_entry_status_attribute_path_accessible(self, tmp_path: Path) -> None:
        """board_config().pipeline.entry_status must be accessible."""
        board = _make_no_config_board(tmp_path)
        engine = KanbanEngine(board)
        config = engine.board_config()
        assert config.pipeline.entry_status == _EXPECTED_ENTRY_STATUS

    def test_board_config_agents_agent_map_attribute_path_accessible(self, tmp_path: Path) -> None:
        """board_config().agents.agent_map must equal product-topology agent_map."""
        board = _make_no_config_board(tmp_path)
        engine = KanbanEngine(board)
        config = engine.board_config()
        assert dict(config.agents.agent_map) == _EXPECTED_AGENT_MAP

    def test_board_config_policy_non_impl_tags_attribute_path_accessible(self, tmp_path: Path) -> None:
        """board_config().policy.non_impl_tags must equal product-topology non_impl_tags."""
        board = _make_no_config_board(tmp_path)
        engine = KanbanEngine(board)
        config = engine.board_config()
        assert frozenset(config.policy.non_impl_tags) == _EXPECTED_NON_IMPL_TAGS

    def test_board_config_paths_tasks_dir_attribute_path_accessible(self, tmp_path: Path) -> None:
        """board_config().paths.tasks_dir must be accessible."""
        board = _make_no_config_board(tmp_path)
        engine = KanbanEngine(board)
        config = engine.board_config()
        assert config.paths.tasks_dir == _EXPECTED_TASKS_DIR

    def test_board_config_paths_archive_dir_attribute_path_accessible(self, tmp_path: Path) -> None:
        """board_config().paths.archive_dir must be accessible."""
        board = _make_no_config_board(tmp_path)
        engine = KanbanEngine(board)
        config = engine.board_config()
        assert config.paths.archive_dir == _EXPECTED_ARCHIVE_DIR

    # --- dispatch._NON_IMPL_TAGS references product constant ---

    def test_dispatch_non_impl_tags_values_match_product_constant(self) -> None:
        """dispatch._NON_IMPL_TAGS must reference the product-topology non_impl_tags.

        After refactor, dispatch._NON_IMPL_TAGS is not an inline frozenset — it
        is the same object as PRODUCT_TOPOLOGY.non_impl_tags.
        """
        from owlbear_kanban import dispatch

        mod = importlib.import_module("owlbear_kanban.topology")
        # Identity: dispatch._NON_IMPL_TAGS IS PRODUCT_TOPOLOGY.non_impl_tags
        # Currently dispatch._NON_IMPL_TAGS is a separate inline frozenset → FAILS (RED)
        assert dispatch._NON_IMPL_TAGS is mod.PRODUCT_TOPOLOGY.non_impl_tags

    # --- frontmatter validates against product topology ---

    def test_task_with_released_status_invalid_per_product_topology(self, tmp_path: Path) -> None:
        """A task with status='released' must fail corruption detection.

        'released' is in dispatch.STATUS_RANK but not in the product topology
        statuses.  When the engine uses the product constant for validation,
        reading this task must raise CorruptionError(ERR_CORRUPT_INVALID_STATUS).

        Currently the config allows any STATUS_RANK value, so no error is raised
        → assertion FAILS (RED).
        """
        # Board whose config explicitly allows "released" as a valid status
        board = _make_board_with_override(
            tmp_path,
            statuses=["research", "released", "done"],
            pipeline={
                "entry_status": "research",
                "terminal_status": "done",
                "wave_size": 4,
                "claim_timeout": "1h",
                "default_priority": "important",
            },
            agents={
                "agent_map": {"research": "r", "released": "r", "done": "a"},
                "agent_types": {},
                "agent_compatibility": {},
            },
        )
        tasks_dir = board / "tasks"
        _write_task_file(tasks_dir, task_id=1, status="released", priority="important")
        engine = KanbanEngine(board)
        # After refactor: CorruptionError raised (released not in product topology)
        # Currently: no error (config allows released) → pytest.raises fails → RED
        with pytest.raises(CorruptionError) as exc_info:
            engine.show_task("1")
        assert exc_info.value.code == ERR_CORRUPT_INVALID_STATUS

    def test_task_with_product_priority_valid_regardless_of_config_override(self, tmp_path: Path) -> None:
        """A task whose priority is in the product topology must be valid even if
        the config.yml override restricts priorities to a subset.

        Board config has priorities=["important"] only.
        Task has priority="critical" (in product topology but not in config override).
        After refactor: read_task must succeed (product topology includes "critical").
        Currently: raises CorruptionError(ERR_CORRUPT_INVALID_PRIORITY) → RED.
        """
        board = _make_board_with_override(
            tmp_path,
            priorities=["important"],
            pipeline={
                "entry_status": "research",
                "terminal_status": "done",
                "wave_size": 4,
                "claim_timeout": "1h",
                "default_priority": "important",
            },
        )
        tasks_dir = board / "tasks"
        _write_task_file(tasks_dir, task_id=1, status="research", priority="critical")
        engine = KanbanEngine(board)
        # After refactor: succeeds (product topology has "critical")
        # Currently: raises CorruptionError (config only allows "important") → RED
        task = engine.show_task("1")
        assert task is not None
        assert task.priority == "critical"

    def test_task_tags_are_preserved_on_read(self, tmp_path: Path) -> None:
        """Task tags are parsed from frontmatter and returned correctly by engine.

        AC4 names tags as a per-task data field validated via the engine's
        product-topology-backed read path.  After refactor, tags must round-trip.
        """
        board = _make_no_config_board(tmp_path)
        now = "2026-01-01T00:00:00+00:00"
        task_content = (
            "---\n"
            "id: 1\n"
            "title: 'Tag round-trip test'\n"
            "status: research\n"
            "priority: important\n"
            f"created: {now}\n"
            f"updated: {now}\n"
            "tags: [scope:backend, type:refactor]\n"
            "depends_on: []\n"
            "blocked: false\n"
            "---\n"
            "Body.\n"
        )
        (board / "tasks" / "1-tag-round-trip.md").write_text(task_content, encoding="utf-8")
        engine = KanbanEngine(board)
        # Currently engine init raises FileNotFoundError → test FAILS (RED)
        task = engine.show_task("1")
        assert list(task.tags) == ["scope:backend", "type:refactor"]

    def test_task_blocked_true_is_preserved_on_read(self, tmp_path: Path) -> None:
        """Task blocked=true is parsed from frontmatter and returned correctly by engine.

        AC4 names blocked as a per-task data field validated via the engine's
        product-topology-backed read path.  After refactor, blocked must round-trip.
        """
        board = _make_no_config_board(tmp_path)
        now = "2026-01-01T00:00:00+00:00"
        task_content = (
            "---\n"
            "id: 1\n"
            "title: 'Blocked round-trip test'\n"
            "status: research\n"
            "priority: important\n"
            f"created: {now}\n"
            f"updated: {now}\n"
            "tags: []\n"
            "depends_on: []\n"
            "blocked: true\n"
            "block_reason: waiting for upstream\n"
            "---\n"
            "Body.\n"
        )
        (board / "tasks" / "1-blocked-round-trip.md").write_text(task_content, encoding="utf-8")
        engine = KanbanEngine(board)
        # Currently engine init raises FileNotFoundError → test FAILS (RED)
        task = engine.show_task("1")
        assert task.blocked is True
        assert task.block_reason == "waiting for upstream"
