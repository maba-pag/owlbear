from __future__ import annotations
import importlib
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from owlbear_kanban.config_loader import load_config
from owlbear_kanban.corruption import detect_corruption
from owlbear_kanban.storage import (  # NEW module — ImportError in RED
    MigrationRequiredError,
    move_to_quarantine,
    read_task,
    write_task,
)
from owlbear_kanban.models import Task
import ast
from unittest.mock import patch
import pytest
from owlbear_kanban.corruption import ERR_CORRUPT_INVALID_STATUS, CorruptionError
from owlbear_kanban.models import BoardConfig
import owlbear_kanban.storage as storage_mod

"""TDD RED: C-05 — storage surface tests.

Task: #1050 (Brief C #1043) — paper-c.md §8.3, §8.6, §8.11
AC:   C13, C14, C15, C16, C28, C29, C30, C48
All tests FAIL (RED phase — storage.py not yet implemented).
"""


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
    "id",
    "title",
    "status",
    "priority",
    "created",
    "updated",
    "tags",
    "parent",
    "depends_on",
    "blocked",
    "block_reason",
    "claimed_at",
    "archival_reason",
    "archival_refs",
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

    def test_ac_c14_task_model_extra_allow_vendor_fields_survive(
        self, tmp_path: Path
    ) -> None:
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
            matching = [
                line for line in content.splitlines() if line.startswith(f"{field}:")
            ]
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

        matching = [
            line for line in content.splitlines() if line.startswith("claimed_at:")
        ]
        assert matching
        assert "+00:00" in matching[0]

    def test_written_frontmatter_fields_in_canonical_order(
        self, tmp_path: Path
    ) -> None:
        """AC-C13: Canonical keys in the written file appear in canonical order."""
        kanban_dir = _make_board(tmp_path)
        task = _minimal_task(1)
        write_task(task, kanban_dir)

        files = list((kanban_dir / "tasks").glob("*.md"))
        assert len(files) == 1

        keys = _extract_frontmatter_keys(files[0])
        written_canonical = [k for k in keys if k in _CANONICAL_FIELD_ORDER]
        expected_order = [k for k in _CANONICAL_FIELD_ORDER if k in keys]
        assert written_canonical == expected_order

    def test_vendor_extra_fields_appear_after_canonical_fields(
        self, tmp_path: Path
    ) -> None:
        """AC-C13 edge: extra fields are not interleaved with canonical fields."""
        kanban_dir = _make_board(tmp_path)
        task = Task(
            id=2,
            title="Vendor ordering",
            status="todo",
            priority="important",
            created="2026-04-20T10:00:00+00:00",
            updated="2026-04-20T10:00:00+00:00",
            **{"class": "epic", "started": "2026-04-20"},
        )
        write_task(task, kanban_dir)

        files = list((kanban_dir / "tasks").glob("*.md"))
        assert len(files) == 1

        keys = _extract_frontmatter_keys(files[0])
        canonical_positions = [
            i for i, k in enumerate(keys) if k in _CANONICAL_FIELD_ORDER
        ]
        vendor_positions = [
            i for i, k in enumerate(keys) if k not in _CANONICAL_FIELD_ORDER
        ]

        if canonical_positions and vendor_positions:
            assert max(canonical_positions) < min(vendor_positions), (
                f"Vendor key(s) appear before canonical keys: {keys}"
            )

    def test_task_model_accepts_vendor_extra_fields(self) -> None:
        """AC-C14: Task model extra='allow' parses vendor fields."""
        task = Task(
            id=1,
            title="Vendor model test",
            status="todo",
            priority="important",
            created="2026-04-20T10:00:00+00:00",
            updated="2026-04-20T10:00:00+00:00",
            **{"class": "epic", "started": "2026-04-20"},
        )
        dumped = task.model_dump()
        assert dumped.get("class") == "epic"
        assert dumped.get("started") == "2026-04-20"

    def test_vendor_extra_fields_survive_write_read_round_trip(
        self, tmp_path: Path
    ) -> None:
        """AC-C14: Vendor fields survive storage.write_task -> storage.read_task round-trip."""
        kanban_dir = _make_board(tmp_path)
        task = Task(
            id=3,
            title="Vendor round-trip",
            status="todo",
            priority="important",
            created="2026-04-20T10:00:00+00:00",
            updated="2026-04-20T10:00:00+00:00",
            **{"class": "epic", "completed": "2026-04-21T00:00:00+00:00"},
        )
        write_task(task, kanban_dir)

        files = list((kanban_dir / "tasks").glob("*.md"))
        assert len(files) == 1
        read_back = read_task(files[0])
        dumped = read_back.model_dump()
        assert dumped.get("class") == "epic"

    def test_all_timestamp_fields_end_with_utc_offset(self, tmp_path: Path) -> None:
        """AC-C15: Every timestamp in written frontmatter ends with +00:00."""
        kanban_dir = _make_board(tmp_path)
        task = _minimal_task(1)
        write_task(task, kanban_dir)

        files = list((kanban_dir / "tasks").glob("*.md"))
        content = files[0].read_text(encoding="utf-8")
        closing_idx = content.index("---\n", 4)
        frontmatter = content[4:closing_idx]

        ts_re = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")
        for line in frontmatter.splitlines():
            if ts_re.search(line):
                assert line.rstrip().endswith("+00:00"), (
                    f"Timestamp line missing +00:00 suffix: {line.rstrip()!r}"
                )

    def test_naive_timestamps_stored_with_utc_offset(self, tmp_path: Path) -> None:
        """AC-C15 boundary: naive timestamp strings are written as UTC +00:00."""
        kanban_dir = _make_board(tmp_path)
        task = Task(
            id=2,
            title="Naive TS",
            status="todo",
            priority="important",
            created="2026-04-20T10:00:00",
            updated="2026-04-20T11:00:00",
        )
        write_task(task, kanban_dir)

        files = list((kanban_dir / "tasks").glob("*.md"))
        content = files[0].read_text(encoding="utf-8")
        closing_idx = content.index("---\n", 4)
        frontmatter = content[4:closing_idx]

        ts_re = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")
        for line in frontmatter.splitlines():
            if ts_re.search(line):
                assert line.rstrip().endswith("+00:00"), (
                    f"Expected +00:00 suffix on naive timestamp: {line.rstrip()!r}"
                )

    def test_non_utc_offset_timestamps_are_converted_to_utc(
        self, tmp_path: Path
    ) -> None:
        """AC-C15 boundary: non-UTC offset fields are converted to UTC +00:00."""
        kanban_dir = _make_board(tmp_path)
        task = Task(
            id=4,
            title="Non-UTC offset",
            status="todo",
            priority="important",
            created="2026-04-20T10:00:00+02:00",
            updated="2026-04-20T12:00:00+02:00",
        )
        write_task(task, kanban_dir)

        files = list((kanban_dir / "tasks").glob("*.md"))
        assert len(files) == 1
        content = files[0].read_text(encoding="utf-8")
        closing_idx = content.index("---\n", 4)
        frontmatter = content[4:closing_idx]

        ts_re = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")
        for line in frontmatter.splitlines():
            if ts_re.search(line):
                assert line.rstrip().endswith("+00:00"), (
                    f"Non-UTC offset not converted to +00:00: {line.rstrip()!r}"
                )
        assert "2026-04-20T08:00:00+00:00" in frontmatter
        assert "2026-04-20T10:00:00+00:00" in frontmatter


# ---------------------------------------------------------------------------
# TestFromAC_ClaimedByDetection — AC-C16, AC-C48
# ---------------------------------------------------------------------------


