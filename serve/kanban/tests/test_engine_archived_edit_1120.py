"""Archived-task edit persistence regression tests (task #1121).

Tests that AgentView.edit_task and KanbanEngine.edit_task correctly persist
edits to tasks stored in archive/.  Covers archival_reason, archival_refs,
append_body, priority update, archive-dir placement (no tasks/ duplicate),
and updated-timestamp propagation.  Also covers the stale-cache fallback
path and rollback behaviour on emit failure.

AC coverage (from task #1121):
  AC-1 → test_agentview_edit_archived_archival_reason_result_updated
          test_agentview_edit_archived_archival_reason_reread_from_archive
  AC-2 → test_agentview_edit_archived_archival_refs_result_updated
          test_agentview_edit_archived_archival_refs_reread_from_archive
          test_agentview_edit_archived_archival_refs_change_to_different_id_result_updated
          test_agentview_edit_archived_archival_refs_change_to_different_id_reread_from_archive
  AC-3 → test_agentview_edit_archived_append_body_result_contains_text
          test_agentview_edit_archived_append_body_reread_from_archive
  AC-4 → test_core_engine_edit_archived_priority_result_updated
          test_core_engine_edit_archived_priority_reread_from_archive
  AC-5 → test_edit_archived_file_stays_in_archive_dir
          test_edit_archived_no_duplicate_created_in_tasks_dir
  AC-6 → test_edit_archived_updated_timestamp_advances
          test_edit_archived_updated_timestamp_advances_persisted_to_disk
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_kanban.engine import AgentView
from owlbear_kanban.models import Task
from owlbear_kanban.storage import (
    ConcurrencyError,
    CorruptionError,
    allocate_next_id,
    generate_slug,
    list_archive_files,
    list_task_files,
    load_config,
    make_task_filename,
    move_to_archive,
    move_to_quarantine,
    read_task,
    save_config,
    validate_path_containment,
    write_task,
    write_task_if_unchanged,
)

_EMIT_PATCH = "owlbear_kanban.activity_store.append_activity_event"

# ---------------------------------------------------------------------------
# Board + task helpers
# ---------------------------------------------------------------------------

_BASE_CONFIG = """\
statuses:
  - research
  - backlog
  - todo
  - in-progress
  - review
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
  todo: builder
  in-progress: builder
  review: reviewer
  done: auditor
