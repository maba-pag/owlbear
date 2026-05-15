"""Tests for task #943: extend mtime cache to show_task() and _find_task_path().

AC coverage:
  1. show_task() checks _id_to_filename → _task_cache before glob+read_task()
  2. show_task() validates freshness via stat(); re-reads on mtime change; evicts + glob
     fallback when file missing
  3. _find_task_path() uses _id_to_filename for O(1) lookup; glob fallback on miss or
     when search_dir != self._tasks_dir
  4. _id_to_filename rebuilt in list_tasks() on non-archived calls only
  5. refresh_config() clears _id_to_filename alongside existing cache clears
  6. int(task_id) conversion; non-integer task_id falls through to glob (no ValueError)
  7. Write ops are NOT required to update caches (stale handled reactively by stat)
  8. _id_to_filename: dict[int, str] initialized as empty dict in __init__

All tests FAIL in RED phase — _id_to_filename not yet implemented.
"""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import patch

import pytest

from owlbear_kanban import KanbanEngine

# ---------------------------------------------------------------------------
# Board helpers  (mirrors test_mtime_cache_942.py conventions)
# ---------------------------------------------------------------------------

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
next_id: {next_id}
archive_dir: archive
activity_log: false
"""


def _make_board(base_dir: Path, n_tasks: int = 3) -> Path:
    """Create a minimal kanban board with *n_tasks* tasks. Returns kanban_dir."""
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(
        _CONFIG_YAML.format(next_id=n_tasks + 1),
        encoding="utf-8",
    )
    tasks_dir = kanban_dir / "tasks"
    tasks_dir.mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    for i in range(1, n_tasks + 1):
        _write_task_file(tasks_dir, i)
    return kanban_dir


def _write_task_file(tasks_dir: Path, task_id: int, status: str = "todo") -> Path:
    """Write a synthetic task file and return its path."""
    content = (
        "---\n"
        f"id: {task_id}\n"
        f'title: "Task {task_id}"\n'
        f"status: {status}\n"
        "priority: important\n"
        "created: 2026-04-17T19:56:44.165954+00:00\n"
        "updated: 2026-04-17T20:02:28.358032+00:00\n"
        "tags: []\n"
        "parent:\n"
        "depends_on: []\n"
        "blocked: false\n"
        "block_reason:\n"
        "claimed_by:\n"
        "claimed_at:\n"
        "---\n"
        "Task body.\n"
    )
    path = tasks_dir / f"{task_id}-task-{task_id}.md"
    path.write_text(content, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def board(tmp_path: Path) -> Path:
    """3-task kanban board. Returns kanban_dir."""
    return _make_board(tmp_path)


@pytest.fixture
def engine(board: Path) -> KanbanEngine:
    """KanbanEngine for the board fixture (cache cold)."""
    return KanbanEngine(board, activity_log=False)


@pytest.fixture
def warm_engine(board: Path) -> KanbanEngine:
    """KanbanEngine whose cache is pre-warmed by list_tasks()."""
    eng = KanbanEngine(board, activity_log=False)
    eng.list_tasks()  # populates _task_cache and rebuilds _id_to_filename
    return eng


# ---------------------------------------------------------------------------
# TestFromAC_IdToFilenameCache
# ---------------------------------------------------------------------------


class TestFromAC_IdToFilenameCache:
    """Verifies _id_to_filename cache behaviour for show_task() and _find_task_path()."""

    # ------------------------------------------------------------------ AC 8
    # _id_to_filename initialized as empty dict

    def test_init_creates_id_to_filename_as_empty_dict(
        self, engine: KanbanEngine
    ) -> None:
        """_id_to_filename must exist and be an empty dict immediately after __init__."""
        assert hasattr(engine, "_id_to_filename"), (
            "_id_to_filename attribute missing from __init__"
        )
        assert engine._id_to_filename == {}

    def test_id_to_filename_is_dict_type(self, engine: KanbanEngine) -> None:
        """_id_to_filename must be a plain dict, not a defaultdict or other mapping."""
        assert isinstance(engine._id_to_filename, dict)

    # ------------------------------------------------------------------ AC 4
    # list_tasks() rebuilds _id_to_filename on non-archived calls only

    def test_list_tasks_populates_id_to_filename(self, engine: KanbanEngine) -> None:
        """list_tasks() must populate _id_to_filename with int→filename mappings."""
        engine.list_tasks()
        assert engine._id_to_filename, (
            "_id_to_filename must be non-empty after list_tasks()"
        )

    def test_id_to_filename_keys_are_ints(self, engine: KanbanEngine) -> None:
        """Keys in _id_to_filename must be integers (task IDs)."""
        engine.list_tasks()
        for key in engine._id_to_filename:
            assert isinstance(key, int), (
                f"key {key!r} must be int, got {type(key).__name__}"
            )

    def test_id_to_filename_values_are_strings(self, engine: KanbanEngine) -> None:
        """Values in _id_to_filename must be filename strings (e.g. '1-task-1.md')."""
        engine.list_tasks()
        for filename in engine._id_to_filename.values():
            assert isinstance(filename, str), (
                f"filename {filename!r} must be str, got {type(filename).__name__}"
            )
            assert filename.endswith(".md"), f"filename {filename!r} must end with .md"

    def test_id_to_filename_covers_all_tasks(
        self, engine: KanbanEngine, board: Path
    ) -> None:
        """_id_to_filename must contain one entry per task file after list_tasks()."""
        tasks_dir = board / "tasks"
        md_count = sum(1 for _ in tasks_dir.glob("*.md"))
        engine.list_tasks()
        assert len(engine._id_to_filename) == md_count

    def test_archived_list_tasks_does_not_rebuild_id_to_filename(
        self, board: Path
    ) -> None:
        """list_tasks(archived=True) must NOT rebuild _id_to_filename — it uses _archive_cache."""
        archive_dir = board / "archive"
        _write_task_file(archive_dir, 99)
        eng = KanbanEngine(board, activity_log=False)
        eng.list_tasks(archived=True)
        # _id_to_filename must remain empty; archived tasks are not indexed there
        assert eng._id_to_filename == {}, (
            "_id_to_filename must remain empty after list_tasks(archived=True)"
        )

    # ------------------------------------------------------------------ AC 5
    # refresh_config() clears _id_to_filename

    def test_refresh_config_clears_id_to_filename(
        self, warm_engine: KanbanEngine
    ) -> None:
        """refresh_config() must reset _id_to_filename to empty dict."""
        assert warm_engine._id_to_filename, (
            "pre-condition: _id_to_filename must be populated"
        )
        warm_engine.refresh_config()
        assert warm_engine._id_to_filename == {}, (
            "_id_to_filename must be empty dict after refresh_config()"
        )

    def test_refresh_config_id_to_filename_reachable_after_re_warm(
        self, warm_engine: KanbanEngine
    ) -> None:
        """After refresh_config() + list_tasks(), _id_to_filename is rebuilt correctly."""
        warm_engine.refresh_config()
        warm_engine.list_tasks()
        assert warm_engine._id_to_filename, (
            "_id_to_filename must be rebuilt after list_tasks() post-refresh"
        )

    # ------------------------------------------------------------------ AC 1
    # show_task() cache hit — no glob, no read_task()

    def test_show_task_warm_cache_does_not_call_glob(
        self, warm_engine: KanbanEngine
    ) -> None:
        """show_task() with warm _id_to_filename must NOT call Path.glob()."""
        task_id = next(iter(warm_engine._id_to_filename))  # first cached id
        with patch.object(type(warm_engine._tasks_dir), "glob") as mock_glob:
            warm_engine.show_task(str(task_id))
            mock_glob.assert_not_called()

    def test_show_task_warm_cache_does_not_call_read_task(
        self, warm_engine: KanbanEngine
    ) -> None:
        """show_task() with warm cache and unchanged file must NOT call read_task()."""
        task_id = next(iter(warm_engine._id_to_filename))
        with patch("owlbear_kanban.engine.read_task") as mock_read:
            warm_engine.show_task(str(task_id))
            mock_read.assert_not_called()

    def test_show_task_warm_cache_returns_correct_task(
        self, warm_engine: KanbanEngine
    ) -> None:
        """show_task() with warm cache must return a Task with the requested ID."""
        task_id = next(iter(warm_engine._id_to_filename))
        task = warm_engine.show_task(str(task_id))
        assert task.id == task_id

    # ------------------------------------------------------------------ AC 2
    # show_task() stat validation — stale mtime triggers re-read

    def test_show_task_stale_mtime_triggers_reread(self, board: Path) -> None:
        """show_task() must re-read file when mtime has changed since cache was built."""
        tasks_dir = board / "tasks"
        eng = KanbanEngine(board, activity_log=False)
        eng.list_tasks()  # warm cache

        task_id = next(iter(eng._id_to_filename))

        # Modify the file to change mtime
        time.sleep(0.01)
        _write_task_file(tasks_dir, task_id, status="in-progress")

        task = eng.show_task(str(task_id))
        assert task.status == "in-progress", (
            "show_task() must return updated content after mtime change"
        )

    def test_show_task_stale_mtime_updates_cache_entry(self, board: Path) -> None:
        """After a stale-mtime re-read, _task_cache must contain the new mtime and task."""
        tasks_dir = board / "tasks"
        eng = KanbanEngine(board, activity_log=False)
        eng.list_tasks()

        task_id = next(iter(eng._id_to_filename))
        filename = eng._id_to_filename[task_id]
        old_mtime_ns = eng._task_cache[filename][0]

        time.sleep(0.01)
        _write_task_file(tasks_dir, task_id, status="in-progress")

        eng.show_task(str(task_id))

        new_mtime_ns = eng._task_cache[filename][0]
        assert new_mtime_ns != old_mtime_ns, (
            "cache mtime_ns must be updated after re-read"
        )
        assert eng._task_cache[filename][1].status == "in-progress"

    # ------------------------------------------------------------------ AC 2
    # show_task() file missing — evict both caches + glob fallback

    def test_show_task_missing_file_evicts_task_cache(self, board: Path) -> None:
        """When stat() reveals file is gone, the entry must be evicted from _task_cache."""
        tasks_dir = board / "tasks"
        eng = KanbanEngine(board, activity_log=False)
        eng.list_tasks()

        task_id = next(iter(eng._id_to_filename))
        filename = eng._id_to_filename[task_id]
        (tasks_dir / filename).unlink()  # delete the file

        with pytest.raises(FileNotFoundError):
            eng.show_task(str(task_id))

        assert filename not in eng._task_cache, (
            "deleted file must be evicted from _task_cache"
        )

    def test_show_task_missing_file_evicts_id_to_filename(self, board: Path) -> None:
        """When the file is gone, the entry must be evicted from _id_to_filename."""
        tasks_dir = board / "tasks"
        eng = KanbanEngine(board, activity_log=False)
        eng.list_tasks()

        task_id = next(iter(eng._id_to_filename))
        filename = eng._id_to_filename[task_id]
        (tasks_dir / filename).unlink()

        with pytest.raises(FileNotFoundError):
            eng.show_task(str(task_id))

        assert task_id not in eng._id_to_filename, (
            "deleted file must be evicted from _id_to_filename"
        )

    def test_show_task_cold_cache_falls_back_to_glob(
        self, engine: KanbanEngine
    ) -> None:
        """show_task() with cold cache (_id_to_filename empty) must fall back to glob."""
        assert engine._id_to_filename == {}, "pre-condition: cache must be cold"
        # Should succeed by falling back to glob
        task = engine.show_task("1")
        assert task.id == 1

    # ------------------------------------------------------------------ AC 6
    # int(task_id) conversion; non-integer falls through to glob (no ValueError)

    def test_show_task_non_integer_id_does_not_raise_value_error(
        self, warm_engine: KanbanEngine
    ) -> None:
        """show_task() with non-numeric task_id must not propagate ValueError.

        Pre-condition: cache is warm (_id_to_filename populated). The new code calls
        int(task_id) which raises ValueError; that must be caught and fall through to glob.
        """
        # Verify cache is warm — this assertion fails in RED phase
        assert warm_engine._id_to_filename, (
            "pre-condition: _id_to_filename must be populated for this test"
        )
        # A non-numeric id cannot match any integer key — must fall through to glob fallback.
        # Glob will also fail to find it, so FileNotFoundError is expected, NOT ValueError.
        with pytest.raises(FileNotFoundError):
            warm_engine.show_task("not-a-number")

    def test_find_task_path_non_integer_id_does_not_raise_value_error(
        self, warm_engine: KanbanEngine
    ) -> None:
        """_find_task_path() with non-numeric task_id must not propagate ValueError.

        Pre-condition: cache is warm (_id_to_filename populated). The new code calls
        int(task_id) which raises ValueError; that must be caught and fall through to glob.
        """
        # Verify cache is warm — this assertion fails in RED phase
        assert warm_engine._id_to_filename, (
            "pre-condition: _id_to_filename must be populated for this test"
        )
        with pytest.raises(FileNotFoundError):
            warm_engine._find_task_path("not-a-number", warm_engine._tasks_dir)

    # ------------------------------------------------------------------ AC 3
    # _find_task_path() O(1) cache hit

    def test_find_task_path_warm_cache_does_not_call_glob(
        self, warm_engine: KanbanEngine
    ) -> None:
        """_find_task_path() with warm _id_to_filename must NOT call glob()."""
        task_id = str(next(iter(warm_engine._id_to_filename)))
        with patch.object(type(warm_engine._tasks_dir), "glob") as mock_glob:
            warm_engine._find_task_path(task_id, warm_engine._tasks_dir)
            mock_glob.assert_not_called()

    def test_find_task_path_warm_cache_returns_correct_path(
        self, warm_engine: KanbanEngine, board: Path
    ) -> None:
        """_find_task_path() with warm cache must return the correct Path."""
        task_id = next(iter(warm_engine._id_to_filename))
        filename = warm_engine._id_to_filename[task_id]
        expected_path = board / "tasks" / filename
        result = warm_engine._find_task_path(str(task_id), warm_engine._tasks_dir)
        assert result == expected_path

    def test_find_task_path_cold_cache_falls_back_to_glob(
        self, engine: KanbanEngine
    ) -> None:
        """_find_task_path() with cold cache must fall back to glob and find the file."""
        assert engine._id_to_filename == {}, "pre-condition: cache must be cold"
        result = engine._find_task_path("1", engine._tasks_dir)
        assert result.name.startswith("1-")

    def test_find_task_path_search_dir_not_tasks_dir_uses_glob(
        self, warm_engine: KanbanEngine, board: Path
    ) -> None:
        """_find_task_path() must use glob when search_dir != _tasks_dir."""
        other_dir = board / "archive"
        _write_task_file(other_dir, 1)  # write a matching file to the other dir

        task_id = str(next(iter(warm_engine._id_to_filename)))
        with patch.object(type(other_dir), "glob", wraps=other_dir.glob) as mock_glob:
            warm_engine._find_task_path(task_id, other_dir)
            mock_glob.assert_called_once()

    def test_find_task_path_post_create_warm_miss_falls_back_to_glob(
        self, warm_engine: KanbanEngine
    ) -> None:
        """_find_task_path() must fall back to glob for a task created after last list_tasks()."""
        new_task = warm_engine.create_task("Brand new task")
        # _id_to_filename is NOT updated by create_task (AC 7 — lazy invalidation)
        assert new_task.id not in warm_engine._id_to_filename, (
            "pre-condition: newly created task must NOT be in _id_to_filename"
        )
        # But _find_task_path must still succeed via glob fallback and return the correct task
        result = warm_engine._find_task_path(str(new_task.id), warm_engine._tasks_dir)
        assert result.name.startswith(str(new_task.id) + "-"), (
            f"expected path for task {new_task.id}, got: {result.name}"
        )

    # ------------------------------------------------------------------ AC 7
    # Write ops do NOT update caches (lazy invalidation)

    def test_create_task_does_not_update_id_to_filename(
        self, warm_engine: KanbanEngine
    ) -> None:
        """create_task() must NOT add the new task's ID to _id_to_filename."""
        before_ids = set(warm_engine._id_to_filename.keys())
        new_task = warm_engine.create_task("Lazy invalidation test")
        after_ids = set(warm_engine._id_to_filename.keys())
        assert new_task.id not in after_ids, (
            "create_task() must not proactively update _id_to_filename"
        )
        assert after_ids == before_ids, (
            "_id_to_filename must be unchanged after create_task()"
        )