class TestFromAC_ClaimedByDetection:
    """AC-C16, AC-C48: claimed_by in tasks/ is corruption; in archive/ silently stripped."""

    def test_ac_c16_tasks_file_with_claimed_by_reports_mode3(
        self, tmp_path: Path
    ) -> None:
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
        """AC-C48: KanbanEngine init does NOT raise MigrationRequiredError when claimed_by is only in archive/."""
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415

        kanban_dir = _make_board(tmp_path)
        (kanban_dir / "archive" / "1001-old.md").write_text(
            "---\nid: 1001\ntitle: old\nstatus: done\npriority: needed\n"
            "claimed_by: agent\n"
            'created: "2026-04-21T10:00:00+00:00"\nupdated: "2026-04-21T10:00:00+00:00"\n'
            "archival_reason: completed\narchival_refs: []\n---\n",
            encoding="utf-8",
        )

        # Engine instantiation must succeed — archive claimed_by must not trigger migration gate
        engine = KanbanEngine(kanban_dir)
        assert engine is not None


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
        task_file.write_text(
            "---\nid: 1001\ntitle: c\nstatus: todo\npriority: needed\n"
            'created: "2026-04-21T10:00:00+00:00"\n'
            'updated: "2026-04-21T10:00:00+00:00"\n---\n',
            encoding="utf-8",
        )

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

    def test_ac_c30_ar_task_body_has_quarantined_file_section(
        self, tmp_path: Path
    ) -> None:
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

    def test_move_to_quarantine_creates_dir_when_absent(self, tmp_path: Path) -> None:
        """AC-C28: quarantine/ is created on first call when it does not exist."""
        kanban_dir = _make_board(tmp_path)
        assert not (kanban_dir / "quarantine").exists()

        task_path = _write_claimed_by_file(kanban_dir / "tasks", task_id=99)
        move_to_quarantine(task_path, kanban_dir)

        assert (kanban_dir / "quarantine").is_dir()

    def test_move_to_quarantine_no_error_when_dir_already_exists(
        self, tmp_path: Path
    ) -> None:
        """AC-C28 edge: quarantine/ pre-existing - no error raised."""
        kanban_dir = _make_board(tmp_path)
        (kanban_dir / "quarantine").mkdir()

        task_path = _write_claimed_by_file(kanban_dir / "tasks", task_id=99)
        move_to_quarantine(task_path, kanban_dir)

    def test_move_to_quarantine_returns_quarantine_subpath(
        self, tmp_path: Path
    ) -> None:
        """AC-C29: Return value is quarantine/{original-filename}."""
        kanban_dir = _make_board(tmp_path)
        task_path = _write_claimed_by_file(kanban_dir / "tasks", task_id=7)
        original_name = task_path.name

        result_path = move_to_quarantine(task_path, kanban_dir)

        assert result_path == kanban_dir / "quarantine" / original_name

    def test_move_to_quarantine_file_exists_at_returned_path(
        self, tmp_path: Path
    ) -> None:
        """AC-C29: Quarantined file physically exists at quarantine/{original-filename}."""
        kanban_dir = _make_board(tmp_path)
        task_path = _write_claimed_by_file(kanban_dir / "tasks", task_id=8)
        original_name = task_path.name

        result_path = move_to_quarantine(task_path, kanban_dir)

        expected = kanban_dir / "quarantine" / original_name
        assert result_path.exists()
        assert result_path == expected

    def test_move_to_quarantine_source_file_removed(self, tmp_path: Path) -> None:
        """AC-C29: Original file is no longer present in tasks/ after quarantine."""
        kanban_dir = _make_board(tmp_path)
        task_path = _write_claimed_by_file(kanban_dir / "tasks", task_id=9)

        move_to_quarantine(task_path, kanban_dir)

        assert not task_path.exists()

    def test_move_to_quarantine_preserves_file_content(self, tmp_path: Path) -> None:
        """AC-C29: Content of the quarantined file is identical to the original."""
        kanban_dir = _make_board(tmp_path)
        task_path = _write_claimed_by_file(kanban_dir / "tasks", task_id=10)
        original_content = task_path.read_text(encoding="utf-8")

        result_path = move_to_quarantine(task_path, kanban_dir)

        assert result_path.read_text(encoding="utf-8") == original_content

    def test_ac_c28_creates_quarantine_dir_if_absent_frontmatter_variant(
        self, tmp_path: Path
    ) -> None:
        """Parity check for merged frontmatter variant of AC-C28."""
        kanban_dir = _make_board(tmp_path)
        quarantine_dir = kanban_dir / "quarantine"
        assert not quarantine_dir.exists()

        task_file = kanban_dir / "tasks" / "2001-corrupt.md"
        task_file.write_text(
            "---\nid: 2001\ntitle: corrupt\nstatus: todo\npriority: needed\n"
            'created: "2026-04-21T10:00:00+00:00"\nupdated: "2026-04-21T10:00:00+00:00"\n---\n',
            encoding="utf-8",
        )
        move_to_quarantine(task_file, kanban_dir)
        assert quarantine_dir.exists()

    def test_ac_c29_quarantined_file_at_expected_path_frontmatter_variant(
        self, tmp_path: Path
    ) -> None:
        """Parity check for merged frontmatter variant of AC-C29."""
        kanban_dir = _make_board(tmp_path)
        original_name = "2002-corrupt.md"
        task_file = kanban_dir / "tasks" / original_name
        task_file.write_text(
            "---\nid: 2002\ntitle: c\nstatus: todo\npriority: needed\n"
            'created: "2026-04-21T10:00:00+00:00"\n'
            'updated: "2026-04-21T10:00:00+00:00"\n---\n',
            encoding="utf-8",
        )

        quarantined_path = move_to_quarantine(task_file, kanban_dir)
        assert quarantined_path == kanban_dir / "quarantine" / original_name
        assert quarantined_path.exists()
        assert not task_file.exists()

    def test_ac_c30_ar_task_has_type_user_action_tag_frontmatter_variant(
        self, tmp_path: Path
    ) -> None:
        """Parity check for merged frontmatter variant of AC-C30 tag behavior."""
        from owlbear_kanban import KanbanEngine  # noqa: PLC0415

        kanban_dir = _make_board(tmp_path)
        corrupt_file = kanban_dir / "tasks" / "2003-bad.md"
        corrupt_file.write_text("no frontmatter delimiters\n", encoding="utf-8")

        engine = KanbanEngine(kanban_dir)
        outcomes = engine.repair_storage()
        quarantined = [o for o in outcomes if o.action in ("quarantined", "failed")]
        assert quarantined

        all_tasks = engine.list_tasks()
        ar_tasks = [t for t in all_tasks if "type:user-action" in (t.tags or [])]
        assert ar_tasks


"""RED-phase tests for threading cached config through read_task hot path (#1205).

AC1 (td:1) → TestFromAC_ReadTaskCachedConfig.test_ac1_accepts_config_keyword_arg
AC1 (td:1) → TestFromAC_ReadTaskCachedConfig.test_ac1_config_provided_skips_load_config_call
AC1 (td:1) → TestFromAC_ReadTaskCachedConfig.test_ac1_config_param_is_keyword_only
AC2 (td:2) → TestFromAC_ReadTaskCachedConfig.test_ac2_happy_valid_task_no_config_yml_config_provided
AC2 (td:2) → TestFromAC_ReadTaskCachedConfig.test_ac2_edge_corrupt_task_no_config_yml_config_provided_raises
AC2 (td:2) → TestFromAC_ReadTaskCachedConfig.test_ac2_error_corrupt_task_config_yml_present_config_provided_raises
AC2 (td:2) → TestFromAC_ReadTaskCachedConfig.test_ac2_boundary_detection_runs_even_when_config_yml_absent
AC3 (td:1) → TestFromAC_ReadTaskCachedConfig.test_ac3_explicit_none_returns_task
AC3 (td:1) → TestFromAC_ReadTaskCachedConfig.test_ac3_explicit_none_calls_load_config
AC3 (td:2) → TestFromAC_ReadTaskCachedConfig.test_ac3_corrupt_task_config_yml_present_none_raises
AC3 (td:2) → TestFromAC_ReadTaskCachedConfig.test_ac3_corrupt_task_no_config_yml_config_none_returns_task
AC4 (td:1) → TestFromAC_ReadTaskCachedConfig.test_ac4_engine_all_call_sites_pass_config
AC4 (td:1) → TestFromAC_ReadTaskCachedConfig.test_ac4_engine_call_sites_value_is_self_config
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_STATUSES = ["research", "backlog", "todo", "in-progress", "review", "done"]
_PRIORITIES = ["someday", "nice-to-have", "important", "needed", "critical"]

_CONFIG_YAML = """\
schema: grouped
statuses:
  - research
  - backlog
  - todo
  - in-progress
  - review
  - done
priorities:
  - someday
  - nice-to-have
  - important
  - needed
  - critical
next_id: 2
paths:
    tasks_dir: tasks
    archive_dir: archive
pipeline:
    entry_status: research
    terminal_status: done
    wave_size: 4
    claim_timeout: 1h
agents:
    agent_map: {}
    agent_types: {}
    agent_compatibility: {}
policy:
    non_impl_tags: [research, docs]
    archival_reasons: [completed, deprecated, dropped, duplicate, wontfix]
    status_predicates: {}
