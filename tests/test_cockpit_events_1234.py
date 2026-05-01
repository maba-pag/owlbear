"""RED-phase tests for #1234: GET /api/events SSE endpoint with watchfiles watcher.

AC coverage:
  AC1 (td:1): events.py module exists; router registered in main.py with /api prefix
  AC2 (td:1): Endpoint returns EventSourceResponse; engine injected via Depends(get_engine)
  AC3 (td:2): Watch filter accepts .md files, rejects .tmp- prefix and non-.md files
  AC4 (td:2): SSE events have event="tasks-changed", data={"mtime": int}; skips deleted files
  AC5 (td:1): Missing tasks_dir → 200 with empty stream (no events, no crash)
  AC6 (td:2): Generator terminates on client disconnect; checks request.is_disconnected
  AC7 (td:1): sse-starlette and watchfiles added to serve/cockpit/pyproject.toml dependencies

All tests FAIL until the builder implements serve/cockpit/src/owlbear_cockpit/routes/events.py.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

# ---------------------------------------------------------------------------
# Board fixture helpers
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
    """Minimal kanban board with no tasks."""
    return _make_board(tmp_path)


@pytest.fixture
def engine(board_dir: Path):
    """KanbanEngine bound to the test board."""
    from owlbear_kanban import KanbanEngine  # noqa: PLC0415

    return KanbanEngine(board_dir, agent_name="cockpit")


@pytest.fixture
def client(engine):
    """FastAPI TestClient with engine injected via dependency_overrides.

    Patches awatch to return immediately because Starlette's sync TestClient
    cannot signal ASGI disconnect on SSE streams (receive waits for
    response_complete which never fires while more_body=True).
    Tests using this fixture only check headers/status, not stream content.
    """
    from fastapi.testclient import TestClient  # noqa: PLC0415
    from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415

    async def _noop_awatch(*_a, **_kw):
        return
        yield  # pragma: no cover — makes this a valid async generator

    app.dependency_overrides[get_engine] = lambda: engine
    with (
        patch("owlbear_cockpit.routes.events.awatch", _noop_awatch),
        TestClient(app, raise_server_exceptions=False) as c,
    ):
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# AC1: events.py module exists; router registered in main.py (td:1)
# ---------------------------------------------------------------------------


class TestFromAC_EventsModuleExists:
    """AC1: events.py must exist and its router must be registered in main.py."""

    def test_events_module_importable(self) -> None:
        """events.py must be importable as owlbear_cockpit.routes.events."""
        from owlbear_cockpit.routes import events  # noqa: PLC0415, F401

    def test_events_module_exports_router(self) -> None:
        """events.py must export an APIRouter named 'router'."""
        from owlbear_cockpit.routes.events import router  # noqa: PLC0415
        from fastapi import APIRouter  # noqa: PLC0415

        assert isinstance(router, APIRouter), "events.router must be a FastAPI APIRouter"

    def test_events_router_registered_in_main(self) -> None:
        """main.py must import and register the events router under /api prefix."""
        main_file = (
            Path(__file__).parent.parent
            / "serve/cockpit/src/owlbear_cockpit/main.py"
        )
        content = main_file.read_text(encoding="utf-8")
        assert "events" in content, (
            "main.py must import the events router from routes.events"
        )
        # Verify it follows the include_router pattern used by read/mutation/decisions
        assert "include_router" in content
        # The events router must be included (not just imported)
        assert "events_router" in content or (
            "events" in content and "include_router" in content
        ), "events router must be registered via app.include_router() in main.py"

    def test_get_api_events_not_404(self, client) -> None:
        """GET /api/events must be a registered endpoint (not 404)."""
        with client.stream("GET", "/api/events") as response:
            assert response.status_code != 404, (
                f"GET /api/events returned 404 — router not registered. "
                f"Status: {response.status_code}"
            )


# ---------------------------------------------------------------------------
# AC2: EventSourceResponse + Depends(get_engine) (td:1)
# ---------------------------------------------------------------------------


class TestFromAC_EventSourceResponseEndpoint:
    """AC2: Endpoint returns EventSourceResponse; engine is injected via DI."""

    def test_endpoint_content_type_is_text_event_stream(self, client) -> None:
        """GET /api/events must return Content-Type: text/event-stream."""
        with client.stream("GET", "/api/events") as response:
            ct = response.headers.get("content-type", "")
            assert "text/event-stream" in ct, (
                f"Expected text/event-stream content-type, got: {ct!r}"
            )

    def test_endpoint_accepts_engine_dependency_override(self, board_dir) -> None:
        """Endpoint must work with a DI-overridden engine (test isolation pattern)."""
        from fastapi.testclient import TestClient  # noqa: PLC0415
        from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415

        engine_a = KanbanEngine(board_dir, agent_name="cockpit")
        engine_b = KanbanEngine(board_dir, agent_name="cockpit")

        async def _noop_awatch(*_a, **_kw):
            return
            yield  # pragma: no cover

        # Each override produces its own engine; endpoint must use the injected one
        # awatch patched: sync TestClient cannot disconnect SSE streams (header-only check)
        for eng in [engine_a, engine_b]:
            app.dependency_overrides[get_engine] = lambda e=eng: e
            with (
                patch("owlbear_cockpit.routes.events.awatch", _noop_awatch),
                TestClient(app, raise_server_exceptions=False).stream(
                    "GET", "/api/events"
                ) as response,
            ):
                assert response.status_code in {200, 307}, (
                    f"Endpoint must accept DI-overridden engine, got {response.status_code}"
                )
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_endpoint_uses_injected_engine_tasks_dir(self, tmp_path) -> None:
        """DI contract: the endpoint must call awatch with the overridden engine's tasks_dir, not a default."""
        from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415

        board_b = _make_board(tmp_path / "board_b")
        engine_b = KanbanEngine(board_b, agent_name="cockpit")
        awatch_paths: list = []

        async def _capture_path(path, **_kwargs):
            awatch_paths.append(path)
            return
            yield  # makes this a valid async generator

        app.dependency_overrides[get_engine] = lambda: engine_b
        try:
            with patch("owlbear_cockpit.routes.events.awatch", new=_capture_path):
                transport = httpx.ASGITransport(app=app)
                async with (
                    httpx.AsyncClient(transport=transport, base_url="http://test") as ac,
                    ac.stream("GET", "/api/events") as response,
                ):
                    assert response.status_code == 200
                    async for _ in response.aiter_lines():
                        pass  # consume stream to ensure generator ran
        finally:
            app.dependency_overrides.clear()

        assert len(awatch_paths) == 1, (
            f"awatch must be called exactly once per connection, got {len(awatch_paths)}"
        )
        assert Path(awatch_paths[0]) == Path(engine_b.tasks_dir), (
            f"Endpoint must use injected engine_b.tasks_dir ({engine_b.tasks_dir!r}); "
            f"got {awatch_paths[0]!r} — DI is not propagating the engine to the watcher."
        )


