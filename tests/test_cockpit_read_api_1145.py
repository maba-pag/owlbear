"""Failing tests for cockpit cache-hit short-circuit restoration (#1145).

Covers AC:
  - MtimeScanCache.has_changed() gates engine.list_tasks() calls — cache hit
    returns cached tasks without calling engine.list_tasks().
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from owlbear_kanban import KanbanEngine

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

    from owlbear_cockpit.cache import MtimeScanCache


# ---------------------------------------------------------------------------
# Board fixture helpers
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
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def board_dir(tmp_path: Path) -> Path:
    """Kanban board with 3 tasks across different statuses/priorities/tags."""
    kanban_dir = _make_board(tmp_path)
    seed = KanbanEngine(kanban_dir, agent_name="seed")
    seed.create_task("Alpha", status="todo", priority="important")
    seed.create_task("Beta", status="review", priority="needed")
    seed.create_task("Gamma", status="todo", priority="someday", tags=["scope:x"])
    return kanban_dir


@pytest.fixture
def engine(board_dir: Path) -> KanbanEngine:
    """KanbanEngine pointed at the test board."""
    eng = KanbanEngine(board_dir, agent_name="test-cockpit")
    eng.list_tasks()  # populate id→filename cache
    return eng


@pytest.fixture
def cache(board_dir: Path) -> MtimeScanCache:
    """Known MtimeScanCache instance for the test board's tasks directory."""
    from owlbear_cockpit.cache import MtimeScanCache  # noqa: PLC0415

    return MtimeScanCache(board_dir / "tasks")


@pytest.fixture
def cache_client(engine: KanbanEngine, cache: MtimeScanCache) -> TestClient:
    """TestClient with get_engine and get_cache both overridden.

    Overriding get_cache ensures tests inspect the exact same MtimeScanCache
    instance that the route handler uses.
    """
    from fastapi.testclient import TestClient  # noqa: PLC0415

    from owlbear_cockpit.deps import get_cache  # noqa: PLC0415
    from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415

    app.dependency_overrides[get_engine] = lambda: engine
    app.dependency_overrides[get_cache] = lambda: cache
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Fixtures — empty board (no tasks) for empty-board cache-hit regression guard
# ---------------------------------------------------------------------------


@pytest.fixture
def empty_board_dir(tmp_path: Path) -> Path:
    """Minimal board with no tasks — exercises the cached-empty-list branch."""
    base = tmp_path / "empty"
    base.mkdir()
    return _make_board(base)


@pytest.fixture
def empty_engine(empty_board_dir: Path) -> KanbanEngine:
    """KanbanEngine pointed at the empty board."""
    return KanbanEngine(empty_board_dir, agent_name="test-cockpit-empty")


@pytest.fixture
def empty_cache(empty_board_dir: Path) -> MtimeScanCache:
    """Known MtimeScanCache instance for the empty board's tasks directory."""
    from owlbear_cockpit.cache import MtimeScanCache  # noqa: PLC0415

    return MtimeScanCache(empty_board_dir / "tasks")


@pytest.fixture
def empty_cache_client(empty_engine: KanbanEngine, empty_cache: MtimeScanCache) -> TestClient:
    """TestClient with get_engine and get_cache overridden for the empty board.

    Overriding get_cache ensures tests inspect the exact same MtimeScanCache
    instance the route handler uses — required for empty-board cache-hit proof.
    """
    from fastapi.testclient import TestClient  # noqa: PLC0415

    from owlbear_cockpit.deps import get_cache  # noqa: PLC0415
    from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415

    app.dependency_overrides[get_engine] = lambda: empty_engine
    app.dependency_overrides[get_cache] = lambda: empty_cache
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# AC: MtimeScanCache.has_changed() gates engine.list_tasks() calls
# ---------------------------------------------------------------------------


