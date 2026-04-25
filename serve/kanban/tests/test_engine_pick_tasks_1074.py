"""Tests for AgentView.pick_tasks — 4-step dispatcher pipeline (task #1074).

Covers AC22, AC23, AC27, AC28, D60 sort, D62/D63 greedy wave assembly:
  - Filter: exclude dep_status="blocked", claimed, archived, blocked==True
  - Sort: priority_rank ASC, age DESC, id ASC (deterministic)
  - Greedy wave assembly: size / dep-disjointness / agent-compatibility
  - DispatchEntry.agent from BoardConfig.agent_map (AC23, D24)
  - Dep on archived tasks: wontfix → blocked/excluded (AC27), deprecated → redirect/included (AC28)
  - Non-todo status tasks included when unclaimed and not dep_blocked (§1.3 filter step)
"""

from __future__ import annotations

from pathlib import Path

from owlbear_kanban import KanbanEngine
from owlbear_kanban.models import PickTasksResponse

# ---------------------------------------------------------------------------
# Board fixtures — each test uses tmp_path for isolation
# ---------------------------------------------------------------------------

# Priorities listed HIGH→LOW so rank 0 = "critical" = highest urgency.
# This matches the Brief B spec: "priority_rank ASC, 0 = highest" → critical first.
_BASE_CONFIG = """\
statuses:
  - research
  - backlog
  - todo
  - in-progress
  - review
  - done
priorities:
  - critical
  - needed
  - important
  - nice-to-have
  - someday
entry_status: research
terminal_status: done
wave_size: 4
agent_map:
  research: researcher
  backlog: architect
  todo: builder
  in-progress: builder
  review: reviewer
  done: auditor
agent_types:
  researcher: research
  architect: design
  builder: impl
  reviewer: review
  auditor: audit
agent_compatibility: {}
non_impl_tags: [research, docs]
archival_reasons: [completed, deprecated, dropped, duplicate, wontfix]
status_predicates: {}
claim_timeout: 1h
next_id: 1
"""

# Config where impl bucket (builder) and review bucket (reviewer) are incompatible.
# Symmetry: impl does NOT list review, review does NOT list impl.
_COMPAT_CONFIG = """\
statuses:
  - research
  - backlog
  - todo
  - in-progress
  - review
  - done
priorities:
  - critical
  - needed
  - important
  - nice-to-have
  - someday
entry_status: research
terminal_status: done
wave_size: 4
agent_map:
  research: researcher
  backlog: architect
  todo: builder
  in-progress: builder
  review: reviewer
  done: auditor
agent_types:
  researcher: research
  architect: design
  builder: impl
  reviewer: review
  auditor: audit
agent_compatibility:
  research: [research, design, impl, audit]
  design: [design, impl, review, research, audit]
  impl: [impl, research, design, audit]
  review: [review, design, audit]
  audit: [audit, impl, review, design, research]
non_impl_tags: [research, docs]
archival_reasons: [completed, deprecated, dropped, duplicate, wontfix]
status_predicates: {}
claim_timeout: 1h
next_id: 1
"""

_TASK_TMPL = """\
---
id: {task_id}
title: {title}
status: {status}
priority: {priority}
created: {created}
updated: "2026-04-01T12:00:00+00:00"
tags: []
parent: null
depends_on: {depends_on}
blocked: {blocked}
block_reason: null
claimed_at: {claimed_at}
archival_reason: null
archival_refs: []
---
Body text.
"""

_ARCHIVE_TASK_TMPL = """\
---
id: {task_id}
title: {title}
status: archived
priority: important
created: "2026-01-01T10:00:00+00:00"
updated: "2026-01-01T10:00:00+00:00"
tags: []
parent: null
depends_on: []
blocked: false
block_reason: null
claimed_at: null
archival_reason: {archival_reason}
archival_refs: []
---
Archived task body.
"""


