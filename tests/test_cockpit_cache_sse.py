from __future__ import annotations

# --- merged from tests/test_cockpit_cache_sse_1346.py ---
"""Failing tests for #1346: Fix Cockpit cache and SSE invalidation.

AC coverage:
  AC1 (td:2): MtimeScanCache uses a directory signature detecting create, delete,
              rename, archive moves; excludes .tmp-* and dotfiles; not just max mtime.
  AC2 (td:2): GET /api/tasks reloads on signature change; never returns a
              deleted/archived active task from cache.
  AC3 (td:2): Mutation routes cause cache invalidation; no stale data on next GET.
  AC4 (td:2): GET /api/events emits tasks-changed for deleted/archived paths even
              when file no longer exists; payload is a numeric mtime; delete-only
              batches emit an event.
  AC5 (td:2): Archive directory writes trigger tasks-changed; archived tasks absent
              from active list.
  AC6 (td:1): Existing activity-changed and decisions-changed behavior is intact
              alongside the new archive-watch support.
  AC7 (td:2): Durable scenarios: deletion of non-newest task, archive move of
              non-newest, delete-only watch batch, mixed delete/survivor batch,
              mutation-route cache invalidation.

All tests FAIL until the builder implements the robust signature and SSE fixes in:
  serve/cockpit/src/owlbear_cockpit/cache.py
  serve/cockpit/src/owlbear_cockpit/routes/events.py
  serve/cockpit/src/owlbear_cockpit/routes/read.py   (double-scan fix)
"""


import asyncio
import json
import os
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlbear_kanban import KanbanEngine

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

    from owlbear_cockpit.cache import MtimeScanCache


# ---------------------------------------------------------------------------
# Board config & fixture helpers
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


def _set_mtime_older(path: Path, offset_ns: int = 2_000_000_000) -> None:
    """Set the file's mtime to offset_ns nanoseconds before its current mtime."""
    stat = path.stat()
    old_ns = stat.st_mtime_ns - offset_ns
    os.utime(path, ns=(stat.st_atime_ns, old_ns))


def _task_file(tasks_dir: Path, task_id: int) -> Path:
    """Return the task file path for the given numeric task ID.

    Engine names files as '{id}-{slug}.md' (e.g., '1-alpha-task.md').
    """
    matches = sorted(
        tasks_dir.glob(f"{task_id}-*.md"),
        key=lambda p: p.name,
    )
    if not matches:
        raise FileNotFoundError(
            f"No task file for id={task_id} in {tasks_dir}. "
            f"Files present: {sorted(p.name for p in tasks_dir.glob('*.md'))}"
        )
    return matches[0]


@pytest.fixture
def board_dir(tmp_path: Path) -> Path:
    """Board with no tasks (clean slate for cache unit tests)."""
    return _make_board(tmp_path)


@pytest.fixture
def engine(board_dir: Path) -> KanbanEngine:
    """KanbanEngine bound to the test board."""
    eng = KanbanEngine(board_dir)
    eng.list_tasks()
    return eng


@pytest.fixture
def two_task_board(tmp_path: Path) -> Path:
    """Board with two tasks where task 1 has a forcibly older mtime.

    Layout after setup:
      tasks/1-*.md  mtime = T-2s  (older, the 'non-newest')
      tasks/2-*.md  mtime = T     (newer, stays in place)
    """
    kanban_dir = _make_board(tmp_path)
    seed = KanbanEngine(kanban_dir)
    seed.create_task("Alpha task", status="todo", priority="important")
    seed.create_task("Beta task", status="todo", priority="needed")
    seed.list_tasks()
    # Force task 1 to have an older mtime so deleting it does not change max-mtime.
    tasks_dir = kanban_dir / "tasks"
    task1_file = _task_file(tasks_dir, 1)
    _set_mtime_older(task1_file)
    return kanban_dir


@pytest.fixture
def two_task_engine(two_task_board: Path) -> KanbanEngine:
    """KanbanEngine on the two-task board, with task list pre-populated."""
    eng = KanbanEngine(two_task_board)
    eng.list_tasks()
    return eng


@pytest.fixture
def cache(engine: KanbanEngine) -> MtimeScanCache:
    """Fresh MtimeScanCache bound to the engine's tasks directory."""
    from owlbear_cockpit.cache import MtimeScanCache  # noqa: PLC0415

    return MtimeScanCache(engine.tasks_dir)


@pytest.fixture
def two_task_cache(two_task_engine: KanbanEngine) -> MtimeScanCache:
    """Cache for the two-task board."""
    from owlbear_cockpit.cache import MtimeScanCache  # noqa: PLC0415

    return MtimeScanCache(two_task_engine.tasks_dir)


@pytest.fixture
def http_client(two_task_engine: KanbanEngine, two_task_cache: MtimeScanCache):
    """TestClient with both get_engine and get_cache overridden."""
    from fastapi.testclient import TestClient  # noqa: PLC0415

    from owlbear_cockpit.deps import get_cache  # noqa: PLC0415
    from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415

    app.dependency_overrides[get_engine] = lambda: two_task_engine
    app.dependency_overrides[get_cache] = lambda: two_task_cache
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helper: run events route with a mock awatch, collect yielded SSE items
# ---------------------------------------------------------------------------


async def _collect_sse(
    engine: KanbanEngine,
    mock_awatch_batches: list,
) -> list[dict]:
    """Call the events route directly, collect all dicts yielded by _stream().

    `mock_awatch_batches` is a list of batches (each batch is an iterable of
    2-tuples (change_type, path_str)).  The mock yields each batch in order.

    Returns a list of dicts like {"event": "tasks-changed", "data": '{"mtime":1}'}.
    """
    from owlbear_cockpit.routes.events import events as events_route  # noqa: PLC0415

    async def _mock_awatch(*_args, **_kwargs):
        for batch in mock_awatch_batches:
            yield batch

    request = MagicMock()
    request.is_disconnected = AsyncMock(return_value=False)

    collected: list[dict] = []
    with patch("owlbear_cockpit.routes.events.awatch", _mock_awatch):
        sse_response = await events_route(request=request, engine=engine)
        async with asyncio.timeout(5.0):
            async for item in sse_response.body_iterator:
                if isinstance(item, dict):
                    collected.append(item)
    return collected