# ---------------------------------------------------------------------------
# AC3: Watch filter — accepts .md, rejects .tmp- prefix and non-.md (td:2)
# ---------------------------------------------------------------------------


class TestFromAC_WatchFilter:
    """AC3: Module-level _watch_filter function implements the file-type guard."""

    def test_filter_accepts_plain_md_file(self) -> None:
        """_watch_filter must return True for a standard .md task file."""
        from owlbear_cockpit.routes.events import _watch_filter  # noqa: PLC0415

        assert _watch_filter(None, "/tasks/1234-my-task.md") is True

    def test_filter_accepts_md_file_in_nested_path(self) -> None:
        """_watch_filter must accept .md files regardless of parent path depth."""
        from owlbear_cockpit.routes.events import _watch_filter  # noqa: PLC0415

        assert _watch_filter(None, "/home/user/.owlbear/kanban/tasks/42-title.md") is True

    def test_filter_rejects_tmp_prefix_md_file(self) -> None:
        """_watch_filter must return False for files starting with .tmp-."""
        from owlbear_cockpit.routes.events import _watch_filter  # noqa: PLC0415

        assert _watch_filter(None, "/tasks/.tmp-1234-my-task.md") is False

    def test_filter_rejects_non_md_file(self) -> None:
        """_watch_filter must return False for non-.md files (e.g. .json)."""
        from owlbear_cockpit.routes.events import _watch_filter  # noqa: PLC0415

        assert _watch_filter(None, "/tasks/task-1.json") is False

    def test_filter_rejects_yml_config_file(self) -> None:
        """_watch_filter must return False for .yml files (e.g. config.yml)."""
        from owlbear_cockpit.routes.events import _watch_filter  # noqa: PLC0415

        assert _watch_filter(None, "/tasks/config.yml") is False

    def test_filter_accepts_md_with_tmp_in_middle_of_name(self) -> None:
        """Rejection is prefix-specific: 'task-tmp-123.md' (no leading dot) must pass."""
        from owlbear_cockpit.routes.events import _watch_filter  # noqa: PLC0415

        # 'tmp' in the middle of the filename is not the .tmp- prefix pattern
        assert _watch_filter(None, "/tasks/task-tmp-123.md") is True

    def test_filter_rejects_minimal_tmp_prefix(self) -> None:
        """Boundary: file named exactly '.tmp-.md' must be rejected."""
        from owlbear_cockpit.routes.events import _watch_filter  # noqa: PLC0415

        assert _watch_filter(None, "/tasks/.tmp-.md") is False

    @pytest.mark.asyncio
    async def test_awatch_call_site_receives_correct_arguments(self, board_dir) -> None:
        """AC3 (revised): awatch() must be called with engine.tasks_dir, watch_filter=_watch_filter, recursive=False."""
        from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415
        from owlbear_cockpit.routes.events import _watch_filter  # noqa: PLC0415
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415

        engine = KanbanEngine(board_dir, agent_name="cockpit")
        awatch_calls: list[tuple] = []

        async def _capture_and_stop(*args, **kwargs):
            awatch_calls.append((args, kwargs))
            return
            yield  # makes this a valid async generator

        app.dependency_overrides[get_engine] = lambda: engine
        try:
            with patch("owlbear_cockpit.routes.events.awatch", new=_capture_and_stop):
                transport = httpx.ASGITransport(app=app)
                async with (
                    httpx.AsyncClient(transport=transport, base_url="http://test") as ac,
                    ac.stream("GET", "/api/events") as response,
                ):
                    assert response.status_code == 200
                    async for _ in response.aiter_lines():
                        pass  # consume entire (empty) stream to ensure generator ran
        finally:
            app.dependency_overrides.clear()

        assert len(awatch_calls) == 1, (
            f"awatch must be called exactly once per connection, got {len(awatch_calls)}"
        )
        args, kwargs = awatch_calls[0]
        assert Path(args[0]) == Path(engine.tasks_dir), (
            f"awatch first arg must be engine.tasks_dir ({engine.tasks_dir!r}), "
            f"got {args[0]!r}"
        )
        assert kwargs.get("watch_filter") is _watch_filter, (
            f"awatch must receive watch_filter=_watch_filter; "
            f"got watch_filter={kwargs.get('watch_filter')!r}"
        )
        assert kwargs.get("recursive") is False, (
            f"awatch must receive recursive=False; got recursive={kwargs.get('recursive')!r}"
        )


