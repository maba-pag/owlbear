"""Task #1223: Sessions API envelope — failing tests (RED phase).

AC coverage:
  - AC1 (td:1): SessionsResponse(BaseModel) with sessions: list[SessionRecord]
                importable from owlbear_cockpit.routes.read
  - AC2 (td:2): GET /api/sessions handler returns SessionsResponse envelope
  - AC3 (td:1): existing TestFromAC_Sessions assertions updated in module-level file
  - AC4 (td:0): no frontend changes — skipped
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from owlbear_kanban import KanbanEngine

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


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
    """Create a minimal kanban board. Returns kanban_dir."""
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


@pytest.fixture()
def board_dir(tmp_path: Path) -> Path:
    return _make_board(tmp_path)


@pytest.fixture()
def engine(board_dir: Path) -> KanbanEngine:
    eng = KanbanEngine(board_dir, agent_name="test-1223")
    eng.list_tasks()
    return eng


@pytest.fixture()
def client(engine: KanbanEngine):
    from fastapi.testclient import TestClient  # noqa: PLC0415
    from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415

    app.dependency_overrides[get_engine] = lambda: engine
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture()
def board_with_session_dir(tmp_path: Path) -> Path:
    """Board with activity_log enabled and one active claim in activity.jsonl."""
    kanban_dir = tmp_path / "board_session"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    seed_eng = KanbanEngine(kanban_dir, agent_name="seeder", activity_log=True)
    task = seed_eng.create_task("Session task", status="todo")
    seed_eng.list_tasks()
    seed_eng.claim_task(str(task.id))
    return kanban_dir


@pytest.fixture()
def client_with_session(board_with_session_dir: Path):
    from fastapi.testclient import TestClient  # noqa: PLC0415
    from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415

    eng = KanbanEngine(board_with_session_dir, agent_name="test-1223-s", activity_log=True)
    eng.list_tasks()
    app.dependency_overrides[get_engine] = lambda: eng
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


class TestFromAC_SessionsEnvelope:
    """Tests for #1223 — GET /api/sessions must return a SessionsResponse envelope."""

    # -- AC1 (td:1): SessionsResponse model importable from read.py --

    def test_sessions_response_model_importable_with_sessions_field(self) -> None:
        """SessionsResponse is importable from read.py and has a 'sessions' field."""
        from owlbear_cockpit.routes.read import SessionsResponse  # noqa: PLC0415

        assert "sessions" in SessionsResponse.model_fields, (
            "SessionsResponse must have a 'sessions' field"
        )

    # -- AC2 (td:2): handler returns envelope --

    def test_sessions_all_filter_returns_dict_with_sessions_key(
        self, client: TestClient
    ) -> None:
        """Happy path: GET /api/sessions?filter=all returns dict with 'sessions' key."""
        response = client.get("/api/sessions", params={"filter": "all"})
        assert response.status_code == 200
        body = response.json()
        assert isinstance(body, dict), (
            f"Expected dict envelope, got {type(body).__name__}: {body!r}"
        )
        assert "sessions" in body, f"Response missing 'sessions' key: {body!r}"
        assert isinstance(body["sessions"], list)

    def test_sessions_active_filter_returns_dict_with_sessions_key(
        self, client: TestClient
    ) -> None:
        """Happy path: GET /api/sessions?filter=active returns dict with 'sessions' key."""
        response = client.get("/api/sessions", params={"filter": "active"})
        assert response.status_code == 200
        body = response.json()
        assert isinstance(body, dict), (
            f"Expected dict envelope, got {type(body).__name__}: {body!r}"
        )
        assert "sessions" in body, f"Response missing 'sessions' key: {body!r}"

    def test_sessions_no_param_returns_dict_with_sessions_key(
        self, client: TestClient
    ) -> None:
        """Edge: GET /api/sessions (no filter param) returns dict with 'sessions' key."""
        response = client.get("/api/sessions")
        assert response.status_code == 200
        body = response.json()
        assert isinstance(body, dict), (
            f"Expected dict envelope, got {type(body).__name__}: {body!r}"
        )
        assert "sessions" in body, f"Response missing 'sessions' key: {body!r}"

    def test_sessions_empty_board_wraps_empty_list(
        self, client: TestClient
    ) -> None:
        """Edge: board with no sessions returns {"sessions": []}, not []."""
        response = client.get("/api/sessions", params={"filter": "all"})
        assert response.status_code == 200
        body = response.json()
        assert isinstance(body, dict), (
            f"Expected dict envelope, got {type(body).__name__}: {body!r}"
        )
        sessions = body.get("sessions")
        assert isinstance(sessions, list), (
            f"body['sessions'] must be a list, got: {sessions!r}"
        )

    def test_sessions_envelope_has_only_sessions_key(
        self, client: TestClient
    ) -> None:
        """Boundary: SessionsResponse has one field — response dict has exactly 'sessions' key."""
        response = client.get("/api/sessions", params={"filter": "all"})
        assert response.status_code == 200
        body = response.json()
        assert isinstance(body, dict)
        assert set(body.keys()) == {"sessions"}, (
            f"Expected only 'sessions' key in response, got: {set(body.keys())!r}"
        )

    # -- AC1 (stronger): annotation is exactly list[SessionRecord] --

    def test_sessions_response_sessions_field_annotation_is_list_of_session_record(
        self,
    ) -> None:
        """AC1 (type annotation proof): sessions field annotation is list[SessionRecord]."""
        import typing  # noqa: PLC0415

        from owlbear_cockpit.routes.read import SessionsResponse  # noqa: PLC0415
        from owlbear_kanban.models import SessionRecord  # noqa: PLC0415

        field = SessionsResponse.model_fields["sessions"]
        origin = typing.get_origin(field.annotation)
        args = typing.get_args(field.annotation)
        assert origin is list, (
            f"Expected list as container type, got {origin!r}"
        )
        assert len(args) == 1, f"Expected single type arg, got args={args!r}"
        assert args[0] is SessionRecord, (
            f"Expected list[SessionRecord] annotation, got args={args!r}"
        )

    # -- AC2 (explicit filter forwarding): ?filter=all routed to view --

    def test_sessions_explicit_all_filter_forwarded_to_view(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC2 (filter proof): explicit ?filter=all is forwarded to CockpitView.list_sessions."""
        from owlbear_cockpit.view import CockpitView  # noqa: PLC0415

        captured_filters: list[str] = []
        original = CockpitView.list_sessions

        def _spy(self_view: CockpitView, *, filter: str = "active") -> list:  # noqa: A002
            captured_filters.append(filter)
            return original(self_view, filter=filter)

        monkeypatch.setattr(CockpitView, "list_sessions", _spy)

        response = client.get("/api/sessions", params={"filter": "all"})
        assert response.status_code == 200
        assert captured_filters == ["all"], (
            "Expected CockpitView.list_sessions called with filter='all', "
            f"got: {captured_filters!r}"
        )

    # -- AC2 (non-empty precondition): per-entry fields on a seeded board --

    def test_sessions_per_entry_fields_with_nonempty_precondition(
        self, client_with_session: TestClient
    ) -> None:
        """AC2 (non-empty guard): board with active claim returns ≥1 session; each has task_id and state."""
        response = client_with_session.get("/api/sessions", params={"filter": "all"})
        assert response.status_code == 200
        body = response.json()
        sessions = body["sessions"]
        assert len(sessions) >= 1, (
            "Expected ≥1 session from board with an active claim — "
            "per-entry assertions would vacuously pass on an empty list"
        )
        for session in sessions:
            assert "task_id" in session, f"Session missing task_id: {session}"
            assert "state" in session, f"Session missing state: {session}"
            assert isinstance(session["task_id"], int)
            assert isinstance(session["state"], str)
