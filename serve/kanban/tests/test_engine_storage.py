"""TDD RED: C-08 — engine storage-integration tests.

Task: #1053 (Brief C #1043) — paper-c.md §8.4, §8.5, §8.11
AC:   C19, C20, C23, C24, C25, C26, C27, C47, C49, C50, C52, C54
All tests FAIL (RED phase — new engine methods / storage module not yet implemented).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_kanban.config_loader import load_config
from owlbear_kanban.engine import (
    MigrationRequiredError,
)  # NEW exception — AttributeError in RED
from owlbear_kanban.corruption import CorruptionError  # NEW module — ImportError in RED

# ---------------------------------------------------------------------------
# Board helpers — use existing OLD schema so KanbanEngine can instantiate today
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
next_id: 1001
archive_dir: archive
activity_log: false
"""

_NEW_CONFIG_YAML = """\
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
terminal_status: done
wave_size: 4
agent_map:
  research: researcher
  backlog: architect
  todo: builder
  in-progress: builder
  review: reviewer
  docs: doc-writer
  done: auditor
agent_types: {}
agent_compatibility: {}
non_impl_tags: [research, docs]
archival_reasons: [completed, deprecated, dropped, duplicate, wontfix]
status_predicates: {}
claim_timeout: 1h
next_id: 1001
"""

_VALID_TASK = """\
---
id: {task_id}
title: Task {task_id}
status: todo
priority: needed
created: "2026-04-21T10:00:00+00:00"
updated: "2026-04-21T10:00:00+00:00"
tags: []
parent: null
depends_on: []
blocked: false
block_reason: null
claimed_at: null
archival_reason: null
archival_refs: []
---

## Notes

Content.
"""

_CORRUPT_TASK = "not valid frontmatter\n"


def _make_board(base_dir: Path) -> Path:
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


def _make_new_board(base_dir: Path) -> Path:
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_NEW_CONFIG_YAML, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


# ---------------------------------------------------------------------------
# TestFromAC_ListTasksCorruption — AC-C19, AC-C20
# ---------------------------------------------------------------------------


