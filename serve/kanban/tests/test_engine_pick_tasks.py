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

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from owlbear_cockpit.view import CockpitView
from owlbear_kanban import KanbanEngine
from owlbear_kanban.errors import ValidationError
from owlbear_kanban.models import PickTasksResponse

# ---------------------------------------------------------------------------
# Board fixtures — each test uses tmp_path for isolation
# ---------------------------------------------------------------------------

# Priorities listed HIGH→LOW so rank 0 = "critical" = highest urgency.
# This matches the Brief B spec: "priority_rank ASC, 0 = highest" → critical first.
_BASE_CONFIG = """\
schema: grouped
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
next_id: 1
paths:
    tasks_dir: tasks
    archive_dir: archive
pipeline:
    entry_status: research
    terminal_status: done
    wave_size: 4
    claim_timeout: 1h
agents:
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
policy:
    non_impl_tags: [research, docs]
    archival_reasons: [completed, deprecated, dropped, duplicate, wontfix]
    status_predicates: {}
"""

# Config where impl bucket (builder) and review bucket (reviewer) are incompatible.
# Symmetry: impl does NOT list review, review does NOT list impl.
_COMPAT_CONFIG = """\
schema: grouped
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
next_id: 1
paths:
    tasks_dir: tasks
    archive_dir: archive
pipeline:
    entry_status: research
    terminal_status: done
    wave_size: 4
    claim_timeout: 1h
agents:
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
policy:
    non_impl_tags: [research, docs]
    archival_reasons: [completed, deprecated, dropped, duplicate, wontfix]
    status_predicates: {}
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
- AC item.
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
        """With PRODUCT_TOPOLOGY, agent_compatibility is always empty — all agents are compatible.

        PRODUCT_TOPOLOGY.agent_compatibility = {} overrides _COMPAT_CONFIG, so tasks
        in different statuses (todo/test-writer and review/reviewer) go to the SAME
        wave (no incompatibility constraint applies).
        """
        board = _make_board(tmp_path, _COMPAT_CONFIG)
        _write_task(board, task_id=1, status="todo")
        _write_task(board, task_id=2, status="review")
        engine = KanbanEngine(board, activity_log=False)
        resp = engine.agent_view().pick_tasks(wave_size=2, max_waves=2)
        ids = _all_ids(resp)
        # Both tasks must be dispatched
        assert 1 in ids, "Task 1 (todo) must be dispatched"
        assert 2 in ids, "Task 2 (review) must be dispatched"
        # With empty agent_compatibility all agents are compatible — one wave fits both
        assert len(resp.waves) == 1, (
            f"With empty agent_compatibility all agents are compatible — expect 1 wave; got {len(resp.waves)}"
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

        PRODUCT_TOPOLOGY has agent_map['todo'] = 'test-writer' (a str, not a list).
        The current implementation does:
            (status_agents.get(task.status) or [default_agent])[0]
        With a str value 'test-writer', this evaluates 'test-writer'[0] = 't'.
        Expected: agent == 'test-writer'.
        Current: agent == 't'.
        """
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, status="todo")
        engine = KanbanEngine(board, activity_log=False)
        resp = engine.agent_view().pick_tasks()
        entries = [entry for wave in resp.waves for entry in wave.tasks]
        assert len(entries) == 1
        assert entries[0].agent == "test-writer", (
            f"DispatchEntry.agent must equal PRODUCT_TOPOLOGY agent_map['todo']='test-writer'; "
            f"got {entries[0].agent!r} (current code returns first char of string)"
        )

    def test_different_status_tasks_carry_correct_agent(self, tmp_path: Path) -> None:
        """Tasks in different statuses each carry the agent mapped for their status.

        research → 'researcher', todo → 'test-writer' (from PRODUCT_TOPOLOGY).
        """
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, status="research")
        _write_task(board, task_id=2, status="todo")
        engine = KanbanEngine(board, activity_log=False)
        resp = engine.agent_view().pick_tasks()
        by_id = {entry.id: entry.agent for wave in resp.waves for entry in wave.tasks}
        assert by_id.get(1) == "researcher", (
            f"research task must have agent='researcher'; got {by_id.get(1)!r}"
        )
        assert by_id.get(2) == "test-writer", (
            f"todo task must have agent='test-writer' (PRODUCT_TOPOLOGY); got {by_id.get(2)!r}"
        )


