"""Failing tests for user-triggered cleanup operation (#1449).

RED phase — all tests must fail until cleanup() is implemented in GREEN.

AC coverage:
  AC-1 (td:1): cleanup() releases expired claimed_at via CAS; returns released_claim_ids
  AC-2 (td:1): cleanup() moves status=archived+archival_reason≠None files to archive/;
               returns archived_task_ids
  AC-3 (td:2): cleanup() skips malformed frontmatter and archive collisions; source
               file preserved; each skipped_items entry has path (str) and reason (str)
  AC-4 (td:1): pick_tasks, start_work, KanbanEngine.__init__, and MCP app_lifespan
               do NOT invoke cleanup() implicitly
"""

from __future__ import annotations

from pathlib import Path
from unittest import mock

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_kanban.agent_view import AgentView

# ---------------------------------------------------------------------------
# Board helpers
# ---------------------------------------------------------------------------

_CONFIG_YAML = """\
next_id: 1
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
claimed_at: {claimed_at}
archival_reason: {archival_reason}
archival_refs: []
---
Body.
"""

# An always-expired claimed_at (well over 1 h before any plausible test run date)
_EXPIRED_TS = '"2026-01-01T00:00:00+00:00"'


def _make_board(base_dir: Path) -> Path:
    """Create a minimal kanban board structure under base_dir."""
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


def _write_task(
    kanban_dir: Path,
    *,
    task_id: int,
    status: str = "todo",
    claimed_at: str = "null",
    archival_reason: str = "null",
) -> Path:
    content = _TASK_TMPL.format(
        task_id=task_id,
        status=status,
        claimed_at=claimed_at,
        archival_reason=archival_reason,
    )
    path = kanban_dir / "tasks" / f"{task_id}-task.md"
    path.write_text(content, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# AC-1: Claim release
# ---------------------------------------------------------------------------


class TestFromAC_ClaimRelease:
    """AC-1: cleanup() releases expired claimed_at values via CAS; returns released_claim_ids.

    Expired = claimed_at timestamp older than the engine's configured claim timeout (≥1 h).
    Live claims (within the timeout window) must be left untouched.
    """

    def test_expired_claim_id_appears_in_released_claim_ids(
        self, tmp_path: Path
    ) -> None:
        """Task with an expired claimed_at appears in released_claim_ids after cleanup()."""
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, status="todo", claimed_at=_EXPIRED_TS)
        engine = KanbanEngine(board, activity_log=False)

        result = engine.cleanup()

        assert 1 in result.released_claim_ids

    def test_expired_claimed_at_is_cleared_on_disk(self, tmp_path: Path) -> None:
        """cleanup() writes cleared claimed_at to disk; re-reading the task shows None."""
        board = _make_board(tmp_path)
        _write_task(board, task_id=2, status="todo", claimed_at=_EXPIRED_TS)
        engine = KanbanEngine(board, activity_log=False)

        engine.cleanup()

        task = engine.show_task("2")
        assert task.claimed_at is None, (
            "claimed_at must be cleared on disk after cleanup releases an expired claim"
        )


# ---------------------------------------------------------------------------
# AC-2: Archive move
# ---------------------------------------------------------------------------


class TestFromAC_ArchiveMove:
    """AC-2: cleanup() moves status=archived files (archival_reason≠None) to archive/.

    A task that has status 'archived' and a non-None archival_reason but still
    resides in tasks/ (drift-archived) must be moved and its ID returned in
    archived_task_ids.
    """

    def test_drift_archived_task_id_appears_in_archived_task_ids(
        self, tmp_path: Path
    ) -> None:
        """ID of a drift-archived task appears in archived_task_ids after cleanup()."""
        board = _make_board(tmp_path)
        _write_task(
            board,
            task_id=1,
            status="archived",
            archival_reason='"completed"',
        )
        engine = KanbanEngine(board, activity_log=False)

        result = engine.cleanup()

        assert 1 in result.archived_task_ids

    def test_drift_archived_task_is_moved_to_archive_dir(
        self, tmp_path: Path
    ) -> None:
        """Drift-archived file is physically moved from tasks/ to archive/ by cleanup()."""
        board = _make_board(tmp_path)
        _write_task(
            board,
            task_id=2,
            status="archived",
            archival_reason='"completed"',
        )
        engine = KanbanEngine(board, activity_log=False)

        engine.cleanup()

        assert not (board / "tasks" / "2-task.md").exists(), (
            "source file must be removed from tasks/ after archive move"
        )
        assert (board / "archive" / "2-task.md").exists(), (
            "file must appear in archive/ after cleanup moves it"
        )


