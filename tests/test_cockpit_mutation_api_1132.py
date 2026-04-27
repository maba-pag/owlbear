"""Failing tests for #1132 — Wire cockpit mutation routes through CockpitView facade.

RED phase — all tests must fail until implementation is complete.

AC coverage:
  AC1: get_view dependency in deps.py returning CockpitView(engine); import from engine.
  AC2: POST /move delegates to CockpitView.move_task with expected_updated kwarg;
       valid_transitions precheck retained (same-status guard preserved).
  AC3: ReleaseRequest(updated: str) body model; extra='forbid'; route requires body;
       route delegates to CockpitView.release_task(task_id, expected_updated=req.updated).
  AC4a: Move error mapping: NotFoundError→404, ValidationError→422, ConcurrencyError→409.
  AC4b: Release error mapping: NotFoundError→404, ConcurrencyError→409.
  AC5: Release guard uses claimed boolean (not claimed_by). Genuinely claimed task
       returns 200 (G3 fix). Unclaimed route still returns 409 (behavior preserved).
  AC6: _task_to_detail adapted for SingleTaskResponse: claimed_at/claimed present;
       no AttributeError on missing claimed_by.
  AC7: POST /release with stale updated token on claimed task → 409 with stale detail.
  AC8: Release without body → 422 (ReleaseRequest.updated is required). Builder must
       update all existing release calls in test_cockpit_mutation_api.py and
       test_cockpit_mutation_race_1131.py to send body with updated field.
  AC10: Release of claimed task writes activity.jsonl entry with source='cockpit'.
  AC11 (regression guard, currently passes — covered by existing suite):
       Edit route unchanged — direct engine path, no CockpitView delegation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING
from unittest import mock

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_kanban.engine import CockpitView
from owlbear_kanban.errors import ConcurrencyError, NotFoundError, ValidationError

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
    """Create a minimal kanban board directory."""
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

    Task 1: status=todo,        priority=important  (unclaimed — move target)
    Task 2: status=in-progress, priority=needed     (claimed   — release target)
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
    """KanbanEngine bound to the test board with activity logging enabled."""
    eng = KanbanEngine(board_dir, agent_name="cockpit", activity_log=True)
    eng.list_tasks()
    return eng


@pytest.fixture
def client(engine: KanbanEngine):
    """FastAPI TestClient with only get_engine overridden (no get_view)."""
    from fastapi.testclient import TestClient  # noqa: PLC0415
    from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415

    app.dependency_overrides[get_engine] = lambda: engine
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def mock_view_client(engine: KanbanEngine):
    """TestClient with mock CockpitView injected via get_view dependency override.

    Fails with ImportError until AC1 (get_view added to deps.py) is implemented.
    Yields (TestClient, mock_view) tuple.
    """
    from fastapi.testclient import TestClient  # noqa: PLC0415
    from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415
    from owlbear_cockpit.deps import get_view  # noqa: PLC0415  # ImportError → RED

    mock_view = mock.MagicMock(spec=CockpitView)
    # Provide the real engine so valid_transitions precheck can use it.
    mock_view.engine = engine

    app.dependency_overrides[get_engine] = lambda: engine
    app.dependency_overrides[get_view] = lambda: mock_view
    try:
        yield TestClient(app), mock_view
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# AC1: get_view dependency in deps.py
# ---------------------------------------------------------------------------


class TestFromAC_GetViewDependency:
    """AC1: get_view callable exists in owlbear_cockpit.deps; returns CockpitView(engine)."""

    def test_get_view_importable_from_deps(self) -> None:
        """get_view can be imported from owlbear_cockpit.deps."""
        from owlbear_cockpit.deps import get_view  # noqa: PLC0415  # ImportError → RED

        assert callable(get_view), "get_view must be a callable (AC1)"

    def test_deps_module_has_get_view_attribute(self) -> None:
        """deps module has get_view attribute after implementation."""
        import owlbear_cockpit.deps as _deps  # noqa: PLC0415

        assert hasattr(_deps, "get_view"), "get_view must be defined in deps.py (AC1)"

    def test_get_view_callable_uses_cockpit_view(self) -> None:
        """get_view() callable exists and is importable (AC1)."""
        from owlbear_cockpit.deps import get_view  # noqa: PLC0415  # ImportError → RED

        assert get_view is not None, "get_view must be importable and not None (AC1)"

    def test_get_view_returns_cockpit_view_instance(self, engine: KanbanEngine) -> None:
        """get_view(engine) returns a CockpitView instance — not a raw engine or other type (AC1)."""
        from owlbear_cockpit.deps import get_view  # noqa: PLC0415

        result = get_view(engine)
        assert isinstance(result, CockpitView), (
            f"get_view(engine) must return CockpitView, got {type(result).__name__!r} (AC1)"
        )

    def test_get_view_engine_attribute_is_injected_engine(self, engine: KanbanEngine) -> None:
        """CockpitView from get_view() has .engine bound to the injected engine (AC1)."""
        from owlbear_cockpit.deps import get_view  # noqa: PLC0415

        result = get_view(engine)
        assert result.engine is engine, (
            "CockpitView.engine must be the same engine instance that was injected (AC1)"
        )

    def test_get_view_constructs_cockpit_view_with_engine_arg(self, engine: KanbanEngine) -> None:
        """get_view() calls CockpitView(engine) — fails if factory returns wrong type (AC1)."""
        from owlbear_cockpit.deps import get_view  # noqa: PLC0415

        with mock.patch("owlbear_cockpit.deps.CockpitView") as mock_cv:
            mock_cv.return_value = mock.MagicMock(spec=CockpitView)
            get_view(engine)
            mock_cv.assert_called_once_with(engine)


# ---------------------------------------------------------------------------
# AC2: POST /move delegates to CockpitView.move_task
# ---------------------------------------------------------------------------


class TestFromAC_MoveCockpitViewDelegation:
    """AC2: Move route calls CockpitView.move_task with expected_updated kwarg."""

    def test_move_calls_cockpit_view_move_task(
        self, mock_view_client, engine: KanbanEngine
    ) -> None:
        """Move route delegates to CockpitView.move_task (not engine.move_task directly)."""
        client, view = mock_view_client
        task = engine.show_task("1")

        from owlbear_kanban.models import SingleTaskResponse  # noqa: PLC0415

        view.move_task.return_value = SingleTaskResponse(
            id=1,
            title="Alpha task",
            status="in-progress",
            priority="important",
            created=task.created,
            updated=task.updated,
        )
        client.post(
            "/api/tasks/1/move",
            json={"status": "in-progress", "updated": task.updated},
        )
        assert view.move_task.called, (
            "Move route must delegate to CockpitView.move_task (AC2)"
        )

    def test_move_cockpit_view_receives_expected_updated_kwarg(
        self, mock_view_client, engine: KanbanEngine
    ) -> None:
        """CockpitView.move_task receives expected_updated matching req.updated."""
        client, view = mock_view_client
        task = engine.show_task("1")

        from owlbear_kanban.models import SingleTaskResponse  # noqa: PLC0415

        view.move_task.return_value = SingleTaskResponse(
            id=1,
            title="Alpha task",
            status="in-progress",
            priority="important",
            created=task.created,
            updated=task.updated,
        )
        client.post(
            "/api/tasks/1/move",
            json={"status": "in-progress", "updated": task.updated},
        )
        assert view.move_task.called, "move_task must be called"
        call_kwargs = view.move_task.call_args.kwargs
        assert "expected_updated" in call_kwargs, (
            "CockpitView.move_task must receive expected_updated kwarg (AC2)"
        )
        assert call_kwargs["expected_updated"] == task.updated, (
            "expected_updated must equal req.updated (AC2)"
        )

    def test_move_cockpit_view_receives_correct_status(
        self, mock_view_client, engine: KanbanEngine
    ) -> None:
        """CockpitView.move_task receives the target status from req.status."""
        client, view = mock_view_client
        task = engine.show_task("1")

        from owlbear_kanban.models import SingleTaskResponse  # noqa: PLC0415

        view.move_task.return_value = SingleTaskResponse(
            id=1,
            title="Alpha task",
            status="review",
            priority="important",
            created=task.created,
            updated=task.updated,
        )
        client.post(
            "/api/tasks/1/move",
            json={"status": "review", "updated": task.updated},
        )
        args = view.move_task.call_args
        assert args is not None, "move_task must be called"
        # status passed as positional or kwarg
        positional_status = args.args[1] if len(args.args) >= 2 else None
        kwarg_status = args.kwargs.get("status")
        actual_status = positional_status or kwarg_status
        assert actual_status == "review", (
            f"CockpitView.move_task must receive status='review', got {actual_status!r} (AC2)"
        )


# ---------------------------------------------------------------------------
# AC3: ReleaseRequest model and route delegation
# ---------------------------------------------------------------------------


class TestFromAC_ReleaseRequestModel:
    """AC3: ReleaseRequest(updated: str) model; route requires body; delegates to CockpitView."""

    def test_release_request_model_importable(self) -> None:
        """ReleaseRequest is importable from the mutation module."""
        from owlbear_cockpit.routes.mutation import ReleaseRequest  # noqa: PLC0415  # ImportError → RED

        assert ReleaseRequest is not None

    def test_release_request_has_required_updated_field(self) -> None:
        """ReleaseRequest(updated='x') constructs with updated as a required string field."""
        from owlbear_cockpit.routes.mutation import ReleaseRequest  # noqa: PLC0415

        req = ReleaseRequest(updated="2025-01-01T00:00:00")
        assert req.updated == "2025-01-01T00:00:00"

    def test_release_request_forbids_extra_fields(self) -> None:
        """ReleaseRequest with extra field raises pydantic.ValidationError (extra='forbid')."""
        import pydantic  # noqa: PLC0415

        from owlbear_cockpit.routes.mutation import ReleaseRequest  # noqa: PLC0415

        with pytest.raises(pydantic.ValidationError):
            ReleaseRequest(updated="2025-01-01T00:00:00", unknown_field="bad")

    def test_release_without_body_returns_422(self, client: TestClient) -> None:
        """POST /release without body returns 422 — ReleaseRequest.updated is required (AC3/AC8)."""
        response = client.post("/api/tasks/2/release")  # no body
        assert response.status_code == 422, (
            f"Release without body must return 422 (ReleaseRequest.updated required), "
            f"got {response.status_code} (AC3)"
        )

    def test_release_delegates_to_cockpit_view_release_task(
        self, mock_view_client, engine: KanbanEngine
    ) -> None:
        """Release route delegates to CockpitView.release_task (not engine.release_task)."""
        client, view = mock_view_client
        task = engine.show_task("2")

        from owlbear_kanban.models import ShowTaskResponse, SingleTaskResponse  # noqa: PLC0415

        view.show_task.return_value = ShowTaskResponse(
            id=2,
            title="Beta task",
            status="in-progress",
            priority="needed",
            created=task.created,
            updated=task.updated,
            guidance=[],
            claimed_at="2025-01-01T00:00:00",
        )
        view.release_task.return_value = SingleTaskResponse(
            id=2,
            title="Beta task",
            status="in-progress",
            priority="needed",
            created=task.created,
            updated=task.updated,
        )
        client.post("/api/tasks/2/release", json={"updated": task.updated})
        assert view.release_task.called, (
            "Release route must delegate to CockpitView.release_task (AC3)"
        )

    def test_release_passes_expected_updated_to_cockpit_view(
        self, mock_view_client, engine: KanbanEngine
    ) -> None:
        """CockpitView.release_task receives expected_updated=req.updated kwarg."""
        client, view = mock_view_client
        task = engine.show_task("2")

        from owlbear_kanban.models import ShowTaskResponse, SingleTaskResponse  # noqa: PLC0415

        view.show_task.return_value = ShowTaskResponse(
            id=2,
            title="Beta task",
            status="in-progress",
            priority="needed",
            created=task.created,
            updated=task.updated,
            guidance=[],
            claimed_at="2025-01-01T00:00:00",
        )
        view.release_task.return_value = SingleTaskResponse(
            id=2,
            title="Beta task",
            status="in-progress",
            priority="needed",
            created=task.created,
            updated=task.updated,
        )
        client.post("/api/tasks/2/release", json={"updated": task.updated})
        assert view.release_task.called, "release_task must be called"
        call_kwargs = view.release_task.call_args.kwargs
        assert "expected_updated" in call_kwargs, (
            "CockpitView.release_task must receive expected_updated kwarg (AC3)"
        )
        assert call_kwargs["expected_updated"] == task.updated, (
            "expected_updated must equal req.updated (AC3)"
        )


# ---------------------------------------------------------------------------
# AC4a: Move error mapping
# ---------------------------------------------------------------------------


class TestFromAC_MoveErrorMapping:
    """AC4a: Move route maps CockpitView errors to HTTP status codes."""

    def test_move_not_found_error_returns_404(
        self, mock_view_client, engine: KanbanEngine
    ) -> None:
        """CockpitView.move_task raises NotFoundError → route returns 404."""
        client, view = mock_view_client
        task = engine.show_task("1")
        view.move_task.side_effect = NotFoundError(
            code="ERR_NOT_FOUND", user_message="Task '1' not found"
        )
        with mock.patch(
            "owlbear_cockpit.adapter.valid_transitions", return_value={"in-progress"}
        ):
            response = client.post(
                "/api/tasks/1/move",
                json={"status": "in-progress", "updated": task.updated},
            )
        assert response.status_code == 404, (
            "NotFoundError from CockpitView.move_task must map to 404 (AC4a)"
        )

    def test_move_validation_error_returns_422(
        self, mock_view_client, engine: KanbanEngine
    ) -> None:
        """CockpitView.move_task raises ValidationError → route returns 422."""
        client, view = mock_view_client
        task = engine.show_task("1")
        view.move_task.side_effect = ValidationError(
            code="ERR_INVALID_STATUS", user_message="Invalid status transition"
        )
        with mock.patch(
            "owlbear_cockpit.adapter.valid_transitions", return_value={"in-progress"}
        ):
            response = client.post(
                "/api/tasks/1/move",
                json={"status": "in-progress", "updated": task.updated},
            )
        assert response.status_code == 422, (
            "ValidationError from CockpitView.move_task must map to 422 (AC4a)"
        )

    def test_move_concurrency_error_returns_409(
        self, mock_view_client, engine: KanbanEngine
    ) -> None:
        """CockpitView.move_task raises ConcurrencyError → route returns 409."""
        client, view = mock_view_client
        task = engine.show_task("1")
        view.move_task.side_effect = ConcurrencyError(
            code="ERR_STALE", user_message="Stale snapshot"
        )
        with mock.patch(
            "owlbear_cockpit.adapter.valid_transitions", return_value={"in-progress"}
        ):
            response = client.post(
                "/api/tasks/1/move",
                json={"status": "in-progress", "updated": task.updated},
            )
        assert response.status_code == 409, (
            "ConcurrencyError from CockpitView.move_task must map to 409 (AC4a)"
        )


# ---------------------------------------------------------------------------
# AC4b: Release error mapping
# ---------------------------------------------------------------------------


class TestFromAC_ReleaseErrorMapping:
    """AC4b: Release route maps CockpitView errors: NotFoundError→404, ConcurrencyError→409."""

    def test_release_not_found_error_returns_404(
        self, mock_view_client, engine: KanbanEngine
    ) -> None:
        """CockpitView.release_task raises NotFoundError → route returns 404."""
        client, view = mock_view_client
        task = engine.show_task("2")

        from owlbear_kanban.models import ShowTaskResponse  # noqa: PLC0415

        # show_task succeeds (claimed=True) so the unclaimed guard does not fire
        view.show_task.return_value = ShowTaskResponse(
            id=2,
            title="Beta task",
            status="in-progress",
            priority="needed",
            created=task.created,
            updated=task.updated,
            guidance=[],
            claimed_at="2025-01-01T00:00:00",
        )
        view.release_task.side_effect = NotFoundError(
            code="ERR_NOT_FOUND", user_message="Task '2' not found"
        )
        response = client.post("/api/tasks/2/release", json={"updated": task.updated})
        assert response.status_code == 404, (
            "NotFoundError from CockpitView.release_task must map to 404 (AC4b)"
        )

    def test_release_concurrency_error_returns_409(
        self, mock_view_client, engine: KanbanEngine
    ) -> None:
        """CockpitView.release_task raises ConcurrencyError → route returns 409."""
        client, view = mock_view_client
        task = engine.show_task("2")

        from owlbear_kanban.models import ShowTaskResponse  # noqa: PLC0415

        view.show_task.return_value = ShowTaskResponse(
            id=2,
            title="Beta task",
            status="in-progress",
            priority="needed",
            created=task.created,
            updated=task.updated,
            guidance=[],
            claimed_at="2025-01-01T00:00:00",
        )
        view.release_task.side_effect = ConcurrencyError(
            code="ERR_STALE", user_message="Stale snapshot"
        )
        response = client.post("/api/tasks/2/release", json={"updated": task.updated})
        assert response.status_code == 409, (
            "ConcurrencyError from CockpitView.release_task must map to 409 (AC4b)"
        )


# ---------------------------------------------------------------------------
# AC5: Release guard uses claimed boolean (not claimed_by)
# ---------------------------------------------------------------------------


class TestFromAC_ReleaseClaim:
    """AC5: Genuinely claimed task → 200; unclaimed guard preserved via claimed bool."""

    def test_release_genuinely_claimed_task_returns_200(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """Claimed task (claimed_at on disk) released via cockpit → 200 (G3 fix).

        Current behavior: 409 (guard uses claimed_by which is Field(exclude=True),
        always None after disk round-trip). After fix: guard uses claimed boolean
        from CockpitView.show_task which correctly reflects claimed_at.
        """
        task = engine.show_task("2")
        assert task.claimed_at is not None, "Precondition: task 2 must have claimed_at on disk"
        response = client.post("/api/tasks/2/release", json={"updated": task.updated})
        assert response.status_code == 200, (
            f"Genuinely claimed task (claimed_at set) must return 200 after G3 fix (AC5), "
            f"got {response.status_code}"
        )

    def test_release_claimed_task_response_has_required_fields(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """Release 200 response has all required task-detail fields."""
        task = engine.show_task("2")
        response = client.post("/api/tasks/2/release", json={"updated": task.updated})
        assert response.status_code == 200
        body = response.json()
        for field in ("id", "title", "status", "priority", "updated", "claimed", "tags"):
            assert field in body, f"Release response must include '{field}' field (AC5)"

    def test_release_claimed_task_response_claimed_false_after_release(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """Release 200 response has claimed=False (claim cleared by release)."""
        task = engine.show_task("2")
        response = client.post("/api/tasks/2/release", json={"updated": task.updated})
        assert response.status_code == 200
        assert response.json()["claimed"] is False, (
            "Release response must show claimed=False after claim is cleared (AC5)"
        )



# ---------------------------------------------------------------------------
# AC6: _task_to_detail handles SingleTaskResponse (move/release return type)
# ---------------------------------------------------------------------------


class TestFromAC_ResponseAdaptation:
    """AC6: _task_to_detail handles SingleTaskResponse without AttributeError on claimed_by."""

    def test_move_response_no_attribute_error_when_cockpit_view_returns_single_task_response(
        self, mock_view_client, engine: KanbanEngine
    ) -> None:
        """_task_to_detail does not raise AttributeError when handling SingleTaskResponse.

        SingleTaskResponse lacks claimed_by. _task_to_detail must use getattr or
        model_validate approach (see builder guidance) instead of task.claimed_by.
        """
        client, view = mock_view_client
        task = engine.show_task("1")

        from owlbear_kanban.models import SingleTaskResponse  # noqa: PLC0415

        # SingleTaskResponse has no claimed_by attribute; helper must handle this
        result = SingleTaskResponse(
            id=1,
            title="Alpha task",
            status="in-progress",
            priority="important",
            created=task.created,
            updated=task.updated,
        )
        view.move_task.return_value = result
        with mock.patch(
            "owlbear_cockpit.adapter.valid_transitions", return_value={"in-progress"}
        ):
            response = client.post(
                "/api/tasks/1/move",
                json={"status": "in-progress", "updated": task.updated},
            )
        assert response.status_code == 200, (
            f"_task_to_detail must not raise AttributeError on SingleTaskResponse "
            f"(AC6), got {response.status_code}"
        )

    def test_move_response_has_claimed_field_from_single_task_response(
        self, mock_view_client, engine: KanbanEngine
    ) -> None:
        """Move response includes 'claimed' field correctly derived from SingleTaskResponse."""
        client, view = mock_view_client
        task = engine.show_task("1")

        from owlbear_kanban.models import SingleTaskResponse  # noqa: PLC0415

        result = SingleTaskResponse(
            id=1,
            title="Alpha task",
            status="in-progress",
            priority="important",
            created=task.created,
            updated=task.updated,
            claimed_at=None,  # unclaimed → claimed=False
        )
        view.move_task.return_value = result
        with mock.patch(
            "owlbear_cockpit.adapter.valid_transitions", return_value={"in-progress"}
        ):
            response = client.post(
                "/api/tasks/1/move",
                json={"status": "in-progress", "updated": task.updated},
            )
        assert response.status_code == 200
        assert "claimed" in response.json(), (
            "Move response must include 'claimed' field when handling SingleTaskResponse (AC6)"
        )



# ---------------------------------------------------------------------------
# AC7: POST /release with stale updated token → 409 with stale detail
# ---------------------------------------------------------------------------


class TestFromAC_ReleaseStaleToken:
    """AC7: Stale updated token on claimed task → 409 with stale-snapshot detail string."""

    def test_release_stale_updated_token_returns_409_with_stale_detail(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """Claimed task + stale updated token → 409 with stale-snapshot detail (AC7).

        Current behavior: guard fires (claimed_by=None) → 409 with 'not currently claimed'.
        After fix: CockpitView.release_task(expected_updated=stale) raises ConcurrencyError
        → 409 with stale-snapshot detail.
        """
        task = engine.show_task("2")
        stale_token = task.updated
        # Advance task's updated timestamp so stale_token is now outdated
        engine.edit_task("2", title="Modified to advance updated timestamp")

        response = client.post("/api/tasks/2/release", json={"updated": stale_token})
        assert response.status_code == 409
        detail = response.json()["detail"]
        assert "stale" in detail.lower() or "modified" in detail.lower(), (
            f"Stale token on claimed task must return 409 with stale-snapshot detail (AC7), "
            f"got detail: {detail!r}"
        )

    def test_release_fresh_updated_token_on_claimed_task_returns_200(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """Claimed task + fresh updated token → 200 (contrast with stale-token 409, AC7)."""
        task = engine.show_task("2")
        response = client.post("/api/tasks/2/release", json={"updated": task.updated})
        assert response.status_code == 200, (
            f"Claimed task with fresh updated token must return 200 (AC7 contrast), "
            f"got {response.status_code}"
        )


# ---------------------------------------------------------------------------
# AC10: Release writes activity.jsonl entry with source='cockpit'
# ---------------------------------------------------------------------------


class TestFromAC_ReleaseActivityLogging:
    """AC10: Release of claimed task writes activity.jsonl entry with source='cockpit'."""

    def test_release_writes_activity_source_cockpit(
        self, client: TestClient, engine: KanbanEngine, board_dir: Path
    ) -> None:
        """Release success (200) produces activity.jsonl entry with source='cockpit'."""
        task = engine.show_task("2")
        response = client.post("/api/tasks/2/release", json={"updated": task.updated})
        assert response.status_code == 200, (
            f"Precondition: release must return 200 to verify activity logging (AC10), "
            f"got {response.status_code}"
        )
        activity_file = board_dir / "activity.jsonl"
        assert activity_file.exists(), "activity.jsonl must exist after successful release (AC10)"
        entries = [
            json.loads(line)
            for line in activity_file.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        cockpit_entries = [e for e in entries if e.get("source") == "cockpit"]
        assert len(cockpit_entries) >= 1, (
            "At least one activity entry must have source='cockpit' after release (AC10)"
        )
