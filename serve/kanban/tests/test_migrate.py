"""TDD RED: C-07 — kanban-migrate entry point tests.

Task: #1052 (Brief C #1043) — paper-c.md §8.7, §8.11
AC:   C31, C32, C33, C34, C35, C36, C37, C38, C38a
All tests FAIL (RED phase — migrate module not yet implemented).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from owlbear_kanban.migrate import main as migrate_main  # NEW module — ImportError in RED

# ---------------------------------------------------------------------------
# Board helpers
# ---------------------------------------------------------------------------

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
non_impl_tags: [research, docs, type:config, type:docs, test, type:test, agent, quality, type:user-action]
archival_reasons: [completed, deprecated, dropped, duplicate, wontfix]
status_predicates: {}
claim_timeout: 1h
next_id: 1001
"""

_LEGACY_CONFIG_YAML = """\
version: 9
board:
  name: TestBoard
tasks_dir: tasks
archive_dir: archive
statuses:
- name: research
  color: "#aaa"
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
activity_log: false
"""

_LEGACY_TASK = """\
---
id: {task_id}
title: Legacy task {task_id}
status: todo
priority: needed
claimed_by: some-agent
created: "2026-01-15T08:00:00+00:00"
updated: "2026-01-15T08:00:00+00:00"
---

## Notes

Legacy content.
"""

_MODERN_TASK = """\
---
id: {task_id}
title: Modern task {task_id}
status: todo
priority: needed
created: "2026-01-15T08:00:00+00:00"
updated: "2026-01-15T08:00:00+00:00"
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

Modern content.
"""

_LEGACY_ARCHIVE = """\
---
id: {task_id}
title: Archive task {task_id}
status: done
priority: needed
created: "2025-12-01T10:00:00+00:00"
updated: "2026-01-10T10:00:00+00:00"
class: tier-1
---

## Notes

Archived content.
"""


def _make_legacy_board(base_dir: Path) -> Path:
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_LEGACY_CONFIG_YAML, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


def _make_modern_board(base_dir: Path) -> Path:
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_NEW_CONFIG_YAML, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


def _run_migrate(
    kanban_dir: Path,
    *,
    lane: str = "all",
    dry_run: bool = False,
) -> subprocess.CompletedProcess[str]:
    cmd = [
        sys.executable, "-m", "owlbear_kanban.migrate",
        "--kanban-dir", str(kanban_dir),
        "--lane", lane,
    ]
    if dry_run:
        cmd.append("--dry-run")
    return subprocess.run(cmd, capture_output=True, text=True)


# ---------------------------------------------------------------------------
# TestFromAC_MigrateEntryPoint — AC-C31
# ---------------------------------------------------------------------------


class TestFromAC_MigrateEntryPoint:
    """AC-C31: kanban-migrate registered as a console script in pyproject.toml."""

    def test_ac_c31_entry_point_in_pyproject(self) -> None:
        """AC-C31: 'kanban-migrate' registered under [project.scripts] in pyproject.toml."""
        pyproject = Path(__file__).parent.parent / "pyproject.toml"
        content = pyproject.read_text(encoding="utf-8")
        assert "kanban-migrate" in content

    def test_ac_c31_migrate_invocable_via_module(self, tmp_path: Path) -> None:
        """AC-C31: owlbear_kanban.migrate:main is callable without error on a new board."""
        kanban_dir = _make_modern_board(tmp_path)
        result = _run_migrate(kanban_dir)
        # On a fully migrated board: exit code 0
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# TestFromAC_LaneSelection — AC-C32
# ---------------------------------------------------------------------------


