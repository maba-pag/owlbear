"""Durable tests for support module migration and compat cleanup.

Promoted from archived task #1175 during test curation.

Historical task context from the original task-scoped suite:

Tests for Phase 3 support module migration and compat layer removal (#1175).

Validates:
- corruption.py uses sub-model access paths (not forwarding properties) for all sites
- storage.py non-save_config sites use sub-model access paths
- BoardConfig no longer exposes forwarding properties (compat layer removed)
- Live .owlbear/kanban/config.yml is in grouped schema format
- terminal_status is present in the live config's pipeline section

AC coverage:
  AC1 → TestFromAC_CorruptionSubModelPaths
  AC2 → TestFromAC_StorageNonSaveConfigPaths
  AC3 → TestFromAC_CompatLayerRemoval
  AC4 → TestFromAC_LiveConfigGroupedFormat
  AC5 → TestFromAC_LiveConfigTerminalStatus

"""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from owlbear_kanban.config_loader import load_config
# Promoted from archived task #1175.

# ---------------------------------------------------------------------------
# Minimal config double — no forwarding properties, sub-model structure only.
# Any code calling config.tasks_dir (forwarding prop) will get AttributeError.
# ---------------------------------------------------------------------------


@dataclass
class _PathsConfig:
    tasks_dir: str = "tasks"
    archive_dir: str = "archive"


@dataclass
class _PipelineConfig:
    entry_status: str = "research"
    terminal_status: str = "done"
    wave_size: int = 4
    claim_timeout: str = "1h"
    default_priority: str = "needed"
    statuses: list = field(default_factory=list)
    priorities: list = field(default_factory=list)


@dataclass
class _AgentsConfig:
    agent_map: dict = field(default_factory=dict)
    agent_types: dict = field(default_factory=dict)
    agent_compatibility: dict = field(default_factory=dict)


@dataclass
class _PolicyConfig:
    non_impl_tags: list = field(default_factory=list)
    archival_reasons: frozenset = field(
        default_factory=lambda: frozenset({"completed", "deprecated", "dropped", "duplicate", "wontfix"})
    )
    status_predicates: dict = field(default_factory=dict)


@dataclass
class _MinimalConfig:
    """Config double WITHOUT forwarding properties.

    Callers that invoke config.tasks_dir (instead of config.paths.tasks_dir)
    will raise AttributeError — proving the migration is incomplete.
    """

    statuses: list = field(default_factory=lambda: ["research", "todo", "done"])
    priorities: list = field(default_factory=lambda: ["needed", "critical"])
    next_id: int = 1
    activity_log: bool = False
    paths: _PathsConfig = field(default_factory=_PathsConfig)
    pipeline: _PipelineConfig = field(default_factory=_PipelineConfig)
    agents: _AgentsConfig = field(default_factory=_AgentsConfig)
    policy: _PolicyConfig = field(default_factory=_PolicyConfig)
    # Explicitly NO forwarding properties: no tasks_dir, archive_dir,
    # entry_status, terminal_status, wave_size, etc. at the top level.


# ---------------------------------------------------------------------------
# Board / task helpers
# ---------------------------------------------------------------------------

_GROUPED_CONFIG = """\
next_id: 1
"""

_TASK_FM = """\
---
id: {id}
title: Task {id}
status: {status}
priority: needed
created: "2026-01-01T10:00:00+00:00"
updated: "2026-01-01T10:00:00+00:00"
tags: []
parent: null
depends_on: []
blocked: false
block_reason: null
claimed_at: null
archival_reason: null
archival_refs: []
---
Body.
"""


def _make_board(base_dir: Path) -> Path:
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_GROUPED_CONFIG, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


def _write_task(kanban_dir: Path, task_id: int = 1, status: str = "todo", subdir: str = "tasks") -> Path:
    path = kanban_dir / subdir / f"{task_id}-task.md"
    path.write_text(_TASK_FM.format(id=task_id, status=status), encoding="utf-8")
    return path


# Live kanban directory — the actual board config being validated
_LIVE_KANBAN_DIR = Path(__file__).parent.parent / ".owlbear" / "kanban"


# ---------------------------------------------------------------------------
# AC1: corruption.py uses sub-model access paths for all 8 access sites
# ---------------------------------------------------------------------------