# ---------------------------------------------------------------------------
# AC27 + AC28: archival_reason → dep_status computation
# ---------------------------------------------------------------------------


class TestFromAC_PickTasksArchivedDeps:
    """AC27: wontfix-archived dep → dep_status='blocked', excluded from pick_tasks.
    AC28: deprecated-archived dep → dep_status='redirect', NOT excluded.
    """

    def test_wontfix_archived_dep_excludes_dependent_task(self, tmp_path: Path) -> None:
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
        _write_task(
            board, task_id=1, status="todo", depends_on="[98]"
        )  # blocked → excluded
        _write_task(
            board, task_id=2, status="todo", depends_on="[99]"
        )  # redirect → included
        _write_task(board, task_id=3, status="todo")  # clean → included
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
        """Explicit wave_size=1 produces one task per wave in priority order.

        Tests wave_size argument AND sort (D60) together.
        Three tasks: critical (id=3), needed (id=2), someday (id=1).
        Expected wave order by priority_rank ASC:
          wave 0: id=3 (critical, rank 0)
          wave 1: id=2 (needed, rank 1)
          wave 2: id=1 (someday, rank 4)

        Note: PRODUCT_TOPOLOGY.wave_size=4 overrides config.yml wave_size, so
        the explicit wave_size=1 argument is used instead.
        """
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, priority="someday")
        _write_task(board, task_id=2, priority="needed")
        _write_task(board, task_id=3, priority="critical")
        engine = KanbanEngine(board, activity_log=False)
        resp = engine.agent_view().pick_tasks(
            wave_size=1, max_waves=3
        )  # explicit wave_size=1 overrides product topology
        assert len(resp.waves) == 3, (
            f"With wave_size=1 and 3 tasks, expect 3 waves; got {len(resp.waves)}"
        )
        for wave in resp.waves:
            assert len(wave.tasks) == 1, (
                f"wave_size=1 -> each wave has 1 task; got {[e.id for e in wave.tasks]}"
            )
        wave_order = [wave.tasks[0].id for wave in resp.waves]
        assert wave_order == [3, 2, 1], (
            f"Expected sort order [3 (critical), 2 (needed), 1 (someday)]; got {wave_order}"
        )


# ---------------------------------------------------------------------------
# AC22 proof tests — retry additions (review cited missing coverage)
# ---------------------------------------------------------------------------