"""

_VALID_TASK_YAML = """\
---
id: 1
title: Test Task
status: todo
priority: important
created: 2026-01-01 00:00:00+00:00
updated: 2026-01-01 00:00:00+00:00
tags: []
depends_on: []
blocked: false
---
"""

_CORRUPT_TASK_YAML = """\
---
id: 1
title: Corrupt Task
status: invalid-status
priority: important
created: 2026-01-01 00:00:00+00:00
updated: 2026-01-01 00:00:00+00:00
tags: []
depends_on: []
blocked: false
---
"""


def _make_config() -> BoardConfig:
    """Return an in-memory BoardConfig with standard statuses/priorities."""
    return BoardConfig(statuses=_STATUSES, priorities=_PRIORITIES, next_id=1)


def _make_board_with_task(tmp_path: Path) -> tuple[Path, Path]:
    """Create a board dir with config.yml and a valid task file.

    Returns (board_dir, task_path).
    """
    board_dir = tmp_path / "board"
    tasks_dir = board_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    (board_dir / "archive").mkdir()
    (board_dir / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
    task_path = tasks_dir / "1-test-task.md"
    task_path.write_text(_VALID_TASK_YAML, encoding="utf-8")
    return board_dir, task_path


def _make_task_no_config_yml(tmp_path: Path, *, corrupt: bool = False) -> Path:
    """Create a board dir WITHOUT config.yml, with a task file.

    Returns task_path. Used to test that config= param bypasses the
    config_path.exists() guard.
    """
    board_dir = tmp_path / "board_no_cfg"
    tasks_dir = board_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    (board_dir / "archive").mkdir()
    # Deliberately NO config.yml
    task_content = _CORRUPT_TASK_YAML if corrupt else _VALID_TASK_YAML
    task_path = tasks_dir / "1-test-task.md"
    task_path.write_text(task_content, encoding="utf-8")
    return task_path


# ---------------------------------------------------------------------------
# TestFromAC_ReadTaskCachedConfig
# ---------------------------------------------------------------------------


class TestFromAC_ReadTaskCachedConfig:
    """Tests for AC1-AC4: read_task optional cached-config parameter."""

    # ------------------------------------------------------------------
    # AC1 — read_task accepts keyword-only config=BoardConfig|None
    # ------------------------------------------------------------------

    def test_ac1_accepts_config_keyword_arg(self, tmp_path: Path) -> None:
        """AC1: read_task(path, config=...) must accept a BoardConfig without error."""
        _, task_path = _make_board_with_task(tmp_path)
        config = _make_config()
        # Will TypeError pre-impl: "got an unexpected keyword argument 'config'"
        task = read_task(task_path, config=config)
        assert task.id == 1

    def test_ac1_config_provided_skips_load_config_call(self, tmp_path: Path) -> None:
        """AC1: when config is provided, load_config must NOT be called."""
        _, task_path = _make_board_with_task(tmp_path)
        config = _make_config()
        with patch("owlbear_kanban.config_loader.load_config") as mock_load:
            # Will TypeError pre-impl before the assertion is reached
            read_task(task_path, config=config)
        mock_load.assert_not_called()

    def test_ac1_config_param_is_keyword_only(self, tmp_path: Path) -> None:
        """AC1: config= must be keyword-only — positional use raises TypeError."""
        _, task_path = _make_board_with_task(tmp_path)
        config = _make_config()
        # Post-impl: passing config positionally must raise TypeError.
        # Pre-impl: TypeError for unknown argument — still fails, different message.
        with pytest.raises(TypeError):
            read_task(task_path, config)  # type: ignore[call-arg]

        # After impl, calling with the keyword must NOT raise TypeError.
        # This assertion fails pre-impl because the line above raises TypeError
        # and does NOT advance past the raises block to reach this assertion.
        _ = read_task(task_path, config=config)  # Will TypeError pre-impl

    # ------------------------------------------------------------------
    # AC2 — when config provided, detection runs unconditionally
    # ------------------------------------------------------------------

    def test_ac2_happy_valid_task_no_config_yml_config_provided(
        self, tmp_path: Path
    ) -> None:
        """AC2: valid task + config provided + no config.yml → task returned cleanly."""
        task_path = _make_task_no_config_yml(tmp_path, corrupt=False)
        config = _make_config()
        # Without config= the function would skip detection (no config.yml).
        # With config= the function runs detection; valid task → returns successfully.
        task = read_task(task_path, config=config)  # TypeError pre-impl
        assert task.id == 1

    def test_ac2_edge_corrupt_task_no_config_yml_config_provided_raises(
        self, tmp_path: Path
    ) -> None:
        """AC2 edge: corrupt task + config provided + no config.yml → CorruptionError.

        The config.yml absence guard is skipped because config is pre-resolved.
        Detection runs unconditionally and must surface the corrupt status.
        """
        task_path = _make_task_no_config_yml(tmp_path, corrupt=True)
        config = _make_config()
        # Pre-impl: TypeError for unexpected config= kwarg
        # Post-impl: CorruptionError for invalid status
        with pytest.raises(CorruptionError) as exc_info:
            read_task(task_path, config=config)
        assert exc_info.value.code == ERR_CORRUPT_INVALID_STATUS

    def test_ac2_error_corrupt_task_config_yml_present_config_provided_raises(
        self, tmp_path: Path
    ) -> None:
        """AC2 error: corrupt task + config.yml present + config provided → CorruptionError."""
        board_dir, _ = _make_board_with_task(tmp_path)
        tasks_dir = board_dir / "tasks"
        corrupt_path = tasks_dir / "1-corrupt.md"
        corrupt_path.write_text(_CORRUPT_TASK_YAML, encoding="utf-8")
        config = _make_config()
        with pytest.raises(CorruptionError) as exc_info:
            read_task(corrupt_path, config=config)  # TypeError pre-impl
        assert exc_info.value.code == ERR_CORRUPT_INVALID_STATUS

    def test_ac2_boundary_detection_runs_even_when_config_yml_absent(
        self, tmp_path: Path
    ) -> None:
        """AC2 boundary: config.yml absent + config provided → CorruptionError, not silent skip.

        Without the guard bypass, missing config.yml would silently skip detection
        and return the (corrupt) task. With config provided, the guard is bypassed
        and detection runs unconditionally, raising CorruptionError.
        Pre-impl: TypeError (unexpected kwarg) — test fails.
        Post-impl: CorruptionError (invalid status surfaced without config.yml).
        """
        task_path = _make_task_no_config_yml(tmp_path, corrupt=True)
        config = _make_config()
        with pytest.raises(CorruptionError) as exc_info:
            read_task(task_path, config=config)
        assert exc_info.value.code == ERR_CORRUPT_INVALID_STATUS

    # ------------------------------------------------------------------
    # AC3 — config=None preserves existing behavior: guard + load_config
    # ------------------------------------------------------------------

    def test_ac3_explicit_none_returns_task(self, tmp_path: Path) -> None:
        """AC3: read_task(path, config=None) must return task identical to read_task(path)."""
        _, task_path = _make_board_with_task(tmp_path)
        # Pre-impl: TypeError for unknown kwarg config=None
        task = read_task(task_path, config=None)
        assert task.id == 1

    def test_ac3_explicit_none_calls_load_config(self, tmp_path: Path) -> None:
        """AC3: when config=None, load_config is still called from disk."""
        _, task_path = _make_board_with_task(tmp_path)
        with patch(
            "owlbear_kanban.config_loader.load_config", wraps=load_config
        ) as mock_load:
            # Pre-impl: TypeError before mock can capture the call
            read_task(task_path, config=None)
        mock_load.assert_called_once()

    # ------------------------------------------------------------------
    # AC3 (td:2 strengthened) — config=None: detection fires on corrupt input;
    # absent config.yml guard skips detection
    # ------------------------------------------------------------------

    def test_ac3_corrupt_task_config_yml_present_none_raises(
        self, tmp_path: Path
    ) -> None:
        """AC3 td:2: corrupt task + config.yml present + config=None → CorruptionError.

        Proves detect_corruption fires on corrupt input in the config=None path.
        Would silently pass if detection were removed from that branch.
        """
        board_dir, _ = _make_board_with_task(tmp_path)
        tasks_dir = board_dir / "tasks"
        corrupt_content = _CORRUPT_TASK_YAML.replace("id: 1", "id: 2")
        corrupt_path = tasks_dir / "2-corrupt.md"
        corrupt_path.write_text(corrupt_content, encoding="utf-8")
        with pytest.raises(CorruptionError) as exc_info:
            read_task(corrupt_path, config=None)
        assert exc_info.value.code == ERR_CORRUPT_INVALID_STATUS

    def test_ac3_corrupt_task_no_config_yml_config_none_returns_task(
        self, tmp_path: Path
    ) -> None:
        """AC3 td:2: corrupt task + no config.yml + config=None → task returned.

        Proves the config_path.exists() guard works: when config.yml is absent
        and config=None, corruption detection is skipped and the task is returned
        (even with an invalid status field).
        """
        task_path = _make_task_no_config_yml(tmp_path, corrupt=True)
        # config=None + no config.yml → guard fires, detection skipped → task returned
        task = read_task(task_path, config=None)
        assert task.id == 1

    # ------------------------------------------------------------------
    # AC4 — all engine.py call sites pass config=self._config
    # ------------------------------------------------------------------

    def test_ac4_engine_all_call_sites_pass_config(self) -> None:
        """AC4: every read_task() call in engine.py must include config= keyword arg."""
        engine_py = Path(__file__).parent.parent / "src/owlbear_kanban/engine.py"
        source = engine_py.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(engine_py))

        violations: list[int] = []
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "read_task"
            ):
                kwarg_names = [kw.arg for kw in node.keywords]
                if "config" not in kwarg_names:
                    violations.append(node.lineno)

        assert not violations, (
            f"read_task() calls in engine.py missing config= keyword argument "
            f"at lines: {violations}. All engine call sites must pass "
            f"config=self._config per AC4."
        )

    def test_ac4_engine_call_sites_value_is_self_config(self) -> None:
        """AC4 (strengthened): config= value at every engine.py call site must be
        self._config (Attribute access: Name('self')._config), not just a keyword.

        Catches cases like config=None or config=load_config(...) which would pass
        test_ac4_engine_all_call_sites_pass_config but violate the contract.
        """
        engine_py = Path(__file__).parent.parent / "src/owlbear_kanban/engine.py"
        source = engine_py.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(engine_py))

        violations: list[int] = []
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "read_task"
            ):
                for kw in node.keywords:
                    if kw.arg == "config":
                        val = kw.value
                        is_self_config = (
                            isinstance(val, ast.Attribute)
                            and val.attr == "_config"
                            and isinstance(val.value, ast.Name)
                            and val.value.id == "self"
                        )
                        if not is_self_config:
                            violations.append(node.lineno)

        assert not violations, (
            f"read_task() calls in engine.py have config= but value is not "
            f"self._config at lines: {violations}. Per AC4 the value must be "
            f"self._config (attribute access on self)."
        )


"""Tests for #1206: Remove storage.load_config wrapper / clean up double-validation.

