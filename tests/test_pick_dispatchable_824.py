"""Failing tests for dispatch.py additional contracts — #824, RED phase.

AC coverage (items NOT already covered in test_pick_dispatchable_823.py):
  AC-CONST   — dispatch.py exposes PRIORITY_RANK and STATUS_RANK as module-level constants
  AC-VALS    — PRIORITY_RANK: critical=0..someday=4; STATUS_RANK: done=0..research=6
  AC-DIVERGE — Rank constants use execution priority ≠ config display order
  AC-EXPORT  — pick_dispatchable is exported from owlbear_kanban.__all__
  AC-BLOCKED — Blocked tasks are excluded from results
  AC-UNCLAIMED — Claimed tasks are excluded from results

All imports from owlbear_kanban.dispatch will raise ModuleNotFoundError (RED) until
the builder creates the module.
"""

from __future__ import annotations

from pathlib import Path

import owlbear_kanban.dispatch as _dispatch_mod
from owlbear_kanban import KanbanEngine
from owlbear_kanban.dispatch import PRIORITY_RANK, STATUS_RANK

# ---------------------------------------------------------------------------
# Shared helpers (same real-engine + temp-filesystem pattern as #823)
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
    body: str = "",
) -> str:
    tags_yaml = "[" + ", ".join(f'"{t}"' for t in (tags or [])) + "]"
    br_yaml = f'"{block_reason}"' if block_reason else "null"
    cb_yaml = f'"{claimed_by}"' if claimed_by else "null"
    return (
        "---\n"
        f"id: {task_id}\n"
        f"title: {title!r}\n"
        f"status: {status}\n"
        f"priority: {priority}\n"
        "created: 2026-01-01T10:00:00.0000000+00:00\n"
        "updated: 2026-01-02T10:00:00.0000000+00:00\n"
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
    s = slug or title.lower().replace(" ", "-")[:30]
    path = kdir / subdir / f"{task_id}-{s}.md"
    path.write_text(_task_content(task_id, title, **kwargs), encoding="utf-8")
    return path


# ===========================================================================
# AC-CONST — PRIORITY_RANK and STATUS_RANK are public module-level constants
# ===========================================================================


class TestFromAC_RankMapConstants:
    def test_priority_rank_is_module_level_attribute(self) -> None:
        """dispatch module exposes PRIORITY_RANK as a directly accessible attribute."""
        assert hasattr(_dispatch_mod, "PRIORITY_RANK")

    def test_status_rank_is_module_level_attribute(self) -> None:
        """dispatch module exposes STATUS_RANK as a directly accessible attribute."""
        assert hasattr(_dispatch_mod, "STATUS_RANK")

    def test_priority_rank_is_dict_of_str_to_int(self) -> None:
        """PRIORITY_RANK maps str priority names to int rank values."""
        assert isinstance(PRIORITY_RANK, dict)
        assert all(isinstance(k, str) and isinstance(v, int) for k, v in PRIORITY_RANK.items())

    def test_status_rank_is_dict_of_str_to_int(self) -> None:
        """STATUS_RANK maps str status names to int rank values."""
        assert isinstance(STATUS_RANK, dict)
        assert all(isinstance(k, str) and isinstance(v, int) for k, v in STATUS_RANK.items())

    def test_priority_rank_covers_all_five_levels(self) -> None:
        """PRIORITY_RANK contains exactly the 5 canonical priority names."""
        assert set(PRIORITY_RANK) == {"critical", "needed", "important", "nice-to-have", "someday"}

    def test_status_rank_covers_all_seven_statuses(self) -> None:
        """STATUS_RANK contains exactly the 7 canonical status names."""
        assert set(STATUS_RANK) == {
            "done", "docs", "review", "in-progress", "todo", "backlog", "research"
        }

    def test_priority_rank_values_are_unique(self) -> None:
        """Each priority level has a distinct rank integer — no ties."""
        values = list(PRIORITY_RANK.values())
        assert len(values) == len(set(values))

    def test_status_rank_values_are_unique(self) -> None:
        """Each status has a distinct rank integer — no ties."""
        values = list(STATUS_RANK.values())
        assert len(values) == len(set(values))


# ===========================================================================
# AC-VALS — PRIORITY_RANK: critical=0..someday=4; STATUS_RANK: done=0..research=6
# ===========================================================================


class TestFromAC_RankMapValues:
    def test_priority_critical_is_rank_zero(self) -> None:
        """critical has rank 0 — highest execution dispatch priority."""
        assert PRIORITY_RANK["critical"] == 0

    def test_priority_needed_is_rank_one(self) -> None:
        assert PRIORITY_RANK["needed"] == 1

    def test_priority_important_is_rank_two(self) -> None:
        assert PRIORITY_RANK["important"] == 2

    def test_priority_nice_to_have_is_rank_three(self) -> None:
        assert PRIORITY_RANK["nice-to-have"] == 3

    def test_priority_someday_is_rank_four(self) -> None:
        """someday has rank 4 — lowest execution dispatch priority."""
        assert PRIORITY_RANK["someday"] == 4

    def test_status_done_is_rank_zero(self) -> None:
        """done has rank 0 — highest execution dispatch priority among statuses."""
        assert STATUS_RANK["done"] == 0

    def test_status_docs_is_rank_one(self) -> None:
        assert STATUS_RANK["docs"] == 1

    def test_status_review_is_rank_two(self) -> None:
        assert STATUS_RANK["review"] == 2

    def test_status_in_progress_is_rank_three(self) -> None:
        assert STATUS_RANK["in-progress"] == 3

    def test_status_todo_is_rank_four(self) -> None:
        assert STATUS_RANK["todo"] == 4

    def test_status_backlog_is_rank_five(self) -> None:
        assert STATUS_RANK["backlog"] == 5

    def test_status_research_is_rank_six(self) -> None:
        """research has rank 6 — lowest execution dispatch priority among statuses."""
        assert STATUS_RANK["research"] == 6


# ===========================================================================
# AC-DIVERGE — Execution rank maps diverge from config display order
# (config: someday→critical, research→done; dispatch: critical→someday, done→research)
# ===========================================================================


class TestFromAC_ExecutionPriorityNotDisplayOrder:
    """Verify that PRIORITY_RANK and STATUS_RANK encode execution priority, which is
    the inverse of the config.yml display order (someday listed first, critical last).
    This satisfies the AC line "Rank maps documented: execution priority ≠ display order".
    """

    def test_priority_rank_critical_beats_someday(self) -> None:
        """critical < someday in PRIORITY_RANK — execution priority is highest-first.
        Config display order is the opposite (someday is the first priority listed).
        """
        assert PRIORITY_RANK["critical"] < PRIORITY_RANK["someday"]

    def test_priority_rank_critical_beats_needed(self) -> None:
        assert PRIORITY_RANK["critical"] < PRIORITY_RANK["needed"]

    def test_status_rank_done_beats_research(self) -> None:
        """done < research in STATUS_RANK — finished work has higher dispatch priority.
        Config display order is the opposite (research is the first status listed).
        """
        assert STATUS_RANK["done"] < STATUS_RANK["research"]

    def test_status_rank_done_beats_todo(self) -> None:
        assert STATUS_RANK["done"] < STATUS_RANK["todo"]

    def test_priority_rank_not_derived_from_config(self, tmp_path: Path) -> None:
        """PRIORITY_RANK['critical'] is 0 even though config lists 'someday' first.
        If it were config-derived, critical would have rank 4 (last in config list).
        """
        kdir = _make_kanban_dir(tmp_path)
        engine = KanbanEngine(kdir)
        # Config-derived rank puts someday=0, critical=4 (reversed from dispatch)
        config_priority_rank = {p: i for i, p in enumerate(engine.board_config().priorities)}
        assert config_priority_rank["someday"] < config_priority_rank["critical"]  # config order
        assert PRIORITY_RANK["critical"] < PRIORITY_RANK["someday"]  # execution order (inverse)

    def test_status_rank_not_derived_from_config(self, tmp_path: Path) -> None:
        """STATUS_RANK['done'] is 0 even though config lists 'research' first.
        If it were config-derived, done would have rank 6 (last in config list).
        """
        kdir = _make_kanban_dir(tmp_path)
        engine = KanbanEngine(kdir)
        # Config-derived rank puts research=0, done=6 (reversed from dispatch)
        config_status_rank = {
            s["name"]: i for i, s in enumerate(engine.board_config().statuses)
        }
        assert config_status_rank["research"] < config_status_rank["done"]  # config order
        assert STATUS_RANK["done"] < STATUS_RANK["research"]  # execution order (inverse)

    def test_rank_constants_do_not_change_across_engine_instances(self, tmp_path: Path) -> None:
        """Module-level constants are fixed — they don't change when engines are created."""
        kdir = _make_kanban_dir(tmp_path)
        KanbanEngine(kdir)
        assert PRIORITY_RANK is _dispatch_mod.PRIORITY_RANK
        assert STATUS_RANK is _dispatch_mod.STATUS_RANK
        assert PRIORITY_RANK["critical"] == 0
        assert STATUS_RANK["done"] == 0


# ===========================================================================
# AC-EXPORT — pick_dispatchable in owlbear_kanban.__all__
# ===========================================================================


class TestFromAC_PackageExport:
    def test_pick_dispatchable_in_package_all(self) -> None:
        """pick_dispatchable must be listed in owlbear_kanban.__all__."""
        import owlbear_kanban  # noqa: PLC0415

        assert "pick_dispatchable" in owlbear_kanban.__all__

    def test_pick_dispatchable_importable_from_package_root(self) -> None:
        """from owlbear_kanban import pick_dispatchable succeeds without errors."""
        from owlbear_kanban import pick_dispatchable as fn  # noqa: PLC0415

        assert callable(fn)

    def test_package_and_module_expose_same_callable(self) -> None:
        """owlbear_kanban.pick_dispatchable is the same object as
        owlbear_kanban.dispatch.pick_dispatchable — the package re-exports directly.
        """
        import owlbear_kanban  # noqa: PLC0415
        from owlbear_kanban.dispatch import pick_dispatchable as from_module  # noqa: PLC0415

        assert owlbear_kanban.pick_dispatchable is from_module


# ===========================================================================
# AC-BLOCKED — Blocked tasks are excluded from results
# ===========================================================================


class TestFromAC_BlockedExclusion:
    def test_blocked_task_excluded(self, tmp_path: Path) -> None:
        """A blocked task is not returned even when it passes all gate checks."""
        from owlbear_kanban.dispatch import pick_dispatchable  # noqa: PLC0415

        kdir = _make_kanban_dir(tmp_path)
        _add_task(
            kdir, 1, "Blocked task",
            status="todo",
            body="- AC item",
            blocked=True,
            block_reason="waiting on upstream",
        )
        engine = KanbanEngine(kdir)
        result = pick_dispatchable(engine)
        assert 1 not in {t.id for t in result}

    def test_unblocked_task_included(self, tmp_path: Path) -> None:
        """An unblocked task with valid AC appears in results."""
        from owlbear_kanban.dispatch import pick_dispatchable  # noqa: PLC0415

        kdir = _make_kanban_dir(tmp_path)
        _add_task(kdir, 2, "Clear task", status="todo", body="- AC item", blocked=False)
        engine = KanbanEngine(kdir)
        result = pick_dispatchable(engine)
        assert 2 in {t.id for t in result}

    def test_blocked_excluded_regardless_of_ac_quality(self, tmp_path: Path) -> None:
        """Blocked status takes precedence — task excluded even with perfect AC."""
        from owlbear_kanban.dispatch import pick_dispatchable  # noqa: PLC0415

        kdir = _make_kanban_dir(tmp_path)
        _add_task(
            kdir, 3, "Blocked with AC",
            status="todo",
            body="- implement feature\n- write tests\n1. verify output",
            blocked=True,
            block_reason="dependency",
        )
        engine = KanbanEngine(kdir)
        result = pick_dispatchable(engine)
        assert 3 not in {t.id for t in result}

    def test_mixed_blocked_and_unblocked(self, tmp_path: Path) -> None:
        """Only unblocked tasks appear; blocked are fully excluded."""
        from owlbear_kanban.dispatch import pick_dispatchable  # noqa: PLC0415

        kdir = _make_kanban_dir(tmp_path)
        _add_task(kdir, 1, "Blocked", status="todo", body="- AC", blocked=True, block_reason="x")
        _add_task(kdir, 2, "Clear", status="todo", body="- AC", blocked=False)
        engine = KanbanEngine(kdir)
        result = pick_dispatchable(engine)
        ids = {t.id for t in result}
        assert 2 in ids
        assert 1 not in ids


# ===========================================================================
# AC-UNCLAIMED — Claimed tasks are excluded from results
# ===========================================================================


class TestFromAC_UnclaimedExclusion:
    def test_claimed_task_excluded(self, tmp_path: Path) -> None:
        """A task with a non-null claimed_by is excluded from dispatch results."""
        from owlbear_kanban.dispatch import pick_dispatchable  # noqa: PLC0415

        kdir = _make_kanban_dir(tmp_path)
        _add_task(
            kdir, 1, "Claimed task",
            status="in-progress",
            body="## Test-Writer Notes\n- 5 tests",
            claimed_by="builder-agent",
        )
        engine = KanbanEngine(kdir)
        result = pick_dispatchable(engine)
        assert 1 not in {t.id for t in result}

    def test_unclaimed_task_included(self, tmp_path: Path) -> None:
        """A task with claimed_by=null is eligible for dispatch."""
        from owlbear_kanban.dispatch import pick_dispatchable  # noqa: PLC0415

        kdir = _make_kanban_dir(tmp_path)
        _add_task(
            kdir, 2, "Unclaimed task",
            status="in-progress",
            body="## Test-Writer Notes\n- 5 tests",
            claimed_by=None,
        )
        engine = KanbanEngine(kdir)
        result = pick_dispatchable(engine)
        assert 2 in {t.id for t in result}

    def test_claimed_excluded_regardless_of_gate_status(self, tmp_path: Path) -> None:
        """Claimed status takes precedence — task excluded even when it passes all gates."""
        from owlbear_kanban.dispatch import pick_dispatchable  # noqa: PLC0415

        kdir = _make_kanban_dir(tmp_path)
        _add_task(
            kdir, 3, "Claimed with notes",
            status="in-progress",
            body="## Test-Writer Notes\n- 10 tests, all fail",
            claimed_by="test-writer-agent",
        )
        engine = KanbanEngine(kdir)
        result = pick_dispatchable(engine)
        assert 3 not in {t.id for t in result}

    def test_mixed_claimed_and_unclaimed(self, tmp_path: Path) -> None:
        """Only unclaimed tasks appear; claimed tasks are fully excluded."""
        from owlbear_kanban.dispatch import pick_dispatchable  # noqa: PLC0415

        kdir = _make_kanban_dir(tmp_path)
        _add_task(
            kdir, 1, "Claimed",
            status="in-progress",
            body="## Test-Writer Notes\n- tests",
            claimed_by="agent-x",
        )
        _add_task(
            kdir, 2, "Unclaimed",
            status="in-progress",
            body="## Test-Writer Notes\n- tests",
            claimed_by=None,
        )
        engine = KanbanEngine(kdir)
        result = pick_dispatchable(engine)
        ids = {t.id for t in result}
        assert 2 in ids
        assert 1 not in ids
