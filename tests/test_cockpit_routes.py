"""Cockpit route contract regression tests.

Behavioral coverage:
  G1: GET /api/tasks route uses cockpit-specific response model with mtime injected
      from MtimeScanCache (not bare ListTasksResponse which strips mtime field).
  G4: POST /api/tasks/{id}/edit preserves block:user tag lifecycle (D21 adapter contract):
      - block:user added when block_reason is set (TestFromAC_BlockUserTagLifecycle)
      - block:user removed when block_reason cleared
      - task-fetch guard expanded to include block_reason field
      - conflict resolution strips contradictory _apply_list_diff entries
        (TestFromAC_BlockUserTagConflict)
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest import mock

import pytest

from owlbear_kanban import KanbanEngine

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

# Provenance: promoted from task-scoped suite for task #1144.


# ---------------------------------------------------------------------------
# Board fixture helpers
# ---------------------------------------------------------------------------

_CONFIG_YAML = """\
next_id: 1
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
    """Board with 2 tasks.

    Task 1: status=build, priority=medium, no tags (mtime + block-lifecycle target)
    Task 2: status=build, priority=high, tags=[scope:cockpit, block:user], blocked=True
            (pre-blocked for conflict and unblock tests)
    """
    kanban_dir = _make_board(tmp_path)
    seed = KanbanEngine(kanban_dir)
    seed.create_task("Alpha task", status="build", priority="medium")
    seed.create_task("Beta blocked", status="build", priority="high", tags=["scope:cockpit"])
    seed.list_tasks()  # populate id→filename cache
    seed.edit_task("2", blocked=True, block_reason="setup block", add_tags=["block:user"])
    return kanban_dir


@pytest.fixture
def engine(board_dir: Path) -> KanbanEngine:
    """KanbanEngine with agent_name='cockpit' and cache pre-warmed."""
    eng = KanbanEngine(board_dir)
    eng.list_tasks()  # populate id→filename cache
    return eng


@pytest.fixture
def client(engine: KanbanEngine):
    """FastAPI TestClient with engine injected via dependency_overrides."""
    from fastapi.testclient import TestClient  # noqa: PLC0415
    from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415

    app.dependency_overrides[get_engine] = lambda: engine
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# AC G1: GET /api/tasks returns mtime from MtimeScanCache
# ---------------------------------------------------------------------------


class TestFromAC_MtimeInjection:
    """GET /api/tasks must return mtime field injected from MtimeScanCache.

    Root cause: route declares response_model=ListTasksResponse which strips any
    extra fields; mtime is therefore absent.  Fix: cockpit-specific response model
    that includes mtime alongside engine envelope fields, with value read from the
    injected MtimeScanCache dependency.

    All tests FAIL until the route uses a cockpit response model that surfaces mtime.
    """

    def test_list_tasks_response_has_mtime_field(self, client: TestClient) -> None:
        """GET /api/tasks response body must contain a 'mtime' key.

        happy — currently absent because ListTasksResponse has no mtime field
        and FastAPI response_model strips unknown fields.
        FAIL: 'mtime' key missing from response body.
        """
        response = client.get("/api/tasks")
        assert response.status_code == 200
        body = response.json()
        assert "mtime" in body  # FAIL: ListTasksResponse strips mtime

    def test_list_tasks_mtime_is_integer(self, client: TestClient) -> None:
        """GET /api/tasks mtime value must be an integer (nanoseconds since epoch).

        happy — type contract; field is absent so any assertion on type also fails.
        FAIL: 'mtime' key absent → assertion fails.
        """
        response = client.get("/api/tasks")
        assert response.status_code == 200
        body = response.json()
        assert "mtime" in body, "mtime field absent from response"  # FAIL
        assert isinstance(body["mtime"], int)

    def test_list_tasks_mtime_injected_from_mtimescancache(self, engine: KanbanEngine) -> None:
        """GET /api/tasks mtime value must equal MtimeScanCache.scan() for the tasks dir.

        boundary — verifies the route reads mtime from the injected cache dependency
        (not a hardcoded default or unrelated source).
        FAIL: even if mtime appeared in response, the route does not call cache.scan(),
        so the sentinel value would not match.
        """
        from fastapi.testclient import TestClient  # noqa: PLC0415

        from owlbear_cockpit.cache import MtimeScanCache  # noqa: PLC0415
        from owlbear_cockpit.deps import get_cache  # noqa: PLC0415
        from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415

        sentinel_mtime = 777_000_111_222_333
        mock_cache = mock.MagicMock(spec=MtimeScanCache)
        mock_cache.scan.return_value = sentinel_mtime

        app.dependency_overrides[get_engine] = lambda: engine
        app.dependency_overrides[get_cache] = lambda: mock_cache
        try:
            test_client = TestClient(app)
            response = test_client.get("/api/tasks")
            assert response.status_code == 200
            body = response.json()
            assert "mtime" in body, "mtime field absent from response"  # FAIL
            assert body["mtime"] == sentinel_mtime, (
                f"route did not read mtime from MtimeScanCache.scan(); "
                f"expected {sentinel_mtime}, got {body.get('mtime')}"
            )  # FAIL: route does not call cache.scan()
        finally:
            app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# AC G4: block:user tag lifecycle — TestFromAC_BlockUserTagLifecycle