AC coverage:
  AC1: storage.py no longer defines or exports load_config (td:1)
       — symbol absent from __all__, module attributes, and module docstring
  AC5: No double _validate_claim_timeout call in any load path (td:1)
       — config_loader.load_config invokes _validate_claim_timeout exactly once
"""


# ---------------------------------------------------------------------------
# Shared board fixture
# ---------------------------------------------------------------------------

_CONFIG_YAML = """\
statuses:
  - research
  - backlog
  - done
priorities:
  - someday
  - important
  - critical
entry_status: research
claim_timeout: 1h
next_id: 1
agent_map:
  research: []
  backlog: []
  done: []
"""


def _make_board(tmp_path: Path, config_yaml: str = _CONFIG_YAML) -> Path:
    kanban_dir = tmp_path / "board"
    kanban_dir.mkdir()
    (kanban_dir / "config.yml").write_text(config_yaml, encoding="utf-8")
    (kanban_dir / "tasks").mkdir()
    (kanban_dir / "archive").mkdir()
    return kanban_dir


# ---------------------------------------------------------------------------
# AC1: storage.py no longer defines or exports load_config
# ---------------------------------------------------------------------------


class TestFromAC_StorageDropsLoadConfig:
    """Verify load_config is fully removed from storage.py public surface (AC1)."""

    def test_load_config_absent_from_dunder_all(self) -> None:
        """load_config must not appear in owlbear_kanban.storage.__all__."""
        assert "load_config" not in storage_mod.__all__

    def test_load_config_not_an_attribute_on_storage_module(self) -> None:
        """storage module must not define a load_config attribute at all."""
        assert not hasattr(storage_mod, "load_config")

    def test_load_config_absent_from_module_docstring(self) -> None:
        """Module docstring (Public API section) must not list load_config."""
        docstring = storage_mod.__doc__ or ""
        assert "load_config" not in docstring


# ---------------------------------------------------------------------------
# AC5: No double _validate_claim_timeout call in any load path
# ---------------------------------------------------------------------------


class TestFromAC_NoDoubleValidation:
    """storage.py must not contain a redundant _validate_claim_timeout call (AC5).

    The double-call exists because storage.load_config re-invokes
    _validate_claim_timeout after delegating to config_loader.load_config.
    After the wrapper is removed, storage.py must not reference
    _validate_claim_timeout at all.
    """

    def test_storage_does_not_reference_validate_claim_timeout(self) -> None:
        """storage.py source must not contain _validate_claim_timeout (no re-call)."""
        import inspect

        source = inspect.getsource(storage_mod)
        assert "_validate_claim_timeout" not in source, (
            "storage.py still references _validate_claim_timeout — "
            "the double-validation wrapper has not been removed"
        )


# ---------------------------------------------------------------------------
# load_config defaults when config.yml is absent
# ---------------------------------------------------------------------------


class TestFromAC_LoadConfigDefaultsWhenMissing:
    """AC1 (topology-constant refactor): load_config() returns PRODUCT_TOPOLOGY-derived
    config and does not raise when config.yml is absent from kanban_dir.

    The reviewer identified that existing tests only cover the config=None path
    indirectly via read_task; this class provides direct load_config proof.
    """

    def _make_board_no_config(self, tmp_path: Path) -> Path:
        """Create kanban_dir with tasks/ and archive/ but without config.yml."""
        kanban_dir = tmp_path / "board"
        kanban_dir.mkdir(parents=True)
        (kanban_dir / "tasks").mkdir()
        (kanban_dir / "archive").mkdir()
        return kanban_dir

    def test_load_config_no_config_yml_does_not_raise(self, tmp_path: Path) -> None:
        """load_config(kanban_dir) must not raise when config.yml is absent."""
        kanban_dir = self._make_board_no_config(tmp_path)
        config_path = kanban_dir / "config.yml"
        assert not config_path.exists(), "Precondition: config.yml must be absent"

        cfg = load_config(kanban_dir)  # must not raise
        assert cfg is not None

    def test_load_config_no_config_yml_returns_product_statuses(
        self, tmp_path: Path
    ) -> None:
        """load_config() with no config.yml returns statuses from PRODUCT_TOPOLOGY."""
        from owlbear_kanban.topology import PRODUCT_TOPOLOGY  # noqa: PLC0415

        kanban_dir = self._make_board_no_config(tmp_path)
        cfg = load_config(kanban_dir)
        assert cfg.statuses == list(PRODUCT_TOPOLOGY.statuses), (
            f"Expected PRODUCT_TOPOLOGY statuses {list(PRODUCT_TOPOLOGY.statuses)!r}; "
            f"got {cfg.statuses!r}"
        )

    def test_load_config_no_config_yml_returns_product_entry_status(
        self, tmp_path: Path
    ) -> None:
        """load_config() with no config.yml returns pipeline.entry_status from PRODUCT_TOPOLOGY."""
        from owlbear_kanban.topology import PRODUCT_TOPOLOGY  # noqa: PLC0415

        kanban_dir = self._make_board_no_config(tmp_path)
        cfg = load_config(kanban_dir)
        assert cfg.pipeline.entry_status == PRODUCT_TOPOLOGY.entry_status, (
            f"Expected entry_status={PRODUCT_TOPOLOGY.entry_status!r}; "
            f"got {cfg.pipeline.entry_status!r}"
        )

    def test_load_config_no_config_yml_next_id_defaults_to_one(
        self, tmp_path: Path
    ) -> None:
        """load_config() with no config.yml defaults next_id to 1."""
        kanban_dir = self._make_board_no_config(tmp_path)
        cfg = load_config(kanban_dir)
        assert cfg.next_id == 1, (
            f"Expected next_id=1 when config.yml is absent; got {cfg.next_id!r}"
        )


# --- merged from serve/kanban/tests/test_storage_frontmatter.py ---
_CANONICAL_FIELD_ORDER: list[str] = [
    "id",
    "title",
    "status",
    "priority",
    "created",
    "updated",
    "tags",
    "parent",
    "depends_on",
    "blocked",
    "block_reason",
    "claimed_at",
    "archival_reason",
    "archival_refs",
]

_NEW_SCHEMA_CONFIG_YAML = """\
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


