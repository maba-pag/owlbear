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


class TestClaimRelease:
    """AC-1: cleanup() releases expired claimed_at values via CAS; returns released_claim_ids.

    Expired = claimed_at timestamp older than the engine's configured claim timeout (≥1 h).
    Live claims (within the timeout window) must be left untouched.
    """

    def test_expired_claim_id_appears_in_released_claim_ids(self, tmp_path: Path) -> None:
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
        assert task.claimed_at is None, "claimed_at must be cleared on disk after cleanup releases an expired claim"


# ---------------------------------------------------------------------------
# AC-2: Archive move
# ---------------------------------------------------------------------------


class TestArchiveMove:
    """AC-2: cleanup() moves status=archived files (archival_reason≠None) to archive/.

    A task that has status 'archived' and a non-None archival_reason but still
    resides in tasks/ (drift-archived) must be moved and its ID returned in
    archived_task_ids.
    """

    def test_drift_archived_task_id_appears_in_archived_task_ids(self, tmp_path: Path) -> None:
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

    def test_drift_archived_task_is_moved_to_archive_dir(self, tmp_path: Path) -> None:
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
        assert (board / "archive" / "2-task.md").exists(), "file must appear in archive/ after cleanup moves it"

    # ---- AC-2 negative branch: archival_reason=None (td:2 upgrade) ----

    def test_archived_without_reason_not_in_archived_task_ids(self, tmp_path: Path) -> None:
        """Archived task with archival_reason=None is NOT moved and not in archived_task_ids."""
        board = _make_board(tmp_path)
        _write_task(board, task_id=3, status="archived", archival_reason="null")
        engine = KanbanEngine(board, activity_log=False)

        result = engine.cleanup()

        assert 3 not in result.archived_task_ids, "task with archival_reason=None must not appear in archived_task_ids"

    def test_archived_without_reason_file_remains_in_tasks(self, tmp_path: Path) -> None:
        """Archived task with archival_reason=None is left in tasks/ — not physically moved."""
        board = _make_board(tmp_path)
        source = _write_task(board, task_id=4, status="archived", archival_reason="null")
        engine = KanbanEngine(board, activity_log=False)

        engine.cleanup()

        assert source.exists(), "source file with archival_reason=None must remain in tasks/ after cleanup"
        assert not (board / "archive" / "4-task.md").exists(), (
            "file with archival_reason=None must not appear in archive/ after cleanup"
        )

    def test_archived_without_reason_produces_skipped_item(self, tmp_path: Path) -> None:
        """Archived task with archival_reason=None produces one skipped_items entry."""
        board = _make_board(tmp_path)
        source = _write_task(board, task_id=5, status="archived", archival_reason="null")
        engine = KanbanEngine(board, activity_log=False)

        result = engine.cleanup()

        assert len(result.skipped_items) == 1, (
            "expected exactly one skipped_items entry for the None-reason archived task"
        )
        assert result.skipped_items[0]["path"] == str(source), (
            "skipped_items entry path must match the source file path"
        )
        assert isinstance(result.skipped_items[0]["reason"], str), "skipped_items entry reason must be a str"


# ---------------------------------------------------------------------------
# AC-3: Skip handling (td:2 — full TDD)
# ---------------------------------------------------------------------------


