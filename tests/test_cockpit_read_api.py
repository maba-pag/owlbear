"""Failing tests for cockpit read-only HTTP endpoints (#928).

RED phase — all tests must fail until routes are implemented in GREEN (#930).

AC coverage:
  - GET /api/board returns board config (statuses, priorities, valid_transitions)
  - GET /api/tasks returns TaskSummary list + mtime integer
  - GET /api/tasks with status/priority/tag/blocked filters
  - GET /api/tasks/{id} returns full task with updated field
  - GET /api/tasks/{id} for non-existent ID returns 404
  - GET /api/sessions?filter=active returns session list
  - GET /api/sessions?filter=all returns all sessions
  - Mtime: repeated GET returns same mtime; modifying a file changes it
"""

from __future__ import annotations

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

_STATUSES = ["research", "backlog", "todo", "in-progress", "review", "docs", "done"]
_PRIORITIES = ["someday", "nice-to-have", "important", "needed", "critical"]


def _make_board(base_dir: Path) -> Path:
    """Create a minimal kanban board. Returns kanban_dir."""
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
    """Minimal kanban board with 3 tasks covering filter dimensions.

    Task 1: status=todo,       priority=important, tags=[alpha], blocked=False
    Task 2: status=review,     priority=critical,  tags=[beta],  blocked=False
    Task 3: status=in-progress,priority=needed,    tags=[gamma], blocked=True
    """
    kanban_dir = _make_board(tmp_path)
    seed_engine = KanbanEngine(kanban_dir, agent_name="seed")
    seed_engine.create_task("Alpha task", status="todo", priority="important", tags=["alpha"])
    seed_engine.create_task("Beta task", status="review", priority="critical", tags=["beta"])
    seed_engine.create_task("Gamma blocked", status="in-progress", priority="needed", tags=["gamma"])
    # Mark task 3 as blocked — list_tasks first to populate id→filename cache
    seed_engine.list_tasks()
    seed_engine.edit_task("3", blocked=True, block_reason="waiting on dependency")
    return kanban_dir


@pytest.fixture
def engine(board_dir: Path) -> KanbanEngine:
    """KanbanEngine pointed at the test board, cache pre-warmed."""
    eng = KanbanEngine(board_dir, agent_name="test-cockpit")
    eng.list_tasks()  # populate id→filename cache
    return eng


@pytest.fixture
def client(engine: KanbanEngine):
    """FastAPI TestClient with engine injected via dependency_overrides.

    In RED phase, ``get_engine`` does not exist in ``owlbear_cockpit.main``
    so this fixture raises ImportError — all tests using it will ERROR (RED).
    """
    from fastapi.testclient import TestClient  # noqa: PLC0415
    from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415  # ImportError in RED

    app.dependency_overrides[get_engine] = lambda: engine
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# AC: GET /api/board
# ---------------------------------------------------------------------------


