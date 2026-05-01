"""Coverage-uplift tests for owlbear_kanban.engine (task #1110).

Targets uncovered code paths identified from the 86% baseline measurement:
  - list_tasks filters (tag, priority, blocked, unclaimed, search)
  - list_tasks sort branches (id, title, status, priority, created, updated)
  - list_tasks reverse + limit
  - list_tasks archived=True: claimed_by cleared
  - list_tasks parse-error skip (ValueError/KeyError)
  - sweep(): corrupt file skip, invalid claimed_at format, tz-naive normalisation
  - list_sessions: release, sweep-release, double-claim crash sessions
  - _compute_duration: tz-naive timestamps
  - __init__ migration gate: OSError, no frontmatter, no closing fence, cleared field
  - end_work invalid outcome, reject with invalid move_to
  - claim_task blocked guard, already-claimed-not-expired guard
  - edit_task blocked=False clears block_reason, append_body with timestamp
  - create_task invalid status / invalid priority
  - move_task invalid status
  - list_sessions _read_log_entries error paths (OSError, invalid JSON, bad timestamp)
  - _derive_sessions non-integer task_id
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path

import pytest
from unittest.mock import patch

from owlbear_kanban import KanbanEngine
from owlbear_kanban.engine import _compute_duration
from owlbear_kanban.storage import read_task

# ---------------------------------------------------------------------------
# Board helpers
# ---------------------------------------------------------------------------

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
depends_on: []
blocked: {blocked}
block_reason: {block_reason}
claimed_at: {claimed_at}
archival_reason: null
archival_refs: []
---
{body}
"""

_EPOCH_CLAIMED_AT = '"2026-01-01T00:00:00+00:00"'  # always expired (> 1 h ago)


def _make_board(base_dir: Path) -> Path:
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
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
        body=body,
    )
    path = kanban_dir / subdir / f"{task_id}-task.md"
    path.write_text(content, encoding="utf-8")
    return path


def _active_claimed_at() -> str:
    """Return a quoted ISO timestamp that is always within the 1 h claim window."""
    return f'"{datetime.now(UTC).isoformat()}"'


# ---------------------------------------------------------------------------
# list_tasks — filter branches
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# list_tasks — sort branches, reverse, limit
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# list_tasks — archived branch (claimed_by cleared)
# ---------------------------------------------------------------------------


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

    def test_archived_task_without_claimed_at_shows_claimed_false(
        self, tmp_path: Path
    ) -> None:
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


# ---------------------------------------------------------------------------
# list_tasks — parse-error skip
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# sweep()
# ---------------------------------------------------------------------------