# ===========================================================================
# AC1 (td:2): MtimeScanCache — robust directory signature
# ===========================================================================


class TestFromAC_CacheDirSignature:
    """AC1: signature must track more than max mtime — also file count or name-set —
    so that deletions, renames, and archive moves are detected."""

    def test_signature_changes_when_non_newest_task_deleted(self, two_task_board: Path) -> None:
        """Deleting the non-newest task file must change the signature.

        Current scan() returns max(st_mtime_ns), which is unchanged when the
        older file is removed → scan() returns same value → bug.
        """
        from owlbear_cockpit.cache import MtimeScanCache  # noqa: PLC0415

        tasks_dir = two_task_board / "tasks"
        cache = MtimeScanCache(tasks_dir)

        sig_before = cache.scan()

        # Delete the task file with the oldest (forced) mtime.
        task1_file = _task_file(tasks_dir, 1)
        task1_file.unlink()

        sig_after = cache.scan()

        assert sig_after != sig_before, (
            "scan() must return a different value after deleting the non-newest task "
            "file. The current max-mtime-only scan() returns the same value because "
            "the deleted file was not the newest — this is the AC1 bug."
        )

    def test_has_changed_true_when_non_newest_task_deleted(self, two_task_board: Path) -> None:
        """has_changed() must return True after deleting the non-newest task file.

        Current has_changed() rescans with max-mtime; since the max is unchanged,
        it returns False → cache is not invalidated → stale data served.
        """
        from owlbear_cockpit.cache import MtimeScanCache  # noqa: PLC0415

        tasks_dir = two_task_board / "tasks"
        cache = MtimeScanCache(tasks_dir)

        # Prime the cache so has_changed() has a baseline.
        cache.has_changed()

        task1_file = _task_file(tasks_dir, 1)
        task1_file.unlink()

        assert cache.has_changed() is True, (
            "has_changed() must return True when the non-newest task file is deleted. "
            "Current implementation only tracks max mtime → returns False → cache "
            "staleness goes undetected."
        )

    def test_tmp_prefixed_files_excluded_from_signature(self, board_dir: Path) -> None:
        """Adding a .tmp-* file to tasks_dir must NOT change the signature.

        Current scan() uses os.scandir with is_file() only — it counts .tmp- files.
        The new implementation must exclude .tmp-* names from the signature,
        consistent with the write-layer convention (storage never persists .tmp- files).
        """
        from owlbear_cockpit.cache import MtimeScanCache  # noqa: PLC0415

        tasks_dir = board_dir / "tasks"
        # Create one real task so the dir is not empty.
        real_task = tasks_dir / "0001-real-task.md"
        real_task.write_text("---\nid: 1\n---\n", encoding="utf-8")

        cache = MtimeScanCache(tasks_dir)
        sig_before = cache.scan()

        # Add a temp file — should be invisible to the signature.
        (tasks_dir / ".tmp-0001-real-task.md").write_text("temp", encoding="utf-8")

        sig_after = cache.scan()

        assert sig_after == sig_before, (
            "scan() signature must be unchanged after adding a .tmp- prefixed file. "
            "Current scan() counts all files including .tmp- → signature changes "
            "spuriously and invalidates cache unnecessarily."
        )

    def test_dotfiles_excluded_from_signature(self, board_dir: Path) -> None:
        """Adding a dotfile to tasks_dir must NOT change the signature.

        Dotfiles (files with names starting with '.') are not written by the
        storage layer and must be excluded from the directory signature.
        """
        from owlbear_cockpit.cache import MtimeScanCache  # noqa: PLC0415

        tasks_dir = board_dir / "tasks"
        real_task = tasks_dir / "0001-real-task.md"
        real_task.write_text("---\nid: 1\n---\n", encoding="utf-8")

        cache = MtimeScanCache(tasks_dir)
        sig_before = cache.scan()

        (tasks_dir / ".DS_Store").write_bytes(b"dotfile")

        sig_after = cache.scan()

        assert sig_after == sig_before, (
            "scan() signature must be unchanged after adding a dotfile (.DS_Store). "
            "Current scan() includes all files → signature spuriously changes."
        )

    def test_signature_changes_on_file_rename(self, board_dir: Path) -> None:
        """Renaming a task file (without touching its mtime) must change the signature.

        A name-set signature detects renames; a max-mtime-only signature does not,
        because rename preserves the file's mtime and the max is unchanged.
        """
        from owlbear_cockpit.cache import MtimeScanCache  # noqa: PLC0415

        tasks_dir = board_dir / "tasks"
        file_a = tasks_dir / "0001-original-name.md"
        file_a.write_text("---\nid: 1\n---\n", encoding="utf-8")

        cache = MtimeScanCache(tasks_dir)
        sig_before = cache.scan()

        # Rename preserves the file's content mtime on most filesystems.
        file_b = tasks_dir / "0001-renamed.md"
        file_a.rename(file_b)

        sig_after = cache.scan()

        assert sig_after != sig_before, (
            "scan() must return a different signature after renaming a task file. "
            "Max-mtime-only scan() returns the same value (mtime preserved on rename) "
            "— the new implementation must track the file-name set."
        )


# ===========================================================================
# AC2 (td:2): GET /api/tasks never returns deleted/archived tasks from cache
# ===========================================================================