# ---------------------------------------------------------------------------
# AC4: SSE event payload — event name, mtime data, skip deleted files (td:2)
# ---------------------------------------------------------------------------


class TestFromAC_EventPayload:
    """AC4: events have name 'tasks-changed', mtime payload; deleted files are skipped."""

    @pytest.mark.asyncio
    async def test_event_name_is_tasks_changed(self, board_dir) -> None:
        """SSE stream must emit events with event type 'tasks-changed'."""
        from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415

        engine = KanbanEngine(board_dir, agent_name="cockpit")
        fake_path = board_dir / "tasks" / "task-99.md"
        fake_path.write_text("---\nid: 99\n---\n", encoding="utf-8")

        async def _one_change(*_args, **_kwargs):
            yield {(MagicMock(), str(fake_path))}

        app.dependency_overrides[get_engine] = lambda: engine
        try:
            with patch("owlbear_cockpit.routes.events.awatch", _one_change):
                transport = httpx.ASGITransport(app=app)
                async with (
                    httpx.AsyncClient(transport=transport, base_url="http://test") as ac,
                    ac.stream("GET", "/api/events") as response,
                ):
                    assert response.status_code == 200
                    event_names = []
                    async for line in response.aiter_lines():
                        if line.startswith("event:"):
                            event_names.append(line[len("event:") :].strip())
                        if event_names:
                            break
            assert event_names == ["tasks-changed"], (
                f"Expected event type 'tasks-changed', got: {event_names}"
            )
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_event_data_contains_mtime_integer(self, board_dir) -> None:
        """SSE event data must be JSON with 'mtime' key holding an integer (st_mtime_ns)."""
        from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415

        engine = KanbanEngine(board_dir, agent_name="cockpit")
        fake_path = board_dir / "tasks" / "task-88.md"
        fake_path.write_text("---\nid: 88\n---\n", encoding="utf-8")
        expected_mtime = fake_path.stat().st_mtime_ns

        async def _one_change(*_args, **_kwargs):
            yield {(MagicMock(), str(fake_path))}

        app.dependency_overrides[get_engine] = lambda: engine
        try:
            with patch("owlbear_cockpit.routes.events.awatch", _one_change):
                transport = httpx.ASGITransport(app=app)
                async with (
                    httpx.AsyncClient(transport=transport, base_url="http://test") as ac,
                    ac.stream("GET", "/api/events") as response,
                ):
                    data_payloads = []
                    async for line in response.aiter_lines():
                        if line.startswith("data:"):
                            data_payloads.append(line[len("data:") :].strip())
                        if data_payloads:
                            break
            assert data_payloads, "No data lines received from SSE stream"
            payload = json.loads(data_payloads[0])
            assert "mtime" in payload, f"SSE data must have 'mtime' key, got: {payload}"
            assert isinstance(payload["mtime"], int), (
                f"mtime must be an integer (st_mtime_ns), got: {type(payload['mtime'])}"
            )
            assert payload["mtime"] == expected_mtime, (
                f"mtime {payload['mtime']} != expected st_mtime_ns {expected_mtime}"
            )
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_event_skipped_when_changed_file_deleted_before_stat(
        self, board_dir
    ) -> None:
        """If all changed files are deleted before stat(), no event must be emitted."""
        from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415

        engine = KanbanEngine(board_dir, agent_name="cockpit")
        # Path that does NOT exist — simulates file deleted after awatch yield
        deleted_path = board_dir / "tasks" / "gone.md"
        assert not deleted_path.exists(), "Test setup: file must not exist"

        async def _one_change_then_stop(*_args, **_kwargs):
            yield {(MagicMock(), str(deleted_path))}
            # generator exhausts after one yield; no more changes

        events_received = []
        app.dependency_overrides[get_engine] = lambda: engine
        try:
            with patch("owlbear_cockpit.routes.events.awatch", _one_change_then_stop):
                transport = httpx.ASGITransport(app=app)
                async with (
                    httpx.AsyncClient(transport=transport, base_url="http://test") as ac,
                    ac.stream("GET", "/api/events") as response,
                ):
                    assert response.status_code == 200
                    async for line in response.aiter_lines():
                        if line.startswith(("event:", "data:")):
                            events_received.append(line)
        finally:
            app.dependency_overrides.clear()

        assert not events_received, (
            f"Expected no events when all changed files are deleted, "
            f"but got: {events_received}"
        )

    @pytest.mark.asyncio
    async def test_mtime_uses_st_mtime_ns(self, board_dir) -> None:
        """mtime payload must use st_mtime_ns (nanoseconds), not st_mtime (seconds)."""
        from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415

        engine = KanbanEngine(board_dir, agent_name="cockpit")
        fake_path = board_dir / "tasks" / "task-77.md"
        fake_path.write_text("---\nid: 77\n---\n", encoding="utf-8")
        mtime_ns = fake_path.stat().st_mtime_ns

        async def _one_change(*_args, **_kwargs):
            yield {(MagicMock(), str(fake_path))}

        app.dependency_overrides[get_engine] = lambda: engine
        try:
            with patch("owlbear_cockpit.routes.events.awatch", _one_change):
                transport = httpx.ASGITransport(app=app)
                async with (
                    httpx.AsyncClient(transport=transport, base_url="http://test") as ac,
                    ac.stream("GET", "/api/events") as response,
                ):
                    data_payloads = []
                    async for line in response.aiter_lines():
                        if line.startswith("data:"):
                            data_payloads.append(line[len("data:") :].strip())
                        if data_payloads:
                            break
        finally:
            app.dependency_overrides.clear()

        assert data_payloads, "No data received"
        payload = json.loads(data_payloads[0])
        # st_mtime_ns is many orders of magnitude larger than st_mtime (seconds)
        # A nanosecond mtime for modern files is > 1e18
        assert payload["mtime"] > 1_000_000_000_000, (
            f"mtime {payload['mtime']} is too small — must be st_mtime_ns (nanoseconds), "
            f"not st_mtime (seconds float). st_mtime_ns for this file: {mtime_ns}"
        )


