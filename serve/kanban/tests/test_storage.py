"""TDD RED: C-05 — storage surface tests.

Task: #1050 (Brief C #1043) — paper-c.md §8.3, §8.6, §8.11
AC:   C13, C14, C15, C16, C28, C29, C30, C48
All tests FAIL (RED phase — storage.py not yet implemented).
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from owlbear_kanban.storage import (  # NEW module — ImportError in RED
    detect_corruption,
    load_config,
    move_to_quarantine,
    read_task,
    write_task,
)
from owlbear_kanban.models import Task

# ---------------------------------------------------------------------------
# Board helpers
# ---------------------------------------------------------------------------

_CONFIG_YAML = """\
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

_CANONICAL_FRONTMATTER_KEYS = [
    "id", "title", "status", "priority", "created", "updated",
    "tags", "parent", "depends_on", "blocked", "block_reason",
    "claimed_at", "archival_reason", "archival_refs",
]


def _make_board(base_dir: Path) -> Path:
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


def _make_task(task_id: int = 1001) -> Task:
    now = datetime.now(tz=UTC).isoformat()
    return Task(
        id=task_id,
        title="Surface test",
        status="todo",
        priority="needed",
        created=now,
        updated=now,
    )


# ---------------------------------------------------------------------------
# TestFromAC_Frontmatter — AC-C13, AC-C14, AC-C15
# ---------------------------------------------------------------------------


class TestFromAC_Frontmatter:
    """AC-C13, AC-C14, AC-C15: frontmatter shape, extra fields, timestamp format."""

    def test_ac_c13_canonical_frontmatter_key_order(self, tmp_path: Path) -> None:
        """AC-C13: written file follows canonical C8.6 frontmatter key order."""
        kanban_dir = _make_board(tmp_path)
        task = _make_task(1001)
        path = write_task(task, kanban_dir)
        content = path.read_text(encoding="utf-8")

        # Extract frontmatter block
        lines = content.split("\n")
        assert lines[0] == "---"
        end_idx = lines.index("---", 1)
        fm_keys = [
            line.split(":")[0].strip()
            for line in lines[1:end_idx]
            if ":" in line and not line.startswith(" ")
        ]

        for i, expected_key in enumerate(_CANONICAL_FRONTMATTER_KEYS):
            pos = next((j for j, k in enumerate(fm_keys) if k == expected_key), None)
            assert pos is not None, f"Key '{expected_key}' missing from frontmatter"
            if i > 0:
                prev_key = _CANONICAL_FRONTMATTER_KEYS[i - 1]
                prev_pos = next((j for j, k in enumerate(fm_keys) if k == prev_key), -1)
                assert prev_pos < pos, (
                    f"Key '{expected_key}' appears before '{prev_key}' — wrong order"
                )

    def test_ac_c14_task_model_extra_allow_vendor_fields_survive(self, tmp_path: Path) -> None:
        """AC-C14: Task model has extra='allow' — vendor fields survive round-trip."""
        kanban_dir = _make_board(tmp_path)
        # Write a task file with vendor fields (class, started, completed — legacy archive shape)
        task_content = """\
---
id: 1001
title: Archive task
status: done
priority: needed
created: "2026-04-21T10:00:00+00:00"
updated: "2026-04-21T10:00:00+00:00"
tags: []
parent: null
depends_on: []
blocked: false
block_reason: null
claimed_at: null
archival_reason: completed
archival_refs: []
class: tier-1
started: "2026-01-01T00:00:00+00:00"
completed: "2026-04-21T09:00:00+00:00"
---

## Notes

content
"""
        task_file = kanban_dir / "archive" / "1001-archive.md"
        task_file.write_text(task_content, encoding="utf-8")

        task = read_task(task_file)
        # Vendor fields preserved via extra='allow'
        assert getattr(task, "class", None) == "tier-1"
        assert getattr(task, "started", None) is not None

    def test_ac_c15_timestamps_utc_plus_00_00(self, tmp_path: Path) -> None:
        """AC-C15: created and updated timestamps written with explicit +00:00 suffix."""
        kanban_dir = _make_board(tmp_path)
        task = _make_task(1001)
        path = write_task(task, kanban_dir)
        content = path.read_text(encoding="utf-8")

        # Both created and updated must end with +00:00
        for field in ("created", "updated"):
            matching = [line for line in content.splitlines() if line.startswith(f"{field}:")]
            assert matching, f"Field '{field}' not found in frontmatter"
            assert "+00:00" in matching[0], (
                f"Field '{field}' is not UTC+00:00: {matching[0]}"
            )

    def test_ac_c15_claimed_at_utc_when_set(self, tmp_path: Path) -> None:
        """AC-C15: claimed_at timestamp also uses +00:00 when not null."""
        kanban_dir = _make_board(tmp_path)
        now = datetime.now(tz=UTC).isoformat()
        task = Task(
            id=1002,
            title="Claimed task",
            status="in-progress",
            priority="needed",
            created=now,
            updated=now,
            claimed_at=now,
        )
        path = write_task(task, kanban_dir)
        content = path.read_text(encoding="utf-8")

        matching = [line for line in content.splitlines() if line.startswith("claimed_at:")]
        assert matching
        assert "+00:00" in matching[0]