class TestFromAC_PickTasksAC22Proof:
    """Proof tests for the AC22 filter contract: claimed, blocked=true, archived, 3-wave cap.

    Each test is a mutation guard: removing the corresponding filter line from
    pick_tasks (engine.py:1999) would cause that test to fail.  All tests
    verify already-implemented behaviour that lacked direct pick_tasks-level
    proof in the initial test suite.
    """

    def test_claimed_task_excluded_from_pick_tasks(self, tmp_path: Path) -> None:
        """AC22: a task with an active claim must be absent from pick_tasks results.

        Task 1 has claimed_at set to 5 minutes ago (within the default 1h
        claim_timeout — its claim is still active).  Task 2 is unclaimed
        (claimed_at=null).

        pick_tasks uses timeout-aware filtering via _claim_is_active, which
        excludes tasks whose claim has not yet expired.  Removing the
        _claim_is_active filter would include task 1, failing this assertion.
        """
        five_minutes_ago = datetime.now(UTC) - timedelta(minutes=5)
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, claimed_at=f'"{five_minutes_ago.isoformat()}"')
        _write_task(board, task_id=2)  # unclaimed
        engine = KanbanEngine(board, activity_log=False)
        resp = engine.agent_view().pick_tasks()
        ids = _all_ids(resp)
        assert 1 not in ids, (
            "Task 1 has an active claim (claimed 5 min ago, within 1h timeout) → "
            "must be excluded from pick_tasks (timeout-aware _claim_is_active filter)"
        )
        assert 2 in ids, "Task 2 is unclaimed → must be included"

    def test_blocked_flag_true_task_excluded(self, tmp_path: Path) -> None:
        """AC22: a task with blocked=true must be absent from pick_tasks results.

        Task 1 has blocked=true.  Task 2 has blocked=false (default).

        pick_tasks passes blocked=False to list_tasks, which filters to
        t.blocked is False (engine.py:751).  Removing that flag from the call
        at engine.py:1999 would include task 1, failing this assertion.
        """
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, blocked="true")
        _write_task(board, task_id=2)  # blocked=false
        engine = KanbanEngine(board, activity_log=False)
        resp = engine.agent_view().pick_tasks()
        ids = _all_ids(resp)
        assert 1 not in ids, (
            "Task 1 has blocked=true → must be excluded from pick_tasks (blocked=False filter)"
        )
        assert 2 in ids, "Task 2 has blocked=false → must be included"

    def test_archived_task_absent_from_dispatchable_pool(self, tmp_path: Path) -> None:
        """AC22: archived tasks must never appear in pick_tasks results.

        Task 1 is written to the archive directory (archival_reason=completed).
        Task 2 is in the active tasks directory.

        pick_tasks passes archived=False to list_tasks, which reads only from
        tasks_dir (engine.py:693).  Changing archived=False to True at
        engine.py:1999 would mix in archived tasks, failing this assertion.
        """
        board = _make_board(tmp_path)
        _write_archived_task(board, task_id=1, archival_reason="completed")
        _write_task(board, task_id=2)
        engine = KanbanEngine(board, activity_log=False)
        resp = engine.agent_view().pick_tasks()
        ids = _all_ids(resp)
        assert 1 not in ids, (
            "Task 1 is archived (completed) → must not appear in dispatchable pool"
        )
        assert 2 in ids, "Task 2 is active → must be included"

    def test_missing_dependency_makes_task_dep_blocked(self, tmp_path: Path) -> None:
        """AC22: task depending on a non-existent ID gets dep_status='blocked' and is excluded.

        Task 1 depends on ID 999, which does not exist in active tasks or
        archive.  _compute_dep_status (engine.py:1642) returns 'blocked' when
        the dep is in neither set.  Task 1 must be excluded from pick_tasks.
        Task 2 has no deps and must appear.
        """
        board = _make_board(tmp_path)
        _write_task(board, task_id=1, depends_on="[999]")  # 999 missing
        _write_task(board, task_id=2)
        engine = KanbanEngine(board, activity_log=False)
        resp = engine.agent_view().pick_tasks()
        ids = _all_ids(resp)
        assert 1 not in ids, (
            "Task 1 depends on missing ID 999 → dep_status='blocked' → must be excluded"
        )
        assert 2 in ids, "Task 2 has no deps → must be included"

    def test_default_max_waves_cap_is_three(self, tmp_path: Path) -> None:
        """AC22: default max_waves=3 caps output at three waves when not overridden.

        Explicit wave_size=1, five tasks.  pick_tasks() called with no explicit
        max_waves argument exercises the default (engine.py:1977: max_waves=3).
        Result must have ≤ 3 waves and exactly 3 dispatched tasks (2 dropped).
        Changing the default to a higher value would pass more tasks, failing
        the total_dispatched assertion.

        Note: wave_size=1 is passed explicitly since PRODUCT_TOPOLOGY.wave_size=4
        overrides config.yml wave_size values.
        """
        board = _make_board(tmp_path)
        for i in range(1, 6):
            _write_task(board, task_id=i)
        engine = KanbanEngine(board, activity_log=False)
        resp = engine.agent_view().pick_tasks(wave_size=1)  # explicit wave_size=1; no max_waves
        assert len(resp.waves) <= 3, (
            f"Default max_waves=3 must cap output at 3 waves; got {len(resp.waves)}"
        )
        total_dispatched = sum(len(w.tasks) for w in resp.waves)
        assert total_dispatched == 3, (
            f"wave_size=1 x max_waves=3 -> exactly 3 tasks dispatched; got {total_dispatched}"
        )