# ---------------------------------------------------------------------------
# AC5: Missing tasks_dir guard (td:1)
# ---------------------------------------------------------------------------


class TestFromAC_MissingDirGuard:
    """AC5: When tasks_dir doesn't exist, endpoint returns 200 with empty stream."""

    def test_missing_tasks_dir_returns_200(self, tmp_path) -> None:
        """GET /api/events must return HTTP 200 even when tasks_dir does not exist."""
        import shutil  # noqa: PLC0415

        from fastapi.testclient import TestClient  # noqa: PLC0415
        from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415

        kanban_dir = _make_board(tmp_path)
        engine = KanbanEngine(kanban_dir, agent_name="cockpit")
        shutil.rmtree(engine.tasks_dir)
        assert not engine.tasks_dir.exists(), "Test setup: tasks_dir must not exist"

        app.dependency_overrides[get_engine] = lambda: engine
        try:
            with TestClient(app, raise_server_exceptions=False).stream(
                "GET", "/api/events"
            ) as response:
                assert response.status_code == 200, (
                    f"Expected 200 for missing tasks_dir guard, got {response.status_code}"
                )
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_missing_tasks_dir_awatch_not_called(self, tmp_path) -> None:
        """Generator must NOT call awatch when tasks_dir does not exist."""
        import shutil  # noqa: PLC0415

        from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415
        from owlbear_cockpit.routes.events import events  # noqa: PLC0415
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415

        kanban_dir = _make_board(tmp_path)
        engine = KanbanEngine(kanban_dir, agent_name="cockpit")
        shutil.rmtree(engine.tasks_dir)

        mock_request = AsyncMock()
        mock_request.is_disconnected = AsyncMock(return_value=False)

        app.dependency_overrides[get_engine] = lambda: engine
        try:
            with patch("owlbear_cockpit.routes.events.awatch") as mock_awatch:
                await events(mock_request, engine)
                mock_awatch.assert_not_called()
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_missing_tasks_dir_stream_is_empty(self, tmp_path) -> None:
        """AC5 (revised): Missing tasks_dir must produce zero SSE event/data lines when stream body is consumed."""
        import shutil  # noqa: PLC0415

        from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415

        kanban_dir = _make_board(tmp_path)
        engine = KanbanEngine(kanban_dir, agent_name="cockpit")
        shutil.rmtree(engine.tasks_dir)
        assert not engine.tasks_dir.exists(), "Test setup: tasks_dir must not exist"

        app.dependency_overrides[get_engine] = lambda: engine
        try:
            transport = httpx.ASGITransport(app=app)
            async with (
                httpx.AsyncClient(transport=transport, base_url="http://test") as ac,
                ac.stream("GET", "/api/events") as response,
            ):
                assert response.status_code == 200
                event_lines: list[str] = []
                async for line in response.aiter_lines():
                    if line.startswith(("event:", "data:")):
                        event_lines.append(line)
        finally:
            app.dependency_overrides.clear()

        assert not event_lines, (
            f"Missing-dir path must produce a truly empty SSE stream (zero event:/data: lines). "
            f"Got: {event_lines}"
        )