class TestFromAC_TaskListCacheInvalidation:
    """AC2: GET /api/tasks must reload whenever the directory signature changes and
    must never return a deleted or archived active task from stale cache."""

    def test_get_tasks_excludes_deleted_non_newest_task(self, http_client: TestClient, two_task_board: Path) -> None:
        """After deleting the non-newest task file, GET /api/tasks must not return it.

        Current bug: max-mtime cache does not detect the deletion → cache miss is not
        triggered → old cached task list is returned including the deleted task.
        """
        tasks_dir = two_task_board / "tasks"

        # Prime the cache with both tasks.
        resp = http_client.get("/api/tasks")
        assert resp.status_code == 200
        task_ids_before = {t["id"] for t in resp.json()["tasks"]}
        assert len(task_ids_before) == 2, "Precondition: both tasks must be listed"

        # Delete the older task file (task1).
        task1_file = _task_file(tasks_dir, 1)
        task_id_deleted = int(task1_file.name.split("-")[0])
        task1_file.unlink()

        resp2 = http_client.get("/api/tasks")
        assert resp2.status_code == 200
        task_ids_after = {t["id"] for t in resp2.json()["tasks"]}

        assert task_id_deleted not in task_ids_after, (
            f"Task {task_id_deleted} was deleted from tasks/ but is still returned by "
            "GET /api/tasks. The max-mtime cache did not detect the deletion because "
            "the deleted file was not the newest — AC2 requires a signature that tracks "
            "file count or name-set."
        )

    def test_get_tasks_excludes_archived_non_newest_task(self, http_client: TestClient, two_task_board: Path) -> None:
        """After moving the non-newest task to archive/, GET /api/tasks must exclude it.

        Current bug: moving (not deleting) the older task does not change max-mtime →
        cache not invalidated → archived task still appears in the active list.
        """
        tasks_dir = two_task_board / "tasks"
        archive_dir = two_task_board / "archive"

        # Prime the cache.
        resp = http_client.get("/api/tasks")
        assert resp.status_code == 200
        task_ids_before = {t["id"] for t in resp.json()["tasks"]}
        assert len(task_ids_before) == 2

        # Move the older task file to archive/ (simulating what the engine does).
        task1_file = _task_file(tasks_dir, 1)
        task_id_archived = int(task1_file.name.split("-")[0])
        task1_file.rename(archive_dir / task1_file.name)

        resp2 = http_client.get("/api/tasks")
        assert resp2.status_code == 200
        task_ids_after = {t["id"] for t in resp2.json()["tasks"]}

        assert task_id_archived not in task_ids_after, (
            f"Task {task_id_archived} was moved to archive/ but is still returned by "
            "GET /api/tasks. The max-mtime cache did not detect the archive move — "
            "AC2 requires a signature that detects file removal from tasks/."
        )


# ===========================================================================
# AC3 (td:2): Mutation routes — cache invalidated, no stale data on next GET
# ===========================================================================


