"""Engine-level OCC plumbing tests for task #1341.

Verifies that KanbanEngine.edit_task, move_task, and sweep correctly
wire ``expected_updated`` through to ``storage.write_task_if_unchanged``.

AC coverage:
  AC#1 — engine.edit_task accepts expected_updated; routes to write_task_if_unchanged
  AC#2 — engine.move_task same pattern
  AC#3 — engine.sweep uses write_task_if_unchanged; catches ERR_STALE silently
  AC#6 — callers without expected_updated still work (non-OCC path preserved)
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest import mock

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_kanban.models import ConcurrencyError

_BASE_CONFIG = """\
next_id: 100
"""

_FIXED_UPDATED = "2026-01-01T10:00:00+00:00"

_TASK_TMPL = """\
---
id: {task_id}
title: {title}
status: {status}
priority: important
created: "2026-01-01T10:00:00+00:00"
updated: "{updated}"
tags: []
parent: null
depends_on: []
blocked: false
block_reason: null
claimed_at: {claimed_at}
archival_reason: null
archival_refs: []
---
Task body.
"""


def _make_board(base_dir: Path) -> Path:
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_BASE_CONFIG, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


def _write_task(  # noqa: PLR0913
    kanban_dir: Path,
    task_id: int = 1,
    *,
    title: str = "Task",
    status: str = "todo",
    updated: str = _FIXED_UPDATED,
    claimed_at: str = "null",
) -> Path:
    content = _TASK_TMPL.format(
        task_id=task_id,
        title=title.lower().replace(" ", "-"),
        status=status,
        updated=updated,
        claimed_at=claimed_at,
    )
    slug = title.lower().replace(" ", "-")
    path = kanban_dir / "tasks" / f"{task_id}-{slug}.md"
    path.write_text(content, encoding="utf-8")
    return path


def _make_engine(kanban_dir: Path) -> KanbanEngine:
    return KanbanEngine(kanban_dir, activity_log=False)


# ---------------------------------------------------------------------------
# AC#1: engine.edit_task OCC plumbing
# ---------------------------------------------------------------------------


class TestFromAC_EngineEditTaskOCC:
    """AC#1: engine.edit_task routes expected_updated to write_task_if_unchanged."""

    def test_edit_task_accepts_expected_updated_keyword(self, tmp_path: Path) -> None:
        """engine.edit_task signature includes expected_updated keyword parameter."""
        import inspect

        kanban_dir = _make_board(tmp_path)
        engine = _make_engine(kanban_dir)
        sig = inspect.signature(engine.edit_task)
        assert "expected_updated" in sig.parameters, "engine.edit_task must declare expected_updated parameter"

    def test_edit_task_expected_updated_defaults_to_none(self, tmp_path: Path) -> None:
        """engine.edit_task.expected_updated default is None (optional)."""
        import inspect

        kanban_dir = _make_board(tmp_path)
        engine = _make_engine(kanban_dir)
        sig = inspect.signature(engine.edit_task)
        param = sig.parameters["expected_updated"]
        assert param.default is None, "engine.edit_task.expected_updated must default to None"

    def test_edit_task_matching_token_writes_task(self, tmp_path: Path) -> None:
        """edit_task with correct expected_updated persists the change."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, 1, updated=_FIXED_UPDATED)
        engine = _make_engine(kanban_dir)

        result = engine.edit_task(
            "1",
            expected_updated=_FIXED_UPDATED,
            append_body="new note",
        )

        assert "new note" in (result.body or "")

    def test_edit_task_stale_token_raises_concurrency_error(self, tmp_path: Path) -> None:
        """edit_task with stale expected_updated raises ConcurrencyError."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, 1, updated=_FIXED_UPDATED)
        engine = _make_engine(kanban_dir)

        with pytest.raises(ConcurrencyError):
            engine.edit_task(
                "1",
                expected_updated="2020-01-01T00:00:00+00:00",
                append_body="should not write",
            )

    def test_edit_task_stale_error_has_err_stale_code(self, tmp_path: Path) -> None:
        """ConcurrencyError raised by stale edit_task has code ERR_STALE."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, 1, updated=_FIXED_UPDATED)
        engine = _make_engine(kanban_dir)

        with pytest.raises(ConcurrencyError) as exc_info:
            engine.edit_task(
                "1",
                expected_updated="2020-01-01T00:00:00+00:00",
                append_body="should not write",
            )

        assert exc_info.value.code == "ERR_STALE"

    def test_edit_task_with_token_calls_write_task_if_unchanged(self, tmp_path: Path) -> None:
        """edit_task with expected_updated invokes storage.write_task_if_unchanged."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, 1, updated=_FIXED_UPDATED)
        engine = _make_engine(kanban_dir)
        stale_err = ConcurrencyError("ERR_STALE", "spy intercepted")

        with (
            mock.patch(
                "owlbear_kanban.storage.write_task_if_unchanged",
                side_effect=stale_err,
            ) as mock_cas,
            pytest.raises(ConcurrencyError),
        ):
            engine.edit_task(
                "1",
                expected_updated=_FIXED_UPDATED,
                append_body="note",
            )

        mock_cas.assert_called_once()

    def test_edit_task_without_token_does_not_call_write_task_if_unchanged(self, tmp_path: Path) -> None:
        """edit_task without expected_updated bypasses write_task_if_unchanged (AC#6)."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, 1, updated=_FIXED_UPDATED)
        engine = _make_engine(kanban_dir)

        with mock.patch("owlbear_kanban.storage.write_task_if_unchanged") as mock_cas:
            engine.edit_task("1", append_body="non-occ edit")

        mock_cas.assert_not_called()


# ---------------------------------------------------------------------------
# AC#2: engine.move_task OCC plumbing
# ---------------------------------------------------------------------------


class TestFromAC_EngineMoveTaskOCC:
    """AC#2: engine.move_task routes expected_updated to write_task_if_unchanged."""

    def test_move_task_accepts_expected_updated_keyword(self, tmp_path: Path) -> None:
        """engine.move_task signature includes expected_updated keyword parameter."""
        import inspect

        kanban_dir = _make_board(tmp_path)
        engine = _make_engine(kanban_dir)
        sig = inspect.signature(engine.move_task)
        assert "expected_updated" in sig.parameters, "engine.move_task must declare expected_updated parameter"

    def test_move_task_expected_updated_defaults_to_none(self, tmp_path: Path) -> None:
        """engine.move_task.expected_updated default is None (optional)."""
        import inspect

        kanban_dir = _make_board(tmp_path)
        engine = _make_engine(kanban_dir)
        sig = inspect.signature(engine.move_task)
        param = sig.parameters["expected_updated"]
        assert param.default is None, "engine.move_task.expected_updated must default to None"

    def test_move_task_matching_token_changes_status(self, tmp_path: Path) -> None:
        """move_task with correct expected_updated persists the new status."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, 1, status="todo", updated=_FIXED_UPDATED)
        engine = _make_engine(kanban_dir)

        result = engine.move_task(
            "1",
            "in-progress",
            expected_updated=_FIXED_UPDATED,
        )

        assert result.status == "in-progress"

    def test_move_task_stale_token_raises_concurrency_error(self, tmp_path: Path) -> None:
        """move_task with stale expected_updated raises ConcurrencyError."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, 1, status="todo", updated=_FIXED_UPDATED)
        engine = _make_engine(kanban_dir)

        with pytest.raises(ConcurrencyError):
            engine.move_task(
                "1",
                "in-progress",
                expected_updated="2020-01-01T00:00:00+00:00",
            )

    def test_move_task_stale_error_code_is_err_stale(self, tmp_path: Path) -> None:
        """ConcurrencyError raised by stale move_task has code ERR_STALE."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, 1, status="todo", updated=_FIXED_UPDATED)
        engine = _make_engine(kanban_dir)

        with pytest.raises(ConcurrencyError) as exc_info:
            engine.move_task(
                "1",
                "in-progress",
                expected_updated="2020-01-01T00:00:00+00:00",
            )

        assert exc_info.value.code == "ERR_STALE"

    def test_move_task_with_token_calls_write_task_if_unchanged(self, tmp_path: Path) -> None:
        """move_task with expected_updated invokes storage.write_task_if_unchanged."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, 1, status="todo", updated=_FIXED_UPDATED)
        engine = _make_engine(kanban_dir)
        stale_err = ConcurrencyError("ERR_STALE", "spy intercepted")

        with (
            mock.patch(
                "owlbear_kanban.storage.write_task_if_unchanged",
                side_effect=stale_err,
            ) as mock_cas,
            pytest.raises(ConcurrencyError),
        ):
            engine.move_task(
                "1",
                "in-progress",
                expected_updated=_FIXED_UPDATED,
            )

        mock_cas.assert_called_once()


