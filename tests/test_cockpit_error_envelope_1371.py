"""Tests for Cockpit error envelope legacy test migration (task #1371) — retry.

tests/test_cockpit_error_envelope_1370.py covers AC1-AC4(a)(b)(c) in full.
This file covers the remaining gaps identified in the reviewer's Required Follow-up:

  AC7 (td:1): Discriminating API-level assertions proving domain error paths
              return {code, message} without any 'detail' field.
  AC4(d) (td:1): GET /api/tasks/{id} forwards sentinel guidance verbatim from
                 the view (not just a 'guidance' key presence check).
  AC8 (td:0): Decisions-route HTTPException retains FastAPI {detail} format
              and is NOT converted to the domain envelope.

Retry: replaces weak source-string guards from the first test-writer pass with
discriminating API assertions that call real endpoints and verify exact shapes.
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest import mock

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_kanban.errors import ConcurrencyError
from owlbear_kanban.models import ShowTaskResponse

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
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


@pytest.fixture
def board_dir(tmp_path: Path) -> Path:
    kanban_dir = _make_board(tmp_path)
    seed = KanbanEngine(kanban_dir)
    seed.create_task("Alpha task", status="todo", priority="important")
    seed.create_task("Beta task", status="in-progress", priority="needed")
    seed.list_tasks()
    seed.claim_task("2")
    return kanban_dir


@pytest.fixture
def engine(board_dir: Path) -> KanbanEngine:
    eng = KanbanEngine(board_dir)
    eng.list_tasks()
    return eng


@pytest.fixture
def client(engine: KanbanEngine):
    from fastapi.testclient import TestClient  # noqa: PLC0415

    from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415

    app.dependency_overrides[get_engine] = lambda: engine
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def envelope_client(engine: KanbanEngine):
    """TestClient with raise_server_exceptions=False for unexpected-error handler tests."""
    from fastapi.testclient import TestClient  # noqa: PLC0415

    from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415

    app.dependency_overrides[get_engine] = lambda: engine
    try:
        yield TestClient(app, raise_server_exceptions=False)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def mock_view_client(engine: KanbanEngine):
    """TestClient with CockpitView replaced by a MagicMock.

    Yields (client, view_mock) so tests can configure return values before
    issuing requests.
    """
    from fastapi.testclient import TestClient  # noqa: PLC0415

    from owlbear_cockpit.deps import get_view  # noqa: PLC0415
    from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415

    view_mock = mock.MagicMock()
    app.dependency_overrides[get_engine] = lambda: engine
    app.dependency_overrides[get_view] = lambda: view_mock
    try:
        yield TestClient(app), view_mock
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# AC7: discriminating API-level assertions for legacy migration sites
# ---------------------------------------------------------------------------


class TestFromAC_LegacyTestMigration:
    """AC7 (td:1): Domain error paths return {code, message}; no 'detail' key.

    Discriminating API-level assertions: each test triggers a domain-error code
    path and verifies the exact envelope shape — replacing the source-string
    guards from the first test-writer pass.

    Covered migration sites:
      - edit ConcurrencyError → 409   (test_cockpit_mutation_api_1134 ~line 204)
      - move NotFoundError  → 404     (test_cockpit_mutation_api_1135 ~line 165)
      - move ConcurrencyError → 409   (test_cockpit_mutation_api_1135 ~line 313)
      - show-task NotFoundError → 404 (test_cockpit_read_api ~line 461)
    """

    def test_edit_concurrency_error_returns_envelope_not_detail(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """409 stale-edit response carries {code, message}; no 'detail' field."""
        task = engine.show_task("1")
        exc = ConcurrencyError(code="ERR_STALE", user_message="stale snapshot detected")
        with mock.patch.object(engine, "edit_task", side_effect=exc):
            response = client.post(
                "/api/tasks/1/edit",
                json={"updated": task.updated, "title": "Envelope probe"},
            )
        body = response.json()
        assert response.status_code == 409
        assert "detail" not in body, (
            f"Domain error must NOT include 'detail' key; got {body!r}"
        )
        assert body.get("code") == "ERR_STALE"
        assert "stale snapshot detected" in body.get("message", ""), (
            f"Envelope message must carry ConcurrencyError.user_message; got {body!r}"
        )

    def test_move_not_found_returns_envelope_not_detail(
        self, client: TestClient
    ) -> None:
        """404 non-existent-task move response carries {code, message}; no 'detail' field."""
        response = client.post(
            "/api/tasks/999/move",
            json={"status": "in-progress", "updated": "2025-01-01T00:00:00"},
        )
        body = response.json()
        assert response.status_code == 404
        assert "detail" not in body, (
            f"Domain error must NOT include 'detail' key; got {body!r}"
        )
        assert body.get("code") == "ERR_NOT_FOUND"
        assert "999" in str(body.get("message", "")), (
            f"404 message should reference the missing task ID '999'; got {body!r}"
        )

    def test_move_concurrency_error_returns_envelope_not_detail(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """409 stale-move response carries {code, message}; no 'detail' field."""
        task = engine.show_task("1")
        exc = ConcurrencyError(code="ERR_STALE", user_message="stale write detected")
        with mock.patch.object(engine, "move_task", side_effect=exc):
            response = client.post(
                "/api/tasks/1/move",
                json={"status": "in-progress", "updated": task.updated},
            )
        body = response.json()
        assert response.status_code == 409
        assert "detail" not in body, (
            f"Domain error must NOT include 'detail' key; got {body!r}"
        )
        assert body.get("code") == "ERR_STALE"
        assert "stale write detected" in body.get("message", ""), (
            f"Envelope message must carry ConcurrencyError.user_message; got {body!r}"
        )

    def test_get_task_not_found_returns_envelope_not_detail(
        self, client: TestClient
    ) -> None:
        """404 task-detail response carries {code, message}; no 'detail' field."""
        response = client.get("/api/tasks/9999")
        body = response.json()
        assert response.status_code == 404
        assert "detail" not in body, (
            f"Domain error must NOT include 'detail' key; got {body!r}"
        )
        assert body.get("code") == "ERR_NOT_FOUND"
        assert "9999" in str(body.get("message", "")), (
            f"404 message should reference the requested ID '9999'; got {body!r}"
        )


# ---------------------------------------------------------------------------
# AC4(d): sentinel-value forwarding for show-task guidance
# ---------------------------------------------------------------------------


class TestFromAC_ShowTaskGuidanceForwarding:
    """AC4(d) (td:1): GET /api/tasks/{id} forwards guidance verbatim from the view.

    The route is a one-line passthrough. Tests that a non-empty sentinel guidance
    list injected through the view dependency appears unchanged in the response.
    An implementation that hardcodes guidance=[] or drops the list fails this test.
    """

    def test_show_task_forwards_sentinel_guidance_values(
        self, mock_view_client, engine: KanbanEngine
    ) -> None:
        """Sentinel guidance list injected via mocked view appears verbatim in response."""
        client, view_mock = mock_view_client
        sentinel = ["sentinel-guidance-alpha", "sentinel-guidance-beta"]

        task = engine.show_task("1")
        payload = task.model_dump()
        payload["guidance"] = sentinel
        payload["missing_sections"] = None
        if isinstance(payload.get("body"), list):
            payload["body"] = None
        view_mock.show_task.return_value = ShowTaskResponse.model_validate(payload)

        response = client.get("/api/tasks/1")
        body = response.json()

        assert response.status_code == 200
        assert body.get("guidance") == sentinel, (
            f"Expected sentinel guidance {sentinel!r} forwarded verbatim; "
            f"got {body.get('guidance')!r}"
        )


# ---------------------------------------------------------------------------
# AC8: decisions-route framework errors retain FastAPI detail format
# ---------------------------------------------------------------------------


class TestFromAC_DecisionsFrameworkCarveOut:
    """AC8 (td:0): Decisions-route HTTPException retains FastAPI {detail} format.

    FastAPI's built-in HTTPException handler produces {"detail": <value>}.
    The domain envelope handler (KanbanError → {code, message}) must NOT be
    applied here — the decisions route uses HTTPException, not KanbanError.
    """

    def test_malformed_decision_id_returns_detail_body_not_domain_envelope(
        self, client: TestClient
    ) -> None:
        """POST /decisions/.hidden/resolve returns {\"detail\": \"Invalid decision id\"}."""
        response = client.post(
            "/api/decisions/.hidden/resolve",
            json={"response": "approved"},
        )
        assert response.status_code == 422
        body = response.json()
        assert "detail" in body, (
            f"Decisions HTTPException must use FastAPI detail format; got {body!r}"
        )
        assert body["detail"] == "Invalid decision id", (
            f"Expected exact detail string 'Invalid decision id'; got {body['detail']!r}"
        )
        assert "code" not in body, (
            f"Decisions route must NOT use domain envelope; got {body!r}"
        )
        assert "message" not in body, (
            f"Decisions route must NOT use domain envelope; got {body!r}"
        )


# ---------------------------------------------------------------------------
# AC3: Unexpected-error handler — exact stable literal assertions
# ---------------------------------------------------------------------------


class TestFromAC_UnexpectedErrorExactContract:
    """AC3 (td:2): Unexpected exceptions return exact stable literals.

    The 1370 tests prove key presence only ('code' in body, 'message' in body).
    These discriminating tests pin the exact string literals named by AC3:
      code    == "COCKPIT_INTERNAL_ERROR"
      message == "An unexpected error occurred."

    A handler returning a different code/message literal would still pass the
    1370 presence checks but will fail these tests.
    """

    def test_scan_unexpected_error_returns_exact_cockpit_internal_error_code(
        self, envelope_client: TestClient
    ) -> None:
        """RuntimeError from scan_corruption → exact code 'COCKPIT_INTERNAL_ERROR'."""
        from owlbear_cockpit.view import CockpitView  # noqa: PLC0415

        with mock.patch.object(
            CockpitView,
            "scan_corruption",
            side_effect=RuntimeError("disk I/O failure"),
        ):
            resp = envelope_client.post("/api/tasks/scan")

        assert resp.status_code == 500
        assert resp.headers.get("content-type", "").startswith("application/json"), (
            f"Content-type must be application/json; got {resp.headers.get('content-type')!r}"
        )
        body = resp.json()
        assert "detail" not in body, (
            f"Unexpected-error envelope must NOT include 'detail'; got {body!r}"
        )
        assert body.get("code") == "COCKPIT_INTERNAL_ERROR", (
            f"Expected exact code 'COCKPIT_INTERNAL_ERROR'; got {body.get('code')!r}"
        )
        assert body.get("message") == "An unexpected error occurred.", (
            f"Expected exact message 'An unexpected error occurred.'; got {body.get('message')!r}"
        )

    def test_repair_unexpected_error_returns_exact_cockpit_internal_error_message(
        self, envelope_client: TestClient
    ) -> None:
        """RuntimeError from repair_storage → exact message 'An unexpected error occurred.'."""
        from owlbear_cockpit.view import CockpitView  # noqa: PLC0415

        with mock.patch.object(
            CockpitView,
            "repair_storage",
            side_effect=RuntimeError("storage backend unavailable"),
        ):
            resp = envelope_client.post("/api/tasks/repair")

        assert resp.status_code == 500
        assert resp.headers.get("content-type", "").startswith("application/json"), (
            f"Content-type must be application/json; got {resp.headers.get('content-type')!r}"
        )
        body = resp.json()
        assert "detail" not in body, (
            f"Unexpected-error envelope must NOT include 'detail'; got {body!r}"
        )
        assert body.get("code") == "COCKPIT_INTERNAL_ERROR", (
            f"Expected exact code 'COCKPIT_INTERNAL_ERROR'; got {body.get('code')!r}"
        )
        assert body.get("message") == "An unexpected error occurred.", (
            f"Expected exact message 'An unexpected error occurred.'; got {body.get('message')!r}"
        )


# ---------------------------------------------------------------------------
# AC7 (broadened): release-operation domain error paths
# ---------------------------------------------------------------------------


class TestFromAC_ReleaseErrorEnvelope:
    """AC7 broadened: Release-operation domain errors use {code, message} envelope.

    Covers migration sites newly identified in:
      - tests/test_cockpit_mutation_api.py lines 482, 500   (not-found + stale release)
      - tests/test_cockpit_mutation_api_1132.py line 709     (stale release token)
      - tests/test_cockpit_mutation_race.py line 281         (unclaimed release)

    Each test proves the exact envelope shape at the API level: no 'detail' key,
    'code' and 'message' keys present. These discriminate against old detail-only
    assertions that the builder must migrate in the named durable test files.
    """

    def test_release_not_found_returns_envelope_not_detail(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """404 release of non-existent task carries {code, message}; no 'detail' field."""
        token = engine.show_task("1").updated
        response = client.post("/api/tasks/999/release", json={"updated": token})
        body = response.json()
        assert response.status_code == 404
        assert "detail" not in body, (
            f"Domain 404 must NOT include 'detail' key; got {body!r}"
        )
        assert body.get("code") == "ERR_NOT_FOUND", (
            f"Expected code 'ERR_NOT_FOUND'; got {body.get('code')!r}"
        )
        assert "999" in str(body.get("message", "")), (
            f"404 message should reference the missing task ID '999'; got {body!r}"
        )

    def test_release_stale_token_returns_envelope_not_detail(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """409 stale-release carries {code, message}; no 'detail' field.

        Board fixture has task 2 pre-claimed.  Editing bumps 'updated' so the
        saved token is stale when release is attempted.
        """
        task = engine.show_task("2")
        stale_token = task.updated
        engine.edit_task("2", title="Bumped to make stale token")

        response = client.post("/api/tasks/2/release", json={"updated": stale_token})
        body = response.json()
        assert response.status_code == 409, (
            f"Stale release must return 409; got {response.status_code}"
        )
        assert "detail" not in body, (
            f"Domain 409 must NOT include 'detail' key; got {body!r}"
        )
        assert body.get("code") == "ERR_STALE", (
            f"Expected code 'ERR_STALE'; got {body.get('code')!r}"
        )
        assert "message" in body, (
            f"Domain 409 must include 'message' key; got {body!r}"
        )

    def test_release_unclaimed_task_returns_envelope_not_detail(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """409 release of unclaimed task carries {code, message}; no 'detail' field."""
        task = engine.show_task("1")
        response = client.post("/api/tasks/1/release", json={"updated": task.updated})
        body = response.json()
        assert response.status_code == 409, (
            f"Release of unclaimed task must return 409; got {response.status_code}"
        )
        assert "detail" not in body, (
            f"Domain 409 must NOT include 'detail' key; got {body!r}"
        )
        assert "code" in body, (
            f"Domain 409 must include 'code' key; got {body!r}"
        )
        assert "message" in body, (
            f"Domain 409 must include 'message' key; got {body!r}"
        )


# ---------------------------------------------------------------------------
# AC10: Pydantic request-validation carve-out discrimination
# ---------------------------------------------------------------------------


class TestFromAC_PydanticCarveOut:
    """AC10 (td:1): Pydantic request-validation 422 retains FastAPI detail format.

    Discriminating proof: the domain envelope handler must NOT contaminate
    framework request-validation errors.  Both facts are asserted together:
      (a) 'detail' is a list  (FastAPI standard format preserved)
      (b) 'code' and 'message' are absent  (domain envelope not applied)

    The test_cockpit_kanban_routes.py:262 existing assertion only checks (a).
    """

    def test_pydantic_validation_422_retains_detail_list_and_excludes_envelope_keys(
        self, client: TestClient
    ) -> None:
        """Missing required 'updated' in move -> 422 with detail list; no code/message."""
        response = client.post(
            "/api/tasks/1/move",
            json={"status": "in-progress"},  # 'updated' is required
        )
        assert response.status_code == 422
        body = response.json()
        assert isinstance(body.get("detail"), list), (
            f"Pydantic 422 must carry 'detail' list (FastAPI format); got {body!r}"
        )
        assert "code" not in body, (
            f"Pydantic 422 must NOT contain domain 'code' key; got {body!r}"
        )
        assert "message" not in body, (
            f"Pydantic 422 must NOT contain domain 'message' key; got {body!r}"
        )