def _make_board(base_dir: Path, config_yaml: str = _BASE_CONFIG) -> Path:
    board = base_dir / "board"
    board.mkdir(parents=True, exist_ok=True)
    (board / "config.yml").write_text(config_yaml, encoding="utf-8")
    (board / "tasks").mkdir(exist_ok=True)
    (board / "archive").mkdir(exist_ok=True)
    return board


def _write_task(  # noqa: PLR0913
    board: Path,
    task_id: int = 1,
    title: str = "Task",
    status: str = "todo",
    priority: str = "important",
    depends_on: str = "[]",
    blocked: str = "false",
    claimed_at: str = "null",
    created: str = '"2026-01-15T10:00:00+00:00"',
) -> Path:
    content = _TASK_TMPL.format(
        task_id=task_id,
        title=title,
        status=status,
        priority=priority,
        created=created,
        depends_on=depends_on,
        blocked=blocked,
        claimed_at=claimed_at,
    )
    path = board / "tasks" / f"{task_id}-task.md"
    path.write_text(content, encoding="utf-8")
    return path


def _write_archived_task(
    board: Path,
    task_id: int,
    title: str = "Archived",
    archival_reason: str = "completed",
) -> Path:
    content = _ARCHIVE_TASK_TMPL.format(
        task_id=task_id,
        title=title,
        archival_reason=archival_reason,
    )
    path = board / "archive" / f"{task_id}-archived.md"
    path.write_text(content, encoding="utf-8")
    return path


def _make_engine(base_dir: Path, config_yaml: str = _BASE_CONFIG) -> KanbanEngine:
    board = _make_board(base_dir, config_yaml)
    return KanbanEngine(board, activity_log=False)


def _all_ids(resp: PickTasksResponse) -> set[int]:
    return {entry.id for wave in resp.waves for entry in wave.tasks}


# ---------------------------------------------------------------------------
# AC22: Filter — dep_status="blocked" tasks must be excluded
# ---------------------------------------------------------------------------


class TestFromAC_PickTasksFilter:
    """AC22: pick_tasks excludes claimed, archived, blocked==true, dep_status='blocked'."""

    def test_dep_status_blocked_task_excluded(self, tmp_path: Path) -> None:
        """Task whose dep resolved to dep_status='blocked' must be excluded.

        Task 1 depends on task 99 which is wontfix-archived → dep_status='blocked'.
        The task itself has blocked=false (the flag), so the list_tasks(blocked=False)
        filter alone does NOT exclude it.  pick_tasks must additionally exclude tasks
        whose computed dep_status equals 'blocked'.
        """
        board = _make_board(tmp_path)
        _write_archived_task(board, task_id=99, archival_reason="wontfix")
        _write_task(board, task_id=1, status="todo", depends_on="[99]")
        _write_task(board, task_id=2, status="todo")  # clean task, should appear
        engine = KanbanEngine(board, activity_log=False)
        resp = engine.agent_view().pick_tasks()
        ids = _all_ids(resp)
        assert 1 not in ids, (
            "Task 1 has dep_status='blocked' (dep on wontfix-archived #99) — must be excluded"
        )
        assert 2 in ids, "Task 2 has no blocking dep — must be included"

    def test_no_intra_wave_dep_edges_across_all_waves(self, tmp_path: Path) -> None:
        """No two tasks in the same wave may have a dep edge (in either direction).

        Tasks 1 and 2 both have todo status (no dep_status blocker).  Task 1
        depends on task 2.  With wave_size=2 and max_waves=2 the naive chunking
        implementation puts both in wave 0, violating the dep-disjointness constraint.
        The correct implementation must separate them into different waves.
        """
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, status="todo", depends_on="[2]")
        _write_task(board, task_id=2, status="todo")
        engine = KanbanEngine(board, activity_log=False)
        resp = engine.agent_view().pick_tasks(wave_size=2, max_waves=2)
        ids = _all_ids(resp)
        assert {1, 2} == ids, "Both tasks should be dispatched"
        for wave in resp.waves:
            wave_ids = {entry.id for entry in wave.tasks}
            assert not ({1, 2} <= wave_ids), (
                f"Tasks 1 and 2 must not appear in the same wave (dep edge); got wave {wave_ids}"
            )