class TestFromAC_CacheHitShortCircuit:
    """AC: MtimeScanCache.has_changed() gates engine.list_tasks() calls.

    Cache hit (unchanged task-dir mtime) must return cached tasks without
    calling engine.list_tasks().
    """

    # -- Happy path -----------------------------------------------------------

    def test_cache_hit_skips_engine_call(
        self,
        cache_client: TestClient,
        engine: KanbanEngine,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """engine.list_tasks() is NOT called on second GET /api/tasks when mtime unchanged."""
        r1 = cache_client.get("/api/tasks")
        assert r1.status_code == 200

        call_count = 0
        original = engine.list_tasks

        def counting(*args: object, **kwargs: object) -> object:
            nonlocal call_count
            call_count += 1
            return original(*args, **kwargs)

        monkeypatch.setattr(engine, "list_tasks", counting)

        r2 = cache_client.get("/api/tasks")
        assert r2.status_code == 200
        assert call_count == 0, (
            f"engine.list_tasks() called {call_count} times on cache hit, expected 0"
        )

    def test_has_changed_called_updates_last_mtime(
        self,
        cache_client: TestClient,
        cache: MtimeScanCache,
    ) -> None:
        """cache.last_mtime > 0 after first GET /api/tasks — has_changed() was invoked."""
        assert cache.last_mtime == 0, "Cache must start with last_mtime=0 before any request"
        cache_client.get("/api/tasks")
        assert cache.last_mtime > 0, (
            "cache.last_mtime must be updated after GET /api/tasks — "
            "has_changed() must be called in the route handler"
        )

    # -- Edge cases: filter parameters on cache-hit path ---------------------

    def test_status_filter_on_cache_hit_skips_engine(
        self,
        cache_client: TestClient,
        engine: KanbanEngine,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """engine.list_tasks() NOT called when ?status= filter applied on cache hit."""
        cache_client.get("/api/tasks")  # first request — populate cache

        call_count = 0
        original = engine.list_tasks

        def counting(*args: object, **kwargs: object) -> object:
            nonlocal call_count
            call_count += 1
            return original(*args, **kwargs)

        monkeypatch.setattr(engine, "list_tasks", counting)

        r = cache_client.get("/api/tasks?status=todo")
        assert r.status_code == 200
        assert call_count == 0, (
            f"engine.list_tasks() called {call_count} times on status-filtered "
            f"cache hit, expected 0"
        )

    def test_priority_filter_on_cache_hit_skips_engine(
        self,
        cache_client: TestClient,
        engine: KanbanEngine,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """engine.list_tasks() NOT called when ?priority= filter applied on cache hit."""
        cache_client.get("/api/tasks")

        call_count = 0
        original = engine.list_tasks

        def counting(*args: object, **kwargs: object) -> object:
            nonlocal call_count
            call_count += 1
            return original(*args, **kwargs)

        monkeypatch.setattr(engine, "list_tasks", counting)

        r = cache_client.get("/api/tasks?priority=important")
        assert r.status_code == 200
        assert call_count == 0, (
            f"engine.list_tasks() called {call_count} times on priority-filtered "
            f"cache hit, expected 0"
        )

    def test_tag_filter_on_cache_hit_skips_engine(
        self,
        cache_client: TestClient,
        engine: KanbanEngine,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """engine.list_tasks() NOT called when ?tag= filter applied on cache hit."""
        cache_client.get("/api/tasks")

        call_count = 0
        original = engine.list_tasks

        def counting(*args: object, **kwargs: object) -> object:
            nonlocal call_count
            call_count += 1
            return original(*args, **kwargs)

        monkeypatch.setattr(engine, "list_tasks", counting)

        r = cache_client.get("/api/tasks?tag=scope%3Ax")
        assert r.status_code == 200
        assert call_count == 0, (
            f"engine.list_tasks() called {call_count} times on tag-filtered "
            f"cache hit, expected 0"
        )

    def test_blocked_filter_on_cache_hit_skips_engine(
        self,
        cache_client: TestClient,
        engine: KanbanEngine,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """engine.list_tasks() NOT called when ?blocked= filter applied on cache hit."""
        cache_client.get("/api/tasks")

        call_count = 0
        original = engine.list_tasks

        def counting(*args: object, **kwargs: object) -> object:
            nonlocal call_count
            call_count += 1
            return original(*args, **kwargs)

        monkeypatch.setattr(engine, "list_tasks", counting)

        r = cache_client.get("/api/tasks?blocked=false")
        assert r.status_code == 200
        assert call_count == 0, (
            f"engine.list_tasks() called {call_count} times on blocked-filtered "
            f"cache hit, expected 0"
        )

    def test_status_filter_returns_correct_tasks_on_cache_hit(
        self,
        cache_client: TestClient,
        engine: KanbanEngine,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Status filter applied in Python on cache hit returns only matching tasks."""
        cache_client.get("/api/tasks")  # populate cache

        call_count = 0
        original = engine.list_tasks

        def counting(*args: object, **kwargs: object) -> object:
            nonlocal call_count
            call_count += 1
            return original(*args, **kwargs)

        monkeypatch.setattr(engine, "list_tasks", counting)

        r = cache_client.get("/api/tasks?status=todo")
        assert r.status_code == 200
        assert call_count == 0, "engine.list_tasks() must NOT be called on cache hit"
        tasks = r.json()["tasks"]
        assert len(tasks) > 0, "Expected at least 1 'todo' task in test board"
        assert all(t["status"] == "todo" for t in tasks), (
            f"All returned tasks must have status='todo' on filtered cache hit, got {tasks!r}"
        )

    # -- Boundary conditions --------------------------------------------------

    def test_multiple_consecutive_requests_all_skip_engine(
        self,
        cache_client: TestClient,
        engine: KanbanEngine,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """engine.list_tasks() NOT called on 2nd, 3rd, or 4th requests when files unchanged."""
        cache_client.get("/api/tasks")  # first request — cache populated

        call_count = 0
        original = engine.list_tasks

        def counting(*args: object, **kwargs: object) -> object:
            nonlocal call_count
            call_count += 1
            return original(*args, **kwargs)

        monkeypatch.setattr(engine, "list_tasks", counting)

        for _ in range(3):
            r = cache_client.get("/api/tasks")
            assert r.status_code == 200

        assert call_count == 0, (
            f"engine.list_tasks() called {call_count} times across 3 consecutive "
            f"cache-hit requests, expected 0"
        )

    def test_first_request_populates_cache_tasks(
        self,
        cache_client: TestClient,
        cache: MtimeScanCache,
    ) -> None:
        """cache.tasks is populated with all tasks after the first GET /api/tasks."""
        assert cache.tasks == [], "cache.tasks must start empty"
        cache_client.get("/api/tasks")
        assert len(cache.tasks) > 0, (
            "cache.tasks must be populated after first GET /api/tasks — "
            "the route must store engine results in cache.tasks on cache miss"
        )

    def test_empty_board_second_request_skips_engine_call(
        self,
        empty_cache_client: TestClient,
        empty_engine: KanbanEngine,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """engine.list_tasks() NOT called on 2nd unchanged request when cached result is [].

        Regression guard: distinguishes 'cache never populated' from 'cached empty list'.
        A route that uses `or not cache.tasks` instead of `or not cache.has_cached_tasks`
        would call engine.list_tasks() on every empty-board request — this test catches that.
        """
        # First request: cache populated with empty task list
        r1 = empty_cache_client.get("/api/tasks")
        assert r1.status_code == 200
        assert r1.json()["tasks"] == [], "Empty board must return empty task list"

        # Monkeypatch AFTER first request so only second-request calls are counted
        call_count = 0
        original = empty_engine.list_tasks

        def counting(*args: object, **kwargs: object) -> object:
            nonlocal call_count
            call_count += 1
            return original(*args, **kwargs)

        monkeypatch.setattr(empty_engine, "list_tasks", counting)

        # Second request: file mtime unchanged — must use cached [] without engine call
        r2 = empty_cache_client.get("/api/tasks")
        assert r2.status_code == 200
        assert r2.json()["tasks"] == [], "Second empty-board response must also be empty"
        assert call_count == 0, (
            f"engine.list_tasks() called {call_count} times on second unchanged "
            f"empty-board request — cached [] must be treated as a valid cache hit"
        )
