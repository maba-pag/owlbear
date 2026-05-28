"""Tests for #1856: Cockpit API — GET /api/requests/pending and POST /api/requests/{id}/resolve.

AC coverage:
  AC1 → TestFromAC_GetRequestsPending
  AC2 → TestFromAC_PostRequestsResolve
  AC3 → TestFromAC_BareCompleteNormalization
  AC4 → TestFromAC_RouteWiring
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_kanban.errors import NotFoundError, ValidationError
from owlbear_kanban.request_models import RequestOption, RequestRecord, Resolution

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Board scaffolding
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
wave_size: 4
agent_map:
  research: []
  backlog: []
  todo: []
  in-progress: []
  review: []
  docs: []
  done: []
agent_types: {}
agent_compatibility: {}
non_impl_tags: [research, docs]
archival_reasons: [completed, deprecated, dropped, duplicate, wontfix]
status_predicates: {}
claim_timeout: 1h
next_id: 1001
"""

_TASK_CONTENT = """\
---
id: 42
title: Test Task
status: todo
priority: needed
created: "2026-05-01T10:00:00+00:00"
updated: "2026-05-01T10:00:00+00:00"
tags: []
parent: null
depends_on: []
blocked: false
block_reason: null
claimed_at: null
archival_reason: null
archival_refs: []
---

Task body.
"""


def _make_board(base_dir: Path) -> Path:
    """Create a minimal kanban board directory structure."""
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    (kanban_dir / "decisions" / "pending").mkdir(parents=True, exist_ok=True)
    (kanban_dir / "decisions" / "resolved").mkdir(parents=True, exist_ok=True)
    (kanban_dir / "tasks" / "42-test-task.md").write_text(_TASK_CONTENT, encoding="utf-8")
    return kanban_dir


def _make_decision_record(request_id: str | None = None) -> RequestRecord:
    """Build a RequestRecord for a pending decision request."""
    rid = request_id or str(uuid.uuid4())
    return RequestRecord(
        request_id=rid,
        task_id=42,
        kind="decision",
        title="Test Decision",
        summary="A test decision summary.",
        agent="test-agent",
        created_at="2026-05-25T10:00:00+02:00",
        options=[
            RequestOption(
                option_id="option-a",
                label="Option Alpha",
                confidence=0.8,
                recommended=True,
                rationale="First option rationale.",
            )
        ],
        resolution=Resolution(selected_option_id=None, free_text=None, resolved_at=None),
        body="Decision body.",
    )


def _make_action_record(request_id: str | None = None) -> RequestRecord:
    """Build a RequestRecord for a pending action request."""
    rid = request_id or str(uuid.uuid4())
    return RequestRecord(
        request_id=rid,
        task_id=42,
        kind="action",
        title="Test Action",
        summary="A test action summary.",
        agent="test-agent",
        created_at="2026-05-25T10:00:00+02:00",
        options=[],
        resolution=Resolution(selected_option_id=None, free_text=None, resolved_at=None),
        body="Action body.",
    )


def _make_resolved_action_record(request_id: str | None = None) -> RequestRecord:
    """Build a RequestRecord for a resolved action request."""
    rid = request_id or str(uuid.uuid4())
    return RequestRecord(
        request_id=rid,
        task_id=42,
        kind="action",
        title="Test Action",
        summary="A test action summary.",
        agent="test-agent",
        created_at="2026-05-25T10:00:00+02:00",
        options=[],
        resolution=Resolution(
            selected_option_id=None,
            free_text="",
            resolved_at="2026-05-25T11:00:00+02:00",
        ),
        body="Action body.",
    )


