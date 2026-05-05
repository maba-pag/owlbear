"""Failing tests for cockpit edit contract gap-fill (#1344).

RED phase — all tests must fail until builder implements fixes.

AC coverage:
  AC1: body, parent, tags, depends_on, block_reason pass through with correct
       semantics; invalid values return 422, not uncaught exceptions.
  AC2: parent: null → clears parent (never raises TypeError); negative parent → 422.
  AC3: body: "" → clears body (must never return 200 with unchanged body).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from owlbear_kanban import KanbanEngine

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Board fixture helpers (self-contained; mirrors test_cockpit_mutation_api.py)
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


@pytest.fixture
def board_dir(tmp_path: Path) -> Path:
    """Board with 2 tasks.

    Task 1: status=todo, priority=important (primary edit target)
    Task 2: status=todo, priority=needed    (used as parent reference)
    """
    kanban_dir = _make_board(tmp_path)
    seed = KanbanEngine(kanban_dir)
    seed.create_task("Alpha task", status="todo", priority="important")
    seed.create_task("Beta task", status="todo", priority="needed")
    seed.list_tasks()
    return kanban_dir


@pytest.fixture
def engine(board_dir: Path) -> KanbanEngine:
    """KanbanEngine with activity logging enabled."""
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
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """parent: null must never result in an uncaught TypeError (500).

        AC1: invalid values return 422, not uncaught exceptions.
        AC2: parent: null must never raise TypeError.

        Current bug: `if parent > 0:` → TypeError: '>' not supported between
        instances of 'NoneType' and 'int'. Route returns 500 instead of 200.
        """
        task = engine.show_task("1")
        response = client.post(
            "/api/tasks/1/edit",
            json={"updated": task.updated, "parent": None},
        )
        assert response.status_code == 200, (
            f"parent: null caused uncaught exception — got {response.status_code}: "
            f"{response.json()}"
        )

    def test_parent_null_clears_parent(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """parent: null in request body clears the parent field (engine clear signal).

        AC2: parent: null clears the parent (maps to engine's parent-clear signal).

        Precondition: task 1 has parent=2 set via engine.
        Expected: POST parent: null → 200, response parent is null.
        """
        engine.edit_task("1", parent=2)
        task = engine.show_task("1")
        assert task.parent == 2, "Precondition: task 1 must have parent=2"

        response = client.post(
            "/api/tasks/1/edit",
            json={"updated": task.updated, "parent": None},
        )
        assert response.status_code == 200
        assert response.json()["parent"] is None, (
            f"parent: null did not clear the parent — got: {response.json()['parent']!r}"
        )

    def test_negative_parent_returns_422(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """Negative parent value is invalid and must return 422.

        AC2: negative values return 422.

        Current bug: CockpitView.edit_task's `if parent > 0:` evaluates False for
        negative values → parent is silently ignored → 200 instead of 422.
        """
        task = engine.show_task("1")
        response = client.post(
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
      - body="" is never forwarded to the engine → engine's clear signal never
        sent → original body remains unchanged → silent no-op violation of AC3.
    """

    def test_body_empty_string_clears_body(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """body: "" in request body must clear the task body to empty string.

        AC3: body: "" clears the task body (maps to engine's body="" contract).

        Precondition: task 1 has a non-empty body.
        Expected: POST body: "" → 200, response body is "".
        """
        engine.edit_task("1", body="## Original content\n\nShould be cleared.")
        task = engine.show_task("1")
        assert task.body, "Precondition: task 1 must have a non-empty body"

        response = client.post(
            "/api/tasks/1/edit",
            json={"updated": task.updated, "body": ""},
        )
        assert response.status_code == 200
        assert response.json()["body"] == "", (
            "body: '' must clear the task body, "
            f"got: {response.json()['body']!r}"
        )

    def test_body_empty_string_does_not_return_unchanged_body(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """POST body: "" must not return 200 with the original body unchanged.

        AC3: it must never return 200 while leaving the body unchanged.

        This test directly encodes the AC3 constraint: if the response is 200,
        the body in the response must differ from the original body (i.e., be "").
        """
        original_body = "## Persistent content that must be cleared"
        engine.edit_task("1", body=original_body)
        task = engine.show_task("1")

        response = client.post(
            "/api/tasks/1/edit",
            json={"updated": task.updated, "body": ""},
        )
        if response.status_code == 200:
            assert response.json()["body"] != original_body, (
                "AC3 violation: returned 200 but original body was left unchanged"
            )