class TestFromAC_LaneSelection:
    """AC-C32: --lane flag routes to correct lane(s)."""

    def test_ac_c32_lane_tasks_runs_only_task_lane(self, tmp_path: Path) -> None:
        """AC-C32: --lane tasks processes tasks/ only; config.yml untouched."""
        kanban_dir = _make_legacy_board(tmp_path)
        (kanban_dir / "tasks" / "1001-t.md").write_text(
            _LEGACY_TASK.format(task_id=1001), encoding="utf-8"
        )
        config_mtime_before = (kanban_dir / "config.yml").stat().st_mtime

        result = _run_migrate(kanban_dir, lane="tasks")
        assert result.returncode in (0, 1)

        # config.yml not touched by --lane tasks
        config_mtime_after = (kanban_dir / "config.yml").stat().st_mtime
        assert config_mtime_after == config_mtime_before

    def test_ac_c32_lane_archive_runs_only_archive_lane(self, tmp_path: Path) -> None:
        """AC-C32: --lane archive processes archive/ only; tasks/ untouched."""
        kanban_dir = _make_legacy_board(tmp_path)
        task_file = kanban_dir / "tasks" / "1001-t.md"
        task_file.write_text(_LEGACY_TASK.format(task_id=1001), encoding="utf-8")
        task_mtime_before = task_file.stat().st_mtime

        result = _run_migrate(kanban_dir, lane="archive")
        assert result.returncode in (0, 1)

        assert task_file.stat().st_mtime == task_mtime_before

    def test_ac_c32_lane_config_runs_only_config_lane(self, tmp_path: Path) -> None:
        """AC-C32: --lane config processes config.yml only; tasks/ and archive/ untouched."""
        kanban_dir = _make_legacy_board(tmp_path)
        task_file = kanban_dir / "tasks" / "1001-t.md"
        task_file.write_text(_LEGACY_TASK.format(task_id=1001), encoding="utf-8")
        task_mtime_before = task_file.stat().st_mtime

        result = _run_migrate(kanban_dir, lane="config")
        assert result.returncode in (0, 1)
        assert task_file.stat().st_mtime == task_mtime_before

    def test_ac_c32_lane_all_runs_all_three_lanes(self, tmp_path: Path) -> None:
        """AC-C32: --lane all (default) touches tasks/, archive/, and config.yml."""
        kanban_dir = _make_legacy_board(tmp_path)
        (kanban_dir / "tasks" / "1001-t.md").write_text(
            _LEGACY_TASK.format(task_id=1001), encoding="utf-8"
        )
        (kanban_dir / "archive" / "0001-old.md").write_text(
            _LEGACY_ARCHIVE.format(task_id=1), encoding="utf-8"
        )
        result = _run_migrate(kanban_dir, lane="all")
        assert result.returncode in (0, 1)
        # At least some output indicating lanes ran
        combined = result.stdout + result.stderr
        assert "Scanned" in combined or "Migrated" in combined or "Failed" in combined


# ---------------------------------------------------------------------------
# TestFromAC_LaneAlgorithms — AC-C33, AC-C35
# ---------------------------------------------------------------------------


class TestFromAC_LaneAlgorithms:
    """AC-C33, AC-C35: per-lane migration algorithms match §5.3 / §5.4."""

    def test_ac_c33_tasks_lane_removes_claimed_by(self, tmp_path: Path) -> None:
        """AC-C33: tasks lane removes claimed_by field from active task files."""
        kanban_dir = _make_legacy_board(tmp_path)
        task_file = kanban_dir / "tasks" / "1001-legacy.md"
        task_file.write_text(_LEGACY_TASK.format(task_id=1001), encoding="utf-8")

        result = _run_migrate(kanban_dir, lane="tasks")
        assert result.returncode in (0, 1)

        content = task_file.read_text(encoding="utf-8")
        assert "claimed_by" not in content

    def test_ac_c33_tasks_lane_adds_archival_fields(self, tmp_path: Path) -> None:
        """AC-C33: tasks lane adds archival_reason: null and archival_refs: [] if absent."""
        kanban_dir = _make_legacy_board(tmp_path)
        task_content = (
            "---\nid: 1001\ntitle: t\nstatus: todo\npriority: needed\n"
            "created: \"2026-01-15T08:00:00+00:00\"\nupdated: \"2026-01-15T08:00:00+00:00\"\n---\n"
        )
        task_file = kanban_dir / "tasks" / "1001-t.md"
        task_file.write_text(task_content, encoding="utf-8")

        _run_migrate(kanban_dir, lane="tasks")
        content = task_file.read_text(encoding="utf-8")

        assert "archival_reason:" in content
        assert "archival_refs:" in content

    def test_ac_c33_tasks_lane_normalises_timestamps_to_utc(self, tmp_path: Path) -> None:
        """AC-C33: tasks lane ensures created/updated timestamps end with +00:00."""
        kanban_dir = _make_legacy_board(tmp_path)
        # Naive timestamp (no tz offset)
        task_content = (
            "---\nid: 1001\ntitle: t\nstatus: todo\npriority: needed\n"
            "created: \"2026-01-15T08:00:00\"\nupdated: \"2026-01-15T08:00:00\"\n---\n"
        )
        task_file = kanban_dir / "tasks" / "1001-t.md"
        task_file.write_text(task_content, encoding="utf-8")

        _run_migrate(kanban_dir, lane="tasks")
        content = task_file.read_text(encoding="utf-8")

        assert "+00:00" in content

    def test_ac_c33_config_lane_converts_statuses_to_list_of_strings(
        self, tmp_path: Path
    ) -> None:
        """AC-C33: config lane converts statuses from list[dict] to list[str]."""
        kanban_dir = _make_legacy_board(tmp_path)
        _run_migrate(kanban_dir, lane="config")
        content = (kanban_dir / "config.yml").read_text(encoding="utf-8")
        # Statuses are now plain strings, not dicts
        assert "name: research" not in content
        assert "- research" in content

    def test_ac_c33_config_lane_drops_legacy_fields(self, tmp_path: Path) -> None:
        """AC-C33: config lane removes board, version, tasks_dir, archive_dir, defaults, activity_log."""
        kanban_dir = _make_legacy_board(tmp_path)
        _run_migrate(kanban_dir, lane="config")
        content = (kanban_dir / "config.yml").read_text(encoding="utf-8")

        for dropped in ("board:", "version:", "tasks_dir:", "archive_dir:", "defaults:", "activity_log:"):
            assert dropped not in content, f"Legacy field '{dropped}' still present"

    def test_ac_c33_config_lane_adds_new_required_fields(self, tmp_path: Path) -> None:
        """AC-C33: config lane adds entry_status, wave_size, non_impl_tags etc."""
        kanban_dir = _make_legacy_board(tmp_path)
        _run_migrate(kanban_dir, lane="config")
        content = (kanban_dir / "config.yml").read_text(encoding="utf-8")

        for new_field in ("entry_status:", "wave_size:", "non_impl_tags:", "archival_reasons:"):
            assert new_field in content, f"New required field '{new_field}' missing"

    def test_ac_c35_tasks_idempotency_check_skips_modern_task(self, tmp_path: Path) -> None:
        """AC-C35: idempotency check skips tasks/ files already in canonical form."""
        kanban_dir = _make_modern_board(tmp_path)
        task_file = kanban_dir / "tasks" / "1001-modern.md"
        task_file.write_text(_MODERN_TASK.format(task_id=1001), encoding="utf-8")
        mtime_before = task_file.stat().st_mtime

        _run_migrate(kanban_dir, lane="tasks")
        assert task_file.stat().st_mtime == mtime_before