# ---------------------------------------------------------------------------
# D60: Sort — priority_rank ASC, age DESC, id ASC
# ---------------------------------------------------------------------------


class TestFromAC_PickTasksSort:
    """Sort: (priority_rank ASC, age DESC, id ASC) produces deterministic dispatch order.

    Uses 5 tasks to drive the full 3-level sort key.  The expected permutation
    [11, 12, 3, 5, 1] has only a 1/120 chance of matching an arbitrary unsorted
    ordering, making accidental passing essentially impossible.
    """

    def test_sort_priority_rank_age_desc_id_asc_combined(self, tmp_path: Path) -> None:
        """Full sort key: (priority_rank ASC, age DESC, id ASC) verified in one scenario.

        priorities in _BASE_CONFIG (high→low): critical(0), needed(1), important(2),
        nice-to-have(3), someday(4).

        Tasks:
          id=11 — critical, OLD (2026-01-01) → rank 0, larger age
          id=12 — critical, NEW (2026-03-01) → rank 0, smaller age
          id=3  — needed,   MID (2026-02-01) → rank 1, lower id
          id=5  — needed,   MID (2026-02-01) → rank 1, higher id
          id=1  — someday,  MID (2026-02-01) → rank 4

        Expected order by (priority_rank ASC, age DESC, id ASC): [11, 12, 3, 5, 1]
          • 11 before 12: same priority, id=11 is older (age DESC).
          • 3 before 5: same priority and age, id=3 < id=5 (id ASC).
          • 1 last: lowest priority.

        Current code: no sort applied; filesystem returns tasks in hash/arbitrary
        order (macOS APFS).  The specific permutation [11,12,3,5,1] occurs only
        by coincidence (p < 1%).
        """
        board = _make_board(tmp_path)
        ts_old = '"2026-01-01T00:00:00+00:00"'
        ts_new = '"2026-03-01T00:00:00+00:00"'
        ts_mid = '"2026-02-01T00:00:00+00:00"'
        _write_task(board, task_id=11, priority="critical", created=ts_old)
        _write_task(board, task_id=12, priority="critical", created=ts_new)
        _write_task(board, task_id=3, priority="needed", created=ts_mid)
        _write_task(board, task_id=5, priority="needed", created=ts_mid)
        _write_task(board, task_id=1, priority="someday", created=ts_mid)
        engine = KanbanEngine(board, activity_log=False)
        resp = engine.agent_view().pick_tasks(wave_size=5, max_waves=1)
        assert len(resp.waves) == 1, f"Expected 1 wave; got {len(resp.waves)}"
        ordered = [entry.id for entry in resp.waves[0].tasks]
        assert ordered == [11, 12, 3, 5, 1], (
            f"Expected sort order [11,12,3,5,1] by "
            f"(priority_rank ASC, age DESC, id ASC); got {ordered}"
        )


# ---------------------------------------------------------------------------
# D62 + D63: Greedy wave assembly — size / dep-disjointness / agent-compat
# ---------------------------------------------------------------------------


