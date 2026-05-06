"""Tests for Cockpit backend error envelope and guidance contract (#1370).

RED phase — all tests must fail until the error envelope handler is
implemented in #1371.

AC coverage:
  AC1 (td:2): Error responses use {code, message} envelope — replaces FastAPI {detail}
  AC2 (td:2): Representative errors: 404 not-found, 409 stale, 422 validation,
              500 config, 500 scanner/repair unhandled exception
  AC3 (td:1): HTTP status codes unchanged by envelope introduction
  AC4 (td:2): Guidance policy — errors no guidance field; list cache-aware; mutations guidance=[]
  META (td:1): At least one test per category fails against current routes (proves RED for #1371)
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest import mock

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_kanban.errors import ConfigError

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
    """Create a minimal kanban board. Returns kanban_dir."""
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
    """Board with 2 tasks: task 1 at status=todo, task 2 at status=in-progress."""
    kanban_dir = _make_board(tmp_path)
    seed = KanbanEngine(kanban_dir)
    seed.create_task("Alpha task", status="todo", priority="important")
    seed.create_task("Beta task", status="in-progress", priority="needed")
    seed.list_tasks()  # populate id→filename cache
    return kanban_dir


@pytest.fixture
def engine(board_dir: Path) -> KanbanEngine:
    """KanbanEngine with activity logging enabled."""
    eng = KanbanEngine(board_dir, activity_log=True)
    eng.list_tasks()  # populate id→filename cache
    return eng


@pytest.fixture
def client(engine: KanbanEngine):
    """TestClient with engine injected; raise_server_exceptions=False for envelope tests."""
    from fastapi.testclient import TestClient  # noqa: PLC0415
    from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415

    app.dependency_overrides[get_engine] = lambda: engine
    try:
        yield TestClient(app, raise_server_exceptions=False)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def cache(board_dir: Path):
    """MtimeScanCache instance for the test board's tasks directory."""
    from owlbear_cockpit.cache import MtimeScanCache  # noqa: PLC0415

    return MtimeScanCache(board_dir / "tasks")


@pytest.fixture
def cache_client(engine: KanbanEngine, cache):
    """TestClient with engine and cache both overridden."""
    from fastapi.testclient import TestClient  # noqa: PLC0415
    from owlbear_cockpit.deps import get_cache  # noqa: PLC0415
    from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415

    app.dependency_overrides[get_engine] = lambda: engine
    app.dependency_overrides[get_cache] = lambda: cache
    try:
        yield TestClient(app, raise_server_exceptions=False)
    finally:
        app.dependency_overrides.clear()


def _has_kanban_error_handler() -> bool:
    """Return True if a KanbanError handler is registered on the Cockpit app.

    Used as a pre-condition in guidance policy tests: FAILS in RED phase (handler
    absent), PASSES after #1371 registers the exception handler.
    """
    from owlbear_cockpit.main import app  # noqa: PLC0415
    from owlbear_kanban.errors import KanbanError  # noqa: PLC0415

    return any(
        isinstance(exc_cls, type) and issubclass(exc_cls, KanbanError)
        for exc_cls in app.exception_handlers
    )


# ---------------------------------------------------------------------------
# AC1: Error envelope shape — {code, message} replaces FastAPI's {detail}
# ---------------------------------------------------------------------------


