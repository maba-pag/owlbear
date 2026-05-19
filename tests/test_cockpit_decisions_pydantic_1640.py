"""Failing tests for task #1640: Pydantic response model for GET /api/decisions/pending.

AC1 — PendingDRItem + PendingDRResponse Pydantic models exist and are importable;
       task_id is int (coerced from YAML str); all 8 fields required.
AC2 — DR files that parse OK but fail model_validate() are excluded;
       count reflects only included items; HTTP 200.
AC3 — GET /api/decisions/pending is decorated with response_model=PendingDRResponse.
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


def _make_board(base_dir: Path) -> Path:
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


def _make_decisions_dir(base_dir: Path) -> Path:
    decisions_dir = base_dir / "decisions"
    (decisions_dir / "pending").mkdir(parents=True)
    (decisions_dir / "resolved").mkdir(parents=True)
    return decisions_dir


def _write_pending_dr(
    decisions_dir: Path,
    *,
    stem: str,
    task_id: int,
    body: str = "# Decision\nWhat to do?",
    response: str = "pending",
) -> Path:
    path = decisions_dir / "pending" / f"{stem}.md"
    content = (
        "---\n"
        f"task_id: {task_id}\n"
        "agent: builder\n"
        "request_type: scope-decision\n"
        "created: '2026-05-19'\n"
        f"response: {response}\n"
        "---\n\n"
        f"{body}\n"
    )
    path.write_text(content, encoding="utf-8")
    return path


@pytest.fixture
def engine(tmp_path: Path):
    from owlbear_kanban import KanbanEngine  # noqa: PLC0415

    board_dir = _make_board(tmp_path)
    eng = KanbanEngine(board_dir)
    eng.list_tasks()
    return eng


@pytest.fixture
def decisions_dir(tmp_path: Path) -> Path:
    return _make_decisions_dir(tmp_path)


@pytest.fixture
def client(engine, decisions_dir: Path):
    from fastapi.testclient import TestClient  # noqa: PLC0415

    from owlbear_cockpit import deps as cockpit_deps  # noqa: PLC0415
    from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415

    app.dependency_overrides[get_engine] = lambda: engine
    get_decisions_dir_fn = getattr(cockpit_deps, "get_decisions_dir", None)
    if get_decisions_dir_fn is not None:
        app.dependency_overrides[get_decisions_dir_fn] = lambda: decisions_dir

    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


class TestFromAC_PydanticDecisionsModel:
    """Tests for #1640: Pydantic response model on GET /api/decisions/pending."""

    # ------------------------------------------------------------------ AC1 --

    def test_pending_dr_item_is_importable(self) -> None:
        """PendingDRItem is importable from owlbear_cockpit.routes.decisions."""
        from owlbear_cockpit.routes.decisions import PendingDRItem  # noqa: PLC0415

        assert PendingDRItem is not None

    def test_pending_dr_response_is_importable(self) -> None:
        """PendingDRResponse is importable from owlbear_cockpit.routes.decisions."""
        from owlbear_cockpit.routes.decisions import PendingDRResponse  # noqa: PLC0415

        assert PendingDRResponse is not None

    def test_pending_dr_item_declares_task_id_as_int(self) -> None:
        """PendingDRItem.model_fields includes task_id with int annotation."""
        from owlbear_cockpit.routes.decisions import PendingDRItem  # noqa: PLC0415

        fields = PendingDRItem.model_fields
        assert "task_id" in fields
        # Pydantic v2: annotation on the FieldInfo resolves to int
        annotation = fields["task_id"].annotation
        assert annotation is int, f"Expected int, got {annotation!r}"

    def test_pending_dr_response_has_count_and_items_fields(self) -> None:
        """PendingDRResponse.model_fields contains count and items."""
        from owlbear_cockpit.routes.decisions import PendingDRResponse  # noqa: PLC0415

        fields = PendingDRResponse.model_fields
        assert "count" in fields
        assert "items" in fields

    def test_task_id_string_in_yaml_is_coerced_to_int_in_response(
        self, client: TestClient, decisions_dir: Path
    ) -> None:
        """task_id quoted as string in YAML ('42') is returned as int 42 in response."""
        path = decisions_dir / "pending" / "10-string-task-id.md"
        path.write_text(
            "---\n"
            "task_id: '42'\n"
            "agent: builder\n"
            "request_type: scope-decision\n"
            "created: '2026-05-19'\n"
            "response: pending\n"
            "---\n\n"
            "# Title\nBody text.\n",
            encoding="utf-8",
        )

        response = client.get("/api/decisions/pending")

        assert response.status_code == 200
        payload = response.json()
        assert payload["count"] == 1
        item = payload["items"][0]
        assert item["task_id"] == 42
        assert isinstance(item["task_id"], int)

    # ------------------------------------------------------------------ AC2 --

    def test_missing_task_id_excludes_item_and_returns_200(self, client: TestClient, decisions_dir: Path) -> None:
        """DR with no task_id in frontmatter is excluded; endpoint returns HTTP 200 count=0."""
        path = decisions_dir / "pending" / "20-no-task-id.md"
        path.write_text(
            "---\n"
            "agent: builder\n"
            "request_type: scope-decision\n"
            "created: '2026-05-19'\n"
            "response: pending\n"
            "---\n\n"
            "# Title\nNo task_id field.\n",
            encoding="utf-8",
        )

        response = client.get("/api/decisions/pending")

        assert response.status_code == 200
        payload = response.json()
        assert payload["count"] == 0
        assert payload["items"] == []

    def test_non_coercible_task_id_excludes_item_and_returns_200(self, client: TestClient, decisions_dir: Path) -> None:
        """DR with task_id: 'not-a-number' is excluded; endpoint returns HTTP 200 count=0."""
        path = decisions_dir / "pending" / "21-bad-task-id.md"
        path.write_text(
            "---\n"
            "task_id: not-a-number\n"
            "agent: builder\n"
            "request_type: scope-decision\n"
            "created: '2026-05-19'\n"
            "response: pending\n"
            "---\n\n"
            "# Title\nBad task_id.\n",
            encoding="utf-8",
        )

        response = client.get("/api/decisions/pending")

        assert response.status_code == 200
        payload = response.json()
        assert payload["count"] == 0
        assert payload["items"] == []

    def test_one_valid_one_missing_task_id_returns_only_valid(self, client: TestClient, decisions_dir: Path) -> None:
        """Mixed set: valid item included, item with missing task_id excluded; count=1."""
        _write_pending_dr(decisions_dir, stem="30-valid", task_id=30)
        (decisions_dir / "pending" / "31-no-task-id.md").write_text(
            "---\n"
            "agent: builder\n"
            "request_type: scope-decision\n"
            "created: '2026-05-19'\n"
            "response: pending\n"
            "---\n\n"
            "# Missing task_id\n",
            encoding="utf-8",
        )

        response = client.get("/api/decisions/pending")

        assert response.status_code == 200
        payload = response.json()
        assert payload["count"] == 1
        assert len(payload["items"]) == 1
        assert payload["items"][0]["id"] == "30-valid"

    def test_count_reflects_only_successfully_validated_items(self, client: TestClient, decisions_dir: Path) -> None:
        """count equals validated items only; invalid items do not inflate count."""
        _write_pending_dr(decisions_dir, stem="40-valid-a", task_id=40)
        _write_pending_dr(decisions_dir, stem="41-valid-b", task_id=41)
        (decisions_dir / "pending" / "42-bad-task-id.md").write_text(
            "---\n"
            "task_id: abc\n"
            "agent: builder\n"
            "request_type: scope-decision\n"
            "created: '2026-05-19'\n"
            "response: pending\n"
            "---\n\n"
            "# Bad task_id\n",
            encoding="utf-8",
        )

        response = client.get("/api/decisions/pending")

        assert response.status_code == 200
        payload = response.json()
        assert payload["count"] == 2
        assert len(payload["items"]) == 2

    # ------------------------------------------------------------------ AC3 --

    def test_route_decorated_with_response_model_pending_dr_response(self) -> None:
        """GET /api/decisions/pending has response_model=PendingDRResponse on the route."""
        from owlbear_cockpit.main import app  # noqa: PLC0415
        from owlbear_cockpit.routes.decisions import PendingDRResponse  # noqa: PLC0415

        matching = [
            r
            for r in app.routes
            if hasattr(r, "path")
            and r.path == "/api/decisions/pending"
            and hasattr(r, "methods")
            and "GET" in r.methods
        ]
        assert matching, "No GET route found for /api/decisions/pending"
        route = matching[0]
        assert hasattr(route, "response_model"), "Route has no response_model attribute"
        assert route.response_model is PendingDRResponse

    def test_integration_response_validates_as_pending_dr_item(self, client: TestClient, decisions_dir: Path) -> None:
        """Full integration: response JSON validates as PendingDRItem with correct int task_id."""
        from owlbear_cockpit.routes.decisions import PendingDRItem  # noqa: PLC0415

        _write_pending_dr(decisions_dir, stem="50-typed", task_id=50)

        response = client.get("/api/decisions/pending")

        assert response.status_code == 200
        payload = response.json()
        assert payload["count"] == 1
        item = payload["items"][0]

        validated = PendingDRItem.model_validate(item)
        assert validated.task_id == 50
        assert isinstance(validated.task_id, int)
        assert isinstance(validated.id, str)
        assert isinstance(validated.agent, str)
        assert isinstance(validated.request_type, str)
        assert isinstance(validated.created, str)
        assert isinstance(validated.title, str)
        assert isinstance(validated.body, str)
        assert isinstance(validated.body_preview, str)

    # ------------------------------------------------------------------ AC4 --

    def test_list_pending_decisions_returns_instance_missing_dir_path(self, tmp_path: Path) -> None:
        """list_pending_decisions() called directly with a missing pending/ dir returns a PendingDRResponse instance."""
        from owlbear_cockpit.routes.decisions import (  # noqa: PLC0415
            PendingDRResponse,
            list_pending_decisions,
        )

        # decisions_dir exists but has no pending/ subdirectory
        decisions_dir = tmp_path / "decisions"
        decisions_dir.mkdir()

        result = list_pending_decisions(decisions_dir)

        assert isinstance(result, PendingDRResponse), (
            f"Expected PendingDRResponse instance on missing-dir path, got {type(result)!r}"
        )
        assert result.count == 0
        assert result.items == []

    def test_list_pending_decisions_returns_instance_normal_path(self, tmp_path: Path) -> None:
        """list_pending_decisions() called directly with a populated pending/ dir returns a PendingDRResponse instance."""
        from owlbear_cockpit.routes.decisions import (  # noqa: PLC0415
            PendingDRResponse,
            list_pending_decisions,
        )

        decisions_dir = _make_decisions_dir(tmp_path)
        _write_pending_dr(decisions_dir, stem="60-direct-call", task_id=60)

        result = list_pending_decisions(decisions_dir)

        assert isinstance(result, PendingDRResponse), (
            f"Expected PendingDRResponse instance on normal iteration path, got {type(result)!r}"
        )
        assert result.count == 1
        assert len(result.items) == 1
        assert result.items[0].task_id == 60