class TestFromAC_PickTasksWaveAssembly:
    """Greedy wave assembly enforces size, dep-disjointness, and agent-compat constraints."""

    def test_dep_disjointness_splits_dependent_tasks_into_different_waves(
        self, tmp_path: Path
    ) -> None:
        """No wave contains a task and its dependency simultaneously (dep-disjointness).

        Setup: task 1 depends on task 2 (both todo, no dep_status blocker since
        task 2 is active, not archived).  wave_size=2, max_waves=2.

        Naive chunking: wave 0 = [task 1, task 2] — violates dep-disjointness.
        Correct:        wave 0 = [task 1],  wave 1 = [task 2] (or any separation).
        """
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, status="todo", depends_on="[2]")
        _write_task(board, task_id=2, status="todo")
        engine = KanbanEngine(board, activity_log=False)
        resp = engine.agent_view().pick_tasks(wave_size=2, max_waves=2)
        assert {1, 2} == _all_ids(resp), "Both tasks should be dispatched"
        for wave in resp.waves:
            wave_ids = {e.id for e in wave.tasks}
            assert not ({1, 2} <= wave_ids), (
                f"Dep-disjointness violated: tasks 1 and 2 are in same wave {wave_ids}"
            )

    def test_task_dropped_when_dep_conflict_and_max_waves_exhausted(
        self, tmp_path: Path
    ) -> None:
        """A task not fitting any wave due to dep conflict is dropped when max_waves reached.

        Setup: task 1 depends on task 2 (both todo).  Task 3 has no deps.
        wave_size=2, max_waves=1 → only 1 wave allowed.

        Greedy assembly:
          - Task 1 → wave 0 (empty, fits)
          - Task 2 → wave 0 has task 1 (dep edge 1→2 or 2→1) → conflict; no wave fits;
            max_waves=1 → task 2 DROPPED.
          - Task 3 → wave 0 has 1 task (space ≤ wave_size=2), no dep conflict → placed.
        Result: wave 0 = [task 1, task 3].  Task 2 is absent.

        Current code (no dep check): wave 0 = [task 1, task 2]; task 3 not selected
        (max_items = wave_size * max_waves = 2 x 1 = 2, so selected = [task1, task2]).
        """
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, status="todo", depends_on="[2]")
        _write_task(board, task_id=2, status="todo")
        _write_task(board, task_id=3, status="todo")
        engine = KanbanEngine(board, activity_log=False)
        resp = engine.agent_view().pick_tasks(wave_size=2, max_waves=1)
        assert len(resp.waves) == 1
        wave_ids = {e.id for e in resp.waves[0].tasks}
        # Task 2 must be dropped; task 3 must be in wave with task 1
        assert 2 not in wave_ids, (
            f"Task 2 should be dropped (dep conflict, max_waves exhausted); got wave {wave_ids}"
        )
        assert 3 in wave_ids, (
            f"Task 3 has no dep conflict and should fill the remaining slot; got {wave_ids}"
        )

    def test_incompatible_agent_buckets_go_to_different_waves(
        self, tmp_path: Path
    ) -> None:
        """Tasks in incompatible agent buckets must not share a wave (D63).

        Using _COMPAT_CONFIG where impl (builder) and review (reviewer) are incompatible.
        Task 1: todo → agent=builder → bucket=impl
        Task 2: review → agent=reviewer → bucket=review

        Correct:  wave 0 = [task 1], wave 1 = [task 2] (incompatible buckets → separate).
        Current:  pick_tasks only considers status='todo', so task 2 is never returned.
                  assert 2 in all_ids fails.
        """
        board = _make_board(tmp_path, _COMPAT_CONFIG)
        _write_task(board, task_id=1, status="todo")
        _write_task(board, task_id=2, status="review")
        engine = KanbanEngine(board, activity_log=False)
        resp = engine.agent_view().pick_tasks(wave_size=2, max_waves=2)
        ids = _all_ids(resp)
        # Both tasks must be dispatched
        assert 1 in ids, "Task 1 (todo/impl) must be dispatched"
        assert 2 in ids, "Task 2 (review/review) must be dispatched"
        # They must be in separate waves (incompatible buckets)
        assert len(resp.waves) == 2, (
            f"impl and review buckets are incompatible → 2 waves expected; got {len(resp.waves)}"
        )
        for wave in resp.waves:
            assert len(wave.tasks) == 1, (
                f"Each wave should have exactly 1 task (incompatible); got {[e.id for e in wave.tasks]}"
            )

    def test_non_todo_status_tasks_included_when_unclaimed_and_unblocked(
        self, tmp_path: Path
    ) -> None:
        """Filter step (§1.3) excludes only archived/claimed/blocked tasks, not by status.

        A 'research' status task that is unclaimed, not dep_blocked, and not flagged
        blocked must appear in pick_tasks results alongside a 'todo' task.

        Current implementation applies an extra filter 'status == todo' that is
        NOT present in the Brief B §1.3 algorithm — this test validates that filter
        must be removed.
        """
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, status="research")
        _write_task(board, task_id=2, status="todo")
        engine = KanbanEngine(board, activity_log=False)
        resp = engine.agent_view().pick_tasks(wave_size=4, max_waves=1)
        ids = _all_ids(resp)
        assert 1 in ids, (
            "Task 1 (research, unclaimed, unblocked) must be included; "
            "filter step excludes only archived/claimed/dep_blocked/blocked tasks"
        )
        assert 2 in ids, "Task 2 (todo) must be included"


