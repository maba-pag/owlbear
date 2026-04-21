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

from owlbear_kanban.models import Task
from owlbear_kanban.storage import (
    CorruptionError,
    MigrationRequiredError,
    detect_corruption,
    load_config,
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

    def test_written_frontmatter_fields_in_canonical_order(self, tmp_path: Path) -> None:
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

    def test_vendor_extra_fields_appear_after_canonical_fields(self, tmp_path: Path) -> None:
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
        canonical_positions = [i for i, k in enumerate(keys) if k in _CANONICAL_FIELD_ORDER]
        vendor_positions = [i for i, k in enumerate(keys) if k not in _CANONICAL_FIELD_ORDER]

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

    def test_vendor_extra_fields_survive_write_read_round_trip(self, tmp_path: Path) -> None:
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

    def test_detect_corruption_claimed_by_detail_exact_string(self, tmp_path: Path) -> None:
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

    def test_move_to_quarantine_no_error_when_dir_already_exists(self, tmp_path: Path) -> None:
        """AC-C28 edge: quarantine/ pre-existing — no error raised."""
        kanban_dir = _make_board(tmp_path)
        (kanban_dir / "quarantine").mkdir()

        task_path = _write_claimed_by_file(kanban_dir / "tasks", task_id=99)
        # Must not raise even if the directory already exists
        move_to_quarantine(task_path, kanban_dir)

    def test_move_to_quarantine_returns_quarantine_subpath(self, tmp_path: Path) -> None:
        """AC-C29: Return value is quarantine/{original-filename}."""
        kanban_dir = _make_board(tmp_path)
        task_path = _write_claimed_by_file(kanban_dir / "tasks", task_id=7)
        original_name = task_path.name

        result_path = move_to_quarantine(task_path, kanban_dir)

        assert result_path == kanban_dir / "quarantine" / original_name

    def test_move_to_quarantine_file_exists_at_returned_path(self, tmp_path: Path) -> None:
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

    def test_repair_storage_ar_task_has_type_user_action_tag(self, tmp_path: Path) -> None:
        """AC-C30: AR task created by repair_storage() carries tag type:user-action."""
        from owlbear_kanban import KanbanEngine

        kanban_dir = _make_board(tmp_path)
        _write_claimed_by_file(kanban_dir / "tasks", task_id=1)

        engine = KanbanEngine(kanban_dir=kanban_dir, agent_name="test-agent")
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

        engine = KanbanEngine(kanban_dir=kanban_dir, agent_name="test-agent")
        engine.repair_storage()

        ar_tasks = [
            engine.show_task(task_id=t.id)
            for t in engine.list_tasks()
            if "type:user-action" in (t.tags or [])
        ]
        assert len(ar_tasks) >= 1
        for ar_task in ar_tasks:
            assert "## Quarantined file" in ar_task.body

    def test_repair_storage_ar_body_has_code_path_detail_fields(self, tmp_path: Path) -> None:
        """AC-C30: AR body ## Quarantined file section contains code, path, and detail."""
        from owlbear_kanban import KanbanEngine

        kanban_dir = _make_board(tmp_path)
        _write_claimed_by_file(kanban_dir / "tasks", task_id=1)

        engine = KanbanEngine(kanban_dir=kanban_dir, agent_name="test-agent")
        engine.repair_storage()

        ar_tasks = [
            engine.show_task(task_id=t.id)
            for t in engine.list_tasks()
            if "type:user-action" in (t.tags or [])
        ]
        assert len(ar_tasks) >= 1
        body = ar_tasks[0].body

        assert "code" in body, f"'code' not found in AR body:\n{body}"
        assert "path" in body, f"'path' not found in AR body:\n{body}"
        assert "detail" in body, f"'detail' not found in AR body:\n{body}"


# ---------------------------------------------------------------------------
# AC-C48 — Archive exemption: claimed_by silently stripped on read
# ---------------------------------------------------------------------------


class TestFromAC_ArchiveExemption:
    """AC-C48: Archive files with claimed_by read successfully; field silently stripped."""

    def test_archive_file_with_claimed_by_reads_without_exception(self, tmp_path: Path) -> None:
        """AC-C48: No CorruptionError when reading archive file containing claimed_by."""
        kanban_dir = _make_board(tmp_path)
        archive_path = _write_claimed_by_file(kanban_dir / "archive", task_id=5)

        task = read_task(archive_path)

        assert task is not None
        assert task.id == 5

    def test_archive_claimed_by_stripped_from_returned_task(self, tmp_path: Path) -> None:
        """AC-C48: claimed_by is absent (or None) in the Task returned from archive read."""
        kanban_dir = _make_board(tmp_path)
        archive_path = _write_claimed_by_file(kanban_dir / "archive", task_id=5)

        task = read_task(archive_path)
        dumped = task.model_dump()

        assert dumped.get("claimed_by") is None

    def test_archive_claimed_by_does_not_raise_corruption_error(self, tmp_path: Path) -> None:
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
        """AC-C48: KanbanEngine.__init__ does NOT raise MigrationRequiredError for archive files."""
        from owlbear_kanban import KanbanEngine

        kanban_dir = _make_board(tmp_path)
        # Only archive/ has claimed_by — tasks/ is clean
        _write_claimed_by_file(kanban_dir / "archive", task_id=5)

        # Must not raise MigrationRequiredError
        try:
            engine = KanbanEngine(kanban_dir=kanban_dir, agent_name="test-agent")
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
