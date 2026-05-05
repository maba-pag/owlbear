"""Failing tests for cockpit edit-route CAS engagement (#1134).

RED phase — AC1 and AC2 tests must fail until the edit route is fixed in GREEN (#1134).
AC3 regression guards are expected to pass (they protect existing behaviour from builder changes).

AC coverage:
  - AC1: engine.edit_task receives expected_updated kwarg set to req.updated
  - AC2: ConcurrencyError from engine.edit_task → HTTPException(409) with canonical
         detail "Task was modified since your last load (stale snapshot)"; error must
         not propagate as 500
  - AC3: existing edit-route behaviour is preserved — happy path 200, stale 409,
         404, no-fields 422 (regression guards; expected to pass in RED)
"""

from __future__ import annotations

from pathlib import Path
from unittest import mock

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_kanban.models import ConcurrencyError


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
    """Board with one unclaimed task in todo status."""
    kanban_dir = _make_board(tmp_path)
    seed = KanbanEngine(kanban_dir)
    seed.create_task("Alpha task", status="todo", priority="important")
    seed.list_tasks()
    return kanban_dir


@pytest.fixture
def engine(board_dir: Path) -> KanbanEngine:
    """KanbanEngine bound to the test board."""
    eng = KanbanEngine(board_dir, activity_log=False)
    eng.list_tasks()
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


# ---------------------------------------------------------------------------
# AC1 — engine.edit_task receives expected_updated kwarg
# ---------------------------------------------------------------------------


class TestFromAC_EditCASEngagement:
    """AC1: edit route passes expected_updated to engine.edit_task."""

    def test_edit_passes_expected_updated_to_engine(
        self, client, engine: KanbanEngine
    ) -> None:
        """engine.edit_task must be called with expected_updated in kwargs.

        The current route calls engine.edit_task(**kwargs) without forwarding
        expected_updated (TOCTOU gap).  After the fix, expected_updated=req.updated
        must appear in the captured call kwargs, engaging the engine CAS.
        """
        task = engine.show_task("1")
        with mock.patch.object(engine, "edit_task", wraps=engine.edit_task) as mocked:
            response = client.post(
                "/api/tasks/1/edit",
                json={"updated": task.updated, "title": "CAS probe"},
            )
        assert response.status_code == 200, f"Unexpected status: {response.status_code}"
        assert mocked.called, "engine.edit_task must have been called"
        call_kwargs = mocked.call_args.kwargs
        assert "expected_updated" in call_kwargs, (
            "Edit route must pass expected_updated to engine (AC1 — CAS must be engaged, "
            "not just the route-level precheck)"
        )

    def test_edit_expected_updated_value_matches_request_snapshot(
        self, client, engine: KanbanEngine
    ) -> None:
        """The expected_updated value forwarded to engine must equal req.updated.

        The CAS token is the updated timestamp from the request body.  Forwarding
        a different value would defeat the CAS purpose.
        """
        task = engine.show_task("1")
        with mock.patch.object(engine, "edit_task", wraps=engine.edit_task) as mocked:
            response = client.post(
                "/api/tasks/1/edit",
                json={"updated": task.updated, "title": "CAS value probe"},
            )
        assert response.status_code == 200, f"Unexpected status: {response.status_code}"
        assert mocked.called, "engine.edit_task must have been called"
        forwarded = mocked.call_args.kwargs.get("expected_updated")
        assert forwarded == task.updated, (
            f"expected_updated forwarded to engine ({forwarded!r}) must equal "
            f"req.updated ({task.updated!r})"
        )


# ---------------------------------------------------------------------------
# AC2 — ConcurrencyError → HTTPException(409)
# ---------------------------------------------------------------------------


class TestFromAC_ConcurrencyErrorHandler:
    """AC2: ConcurrencyError from engine.edit_task is mapped to HTTP 409."""

    def test_edit_concurrency_error_returns_409(
        self, client, engine: KanbanEngine
    ) -> None:
        """When engine.edit_task raises ConcurrencyError, route must return 409.

        Currently the route has no except ConcurrencyError handler, so the
        exception propagates to the ASGI layer as 500.
        """
        task = engine.show_task("1")
        exc = ConcurrencyError(code="ERR_STALE", user_message="stale")
        with mock.patch.object(engine, "edit_task", side_effect=exc):
            response = client.post(
                "/api/tasks/1/edit",
                json={"updated": task.updated, "title": "ConcurrencyError probe"},
            )
        assert response.status_code == 409, (
            f"ConcurrencyError must map to 409, got {response.status_code}"
        )

    def test_edit_concurrency_error_detail_matches_canonical_message(
        self, client, engine: KanbanEngine
    ) -> None:
        """409 detail string must be the canonical stale-snapshot message."""
        task = engine.show_task("1")
        exc = ConcurrencyError(code="ERR_STALE", user_message="stale")
        with mock.patch.object(engine, "edit_task", side_effect=exc):
            response = client.post(
                "/api/tasks/1/edit",
                json={"updated": task.updated, "title": "Detail probe"},
            )
        detail = response.json().get("detail", "")
        assert detail == "Task was modified since your last load (stale snapshot)", (
            f"Detail string mismatch: {detail!r}"
        )

    def test_edit_concurrency_error_not_propagated_as_500(
        self, client, engine: KanbanEngine
    ) -> None:
        """ConcurrencyError must not leak as an unhandled 500 server error."""
        task = engine.show_task("1")
        exc = ConcurrencyError(code="ERR_STALE", user_message="stale")
        with mock.patch.object(engine, "edit_task", side_effect=exc):
            response = client.post(
                "/api/tasks/1/edit",
                json={"updated": task.updated, "title": "500-guard probe"},
            )
        assert response.status_code != 500, (
            "ConcurrencyError must not propagate as 500 — add except ConcurrencyError handler"
        )


# ---------------------------------------------------------------------------
# AC3 — Existing edit-route behaviour is unchanged (regression guards)
# ---------------------------------------------------------------------------


class TestFromAC_ExistingBehaviorUnchanged:
    """AC3: Builder changes must not break existing edit-route behaviour.

    These tests guard currently-passing behaviour.  They are expected to pass
    in RED phase (they document the contract the builder must preserve).
    """

    def test_edit_title_happy_path_returns_200(
        self, client, engine: KanbanEngine
    ) -> None:
        """Direct regression: edit title with valid snapshot → 200 with updated task."""
        task = engine.show_task("1")
        response = client.post(
            "/api/tasks/1/edit",
            json={"updated": task.updated, "title": "Regression guard title"},
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Regression guard title"

    def test_edit_stale_snapshot_still_returns_409(self, client) -> None:
        """Regression: stale updated token → 409 (precheck preserved)."""
        response = client.post(
            "/api/tasks/1/edit",
            json={"updated": "1970-01-01T00:00:00+00:00", "title": "Stale probe"},
        )
        assert response.status_code == 409

    def test_edit_nonexistent_task_still_returns_404(self, client) -> None:
        """Regression: non-existent task ID → 404."""
        response = client.post(
            "/api/tasks/999/edit",
            json={"updated": "1970-01-01T00:00:00+00:00", "title": "Not found probe"},
        )
        assert response.status_code == 404

    def test_edit_no_editable_fields_still_returns_422(
        self, client, engine: KanbanEngine
    ) -> None:
        """Regression: request with only updated field (no editable fields) → 422."""
        task = engine.show_task("1")
        response = client.post(
            "/api/tasks/1/edit",
            json={"updated": task.updated},
        )
        assert response.status_code == 422
