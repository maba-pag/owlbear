"""Tests for C-05: storage surface — AC-C13, C-14, C-15, C-16, C-28, C-29, C-30, C-48.

Module: serve/kanban/tests/test_storage_1050.py
Target: owlbear_kanban.storage (new module — all tests fail in RED phase via ImportError)

AC coverage:
  AC-C13: Written frontmatter follows C8.6 canonical order.
  AC-C14: Pydantic Task model has extra="allow" (vendor archive fields survive).
  AC-C15: All timestamps written are ISO-8601 UTC with explicit +00:00.
  AC-C16: detect_corruption on tasks/ file with claimed_by reports mode 3
           with detail="forbidden field claimed_by present".
  AC-C28: move_to_quarantine creates quarantine/ directory if absent.
  AC-C29: Quarantined file path: quarantine/{original-filename}.
  AC-C30: AR task created by quarantine has tag type:user-action and body
           section ## Quarantined file with code, path, detail.
  AC-C48: Archive files containing claimed_by are read successfully (field
           silently stripped); no CorruptionError, no MigrationRequiredError.

All tests FAIL in RED phase — storage.py does not exist yet.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from owlbear_kanban.config_loader import load_config
from owlbear_kanban.corruption import CorruptionError, detect_corruption
from owlbear_kanban.models import Task
from owlbear_kanban.storage import (
    MigrationRequiredError,
    move_to_quarantine,
    read_task,
    write_task,
)

# ---------------------------------------------------------------------------
# Canonical frontmatter field order per §2.3 of paper-c.md
# ---------------------------------------------------------------------------

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

# ---------------------------------------------------------------------------
# Board / config helpers
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

# New-schema board config: no 'version' field — the migration gate in
# KanbanEngine.__init__ is active for these boards.
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


def _make_board(tmp_path: Path) -> Path:
    """Create a minimal board directory structure. Returns kanban_dir."""
    kanban_dir = tmp_path / "board"
    kanban_dir.mkdir(parents=True)
    (kanban_dir / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
    (kanban_dir / "tasks").mkdir()
    (kanban_dir / "archive").mkdir()
    return kanban_dir


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


# ---------------------------------------------------------------------------
# AC-C13, AC-C14, AC-C15 — Frontmatter canonical order, extra fields, timestamps
# ---------------------------------------------------------------------------


class TestFromAC_Frontmatter:
    """AC-C13, AC-C14, AC-C15: Frontmatter canonical order, extra fields, timestamps."""

    # AC-C13 -------------------------------------------------------------------

    def test_written_frontmatter_fields_in_canonical_order(
        self, tmp_path: Path
    ) -> None:
        """AC-C13: Canonical keys in the written file appear in §2.3 order."""
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
        """AC-C13 edge: Extra/vendor fields are NOT interleaved with canonical ones."""
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

    # AC-C14 -------------------------------------------------------------------

    def test_task_model_accepts_vendor_extra_fields(self) -> None:
        """AC-C14: Task model extra='allow' — vendor fields parsed without error."""
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
        """AC-C14: Vendor fields survive storage.write_task → storage.read_task round-trip."""
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

    # AC-C15 -------------------------------------------------------------------

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
        """AC-C15 boundary: Naive timestamp strings are written as UTC +00:00."""
        kanban_dir = _make_board(tmp_path)
        task = Task(
            id=2,
            title="Naive TS",
            status="todo",
            priority="important",
            created="2026-04-20T10:00:00",  # no tz
            updated="2026-04-20T11:00:00",  # no tz
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
        """AC-C15 boundary: Canonical TS fields with non-UTC offsets (+02:00) are
        converted to the UTC equivalent (+00:00) when written by write_task()."""
        kanban_dir = _make_board(tmp_path)
        task = Task(
            id=4,
            title="Non-UTC offset",
            status="todo",
            priority="important",
            created="2026-04-20T10:00:00+02:00",  # +02:00 → must become 08:00+00:00
            updated="2026-04-20T12:00:00+02:00",  # +02:00 → must become 10:00+00:00
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
        # Verify the actual UTC values were written (not just the offset)
        assert "2026-04-20T08:00:00+00:00" in frontmatter, (
            "created +02:00 should be converted to UTC 08:00+00:00"
        )
        assert "2026-04-20T10:00:00+00:00" in frontmatter, (
            "updated +02:00 should be converted to UTC 10:00+00:00"
        )


# ---------------------------------------------------------------------------
# AC-C16 — Corruption detection: claimed_by in tasks/
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# AC-C28, AC-C29 — Quarantine directory creation and file path
# ---------------------------------------------------------------------------


class TestFromAC_Quarantine:
    """AC-C28, AC-C29: move_to_quarantine directory creation and file placement."""

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
        """AC-C28 edge: quarantine/ pre-existing — no error raised."""
        kanban_dir = _make_board(tmp_path)
        (kanban_dir / "quarantine").mkdir()

        task_path = _write_claimed_by_file(kanban_dir / "tasks", task_id=99)
        # Must not raise even if the directory already exists
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


# ---------------------------------------------------------------------------
# AC-C30 — AR task content after engine.repair_storage()
# ---------------------------------------------------------------------------


class TestFromAC_QuarantineRepair:
    """AC-C30: repair_storage() AR task has type:user-action tag and ## Quarantined file body."""

    def test_repair_storage_ar_task_has_type_user_action_tag(
        self, tmp_path: Path
    ) -> None:
        """AC-C30: AR task created by repair_storage() carries tag type:user-action."""
        from owlbear_kanban import KanbanEngine

        kanban_dir = _make_board(tmp_path)
        _write_claimed_by_file(kanban_dir / "tasks", task_id=1)

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
        _write_claimed_by_file(kanban_dir / "tasks", task_id=1)

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
        _write_claimed_by_file(kanban_dir / "tasks", task_id=1)

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


# ---------------------------------------------------------------------------
# AC-C48 — Archive exemption: claimed_by silently stripped on read
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Builder-discovered edge cases
# ---------------------------------------------------------------------------


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
        """allocate_next_id returns current next_id and persists incremented config value."""
        from owlbear_kanban.storage import allocate_next_id

        kanban_dir = _make_board(tmp_path)
        before = load_config(kanban_dir).next_id

        allocated = allocate_next_id(kanban_dir)
        after = load_config(kanban_dir).next_id

        assert allocated == before
        assert after == before + 1

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


# ---------------------------------------------------------------------------
# AC-REGR: claimed tasks must not vanish from list_tasks()
# ---------------------------------------------------------------------------


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
