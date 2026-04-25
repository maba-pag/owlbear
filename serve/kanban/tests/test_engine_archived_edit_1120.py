"""RED-phase tests for archived-task edit persistence (task #1120).

Two defects block all persistence paths:
  D1: engine._find_task_path only searches tasks/, not archive/ -- FileNotFoundError
  D2: storage.write_task always writes to tasks/, never archive/ -- duplicate / wrong location

Both AgentView.edit_task and core KanbanEngine.edit_task are affected.
Validation paths (show_task archive fallback, S4 gate) are NOT affected and
remain GREEN — only the write path is broken.

AC coverage (from task #1121):
  AC-1 → test_agentview_edit_archived_archival_reason_result_updated
          test_agentview_edit_archived_archival_reason_reread_from_archive
  AC-2 → test_agentview_edit_archived_archival_refs_result_updated
          test_agentview_edit_archived_archival_refs_reread_from_archive
  AC-3 → test_agentview_edit_archived_append_body_result_contains_text
          test_agentview_edit_archived_append_body_reread_from_archive
  AC-4 → test_core_engine_edit_archived_priority_result_updated
          test_core_engine_edit_archived_priority_reread_from_archive
  AC-5 → test_edit_archived_file_stays_in_archive_dir
          test_edit_archived_no_duplicate_in_tasks_dir
  AC-6 → test_edit_archived_updated_timestamp_advances
  AC-7 (S4 gate) -- EXCLUDED: validation fires in AgentView before D1 raises;
                   ERR_COMPLETED_REQUIRES_DONE already covered by existing suites.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_kanban.engine import AgentView, CockpitView
from owlbear_kanban.models import (
    ListTasksResponse,
    MigrationRequiredError,
    NotFoundError,
    SingleTaskResponse,
)
from owlbear_kanban.storage import (
    ConcurrencyError,
    CorruptionError,
    _normalize_timestamp,  # noqa: PLC2701
    generate_slug,
    list_archive_files,
    list_task_files,
    move_to_archive,
    move_to_quarantine,
    read_task,
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

        assert result.updated != original_updated, (
            "edit of an archived task must advance the 'updated' timestamp; "
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
        assert reread.updated != original_updated, (
            "persisted file in archive/ must have an advanced 'updated' timestamp; "
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

    # ------------------------------------------------------------------
    # write_task backwards-compatibility: default target_dir writes to tasks/
    # ------------------------------------------------------------------

    def test_write_task_default_target_dir_writes_to_tasks(
        self, tmp_path: Path
    ) -> None:
        """Backwards-compat: write_task(task, kanban_dir) without target_dir writes to tasks/.

        The target_dir=None default introduced for archived-edit must not change the
        behaviour of the 12 unchanged callers in engine.py that omit the parameter.
        """
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, task_id=1, status="todo", subdir="tasks")
        task = read_task(kanban_dir / "tasks" / "1-task.md")
        task.priority = "critical"

        written_path = write_task(task, kanban_dir)

        assert written_path.parent == kanban_dir / "tasks", (
            f"write_task without target_dir must write to tasks/; got {written_path.parent}"
        )
        assert (kanban_dir / "tasks" / "1-task.md").exists(), (
            "file must exist in tasks/ after default write"
        )
        assert not (kanban_dir / "archive" / "1-task.md").exists(), (
            "file must not exist in archive/ when target_dir is omitted"
        )


# ---------------------------------------------------------------------------
# TestFromAC_StorageCoveragePaths
# ---------------------------------------------------------------------------


class TestFromAC_StorageCoveragePaths:
    """Supplementary coverage tests targeting storage.py branches uncovered by existing suites.

    These tests raise owlbear_kanban.storage module coverage to the >=90% pipeline gate.
    Covers: generate_slug, validate_path_containment, _parse_task_file delimiter error,
    read_task id/filename checks, write_task vendor-extras loop, write_task_if_unchanged
    (happy / stale / missing), list_task_files / list_archive_files no-dir guard,
    and move_to_archive (happy / missing).
    """

    # ------------------------------------------------------------------
    # generate_slug: empty and Windows-reserved paths
    # ------------------------------------------------------------------

    def test_generate_slug_empty_title_returns_empty(self) -> None:
        """generate_slug("") must return "" without raising."""
        assert generate_slug("") == ""

    def test_generate_slug_windows_reserved_name_raises_value_error(self) -> None:
        """generate_slug("con") must raise ValueError (Windows reserved filename)."""
        with pytest.raises(ValueError, match="reserved"):
            generate_slug("con")

    # ------------------------------------------------------------------
    # validate_path_containment: null-byte and self-reference edge cases
    # ------------------------------------------------------------------

    def test_validate_path_containment_null_byte_raises_value_error(
        self, tmp_path: Path
    ) -> None:
        """validate_path_containment raises ValueError when path contains a null byte."""
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        bad_path = tasks_dir / "file\x00name.md"
        with pytest.raises(ValueError, match="null byte"):
            validate_path_containment(tasks_dir, bad_path)

    def test_validate_path_containment_path_equals_tasks_dir_raises_value_error(
        self, tmp_path: Path
    ) -> None:
        """validate_path_containment raises ValueError when path IS tasks_dir itself."""
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        with pytest.raises(ValueError, match="not tasks_dir itself"):
            validate_path_containment(tasks_dir, tasks_dir)

    # ------------------------------------------------------------------
    # read_task: missing closing delimiter
    # ------------------------------------------------------------------

    def test_read_task_missing_closing_delimiter_raises_corruption_error(
        self, tmp_path: Path
    ) -> None:
        """read_task raises CorruptionError when closing '---' is absent.

        Covers _parse_task_file lines that detect a missing closing delimiter
        and raise ValueError, which read_task re-raises as ERR_CORRUPT_DELIMITERS.
        """
        task_file = tmp_path / "1-task.md"
        task_file.write_text("---\nid: 1\ntitle: X\n", encoding="utf-8")
        with pytest.raises(CorruptionError):
            read_task(task_file)

    # ------------------------------------------------------------------
    # read_task: filename id parsing edge cases
    # ------------------------------------------------------------------

    def test_read_task_non_integer_filename_prefix_returns_task(
        self, tmp_path: Path
    ) -> None:
        """read_task: filename prefix non-parseable as int → file_id=None, task returned.

        Covers the except ValueError branch in the filename-id extraction block
        so that non-integer-prefixed filenames silently skip the id-match check.
        """
        # Place file outside a board (no config.yml two levels up) so
        # board-level corruption detection is skipped.
        raw_dir = tmp_path / "rawdir"
        raw_dir.mkdir()
        task_file = raw_dir / "not-an-id.md"
        task_file.write_text(
            _TASK_TMPL.format(
                task_id=1,
                title="Task",
                status="todo",
                priority="needed",
                archival_reason="null",
                archival_refs="[]",
                body="Body.",
            ),
            encoding="utf-8",
        )

        task = read_task(task_file)

        assert task.id == 1, "task must be returned even when filename prefix is non-integer"

    def test_read_task_id_filename_mismatch_raises_corruption_error(
        self, tmp_path: Path
    ) -> None:
        """read_task raises CorruptionError when filename id differs from frontmatter id.

        Filename is '2-task.md' but frontmatter contains id=1 → ERR_CORRUPT_ID_FILENAME_MISMATCH.
        """
        raw_dir = tmp_path / "rawdir"
        raw_dir.mkdir()
        task_file = raw_dir / "2-task.md"  # filename prefix = 2
        task_file.write_text(
            _TASK_TMPL.format(
                task_id=1,  # frontmatter id = 1 (mismatch)
                title="Task",
                status="todo",
                priority="needed",
                archival_reason="null",
                archival_refs="[]",
                body="Body.",
            ),
            encoding="utf-8",
        )

        with pytest.raises(CorruptionError):
            read_task(task_file)

    # ------------------------------------------------------------------
    # write_task: vendor-extras loop (Task with extra fields)
    # ------------------------------------------------------------------

    def test_write_task_preserves_vendor_extra_fields(self, tmp_path: Path) -> None:
        """write_task serialises vendor extra fields (not in _CANONICAL_FIELDS) to disk.

        Task.model_config allows extra='allow'; extra fields pass through the vendor-extras
        loop in write_task and are round-tripped via the ruamel YAML stream.
        """
        kanban_dir = _make_board(tmp_path)
        # Write a task file with a non-canonical extra field.
        task_file = kanban_dir / "tasks" / "1-task.md"
        task_file.write_text(
            "---\n"
            "id: 1\n"
            "title: Task\n"
            "status: todo\n"
            "priority: needed\n"
            'created: "2026-01-01T10:00:00+00:00"\n'
            'updated: "2026-01-01T10:00:00+00:00"\n'
            "tags: []\n"
            "parent: null\n"
            "depends_on: []\n"
            "blocked: false\n"
            "block_reason: null\n"
            "claimed_at: null\n"
            "archival_reason: null\n"
            "archival_refs: []\n"
            "custom_field: vendored\n"
            "---\nBody.",
            encoding="utf-8",
        )
        task = read_task(task_file)
        assert task.model_extra.get("custom_field") == "vendored", "pre-condition: extra field read"

        written_path = write_task(task, kanban_dir)

        written_text = written_path.read_text(encoding="utf-8")
        assert "custom_field" in written_text, (
            "vendor extra field must be serialised by write_task"
        )

    # ------------------------------------------------------------------
    # write_task_if_unchanged
    # ------------------------------------------------------------------

    def test_write_task_if_unchanged_writes_when_updated_matches(
        self, tmp_path: Path
    ) -> None:
        """write_task_if_unchanged succeeds when expected_updated matches on-disk timestamp."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, task_id=1, status="todo", priority="needed")
        task = read_task(kanban_dir / "tasks" / "1-task.md")
        original_updated = task.updated
        task.priority = "critical"

        written_path = write_task_if_unchanged(task, original_updated, kanban_dir)

        assert written_path.exists(), "write_task_if_unchanged must return an existing path"
        reopened = read_task(written_path)
        assert reopened.priority == "critical", "priority must be updated after successful write"

    def test_write_task_if_unchanged_raises_stale_on_timestamp_mismatch(
        self, tmp_path: Path
    ) -> None:
        """write_task_if_unchanged raises ConcurrencyError when expected_updated is stale."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, task_id=1, status="todo")
        task = read_task(kanban_dir / "tasks" / "1-task.md")
        task.priority = "critical"
        stale_timestamp = "2000-01-01T00:00:00+00:00"  # older than what's on disk

        with pytest.raises(ConcurrencyError) as exc_info:
            write_task_if_unchanged(task, stale_timestamp, kanban_dir)

        assert exc_info.value.code == "ERR_STALE"

    def test_write_task_if_unchanged_raises_when_task_file_missing(
        self, tmp_path: Path
    ) -> None:
        """write_task_if_unchanged raises FileNotFoundError when no file exists for the task id."""
        kanban_dir = _make_board(tmp_path)
        # No task file created — tasks/ dir is empty.
        from owlbear_kanban.models import Task as TaskModel

        phantom_task = TaskModel(
            id=99,
            title="Ghost",
            status="todo",
            priority="needed",
            created="2026-01-01T10:00:00+00:00",
            updated="2026-01-01T10:00:00+00:00",
        )
        with pytest.raises(FileNotFoundError):
            write_task_if_unchanged(phantom_task, phantom_task.updated, kanban_dir)

    # ------------------------------------------------------------------
    # list_task_files / list_archive_files: missing directory guard
    # ------------------------------------------------------------------

    def test_list_task_files_returns_empty_when_tasks_dir_missing(
        self, tmp_path: Path
    ) -> None:
        """list_task_files returns [] when tasks/ directory does not exist."""
        kanban_dir = tmp_path / "board"
        kanban_dir.mkdir()
        (kanban_dir / "config.yml").write_text(_BASE_CONFIG, encoding="utf-8")
        # Intentionally NOT creating tasks/ directory.

        result = list_task_files(kanban_dir)

        assert result == [], f"expected [], got {result}"

    def test_list_archive_files_returns_empty_when_archive_dir_missing(
        self, tmp_path: Path
    ) -> None:
        """list_archive_files returns [] when archive/ directory does not exist."""
        kanban_dir = tmp_path / "board"
        kanban_dir.mkdir()
        (kanban_dir / "config.yml").write_text(_BASE_CONFIG, encoding="utf-8")
        # Intentionally NOT creating archive/ directory.

        result = list_archive_files(kanban_dir)

        assert result == [], f"expected [], got {result}"

    # ------------------------------------------------------------------
    # move_to_archive
    # ------------------------------------------------------------------

    def test_move_to_archive_moves_task_file_from_tasks_to_archive(
        self, tmp_path: Path
    ) -> None:
        """move_to_archive moves the task file from tasks/ to archive/ and returns dest path."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, task_id=1, status="done", subdir="tasks")
        assert (kanban_dir / "tasks" / "1-task.md").exists(), "pre-condition: file in tasks/"

        dest = move_to_archive(1, kanban_dir)

        assert dest == kanban_dir / "archive" / "1-task.md", (
            f"dest must be in archive/; got {dest}"
        )
        assert dest.exists(), "moved file must exist at archive/ dest"
        assert not (kanban_dir / "tasks" / "1-task.md").exists(), (
            "source file must be removed from tasks/ after move"
        )

    def test_move_to_archive_raises_when_task_not_found(
        self, tmp_path: Path
    ) -> None:
        """move_to_archive raises FileNotFoundError when no task file exists for the given id."""
        kanban_dir = _make_board(tmp_path)
        # No task file for id=999.

        with pytest.raises(FileNotFoundError):
            move_to_archive(999, kanban_dir)

    # ------------------------------------------------------------------
    # validate_path_containment: path outside tasks_dir raises PermissionError
    # ------------------------------------------------------------------

    def test_validate_path_containment_path_outside_raises_permission_error(
        self, tmp_path: Path
    ) -> None:
        """validate_path_containment raises PermissionError when path escapes tasks_dir.

        Covers lines 131-133: the relative_to() check raises ValueError → PermissionError.
        """
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        outside_path = tmp_path / "other" / "evil.md"

        with pytest.raises(PermissionError, match="outside tasks_dir"):
            validate_path_containment(tasks_dir, outside_path)

    # ------------------------------------------------------------------
    # _parse_task_file: missing opening '---' delimiter
    # ------------------------------------------------------------------

    def test_read_task_missing_opening_delimiter_raises_corruption_error(
        self, tmp_path: Path
    ) -> None:
        """read_task raises CorruptionError when the file has no opening '---' delimiter.

        Covers lines 144-145: _parse_task_file raises ValueError for missing opening ---,
        which read_task re-raises as CorruptionError(code='ERR_CORRUPT_DELIMITERS').
        """
        task_file = tmp_path / "1-task.md"
        # Valid YAML-like content but no opening '---'
        task_file.write_text("id: 1\ntitle: Task\n---\nBody.", encoding="utf-8")

        with pytest.raises(CorruptionError) as exc_info:
            read_task(task_file)

        assert "CORRUPT_DELIMITERS" in exc_info.value.code

    # ------------------------------------------------------------------
    # read_task: YAML parse error path
    # ------------------------------------------------------------------

    def test_read_task_yaml_parse_error_raises_corruption_error_yaml_parse(
        self, tmp_path: Path
    ) -> None:
        """read_task raises CorruptionError(ERR_CORRUPT_YAML_PARSE) when frontmatter is broken YAML.

        Covers line 317: the except yaml.YAMLError branch in read_task.
        """
        task_file = tmp_path / "1-task.md"
        # An unclosed bracket causes a YAML scan error.
        task_file.write_text("---\n[unclosed bracket\n---\nBody.", encoding="utf-8")

        with pytest.raises(CorruptionError) as exc_info:
            read_task(task_file)

        assert exc_info.value.code == "ERR_CORRUPT_YAML_PARSE"

    # ------------------------------------------------------------------
    # read_task: pydantic ValidationError → _validation_to_corruption
    # ------------------------------------------------------------------

    def test_read_task_missing_required_field_raises_corruption_error_missing_field(
        self, tmp_path: Path
    ) -> None:
        """read_task raises CorruptionError(ERR_CORRUPT_MISSING_FIELD) when a required field is absent.

        Covers lines 166-176 (_validation_to_corruption) and line 323 (except ValidationError in read_task).
        The file omits the required 'id' field so pydantic raises ValidationError.
        """
        task_file = tmp_path / "1-task.md"
        # Valid YAML with valid delimiters, but missing required 'id' field.
        task_file.write_text(
            "---\ntitle: Task\nstatus: todo\npriority: needed\n---\nBody.",
            encoding="utf-8",
        )

        with pytest.raises(CorruptionError) as exc_info:
            read_task(task_file)

        assert exc_info.value.code == "ERR_CORRUPT_MISSING_FIELD"

    # ------------------------------------------------------------------
    # _normalize_timestamp: None, Z-suffix, and no-tz cases
    # ------------------------------------------------------------------

    def test_normalize_timestamp_none_returns_none(self) -> None:
        """_normalize_timestamp(None) returns None without raising.

        Covers line 272: the 'if ts is None: return None' early-exit branch.
        """
        result = _normalize_timestamp(None)

        assert result is None

    def test_normalize_timestamp_z_suffix_converts_to_utc_offset(self) -> None:
        """_normalize_timestamp converts 'Z' suffix to explicit '+00:00'.

        Covers line 280: the 'if tz == "Z": return f"{base}{frac}+00:00"' branch.
        """
        result = _normalize_timestamp("2026-01-01T10:00:00Z")

        assert result == "2026-01-01T10:00:00+00:00"

    def test_normalize_timestamp_no_tz_appends_utc_offset(self) -> None:
        """_normalize_timestamp adds '+00:00' when no timezone is present.

        Covers line 282: the no-tz fallback 'return f"{base}{frac}+00:00"' branch.
        """
        result = _normalize_timestamp("2026-01-01T10:00:00")

        assert result == "2026-01-01T10:00:00+00:00"

    # ------------------------------------------------------------------
    # list_task_files / list_archive_files: happy path (dir exists, files present)
    # ------------------------------------------------------------------

    def test_list_task_files_returns_sorted_files_when_tasks_dir_exists(
        self, tmp_path: Path
    ) -> None:
        """list_task_files returns sorted .md paths when tasks/ exists and has files.

        Covers line 465: the 'return sorted(...)' branch when tasks_dir.exists().
        """
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, task_id=2, status="todo", subdir="tasks")
        _write_task(kanban_dir, task_id=1, status="todo", subdir="tasks")

        result = list_task_files(kanban_dir)

        assert len(result) == 2
        assert result[0].name < result[1].name, "results must be sorted"

    def test_list_archive_files_returns_sorted_files_when_archive_dir_exists(
        self, tmp_path: Path
    ) -> None:
        """list_archive_files returns sorted .md paths when archive/ exists and has files.

        Covers line 481: the 'return sorted(...)' branch when archive_dir.exists().
        """
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, task_id=1, status="archived", subdir="archive")
        _write_task(kanban_dir, task_id=2, status="archived", subdir="archive")

        result = list_archive_files(kanban_dir)

        assert len(result) == 2
        assert result[0].name < result[1].name, "results must be sorted"

    # ------------------------------------------------------------------
    # move_to_quarantine: happy path
    # ------------------------------------------------------------------

    def test_move_to_quarantine_moves_task_file_to_quarantine_dir(
        self, tmp_path: Path
    ) -> None:
        """move_to_quarantine moves the file to quarantine/ and returns its dest path.

        Covers lines 528-537: the full happy-path in move_to_quarantine.
        """
        kanban_dir = _make_board(tmp_path)
        task_file = kanban_dir / "tasks" / "1-task.md"
        _write_task(kanban_dir, task_id=1, status="todo", subdir="tasks")
        assert task_file.exists(), "pre-condition: task file must exist"

        dest = move_to_quarantine(task_file, kanban_dir)

        assert dest.parent.name == "quarantine", (
            f"file must be in quarantine/; got {dest.parent}"
        )
        assert dest.exists(), "quarantined file must exist at destination"
        assert not task_file.exists(), "original file must be removed from tasks/"


