"""Release-task OCC regression tests.

Promoted from the task-scoped suite for task #1133.

AC coverage preserved from the task-scoped suite:
  ac1-sig       — engine.release_task accepts optional expected_updated (default None)
  ac2-cas-write — claimed task + fresh token → write_task_if_unchanged, claim cleared
  ac3-stale     — claimed task + stale token → ConcurrencyError(ERR_STALE)
  ac4-lww       — expected_updated=None → LWW behavior unchanged, claim cleared
  ac5-noop-stale — unclaimed + stale token → ConcurrencyError(ERR_STALE)
  ac5-noop-fresh — unclaimed + fresh token → silent no-op, updated NOT advanced
  ac6-facade-sig — CockpitView.release_task requires expected_updated (no default)
  ac6-facade-ok  — CockpitView: fresh token + claimed → claim cleared
  ac6-facade-err — CockpitView: stale token propagates ConcurrencyError(ERR_STALE)
  ac6-facade-noop-fresh — CockpitView: unclaimed + fresh token → no-op
  ac6-facade-noop-stale — CockpitView: unclaimed + stale token → ConcurrencyError(ERR_STALE)
"""

from __future__ import annotations

import inspect
from pathlib import Path
from unittest import mock

import pytest

from owlbear_cockpit.view import CockpitView
from owlbear_kanban import KanbanEngine
from owlbear_kanban.models import ConcurrencyError, SingleTaskResponse

# Provenance: promoted from task-scoped suite for task #1133.

# ---------------------------------------------------------------------------
# Board / task helpers
# ---------------------------------------------------------------------------

_BASE_CONFIG = """\
next_id: 100
"""

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
    task_id: int,
    title: str = "Task",
    status: str = "research",
    updated: str = "2026-01-01T10:00:00+00:00",
    claimed_at: str = "null",
) -> Path:
    safe_title = title.lower().replace(" ", "-")
    filename = f"{task_id}-{safe_title}.md"
    path = kanban_dir / "tasks" / filename
    content = _TASK_TMPL.format(
        task_id=task_id,
        title=title,
        status=status,
        updated=updated,
        claimed_at=claimed_at,
    )
    path.write_text(content, encoding="utf-8")
    return path


def _make_engine(kanban_dir: Path) -> KanbanEngine:
    return KanbanEngine(kanban_dir)


def _make_cockpit_view(kanban_dir: Path) -> CockpitView:
    return CockpitView(_make_engine(kanban_dir))


# ---------------------------------------------------------------------------
# AC1-AC5: engine.release_task OCC parameter
# ---------------------------------------------------------------------------


