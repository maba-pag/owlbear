"""RED-phase tests for lazy agent_map validation (#1221).

AC coverage:
- AC1: KanbanEngine.__init__ no longer raises ConfigError for missing agent_map entries
- AC2: pick_tasks() raises ConfigError(ERR_INVALID_STATUS) for incomplete agent_map (td:2)
        — validates at top of method, before filtering/sorting/wave assembly
- AC3: Cockpit starts successfully with agent_map: {} in grouped config
- AC4: MCP pick_tasks raises (ToolError from ConfigError) with missing-entry message

RED strategy:
- AC1/AC3 tests: fail at KanbanEngine.__init__ (currently raises for missing agent_map)
- AC2/AC4 tests: fail because pick_tasks() does not yet validate agent_map
  (uses refresh_config() to reload incomplete config without triggering init validation)
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_kanban.errors import ConfigError, ValidationError

# ---------------------------------------------------------------------------
# Board config fixtures
# ---------------------------------------------------------------------------

_BASE_CONFIG_COMPLETE = """\
schema: grouped
statuses:
  - research
  - backlog
  - todo
  - in-progress
  - review
  - done
priorities:
  - critical
  - needed
  - important
  - nice-to-have
  - someday
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
        in-progress: builder
        review: reviewer
        done: auditor
    agent_types: {}
    agent_compatibility: {}
policy:
    non_impl_tags: [research, docs]
    archival_reasons: [completed, deprecated, dropped, duplicate, wontfix]
    status_predicates: {}
"""

# agent_map is completely empty — all 6 statuses are missing
_BASE_CONFIG_EMPTY_AGENT_MAP = """\
schema: grouped
statuses:
  - research
  - backlog
  - todo
  - in-progress
  - review
  - done
priorities:
  - critical
  - needed
  - important
  - nice-to-have
  - someday
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
    agent_map: {}
    agent_types: {}
    agent_compatibility: {}
policy:
    non_impl_tags: [research, docs]
    archival_reasons: [completed, deprecated, dropped, duplicate, wontfix]
    status_predicates: {}
"""

# wave_size: 0 AND agent_map: {} — exercises effective_wave < 1 guard before agent_map guard
_BASE_CONFIG_ZERO_WAVE_EMPTY_AGENT_MAP = """\
schema: grouped
statuses:
  - research
  - backlog
  - todo
  - in-progress
  - review
  - done
priorities:
  - critical
  - needed
  - important
  - nice-to-have
  - someday
next_id: 1
paths:
    tasks_dir: tasks
    archive_dir: archive
pipeline:
    entry_status: research
    terminal_status: done
    wave_size: 0
    claim_timeout: 1h
agents:
    agent_map: {}
    agent_types: {}
    agent_compatibility: {}
policy:
    non_impl_tags: [research, docs]
    archival_reasons: [completed, deprecated, dropped, duplicate, wontfix]
    status_predicates: {}
"""

# agent_map has only 2 of 6 statuses — "todo", "in-progress", "review", "done" are missing
_BASE_CONFIG_PARTIAL_AGENT_MAP = """\
schema: grouped
statuses:
  - research
  - backlog
  - todo
  - in-progress
  - review
  - done
priorities:
  - critical
  - needed
  - important
  - nice-to-have
  - someday
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
    agent_types: {}
    agent_compatibility: {}
policy:
    non_impl_tags: [research, docs]
    archival_reasons: [completed, deprecated, dropped, duplicate, wontfix]
    status_predicates: {}
