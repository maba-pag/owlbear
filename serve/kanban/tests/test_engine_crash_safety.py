"""Engine create_task crash-safety tests (AC-C51-engine).

Task:  #1101 — Engine create_task crash-safety test (AC-C51-engine)
AC:    AC-1 (crash scenario / burned ID), AC-2 (allocate_next_id routing), AC-3 (regression)
Depends on: #1062 (engine refactor to allocate_next_id)
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_kanban.config_loader import load_config
from owlbear_kanban.storage import allocate_next_id

# ---------------------------------------------------------------------------
# Board fixture in current BoardConfig schema.
# ---------------------------------------------------------------------------

_CONFIG_YAML = """\
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
entry_status: research
terminal_status: done
wave_size: 4
agent_map:
    research: researcher
    backlog: architect
    todo: builder
    in-progress: builder
    review: reviewer
    docs: doc-writer
    done: auditor
agent_types: {}
agent_compatibility: {}
non_impl_tags: [research, docs]
archival_reasons: [completed, deprecated, dropped, duplicate, wontfix]
status_predicates: {}
claim_timeout: 1h
next_id: 1001
tasks_dir: tasks
archive_dir: archive
activity_log: false
"""


def _make_board(base_dir: Path) -> Path:
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestFromAC_EngineCrashSafety:
    """AC-2b, AC-3 — engine-level crash-safety after #1062 refactor."""

    # ------------------------------------------------------------------
    # AC-2b: create_task calls allocate_next_id (flock-guarded) not
    #         inline config.next_id read/write.
    # ------------------------------------------------------------------

    def test_ac2_create_task_routes_through_allocate_next_id(self, tmp_path: Path) -> None:
        """AC-2: allocate_next_id is called exactly once per create_task invocation.

        Patches owlbear_kanban.storage.allocate_next_id with a wrapping spy.
        """
        kanban_dir = _make_board(tmp_path)
        engine = KanbanEngine(kanban_dir)

        with patch(
            "owlbear_kanban.storage.allocate_next_id",
            wraps=allocate_next_id,
        ) as spy:
            engine.create_task("routing-check")

        assert spy.call_count == 1, (
            f"create_task must call allocate_next_id exactly once; "
            f"got call_count={spy.call_count}. "
            "create_task did not route ID allocation through allocate_next_id."
        )

    # ------------------------------------------------------------------
    # AC-3: Regression — basic create_task contract is preserved after
    #       the #1062 refactor (correct id, title, file on disk, config).
    # ------------------------------------------------------------------

    def test_ac3_create_task_contract_preserved_with_new_routing(self, tmp_path: Path) -> None:
        """AC-3: create_task still returns a correct Task and updates config.

        Regression guard verifying that the #1062 allocate_next_id refactor does
        not break existing create_task behavior. Includes a routing check with
        the same allocate_next_id spy assertion used in AC-2b.
        """
        kanban_dir = _make_board(tmp_path)
        engine = KanbanEngine(kanban_dir)

        with patch(
            "owlbear_kanban.storage.allocate_next_id",
            wraps=allocate_next_id,
        ) as spy:
            task = engine.create_task("regression-task")

        # --- Basic contract (scan-based #1443) ---
        # Empty board → scan finds no files → max=0 → ID=1 (ignores config.next_id=1001)
        assert task.id == 1, (
            f"Scan-based empty board must allocate ID 1 (ignores config.next_id=1001); "
            f"got {task.id}. create_task is still reading config.next_id."
        )
        assert task.title == "regression-task"

        task_files = list((kanban_dir / "tasks").glob("1-*.md"))
        assert len(task_files) == 1, "Task file must be written to tasks/ dir with ID 1"

        config_after = load_config(kanban_dir)
        assert config_after.next_id == 1001, (
            f"config.next_id must be unchanged after scan-based create_task; "
            f"expected 1001 (board initial), got {config_after.next_id}. "
            "allocate_next_id is still incrementing config.next_id."
        )

        # --- Routing assertion ---
        assert spy.call_count == 1, (
            f"AC-3 regression: create_task must route through allocate_next_id (call_count=1), got {spy.call_count}."
        )
