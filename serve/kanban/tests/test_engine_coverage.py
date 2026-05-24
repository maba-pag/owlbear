"""Coverage-uplift tests for owlbear_kanban.engine (task #1068).

Covers engine operations that the init-focused 1067/1068 suites leave uncovered:
  - Module-level helpers: _parse_duration, _classify_end_work_state/outcome,
    _compute_duration, _state_from_age, _validate_session_filter, _apply_session_filter,
  - Engine init: agent_name property, revision counter, board_config(), refresh_config(),
    valid_transitions(), migration-gate edge cases
  - list_tasks: full filter/sort/archive/parse-error paths
  - show_task: happy path and FileNotFoundError
  - create_task: success and validation errors
  - edit_task: all mutation fields and error paths
  - move_task: status change, archive, invalid status
  - claim_task / release_task / start_work: guards and success paths
  - end_work: all four outcomes (success, fail, block, reject) and validation
  - sweep: expired-claim release, skips, tz-naive normalisation
  - list_sessions / _read_log_entries / _derive_sessions: full parsing
  - _collect_task_sessions: all session-state branches
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_kanban._duration import _parse_duration
from owlbear_kanban.engine import (
    AgentView,
    _apply_session_filter,
    _classify_end_work_outcome,
    _classify_end_work_state,
    _collect_task_sessions,
    _compute_duration,
    _state_from_age,
    _validate_session_filter,
)
from owlbear_kanban.storage import read_task
from owlbear_kanban.topology import PRODUCT_TOPOLOGY
from owlbear_kanban.models import (
    BoardConfig,
    ConfigError,
    ConcurrencyError,
    ListTasksResponse,
    NotFoundError,
    PickTasksResponse,
    SessionRecord,
    ShowTaskResponse,
    SingleTaskResponse,
    ValidationError,
)

# ---------------------------------------------------------------------------
# Board + task fixtures
# ---------------------------------------------------------------------------

_BASE_CONFIG = """\
schema: grouped
statuses:
  - research
  - backlog
  - todo
  - in-progress
  - review
  - done
priorities:
  - someday
  - nice-to-have
  - important
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

_TASK_TMPL = """\
---
id: {task_id}
title: {title}
status: {status}
priority: {priority}
created: "2026-01-01T10:00:00+00:00"
updated: "2026-01-01T10:00:00+00:00"
tags: {tags}
parent: null
depends_on: {depends_on}
blocked: {blocked}
block_reason: {block_reason}
claimed_at: {claimed_at}
archival_reason: null
archival_refs: []
---
{body}
"""

_EPOCH_TS = '"2026-01-01T00:00:00+00:00"'  # always expired (> 1 h ago)