# --- merged from serve/kanban/tests/test_idtofilename_cache_refresh.py ---
class TestFromAC_IdToFilenameCache_944:
    """Edge case and interaction tests for the _id_to_filename cache (task #944).

    Complements test_idtofilename_cache_943.py with scenarios not covered there.
    """

    # ------------------------------------------------------------------ AC 1
    # __init__ adds _id_to_filename: dict[int, str] = {}

    def test_init_id_to_filename_exists_before_any_list_tasks(
        self, engine: KanbanEngine
    ) -> None:
        """_id_to_filename must be present as empty dict immediately on construction.

        Verifies the attribute is declared in __init__, not lazily on first list_tasks().
        """
        assert hasattr(engine, "_id_to_filename"), (
            "_id_to_filename missing before list_tasks()"
        )
        assert engine._id_to_filename == {}
        assert type(engine._id_to_filename) is dict

    # ------------------------------------------------------------------ AC 2
    # list_tasks() rebuilds _id_to_filename from _task_cache after scandir loop

    def test_list_tasks_with_status_filter_rebuilds_full_id_to_filename(
        self, board: Path
    ) -> None:
        """list_tasks(status='done') must rebuild _id_to_filename for ALL tasks, not just filtered.

        _id_to_filename is rebuilt from _task_cache (full scan), then filters are applied
        to the returned list separately. Both sets of tasks must appear in the index.
        """
        tasks_dir = board / "tasks"
        # Add a done-status task alongside the existing todo tasks
        _write_task_file(tasks_dir, 10, status="done")
        _write_task_file(tasks_dir, 11, status="todo")

        # Reload engine so it discovers all 5 files
        eng = KanbanEngine(board, activity_log=False)
        result = eng.list_tasks(status="done")

        assert len(result) == 1, "filter must return only done tasks"
        # Both done and todo task IDs must be in _id_to_filename
        assert 10 in eng._id_to_filename, (
            "filtered-out task 10 (done) must still be in _id_to_filename"
        )
        assert 11 in eng._id_to_filename, (
            "non-filtered task 11 (todo) must be in _id_to_filename"
        )
        # All original tasks (1-3) must be there too
        for tid in (1, 2, 3):
            assert tid in eng._id_to_filename, f"task {tid} must be in _id_to_filename"

    def test_list_tasks_second_call_removes_deleted_task_from_id_to_filename(
        self, board: Path
    ) -> None:
        """A task deleted between list_tasks() calls must be absent from _id_to_filename.

        The scandir loop prunes stale cache entries; _id_to_filename is rebuilt from
        the pruned _task_cache, so deleted tasks must no longer appear.
        """
        tasks_dir = board / "tasks"
        eng = KanbanEngine(board, activity_log=False)
        eng.list_tasks()  # warm cache with tasks 1-3

        # Confirm task 2 is indexed
        assert 2 in eng._id_to_filename, (
            "pre-condition: task 2 must be in _id_to_filename"
        )

        # Delete task 2 from disk
        (tasks_dir / eng._id_to_filename[2]).unlink()

        # Second list_tasks() must detect the deletion and rebuild _id_to_filename
        eng.list_tasks()
        assert 2 not in eng._id_to_filename, (
            "_id_to_filename must not contain deleted task 2 after second list_tasks()"
        )

    def test_list_tasks_second_call_reflects_new_task_in_id_to_filename(
        self, board: Path
    ) -> None:
        """A task added between list_tasks() calls must appear in _id_to_filename after re-scan.

        The scandir loop picks up new files; _id_to_filename is rebuilt from the updated cache.
        """
        tasks_dir = board / "tasks"
        eng = KanbanEngine(board, activity_log=False)
        eng.list_tasks()  # warm cache with tasks 1-3

        # Manually write a new file (bypassing create_task to avoid cache updates)
        _write_task_file(tasks_dir, 99)

        eng.list_tasks()  # re-scan
        assert 99 in eng._id_to_filename, (
            "_id_to_filename must include task 99 after second list_tasks()"
        )

    def test_list_tasks_archived_does_not_corrupt_id_to_filename(
        self, board: Path
    ) -> None:
        """list_tasks(archived=True) must leave _id_to_filename unchanged.

        Prior list_tasks() call populates _id_to_filename; archived=True call must
        not clear or modify it.
        """
        archive_dir = board / "archive"
        eng = KanbanEngine(board, activity_log=False)
        eng.list_tasks()  # populate _id_to_filename with tasks 1-3
        pre_index = dict(eng._id_to_filename)  # snapshot

        # Add an archived task and call list_tasks(archived=True)
        _write_task_file(archive_dir, 50)
        eng.list_tasks(archived=True)

        assert eng._id_to_filename == pre_index, (
            "list_tasks(archived=True) must not modify _id_to_filename"
        )

    # ------------------------------------------------------------------ AC 3
    # refresh_config() clears _id_to_filename

    def test_refresh_config_clears_id_to_filename_to_empty_dict(
        self, warm_engine: KanbanEngine
    ) -> None:
        """refresh_config() must reset _id_to_filename to an empty dict (not None, not stale)."""
        assert warm_engine._id_to_filename, (
            "pre-condition: _id_to_filename must be populated"
        )
        warm_engine.refresh_config()

        assert warm_engine._id_to_filename == {}
        assert type(warm_engine._id_to_filename) is dict, (
            "_id_to_filename must be a dict after refresh_config(), not None"
        )

    # ------------------------------------------------------------------ AC 4
    # show_task() checks _id_to_filename → _task_cache → stat validate → fallback to glob

    def test_show_task_warm_id_cache_cold_task_cache_does_not_call_glob(
        self, warm_engine: KanbanEngine
    ) -> None:
        """When _id_to_filename is warm but _task_cache is cold, show_task() uses stat→read_task.

        The _id_to_filename provides the filename; stat validates freshness; read_task loads
        the file directly. glob must NOT be called in this path.
        """
        task_id = next(iter(warm_engine._id_to_filename))
        # Deliberately clear _task_cache to test the _id_to_filename-only path
        warm_engine._task_cache.clear()

        with patch.object(type(warm_engine._tasks_dir), "glob") as mock_glob:
            result = warm_engine.show_task(str(task_id))
            mock_glob.assert_not_called()

        assert result.id == task_id

    def test_show_task_warm_id_cache_cold_task_cache_calls_read_task(
        self, warm_engine: KanbanEngine
    ) -> None:
        """When _id_to_filename warm and _task_cache cold, show_task() must call read_task()."""
        task_id = next(iter(warm_engine._id_to_filename))
        warm_engine._task_cache.clear()

        with patch(
            "owlbear_kanban.engine.read_task",
            wraps=__import__("owlbear_kanban.engine", fromlist=["read_task"]).read_task,
        ) as mock_read:
            warm_engine.show_task(str(task_id))
            mock_read.assert_called_once()

    def test_show_task_warm_id_cache_cold_task_cache_repopulates_task_cache(
        self, warm_engine: KanbanEngine
    ) -> None:
        """After a cache-miss show_task(), _task_cache must be repopulated with the new entry."""
        task_id = next(iter(warm_engine._id_to_filename))
        filename = warm_engine._id_to_filename[task_id]
        warm_engine._task_cache.clear()

        warm_engine.show_task(str(task_id))

        assert filename in warm_engine._task_cache, (
            "_task_cache must be repopulated after show_task() cache miss"
        )
        cached_mtime, cached_task = warm_engine._task_cache[filename]
        assert cached_task.id == task_id
        assert isinstance(cached_mtime, int)

    def test_show_task_id_cache_cold_falls_back_to_glob_and_succeeds(
        self, engine: KanbanEngine
    ) -> None:
        """show_task() on a cold engine (no cache) must find the task via glob."""
        assert engine._id_to_filename == {}, "pre-condition: id cache must be cold"
        task = engine.show_task("2")
        assert task.id == 2

    def test_show_task_unknown_id_raises_file_not_found(
        self, warm_engine: KanbanEngine
    ) -> None:
        """show_task() for a non-existent ID must raise FileNotFoundError (not KeyError)."""
        with pytest.raises(FileNotFoundError):
            warm_engine.show_task("9999")

    def test_show_task_non_integer_id_raises_file_not_found_not_value_error(
        self, warm_engine: KanbanEngine
    ) -> None:
        """show_task() with non-numeric ID must raise FileNotFoundError, not ValueError.

        int(task_id) ValueError must be caught internally; the public contract raises
        FileNotFoundError for missing tasks and never propagates ValueError.
        """
        assert warm_engine._id_to_filename, "pre-condition: id cache must be warm"
        with pytest.raises(FileNotFoundError):
            warm_engine.show_task("not-a-number")

    # ------------------------------------------------------------------ AC 5
    # show_task() evicts stale entries on stat() FileNotFoundError

    def test_show_task_stale_id_entry_raises_file_not_found(self, board: Path) -> None:
        """show_task() must raise FileNotFoundError when the indexed file no longer exists.

        The eviction must happen before the error is raised — ghost entry is removed
        from both caches in the same operation.
        """
        tasks_dir = board / "tasks"
        eng = KanbanEngine(board, activity_log=False)
        eng.list_tasks()

        task_id = next(iter(eng._id_to_filename))
        filename = eng._id_to_filename[task_id]
        (tasks_dir / filename).unlink()

        with pytest.raises(FileNotFoundError):
            eng.show_task(str(task_id))

    def test_show_task_eviction_leaves_other_tasks_intact(self, board: Path) -> None:
        """Evicting one ghost entry must not disturb other entries in _id_to_filename."""
        tasks_dir = board / "tasks"
        eng = KanbanEngine(board, activity_log=False)
        eng.list_tasks()
        ids = sorted(eng._id_to_filename.keys())
        assert len(ids) >= 2, "pre-condition: need at least 2 tasks"

        # Delete only the first task
        evict_id = ids[0]
        remaining_id = ids[1]
        (tasks_dir / eng._id_to_filename[evict_id]).unlink()

        with pytest.raises(FileNotFoundError):
            eng.show_task(str(evict_id))

        # Eviction must be surgical — other entry must remain
        assert remaining_id in eng._id_to_filename, (
            "evicting one ghost entry must not remove other valid entries from _id_to_filename"
        )

    def test_show_task_after_eviction_second_call_can_succeed_via_glob(
        self, board: Path
    ) -> None:
        """After a ghost eviction, show_task() with a moved/recreated file falls back to glob.

        Scenario: file is deleted (eviction triggers), then recreated with same ID.
        Second call must find it via glob fallback.
        """
        tasks_dir = board / "tasks"
        eng = KanbanEngine(board, activity_log=False)
        eng.list_tasks()

        task_id = next(iter(eng._id_to_filename))
        filename = eng._id_to_filename[task_id]
        (tasks_dir / filename).unlink()

        # First call: evicts entry, raises FileNotFoundError
        with pytest.raises(FileNotFoundError):
            eng.show_task(str(task_id))

        assert task_id not in eng._id_to_filename, (
            "ghost must be evicted after first call"
        )

        # Recreate the file (simulates rename/recreation with same ID)
        _write_task_file(tasks_dir, task_id, status="in-progress")

        # Second call: _id_to_filename has no entry → glob fallback → succeeds
        task = eng.show_task(str(task_id))
        assert task.id == task_id

    # ------------------------------------------------------------------ AC 6
    # _find_task_path() checks _id_to_filename → return path → fallback to glob

    def test_find_task_path_warm_cache_id_absent_falls_back_to_glob(
        self, warm_engine: KanbanEngine
    ) -> None:
        """_find_task_path() must use glob when id cache is warm but ID is not in it.

        This tests the "warm cache + cache miss" path: _id_to_filename is non-empty
        (warm) but does not contain the requested id, so glob fallback activates.
        """
        tasks_dir = warm_engine._tasks_dir
        # Write a new task file directly — bypassing create_task so _id_to_filename stays stale
        _write_task_file(tasks_dir, 77)
        assert 77 not in warm_engine._id_to_filename, (
            "pre-condition: task 77 must not be in warm _id_to_filename"
        )

        # _find_task_path must fall through to glob and find the file
        result = warm_engine._find_task_path("77", warm_engine._tasks_dir)
        assert result.exists()
        assert result.name.startswith("77-")

    def test_find_task_path_returns_path_object(
        self, warm_engine: KanbanEngine
    ) -> None:
        """_find_task_path() must return a Path object, not a str or None."""
        task_id = str(next(iter(warm_engine._id_to_filename)))
        result = warm_engine._find_task_path(task_id, warm_engine._tasks_dir)
        assert isinstance(result, Path)

    def test_find_task_path_returned_path_is_absolute(
        self, warm_engine: KanbanEngine
    ) -> None:
        """_find_task_path() must return an absolute path (tasks_dir / filename)."""
        task_id = str(next(iter(warm_engine._id_to_filename)))
        result = warm_engine._find_task_path(task_id, warm_engine._tasks_dir)
        assert result.is_absolute(), f"expected absolute path, got {result}"

    def test_find_task_path_returned_path_exists(
        self, warm_engine: KanbanEngine
    ) -> None:
        """Path returned by _find_task_path() must exist on disk."""
        task_id = str(next(iter(warm_engine._id_to_filename)))
        result = warm_engine._find_task_path(task_id, warm_engine._tasks_dir)
        assert result.exists(), f"returned path does not exist: {result}"

    def test_find_task_path_missing_id_raises_file_not_found(
        self, warm_engine: KanbanEngine
    ) -> None:
        """_find_task_path() must raise FileNotFoundError when no matching file exists."""
        with pytest.raises(FileNotFoundError):
            warm_engine._find_task_path("9999", warm_engine._tasks_dir)

    def test_find_task_path_non_integer_id_warm_cache_raises_file_not_found(
        self, warm_engine: KanbanEngine
    ) -> None:
        """_find_task_path() with non-numeric task_id must raise FileNotFoundError, not ValueError.

        ValueError from int(task_id) must be caught; the method falls back to glob
        and raises FileNotFoundError when no match is found.
        """
        assert warm_engine._id_to_filename, "pre-condition: id cache must be warm"
        with pytest.raises(FileNotFoundError):
            warm_engine._find_task_path("not-a-number", warm_engine._tasks_dir)

    # ------------------------------------------------------------------ AC 7
    # No archive dispatch in _find_task_path() (all callers use tasks_dir)

    def test_find_task_path_with_archive_dir_does_not_use_id_to_filename(
        self, board: Path
    ) -> None:
        """_find_task_path() with archive_dir as search_dir must NOT consult _id_to_filename.

        The cache only indexes tasks in tasks_dir; _id_to_filename entries must not be
        used when searching another directory.
        """
        archive_dir = board / "archive"
        eng = KanbanEngine(board, activity_log=False)
        eng.list_tasks()  # populate _id_to_filename with tasks 1-3

        # Write task 1 to archive dir (simulating an archived version)
        _write_task_file(archive_dir, 1)

        # The archive path must be found via glob (not from _id_to_filename pointing to tasks_dir)
        result = eng._find_task_path("1", archive_dir)
        assert result.parent == archive_dir, (
            "_find_task_path() with archive_dir must return a path inside archive_dir"
        )

    def test_find_task_path_tasks_dir_does_not_access_archive_dir(
        self, warm_engine: KanbanEngine, board: Path
    ) -> None:
        """_find_task_path(tasks_dir) must never access archive_dir.

        No archive dispatch: the method uses _id_to_filename (for tasks_dir) or glob
        on the provided search_dir — it never redirects to a different directory.
        """
        archive_dir = board / "archive"
        task_id = str(next(iter(warm_engine._id_to_filename)))

        with patch.object(type(archive_dir), "glob") as mock_glob:
            warm_engine._find_task_path(task_id, warm_engine._tasks_dir)
            mock_glob.assert_not_called()