def _minimal_task(task_id: int = 1) -> Task:
    """Return a minimal valid Task with explicit UTC timestamps."""
    return Task(
        id=task_id,
        title="Test task",
        status="todo",
        priority="important",
        created="2026-04-20T10:00:00+00:00",
        updated="2026-04-20T10:00:00+00:00",
    )


def _write_claimed_by_file(directory: Path, task_id: int = 1) -> Path:
    """Write a task file containing the forbidden claimed_by field into *directory*."""
    path = directory / f"{task_id}-test.md"
    content = (
        "---\n"
        f"id: {task_id}\n"
        'title: "Test"\n'
        "status: todo\n"
        "priority: important\n"
        "created: 2026-04-20T10:00:00+00:00\n"
        "updated: 2026-04-20T10:00:00+00:00\n"
        "tags: []\n"
        "parent:\n"
        "depends_on: []\n"
        "blocked: false\n"
        "block_reason:\n"
        "claimed_by: some-agent\n"
        "claimed_at:\n"
        "---\n"
    )
    path.write_text(content, encoding="utf-8")
    return path


def _extract_frontmatter_keys(path: Path) -> list[str]:
    """Parse a task file and return the ordered list of frontmatter keys."""
    content = path.read_text(encoding="utf-8")
    assert content.startswith("---\n"), f"Missing opening --- in {path}"
    closing_idx = content.index("---\n", 4)
    frontmatter = content[4:closing_idx]
    return [
        line.split(":")[0].strip()
        for line in frontmatter.splitlines()
        if ":" in line and not line.startswith(" ")
    ]


class TestFromAC_CorruptionDetection:
    """AC-C16: detect_corruption identifies claimed_by as mode-3 corruption in tasks/."""

    def test_detect_corruption_claimed_by_in_tasks_dir(self, tmp_path: Path) -> None:
        """AC-C16: File in tasks/ with claimed_by → CorruptionError mode 3."""
        kanban_dir = _make_board(tmp_path)
        config = load_config(kanban_dir)
        path = _write_claimed_by_file(kanban_dir / "tasks", task_id=1)

        error = detect_corruption(path, config)

        assert error is not None
        assert error.code == "ERR_CORRUPT_MISSING_FIELD"

    def test_detect_corruption_claimed_by_detail_exact_string(
        self, tmp_path: Path
    ) -> None:
        """AC-C16: detail attribute is exactly 'forbidden field claimed_by present'."""
        kanban_dir = _make_board(tmp_path)
        config = load_config(kanban_dir)
        path = _write_claimed_by_file(kanban_dir / "tasks", task_id=1)

        error = detect_corruption(path, config)

        assert error is not None
        assert error.detail == "forbidden field claimed_by present"

    def test_detect_corruption_clean_task_returns_none(self, tmp_path: Path) -> None:
        """AC-C16 contrast: Clean task file returns None from detect_corruption."""
        kanban_dir = _make_board(tmp_path)
        config = load_config(kanban_dir)
        task = _minimal_task(1)
        write_task(task, kanban_dir)

        files = list((kanban_dir / "tasks").glob("*.md"))
        assert len(files) == 1

        result = detect_corruption(files[0], config)
        assert result is None

    def test_detect_corruption_archive_file_with_claimed_by_returns_none(
        self, tmp_path: Path
    ) -> None:
        """AC-C16 / AC-C48: claimed_by in archive/ is NOT flagged as corruption."""
        kanban_dir = _make_board(tmp_path)
        config = load_config(kanban_dir)
        archive_path = _write_claimed_by_file(kanban_dir / "archive", task_id=5)

        error = detect_corruption(archive_path, config)

        # Archive files are exempt from claimed_by corruption rule
        assert error is None


class TestFromAC_QuarantineRepair:
    """AC-C30: repair_storage() AR task has type:user-action tag and ## Quarantined file body."""

    def test_repair_storage_ar_task_has_type_user_action_tag(
        self, tmp_path: Path
    ) -> None:
        """AC-C30: AR task created by repair_storage() carries tag type:user-action."""
        from owlbear_kanban import KanbanEngine

        kanban_dir = _make_board(tmp_path)
        # Use a file with missing required fields (ERR_CORRUPT_MISSING_FIELD) — not
        # claimed_by, which would trigger MigrationRequiredError at engine init.
        corrupt_file = kanban_dir / "tasks" / "1-test.md"
        corrupt_file.write_text(
            "---\nid: 1\ntitle: test task\n---\n\nBody.\n", encoding="utf-8"
        )

        engine = KanbanEngine(kanban_dir=kanban_dir)
        engine.repair_storage()

        ar_tasks = [
            engine.show_task(task_id=t.id)
            for t in engine.list_tasks()
            if "type:user-action" in (t.tags or [])
        ]
        assert len(ar_tasks) >= 1
        for ar_task in ar_tasks:
            assert "type:user-action" in ar_task.tags

    def test_repair_storage_ar_body_contains_quarantined_file_section(
        self, tmp_path: Path
    ) -> None:
        """AC-C30: AR task body contains a ## Quarantined file section."""
        from owlbear_kanban import KanbanEngine

        kanban_dir = _make_board(tmp_path)
        corrupt_file = kanban_dir / "tasks" / "1-test.md"
        corrupt_file.write_text(
            "---\nid: 1\ntitle: test task\n---\n\nBody.\n", encoding="utf-8"
        )

        engine = KanbanEngine(kanban_dir=kanban_dir)
        engine.repair_storage()

        ar_tasks = [
            engine.show_task(task_id=t.id)
            for t in engine.list_tasks()
            if "type:user-action" in (t.tags or [])
        ]
        assert len(ar_tasks) >= 1
        for ar_task in ar_tasks:
            assert "## Quarantined file" in ar_task.body

    def test_repair_storage_ar_body_has_code_path_detail_fields(
        self, tmp_path: Path
    ) -> None:
        """AC-C30: AR body ## Quarantined file section contains code, path, and detail."""
        from owlbear_kanban import KanbanEngine

        kanban_dir = _make_board(tmp_path)
        corrupt_file = kanban_dir / "tasks" / "1-test.md"
        corrupt_file.write_text(
            "---\nid: 1\ntitle: test task\n---\n\nBody.\n", encoding="utf-8"
        )

        engine = KanbanEngine(kanban_dir=kanban_dir)
        engine.repair_storage()

        ar_tasks = [
            engine.show_task(task_id=t.id)
            for t in engine.list_tasks()
            if "type:user-action" in (t.tags or [])
        ]
        assert len(ar_tasks) >= 1
        body = ar_tasks[0].body

        expected_quarantine_path = str(kanban_dir / "quarantine" / "1-test.md")
        assert "ERR_CORRUPT_MISSING_FIELD" in body, (
            f"Expected error code not found in AR body:\n{body}"
        )
        assert expected_quarantine_path in body, (
            f"Expected quarantine path not found in AR body:\n{body}"
        )
        assert f"quarantined to {expected_quarantine_path}" in body, (
            f"Expected detail value not found in AR body:\n{body}"
        )