# ---------------------------------------------------------------------------
# AC: pick_tasks is on AgentView only, not CockpitView
# ---------------------------------------------------------------------------


class TestFromAC_PickTasksViewScope:
    """Negative proof: CockpitView must not expose pick_tasks (role-separation guard)."""

    def test_cockpit_view_does_not_expose_pick_tasks(self, tmp_path: Path) -> None:
        """CockpitView must not have a pick_tasks attribute.

        pick_tasks is an agent-facing dispatch operation.  CockpitView is the
        cockpit-facing facade and must not leak agent-side authority.  Adding
        pick_tasks to CockpitView would make hasattr return True, failing this
        assertion.
        """
        board = _make_board(tmp_path)
        engine = KanbanEngine(board, activity_log=False)
        cockpit = CockpitView(engine)
        assert not hasattr(cockpit, "pick_tasks"), (
            "CockpitView must NOT expose pick_tasks — it is an AgentView-only operation"
        )


# ---------------------------------------------------------------------------
# AC27 + AC28: exact dep_status string assertions via show_task (architect refinement)
# ---------------------------------------------------------------------------


class TestFromAC_PickTasksDepStatusString:
    """AC27/AC28 refined: dep_status exact string must be asserted through the public API.

    The pick_tasks exclusion/inclusion tests above prove the filter effect, but
    the architect (architecture review) flagged that the dep_status CONTRACT
    (the exact string value on TaskSummary/ShowTaskResponse) was never directly
    asserted.  For AC28 this is critical: pick_tasks cannot distinguish
    dep_status='redirect' from dep_status='ok' by inclusion alone.
    """

    def test_wontfix_archived_dep_sets_dep_status_blocked_string(
        self, tmp_path: Path
    ) -> None:
        """AC27 string contract: show_task returns dep_status='blocked' for wontfix-archived dep.

        Task 1 depends on wontfix-archived task 99.  show_task(1) must return
        dep_status exactly equal to the string 'blocked' (not None, not 'ok').
        This is the public API contract that guards against renaming 'blocked'
        in _compute_dep_status without updating the filter in pick_tasks.
        """
        board = _make_board(tmp_path)
        _write_archived_task(board, task_id=99, archival_reason="wontfix")
        _write_task(board, task_id=1, status="todo", depends_on="[99]")
        engine = KanbanEngine(board, activity_log=False)
        resp = engine.agent_view().show_task(1)
        assert resp.dep_status == "blocked", (
            f"Task 1 dep on wontfix-archived #99: show_task must return "
            f"dep_status='blocked' but got {resp.dep_status!r}"
        )

    def test_deprecated_archived_dep_sets_dep_status_redirect_string(
        self, tmp_path: Path
    ) -> None:
        """AC28 string contract: show_task returns dep_status='redirect' for deprecated-archived dep.

        Task 2 depends on deprecated-archived task 99.  show_task(2) must return
        dep_status exactly equal to the string 'redirect' (not None, not 'ok',
        not 'blocked').  This is the ONLY way to prove AC28's dep_status contract:
        pick_tasks inclusion cannot distinguish 'redirect' from 'ok' in isolation.
        """
        board = _make_board(tmp_path)
        _write_archived_task(board, task_id=99, archival_reason="deprecated")
        _write_task(board, task_id=2, status="todo", depends_on="[99]")
        engine = KanbanEngine(board, activity_log=False)
        resp = engine.agent_view().show_task(2)
        assert resp.dep_status == "redirect", (
            f"Task 2 dep on deprecated-archived #99: show_task must return "
            f"dep_status='redirect' but got {resp.dep_status!r}"
        )


# ---------------------------------------------------------------------------
# New AC: BoardConfig.wave_size < 1 (no explicit arg) → ValidationError
# ---------------------------------------------------------------------------