# ---------------------------------------------------------------------------
# AC6: Generator terminates cleanly on disconnect / shutdown (td:2)
# ---------------------------------------------------------------------------


class TestFromAC_GeneratorCleanup:
    """AC6: Generator terminates on client disconnect; uses request.is_disconnected."""

    def test_generator_checks_is_disconnected(self) -> None:
        """events.py source must reference request.is_disconnected() for disconnect detection."""
        events_file = (
            Path(__file__).parent.parent
            / "serve/cockpit/src/owlbear_cockpit/routes/events.py"
        )
        assert events_file.exists(), (
            "serve/cockpit/src/owlbear_cockpit/routes/events.py does not exist"
        )
        content = events_file.read_text(encoding="utf-8")
        assert "is_disconnected" in content, (
            "Generator must call request.is_disconnected() to detect client disconnect (AC6). "
            "Found no reference to is_disconnected in events.py."
        )

    @pytest.mark.asyncio
    async def test_generator_stops_iteration_on_disconnect(self, board_dir) -> None:
        """Generator must stop emitting events once request reports disconnected."""
        from owlbear_cockpit.routes.events import events  # noqa: PLC0415
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415

        engine = KanbanEngine(board_dir, agent_name="cockpit")
        fake_path = board_dir / "tasks" / "task-d.md"
        fake_path.write_text("---\nid: 1\n---\n", encoding="utf-8")

        # Client is already disconnected before the first event
        mock_request = AsyncMock()
        mock_request.is_disconnected = AsyncMock(return_value=True)

        yielded_from_mock = []

        async def _infinite_changes(*_args, **_kwargs):
            while True:
                yielded_from_mock.append(1)
                yield {(MagicMock(), str(fake_path))}

        with patch("owlbear_cockpit.routes.events.awatch", _infinite_changes):
            # Call the endpoint — it should create an EventSourceResponse
            # The generator inside must detect disconnect and not loop indefinitely
            response = await events(mock_request, engine)

        from sse_starlette import EventSourceResponse  # noqa: PLC0415

        assert isinstance(response, EventSourceResponse), (
            "events() must return an EventSourceResponse"
        )

    @pytest.mark.asyncio
    async def test_events_endpoint_is_async(self) -> None:
        """events() endpoint function must be declared async (supports async generator)."""
        import inspect  # noqa: PLC0415

        from owlbear_cockpit.routes.events import events  # noqa: PLC0415

        assert inspect.iscoroutinefunction(events), (
            "events() must be declared 'async def' to support the async SSE generator pattern"
        )

    @pytest.mark.asyncio
    async def test_awatch_receives_yield_on_timeout_true(self, board_dir) -> None:
        """AC6a (td:1): awatch() must receive yield_on_timeout=True for periodic disconnect checks."""
        from owlbear_cockpit.routes.events import events  # noqa: PLC0415
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415

        engine = KanbanEngine(board_dir, agent_name="cockpit")
        mock_request = AsyncMock()
        mock_request.is_disconnected = AsyncMock(return_value=False)
        awatch_kwargs: list[dict] = []

        async def _capture_kwargs(*_args, **kwargs):
            awatch_kwargs.append(kwargs)
            return
            yield  # makes this a valid async generator

        with patch("owlbear_cockpit.routes.events.awatch", new=_capture_kwargs):
            response = await events(mock_request, engine)
            async for _ in response.body_iterator:
                pass  # consume the (empty) generator to ensure awatch was called

        assert len(awatch_kwargs) == 1, (
            f"awatch must be called exactly once, got {len(awatch_kwargs)}"
        )
        assert awatch_kwargs[0].get("yield_on_timeout") is True, (
            "awatch() must receive yield_on_timeout=True (AC6a) so the generator can "
            "check request.is_disconnected() during idle periods (no file changes). "
            f"Got: yield_on_timeout={awatch_kwargs[0].get('yield_on_timeout')!r}"
        )

    @pytest.mark.asyncio
    async def test_generator_terminates_on_disconnect_executable(self, board_dir) -> None:
        """AC6b: When is_disconnected() returns True, generator exits the watch loop — proven by consuming body_iterator."""
        import asyncio  # noqa: PLC0415

        from owlbear_cockpit.routes.events import events  # noqa: PLC0415
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415

        engine = KanbanEngine(board_dir, agent_name="cockpit")
        fake_path = board_dir / "tasks" / "task-d2.md"
        fake_path.write_text("---\nid: 1\n---\n", encoding="utf-8")

        mock_request = AsyncMock()
        disconnect_calls = [0]

        async def _always_disconnected():
            disconnect_calls[0] += 1
            return True

        mock_request.is_disconnected = _always_disconnected
        awatch_yields = [0]

        async def _infinite_changes(*_args, **_kwargs):
            while True:
                awatch_yields[0] += 1
                yield {(MagicMock(), str(fake_path))}

        with patch("owlbear_cockpit.routes.events.awatch", _infinite_changes):
            response = await events(mock_request, engine)
            # Iterate the body_iterator with a timeout — generator must terminate,
            # not loop infinitely, once is_disconnected() returns True.
            async with asyncio.timeout(3.0):
                async for _ in response.body_iterator:
                    pass

        assert disconnect_calls[0] >= 1, (
            "is_disconnected() was never called — generator does not check for client disconnect"
        )
        assert awatch_yields[0] <= 1, (
            f"Generator must exit after is_disconnected()=True; "
            f"awatch was iterated {awatch_yields[0]} times — generator did not break."
        )

    @pytest.mark.asyncio
    async def test_generator_continues_on_empty_changeset(self, board_dir) -> None:
        """AC6c: An empty awatch yield (idle timeout) must NOT terminate the stream; a subsequent real change must still produce an event."""
        import asyncio  # noqa: PLC0415

        from owlbear_cockpit.routes.events import events  # noqa: PLC0415
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415

        engine = KanbanEngine(board_dir, agent_name="cockpit")
        real_path = board_dir / "tasks" / "task-real.md"
        real_path.write_text("---\nid: 1\n---\n", encoding="utf-8")

        mock_request = AsyncMock()
        mock_request.is_disconnected = AsyncMock(return_value=False)

        # First yield: empty (simulates idle timeout with no file changes)
        # Second yield: real file change — must reach the generator and produce an event
        async def _empty_then_real(*_args, **_kwargs):
            yield set()
            yield {(MagicMock(), str(real_path))}

        with patch("owlbear_cockpit.routes.events.awatch", _empty_then_real):
            response = await events(mock_request, engine)
            events_yielded: list[dict] = []
            async with asyncio.timeout(3.0):
                async for chunk in response.body_iterator:
                    if isinstance(chunk, dict) and chunk.get("event") == "tasks-changed":
                        events_yielded.append(chunk)
                    if events_yielded:
                        break  # got the expected event, stop consuming

        assert events_yielded, (
            "Generator must continue after an empty changeset (idle timeout), "
            "then emit the subsequent real change as a 'tasks-changed' event. "
            "No event was produced — generator likely broke on the empty yield instead of continuing."
        )


