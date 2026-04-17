"""Tests for timestamp sort fix — KanbanEngine sort by created/updated (#816, RED phase).

AC coverage:
  AC1 — sort by created/updated parses timestamps to datetime via fromisoformat()
  AC2 — handles both Go 7-digit nanosecond and Python 6-digit microsecond format
  AC3 — stored timestamp string unchanged after sort (show_task round-trip fidelity)
  AC4 — correct UTC chronological ordering across mixed timezone offsets

NOTE: TDD RED waiver — implementation (engine.py L252-255) was applied during
research/validation alongside #815 tests. These tests serve as the verification
contract for the builder. See task #816 architecture review notes.
"""

from __future__ import annotations

from pathlib import Path

from owlbear_kanban import KanbanEngine

# ---------------------------------------------------------------------------
# Helpers
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
    class: standard
claim_timeout: 1h
next_id: 100
"""


def _make_kanban_dir(tmp: Path) -> Path:
    kdir = tmp / "kanban"
    kdir.mkdir()
    (kdir / "tasks").mkdir()
    (kdir / "archive").mkdir()
    (kdir / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
    return kdir


def _task_content(  # noqa: PLR0913
    task_id: int,
    title: str,
    *,
    status: str = "todo",
    priority: str = "important",
    tags: list[str] | None = None,
    created: str = "2026-01-01T10:00:00.0000000+00:00",
    updated: str = "2026-01-02T10:00:00.0000000+00:00",
    body: str = "",
) -> str:
    tags_yaml = "[" + ", ".join(f'"{t}"' for t in (tags or [])) + "]"
    return (
        "---\n"
        f"id: {task_id}\n"
        f"title: {title!r}\n"
        f"status: {status}\n"
        f"priority: {priority}\n"
        f"created: {created}\n"
        f"updated: {updated}\n"
        f"tags: {tags_yaml}\n"
        "parent: null\n"
        "depends_on: []\n"
        "blocked: false\n"
        "block_reason: null\n"
        "claimed_by: null\n"
        "claimed_at: null\n"
        "---\n"
        f"{body}"
    )


def _add_task(
    kdir: Path,
    task_id: int,
    title: str,
    *,
    subdir: str = "tasks",
    slug: str | None = None,
    **kwargs: object,
) -> Path:
    s = slug or title.lower().replace(" ", "-")[:30]
    path = kdir / subdir / f"{task_id}-{s}.md"
    path.write_text(_task_content(task_id, title, **kwargs), encoding="utf-8")
    return path


# ===========================================================================
# TestFromAC_TimestampSort - AC1-AC4
# ===========================================================================


class TestFromAC_TimestampSort:
    # -----------------------------------------------------------------------
    # AC2 — Go 7-digit nanosecond format on the updated field
    # -----------------------------------------------------------------------

    def test_sort_by_updated_go_format_correct_order(self, tmp_path: Path) -> None:
        """AC2: sort by updated handles Go 7-digit nanosecond format.

        Task 1 updated: Go format 2026-02-01T12:00:00.1234567+02:00 == 10:00 UTC (earlier)
        Task 2 updated: Python    2026-02-01T11:00:00.123456+00:00   == 11:00 UTC (later)
        String sort: "11..." < "12..." → wrong order [2, 1].
        Correct UTC sort with fromisoformat(): [1, 2].
        """
        kdir = _make_kanban_dir(tmp_path)
        _add_task(kdir, 1, "Go format earlier UTC", updated="2026-02-01T12:00:00.1234567+02:00")
        _add_task(kdir, 2, "Python format later UTC", updated="2026-02-01T11:00:00.123456+00:00")

        engine = KanbanEngine(kdir)
        result = engine.list_tasks(sort="updated")

        assert [t.id for t in result] == [1, 2]

    # -----------------------------------------------------------------------
    # AC3 — stored string unchanged after datetime-based sort (show_task)
    # -----------------------------------------------------------------------

    def test_sort_round_trip_created_fidelity_via_show_task(self, tmp_path: Path) -> None:
        """AC3: list_tasks() sort does not mutate the stored created timestamp.

        The sort key uses datetime.fromisoformat() for comparison only — the
        original Go 7-digit string must be preserved verbatim in the task file.
        show_task() returns Task (not TaskSummary) which retains created/updated
        as plain strings per the no-mutation model design.
        """
        go_ts = "2026-01-15T12:00:00.1234567+02:00"  # Go 7-digit, 10:00 UTC

        kdir = _make_kanban_dir(tmp_path)
        _add_task(kdir, 1, "Go created round trip", created=go_ts)
        _add_task(kdir, 2, "Reference task", created="2026-01-15T11:00:00.000000+00:00")

        engine = KanbanEngine(kdir)
        engine.list_tasks(sort="created")  # trigger sort; must not mutate files

        task = engine.show_task("1")

        assert task.created == go_ts

    def test_sort_round_trip_updated_fidelity_via_show_task(self, tmp_path: Path) -> None:
        """AC3: list_tasks() sort does not mutate the stored updated timestamp.

        The exact Go format timestamp from the AC specification must survive
        a sort cycle unchanged — no digit truncation, no TZ normalisation.
        """
        go_ts = "2026-04-09T03:24:26.6974428+02:00"  # canonical Go example from AC

        kdir = _make_kanban_dir(tmp_path)
        _add_task(kdir, 1, "Go updated round trip", updated=go_ts)
        _add_task(kdir, 2, "Reference task", updated="2026-04-09T02:00:00.000000+00:00")

        engine = KanbanEngine(kdir)
        engine.list_tasks(sort="updated")  # trigger sort; must not mutate files

        task = engine.show_task("1")

        assert task.updated == go_ts

    def test_sort_does_not_expose_created_in_list_result(self, tmp_path: Path) -> None:
        """AC3: TaskSummary from list_tasks() has no created/updated attributes.

        The implementation sorts on internal Task objects then converts to
        TaskSummary (which intentionally drops created/updated). This test
        verifies the sort-key-only contract: timestamps are never surfaced in
        list results.
        """
        kdir = _make_kanban_dir(tmp_path)
        _add_task(kdir, 1, "Task", created="2026-01-15T12:00:00.1234567+02:00")

        engine = KanbanEngine(kdir)
        result = engine.list_tasks(sort="created")

        assert len(result) == 1
        assert not hasattr(result[0], "created")
        assert not hasattr(result[0], "updated")

    # -----------------------------------------------------------------------
    # AC4 — correct ordering across mixed timezone offsets (boundary cases)
    # -----------------------------------------------------------------------

    def test_sort_by_created_three_tasks_mixed_tz(self, tmp_path: Path) -> None:
        """AC4: 3-task sort with extreme positive, negative, and UTC offsets.

        UTC equivalents:
          Task 1: 2026-01-01T00:00:00+14:00 == 2025-12-31T10:00:00Z (earliest)
          Task 2: 2026-01-01T00:00:00-12:00 == 2026-01-01T12:00:00Z (latest)
          Task 3: 2026-01-01T10:00:00+00:00 == 2026-01-01T10:00:00Z (middle)
        Correct UTC order: [1, 3, 2].
        """
        kdir = _make_kanban_dir(tmp_path)
        _add_task(kdir, 1, "Extreme positive TZ", created="2026-01-01T00:00:00.000000+14:00")
        _add_task(kdir, 2, "Extreme negative TZ", created="2026-01-01T00:00:00.000000-12:00")
        _add_task(kdir, 3, "UTC reference", created="2026-01-01T10:00:00.000000+00:00")

        engine = KanbanEngine(kdir)
        result = engine.list_tasks(sort="created")

        assert [t.id for t in result] == [1, 3, 2]

    def test_sort_by_updated_negative_tz_offset(self, tmp_path: Path) -> None:
        """AC4: updated sort with negative timezone offset produces correct UTC order.

        Task 1 updated: 2026-03-15T08:00:00.000000-05:00 == 13:00 UTC (later)
        Task 2 updated: 2026-03-15T10:00:00.000000+00:00 == 10:00 UTC (earlier)
        String sort: "08..." < "10..." → wrong [1, 2].
        Correct UTC sort: [2, 1].
        """
        kdir = _make_kanban_dir(tmp_path)
        _add_task(kdir, 1, "Negative TZ later UTC", updated="2026-03-15T08:00:00.000000-05:00")
        _add_task(kdir, 2, "UTC reference earlier", updated="2026-03-15T10:00:00.000000+00:00")

        engine = KanbanEngine(kdir)
        result = engine.list_tasks(sort="updated")

        assert [t.id for t in result] == [2, 1]

    def test_sort_by_created_negative_tz_go_format(self, tmp_path: Path) -> None:
        """AC4+AC2: created sort with Go 7-digit format and negative TZ offset.

        Task 1 created: 2026-05-20T06:30:00.0000000-08:00 == 14:30 UTC (later)
        Task 2 created: 2026-05-20T12:00:00.0000000+00:00 == 12:00 UTC (earlier)
        String sort: "06..." < "12..." → wrong [1, 2].
        Correct UTC sort: [2, 1].
        """
        kdir = _make_kanban_dir(tmp_path)
        _add_task(kdir, 1, "Negative TZ Go format", created="2026-05-20T06:30:00.0000000-08:00")
        _add_task(kdir, 2, "UTC noon reference", created="2026-05-20T12:00:00.0000000+00:00")

        engine = KanbanEngine(kdir)
        result = engine.list_tasks(sort="created")

        assert [t.id for t in result] == [2, 1]