# ---------------------------------------------------------------------------


class TestFromAC_BlockUserTagLifecycle:
    """POST /api/tasks/{id}/edit must manage the block:user tag via _apply_block_kwargs.

    D21 adapter contract (blocking brief): the cockpit edit route is responsible for
    adding/removing the block:user tag whenever block_reason is set or cleared.
    The task-fetch guard must also expand to include block_reason so _apply_block_kwargs
    has access to current tag state even when tags/depends_on are not in the request.

    All tests FAIL until _apply_block_kwargs is implemented in the edit route.
    """

    def test_edit_block_reason_set_adds_block_user_tag(self, client: TestClient, engine: KanbanEngine) -> None:
        """Setting block_reason in an edit request adds 'block:user' to task tags.

        happy — cockpit adapter must inject add_tag=['block:user'] when block_reason
        is non-null, regardless of whether tags are also in the request.
        FAIL: no _apply_block_kwargs helper; block:user is never added to kwargs.
        """
        task = engine.show_task("1")
        assert "block:user" not in task.tags  # setup guard: task 1 has no block:user

        response = client.post(
            "/api/tasks/1/edit",
            json={"updated": task.updated, "block_reason": "blocked by user"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["blocked"] is True
        assert "block:user" in body["tags"]  # FAIL: _apply_block_kwargs not implemented

    def test_edit_null_block_reason_removes_block_user_tag(self, client: TestClient, engine: KanbanEngine) -> None:
        """Clearing block_reason (null) removes 'block:user' from task tags.

        happy — cockpit adapter must inject remove_tag=['block:user'] when block_reason
        is null (unblock path).  Task 2 is pre-blocked with block:user.
        FAIL: no _apply_block_kwargs; block:user remains in tags after unblock.
        """
        task = engine.show_task("2")
        assert "block:user" in task.tags  # setup guard
        assert task.blocked is True

        response = client.post(
            "/api/tasks/2/edit",
            json={"updated": task.updated, "block_reason": None},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["blocked"] is False
        assert "block:user" not in body["tags"]  # FAIL: no remove_tag via _apply_block_kwargs

    def test_edit_block_reason_with_other_tags_adds_block_user_tag(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """Blocking with tags field also present adds block:user alongside explicit tags.

        edge — tests the combined path where task-fetch is triggered by tags field
        AND _apply_block_kwargs must add block:user on top of the tags diff result.
        Task 1 starts empty-tagged; request sets tags=['scope:test'] and block_reason.
        FAIL: _apply_block_kwargs not called; only scope:test added, not block:user.
        """
        task = engine.show_task("1")
        assert not task.tags  # setup guard: task 1 has no tags

        response = client.post(
            "/api/tasks/1/edit",
            json={
                "updated": task.updated,
                "tags": ["scope:test"],
                "block_reason": "blocked with explicit tags",
            },
        )
        assert response.status_code == 200
        body = response.json()
        tags = set(body["tags"])
        assert "scope:test" in tags
        assert "block:user" in tags  # FAIL: _apply_block_kwargs not called alongside tags diff


# ---------------------------------------------------------------------------
# AC G4: conflict resolution — TestFromAC_BlockUserTagConflict
# ---------------------------------------------------------------------------


class TestFromAC_BlockUserTagConflict:
    """Conflict resolution: _apply_block_kwargs wins over contradictory _apply_list_diff entries.

    When the tags diff (_apply_list_diff) and the block helper (_apply_block_kwargs) produce
    contradictory operations on block:user, the block helper result is authoritative:
    - block_reason set → add_tag=['block:user'] wins even if tags diff says remove_tag=['block:user']
    - block_reason null → remove_tag=['block:user'] wins even if tags diff leaves block:user unchanged

    All tests FAIL until conflict resolution strips contradictory _apply_list_diff entries.
    """

    def test_tags_diff_removes_block_user_but_block_reason_set_overrides(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """Tags=[scope:cockpit] removes block:user via diff, but block_reason wins.

        error — conflict: _apply_list_diff produces remove_tag=[block:user] because
        desired tags omit it; _apply_block_kwargs produces add_tag=[block:user] because
        block_reason is non-null.  Conflict resolution: block helper wins, contradictory
        remove_tag entry is stripped.
        Task 2 has [scope:cockpit, block:user]; request sets tags=[scope:cockpit] (removes
        block:user) and block_reason='still blocked'.
        FAIL: current code applies remove_tag=[block:user] without conflict resolution,
        removing block:user even though block_reason is set.
        """
        task = engine.show_task("2")
        assert "block:user" in task.tags  # setup guard
        assert "scope:cockpit" in task.tags

        response = client.post(
            "/api/tasks/2/edit",
            json={
                "updated": task.updated,
                "tags": ["scope:cockpit"],  # diff: remove block:user from desired
                "block_reason": "still blocked by user",  # block helper: add block:user
            },
        )
        assert response.status_code == 200
        body = response.json()
        # block_reason wins: block:user must survive despite tags diff requesting removal
        assert "block:user" in body["tags"]  # FAIL: no conflict resolution; diff removes block:user
        assert "scope:cockpit" in body["tags"]

    def test_tags_diff_keeps_block_user_but_null_block_reason_overrides(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """Tags=[block:user, scope:cockpit] keeps block:user, but unblock wins.

        error — conflict: _apply_list_diff produces no-op for block:user (desired = current);
        _apply_block_kwargs produces remove_tag=[block:user] because block_reason is null.
        Conflict resolution: unblock wins — block:user is removed even though tags diff
        would preserve it.
        Task 2 has [scope:cockpit, block:user]; request sets tags=[block:user, scope:cockpit]
        (no change in diff) and block_reason=null (unblock).
        FAIL: current code applies no remove_tag for block:user (diff = no-op),
        so block:user stays in tags after unblocking.
        """
        task = engine.show_task("2")
        assert "block:user" in task.tags  # setup guard
        assert "scope:cockpit" in task.tags

        response = client.post(
            "/api/tasks/2/edit",
            json={
                "updated": task.updated,
                "tags": ["block:user", "scope:cockpit"],  # diff: no-op (keep both)
                "block_reason": None,  # unblock: remove_tag=[block:user]
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["blocked"] is False
        # unblock wins: block:user must be removed despite tags diff being no-op
        assert "block:user" not in body["tags"]  # FAIL: no _apply_block_kwargs + conflict resolution
        assert "scope:cockpit" in body["tags"]
