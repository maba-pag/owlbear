"""RED tests for cockpit read API module structure and edge cases (#930).

Covers AC gaps not addressed by #928 tests:
  - owlbear_cockpit.cache: MtimeScanCache importable and correct for empty/non-empty dirs
  - owlbear_cockpit.models: Pydantic response models importable
  - owlbear_cockpit.routes.read: router importable
  - Empty board edge case: GET /api/tasks returns 200 + mtime=0, not exception
  - Engine reload: new task appears in list after file added (cache-miss reload)
  - Engine reload: removed task disappears from list after file removed
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from owlbear_kanban import KanbanEngine

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Board fixture helpers (minimal duplication from test_cockpit_read_api.py)
# ---------------------------------------------------------------------------

_CONFIG_YAML = """\
version: 10
board:
  name: TestBoard
tasks_dir: tasks
statuses:
- name: research
- name: backlog
- name: todo
- name: in-progress
- name: review
- name: docs
- name: done
priorities:
- someday
- nice-to-have
- important
- needed
- critical
defaults:
  status: research
  priority: important
claim_timeout: 1h
next_id: 1
archive_dir: archive
activity_log: false
"""


def _make_board(base_dir: Path) -> Path:
    """Create a minimal kanban board directory. Returns kanban_dir."""
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


# ---------------------------------------------------------------------------
# Fixtures — empty board (no tasks)
# ---------------------------------------------------------------------------


@pytest.fixture
def empty_board_dir(tmp_path: Path) -> Path:
    """Minimal kanban board with NO tasks — exercises the mtime=0 edge case."""
    return _make_board(tmp_path)


@pytest.fixture
def empty_engine(empty_board_dir: Path) -> KanbanEngine:
    """KanbanEngine pointed at the empty board."""
    return KanbanEngine(empty_board_dir, agent_name="test-cockpit-empty")


@pytest.fixture
def empty_client(empty_engine: KanbanEngine):
    """FastAPI TestClient with an empty-board engine injected.

    In RED phase, ``get_engine`` does not exist in ``owlbear_cockpit.main``
    so this fixture raises ImportError — all tests using it will ERROR (RED).
    """
    from fastapi.testclient import TestClient  # noqa: PLC0415
    from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415  # ImportError in RED

    app.dependency_overrides[get_engine] = lambda: empty_engine
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Fixtures — board with tasks (for reload tests)
# ---------------------------------------------------------------------------


@pytest.fixture
def board_dir(tmp_path: Path) -> Path:
    """Minimal kanban board with 2 tasks."""
    kanban_dir = _make_board(tmp_path)
    seed_engine = KanbanEngine(kanban_dir, agent_name="seed")
    seed_engine.create_task("Task One", status="todo", priority="important")
    seed_engine.create_task("Task Two", status="review", priority="needed")
    return kanban_dir


@pytest.fixture
def engine(board_dir: Path) -> KanbanEngine:
    """KanbanEngine pointed at the test board."""
    eng = KanbanEngine(board_dir, agent_name="test-cockpit")
    eng.list_tasks()  # populate id→filename cache
    return eng


@pytest.fixture
def client(engine: KanbanEngine):
    """FastAPI TestClient with a 2-task board engine injected."""
    from fastapi.testclient import TestClient  # noqa: PLC0415
    from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415  # ImportError in RED

    app.dependency_overrides[get_engine] = lambda: engine
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# AC: New modules are importable
# ---------------------------------------------------------------------------


class TestFromAC_NewModulesImportable:
    """Verify that the three new modules introduced in #930 are importable.

    Covers:
    - owlbear_cockpit.cache (MtimeScanCache)
    - owlbear_cockpit.models (response models)
    - owlbear_cockpit.routes.read (FastAPI router)
    """

    def test_cache_module_importable(self) -> None:
        """owlbear_cockpit.cache.MtimeScanCache is importable."""
        from owlbear_cockpit.cache import MtimeScanCache  # noqa: PLC0415, F401

    def test_models_task_summary_out_importable(self) -> None:
        """owlbear_cockpit.models.TaskSummaryOut is importable."""
        from owlbear_cockpit.models import TaskSummaryOut  # noqa: PLC0415, F401

    def test_models_task_detail_out_importable(self) -> None:
        """owlbear_cockpit.models.TaskDetailOut is importable."""
        from owlbear_cockpit.models import TaskDetailOut  # noqa: PLC0415, F401

    def test_models_board_out_importable(self) -> None:
        """owlbear_cockpit.models.BoardOut is importable."""
        from owlbear_cockpit.models import BoardOut  # noqa: PLC0415, F401

    def test_models_session_out_importable(self) -> None:
        """owlbear_cockpit.models.SessionOut is importable."""
        from owlbear_cockpit.models import SessionOut  # noqa: PLC0415, F401

    def test_routes_read_router_importable(self) -> None:
        """owlbear_cockpit.routes.read exposes a FastAPI APIRouter named router."""
        from fastapi import APIRouter  # noqa: PLC0415
        from owlbear_cockpit.routes.read import router  # noqa: PLC0415

        assert isinstance(router, APIRouter), (
            f"routes.read.router must be an APIRouter, got {type(router).__name__}"
        )


# ---------------------------------------------------------------------------
# AC: Pydantic response models
# ---------------------------------------------------------------------------


class TestFromAC_PydanticResponseModels:
    """Verify that all response models are Pydantic BaseModel subclasses.

    Covers AC item: 'Pydantic response models for all endpoints'.
    """

    def test_task_summary_out_is_pydantic_model(self) -> None:
        """TaskSummaryOut is a pydantic BaseModel subclass."""
        from pydantic import BaseModel  # noqa: PLC0415
        from owlbear_cockpit.models import TaskSummaryOut  # noqa: PLC0415

        assert issubclass(TaskSummaryOut, BaseModel), (
            "TaskSummaryOut must be a pydantic BaseModel"
        )

    def test_task_detail_out_is_pydantic_model(self) -> None:
        """TaskDetailOut is a pydantic BaseModel subclass."""
        from pydantic import BaseModel  # noqa: PLC0415
        from owlbear_cockpit.models import TaskDetailOut  # noqa: PLC0415

        assert issubclass(TaskDetailOut, BaseModel), (
            "TaskDetailOut must be a pydantic BaseModel"
        )

    def test_board_out_is_pydantic_model(self) -> None:
        """BoardOut is a pydantic BaseModel subclass."""
        from pydantic import BaseModel  # noqa: PLC0415
        from owlbear_cockpit.models import BoardOut  # noqa: PLC0415

        assert issubclass(BoardOut, BaseModel), (
            "BoardOut must be a pydantic BaseModel"
        )

    def test_session_out_is_pydantic_model(self) -> None:
        """SessionOut is a pydantic BaseModel subclass."""
        from pydantic import BaseModel  # noqa: PLC0415
        from owlbear_cockpit.models import SessionOut  # noqa: PLC0415

        assert issubclass(SessionOut, BaseModel), (
            "SessionOut must be a pydantic BaseModel"
        )


# ---------------------------------------------------------------------------
# AC: Empty board edge case — mtime=0, no ValueError
# ---------------------------------------------------------------------------


class TestFromAC_EmptyBoardEdgeCase:
    """GET /api/tasks on a board with zero task files must not raise an exception.

    Covers AC item: mtime-scan cache must handle empty tasks dir with max(..., default=0).
    Architecture note: 'os.scandir() on empty tasks dir raises ValueError from max()
    unless handled with max(..., default=0)'.
    """

    def test_empty_board_tasks_returns_200(self, empty_client: TestClient) -> None:
        """GET /api/tasks on a board with no task files returns HTTP 200 (no exception)."""
        response = empty_client.get("/api/tasks")
        assert response.status_code == 200

    def test_empty_board_tasks_list_is_empty(self, empty_client: TestClient) -> None:
        """GET /api/tasks on empty board returns an empty tasks list."""
        response = empty_client.get("/api/tasks")
        assert response.status_code == 200
        body = response.json()
        assert "tasks" in body
        assert body["tasks"] == [], (
            f"Expected empty tasks list for empty board, got {body['tasks']!r}"
        )

    def test_empty_board_tasks_mtime_is_zero(self, empty_client: TestClient) -> None:
        """GET /api/tasks on empty board returns mtime=0 (no task files → default 0)."""
        response = empty_client.get("/api/tasks")
        assert response.status_code == 200
        body = response.json()
        assert "mtime" in body
        assert body["mtime"] == 0, (
            f"Expected mtime=0 for empty board, got {body['mtime']!r}"
        )


# ---------------------------------------------------------------------------
# AC: MtimeScanCache unit — empty dir, non-empty dir, max mtime
# ---------------------------------------------------------------------------


class TestFromAC_MtimeScanCacheUnit:
    """Unit tests for MtimeScanCache — directly tests the cache module contract.

    Covers AC item: 'os.scandir() builds {filename: mtime_ns} dict on tasks dir'.
    """

    def test_mtime_scan_cache_instantiable_with_path(self, tmp_path: Path) -> None:
        """MtimeScanCache can be instantiated with a Path argument."""
        from owlbear_cockpit.cache import MtimeScanCache  # noqa: PLC0415

        cache = MtimeScanCache(tmp_path)
        assert cache is not None

    def test_empty_dir_scan_returns_zero(self, tmp_path: Path) -> None:
        """MtimeScanCache.scan() returns 0 when the directory contains no files."""
        from owlbear_cockpit.cache import MtimeScanCache  # noqa: PLC0415

        cache = MtimeScanCache(tmp_path)
        assert cache.scan() == 0, (
            "Empty tasks dir must return mtime=0 (max with default=0)"
        )

    def test_non_empty_dir_scan_returns_positive_int(self, tmp_path: Path) -> None:
        """MtimeScanCache.scan() returns a positive integer when files are present."""
        from owlbear_cockpit.cache import MtimeScanCache  # noqa: PLC0415

        (tmp_path / "1-task.md").write_text("# task", encoding="utf-8")
        cache = MtimeScanCache(tmp_path)
        result = cache.scan()
        assert isinstance(result, int), f"scan() must return int, got {type(result).__name__}"
        assert result > 0, "scan() must return positive mtime_ns when files are present"

    def test_scan_returns_max_mtime_across_files(self, tmp_path: Path) -> None:
        """MtimeScanCache.scan() returns the maximum mtime_ns across all files."""
        from owlbear_cockpit.cache import MtimeScanCache  # noqa: PLC0415

        f1 = tmp_path / "1-task.md"
        f1.write_text("# task 1", encoding="utf-8")
        # Small sleep ensures f2 has a strictly higher mtime
        time.sleep(0.01)
        f2 = tmp_path / "2-task.md"
        f2.write_text("# task 2", encoding="utf-8")

        expected_max = max(
            f1.stat().st_mtime_ns,
            f2.stat().st_mtime_ns,
        )
        cache = MtimeScanCache(tmp_path)
        assert cache.scan() == expected_max, (
            "scan() must return the maximum mtime_ns, not the first or minimum"
        )

    def test_scan_is_repeatable_with_no_changes(self, tmp_path: Path) -> None:
        """Two consecutive scan() calls with no file changes return the same value."""
        from owlbear_cockpit.cache import MtimeScanCache  # noqa: PLC0415

        (tmp_path / "1-task.md").write_text("# task", encoding="utf-8")
        cache = MtimeScanCache(tmp_path)
        assert cache.scan() == cache.scan(), (
            "scan() must return a stable value when files are unchanged"
        )


# ---------------------------------------------------------------------------
# AC: Engine reload when mtime changes (observable via HTTP)
# ---------------------------------------------------------------------------


class TestFromAC_EngineReloadOnMtimeChange:
    """New tasks created between requests must be reflected in the task list.

    Covers AC item: 'full engine reload only when mtime changes'.
    Tested at the HTTP level: the observable contract is that fresh file state
    appears in the response after a file-modifying operation.
    """

    def test_new_task_appears_in_list_after_creation(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """A task created after the first request appears in a subsequent request."""
        r1 = client.get("/api/tasks")
        assert r1.status_code == 200
        count_before = len(r1.json()["tasks"])

        engine.create_task("New task via engine", status="todo", priority="important")

        r2 = client.get("/api/tasks")
        assert r2.status_code == 200
        count_after = len(r2.json()["tasks"])
        assert count_after > count_before, (
            f"New task must appear in subsequent GET /api/tasks response "
            f"(before={count_before}, after={count_after})"
        )

    def test_mtime_increases_after_new_task_created(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """Creating a new task file increases the mtime returned by GET /api/tasks."""
        r1 = client.get("/api/tasks")
        assert r1.status_code == 200
        mtime_before = r1.json()["mtime"]

        engine.create_task("Another new task", status="backlog", priority="someday")

        r2 = client.get("/api/tasks")
        assert r2.status_code == 200
        mtime_after = r2.json()["mtime"]
        assert mtime_after > mtime_before, (
            f"mtime must increase after a new task file is created "
            f"(before={mtime_before}, after={mtime_after})"
        )