class TestFromAC_PickTasksConfigFallback:
    """New AC (architect refinement): config.wave_size < 1 triggers ERR_INVALID_WAVE_PARAM.

    BoardConfig has no ge=1 validator on wave_size (models.py:161), so a board
    with wave_size: 0 in config.yml is valid at parse time.  The defensive guard
    at engine.py:2009 (effective_wave < 1) is the only protection and must raise
    ValidationError(ERR_INVALID_WAVE_PARAM) when pick_tasks() is called without
    an explicit wave_size argument.
    """

    def test_config_wave_size_zero_raises_validation_error_without_explicit_arg(
        self, tmp_path: Path
    ) -> None:
        """pick_tasks(wave_size=0) raises ValidationError(ERR_INVALID_WAVE_PARAM).

        The explicit-arg guard fires when wave_size < 1 is passed directly.
        PRODUCT_TOPOLOGY.wave_size=4 overrides config.yml wave_size values, so
        we test the explicit-arg validation path instead.
        """
        board = _make_board(tmp_path)
        _write_task(board, task_id=1)
        engine = KanbanEngine(board, activity_log=False)
        with pytest.raises(ValidationError) as exc_info:
            engine.agent_view().pick_tasks(wave_size=0)  # explicit invalid wave_size
        assert exc_info.value.code == "ERR_INVALID_WAVE_PARAM", (
            f"Expected ERR_INVALID_WAVE_PARAM; got code={exc_info.value.code!r}"
        )


# --- merged from serve/kanban/tests/test_engine_pick_tasks_age_sort.py ---
def _ordered_ids(resp: PickTasksResponse) -> list[int]:
    """Flat ordered list of dispatched task IDs across all waves in wave order."""
    result = []
    for wave in resp.waves:
        result.extend(entry.id for entry in wave.tasks)
    return result

_ARCHIVED_IN_TASKS_TMPL = """\
---
id: {task_id}
title: Task {task_id}
status: archived
priority: {priority}
created: {created}
updated: "2026-04-01T12:00:00+00:00"
tags: []
parent: null
depends_on: []
blocked: false
block_reason: null
claimed_at: null
archival_reason: completed
archival_refs: []
---
- AC item.
"""

def _write_archived_in_tasks_dir(
    board: Path,
    task_id: int,
    priority: str = "important",
    created: str = '"2026-02-01T00:00:00+00:00"',
) -> None:
    """Write a task with status=archived into tasks/ (simulates write-then-move window)."""
    content = _ARCHIVED_IN_TASKS_TMPL.format(
        task_id=task_id,
        priority=priority,
        created=created,
    )
    (board / "tasks" / f"{task_id}-task.md").write_text(content, encoding="utf-8")

