"""Regression guards for MoveRequest archival fields and route pass-through (#1243).

Implementation was pre-completed during #1239's builder phase.  All tests here
are GREEN at time of writing.  They serve as task-scoped regression guards and
audit evidence for #1243's AC:

  AC1: MoveRequest has archival_reason: str | None = None field
  AC2: MoveRequest has archival_refs: list[int] = [] field
  AC3: extra="forbid" is preserved on MoveRequest
  AC4: Move route passes req.archival_reason and req.archival_refs to view.move_task()
  AC5: Existing move requests without archival fields are unaffected

NOTE: All tests in this file PASS against the current implementation.
The RED baseline was established by test_cockpit_mutation_api_1239.py (#1239),
which went RED before the builder implemented the feature.
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
    kanban_dir = _make_board(tmp_path)
    seed = KanbanEngine(kanban_dir, agent_name="seed")
    seed.create_task("Beta task", status="todo", priority="needed")
    seed.list_tasks()
    return kanban_dir


@pytest.fixture
def engine(board_dir: Path) -> KanbanEngine:
    eng = KanbanEngine(board_dir, agent_name="cockpit", activity_log=True)
    eng.list_tasks()
    return eng


@pytest.fixture
def mock_view_client(engine: KanbanEngine):
    """TestClient with mock CockpitView injected via get_view dependency."""
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
# AC1 — archival_reason field on MoveRequest
# ---------------------------------------------------------------------------


class TestFromAC_MoveRequestArchivalReason:
    """AC1: MoveRequest.archival_reason defaults to None."""

    def test_archival_reason_field_exists_on_moverequest(self) -> None:
        """MoveRequest has an archival_reason attribute (AC1)."""
        req = MoveRequest(status="in-progress", updated="2026-01-01T00:00:00+00:00")
        assert hasattr(req, "archival_reason")

    def test_archival_reason_defaults_to_none(self) -> None:
        """archival_reason default is None when not supplied (AC1)."""
        req = MoveRequest(status="in-progress", updated="2026-01-01T00:00:00+00:00")
        assert req.archival_reason is None

    def test_archival_reason_accepts_string_value(self) -> None:
        """archival_reason accepts a string value (AC1)."""
        req = MoveRequest(
            status="in-progress",
            updated="2026-01-01T00:00:00+00:00",
            archival_reason="deprecated",
        )
        assert req.archival_reason == "deprecated"

    def test_archival_reason_type_is_optional_str(self) -> None:
        """archival_reason accepts None explicitly, confirming str | None type (AC1)."""
        req = MoveRequest(
            status="in-progress",
            updated="2026-01-01T00:00:00+00:00",
            archival_reason=None,
        )
        assert req.archival_reason is None


# ---------------------------------------------------------------------------
# AC2 — archival_refs field on MoveRequest
# ---------------------------------------------------------------------------


class TestFromAC_MoveRequestArchivalRefs:
    """AC2: MoveRequest.archival_refs defaults to []."""

    def test_archival_refs_field_exists_on_moverequest(self) -> None:
        """MoveRequest has an archival_refs attribute (AC2)."""
        req = MoveRequest(status="in-progress", updated="2026-01-01T00:00:00+00:00")
        assert hasattr(req, "archival_refs")

    def test_archival_refs_defaults_to_empty_list(self) -> None:
        """archival_refs default is [] when not supplied (AC2)."""
        req = MoveRequest(status="in-progress", updated="2026-01-01T00:00:00+00:00")
        assert req.archival_refs == []

    def test_archival_refs_default_is_list_type(self) -> None:
        """archival_refs default value is a list instance (AC2)."""
        req = MoveRequest(status="in-progress", updated="2026-01-01T00:00:00+00:00")
        assert isinstance(req.archival_refs, list)

    def test_archival_refs_accepts_list_of_ints(self) -> None:
        """archival_refs accepts a list of integer task IDs (AC2)."""
        req = MoveRequest(
            status="in-progress",
            updated="2026-01-01T00:00:00+00:00",
            archival_refs=[10, 20, 30],
        )
        assert req.archival_refs == [10, 20, 30]

    def test_archival_refs_mutable_default_is_safe(self) -> None:
        """Two MoveRequest instances share no archival_refs state (AC2 — safe default)."""
        req_a = MoveRequest(status="in-progress", updated="2026-01-01T00:00:00+00:00")
        req_b = MoveRequest(status="in-progress", updated="2026-01-01T00:00:00+00:00")
        # Mutating one must not affect the other (Field(default_factory=list) safety)
        req_a.archival_refs.append(99)
        assert req_b.archival_refs == []


# ---------------------------------------------------------------------------
# AC3 — extra="forbid" preserved
# ---------------------------------------------------------------------------


class TestFromAC_ExtraForbidPreserved:
    """AC3: extra='forbid' is preserved after archival fields are added."""

    def test_unknown_field_still_raises_validation_error(self) -> None:
        """Unknown field after archival extension still raises ValidationError (AC3)."""
        with pytest.raises(pydantic.ValidationError):
            MoveRequest(
                status="in-progress",
                updated="2026-01-01T00:00:00+00:00",
                archival_reason="completed",
                not_a_known_field="should-fail",
            )

    def test_archival_fields_themselves_are_not_extra(self) -> None:
        """archival_reason and archival_refs are declared, not extra (AC3).

        If extra='forbid' were applied to the archival fields themselves, this
        would raise.  It must not raise.
        """
        req = MoveRequest(
            status="in-progress",
            updated="2026-01-01T00:00:00+00:00",
            archival_reason="completed",
            archival_refs=[1, 2],
        )
        assert req.archival_reason == "completed"
        assert req.archival_refs == [1, 2]


# ---------------------------------------------------------------------------
# AC4 — Route passes archival kwargs to view.move_task()
# ---------------------------------------------------------------------------


class TestFromAC_RouteArchivalPassThrough:
    """AC4: Move route passes req.archival_reason and req.archival_refs to view.move_task()."""

    def test_route_passes_archival_reason_kwarg(
        self, mock_view_client, engine: KanbanEngine
    ) -> None:
        """Route forwards archival_reason= kwarg to view.move_task() (AC4)."""
        from owlbear_kanban.models import SingleTaskResponse  # noqa: PLC0415

        client, view = mock_view_client
        task = engine.show_task("1")
        view.move_task.return_value = SingleTaskResponse(
            id=1,
            title="Beta task",
            status="in-progress",
            priority="needed",
            created=task.created,
            updated=task.updated,
        )

        resp = client.post(
            "/api/tasks/1/move",
            json={
                "status": "in-progress",
                "updated": task.updated,
                "archival_reason": "wontfix",
            },
        )
        assert resp.status_code == 200
        kwargs = view.move_task.call_args.kwargs
        assert "archival_reason" in kwargs
        assert kwargs["archival_reason"] == "wontfix"

    def test_route_passes_archival_refs_kwarg(
        self, mock_view_client, engine: KanbanEngine
    ) -> None:
        """Route forwards archival_refs= kwarg to view.move_task() (AC4)."""
        from owlbear_kanban.models import SingleTaskResponse  # noqa: PLC0415

        client, view = mock_view_client
        task = engine.show_task("1")
        view.move_task.return_value = SingleTaskResponse(
            id=1,
            title="Beta task",
            status="in-progress",
            priority="needed",
            created=task.created,
            updated=task.updated,
        )

        resp = client.post(
            "/api/tasks/1/move",
            json={
                "status": "in-progress",
                "updated": task.updated,
                "archival_refs": [3, 7],
            },
        )
        assert resp.status_code == 200
        kwargs = view.move_task.call_args.kwargs
        assert "archival_refs" in kwargs
        assert kwargs["archival_refs"] == [3, 7]

    def test_route_passes_both_archival_kwargs_simultaneously(
        self, mock_view_client, engine: KanbanEngine
    ) -> None:
        """Route forwards both archival_reason AND archival_refs together (AC4)."""
        from owlbear_kanban.models import SingleTaskResponse  # noqa: PLC0415

        client, view = mock_view_client
        task = engine.show_task("1")
        view.move_task.return_value = SingleTaskResponse(
            id=1,
            title="Beta task",
            status="in-progress",
            priority="needed",
            created=task.created,
            updated=task.updated,
        )

        resp = client.post(
            "/api/tasks/1/move",
            json={
                "status": "in-progress",
                "updated": task.updated,
                "archival_reason": "duplicate",
                "archival_refs": [5, 8],
            },
        )
        assert resp.status_code == 200
        kwargs = view.move_task.call_args.kwargs
        assert kwargs.get("archival_reason") == "duplicate"
        assert kwargs.get("archival_refs") == [5, 8]


# ---------------------------------------------------------------------------
# AC5 — Backwards-compatibility: existing move requests unaffected
# ---------------------------------------------------------------------------


class TestFromAC_BackwardsCompatibility:
    """AC5: Existing move requests without archival fields are unaffected."""

    def test_plain_move_request_is_still_valid(self) -> None:
        """MoveRequest with only status+updated deserialises without error (AC5)."""
        req = MoveRequest(status="review", updated="2026-01-01T00:00:00+00:00")
        assert req.status == "review"
        assert req.updated == "2026-01-01T00:00:00+00:00"

    def test_plain_move_request_defaults_archival_reason_to_none(self) -> None:
        """Plain MoveRequest gets archival_reason=None default (AC5)."""
        req = MoveRequest(status="review", updated="2026-01-01T00:00:00+00:00")
        assert req.archival_reason is None

    def test_plain_move_request_defaults_archival_refs_to_empty_list(self) -> None:
        """Plain MoveRequest gets archival_refs=[] default (AC5)."""
        req = MoveRequest(status="review", updated="2026-01-01T00:00:00+00:00")
        assert req.archival_refs == []

    def test_route_with_no_archival_fields_still_returns_200(
        self, mock_view_client, engine: KanbanEngine
    ) -> None:
        """Plain move POST (no archival fields) returns 200 unchanged (AC5)."""
        from owlbear_kanban.models import SingleTaskResponse  # noqa: PLC0415

        client, view = mock_view_client
        task = engine.show_task("1")
        view.move_task.return_value = SingleTaskResponse(
            id=1,
            title="Beta task",
            status="in-progress",
            priority="needed",
            created=task.created,
            updated=task.updated,
        )

        resp = client.post(
            "/api/tasks/1/move",
            json={"status": "in-progress", "updated": task.updated},
        )
        assert resp.status_code == 200

    def test_route_with_no_archival_fields_passes_none_and_empty_list(
        self, mock_view_client, engine: KanbanEngine
    ) -> None:
        """Plain move POST forwards archival_reason=None, archival_refs=[] (AC5)."""
        from owlbear_kanban.models import SingleTaskResponse  # noqa: PLC0415

        client, view = mock_view_client
        task = engine.show_task("1")
        view.move_task.return_value = SingleTaskResponse(
            id=1,
            title="Beta task",
            status="in-progress",
            priority="needed",
            created=task.created,
            updated=task.updated,
        )

        resp = client.post(
            "/api/tasks/1/move",
            json={"status": "in-progress", "updated": task.updated},
        )
        assert resp.status_code == 200
        kwargs = view.move_task.call_args.kwargs
        assert kwargs.get("archival_reason") is None
        assert kwargs.get("archival_refs") == []