class TestFromAC_CorruptionSubModelPaths:
    """AC1: Tests validate corruption.py uses sub-model access paths.

    corruption.py currently uses config.tasks_dir and config.archive_dir
    (forwarding properties).  After migration these become config.paths.tasks_dir
    and config.paths.archive_dir.  All tests below FAIL until migration is done.
    """

    def test_corruption_source_no_config_tasks_dir(self) -> None:
        """corruption.py must not reference config.tasks_dir (forwarding property)."""
        import owlbear_kanban.corruption as _mod

        source = inspect.getsource(_mod)
        assert "config.tasks_dir" not in source, (
            "corruption.py still uses config.tasks_dir (forwarding property); migrate to config.paths.tasks_dir"
        )

    def test_corruption_source_uses_config_paths_tasks_dir(self) -> None:
        """corruption.py must use config.paths.tasks_dir (sub-model path)."""
        import owlbear_kanban.corruption as _mod

        source = inspect.getsource(_mod)
        assert "config.paths.tasks_dir" in source, (
            "corruption.py does not contain config.paths.tasks_dir; migration incomplete"
        )

    def test_corruption_source_no_config_archive_dir(self) -> None:
        """corruption.py must not reference config.archive_dir (forwarding property)."""
        import owlbear_kanban.corruption as _mod

        source = inspect.getsource(_mod)
        assert "config.archive_dir" not in source, (
            "corruption.py still uses config.archive_dir (forwarding property); migrate to config.paths.archive_dir"
        )

    def test_corruption_source_uses_config_paths_archive_dir(self) -> None:
        """corruption.py must use config.paths.archive_dir (sub-model path)."""
        import owlbear_kanban.corruption as _mod

        source = inspect.getsource(_mod)
        assert "config.paths.archive_dir" in source, (
            "corruption.py does not contain config.paths.archive_dir; migration incomplete"
        )

    def test_scan_and_fix_works_without_forwarding_props(self, tmp_path: Path) -> None:
        """scan_and_fix() must work when config has no forwarding properties.

        Currently FAILS with AttributeError on config.tasks_dir.
        After migration (config.paths.tasks_dir), returns an empty list.
        """
        from owlbear_kanban.corruption import scan_and_fix

        kanban_dir = tmp_path / "board"
        (kanban_dir / "tasks").mkdir(parents=True)
        (kanban_dir / "archive").mkdir(parents=True)
        config = _MinimalConfig()

        result = scan_and_fix(kanban_dir, config)

        assert isinstance(result, list)

    def test_detect_corruption_works_without_forwarding_props(self, tmp_path: Path) -> None:
        """detect_corruption() must work when config has no forwarding properties.

        Internally calls _is_archive_path(path, config) which uses
        config.archive_dir.  Currently FAILS with AttributeError.
        After migration (config.paths.archive_dir), returns None for a clean task.
        """
        from owlbear_kanban.corruption import detect_corruption

        kanban_dir = tmp_path / "board"
        (kanban_dir / "tasks").mkdir(parents=True)
        path = kanban_dir / "tasks" / "1-task.md"
        path.write_text(
            "---\nid: 1\ntitle: Task\nstatus: todo\npriority: needed\n"
            'created: "2026-01-01T10:00:00+00:00"\nupdated: "2026-01-01T10:00:00+00:00"\n---\n',
            encoding="utf-8",
        )
        config = _MinimalConfig()

        result = detect_corruption(path, config)

        assert result is None

    def test_is_archive_path_uses_paths_sub_model(self, tmp_path: Path) -> None:
        """_is_archive_path() (called via scan_and_fix) must use config.paths.archive_dir.

        Creates a task with a claimed_by field to force _is_archive_path check.
        FAILS with AttributeError until corruption.py is migrated.
        """
        from owlbear_kanban.corruption import scan_and_fix

        kanban_dir = tmp_path / "board"
        (kanban_dir / "tasks").mkdir(parents=True)
        (kanban_dir / "archive").mkdir(parents=True)
        path = kanban_dir / "tasks" / "1-task.md"
        path.write_text(
            "---\nid: 1\ntitle: Task\nstatus: todo\npriority: needed\n"
            'created: "2026-01-01T10:00:00+00:00"\nupdated: "2026-01-01T10:00:00+00:00"\n'
            "claimed_by: some-agent\n---\n",
            encoding="utf-8",
        )
        config = _MinimalConfig()

        # FAILS with AttributeError on config.archive_dir until migrated.
        # After migration, scan_and_fix returns a RepairOutcome for the corrupted file.
        result = scan_and_fix(kanban_dir, config)

        assert any(o.code == "ERR_CORRUPT_MISSING_FIELD" for o in result)

    def test_scan_and_fix_reads_sentinel_tasks_dir(self, tmp_path: Path) -> None:
        """scan_and_fix() must find files in config.paths.tasks_dir (not hardcoded 'tasks').

        Only 'sentinel_tasks/' is created — 'tasks/' does not exist.
        A corrupted task file is placed in 'sentinel_tasks/'.
        If scan_and_fix uses config.paths.tasks_dir, it finds the file and returns
        a non-empty result.  If it hardcodes 'tasks', it returns [] (dir not found).
        """
        from owlbear_kanban.corruption import scan_and_fix

        kanban_dir = tmp_path / "board"
        (kanban_dir / "sentinel_tasks").mkdir(parents=True)
        (kanban_dir / "sentinel_archive").mkdir(parents=True)
        # claimed_by present in tasks/ → corrupt (not archive)
        path = kanban_dir / "sentinel_tasks" / "1-task.md"
        path.write_text(
            "---\nid: 1\ntitle: Task\nstatus: todo\npriority: needed\n"
            'created: "2026-01-01T10:00:00+00:00"\nupdated: "2026-01-01T10:00:00+00:00"\n'
            "claimed_by: some-agent\n---\n",
            encoding="utf-8",
        )
        config = _MinimalConfig(paths=_PathsConfig(tasks_dir="sentinel_tasks", archive_dir="sentinel_archive"))

        result = scan_and_fix(kanban_dir, config)

        assert len(result) >= 1, (
            "scan_and_fix returned no results for corrupted file in sentinel_tasks/; "
            "does not use config.paths.tasks_dir (sentinel value — hardcoded 'tasks' cannot pass)"
        )

    def test_scan_and_fix_reads_sentinel_archive_dir(self, tmp_path: Path) -> None:
        """scan_and_fix() must find files in config.paths.archive_dir (not hardcoded 'archive').

        Only 'sentinel_archive/' is created — 'archive/' does not exist.
        A corrupt file is placed in 'sentinel_archive/'.
        If scan_and_fix uses config.paths.archive_dir, it finds it and reports corruption.
        If it hardcodes 'archive', it finds nothing and returns [].
        """
        from owlbear_kanban.corruption import scan_and_fix

        kanban_dir = tmp_path / "board"
        (kanban_dir / "sentinel_tasks").mkdir(parents=True)
        (kanban_dir / "sentinel_archive").mkdir(parents=True)
        # File with missing required fields in archive dir
        path = kanban_dir / "sentinel_archive" / "2-task.md"
        path.write_text(
            "---\nid: 2\ntitle: Task\nstatus: todo\n---\n",  # missing priority, created, updated
            encoding="utf-8",
        )
        config = _MinimalConfig(paths=_PathsConfig(tasks_dir="sentinel_tasks", archive_dir="sentinel_archive"))

        result = scan_and_fix(kanban_dir, config)

        assert len(result) >= 1, (
            "scan_and_fix returned no results for corrupted file in sentinel_archive/; "
            "does not use config.paths.archive_dir (sentinel value — hardcoded 'archive' cannot pass)"
        )

    def test_is_archive_path_uses_sentinel_archive_dir(self, tmp_path: Path) -> None:
        """_is_archive_path() must use config.paths.archive_dir (not hardcoded 'archive').

        A task with claimed_by in the archive is NOT corrupt (archive files are exempt).
        Test uses 'sentinel_archive/' as the archive directory.
        If _is_archive_path uses config.paths.archive_dir = 'sentinel_archive',
        it correctly identifies the file as archived → no corruption detected.
        If it hardcodes 'archive', it returns False for 'sentinel_archive/' and
        wrongly reports claimed_by corruption.
        """
        from owlbear_kanban.corruption import detect_corruption

        kanban_dir = tmp_path / "board"
        (kanban_dir / "sentinel_archive").mkdir(parents=True)
        path = kanban_dir / "sentinel_archive" / "1-task.md"
        path.write_text(
            "---\nid: 1\ntitle: Task\nstatus: done\npriority: needed\n"
            'created: "2026-01-01T10:00:00+00:00"\nupdated: "2026-01-01T10:00:00+00:00"\n'
            "claimed_by: some-agent\n---\n",
            encoding="utf-8",
        )
        config = _MinimalConfig(paths=_PathsConfig(tasks_dir="sentinel_tasks", archive_dir="sentinel_archive"))

        # With sentinel archive dir config, _is_archive_path returns True → no corruption.
        # With hardcoded 'archive', _is_archive_path returns False → false corruption reported.
        result = detect_corruption(path, config)

        assert result is None, (
            f"detect_corruption returned {result!r} for archive file with claimed_by; "
            "_is_archive_path does not use config.paths.archive_dir (sentinel value)"
        )