"""

_TASK_TMPL = """\
---
id: {task_id}
title: Task {task_id}
status: {status}
priority: needed
created: "2026-01-01T10:00:00+00:00"
updated: "2026-01-01T10:00:00+00:00"
tags: []
parent: null
depends_on: []
blocked: false
block_reason: null
claimed_at: null
archival_reason: null
archival_refs: []
---
Task body.
"""


def _make_board(base_dir: Path, config_yaml: str = _BASE_CONFIG_COMPLETE) -> Path:
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(config_yaml, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


def _write_task(kanban_dir: Path, task_id: int = 1, status: str = "todo") -> None:
    content = _TASK_TMPL.format(task_id=task_id, status=status)
    filename = f"{task_id:04d}-task-{task_id}.md"
    (kanban_dir / "tasks" / filename).write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# TestFromAC_InitNoLongerRaises  (AC1)
# ---------------------------------------------------------------------------


class TestFromAC_InitNoLongerRaises:
    """KanbanEngine.__init__ must not raise ConfigError for missing agent_map entries.

    Currently __init__ calls _validate_engine_config() which raises for any status
    absent from agent_map.  After the fix, that check is removed from __init__.
    """

    def test_init_accepts_empty_agent_map(self, tmp_path: Path) -> None:
        """KanbanEngine.__init__ with agent_map: {} must not raise ConfigError."""
        kanban_dir = _make_board(tmp_path, _BASE_CONFIG_EMPTY_AGENT_MAP)
        # RED: currently raises ConfigError("agent_map missing status entries: ...")
        engine = KanbanEngine(kanban_dir)
        assert engine is not None

    def test_init_accepts_partial_agent_map(self, tmp_path: Path) -> None:
        """KanbanEngine.__init__ with partially populated agent_map must not raise ConfigError."""
        kanban_dir = _make_board(tmp_path, _BASE_CONFIG_PARTIAL_AGENT_MAP)
        # RED: currently raises ConfigError for missing todo/in-progress/review/done
        engine = KanbanEngine(kanban_dir)
        assert engine is not None


# ---------------------------------------------------------------------------
# TestFromAC_PickTasksValidatesAgentMap  (AC2)
# ---------------------------------------------------------------------------


class TestFromAC_PickTasksValidatesAgentMap:
    """pick_tasks() must validate agent_map at the top of the method.

    Tests use a complete config for init (so engine is created), then reload
    an incomplete config via refresh_config() so the validation failure is in
    pick_tasks(), not in __init__.
    """

    def test_pick_tasks_raises_config_error_for_empty_agent_map(self, tmp_path: Path) -> None:
        """pick_tasks raises ConfigError when agent_map is empty (no tasks on board)."""
        kanban_dir = _make_board(tmp_path, _BASE_CONFIG_COMPLETE)
        engine = KanbanEngine(kanban_dir)
        av = engine.agent_view()

        # Swap to a config with no agent_map entries; refresh skips __init__ validation
        (kanban_dir / "config.yml").write_text(_BASE_CONFIG_EMPTY_AGENT_MAP, encoding="utf-8")
        engine.refresh_config()

        # RED: pick_tasks currently returns PickTasksResponse(waves=[]) without raising
        with pytest.raises(ConfigError):
            av.pick_tasks()

    def test_pick_tasks_raises_config_error_for_partial_agent_map(self, tmp_path: Path) -> None:
        """pick_tasks raises ConfigError when some statuses are absent from agent_map."""
        kanban_dir = _make_board(tmp_path, _BASE_CONFIG_COMPLETE)
        engine = KanbanEngine(kanban_dir)
        av = engine.agent_view()

        (kanban_dir / "config.yml").write_text(_BASE_CONFIG_PARTIAL_AGENT_MAP, encoding="utf-8")
        engine.refresh_config()

        # RED: pick_tasks currently does not check agent_map completeness
        with pytest.raises(ConfigError):
            av.pick_tasks()

    def test_pick_tasks_error_code_is_err_invalid_status(self, tmp_path: Path) -> None:
        """ConfigError raised by pick_tasks must carry code='ERR_INVALID_STATUS'."""
        kanban_dir = _make_board(tmp_path, _BASE_CONFIG_COMPLETE)
        engine = KanbanEngine(kanban_dir)
        av = engine.agent_view()

        (kanban_dir / "config.yml").write_text(_BASE_CONFIG_EMPTY_AGENT_MAP, encoding="utf-8")
        engine.refresh_config()

        # RED: no ConfigError raised → exc_info assertion never reached
        with pytest.raises(ConfigError) as exc_info:
            av.pick_tasks()
        assert exc_info.value.code == "ERR_INVALID_STATUS"

    def test_pick_tasks_error_message_names_missing_statuses(self, tmp_path: Path) -> None:
        """ConfigError user_message must identify at least one missing status entry."""
        kanban_dir = _make_board(tmp_path, _BASE_CONFIG_COMPLETE)
        engine = KanbanEngine(kanban_dir)
        av = engine.agent_view()

        # Partial config: research + backlog only; todo/in-progress/review/done absent
        (kanban_dir / "config.yml").write_text(_BASE_CONFIG_PARTIAL_AGENT_MAP, encoding="utf-8")
        engine.refresh_config()

        # RED: no ConfigError raised → assertion never reached
        with pytest.raises(ConfigError) as exc_info:
            av.pick_tasks()
        msg = exc_info.value.user_message
        # Message must mention at least one missing status by name
        assert any(s in msg for s in ("todo", "in-progress", "review", "done", "missing")), (
            f"Error message must name missing statuses; got: {msg!r}"
        )

    def test_pick_tasks_validates_before_filtering_with_tasks_present(self, tmp_path: Path) -> None:
        """pick_tasks validates agent_map before filtering tasks (AC2 placement rule).

        With a dispatchable task on the board, pick_tasks must still raise ConfigError
        rather than returning the task — proving validation fires before filtering.
        """
        kanban_dir = _make_board(tmp_path, _BASE_CONFIG_COMPLETE)
        engine = KanbanEngine(kanban_dir)
        _write_task(kanban_dir, task_id=1, status="todo")
        av = engine.agent_view()

        (kanban_dir / "config.yml").write_text(_BASE_CONFIG_EMPTY_AGENT_MAP, encoding="utf-8")
        engine.refresh_config()

        # RED: pick_tasks currently returns the task instead of raising
        with pytest.raises(ConfigError):
            av.pick_tasks()

    def test_pick_tasks_validates_before_list_tasks_is_called(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Ordering proof: list_tasks is NOT called when agent_map validation fails.

        If list_tasks is never invoked, the ConfigError must have been raised before
        the filtering stage — a non-call proof of AC2's placement invariant.
        """
        kanban_dir = _make_board(tmp_path, _BASE_CONFIG_COMPLETE)
        engine = KanbanEngine(kanban_dir)
        av = engine.agent_view()

        (kanban_dir / "config.yml").write_text(_BASE_CONFIG_EMPTY_AGENT_MAP, encoding="utf-8")
        engine.refresh_config()

        list_tasks_calls: list[tuple] = []
        original_list_tasks = engine.list_tasks

        def spy_list_tasks(*args: object, **kwargs: object) -> object:
            list_tasks_calls.append((args, kwargs))
            return original_list_tasks(*args, **kwargs)

        monkeypatch.setattr(engine, "list_tasks", spy_list_tasks)

        with pytest.raises(ConfigError):
            av.pick_tasks()

        assert list_tasks_calls == [], (
            "list_tasks must NOT be called when agent_map validation raises ConfigError "
            f"(was called {len(list_tasks_calls)} time(s))"
        )

    def test_pick_tasks_effective_wave_guard_fires_before_agent_map_guard(self, tmp_path: Path) -> None:
        """AC7 conflict proof: ERR_INVALID_WAVE_PARAM wins when effective_wave < 1 AND agent_map is incomplete.

        Config has wave_size: 0 (effective_wave = 0 < 1) and agent_map: {}.
        pick_tasks() with no explicit wave_size arg must raise ValidationError
        (ERR_INVALID_WAVE_PARAM), not ConfigError (ERR_INVALID_STATUS).
        This proves the effective_wave < 1 guard at engine.py:2327 executes before
        the agent_map completeness check at engine.py:2333.
        """
        kanban_dir = _make_board(tmp_path, _BASE_CONFIG_COMPLETE)
        engine = KanbanEngine(kanban_dir)
        av = engine.agent_view()

        (kanban_dir / "config.yml").write_text(_BASE_CONFIG_ZERO_WAVE_EMPTY_AGENT_MAP, encoding="utf-8")
        engine.refresh_config()

        with pytest.raises(ValidationError) as exc_info:
            av.pick_tasks()  # no explicit wave_size arg → effective_wave = config.wave_size = 0

        assert exc_info.value.code == "ERR_INVALID_WAVE_PARAM", (
            f"Expected ERR_INVALID_WAVE_PARAM but got code={exc_info.value.code!r}; "
            "effective_wave guard must fire before agent_map guard"
        )


