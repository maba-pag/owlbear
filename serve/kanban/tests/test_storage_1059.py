"""Tests for C-14: storage.py public surface — task_io.py removal contract.

Module: serve/kanban/tests/test_storage_1059.py
Target: owlbear_kanban (package — structural import contract)

AC coverage:
  AC-task_io-removed: task_io.py is deleted; importing it raises ModuleNotFoundError.
  AC-engine-redirected: engine.py no longer imports from task_io; uses storage instead.
  AC-dispatch-redirected: dispatch.py no longer imports from task_io; uses storage instead.
  AC-storage-clean: storage.py itself does not import from task_io.
  AC-corruption-redirected: corruption.py no longer imports from task_io.

All tests FAIL in RED phase — task_io.py still exists and all four consumer
modules still import from it.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Helper — canonical path to the kanban source package
# ---------------------------------------------------------------------------

_KANBAN_SRC = Path(__file__).parent.parent / "src" / "owlbear_kanban"


def _read_source(filename: str) -> str:
    """Return source text of *filename* from the owlbear_kanban package."""
    return (_KANBAN_SRC / filename).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# AC-task_io-removed — task_io.py deleted from the package
# ---------------------------------------------------------------------------


class TestFromAC_TaskIoRemoved:
    """task_io.py must be deleted; the module must not be importable."""

    def test_task_io_py_does_not_exist_on_disk(self) -> None:
        """task_io.py file must not exist in the owlbear_kanban source directory."""
        task_io_path = _KANBAN_SRC / "task_io.py"
        assert not task_io_path.exists(), (
            f"task_io.py still present at {task_io_path}; "
            "it must be deleted per AC: task_io.py removed"
        )

    def test_importing_task_io_raises_module_not_found(self) -> None:
        """Importing owlbear_kanban.task_io must raise ModuleNotFoundError."""
        # Evict any cached module so the import is fresh
        sys.modules.pop("owlbear_kanban.task_io", None)
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module("owlbear_kanban.task_io")

    def test_no_package_source_file_references_task_io(self) -> None:
        """No .py file in the owlbear_kanban package may reference task_io after removal."""
        offenders: list[str] = []
        for py_file in sorted(_KANBAN_SRC.glob("*.py")):
            if py_file.name == "task_io.py":
                continue  # the file itself is the thing to delete
            if "task_io" in py_file.read_text(encoding="utf-8"):
                offenders.append(py_file.name)
        assert offenders == [], (
            f"These files still reference task_io and must be redirected to storage: {offenders}"
        )


# ---------------------------------------------------------------------------
# AC-storage-clean — storage.py must not import from task_io
# ---------------------------------------------------------------------------


class TestFromAC_StorageClean:
    """storage.py must not reference task_io in its source (all logic inlined)."""

    def test_storage_py_has_no_task_io_import(self) -> None:
        """storage.py source must not contain 'task_io'."""
        source = _read_source("storage.py")
        assert "task_io" not in source, (
            "storage.py still imports from task_io; "
            "it must be self-contained per AC: all imports redirected to storage"
        )


# ---------------------------------------------------------------------------
# AC-engine-redirected — engine.py redirected to storage
# ---------------------------------------------------------------------------


class TestFromAC_EngineRedirected:
    """engine.py must import from owlbear_kanban.storage, not from task_io."""

    def test_engine_py_has_no_task_io_import(self) -> None:
        """engine.py source must not contain 'task_io'."""
        source = _read_source("engine.py")
        assert "task_io" not in source, (
            "engine.py still imports from task_io; "
            "redirect to owlbear_kanban.storage per AC"
        )

    def test_engine_imports_read_task_from_storage(self) -> None:
        """engine.py must import read_task from owlbear_kanban.storage, not task_io."""
        source = _read_source("engine.py")
        # After migration, engine.py must have a direct storage import for read_task
        assert "from owlbear_kanban.storage import" in source, (
            "engine.py must use 'from owlbear_kanban.storage import ...' for its I/O calls"
        )
        # And must NOT fall back to task_io for any of those
        assert "task_io" not in source, (
            "engine.py still references task_io; all I/O must come from storage"
        )

    def test_engine_imports_write_task_from_storage(self) -> None:
        """engine.py must resolve write_task via owlbear_kanban.storage, not task_io."""
        source = _read_source("engine.py")
        assert "task_io" not in source, (
            "engine.py write_task must come from storage, not task_io"
        )


# ---------------------------------------------------------------------------
# AC-dispatch-redirected — dispatch.py redirected to storage
# ---------------------------------------------------------------------------


class TestFromAC_DispatchRedirected:
    """dispatch.py must import from owlbear_kanban.storage, not from task_io."""

    def test_dispatch_py_has_no_task_io_import(self) -> None:
        """dispatch.py source must not contain 'task_io'."""
        source = _read_source("dispatch.py")
        assert "task_io" not in source, (
            "dispatch.py still imports from task_io; "
            "redirect to owlbear_kanban.storage per AC"
        )

    def test_dispatch_imports_read_task_from_storage(self) -> None:
        """dispatch.py must resolve read_task from owlbear_kanban.storage."""
        source = _read_source("dispatch.py")
        assert "from owlbear_kanban.storage" in source or "from .storage" in source, (
            "dispatch.py must import read_task from owlbear_kanban.storage"
        )


# ---------------------------------------------------------------------------
# AC-corruption-redirected — corruption.py redirected to storage
# ---------------------------------------------------------------------------


class TestFromAC_CorruptionRedirected:
    """corruption.py must not import from task_io (lazy or otherwise)."""

    def test_corruption_py_has_no_task_io_import(self) -> None:
        """corruption.py source must not contain 'task_io'."""
        source = _read_source("corruption.py")
        assert "task_io" not in source, (
            "corruption.py still imports from task_io; "
            "redirect to owlbear_kanban.storage per AC"
        )


# ---------------------------------------------------------------------------
# AC-move_to_quarantine-containment — containment guard rejects out-of-board paths
# ---------------------------------------------------------------------------


class TestFromAC_QuarantineContainment:
    """move_to_quarantine must call validate_path_containment and reject paths outside kanban_dir."""

    def test_move_to_quarantine_rejects_path_outside_kanban_dir(
        self, tmp_path: Path
    ) -> None:
        """PermissionError raised when task_path resolves outside kanban_dir."""
        from owlbear_kanban.storage import move_to_quarantine

        kanban_dir = tmp_path / "board"
        kanban_dir.mkdir()
        outside_file = tmp_path / "evil.md"
        outside_file.write_text("content", encoding="utf-8")

        with pytest.raises(PermissionError):
            move_to_quarantine(outside_file, kanban_dir)

    def test_move_to_quarantine_rejects_sibling_directory_path(
        self, tmp_path: Path
    ) -> None:
        """PermissionError raised when task_path is in a sibling directory of kanban_dir."""
        from owlbear_kanban.storage import move_to_quarantine

        kanban_dir = tmp_path / "board"
        kanban_dir.mkdir()
        sibling_dir = tmp_path / "other"
        sibling_dir.mkdir()
        sibling_file = sibling_dir / "not-my-task.md"
        sibling_file.write_text("content", encoding="utf-8")

        with pytest.raises(PermissionError):
            move_to_quarantine(sibling_file, kanban_dir)

    def test_move_to_quarantine_does_not_create_quarantine_dir_on_rejection(
        self, tmp_path: Path
    ) -> None:
        """quarantine/ directory must NOT be created when the path is rejected."""
        from owlbear_kanban.storage import move_to_quarantine

        kanban_dir = tmp_path / "board"
        kanban_dir.mkdir()
        outside_file = tmp_path / "evil.md"
        outside_file.write_text("content", encoding="utf-8")

        with pytest.raises(PermissionError):
            move_to_quarantine(outside_file, kanban_dir)

        assert not (kanban_dir / "quarantine").exists(), (
            "quarantine/ must not be created when path containment is rejected"
        )


# ---------------------------------------------------------------------------
# Board helper for AC-C15 behavioral tests
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
next_id: 10
archive_dir: archive
activity_log: false
"""


