"""Tests for AgentView.pick_tasks — age-DESC sort correctness (task #1076).

AC: Sort deterministic: priority_rank(BoardConfig.priorities index) ASC,
    age DESC, id ASC.

Root cause targeted by this file:
  TaskSummary.model_config = ConfigDict(extra='ignore') and TaskSummary has no
  'created' field, so TaskSummary.model_validate(task.model_dump()) silently
  discards 'created'.  pick_tasks calls self.engine.list_tasks() which returns
  list[TaskSummary], then sorts by:

      getattr(task, "created", "")   → always "" (no attribute on TaskSummary)
      _created_key("") → datetime.fromisoformat("") raises ValueError
                       → returns datetime.max

  Every task gets the same datetime.max key, so the sort degenerates to
  (priority_rank ASC, id ASC) — the "age DESC" component is silently dropped.

  A correct implementation must either pass sort="created" to list_tasks()
  (before TaskSummary projection) or include 'created' in TaskSummary.

All tests are RED — they fail against the current implementation.
"""

from __future__ import annotations

from pathlib import Path

from owlbear_kanban import KanbanEngine
from owlbear_kanban.models import PickTasksResponse

# ---------------------------------------------------------------------------
# Board / task helpers — minimal, self-contained
# ---------------------------------------------------------------------------

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

_TASK_TMPL = """\
---
id: {task_id}
title: Task {task_id}
status: todo
priority: {priority}
created: {created}
updated: "2026-04-01T12:00:00+00:00"
tags: []
parent: null
depends_on: []
blocked: false
block_reason: null
claimed_at: null
archival_reason: null
archival_refs: []
---
Body text.
"""


def _make_board(tmp_path: Path) -> Path:
    board = tmp_path / "board"
    board.mkdir(parents=True)
    (board / "config.yml").write_text(_BASE_CONFIG, encoding="utf-8")
    (board / "tasks").mkdir()
    (board / "archive").mkdir()
    return board


def _write_task(
    board: Path,
    task_id: int,
    priority: str = "important",
    created: str = '"2026-02-01T00:00:00+00:00"',
) -> None:
    content = _TASK_TMPL.format(
        task_id=task_id,
        priority=priority,
        created=created,
    )
    (board / "tasks" / f"{task_id}-task.md").write_text(content, encoding="utf-8")


def _ordered_ids(resp: PickTasksResponse) -> list[int]:
    """Flat ordered list of dispatched task IDs across all waves in wave order."""
    result = []
    for wave in resp.waves:
        result.extend(entry.id for entry in wave.tasks)
    return result


# ---------------------------------------------------------------------------
# AC: Sort age DESC — older tasks must precede newer tasks of equal priority,
#     even when the older task has a higher numeric id (age beats id).
# ---------------------------------------------------------------------------


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
        _write_task(board, task_id=5, priority="critical", created='"2026-01-01T00:00:00+00:00"')
        _write_task(board, task_id=3, priority="critical", created='"2026-03-01T00:00:00+00:00"')
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
        _write_task(board, task_id=9, priority="needed", created='"2026-01-01T00:00:00+00:00"')
        _write_task(board, task_id=6, priority="needed", created='"2026-02-01T00:00:00+00:00"')
        _write_task(board, task_id=3, priority="needed", created='"2026-03-01T00:00:00+00:00"')
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
        _write_task(board, task_id=10, priority="critical", created='"2026-01-01T00:00:00+00:00"')
        _write_task(board, task_id=5, priority="critical", created='"2026-03-01T00:00:00+00:00"')
        _write_task(board, task_id=8, priority="someday", created='"2026-01-01T00:00:00+00:00"')
        _write_task(board, task_id=2, priority="someday", created='"2026-03-01T00:00:00+00:00"')
        engine = KanbanEngine(board, activity_log=False)
        resp = engine.agent_view().pick_tasks(wave_size=4, max_waves=1)
        ordered = _ordered_ids(resp)
        assert ordered == [10, 5, 8, 2], (
            f"Expected age-DESC within each priority group: [10, 5, 8, 2]; "
            f"got {ordered} — broken id-ASC fallback yields [5, 10, 2, 8]"
        )