# ---------------------------------------------------------------------------
# TestFromAC_CockpitInitWithEmptyAgentMap  (AC3)
# ---------------------------------------------------------------------------


class TestFromAC_CockpitInitWithEmptyAgentMap:
    """Cockpit must be able to create KanbanEngine with agent_map: {} (grouped config).

    Cockpit is a read-only consumer that never calls pick_tasks — it must not be
    blocked by dispatcher-only validation at __init__ time.
    """

    def test_cockpit_engine_init_succeeds_with_empty_agent_map(self, tmp_path: Path) -> None:
        """KanbanEngine(kanban_dir) must not raise for agent_map: {}."""
        kanban_dir = _make_board(tmp_path, _BASE_CONFIG_EMPTY_AGENT_MAP)
        # RED: currently raises ConfigError at __init__
        engine = KanbanEngine(kanban_dir)
        assert engine is not None

    def test_cockpit_engine_board_config_accessible_with_empty_agent_map(self, tmp_path: Path) -> None:
        """board_config() must be callable after cockpit init with empty agent_map."""
        kanban_dir = _make_board(tmp_path, _BASE_CONFIG_EMPTY_AGENT_MAP)
        # RED: engine creation currently fails before board_config() can be called
        engine = KanbanEngine(kanban_dir)
        cfg = engine.board_config()
        assert cfg is not None