class TestFromAC_ArchiveExemption:
    """AC-C48: Archive files with claimed_by read successfully; field silently stripped."""

    def test_archive_file_with_claimed_by_reads_without_exception(
        self, tmp_path: Path
    ) -> None:
        """AC-C48: No CorruptionError when reading archive file containing claimed_by."""
        kanban_dir = _make_board(tmp_path)
        archive_path = _write_claimed_by_file(kanban_dir / "archive", task_id=5)

        task = read_task(archive_path)

        assert task is not None
        assert task.id == 5

    def test_archive_claimed_by_stripped_from_returned_task(
        self, tmp_path: Path
    ) -> None:
        """AC-C48: claimed_by is absent (or None) in the Task returned from archive read."""
        kanban_dir = _make_board(tmp_path)
        archive_path = _write_claimed_by_file(kanban_dir / "archive", task_id=5)

        task = read_task(archive_path)
        dumped = task.model_dump()

        assert dumped.get("claimed_by") is None

    def test_archive_claimed_by_does_not_raise_corruption_error(
        self, tmp_path: Path
    ) -> None:
        """AC-C48: Reading archive file with claimed_by does NOT raise CorruptionError."""
        kanban_dir = _make_board(tmp_path)
        archive_path = _write_claimed_by_file(kanban_dir / "archive", task_id=5)

        # Must complete without raising CorruptionError
        try:
            task = read_task(archive_path)
        except CorruptionError:
            pytest.fail("CorruptionError raised for archive file with claimed_by")

        assert task is not None

    def test_engine_init_with_archive_claimed_by_no_migration_error(
        self, tmp_path: Path
    ) -> None:
        """AC-C48: KanbanEngine.__init__ does NOT raise MigrationRequiredError for archive files.

        Uses a new-schema board (no 'version' field) so the migration gate at
        engine.py:314 is active.  tasks/ is clean; archive/ has claimed_by.
        The gate must not fire for archive-only legacy fields.
        """
        from owlbear_kanban import KanbanEngine

        # New-schema board: gate is active (legacy boards bypass it entirely)
        kanban_dir = tmp_path / "board"
        kanban_dir.mkdir(parents=True)
        (kanban_dir / "config.yml").write_text(
            _NEW_SCHEMA_CONFIG_YAML, encoding="utf-8"
        )
        (kanban_dir / "tasks").mkdir()
        (kanban_dir / "archive").mkdir()
        # Only archive/ has claimed_by — tasks/ is intentionally clean
        _write_claimed_by_file(kanban_dir / "archive", task_id=5)

        # Must not raise MigrationRequiredError even though gate is active
        try:
            engine = KanbanEngine(kanban_dir=kanban_dir)
        except MigrationRequiredError:
            pytest.fail(
                "MigrationRequiredError raised for engine init with claimed_by only in archive/"
            )

        assert engine is not None

    def test_archive_vendor_fields_preserved_when_claimed_by_stripped(
        self, tmp_path: Path
    ) -> None:
        """AC-C48 edge: Stripping claimed_by does not affect other vendor extra fields."""
        kanban_dir = _make_board(tmp_path)
        archive_path = kanban_dir / "archive" / "5-vendor.md"
        content = (
            "---\n"
            "id: 5\n"
            'title: "Vendor"\n'
            "status: done\n"
            "priority: important\n"
            "created: 2026-04-20T10:00:00+00:00\n"
            "updated: 2026-04-20T10:00:00+00:00\n"
            "tags: []\n"
            "claimed_by: old-agent\n"
            "class: epic\n"
            "---\n"
        )
        archive_path.write_text(content, encoding="utf-8")

        task = read_task(archive_path)
        dumped = task.model_dump()

        assert dumped.get("claimed_by") is None, "claimed_by must be stripped"
        assert dumped.get("class") == "epic", "vendor field 'class' must be preserved"