class TestFromAC_BoardConfig:
    """Tests for the GET /api/board endpoint.

    Covers: statuses, priorities (config-ordered), and valid_transitions map.
    """

    def test_board_endpoint_returns_200(self, client: TestClient) -> None:
        """Happy path: GET /api/board returns HTTP 200."""
        response = client.get("/api/board")
        assert response.status_code == 200

    def test_board_response_includes_statuses_list(self, client: TestClient) -> None:
        """Response body contains a 'statuses' key with a list value."""
        response = client.get("/api/board")
        assert response.status_code == 200
        body = response.json()
        assert "statuses" in body
        assert isinstance(body["statuses"], list)

    def test_board_statuses_preserve_config_order(self, client: TestClient) -> None:
        """Statuses array preserves the config.yml ordering (R1 / AC display-order)."""
        response = client.get("/api/board")
        assert response.status_code == 200
        statuses = response.json()["statuses"]
        names = [s["name"] for s in statuses]
        assert names == _STATUSES

    def test_board_response_includes_priorities_list(self, client: TestClient) -> None:
        """Response body contains a 'priorities' key with a list value."""
        response = client.get("/api/board")
        assert response.status_code == 200
        body = response.json()
        assert "priorities" in body
        assert isinstance(body["priorities"], list)

    def test_board_priorities_preserve_config_order(self, client: TestClient) -> None:
        """Priorities array preserves the config.yml ordering (R1 / AC display-order)."""
        response = client.get("/api/board")
        assert response.status_code == 200
        priorities = response.json()["priorities"]
        assert priorities == _PRIORITIES

    def test_board_response_includes_valid_transitions_dict(self, client: TestClient) -> None:
        """Response body contains a 'valid_transitions' key with a dict value (R1)."""
        response = client.get("/api/board")
        assert response.status_code == 200
        body = response.json()
        assert "valid_transitions" in body
        assert isinstance(body["valid_transitions"], dict)

    def test_board_valid_transitions_maps_every_configured_status(
        self, client: TestClient
    ) -> None:
        """valid_transitions dict has an entry for every configured status (R1)."""
        response = client.get("/api/board")
        assert response.status_code == 200
        vt = response.json()["valid_transitions"]
        assert set(vt.keys()) == set(_STATUSES)

    def test_board_valid_transitions_values_are_lists_of_strings(
        self, client: TestClient
    ) -> None:
        """Each valid_transitions value is a non-empty list of strings (R1)."""
        response = client.get("/api/board")
        assert response.status_code == 200
        vt = response.json()["valid_transitions"]
        for status, targets in vt.items():
            assert isinstance(targets, list), f"targets for {status!r} is not a list"
            assert len(targets) > 0, f"targets for {status!r} is empty"
            for t in targets:
                assert isinstance(t, str), f"target {t!r} for {status!r} is not a string"

    def test_board_valid_transitions_excludes_current_status(
        self, client: TestClient
    ) -> None:
        """Each status is excluded from its own valid_transitions list (R1)."""
        response = client.get("/api/board")
        assert response.status_code == 200
        vt = response.json()["valid_transitions"]
        for status, targets in vt.items():
            assert status not in targets, (
                f"valid_transitions[{status!r}] contains itself: {targets}"
            )


# ---------------------------------------------------------------------------
# AC: GET /api/tasks (list + filters + mtime)
# ---------------------------------------------------------------------------