# ---------------------------------------------------------------------------
# TestFromAC_McpPickTasksRaisesForIncompleteAgentMap  (AC4)
# ---------------------------------------------------------------------------


class TestFromAC_McpPickTasksRaisesForIncompleteAgentMap:
    """MCP pick_tasks must surface ConfigError as ToolError when agent_map is incomplete."""

    @pytest.mark.asyncio
    async def test_mcp_pick_tasks_raises_tool_error_for_incomplete_agent_map(self, tmp_path: Path) -> None:
        """pick_tasks MCP handler must raise ToolError when agent_map is missing entries."""
        from mcp.server.fastmcp.exceptions import ToolError

        from owlbear_mcp_kanban.server import AppContext, pick_tasks

        kanban_dir = _make_board(tmp_path, _BASE_CONFIG_COMPLETE)
        engine = KanbanEngine(kanban_dir)

        # Reload with incomplete agent_map
        (kanban_dir / "config.yml").write_text(_BASE_CONFIG_EMPTY_AGENT_MAP, encoding="utf-8")
        engine.refresh_config()

        app_ctx = AppContext(engine=engine, kanban_dir=kanban_dir)

        ctx = MagicMock()
        ctx.request_context.lifespan_context = app_ctx

        # RED: pick_tasks currently returns PickTasksResponse(waves=[]) → no ToolError raised
        with pytest.raises(ToolError):
            await pick_tasks(ctx)

    @pytest.mark.asyncio
    async def test_mcp_pick_tasks_tool_error_message_contains_missing_entries(self, tmp_path: Path) -> None:
        """ToolError raised by MCP pick_tasks must carry the ConfigError user_message."""
        from mcp.server.fastmcp.exceptions import ToolError

        from owlbear_mcp_kanban.server import AppContext, pick_tasks

        kanban_dir = _make_board(tmp_path, _BASE_CONFIG_COMPLETE)
        engine = KanbanEngine(kanban_dir)

        (kanban_dir / "config.yml").write_text(_BASE_CONFIG_PARTIAL_AGENT_MAP, encoding="utf-8")
        engine.refresh_config()

        app_ctx = AppContext(engine=engine, kanban_dir=kanban_dir)

        ctx = MagicMock()
        ctx.request_context.lifespan_context = app_ctx

        # RED: no ToolError raised → assertion never reached
        with pytest.raises(ToolError) as exc_info:
            await pick_tasks(ctx)
        error_text = str(exc_info.value)
        assert any(s in error_text for s in ("missing", "agent_map", "todo", "in-progress")), (
            f"ToolError message must reference missing agent_map entries; got: {error_text!r}"
        )

    @pytest.mark.asyncio
    async def test_mcp_pick_tasks_tool_error_message_names_all_missing_statuses(self, tmp_path: Path) -> None:
        """ToolError message must contain ALL four missing status names (exact AC4 contract).

        Partial config has research + backlog in agent_map; todo, in-progress, review,
        and done are absent.  Every absent status must appear in the propagated message.
        """
        from mcp.server.fastmcp.exceptions import ToolError

        from owlbear_mcp_kanban.server import AppContext, pick_tasks

        kanban_dir = _make_board(tmp_path, _BASE_CONFIG_COMPLETE)
        engine = KanbanEngine(kanban_dir)

        (kanban_dir / "config.yml").write_text(_BASE_CONFIG_PARTIAL_AGENT_MAP, encoding="utf-8")
        engine.refresh_config()

        app_ctx = AppContext(engine=engine, kanban_dir=kanban_dir)

        ctx = MagicMock()
        ctx.request_context.lifespan_context = app_ctx

        with pytest.raises(ToolError) as exc_info:
            await pick_tasks(ctx)
        error_text = str(exc_info.value)
        # All four absent statuses must be individually named in the propagated message
        for missing_status in ("todo", "in-progress", "review", "done"):
            assert missing_status in error_text, (
                f"ToolError must name missing status {missing_status!r}; got: {error_text!r}"
            )
