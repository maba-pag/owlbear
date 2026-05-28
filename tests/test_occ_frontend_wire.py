"""Failing tests for #1137: Wire updated OCC token through cockpit frontend move flow.

RED phase — all tests must fail until implementation in GREEN.

AC coverage:
  - AC0: TaskSummary (kanban models.py) includes ``updated: str`` field;
         docstring no longer claims it excludes ``updated``
    - AC1: Cockpit task responses include ``updated: str`` field
  - AC2: GET /api/tasks response includes ``updated`` (ISO string) for each task
  - AC3: Task interface in useBoard.ts includes ``updated: string``
  - AC4: handleTransitionClick in KanbanBoard.tsx includes ``updated`` in POST body
  - AC5: KanbanBoard.test.tsx updated to assert ``updated`` in POST /move body
  - AC7: MCP test fixtures in test_mcp_read_tools.py and test_mcp_models_1084.py
         include ``updated`` when constructing TaskSummary
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from owlbear_kanban import KanbanEngine

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

_WEB = Path(__file__).parent.parent / "serve" / "cockpit" / "web"
_SRC = _WEB / "src"
_MCP_KANBAN_TESTS = Path(__file__).parent.parent / "serve" / "mcp-kanban" / "tests"


# ---------------------------------------------------------------------------
# Board setup helpers
# ---------------------------------------------------------------------------

_CONFIG_YAML = """\
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
    """Minimal board with two tasks at different statuses."""
    kanban_dir = _make_board(tmp_path)
    seed = KanbanEngine(kanban_dir)
    seed.create_task("Alpha task", status="todo", priority="important")
    seed.create_task("Beta task", status="review", priority="critical")
    return kanban_dir


@pytest.fixture
def engine(board_dir: Path) -> KanbanEngine:
    """KanbanEngine with pre-warmed id→filename cache."""
    eng = KanbanEngine(board_dir)
    eng.list_tasks()
    return eng


@pytest.fixture
def client(engine: KanbanEngine):
    """FastAPI TestClient with dependency-injected engine."""
    from fastapi.testclient import TestClient  # noqa: PLC0415
    from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415

    app.dependency_overrides[get_engine] = lambda: engine
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# AC0: TaskSummary.updated field + docstring update
# ---------------------------------------------------------------------------


class TestFromAC_TaskSummaryUpdatedField:
    """AC0: kanban TaskSummary must expose ``updated: str`` and drop exclusion claim."""

    def test_task_summary_has_updated_in_model_fields(self) -> None:
        """Structural: 'updated' must appear in TaskSummary.model_fields."""
        from owlbear_kanban.models import TaskSummary  # noqa: PLC0415

        assert "updated" in TaskSummary.model_fields, (
            "TaskSummary.model_fields does not include 'updated' — AC0 not implemented"
        )

    def test_task_summary_preserves_updated_on_construct(self) -> None:
        """Happy path: TaskSummary constructed with updated preserves the value."""
        from owlbear_kanban.models import TaskSummary  # noqa: PLC0415

        ts = TaskSummary(
            id=1,
            title="T",
            status="todo",
            priority="important",
            updated="2026-04-27T10:00:00+00:00",
        )
        assert ts.updated == "2026-04-27T10:00:00+00:00"

    def test_task_summary_docstring_no_longer_claims_updated_excluded(self) -> None:
        """Boundary: docstring must not list 'updated' as an excluded field."""
        from owlbear_kanban.models import TaskSummary  # noqa: PLC0415

        doc = TaskSummary.__doc__ or ""
        # Before fix: "Excludes ``body``, ``created``, and ``updated``..."
        assert "and ``updated``" not in doc, (
            "TaskSummary docstring still claims 'updated' is excluded — AC0 not implemented"
        )

    def test_list_tasks_result_has_updated_attribute(self, engine: KanbanEngine) -> None:
        """Happy path: engine.list_tasks() returns TaskSummary objects with updated."""
        summaries = engine.list_tasks()
        assert len(summaries) > 0, "Board must have tasks for this test"
        for s in summaries:
            assert hasattr(s, "updated"), f"TaskSummary from list_tasks() is missing 'updated': {s}"
            assert s.updated, "TaskSummary.updated must be non-empty"


# ---------------------------------------------------------------------------
# AC2: GET /api/tasks response includes updated
# ---------------------------------------------------------------------------


_ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")