class TestSkipHandling:
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
        assert not any("1-task.md" in item.get("path", "") for item in result.skipped_items)

    # ---- error paths: skip condition 1 — malformed frontmatter ----

    def test_malformed_frontmatter_produces_skipped_items_entry(self, tmp_path: Path) -> None:
        """A file with unparseable frontmatter adds one entry to skipped_items."""
        board = _make_board(tmp_path)
        (board / "tasks" / "99-bad.md").write_text("not valid frontmatter at all\n", encoding="utf-8")
        engine = KanbanEngine(board, activity_log=False)

        result = engine.cleanup()

        assert len(result.skipped_items) >= 1

    def test_malformed_skipped_item_has_path_str(self, tmp_path: Path) -> None:
        """skipped_items entry for malformed file has 'path' field of type str."""
        board = _make_board(tmp_path)
        (board / "tasks" / "99-bad.md").write_text("not valid frontmatter\n", encoding="utf-8")
        engine = KanbanEngine(board, activity_log=False)

        result = engine.cleanup()

        for item in result.skipped_items:
            assert "path" in item, "skipped_items entry must have 'path' field"
            assert isinstance(item["path"], str), "'path' must be a str"

    def test_malformed_skipped_item_has_reason_str(self, tmp_path: Path) -> None:
        """skipped_items entry for malformed file has 'reason' field of type str."""
        board = _make_board(tmp_path)
        (board / "tasks" / "99-bad.md").write_text("not valid frontmatter\n", encoding="utf-8")
        engine = KanbanEngine(board, activity_log=False)

        result = engine.cleanup()

        for item in result.skipped_items:
            assert "reason" in item, "skipped_items entry must have 'reason' field"
            assert isinstance(item["reason"], str), "'reason' must be a str"

    # ---- boundary: source file preserved on malformed skip ----

    def test_malformed_source_file_not_deleted_on_skip(self, tmp_path: Path) -> None:
        """Source file with malformed frontmatter is left in tasks/ after skip."""
        board = _make_board(tmp_path)
        malformed = board / "tasks" / "99-bad.md"
        malformed.write_text("not valid frontmatter\n", encoding="utf-8")
        engine = KanbanEngine(board, activity_log=False)

        engine.cleanup()

        assert malformed.exists(), "malformed source file must not be deleted when skipped"

    # ---- error paths: skip condition 2 — archive destination collision ----

    def test_archive_collision_produces_skipped_items_entry(self, tmp_path: Path) -> None:
        """A drift-archived task whose destination already exists adds a skipped_items entry."""
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, status="archived", archival_reason='"completed"')
        # Pre-create the collision target
        (board / "archive" / "1-task.md").write_text("collision sentinel", encoding="utf-8")
        engine = KanbanEngine(board, activity_log=False)

        result = engine.cleanup()

        assert 1 not in result.archived_task_ids, "collided task must NOT appear in archived_task_ids"
        assert len(result.skipped_items) >= 1

    def test_collision_skipped_item_has_path_and_reason(self, tmp_path: Path) -> None:
        """skipped_items entry for a collision has both 'path' and 'reason' str fields."""
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, status="archived", archival_reason='"completed"')
        (board / "archive" / "1-task.md").write_text("collision sentinel", encoding="utf-8")
        engine = KanbanEngine(board, activity_log=False)

        result = engine.cleanup()

        assert result.skipped_items, "expected at least one skipped_items entry"
        for item in result.skipped_items:
            assert isinstance(item.get("path"), str), "'path' must be str"
            assert isinstance(item.get("reason"), str), "'reason' must be str"

    # ---- boundary: source file preserved on collision skip ----

    def test_collision_source_file_not_deleted_on_skip(self, tmp_path: Path) -> None:
        """Source task file is left in tasks/ when an archive collision causes a skip."""
        board = _make_board(tmp_path)
        source = _write_task(board, task_id=1, status="archived", archival_reason='"completed"')
        (board / "archive" / "1-task.md").write_text("collision sentinel", encoding="utf-8")
        engine = KanbanEngine(board, activity_log=False)

        engine.cleanup()

        assert source.exists(), "source task file must not be deleted when archive collision causes a skip"

    # ---- AC-3: exact cardinality and exact path value ----

    def test_single_malformed_skipped_item_has_exact_cardinality_and_path(self, tmp_path: Path) -> None:
        """Single malformed file produces exactly one skipped_items entry with exact path."""
        board = _make_board(tmp_path)
        bad_file = board / "tasks" / "77-bad.md"
        bad_file.write_text("not valid frontmatter\n", encoding="utf-8")
        engine = KanbanEngine(board, activity_log=False)

        result = engine.cleanup()

        assert len(result.skipped_items) == 1, "exactly one skipped_items entry expected for a single malformed file"
        assert result.skipped_items[0]["path"] == str(bad_file), (
            "skipped_items[0].path must equal the actual source file path"
        )

    def test_single_collision_skipped_item_has_exact_cardinality_and_path(self, tmp_path: Path) -> None:
        """Single early collision produces exactly one skipped_items entry with exact path."""
        board = _make_board(tmp_path)
        source = _write_task(board, task_id=2, status="archived", archival_reason='"completed"')
        (board / "archive" / "2-task.md").write_text("sentinel", encoding="utf-8")
        engine = KanbanEngine(board, activity_log=False)

        result = engine.cleanup()

        assert len(result.skipped_items) == 1, "exactly one skipped_items entry expected for a single archive collision"
        assert result.skipped_items[0]["path"] == str(source), (
            "skipped_items[0].path must equal the actual source file path"
        )

    # ---- AC-3: late FileExistsError branch (no_overwrite=True atomic move) ----

    def test_late_file_exists_error_produces_skipped_items_entry(self, tmp_path: Path) -> None:
        """Late FileExistsError from _move_file is caught; entry added to skipped_items.

        Simulates a race where dest.exists() pre-check passes (no collision at pre-check
        time) but os.link() raises FileExistsError because the destination appeared
        concurrently before the atomic move completed.
        """
        board = _make_board(tmp_path)
        source = _write_task(board, task_id=3, status="archived", archival_reason='"completed"')
        engine = KanbanEngine(board, activity_log=False)

        # Dest does not exist — pre-check passes — but _move_file raises FileExistsError.
        with mock.patch("owlbear_kanban.engine._move_file", side_effect=FileExistsError):
            result = engine.cleanup()

        assert 3 not in result.archived_task_ids, "late-collision task must NOT appear in archived_task_ids"
        assert len(result.skipped_items) == 1, "exactly one skipped_items entry expected for a single late collision"
        assert result.skipped_items[0]["path"] == str(source), (
            "skipped_items[0].path must equal the actual source file path"
        )
        assert source.exists(), "source file must not be deleted when a late FileExistsError causes a skip"
        assert isinstance(result.skipped_items[0]["reason"], str), (
            "skipped_items[0].reason must be a str for the late FileExistsError branch"
        )