class TestFromAC_TaskList:
    """Tests for the GET /api/tasks endpoint and query-string filters.

    Filter scope (R3): only status, priority, tag, blocked are tested.
    """

    def test_tasks_endpoint_returns_200(self, client: TestClient) -> None:
        """Happy path: GET /api/tasks returns HTTP 200."""
        response = client.get("/api/tasks")
        assert response.status_code == 200

    def test_tasks_response_has_tasks_list(self, client: TestClient) -> None:
        """Response body contains a 'tasks' key with a list value."""
        response = client.get("/api/tasks")
        assert response.status_code == 200
        body = response.json()
        assert "tasks" in body
        assert isinstance(body["tasks"], list)

    def test_tasks_response_has_mtime_integer(self, client: TestClient) -> None:
        """Response body contains an integer 'mtime' (nanoseconds, R2)."""
        response = client.get("/api/tasks")
        assert response.status_code == 200
        body = response.json()
        assert "mtime" in body
        assert isinstance(body["mtime"], int)

    def test_tasks_each_summary_has_required_fields(self, client: TestClient) -> None:
        """Each task summary has id, title, status, priority fields."""
        response = client.get("/api/tasks")
        assert response.status_code == 200
        tasks = response.json()["tasks"]
        assert len(tasks) > 0, "Board has tasks — list must not be empty"
        for task in tasks:
            for field in ("id", "title", "status", "priority"):
                assert field in task, f"Task summary missing field {field!r}: {task}"

    def test_tasks_filter_by_status_returns_200(self, client: TestClient) -> None:
        """GET /api/tasks?status=review returns HTTP 200."""
        response = client.get("/api/tasks", params={"status": "review"})
        assert response.status_code == 200

    def test_tasks_filter_by_status_returns_only_matching(
        self, client: TestClient
    ) -> None:
        """All tasks in a status-filtered response have the requested status."""
        response = client.get("/api/tasks", params={"status": "review"})
        assert response.status_code == 200
        tasks = response.json()["tasks"]
        assert len(tasks) == 1, f"Expected 1 review task, got {len(tasks)}"
        assert tasks[0]["status"] == "review"

    def test_tasks_filter_by_priority_returns_200(self, client: TestClient) -> None:
        """GET /api/tasks?priority=critical returns HTTP 200."""
        response = client.get("/api/tasks", params={"priority": "critical"})
        assert response.status_code == 200

    def test_tasks_filter_by_priority_returns_only_matching(
        self, client: TestClient
    ) -> None:
        """All tasks in a priority-filtered response have the requested priority."""
        response = client.get("/api/tasks", params={"priority": "critical"})
        assert response.status_code == 200
        tasks = response.json()["tasks"]
        assert len(tasks) == 1, f"Expected 1 critical task, got {len(tasks)}"
        assert tasks[0]["priority"] == "critical"

    def test_tasks_filter_by_tag_returns_200(self, client: TestClient) -> None:
        """GET /api/tasks?tag=alpha returns HTTP 200."""
        response = client.get("/api/tasks", params={"tag": "alpha"})
        assert response.status_code == 200

    def test_tasks_filter_by_tag_returns_only_matching(
        self, client: TestClient
    ) -> None:
        """All tasks in a tag-filtered response include the requested tag."""
        response = client.get("/api/tasks", params={"tag": "alpha"})
        assert response.status_code == 200
        tasks = response.json()["tasks"]
        assert len(tasks) == 1, f"Expected 1 alpha task, got {len(tasks)}"
        assert "alpha" in tasks[0]["tags"]

    def test_tasks_filter_by_blocked_true_returns_200(self, client: TestClient) -> None:
        """GET /api/tasks?blocked=true returns HTTP 200."""
        response = client.get("/api/tasks", params={"blocked": "true"})
        assert response.status_code == 200

    def test_tasks_filter_by_blocked_returns_only_blocked_tasks(
        self, client: TestClient
    ) -> None:
        """All tasks in a blocked=true response have blocked=True."""
        response = client.get("/api/tasks", params={"blocked": "true"})
        assert response.status_code == 200
        tasks = response.json()["tasks"]
        assert len(tasks) == 1, f"Expected 1 blocked task, got {len(tasks)}"
        assert tasks[0]["blocked"] is True


# ---------------------------------------------------------------------------
# AC: GET /api/tasks/{id}
# ---------------------------------------------------------------------------


class TestFromAC_TaskDetail:
    """Tests for the GET /api/tasks/{id} endpoint."""

    def test_task_detail_returns_200(self, client: TestClient) -> None:
        """Happy path: GET /api/tasks/1 for an existing task returns HTTP 200."""
        response = client.get("/api/tasks/1")
        assert response.status_code == 200

    def test_task_detail_has_updated_field(self, client: TestClient) -> None:
        """Task detail response includes an 'updated' timestamp string."""
        response = client.get("/api/tasks/1")
        assert response.status_code == 200
        body = response.json()
        assert "updated" in body
        assert isinstance(body["updated"], str)
        assert len(body["updated"]) > 0

    def test_task_detail_has_full_task_fields(self, client: TestClient) -> None:
        """Task detail response includes all core Task fields (id, title, status, priority, body)."""
        response = client.get("/api/tasks/1")
        assert response.status_code == 200
        body = response.json()
        for field in ("id", "title", "status", "priority", "body", "updated", "created"):
            assert field in body, f"Task detail missing field {field!r}"

    def test_task_detail_nonexistent_id_returns_404_with_id_in_detail(
        self, client: TestClient
    ) -> None:
        """GET /api/tasks/9999 returns 404 with the ID referenced in the error detail."""
        response = client.get("/api/tasks/9999")
        assert response.status_code == 404
        detail = response.json().get("detail", "")
        assert "9999" in str(detail), (
            f"404 detail should reference the requested ID '9999', got: {detail!r}"
        )