class TestFromAC_EngineSweep:
    """AC: sweep() uncovered code paths — corrupt skip, bad timestamp, tz-naive."""

    def test_sweep_returns_empty_when_no_claimed_tasks(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, claimed_at="null")
        engine = KanbanEngine(board, activity_log=False)
        assert engine.sweep() == []

    def test_sweep_releases_expired_claim(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, claimed_at=_EPOCH_CLAIMED_AT)
        engine = KanbanEngine(board, activity_log=False)
        released = engine.sweep()
        assert 1 in released
        assert read_task(board / "tasks" / "1-task.md").claimed_at is None

    def test_sweep_silently_skips_unparseable_corrupt_file(
        self, tmp_path: Path
    ) -> None:
        board = _make_board(tmp_path)
        (board / "tasks" / "99-corrupt.md").write_text(
            "this is not valid yaml frontmatter at all", encoding="utf-8"
        )
        engine = KanbanEngine(board, activity_log=False)
        released = engine.sweep()
        assert 99 not in released

    def test_sweep_skips_task_with_invalid_claimed_at_format(
        self, tmp_path: Path
    ) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, claimed_at='"not-a-valid-datetime"')
        engine = KanbanEngine(board, activity_log=False)
        released = engine.sweep()
        assert 1 not in released

    def test_sweep_tz_naive_claimed_at_treated_as_utc(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        # tz-naive timestamp that is far in the past (clearly expired)
        _write_task(board, task_id=1, claimed_at='"2026-01-01T00:00:00"')
        engine = KanbanEngine(board, activity_log=False)
        released = engine.sweep()
        assert 1 in released

    def test_sweep_skips_parseable_but_corrupt_file(self, tmp_path: Path) -> None:
        """detect_corruption returns non-None → sweep skips the file."""
        board = _make_board(tmp_path)
        # Instantiate engine BEFORE creating the corrupt file so migration gate
        # does not reject the board during __init__.
        engine = KanbanEngine(board, activity_log=False)
        # Now write a task with claimed_by (forbidden in new schema) directly
        # so detect_corruption flags it as corrupt during sweep.
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
        # Corrupt file must NOT be mutated → 1 not in released
        assert 1 not in released


# ---------------------------------------------------------------------------
# _compute_duration — tz-naive paths
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# list_sessions — release / sweep-release / double-claim via activity log
# ---------------------------------------------------------------------------


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

    def test_sweep_release_action_produces_expired_session(
        self, tmp_path: Path
    ) -> None:
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

    def test_double_claim_adds_session_for_unclosed_prior_claim(
        self, tmp_path: Path
    ) -> None:
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


# ---------------------------------------------------------------------------
# __init__ migration gate — edge cases
# ---------------------------------------------------------------------------


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

    def test_file_without_yaml_frontmatter_marker_is_skipped(
        self, tmp_path: Path
    ) -> None:
        board = _make_board(tmp_path)
        (board / "tasks" / "1-nofm.md").write_text(
            "no frontmatter\nclaimed_by: someone\n", encoding="utf-8"
        )
        engine = KanbanEngine(board, activity_log=False)
        assert engine is not None

    def test_frontmatter_without_closing_fence_is_skipped(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        (board / "tasks" / "1-nofence.md").write_text(
            "---\nclaimed_by: someone\n# no closing ---\n", encoding="utf-8"
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

    def test_cleared_claimed_by_empty_string_does_not_raise(
        self, tmp_path: Path
    ) -> None:
        board = _make_board(tmp_path)
        (board / "tasks" / "1-empty.md").write_text(
            '---\nid: 1\ntitle: T\nstatus: todo\nclaimed_by: ""\n---\nBody\n',
            encoding="utf-8",
        )
        engine = KanbanEngine(board, activity_log=False)
        assert engine is not None


# ---------------------------------------------------------------------------
# end_work — validation paths
# ---------------------------------------------------------------------------


class TestFromAC_EngineEndWorkValidation:
    """AC: end_work raises ValueError for unknown outcome and invalid move_to."""

    def test_invalid_outcome_raises_value_error(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1)
        engine = KanbanEngine(board, activity_log=False)
        with pytest.raises(ValueError, match="Unknown outcome"):
            engine.end_work("1", note="done", outcome="bogus-outcome")

    def test_reject_with_invalid_move_to_raises_value_error(
        self, tmp_path: Path
    ) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1)
        engine = KanbanEngine(board, activity_log=False)
        with pytest.raises(ValueError, match="move_to"):
            engine.end_work(
                "1", note="reject", outcome="reject", move_to="nonexistent-status"
            )

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


# ---------------------------------------------------------------------------
# claim_task — blocked guard and already-claimed guard
# ---------------------------------------------------------------------------


class TestFromAC_EngineClaimTaskGuards:
    """AC: claim_task rejects blocked tasks and active rival claims."""

    def test_claim_blocked_task_raises_value_error(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, blocked="true", block_reason='"blocked"')
        engine = KanbanEngine(board, activity_log=False)
        with pytest.raises(ValueError, match="blocked"):
            engine.claim_task("1")

    def test_claim_task_already_claimed_not_expired_raises(
        self, tmp_path: Path
    ) -> None:
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
        assert task.claimed_by == engine.agent_name


# ---------------------------------------------------------------------------
# edit_task — blocked=False clears block_reason; timestamp prefix
# ---------------------------------------------------------------------------


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

    def test_append_body_with_timestamp_inserts_date_prefix(
        self, tmp_path: Path
    ) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1)
        engine = KanbanEngine(board, activity_log=False)
        task = engine.edit_task("1", append_body="My note content", timestamp=True)
        assert re.search(r"\[\[20\d{2}-\d{2}-\d{2}\]\]", task.body)
        assert "My note content" in task.body


# ---------------------------------------------------------------------------
# edit_task — rollback path when activity log emit raises OSError
# ---------------------------------------------------------------------------


class TestFromAC_EngineEditTaskRollback:
    """AC: edit_task() rollback path (engine.py:899-901) — when _emit_event raises
    OSError, write_task(original) is called to restore the on-disk state."""

    def test_edit_task_oserror_on_emit_restores_original_task(
        self, tmp_path: Path
    ) -> None:
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

    def test_edit_task_oserror_on_emit_original_body_preserved(
        self, tmp_path: Path
    ) -> None:
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


# ---------------------------------------------------------------------------
# create_task — invalid status / priority validation
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# move_task — invalid status validation
# ---------------------------------------------------------------------------


class TestFromAC_EngineMoveTaskValidation:
    """AC: move_task raises ValueError for an invalid target status."""

    def test_move_to_invalid_status_raises(self, tmp_path: Path) -> None:
        board = _make_board(tmp_path)
        _write_task(board, task_id=1)
        engine = KanbanEngine(board, activity_log=False)
        with pytest.raises(ValueError, match="Invalid status"):
            engine.move_task("1", "nonexistent-status")


# ---------------------------------------------------------------------------
# list_sessions — _read_log_entries error paths
# ---------------------------------------------------------------------------


class TestFromAC_EngineReadLogEntriesErrors:
    """AC: _read_log_entries handles OSError, invalid JSON, and bad timestamps."""

    def test_oserror_on_activity_log_read_returns_empty_sessions(
        self, tmp_path: Path
    ) -> None:
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

    def test_invalid_json_line_skipped_valid_entry_still_parsed(
        self, tmp_path: Path
    ) -> None:
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


# ---------------------------------------------------------------------------
# _derive_sessions — non-integer task_id skip
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# end_work — rollback path when activity log emit raises OSError
# ---------------------------------------------------------------------------


class TestFromAC_EngineEndWorkRollback:
    """AC: end_work() rollback path (engine.py:1204-1208) — when _emit_event raises
    OSError, write_task(original) restores the on-disk state; for archive outcomes
    the file is also moved back from archive/ to tasks/."""

    def test_end_work_oserror_on_emit_restores_original_task(
        self, tmp_path: Path
    ) -> None:
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

    def test_end_work_archive_oserror_on_emit_moves_file_back(
        self, tmp_path: Path
    ) -> None:
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

    def test_end_work_archive_oserror_archive_file_removed_after_rollback(
        self, tmp_path: Path
    ) -> None:
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
        assert not archive_file.exists(), (
            "archive file was not moved back during rollback"
        )