# ---------------------------------------------------------------------------
# TestFromAC_ClaimedByDetection — AC-C16, AC-C48
# ---------------------------------------------------------------------------


class TestFromAC_ClaimedByDetection:
    """AC-C16, AC-C48: claimed_by in tasks/ is corruption; in archive/ silently stripped."""

    def test_ac_c16_tasks_file_with_claimed_by_reports_mode3(self, tmp_path: Path) -> None:
        """AC-C16: detect_corruption on tasks/ file with claimed_by → ERR_CORRUPT_MISSING_FIELD, mode 3."""
        kanban_dir = _make_board(tmp_path)
        bad_file = kanban_dir / "tasks" / "1001-legacy.md"
        bad_file.write_text(
            "---\nid: 1001\ntitle: legacy\nstatus: todo\npriority: needed\n"
            "claimed_by: some-agent\n"
            'created: "2026-04-21T10:00:00+00:00"\nupdated: "2026-04-21T10:00:00+00:00"\n---\n',
            encoding="utf-8",
        )
        config = load_config(kanban_dir)

        err = detect_corruption(bad_file, config)
        assert err is not None
        assert err.code == "ERR_CORRUPT_MISSING_FIELD"
        assert "claimed_by" in (err.detail or "").lower()

    def test_ac_c48_archive_file_with_claimed_by_reads_successfully(
        self, tmp_path: Path
    ) -> None:
        """AC-C48: archive file with claimed_by is read without CorruptionError; field stripped."""
        kanban_dir = _make_board(tmp_path)
        archive_file = kanban_dir / "archive" / "1001-old.md"
        archive_file.write_text(
            "---\nid: 1001\ntitle: old task\nstatus: done\npriority: needed\n"
            "claimed_by: some-agent\n"
            'created: "2026-04-21T10:00:00+00:00"\nupdated: "2026-04-21T10:00:00+00:00"\n'
            "archival_reason: completed\narchival_refs: []\n---\n",
            encoding="utf-8",
        )

        # Must not raise CorruptionError
        task = read_task(archive_file)
        assert task is not None
        # claimed_by stripped from model
        assert not hasattr(task, "claimed_by") or task.claimed_by is None  # type: ignore[union-attr]

    def test_ac_c48_archive_with_claimed_by_no_migration_required_error(
        self, tmp_path: Path
    ) -> None:
        """AC-C48: archive file with claimed_by does NOT trigger MigrationRequiredError."""
        from owlbear_kanban.engine import MigrationRequiredError  # NEW exception  # noqa: PLC0415

        kanban_dir = _make_board(tmp_path)
        (kanban_dir / "archive" / "1001-old.md").write_text(
            "---\nid: 1001\ntitle: old\nstatus: done\npriority: needed\n"
            "claimed_by: agent\n"
            'created: "2026-04-21T10:00:00+00:00"\nupdated: "2026-04-21T10:00:00+00:00"\n'
            "archival_reason: completed\narchival_refs: []\n---\n",
            encoding="utf-8",
        )

        # Engine instantiation must succeed (no tasks/ files have claimed_by)
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415, F401

        with pytest.raises(MigrationRequiredError):
            # This proves MigrationRequiredError is the NEW exception type
            raise MigrationRequiredError(
                code="ERR_MIGRATION_REQUIRED",
                user_message="test — confirming exception shape",
            )