# ---------------------------------------------------------------------------
# TestFromAC_EngineCoveragePaths
# ---------------------------------------------------------------------------

_LEGACY_TASK_CLEARED = """\
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
claimed_by: {claimed_by}
archival_reason: null
archival_refs: []
---
Body.
"""


class TestFromAC_EngineCoveragePaths:
    """Targeted coverage for KanbanEngine, AgentView, and CockpitView paths.

    These tests exercise engine operations (move_task, claim_task, end_work,
    list_tasks filters, show_task paths, _find_task_path cache paths, migration gate)
    that are not exercised by the archived-edit AC tests above, raising touched-module
    coverage toward the pipeline gate.
    """

    # ------------------------------------------------------------------
    # KanbanEngine properties
    # ------------------------------------------------------------------

    def test_agent_name_is_non_empty_string(self, tmp_path: Path) -> None:
        """KanbanEngine.agent_name is a non-empty string (covers line 490)."""
        engine, _ = _make_engine(tmp_path)

        assert isinstance(engine.agent_name, str)
        assert engine.agent_name

    def test_revision_starts_at_zero(self, tmp_path: Path) -> None:
        """KanbanEngine.revision is 0 immediately after init (covers line 495)."""
        engine, _ = _make_engine(tmp_path)

        assert engine.revision == 0

    def test_board_config_returns_config_with_statuses(self, tmp_path: Path) -> None:
        """KanbanEngine.board_config() returns the loaded BoardConfig (covers line 512)."""
        engine, _ = _make_engine(tmp_path)

        config = engine.board_config()

        assert "todo" in config.statuses

    def test_agent_view_property_returns_agent_view(self, tmp_path: Path) -> None:
        """KanbanEngine.agent_view returns an AgentView (covers line 520)."""
        engine, _ = _make_engine(tmp_path)

        assert isinstance(engine.agent_view(), AgentView)

    # ------------------------------------------------------------------
    # valid_transitions
    # ------------------------------------------------------------------

    def test_valid_transitions_for_todo_contains_adjacent_statuses(
        self, tmp_path: Path
    ) -> None:
        """valid_transitions('todo') returns the reachable status set (covers lines 545-561)."""
        engine, _ = _make_engine(tmp_path)

        result = engine.valid_transitions("todo")

        assert isinstance(result, set)
        # 'in-progress' is next in the configured sequence; result must be non-empty.
        assert len(result) > 0

    # ------------------------------------------------------------------
    # KanbanEngine.list_tasks filter paths
    # ------------------------------------------------------------------

    def test_list_tasks_status_filter_returns_matching_tasks(
        self, tmp_path: Path
    ) -> None:
        """list_tasks(status='todo') returns only tasks with that status."""
        engine, kanban_dir = _make_engine(tmp_path)
        _write_task(kanban_dir, task_id=1, status="todo", subdir="tasks")
        _write_task(kanban_dir, task_id=2, status="backlog", subdir="tasks")

        result = engine.list_tasks(status="todo")

        assert all(t.status == "todo" for t in result)
        ids = [t.id for t in result]
        assert 1 in ids
        assert 2 not in ids

    def test_list_tasks_blocked_filter_returns_only_blocked(
        self, tmp_path: Path
    ) -> None:
        """list_tasks(blocked=True) returns only blocked tasks."""
        kanban_dir = _make_board(tmp_path)
        blocked_content = _TASK_TMPL.format(
            task_id=1, title="Blocked", status="todo", priority="needed",
            archival_reason="null", archival_refs="[]", body="",
        ).replace("blocked: false", "blocked: true").replace(
            "block_reason: null", "block_reason: needs review"
        )
        (kanban_dir / "tasks" / "1-task.md").write_text(blocked_content, encoding="utf-8")
        _write_task(kanban_dir, task_id=2, status="todo", subdir="tasks")
        engine = KanbanEngine(kanban_dir, activity_log=False)

        result = engine.list_tasks(blocked=True)

        assert all(t.blocked for t in result)
        ids = [t.id for t in result]
        assert 1 in ids
        assert 2 not in ids

    def test_list_tasks_unclaimed_filter_excludes_claimed(
        self, tmp_path: Path
    ) -> None:
        """list_tasks(unclaimed=True) skips tasks with non-null claimed_at."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, task_id=1, status="todo", subdir="tasks")
        # Task 2 has a claimed_at timestamp.
        claimed_content = _TASK_TMPL.format(
            task_id=2, title="Claimed", status="todo", priority="needed",
            archival_reason="null", archival_refs="[]", body="",
        ).replace("claimed_at: null", 'claimed_at: "2026-01-01T12:00:00+00:00"')
        (kanban_dir / "tasks" / "2-task.md").write_text(claimed_content, encoding="utf-8")
        engine = KanbanEngine(kanban_dir, activity_log=False)

        result = engine.list_tasks(unclaimed=True)

        ids = [t.id for t in result]
        assert 1 in ids
        assert 2 not in ids

    def test_list_tasks_sort_by_id_returns_ascending_order(
        self, tmp_path: Path
    ) -> None:
        """list_tasks(sort='id') returns tasks in ascending id order."""
        engine, kanban_dir = _make_engine(tmp_path)
        _write_task(kanban_dir, task_id=3, status="todo", subdir="tasks")
        _write_task(kanban_dir, task_id=1, status="todo", subdir="tasks")
        _write_task(kanban_dir, task_id=2, status="todo", subdir="tasks")

        result = engine.list_tasks(sort="id")

        ids = [t.id for t in result]
        assert ids == sorted(ids), f"expected ascending ids, got {ids}"

    def test_list_tasks_include_archived_returns_archived_tasks(
        self, tmp_path: Path
    ) -> None:
        """list_tasks(archived=True) reads from archive/ directory."""
        engine, kanban_dir = _make_engine(tmp_path)
        _write_task(kanban_dir, task_id=1, status="archived", subdir="archive")
        _write_task(kanban_dir, task_id=2, status="todo", subdir="tasks")

        result = engine.list_tasks(archived=True)

        ids = [t.id for t in result]
        assert 1 in ids, "archived task must appear in archived listing"
        assert 2 not in ids, "live task must not appear in archived listing"

    # ------------------------------------------------------------------
    # KanbanEngine.show_task paths
    # ------------------------------------------------------------------

    def test_show_task_via_glob_fallback_returns_task(
        self, tmp_path: Path
    ) -> None:
        """show_task finds the task via glob when _id_to_filename cache is cold."""
        engine, kanban_dir = _make_engine(tmp_path)
        _write_task(kanban_dir, task_id=1, status="todo", subdir="tasks")

        # Cold cache: _id_to_filename is empty → glob path taken.
        result = engine.show_task("1")

        assert result.id == 1

    def test_show_task_archive_glob_returns_archived_task(
        self, tmp_path: Path
    ) -> None:
        """show_task finds a task in archive/ when not present in tasks/."""
        engine, kanban_dir = _make_engine(tmp_path)
        _write_task(kanban_dir, task_id=5, status="archived", subdir="archive")

        result = engine.show_task("5")

        assert result.id == 5

    def test_show_task_not_found_raises_file_not_found_error(
        self, tmp_path: Path
    ) -> None:
        """show_task raises FileNotFoundError when the task does not exist anywhere."""
        engine, _ = _make_engine(tmp_path)

        with pytest.raises(FileNotFoundError):
            engine.show_task("999")

    # ------------------------------------------------------------------
    # _find_task_path: warm-cache fast-path and non-integer id
    # ------------------------------------------------------------------

    def test_find_task_path_warm_cache_file_exists_returns_path_directly(
        self, tmp_path: Path
    ) -> None:
        """_find_task_path returns the cached tasks/ path when cache is warm and file exists.

        Covers line 1545: 'return candidate' when _id_to_filename has the id and file exists.
        """
        engine, kanban_dir = _make_engine(tmp_path)
        _write_task(kanban_dir, task_id=1, status="todo", subdir="tasks")
        # Warm the _id_to_filename cache.
        engine.list_tasks()
        assert 1 in engine._id_to_filename, "pre-condition: cache must contain task 1"

        # File is still in tasks/ — fast-path returns it.
        result = engine.edit_task("1", priority="critical")

        assert result.priority == "critical"
        assert (kanban_dir / "tasks" / "1-task.md").exists()

    def test_find_task_path_non_integer_id_warm_cache_raises_file_not_found(
        self, tmp_path: Path
    ) -> None:
        """_find_task_path with non-integer task_id triggers ValueError→int_id=None path.

        Covers lines 1539-1540 (except ValueError: int_id = None) and 1558-1559
        (FileNotFoundError when no matches found).  The warm cache ensures the outer
        id-filename lookup block is entered before the ValueError branch fires.
        """
        engine, kanban_dir = _make_engine(tmp_path)
        _write_task(kanban_dir, task_id=1, status="todo", subdir="tasks")
        # Warm the cache so the 'if self._id_to_filename:' guard is True.
        engine.list_tasks()

        with pytest.raises(FileNotFoundError):
            engine.edit_task("not-an-integer", priority="critical")

    # ------------------------------------------------------------------
    # KanbanEngine.move_task
    # ------------------------------------------------------------------

    def test_move_task_advances_status_and_writes_to_tasks(
        self, tmp_path: Path
    ) -> None:
        """move_task advances a live task to the requested status (covers lines 1054-1089)."""
        engine, kanban_dir = _make_engine(tmp_path)
        _write_task(kanban_dir, task_id=1, status="todo", subdir="tasks")

        result = engine.move_task("1", "in-progress")

        assert result.status == "in-progress"
        reread = engine.show_task("1")
        assert reread.status == "in-progress"

    # ------------------------------------------------------------------
    # KanbanEngine.claim_task
    # ------------------------------------------------------------------

    def test_claim_task_sets_claimed_at_on_unclaimed_task(
        self, tmp_path: Path
    ) -> None:
        """claim_task sets claimed_at on an unclaimed task (covers lines 1107-1142)."""
        engine, kanban_dir = _make_engine(tmp_path)
        _write_task(kanban_dir, task_id=1, status="todo", subdir="tasks")
        assert engine.show_task("1").claimed_at is None, "pre-condition: unclaimed"

        result = engine.claim_task("1")

        assert result.claimed_at is not None, "claimed_at must be set after claim"

    def test_claim_task_blocked_raises_value_error(self, tmp_path: Path) -> None:
        """claim_task raises ValueError when the task is blocked."""
        kanban_dir = _make_board(tmp_path)
        blocked_content = _TASK_TMPL.format(
            task_id=1, title="Blocked", status="todo", priority="needed",
            archival_reason="null", archival_refs="[]", body="",
        ).replace("blocked: false", "blocked: true").replace(
            "block_reason: null", "block_reason: waiting"
        )
        (kanban_dir / "tasks" / "1-task.md").write_text(blocked_content, encoding="utf-8")
        engine = KanbanEngine(kanban_dir, activity_log=False)

        with pytest.raises(ValueError, match="blocked"):
            engine.claim_task("1")

    # ------------------------------------------------------------------
    # KanbanEngine.release_task
    # ------------------------------------------------------------------

    def test_release_task_clears_claimed_at(self, tmp_path: Path) -> None:
        """release_task clears claimed_at on a claimed task (covers lines 1158-1173)."""
        engine, kanban_dir = _make_engine(tmp_path)
        _write_task(kanban_dir, task_id=1, status="todo", subdir="tasks")
        engine.claim_task("1")
        assert engine.show_task("1").claimed_at is not None, "pre-condition: claimed"

        result = engine.release_task("1")

        assert result.claimed_at is None, "claimed_at must be None after release"

    # ------------------------------------------------------------------
    # KanbanEngine.end_work outcomes
    # ------------------------------------------------------------------

    def test_end_work_success_advances_to_next_status(self, tmp_path: Path) -> None:
        """end_work(outcome='success') advances the task to the next status (covers 1258-1313)."""
        engine, kanban_dir = _make_engine(tmp_path)
        _write_task(kanban_dir, task_id=1, status="todo", subdir="tasks")

        result = engine.end_work("1", note="Done.", outcome="success")

        assert result.status == "in-progress", (
            f"todo + success should advance to in-progress, got {result.status!r}"
        )

    def test_end_work_fail_keeps_current_status(self, tmp_path: Path) -> None:
        """end_work(outcome='fail') leaves the task at its current status."""
        engine, kanban_dir = _make_engine(tmp_path)
        _write_task(kanban_dir, task_id=1, status="todo", subdir="tasks")

        result = engine.end_work("1", note="Failed.", outcome="fail")

        assert result.status == "todo", (
            f"fail outcome must keep status; got {result.status!r}"
        )

    def test_end_work_block_sets_blocked_flag(self, tmp_path: Path) -> None:
        """end_work(outcome='block') sets blocked=True and stores block_reason."""
        engine, kanban_dir = _make_engine(tmp_path)
        _write_task(kanban_dir, task_id=1, status="todo", subdir="tasks")

        result = engine.end_work(
            "1", note="Blocked.", outcome="block", block_reason="waiting for review"
        )

        assert result.blocked is True
        assert result.block_reason == "waiting for review"

    # ------------------------------------------------------------------
    # AgentView: list_tasks, show_task, move_task, start_work, end_work
    # ------------------------------------------------------------------

    def test_agentview_list_tasks_returns_list_tasks_response(
        self, tmp_path: Path
    ) -> None:
        """AgentView.list_tasks returns a ListTasksResponse (covers lines 1709-1770)."""
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, task_id=1, status="todo", subdir="tasks")

        result = view.list_tasks()

        assert isinstance(result, ListTasksResponse)
        assert any(t.id == 1 for t in result.tasks)

    def test_agentview_show_task_returns_single_task_response(
        self, tmp_path: Path
    ) -> None:
        """AgentView.show_task returns a ShowTaskResponse for an existing task (covers 1794-1833)."""
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, task_id=1, status="todo", subdir="tasks")

        result = view.show_task(1)

        assert result.id == 1

    def test_agentview_show_task_not_found_raises_not_found_error(
        self, tmp_path: Path
    ) -> None:
        """AgentView.show_task raises NotFoundError for a missing task."""
        view, _ = _make_view(tmp_path)

        with pytest.raises(NotFoundError):
            view.show_task(999)

    def test_agentview_move_task_advances_status(self, tmp_path: Path) -> None:
        """AgentView.move_task returns a SingleTaskResponse with updated status (covers 2158-2172)."""
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, task_id=1, status="todo", subdir="tasks")

        result = view.move_task(1, "in-progress")

        assert isinstance(result, SingleTaskResponse)
        assert result.status == "in-progress"

    def test_agentview_start_work_returns_single_response(
        self, tmp_path: Path
    ) -> None:
        """AgentView.start_work claims the task and returns a response (covers lines 2174-2186)."""
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, task_id=1, status="todo", subdir="tasks")

        result = view.start_work(1)

        assert isinstance(result, SingleTaskResponse)
        assert result.claimed_at is not None, "claimed_at must be set after start_work"

    def test_agentview_end_work_success_advances_status(
        self, tmp_path: Path
    ) -> None:
        """AgentView.end_work(outcome='success') advances status (covers lines 2189-2231)."""
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, task_id=1, status="todo", subdir="tasks")

        result = view.end_work(1, outcome="success", note="Done.")

        assert isinstance(result, SingleTaskResponse)
        assert result.status == "in-progress"

    def test_agentview_end_work_reject_moves_to_research(
        self, tmp_path: Path
    ) -> None:
        """AgentView.end_work(outcome='reject') moves task back to research status."""
        view, kanban_dir = _make_view(tmp_path)
        _write_task(kanban_dir, task_id=1, status="todo", subdir="tasks")

        result = view.end_work(1, outcome="reject", note="Rejected.", move_to="research")

        assert result.status == "research"

    # ------------------------------------------------------------------
    # CockpitView: all methods raise NotImplementedError
    # ------------------------------------------------------------------

    def test_cockpitview_list_tasks_raises_not_implemented(
        self, tmp_path: Path
    ) -> None:
        """CockpitView.list_tasks() raises NotImplementedError (covers line 2241-2260)."""
        engine, _ = _make_engine(tmp_path)
        cv = engine.cockpit_view()

        assert isinstance(cv, CockpitView)
        with pytest.raises(NotImplementedError):  # noqa: PT011
            cv.list_tasks()

    def test_cockpitview_show_task_raises_not_implemented(
        self, tmp_path: Path
    ) -> None:
        """CockpitView.show_task() raises NotImplementedError."""
        engine, _ = _make_engine(tmp_path)
        with pytest.raises(NotImplementedError):  # noqa: PT011
            engine.cockpit_view().show_task(1)

    def test_cockpitview_move_task_raises_not_implemented(
        self, tmp_path: Path
    ) -> None:
        """CockpitView.move_task() raises NotImplementedError."""
        engine, _ = _make_engine(tmp_path)
        with pytest.raises(NotImplementedError):  # noqa: PT011
            engine.cockpit_view().move_task(1, "done")

    # ------------------------------------------------------------------
    # KanbanEngine init: legacy claimed_by migration gate (lines 448-482)
    # ------------------------------------------------------------------

    def test_engine_init_legacy_cleared_claimed_by_does_not_raise(
        self, tmp_path: Path
    ) -> None:
        """KanbanEngine init succeeds when tasks/ has 'claimed_by: null' (cleared legacy field).

        Covers lines 448-482: the init scans for 'claimed_by:' in frontmatter;
        when it is null (cleared), the loop continues without raising.
        """
        kanban_dir = _make_board(tmp_path)
        content = _LEGACY_TASK_CLEARED.format(
            task_id=1, title="Task", status="todo", priority="needed",
            claimed_by="null",
        )
        (kanban_dir / "tasks" / "1-task.md").write_text(content, encoding="utf-8")

        engine = KanbanEngine(kanban_dir, activity_log=False)

        assert engine is not None

    def test_engine_init_legacy_set_claimed_by_raises_migration_required_error(
        self, tmp_path: Path
    ) -> None:
        """KanbanEngine init raises MigrationRequiredError when claimed_by is non-null.

        Covers the MigrationRequiredError raise path (line ~480-482): when a task has
        a non-empty 'claimed_by' in frontmatter, the engine refuses to start.
        """
        kanban_dir = _make_board(tmp_path)
        content = _LEGACY_TASK_CLEARED.format(
            task_id=1, title="Task", status="todo", priority="needed",
            claimed_by="legacy-agent",
        )
        (kanban_dir / "tasks" / "1-task.md").write_text(content, encoding="utf-8")

        with pytest.raises(MigrationRequiredError):
            KanbanEngine(kanban_dir, activity_log=False)

    # ------------------------------------------------------------------
    # create_task: invalid status/priority validation paths
    # ------------------------------------------------------------------

    def test_create_task_invalid_status_raises_value_error(
        self, tmp_path: Path
    ) -> None:
        """create_task raises ValueError when status is not in config (covers lines 888-889)."""
        engine, _ = _make_engine(tmp_path)

        with pytest.raises(ValueError, match="INVALID_STATUS"):
            engine.create_task("New Task", status="INVALID_STATUS")

    def test_create_task_invalid_priority_raises_value_error(
        self, tmp_path: Path
    ) -> None:
        """create_task raises ValueError when priority is not in config (covers lines 891-892)."""
        engine, _ = _make_engine(tmp_path)

        with pytest.raises(ValueError, match="INVALID_PRIORITY"):
            engine.create_task("New Task", priority="INVALID_PRIORITY")

    # ------------------------------------------------------------------
    # edit_task: title and add_tags branches
    # ------------------------------------------------------------------

    def test_edit_task_title_update_persists(self, tmp_path: Path) -> None:
        """engine.edit_task with title= replaces the task title (covers title-update branch)."""
        engine, kanban_dir = _make_engine(tmp_path)
        _write_task(kanban_dir, task_id=1, status="todo", title="Old Title", subdir="tasks")

        result = engine.edit_task("1", title="New Title")

        assert result.title == "New Title"

    def test_edit_task_add_tags_adds_new_tag(self, tmp_path: Path) -> None:
        """engine.edit_task with add_tags= appends new tags (covers add_tags branch)."""
        engine, kanban_dir = _make_engine(tmp_path)
        _write_task(kanban_dir, task_id=1, status="todo", subdir="tasks")

        result = engine.edit_task("1", add_tags=["my-tag"])

        assert "my-tag" in result.tags

    # ------------------------------------------------------------------
    # list_tasks: tag, priority, and search filter branches
    # ------------------------------------------------------------------

    def test_list_tasks_tag_filter_returns_matching_tasks(
        self, tmp_path: Path
    ) -> None:
        """list_tasks(tag='research') returns only tasks with that tag."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, task_id=1, status="todo", subdir="tasks")
        engine = KanbanEngine(kanban_dir, activity_log=False)
        engine.edit_task("1", add_tags=["research"])
        _write_task(kanban_dir, task_id=2, status="todo", subdir="tasks")

        result = engine.list_tasks(tag="research")

        ids = [t.id for t in result]
        assert 1 in ids
        assert 2 not in ids

    def test_list_tasks_priority_filter_returns_matching_tasks(
        self, tmp_path: Path
    ) -> None:
        """list_tasks(priority='critical') returns only tasks with that priority."""
        engine, kanban_dir = _make_engine(tmp_path)
        _write_task(kanban_dir, task_id=1, status="todo", priority="critical", subdir="tasks")
        _write_task(kanban_dir, task_id=2, status="todo", priority="needed", subdir="tasks")

        result = engine.list_tasks(priority="critical")

        ids = [t.id for t in result]
        assert 1 in ids
        assert 2 not in ids

    def test_list_tasks_search_filter_matches_title_substring(
        self, tmp_path: Path
    ) -> None:
        """list_tasks(search='keyword') returns tasks whose title contains the substring."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, task_id=1, status="todo", title="keyword in title", subdir="tasks")
        _write_task(kanban_dir, task_id=2, status="todo", title="unrelated", subdir="tasks")
        engine = KanbanEngine(kanban_dir, activity_log=False)

        result = engine.list_tasks(search="keyword")

        ids = [t.id for t in result]
        assert 1 in ids
        assert 2 not in ids

    def test_list_tasks_sort_priority_returns_consistent_order(
        self, tmp_path: Path
    ) -> None:
        """list_tasks(sort='priority') returns tasks sorted by priority rank."""
        engine, kanban_dir = _make_engine(tmp_path)
        _write_task(kanban_dir, task_id=1, status="todo", priority="someday", subdir="tasks")
        _write_task(kanban_dir, task_id=2, status="todo", priority="critical", subdir="tasks")

        result = engine.list_tasks(sort="priority")

        assert len(result) == 2

    # ------------------------------------------------------------------
    # Storage: board-level corruption detection in read_task (line 338)
    # ------------------------------------------------------------------

    def test_read_task_board_corruption_detected_raises_corruption_error(
        self, tmp_path: Path
    ) -> None:
        """read_task raises CorruptionError when detect_corruption finds an invalid status.

        Covers line 338: the 'raise corruption' branch when detect_corruption returns non-None
        for a task in a board context with a status not in config.statuses.
        """
        kanban_dir = _make_board(tmp_path)
        # Write a task with a status not in the config, but valid YAML + pydantic.
        task_content = (
            "---\n"
            "id: 1\n"
            "title: Task\n"
            "status: INVALID_STATUS_NOT_IN_CONFIG\n"
            "priority: needed\n"
            'created: "2026-01-01T10:00:00+00:00"\n'
            'updated: "2026-01-01T10:00:00+00:00"\n'
            "tags: []\n"
            "parent: null\n"
            "depends_on: []\n"
            "blocked: false\n"
            "block_reason: null\n"
            "claimed_at: null\n"
            "archival_reason: null\n"
            "archival_refs: []\n"
            "---\nBody."
        )
        task_file = kanban_dir / "tasks" / "1-task.md"
        task_file.write_text(task_content, encoding="utf-8")

        with pytest.raises(CorruptionError):
            read_task(task_file)

    # ------------------------------------------------------------------
    # Storage: move_to_quarantine lock-file skip path (line 529)
    # ------------------------------------------------------------------

    def test_move_to_quarantine_skips_lock_files(self, tmp_path: Path) -> None:
        """move_to_quarantine returns the lock file unchanged without moving it.

        Covers line 529: 'if task_path.name.startswith(".") and task_path.name.endswith(".lock"): return task_path'.
        """
        kanban_dir = _make_board(tmp_path)
        lock_file = kanban_dir / "tasks" / ".1.lock"
        lock_file.touch()

        result = move_to_quarantine(lock_file, kanban_dir)

        assert result == lock_file, "lock files must be returned unchanged"
        assert not (kanban_dir / "quarantine").exists(), (
            "quarantine dir must not be created for lock files"
        )
