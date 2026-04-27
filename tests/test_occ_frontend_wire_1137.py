"""Failing tests for #1137: Wire updated OCC token through cockpit frontend move flow.

RED phase — all tests must fail until implementation in GREEN.

AC coverage:
  - AC0: TaskSummary (kanban models.py) includes ``updated: str`` field;
         docstring no longer claims it excludes ``updated``
  - AC1: TaskSummaryOut (cockpit models.py) includes ``updated: str`` field
  - AC2: GET /api/tasks response includes ``updated`` (ISO string) for each task
  - AC3: Task interface in useBoard.ts includes ``updated: string``
  - AC4: handleTransitionClick in KanbanBoard.tsx includes ``updated`` in POST body
  - AC5: KanbanBoard.test.tsx updated to assert ``updated`` in POST /move body
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


# ---------------------------------------------------------------------------
# Board setup helpers
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
    seed = KanbanEngine(kanban_dir, agent_name="seed-1137")
    seed.create_task("Alpha task", status="todo", priority="important")
    seed.create_task("Beta task", status="review", priority="critical")
    return kanban_dir


@pytest.fixture
def engine(board_dir: Path) -> KanbanEngine:
    """KanbanEngine with pre-warmed id→filename cache."""
    eng = KanbanEngine(board_dir, agent_name="test-1137")
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

    def test_list_tasks_result_has_updated_attribute(
        self, engine: KanbanEngine
    ) -> None:
        """Happy path: engine.list_tasks() returns TaskSummary objects with updated."""
        summaries = engine.list_tasks()
        assert len(summaries) > 0, "Board must have tasks for this test"
        for s in summaries:
            assert hasattr(s, "updated"), (
                f"TaskSummary from list_tasks() is missing 'updated': {s}"
            )
            assert s.updated, "TaskSummary.updated must be non-empty"


# ---------------------------------------------------------------------------
# AC1: TaskSummaryOut.updated field
# ---------------------------------------------------------------------------


class TestFromAC_TaskSummaryOutUpdatedField:
    """AC1: cockpit TaskSummaryOut must include ``updated: str`` field."""

    def test_task_summary_out_has_updated_in_model_fields(self) -> None:
        """Structural: 'updated' must appear in TaskSummaryOut.model_fields."""
        from owlbear_cockpit.models import TaskSummaryOut  # noqa: PLC0415

        assert "updated" in TaskSummaryOut.model_fields, (
            "TaskSummaryOut.model_fields does not include 'updated' — AC1 not implemented"
        )

    def test_task_summary_out_preserves_updated_on_construct(self) -> None:
        """Happy path: TaskSummaryOut constructed with updated preserves the value."""
        from owlbear_cockpit.models import TaskSummaryOut  # noqa: PLC0415

        out = TaskSummaryOut(
            id=1,
            title="T",
            status="todo",
            priority="important",
            updated="2026-04-27T10:00:00+00:00",
        )
        assert out.updated == "2026-04-27T10:00:00+00:00"


# ---------------------------------------------------------------------------
# AC2: GET /api/tasks response includes updated
# ---------------------------------------------------------------------------


_ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")


class TestFromAC_TasksEndpointIncludesUpdated:
    """AC2: GET /api/tasks must return ``updated`` (ISO string) for every task."""

    def test_get_tasks_each_task_has_updated_key(
        self, client: TestClient
    ) -> None:
        """Happy path: every task in the response carries an 'updated' key."""
        response = client.get("/api/tasks")
        assert response.status_code == 200
        tasks = response.json()["tasks"]
        assert len(tasks) > 0, "Board must have tasks for this assertion"
        for task in tasks:
            assert "updated" in task, (
                f"Task missing 'updated' field in GET /api/tasks response: {task}"
            )

    def test_get_tasks_updated_is_a_string(self, client: TestClient) -> None:
        """Boundary: each task's 'updated' value must be a string."""
        response = client.get("/api/tasks")
        assert response.status_code == 200
        for task in response.json()["tasks"]:
            assert isinstance(task["updated"], str), (
                f"Task 'updated' is not a string: {task.get('updated')!r}"
            )

    def test_get_tasks_updated_is_non_empty(self, client: TestClient) -> None:
        """Edge: each task's 'updated' value must be a non-empty string."""
        response = client.get("/api/tasks")
        assert response.status_code == 200
        for task in response.json()["tasks"]:
            assert task.get("updated"), (
                f"Task 'updated' is empty or missing: {task}"
            )

    def test_get_tasks_updated_matches_iso_timestamp_pattern(
        self, client: TestClient
    ) -> None:
        """Boundary: each task's 'updated' must look like an ISO 8601 timestamp."""
        response = client.get("/api/tasks")
        assert response.status_code == 200
        for task in response.json()["tasks"]:
            val = task.get("updated", "")
            assert _ISO_RE.match(val), (
                f"Task 'updated' {val!r} does not match ISO timestamp pattern"
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
            "KanbanBoard.tsx handleTransitionClick does not include 'updated' in "
            "the request body — AC4 not implemented"
        )

    def test_kanban_board_test_file_asserts_updated_in_move_body(self) -> None:
        """AC5: KanbanBoard.test.tsx must contain a test asserting updated in POST /move body."""
        test_file = _SRC / "__tests__" / "KanbanBoard.test.tsx"
        content = test_file.read_text(encoding="utf-8")
        assert "updated" in content, (
            "KanbanBoard.test.tsx does not reference 'updated' — "
            "AC5 test asserting updated in POST /move body not yet added"
        )