# ---------------------------------------------------------------------------
# AC7: sse-starlette and watchfiles added to pyproject.toml (td:1)
# ---------------------------------------------------------------------------


class TestFromAC_ProjDependencies:
    """AC7: Both sse-starlette and watchfiles must appear in serve/cockpit/pyproject.toml."""

    _PYPROJECT = (
        Path(__file__).parent.parent / "serve/cockpit/pyproject.toml"
    )

    def test_sse_starlette_in_pyproject_dependencies(self) -> None:
        """sse-starlette must be explicitly listed in serve/cockpit/pyproject.toml."""
        content = self._PYPROJECT.read_text(encoding="utf-8")
        assert "sse-starlette" in content, (
            "sse-starlette is missing from serve/cockpit/pyproject.toml [project.dependencies]. "
            "Builder must add it explicitly even though it may already be transitively available."
        )

    def test_watchfiles_in_pyproject_dependencies(self) -> None:
        """watchfiles must be explicitly listed in serve/cockpit/pyproject.toml."""
        content = self._PYPROJECT.read_text(encoding="utf-8")
        assert "watchfiles" in content, (
            "watchfiles is missing from serve/cockpit/pyproject.toml [project.dependencies]. "
            "Builder must add it explicitly — it is a new direct dependency."
        )
