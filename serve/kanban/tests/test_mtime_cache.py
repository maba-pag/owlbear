"""Tests for task #942: mtime-scan cache in KanbanEngine.list_tasks().

AC coverage:
  1.  KanbanEngine.__init__ initializes _task_cache and _archive_cache as empty dicts
       (keyed by filename, valued by (st_mtime_ns: int, Task) tuples)
  2.  list_tasks() uses os.scandir() + entry.stat().st_mtime_ns — not glob
  3.  Only modified/new files re-parsed; cached Task objects returned for unchanged
  4.  Cache eviction for deleted files: entries not seen in scandir are removed
  5.  refresh_config() clears both caches
  6.  Non-existent archive_dir handled gracefully (empty list, no crash)
  7.  Engine revision counter continues incrementing on writes (cache is orthogonal)
  8.  Invalidation is lazy: write operations do NOT proactively update the cache
  9.  (Arch refinement) Suffix filtering: only .md files enter the cache
  10. (Arch refinement) Race condition guard: FileNotFoundError from read_task() suppressed

All tests FAIL in RED phase — cache not yet implemented in engine.py.
"""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import patch

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_kanban.models import Task

# ---------------------------------------------------------------------------
# Board helpers
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
claim_timeout: 1h
next_id: {next_id}
entry_status: research
terminal_status: done
wave_size: 4
agent_map:
    research: researcher
    backlog: architect
    todo: builder
    in-progress: reviewer
    review: reviewer
    docs: doc-writer
    done: auditor
agent_types: {{}}
agent_compatibility: {{}}
non_impl_tags: []
archival_reasons: [completed, deprecated, dropped, duplicate, wontfix]
tasks_dir: tasks
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
    """KanbanEngine for the board fixture."""
    return KanbanEngine(board, activity_log=False)


# ---------------------------------------------------------------------------
# TestFromAC_MtimeCache
# ---------------------------------------------------------------------------