# ---------------------------------------------------------------------------
# AC2: storage.py non-save_config sites use sub-model access paths
# ---------------------------------------------------------------------------


class TestFromAC_StorageNonSaveConfigPaths:
    """AC2: Tests validate storage.py non-save_config sites use sub-model paths.

    storage.py functions write_task, write_task_if_unchanged, list_task_files,
    list_archive_files, and move_to_archive all use config.tasks_dir or
    config.archive_dir (forwarding properties).  After migration these must
    use config.paths.tasks_dir and config.paths.archive_dir.
    All tests below FAIL until migration is done.
    """

    def test_write_task_source_no_config_tasks_dir(self) -> None:
        """write_task() must not reference config.tasks_dir forwarding property."""
        import owlbear_kanban.storage as _mod

        source = inspect.getsource(_mod.write_task)
        assert "config.tasks_dir" not in source, (
            "write_task still uses config.tasks_dir; migrate to config.paths.tasks_dir"
        )

    def test_write_task_if_unchanged_source_no_config_tasks_dir(self) -> None:
        """write_task_if_unchanged() must not reference config.tasks_dir."""
        import owlbear_kanban.storage as _mod

        source = inspect.getsource(_mod.write_task_if_unchanged)
        assert "config.tasks_dir" not in source, (
            "write_task_if_unchanged uses config.tasks_dir; migrate to config.paths.tasks_dir"
        )

    def test_write_task_if_unchanged_source_no_config_archive_dir(self) -> None:
        """write_task_if_unchanged() must not reference config.archive_dir."""
        import owlbear_kanban.storage as _mod

        source = inspect.getsource(_mod.write_task_if_unchanged)
        assert "config.archive_dir" not in source, (
            "write_task_if_unchanged uses config.archive_dir; migrate to config.paths.archive_dir"
        )

    def test_list_task_files_source_no_config_tasks_dir(self) -> None:
        """list_task_files() must not reference config.tasks_dir forwarding property."""
        import owlbear_kanban.storage as _mod

        source = inspect.getsource(_mod.list_task_files)
        assert "config.tasks_dir" not in source, (
            "list_task_files uses config.tasks_dir; migrate to config.paths.tasks_dir"
        )

    def test_list_archive_files_source_no_config_archive_dir(self) -> None:
        """list_archive_files() must not reference config.archive_dir forwarding property."""
        import owlbear_kanban.storage as _mod

        source = inspect.getsource(_mod.list_archive_files)
        assert "config.archive_dir" not in source, (
            "list_archive_files uses config.archive_dir; migrate to config.paths.archive_dir"
        )

    def test_move_to_archive_source_no_config_tasks_dir(self) -> None:
        """move_to_archive() must not reference config.tasks_dir forwarding property."""
        import owlbear_kanban.storage as _mod

        source = inspect.getsource(_mod.move_to_archive)
        assert "config.tasks_dir" not in source, (
            "move_to_archive uses config.tasks_dir; migrate to config.paths.tasks_dir"
        )

    def test_move_to_archive_source_no_config_archive_dir(self) -> None:
        """move_to_archive() must not reference config.archive_dir forwarding property."""
        import owlbear_kanban.storage as _mod

        source = inspect.getsource(_mod.move_to_archive)
        assert "config.archive_dir" not in source, (
            "move_to_archive uses config.archive_dir; migrate to config.paths.archive_dir"
        )

    def test_list_task_files_with_minimal_config(self, tmp_path: Path) -> None:
        """list_task_files() must work with a config that has no forwarding properties.

        Currently FAILS with AttributeError on config.tasks_dir.
        After migration (config.paths.tasks_dir), returns an empty list.
        """
        import owlbear_kanban.storage as _storage

        kanban_dir = tmp_path / "board"
        (kanban_dir / "tasks").mkdir(parents=True)
        config = _MinimalConfig()

        with patch("owlbear_kanban.config_loader.load_config", return_value=config):
            result = _storage.list_task_files(kanban_dir)

        assert result == []

    def test_list_archive_files_with_minimal_config(self, tmp_path: Path) -> None:
        """list_archive_files() must work with a config that has no forwarding properties.

        Currently FAILS with AttributeError on config.archive_dir.
        After migration (config.paths.archive_dir), returns an empty list.
        """
        import owlbear_kanban.storage as _storage

        kanban_dir = tmp_path / "board"
        (kanban_dir / "archive").mkdir(parents=True)
        config = _MinimalConfig()

        with patch("owlbear_kanban.config_loader.load_config", return_value=config):
            result = _storage.list_archive_files(kanban_dir)

        assert result == []

    def test_move_to_archive_with_minimal_config(self, tmp_path: Path) -> None:
        """move_to_archive() must work with a config that has no forwarding properties.

        Currently FAILS with AttributeError on config.tasks_dir.
        After migration (config.paths.tasks_dir), moves the task file to archive/.
        """
        import owlbear_kanban.storage as _storage

        kanban_dir = tmp_path / "board"
        (kanban_dir / "tasks").mkdir(parents=True)
        (kanban_dir / "archive").mkdir(parents=True)
        task_path = kanban_dir / "tasks" / "1-task.md"
        task_path.write_text(
            "---\nid: 1\ntitle: T\nstatus: todo\npriority: needed\n"
            "created: '2026-01-01T10:00:00+00:00'\nupdated: '2026-01-01T10:00:00+00:00'\n---\n",
            encoding="utf-8",
        )
        config = _MinimalConfig()

        with patch("owlbear_kanban.config_loader.load_config", return_value=config):
            result = _storage.move_to_archive(1, kanban_dir)

        assert result.parent.name == "archive"

    def test_write_task_writes_to_sentinel_tasks_dir(self, tmp_path: Path) -> None:
        """write_task() must write to config.paths.tasks_dir (not hardcoded 'tasks').

        Only 'sentinel_tasks/' is created — 'tasks/' does not exist.
        If write_task uses config.paths.tasks_dir, it writes there and returns
        a path under 'sentinel_tasks/'.
        If it hardcodes 'tasks', the dir does not exist and write fails or
        the returned path would not be under 'sentinel_tasks/'.
        """
        import owlbear_kanban.storage as _storage
        from owlbear_kanban.models import Task

        kanban_dir = tmp_path / "board"
        (kanban_dir / "sentinel_tasks").mkdir(parents=True)
        config = _MinimalConfig(paths=_PathsConfig(tasks_dir="sentinel_tasks", archive_dir="sentinel_archive"))
        task = Task(
            id=1,
            title="Sentinel Task",
            status="todo",
            priority="needed",
            created="2026-01-01T10:00:00+00:00",
            updated="2026-01-01T10:00:00+00:00",
        )

        with patch("owlbear_kanban.config_loader.load_config", return_value=config):
            result = _storage.write_task(task, kanban_dir)

        assert result.parent.name == "sentinel_tasks", (
            f"write_task wrote to {result.parent.name!r}, expected 'sentinel_tasks'; "
            "does not use config.paths.tasks_dir (sentinel value — hardcoded 'tasks' cannot pass)"
        )

    def test_write_task_if_unchanged_reads_sentinel_tasks_dir(self, tmp_path: Path) -> None:
        """write_task_if_unchanged() must look in config.paths.tasks_dir (not hardcoded 'tasks').

        Task file is in 'sentinel_tasks/' — 'tasks/' does not exist.
        If write_task_if_unchanged uses config.paths.tasks_dir, it finds the file.
        If it hardcodes 'tasks', it raises FileNotFoundError.
        """
        import owlbear_kanban.storage as _storage
        from owlbear_kanban.storage import read_task

        kanban_dir = tmp_path / "board"
        (kanban_dir / "sentinel_tasks").mkdir(parents=True)
        (kanban_dir / "sentinel_archive").mkdir(parents=True)
        task_path = kanban_dir / "sentinel_tasks" / "1-task.md"
        task_path.write_text(
            "---\nid: 1\ntitle: Task\nstatus: todo\npriority: needed\n"
            'created: "2026-01-01T10:00:00+00:00"\nupdated: "2026-01-01T10:00:00+00:00"\n'
            "tags: []\nparent: null\ndepends_on: []\nblocked: false\nblock_reason: null\n"
            "claimed_at: null\n---\nBody.\n",
            encoding="utf-8",
        )
        task = read_task(task_path)
        expected_updated = task.updated
        config = _MinimalConfig(paths=_PathsConfig(tasks_dir="sentinel_tasks", archive_dir="sentinel_archive"))

        with patch("owlbear_kanban.config_loader.load_config", return_value=config):
            result = _storage.write_task_if_unchanged(task, expected_updated, kanban_dir)

        assert result.parent.name == "sentinel_tasks", (
            f"write_task_if_unchanged returned path under {result.parent.name!r}; "
            "expected 'sentinel_tasks' — does not use config.paths.tasks_dir (sentinel value)"
        )

    def test_list_task_files_reads_sentinel_tasks_dir(self, tmp_path: Path) -> None:
        """list_task_files() must list from config.paths.tasks_dir (not hardcoded 'tasks').

        A task file is placed in 'sentinel_tasks/' — 'tasks/' does not exist.
        If list_task_files uses config.paths.tasks_dir, it finds the file.
        If it hardcodes 'tasks', it returns [] (dir does not exist → no files).
        """
        import owlbear_kanban.storage as _storage

        kanban_dir = tmp_path / "board"
        (kanban_dir / "sentinel_tasks").mkdir(parents=True)
        task_path = kanban_dir / "sentinel_tasks" / "1-task.md"
        task_path.write_text("---\nid: 1\n---\n", encoding="utf-8")
        config = _MinimalConfig(paths=_PathsConfig(tasks_dir="sentinel_tasks", archive_dir="sentinel_archive"))

        with patch("owlbear_kanban.config_loader.load_config", return_value=config):
            result = _storage.list_task_files(kanban_dir)

        assert result == [task_path], (
            f"list_task_files returned {result!r}, expected [{task_path!r}]; "
            "does not use config.paths.tasks_dir (sentinel value — hardcoded 'tasks' cannot pass)"
        )

    def test_list_archive_files_reads_sentinel_archive_dir(self, tmp_path: Path) -> None:
        """list_archive_files() must list from config.paths.archive_dir (not hardcoded 'archive').

        A file is placed in 'sentinel_archive/' — 'archive/' does not exist.
        If list_archive_files uses config.paths.archive_dir, it finds the file.
        If it hardcodes 'archive', it returns [] (dir does not exist → no files).
        """
        import owlbear_kanban.storage as _storage

        kanban_dir = tmp_path / "board"
        (kanban_dir / "sentinel_archive").mkdir(parents=True)
        archive_path = kanban_dir / "sentinel_archive" / "1-archived.md"
        archive_path.write_text("---\nid: 1\n---\n", encoding="utf-8")
        config = _MinimalConfig(paths=_PathsConfig(tasks_dir="sentinel_tasks", archive_dir="sentinel_archive"))

        with patch("owlbear_kanban.config_loader.load_config", return_value=config):
            result = _storage.list_archive_files(kanban_dir)

        assert result == [archive_path], (
            f"list_archive_files returned {result!r}, expected [{archive_path!r}]; "
            "does not use config.paths.archive_dir (sentinel value — hardcoded 'archive' cannot pass)"
        )

    def test_move_to_archive_uses_sentinel_dirs(self, tmp_path: Path) -> None:
        """move_to_archive() must read from config.paths.tasks_dir and write to config.paths.archive_dir.

        Task is in 'sentinel_tasks/' — 'tasks/' does not exist.
        Target is 'sentinel_archive/' — 'archive/' does not exist.
        If move_to_archive uses hardcoded dirs, it raises FileNotFoundError (no task file found).
        """
        import owlbear_kanban.storage as _storage

        kanban_dir = tmp_path / "board"
        (kanban_dir / "sentinel_tasks").mkdir(parents=True)
        (kanban_dir / "sentinel_archive").mkdir(parents=True)
        task_path = kanban_dir / "sentinel_tasks" / "1-task.md"
        task_path.write_text(
            "---\nid: 1\ntitle: T\nstatus: todo\npriority: needed\n"
            "created: '2026-01-01T10:00:00+00:00'\nupdated: '2026-01-01T10:00:00+00:00'\n---\n",
            encoding="utf-8",
        )
        config = _MinimalConfig(paths=_PathsConfig(tasks_dir="sentinel_tasks", archive_dir="sentinel_archive"))

        with patch("owlbear_kanban.config_loader.load_config", return_value=config):
            result = _storage.move_to_archive(1, kanban_dir)

        assert result.parent.name == "sentinel_archive", (
            f"move_to_archive placed file in {result.parent.name!r}, expected 'sentinel_archive'; "
            "does not use config.paths.archive_dir (sentinel value)"
        )
        assert not task_path.exists(), "task file still present in sentinel_tasks/ after move"


