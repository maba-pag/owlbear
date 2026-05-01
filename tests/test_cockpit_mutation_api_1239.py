"""Tests for MoveRequest archival fields and route pass-through (#1239).

RED phase — all tests must fail until implementation is complete.

AC coverage:
  AC1: MoveRequest with no archival_reason/archival_refs fields deserialises
       correctly (backwards-compatible) — defaults archival_reason=None,
       archival_refs=[].
  AC2: MoveRequest with archival_reason="completed" and archival_refs=[1, 2]
       deserialises with correct types and defaults.
  AC3: extra="forbid" still rejects unknown fields (no regression).
  AC4: Move route handler calls view.move_task() with archival_reason and
       archival_refs forwarded from the request.
  AC5: Move route with default values (archival_reason=None, archival_refs=[])
       passes through without error.
"""

from __future__ import annotations

from pathlib import Path
from unittest import mock

import pydantic
import pytest

from owlbear_kanban import KanbanEngine
from owlbear_cockpit.routes.mutation import MoveRequest
from owlbear_cockpit.view import CockpitView


# ---------------------------------------------------------------------------
# Board helpers
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
    """Board with one task at todo status (move/route target)."""
    kanban_dir = _make_board(tmp_path)
    seed = KanbanEngine(kanban_dir, agent_name="seed")
    seed.create_task("Alpha task", status="todo", priority="important")
    seed.list_tasks()
    return kanban_dir


@pytest.fixture
def engine(board_dir: Path) -> KanbanEngine:
    """KanbanEngine bound to the test board."""
    eng = KanbanEngine(board_dir, agent_name="cockpit", activity_log=True)
    eng.list_tasks()
    return eng


@pytest.fixture
def mock_view_client(engine: KanbanEngine):
    """TestClient with mock CockpitView injected via get_view dependency.

    Yields (TestClient, mock_view) tuple.
    Fails with ImportError until AC1 (get_view in deps.py) is implemented.
    """
    from fastapi.testclient import TestClient  # noqa: PLC0415
    from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415
    from owlbear_cockpit.deps import get_view  # noqa: PLC0415

    mock_view = mock.MagicMock(spec=CockpitView)
    mock_view.engine = engine

    app.dependency_overrides[get_engine] = lambda: engine
    app.dependency_overrides[get_view] = lambda: mock_view
    try:
        yield TestClient(app), mock_view
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# AC1 + AC2 + AC3 — MoveRequest model field tests
# ---------------------------------------------------------------------------


class TestFromAC_MoveRequestArchivalFields:
    """Tests for MoveRequest archival field extension (AC1, AC2, AC3)."""

    # --- AC1: backwards-compatible defaults ---

    def test_moverequest_without_archival_fields_has_none_reason(self) -> None:
        """MoveRequest without archival_reason defaults to None (AC1)."""
        req = MoveRequest(status="in-progress", updated="2026-01-01T00:00:00+00:00")
        # AttributeError → RED (field does not exist yet)
        assert req.archival_reason is None

    def test_moverequest_without_archival_fields_has_empty_refs(self) -> None:
        """MoveRequest without archival_refs defaults to [] (AC1)."""
        req = MoveRequest(status="in-progress", updated="2026-01-01T00:00:00+00:00")
        # AttributeError → RED (field does not exist yet)
        assert req.archival_refs == []

    # --- AC2: explicit archival field values accepted ---

    def test_moverequest_accepts_archival_reason_string(self) -> None:
        """MoveRequest accepts archival_reason as a string value (AC2)."""
        # ValidationError (extra="forbid" rejects undeclared field) → RED
        req = MoveRequest(
            status="archived",
            updated="2026-01-01T00:00:00+00:00",
            archival_reason="completed",
        )
        assert req.archival_reason == "completed"

    def test_moverequest_accepts_archival_refs_list_of_ints(self) -> None:
        """MoveRequest accepts archival_refs as a list of ints (AC2)."""
        # ValidationError (extra="forbid" rejects undeclared field) → RED
        req = MoveRequest(
            status="archived",
            updated="2026-01-01T00:00:00+00:00",
            archival_refs=[1, 2],
        )
        assert req.archival_refs == [1, 2]

    def test_moverequest_archival_reason_accepts_none_explicitly(self) -> None:
        """archival_reason=None is accepted (str | None type) (AC2)."""
        # ValidationError (extra="forbid") → RED
        req = MoveRequest(
            status="in-progress",
            updated="2026-01-01T00:00:00+00:00",
            archival_reason=None,
        )
        assert req.archival_reason is None

    def test_moverequest_archival_refs_accepts_empty_list_explicitly(self) -> None:
        """archival_refs=[] is explicitly accepted as a valid value (AC2)."""
        # ValidationError (extra="forbid") → RED
        req = MoveRequest(
            status="in-progress",
            updated="2026-01-01T00:00:00+00:00",
            archival_refs=[],
        )
        assert req.archival_refs == []

    def test_moverequest_full_archival_payload_round_trips(self) -> None:
        """MoveRequest with both archival fields set deserialises correctly (AC2)."""
        # ValidationError (extra="forbid") → RED
        req = MoveRequest(
            status="archived",
            updated="2026-01-01T00:00:00+00:00",
            archival_reason="deprecated",
            archival_refs=[5, 10],
        )
        assert req.archival_reason == "deprecated"
        assert req.archival_refs == [5, 10]

    # --- AC3: extra="forbid" regression guard ---

    def test_extra_forbid_preserved_after_archival_fields_added(self) -> None:
        """extra='forbid' still rejects truly unknown fields after extension (AC3).

        This test requires archival_reason to be a declared field (not extra).
        The first MoveRequest() call fails in RED (archival_reason is extra) →
        making the whole test fail in RED.
        """
        # AC2 dependency: archival_reason must be accepted as declared field
        # (fails in RED — extra field rejection)
        req = MoveRequest(
            status="in-progress",
            updated="2026-01-01T00:00:00+00:00",
            archival_reason="completed",
        )
        assert req.archival_reason == "completed"
        # Regression: a genuinely unknown field must still be rejected
        with pytest.raises(pydantic.ValidationError):
            MoveRequest(
                status="in-progress",
                updated="2026-01-01T00:00:00+00:00",
                archival_reason="completed",
                completely_unknown_field="should-be-rejected",
            )


