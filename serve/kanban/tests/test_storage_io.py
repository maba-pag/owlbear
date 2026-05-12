"""TDD: C-01 — storage_io atomic-write & ID-allocation tests.

Task: #1046 (Brief C #1043) — paper-c.md §8.1, §8.11
AC:   C1, C2, C3, C4, C4a, C4b, C51
All 15 tests GREEN (implementation in storage_io.py and storage.py).
"""

from __future__ import annotations

import os
import threading
from pathlib import Path
from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from owlbear_kanban.config_loader import load_config
from owlbear_kanban.storage_io import atomic_write  # NEW module — ImportError in RED
from owlbear_kanban.storage import (  # NEW module — ImportError in RED
    ConcurrencyError,
    allocate_next_id,
    list_archive_files,
    list_task_files,
    move_to_archive,
    move_to_quarantine,
    save_config,
    write_task,
    write_task_if_unchanged,
)
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
entry_status: research
wave_size: 4
agent_map: {}
agent_types: {}
agent_compatibility: {}
non_impl_tags: [research, docs, type:config, type:docs, test, type:test, agent, quality, type:user-action]
archival_reasons: [completed, deprecated, dropped, duplicate, wontfix]
status_predicates: {}
claim_timeout: 1h
next_id: 1001
"""


def _make_board(base_dir: Path) -> Path:
    """Create a minimal Brief C kanban board. Returns kanban_dir."""
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


def _make_task(task_id: int = 1001) -> Task:
    """Return a minimal Task for write tests."""
    now = datetime.now(tz=UTC).isoformat()
    return Task(
        id=task_id,
        title="Atomic write test",
        status="todo",
        priority="needed",
        created=now,
        updated=now,
    )


# ---------------------------------------------------------------------------
# TestFromAC_AtomicWrite — AC-C1, AC-C2, AC-C3
# ---------------------------------------------------------------------------


class TestFromAC_AtomicWrite:
    """AC-C1, AC-C2, AC-C3: atomic_write primitive contract."""

    def test_ac_c1_writes_via_tmp_sibling(self, tmp_path: Path) -> None:
        """AC-C1: atomic_write uses .tmp-* sibling (same parent dir) before os.replace."""
        target = tmp_path / "output.md"
        content = "hello world\n"
        tmp_paths_seen: list[Path] = []
        original_replace = os.replace

        def spy_replace(src: str, dst: str) -> None:
            tmp_paths_seen.append(Path(src))
            original_replace(src, dst)

        with patch("os.replace", side_effect=spy_replace):
            atomic_write(target, content)

        assert target.read_text(encoding="utf-8") == content
        assert len(tmp_paths_seen) == 1
        tmp_used = tmp_paths_seen[0]
        assert tmp_used.name.startswith(".tmp-"), (
            f"Expected .tmp-* name, got {tmp_used.name}"
        )
        assert tmp_used.parent == target.parent, (
            f"tmp file must be a sibling of target; got {tmp_used.parent} vs {target.parent}"
        )

    @pytest.mark.skipif(
        not hasattr(os, "O_DIRECTORY"),
        reason="dir-fsync requires O_DIRECTORY (POSIX only)",
    )
    def test_ac_c1_posix_fsyncs_file_and_dir(self, tmp_path: Path) -> None:
        """AC-C1: when O_DIRECTORY available, atomic_write fsyncs file fd then parent-dir fd."""
        target = tmp_path / "output.md"
        parent_dir = str(target.parent)
        original_open = os.open
        original_fsync = os.fsync

        dir_fds: list[int] = []
        fsync_calls: list[int] = []

        def spy_open(path: str, flags: int, *args: object, **kwargs: object) -> int:
            fd = original_open(path, flags, *args, **kwargs)
            if isinstance(path, str) and path == parent_dir:
                dir_fds.append(fd)
            return fd

        def spy_fsync(fd: int) -> None:
            fsync_calls.append(fd)
            original_fsync(fd)

        with (
            patch("os.open", side_effect=spy_open),
            patch("os.fsync", side_effect=spy_fsync),
        ):
            atomic_write(target, "data\n")

        # At least 2 fsyncs: file fd + parent-directory fd (O_DIRECTORY platforms)
        assert len(fsync_calls) >= 2, f"Expected >=2 fsyncs, got {len(fsync_calls)}"
        assert len(dir_fds) >= 1, (
            "Expected os.open call for parent directory (dir-fsync)"
        )
        assert any(fd in set(dir_fds) for fd in fsync_calls), (
            f"No fsync on parent-dir fd; fsynced: {fsync_calls}, parent-dir fds: {dir_fds}"
        )

    def test_ac_c1_final_content_is_correct(self, tmp_path: Path) -> None:
        """AC-C1: target file contains exactly the written content after atomic_write."""
        target = tmp_path / "task.md"
        content = "---\nid: 1\ntitle: hello\n---\n\nbody\n"
        atomic_write(target, content)
        assert target.read_text(encoding="utf-8") == content

    def test_ac_c1_fsyncs_in_correct_order(self, tmp_path: Path) -> None:
        """AC-C1: fsync(file-fd) → replace always; fsync(dir-fd) only when O_DIRECTORY available."""
        target = tmp_path / "output.md"
        parent_dir = str(target.parent)
        original_open = os.open
        original_fsync = os.fsync
        original_replace = os.replace

        dir_fds: set[int] = set()
        sequence: list[str] = []

        def spy_open(path: str, flags: int, *args: object, **kwargs: object) -> int:
            fd = original_open(path, flags, *args, **kwargs)
            if path == parent_dir:
                dir_fds.add(fd)
            return fd

        def spy_fsync(fd: int) -> None:
            sequence.append("fsync_dir" if fd in dir_fds else "fsync_file")
            original_fsync(fd)

        def spy_replace(src: str, dst: str) -> None:
            sequence.append("replace")
            original_replace(src, dst)

        with (
            patch("os.open", side_effect=spy_open),
            patch("os.fsync", side_effect=spy_fsync),
            patch("os.replace", side_effect=spy_replace),
        ):
            atomic_write(target, "test content\n")

        if hasattr(os, "O_DIRECTORY"):
            expected = ["fsync_file", "replace", "fsync_dir"]
        else:
            expected = ["fsync_file", "replace"]
        assert sequence == expected, f"Expected {expected}, got {sequence}"

    def test_ac_c2_cleans_up_tmp_on_replace_failure(self, tmp_path: Path) -> None:
        """AC-C2: .tmp-* file removed when os.replace raises; target unaffected."""
        target = tmp_path / "existing.md"
        original = "original content\n"
        target.write_text(original, encoding="utf-8")

        with (
            patch("os.replace", side_effect=OSError("simulated replace failure")),
            pytest.raises(OSError, match="simulated replace failure"),
        ):
            atomic_write(target, "new content\n")

        tmp_leftovers = list(tmp_path.glob(".tmp-*"))
        assert tmp_leftovers == [], f"Leftover .tmp- files: {tmp_leftovers}"
        assert target.read_text(encoding="utf-8") == original

    def test_ac_c2_target_unaffected_on_fsync_failure(self, tmp_path: Path) -> None:
        """AC-C2: target unaffected when fsync raises; no .tmp-* file left."""
        target = tmp_path / "task.md"
        original = "original\n"
        target.write_text(original, encoding="utf-8")

        call_count = {"n": 0}
        original_fsync = os.fsync

        def fail_first_fsync(fd: int) -> None:
            call_count["n"] += 1
            if call_count["n"] == 1:
                msg = "simulated fsync failure"
                raise OSError(msg)
            original_fsync(fd)

        with patch("os.fsync", side_effect=fail_first_fsync), pytest.raises(OSError):
            atomic_write(target, "updated\n")

        tmp_leftovers = list(tmp_path.glob(".tmp-*"))
        assert tmp_leftovers == [], f"Leftover .tmp- files: {tmp_leftovers}"
        assert target.read_text(encoding="utf-8") == original

    def test_ac_c3_list_task_files_excludes_tmp(self, tmp_path: Path) -> None:
        """AC-C3: list_task_files never returns .tmp-* entries."""
        kanban_dir = _make_board(tmp_path)
        tasks_dir = kanban_dir / "tasks"
        (tasks_dir / "1001-real.md").write_text(
            "---\nid: 1001\n---\n", encoding="utf-8"
        )
        (tasks_dir / ".tmp-abc123.md").write_text("partial\n", encoding="utf-8")

        result = list_task_files(kanban_dir)
        names = [p.name for p in result]

        assert "1001-real.md" in names
        assert not any(n.startswith(".tmp-") for n in names)


# ---------------------------------------------------------------------------
# TestFromAC_IDAllocation — AC-C4, AC-C4a, AC-C4b, AC-C51
# ---------------------------------------------------------------------------


class TestFromAC_IDAllocation:
    """AC-C4, AC-C4a, AC-C4b, AC-C51: ID allocation and CAS contract."""

    def test_ac_c4_50_concurrent_threads_yield_distinct_ids(
        self, tmp_path: Path
    ) -> None:
        """AC-C4: 50 threads x 1 allocation -> 50 distinct IDs, no duplicates."""
        kanban_dir = _make_board(tmp_path)
        results: list[int] = []
        errors: list[Exception] = []
        lock = threading.Lock()

        def allocate() -> None:
            try:
                new_id = allocate_next_id(kanban_dir)
                with lock:
                    results.append(new_id)
            except Exception as exc:  # noqa: BLE001
                with lock:
                    errors.append(exc)

        threads = [threading.Thread(target=allocate) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Unexpected errors during allocation: {errors}"
        assert len(results) == 50
        assert len(set(results)) == 50, f"Duplicate IDs found: {sorted(results)}"

    def test_ac_c4_next_id_lock_file_exists_after_allocation(
        self, tmp_path: Path
    ) -> None:
        """AC-C4: allocate_next_id uses kanban_dir/.next_id.lock — file exists after call."""
        kanban_dir = _make_board(tmp_path)
        expected_lock = kanban_dir / ".next_id.lock"

        assert not expected_lock.exists(), (
            "Lock file must not exist before first allocation"
        )

        allocate_next_id(kanban_dir)

        assert expected_lock.exists(), (
            f".next_id.lock must exist at {expected_lock} after allocate_next_id; "
            "using a threading.Lock or a different path would fail this assertion"
        )

    def test_ac_c4a_cas_20_threads_one_success_19_stale(self, tmp_path: Path) -> None:
        """AC-C4a: 20 threads racing write_task_if_unchanged → exactly 1 success, 19 ERR_STALE."""
        kanban_dir = _make_board(tmp_path)
        task = _make_task(1001)
        write_task(task, kanban_dir)
        expected_updated = task.updated

        successes: list[int] = []
        stale_count: list[int] = []
        other_errors: list[Exception] = []
        lock = threading.Lock()

        def attempt() -> None:
            updated_task = task.model_copy(
                update={"updated": "2026-04-21T11:00:00+00:00"}
            )
            try:
                write_task_if_unchanged(updated_task, expected_updated, kanban_dir)
                with lock:
                    successes.append(1)
            except ConcurrencyError as exc:
                if exc.code == "ERR_STALE":
                    with lock:
                        stale_count.append(1)
                else:
                    with lock:
                        other_errors.append(exc)
            except Exception as exc:  # noqa: BLE001
                with lock:
                    other_errors.append(exc)

        threads = [threading.Thread(target=attempt) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert other_errors == [], f"Unexpected errors: {other_errors}"
        assert len(successes) == 1, f"Expected 1 success, got {len(successes)}"
        assert len(stale_count) == 19, f"Expected 19 ERR_STALE, got {len(stale_count)}"

    def test_ac_c4a_survivor_write_intact(self, tmp_path: Path) -> None:
        """AC-C4a: the one successful CAS write produces a readable task on disk."""
        kanban_dir = _make_board(tmp_path)
        task = _make_task(1001)
        write_task(task, kanban_dir)
        expected_updated = task.updated
        new_updated = "2026-04-21T12:00:00+00:00"
        updated_task = task.model_copy(
            update={"updated": new_updated, "title": "Updated"}
        )

        successes: list[int] = []
        lock = threading.Lock()

        def attempt() -> None:
            try:
                write_task_if_unchanged(updated_task, expected_updated, kanban_dir)
                with lock:
                    successes.append(1)
            except ConcurrencyError:
                pass

        threads = [threading.Thread(target=attempt) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(successes) == 1
        # The task file on disk must be readable and carry the updated title
        from owlbear_kanban.storage import read_task

        task_files = list_task_files(kanban_dir)
        assert len(task_files) >= 1
        written = read_task(task_files[0])
        assert written.title == "Updated"

    def test_ac_c4b_lock_files_not_in_list_task_files(self, tmp_path: Path) -> None:
        """AC-C4b: tasks/.<id>.lock files are NOT returned by list_task_files."""
        kanban_dir = _make_board(tmp_path)
        tasks_dir = kanban_dir / "tasks"
        (tasks_dir / "1001-real.md").write_text(
            "---\nid: 1001\n---\n", encoding="utf-8"
        )
        (tasks_dir / ".1001.lock").write_text("", encoding="utf-8")

        result = list_task_files(kanban_dir)
        names = [p.name for p in result]

        assert "1001-real.md" in names
        assert ".1001.lock" not in names

    def test_ac_c4b_lock_files_not_in_list_archive_files(self, tmp_path: Path) -> None:
        """AC-C4b: archive/.<id>.lock files are NOT returned by list_archive_files."""
        kanban_dir = _make_board(tmp_path)
        archive_dir = kanban_dir / "archive"
        (archive_dir / "0001-old.md").write_text("---\nid: 1\n---\n", encoding="utf-8")
        (archive_dir / ".0001.lock").write_text("", encoding="utf-8")

        result = list_archive_files(kanban_dir)
        names = [p.name for p in result]

        assert "0001-old.md" in names
        assert ".0001.lock" not in names

    def test_ac_c4b_write_task_if_unchanged_creates_lock_at_per_task_path(
        self, tmp_path: Path
    ) -> None:
        """AC-C4b: write_task_if_unchanged creates lock file at tasks/.<id>.lock."""
        kanban_dir = _make_board(tmp_path)
        task = _make_task(1001)
        write_task(task, kanban_dir)
        tasks_dir = kanban_dir / "tasks"
        expected_lock = tasks_dir / ".1001.lock"

        assert not expected_lock.exists(), (
            "Lock file must not exist before first write_task_if_unchanged"
        )

        updated = task.model_copy(update={"updated": "2026-04-21T12:00:00+00:00"})
        write_task_if_unchanged(updated, task.updated, kanban_dir)

        assert expected_lock.exists(), (
            f"write_task_if_unchanged must create lock at {expected_lock}; "
            "per-task lock must be at tasks/.<id>.lock"
        )

    def test_ac_c51_scan_based_allocation_ignores_config_next_id(
        self, tmp_path: Path
    ) -> None:
        """AC-#1443 scan-based: allocate_next_id ignores config.next_id; no burned-ID concept.

        Old AC-C51 tested burned-ID semantics (config.next_id incremented before write_task).
        Task #1443 replaces that with scan-based allocation: config.next_id is never read
        or written by allocate_next_id. Manually advancing config.next_id has no effect.
        An empty task board → allocate_next_id returns 1, regardless of config.next_id.
        """
        kanban_dir = _make_board(tmp_path)
        original_next_id = load_config(kanban_dir).next_id  # 1001 from _CONFIG_YAML

        # Simulate old burned-ID state by manually advancing config.next_id
        config = load_config(kanban_dir)
        config_burned = config.model_copy(update={"next_id": original_next_id + 1})
        save_config(config_burned, kanban_dir)
        assert load_config(kanban_dir).next_id == original_next_id + 1

        # Scan-based allocation: empty board → ID 1, ignoring config.next_id entirely
        next_id = allocate_next_id(kanban_dir)
        assert next_id == 1, (
            f"Scan-based allocate_next_id on empty board must return 1 "
            f"(ignores config.next_id={original_next_id + 1}); got {next_id}. "
            "Old config-based burned-ID semantics still active — scan-based not implemented."
        )

        # allocate_next_id must NOT modify config.next_id
        config_after = load_config(kanban_dir)
        assert config_after.next_id == original_next_id + 1, (
            f"allocate_next_id must not modify config.next_id (scan-based); "
            f"expected {original_next_id + 1} (unchanged), got {config_after.next_id}."
        )


# --- merged from serve/kanban/tests/test_storage_io_guards.py ---
class TestFromAC_ListFilesFilesOnly:
    """AC-C3: list_task_files / list_archive_files must return only regular files.

    The functions filter ``.tmp-*`` and ``.<id>.lock`` entries per the AC.
    The "list task **files**" contract implies directories must also be excluded:
    a directory with a ``.md`` name is not a task file.

    These tests expose the missing ``p.is_file()`` guard in both functions.
    """

    def test_ac_c3_list_task_files_excludes_md_named_directories(
        self, tmp_path: Path
    ) -> None:
        """AC-C3: list_task_files must not return a directory with a .md extension."""
        kanban_dir = _make_board(tmp_path)
        tasks_dir = kanban_dir / "tasks"

        # A valid task file
        (tasks_dir / "1002-real.md").write_text(
            "---\nid: 1002\ntitle: t\nstatus: todo\npriority: needed"
            "\ncreated: 2026-01-01T00:00:00+00:00\nupdated: 2026-01-01T00:00:00+00:00\n---\n",
            encoding="utf-8",
        )
        # A directory with a .md extension (e.g. left by an interrupted tool)
        (tasks_dir / "1001-dir.md").mkdir()

        result = list_task_files(kanban_dir)
        names = [p.name for p in result]

        assert "1002-real.md" in names, "Real task file must be listed"
        assert "1001-dir.md" not in names, (
            "Directory with .md extension must NOT be returned by list_task_files; "
            "only regular files are task files"
        )

    def test_ac_c3_list_task_files_all_results_are_regular_files(
        self, tmp_path: Path
    ) -> None:
        """AC-C3: Every path returned by list_task_files must satisfy p.is_file()."""
        kanban_dir = _make_board(tmp_path)
        tasks_dir = kanban_dir / "tasks"

        (tasks_dir / "1001-task.md").write_text(
            "---\nid: 1001\ntitle: t\nstatus: todo\npriority: needed"
            "\ncreated: 2026-01-01T00:00:00+00:00\nupdated: 2026-01-01T00:00:00+00:00\n---\n",
            encoding="utf-8",
        )
        (tasks_dir / "1002-dir.md").mkdir()  # directory masquerading as a task

        result = list_task_files(kanban_dir)

        non_files = [p for p in result if not p.is_file()]
        assert non_files == [], (
            f"list_task_files returned non-file entries: {[p.name for p in non_files]}"
        )

    def test_ac_c3_list_archive_files_excludes_md_named_directories(
        self, tmp_path: Path
    ) -> None:
        """AC-C3: list_archive_files must not return a directory with a .md extension."""
        kanban_dir = _make_board(tmp_path)
        archive_dir = kanban_dir / "archive"

        # A valid archived task file
        (archive_dir / "0002-archived.md").write_text(
            "---\nid: 2\ntitle: t\nstatus: done\npriority: needed"
            "\ncreated: 2026-01-01T00:00:00+00:00\nupdated: 2026-01-01T00:00:00+00:00\n---\n",
            encoding="utf-8",
        )
        # A directory with a .md extension
        (archive_dir / "0001-dir.md").mkdir()

        result = list_archive_files(kanban_dir)
        names = [p.name for p in result]

        assert "0002-archived.md" in names, "Real archived file must be listed"
        assert "0001-dir.md" not in names, (
            "Directory with .md extension must NOT be returned by list_archive_files"
        )

    def test_ac_c3_list_archive_files_all_results_are_regular_files(
        self, tmp_path: Path
    ) -> None:
        """AC-C3: Every path returned by list_archive_files must satisfy p.is_file()."""
        kanban_dir = _make_board(tmp_path)
        archive_dir = kanban_dir / "archive"

        (archive_dir / "0001-real.md").write_text(
            "---\nid: 1\ntitle: t\nstatus: done\npriority: needed"
            "\ncreated: 2026-01-01T00:00:00+00:00\nupdated: 2026-01-01T00:00:00+00:00\n---\n",
            encoding="utf-8",
        )
        (archive_dir / "0002-dir.md").mkdir()

        result = list_archive_files(kanban_dir)

        non_files = [p for p in result if not p.is_file()]
        assert non_files == [], (
            f"list_archive_files returned non-file entries: {[p.name for p in non_files]}"
        )

class TestFromAC_QuarantineLockHygiene:
    """AC-C4b2: move_to_quarantine no-ops on lock files matching .<digits>.lock.

    Mutation guard: removing the early-return branch in move_to_quarantine would
    cause the lock file to be moved into quarantine/, breaking coordination.
    """

    def test_ac_c4b2_lock_file_returned_unchanged(self, tmp_path: Path) -> None:
        """AC-C4b2: move_to_quarantine returns the original path for a .<digits>.lock file."""
        kanban_dir = _make_board(tmp_path)
        tasks_dir = kanban_dir / "tasks"
        lock_path = tasks_dir / ".1001.lock"
        lock_path.write_bytes(b"")

        result = move_to_quarantine(lock_path, kanban_dir)

        assert result == lock_path, (
            "move_to_quarantine must return the original path for a lock file, "
            "not a quarantine destination"
        )

    def test_ac_c4b2_lock_file_stays_at_original_path(self, tmp_path: Path) -> None:
        """AC-C4b2: lock file must remain at its original path after move_to_quarantine."""
        kanban_dir = _make_board(tmp_path)
        tasks_dir = kanban_dir / "tasks"
        lock_path = tasks_dir / ".1001.lock"
        lock_path.write_bytes(b"")

        move_to_quarantine(lock_path, kanban_dir)

        assert lock_path.exists(), (
            "Lock file must still exist at original path — move_to_quarantine must not move it"
        )

    def test_ac_c4b2_lock_file_not_present_in_quarantine(self, tmp_path: Path) -> None:
        """AC-C4b2: lock file must NOT appear in quarantine/ after move_to_quarantine."""
        kanban_dir = _make_board(tmp_path)
        tasks_dir = kanban_dir / "tasks"
        lock_path = tasks_dir / ".1001.lock"
        lock_path.write_bytes(b"")

        move_to_quarantine(lock_path, kanban_dir)

        quarantine_copy = kanban_dir / "quarantine" / ".1001.lock"
        assert not quarantine_copy.exists(), (
            "Lock file must NOT be moved into quarantine/ — move_to_quarantine must no-op it"
        )

    def test_ac_c4b2_quarantine_dir_not_created_for_lock_file(
        self, tmp_path: Path
    ) -> None:
        """AC-C4b2: quarantine/ directory must not be created when the input is a lock file."""
        kanban_dir = _make_board(tmp_path)
        tasks_dir = kanban_dir / "tasks"
        lock_path = tasks_dir / ".1001.lock"
        lock_path.write_bytes(b"")

        move_to_quarantine(lock_path, kanban_dir)

        assert not (kanban_dir / "quarantine").exists(), (
            "quarantine/ must not be created when move_to_quarantine no-ops on a lock file"
        )

class TestFromAC_ArchiveLockHygiene:
    """AC-C4b3: move_to_archive acquires both tasks/.<id>.lock and archive/.<id>.lock.

    Mutation guard: removing archive-lock acquisition would leave archive_dir/.<id>.lock
    absent after the call, failing the existence assertion.
    """

    _TASK_BODY = (
        "---\nid: {id}\ntitle: test-task\nstatus: done\npriority: needed"
        "\ncreated: 2026-01-01T00:00:00+00:00\nupdated: 2026-01-01T00:00:00+00:00\n---\n"
    )

    def test_ac_c4b3_archive_lock_file_exists_after_move(self, tmp_path: Path) -> None:
        """AC-C4b3: archive/.<id>.lock must exist after move_to_archive (archive lock acquired)."""
        task_id = 1001
        kanban_dir = _make_board(tmp_path)
        tasks_dir = kanban_dir / "tasks"
        (tasks_dir / f"{task_id}-test-task.md").write_text(
            self._TASK_BODY.format(id=task_id), encoding="utf-8"
        )

        move_to_archive(task_id, kanban_dir)

        archive_lock = kanban_dir / "archive" / f".{task_id}.lock"
        assert archive_lock.exists(), (
            "archive/.<id>.lock must exist after move_to_archive — "
            "proves _exclusive_file_lock was acquired on the archive-side lock path"
        )

    def test_ac_c4b3_task_lock_file_exists_after_move(self, tmp_path: Path) -> None:
        """AC-C4b3: tasks/.<id>.lock must exist after move_to_archive (task-side lock, first)."""
        task_id = 1002
        kanban_dir = _make_board(tmp_path)
        tasks_dir = kanban_dir / "tasks"
        (tasks_dir / f"{task_id}-test-task.md").write_text(
            self._TASK_BODY.format(id=task_id), encoding="utf-8"
        )

        move_to_archive(task_id, kanban_dir)

        task_lock = tasks_dir / f".{task_id}.lock"
        assert task_lock.exists(), (
            "tasks/.<id>.lock must exist after move_to_archive — "
            "proves task-side _exclusive_file_lock was acquired (lock order: task then archive)"
        )

    def test_ac_c4b3_both_lock_files_exist_after_move(self, tmp_path: Path) -> None:
        """AC-C4b3: both tasks/.<id>.lock and archive/.<id>.lock must exist (dual-lock contract)."""
        task_id = 1003
        kanban_dir = _make_board(tmp_path)
        tasks_dir = kanban_dir / "tasks"
        archive_dir = kanban_dir / "archive"
        (tasks_dir / f"{task_id}-test-task.md").write_text(
            self._TASK_BODY.format(id=task_id), encoding="utf-8"
        )

        move_to_archive(task_id, kanban_dir)

        missing = [
            p
            for p in [
                tasks_dir / f".{task_id}.lock",
                archive_dir / f".{task_id}.lock",
            ]
            if not p.exists()
        ]
        assert missing == [], (
            f"Both task and archive lock files must exist after move_to_archive; "
            f"missing: {[p.name for p in missing]}"
        )