# ---------------------------------------------------------------------------
# AC-4: No implicit cleanup invocation (td:1)
# ---------------------------------------------------------------------------


class TestNoImplicitCleanup:
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
    async def test_mcp_app_lifespan_does_not_call_cleanup(self, tmp_path: Path) -> None:
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


# ---------------------------------------------------------------------------
# AC-5: Stale-state skip before archive move (td:1)
# ---------------------------------------------------------------------------


class TestStaleStateSkip:
    """AC-5: cleanup() re-reads task from disk before archive move.

    If the on-disk status is no longer 'archived' or archival_reason has become
    None between the initial scan read and the move, cleanup() must skip the
    file and produce a skipped_items entry instead of moving it.
    """

    def test_stale_state_task_is_skipped_when_status_changes_before_move(self, tmp_path: Path) -> None:
        """AC-5: cleanup() skips archive move when on-disk status changes after initial read.

        Simulates concurrent state drift: the initial read returns an archived
        record, then the file is overwritten to status=in-progress before the
        re-read that the new implementation performs immediately before moving.

        Current implementation (no re-read): moves the stale file and adds the
        task to archived_task_ids — this assertion fails, confirming RED phase.

        New implementation (re-reads before _move_file): catches the drift and
        produces a skipped_items entry — all assertions pass.
        """
        import owlbear_kanban.engine as eng_mod

        board = _make_board(tmp_path)
        # File starts as archived+completed so the first read_task returns archived state.
        source = _write_task(board, task_id=1, status="archived", archival_reason='"completed"')
        engine = KanbanEngine(board, activity_log=False)

        real_read_task = eng_mod.read_task
        per_path_calls: dict = {}

        def read_side_effect(path: Path, *, config=None) -> object:
            per_path_calls[path] = per_path_calls.get(path, 0) + 1
            result = real_read_task(path, config=config)
            if path == source and per_path_calls[path] == 1:
                # After returning the archived record, rewrite to simulate a
                # concurrent writer changing status to in-progress before re-read.
                source.write_text(
                    _TASK_TMPL.format(
                        task_id=1,
                        status="in-progress",
                        claimed_at="null",
                        archival_reason="null",
                    ),
                    encoding="utf-8",
                )
            return result

        with mock.patch("owlbear_kanban.engine.read_task", side_effect=read_side_effect):
            result = engine.cleanup()

        assert 1 not in result.archived_task_ids, (
            "task whose on-disk status changed to in-progress must not appear "
            "in archived_task_ids — cleanup() must re-read before moving"
        )
        assert source.exists(), "source file must remain in tasks/ when cleanup skips due to stale-state drift"
        assert len(result.skipped_items) == 1, (
            "exactly one skipped_items entry expected when on-disk status is no longer archived"
        )

    def test_stale_state_task_is_skipped_when_archival_reason_becomes_none(self, tmp_path: Path) -> None:
        """AC-5: cleanup() skips archive move when on-disk archival_reason becomes None after initial read.

        Simulates concurrent state drift: the initial read returns an archived
        record with archival_reason='completed', then the file is overwritten
        keeping status='archived' but clearing archival_reason to null before
        the re-read that cleanup() performs before moving.

        This independently discriminates the ``current.archival_reason is None``
        guard — if that guard is removed the task would be moved into archive/
        and this assertion would fail.
        """
        import owlbear_kanban.engine as eng_mod

        board = _make_board(tmp_path)
        source = _write_task(board, task_id=2, status="archived", archival_reason='"completed"')
        engine = KanbanEngine(board, activity_log=False)

        real_read_task = eng_mod.read_task
        per_path_calls: dict = {}

        def read_side_effect(path: Path, *, config=None) -> object:
            per_path_calls[path] = per_path_calls.get(path, 0) + 1
            result = real_read_task(path, config=config)
            if path == source and per_path_calls[path] == 1:
                # After returning the archived+completed record, rewrite to
                # simulate a concurrent writer clearing archival_reason while
                # leaving status as 'archived'.
                source.write_text(
                    _TASK_TMPL.format(
                        task_id=2,
                        status="archived",
                        claimed_at="null",
                        archival_reason="null",
                    ),
                    encoding="utf-8",
                )
            return result

        with mock.patch("owlbear_kanban.engine.read_task", side_effect=read_side_effect):
            result = engine.cleanup()

        assert 2 not in result.archived_task_ids, (
            "task whose archival_reason became None must not appear in archived_task_ids "
            "— cleanup() must check archival_reason on the re-read"
        )
        assert source.exists(), "source file must remain in tasks/ when cleanup skips due to archival_reason drift"
        assert len(result.skipped_items) == 1, (
            "exactly one skipped_items entry expected when archival_reason becomes None after initial read"
        )