class TestFromAC_MtimeCache:
    """Verifies mtime-scan cache behavior in KanbanEngine."""

    # ------------------------------------------------------------------ AC 1
    # Cache initialization

    def test_init_creates_task_cache_as_empty_dict(self, engine: KanbanEngine) -> None:
        """_task_cache must exist and be an empty dict immediately after __init__."""
        assert hasattr(engine, "_task_cache"), "_task_cache attribute missing from __init__"
        assert engine._task_cache == {}

    def test_init_creates_archive_cache_as_empty_dict(self, engine: KanbanEngine) -> None:
        """_archive_cache must exist and be an empty dict immediately after __init__."""
        assert hasattr(engine, "_archive_cache"), "_archive_cache attribute missing from __init__"
        assert engine._archive_cache == {}

    def test_cache_entry_is_int_mtime_ns_task_tuple(self, engine: KanbanEngine) -> None:
        """After list_tasks(), _task_cache values are (int, Task) tuples keyed by filename."""
        engine.list_tasks()
        assert engine._task_cache, "_task_cache must be non-empty after list_tasks()"
        for filename, value in engine._task_cache.items():
            assert isinstance(filename, str), f"key must be str filename, got {type(filename)}"
            assert isinstance(value, tuple), "value must be tuple"
            assert len(value) == 2, "value must be 2-tuple"
            mtime_ns, task = value
            assert isinstance(mtime_ns, int), f"mtime_ns must be int (st_mtime_ns), got {type(mtime_ns).__name__}"
            assert isinstance(task, Task), f"second element must be Task, got {type(task)}"

    # ------------------------------------------------------------------ AC 2 + 3
    # Warm cache: unchanged files not re-parsed

    def test_cold_call_populates_task_cache(self, engine: KanbanEngine) -> None:
        """Cold list_tasks() populates _task_cache with one entry per .md file."""
        results = engine.list_tasks()
        assert len(engine._task_cache) == len(results), "_task_cache must contain one entry per returned task"

    def test_unchanged_file_not_reparsed_on_warm_call(self, engine: KanbanEngine) -> None:
        """Second list_tasks() must not call read_task() when no files changed."""
        engine.list_tasks()  # cold call — populate cache
        with patch("owlbear_kanban.engine.read_task") as mock_read:
            engine.list_tasks()  # warm call — all files unchanged
            mock_read.assert_not_called()

    def test_warm_call_returns_same_task_ids(self, engine: KanbanEngine) -> None:
        """Warm list_tasks() returns the same task IDs as cold call (cache consistent)."""
        cold_ids = {t.id for t in engine.list_tasks()}
        warm_ids = {t.id for t in engine.list_tasks()}
        assert cold_ids == warm_ids
        # Also verify cache populated (fails with AttributeError if not implemented)
        assert len(engine._task_cache) == len(cold_ids)

    def test_modified_file_triggers_reparsing_and_cache_update(self, board: Path) -> None:
        """When a file's mtime changes, list_tasks() must re-parse it and update the cache."""
        tasks_dir = board / "tasks"
        eng = KanbanEngine(board, activity_log=False)
        eng.list_tasks()  # cold call

        # Pick one file; record its cached mtime
        md_files = sorted(tasks_dir.glob("*.md"))
        target = md_files[0]
        target_name = target.name
        old_mtime_ns = eng._task_cache[target_name][0]

        # Overwrite with new content (ensures mtime changes)
        time.sleep(0.01)  # ensure mtime differs on coarse-grained filesystems
        _write_task_file(tasks_dir, int(target_name.split("-")[0]), status="in-progress")

        eng.list_tasks()  # second call — target file modified

        new_mtime_ns = eng._task_cache[target_name][0]
        assert new_mtime_ns != old_mtime_ns, "cache must update mtime_ns after file modification"
        assert eng._task_cache[target_name][1].status == "in-progress", (
            "cache must reflect new task content after re-parse"
        )

    # ------------------------------------------------------------------ AC 4
    # Deleted file eviction

    def test_deleted_file_evicted_from_task_cache(self, board: Path) -> None:
        """Cache entry for a deleted file must be removed on next list_tasks()."""
        tasks_dir = board / "tasks"
        eng = KanbanEngine(board, activity_log=False)
        eng.list_tasks()  # populate cache

        md_files = sorted(tasks_dir.glob("*.md"))
        target = md_files[0]
        target_name = target.name
        assert target_name in eng._task_cache, "pre-condition: file in cache before deletion"

        target.unlink()
        eng.list_tasks()  # trigger eviction

        assert target_name not in eng._task_cache, "deleted file must be evicted from cache"

    def test_deleted_file_absent_from_results_after_eviction(self, board: Path) -> None:
        """Deleted task must not appear in list_tasks() results."""
        tasks_dir = board / "tasks"
        eng = KanbanEngine(board, activity_log=False)
        cold_ids = {t.id for t in eng.list_tasks()}

        md_files = sorted(tasks_dir.glob("*.md"))
        deleted_id = int(md_files[0].stem.split("-")[0])
        md_files[0].unlink()

        warm_ids = {t.id for t in eng.list_tasks()}
        assert deleted_id not in warm_ids
        assert len(warm_ids) == len(cold_ids) - 1
        # Verify cache eviction (fails with AttributeError if not implemented)
        assert len(eng._task_cache) == len(warm_ids)

    # ------------------------------------------------------------------ AC 5
    # refresh_config clears caches

    def test_refresh_config_clears_task_cache(self, engine: KanbanEngine) -> None:
        """refresh_config() must reset _task_cache to empty dict."""
        engine.list_tasks()
        assert engine._task_cache, "pre-condition: cache must be populated"
        engine.refresh_config()
        assert engine._task_cache == {}, "_task_cache must be empty after refresh_config()"

    def test_refresh_config_clears_archive_cache(self, board: Path) -> None:
        """refresh_config() must reset _archive_cache to empty dict."""
        archive_dir = board / "archive"
        _write_task_file(archive_dir, 99)
        eng = KanbanEngine(board, activity_log=False)
        eng.list_tasks(archived=True)
        assert eng._archive_cache, "pre-condition: archive cache must be populated"
        eng.refresh_config()
        assert eng._archive_cache == {}, "_archive_cache must be empty after refresh_config()"

    # ------------------------------------------------------------------ AC 6
    # Non-existent archive_dir graceful handling

    def test_nonexistent_archive_dir_returns_empty_list(self, board: Path) -> None:
        """list_tasks(archived=True) must return [] when archive_dir does not exist."""
        archive_dir = board / "archive"
        archive_dir.rmdir()  # remove the directory
        eng = KanbanEngine(board, activity_log=False)
        result = eng.list_tasks(archived=True)
        assert result == []
        # Also verify cache is empty (fails with AttributeError if not implemented)
        assert eng._archive_cache == {}

    def test_nonexistent_archive_dir_does_not_raise(self, board: Path) -> None:
        """list_tasks(archived=True) must not raise any exception when archive_dir missing."""
        archive_dir = board / "archive"
        archive_dir.rmdir()
        eng = KanbanEngine(board, activity_log=False)
        try:
            eng.list_tasks(archived=True)
        except Exception as exc:  # noqa: BLE001
            pytest.fail(f"list_tasks(archived=True) raised unexpectedly: {type(exc).__name__}: {exc}")
        # Cache must exist and be empty (fails with AttributeError if not implemented)
        assert eng._archive_cache == {}

    # ------------------------------------------------------------------ AC 7
    # Revision counter orthogonal to cache

    def test_revision_increments_after_create_with_warm_cache(self, engine: KanbanEngine) -> None:
        """revision must increment on create_task() even when cache is populated."""
        assert hasattr(engine, "_task_cache"), "pre-condition: _task_cache must exist"
        engine.list_tasks()  # warm cache
        before = engine.revision
        engine.create_task("Orthogonal task")
        assert engine.revision == before + 1

    def test_revision_increments_after_edit_with_warm_cache(self, board: Path) -> None:
        """revision must increment on edit_task() when cache is warm."""
        eng = KanbanEngine(board, activity_log=False)
        assert hasattr(eng, "_task_cache"), "pre-condition: _task_cache must exist"
        eng.list_tasks()  # warm cache
        before = eng.revision
        eng.edit_task("1", title="Updated title")
        assert eng.revision == before + 1

    # ------------------------------------------------------------------ AC 8
    # Lazy invalidation — write operations do NOT proactively update cache

    def test_edit_does_not_proactively_update_task_cache(self, engine: KanbanEngine) -> None:
        """After edit_task(), _task_cache entry must still hold the pre-edit task state."""
        engine.list_tasks()  # populate cache
        cached_filename = next(iter(engine._task_cache))
        _old_mtime_ns, old_task = engine._task_cache[cached_filename]
        old_title = old_task.title

        engine.edit_task(str(old_task.id), title="Should not appear in cache yet")

        # Cache must NOT be updated by the write — still holds old state
        assert engine._task_cache[cached_filename][1].title == old_title, (
            "write operations must not proactively update _task_cache"
        )

    def test_cache_updated_lazily_on_next_list_tasks(self, engine: KanbanEngine) -> None:
        """Cache update is deferred to the next list_tasks() call (scandir-driven)."""
        engine.list_tasks()  # warm cache
        cached_filename = next(iter(engine._task_cache))
        _, old_task = engine._task_cache[cached_filename]
        new_title = "Lazy update expected"

        engine.edit_task(str(old_task.id), title=new_title)
        # Before next list_tasks: cache still has old title
        assert engine._task_cache[cached_filename][1].title != new_title, (
            "cache must not be updated until next list_tasks()"
        )
        # After next list_tasks: cache reflects new content
        engine.list_tasks()
        assert engine._task_cache[cached_filename][1].title == new_title, (
            "cache must be updated on next list_tasks() after file modification"
        )

    # ------------------------------------------------------------------ AC 9 (arch refinement)
    # Suffix filtering

    def test_non_md_files_not_added_to_task_cache(self, board: Path) -> None:
        """Non-.md files in tasks_dir must not appear in _task_cache."""
        tasks_dir = board / "tasks"
        (tasks_dir / ".DS_Store").write_bytes(b"\x00junk")
        (tasks_dir / "tmp_abc123.tmp").write_text("temp", encoding="utf-8")
        eng = KanbanEngine(board, activity_log=False)
        eng.list_tasks()
        assert ".DS_Store" not in eng._task_cache, ".DS_Store must be excluded from cache"
        assert "tmp_abc123.tmp" not in eng._task_cache, ".tmp files must be excluded from cache"

    def test_non_md_files_not_in_list_tasks_results(self, board: Path) -> None:
        """Non-.md files must not produce TaskSummary entries in list_tasks() results."""
        tasks_dir = board / "tasks"
        (tasks_dir / "notes.txt").write_text("not a task", encoding="utf-8")
        eng = KanbanEngine(board, activity_log=False)
        results = eng.list_tasks()
        # All returned summaries must have integer IDs (from valid task files)
        for summary in results:
            assert isinstance(summary.id, int)
        # Verify non-md file didn't inflate results beyond expected count
        assert len(results) == 3, "non-.md files must not inflate result count"
        # Cache must not contain the non-md file (fails with AttributeError if not implemented)
        assert "notes.txt" not in eng._task_cache

    # ------------------------------------------------------------------ AC 10 (arch refinement)
    # Race condition guard

    def test_race_condition_fileerror_during_read_task_suppressed(self, engine: KanbanEngine) -> None:
        """FileNotFoundError from read_task() inside list_tasks() must be suppressed."""
        engine.list_tasks()  # populate cache

        # Simulate a race: first call to read_task raises FileNotFoundError
        # (file deleted between scandir and read)
        call_count: dict[str, int] = {"n": 0}
        original_read_task = __import__("owlbear_kanban.storage", fromlist=["read_task"]).read_task

        def patched_read(path: Path, **_kwargs) -> Task:  # type: ignore[return]
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise FileNotFoundError(f"Race: file vanished: {path}")
            return original_read_task(path)

        with patch("owlbear_kanban.engine.read_task", side_effect=patched_read):
            try:
                engine.list_tasks()
            except FileNotFoundError as exc:
                pytest.fail(f"FileNotFoundError must be suppressed, but got: {exc}")

    def test_race_condition_evicts_entry_from_cache_when_file_gone(self, board: Path) -> None:
        """If read_task() raises FileNotFoundError for a cached file, evict that cache entry."""
        tasks_dir = board / "tasks"
        eng = KanbanEngine(board, activity_log=False)
        eng.list_tasks()  # cold call — populate cache

        md_files = sorted(tasks_dir.glob("*.md"))
        target = md_files[0]
        target_name = target.name
        assert target_name in eng._task_cache, "pre-condition: target in cache"

        # Force mtime change so next scandir sees the entry as modified (cache miss),
        # causing read_task() to be called — without this the warm call is a cache hit
        # and read_task() is never invoked, making the FileNotFoundError unreachable.
        time.sleep(0.01)
        target.write_bytes(target.read_bytes())

        original_read_task = __import__("owlbear_kanban.storage", fromlist=["read_task"]).read_task

        def patched_read(path: Path, **_kwargs) -> Task:  # type: ignore[return]
            if path.name == target_name:
                raise FileNotFoundError(f"Race: {path}")
            return original_read_task(path)

        with patch("owlbear_kanban.engine.read_task", side_effect=patched_read):
            eng.list_tasks()

        assert target_name not in eng._task_cache, "cache entry must be evicted when read_task raises FileNotFoundError"