agent_types: {}
agent_compatibility: {}
non_impl_tags: [research, docs]
archival_reasons: [completed, deprecated, dropped, duplicate, wontfix]
status_predicates: {}
claim_timeout: 1h
next_id: 10
"""

_TASK_TMPL = """\
---
id: {task_id}
title: {title}
status: {status}
priority: {priority}
created: "2026-01-01T10:00:00+00:00"
updated: "2026-01-01T10:00:00+00:00"
tags: []
parent: null
depends_on: []
blocked: false
block_reason: null
claimed_at: null
archival_reason: {archival_reason}
archival_refs: {archival_refs}
---
{body}
"""


def _make_board(base_dir: Path) -> Path:
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_BASE_CONFIG, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


def _write_task(  # noqa: PLR0913
    kanban_dir: Path,
    *,
    task_id: int = 1,
    title: str = "Task",
    status: str = "todo",
    priority: str = "needed",
    archival_reason: str = "null",
    archival_refs: str = "[]",
    body: str = "Body.",
    subdir: str = "tasks",
) -> Path:
    content = _TASK_TMPL.format(
        task_id=task_id,
        title=title,
        status=status,
        priority=priority,
        archival_reason=archival_reason,
        archival_refs=archival_refs,
        body=body,
    )
    dest_dir = kanban_dir / subdir
    dest_dir.mkdir(parents=True, exist_ok=True)
    path = dest_dir / f"{task_id}-task.md"
    path.write_text(content, encoding="utf-8")
    return path


def _make_engine(base_dir: Path) -> tuple[KanbanEngine, Path]:
    kanban_dir = _make_board(base_dir)
    engine = KanbanEngine(kanban_dir, activity_log=False)
    return engine, kanban_dir


def _make_view(base_dir: Path) -> tuple[AgentView, Path]:
    engine, kanban_dir = _make_engine(base_dir)
    return AgentView(engine), kanban_dir


# ---------------------------------------------------------------------------
# TestFromAC_ArchivedTaskEditPersistence
# ---------------------------------------------------------------------------


class TestFromAC_ArchivedTaskEditPersistence:
    """Covers archived-task edit persistence — defects D1 and D2 in engine + storage.

    All tests currently fail with FileNotFoundError at the engine._find_task_path step (D1).
    After D1 is fixed, tests for file location (AC-5) and on-disk content (AC-1 through AC-4, AC-6)
    will additionally expose D2 (write_task targets tasks/ instead of archive/).
    """

    # ------------------------------------------------------------------
    # AC-1: AgentView.edit_task — archival_reason update
    # ------------------------------------------------------------------

    def test_agentview_edit_archived_archival_reason_result_updated(
        self, tmp_path: Path
    ) -> None:
        """AC-1: edit_task on archived task with archival_reason='dropped'; returned object shows updated reason.

        Fails now: _find_task_path raises FileNotFoundError (D1 — tasks/ only).
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(
            kanban_dir,
            task_id=1,
            status="archived",
            archival_reason="null",
            archival_refs="[]",
            subdir="archive",
        )

        result = view.edit_task(1, archival_reason="dropped")

        assert result.archival_reason == "dropped"

    def test_agentview_edit_archived_archival_reason_reread_from_archive(
        self, tmp_path: Path
    ) -> None:
        """AC-1: after edit, re-reading via show_task returns updated archival_reason from archive/.

        Confirms on-disk persistence, not just the in-memory return value.
        Fails now: _find_task_path raises FileNotFoundError (D1).
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(
            kanban_dir,
            task_id=1,
            status="archived",
            archival_reason="null",
            archival_refs="[]",
            subdir="archive",
        )

        view.edit_task(1, archival_reason="dropped")

        reread = view.engine.show_task("1")
        assert reread.archival_reason == "dropped"

    # ------------------------------------------------------------------
    # AC-2: AgentView.edit_task — archival_refs update
    # ------------------------------------------------------------------

    def test_agentview_edit_archived_archival_refs_result_updated(
        self, tmp_path: Path
    ) -> None:
        """AC-2: edit_task on archived task (reason=deprecated) with archival_refs=[2, 3]; result shows updated refs.

        Task starts with refs=[2]; edit adds ref 3 so the change is non-trivial and not a no-op.
        Fails now: _find_task_path raises FileNotFoundError (D1).
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, task_id=2, status="done", subdir="tasks")
        _write_task(kanban_dir, task_id=3, status="done", subdir="tasks")
        _write_task(
            kanban_dir,
            task_id=1,
            status="archived",
            archival_reason="deprecated",
            archival_refs="[2]",
            subdir="archive",
        )

        result = view.edit_task(1, archival_refs=[2, 3])

        assert result.archival_refs == [2, 3]

    def test_agentview_edit_archived_archival_refs_reread_from_archive(
        self, tmp_path: Path
    ) -> None:
        """AC-2: after archival_refs edit, re-read from archive shows the new refs.

        Starts with refs=[2]; edits to [2, 3] to confirm a real change round-trips through disk.
        Fails now: _find_task_path raises FileNotFoundError (D1).
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, task_id=2, status="done", subdir="tasks")
        _write_task(kanban_dir, task_id=3, status="done", subdir="tasks")
        _write_task(
            kanban_dir,
            task_id=1,
            status="archived",
            archival_reason="deprecated",
            archival_refs="[2]",
            subdir="archive",
        )

        view.edit_task(1, archival_refs=[2, 3])

        reread = view.engine.show_task("1")
        assert 3 in reread.archival_refs

    # ------------------------------------------------------------------
    # AC-3: AgentView.edit_task — append_body
    # ------------------------------------------------------------------

    def test_agentview_edit_archived_append_body_result_contains_text(
        self, tmp_path: Path
    ) -> None:
        """AC-3: append_body on an archived task; returned body contains the appended text.

        Fails now: _find_task_path raises FileNotFoundError (D1).
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(
            kanban_dir,
            task_id=1,
            status="archived",
            archival_reason="dropped",
            body="Original body.",
            subdir="archive",
        )

        result = view.edit_task(1, append_body="Appended note.")

        assert "Original body." in (result.body or ""), (
            "original body content must be preserved after append"
        )
        assert "Appended note." in (result.body or "")

    def test_agentview_edit_archived_append_body_reread_from_archive(
        self, tmp_path: Path
    ) -> None:
        """AC-3: after append_body edit, re-reading from archive confirms text was persisted.

        Fails now: _find_task_path raises FileNotFoundError (D1).
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(
            kanban_dir,
            task_id=1,
            status="archived",
            archival_reason="dropped",
            body="Original body.",
            subdir="archive",
        )

        view.edit_task(1, append_body="Appended note.")

        reread = view.engine.show_task("1")
        assert "Original body." in (reread.body or ""), (
            "original body content must be preserved in archive after append"
        )
        assert "Appended note." in (reread.body or "")

    # ------------------------------------------------------------------
    # AC-4: core KanbanEngine.edit_task — priority update
    # ------------------------------------------------------------------

    def test_core_engine_edit_archived_priority_result_updated(
        self, tmp_path: Path
    ) -> None:
        """AC-4: KanbanEngine.edit_task on archived task with priority='critical'; result shows updated priority.

        Bypasses AgentView to confirm the defect is in the core engine path, not only AgentView.
        Fails now: _find_task_path raises FileNotFoundError (D1).
        """
        engine, kanban_dir = _make_engine(tmp_path)
        _write_task(
            kanban_dir,
            task_id=1,
            status="archived",
            archival_reason="dropped",
            priority="needed",
            subdir="archive",
        )

        result = engine.edit_task("1", priority="critical")

        assert result.priority == "critical"

    def test_core_engine_edit_archived_priority_reread_from_archive(
        self, tmp_path: Path
    ) -> None:
        """AC-4: after engine.edit_task, re-reading from archive shows the updated priority on disk.

        Fails now: _find_task_path raises FileNotFoundError (D1).
        """
        engine, kanban_dir = _make_engine(tmp_path)
        _write_task(
            kanban_dir,
            task_id=1,
            status="archived",
            archival_reason="dropped",
            priority="needed",
            subdir="archive",
        )

        engine.edit_task("1", priority="critical")

        reread = engine.show_task("1")
        assert reread.priority == "critical"

    # ------------------------------------------------------------------
    # AC-5: file stays in archive/, no duplicate in tasks/
    # ------------------------------------------------------------------

    def test_edit_archived_file_stays_in_archive_dir(
        self, tmp_path: Path
    ) -> None:
        """AC-5: after a successful edit the task file still exists in archive/.

        D1 prevents reaching the write step; once D1 is fixed, D2 would still
        create the file in the wrong location.
        Fails now: _find_task_path raises FileNotFoundError (D1).
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(
            kanban_dir,
            task_id=1,
            status="archived",
            archival_reason="dropped",
            subdir="archive",
        )

        view.edit_task(1, append_body="Changed.")

        archive_file = kanban_dir / "archive" / "1-task.md"
        assert archive_file.exists(), "task file must remain in archive/ after edit"

    def test_edit_archived_no_duplicate_created_in_tasks_dir(
        self, tmp_path: Path
    ) -> None:
        """AC-5: no task file is created in tasks/ after editing an archived task.

        D2 causes write_task to always target tasks/; the fix must preserve archive/ placement.
        Fails now: _find_task_path raises FileNotFoundError (D1).
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(
            kanban_dir,
            task_id=1,
            status="archived",
            archival_reason="dropped",
            subdir="archive",
        )

        view.edit_task(1, append_body="Changed.")

        tasks_files = list((kanban_dir / "tasks").glob("1-*.md"))
        assert tasks_files == [], (
            "no task file should exist in tasks/ after editing an archived task; "
            f"found: {tasks_files}"
        )

    # ------------------------------------------------------------------
    # AC-6: updated timestamp advances
    # ------------------------------------------------------------------

    def test_edit_archived_updated_timestamp_advances(
        self, tmp_path: Path
    ) -> None:
        """AC-6: successful edit of an archived task advances the 'updated' timestamp.

        The initial timestamp is '2026-01-01T10:00:00+00:00'; any successful edit must change it.
        Fails now: _find_task_path raises FileNotFoundError (D1).
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(
            kanban_dir,
            task_id=1,
            status="archived",
            archival_reason="dropped",
            subdir="archive",
        )
        original_task = view.engine.show_task("1")
        original_updated = original_task.updated

        result = view.edit_task(1, append_body="New note.")

        assert result.updated > original_updated, (
            "edit of an archived task must advance the 'updated' timestamp forward; "
            f"before={original_updated!r}, after={result.updated!r}"
        )

    def test_edit_archived_updated_timestamp_advances_persisted_to_disk(
        self, tmp_path: Path
    ) -> None:
        """AC-6 (on-disk): re-reading from archive confirms the advanced timestamp was persisted.

        The existing AC-6 test only checks the returned Task object; this test proves
        the advanced timestamp is also present in the file on disk (archive/).
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(
            kanban_dir,
            task_id=1,
            status="archived",
            archival_reason="dropped",
            subdir="archive",
        )
        original_task = view.engine.show_task("1")
        original_updated = original_task.updated

        view.edit_task(1, append_body="Disk proof.")

        reread = view.engine.show_task("1")
        assert reread.updated > original_updated, (
            "persisted file in archive/ must have an advanced 'updated' timestamp forward; "
            f"before={original_updated!r}, after={reread.updated!r}"
        )

    # ------------------------------------------------------------------
    # AC-2 strengthened: archival_refs change to a different value
    # ------------------------------------------------------------------

    def test_agentview_edit_archived_archival_refs_change_to_different_id_result_updated(
        self, tmp_path: Path
    ) -> None:
        """AC-2 (strict): archival_refs updated from [2] to [3]; result must equal [3] exactly.

        The existing AC-2 test seeds [2] and re-applies [2]; that test passes even if the
        assignment were removed.  This test starts with refs=[2] and edits to [3] — the result
        must be exactly [3], not a superset or the old value.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, task_id=2, status="done", subdir="tasks")
        _write_task(kanban_dir, task_id=3, status="done", subdir="tasks")
        _write_task(
            kanban_dir,
            task_id=1,
            status="archived",
            archival_reason="deprecated",
            archival_refs="[2]",
            subdir="archive",
        )

        result = view.edit_task(1, archival_refs=[3])

        assert result.archival_refs == [3], (
            f"archival_refs must be replaced with [3]; got {result.archival_refs!r}"
        )

    def test_agentview_edit_archived_archival_refs_change_to_different_id_reread_from_archive(
        self, tmp_path: Path
    ) -> None:
        """AC-2 (strict, on-disk): after changing archival_refs from [2] to [3], re-reading
        from archive must return [3] exactly — not [2] or a superset.
        """
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, task_id=2, status="done", subdir="tasks")
        _write_task(kanban_dir, task_id=3, status="done", subdir="tasks")
        _write_task(
            kanban_dir,
            task_id=1,
            status="archived",
            archival_reason="deprecated",
            archival_refs="[2]",
            subdir="archive",
        )

        view.edit_task(1, archival_refs=[3])

        reread = view.engine.show_task("1")
        assert reread.archival_refs == [3], (
            f"re-read archival_refs from archive must be [3]; got {reread.archival_refs!r}"
        )

    # ------------------------------------------------------------------
    # AC-8: warm _id_to_filename cache must not bypass archive fallback
    # ------------------------------------------------------------------

    def test_edit_archived_stale_id_to_filename_cache_falls_back_to_archive(
        self, tmp_path: Path
    ) -> None:
        """AC-8: _find_task_path archive fallback works even when _id_to_filename is warm.

        Scenario:
          1. Task 1 starts in tasks/ — list_tasks populates _id_to_filename[1].
          2. The file is moved to archive/ outside the engine (stale cache entry).
          3. engine.edit_task must still find the task via archive fallback and succeed.
          4. The edited file must remain in archive/; no duplicate must appear in tasks/.

        This test would fail if _find_task_path returned the stale tasks/ path without
        checking for archive fallback when the candidate does not exist.
        """
        engine, kanban_dir = _make_engine(tmp_path)
        _write_task(
            kanban_dir,
            task_id=1,
            status="archived",
            archival_reason="dropped",
            priority="needed",
            subdir="tasks",
        )

        # Warm the _id_to_filename cache.
        engine.list_tasks()
        assert 1 in engine._id_to_filename, "pre-condition: cache must contain task 1"

        # Move file to archive/ without going through engine.move_task
        # (cache remains stale — _id_to_filename[1] still points to tasks/).
        tasks_file = kanban_dir / "tasks" / "1-task.md"
        archive_file = kanban_dir / "archive" / "1-task.md"
        tasks_file.rename(archive_file)

        # edit_task must succeed via archive fallback.
        result = engine.edit_task("1", priority="critical")

        assert result.priority == "critical", "priority must be updated to 'critical'"
        assert archive_file.exists(), "edited file must remain in archive/"
        assert not (kanban_dir / "tasks" / "1-task.md").exists(), (
            "no duplicate must appear in tasks/ after editing via archive fallback"
        )

    # ------------------------------------------------------------------
    # Rollback: archived-task edit must roll back to archive/ on emit failure
    # ------------------------------------------------------------------

    def test_edit_archived_rollback_on_emit_failure_content_preserved_in_archive(
        self, tmp_path: Path
    ) -> None:
        """Rollback: when _emit_event fails for an archived task, write_task rolls back
        the original content to archive/ (not tasks/), and the OSError propagates.

        This proves the rollback write_task call uses target_dir=archive/.
        """
        kanban_dir = _make_board(tmp_path)
        _write_task(
            kanban_dir,
            task_id=1,
            status="archived",
            archival_reason="dropped",
            priority="needed",
            subdir="archive",
        )
        engine = KanbanEngine(kanban_dir, activity_log=True)
        archive_file = kanban_dir / "archive" / "1-task.md"
        original_content = archive_file.read_text(encoding="utf-8")

        with (
            patch(_EMIT_PATCH, side_effect=OSError("disk full")),
            pytest.raises(OSError, match="disk full"),
        ):
            engine.edit_task("1", priority="critical")

        rolled_back = read_task(archive_file)
        assert rolled_back.priority == "needed", (
            "priority must be rolled back to 'needed' after emit failure"
        )
        assert not (kanban_dir / "tasks" / "1-task.md").exists(), (
            "rollback write must not create a file in tasks/"
        )
        _ = original_content  # retained for readability; content already validated via read_task