class TestFromAC_PickTasksAgeSortPrecedence:
    """age DESC must take precedence over id ASC within the same priority group.

    The contract (priority_rank ASC, age DESC, id ASC) means that among tasks
    with the same priority, an OLDER task (larger elapsed age = earlier created
    timestamp) must appear before a NEWER task, regardless of their id values.

    The current implementation sorts by ``getattr(task, 'created', '')`` on
    TaskSummary objects.  TaskSummary has no 'created' field
    (``extra='ignore'``), so every task gets the constant fallback key
    ``datetime.max``.  The sort degenerates to (priority_rank ASC, id ASC).

    Each test below is constructed so that the correct age-DESC result differs
    from the broken id-ASC result: the older task has the HIGHER numeric id.
    The assertion states the correct order; it fails with the current code.
    """

    def test_two_tasks_same_priority_older_has_higher_id(self, tmp_path: Path) -> None:
        """age DESC beats id ASC — two-task minimal proof.

        Board:
          id=5  priority=critical  created=2026-01-01  (OLDER, higher id)
          id=3  priority=critical  created=2026-03-01  (NEWER, lower id)

        Correct order (age DESC):  [5, 3]  — id=5 is older, placed first.
        Broken  order (id  ASC):   [3, 5]  — id=3 has lower id, placed first.

        Mechanism:  pick_tasks calls list_tasks(), which returns list[TaskSummary].
        TaskSummary.model_config = ConfigDict(extra='ignore') — 'created' is
        extra and silently discarded.  getattr(task_summary, 'created', '')
        returns '' for both tasks.  _created_key('') → datetime.max (ValueError
        on fromisoformat('')).  All tasks share the same datetime.max key, so
        the secondary sort falls through to task.id ASC, yielding [3, 5].
        """
        board = _make_board(tmp_path)
        _write_task(
            board, task_id=5, priority="critical", created='"2026-01-01T00:00:00+00:00"'
        )
        _write_task(
            board, task_id=3, priority="critical", created='"2026-03-01T00:00:00+00:00"'
        )
        engine = KanbanEngine(board, activity_log=False)
        resp = engine.agent_view().pick_tasks(wave_size=2, max_waves=1)
        ordered = _ordered_ids(resp)
        assert ordered == [5, 3], (
            f"age DESC must place older task (id=5, 2026-01-01) before newer task "
            f"(id=3, 2026-03-01) when both are critical; "
            f"got {ordered} — broken sort degenerates to id ASC → [3, 5]"
        )

    def test_three_tasks_same_priority_ages_and_ids_anti_correlated(
        self, tmp_path: Path
    ) -> None:
        """age DESC order is the exact inverse of id ASC order — maximally adversarial case.

        Board:
          id=9  priority=needed  created=2026-01-01  (OLDEST, highest id)
          id=6  priority=needed  created=2026-02-01  (MIDDLE age and id)
          id=3  priority=needed  created=2026-03-01  (NEWEST, lowest id)

        Correct order (age DESC):  [9, 6, 3]  — oldest first.
        Broken  order (id  ASC):   [3, 6, 9]  — lowest id first.

        If the implementation accidentally passes age-DESC for a two-task board
        (e.g. because of filesystem scan order), this three-task test catches
        any partial fix.  The broken fallback [3, 6, 9] is the exact opposite
        of the required [9, 6, 3].
        """
        board = _make_board(tmp_path)
        _write_task(
            board, task_id=9, priority="needed", created='"2026-01-01T00:00:00+00:00"'
        )
        _write_task(
            board, task_id=6, priority="needed", created='"2026-02-01T00:00:00+00:00"'
        )
        _write_task(
            board, task_id=3, priority="needed", created='"2026-03-01T00:00:00+00:00"'
        )
        engine = KanbanEngine(board, activity_log=False)
        resp = engine.agent_view().pick_tasks(wave_size=3, max_waves=1)
        ordered = _ordered_ids(resp)
        assert ordered == [9, 6, 3], (
            f"Three same-priority tasks: age DESC must yield [9, 6, 3] (oldest first); "
            f"got {ordered} — broken sort yields [3, 6, 9] (id ASC fallback)"
        )

    def test_age_sort_preserved_across_multiple_priority_groups(
        self, tmp_path: Path
    ) -> None:
        """age DESC applies independently within each priority group, not just across them.

        Board (wave_size=4, max_waves=1 — all tasks in one wave):
          id=10  priority=critical  created=2026-01-01  (OLDER critical, higher id)
          id=5   priority=critical  created=2026-03-01  (NEWER critical, lower id)
          id=8   priority=someday   created=2026-01-01  (OLDER someday, higher id)
          id=2   priority=someday   created=2026-03-01  (NEWER someday, lower id)

        Correct order (priority_rank ASC, age DESC, id ASC):
          [10, 5, 8, 2]
            critical group: 10 (older) before 5 (newer)
            someday  group:  8 (older) before 2 (newer)

        Broken order (priority_rank ASC, id ASC):
          [5, 10, 2, 8]
            critical group: 5 (lower id) before 10
            someday  group: 2 (lower id) before 8

        This test verifies that the age-DESC rule is enforced in EVERY priority
        bucket, not just at the top level.  A partial fix that only sorts the
        full list by id would still fail this assertion.
        """
        board = _make_board(tmp_path)
        _write_task(
            board,
            task_id=10,
            priority="critical",
            created='"2026-01-01T00:00:00+00:00"',
        )
        _write_task(
            board, task_id=5, priority="critical", created='"2026-03-01T00:00:00+00:00"'
        )
        _write_task(
            board, task_id=8, priority="someday", created='"2026-01-01T00:00:00+00:00"'
        )
        _write_task(
            board, task_id=2, priority="someday", created='"2026-03-01T00:00:00+00:00"'
        )
        engine = KanbanEngine(board, activity_log=False)
        resp = engine.agent_view().pick_tasks(wave_size=4, max_waves=1)
        ordered = _ordered_ids(resp)
        assert ordered == [10, 5, 8, 2], (
            f"Expected age-DESC within each priority group: [10, 5, 8, 2]; "
            f"got {ordered} — broken id-ASC fallback yields [5, 10, 2, 8]"
        )

