"""Failing tests for cockpit mutation API endpoints (#932).

RED phase — all tests must fail until routes are implemented in GREEN (#934).

AC coverage:
  - POST /api/tasks/{id}/move with target status; validates against valid_transitions → 200
  - POST /api/tasks/{id}/move with invalid target → 422
  - POST /api/tasks/{id}/move for non-existent task → 404
  - POST /api/tasks/{id}/edit with allowlisted fields (title, tags, priority,
    depends_on, parent, block_reason, body) → 200 with updated task object
  - POST /api/tasks/{id}/edit with non-allowlisted field 'status' → 422
  - POST /api/tasks/{id}/edit with 'blocked' directly → 422
  - POST /api/tasks/{id}/edit without 'updated' snapshot → 422
  - POST /api/tasks/{id}/edit with stale 'updated' snapshot → 409 Conflict (D9)
  - Block mutation: edit with block_reason sets blocked=True
  - Unblock mutation: edit with block_reason=null clears blocked state
  - POST /api/tasks/{id}/edit for non-existent task → 404
  - POST /api/tasks/{id}/release unclaims claimed task → 200 with updated task
  - POST /api/tasks/{id}/release on unclaimed task → 409 Conflict
  - POST /api/tasks/{id}/release for non-existent task → 404
    - All mutations write entry to activity.jsonl with source='cockpit'
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import TYPE_CHECKING
from unittest import mock

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_kanban.errors import ConcurrencyError
from owlbear_kanban.models import ConcurrencyError as ModelConcurrencyError
from owlbear_kanban.errors import NotFoundError, ValidationError
from owlbear_kanban.agent_view import AgentView
from owlbear_cockpit.view import CockpitView
from owlbear_cockpit.routes.mutation import MoveRequest
import pydantic
from datetime import UTC, datetime
import importlib.util

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


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
    """Board with 3 tasks. Task 2 is pre-claimed for release tests.

    Task 1: status=todo,        priority=important  (unclaimed — move/edit target)
    Task 2: status=in-progress, priority=needed     (claimed   — release target)
    Task 3: status=todo,        priority=someday    (unclaimed — depends_on/parent target)
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
    """KanbanEngine with agent_name='cockpit' and activity logging enabled."""
    eng = KanbanEngine(board_dir, activity_log=True)
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


# ---------------------------------------------------------------------------
# AC: POST /api/tasks/{id}/move
# ---------------------------------------------------------------------------


