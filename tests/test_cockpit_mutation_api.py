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
  - All mutations write entry to activity.jsonl with actor='cockpit'
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from owlbear_kanban import KanbanEngine

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Board fixture helpers
# ---------------------------------------------------------------------------

_CONFIG_YAML = """\
version: 10
board:
  name: TestBoard
tasks_dir: tasks
statuses:
- name: research
- name: backlog
- name: todo
- name: in-progress
- name: review
- name: docs
- name: done
priorities:
- someday
- nice-to-have
- important
- needed
- critical
defaults:
  status: research
  priority: important
claim_timeout: 1h
next_id: 1
archive_dir: archive
activity_log: false
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
    seed = KanbanEngine(kanban_dir, agent_name="seed")
    seed.create_task("Alpha task", status="todo", priority="important")
    seed.create_task("Beta task", status="in-progress", priority="needed")
    seed.create_task("Gamma task", status="todo", priority="someday")
    seed.list_tasks()  # populate id→filename cache
    seed.claim_task("2")
    return kanban_dir


@pytest.fixture
def engine(board_dir: Path) -> KanbanEngine:
    """KanbanEngine with agent_name='cockpit' and activity logging enabled."""
    eng = KanbanEngine(board_dir, agent_name="cockpit", activity_log=True)
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

    def test_move_happy_path_returns_200(self, client: TestClient) -> None:
        """Happy path: move task 1 from 'todo' to 'in-progress' returns 200."""
        response = client.post("/api/tasks/1/move", json={"status": "in-progress"})
        assert response.status_code == 200

    def test_move_returns_updated_task_object(self, client: TestClient) -> None:
        """Response body is a task object with the new status applied."""
        response = client.post("/api/tasks/1/move", json={"status": "review"})
        assert response.status_code == 200
        body = response.json()
        assert body["id"] == 1
        assert body["status"] == "review"
        assert "title" in body
        assert "priority" in body

    def test_move_invalid_target_status_returns_422(self, client: TestClient) -> None:
        """Unknown status string not in valid_transitions → 422."""
        response = client.post("/api/tasks/1/move", json={"status": "not-a-real-status"})
        assert response.status_code == 422

    def test_move_same_status_returns_422(self, client: TestClient, engine: KanbanEngine) -> None:
        """Moving to current status is excluded from valid_transitions → 422."""
        task = engine.show_task("1")
        response = client.post("/api/tasks/1/move", json={"status": task.status})
        assert response.status_code == 422

    def test_move_nonexistent_task_returns_404(self, client: TestClient) -> None:
        """Non-existent task ID returns 404 with ID in detail."""
        response = client.post("/api/tasks/999/move", json={"status": "in-progress"})
        assert response.status_code == 404
        assert "999" in response.json()["detail"]


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
        assert "999" in response.json()["detail"]


# ---------------------------------------------------------------------------
# AC: POST /api/tasks/{id}/release
# ---------------------------------------------------------------------------


class TestFromAC_ReleaseTask:
    """Tests for POST /api/tasks/{id}/release.

    Covers: happy path on claimed task (200 + task object), unclaimed task
    (409 Conflict per AC refinement), and non-existent task (404).
    """

    def test_release_claimed_task_returns_200(self, client: TestClient) -> None:
        """Happy path: release pre-claimed task 2 returns 200."""
        response = client.post("/api/tasks/2/release")
        assert response.status_code == 200

    def test_release_returns_task_object_shape(self, client: TestClient) -> None:
        """Release response body matches the TaskDetailOut shape (same as GET /tasks/{id})."""
        response = client.post("/api/tasks/2/release")
        assert response.status_code == 200
        body = response.json()
        assert body["id"] == 2
        assert "title" in body
        assert "status" in body
        assert "priority" in body
        assert "updated" in body

    def test_release_unclaimed_task_returns_409(self, client: TestClient) -> None:
        """Releasing an unclaimed task is a state conflict → 409 (AC refinement #1)."""
        response = client.post("/api/tasks/1/release")  # task 1 is unclaimed
        assert response.status_code == 409

    def test_release_nonexistent_task_returns_404(self, client: TestClient) -> None:
        """Non-existent task ID returns 404 with ID in detail."""
        response = client.post("/api/tasks/999/release")
        assert response.status_code == 404
        assert "999" in response.json()["detail"]


# ---------------------------------------------------------------------------
# AC: All mutations write activity.jsonl with actor='cockpit'
# ---------------------------------------------------------------------------


class TestFromAC_AuditLogging:
    """Tests verifying that every mutation endpoint writes an activity log entry.

    Each mutation must produce at least one entry in activity.jsonl with
    actor='cockpit'. Engine is constructed with agent_name='cockpit' and
    activity_log=True so entries are written at all.
    """

    def test_move_writes_activity_log_actor_cockpit(
        self, client: TestClient, board_dir: Path
    ) -> None:
        """Move mutation writes activity.jsonl entry with actor='cockpit'."""
        client.post("/api/tasks/1/move", json={"status": "in-progress"})
        activity_file = board_dir / "activity.jsonl"
        assert activity_file.exists(), "activity.jsonl must be created by move mutation"
        entries = [json.loads(line) for line in activity_file.read_text().splitlines() if line.strip()]
        cockpit_entries = [e for e in entries if e.get("actor") == "cockpit"]
        assert len(cockpit_entries) >= 1, "At least one activity entry must have actor='cockpit'"

    def test_edit_writes_activity_log_actor_cockpit(
        self, client: TestClient, engine: KanbanEngine, board_dir: Path
    ) -> None:
        """Edit mutation writes activity.jsonl entry with actor='cockpit'."""
        task = engine.show_task("1")
        client.post(
            "/api/tasks/1/edit",
            json={"updated": task.updated, "title": "Audit log test title"},
        )
        activity_file = board_dir / "activity.jsonl"
        assert activity_file.exists(), "activity.jsonl must be created by edit mutation"
        entries = [json.loads(line) for line in activity_file.read_text().splitlines() if line.strip()]
        cockpit_entries = [e for e in entries if e.get("actor") == "cockpit"]
        assert len(cockpit_entries) >= 1, "At least one activity entry must have actor='cockpit'"

    def test_release_writes_activity_log_actor_cockpit(
        self, client: TestClient, board_dir: Path
    ) -> None:
        """Release mutation writes activity.jsonl entry with actor='cockpit'."""
        client.post("/api/tasks/2/release")  # task 2 is pre-claimed
        activity_file = board_dir / "activity.jsonl"
        assert activity_file.exists(), "activity.jsonl must be created by release mutation"
        entries = [json.loads(line) for line in activity_file.read_text().splitlines() if line.strip()]
        cockpit_entries = [e for e in entries if e.get("actor") == "cockpit"]
        assert len(cockpit_entries) >= 1, "At least one activity entry must have actor='cockpit'"


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
        self, client: TestClient, board_dir: Path
    ) -> None:
        """Move audit log entry has action='move' and task_id matching the mutated task."""
        client.post("/api/tasks/1/move", json={"status": "in-progress"})
        entries = [
            json.loads(line)
            for line in (board_dir / "activity.jsonl").read_text().splitlines()
            if line.strip()
        ]
        cockpit_entries = [e for e in entries if e.get("actor") == "cockpit"]
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
        cockpit_entries = [e for e in entries if e.get("actor") == "cockpit"]
        assert cockpit_entries[0]["action"] == "edit"
        assert cockpit_entries[0]["task_id"] == 1

    def test_release_audit_log_has_correct_action_and_task_id(
        self, client: TestClient, board_dir: Path
    ) -> None:
        """Release audit log entry has action='release' and task_id matching the mutated task."""
        client.post("/api/tasks/2/release")  # task 2 is pre-claimed
        entries = [
            json.loads(line)
            for line in (board_dir / "activity.jsonl").read_text().splitlines()
            if line.strip()
        ]
        cockpit_entries = [e for e in entries if e.get("actor") == "cockpit"]
        assert cockpit_entries[0]["action"] == "release"
        assert cockpit_entries[0]["task_id"] == 2