# ---------------------------------------------------------------------------
# AC4 + AC5 — Move route archival pass-through tests
# ---------------------------------------------------------------------------


class TestFromAC_MoveRouteArchivalPassThrough:
    """Tests for move route forwarding archival kwargs to view.move_task (AC4, AC5)."""

    def test_move_route_forwards_archival_reason_to_view(
        self, mock_view_client, engine: KanbanEngine
    ) -> None:
        """Route passes req.archival_reason to view.move_task (AC4).

        Fails in RED: Pydantic rejects archival_reason as an extra field → 422.
        """
        from owlbear_kanban.models import SingleTaskResponse  # noqa: PLC0415

        client, view = mock_view_client
        task = engine.show_task("1")
        view.move_task.return_value = SingleTaskResponse(
            id=1,
            title="Alpha task",
            status="in-progress",
            priority="important",
            created=task.created,
            updated=task.updated,
        )

        resp = client.post(
            "/api/tasks/1/move",
            json={
                "status": "in-progress",
                "updated": task.updated,
                "archival_reason": "dropped",
            },
        )
        # Fails in RED: extra field → 422 instead of 200
        assert resp.status_code == 200
        call_kwargs = view.move_task.call_args.kwargs
        assert call_kwargs.get("archival_reason") == "dropped"

    def test_move_route_forwards_archival_refs_to_view(
        self, mock_view_client, engine: KanbanEngine
    ) -> None:
        """Route passes req.archival_refs to view.move_task (AC4).

        Fails in RED: Pydantic rejects archival_refs as an extra field → 422.
        """
        from owlbear_kanban.models import SingleTaskResponse  # noqa: PLC0415

        client, view = mock_view_client
        task = engine.show_task("1")
        view.move_task.return_value = SingleTaskResponse(
            id=1,
            title="Alpha task",
            status="in-progress",
            priority="important",
            created=task.created,
            updated=task.updated,
        )

        resp = client.post(
            "/api/tasks/1/move",
            json={
                "status": "in-progress",
                "updated": task.updated,
                "archival_refs": [2, 3],
            },
        )
        # Fails in RED: extra field → 422 instead of 200
        assert resp.status_code == 200
        call_kwargs = view.move_task.call_args.kwargs
        assert call_kwargs.get("archival_refs") == [2, 3]

    def test_move_route_default_archival_reason_forwarded_as_none(
        self, mock_view_client, engine: KanbanEngine
    ) -> None:
        """Route explicitly passes archival_reason=None when not in body (AC5).

        Fails in RED: route omits archival_reason kwarg entirely, so
        'archival_reason' is not in call_args.kwargs.
        """
        from owlbear_kanban.models import SingleTaskResponse  # noqa: PLC0415

        client, view = mock_view_client
        task = engine.show_task("1")
        view.move_task.return_value = SingleTaskResponse(
            id=1,
            title="Alpha task",
            status="in-progress",
            priority="important",
            created=task.created,
            updated=task.updated,
        )

        resp = client.post(
            "/api/tasks/1/move",
            json={"status": "in-progress", "updated": task.updated},
        )
        assert resp.status_code == 200
        call_kwargs = view.move_task.call_args.kwargs
        # Fails in RED: key absent from kwargs (route doesn't forward archival params)
        assert "archival_reason" in call_kwargs
        assert call_kwargs["archival_reason"] is None

    def test_move_route_default_archival_refs_forwarded_as_empty_list(
        self, mock_view_client, engine: KanbanEngine
    ) -> None:
        """Route explicitly passes archival_refs=[] when not in body (AC5).

        Fails in RED: route omits archival_refs kwarg entirely, so
        'archival_refs' is not in call_args.kwargs.
        """
        from owlbear_kanban.models import SingleTaskResponse  # noqa: PLC0415

        client, view = mock_view_client
        task = engine.show_task("1")
        view.move_task.return_value = SingleTaskResponse(
            id=1,
            title="Alpha task",
            status="in-progress",
            priority="important",
            created=task.created,
            updated=task.updated,
        )

        resp = client.post(
            "/api/tasks/1/move",
            json={"status": "in-progress", "updated": task.updated},
        )
        assert resp.status_code == 200
        call_kwargs = view.move_task.call_args.kwargs
        # Fails in RED: key absent from kwargs (route doesn't forward archival params)
        assert "archival_refs" in call_kwargs
        assert call_kwargs["archival_refs"] == []