class TestFromAC_ListTasksCorruption:
    """AC-C19, AC-C20: list_tasks behaviour with corrupt files."""

    def test_ac_c19_list_tasks_skips_mode1_corrupt_silently(
        self, tmp_path: Path
    ) -> None:
        """AC-C19: list_tasks silently skips file with missing delimiters (mode 1)."""
        kanban_dir = _make_new_board(tmp_path)
        (kanban_dir / "tasks" / "1001-good.md").write_text(
            _VALID_TASK.format(task_id=1001), encoding="utf-8"
        )
        (kanban_dir / "tasks" / "1002-bad.md").write_text(
            _CORRUPT_TASK, encoding="utf-8"
        )

        engine = KanbanEngine(kanban_dir)
        tasks = engine.list_tasks()

        task_ids = [t.id for t in tasks]
        assert 1001 in task_ids
        assert 1002 not in task_ids

    def test_ac_c19_list_tasks_skips_all_non_mode2_corrupt(
        self, tmp_path: Path
    ) -> None:
        """AC-C19: list_tasks silently skips modes 3-9 corrupt files."""
        kanban_dir = _make_new_board(tmp_path)
        (kanban_dir / "tasks" / "1001-good.md").write_text(
            _VALID_TASK.format(task_id=1001), encoding="utf-8"
        )
        # Mode 8: invalid status
        (kanban_dir / "tasks" / "1003-badstatus.md").write_text(
            "---\nid: 1003\ntitle: bad\nstatus: NONEXISTENT_STATUS\npriority: needed\n"
            'created: "2026-04-21T10:00:00+00:00"\nupdated: "2026-04-21T10:00:00+00:00"\n---\n',
            encoding="utf-8",
        )

        engine = KanbanEngine(kanban_dir)
        tasks = engine.list_tasks()

        task_ids = [t.id for t in tasks]
        assert 1001 in task_ids
        assert 1003 not in task_ids

    def test_ac_c20_list_tasks_hard_raises_on_duplicate_id(
        self, tmp_path: Path
    ) -> None:
        """AC-C20: list_tasks raises CorruptionError(code=ERR_CORRUPT_DUPLICATE_ID) for mode 2."""
        kanban_dir = _make_new_board(tmp_path)
        task_content = _VALID_TASK.format(task_id=1001)
        (kanban_dir / "tasks" / "1001-original.md").write_text(
            task_content, encoding="utf-8"
        )
        (kanban_dir / "tasks" / "1001-duplicate.md").write_text(
            task_content, encoding="utf-8"
        )

        engine = KanbanEngine(kanban_dir)
        with pytest.raises(CorruptionError) as exc_info:
            engine.list_tasks()

        assert exc_info.value.code == "ERR_CORRUPT_DUPLICATE_ID"

    def test_ac_c19_list_tasks_skips_mode6_id_filename_mismatch(
        self, tmp_path: Path
    ) -> None:
        """AC-C19: list_tasks silently skips files where frontmatter id != filename id (mode 6)."""
        kanban_dir = _make_new_board(tmp_path)
        (kanban_dir / "tasks" / "1001-good.md").write_text(
            _VALID_TASK.format(task_id=1001), encoding="utf-8"
        )
        # Mode 6: file named 9999-mismatch.md but frontmatter id=2001 (9999 ≠ 2001)
        mismatch_content = _VALID_TASK.format(task_id=2001)
        (kanban_dir / "tasks" / "9999-mismatch.md").write_text(
            mismatch_content, encoding="utf-8"
        )

        engine = KanbanEngine(kanban_dir)
        tasks = engine.list_tasks()

        task_ids = [t.id for t in tasks]
        assert 1001 in task_ids
        assert 2001 not in task_ids, (
            "mode-6 file (id-filename mismatch) must be silently skipped"
        )
        assert 9999 not in task_ids

    def test_ac_c19_list_tasks_skips_mode9_invalid_priority(
        self, tmp_path: Path
    ) -> None:
        """AC-C19: list_tasks silently skips files with an invalid priority value (mode 9)."""
        kanban_dir = _make_new_board(tmp_path)
        (kanban_dir / "tasks" / "1001-good.md").write_text(
            _VALID_TASK.format(task_id=1001), encoding="utf-8"
        )
        # Mode 9: priority not in the configured list
        bad_priority_content = _VALID_TASK.format(task_id=1002).replace(
            "priority: needed", "priority: ultra-mega-important"
        )
        (kanban_dir / "tasks" / "1002-badpriority.md").write_text(
            bad_priority_content, encoding="utf-8"
        )

        engine = KanbanEngine(kanban_dir)
        tasks = engine.list_tasks()

        task_ids = [t.id for t in tasks]
        assert 1001 in task_ids
        assert 1002 not in task_ids, (
            "mode-9 file (invalid priority) must be silently skipped"
        )

    def test_ac_c19_list_tasks_skips_mode3_missing_required_field(
        self, tmp_path: Path
    ) -> None:
        """AC-C19: list_tasks silently skips mode-3 files (ERR_CORRUPT_MISSING_FIELD — missing title)."""
        kanban_dir = _make_new_board(tmp_path)
        (kanban_dir / "tasks" / "1001-good.md").write_text(
            _VALID_TASK.format(task_id=1001), encoding="utf-8"
        )
        # Mode 3: required field 'title' absent
        (kanban_dir / "tasks" / "1002-notitle.md").write_text(
            "---\nid: 1002\nstatus: todo\npriority: needed\n"
            'created: "2026-04-21T10:00:00+00:00"\nupdated: "2026-04-21T10:00:00+00:00"\n'
            "tags: []\nparent: null\ndepends_on: []\nblocked: false\nblock_reason: null\n"
            "claimed_at: null\narchival_reason: null\narchival_refs: []\n---\n",
            encoding="utf-8",
        )

        engine = KanbanEngine(kanban_dir)
        tasks = engine.list_tasks()

        task_ids = [t.id for t in tasks]
        assert 1001 in task_ids
        assert 1002 not in task_ids, (
            "mode-3 file (missing required field) must be silently skipped"
        )

    def test_ac_c19_list_tasks_skips_mode3b_claimed_by_on_legacy_schema(
        self, tmp_path: Path
    ) -> None:
        """AC-C47/C19 mode-3b: KanbanEngine raises MigrationRequiredError when tasks/
        contains a file with non-null claimed_by, regardless of board schema.

        With the topology-constant refactor (task #1439), is_legacy_schema is always
        False because load_config uses PRODUCT_TOPOLOGY and does not pass version
        through model_extra.  The migration gate therefore runs on ALL boards.
        Any board with claimed_by in tasks/ triggers MigrationRequiredError at init.
        """
        kanban_dir = _make_board(tmp_path)  # legacy schema board (version: 10)
        (kanban_dir / "tasks" / "1001-good.md").write_text(
            _VALID_TASK.format(task_id=1001), encoding="utf-8"
        )
        # Mode-3b: all required fields present PLUS forbidden claimed_by: some-agent
        (kanban_dir / "tasks" / "1002-claimed.md").write_text(
            "---\nid: 1002\ntitle: legacy claimed task\nstatus: todo\npriority: needed\n"
            "claimed_by: some-agent\n"
            'created: "2026-04-21T10:00:00+00:00"\nupdated: "2026-04-21T10:00:00+00:00"\n'
            "tags: []\nparent: null\ndepends_on: []\nblocked: false\nblock_reason: null\n"
            "claimed_at: null\narchival_reason: null\narchival_refs: []\n---\n\nBody.\n",
            encoding="utf-8",
        )

        with pytest.raises(MigrationRequiredError):
            KanbanEngine(kanban_dir)

    def test_ac_c19_list_tasks_skips_mode4_type_mismatch_id_string(
        self, tmp_path: Path
    ) -> None:
        """AC-C19: list_tasks silently skips mode-4 files (ERR_CORRUPT_TYPE_MISMATCH — id is string)."""
        kanban_dir = _make_new_board(tmp_path)
        (kanban_dir / "tasks" / "1001-good.md").write_text(
            _VALID_TASK.format(task_id=1001), encoding="utf-8"
        )
        # Mode 4: id field is a string (not int)
        (kanban_dir / "tasks" / "1002-badtype.md").write_text(
            '---\nid: "not_an_int"\ntitle: bad type\nstatus: todo\npriority: needed\n'
            'created: "2026-04-21T10:00:00+00:00"\nupdated: "2026-04-21T10:00:00+00:00"\n'
            "tags: []\nparent: null\ndepends_on: []\nblocked: false\nblock_reason: null\n"
            "claimed_at: null\narchival_reason: null\narchival_refs: []\n---\n",
            encoding="utf-8",
        )

        engine = KanbanEngine(kanban_dir)
        tasks = engine.list_tasks()

        task_ids = [t.id for t in tasks]
        assert 1001 in task_ids
        assert all(isinstance(tid, int) for tid in task_ids), (
            "no string IDs must appear in list_tasks output"
        )
        assert len(tasks) == 1, "mode-4 file (type mismatch) must be silently skipped"

    def test_ac_c19_list_tasks_skips_mode5_yaml_parse_error(
        self, tmp_path: Path
    ) -> None:
        """AC-C19: list_tasks silently skips mode-5 files (ERR_CORRUPT_YAML_PARSE — bad YAML)."""
        kanban_dir = _make_new_board(tmp_path)
        (kanban_dir / "tasks" / "1001-good.md").write_text(
            _VALID_TASK.format(task_id=1001), encoding="utf-8"
        )
        # Mode 5: YAML frontmatter that cannot be parsed
        (kanban_dir / "tasks" / "1002-badyaml.md").write_text(
            "---\n: invalid_yaml_key: [unclosed bracket\n---\n",
            encoding="utf-8",
        )

        engine = KanbanEngine(kanban_dir)
        tasks = engine.list_tasks()

        task_ids = [t.id for t in tasks]
        assert 1001 in task_ids
        assert len(tasks) == 1, (
            "mode-5 file (YAML parse error) must be silently skipped"
        )

    def test_ac_c19_list_tasks_skips_mode7_duplicate_location(
        self, tmp_path: Path
    ) -> None:
        """AC-C19: list_tasks silently skips tasks/ file when same ID also exists in archive/ (mode 7).

        ERR_CORRUPT_DUPLICATE_LOCATION: task ID present in both tasks/ and archive/.
        The archive copy is canonical (archive-wins per AC-C26); the tasks/ copy must
        not appear in the non-archived list_tasks result.
        """
        kanban_dir = _make_new_board(tmp_path)
        task_content = _VALID_TASK.format(task_id=1001)
        (kanban_dir / "tasks" / "1001-active.md").write_text(
            task_content, encoding="utf-8"
        )
        (kanban_dir / "archive" / "1001-active.md").write_text(
            task_content, encoding="utf-8"
        )
        (kanban_dir / "tasks" / "1002-good.md").write_text(
            _VALID_TASK.format(task_id=1002), encoding="utf-8"
        )

        engine = KanbanEngine(kanban_dir)
        tasks = engine.list_tasks()

        task_ids = [t.id for t in tasks]
        assert 1002 in task_ids
        assert 1001 not in task_ids, (
            "mode-7 file (duplicate location: same ID in tasks/ and archive/) "
            "must be silently skipped by list_tasks"
        )


