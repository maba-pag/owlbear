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

import time
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from owlbear_kanban import KanbanEngine

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

    from owlbear_cockpit.cache import MtimeScanCache


# ---------------------------------------------------------------------------
# Board fixture helpers
# ---------------------------------------------------------------------------

_CONFIG_YAML = """\
next_id: 1
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
    """Minimal kanban board with 4 tasks covering filter dimensions.

    Task 1: status=todo,       priority=important, tags=[alpha], blocked=False, claimed=False
    Task 2: status=review,     priority=critical,  tags=[beta],  blocked=False, claimed=False
    Task 3: status=in-progress,priority=needed,    tags=[gamma], blocked=True,  claimed=False
    Task 4: status=in-progress,priority=important, tags=[delta], blocked=False, claimed=True
    """
    kanban_dir = _make_board(tmp_path)
    seed_engine = KanbanEngine(kanban_dir)
    seed_engine.create_task(
        "Alpha task", status="todo", priority="important", tags=["alpha"]
    )
    seed_engine.create_task(
        "Beta task", status="review", priority="critical", tags=["beta"]
    )
    seed_engine.create_task(
        "Gamma blocked", status="in-progress", priority="needed", tags=["gamma"]
    )
    seed_engine.create_task(
        "Delta claimed", status="in-progress", priority="important", tags=["delta"]
    )
    # Populate id→filename cache before edits
    seed_engine.list_tasks()
    seed_engine.edit_task("3", blocked=True, block_reason="waiting on dependency")
    seed_engine.claim_task("4")
    return kanban_dir


@pytest.fixture
def engine(board_dir: Path) -> KanbanEngine:
    """KanbanEngine pointed at the test board, cache pre-warmed."""
    eng = KanbanEngine(board_dir)
    eng.list_tasks()  # populate id→filename cache
    return eng


@pytest.fixture
def client(engine: KanbanEngine, cache: MtimeScanCache):
    """FastAPI TestClient with engine injected via dependency_overrides.

    In RED phase, ``get_engine`` does not exist in ``owlbear_cockpit.main``
    so this fixture raises ImportError — all tests using it will ERROR (RED).
    """
    from fastapi.testclient import TestClient  # noqa: PLC0415
    from owlbear_cockpit.deps import get_cache  # noqa: PLC0415
    from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415  # ImportError in RED

    app.dependency_overrides[get_engine] = lambda: engine
    app.dependency_overrides[get_cache] = lambda: cache
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def empty_board_dir(tmp_path: Path) -> Path:
    """Minimal kanban board with no tasks."""
    base = tmp_path / "empty"
    base.mkdir()
    return _make_board(base)


@pytest.fixture
def empty_engine(empty_board_dir: Path) -> KanbanEngine:
    """KanbanEngine pointed at an empty board."""
    return KanbanEngine(empty_board_dir)


@pytest.fixture
def empty_client(empty_engine: KanbanEngine, empty_cache: MtimeScanCache):
    """FastAPI TestClient with an empty-board engine injected."""
    from fastapi.testclient import TestClient  # noqa: PLC0415
    from owlbear_cockpit.deps import get_cache  # noqa: PLC0415
    from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415

    app.dependency_overrides[get_engine] = lambda: empty_engine
    app.dependency_overrides[get_cache] = lambda: empty_cache
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def cache(board_dir: Path) -> MtimeScanCache:
    """Known MtimeScanCache instance for the test board's tasks directory."""
    from owlbear_cockpit.cache import MtimeScanCache  # noqa: PLC0415

    return MtimeScanCache(board_dir / "tasks")


@pytest.fixture
def cache_client(engine: KanbanEngine, cache: MtimeScanCache) -> TestClient:
    """TestClient with get_engine and get_cache both overridden."""
    from fastapi.testclient import TestClient  # noqa: PLC0415

    from owlbear_cockpit.deps import get_cache  # noqa: PLC0415
    from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415

    app.dependency_overrides[get_engine] = lambda: engine
    app.dependency_overrides[get_cache] = lambda: cache
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def empty_cache(empty_board_dir: Path) -> MtimeScanCache:
    """Known MtimeScanCache instance for the empty board's tasks directory."""
    from owlbear_cockpit.cache import MtimeScanCache  # noqa: PLC0415

    return MtimeScanCache(empty_board_dir / "tasks")