class TestFromAC_MutationCacheInvalidation:
    """AC3: The cache must detect mutations deterministically — the scan-then-decide
    path must be atomic with respect to the signature state, and the signature must
    track enough information that archive/delete mutations of non-newest files are
    always detected without relying on coincidental lock-file side effects."""

    def test_has_changed_detects_archive_of_non_newest_when_same_mtime(self, tmp_path: Path) -> None:
        """When two tasks share the same mtime and one is removed (archived),
        the cache must still detect the change via file-count or name-set.

        Current bug: max-mtime is identical before and after → has_changed() = False
        → mutation route cannot trigger cache reload deterministically.

        AC3 requires 'deterministic' invalidation: the scan-then-decide path must
        detect the mutation. This test proves the prerequisite is broken: the cache
        cannot detect a removal when max-mtime is unchanged.
        """
        from owlbear_cockpit.cache import MtimeScanCache  # noqa: PLC0415

        kanban_dir = _make_board(tmp_path / "board3")
        seed = KanbanEngine(kanban_dir)
        seed.create_task("Alpha task", status="todo", priority="important")
        seed.create_task("Beta task", status="todo", priority="needed")
        seed.list_tasks()
        tasks_dir = kanban_dir / "tasks"

        task1_file = _task_file(tasks_dir, 1)
        task2_file = _task_file(tasks_dir, 2)

        # Set both files to the SAME mtime (common_mtime = task1's original mtime).
        # This ensures that removing either file cannot be detected via max-mtime.
        common_mtime_ns = task1_file.stat().st_mtime_ns
        for f in (task1_file, task2_file):
            stat = f.stat()
            os.utime(f, ns=(stat.st_atime_ns, common_mtime_ns))

        cache = MtimeScanCache(tasks_dir)
        # Prime the cache: _last_mtime = common_mtime_ns.
        cache.has_changed()

        # Simulate the filesystem effect of an archive mutation:
        # remove task1 from tasks/ (the non-newest, same-mtime file).
        archive_dir = kanban_dir / "archive"
        task1_file.rename(archive_dir / task1_file.name)

        # The cache must detect this change (file-count or name-set changed).
        # Current max-mtime scan: max remains common_mtime_ns → has_changed() = False.
        assert cache.has_changed() is True, (
            "has_changed() must return True after archiving a task when both files share "
            "the same mtime. Current max-mtime scan cannot distinguish between "
            "{task1, task2} and {task2} when mtime is identical — AC3 requires "
            "deterministic detection of file-set changes."
        )

    def test_get_tasks_after_same_mtime_archive_excludes_archived_task(self, tmp_path: Path) -> None:
        """When two tasks share the same mtime and one is archived,
        GET /api/tasks must exclude the archived task on the next request.

        This is the observable contract for AC3: mutation routes must deterministically
        cause the next GET /api/tasks to reflect the updated state.
        """
        from fastapi.testclient import TestClient  # noqa: PLC0415

        from owlbear_cockpit.cache import MtimeScanCache  # noqa: PLC0415
        from owlbear_cockpit.deps import get_cache  # noqa: PLC0415
        from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415

        kanban_dir = _make_board(tmp_path / "board3b")
        seed = KanbanEngine(kanban_dir)
        seed.create_task("Alpha task", status="todo", priority="important")
        seed.create_task("Beta task", status="todo", priority="needed")
        seed.list_tasks()
        tasks_dir = kanban_dir / "tasks"
        archive_dir = kanban_dir / "archive"

        task1_file = _task_file(tasks_dir, 1)
        task2_file = _task_file(tasks_dir, 2)
        common_mtime_ns = task1_file.stat().st_mtime_ns
        for f in (task1_file, task2_file):
            stat = f.stat()
            os.utime(f, ns=(stat.st_atime_ns, common_mtime_ns))

        eng = KanbanEngine(kanban_dir)
        eng.list_tasks()
        local_cache = MtimeScanCache(eng.tasks_dir)

        app.dependency_overrides[get_engine] = lambda: eng
        app.dependency_overrides[get_cache] = lambda: local_cache
        try:
            client = TestClient(app)

            # Prime cache with both tasks.
            prime_resp = client.get("/api/tasks")
            assert prime_resp.status_code == 200
            assert len(prime_resp.json()["tasks"]) == 2, "Precondition: 2 tasks"

            # Simulate archive: move task1 to archive/ (no engine call = no lock file).
            task1_file.rename(archive_dir / task1_file.name)

            # Next GET /api/tasks must exclude task1.
            resp = client.get("/api/tasks")
            assert resp.status_code == 200
            task_ids = {t["id"] for t in resp.json()["tasks"]}
            assert 1 not in task_ids, (
                "Task 1 was moved to archive/ but GET /api/tasks still returns it. "
                "When both task files share the same mtime, the max-mtime cache cannot "
                "detect the removal — AC3 requires deterministic invalidation regardless "
                "of relative file mtimes."
            )
        finally:
            app.dependency_overrides.clear()

    def test_get_tasks_reflects_status_change_after_move_route(self, tmp_path: Path) -> None:
        """After POST /api/tasks/{id}/move, GET /api/tasks must reflect the new status.

        AC3/AC7 proof gap: existing AC3 tests use direct filesystem renames rather
        than calling the cockpit mutation route.  This test drives the full
        mutation-route → read-route cycle exactly as a real client would:

          1. Prime cache via GET /api/tasks (both tasks visible in 'todo').
          2. Move task 1 to 'in-progress' via POST /api/tasks/1/move.
          3. The route rewrites the task file on disk → file mtime changes.
          4. GET /api/tasks?status=todo must exclude task 1 (cache invalidated).

        Fails if cache.scan() still returns the old signature (e.g. because the
        mutation route does not touch files in tasks_dir or the signature ignores
        mtime changes to existing files).
        """
        from fastapi.testclient import TestClient  # noqa: PLC0415

        from owlbear_cockpit.cache import MtimeScanCache  # noqa: PLC0415
        from owlbear_cockpit.deps import get_cache  # noqa: PLC0415
        from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415

        kanban_dir = _make_board(tmp_path / "board_mutation")
        seed = KanbanEngine(kanban_dir)
        seed.create_task("Alpha task", status="todo", priority="important")
        seed.create_task("Beta task", status="todo", priority="needed")
        seed.list_tasks()

        eng = KanbanEngine(kanban_dir)
        eng.list_tasks()
        local_cache = MtimeScanCache(eng.tasks_dir)

        app.dependency_overrides[get_engine] = lambda: eng
        app.dependency_overrides[get_cache] = lambda: local_cache
        try:
            client = TestClient(app)

            # Prime the cache with both tasks in 'todo'.
            resp_prime = client.get("/api/tasks")
            assert resp_prime.status_code == 200
            todo_ids_before = {t["id"] for t in resp_prime.json()["tasks"] if t["status"] == "todo"}
            assert 1 in todo_ids_before, "Precondition: task 1 must be in 'todo'"

            # Move task 1 from 'todo' to 'in-progress' via the cockpit mutation route.
            task = eng.show_task("1")
            move_resp = client.post(
                "/api/tasks/1/move",
                json={"status": "in-progress", "updated": task.updated},
            )
            assert move_resp.status_code == 200, (
                f"POST /api/tasks/1/move returned {move_resp.status_code}: {move_resp.json()}"
            )

            # GET /api/tasks?status=todo must NOT include task 1 (now in-progress).
            resp_after = client.get("/api/tasks", params={"status": "todo"})
            assert resp_after.status_code == 200
            todo_ids_after = {t["id"] for t in resp_after.json()["tasks"]}

            assert 1 not in todo_ids_after, (
                "Task 1 was moved from 'todo' to 'in-progress' via POST /api/tasks/1/move, "
                "but GET /api/tasks?status=todo still returns it. "
                "The cache was not invalidated after the mutation route rewrote the task "
                "file on disk. AC3/AC7 requires deterministic cache invalidation after "
                "cockpit mutation routes change task visibility."
            )
        finally:
            app.dependency_overrides.clear()


# ===========================================================================
# AC4 (td:2): SSE — tasks-changed emitted for deleted/archived paths
# ===========================================================================