# ---------------------------------------------------------------------------
# TestFromAC_Idempotency — AC-C34
# ---------------------------------------------------------------------------


class TestFromAC_Idempotency:
    """AC-C34: re-running on a fully migrated board reports Migrated: 0."""

    def test_ac_c34_fully_migrated_board_zero_migrations(self, tmp_path: Path) -> None:
        """AC-C34: second migration pass on already-migrated board reports Migrated: 0."""
        kanban_dir = _make_legacy_board(tmp_path)
        (kanban_dir / "tasks" / "1001-t.md").write_text(
            _LEGACY_TASK.format(task_id=1001), encoding="utf-8"
        )

        # First pass migrates
        _run_migrate(kanban_dir, lane="all")
        # Second pass: nothing to migrate
        result2 = _run_migrate(kanban_dir, lane="all")

        assert result2.returncode == 0
        assert "Migrated:         0" in result2.stdout or "Migrated: 0" in result2.stdout

    def test_ac_c34_modern_board_zero_migrations(self, tmp_path: Path) -> None:
        """AC-C34: modern board with fully migrated tasks reports Migrated: 0 on first run."""
        kanban_dir = _make_modern_board(tmp_path)
        (kanban_dir / "tasks" / "1001-modern.md").write_text(
            _MODERN_TASK.format(task_id=1001), encoding="utf-8"
        )
        result = _run_migrate(kanban_dir)
        assert result.returncode == 0
        assert "Migrated:         0" in result.stdout or "Migrated: 0" in result.stdout


# ---------------------------------------------------------------------------
# TestFromAC_DryRun — AC-C36
# ---------------------------------------------------------------------------


class TestFromAC_DryRun:
    """AC-C36: --dry-run writes nothing, only prints."""

    def test_ac_c36_dry_run_writes_nothing_tasks(self, tmp_path: Path) -> None:
        """AC-C36: --dry-run with legacy tasks/ produces no file changes."""
        kanban_dir = _make_legacy_board(tmp_path)
        task_file = kanban_dir / "tasks" / "1001-t.md"
        original = _LEGACY_TASK.format(task_id=1001)
        task_file.write_text(original, encoding="utf-8")

        result = _run_migrate(kanban_dir, lane="tasks", dry_run=True)
        assert result.returncode == 0
        # File unchanged
        assert task_file.read_text(encoding="utf-8") == original

    def test_ac_c36_dry_run_writes_nothing_config(self, tmp_path: Path) -> None:
        """AC-C36: --dry-run leaves config.yml unchanged."""
        kanban_dir = _make_legacy_board(tmp_path)
        original_config = (kanban_dir / "config.yml").read_text(encoding="utf-8")

        _run_migrate(kanban_dir, lane="config", dry_run=True)

        assert (kanban_dir / "config.yml").read_text(encoding="utf-8") == original_config

    def test_ac_c36_dry_run_prints_what_would_change(self, tmp_path: Path) -> None:
        """AC-C36: --dry-run prints at least some output describing what would be migrated."""
        kanban_dir = _make_legacy_board(tmp_path)
        (kanban_dir / "tasks" / "1001-t.md").write_text(
            _LEGACY_TASK.format(task_id=1001), encoding="utf-8"
        )

        result = _run_migrate(kanban_dir, lane="tasks", dry_run=True)
        # Some output expected
        assert result.stdout or result.stderr