class TestFromAC_TasksEndpointIncludesUpdated:
    """AC2: GET /api/tasks must return ``updated`` (ISO string) for every task."""

    def test_get_tasks_each_task_has_updated_key(self, client: TestClient) -> None:
        """Happy path: every task in the response carries an 'updated' key."""
        response = client.get("/api/tasks")
        assert response.status_code == 200
        tasks = response.json()["tasks"]
        assert len(tasks) > 0, "Board must have tasks for this assertion"
        for task in tasks:
            assert "updated" in task, f"Task missing 'updated' field in GET /api/tasks response: {task}"

    def test_get_tasks_updated_is_a_string(self, client: TestClient) -> None:
        """Boundary: each task's 'updated' value must be a string."""
        response = client.get("/api/tasks")
        assert response.status_code == 200
        for task in response.json()["tasks"]:
            assert isinstance(task["updated"], str), f"Task 'updated' is not a string: {task.get('updated')!r}"

    def test_get_tasks_updated_is_non_empty(self, client: TestClient) -> None:
        """Edge: each task's 'updated' value must be a non-empty string."""
        response = client.get("/api/tasks")
        assert response.status_code == 200
        for task in response.json()["tasks"]:
            assert task.get("updated"), f"Task 'updated' is empty or missing: {task}"

    def test_get_tasks_updated_matches_iso_timestamp_pattern(self, client: TestClient) -> None:
        """Boundary: each task's 'updated' must look like an ISO 8601 timestamp."""
        response = client.get("/api/tasks")
        assert response.status_code == 200
        for task in response.json()["tasks"]:
            val = task.get("updated", "")
            assert _ISO_RE.match(val), f"Task 'updated' {val!r} does not match ISO timestamp pattern"

    def test_get_tasks_updated_value_matches_engine_show_task(self, client: TestClient, engine: KanbanEngine) -> None:
        """Source-parity (AC2): GET /api/tasks 'updated' must equal engine.show_task(id).updated."""
        response = client.get("/api/tasks")
        assert response.status_code == 200
        api_tasks = response.json()["tasks"]
        assert len(api_tasks) > 0, "Board must have tasks for this assertion"
        for api_task in api_tasks:
            task_id = str(api_task["id"])
            full_task = engine.show_task(task_id)
            assert api_task["updated"] == str(full_task.updated), (
                f"Task {task_id}: GET /api/tasks returned updated={api_task['updated']!r} "
                f"but engine.show_task returned {str(full_task.updated)!r} — "
                "updated must flow from real engine state, not a default/hardcoded value"
            )


# ---------------------------------------------------------------------------
# AC3-AC5: Frontend static contract tests
# ---------------------------------------------------------------------------




class TestFromAC_RoundTripOCCProof:
    """AC6: updated token from GET /api/tasks must be accepted by POST /move (no 409)."""

    def test_move_with_updated_from_list_tasks_returns_200(self, client: TestClient) -> None:
        """Round-trip: updated extracted from GET /api/tasks accepted by POST /move → 200."""
        # Step 1: GET /api/tasks — extract first task's id, updated, and status
        list_resp = client.get("/api/tasks")
        assert list_resp.status_code == 200
        api_tasks = list_resp.json()["tasks"]
        assert len(api_tasks) > 0, "Need at least one task for round-trip test"
        task = api_tasks[0]
        task_id = task["id"]
        task_updated = task["updated"]
        task_status = task["status"]

        # Step 2: GET /api/board — find a valid target status
        board_resp = client.get("/api/board")
        assert board_resp.status_code == 200
        valid_transitions = board_resp.json()["valid_transitions"]
        targets = valid_transitions.get(task_status, [])
        assert len(targets) > 0, (
            f"Task {task_id} in status {task_status!r} has no valid transitions — cannot execute round-trip test"
        )
        target_status = targets[0]

        # Step 3: POST /move with updated from list API — must be 200, not 409/422
        move_resp = client.post(
            f"/api/tasks/{task_id}/move",
            json={"status": target_status, "updated": task_updated},
        )
        assert move_resp.status_code == 200, (
            f"Round-trip OCC failed: POST /tasks/{task_id}/move returned "
            f"{move_resp.status_code} (expected 200). "
            "The updated token from GET /api/tasks was rejected — OCC wire broken.\n"
            f"Request: status={target_status!r}, updated={task_updated!r}"
        )

    def test_stale_updated_token_returns_409(self, client: TestClient) -> None:
        """Edge (AC6): a stale updated token must be rejected with 409."""
        # GET a real task to get a valid id and status
        list_resp = client.get("/api/tasks")
        assert list_resp.status_code == 200
        task = list_resp.json()["tasks"][0]
        task_id = task["id"]
        task_status = task["status"]

        # Find a valid target status
        board_resp = client.get("/api/board")
        targets = board_resp.json()["valid_transitions"].get(task_status, [])
        assert len(targets) > 0, "Need valid transitions for OCC rejection test"
        target_status = targets[0]

        # Use a deliberately stale token
        stale_updated = "2000-01-01T00:00:00+00:00"
        move_resp = client.post(
            f"/api/tasks/{task_id}/move",
            json={"status": target_status, "updated": stale_updated},
        )
        assert move_resp.status_code == 409, (
            f"Expected 409 for stale OCC token but got {move_resp.status_code} — "
            "OCC precheck not enforced on POST /move"
        )


# ---------------------------------------------------------------------------
# AC7: MCP fixture remediation
# TaskSummary.updated is required; MCP test fixtures must supply it
# ---------------------------------------------------------------------------