@pytest.fixture
def empty_cache_client(
    empty_engine: KanbanEngine,
    empty_cache: MtimeScanCache,
) -> TestClient:
    """TestClient with get_engine and get_cache overridden for the empty board."""
    from fastapi.testclient import TestClient  # noqa: PLC0415

    from owlbear_cockpit.deps import get_cache  # noqa: PLC0415
    from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415

    app.dependency_overrides[get_engine] = lambda: empty_engine
    app.dependency_overrides[get_cache] = lambda: empty_cache
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

    def test_board_response_includes_valid_transitions_dict(
        self, client: TestClient
    ) -> None:
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
                assert isinstance(t, str), (
                    f"target {t!r} for {status!r} is not a string"
                )

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
        for field in (
            "id",
            "title",
            "status",
            "priority",
            "body",
            "updated",
            "created",
        ):
            assert field in body, f"Task detail missing field {field!r}"

    def test_task_detail_nonexistent_id_returns_404_with_id_in_detail(
        self, client: TestClient
    ) -> None:
        """GET /api/tasks/9999 returns 404 with the ID referenced in the error detail."""
        response = client.get("/api/tasks/9999")
        assert response.status_code == 404
        body = response.json()
        assert "detail" not in body
        assert body.get("code") == "ERR_NOT_FOUND"
        message = body.get("message", "")
        assert "9999" in str(message), (
            f"404 message should reference the requested ID '9999', got: {message!r}"
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
        """Response body is a dict with 'sessions' key whose value is a list."""
        response = client.get("/api/sessions", params={"filter": "all"})
        assert response.status_code == 200
        body = response.json()
        assert isinstance(body, dict), (
            f"Expected dict envelope, got {type(body).__name__}: {body!r}"
        )
        assert "sessions" in body, f"Response missing 'sessions' key: {body!r}"
        assert isinstance(body["sessions"], list)

    def test_sessions_each_entry_has_task_id_and_state(
        self, client: TestClient
    ) -> None:
        """Each session entry has task_id (int) and state (str) fields."""
        response = client.get("/api/sessions", params={"filter": "all"})
        assert response.status_code == 200
        body = response.json()
        sessions = body["sessions"]
        for session in sessions:
            assert "task_id" in session, f"Session missing task_id: {session}"
            assert "state" in session, f"Session missing state: {session}"
            assert isinstance(session["task_id"], int)
            assert isinstance(session["state"], str)

    def test_sessions_active_is_default_filter(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """GET /api/sessions (no filter param) defaults to active and returns HTTP 200."""
        from owlbear_cockpit.view import CockpitView

        called_filter: str | None = None
        original = CockpitView.list_sessions

        def _spy_list_sessions(self: CockpitView, filter: str = "active"):  # noqa: A002
            nonlocal called_filter
            called_filter = filter
            return original(self, filter=filter)

        monkeypatch.setattr(CockpitView, "list_sessions", _spy_list_sessions)

        response = client.get("/api/sessions")
        assert response.status_code == 200
        body = response.json()
        assert isinstance(body, dict)
        assert "sessions" in body
        assert isinstance(body["sessions"], list)
        assert called_filter == "active"


@pytest.fixture()
def board_dir_1223(tmp_path: Path) -> Path:
    return _make_board(tmp_path)


@pytest.fixture()
def engine_1223(board_dir_1223: Path) -> KanbanEngine:
    eng = KanbanEngine(board_dir_1223)
    eng.list_tasks()
    return eng


@pytest.fixture()
def client_1223(engine_1223: KanbanEngine):
    from fastapi.testclient import TestClient  # noqa: PLC0415
    from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415

    app.dependency_overrides[get_engine] = lambda: engine_1223
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture()
def board_with_session_dir_1223(tmp_path: Path) -> Path:
    """Board with activity_log enabled and one active claim in activity.jsonl."""
    kanban_dir = tmp_path / "board_session"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    seed_eng = KanbanEngine(kanban_dir, activity_log=True)
    task = seed_eng.create_task("Session task", status="todo")
    seed_eng.list_tasks()
    seed_eng.claim_task(str(task.id))
    return kanban_dir


@pytest.fixture()
def client_with_session_1223(board_with_session_dir_1223: Path):
    from fastapi.testclient import TestClient  # noqa: PLC0415
    from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415

    eng = KanbanEngine(board_with_session_dir_1223, activity_log=True)
    eng.list_tasks()
    app.dependency_overrides[get_engine] = lambda: eng
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture()
def clear_overrides_1223() -> None:
    """Guard against dependency override leakage from merged #1223 tests."""
    from owlbear_cockpit.main import app  # noqa: PLC0415

    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


@pytest.mark.usefixtures("clear_overrides_1223")
class TestFromAC_SessionsEnvelope1223:
    """Promoted unique sessions-envelope checks from task-scoped file #1223."""

    def test_sessions_response_model_importable_with_sessions_field(self) -> None:
        """SessionsResponse is importable from read.py and has a 'sessions' field."""
        from owlbear_cockpit.routes.read import SessionsResponse  # noqa: PLC0415

        assert "sessions" in SessionsResponse.model_fields, (
            "SessionsResponse must have a 'sessions' field"
        )

    def test_sessions_all_filter_returns_dict_with_sessions_key(
        self, client_1223: TestClient
    ) -> None:
        """Happy path: GET /api/sessions?filter=all returns dict with 'sessions'."""
        response = client_1223.get("/api/sessions", params={"filter": "all"})
        assert response.status_code == 200
        body = response.json()
        assert isinstance(body, dict), (
            f"Expected dict envelope, got {type(body).__name__}: {body!r}"
        )
        assert "sessions" in body, f"Response missing 'sessions' key: {body!r}"
        assert isinstance(body["sessions"], list)

    def test_sessions_active_filter_returns_dict_with_sessions_key(
        self, client_1223: TestClient
    ) -> None:
        """Happy path: GET /api/sessions?filter=active returns dict with 'sessions'."""
        response = client_1223.get("/api/sessions", params={"filter": "active"})
        assert response.status_code == 200
        body = response.json()
        assert isinstance(body, dict), (
            f"Expected dict envelope, got {type(body).__name__}: {body!r}"
        )
        assert "sessions" in body, f"Response missing 'sessions' key: {body!r}"

    def test_sessions_no_param_returns_dict_with_sessions_key(
        self, client_1223: TestClient
    ) -> None:
        """Edge: GET /api/sessions (no filter param) returns dict with 'sessions'."""
        response = client_1223.get("/api/sessions")
        assert response.status_code == 200
        body = response.json()
        assert isinstance(body, dict), (
            f"Expected dict envelope, got {type(body).__name__}: {body!r}"
        )
        assert "sessions" in body, f"Response missing 'sessions' key: {body!r}"

    def test_sessions_empty_board_wraps_empty_list(
        self, client_1223: TestClient
    ) -> None:
        """Edge: board with no sessions returns {'sessions': []}, not []."""
        response = client_1223.get("/api/sessions", params={"filter": "all"})
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
        self, client_1223: TestClient
    ) -> None:
        """Boundary: SessionsResponse has one field only: 'sessions'."""
        response = client_1223.get("/api/sessions", params={"filter": "all"})
        assert response.status_code == 200
        body = response.json()
        assert isinstance(body, dict)
        assert set(body.keys()) == {"sessions"}, (
            f"Expected only 'sessions' key in response, got: {set(body.keys())!r}"
        )

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
        assert origin is list, f"Expected list as container type, got {origin!r}"
        assert len(args) == 1, f"Expected single type arg, got args={args!r}"
        assert args[0] is SessionRecord, (
            f"Expected list[SessionRecord] annotation, got args={args!r}"
        )

    def test_sessions_explicit_all_filter_forwarded_to_view(
        self, client_1223: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Explicit ?filter=all is forwarded to CockpitView.list_sessions."""
        from owlbear_cockpit.view import CockpitView  # noqa: PLC0415

        captured_filters: list[str] = []
        original = CockpitView.list_sessions

        def _spy(self_view: CockpitView, *, filter: str = "active") -> list:  # noqa: A002
            captured_filters.append(filter)
            return original(self_view, filter=filter)

        monkeypatch.setattr(CockpitView, "list_sessions", _spy)

        response = client_1223.get("/api/sessions", params={"filter": "all"})
        assert response.status_code == 200
        assert captured_filters == ["all"], (
            "Expected CockpitView.list_sessions called with filter='all', "
            f"got: {captured_filters!r}"
        )

    def test_sessions_per_entry_fields_with_nonempty_precondition(
        self, client_with_session_1223: TestClient
    ) -> None:
        """Seeded board with active claim returns >=1 session with task_id/state."""
        response = client_with_session_1223.get(
            "/api/sessions", params={"filter": "all"}
        )
        assert response.status_code == 200
        body = response.json()
        sessions = body["sessions"]
        assert len(sessions) >= 1, (
            "Expected >=1 session from board with an active claim"
        )
        for session in sessions:
            assert "task_id" in session, f"Session missing task_id: {session}"
            assert "state" in session, f"Session missing state: {session}"
            assert isinstance(session["task_id"], int)
            assert isinstance(session["state"], str)


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


# ---------------------------------------------------------------------------
# AC: block_reason and claimed fields on task summaries (#954)
# ---------------------------------------------------------------------------


class TestFromAC_TaskSummaryFields:
    """Tests that GET /api/tasks exposes block_reason and claimed per task.

    Covers:
    - Task summary response includes block_reason: str | None = None  (AC#1)
    - Task summary response includes claimed: bool = False            (AC#1)
    - Adapter maps block_reason and claimed from engine TaskSummary (AC#2)
    - GET /api/tasks response includes both fields per task     (AC#4)
    - Correct values: block_reason for blocked task, claimed for claimed task (AC arch-review)
    - Default nulls/false for unblocked/unclaimed tasks         (AC arch-review)
    """

    def test_task_summary_has_block_reason_field(self, client: TestClient) -> None:
        """Each task summary in GET /api/tasks includes a 'block_reason' key."""
        response = client.get("/api/tasks")
        assert response.status_code == 200
        tasks = response.json()["tasks"]
        assert len(tasks) > 0
        for task in tasks:
            assert "block_reason" in task, (
                f"Task summary missing 'block_reason': {task}"
            )

    def test_task_summary_has_claimed_field(self, client: TestClient) -> None:
        """Each task summary in GET /api/tasks includes a 'claimed' key."""
        response = client.get("/api/tasks")
        assert response.status_code == 200
        tasks = response.json()["tasks"]
        assert len(tasks) > 0
        for task in tasks:
            assert "claimed" in task, f"Task summary missing 'claimed': {task}"

    def test_blocked_task_block_reason_is_correct_value(
        self, client: TestClient
    ) -> None:
        """The blocked task (task 3) has block_reason == 'waiting on dependency'."""
        response = client.get("/api/tasks", params={"blocked": "true"})
        assert response.status_code == 200
        tasks = response.json()["tasks"]
        assert len(tasks) == 1, f"Expected 1 blocked task, got {len(tasks)}"
        assert tasks[0]["block_reason"] == "waiting on dependency"

    def test_claimed_task_claimed_is_true(self, client: TestClient) -> None:
        """The claimed task (task 4, tag=delta) has claimed == true."""
        response = client.get("/api/tasks", params={"tag": "delta"})
        assert response.status_code == 200
        tasks = response.json()["tasks"]
        assert len(tasks) == 1, f"Expected 1 delta task, got {len(tasks)}"
        assert tasks[0]["claimed"] is True

    def test_unblocked_task_block_reason_is_null(self, client: TestClient) -> None:
        """An unblocked task (task 1) has block_reason == null."""
        response = client.get("/api/tasks", params={"tag": "alpha"})
        assert response.status_code == 200
        tasks = response.json()["tasks"]
        assert len(tasks) == 1, f"Expected 1 alpha task, got {len(tasks)}"
        assert tasks[0]["block_reason"] is None

    def test_unclaimed_task_claimed_is_false(self, client: TestClient) -> None:
        """An unclaimed task (task 1) has claimed == false."""
        response = client.get("/api/tasks", params={"tag": "alpha"})
        assert response.status_code == 200
        tasks = response.json()["tasks"]
        assert len(tasks) == 1, f"Expected 1 alpha task, got {len(tasks)}"
        assert tasks[0]["claimed"] is False

    def test_all_tasks_have_block_reason_and_claimed_with_correct_types(
        self, client: TestClient
    ) -> None:
        """block_reason is str-or-null and claimed is bool for every task summary."""
        response = client.get("/api/tasks")
        assert response.status_code == 200
        tasks = response.json()["tasks"]
        for task in tasks:
            assert task["block_reason"] is None or isinstance(
                task["block_reason"], str
            ), (
                f"block_reason must be str or null, got {task['block_reason']!r} for task {task['id']}"
            )
            assert isinstance(task["claimed"], bool), (
                f"claimed must be bool, got {task['claimed']!r} for task {task['id']}"
            )


# ---------------------------------------------------------------------------
# AC: claimed and claimed_by fields on task detail response (#972)
# ---------------------------------------------------------------------------


class TestFromAC_TaskDetailClaimedFields:
    """Tests for claimed-field behavior on the GET /api/tasks/{id} response.

    Covers:
    - Task detail response includes claimed: bool = False     (AC#1)
    - GET /api/tasks/{id} excludes claimed_by per Brief B D11
    - Unclaimed task (task 1): claimed=False
    - Claimed task (task 4): claimed=True
    """

    def test_task_detail_response_has_claimed_field(self, client: TestClient) -> None:
        """GET /api/tasks/1 response includes a 'claimed' key."""
        response = client.get("/api/tasks/1")
        assert response.status_code == 200
        body = response.json()
        assert "claimed" in body, (
            f"Task detail response missing 'claimed' field: {list(body.keys())}"
        )

    def test_task_detail_response_has_claimed_by_field(
        self, client: TestClient
    ) -> None:
        """GET /api/tasks/1 response excludes the legacy 'claimed_by' key."""
        response = client.get("/api/tasks/1")
        assert response.status_code == 200
        body = response.json()
        assert "claimed_by" not in body, (
            f"Task detail response must not include 'claimed_by': {list(body.keys())}"
        )

    def test_unclaimed_task_detail_claimed_is_false(self, client: TestClient) -> None:
        """Unclaimed task (task 1, tag=alpha): detail response has claimed=false."""
        response = client.get("/api/tasks/1")
        assert response.status_code == 200
        body = response.json()
        assert body["claimed"] is False, (
            f"Expected claimed=false for task 1, got {body['claimed']!r}"
        )

    def test_unclaimed_task_detail_claimed_by_is_null(self, client: TestClient) -> None:
        """Unclaimed task (task 1): detail response omits claimed_by."""
        response = client.get("/api/tasks/1")
        assert response.status_code == 200
        body = response.json()
        assert "claimed_by" not in body, (
            f"Expected no claimed_by field for task 1, got keys {list(body.keys())}"
        )

    def test_claimed_task_detail_claimed_is_true(self, client: TestClient) -> None:
        """Claimed task (task 4, tag=delta): detail response has claimed=true."""
        response = client.get("/api/tasks/4")
        assert response.status_code == 200
        body = response.json()
        assert body["claimed"] is True, (
            f"Expected claimed=true for task 4, got {body['claimed']!r}"
        )

    def test_claimed_task_detail_claimed_by_is_non_null_string(
        self, client: TestClient
    ) -> None:
        """Claimed task (task 4): detail response omits legacy claimed_by."""
        response = client.get("/api/tasks/4")
        assert response.status_code == 200
        body = response.json()
        assert "claimed_by" not in body, (
            f"Expected no claimed_by field for task 4, got keys {list(body.keys())}"
        )

    def test_claimed_field_is_bool_type(self, client: TestClient) -> None:
        """The 'claimed' field in task detail is a bool, not a string or other type."""
        response = client.get("/api/tasks/1")
        assert response.status_code == 200
        body = response.json()
        assert isinstance(body["claimed"], bool), (
            f"claimed must be bool, got {type(body['claimed']).__name__!r}: {body['claimed']!r}"
        )

    def test_claimed_by_field_is_str_or_null(self, client: TestClient) -> None:
        """The task detail response does not expose the legacy claimed_by field."""
        for task_id in ("1", "4"):
            response = client.get(f"/api/tasks/{task_id}")
            assert response.status_code == 200
            body = response.json()
            assert "claimed_by" not in body, (
                f"claimed_by must be absent for task {task_id}, got keys {list(body.keys())}"
            )


class TestFromAC_NewModulesImportable:
    """Coverage for read API module boundaries promoted from archived task tests."""

    def test_cache_module_importable(self) -> None:
        """owlbear_cockpit.cache.MtimeScanCache is importable."""
        from owlbear_cockpit.cache import MtimeScanCache  # noqa: PLC0415, F401

    def test_routes_read_router_importable(self) -> None:
        """owlbear_cockpit.routes.read exposes a FastAPI APIRouter named router."""
        from fastapi import APIRouter  # noqa: PLC0415
        from owlbear_cockpit.routes.read import router  # noqa: PLC0415

        assert isinstance(router, APIRouter), (
            f"routes.read.router must be an APIRouter, got {type(router).__name__}"
        )


class TestFromAC_PydanticResponseModels:
    """Response models remain importable Pydantic models."""

    def test_board_out_is_pydantic_model(self) -> None:
        """BoardOut is a pydantic BaseModel subclass."""
        from pydantic import BaseModel  # noqa: PLC0415
        from owlbear_cockpit.models import BoardOut  # noqa: PLC0415

        assert issubclass(BoardOut, BaseModel), "BoardOut must be a pydantic BaseModel"


class TestFromAC_EmptyBoardEdgeCase:
    """GET /api/tasks on a board with zero task files must not raise an exception."""

    def test_empty_board_tasks_returns_200(self, empty_client: TestClient) -> None:
        """GET /api/tasks on a board with no task files returns HTTP 200."""
        response = empty_client.get("/api/tasks")
        assert response.status_code == 200

    def test_empty_board_tasks_list_is_empty(self, empty_client: TestClient) -> None:
        """GET /api/tasks on an empty board returns an empty task list."""
        response = empty_client.get("/api/tasks")
        assert response.status_code == 200
        body = response.json()
        assert "tasks" in body
        assert body["tasks"] == [], (
            f"Expected empty tasks list for empty board, got {body['tasks']!r}"
        )

    def test_empty_board_tasks_mtime_is_zero(self, empty_client: TestClient) -> None:
        """GET /api/tasks on an empty board returns mtime=0."""
        response = empty_client.get("/api/tasks")
        assert response.status_code == 200
        body = response.json()
        assert "mtime" in body
        assert body["mtime"] == 0, (
            f"Expected mtime=0 for empty board, got {body['mtime']!r}"
        )


class TestFromAC_MtimeScanCacheUnit:
    """Direct unit coverage for MtimeScanCache."""

    def test_mtime_scan_cache_instantiable_with_path(self, tmp_path: Path) -> None:
        """MtimeScanCache can be instantiated with a Path argument."""
        from owlbear_cockpit.cache import MtimeScanCache  # noqa: PLC0415

        cache = MtimeScanCache(tmp_path)
        assert cache is not None

    def test_empty_dir_scan_returns_zero(self, tmp_path: Path) -> None:
        """MtimeScanCache.scan() returns 0 for an empty directory."""
        from owlbear_cockpit.cache import MtimeScanCache  # noqa: PLC0415

        cache = MtimeScanCache(tmp_path)
        assert cache.scan() == 0, (
            "Empty tasks dir must return mtime=0 (max with default=0)"
        )

    def test_non_empty_dir_scan_returns_positive_int(self, tmp_path: Path) -> None:
        """MtimeScanCache.scan() returns a positive integer when files are present."""
        from owlbear_cockpit.cache import MtimeScanCache  # noqa: PLC0415

        (tmp_path / "1-task.md").write_text("# task", encoding="utf-8")
        cache = MtimeScanCache(tmp_path)
        result = cache.scan()
        assert isinstance(result, int), (
            f"scan() must return int, got {type(result).__name__}"
        )
        assert result > 0, "scan() must return positive mtime_ns when files are present"

    def test_scan_returns_robust_signature_not_raw_max_mtime(
        self, tmp_path: Path
    ) -> None:
        """Post-1346 AC1: MtimeScanCache.scan() returns a directory signature (hash)
        that captures file-name set changes, NOT the raw maximum mtime_ns.

        Old contract was 'returns max mtime_ns', which missed deletions of
        non-newest files. New contract: opaque integer signature that changes on
        create, edit, delete, and rename of .md task files.
        """
        from owlbear_cockpit.cache import MtimeScanCache  # noqa: PLC0415

        first = tmp_path / "1-task.md"
        first.write_text("# task 1", encoding="utf-8")
        time.sleep(0.01)
        second = tmp_path / "2-task.md"
        second.write_text("# task 2", encoding="utf-8")

        raw_max_mtime = max(first.stat().st_mtime_ns, second.stat().st_mtime_ns)
        cache = MtimeScanCache(tmp_path)
        sig = cache.scan()
        assert isinstance(sig, int), f"scan() must return int, got {type(sig).__name__}"
        assert sig != raw_max_mtime, (
            "scan() must NOT return the raw max mtime_ns. Post-1346 it returns a "
            "directory signature (hash) that detects deletions and renames, not "
            f"just max mtime. Got {sig!r} == raw_max {raw_max_mtime!r}."
        )
        # Signature must change when the file-name set changes (deletion detection)
        first.unlink()
        sig_after_delete = cache.scan()
        assert sig_after_delete != sig, (
            f"scan() must return a different signature after deleting a file. "
            f"before={sig!r}, after={sig_after_delete!r}. "
            f"Max-mtime-only scan would NOT detect this deletion."
        )

    def test_scan_is_repeatable_with_no_changes(self, tmp_path: Path) -> None:
        """Two consecutive scan() calls with no file changes return the same value."""
        from owlbear_cockpit.cache import MtimeScanCache  # noqa: PLC0415

        (tmp_path / "1-task.md").write_text("# task", encoding="utf-8")
        cache = MtimeScanCache(tmp_path)
        assert cache.scan() == cache.scan(), (
            "scan() must return a stable value when files are unchanged"
        )


class TestFromAC_EngineReloadOnMtimeChange:
    """New tasks created between requests must be reflected in the task list."""

    def test_new_task_appears_in_list_after_creation(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """A task created after the first request appears in a subsequent request."""
        first = client.get("/api/tasks")
        assert first.status_code == 200
        count_before = len(first.json()["tasks"])

        engine.create_task("New task via engine", status="todo", priority="important")

        second = client.get("/api/tasks")
        assert second.status_code == 200
        count_after = len(second.json()["tasks"])
        assert count_after > count_before, (
            "New task must appear in subsequent GET /api/tasks response "
            f"(before={count_before}, after={count_after})"
        )

    def test_mtime_increases_after_new_task_created(
        self, client: TestClient, engine: KanbanEngine
    ) -> None:
        """Creating a new task file increases the mtime returned by GET /api/tasks."""
        first = client.get("/api/tasks")
        assert first.status_code == 200
        mtime_before = first.json()["mtime"]

        engine.create_task("Another new task", status="backlog", priority="someday")

        second = client.get("/api/tasks")
        assert second.status_code == 200
        mtime_after = second.json()["mtime"]
        assert mtime_after != mtime_before, (
            "signature must change after a new task file is created "
            f"(before={mtime_before}, after={mtime_after})"
        )


class TestFromAC_CacheHitShortCircuit:
    """Cache hits return cached tasks without reloading through the engine."""

    def test_cache_hit_skips_engine_call(
        self,
        cache_client: TestClient,
        engine: KanbanEngine,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """engine.list_tasks() is not called on second GET /api/tasks when mtime is unchanged."""
        first = cache_client.get("/api/tasks")
        assert first.status_code == 200

        call_count = 0
        original = engine.list_tasks

        def counting(*args: object, **kwargs: object) -> object:
            nonlocal call_count
            call_count += 1
            return original(*args, **kwargs)

        monkeypatch.setattr(engine, "list_tasks", counting)

        second = cache_client.get("/api/tasks")
        assert second.status_code == 200
        assert call_count == 0, (
            f"engine.list_tasks() called {call_count} times on cache hit, expected 0"
        )

    def test_has_changed_called_updates_last_mtime(
        self,
        cache_client: TestClient,
        cache: MtimeScanCache,
    ) -> None:
        """cache.last_mtime is updated after the first GET /api/tasks."""
        assert cache.last_mtime == 0, (
            "Cache must start with last_mtime=0 before any request"
        )
        cache_client.get("/api/tasks")
        assert cache.last_mtime > 0, (
            "cache.last_mtime must be updated after GET /api/tasks — "
            "has_changed() must be called in the route handler"
        )

    def test_status_filter_on_cache_hit_skips_engine(
        self,
        cache_client: TestClient,
        engine: KanbanEngine,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """engine.list_tasks() is not called when a status filter is applied on cache hit."""
        cache_client.get("/api/tasks")

        call_count = 0
        original = engine.list_tasks

        def counting(*args: object, **kwargs: object) -> object:
            nonlocal call_count
            call_count += 1
            return original(*args, **kwargs)

        monkeypatch.setattr(engine, "list_tasks", counting)

        response = cache_client.get("/api/tasks?status=todo")
        assert response.status_code == 200
        assert call_count == 0, (
            f"engine.list_tasks() called {call_count} times on status-filtered cache hit, expected 0"
        )

    def test_priority_filter_on_cache_hit_skips_engine(
        self,
        cache_client: TestClient,
        engine: KanbanEngine,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """engine.list_tasks() is not called when a priority filter is applied on cache hit."""
        cache_client.get("/api/tasks")

        call_count = 0
        original = engine.list_tasks

        def counting(*args: object, **kwargs: object) -> object:
            nonlocal call_count
            call_count += 1
            return original(*args, **kwargs)

        monkeypatch.setattr(engine, "list_tasks", counting)

        response = cache_client.get("/api/tasks?priority=important")
        assert response.status_code == 200
        assert call_count == 0, (
            f"engine.list_tasks() called {call_count} times on priority-filtered cache hit, expected 0"
        )

    def test_tag_filter_on_cache_hit_skips_engine(
        self,
        cache_client: TestClient,
        engine: KanbanEngine,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """engine.list_tasks() is not called when a tag filter is applied on cache hit."""
        cache_client.get("/api/tasks")

        call_count = 0
        original = engine.list_tasks

        def counting(*args: object, **kwargs: object) -> object:
            nonlocal call_count
            call_count += 1
            return original(*args, **kwargs)

        monkeypatch.setattr(engine, "list_tasks", counting)

        response = cache_client.get("/api/tasks?tag=scope%3Ax")
        assert response.status_code == 200
        assert call_count == 0, (
            f"engine.list_tasks() called {call_count} times on tag-filtered cache hit, expected 0"
        )

    def test_blocked_filter_on_cache_hit_skips_engine(
        self,
        cache_client: TestClient,
        engine: KanbanEngine,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """engine.list_tasks() is not called when a blocked filter is applied on cache hit."""
        cache_client.get("/api/tasks")

        call_count = 0
        original = engine.list_tasks

        def counting(*args: object, **kwargs: object) -> object:
            nonlocal call_count
            call_count += 1
            return original(*args, **kwargs)

        monkeypatch.setattr(engine, "list_tasks", counting)

        response = cache_client.get("/api/tasks?blocked=false")
        assert response.status_code == 200
        assert call_count == 0, (
            f"engine.list_tasks() called {call_count} times on blocked-filtered cache hit, expected 0"
        )

    def test_status_filter_returns_correct_tasks_on_cache_hit(
        self,
        cache_client: TestClient,
        engine: KanbanEngine,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Status filtering on a cache hit returns only matching tasks."""
        cache_client.get("/api/tasks")

        call_count = 0
        original = engine.list_tasks

        def counting(*args: object, **kwargs: object) -> object:
            nonlocal call_count
            call_count += 1
            return original(*args, **kwargs)

        monkeypatch.setattr(engine, "list_tasks", counting)

        response = cache_client.get("/api/tasks?status=todo")
        assert response.status_code == 200
        assert call_count == 0, "engine.list_tasks() must not be called on cache hit"
        tasks = response.json()["tasks"]
        assert len(tasks) > 0, "Expected at least 1 'todo' task in test board"
        assert all(task["status"] == "todo" for task in tasks), (
            f"All returned tasks must have status='todo' on filtered cache hit, got {tasks!r}"
        )

    def test_multiple_consecutive_requests_all_skip_engine(
        self,
        cache_client: TestClient,
        engine: KanbanEngine,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """engine.list_tasks() is not called on later unchanged requests."""
        cache_client.get("/api/tasks")

        call_count = 0
        original = engine.list_tasks

        def counting(*args: object, **kwargs: object) -> object:
            nonlocal call_count
            call_count += 1
            return original(*args, **kwargs)

        monkeypatch.setattr(engine, "list_tasks", counting)

        for _ in range(3):
            response = cache_client.get("/api/tasks")
            assert response.status_code == 200

        assert call_count == 0, (
            f"engine.list_tasks() called {call_count} times across 3 consecutive cache-hit requests, expected 0"
        )

    def test_first_request_populates_cache_tasks(
        self,
        cache_client: TestClient,
        cache: MtimeScanCache,
    ) -> None:
        """cache.tasks is populated with all tasks after the first GET /api/tasks."""
        assert cache.tasks == [], "cache.tasks must start empty"
        cache_client.get("/api/tasks")
        assert len(cache.tasks) > 0, (
            "cache.tasks must be populated after first GET /api/tasks — "
            "the route must store engine results in cache.tasks on cache miss"
        )

    def test_empty_board_second_request_skips_engine_call(
        self,
        empty_cache_client: TestClient,
        empty_engine: KanbanEngine,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A cached empty task list is treated as a valid cache hit."""
        first = empty_cache_client.get("/api/tasks")
        assert first.status_code == 200
        assert first.json()["tasks"] == [], "Empty board must return empty task list"

        call_count = 0
        original = empty_engine.list_tasks

        def counting(*args: object, **kwargs: object) -> object:
            nonlocal call_count
            call_count += 1
            return original(*args, **kwargs)

        monkeypatch.setattr(empty_engine, "list_tasks", counting)

        second = empty_cache_client.get("/api/tasks")
        assert second.status_code == 200
        assert second.json()["tasks"] == [], (
            "Second empty-board response must also be empty"
        )
        assert call_count == 0, (
            f"engine.list_tasks() called {call_count} times on second unchanged empty-board request — cached [] must be treated as a valid cache hit"
        )
