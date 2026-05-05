"""Failing tests for CockpitView archival validation 422 surfacing via the route (#1244).

RED phase — all tests must fail until the route allows 'archived' moves to reach the
CockpitView.move_task validation block and surface the archival ValidationErrors as
HTTP 422 responses with validation-specific detail messages.

Root cause of failure: the route's valid_transitions() check returns only configured
pipeline statuses (research … done) — 'archived' is not among them, so the route
returns 422 "Cannot move from '...' to 'archived'" before view.move_task() is ever
reached.  The builder must allow 'archived' past the transition check so the view
layer's validation block can run and its error messages can surface.

AC coverage:
  AC1:  POST /move no reason → 422 detail contains archival_reason context
  AC2:  reason="completed" + refs → 422 detail reflects refs-forbidden
  AC3:  reason="dropped"   + refs → 422 detail reflects refs-forbidden
  AC4:  reason="wontfix"   + refs → 422 detail reflects refs-forbidden
  AC5:  reason="deprecated" + empty refs → 422 detail reflects refs-required
  AC6:  reason="duplicate"  + empty refs → 422 detail reflects refs-required
  AC7:  reason="completed", task not at done → 422 detail reflects done-required
  AC8:  archival_refs contains non-existent ID → 422 detail contains missing-ref context
  AC9:  archival_refs contains task's own ID → 422 detail reflects self-reference
  AC10: archival_refs creates a cycle → 422 detail reflects cycle detection
  AC11: valid archived from done (completed, no refs) → 200 with status='archived'
  (AC12: all 11 tests from #1240 pass — regression guard; see test_cockpit_view_1240.py)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from owlbear_kanban import KanbanEngine


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
    """Board with two tasks: task 1 at 'done', task 2 at 'todo'."""
    kanban_dir = _make_board(tmp_path)
    seed = KanbanEngine(kanban_dir)
    seed.create_task("Done task", status="done", priority="important")
    seed.create_task("Todo task", status="todo", priority="important")
    return kanban_dir


@pytest.fixture
def engine(board_dir: Path) -> KanbanEngine:
    """KanbanEngine bound to the test board."""
    eng = KanbanEngine(board_dir)
    eng.list_tasks()
    return eng


@pytest.fixture
def client(engine: KanbanEngine):
    """FastAPI TestClient with real engine injected via dependency_overrides."""
    from fastapi.testclient import TestClient  # noqa: PLC0415
    from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415

    app.dependency_overrides[get_engine] = lambda: engine
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def _updated(engine: KanbanEngine, task_id: int) -> str:
    """Return the current 'updated' timestamp string for the given task."""
    return str(engine.show_task(str(task_id)).updated)


# ---------------------------------------------------------------------------
# TestFromAC_ArchivalValidation422Surfacing
# ---------------------------------------------------------------------------


class TestFromAC_ArchivalValidation422Surfacing:
    """Route surfaces CockpitView.move_task archival ValidationErrors as HTTP 422.

    Each test POSTs to POST /api/tasks/{id}/move with status='archived' and
    invalid archival combinations, then asserts the 422 detail contains content
    from the archival validation block — not from the generic transition check
    ("Cannot move from '...' to 'archived'").

    All tests currently FAIL because valid_transitions() never includes 'archived',
    so the transition check fires first and the view validation block is unreachable
    via the route.
    """

    # -- AC1: archival_reason required when status='archived' --

    def test_route_archive_without_reason_returns_422_with_archival_detail(
        self, client, engine: KanbanEngine
    ) -> None:
        """AC1: POST /move with status='archived' and no archival_reason returns
        a 422 whose detail message references archival_reason, not a generic
        transition rejection.

        Currently FAILS: route's valid_transitions() blocks 'archived', returning
        "Cannot move from 'done' to 'archived'" which does not mention archival_reason.
        """
        resp = client.post(
            "/api/tasks/1/move",
            json={"status": "archived", "updated": _updated(engine, 1)},
        )
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        # Validation block message: "archival_reason is required when status='archived'"
        assert "archival_reason" in detail

    # -- AC2-AC4: archival_refs forbidden for completed / dropped / wontfix --

    def test_route_archive_completed_with_refs_returns_422_with_forbidden_detail(
        self, client, engine: KanbanEngine
    ) -> None:
        """AC2: reason='completed' + non-empty refs → 422 detail shows refs-forbidden.

        Currently FAILS: route blocks 'archived' before view validation runs.
        """
        resp = client.post(
            "/api/tasks/1/move",
            json={
                "status": "archived",
                "updated": _updated(engine, 1),
                "archival_reason": "completed",
                "archival_refs": [2],
            },
        )
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        assert "archival_refs" in detail
        assert "forbidden" in detail.lower()

    def test_route_archive_dropped_with_refs_returns_422_with_forbidden_detail(
        self, client, engine: KanbanEngine
    ) -> None:
        """AC3: reason='dropped' + non-empty refs → 422 detail shows refs-forbidden.

        Currently FAILS: route blocks 'archived' before view validation runs.
        """
        resp = client.post(
            "/api/tasks/1/move",
            json={
                "status": "archived",
                "updated": _updated(engine, 1),
                "archival_reason": "dropped",
                "archival_refs": [2],
            },
        )
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        assert "archival_refs" in detail
        assert "forbidden" in detail.lower()

    def test_route_archive_wontfix_with_refs_returns_422_with_forbidden_detail(
        self, client, engine: KanbanEngine
    ) -> None:
        """AC4: reason='wontfix' + non-empty refs → 422 detail shows refs-forbidden.

        Currently FAILS: route blocks 'archived' before view validation runs.
        """
        resp = client.post(
            "/api/tasks/1/move",
            json={
                "status": "archived",
                "updated": _updated(engine, 1),
                "archival_reason": "wontfix",
                "archival_refs": [2],
            },
        )
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        assert "archival_refs" in detail
        assert "forbidden" in detail.lower()

    # -- AC5-AC6: archival_refs required for deprecated / duplicate --

    def test_route_archive_deprecated_without_refs_returns_422_with_required_detail(
        self, client, engine: KanbanEngine
    ) -> None:
        """AC5: reason='deprecated' + empty refs → 422 detail shows refs-required.

        Currently FAILS: route blocks 'archived' before view validation runs.
        """
        resp = client.post(
            "/api/tasks/1/move",
            json={
                "status": "archived",
                "updated": _updated(engine, 1),
                "archival_reason": "deprecated",
                "archival_refs": [],
            },
        )
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        assert "archival_refs" in detail
        assert "required" in detail.lower()

    def test_route_archive_duplicate_without_refs_returns_422_with_required_detail(
        self, client, engine: KanbanEngine
    ) -> None:
        """AC6: reason='duplicate' + empty refs → 422 detail shows refs-required.

        Currently FAILS: route blocks 'archived' before view validation runs.
        """
        resp = client.post(
            "/api/tasks/1/move",
            json={
                "status": "archived",
                "updated": _updated(engine, 1),
                "archival_reason": "duplicate",
                "archival_refs": [],
            },
        )
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        assert "archival_refs" in detail
        assert "required" in detail.lower()

    # -- AC7: completed requires task.status == 'done' --

    def test_route_archive_completed_from_non_done_returns_422_with_done_detail(
        self, client, engine: KanbanEngine
    ) -> None:
        """AC7: reason='completed' when task.status != 'done' → 422 detail shows
        done-required context.

        Task 2 is at 'todo'. Currently FAILS: route blocks 'archived' before the
        view can check the pre-move status; detail says "Cannot move from 'todo' to
        'archived'" which does not mention 'done' or 'terminal'.
        """
        resp = client.post(
            "/api/tasks/2/move",
            json={
                "status": "archived",
                "updated": _updated(engine, 2),
                "archival_reason": "completed",
                "archival_refs": [],
            },
        )
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        # Validation block message: "archival_reason='completed' requires terminal status"
        assert "terminal" in detail.lower() or "done" in detail.lower()

    # -- AC8: non-existent ref ID --

    def test_route_archive_with_nonexistent_ref_returns_422_with_ref_missing_detail(
        self, client, engine: KanbanEngine
    ) -> None:
        """AC8: archival_refs contains a non-existent task ID → 422 detail mentions
        the missing ref ID or 'not found'.

        Currently FAILS: route blocks 'archived'; detail is generic transition error.
        """
        resp = client.post(
            "/api/tasks/1/move",
            json={
                "status": "archived",
                "updated": _updated(engine, 1),
                "archival_reason": "deprecated",
                "archival_refs": [99999],
            },
        )
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        # Validation block message: "archival reference task '99999' not found"
        assert "99999" in detail or "not found" in detail.lower()

    # -- AC9: self-reference in archival_refs --

    def test_route_archive_with_self_ref_returns_422_with_self_ref_detail(
        self, client, engine: KanbanEngine
    ) -> None:
        """AC9: archival_refs contains the task's own ID → 422 detail reflects
        self-reference rejection.

        Currently FAILS: route blocks 'archived'; detail is generic transition error.
        """
        resp = client.post(
            "/api/tasks/1/move",
            json={
                "status": "archived",
                "updated": _updated(engine, 1),
                "archival_reason": "deprecated",
                "archival_refs": [1],
            },
        )
        assert resp.status_code == 422
        detail = resp.json()["detail"]
        # Validation block message: "archival_refs cannot include the task itself"
        assert "itself" in detail.lower() or "self" in detail.lower()

    # -- AC10: cyclic archival_refs --

    def test_route_archive_with_cyclic_refs_returns_422_with_cycle_detail(
        self, tmp_path: Path
    ) -> None:
        """AC10: archival_refs that create a cycle → 422 detail reflects cycle detection.

        Setup:
          - Task A (id=1, done): to be archived via route with refs=[B.id]
          - Task B (id=2, todo): archived directly via engine with refs=[A.id]

        B→A is already stored (archived directly). When archiving A→B via route, the
        cycle A→B→A is detected by CockpitView._has_archival_cycle.

        Currently FAILS: route blocks 'archived'; cycle check is never reached.
        """
        from fastapi.testclient import TestClient  # noqa: PLC0415
        from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415

        kanban_dir = _make_board(tmp_path)
        seed = KanbanEngine(kanban_dir)
        seed.create_task("Task A", status="done", priority="important")
        seed.create_task("Task B", status="todo", priority="important")

        eng = KanbanEngine(kanban_dir)
        eng.list_tasks()
        # Archive B directly via engine (bypassing view validation): B refs A.
        eng.move_task("2", "archived", archival_reason="deprecated", archival_refs=[1])

        app.dependency_overrides[get_engine] = lambda: eng
        try:
            tc = TestClient(app)
            updated_a = str(eng.show_task("1").updated)
            resp = tc.post(
                "/api/tasks/1/move",
                json={
                    "status": "archived",
                    "updated": updated_a,
                    "archival_reason": "deprecated",
                    "archival_refs": [2],
                },
            )
        finally:
            app.dependency_overrides.clear()

        assert resp.status_code == 422
        detail = resp.json()["detail"]
        # Validation block message: "archival_refs would introduce a cycle"
        assert "cycle" in detail.lower()

    # -- AC11 (happy path): valid archival from done → 200 --

    def test_route_valid_archive_from_done_returns_200_with_archived_status(
        self, client, engine: KanbanEngine
    ) -> None:
        """AC11: POST /move with status='archived', reason='completed', no refs,
        task at 'done' → HTTP 200 with status='archived' in the response.

        Currently FAILS: route blocks 'archived' via valid_transitions(), returning
        422 instead of 200.
        """
        resp = client.post(
            "/api/tasks/1/move",
            json={
                "status": "archived",
                "updated": _updated(engine, 1),
                "archival_reason": "completed",
                "archival_refs": [],
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "archived"