class TestFromAC_SSEDeletedPathEvent:
    """AC4: GET /api/events must emit tasks-changed for delete-only watch batches
    even when the changed task path no longer exists on disk.  The payload mtime
    must be a positive integer (numeric, not zero or missing)."""

    @pytest.mark.asyncio
    async def test_delete_only_batch_emits_tasks_changed(self, board_dir: Path) -> None:
        """A watch batch containing only a deleted task path must emit tasks-changed.

        Current events.py catches FileNotFoundError on stat() and skips the path,
        so no event is emitted for delete-only batches.  This is the AC4 bug.
        """
        engine = KanbanEngine(board_dir)

        # Path that looks like a task file but does NOT exist on disk.
        deleted_path = str(engine.tasks_dir / "99-deleted-task.md")
        assert not os.path.exists(deleted_path), (  # noqa: ASYNC240,PTH110
            "Precondition: test path must not exist on disk"
        )

        batch = {("deleted", deleted_path)}
        collected = await _collect_sse(engine, [batch])

        tasks_changed = [e for e in collected if e.get("event") == "tasks-changed"]
        assert len(tasks_changed) >= 1, (
            "tasks-changed event must be emitted for a delete-only watch batch. "
            "Current events.py skips paths that raise FileNotFoundError → no event "
            "emitted for pure deletion batches."
        )

    @pytest.mark.asyncio
    async def test_tasks_changed_payload_mtime_positive_for_deleted_path(self, board_dir: Path) -> None:
        """The tasks-changed payload mtime must be a positive integer even when the
        changed path no longer exists (so stat() is unavailable).

        The implementation must use an alternative mtime source (e.g., time.time_ns()
        or directory scan mtime) rather than skipping the deleted path entirely.
        """
        engine = KanbanEngine(board_dir)
        deleted_path = str(engine.tasks_dir / "99-gone.md")

        batch = {("deleted", deleted_path)}
        collected = await _collect_sse(engine, [batch])

        tasks_changed = [e for e in collected if e.get("event") == "tasks-changed"]
        assert len(tasks_changed) >= 1, (
            "tasks-changed event must be emitted for a deleted path. "
            "See test_delete_only_batch_emits_tasks_changed for the primary assertion."
        )
        payload = json.loads(tasks_changed[0]["data"])
        assert isinstance(payload.get("mtime"), int), (
            f"tasks-changed payload mtime must be an integer. Got: {payload!r}"
        )
        assert payload["mtime"] > 0, (
            f"tasks-changed payload mtime must be > 0. Got: {payload['mtime']}. "
            "An alternative mtime source (time.time_ns() or directory mtime) must be "
            "used when stat() raises FileNotFoundError."
        )

    @pytest.mark.asyncio
    async def test_mixed_batch_tasks_deleted_decisions_changed_emits_tasks_changed(self, board_dir: Path) -> None:
        """Mixed batch: deleted task path + surviving decisions file.

        In this batch the only task-classified path is the DELETED task path.
        The surviving path (decisions/pending/*.md) is decisions-changed, not
        tasks-changed.  tasks-changed must still be emitted for the deleted task path.

        Current bug: deleted task path → FileNotFoundError → skip → no tasks-changed
        emitted; only decisions-changed is emitted.
        """
        engine = KanbanEngine(board_dir)
        decisions_pending_dir = engine.kanban_dir / "decisions" / "pending"
        os.makedirs(decisions_pending_dir, exist_ok=True)  # noqa: PTH103

        # Create a real decisions file (so it survives stat()).
        decisions_file = decisions_pending_dir / "dr-99.md"
        with open(decisions_file, "w", encoding="utf-8") as fh:  # noqa: ASYNC230,PTH123
            fh.write("# DR 99\n")

        # Deleted task path that does NOT exist on disk.
        deleted_task = str(engine.tasks_dir / "99-deleted.md")
        assert not os.path.exists(deleted_task)  # noqa: ASYNC240,PTH110

        batch = {
            ("deleted", deleted_task),  # task-classified, file gone
            ("modified", str(decisions_file)),  # decisions-classified, file exists
        }
        collected = await _collect_sse(engine, [batch])

        tasks_changed = [e for e in collected if e.get("event") == "tasks-changed"]
        assert len(tasks_changed) >= 1, (
            "tasks-changed must be emitted for the deleted task path in a mixed batch. "
            "Current events.py skips deleted paths, so only decisions-changed is "
            "emitted — AC4 requires tasks-changed even when the file is gone."
        )

    @pytest.mark.asyncio
    async def test_repeated_tasks_changed_payload_differs_when_candidate_mtime_unchanged(self, board_dir: Path) -> None:
        """Two successive tasks-changed emissions from the same file at the same mtime
        must produce different (strictly increasing) payload mtime values.

        AC4 proof gap: _next_event_mtime() has a stateful guard —
        when candidate_mtime <= last_emitted_mtime, it returns last_emitted + 1 so
        the frontend always sees a new value and triggers a refetch.  This branch
        is exercised by sending two watch batches with the same path at the same
        pinned mtime:

          Batch 1: file.stat().st_mtime_ns = T → emitted = T
          Batch 2: same file, same mtime   → candidate T <= previous T → emitted T+1

        The test asserts that mtime2 == mtime1 + 1, proving the stateful branch runs.
        """
        engine = KanbanEngine(board_dir)
        tasks_dir = engine.tasks_dir

        # Create a task file and pin its mtime to a fixed nanosecond value so both
        # batches see the identical candidate_mtime from stat().
        task_file = tasks_dir / "77-stable.md"
        task_file.write_text("---\nid: 77\n---\n", encoding="utf-8")
        pinned_ns = 1_700_000_000_000_000_000  # arbitrary fixed timestamp
        stat = task_file.stat()
        os.utime(task_file, ns=(stat.st_atime_ns, pinned_ns))

        # Two batches pointing to the same file — mtime is identical in both.
        batch1 = {("modified", str(task_file))}
        batch2 = {("modified", str(task_file))}
        collected = await _collect_sse(engine, [batch1, batch2])

        tasks_changed = [e for e in collected if e.get("event") == "tasks-changed"]
        assert len(tasks_changed) == 2, (
            f"Expected 2 tasks-changed events (one per batch); got {len(tasks_changed)}.  Events: {tasks_changed}"
        )

        mtime1 = json.loads(tasks_changed[0]["data"])["mtime"]
        mtime2 = json.loads(tasks_changed[1]["data"])["mtime"]

        assert mtime1 != mtime2, (
            f"Two successive tasks-changed emissions from the same file at the same "
            f"mtime must produce different payload values. Got mtime1={mtime1}, "
            f"mtime2={mtime2}. _next_event_mtime() stateful guard (candidate <= "
            f"previous → previous + 1) was not exercised."
        )
        assert mtime2 == mtime1 + 1, (
            f"When candidate_mtime == previous emitted mtime, _next_event_mtime() must "
            f"return previous + 1. Got mtime1={mtime1}, mtime2={mtime2} "
            f"(expected {mtime1 + 1})."
        )


# ===========================================================================
# AC5 (td:2): Archive directory writes — tasks-changed invalidation signal
# ===========================================================================


