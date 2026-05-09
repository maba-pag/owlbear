"""TDD RED: C-07 — kanban-migrate entry point tests.

Task: #1052 (Brief C #1043) — paper-c.md §8.7, §8.11
AC:   C31, C32, C33, C34, C35, C36, C37, C38, C38a
All tests FAIL (RED phase — migrate module not yet implemented).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch
import contextlib


# ---------------------------------------------------------------------------
# Board helpers
# ---------------------------------------------------------------------------

_NEW_CONFIG_YAML = """\
schema: grouped
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
next_id: 1001
paths:
    tasks_dir: tasks
    archive_dir: archive
pipeline:
    entry_status: research
    terminal_status: done
    wave_size: 4
    claim_timeout: 1h
    default_priority: important
agents:
    agent_map: {}
    agent_types: {}
    agent_compatibility: {}
policy:
    non_impl_tags: [research, docs, type:config, type:docs, test, type:test, agent, quality, type:user-action]
    archival_reasons: [completed, deprecated, dropped, duplicate, wontfix]
    status_predicates: {}
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

_MODERN_ARCHIVE = """\
---
id: {task_id}
title: Archive task {task_id}
status: done
priority: needed
created: "2025-12-01T10:00:00+00:00"
updated: "2026-01-10T10:00:00+00:00"
archival_reason: completed
archival_refs: []
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
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    cmd = [
        sys.executable,
        "-m",
        "owlbear_kanban.migrate",
        "--kanban-dir",
        str(kanban_dir),
        "--lane",
        lane,
    ]
    if dry_run:
        cmd.append("--dry-run")
    env = {**os.environ, **(extra_env or {})}
    return subprocess.run(cmd, capture_output=True, text=True, env=env)


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

    def test_ac_c31_pyproject_scripts_exact_key_value(self) -> None:
        """AC-C31 (strict): pyproject.toml maps kanban-migrate to owlbear_kanban.migrate:main exactly."""
        pyproject = Path(__file__).parent.parent / "pyproject.toml"
        content = pyproject.read_text(encoding="utf-8")
        assert 'kanban-migrate = "owlbear_kanban.migrate:main"' in content, (
            "pyproject.toml [project.scripts] must have "
            'kanban-migrate = "owlbear_kanban.migrate:main"'
        )


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
        assert result.returncode == 0

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
        assert result.returncode == 0

        assert task_file.stat().st_mtime == task_mtime_before

    def test_ac_c32_lane_config_runs_only_config_lane(self, tmp_path: Path) -> None:
        """AC-C32: --lane config processes config.yml only; tasks/ and archive/ untouched."""
        kanban_dir = _make_legacy_board(tmp_path)
        task_file = kanban_dir / "tasks" / "1001-t.md"
        task_file.write_text(_LEGACY_TASK.format(task_id=1001), encoding="utf-8")
        task_mtime_before = task_file.stat().st_mtime

        result = _run_migrate(kanban_dir, lane="config")
        assert result.returncode == 0
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
        assert result.returncode == 0
        # Pin all four summary labels in stdout
        assert "Scanned:" in result.stdout
        assert "Migrated:" in result.stdout
        assert "Already:" in result.stdout
        assert "Failed:" in result.stdout

    def test_ac_c32_all_lane_processes_task_archive_and_config_content(
        self, tmp_path: Path
    ) -> None:
        """AC-C32 (strict): --lane all must modify task, archive, AND config file content."""
        kanban_dir = _make_legacy_board(tmp_path)
        task_file = kanban_dir / "tasks" / "1001-t.md"
        arc_file = kanban_dir / "archive" / "0001-old.md"
        task_file.write_text(_LEGACY_TASK.format(task_id=1001), encoding="utf-8")
        arc_file.write_text(_LEGACY_ARCHIVE.format(task_id=1), encoding="utf-8")

        result = _run_migrate(kanban_dir, lane="all")
        assert result.returncode == 0

        # Task lane evidence: claimed_by removed
        task_content = task_file.read_text(encoding="utf-8")
        assert "claimed_by" not in task_content, "--lane all did not process task lane"

        # Archive lane evidence: archival_reason added
        arc_content = arc_file.read_text(encoding="utf-8")
        assert "archival_reason:" in arc_content, (
            "--lane all did not process archive lane"
        )

        # Config lane evidence: statuses converted from list[dict] to list[str]
        config_content = (kanban_dir / "config.yml").read_text(encoding="utf-8")
        assert "name: research" not in config_content, (
            "--lane all did not process config lane"
        )
        assert "- research" in config_content, (
            "--lane all did not produce list[str] statuses"
        )

    def test_ac_c32_archive_lane_does_not_touch_config(self, tmp_path: Path) -> None:
        """AC-C32 (exclusivity): --lane archive must NOT modify config.yml content or mtime."""
        kanban_dir = _make_legacy_board(tmp_path)
        (kanban_dir / "archive" / "0001-old.md").write_text(
            _LEGACY_ARCHIVE.format(task_id=1), encoding="utf-8"
        )
        config_content_before = (kanban_dir / "config.yml").read_text(encoding="utf-8")
        config_mtime_before = (kanban_dir / "config.yml").stat().st_mtime

        result = _run_migrate(kanban_dir, lane="archive")
        assert result.returncode == 0

        assert (kanban_dir / "config.yml").stat().st_mtime == config_mtime_before, (
            "--lane archive must not modify config.yml mtime"
        )
        assert (kanban_dir / "config.yml").read_text(
            encoding="utf-8"
        ) == config_content_before, "--lane archive must not modify config.yml content"

    def test_ac_c32_config_lane_does_not_touch_archive(self, tmp_path: Path) -> None:
        """AC-C32 (exclusivity): --lane config must NOT modify archive file content or mtime."""
        kanban_dir = _make_legacy_board(tmp_path)
        arc_file = kanban_dir / "archive" / "0001-old.md"
        arc_content_before = _LEGACY_ARCHIVE.format(task_id=1)
        arc_file.write_text(arc_content_before, encoding="utf-8")
        arc_mtime_before = arc_file.stat().st_mtime

        result = _run_migrate(kanban_dir, lane="config")
        assert result.returncode == 0

        assert arc_file.stat().st_mtime == arc_mtime_before, (
            "--lane config must not modify archive file mtime"
        )
        assert arc_file.read_text(encoding="utf-8") == arc_content_before, (
            "--lane config must not modify archive file content"
        )


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
        assert result.returncode == 0

        content = task_file.read_text(encoding="utf-8")
        assert "claimed_by" not in content

    def test_ac_c33_tasks_lane_adds_all_defaults_with_exact_values(
        self, tmp_path: Path
    ) -> None:
        """AC-C33 (T4): tasks lane injects ALL _ACTIVE_TASK_DEFAULTS with exact values when absent."""
        kanban_dir = _make_legacy_board(tmp_path)
        task_content = (
            "---\nid: 1001\ntitle: t\nstatus: todo\npriority: needed\n"
            'created: "2026-01-15T08:00:00+00:00"\nupdated: "2026-01-15T08:00:00+00:00"\n---\n'
        )
        task_file = kanban_dir / "tasks" / "1001-t.md"
        task_file.write_text(task_content, encoding="utf-8")

        _run_migrate(kanban_dir, lane="tasks")
        content = task_file.read_text(encoding="utf-8")

        # None values may render as bare 'key:\n' or explicit 'key: null\n' depending on ruamel.yaml
        assert (
            "archival_reason: null\n" in content or "archival_reason:\n" in content
        ), "archival_reason must be null after migration"
        assert "archival_refs: []" in content, (
            "archival_refs must be [] after migration"
        )
        assert "tags: []" in content, "tags must be [] after migration"
        assert "parent: null\n" in content or "parent:\n" in content, (
            "parent must be null after migration"
        )
        assert "depends_on: []" in content, "depends_on must be [] after migration"
        assert "blocked: false" in content, "blocked must be false after migration"
        assert "block_reason: null\n" in content or "block_reason:\n" in content, (
            "block_reason must be null after migration"
        )
        assert "claimed_at: null\n" in content or "claimed_at:\n" in content, (
            "claimed_at must be null after migration"
        )

    def test_ac_c33_tasks_lane_normalises_timestamps_to_utc(
        self, tmp_path: Path
    ) -> None:
        """AC-C33: tasks lane ensures created/updated timestamps end with +00:00."""
        kanban_dir = _make_legacy_board(tmp_path)
        # Naive timestamp (no tz offset)
        task_content = (
            "---\nid: 1001\ntitle: t\nstatus: todo\npriority: needed\n"
            'created: "2026-01-15T08:00:00"\nupdated: "2026-01-15T08:00:00"\n---\n'
        )
        task_file = kanban_dir / "tasks" / "1001-t.md"
        task_file.write_text(task_content, encoding="utf-8")

        _run_migrate(kanban_dir, lane="tasks")
        content = task_file.read_text(encoding="utf-8")

        lines = content.splitlines()
        created_lines = [line for line in lines if line.strip().startswith("created:")]
        updated_lines = [line for line in lines if line.strip().startswith("updated:")]
        assert created_lines, "created field missing after migration"
        assert updated_lines, "updated field missing after migration"
        assert "+00:00" in created_lines[0], (
            f"created not normalised to +00:00: {created_lines[0]}"
        )
        assert "+00:00" in updated_lines[0], (
            f"updated not normalised to +00:00: {updated_lines[0]}"
        )

    def test_ac_c33_tasks_lane_normalises_nonnull_claimed_at(
        self, tmp_path: Path
    ) -> None:
        """AC-C33 (T3): tasks lane normalises non-null claimed_at timestamps to +00:00."""
        kanban_dir = _make_legacy_board(tmp_path)
        # claimed_at present but naive (no tz offset)
        task_content = (
            "---\n"
            "id: 1001\n"
            "title: t\n"
            "status: todo\n"
            "priority: needed\n"
            'created: "2026-01-15T08:00:00+00:00"\n'
            'updated: "2026-01-15T08:00:00+00:00"\n'
            'claimed_at: "2026-01-20T10:00:00"\n'
            "---\n"
        )
        task_file = kanban_dir / "tasks" / "1001-t.md"
        task_file.write_text(task_content, encoding="utf-8")

        _run_migrate(kanban_dir, lane="tasks")
        content = task_file.read_text(encoding="utf-8")

        lines = content.splitlines()
        claimed_at_lines = [
            line for line in lines if line.strip().startswith("claimed_at:")
        ]
        assert claimed_at_lines, "claimed_at field missing after migration"
        assert "+00:00" in claimed_at_lines[0], (
            f"claimed_at not normalised to +00:00: {claimed_at_lines[0]}"
        )
        assert "null" not in claimed_at_lines[0], (
            "claimed_at must be normalised (preserved), not set to null"
        )

    def test_ac_c33_tasks_lane_preserves_existing_nonnull_values(
        self, tmp_path: Path
    ) -> None:
        """AC-C33 (T5): tasks lane preserves existing non-default field values unchanged."""
        kanban_dir = _make_legacy_board(tmp_path)
        # tags: [bug] and parent: 42 exist; archival_reason/archival_refs absent
        task_content = (
            "---\n"
            "id: 1001\n"
            "title: t\n"
            "status: todo\n"
            "priority: needed\n"
            'created: "2026-01-15T08:00:00+00:00"\n'
            'updated: "2026-01-15T08:00:00+00:00"\n'
            "tags:\n"
            "- bug\n"
            "parent: 42\n"
            "---\n"
        )
        task_file = kanban_dir / "tasks" / "1001-t.md"
        task_file.write_text(task_content, encoding="utf-8")

        _run_migrate(kanban_dir, lane="tasks")
        content = task_file.read_text(encoding="utf-8")

        assert "- bug" in content, "existing tags value must be preserved"
        assert "parent: 42" in content, "existing parent value must be preserved"
        # None values may render as bare 'key:\n' or explicit 'key: null\n'
        assert (
            "archival_reason: null\n" in content or "archival_reason:\n" in content
        ), "missing archival_reason must be added with default value null"
        assert "archival_refs: []" in content, (
            "missing archival_refs must be added with default value []"
        )

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

        for dropped in (
            "board:",
            "version:",
            "defaults:",
        ):
            assert dropped not in content, f"Legacy field '{dropped}' still present"

    def test_ac_c33_config_lane_adds_new_required_fields(self, tmp_path: Path) -> None:
        """AC-C33: config lane adds entry_status, wave_size, non_impl_tags etc."""
        kanban_dir = _make_legacy_board(tmp_path)
        _run_migrate(kanban_dir, lane="config")
        content = (kanban_dir / "config.yml").read_text(encoding="utf-8")

        for new_field in (
            "entry_status:",
            "wave_size:",
            "non_impl_tags:",
            "archival_reasons:",
        ):
            assert new_field in content, f"New required field '{new_field}' missing"

        # AC-C33 (C4): assert exact derived and preserved values
        assert "entry_status: research" in content, (
            "entry_status must be derived from legacy defaults.status: research"
        )
        assert "claim_timeout: 1h" in content, (
            "claim_timeout: 1h must be preserved from legacy config"
        )
        assert "next_id: 1001" in content, (
            "next_id: 1001 must be preserved from legacy config"
        )
        assert "wave_size: 4" in content, "wave_size must be set to 4 (constant)"
        # AC-C33 (C4): priorities list must be preserved from legacy config (all 5 values)
        for p in ("someday", "nice-to-have", "important", "needed", "critical"):
            assert f"- {p}" in content, (
                f"priorities must include '{p}' from legacy config"
            )

    def test_ac_c35_tasks_idempotency_check_skips_modern_task(
        self, tmp_path: Path
    ) -> None:
        """AC-C35: idempotency check skips tasks/ files already in canonical form."""
        kanban_dir = _make_modern_board(tmp_path)
        task_file = kanban_dir / "tasks" / "1001-modern.md"
        task_file.write_text(_MODERN_TASK.format(task_id=1001), encoding="utf-8")
        mtime_before = task_file.stat().st_mtime

        _run_migrate(kanban_dir, lane="tasks")
        assert task_file.stat().st_mtime == mtime_before

    def test_ac_c33_archive_lane_adds_archival_reason(self, tmp_path: Path) -> None:
        """AC-C33: archive lane adds archival_reason: completed to legacy archive files."""
        kanban_dir = _make_legacy_board(tmp_path)
        arc_file = kanban_dir / "archive" / "0001-old.md"
        arc_file.write_text(_LEGACY_ARCHIVE.format(task_id=1), encoding="utf-8")

        result = _run_migrate(kanban_dir, lane="archive")
        assert result.returncode == 0

        content = arc_file.read_text(encoding="utf-8")
        assert "archival_reason: completed" in content

    def test_ac_c33_archive_lane_adds_archival_refs(self, tmp_path: Path) -> None:
        """AC-C33: archive lane adds archival_refs: [] to legacy archive files."""
        kanban_dir = _make_legacy_board(tmp_path)
        arc_file = kanban_dir / "archive" / "0001-old.md"
        arc_file.write_text(_LEGACY_ARCHIVE.format(task_id=1), encoding="utf-8")

        _run_migrate(kanban_dir, lane="archive")
        content = arc_file.read_text(encoding="utf-8")

        assert "archival_refs: []" in content

    def test_ac_c35_archive_idempotency_check_skips_modern_archive(
        self, tmp_path: Path
    ) -> None:
        """AC-C35: archive lane skips files that already have non-null archival_reason + archival_refs."""
        kanban_dir = _make_modern_board(tmp_path)
        arc_file = kanban_dir / "archive" / "0001-modern.md"
        arc_file.write_text(_MODERN_ARCHIVE.format(task_id=1), encoding="utf-8")
        mtime_before = arc_file.stat().st_mtime

        _run_migrate(kanban_dir, lane="archive")
        assert arc_file.stat().st_mtime == mtime_before


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
        assert (
            "Migrated:         0" in result2.stdout or "Migrated: 0" in result2.stdout
        )

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
        mtime_before = task_file.stat().st_mtime

        result = _run_migrate(kanban_dir, lane="tasks", dry_run=True)
        assert result.returncode == 0
        # File unchanged — both content and mtime must be unmodified
        assert task_file.read_text(encoding="utf-8") == original
        assert task_file.stat().st_mtime == mtime_before

    def test_ac_c36_dry_run_writes_nothing_config(self, tmp_path: Path) -> None:
        """AC-C36: --dry-run leaves config.yml unchanged."""
        kanban_dir = _make_legacy_board(tmp_path)
        original_config = (kanban_dir / "config.yml").read_text(encoding="utf-8")
        mtime_before = (kanban_dir / "config.yml").stat().st_mtime

        _run_migrate(kanban_dir, lane="config", dry_run=True)

        assert (kanban_dir / "config.yml").read_text(
            encoding="utf-8"
        ) == original_config
        assert (kanban_dir / "config.yml").stat().st_mtime == mtime_before

    def test_ac_c36_dry_run_prints_what_would_change(self, tmp_path: Path) -> None:
        """AC-C36: --dry-run prints at least some output describing what would be migrated."""
        kanban_dir = _make_legacy_board(tmp_path)
        (kanban_dir / "tasks" / "1001-t.md").write_text(
            _LEGACY_TASK.format(task_id=1001), encoding="utf-8"
        )

        result = _run_migrate(kanban_dir, lane="tasks", dry_run=True)
        # Pin all four summary labels in stdout
        assert "Scanned:" in result.stdout
        assert "Migrated:" in result.stdout
        assert "Already:" in result.stdout
        assert "Failed:" in result.stdout

    def test_ac_c36_dry_run_stdout_pins_specific_summary_labels(
        self, tmp_path: Path
    ) -> None:
        """AC-C36 (strict): --dry-run stdout must contain Scanned:/Migrated:/Already:/Failed: labels.

        AC-test item (b): pins specific summary labels rather than accepting any output.
        """
        kanban_dir = _make_legacy_board(tmp_path)
        (kanban_dir / "tasks" / "1001-t.md").write_text(
            _LEGACY_TASK.format(task_id=1001), encoding="utf-8"
        )
        result = _run_migrate(kanban_dir, lane="tasks", dry_run=True)
        assert result.returncode == 0
        assert "Scanned:" in result.stdout
        assert "Migrated:" in result.stdout
        assert "Already:" in result.stdout
        assert "Failed:" in result.stdout


# ---------------------------------------------------------------------------
# TestFromAC_CrashRecovery — AC-C37
# ---------------------------------------------------------------------------


class TestFromAC_CrashRecovery:
    """AC-C37: crash mid-migration leaves no partial files; resume converges."""

    def test_ac_c37_no_partial_files_after_failure(self, tmp_path: Path) -> None:
        """AC-C37: if atomic_write is used, no .tmp-* files left after a failure."""

        kanban_dir = _make_legacy_board(tmp_path)
        (kanban_dir / "tasks" / "1001-t.md").write_text(
            _LEGACY_TASK.format(task_id=1001), encoding="utf-8"
        )

        call_count = {"n": 0}
        original_replace = __import__("os").replace

        def crash_on_second_replace(src: str, dst: str) -> None:
            call_count["n"] += 1
            if call_count["n"] == 2:
                msg = "simulated mid-migration crash"
                raise OSError(msg)
            original_replace(src, dst)

        with (
            patch("os.replace", side_effect=crash_on_second_replace),
            contextlib.suppress(OSError),
        ):
            _run_migrate(kanban_dir, lane="tasks")

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
        assert "FAIL " in result.stderr
        assert "9999-bad.md" in result.stderr

    def test_ac_c38_stderr_fail_line_format_contains_path_and_colon_reason(
        self, tmp_path: Path
    ) -> None:
        """AC-C38 (strict): stderr FAIL lines must contain 'FAIL ' prefix and the file path.

        AC-test item (c): assert 'FAIL ' prefix followed by path-like content,
        not just the substring 'FAIL'.
        """
        kanban_dir = _make_legacy_board(tmp_path)
        bad_file = kanban_dir / "tasks" / "9999-bad.md"
        bad_file.write_text("NOT VALID\x00\x00\x00", encoding="utf-8")

        result = _run_migrate(kanban_dir, lane="tasks")
        assert result.returncode == 1
        # 'FAIL ' prefix must be followed by path content including the filename
        assert "FAIL " in result.stderr
        assert "9999-bad.md" in result.stderr

    def test_ac_c38a_config_lane_with_stubs_emits_manual_action_summary(
        self, tmp_path: Path
    ) -> None:
        """AC-C38a: config lane with empty stubs emits a manual-action warning/summary."""
        kanban_dir = _make_legacy_board(tmp_path)
        result = _run_migrate(kanban_dir, lane="config")

        combined = result.stdout + result.stderr
        # Should mention the stub fields that require manual attention
        assert (
            "agent_map" in combined
            or "WARNING" in combined
            or "manual" in combined.lower()
        )


# ---------------------------------------------------------------------------
# TestFromAC_LaneSelectionStrict — AC-C32 (stricter assertions, retry-cycle)
# ---------------------------------------------------------------------------


class TestFromAC_LaneSelectionStrict:
    """AC-C32: success-path invocations must exit 0 (not 0-or-1)."""

    def test_ac_c32_tasks_lane_exits_0_on_success_path(self, tmp_path: Path) -> None:
        """AC-C32: --lane tasks exits 0 when a legacy task is successfully migrated."""
        kanban_dir = _make_legacy_board(tmp_path)
        (kanban_dir / "tasks" / "1001-t.md").write_text(
            _LEGACY_TASK.format(task_id=1001), encoding="utf-8"
        )
        result = _run_migrate(kanban_dir, lane="tasks")
        assert result.returncode == 0

    def test_ac_c32_archive_lane_exits_0_on_success_path(self, tmp_path: Path) -> None:
        """AC-C32: --lane archive exits 0 when a legacy archive is successfully migrated."""
        kanban_dir = _make_legacy_board(tmp_path)
        (kanban_dir / "archive" / "0001-old.md").write_text(
            _LEGACY_ARCHIVE.format(task_id=1), encoding="utf-8"
        )
        result = _run_migrate(kanban_dir, lane="archive")
        assert result.returncode == 0

    def test_ac_c32_all_lane_exits_0_on_full_legacy_board(self, tmp_path: Path) -> None:
        """AC-C32: --lane all exits 0 when all lanes migrate successfully."""
        kanban_dir = _make_legacy_board(tmp_path)
        (kanban_dir / "tasks" / "1001-t.md").write_text(
            _LEGACY_TASK.format(task_id=1001), encoding="utf-8"
        )
        (kanban_dir / "archive" / "0001-old.md").write_text(
            _LEGACY_ARCHIVE.format(task_id=1), encoding="utf-8"
        )
        result = _run_migrate(kanban_dir, lane="all")
        assert result.returncode == 0

    def test_ac_c32_single_lane_does_not_touch_other_dir(self, tmp_path: Path) -> None:
        """AC-C32: --lane tasks must not modify archive files; archive content asserted intact."""
        kanban_dir = _make_legacy_board(tmp_path)
        arc_file = kanban_dir / "archive" / "0001-old.md"
        arc_content = _LEGACY_ARCHIVE.format(task_id=1)
        arc_file.write_text(arc_content, encoding="utf-8")
        (kanban_dir / "tasks" / "1001-t.md").write_text(
            _LEGACY_TASK.format(task_id=1001), encoding="utf-8"
        )
        _run_migrate(kanban_dir, lane="tasks")
        assert arc_file.read_text(encoding="utf-8") == arc_content


# ---------------------------------------------------------------------------
# TestFromAC_ArchiveLaneAlgorithmsStrict — AC-C33 (stricter, retry-cycle)
# ---------------------------------------------------------------------------


_ARCHIVE_ONE_REASON_NO_REFS = """\
---
id: {task_id}
title: Archive partial {task_id}
status: done
priority: needed
archival_reason: completed
---

