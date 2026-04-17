"""Failing tests for KanbanEngine.list_tasks() with filtering, sorting, and
pagination (#719, RED phase).

AC coverage:
  AC1 - list all tasks from tasks_dir
  AC2 - filter by status, tag, priority, blocked (tri-state), unclaimed
  AC3 - full-text search in titles and bodies
  AC4 - sort by priority, updated, id, title, status, created
  AC5 - reverse ordering
  AC6 - limit (pagination cap)
  AC7 - archived task listing
  AC8 - all tests fail

Import path: owlbear_mcp_kanban.engine (module does NOT exist yet).
All tests must FAIL — GREEN phase is task #720.
"""

from __future__ import annotations

from pathlib import Path

from owlbear_kanban import KanbanEngine

# ---------------------------------------------------------------------------
# Priority / status rank maps — derived from config.yml statuses/priorities
# ---------------------------------------------------------------------------

PRIORITY_RANK: dict[str, int] = {
    "someday": 0,
    "nice-to-have": 1,
    "important": 2,
    "needed": 3,
    "critical": 4,
}

STATUS_RANK: dict[str, int] = {
    "research": 0,
    "backlog": 1,
    "todo": 2,
    "in-progress": 3,
    "review": 4,
    "docs": 5,
    "done": 6,
}

# ---------------------------------------------------------------------------
# Fixtures / helpers
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
    """Return a kanban dir with config.yml, tasks/, and archive/ directories."""
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
    blocked: bool = False,
    block_reason: str | None = None,
    claimed_by: str | None = None,
    created: str = "2026-01-01T10:00:00.0000000+00:00",
    updated: str = "2026-01-02T10:00:00.0000000+00:00",
    body: str = "",
) -> str:
    """Build YAML frontmatter + markdown body string for a task file."""
    tags_yaml = "[" + ", ".join(f'"{t}"' for t in (tags or [])) + "]"
    br_yaml = f'"{block_reason}"' if block_reason else "null"
    cb_yaml = f'"{claimed_by}"' if claimed_by else "null"
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
        f"blocked: {'true' if blocked else 'false'}\n"
        f"block_reason: {br_yaml}\n"
        f"claimed_by: {cb_yaml}\n"
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
    **kwargs,
) -> Path:
    """Write a task file and return its path."""
    s = slug or title.lower().replace(" ", "-")[:30]
    path = kdir / subdir / f"{task_id}-{s}.md"
    path.write_text(_task_content(task_id, title, **kwargs), encoding="utf-8")
    return path


# ===========================================================================
# AC1 — list all tasks from tasks_dir
# ===========================================================================


class TestFromAC_ListAllTasks:
    def test_returns_all_task_files(self, tmp_path: Path) -> None:
        """list_tasks() returns one Task per file in tasks_dir."""
        kdir = _make_kanban_dir(tmp_path)
        _add_task(kdir, 1, "Alpha task")
        _add_task(kdir, 2, "Beta task")
        _add_task(kdir, 3, "Gamma task")

        engine = KanbanEngine(kdir)
        result = engine.list_tasks()

        assert len(result) == 3
        ids = {t.id for t in result}
        assert ids == {1, 2, 3}

    def test_empty_tasks_dir_returns_empty_list(self, tmp_path: Path) -> None:
        """list_tasks() returns [] when no task files exist."""
        kdir = _make_kanban_dir(tmp_path)

        engine = KanbanEngine(kdir)
        result = engine.list_tasks()

        assert result == []

    def test_result_items_are_task_records(self, tmp_path: Path) -> None:
        """list_tasks() returns list[TaskSummary] with correct field values."""
        from owlbear_kanban.models import TaskSummary

        kdir = _make_kanban_dir(tmp_path)
        _add_task(kdir, 5, "Field check task", status="review", priority="needed")

        engine = KanbanEngine(kdir)
        result = engine.list_tasks()

        assert len(result) == 1
        rec = result[0]
        assert isinstance(rec, TaskSummary)
        assert rec.id == 5
        assert rec.title == "Field check task"
        assert rec.status == "review"
        assert rec.priority == "needed"


# ===========================================================================
# AC2 — filter by status, tag, priority, blocked (tri-state), unclaimed
# ===========================================================================