# ---------------------------------------------------------------------------
# AC#3: engine.sweep OCC plumbing
# ---------------------------------------------------------------------------


class TestFromAC_EngineSweepOCC:
    """AC#3: engine.sweep uses write_task_if_unchanged; catches ERR_STALE silently."""

    def _expired_ts(self) -> str:
        return (datetime.now(tz=UTC) - timedelta(hours=2)).isoformat()

    def test_sweep_calls_write_task_if_unchanged_for_expired_claim(self, tmp_path: Path) -> None:
        """sweep invokes write_task_if_unchanged when clearing an expired claim."""
        kanban_dir = _make_board(tmp_path)
        _write_task(
            kanban_dir,
            1,
            claimed_at=f'"{self._expired_ts()}"',
            updated=_FIXED_UPDATED,
        )
        engine = _make_engine(kanban_dir)

        with mock.patch(
            "owlbear_kanban.storage.write_task_if_unchanged",
        ) as mock_cas:
            engine.sweep()

        mock_cas.assert_called_once()

    def test_sweep_err_stale_does_not_raise(self, tmp_path: Path) -> None:
        """sweep catches ConcurrencyError ERR_STALE and does not re-raise it."""
        kanban_dir = _make_board(tmp_path)
        _write_task(
            kanban_dir,
            1,
            claimed_at=f'"{self._expired_ts()}"',
            updated=_FIXED_UPDATED,
        )
        engine = _make_engine(kanban_dir)
        stale_err = ConcurrencyError("ERR_STALE", "concurrent modification")

        with mock.patch(
            "owlbear_kanban.storage.write_task_if_unchanged",
            side_effect=stale_err,
        ):
            # Must not raise
            released = engine.sweep()

        assert isinstance(released, list)

    def test_sweep_err_stale_task_excluded_from_released_list(self, tmp_path: Path) -> None:
        """sweep does not include a ERR_STALE task in the returned released list."""
        kanban_dir = _make_board(tmp_path)
        _write_task(
            kanban_dir,
            1,
            claimed_at=f'"{self._expired_ts()}"',
            updated=_FIXED_UPDATED,
        )
        engine = _make_engine(kanban_dir)
        stale_err = ConcurrencyError("ERR_STALE", "concurrent modification")

        with mock.patch(
            "owlbear_kanban.storage.write_task_if_unchanged",
            side_effect=stale_err,
        ):
            released = engine.sweep()

        assert 1 not in released

    def test_sweep_continues_after_err_stale_releases_subsequent_tasks(self, tmp_path: Path) -> None:
        """sweep continues processing remaining expired tasks after an ERR_STALE."""
        kanban_dir = _make_board(tmp_path)
        expired = self._expired_ts()
        _write_task(
            kanban_dir,
            1,
            claimed_at=f'"{expired}"',
            updated=_FIXED_UPDATED,
        )
        _write_task(
            kanban_dir,
            2,
            title="Task Two",
            claimed_at=f'"{expired}"',
            updated=_FIXED_UPDATED,
        )
        engine = _make_engine(kanban_dir)
        stale_err = ConcurrencyError("ERR_STALE", "concurrent modification")

        with mock.patch(
            "owlbear_kanban.storage.write_task_if_unchanged",
            side_effect=[stale_err, mock.DEFAULT],
        ) as mock_cas:
            released = engine.sweep()

        assert mock_cas.call_count == 2
        assert 1 not in released
        assert 2 in released