def _make_resolved_decision_record(request_id: str | None = None) -> RequestRecord:
    """Build a RequestRecord for a resolved decision request."""
    rid = request_id or str(uuid.uuid4())
    return RequestRecord(
        request_id=rid,
        task_id=42,
        kind="decision",
        title="Test Decision",
        summary="A test decision summary.",
        agent="test-agent",
        created_at="2026-05-25T10:00:00+02:00",
        options=[
            RequestOption(
                option_id="option-a",
                label="Option Alpha",
                confidence=0.8,
                recommended=True,
                rationale="First option rationale.",
            )
        ],
        resolution=Resolution(
            selected_option_id="option-a",
            free_text=None,
            resolved_at="2026-05-25T11:00:00+02:00",
        ),
        body="Decision body.",
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_engine() -> MagicMock:
    """MagicMock engine for testing error paths and sweep/listing behavior."""
    eng = MagicMock(spec=KanbanEngine)
    eng.sweep_requests.return_value = []
    eng.list_requests.return_value = []
    return eng


@pytest.fixture
def mock_client(mock_engine: MagicMock):
    """FastAPI TestClient wired to the mock engine via dependency override."""
    from fastapi.testclient import TestClient  # noqa: PLC0415

    from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415

    app.dependency_overrides[get_engine] = lambda: mock_engine
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# AC1: GET /api/requests/pending
# ---------------------------------------------------------------------------


class TestGetRequestsPending:
    """AC1: GET /api/requests/pending — sweep + list + JSON response shape."""

    def test_returns_pending_records_list(self, mock_engine: MagicMock, mock_client: TestClient) -> None:
        """AC1 happy: returns a JSON array containing pending request records."""
        record = _make_action_record()
        mock_engine.list_requests.return_value = [record]

        resp = mock_client.get("/api/requests/pending")

        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 1

    def test_response_item_has_required_fields(self, mock_engine: MagicMock, mock_client: TestClient) -> None:
        """AC1 happy: each item contains request_id, task_id, kind, title, summary, agent, created_at, options, body."""
        record = _make_action_record()
        mock_engine.list_requests.return_value = [record]

        resp = mock_client.get("/api/requests/pending")

        assert resp.status_code == 200
        item = resp.json()[0]
        required_fields = {
            "request_id",
            "task_id",
            "kind",
            "title",
            "summary",
            "agent",
            "created_at",
            "options",
            "body",
        }
        for field in required_fields:
            assert field in item, f"Missing required field: {field!r}"

    def test_decision_request_options_have_required_subfields(
        self, mock_engine: MagicMock, mock_client: TestClient
    ) -> None:
        """AC1 happy: decision request options include option_id, label, confidence, recommended, rationale."""
        record = _make_decision_record()
        mock_engine.list_requests.return_value = [record]

        resp = mock_client.get("/api/requests/pending")

        assert resp.status_code == 200
        options = resp.json()[0]["options"]
        assert len(options) == 1
        option = options[0]
        for field in ("option_id", "label", "confidence", "recommended", "rationale"):
            assert field in option, f"Missing option sub-field: {field!r}"

    def test_action_request_has_empty_options(self, mock_engine: MagicMock, mock_client: TestClient) -> None:
        """AC1 boundary: action request returns empty options list."""
        record = _make_action_record()
        mock_engine.list_requests.return_value = [record]

        resp = mock_client.get("/api/requests/pending")

        assert resp.status_code == 200
        assert resp.json()[0]["options"] == []

    def test_returns_empty_list_when_no_pending(self, mock_engine: MagicMock, mock_client: TestClient) -> None:
        """AC1 edge: returns empty JSON array when no pending requests exist."""
        mock_engine.list_requests.return_value = []

        resp = mock_client.get("/api/requests/pending")

        assert resp.status_code == 200
        assert resp.json() == []

    def test_sweep_exception_does_not_abort_listing(
        self,
        mock_engine: MagicMock,
        mock_client: TestClient,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """AC1 edge: sweep_requests exception is caught (WARNING logged) and listing continues."""
        import logging  # noqa: PLC0415

        mock_engine.sweep_requests.side_effect = OSError("simulated disk I/O error")
        mock_engine.list_requests.return_value = []

        with caplog.at_level(logging.WARNING):
            resp = mock_client.get("/api/requests/pending")

        assert resp.status_code == 200
        assert resp.json() == []
        # list_requests must still be called after the sweep failure
        mock_engine.list_requests.assert_called_once()

    def test_response_excludes_resolution_field(self, mock_engine: MagicMock, mock_client: TestClient) -> None:
        """AC1 boundary: response model extra='forbid' — 'resolution' must not appear in response."""
        record = _make_action_record()
        mock_engine.list_requests.return_value = [record]

        resp = mock_client.get("/api/requests/pending")

        assert resp.status_code == 200
        item = resp.json()[0]
        assert "resolution" not in item

    def test_normal_path_calls_sweep_requests_once(self, mock_engine: MagicMock, mock_client: TestClient) -> None:
        """AC1 interaction: GET calls engine.sweep_requests() on the normal (non-exception) path."""
        mock_engine.list_requests.return_value = []

        mock_client.get("/api/requests/pending")

        mock_engine.sweep_requests.assert_called_once_with()

    def test_normal_path_delegates_list_requests_with_pending_status(
        self, mock_engine: MagicMock, mock_client: TestClient
    ) -> None:
        """AC1 interaction: GET delegates to engine.list_requests(status='pending') — not an unfiltered call."""
        mock_engine.list_requests.return_value = []

        mock_client.get("/api/requests/pending")

        mock_engine.list_requests.assert_called_once_with(status="pending")

    def test_sweep_failure_emits_warning_log_record(
        self,
        mock_engine: MagicMock,
        mock_client: TestClient,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """AC1 edge: sweep exception → WARNING log record is emitted (not silently swallowed)."""
        import logging  # noqa: PLC0415

        mock_engine.sweep_requests.side_effect = OSError("disk error")
        mock_engine.list_requests.return_value = []

        with caplog.at_level(logging.WARNING, logger="owlbear_cockpit.routes.requests"):
            mock_client.get("/api/requests/pending")

        warning_records = [r for r in caplog.records if r.levelno >= logging.WARNING]
        assert warning_records, "Expected at least one WARNING log record from sweep failure"


# ---------------------------------------------------------------------------
# AC2: POST /api/requests/{id}/resolve
# ---------------------------------------------------------------------------


class TestPostRequestsResolve:
    """AC2: POST /api/requests/{id}/resolve — UUID4 validation, delegation, error mapping."""

    def test_resolve_decision_request_returns_200(self, mock_engine: MagicMock, mock_client: TestClient) -> None:
        """AC2 happy: valid UUID4 + decision body with selected_option_id → 200."""
        rid = str(uuid.uuid4())
        mock_engine.resolve_request.return_value = _make_resolved_decision_record(request_id=rid)

        resp = mock_client.post(
            f"/api/requests/{rid}/resolve",
            json={"selected_option_id": "option-a", "free_text": None, "kind": "decision"},
        )

        assert resp.status_code == 200

    def test_resolve_action_request_returns_200(self, mock_engine: MagicMock, mock_client: TestClient) -> None:
        """AC2 happy: valid UUID4 + action body with free_text → 200."""
        rid = str(uuid.uuid4())
        mock_engine.resolve_request.return_value = _make_resolved_action_record(request_id=rid)

        resp = mock_client.post(
            f"/api/requests/{rid}/resolve",
            json={"selected_option_id": None, "free_text": "done", "kind": "action"},
        )

        assert resp.status_code == 200

    def test_response_has_required_fields(self, mock_engine: MagicMock, mock_client: TestClient) -> None:
        """AC2 happy: 200 response contains request_id, task_id, kind, title, resolved_at."""
        rid = str(uuid.uuid4())
        mock_engine.resolve_request.return_value = _make_resolved_decision_record(request_id=rid)

        resp = mock_client.post(
            f"/api/requests/{rid}/resolve",
            json={"selected_option_id": "option-a", "free_text": None, "kind": "decision"},
        )

        assert resp.status_code == 200
        body = resp.json()
        for field in ("request_id", "task_id", "kind", "title", "resolved_at"):
            assert field in body, f"Missing response field: {field!r}"

    def test_non_uuid_id_returns_422_with_invalid_request_id(self, mock_client: TestClient) -> None:
        """AC2 error: non-UUID path param → 422 HTTPException detail='Invalid request id'."""
        resp = mock_client.post(
            "/api/requests/not-a-uuid/resolve",
            json={"selected_option_id": "x", "free_text": None, "kind": "decision"},
        )

        assert resp.status_code == 422
        assert resp.json()["detail"] == "Invalid request id"

    def test_uuid_v1_id_returns_422_with_invalid_request_id(self, mock_client: TestClient) -> None:
        """AC2 boundary: UUID v1 (not UUID4) → 422 HTTPException detail='Invalid request id'."""
        uuid_v1 = "550e8400-e29b-11d4-a716-446655440000"  # UUID version 1

        resp = mock_client.post(
            f"/api/requests/{uuid_v1}/resolve",
            json={"selected_option_id": None, "free_text": "ok", "kind": "action"},
        )

        assert resp.status_code == 422
        assert resp.json()["detail"] == "Invalid request id"

    def test_engine_not_found_returns_404(self, mock_engine: MagicMock, mock_client: TestClient) -> None:
        """AC2 error: engine raises NotFoundError → 404 via existing KanbanError handler."""
        rid = str(uuid.uuid4())
        mock_engine.resolve_request.side_effect = NotFoundError(code="ERR_NOT_FOUND", user_message="request not found")

        resp = mock_client.post(
            f"/api/requests/{rid}/resolve",
            json={"selected_option_id": None, "free_text": "done", "kind": "action"},
        )

        assert resp.status_code == 404
        # Distinguish engine-raised 404 from route-not-registered 404
        body = resp.json()
        assert body.get("code") == "ERR_NOT_FOUND"

    def test_engine_already_resolved_returns_422(self, mock_engine: MagicMock, mock_client: TestClient) -> None:
        """AC2 error: engine raises ValidationError (ERR_ALREADY_RESOLVED) → 422 via existing handler."""
        rid = str(uuid.uuid4())
        mock_engine.resolve_request.side_effect = ValidationError(
            code="ERR_ALREADY_RESOLVED", user_message="already resolved"
        )

        resp = mock_client.post(
            f"/api/requests/{rid}/resolve",
            json={"selected_option_id": None, "free_text": "done", "kind": "action"},
        )

        assert resp.status_code == 422

    def test_extra_field_in_body_returns_422(self, mock_client: TestClient) -> None:
        """AC2 error: request body with extra='forbid' — unknown field → 422."""
        rid = str(uuid.uuid4())

        resp = mock_client.post(
            f"/api/requests/{rid}/resolve",
            json={
                "selected_option_id": "x",
                "free_text": None,
                "kind": "decision",
                "unknown_field": "bad",
            },
        )

        assert resp.status_code == 422

    def test_invalid_kind_value_returns_422(self, mock_client: TestClient) -> None:
        """AC2 error: kind must be 'decision' or 'action' — unrecognized value → 422."""
        rid = str(uuid.uuid4())

        resp = mock_client.post(
            f"/api/requests/{rid}/resolve",
            json={"selected_option_id": None, "free_text": "ok", "kind": "bad-kind"},
        )

        assert resp.status_code == 422

    def test_resolve_decision_passes_request_id_and_option_id_to_engine(
        self, mock_engine: MagicMock, mock_client: TestClient
    ) -> None:
        """AC2 interaction: POST delegates resolve_request with submitted request_id, selected_option_id, free_text."""
        rid = str(uuid.uuid4())
        mock_engine.resolve_request.return_value = _make_resolved_decision_record(request_id=rid)

        mock_client.post(
            f"/api/requests/{rid}/resolve",
            json={"selected_option_id": "option-a", "free_text": None, "kind": "decision"},
        )

        mock_engine.resolve_request.assert_called_once_with(rid, "option-a", None)

    def test_resolve_action_passes_request_id_and_free_text_to_engine(
        self, mock_engine: MagicMock, mock_client: TestClient
    ) -> None:
        """AC2 interaction: POST delegates resolve_request with submitted request_id, selected_option_id, free_text for action."""
        rid = str(uuid.uuid4())
        mock_engine.resolve_request.return_value = _make_resolved_action_record(request_id=rid)

        mock_client.post(
            f"/api/requests/{rid}/resolve",
            json={"selected_option_id": None, "free_text": "done", "kind": "action"},
        )

        mock_engine.resolve_request.assert_called_once_with(rid, None, "done")


# ---------------------------------------------------------------------------
# AC3: POST bare-Complete normalization
# ---------------------------------------------------------------------------


class TestBareCompleteNormalization:
    """AC3: both null + kind='action' normalizes free_text to ''; otherwise 422."""

    def test_both_null_kind_action_delegates_with_empty_free_text(
        self, mock_engine: MagicMock, mock_client: TestClient
    ) -> None:
        """AC3 happy: both null + kind='action' normalizes free_text to '' before engine.resolve_request."""
        rid = str(uuid.uuid4())
        mock_engine.resolve_request.return_value = _make_resolved_action_record(request_id=rid)

        resp = mock_client.post(
            f"/api/requests/{rid}/resolve",
            json={"selected_option_id": None, "free_text": None, "kind": "action"},
        )

        assert resp.status_code == 200
        # Verify the route normalized free_text to "" (not None) when delegating
        mock_engine.resolve_request.assert_called_once_with(rid, None, "")

    def test_both_null_no_kind_returns_422(self, mock_client: TestClient) -> None:
        """AC3 error: both null, kind field absent → 422 with specific detail message."""
        rid = str(uuid.uuid4())

        resp = mock_client.post(
            f"/api/requests/{rid}/resolve",
            json={"selected_option_id": None, "free_text": None},
        )

        assert resp.status_code == 422
        assert resp.json()["detail"] == "decision requests require selected_option_id or free_text"

    def test_both_null_kind_decision_returns_422(self, mock_client: TestClient) -> None:
        """AC3 error: both null + kind='decision' → 422 with specific detail message."""
        rid = str(uuid.uuid4())

        resp = mock_client.post(
            f"/api/requests/{rid}/resolve",
            json={"selected_option_id": None, "free_text": None, "kind": "decision"},
        )

        assert resp.status_code == 422
        assert resp.json()["detail"] == "decision requests require selected_option_id or free_text"

    def test_both_null_kind_none_returns_422(self, mock_client: TestClient) -> None:
        """AC3 boundary: kind=null (explicit JSON null) treated as absent → same 422."""
        rid = str(uuid.uuid4())

        resp = mock_client.post(
            f"/api/requests/{rid}/resolve",
            json={"selected_option_id": None, "free_text": None, "kind": None},
        )

        assert resp.status_code == 422
        assert resp.json()["detail"] == "decision requests require selected_option_id or free_text"


# ---------------------------------------------------------------------------
# AC4: Route wiring
# ---------------------------------------------------------------------------


class TestRouteWiring:
    """AC4: routes/requests.py registered in main.py with prefix='/api'."""

    def test_get_requests_route_registered(self, mock_engine: MagicMock, mock_client: TestClient) -> None:
        """AC4 direct: GET /api/requests/pending returns 200 (not 404 — route is registered)."""
        mock_engine.list_requests.return_value = []

        resp = mock_client.get("/api/requests/pending")

        assert resp.status_code == 200

    def test_post_requests_route_registered(self, mock_client: TestClient) -> None:
        """AC4 direct: POST /api/requests/{uuid}/resolve is reachable (returns non-404)."""
        rid = str(uuid.uuid4())
        # Send an invalid body — a registered route returns 422; an absent route returns 404.
        resp = mock_client.post(
            f"/api/requests/{rid}/resolve",
            json={"selected_option_id": None, "free_text": None, "unknown": "extra"},
        )

        # 404 means the route is not registered; any other status means it is reachable
        assert resp.status_code != 404

    def test_routes_requests_file_exists(self) -> None:
        """AC4 direct: routes/requests.py exists as a separate file (not inlined into decisions.py)."""
        cockpit_routes = Path(__file__).parent.parent / "serve" / "cockpit" / "src" / "owlbear_cockpit" / "routes"
        requests_file = cockpit_routes / "requests.py"

        assert requests_file.exists(), (
            "routes/requests.py does not exist — builder must create it and register it in main.py"
        )


# ---------------------------------------------------------------------------
# AC3 retry: Error envelope proof + UUID4 canonicalization
# ---------------------------------------------------------------------------


class TestErrorEnvelopeAndCanonicalization:
    """AC3: ValidationError → shared envelope {code, message}; uppercase UUID4 → canonical lowercase delegation."""

    def test_engine_already_resolved_returns_422_with_envelope_code(
        self, mock_engine: MagicMock, mock_client: TestClient
    ) -> None:
        """AC3 error: engine ValidationError(ERR_ALREADY_RESOLVED) → 422 response body code=='ERR_ALREADY_RESOLVED'."""
        rid = str(uuid.uuid4())
        mock_engine.resolve_request.side_effect = ValidationError(
            code="ERR_ALREADY_RESOLVED", user_message="already resolved"
        )

        resp = mock_client.post(
            f"/api/requests/{rid}/resolve",
            json={"selected_option_id": None, "free_text": "done", "kind": "action"},
        )

        assert resp.status_code == 422
        body = resp.json()
        assert body.get("code") == "ERR_ALREADY_RESOLVED", (
            f"Expected envelope code='ERR_ALREADY_RESOLVED', got {body!r}"
        )

    def test_uppercase_uuid4_canonicalized_to_lowercase_for_engine(
        self, mock_engine: MagicMock, mock_client: TestClient
    ) -> None:
        """AC3 regression: uppercase UUID4 accepted, but engine.resolve_request receives lowercase canonical form."""
        rid_lower = str(uuid.uuid4())
        rid_upper = rid_lower.upper()
        mock_engine.resolve_request.return_value = _make_resolved_action_record(request_id=rid_lower)

        mock_client.post(
            f"/api/requests/{rid_upper}/resolve",
            json={"selected_option_id": None, "free_text": "done", "kind": "action"},
        )

        # Engine must receive the lowercase canonical id, not the original uppercase path param
        mock_engine.resolve_request.assert_called_once_with(rid_lower, None, "done")

    def test_uppercase_uuid4_accepted_returns_200(self, mock_engine: MagicMock, mock_client: TestClient) -> None:
        """AC3 regression: uppercase UUID4 is not rejected by the API (canonicalized → 200)."""
        rid_lower = str(uuid.uuid4())
        rid_upper = rid_lower.upper()
        mock_engine.resolve_request.return_value = _make_resolved_action_record(request_id=rid_lower)

        resp = mock_client.post(
            f"/api/requests/{rid_upper}/resolve",
            json={"selected_option_id": None, "free_text": "done", "kind": "action"},
        )

        assert resp.status_code == 200