class TestBuilderDiscovered:
    """Edge cases discovered during implementation; complementary to TestFromAC_* coverage."""

    def test_migration_required_error_carries_code_and_user_message(self) -> None:
        """MigrationRequiredError stores code and user_message on the instance."""
        err = MigrationRequiredError(
            code="ERR_MIGRATION_REQUIRED",
            user_message="board requires migration",
        )
        assert err.code == "ERR_MIGRATION_REQUIRED"
        assert err.user_message == "board requires migration"
        assert str(err) == "board requires migration"

    def test_normalize_timestamp_none_returns_none(self) -> None:
        """_normalize_timestamp returns None when the input timestamp is None."""
        from owlbear_kanban.storage import _normalize_timestamp

        assert _normalize_timestamp(None) is None

    def test_read_task_missing_field_maps_to_missing_field_error(
        self, tmp_path: Path
    ) -> None:
        """read_task maps missing required fields to ERR_CORRUPT_MISSING_FIELD."""
        kanban_dir = _make_board(tmp_path)
        bad_file = kanban_dir / "tasks" / "501-missing-updated.md"
        bad_file.write_text(
            "---\n"
            "id: 501\n"
            "title: Missing updated\n"
            "status: todo\n"
            "priority: important\n"
            "created: 2026-04-20T10:00:00+00:00\n"
            "---\n",
            encoding="utf-8",
        )

        with pytest.raises(CorruptionError) as exc_info:
            read_task(bad_file)

        assert exc_info.value.code == "ERR_CORRUPT_MISSING_FIELD"

    def test_read_task_type_mismatch_maps_to_type_mismatch_error(
        self, tmp_path: Path
    ) -> None:
        """read_task maps type errors to ERR_CORRUPT_TYPE_MISMATCH."""
        kanban_dir = _make_board(tmp_path)
        bad_file = kanban_dir / "tasks" / "502-bad-id-type.md"
        bad_file.write_text(
            "---\n"
            "id: not-an-int\n"
            "title: Bad id type\n"
            "status: todo\n"
            "priority: important\n"
            "created: 2026-04-20T10:00:00+00:00\n"
            "updated: 2026-04-20T10:00:00+00:00\n"
            "---\n",
            encoding="utf-8",
        )

        with pytest.raises(CorruptionError) as exc_info:
            read_task(bad_file)

        assert exc_info.value.code == "ERR_CORRUPT_TYPE_MISMATCH"

    def test_read_task_missing_delimiters_maps_to_delimiters_error(
        self, tmp_path: Path
    ) -> None:
        """read_task maps delimiter errors to ERR_CORRUPT_DELIMITERS."""
        kanban_dir = _make_board(tmp_path)
        bad_file = kanban_dir / "tasks" / "503-no-delimiters.md"
        bad_file.write_text("id: 503\ntitle: no delimiters\n", encoding="utf-8")

        with pytest.raises(CorruptionError) as exc_info:
            read_task(bad_file)

        assert exc_info.value.code == "ERR_CORRUPT_DELIMITERS"

    def test_detect_corruption_file_missing_closing_delimiter_returns_error(
        self, tmp_path: Path
    ) -> None:
        """detect_corruption on a file missing the closing '---' returns ERR_CORRUPT_DELIMITERS."""
        kanban_dir = _make_board(tmp_path)
        config = load_config(kanban_dir)
        bad_file = kanban_dir / "tasks" / "99-no-close.md"
        bad_file.write_text(
            "---\nid: 99\ntitle: broken\nclaimed_by: agent\n", encoding="utf-8"
        )

        result = detect_corruption(bad_file, config)

        assert result is not None
        assert result.code == "ERR_CORRUPT_DELIMITERS"

    def test_detect_corruption_file_without_frontmatter_returns_error(
        self, tmp_path: Path
    ) -> None:
        """detect_corruption on a plain-text file (no '---') returns ERR_CORRUPT_DELIMITERS."""
        kanban_dir = _make_board(tmp_path)
        config = load_config(kanban_dir)
        plain_file = kanban_dir / "tasks" / "99-plain.md"
        plain_file.write_text("Just some text\nclaimed_by: agent\n", encoding="utf-8")

        result = detect_corruption(plain_file, config)

        assert result is not None
        assert result.code == "ERR_CORRUPT_DELIMITERS"

    def test_save_config_round_trip(self, tmp_path: Path) -> None:
        """save_config writes a valid config that can be reloaded."""
        from owlbear_kanban.storage import save_config

        kanban_dir = _make_board(tmp_path)
        config = load_config(kanban_dir)
        config.next_id = 9999
        save_config(config, kanban_dir)
        reloaded = load_config(kanban_dir)
        assert reloaded.next_id == 9999

    def test_write_task_reuses_existing_filename_for_same_id(
        self, tmp_path: Path
    ) -> None:
        """write_task keeps filename stable when a file for the same ID already exists."""
        kanban_dir = _make_board(tmp_path)
        original = Task(
            id=55,
            title="Original title",
            status="todo",
            priority="important",
            created="2026-04-20T10:00:00+00:00",
            updated="2026-04-20T10:00:00+00:00",
        )
        first_path = write_task(original, kanban_dir)

        updated = original.model_copy(deep=True)
        updated.title = "New title"
        updated.updated = "2026-04-20T10:05:00+00:00"
        second_path = write_task(updated, kanban_dir)

        assert second_path == first_path

    def test_move_to_archive_moves_file(self, tmp_path: Path) -> None:
        """move_to_archive moves a task file from tasks/ to archive/."""
        from owlbear_kanban.storage import move_to_archive

        kanban_dir = _make_board(tmp_path)
        task = _minimal_task(42)
        write_task(task, kanban_dir)
        dest = move_to_archive(42, kanban_dir)
        assert dest.parent.name == "archive"
        assert not (kanban_dir / "tasks" / dest.name).exists()

    def test_move_to_archive_missing_task_raises_file_not_found(
        self, tmp_path: Path
    ) -> None:
        """move_to_archive raises FileNotFoundError when task file does not exist."""
        from owlbear_kanban.storage import move_to_archive

        kanban_dir = _make_board(tmp_path)

        with pytest.raises(FileNotFoundError):
            move_to_archive(9999, kanban_dir)

    def test_write_task_if_unchanged_writes_when_timestamp_matches(
        self, tmp_path: Path
    ) -> None:
        """write_task_if_unchanged writes successfully when expected_updated matches disk."""
        from owlbear_kanban.storage import write_task_if_unchanged

        kanban_dir = _make_board(tmp_path)
        task = _minimal_task(88)
        path = write_task(task, kanban_dir)
        current = read_task(path)

        updated = current.model_copy(deep=True)
        updated.title = "OCC updated"
        updated.updated = "2026-04-20T11:00:00+00:00"

        written_path = write_task_if_unchanged(
            updated,
            expected_updated=current.updated,
            kanban_dir=kanban_dir,
        )

        assert written_path.exists()
        assert read_task(written_path).title == "OCC updated"

    def test_write_task_if_unchanged_raises_stale_on_timestamp_mismatch(
        self, tmp_path: Path
    ) -> None:
        """write_task_if_unchanged raises ERR_STALE on optimistic-concurrency mismatch."""
        from owlbear_kanban.storage import ConcurrencyError, write_task_if_unchanged

        kanban_dir = _make_board(tmp_path)
        task = _minimal_task(89)
        path = write_task(task, kanban_dir)
        current = read_task(path)

        updated = current.model_copy(deep=True)
        updated.title = "Should fail"
        updated.updated = "2026-04-20T12:00:00+00:00"

        with pytest.raises(ConcurrencyError) as exc_info:
            write_task_if_unchanged(
                updated,
                expected_updated="2020-01-01T00:00:00+00:00",
                kanban_dir=kanban_dir,
            )

        assert exc_info.value.code == "ERR_STALE"

    def test_write_task_if_unchanged_raises_file_not_found_when_missing(
        self, tmp_path: Path
    ) -> None:
        """write_task_if_unchanged raises FileNotFoundError for missing task files."""
        from owlbear_kanban.storage import write_task_if_unchanged

        kanban_dir = _make_board(tmp_path)
        missing_task = _minimal_task(777)

        with pytest.raises(FileNotFoundError):
            write_task_if_unchanged(
                missing_task,
                expected_updated=missing_task.updated,
                kanban_dir=kanban_dir,
            )

    def test_list_task_files_returns_only_visible_markdown_files(
        self, tmp_path: Path
    ) -> None:
        """list_task_files includes only visible .md files and excludes temp/hidden files."""
        from owlbear_kanban.storage import list_task_files

        kanban_dir = _make_board(tmp_path)
        task = _minimal_task(901)
        written = write_task(task, kanban_dir)
        (kanban_dir / "tasks" / ".tmp-scratch.md").write_text("tmp", encoding="utf-8")
        (kanban_dir / "tasks" / ".hidden.md").write_text("hidden", encoding="utf-8")
        (kanban_dir / "tasks" / "note.txt").write_text("note", encoding="utf-8")

        files = list_task_files(kanban_dir)

        assert [p.name for p in files] == [written.name]

    def test_list_task_files_returns_empty_when_tasks_dir_missing(
        self, tmp_path: Path
    ) -> None:
        """list_task_files returns [] when the configured tasks directory is absent."""
        from owlbear_kanban.storage import list_task_files

        kanban_dir = _make_board(tmp_path)
        (kanban_dir / "tasks").rmdir()

        assert list_task_files(kanban_dir) == []

    def test_list_archive_files_returns_only_visible_markdown_files(
        self, tmp_path: Path
    ) -> None:
        """list_archive_files includes only visible .md files and excludes temp/hidden files."""
        from owlbear_kanban.storage import list_archive_files

        kanban_dir = _make_board(tmp_path)
        kept = _write_claimed_by_file(kanban_dir / "archive", task_id=902)
        (kanban_dir / "archive" / ".tmp-scratch.md").write_text("tmp", encoding="utf-8")
        (kanban_dir / "archive" / ".hidden.md").write_text("hidden", encoding="utf-8")
        (kanban_dir / "archive" / "note.txt").write_text("note", encoding="utf-8")

        files = list_archive_files(kanban_dir)

        assert [p.name for p in files] == [kept.name]

    def test_list_archive_files_returns_empty_when_archive_dir_missing(
        self, tmp_path: Path
    ) -> None:
        """list_archive_files returns [] when the configured archive directory is absent."""
        from owlbear_kanban.storage import list_archive_files

        kanban_dir = _make_board(tmp_path)
        (kanban_dir / "archive").rmdir()

        assert list_archive_files(kanban_dir) == []

    def test_allocate_next_id_returns_current_and_persists_increment(
        self, tmp_path: Path
    ) -> None:
        """Scan-based allocate_next_id returns 1 on empty board; config.next_id unchanged."""
        from owlbear_kanban.storage import allocate_next_id

        kanban_dir = _make_board(tmp_path)
        before = load_config(kanban_dir).next_id

        allocated = allocate_next_id(kanban_dir)
        after = load_config(kanban_dir).next_id

        assert allocated == 1
        assert after == before

    def test_normalize_timestamp_already_has_tz(self) -> None:
        """_normalize_timestamp converts non-UTC offset to UTC per AC-C15 / Brief C §5.3."""
        from owlbear_kanban.storage import _normalize_timestamp

        # +02:00 input → UTC equivalent 08:00+00:00
        assert (
            _normalize_timestamp("2026-04-20T10:00:00+02:00")
            == "2026-04-20T08:00:00+00:00"
        )

    def test_normalize_timestamp_z_suffix_is_normalized_to_explicit_utc(self) -> None:
        """_normalize_timestamp rewrites Z-suffix timestamps to +00:00."""
        from owlbear_kanban.storage import _normalize_timestamp

        assert (
            _normalize_timestamp("2026-04-20T10:00:00Z") == "2026-04-20T10:00:00+00:00"
        )

    def test_normalize_timestamp_non_matching_format(self) -> None:
        """_normalize_timestamp returns ts unchanged when regex does not match."""
        from owlbear_kanban.storage import _normalize_timestamp

        ts = "not-a-timestamp"
        assert _normalize_timestamp(ts) == ts

    def test_attempt_repair_mode9_invalid_priority_auto_fixes(
        self, tmp_path: Path
    ) -> None:
        """attempt_repair for ERR_CORRUPT_INVALID_PRIORITY coerces priority to first configured."""
        from owlbear_kanban.corruption import (
            attempt_repair,
            ERR_CORRUPT_INVALID_PRIORITY,
        )

        kanban_dir = _make_board(tmp_path)
        config = load_config(kanban_dir)
        bad_file = kanban_dir / "tasks" / "1001-bad-priority.md"
        bad_file.write_text(
            "---\nid: 1001\ntitle: bad priority\nstatus: todo\npriority: invalid-prio\n"
            "created: 2026-01-01T00:00:00+00:00\nupdated: 2026-01-01T00:00:00+00:00\n---\n",
            encoding="utf-8",
        )
        outcome = attempt_repair(bad_file, ERR_CORRUPT_INVALID_PRIORITY, config)
        assert outcome.action == "fixed"

    def test_attempt_repair_mode6_id_filename_mismatch_renames(
        self, tmp_path: Path
    ) -> None:
        """attempt_repair for ERR_CORRUPT_ID_FILENAME_MISMATCH renames the file."""
        from owlbear_kanban.corruption import (
            attempt_repair,
            ERR_CORRUPT_ID_FILENAME_MISMATCH,
        )

        kanban_dir = _make_board(tmp_path)
        config = load_config(kanban_dir)
        bad_file = kanban_dir / "tasks" / "1001-wrong-name.md"
        bad_file.write_text(
            "---\nid: 1002\ntitle: mismatch\nstatus: todo\npriority: important\n"
            "created: 2026-01-01T00:00:00+00:00\nupdated: 2026-01-01T00:00:00+00:00\n---\n",
            encoding="utf-8",
        )
        outcome = attempt_repair(bad_file, ERR_CORRUPT_ID_FILENAME_MISMATCH, config)
        assert outcome.action == "fixed"
        assert not bad_file.exists()

    def test_engine_list_tasks_archived_strips_legacy_claimed_by(
        self, tmp_path: Path
    ) -> None:
        """Archived list summaries should not surface legacy claimed_by as claimed=True."""
        from owlbear_kanban import KanbanEngine

        kanban_dir = _make_board(tmp_path)
        _write_claimed_by_file(kanban_dir / "archive", task_id=77)

        engine = KanbanEngine(kanban_dir=kanban_dir)
        archived = {task.id: task for task in engine.list_tasks(archived=True)}

        assert 77 in archived
        assert archived[77].claimed is False