class TestFromAC_FilterByStatus:
    def test_status_filter_returns_only_matching(self, tmp_path: Path) -> None:
        kdir = _make_kanban_dir(tmp_path)
        _add_task(kdir, 1, "Todo task", status="todo")
        _add_task(kdir, 2, "Done task", status="done")
        _add_task(kdir, 3, "Another todo", status="todo")

        engine = KanbanEngine(kdir)
        result = engine.list_tasks(status="todo")

        assert all(t.status == "todo" for t in result)
        assert len(result) == 2

    def test_status_filter_no_match_returns_empty(self, tmp_path: Path) -> None:
        kdir = _make_kanban_dir(tmp_path)
        _add_task(kdir, 1, "A task", status="todo")

        engine = KanbanEngine(kdir)
        result = engine.list_tasks(status="done")

        assert result == []

    def test_empty_status_returns_all(self, tmp_path: Path) -> None:
        """Empty string status means no filter — all tasks returned."""
        kdir = _make_kanban_dir(tmp_path)
        _add_task(kdir, 1, "Task one", status="todo")
        _add_task(kdir, 2, "Task two", status="done")

        engine = KanbanEngine(kdir)
        result = engine.list_tasks(status="")

        assert len(result) == 2


class TestFromAC_FilterByTag:
    def test_tag_filter_returns_tasks_with_tag(self, tmp_path: Path) -> None:
        kdir = _make_kanban_dir(tmp_path)
        _add_task(kdir, 1, "Tagged task", tags=["phase-3", "kanban"])
        _add_task(kdir, 2, "No match task", tags=["other"])
        _add_task(kdir, 3, "Also tagged", tags=["phase-3"])

        engine = KanbanEngine(kdir)
        result = engine.list_tasks(tag="phase-3")

        assert len(result) == 2
        assert all("phase-3" in t.tags for t in result)

    def test_tag_filter_no_match_returns_empty(self, tmp_path: Path) -> None:
        kdir = _make_kanban_dir(tmp_path)
        _add_task(kdir, 1, "Task", tags=["kanban"])

        engine = KanbanEngine(kdir)
        result = engine.list_tasks(tag="missing-tag")

        assert result == []


class TestFromAC_FilterByPriority:
    def test_priority_filter_returns_matching(self, tmp_path: Path) -> None:
        kdir = _make_kanban_dir(tmp_path)
        _add_task(kdir, 1, "Needed task", priority="needed")
        _add_task(kdir, 2, "Critical task", priority="critical")
        _add_task(kdir, 3, "Also needed", priority="needed")

        engine = KanbanEngine(kdir)
        result = engine.list_tasks(priority="needed")

        assert len(result) == 2
        assert all(t.priority == "needed" for t in result)

    def test_priority_filter_no_match_returns_empty(self, tmp_path: Path) -> None:
        kdir = _make_kanban_dir(tmp_path)
        _add_task(kdir, 1, "Important task", priority="important")

        engine = KanbanEngine(kdir)
        result = engine.list_tasks(priority="someday")

        assert result == []


class TestFromAC_FilterByBlocked:
    def test_blocked_true_returns_only_blocked(self, tmp_path: Path) -> None:
        kdir = _make_kanban_dir(tmp_path)
        _add_task(kdir, 1, "Blocked task", blocked=True, block_reason="waiting")
        _add_task(kdir, 2, "Free task", blocked=False)

        engine = KanbanEngine(kdir)
        result = engine.list_tasks(blocked=True)

        assert len(result) == 1
        assert result[0].blocked is True

    def test_blocked_false_returns_only_unblocked(self, tmp_path: Path) -> None:
        kdir = _make_kanban_dir(tmp_path)
        _add_task(kdir, 1, "Blocked task", blocked=True, block_reason="stuck")
        _add_task(kdir, 2, "Free task", blocked=False)

        engine = KanbanEngine(kdir)
        result = engine.list_tasks(blocked=False)

        assert len(result) == 1
        assert result[0].blocked is False

    def test_blocked_none_is_tri_state_no_filter(self, tmp_path: Path) -> None:
        """blocked=None (default) means no filter — returns both blocked and unblocked."""
        kdir = _make_kanban_dir(tmp_path)
        _add_task(kdir, 1, "Blocked task", blocked=True, block_reason="dep")
        _add_task(kdir, 2, "Free task", blocked=False)

        engine = KanbanEngine(kdir)
        result = engine.list_tasks(blocked=None)

        assert len(result) == 2


