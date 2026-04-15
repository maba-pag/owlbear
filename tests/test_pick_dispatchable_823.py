"""Failing tests for pick_dispatchable() engine function (#823, RED phase).

AC coverage:
  AC1 — pick_dispatchable(engine, limit=25, tag="") returns list[Task]
  AC2 — TDD gate: in-progress task without test-writer notes or non-impl tag is excluded
  AC3 — Clarity gate: active-status task without bullet/numbered AC is excluded
  AC4 — Priority ranking: critical > needed > important > nice-to-have > someday
  AC5 — Status ranking: done > docs > review > in-progress > todo > backlog > research (archived excluded)
  AC6 — Result capping at limit
  AC7 — Tag filtering
  AC8 — Importable without MCP dependency
  AC9 — All tests fail RED before implementation

Import path: owlbear_kanban.dispatch (module does NOT exist yet — all tests fail
with ImportError until the GREEN phase builder creates it).
"""

from __future__ import annotations

from pathlib import Path

import owlbear_kanban.dispatch as _dispatch_mod
from owlbear_kanban import KanbanEngine
from owlbear_kanban.dispatch import pick_dispatchable
from owlbear_kanban.models import Task

# ---------------------------------------------------------------------------
# Fixtures / helpers  (real-engine + temp-filesystem pattern)
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
    kdir.mkdir(parents=True, exist_ok=True)
    (kdir / "tasks").mkdir(exist_ok=True)
    (kdir / "archive").mkdir(exist_ok=True)
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
# AC8 — Importable without MCP dependency
# ===========================================================================


class TestFromAC_PickDispatchableImport:
    def test_pick_dispatchable_callable(self) -> None:
        """pick_dispatchable is a callable importable from owlbear_kanban.dispatch."""
        assert callable(pick_dispatchable)

    def test_module_is_in_owlbear_kanban_package(self) -> None:
        """dispatch module belongs to the owlbear_kanban package, not mcp-kanban."""
        assert _dispatch_mod.__package__ == "owlbear_kanban"

    def test_dispatch_module_does_not_import_mcp(self) -> None:
        """owlbear_kanban.dispatch must not import mcp or owlbear_mcp_kanban at module level."""
        mcp_names = {"mcp", "fastmcp", "owlbear_mcp_kanban"}
        module_globals = vars(_dispatch_mod)
        for name in mcp_names:
            assert name not in module_globals, (
                f"dispatch module imports {name!r} — must have no MCP dependency"
            )


# ===========================================================================
# AC1 — returns list[Task]
# ===========================================================================


class TestFromAC_PickDispatchableSignature:
    def test_returns_list(self, tmp_path: Path) -> None:
        """pick_dispatchable returns a list."""
        kdir = _make_kanban_dir(tmp_path)
        engine = KanbanEngine(kdir)
        result = pick_dispatchable(engine)
        assert isinstance(result, list)

    def test_result_items_are_task_instances(self, tmp_path: Path) -> None:
        """Result items are Task model instances (have a .body attribute)."""
        kdir = _make_kanban_dir(tmp_path)
        _add_task(kdir, 1, "Task A", status="todo", body="- some AC")
        engine = KanbanEngine(kdir)
        result = pick_dispatchable(engine)
        assert len(result) >= 1
        assert isinstance(result[0], Task)
        assert hasattr(result[0], "body")

    def test_accepts_limit_keyword(self, tmp_path: Path) -> None:
        """Accepts limit as a keyword argument without raising."""
        kdir = _make_kanban_dir(tmp_path)
        engine = KanbanEngine(kdir)
        result = pick_dispatchable(engine, limit=10)
        assert isinstance(result, list)

    def test_accepts_tag_keyword(self, tmp_path: Path) -> None:
        """Accepts tag as a keyword argument without raising."""
        kdir = _make_kanban_dir(tmp_path)
        engine = KanbanEngine(kdir)
        result = pick_dispatchable(engine, tag="")
        assert isinstance(result, list)

    def test_result_has_body_field(self, tmp_path: Path) -> None:
        """Returned Task objects expose the body field (not stripped like TaskSummary)."""
        kdir = _make_kanban_dir(tmp_path)
        body_content = "## AC\n- implement login\n"
        _add_task(kdir, 1, "Has body", status="todo", body=body_content)
        engine = KanbanEngine(kdir)
        result = pick_dispatchable(engine)
        task = next(t for t in result if t.id == 1)
        assert task.body == body_content


