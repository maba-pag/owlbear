"""Failing tests for engine write-before-log atomicity (#1104).

All 6 engine mutators follow write_task() then _emit_event(). If
append_activity_event() raises after the task write, board state is changed
but the activity event is missing.  These tests assert the EXPECTED rollback
behaviour: each mutator must restore the pre-mutation task state when the emit
fails and re-raise the original exception.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_kanban.storage import read_task

# ---------------------------------------------------------------------------
# Board / task scaffolding
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
next_id: 1001
"""

_TASK_TEMPLATE = """\
---
id: {task_id}
title: Task {task_id}
status: {status}
priority: needed
created: "2026-04-21T10:00:00+00:00"
updated: "2026-04-21T10:00:00+00:00"
tags: []
parent: null
depends_on: []
blocked: false
block_reason: null
claimed_at: {claimed_at_value}
archival_reason: null
archival_refs: []
---

## Notes

Content for task {task_id}.
"""

# An epoch-past timestamp guaranteed to be beyond the 1-hour claim_timeout.
_EXPIRED_CLAIMED_AT = "2026-01-01T00:00:00+00:00"

_EMIT_PATCH = "owlbear_kanban.activity_store.append_activity_event"


def _make_board(base_dir: Path) -> Path:
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


def _make_task_file(
    kanban_dir: Path,
    task_id: int,
    status: str = "todo",
    claimed_at: str | None = None,
) -> Path:
    claimed_at_value = f'"{claimed_at}"' if claimed_at else "null"
    content = _TASK_TEMPLATE.format(
        task_id=task_id,
        status=status,
        claimed_at_value=claimed_at_value,
    )
    path = kanban_dir / "tasks" / f"{task_id}-task.md"
    path.write_text(content, encoding="utf-8")
    return path


def _activity_line_count(kanban_dir: Path) -> int:
    log = kanban_dir / "activity.jsonl"
    if not log.exists():
        return 0
    return sum(1 for ln in log.read_text(encoding="utf-8").splitlines() if ln.strip())