class TestFromAC_FilterByUnclaimed:
    def test_unclaimed_returns_only_tasks_without_claimed_by(self, tmp_path: Path) -> None:
        kdir = _make_kanban_dir(tmp_path)
        _add_task(kdir, 1, "Claimed task", claimed_by="river-port")
        _add_task(kdir, 2, "Free task")
        _add_task(kdir, 3, "Also free task")

        engine = KanbanEngine(kdir)
        result = engine.list_tasks(unclaimed=True)

        assert len(result) == 2
        assert all(t.claimed is False for t in result)

    def test_unclaimed_false_returns_all_tasks(self, tmp_path: Path) -> None:
        """unclaimed=False means no filter — claimed and unclaimed both included."""
        kdir = _make_kanban_dir(tmp_path)
        _add_task(kdir, 1, "Claimed task", claimed_by="drift-vault")
        _add_task(kdir, 2, "Free task")

        engine = KanbanEngine(kdir)
        result = engine.list_tasks(unclaimed=False)

        assert len(result) == 2


# ===========================================================================
# AC3 — full-text search in titles and bodies
# ===========================================================================


class TestFromAC_FullTextSearch:
    def test_search_matches_title(self, tmp_path: Path) -> None:
        kdir = _make_kanban_dir(tmp_path)
        _add_task(kdir, 1, "Implement engine bootstrap")
        _add_task(kdir, 2, "Fix pagination bug")

        engine = KanbanEngine(kdir)
        result = engine.list_tasks(search="bootstrap")

        assert len(result) == 1
        assert result[0].id == 1

    def test_search_matches_body(self, tmp_path: Path) -> None:
        kdir = _make_kanban_dir(tmp_path)
        _add_task(kdir, 1, "Task alpha", body="## Objective\nRefactor the pipeline.\n")
        _add_task(kdir, 2, "Task beta", body="## Notes\nFix unrelated bug.\n")

        engine = KanbanEngine(kdir)
        result = engine.list_tasks(search="Refactor")

        assert len(result) == 1
        assert result[0].id == 1

    def test_search_no_match_returns_empty(self, tmp_path: Path) -> None:
        kdir = _make_kanban_dir(tmp_path)
        _add_task(kdir, 1, "Implement feature", body="Some body text.\n")

        engine = KanbanEngine(kdir)
        result = engine.list_tasks(search="xyznomatch")

        assert result == []

    def test_search_matches_both_title_and_body_tasks(self, tmp_path: Path) -> None:
        """Search returns tasks matching in either title OR body."""
        kdir = _make_kanban_dir(tmp_path)
        _add_task(kdir, 1, "native engine task")
        _add_task(kdir, 2, "Other task", body="## AC\nBuild native support.\n")
        _add_task(kdir, 3, "Unrelated work")

        engine = KanbanEngine(kdir)
        result = engine.list_tasks(search="native")

        assert len(result) == 2
        assert {t.id for t in result} == {1, 2}


# ===========================================================================
# AC4 — sort by priority, updated, id, title, status, created
# ===========================================================================