# ---------------------------------------------------------------------------
# AC3: BoardConfig no longer exposes forwarding properties (compat layer removed)
# ---------------------------------------------------------------------------


class TestFromAC_CompatLayerRemoval:
    """AC3: Tests verify BoardConfig no longer exposes forwarding properties.

    BoardConfig currently has 13 @property descriptors that forward to sub-models
    (tasks_dir → paths.tasks_dir, entry_status → pipeline.entry_status, etc.).
    After compat layer removal these properties must not exist.
    All tests below FAIL until the forwarding properties are deleted.
    """

    def test_no_tasks_dir_forwarding_property(self) -> None:
        """BoardConfig must not have a tasks_dir @property (compat layer removed)."""
        from owlbear_kanban.models import BoardConfig

        assert not isinstance(BoardConfig.__dict__.get("tasks_dir"), property), (
            "BoardConfig.tasks_dir forwarding property still present; compat not removed"
        )

    def test_no_archive_dir_forwarding_property(self) -> None:
        """BoardConfig must not have an archive_dir @property (compat layer removed)."""
        from owlbear_kanban.models import BoardConfig

        assert not isinstance(BoardConfig.__dict__.get("archive_dir"), property), (
            "BoardConfig.archive_dir forwarding property still present; compat not removed"
        )

    def test_no_entry_status_forwarding_property(self) -> None:
        """BoardConfig must not have an entry_status @property (compat layer removed)."""
        from owlbear_kanban.models import BoardConfig

        assert not isinstance(BoardConfig.__dict__.get("entry_status"), property), (
            "BoardConfig.entry_status forwarding property still present; compat not removed"
        )

    def test_no_terminal_status_forwarding_property(self) -> None:
        """BoardConfig must not have a terminal_status @property (compat layer removed)."""
        from owlbear_kanban.models import BoardConfig

        assert not isinstance(BoardConfig.__dict__.get("terminal_status"), property), (
            "BoardConfig.terminal_status forwarding property still present; compat not removed"
        )

    def test_no_wave_size_forwarding_property(self) -> None:
        """BoardConfig must not have a wave_size @property (compat layer removed)."""
        from owlbear_kanban.models import BoardConfig

        assert not isinstance(BoardConfig.__dict__.get("wave_size"), property), (
            "BoardConfig.wave_size forwarding property still present; compat not removed"
        )

    def test_no_claim_timeout_forwarding_property(self) -> None:
        """BoardConfig must not have a claim_timeout @property (compat layer removed)."""
        from owlbear_kanban.models import BoardConfig

        assert not isinstance(BoardConfig.__dict__.get("claim_timeout"), property), (
            "BoardConfig.claim_timeout forwarding property still present; compat not removed"
        )

    def test_no_default_priority_forwarding_property(self) -> None:
        """BoardConfig must not have a default_priority @property (compat layer removed)."""
        from owlbear_kanban.models import BoardConfig

        assert not isinstance(BoardConfig.__dict__.get("default_priority"), property), (
            "BoardConfig.default_priority forwarding property still present; compat not removed"
        )

    def test_no_agent_map_forwarding_property(self) -> None:
        """BoardConfig must not have an agent_map @property (compat layer removed)."""
        from owlbear_kanban.models import BoardConfig

        assert not isinstance(BoardConfig.__dict__.get("agent_map"), property), (
            "BoardConfig.agent_map forwarding property still present; compat not removed"
        )

    def test_no_agent_types_forwarding_property(self) -> None:
        """BoardConfig must not have an agent_types @property (compat layer removed)."""
        from owlbear_kanban.models import BoardConfig

        assert not isinstance(BoardConfig.__dict__.get("agent_types"), property), (
            "BoardConfig.agent_types forwarding property still present; compat not removed"
        )

    def test_no_agent_compatibility_forwarding_property(self) -> None:
        """BoardConfig must not have an agent_compatibility @property (compat layer removed)."""
        from owlbear_kanban.models import BoardConfig

        assert not isinstance(BoardConfig.__dict__.get("agent_compatibility"), property), (
            "BoardConfig.agent_compatibility forwarding property still present; compat not removed"
        )

    def test_no_non_impl_tags_forwarding_property(self) -> None:
        """BoardConfig must not have a non_impl_tags @property (compat layer removed)."""
        from owlbear_kanban.models import BoardConfig

        assert not isinstance(BoardConfig.__dict__.get("non_impl_tags"), property), (
            "BoardConfig.non_impl_tags forwarding property still present; compat not removed"
        )

    def test_no_archival_reasons_forwarding_property(self) -> None:
        """BoardConfig must not have an archival_reasons @property (compat layer removed)."""
        from owlbear_kanban.models import BoardConfig

        assert not isinstance(BoardConfig.__dict__.get("archival_reasons"), property), (
            "BoardConfig.archival_reasons forwarding property still present; compat not removed"
        )

    def test_no_status_predicates_forwarding_property(self) -> None:
        """BoardConfig must not have a status_predicates @property (compat layer removed)."""
        from owlbear_kanban.models import BoardConfig

        assert not isinstance(BoardConfig.__dict__.get("status_predicates"), property), (
            "BoardConfig.status_predicates forwarding property still present; compat not removed"
        )