class TestFromAC_ArchiveInvalidationSignal:
    """AC5: Writes to the archive directory that affect active-board membership
    must be treated as tasks-changed invalidation signals."""

    @pytest.mark.asyncio
    async def test_archive_path_classified_as_tasks_changed(self, board_dir: Path) -> None:
        """A watch batch containing an archive/*.md path must produce tasks-changed.

        Current _classify_path returns None for archive paths → no event emitted.
        The new implementation must classify archive-dir changes as tasks-changed.
        """
        engine = KanbanEngine(board_dir)
        archive_dir = engine.kanban_dir / "archive"

        # Create an archived task file so stat() succeeds.
        archived_file = archive_dir / "1-done-task.md"
        with open(archived_file, "w", encoding="utf-8") as fh:  # noqa: ASYNC230,PTH123
            fh.write("---\nid: 1\nstatus: done\n---\n")

        batch = {("modified", str(archived_file))}
        collected = await _collect_sse(engine, [batch])

        tasks_changed = [e for e in collected if e.get("event") == "tasks-changed"]
        assert len(tasks_changed) >= 1, (
            "tasks-changed must be emitted for archive/*.md path in the watch batch. "
            "Current _classify_path returns None for archive paths → no event emitted. "
            "AC5 requires archive writes to be treated as tasks-changed signals."
        )

    @pytest.mark.asyncio
    async def test_archive_watch_emits_tasks_changed_not_other_event(self, board_dir: Path) -> None:
        """Archive path changes must be classified as tasks-changed, not a new event
        type.  Frontend only handles known event types; a new event type would be
        silently ignored."""
        engine = KanbanEngine(board_dir)
        archive_dir = engine.kanban_dir / "archive"
        archived_file = archive_dir / "2-archived.md"
        with open(archived_file, "w", encoding="utf-8") as fh:  # noqa: ASYNC230,PTH123
            fh.write("---\nid: 2\n---\n")

        batch = {("modified", str(archived_file))}
        collected = await _collect_sse(engine, [batch])

        tasks_changed = [e for e in collected if e.get("event") == "tasks-changed"]

        # The primary assertion is tasks-changed exists — covered by the previous test.
        # This test verifies the event type is exactly 'tasks-changed', not a new type.
        assert len(tasks_changed) >= 1, (
            "Archive path changes must produce event='tasks-changed'. "
            "Current code emits no event for archive paths — AC5 requires classification "
            "as tasks-changed."
        )

    def test_archived_task_absent_from_get_tasks_after_direct_archive_move(self, two_task_board: Path) -> None:
        """Simulating an archive move (moving task file to archive/) must cause the
        next GET /api/tasks to exclude the archived task.

        This is the AC5 functional test: archive moves that affect active-board
        membership must not leave stale data in GET /api/tasks.
        """
        from fastapi.testclient import TestClient  # noqa: PLC0415

        from owlbear_cockpit.cache import MtimeScanCache  # noqa: PLC0415
        from owlbear_cockpit.deps import get_cache  # noqa: PLC0415
        from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415

        tasks_dir = two_task_board / "tasks"
        archive_dir = two_task_board / "archive"

        eng = KanbanEngine(two_task_board)
        eng.list_tasks()
        local_cache = MtimeScanCache(eng.tasks_dir)

        app.dependency_overrides[get_engine] = lambda: eng
        app.dependency_overrides[get_cache] = lambda: local_cache
        try:
            client = TestClient(app)

            # Prime cache — two tasks.
            resp = client.get("/api/tasks")
            assert resp.status_code == 200
            assert len(resp.json()["tasks"]) == 2, "Precondition: 2 tasks"

            # Move older task (task 1) to archive/ directly.
            task1_file = _task_file(tasks_dir, 1)
            task_id_archived = int(task1_file.name.split("-")[0])
            task1_file.rename(archive_dir / task1_file.name)

            # Next GET must exclude the archived task.
            resp2 = client.get("/api/tasks")
            assert resp2.status_code == 200
            task_ids = {t["id"] for t in resp2.json()["tasks"]}
            assert task_id_archived not in task_ids, (
                f"Task {task_id_archived} was moved to archive/ but GET /api/tasks still "
                "returns it. Cache was not invalidated after archive move — AC5 requires "
                "archive directory changes to be treated as invalidation signals."
            )
        finally:
            app.dependency_overrides.clear()


# ===========================================================================
# AC6 (td:1): Existing activity-changed and decisions-changed behavior intact
# ===========================================================================