class TestFromAC_SortByField:
    def test_sort_by_id(self, tmp_path: Path) -> None:
        kdir = _make_kanban_dir(tmp_path)
        _add_task(kdir, 30, "C task")
        _add_task(kdir, 10, "A task")
        _add_task(kdir, 20, "B task")

        engine = KanbanEngine(kdir)
        result = engine.list_tasks(sort="id")

        assert [t.id for t in result] == [10, 20, 30]

    def test_sort_by_title_alphabetical(self, tmp_path: Path) -> None:
        kdir = _make_kanban_dir(tmp_path)
        _add_task(kdir, 1, "Zeta work")
        _add_task(kdir, 2, "Alpha work")
        _add_task(kdir, 3, "Mu work")

        engine = KanbanEngine(kdir)
        result = engine.list_tasks(sort="title")

        assert [t.title for t in result] == ["Alpha work", "Mu work", "Zeta work"]

    def test_sort_by_status_uses_config_order(self, tmp_path: Path) -> None:
        """Status sort uses config.yml statuses order, not alphabetical."""
        kdir = _make_kanban_dir(tmp_path)
        _add_task(kdir, 1, "Done task", status="done")
        _add_task(kdir, 2, "Research task", status="research")
        _add_task(kdir, 3, "Todo task", status="todo")

        engine = KanbanEngine(kdir)
        result = engine.list_tasks(sort="status")

        statuses = [t.status for t in result]
        # research → todo → done (index order in config, not alphabetical)
        assert [STATUS_RANK[s] for s in statuses] == sorted(STATUS_RANK[s] for s in statuses)

    def test_sort_by_priority_uses_config_rank(self, tmp_path: Path) -> None:
        """Priority sort uses config.yml priorities rank, not alphabetical.

        Alphabetical order would be: critical, important, needed, nice-to-have, someday.
        Config rank order:           someday, nice-to-have, important, needed, critical.
        These two orders differ — the test catches alphabetical vs rank bugs.
        """
        kdir = _make_kanban_dir(tmp_path)
        _add_task(kdir, 1, "Critical task", priority="critical")
        _add_task(kdir, 2, "Someday task", priority="someday")
        _add_task(kdir, 3, "Needed task", priority="needed")

        engine = KanbanEngine(kdir)
        result = engine.list_tasks(sort="priority")

        priorities = [t.priority for t in result]
        ranks = [PRIORITY_RANK[p] for p in priorities]
        assert ranks == sorted(ranks)
        # Verify it's NOT alphabetical (critical < important alphabetically, but critical=4 by rank)
        assert priorities[0] == "someday"

    def test_sort_by_created(self, tmp_path: Path) -> None:
        kdir = _make_kanban_dir(tmp_path)
        _add_task(kdir, 1, "Newest", created="2026-03-01T10:00:00.0000000+00:00")
        _add_task(kdir, 2, "Oldest", created="2026-01-01T10:00:00.0000000+00:00")
        _add_task(kdir, 3, "Middle", created="2026-02-01T10:00:00.0000000+00:00")

        engine = KanbanEngine(kdir)
        result = engine.list_tasks(sort="created")

        assert [t.id for t in result] == [2, 3, 1]

    def test_sort_by_updated(self, tmp_path: Path) -> None:
        kdir = _make_kanban_dir(tmp_path)
        _add_task(kdir, 1, "Old update", updated="2026-01-05T10:00:00.0000000+00:00")
        _add_task(kdir, 2, "New update", updated="2026-03-05T10:00:00.0000000+00:00")
        _add_task(kdir, 3, "Mid update", updated="2026-02-05T10:00:00.0000000+00:00")

        engine = KanbanEngine(kdir)
        result = engine.list_tasks(sort="updated")

        assert [t.id for t in result] == [1, 3, 2]

    # -----------------------------------------------------------------------
    # AC1 — sort by created with mixed timezone offsets (#815)
    # -----------------------------------------------------------------------

    def test_sort_by_created_mixed_tz_offsets(self, tmp_path: Path) -> None:
        """AC1: created sort uses UTC order, not string order, with mixed TZ offsets.

        Task 1: 2026-01-01T12:00:00+02:00 == 10:00 UTC (earlier — should rank first)
        Task 2: 2026-01-01T11:00:00+00:00 == 11:00 UTC (later  — should rank second)
        String sort orders by numeric hour digit: "11..." < "12..." → wrong [2, 1].
        Correct UTC sort: [1, 2].
        """
        kdir = _make_kanban_dir(tmp_path)
        _add_task(
            kdir,
            1,
            "Earlier UTC",
            created="2026-01-01T12:00:00.0000000+02:00",
        )
        _add_task(
            kdir,
            2,
            "Later UTC",
            created="2026-01-01T11:00:00.0000000+00:00",
        )

        engine = KanbanEngine(kdir)
        result = engine.list_tasks(sort="created")

        assert [t.id for t in result] == [1, 2]

    # -----------------------------------------------------------------------
    # AC2 — sort by updated with mixed timezone offsets (#815)
    # -----------------------------------------------------------------------

    def test_sort_by_updated_mixed_tz_offsets(self, tmp_path: Path) -> None:
        """AC2: updated sort uses UTC order, not string order, with mixed TZ offsets.

        Task 1: 2026-02-01T12:00:00+02:00 == 10:00 UTC (earlier — should rank first)
        Task 2: 2026-02-01T11:00:00+00:00 == 11:00 UTC (later  — should rank second)
        String sort orders by hour digit: "11..." < "12..." → wrong [2, 1].
        Correct UTC sort: [1, 2].
        """
        kdir = _make_kanban_dir(tmp_path)
        _add_task(
            kdir,
            1,
            "Earlier UTC updated",
            updated="2026-02-01T12:00:00.0000000+02:00",
        )
        _add_task(
            kdir,
            2,
            "Later UTC updated",
            updated="2026-02-01T11:00:00.0000000+00:00",
        )

        engine = KanbanEngine(kdir)
        result = engine.list_tasks(sort="updated")

        assert [t.id for t in result] == [1, 2]

    # -----------------------------------------------------------------------
    # AC3 — mixed Go 7-digit and Python 6-digit precision formats (#815)
    # -----------------------------------------------------------------------

    def test_sort_by_created_mixed_precision_formats(self, tmp_path: Path) -> None:
        """AC3: sort handles Go 7-digit nanosecond and Python 6-digit microsecond formats.

        Task 1: Go format    2026-01-01T12:00:00.1234567+02:00 == 10:00 UTC (earlier)
        Task 2: Python format 2026-01-01T11:00:00.123456+00:00 == 11:00 UTC (later)
        String sort: "11..." < "12..." → wrong [2, 1].
        Correct UTC sort: [1, 2].
        """
        kdir = _make_kanban_dir(tmp_path)
        _add_task(
            kdir,
            1,
            "Go fmt earlier UTC",
            created="2026-01-01T12:00:00.1234567+02:00",
        )
        _add_task(
            kdir,
            2,
            "Python fmt later UTC",
            created="2026-01-01T11:00:00.123456+00:00",
        )

        engine = KanbanEngine(kdir)
        result = engine.list_tasks(sort="created")

        assert [t.id for t in result] == [1, 2]

    # -----------------------------------------------------------------------
    # AC4 — stored timestamp strings unchanged after datetime-based sort (#815)
    # -----------------------------------------------------------------------

    def test_sort_round_trip_string_fidelity(self, tmp_path: Path) -> None:
        """AC4: list_tasks() returns the exact stored timestamp string — no mutation.

        The sort key uses datetime.fromisoformat() for comparison only.
        The stored Go 7-digit string must survive the round-trip unchanged:
        7th digit must not be truncated, TZ offset must not be normalised.

        This test also asserts correct UTC order so it fails RED:
        Task 1: 2026-01-15T12:00:00.1234567+02:00 == 10:00 UTC (earlier)
        Task 2: 2026-01-15T11:00:00.000000+00:00  == 11:00 UTC (later)
        String sort: [2, 1] (wrong).  Correct UTC sort: [1, 2].
        """
        go_ts = "2026-01-15T12:00:00.1234567+02:00"  # Go 7-digit, 10:00 UTC
        py_ts = "2026-01-15T11:00:00.000000+00:00"  # Python 6-digit, 11:00 UTC

        kdir = _make_kanban_dir(tmp_path)
        _add_task(kdir, 1, "Go fmt round trip", created=go_ts)
        _add_task(kdir, 2, "Python fmt round trip", created=py_ts)

        engine = KanbanEngine(kdir)
        result = engine.list_tasks(sort="created")

        # Correct UTC chronological order — FAILS RED with string sort
        assert [t.id for t in result] == [1, 2]
        # Go 7-digit string preserved exactly (not truncated to 6-digit µs).
        # show_task() returns Task (not TaskSummary), which carries created/updated.
        task1_full = engine.show_task("1")
        assert task1_full.created == go_ts