# ---------------------------------------------------------------------------
# TestFromAC_Sweep — AC-C23, AC-C27, AC-C52
# ---------------------------------------------------------------------------


class TestFromAC_Sweep:
    """AC-C23, AC-C27, AC-C52: sweep() contract."""

    def test_ac_c23_sweep_returns_list_of_int(self, tmp_path: Path) -> None:
        """AC-C23: sweep() returns list[int] (not dict) of released claim IDs."""
        kanban_dir = _make_new_board(tmp_path)
        engine = KanbanEngine(kanban_dir)
        result = engine.sweep()

        assert isinstance(result, list)
        assert all(isinstance(i, int) for i in result)

    def test_ac_c23_sweep_returns_only_released_ids(self, tmp_path: Path) -> None:
        """AC-C23: sweep() returns IDs of tasks whose expired claims were released."""
        kanban_dir = _make_new_board(tmp_path)
        # Write a task with an expired claimed_at
        expired_ts = (datetime.now(tz=UTC) - timedelta(hours=3)).isoformat()
        task_content = _VALID_TASK.format(task_id=1001).replace(
            "claimed_at: null", f'claimed_at: "{expired_ts}"'
        )
        (kanban_dir / "tasks" / "1001-expired.md").write_text(
            task_content, encoding="utf-8"
        )
        (kanban_dir / "tasks" / "1002-unclaimed.md").write_text(
            _VALID_TASK.format(task_id=1002), encoding="utf-8"
        )

        engine = KanbanEngine(kanban_dir)
        released = engine.sweep()

        assert 1001 in released
        assert 1002 not in released

    def test_ac_c23_sweep_returns_exact_released_id_set(self, tmp_path: Path) -> None:
        """AC-C23: sweep() returns EXACTLY the set of released IDs — no extras, no omissions.

        Tightens the membership-only assertion to a full set-equality check so that
        unexpected extra IDs in the return value would be caught as a regression.
        """
        kanban_dir = _make_new_board(tmp_path)
        expired_ts = (datetime.now(tz=UTC) - timedelta(hours=3)).isoformat()
        (kanban_dir / "tasks" / "1001-expired.md").write_text(
            _VALID_TASK.format(task_id=1001).replace(
                "claimed_at: null", f'claimed_at: "{expired_ts}"'
            ),
            encoding="utf-8",
        )
        (kanban_dir / "tasks" / "1002-expired.md").write_text(
            _VALID_TASK.format(task_id=1002).replace(
                "claimed_at: null", f'claimed_at: "{expired_ts}"'
            ),
            encoding="utf-8",
        )
        (kanban_dir / "tasks" / "1003-unclaimed.md").write_text(
            _VALID_TASK.format(task_id=1003), encoding="utf-8"
        )

        engine = KanbanEngine(kanban_dir)
        released = engine.sweep()

        assert set(released) == {1001, 1002}, (
            f"sweep() must return exactly the set of expired claim IDs; got {set(released)}"
        )
        assert 1003 not in released, "unclaimed task must NOT appear in released set"

    def test_ac_c27_sweep_independent_of_corruption_repair(
        self, tmp_path: Path
    ) -> None:
        """AC-C27: sweep() releases expired claims without touching corrupt files."""
        kanban_dir = _make_new_board(tmp_path)
        expired_ts = (datetime.now(tz=UTC) - timedelta(hours=3)).isoformat()
        (kanban_dir / "tasks" / "1001-expired.md").write_text(
            _VALID_TASK.format(task_id=1001).replace(
                "claimed_at: null", f'claimed_at: "{expired_ts}"'
            ),
            encoding="utf-8",
        )
        (kanban_dir / "tasks" / "9999-corrupt.md").write_text(
            _CORRUPT_TASK, encoding="utf-8"
        )

        engine = KanbanEngine(kanban_dir)
        released = engine.sweep()

        # Only the expired claim is released; corrupt file untouched (not quarantined)
        assert 1001 in released
        assert (kanban_dir / "tasks" / "9999-corrupt.md").exists()
        assert not (kanban_dir / "quarantine").exists()

    def test_ac_c27_sweep_does_not_write_to_parseable_corrupt_file(
        self, tmp_path: Path
    ) -> None:
        """AC-C27 (refined): sweep() must NOT write to parseable-but-corrupt files.

        A mode-9 file (invalid priority — parseable but flagged by detect_corruption) with
        an expired claimed_at must NOT have its claim released by sweep(). The file must
        remain byte-for-byte unchanged after sweep() completes.

        Current implementation only skips unreadable files (mode 1), so it rewrites
        parseable corrupt files — this test catches that regression.
        """
        kanban_dir = _make_new_board(tmp_path)
        expired_ts = (datetime.now(tz=UTC) - timedelta(hours=3)).isoformat()
        # Mode 9: invalid priority — YAML parses fine but detect_corruption flags it
        corrupt_content = (
            "---\nid: 1001\ntitle: Parseable corrupt\nstatus: in-progress\n"
            "priority: ultra-mega-important\n"  # not in config — mode 9
            f'created: "2026-04-21T10:00:00+00:00"\nupdated: "2026-04-21T10:00:00+00:00"\n'
            "tags: []\nparent: null\ndepends_on: []\nblocked: false\nblock_reason: null\n"
            f'claimed_at: "{expired_ts}"\narchival_reason: null\narchival_refs: []\n---\n'
        )
        corrupt_file = kanban_dir / "tasks" / "1001-parseable-corrupt.md"
        corrupt_file.write_text(corrupt_content, encoding="utf-8")

        engine = KanbanEngine(kanban_dir)
        released = engine.sweep()

        assert 1001 not in released, (
            "sweep() must NOT release claims on parseable-but-corrupt files; "
            "detect_corruption must gate claim release (AC-C27 refined)"
        )
        assert corrupt_file.read_text(encoding="utf-8") == corrupt_content, (
            "sweep() must NOT modify a parseable-but-corrupt file (AC-C27 refined)"
        )

    def test_ac_c52_sweep_does_not_mutate_body(self, tmp_path: Path) -> None:
        """AC-C52: sweep() only clears claimed_at and advances updated; body unchanged."""
        kanban_dir = _make_new_board(tmp_path)
        expired_ts = (datetime.now(tz=UTC) - timedelta(hours=3)).isoformat()
        original_body = "\n## Notes\n\nThis is the body.\n"
        task_content = (
            "---\nid: 1001\ntitle: Sweep test\nstatus: in-progress\npriority: needed\n"
            f'created: "2026-04-21T10:00:00+00:00"\nupdated: "2026-04-21T10:00:00+00:00"\n'
            f"tags: []\nparent: null\ndepends_on: []\nblocked: false\nblock_reason: null\n"
            f'claimed_at: "{expired_ts}"\narchival_reason: null\narchival_refs: []\n---\n'
            + original_body
        )
        (kanban_dir / "tasks" / "1001-sweep.md").write_text(
            task_content, encoding="utf-8"
        )

        engine = KanbanEngine(kanban_dir)
        released = engine.sweep()

        assert 1001 in released
        updated_task = engine.show_task(1001)
        # claimed_at cleared
        assert updated_task.claimed_at is None
        # Body unchanged
        assert original_body.strip() in (updated_task.body or "")

    def test_ac_c52_sweep_advances_updated_timestamp(self, tmp_path: Path) -> None:
        """AC-C52: sweep() advances the 'updated' timestamp when releasing an expired claim."""
        kanban_dir = _make_new_board(tmp_path)
        original_updated = "2026-04-21T10:00:00+00:00"
        expired_ts = (datetime.now(tz=UTC) - timedelta(hours=3)).isoformat()
        task_content = (
            "---\nid: 1001\ntitle: Timestamp test\nstatus: in-progress\npriority: needed\n"
            f'created: "{original_updated}"\nupdated: "{original_updated}"\n'
            "tags: []\nparent: null\ndepends_on: []\nblocked: false\nblock_reason: null\n"
            f'claimed_at: "{expired_ts}"\narchival_reason: null\narchival_refs: []\n---\n'
        )
        (kanban_dir / "tasks" / "1001-ts.md").write_text(task_content, encoding="utf-8")

        before = datetime.now(tz=UTC)
        engine = KanbanEngine(kanban_dir)
        released = engine.sweep()

        assert 1001 in released
        updated_task = engine.show_task(1001)
        updated_dt = datetime.fromisoformat(updated_task.updated)
        if updated_dt.tzinfo is None:
            updated_dt = updated_dt.replace(tzinfo=UTC)
        assert updated_dt >= before, (
            "sweep() must advance 'updated' to at least the time sweep started"
        )

    def test_ac_c52_sweep_preserves_body_exactly(self, tmp_path: Path) -> None:
        """AC-C52: sweep() preserves task body with exact equality, not just substring containment.

        The AC forbids body mutation during sweep. A substring-only check would miss
        prefix or suffix additions. This test asserts strict equality between the
        original body string and the body read back after sweep releases the claim.
        """
        kanban_dir = _make_new_board(tmp_path)
        expired_ts = (datetime.now(tz=UTC) - timedelta(hours=3)).isoformat()
        original_body = (
            "\n## Notes\n\nExact body content — must survive sweep unchanged.\n"
        )
        task_content = (
            "---\nid: 1001\ntitle: Exact body test\nstatus: in-progress\npriority: needed\n"
            f'created: "2026-04-21T10:00:00+00:00"\nupdated: "2026-04-21T10:00:00+00:00"\n'
            "tags: []\nparent: null\ndepends_on: []\nblocked: false\nblock_reason: null\n"
            f'claimed_at: "{expired_ts}"\narchival_reason: null\narchival_refs: []\n---\n'
            + original_body
        )
        (kanban_dir / "tasks" / "1001-exactbody.md").write_text(
            task_content, encoding="utf-8"
        )

        engine = KanbanEngine(kanban_dir)
        released = engine.sweep()

        assert 1001 in released
        updated_task = engine.show_task(1001)
        assert updated_task.body == original_body, (
            "sweep() must preserve the task body with exact equality; "
            "only claimed_at and updated are permitted to change (AC-C52)"
        )

    def test_ac_c52_sweep_does_not_serialize_claimed_by_to_file(
        self, tmp_path: Path
    ) -> None:
        """AC-C52: sweep() must not write 'claimed_by' to a file that didn't contain it.

        task_io.write_task serializes record.model_dump() which includes claimed_by from
        the Task model default. This test asserts that 'claimed_by' does NOT appear in
        the on-disk frontmatter after sweep releases an expired claim.
        """
        kanban_dir = _make_new_board(tmp_path)
        expired_ts = (datetime.now(tz=UTC) - timedelta(hours=3)).isoformat()
        task_content = (
            "---\nid: 1001\ntitle: No CB test\nstatus: in-progress\npriority: needed\n"
            f'created: "2026-04-21T10:00:00+00:00"\nupdated: "2026-04-21T10:00:00+00:00"\n'
            "tags: []\nparent: null\ndepends_on: []\nblocked: false\nblock_reason: null\n"
            f'claimed_at: "{expired_ts}"\narchival_reason: null\narchival_refs: []\n---\n'
        )
        task_file = kanban_dir / "tasks" / "1001-nocb.md"
        task_file.write_text(task_content, encoding="utf-8")
        assert "claimed_by" not in task_content, (
            "precondition: original file has no claimed_by"
        )

        engine = KanbanEngine(kanban_dir)
        released = engine.sweep()

        assert 1001 in released
        written_content = task_file.read_text(encoding="utf-8")
        # Extract frontmatter section only (between first and second ---)
        fm_section = written_content.split("---")[1]
        assert "claimed_by" not in fm_section, (
            "sweep() must not add 'claimed_by' to a file that did not originally contain it; "
            "only claimed_at and updated are permitted to change (AC-C52)"
        )

    def test_ac_c52_sweep_with_cleared_legacy_claimed_by(self, tmp_path: Path) -> None:
        """AC-C52: sweep() on a file with cleared legacy 'claimed_by: null' + expired claim.

        AC-C47 (refined) now allows 'claimed_by: null' in tasks/ files as an already-cleared
        value. This regression guard ensures that sweep() still releases the expired claim
        on such files and applies expected normalization:
          - body preserved exactly
          - claimed_at cleared (null / absent)
          - updated advanced
          - claimed_by absent in written frontmatter (schema normalization via write_task)

        The implementation sets record.claimed_by = None in sweep() and write_task strips
        the field entirely — this is expected behaviour, not mutation beyond the AC.
        """
        kanban_dir = _make_new_board(tmp_path)
        original_updated = "2026-04-21T10:00:00+00:00"
        expired_ts = (datetime.now(tz=UTC) - timedelta(hours=3)).isoformat()
        original_body = "\n## Notes\n\nLegacy claimed_by null body — must survive sweep unchanged.\n"
        task_content = (
            "---\nid: 1001\ntitle: Legacy CB null test\nstatus: in-progress\npriority: needed\n"
            f'created: "{original_updated}"\nupdated: "{original_updated}"\n'
            "tags: []\nparent: null\ndepends_on: []\nblocked: false\nblock_reason: null\n"
            f'claimed_at: "{expired_ts}"\nclaimed_by: null\narchival_reason: null\narchival_refs: []\n---\n'
            + original_body
        )
        task_file = kanban_dir / "tasks" / "1001-legacy-cb.md"
        task_file.write_text(task_content, encoding="utf-8")

        before = datetime.now(tz=UTC)
        engine = KanbanEngine(kanban_dir)
        released = engine.sweep()

        # Claim released
        assert 1001 in released, (
            "sweep() must release the expired claim on a claimed_by:null file"
        )

        # Model-level checks (claimed_at, updated)
        updated_task = engine.show_task(1001)
        assert updated_task.claimed_at is None, "sweep() must clear claimed_at (AC-C52)"
        updated_dt = datetime.fromisoformat(updated_task.updated)
        if updated_dt.tzinfo is None:
            updated_dt = updated_dt.replace(tzinfo=UTC)
        assert updated_dt >= before, "sweep() must advance updated timestamp (AC-C52)"

        # Raw-file checks (claimed_by absent)
        written_content = task_file.read_text(encoding="utf-8")
        fm_section = written_content.split("---", 2)[1]

        # claimed_by absent from written frontmatter (expected schema normalization)
        assert "claimed_by" not in fm_section, (
            "write_task must strip claimed_by from disk; schema normalization applies to all "
            "write paths including sweep (AC-C52 refined)"
        )

        # body preserved exactly (use model API — same pattern as test_ac_c52_sweep_preserves_body_exactly)
        assert updated_task.body == original_body, (
            "sweep() must not mutate the task body; only claim fields and updated may change (AC-C52)"
        )