class TestFromAC_ExistingEventBehaviorUnchanged:
    """AC6: After the builder extends events.py to handle archive paths and
    fix deleted-path mtime, the existing activity-changed and decisions-changed
    events must still be emitted correctly."""

    @pytest.mark.asyncio
    async def test_activity_changed_still_emitted_after_archive_expansion(self, board_dir: Path) -> None:
        """activity-changed must be emitted AND archive paths must be classified
        as tasks-changed.  This test requires BOTH the old behavior (activity-changed)
        and the new behavior (archive as tasks-changed) simultaneously.

        The test FAILS until the builder implements archive classification (AC5)
        while preserving the activity-changed path (AC6).
        """
        engine = KanbanEngine(board_dir)
        activity_path = engine.kanban_dir / "activity.jsonl"
        with open(activity_path, "w", encoding="utf-8") as fh:  # noqa: ASYNC230,PTH123
            fh.write("[]\n")

        archive_dir = engine.kanban_dir / "archive"
        archived_file = archive_dir / "1-archived.md"
        with open(archived_file, "w", encoding="utf-8") as fh:  # noqa: ASYNC230,PTH123
            fh.write("---\nid: 1\n---\n")

        # Batch contains both an activity write and an archive write.
        batch = {
            ("modified", str(activity_path)),
            ("modified", str(archived_file)),
        }
        collected = await _collect_sse(engine, [batch])

        event_types = {e.get("event") for e in collected}
        assert "activity-changed" in event_types, (
            "activity-changed must still be emitted when the batch also contains an archive path. AC6 regression guard."
        )
        assert "tasks-changed" in event_types, (
            "tasks-changed must be emitted for the archive path in the same batch. "
            "This assertion fails until the builder implements AC5 (archive → "
            "tasks-changed classification)."
        )

    @pytest.mark.asyncio
    async def test_decisions_changed_still_emitted_after_archive_expansion(self, board_dir: Path) -> None:
        """decisions-changed must still be emitted after archive expansion.

        Similar to the activity-changed test: mixed batch with decisions and archive.
        The decisions-changed path must still fire correctly after events.py changes.
        """
        engine = KanbanEngine(board_dir)
        decisions_pending_dir = engine.kanban_dir / "decisions" / "pending"
        os.makedirs(decisions_pending_dir, exist_ok=True)  # noqa: PTH103
        dr_file = decisions_pending_dir / "dr-42.md"
        with open(dr_file, "w", encoding="utf-8") as fh:  # noqa: ASYNC230,PTH123
            fh.write("# DR 42\n")

        archive_dir = engine.kanban_dir / "archive"
        archived_file = archive_dir / "1-done.md"
        with open(archived_file, "w", encoding="utf-8") as fh:  # noqa: ASYNC230,PTH123
            fh.write("---\nid: 1\n---\n")

        batch = {
            ("modified", str(dr_file)),
            ("modified", str(archived_file)),
        }
        collected = await _collect_sse(engine, [batch])

        event_types = {e.get("event") for e in collected}
        assert "decisions-changed" in event_types, (
            "decisions-changed must still be emitted when the batch also contains an "
            "archive path. AC6 regression guard."
        )
        assert "tasks-changed" in event_types, (
            "tasks-changed must be emitted for the archive path. "
            "Fails until the builder implements AC5 archive classification."
        )


# --- merged from tests/test_cockpit_cache_sse_1401.py ---
"""GET-after-mutation cache-invalidation proofs for cockpit edit and release routes (#1401).

AC coverage:
  AC1: GET /api/tasks reflects title changes after POST /api/tasks/{id}/edit
        (field-inspection: locate task by ID, assert title == new value)
  AC2: GET /api/tasks reflects exact tag replacement after POST /api/tasks/{id}/edit
        (field-inspection: exact set equality — no stale or extra tags permitted)
  AC3: GET /api/tasks reflects claimed=False after POST /api/tasks/{id}/release
        (field-inspection: locate task by ID, assert claimed == False)

All tests follow the prime→mutate→re-read pattern:
  1. Prime cache via initial GET /api/tasks.
  2. Perform mutation via the corresponding POST route.
  3. Assert a fresh GET /api/tasks reflects the change.

Assertion strategy: field-inspection on the task summary object (distinct from the
move-route proof in test_cockpit_cache_sse_1346.py which uses filter-exclusion).

Proofs depend on:
  serve/cockpit/src/owlbear_cockpit/cache.py  — MtimeScanCache passive invalidation
  serve/cockpit/src/owlbear_cockpit/routes/read.py — cache.has_changed_at check
"""


from pathlib import Path

from owlbear_kanban import KanbanEngine


# ---------------------------------------------------------------------------
# Board config & helpers (self-contained, no shared fixtures from other modules)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# AC1 / AC2 / AC3 proof tests
# ---------------------------------------------------------------------------


