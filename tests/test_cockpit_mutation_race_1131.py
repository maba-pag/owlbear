"""GREEN characterization tests for cockpit mutation race conditions and OCC gaps (#1131).

These tests document CURRENT behavior (OCC gaps) in the cockpit mutation routes:
  - G1: Edit route precheck-only TOCTOU — engine CAS (expected_updated) never engaged
  - G2: Move route has no OCC token — succeeds regardless of concurrent edits
  - G3: Release route actor-agnostic — clears any claim regardless of owner identity
  - AC4: Exact 409 detail strings for stale edit and unclaimed release
  - AC5: All 14 TaskDetailOut keys present in 200 responses

Tests pass against current code. Follow-up tasks #1134, #1135, #1136 address fixes.

AC coverage:
  - AC1: engine.edit_task never receives expected_updated kwarg
  - AC2: move succeeds despite concurrent engine edit bumping updated
  - AC3: cockpit release clears claim held by a foreign engine instance
  - AC4a: edit stale → exact detail "Task was modified since your last load (stale snapshot)"
  - AC4b: release unclaimed → exact detail "Task {id} is not currently claimed"
  - AC5a: move 200 response has all 14 TaskDetailOut keys
  - AC5b: edit 200 response has all 14 TaskDetailOut keys
  - AC5c: release 200 response has all 14 TaskDetailOut keys
"""

from __future__ import annotations

from pathlib import Path
from unittest import mock

import pytest

from owlbear_kanban import KanbanEngine


# ---------------------------------------------------------------------------
# Board fixture helpers (same pattern as test_cockpit_mutation_api.py)
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
    """Board with 3 tasks. Task 2 is pre-claimed by 'seed' for release tests.

    Task 1: status=todo,        priority=important  (unclaimed)
    Task 2: status=in-progress, priority=needed     (claimed)
    Task 3: status=todo,        priority=someday    (unclaimed)
    """
    kanban_dir = _make_board(tmp_path)
    seed = KanbanEngine(kanban_dir)
    seed.create_task("Alpha task", status="todo", priority="important")
    seed.create_task("Beta task", status="in-progress", priority="needed")
    seed.create_task("Gamma task", status="todo", priority="someday")
    seed.list_tasks()  # populate id→filename cache
    seed.claim_task("2")
    return kanban_dir


@pytest.fixture
def engine(board_dir: Path) -> KanbanEngine:
    """KanbanEngine with activity logging enabled (agent_name auto-assigned)."""
    eng = KanbanEngine(board_dir, activity_log=True)
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


# Expected 14-key schema for TaskDetailOut
_TASK_DETAIL_KEYS = frozenset({
    "id", "title", "status", "priority", "body",
    "updated", "created", "tags", "blocked", "block_reason",
    "parent", "depends_on", "claimed", "claimed_by",
})


# ---------------------------------------------------------------------------
# AC1 — Edit TOCTOU: engine.edit_task never receives expected_updated
# ---------------------------------------------------------------------------


class TestFromAC_EditTOCTOU:
    """AC1: Edit route precheck-only TOCTOU — engine CAS never engaged (gap G1)."""

    def test_edit_route_does_not_pass_expected_updated_to_engine(
        self, client, engine: KanbanEngine
    ) -> None:
        """Wraps engine.edit_task to inspect kwargs; expected_updated must be absent.

        Proves the route performs only a precheck (req.updated != str(task.updated))
        and never forwards expected_updated to the engine's CAS mechanism.
        """
        task = engine.show_task("1")
        with mock.patch.object(engine, "edit_task", wraps=engine.edit_task) as mocked:
            response = client.post(
                "/api/tasks/1/edit",
                json={"updated": task.updated, "title": "G1 probe title"},
            )
        assert response.status_code == 200
        assert mocked.called, "engine.edit_task must have been called"
        call_kwargs = mocked.call_args.kwargs
        assert "expected_updated" not in call_kwargs, (
            "Edit route must not pass expected_updated to engine (gap G1 — precheck only)"
        )


# ---------------------------------------------------------------------------
# AC2 — Move no-OCC: move succeeds despite concurrent engine edit
# ---------------------------------------------------------------------------


class TestFromAC_MoveNoOCC:
    """AC2: Move route has no OCC token — succeeds regardless of concurrent edits (gap G2)."""

    def test_move_succeeds_after_concurrent_edit_bumps_updated(
        self, client, engine: KanbanEngine
    ) -> None:
        """Engine mutates task (bumps updated) before HTTP move; move still returns 200.

        Proves MoveRequest has no 'updated' field — the move path cannot detect
        that the task was modified between the client's snapshot and the request.
        """
        # Simulate concurrent edit that bumps task.updated
        engine.edit_task("1", title="Concurrent edit — bumps updated timestamp")
        # Move via cockpit HTTP — no OCC check means this must succeed
        response = client.post("/api/tasks/1/move", json={"status": "in-progress"})
        assert response.status_code == 200, (
            "Move route must succeed regardless of concurrent engine edit (gap G2)"
        )


# ---------------------------------------------------------------------------
# AC3 — Release actor-agnostic: cockpit clears any active claim
# ---------------------------------------------------------------------------