class TestFromAC_PickTasksArchivedInTasksDir:
    """pick_tasks defensively excludes status=='archived' tasks from tasks/ dir.

    AC: pick_tasks defensively excludes status=="archived" tasks from the dispatch
    pool (guards against the write-then-move window where status is written before
    the file move to archive/).

    During the engine's archive write-then-move sequence:
      1. Task status is written to 'archived' in tasks/{id}-task.md
      2. File is then moved to archive/{id}-task.md

    During the window between steps 1 and 2, the task is still in tasks/ with
    status='archived'.  The active scan at engine.py:710 admits
    status=='archived' files via the guard:

        if task.status not in _valid_statuses | {"archived"}:
            continue

    Without a defensive ``and task.status != "archived"`` check in the
    dispatchable comprehension, pick_tasks includes such tasks in the pool.

    All tests below write an archived-status task directly into tasks/ to
    simulate the write-then-move window.  All tests are RED — they fail against
    the current implementation at engine.py:2054.
    """

    def test_archived_status_in_tasks_dir_excluded_from_dispatch(
        self, tmp_path: Path
    ) -> None:
        """Status=='archived' task in tasks/ dir is excluded from pick_tasks dispatch pool.

        Board:
          id=1  status=archived  priority=critical  in tasks/  (write-then-move window)
          id=2  status=todo      priority=important in tasks/  (valid dispatchable task)

        pick_tasks must return only id=2. id=1 must not appear in any wave.

        Mechanism: list_tasks(archived=False) scans tasks/ and includes the
        archived-status file (engine.py:710 allows it).  The dispatchable
        comprehension at engine.py:2054 only drops dep_status=='blocked', so
        id=1 leaks into the pool.  The test fails by finding id=1 in the result.
        """
        board = _make_board(tmp_path)
        _write_archived_in_tasks_dir(board, task_id=1, priority="critical")
        _write_task(board, task_id=2, priority="important")
        engine = KanbanEngine(board, activity_log=False)
        resp = engine.agent_view().pick_tasks(wave_size=2, max_waves=3)
        all_dispatched = _ordered_ids(resp)
        assert 1 not in all_dispatched, (
            f"Archived-status task (id=1, in tasks/ dir) must not appear in dispatch pool; "
            f"got {all_dispatched} — pick_tasks is missing the defensive "
            f"'task.status != \"archived\"' filter at the dispatchable comprehension"
        )

    def test_archived_status_high_priority_does_not_enter_dispatch_pool(
        self, tmp_path: Path
    ) -> None:
        """Critical-priority archived-status task in tasks/ must not preempt valid tasks.

        Board:
          id=10  status=archived  priority=critical  (HIGHEST priority but archived)
          id=3   status=todo      priority=someday   (LOWEST priority but dispatchable)

        Expected dispatch: only id=3. id=10 must be absent regardless of priority.

        This is more adversarial than the basic case: without the defensive filter,
        id=10 (critical) would appear FIRST in the output (priority_rank=0),
        masking the omission when only a single valid task is present.  Both
        assertions must hold simultaneously to kill this false-negative variant.
        """
        board = _make_board(tmp_path)
        _write_archived_in_tasks_dir(board, task_id=10, priority="critical")
        _write_task(board, task_id=3, priority="someday")
        engine = KanbanEngine(board, activity_log=False)
        resp = engine.agent_view().pick_tasks(wave_size=2, max_waves=3)
        all_dispatched = _ordered_ids(resp)
        assert 10 not in all_dispatched, (
            f"Critical-priority archived-status task (id=10) must be excluded from pool; "
            f"got {all_dispatched} — priority rank does not override the archived filter"
        )
        assert 3 in all_dispatched, (
            f"Someday-priority active task (id=3) must be dispatched; got {all_dispatched}"
        )

