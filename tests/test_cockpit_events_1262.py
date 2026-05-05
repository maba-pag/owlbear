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

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

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


@pytest.fixture
def board_dir(tmp_path: Path) -> Path:
    """Minimal kanban board with no tasks."""
    return _make_board(tmp_path)


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


class TestFromAC_WatchFilter:
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
    async def test_filter_rejects_archive_md(self, board_dir: Path) -> None:
        """Filter must return False for .md files in archive/ (not a watched surface).

        Current generic filter accepts any .md regardless of directory → returns True
        → this test FAILS against current code.
        """
        captured, engine = await _run_and_capture(board_dir)
        archive_md = str(engine.kanban_dir / "archive" / "100-done-task.md")
        assert captured["filter"](None, archive_md) is False, (
            f"Filter must reject archive/*.md; got True for {archive_md!r}. "
            f"Current filter accepts any .md — new filter must be board-specific."
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
    async def test_archive_md_classified_as_none_no_event(
        self, board_dir: Path
    ) -> None:
        """A path in archive/ must be classified as None (no event emitted).

        Current code emits 'tasks-changed' for any surviving .md → FAILS.
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
        finally:
            app.dependency_overrides.clear()

        assert not events_received, (
            f"archive/*.md must produce no events (classifier returns None). "
            f"Got: {events_received!r}. "
            f"Current code emits 'tasks-changed' for any surviving .md."
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
    async def test_deletion_only_tasks_batch_emits_no_tasks_changed_event(
        self, board_dir: Path
    ) -> None:
        """When ALL paths for the tasks surface in a batch are deleted (stat raises
        FileNotFoundError), no 'tasks-changed' event must be emitted for that type.

        A surviving decisions/pending path in the same batch must still yield
        'decisions-changed', proving the deletion-only suppression is per-surface.

        This covers the deletion-only suppression branch at events.py:113 for a type
        where every path has vanished.
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

        assert "tasks-changed" not in event_names, (
            f"tasks-changed must NOT be emitted when the only tasks path is deleted "
            f"(stat raises FileNotFoundError). Got events: {event_names!r}"
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
