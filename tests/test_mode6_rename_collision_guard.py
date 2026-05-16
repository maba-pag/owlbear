"""Durable tests for mode-6 rename collision guarding in attempt_repair.

Promoted from archived task #1109 during test curation.
"""

from __future__ import annotations

from pathlib import Path

from owlbear_kanban.corruption import (
    ERR_CORRUPT_ID_FILENAME_MISMATCH,
    attempt_repair,
)
from owlbear_kanban.config_loader import load_config

# Promoted from archived task #1109.

# ---------------------------------------------------------------------------
# Board helpers
# ---------------------------------------------------------------------------

_CONFIG_YAML = """\
next_id: 1
"""

_VALID_TASK_42 = """\
---
id: 42
title: My Task
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

Valid task body.
"""

_CORRUPT_999_WRONG = """\
---
id: 42
title: My Task
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

Corrupt file — filename says 999 but frontmatter says 42.
"""


def _make_board(tmp_path: Path) -> Path:
    kanban_dir = tmp_path / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# TestFromAC_Mode6CollisionGuard — AC-1, AC-2, AC-3, AC-4
# ---------------------------------------------------------------------------


class TestFromAC_Mode6CollisionGuard:
    """AC-1 to AC-4: exists-guard for mode-6 rename in attempt_repair."""

    # AC-1 -------------------------------------------------------------------

    def test_ac1_collision_quarantines_corrupt_file(self, tmp_path: Path) -> None:
        """AC-1: mode-6 repair quarantines corrupt file when target path already exists."""
        kanban_dir = _make_board(tmp_path)
        config = load_config(kanban_dir)

        _write(kanban_dir / "tasks" / "42-my-task.md", _VALID_TASK_42)
        corrupt = kanban_dir / "tasks" / "999-wrong.md"
        _write(corrupt, _CORRUPT_999_WRONG)

        outcome = attempt_repair(corrupt, ERR_CORRUPT_ID_FILENAME_MISMATCH, config)

        assert outcome.action == "quarantined"

    def test_ac1_collision_corrupt_file_moved_to_quarantine_dir(self, tmp_path: Path) -> None:
        """AC-1: corrupt file physically ends up in quarantine/ after collision guard fires."""
        kanban_dir = _make_board(tmp_path)
        config = load_config(kanban_dir)

        _write(kanban_dir / "tasks" / "42-my-task.md", _VALID_TASK_42)
        corrupt = kanban_dir / "tasks" / "999-wrong.md"
        _write(corrupt, _CORRUPT_999_WRONG)

        attempt_repair(corrupt, ERR_CORRUPT_ID_FILENAME_MISMATCH, config)

        assert not corrupt.exists(), "Corrupt file must be removed from tasks/ after quarantine"
        quarantine_file = kanban_dir / "quarantine" / "999-wrong.md"
        assert quarantine_file.exists(), "Corrupt file must be present in quarantine/"

    def test_ac1_no_collision_does_not_quarantine(self, tmp_path: Path) -> None:
        """AC-1 contrast: mode-6 repair does NOT quarantine when target path is free."""
        kanban_dir = _make_board(tmp_path)
        config = load_config(kanban_dir)

        corrupt = kanban_dir / "tasks" / "999-wrong.md"
        _write(corrupt, _CORRUPT_999_WRONG)

        outcome = attempt_repair(corrupt, ERR_CORRUPT_ID_FILENAME_MISMATCH, config)

        assert outcome.action != "quarantined"

    # AC-2 -------------------------------------------------------------------

    def test_ac2_quarantine_outcome_action_is_quarantined(self, tmp_path: Path) -> None:
        """AC-2: RepairOutcome.action == 'quarantined' on collision."""
        kanban_dir = _make_board(tmp_path)
        config = load_config(kanban_dir)

        _write(kanban_dir / "tasks" / "42-my-task.md", _VALID_TASK_42)
        corrupt = kanban_dir / "tasks" / "999-wrong.md"
        _write(corrupt, _CORRUPT_999_WRONG)

        outcome = attempt_repair(corrupt, ERR_CORRUPT_ID_FILENAME_MISMATCH, config)

        assert outcome.action == "quarantined"

    def test_ac2_detail_mentions_rename_collision(self, tmp_path: Path) -> None:
        """AC-2: RepairOutcome.detail contains 'rename collision'."""
        kanban_dir = _make_board(tmp_path)
        config = load_config(kanban_dir)

        _write(kanban_dir / "tasks" / "42-my-task.md", _VALID_TASK_42)
        corrupt = kanban_dir / "tasks" / "999-wrong.md"
        _write(corrupt, _CORRUPT_999_WRONG)

        outcome = attempt_repair(corrupt, ERR_CORRUPT_ID_FILENAME_MISMATCH, config)

        assert "rename collision" in (outcome.detail or ""), (
            f"Expected 'rename collision' in detail, got: {outcome.detail!r}"
        )

    # AC-3 -------------------------------------------------------------------

    def test_ac3_existing_destination_file_content_untouched(self, tmp_path: Path) -> None:
        """AC-3: valid destination file is byte-for-byte identical after collision guard."""
        kanban_dir = _make_board(tmp_path)
        config = load_config(kanban_dir)

        valid_path = kanban_dir / "tasks" / "42-my-task.md"
        _write(valid_path, _VALID_TASK_42)
        original_content = valid_path.read_text(encoding="utf-8")

        corrupt = kanban_dir / "tasks" / "999-wrong.md"
        _write(corrupt, _CORRUPT_999_WRONG)

        attempt_repair(corrupt, ERR_CORRUPT_ID_FILENAME_MISMATCH, config)

        assert valid_path.exists(), "Valid destination file must still exist after collision guard"
        assert valid_path.read_text(encoding="utf-8") == original_content, (
            "Valid file content must be unchanged after collision guard fires"
        )

    # AC-4 -------------------------------------------------------------------

    def test_ac4_happy_path_no_collision_returns_fixed(self, tmp_path: Path) -> None:
        """AC-4: mode-6 rename with no collision returns action='fixed'."""
        kanban_dir = _make_board(tmp_path)
        config = load_config(kanban_dir)

        corrupt = kanban_dir / "tasks" / "999-wrong.md"
        _write(corrupt, _CORRUPT_999_WRONG)

        outcome = attempt_repair(corrupt, ERR_CORRUPT_ID_FILENAME_MISMATCH, config)

        assert outcome.action == "fixed"

    def test_ac4_happy_path_renamed_file_exists(self, tmp_path: Path) -> None:
        """AC-4: after successful mode-6 rename, renamed file exists in tasks/."""
        kanban_dir = _make_board(tmp_path)
        config = load_config(kanban_dir)

        corrupt = kanban_dir / "tasks" / "999-wrong.md"
        _write(corrupt, _CORRUPT_999_WRONG)

        attempt_repair(corrupt, ERR_CORRUPT_ID_FILENAME_MISMATCH, config)

        renamed = kanban_dir / "tasks" / "42-my-task.md"
        assert renamed.exists(), "Renamed file must exist in tasks/ after happy-path mode-6 repair"

    def test_ac4_happy_path_original_file_gone(self, tmp_path: Path) -> None:
        """AC-4: after successful mode-6 rename, original corrupt file no longer exists."""
        kanban_dir = _make_board(tmp_path)
        config = load_config(kanban_dir)

        corrupt = kanban_dir / "tasks" / "999-wrong.md"
        _write(corrupt, _CORRUPT_999_WRONG)

        attempt_repair(corrupt, ERR_CORRUPT_ID_FILENAME_MISMATCH, config)

        assert not corrupt.exists(), "Original corrupt file must be gone after happy-path rename"

    def test_ac4_happy_path_outcome_task_id_is_frontmatter_id(self, tmp_path: Path) -> None:
        """AC-4: RepairOutcome.task_id matches the frontmatter id (42), not the filename (999)."""
        kanban_dir = _make_board(tmp_path)
        config = load_config(kanban_dir)

        corrupt = kanban_dir / "tasks" / "999-wrong.md"
        _write(corrupt, _CORRUPT_999_WRONG)

        outcome = attempt_repair(corrupt, ERR_CORRUPT_ID_FILENAME_MISMATCH, config)

        assert outcome.task_id == 42