# ---------------------------------------------------------------------------
# AC4: Tests verify live config.yml loads correctly in grouped format
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not (_LIVE_KANBAN_DIR / "config.yml").exists(),
    reason="Live kanban config.yml not found",
)
class TestFromAC_LiveConfigGroupedFormat:
    """AC4: Tests verify live .owlbear/kanban/config.yml is in grouped schema format.

    The live config is currently in legacy/flat format.
    All tests below FAIL until it is migrated to grouped schema (schema: grouped).
    """

    def test_live_config_has_schema_grouped_marker(self) -> None:
        """Raw config.yml must contain 'schema: grouped' at the top level."""
        content = (_LIVE_KANBAN_DIR / "config.yml").read_text(encoding="utf-8")
        assert "schema: grouped" in content, (
            "Live config.yml does not contain 'schema: grouped'; flat-to-grouped migration not yet done"
        )

    def test_live_config_has_paths_section(self) -> None:
        """Raw config.yml must have a 'paths:' subsection (not flat tasks_dir/archive_dir)."""
        content = (_LIVE_KANBAN_DIR / "config.yml").read_text(encoding="utf-8")
        assert "paths:" in content, "Live config.yml missing 'paths:' section; grouped migration incomplete"

    def test_live_config_has_pipeline_section(self) -> None:
        """Raw config.yml must have a 'pipeline:' subsection."""
        content = (_LIVE_KANBAN_DIR / "config.yml").read_text(encoding="utf-8")
        assert "pipeline:" in content, "Live config.yml missing 'pipeline:' section; grouped migration incomplete"

    def test_live_config_has_agents_section(self) -> None:
        """Raw config.yml must have an 'agents:' subsection (not flat agent_map)."""
        content = (_LIVE_KANBAN_DIR / "config.yml").read_text(encoding="utf-8")
        assert "agents:" in content, "Live config.yml missing 'agents:' section; grouped migration incomplete"

    def test_live_config_has_policy_section(self) -> None:
        """Raw config.yml must have a 'policy:' subsection (not flat non_impl_tags)."""
        content = (_LIVE_KANBAN_DIR / "config.yml").read_text(encoding="utf-8")
        assert "policy:" in content, "Live config.yml missing 'policy:' section; grouped migration incomplete"

    def test_live_config_paths_section_is_dict(self) -> None:
        """Raw config.yml 'paths:' value must be a YAML mapping, not a string."""
        with (_LIVE_KANBAN_DIR / "config.yml").open(encoding="utf-8") as fh:
            raw = yaml.safe_load(fh)
        paths = raw.get("paths")
        assert isinstance(paths, dict), (
            f"config.yml 'paths' is {type(paths).__name__!r}, expected dict; migration to grouped format not done"
        )

    def test_live_config_loads_via_canonical_loader_with_grouped_submodels(
        self,
    ) -> None:
        """load_config() on the live config.yml must prove grouped extraction via value-equality.

        Exercises the canonical loader path (config_loader.load_config) and proves
        that config.pipeline.statuses was extracted from the root statuses list —
        not just type-checked.  PipelineConfig.statuses defaults to [], so a
        non-empty result that equals the root list proves the normalizer ran.
        """
        config = load_config(_LIVE_KANBAN_DIR)
        # Value-equality assertion: pipeline.statuses must equal the root statuses list.
        # PipelineConfig default is [] — a non-empty match proves normalizer extraction.
        assert config.pipeline.statuses == config.statuses, (
            f"config.pipeline.statuses {config.pipeline.statuses!r} != "
            f"config.statuses {config.statuses!r}; normalizer extraction failed"
        )
        assert len(config.pipeline.statuses) == 7, (
            f"Expected 7 statuses (live config), got {len(config.pipeline.statuses)}; "
            "PipelineConfig default is [] so any non-zero count would pass type check"
        )