# ---------------------------------------------------------------------------
# TestFromAC_StorageCoveragePaths
# ---------------------------------------------------------------------------

_TASK_DICT = {
    "id": 1,
    "title": "Task",
    "status": "todo",
    "priority": "needed",
    "created": "2026-01-01T10:00:00+00:00",
    "updated": "2026-01-01T10:00:00+00:00",
    "tags": [],
    "parent": None,
    "depends_on": [],
    "blocked": False,
    "block_reason": None,
    "claimed_at": None,
    "archival_reason": None,
    "archival_refs": [],
    "body": "",
}


class TestFromAC_StorageCoveragePaths:
    """Supplementary coverage tests for owlbear_kanban.storage.

    Written to bring storage module coverage to >=90% by exercising branches
    not reached by the AC test suite above. Each test targets a specific
    uncovered line-range identified from the coverage report when running
    only the 16 AC tests.

    These tests are GREEN against the completed implementation (round 2+).
    Added post-implementation per builder and reviewer coverage requests.
    """

    # ------------------------------------------------------------------
    # generate_slug
    # ------------------------------------------------------------------

    def test_generate_slug_empty_title_returns_empty(self) -> None:
        """generate_slug('') returns '' via the early-return branch."""
        assert generate_slug("") == ""

    def test_generate_slug_windows_reserved_name_raises(self) -> None:
        """generate_slug raises ValueError for Windows reserved filenames like 'con'."""
        with pytest.raises(ValueError, match="Windows reserved"):
            generate_slug("con")

    # ------------------------------------------------------------------
    # make_task_filename
    # ------------------------------------------------------------------

    def test_make_task_filename_returns_id_dash_slug_dot_md(self) -> None:
        """make_task_filename returns '{id}-{slug}.md'."""
        assert make_task_filename(5, "Hello World") == "5-hello-world.md"

    # ------------------------------------------------------------------
    # validate_path_containment
    # ------------------------------------------------------------------

    def test_validate_path_containment_null_byte_raises(self, tmp_path: Path) -> None:
        """validate_path_containment raises ValueError when str(path) contains a null byte."""
        bad_path = MagicMock()
        bad_path.__str__ = MagicMock(return_value="evil\x00.md")  # noqa: S108

        with pytest.raises(ValueError, match="null byte"):
            validate_path_containment(tmp_path, bad_path)

    def test_validate_path_containment_path_equals_dir_raises(
        self, tmp_path: Path
    ) -> None:
        """validate_path_containment raises ValueError when path == tasks_dir."""
        with pytest.raises(ValueError, match="not tasks_dir itself"):
            validate_path_containment(tmp_path, tmp_path)

    def test_validate_path_containment_path_outside_dir_raises(
        self, tmp_path: Path
    ) -> None:
        """validate_path_containment raises PermissionError when path escapes tasks_dir."""
        outside = tmp_path.parent / "other" / "file.md"
        with pytest.raises(PermissionError, match="outside tasks_dir"):
            validate_path_containment(tmp_path, outside)

    # ------------------------------------------------------------------
    # read_task: special paths
    # ------------------------------------------------------------------

    def test_read_task_cp1252_fallback_succeeds(self, tmp_path: Path) -> None:
        """read_task falls back to cp1252 when the file is not valid UTF-8.

        The euro sign (€ U+20AC) is byte 0x80 in cp1252, which is an invalid
        continuation byte in UTF-8 — triggering the UnicodeDecodeError branch.
        """
        content = _TASK_TMPL.format(
            task_id=1,
            title="Task",
            status="todo",
            priority="needed",
            archival_reason="null",
            archival_refs="[]",
            body="Body with euro: \u20ac",
        )
        path = tmp_path / "1-task.md"
        path.write_bytes(content.encode("cp1252"))

        task = read_task(path)

        assert task.id == 1
        assert "\u20ac" in (task.body or "")

    def test_read_task_missing_opening_delimiter_raises_corruption(
        self, tmp_path: Path
    ) -> None:
        """read_task raises CorruptionError (ERR_CORRUPT_DELIMITERS) without opening '---'."""
        path = tmp_path / "no-frontmatter.md"
        path.write_text("no yaml here\nbody content", encoding="utf-8")

        with pytest.raises(CorruptionError) as exc_info:
            read_task(path)

        assert exc_info.value.code == "ERR_CORRUPT_DELIMITERS"

    def test_read_task_missing_closing_delimiter_raises_corruption(
        self, tmp_path: Path
    ) -> None:
        """read_task raises CorruptionError (ERR_CORRUPT_DELIMITERS) without closing '---'."""
        path = tmp_path / "1-no-close.md"
        path.write_text("---\nid: 1\ntitle: Task\n", encoding="utf-8")

        with pytest.raises(CorruptionError) as exc_info:
            read_task(path)

        assert exc_info.value.code == "ERR_CORRUPT_DELIMITERS"

    def test_read_task_type_mismatch_raises_corruption(self, tmp_path: Path) -> None:
        """read_task raises CorruptionError when a field has an incompatible type.

        id: 'abc' (string) fails pydantic int coercion → ValidationError →
        _validation_to_corruption → CorruptionError(ERR_CORRUPT_TYPE_MISMATCH).
        No config.yml at path.parent.parent so board-level corruption check is skipped.
        """
        path = tmp_path / "bad.md"
        path.write_text(
            "---\n"
            "id: abc\n"
            "title: Task\n"
            "status: todo\n"
            "priority: needed\n"
            "created: '2026-01-01T10:00:00+00:00'\n"
            "updated: '2026-01-01T10:00:00+00:00'\n"
            "tags: []\n"
            "parent: null\n"
            "depends_on: []\n"
            "blocked: false\n"
            "block_reason: null\n"
            "claimed_at: null\n"
            "archival_reason: null\n"
            "archival_refs: []\n"
            "---\nBody",
            encoding="utf-8",
        )

        with pytest.raises(CorruptionError):
            read_task(path)

    def test_read_task_non_integer_stem_prefix_skips_mismatch_check(
        self, tmp_path: Path
    ) -> None:
        """read_task with non-integer stem sets file_id=None and skips mismatch guard."""
        content = _TASK_TMPL.format(
            task_id=1,
            title="Task",
            status="todo",
            priority="needed",
            archival_reason="null",
            archival_refs="[]",
            body="Body",
        )
        path = tmp_path / "abc-task.md"  # stem prefix "abc" is non-integer → file_id=None
        path.write_text(content, encoding="utf-8")

        task = read_task(path)

        assert task.id == 1  # no mismatch error despite name prefix ≠ frontmatter id

    def test_read_task_id_filename_mismatch_raises_corruption(
        self, tmp_path: Path
    ) -> None:
        """read_task raises ERR_CORRUPT_ID_FILENAME_MISMATCH when filename id ≠ frontmatter id."""
        content = _TASK_TMPL.format(
            task_id=99,  # frontmatter id=99, but filename says id=1
            title="Task",
            status="todo",
            priority="needed",
            archival_reason="null",
            archival_refs="[]",
            body="Body",
        )
        path = tmp_path / "1-task.md"
        path.write_text(content, encoding="utf-8")

        with pytest.raises(CorruptionError) as exc_info:
            read_task(path)

        assert exc_info.value.code == "ERR_CORRUPT_ID_FILENAME_MISMATCH"

    # ------------------------------------------------------------------
    # save_config
    # ------------------------------------------------------------------

    def test_save_config_roundtrip_persists_next_id(self, tmp_path: Path) -> None:
        """save_config serialises BoardConfig to disk; load_config reads it back."""
        kanban_dir = _make_board(tmp_path)
        config = load_config(kanban_dir)
        config.next_id = 42

        save_config(config, kanban_dir)

        reloaded = load_config(kanban_dir)
        assert reloaded.next_id == 42

    # ------------------------------------------------------------------
    # write_task
    # ------------------------------------------------------------------

    def test_write_task_default_target_dir_writes_to_tasks_dir(
        self, tmp_path: Path
    ) -> None:
        """write_task(..., target_dir=None) writes to tasks/ — backwards-compat default."""
        kanban_dir = _make_board(tmp_path)
        task = Task.model_validate({**_TASK_DICT, "id": 1, "title": "New Task"})

        path = write_task(task, kanban_dir)

        assert path.parent == kanban_dir / "tasks"
        assert path.exists()
        assert path.name.startswith("1-")

    def test_write_task_existing_file_keeps_filename_stable(
        self, tmp_path: Path
    ) -> None:
        """write_task reuses existing filename when a file already exists for the task id."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, task_id=1, title="Task", status="todo", subdir="tasks")

        # Change title to something that would produce a different slug.
        task = Task.model_validate(
            {**_TASK_DICT, "id": 1, "title": "Completely Different Title"}
        )

        path = write_task(task, kanban_dir)

        # Must keep the original slug-based name, not derive a new one from the new title.
        assert path.name == "1-task.md"

    # ------------------------------------------------------------------
    # write_task_if_unchanged
    # ------------------------------------------------------------------

    def test_write_task_if_unchanged_happy_path_writes_task(
        self, tmp_path: Path
    ) -> None:
        """write_task_if_unchanged succeeds when on-disk updated matches expected_updated."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, task_id=1, status="todo", subdir="tasks")
        task_path = kanban_dir / "tasks" / "1-task.md"
        task = read_task(task_path)
        expected_updated = task.updated

        task.priority = "critical"
        write_task_if_unchanged(task, expected_updated, kanban_dir)

        reread = read_task(task_path)
        assert reread.priority == "critical"

    def test_write_task_if_unchanged_stale_raises_concurrency_error(
        self, tmp_path: Path
    ) -> None:
        """write_task_if_unchanged raises ConcurrencyError (ERR_STALE) for stale reads."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, task_id=1, status="todo", subdir="tasks")
        task = read_task(kanban_dir / "tasks" / "1-task.md")

        with pytest.raises(ConcurrencyError) as exc_info:
            write_task_if_unchanged(task, "2020-01-01T00:00:00+00:00", kanban_dir)

        assert exc_info.value.code == "ERR_STALE"

    def test_write_task_if_unchanged_missing_file_raises_file_not_found(
        self, tmp_path: Path
    ) -> None:
        """write_task_if_unchanged raises FileNotFoundError when task file is absent."""
        kanban_dir = _make_board(tmp_path)
        task = Task.model_validate({**_TASK_DICT, "id": 999, "title": "Ghost"})

        with pytest.raises(FileNotFoundError):
            write_task_if_unchanged(task, task.updated, kanban_dir)

    # ------------------------------------------------------------------
    # list_task_files
    # ------------------------------------------------------------------

    def test_list_task_files_empty_tasks_dir_returns_empty_list(
        self, tmp_path: Path
    ) -> None:
        """list_task_files returns [] when tasks/ is empty."""
        kanban_dir = _make_board(tmp_path)

        result = list_task_files(kanban_dir)

        assert result == []

    def test_list_task_files_returns_sorted_md_files_excluding_hidden(
        self, tmp_path: Path
    ) -> None:
        """list_task_files returns sorted .md files, excluding lock and hidden files."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, task_id=2, status="todo", subdir="tasks")
        _write_task(kanban_dir, task_id=1, status="todo", subdir="tasks")
        (kanban_dir / "tasks" / ".1.lock").write_text("", encoding="utf-8")

        result = list_task_files(kanban_dir)

        assert [p.name for p in result] == ["1-task.md", "2-task.md"]

    # ------------------------------------------------------------------
    # list_archive_files
    # ------------------------------------------------------------------

    def test_list_archive_files_empty_archive_dir_returns_empty_list(
        self, tmp_path: Path
    ) -> None:
        """list_archive_files returns [] when archive/ is empty."""
        kanban_dir = _make_board(tmp_path)

        result = list_archive_files(kanban_dir)

        assert result == []

    def test_list_archive_files_returns_sorted_md_files(self, tmp_path: Path) -> None:
        """list_archive_files returns sorted .md files from archive/."""
        kanban_dir = _make_board(tmp_path)
        _write_task(
            kanban_dir,
            task_id=2,
            status="archived",
            archival_reason="completed",
            subdir="archive",
        )
        _write_task(
            kanban_dir,
            task_id=1,
            status="archived",
            archival_reason="completed",
            subdir="archive",
        )

        result = list_archive_files(kanban_dir)

        assert [p.name for p in result] == ["1-task.md", "2-task.md"]

    # ------------------------------------------------------------------
    # move_to_archive
    # ------------------------------------------------------------------

    def test_move_to_archive_happy_path_moves_file(self, tmp_path: Path) -> None:
        """move_to_archive moves the task file from tasks/ to archive/."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, task_id=1, status="done", subdir="tasks")

        dest = move_to_archive(1, kanban_dir)

        assert dest.parent == kanban_dir / "archive"
        assert dest.exists()
        assert not (kanban_dir / "tasks" / "1-task.md").exists()

    def test_move_to_archive_missing_task_raises_file_not_found(
        self, tmp_path: Path
    ) -> None:
        """move_to_archive raises FileNotFoundError when task is absent from tasks/."""
        kanban_dir = _make_board(tmp_path)

        with pytest.raises(FileNotFoundError, match="No task file found"):
            move_to_archive(999, kanban_dir)

    # ------------------------------------------------------------------
    # move_to_quarantine
    # ------------------------------------------------------------------

    def test_move_to_quarantine_happy_path_moves_file(self, tmp_path: Path) -> None:
        """move_to_quarantine moves a task file to quarantine/."""
        kanban_dir = _make_board(tmp_path)
        task_path = _write_task(kanban_dir, task_id=1, status="todo", subdir="tasks")

        dest = move_to_quarantine(task_path, kanban_dir)

        assert dest.parent == kanban_dir / "quarantine"
        assert dest.exists()
        assert not task_path.exists()

    def test_move_to_quarantine_lock_file_is_skipped_and_returned_unchanged(
        self, tmp_path: Path
    ) -> None:
        """move_to_quarantine returns lock files unchanged without moving them."""
        kanban_dir = _make_board(tmp_path)
        lock_file = kanban_dir / "tasks" / ".1.lock"
        lock_file.write_text("", encoding="utf-8")

        result = move_to_quarantine(lock_file, kanban_dir)

        assert result == lock_file
        assert lock_file.exists()
        assert not (kanban_dir / "quarantine").exists()

    # ------------------------------------------------------------------
    # allocate_next_id
    # ------------------------------------------------------------------

    def test_allocate_next_id_returns_current_next_id_and_increments(
        self, tmp_path: Path
    ) -> None:
        """allocate_next_id returns the current next_id and increments it in config."""
        kanban_dir = _make_board(tmp_path)
        config = load_config(kanban_dir)
        expected_id = config.next_id

        result = allocate_next_id(kanban_dir)

        assert result == expected_id
        new_config = load_config(kanban_dir)
        assert new_config.next_id == expected_id + 1