# ---------------------------------------------------------------------------
# TestFromAC_RepairStorage — AC-C24, AC-C25, AC-C26
# ---------------------------------------------------------------------------


class TestFromAC_RepairStorage:
    """AC-C24, AC-C25, AC-C26: repair_storage() two-phase quarantine + AR contract."""

    def test_ac_c24_file_moved_before_ar_creation(self, tmp_path: Path) -> None:
        """AC-C24: corrupt file is quarantined BEFORE AR task creation attempt.

        Asserts both that the quarantine destination exists AND that the original
        tasks/ file is already gone at the moment create_task() is entered.
        """
        kanban_dir = _make_new_board(tmp_path)
        corrupt_file = kanban_dir / "tasks" / "1001-corrupt.md"
        corrupt_file.write_text(_CORRUPT_TASK, encoding="utf-8")

        quarantine_check: list[bool] = []
        original_gone_check: list[bool] = []
        original_create = KanbanEngine.create_task

        def spy_create(
            self_engine: KanbanEngine, *args: object, **kwargs: object
        ) -> object:
            quarantine_file = kanban_dir / "quarantine" / "1001-corrupt.md"
            quarantine_check.append(quarantine_file.exists())
            original_gone_check.append(
                not corrupt_file.exists()
            )  # original must be GONE
            return original_create(self_engine, *args, **kwargs)

        with patch.object(KanbanEngine, "create_task", side_effect=spy_create):
            engine = KanbanEngine(kanban_dir)
            engine.repair_storage()

        # Quarantine destination existed when create_task was entered
        assert quarantine_check
        assert all(quarantine_check)
        # Original corrupt file was already gone from tasks/ at that moment (§4.4 move-before-AR)
        assert original_gone_check
        assert all(original_gone_check), (
            "corrupt file must be GONE from tasks/ before AR creation attempt (AC-C24 §4.4)"
        )

    def test_ac_c25_repair_records_failed_when_ar_creation_fails(
        self, tmp_path: Path
    ) -> None:
        """AC-C25: if AR creation fails, outcome.action='failed'; file remains quarantined."""
        kanban_dir = _make_new_board(tmp_path)
        corrupt_file = kanban_dir / "tasks" / "1001-corrupt.md"
        corrupt_file.write_text(_CORRUPT_TASK, encoding="utf-8")

        def raise_on_create(
            _self_engine: KanbanEngine, *_args: object, **_kwargs: object
        ) -> object:
            msg = "simulated AR creation failure"
            raise OSError(msg)

        with patch.object(KanbanEngine, "create_task", side_effect=raise_on_create):
            engine = KanbanEngine(kanban_dir)
            outcomes = engine.repair_storage()

        failed = [o for o in outcomes if o.action == "failed"]
        assert failed, "Expected at least one action='failed' outcome"
        # File still in quarantine
        assert (kanban_dir / "quarantine" / "1001-corrupt.md").exists()

    def test_ac_c25_original_tasks_file_absent_after_ar_creation_fails(
        self, tmp_path: Path
    ) -> None:
        """AC-C25: after AR creation fails, the original tasks/ file is NOT restored.

        Divergent from test_ac_c25_repair_records_failed_when_ar_creation_fails:
        this test directly asserts the tasks/ path is absent, not only that the
        quarantine copy exists. An implementation that moves the file back from
        quarantine on AR failure would fail this assertion.
        """
        kanban_dir = _make_new_board(tmp_path)
        tasks_path = kanban_dir / "tasks" / "1001-corrupt.md"
        tasks_path.write_text(_CORRUPT_TASK, encoding="utf-8")

        def raise_on_create(
            _self_engine: KanbanEngine, *_args: object, **_kwargs: object
        ) -> object:
            msg = "simulated AR creation failure"
            raise OSError(msg)

        with patch.object(KanbanEngine, "create_task", side_effect=raise_on_create):
            engine = KanbanEngine(kanban_dir)
            engine.repair_storage()

        # Original tasks/ path must be absent — file must not be restored after AR failure.
        assert not tasks_path.exists(), (
            "tasks/1001-corrupt.md must remain absent after failed AR creation (AC-C25)"
        )

    def test_ac_c26_duplicate_location_resolved_archive_wins(
        self, tmp_path: Path
    ) -> None:
        """AC-C26: ERR_CORRUPT_DUPLICATE_LOCATION → archive file wins; tasks/ file removed.

        Uses DIVERGENT content so an implementation that clobbers the archive with the
        tasks/ copy (or vice-versa) is detected by the content assertion.
        """
        kanban_dir = _make_new_board(tmp_path)
        # Archive copy has "Archive body" — tasks/ copy has "Tasks body".
        # The two differ so we can assert archive content is preserved verbatim.
        archive_content = _VALID_TASK.format(task_id=1001).replace(
            "Content.", "Archive body."
        )
        tasks_content = _VALID_TASK.format(task_id=1001).replace(
            "Content.", "Tasks body."
        )
        assert archive_content != tasks_content  # guard: fixtures must differ

        (kanban_dir / "archive" / "1001-active.md").write_text(
            archive_content, encoding="utf-8"
        )
        (kanban_dir / "tasks" / "1001-active.md").write_text(
            tasks_content, encoding="utf-8"
        )

        engine = KanbanEngine(kanban_dir)
        engine.repair_storage()

        # Archive file survives with its original content intact
        assert (kanban_dir / "archive" / "1001-active.md").exists()
        assert (kanban_dir / "archive" / "1001-active.md").read_text(
            encoding="utf-8"
        ) == archive_content
        # tasks/ file gone (moved to quarantine or removed)
        assert not (kanban_dir / "tasks" / "1001-active.md").exists()