# ===========================================================================
# AC2 — TDD gate
# ===========================================================================


class TestFromAC_PickDispatchableTDDGate:
    def test_in_progress_without_notes_excluded(self, tmp_path: Path) -> None:
        """in-progress task without ## Test-Writer Notes and no non-impl tag is excluded."""
        kdir = _make_kanban_dir(tmp_path)
        # Body has bullets (passes clarity gate) but no notes (fails TDD gate)
        _add_task(
            kdir, 1, "Impl task",
            status="in-progress",
            body="- implement the feature\n- write tests",
        )
        engine = KanbanEngine(kdir)
        result = pick_dispatchable(engine)
        ids = {t.id for t in result}
        assert 1 not in ids

    def test_in_progress_with_notes_included(self, tmp_path: Path) -> None:
        """in-progress task containing ## Test-Writer Notes in body passes TDD gate."""
        kdir = _make_kanban_dir(tmp_path)
        _add_task(
            kdir, 2, "Ready impl",
            status="in-progress",
            body="## Test-Writer Notes\n- 5 tests written, all fail",
        )
        engine = KanbanEngine(kdir)
        result = pick_dispatchable(engine)
        ids = {t.id for t in result}
        assert 2 in ids

    def test_in_progress_non_impl_tag_exempt_from_tdd(self, tmp_path: Path) -> None:
        """in-progress task with a non-impl tag is exempt from the TDD gate."""
        kdir = _make_kanban_dir(tmp_path)
        _add_task(
            kdir, 3, "Doc task",
            status="in-progress",
            tags=["type:docs"],
            body="- update the README section",
        )
        engine = KanbanEngine(kdir)
        result = pick_dispatchable(engine)
        ids = {t.id for t in result}
        assert 3 in ids

    def test_non_in_progress_skips_tdd_gate(self, tmp_path: Path) -> None:
        """TDD gate only applies to in-progress status; todo without notes passes."""
        kdir = _make_kanban_dir(tmp_path)
        _add_task(kdir, 4, "Todo task", status="todo", body="- implement feature")
        engine = KanbanEngine(kdir)
        result = pick_dispatchable(engine)
        ids = {t.id for t in result}
        assert 4 in ids

    def test_all_non_impl_tags_exempt_from_tdd_gate(self, tmp_path: Path) -> None:
        """Every non-impl tag value exempts an in-progress task from the TDD gate."""
        non_impl_tags = [
            "research", "docs", "type:config", "type:docs", "test",
            "type:test", "agent", "quality", "type:user-action",
        ]
        for i, tag_value in enumerate(non_impl_tags, start=10):
            board_dir = tmp_path / f"board_{i}"
            kdir = _make_kanban_dir(board_dir)
            _add_task(
                kdir, i, f"Task {i}",
                status="in-progress",
                tags=[tag_value],
                body="- AC item",
            )
            engine = KanbanEngine(kdir)
            result = pick_dispatchable(engine)
            ids = {t.id for t in result}
            assert i in ids, f"non-impl tag '{tag_value}' should exempt task from TDD gate"


# ===========================================================================
# AC3 — Clarity gate
# ===========================================================================