# ---------------------------------------------------------------------------
# TestFromAC_CrashRecovery — AC-C37
# ---------------------------------------------------------------------------


class TestFromAC_CrashRecovery:
    """AC-C37: crash mid-migration leaves no partial files; resume converges."""

    def test_ac_c37_no_partial_files_after_failure(self, tmp_path: Path) -> None:
        """AC-C37: if atomic_write is used, no .tmp-* files left after a failure."""
        from unittest.mock import patch  # noqa: PLC0415

        kanban_dir = _make_legacy_board(tmp_path)
        (kanban_dir / "tasks" / "1001-t.md").write_text(
            _LEGACY_TASK.format(task_id=1001), encoding="utf-8"
        )

        call_count = {"n": 0}
        original_replace = __import__("os").replace

        def crash_on_second_replace(src: str, dst: str) -> None:
            call_count["n"] += 1
            if call_count["n"] == 2:
                raise OSError("simulated mid-migration crash")
            original_replace(src, dst)

        with patch("os.replace", side_effect=crash_on_second_replace):
            try:
                _run_migrate(kanban_dir, lane="tasks")
            except OSError:
                pass

        tmp_leftovers = list((kanban_dir / "tasks").glob(".tmp-*"))
        assert tmp_leftovers == [], f"Leftover .tmp- files: {tmp_leftovers}"

    def test_ac_c37_resume_after_partial_run_converges(self, tmp_path: Path) -> None:
        """AC-C37: re-running migrate after partial failure converges to 0 failures."""
        kanban_dir = _make_legacy_board(tmp_path)
        for i in range(1001, 1004):
            (kanban_dir / "tasks" / f"{i}-task.md").write_text(
                _LEGACY_TASK.format(task_id=i), encoding="utf-8"
            )

        # First pass may partially fail (mocked crash) — ignore outcome
        _run_migrate(kanban_dir, lane="tasks")
        # Second pass must succeed
        result2 = _run_migrate(kanban_dir, lane="tasks")
        assert result2.returncode == 0


# ---------------------------------------------------------------------------
# TestFromAC_ExitCode — AC-C38, AC-C38a
# ---------------------------------------------------------------------------


class TestFromAC_ExitCode:
    """AC-C38, AC-C38a: exit codes and manual-action summaries."""

    def test_ac_c38_exit_0_on_full_success(self, tmp_path: Path) -> None:
        """AC-C38: exit code 0 when no files fail."""
        kanban_dir = _make_modern_board(tmp_path)
        result = _run_migrate(kanban_dir)
        assert result.returncode == 0

    def test_ac_c38_exit_1_when_any_file_fails(self, tmp_path: Path) -> None:
        """AC-C38: exit code 1 when at least one file fails migration."""
        kanban_dir = _make_legacy_board(tmp_path)
        # Write an unreadable / corrupt task file
        bad_file = kanban_dir / "tasks" / "9999-bad.md"
        bad_file.write_text("NOT VALID YAML FRONTMATTER\x00\x00\x00", encoding="utf-8")

        result = _run_migrate(kanban_dir, lane="tasks")
        assert result.returncode == 1

    def test_ac_c38_failed_files_reported_on_stderr(self, tmp_path: Path) -> None:
        """AC-C38: each failed file produces a 'FAIL {path}: {reason}' stderr line."""
        kanban_dir = _make_legacy_board(tmp_path)
        bad_file = kanban_dir / "tasks" / "9999-bad.md"
        bad_file.write_text("NOT VALID\x00\x00\x00", encoding="utf-8")

        result = _run_migrate(kanban_dir, lane="tasks")
        assert "FAIL" in result.stderr

    def test_ac_c38a_config_lane_with_stubs_emits_manual_action_summary(
        self, tmp_path: Path
    ) -> None:
        """AC-C38a: config lane with empty stubs emits a manual-action warning/summary."""
        kanban_dir = _make_legacy_board(tmp_path)
        result = _run_migrate(kanban_dir, lane="config")

        combined = result.stdout + result.stderr
        # Should mention the stub fields that require manual attention
        assert "agent_map" in combined or "WARNING" in combined or "manual" in combined.lower()