# ---------------------------------------------------------------------------
# AC#6: non-OCC callers (no expected_updated) continue to work
# ---------------------------------------------------------------------------


class TestFromAC_EngineNonOCCPathPreserved:
    """AC#6: existing callers without expected_updated continue to work."""

    def test_edit_task_without_expected_updated_persists_change(self, tmp_path: Path) -> None:
        """edit_task without expected_updated still writes the task (non-OCC path)."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, 1, updated=_FIXED_UPDATED)
        engine = _make_engine(kanban_dir)

        result = engine.edit_task("1", priority="someday")

        assert result.priority == "someday"

    def test_move_task_without_expected_updated_changes_status(self, tmp_path: Path) -> None:
        """move_task without expected_updated still changes status (non-OCC path)."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, 1, status="todo", updated=_FIXED_UPDATED)
        engine = _make_engine(kanban_dir)

        result = engine.move_task("1", "in-progress")

        assert result.status == "in-progress"

    def test_edit_task_none_expected_updated_does_not_raise_on_fresh_task(self, tmp_path: Path) -> None:
        """Explicitly passing expected_updated=None uses the non-OCC path."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, 1, updated=_FIXED_UPDATED)
        engine = _make_engine(kanban_dir)

        # Should succeed without raising
        result = engine.edit_task("1", expected_updated=None, append_body="no-occ")

        assert "no-occ" in (result.body or "")

    def test_move_task_none_expected_updated_does_not_raise(self, tmp_path: Path) -> None:
        """Explicitly passing expected_updated=None to move_task uses non-OCC path."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, 1, status="todo", updated=_FIXED_UPDATED)
        engine = _make_engine(kanban_dir)

        result = engine.move_task("1", "in-progress", expected_updated=None)

        assert result.status == "in-progress"
