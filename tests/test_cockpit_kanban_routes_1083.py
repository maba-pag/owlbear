"""Failing tests for #1083 — cockpit backend admin routes: scan, repair, compact-activity.

RED phase — all tests must fail until the builder implements the admin routes.

AC coverage:
  Admin routes: POST /api/tasks/scan     → delegates to CockpitView.scan_corruption()
                POST /api/tasks/repair   → delegates to CockpitView.repair_storage()
                POST /api/tasks/compact-activity → delegates to CockpitView.compact_activity()
  DI pattern:   get_engine override reaches all three admin routes
  Response shapes:
    scan             → list (empty when no corruption detected)
    repair           → list of RepairOutcome objects (task_id, file_path, code, action, detail)
    compact-activity → ActivityCompactionResult (before_bytes, after_bytes, records_compacted)
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest import mock

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_kanban.models import ActivityCompactionResult

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Board fixture helpers
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
    """Board with one task; used as a clean (no-corruption) target for admin ops."""
    kanban_dir = _make_board(tmp_path)
    seed = KanbanEngine(kanban_dir, agent_name="seed")
    seed.create_task("Alpha task", status="todo", priority="important")
    return kanban_dir


@pytest.fixture
def engine(board_dir: Path) -> KanbanEngine:
    """KanbanEngine with activity logging enabled."""
    eng = KanbanEngine(board_dir, agent_name="cockpit", activity_log=True)
    eng.list_tasks()  # populate id→filename cache
    return eng


@pytest.fixture
def client(engine: KanbanEngine):
    """FastAPI TestClient with cockpit engine injected via dependency_overrides."""
    from fastapi.testclient import TestClient  # noqa: PLC0415
    from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415

    app.dependency_overrides[get_engine] = lambda: engine
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def view_mock() -> mock.MagicMock:
    """Isolated MagicMock representing CockpitView for delegation tests."""
    return mock.MagicMock()


@pytest.fixture
def mock_client(engine: KanbanEngine, view_mock: mock.MagicMock):
    """FastAPI TestClient with real engine and mocked CockpitView (get_view overridden)."""
    from fastapi.testclient import TestClient  # noqa: PLC0415
    from owlbear_cockpit.deps import get_view  # noqa: PLC0415
    from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415

    app.dependency_overrides[get_engine] = lambda: engine
    app.dependency_overrides[get_view] = lambda: view_mock
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# TestFromAC_AdminRoutes
# ---------------------------------------------------------------------------


class TestFromAC_AdminRoutes:
    """Tests for admin routes: scan, repair, compact-activity.

    RED phase: all tests must fail until the builder registers these routes.

    Categories:
      happy    — route exists, correct status code, correct response shape
      edge     — clean board (no corruption, no repairs needed)
      boundary — compact-activity with no prior activity log data
    """

    # ===================================================================
    # AC: POST /api/tasks/scan delegates to CockpitView.scan_corruption()
    # ===================================================================

    def test_scan_endpoint_returns_200(self, client: TestClient) -> None:
        """POST /api/tasks/scan must exist and return HTTP 200.

        happy — route does not yet exist.
        FAIL: 404 (route not registered).
        """
        response = client.post("/api/tasks/scan")
        assert response.status_code == 200  # FAIL: 404

    def test_scan_response_is_list(self, client: TestClient) -> None:
        """POST /api/tasks/scan must return a JSON array.

        happy — route does not yet exist.
        FAIL: 404 (route not registered).
        """
        response = client.post("/api/tasks/scan")
        assert response.status_code == 200  # FAIL: 404
        assert isinstance(response.json(), list)

    def test_scan_clean_board_returns_empty_list(self, client: TestClient) -> None:
        """POST /api/tasks/scan on a clean board must return an empty list.

        edge — no corrupt files in tasks or archive dirs → no issues to report.
        FAIL: 404 (route not registered).
        """
        response = client.post("/api/tasks/scan")
        assert response.status_code == 200  # FAIL: 404
        data = response.json()
        assert isinstance(data, list)
        assert data == []  # clean board has no corruption

    def test_scan_delegates_to_cockpit_view_scan_corruption(
        self,
        mock_client: TestClient,
        view_mock: mock.MagicMock,
    ) -> None:
        """POST /api/tasks/scan must call CockpitView.scan_corruption() exactly once.

        happy — route does not exist; mock is never called.
        FAIL: view_mock.scan_corruption.assert_called_once() raises (0 calls).
        """
        view_mock.scan_corruption.return_value = []
        response = mock_client.post("/api/tasks/scan")
        assert response.status_code == 200  # FAIL: 404
        view_mock.scan_corruption.assert_called_once()  # FAIL: never called

    def test_scan_returns_list_of_corruption_items_when_corruption_detected(
        self,
        mock_client: TestClient,
        view_mock: mock.MagicMock,
    ) -> None:
        """POST /api/tasks/scan with mock returning corruption items → non-empty list.

        happy — verifies that scan results are serialized and returned from the route.
        FAIL: 404 (route not registered); mock side never reached.
        """
        view_mock.scan_corruption.return_value = [
            {"code": "ERR_CORRUPT_MISSING_ID", "detail": "missing id field", "file_path": "tasks/001.md"}
        ]
        response = mock_client.post("/api/tasks/scan")
        assert response.status_code == 200  # FAIL: 404
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1

    # ===================================================================
    # AC: POST /api/tasks/repair delegates to CockpitView.repair_storage()
    # ===================================================================

    def test_repair_endpoint_returns_200(self, client: TestClient) -> None:
        """POST /api/tasks/repair must exist and return HTTP 200.

        happy — route does not yet exist.
        FAIL: 404 (route not registered).
        """
        response = client.post("/api/tasks/repair")
        assert response.status_code == 200  # FAIL: 404

    def test_repair_response_is_list(self, client: TestClient) -> None:
        """POST /api/tasks/repair must return a JSON array.

        happy — route does not yet exist.
        FAIL: 404 (route not registered).
        """
        response = client.post("/api/tasks/repair")
        assert response.status_code == 200  # FAIL: 404
        assert isinstance(response.json(), list)

    def test_repair_clean_board_returns_empty_list(self, client: TestClient) -> None:
        """POST /api/tasks/repair on a clean board must return an empty list.

        edge — no corrupt files → scan_and_fix finds nothing → no RepairOutcomes.
        FAIL: 404 (route not registered).
        """
        response = client.post("/api/tasks/repair")
        assert response.status_code == 200  # FAIL: 404
        data = response.json()
        assert isinstance(data, list)
        assert data == []

    def test_repair_delegates_to_cockpit_view_repair_storage(
        self,
        mock_client: TestClient,
        view_mock: mock.MagicMock,
    ) -> None:
        """POST /api/tasks/repair must call CockpitView.repair_storage() exactly once.

        happy — route does not exist; mock is never called.
        FAIL: view_mock.repair_storage.assert_called_once() raises (0 calls).
        """
        view_mock.repair_storage.return_value = []
        response = mock_client.post("/api/tasks/repair")
        assert response.status_code == 200  # FAIL: 404
        view_mock.repair_storage.assert_called_once()  # FAIL: never called

    def test_repair_response_items_have_repair_outcome_fields(
        self,
        mock_client: TestClient,
        view_mock: mock.MagicMock,
    ) -> None:
        """POST /api/tasks/repair items must include RepairOutcome fields.

        happy — verifies contract: task_id, file_path, code, action, detail.
        FAIL: 404 (route not registered); mock side never reached.
        """
        from owlbear_kanban.models import RepairOutcome  # noqa: PLC0415

        outcome = RepairOutcome(
            task_id=1,
            file_path="tasks/001.md",
            code="ERR_CORRUPT_MISSING_ID",
            action="quarantined",
            detail="id field absent",
        )
        view_mock.repair_storage.return_value = [outcome]
        response = mock_client.post("/api/tasks/repair")
        assert response.status_code == 200  # FAIL: 404
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        item = data[0]
        assert "task_id" in item
        assert "file_path" in item
        assert "code" in item
        assert "action" in item

    # ===================================================================
    # AC: POST /api/tasks/compact-activity delegates to CockpitView.compact_activity()
    # ===================================================================

    def test_compact_activity_endpoint_returns_200(self, client: TestClient) -> None:
        """POST /api/tasks/compact-activity must exist and return HTTP 200.

        boundary — engine with activity logging; log may be absent or empty.
        FAIL: 404 (route not registered).
        """
        response = client.post("/api/tasks/compact-activity")
        assert response.status_code == 200  # FAIL: 404

    def test_compact_activity_response_has_required_fields(
        self, client: TestClient
    ) -> None:
        """POST /api/tasks/compact-activity must return ActivityCompactionResult fields.

        happy — before_bytes, after_bytes, records_compacted all present.
        FAIL: 404 (route not registered).
        """
        response = client.post("/api/tasks/compact-activity")
        assert response.status_code == 200  # FAIL: 404
        body = response.json()
        assert "before_bytes" in body
        assert "after_bytes" in body
        assert "records_compacted" in body

    def test_compact_activity_result_fields_are_non_negative_integers(
        self, client: TestClient
    ) -> None:
        """ActivityCompactionResult fields must be non-negative integers.

        boundary — validates the compaction result field types and value constraints.
        FAIL: 404 (route not registered).
        """
        response = client.post("/api/tasks/compact-activity")
        assert response.status_code == 200  # FAIL: 404
        body = response.json()
        assert isinstance(body["before_bytes"], int)
        assert isinstance(body["after_bytes"], int)
        assert isinstance(body["records_compacted"], int)
        assert body["before_bytes"] >= 0
        assert body["after_bytes"] >= 0
        assert body["records_compacted"] >= 0

    def test_compact_activity_delegates_to_cockpit_view_compact_activity(
        self,
        mock_client: TestClient,
        view_mock: mock.MagicMock,
    ) -> None:
        """POST /api/tasks/compact-activity must call CockpitView.compact_activity() once.

        happy — route does not exist; mock is never called.
        FAIL: view_mock.compact_activity.assert_called_once() raises (0 calls).
        """
        view_mock.compact_activity.return_value = ActivityCompactionResult(
            before_bytes=1024,
            after_bytes=512,
            records_compacted=10,
        )
        response = mock_client.post("/api/tasks/compact-activity")
        assert response.status_code == 200  # FAIL: 404
        view_mock.compact_activity.assert_called_once()  # FAIL: never called

    def test_compact_activity_response_values_match_view_result(
        self,
        mock_client: TestClient,
        view_mock: mock.MagicMock,
    ) -> None:
        """POST /api/tasks/compact-activity response values come from CockpitView.compact_activity().

        happy — verifies that route serializes the ActivityCompactionResult correctly.
        FAIL: 404 (route not registered); mock side never reached.
        """
        view_mock.compact_activity.return_value = ActivityCompactionResult(
            before_bytes=2048,
            after_bytes=1024,
            records_compacted=5,
        )
        response = mock_client.post("/api/tasks/compact-activity")
        assert response.status_code == 200  # FAIL: 404
        body = response.json()
        assert body["before_bytes"] == 2048
        assert body["after_bytes"] == 1024
        assert body["records_compacted"] == 5

    # ===================================================================
    # AC: DI pattern maintained — get_engine override reaches admin routes
    # ===================================================================

    def test_di_engine_override_reaches_scan_route(
        self, tmp_path: Path
    ) -> None:
        """Admin route /api/tasks/scan must respect dependency_overrides[get_engine].

        happy — proves admin routes use the DI pattern: overriding get_engine
        in tests determines which engine instance the route operates on.
        FAIL: 404 (route not registered); override has no effect.
        """
        from fastapi.testclient import TestClient  # noqa: PLC0415
        from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415

        alt_dir = _make_board(tmp_path)
        alt_engine = KanbanEngine(alt_dir, agent_name="alt")
        alt_engine.create_task("Isolated task", status="todo", priority="someday")

        app.dependency_overrides[get_engine] = lambda: alt_engine
        try:
            client = TestClient(app)
            response = client.post("/api/tasks/scan")
            assert response.status_code == 200  # FAIL: 404
        finally:
            app.dependency_overrides.clear()

    def test_di_engine_override_reaches_repair_route(
        self, tmp_path: Path
    ) -> None:
        """Admin route /api/tasks/repair must respect dependency_overrides[get_engine].

        happy — proves admin routes use the DI pattern.
        FAIL: 404 (route not registered); override has no effect.
        """
        from fastapi.testclient import TestClient  # noqa: PLC0415
        from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415

        alt_dir = _make_board(tmp_path)
        alt_engine = KanbanEngine(alt_dir, agent_name="alt")
        alt_engine.create_task("Isolated task", status="todo", priority="someday")

        app.dependency_overrides[get_engine] = lambda: alt_engine
        try:
            client = TestClient(app)
            response = client.post("/api/tasks/repair")
            assert response.status_code == 200  # FAIL: 404
        finally:
            app.dependency_overrides.clear()

    def test_di_engine_override_reaches_compact_activity_route(
        self, tmp_path: Path
    ) -> None:
        """Admin route /api/tasks/compact-activity must respect dependency_overrides[get_engine].

        happy — proves admin routes use the DI pattern.
        FAIL: 404 (route not registered); override has no effect.
        """
        from fastapi.testclient import TestClient  # noqa: PLC0415
        from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415

        alt_dir = _make_board(tmp_path)
        alt_engine = KanbanEngine(alt_dir, agent_name="alt", activity_log=True)
        alt_engine.create_task("Isolated task", status="todo", priority="someday")

        app.dependency_overrides[get_engine] = lambda: alt_engine
        try:
            client = TestClient(app)
            response = client.post("/api/tasks/compact-activity")
            assert response.status_code == 200  # FAIL: 404
        finally:
            app.dependency_overrides.clear()