def _make_board(tmp_path: Path) -> Path:
    """Create a minimal board directory structure. Returns kanban_dir."""
    kanban_dir = tmp_path / "board"
    kanban_dir.mkdir(parents=True)
    (kanban_dir / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
    (kanban_dir / "tasks").mkdir()
    (kanban_dir / "archive").mkdir()
    return kanban_dir


# ---------------------------------------------------------------------------
# AC-C15: vendor-extra timestamp normalization end-to-end through write_task()
# ---------------------------------------------------------------------------


class TestFromAC_VendorExtraTimestamps:
    """AC-C15 end-to-end proof for vendor extra fields through write_task().

    AC-C15 uses the universal quantifier 'All timestamps written', which
    encompasses vendor extra fields stored via extra='allow'.  The path at
    storage.py:397-399 applies _normalize_timestamp to every extra string
    value before writing.  Existing tests only exercise canonical fields
    (created, updated, claimed_at) or prove the helper in isolation.
    These tests provide the required direct write-side proof.
    """

    def test_vendor_extra_naive_timestamp_written_with_utc_offset(
        self, tmp_path: Path
    ) -> None:
        """AC-C15: vendor extra naive timestamp → +00:00 suffix on disk via write_task()."""
        from owlbear_kanban.models import Task
        from owlbear_kanban.storage import write_task

        kanban_dir = _make_board(tmp_path)
        task = Task(
            id=10,
            title="Vendor TS naive",
            status="todo",
            priority="important",
            created="2026-04-20T10:00:00+00:00",
            updated="2026-04-20T10:00:00+00:00",
            released_at="2026-04-20T09:00:00",  # naive — no timezone
        )
        write_task(task, kanban_dir)

        files = list((kanban_dir / "tasks").glob("*.md"))
        assert len(files) == 1
        content = files[0].read_text(encoding="utf-8")
        closing_idx = content.index("---\n", 4)
        frontmatter = content[4:closing_idx]

        released_at_line = next(
            (
                line
                for line in frontmatter.splitlines()
                if line.startswith("released_at:")
            ),
            None,
        )
        assert released_at_line is not None, (
            "released_at vendor extra field was not written to frontmatter by write_task()"
        )
        assert released_at_line.rstrip().endswith("+00:00"), (
            f"AC-C15: vendor extra naive timestamp not normalized to +00:00 by write_task(): "
            f"{released_at_line.rstrip()!r}"
        )

    def test_vendor_extra_z_suffix_timestamp_converted_to_plus_zero(
        self, tmp_path: Path
    ) -> None:
        """AC-C15: vendor extra timestamp with Z suffix → +00:00 on disk (Z replaced)."""
        from owlbear_kanban.models import Task
        from owlbear_kanban.storage import write_task

        kanban_dir = _make_board(tmp_path)
        task = Task(
            id=11,
            title="Vendor TS Z",
            status="todo",
            priority="important",
            created="2026-04-20T10:00:00+00:00",
            updated="2026-04-20T10:00:00+00:00",
            synced_at="2026-04-20T09:00:00Z",  # Z suffix — must become +00:00
        )
        write_task(task, kanban_dir)

        files = list((kanban_dir / "tasks").glob("*.md"))
        content = files[0].read_text(encoding="utf-8")
        closing_idx = content.index("---\n", 4)
        frontmatter = content[4:closing_idx]

        synced_at_line = next(
            (
                line
                for line in frontmatter.splitlines()
                if line.startswith("synced_at:")
            ),
            None,
        )
        assert synced_at_line is not None, (
            "synced_at vendor extra field was not written to frontmatter by write_task()"
        )
        assert "+00:00" in synced_at_line, (
            f"AC-C15: vendor extra Z timestamp not converted to +00:00: {synced_at_line.rstrip()!r}"
        )
        assert "Z" not in synced_at_line, (
            f"AC-C15: Z suffix must be replaced with +00:00, not kept as-is: {synced_at_line.rstrip()!r}"
        )

    def test_vendor_extra_non_timestamp_string_written_unchanged(
        self, tmp_path: Path
    ) -> None:
        """AC-C15 boundary: non-timestamp vendor extra strings pass through write_task() unmodified."""
        from owlbear_kanban.models import Task
        from owlbear_kanban.storage import write_task

        kanban_dir = _make_board(tmp_path)
        task = Task(
            id=12,
            title="Vendor non-TS",
            status="todo",
            priority="important",
            created="2026-04-20T10:00:00+00:00",
            updated="2026-04-20T10:00:00+00:00",
            external_ref="JIRA-42",  # plain string — must survive unchanged
        )
        write_task(task, kanban_dir)

        files = list((kanban_dir / "tasks").glob("*.md"))
        content = files[0].read_text(encoding="utf-8")
        closing_idx = content.index("---\n", 4)
        frontmatter = content[4:closing_idx]

        ext_ref_line = next(
            (
                line
                for line in frontmatter.splitlines()
                if line.startswith("external_ref:")
            ),
            None,
        )
        assert ext_ref_line is not None, (
            "external_ref vendor extra field was not written to frontmatter by write_task()"
        )
        assert "JIRA-42" in ext_ref_line, (
            f"AC-C15: non-timestamp vendor extra value must survive unchanged: {ext_ref_line.rstrip()!r}"
        )