class TestFromAC_EngineReleaseOCC:
    """OCC compare-and-swap support on engine.release_task (AC1-AC5)."""

    # -- ac1-sig: signature -----------------------------------------------

    def test_engine_release_task_signature_has_expected_updated_param(self, tmp_path: Path) -> None:
        """AC1: release_task must declare expected_updated as a keyword parameter."""
        engine = _make_engine(_make_board(tmp_path))
        sig = inspect.signature(engine.release_task)
        assert "expected_updated" in sig.parameters, "engine.release_task must accept expected_updated OCC token"

    def test_engine_release_task_expected_updated_default_is_none(self, tmp_path: Path) -> None:
        """AC1: expected_updated default must be None (optional for agent callers)."""
        engine = _make_engine(_make_board(tmp_path))
        sig = inspect.signature(engine.release_task)
        param = sig.parameters.get("expected_updated")
        assert param is not None, "expected_updated param missing"
        assert param.default is None, "expected_updated must default to None (optional OCC token)"

    # -- ac2-cas-write: CAS happy path (claimed + fresh token) ---------------

    def test_engine_release_task_cas_fresh_token_clears_claimed_at(self, tmp_path: Path) -> None:
        """AC2: claimed task + matching expected_updated → claimed_at cleared."""
        kanban_dir = _make_board(tmp_path)
        _write_task(
            kanban_dir,
            1,
            updated="2026-01-01T10:00:00+00:00",
            claimed_at='"2026-01-01T09:00:00+00:00"',
        )
        engine = _make_engine(kanban_dir)
        result = engine.release_task("1", expected_updated="2026-01-01T10:00:00+00:00")
        assert result.claimed_at is None

    def test_engine_release_task_cas_fresh_token_returns_task(self, tmp_path: Path) -> None:
        """AC2: CAS release on claimed task returns the updated Task object."""
        from owlbear_kanban.models import Task

        kanban_dir = _make_board(tmp_path)
        _write_task(
            kanban_dir,
            1,
            updated="2026-01-01T10:00:00+00:00",
            claimed_at='"2026-01-01T09:00:00+00:00"',
        )
        engine = _make_engine(kanban_dir)
        result = engine.release_task("1", expected_updated="2026-01-01T10:00:00+00:00")
        assert isinstance(result, Task)

    # -- ac3-stale: CAS conflict on claimed task ------------------------------

    def test_engine_release_task_stale_token_raises_concurrency_error(self, tmp_path: Path) -> None:
        """AC3: stale expected_updated on claimed task raises ConcurrencyError."""
        kanban_dir = _make_board(tmp_path)
        _write_task(
            kanban_dir,
            1,
            updated="2026-01-01T10:00:00+00:00",
            claimed_at='"2026-01-01T09:00:00+00:00"',
        )
        engine = _make_engine(kanban_dir)
        with pytest.raises(ConcurrencyError):
            engine.release_task("1", expected_updated="2025-01-01T00:00:00+00:00")

    def test_engine_release_task_stale_token_error_code_is_err_stale(self, tmp_path: Path) -> None:
        """AC3: ConcurrencyError from stale token has code='ERR_STALE'."""
        kanban_dir = _make_board(tmp_path)
        _write_task(
            kanban_dir,
            1,
            updated="2026-01-01T10:00:00+00:00",
            claimed_at='"2026-01-01T09:00:00+00:00"',
        )
        engine = _make_engine(kanban_dir)
        with pytest.raises(ConcurrencyError) as exc_info:
            engine.release_task("1", expected_updated="2025-01-01T00:00:00+00:00")
        assert exc_info.value.code == "ERR_STALE"

    # -- ac4-lww: None token -> existing LWW behavior unchanged ---------------

    def test_engine_release_task_none_token_lww_clears_claim(self, tmp_path: Path) -> None:
        """AC4: expected_updated=None -> LWW fallback, claim cleared without CAS check."""
        kanban_dir = _make_board(tmp_path)
        _write_task(
            kanban_dir,
            1,
            updated="2026-01-01T10:00:00+00:00",
            claimed_at='"2026-01-01T09:00:00+00:00"',
        )
        engine = _make_engine(kanban_dir)
        result = engine.release_task("1", expected_updated=None)
        assert result.claimed_at is None

    # -- ac5-noop-stale: unclaimed + stale token → ConcurrencyError ----------

    def test_engine_release_task_unclaimed_stale_token_raises_concurrency_error(self, tmp_path: Path) -> None:
        """AC5: unclaimed task + stale expected_updated → ConcurrencyError(ERR_STALE)."""
        kanban_dir = _make_board(tmp_path)
        _write_task(
            kanban_dir,
            1,
            updated="2026-01-01T10:00:00+00:00",
            claimed_at="null",
        )
        engine = _make_engine(kanban_dir)
        with pytest.raises(ConcurrencyError) as exc_info:
            engine.release_task("1", expected_updated="2025-01-01T00:00:00+00:00")
        assert exc_info.value.code == "ERR_STALE"

    # -- ac5-noop-fresh: unclaimed + fresh token → silent no-op --------------

    def test_engine_release_task_unclaimed_fresh_token_is_silent_noop(self, tmp_path: Path) -> None:
        """AC5: unclaimed task + matching expected_updated → no-op, no exception."""
        kanban_dir = _make_board(tmp_path)
        _write_task(
            kanban_dir,
            1,
            updated="2026-01-01T10:00:00+00:00",
            claimed_at="null",
        )
        engine = _make_engine(kanban_dir)
        # Should not raise
        result = engine.release_task("1", expected_updated="2026-01-01T10:00:00+00:00")
        assert result.claimed_at is None

    def test_engine_release_task_unclaimed_fresh_token_updated_not_advanced(self, tmp_path: Path) -> None:
        """AC5: unclaimed + fresh token no-op must NOT advance the updated timestamp."""
        kanban_dir = _make_board(tmp_path)
        original_updated = "2026-01-01T10:00:00+00:00"
        _write_task(
            kanban_dir,
            1,
            updated=original_updated,
            claimed_at="null",
        )
        engine = _make_engine(kanban_dir)
        result = engine.release_task("1", expected_updated=original_updated)
        assert result.updated == original_updated, "No-op release must not advance updated timestamp"

    # -- ac2-cas-helper: CAS path calls write_task_if_unchanged, not write_task --

    def test_engine_release_task_cas_path_calls_write_task_if_unchanged(self, tmp_path: Path) -> None:
        """AC2: claimed + fresh token → write_task_if_unchanged called (not write_task)."""
        from owlbear_kanban import storage

        kanban_dir = _make_board(tmp_path)
        _write_task(
            kanban_dir,
            1,
            updated="2026-01-01T10:00:00+00:00",
            claimed_at='"2026-01-01T09:00:00+00:00"',
        )
        engine = _make_engine(kanban_dir)
        with mock.patch.object(
            storage,
            "write_task_if_unchanged",
            wraps=storage.write_task_if_unchanged,
        ) as mock_cas:
            engine.release_task("1", expected_updated="2026-01-01T10:00:00+00:00")
        assert mock_cas.called, "release_task must call write_task_if_unchanged (CAS) when expected_updated is set"

    def test_engine_release_task_lww_path_does_not_call_write_task_if_unchanged(self, tmp_path: Path) -> None:
        """AC4: expected_updated=None → write_task_if_unchanged must NOT be called (LWW path)."""
        from owlbear_kanban import storage

        kanban_dir = _make_board(tmp_path)
        _write_task(
            kanban_dir,
            1,
            updated="2026-01-01T10:00:00+00:00",
            claimed_at='"2026-01-01T09:00:00+00:00"',
        )
        engine = _make_engine(kanban_dir)
        with mock.patch.object(
            storage,
            "write_task_if_unchanged",
            wraps=storage.write_task_if_unchanged,
        ) as mock_cas:
            engine.release_task("1", expected_updated=None)
        assert not mock_cas.called, (
            "release_task must NOT call write_task_if_unchanged when expected_updated is None (LWW)"
        )


