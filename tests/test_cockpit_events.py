from __future__ import annotations

# --- merged from tests/test_cockpit_events_1234.py ---
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


import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

# ---------------------------------------------------------------------------
# Board fixture helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def client(engine):
    """FastAPI TestClient with engine injected via dependency_overrides.

    Patches awatch to return immediately because Starlette's sync TestClient
    cannot signal ASGI disconnect on SSE streams (header-only checks).
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

        assert isinstance(router, APIRouter), (
            "events.router must be a FastAPI APIRouter"
        )

    def test_events_router_registered_in_main(self) -> None:
        """main.py must import and register the events router under /api prefix."""
        main_file = (
            Path(__file__).parent.parent / "serve/cockpit/src/owlbear_cockpit/main.py"
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

    def test_events_router_registered_in_main_exact_pattern(self) -> None:
        """AC1 (tightened): main.py must contain the exact include_router call wiring."""
        main_file = (
            Path(__file__).parent.parent / "serve/cockpit/src/owlbear_cockpit/main.py"
        )
        content = main_file.read_text(encoding="utf-8")
        assert 'include_router(events_router, prefix="/api")' in content, (
            'main.py must contain: include_router(events_router, prefix="/api"). '
            "Substring checks for 'events_router' and 'include_router' in isolation "
            "are insufficient — the exact pattern proves the wiring is correct."
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

        engine_a = KanbanEngine(board_dir)
        engine_b = KanbanEngine(board_dir)

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
    async def test_endpoint_uses_injected_engine_kanban_dir(self, tmp_path) -> None:
        """DI contract: the endpoint must call awatch with the overridden engine's kanban_dir (recursive watch), not tasks_dir."""
        from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415

        board_b = _make_board_1262(tmp_path / "board_b")
        engine_b = KanbanEngine(board_b)
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
                    httpx.AsyncClient(
                        transport=transport, base_url="http://test"
                    ) as ac,
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
        assert Path(awatch_paths[0]) == Path(engine_b.kanban_dir), (
            f"Endpoint must use injected engine_b.kanban_dir ({engine_b.kanban_dir!r}) "
            f"for recursive watching; got {awatch_paths[0]!r}. "
            f"Post-1346: awatch watches kanban_dir recursively, not tasks_dir alone."
        )


# ---------------------------------------------------------------------------
# AC3: Watch filter — board-specific, accepts tasks/.md, rejects .tmp-, non-.md (td:2)
# ---------------------------------------------------------------------------