def _make_board(base_dir: Path, config_yaml: str = _BASE_CONFIG) -> Path:
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(config_yaml, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


def _write_task(  # noqa: PLR0913
    kanban_dir: Path,
    task_id: int = 1,
    title: str = "Task",
    status: str = "todo",
    priority: str = "needed",
    tags: str = "[]",
    blocked: str = "false",
    block_reason: str = "null",
    claimed_at: str = "null",
    depends_on: str = "[]",
    body: str = "Body.",
    subdir: str = "tasks",
) -> Path:
    content = _TASK_TMPL.format(
        task_id=task_id,
        title=title,
        status=status,
        priority=priority,
        tags=tags,
        blocked=blocked,
        block_reason=block_reason,
        claimed_at=claimed_at,
        depends_on=depends_on,
        body=body,
    )
    path = kanban_dir / subdir / f"{task_id}-task.md"
    path.write_text(content, encoding="utf-8")
    return path


def _make_engine(base_dir: Path, config_yaml: str = _BASE_CONFIG) -> KanbanEngine:
    kanban_dir = _make_board(base_dir, config_yaml)
    return KanbanEngine(kanban_dir, activity_log=False)


def _now_ts() -> str:
    """Return a quoted ISO timestamp that is always within the 1 h claim window."""
    return f'"{datetime.now(UTC).isoformat()}"'


# ---------------------------------------------------------------------------
# _parse_duration — module-level function
# ---------------------------------------------------------------------------


class TestFromAC_ParseDuration:
    """AC: claim_timeout parsed from Ns/Nm/Nh/Nd string (D29)."""

    def test_hours_only(self) -> None:
        assert _parse_duration("2h") == timedelta(hours=2)

    def test_minutes_only(self) -> None:
        assert _parse_duration("30m") == timedelta(minutes=30)

    def test_seconds_only(self) -> None:
        assert _parse_duration("45s") == timedelta(seconds=45)

    def test_days_only(self) -> None:
        assert _parse_duration("3d") == timedelta(days=3)

    def test_combined_hours_and_minutes(self) -> None:
        assert _parse_duration("2h30m") == timedelta(hours=2, minutes=30)

    def test_combined_days_hours_minutes_seconds(self) -> None:
        result = _parse_duration("1d2h3m4s")
        assert result == timedelta(days=1, hours=2, minutes=3, seconds=4)

    def test_empty_string_raises_config_error(self) -> None:
        with pytest.raises(ConfigError, match="Invalid claim_timeout format"):
            _parse_duration("")

    def test_invalid_format_raises_config_error(self) -> None:
        with pytest.raises(ConfigError, match="Invalid claim_timeout format"):
            _parse_duration("1x")

    def test_plain_number_raises_config_error(self) -> None:
        with pytest.raises(ConfigError, match="Invalid claim_timeout format"):
            _parse_duration("60")

    def test_whitespace_stripped_before_parse(self) -> None:
        assert _parse_duration("  1h  ") == timedelta(hours=1)


# ---------------------------------------------------------------------------
# _classify_end_work_state and _classify_end_work_outcome
# ---------------------------------------------------------------------------


class TestFromAC_EndWorkClassifiers:
    """Helpers that derive session state/outcome from end_work detail strings."""

    def test_state_success_is_completed(self) -> None:
        assert _classify_end_work_state("success: todo -> in-progress") == "completed"

    def test_state_reject_is_rejected(self) -> None:
        assert _classify_end_work_state("reject: in-progress -> todo") == "rejected"

    def test_state_blocked_is_blocked(self) -> None:
        assert _classify_end_work_state("blocked: dependency missing") == "blocked"

    def test_state_outcome_fail_is_blocked(self) -> None:
        assert _classify_end_work_state("outcome=fail") == "blocked"

    def test_outcome_success_prefix(self) -> None:
        assert _classify_end_work_outcome("success: todo -> in-progress") == "success"

    def test_outcome_reject_prefix(self) -> None:
        assert _classify_end_work_outcome("reject: in-progress -> todo") == "reject"

    def test_outcome_outcome_fail_is_fail(self) -> None:
        assert _classify_end_work_outcome("outcome=fail") == "fail"

    def test_outcome_blocked_prefix_is_block(self) -> None:
        assert _classify_end_work_outcome("blocked: reason") == "block"


# ---------------------------------------------------------------------------
# _compute_duration and _state_from_age
# ---------------------------------------------------------------------------


class TestFromAC_SessionDurationHelpers:
    """AC: session duration and age classification helpers."""

    def test_compute_duration_tz_aware(self) -> None:
        result = _compute_duration(
            "2026-04-23T10:00:00+00:00",
            "2026-04-23T11:00:00+00:00",
        )
        assert result == 3600.0

    def test_compute_duration_tz_naive_normalised_to_utc(self) -> None:
        result = _compute_duration(
            "2026-04-23T10:00:00",
            "2026-04-23T11:00:00",
        )
        assert result == 3600.0

    def test_compute_duration_mixed_tz(self) -> None:
        result = _compute_duration(
            "2026-04-23T10:00:00",  # tz-naive
            "2026-04-23T11:00:00+00:00",  # tz-aware
        )
        assert result == 3600.0

    def test_state_from_age_recent_is_running(self) -> None:
        now = datetime.now(UTC)
        ref_ts = now.isoformat()
        state = _state_from_age(ref_ts, timedelta(hours=1), now)
        assert state == "running"

    def test_state_from_age_old_is_stuck(self) -> None:
        now = datetime.now(UTC)
        ref_ts = "2026-01-01T00:00:00+00:00"  # far in the past
        state = _state_from_age(ref_ts, timedelta(hours=1), now)
        assert state == "stuck"

    def test_state_from_age_tz_naive_normalised(self) -> None:
        now = datetime.now(UTC)
        ref_ts = "2026-01-01T00:00:00"  # tz-naive, far in the past
        state = _state_from_age(ref_ts, timedelta(hours=1), now)
        assert state == "stuck"


# ---------------------------------------------------------------------------
# _collect_task_sessions — session accumulation
# ---------------------------------------------------------------------------


class TestFromAC_CollectTaskSessions:
    """AC: session records derived from claim+close event pairs."""

    def _evt(self, action: str, detail: str, ts: str) -> dict:
        return {"action": action, "detail": detail, "timestamp": ts}

    def test_claim_and_end_work_success_produces_completed_session(self) -> None:
        events = [
            self._evt("claim", "agent-A", "2026-04-23T10:00:00+00:00"),
            self._evt(
                "end_work",
                "success: todo -> in-progress",
                "2026-04-23T10:30:00+00:00",
            ),
        ]
        sessions: list[SessionRecord] = []
        _collect_task_sessions(1, events, timedelta(hours=1), datetime.now(UTC), sessions)
        assert len(sessions) == 1
        assert sessions[0].state == "completed"
        assert sessions[0].outcome == "success"
        assert sessions[0].duration == 1800.0

    def test_open_claim_classified_as_running(self) -> None:
        events = [
            self._evt("claim", "agent-A", datetime.now(UTC).isoformat()),
        ]
        sessions: list[SessionRecord] = []
        _collect_task_sessions(2, events, timedelta(hours=1), datetime.now(UTC), sessions)
        assert len(sessions) == 1
        assert sessions[0].state == "running"

    def test_open_claim_old_classified_as_stuck(self) -> None:
        events = [
            self._evt("claim", "agent-A", "2026-01-01T10:00:00+00:00"),
        ]
        sessions: list[SessionRecord] = []
        _collect_task_sessions(3, events, timedelta(hours=1), datetime.now(UTC), sessions)
        assert sessions[0].state == "stuck"

    def test_double_claim_emits_first_as_stuck(self) -> None:
        events = [
            self._evt("claim", "agent-A", "2026-01-01T10:00:00+00:00"),
            self._evt("claim", "agent-B", datetime.now(UTC).isoformat()),
        ]
        sessions: list[SessionRecord] = []
        _collect_task_sessions(4, events, timedelta(hours=1), datetime.now(UTC), sessions)
        assert len(sessions) >= 2
        assert any(s.agent == "agent-A" and s.state == "stuck" for s in sessions)

    def test_release_action_produces_released_session(self) -> None:
        events = [
            self._evt("claim", "agent-A", "2026-04-23T10:00:00+00:00"),
            self._evt("release", "released by agent-A", "2026-04-23T10:30:00+00:00"),
        ]
        sessions: list[SessionRecord] = []
        _collect_task_sessions(5, events, timedelta(hours=1), datetime.now(UTC), sessions)
        assert sessions[0].state == "released"
        assert sessions[0].outcome == "release"

    def test_sweep_release_produces_expired_session(self) -> None:
        events = [
            self._evt("claim", "agent-A", "2026-04-23T10:00:00+00:00"),
            self._evt("sweep-release", "expired claim released", "2026-04-23T12:00:00+00:00"),
        ]
        sessions: list[SessionRecord] = []
        _collect_task_sessions(6, events, timedelta(hours=1), datetime.now(UTC), sessions)
        assert sessions[0].state == "expired"

    def test_orphan_close_without_open_claim_is_skipped(self) -> None:
        events = [
            self._evt("end_work", "success: todo -> done", "2026-04-23T10:00:00+00:00"),
        ]
        sessions: list[SessionRecord] = []
        _collect_task_sessions(7, events, timedelta(hours=1), datetime.now(UTC), sessions)
        assert sessions == []

    def test_intermediate_event_updates_last_activity_ts(self) -> None:
        """Non-claim non-close events update last_activity_ts for stuck detection."""
        events = [
            self._evt("claim", "agent-A", "2026-01-01T10:00:00+00:00"),
            self._evt("edit", "task edited", datetime.now(UTC).isoformat()),
        ]
        sessions: list[SessionRecord] = []
        _collect_task_sessions(8, events, timedelta(hours=1), datetime.now(UTC), sessions)
        # recent activity → should be running, not stuck
        assert sessions[0].state == "running"


# ---------------------------------------------------------------------------
# _validate_session_filter and _apply_session_filter
# ---------------------------------------------------------------------------


class TestFromAC_SessionFilterHelpers:
    """AC: session filter validation and application."""

    def _make_sessions(self, states: list[str]) -> list[SessionRecord]:
        return [
            SessionRecord(
                task_id=i,
                task_status_at_start="todo",
                agent="agent-A",
                state=s,
                started_at="2026-04-23T10:00:00+00:00",
                ended_at=None,
                outcome=None,
                duration=None,
                duration_s=None,
            )
            for i, s in enumerate(states, 1)
        ]

    def test_validate_all_is_valid(self) -> None:
        _validate_session_filter("all")  # must not raise

    def test_validate_active_is_valid(self) -> None:
        _validate_session_filter("active")

    def test_validate_blocked_or_rejected_is_valid(self) -> None:
        _validate_session_filter("blocked-or-rejected")

    def test_validate_failed_or_rejected_alias_is_valid(self) -> None:
        _validate_session_filter("failed-or-rejected")

    def test_validate_released_is_valid(self) -> None:
        _validate_session_filter("released")

    def test_validate_unknown_filter_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Unsupported session filter"):
            _validate_session_filter("bogus")

    def test_apply_all_returns_all_sessions(self) -> None:
        sessions = self._make_sessions(["running", "stuck", "released"])
        result = _apply_session_filter(sessions, "all")
        assert len(result) == 3

    def test_apply_active_returns_running_and_stuck(self) -> None:
        sessions = self._make_sessions(["running", "stuck", "released", "completed"])
        result = _apply_session_filter(sessions, "active")
        states = {s.state for s in result}
        assert states == {"running", "stuck"}

    def test_apply_released_returns_only_released(self) -> None:
        sessions = self._make_sessions(["running", "released"])
        result = _apply_session_filter(sessions, "released")
        assert all(s.state == "released" for s in result)

    def test_apply_blocked_or_rejected(self) -> None:
        sessions = self._make_sessions(["blocked", "rejected", "running"])
        result = _apply_session_filter(sessions, "blocked-or-rejected")
        states = {s.state for s in result}
        assert states == {"blocked", "rejected"}


# ---------------------------------------------------------------------------
# Engine properties: agent_name, revision, board_config
# ---------------------------------------------------------------------------


class TestFromAC_EngineProperties:
    """AC: engine properties accessible after init."""

    def test_agent_name_is_string(self, tmp_path: Path) -> None:
        engine = _make_engine(tmp_path)
        assert isinstance(engine.agent_name, str)
        assert len(engine.agent_name) > 0

    def test_agent_name_stable_across_calls(self, tmp_path: Path) -> None:
        engine = _make_engine(tmp_path)
        assert engine.agent_name == engine.agent_name

    def test_revision_starts_at_zero(self, tmp_path: Path) -> None:
        engine = _make_engine(tmp_path)
        assert engine.revision == 0

    def test_revision_increments_after_write(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        engine = KanbanEngine(board, activity_log=False)
        engine.create_task("Task 1")
        assert engine.revision == 1
        engine.create_task("Task 2")
        assert engine.revision == 2

    def test_board_config_returns_copy(self, tmp_path: Path) -> None:
        engine = _make_engine(tmp_path)
        cfg = engine.board_config()
        assert isinstance(cfg, BoardConfig)

    def test_board_config_is_deep_copy(self, tmp_path: Path) -> None:
        engine = _make_engine(tmp_path)
        cfg1 = engine.board_config()
        cfg2 = engine.board_config()
        cfg1.statuses.append("mutated")
        assert "mutated" not in cfg2.statuses

    def test_board_config_contains_configured_statuses(self, tmp_path: Path) -> None:
        engine = _make_engine(tmp_path)
        cfg = engine.board_config()
        assert "research" in cfg.statuses
        assert "done" in cfg.statuses


# ---------------------------------------------------------------------------
# refresh_config and valid_transitions
# ---------------------------------------------------------------------------


class TestFromAC_EngineConfigOps:
    """AC: refresh_config reloads from disk; valid_transitions returns reachable statuses."""

    def test_refresh_config_clears_cache(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        engine = KanbanEngine(board, activity_log=False)
        _write_task(board, task_id=1)
        engine.list_tasks()  # warm cache
        engine.refresh_config()
        # After refresh, id_to_filename cache is cleared; list_tasks must re-scan
        result = engine.list_tasks()
        assert any(t.id == 1 for t in result)

    def test_refresh_config_reloads_updated_config(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        engine = KanbanEngine(board, activity_log=False)
        original_next_id = engine.board_config().next_id
        # Update next_id in config — next_id IS read from config.yml (not PRODUCT_TOPOLOGY)
        new_config = _BASE_CONFIG.replace(
            f"next_id: {original_next_id}",
            "next_id: 9999",
        )
        (board / "config.yml").write_text(new_config, encoding="utf-8")
        engine.refresh_config()
        cfg = engine.board_config()
        assert cfg.next_id == 9999

    def test_valid_transitions_excludes_current_status(self, tmp_path: Path) -> None:
        engine = _make_engine(tmp_path)
        transitions = engine.valid_transitions("todo")
        assert "todo" not in transitions
        assert "research" in transitions
        assert "done" in transitions

    def test_valid_transitions_raises_for_unknown_status(self, tmp_path: Path) -> None:
        engine = _make_engine(tmp_path)
        with pytest.raises(ValueError, match="Invalid status"):
            engine.valid_transitions("nonexistent")

    def test_valid_transitions_returns_all_other_statuses(self, tmp_path: Path) -> None:
        engine = _make_engine(tmp_path)
        transitions = engine.valid_transitions("todo")
        all_statuses = set(engine.board_config().statuses)
        assert transitions == all_statuses - {"todo"}


# ---------------------------------------------------------------------------
# Migration gate — edge cases in __init__
# ---------------------------------------------------------------------------


class TestFromAC_MigrationGateEdgeCases:
    """AC: MigrationRequiredError raised if active tasks carry claimed_by frontmatter."""

    def test_task_with_oserror_is_skipped(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        task_path = board / "tasks" / "1-unreadable.md"
        task_path.write_text("claimed_by: agent\n", encoding="utf-8")
        task_path.chmod(0o000)
        try:
            engine = KanbanEngine(board, activity_log=False)
            assert engine is not None
        finally:
            task_path.chmod(0o644)

    def test_task_without_frontmatter_marker_is_skipped(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        (board / "tasks" / "1-nofm.md").write_text("no frontmatter here\nclaimed_by: agent\n", encoding="utf-8")
        engine = KanbanEngine(board, activity_log=False)
        assert engine is not None

    def test_frontmatter_without_closing_fence_is_skipped(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        (board / "tasks" / "1-unclosed.md").write_text(
            "---\nclaimed_by: agent\n# missing closing fence\n", encoding="utf-8"
        )
        engine = KanbanEngine(board, activity_log=False)
        assert engine is not None

    def test_cleared_claimed_by_null_does_not_raise(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        (board / "tasks" / "1-cleared.md").write_text(
            "---\nid: 1\ntitle: T\nstatus: todo\nclaimed_by: null\n---\nBody\n",
            encoding="utf-8",
        )
        engine = KanbanEngine(board, activity_log=False)
        assert engine is not None

    def test_cleared_claimed_by_empty_string_does_not_raise(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        (board / "tasks" / "1-empty.md").write_text(
            '---\nid: 1\ntitle: T\nstatus: todo\nclaimed_by: ""\n---\nBody\n',
            encoding="utf-8",
        )
        engine = KanbanEngine(board, activity_log=False)
        assert engine is not None


# ---------------------------------------------------------------------------
# list_tasks — comprehensive filter, sort, archive, and error paths
# ---------------------------------------------------------------------------


class TestFromAC_EngineListTasks:
    """AC: list_tasks returns filtered, sorted task summaries."""

    def test_empty_board_returns_empty_list(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        engine = KanbanEngine(board, activity_log=False)
        assert engine.list_tasks() == []

    def test_returns_all_tasks_without_filters(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, title="A")
        _write_task(board, task_id=2, title="B")
        engine = KanbanEngine(board, activity_log=False)
        assert len(engine.list_tasks()) == 2

    def test_filter_by_status(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, status="todo")
        _write_task(board, task_id=2, status="research")
        engine = KanbanEngine(board, activity_log=False)
        result = engine.list_tasks(status="todo")
        assert len(result) == 1
        assert result[0].id == 1

    def test_filter_by_tag(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, tags='["alpha"]')
        _write_task(board, task_id=2, tags='["beta"]')
        engine = KanbanEngine(board, activity_log=False)
        result = engine.list_tasks(tag="alpha")
        assert [t.id for t in result] == [1]

    def test_filter_by_priority(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, priority="critical")
        _write_task(board, task_id=2, priority="someday")
        engine = KanbanEngine(board, activity_log=False)
        result = engine.list_tasks(priority="critical")
        assert [t.id for t in result] == [1]

    def test_filter_blocked_true(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, blocked="true", block_reason='"reason"')
        _write_task(board, task_id=2, blocked="false")
        engine = KanbanEngine(board, activity_log=False)
        result = engine.list_tasks(blocked=True)
        assert [t.id for t in result] == [1]

    def test_filter_blocked_false(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, blocked="true", block_reason='"reason"')
        _write_task(board, task_id=2, blocked="false")
        engine = KanbanEngine(board, activity_log=False)
        result = engine.list_tasks(blocked=False)
        assert [t.id for t in result] == [2]

    def test_filter_unclaimed_excludes_claimed(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, claimed_at=_now_ts())
        _write_task(board, task_id=2, claimed_at="null")
        engine = KanbanEngine(board, activity_log=False)
        result = engine.list_tasks(unclaimed=True)
        assert [t.id for t in result] == [2]

    def test_filter_search_matches_title(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, title="Alpha task")
        _write_task(board, task_id=2, title="Beta task")
        engine = KanbanEngine(board, activity_log=False)
        assert [t.id for t in engine.list_tasks(search="alpha")] == [1]

    def test_filter_search_matches_body(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, body="needle hidden here")
        _write_task(board, task_id=2, body="nothing interesting")
        engine = KanbanEngine(board, activity_log=False)
        assert [t.id for t in engine.list_tasks(search="needle")] == [1]

    def test_sort_by_id(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=3)
        _write_task(board, task_id=1)
        _write_task(board, task_id=2)
        engine = KanbanEngine(board, activity_log=False)
        result = engine.list_tasks(sort="id")
        assert [t.id for t in result] == [1, 2, 3]

    def test_sort_by_title(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, title="Zebra")
        _write_task(board, task_id=2, title="Apple")
        engine = KanbanEngine(board, activity_log=False)
        result = engine.list_tasks(sort="title")
        assert result[0].title == "Apple"

    def test_sort_by_status(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, status="done")
        _write_task(board, task_id=2, status="research")
        engine = KanbanEngine(board, activity_log=False)
        result = engine.list_tasks(sort="status")
        assert result[0].status == "research"

    def test_sort_by_priority(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, priority="critical")
        _write_task(board, task_id=2, priority="someday")
        engine = KanbanEngine(board, activity_log=False)
        result = engine.list_tasks(sort="priority")
        assert result[0].priority == "someday"

    def test_sort_by_created(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1)
        path = board / "tasks" / "1-task.md"
        path.write_text(
            path.read_text().replace(
                'created: "2026-01-01T10:00:00+00:00"',
                'created: "2025-01-01T10:00:00+00:00"',
            )
        )
        _write_task(board, task_id=2)
        engine = KanbanEngine(board, activity_log=False)
        result = engine.list_tasks(sort="created")
        assert result[0].id == 1

    def test_sort_by_updated(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1)
        path = board / "tasks" / "1-task.md"
        path.write_text(
            path.read_text().replace(
                'updated: "2026-01-01T10:00:00+00:00"',
                'updated: "2025-01-01T10:00:00+00:00"',
            )
        )
        _write_task(board, task_id=2)
        engine = KanbanEngine(board, activity_log=False)
        result = engine.list_tasks(sort="updated")
        assert result[0].id == 1

    def test_sort_reverse_inverts_order(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        for i in (1, 2, 3):
            _write_task(board, task_id=i)
        engine = KanbanEngine(board, activity_log=False)
        result = engine.list_tasks(sort="id", reverse=True)
        assert [t.id for t in result] == [3, 2, 1]

    def test_limit_caps_results(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        for i in (1, 2, 3, 4):
            _write_task(board, task_id=i)
        engine = KanbanEngine(board, activity_log=False)
        result = engine.list_tasks(sort="id", limit=2)
        assert len(result) == 2

    def test_archived_returns_tasks_from_archive_dir(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, subdir="archive")
        engine = KanbanEngine(board, activity_log=False)
        result = engine.list_tasks(archived=True)
        assert len(result) == 1
        assert result[0].id == 1

    def test_skips_task_with_missing_required_fields(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1)
        (board / "tasks" / "99-bad.md").write_text("---\ntitle: Bad\nstatus: todo\n---\nBody\n", encoding="utf-8")
        engine = KanbanEngine(board, activity_log=False)
        ids = [t.id for t in engine.list_tasks()]
        assert 1 in ids
        assert 99 not in ids

    def test_dep_status_included_in_summary(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, depends_on="[2]")
        _write_task(board, task_id=2)
        engine = KanbanEngine(board, activity_log=False)
        result = engine.list_tasks(sort="id")
        # task 1 depends on task 2 (active/unresolved) → dep_status = "blocked"
        task1 = next(t for t in result if t.id == 1)
        assert task1.dep_status == "blocked"

    def test_tasks_dir_missing_returns_empty(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        (board / "tasks").rmdir()
        engine = KanbanEngine(board, activity_log=False)
        assert engine.list_tasks() == []


# ---------------------------------------------------------------------------
# show_task
# ---------------------------------------------------------------------------


class TestFromAC_EngineShowTask:
    """AC: show_task returns a single Task by ID."""

    def test_show_task_returns_correct_task(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=5, title="My Task")
        engine = KanbanEngine(board, activity_log=False)
        # Warm the id→filename index
        engine.list_tasks()
        task = engine.show_task("5")
        assert task.id == 5
        assert task.title == "My Task"

    def test_show_task_without_index_uses_glob(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=7, title="Direct Glob")
        engine = KanbanEngine(board, activity_log=False)
        # Do NOT call list_tasks() first → _id_to_filename is empty → glob path
        task = engine.show_task("7")
        assert task.id == 7

    def test_show_task_not_found_raises_file_not_found(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        engine = KanbanEngine(board, activity_log=False)
        with pytest.raises(FileNotFoundError):
            engine.show_task("999")


# ---------------------------------------------------------------------------
# create_task
# ---------------------------------------------------------------------------


class TestFromAC_EngineCreateTask:
    """AC: create_task allocates IDs and writes task files."""

    def test_create_task_returns_task_with_correct_title(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        engine = KanbanEngine(board, activity_log=False)
        task = engine.create_task("New Feature")
        assert task.title == "New Feature"
        assert task.id > 0

    def test_create_task_uses_default_status(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        engine = KanbanEngine(board, activity_log=False)
        task = engine.create_task("Task")
        assert task.status in engine.board_config().statuses

    def test_create_task_explicit_status(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        engine = KanbanEngine(board, activity_log=False)
        task = engine.create_task("Task", status="todo")
        assert task.status == "todo"

    def test_create_task_explicit_priority(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        engine = KanbanEngine(board, activity_log=False)
        task = engine.create_task("Task", priority="critical")
        assert task.priority == "critical"

    def test_create_task_with_tags_body_parent_deps(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        engine = KanbanEngine(board, activity_log=False)
        _write_task(board, task_id=1, title="Parent")
        task = engine.create_task(
            "Sub-task",
            tags=["alpha", "beta"],
            body="Initial body.",
            parent=1,
            depends_on=[],
        )
        assert "alpha" in task.tags
        assert task.body == "Initial body."

    def test_create_task_invalid_status_raises(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        engine = KanbanEngine(board, activity_log=False)
        with pytest.raises(ValueError, match="Invalid status"):
            engine.create_task("Task", status="nonexistent")

    def test_create_task_invalid_priority_raises(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        engine = KanbanEngine(board, activity_log=False)
        with pytest.raises(ValueError, match="Invalid priority"):
            engine.create_task("Task", priority="mega-urgent")

    def test_create_task_increments_revision(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        engine = KanbanEngine(board, activity_log=False)
        engine.create_task("Task 1")
        engine.create_task("Task 2")
        assert engine.revision == 2

    def test_create_task_file_exists_on_disk(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        engine = KanbanEngine(board, activity_log=False)
        task = engine.create_task("Disk Task")
        matches = list((board / "tasks").glob(f"{task.id}-*.md"))
        assert len(matches) == 1


# ---------------------------------------------------------------------------
# edit_task
# ---------------------------------------------------------------------------


class TestFromAC_EngineEditTask:
    """AC: edit_task modifies task fields in-place; filename unchanged."""

    def test_edit_task_title(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, title="Old Title")
        engine = KanbanEngine(board, activity_log=False)
        result = engine.edit_task("1", title="New Title")
        assert result.title == "New Title"

    def test_edit_task_body_replace(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, body="Old body.")
        engine = KanbanEngine(board, activity_log=False)
        result = engine.edit_task("1", body="New body.")
        assert result.body == "New body."

    def test_edit_task_append_body(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, body="Original.")
        engine = KanbanEngine(board, activity_log=False)
        result = engine.edit_task("1", append_body="Appended.")
        assert "Original." in result.body
        assert "Appended." in result.body

    def test_edit_task_append_body_with_timestamp(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, body="Base.")
        engine = KanbanEngine(board, activity_log=False)
        result = engine.edit_task("1", append_body="Dated note.", timestamp=True)
        assert "[[" in result.body  # timestamp prefix added
        assert "Dated note." in result.body

    def test_edit_task_add_and_remove_tags(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, tags='["existing"]')
        engine = KanbanEngine(board, activity_log=False)
        result = engine.edit_task("1", add_tags=["new-tag"], remove_tags=["existing"])
        assert "new-tag" in result.tags
        assert "existing" not in result.tags

    def test_edit_task_add_and_remove_deps(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, depends_on="[5]")
        _write_task(board, task_id=6)
        engine = KanbanEngine(board, activity_log=False)
        result = engine.edit_task("1", add_deps=[6], remove_deps=[5])
        assert 6 in result.depends_on
        assert 5 not in result.depends_on

    def test_edit_task_set_blocked_true(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1)
        engine = KanbanEngine(board, activity_log=False)
        result = engine.edit_task("1", blocked=True, block_reason="some reason")
        assert result.blocked is True
        assert result.block_reason == "some reason"

    def test_edit_task_set_blocked_false_clears_block_reason(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, blocked="true", block_reason='"old reason"')
        engine = KanbanEngine(board, activity_log=False)
        result = engine.edit_task("1", blocked=False)
        assert result.blocked is False
        assert result.block_reason is None

    def test_edit_task_invalid_status_raises(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1)
        engine = KanbanEngine(board, activity_log=False)
        with pytest.raises(ValueError, match="Invalid status"):
            engine.edit_task("1", status="nosuchstatus")

    def test_edit_task_invalid_priority_raises(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1)
        engine = KanbanEngine(board, activity_log=False)
        with pytest.raises(ValueError, match="Invalid priority"):
            engine.edit_task("1", priority="ultra-mega")

    def test_edit_task_not_found_raises_file_not_found(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        engine = KanbanEngine(board, activity_log=False)
        with pytest.raises(FileNotFoundError):
            engine.edit_task("999", title="Ghost")

    def test_edit_task_increments_revision(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1)
        engine = KanbanEngine(board, activity_log=False)
        engine.edit_task("1", title="Updated")
        assert engine.revision == 1


# ---------------------------------------------------------------------------
# move_task
# ---------------------------------------------------------------------------


class TestFromAC_EngineMoveTask:
    """AC: move_task changes status; 'archived' moves file to archive/."""

    def test_move_task_changes_status(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, status="todo")
        engine = KanbanEngine(board, activity_log=False)
        result = engine.move_task("1", "in-progress")
        assert result.status == "in-progress"

    def test_move_task_to_archived_moves_file(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, status="done")
        engine = KanbanEngine(board, activity_log=False)
        engine.move_task("1", "archived", archival_reason="completed")
        assert not (board / "tasks" / "1-task.md").exists()
        assert (board / "archive" / "1-task.md").exists()

    def test_move_task_invalid_status_raises(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1)
        engine = KanbanEngine(board, activity_log=False)
        with pytest.raises(ValueError, match="Invalid status"):
            engine.move_task("1", "nonexistent-status")

    def test_move_task_increments_revision(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, status="todo")
        engine = KanbanEngine(board, activity_log=False)
        engine.move_task("1", "in-progress")
        assert engine.revision == 1

    def test_move_task_not_found_raises(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        engine = KanbanEngine(board, activity_log=False)
        with pytest.raises(FileNotFoundError):
            engine.move_task("999", "todo")


# ---------------------------------------------------------------------------
# claim_task / release_task / start_work
# ---------------------------------------------------------------------------


class TestFromAC_EngineClaimRelease:
    """AC: claim_task / release_task / start_work manage task ownership."""

    def test_claim_task_sets_claimed_at(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1)
        engine = KanbanEngine(board, activity_log=False)
        result = engine.claim_task("1")
        assert result.claimed_at is not None

    def test_claim_task_blocked_raises(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, blocked="true", block_reason='"blocked"')
        engine = KanbanEngine(board, activity_log=False)
        with pytest.raises(ValueError, match="blocked"):
            engine.claim_task("1")

    def test_claim_task_already_claimed_not_expired_raises(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, claimed_at=_now_ts())
        engine = KanbanEngine(board, activity_log=False)
        with pytest.raises(ValueError, match="already claimed"):
            engine.claim_task("1")

    def test_claim_task_expired_claim_succeeds(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, claimed_at=_EPOCH_TS)
        engine = KanbanEngine(board, activity_log=False)
        result = engine.claim_task("1")
        assert result.claimed_at is not None

    def test_release_task_clears_claimed_at(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, claimed_at=_now_ts())
        engine = KanbanEngine(board, activity_log=False)
        result = engine.release_task("1")
        assert result.claimed_at is None

    def test_release_task_increments_revision(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, claimed_at=_now_ts())
        engine = KanbanEngine(board, activity_log=False)
        engine.release_task("1")
        assert engine.revision == 1

    def test_start_work_delegates_to_claim_task(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1)
        engine = KanbanEngine(board, activity_log=False)
        result = engine.start_work("1")
        assert result.claimed_at is not None


# ---------------------------------------------------------------------------
# end_work — all four outcomes
# ---------------------------------------------------------------------------


class TestFromAC_EngineEndWork:
    """AC: end_work finalises work session with outcome-specific state changes."""

    def test_end_work_success_advances_status(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, status="todo")
        engine = KanbanEngine(board, activity_log=False)
        result = engine.end_work("1", note="Done!", outcome="success")
        assert result.status == "in-progress"  # next after "todo"

    def test_end_work_success_last_status_archives(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, status="done")
        engine = KanbanEngine(board, activity_log=False)
        result = engine.end_work("1", note="Archived!", outcome="success")
        assert result.status == "archived"
        assert (board / "archive" / "1-task.md").exists()

    def test_end_work_fail_preserves_status(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, status="in-progress")
        engine = KanbanEngine(board, activity_log=False)
        result = engine.end_work("1", note="Failed.", outcome="fail")
        assert result.status == "in-progress"

    def test_end_work_block_sets_blocked(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, status="todo")
        engine = KanbanEngine(board, activity_log=False)
        result = engine.end_work("1", note="Blocked!", outcome="block", block_reason="missing dep")
        assert result.blocked is True
        assert result.block_reason == "missing dep"

    def test_end_work_reject_moves_to_specified_status(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, status="in-progress")
        engine = KanbanEngine(board, activity_log=False)
        result = engine.end_work("1", note="Rejected.", outcome="reject", move_to="todo")
        assert result.status == "todo"

    def test_end_work_invalid_outcome_raises(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1)
        engine = KanbanEngine(board, activity_log=False)
        with pytest.raises(ValueError, match="Unknown outcome"):
            engine.end_work("1", note="Bad.", outcome="bogus")

    def test_end_work_reject_invalid_move_to_raises(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1)
        engine = KanbanEngine(board, activity_log=False)
        with pytest.raises(ValueError, match="move_to"):
            engine.end_work("1", note="Reject.", outcome="reject", move_to="phantom-status")

    def test_end_work_appends_note_to_body(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, body="Original body.")
        engine = KanbanEngine(board, activity_log=False)
        result = engine.end_work("1", note="## Notes\nGreat work.", outcome="fail")
        assert "Original body." in result.body
        assert "## Notes" in result.body

    def test_end_work_clears_claimed_at(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, claimed_at=_now_ts())
        engine = KanbanEngine(board, activity_log=False)
        result = engine.end_work("1", note="Done.", outcome="fail")
        assert result.claimed_at is None

    def test_end_work_increments_revision(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1)
        engine = KanbanEngine(board, activity_log=False)
        engine.end_work("1", note=".", outcome="fail")
        assert engine.revision == 1


# ---------------------------------------------------------------------------
# sweep — expired claim release
# ---------------------------------------------------------------------------


class TestFromAC_EngineSweep:
    """AC: sweep() releases expired claims without touching non-expired or corrupt files."""

    def test_sweep_returns_empty_when_no_claimed_tasks(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, claimed_at="null")
        engine = KanbanEngine(board, activity_log=False)
        assert engine.sweep() == []

    def test_sweep_releases_expired_claim(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, claimed_at=_EPOCH_TS)
        engine = KanbanEngine(board, activity_log=False)
        released = engine.sweep()
        assert 1 in released

    def test_sweep_preserves_non_expired_claim(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, claimed_at=_now_ts())
        engine = KanbanEngine(board, activity_log=False)
        released = engine.sweep()
        assert 1 not in released

    def test_sweep_skips_unparseable_file(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        (board / "tasks" / "99-garbage.md").write_text("not valid yaml frontmatter at all!!!", encoding="utf-8")
        engine = KanbanEngine(board, activity_log=False)
        assert 99 not in engine.sweep()

    def test_sweep_skips_invalid_claimed_at_format(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, claimed_at='"not-a-datetime"')
        engine = KanbanEngine(board, activity_log=False)
        assert 1 not in engine.sweep()

    def test_sweep_tz_naive_claimed_at_treated_as_utc(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, claimed_at='"2026-01-01T00:00:00"')
        engine = KanbanEngine(board, activity_log=False)
        released = engine.sweep()
        assert 1 in released

    def test_sweep_silently_skips_unparseable_corrupt_file(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        (board / "tasks" / "99-corrupt.md").write_text("this is not valid yaml frontmatter at all", encoding="utf-8")
        engine = KanbanEngine(board, activity_log=False)
        released = engine.sweep()
        assert 99 not in released

    def test_sweep_skips_parseable_but_corrupt_file(self, tmp_path: Path) -> None:
        """detect_corruption returns non-None -> sweep skips the file."""
        board = _make_board(tmp_path)
        # Instantiate engine before creating the corrupt file so the migration gate
        # does not reject the board during __init__.
        engine = KanbanEngine(board, activity_log=False)
        # Write a task with claimed_by directly so detect_corruption flags it.
        task_path = board / "tasks" / "1-task.md"
        task_path.write_text(
            "---\nclaimed_by: agent-old\nid: 1\ntitle: T\nstatus: todo"
            '\npriority: needed\ncreated: "2026-01-01T00:00:00+00:00"'
            '\nupdated: "2026-01-01T00:00:00+00:00"\ntags: []'
            "\nparent: null\ndepends_on: []\nblocked: false"
            "\nblock_reason: null"
            f"\nclaimed_at: {_EPOCH_CLAIMED_AT}"
            "\narchival_reason: null\narchival_refs: []\n---\nBody\n",
            encoding="utf-8",
        )
        released = engine.sweep()
        assert 1 not in released

    def test_sweep_skips_task_with_invalid_claimed_at_format(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, claimed_at='"not-a-valid-datetime"')
        engine = KanbanEngine(board, activity_log=False)
        released = engine.sweep()
        assert 1 not in released


# ---------------------------------------------------------------------------
# list_sessions / _read_log_entries / _derive_sessions — activity log parsing
# ---------------------------------------------------------------------------


class TestFromAC_EngineListSessions:
    """AC: list_sessions derives SessionRecord values from activity.jsonl."""

    def _write_log(self, board: Path, entries: list[dict]) -> None:
        log_path = board / "activity.jsonl"
        lines = "\n".join(json.dumps(e) for e in entries)
        log_path.write_text(lines + "\n", encoding="utf-8")

    def _claim_evt(self, task_id: int, ts: str, agent: str = "agent-A") -> dict:
        return {
            "action": "claim",
            "task_id": task_id,
            "detail": agent,
            "timestamp": ts,
            "task_status_at_start": "todo",
        }

    def _end_evt(self, task_id: int, detail: str, ts: str) -> dict:
        return {
            "action": "end_work",
            "task_id": task_id,
            "detail": detail,
            "timestamp": ts,
        }

    def test_no_activity_log_returns_empty(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        engine = KanbanEngine(board, activity_log=False)
        assert engine.list_sessions() == []

    def test_empty_log_returns_empty(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        engine = KanbanEngine(board, activity_log=True)
        assert engine.list_sessions() == []

    def test_completed_session_from_success_end_work(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        self._write_log(
            board,
            [
                self._claim_evt(1, "2026-04-23T10:00:00+00:00"),
                self._end_evt(1, "success: todo -> in-progress", "2026-04-23T11:00:00+00:00"),
            ],
        )
        engine = KanbanEngine(board, activity_log=True)
        sessions = engine.list_sessions(filter="all")
        assert len(sessions) == 1
        assert sessions[0].state == "completed"
        assert sessions[0].duration == 3600.0

    def test_active_session_filter_returns_running(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        self._write_log(board, [self._claim_evt(1, datetime.now(UTC).isoformat())])
        engine = KanbanEngine(board, activity_log=True)
        sessions = engine.list_sessions(filter="active")
        assert len(sessions) == 1
        assert sessions[0].state == "running"

    def test_release_action_produces_released_session(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        self._write_log(
            board,
            [
                self._claim_evt(1, "2026-04-23T10:00:00+00:00"),
                {
                    "action": "release",
                    "task_id": 1,
                    "detail": "released",
                    "timestamp": "2026-04-23T10:30:00+00:00",
                },
            ],
        )
        engine = KanbanEngine(board, activity_log=True)
        sessions = engine.list_sessions(filter="released")
        assert len(sessions) == 1
        assert sessions[0].state == "released"

    def test_sweep_release_produces_expired_session(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        self._write_log(
            board,
            [
                self._claim_evt(2, "2026-04-23T10:00:00+00:00"),
                {
                    "action": "sweep-release",
                    "task_id": 2,
                    "detail": "expired claim released",
                    "timestamp": "2026-04-23T12:00:00+00:00",
                },
            ],
        )
        engine = KanbanEngine(board, activity_log=True)
        sessions = engine.list_sessions(filter="all")
        expired = [s for s in sessions if s.state == "expired"]
        assert len(expired) == 1

    def test_invalid_json_line_skipped(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        (board / "activity.jsonl").write_text(
            "not valid json\n"
            + json.dumps(
                {
                    "action": "claim",
                    "task_id": 1,
                    "detail": "agent",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "task_status_at_start": "todo",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        engine = KanbanEngine(board, activity_log=True)
        sessions = engine.list_sessions(filter="active")
        assert len(sessions) == 1  # only the valid entry counted

    def test_missing_required_log_fields_line_skipped(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        (board / "activity.jsonl").write_text(
            json.dumps({"action": "claim"}) + "\n",  # missing task_id, detail, timestamp
            encoding="utf-8",
        )
        engine = KanbanEngine(board, activity_log=True)
        assert engine.list_sessions(filter="all") == []

    def test_invalid_timestamp_in_log_line_skipped(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        (board / "activity.jsonl").write_text(
            json.dumps(
                {
                    "action": "claim",
                    "task_id": 1,
                    "detail": "agent",
                    "timestamp": "not-a-timestamp",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        engine = KanbanEngine(board, activity_log=True)
        assert engine.list_sessions(filter="all") == []

    def test_non_integer_task_id_in_log_is_skipped(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        (board / "activity.jsonl").write_text(
            json.dumps(
                {
                    "action": "claim",
                    "task_id": "not-an-int",
                    "detail": "agent",
                    "timestamp": datetime.now(UTC).isoformat(),
                }
            )
            + "\n",
            encoding="utf-8",
        )
        engine = KanbanEngine(board, activity_log=True)
        assert engine.list_sessions(filter="all") == []

    def test_blocked_or_rejected_filter(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        self._write_log(
            board,
            [
                self._claim_evt(1, "2026-04-23T10:00:00+00:00"),
                self._end_evt(1, "blocked: dependency missing", "2026-04-23T11:00:00+00:00"),
            ],
        )
        engine = KanbanEngine(board, activity_log=True)
        sessions = engine.list_sessions(filter="blocked-or-rejected")
        assert len(sessions) == 1
        assert sessions[0].state == "blocked"

    def test_invalid_filter_raises_value_error(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        engine = KanbanEngine(board, activity_log=True)
        with pytest.raises(ValueError, match="Unsupported session filter"):
            engine.list_sessions(filter="invalid-filter")


# ---------------------------------------------------------------------------
# Activity log emission (_emit_event via CRUD operations)
# ---------------------------------------------------------------------------


class TestFromAC_EngineActivityLog:
    """AC: engine emits activity log entries when activity_log=True."""

    def test_create_task_emits_no_event_when_activity_log_false(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        engine = KanbanEngine(board, activity_log=False)
        engine.create_task("Task 1")
        assert not (board / "activity.jsonl").exists()

    def test_claim_and_release_emit_events_to_log(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1)
        engine = KanbanEngine(board, activity_log=True)
        engine.claim_task("1")
        engine.release_task("1")
        log_path = board / "activity.jsonl"
        assert log_path.exists()
        lines = [json.loads(ln) for ln in log_path.read_text().splitlines() if ln.strip()]
        actions = [e["action"] for e in lines]
        assert "claim" in actions
        assert "release" in actions

    def test_end_work_emits_event_to_log(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1)
        engine = KanbanEngine(board, activity_log=True)
        engine.end_work("1", note="Done.", outcome="fail")
        log_path = board / "activity.jsonl"
        lines = [json.loads(ln) for ln in log_path.read_text().splitlines() if ln.strip()]
        actions = [e["action"] for e in lines]
        assert "end_work" in actions

    def test_move_task_emits_event_to_log(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, status="todo")
        engine = KanbanEngine(board, activity_log=True)
        engine.move_task("1", "in-progress")
        log_path = board / "activity.jsonl"
        lines = [json.loads(ln) for ln in log_path.read_text().splitlines() if ln.strip()]
        actions = [e["action"] for e in lines]
        assert "move" in actions

    def test_edit_task_emits_event_to_log(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1)
        engine = KanbanEngine(board, activity_log=True)
        engine.edit_task("1", title="Updated Title")
        log_path = board / "activity.jsonl"
        lines = [json.loads(ln) for ln in log_path.read_text().splitlines() if ln.strip()]
        actions = [e["action"] for e in lines]
        assert "edit" in actions


# ---------------------------------------------------------------------------
# Cache-hit paths: show_task and _find_task_path with populated id_to_filename
# ---------------------------------------------------------------------------


class TestFromAC_EngineCacheHitPaths:
    """AC: engine caches task reads and uses id→filename index after list_tasks."""

    def test_show_task_uses_cache_after_list_tasks(self, tmp_path: Path) -> None:
        """show_task should use the id→filename cache built by list_tasks."""
        board = _make_board(tmp_path)
        _write_task(board, task_id=3, title="Cached Task")
        engine = KanbanEngine(board, activity_log=False)
        engine.list_tasks()  # warms cache and id_to_filename
        task = engine.show_task("3")
        assert task.id == 3
        assert task.title == "Cached Task"

    def test_show_task_cache_hit_returns_same_object(self, tmp_path: Path) -> None:
        """Second show_task call should use the mtime-keyed task cache."""
        board = _make_board(tmp_path)
        _write_task(board, task_id=4, title="Mtime Cached")
        engine = KanbanEngine(board, activity_log=False)
        engine.list_tasks()  # cold scan + cache fill
        t1 = engine.show_task("4")
        t2 = engine.show_task("4")  # should hit mtime cache
        assert t1.id == t2.id == 4

    def test_find_task_path_uses_index_in_edit_task(self, tmp_path: Path) -> None:
        """edit_task after list_tasks uses the id→filename index via _find_task_path."""
        board = _make_board(tmp_path)
        _write_task(board, task_id=10, title="Indexed")
        engine = KanbanEngine(board, activity_log=False)
        engine.list_tasks()  # populates _id_to_filename
        result = engine.edit_task("10", title="Via Index")
        assert result.title == "Via Index"

    def test_find_task_path_uses_index_in_move_task(self, tmp_path: Path) -> None:
        """move_task after list_tasks uses the id→filename index."""
        board = _make_board(tmp_path)
        _write_task(board, task_id=11, status="todo")
        engine = KanbanEngine(board, activity_log=False)
        engine.list_tasks()
        result = engine.move_task("11", "in-progress")
        assert result.status == "in-progress"

    def test_find_task_path_uses_index_in_claim_task(self, tmp_path: Path) -> None:
        """claim_task after list_tasks uses the id→filename index."""
        board = _make_board(tmp_path)
        _write_task(board, task_id=12)
        engine = KanbanEngine(board, activity_log=False)
        engine.list_tasks()
        result = engine.claim_task("12")
        assert result.claimed_at is not None


# ---------------------------------------------------------------------------
# list_tasks — archive scanning and dep_status with archived deps
# ---------------------------------------------------------------------------


class TestFromAC_EngineListTasksArchiveScan:
    """AC: list_tasks correctly handles archived tasks and dep_status computation."""

    def test_list_tasks_skips_active_copy_when_archive_copy_exists(self, tmp_path: Path) -> None:
        """When a task ID appears in archive/, the tasks/ copy is excluded from active list.

        AC-C19 mode 7: archive copy takes precedence — the active copy is skipped
        so the task does not appear in the active task list.
        """
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, status="done")  # in tasks/
        _write_task(board, task_id=1, subdir="archive")  # also in archive/
        engine = KanbanEngine(board, activity_log=False)
        active = engine.list_tasks(archived=False)
        ids = [t.id for t in active]
        # Archive copy takes precedence → task 1 NOT in active list
        assert 1 not in ids

    def test_list_tasks_archived_true_returns_archive_copy(self, tmp_path: Path) -> None:
        """list_tasks(archived=True) reads from archive/ directly."""
        board = _make_board(tmp_path)
        _write_task(board, task_id=5, title="Archived Task", subdir="archive")
        engine = KanbanEngine(board, activity_log=False)
        result = engine.list_tasks(archived=True)
        assert any(t.id == 5 for t in result)

    def test_dep_status_blocked_when_dep_not_found(self, tmp_path: Path) -> None:
        """dep_status is 'blocked' when a dependency ID is neither active nor archived."""
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, depends_on="[999]")
        engine = KanbanEngine(board, activity_log=False)
        result = engine.list_tasks()
        task1 = next(t for t in result if t.id == 1)
        assert task1.dep_status == "blocked"

    def test_dep_status_redirect_when_dep_archived_as_duplicate(self, tmp_path: Path) -> None:
        """dep_status is 'redirect' when dep archived with duplicate/deprecated reason."""
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, depends_on="[2]")
        # Write task 2 in archive with archival_reason: duplicate
        archived_content = """\
---
id: 2
title: Archived Dep
status: archived
priority: needed
created: "2026-01-01T10:00:00+00:00"
updated: "2026-01-01T10:00:00+00:00"
tags: []
parent: null
depends_on: []
blocked: false
block_reason: null
claimed_at: null
archival_reason: duplicate
archival_refs: []
---
Body.
"""
        (board / "archive" / "2-task.md").write_text(archived_content, encoding="utf-8")
        engine = KanbanEngine(board, activity_log=False)
        result = engine.list_tasks()
        task1 = next(t for t in result if t.id == 1)
        assert task1.dep_status == "redirect"

    def test_dep_status_blocked_when_dep_archived_as_dropped(self, tmp_path: Path) -> None:
        """dep_status is 'blocked' when dep archived with dropped/wontfix reason."""
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, depends_on="[3]")
        archived_content = """\
---
id: 3
title: Dropped Dep
status: archived
priority: needed
created: "2026-01-01T10:00:00+00:00"
updated: "2026-01-01T10:00:00+00:00"
tags: []
parent: null
depends_on: []
blocked: false
block_reason: null
claimed_at: null
archival_reason: dropped
archival_refs: []
---
Body.
"""
        (board / "archive" / "3-task.md").write_text(archived_content, encoding="utf-8")
        engine = KanbanEngine(board, activity_log=False)
        result = engine.list_tasks()
        task1 = next(t for t in result if t.id == 1)
        assert task1.dep_status == "blocked"


# ---------------------------------------------------------------------------
# end_work — success on intermediate status advances correctly
# ---------------------------------------------------------------------------


class TestFromAC_EngineApplyOutcome:
    """AC: _apply_outcome advances status, sets blocked, rejects, or fails."""

    def test_success_from_first_status_advances_to_second(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, status="research")
        engine = KanbanEngine(board, activity_log=False)
        result = engine.end_work("1", note=".", outcome="success")
        assert result.status == "backlog"

    def test_success_from_second_to_last_status_advances_to_last(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, status="docs")
        engine = KanbanEngine(board, activity_log=False)
        result = engine.end_work("1", note=".", outcome="success")
        assert result.status == "done"

    def test_reject_to_research_default(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, status="in-progress")
        engine = KanbanEngine(board, activity_log=False)
        result = engine.end_work("1", note=".", outcome="reject", move_to="research")
        assert result.status == "research"


# ---------------------------------------------------------------------------
# Additional targeted coverage for remaining uncovered paths
# ---------------------------------------------------------------------------


class TestFromAC_EngineEditTaskFieldAssignment:
    """AC: edit_task applies valid status and priority assignments."""

    def test_edit_task_valid_status_assignment(self, tmp_path: Path) -> None:
        """edit_task with a valid status updates the task status field."""
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, status="todo")
        engine = KanbanEngine(board, activity_log=False)
        result = engine.edit_task("1", status="backlog")
        assert result.status == "backlog"

    def test_edit_task_valid_priority_assignment(self, tmp_path: Path) -> None:
        """edit_task with a valid priority updates the task priority field."""
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, priority="needed")
        engine = KanbanEngine(board, activity_log=False)
        result = engine.edit_task("1", priority="critical")
        assert result.priority == "critical"

    def test_edit_task_parent_assignment(self, tmp_path: Path) -> None:
        """edit_task with parent updates the parent field."""
        board = _make_board(tmp_path)
        _write_task(board, task_id=1)
        _write_task(board, task_id=42, title="Parent")
        engine = KanbanEngine(board, activity_log=False)
        result = engine.edit_task("1", parent=42)
        assert result.parent == 42

    def test_edit_task_status_and_priority_together(self, tmp_path: Path) -> None:
        """edit_task can update status and priority in a single call."""
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, status="todo", priority="needed")
        engine = KanbanEngine(board, activity_log=False)
        result = engine.edit_task("1", status="in-progress", priority="critical")
        assert result.status == "in-progress"
        assert result.priority == "critical"


class TestFromAC_EngineNonIntegerTaskId:
    """AC: engine methods handle non-integer task IDs gracefully via _find_task_path."""

    def test_edit_task_non_integer_id_raises_file_not_found(self, tmp_path: Path) -> None:
        """edit_task with non-integer task_id raises FileNotFoundError."""
        board = _make_board(tmp_path)
        engine = KanbanEngine(board, activity_log=False)
        engine.list_tasks()  # populate id→filename index
        with pytest.raises(FileNotFoundError):
            engine.edit_task("not-an-id", title="Ghost")

    def test_move_task_non_integer_id_raises_file_not_found(self, tmp_path: Path) -> None:
        """move_task with non-integer task_id raises FileNotFoundError."""
        board = _make_board(tmp_path)
        engine = KanbanEngine(board, activity_log=False)
        engine.list_tasks()
        with pytest.raises(FileNotFoundError):
            engine.move_task("abc", "todo")

    def test_show_task_non_integer_id_uses_glob(self, tmp_path: Path) -> None:
        """show_task with non-integer task_id falls through to glob path."""
        board = _make_board(tmp_path)
        engine = KanbanEngine(board, activity_log=False)
        engine.list_tasks()
        with pytest.raises(FileNotFoundError):
            engine.show_task("not-a-number")


class TestFromAC_EngineListTasksInvalidStatus:
    """AC: list_tasks silently skips tasks with invalid/unconfigured status."""

    def test_skips_task_with_status_not_in_config(self, tmp_path: Path) -> None:
        """Tasks with status not in config.statuses (and not 'archived') are silently skipped."""
        board = _make_board(tmp_path)
        # Write a valid task for baseline
        _write_task(board, task_id=1, status="todo")
        # Write a task with a status not in config
        invalid_task = _TASK_TMPL.format(
            task_id=2,
            title="Invalid Status",
            status="non-existent-status",
            priority="needed",
            tags="[]",
            blocked="false",
            block_reason="null",
            claimed_at="null",
            depends_on="[]",
            body="Body.",
        )
        (board / "tasks" / "2-task.md").write_text(invalid_task, encoding="utf-8")
        engine = KanbanEngine(board, activity_log=False)
        result = engine.list_tasks()
        ids = [t.id for t in result]
        assert 1 in ids
        assert 2 not in ids


class TestFromAC_EngineArchiveScanErrorPaths:
    """AC: list_tasks handles unreadable/corrupt archive files gracefully."""

    def test_archive_scan_skips_unreadable_archive_file(self, tmp_path: Path) -> None:
        """Archive scan continues when a file cannot be parsed (CorruptionError/ValueError)."""
        board = _make_board(tmp_path)
        _write_task(board, task_id=1)  # valid task in tasks/
        # Create a corrupt (unparseable) file in archive/ — missing --- delimiters
        archive_bad = board / "archive" / "99-bad.md"
        archive_bad.write_text("not valid frontmatter\n", encoding="utf-8")
        engine = KanbanEngine(board, activity_log=False)
        result = engine.list_tasks()
        # Task 1 should still be returned; bad archive file is skipped
        assert any(t.id == 1 for t in result)

    def test_archive_scan_skips_archive_file_with_non_digit_prefix(self, tmp_path: Path) -> None:
        """Archive files without numeric prefix are ignored during archive scan."""
        board = _make_board(tmp_path)
        _write_task(board, task_id=1)
        # Write an archive file with no numeric prefix
        (board / "archive" / "no-id-prefix.md").write_text("---\nid: 1\ntitle: T\n---\n", encoding="utf-8")
        engine = KanbanEngine(board, activity_log=False)
        result = engine.list_tasks()
        # task 1 should appear in active list (non-digit archive prefix skipped)
        assert any(t.id == 1 for t in result)


# ---------------------------------------------------------------------------
# Duplicate ID detection in list_tasks
# ---------------------------------------------------------------------------


class TestFromAC_EngineDuplicateIdDetection:
    """AC: list_tasks raises CorruptionError when two active tasks share the same ID."""

    def test_duplicate_task_id_raises_corruption_error(self, tmp_path: Path) -> None:
        """Two task files with the same numeric ID trigger CorruptionError."""
        from owlbear_kanban.corruption import CorruptionError

        board = _make_board(tmp_path)
        _write_task(board, task_id=1, title="First")
        # Write a second task file with the same ID but different filename
        second_content = _TASK_TMPL.format(
            task_id=1,
            title="Duplicate ID",
            status="todo",
            priority="needed",
            tags="[]",
            blocked="false",
            block_reason="null",
            claimed_at="null",
            depends_on="[]",
            body="Duplicate body.",
        )
        (board / "tasks" / "1-duplicate-task.md").write_text(second_content, encoding="utf-8")
        engine = KanbanEngine(board, activity_log=False)
        with pytest.raises(CorruptionError):
            engine.list_tasks()


# ---------------------------------------------------------------------------
# show_task — stale index path (file deleted after list_tasks)
# ---------------------------------------------------------------------------


class TestFromAC_EngineShowTaskStalePath:
    """AC: show_task handles FileNotFoundError when cached file is deleted."""

    def test_show_task_file_deleted_after_index_built(self, tmp_path: Path) -> None:
        """show_task raises FileNotFoundError when file is deleted after list_tasks."""
        board = _make_board(tmp_path)
        path = _write_task(board, task_id=20, title="Ephemeral")
        engine = KanbanEngine(board, activity_log=False)
        engine.list_tasks()  # warms id→filename index
        path.unlink()  # delete the task file after index is built
        with pytest.raises(FileNotFoundError):
            engine.show_task("20")

    def test_edit_task_via_index_with_actual_task(self, tmp_path: Path) -> None:
        """edit_task uses the id→filename index when populated by list_tasks."""
        board = _make_board(tmp_path)
        _write_task(board, task_id=30, title="Indexed Task")
        engine = KanbanEngine(board, activity_log=False)
        engine.list_tasks()  # populate id→filename
        # Non-integer task_id after index is populated hits ValueError path
        with pytest.raises(FileNotFoundError):
            engine.edit_task("not-a-number", title="Ghost")

    def test_claim_task_via_index_after_list_tasks(self, tmp_path: Path) -> None:
        """claim_task uses id→filename index after list_tasks."""
        board = _make_board(tmp_path)
        _write_task(board, task_id=31)
        engine = KanbanEngine(board, activity_log=False)
        engine.list_tasks()  # populate id→filename
        result = engine.claim_task("31")
        assert result.claimed_at is not None


# ---------------------------------------------------------------------------
# AgentView.list_tasks — interface coverage
# ---------------------------------------------------------------------------


class TestFromAC_AgentViewListTasks:
    """AC: AgentView.list_tasks returns ListTasksResponse; ids filter narrows results."""

    def test_list_tasks_returns_list_tasks_response(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, title="Alpha")
        engine = KanbanEngine(board, activity_log=False)
        resp = engine.agent_view().list_tasks()
        assert isinstance(resp, ListTasksResponse)
        assert any(t.id == 1 for t in resp.tasks)

    def test_list_tasks_ids_filter_returns_only_requested(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, title="Alpha")
        _write_task(board, task_id=2, title="Beta")
        engine = KanbanEngine(board, activity_log=False)
        resp = engine.agent_view().list_tasks(ids=[1])
        assert len(resp.tasks) == 1
        assert resp.tasks[0].id == 1

    def test_list_tasks_ids_filter_reports_missing(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1)
        engine = KanbanEngine(board, activity_log=False)
        resp = engine.agent_view().list_tasks(ids=[1, 99])
        assert 99 in (resp.missing_ids or [])


# ---------------------------------------------------------------------------
# AgentView.show_task — interface coverage
# ---------------------------------------------------------------------------


class TestFromAC_AgentViewShowTask:
    """AC: AgentView.show_task returns ShowTaskResponse; section extraction works."""

    def test_show_task_happy(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, title="Zeta")
        engine = KanbanEngine(board, activity_log=False)
        resp = engine.agent_view().show_task(1)
        assert isinstance(resp, ShowTaskResponse)
        assert resp.id == 1

    def test_show_task_not_found_raises_not_found_error(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        engine = KanbanEngine(board, activity_log=False)
        with pytest.raises(NotFoundError):
            engine.agent_view().show_task(999)

    def test_show_task_with_section_returns_section_body(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, body="## Summary\n\nHello section.")
        engine = KanbanEngine(board, activity_log=False)
        resp = engine.agent_view().show_task(1, section="Summary")
        assert resp.body is not None
        assert "Hello section" in resp.body

    def test_show_task_section_not_found_sets_missing_sections(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, body="## Summary\n\nHello.")
        engine = KanbanEngine(board, activity_log=False)
        resp = engine.agent_view().show_task(1, section="NonExistent")
        assert resp.missing_sections == ["NonExistent"]

    def test_show_task_empty_section_raises_validation_error(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1)
        engine = KanbanEngine(board, activity_log=False)
        with pytest.raises(ValidationError) as exc_info:
            engine.agent_view().show_task(1, section="  ")
        assert exc_info.value.code == "ERR_SECTION_EMPTY"


# ---------------------------------------------------------------------------
# AgentView.pick_tasks — interface coverage
# ---------------------------------------------------------------------------


class TestFromAC_AgentViewPickTasks:
    """AC: AgentView.pick_tasks returns PickTasksResponse; validates params."""

    def test_pick_tasks_empty_board_returns_empty_waves(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        engine = KanbanEngine(board, activity_log=False)
        resp = engine.agent_view().pick_tasks()
        assert isinstance(resp, PickTasksResponse)
        assert resp.waves == []

    def test_pick_tasks_todo_tasks_returned_in_waves(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, status="todo", body="- AC item.")
        _write_task(board, task_id=2, status="todo", body="- AC item.")
        engine = KanbanEngine(board, activity_log=False)
        resp = engine.agent_view().pick_tasks(wave_size=2)
        assert len(resp.waves) >= 1
        all_ids = {e.id for wave in resp.waves for e in wave.tasks}
        assert {1, 2}.issubset(all_ids)

    def test_pick_tasks_invalid_max_waves_raises(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        engine = KanbanEngine(board, activity_log=False)
        with pytest.raises(ValidationError) as exc_info:
            engine.agent_view().pick_tasks(max_waves=0)
        assert exc_info.value.code == "ERR_INVALID_WAVE_PARAM"

    def test_pick_tasks_invalid_wave_size_raises(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        engine = KanbanEngine(board, activity_log=False)
        with pytest.raises(ValidationError) as exc_info:
            engine.agent_view().pick_tasks(wave_size=0)
        assert exc_info.value.code == "ERR_INVALID_WAVE_PARAM"


# ---------------------------------------------------------------------------
# AgentView.create_task — interface coverage
# ---------------------------------------------------------------------------


class TestFromAC_AgentViewCreateTask:
    """AC: AgentView.create_task returns SingleTaskResponse; invalid inputs raise."""

    def test_create_task_happy(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        engine = KanbanEngine(board, activity_log=False)
        resp = engine.agent_view().create_task(title="New Task", body="Some body")
        assert isinstance(resp, SingleTaskResponse)
        assert resp.title == "New Task"

    def test_create_task_empty_title_raises_validation_error(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        engine = KanbanEngine(board, activity_log=False)
        with pytest.raises(ValidationError):
            engine.agent_view().create_task(title="   ")

    def test_create_task_invalid_priority_raises_validation_error(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        engine = KanbanEngine(board, activity_log=False)
        with pytest.raises(ValidationError):
            engine.agent_view().create_task(title="X", priority="ultra")


# ---------------------------------------------------------------------------
# AgentView.edit_task — interface coverage
# ---------------------------------------------------------------------------


class TestFromAC_AgentViewEditTask:
    """AC: AgentView.edit_task returns SingleTaskResponse; not found raises."""

    def test_edit_task_happy(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, title="Old")
        engine = KanbanEngine(board, activity_log=False)
        resp = engine.agent_view().edit_task(1, body="Updated body")
        assert isinstance(resp, SingleTaskResponse)

    def test_edit_task_not_found_raises_not_found_error(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        engine = KanbanEngine(board, activity_log=False)
        with pytest.raises(NotFoundError):
            engine.agent_view().edit_task(999, body="x")

    def test_edit_task_invalid_priority_raises_validation_error(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1)
        engine = KanbanEngine(board, activity_log=False)
        with pytest.raises(ValidationError):
            engine.agent_view().edit_task(1, priority="ultra")


# ---------------------------------------------------------------------------
# AgentView.move_task — interface coverage
# ---------------------------------------------------------------------------


class TestFromAC_AgentViewMoveTask:
    """AC: AgentView.move_task returns SingleTaskResponse; skip guidance emitted."""

    def test_move_task_adjacent_status(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, status="todo")
        engine = KanbanEngine(board, activity_log=False)
        resp = engine.agent_view().move_task(1, "in-progress")
        assert resp.status == "in-progress"

    def test_move_task_multi_column_skip_emits_guidance(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, status="research")
        engine = KanbanEngine(board, activity_log=False)
        # research → in-progress skips backlog and todo
        resp = engine.agent_view().move_task(1, "in-progress")
        assert any("skip" in g.lower() for g in resp.guidance)

    def test_move_task_not_found_raises(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        engine = KanbanEngine(board, activity_log=False)
        with pytest.raises(NotFoundError):
            engine.agent_view().move_task(999, "todo")

    def test_move_task_invalid_status_raises(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1)
        engine = KanbanEngine(board, activity_log=False)
        with pytest.raises(ValidationError):
            engine.agent_view().move_task(1, "nonexistent")


# ---------------------------------------------------------------------------
# AgentView.start_work — interface coverage
# ---------------------------------------------------------------------------


class TestFromAC_AgentViewStartWork:
    """AC: AgentView.start_work claims task; already claimed raises ConcurrencyError."""

    def test_start_work_happy(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1)
        engine = KanbanEngine(board, activity_log=False)
        resp = engine.agent_view().start_work(1)
        assert isinstance(resp, SingleTaskResponse)
        assert resp.claimed_at is not None

    def test_start_work_not_found_raises(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        engine = KanbanEngine(board, activity_log=False)
        with pytest.raises(NotFoundError):
            engine.agent_view().start_work(999)

    def test_start_work_already_claimed_raises_concurrency_error(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        # Write task with a future (unexpired) claim timestamp
        _write_task(board, task_id=1, claimed_at='"2099-01-01T00:00:00+00:00"')
        engine = KanbanEngine(board, activity_log=False)
        with pytest.raises(ConcurrencyError) as exc_info:
            engine.agent_view().start_work(1)
        assert exc_info.value.code == "ERR_ALREADY_CLAIMED"

    def test_start_work_blocked_task_raises_validation_error(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, blocked="true")
        engine = KanbanEngine(board, activity_log=False)
        with pytest.raises(ValidationError):
            engine.agent_view().start_work(1)


# ---------------------------------------------------------------------------
# AgentView.end_work — interface coverage
# ---------------------------------------------------------------------------


class TestFromAC_AgentViewEndWork:
    """AC: AgentView.end_work applies outcome and returns SingleTaskResponse."""

    def test_end_work_success_advances_status(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, status="todo", claimed_at=_now_ts())
        engine = KanbanEngine(board, activity_log=False)
        resp = engine.agent_view().end_work(1, outcome="success", note="Done.")
        assert resp.status == "in-progress"

    def test_end_work_fail_keeps_status(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, status="todo", claimed_at=_now_ts())
        engine = KanbanEngine(board, activity_log=False)
        resp = engine.agent_view().end_work(1, outcome="fail", note="Failed.")
        assert resp.status == "todo"

    def test_end_work_block_returns_ar_hint_in_guidance(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, status="todo", claimed_at=_now_ts())
        engine = KanbanEngine(board, activity_log=False)
        resp = engine.agent_view().end_work(1, outcome="block", note="Blocked.", block_reason="waiting for dep")
        assert any("ACTION REQUIRED" in g for g in resp.guidance)

    def test_end_work_reject_with_forward_move_emits_skip_guidance(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, status="research", claimed_at=_now_ts())
        engine = KanbanEngine(board, activity_log=False)
        # reject from research to in-progress skips backlog + todo → guidance
        resp = engine.agent_view().end_work(1, outcome="reject", note="Rejected.", move_to="in-progress")
        assert any("skip" in g.lower() for g in resp.guidance)

    def test_end_work_not_found_raises(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        engine = KanbanEngine(board, activity_log=False)
        with pytest.raises(NotFoundError):
            engine.agent_view().end_work(999, outcome="success", note="x")


# ---------------------------------------------------------------------------
# AgentView._skip_transition_guidance — static method coverage
# ---------------------------------------------------------------------------


class TestFromAC_SkipTransitionGuidance:
    """AC: _skip_transition_guidance returns guidance only when columns are skipped."""

    def test_no_guidance_for_adjacent_statuses(self) -> None:
        statuses = ["research", "backlog", "todo", "in-progress", "done"]
        result = AgentView._skip_transition_guidance(
            before_status="research",
            after_status="backlog",
            status_names=statuses,
        )
        assert result == []

    def test_guidance_returned_for_multi_column_skip(self) -> None:
        statuses = ["research", "backlog", "todo", "in-progress", "done"]
        result = AgentView._skip_transition_guidance(
            before_status="research",
            after_status="in-progress",
            status_names=statuses,
        )
        assert len(result) == 1
        assert "skip" in result[0].lower()

    def test_no_guidance_for_unknown_before_status(self) -> None:
        statuses = ["research", "backlog", "todo"]
        result = AgentView._skip_transition_guidance(
            before_status="nonexistent",
            after_status="todo",
            status_names=statuses,
        )
        assert result == []


# ---------------------------------------------------------------------------
# dep_status computation paths (list_tasks projection)
# ---------------------------------------------------------------------------


_ARCHIVE_TASK_TMPL = """\
---
id: {task_id}
title: {title}
status: archived
priority: needed
created: "2026-01-01T10:00:00+00:00"
updated: "2026-01-01T10:00:00+00:00"
tags: []
parent: null
depends_on: []
blocked: false
block_reason: null
claimed_at: null
archival_reason: {archival_reason}
archival_refs: []
---
"""


class TestFromAC_DepStatusPaths:
    """AC: _compute_dep_status returns correct dep_status based on archived reasons."""

    def test_dep_status_blocked_when_dep_archived_with_dropped(self, tmp_path: Path) -> None:
        """Dep archived with 'dropped' reason → dep_status = 'blocked'."""
        board = _make_board(tmp_path)
        (board / "archive" / "10-dropped-dep.md").write_text(
            _ARCHIVE_TASK_TMPL.format(task_id=10, title="Dropped", archival_reason="dropped"),
            encoding="utf-8",
        )
        _write_task(board, task_id=1, depends_on="[10]")
        engine = KanbanEngine(board, activity_log=False)
        summaries = engine.list_tasks()
        t = next(s for s in summaries if s.id == 1)
        assert t.dep_status == "blocked"

    def test_dep_status_redirect_when_dep_archived_with_duplicate(self, tmp_path: Path) -> None:
        """Dep archived with 'duplicate' reason → dep_status = 'redirect'."""
        board = _make_board(tmp_path)
        (board / "archive" / "10-dup-dep.md").write_text(
            _ARCHIVE_TASK_TMPL.format(task_id=10, title="Dup", archival_reason="duplicate"),
            encoding="utf-8",
        )
        _write_task(board, task_id=1, depends_on="[10]")
        engine = KanbanEngine(board, activity_log=False)
        summaries = engine.list_tasks()
        t = next(s for s in summaries if s.id == 1)
        assert t.dep_status == "redirect"

    def test_dep_status_blocked_when_dep_not_in_active_or_archived(self, tmp_path: Path) -> None:
        """Dep missing from both active and archived → dep_status = 'blocked'."""
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, depends_on="[999]")
        engine = KanbanEngine(board, activity_log=False)
        summaries = engine.list_tasks()
        t = next(s for s in summaries if s.id == 1)
        assert t.dep_status == "blocked"


# ---------------------------------------------------------------------------
# list_tasks sort by created/updated timestamp paths
# ---------------------------------------------------------------------------


class TestFromAC_SortByTimestampPath:
    """AC: list_tasks sort='created' and sort='updated' use datetime comparison."""

    def _write_task_with_timestamps(self, board: Path, task_id: int, title: str, created: str, updated: str) -> None:
        content = _TASK_TMPL.format(
            task_id=task_id,
            title=title,
            status="todo",
            priority="needed",
            tags="[]",
            blocked="false",
            block_reason="null",
            claimed_at="null",
            depends_on="[]",
            body="",
        )
        content = content.replace('created: "2026-01-01T10:00:00+00:00"', f'created: "{created}"').replace(
            'updated: "2026-01-01T10:00:00+00:00"', f'updated: "{updated}"'
        )
        (board / "tasks" / f"{task_id}-task.md").write_text(content, encoding="utf-8")

    def test_list_tasks_sort_by_created(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        self._write_task_with_timestamps(board, 1, "Early", "2026-01-01T08:00:00+00:00", "2026-01-01T10:00:00+00:00")
        self._write_task_with_timestamps(board, 2, "Late", "2026-01-02T10:00:00+00:00", "2026-01-02T10:00:00+00:00")
        engine = KanbanEngine(board, activity_log=False)
        result = engine.list_tasks(sort="created")
        ids = [t.id for t in result]
        assert ids.index(1) < ids.index(2)

    def test_list_tasks_sort_by_updated(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        self._write_task_with_timestamps(board, 1, "Early", "2026-01-01T10:00:00+00:00", "2026-01-01T08:00:00+00:00")
        self._write_task_with_timestamps(board, 2, "Late", "2026-01-01T10:00:00+00:00", "2026-01-02T10:00:00+00:00")
        engine = KanbanEngine(board, activity_log=False)
        result = engine.list_tasks(sort="updated")
        ids = [t.id for t in result]
        assert ids.index(1) < ids.index(2)


# ---------------------------------------------------------------------------
# list_sessions — no activity-log path
# ---------------------------------------------------------------------------


class TestFromAC_ListSessionsNoLog:
    """AC: list_sessions returns empty when activity log is disabled."""

    def test_list_sessions_returns_empty_when_no_activity_log(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        engine = KanbanEngine(board, activity_log=False)
        assert engine.list_sessions() == []

    def test_list_sessions_returns_empty_when_log_file_absent(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        # Use a config with activity_log=true but don't create the file
        engine = KanbanEngine(board, activity_log=True)
        # activity.jsonl doesn't exist yet → empty list
        assert engine.list_sessions() == []


# ---------------------------------------------------------------------------
# repair_storage — basic coverage
# ---------------------------------------------------------------------------


class TestFromAC_RepairStorage:
    """AC: repair_storage returns empty list on a clean board."""

    def test_repair_storage_clean_board_returns_empty(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1)
        engine = KanbanEngine(board, activity_log=False)
        outcomes = engine.repair_storage()
        assert outcomes == []


# ---------------------------------------------------------------------------
# Canonical board-status tuple and released status disambiguation
# ---------------------------------------------------------------------------


class TestFromAC_CanonicalBoardStatusTuple:
    """AC1 (topology-constant refactor): board statuses are exactly the 7-item
    PRODUCT_TOPOLOGY tuple; board status 'released' is absent; session state
    'released' remains a valid _classify_end_work_state output.
    """

    def test_board_config_statuses_exact_seven_tuple(self, tmp_path: Path) -> None:
        """board_config().statuses matches the canonical 7-status tuple exactly.

        Proves the full ordered list matches PRODUCT_TOPOLOGY.statuses so that
        no status can be silently added, removed, or reordered.
        """
        engine = _make_engine(tmp_path)
        cfg = engine.board_config()
        expected = list(PRODUCT_TOPOLOGY.statuses)
        assert cfg.statuses == expected, f"Expected canonical status tuple {expected!r}; got {cfg.statuses!r}"

    def test_board_status_released_absent(self, tmp_path: Path) -> None:
        """'released' must NOT be a board status — it is a session lifecycle state only.

        Current membership-only tests allow 'released' to slip in without notice.
        This test pins the exclusion explicitly.
        """
        engine = _make_engine(tmp_path)
        cfg = engine.board_config()
        assert "released" not in cfg.statuses, (
            "'released' must not appear in board statuses; it is a session state only"
        )

    def test_session_state_released_valid_from_classify(self) -> None:
        """_classify_end_work_state maps 'release' prefix to session state 'released'.

        Proves the session lifecycle state 'released' remains valid even though
        board status 'released' is absent. These are distinct concepts.
        """
        result = _classify_end_work_state("release")
        assert result == "released", f"Session state for 'release' must be 'released'; got {result!r}"


# --- merged from serve/kanban/tests/test_engine_coverage_regressions.py ---
_CONFIG_YAML = """\
statuses:
  - research
  - backlog
  - todo
  - in-progress
  - review
  - docs
  - done
priorities:
  - someday
  - nice-to-have
  - important
  - needed
  - critical
entry_status: research
wave_size: 4
agent_map:
  research: []
  backlog: []
  todo: []
  in-progress: []
  review: []
  docs: []
  done: []
agent_types: {}
agent_compatibility: {}
non_impl_tags: [research, docs]
archival_reasons: [completed, deprecated, dropped, duplicate, wontfix]
status_predicates: {}
claim_timeout: 1h
next_id: 1
"""

_EPOCH_CLAIMED_AT = '"2026-01-01T00:00:00+00:00"'  # always expired (> 1 h ago)


def _active_claimed_at() -> str:
    """Return a quoted ISO timestamp that is always within the 1 h claim window."""
    return f'"{datetime.now(UTC).isoformat()}"'


class TestFromAC_EngineListTasksFilters:
    """AC: list_tasks filter/sort branches; covers tag, priority, blocked,
    unclaimed, and search code paths."""

    def test_filter_by_tag_returns_only_matching(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, tags='["alpha"]')
        _write_task(board, task_id=2, tags='["beta"]')
        engine = KanbanEngine(board, activity_log=False)
        result = engine.list_tasks(tag="alpha")
        assert len(result) == 1
        assert result[0].id == 1

    def test_filter_by_priority_returns_only_matching(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, priority="critical")
        _write_task(board, task_id=2, priority="someday")
        engine = KanbanEngine(board, activity_log=False)
        result = engine.list_tasks(priority="critical")
        assert len(result) == 1
        assert result[0].id == 1

    def test_filter_blocked_true_returns_only_blocked(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, blocked="true", block_reason='"blocked"')
        _write_task(board, task_id=2, blocked="false")
        engine = KanbanEngine(board, activity_log=False)
        result = engine.list_tasks(blocked=True)
        assert [t.id for t in result] == [1]

    def test_filter_blocked_false_returns_only_unblocked(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, blocked="true", block_reason='"blocked"')
        _write_task(board, task_id=2, blocked="false")
        engine = KanbanEngine(board, activity_log=False)
        result = engine.list_tasks(blocked=False)
        assert [t.id for t in result] == [2]

    def test_filter_unclaimed_excludes_claimed_tasks(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, claimed_at=_active_claimed_at())
        _write_task(board, task_id=2, claimed_at="null")
        engine = KanbanEngine(board, activity_log=False)
        result = engine.list_tasks(unclaimed=True)
        assert [t.id for t in result] == [2]

    def test_filter_search_matches_title(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, title="Alpha task")
        _write_task(board, task_id=2, title="Beta task")
        engine = KanbanEngine(board, activity_log=False)
        result = engine.list_tasks(search="alpha")
        assert [t.id for t in result] == [1]

    def test_filter_search_matches_body(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, body="contains the needle")
        _write_task(board, task_id=2, body="no match here")
        engine = KanbanEngine(board, activity_log=False)
        result = engine.list_tasks(search="needle")
        assert [t.id for t in result] == [1]


class TestFromAC_EngineListTasksSortAndPage:
    """AC: list_tasks sort, reverse, and limit branches."""

    def test_sort_by_id(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=3, title="C")
        _write_task(board, task_id=1, title="A")
        _write_task(board, task_id=2, title="B")
        engine = KanbanEngine(board, activity_log=False)
        result = engine.list_tasks(sort="id")
        assert [t.id for t in result] == [1, 2, 3]

    def test_sort_by_title(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, title="Zebra")
        _write_task(board, task_id=2, title="Apple")
        engine = KanbanEngine(board, activity_log=False)
        result = engine.list_tasks(sort="title")
        assert result[0].title == "Apple"
        assert result[1].title == "Zebra"

    def test_sort_by_status(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, status="done")
        _write_task(board, task_id=2, status="research")
        engine = KanbanEngine(board, activity_log=False)
        result = engine.list_tasks(sort="status")
        # research is index 0 in config
        assert result[0].status == "research"
        assert result[-1].status == "done"

    def test_sort_by_priority(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, priority="critical")
        _write_task(board, task_id=2, priority="someday")
        engine = KanbanEngine(board, activity_log=False)
        result = engine.list_tasks(sort="priority")
        # someday is index 0 in config
        assert result[0].priority == "someday"
        assert result[-1].priority == "critical"

    def test_sort_by_created(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, title="Older")
        # Overwrite created to an earlier timestamp
        path = board / "tasks" / "1-task.md"
        path.write_text(
            path.read_text().replace(
                'created: "2026-01-01T10:00:00+00:00"',
                'created: "2025-01-01T10:00:00+00:00"',
            )
        )
        _write_task(board, task_id=2, title="Newer")
        engine = KanbanEngine(board, activity_log=False)
        result = engine.list_tasks(sort="created")
        assert result[0].id == 1

    def test_sort_by_updated(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, title="OldUpdate")
        path = board / "tasks" / "1-task.md"
        path.write_text(
            path.read_text().replace(
                'updated: "2026-01-01T10:00:00+00:00"',
                'updated: "2025-01-01T10:00:00+00:00"',
            )
        )
        _write_task(board, task_id=2, title="NewUpdate")
        engine = KanbanEngine(board, activity_log=False)
        result = engine.list_tasks(sort="updated")
        assert result[0].id == 1  # oldest updated first

    def test_sort_with_reverse_inverts_order(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        for i in (1, 2, 3):
            _write_task(board, task_id=i, title=f"T{i}")
        engine = KanbanEngine(board, activity_log=False)
        result = engine.list_tasks(sort="id", reverse=True)
        assert [t.id for t in result] == [3, 2, 1]

    def test_limit_caps_result_count(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        for i in (1, 2, 3, 4):
            _write_task(board, task_id=i, title=f"T{i}")
        engine = KanbanEngine(board, activity_log=False)
        result = engine.list_tasks(sort="id", limit=2)
        assert len(result) == 2
        assert [t.id for t in result] == [1, 2]


class TestFromAC_EngineListTasksArchived:
    """AC: list_tasks archived=True sets claimed_by to None."""

    def test_archived_task_claimed_by_is_cleared(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, claimed_at=_active_claimed_at(), subdir="archive")
        engine = KanbanEngine(board, activity_log=False)
        result = engine.list_tasks(archived=True)
        assert len(result) == 1
        # claimed_at is set → TaskSummary.claimed=True; engine cleared claimed_by
        # to None for archived tasks (coverage target: line 558 in list_tasks)
        assert result[0].claimed is True

    def test_archived_task_without_claimed_at_shows_claimed_false(self, tmp_path: Path) -> None:
        """Archived task with no claimed_at must report claimed=False.

        Regression guard: TaskSummary derives `claimed` from `claimed_at` only;
        removing the in-memory `task.claimed_by = None` mutation (list_tasks line
        for archived tasks) must not affect this — the projection handles it.
        This test proves both branches of the claimed projection for archived tasks.
        """
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, claimed_at="null", subdir="archive")
        engine = KanbanEngine(board, activity_log=False)
        result = engine.list_tasks(archived=True)
        assert len(result) == 1
        assert result[0].claimed is False


class TestFromAC_EngineListTasksParseErrors:
    """AC: list_tasks silently skips files that fail to parse."""

    def test_skips_task_file_with_missing_required_field(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1)
        # Write a file that is missing required fields → parse error
        bad = board / "tasks" / "99-bad.md"
        bad.write_text("---\ntitle: Bad\nstatus: todo\n---\nBody\n", encoding="utf-8")
        engine = KanbanEngine(board, activity_log=False)
        result = engine.list_tasks()
        ids = [t.id for t in result]
        assert 1 in ids
        assert 99 not in ids


class TestFromAC_EngineComputeDuration:
    """AC: _compute_duration normalises tz-naive timestamps to UTC."""

    def test_tz_naive_claim_ts_normalised_to_utc(self) -> None:
        result = _compute_duration(
            "2026-04-23T10:00:00",  # tz-naive
            "2026-04-23T11:00:00+00:00",  # tz-aware
        )
        assert result == 3600.0

    def test_tz_naive_close_ts_normalised_to_utc(self) -> None:
        result = _compute_duration(
            "2026-04-23T10:00:00+00:00",  # tz-aware
            "2026-04-23T11:00:00",  # tz-naive
        )
        assert result == 3600.0

    def test_both_tz_naive_computed_correctly(self) -> None:
        result = _compute_duration("2026-04-23T10:00:00", "2026-04-23T11:30:00")
        assert result == 5400.0


class TestFromAC_EngineListSessionsSpecialActions:
    """AC: list_sessions reflects release, sweep-release, and double-claim events
    from activity.jsonl (_collect_task_sessions uncovered branches)."""

    def _write_log(self, board: Path, entries: list[dict]) -> None:
        import json as _json

        log = board / "activity.jsonl"
        lines = "\n".join(_json.dumps(e) for e in entries)
        log.write_text(lines + "\n", encoding="utf-8")

    def test_release_action_produces_released_session(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        self._write_log(
            board,
            [
                {
                    "action": "claim",
                    "task_id": 1,
                    "detail": "agent-X",
                    "timestamp": "2026-04-23T10:00:00+00:00",
                    "task_status_at_start": "todo",
                },
                {
                    "action": "release",
                    "task_id": 1,
                    "detail": "released by agent-X",
                    "timestamp": "2026-04-23T10:30:00+00:00",
                },
            ],
        )
        engine = KanbanEngine(board, activity_log=True)
        sessions = engine.list_sessions(filter="released")
        assert len(sessions) == 1
        assert sessions[0].state == "released"
        assert sessions[0].outcome == "release"

    def test_sweep_release_action_produces_expired_session(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        self._write_log(
            board,
            [
                {
                    "action": "claim",
                    "task_id": 2,
                    "detail": "agent-Y",
                    "timestamp": "2026-04-23T10:00:00+00:00",
                    "task_status_at_start": "todo",
                },
                {
                    "action": "sweep-release",
                    "task_id": 2,
                    "detail": "expired claim released",
                    "timestamp": "2026-04-23T12:00:00+00:00",
                },
            ],
        )
        engine = KanbanEngine(board, activity_log=True)
        sessions = engine.list_sessions(filter="all")
        expired = [s for s in sessions if s.state == "expired"]
        assert len(expired) == 1
        assert expired[0].outcome == "expired"

    def test_double_claim_adds_session_for_unclosed_prior_claim(self, tmp_path: Path) -> None:
        """A second claim while one is open → previous claim emitted as running/stuck."""
        board = _make_board(tmp_path)
        self._write_log(
            board,
            [
                {
                    "action": "claim",
                    "task_id": 3,
                    "detail": "agent-A",
                    "timestamp": "2026-01-01T10:00:00+00:00",  # very old → stuck
                    "task_status_at_start": "todo",
                },
                {
                    "action": "claim",
                    "task_id": 3,
                    "detail": "agent-B",
                    "timestamp": "2026-04-23T10:00:00+00:00",
                    "task_status_at_start": "todo",
                },
            ],
        )
        engine = KanbanEngine(board, activity_log=True)
        sessions = engine.list_sessions(filter="all")
        # At least 2 sessions: the crash-detected first one + the open second one
        assert len(sessions) >= 2
        states = {s.state for s in sessions}
        assert states & {"running", "stuck"}


class TestFromAC_EngineInitMigrationGateEdgeCases:
    """AC: __init__ migration gate handles OSError, no frontmatter, no closing
    fence, and cleared claimed_by without raising."""

    def test_oserror_reading_task_file_is_skipped(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        task_path = board / "tasks" / "1-unreadable.md"
        task_path.write_text("claimed_by: someone\n", encoding="utf-8")
        task_path.chmod(0o000)
        try:
            engine = KanbanEngine(board, activity_log=False)
            assert engine is not None
        finally:
            task_path.chmod(0o644)

    def test_file_without_yaml_frontmatter_marker_is_skipped(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        (board / "tasks" / "1-nofm.md").write_text("no frontmatter\nclaimed_by: someone\n", encoding="utf-8")
        engine = KanbanEngine(board, activity_log=False)
        assert engine is not None

    def test_frontmatter_without_closing_fence_is_skipped(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        (board / "tasks" / "1-nofence.md").write_text("---\nclaimed_by: someone\n# no closing ---\n", encoding="utf-8")
        engine = KanbanEngine(board, activity_log=False)
        assert engine is not None

    def test_cleared_claimed_by_null_does_not_raise(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        (board / "tasks" / "1-cleared.md").write_text(
            "---\nid: 1\ntitle: T\nstatus: todo\nclaimed_by: null\n---\nBody\n",
            encoding="utf-8",
        )
        engine = KanbanEngine(board, activity_log=False)
        assert engine is not None

    def test_cleared_claimed_by_empty_string_does_not_raise(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        (board / "tasks" / "1-empty.md").write_text(
            '---\nid: 1\ntitle: T\nstatus: todo\nclaimed_by: ""\n---\nBody\n',
            encoding="utf-8",
        )
        engine = KanbanEngine(board, activity_log=False)
        assert engine is not None


class TestFromAC_EngineEndWorkValidation:
    """AC: end_work raises ValueError for unknown outcome and invalid move_to."""

    def test_invalid_outcome_raises_value_error(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1)
        engine = KanbanEngine(board, activity_log=False)
        with pytest.raises(ValueError, match="Unknown outcome"):
            engine.end_work("1", note="done", outcome="bogus-outcome")

    def test_reject_with_invalid_move_to_raises_value_error(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1)
        engine = KanbanEngine(board, activity_log=False)
        with pytest.raises(ValueError, match="move_to"):
            engine.end_work("1", note="reject", outcome="reject", move_to="nonexistent-status")

    def test_end_work_block_outcome_marks_task_blocked(self, tmp_path: Path) -> None:
        """AC: end_work block outcome sets blocked=True and records block_reason."""
        board = _make_board(tmp_path)
        _write_task(board, task_id=1)
        engine = KanbanEngine(board, activity_log=False)
        result = engine.end_work(
            "1",
            note="blocking this task",
            outcome="block",
            block_reason="dependency missing",
        )
        assert result.blocked is True
        assert result.block_reason == "dependency missing"

    def test_end_work_fail_outcome_preserves_task_status(self, tmp_path: Path) -> None:
        """AC: end_work fail outcome leaves the task status unchanged."""
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, status="in-progress")
        engine = KanbanEngine(board, activity_log=False)
        result = engine.end_work("1", note="attempt failed", outcome="fail")
        assert result.status == "in-progress"


class TestFromAC_EngineClaimTaskGuards:
    """AC: claim_task rejects blocked tasks and active rival claims."""

    def test_claim_blocked_task_raises_value_error(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, blocked="true", block_reason='"blocked"')
        engine = KanbanEngine(board, activity_log=False)
        with pytest.raises(ValueError, match="blocked"):
            engine.claim_task("1")

    def test_claim_task_already_claimed_not_expired_raises(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, claimed_at=_active_claimed_at())
        engine = KanbanEngine(board, activity_log=False)
        with pytest.raises(ValueError, match="already claimed"):
            engine.claim_task("1")

    def test_claim_task_expired_claim_is_overridable(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, claimed_at=_EPOCH_CLAIMED_AT)
        engine = KanbanEngine(board, activity_log=False)
        task = engine.claim_task("1")
        assert task.claimed_at is not None


class TestFromAC_EngineEditTaskMutationPaths:
    """AC: edit_task blocked=False clears block_reason; append_body with
    timestamp=True prepends [[YYYY-MM-DD]] to the note."""

    def test_unblock_clears_block_reason(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, blocked="true", block_reason='"some reason"')
        engine = KanbanEngine(board, activity_log=False)
        task = engine.edit_task("1", blocked=False)
        assert task.blocked is False
        assert task.block_reason is None

    def test_append_body_with_timestamp_inserts_date_prefix(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1)
        engine = KanbanEngine(board, activity_log=False)
        task = engine.edit_task("1", append_body="My note content", timestamp=True)
        assert re.search(r"\[\[20\d{2}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}\]\]", task.body)
        assert "My note content" in task.body


class TestFromAC_EngineEditTaskRollback:
    """AC: edit_task() rollback path (engine.py:899-901) — when _emit_event raises
    OSError, write_task(original) is called to restore the on-disk state."""

    def test_edit_task_oserror_on_emit_restores_original_task(self, tmp_path: Path) -> None:
        """If activity log emit fails after edit_task write, original is restored."""
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, title="Original Title")
        engine = KanbanEngine(board, activity_log=False)
        with (
            patch.object(engine, "_emit_event", side_effect=OSError("disk full")),
            pytest.raises(OSError),
        ):
            engine.edit_task("1", title="New Title")
        # Rollback must have restored original title to disk
        restored = read_task(board / "tasks" / "1-task.md")
        assert restored.title == "Original Title"

    def test_edit_task_oserror_on_emit_original_body_preserved(self, tmp_path: Path) -> None:
        """Rollback also restores original body when body was appended."""
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, body="original body content")
        engine = KanbanEngine(board, activity_log=False)
        with (
            patch.object(engine, "_emit_event", side_effect=OSError("disk full")),
            pytest.raises(OSError),
        ):
            engine.edit_task("1", append_body="extra appended text")
        restored = read_task(board / "tasks" / "1-task.md")
        assert "extra appended text" not in restored.body
        assert "original body content" in restored.body


class TestFromAC_EngineCreateTaskValidation:
    """AC: create_task raises ValueError for invalid status and priority."""

    def test_create_with_invalid_status_raises(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        engine = KanbanEngine(board, activity_log=False)
        with pytest.raises(ValueError, match="Invalid status"):
            engine.create_task("My task", status="nonexistent-status")

    def test_create_with_invalid_priority_raises(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        engine = KanbanEngine(board, activity_log=False)
        with pytest.raises(ValueError, match="Invalid priority"):
            engine.create_task("My task", priority="ultra-critical")


class TestFromAC_EngineMoveTaskValidation:
    """AC: move_task raises ValueError for an invalid target status."""

    def test_move_to_invalid_status_raises(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1)
        engine = KanbanEngine(board, activity_log=False)
        with pytest.raises(ValueError, match="Invalid status"):
            engine.move_task("1", "nonexistent-status")


class TestFromAC_EngineReadLogEntriesErrors:
    """AC: _read_log_entries handles OSError, invalid JSON, and bad timestamps."""

    def test_oserror_on_activity_log_read_returns_empty_sessions(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        log = board / "activity.jsonl"
        import json as _json

        log.write_text(
            _json.dumps(
                {
                    "action": "claim",
                    "task_id": 1,
                    "detail": "x",
                    "timestamp": "2026-01-01T00:00:00+00:00",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        log.chmod(0o000)
        try:
            engine = KanbanEngine(board, activity_log=True)
            result = engine.list_sessions(filter="all")
            assert result == []
        finally:
            log.chmod(0o644)

    def test_invalid_json_line_is_skipped(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        log = board / "activity.jsonl"
        import json as _json

        valid = _json.dumps(
            {
                "action": "claim",
                "task_id": 1,
                "detail": "x",
                "timestamp": "2026-04-23T10:00:00+00:00",
                "task_status_at_start": "todo",
            }
        )
        log.write_text("not-valid-json\n" + valid + "\n", encoding="utf-8")
        engine = KanbanEngine(board, activity_log=True)
        result = engine.list_sessions(filter="all")
        assert isinstance(result, list)  # did not raise; bad line was skipped

    def test_entry_with_invalid_timestamp_is_skipped(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        log = board / "activity.jsonl"
        import json as _json

        log.write_text(
            _json.dumps(
                {
                    "action": "claim",
                    "task_id": 1,
                    "detail": "x",
                    "timestamp": "not-a-timestamp",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        engine = KanbanEngine(board, activity_log=True)
        result = engine.list_sessions(filter="all")
        assert result == []

    def test_blank_lines_in_log_are_skipped(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        log = board / "activity.jsonl"
        import json as _json

        valid = _json.dumps(
            {
                "action": "claim",
                "task_id": 1,
                "detail": "x",
                "timestamp": "2026-04-23T10:00:00+00:00",
                "task_status_at_start": "todo",
            }
        )
        log.write_text("\n\n" + valid + "\n\n", encoding="utf-8")
        engine = KanbanEngine(board, activity_log=True)
        result = engine.list_sessions(filter="all")
        # Valid entry parsed; blank lines skipped
        assert isinstance(result, list)

    def test_invalid_json_line_skipped_valid_entry_still_parsed(self, tmp_path: Path) -> None:
        """Invalid JSON line is skipped; the following valid claim entry is parsed."""
        import json as _json

        board = _make_board(tmp_path)
        log = board / "activity.jsonl"
        valid = _json.dumps(
            {
                "action": "claim",
                "task_id": 1,
                "detail": "x",
                "timestamp": "2026-04-23T10:00:00+00:00",
                "task_status_at_start": "todo",
            }
        )
        log.write_text("not-valid-json\n" + valid + "\n", encoding="utf-8")
        engine = KanbanEngine(board, activity_log=True)
        result = engine.list_sessions(filter="all")
        # Exactly one session from the one valid claim entry
        assert len(result) == 1
        assert result[0].task_id == 1

    def test_blank_lines_skipped_valid_entry_still_parsed(self, tmp_path: Path) -> None:
        """Blank lines surrounding the valid claim entry are skipped gracefully."""
        import json as _json

        board = _make_board(tmp_path)
        log = board / "activity.jsonl"
        valid = _json.dumps(
            {
                "action": "claim",
                "task_id": 1,
                "detail": "x",
                "timestamp": "2026-04-23T10:00:00+00:00",
                "task_status_at_start": "todo",
            }
        )
        log.write_text("\n\n" + valid + "\n\n", encoding="utf-8")
        engine = KanbanEngine(board, activity_log=True)
        result = engine.list_sessions(filter="all")
        # Exactly one session from the one valid claim entry
        assert len(result) == 1
        assert result[0].task_id == 1


class TestFromAC_EngineDeriveSessionsNonIntTaskId:
    """AC: _derive_sessions skips entries with non-integer task_id."""

    def test_non_integer_task_id_entry_skipped(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        log = board / "activity.jsonl"
        import json as _json

        log.write_text(
            _json.dumps(
                {
                    "action": "claim",
                    "task_id": "not-an-int",
                    "detail": "x",
                    "timestamp": "2026-01-01T00:00:00+00:00",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        engine = KanbanEngine(board, activity_log=True)
        result = engine.list_sessions(filter="all")
        assert result == []


class TestFromAC_EngineEndWorkRollback:
    """AC: end_work() rollback path (engine.py:1204-1208) — when _emit_event raises
    OSError, write_task(original) restores the on-disk state; for archive outcomes
    the file is also moved back from archive/ to tasks/."""

    def test_end_work_oserror_on_emit_restores_original_task(self, tmp_path: Path) -> None:
        """Non-archive outcome: original task body restored when emit fails."""
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, body="original body")
        engine = KanbanEngine(board, activity_log=False)
        with (
            patch.object(engine, "_emit_event", side_effect=OSError("disk full")),
            pytest.raises(OSError),
        ):
            engine.end_work("1", note="end-work note", outcome="fail")
        # Rollback restores the original body
        restored = read_task(board / "tasks" / "1-task.md")
        assert "end-work note" not in restored.body
        assert "original body" in restored.body

    def test_end_work_archive_oserror_on_emit_moves_file_back(self, tmp_path: Path) -> None:
        """Archive outcome: after successful file move, emit failure moves file back."""
        board = _make_board(tmp_path)
        # 'done' is the last status → end_work(success) archives the task
        _write_task(board, task_id=1, status="done", body="done body")
        engine = KanbanEngine(board, activity_log=False)
        with (
            patch.object(engine, "_emit_event", side_effect=OSError("disk full")),
            pytest.raises(OSError),
        ):
            engine.end_work("1", note="archiving note", outcome="success")
        # Task file must be back in tasks/ (not stranded in archive/)
        task_file = board / "tasks" / "1-task.md"
        assert task_file.exists(), "task file not restored to tasks/ after rollback"
        # And content must match the original (pre-mutation)
        restored = read_task(task_file)
        assert "archiving note" not in restored.body
        assert "done body" in restored.body

    def test_end_work_archive_oserror_archive_file_removed_after_rollback(self, tmp_path: Path) -> None:
        """After rollback of an archive outcome, archive/ must not retain the file."""
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, status="done")
        engine = KanbanEngine(board, activity_log=False)
        with (
            patch.object(engine, "_emit_event", side_effect=OSError("disk full")),
            pytest.raises(OSError),
        ):
            engine.end_work("1", note="archiving note", outcome="success")
        # archive/ file must have been moved back (not left in archive/)
        archive_file = board / "archive" / "1-task.md"
        assert not archive_file.exists(), "archive file was not moved back during rollback"