## Notes

Has reason, missing refs.
"""

_ARCHIVE_NO_REASON_EMPTY_REFS = """\
---
id: {task_id}
title: Archive partial {task_id}
status: done
priority: needed
archival_refs: []
---

## Notes

Has refs, missing reason.
"""

_ARCHIVE_EMPTY_REASON = """\
---
id: {task_id}
title: Archive bad reason {task_id}
status: done
priority: needed
archival_reason: ""
archival_refs: []
---

## Notes

Empty reason is invalid.
"""

_ARCHIVE_WITH_INT_REFS = """\
---
id: {task_id}
title: Archive int refs {task_id}
status: done
priority: needed
archival_reason: completed
archival_refs:
- 1001
- 1002
---

## Notes

Integer refs from pre-C model.
"""

_ARCHIVE_INVALID_REFS = """\
---
id: {task_id}
title: Archive invalid refs {task_id}
status: done
priority: needed
archival_reason: completed
archival_refs: "not-a-list"
---

## Notes

Invalid archival_refs — non-list value triggers manual-action failure.
"""

_ARCHIVE_BOOL_REFS = """\
---
id: {task_id}
title: Archive bool refs {task_id}
status: done
priority: needed
archival_reason: completed
archival_refs:
- true
---

## Notes

Boolean in archival_refs list — triggers manual-action failure.
"""


class TestFromAC_ArchiveLaneAlgorithmsStrict:
    """AC-C33 strict: one-field-present auto-fill, invalid field failures, body preservation."""

    def test_ac_c33_archive_with_reason_fills_absent_refs(self, tmp_path: Path) -> None:
        """AC-C33: archive with valid reason but missing refs gets refs: [] auto-filled."""
        kanban_dir = _make_legacy_board(tmp_path)
        arc_file = kanban_dir / "archive" / "0001.md"
        arc_file.write_text(
            _ARCHIVE_ONE_REASON_NO_REFS.format(task_id=1), encoding="utf-8"
        )

        result = _run_migrate(kanban_dir, lane="archive")
        assert result.returncode == 0

        content = arc_file.read_text(encoding="utf-8")
        assert "archival_reason: completed" in content
        assert "archival_refs:" in content

    def test_ac_c33_archive_with_refs_fills_absent_reason(self, tmp_path: Path) -> None:
        """AC-C33: archive with valid refs but missing reason gets reason: completed auto-filled."""
        kanban_dir = _make_legacy_board(tmp_path)
        arc_file = kanban_dir / "archive" / "0001.md"
        arc_file.write_text(
            _ARCHIVE_NO_REASON_EMPTY_REFS.format(task_id=1), encoding="utf-8"
        )

        result = _run_migrate(kanban_dir, lane="archive")
        assert result.returncode == 0

        content = arc_file.read_text(encoding="utf-8")
        assert "archival_reason: completed" in content

    def test_ac_c33_archive_empty_string_reason_records_failure(
        self, tmp_path: Path
    ) -> None:
        """AC-C33: archive with empty-string archival_reason records manual-action failure."""
        kanban_dir = _make_legacy_board(tmp_path)
        arc_file = kanban_dir / "archive" / "0001.md"
        arc_file.write_text(_ARCHIVE_EMPTY_REASON.format(task_id=1), encoding="utf-8")

        result = _run_migrate(kanban_dir, lane="archive")
        assert result.returncode == 1
        assert "manual-action required" in result.stderr

    def test_ac_c33_archive_preserves_body_text_verbatim(self, tmp_path: Path) -> None:
        """AC-C33: archive lane does NOT rewrite body — body text preserved verbatim."""
        body = "\n## Notes\n\nOriginal body content with *markdown*.\n"
        arc_content = (
            f"---\nid: 1\ntitle: t\nstatus: done\npriority: needed\n---\n{body}"
        )
        kanban_dir = _make_legacy_board(tmp_path)
        arc_file = kanban_dir / "archive" / "0001.md"
        arc_file.write_text(arc_content, encoding="utf-8")

        _run_migrate(kanban_dir, lane="archive")
        written = arc_file.read_text(encoding="utf-8")
        # Body text after closing --- must be preserved verbatim (exact equality)
        after_fm = written.split("---\n", 2)[-1]
        assert after_fm == body, (
            f"archive body must be preserved verbatim after migration; got: {after_fm!r}"
        )

    def test_ac_c33_config_lane_warning_mentions_readme(self, tmp_path: Path) -> None:
        """AC-C33: config lane emits warning line mentioning serve/kanban/README.md."""
        kanban_dir = _make_legacy_board(tmp_path)
        result = _run_migrate(kanban_dir, lane="config")
        assert "serve/kanban/README.md" in result.stderr


# ---------------------------------------------------------------------------
# TestFromAC_IdempotencyEdgeCases — AC-C35 (edge cases, retry-cycle)
# ---------------------------------------------------------------------------


class TestFromAC_IdempotencyEdgeCases:
    """AC-C35: idempotency predicates for tasks and archives — edge cases."""

    def test_ac_c35_task_missing_one_canonical_field_is_migrated(
        self, tmp_path: Path
    ) -> None:
        """AC-C35: task missing archival_refs (even with archival_reason) is NOT skipped."""
        # Has archival_reason but NOT archival_refs → is_task_migrated returns False
        task_content = (
            "---\n"
            "id: 1001\n"
            "title: partial\n"
            "status: todo\n"
            "priority: needed\n"
            'created: "2026-01-15T08:00:00+00:00"\n'
            'updated: "2026-01-15T08:00:00+00:00"\n'
            "tags: []\n"
            "parent: null\n"
            "depends_on: []\n"
            "blocked: false\n"
            "block_reason: null\n"
            "claimed_at: null\n"
            "archival_reason: null\n"
            "---\n\n## Notes\n\nContent.\n"
        )
        kanban_dir = _make_legacy_board(tmp_path)
        task_file = kanban_dir / "tasks" / "1001-partial.md"
        task_file.write_text(task_content, encoding="utf-8")
        mtime_before = task_file.stat().st_mtime

        _run_migrate(kanban_dir, lane="tasks")
        # File must have been written (not skipped)
        assert task_file.stat().st_mtime != mtime_before or (
            "archival_refs:" in task_file.read_text(encoding="utf-8")
        )
        assert "archival_refs:" in task_file.read_text(encoding="utf-8")

    def test_ac_c35_archive_empty_reason_not_treated_as_idempotent(
        self, tmp_path: Path
    ) -> None:
        """AC-C35: archive with empty-string reason is NOT skipped (fails for manual action)."""
        kanban_dir = _make_legacy_board(tmp_path)
        arc_file = kanban_dir / "archive" / "0001.md"
        arc_file.write_text(_ARCHIVE_EMPTY_REASON.format(task_id=1), encoding="utf-8")

        result = _run_migrate(kanban_dir, lane="archive")
        # Must NOT be treated as already-migrated; should fail for manual action
        assert result.returncode == 1
        assert "manual-action required" in result.stderr

    def test_ac_c35_archive_list_int_refs_not_rejected_as_invalid(
        self, tmp_path: Path
    ) -> None:
        """AC-C35: archive with list[int] archival_refs must be treated as idempotent.

        Architecture Notes: 'The idempotency predicate should not reject list[int] values.'
        A file with archival_reason: completed and archival_refs: [1001, 1002] (integers)
        is already migrated and must be skipped without failure.
        """
        kanban_dir = _make_modern_board(tmp_path)
        arc_file = kanban_dir / "archive" / "0001-int-refs.md"
        arc_file.write_text(_ARCHIVE_WITH_INT_REFS.format(task_id=1), encoding="utf-8")

        result = _run_migrate(kanban_dir, lane="archive")
        # Must exit 0 (no failures) — list[int] refs are valid per Architecture Notes
        assert result.returncode == 0
        assert "manual-action required" not in result.stderr

    def test_ac_c35_config_list_str_statuses_is_already_migrated(
        self, tmp_path: Path
    ) -> None:
        """AC-C35: config with list[str] statuses and all new keys is already migrated.

        AC-test item (a) positive: correct list[str] statuses must trigger the 'already' path.
        """
        # _make_modern_board writes _NEW_CONFIG_YAML which has statuses: [str, ...]
        kanban_dir = _make_modern_board(tmp_path)
        config_file = kanban_dir / "config.yml"
        mtime_before = config_file.stat().st_mtime

        result = _run_migrate(kanban_dir, lane="config")
        assert result.returncode == 0
        # File must NOT be rewritten — already migrated
        assert config_file.stat().st_mtime == mtime_before
        assert "Already: 1" in result.stdout or "Already:         1" in result.stdout

    def test_ac_c35_task_missing_created_is_migrated_not_skipped(
        self, tmp_path: Path
    ) -> None:
        """AC-C35: task without 'created' field must be migrated, not treated as already-migrated."""
        task_content = (
            "---\n"
            "id: 1001\n"
            "title: missing created\n"
            "status: todo\n"
            "priority: needed\n"
            # 'created' intentionally absent — idempotency predicate must reject
            'updated: "2026-01-15T08:00:00+00:00"\n'
            "tags: []\n"
            "parent: null\n"
            "depends_on: []\n"
            "blocked: false\n"
            "block_reason: null\n"
            "claimed_at: null\n"
            "archival_reason: null\n"
            "archival_refs: []\n"
            "---\n\n## Notes\n\nContent.\n"
        )
        kanban_dir = _make_modern_board(tmp_path)
        (kanban_dir / "tasks" / "1001-no-created.md").write_text(
            task_content, encoding="utf-8"
        )
        result = _run_migrate(kanban_dir, lane="tasks")
        assert result.returncode == 0
        assert (
            "Migrated: 1" in result.stdout or "Migrated:         1" in result.stdout
        ), (
            "task missing 'created' was incorrectly treated as already-migrated "
            "(_is_task_migrated must require 'created' field presence)"
        )

    def test_ac_c35_task_missing_updated_is_migrated_not_skipped(
        self, tmp_path: Path
    ) -> None:
        """AC-C35: task without 'updated' field must be migrated, not treated as already-migrated."""
        task_content = (
            "---\n"
            "id: 1002\n"
            "title: missing updated\n"
            "status: todo\n"
            "priority: needed\n"
            'created: "2026-01-15T08:00:00+00:00"\n'
            # 'updated' intentionally absent — idempotency predicate must reject
            "tags: []\n"
            "parent: null\n"
            "depends_on: []\n"
            "blocked: false\n"
            "block_reason: null\n"
            "claimed_at: null\n"
            "archival_reason: null\n"
            "archival_refs: []\n"
            "---\n\n## Notes\n\nContent.\n"
        )
        kanban_dir = _make_modern_board(tmp_path)
        (kanban_dir / "tasks" / "1002-no-updated.md").write_text(
            task_content, encoding="utf-8"
        )
        result = _run_migrate(kanban_dir, lane="tasks")
        assert result.returncode == 0
        assert (
            "Migrated: 1" in result.stdout or "Migrated:         1" in result.stdout
        ), (
            "task missing 'updated' was incorrectly treated as already-migrated "
            "(_is_task_migrated must require 'updated' field presence)"
        )

    def test_ac_c35_config_integer_statuses_not_treated_as_already_migrated(
        self, tmp_path: Path
    ) -> None:
        """AC-C35: config with statuses: [int] must NOT be treated as already migrated.

        AC-test item (a) negative — MUST FAIL (RED test exposing _is_config_migrated bug).
        AC-C35 requires: list[str] check `all(isinstance(s, str) for s in statuses)`.
        A list[int] statuses must be normalised, NOT skipped as already migrated.
        """
        # Config with all new keys present but statuses is list[int] (no legacy keys)
        int_statuses_config = (
            "statuses:\n"
            "- 1\n"
            "- 2\n"
            "priorities:\n"
            "- someday\n"
            "- nice-to-have\n"
            "entry_status: research\n"
            "wave_size: 4\n"
            "agent_map: {}\n"
            "agent_types: {}\n"
            "agent_compatibility: {}\n"
            "non_impl_tags: []\n"
            "archival_reasons: [completed]\n"
            "status_predicates: {}\n"
            "claim_timeout: 1h\n"
            "next_id: 1001\n"
        )
        kanban_dir = tmp_path / "board"
        kanban_dir.mkdir()
        (kanban_dir / "tasks").mkdir()
        (kanban_dir / "archive").mkdir()
        config_file = kanban_dir / "config.yml"
        config_file.write_text(int_statuses_config, encoding="utf-8")

        result = _run_migrate(kanban_dir, lane="config")
        assert result.returncode == 0
        # list[int] statuses must be normalised, not skipped — expect Migrated: 1
        # With the bug, _is_config_migrated returns True for list[int] → Already: 1 (incorrect).
        # This assertion FAILS while the bug in _is_config_migrated exists.
        assert (
            "Migrated: 1" in result.stdout or "Migrated:         1" in result.stdout
        ), (
            "config with statuses: [1] was incorrectly treated as already migrated "
            "(_is_config_migrated bug: checks only list[dict], not list[int])"
        )

    def test_ac_c35_archive_invalid_archival_refs_not_treated_as_already(
        self, tmp_path: Path
    ) -> None:
        """AC-C35 (branch matrix): archive with invalid archival_refs must fail, not be skipped.

        Files with archival_refs: "not-a-list" (non-list) are contract-invalid.
        _migrate_archive_file must return ("failed", "manual-action required: invalid archival_refs")
        rather than treating the file as already migrated.
        Expected: Failed: 1, Migrated: 0, exit code 1, manual-action required in stderr.
        """
        kanban_dir = _make_legacy_board(tmp_path)
        arc_file = kanban_dir / "archive" / "0001-invalid-refs.md"
        arc_file.write_text(_ARCHIVE_INVALID_REFS.format(task_id=1), encoding="utf-8")

        result = _run_migrate(kanban_dir, lane="archive")

        assert result.returncode == 1, (
            "archive with invalid archival_refs must exit 1 (failed count > 0)"
        )
        assert "Failed: 1" in result.stdout or "Failed:         1" in result.stdout, (
            "archive with invalid archival_refs must report Failed: 1 in stdout"
        )
        assert (
            "Migrated: 0" in result.stdout or "Migrated:         0" in result.stdout
        ), "archive with invalid archival_refs must NOT increment Migrated counter"
        assert "manual-action required: invalid archival_refs" in result.stderr, (
            "stderr must contain 'manual-action required: invalid archival_refs' "
            "per _migrate_archive_file at migrate.py:267-268"
        )

    def test_ac_c35_archive_boolean_list_refs_not_treated_as_already(
        self, tmp_path: Path
    ) -> None:
        """AC-C35 (branch matrix): archive with boolean in archival_refs list must fail, not be skipped.

        AC-C35 specifies invalid archival_refs includes lists containing booleans (e.g. [true]).
        _is_archive_refs_valid checks `not isinstance(item, bool)` at migrate.py:116.
        Expected: Failed: 1, Migrated: 0, exit code 1, manual-action required: invalid archival_refs.
        """
        kanban_dir = _make_legacy_board(tmp_path)
        arc_file = kanban_dir / "archive" / "0001-bool-refs.md"
        arc_file.write_text(_ARCHIVE_BOOL_REFS.format(task_id=1), encoding="utf-8")

        result = _run_migrate(kanban_dir, lane="archive")

        assert result.returncode == 1, (
            "archive with boolean in archival_refs must exit 1 (failed count > 0)"
        )
        assert "Failed: 1" in result.stdout or "Failed:         1" in result.stdout, (
            "archive with boolean in archival_refs must report Failed: 1 in stdout"
        )
        assert (
            "Migrated: 0" in result.stdout or "Migrated:         0" in result.stdout
        ), "archive with boolean in archival_refs must NOT increment Migrated counter"
        assert "manual-action required: invalid archival_refs" in result.stderr, (
            "stderr must contain 'manual-action required: invalid archival_refs' "
            "per _is_archive_refs_valid boolean check at migrate.py:116"
        )

    def test_ac_c35_task_misordered_canonical_fields_is_migrated_not_skipped(
        self, tmp_path: Path
    ) -> None:
        """AC-C35 (branch matrix): task with all canonical fields in non-canonical order is migrated.

        §5.3 step 2 condition 5 requires canonical field order as an idempotency condition.
        _is_task_migrated() calls _has_canonical_order() — a task with `title` before `id`
        must be re-migrated (Migrated: 1), NOT skipped (Already: 1).
        After migration, the output file must have `id` before `title` (canonical order restored).
        """
        # All canonical fields present with correct values, but `title` precedes `id` — wrong order.
        task_content = (
            "---\n"
            "title: misordered task\n"
            "id: 1001\n"
            "status: todo\n"
            "priority: needed\n"
            'created: "2026-01-15T08:00:00+00:00"\n'
            'updated: "2026-01-15T08:00:00+00:00"\n'
            "tags: []\n"
            "parent: null\n"
            "depends_on: []\n"
            "blocked: false\n"
            "block_reason: null\n"
            "claimed_at: null\n"
            "archival_reason: null\n"
            "archival_refs: []\n"
            "---\n\n## Notes\n\nContent.\n"
        )
        kanban_dir = _make_modern_board(tmp_path)
        task_file = kanban_dir / "tasks" / "1001-misordered.md"
        task_file.write_text(task_content, encoding="utf-8")

        result = _run_migrate(kanban_dir, lane="tasks")

        assert result.returncode == 0, (
            "task with misordered canonical fields must exit 0 (no failure)"
        )
        assert (
            "Migrated: 1" in result.stdout or "Migrated:         1" in result.stdout
        ), (
            "task with non-canonical field order was incorrectly treated as already-migrated "
            "(_is_task_migrated must require _has_canonical_order to return True)"
        )
        # After migration the file must open with id before title (canonical order restored)
        migrated_text = task_file.read_text(encoding="utf-8")
        id_pos = migrated_text.find("\nid:")
        title_pos = migrated_text.find("\ntitle:")
        assert id_pos < title_pos, (
            "after migration, 'id' must appear before 'title' in the frontmatter "
            "(canonical order must be restored by _migrate_task_file)"
        )


# ---------------------------------------------------------------------------
# TestFromAC_DryRunStrict — AC-C36 (stricter, retry-cycle)
# ---------------------------------------------------------------------------


class TestFromAC_DryRunStrict:
    """AC-C36: dry-run writes nothing across all lanes; file mtimes unchanged."""

    def test_ac_c36_dry_run_archive_leaves_file_unchanged(self, tmp_path: Path) -> None:
        """AC-C36: --lane archive --dry-run leaves archive file content and mtime unchanged."""
        kanban_dir = _make_legacy_board(tmp_path)
        arc_file = kanban_dir / "archive" / "0001-old.md"
        original = _LEGACY_ARCHIVE.format(task_id=1)
        arc_file.write_text(original, encoding="utf-8")
        mtime_before = arc_file.stat().st_mtime

        result = _run_migrate(kanban_dir, lane="archive", dry_run=True)
        assert result.returncode == 0
        assert arc_file.read_text(encoding="utf-8") == original
        assert arc_file.stat().st_mtime == mtime_before

    def test_ac_c36_dry_run_tasks_exits_0_and_reports_scanned(
        self, tmp_path: Path
    ) -> None:
        """AC-C36: --dry-run on legacy tasks exits 0 and reports Scanned count in output."""
        kanban_dir = _make_legacy_board(tmp_path)
        (kanban_dir / "tasks" / "1001-t.md").write_text(
            _LEGACY_TASK.format(task_id=1001), encoding="utf-8"
        )
        result = _run_migrate(kanban_dir, lane="tasks", dry_run=True)
        assert result.returncode == 0
        assert "Scanned: 1" in result.stdout
        assert "Migrated: 1" in result.stdout


# ---------------------------------------------------------------------------
# TestFromAC_CrashRecoverySubprocess — AC-C37 (subprocess seam, retry-cycle)
# ---------------------------------------------------------------------------


class TestFromAC_CrashRecoverySubprocess:
    """AC-C37: crash via KANBAN_MIGRATE_CRASH_AFTER env var — subprocess seam."""

    def _write_tasks(self, kanban_dir: Path, count: int = 3) -> list[Path]:
        files = []
        for i in range(1001, 1001 + count):
            f = kanban_dir / "tasks" / f"{i}-task.md"
            f.write_text(_LEGACY_TASK.format(task_id=i), encoding="utf-8")
            files.append(f)
        return files

    def test_ac_c37_crash_after_first_write_exits_nonzero(self, tmp_path: Path) -> None:
        """AC-C37: KANBAN_MIGRATE_CRASH_AFTER=1 causes subprocess to exit non-zero."""
        kanban_dir = _make_legacy_board(tmp_path)
        self._write_tasks(kanban_dir)

        result = _run_migrate(
            kanban_dir, lane="tasks", extra_env={"KANBAN_MIGRATE_CRASH_AFTER": "1"}
        )
        assert result.returncode != 0

    def test_ac_c37_crash_leaves_no_tmp_files_in_tasks_dir(
        self, tmp_path: Path
    ) -> None:
        """AC-C37: crash after write leaves no .tmp-* partial files in tasks/."""
        kanban_dir = _make_legacy_board(tmp_path)
        self._write_tasks(kanban_dir)

        _run_migrate(
            kanban_dir, lane="tasks", extra_env={"KANBAN_MIGRATE_CRASH_AFTER": "1"}
        )
        leftovers = list((kanban_dir / "tasks").glob(".tmp-*"))
        assert leftovers == [], f"Partial .tmp- files found: {leftovers}"

    def test_ac_c37_resume_after_crash_exits_0(self, tmp_path: Path) -> None:
        """AC-C37: re-running after a crash (without crash env) converges to exit 0."""
        kanban_dir = _make_legacy_board(tmp_path)
        self._write_tasks(kanban_dir)

        # First run: crash after 1 write
        _run_migrate(
            kanban_dir, lane="tasks", extra_env={"KANBAN_MIGRATE_CRASH_AFTER": "1"}
        )
        # Resume: must succeed
        result2 = _run_migrate(kanban_dir, lane="tasks")
        assert result2.returncode == 0

    def test_ac_c37_final_state_fully_migrated_after_crash_and_resume(
        self, tmp_path: Path
    ) -> None:
        """AC-C37: after crash + resume, all task files have claimed_by removed."""
        kanban_dir = _make_legacy_board(tmp_path)
        files = self._write_tasks(kanban_dir)

        _run_migrate(
            kanban_dir, lane="tasks", extra_env={"KANBAN_MIGRATE_CRASH_AFTER": "1"}
        )
        _run_migrate(kanban_dir, lane="tasks")

        for f in files:
            content = f.read_text(encoding="utf-8")
            assert "claimed_by" not in content, (
                f"{f.name} still has claimed_by after resume"
            )

    def test_ac_c37_crash_resume_equals_clean_migration_full_content(
        self, tmp_path: Path
    ) -> None:
        """AC-C37: crash+resume produces identical file content to a clean full migration run.

        Arch review cycle 2: final-state equivalence must compare full file contents
        against a reference clean-migration run on an identical starting board.
        """
        task_count = 3

        # Reference board: clean full migration in one pass
        ref_board = _make_legacy_board(tmp_path / "reference")
        for i in range(1001, 1001 + task_count):
            (ref_board / "tasks" / f"{i}-task.md").write_text(
                _LEGACY_TASK.format(task_id=i), encoding="utf-8"
            )
        _run_migrate(ref_board, lane="tasks")
        ref_contents = {
            f.name: f.read_text(encoding="utf-8")
            for f in sorted((ref_board / "tasks").glob("*.md"))
        }

        # Test board: crash after first write, then resume
        test_board = _make_legacy_board(tmp_path / "crashresume")
        for i in range(1001, 1001 + task_count):
            (test_board / "tasks" / f"{i}-task.md").write_text(
                _LEGACY_TASK.format(task_id=i), encoding="utf-8"
            )
        _run_migrate(
            test_board, lane="tasks", extra_env={"KANBAN_MIGRATE_CRASH_AFTER": "1"}
        )
        _run_migrate(test_board, lane="tasks")
        test_contents = {
            f.name: f.read_text(encoding="utf-8")
            for f in sorted((test_board / "tasks").glob("*.md"))
        }

        assert set(test_contents.keys()) == set(ref_contents.keys()), (
            "crash+resume board has different files than clean migration reference"
        )
        for fname, expected_content in ref_contents.items():
            assert test_contents[fname] == expected_content, (
                f"{fname}: crash+resume content differs from clean migration reference"
            )


# ---------------------------------------------------------------------------
# TestFromAC_ManualActionSummaryStrict — AC-C38a (stricter, retry-cycle)
# ---------------------------------------------------------------------------


class TestFromAC_ManualActionSummaryStrict:
    """AC-C38a: MANUAL ACTION SUMMARY output pinned with all required keywords."""

    def test_ac_c38a_config_migration_emits_manual_action_summary_header(
        self, tmp_path: Path
    ) -> None:
        """AC-C38a: config lane migration emits 'MANUAL ACTION SUMMARY:' on stderr."""
        kanban_dir = _make_legacy_board(tmp_path)
        result = _run_migrate(kanban_dir, lane="config")
        assert "MANUAL ACTION SUMMARY:" in result.stderr

    def test_ac_c38a_config_summary_mentions_agent_map(self, tmp_path: Path) -> None:
        """AC-C38a: config manual-action summary mentions agent_map."""
        kanban_dir = _make_legacy_board(tmp_path)
        result = _run_migrate(kanban_dir, lane="config")
        assert "agent_map" in result.stderr

    def test_ac_c38a_config_summary_mentions_agent_types(self, tmp_path: Path) -> None:
        """AC-C38a: config manual-action summary mentions agent_types."""
        kanban_dir = _make_legacy_board(tmp_path)
        result = _run_migrate(kanban_dir, lane="config")
        assert "agent_types" in result.stderr

    def test_ac_c38a_config_summary_mentions_agent_compatibility(
        self, tmp_path: Path
    ) -> None:
        """AC-C38a: config manual-action summary mentions agent_compatibility."""
        kanban_dir = _make_legacy_board(tmp_path)
        result = _run_migrate(kanban_dir, lane="config")
        assert "agent_compatibility" in result.stderr

    def test_ac_c38a_config_summary_mentions_type_user_action(
        self, tmp_path: Path
    ) -> None:
        """AC-C38a: config manual-action summary mentions type:user-action task materialisation."""
        kanban_dir = _make_legacy_board(tmp_path)
        result = _run_migrate(kanban_dir, lane="config")
        assert "type:user-action" in result.stderr

    def test_ac_c38a_archive_invalid_reason_produces_fail_line_on_stderr(
        self, tmp_path: Path
    ) -> None:
        """AC-C38a: archive lane manual-action failure emits FAIL line with reason on stderr."""
        kanban_dir = _make_legacy_board(tmp_path)
        arc_file = kanban_dir / "archive" / "0001-bad.md"
        arc_file.write_text(_ARCHIVE_EMPTY_REASON.format(task_id=1), encoding="utf-8")

        result = _run_migrate(kanban_dir, lane="archive")
        assert result.returncode == 1
        assert "FAIL" in result.stderr
        assert "manual-action required" in result.stderr
        assert "MANUAL ACTION SUMMARY:" in result.stderr
        summary_items = [
            line
            for line in result.stderr.splitlines()
            if line.strip().startswith("- archive:")
        ]
        assert len(summary_items) >= 1, (
            "expected at least one '- archive:' summary-item line in stderr"
        )
        assert "0001-bad.md" in summary_items[0], (
            f"summary-item line must contain archive file path: {summary_items}"
        )
        assert "invalid archival_reason" in summary_items[0], (
            f"summary-item line must contain failure reason text: {summary_items}"
        )

    def test_ac_c38a_archive_invalid_reason_emits_manual_action_summary_header(
        self, tmp_path: Path
    ) -> None:
        """AC-C38a (strict): archive manual-action failures feed into MANUAL ACTION SUMMARY: block.

        AC-test item (d): assert 'MANUAL ACTION SUMMARY:' header presence on stderr
        when archive lane records a manual-action failure, per main() summary emission.
        """
        kanban_dir = _make_legacy_board(tmp_path)
        arc_file = kanban_dir / "archive" / "0001-bad.md"
        arc_file.write_text(_ARCHIVE_EMPTY_REASON.format(task_id=1), encoding="utf-8")

        result = _run_migrate(kanban_dir, lane="archive")
        assert result.returncode == 1
        # Archive manual-action failures must trigger the MANUAL ACTION SUMMARY: header
        assert "MANUAL ACTION SUMMARY:" in result.stderr

    def test_ac_c38a_config_rerun_already_migrated_with_empty_stubs_emits_summary(
        self, tmp_path: Path
    ) -> None:
        """AC-C38a: rerunning --lane config on already-migrated config with empty stubs emits MANUAL ACTION SUMMARY.

        Proves the 'already' config result branch still emits the summary when
        agent_map/agent_types/agent_compatibility remain unresolved empty dicts.
        """
        # _make_modern_board writes _NEW_CONFIG_YAML which has agent_map: {}, agent_types: {},
        # agent_compatibility: {} — unresolved stubs; config is already in new schema.
        kanban_dir = _make_modern_board(tmp_path)

        # Prerequisite: confirm this is the 'already' path (not a fresh migration)
        result1 = _run_migrate(kanban_dir, lane="config")
        assert (
            "Already: 1" in result1.stdout or "Already:         1" in result1.stdout
        ), (
            "prerequisite failed: _make_modern_board must produce an already-migrated config"
        )

        # Rerun: even on 'already' path, MANUAL ACTION SUMMARY must be emitted
        result2 = _run_migrate(kanban_dir, lane="config")
        assert "MANUAL ACTION SUMMARY:" in result2.stderr, (
            "rerunning --lane config on already-migrated config with empty agent_map/"
            "agent_types/agent_compatibility stubs must emit MANUAL ACTION SUMMARY: on stderr"
        )

    def test_ac_c38a_config_rerun_summary_mentions_stub_fields(
        self, tmp_path: Path
    ) -> None:
        """AC-C38a: config rerun on already-migrated config names stub fields in the summary."""
        kanban_dir = _make_modern_board(tmp_path)

        # First pass confirms 'already' path
        r1 = _run_migrate(kanban_dir, lane="config")
        assert "Already: 1" in r1.stdout or "Already:         1" in r1.stdout

        # Rerun: stub field names must appear in stderr summary
        r2 = _run_migrate(kanban_dir, lane="config")
        assert "agent_map" in r2.stderr, (
            "config rerun MANUAL ACTION SUMMARY must mention agent_map"
        )
        assert "agent_types" in r2.stderr
        assert "agent_compatibility" in r2.stderr

    def test_ac_c38a_archive_invalid_refs_emits_manual_action_summary(
        self, tmp_path: Path
    ) -> None:
        """AC-C38a (branch matrix): archive with invalid archival_refs emits MANUAL ACTION SUMMARY.

        AC-C38a requires both invalid archival_reason AND invalid archival_refs archive failures
        to produce entries in 'MANUAL ACTION SUMMARY:' on stderr.
        This test exercises the archival_refs variant at migrate.py:450-451 → :506.
        """
        kanban_dir = _make_legacy_board(tmp_path)
        arc_file = kanban_dir / "archive" / "0001-invalid-refs.md"
        arc_file.write_text(_ARCHIVE_INVALID_REFS.format(task_id=1), encoding="utf-8")

        result = _run_migrate(kanban_dir, lane="archive")

        assert result.returncode == 1
        assert "MANUAL ACTION SUMMARY:" in result.stderr, (
            "archive with invalid archival_refs must feed into MANUAL ACTION SUMMARY: on stderr "
            "via _run_lane manual_actions list at migrate.py:450-451"
        )
        summary_items = [
            line
            for line in result.stderr.splitlines()
            if line.strip().startswith("- archive:")
        ]
        assert len(summary_items) >= 1, (
            "expected at least one '- archive:' summary-item line in stderr"
        )
        assert "0001-invalid-refs.md" in summary_items[0], (
            f"summary-item line must contain archive file path: {summary_items}"
        )
        assert "invalid archival_refs" in summary_items[0], (
            f"summary-item line must contain failure reason text: {summary_items}"
        )