# ===========================================================================
# AC5 — reverse ordering
# ===========================================================================


class TestFromAC_ReverseOrdering:
    def test_reverse_inverts_default_id_order(self, tmp_path: Path) -> None:
        kdir = _make_kanban_dir(tmp_path)
        for i in [1, 2, 3]:
            _add_task(kdir, i, f"Task {i}")

        engine = KanbanEngine(kdir)
        fwd = engine.list_tasks(sort="id", reverse=False)
        rev = engine.list_tasks(sort="id", reverse=True)

        assert [t.id for t in fwd] == [1, 2, 3]
        assert [t.id for t in rev] == [3, 2, 1]

    def test_reverse_with_priority_sort(self, tmp_path: Path) -> None:
        """reverse=True + sort=priority yields highest-priority first."""
        kdir = _make_kanban_dir(tmp_path)
        _add_task(kdir, 1, "Someday task", priority="someday")
        _add_task(kdir, 2, "Critical task", priority="critical")
        _add_task(kdir, 3, "Important task", priority="important")

        engine = KanbanEngine(kdir)
        result = engine.list_tasks(sort="priority", reverse=True)

        priorities = [t.priority for t in result]
        ranks = [PRIORITY_RANK[p] for p in priorities]
        assert ranks == sorted(ranks, reverse=True)
        assert priorities[0] == "critical"


