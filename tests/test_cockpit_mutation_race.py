"""Cockpit mutation route OCC and response-shape regression tests.

Promoted from the task-scoped suite for task #1131.

These tests document CURRENT (broken) behavior in the cockpit mutation HTTP routes:
  - G1 (confirmed): Edit route precheck-only TOCTOU — engine CAS (expected_updated)
    never engaged.  The route compares req.updated against task.updated and raises 409
    on mismatch, but on match it calls engine.edit_task(**kwargs) WITHOUT forwarding
    expected_updated (mutation.py L~209).
  - G2 (RETRACTED): Move route DOES have OCC — MoveRequest carries updated: str and
    the route passes expected_updated=req.updated to engine.move_task (mutation.py
    L~108).  Original research incorrectly claimed move had no OCC.
  - G3 (confirmed, reframed): Release route guard uses task.claimed_by (Field
    exclude=True — never persisted, always None after disk round-trip).  The route's
    ``if not task.claimed_by`` guard fires even when claimed_at IS on disk, so the
    route always returns 409 on new-schema boards regardless of actual claim state.

Tests pass against current code without production changes.  Follow-up fix tasks
#1134 (edit CAS fix), #1133 (release engine CAS), #1132 (route wiring through CockpitView).

AC coverage:
  - AC1: engine.edit_task never receives expected_updated kwarg (gap G1)
  - AC2: engine.move_task does receive expected_updated kwarg matching req.updated
         (contrast — move has OCC, edit does not)
  - AC3: claiming a task via engine then releasing via cockpit HTTP always returns
         409 (gap G3 — claimed_by guard broken on new-schema boards)
  - AC4a: edit with stale updated → 409 "Task was modified since your last load
          (stale snapshot)"
  - AC4b: release on unclaimed task → 409 "Task {id} is not currently claimed"
    - AC5a: move 200 response has all 14 task-detail keys
    - AC5b: edit 200 response has all 14 task-detail keys
"""

from __future__ import annotations

from pathlib import Path
from unittest import mock

import pytest

from owlbear_kanban import KanbanEngine

# Provenance: promoted from task-scoped suite for task #1131.


# ---------------------------------------------------------------------------
# Board fixture helpers
# ---------------------------------------------------------------------------