class TestFromAC_PickDispatchableClarityGate:
    def test_todo_without_bullets_excluded(self, tmp_path: Path) -> None:
        """todo task with prose-only body (no bullets/numbered list) is excluded."""
        kdir = _make_kanban_dir(tmp_path)
        _add_task(kdir, 1, "Needs AC", status="todo", body="No structured criteria here")
        engine = KanbanEngine(kdir)
        result = pick_dispatchable(engine)
        ids = {t.id for t in result}
        assert 1 not in ids

    def test_todo_empty_body_excluded(self, tmp_path: Path) -> None:
        """todo task with empty body is excluded by clarity gate."""
        kdir = _make_kanban_dir(tmp_path)
        _add_task(kdir, 2, "No body", status="todo", body="")
        engine = KanbanEngine(kdir)
        result = pick_dispatchable(engine)
        ids = {t.id for t in result}
        assert 2 not in ids

    def test_todo_with_bullet_list_included(self, tmp_path: Path) -> None:
        """todo task with `- item` bullet line passes clarity gate."""
        kdir = _make_kanban_dir(tmp_path)
        _add_task(kdir, 3, "Has bullets", status="todo", body="## AC\n- implement login\n")
        engine = KanbanEngine(kdir)
        result = pick_dispatchable(engine)
        ids = {t.id for t in result}
        assert 3 in ids

    def test_todo_with_numbered_list_included(self, tmp_path: Path) -> None:
        """todo task with `1. item` numbered list passes clarity gate."""
        kdir = _make_kanban_dir(tmp_path)
        _add_task(kdir, 4, "Has numbered", status="todo", body="1. implement\n2. verify")
        engine = KanbanEngine(kdir)
        result = pick_dispatchable(engine)
        ids = {t.id for t in result}
        assert 4 in ids

    def test_research_without_bullets_passes_clarity(self, tmp_path: Path) -> None:
        """research status is not subject to clarity gate — prose body is accepted."""
        kdir = _make_kanban_dir(tmp_path)
        _add_task(kdir, 5, "Research task", status="research", body="Just prose notes")
        engine = KanbanEngine(kdir)
        result = pick_dispatchable(engine)
        ids = {t.id for t in result}
        assert 5 in ids

    def test_backlog_without_bullets_passes_clarity(self, tmp_path: Path) -> None:
        """backlog status is not subject to clarity gate."""
        kdir = _make_kanban_dir(tmp_path)
        _add_task(kdir, 6, "Backlog task", status="backlog", body="")
        engine = KanbanEngine(kdir)
        result = pick_dispatchable(engine)
        ids = {t.id for t in result}
        assert 6 in ids

    def test_done_with_bullets_dispatched(self, tmp_path: Path) -> None:
        """done tasks with AC bullets are dispatchable (auditor needs them)."""
        kdir = _make_kanban_dir(tmp_path)
        _add_task(kdir, 7, "Done with bullets", status="done", body="- AC item")
        engine = KanbanEngine(kdir)
        result = pick_dispatchable(engine)
        ids = {t.id for t in result}
        assert 7 in ids

    def test_review_without_bullets_excluded(self, tmp_path: Path) -> None:
        """review status is in the active set; prose-only body fails clarity gate."""
        kdir = _make_kanban_dir(tmp_path)
        _add_task(kdir, 8, "Review no bullets", status="review", body="Plain text only")
        engine = KanbanEngine(kdir)
        result = pick_dispatchable(engine)
        ids = {t.id for t in result}
        assert 8 not in ids


# ===========================================================================
# AC4 — Priority ranking: critical > needed > important > nice-to-have > someday
# ===========================================================================


class TestFromAC_PickDispatchablePriorityRanking:
    def test_critical_before_someday(self, tmp_path: Path) -> None:
        """critical priority appears before someday in dispatch results."""
        kdir = _make_kanban_dir(tmp_path)
        _add_task(kdir, 1, "Someday task", priority="someday", status="todo", body="- AC")
        _add_task(kdir, 2, "Critical task", priority="critical", status="todo", body="- AC")
        engine = KanbanEngine(kdir)
        result = pick_dispatchable(engine)
        ids = [t.id for t in result]
        assert ids.index(2) < ids.index(1)

    def test_all_priorities_in_dispatch_order(self, tmp_path: Path) -> None:
        """All 5 priority levels ordered: critical, needed, important, nice-to-have, someday."""
        kdir = _make_kanban_dir(tmp_path)
        # Add in reverse order to ensure sorting is not file-order-dependent
        priorities_reversed = ["someday", "nice-to-have", "important", "needed", "critical"]
        for i, p in enumerate(priorities_reversed, start=1):
            _add_task(kdir, i, f"{p} task", priority=p, status="todo", body="- AC item")
        engine = KanbanEngine(kdir)
        result = pick_dispatchable(engine)
        result_priorities = [t.priority for t in result]
        expected_order = ["critical", "needed", "important", "nice-to-have", "someday"]
        assert result_priorities == expected_order

    def test_critical_before_needed_before_important(self, tmp_path: Path) -> None:
        """Adjacent priority levels are correctly ordered."""
        kdir = _make_kanban_dir(tmp_path)
        _add_task(kdir, 1, "Important", priority="important", status="todo", body="- AC")
        _add_task(kdir, 2, "Needed", priority="needed", status="todo", body="- AC")
        _add_task(kdir, 3, "Critical", priority="critical", status="todo", body="- AC")
        engine = KanbanEngine(kdir)
        result = pick_dispatchable(engine)
        ids = [t.id for t in result]
        assert ids.index(3) < ids.index(2) < ids.index(1)


