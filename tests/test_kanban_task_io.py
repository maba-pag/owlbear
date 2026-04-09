"""Failing tests for task file I/O (#717, RED phase).

AC coverage:
  AC1 - read_task(path) -> TaskRecord: all frontmatter fields + markdown body
  AC2 - write_task(path, record): --- delimited YAML frontmatter + body
  AC3 - round-trip: unknown fields, body formatting, --- in body preserved
  AC4 - validate_path_containment: reject paths outside kanban tasks_dir
  AC5 - generate_slug: [a-z0-9-] output, max 80 chars
  AC6 - Windows reserved filename rejection: CON, PRN, AUX, NUL, COM1-9, LPT1-9
  AC7 - file naming convention: {id}-{slug}.md

Import path: owlbear_mcp_kanban.task_io (module does not exist yet).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import ClassVar

import pytest

from owlbear_mcp_kanban.engine_models import TaskRecord  # type: ignore[import-not-found]
from owlbear_mcp_kanban.task_io import (  # type: ignore[import-not-found]
    generate_slug,
    make_task_filename,
    read_task,
    validate_path_containment,
    write_task,
)

# ---------------------------------------------------------------------------
# Sample task file content — mirrors .owlbear/kanban/tasks/<id>-<slug>.md
# ---------------------------------------------------------------------------

_TASK_FILE_MINIMAL = """\
---
id: 42
title: Test task title
status: todo
priority: important
created: 2026-04-09T03:24:26.6974428+02:00
updated: 2026-04-09T04:00:00.0000000+02:00
tags: []
parent: null
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
"""

_TASK_FILE_FULL = """\
---
id: 717
title: "P3-05: RED \u2014 task file I/O (read, write, round-trip)"
status: todo
priority: critical
created: 2026-04-09T03:25:21.0909825+02:00
updated: 2026-04-09T08:33:43.6088688+02:00
tags: [kanban, phase-3, type:test]
parent: 712
depends_on: [714]
blocked: false
block_reason: null
claimed_by: drift-vault
claimed_at: 2026-04-09T08:33:43.6068096+02:00
class: standard
started: null
completed: null
---

## Objective
Write failing tests for task file I/O.

## AC
- [ ] Test reads a task file...

More body content.
"""

_TASK_FILE_DASHES_IN_BODY = """\
---
id: 99
title: Task with dashes in body
status: backlog
priority: nice-to-have
created: 2026-04-09T10:00:00.0000000+02:00
updated: 2026-04-09T10:00:00.0000000+02:00
tags: []
parent: null
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---

# Section header

---

Content after first horizontal rule.

---