class TestFromAC_WatchFilter:
    """AC3: Board-specific watch filter built by _build_watch_filter."""

    _TASKS = Path("/fake/kanban/tasks")
    _ARCHIVE = Path("/fake/kanban/archive")
    _DECISIONS_PENDING = Path("/fake/kanban/decisions/pending")
    _ACTIVITY = Path("/fake/kanban/activity.jsonl")

    def _make_filter(self) -> object:
        from owlbear_cockpit.routes.events import _build_watch_filter  # noqa: PLC0415

        return _build_watch_filter(
            self._TASKS, self._ARCHIVE, self._DECISIONS_PENDING, self._ACTIVITY
        )

    def test_filter_accepts_plain_md_file(self) -> None:
        """Board-specific filter must return True for a direct .md child of tasks_dir."""
        assert self._make_filter()(None, "/fake/kanban/tasks/1234-my-task.md") is True

    def test_filter_accepts_md_file_in_tasks_dir(self) -> None:
        """Filter accepts a direct .md child of the configured tasks dir (depth-1 path)."""
        tasks_dir = Path("/home/user/.owlbear/kanban/tasks")
        from owlbear_cockpit.routes.events import _build_watch_filter  # noqa: PLC0415

        watch_filter = _build_watch_filter(
            tasks_dir,
            tasks_dir.parent / "archive",
            tasks_dir.parent / "decisions" / "pending",
            tasks_dir.parent / "activity.jsonl",
        )
        assert watch_filter(None, "/home/user/.owlbear/kanban/tasks/42-title.md") is True

    def test_filter_rejects_tmp_prefix_md_file(self) -> None:
        """Filter must return False for .md files starting with .tmp-."""
        assert (
            self._make_filter()(None, "/fake/kanban/tasks/.tmp-1234-my-task.md") is False
        )

    def test_filter_rejects_non_md_file(self) -> None:
        """Filter must return False for non-.md files (e.g. .json) in tasks_dir."""
        assert self._make_filter()(None, "/fake/kanban/tasks/task-1.json") is False

    def test_filter_rejects_yml_config_file(self) -> None:
        """Filter must return False for .yml files in tasks_dir."""
        assert self._make_filter()(None, "/fake/kanban/tasks/config.yml") is False

    def test_filter_accepts_md_with_tmp_in_middle_of_name(self) -> None:
        """Rejection is prefix-specific: 'task-tmp-123.md' (no leading dot) must pass."""
        # 'tmp' in the middle of the filename is not the .tmp- prefix pattern
        assert (
            self._make_filter()(None, "/fake/kanban/tasks/task-tmp-123.md") is True
        )

    def test_filter_rejects_minimal_tmp_prefix(self) -> None:
        """Boundary: file named exactly '.tmp-.md' must be rejected."""
        assert self._make_filter()(None, "/fake/kanban/tasks/.tmp-.md") is False

    @pytest.mark.asyncio
    async def test_awatch_call_site_receives_correct_arguments(self, board_dir) -> None:
        """Post-1346: awatch() must be called with engine.kanban_dir, a callable watch_filter, recursive=True."""
        from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415

        engine = KanbanEngine(board_dir)
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
                    httpx.AsyncClient(
                        transport=transport, base_url="http://test"
                    ) as ac,
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
        assert Path(args[0]) == Path(engine.kanban_dir), (
            f"awatch first arg must be engine.kanban_dir ({engine.kanban_dir!r}), "
            f"got {args[0]!r}. Post-1346: awatch uses kanban_dir with recursive=True."
        )
        assert callable(kwargs.get("watch_filter")), (
            f"awatch must receive a callable watch_filter; "
            f"got watch_filter={kwargs.get('watch_filter')!r}"
        )
        assert kwargs.get("recursive") is True, (
            f"awatch must receive recursive=True; got recursive={kwargs.get('recursive')!r}"
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

        engine = KanbanEngine(board_dir)
        fake_path = board_dir / "tasks" / "task-99.md"
        fake_path.write_text("---\nid: 99\n---\n", encoding="utf-8")

        async def _one_change(*_args, **_kwargs):
            yield {(MagicMock(), str(fake_path))}

        app.dependency_overrides[get_engine] = lambda: engine
        try:
            with patch("owlbear_cockpit.routes.events.awatch", _one_change):
                transport = httpx.ASGITransport(app=app)
                async with (
                    httpx.AsyncClient(
                        transport=transport, base_url="http://test"
                    ) as ac,
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

        engine = KanbanEngine(board_dir)
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
                    httpx.AsyncClient(
                        transport=transport, base_url="http://test"
                    ) as ac,
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
    async def test_event_emitted_when_changed_file_deleted_before_stat(
        self, board_dir
    ) -> None:
        """Post-1346 AC4: When a tasks file is deleted before stat(), a tasks-changed
        event MUST still be emitted using a synthetic time.time_ns() mtime.

        Old contract said 'skip deleted paths — no event'. New contract says emit
        a numeric mtime payload so the frontend detects the deletion and refetches.
        """
        from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415

        engine = KanbanEngine(board_dir)
        # Path that does NOT exist — simulates file deleted after awatch yield
        deleted_path = board_dir / "tasks" / "gone.md"
        assert not deleted_path.exists(), "Test setup: file must not exist"

        async def _one_change_then_stop(*_args, **_kwargs):
            yield {(MagicMock(), str(deleted_path))}
            # generator exhausts after one yield; no more changes

        events_received: list[str] = []
        app.dependency_overrides[get_engine] = lambda: engine
        try:
            with patch("owlbear_cockpit.routes.events.awatch", _one_change_then_stop):
                transport = httpx.ASGITransport(app=app)
                async with (
                    httpx.AsyncClient(
                        transport=transport, base_url="http://test"
                    ) as ac,
                    ac.stream("GET", "/api/events") as response,
                ):
                    assert response.status_code == 200
                    async for line in response.aiter_lines():
                        if line.startswith(("event:", "data:")):
                            events_received.append(line)
        finally:
            app.dependency_overrides.clear()

        event_names = [
            ln.split(":", 1)[1].strip()
            for ln in events_received
            if ln.startswith("event:")
        ]
        data_payloads = [
            ln.split(":", 1)[1].strip()
            for ln in events_received
            if ln.startswith("data:")
        ]
        assert "tasks-changed" in event_names, (
            f"tasks-changed MUST be emitted for a deleted task file (AC4: synthetic mtime). "
            f"Got events: {event_names!r}. "
            f"Old contract said 'skip deleted paths' — new contract requires emission."
        )
        assert data_payloads, "No data payload received for deleted-file tasks-changed event"
        payload = json.loads(data_payloads[0])
        assert isinstance(payload.get("mtime"), int), (
            f"mtime must be an integer (synthetic time.time_ns()); got {payload!r}"
        )
        assert payload["mtime"] > 0, (
            f"Synthetic mtime must be positive; got {payload['mtime']}"
        )

    @pytest.mark.asyncio
    async def test_mixed_batch_surviving_file_still_emits_event(
        self, board_dir
    ) -> None:
        """AC4b: When a batch contains both a deleted and a surviving .md file, the surviving file still produces a tasks-changed event."""
        from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415

        engine = KanbanEngine(board_dir)
        surviving_path = board_dir / "tasks" / "task-surviving.md"
        surviving_path.write_text("---\nid: 10\n---\n", encoding="utf-8")
        deleted_path = board_dir / "tasks" / "task-deleted.md"
        # deleted_path intentionally does NOT exist
        assert not deleted_path.exists(), "Test setup: deleted_path must not exist"

        async def _mixed_batch_then_stop(*_args, **_kwargs):
            # One batch with both a deleted path and a surviving path
            yield {(MagicMock(), str(deleted_path)), (MagicMock(), str(surviving_path))}

        app.dependency_overrides[get_engine] = lambda: engine
        try:
            with patch("owlbear_cockpit.routes.events.awatch", _mixed_batch_then_stop):
                transport = httpx.ASGITransport(app=app)
                async with (
                    httpx.AsyncClient(
                        transport=transport, base_url="http://test"
                    ) as ac,
                    ac.stream("GET", "/api/events") as response,
                ):
                    assert response.status_code == 200
                    event_lines: list[str] = []
                    data_lines: list[str] = []
                    async for line in response.aiter_lines():
                        if line.startswith("event:"):
                            event_lines.append(line[len("event:") :].strip())
                        elif line.startswith("data:"):
                            data_lines.append(line[len("data:") :].strip())
                        if event_lines and data_lines:
                            break
        finally:
            app.dependency_overrides.clear()

        assert event_lines == ["tasks-changed"], (
            f"Expected one 'tasks-changed' event from the mixed batch (deleted file "
            f"must NOT suppress the event). Got events: {event_lines!r}"
        )
        assert data_lines, "No data line received for the mixed-batch event"
        payload = json.loads(data_lines[0])
        assert isinstance(payload.get("mtime"), int), (
            f"mtime must be an integer. Got: {payload!r}"
        )
        assert payload.get("mtime") > 0, (  # type: ignore[operator]
            f"mtime must be positive. Post-1346: the batch mtime is the "
            f"max of all paths' mtimes, including synthetic time.time_ns() for deleted "
            f"files (which is >= the surviving file's st_mtime_ns). Got: {payload!r}"
        )

    @pytest.mark.asyncio
    async def test_mtime_uses_st_mtime_ns(self, board_dir) -> None:
        """mtime payload must use st_mtime_ns (nanoseconds), not st_mtime (seconds)."""
        from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415

        engine = KanbanEngine(board_dir)
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
                    httpx.AsyncClient(
                        transport=transport, base_url="http://test"
                    ) as ac,
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

    @pytest.mark.asyncio
    async def test_missing_tasks_dir_returns_200(self, tmp_path) -> None:
        """GET /api/events must return HTTP 200 even when tasks_dir does not exist."""
        import shutil  # noqa: PLC0415

        from owlbear_cockpit.routes.events import events  # noqa: PLC0415
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415

        kanban_dir = _make_board_1262(tmp_path)
        engine = KanbanEngine(kanban_dir)
        shutil.rmtree(engine.tasks_dir)
        assert not engine.tasks_dir.exists(), "Test setup: tasks_dir must not exist"

        mock_request = AsyncMock()
        response = await events(mock_request, engine)
        assert response.status_code == 200, (
            f"Expected 200 for missing tasks_dir guard, got {response.status_code}"
        )

    @pytest.mark.asyncio
    async def test_missing_tasks_dir_awatch_not_called(self, tmp_path) -> None:
        """Generator must NOT call awatch when tasks_dir does not exist."""
        import shutil  # noqa: PLC0415

        from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415
        from owlbear_cockpit.routes.events import events  # noqa: PLC0415
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415

        kanban_dir = _make_board_1262(tmp_path)
        engine = KanbanEngine(kanban_dir)
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
        """AC5 (revised): Missing tasks_dir must produce zero SSE event/data lines within a sampling window."""
        import asyncio  # noqa: PLC0415
        import shutil  # noqa: PLC0415

        from owlbear_cockpit.routes.events import events  # noqa: PLC0415
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415

        kanban_dir = _make_board_1262(tmp_path)
        engine = KanbanEngine(kanban_dir)
        shutil.rmtree(engine.tasks_dir)
        assert not engine.tasks_dir.exists(), "Test setup: tasks_dir must not exist"

        mock_request = AsyncMock()
        mock_request.is_disconnected = AsyncMock(return_value=False)
        response = await events(mock_request, engine)

        event_lines: list[str] = []
        try:
            async with asyncio.timeout(2):
                async for chunk in response.body_iterator:
                    text = chunk.decode() if isinstance(chunk, bytes) else str(chunk)
                    for line in text.splitlines():
                        if line.startswith(("event:", "data:")):
                            event_lines.append(line)
        except (TimeoutError, asyncio.CancelledError):
            pass  # Expected: SSE stream is infinite, timeout is the exit path

        assert not event_lines, (
            f"Missing-dir path must produce a truly empty SSE stream (zero event:/data: lines). "
            f"Got: {event_lines}"
        )

    @pytest.mark.asyncio
    async def test_missing_kanban_dir_awatch_unreachable_on_consumed_path(
        self, tmp_path
    ) -> None:
        """AC5 (combined proof): consuming a missing-dir stream produces zero events AND never calls awatch.

        Patches awatch to raise immediately if invoked, proving the missing-dir guard
        (checks kanban_dir.exists()) short-circuits before awatch is reached.
        Post-1346: guard checks kanban_dir (not tasks_dir) since awatch now watches
        kanban_dir recursively.
        """
        import shutil  # noqa: PLC0415

        from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415

        kanban_dir = _make_board_1262(tmp_path)
        engine = KanbanEngine(kanban_dir)
        shutil.rmtree(engine.kanban_dir)
        assert not engine.kanban_dir.exists(), "Test setup: kanban_dir must not exist"

        async def _raise_if_called(*_args, **_kwargs):
            msg = (
                "awatch must not be called when kanban_dir does not exist "
                "\u2014 missing-dir guard is absent or placed after the awatch call."
            )
            raise AssertionError(msg)
            yield  # pragma: no cover — makes this a valid async generator

        app.dependency_overrides[get_engine] = lambda: engine
        try:
            with patch("owlbear_cockpit.routes.events.awatch", _raise_if_called):
                transport = httpx.ASGITransport(app=app)
                async with (
                    httpx.AsyncClient(
                        transport=transport, base_url="http://test"
                    ) as ac,
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
            f"Missing-dir path must produce zero SSE event:/data: lines. Got: {event_lines}"
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

        engine = KanbanEngine(board_dir)
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

        engine = KanbanEngine(board_dir)
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
    async def test_generator_terminates_on_disconnect_executable(
        self, board_dir
    ) -> None:
        """AC6b: When is_disconnected() returns True, generator exits the watch loop — proven by consuming body_iterator."""
        import asyncio  # noqa: PLC0415

        from owlbear_cockpit.routes.events import events  # noqa: PLC0415
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415

        engine = KanbanEngine(board_dir)
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
    async def test_generator_emits_zero_chunks_when_disconnected_before_first_yield(
        self, board_dir
    ) -> None:
        """AC6b (revised): When is_disconnected() is True at the first disconnect check, zero event/data chunks must be emitted — disconnect fires before payload processing."""
        import asyncio  # noqa: PLC0415

        from owlbear_cockpit.routes.events import events  # noqa: PLC0415
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415

        engine = KanbanEngine(board_dir)
        real_path = board_dir / "tasks" / "task-dc.md"
        real_path.write_text("---\nid: 1\n---\n", encoding="utf-8")

        mock_request = AsyncMock()
        # Disconnected from the very first check — before any payload processing
        mock_request.is_disconnected = AsyncMock(return_value=True)

        async def _one_real_change(*_args, **_kwargs):
            # Yields a real change set — would produce an event if disconnect check is late
            yield {(MagicMock(), str(real_path))}

        with patch("owlbear_cockpit.routes.events.awatch", _one_real_change):
            response = await events(mock_request, engine)
            emitted_chunks: list = []
            async with asyncio.timeout(3.0):
                async for chunk in response.body_iterator:
                    if (
                        isinstance(chunk, dict)
                        and chunk.get("event") == "tasks-changed"
                    ):
                        emitted_chunks.append(chunk)

        assert not emitted_chunks, (
            f"AC6b: when is_disconnected() returns True before payload processing, "
            f"zero 'tasks-changed' chunks must be emitted. "
            f"Got: {emitted_chunks!r} — disconnect check may fire AFTER the yield."
        )

    @pytest.mark.asyncio
    async def test_generator_continues_on_empty_changeset(self, board_dir) -> None:
        """AC6c: An empty awatch yield (idle timeout) must NOT terminate the stream; a subsequent real change must still produce an event."""
        import asyncio  # noqa: PLC0415

        from owlbear_cockpit.routes.events import events  # noqa: PLC0415
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415

        engine = KanbanEngine(board_dir)
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
                    if (
                        isinstance(chunk, dict)
                        and chunk.get("event") == "tasks-changed"
                    ):
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

    _PYPROJECT = Path(__file__).parent.parent / "serve/cockpit/pyproject.toml"

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

    def test_sse_starlette_in_project_dependencies_section(self) -> None:
        """AC7 (tightened): sse-starlette must be in [project.dependencies], not merely elsewhere in the file."""
        import tomllib  # noqa: PLC0415

        with self._PYPROJECT.open("rb") as f:
            data = tomllib.load(f)
        deps: list[str] = data.get("project", {}).get("dependencies", [])
        assert any("sse-starlette" in dep for dep in deps), (
            f"sse-starlette not found in [project.dependencies] section. "
            f"Raw substring search is insufficient — name must appear in the structured "
            f"[project.dependencies] list. Got dependencies: {deps}"
        )

    def test_watchfiles_in_project_dependencies_section(self) -> None:
        """AC7 (tightened): watchfiles must be in [project.dependencies], not merely elsewhere in the file."""
        import tomllib  # noqa: PLC0415

        with self._PYPROJECT.open("rb") as f:
            data = tomllib.load(f)
        deps: list[str] = data.get("project", {}).get("dependencies", [])
        assert any("watchfiles" in dep for dep in deps), (
            f"watchfiles not found in [project.dependencies] section. "
            f"Raw substring search is insufficient — name must appear in the structured "
            f"[project.dependencies] list. Got dependencies: {deps}"
        )


# --- merged from tests/test_cockpit_events_1262.py ---
"""RED-phase tests for #1262: Extend SSE watcher to recursive kanban_dir with typed
multi-surface events.

AC coverage:
  AC1 (td:2): Watch filter accepts tasks/*.md (not .tmp-), decisions/pending/*.md,
              activity.jsonl; rejects all other paths under kanban_dir; filter
              requires board-specific paths (engine.tasks_dir, decisions/pending
              dir, activity.jsonl path)
  AC2 (td:2): Path classifier returns "tasks-changed" | "decisions-changed" |
              "activity-changed" | None; uses engine board-specific paths
  AC3 (td:1): awatch uses engine.kanban_dir with recursive=True (replaces
              engine.tasks_dir with recursive=False)
  AC4 (td:2): Each distinct event type in a change batch → separate SSE event with
              event={type} and data={"mtime": max_st_mtime_ns}; deletion-only paths
              for a type → no event emitted for that type
  AC5 (td:1): Missing kanban_dir → stream returns immediately, no events, no crash

All tests FAIL until builder refactors:
  serve/cockpit/src/owlbear_cockpit/routes/events.py
"""


import asyncio
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

# ---------------------------------------------------------------------------
# Board fixture helpers
# ---------------------------------------------------------------------------

_CONFIG_YAML_1262 = """\
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


def _make_board_1262(base_dir: Path) -> Path:
    """Create a minimal kanban board directory. Returns kanban_dir."""
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_CONFIG_YAML_1262, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


@pytest.fixture
def board_dir(tmp_path: Path) -> Path:
    """Minimal kanban board with no tasks."""
    return _make_board_1262(tmp_path)


@pytest.fixture
def engine(board_dir: Path):
    """KanbanEngine bound to the test board."""
    from owlbear_kanban import KanbanEngine  # noqa: PLC0415

    return KanbanEngine(board_dir)

# ---------------------------------------------------------------------------
# Async helper: run endpoint and capture awatch call kwargs
# ---------------------------------------------------------------------------


async def _run_and_capture(board_dir: Path) -> tuple[dict, object]:
    """Run /api/events with a noop awatch mock, capture the call kwargs.

    Returns (captured, engine) where captured has keys:
      "filter"  — the watch_filter callable passed to awatch (or None)
      "args"    — positional args passed to awatch
      "kwargs"  — keyword args passed to awatch
    """
    from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415
    from owlbear_kanban import KanbanEngine  # noqa: PLC0415

    engine = KanbanEngine(board_dir)
    captured: dict = {"filter": None, "args": (), "kwargs": {}}

    async def _grab(*args, **kwargs):
        captured.update(filter=kwargs.get("watch_filter"), args=args, kwargs=kwargs)
        return
        yield  # pragma: no cover — makes this a valid async generator

    app.dependency_overrides[get_engine] = lambda: engine
    try:
        with patch("owlbear_cockpit.routes.events.awatch", _grab):
            transport = httpx.ASGITransport(app=app)
            async with (
                httpx.AsyncClient(transport=transport, base_url="http://test") as ac,
                ac.stream("GET", "/api/events") as response,
            ):
                assert response.status_code == 200
                async for _ in response.aiter_lines():
                    pass
    finally:
        app.dependency_overrides.clear()

    return captured, engine


# ---------------------------------------------------------------------------
# AC1: Watch filter — board-specific path acceptance/rejection (td:2)
# ---------------------------------------------------------------------------


class TestFromAC_WatchFilter_1262:
    """AC1: Filter is board-specific; accepts tasks/*.md (not .tmp-),
    decisions/pending/*.md, and exact activity.jsonl; rejects all other paths."""

    @pytest.mark.asyncio
    async def test_filter_accepts_activity_jsonl(self, board_dir: Path) -> None:
        """Filter must return True for the board's exact activity.jsonl path.

        Current _watch_filter checks name.endswith('.md') — activity.jsonl fails
        that check → returns False → this test FAILS against current code.
        """
        captured, engine = await _run_and_capture(board_dir)
        assert captured["filter"] is not None, "awatch must receive a watch_filter"

        activity_path = str(engine.kanban_dir / "activity.jsonl")
        result = captured["filter"](None, activity_path)
        assert result is True, (
            f"Filter must accept the board's activity.jsonl path: {activity_path!r}. "
            f"Got False — current generic filter only accepts .md files."
        )

    @pytest.mark.asyncio
    async def test_filter_accepts_archive_md(self, board_dir: Path) -> None:
        """Post-1346 AC5: Filter must return True for .md files in archive/.

        archive/*.md is now a watched surface: archive moves affect active-board
        membership and must trigger a tasks-changed SSE event. The old contract
        said archive/*.md is rejected (classifier returns None). New contract:
        archive/*.md is accepted by the watch filter and classified as tasks-changed.
        """
        captured, engine = await _run_and_capture(board_dir)
        archive_md = str(engine.kanban_dir / "archive" / "100-done-task.md")
        assert captured["filter"](None, archive_md) is True, (
            f"Filter must accept archive/*.md (AC5: archive moves are task-list "
            f"invalidation signals); got False for {archive_md!r}. "
            f"Post-1346: archive_dir is an accepted watch surface."
        )

    @pytest.mark.asyncio
    async def test_filter_rejects_decisions_non_pending_md(
        self, board_dir: Path
    ) -> None:
        """Filter must return False for decisions that are not in pending/.

        Only decisions/pending/*.md is watched. decisions/resolved/*.md and
        top-level decisions/*.md must be rejected.
        Current generic filter returns True for any .md → FAILS.
        """
        captured, engine = await _run_and_capture(board_dir)
        resolved_md = str(engine.kanban_dir / "decisions" / "resolved" / "dr-42.md")
        assert captured["filter"](None, resolved_md) is False, (
            f"Filter must reject decisions/resolved/*.md; got True for {resolved_md!r}"
        )
        top_level_md = str(engine.kanban_dir / "decisions" / "dr-99.md")
        assert captured["filter"](None, top_level_md) is False, (
            f"Filter must reject decisions/*.md (not in pending/); "
            f"got True for {top_level_md!r}"
        )

    @pytest.mark.asyncio
    async def test_filter_rejects_kanban_root_md(self, board_dir: Path) -> None:
        """Filter must return False for .md files directly at the kanban_dir root.

        Current generic filter returns True for any .md → FAILS.
        """
        captured, engine = await _run_and_capture(board_dir)
        root_md = str(engine.kanban_dir / "notes.md")
        assert captured["filter"](None, root_md) is False, (
            f"Filter must reject {root_md!r}; only tasks/, decisions/pending/, "
            f"and activity.jsonl are watched surfaces."
        )

    @pytest.mark.asyncio
    async def test_filter_accepts_own_tasks_md_but_rejects_other_board(
        self, board_dir: Path, tmp_path: Path
    ) -> None:
        """Filter must be board-specific: accepts own board's tasks/*.md and rejects
        the same relative path under a different board directory.

        Current generic filter returns True for any .md regardless of board
        → second assertion (rejects other board) FAILS against current code.
        """
        captured, engine = await _run_and_capture(board_dir)
        own_task = str(engine.tasks_dir / "task-1.md")
        other_task = str(tmp_path / "other_board" / "tasks" / "task-1.md")

        assert captured["filter"](None, own_task) is True, (
            f"Filter must accept own board tasks path: {own_task!r}"
        )
        assert captured["filter"](None, other_task) is False, (
            f"Filter must reject tasks path from a different board: {other_task!r}. "
            f"Current filter accepts any .md — new filter must use board-specific paths."
        )

    @pytest.mark.asyncio
    async def test_filter_accepts_decisions_pending_but_rejects_different_board_pending(
        self, board_dir: Path, tmp_path: Path
    ) -> None:
        """Filter is board-specific for decisions/pending too: accepts own board's
        decisions/pending/*.md and rejects the same relative path from another board.

        Current generic filter accepts both → second assertion FAILS.
        """
        captured, engine = await _run_and_capture(board_dir)
        own_pending = str(engine.kanban_dir / "decisions" / "pending" / "dr.md")
        other_pending = str(
            tmp_path / "other_board" / "decisions" / "pending" / "dr.md"
        )

        assert captured["filter"](None, own_pending) is True, (
            f"Filter must accept own board's decisions/pending/*.md: {own_pending!r}"
        )
        assert captured["filter"](None, other_pending) is False, (
            f"Filter must reject decisions/pending/*.md from a different board: "
            f"{other_pending!r}"
        )

    @pytest.mark.asyncio
    async def test_filter_rejects_tmp_prefixed_task_md(self, board_dir: Path) -> None:
        """Filter must return False for .tmp- prefixed files inside tasks/, even though
        they reside in the watched tasks directory.

        This covers the explicit .tmp- guard branch at events.py:48 which is otherwise
        untested: the filter returns False before the is_direct_md check runs.
        """
        captured, engine = await _run_and_capture(board_dir)
        assert captured["filter"] is not None, "awatch must receive a watch_filter"

        tmp_path_str = str(engine.tasks_dir / ".tmp-task-42.md")
        result = captured["filter"](None, tmp_path_str)
        assert result is False, (
            f"Filter must reject .tmp- prefixed files in tasks/; got True for "
            f"{tmp_path_str!r}. The .tmp- guard branch in events.py must be hit."
        )

    @pytest.mark.asyncio
    async def test_filter_rejects_nested_tasks_subdir_md(self, board_dir: Path) -> None:
        """Filter must return False for paths nested below tasks/ (depth > 1).

        tasks/subdir/x.md has len(relative.parts) == 2 relative to tasks_dir, so
        _is_direct_md returns False. Proves the depth=1 guard in the filter
        (AC1: 'direct children only; nested paths like tasks/sub/x.md must be rejected').
        """
        captured, engine = await _run_and_capture(board_dir)
        nested = str(engine.tasks_dir / "subdir" / "task-x.md")
        assert captured["filter"](None, nested) is False, (
            f"Filter must reject nested tasks path {nested!r}; "
            f"only direct children of tasks/ qualify (depth=1)."
        )

    @pytest.mark.asyncio
    async def test_filter_rejects_nested_decisions_pending_subdir_md(
        self, board_dir: Path
    ) -> None:
        """Filter must return False for paths nested below decisions/pending/ (depth > 1).

        decisions/pending/subdir/dr.md has len(relative.parts) == 2 relative to
        decisions_pending_dir, so _is_direct_md returns False. Proves the depth=1
        guard in the filter (AC1: 'direct children only').
        """
        captured, engine = await _run_and_capture(board_dir)
        nested = str(engine.kanban_dir / "decisions" / "pending" / "subdir" / "dr.md")
        assert captured["filter"](None, nested) is False, (
            f"Filter must reject nested decisions/pending path {nested!r}; "
            f"only direct children of decisions/pending/ qualify (depth=1)."
        )


# ---------------------------------------------------------------------------
# AC2: Path classifier — typed event names from board-specific paths (td:2)
# ---------------------------------------------------------------------------


class TestFromAC_Classify:
    """AC2: Classifier returns "tasks-changed" | "decisions-changed" |
    "activity-changed" | None based on board-specific path matching."""

    @pytest.mark.asyncio
    async def test_decisions_pending_path_emits_decisions_changed(
        self, board_dir: Path
    ) -> None:
        """A path in decisions/pending/ must produce a 'decisions-changed' event.

        Current code emits 'tasks-changed' for any path → this test FAILS.
        """
        from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415

        engine = KanbanEngine(board_dir)
        pending_dir = engine.kanban_dir / "decisions" / "pending"
        pending_dir.mkdir(parents=True, exist_ok=True)
        dr_path = pending_dir / "dr-10.md"
        dr_path.write_text("# DR-10\n", encoding="utf-8")

        async def _one_change(*_args, **_kwargs):
            yield {(MagicMock(), str(dr_path))}

        app.dependency_overrides[get_engine] = lambda: engine
        try:
            with patch("owlbear_cockpit.routes.events.awatch", _one_change):
                transport = httpx.ASGITransport(app=app)
                async with (
                    httpx.AsyncClient(
                        transport=transport, base_url="http://test"
                    ) as ac,
                    ac.stream("GET", "/api/events") as response,
                ):
                    assert response.status_code == 200
                    event_names: list[str] = []
                    async for line in response.aiter_lines():
                        if line.startswith("event:"):
                            event_names.append(line[len("event:") :].strip())
                        if event_names:
                            break
        finally:
            app.dependency_overrides.clear()

        assert "decisions-changed" in event_names, (
            f"decisions/pending/*.md must produce 'decisions-changed' event. "
            f"Got events: {event_names!r}. "
            f"Current code always emits 'tasks-changed'."
        )
        assert "tasks-changed" not in event_names, (
            f"decisions/pending/*.md must NOT produce 'tasks-changed'. "
            f"Got: {event_names!r}"
        )

    @pytest.mark.asyncio
    async def test_activity_path_emits_activity_changed(self, board_dir: Path) -> None:
        """The activity.jsonl path must produce an 'activity-changed' event.

        Current code emits 'tasks-changed' for any surviving path → FAILS.
        """
        from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415

        engine = KanbanEngine(board_dir)
        activity_path = engine.kanban_dir / "activity.jsonl"
        activity_path.write_text("{}\n", encoding="utf-8")

        async def _one_change(*_args, **_kwargs):
            yield {(MagicMock(), str(activity_path))}

        app.dependency_overrides[get_engine] = lambda: engine
        try:
            with patch("owlbear_cockpit.routes.events.awatch", _one_change):
                transport = httpx.ASGITransport(app=app)
                async with (
                    httpx.AsyncClient(
                        transport=transport, base_url="http://test"
                    ) as ac,
                    ac.stream("GET", "/api/events") as response,
                ):
                    event_names: list[str] = []
                    async for line in response.aiter_lines():
                        if line.startswith("event:"):
                            event_names.append(line[len("event:") :].strip())
                        if event_names:
                            break
        finally:
            app.dependency_overrides.clear()

        assert "activity-changed" in event_names, (
            f"activity.jsonl must produce 'activity-changed' event. "
            f"Got: {event_names!r}"
        )
        assert "tasks-changed" not in event_names, (
            f"activity.jsonl must NOT produce 'tasks-changed'. Got: {event_names!r}"
        )

    @pytest.mark.asyncio
    async def test_archive_md_classified_as_tasks_changed(
        self, board_dir: Path
    ) -> None:
        """Post-1346 AC5: A path in archive/ must be classified as 'tasks-changed'
        (archive moves affect active-board membership).

        Old contract said classifier returns None for archive paths (no event).
        New contract: archive/*.md maps to tasks-changed so the frontend refetches
        when a task is archived out of the active list.
        """
        from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415

        engine = KanbanEngine(board_dir)
        archive_md = engine.kanban_dir / "archive" / "old-task.md"
        archive_md.write_text("# done\n", encoding="utf-8")  # exists on disk

        async def _one_change(*_args, **_kwargs):
            yield {(MagicMock(), str(archive_md))}

        app.dependency_overrides[get_engine] = lambda: engine
        events_received: list[str] = []
        try:
            with patch("owlbear_cockpit.routes.events.awatch", _one_change):
                transport = httpx.ASGITransport(app=app)
                async with (
                    httpx.AsyncClient(
                        transport=transport, base_url="http://test"
                    ) as ac,
                    ac.stream("GET", "/api/events") as response,
                ):
                    async for line in response.aiter_lines():
                        if line.startswith(("event:", "data:")):
                            events_received.append(line)
                        if len(events_received) >= 2:
                            break
        finally:
            app.dependency_overrides.clear()

        event_names = [
            ln.split(":", 1)[1].strip()
            for ln in events_received
            if ln.startswith("event:")
        ]
        assert "tasks-changed" in event_names, (
            f"archive/*.md must produce 'tasks-changed' (AC5: archive moves are "
            f"task-list invalidation signals). Got: {event_names!r}. "
            f"Old contract said 'no event for archive paths' — new contract requires emission."
        )

    @pytest.mark.asyncio
    async def test_different_board_path_classified_as_none_no_event(
        self, board_dir: Path, tmp_path: Path
    ) -> None:
        """A tasks/*.md path from a different board must be classified as None (no event).

        Current code emits 'tasks-changed' for any surviving .md → FAILS.
        """
        from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415

        engine = KanbanEngine(board_dir)
        # Create a real .md file in a different board's tasks directory
        other_task = tmp_path / "other_board" / "tasks" / "task-42.md"
        other_task.parent.mkdir(parents=True)
        other_task.write_text("# task 42\n", encoding="utf-8")

        async def _one_change(*_args, **_kwargs):
            yield {(MagicMock(), str(other_task))}

        app.dependency_overrides[get_engine] = lambda: engine
        events_received: list[str] = []
        try:
            with patch("owlbear_cockpit.routes.events.awatch", _one_change):
                transport = httpx.ASGITransport(app=app)
                async with (
                    httpx.AsyncClient(
                        transport=transport, base_url="http://test"
                    ) as ac,
                    ac.stream("GET", "/api/events") as response,
                ):
                    async for line in response.aiter_lines():
                        if line.startswith(("event:", "data:")):
                            events_received.append(line)
        finally:
            app.dependency_overrides.clear()

        assert not events_received, (
            f"Path from a different board must produce no events. "
            f"Got: {events_received!r}. "
            f"Current code emits 'tasks-changed' for any surviving .md path."
        )

    @pytest.mark.asyncio
    async def test_other_board_activity_jsonl_classified_as_none_no_event(
        self, board_dir: Path, tmp_path: Path
    ) -> None:
        """activity.jsonl from a DIFFERENT board must produce no event.

        A name-only check (`path.name == 'activity.jsonl'`) would incorrectly
        classify any file named activity.jsonl as 'activity-changed', regardless
        of board. The classifier must use the board-specific exact path.
        """
        from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415

        engine = KanbanEngine(board_dir)
        other_activity = tmp_path / "other_board" / "activity.jsonl"
        other_activity.parent.mkdir(parents=True, exist_ok=True)
        other_activity.write_text("{}\n", encoding="utf-8")

        async def _one_change(*_a, **_k):
            yield {(MagicMock(), str(other_activity))}

        app.dependency_overrides[get_engine] = lambda: engine
        events_received: list[str] = []
        try:
            with patch("owlbear_cockpit.routes.events.awatch", _one_change):
                transport = httpx.ASGITransport(app=app)
                async with (
                    httpx.AsyncClient(
                        transport=transport, base_url="http://test"
                    ) as ac,
                    ac.stream("GET", "/api/events") as response,
                ):
                    async for line in response.aiter_lines():
                        if line.startswith(("event:", "data:")):
                            events_received.append(line)
        finally:
            app.dependency_overrides.clear()

        assert not events_received, (
            f"activity.jsonl from a different board must produce no events. "
            f"Got: {events_received!r}. "
            f"A name-only check (`path.name == 'activity.jsonl'`) would misclassify it."
        )

    @pytest.mark.asyncio
    async def test_other_board_decisions_pending_md_classified_as_none_no_event(
        self, board_dir: Path, tmp_path: Path
    ) -> None:
        """decisions/pending/*.md from a DIFFERENT board must produce no event.

        A path-suffix or directory-name check could incorrectly classify any file
        whose parent chain contains 'decisions/pending' as 'decisions-changed',
        regardless of board. The classifier must use the board-specific
        decisions_pending_dir path.
        """
        from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415

        engine = KanbanEngine(board_dir)
        other_pending = tmp_path / "other_board" / "decisions" / "pending" / "dr-99.md"
        other_pending.parent.mkdir(parents=True, exist_ok=True)
        other_pending.write_text("# DR-99\n", encoding="utf-8")

        async def _one_change(*_a, **_k):
            yield {(MagicMock(), str(other_pending))}

        app.dependency_overrides[get_engine] = lambda: engine
        events_received: list[str] = []
        try:
            with patch("owlbear_cockpit.routes.events.awatch", _one_change):
                transport = httpx.ASGITransport(app=app)
                async with (
                    httpx.AsyncClient(
                        transport=transport, base_url="http://test"
                    ) as ac,
                    ac.stream("GET", "/api/events") as response,
                ):
                    async for line in response.aiter_lines():
                        if line.startswith(("event:", "data:")):
                            events_received.append(line)
        finally:
            app.dependency_overrides.clear()

        assert not events_received, (
            f"decisions/pending/*.md from a different board must produce no events. "
            f"Got: {events_received!r}. "
            f"A directory-name check would misclassify this path."
        )

    @pytest.mark.asyncio
    async def test_nested_tasks_subdir_classified_as_none_no_event(
        self, board_dir: Path
    ) -> None:
        """A path at tasks/subdir/x.md must be classified as None → no SSE event.

        The endpoint receives the nested path via the mocked awatch (bypassing the
        filter) and _classify_path must return None because _is_direct_md rejects
        depth>1 paths (AC2: 'only direct children qualify — nested descendants return None').
        """
        from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415

        engine = KanbanEngine(board_dir)
        nested_task = engine.tasks_dir / "subdir" / "task-deep.md"
        nested_task.parent.mkdir(parents=True, exist_ok=True)
        nested_task.write_text("# deep\n", encoding="utf-8")

        async def _one_change(*_a, **_k):
            yield {(MagicMock(), str(nested_task))}

        app.dependency_overrides[get_engine] = lambda: engine
        events_received: list[str] = []
        try:
            with patch("owlbear_cockpit.routes.events.awatch", _one_change):
                transport = httpx.ASGITransport(app=app)
                async with (
                    httpx.AsyncClient(
                        transport=transport, base_url="http://test"
                    ) as ac,
                    ac.stream("GET", "/api/events") as response,
                ):
                    async for line in response.aiter_lines():
                        if line.startswith(("event:", "data:")):
                            events_received.append(line)
        finally:
            app.dependency_overrides.clear()

        assert not events_received, (
            f"tasks/subdir/x.md (nested, depth>1) must produce no events; "
            f"classifier must return None. Got: {events_received!r}"
        )


# ---------------------------------------------------------------------------
# AC3: awatch uses engine.kanban_dir with recursive=True (td:1)
# ---------------------------------------------------------------------------


class TestFromAC_AWatchTarget:
    """AC3: awatch must be called with engine.kanban_dir and recursive=True."""

    @pytest.mark.asyncio
    async def test_awatch_called_with_kanban_dir_not_tasks_dir(
        self, board_dir: Path
    ) -> None:
        """awatch's first positional arg must be engine.kanban_dir, not engine.tasks_dir.

        Current code passes engine.tasks_dir → this test FAILS.
        """
        captured, engine = await _run_and_capture(board_dir)
        assert len(captured["args"]) >= 1, (
            "awatch must be called with at least one positional arg"
        )
        called_with = Path(captured["args"][0])
        assert called_with == engine.kanban_dir, (
            f"awatch must be called with engine.kanban_dir ({engine.kanban_dir!r}), "
            f"got {captured['args'][0]!r}. "
            f"Current code uses engine.tasks_dir ({engine.tasks_dir!r})."
        )

    @pytest.mark.asyncio
    async def test_awatch_called_with_recursive_true(self, board_dir: Path) -> None:
        """awatch must receive recursive=True to catch newly created subdirs.

        Current code passes recursive=False → this test FAILS.
        """
        captured, _ = await _run_and_capture(board_dir)
        recursive = captured["kwargs"].get("recursive")
        assert recursive is True, (
            f"awatch must be called with recursive=True; "
            f"got recursive={recursive!r}. "
            f"Current code uses recursive=False."
        )


# ---------------------------------------------------------------------------
# AC4: Typed events per surface, mtime semantics, deletion handling (td:2)
# ---------------------------------------------------------------------------


class TestFromAC_TypedEvents:
    """AC4: Each surface type in a batch emits a separate SSE event; max mtime per
    surface; deletion-only for a type suppresses that type's event."""

    @pytest.mark.asyncio
    async def test_decisions_change_emits_decisions_changed_event(
        self, board_dir: Path
    ) -> None:
        """decisions/pending/*.md change must yield event='decisions-changed' with mtime.

        Current code only emits 'tasks-changed' → FAILS.
        """
        from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415

        engine = KanbanEngine(board_dir)
        pending_dir = engine.kanban_dir / "decisions" / "pending"
        pending_dir.mkdir(parents=True, exist_ok=True)
        dr = pending_dir / "dr-1.md"
        dr.write_text("# DR\n", encoding="utf-8")
        expected_mtime = dr.stat().st_mtime_ns

        async def _one_change(*_a, **_k):
            yield {(MagicMock(), str(dr))}

        app.dependency_overrides[get_engine] = lambda: engine
        try:
            with patch("owlbear_cockpit.routes.events.awatch", _one_change):
                transport = httpx.ASGITransport(app=app)
                async with (
                    httpx.AsyncClient(
                        transport=transport, base_url="http://test"
                    ) as ac,
                    ac.stream("GET", "/api/events") as response,
                ):
                    lines: list[str] = []
                    async for line in response.aiter_lines():
                        if line.startswith(("event:", "data:")):
                            lines.append(line)
                        if len(lines) >= 2:
                            break
        finally:
            app.dependency_overrides.clear()

        event_line = next((ln for ln in lines if ln.startswith("event:")), None)
        data_line = next((ln for ln in lines if ln.startswith("data:")), None)
        assert event_line is not None, "No event line received"
        assert event_line.split(":", 1)[1].strip() == "decisions-changed", (
            f"Expected 'decisions-changed', got: {event_line!r}"
        )
        assert data_line is not None, "No data line received"
        payload = json.loads(data_line.split(":", 1)[1].strip())
        assert payload.get("mtime") == expected_mtime, (
            f"mtime mismatch: {payload.get('mtime')} != {expected_mtime}"
        )

    @pytest.mark.asyncio
    async def test_activity_change_emits_activity_changed_event(
        self, board_dir: Path
    ) -> None:
        """activity.jsonl change must yield event='activity-changed' with mtime.

        Current code only emits 'tasks-changed' → FAILS.
        """
        from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415

        engine = KanbanEngine(board_dir)
        activity = engine.kanban_dir / "activity.jsonl"
        activity.write_text("{}\n", encoding="utf-8")
        expected_mtime = activity.stat().st_mtime_ns

        async def _one_change(*_a, **_k):
            yield {(MagicMock(), str(activity))}

        app.dependency_overrides[get_engine] = lambda: engine
        try:
            with patch("owlbear_cockpit.routes.events.awatch", _one_change):
                transport = httpx.ASGITransport(app=app)
                async with (
                    httpx.AsyncClient(
                        transport=transport, base_url="http://test"
                    ) as ac,
                    ac.stream("GET", "/api/events") as response,
                ):
                    lines: list[str] = []
                    async for line in response.aiter_lines():
                        if line.startswith(("event:", "data:")):
                            lines.append(line)
                        if len(lines) >= 2:
                            break
        finally:
            app.dependency_overrides.clear()

        event_line = next((ln for ln in lines if ln.startswith("event:")), None)
        data_line = next((ln for ln in lines if ln.startswith("data:")), None)
        assert event_line is not None, "No event line received"
        assert event_line.split(":", 1)[1].strip() == "activity-changed", (
            f"Expected 'activity-changed', got: {event_line!r}"
        )
        assert data_line is not None, "No data line received"
        payload = json.loads(data_line.split(":", 1)[1].strip())
        assert payload.get("mtime") == expected_mtime, (
            f"mtime mismatch: {payload.get('mtime')} != {expected_mtime}"
        )

    @pytest.mark.asyncio
    async def test_mixed_batch_yields_tasks_and_decisions_changed_events(
        self, board_dir: Path
    ) -> None:
        """A batch with both a tasks path and a decisions/pending path must yield
        two distinct events: 'tasks-changed' and 'decisions-changed'.

        Current code emits only one 'tasks-changed' event per batch → FAILS.
        """
        from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415

        engine = KanbanEngine(board_dir)
        task_md = engine.tasks_dir / "task-11.md"
        task_md.write_text("# task 11\n", encoding="utf-8")
        pending_dir = engine.kanban_dir / "decisions" / "pending"
        pending_dir.mkdir(parents=True, exist_ok=True)
        dr_md = pending_dir / "dr-11.md"
        dr_md.write_text("# DR-11\n", encoding="utf-8")

        async def _mixed_batch(*_a, **_k):
            yield {(MagicMock(), str(task_md)), (MagicMock(), str(dr_md))}

        app.dependency_overrides[get_engine] = lambda: engine
        try:
            with patch("owlbear_cockpit.routes.events.awatch", _mixed_batch):
                transport = httpx.ASGITransport(app=app)
                async with (
                    httpx.AsyncClient(
                        transport=transport, base_url="http://test"
                    ) as ac,
                    ac.stream("GET", "/api/events") as response,
                ):
                    event_names: list[str] = []
                    async for line in response.aiter_lines():
                        if line.startswith("event:"):
                            event_names.append(line.split(":", 1)[1].strip())
                        if len(event_names) >= 2:
                            break
        finally:
            app.dependency_overrides.clear()

        assert "tasks-changed" in event_names, (
            f"Expected 'tasks-changed' in mixed batch; got: {event_names!r}"
        )
        assert "decisions-changed" in event_names, (
            f"Expected 'decisions-changed' in mixed batch; got: {event_names!r}. "
            f"Current code only emits 'tasks-changed' per batch."
        )

    @pytest.mark.asyncio
    async def test_mixed_batch_yields_all_three_surface_events(
        self, board_dir: Path
    ) -> None:
        """A batch with tasks, decisions/pending, and activity.jsonl paths must yield
        three separate events, one per surface.

        Current code emits only one 'tasks-changed' → FAILS.
        """
        from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415

        engine = KanbanEngine(board_dir)
        task_md = engine.tasks_dir / "task-20.md"
        task_md.write_text("# task 20\n", encoding="utf-8")
        pending_dir = engine.kanban_dir / "decisions" / "pending"
        pending_dir.mkdir(parents=True, exist_ok=True)
        dr_md = pending_dir / "dr-20.md"
        dr_md.write_text("# DR-20\n", encoding="utf-8")
        activity = engine.kanban_dir / "activity.jsonl"
        activity.write_text("{}\n", encoding="utf-8")

        async def _all_surfaces(*_a, **_k):
            yield {
                (MagicMock(), str(task_md)),
                (MagicMock(), str(dr_md)),
                (MagicMock(), str(activity)),
            }

        app.dependency_overrides[get_engine] = lambda: engine
        try:
            with patch("owlbear_cockpit.routes.events.awatch", _all_surfaces):
                transport = httpx.ASGITransport(app=app)
                async with (
                    httpx.AsyncClient(
                        transport=transport, base_url="http://test"
                    ) as ac,
                    ac.stream("GET", "/api/events") as response,
                ):
                    event_names: list[str] = []
                    async for line in response.aiter_lines():
                        if line.startswith("event:"):
                            event_names.append(line.split(":", 1)[1].strip())
                        if len(event_names) >= 3:
                            break
        finally:
            app.dependency_overrides.clear()

        assert set(event_names) == {
            "tasks-changed",
            "decisions-changed",
            "activity-changed",
        }, (
            f"Expected all three surface events from a mixed batch. "
            f"Got: {event_names!r}. "
            f"Current code only emits 'tasks-changed'."
        )

    @pytest.mark.asyncio
    async def test_per_surface_mtime_is_max_of_paths_for_that_surface(
        self, board_dir: Path
    ) -> None:
        """When a batch contains two tasks-changed paths, the emitted mtime is the
        max st_mtime_ns across those two paths (not across all surfaces combined).

        Current code computes a single global max mtime across ALL paths → FAILS if
        a decisions path has a higher mtime than tasks (wrong surface's mtime used).
        """
        from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415

        engine = KanbanEngine(board_dir)
        task_early = engine.tasks_dir / "task-early.md"
        task_early.write_text("# early\n", encoding="utf-8")
        task_early_mtime = task_early.stat().st_mtime_ns

        # Ensure task_late has a later mtime
        await asyncio.sleep(0.01)
        task_late = engine.tasks_dir / "task-late.md"
        task_late.write_text("# late\n", encoding="utf-8")
        task_late_mtime = task_late.stat().st_mtime_ns
        assert task_late_mtime > task_early_mtime, (
            "Test setup: task_late must have newer mtime"
        )

        # decisions/pending path with VERY late mtime (newest overall)
        pending_dir = engine.kanban_dir / "decisions" / "pending"
        pending_dir.mkdir(parents=True, exist_ok=True)
        await asyncio.sleep(0.01)
        dr = pending_dir / "dr-x.md"
        dr.write_text("# DR-X\n", encoding="utf-8")
        dr_mtime = dr.stat().st_mtime_ns
        assert dr_mtime > task_late_mtime, "Test setup: dr must have newest mtime"

        async def _two_tasks_one_dr(*_a, **_k):
            yield {
                (MagicMock(), str(task_early)),
                (MagicMock(), str(task_late)),
                (MagicMock(), str(dr)),
            }

        app.dependency_overrides[get_engine] = lambda: engine
        tasks_mtimes: list[int] = []
        try:
            with patch("owlbear_cockpit.routes.events.awatch", _two_tasks_one_dr):
                transport = httpx.ASGITransport(app=app)
                async with (
                    httpx.AsyncClient(
                        transport=transport, base_url="http://test"
                    ) as ac,
                    ac.stream("GET", "/api/events") as response,
                ):
                    current_event: str | None = None
                    async for line in response.aiter_lines():
                        if line.startswith("event:"):
                            current_event = line.split(":", 1)[1].strip()
                        elif (
                            line.startswith("data:")
                            and current_event == "tasks-changed"
                        ):
                            payload = json.loads(line.split(":", 1)[1].strip())
                            tasks_mtimes.append(payload.get("mtime", 0))
                            current_event = None
        finally:
            app.dependency_overrides.clear()

        assert tasks_mtimes, "Expected at least one 'tasks-changed' event"
        assert tasks_mtimes[0] == task_late_mtime, (
            f"tasks-changed mtime must be max of tasks paths ({task_late_mtime}), "
            f"not the global max including decisions ({dr_mtime}). "
            f"Got: {tasks_mtimes[0]}"
        )

    @pytest.mark.asyncio
    async def test_decisions_surviving_path_emits_decisions_changed_not_tasks_changed(
        self, board_dir: Path
    ) -> None:
        """When a decisions/pending batch has one surviving and one deleted path,
        exactly one 'decisions-changed' event is emitted (not 'tasks-changed').

        Current code emits 'tasks-changed' for any surviving path → FAILS.
        """
        from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415

        engine = KanbanEngine(board_dir)
        pending_dir = engine.kanban_dir / "decisions" / "pending"
        pending_dir.mkdir(parents=True, exist_ok=True)
        surviving_dr = pending_dir / "dr-alive.md"
        surviving_dr.write_text("# alive\n", encoding="utf-8")
        deleted_dr = pending_dir / "dr-gone.md"
        assert not deleted_dr.exists(), "Test setup: deleted_dr must not exist"

        async def _mixed_decisions(*_a, **_k):
            yield {
                (MagicMock(), str(surviving_dr)),
                (MagicMock(), str(deleted_dr)),
            }

        app.dependency_overrides[get_engine] = lambda: engine
        try:
            with patch("owlbear_cockpit.routes.events.awatch", _mixed_decisions):
                transport = httpx.ASGITransport(app=app)
                async with (
                    httpx.AsyncClient(
                        transport=transport, base_url="http://test"
                    ) as ac,
                    ac.stream("GET", "/api/events") as response,
                ):
                    event_names: list[str] = []
                    async for line in response.aiter_lines():
                        if line.startswith("event:"):
                            event_names.append(line.split(":", 1)[1].strip())
                        if event_names:
                            break
        finally:
            app.dependency_overrides.clear()

        assert "decisions-changed" in event_names, (
            f"Surviving decisions/pending path must emit 'decisions-changed'. "
            f"Got: {event_names!r}"
        )
        assert "tasks-changed" not in event_names, (
            f"decisions/pending path must NOT produce 'tasks-changed'. "
            f"Got: {event_names!r}. "
            f"Current code always emits 'tasks-changed' for surviving paths."
        )

    @pytest.mark.asyncio
    async def test_deletion_only_tasks_batch_emits_tasks_changed_event(
        self, board_dir: Path
    ) -> None:
        """Post-1346 AC4: When ALL paths for the tasks surface are deleted (stat raises
        FileNotFoundError), a 'tasks-changed' event MUST still be emitted using a
        synthetic time.time_ns() mtime.

        Old contract said deletion-only suppresses the event. New contract: emit
        even for deleted paths so the frontend detects the deletion and refetches.
        A surviving decisions/pending path in the same batch must still yield
        'decisions-changed' independently.
        """
        from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415

        engine = KanbanEngine(board_dir)
        # This task file does not exist on disk — stat() will raise FileNotFoundError
        deleted_task = engine.tasks_dir / "task-vanished.md"
        assert not deleted_task.exists(), "Test setup: task must not exist on disk"

        pending_dir = engine.kanban_dir / "decisions" / "pending"
        pending_dir.mkdir(parents=True, exist_ok=True)
        surviving_dr = pending_dir / "dr-still-here.md"
        surviving_dr.write_text("# DR\n", encoding="utf-8")

        async def _deleted_task_surviving_dr(*_a, **_k):
            yield {
                (MagicMock(), str(deleted_task)),
                (MagicMock(), str(surviving_dr)),
            }

        app.dependency_overrides[get_engine] = lambda: engine
        event_names: list[str] = []
        try:
            with patch(
                "owlbear_cockpit.routes.events.awatch", _deleted_task_surviving_dr
            ):
                transport = httpx.ASGITransport(app=app)
                async with (
                    httpx.AsyncClient(
                        transport=transport, base_url="http://test"
                    ) as ac,
                    ac.stream("GET", "/api/events") as response,
                ):
                    async for line in response.aiter_lines():
                        if line.startswith("event:"):
                            event_names.append(line.split(":", 1)[1].strip())
                        if len(event_names) >= 2:
                            break
        finally:
            app.dependency_overrides.clear()

        assert "tasks-changed" in event_names, (
            f"tasks-changed MUST be emitted for a deleted task path (AC4: synthetic mtime). "
            f"Got events: {event_names!r}. "
            f"Old contract said 'suppress deletion-only events' — new contract requires emission."
        )
        assert "decisions-changed" in event_names, (
            f"decisions-changed MUST be emitted for the surviving decisions path. "
            f"Got events: {event_names!r}"
        )

    @pytest.mark.asyncio
    async def test_multiple_same_type_tasks_paths_emit_exactly_one_event(
        self, board_dir: Path
    ) -> None:
        """A batch with two tasks/*.md paths must emit exactly ONE 'tasks-changed'
        event, not two. Multiple same-type paths coalesce into a single event
        (AC4: 'exactly one SSE event per distinct surface type present').
        """
        from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415

        engine = KanbanEngine(board_dir)
        task_a = engine.tasks_dir / "task-coalesce-a.md"
        task_a.write_text("# a\n", encoding="utf-8")
        task_b = engine.tasks_dir / "task-coalesce-b.md"
        task_b.write_text("# b\n", encoding="utf-8")

        async def _two_tasks(*_a, **_k):
            yield {(MagicMock(), str(task_a)), (MagicMock(), str(task_b))}

        app.dependency_overrides[get_engine] = lambda: engine
        event_names: list[str] = []
        try:
            with patch("owlbear_cockpit.routes.events.awatch", _two_tasks):
                transport = httpx.ASGITransport(app=app)
                async with (
                    httpx.AsyncClient(
                        transport=transport, base_url="http://test"
                    ) as ac,
                    ac.stream("GET", "/api/events") as response,
                ):
                    async for line in response.aiter_lines():
                        if line.startswith("event:"):
                            event_names.append(line.split(":", 1)[1].strip())
        finally:
            app.dependency_overrides.clear()

        tasks_events = [e for e in event_names if e == "tasks-changed"]
        assert len(tasks_events) == 1, (
            f"Two tasks/*.md paths in a single batch must coalesce into exactly one "
            f"'tasks-changed' event. Got {len(tasks_events)} 'tasks-changed' events "
            f"in {event_names!r}."
        )


# ---------------------------------------------------------------------------
# AC5: Missing kanban_dir → 200 with empty stream, no crash (td:1)
# ---------------------------------------------------------------------------


class TestFromAC_MissingKanbanDir:
    """AC5: When kanban_dir does not exist, the stream endpoint must return 200
    with an empty stream and never call awatch."""

    @pytest.mark.asyncio
    async def test_missing_kanban_dir_awatch_not_called(self, tmp_path: Path) -> None:
        """When kanban_dir does not exist (but tasks_dir path does exist on disk),
        awatch must NOT be called — the guard fires on kanban_dir, not tasks_dir.

        Current code guards on tasks_dir.exists() — if tasks_dir exists, it calls
        awatch even when kanban_dir itself is absent → this test FAILS.
        """
        from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415

        # Mock engine: tasks_dir exists on disk, kanban_dir does not
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir(parents=True)
        missing_kanban_dir = tmp_path / "nonexistent_kanban"
        assert not missing_kanban_dir.exists()

        mock_engine = MagicMock()
        mock_engine.tasks_dir = tasks_dir
        mock_engine.kanban_dir = missing_kanban_dir

        awatch_calls: list = []

        async def _record_if_called(*args, **_kw):
            awatch_calls.append(args)
            return
            yield  # pragma: no cover

        app.dependency_overrides[get_engine] = lambda: mock_engine
        try:
            with patch("owlbear_cockpit.routes.events.awatch", _record_if_called):
                transport = httpx.ASGITransport(app=app)
                async with (
                    httpx.AsyncClient(
                        transport=transport, base_url="http://test"
                    ) as ac,
                    ac.stream("GET", "/api/events") as response,
                ):
                    assert response.status_code == 200
                    async for _ in response.aiter_lines():
                        pass
        finally:
            app.dependency_overrides.clear()

        assert not awatch_calls, (
            f"awatch must NOT be called when kanban_dir is missing. "
            f"Got {len(awatch_calls)} call(s). "
            f"Current code guards on tasks_dir.exists() — if tasks_dir exists, "
            f"it calls awatch even when kanban_dir is absent."
        )

    @pytest.mark.asyncio
    async def test_missing_kanban_dir_stream_is_empty(self, tmp_path: Path) -> None:
        """When kanban_dir does not exist the consumed SSE stream must carry no
        event lines and no data lines — it closes immediately after the 200 header.

        The existing test proves awatch is not called; this test proves the 'no
        events' subclause of AC5 by asserting the full stream body is empty.
        """
        from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415

        missing_kanban_dir = tmp_path / "nonexistent_kanban"
        assert not missing_kanban_dir.exists()

        mock_engine = MagicMock()
        mock_engine.tasks_dir = tmp_path / "tasks"
        mock_engine.kanban_dir = missing_kanban_dir

        app.dependency_overrides[get_engine] = lambda: mock_engine
        stream_lines: list[str] = []
        try:
            with patch("owlbear_cockpit.routes.events.awatch"):
                transport = httpx.ASGITransport(app=app)
                async with (
                    httpx.AsyncClient(
                        transport=transport, base_url="http://test"
                    ) as ac,
                    ac.stream("GET", "/api/events") as response,
                ):
                    assert response.status_code == 200
                    async for line in response.aiter_lines():
                        if line.startswith(("event:", "data:")):
                            stream_lines.append(line)
        finally:
            app.dependency_overrides.clear()

        assert not stream_lines, (
            f"Stream must contain no event or data lines when kanban_dir is missing. "
            f"Got {len(stream_lines)} line(s): {stream_lines!r}"
        )