# ===========================================================================
# AC5 — Status ranking: done > docs > review > in-progress > todo > backlog > research (archived excluded)
#         (done/archived are terminal — excluded from dispatch)
# ===========================================================================


class TestFromAC_PickDispatchableStatusRanking:
    def test_done_before_research(self, tmp_path: Path) -> None:
        """done status ranks before research when priority is equal."""
        kdir = _make_kanban_dir(tmp_path)
        _add_task(kdir, 1, "Research task", status="research", priority="critical", body="")
        _add_task(kdir, 2, "Done task", status="done", priority="critical", body="- AC item")
        engine = KanbanEngine(kdir)
        result = pick_dispatchable(engine)
        ids = [t.id for t in result]
        assert ids.index(2) < ids.index(1)

    def test_archived_excluded_from_dispatch(self, tmp_path: Path) -> None:
        """archived is a terminal status and must not appear in dispatch results."""
        kdir = _make_kanban_dir(tmp_path)
        _add_task(kdir, 1, "Archived task", status="archived", priority="critical", body="- AC item")
        engine = KanbanEngine(kdir)
        result = pick_dispatchable(engine)
        assert all(t.status != "archived" for t in result)

    def test_all_statuses_in_dispatch_order(self, tmp_path: Path) -> None:
        """All 7 active statuses ordered: done, docs, review, in-progress, todo, backlog, research."""
        kdir = _make_kanban_dir(tmp_path)
        # in-progress needs ## Test-Writer Notes + bullet to pass both gates
        bodies: dict[str, str] = {
            "research": "",
            "backlog": "",
            "todo": "- AC item",
            "in-progress": "## Test-Writer Notes\n- tests written",
            "review": "- AC item",
            "docs": "- AC item",
            "done": "- AC item",
        }
        # Add tasks with equal priority so only status order matters
        statuses_reversed = ["research", "backlog", "todo", "in-progress", "review", "docs", "done"]
        for i, s in enumerate(statuses_reversed, start=1):
            _add_task(kdir, i, f"{s} task", status=s, priority="critical", body=bodies[s])
        engine = KanbanEngine(kdir)
        result = pick_dispatchable(engine)
        result_statuses = [t.status for t in result]
        expected_order = ["done", "docs", "review", "in-progress", "todo", "backlog", "research"]
        assert result_statuses == expected_order

    def test_priority_dominates_status(self, tmp_path: Path) -> None:
        """A critical/research task ranks before a someday/done task."""
        kdir = _make_kanban_dir(tmp_path)
        _add_task(kdir, 1, "Someday done", status="done", priority="someday", body="- AC item")
        _add_task(kdir, 2, "Critical research", status="research", priority="critical", body="")
        engine = KanbanEngine(kdir)
        result = pick_dispatchable(engine)
        ids = [t.id for t in result]
        assert ids.index(2) < ids.index(1)

    def test_docs_before_in_progress(self, tmp_path: Path) -> None:
        """docs ranks before in-progress when priority is equal."""
        kdir = _make_kanban_dir(tmp_path)
        _add_task(
            kdir, 1, "In-progress task",
            status="in-progress",
            priority="critical",
            body="## Test-Writer Notes\n- tests written",
        )
        _add_task(kdir, 2, "Docs task", status="docs", priority="critical", body="- AC item")
        engine = KanbanEngine(kdir)
        result = pick_dispatchable(engine)
        ids = [t.id for t in result]
        assert ids.index(2) < ids.index(1)


# ===========================================================================
# AC6 — Result capping at limit
# ===========================================================================