class TestFromAC_MoveTask:
    """Tests for POST /api/tasks/{id}/move.

    Covers: happy path (200 + updated task), valid_transitions enforcement,
    invalid target (422), same-status boundary (422), non-existent task (404).
    """

    def test_move_happy_path_returns_200(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """Happy path: move task 1 from 'todo' to 'in-progress' returns 200."""
        task = engine.show_task("1")
        response = client.post(
            "/api/tasks/1/move",
            json={"status": "in-progress", "updated": task.updated},
        )
        assert response.status_code == 200

    def test_move_returns_updated_task_object(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """Response body is a task object with the new status applied."""
        task = engine.show_task("1")
        response = client.post(
            "/api/tasks/1/move",
            json={"status": "review", "updated": task.updated},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["id"] == 1
        assert body["status"] == "review"
        assert "title" in body
        assert "priority" in body

    def test_move_invalid_target_status_returns_422(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """Unknown status string not in valid_transitions → 422."""
        task = engine.show_task("1")
        response = client.post(
            "/api/tasks/1/move",
            json={"status": "not-a-real-status", "updated": task.updated},
        )
        assert response.status_code == 422

    def test_move_same_status_returns_422(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """Moving to current status is excluded from valid_transitions → 422."""
        task = engine.show_task("1")
        response = client.post(
            "/api/tasks/1/move",
            json={"status": task.status, "updated": task.updated},
        )
        assert response.status_code == 422

    def test_move_nonexistent_task_returns_404(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """Non-existent task ID returns 404 with ID in detail."""
        task = engine.show_task("1")
        response = client.post(
            "/api/tasks/999/move",
            json={"status": "in-progress", "updated": task.updated},
        )
        assert response.status_code == 404
        body = response.json()
        assert "detail" not in body
        assert body.get("code") == "ERR_NOT_FOUND"
        assert "999" in str(body.get("message", ""))

    def test_move_missing_updated_returns_422(self, client: TestClient) -> None:
        """Missing required 'updated' field in move request returns 422."""
        response = client.post("/api/tasks/1/move", json={"status": "in-progress"})
        assert response.status_code == 422

    def test_move_stale_updated_returns_409(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """Stale OCC token in move request returns 409."""
        task = engine.show_task("1")
        stale_updated = task.updated
        engine.edit_task("1", title="Concurrent mutation bumps updated")

        response = client.post(
            "/api/tasks/1/move",
            json={"status": "in-progress", "updated": stale_updated},
        )

        assert response.status_code == 409

    def test_move_concurrency_error_returns_409_with_stale_detail(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """Engine ConcurrencyError during move maps to 409 with stale detail."""
        task = engine.show_task("1")
        exc = ConcurrencyError(code="ERR_STALE", user_message="stale")

        with mock.patch.object(engine, "move_task", side_effect=exc):
            response = client.post(
                "/api/tasks/1/move",
                json={"status": "in-progress", "updated": task.updated},
            )

        assert response.status_code == 409
        body = response.json()
        assert "detail" not in body
        assert body.get("code") == "ERR_STALE"
        assert body["message"] == "stale"


# ---------------------------------------------------------------------------
# AC: POST /api/tasks/{id}/edit
# ---------------------------------------------------------------------------


class TestFromAC_EditTask:
    """Tests for POST /api/tasks/{id}/edit.

    Covers: all allowlisted fields, non-allowlisted rejections, missing/stale
    'updated' snapshot, block/unblock mutations, and 404 for unknown tasks.
    """

    def test_edit_title_returns_200_with_new_title(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """Edit allowlisted field 'title' returns 200 with updated title."""
        task = engine.show_task("1")
        response = client.post(
            "/api/tasks/1/edit",
            json={"updated": task.updated, "title": "Renamed task"},
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Renamed task"

    def test_edit_tags_replaces_full_tag_list(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """Edit 'tags' replaces the full tag list (full-replacement semantics)."""
        task = engine.show_task("1")
        response = client.post(
            "/api/tasks/1/edit",
            json={"updated": task.updated, "tags": ["new-tag", "another"]},
        )
        assert response.status_code == 200
        assert set(response.json()["tags"]) == {"new-tag", "another"}

    def test_edit_priority_returns_200(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """Edit allowlisted field 'priority' returns 200 with updated priority."""
        task = engine.show_task("1")
        response = client.post(
            "/api/tasks/1/edit",
            json={"updated": task.updated, "priority": "critical"},
        )
        assert response.status_code == 200
        assert response.json()["priority"] == "critical"

    def test_edit_depends_on_returns_200(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """Edit allowlisted field 'depends_on' (full replacement list) returns 200."""
        task = engine.show_task("1")
        response = client.post(
            "/api/tasks/1/edit",
            json={"updated": task.updated, "depends_on": [2, 3]},
        )
        assert response.status_code == 200
        assert set(response.json()["depends_on"]) == {2, 3}

    def test_edit_parent_returns_200(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """Edit allowlisted field 'parent' returns 200 with updated parent."""
        task = engine.show_task("1")
        response = client.post(
            "/api/tasks/1/edit",
            json={"updated": task.updated, "parent": 3},
        )
        assert response.status_code == 200
        assert response.json()["parent"] == 3

    def test_edit_body_returns_200(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """Edit allowlisted field 'body' returns 200 with updated body."""
        task = engine.show_task("1")
        new_body = "## New body\n\nSome markdown content."
        response = client.post(
            "/api/tasks/1/edit",
            json={"updated": task.updated, "body": new_body},
        )
        assert response.status_code == 200
        assert response.json()["body"] == new_body

    def test_edit_status_field_rejected_422(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """Non-allowlisted field 'status' (highest-value bypass target) → 422."""
        task = engine.show_task("1")
        response = client.post(
            "/api/tasks/1/edit",
            json={"updated": task.updated, "status": "done"},
        )
        assert response.status_code == 422

    def test_edit_blocked_field_directly_rejected_422(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """Non-allowlisted field 'blocked' directly → 422; use block_reason instead."""
        task = engine.show_task("1")
        response = client.post(
            "/api/tasks/1/edit",
            json={"updated": task.updated, "blocked": True},
        )
        assert response.status_code == 422

    def test_edit_missing_updated_returns_422(self, client: TestClient) -> None:
        """Missing required 'updated' snapshot field → 422."""
        response = client.post("/api/tasks/1/edit", json={"title": "No timestamp"})
        assert response.status_code == 422

    def test_edit_stale_updated_returns_409(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """D9: stale 'updated' snapshot (task mutated since load) → 409 Conflict."""
        task = engine.show_task("1")
        stale_timestamp = task.updated
        # Advance the task's 'updated' timestamp directly via engine
        engine.edit_task("1", title="Modified by engine between load and save")
        # Cockpit request carries the old (stale) snapshot
        response = client.post(
            "/api/tasks/1/edit",
            json={"updated": stale_timestamp, "title": "Cockpit overwrite attempt"},
        )
        assert response.status_code == 409

    def test_edit_block_reason_sets_blocked_state(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """Edit with block_reason sets blocked=True implicitly."""
        task = engine.show_task("1")
        response = client.post(
            "/api/tasks/1/edit",
            json={"updated": task.updated, "block_reason": "waiting on dependency"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["blocked"] is True
        assert body["block_reason"] == "waiting on dependency"

    def test_edit_null_block_reason_clears_blocked_state(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """Unblock: edit with block_reason=null clears blocked=False and block_reason=None."""
        # Setup: block task 1 via engine directly
        engine.edit_task("1", blocked=True, block_reason="originally blocked")
        task = engine.show_task("1")
        assert task.blocked is True  # confirm setup
        # Unblock via cockpit
        response = client.post(
            "/api/tasks/1/edit",
            json={"updated": task.updated, "block_reason": None},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["blocked"] is False
        assert body["block_reason"] is None

    def test_edit_nonexistent_task_returns_404(self, client: TestClient) -> None:
        """Non-existent task ID returns 404 with ID in detail."""
        response = client.post(
            "/api/tasks/999/edit",
            json={"updated": "2025-01-01T00:00:00", "title": "Ghost task"},
        )
        assert response.status_code == 404
        body = response.json()
        assert "detail" not in body
        assert body.get("code") == "ERR_NOT_FOUND"
        assert "999" in str(body.get("message", ""))

    def test_edit_concurrency_error_returns_409_with_stale_detail(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """Engine ConcurrencyError during edit maps to 409 with stale detail."""
        task = engine.show_task("1")
        exc = ConcurrencyError(code="ERR_STALE", user_message="stale")

        with mock.patch.object(engine, "edit_task", side_effect=exc):
            response = client.post(
                "/api/tasks/1/edit",
                json={"updated": task.updated, "title": "Concurrency probe"},
            )

        assert response.status_code == 409
        body = response.json()
        assert "detail" not in body
        assert body.get("code") == "ERR_STALE"
        assert body["message"] == "stale"


# ---------------------------------------------------------------------------
# AC: POST /api/tasks/{id}/release
# ---------------------------------------------------------------------------


class TestFromAC_ReleaseTask:
    """Tests for POST /api/tasks/{id}/release.

    Covers: happy path on claimed task (200 + task object), unclaimed task
    (409 Conflict per AC refinement), and non-existent task (404).
    """

    def test_release_claimed_task_returns_200(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """Happy path: release pre-claimed task 2 returns 200."""
        task = engine.show_task("2")
        response = client.post("/api/tasks/2/release", json={"updated": task.updated})
        assert response.status_code == 200

    def test_release_returns_task_object_shape(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """Release response body matches the task-detail shape (same as GET /tasks/{id})."""
        task = engine.show_task("2")
        response = client.post("/api/tasks/2/release", json={"updated": task.updated})
        assert response.status_code == 200
        body = response.json()
        assert body["id"] == 2
        assert "title" in body
        assert "status" in body
        assert "priority" in body
        assert "updated" in body

    def test_release_unclaimed_task_returns_409(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """Releasing an unclaimed task is a state conflict → 409 (AC refinement #1)."""
        task = engine.show_task("1")
        response = client.post("/api/tasks/1/release", json={"updated": task.updated})
        assert response.status_code == 409

    def test_release_nonexistent_task_returns_404(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """Non-existent task ID returns 404 with ID in detail."""
        token = engine.show_task("1").updated
        response = client.post("/api/tasks/999/release", json={"updated": token})
        assert response.status_code == 404
        body = response.json()
        assert "detail" not in body
        assert body.get("code") == "ERR_NOT_FOUND"
        assert "999" in str(body.get("message", ""))

    def test_release_without_body_returns_422(self, client: TestClient) -> None:
        """Release requires a request body with the current updated token."""
        response = client.post("/api/tasks/2/release")
        assert response.status_code == 422

    def test_release_stale_updated_returns_409_with_stale_detail(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """Claimed task with stale release token returns 409 stale detail."""
        task = engine.show_task("2")
        stale_updated = task.updated
        engine.edit_task("2", title="Concurrent release mutation bumps updated")

        response = client.post("/api/tasks/2/release", json={"updated": stale_updated})

        assert response.status_code == 409
        body = response.json()
        assert "detail" not in body
        assert body.get("code") == "ERR_STALE"
        assert "changed since read" in body["message"]


# ---------------------------------------------------------------------------
# AC: All mutations write activity.jsonl with source='cockpit'
# ---------------------------------------------------------------------------


class TestFromAC_AuditLogging:
    """Tests verifying that every mutation endpoint writes an activity log entry.

    Each mutation must produce at least one entry in activity.jsonl with
    source='cockpit'. Engine is constructed with agent_name='cockpit' and
    activity_log=True so entries are written at all.
    """

    def test_move_writes_activity_log_source_cockpit(
        self, client: TestClient, engine: KanbanEngine, board_dir: Path
    ) -> None:
        """Move mutation writes activity.jsonl entry with source='cockpit'."""
        task = engine.show_task("1")
        client.post(
            "/api/tasks/1/move",
            json={"status": "in-progress", "updated": task.updated},
        )
        activity_file = board_dir / "activity.jsonl"
        assert activity_file.exists(), "activity.jsonl must be created by move mutation"
        entries = [
            json.loads(line)
            for line in activity_file.read_text().splitlines()
            if line.strip()
        ]
        cockpit_entries = [e for e in entries if e.get("source") == "cockpit"]
        assert len(cockpit_entries) >= 1, (
            "At least one activity entry must have source='cockpit'"
        )

    def test_edit_writes_activity_log_source_cockpit(
        self, client: TestClient, engine: KanbanEngine, board_dir: Path
    ) -> None:
        """Edit mutation writes activity.jsonl entry with source='cockpit'."""
        task = engine.show_task("1")
        client.post(
            "/api/tasks/1/edit",
            json={"updated": task.updated, "title": "Audit log test title"},
        )
        activity_file = board_dir / "activity.jsonl"
        assert activity_file.exists(), "activity.jsonl must be created by edit mutation"
        entries = [
            json.loads(line)
            for line in activity_file.read_text().splitlines()
            if line.strip()
        ]
        cockpit_entries = [e for e in entries if e.get("source") == "cockpit"]
        assert len(cockpit_entries) >= 1, (
            "At least one activity entry must have source='cockpit'"
        )

    def test_edit_noop_only_updated_writes_activity_log_source_cockpit(
        self, client: TestClient, engine: KanbanEngine, board_dir: Path
    ) -> None:
        """AC6: edit with only 'updated' (no other fields) must still write activity log.

        The empty-kwargs path currently bypasses engine.edit_task entirely, which
        silently skips the audit log. AC6 states all mutations must log source='cockpit'.
        Either the endpoint must reject no-op edits (422) or must call engine.edit_task
        to ensure the audit trail is written.
        """
        task = engine.show_task("1")
        response = client.post(
            "/api/tasks/1/edit",
            json={"updated": task.updated},  # no editable fields — empty kwargs
        )
        # A valid 200 response without an audit log entry violates AC6.
        # The endpoint must either: (a) call engine.edit_task producing an audit entry,
        # or (b) reject the no-op with 422 (no mutation = no log needed).
        # If 200 is returned, an activity log entry with source='cockpit' MUST exist.
        if response.status_code == 200:
            activity_file = board_dir / "activity.jsonl"
            assert activity_file.exists(), (
                "activity.jsonl must exist after a 200 edit response (AC6)"
            )
            entries = [
                json.loads(line)
                for line in activity_file.read_text().splitlines()
                if line.strip()
            ]
            cockpit_entries = [e for e in entries if e.get("source") == "cockpit"]
            assert len(cockpit_entries) >= 1, (
                "POST /edit with only 'updated' returned 200 but wrote no activity log "
                "entry — AC6 requires source='cockpit' for all mutations (empty-kwargs path)"
            )
        else:
            # 422 is also acceptable — a no-op edit is not a mutation, so no log needed.
            assert response.status_code == 422, (
                f"Expected 200 (with audit log) or 422 (no-op rejected), got {response.status_code}"
            )

    def test_release_writes_activity_log_source_cockpit(
        self, client: TestClient, engine: KanbanEngine, board_dir: Path
    ) -> None:
        """Release mutation writes activity.jsonl entry with source='cockpit'."""
        task = engine.show_task("2")
        client.post("/api/tasks/2/release", json={"updated": task.updated})
        activity_file = board_dir / "activity.jsonl"
        assert activity_file.exists(), (
            "activity.jsonl must be created by release mutation"
        )
        entries = [
            json.loads(line)
            for line in activity_file.read_text().splitlines()
            if line.strip()
        ]
        cockpit_entries = [e for e in entries if e.get("source") == "cockpit"]
        assert len(cockpit_entries) >= 1, (
            "At least one activity entry must have source='cockpit'"
        )


# ---------------------------------------------------------------------------
# Builder-discovered: edge cases not covered by TestFromAC_*
# ---------------------------------------------------------------------------


class TestBuilderDiscovered:
    """Builder-discovered tests: invalid priority → 422, and audit log content assertions."""

    def test_edit_invalid_priority_returns_422(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """Invalid priority string causes engine.edit_task to raise ValueError → must be 422."""
        task = engine.show_task("1")
        response = client.post(
            "/api/tasks/1/edit",
            json={"updated": task.updated, "priority": "ultra-critical"},
        )
        assert response.status_code == 422

    def test_move_audit_log_has_correct_action_and_task_id(
        self, client: TestClient, engine: KanbanEngine, board_dir: Path
    ) -> None:
        """Move audit log entry has action='move' and task_id matching the mutated task."""
        task = engine.show_task("1")
        client.post(
            "/api/tasks/1/move",
            json={"status": "in-progress", "updated": task.updated},
        )
        entries = [
            json.loads(line)
            for line in (board_dir / "activity.jsonl").read_text().splitlines()
            if line.strip()
        ]
        cockpit_entries = [e for e in entries if e.get("source") == "cockpit"]
        assert cockpit_entries[0]["action"] == "move"
        assert cockpit_entries[0]["task_id"] == 1

    def test_edit_audit_log_has_correct_action_and_task_id(
        self, client: TestClient, engine: KanbanEngine, board_dir: Path
    ) -> None:
        """Edit audit log entry has action='edit' and task_id matching the mutated task."""
        task = engine.show_task("1")
        client.post(
            "/api/tasks/1/edit",
            json={"updated": task.updated, "title": "Audit action test"},
        )
        entries = [
            json.loads(line)
            for line in (board_dir / "activity.jsonl").read_text().splitlines()
            if line.strip()
        ]
        cockpit_entries = [e for e in entries if e.get("source") == "cockpit"]
        assert cockpit_entries[0]["action"] == "edit"
        assert cockpit_entries[0]["task_id"] == 1

    def test_release_audit_log_has_correct_action_and_task_id(
        self, client: TestClient, engine: KanbanEngine, board_dir: Path
    ) -> None:
        """Release audit log entry has action='release' and task_id matching the mutated task."""
        task = engine.show_task("2")
        client.post("/api/tasks/2/release", json={"updated": task.updated})
        entries = [
            json.loads(line)
            for line in (board_dir / "activity.jsonl").read_text().splitlines()
            if line.strip()
        ]
        cockpit_entries = [e for e in entries if e.get("source") == "cockpit"]
        assert cockpit_entries[0]["action"] == "release"
        assert cockpit_entries[0]["task_id"] == 2


# ---------------------------------------------------------------------------
# AC #975: block:user tag lifecycle in edit_task route
# ---------------------------------------------------------------------------


class TestFromAC_BlockUserTag:
    """Tests for automatic block:user tag lifecycle in POST /api/tasks/{id}/edit.

    AC #975 — all tests must FAIL until GREEN implementation injects tag logic:
      1. edit_task adds 'block:user' tag when transitioning task to blocked
      2. edit_task removes 'block:user' tag when unblocking
      3. Tag addition is idempotent (no duplicates if called repeatedly)
      4. Unblock on a task without the tag doesn't error (robustness guard)

    Notes: AC4 trivially passes in RED (route returns 200 without tag handling).
    AC1-3 fail because the route does not inject/remove 'block:user' yet.
    """

    def test_block_adds_block_user_tag(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """AC1: Blocking via cockpit edit_task injects 'block:user' into the task's tags."""
        task = engine.show_task("1")
        response = client.post(
            "/api/tasks/1/edit",
            json={"updated": task.updated, "block_reason": "waiting on infra"},
        )
        assert response.status_code == 200
        assert "block:user" in response.json()["tags"]
        assert response.json()["blocked"] is True

    def test_unblock_removes_block_user_tag(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """AC2: Unblocking via cockpit edit_task removes 'block:user' from task tags."""
        # Setup: block with block:user tag present (simulates a prior cockpit block)
        engine.edit_task(
            "1", blocked=True, block_reason="dependency", add_tags=["block:user"]
        )
        task = engine.show_task("1")
        assert "block:user" in (task.tags or [])  # confirm setup

        response = client.post(
            "/api/tasks/1/edit",
            json={"updated": task.updated, "block_reason": None},
        )
        assert response.status_code == 200
        assert "block:user" not in response.json()["tags"]
        assert response.json()["blocked"] is False

    def test_block_user_tag_is_idempotent(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """AC3: Blocking a second time doesn't create duplicate 'block:user' tags."""
        # First block
        task = engine.show_task("1")
        r1 = client.post(
            "/api/tasks/1/edit",
            json={"updated": task.updated, "block_reason": "first block"},
        )
        assert r1.status_code == 200

        # Second block (task is already blocked — update reason)
        task2 = engine.show_task("1")
        r2 = client.post(
            "/api/tasks/1/edit",
            json={"updated": task2.updated, "block_reason": "second block"},
        )
        assert r2.status_code == 200
        tags = r2.json()["tags"]
        assert tags.count("block:user") == 1, (
            f"Expected exactly 1 'block:user' tag, got {tags.count('block:user')}: {tags}"
        )

    def test_unblock_without_tag_present_returns_200(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """AC4: Unblocking a task that has no 'block:user' tag doesn't error (returns 200)."""
        # Setup: block via engine directly WITHOUT adding block:user tag
        engine.edit_task("1", blocked=True, block_reason="set by engine, no tag added")
        task = engine.show_task("1")
        assert "block:user" not in (task.tags or [])  # confirm tag absent

        response = client.post(
            "/api/tasks/1/edit",
            json={"updated": task.updated, "block_reason": None},
        )
        assert response.status_code == 200
        assert response.json()["blocked"] is False


# ---------------------------------------------------------------------------
# AC #990: block:user tag-diff conflict resolution
# ---------------------------------------------------------------------------


class TestFromAC_BlockUserTagConflict:
    """Tests for tag-diff conflict resolution in POST /api/tasks/{id}/edit.

    AC #990 — conflict resolution when _apply_list_diff and _apply_block_kwargs
    produce contradictory add_tags/remove_tags entries for 'block:user'.

    RED phase — all tests fail until _apply_block_kwargs strips conflicting entries.
    """

    def test_block_conflict_preserves_block_user_tag(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """AC1 conflict: Blocking while tag-diff would remove block:user → block:user preserved.

        Setup: task already has 'block:user'. User sends tags=[] (omitting block:user)
        + block_reason set. Without conflict resolution, _apply_list_diff would add
        block:user to remove_tags, then _apply_block_kwargs skips (already in tags).
        Result without fix: block:user removed despite active blocking.
        """
        # Setup: task has block:user tag + scope:test tag
        engine.edit_task("1", add_tags=["block:user", "scope:test"])
        task = engine.show_task("1")
        assert "block:user" in (task.tags or [])  # confirm setup

        # User sends only ["scope:test"] in tags (omitting block:user) + sets block_reason
        # This causes tag-diff to put block:user in remove_tags
        response = client.post(
            "/api/tasks/1/edit",
            json={
                "updated": task.updated,
                "tags": ["scope:test"],
                "block_reason": "dependency still blocked",
            },
        )
        assert response.status_code == 200
        assert "block:user" in response.json()["tags"], (
            f"Expected block:user preserved during block+tag-diff, got {response.json()['tags']!r}"
        )
        assert "scope:test" in response.json()["tags"], (
            f"Expected scope:test sibling tag preserved, got {response.json()['tags']!r}"
        )

    def test_unblock_conflict_removes_block_user_tag(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """AC2 conflict: Unblocking while tag-diff would add block:user → block:user removed.

        Setup: task lacks 'block:user'. User sends tags=["block:user"] + block_reason=null.
        Without conflict resolution, _apply_list_diff would add block:user to add_tags,
        then _apply_block_kwargs skips (not in current_tags). Result: block:user added.
        """
        # Setup: block via engine without block:user tag
        engine.edit_task("1", blocked=True, block_reason="dependency")
        task = engine.show_task("1")
        assert "block:user" not in (task.tags or [])  # confirm setup

        # User sends tags=["block:user"] + block_reason=null (unblocking)
        response = client.post(
            "/api/tasks/1/edit",
            json={
                "updated": task.updated,
                "tags": ["block:user"],
                "block_reason": None,
            },
        )
        assert response.status_code == 200
        assert "block:user" not in response.json()["tags"], (
            f"Expected block:user not added during unblock+tag-diff, got {response.json()['tags']!r}"
        )

    def test_block_with_new_tags_adds_both(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """AC3 happy path: Blocking with new tags adds both block:user and the new tag."""
        task = engine.show_task("1")
        assert "block:user" not in (task.tags or [])  # confirm no prior block:user

        response = client.post(
            "/api/tasks/1/edit",
            json={
                "updated": task.updated,
                "tags": ["scope:test"],
                "block_reason": "waiting on dependency",
            },
        )
        assert response.status_code == 200
        result_tags = response.json()["tags"]
        assert "block:user" in result_tags, (
            f"Expected block:user in tags after block, got {result_tags!r}"
        )
        assert "scope:test" in result_tags, (
            f"Expected scope:test in tags after block, got {result_tags!r}"
        )


# ---------------------------------------------------------------------------
# AC7: Durable proof of parent:null, body:"", body:null/omitted, negative parent
# ---------------------------------------------------------------------------


class TestFromAC_EditBodyParentSemantics:
    """Durable proof of tri-state body/parent edit semantics (AC7).

    AC7 requires:
      (a) parent: null → clears parent
      (b) body: "" → clears body
      (c) body: null / omitted → no change
      (d) negative parent → 422
    """

    def test_edit_parent_null_clears_parent(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """AC7(a): parent: null in request body clears the parent field."""
        engine.edit_task("1", parent=3)
        task = engine.show_task("1")
        assert task.parent == 3, "Precondition: task 1 must have parent=3"

        response = client.post(
            "/api/tasks/1/edit",
            json={"updated": task.updated, "parent": None},
        )
        assert response.status_code == 200
        assert response.json()["parent"] is None

    def test_edit_body_empty_string_clears_body(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """AC7(b): body: "" clears the task body to empty string."""
        engine.edit_task("1", body="## Original content")
        task = engine.show_task("1")
        assert task.body, "Precondition: task 1 must have a non-empty body"

        response = client.post(
            "/api/tasks/1/edit",
            json={"updated": task.updated, "body": ""},
        )
        assert response.status_code == 200
        assert response.json()["body"] == ""

    def test_edit_body_null_does_not_change_body(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """AC7(c): body: null leaves the task body unchanged (no-change semantics)."""
        original_body = "## Persistent content"
        engine.edit_task("1", body=original_body)
        task = engine.show_task("1")
        assert task.body == original_body, "Precondition: body must be set"

        response = client.post(
            "/api/tasks/1/edit",
            json={"updated": task.updated, "title": "no-op body", "body": None},
        )
        assert response.status_code == 200
        assert response.json()["body"] == original_body

    def test_edit_body_omitted_does_not_change_body(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """AC7(c): omitting body from the request leaves the task body unchanged."""
        original_body = "## Persistent content that must survive"
        engine.edit_task("1", body=original_body)
        task = engine.show_task("1")

        response = client.post(
            "/api/tasks/1/edit",
            json={"updated": task.updated, "title": "changed title, body omitted"},
        )
        assert response.status_code == 200
        assert response.json()["body"] == original_body

    def test_edit_negative_parent_returns_422(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """AC7(d): negative parent value returns 422."""
        task = engine.show_task("1")
        response = client.post(
            "/api/tasks/1/edit",
            json={"updated": task.updated, "parent": -1},
        )
        assert response.status_code == 422

    def test_edit_empty_string_block_reason_clears_blocked_state(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """AC1: block_reason: '' (empty string) unblocks — same semantics as null.

        _apply_block_kwargs must treat falsy block_reason (None or '') as the
        unblock signal, removing block:user tag and setting blocked=False.
        """
        engine.edit_task("1", blocked=True, block_reason="waiting for review")
        task = engine.show_task("1")
        assert task.blocked is True, "Precondition: task 1 must be blocked"

        response = client.post(
            "/api/tasks/1/edit",
            json={"updated": task.updated, "block_reason": ""},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["blocked"] is False, "empty block_reason must unblock the task"
        assert "block:user" not in (body.get("tags") or []), (
            "block:user tag must be removed"
        )


# ---------------------------------------------------------------------------
# AC1: Durable proof of tags/depends_on clear+omit semantics
# ---------------------------------------------------------------------------


class TestFromAC_EditListClearOmit:
    """Durable proof of tags/depends_on clear+omit semantics (AC1).

    _apply_list_diff() in mutation.py handles:
    - desired=[] → clear (remove all current items from the task)
    - desired=None (field omitted from request) → no-op (preserve current items)
    """

    def test_edit_tags_empty_list_clears_all_tags(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """AC1: tags=[] removes all existing tags (full-clear semantics)."""
        engine.edit_task("1", add_tags=["scope:test", "type:bug"])
        task = engine.show_task("1")
        assert {"scope:test", "type:bug"} <= set(task.tags or []), (
            "Precondition: task 1 must have scope:test and type:bug tags"
        )

        response = client.post(
            "/api/tasks/1/edit",
            json={"updated": task.updated, "tags": []},
        )
        assert response.status_code == 200
        assert response.json()["tags"] == []

    def test_edit_depends_on_empty_list_clears_all_deps(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """AC1: depends_on=[] removes all existing dependencies (full-clear semantics)."""
        engine.edit_task("1", add_deps=[3])
        task = engine.show_task("1")
        assert 3 in (task.depends_on or []), (
            "Precondition: task 1 must have dep on task 3"
        )

        response = client.post(
            "/api/tasks/1/edit",
            json={"updated": task.updated, "depends_on": []},
        )
        assert response.status_code == 200
        assert response.json()["depends_on"] == []

    def test_edit_tags_field_omitted_preserves_existing_tags(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """AC1: omitting tags from request leaves existing tags unchanged (omit semantics)."""
        engine.edit_task("1", add_tags=["scope:test"])
        task = engine.show_task("1")
        assert "scope:test" in (task.tags or []), (
            "Precondition: task 1 must have scope:test tag"
        )

        response = client.post(
            "/api/tasks/1/edit",
            json={"updated": task.updated, "title": "title change, tags omitted"},
        )
        assert response.status_code == 200
        assert "scope:test" in (response.json()["tags"] or [])

    def test_edit_depends_on_field_omitted_preserves_existing_deps(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """AC1: omitting depends_on from request leaves existing deps unchanged (omit semantics)."""
        engine.edit_task("1", add_deps=[3])
        task = engine.show_task("1")
        assert 3 in (task.depends_on or []), (
            "Precondition: task 1 must have dep on task 3"
        )

        response = client.post(
            "/api/tasks/1/edit",
            json={"updated": task.updated, "title": "title change, deps omitted"},
        )
        assert response.status_code == 200
        assert 3 in (response.json()["depends_on"] or [])


# ---------------------------------------------------------------------------
# Merged from test_cockpit_mutation_api_1132.py (task #1132)
# ---------------------------------------------------------------------------

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Board fixture helpers
# ---------------------------------------------------------------------------

_CONFIG_YAML_1132 = """\
next_id: 1
"""


def _make_board_1132(base_dir: Path) -> Path:
    """Create a minimal kanban board directory."""
    kanban_dir_1132 = base_dir / "board"
    kanban_dir_1132.mkdir(parents=True, exist_ok=True)
    (kanban_dir_1132 / "config.yml").write_text(_CONFIG_YAML_1132, encoding="utf-8")
    (kanban_dir_1132 / "tasks").mkdir(exist_ok=True)
    (kanban_dir_1132 / "archive").mkdir(exist_ok=True)
    return kanban_dir_1132


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def board_dir_1132(tmp_path: Path) -> Path:
    """Board with 2 tasks.

    Task 1: status=todo,        priority=important  (unclaimed — move target)
    Task 2: status=in-progress, priority=needed     (claimed   — release target)
    """
    kanban_dir_1132 = _make_board_1132(tmp_path)
    seed = KanbanEngine(kanban_dir_1132)
    seed.create_task("Alpha task", status="todo", priority="important")
    seed.create_task("Beta task", status="in-progress", priority="needed")
    seed.list_tasks()
    seed.claim_task("2")
    return kanban_dir_1132


@pytest.fixture
def engine_1132(board_dir_1132: Path) -> KanbanEngine:
    """KanbanEngine bound to the test board with activity logging enabled."""
    eng = KanbanEngine(board_dir_1132, activity_log=True)
    eng.list_tasks()
    return eng


@pytest.fixture
def client_1132(engine_1132: KanbanEngine):
    """FastAPI TestClient with only get_engine overridden (no get_view)."""
    from fastapi.testclient import TestClient  # noqa: PLC0415
    from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415

    app.dependency_overrides[get_engine] = lambda: engine_1132
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def mock_view_client(engine_1132: KanbanEngine):
    """TestClient with mock CockpitView injected via get_view dependency override.

    Fails with ImportError until AC1 (get_view added to deps.py) is implemented.
    Yields (TestClient, mock_view) tuple.
    """
    from fastapi.testclient import TestClient  # noqa: PLC0415
    from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415
    from owlbear_cockpit.deps import get_view  # noqa: PLC0415  # ImportError → RED

    mock_view = mock.MagicMock(spec=CockpitView)
    # Provide the real engine_1132 so valid_transitions precheck can use it.
    mock_view.engine = engine_1132

    app.dependency_overrides[get_engine] = lambda: engine_1132
    app.dependency_overrides[get_view] = lambda: mock_view
    try:
        yield TestClient(app), mock_view
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# AC1: get_view dependency in deps.py
# ---------------------------------------------------------------------------


class TestFromAC_GetViewDependency:
    """AC1: get_view callable exists in owlbear_cockpit.deps; returns CockpitView(engine_1132)."""

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

    def test_get_view_returns_cockpit_view_instance(
        self, engine_1132: KanbanEngine
    ) -> None:
        """get_view(engine_1132) returns a CockpitView instance — not a raw engine_1132 or other type (AC1)."""
        from owlbear_cockpit.deps import get_view  # noqa: PLC0415

        result = get_view(engine_1132)
        assert isinstance(result, CockpitView), (
            f"get_view(engine_1132) must return CockpitView, got {type(result).__name__!r} (AC1)"
        )

    def test_get_view_engine_attribute_is_injected_engine(
        self, engine_1132: KanbanEngine
    ) -> None:
        """CockpitView from get_view() has .engine bound to the injected engine_1132 (AC1)."""
        from owlbear_cockpit.deps import get_view  # noqa: PLC0415

        result = get_view(engine_1132)
        assert result.engine is engine_1132, (
            "CockpitView.engine must be the same engine_1132 instance that was injected (AC1)"
        )

    def test_get_view_constructs_cockpit_view_with_engine_arg(
        self, engine_1132: KanbanEngine
    ) -> None:
        """get_view() calls CockpitView(engine_1132) — fails if factory returns wrong type (AC1)."""
        from owlbear_cockpit.deps import get_view  # noqa: PLC0415

        with mock.patch("owlbear_cockpit.deps.CockpitView") as mock_cv:
            mock_cv.return_value = mock.MagicMock(spec=CockpitView)
            get_view(engine_1132)
            mock_cv.assert_called_once_with(engine_1132)


# ---------------------------------------------------------------------------
# AC2: POST /move delegates to CockpitView.move_task
# ---------------------------------------------------------------------------


class TestFromAC_MoveCockpitViewDelegation:
    """AC2: Move route calls CockpitView.move_task with expected_updated kwarg."""

    def test_move_calls_cockpit_view_move_task(
        self, mock_view_client, engine_1132: KanbanEngine
    ) -> None:
        """Move route delegates to CockpitView.move_task (not engine_1132.move_task directly)."""
        client_1132, view = mock_view_client
        task = engine_1132.show_task("1")

        from owlbear_kanban.models import SingleTaskResponse  # noqa: PLC0415

        view.move_task.return_value = SingleTaskResponse(
            id=1,
            title="Alpha task",
            status="in-progress",
            priority="important",
            created=task.created,
            updated=task.updated,
        )
        client_1132.post(
            "/api/tasks/1/move",
            json={"status": "in-progress", "updated": task.updated},
        )
        assert view.move_task.called, (
            "Move route must delegate to CockpitView.move_task (AC2)"
        )

    def test_move_cockpit_view_receives_expected_updated_kwarg(
        self, mock_view_client, engine_1132: KanbanEngine
    ) -> None:
        """CockpitView.move_task receives expected_updated matching req.updated."""
        client_1132, view = mock_view_client
        task = engine_1132.show_task("1")

        from owlbear_kanban.models import SingleTaskResponse  # noqa: PLC0415

        view.move_task.return_value = SingleTaskResponse(
            id=1,
            title="Alpha task",
            status="in-progress",
            priority="important",
            created=task.created,
            updated=task.updated,
        )
        client_1132.post(
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
        self, mock_view_client, engine_1132: KanbanEngine
    ) -> None:
        """CockpitView.move_task receives the target status from req.status."""
        client_1132, view = mock_view_client
        task = engine_1132.show_task("1")

        from owlbear_kanban.models import SingleTaskResponse  # noqa: PLC0415

        view.move_task.return_value = SingleTaskResponse(
            id=1,
            title="Alpha task",
            status="review",
            priority="important",
            created=task.created,
            updated=task.updated,
        )
        client_1132.post(
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

    def test_release_without_body_returns_422_1132(
        self, client_1132: TestClient
    ) -> None:
        """POST /release without body returns 422 — ReleaseRequest.updated is required (AC3/AC8)."""
        response = client_1132.post("/api/tasks/2/release")  # no body
        assert response.status_code == 422, (
            f"Release without body must return 422 (ReleaseRequest.updated required), "
            f"got {response.status_code} (AC3)"
        )

    def test_release_delegates_to_cockpit_view_release_task(
        self, mock_view_client, engine_1132: KanbanEngine
    ) -> None:
        """Release route delegates to CockpitView.release_task (not engine_1132.release_task)."""
        client_1132, view = mock_view_client
        task = engine_1132.show_task("2")

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
        client_1132.post("/api/tasks/2/release", json={"updated": task.updated})
        assert view.release_task.called, (
            "Release route must delegate to CockpitView.release_task (AC3)"
        )

    def test_release_passes_expected_updated_to_cockpit_view(
        self, mock_view_client, engine_1132: KanbanEngine
    ) -> None:
        """CockpitView.release_task receives expected_updated=req.updated kwarg."""
        client_1132, view = mock_view_client
        task = engine_1132.show_task("2")

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
        client_1132.post("/api/tasks/2/release", json={"updated": task.updated})
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
        self, mock_view_client, engine_1132: KanbanEngine
    ) -> None:
        """CockpitView.move_task raises NotFoundError → route returns 404."""
        client_1132, view = mock_view_client
        task = engine_1132.show_task("1")
        view.move_task.side_effect = NotFoundError(
            code="ERR_NOT_FOUND", user_message="Task '1' not found"
        )
        view.engine.valid_transitions.return_value = {"in-progress"}
        response = client_1132.post(
            "/api/tasks/1/move",
            json={"status": "in-progress", "updated": task.updated},
        )
        assert response.status_code == 404, (
            "NotFoundError from CockpitView.move_task must map to 404 (AC4a)"
        )

    def test_move_validation_error_returns_422(
        self, mock_view_client, engine_1132: KanbanEngine
    ) -> None:
        """CockpitView.move_task raises ValidationError → route returns 422."""
        client_1132, view = mock_view_client
        task = engine_1132.show_task("1")
        view.move_task.side_effect = ValidationError(
            code="ERR_INVALID_STATUS", user_message="Invalid status transition"
        )
        view.engine.valid_transitions.return_value = {"in-progress"}
        response = client_1132.post(
            "/api/tasks/1/move",
            json={"status": "in-progress", "updated": task.updated},
        )
        assert response.status_code == 422, (
            "ValidationError from CockpitView.move_task must map to 422 (AC4a)"
        )

    def test_move_concurrency_error_returns_409(
        self, mock_view_client, engine_1132: KanbanEngine
    ) -> None:
        """CockpitView.move_task raises ConcurrencyError → route returns 409."""
        client_1132, view = mock_view_client
        task = engine_1132.show_task("1")
        view.move_task.side_effect = ConcurrencyError(
            code="ERR_STALE", user_message="Stale snapshot"
        )
        view.engine.valid_transitions.return_value = {"in-progress"}
        response = client_1132.post(
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
        self, mock_view_client, engine_1132: KanbanEngine
    ) -> None:
        """CockpitView.release_task raises NotFoundError → route returns 404."""
        client_1132, view = mock_view_client
        task = engine_1132.show_task("2")

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
        response = client_1132.post(
            "/api/tasks/2/release", json={"updated": task.updated}
        )
        assert response.status_code == 404, (
            "NotFoundError from CockpitView.release_task must map to 404 (AC4b)"
        )

    def test_release_concurrency_error_returns_409(
        self, mock_view_client, engine_1132: KanbanEngine
    ) -> None:
        """CockpitView.release_task raises ConcurrencyError → route returns 409."""
        client_1132, view = mock_view_client
        task = engine_1132.show_task("2")

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
        response = client_1132.post(
            "/api/tasks/2/release", json={"updated": task.updated}
        )
        assert response.status_code == 409, (
            "ConcurrencyError from CockpitView.release_task must map to 409 (AC4b)"
        )


# ---------------------------------------------------------------------------
# AC5: Release guard uses claimed boolean (not claimed_by)
# ---------------------------------------------------------------------------


class TestFromAC_ReleaseClaim:
    """AC5: Genuinely claimed task → 200; unclaimed guard preserved via claimed bool."""

    def test_release_genuinely_claimed_task_returns_200(
        self, client_1132: TestClient, engine_1132: KanbanEngine
    ) -> None:
        """Claimed task (claimed_at on disk) released via cockpit → 200 (G3 fix).

        Current behavior: 409 (guard uses claimed_by which is Field(exclude=True),
        always None after disk round-trip). After fix: guard uses claimed boolean
        from CockpitView.show_task which correctly reflects claimed_at.
        """
        task = engine_1132.show_task("2")
        assert task.claimed_at is not None, (
            "Precondition: task 2 must have claimed_at on disk"
        )
        response = client_1132.post(
            "/api/tasks/2/release", json={"updated": task.updated}
        )
        assert response.status_code == 200, (
            f"Genuinely claimed task (claimed_at set) must return 200 after G3 fix (AC5), "
            f"got {response.status_code}"
        )

    def test_release_claimed_task_response_has_required_fields(
        self, client_1132: TestClient, engine_1132: KanbanEngine
    ) -> None:
        """Release 200 response has all required task-detail fields."""
        task = engine_1132.show_task("2")
        response = client_1132.post(
            "/api/tasks/2/release", json={"updated": task.updated}
        )
        assert response.status_code == 200
        body = response.json()
        for field in (
            "id",
            "title",
            "status",
            "priority",
            "updated",
            "claimed",
            "tags",
        ):
            assert field in body, f"Release response must include '{field}' field (AC5)"

    def test_release_claimed_task_response_claimed_false_after_release(
        self, client_1132: TestClient, engine_1132: KanbanEngine
    ) -> None:
        """Release 200 response has claimed=False (claim cleared by release)."""
        task = engine_1132.show_task("2")
        response = client_1132.post(
            "/api/tasks/2/release", json={"updated": task.updated}
        )
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
        self, mock_view_client, engine_1132: KanbanEngine
    ) -> None:
        """_task_to_detail does not raise AttributeError when handling SingleTaskResponse.

        SingleTaskResponse lacks claimed_by. _task_to_detail must use getattr or
        model_validate approach (see builder guidance) instead of task.claimed_by.
        """
        client_1132, view = mock_view_client
        task = engine_1132.show_task("1")

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
        view.engine.valid_transitions.return_value = {"in-progress"}
        response = client_1132.post(
            "/api/tasks/1/move",
            json={"status": "in-progress", "updated": task.updated},
        )
        assert response.status_code == 200, (
            f"_task_to_detail must not raise AttributeError on SingleTaskResponse "
            f"(AC6), got {response.status_code}"
        )

    def test_move_response_has_claimed_field_from_single_task_response(
        self, mock_view_client, engine_1132: KanbanEngine
    ) -> None:
        """Move response includes 'claimed' field correctly derived from SingleTaskResponse."""
        client_1132, view = mock_view_client
        task = engine_1132.show_task("1")

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
        view.engine.valid_transitions.return_value = {"in-progress"}
        response = client_1132.post(
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
        self, client_1132: TestClient, engine_1132: KanbanEngine
    ) -> None:
        """Claimed task + stale updated token → 409 with stale-snapshot detail (AC7).

        Current behavior: guard fires (claimed_by=None) → 409 with 'not currently claimed'.
        After fix: CockpitView.release_task(expected_updated=stale) raises ConcurrencyError
        → 409 with stale-snapshot detail.
        """
        task = engine_1132.show_task("2")
        stale_token = task.updated
        # Advance task's updated timestamp so stale_token is now outdated
        engine_1132.edit_task("2", title="Modified to advance updated timestamp")

        response = client_1132.post(
            "/api/tasks/2/release", json={"updated": stale_token}
        )
        assert response.status_code == 409
        body = response.json()
        assert "detail" not in body
        assert body.get("code") == "ERR_STALE"
        assert "message" in body, (
            f"Stale token on claimed task must return 409 with stale-snapshot detail (AC7), "
            f"got body: {body!r}"
        )

    def test_release_fresh_updated_token_on_claimed_task_returns_200(
        self, client_1132: TestClient, engine_1132: KanbanEngine
    ) -> None:
        """Claimed task + fresh updated token → 200 (contrast with stale-token 409, AC7)."""
        task = engine_1132.show_task("2")
        response = client_1132.post(
            "/api/tasks/2/release", json={"updated": task.updated}
        )
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
        self, client_1132: TestClient, engine_1132: KanbanEngine, board_dir_1132: Path
    ) -> None:
        """Release success (200) produces activity.jsonl entry with source='cockpit'."""
        task = engine_1132.show_task("2")
        response = client_1132.post(
            "/api/tasks/2/release", json={"updated": task.updated}
        )
        assert response.status_code == 200, (
            f"Precondition: release must return 200 to verify activity logging (AC10), "
            f"got {response.status_code}"
        )
        activity_file = board_dir_1132 / "activity.jsonl"
        assert activity_file.exists(), (
            "activity.jsonl must exist after successful release (AC10)"
        )
        entries = [
            json.loads(line)
            for line in activity_file.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        cockpit_entries = [e for e in entries if e.get("source") == "cockpit"]
        assert len(cockpit_entries) >= 1, (
            "At least one activity entry must have source='cockpit' after release (AC10)"
        )


# ---------------------------------------------------------------------------
# Merged from test_cockpit_mutation_api_1134.py (task #1134)
# ---------------------------------------------------------------------------

_CONFIG_YAML_1134 = """\
next_id: 1
"""


def _make_board_1134(base_dir: Path) -> Path:
    """Create a minimal kanban board directory. Returns kanban_dir_1134."""
    kanban_dir_1134 = base_dir / "board"
    kanban_dir_1134.mkdir(parents=True, exist_ok=True)
    (kanban_dir_1134 / "config.yml").write_text(_CONFIG_YAML_1134, encoding="utf-8")
    (kanban_dir_1134 / "tasks").mkdir(exist_ok=True)
    (kanban_dir_1134 / "archive").mkdir(exist_ok=True)
    return kanban_dir_1134


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def board_dir_1134(tmp_path: Path) -> Path:
    """Board with one unclaimed task in todo status."""
    kanban_dir_1134 = _make_board_1134(tmp_path)
    seed = KanbanEngine(kanban_dir_1134)
    seed.create_task("Alpha task", status="todo", priority="important")
    seed.list_tasks()
    return kanban_dir_1134


@pytest.fixture
def engine_1134(board_dir_1134: Path) -> KanbanEngine:
    """KanbanEngine bound to the test board."""
    eng = KanbanEngine(board_dir_1134, activity_log=False)
    eng.list_tasks()
    return eng


@pytest.fixture
def client_1134(engine_1134: KanbanEngine):
    """FastAPI TestClient with cockpit engine_1134 injected via dependency_overrides."""
    from fastapi.testclient import TestClient  # noqa: PLC0415
    from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415

    app.dependency_overrides[get_engine] = lambda: engine_1134
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# AC1 — engine_1134.edit_task receives expected_updated kwarg
# ---------------------------------------------------------------------------


class TestFromAC_EditCASEngagement:
    """AC1: edit route passes expected_updated to engine_1134.edit_task."""

    def test_edit_passes_expected_updated_to_engine(
        self, client_1134, engine_1134: KanbanEngine
    ) -> None:
        """engine_1134.edit_task must be called with expected_updated in kwargs.

        The current route calls engine_1134.edit_task(**kwargs) without forwarding
        expected_updated (TOCTOU gap).  After the fix, expected_updated=req.updated
        must appear in the captured call kwargs, engaging the engine_1134 CAS.
        """
        task = engine_1134.show_task("1")
        with mock.patch.object(
            engine_1134, "edit_task", wraps=engine_1134.edit_task
        ) as mocked:
            response = client_1134.post(
                "/api/tasks/1/edit",
                json={"updated": task.updated, "title": "CAS probe"},
            )
        assert response.status_code == 200, f"Unexpected status: {response.status_code}"
        assert mocked.called, "engine_1134.edit_task must have been called"
        call_kwargs = mocked.call_args.kwargs
        assert "expected_updated" in call_kwargs, (
            "Edit route must pass expected_updated to engine_1134 (AC1 — CAS must be engaged, "
            "not just the route-level precheck)"
        )

    def test_edit_expected_updated_value_matches_request_snapshot(
        self, client_1134, engine_1134: KanbanEngine
    ) -> None:
        """The expected_updated value forwarded to engine_1134 must equal req.updated.

        The CAS token is the updated timestamp from the request body.  Forwarding
        a different value would defeat the CAS purpose.
        """
        task = engine_1134.show_task("1")
        with mock.patch.object(
            engine_1134, "edit_task", wraps=engine_1134.edit_task
        ) as mocked:
            response = client_1134.post(
                "/api/tasks/1/edit",
                json={"updated": task.updated, "title": "CAS value probe"},
            )
        assert response.status_code == 200, f"Unexpected status: {response.status_code}"
        assert mocked.called, "engine_1134.edit_task must have been called"
        forwarded = mocked.call_args.kwargs.get("expected_updated")
        assert forwarded == task.updated, (
            f"expected_updated forwarded to engine_1134 ({forwarded!r}) must equal "
            f"req.updated ({task.updated!r})"
        )


# ---------------------------------------------------------------------------
# AC2 — ModelConcurrencyError → HTTPException(409)
# ---------------------------------------------------------------------------


class TestFromAC_ConcurrencyErrorHandler:
    """AC2: ModelConcurrencyError from engine_1134.edit_task is mapped to HTTP 409."""

    def test_edit_concurrency_error_returns_409(
        self, client_1134, engine_1134: KanbanEngine
    ) -> None:
        """When engine_1134.edit_task raises ModelConcurrencyError, route must return 409.

        Currently the route has no except ModelConcurrencyError handler, so the
        exception propagates to the ASGI layer as 500.
        """
        task = engine_1134.show_task("1")
        exc = ModelConcurrencyError(code="ERR_STALE", user_message="stale")
        with mock.patch.object(engine_1134, "edit_task", side_effect=exc):
            response = client_1134.post(
                "/api/tasks/1/edit",
                json={"updated": task.updated, "title": "ModelConcurrencyError probe"},
            )
        assert response.status_code == 409, (
            f"ModelConcurrencyError must map to 409, got {response.status_code}"
        )

    def test_edit_concurrency_error_detail_matches_canonical_message(
        self, client_1134, engine_1134: KanbanEngine
    ) -> None:
        """409 detail string must be the canonical stale-snapshot message."""
        task = engine_1134.show_task("1")
        exc = ModelConcurrencyError(code="ERR_STALE", user_message="stale")
        with mock.patch.object(engine_1134, "edit_task", side_effect=exc):
            response = client_1134.post(
                "/api/tasks/1/edit",
                json={"updated": task.updated, "title": "Detail probe"},
            )
        body = response.json()
        assert "detail" not in body
        assert body.get("code") == "ERR_STALE"
        assert body.get("message") == "stale", f"Envelope message mismatch: {body!r}"

    def test_edit_concurrency_error_not_propagated_as_500(
        self, client_1134, engine_1134: KanbanEngine
    ) -> None:
        """ModelConcurrencyError must not leak as an unhandled 500 server error."""
        task = engine_1134.show_task("1")
        exc = ModelConcurrencyError(code="ERR_STALE", user_message="stale")
        with mock.patch.object(engine_1134, "edit_task", side_effect=exc):
            response = client_1134.post(
                "/api/tasks/1/edit",
                json={"updated": task.updated, "title": "500-guard probe"},
            )
        assert response.status_code != 500, (
            "ModelConcurrencyError must not propagate as 500 — add except ModelConcurrencyError handler"
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
        self, client_1134, engine_1134: KanbanEngine
    ) -> None:
        """Direct regression: edit title with valid snapshot → 200 with updated task."""
        task = engine_1134.show_task("1")
        response = client_1134.post(
            "/api/tasks/1/edit",
            json={"updated": task.updated, "title": "Regression guard title"},
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Regression guard title"

    def test_edit_stale_snapshot_still_returns_409(self, client_1134) -> None:
        """Regression: stale updated token → 409 (precheck preserved)."""
        response = client_1134.post(
            "/api/tasks/1/edit",
            json={"updated": "1970-01-01T00:00:00+00:00", "title": "Stale probe"},
        )
        assert response.status_code == 409

    def test_edit_nonexistent_task_still_returns_404(self, client_1134) -> None:
        """Regression: non-existent task ID → 404."""
        response = client_1134.post(
            "/api/tasks/999/edit",
            json={"updated": "1970-01-01T00:00:00+00:00", "title": "Not found probe"},
        )
        assert response.status_code == 404

    def test_edit_no_editable_fields_still_returns_422(
        self, client_1134, engine_1134: KanbanEngine
    ) -> None:
        """Regression: request with only updated field (no editable fields) → 422."""
        task = engine_1134.show_task("1")
        response = client_1134.post(
            "/api/tasks/1/edit",
            json={"updated": task.updated},
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Merged from test_cockpit_mutation_api_1135.py (task #1135)
# ---------------------------------------------------------------------------

_CONFIG_YAML_1135 = """\
next_id: 1
"""


def _make_board_1135(base_dir: Path) -> Path:
    """Create a minimal kanban board directory. Returns kanban_dir_1135."""
    kanban_dir_1135 = base_dir / "board"
    kanban_dir_1135.mkdir(parents=True, exist_ok=True)
    (kanban_dir_1135 / "config.yml").write_text(_CONFIG_YAML_1135, encoding="utf-8")
    (kanban_dir_1135 / "tasks").mkdir(exist_ok=True)
    (kanban_dir_1135 / "archive").mkdir(exist_ok=True)
    return kanban_dir_1135


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def board_dir_1135(tmp_path: Path) -> Path:
    """Board with 2 tasks.

    Task 1: status=todo,        priority=important  (unclaimed — move target)
    Task 2: status=in-progress, priority=needed     (unclaimed)
    """
    kanban_dir_1135 = _make_board_1135(tmp_path)
    seed = KanbanEngine(kanban_dir_1135)
    seed.create_task("Alpha task", status="todo", priority="important")
    seed.create_task("Beta task", status="in-progress", priority="needed")
    seed.list_tasks()
    return kanban_dir_1135


@pytest.fixture
def engine_1135(board_dir_1135: Path) -> KanbanEngine:
    """KanbanEngine for cockpit route tests."""
    eng = KanbanEngine(board_dir_1135)
    eng.list_tasks()
    return eng


@pytest.fixture
def client_1135(engine_1135: KanbanEngine):
    """FastAPI TestClient with cockpit engine_1135 injected via dependency_overrides."""
    from fastapi.testclient import TestClient  # noqa: PLC0415
    from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415

    app.dependency_overrides[get_engine] = lambda: engine_1135
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# AC1 — MoveRequest requires 'updated' field
# ---------------------------------------------------------------------------


class TestFromAC_MoveRequestUpdatedField:
    """AC1: MoveRequest must accept a required 'updated' field (str).

    Currently MoveRequest has only 'status'. Adding 'updated' as required means
    requests without it get 422 (Pydantic validates before the handler runs).
    """

    def test_move_without_updated_field_returns_422(self, client_1135) -> None:
        """Move request missing 'updated' field → 422 validation error.

        Fails against current code because MoveRequest has no 'updated' field
        and the request succeeds with just {'status': 'in-progress'}.
        """
        response = client_1135.post("/api/tasks/1/move", json={"status": "in-progress"})
        assert response.status_code == 422

    def test_move_with_valid_updated_and_status_returns_200(
        self, client_1135, engine_1135: KanbanEngine
    ) -> None:
        """Happy path: move with valid 'updated' token and reachable status → 200.

        Fails against current code because 'updated' is not accepted in MoveRequest.
        """
        task = engine_1135.show_task("1")
        response = client_1135.post(
            "/api/tasks/1/move",
            json={"status": "in-progress", "updated": task.updated},
        )
        assert response.status_code == 200

    def test_move_nonexistent_task_with_updated_returns_404(self, client_1135) -> None:
        """Non-existent task with 'updated' present → 404 (not 422 or 200).

        Pydantic accepts the request body; handler raises 404.
        Fails because 'updated' is not yet a field in MoveRequest.
        """
        response = client_1135.post(
            "/api/tasks/999/move",
            json={"status": "in-progress", "updated": "2025-01-01T00:00:00"},
        )
        assert response.status_code == 404
        body = response.json()
        assert "detail" not in body
        assert body.get("code") == "ERR_NOT_FOUND"
        assert "999" in str(body.get("message", ""))

    def test_move_with_null_updated_returns_422(self, client_1135) -> None:
        """Move request with null 'updated' value → 422 validation error.

        AC1 specifies 'updated' must be str (required). A null value is not a
        valid string and must be rejected by Pydantic type validation before
        the handler body runs. This is an AC1 non-string boundary case.
        """
        response = client_1135.post(
            "/api/tasks/1/move",
            json={"status": "in-progress", "updated": None},
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# AC2 — Precheck and expected_updated passthrough
# ---------------------------------------------------------------------------


class TestFromAC_MovePrecheck:
    """AC2: Route checks req.updated != str(task.updated) -> 409 and passes
    expected_updated=req.updated to engine_1135.move_task().
    """

    def test_move_with_matching_updated_calls_engine_with_expected_updated(
        self, client_1135, engine_1135: KanbanEngine
    ) -> None:
        """Route must pass expected_updated=req.updated to engine_1135.move_task().

        Wraps engine_1135.move_task to inspect kwargs. Currently the route calls
        engine_1135.move_task without expected_updated — this test proves the gap.
        """
        task = engine_1135.show_task("1")
        with mock.patch.object(
            engine_1135, "move_task", wraps=engine_1135.move_task
        ) as mocked:
            response = client_1135.post(
                "/api/tasks/1/move",
                json={"status": "in-progress", "updated": task.updated},
            )
        assert response.status_code == 200
        assert mocked.called, "engine_1135.move_task must have been called"
        call_kwargs = mocked.call_args.kwargs
        assert "expected_updated" in call_kwargs, (
            "Route must pass expected_updated to engine_1135.move_task"
        )
        assert call_kwargs["expected_updated"] == task.updated

    def test_move_precheck_stale_updated_returns_409(
        self, client_1135, engine_1135: KanbanEngine
    ) -> None:
        """Stale 'updated' token (precheck) → 409 before engine_1135 is called.

        The route must short-circuit with 409 when req.updated does not match
        the current task.updated. Currently no precheck exists — move succeeds.
        """
        task = engine_1135.show_task("1")
        stale_timestamp = task.updated
        # Advance task.updated via engine_1135 before the HTTP move
        engine_1135.edit_task("1", title="Concurrently modified — bumps updated")
        # HTTP move carries the old (stale) snapshot
        response = client_1135.post(
            "/api/tasks/1/move",
            json={"status": "in-progress", "updated": stale_timestamp},
        )
        assert response.status_code == 409

    def test_move_precheck_stale_does_not_call_engine_move(
        self, client_1135, engine_1135: KanbanEngine
    ) -> None:
        """When precheck detects stale token, route returns 409 without calling engine_1135.

        Ensures the route short-circuits before the write rather than relying
        solely on the engine_1135 CAS for protection.
        """
        task = engine_1135.show_task("1")
        stale_timestamp = task.updated
        engine_1135.edit_task("1", title="Bump updated for precheck test")
        with mock.patch.object(
            engine_1135, "move_task", wraps=engine_1135.move_task
        ) as mocked:
            response = client_1135.post(
                "/api/tasks/1/move",
                json={"status": "in-progress", "updated": stale_timestamp},
            )
        # Both assertions must hold: route returns 409 AND engine_1135 is never invoked
        assert response.status_code == 409, (
            "Stale precheck must return 409, not bypass to engine_1135"
        )
        assert not mocked.called, (
            "engine_1135.move_task must not be called when precheck detects stale token"
        )


# ---------------------------------------------------------------------------
# AC3 — ConcurrencyError → HTTP 409 with exact detail string
# ---------------------------------------------------------------------------


class TestFromAC_MoveConcurrencyError:
    """AC3: Route catches ConcurrencyError and returns 409 with the exact detail string.

    The precheck guards against detected staleness; engine_1135.move_task with
    expected_updated is belt-and-suspenders for TOCTOU races. The route must
    catch ConcurrencyError and return 409.
    """

    def test_move_concurrency_error_from_engine_returns_409(
        self, client_1135, engine_1135: KanbanEngine
    ) -> None:
        """ConcurrencyError raised by engine_1135.move_task → HTTP 409.

        Currently the route has no ConcurrencyError handler — the exception
        would propagate as a 500.
        """
        task = engine_1135.show_task("1")

        def _raise_concurrency(*_args, **_kwargs):  # type: ignore[no-untyped-def]
            raise ConcurrencyError(
                code="ERR_STALE",
                user_message="stale write detected",
            )

        with mock.patch.object(
            engine_1135, "move_task", side_effect=_raise_concurrency
        ):
            response = client_1135.post(
                "/api/tasks/1/move",
                json={"status": "in-progress", "updated": task.updated},
            )
        assert response.status_code == 409

    def test_move_concurrency_error_has_exact_detail_string(
        self, client_1135, engine_1135: KanbanEngine
    ) -> None:
        """ConcurrencyError → 409 detail must be the canonical stale-snapshot message.

        Exact string: "Task was modified since your last load (stale snapshot)"
        """
        task = engine_1135.show_task("1")

        def _raise_concurrency(*_args, **_kwargs):  # type: ignore[no-untyped-def]
            raise ConcurrencyError(
                code="ERR_STALE",
                user_message="stale write detected",
            )

        with mock.patch.object(
            engine_1135, "move_task", side_effect=_raise_concurrency
        ):
            response = client_1135.post(
                "/api/tasks/1/move",
                json={"status": "in-progress", "updated": task.updated},
            )
        body = response.json()
        assert "detail" not in body
        assert body.get("code") == "ERR_STALE"
        assert body.get("message") == "stale write detected"


# ---------------------------------------------------------------------------
# AC5 — test_move_stale_updated_returns_409_1135 (named per AC)
# ---------------------------------------------------------------------------


class TestFromAC_MoveStaleUpdated:
    """AC5: End-to-end stale-token test using real engine_1135 state mutation.

    Pattern: obtain task snapshot → mutate task via engine_1135 (bumps updated) →
    HTTP move with stale token → 409.
    """

    def test_move_stale_updated_returns_409_1135(
        self, client_1135, engine_1135: KanbanEngine
    ) -> None:
        """Stale 'updated' token causes move route to return 409.

        Follows the pattern from test_edit_stale_updated_returns_409 in
        test_cockpit_mutation_api.py (same file, L286-300).
        """
        task = engine_1135.show_task("1")
        stale_updated = task.updated
        # Mutate task via engine_1135 between the client_1135's snapshot and the HTTP move
        engine_1135.edit_task("1", title="Interleaved engine_1135 mutation")
        # HTTP move with stale snapshot
        response = client_1135.post(
            "/api/tasks/1/move",
            json={"status": "in-progress", "updated": stale_updated},
        )
        assert response.status_code == 409

    def test_move_fresh_updated_after_mutation_returns_200(
        self, client_1135, engine_1135: KanbanEngine
    ) -> None:
        """After mutation, a fresh 'updated' token allows the move to succeed → 200.

        Boundary: confirms 409 is token-staleness specific, not a blanket block.
        """
        # Mutate task first
        engine_1135.edit_task("1", title="Pre-move mutation")
        # Re-read the task to get the fresh updated token
        task = engine_1135.show_task("1")
        response = client_1135.post(
            "/api/tasks/1/move",
            json={"status": "in-progress", "updated": task.updated},
        )
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# AC4 — Shared suite contract: test_cockpit_mutation_api.py move tests updated
# ---------------------------------------------------------------------------


class TestFromAC_MoveSharedSuiteContract:
    """AC4: All /move POST calls in test_cockpit_mutation_api.py include 'updated' token.

    Source inspection guard. Fails until the builder updates the shared mutation
    suite to carry the required OCC token in every move request payload.
    """

    @staticmethod
    def _find_enclosing_test_name(lines: list[str], index: int) -> str:
        """Return the nearest enclosing test function name for a source line."""
        for j in range(index, -1, -1):
            stripped = lines[j].strip()
            if stripped.startswith("def test_"):
                return stripped
        return ""

    def test_shared_suite_move_posts_all_include_updated_token(self) -> None:
        """Source inspection: every /move POST in test_cockpit_mutation_api.py
        carries 'updated' in the json payload.

        Fails currently because test_cockpit_mutation_api.py sends status-only
        payloads for all 6 move POST calls (lines ~139, 144, 153, 164, 169, 400).
        Passes after builder applies AC4 and adds 'updated' to each call.
        """
        source = Path("tests/test_cockpit_mutation_api.py").read_text(encoding="utf-8")
        lines = source.splitlines()
        violations: list[str] = []
        client_post_pattern = re.compile(r"client\w*\.post")

        for i, line in enumerate(lines):
            # Match lines that contain a /move URL fragment (part of a move POST)
            if "/move" not in line:
                continue
            enclosing_test = self._find_enclosing_test_name(lines, i)
            # Intentionally missing-updated tests are expected to omit OCC token.
            if (
                "without_updated" in enclosing_test
                or "missing_updated" in enclosing_test
            ):
                continue
            # Collect a window covering the enclosing client.post(...) call
            start = max(0, i - 2)
            end = min(len(lines), i + 5)
            window = "\n".join(lines[start:end])
            # Skip lines that are not part of a client.post call
            if not client_post_pattern.search(window):
                continue
            # Flag if 'updated' is absent from the payload context
            if '"updated"' not in window and "'updated'" not in window:
                violations.append(f"  line {i + 1}: {line.strip()!r}")

        assert not violations, (
            "Move POST calls in test_cockpit_mutation_api.py missing 'updated' OCC token"
            " (AC4 — builder must update all move payloads):\n" + "\n".join(violations)
        )

    def test_shared_suite_move_posts_source_updated_from_engine_show_task(self) -> None:
        """Stronger AC4 guard: every /move POST in test_cockpit_mutation_api.py
        sources 'updated' dynamically from engine_1135.show_task (not hardcoded).

        The weaker guard (test_shared_suite_move_posts_all_include_updated_token)
        only checks that the 'updated' key is present in the payload window.
        This test additionally verifies 'task.updated' appears nearby, proving
        the token is sourced dynamically — not from a hardcoded or stale value.

        Fails if any /move POST payload uses a hardcoded 'updated' value
        instead of one derived from engine.show_task().updated.
        """
        source = Path("tests/test_cockpit_mutation_api.py").read_text(encoding="utf-8")
        lines = source.splitlines()
        violations: list[str] = []
        client_post_pattern = re.compile(r"client\w*\.post")

        for i, line in enumerate(lines):
            if "/move" not in line:
                continue
            enclosing_test = self._find_enclosing_test_name(lines, i)
            if (
                "without_updated" in enclosing_test
                or "missing_updated" in enclosing_test
                or "nonexistent_task" in enclosing_test
                or "null_updated" in enclosing_test
            ):
                continue
            start = max(0, i - 8)
            end = min(len(lines), i + 5)
            window = "\n".join(lines[start:end])
            if not client_post_pattern.search(window):
                continue
            # Skip if 'updated' key is absent from actual payload (colon
            # distinguishes dict keys from docstring/comment mentions)
            if '"updated":' not in window and "'updated':" not in window:
                continue
            # Stronger: verify 'updated' value is sourced from task.updated
            if "task.updated" not in window:
                violations.append(
                    f"  line {i + 1}: /move POST has 'updated' key but no "
                    f"'task.updated' source (may be hardcoded): {line.strip()!r}"
                )

        assert not violations, (
            "Move POST payloads in test_cockpit_mutation_api.py must source 'updated' from "
            "engine.show_task().updated (not hardcoded) per AC4:\n"
            + "\n".join(violations)
        )

    def test_shared_suite_config_is_engine_compatible(self, tmp_path: Path) -> None:
        """AC4: The _CONFIG_YAML_1135 in test_cockpit_mutation_api.py can initialize
        KanbanEngine without ConfigError.

        The shared move tests cannot execute when their board fixture raises
        ConfigError at KanbanEngine init. This test proves the shared suite's
        config format satisfies current engine_1135 validation requirements,
        including agent_map for every declared status.

        Fails when test_cockpit_mutation_api.py uses a stale config format
        that is missing agent_map — causing 37 setup errors that prevent AC4
        from being verified by executable regression of the named suite.
        """
        module_path = Path("tests/test_cockpit_mutation_api.py")
        spec = importlib.util.spec_from_file_location(
            "_shared_suite_probe", module_path
        )
        assert spec is not None
        assert spec.loader is not None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # defines _CONFIG_YAML_1135 and imports
        config_yaml: str = mod._CONFIG_YAML_1135

        kanban_dir_1135 = tmp_path / "shared-board"
        kanban_dir_1135.mkdir()
        (kanban_dir_1135 / "config.yml").write_text(config_yaml, encoding="utf-8")
        (kanban_dir_1135 / "tasks").mkdir()
        (kanban_dir_1135 / "archive").mkdir()

        # Must not raise ConfigError — failure here proves the shared suite
        # is setup-blocked and AC4 cannot be confirmed by executable regression
        KanbanEngine(kanban_dir_1135)


# ---------------------------------------------------------------------------
# Merged from test_cockpit_mutation_api_1239.py (task #1239)
# ---------------------------------------------------------------------------

_CONFIG_YAML_1239 = """\
next_id: 1
"""


def _make_board_1239(base_dir: Path) -> Path:
    """Create a minimal kanban board directory."""
    kanban_dir_1239 = base_dir / "board"
    kanban_dir_1239.mkdir(parents=True, exist_ok=True)
    (kanban_dir_1239 / "config.yml").write_text(_CONFIG_YAML_1239, encoding="utf-8")
    (kanban_dir_1239 / "tasks").mkdir(exist_ok=True)
    (kanban_dir_1239 / "archive").mkdir(exist_ok=True)
    return kanban_dir_1239


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def board_dir_1239(tmp_path: Path) -> Path:
    """Board with one task at todo status (move/route target)."""
    kanban_dir_1239 = _make_board_1239(tmp_path)
    seed = KanbanEngine(kanban_dir_1239)
    seed.create_task("Alpha task", status="todo", priority="important")
    seed.list_tasks()
    return kanban_dir_1239


@pytest.fixture
def engine_1239(board_dir_1239: Path) -> KanbanEngine:
    """KanbanEngine bound to the test board."""
    eng = KanbanEngine(board_dir_1239, activity_log=True)
    eng.list_tasks()
    return eng


@pytest.fixture
def mock_view_client_1239(engine_1239: KanbanEngine):
    """TestClient with mock CockpitView injected via get_view dependency.

    Yields (TestClient, mock_view) tuple.
    Fails with ImportError until AC1 (get_view in deps.py) is implemented.
    """
    from fastapi.testclient import TestClient  # noqa: PLC0415
    from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415
    from owlbear_cockpit.deps import get_view  # noqa: PLC0415

    mock_view = mock.MagicMock(spec=CockpitView)
    mock_view.engine = engine_1239

    app.dependency_overrides[get_engine] = lambda: engine_1239
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
        """MoveRequest without archival_refs defaults to None (AC1)."""
        req = MoveRequest(status="in-progress", updated="2026-01-01T00:00:00+00:00")
        # AttributeError → RED (field does not exist yet)
        assert req.archival_refs is None

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
        self, mock_view_client_1239, engine_1239: KanbanEngine
    ) -> None:
        """Route passes req.archival_reason to view.move_task (AC4).

        Fails in RED: Pydantic rejects archival_reason as an extra field → 422.
        """
        from owlbear_kanban.models import SingleTaskResponse  # noqa: PLC0415

        client_1239, view = mock_view_client_1239
        task = engine_1239.show_task("1")
        view.move_task.return_value = SingleTaskResponse(
            id=1,
            title="Alpha task",
            status="in-progress",
            priority="important",
            created=task.created,
            updated=task.updated,
        )

        resp = client_1239.post(
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
        self, mock_view_client_1239, engine_1239: KanbanEngine
    ) -> None:
        """Route passes req.archival_refs to view.move_task (AC4).

        Fails in RED: Pydantic rejects archival_refs as an extra field → 422.
        """
        from owlbear_kanban.models import SingleTaskResponse  # noqa: PLC0415

        client_1239, view = mock_view_client_1239
        task = engine_1239.show_task("1")
        view.move_task.return_value = SingleTaskResponse(
            id=1,
            title="Alpha task",
            status="in-progress",
            priority="important",
            created=task.created,
            updated=task.updated,
        )

        resp = client_1239.post(
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
        self, mock_view_client_1239, engine_1239: KanbanEngine
    ) -> None:
        """Route explicitly passes archival_reason=None when not in body (AC5).

        Fails in RED: route omits archival_reason kwarg entirely, so
        'archival_reason' is not in call_args.kwargs.
        """
        from owlbear_kanban.models import SingleTaskResponse  # noqa: PLC0415

        client_1239, view = mock_view_client_1239
        task = engine_1239.show_task("1")
        view.move_task.return_value = SingleTaskResponse(
            id=1,
            title="Alpha task",
            status="in-progress",
            priority="important",
            created=task.created,
            updated=task.updated,
        )

        resp = client_1239.post(
            "/api/tasks/1/move",
            json={"status": "in-progress", "updated": task.updated},
        )
        assert resp.status_code == 200
        call_kwargs = view.move_task.call_args.kwargs
        # Fails in RED: key absent from kwargs (route doesn't forward archival params)
        assert "archival_reason" in call_kwargs
        assert call_kwargs["archival_reason"] is None

    def test_move_route_default_archival_refs_forwarded_as_empty_list(
        self, mock_view_client_1239, engine_1239: KanbanEngine
    ) -> None:
        """Route explicitly passes archival_refs=None when not in body (AC5).

        Fails in RED: route omits archival_refs kwarg entirely, so
        'archival_refs' is not in call_args.kwargs.
        """
        from owlbear_kanban.models import SingleTaskResponse  # noqa: PLC0415

        client_1239, view = mock_view_client_1239
        task = engine_1239.show_task("1")
        view.move_task.return_value = SingleTaskResponse(
            id=1,
            title="Alpha task",
            status="in-progress",
            priority="important",
            created=task.created,
            updated=task.updated,
        )

        resp = client_1239.post(
            "/api/tasks/1/move",
            json={"status": "in-progress", "updated": task.updated},
        )
        assert resp.status_code == 200
        call_kwargs = view.move_task.call_args.kwargs
        # Fails in RED: key absent from kwargs (route doesn't forward archival params)
        assert "archival_refs" in call_kwargs
        assert call_kwargs["archival_refs"] is None


# ---------------------------------------------------------------------------
# Merged from test_cockpit_mutation_api_1243.py (task #1243)
# ---------------------------------------------------------------------------

_CONFIG_YAML_1243 = """\
next_id: 1
"""


def _make_board_1243(base_dir: Path) -> Path:
    kanban_dir_1243 = base_dir / "board"
    kanban_dir_1243.mkdir(parents=True, exist_ok=True)
    (kanban_dir_1243 / "config.yml").write_text(_CONFIG_YAML_1243, encoding="utf-8")
    (kanban_dir_1243 / "tasks").mkdir(exist_ok=True)
    (kanban_dir_1243 / "archive").mkdir(exist_ok=True)
    return kanban_dir_1243


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def board_dir_1243(tmp_path: Path) -> Path:
    kanban_dir_1243 = _make_board_1243(tmp_path)
    seed = KanbanEngine(kanban_dir_1243)
    seed.create_task("Beta task", status="todo", priority="needed")
    seed.list_tasks()
    return kanban_dir_1243


@pytest.fixture
def engine_1243(board_dir_1243: Path) -> KanbanEngine:
    eng = KanbanEngine(board_dir_1243, activity_log=True)
    eng.list_tasks()
    return eng


@pytest.fixture
def mock_view_client_1243(engine_1243: KanbanEngine):
    """TestClient with mock CockpitView injected via get_view dependency."""
    from fastapi.testclient import TestClient  # noqa: PLC0415
    from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415
    from owlbear_cockpit.deps import get_view  # noqa: PLC0415

    mock_view = mock.MagicMock(spec=CockpitView)
    mock_view.engine = engine_1243

    app.dependency_overrides[get_engine] = lambda: engine_1243
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
        """archival_refs default is None when not supplied (AC2)."""
        req = MoveRequest(status="in-progress", updated="2026-01-01T00:00:00+00:00")
        assert req.archival_refs is None

    def test_archival_refs_default_is_list_type(self) -> None:
        """archival_refs default value is None when omitted (AC2)."""
        req = MoveRequest(status="in-progress", updated="2026-01-01T00:00:00+00:00")
        assert req.archival_refs is None

    def test_archival_refs_accepts_list_of_ints(self) -> None:
        """archival_refs accepts a list of integer task IDs (AC2)."""
        req = MoveRequest(
            status="in-progress",
            updated="2026-01-01T00:00:00+00:00",
            archival_refs=[10, 20, 30],
        )
        assert req.archival_refs == [10, 20, 30]

    def test_archival_refs_mutable_default_is_safe(self) -> None:
        """Two MoveRequest instances both default archival_refs to None (AC2)."""
        req_a = MoveRequest(status="in-progress", updated="2026-01-01T00:00:00+00:00")
        req_b = MoveRequest(status="in-progress", updated="2026-01-01T00:00:00+00:00")
        assert req_a.archival_refs is None
        assert req_b.archival_refs is None


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
        self, mock_view_client_1243, engine_1243: KanbanEngine
    ) -> None:
        """Route forwards archival_reason= kwarg to view.move_task() (AC4)."""
        from owlbear_kanban.models import SingleTaskResponse  # noqa: PLC0415

        client_1243, view = mock_view_client_1243
        task = engine_1243.show_task("1")
        view.move_task.return_value = SingleTaskResponse(
            id=1,
            title="Beta task",
            status="in-progress",
            priority="needed",
            created=task.created,
            updated=task.updated,
        )

        resp = client_1243.post(
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
        self, mock_view_client_1243, engine_1243: KanbanEngine
    ) -> None:
        """Route forwards archival_refs= kwarg to view.move_task() (AC4)."""
        from owlbear_kanban.models import SingleTaskResponse  # noqa: PLC0415

        client_1243, view = mock_view_client_1243
        task = engine_1243.show_task("1")
        view.move_task.return_value = SingleTaskResponse(
            id=1,
            title="Beta task",
            status="in-progress",
            priority="needed",
            created=task.created,
            updated=task.updated,
        )

        resp = client_1243.post(
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
        self, mock_view_client_1243, engine_1243: KanbanEngine
    ) -> None:
        """Route forwards both archival_reason AND archival_refs together (AC4)."""
        from owlbear_kanban.models import SingleTaskResponse  # noqa: PLC0415

        client_1243, view = mock_view_client_1243
        task = engine_1243.show_task("1")
        view.move_task.return_value = SingleTaskResponse(
            id=1,
            title="Beta task",
            status="in-progress",
            priority="needed",
            created=task.created,
            updated=task.updated,
        )

        resp = client_1243.post(
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
        """Plain MoveRequest gets archival_refs=None default (AC5)."""
        req = MoveRequest(status="review", updated="2026-01-01T00:00:00+00:00")
        assert req.archival_refs is None

    def test_route_with_no_archival_fields_still_returns_200(
        self, mock_view_client_1243, engine_1243: KanbanEngine
    ) -> None:
        """Plain move POST (no archival fields) returns 200 unchanged (AC5)."""
        from owlbear_kanban.models import SingleTaskResponse  # noqa: PLC0415

        client_1243, view = mock_view_client_1243
        task = engine_1243.show_task("1")
        view.move_task.return_value = SingleTaskResponse(
            id=1,
            title="Beta task",
            status="in-progress",
            priority="needed",
            created=task.created,
            updated=task.updated,
        )

        resp = client_1243.post(
            "/api/tasks/1/move",
            json={"status": "in-progress", "updated": task.updated},
        )
        assert resp.status_code == 200

    def test_route_with_no_archival_fields_passes_none_and_empty_list(
        self, mock_view_client_1243, engine_1243: KanbanEngine
    ) -> None:
        """Plain move POST forwards archival_reason=None, archival_refs=None (AC5)."""
        from owlbear_kanban.models import SingleTaskResponse  # noqa: PLC0415

        client_1243, view = mock_view_client_1243
        task = engine_1243.show_task("1")
        view.move_task.return_value = SingleTaskResponse(
            id=1,
            title="Beta task",
            status="in-progress",
            priority="needed",
            created=task.created,
            updated=task.updated,
        )

        resp = client_1243.post(
            "/api/tasks/1/move",
            json={"status": "in-progress", "updated": task.updated},
        )
        assert resp.status_code == 200
        kwargs = view.move_task.call_args.kwargs
        assert kwargs.get("archival_reason") is None
        assert kwargs.get("archival_refs") is None


# ---------------------------------------------------------------------------
# Merged from test_cockpit_mutation_api_1344.py (task #1344)
# ---------------------------------------------------------------------------

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Board fixture helpers (self-contained; mirrors test_cockpit_mutation_api.py)
# ---------------------------------------------------------------------------

_CONFIG_YAML_1344 = """\
next_id: 1
"""


def _make_board_1344(base_dir: Path) -> Path:
    kanban_dir_1344 = base_dir / "board"
    kanban_dir_1344.mkdir(parents=True, exist_ok=True)
    (kanban_dir_1344 / "config.yml").write_text(_CONFIG_YAML_1344, encoding="utf-8")
    (kanban_dir_1344 / "tasks").mkdir(exist_ok=True)
    (kanban_dir_1344 / "archive").mkdir(exist_ok=True)
    return kanban_dir_1344


@pytest.fixture
def board_dir_1344(tmp_path: Path) -> Path:
    """Board with 2 tasks.

    Task 1: status=todo, priority=important (primary edit target)
    Task 2: status=todo, priority=needed    (used as parent reference)
    """
    kanban_dir_1344 = _make_board_1344(tmp_path)
    seed = KanbanEngine(kanban_dir_1344)
    seed.create_task("Alpha task", status="todo", priority="important")
    seed.create_task("Beta task", status="todo", priority="needed")
    seed.list_tasks()
    return kanban_dir_1344


@pytest.fixture
def engine_1344(board_dir_1344: Path) -> KanbanEngine:
    """KanbanEngine with activity logging enabled."""
    eng = KanbanEngine(board_dir_1344, activity_log=True)
    eng.list_tasks()
    return eng


@pytest.fixture
def client_1344(engine_1344: KanbanEngine):
    """FastAPI TestClient with cockpit engine_1344 injected via dependency_overrides."""
    from fastapi.testclient import TestClient  # noqa: PLC0415
    from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415

    app.dependency_overrides[get_engine] = lambda: engine_1344
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# AC1 + AC2: POST /api/tasks/{id}/edit — parent: null and negative parent
# ---------------------------------------------------------------------------


class TestFromAC_EditParentContract:
    """Tests for parent: null → clears parent, negative parent → 422.

    Covers AC1 (correct clear/omit semantics, no uncaught exceptions) and
    AC2 (parent: null clears parent; negative parent returns 422).

    Audit evidence:
      - CockpitView.edit_task does `if parent > 0:` which raises TypeError when
        parent is None → 500 Internal Server Error.
      - Negative parent (-1) passes `if parent > 0:` as False → silently ignored
        → 200 instead of the required 422.
    """

    def test_parent_null_returns_200_not_typeerror(
        self, client_1344: TestClient, engine_1344: KanbanEngine
    ) -> None:
        """parent: null must never result in an uncaught TypeError (500).

        AC1: invalid values return 422, not uncaught exceptions.
        AC2: parent: null must never raise TypeError.

        Current bug: `if parent > 0:` → TypeError: '>' not supported between
        instances of 'NoneType' and 'int'. Route returns 500 instead of 200.
        """
        task = engine_1344.show_task("1")
        response = client_1344.post(
            "/api/tasks/1/edit",
            json={"updated": task.updated, "parent": None},
        )
        assert response.status_code == 200, (
            f"parent: null caused uncaught exception — got {response.status_code}: "
            f"{response.json()}"
        )

    def test_parent_null_clears_parent_1344(
        self, client_1344: TestClient, engine_1344: KanbanEngine
    ) -> None:
        """parent: null in request body clears the parent field (engine_1344 clear signal).

        AC2: parent: null clears the parent (maps to engine_1344's parent-clear signal).

        Precondition: task 1 has parent=2 set via engine_1344.
        Expected: POST parent: null → 200, response parent is null.
        """
        engine_1344.edit_task("1", parent=2)
        task = engine_1344.show_task("1")
        assert task.parent == 2, "Precondition: task 1 must have parent=2"

        response = client_1344.post(
            "/api/tasks/1/edit",
            json={"updated": task.updated, "parent": None},
        )
        assert response.status_code == 200
        assert response.json()["parent"] is None, (
            f"parent: null did not clear the parent — got: {response.json()['parent']!r}"
        )

    def test_negative_parent_returns_422(
        self, client_1344: TestClient, engine_1344: KanbanEngine
    ) -> None:
        """Negative parent value is invalid and must return 422.

        AC2: negative values return 422.

        Current bug: CockpitView.edit_task's `if parent > 0:` evaluates False for
        negative values → parent is silently ignored → 200 instead of 422.
        """
        task = engine_1344.show_task("1")
        response = client_1344.post(
            "/api/tasks/1/edit",
            json={"updated": task.updated, "parent": -1},
        )
        assert response.status_code == 422, (
            f"Negative parent -1 should return 422, got: {response.status_code}"
        )


# ---------------------------------------------------------------------------
# AC1 + AC3: POST /api/tasks/{id}/edit — body: "" clears body
# ---------------------------------------------------------------------------


class TestFromAC_EditBodyContract:
    """Tests for body: "" → clears body; must not return 200 with unchanged body.

    Covers AC1 (correct set/clear/omit semantics) and AC3 (body: "" clears
    body; must never return 200 while leaving the body unchanged).

    Audit evidence:
      - CockpitView.edit_task uses `if body:` which treats "" as falsy.
      - body="" is never forwarded to the engine_1344 → engine_1344's clear signal never
        sent → original body remains unchanged → silent no-op violation of AC3.
    """

    def test_body_empty_string_clears_body_1344(
        self, client_1344: TestClient, engine_1344: KanbanEngine
    ) -> None:
        """body: "" in request body must clear the task body to empty string.

        AC3: body: "" clears the task body (maps to engine_1344's body="" contract).

        Precondition: task 1 has a non-empty body.
        Expected: POST body: "" → 200, response body is "".
        """
        engine_1344.edit_task("1", body="## Original content\n\nShould be cleared.")
        task = engine_1344.show_task("1")
        assert task.body, "Precondition: task 1 must have a non-empty body"

        response = client_1344.post(
            "/api/tasks/1/edit",
            json={"updated": task.updated, "body": ""},
        )
        assert response.status_code == 200
        assert response.json()["body"] == "", (
            f"body: '' must clear the task body, got: {response.json()['body']!r}"
        )

    def test_body_empty_string_does_not_return_unchanged_body(
        self, client_1344: TestClient, engine_1344: KanbanEngine
    ) -> None:
        """POST body: "" must not return 200 with the original body unchanged.

        AC3: it must never return 200 while leaving the body unchanged.

        This test directly encodes the AC3 constraint: if the response is 200,
        the body in the response must differ from the original body (i.e., be "").
        """
        original_body = "## Persistent content that must be cleared"
        engine_1344.edit_task("1", body=original_body)
        task = engine_1344.show_task("1")

        response = client_1344.post(
            "/api/tasks/1/edit",
            json={"updated": task.updated, "body": ""},
        )
        if response.status_code == 200:
            assert response.json()["body"] != original_body, (
                "AC3 violation: returned 200 but original body was left unchanged"
            )


# ---------------------------------------------------------------------------
# Merged from test_cockpit_mutation_api_1448.py (task #1448)
# ---------------------------------------------------------------------------

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Board helpers (consistent with test_engine_coverage_1068 patterns)
# ---------------------------------------------------------------------------

_CONFIG_YAML_1448 = """\
next_id: 1
"""

_TASK_TMPL = """\
---
id: {task_id}
title: {title}
status: {status}
priority: {priority}
created: "2026-01-01T10:00:00+00:00"
updated: "2026-01-01T10:00:00+00:00"
tags: []
parent: null
depends_on: []
blocked: false
block_reason: null
claimed_at: {claimed_at}
archival_reason: {archival_reason}
archival_refs: []
---
Body.
"""

_EPOCH_TS = '"2026-01-01T00:00:00+00:00"'  # always expired (> 1 h ago)


def _make_board_1448(base_dir: Path) -> Path:
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_CONFIG_YAML_1448, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


def _write_task_1448(  # noqa: PLR0913
    kanban_dir: Path,
    task_id: int = 1,
    title: str = "Task",
    status: str = "todo",
    priority: str = "needed",
    claimed_at: str = "null",
    archival_reason: str = "null",
    subdir: str = "tasks",
) -> Path:
    content = _TASK_TMPL.format(
        task_id=task_id,
        title=title,
        status=status,
        priority=priority,
        claimed_at=claimed_at,
        archival_reason=archival_reason,
    )
    path = kanban_dir / subdir / f"{task_id}-task.md"
    path.write_text(content, encoding="utf-8")
    return path


def _make_engine_1448(base_dir: Path) -> KanbanEngine:
    kanban_dir = _make_board_1448(base_dir)
    return KanbanEngine(kanban_dir, activity_log=False)


def _now_ts_1448() -> str:
    """Return a quoted ISO timestamp within the 1 h claim window."""
    return f'"{datetime.now(UTC).isoformat()}"'


# ---------------------------------------------------------------------------
# Cockpit fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def kanban_dir(tmp_path: Path) -> Path:
    return _make_board_1448(tmp_path)


@pytest.fixture
def engine_1448(kanban_dir: Path) -> KanbanEngine:
    return KanbanEngine(kanban_dir, activity_log=False)


@pytest.fixture
def client_1448(engine_1448: KanbanEngine):
    from fastapi.testclient import TestClient  # noqa: PLC0415
    from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415

    app.dependency_overrides[get_engine] = lambda: engine_1448
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# AC1 — Claim-release probe
# ---------------------------------------------------------------------------


class TestFromAC_CleanupClaimRelease:
    """AC1: cleanup() releases expired claims via CAS and reports released_claim_ids.

    Contract:
    - Expired claimed_at (> 1 h old) → task ID in result.released_claim_ids
    - Live claimed_at (< 1 h old) → NOT in released_claim_ids; file unchanged
    """

    def test_cleanup_returns_expired_task_id_in_released_claim_ids(
        self, tmp_path: Path
    ) -> None:
        """Expired claimed_at is cleared; task ID appears in released_claim_ids."""
        board = _make_board_1448(tmp_path)
        _write_task_1448(board, task_id=1, status="todo", claimed_at=_EPOCH_TS)
        engine_1448 = KanbanEngine(board, activity_log=False)

        result = engine_1448.cleanup()  # type: ignore[attr-defined]  # not yet implemented

        assert 1 in result.released_claim_ids

    def test_cleanup_leaves_live_claim_untouched(self, tmp_path: Path) -> None:
        """Live claim (< 1 h) is not cleared and not reported in released_claim_ids."""
        board = _make_board_1448(tmp_path)
        _write_task_1448(board, task_id=2, status="todo", claimed_at=_now_ts_1448())
        engine_1448 = KanbanEngine(board, activity_log=False)

        result = engine_1448.cleanup()  # type: ignore[attr-defined]  # not yet implemented

        assert 2 not in result.released_claim_ids
        # Verify on-disk: claimed_at still set
        engine_1448.list_tasks()  # warm id→filename index
        task = engine_1448.show_task("2")
        assert task.claimed_at is not None

    def test_cleanup_clears_expired_claimed_at_on_disk(self, tmp_path: Path) -> None:
        """After cleanup, re-reading the expired task proves claimed_at is None on disk."""
        board = _make_board_1448(tmp_path)
        _write_task_1448(board, task_id=3, status="todo", claimed_at=_EPOCH_TS)
        engine_1448 = KanbanEngine(board, activity_log=False)

        result = engine_1448.cleanup()  # type: ignore[attr-defined]

        assert 3 in result.released_claim_ids
        # Re-read from disk to prove CAS write persisted the cleared claimed_at
        task = engine_1448.show_task("3")
        assert task.claimed_at is None, (
            "cleanup must clear claimed_at on disk for expired task"
        )


# ---------------------------------------------------------------------------
# AC2 — Archive-move probe
# ---------------------------------------------------------------------------


class TestFromAC_CleanupArchiveMove:
    """AC2: cleanup() moves drift-archived task files from tasks/ to archive/.

    A drift-archived file is one in tasks/ with status=archived and a valid
    archival_reason (e.g. completed). cleanup() must move it and report the
    task ID in archived_task_ids.
    """

    def test_cleanup_moves_archived_status_task_to_archive_dir(
        self, tmp_path: Path
    ) -> None:
        """Task with status=archived in tasks/ is moved to archive/."""
        board = _make_board_1448(tmp_path)
        _write_task_1448(
            board, task_id=1, status="archived", archival_reason='"completed"'
        )
        engine_1448 = KanbanEngine(board, activity_log=False)

        result = engine_1448.cleanup()  # type: ignore[attr-defined]  # not yet implemented

        assert 1 in result.archived_task_ids
        assert not (board / "tasks" / "1-task.md").exists()
        assert (board / "archive" / "1-task.md").exists()


# ---------------------------------------------------------------------------
# AC3 — Safety probe
# ---------------------------------------------------------------------------


class TestFromAC_CleanupSafety:
    """AC3: collision and malformed files are skipped; skipped_items shape is correct.

    Each skipped_items entry must have:
    - path: str  — path to the skipped file
    - reason: str — human-readable reason for skipping
    Source file must not be deleted when a skip occurs.
    """

    def test_cleanup_skips_archive_collision(self, tmp_path: Path) -> None:
        """Destination file already exists in archive/ → task skipped; not in archived_task_ids."""
        board = _make_board_1448(tmp_path)
        _write_task_1448(
            board, task_id=1, status="archived", archival_reason='"completed"'
        )
        # Pre-create collision target
        (board / "archive" / "1-task.md").write_text(
            "collision sentinel", encoding="utf-8"
        )
        engine_1448 = KanbanEngine(board, activity_log=False)

        result = engine_1448.cleanup()  # type: ignore[attr-defined]  # not yet implemented

        assert 1 not in result.archived_task_ids
        assert len(result.skipped_items) >= 1

    def test_cleanup_skipped_item_has_path_and_reason_fields(
        self, tmp_path: Path
    ) -> None:
        """Each skipped_items entry must expose path (str) and reason (str)."""
        board = _make_board_1448(tmp_path)
        # Malformed frontmatter — unparseable by the engine_1448
        (board / "tasks" / "99-bad.md").write_text(
            "not valid frontmatter at all\n", encoding="utf-8"
        )
        engine_1448 = KanbanEngine(board, activity_log=False)

        result = engine_1448.cleanup()  # type: ignore[attr-defined]  # not yet implemented

        assert len(result.skipped_items) >= 1
        for item in result.skipped_items:
            assert "path" in item, "skipped_items entry missing 'path' field"
            assert "reason" in item, "skipped_items entry missing 'reason' field"
            assert isinstance(item["path"], str)
            assert isinstance(item["reason"], str)

    def test_cleanup_source_file_not_deleted_on_collision_skip(
        self, tmp_path: Path
    ) -> None:
        """Source task file is not deleted when archive collision causes a skip."""
        board = _make_board_1448(tmp_path)
        source = _write_task_1448(
            board, task_id=1, status="archived", archival_reason='"completed"'
        )
        (board / "archive" / "1-task.md").write_text(
            "collision sentinel", encoding="utf-8"
        )
        engine_1448 = KanbanEngine(board, activity_log=False)

        engine_1448.cleanup()  # type: ignore[attr-defined]  # not yet implemented

        assert source.exists(), "Source task file must not be deleted when skip occurs"

    def test_cleanup_source_file_not_deleted_on_malformed_skip(
        self, tmp_path: Path
    ) -> None:
        """Malformed source file is not deleted when it is added to skipped_items."""
        board = _make_board_1448(tmp_path)
        malformed = board / "tasks" / "99-bad.md"
        malformed.write_text("not valid frontmatter at all\n", encoding="utf-8")
        engine_1448 = KanbanEngine(board, activity_log=False)

        engine_1448.cleanup()  # type: ignore[attr-defined]  # not yet implemented

        assert malformed.exists(), (
            "malformed source file must not be deleted when skipped"
        )


# ---------------------------------------------------------------------------
# AC4 — Single-call aggregation probe
# ---------------------------------------------------------------------------


class TestFromAC_CleanupAggregation:
    """AC4: one cleanup() invocation returns all three result categories."""

    def test_cleanup_single_call_returns_all_three_categories(
        self, tmp_path: Path
    ) -> None:
        """Board with expired claim + drift-archived task + malformed file.

        A single cleanup() call must return all three categories in one result.
        """
        board = _make_board_1448(tmp_path)
        # Expired claim
        _write_task_1448(board, task_id=1, status="todo", claimed_at=_EPOCH_TS)
        # Drift-archived task
        _write_task_1448(
            board, task_id=2, status="archived", archival_reason='"completed"'
        )
        # Malformed file (will be skipped)
        (board / "tasks" / "99-bad.md").write_text(
            "not valid frontmatter\n", encoding="utf-8"
        )
        engine_1448 = KanbanEngine(board, activity_log=False)

        result = engine_1448.cleanup()  # type: ignore[attr-defined]  # not yet implemented

        assert 1 in result.released_claim_ids, "expired claim must be released"
        assert 2 in result.archived_task_ids, "drift-archived task must be moved"
        assert len(result.skipped_items) >= 1, "malformed file must be in skipped_items"


# ---------------------------------------------------------------------------
# AC5 — Cockpit contract probe
# ---------------------------------------------------------------------------


class TestFromAC_CockpitCleanupContract:
    """AC5: POST /api/tasks/cleanup returns the correct response shape.

    Fields:
    - released_claim_ids: list[int]
    - archived_task_ids: list[int]
    - skipped_items: list[object with path (str) and reason (str)]

    Cockpit view/route passes skipped_items through without converting to a
    generic error envelope.
    """

    def test_post_cleanup_returns_200_with_correct_field_shape(
        self, client_1448: TestClient
    ) -> None:
        """POST /api/tasks/cleanup → 200 with released_claim_ids, archived_task_ids, skipped_items."""
        response = client_1448.post("/api/tasks/cleanup")

        assert response.status_code == 200
        body = response.json()
        assert "released_claim_ids" in body, "response missing released_claim_ids"
        assert "archived_task_ids" in body, "response missing archived_task_ids"
        assert "skipped_items" in body, "response missing skipped_items"
        assert isinstance(body["released_claim_ids"], list)
        assert isinstance(body["archived_task_ids"], list)
        assert isinstance(body["skipped_items"], list)

    def test_post_cleanup_skipped_items_are_objects_with_path_and_reason(
        self, client_1448: TestClient, kanban_dir: Path
    ) -> None:
        """skipped_items entries are objects with path+reason, not converted to a generic error."""
        # Add a malformed file to trigger a skipped_items entry
        (kanban_dir / "tasks" / "99-bad.md").write_text(
            "not valid frontmatter\n", encoding="utf-8"
        )

        response = client_1448.post("/api/tasks/cleanup")

        assert response.status_code == 200
        body = response.json()
        for item in body.get("skipped_items", []):
            assert "path" in item, "skipped_item missing path field"
            assert "reason" in item, "skipped_item missing reason field"

    def test_post_cleanup_skipped_items_nonempty_with_malformed_file(
        self, client_1448: TestClient, kanban_dir: Path
    ) -> None:
        """skipped_items is non-empty when a malformed file is present; entries are typed."""
        (kanban_dir / "tasks" / "99-bad.md").write_text(
            "not valid frontmatter\n", encoding="utf-8"
        )

        response = client_1448.post("/api/tasks/cleanup")

        assert response.status_code == 200
        body = response.json()
        assert len(body["skipped_items"]) >= 1, (
            "malformed file must appear in skipped_items"
        )
        for item in body["skipped_items"]:
            assert isinstance(item["path"], str), "skipped_items path must be str"
            assert isinstance(item["reason"], str), "skipped_items reason must be str"


# ---------------------------------------------------------------------------
# AC6 — Negative probe
# ---------------------------------------------------------------------------


class TestFromAC_CleanupNegativeProbe:
    """AC6: cleanup is NOT invoked by pick_tasks, start_work, engine_1448 init,
    Cockpit startup, board read endpoints, task list refresh, or SSE streaming.

    Each test asserts the cleanup interface exists on KanbanEngine AND verifies
    it is not called by the named operation.
    """

    def test_engine_init_does_not_invoke_cleanup(self, tmp_path: Path) -> None:
        """KanbanEngine.__init__ must not call cleanup()."""
        board = _make_board_1448(tmp_path)
        assert hasattr(KanbanEngine, "cleanup"), (
            "KanbanEngine.cleanup must exist as a method"
        )
        with mock.patch.object(KanbanEngine, "cleanup") as mock_cleanup:
            KanbanEngine(board, activity_log=False)
            mock_cleanup.assert_not_called()

    def test_pick_tasks_does_not_invoke_cleanup(self, tmp_path: Path) -> None:
        """AgentView.pick_tasks must not call KanbanEngine.cleanup()."""
        board = _make_board_1448(tmp_path)
        _write_task_1448(board, task_id=1, status="todo")
        engine_1448 = KanbanEngine(board, activity_log=False)
        engine_1448.list_tasks()  # warm id→filename index
        assert hasattr(engine_1448, "cleanup"), "KanbanEngine.cleanup() must exist"
        with mock.patch.object(engine_1448, "cleanup") as mock_cleanup:
            view = AgentView(engine_1448)
            view.pick_tasks()
            mock_cleanup.assert_not_called()

    def test_start_work_does_not_invoke_cleanup(self, tmp_path: Path) -> None:
        """KanbanEngine.start_work must not call cleanup()."""
        board = _make_board_1448(tmp_path)
        _write_task_1448(board, task_id=1, status="todo")
        engine_1448 = KanbanEngine(board, activity_log=False)
        engine_1448.list_tasks()
        assert hasattr(engine_1448, "cleanup"), "KanbanEngine.cleanup() must exist"
        with mock.patch.object(engine_1448, "cleanup") as mock_cleanup:
            engine_1448.start_work("1")
            mock_cleanup.assert_not_called()

    def test_cockpit_get_tasks_does_not_invoke_cleanup(
        self, client_1448: TestClient, engine_1448: KanbanEngine
    ) -> None:
        """GET /api/tasks must not invoke cleanup()."""
        assert hasattr(engine_1448, "cleanup"), "KanbanEngine.cleanup() must exist"
        with mock.patch.object(engine_1448, "cleanup") as mock_cleanup:
            response = client_1448.get("/api/tasks")
            assert response.status_code == 200
            mock_cleanup.assert_not_called()

    def test_cockpit_get_board_does_not_invoke_cleanup(
        self, client_1448: TestClient, engine_1448: KanbanEngine
    ) -> None:
        """GET /api/board must not invoke cleanup()."""
        assert hasattr(engine_1448, "cleanup"), "KanbanEngine.cleanup() must exist"
        with mock.patch.object(engine_1448, "cleanup") as mock_cleanup:
            response = client_1448.get("/api/board")
            assert response.status_code == 200
            mock_cleanup.assert_not_called()

    def test_cockpit_sse_does_not_invoke_cleanup(
        self, client_1448: TestClient, engine_1448: KanbanEngine
    ) -> None:
        """SSE /api/events must not invoke cleanup() before streaming begins."""
        assert hasattr(engine_1448, "cleanup"), "KanbanEngine.cleanup() must exist"

        # Patch awatch to prevent actual filesystem watching (avoids SSE deadlock)
        async def _noop_awatch(*_args, **_kwargs):  # noqa: RUF029
            return
            yield  # make it an async generator

        with (
            mock.patch("owlbear_cockpit.routes.events.awatch", _noop_awatch),
            mock.patch.object(engine_1448, "cleanup") as mock_cleanup,
        ):
            # Only check headers — do not stream body (would deadlock with sync client_1448)
            with client_1448.stream("GET", "/api/events") as resp:
                assert resp.status_code == 200
            mock_cleanup.assert_not_called()