# ---------------------------------------------------------------------------
# TestFromAC_MigrationGate — AC-C47
# ---------------------------------------------------------------------------


class TestFromAC_MigrationGate:
    """AC-C47: KanbanEngine.__init__ raises MigrationRequiredError if any tasks/ file has claimed_by."""

    def test_ac_c47_raises_on_claimed_by_in_tasks(self, tmp_path: Path) -> None:
        """AC-C47: __init__ raises MigrationRequiredError if tasks/ contains claimed_by."""
        kanban_dir = _make_new_board(tmp_path)
        (kanban_dir / "tasks" / "1001-legacy.md").write_text(
            "---\nid: 1001\ntitle: legacy\nstatus: todo\npriority: needed\n"
            "claimed_by: some-agent\n"
            'created: "2026-04-21T10:00:00+00:00"\nupdated: "2026-04-21T10:00:00+00:00"\n---\n',
            encoding="utf-8",
        )

        with pytest.raises(MigrationRequiredError) as exc_info:
            KanbanEngine(kanban_dir)

        assert exc_info.value.code == "ERR_MIGRATION_REQUIRED"
        assert "kanban-migrate" in (exc_info.value.user_message or "").lower()

    def test_ac_c47_no_error_when_no_claimed_by(self, tmp_path: Path) -> None:
        """AC-C47: __init__ succeeds when no tasks/ file has claimed_by."""
        kanban_dir = _make_new_board(tmp_path)
        (kanban_dir / "tasks" / "1001-modern.md").write_text(
            _VALID_TASK.format(task_id=1001), encoding="utf-8"
        )
        # Must not raise
        engine = KanbanEngine(kanban_dir)
        assert engine is not None

    def test_ac_c47_migration_error_has_err_migration_required_code(
        self, _tmp_path: Path
    ) -> None:
        """AC-C47: MigrationRequiredError carries code='ERR_MIGRATION_REQUIRED'."""
        err = MigrationRequiredError(
            code="ERR_MIGRATION_REQUIRED",
            user_message="run uv run kanban-migrate",
        )
        assert err.code == "ERR_MIGRATION_REQUIRED"

    def test_ac_c47_claimed_by_null_does_not_raise(self, tmp_path: Path) -> None:
        """AC-C47 (refined): claimed_by: null is treated as already-cleared — no migration error.

        YAML null is a cleared field remnant, not an active legacy claim.
        Regression guard for AC-C47 refinement from arch review cycle 3.
        """
        kanban_dir = _make_new_board(tmp_path)
        (kanban_dir / "tasks" / "1001-nullcb.md").write_text(
            "---\nid: 1001\ntitle: null cb\nstatus: todo\npriority: needed\n"
            "claimed_by: null\n"
            'created: "2026-04-21T10:00:00+00:00"\nupdated: "2026-04-21T10:00:00+00:00"\n'
            "tags: []\nparent: null\ndepends_on: []\nblocked: false\nblock_reason: null\n"
            "claimed_at: null\narchival_reason: null\narchival_refs: []\n---\n",
            encoding="utf-8",
        )
        # Must not raise — null claimed_by is a cleared field, not a migration target
        engine = KanbanEngine(kanban_dir)
        assert engine is not None

    def test_ac_c47_claimed_by_tilde_does_not_raise(self, tmp_path: Path) -> None:
        """AC-C47 (refined): claimed_by: ~ is treated as already-cleared — no migration error.

        YAML tilde (~) is the shorthand null variant; treated identically to null.
        Regression guard for AC-C47 refinement from arch review cycle 3.
        """
        kanban_dir = _make_new_board(tmp_path)
        (kanban_dir / "tasks" / "1001-tildecb.md").write_text(
            "---\nid: 1001\ntitle: tilde cb\nstatus: todo\npriority: needed\n"
            "claimed_by: ~\n"
            'created: "2026-04-21T10:00:00+00:00"\nupdated: "2026-04-21T10:00:00+00:00"\n'
            "tags: []\nparent: null\ndepends_on: []\nblocked: false\nblock_reason: null\n"
            "claimed_at: null\narchival_reason: null\narchival_refs: []\n---\n",
            encoding="utf-8",
        )
        # Must not raise — tilde is YAML null shorthand, treated as cleared field
        engine = KanbanEngine(kanban_dir)
        assert engine is not None

    def test_ac_c47_claimed_by_empty_does_not_raise(self, tmp_path: Path) -> None:
        """AC-C47 (refined): claimed_by: '' (empty) is treated as already-cleared — no migration error.

        An empty claimed_by value indicates an already-cleared field (e.g. from a legacy
        migration tool that zero-filled rather than deleted the key). Not a migration target.
        Regression guard for AC-C47 refinement from arch review cycle 3.
        """
        kanban_dir = _make_new_board(tmp_path)
        (kanban_dir / "tasks" / "1001-emptycb.md").write_text(
            "---\nid: 1001\ntitle: empty cb\nstatus: todo\npriority: needed\n"
            'claimed_by: ""\n'
            'created: "2026-04-21T10:00:00+00:00"\nupdated: "2026-04-21T10:00:00+00:00"\n'
            "tags: []\nparent: null\ndepends_on: []\nblocked: false\nblock_reason: null\n"
            "claimed_at: null\narchival_reason: null\narchival_refs: []\n---\n",
            encoding="utf-8",
        )
        # Must not raise — empty string claimed_by is already-cleared, not a migration target
        engine = KanbanEngine(kanban_dir)
        assert engine is not None

    def test_ac_c47_claimed_by_quoted_null_raises(self, tmp_path: Path) -> None:
        """AC-C47 (refined): claimed_by: "null" (quoted string) MUST raise MigrationRequiredError.

        A YAML quoted string "null" is a non-empty string value, NOT a null sentinel.
        The refined AC-C47 distinguishes unquoted null/~ (treated as cleared) from
        quoted non-empty strings including "null" and "~" (must trigger migration).

        Current implementation strips surrounding quotes before checking the skip list,
        so it incorrectly treats claimed_by: "null" as cleared — this test catches that.
        """
        kanban_dir = _make_new_board(tmp_path)
        (kanban_dir / "tasks" / "1001-quotednull.md").write_text(
            "---\nid: 1001\ntitle: quoted null\nstatus: todo\npriority: needed\n"
            'claimed_by: "null"\n'
            'created: "2026-04-21T10:00:00+00:00"\nupdated: "2026-04-21T10:00:00+00:00"\n'
            "tags: []\nparent: null\ndepends_on: []\nblocked: false\nblock_reason: null\n"
            "claimed_at: null\narchival_reason: null\narchival_refs: []\n---\n",
            encoding="utf-8",
        )
        # Must raise — claimed_by: "null" is a non-empty quoted string, not a YAML null
        with pytest.raises(MigrationRequiredError) as exc_info:
            KanbanEngine(kanban_dir)
        assert exc_info.value.code == "ERR_MIGRATION_REQUIRED"

    def test_ac_c47_claimed_by_quoted_tilde_raises(self, tmp_path: Path) -> None:
        """AC-C47 (refined): claimed_by: "~" (quoted string) MUST raise MigrationRequiredError.

        A YAML quoted string "~" is a non-empty string value, NOT the YAML null shorthand.
        The refined AC-C47 treats only unquoted ~ as null-equivalent; the quoted form
        is a real (possibly agent-name-like) string and must trigger migration detection.

        Current implementation strips quotes before checking the skip list, so it
        incorrectly treats claimed_by: "~" as cleared — this test catches that.
        """
        kanban_dir = _make_new_board(tmp_path)
        (kanban_dir / "tasks" / "1001-quotedtilde.md").write_text(
            "---\nid: 1001\ntitle: quoted tilde\nstatus: todo\npriority: needed\n"
            'claimed_by: "~"\n'
            'created: "2026-04-21T10:00:00+00:00"\nupdated: "2026-04-21T10:00:00+00:00"\n'
            "tags: []\nparent: null\ndepends_on: []\nblocked: false\nblock_reason: null\n"
            "claimed_at: null\narchival_reason: null\narchival_refs: []\n---\n",
            encoding="utf-8",
        )
        # Must raise — claimed_by: "~" is a non-empty quoted string, not the YAML null shorthand
        with pytest.raises(MigrationRequiredError) as exc_info:
            KanbanEngine(kanban_dir)
        assert exc_info.value.code == "ERR_MIGRATION_REQUIRED"


