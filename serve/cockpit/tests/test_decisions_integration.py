"""Durable integration tests: Cockpit Decisions Tab backend contract (#1649).

Consolidation backstop: verifies the full engine→API chain for the decisions
backend after all backend subtasks (#1640 Pydantic model, #1641 notes cap) are
implemented.

AC5 coverage:
  AC5-a: GET /api/decisions/pending returns a JSON object with top-level
          ``count`` (int) and ``items`` (list) keys — the PendingDRResponse
          shape enforced by Pydantic.
  AC5-b: ``count`` matches ``len(items)`` and each item includes the 8
          required PendingDRItem fields: id, task_id, agent, request_type,
          created, title, body, body_preview.
  AC5-c: POST /api/decisions/{id}/resolve with ``notes`` exceeding 10,000
          characters returns HTTP 422 with a Pydantic validation error
          containing type ``string_too_long``.
  AC5-d: GET /api/decisions/pending returns count=0 and items=[] when the
          pending directory contains no valid files (empty-state path).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_CONFIG_YAML = """\
next_id: 1
"""

_NOTES_OVER_CAP = "x" * 10_001
_NOTES_AT_CAP = "y" * 10_000


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_board(tmp_path: Path) -> Path:
    """Create a minimal kanban board directory and return its path."""
    kanban_dir = tmp_path / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


def _make_decisions_dir(tmp_path: Path) -> Path:
    """Create decisions/pending and decisions/resolved directories."""
    decisions_dir = tmp_path / "decisions"
    (decisions_dir / "pending").mkdir(parents=True)
    (decisions_dir / "resolved").mkdir(parents=True)
    return decisions_dir


def _write_pending_dr(
    decisions_dir: Path,
    *,
    stem: str,
    task_id: int,
    body: str = "# Decision\n\nWhat should we do?",
    response: str = "pending",
) -> Path:
    """Write a minimal pending decision request file; return its path."""
    path = decisions_dir / "pending" / f"{stem}.md"
    content = (
        "---\n"
        f"task_id: {task_id}\n"
        "agent: builder\n"
        "request_type: scope-decision\n"
        "created: '2026-05-01T10:00:00Z'\n"
        f"response: {response}\n"
        "---\n\n"
        f"{body}\n"
    )
    path.write_text(content, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def engine(tmp_path: Path):
    """KanbanEngine backed by an isolated temporary board directory."""
    from owlbear_kanban import KanbanEngine  # noqa: PLC0415

    kanban_dir = _make_board(tmp_path)
    eng = KanbanEngine(kanban_dir)
    eng.list_tasks()  # warm cache
    return eng


@pytest.fixture
def decisions_dir(tmp_path: Path) -> Path:
    """Isolated decisions directory with pending/ and resolved/ subdirs."""
    return _make_decisions_dir(tmp_path)


@pytest.fixture
def client(engine, decisions_dir: Path):
    """FastAPI TestClient with DI overrides for engine and decisions_dir."""
    from fastapi.testclient import TestClient  # noqa: PLC0415

    from owlbear_cockpit import deps as cockpit_deps  # noqa: PLC0415
    from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415

    app.dependency_overrides[get_engine] = lambda: engine
    get_decisions_dir = getattr(cockpit_deps, "get_decisions_dir", None)
    if get_decisions_dir is not None:
        app.dependency_overrides[get_decisions_dir] = lambda: decisions_dir

    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# AC5 — Backend contract (full-stack)
# ---------------------------------------------------------------------------


class TestDecisionsBackendIntegrationDurable:
    """Integration tests for the full engine→API decisions contract (AC5)."""

    # ── AC5-d: empty-state path ──────────────────────────────────────────────

    def test_get_pending_returns_http_200_with_empty_state(self, client: TestClient) -> None:
        """AC5-d: GET /api/decisions/pending returns HTTP 200 when no DRs exist."""
        response = client.get("/api/decisions/pending")
        assert response.status_code == 200

    def test_get_pending_empty_state_has_count_zero_and_empty_items(self, client: TestClient) -> None:
        """AC5-d: count=0 and items=[] when pending directory is empty."""
        body = client.get("/api/decisions/pending").json()
        assert body["count"] == 0
        assert body["items"] == []

    # ── AC5-a + AC5-b: PendingDRResponse shape with real files ──────────────

    def test_get_pending_response_has_count_and_items_keys(self, client: TestClient, decisions_dir: Path) -> None:
        """AC5-a: Response top-level keys are 'count' and 'items'."""
        _write_pending_dr(decisions_dir, stem="dr-shape-test", task_id=42)
        body = client.get("/api/decisions/pending").json()
        assert "count" in body
        assert "items" in body

    def test_get_pending_count_matches_items_length(self, client: TestClient, decisions_dir: Path) -> None:
        """AC5-b: count equals len(items) for a single pending DR."""
        _write_pending_dr(decisions_dir, stem="dr-count-test", task_id=99)
        body = client.get("/api/decisions/pending").json()
        assert body["count"] == len(body["items"])
        assert body["count"] == 1

    def test_get_pending_item_has_all_required_fields(self, client: TestClient, decisions_dir: Path) -> None:
        """AC5-b: Each PendingDRItem exposes all 8 required fields."""
        _write_pending_dr(
            decisions_dir,
            stem="dr-fields-test",
            task_id=7,
            body="# Decision title\n\nWhat to do?",
        )
        body = client.get("/api/decisions/pending").json()
        assert len(body["items"]) == 1
        item = body["items"][0]
        required_fields = {
            "id",
            "task_id",
            "agent",
            "request_type",
            "created",
            "title",
            "body",
            "body_preview",
        }
        assert required_fields.issubset(item.keys()), f"Missing fields: {required_fields - item.keys()}"

    def test_get_pending_task_id_is_integer_not_string(self, client: TestClient, decisions_dir: Path) -> None:
        """AC5-b: task_id is coerced to int by Pydantic (not left as YAML string)."""
        _write_pending_dr(decisions_dir, stem="dr-taskid-coerce", task_id=123)
        body = client.get("/api/decisions/pending").json()
        item = body["items"][0]
        assert isinstance(item["task_id"], int)
        assert item["task_id"] == 123

    def test_get_pending_count_reflects_multiple_pending_drs(self, client: TestClient, decisions_dir: Path) -> None:
        """AC5-b: count equals the number of valid pending DR files."""
        _write_pending_dr(decisions_dir, stem="dr-multi-a", task_id=10)
        _write_pending_dr(decisions_dir, stem="dr-multi-b", task_id=11)
        _write_pending_dr(decisions_dir, stem="dr-multi-c", task_id=12)
        body = client.get("/api/decisions/pending").json()
        assert body["count"] == 3
        assert len(body["items"]) == 3

    # ── AC5-c: notes cap validation ──────────────────────────────────────────

    def test_resolve_with_notes_over_10k_chars_returns_422(self, client: TestClient, decisions_dir: Path) -> None:
        """AC5-c: POST resolve with notes > 10,000 chars returns HTTP 422."""
        _write_pending_dr(decisions_dir, stem="dr-notes-cap", task_id=55)
        response = client.post(
            "/api/decisions/dr-notes-cap/resolve",
            json={
                "response": "approved",
                "notes": _NOTES_OVER_CAP,
            },
        )
        assert response.status_code == 422

    def test_resolve_with_notes_over_10k_chars_returns_string_too_long_error(
        self, client: TestClient, decisions_dir: Path
    ) -> None:
        """AC5-c: 422 body contains Pydantic error type 'string_too_long'."""
        _write_pending_dr(decisions_dir, stem="dr-notes-type", task_id=56)
        response = client.post(
            "/api/decisions/dr-notes-type/resolve",
            json={
                "response": "approved",
                "notes": _NOTES_OVER_CAP,
            },
        )
        body = response.json()
        error_types = [err.get("type") for err in body.get("detail", []) if isinstance(err, dict)]
        assert "string_too_long" in error_types, f"Expected 'string_too_long' in error types; got: {error_types}"

    def test_resolve_with_notes_exactly_at_cap_returns_200(self, client: TestClient, decisions_dir: Path) -> None:
        """AC5-c boundary: notes at exactly 10,000 chars are accepted (HTTP 200)."""
        _write_pending_dr(decisions_dir, stem="dr-notes-boundary", task_id=57)
        response = client.post(
            "/api/decisions/dr-notes-boundary/resolve",
            json={
                "response": "approved",
                "notes": _NOTES_AT_CAP,
            },
        )
        assert response.status_code == 200

    def test_resolve_with_null_notes_returns_200(self, client: TestClient, decisions_dir: Path) -> None:
        """AC5-c: notes=null is accepted (field is optional)."""
        _write_pending_dr(decisions_dir, stem="dr-notes-null", task_id=58)
        response = client.post(
            "/api/decisions/dr-notes-null/resolve",
            json={"response": "approved", "notes": None},
        )
        assert response.status_code == 200