# ---------------------------------------------------------------------------
# AC6: CockpitView.release_task facade — required token, delegation
# ---------------------------------------------------------------------------


class TestFromAC_CockpitViewReleaseOCC:
    """CockpitView.release_task requires expected_updated and delegates OCC (AC6)."""

    # -- ac6-facade-sig: signature -------------------------------------------

    def test_cockpit_view_release_task_signature_has_expected_updated_param(self, tmp_path: Path) -> None:
        """AC6: CockpitView.release_task must declare expected_updated parameter."""
        cv = _make_cockpit_view(_make_board(tmp_path))
        sig = inspect.signature(cv.release_task)
        assert "expected_updated" in sig.parameters, "CockpitView.release_task must accept expected_updated (OCC token)"

    def test_cockpit_view_release_task_expected_updated_is_required(self, tmp_path: Path) -> None:
        """AC6: CockpitView.release_task expected_updated has no default (required)."""
        cv = _make_cockpit_view(_make_board(tmp_path))
        sig = inspect.signature(cv.release_task)
        param = sig.parameters.get("expected_updated")
        assert param is not None, "expected_updated param missing"
        assert param.default is inspect.Parameter.empty, (
            "CockpitView.release_task.expected_updated must be required (no default)"
        )

    # -- ac6-facade-ok: fresh token + claimed → claim cleared -----------------

    def test_cockpit_view_release_task_fresh_token_claimed_clears_claim(self, tmp_path: Path) -> None:
        """AC6: CockpitView: fresh expected_updated + claimed task → claim cleared."""
        kanban_dir = _make_board(tmp_path)
        _write_task(
            kanban_dir,
            1,
            updated="2026-01-01T10:00:00+00:00",
            claimed_at='"2026-01-01T09:00:00+00:00"',
        )
        cv = _make_cockpit_view(kanban_dir)
        result = cv.release_task(1, expected_updated="2026-01-01T10:00:00+00:00")
        assert isinstance(result, SingleTaskResponse)
        assert result.claimed_at is None

    # -- ac6-facade-err: stale token propagates ConcurrencyError --------------

    def test_cockpit_view_release_task_stale_token_raises_concurrency_error(self, tmp_path: Path) -> None:
        """AC6: CockpitView: stale expected_updated propagates ConcurrencyError(ERR_STALE)."""
        kanban_dir = _make_board(tmp_path)
        _write_task(
            kanban_dir,
            1,
            updated="2026-01-01T10:00:00+00:00",
            claimed_at='"2026-01-01T09:00:00+00:00"',
        )
        cv = _make_cockpit_view(kanban_dir)
        with pytest.raises(ConcurrencyError) as exc_info:
            cv.release_task(1, expected_updated="2025-01-01T00:00:00+00:00")
        assert exc_info.value.code == "ERR_STALE"

    # -- ac6-facade-noop-fresh: unclaimed + fresh token → no-op ---------------

    def test_cockpit_view_release_task_unclaimed_fresh_token_returns_unchanged(self, tmp_path: Path) -> None:
        """AC6: CockpitView: fresh token + unclaimed → no-op, returns unchanged task."""
        kanban_dir = _make_board(tmp_path)
        _write_task(
            kanban_dir,
            1,
            updated="2026-01-01T10:00:00+00:00",
            claimed_at="null",
        )
        cv = _make_cockpit_view(kanban_dir)
        result = cv.release_task(1, expected_updated="2026-01-01T10:00:00+00:00")
        assert isinstance(result, SingleTaskResponse)
        assert result.claimed_at is None

    # -- ac6-facade-noop-stale: unclaimed + stale token → ConcurrencyError ----

    def test_cockpit_view_release_task_unclaimed_stale_token_raises_concurrency_error(self, tmp_path: Path) -> None:
        """AC6: CockpitView: unclaimed + stale token → ConcurrencyError(ERR_STALE)."""
        kanban_dir = _make_board(tmp_path)
        _write_task(
            kanban_dir,
            1,
            updated="2026-01-01T10:00:00+00:00",
            claimed_at="null",
        )
        cv = _make_cockpit_view(kanban_dir)
        with pytest.raises(ConcurrencyError) as exc_info:
            cv.release_task(1, expected_updated="2025-01-01T00:00:00+00:00")
        assert exc_info.value.code == "ERR_STALE"
