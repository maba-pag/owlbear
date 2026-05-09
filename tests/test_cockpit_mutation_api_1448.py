"""Failing tests for maintenance cleanup semantics (#1448).

RED phase — all tests must fail until cleanup is implemented in #1449 (engine)
and #1457 (Cockpit route).

AC coverage:
  AC1: cleanup() clears only expired claimed_at via CAS; live claim untouched;
       released task ID in released_claim_ids
  AC2: cleanup() moves drift-archived task file from tasks/ to archive/;
       archived task ID in archived_task_ids
  AC3: archive collision and malformed file skipped; skipped_items entry has
       path (str) and reason (str) fields; source task file not deleted
  AC4: single cleanup() call returns all three result categories at once
  AC5: POST /api/tasks/cleanup returns released_claim_ids (list[int]),
       archived_task_ids (list[int]), skipped_items (list[{path,reason}]);
       skipped_items passed through without generic error conversion
  AC6: pick_tasks, start_work, engine init, Cockpit startup, board read
       endpoints, task list refresh, and SSE event streaming do NOT invoke
       cleanup
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING
from unittest import mock

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_kanban.agent_view import AgentView

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Board helpers (consistent with test_engine_coverage_1068 patterns)
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
terminal_status: done
wave_size: 4
agent_map:
    research: researcher
    backlog: architect
    todo: test-writer
    in-progress: builder
    review: reviewer
    docs: doc-writer
    done: auditor
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

_EPOCH_TS = '"2026-01-01T00:00:00+00:00"'  # always expired (> 1 h ago)


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
    claimed_at: str = "null",
    archival_reason: str = "null",
    subdir: str = "tasks",
) -> Path:
    content = _TASK_TMPL.format(
        task_id=task_id,
        title=title,
        status=status,
        priority=priority,
        claimed_at=claimed_at,
        archival_reason=archival_reason,
    )
    path = kanban_dir / subdir / f"{task_id}-task.md"
    path.write_text(content, encoding="utf-8")
    return path


def _make_engine(base_dir: Path) -> KanbanEngine:
    kanban_dir = _make_board(base_dir)
    return KanbanEngine(kanban_dir, activity_log=False)


def _now_ts() -> str:
    """Return a quoted ISO timestamp within the 1 h claim window."""
    return f'"{datetime.now(UTC).isoformat()}"'


# ---------------------------------------------------------------------------
# Cockpit fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def kanban_dir(tmp_path: Path) -> Path:
    return _make_board(tmp_path)


@pytest.fixture
def engine(kanban_dir: Path) -> KanbanEngine:
    return KanbanEngine(kanban_dir, activity_log=False)


@pytest.fixture
def client(engine: KanbanEngine):
    from fastapi.testclient import TestClient  # noqa: PLC0415
    from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415

    app.dependency_overrides[get_engine] = lambda: engine
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# AC1 — Claim-release probe
# ---------------------------------------------------------------------------


class TestFromAC_CleanupClaimRelease:
    """AC1: cleanup() releases expired claims via CAS and reports released_claim_ids.

    Contract:
    - Expired claimed_at (> 1 h old) → task ID in result.released_claim_ids
    - Live claimed_at (< 1 h old) → NOT in released_claim_ids; file unchanged
    """

    def test_cleanup_returns_expired_task_id_in_released_claim_ids(
        self, tmp_path: Path
    ) -> None:
        """Expired claimed_at is cleared; task ID appears in released_claim_ids."""
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, status="todo", claimed_at=_EPOCH_TS)
        engine = KanbanEngine(board, activity_log=False)

        result = engine.cleanup()  # type: ignore[attr-defined]  # not yet implemented

        assert 1 in result.released_claim_ids

    def test_cleanup_leaves_live_claim_untouched(self, tmp_path: Path) -> None:
        """Live claim (< 1 h) is not cleared and not reported in released_claim_ids."""
        board = _make_board(tmp_path)
        _write_task(board, task_id=2, status="todo", claimed_at=_now_ts())
        engine = KanbanEngine(board, activity_log=False)

        result = engine.cleanup()  # type: ignore[attr-defined]  # not yet implemented

        assert 2 not in result.released_claim_ids
        # Verify on-disk: claimed_at still set
        engine.list_tasks()  # warm id→filename index
        task = engine.show_task("2")
        assert task.claimed_at is not None

    def test_cleanup_clears_expired_claimed_at_on_disk(
        self, tmp_path: Path
    ) -> None:
        """After cleanup, re-reading the expired task proves claimed_at is None on disk."""
        board = _make_board(tmp_path)
        _write_task(board, task_id=3, status="todo", claimed_at=_EPOCH_TS)
        engine = KanbanEngine(board, activity_log=False)

        result = engine.cleanup()  # type: ignore[attr-defined]

        assert 3 in result.released_claim_ids
        # Re-read from disk to prove CAS write persisted the cleared claimed_at
        task = engine.show_task("3")
        assert task.claimed_at is None, "cleanup must clear claimed_at on disk for expired task"


# ---------------------------------------------------------------------------
# AC2 — Archive-move probe
# ---------------------------------------------------------------------------


class TestFromAC_CleanupArchiveMove:
    """AC2: cleanup() moves drift-archived task files from tasks/ to archive/.

    A drift-archived file is one in tasks/ with status=archived and a valid
    archival_reason (e.g. completed). cleanup() must move it and report the
    task ID in archived_task_ids.
    """

    def test_cleanup_moves_archived_status_task_to_archive_dir(
        self, tmp_path: Path
    ) -> None:
        """Task with status=archived in tasks/ is moved to archive/."""
        board = _make_board(tmp_path)
        _write_task(
            board, task_id=1, status="archived", archival_reason='"completed"'
        )
        engine = KanbanEngine(board, activity_log=False)

        result = engine.cleanup()  # type: ignore[attr-defined]  # not yet implemented

        assert 1 in result.archived_task_ids
        assert not (board / "tasks" / "1-task.md").exists()
        assert (board / "archive" / "1-task.md").exists()


# ---------------------------------------------------------------------------
# AC3 — Safety probe
# ---------------------------------------------------------------------------


class TestFromAC_CleanupSafety:
    """AC3: collision and malformed files are skipped; skipped_items shape is correct.

    Each skipped_items entry must have:
    - path: str  — path to the skipped file
    - reason: str — human-readable reason for skipping
    Source file must not be deleted when a skip occurs.
    """

    def test_cleanup_skips_archive_collision(self, tmp_path: Path) -> None:
        """Destination file already exists in archive/ → task skipped; not in archived_task_ids."""
        board = _make_board(tmp_path)
        _write_task(
            board, task_id=1, status="archived", archival_reason='"completed"'
        )
        # Pre-create collision target
        (board / "archive" / "1-task.md").write_text(
            "collision sentinel", encoding="utf-8"
        )
        engine = KanbanEngine(board, activity_log=False)

        result = engine.cleanup()  # type: ignore[attr-defined]  # not yet implemented

        assert 1 not in result.archived_task_ids
        assert len(result.skipped_items) >= 1

    def test_cleanup_skipped_item_has_path_and_reason_fields(
        self, tmp_path: Path
    ) -> None:
        """Each skipped_items entry must expose path (str) and reason (str)."""
        board = _make_board(tmp_path)
        # Malformed frontmatter — unparseable by the engine
        (board / "tasks" / "99-bad.md").write_text(
            "not valid frontmatter at all\n", encoding="utf-8"
        )
        engine = KanbanEngine(board, activity_log=False)

        result = engine.cleanup()  # type: ignore[attr-defined]  # not yet implemented

        assert len(result.skipped_items) >= 1
        for item in result.skipped_items:
            assert "path" in item, "skipped_items entry missing 'path' field"
            assert "reason" in item, "skipped_items entry missing 'reason' field"
            assert isinstance(item["path"], str)
            assert isinstance(item["reason"], str)

    def test_cleanup_source_file_not_deleted_on_collision_skip(
        self, tmp_path: Path
    ) -> None:
        """Source task file is not deleted when archive collision causes a skip."""
        board = _make_board(tmp_path)
        source = _write_task(
            board, task_id=1, status="archived", archival_reason='"completed"'
        )
        (board / "archive" / "1-task.md").write_text(
            "collision sentinel", encoding="utf-8"
        )
        engine = KanbanEngine(board, activity_log=False)

        engine.cleanup()  # type: ignore[attr-defined]  # not yet implemented

        assert source.exists(), "Source task file must not be deleted when skip occurs"

    def test_cleanup_source_file_not_deleted_on_malformed_skip(
        self, tmp_path: Path
    ) -> None:
        """Malformed source file is not deleted when it is added to skipped_items."""
        board = _make_board(tmp_path)
        malformed = board / "tasks" / "99-bad.md"
        malformed.write_text("not valid frontmatter at all\n", encoding="utf-8")
        engine = KanbanEngine(board, activity_log=False)

        engine.cleanup()  # type: ignore[attr-defined]  # not yet implemented

        assert malformed.exists(), "malformed source file must not be deleted when skipped"


# ---------------------------------------------------------------------------
# AC4 — Single-call aggregation probe
# ---------------------------------------------------------------------------


class TestFromAC_CleanupAggregation:
    """AC4: one cleanup() invocation returns all three result categories."""

    def test_cleanup_single_call_returns_all_three_categories(
        self, tmp_path: Path
    ) -> None:
        """Board with expired claim + drift-archived task + malformed file.

        A single cleanup() call must return all three categories in one result.
        """
        board = _make_board(tmp_path)
        # Expired claim
        _write_task(board, task_id=1, status="todo", claimed_at=_EPOCH_TS)
        # Drift-archived task
        _write_task(
            board, task_id=2, status="archived", archival_reason='"completed"'
        )
        # Malformed file (will be skipped)
        (board / "tasks" / "99-bad.md").write_text(
            "not valid frontmatter\n", encoding="utf-8"
        )
        engine = KanbanEngine(board, activity_log=False)

        result = engine.cleanup()  # type: ignore[attr-defined]  # not yet implemented

        assert 1 in result.released_claim_ids, "expired claim must be released"
        assert 2 in result.archived_task_ids, "drift-archived task must be moved"
        assert len(result.skipped_items) >= 1, "malformed file must be in skipped_items"


# ---------------------------------------------------------------------------
# AC5 — Cockpit contract probe
# ---------------------------------------------------------------------------


class TestFromAC_CockpitCleanupContract:
    """AC5: POST /api/tasks/cleanup returns the correct response shape.

    Fields:
    - released_claim_ids: list[int]
    - archived_task_ids: list[int]
    - skipped_items: list[object with path (str) and reason (str)]

    Cockpit view/route passes skipped_items through without converting to a
    generic error envelope.
    """

    def test_post_cleanup_returns_200_with_correct_field_shape(
        self, client: TestClient
    ) -> None:
        """POST /api/tasks/cleanup → 200 with released_claim_ids, archived_task_ids, skipped_items."""
        response = client.post("/api/tasks/cleanup")

        assert response.status_code == 200
        body = response.json()
        assert "released_claim_ids" in body, "response missing released_claim_ids"
        assert "archived_task_ids" in body, "response missing archived_task_ids"
        assert "skipped_items" in body, "response missing skipped_items"
        assert isinstance(body["released_claim_ids"], list)
        assert isinstance(body["archived_task_ids"], list)
        assert isinstance(body["skipped_items"], list)

    def test_post_cleanup_skipped_items_are_objects_with_path_and_reason(
        self, client: TestClient, kanban_dir: Path
    ) -> None:
        """skipped_items entries are objects with path+reason, not converted to a generic error."""
        # Add a malformed file to trigger a skipped_items entry
        (kanban_dir / "tasks" / "99-bad.md").write_text(
            "not valid frontmatter\n", encoding="utf-8"
        )

        response = client.post("/api/tasks/cleanup")

        assert response.status_code == 200
        body = response.json()
        for item in body.get("skipped_items", []):
            assert "path" in item, "skipped_item missing path field"
            assert "reason" in item, "skipped_item missing reason field"

    def test_post_cleanup_skipped_items_nonempty_with_malformed_file(
        self, client: TestClient, kanban_dir: Path
    ) -> None:
        """skipped_items is non-empty when a malformed file is present; entries are typed."""
        (kanban_dir / "tasks" / "99-bad.md").write_text(
            "not valid frontmatter\n", encoding="utf-8"
        )

        response = client.post("/api/tasks/cleanup")

        assert response.status_code == 200
        body = response.json()
        assert len(body["skipped_items"]) >= 1, "malformed file must appear in skipped_items"
        for item in body["skipped_items"]:
            assert isinstance(item["path"], str), "skipped_items path must be str"
            assert isinstance(item["reason"], str), "skipped_items reason must be str"


# ---------------------------------------------------------------------------
# AC6 — Negative probe
# ---------------------------------------------------------------------------


class TestFromAC_CleanupNegativeProbe:
    """AC6: cleanup is NOT invoked by pick_tasks, start_work, engine init,
    Cockpit startup, board read endpoints, task list refresh, or SSE streaming.

    Each test asserts the cleanup interface exists on KanbanEngine AND verifies
    it is not called by the named operation.
    """

    def test_engine_init_does_not_invoke_cleanup(self, tmp_path: Path) -> None:
        """KanbanEngine.__init__ must not call cleanup()."""
        board = _make_board(tmp_path)
        assert hasattr(KanbanEngine, "cleanup"), (
            "KanbanEngine.cleanup must exist as a method"
        )
        with mock.patch.object(KanbanEngine, "cleanup") as mock_cleanup:
            KanbanEngine(board, activity_log=False)
            mock_cleanup.assert_not_called()

    def test_pick_tasks_does_not_invoke_cleanup(self, tmp_path: Path) -> None:
        """AgentView.pick_tasks must not call KanbanEngine.cleanup()."""
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, status="todo")
        engine = KanbanEngine(board, activity_log=False)
        engine.list_tasks()  # warm id→filename index
        assert hasattr(engine, "cleanup"), "KanbanEngine.cleanup() must exist"
        with mock.patch.object(engine, "cleanup") as mock_cleanup:
            view = AgentView(engine)
            view.pick_tasks()
            mock_cleanup.assert_not_called()

    def test_start_work_does_not_invoke_cleanup(self, tmp_path: Path) -> None:
        """KanbanEngine.start_work must not call cleanup()."""
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, status="todo")
        engine = KanbanEngine(board, activity_log=False)
        engine.list_tasks()
        assert hasattr(engine, "cleanup"), "KanbanEngine.cleanup() must exist"
        with mock.patch.object(engine, "cleanup") as mock_cleanup:
            engine.start_work("1")
            mock_cleanup.assert_not_called()

    def test_cockpit_get_tasks_does_not_invoke_cleanup(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """GET /api/tasks must not invoke cleanup()."""
        assert hasattr(engine, "cleanup"), "KanbanEngine.cleanup() must exist"
        with mock.patch.object(engine, "cleanup") as mock_cleanup:
            response = client.get("/api/tasks")
            assert response.status_code == 200
            mock_cleanup.assert_not_called()

    def test_cockpit_get_board_does_not_invoke_cleanup(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """GET /api/board must not invoke cleanup()."""
        assert hasattr(engine, "cleanup"), "KanbanEngine.cleanup() must exist"
        with mock.patch.object(engine, "cleanup") as mock_cleanup:
            response = client.get("/api/board")
            assert response.status_code == 200
            mock_cleanup.assert_not_called()

    def test_cockpit_sse_does_not_invoke_cleanup(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """SSE /api/events must not invoke cleanup() before streaming begins."""
        assert hasattr(engine, "cleanup"), "KanbanEngine.cleanup() must exist"
        # Patch awatch to prevent actual filesystem watching (avoids SSE deadlock)
        async def _noop_awatch(*_args, **_kwargs):  # noqa: RUF029
            return
            yield  # make it an async generator

        with (
            mock.patch("owlbear_cockpit.routes.events.awatch", _noop_awatch),
            mock.patch.object(engine, "cleanup") as mock_cleanup,
        ):
            # Only check headers — do not stream body (would deadlock with sync client)
            with client.stream("GET", "/api/events") as resp:
                assert resp.status_code == 200
            mock_cleanup.assert_not_called()
