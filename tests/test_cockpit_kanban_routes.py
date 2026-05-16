"""Cockpit kanban route regression tests.

Promoted from archived tasks #1082 and #1083 during test curation.

AC coverage:
  - cockpit read and mutation routes preserve guidance/missing-sections envelopes
  - edit/move/release route wiring delegates through CockpitView with error mapping
  - activity and sweep routes preserve list-based response contracts
  - admin scan/repair/compact-activity routes delegate through CockpitView and honor DI overrides
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest import mock

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_kanban.errors import (
    ConcurrencyError,
    ConfigError,
    NotFoundError,
    ValidationError,
)
from owlbear_kanban.models import ActivityCompactionResult

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

# Provenance: promoted from archived task-scoped suites for #1082 and #1083.


# ---------------------------------------------------------------------------
# Board fixture helpers
# ---------------------------------------------------------------------------

_CONFIG_YAML = """\
next_id: 1
"""


def _make_board(base_dir: Path) -> Path:
    """Create a minimal kanban board directory."""
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


def _inject_corrupt_task_file(kanban_dir: Path) -> Path:
    """Write a corrupt task file into tasks/."""
    corrupt_path = kanban_dir / "tasks" / "9999-corrupt-sentinel.md"
    corrupt_path.write_text(
        "no frontmatter delimiters here\njust plain text\n",
        encoding="utf-8",
    )
    return corrupt_path


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def board_dir(tmp_path: Path) -> Path:
    """Board with 2 tasks; task 2 is pre-claimed for release-route tests."""
    kanban_dir = _make_board(tmp_path)
    seed = KanbanEngine(kanban_dir)
    seed.create_task("Alpha task", status="todo", priority="important")
    seed.create_task("Beta task", status="in-progress", priority="needed")
    seed.list_tasks()
    seed.claim_task("2")
    return kanban_dir


@pytest.fixture
def engine(board_dir: Path) -> KanbanEngine:
    """Cockpit engine with activity logging enabled."""
    eng = KanbanEngine(board_dir, activity_log=True)
    eng.list_tasks()
    return eng


@pytest.fixture
def client(engine: KanbanEngine):
    """FastAPI TestClient with the cockpit engine injected."""
    from fastapi.testclient import TestClient  # noqa: PLC0415
    from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415

    app.dependency_overrides[get_engine] = lambda: engine
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def view_mock() -> mock.MagicMock:
    """Isolated CockpitView double for delegation tests."""
    return mock.MagicMock()


@pytest.fixture
def mock_client(engine: KanbanEngine, view_mock: mock.MagicMock):
    """TestClient with a real engine and mocked CockpitView dependency."""
    from fastapi.testclient import TestClient  # noqa: PLC0415
    from owlbear_cockpit.deps import get_view  # noqa: PLC0415
    from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415

    app.dependency_overrides[get_engine] = lambda: engine
    app.dependency_overrides[get_view] = lambda: view_mock
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def _single_task_response(engine: KanbanEngine, task_id: str):
    """Build a SingleTaskResponse from an existing task for mock return values."""
    from owlbear_kanban.models import SingleTaskResponse  # noqa: PLC0415

    task = engine.show_task(task_id)
    payload = task.model_dump()
    payload["guidance"] = []
    if isinstance(payload.get("body"), list):
        payload["body"] = None
    return SingleTaskResponse.model_validate(payload)


# ---------------------------------------------------------------------------
# Envelope contracts
# ---------------------------------------------------------------------------


class TestFromAC_CockpitRouteEnvelopes:
    """Route envelope contracts preserved from archived cockpit route tasks."""

    def test_list_tasks_response_has_guidance_field(self, client: TestClient) -> None:
        """GET /api/tasks includes cockpit guidance in the response envelope."""
        response = client.get("/api/tasks")
        assert response.status_code == 200
        body = response.json()
        assert "guidance" in body

    def test_show_task_response_has_guidance_field(self, client: TestClient) -> None:
        """GET /api/tasks/{id} includes cockpit guidance in the response body."""
        response = client.get("/api/tasks/1")
        assert response.status_code == 200
        body = response.json()
        assert "guidance" in body

    def test_show_task_response_has_missing_sections_field(self, client: TestClient) -> None:
        """GET /api/tasks/{id} exposes missing_sections from ShowTaskResponse."""
        response = client.get("/api/tasks/1")
        assert response.status_code == 200
        body = response.json()
        assert "missing_sections" in body

    def test_move_response_has_guidance_field(self, client: TestClient, engine: KanbanEngine) -> None:
        """POST /api/tasks/{id}/move preserves SingleTaskResponse.guidance."""
        task = engine.show_task("1")
        response = client.post(
            "/api/tasks/1/move",
            json={"status": "in-progress", "updated": task.updated},
        )
        assert response.status_code == 200
        body = response.json()
        assert "guidance" in body

    def test_release_response_has_guidance_field(self, client: TestClient, engine: KanbanEngine) -> None:
        """POST /api/tasks/{id}/release preserves SingleTaskResponse.guidance."""
        task = engine.show_task("2")
        response = client.post(
            "/api/tasks/2/release",
            json={"updated": task.updated},
        )
        assert response.status_code == 200
        body = response.json()
        assert "guidance" in body


# ---------------------------------------------------------------------------
# CockpitView edit delegation
# ---------------------------------------------------------------------------


class TestFromAC_CockpitEditDelegation:
    """Edit-route CockpitView delegation and error mapping contracts."""

    def test_edit_delegates_to_cockpit_view_not_engine(
        self,
        mock_client: TestClient,
        engine: KanbanEngine,
        view_mock: mock.MagicMock,
    ) -> None:
        """POST /api/tasks/{id}/edit calls CockpitView.edit_task exactly once."""
        view_mock.edit_task.return_value = _single_task_response(engine, "1")
        task = engine.show_task("1")
        response = mock_client.post(
            "/api/tasks/1/edit",
            json={"updated": task.updated, "title": "New title"},
        )
        assert response.status_code == 200
        view_mock.edit_task.assert_called_once()

    def test_edit_status_field_rejected_before_cockpit_view(
        self,
        mock_client: TestClient,
        engine: KanbanEngine,
        view_mock: mock.MagicMock,
    ) -> None:
        """Pydantic rejects status edits before the CockpitView dependency is used."""
        task = engine.show_task("1")
        response = mock_client.post(
            "/api/tasks/1/edit",
            json={"updated": task.updated, "status": "done"},
        )
        assert response.status_code == 422
        body = response.json()
        assert isinstance(body.get("detail"), list)
        view_mock.edit_task.assert_not_called()

    def test_edit_passes_exact_expected_updated_to_cockpit_view(
        self,
        mock_client: TestClient,
        engine: KanbanEngine,
        view_mock: mock.MagicMock,
    ) -> None:
        """The edit route forwards the exact OCC token to CockpitView.edit_task."""
        task = engine.show_task("1")
        expected_updated = task.updated
        view_mock.edit_task.return_value = _single_task_response(engine, "1")

        response = mock_client.post(
            "/api/tasks/1/edit",
            json={"updated": expected_updated, "title": "Proof title"},
        )

        assert response.status_code == 200
        call_kwargs = view_mock.edit_task.call_args.kwargs
        assert "expected_updated" in call_kwargs, "expected_updated not forwarded to CockpitView.edit_task"
        assert call_kwargs["expected_updated"] == expected_updated

    def test_edit_stale_token_from_cockpit_view_returns_409(
        self,
        mock_client: TestClient,
        engine: KanbanEngine,
        view_mock: mock.MagicMock,
    ) -> None:
        """ConcurrencyError from CockpitView.edit_task maps to HTTP 409."""
        view_mock.edit_task.side_effect = ConcurrencyError(
            code="ERR_STALE",
            user_message="Stale snapshot",
        )
        task = engine.show_task("1")
        response = mock_client.post(
            "/api/tasks/1/edit",
            json={"updated": task.updated, "title": "New title"},
        )
        assert response.status_code == 409

    def test_edit_not_found_from_cockpit_view_returns_404(
        self,
        mock_client: TestClient,
        engine: KanbanEngine,
        view_mock: mock.MagicMock,
    ) -> None:
        """NotFoundError from CockpitView.edit_task maps to HTTP 404."""
        view_mock.edit_task.side_effect = NotFoundError(
            code="ERR_NOT_FOUND",
            user_message="Task '1' not found",
        )
        task = engine.show_task("1")
        response = mock_client.post(
            "/api/tasks/1/edit",
            json={"updated": task.updated, "title": "New title"},
        )
        assert response.status_code == 404

    def test_edit_validation_error_from_cockpit_view_returns_422(
        self,
        mock_client: TestClient,
        engine: KanbanEngine,
        view_mock: mock.MagicMock,
    ) -> None:
        """ValidationError from CockpitView.edit_task maps to HTTP 422."""
        view_mock.edit_task.side_effect = ValidationError(
            code="ERR_INVALID_STATUS",
            user_message="invalid priority value",
        )
        task = engine.show_task("1")
        response = mock_client.post(
            "/api/tasks/1/edit",
            json={"updated": task.updated, "title": "New title"},
        )
        assert response.status_code == 422

    def test_edit_config_error_from_cockpit_view_returns_500(
        self,
        mock_client: TestClient,
        engine: KanbanEngine,
        view_mock: mock.MagicMock,
    ) -> None:
        """ConfigError from CockpitView.edit_task maps to HTTP 500."""
        view_mock.edit_task.side_effect = ConfigError(
            code="ERR_INVALID_CLAIM_TIMEOUT",
            user_message="bad config",
        )
        task = engine.show_task("1")
        response = mock_client.post(
            "/api/tasks/1/edit",
            json={"updated": task.updated, "title": "New title"},
        )
        assert response.status_code == 500


# ---------------------------------------------------------------------------
# CockpitView move/release routing
# ---------------------------------------------------------------------------


class TestFromAC_CockpitMutationViewRouting:
    """Move/release route wiring through CockpitView."""

    def test_move_passes_exact_expected_updated_to_cockpit_view(
        self,
        mock_client: TestClient,
        engine: KanbanEngine,
        view_mock: mock.MagicMock,
    ) -> None:
        """The move route forwards the exact OCC token to CockpitView.move_task."""
        view_mock.engine = engine
        task = engine.show_task("1")
        expected_updated = task.updated
        view_mock.move_task.return_value = _single_task_response(engine, "1")

        response = mock_client.post(
            "/api/tasks/1/move",
            json={"status": "in-progress", "updated": expected_updated},
        )

        assert response.status_code == 200
        call_kwargs = view_mock.move_task.call_args.kwargs
        assert "expected_updated" in call_kwargs, "expected_updated not forwarded to CockpitView.move_task"
        assert call_kwargs["expected_updated"] == expected_updated

    def test_release_passes_exact_expected_updated_to_cockpit_view(
        self,
        mock_client: TestClient,
        engine: KanbanEngine,
        view_mock: mock.MagicMock,
    ) -> None:
        """The release route forwards the exact OCC token to CockpitView.release_task."""
        view_mock.show_task.return_value.claimed = True
        task = engine.show_task("2")
        expected_updated = task.updated
        view_mock.release_task.return_value = _single_task_response(engine, "2")

        response = mock_client.post(
            "/api/tasks/2/release",
            json={"updated": expected_updated},
        )

        assert response.status_code == 200
        call_kwargs = view_mock.release_task.call_args.kwargs
        assert "expected_updated" in call_kwargs, "expected_updated not forwarded to CockpitView.release_task"
        assert call_kwargs["expected_updated"] == expected_updated

    def test_move_stale_token_from_cockpit_view_returns_409(
        self,
        mock_client: TestClient,
        engine: KanbanEngine,
        view_mock: mock.MagicMock,
    ) -> None:
        """ConcurrencyError from CockpitView.move_task maps to HTTP 409."""
        view_mock.engine = engine
        task = engine.show_task("1")
        view_mock.move_task.side_effect = ConcurrencyError(
            code="ERR_STALE",
            user_message="Stale snapshot",
        )

        response = mock_client.post(
            "/api/tasks/1/move",
            json={"status": "in-progress", "updated": task.updated},
        )

        assert response.status_code == 409

    def test_release_stale_token_from_cockpit_view_returns_409(
        self,
        mock_client: TestClient,
        engine: KanbanEngine,
        view_mock: mock.MagicMock,
    ) -> None:
        """ConcurrencyError from CockpitView.release_task maps to HTTP 409."""
        view_mock.show_task.return_value.claimed = True
        view_mock.release_task.side_effect = ConcurrencyError(
            code="ERR_STALE",
            user_message="Stale snapshot",
        )
        task = engine.show_task("2")

        response = mock_client.post(
            "/api/tasks/2/release",
            json={"updated": task.updated},
        )

        assert response.status_code == 409

    def test_move_not_found_from_cockpit_view_returns_404(
        self,
        mock_client: TestClient,
        engine: KanbanEngine,
        view_mock: mock.MagicMock,
    ) -> None:
        """NotFoundError from CockpitView.move_task maps to HTTP 404."""
        view_mock.engine = engine
        task = engine.show_task("1")
        view_mock.move_task.side_effect = NotFoundError(
            code="ERR_NOT_FOUND",
            user_message="Task '1' not found",
        )

        response = mock_client.post(
            "/api/tasks/1/move",
            json={"status": "in-progress", "updated": task.updated},
        )

        assert response.status_code == 404

    def test_release_not_found_from_cockpit_view_returns_404(
        self,
        mock_client: TestClient,
        engine: KanbanEngine,
        view_mock: mock.MagicMock,
    ) -> None:
        """NotFoundError from CockpitView.release_task maps to HTTP 404."""
        view_mock.show_task.return_value.claimed = True
        view_mock.release_task.side_effect = NotFoundError(
            code="ERR_NOT_FOUND",
            user_message="Task '2' not found",
        )
        task = engine.show_task("2")

        response = mock_client.post(
            "/api/tasks/2/release",
            json={"updated": task.updated},
        )

        assert response.status_code == 404

    def test_move_validation_error_from_cockpit_view_returns_422(
        self,
        mock_client: TestClient,
        engine: KanbanEngine,
        view_mock: mock.MagicMock,
    ) -> None:
        """ValidationError from CockpitView.move_task maps to HTTP 422."""
        view_mock.engine = engine
        task = engine.show_task("1")
        view_mock.move_task.side_effect = ValidationError(
            code="ERR_INVALID_STATUS",
            user_message="invalid transition",
        )

        response = mock_client.post(
            "/api/tasks/1/move",
            json={"status": "in-progress", "updated": task.updated},
        )

        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Activity and sweep routes
# ---------------------------------------------------------------------------


class TestFromAC_CockpitActivityAndSweepRoutes:
    """List-based route contracts for activity and sweep endpoints."""

    def test_get_activity_returns_list_of_event_objects(self, client: TestClient) -> None:
        """GET /api/activity returns a JSON list of activity records."""
        response = client.get("/api/activity")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_activity_filter_by_task_id_scopes_results(self, client: TestClient, engine: KanbanEngine) -> None:
        """GET /api/activity?task_id=1 returns only task-1 events."""
        engine.claim_task("1")
        response = client.get("/api/activity?task_id=1")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert all(event.get("task_id") == 1 for event in data)

    def test_list_activity_with_limit_filter(self, client: TestClient, engine: KanbanEngine) -> None:
        """GET /api/activity?limit=1 returns at most one event."""
        engine.claim_task("1")
        response = client.get("/api/activity?limit=1")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 1

    def test_sweep_returns_list_of_integer_task_ids(self, client: TestClient) -> None:
        """POST /api/tasks/sweep returns a JSON array of integer task IDs."""
        response = client.post("/api/tasks/sweep")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert all(isinstance(item, int) for item in data)


# ---------------------------------------------------------------------------
# Admin routes
# ---------------------------------------------------------------------------


class TestFromAC_CockpitAdminRoutes:
    """Admin route delegation, shape, and DI contracts."""

    def test_scan_clean_board_returns_empty_list(self, client: TestClient) -> None:
        """POST /api/tasks/scan on a clean board returns an empty list."""
        response = client.post("/api/tasks/scan")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert data == []

    def test_scan_delegates_to_cockpit_view_scan_corruption(
        self,
        mock_client: TestClient,
        view_mock: mock.MagicMock,
    ) -> None:
        """POST /api/tasks/scan delegates to CockpitView.scan_corruption."""
        view_mock.scan_corruption.return_value = []
        response = mock_client.post("/api/tasks/scan")
        assert response.status_code == 200
        view_mock.scan_corruption.assert_called_once()

    def test_scan_mock_item_includes_all_required_fields(
        self,
        mock_client: TestClient,
        view_mock: mock.MagicMock,
    ) -> None:
        """Scan responses preserve code/detail/file_path for corruption items."""
        view_mock.scan_corruption.return_value = [
            {
                "code": "ERR_CORRUPT_DELIMITERS",
                "detail": "file does not start with ---",
                "file_path": "tasks/9999-corrupt-sentinel.md",
            }
        ]

        response = mock_client.post("/api/tasks/scan")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        item = data[0]
        assert item["code"] == "ERR_CORRUPT_DELIMITERS"
        assert item["detail"] == "file does not start with ---"
        assert item["file_path"] == "tasks/9999-corrupt-sentinel.md"

    def test_di_scan_observes_overridden_board_not_default(self, tmp_path: Path) -> None:
        """Overriding get_engine routes scan to the overridden board."""
        from fastapi.testclient import TestClient  # noqa: PLC0415
        from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415

        alt_dir = _make_board(tmp_path / "alt")
        _inject_corrupt_task_file(alt_dir)
        alt_engine = KanbanEngine(alt_dir)

        app.dependency_overrides[get_engine] = lambda: alt_engine
        try:
            test_client = TestClient(app)
            response = test_client.post("/api/tasks/scan")
            assert response.status_code == 200
            data = response.json()
            assert len(data) >= 1
        finally:
            app.dependency_overrides.clear()

    def test_repair_clean_board_returns_empty_list(self, client: TestClient) -> None:
        """POST /api/tasks/repair on a clean board returns an empty list."""
        response = client.post("/api/tasks/repair")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert data == []

    def test_repair_delegates_to_cockpit_view_repair_storage(
        self,
        mock_client: TestClient,
        view_mock: mock.MagicMock,
    ) -> None:
        """POST /api/tasks/repair delegates to CockpitView.repair_storage."""
        view_mock.repair_storage.return_value = []
        response = mock_client.post("/api/tasks/repair")
        assert response.status_code == 200
        view_mock.repair_storage.assert_called_once()

    def test_repair_response_item_includes_detail_field(
        self,
        mock_client: TestClient,
        view_mock: mock.MagicMock,
    ) -> None:
        """Repair responses preserve the detail field from RepairOutcome."""
        from owlbear_kanban.models import RepairOutcome as _RepairOutcome  # noqa: PLC0415

        view_mock.repair_storage.return_value = [
            _RepairOutcome(
                task_id=1,
                file_path="tasks/001.md",
                code="ERR_CORRUPT_MISSING_FIELD",
                action="quarantined",
                detail="required field 'id' absent",
            )
        ]

        response = mock_client.post("/api/tasks/repair")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        item = data[0]
        assert item["detail"] == "required field 'id' absent"

    def test_di_repair_observes_overridden_board_not_default(self, tmp_path: Path) -> None:
        """Overriding get_engine routes repair to the overridden board."""
        from fastapi.testclient import TestClient  # noqa: PLC0415
        from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415

        alt_dir = _make_board(tmp_path / "alt")
        _inject_corrupt_task_file(alt_dir)
        alt_engine = KanbanEngine(alt_dir)

        app.dependency_overrides[get_engine] = lambda: alt_engine
        try:
            test_client = TestClient(app)
            response = test_client.post("/api/tasks/repair")
            assert response.status_code == 200
            data = response.json()
            assert len(data) >= 1
        finally:
            app.dependency_overrides.clear()

    def test_compact_activity_response_has_required_fields(self, client: TestClient) -> None:
        """POST /api/tasks/compact-activity returns compaction result fields."""
        response = client.post("/api/tasks/compact-activity")
        assert response.status_code == 200
        body = response.json()
        assert "before_bytes" in body
        assert "after_bytes" in body
        assert "records_compacted" in body

    def test_compact_activity_delegates_to_cockpit_view_compact_activity(
        self,
        mock_client: TestClient,
        view_mock: mock.MagicMock,
    ) -> None:
        """POST /api/tasks/compact-activity delegates to CockpitView.compact_activity."""
        view_mock.compact_activity.return_value = ActivityCompactionResult(
            before_bytes=1024,
            after_bytes=512,
            records_compacted=10,
        )

        response = mock_client.post("/api/tasks/compact-activity")

        assert response.status_code == 200
        view_mock.compact_activity.assert_called_once()

    def test_compact_activity_response_values_match_view_result(
        self,
        mock_client: TestClient,
        view_mock: mock.MagicMock,
    ) -> None:
        """Compaction responses serialize CockpitView.compact_activity values."""
        view_mock.compact_activity.return_value = ActivityCompactionResult(
            before_bytes=2048,
            after_bytes=1024,
            records_compacted=5,
        )

        response = mock_client.post("/api/tasks/compact-activity")

        assert response.status_code == 200
        body = response.json()
        assert body["before_bytes"] == 2048
        assert body["after_bytes"] == 1024
        assert body["records_compacted"] == 5

    def test_di_compact_observes_overridden_board_not_default(self, tmp_path: Path) -> None:
        """Overriding get_engine routes compact-activity through the injected engine."""
        from owlbear_cockpit.view import CockpitView as _RealCockpitView  # noqa: PLC0415
        from fastapi.testclient import TestClient  # noqa: PLC0415
        from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415

        alt_dir = _make_board(tmp_path / "alt")
        alt_engine = KanbanEngine(
            alt_dir,
            activity_log=True,
        )

        captured_engines: list[KanbanEngine] = []

        def _spy_view(engine_arg: KanbanEngine):
            captured_engines.append(engine_arg)
            return _RealCockpitView(engine_arg)

        app.dependency_overrides[get_engine] = lambda: alt_engine
        try:
            with mock.patch("owlbear_cockpit.deps.CockpitView", side_effect=_spy_view):
                test_client = TestClient(app)
                response = test_client.post("/api/tasks/compact-activity")
            assert response.status_code == 200
            assert len(captured_engines) >= 1, "CockpitView was never constructed through the dependency chain"
            assert captured_engines[-1] is alt_engine
        finally:
            app.dependency_overrides.clear()