# ---------------------------------------------------------------------------
# TestFromAC_ParseDuration — AC-C49, AC-C50
# ---------------------------------------------------------------------------


class TestFromAC_ParseDuration:
    """AC-C49, AC-C50: _parse_duration and eager BoardConfig validation."""

    def test_ac_c49_parse_duration_30m(self) -> None:
        """AC-C49: _parse_duration('30m') returns timedelta(minutes=30)."""
        from owlbear_kanban._duration import (
            _parse_duration,
        )  # NEW function signature  # noqa: PLC0415

        result = _parse_duration("30m")
        assert result == timedelta(minutes=30)

    def test_ac_c49_parse_duration_1h(self) -> None:
        """AC-C49: _parse_duration('1h') returns timedelta(hours=1)."""
        from owlbear_kanban._duration import _parse_duration  # noqa: PLC0415

        result = _parse_duration("1h")
        assert result == timedelta(hours=1)

    def test_ac_c49_parse_duration_2h30m(self) -> None:
        """AC-C49: _parse_duration('2h30m') returns timedelta(hours=2, minutes=30)."""
        from owlbear_kanban._duration import _parse_duration  # noqa: PLC0415

        result = _parse_duration("2h30m")
        assert result == timedelta(hours=2, minutes=30)

    def test_ac_c49_malformed_raises_config_error(self) -> None:
        """AC-C49: _parse_duration with malformed input raises ConfigError(code=ERR_INVALID_CLAIM_TIMEOUT)."""
        from owlbear_kanban._duration import _parse_duration  # noqa: PLC0415
        from owlbear_kanban.models import (
            ConfigError,
        )  # NEW exception type  # noqa: PLC0415

        with pytest.raises(ConfigError) as exc_info:
            _parse_duration("not_valid_duration")
        assert exc_info.value.code == "ERR_INVALID_CLAIM_TIMEOUT"

    def test_ac_c50_board_config_eager_validation_on_load(self) -> None:
        """AC-C50: _parse_duration with invalid claim_timeout raises ConfigError at parse time.

        With the topology-constant refactor, load_config uses PRODUCT_TOPOLOGY claim_timeout
        and ignores config.yml values, so we test _parse_duration directly — the validation
        is eager (raises at call time, not lazily).
        """
        from owlbear_kanban.config_loader import _parse_duration  # noqa: PLC0415
        from owlbear_kanban.models import ConfigError  # noqa: PLC0415

        with pytest.raises(ConfigError) as exc_info:
            _parse_duration("BADVALUE")
        assert exc_info.value.code == "ERR_INVALID_CLAIM_TIMEOUT"

    def test_ac_c50_valid_claim_timeout_loads_without_error(
        self, tmp_path: Path
    ) -> None:
        """AC-C50: valid claim_timeout format does not raise at config load time."""
        kanban_dir = _make_new_board(tmp_path)
        config = load_config(kanban_dir)
        assert config is not None

    def test_ac_c50_config_load_calls_parse_duration_not_only_regex(
        self, tmp_path: Path
    ) -> None:
        """AC-C50: config_loader.load_config must call _duration._parse_duration at load time.

        The AC states 'BoardConfig validation calls _parse_duration(claim_timeout) at
        config load time (eager validation)'. KanbanEngine.__init__ uses
        config_loader.load_config (engine.py:39/328), NOT storage.load_config.
        config_loader.load_config currently returns at BoardConfig.model_validate() before
        _validate_claim_timeout() is wired in — so _parse_duration is never reached via
        this path. This test targets the actual engine load path and asserts the spy is
        called exactly once.
        """
        import owlbear_kanban.config_loader as _config_loader  # noqa: PLC0415

        kanban_dir = _make_new_board(tmp_path)
        with patch.object(
            _config_loader,
            "_parse_duration",
            wraps=_config_loader._parse_duration,
        ) as mock_pd:
            _config_loader.load_config(
                kanban_dir
            )  # real engine path (not storage.load_config)
        mock_pd.assert_called_once()  # FAILS: config_loader.load_config returns before _validate_claim_timeout


