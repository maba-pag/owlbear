"""Failing tests for renaming v1-archive → archive in kanban engine (#744, RED phase).

AC coverage:
  AC1 - _ARCHIVE_DIR_NAME constant equals "archive" (not "v1-archive")
  AC2 - Engine docstrings use "archive/" not "v1-archive/"
  AC3/AC4 - end_work(success) on last status writes task file to archive/ directory
  AC7 - list_tasks(archived=True) reads from archive/ directory
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from owlbear_kanban.engine import (
    KanbanEngine,
)
from owlbear_kanban.models import BoardConfig

# ---------------------------------------------------------------------------
# Shared config content — mirrors real .owlbear/kanban/config.yml
# ---------------------------------------------------------------------------

_BASE_CONFIG_YAML = """\
version: 10
board:
    name: OwlBear
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
    class: standard
claim_timeout: 1h
next_id: 100
"""

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def kanban_dir(tmp_path: Path) -> Path:
    """Minimal kanban directory: config.yml + tasks/ only (no archive dir)."""
    (tmp_path / "config.yml").write_text(_BASE_CONFIG_YAML, encoding="utf-8")
    (tmp_path / "tasks").mkdir()
    return tmp_path


@pytest.fixture()
def engine(kanban_dir: Path) -> KanbanEngine:
    """KanbanEngine with a pinned agent_name for deterministic tests."""
    return KanbanEngine(kanban_dir, agent_name="test-agent")


@pytest.fixture()
def kanban_dir_with_archive(tmp_path: Path) -> Path:
    """Kanban directory with archive/ subdirectory pre-created."""
    kdir = tmp_path / "kanban"
    kdir.mkdir()
    (kdir / "config.yml").write_text(_BASE_CONFIG_YAML, encoding="utf-8")
    (kdir / "tasks").mkdir()
    (kdir / "archive").mkdir()
    return kdir


def _write_task_file(directory: Path, task_id: int, title: str) -> Path:
    """Write a minimal task file to *directory* and return the path."""
    slug = title.lower().replace(" ", "-")[:30]
    path = directory / f"{task_id}-{slug}.md"
    path.write_text(
        "---\n"
        f"id: {task_id}\n"
        f"title: {title!r}\n"
        "status: 'done'\n"
        "priority: 'important'\n"
        "created: '2026-01-01T10:00:00+00:00'\n"
        "updated: '2026-01-02T10:00:00+00:00'\n"
        "tags: []\n"
        "parent: null\n"
        "depends_on: []\n"
        "blocked: false\n"
        "block_reason: null\n"
        "claimed_by: null\n"
        "claimed_at: null\n"
        "---\n",
        encoding="utf-8",
    )
    return path


# ===========================================================================
# TestFromAC_ArchiveDirConstant — AC1
# ===========================================================================


class TestFromAC_ArchiveDirConstant:
    """Tests for AC1: BoardConfig.archive_dir defaults to 'archive'."""

    def test_archive_dir_default_is_archive(self) -> None:
        """BoardConfig.archive_dir default must equal 'archive', not 'v1-archive'."""
        assert BoardConfig.model_fields["archive_dir"].default == "archive"

    def test_archive_dir_default_not_v1_archive(self) -> None:
        """BoardConfig.archive_dir default must not contain the legacy 'v1-archive' value."""
        default = BoardConfig.model_fields["archive_dir"].default
        assert default != "v1-archive"
        assert "v1" not in default


# ===========================================================================
# TestFromAC_EngineDocstrings — AC2
# ===========================================================================


class TestFromAC_EngineDocstrings:
    """Tests for AC2: engine.py docstrings reference 'archive/' not 'v1-archive/'."""

    def test_move_task_docstring_has_no_v1_archive_reference(self) -> None:
        """move_task docstring must not reference the legacy 'v1-archive' path."""
        doc = inspect.getdoc(KanbanEngine.move_task) or ""
        assert "v1-archive" not in doc

    def test_list_tasks_docstring_has_no_v1_archive_reference(self) -> None:
        """list_tasks docstring must not reference the legacy 'v1-archive' path."""
        doc = inspect.getdoc(KanbanEngine.list_tasks) or ""
        assert "v1-archive" not in doc

    def test_module_docstring_has_no_v1_archive_reference(self) -> None:
        """engine.py module-level docstring must not reference 'v1-archive'."""
        import owlbear_kanban.engine as engine_module

        doc = engine_module.__doc__ or ""
        assert "v1-archive" not in doc


# ===========================================================================
# TestFromAC_ArchiveDirectoryBehavior — AC3 / AC4 (filesystem side)
# ===========================================================================


class TestFromAC_ArchiveDirectoryBehavior:
    """Tests for AC3/AC4: archived tasks are written to and read from archive/."""

    def test_end_work_last_status_writes_to_archive_dir(self, engine: KanbanEngine, kanban_dir: Path) -> None:
        """end_work(success) on 'done' (last status) writes task file to archive/ directory."""
        task = engine.create_task("To be archived", status="done")
        engine.start_work(str(task.id))
        engine.end_work(str(task.id), note="Archiving now", outcome="success")

        archive_dir = kanban_dir / "archive"
        archive_files = list(archive_dir.glob(f"{task.id}-*.md"))
        assert len(archive_files) == 1

    def test_end_work_last_status_no_file_in_v1_archive(self, engine: KanbanEngine, kanban_dir: Path) -> None:
        """end_work(success) on 'done' must NOT write to the legacy v1-archive/ directory."""
        task = engine.create_task("Should not go to v1-archive", status="done")
        engine.start_work(str(task.id))
        engine.end_work(str(task.id), note="Archiving", outcome="success")

        legacy_archive_dir = kanban_dir / "v1-archive"
        if legacy_archive_dir.exists():
            legacy_files = list(legacy_archive_dir.glob(f"{task.id}-*.md"))
            assert legacy_files == []

    def test_move_task_archived_writes_to_archive_dir(self, engine: KanbanEngine, kanban_dir: Path) -> None:
        """move_task('archived') places the task file in archive/ directory."""
        task = engine.create_task("Move to archive")
        engine.move_task(str(task.id), "archived")

        archive_dir = kanban_dir / "archive"
        archive_files = list(archive_dir.glob(f"{task.id}-*.md"))
        assert len(archive_files) == 1


# ===========================================================================
# TestFromAC_ListTasksArchiveDir — AC7
# ===========================================================================


class TestFromAC_ListTasksArchiveDir:
    """Tests for AC7: list_tasks(archived=True) reads from archive/ directory."""

    def test_list_tasks_archived_reads_from_archive_dir(self, kanban_dir_with_archive: Path) -> None:
        """list_tasks(archived=True) returns tasks placed in archive/ directory."""
        archive_dir = kanban_dir_with_archive / "archive"
        _write_task_file(archive_dir, 201, "Archived task alpha")
        _write_task_file(archive_dir, 202, "Archived task beta")

        engine = KanbanEngine(kanban_dir_with_archive, agent_name="test-agent")
        result = engine.list_tasks(archived=True)

        assert len(result) == 2
        ids = {t.id for t in result}
        assert ids == {201, 202}

    def test_list_tasks_archived_does_not_read_from_v1_archive(self, kanban_dir_with_archive: Path) -> None:
        """list_tasks(archived=True) reads from archive/, not v1-archive/."""
        # Place tasks only in the legacy v1-archive/; engine must NOT find them
        legacy_dir = kanban_dir_with_archive / "v1-archive"
        legacy_dir.mkdir()
        _write_task_file(legacy_dir, 301, "Stale v1-archive task")

        engine = KanbanEngine(kanban_dir_with_archive, agent_name="test-agent")
        result = engine.list_tasks(archived=True)

        ids = {t.id for t in result}
        assert 301 not in ids

    def test_list_tasks_archived_nonexistent_archive_dir_returns_empty(self, kanban_dir_with_archive: Path) -> None:
        """list_tasks(archived=True) returns [] when only v1-archive/ exists (not archive/)."""
        # Create v1-archive/ with tasks in it — the renamed engine must NOT read this.
        legacy_dir = kanban_dir_with_archive / "v1-archive"
        legacy_dir.mkdir()
        _write_task_file(legacy_dir, 501, "Legacy-only archived task")

        engine = KanbanEngine(kanban_dir_with_archive, agent_name="test-agent")
        result = engine.list_tasks(archived=True)

        # After rename: archive/ is empty → [], not drawn from legacy v1-archive/
        assert result == []
