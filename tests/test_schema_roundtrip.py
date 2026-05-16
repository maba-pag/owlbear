"""TDD RED: #1338 — Prove old-to-new schema round-trip before sync.

AC 5: Round-trip test: old-format board → engine loads → saves →
      old-format reader can still parse (or explicit migration converts cleanly).

All tests FAIL in RED phase because:
- read_task on archive files does not strip claimed_by (returns 'some-agent' not None)
- write_task single-quotes timestamps so endswith('+00:00') check fails on raw content
- Engine move_task to 'archived' now requires archival_reason (old fixtures omit it)
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from owlbear_kanban import KanbanEngine
from owlbear_kanban.storage import list_task_files, read_task, write_task

# ---------------------------------------------------------------------------
# Board fixture templates
# ---------------------------------------------------------------------------

_GROUPED_CONFIG_YAML = """\
schema: grouped
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
next_id: 1001
activity_log: false
paths:
  tasks_dir: tasks
  archive_dir: archive
pipeline:
  entry_status: research
  terminal_status: done
  wave_size: 4
  claim_timeout: 1h
  default_priority: important
agents:
  agent_map:
    research: []
    backlog: []
    todo: []
    in-progress: []
    review: []
    docs: []
    done: []
  agent_types: {}
  agent_compatibility: {}
policy:
  non_impl_tags:
    - research
    - docs
    - type:config
    - type:docs
    - test
    - type:test
    - agent
    - quality
    - type:user-action
  archival_reasons:
    - completed
    - deprecated
    - dropped
    - duplicate
    - wontfix
  status_predicates: {}
"""

_LEGACY_CONFIG_YAML = """\
version: 9
board:
  name: TestBoard
tasks_dir: tasks
archive_dir: archive
statuses:
- name: research
  color: "#aaa"
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
next_id: 1001
activity_log: false
"""

# Legacy task with claimed_by and no frontmatter defaults
_LEGACY_TASK_MD = """\
---
id: {task_id}
title: {title}
status: todo
priority: needed
claimed_by: some-agent
created: "2026-01-15T08:00:00+00:00"
updated: "2026-01-15T08:00:00+00:00"
---

## Notes

Legacy task body for {task_id}.
"""

# Legacy archive file without archival_reason and without claimed_by (normal archive)
_LEGACY_ARCHIVE_MD = """\
---
id: {task_id}
title: {title}
status: done
priority: needed
created: "2026-01-10T08:00:00+00:00"
updated: "2026-01-12T09:00:00+00:00"
class: tier-1
---

## Notes

Legacy archive body for {task_id}.
"""

# Archive file WITH claimed_by (mimics a pre-migration active task that got archived)
_ARCHIVE_WITH_CLAIMED_BY_MD = """\
---
id: {task_id}
title: {title}
status: done
priority: needed
claimed_by: some-agent
created: "2026-01-10T08:00:00+00:00"
updated: "2026-01-12T09:00:00+00:00"
---

## Notes

Archive with claimed_by body for {task_id}.
"""

# Modern fully-formed active task (no claimed_by, all defaults)
_MODERN_TASK_MD = """\
---
id: {task_id}
title: {title}
status: todo
priority: needed
created: "2026-01-15T08:00:00+00:00"
updated: "2026-01-15T08:00:00+00:00"
tags: []
parent: null
depends_on: []
blocked: false
block_reason: null
claimed_at: null
archival_reason: null
archival_refs: []
---

## Notes