def _assert_no_activity_written(kanban_dir: Path) -> None:
    """Assert activity.jsonl has no entries after a failed emit."""
    log = kanban_dir / "activity.jsonl"
    if not log.exists():
        return
    lines = [ln for ln in log.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert lines == [], f"Expected 0 activity entries, got {len(lines)}"


def _assert_all_valid_json(kanban_dir: Path, expected_count: int) -> None:
    """Assert activity.jsonl has exactly expected_count well-formed JSON lines."""
    log = kanban_dir / "activity.jsonl"
    lines = [ln for ln in log.read_text(encoding="utf-8").splitlines() if ln.strip()] if log.exists() else []
    assert len(lines) == expected_count, f"Expected {expected_count} lines, got {len(lines)}"
    for ln in lines:
        json.loads(ln)  # raises JSONDecodeError if malformed


# ---------------------------------------------------------------------------
# TestFromAC_EngineAtomicity
# ---------------------------------------------------------------------------


class TestFromAC_EngineAtomicity:
    """AC #1104: engine mutators roll back task state when _emit_event fails."""

    # --- edit_task -----------------------------------------------------------

    def test_edit_task_emit_failure_rollback(self, tmp_path: Path) -> None:
        """edit_task: OSError from emit must propagate; task title stays unchanged."""
        kanban_dir = _make_board(tmp_path)
        task_path = _make_task_file(kanban_dir, 1001, status="todo")
        engine = KanbanEngine(kanban_dir)
        before = read_task(task_path)

        with (
            patch(_EMIT_PATCH, side_effect=OSError("disk full")),
            pytest.raises(OSError, match="disk full"),
        ):
            engine.edit_task("1001", title="Mutated Title")

        after = read_task(task_path)
        assert after.title == before.title, "title must be rolled back on emit failure"
        assert after.updated == before.updated, "updated timestamp must be rolled back"
        _assert_no_activity_written(kanban_dir)

    def test_edit_task_emit_failure_body_rollback(self, tmp_path: Path) -> None:
        """edit_task with append_body: OSError must propagate; body stays unchanged."""
        kanban_dir = _make_board(tmp_path)
        task_path = _make_task_file(kanban_dir, 1001, status="todo")
        engine = KanbanEngine(kanban_dir)
        before = read_task(task_path)

        with (
            patch(_EMIT_PATCH, side_effect=OSError("disk full")),
            pytest.raises(OSError, match="disk full"),
        ):
            engine.edit_task("1001", append_body="injected note")

        after = read_task(task_path)
        assert after.body == before.body, "body must be rolled back on emit failure"
        _assert_no_activity_written(kanban_dir)

    # --- move_task (non-archive) ---------------------------------------------

    def test_move_task_emit_failure_status_rollback(self, tmp_path: Path) -> None:
        """move_task (non-archive): OSError must propagate; status stays unchanged."""
        kanban_dir = _make_board(tmp_path)
        task_path = _make_task_file(kanban_dir, 1001, status="todo")
        engine = KanbanEngine(kanban_dir)
        before = read_task(task_path)

        with (
            patch(_EMIT_PATCH, side_effect=OSError("disk full")),
            pytest.raises(OSError, match="disk full"),
        ):
            engine.move_task("1001", "in-progress")

        after = read_task(task_path)
        assert after.status == before.status, "status must be rolled back on emit failure"
        _assert_no_activity_written(kanban_dir)

    # --- move_task (archive path) --------------------------------------------

    def test_move_task_archive_emit_failure_file_stays_in_tasks(self, tmp_path: Path) -> None:
        """move_task to 'archived': OSError must propagate; file must NOT move to archive/."""
        kanban_dir = _make_board(tmp_path)
        task_path = _make_task_file(kanban_dir, 1001, status="done")
        engine = KanbanEngine(kanban_dir)
        before = read_task(task_path)

        with (
            patch(_EMIT_PATCH, side_effect=OSError("disk full")),
            pytest.raises(OSError, match="disk full"),
        ):
            engine.move_task("1001", "archived", archival_reason="completed")

        assert task_path.exists(), "task file must not be moved to archive/ on emit failure"
        archive_contents = [f for f in (kanban_dir / "archive").iterdir() if f.suffix == ".md"]
        assert archive_contents == [], "archive/ must have no .md task files after failed archive move"
        after = read_task(task_path)
        assert after.status == before.status, "status must be rolled back (not 'archived')"
        _assert_no_activity_written(kanban_dir)

    # --- claim_task ----------------------------------------------------------

    def test_claim_task_emit_failure_rollback(self, tmp_path: Path) -> None:
        """claim_task: OSError must propagate; claimed_at must be rolled back to null."""
        kanban_dir = _make_board(tmp_path)
        task_path = _make_task_file(kanban_dir, 1001, status="todo")
        engine = KanbanEngine(kanban_dir)
        before = read_task(task_path)
        assert before.claimed_at is None

        with (
            patch(_EMIT_PATCH, side_effect=OSError("disk full")),
            pytest.raises(OSError, match="disk full"),
        ):
            engine.claim_task("1001")

        after = read_task(task_path)
        assert after.claimed_at is None, "claimed_at must be null after rolled-back claim"
        _assert_no_activity_written(kanban_dir)

    # --- end_work (non-archive) ----------------------------------------------

    def test_end_work_emit_failure_status_rollback(self, tmp_path: Path) -> None:
        """end_work (success, non-archive): OSError must propagate; status must not advance."""
        claimed_at = "2026-04-22T10:00:00+00:00"
        kanban_dir = _make_board(tmp_path)
        task_path = _make_task_file(kanban_dir, 1001, status="in-progress", claimed_at=claimed_at)
        engine = KanbanEngine(kanban_dir)
        before = read_task(task_path)

        with (
            patch(_EMIT_PATCH, side_effect=OSError("disk full")),
            pytest.raises(OSError, match="disk full"),
        ):
            engine.end_work("1001", note="Work done", outcome="success")

        after = read_task(task_path)
        assert after.status == before.status, "status must not advance on emit failure"
        assert after.claimed_at == before.claimed_at, "claimed_at must be rolled back"
        _assert_no_activity_written(kanban_dir)

    def test_end_work_emit_failure_body_rollback(self, tmp_path: Path) -> None:
        """end_work: OSError must propagate; note must not be appended to body."""
        claimed_at = "2026-04-22T10:00:00+00:00"
        kanban_dir = _make_board(tmp_path)
        task_path = _make_task_file(kanban_dir, 1001, status="in-progress", claimed_at=claimed_at)
        engine = KanbanEngine(kanban_dir)
        before = read_task(task_path)

        with (
            patch(_EMIT_PATCH, side_effect=OSError("disk full")),
            pytest.raises(OSError, match="disk full"),
        ):
            engine.end_work("1001", note="Secret note", outcome="fail")

        after = read_task(task_path)
        assert "Secret note" not in str(after.body), "appended note must be rolled back"
        assert after.body == before.body, "body must be fully restored"
        _assert_no_activity_written(kanban_dir)

    # --- end_work (archive path) ---------------------------------------------

    def test_end_work_archive_emit_failure_file_stays_in_tasks(self, tmp_path: Path) -> None:
        """end_work (success from 'done'): OSError must propagate; file must NOT move to archive/."""
        claimed_at = "2026-04-22T10:00:00+00:00"
        kanban_dir = _make_board(tmp_path)
        task_path = _make_task_file(kanban_dir, 1001, status="done", claimed_at=claimed_at)
        engine = KanbanEngine(kanban_dir)
        before = read_task(task_path)

        with (
            patch(_EMIT_PATCH, side_effect=OSError("disk full")),
            pytest.raises(OSError, match="disk full"),
        ):
            engine.end_work("1001", note="Archiving", outcome="success")

        assert task_path.exists(), "task file must not be moved to archive/ on emit failure"
        archive_contents = list((kanban_dir / "archive").iterdir())
        assert archive_contents == [], "archive/ must be empty after failed archive end_work"
        after = read_task(task_path)
        assert after.status == before.status, "status must be rolled back (not 'archived')"
        _assert_no_activity_written(kanban_dir)

    # --- release_task --------------------------------------------------------

    def test_release_task_emit_failure_rollback(self, tmp_path: Path) -> None:
        """release_task: OSError must propagate; claimed_at must be restored."""
        claimed_at = "2026-04-22T10:00:00+00:00"
        kanban_dir = _make_board(tmp_path)
        task_path = _make_task_file(kanban_dir, 1001, status="in-progress", claimed_at=claimed_at)
        engine = KanbanEngine(kanban_dir)
        before = read_task(task_path)
        assert before.claimed_at is not None

        with (
            patch(_EMIT_PATCH, side_effect=OSError("disk full")),
            pytest.raises(OSError, match="disk full"),
        ):
            engine.release_task("1001")

        after = read_task(task_path)
        assert after.claimed_at == before.claimed_at, "claimed_at must be restored to pre-release value on emit failure"
        _assert_no_activity_written(kanban_dir)

    # --- sweep (partial per-task rollback) -----------------------------------

    def test_sweep_second_task_emit_failure_per_task_rollback(self, tmp_path: Path) -> None:
        """sweep: emit failure on 2nd task must roll back that task; loop must continue."""
        kanban_dir = _make_board(tmp_path)

        # Task 1001 and 1002 both have expired claims.
        # Task 1003: fresh, no expired claim — visited by loop but not swept.
        task1_path = _make_task_file(kanban_dir, 1001, status="in-progress", claimed_at=_EXPIRED_CLAIMED_AT)
        task2_path = _make_task_file(kanban_dir, 1002, status="in-progress", claimed_at=_EXPIRED_CLAIMED_AT)
        _make_task_file(kanban_dir, 1003, status="todo")
        engine = KanbanEngine(kanban_dir)
        before2 = read_task(task2_path)

        # First emit call (task 1001) succeeds; second (task 1002) fails.
        emit_mock = Mock(side_effect=[None, OSError("disk full")])
        with patch(_EMIT_PATCH, emit_mock):
            # sweep() must NOT raise — per-task failures must be absorbed by the loop.
            released = engine.sweep()

        # Task 1001: claim released, included in return list.
        after1 = read_task(task1_path)
        assert after1.claimed_at is None, "task 1001 claim must be released"
        assert 1001 in released, "task 1001 must appear in sweep() return list"

        # Task 1002: rolled back — claim must still be present, excluded from return list.
        after2 = read_task(task2_path)
        assert after2.claimed_at == before2.claimed_at, "task 1002 claimed_at must be restored after emit failure"
        assert 1002 not in released, "task 1002 must NOT appear in sweep() return list"

        # Loop continued: task 1003 was visited (no crash, fresh task unmodified).
        task3_path = kanban_dir / "tasks" / "1003-task.md"
        assert task3_path.exists(), "task 1003 must be unaffected (loop continued past error)"

    def test_sweep_second_task_emit_failure_activity_log_integrity(self, tmp_path: Path) -> None:
        """sweep: activity.jsonl must contain only complete, valid JSON lines after partial failure."""
        kanban_dir = _make_board(tmp_path)
        _make_task_file(kanban_dir, 1001, status="in-progress", claimed_at=_EXPIRED_CLAIMED_AT)
        _make_task_file(kanban_dir, 1002, status="in-progress", claimed_at=_EXPIRED_CLAIMED_AT)
        engine = KanbanEngine(kanban_dir)

        # Let the real append_activity_event run for task 1001 only;
        # fail on task 1002.
        real_append_calls: list[object] = []

        from owlbear_kanban.activity_store import append_activity_event as _real_append  # noqa: PLC0415

        def _side_effect(event: object, kanban_dir: Path) -> None:  # type: ignore[misc]
            real_append_calls.append(event)
            if len(real_append_calls) == 1:
                _real_append(event, kanban_dir)  # type: ignore[arg-type]
            else:
                msg = "disk full"
                raise OSError(msg)

        with patch(_EMIT_PATCH, side_effect=_side_effect):
            engine.sweep()

        # Exactly 1 valid JSON entry in the log (for task 1001 only).
        _assert_all_valid_json(kanban_dir, expected_count=1)
        log = kanban_dir / "activity.jsonl"
        entry = json.loads(log.read_text(encoding="utf-8").strip())
        assert entry["task_id"] == 1001, "only task 1001's event may be in the log"
        assert entry["action"] == "sweep-release"

    # --- Full snapshot equality: edit_task ---

    def test_edit_task_emit_failure_full_snapshot_equality(self, tmp_path: Path) -> None:
        """edit_task: rollback must restore the complete Task model, not just selected fields."""
        kanban_dir = _make_board(tmp_path)
        task_path = _make_task_file(kanban_dir, 1001, status="todo")
        engine = KanbanEngine(kanban_dir)
        before = read_task(task_path)

        with (
            patch(_EMIT_PATCH, side_effect=OSError("disk full")),
            pytest.raises(OSError, match="disk full"),
        ):
            engine.edit_task("1001", title="Mutated Title", append_body="injected note")

        after = read_task(task_path)
        assert after.model_dump() == before.model_dump(), (
            "full Task model must be identical to pre-mutation snapshot after emit-failure rollback"
        )
        _assert_no_activity_written(kanban_dir)

    # --- Full snapshot equality: move_task (non-archive) ---

    def test_move_task_emit_failure_full_snapshot_equality(self, tmp_path: Path) -> None:
        """move_task (non-archive): rollback must restore the complete Task model."""
        kanban_dir = _make_board(tmp_path)
        task_path = _make_task_file(kanban_dir, 1001, status="todo")
        engine = KanbanEngine(kanban_dir)
        before = read_task(task_path)

        with (
            patch(_EMIT_PATCH, side_effect=OSError("disk full")),
            pytest.raises(OSError, match="disk full"),
        ):
            engine.move_task("1001", "in-progress")

        after = read_task(task_path)
        assert after.model_dump() == before.model_dump(), (
            "full Task model must be identical to pre-mutation snapshot after emit-failure rollback"
        )
        _assert_no_activity_written(kanban_dir)

    # --- Full snapshot equality: claim_task ---

    def test_claim_task_emit_failure_full_snapshot_equality(self, tmp_path: Path) -> None:
        """claim_task: rollback must restore the complete Task model (claimed_at, updated, etc.)."""
        kanban_dir = _make_board(tmp_path)
        task_path = _make_task_file(kanban_dir, 1001, status="todo")
        engine = KanbanEngine(kanban_dir)
        before = read_task(task_path)

        with (
            patch(_EMIT_PATCH, side_effect=OSError("disk full")),
            pytest.raises(OSError, match="disk full"),
        ):
            engine.claim_task("1001")

        after = read_task(task_path)
        assert after.model_dump() == before.model_dump(), (
            "full Task model must be identical to pre-mutation snapshot after emit-failure rollback"
        )
        _assert_no_activity_written(kanban_dir)

    # --- Full snapshot equality: release_task ---

    def test_release_task_emit_failure_full_snapshot_equality(self, tmp_path: Path) -> None:
        """release_task: rollback must restore the complete Task model (claimed_at, updated, etc.)."""
        claimed_at = "2026-04-22T10:00:00+00:00"
        kanban_dir = _make_board(tmp_path)
        task_path = _make_task_file(kanban_dir, 1001, status="in-progress", claimed_at=claimed_at)
        engine = KanbanEngine(kanban_dir)
        before = read_task(task_path)

        with (
            patch(_EMIT_PATCH, side_effect=OSError("disk full")),
            pytest.raises(OSError, match="disk full"),
        ):
            engine.release_task("1001")

        after = read_task(task_path)
        assert after.model_dump() == before.model_dump(), (
            "full Task model must be identical to pre-mutation snapshot after emit-failure rollback"
        )
        _assert_no_activity_written(kanban_dir)

    # --- Full snapshot equality: end_work (non-archive) ---

    def test_end_work_emit_failure_full_snapshot_equality(self, tmp_path: Path) -> None:
        """end_work: rollback must restore the complete Task model (status, body, claimed_at, updated)."""
        claimed_at = "2026-04-22T10:00:00+00:00"
        kanban_dir = _make_board(tmp_path)
        task_path = _make_task_file(kanban_dir, 1001, status="in-progress", claimed_at=claimed_at)
        engine = KanbanEngine(kanban_dir)
        before = read_task(task_path)

        with (
            patch(_EMIT_PATCH, side_effect=OSError("disk full")),
            pytest.raises(OSError, match="disk full"),
        ):
            engine.end_work("1001", note="Work done", outcome="success")

        after = read_task(task_path)
        assert after.model_dump() == before.model_dump(), (
            "full Task model must be identical to pre-mutation snapshot after emit-failure rollback"
        )
        _assert_no_activity_written(kanban_dir)

    # --- Full snapshot equality: sweep per-task rollback ---

    def test_sweep_second_task_emit_failure_full_snapshot_equality(self, tmp_path: Path) -> None:
        """sweep: rolled-back task must have complete model equality with its pre-sweep snapshot."""
        kanban_dir = _make_board(tmp_path)
        _make_task_file(kanban_dir, 1001, status="in-progress", claimed_at=_EXPIRED_CLAIMED_AT)
        task2_path = _make_task_file(kanban_dir, 1002, status="in-progress", claimed_at=_EXPIRED_CLAIMED_AT)
        engine = KanbanEngine(kanban_dir)
        before2 = read_task(task2_path)

        emit_mock = Mock(side_effect=[None, OSError("disk full")])
        with patch(_EMIT_PATCH, emit_mock):
            engine.sweep()

        after2 = read_task(task2_path)
        assert after2.model_dump() == before2.model_dump(), (
            "full Task model must be identical to pre-sweep snapshot after per-task emit-failure rollback"
        )

    # --- Sweep continuation: 3 expired tasks prove the loop continues past 2nd failure ---

    def test_sweep_continues_after_second_emit_failure_third_task_released(self, tmp_path: Path) -> None:
        """sweep: after 2nd task emit failure and rollback, 3rd expired task must still be swept."""
        kanban_dir = _make_board(tmp_path)
        _make_task_file(kanban_dir, 1001, status="in-progress", claimed_at=_EXPIRED_CLAIMED_AT)
        _make_task_file(kanban_dir, 1002, status="in-progress", claimed_at=_EXPIRED_CLAIMED_AT)
        task3_path = _make_task_file(kanban_dir, 1003, status="in-progress", claimed_at=_EXPIRED_CLAIMED_AT)
        engine = KanbanEngine(kanban_dir)

        # emit call 1 (task 1001) succeeds; call 2 (task 1002) fails; call 3 (task 1003) succeeds.
        emit_mock = Mock(side_effect=[None, OSError("disk full"), None])
        with patch(_EMIT_PATCH, emit_mock):
            released = engine.sweep()

        # Task 1003 must appear in released: proves the loop continued past the 1002 emit failure.
        assert 1003 in released, "task 1003 must be swept: loop must continue after 2nd task emit failure"
        after3 = read_task(task3_path)
        assert after3.claimed_at is None, "task 1003 claimed_at must be cleared: loop continued and processed it"
        # Task 1002 must NOT be released (its emit failed and was rolled back).
        assert 1002 not in released, "task 1002 must not appear in released list (emit failed)"

    # --- Full snapshot equality: move_task (archive path) ---

    def test_move_task_archive_emit_failure_full_snapshot_equality(self, tmp_path: Path) -> None:
        """move_task to 'archived': rollback must restore the complete Task model, not just status."""
        kanban_dir = _make_board(tmp_path)
        task_path = _make_task_file(kanban_dir, 1001, status="done")
        engine = KanbanEngine(kanban_dir)
        before = read_task(task_path)

        with (
            patch(_EMIT_PATCH, side_effect=OSError("disk full")),
            pytest.raises(OSError, match="disk full"),
        ):
            engine.move_task("1001", "archived", archival_reason="completed")

        # File must be back in tasks/ (already covered by existing test; verified again for context)
        assert task_path.exists(), "task file must remain in tasks/ after archive rollback"
        after = read_task(task_path)
        assert after.model_dump() == before.model_dump(), (
            "full Task model must be identical to pre-mutation snapshot after archive emit-failure rollback"
        )
        _assert_no_activity_written(kanban_dir)

    # --- Full snapshot equality: end_work (archive path) ---

    def test_end_work_archive_emit_failure_full_snapshot_equality(self, tmp_path: Path) -> None:
        """end_work (success from 'done'): rollback must restore the complete Task model."""
        claimed_at = "2026-04-22T10:00:00+00:00"
        kanban_dir = _make_board(tmp_path)
        task_path = _make_task_file(kanban_dir, 1001, status="done", claimed_at=claimed_at)
        engine = KanbanEngine(kanban_dir)
        before = read_task(task_path)

        with (
            patch(_EMIT_PATCH, side_effect=OSError("disk full")),
            pytest.raises(OSError, match="disk full"),
        ):
            engine.end_work("1001", note="Archive note", outcome="success")

        # File must be back in tasks/ (already covered by existing test; verified again for context)
        assert task_path.exists(), "task file must remain in tasks/ after archive rollback"
        archive_contents = list((kanban_dir / "archive").iterdir())
        assert archive_contents == [], "archive/ must be empty after archive rollback"
        after = read_task(task_path)
        assert after.model_dump() == before.model_dump(), (
            "full Task model (body, status, claimed_at, updated, etc.) must be identical "
            "to pre-mutation snapshot after archive emit-failure rollback"
        )
        _assert_no_activity_written(kanban_dir)

    # --- end_work block/reject outcome rollback (AC addendum, loop-breaker 3) ---

    def test_end_work_block_emit_failure_rollback(self, tmp_path: Path) -> None:
        """end_work (block): OSError from emit must propagate; blocked/block_reason/body/claimed_at must be rolled back."""
        claimed_at = "2026-04-22T10:00:00+00:00"
        kanban_dir = _make_board(tmp_path)
        task_path = _make_task_file(kanban_dir, 1001, status="in-progress", claimed_at=claimed_at)
        engine = KanbanEngine(kanban_dir)
        before = read_task(task_path)
        assert before.blocked is False
        assert before.block_reason is None

        with (
            patch(_EMIT_PATCH, side_effect=OSError("disk full")),
            pytest.raises(OSError, match="disk full"),
        ):
            engine.end_work(
                "1001",
                note="Blocked on dependency",
                outcome="block",
                block_reason="waiting for user",
            )

        after = read_task(task_path)
        assert after.blocked is False, "blocked must be rolled back to False on emit failure"
        assert after.block_reason is None, "block_reason must be rolled back to None on emit failure"
        assert after.status == before.status, "status must be unchanged on emit failure"
        assert after.body == before.body, "body must be rolled back (note not appended)"
        assert after.claimed_at == before.claimed_at, "claimed_at must be restored on emit failure"
        _assert_no_activity_written(kanban_dir)

    def test_end_work_reject_emit_failure_rollback(self, tmp_path: Path) -> None:
        """end_work (reject): OSError from emit must propagate; status/body/claimed_at must be rolled back."""
        claimed_at = "2026-04-22T10:00:00+00:00"
        kanban_dir = _make_board(tmp_path)
        task_path = _make_task_file(kanban_dir, 1001, status="in-progress", claimed_at=claimed_at)
        engine = KanbanEngine(kanban_dir)
        before = read_task(task_path)

        with (
            patch(_EMIT_PATCH, side_effect=OSError("disk full")),
            pytest.raises(OSError, match="disk full"),
        ):
            engine.end_work("1001", note="Rejected back", outcome="reject", move_to="research")

        after = read_task(task_path)
        assert after.status == before.status, "status must not change to 'research' on emit failure"
        assert after.body == before.body, "body must be rolled back (note not appended)"
        assert after.claimed_at == before.claimed_at, "claimed_at must be restored on emit failure"
        _assert_no_activity_written(kanban_dir)

    # --- Full snapshot equality: end_work block/reject outcome ---

    def test_end_work_block_emit_failure_full_snapshot_equality(self, tmp_path: Path) -> None:
        """end_work (block): rollback must restore the complete Task model (blocked, block_reason, body, claimed_at, etc.)."""
        claimed_at = "2026-04-22T10:00:00+00:00"
        kanban_dir = _make_board(tmp_path)
        task_path = _make_task_file(kanban_dir, 1001, status="in-progress", claimed_at=claimed_at)
        engine = KanbanEngine(kanban_dir)
        before = read_task(task_path)

        with (
            patch(_EMIT_PATCH, side_effect=OSError("disk full")),
            pytest.raises(OSError, match="disk full"),
        ):
            engine.end_work(
                "1001",
                note="Blocked on dependency",
                outcome="block",
                block_reason="waiting for user",
            )

        after = read_task(task_path)
        assert after.model_dump() == before.model_dump(), (
            "full Task model must be identical to pre-mutation snapshot after block emit-failure rollback"
        )
        _assert_no_activity_written(kanban_dir)

    def test_end_work_reject_emit_failure_full_snapshot_equality(self, tmp_path: Path) -> None:
        """end_work (reject): rollback must restore the complete Task model (status, body, claimed_at, etc.)."""
        claimed_at = "2026-04-22T10:00:00+00:00"
        kanban_dir = _make_board(tmp_path)
        task_path = _make_task_file(kanban_dir, 1001, status="in-progress", claimed_at=claimed_at)
        engine = KanbanEngine(kanban_dir)
        before = read_task(task_path)

        with (
            patch(_EMIT_PATCH, side_effect=OSError("disk full")),
            pytest.raises(OSError, match="disk full"),
        ):
            engine.end_work("1001", note="Rejected back", outcome="reject", move_to="research")

        after = read_task(task_path)
        assert after.model_dump() == before.model_dump(), (
            "full Task model must be identical to pre-mutation snapshot after reject emit-failure rollback"
        )
        _assert_no_activity_written(kanban_dir)

    # --- create_task emit-failure rollback (AC-7, retry cycle 3) ----------------

    def test_create_task_emit_failure_rollback(self, tmp_path: Path) -> None:
        """create_task: OSError from emit must propagate; task file must be deleted and no activity written."""
        kanban_dir = _make_board(tmp_path)
        _make_task_file(kanban_dir, 1001, status="todo")
        engine = KanbanEngine(kanban_dir)
        tasks_before = {f.name for f in (kanban_dir / "tasks").iterdir()}

        with (
            patch(_EMIT_PATCH, side_effect=OSError("disk full")),
            pytest.raises(OSError, match="disk full"),
        ):
            engine.create_task("Rollback Target")

        tasks_after = {f.name for f in (kanban_dir / "tasks").iterdir()}
        assert tasks_after == tasks_before, "tasks/ must have no new file after failed create_task emit"
        _assert_no_activity_written(kanban_dir)

    def test_create_task_emit_failure_task_not_in_index(self, tmp_path: Path) -> None:
        """create_task: after emit-failure rollback, the failed task must not appear in list_tasks()."""
        kanban_dir = _make_board(tmp_path)
        engine = KanbanEngine(kanban_dir)

        with (
            patch(_EMIT_PATCH, side_effect=OSError("disk full")),
            pytest.raises(OSError, match="disk full"),
        ):
            engine.create_task("Ghost Task")

        tasks = engine.list_tasks()
        task_titles = [t.title for t in tasks]
        assert "Ghost Task" not in task_titles, "failed create_task must not leave a ghost entry in the task index"