# ===========================================================================
# AC6 — limit (pagination cap)
# ===========================================================================


class TestFromAC_LimitPagination:
    def test_limit_caps_result_count(self, tmp_path: Path) -> None:
        kdir = _make_kanban_dir(tmp_path)
        for i in range(1, 6):
            _add_task(kdir, i, f"Task {i}")

        engine = KanbanEngine(kdir)
        result = engine.list_tasks(sort="id", limit=3)

        assert len(result) == 3

    def test_limit_zero_means_no_cap(self, tmp_path: Path) -> None:
        """limit=0 is the sentinel for unlimited — returns all tasks."""
        kdir = _make_kanban_dir(tmp_path)
        for i in range(1, 6):
            _add_task(kdir, i, f"Task {i}")

        engine = KanbanEngine(kdir)
        result = engine.list_tasks(sort="id", limit=0)

        assert len(result) == 5

    def test_limit_greater_than_count_returns_all(self, tmp_path: Path) -> None:
        """limit larger than total task count returns all tasks without error."""
        kdir = _make_kanban_dir(tmp_path)
        _add_task(kdir, 1, "Only task")

        engine = KanbanEngine(kdir)
        result = engine.list_tasks(limit=100)

        assert len(result) == 1


# ===========================================================================
# AC7 — archived task listing
# ===========================================================================


class TestFromAC_ArchivedTasks:
    def test_default_excludes_archive_dir_tasks(self, tmp_path: Path) -> None:
        """list_tasks() default (archived=False) does not include archive/ tasks."""
        kdir = _make_kanban_dir(tmp_path)
        _add_task(kdir, 1, "Live task", subdir="tasks")
        _add_task(kdir, 2, "Archived task", subdir="archive")

        engine = KanbanEngine(kdir)
        result = engine.list_tasks()

        assert len(result) == 1
        assert result[0].id == 1

    def test_archived_true_returns_tasks_from_archive_dir(self, tmp_path: Path) -> None:
        """list_tasks(archived=True) reads tasks from archive/ directory."""
        kdir = _make_kanban_dir(tmp_path)
        _add_task(kdir, 1, "Live task", subdir="tasks")
        _add_task(kdir, 2, "Archived task A", subdir="archive")
        _add_task(kdir, 3, "Archived task B", subdir="archive")

        engine = KanbanEngine(kdir)
        result = engine.list_tasks(archived=True)

        assert len(result) == 2
        assert all(t.id in {2, 3} for t in result)

    def test_archived_true_does_not_include_live_tasks(self, tmp_path: Path) -> None:
        """archived=True returns only archived tasks, not live tasks."""
        kdir = _make_kanban_dir(tmp_path)
        _add_task(kdir, 1, "Live task", subdir="tasks")
        _add_task(kdir, 2, "Archived task", subdir="archive")

        engine = KanbanEngine(kdir)
        result = engine.list_tasks(archived=True)

        ids = {t.id for t in result}
        assert 1 not in ids
        assert 2 in ids

    def test_archived_true_empty_archive_returns_empty(self, tmp_path: Path) -> None:
        """archived=True returns [] when archive/ is empty."""
        kdir = _make_kanban_dir(tmp_path)
        _add_task(kdir, 1, "Live task", subdir="tasks")

        engine = KanbanEngine(kdir)
        result = engine.list_tasks(archived=True)

        assert result == []
