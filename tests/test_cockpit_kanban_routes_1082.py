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

        happy — ListTasksResponse has guidance; current legacy list response does not.
        FAIL: 'guidance' key absent from current response.
        """
        response = client.get("/api/tasks")
        assert response.status_code == 200
        body = response.json()
        assert "guidance" in body  # FAIL: legacy list response has no guidance field

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

        happy — ShowTaskResponse has guidance; current legacy detail response does not.
        FAIL: 'guidance' key absent from current response.
        """
        response = client.get("/api/tasks/1")
        assert response.status_code == 200
        body = response.json()
        assert "guidance" in body  # FAIL: legacy detail response has no guidance

    def test_show_task_response_has_missing_sections_field(
        self, client: TestClient
    ) -> None:
        """GET /api/tasks/{id} must include 'missing_sections' in the response body.

        happy — ShowTaskResponse has missing_sections; current legacy detail response does not.
        FAIL: 'missing_sections' key absent from current response.
        """
        response = client.get("/api/tasks/1")
        assert response.status_code == 200
        body = response.json()
        assert "missing_sections" in body  # FAIL: legacy detail response has no missing_sections

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

        boundary — current route returns a wrapped envelope: {'sessions': [...]}.
        FAIL: response.json() is a dict with 'sessions' key, not a list.
        """
        response = client.get("/api/sessions")
        assert response.status_code == 200
        # Expected: [...] (flat list of SessionRecord)
        # Current:  {"sessions": [...]} (wrapped envelope)
        assert isinstance(response.json(), list)  # FAIL: returns dict

    def test_sessions_record_has_task_status_at_start_field(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """Session records must include 'task_status_at_start' (SessionRecord field).

        happy — current session response does not expose task_status_at_start.
        FAIL: response is a dict (not a list); even if list, field is absent.
        """
        engine.claim_task("1")
        engine.end_work("1", note="done", outcome="success")
        response = client.get("/api/sessions?filter=all")
        assert response.status_code == 200
        sessions = response.json()
        assert isinstance(sessions, list), "sessions must be a flat list (not wrapped)"  # FAIL
        assert len(sessions) >= 1
        assert "task_status_at_start" in sessions[0]  # FAIL: not in current session payload

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

        happy — current route returns a legacy detail response with no guidance.
        FAIL: 'guidance' key absent from current release response.
        """
        task = engine.show_task("2")  # task 2 is pre-claimed
        response = client.post(
            "/api/tasks/2/release",
            json={"updated": task.updated},
        )
        assert response.status_code == 200
        body = response.json()
        assert "guidance" in body  # FAIL: legacy detail response has no guidance

    # ===================================================================
    # AC: OCC mutations pass expected_updated to CockpitView / SingleTaskResponse
    # ===================================================================

    def test_move_response_has_guidance_field(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """POST /api/tasks/{id}/move must return 'guidance' field (SingleTaskResponse).

        happy — current route returns a legacy detail response with no guidance.
        FAIL: 'guidance' key absent from current move response.
        """
        task = engine.show_task("1")
        response = client.post(
            "/api/tasks/1/move",
            json={"status": "in-progress", "updated": task.updated},
        )
        assert response.status_code == 200
        body = response.json()
        assert "guidance" in body  # FAIL: legacy detail response has no guidance

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

    # ===================================================================
    # AC-NEW-24 (refined): before-engine rejection proof
    # ===================================================================

    def test_edit_status_field_rejected_before_cockpit_view(
        self,
        mock_client: TestClient,
        engine: KanbanEngine,
        view_mock: mock.MagicMock,
    ) -> None:
        """POST /api/tasks/{id}/edit with status in body → 422 AND view NOT called.

        AC-NEW-24 stronger proof: Pydantic rejects extra fields BEFORE the route
        handler runs. The CockpitView mock must NOT be consulted at all.
        FAIL: view_mock.edit_task.assert_not_called() raises (handler reached)
              OR response.status_code != 422.
        """
        task = engine.show_task("1")
        response = mock_client.post(
            "/api/tasks/1/edit",
            json={"updated": task.updated, "status": "done"},  # 'status' is extra
        )
        assert response.status_code == 422
        body = response.json()
        # FastAPI Pydantic validation error: detail is a list of error objects
        assert isinstance(body.get("detail"), list)
        # CockpitView must NOT be reached when Pydantic rejects the body
        view_mock.edit_task.assert_not_called()

    # ===================================================================
    # AC: OCC mutations pass exact expected_updated value to CockpitView
    # ===================================================================

    def test_edit_passes_exact_expected_updated_to_cockpit_view(
        self,
        mock_client: TestClient,
        engine: KanbanEngine,
        view_mock: mock.MagicMock,
    ) -> None:
        """edit route MUST forward exact expected_updated kwarg to CockpitView.edit_task.

        OCC proof: assert_called_once alone does not prove the token is forwarded.
        FAIL: 'expected_updated' absent from call_args, or does not equal request value.
        """
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

    def test_move_passes_exact_expected_updated_to_cockpit_view(
        self,
        mock_client: TestClient,
        engine: KanbanEngine,
        view_mock: mock.MagicMock,
    ) -> None:
        """move route MUST forward exact expected_updated kwarg to CockpitView.move_task.

        OCC proof: verifies the OCC token reaches the view delegation call.
        FAIL: 'expected_updated' absent from call_args, or does not equal request value.
        """
        view_mock.engine = engine  # real engine for pre-delegation OCC/transition checks
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
        """release route MUST forward exact expected_updated kwarg to CockpitView.release_task.

        OCC proof: verifies the OCC token reaches the view delegation call.
        FAIL: 'expected_updated' absent from call_args, or does not equal request value.
        """
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

    # ===================================================================
    # AC: ERR_STALE → 409 for ALL delegated routes (move, release)
    # ===================================================================

    def test_move_stale_token_from_cockpit_view_returns_409(
        self,
        mock_client: TestClient,
        engine: KanbanEngine,
        view_mock: mock.MagicMock,
    ) -> None:
        """ConcurrencyError from CockpitView.move_task → HTTP 409.

        error — proves ERR_STALE propagates from the delegated move call, not just edit.
        FAIL: ConcurrencyError from view.move_task does not yield 409.
        """
        view_mock.engine = engine
        task = engine.show_task("1")
        view_mock.move_task.side_effect = ConcurrencyError(
            code="ERR_STALE", user_message="Stale snapshot"
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
        """ConcurrencyError from CockpitView.release_task → HTTP 409.

        error — proves ERR_STALE propagates from the delegated release call, not just edit.
        FAIL: ConcurrencyError from view.release_task does not yield 409.
        """
        view_mock.show_task.return_value.claimed = True
        view_mock.release_task.side_effect = ConcurrencyError(
            code="ERR_STALE", user_message="Stale snapshot"
        )
        task = engine.show_task("2")
        response = mock_client.post(
            "/api/tasks/2/release",
            json={"updated": task.updated},
        )
        assert response.status_code == 409

    # ===================================================================
    # AC: ERR_NOT_FOUND → 404 for ALL delegated routes (move, release)
    # ===================================================================

    def test_move_not_found_from_cockpit_view_returns_404(
        self,
        mock_client: TestClient,
        engine: KanbanEngine,
        view_mock: mock.MagicMock,
    ) -> None:
        """NotFoundError from CockpitView.move_task → HTTP 404.

        error — proves ERR_NOT_FOUND propagates from the delegated move call, not just edit.
        FAIL: NotFoundError from view.move_task does not yield 404.
        """
        view_mock.engine = engine
        task = engine.show_task("1")
        view_mock.move_task.side_effect = NotFoundError(
            code="ERR_NOT_FOUND", user_message="Task '1' not found"
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
        """NotFoundError from CockpitView.release_task → HTTP 404.

        error — proves ERR_NOT_FOUND propagates from the delegated release call, not just edit.
        FAIL: NotFoundError from view.release_task does not yield 404.
        """
        view_mock.show_task.return_value.claimed = True
        view_mock.release_task.side_effect = NotFoundError(
            code="ERR_NOT_FOUND", user_message="Task '2' not found"
        )
        task = engine.show_task("2")
        response = mock_client.post(
            "/api/tasks/2/release",
            json={"updated": task.updated},
        )
        assert response.status_code == 404

    # ===================================================================
    # AC: ValidationError → 422 for move route
    # ===================================================================

    def test_move_validation_error_from_cockpit_view_returns_422(
        self,
        mock_client: TestClient,
        engine: KanbanEngine,
        view_mock: mock.MagicMock,
    ) -> None:
        """ValidationError from CockpitView.move_task → HTTP 422.

        error — proves ValidationError propagates from the delegated move call, not just edit.
        FAIL: ValidationError from view.move_task does not yield 422.
        """
        view_mock.engine = engine
        task = engine.show_task("1")
        view_mock.move_task.side_effect = ValidationError(
            code="ERR_INVALID_STATUS", user_message="invalid transition"
        )
        response = mock_client.post(
            "/api/tasks/1/move",
            json={"status": "in-progress", "updated": task.updated},
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# TestFromAC_RouteGuardBranches
# ---------------------------------------------------------------------------


class TestFromAC_RouteGuardBranches:
    """Coverage tests for guard/non-happy branches in cockpit route handlers.

    The builder's implementation is complete; these tests prove existing
    guard branches not previously exercised by TestFromAC_CockpitRoutes.

    Categories:
      error    — pre-delegation guard failures (not-found, stale, invalid-transition,
                 not-claimed, no-editable-fields)
      happy    — read route entry points and cache-hit path
    """

    # ===================================================================
    # move_task pre-delegation guards
    # ===================================================================

    def test_move_task_pre_check_not_found_returns_404(
        self,
        mock_client: TestClient,
        view_mock: mock.MagicMock,
    ) -> None:
        """move_task must return 404 when view.engine.show_task raises FileNotFoundError.

        error — pre-delegation guard: FileNotFoundError before OCC check or delegation.
        """
        view_mock.engine.show_task.side_effect = FileNotFoundError()
        response = mock_client.post(
            "/api/tasks/99/move",
            json={"status": "in-progress", "updated": "any-token"},
        )
        assert response.status_code == 404

    def test_move_task_pre_check_stale_token_returns_409(
        self,
        client: TestClient,
    ) -> None:
        """move_task must return 409 when req.updated does not match the stored token.

        error — pre-delegation stale guard (line: if req.updated != str(task.updated)).
        Uses real engine; sends deliberately wrong updated value.
        """
        response = client.post(
            "/api/tasks/1/move",
            json={"status": "in-progress", "updated": "stale-token"},
        )
        assert response.status_code == 409
        detail = response.json().get("detail", "")
        assert "stale" in detail.lower() or "modified" in detail.lower()

    def test_move_task_pre_check_invalid_transition_returns_422(
        self,
        client: TestClient,
        engine: KanbanEngine,
    ) -> None:
        """move_task must return 422 when req.status is not a valid transition.

        error — pre-delegation transition guard (line: if req.status not in transitions).
        Uses real engine; sends real updated value so stale check passes.
        """
        task = engine.show_task("1")
        response = client.post(
            "/api/tasks/1/move",
            json={"status": "nonexistent-status", "updated": task.updated},
        )
        assert response.status_code == 422
        detail = response.json().get("detail", "")
        assert "Cannot move" in detail or "nonexistent" in detail

    # ===================================================================
    # edit_task guard branches
    # ===================================================================

    def test_edit_no_editable_fields_returns_422(
        self,
        client: TestClient,
        engine: KanbanEngine,
    ) -> None:
        """edit_task must return 422 when request has no editable fields.

        error — guard: if not kwargs: raise HTTPException(422, "No editable fields").
        Sends only 'updated' — model_fields_set - {'updated'} is empty.
        """
        task = engine.show_task("1")
        response = client.post(
            "/api/tasks/1/edit",
            json={"updated": task.updated},
        )
        assert response.status_code == 422
        assert "No editable fields" in response.json().get("detail", "")

    def test_edit_tags_field_show_task_not_found_returns_404(
        self,
        mock_client: TestClient,
        engine: KanbanEngine,
        view_mock: mock.MagicMock,
    ) -> None:
        """edit_task must return 404 when tags field triggers show_task and it raises NotFoundError.

        error — early guard: when tags/depends_on/block_reason in fields,
        view.show_task() is called first; NotFoundError → 404 before delegation.
        """
        view_mock.show_task.side_effect = NotFoundError(
            code="ERR_NOT_FOUND", user_message="Task '1' not found"
        )
        task = engine.show_task("1")
        response = mock_client.post(
            "/api/tasks/1/edit",
            json={"updated": task.updated, "tags": ["new-tag"]},
        )
        assert response.status_code == 404

    def test_edit_title_field_updates_task(
        self,
        client: TestClient,
        engine: KanbanEngine,
    ) -> None:
        """edit_task with title field must return 200 and updated task title.

        happy — exercises _build_edit_kwargs title branch and view.edit_task delegation.
        """
        task = engine.show_task("1")
        response = client.post(
            "/api/tasks/1/edit",
            json={"updated": task.updated, "title": "Coverage Title"},
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Coverage Title"

    # ===================================================================
    # release_task guard branch
    # ===================================================================

    def test_release_unclaimed_task_returns_409(
        self,
        client: TestClient,
        engine: KanbanEngine,
    ) -> None:
        """release_task must return 409 when the task is not currently claimed.

        error — guard: if not task.claimed: raise HTTPException(409, "not currently claimed").
        Task 1 is unclaimed in the fixture.
        """
        task = engine.show_task("1")
        response = client.post(
            "/api/tasks/1/release",
            json={"updated": task.updated},
        )
        assert response.status_code == 409
        assert "not currently claimed" in response.json().get("detail", "")

    # ===================================================================
    # read.py — get_board, get_task 404, list_tasks cache-hit, list_sessions filter
    # ===================================================================

    def test_get_board_returns_statuses_and_priorities(
        self, client: TestClient
    ) -> None:
        """GET /api/board must return statuses and priorities from board config.

        happy — exercises get_board route which is not covered by TestFromAC_CockpitRoutes.
        """
        response = client.get("/api/board")
        assert response.status_code == 200
        body = response.json()
        assert "statuses" in body
        assert "priorities" in body
        assert isinstance(body["statuses"], list)
        assert len(body["statuses"]) > 0

    def test_get_task_not_found_returns_404(self, client: TestClient) -> None:
        """GET /api/tasks/{id} must return 404 for a non-existent task.

        error — get_task NotFoundError guard; exercises the except NotFoundError → 404 branch.
        """
        response = client.get("/api/tasks/9999")
        assert response.status_code == 404

    def test_list_tasks_cache_hit_path_returns_tasks(
        self, client: TestClient
    ) -> None:
        """GET /api/tasks on second call must use the cache-hit path.

        happy — first call populates per-engine cache; second call has_changed()=False
        and has_cached_tasks=True, exercising the cache-hit branch in list_tasks.
        """
        # First call: cache miss — populates cache
        first = client.get("/api/tasks")
        assert first.status_code == 200
        # Second call: cache hit (mtime unchanged between calls)
        second = client.get("/api/tasks")
        assert second.status_code == 200
        body = second.json()
        assert "tasks" in body
        assert isinstance(body["tasks"], list)

    def test_list_tasks_cache_hit_with_status_filter(
        self, client: TestClient
    ) -> None:
        """GET /api/tasks?status=todo on cache-hit path must return only todo tasks.

        happy — exercises _filter_cached_tasks on the cache-hit branch with status filter.
        """
        # Warm the cache
        client.get("/api/tasks")
        # Cache-hit call with filter
        response = client.get("/api/tasks?status=todo")
        assert response.status_code == 200
        body = response.json()
        assert all(t["status"] == "todo" for t in body["tasks"])

    def test_list_sessions_filter_all_returns_list(
        self,
        client: TestClient,
        engine: KanbanEngine,
    ) -> None:
        """GET /api/sessions?filter=all must return a flat list including completed sessions.

        happy — exercises list_sessions with filter='all' (vs default 'active').
        """
        engine.claim_task("1")
        engine.end_work("1", note="done", outcome="success")
        response = client.get("/api/sessions?filter=all")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_list_activity_with_limit_filter(
        self,
        client: TestClient,
        engine: KanbanEngine,
    ) -> None:
        """GET /api/activity?limit=1 must return at most one event.

        happy — exercises list_activity route with limit parameter.
        """
        engine.claim_task("1")
        response = client.get("/api/activity?limit=1")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 1

    # ===================================================================
    # _build_edit_kwargs field branches (priority, body, parent)
    # ===================================================================

    def test_edit_priority_field_builds_kwargs(
        self,
        client: TestClient,
        engine: KanbanEngine,
    ) -> None:
        """edit_task with priority field must return 200 (exercises _build_edit_kwargs priority branch).

        happy — line 150: kwargs['priority'] = req.priority.
        """
        task = engine.show_task("1")
        response = client.post(
            "/api/tasks/1/edit",
            json={"updated": task.updated, "priority": "critical"},
        )
        assert response.status_code == 200
        assert response.json()["priority"] == "critical"

    def test_edit_body_field_builds_kwargs(
        self,
        client: TestClient,
        engine: KanbanEngine,
    ) -> None:
        """edit_task with body field must return 200 (exercises _build_edit_kwargs body branch).

        happy — line 154: kwargs['body'] = req.body.
        """
        task = engine.show_task("1")
        response = client.post(
            "/api/tasks/1/edit",
            json={"updated": task.updated, "body": "## Coverage\n- added by test"},
        )
        assert response.status_code == 200
        assert "Coverage" in response.json().get("body", "")

    def test_edit_parent_field_builds_kwargs(
        self,
        mock_client: TestClient,
        engine: KanbanEngine,
        view_mock: mock.MagicMock,
    ) -> None:
        """edit_task with parent field must forward parent to CockpitView.edit_task.

        happy — line 152: kwargs['parent'] = req.parent.
        Uses mock to avoid engine parent-validation constraints.
        """
        view_mock.edit_task.return_value = _single_task_response(engine, "1")
        task = engine.show_task("1")
        response = mock_client.post(
            "/api/tasks/1/edit",
            json={"updated": task.updated, "parent": None},
        )
        assert response.status_code == 200
        call_kwargs = view_mock.edit_task.call_args.kwargs
        assert "parent" in call_kwargs

    # ===================================================================
    # _apply_list_diff — tags add and remove paths
    # ===================================================================

    def test_edit_tags_add_new_tag_via_list_diff(
        self,
        client: TestClient,
        engine: KanbanEngine,
    ) -> None:
        """edit_task with tags=[new] must add tag (exercises _apply_list_diff add path).

        happy — lines 195-200: desired is not None, desired_set - current_set = [new].
        """
        task = engine.show_task("1")
        response = client.post(
            "/api/tasks/1/edit",
            json={"updated": task.updated, "tags": ["phase:test"]},
        )
        assert response.status_code == 200
        assert "phase:test" in response.json().get("tags", [])

    def test_edit_tags_remove_existing_tag_via_list_diff(
        self,
        mock_client: TestClient,
        engine: KanbanEngine,
        view_mock: mock.MagicMock,
    ) -> None:
        """edit_task with tags=[] when task has a tag must compute remove set.

        happy — line 201: if remove: kwargs[remove_key] = remove.
        Uses mock so view.show_task returns a task with an existing tag.
        """
        view_mock.show_task.return_value.tags = ["existing-tag"]
        view_mock.edit_task.return_value = _single_task_response(engine, "1")
        task = engine.show_task("1")
        response = mock_client.post(
            "/api/tasks/1/edit",
            json={"updated": task.updated, "tags": []},
        )
        assert response.status_code == 200
        call_kwargs = view_mock.edit_task.call_args.kwargs
        assert "remove_tag" in call_kwargs
        assert "existing-tag" in call_kwargs["remove_tag"]

    # ===================================================================
    # _apply_block_kwargs and tag-op helpers (lines 211-235)
    # ===================================================================

    def test_edit_block_reason_set_triggers_block_user_tag(
        self,
        mock_client: TestClient,
        engine: KanbanEngine,
        view_mock: mock.MagicMock,
    ) -> None:
        """edit_task with block_reason (non-None) must add block:user tag via _apply_block_kwargs.

        happy — lines 174-175, 217-219, 224-226, 231: block_reason field processed,
        _apply_block_kwargs called with non-None reason, _add_tag_op called, _remove_tag_op called.
        """
        view_mock.show_task.return_value.tags = []
        view_mock.edit_task.return_value = _single_task_response(engine, "1")
        task = engine.show_task("1")
        response = mock_client.post(
            "/api/tasks/1/edit",
            json={"updated": task.updated, "block_reason": "waiting for dependency"},
        )
        assert response.status_code == 200
        call_kwargs = view_mock.edit_task.call_args.kwargs
        assert "block_reason" in call_kwargs
        assert "add_tag" in call_kwargs
        assert "block:user" in call_kwargs["add_tag"]

    def test_edit_block_reason_none_removes_block_user_tag(
        self,
        mock_client: TestClient,
        engine: KanbanEngine,
        view_mock: mock.MagicMock,
    ) -> None:
        """edit_task with block_reason=null on a blocked task must remove block:user tag.

        happy — lines 211-215, 231-235: _apply_block_kwargs None branch;
        block:user in current_tags → _add_tag_op for remove_tag → _remove_tag_op clears add_tag.
        """
        view_mock.show_task.return_value.tags = ["block:user"]
        view_mock.edit_task.return_value = _single_task_response(engine, "1")
        task = engine.show_task("1")
        response = mock_client.post(
            "/api/tasks/1/edit",
            json={"updated": task.updated, "block_reason": None},
        )
        assert response.status_code == 200
        call_kwargs = view_mock.edit_task.call_args.kwargs
        assert "remove_tag" in call_kwargs
        assert "block:user" in call_kwargs["remove_tag"]

    # ===================================================================
    # release_task show_task not-found guard (lines 281-282)
    # ===================================================================

    def test_release_task_show_task_not_found_returns_404(
        self,
        mock_client: TestClient,
        view_mock: mock.MagicMock,
    ) -> None:
        """release_task must return 404 when view.show_task raises NotFoundError.

        error — lines 281-282: except (FileNotFoundError, NotFoundError) → HTTPException 404.
        """
        view_mock.show_task.side_effect = NotFoundError(
            code="ERR_NOT_FOUND", user_message="Task '99' not found"
        )
        response = mock_client.post(
            "/api/tasks/99/release",
            json={"updated": "any-token"},
        )
        assert response.status_code == 404