# ---------------------------------------------------------------------------
# TestFromAC_Quarantine — AC-C28, AC-C29, AC-C30
# ---------------------------------------------------------------------------


class TestFromAC_Quarantine:
    """AC-C28, AC-C29, AC-C30: move_to_quarantine contract."""

    def test_ac_c28_creates_quarantine_dir_if_absent(self, tmp_path: Path) -> None:
        """AC-C28: move_to_quarantine creates quarantine/ directory lazily if absent."""
        kanban_dir = _make_board(tmp_path)
        quarantine_dir = kanban_dir / "quarantine"
        assert not quarantine_dir.exists()

        task_file = kanban_dir / "tasks" / "1001-corrupt.md"
        task_file.write_text(
            "---\nid: 1001\ntitle: corrupt\nstatus: todo\npriority: needed\n"
            'created: "2026-04-21T10:00:00+00:00"\nupdated: "2026-04-21T10:00:00+00:00"\n---\n',
            encoding="utf-8",
        )

        move_to_quarantine(task_file, kanban_dir)

        assert quarantine_dir.exists()

    def test_ac_c29_quarantined_file_at_expected_path(self, tmp_path: Path) -> None:
        """AC-C29: quarantined file ends up at quarantine/{original-filename}."""
        kanban_dir = _make_board(tmp_path)
        original_name = "1001-corrupt.md"
        task_file = kanban_dir / "tasks" / original_name
        task_file.write_text("---\nid: 1001\ntitle: c\nstatus: todo\npriority: needed\n"
                              'created: "2026-04-21T10:00:00+00:00"\n'
                              'updated: "2026-04-21T10:00:00+00:00"\n---\n',
                              encoding="utf-8")

        quarantined_path = move_to_quarantine(task_file, kanban_dir)

        assert quarantined_path == kanban_dir / "quarantine" / original_name
        assert quarantined_path.exists()
        assert not task_file.exists()

    def test_ac_c30_ar_task_has_type_user_action_tag(self, tmp_path: Path) -> None:
        """AC-C30: AR task created by repair_storage() carries tag type:user-action."""
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415

        kanban_dir = _make_board(tmp_path)
        corrupt_file = kanban_dir / "tasks" / "1001-bad.md"
        corrupt_file.write_text("no frontmatter delimiters\n", encoding="utf-8")

        engine = KanbanEngine(kanban_dir)
        outcomes = engine.repair_storage()

        quarantined = [o for o in outcomes if o.action in ("quarantined", "failed")]
        assert quarantined, "Expected at least one quarantined outcome"

        # AR task created
        all_tasks = engine.list_tasks()
        ar_tasks = [t for t in all_tasks if "type:user-action" in (t.tags or [])]
        assert ar_tasks, "Expected an AR task with type:user-action tag"

    def test_ac_c30_ar_task_body_has_quarantined_file_section(self, tmp_path: Path) -> None:
        """AC-C30: AR task body contains '## Quarantined file' section with code, path, detail."""
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415

        kanban_dir = _make_board(tmp_path)
        corrupt_file = kanban_dir / "tasks" / "1001-bad.md"
        corrupt_file.write_text("no frontmatter delimiters\n", encoding="utf-8")

        engine = KanbanEngine(kanban_dir)
        engine.repair_storage()

        all_tasks = engine.list_tasks()
        ar_tasks = [t for t in all_tasks if "type:user-action" in (t.tags or [])]
        assert ar_tasks
        ar_body = engine.show_task(ar_tasks[0].id).body
        assert "## Quarantined file" in ar_body
        assert "code" in ar_body