class TestFromAC_ClaimListRegression:
    """AC-REGR: list_tasks() must not silently drop actively-claimed tasks.

    Regression: claim_task() writes claimed_by to disk (via task_io.write_task
    which preserves the field).  list_tasks() detects a cache miss on the new
    mtime, calls detect_corruption(), receives a mode-3 CorruptionError for the
    claimed_by field, and silently skips the file.  Net effect: every task
    disappears from list_tasks() immediately after start_work().
    """

    def _make_new_schema_board(self, tmp_path: Path, task_id: int = 1) -> Path:
        """Return a new-schema board with one clean task in tasks/."""
        kanban_dir = tmp_path / "board"
        kanban_dir.mkdir(parents=True)
        (kanban_dir / "config.yml").write_text(
            _NEW_SCHEMA_CONFIG_YAML, encoding="utf-8"
        )
        (kanban_dir / "tasks").mkdir()
        (kanban_dir / "archive").mkdir()
        write_task(_minimal_task(task_id), kanban_dir)
        return kanban_dir

    def test_claimed_task_remains_in_list_tasks_same_engine(
        self, tmp_path: Path
    ) -> None:
        """AC-REGR: claim_task() then list_tasks() on same engine — task must be visible."""
        from owlbear_kanban import KanbanEngine

        kanban_dir = self._make_new_schema_board(tmp_path, task_id=1)
        engine = KanbanEngine(kanban_dir=kanban_dir)
        engine.claim_task("1")

        task_ids = {t.id for t in engine.list_tasks()}

        assert 1 in task_ids, (
            "Claimed task must appear in list_tasks() after claim_task()"
        )

    def test_claimed_task_remains_in_list_tasks_after_cache_miss(
        self, tmp_path: Path
    ) -> None:
        """AC-REGR: Warm cache, then claim_task() triggers mtime change — task must survive cache miss.

        Flow: list_tasks() (warms cache) → claim_task() (file mtime changes)
        → list_tasks() (cache miss: detect_corruption runs) — task must still appear.
        """
        from owlbear_kanban import KanbanEngine

        kanban_dir = self._make_new_schema_board(tmp_path, task_id=2)
        engine = KanbanEngine(kanban_dir=kanban_dir)

        # Warm the cache so next call exercises the cache-miss path
        engine.list_tasks()

        # claim_task writes claimed_by to disk → new mtime → cache miss on next list_tasks
        engine.claim_task("2")

        task_ids = {t.id for t in engine.list_tasks()}

        assert 2 in task_ids, (
            "Claimed task must appear in list_tasks() after cache miss"
        )

    def test_start_work_then_list_tasks_includes_task(self, tmp_path: Path) -> None:
        """AC-REGR: start_work() is the public API for claiming — task must stay in list."""
        from owlbear_kanban import KanbanEngine

        kanban_dir = self._make_new_schema_board(tmp_path, task_id=3)
        engine = KanbanEngine(kanban_dir=kanban_dir)
        engine.start_work("3")

        task_ids = {t.id for t in engine.list_tasks()}

        assert 3 in task_ids, (
            "Task claimed via start_work() must appear in list_tasks()"
        )


class TestFromAC_SaveConfigPersistsOnlyNextId:
    """AC1 (topology-constant refactor): save_config() writes only next_id to config.yml.

    The reviewer identified that the existing round-trip test only proves next_id
    survives; it does not prove topology fields are absent from the written file.
    These tests provide direct evidence of the next_id-only persistence contract.
    """

    def test_save_config_config_yml_contains_only_next_id_key(
        self, tmp_path: Path
    ) -> None:
        """config.yml after save_config() has exactly one top-level key: next_id.

        Proves topology sections (statuses, priorities, pipeline, agents, policy)
        are not written to disk.
        """
        import re  # noqa: PLC0415

        from owlbear_kanban.storage import save_config  # noqa: PLC0415

        kanban_dir = _make_board(tmp_path)
        config = load_config(kanban_dir)
        config.next_id = 42
        save_config(config, kanban_dir)

        raw = (kanban_dir / "config.yml").read_text(encoding="utf-8")
        # Extract top-level YAML keys (lines that start at column 0).
        top_level_keys = re.findall(r"^([a-z_][a-z0-9_]*):", raw, re.MULTILINE)
        assert top_level_keys == ["next_id"], (
            f"config.yml must contain only 'next_id'; found keys: {top_level_keys!r}"
        )

    def test_save_config_omits_topology_sections(self, tmp_path: Path) -> None:
        """config.yml after save_config() does not contain topology section keys.

        Checks that 'statuses', 'priorities', 'pipeline', 'agents', and 'policy'
        are absent from the written file.
        """
        from owlbear_kanban.storage import save_config  # noqa: PLC0415

        kanban_dir = _make_board(tmp_path)
        config = load_config(kanban_dir)
        save_config(config, kanban_dir)

        raw = (kanban_dir / "config.yml").read_text(encoding="utf-8")
        for key in ("statuses", "priorities", "pipeline", "agents", "policy"):
            assert key not in raw, (
                f"Topology key '{key}' must not appear in config.yml after save_config(); "
                f"content:\n{raw}"
            )

    def test_save_config_preserves_next_id_value(self, tmp_path: Path) -> None:
        """config.yml after save_config(next_id=777) reads back as 777 via load_config."""
        from owlbear_kanban.storage import save_config  # noqa: PLC0415

        kanban_dir = _make_board(tmp_path)
        config = load_config(kanban_dir)
        config.next_id = 777
        save_config(config, kanban_dir)

        reloaded = load_config(kanban_dir)
        assert reloaded.next_id == 777, (
            f"Expected next_id=777 after save_config; got {reloaded.next_id!r}"
        )


# --- merged from serve/kanban/tests/test_storage_imports.py ---
_KANBAN_SRC = Path(__file__).parent.parent / "src" / "owlbear_kanban"


def _read_source(filename: str) -> str:
    """Return source text of *filename* from the owlbear_kanban package."""
    return (_KANBAN_SRC / filename).read_text(encoding="utf-8")


class TestFromAC_TaskIoRemoved:
    """task_io.py must be deleted; the module must not be importable."""

    def test_task_io_py_does_not_exist_on_disk(self) -> None:
        """task_io.py file must not exist in the owlbear_kanban source directory."""
        task_io_path = _KANBAN_SRC / "task_io.py"
        assert not task_io_path.exists(), (
            f"task_io.py still present at {task_io_path}; "
            "it must be deleted per AC: task_io.py removed"
        )

    def test_storage_module_is_importable(self) -> None:
        """Importing owlbear_kanban.storage must succeed."""
        sys.modules.pop("owlbear_kanban.storage", None)
        module = importlib.import_module("owlbear_kanban.storage")
        assert module is not None

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


class TestFromAC_StorageClean:
    """storage.py must not reference task_io in its source (all logic inlined)."""

    def test_storage_py_has_no_task_io_import(self) -> None:
        """storage.py source must not contain 'task_io'."""
        source = _read_source("storage.py")
        assert "task_io" not in source, (
            "storage.py still imports from task_io; "
            "it must be self-contained per AC: all imports redirected to storage"
        )


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


class TestFromAC_DispatchRedirected:
    """dispatch.py must not import task_io and must avoid direct storage imports."""

    def test_dispatch_py_has_no_task_io_import(self) -> None:
        """dispatch.py source must not contain 'task_io'."""
        source = _read_source("dispatch.py")
        assert "task_io" not in source, (
            "dispatch.py still imports from task_io; "
            "redirect to owlbear_kanban.storage per AC"
        )

    def test_dispatch_imports_read_task_from_storage(self) -> None:
        """dispatch.py must avoid direct storage imports while still resolving reads."""
        source = _read_source("dispatch.py")
        assert "owlbear_kanban.storage" not in source, (
            "dispatch.py must not import from owlbear_kanban.storage directly; "
            "only engine.py may import storage"
        )
        assert "show_task" in source, "dispatch.py must resolve reads via engine"


class TestFromAC_CorruptionRedirected:
    """corruption.py must not import from task_io (lazy or otherwise)."""

    def test_corruption_py_has_no_task_io_import(self) -> None:
        """corruption.py source must not contain 'task_io'."""
        source = _read_source("corruption.py")
        assert "task_io" not in source, (
            "corruption.py still imports from task_io; "
            "redirect to owlbear_kanban.storage per AC"
        )


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
        assert "+00:00" in released_at_line, (
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