# ---------------------------------------------------------------------------
# AC5: Tests verify terminal_status is present in the live config
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not (_LIVE_KANBAN_DIR / "config.yml").exists(),
    reason="Live kanban config.yml not found",
)
class TestFromAC_LiveConfigTerminalStatus:
    """AC5: Tests verify terminal_status is present in the live config.yml.

    In the current flat/legacy config, terminal_status is absent (the model
    derives it from the last status via the normaliser).  After migration it
    must appear explicitly under the pipeline: section.
    All tests below FAIL until the live config is migrated.
    """

    def test_live_config_raw_contains_terminal_status(self) -> None:
        """Raw config.yml must contain a 'terminal_status:' key."""
        content = (_LIVE_KANBAN_DIR / "config.yml").read_text(encoding="utf-8")
        assert "terminal_status:" in content, (
            "Live config.yml does not contain 'terminal_status:'; "
            "flat config omits it (defaults applied by normaliser — not explicit)"
        )

    def test_live_config_pipeline_section_has_terminal_status(self) -> None:
        """Raw config.yml pipeline: section must have a terminal_status key."""
        with (_LIVE_KANBAN_DIR / "config.yml").open(encoding="utf-8") as fh:
            raw = yaml.safe_load(fh)
        pipeline = raw.get("pipeline")
        assert isinstance(pipeline, dict), (
            f"config.yml 'pipeline' is {type(pipeline).__name__!r}, not a dict; config not in grouped format"
        )
        assert "terminal_status" in pipeline, f"pipeline section has no terminal_status key; keys: {list(pipeline)!r}"

    def test_live_config_terminal_status_equals_last_status(self) -> None:
        """pipeline.terminal_status in raw YAML must equal the last entry in statuses."""
        with (_LIVE_KANBAN_DIR / "config.yml").open(encoding="utf-8") as fh:
            raw = yaml.safe_load(fh)
        pipeline = raw.get("pipeline")
        assert isinstance(pipeline, dict), "pipeline section must be a dict"
        terminal = pipeline.get("terminal_status")
        statuses = raw.get("statuses", [])
        assert statuses, "statuses list must not be empty"
        assert terminal == statuses[-1], f"pipeline.terminal_status={terminal!r} != statuses[-1]={statuses[-1]!r}"