class TestFromAC_ReleaseActorAgnostic:
    """AC3: Release route actor-agnostic — clears any active claim regardless of owner (gap G3).

    NOTE: The cockpit release route checks ``task.claimed_by`` to detect a claim.
    Due to AC-C13, ``claimed_by`` is never written to disk; it is an in-memory alias
    only.  To set up the precondition (a claimed task visible to the route's guard),
    this test patches ``engine.show_task`` to inject ``claimed_by`` into the returned
    Task.  The underlying ``engine.release_task`` reads ``claimed_at`` from disk, which
    IS set by ``engine.claim_task``, so the release proceeds correctly.  The mock proves
    that once the guard sees a claim, the route does NOT verify ownership — any caller
    can release any active claim (gap G3).
    """

    def test_release_clears_foreign_claimed_by_without_ownership_check(
        self, client, engine: KanbanEngine
    ) -> None:
        """Inject claimed_by='foreign-agent' via mock; cockpit releases without verifying owner.

        Proves the route's guard (``if not task.claimed_by``) passes when claimed_by is
        set, and the route then calls engine.release_task WITHOUT any ownership check.
        The task is first claimed via engine so that ``claimed_at`` is on disk (enabling
        the real engine.release_task to clear the claim).
        """
        # Set up: claim task 1 so claimed_at is on disk
        engine.claim_task("1")

        # Inject claimed_by via mock — simulates a foreign-agent claim visible to the route
        _real_show = engine.show_task

        def _show_with_claimed_by(task_id: str) -> object:
            task = _real_show(task_id)
            task.claimed_by = "foreign-agent"  # in-memory only; prove route ignores identity
            return task

        with mock.patch.object(engine, "show_task", side_effect=_show_with_claimed_by):
            response = client.post("/api/tasks/1/release")

        assert response.status_code == 200, (
            "Release route must succeed without verifying claimed_by identity (gap G3)"
        )
        body = response.json()
        assert body.get("claimed_by") is None, (
            "claimed_by must be absent/null in response after release"
        )


# ---------------------------------------------------------------------------
# AC4 — 409 detail strings: exact messages for stale edit and unclaimed release
# ---------------------------------------------------------------------------


class TestFromAC_409DetailStrings:
    """AC4: Exact 409 detail strings — complement existing status-code-only tests."""

    def test_edit_stale_snapshot_exact_detail_string(self, client) -> None:
        """Stale 'updated' in edit request → 409 with exact detail string."""
        response = client.post(
            "/api/tasks/1/edit",
            json={"updated": "1970-01-01T00:00:00", "title": "Stale probe"},
        )
        assert response.status_code == 409
        assert response.json()["detail"] == (
            "Task was modified since your last load (stale snapshot)"
        )

    def test_release_unclaimed_task_exact_detail_string(self, client) -> None:
        """Release on unclaimed task 1 → 409 with exact 'Task {id} is not currently claimed'."""
        # Task 1 is unclaimed in the fixture
        response = client.post("/api/tasks/1/release")
        assert response.status_code == 409
        assert response.json()["detail"] == "Task 1 is not currently claimed"


# ---------------------------------------------------------------------------
# AC5 — Schema baseline: all 14 TaskDetailOut keys present in 200 responses
# ---------------------------------------------------------------------------


class TestFromAC_SchemaBaseline:
    """AC5: All 14 TaskDetailOut keys present in 200 responses for race-path routes."""

    def test_move_response_has_all_14_taskdetailout_keys(self, client) -> None:
        """Move 200 response contains all 14 TaskDetailOut keys."""
        response = client.post("/api/tasks/1/move", json={"status": "in-progress"})
        assert response.status_code == 200
        body = response.json()
        missing = _TASK_DETAIL_KEYS - set(body.keys())
        assert not missing, f"Missing TaskDetailOut keys in move response: {missing}"

    def test_edit_response_has_all_14_taskdetailout_keys(
        self, client, engine: KanbanEngine
    ) -> None:
        """Edit 200 response contains all 14 TaskDetailOut keys."""
        task = engine.show_task("1")
        response = client.post(
            "/api/tasks/1/edit",
            json={"updated": task.updated, "title": "Schema baseline probe"},
        )
        assert response.status_code == 200
        body = response.json()
        missing = _TASK_DETAIL_KEYS - set(body.keys())
        assert not missing, f"Missing TaskDetailOut keys in edit response: {missing}"

    def test_release_response_has_all_14_taskdetailout_keys(
        self, client, engine: KanbanEngine
    ) -> None:
        """Release 200 response contains all 14 TaskDetailOut keys (task 2, pre-claimed).

        Task 2 has ``claimed_at`` on disk (seed.claim_task in board_dir fixture).
        show_task is patched to inject ``claimed_by`` so the route's guard passes.
        The real engine.release_task then reads claimed_at from disk and clears it.
        """
        _real_show = engine.show_task

        def _show_with_claimed_by(task_id: str) -> object:
            task = _real_show(task_id)
            task.claimed_by = "seed"
            return task

        with mock.patch.object(engine, "show_task", side_effect=_show_with_claimed_by):
            response = client.post("/api/tasks/2/release")

        assert response.status_code == 200
        body = response.json()
        missing = _TASK_DETAIL_KEYS - set(body.keys())
        assert not missing, f"Missing TaskDetailOut keys in release response: {missing}"
