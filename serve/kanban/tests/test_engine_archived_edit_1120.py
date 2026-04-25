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
from owlbear_kanban.engine import AgentView
from owlbear_kanban.storage import read_task, write_task

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
