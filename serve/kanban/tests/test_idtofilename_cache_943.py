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
    return KanbanEngine(board, agent_name="test-agent", activity_log=False)


@pytest.fixture
def warm_engine(board: Path) -> KanbanEngine:
    """KanbanEngine whose cache is pre-warmed by list_tasks()."""
    eng = KanbanEngine(board, agent_name="test-agent", activity_log=False)
    eng.list_tasks()  # populates _task_cache and rebuilds _id_to_filename
    return eng


# ---------------------------------------------------------------------------
# TestFromAC_IdToFilenameCache
# ---------------------------------------------------------------------------


class TestFromAC_IdToFilenameCache:
    """Verifies _id_to_filename cache behaviour for show_task() and _find_task_path()."""

    # ------------------------------------------------------------------ AC 8
    # _id_to_filename initialized as empty dict

    def test_init_creates_id_to_filename_as_empty_dict(self, engine: KanbanEngine) -> None:
        """_id_to_filename must exist and be an empty dict immediately after __init__."""
        assert hasattr(engine, "_id_to_filename"), "_id_to_filename attribute missing from __init__"
        assert engine._id_to_filename == {}

    def test_id_to_filename_is_dict_type(self, engine: KanbanEngine) -> None:
        """_id_to_filename must be a plain dict, not a defaultdict or other mapping."""
        assert isinstance(engine._id_to_filename, dict)

    # ------------------------------------------------------------------ AC 4
    # list_tasks() rebuilds _id_to_filename on non-archived calls only

    def test_list_tasks_populates_id_to_filename(self, engine: KanbanEngine) -> None:
        """list_tasks() must populate _id_to_filename with int→filename mappings."""
        engine.list_tasks()
        assert engine._id_to_filename, "_id_to_filename must be non-empty after list_tasks()"

    def test_id_to_filename_keys_are_ints(self, engine: KanbanEngine) -> None:
        """Keys in _id_to_filename must be integers (task IDs)."""
        engine.list_tasks()
        for key in engine._id_to_filename:
            assert isinstance(key, int), f"key {key!r} must be int, got {type(key).__name__}"

    def test_id_to_filename_values_are_strings(self, engine: KanbanEngine) -> None:
        """Values in _id_to_filename must be filename strings (e.g. '1-task-1.md')."""
        engine.list_tasks()
        for filename in engine._id_to_filename.values():
            assert isinstance(filename, str), (
                f"filename {filename!r} must be str, got {type(filename).__name__}"
            )
            assert filename.endswith(".md"), f"filename {filename!r} must end with .md"

    def test_id_to_filename_covers_all_tasks(self, engine: KanbanEngine, board: Path) -> None:
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
        eng = KanbanEngine(board, agent_name="test-agent", activity_log=False)
        eng.list_tasks(archived=True)
        # _id_to_filename must remain empty; archived tasks are not indexed there
        assert eng._id_to_filename == {}, (
            "_id_to_filename must remain empty after list_tasks(archived=True)"
        )

    # ------------------------------------------------------------------ AC 5
    # refresh_config() clears _id_to_filename

    def test_refresh_config_clears_id_to_filename(self, warm_engine: KanbanEngine) -> None:
        """refresh_config() must reset _id_to_filename to empty dict."""
        assert warm_engine._id_to_filename, "pre-condition: _id_to_filename must be populated"
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
        assert warm_engine._id_to_filename, "_id_to_filename must be rebuilt after list_tasks() post-refresh"

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
        eng = KanbanEngine(board, agent_name="test-agent", activity_log=False)
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
        eng = KanbanEngine(board, agent_name="test-agent", activity_log=False)
        eng.list_tasks()

        task_id = next(iter(eng._id_to_filename))
        filename = eng._id_to_filename[task_id]
        old_mtime_ns = eng._task_cache[filename][0]

        time.sleep(0.01)
        _write_task_file(tasks_dir, task_id, status="in-progress")

        eng.show_task(str(task_id))

        new_mtime_ns = eng._task_cache[filename][0]
        assert new_mtime_ns != old_mtime_ns, "cache mtime_ns must be updated after re-read"
        assert eng._task_cache[filename][1].status == "in-progress"

    # ------------------------------------------------------------------ AC 2
    # show_task() file missing — evict both caches + glob fallback

    def test_show_task_missing_file_evicts_task_cache(self, board: Path) -> None:
        """When stat() reveals file is gone, the entry must be evicted from _task_cache."""
        tasks_dir = board / "tasks"
        eng = KanbanEngine(board, agent_name="test-agent", activity_log=False)
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
        eng = KanbanEngine(board, agent_name="test-agent", activity_log=False)
        eng.list_tasks()

        task_id = next(iter(eng._id_to_filename))
        filename = eng._id_to_filename[task_id]
        (tasks_dir / filename).unlink()

        with pytest.raises(FileNotFoundError):
            eng.show_task(str(task_id))

        assert task_id not in eng._id_to_filename, (
            "deleted file must be evicted from _id_to_filename"
        )

    def test_show_task_cold_cache_falls_back_to_glob(self, engine: KanbanEngine) -> None:
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
        # But _find_task_path must still succeed via glob fallback
        result = warm_engine._find_task_path(str(new_task.id), warm_engine._tasks_dir)
        assert result.exists()

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
        assert after_ids == before_ids, "_id_to_filename must be unchanged after create_task()"