# ---------------------------------------------------------------------------
# AC23 + D24: DispatchEntry.agent from BoardConfig.agent_map
# ---------------------------------------------------------------------------


class TestFromAC_PickTasksAgent:
    """AC23: each DispatchEntry.agent equals the full string from BoardConfig.agent_map."""

    def test_agent_is_full_agent_map_value_not_first_character(
        self, tmp_path: Path
    ) -> None:
        """DispatchEntry.agent must be the complete agent_map value, not its first char.

        _BASE_CONFIG has agent_map['todo'] = 'builder' (a str, not a list).
        The current implementation does:
            (status_agents.get(task.status) or [default_agent])[0]
        With a str value 'builder', this evaluates 'builder'[0] = 'b'.
        Expected: agent == 'builder'.
        Current: agent == 'b'.
        """
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, status="todo")
        engine = KanbanEngine(board, activity_log=False)
        resp = engine.agent_view().pick_tasks()
        entries = [entry for wave in resp.waves for entry in wave.tasks]
        assert len(entries) == 1
        assert entries[0].agent == "builder", (
            f"DispatchEntry.agent must equal agent_map['todo']='builder'; "
            f"got {entries[0].agent!r} (current code returns first char of string)"
        )

    def test_different_status_tasks_carry_correct_agent(self, tmp_path: Path) -> None:
        """Tasks in different statuses each carry the agent mapped for their status.

        research → 'researcher', todo → 'builder'.
        This test fails on TWO fronts with current code:
          (a) research task is excluded (only todo is picked), and
          (b) even for todo the agent would be 'b' not 'builder'.
        """
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, status="research")
        _write_task(board, task_id=2, status="todo")
        engine = KanbanEngine(board, activity_log=False)
        resp = engine.agent_view().pick_tasks()
        by_id = {
            entry.id: entry.agent
            for wave in resp.waves
            for entry in wave.tasks
        }
        assert by_id.get(1) == "researcher", (
            f"research task must have agent='researcher'; got {by_id.get(1)!r}"
        )
        assert by_id.get(2) == "builder", (
            f"todo task must have agent='builder'; got {by_id.get(2)!r}"
        )


# ---------------------------------------------------------------------------
# AC27 + AC28: archival_reason → dep_status computation
# ---------------------------------------------------------------------------


