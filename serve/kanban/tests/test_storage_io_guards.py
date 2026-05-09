"""TDD: C-10 GREEN — storage_io atomic-write & ID-allocation (additional RED).

Task: #1055 (Brief C #1043) — paper-c.md §3, §8.1, §8.11
AC:   C1, C2, C3, C4, C4a, C4b, C51

All tests in the original C-01 RED file (test_storage_io.py) are GREEN —
the storage_io implementation is complete for the happy-path and concurrency
contract.  This file adds failing tests for a verified implementation gap:

Gap — AC-C3 (list_task_files / list_archive_files):
  Both functions use ``p.suffix == ".md"`` without ``p.is_file()``.
  A directory named ``1001-dir.md/`` inside tasks/ or archive/ is incorrectly
  included in the listing.  The contract ("list task **files**") implies only
  regular files should be returned.

All 4 tests FAIL in RED phase.
"""

from __future__ import annotations

from pathlib import Path

from owlbear_kanban.storage import (
    list_archive_files,
    list_task_files,
    move_to_archive,
    move_to_quarantine,
)

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


# ---------------------------------------------------------------------------
# TestFromAC_ListFilesFilesOnly — AC-C3
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# TestFromAC_QuarantineLockHygiene — AC-C4b2
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# TestFromAC_ArchiveLockHygiene — AC-C4b3
# ---------------------------------------------------------------------------


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
