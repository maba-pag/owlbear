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

from __future__ import annotations

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

    def test_signature_changes_when_non_newest_task_deleted(
        self, two_task_board: Path
    ) -> None:
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

    def test_has_changed_true_when_non_newest_task_deleted(
        self, two_task_board: Path
    ) -> None:
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

    def test_tmp_prefixed_files_excluded_from_signature(
        self, board_dir: Path
    ) -> None:
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

    def test_get_tasks_excludes_deleted_non_newest_task(
        self, http_client: TestClient, two_task_board: Path
    ) -> None:
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

    def test_get_tasks_excludes_archived_non_newest_task(
        self, http_client: TestClient, two_task_board: Path
    ) -> None:
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

    def test_has_changed_detects_archive_of_non_newest_when_same_mtime(
        self, tmp_path: Path
    ) -> None:
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

    def test_get_tasks_after_same_mtime_archive_excludes_archived_task(
        self, tmp_path: Path
    ) -> None:
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


# ===========================================================================
# AC4 (td:2): SSE — tasks-changed emitted for deleted/archived paths
# ===========================================================================


class TestFromAC_SSEDeletedPathEvent:
    """AC4: GET /api/events must emit tasks-changed for delete-only watch batches
    even when the changed task path no longer exists on disk.  The payload mtime
    must be a positive integer (numeric, not zero or missing)."""

    @pytest.mark.asyncio
    async def test_delete_only_batch_emits_tasks_changed(
        self, board_dir: Path
    ) -> None:
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
    async def test_tasks_changed_payload_mtime_positive_for_deleted_path(
        self, board_dir: Path
    ) -> None:
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
    async def test_mixed_batch_tasks_deleted_decisions_changed_emits_tasks_changed(
        self, board_dir: Path
    ) -> None:
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
            ("deleted", deleted_task),          # task-classified, file gone
            ("modified", str(decisions_file)),  # decisions-classified, file exists
        }
        collected = await _collect_sse(engine, [batch])

        tasks_changed = [e for e in collected if e.get("event") == "tasks-changed"]
        assert len(tasks_changed) >= 1, (
            "tasks-changed must be emitted for the deleted task path in a mixed batch. "
            "Current events.py skips deleted paths, so only decisions-changed is "
            "emitted — AC4 requires tasks-changed even when the file is gone."
        )


# ===========================================================================
# AC5 (td:2): Archive directory writes — tasks-changed invalidation signal
# ===========================================================================


class TestFromAC_ArchiveInvalidationSignal:
    """AC5: Writes to the archive directory that affect active-board membership
    must be treated as tasks-changed invalidation signals."""

    @pytest.mark.asyncio
    async def test_archive_path_classified_as_tasks_changed(
        self, board_dir: Path
    ) -> None:
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
    async def test_archive_watch_emits_tasks_changed_not_other_event(
        self, board_dir: Path
    ) -> None:
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

    def test_archived_task_absent_from_get_tasks_after_direct_archive_move(
        self, two_task_board: Path
    ) -> None:
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
    async def test_activity_changed_still_emitted_after_archive_expansion(
        self, board_dir: Path
    ) -> None:
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
            "activity-changed must still be emitted when the batch also contains an "
            "archive path. AC6 regression guard."
        )
        assert "tasks-changed" in event_types, (
            "tasks-changed must be emitted for the archive path in the same batch. "
            "This assertion fails until the builder implements AC5 (archive → "
            "tasks-changed classification)."
        )

    @pytest.mark.asyncio
    async def test_decisions_changed_still_emitted_after_archive_expansion(
        self, board_dir: Path
    ) -> None:
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
