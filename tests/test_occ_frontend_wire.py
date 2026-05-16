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


class TestFromAC_FrontendOCCContract:
    """AC3/AC4/AC5: Frontend source files must wire updated through the move flow.

    These tests verify static source contracts since the test-writer cannot write
    to serve/cockpit/web/src/__tests__/ directly (path guard restriction).
    Failure mode: files don't yet contain the required patterns.
    """

    def test_task_interface_in_useboard_has_updated_field(self) -> None:
        """AC3: useBoard.ts Task interface must declare ``updated: string``."""
        content = (_SRC / "hooks" / "useBoard.ts").read_text(encoding="utf-8")
        assert "updated: string" in content, (
            "useBoard.ts Task interface does not include 'updated: string' — AC3 not implemented"
        )

    def test_handle_transition_click_includes_updated_in_body(self) -> None:
        """AC4: handleTransitionClick in KanbanBoard.tsx must include updated in POST body."""
        content = (_SRC / "KanbanBoard.tsx").read_text(encoding="utf-8")
        idx = content.find("handleTransitionClick")
        assert idx >= 0, "handleTransitionClick function not found in KanbanBoard.tsx"
        # Scan the 600 chars after the function declaration — covers the fetch body
        section = content[idx : idx + 600]
        assert "updated" in section, (
            "KanbanBoard.tsx handleTransitionClick does not include 'updated' in the request body — AC4 not implemented"
        )

    def test_kanban_board_test_file_asserts_updated_in_move_body(self) -> None:
        """AC5: KanbanBoard.test.tsx must contain a test asserting updated in POST /move body."""
        test_file = _SRC / "__tests__" / "KanbanBoard.test.tsx"
        content = test_file.read_text(encoding="utf-8")
        assert "updated" in content, (
            "KanbanBoard.test.tsx does not reference 'updated' — "
            "AC5 test asserting updated in POST /move body not yet added"
        )

    def test_handle_transition_click_json_stringify_contains_updated(self) -> None:
        """AC4 tightened: JSON.stringify in KanbanBoard.tsx must include 'updated' in object literal."""
        content = (_SRC / "KanbanBoard.tsx").read_text(encoding="utf-8")
        # Regex specifically matches JSON.stringify({...updated...}) — not just nearby text
        pattern = re.compile(r"JSON\.stringify\(\s*\{[^}]*\bupdated\b[^}]*\}", re.DOTALL)
        assert pattern.search(content) is not None, (
            "KanbanBoard.tsx: no JSON.stringify call includes 'updated' in its object "
            "literal — AC4 not satisfied (updated may appear in function signature "
            "but not in the actual request body)"
        )

    def test_kanban_board_test_move_body_has_status_and_updated_together(self) -> None:
        """AC5 tightened: KanbanBoard.test.tsx must assert both status and updated in same stringify body."""
        test_file = _SRC / "__tests__" / "KanbanBoard.test.tsx"
        content = test_file.read_text(encoding="utf-8")
        # Require both status and updated inside the same JSON.stringify object literal
        pattern = re.compile(
            r"JSON\.stringify\(\s*\{[^}]*\bstatus\b[^}]*\bupdated\b[^}]*\}",
            re.DOTALL,
        )
        assert pattern.search(content) is not None, (
            "KanbanBoard.test.tsx: no JSON.stringify call found that includes both "
            "'status' and 'updated' in the same object literal — AC5 assertion does "
            "not prove the move body sends both fields together"
        )


# ---------------------------------------------------------------------------
# AC6: Round-trip OCC proof — GET /api/tasks → POST /move → 200
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


class TestFromAC_MCPFixtureRemediation:
    """AC7: MCP test fixture helpers/constructions must include ``updated`` field.

    TaskSummary.updated became required when AC0 wired it through the engine model.
    Two fixture locations in mcp-kanban tests still construct TaskSummary without it,
    causing ValidationError at runtime.
    """

    def test_mcp_read_tools_make_task_summary_defaults_include_updated(self) -> None:
        """AC7: _make_task_summary defaults in test_mcp_read_tools.py must include 'updated'."""
        content = (_MCP_KANBAN_TESTS / "test_mcp_read_tools.py").read_text(encoding="utf-8")
        fn_start = content.find("def _make_task_summary")
        assert fn_start >= 0, "_make_task_summary not found in test_mcp_read_tools.py"
        # Scope to just this function body — stops before _make_show_task_response
        next_fn = content.find("def _make_show_task_response", fn_start)
        assert next_fn > fn_start, "_make_show_task_response sentinel not found"
        section = content[fn_start:next_fn]
        assert '"updated"' in section or "'updated'" in section, (
            "test_mcp_read_tools.py: _make_task_summary defaults dict does not include "
            "'updated' key — TaskSummary.updated is required since AC0; construction "
            "without it raises ValidationError. AC7 fixture remediation not applied."
        )

    def test_mcp_models_1084_archival_refs_construction_includes_updated(self) -> None:
        """AC7: TaskSummary call in test_task_summary_has_archival_refs_int_list must include updated=."""
        content = (_MCP_KANBAN_TESTS / "test_mcp_models_1084.py").read_text(encoding="utf-8")
        fn_start = content.find("def test_task_summary_has_archival_refs_int_list")
        assert fn_start >= 0, "test_task_summary_has_archival_refs_int_list not found in test_mcp_models_1084.py"
        next_fn = content.find("def test_task_summary_has_dep_status", fn_start)
        assert next_fn > fn_start, "dep_status sentinel not found after archival_refs test"
        section = content[fn_start:next_fn]
        assert "updated=" in section, (
            "test_mcp_models_1084.py: TaskSummary() in test_task_summary_has_archival_refs_int_list "
            "does not pass updated= — AC7 fixture remediation not applied. "
            "This construction raises ValidationError: TaskSummary updated Field required."
        )

    def test_mcp_models_1084_dep_status_none_construction_includes_updated(
        self,
    ) -> None:
        """AC7: TaskSummary call in test_task_summary_dep_status_none_when_no_deps must include updated=."""
        content = (_MCP_KANBAN_TESTS / "test_mcp_models_1084.py").read_text(encoding="utf-8")
        fn_start = content.find("def test_task_summary_dep_status_none_when_no_deps")
        assert fn_start >= 0, "test_task_summary_dep_status_none_when_no_deps not found in test_mcp_models_1084.py"
        # Scope to this function body only
        next_fn = content.find("\n\n\n", fn_start)
        section = content[fn_start : next_fn if next_fn > fn_start else fn_start + 400]
        assert "updated=" in section, (
            "test_mcp_models_1084.py: TaskSummary() in test_task_summary_dep_status_none_when_no_deps "
            "does not pass updated= — AC7 fixture remediation not applied. "
            "This construction raises ValidationError: TaskSummary updated Field required."
        )