class TestFromAC_EditReleaseCacheInvalidation:
    """GET-after-mutation cache invalidation proofs for edit and release routes.

    All three tests use the prime→mutate→re-read pattern with field-inspection:
    locate the mutated task by ID in the GET /api/tasks response, then assert
    the relevant field equals the post-mutation value.
    """

    def test_get_tasks_reflects_title_after_edit_route(self, tmp_path: Path) -> None:
        """AC1: GET /api/tasks reflects title changes after POST /api/tasks/{id}/edit.

        After editing a task's title via the cockpit edit route, a subsequent
        GET /api/tasks must return the updated title, not the cached pre-edit value.

        Fails if cache.has_changed_at() returns False after edit rewrites the task
        file (i.e. MtimeScanCache does not detect the mtime change).
        """
        from fastapi.testclient import TestClient  # noqa: PLC0415

        from owlbear_cockpit.cache import MtimeScanCache  # noqa: PLC0415
        from owlbear_cockpit.deps import get_cache  # noqa: PLC0415
        from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415

        kanban_dir = _make_board(tmp_path / "board_edit_title")
        seed = KanbanEngine(kanban_dir)
        seed.create_task("Original title", status="todo", priority="important")
        seed.list_tasks()

        eng = KanbanEngine(kanban_dir)
        eng.list_tasks()
        local_cache = MtimeScanCache(eng.tasks_dir)

        app.dependency_overrides[get_engine] = lambda: eng
        app.dependency_overrides[get_cache] = lambda: local_cache
        try:
            client = TestClient(app)

            # Prime cache with the original task list.
            prime_resp = client.get("/api/tasks")
            assert prime_resp.status_code == 200
            primed = {t["id"]: t for t in prime_resp.json()["tasks"]}
            assert 1 in primed, "Precondition: task 1 must be present"
            assert primed[1]["title"] == "Original title", (
                "Precondition: task 1 must carry the original title before mutation"
            )

            # Mutate: edit title via the cockpit edit route.
            task = eng.show_task("1")
            edit_resp = client.post(
                "/api/tasks/1/edit",
                json={"updated": task.updated, "title": "Mutated title"},
            )
            assert edit_resp.status_code == 200, (
                f"POST /api/tasks/1/edit returned {edit_resp.status_code}: {edit_resp.json()}"
            )

            # Re-read: GET /api/tasks must reflect the mutated title.
            resp_after = client.get("/api/tasks")
            assert resp_after.status_code == 200
            after = {t["id"]: t for t in resp_after.json()["tasks"]}
            assert 1 in after, "Task 1 must still be present after title edit"
            assert after[1]["title"] == "Mutated title", (
                "Task 1 title was updated via POST /api/tasks/1/edit but "
                "GET /api/tasks still returns the pre-edit value. "
                "Cache was not invalidated after the edit route rewrote the task file."
            )
        finally:
            app.dependency_overrides.clear()

    def test_get_tasks_reflects_tags_after_edit_route(self, tmp_path: Path) -> None:
        """AC2: GET /api/tasks reflects exact tag replacement after POST /api/tasks/{id}/edit.

        After replacing tags via the cockpit edit route, a subsequent GET /api/tasks
        must return the new tag list with exact set equality — no stale, removed, or
        extra tags permitted.

        Fails if:
        - Cache is not invalidated (stale tag list returned), OR
        - The tag set differs from the exact replacement list for any reason.
        """
        from fastapi.testclient import TestClient  # noqa: PLC0415

        from owlbear_cockpit.cache import MtimeScanCache  # noqa: PLC0415
        from owlbear_cockpit.deps import get_cache  # noqa: PLC0415
        from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415

        kanban_dir = _make_board(tmp_path / "board_edit_tags")
        seed = KanbanEngine(kanban_dir)
        seed.create_task("Tag test task", status="todo", priority="important")
        seed.list_tasks()
        # Set up known initial tags so we can assert the removed tag is absent.
        seed.edit_task("1", add_tags=["old-tag", "keep-tag"])

        eng = KanbanEngine(kanban_dir)
        eng.list_tasks()
        local_cache = MtimeScanCache(eng.tasks_dir)

        app.dependency_overrides[get_engine] = lambda: eng
        app.dependency_overrides[get_cache] = lambda: local_cache
        try:
            client = TestClient(app)

            # Prime cache with the initial tag state.
            prime_resp = client.get("/api/tasks")
            assert prime_resp.status_code == 200
            primed = {t["id"]: t for t in prime_resp.json()["tasks"]}
            assert 1 in primed, "Precondition: task 1 must be present"
            assert "old-tag" in primed[1]["tags"], "Precondition: old-tag must be in task 1 before mutation"

            # Mutate: replace tags via the cockpit edit route (full-replacement semantics).
            task = eng.show_task("1")
            edit_resp = client.post(
                "/api/tasks/1/edit",
                json={"updated": task.updated, "tags": ["new-tag", "another-tag"]},
            )
            assert edit_resp.status_code == 200, (
                f"POST /api/tasks/1/edit (tags) returned {edit_resp.status_code}: {edit_resp.json()}"
            )

            # Re-read: GET /api/tasks must reflect the exact replacement tag list.
            resp_after = client.get("/api/tasks")
            assert resp_after.status_code == 200
            after = {t["id"]: t for t in resp_after.json()["tasks"]}
            assert 1 in after, "Task 1 must still be present after tag edit"
            actual_tags = set(after[1]["tags"])
            # Exact set equality — no stale, removed, or extra tags permitted.
            assert actual_tags == {"new-tag", "another-tag"}, (
                f"GET /api/tasks returned tags {actual_tags!r} after tag replacement "
                "via POST /api/tasks/1/edit — expected exactly {{'new-tag', 'another-tag'}}. "
                "Either the cache was not invalidated (stale tags returned) or the edit "
                "route does not apply full-replacement semantics (extra or removed tags remain)."
            )
        finally:
            app.dependency_overrides.clear()

    def test_get_tasks_reflects_claimed_false_after_release_route(self, tmp_path: Path) -> None:
        """AC3: GET /api/tasks reflects claimed=False after POST /api/tasks/{id}/release.

        After releasing a claimed task via the cockpit release route, a subsequent
        GET /api/tasks must return claimed=False for that task.

        Fails if cache.has_changed_at() returns False after release rewrites the
        task file (i.e. MtimeScanCache does not detect the mtime change), causing
        GET /api/tasks to return the stale claimed=True value from cache.
        """
        from fastapi.testclient import TestClient  # noqa: PLC0415

        from owlbear_cockpit.cache import MtimeScanCache  # noqa: PLC0415
        from owlbear_cockpit.deps import get_cache  # noqa: PLC0415
        from owlbear_cockpit.main import app, get_engine  # noqa: PLC0415

        kanban_dir = _make_board(tmp_path / "board_release")
        seed = KanbanEngine(kanban_dir)
        seed.create_task("Claimed task", status="in-progress", priority="important")
        seed.list_tasks()
        seed.claim_task("1")

        eng = KanbanEngine(kanban_dir)
        eng.list_tasks()
        local_cache = MtimeScanCache(eng.tasks_dir)

        app.dependency_overrides[get_engine] = lambda: eng
        app.dependency_overrides[get_cache] = lambda: local_cache
        try:
            client = TestClient(app)

            # Prime cache with task 1 in claimed=True state.
            prime_resp = client.get("/api/tasks")
            assert prime_resp.status_code == 200
            primed = {t["id"]: t for t in prime_resp.json()["tasks"]}
            assert 1 in primed, "Precondition: task 1 must be present"
            assert primed[1]["claimed"] is True, "Precondition: task 1 must be claimed before release"

            # Mutate: release the task via the cockpit release route.
            task = eng.show_task("1")
            release_resp = client.post(
                "/api/tasks/1/release",
                json={"updated": task.updated},
            )
            assert release_resp.status_code == 200, (
                f"POST /api/tasks/1/release returned {release_resp.status_code}: {release_resp.json()}"
            )

            # Re-read: GET /api/tasks must reflect claimed=False for the released task.
            resp_after = client.get("/api/tasks")
            assert resp_after.status_code == 200
            after = {t["id"]: t for t in resp_after.json()["tasks"]}
            assert 1 in after, "Task 1 must still be present after release"
            assert after[1]["claimed"] is False, (
                "Task 1 was released via POST /api/tasks/1/release but "
                "GET /api/tasks still shows claimed=True. "
                "Cache was not invalidated after the release route rewrote the task file."
            )
        finally:
            app.dependency_overrides.clear()