# ---------------------------------------------------------------------------
# AC-6: _move_file no_overwrite rollback safety (td:1)
# ---------------------------------------------------------------------------


class TestMoveRollback:
    """AC-6: _move_file(no_overwrite=True) rolls back dest hard link on src.unlink() failure.

    If os.link(src, dest) succeeds but src.unlink() raises OSError, the destination
    hard link must be removed before the error propagates to prevent dual-location state.
    cleanup() must catch the re-raised OSError and record a skipped_items entry.
    """

    def test_move_rollback_removes_dest_on_src_unlink_failure(self, tmp_path: Path) -> None:
        """Destination hard link is rolled back and skipped_items entry added on src.unlink() failure.

        Simulates a partial move: os.link() creates the archive hard link, then
        src.unlink() fails with OSError.  The no_overwrite path must roll back the
        destination before re-raising so cleanup() sees no destination file and
        records a skipped_items entry instead of leaving dual-location state.
        """
        board = _make_board(tmp_path)
        source = _write_task(board, task_id=1, status="archived", archival_reason='"completed"')
        dest = board / "archive" / "1-task.md"
        engine = KanbanEngine(board, activity_log=False)

        original_unlink = Path.unlink

        def failing_unlink(self_path: Path, **kwargs) -> None:
            if self_path == source:
                msg = "simulated src.unlink() failure"
                raise OSError(msg)
            return original_unlink(self_path, **kwargs)  # type: ignore[func-returns-value]

        with mock.patch.object(Path, "unlink", failing_unlink):
            result = engine.cleanup()

        assert source.exists(), "source must remain in tasks/ when src.unlink() fails"
        assert not dest.exists(), (
            "destination hard link must be rolled back when src.unlink() fails; no dual-location state is permitted"
        )
        assert len(result.skipped_items) == 1, (
            "exactly one skipped_items entry expected when no_overwrite move partially fails"
        )