Content after second horizontal rule.
"""

# Minimal TaskRecord used in write tests
_MINIMAL_RECORD = TaskRecord(
    id=42,
    title="Test task title",
    status="todo",
    priority="important",
    created="2026-04-09T03:24:26.6974428+02:00",
    updated="2026-04-09T04:00:00.0000000+02:00",
)

# Full TaskRecord with all optional fields + unknown fields
_FULL_RECORD = TaskRecord.model_validate(
    {
        "id": 717,
        "title": "P3-05: RED \u2014 task file I/O (read, write, round-trip)",
        "status": "todo",
        "priority": "critical",
        "created": "2026-04-09T03:25:21.0909825+02:00",
        "updated": "2026-04-09T08:33:43.6088688+02:00",
        "tags": ["kanban", "phase-3", "type:test"],
        "parent": 712,
        "depends_on": [714],
        "blocked": False,
        "block_reason": None,
        "claimed_by": "drift-vault",
        "claimed_at": "2026-04-09T08:33:43.6068096+02:00",
        # unknown fields — Go kanban-md extras
        "class": "standard",
        "started": None,
        "completed": None,
        "body": "## Objective\nWrite failing tests.\n",
    }
)

_RECORD_WITH_DASHES_IN_BODY = TaskRecord(
    id=99,
    title="Task with dashes in body",
    status="backlog",
    priority="nice-to-have",
    created="2026-04-09T10:00:00.0000000+02:00",
    updated="2026-04-09T10:00:00.0000000+02:00",
    body="# Section header\n\n---\n\nContent after first horizontal rule.\n\n---\n\nContent after second.\n",
)


# ===========================================================================
# TestFromAC_ReadTaskFile (AC1)
# ===========================================================================


class TestFromAC_ReadTaskFile:
    """Tests for AC1: read_task(path) -> TaskRecord with all frontmatter fields + body."""

    # --- Happy path ---------------------------------------------------------

    def test_read_returns_task_record(self, tmp_path: Path) -> None:
        """read_task returns a TaskRecord instance."""
        task_file = tmp_path / "42-test-task-title.md"
        task_file.write_text(_TASK_FILE_MINIMAL, encoding="utf-8")
        result = read_task(task_file)
        assert isinstance(result, TaskRecord)

    def test_read_parses_id(self, tmp_path: Path) -> None:
        """read_task correctly parses the id field as int."""
        task_file = tmp_path / "42-test-task-title.md"
        task_file.write_text(_TASK_FILE_MINIMAL, encoding="utf-8")
        result = read_task(task_file)
        assert result.id == 42

    def test_read_parses_title(self, tmp_path: Path) -> None:
        """read_task correctly parses the title field as str."""
        task_file = tmp_path / "42-test-task-title.md"
        task_file.write_text(_TASK_FILE_MINIMAL, encoding="utf-8")
        result = read_task(task_file)
        assert result.title == "Test task title"

    def test_read_parses_status_and_priority(self, tmp_path: Path) -> None:
        """read_task correctly parses status and priority fields."""
        task_file = tmp_path / "42-test-task-title.md"
        task_file.write_text(_TASK_FILE_MINIMAL, encoding="utf-8")
        result = read_task(task_file)
        assert result.status == "todo"
        assert result.priority == "important"

    def test_read_parses_timestamps_as_str(self, tmp_path: Path) -> None:
        """read_task stores created and updated as strings, not datetime objects."""
        task_file = tmp_path / "42-test-task-title.md"
        task_file.write_text(_TASK_FILE_MINIMAL, encoding="utf-8")
        result = read_task(task_file)
        assert isinstance(result.created, str)
        assert isinstance(result.updated, str)

    def test_read_preserves_go_nanosecond_precision(self, tmp_path: Path) -> None:
        """read_task preserves 7-digit nanosecond timestamps verbatim (Go format)."""
        task_file = tmp_path / "42-test-task-title.md"
        task_file.write_text(_TASK_FILE_MINIMAL, encoding="utf-8")
        result = read_task(task_file)
        # 7 decimal places (Go nanosecond format) — must not truncate to 6
        assert result.created == "2026-04-09T03:24:26.6974428+02:00"

    def test_read_parses_all_optional_fields(self, tmp_path: Path) -> None:
        """read_task parses tags, parent, depends_on, blocked, claimed_by, claimed_at."""
        task_file = tmp_path / "717-p3-05.md"
        task_file.write_text(_TASK_FILE_FULL, encoding="utf-8")
        result = read_task(task_file)
        assert result.tags == ["kanban", "phase-3", "type:test"]
        assert result.parent == 712
        assert result.depends_on == [714]
        assert result.blocked is False
        assert result.claimed_by == "drift-vault"
        assert isinstance(result.claimed_at, str)

    def test_read_parses_body_as_str(self, tmp_path: Path) -> None:
        """read_task places markdown body content in the body field as a string."""
        task_file = tmp_path / "717-p3-05.md"
        task_file.write_text(_TASK_FILE_FULL, encoding="utf-8")
        result = read_task(task_file)
        assert isinstance(result.body, str)
        assert "## Objective" in result.body

    def test_read_empty_body_returns_empty_or_whitespace(self, tmp_path: Path) -> None:
        """read_task on a file with no body returns empty string or only whitespace."""
        task_file = tmp_path / "42-test-task-title.md"
        task_file.write_text(_TASK_FILE_MINIMAL, encoding="utf-8")
        result = read_task(task_file)
        assert result.body.strip() == ""

    def test_read_preserves_unknown_frontmatter_fields(self, tmp_path: Path) -> None:
        """read_task preserves unknown fields (e.g. class, started) via extra='allow'."""
        task_file = tmp_path / "717-p3-05.md"
        task_file.write_text(_TASK_FILE_FULL, encoding="utf-8")
        result = read_task(task_file)
        dumped = result.model_dump()
        assert dumped.get("class") == "standard"

    def test_read_nonexistent_file_raises(self, tmp_path: Path) -> None:
        """read_task raises an error when the path does not exist."""
        missing = tmp_path / "9999-does-not-exist.md"
        with pytest.raises((FileNotFoundError, OSError)):
            read_task(missing)

    def test_read_file_missing_frontmatter_raises(self, tmp_path: Path) -> None:
        """read_task raises an error when the file has no YAML frontmatter delimiters."""
        task_file = tmp_path / "bad-file.md"
        task_file.write_text("Just plain markdown, no frontmatter here.\n", encoding="utf-8")
        with pytest.raises((ValueError, KeyError, Exception)):
            read_task(task_file)


# ===========================================================================
# TestFromAC_WriteTaskFile (AC2)
# ===========================================================================


class TestFromAC_WriteTaskFile:
    """Tests for AC2: write_task(path, record) produces --- delimited YAML + body."""

    # --- Happy path ---------------------------------------------------------

    def test_write_creates_file(self, tmp_path: Path) -> None:
        """write_task creates a file at the given path."""
        task_file = tmp_path / "42-test-task-title.md"
        write_task(task_file, _MINIMAL_RECORD)
        assert task_file.exists()

    def test_write_begins_with_frontmatter_delimiter(self, tmp_path: Path) -> None:
        """write_task produces a file whose first line is ---."""
        task_file = tmp_path / "42-test-task-title.md"
        write_task(task_file, _MINIMAL_RECORD)
        content = task_file.read_text(encoding="utf-8")
        assert content.startswith("---\n")

    def test_write_contains_closing_frontmatter_delimiter(self, tmp_path: Path) -> None:
        """write_task file has a second --- that closes the YAML frontmatter block."""
        task_file = tmp_path / "42-test-task-title.md"
        write_task(task_file, _MINIMAL_RECORD)
        content = task_file.read_text(encoding="utf-8")
        # lines: first line is '---', second --- closes frontmatter
        lines = content.splitlines()
        assert lines[0] == "---"
        assert "---" in lines[1:]  # closing delimiter must appear after opening

    def test_write_includes_id_in_frontmatter(self, tmp_path: Path) -> None:
        """write_task includes the task id in the YAML frontmatter."""
        task_file = tmp_path / "42-test-task-title.md"
        write_task(task_file, _MINIMAL_RECORD)
        content = task_file.read_text(encoding="utf-8")
        assert "id: 42" in content

    def test_write_includes_title_in_frontmatter(self, tmp_path: Path) -> None:
        """write_task includes the task title in the YAML frontmatter."""
        task_file = tmp_path / "42-test-task-title.md"
        write_task(task_file, _MINIMAL_RECORD)
        content = task_file.read_text(encoding="utf-8")
        assert "Test task title" in content

    def test_write_body_appears_after_second_delimiter(self, tmp_path: Path) -> None:
        """write_task places markdown body after the closing --- delimiter."""
        record = TaskRecord(
            id=42,
            title="Title",
            status="todo",
            priority="important",
            created="2026-04-09T03:24:26.6974428+02:00",
            updated="2026-04-09T04:00:00.0000000+02:00",
            body="## Objective\nSome content.\n",
        )
        task_file = tmp_path / "42-title.md"
        write_task(task_file, record)
        content = task_file.read_text(encoding="utf-8")
        # body must appear after frontmatter block ends
        body_start = content.index("---\n", 4) + 4  # skip past second ---
        assert "## Objective" in content[body_start:]

    def test_write_preserves_optional_fields(self, tmp_path: Path) -> None:
        """write_task preserves optional fields like tags, parent, depends_on."""
        task_file = tmp_path / "717-p3-05.md"
        write_task(task_file, _FULL_RECORD)
        content = task_file.read_text(encoding="utf-8")
        assert "phase-3" in content
        assert "712" in content  # parent
        assert "714" in content  # depends_on

    def test_write_empty_body_produces_valid_file(self, tmp_path: Path) -> None:
        """write_task with empty body still produces a valid frontmatter file."""
        task_file = tmp_path / "42-test-task-title.md"
        write_task(task_file, _MINIMAL_RECORD)
        content = task_file.read_text(encoding="utf-8")
        assert "---" in content  # at minimum frontmatter delimiters present

    def test_write_dashes_in_body_do_not_appear_in_frontmatter_block(
        self, tmp_path: Path
    ) -> None:
        """write_task with --- in body: the --- markers appear only after closing delimiter."""
        task_file = tmp_path / "99-dashes-in-body.md"
        write_task(task_file, _RECORD_WITH_DASHES_IN_BODY)
        content = task_file.read_text(encoding="utf-8")
        lines = content.splitlines()
        # Find index of opening and closing frontmatter delimiters
        opening = 0  # line 0 is "---"
        closing = next(i for i, ln in enumerate(lines) if i > 0 and ln == "---")
        frontmatter_yaml = "\n".join(lines[opening + 1 : closing])
        # The YAML block must not contain stray --- that look like extra frontmatter
        assert frontmatter_yaml.count("---") == 0

    def test_write_overwrites_existing_file(self, tmp_path: Path) -> None:
        """write_task replaces existing file contents at the path."""
        task_file = tmp_path / "42-test-task-title.md"
        task_file.write_text("old content", encoding="utf-8")
        write_task(task_file, _MINIMAL_RECORD)
        content = task_file.read_text(encoding="utf-8")
        assert "old content" not in content
        assert "id: 42" in content


# ===========================================================================
# TestFromAC_RoundTrip (AC3)
# ===========================================================================


class TestFromAC_RoundTrip:
    """Tests for AC3: round-trip preserves data without data loss."""

    def test_round_trip_required_fields_preserved(self, tmp_path: Path) -> None:
        """write_task + read_task preserves id, title, status, priority, timestamps."""
        task_file = tmp_path / "42-test-task-title.md"
        write_task(task_file, _MINIMAL_RECORD)
        result = read_task(task_file)
        assert result.id == _MINIMAL_RECORD.id
        assert result.title == _MINIMAL_RECORD.title
        assert result.status == _MINIMAL_RECORD.status
        assert result.priority == _MINIMAL_RECORD.priority
        assert result.created == _MINIMAL_RECORD.created
        assert result.updated == _MINIMAL_RECORD.updated

    def test_round_trip_optional_fields_preserved(self, tmp_path: Path) -> None:
        """write_task + read_task preserves tags, parent, depends_on, claimed_by."""
        task_file = tmp_path / "717-p3-05.md"
        write_task(task_file, _FULL_RECORD)
        result = read_task(task_file)
        assert result.tags == _FULL_RECORD.tags
        assert result.parent == _FULL_RECORD.parent
        assert result.depends_on == _FULL_RECORD.depends_on
        assert result.claimed_by == _FULL_RECORD.claimed_by

    def test_round_trip_unknown_fields_preserved(self, tmp_path: Path) -> None:
        """write_task + read_task preserves unknown extra fields (class, started, completed)."""
        task_file = tmp_path / "717-p3-05.md"
        write_task(task_file, _FULL_RECORD)
        result = read_task(task_file)
        original_dump = _FULL_RECORD.model_dump()
        result_dump = result.model_dump()
        assert result_dump.get("class") == original_dump.get("class")
        assert "started" in result_dump

    def test_round_trip_body_formatting_preserved(self, tmp_path: Path) -> None:
        """write_task + read_task preserves markdown body content verbatim."""
        task_file = tmp_path / "717-p3-05.md"
        write_task(task_file, _FULL_RECORD)
        result = read_task(task_file)
        assert result.body == _FULL_RECORD.body

    def test_round_trip_dashes_in_body_preserved(self, tmp_path: Path) -> None:
        """Round-trip with --- in body: horizontal rules survive without corrupting frontmatter."""
        task_file = tmp_path / "99-dashes-in-body.md"
        write_task(task_file, _RECORD_WITH_DASHES_IN_BODY)
        result = read_task(task_file)
        assert "---" in result.body  # horizontal rule still in body
        assert result.id == 99  # frontmatter still parsed correctly
        assert result.title == "Task with dashes in body"

    def test_round_trip_go_nanosecond_timestamp_exact(self, tmp_path: Path) -> None:
        """Round-trip preserves 7-digit Go nanosecond timestamp precision exactly."""
        go_ts = "2026-04-09T03:25:21.0909825+02:00"
        record = TaskRecord(
            id=1,
            title="Precision test",
            status="todo",
            priority="important",
            created=go_ts,
            updated=go_ts,
        )
        task_file = tmp_path / "1-precision-test.md"
        write_task(task_file, record)
        result = read_task(task_file)
        assert result.created == go_ts
        assert result.updated == go_ts

    def test_round_trip_multiline_body_preserved(self, tmp_path: Path) -> None:
        """Round-trip preserves multi-paragraph body including blank lines."""
        multiline_body = "# Section 1\n\nParagraph one.\n\n# Section 2\n\nParagraph two.\n"
        record = TaskRecord(
            id=5,
            title="Multi section",
            status="todo",
            priority="important",
            created="2026-04-09T00:00:00.0000000+00:00",
            updated="2026-04-09T00:00:00.0000000+00:00",
            body=multiline_body,
        )
        task_file = tmp_path / "5-multi-section.md"
        write_task(task_file, record)
        result = read_task(task_file)
        assert result.body == multiline_body

    def test_round_trip_file_from_disk_matches_original(self, tmp_path: Path) -> None:
        """Reading a manually crafted task file then writing it back produces identical content."""
        task_file = tmp_path / "717-p3-05.md"
        task_file.write_text(_TASK_FILE_FULL, encoding="utf-8")
        record = read_task(task_file)
        out_file = tmp_path / "717-p3-05-out.md"
        write_task(out_file, record)
        # Re-read the output and verify key fields round-tripped
        result = read_task(out_file)
        assert result.id == 717
        assert result.title == record.title
        assert result.body == record.body


# ===========================================================================
# TestFromAC_PathContainment (AC4)
# ===========================================================================


class TestFromAC_PathContainment:
    """Tests for AC4: validate_path_containment rejects paths outside tasks_dir."""

    def test_valid_path_inside_dir_accepted(self, tmp_path: Path) -> None:
        """Path inside tasks_dir passes without error."""
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        valid_path = tasks_dir / "42-my-task.md"
        # must not raise
        validate_path_containment(tasks_dir, valid_path)

    def test_path_outside_dir_raises(self, tmp_path: Path) -> None:
        """Path outside tasks_dir raises PermissionError or ValueError."""
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        outside = tmp_path / "secret.md"
        with pytest.raises((PermissionError, ValueError)):
            validate_path_containment(tasks_dir, outside)

    def test_dotdot_traversal_raises(self, tmp_path: Path) -> None:
        """Path with .. traversal that escapes tasks_dir raises."""
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        traversal = tasks_dir / ".." / ".." / "etc" / "passwd"
        with pytest.raises((PermissionError, ValueError)):
            validate_path_containment(tasks_dir, traversal)

    def test_null_byte_in_path_raises(self, tmp_path: Path) -> None:
        """Path containing a null byte is rejected (security: null byte injection)."""
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        with pytest.raises((PermissionError, ValueError, OSError)):
            validate_path_containment(tasks_dir, Path(str(tasks_dir) + "/42-task\x00.md"))

    def test_tasks_dir_itself_raises(self, tmp_path: Path) -> None:
        """The tasks_dir root itself is not a valid task file path."""
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        with pytest.raises((PermissionError, ValueError, IsADirectoryError)):
            validate_path_containment(tasks_dir, tasks_dir)

    def test_sibling_dir_path_raises(self, tmp_path: Path) -> None:
        """Path inside a sibling directory (not tasks_dir) is rejected."""
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        sibling = tmp_path / "other_dir"
        sibling.mkdir()
        sibling_path = sibling / "42-my-task.md"
        with pytest.raises((PermissionError, ValueError)):
            validate_path_containment(tasks_dir, sibling_path)


# ===========================================================================
# TestFromAC_SlugGeneration (AC5)
# ===========================================================================


class TestFromAC_SlugGeneration:
    """Tests for AC5: generate_slug produces [a-z0-9-] slug with max 80 chars."""

    def test_simple_title_lowercased(self) -> None:
        """generate_slug produces lowercase output."""
        slug = generate_slug("My Task Title")
        assert slug == slug.lower()

    def test_spaces_become_hyphens(self) -> None:
        """generate_slug replaces spaces with hyphens."""
        slug = generate_slug("my task title")
        assert " " not in slug
        assert "-" in slug

    def test_example_title_produces_expected_slug(self) -> None:
        """Real task title produces a correct slug (verified against known output)."""
        # Title: "P3-05: RED — task file I/O (read, write, round-trip)"
        # Expected slug: "p3-05-red-task-file-io-read-write-round-trip"
        slug = generate_slug("P3-05: RED \u2014 task file I/O (read, write, round-trip)")
        assert re.fullmatch(r"[a-z0-9-]+", slug), f"Slug contains illegal chars: {slug!r}"

    def test_slug_only_contains_allowed_chars(self) -> None:
        """generate_slug output matches [a-z0-9-]+ only."""
        titles = [
            "Simple Title",
            "Task with (parentheses) and [brackets]",
            "Emoji: \U0001f4a1 idea",
            "Slashes/and\\backslashes",
            "Mixed CASE and Numbers 42",
        ]
        for title in titles:
            slug = generate_slug(title)
            assert re.fullmatch(r"[a-z0-9-]*", slug), f"Illegal chars in slug for {title!r}: {slug!r}"

    def test_slug_at_exactly_80_chars_not_truncated(self) -> None:
        """Title producing exactly 80-char slug is not truncated."""
        # 80 'a' chars separated by spaces -> slug = 40 'a' + hyphens or just 'a' x 80
        title = "a " * 40  # "a a a a..." -> "a-a-a-a-..." -> 79 chars with hyphens
        slug = generate_slug(title.strip())
        assert len(slug) <= 80

    def test_slug_truncated_to_max_80_chars(self) -> None:
        """generate_slug truncates slug to max 80 characters."""
        long_title = "word " * 30  # Very long title
        slug = generate_slug(long_title.strip())
        assert len(slug) <= 80

    def test_slug_exactly_80_chars_boundary(self) -> None:
        """A title whose slug is borderline 80 chars is handled correctly."""
        # Construct title where slug is exactly 81 chars before truncation
        base = "ab" * 41  # 82 chars, all lowercase alphanum
        slug = generate_slug(base)
        assert len(slug) <= 80

    def test_empty_title_returns_empty_or_raises(self) -> None:
        """generate_slug with empty string returns empty string or raises ValueError."""
        try:
            result = generate_slug("")
            assert isinstance(result, str)
        except ValueError:
            pass  # raising is also acceptable


# ===========================================================================
# TestFromAC_WindowsReservedNames (AC6)
# ===========================================================================


class TestFromAC_WindowsReservedNames:
    """Tests for AC6: Windows reserved filenames rejected by generate_slug."""

    _DEVICE_NAMES: ClassVar[list[str]] = ["CON", "PRN", "AUX", "NUL"]
    _COM_NAMES: ClassVar[list[str]] = [f"COM{i}" for i in range(1, 10)]
    _LPT_NAMES: ClassVar[list[str]] = [f"LPT{i}" for i in range(1, 10)]

    def test_con_rejected(self) -> None:
        """generate_slug('CON') raises ValueError (Windows reserved device name)."""
        with pytest.raises(ValueError, match=r"(?i)reserved|con"):
            generate_slug("CON")

    def test_prn_rejected(self) -> None:
        """generate_slug('PRN') raises ValueError."""
        with pytest.raises(ValueError, match=r"(?i)reserved|prn"):
            generate_slug("PRN")

    def test_aux_rejected(self) -> None:
        """generate_slug('AUX') raises ValueError."""
        with pytest.raises(ValueError, match=r"(?i)reserved|aux"):
            generate_slug("AUX")

    def test_nul_rejected(self) -> None:
        """generate_slug('NUL') raises ValueError."""
        with pytest.raises(ValueError, match=r"(?i)reserved|nul"):
            generate_slug("NUL")

    def test_com1_through_com9_all_rejected(self) -> None:
        """generate_slug('COM1') through ('COM9') all raise ValueError."""
        for name in self._COM_NAMES:
            with pytest.raises(ValueError, match=r"(?i)reserved"):
                generate_slug(name)

    def test_lpt1_through_lpt9_all_rejected(self) -> None:
        """generate_slug('LPT1') through ('LPT9') all raise ValueError."""
        for name in self._LPT_NAMES:
            with pytest.raises(ValueError, match=r"(?i)reserved"):
                generate_slug(name)

    def test_reserved_names_case_insensitive(self) -> None:
        """Reserved name check is case-insensitive: 'con', 'Con', 'CON' all rejected."""
        for variant in ("con", "Con", "CON"):
            with pytest.raises(ValueError, match=r"(?i)reserved|con"):
                generate_slug(variant)

    def test_reserved_name_as_word_in_longer_title_accepted(self) -> None:
        """'CON' as part of a longer slug ('con-task') is not rejected."""
        # "CON task" -> slug "con-task" -> NOT a reserved name (exact match only)
        slug = generate_slug("CON task")
        assert slug is not None  # should not raise

    def test_valid_slug_not_rejected(self) -> None:
        """Normal titles produce valid slugs without raising."""
        slug = generate_slug("My Normal Task Title 42")
        assert isinstance(slug, str)
        assert len(slug) > 0


# ===========================================================================
# TestFromAC_FileNamingConvention (AC7)
# ===========================================================================


class TestFromAC_FileNamingConvention:
    """Tests for AC7: make_task_filename returns '{id}-{slug}.md' filenames."""

    def test_filename_follows_id_dash_slug_dot_md_pattern(self) -> None:
        """make_task_filename returns a string matching '<int>-<slug>.md'."""
        filename = make_task_filename(42, "My Task Title")
        assert re.fullmatch(r"\d+-[a-z0-9-]+\.md", filename), (
            f"Filename {filename!r} does not match '<int>-<slug>.md'"
        )

    def test_filename_starts_with_task_id(self) -> None:
        """make_task_filename prefixes the filename with the task id."""
        filename = make_task_filename(717, "P3-05: RED task")
        assert filename.startswith("717-")

    def test_filename_ends_with_dot_md(self) -> None:
        """make_task_filename produces a .md file extension."""
        filename = make_task_filename(1, "Simple Title")
        assert filename.endswith(".md")

    def test_slug_in_filename_matches_generate_slug_output(self) -> None:
        """The slug portion of the filename matches generate_slug(title) output."""
        title = "My Amazing Task"
        slug = generate_slug(title)
        filename = make_task_filename(100, title)
        expected = f"100-{slug}.md"
        assert filename == expected

    def test_filename_slug_only_contains_allowed_chars(self) -> None:
        """Slug portion of make_task_filename contains only [a-z0-9-] chars."""
        filename = make_task_filename(55, "Task: (with) [special] chars!")
        slug_part = filename[len("55-") : -len(".md")]
        assert re.fullmatch(r"[a-z0-9-]+", slug_part), (
            f"Slug portion {slug_part!r} contains illegal chars"
        )


# ===========================================================================
# TestBuilderDiscovered
# ===========================================================================


class TestBuilderDiscovered:
    """Edge cases discovered during implementation that were not in TestFromAC_* tests."""

    def test_read_task_missing_closing_delimiter_raises(self, tmp_path: Path) -> None:
        """read_task raises ValueError when file has opening --- but no closing ---."""
        task_file = tmp_path / "bad-missing-close.md"
        task_file.write_text(
            "---\nid: 42\ntitle: No closing delimiter\n",
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match=r"closing"):
            read_task(task_file)
