"""Tests for #1200: Remove claimed_by ghost field from Task model.

AC lines tested:
  - AC1 (td:1): ``claimed_by`` not in ``Task.model_fields``
  - AC3 (td:1): On-disk legacy handling unchanged — storage.py pop,
    corruption.py detection, migrate.py removal, engine migration gate.

All AC3 tests gate on the AC1 assertion so they fail in RED alongside it.
After the builder removes the field declaration the gate passes and each
test verifies the specific legacy handler is still intact.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import owlbear_kanban.migrate as _migrate_mod
from owlbear_kanban.config_loader import load_config
from owlbear_kanban.corruption import detect_corruption
from owlbear_kanban.engine import KanbanEngine, MigrationRequiredError
from owlbear_kanban.models import Task
from owlbear_kanban.storage import write_task

# ---------------------------------------------------------------------------
# Board helper
# ---------------------------------------------------------------------------

_CONFIG_YAML = """\
next_id: 1
"""

_TASK_TIMESTAMPS = {
    "created": "2026-01-01T00:00:00+00:00",
    "updated": "2026-01-01T00:00:00+00:00",
}


def _make_board(base_dir: Path) -> Path:
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


def _legacy_task_content(*, task_id: int = 1, claimed_by: str = "some-agent") -> str:
    """Return raw frontmatter content for a legacy task with a non-null claimed_by."""
    return (
        "---\n"
        f"id: {task_id}\n"
        f"title: Legacy Task {task_id}\n"
        "status: todo\n"
        "priority: needed\n"
        f'created: "2026-01-01T00:00:00+00:00"\n'
        f'updated: "2026-01-01T00:00:00+00:00"\n'
        f"claimed_by: {claimed_by}\n"
        "---\n"
    )


# ---------------------------------------------------------------------------
# TestFromAC_ClaimedByFieldRemoval
# ---------------------------------------------------------------------------


class TestFromAC_ClaimedByFieldRemoval:
    """AC1: claimed_by must not appear in Task.model_fields after field removal."""

    def test_claimed_by_not_in_task_model_fields(self) -> None:
        """AC1: claimed_by must not be a declared field on Task.

        Currently FAILS because models.py declares:
            claimed_by: str | None = Field(default=None, exclude=True)
        After the builder removes that declaration this test passes.
        """
        assert "claimed_by" not in Task.model_fields, (
            "claimed_by is still declared in Task.model_fields. Remove the field declaration from models.py."
        )


# ---------------------------------------------------------------------------
# TestFromAC_LegacyOnDiskHandling
# ---------------------------------------------------------------------------


class TestFromAC_LegacyOnDiskHandling:
    """AC3: legacy on-disk handlers are unchanged after model field removal.

    All tests gate on the AC1 assertion so they fail in RED and only pass
    once the builder has removed the field declaration AND left the legacy
    handlers intact.
    """

    def test_storage_pop_prevents_claimed_by_reaching_disk(self, tmp_path: Path) -> None:
        """AC3(storage): write_task must not write claimed_by to disk.

        With extra="allow" on Task, removing the declared field means any
        claimed_by kwarg becomes an extra field present in model_dump().
        The data.pop('claimed_by', None) guard in storage.py must still
        strip it before the file is written.

        Gate: fails now because claimed_by is still a declared field.
        """
        assert "claimed_by" not in Task.model_fields, (
            "Gate: remove claimed_by from Task.model_fields before this test can pass."
        )
        kanban_dir = _make_board(tmp_path)
        task = Task(
            id=1,
            title="Ghost",
            status="todo",
            priority="needed",
            claimed_by="agent-x",
            **_TASK_TIMESTAMPS,
        )
        write_task(task, kanban_dir)

        files = list((kanban_dir / "tasks").glob("1-*.md"))
        assert files, "write_task must create a task file"
        content = files[0].read_text(encoding="utf-8")
        assert "claimed_by" not in content, (
            "storage.py write_task wrote claimed_by to disk. "
            "Ensure the data.pop('claimed_by', None) guard is still present."
        )

    def test_corruption_detection_flags_claimed_by_in_raw_frontmatter(self, tmp_path: Path) -> None:
        """AC3(corruption): detect_corruption must still flag non-null claimed_by.

        corruption.py operates on raw YAML dicts independent of the Task model;
        Mode 3 must return ERR_CORRUPT_MISSING_FIELD with a detail mentioning
        claimed_by when the frontmatter carries a non-null value.

        Gate: fails now because claimed_by is still a declared field.
        """
        assert "claimed_by" not in Task.model_fields, (
            "Gate: remove claimed_by from Task.model_fields before this test can pass."
        )
        kanban_dir = _make_board(tmp_path)
        task_file = kanban_dir / "tasks" / "1-legacy.md"
        task_file.write_text(_legacy_task_content(), encoding="utf-8")

        config = load_config(kanban_dir)
        error = detect_corruption(task_file, config)

        assert error is not None, (
            "detect_corruption returned None for a file with non-null claimed_by. "
            "The Mode 3 forbidden-field check in corruption.py was removed or broken."
        )
        assert "claimed_by" in error.detail, (
            f"CorruptionError.detail does not mention claimed_by: {error.detail!r}. "
            "The detail string must be 'forbidden field claimed_by present'."
        )

    def test_migrate_strips_claimed_by_from_task_frontmatter(self, tmp_path: Path) -> None:
        """AC3(migrate): _migrate_task_file must remove claimed_by from frontmatter.

        The fm.pop('claimed_by', None) in migrate.py must still execute so
        that legacy files are cleaned during migration runs.

        Gate: fails now because claimed_by is still a declared field.
        """
        assert "claimed_by" not in Task.model_fields, (
            "Gate: remove claimed_by from Task.model_fields before this test can pass."
        )
        task_file = tmp_path / "1-legacy.md"
        task_file.write_text(_legacy_task_content(), encoding="utf-8")

        outcome, reason = _migrate_mod._migrate_task_file(task_file)

        assert outcome == "migrated", (
            f"_migrate_task_file returned {outcome!r} (reason={reason!r}) "
            "instead of 'migrated'. The file may have failed to parse or write."
        )
        content = task_file.read_text(encoding="utf-8")
        assert "claimed_by" not in content, (
            "migrate.py did not strip claimed_by from the task frontmatter. "
            "The fm.pop('claimed_by', None) guard was removed or is unreachable."
        )

    def test_engine_migration_gate_raises_on_legacy_claimed_by(self, tmp_path: Path) -> None:
        """AC3(migration gate): KanbanEngine.__init__ must raise MigrationRequiredError.

        The migration gate in engine.py scans tasks/ frontmatter for non-null
        claimed_by and raises if found.  It must still trigger after the Task
        model field is removed, since it operates on raw file content.

        Gate: fails now because claimed_by is still a declared field.
        """
        assert "claimed_by" not in Task.model_fields, (
            "Gate: remove claimed_by from Task.model_fields before this test can pass."
        )
        kanban_dir = _make_board(tmp_path)
        (kanban_dir / "tasks" / "1-legacy.md").write_text(_legacy_task_content(), encoding="utf-8")

        with pytest.raises(MigrationRequiredError) as exc_info:
            KanbanEngine(kanban_dir)

        assert exc_info.value.code == "ERR_MIGRATION_REQUIRED", (
            f"Expected code='ERR_MIGRATION_REQUIRED', got {exc_info.value.code!r}. "
            "The migration gate in engine.py must still raise on legacy claimed_by."
        )
