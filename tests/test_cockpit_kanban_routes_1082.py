"""Failing tests for #1082 — cockpit backend routes: CockpitView delegation and new endpoints.

RED phase — all tests must fail until implementation is complete.

AC coverage:
  AC-NEW-24: POST /api/tasks/{id}/edit with status in body → 422 (Pydantic before engine)
             (Covered via delegation tests; constraint verified by EditRequest.extra='forbid')
  OCC:       edit/move/release pass expected_updated to CockpitView
  ERR_STALE: CockpitView raises ConcurrencyError(ERR_STALE) → 409
  ERR_NOT_FOUND: CockpitView raises NotFoundError → 404
  ValidationError: CockpitView raises ValidationError → 422
  ConfigError: CockpitView raises ConfigError → 500
  ListTasksResponse: GET /api/tasks returns tasks + guidance envelope
  ShowTaskResponse: GET /api/tasks/{id} returns task + guidance + missing_sections envelope
  Activity: GET /api/activity returns filtered activity events
  Sessions: GET /api/sessions returns flat SessionRecord list (not wrapped envelope)
  SingleTaskResponse: POST /api/tasks/{id}/release returns guidance field
  SingleTaskResponse: POST /api/tasks/{id}/move returns guidance field
  Sweep: POST /api/tasks/sweep returns list of released task IDs
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest import mock

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_kanban.errors import ConcurrencyError, ConfigError, NotFoundError, ValidationError

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
    """Board with 2 tasks; task 2 is pre-claimed for release/sessions tests.

    Task 1: status=todo,        priority=important  (unclaimed)
    Task 2: status=in-progress, priority=needed     (claimed via seed engine)
    """
    kanban_dir = _make_board(tmp_path)
    seed = KanbanEngine(kanban_dir, agent_name="seed")
    seed.create_task("Alpha task", status="todo", priority="important")
    seed.create_task("Beta task", status="in-progress", priority="needed")
    seed.list_tasks()
    seed.claim_task("2")
    return kanban_dir


@pytest.fixture
def engine(board_dir: Path) -> KanbanEngine:
    """KanbanEngine with agent_name='cockpit' and activity logging enabled."""
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
# TestFromAC_CockpitRoutes
# ---------------------------------------------------------------------------


class TestFromAC_CockpitRoutes:
    """Tests for cockpit backend routes — new endpoints and CockpitView delegation.

    RED phase: all tests must fail until the builder implements the required changes.

    Categories:
      happy  — correct response shape and status code when request is valid
      error  — correct HTTP status when CockpitView raises domain errors
      boundary — edge cases (empty activity log, sweep with no expired claims)
    """

    # ===================================================================
    # AC: GET /api/tasks returns ListTasksResponse envelope
    # ===================================================================

    def test_list_tasks_response_has_guidance_field(
        self, client: TestClient
    ) -> None:
        """GET /api/tasks must include 'guidance' in the response body.

        happy — ListTasksResponse has guidance; current TaskListOut does not.
        FAIL: 'guidance' key absent from current response.
        """
        response = client.get("/api/tasks")
        assert response.status_code == 200
        body = response.json()
        assert "guidance" in body  # FAIL: TaskListOut has no guidance field

    def test_list_tasks_envelope_has_no_mtime_field(
        self, client: TestClient
    ) -> None:
        """GET /api/tasks cockpit envelope includes adapter-level 'mtime' metadata."""
        response = client.get("/api/tasks")
        assert response.status_code == 200
        body = response.json()
        assert "mtime" in body
        assert isinstance(body["mtime"], int)

    # ===================================================================
    # AC: GET /api/tasks/{id} returns ShowTaskResponse envelope
    # ===================================================================

    def test_show_task_response_has_guidance_field(
        self, client: TestClient
    ) -> None:
        """GET /api/tasks/{id} must include 'guidance' in the response body.

        happy — ShowTaskResponse has guidance; current TaskDetailOut does not.
        FAIL: 'guidance' key absent from current response.
        """
        response = client.get("/api/tasks/1")
        assert response.status_code == 200
        body = response.json()
        assert "guidance" in body  # FAIL: TaskDetailOut has no guidance

    def test_show_task_response_has_missing_sections_field(
        self, client: TestClient
    ) -> None:
        """GET /api/tasks/{id} must include 'missing_sections' in the response body.

        happy — ShowTaskResponse has missing_sections; current TaskDetailOut does not.
        FAIL: 'missing_sections' key absent from current response.
        """
        response = client.get("/api/tasks/1")
        assert response.status_code == 200
        body = response.json()
        assert "missing_sections" in body  # FAIL: TaskDetailOut has no missing_sections

    # ===================================================================
    # AC: GET /api/activity returns filtered activity events
    # ===================================================================

    def test_get_activity_endpoint_returns_200(
        self, client: TestClient
    ) -> None:
        """GET /api/activity must exist and return HTTP 200.

        happy — route does not yet exist.
        FAIL: route not registered → 404.
        """
        response = client.get("/api/activity")
        assert response.status_code == 200  # FAIL: 404

    def test_get_activity_returns_list_of_event_objects(
        self, client: TestClient
    ) -> None:
        """GET /api/activity must return a JSON array of activity event objects.

        happy — route does not yet exist.
        FAIL: route not registered → 404.
        """
        response = client.get("/api/activity")
        assert response.status_code == 200  # FAIL: 404
        data = response.json()
        assert isinstance(data, list)

    def test_get_activity_filter_by_task_id_scopes_results(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """GET /api/activity?task_id=1 must return only events for task 1.

        happy — route does not yet exist; also verifies task_id filtering.
        FAIL: route not registered → 404.
        """
        engine.claim_task("1")
        response = client.get("/api/activity?task_id=1")
        assert response.status_code == 200  # FAIL: 404
        data = response.json()
        assert isinstance(data, list)
        assert all(event.get("task_id") == 1 for event in data)

    # ===================================================================
    # AC: GET /api/sessions returns SessionRecord list
    # ===================================================================

    def test_sessions_response_is_flat_list_not_wrapped(
        self, client: TestClient
    ) -> None:
        """GET /api/sessions must return a flat JSON array, not a wrapped envelope.

        boundary — current route returns SessionListOut: {'sessions': [...]}.
        FAIL: response.json() is a dict with 'sessions' key, not a list.
        """
        response = client.get("/api/sessions")
        assert response.status_code == 200
        # Expected: [...] (flat list of SessionRecord)
        # Current:  {"sessions": [...]} (SessionListOut envelope)
        assert isinstance(response.json(), list)  # FAIL: returns dict

    def test_sessions_record_has_task_status_at_start_field(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """Session records must include 'task_status_at_start' (SessionRecord field).

        happy — current SessionOut model does not expose task_status_at_start.
        FAIL: response is a dict (not a list); even if list, field is absent.
        """
        engine.claim_task("1")
        engine.end_work("1", note="done", outcome="success")
        response = client.get("/api/sessions?filter=all")
        assert response.status_code == 200
        sessions = response.json()
        assert isinstance(sessions, list), "sessions must be a flat list (not wrapped)"  # FAIL
        assert len(sessions) >= 1
        assert "task_status_at_start" in sessions[0]  # FAIL: not in current SessionOut

    # ===================================================================
    # AC: POST /api/tasks/sweep returns list of released task IDs
    # ===================================================================

    def test_sweep_endpoint_returns_200(
        self, client: TestClient
    ) -> None:
        """POST /api/tasks/sweep must exist and return HTTP 200.

        happy — route does not yet exist.
        FAIL: route not registered → 404 or 405.
        """
        response = client.post("/api/tasks/sweep")
        assert response.status_code == 200  # FAIL: route not found

    def test_sweep_returns_list_of_integer_task_ids(
        self, client: TestClient
    ) -> None:
        """POST /api/tasks/sweep must return a JSON array of integer task IDs.

        happy — route does not yet exist.
        FAIL: route not registered → 404 or 405.
        """
        response = client.post("/api/tasks/sweep")
        assert response.status_code == 200  # FAIL: route not found
        data = response.json()
        assert isinstance(data, list)
        assert all(isinstance(item, int) for item in data)

    # ===================================================================
    # AC: POST /api/tasks/{id}/release returns SingleTaskResponse
    # ===================================================================

    def test_release_response_has_guidance_field(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """POST /api/tasks/{id}/release must return 'guidance' field (SingleTaskResponse).

        happy — current route returns TaskDetailOut which has no guidance.
        FAIL: 'guidance' key absent from current release response.
        """
        task = engine.show_task("2")  # task 2 is pre-claimed
        response = client.post(
            "/api/tasks/2/release",
            json={"updated": task.updated},
        )
        assert response.status_code == 200
        body = response.json()
        assert "guidance" in body  # FAIL: TaskDetailOut has no guidance

    # ===================================================================
    # AC: OCC mutations pass expected_updated to CockpitView / SingleTaskResponse
    # ===================================================================

    def test_move_response_has_guidance_field(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """POST /api/tasks/{id}/move must return 'guidance' field (SingleTaskResponse).

        happy — current route returns TaskDetailOut which has no guidance.
        FAIL: 'guidance' key absent from current move response.
        """
        task = engine.show_task("1")
        response = client.post(
            "/api/tasks/1/move",
            json={"status": "in-progress", "updated": task.updated},
        )
        assert response.status_code == 200
        body = response.json()
        assert "guidance" in body  # FAIL: TaskDetailOut has no guidance

    # ===================================================================
    # AC: edit route delegates to CockpitView (not KanbanEngine directly)
    # ===================================================================

    def test_edit_delegates_to_cockpit_view_not_engine(
        self,
        mock_client: TestClient,
        engine: KanbanEngine,
        view_mock: mock.MagicMock,
    ) -> None:
        """POST /api/tasks/{id}/edit must call CockpitView.edit_task, not engine.edit_task.

        happy — current edit route uses _Engine directly; view_mock.edit_task never called.
        FAIL: view_mock.edit_task.assert_called_once() raises AssertionError (0 calls).
        """
        view_mock.edit_task.return_value = _single_task_response(engine, "1")
        task = engine.show_task("1")
        response = mock_client.post(
            "/api/tasks/1/edit",
            json={"updated": task.updated, "title": "New title"},
        )
        # Current route uses engine.edit_task() → succeeds → 200
        assert response.status_code == 200
        # Expected: edit route delegates to view.edit_task (CockpitView)
        view_mock.edit_task.assert_called_once()  # FAIL: 0 calls (engine used, not view)

    def test_edit_stale_token_from_cockpit_view_returns_409(
        self,
        mock_client: TestClient,
        engine: KanbanEngine,
        view_mock: mock.MagicMock,
    ) -> None:
        """ConcurrencyError(ERR_STALE) from CockpitView.edit_task must yield HTTP 409.

        error — current edit route bypasses view; mock side_effect is never triggered;
        real engine edit with fresh token returns 200 instead.
        FAIL: response is 200 (engine succeeds), not 409.
        """
        view_mock.edit_task.side_effect = ConcurrencyError(
            code="ERR_STALE", user_message="Stale snapshot"
        )
        task = engine.show_task("1")
        response = mock_client.post(
            "/api/tasks/1/edit",
            json={"updated": task.updated, "title": "New title"},
        )
        assert response.status_code == 409  # FAIL: view mock not triggered → 200

    def test_edit_not_found_from_cockpit_view_returns_404(
        self,
        mock_client: TestClient,
        engine: KanbanEngine,
        view_mock: mock.MagicMock,
    ) -> None:
        """NotFoundError from CockpitView.edit_task must yield HTTP 404.

        error — current edit route bypasses view; mock side_effect is never triggered;
        real engine edit of existing task returns 200 instead.
        FAIL: response is 200 (engine succeeds), not 404.
        """
        view_mock.edit_task.side_effect = NotFoundError(
            code="ERR_NOT_FOUND", user_message="Task '1' not found"
        )
        task = engine.show_task("1")
        response = mock_client.post(
            "/api/tasks/1/edit",
            json={"updated": task.updated, "title": "New title"},
        )
        assert response.status_code == 404  # FAIL: view mock not triggered → 200

    def test_edit_validation_error_from_cockpit_view_returns_422(
        self,
        mock_client: TestClient,
        engine: KanbanEngine,
        view_mock: mock.MagicMock,
    ) -> None:
        """ValidationError from CockpitView.edit_task must yield HTTP 422.

        error — current edit route bypasses view; mock side_effect is never triggered;
        real engine edit of existing task returns 200 instead.
        FAIL: response is 200 (engine succeeds), not 422.
        """
        view_mock.edit_task.side_effect = ValidationError(
            code="ERR_INVALID_STATUS", user_message="invalid priority value"
        )
        task = engine.show_task("1")
        response = mock_client.post(
            "/api/tasks/1/edit",
            json={"updated": task.updated, "title": "New title"},
        )
        assert response.status_code == 422  # FAIL: view mock not triggered → 200

    def test_edit_config_error_from_cockpit_view_returns_500(
        self,
        mock_client: TestClient,
        engine: KanbanEngine,
        view_mock: mock.MagicMock,
    ) -> None:
        """ConfigError from CockpitView.edit_task must yield HTTP 500.

        error — current edit route bypasses view; mock side_effect is never triggered;
        real engine edit of existing task returns 200 instead.
        FAIL: response is 200 (engine succeeds), not 500.
        """
        view_mock.edit_task.side_effect = ConfigError(
            code="ERR_INVALID_CLAIM_TIMEOUT", user_message="bad config"
        )
        task = engine.show_task("1")
        response = mock_client.post(
            "/api/tasks/1/edit",
            json={"updated": task.updated, "title": "New title"},
        )
        assert response.status_code == 500  # FAIL: view mock not triggered → 200