class TestFromAC_ErrorEnvelopeShape:
    """AC1 (td:2): error responses use {code, message} envelope, not {detail: str}.

    All tests FAIL until #1371 implements the exception handler.
    happy: code + message present; error: detail absent; boundary: stale-409 has code;
    edge: field values are non-empty strings.
    """

    def test_not_found_error_has_code_field(self, client: TestClient) -> None:
        """404 response body contains a stable 'code' field."""
        resp = client.get("/api/tasks/99999")
        assert resp.status_code == 404
        body = resp.json()
        assert "code" in body  # FAILS: current response is {"detail": "..."}

    def test_not_found_error_has_message_field(self, client: TestClient) -> None:
        """404 response body contains a human-readable 'message' field."""
        resp = client.get("/api/tasks/99999")
        assert resp.status_code == 404
        body = resp.json()
        assert "message" in body  # FAILS: no 'message' field in current response

    def test_not_found_error_no_detail_field(self, client: TestClient) -> None:
        """404 response body does NOT contain FastAPI's default 'detail' field."""
        resp = client.get("/api/tasks/99999")
        assert resp.status_code == 404
        body = resp.json()
        assert "detail" not in body  # FAILS: 'detail' IS present currently

    def test_envelope_code_is_stable_string(self, client: TestClient) -> None:
        """Envelope 'code' value is a non-empty string (machine-readable identifier)."""
        resp = client.get("/api/tasks/99999")
        assert resp.status_code == 404
        body = resp.json()
        code = body.get("code")
        assert isinstance(code, str)  # FAILS: code is absent (None)
        assert code  # non-empty

    def test_envelope_message_is_string(self, client: TestClient) -> None:
        """Envelope 'message' value is a non-empty human-readable string."""
        resp = client.get("/api/tasks/99999")
        assert resp.status_code == 404
        body = resp.json()
        message = body.get("message")
        assert isinstance(message, str)  # FAILS: message is absent
        assert message  # non-empty

    def test_stale_conflict_has_code_field(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """409 stale-conflict response body contains a 'code' field."""
        tasks = engine.list_tasks(status="todo")
        assert tasks, "fixture must have a todo task"
        task = tasks[0]
        resp = client.post(
            f"/api/tasks/{task.id}/move",
            json={"status": "in-progress", "updated": "2000-01-01T00:00:00"},
        )
        assert resp.status_code == 409
        body = resp.json()
        assert "code" in body  # FAILS: {"detail": "Task was modified..."} has no code

    def test_stale_conflict_409_code_is_nonempty_string(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """AC1 tightening: 409 envelope code and message are non-empty strings."""
        tasks = engine.list_tasks(status="todo")
        assert tasks, "fixture must have a todo task"
        task = tasks[0]
        resp = client.post(
            f"/api/tasks/{task.id}/move",
            json={"status": "in-progress", "updated": "2000-01-01T00:00:00"},
        )
        assert resp.status_code == 409
        body = resp.json()
        code = body.get("code")
        assert isinstance(code, str)  # FAILS: code is absent (None)
        assert code  # non-empty
        message = body.get("message")
        assert isinstance(message, str)  # FAILS: message is absent
        assert message  # non-empty

    def test_invalid_transition_422_code_is_nonempty_string(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """AC1 tightening: 422 envelope code and message are non-empty strings."""
        tasks = engine.list_tasks(status="todo")
        assert tasks, "fixture must have a todo task"
        task = tasks[0]
        resp = client.post(
            f"/api/tasks/{task.id}/move",
            json={"status": "nonexistent-status", "updated": task.updated},
        )
        assert resp.status_code == 422
        body = resp.json()
        code = body.get("code")
        assert isinstance(code, str)  # FAILS: code is absent (None)
        assert code  # non-empty
        message = body.get("message")
        assert isinstance(message, str)  # FAILS: message is absent
        assert message  # non-empty

    def test_config_error_500_code_is_nonempty_string(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """AC1 tightening: 500 envelope code and message are non-empty strings."""
        from owlbear_cockpit.view import CockpitView  # noqa: PLC0415

        tasks = engine.list_tasks(status="todo")
        assert tasks, "fixture must have a todo task"
        task = tasks[0]
        with mock.patch.object(
            CockpitView,
            "edit_task",
            side_effect=ConfigError("ERR_INVALID_STATUS", "invalid board configuration"),
        ):
            resp = client.post(
                f"/api/tasks/{task.id}/edit",
                json={"updated": task.updated, "title": "Patched title"},
            )
        assert resp.status_code == 500
        body = resp.json()
        code = body.get("code")
        assert isinstance(code, str)  # FAILS: code is absent (None)
        assert code  # non-empty
        message = body.get("message")
        assert isinstance(message, str)  # FAILS: message is absent
        assert message  # non-empty


# ---------------------------------------------------------------------------
# AC2: Representative error coverage — status code + envelope per error type
# ---------------------------------------------------------------------------


class TestFromAC_ErrorCoverage:
    """AC2 (td:2): each expected error type returns correct status + {code, message}.

    Covers: 404 not-found, 409 stale, 422 invalid-transition, 500 config-error,
    500 scanner/repair unhandled exception.
    All tests FAIL until #1371 implements the exception handler.
    happy: not-found; error: stale, validation, config, scanner, repair
    """

    def test_not_found_404_has_envelope(self, client: TestClient) -> None:
        """GET /api/tasks/{id} for missing task → 404 + code + message."""
        resp = client.get("/api/tasks/99999")
        body = resp.json()
        assert resp.status_code == 404
        assert "code" in body  # FAILS
        assert "message" in body  # FAILS

    def test_stale_conflict_409_has_envelope(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """POST /api/tasks/{id}/move with stale updated token → 409 + code + message."""
        tasks = engine.list_tasks(status="todo")
        assert tasks
        task = tasks[0]
        resp = client.post(
            f"/api/tasks/{task.id}/move",
            json={"status": "in-progress", "updated": "2000-01-01T00:00:00"},
        )
        body = resp.json()
        assert resp.status_code == 409
        assert "code" in body  # FAILS
        assert "message" in body  # FAILS
        assert "detail" not in body  # FAILS — FastAPI detail still present

    def test_invalid_transition_422_has_envelope(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """POST /api/tasks/{id}/move with invalid target status → 422 + code + message."""
        tasks = engine.list_tasks(status="todo")
        assert tasks
        task = tasks[0]
        resp = client.post(
            f"/api/tasks/{task.id}/move",
            json={"status": "nonexistent-status", "updated": task.updated},
        )
        body = resp.json()
        assert resp.status_code == 422
        assert "code" in body  # FAILS
        assert "message" in body  # FAILS
        assert "detail" not in body  # FAILS — FastAPI detail still present

    def test_config_error_500_has_envelope(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """POST /api/tasks/{id}/edit raising ConfigError → 500 + code + message."""
        tasks = engine.list_tasks(status="todo")
        assert tasks
        task = tasks[0]
        from owlbear_cockpit.view import CockpitView  # noqa: PLC0415

        with mock.patch.object(
            CockpitView,
            "edit_task",
            side_effect=ConfigError("ERR_INVALID_STATUS", "invalid board configuration"),
        ):
            resp = client.post(
                f"/api/tasks/{task.id}/edit",
                json={"updated": task.updated, "title": "Patched title"},
            )
        body = resp.json()
        assert resp.status_code == 500
        assert "code" in body  # FAILS: currently {"detail": "Invalid board configuration"}
        assert "message" in body  # FAILS
        assert "detail" not in body  # FAILS — FastAPI detail still present

    def test_scan_corruption_exception_500_has_envelope(
        self, client: TestClient
    ) -> None:
        """POST /api/tasks/scan raising RuntimeError → 500 + code + message, not generic page."""
        from owlbear_cockpit.view import CockpitView  # noqa: PLC0415

        with mock.patch.object(
            CockpitView,
            "scan_corruption",
            side_effect=RuntimeError("disk I/O failure"),
        ):
            resp = client.post("/api/tasks/scan")
        assert resp.status_code == 500
        # Pre-#1371: Starlette returns plain text; post-#1371: JSON envelope
        assert resp.headers.get("content-type", "").startswith("application/json")  # FAILS
        body = resp.json()
        assert "code" in body
        assert "message" in body
        assert "detail" not in body  # FAILS — envelope replaces FastAPI detail

    def test_repair_storage_exception_500_has_envelope(
        self, client: TestClient
    ) -> None:
        """POST /api/tasks/repair raising RuntimeError → 500 + code + message."""
        from owlbear_cockpit.view import CockpitView  # noqa: PLC0415

        with mock.patch.object(
            CockpitView,
            "repair_storage",
            side_effect=RuntimeError("disk I/O failure"),
        ):
            resp = client.post("/api/tasks/repair")
        assert resp.status_code == 500
        # Pre-#1371: Starlette returns plain text; post-#1371: JSON envelope
        assert resp.headers.get("content-type", "").startswith("application/json")  # FAILS
        body = resp.json()
        assert "code" in body
        assert "message" in body
        assert "detail" not in body  # FAILS — envelope replaces FastAPI detail


# ---------------------------------------------------------------------------
# AC3: HTTP status codes preserved — envelope wraps existing semantics
# ---------------------------------------------------------------------------


class TestFromAC_StatusPreservation:
    """AC3 (td:1): HTTP status codes are unchanged when the error envelope is introduced.

    Each test combines a status assertion (passes now) with an envelope assertion
    (fails now) to ensure at least one test per class fails in RED phase.
    """

    def test_not_found_preserves_404_with_envelope(self, client: TestClient) -> None:
        """Not-found error: 404 status preserved; response also includes code field."""
        resp = client.get("/api/tasks/99999")
        assert resp.status_code == 404  # passes now — status must not change
        body = resp.json()
        assert "code" in body  # FAILS — envelope not yet present

    def test_stale_preserves_409_with_envelope(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """Stale-conflict error: 409 status preserved; response also includes code field."""
        tasks = engine.list_tasks(status="todo")
        assert tasks
        task = tasks[0]
        resp = client.post(
            f"/api/tasks/{task.id}/move",
            json={"status": "in-progress", "updated": "2000-01-01T00:00:00"},
        )
        assert resp.status_code == 409  # passes now — status must not change
        body = resp.json()
        assert "code" in body  # FAILS

    def test_validation_preserves_422_with_envelope(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """Invalid-transition error: 422 status preserved; response also includes code field."""
        tasks = engine.list_tasks(status="todo")
        assert tasks
        task = tasks[0]
        resp = client.post(
            f"/api/tasks/{task.id}/move",
            json={"status": "nonexistent-status", "updated": task.updated},
        )
        assert resp.status_code == 422  # passes now — status must not change
        body = resp.json()
        assert "code" in body  # FAILS


# ---------------------------------------------------------------------------
# AC4: Guidance policy
# ---------------------------------------------------------------------------


class TestFromAC_GuidancePolicy:
    """AC4 (td:2): guidance policy contract for error, list, and mutation responses.

    (a) Error responses do NOT include a 'guidance' field.
    (b) List cache miss includes guidance from engine; cache hit returns guidance=[].
    (c) Successful mutation responses return guidance=[].

    Tests (b) and (c) assert that a KanbanError exception handler is registered
    (#1371 pre-condition) before checking guidance behavior, guaranteeing RED
    phase failure until #1371 registers the handler.
    happy: list cache miss; edge: list cache hit; boundary: error no guidance;
    error path: mutation guidance=[]
    """

    def test_error_response_no_guidance_and_uses_envelope(
        self, client: TestClient
    ) -> None:
        """(a) 404 error: no 'guidance' field AND response uses code+message envelope."""
        resp = client.get("/api/tasks/99999")
        assert resp.status_code == 404
        body = resp.json()
        assert "guidance" not in body  # passes now (detail-response has no guidance)
        assert "code" in body  # FAILS — envelope not yet present

    def test_list_cache_miss_guidance_in_response(
        self, cache_client: TestClient
    ) -> None:
        """(b) Cache-miss list response forwards exact engine guidance (not a hardcoded empty list).

        Injects a sentinel guidance payload via mock so a hardcoded [] implementation
        cannot falsely pass this test.
        Pre-condition: KanbanError exception handler must be registered (#1371).
        """
        assert _has_kanban_error_handler()  # FAILS — handler not yet registered

        from owlbear_cockpit.view import CockpitView  # noqa: PLC0415

        sentinel_guidance = ["cockpit-test-guidance-sentinel"]
        with mock.patch.object(
            CockpitView,
            "list_tasks",
            return_value=mock.MagicMock(
                tasks=[],
                guidance=sentinel_guidance,
                missing_ids=[],
            ),
        ):
            resp = cache_client.get("/api/tasks")
        body = resp.json()
        assert resp.status_code == 200
        assert body["guidance"] == sentinel_guidance  # proves forwarding, not hardcoded []

    def test_list_cache_hit_guidance_is_empty_list(
        self, cache_client: TestClient
    ) -> None:
        """(b) Cache-hit returns guidance=[] even when the seeding miss had sentinel guidance.

        Seeds the cache via a mocked miss that returns non-empty sentinel guidance.
        After the mock exits, the second request is a cache hit (directory unchanged)
        and must return guidance=[] — proving the hit path never surfaces stale guidance.
        Pre-condition: KanbanError exception handler must be registered (#1371).
        """
        assert _has_kanban_error_handler()  # FAILS — handler not yet registered

        from owlbear_cockpit.view import CockpitView  # noqa: PLC0415

        sentinel_guidance = ["cockpit-test-cache-hit-sentinel"]
        with mock.patch.object(
            CockpitView,
            "list_tasks",
            return_value=mock.MagicMock(
                tasks=[],
                guidance=sentinel_guidance,
                missing_ids=[],
            ),
        ):
            cache_client.get("/api/tasks")  # cache miss — sentinel guidance stored

        # Second request: cache hit — list_tasks is NOT called; guidance must be []
        resp = cache_client.get("/api/tasks")
        body = resp.json()
        assert resp.status_code == 200
        assert body.get("guidance") == []  # must NOT return the sentinel guidance

    def test_mutation_response_guidance_is_empty_list(
        self, cache_client: TestClient, engine: KanbanEngine
    ) -> None:
        """(c) Successful mutation response returns guidance=[] (no operation-level guidance).

        Pre-condition: KanbanError exception handler must be registered (#1371).
        """
        assert _has_kanban_error_handler()  # FAILS — handler not yet registered

        tasks = engine.list_tasks(status="todo")
        assert tasks, "fixture must have a todo task"
        task = tasks[0]
        resp = cache_client.post(
            f"/api/tasks/{task.id}/move",
            json={"status": "in-progress", "updated": task.updated},
        )
        body = resp.json()
        assert resp.status_code == 200
        assert body.get("guidance") == []
