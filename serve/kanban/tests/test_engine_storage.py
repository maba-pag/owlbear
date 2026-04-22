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
from owlbear_kanban.engine import (
    MigrationRequiredError,
)  # NEW exception — AttributeError in RED
from owlbear_kanban.storage import (  # NEW module — ImportError in RED
    load_config,
)
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
wave_size: 4
agent_map: {}
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


# ---------------------------------------------------------------------------
# TestFromAC_RepairStorage — AC-C24, AC-C25, AC-C26
# ---------------------------------------------------------------------------


class TestFromAC_RepairStorage:
    """AC-C24, AC-C25, AC-C26: repair_storage() two-phase quarantine + AR contract."""

    def test_ac_c24_file_moved_before_ar_creation(self, tmp_path: Path) -> None:
        """AC-C24: corrupt file is quarantined BEFORE AR task creation attempt."""
        kanban_dir = _make_new_board(tmp_path)
        corrupt_file = kanban_dir / "tasks" / "1001-corrupt.md"
        corrupt_file.write_text(_CORRUPT_TASK, encoding="utf-8")

        quarantine_check: list[bool] = []
        original_create = KanbanEngine.create_task

        def spy_create(
            self_engine: KanbanEngine, *args: object, **kwargs: object
        ) -> object:
            quarantine_file = kanban_dir / "quarantine" / "1001-corrupt.md"
            quarantine_check.append(quarantine_file.exists())
            return original_create(self_engine, *args, **kwargs)

        with patch.object(KanbanEngine, "create_task", side_effect=spy_create):
            engine = KanbanEngine(kanban_dir)
            engine.repair_storage()

        # File was already in quarantine when create_task was called
        assert quarantine_check
        assert all(quarantine_check)

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
            raise RuntimeError(msg)

        with patch.object(KanbanEngine, "create_task", side_effect=raise_on_create):
            engine = KanbanEngine(kanban_dir)
            outcomes = engine.repair_storage()

        failed = [o for o in outcomes if o.action == "failed"]
        assert failed, "Expected at least one action='failed' outcome"
        # File still in quarantine
        assert (kanban_dir / "quarantine" / "1001-corrupt.md").exists()

    def test_ac_c26_duplicate_location_resolved_archive_wins(
        self, tmp_path: Path
    ) -> None:
        """AC-C26: ERR_CORRUPT_DUPLICATE_LOCATION → archive file wins; tasks/ file removed."""
        kanban_dir = _make_new_board(tmp_path)
        task_content = _VALID_TASK.format(task_id=1001)
        (kanban_dir / "tasks" / "1001-active.md").write_text(
            task_content, encoding="utf-8"
        )
        (kanban_dir / "archive" / "1001-active.md").write_text(
            task_content, encoding="utf-8"
        )

        engine = KanbanEngine(kanban_dir)
        engine.repair_storage()

        # Archive file survives
        assert (kanban_dir / "archive" / "1001-active.md").exists()
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


# ---------------------------------------------------------------------------
# TestFromAC_ParseDuration — AC-C49, AC-C50
# ---------------------------------------------------------------------------


class TestFromAC_ParseDuration:
    """AC-C49, AC-C50: _parse_duration and eager BoardConfig validation."""

    def test_ac_c49_parse_duration_30m(self) -> None:
        """AC-C49: _parse_duration('30m') returns timedelta(minutes=30)."""
        from owlbear_kanban.engine import (
            _parse_duration,
        )  # NEW function signature  # noqa: PLC0415

        result = _parse_duration("30m")
        assert result == timedelta(minutes=30)

    def test_ac_c49_parse_duration_1h(self) -> None:
        """AC-C49: _parse_duration('1h') returns timedelta(hours=1)."""
        from owlbear_kanban.engine import _parse_duration  # noqa: PLC0415

        result = _parse_duration("1h")
        assert result == timedelta(hours=1)

    def test_ac_c49_parse_duration_2h30m(self) -> None:
        """AC-C49: _parse_duration('2h30m') returns timedelta(hours=2, minutes=30)."""
        from owlbear_kanban.engine import _parse_duration  # noqa: PLC0415

        result = _parse_duration("2h30m")
        assert result == timedelta(hours=2, minutes=30)

    def test_ac_c49_malformed_raises_config_error(self) -> None:
        """AC-C49: _parse_duration with malformed input raises ConfigError(code=ERR_INVALID_CLAIM_TIMEOUT)."""
        from owlbear_kanban.engine import _parse_duration  # noqa: PLC0415
        from owlbear_kanban.models import (
            ConfigError,
        )  # NEW exception type  # noqa: PLC0415

        with pytest.raises(ConfigError) as exc_info:
            _parse_duration("not_valid_duration")
        assert exc_info.value.code == "ERR_INVALID_CLAIM_TIMEOUT"

    def test_ac_c50_board_config_eager_validation_on_load(self, tmp_path: Path) -> None:
        """AC-C50: load_config with invalid claim_timeout raises ConfigError at load time."""
        from owlbear_kanban.models import ConfigError  # noqa: PLC0415

        kanban_dir = _make_new_board(tmp_path)
        bad_config = _NEW_CONFIG_YAML.replace(
            "claim_timeout: 1h", "claim_timeout: BADVALUE"
        )
        (kanban_dir / "config.yml").write_text(bad_config, encoding="utf-8")

        with pytest.raises(ConfigError) as exc_info:
            load_config(kanban_dir)
        assert exc_info.value.code == "ERR_INVALID_CLAIM_TIMEOUT"

    def test_ac_c50_valid_claim_timeout_loads_without_error(
        self, tmp_path: Path
    ) -> None:
        """AC-C50: valid claim_timeout format does not raise at config load time."""
        kanban_dir = _make_new_board(tmp_path)
        config = load_config(kanban_dir)
        assert config is not None


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
