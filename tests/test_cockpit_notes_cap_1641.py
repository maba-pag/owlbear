"""Smoke tests for ResolveRequest.notes max_length cap (#1641).

AC-1: ResolveRequest.notes field has max_length=10_000 via Pydantic Field constraint.
AC-2: POST /api/decisions/{id}/resolve returns HTTP 422 with response body
      containing type "string_too_long" when notes exceeds 10,000 characters.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


_CONFIG_YAML = """\
next_id: 1
"""

_NOTES_MAX = 10_000


def _make_board(base_dir: Path) -> Path:
    """Create a minimal kanban board directory."""
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


def _make_decisions_dir(base_dir: Path) -> Path:
    """Create decisions/pending and decisions/resolved directories."""
    decisions_dir = base_dir / "decisions"
    (decisions_dir / "pending").mkdir(parents=True)
    (decisions_dir / "resolved").mkdir(parents=True)
    return decisions_dir


def _write_pending_dr(decisions_dir: Path, *, stem: str, task_id: int) -> None:
    """Write a minimal pending decision request file."""
    path = decisions_dir / "pending" / f"{stem}.md"
    content = (
        "---\n"
        f"task_id: {task_id}\n"
        "agent: builder\n"
        "request_type: scope-decision\n"
        "created: '2026-05-19'\n"
        "response: pending\n"
        "---\n\n"
        f"# {stem}\n\n"
        "Body text.\n"
    )
    path.write_text(content, encoding="utf-8")


@pytest.fixture
def decisions_dir(tmp_path: Path) -> Path:
    """Isolated decisions directory."""
    return _make_decisions_dir(tmp_path)


@pytest.fixture
def engine(tmp_path: Path):
    """KanbanEngine backed by an isolated board."""
    from owlbear_kanban import KanbanEngine  # noqa: PLC0415

    board = _make_board(tmp_path)
    eng = KanbanEngine(board)
    eng.list_tasks()
    return eng


@pytest.fixture
def client(engine, decisions_dir: Path):
    """FastAPI TestClient with dependency overrides for engine and decisions_dir."""
    from fastapi.testclient import TestClient  # noqa: PLC0415

    from owlbear_cockpit import deps as cockpit_deps  # noqa: PLC0415
    from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415

    app.dependency_overrides[get_engine] = lambda: engine

    get_decisions_dir = getattr(cockpit_deps, "get_decisions_dir", None)
    if get_decisions_dir is not None:
        app.dependency_overrides[get_decisions_dir] = lambda: decisions_dir

    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


class TestFromAC_NotesLengthCap:
    """Smoke tests: notes max_length cap on ResolveRequest (#1641)."""

    def test_resolve_request_notes_field_has_max_length_10000(self) -> None:
        """AC-1: ResolveRequest.notes has max_length=10_000 via Pydantic Field."""
        from pydantic.fields import FieldInfo  # noqa: PLC0415

        from owlbear_cockpit.routes.decisions import ResolveRequest  # noqa: PLC0415

        field_info: FieldInfo = ResolveRequest.model_fields["notes"]
        max_lengths = [m.max_length for m in field_info.metadata if hasattr(m, "max_length")]
        assert max_lengths == [_NOTES_MAX], f"Expected notes max_length=[{_NOTES_MAX}], got {max_lengths}"

    def test_resolve_returns_422_with_string_too_long_when_notes_over_limit(
        self, client: TestClient, decisions_dir: Path
    ) -> None:
        """AC-2: POST /resolve with notes >10_000 chars returns 422 string_too_long."""
        decision_id = "1641-cap-test"
        _write_pending_dr(decisions_dir, stem=decision_id, task_id=1641)

        oversized_notes = "x" * (_NOTES_MAX + 1)
        response = client.post(
            f"/api/decisions/{decision_id}/resolve",
            json={"response": "approved", "notes": oversized_notes},
        )

        assert response.status_code == 422
        body = response.json()
        error_types = [err.get("type") for err in body.get("detail", []) if isinstance(err, dict)]
        assert "string_too_long" in error_types, f"Expected 'string_too_long' in error types, got: {error_types!r}"