Modern task body for {task_id}.
"""


# ---------------------------------------------------------------------------
# Board helpers
# ---------------------------------------------------------------------------


def _make_grouped_board(base_dir: Path) -> Path:
    """Create a board already in grouped (new) schema format."""
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_GROUPED_CONFIG_YAML, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


def _make_legacy_board(base_dir: Path) -> Path:
    """Create a board in legacy schema format (version: 9, list-of-dict statuses)."""
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_LEGACY_CONFIG_YAML, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


def _write_legacy_task(kanban_dir: Path, task_id: int, title: str) -> Path:
    path = kanban_dir / "tasks" / f"{task_id}-task.md"
    path.write_text(
        _LEGACY_TASK_MD.format(task_id=task_id, title=title),
        encoding="utf-8",
    )
    return path


def _write_legacy_archive(kanban_dir: Path, task_id: int, title: str) -> Path:
    path = kanban_dir / "archive" / f"{task_id}-archive.md"
    path.write_text(
        _LEGACY_ARCHIVE_MD.format(task_id=task_id, title=title),
        encoding="utf-8",
    )
    return path


def _write_archive_with_claimed_by(kanban_dir: Path, task_id: int, title: str) -> Path:
    path = kanban_dir / "archive" / f"{task_id}-archive.md"
    path.write_text(
        _ARCHIVE_WITH_CLAIMED_BY_MD.format(task_id=task_id, title=title),
        encoding="utf-8",
    )
    return path


def _write_modern_task(kanban_dir: Path, task_id: int, title: str) -> Path:
    path = kanban_dir / "tasks" / f"{task_id}-task.md"
    path.write_text(
        _MODERN_TASK_MD.format(task_id=task_id, title=title),
        encoding="utf-8",
    )
    return path


def _run_migrate(
    kanban_dir: Path,
    *,
    lane: str = "all",
) -> subprocess.CompletedProcess[str]:
    cmd = [
        sys.executable,
        "-m",
        "owlbear_kanban.migrate",
        "--kanban-dir",
        str(kanban_dir),
        "--lane",
        lane,
    ]
    return subprocess.run(cmd, capture_output=True, text=True, env={**os.environ})


def _extract_frontmatter(path: Path) -> str:
    """Return the raw frontmatter block (between the two --- delimiters)."""
    content = path.read_text(encoding="utf-8")
    assert content.startswith("---\n"), f"No opening --- in {path}"
    closing_idx = content.index("---\n", 4)
    return content[4:closing_idx]


# ---------------------------------------------------------------------------
# TestFromAC_SchemaRoundTrip
# ---------------------------------------------------------------------------


class TestFromAC_SchemaRoundTrip:
    """AC 5: Old-format board → migrate → engine loads → saves → re-parseable."""

    def test_full_round_trip_timestamps_unquoted_in_written_file(self, tmp_path: Path) -> None:
        """AC 5: After migration + engine write, timestamp lines end with +00:00 (plain, not quoted).

        The round-trip: legacy board → kanban-migrate → engine.show_task →
        write_task → raw content check.  Fails because write_task wraps
        timestamps in single quotes so the line ends with '+00:00'' not
        '+00:00'.
        """
        import re

        kanban_dir = _make_legacy_board(tmp_path)
        _write_legacy_task(kanban_dir, 1001, "Round-trip timestamp check")

        result = _run_migrate(kanban_dir)
        assert result.returncode == 0, f"kanban-migrate failed:\n{result.stdout}\n{result.stderr}"

        engine = KanbanEngine(kanban_dir=kanban_dir)
        task = engine.show_task(task_id="1001")
        written_path = write_task(task, kanban_dir)

        frontmatter = _extract_frontmatter(written_path)
        ts_re = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")
        for line in frontmatter.splitlines():
            if ts_re.search(line):
                assert line.rstrip().endswith("+00:00"), (
                    f"Round-trip: timestamp line must end with +00:00 (not single-quoted): {line.rstrip()!r}"
                )

    def test_full_round_trip_task_data_preserved_after_migrate_and_write(self, tmp_path: Path) -> None:
        """AC 5: All core task fields survive the full round-trip without data loss.

        Round-trip: legacy board → kanban-migrate → engine.show_task →
        write_task → read_task.  Field values must be identical after
        the round-trip.  Fails because write_task single-quotes timestamps,
        which causes read_task to mis-parse updated/created timestamps
        or otherwise break data integrity.
        """
        import re

        kanban_dir = _make_legacy_board(tmp_path)
        _write_legacy_task(kanban_dir, 1001, "Data integrity check task")

        result = _run_migrate(kanban_dir)
        assert result.returncode == 0, f"kanban-migrate failed:\n{result.stdout}\n{result.stderr}"

        engine = KanbanEngine(kanban_dir=kanban_dir)
        task_before = engine.show_task(task_id="1001")
        written_path = write_task(task_before, kanban_dir)

        task_after = read_task(written_path)

        # Core fields must be preserved exactly
        assert task_after.id == task_before.id
        assert task_after.title == task_before.title
        assert task_after.status == task_before.status
        assert task_after.priority == task_before.priority
        assert task_after.body == task_before.body
        assert task_after.parent == task_before.parent
        assert task_after.tags == task_before.tags
        assert task_after.depends_on == task_before.depends_on
        assert task_after.blocked == task_before.blocked
        assert task_after.block_reason == task_before.block_reason
        assert task_after.claimed_at == task_before.claimed_at
        assert task_after.archival_reason == task_before.archival_reason
        assert task_after.archival_refs == task_before.archival_refs

        # Timestamps must round-trip in canonical +00:00 format (no quoting artefacts)
        frontmatter = _extract_frontmatter(written_path)
        ts_re = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")
        for line in frontmatter.splitlines():
            if ts_re.search(line):
                assert line.rstrip().endswith("+00:00"), (
                    f"Timestamp format broken after round-trip write: {line.rstrip()!r}"
                )


# ---------------------------------------------------------------------------
# TestFromAC_ArchiveClaimedByStripping
# ---------------------------------------------------------------------------


class TestFromAC_ArchiveClaimedByStripping:
    """AC 5 / AC-C48: read_task strips claimed_by from archive files.

    For the round-trip to be data-clean, read_task on an archive file
    containing the legacy 'claimed_by' field must return a Task where
    claimed_by is None (stripped), not 'some-agent' (preserved).

    All tests FAIL because read_task currently preserves claimed_by via
    extra='allow' instead of stripping it for archive files.
    """

    def test_archive_read_task_claimed_by_stripped_to_none(self, tmp_path: Path) -> None:
        """AC 5 / AC-C48: read_task on archive file returns claimed_by=None.

        Fails because read_task does not strip claimed_by from archive files;
        instead, 'some-agent' leaks through via Task.model_extra.
        """
        kanban_dir = _make_grouped_board(tmp_path)
        archive_path = _write_archive_with_claimed_by(kanban_dir, 5, "Archive with claimed_by")

        task = read_task(archive_path)
        dumped = task.model_dump()

        assert dumped.get("claimed_by") is None, (
            f"read_task must strip claimed_by from archive files; got {dumped.get('claimed_by')!r}"
        )

    def test_archive_read_task_claimed_by_not_in_model_extra(self, tmp_path: Path) -> None:
        """AC 5 / AC-C48: claimed_by must not appear in Task.model_extra for archive reads.

        Fails because Task.extra='allow' lets claimed_by persist in model_extra,
        which then appears in model_dump() and can silently propagate downstream.
        """
        kanban_dir = _make_grouped_board(tmp_path)
        archive_path = _write_archive_with_claimed_by(kanban_dir, 6, "claimed_by in extras")

        task = read_task(archive_path)

        assert "claimed_by" not in (task.model_extra or {}), (
            "claimed_by must not be in Task.model_extra after reading an archive file"
        )


# ---------------------------------------------------------------------------
# TestFromAC_TimestampRoundTrip
# ---------------------------------------------------------------------------


class TestFromAC_TimestampRoundTrip:
    """AC 5 / AC-C15: Timestamps are written as unquoted plain scalars ending with +00:00.

    write_task currently wraps timestamps in single quotes, so a line reads
    'created: '2026-..+00:00'' and endswith('+00:00') returns False.

    All tests FAIL because ruamel.yaml adds single-quote protection.
    """

    def test_write_task_timestamp_line_ends_with_utc_offset(self, tmp_path: Path) -> None:
        """AC 5 / AC-C15: Raw line for a UTC timestamp must end with +00:00 (not +00:00').

        Fails because write_task produces 'created: '2026-04-20T10:00:00+00:00''
        (single-quoted), so line.rstrip().endswith('+00:00') is False.
        """
        import re

        from owlbear_kanban.models import Task

        kanban_dir = _make_grouped_board(tmp_path)
        task = Task(
            id=1001,
            title="Timestamp format test",
            status="todo",
            priority="important",
            created="2026-04-20T10:00:00+00:00",
            updated="2026-04-20T11:00:00+00:00",
        )
        write_task(task, kanban_dir)

        task_files = list_task_files(kanban_dir)
        assert len(task_files) == 1
        frontmatter = _extract_frontmatter(task_files[0])

        ts_re = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")
        for line in frontmatter.splitlines():
            if ts_re.search(line):
                assert line.rstrip().endswith("+00:00"), (
                    f"Timestamp line must end with +00:00 (no surrounding quotes): {line.rstrip()!r}"
                )

    def test_write_task_naive_timestamp_stored_with_utc_offset_unquoted(self, tmp_path: Path) -> None:
        """AC 5 / AC-C15: Naive timestamp written by write_task ends with +00:00 (unquoted).

        write_task must normalise 'YYYY-MM-DDTHH:MM:SS' (no tz) to
        'YYYY-MM-DDTHH:MM:SS+00:00' AND write it without surrounding quotes.
        Fails because the timestamp is single-quoted in the output.
        """
        import re

        from owlbear_kanban.models import Task

        kanban_dir = _make_grouped_board(tmp_path)
        task = Task(
            id=1002,
            title="Naive timestamp test",
            status="todo",
            priority="important",
            created="2026-04-20T10:00:00",  # no timezone
            updated="2026-04-20T11:00:00",  # no timezone
        )
        write_task(task, kanban_dir)

        task_files = list_task_files(kanban_dir)
        assert len(task_files) == 1
        frontmatter = _extract_frontmatter(task_files[0])

        ts_re = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")
        for line in frontmatter.splitlines():
            if ts_re.search(line):
                assert line.rstrip().endswith("+00:00"), (
                    f"Naive timestamp must be normalised and unquoted, ending with +00:00: {line.rstrip()!r}"
                )

    def test_write_task_non_utc_timestamp_converted_unquoted(self, tmp_path: Path) -> None:
        """AC 5 / AC-C15: +02:00 timestamp converted to UTC and written unquoted.

        created: '2026-04-20T10:00:00+02:00' must become '2026-04-20T08:00:00+00:00'
        as a plain scalar.  Fails because the converted timestamp is single-quoted.
        """
        import re

        from owlbear_kanban.models import Task

        kanban_dir = _make_grouped_board(tmp_path)
        task = Task(
            id=1003,
            title="Non-UTC timestamp test",
            status="todo",
            priority="important",
            created="2026-04-20T10:00:00+02:00",
            updated="2026-04-20T12:00:00+02:00",
        )
        write_task(task, kanban_dir)

        task_files = list_task_files(kanban_dir)
        assert len(task_files) == 1
        frontmatter = _extract_frontmatter(task_files[0])

        ts_re = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")
        for line in frontmatter.splitlines():
            if ts_re.search(line):
                assert line.rstrip().endswith("+00:00"), (
                    f"+02:00 timestamp must be converted to UTC and written unquoted, "
                    f"ending with +00:00: {line.rstrip()!r}"
                )

        # Also verify the UTC-converted value itself
        assert "2026-04-20T08:00:00+00:00" in frontmatter, "created +02:00 must be converted to UTC 08:00+00:00"
        assert "2026-04-20T10:00:00+00:00" in frontmatter, "updated +02:00 must be converted to UTC 10:00+00:00"
