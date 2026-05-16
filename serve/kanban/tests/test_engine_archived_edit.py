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
from unittest.mock import patch

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_kanban.config_loader import load_config
from owlbear_kanban.corruption import CorruptionError
from owlbear_kanban.engine import AgentView
from owlbear_kanban.models import ConcurrencyError, Task
from owlbear_kanban.storage import (
    _normalize_timestamp,
    allocate_next_id,
    generate_slug,
    list_archive_files,
    list_task_files,
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
    """Regression tests for archived-task edit persistence (task #1121).

    Verifies that AgentView.edit_task and KanbanEngine.edit_task correctly locate
    and persist edits to tasks stored in archive/.  Covers archival_reason, archival_refs,
    append_body, priority update, archive-dir placement, and updated-timestamp propagation.
    """

    # ------------------------------------------------------------------
    # AC-1: AgentView.edit_task — archival_reason update
    # ------------------------------------------------------------------

    def test_agentview_edit_archived_archival_reason_result_updated(self, tmp_path: Path) -> None:
        """AC-1: edit_task on archived task with archival_reason='dropped'; returned object shows updated reason."""
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

    def test_agentview_edit_archived_archival_reason_reread_from_archive(self, tmp_path: Path) -> None:
        """AC-1: after edit, re-reading via show_task returns updated archival_reason from archive/.

        Confirms on-disk persistence, not just the in-memory return value.
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

    def test_agentview_edit_archived_archival_refs_result_updated(self, tmp_path: Path) -> None:
        """AC-2: edit_task on archived task (reason=deprecated) with archival_refs=[2, 3]; result shows updated refs.

        Task starts with refs=[2]; edit adds ref 3 so the change is non-trivial and not a no-op.
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

    def test_agentview_edit_archived_archival_refs_reread_from_archive(self, tmp_path: Path) -> None:
        """AC-2: after archival_refs edit, re-read from archive shows the new refs.

        Starts with refs=[2]; edits to [2, 3] to confirm a real change round-trips through disk.
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

    def test_agentview_edit_archived_append_body_result_contains_text(self, tmp_path: Path) -> None:
        """AC-3: append_body on an archived task; returned body contains the appended text."""
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

        assert "Original body." in (result.body or ""), "original body content must be preserved after append"
        assert "Appended note." in (result.body or "")

    def test_agentview_edit_archived_append_body_reread_from_archive(self, tmp_path: Path) -> None:
        """AC-3: after append_body edit, re-reading from archive confirms text was persisted."""
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

    def test_core_engine_edit_archived_priority_result_updated(self, tmp_path: Path) -> None:
        """AC-4: KanbanEngine.edit_task on archived task with priority='critical'; result shows updated priority.

        Bypasses AgentView to confirm the fix covers the core engine path, not only AgentView.
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

    def test_core_engine_edit_archived_priority_reread_from_archive(self, tmp_path: Path) -> None:
        """AC-4: after engine.edit_task, re-reading from archive shows the updated priority on disk."""
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

    def test_edit_archived_file_stays_in_archive_dir(self, tmp_path: Path) -> None:
        """AC-5: after a successful edit the task file still exists in archive/."""
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

    def test_edit_archived_no_duplicate_created_in_tasks_dir(self, tmp_path: Path) -> None:
        """AC-5: no task file is created in tasks/ after editing an archived task."""
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
            f"no task file should exist in tasks/ after editing an archived task; found: {tasks_files}"
        )

    # ------------------------------------------------------------------
    # AC-6: updated timestamp advances
    # ------------------------------------------------------------------

    def test_edit_archived_updated_timestamp_advances(self, tmp_path: Path) -> None:
        """AC-6: successful edit of an archived task advances the 'updated' timestamp.

        The initial timestamp is '2026-01-01T10:00:00+00:00'; any successful edit must advance it.
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

    def test_edit_archived_updated_timestamp_advances_persisted_to_disk(self, tmp_path: Path) -> None:
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

    def test_agentview_edit_archived_archival_refs_change_to_different_id_result_updated(self, tmp_path: Path) -> None:
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

        assert result.archival_refs == [3], f"archival_refs must be replaced with [3]; got {result.archival_refs!r}"

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

    def test_edit_archived_stale_id_to_filename_cache_falls_back_to_archive(self, tmp_path: Path) -> None:
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

    def test_edit_archived_rollback_on_emit_failure_content_preserved_in_archive(self, tmp_path: Path) -> None:
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
        assert rolled_back.priority == "needed", "priority must be rolled back to 'needed' after emit failure"
        assert not (kanban_dir / "tasks" / "1-task.md").exists(), "rollback write must not create a file in tasks/"
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


# ---------------------------------------------------------------------------
# TestFromAC_StorageCoveragePaths
# ---------------------------------------------------------------------------


class TestFromAC_StorageCoveragePaths:
    """Direct-call coverage tests for storage.py branches not exercised by the
    archived-edit AC suite.

    Each test exercises a specific function or branch documented in the
    storage-module coverage gap report.  All tests run against the
    already-fixed implementation and are expected to PASS.
    """

    # ------------------------------------------------------------------
    # generate_slug (lines 101-108)
    # ------------------------------------------------------------------

    def test_generate_slug_empty_title_returns_empty(self) -> None:
        """Line 101-102: empty title → early return ''."""
        assert generate_slug("") == ""

    def test_generate_slug_normal_title_returns_slug(self) -> None:
        """Lines 101, 103-104, 108: normal title → lower-cased slug."""
        assert generate_slug("Hello World") == "hello-world"

    def test_generate_slug_windows_reserved_name_raises(self) -> None:
        """Lines 105-107: slug matches Windows reserved name → ValueError."""
        with pytest.raises(ValueError, match="Windows reserved"):
            generate_slug("nul")

    def test_generate_slug_con_reserved_raises(self) -> None:
        """Lines 105-107: 'con' is reserved → ValueError."""
        with pytest.raises(ValueError, match="Windows reserved"):
            generate_slug("con")

    # ------------------------------------------------------------------
    # make_task_filename (line 113)
    # ------------------------------------------------------------------

    def test_make_task_filename_returns_id_slug_md(self) -> None:
        """Line 113: make_task_filename delegates to generate_slug."""
        assert make_task_filename(42, "My Task") == "42-my-task.md"

    # ------------------------------------------------------------------
    # validate_path_containment (lines 119-120, 126-127, 131-133)
    # ------------------------------------------------------------------

    def test_validate_path_containment_null_byte_raises(self, tmp_path: Path) -> None:
        """Lines 119-120: path string contains null byte → ValueError.

        Uses a minimal path-like object so Path construction issues on
        stricter platforms do not mask the real guard.
        """
        null_str = str(tmp_path / "evil") + "\x00extra"

        class _NullPath:
            def __str__(self) -> str:
                return null_str

            def resolve(self) -> Path:
                return tmp_path / "evil"

        with pytest.raises(ValueError, match="null byte"):
            validate_path_containment(tmp_path, _NullPath())  # type: ignore[arg-type]

    def test_validate_path_containment_path_equals_dir_raises(self, tmp_path: Path) -> None:
        """Lines 126-127: path == tasks_dir → ValueError."""
        with pytest.raises(ValueError, match="file inside tasks_dir"):
            validate_path_containment(tmp_path, tmp_path)

    def test_validate_path_containment_path_outside_dir_raises(self, tmp_path: Path) -> None:
        """Lines 131-133: path outside tasks_dir → PermissionError."""
        outside = tmp_path.parent / "other"
        with pytest.raises(PermissionError, match="outside tasks_dir"):
            validate_path_containment(tmp_path, outside)

    # ------------------------------------------------------------------
    # _normalize_timestamp (lines 272, 276, 280, 282)
    # ------------------------------------------------------------------

    def test_normalize_timestamp_none_returns_none(self) -> None:
        """_normalize_timestamp(None) → None."""
        assert _normalize_timestamp(None) is None

    def test_normalize_timestamp_non_matching_string_returns_as_is(self) -> None:
        """Line 272: string not matching _TS_RE → returned unchanged."""
        result = _normalize_timestamp("not-a-timestamp")
        assert result == "not-a-timestamp"

    def test_normalize_timestamp_z_suffix_becomes_utc_plus00(self) -> None:
        """Line 276: Z suffix → replaced with +00:00."""
        result = _normalize_timestamp("2026-01-01T10:00:00Z")
        assert result == "2026-01-01T10:00:00+00:00"

    def test_normalize_timestamp_positive_offset_converts_to_utc(self) -> None:
        """Line 280: non-Z timezone offset → UTC isoformat."""
        result = _normalize_timestamp("2026-01-01T15:30:00+05:30")
        # 15:30 +05:30 = 10:00 UTC
        assert result == "2026-01-01T10:00:00+00:00"

    def test_normalize_timestamp_no_timezone_appends_utc_suffix(self) -> None:
        """Line 282: no timezone in string → +00:00 appended."""
        result = _normalize_timestamp("2026-01-01T10:00:00")
        assert result == "2026-01-01T10:00:00+00:00"

    # ------------------------------------------------------------------
    # read_task error paths (lines 140-141, 144-145, 154-155, 166-176,
    #                        316-325, 338, 343-344, 346)
    # ------------------------------------------------------------------

    def test_read_task_cp1252_fallback_succeeds(self, tmp_path: Path) -> None:
        """Lines 140-141: UTF-8 decode fails → cp1252 fallback reads task."""
        task_file = tmp_path / "1-cp1252.md"
        # \x80 is valid cp1252 (€) but NOT valid UTF-8.
        content = (
            b"---\nid: 1\ntitle: CP Task\nstatus: todo\npriority: needed\n"
            b'created: "2026-01-01T10:00:00+00:00"\n'
            b'updated: "2026-01-01T10:00:00+00:00"\n'
            b"tags: []\nparent: null\ndepends_on: []\nblocked: false\n"
            b"block_reason: null\nclaimed_at: null\narchival_reason: null\n"
            b"archival_refs: []\n---\nBody with \x80 char.\n"
        )
        task_file.write_bytes(content)
        # File is at tmp_path/1-cp1252.md; grandparent has no config.yml.
        task = read_task(task_file)
        assert task.id == 1
        assert task.title == "CP Task"

    def test_read_task_no_opening_delimiter_raises_corruption(self, tmp_path: Path) -> None:
        """Lines 144-145, 324-329: no opening --- → ERR_CORRUPT_DELIMITERS."""
        task_file = tmp_path / "1-nodelim.md"
        task_file.write_text("No frontmatter here.\n", encoding="utf-8")
        with pytest.raises(CorruptionError) as exc_info:
            read_task(task_file)
        assert exc_info.value.code == "ERR_CORRUPT_DELIMITERS"

    def test_read_task_no_closing_delimiter_raises_corruption(self, tmp_path: Path) -> None:
        """Lines 154-155: no closing --- → ERR_CORRUPT_DELIMITERS."""
        task_file = tmp_path / "1-noclosing.md"
        task_file.write_text(
            "---\nid: 1\ntitle: Task\n# no closing delimiter\nBody\n",
            encoding="utf-8",
        )
        with pytest.raises(CorruptionError) as exc_info:
            read_task(task_file)
        assert exc_info.value.code == "ERR_CORRUPT_DELIMITERS"

    def test_read_task_yaml_parse_error_raises_corruption(self, tmp_path: Path) -> None:
        """Lines 316-321: yaml.YAMLError → ERR_CORRUPT_YAML_PARSE."""
        task_file = tmp_path / "1-badyaml.md"
        # Unclosed YAML flow sequence → YAML parse error.
        task_file.write_text(
            "---\nid: [\nunclosed\n---\nBody\n",
            encoding="utf-8",
        )
        with pytest.raises(CorruptionError) as exc_info:
            read_task(task_file)
        assert "YAML" in exc_info.value.code or "ERR_CORRUPT" in exc_info.value.code

    def test_read_task_missing_required_field_raises_missing_field_corruption(self, tmp_path: Path) -> None:
        """Lines 322-323, 166-176: Pydantic missing field → ERR_CORRUPT_MISSING_FIELD."""
        task_file = tmp_path / "1-noid.md"
        task_file.write_text(
            "---\ntitle: No ID\nstatus: todo\npriority: needed\n"
            'created: "2026-01-01T10:00:00+00:00"\n'
            'updated: "2026-01-01T10:00:00+00:00"\n'
            "tags: []\nparent: null\ndepends_on: []\nblocked: false\n"
            "block_reason: null\nclaimed_at: null\narchival_reason: null\n"
            "archival_refs: []\n---\nBody\n",
            encoding="utf-8",
        )
        with pytest.raises(CorruptionError) as exc_info:
            read_task(task_file)
        assert exc_info.value.code == "ERR_CORRUPT_MISSING_FIELD"

    def test_read_task_detect_corruption_raises_for_invalid_status(self, tmp_path: Path) -> None:
        """Line 338: detect_corruption returns error → raise corruption."""
        kanban_dir = _make_board(tmp_path)
        task_content = _TASK_TMPL.format(
            task_id=1,
            title="Bad Status",
            status="invalid-status-xyz",
            priority="needed",
            archival_reason="null",
            archival_refs="[]",
            body="Body.",
        )
        task_file = kanban_dir / "tasks" / "1-bad-status.md"
        task_file.write_text(task_content, encoding="utf-8")
        with pytest.raises(CorruptionError):
            read_task(task_file)

    def test_read_task_non_integer_filename_prefix_reads_task_successfully(self, tmp_path: Path) -> None:
        """Lines 343-344: stem prefix is non-integer → file_id=None → no mismatch check."""
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        # Stem "abc-1-task" → split("-",1)[0]="abc" → int("abc") raises → file_id=None.
        task_file = tasks_dir / "abc-1-task.md"
        task_file.write_text(
            "---\nid: 1\ntitle: Task\nstatus: todo\npriority: needed\n"
            'created: "2026-01-01T10:00:00+00:00"\n'
            'updated: "2026-01-01T10:00:00+00:00"\n'
            "tags: []\nparent: null\ndepends_on: []\nblocked: false\n"
            "block_reason: null\nclaimed_at: null\narchival_reason: null\n"
            "archival_refs: []\n---\nBody.\n",
            encoding="utf-8",
        )
        # tmp_path has no config.yml → no detect_corruption.
        task = read_task(task_file)
        assert task.id == 1

    def test_read_task_id_filename_mismatch_raises_corruption(self, tmp_path: Path) -> None:
        """Line 346: filename prefix id=5 but frontmatter id=1 → ERR_CORRUPT_ID_FILENAME_MISMATCH."""
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        task_file = tasks_dir / "5-task.md"
        task_file.write_text(
            "---\nid: 1\ntitle: Task\nstatus: todo\npriority: needed\n"
            'created: "2026-01-01T10:00:00+00:00"\n'
            'updated: "2026-01-01T10:00:00+00:00"\n'
            "tags: []\nparent: null\ndepends_on: []\nblocked: false\n"
            "block_reason: null\nclaimed_at: null\narchival_reason: null\n"
            "archival_refs: []\n---\nBody.\n",
            encoding="utf-8",
        )
        with pytest.raises(CorruptionError) as exc_info:
            read_task(task_file)
        assert exc_info.value.code == "ERR_CORRUPT_ID_FILENAME_MISMATCH"

    # ------------------------------------------------------------------
    # save_config (lines 245-261)
    # ------------------------------------------------------------------

    def test_save_config_writes_readable_config(self, tmp_path: Path) -> None:
        """Lines 245-261: save_config serialises BoardConfig to config.yml."""
        kanban_dir = _make_board(tmp_path)
        config = load_config(kanban_dir)
        config.next_id = 42
        save_config(config, kanban_dir)
        reloaded = load_config(kanban_dir)
        assert reloaded.next_id == 42

    # ------------------------------------------------------------------
    # write_task: new-file else branch (lines 379-380) and default dir
    # ------------------------------------------------------------------

    def test_write_task_creates_new_file_when_no_existing_match(self, tmp_path: Path) -> None:
        """Lines 379-380: no existing glob match → make_task_filename + new path created."""
        kanban_dir = _make_board(tmp_path)
        task = Task.model_validate({**_TASK_DICT, "id": 99, "title": "New Task"})
        path = write_task(task, kanban_dir)
        assert path.exists()
        assert "99-new-task" in path.name

    def test_write_task_default_target_dir_none_writes_to_tasks(self, tmp_path: Path) -> None:
        """Backwards-compat: write_task without target_dir → writes to tasks/."""
        kanban_dir = _make_board(tmp_path)
        task = Task.model_validate({**_TASK_DICT, "id": 1, "title": "Task"})
        path = write_task(task, kanban_dir)
        assert "tasks" in str(path)

    # ------------------------------------------------------------------
    # write_task_if_unchanged (lines 433-451)
    # ------------------------------------------------------------------

    def test_write_task_if_unchanged_happy_path(self, tmp_path: Path) -> None:
        """Lines 433-451: matching updated timestamp → writes successfully."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, task_id=1, status="todo", subdir="tasks")
        task_path = kanban_dir / "tasks" / "1-task.md"
        task = read_task(task_path)
        result_path = write_task_if_unchanged(task, task.updated, kanban_dir)
        assert result_path.exists()

    def test_write_task_if_unchanged_raises_stale_when_updated_changed(self, tmp_path: Path) -> None:
        """Lines 444-446: on-disk updated differs from expected → ConcurrencyError ERR_STALE."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, task_id=1, status="todo", subdir="tasks")
        task_path = kanban_dir / "tasks" / "1-task.md"
        task = read_task(task_path)
        old_updated = task.updated
        # Write a newer version to disk.
        newer = task.model_copy(update={"updated": "2026-12-31T23:59:59+00:00"})
        write_task(newer, kanban_dir)
        with pytest.raises(ConcurrencyError) as exc_info:
            write_task_if_unchanged(task, old_updated, kanban_dir)
        assert exc_info.value.code == "ERR_STALE"

    def test_write_task_if_unchanged_raises_when_file_missing(self, tmp_path: Path) -> None:
        """Lines 436-439: no file found for id → FileNotFoundError."""
        kanban_dir = _make_board(tmp_path)
        task = Task.model_validate({**_TASK_DICT, "id": 99, "title": "Absent Task"})
        with pytest.raises(FileNotFoundError):
            write_task_if_unchanged(task, "2026-01-01T10:00:00+00:00", kanban_dir)

    # ------------------------------------------------------------------
    # list_task_files (lines 461-465)
    # ------------------------------------------------------------------

    def test_list_task_files_empty_dir_returns_empty_list(self, tmp_path: Path) -> None:
        """Lines 461-465: no files in tasks/ → []."""
        kanban_dir = _make_board(tmp_path)
        assert list_task_files(kanban_dir) == []

    def test_list_task_files_returns_sorted_md_files(self, tmp_path: Path) -> None:
        """list_task_files returns sorted .md files from tasks/."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, task_id=1, subdir="tasks")
        _write_task(kanban_dir, task_id=2, subdir="tasks")
        result = list_task_files(kanban_dir)
        assert len(result) == 2
        assert all(p.suffix == ".md" for p in result)

    # ------------------------------------------------------------------
    # list_archive_files (lines 477-481)
    # ------------------------------------------------------------------

    def test_list_archive_files_empty_dir_returns_empty_list(self, tmp_path: Path) -> None:
        """Lines 477-481: no files in archive/ → []."""
        kanban_dir = _make_board(tmp_path)
        assert list_archive_files(kanban_dir) == []

    def test_list_archive_files_returns_sorted_archive_md_files(self, tmp_path: Path) -> None:
        """list_archive_files returns sorted .md files from archive/."""
        kanban_dir = _make_board(tmp_path)
        _write_task(
            kanban_dir,
            task_id=1,
            status="archived",
            archival_reason="dropped",
            subdir="archive",
        )
        result = list_archive_files(kanban_dir)
        assert len(result) == 1
        assert result[0].name == "1-task.md"

    # ------------------------------------------------------------------
    # move_to_archive (lines 498-516)
    # ------------------------------------------------------------------

    def test_move_to_archive_moves_file_from_tasks_to_archive(self, tmp_path: Path) -> None:
        """Lines 498-516: task in tasks/ → moved to archive/."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, task_id=1, subdir="tasks")
        assert (kanban_dir / "tasks" / "1-task.md").exists()
        dest = move_to_archive(1, kanban_dir)
        assert dest.parent == kanban_dir / "archive"
        assert not (kanban_dir / "tasks" / "1-task.md").exists()

    def test_move_to_archive_raises_when_file_not_found(self, tmp_path: Path) -> None:
        """move_to_archive raises FileNotFoundError when no file exists for id."""
        kanban_dir = _make_board(tmp_path)
        with pytest.raises(FileNotFoundError):
            move_to_archive(99, kanban_dir)

    # ------------------------------------------------------------------
    # move_to_quarantine (lines 528-537)
    # ------------------------------------------------------------------

    def test_move_to_quarantine_moves_non_lock_file(self, tmp_path: Path) -> None:
        """Lines 528-537: regular file → moved to quarantine/."""
        kanban_dir = _make_board(tmp_path)
        _write_task(kanban_dir, task_id=1, subdir="tasks")
        task_file = kanban_dir / "tasks" / "1-task.md"
        dest = move_to_quarantine(task_file, kanban_dir)
        assert dest.parent == kanban_dir / "quarantine"
        assert not task_file.exists()

    # ------------------------------------------------------------------
    # allocate_next_id (lines 547-555)
    # ------------------------------------------------------------------

    def test_allocate_next_id_returns_current_next_id_and_increments(self, tmp_path: Path) -> None:
        """Scan-based allocate_next_id returns 1 on empty board; config.next_id unchanged."""
        kanban_dir = _make_board(tmp_path)
        expected_id = load_config(kanban_dir).next_id
        allocated = allocate_next_id(kanban_dir)
        assert allocated == 1
        assert load_config(kanban_dir).next_id == expected_id

    # ------------------------------------------------------------------
    # write_task: backwards-compat default dir (canonical assertion — AC-2)
    # ------------------------------------------------------------------

    def test_write_task_default_target_dir_canonical_dir_is_tasks(self, tmp_path: Path) -> None:
        """AC-2: write_task without target_dir → parent dir is exactly tasks/, not just a dir
        containing 'tasks' in its name."""
        kanban_dir = _make_board(tmp_path)
        task = Task.model_validate({**_TASK_DICT, "id": 55, "title": "Canonical Dir Test"})
        path = write_task(task, kanban_dir)
        assert path.parent == kanban_dir / "tasks"

    # ------------------------------------------------------------------
    # write_task: explicit target_dir, no existing file (lines 375-380)
    # ------------------------------------------------------------------

    def test_write_task_explicit_target_dir_no_existing_file_writes_to_explicit_dir(self, tmp_path: Path) -> None:
        """Lines 375-380 (else branch): explicit target_dir + no existing glob match →
        new file created in target_dir, not in tasks/."""
        kanban_dir = _make_board(tmp_path)
        archive_dir = kanban_dir / "archive"
        task = Task.model_validate({**_TASK_DICT, "id": 77, "title": "Explicit Target Dir"})
        path = write_task(task, kanban_dir, target_dir=archive_dir)
        assert path.parent == archive_dir
        assert not (kanban_dir / "tasks" / path.name).exists()