# ---------------------------------------------------------------------------
# AC: GET /api/sessions
# ---------------------------------------------------------------------------


class TestFromAC_Sessions:
    """Tests for the GET /api/sessions endpoint."""

    def test_sessions_active_filter_returns_200(self, client: TestClient) -> None:
        """Happy path: GET /api/sessions?filter=active returns HTTP 200."""
        response = client.get("/api/sessions", params={"filter": "active"})
        assert response.status_code == 200

    def test_sessions_all_filter_returns_200(self, client: TestClient) -> None:
        """GET /api/sessions?filter=all returns HTTP 200."""
        response = client.get("/api/sessions", params={"filter": "all"})
        assert response.status_code == 200

    def test_sessions_response_has_sessions_list(self, client: TestClient) -> None:
        """Response body contains a 'sessions' key with a list value."""
        response = client.get("/api/sessions", params={"filter": "all"})
        assert response.status_code == 200
        body = response.json()
        assert "sessions" in body
        assert isinstance(body["sessions"], list)

    def test_sessions_each_entry_has_task_id_and_state(
        self, client: TestClient
    ) -> None:
        """Each session entry has task_id (int) and state (str) fields."""
        response = client.get("/api/sessions", params={"filter": "all"})
        assert response.status_code == 200
        sessions = response.json()["sessions"]
        for session in sessions:
            assert "task_id" in session, f"Session missing task_id: {session}"
            assert "state" in session, f"Session missing state: {session}"
            assert isinstance(session["task_id"], int)
            assert isinstance(session["state"], str)

    def test_sessions_active_is_default_filter(self, client: TestClient) -> None:
        """GET /api/sessions (no filter param) defaults to active and returns HTTP 200."""
        response = client.get("/api/sessions")
        assert response.status_code == 200
        body = response.json()
        assert "sessions" in body


# ---------------------------------------------------------------------------
# AC: Mtime cache behaviour (R2)
# ---------------------------------------------------------------------------


class TestFromAC_MtimeCache:
    """Tests for the tasks-dir mtime returned by GET /api/tasks.

    Strategy (R2): mtime = max(f.stat().st_mtime_ns for f in tasks_dir.iterdir())
    """

    def test_mtime_is_integer(self, client: TestClient) -> None:
        """The mtime value in the response is an integer (nanoseconds per R2)."""
        response = client.get("/api/tasks")
        assert response.status_code == 200
        mtime = response.json()["mtime"]
        assert isinstance(mtime, int)
        assert mtime > 0

    def test_mtime_stable_on_repeated_calls_without_file_changes(
        self, client: TestClient
    ) -> None:
        """Two sequential GETs with no file changes return the same mtime (cache hit)."""
        r1 = client.get("/api/tasks")
        assert r1.status_code == 200
        r2 = client.get("/api/tasks")
        assert r2.status_code == 200
        assert r1.json()["mtime"] == r2.json()["mtime"]

    def test_mtime_changes_after_task_file_modified(
        self, client: TestClient, board_dir: Path
    ) -> None:
        """After modifying a task file the mtime in the response changes."""
        r1 = client.get("/api/tasks")
        assert r1.status_code == 200
        mtime_before = r1.json()["mtime"]

        # Append whitespace to the first task file to update its mtime
        tasks_dir = board_dir / "tasks"
        task_files = sorted(tasks_dir.glob("*.md"))
        assert task_files, "Board must have task files for this test"
        target = task_files[0]
        target.write_text(target.read_text(encoding="utf-8") + " ", encoding="utf-8")

        r2 = client.get("/api/tasks")
        assert r2.status_code == 200
        mtime_after = r2.json()["mtime"]

        assert mtime_after != mtime_before, (
            "mtime must change when a task file is modified, "
            f"but before={mtime_before} and after={mtime_after} are equal"
        )