_CONFIG_YAML = """\
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
    """Board with one task in build status.

    Task 1: status=build, priority=medium (unclaimed — target for all AC tests)
    """
    kanban_dir = _make_board(tmp_path)
    seed = KanbanEngine(kanban_dir)
    seed.create_task("Alpha task", status="build", priority="medium")
    seed.list_tasks()  # populate id→filename cache
    return kanban_dir


@pytest.fixture
def engine(board_dir: Path) -> KanbanEngine:
    """KanbanEngine bound to the test board."""
    eng = KanbanEngine(board_dir, activity_log=False)
    eng.list_tasks()  # populate id→filename cache
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


# Expected 13-key schema for task detail responses
_TASK_DETAIL_KEYS = frozenset(
    {
        "id",
        "title",
        "status",
        "priority",
        "body",
        "updated",
        "created",
        "tags",
        "blocked",
        "block_reason",
        "parent",
        "depends_on",
        "claimed",
    }
)


# ---------------------------------------------------------------------------
# AC1 / AC4 — Edit CAS engagement: engine.edit_task receives expected_updated
# ---------------------------------------------------------------------------


class TestFromAC_EditTOCTOU:
    """AC1 (updated for #1134 AC4): Edit route CAS engaged — expected_updated forwarded."""

    def test_edit_route_passes_expected_updated_to_engine(self, client, engine: KanbanEngine) -> None:
        """Wraps engine.edit_task to inspect kwargs; expected_updated must be present.

        Updated for #1134 AC4: inverts the original gap proof.  The route must now
        forward expected_updated=req.updated to engine.edit_task, engaging the
        engine's CAS mechanism (not just the route-level precheck).
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
        assert "expected_updated" in call_kwargs, (
            "Edit route must pass expected_updated to engine (AC1/#1134 — CAS engaged)"
        )


# ---------------------------------------------------------------------------
# AC2 — Move OCC contrast: engine.move_task DOES receive expected_updated
# ---------------------------------------------------------------------------


class TestFromAC_MoveOCCContrast:
    """AC2: Move route forwards OCC token — contrast with AC1's edit gap.

    Unlike the edit route, the move route (mutation.py L~84) passes
    expected_updated=req.updated to engine.move_task, engaging the engine's
    CAS.  This test proves the structural asymmetry between the two routes.
    """

    def test_move_route_passes_expected_updated_to_engine(self, client, engine: KanbanEngine) -> None:
        """Wraps engine.move_task; expected_updated must be present in call kwargs.

        Sends a valid move request using the task's current updated timestamp.
        Proves the route correctly forwards the OCC token to the engine.
        """
        task = engine.show_task("1")
        with mock.patch.object(engine, "move_task", wraps=engine.move_task) as mocked:
            response = client.post(
                "/api/tasks/1/move",
                json={"status": "verify", "updated": task.updated},
            )
        assert response.status_code == 200
        assert mocked.called, "engine.move_task must have been called"
        call_kwargs = mocked.call_args.kwargs
        assert "expected_updated" in call_kwargs, "Move route must forward expected_updated to engine (OCC engaged)"
        assert call_kwargs["expected_updated"] == task.updated, (
            "expected_updated must match the updated value sent in the request"
        )


# ---------------------------------------------------------------------------
# AC3 — Release guard broken on new-schema boards (gap G3)
# ---------------------------------------------------------------------------


class TestFromAC_ReleaseGuardBroken:
    """AC3: Release route behavior after CockpitView wiring (#1132)."""

    def test_release_returns_200_when_task_is_genuinely_claimed(self, client, engine: KanbanEngine) -> None:
        """Claim task 1 via engine (writes claimed_at to disk); release route → 200.

        No mocking: proves the live route behavior when claimed_at IS on disk.
        """
        engine.claim_task("1")
        claimed_task = engine.show_task("1")
        assert claimed_task.claimed_at is not None, (
            "Precondition: engine.claim_task must have written claimed_at to disk"
        )

        response = client.post(
            "/api/tasks/1/release",
            json={"updated": claimed_task.updated},
        )

        assert response.status_code == 200, "Release route must return 200 when task is genuinely claimed"


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
        body = response.json()
        assert "detail" not in body
        assert body.get("code") == "ERR_STALE"
        assert "changed since read" in body["message"]

    def test_release_unclaimed_task_exact_detail_string(self, client, engine: KanbanEngine) -> None:
        """Release on unclaimed task 1 → 409 with exact 'Task {id} is not currently claimed'."""
        task = engine.show_task("1")
        response = client.post("/api/tasks/1/release", json={"updated": task.updated})
        assert response.status_code == 409
        body = response.json()
        assert "detail" not in body
        assert "code" in body
        assert "not currently claimed" in str(body.get("message", "")).lower()


# ---------------------------------------------------------------------------
# AC5 — Schema baseline: all 13 task-detail keys present in 200 responses
# ---------------------------------------------------------------------------


class TestFromAC_SchemaBaseline:
    """AC5: All 13 task-detail keys present in move and edit 200 responses.

    No release 200 test — the release 200 path is unreachable on new-schema
    boards due to gap G3 (AC3 above).
    """

    def test_move_200_response_has_all_14_taskdetailout_keys(self, client, engine: KanbanEngine) -> None:
        """Move 200 response body contains all 13 task-detail keys."""
        task = engine.show_task("1")
        response = client.post(
            "/api/tasks/1/move",
            json={"status": "verify", "updated": task.updated},
        )
        assert response.status_code == 200
        missing = _TASK_DETAIL_KEYS - set(response.json().keys())
        assert not missing, f"Missing task-detail keys in move response: {missing}"

    def test_edit_200_response_has_all_14_taskdetailout_keys(self, client, engine: KanbanEngine) -> None:
        """Edit 200 response body contains all 13 task-detail keys."""
        task = engine.show_task("1")
        response = client.post(
            "/api/tasks/1/edit",
            json={"updated": task.updated, "title": "Schema baseline probe"},
        )
        assert response.status_code == 200
        missing = _TASK_DETAIL_KEYS - set(response.json().keys())
        assert not missing, f"Missing task-detail keys in edit response: {missing}"