# ---------------------------------------------------------------------------
# AC-3: Skip handling (td:2 — full TDD)
# ---------------------------------------------------------------------------


class TestFromAC_SkipHandling:
    """AC-3: cleanup() skips malformed task files and archive destination collisions.

    For each skipped file:
    - the source file is left in place (not deleted)
    - one entry is added to skipped_items with path (str) and reason (str) fields
    """

    # ---- happy path (processing proceeds alongside skips) ----

    def test_clean_task_is_not_skipped(self, tmp_path: Path) -> None:
        """A well-formed task with no archived status produces no skipped_items entry."""
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, status="todo")
        engine = KanbanEngine(board, activity_log=False)

        result = engine.cleanup()

        assert 1 not in result.archived_task_ids
        assert not any(
            "1-task.md" in item.get("path", "") for item in result.skipped_items
        )

    # ---- error paths: skip condition 1 — malformed frontmatter ----

    def test_malformed_frontmatter_produces_skipped_items_entry(
        self, tmp_path: Path
    ) -> None:
        """A file with unparseable frontmatter adds one entry to skipped_items."""
        board = _make_board(tmp_path)
        (board / "tasks" / "99-bad.md").write_text(
            "not valid frontmatter at all\n", encoding="utf-8"
        )
        engine = KanbanEngine(board, activity_log=False)

        result = engine.cleanup()

        assert len(result.skipped_items) >= 1

    def test_malformed_skipped_item_has_path_str(self, tmp_path: Path) -> None:
        """skipped_items entry for malformed file has 'path' field of type str."""
        board = _make_board(tmp_path)
        (board / "tasks" / "99-bad.md").write_text(
            "not valid frontmatter\n", encoding="utf-8"
        )
        engine = KanbanEngine(board, activity_log=False)

        result = engine.cleanup()

        for item in result.skipped_items:
            assert "path" in item, "skipped_items entry must have 'path' field"
            assert isinstance(item["path"], str), "'path' must be a str"

    def test_malformed_skipped_item_has_reason_str(self, tmp_path: Path) -> None:
        """skipped_items entry for malformed file has 'reason' field of type str."""
        board = _make_board(tmp_path)
        (board / "tasks" / "99-bad.md").write_text(
            "not valid frontmatter\n", encoding="utf-8"
        )
        engine = KanbanEngine(board, activity_log=False)

        result = engine.cleanup()

        for item in result.skipped_items:
            assert "reason" in item, "skipped_items entry must have 'reason' field"
            assert isinstance(item["reason"], str), "'reason' must be a str"

    # ---- boundary: source file preserved on malformed skip ----

    def test_malformed_source_file_not_deleted_on_skip(
        self, tmp_path: Path
    ) -> None:
        """Source file with malformed frontmatter is left in tasks/ after skip."""
        board = _make_board(tmp_path)
        malformed = board / "tasks" / "99-bad.md"
        malformed.write_text("not valid frontmatter\n", encoding="utf-8")
        engine = KanbanEngine(board, activity_log=False)

        engine.cleanup()

        assert malformed.exists(), (
            "malformed source file must not be deleted when skipped"
        )

    # ---- error paths: skip condition 2 — archive destination collision ----

    def test_archive_collision_produces_skipped_items_entry(
        self, tmp_path: Path
    ) -> None:
        """A drift-archived task whose destination already exists adds a skipped_items entry."""
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, status="archived", archival_reason='"completed"')
        # Pre-create the collision target
        (board / "archive" / "1-task.md").write_text(
            "collision sentinel", encoding="utf-8"
        )
        engine = KanbanEngine(board, activity_log=False)

        result = engine.cleanup()

        assert 1 not in result.archived_task_ids, (
            "collided task must NOT appear in archived_task_ids"
        )
        assert len(result.skipped_items) >= 1

    def test_collision_skipped_item_has_path_and_reason(
        self, tmp_path: Path
    ) -> None:
        """skipped_items entry for a collision has both 'path' and 'reason' str fields."""
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, status="archived", archival_reason='"completed"')
        (board / "archive" / "1-task.md").write_text(
            "collision sentinel", encoding="utf-8"
        )
        engine = KanbanEngine(board, activity_log=False)

        result = engine.cleanup()

        assert result.skipped_items, "expected at least one skipped_items entry"
        for item in result.skipped_items:
            assert isinstance(item.get("path"), str), "'path' must be str"
            assert isinstance(item.get("reason"), str), "'reason' must be str"

    # ---- boundary: source file preserved on collision skip ----

    def test_collision_source_file_not_deleted_on_skip(
        self, tmp_path: Path
    ) -> None:
        """Source task file is left in tasks/ when an archive collision causes a skip."""
        board = _make_board(tmp_path)
        source = _write_task(
            board, task_id=1, status="archived", archival_reason='"completed"'
        )
        (board / "archive" / "1-task.md").write_text(
            "collision sentinel", encoding="utf-8"
        )
        engine = KanbanEngine(board, activity_log=False)

        engine.cleanup()

        assert source.exists(), (
            "source task file must not be deleted when archive collision causes a skip"
        )