class TestFromAC_PickDispatchableLimit:
    def test_limit_caps_results(self, tmp_path: Path) -> None:
        """limit=3 returns exactly 3 tasks when more are available."""
        kdir = _make_kanban_dir(tmp_path)
        for i in range(1, 11):
            _add_task(kdir, i, f"Task {i}", status="research")
        engine = KanbanEngine(kdir)
        result = pick_dispatchable(engine, limit=3)
        assert len(result) == 3

    def test_limit_does_not_pad(self, tmp_path: Path) -> None:
        """limit=10 returns fewer tasks if fewer pass the gates."""
        kdir = _make_kanban_dir(tmp_path)
        _add_task(kdir, 1, "Only task", status="research")
        engine = KanbanEngine(kdir)
        result = pick_dispatchable(engine, limit=10)
        assert len(result) == 1

    def test_default_limit_is_25(self, tmp_path: Path) -> None:
        """Default limit is 25: 30 tasks → exactly 25 returned."""
        kdir = _make_kanban_dir(tmp_path)
        for i in range(1, 31):
            _add_task(kdir, i, f"Task {i}", status="research")
        engine = KanbanEngine(kdir)
        result = pick_dispatchable(engine)
        assert len(result) == 25

    def test_limit_zero_returns_empty(self, tmp_path: Path) -> None:
        """limit=0 returns an empty list."""
        kdir = _make_kanban_dir(tmp_path)
        _add_task(kdir, 1, "Task", status="research")
        engine = KanbanEngine(kdir)
        result = pick_dispatchable(engine, limit=0)
        assert result == []


# ===========================================================================
# AC7 — Tag filtering
# ===========================================================================


class TestFromAC_PickDispatchableTagFilter:
    def test_tag_filter_excludes_untagged(self, tmp_path: Path) -> None:
        """tag='phase-3' returns only tasks carrying the phase-3 tag."""
        kdir = _make_kanban_dir(tmp_path)
        _add_task(kdir, 1, "Phase-3 task", tags=["phase-3"], status="todo", body="- AC")
        _add_task(kdir, 2, "Phase-2 task", tags=["phase-2"], status="todo", body="- AC")
        engine = KanbanEngine(kdir)
        result = pick_dispatchable(engine, tag="phase-3")
        ids = {t.id for t in result}
        assert 1 in ids
        assert 2 not in ids

    def test_empty_tag_includes_all_passing(self, tmp_path: Path) -> None:
        """tag='' (default) does not filter by tag — all gate-passing tasks are returned."""
        kdir = _make_kanban_dir(tmp_path)
        _add_task(kdir, 1, "Phase-3 task", tags=["phase-3"], status="todo", body="- AC")
        _add_task(kdir, 2, "Phase-2 task", tags=["phase-2"], status="todo", body="- AC")
        engine = KanbanEngine(kdir)
        result = pick_dispatchable(engine, tag="")
        ids = {t.id for t in result}
        assert ids == {1, 2}

    def test_tag_no_match_returns_empty(self, tmp_path: Path) -> None:
        """tag='nonexistent' returns an empty list when no tasks carry that tag."""
        kdir = _make_kanban_dir(tmp_path)
        _add_task(kdir, 1, "Task", tags=["phase-3"], status="todo", body="- AC")
        engine = KanbanEngine(kdir)
        result = pick_dispatchable(engine, tag="phase-99")
        assert result == []

    def test_multi_tag_task_matched_by_any_tag(self, tmp_path: Path) -> None:
        """A task with multiple tags is included when filtering by any of its tags."""
        kdir = _make_kanban_dir(tmp_path)
        _add_task(
            kdir, 1, "Multi-tag task",
            tags=["phase-3", "scope:kanban"],
            status="todo",
            body="- AC",
        )
        engine = KanbanEngine(kdir)
        result = pick_dispatchable(engine, tag="scope:kanban")
        ids = {t.id for t in result}
        assert 1 in ids

    def test_tag_filter_applied_before_gates(self, tmp_path: Path) -> None:
        """Tag pre-filter is applied before gate checks — wrong-tag task not gate-tested."""
        kdir = _make_kanban_dir(tmp_path)
        # This task has the wrong tag and no bullets; it should be absent after tag filter
        _add_task(kdir, 1, "Wrong tag no bullets", tags=["other"], status="todo", body="prose")
        # This task has the right tag and bullets
        _add_task(kdir, 2, "Right tag", tags=["target"], status="todo", body="- AC")
        engine = KanbanEngine(kdir)
        result = pick_dispatchable(engine, tag="target")
        ids = {t.id for t in result}
        assert 2 in ids
        assert 1 not in ids