# ---------------------------------------------------------------------------
# TestFromAC_ARCreationSignature — AC-C54
# ---------------------------------------------------------------------------


class TestFromAC_ARCreationSignature:
    """AC-C54: repair_storage() creates AR tasks using body=str, no status argument."""

    def test_ac_c54_create_task_called_with_body_str_no_status(
        self, tmp_path: Path
    ) -> None:
        """AC-C54: AR creation uses keyword body=str (markdown) and does NOT pass status."""
        kanban_dir = _make_new_board(tmp_path)
        (kanban_dir / "tasks" / "1001-corrupt.md").write_text(
            _CORRUPT_TASK, encoding="utf-8"
        )

        captured_calls: list[dict] = []
        original_create = KanbanEngine.create_task

        def spy_create(  # noqa: PLR0913
            self_engine: KanbanEngine,
            title: str,
            *,
            body: str = "",
            tags: list[str] | None = None,
            priority: str = "",
            status: str = "",
            parent: int | None = None,
            depends_on: list[int] | None = None,
        ) -> object:
            captured_calls.append(
                {
                    "title": title,
                    "body": body,
                    "body_is_str": isinstance(body, str),
                    "status": status,
                    "tags": tags,
                }
            )
            return original_create(
                self_engine,
                title,
                body=body,
                tags=tags,
                priority=priority,
                status=status,
                parent=parent,
                depends_on=depends_on,
            )

        with patch.object(KanbanEngine, "create_task", side_effect=spy_create):
            engine = KanbanEngine(kanban_dir)
            engine.repair_storage()

        assert captured_calls, "Expected create_task to be called for AR"
        for call in captured_calls:
            assert call["body_is_str"], "body must be str (markdown), not list[Section]"
            assert call["status"] == "", (
                "status must NOT be passed (no status arg per Brief B D50)"
            )

    def test_ac_c54_status_not_explicitly_passed_in_create_task_kwargs(
        self, tmp_path: Path
    ) -> None:
        """AC-C54: AR creation must NOT pass 'status' as an explicit keyword argument.

        Distinguishes `create_task(..., status='')` (explicit — forbidden) from
        `create_task(...)` (omitted — correct). Uses **kwargs capture to observe
        only the arguments that were genuinely passed, not defaults.
        """
        kanban_dir = _make_new_board(tmp_path)
        (kanban_dir / "tasks" / "1001-corrupt.md").write_text(
            _CORRUPT_TASK, encoding="utf-8"
        )

        captured_kwargs: list[set[str]] = []
        original_create = KanbanEngine.create_task

        def spy_create_kwargs(
            self_engine: KanbanEngine, *args: object, **kwargs: object
        ) -> object:
            captured_kwargs.append(set(kwargs.keys()))
            return original_create(self_engine, *args, **kwargs)

        with patch.object(KanbanEngine, "create_task", side_effect=spy_create_kwargs):
            engine = KanbanEngine(kanban_dir)
            engine.repair_storage()

        assert captured_kwargs, "Expected create_task to be called for AR"
        for kwarg_keys in captured_kwargs:
            assert "status" not in kwarg_keys, (
                "repair_storage() must NOT explicitly pass 'status' to create_task; "
                "omit it entirely so Brief B defaults apply"
            )