# ---------------------------------------------------------------------------
# AC-4: No implicit cleanup invocation (td:1)
# ---------------------------------------------------------------------------


class TestFromAC_NoImplicitCleanup:
    """AC-4: pick_tasks, start_work, KanbanEngine.__init__, and MCP app_lifespan
    must not invoke cleanup() implicitly.
    """

    def test_engine_init_does_not_call_cleanup(self, tmp_path: Path) -> None:
        """KanbanEngine.__init__ must not call cleanup()."""
        board = _make_board(tmp_path)
        with mock.patch.object(KanbanEngine, "cleanup") as mock_cleanup:
            KanbanEngine(board, activity_log=False)
            mock_cleanup.assert_not_called()

    def test_pick_tasks_does_not_call_cleanup(self, tmp_path: Path) -> None:
        """AgentView.pick_tasks must not invoke KanbanEngine.cleanup()."""
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, status="todo")
        engine = KanbanEngine(board, activity_log=False)
        engine.list_tasks()
        with mock.patch.object(engine, "cleanup") as mock_cleanup:
            view = AgentView(engine)
            view.pick_tasks()
            mock_cleanup.assert_not_called()

    def test_start_work_does_not_call_cleanup(self, tmp_path: Path) -> None:
        """KanbanEngine.start_work must not invoke cleanup()."""
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, status="todo")
        engine = KanbanEngine(board, activity_log=False)
        engine.list_tasks()
        with mock.patch.object(engine, "cleanup") as mock_cleanup:
            engine.start_work("1")
            mock_cleanup.assert_not_called()

    @pytest.mark.asyncio
    async def test_mcp_app_lifespan_does_not_call_cleanup(
        self, tmp_path: Path
    ) -> None:
        """MCP server app_lifespan must not call cleanup() during startup.

        app_lifespan calls engine.sweep() (claim-only) — this is a distinct
        operation from cleanup(). Verified by mocking cleanup and asserting it
        is never called during lifespan startup.
        """
        from owlbear_mcp_kanban.server import app_lifespan  # noqa: PLC0415

        board = _make_board(tmp_path)
        server_mock = mock.MagicMock()

        with (
            mock.patch(
                "owlbear_mcp_kanban.server._resolve_kanban_dir",
                return_value=board,
            ),
            mock.patch.object(KanbanEngine, "cleanup") as mock_cleanup,
        ):
            async with app_lifespan(server_mock):
                pass

        mock_cleanup.assert_not_called()
