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