class TestFromAC_PickTasksArchivedDeps:
    """AC27: wontfix-archived dep → dep_status='blocked', excluded from pick_tasks.
    AC28: deprecated-archived dep → dep_status='redirect', NOT excluded.
    """

    def test_wontfix_archived_dep_excludes_dependent_task(
        self, tmp_path: Path
    ) -> None:
        """AC27: task whose only dep is wontfix-archived gets dep_status='blocked' → excluded.

        Task 1 depends on archived task 99 (archival_reason='wontfix').
        Task 1 has blocked=false (the field), so only dep_status filtering catches it.
        Current code does not filter by dep_status → task 1 appears → assertion fails.
        """
        board = _make_board(tmp_path)
        _write_archived_task(board, task_id=99, archival_reason="wontfix")
        _write_task(board, task_id=1, status="todo", depends_on="[99]")
        engine = KanbanEngine(board, activity_log=False)
        resp = engine.agent_view().pick_tasks()
        assert 1 not in _all_ids(resp), (
            "Task 1 has dep on wontfix-archived #99 → dep_status='blocked' → must be excluded"
        )

    def test_dropped_archived_dep_also_excluded(self, tmp_path: Path) -> None:
        """AC27 applies equally to 'dropped' archival reason (also maps to dep_status='blocked')."""
        board = _make_board(tmp_path)
        _write_archived_task(board, task_id=99, archival_reason="dropped")
        _write_task(board, task_id=1, status="todo", depends_on="[99]")
        engine = KanbanEngine(board, activity_log=False)
        resp = engine.agent_view().pick_tasks()
        assert 1 not in _all_ids(resp), (
            "Task 1 has dep on dropped-archived #99 → dep_status='blocked' → must be excluded"
        )

    def test_ac27_blocked_excluded_ac28_redirect_included_simultaneously(
        self, tmp_path: Path
    ) -> None:
        """AC27 and AC28 together: wontfix dep excluded, deprecated dep included.

        Task 1 depends on wontfix-archived #98 → dep_status='blocked' → excluded.
        Task 2 depends on deprecated-archived #99 → dep_status='redirect' → included.
        Task 3 has no deps → included.

        Current code does not filter by dep_status → task 1 appears → assertion fails.
        """
        board = _make_board(tmp_path)
        _write_archived_task(board, task_id=98, archival_reason="wontfix")
        _write_archived_task(board, task_id=99, archival_reason="deprecated")
        _write_task(board, task_id=1, status="todo", depends_on="[98]")  # blocked → excluded
        _write_task(board, task_id=2, status="todo", depends_on="[99]")  # redirect → included
        _write_task(board, task_id=3, status="todo")                      # clean → included
        engine = KanbanEngine(board, activity_log=False)
        resp = engine.agent_view().pick_tasks()
        ids = _all_ids(resp)
        assert 1 not in ids, (
            "Task 1 dep on wontfix #98 → dep_status='blocked' → must be excluded"
        )
        assert 2 in ids, (
            "Task 2 dep on deprecated #99 → dep_status='redirect' → must NOT be excluded"
        )
        assert 3 in ids, "Task 3 has no dep -> must be included"


# ---------------------------------------------------------------------------
# Default wave_size fallback (D42) — combined with sort to force failure
# ---------------------------------------------------------------------------


class TestFromAC_PickTasksDefaults:
    """Default wave_size from BoardConfig.wave_size and max_waves cardinality."""

    def test_default_wave_size_from_config_and_sort_order_combined(
        self, tmp_path: Path
    ) -> None:
        """Default wave_size=1 (from config) produces one task per wave in priority order.

        Tests wave_size fallback (D42) AND sort (D60) together.
        Config has wave_size=1.  Three tasks: critical (id=3), needed (id=2), someday (id=1).
        Expected wave order by priority_rank ASC:
          wave 0: id=3 (critical, rank 0)
          wave 1: id=2 (needed, rank 1)
          wave 2: id=1 (someday, rank 4)

        Current code: wave_size fallback IS implemented (wave_size=1 from config).
        Sort is NOT implemented.  Filesystem returns an arbitrary permutation of
        tasks.  The wave_order assertion [3, 2, 1] fails when filesystem returns
        any order other than the correct priority order.
        """
        config = _BASE_CONFIG.replace("wave_size: 4", "wave_size: 1")
        board = _make_board(tmp_path, config)
        _write_task(board, task_id=1, priority="someday")
        _write_task(board, task_id=2, priority="needed")
        _write_task(board, task_id=3, priority="critical")
        engine = KanbanEngine(board, activity_log=False)
        resp = engine.agent_view().pick_tasks(max_waves=3)  # no wave_size arg -> uses config
        assert len(resp.waves) == 3, (
            f"With config wave_size=1 and 3 tasks, expect 3 waves; got {len(resp.waves)}"
        )
        for wave in resp.waves:
            assert len(wave.tasks) == 1, (
                f"wave_size=1 -> each wave has 1 task; got {[e.id for e in wave.tasks]}"
            )
        wave_order = [wave.tasks[0].id for wave in resp.waves]
        assert wave_order == [3, 2, 1], (
            f"Expected sort order [3 (critical), 2 (needed), 1 (someday)]; got {wave_order}"
        )
