"""TDD RED: Engine create_task crash-safety tests (AC-C51-engine).

Task:  #1101 — Engine create_task crash-safety test (AC-C51-engine)
AC:    AC-1 (crash scenario / burned ID), AC-2 (allocate_next_id routing), AC-3 (regression)
Depends on: #1062 (engine refactor to allocate_next_id)

All tests FAIL (RED phase) because the current engine.create_task allocates IDs
inline (write_task BEFORE save_config).  After #1062 refactors create_task to
call allocate_next_id(), config is saved first — inside the flock — so an
interrupted write_task burns the ID safely.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_kanban.config_loader import load_config
from owlbear_kanban.storage import allocate_next_id

# ---------------------------------------------------------------------------
# Board fixture — legacy schema so the migration gate in KanbanEngine.__init__
# is skipped (version field present ⇒ is_legacy_schema=True).
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
claim_timeout: 1h
next_id: 1001
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
    """AC-1, AC-2, AC-3 — engine-level crash-safety after #1062 refactor."""

    # ------------------------------------------------------------------
    # AC-1: crash after ID allocation burns the ID; next create_task
    #       returns the next sequential ID (burned ID never reused).
    # ------------------------------------------------------------------

    def test_ac1_crash_after_id_allocation_burns_id(self, tmp_path: Path) -> None:
        """AC-1: OSError in write_task after allocate_next_id; next call skips burned ID.

        Post-#1062 order:
          allocate_next_id() → save_config (next_id=1002) → [flock released]
          write_task() → OSError

        Expected state after crash:
          config.next_id == 1002  (already saved by allocate_next_id)
          no task file at ID 1001 (write_task never completed)
          next create_task returns task.id == 1002

        Currently FAILS because config.next_id remains 1001 after crash
        (save_config is not called until AFTER write_task in the current engine).
        """
        kanban_dir = _make_board(tmp_path)
        engine = KanbanEngine(kanban_dir)

        # Patch write_task in engine's namespace so the first call raises OSError
        calls: list[int] = []

        from owlbear_kanban.storage import write_task as _real_write_task  # noqa: PLC0415

        def _crash_on_first(task: object, kanban_dir: Path) -> None:
            calls.append(1)
            if len(calls) == 1:
                msg = "simulated disk failure during task write"
                raise OSError(msg)
            _real_write_task(task, kanban_dir)

        with (
            patch("owlbear_kanban.engine.write_task", side_effect=_crash_on_first),
            pytest.raises(OSError, match="simulated disk failure"),
        ):
            engine.create_task("crash-victim")

        # --- Assert: config.next_id already saved by allocate_next_id before crash ---
        config_after_crash = load_config(kanban_dir)
        assert config_after_crash.next_id == 1002, (
            f"Expected config.next_id=1002 after crash (allocate_next_id must save "
            f"config before write_task is called), got {config_after_crash.next_id}. "
            "Current engine saves config AFTER write_task — refactor required."
        )

        # --- Assert: no task file at the burned ID ---
        burned_files = list((kanban_dir / "tasks").glob("1001-*.md"))
        assert burned_files == [], (
            f"Burned ID 1001 must have no task file on disk; found {burned_files}"
        )

        # --- Assert: next create_task skips burned ID, returns 1002 ---
        task = engine.create_task("after-crash")
        assert task.id == 1002, (
            f"Expected task.id=1002 (burned slot 1001 skipped), got {task.id}. "
            "Engine must not re-allocate the burned ID."
        )

    # ------------------------------------------------------------------
    # AC-2a: config.next_id is already incremented at the moment
    #         write_task is called — observable proof that allocate_next_id
    #         (save_config inside flock) runs BEFORE write_task.
    # ------------------------------------------------------------------

    def test_ac2_config_saved_before_write_task_executes(self, tmp_path: Path) -> None:
        """AC-2: config.next_id is 1002 at the moment write_task is invoked.

        Intercepts write_task and snapshots config state during that call.
        Post-#1062: allocate_next_id saves next_id=1002 first; write_task sees 1002.
        Currently FAILS: config.next_id is still 1001 when write_task is called
        (save_config not yet executed at that point in the current engine).
        """
        kanban_dir = _make_board(tmp_path)
        engine = KanbanEngine(kanban_dir)

        from owlbear_kanban.storage import write_task as _real_write_task  # noqa: PLC0415

        config_next_id_at_write: list[int] = []

        def _spy_write_task(task: object, kanban_dir: Path) -> None:
            # Capture config state AT the moment write_task is called
            config_next_id_at_write.append(load_config(kanban_dir).next_id)
            _real_write_task(task, kanban_dir)

        with patch("owlbear_kanban.engine.write_task", side_effect=_spy_write_task):
            engine.create_task("spy-subject")

        assert len(config_next_id_at_write) == 1, "write_task must be called exactly once"
        observed_next_id = config_next_id_at_write[0]
        assert observed_next_id == 1002, (
            f"config.next_id must be 1002 when write_task executes "
            f"(allocate_next_id saves config first), got {observed_next_id}. "
            "Current engine: next_id is still 1001 at write_task time — save_config runs later."
        )

    # ------------------------------------------------------------------
    # AC-2b: create_task calls allocate_next_id (flock-guarded) not
    #         inline config.next_id read/write.
    # ------------------------------------------------------------------

    def test_ac2_create_task_routes_through_allocate_next_id(self, tmp_path: Path) -> None:
        """AC-2: allocate_next_id is called exactly once per create_task invocation.

        Patches owlbear_kanban.storage.allocate_next_id with a wrapping spy.
        Currently FAILS: current engine does not call allocate_next_id at all
        (allocates IDs inline with config.next_id inside its own flock section).
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
            "Current engine allocates IDs inline — does not call allocate_next_id."
        )

    # ------------------------------------------------------------------
    # AC-3: Regression — basic create_task contract is preserved after
    #       the #1062 refactor (correct id, title, file on disk, config).
    #       Combined with routing check so this test fails in RED phase.
    # ------------------------------------------------------------------

    def test_ac3_create_task_contract_preserved_with_new_routing(
        self, tmp_path: Path
    ) -> None:
        """AC-3: create_task still returns a correct Task and updates config.

        Regression guard verifying that the #1062 allocate_next_id refactor does
        not break existing create_task behavior. Routing check (spy) makes this
        fail in RED phase — same assertion as AC-2b but scoped to the regression.
        """
        kanban_dir = _make_board(tmp_path)
        engine = KanbanEngine(kanban_dir)

        with patch(
            "owlbear_kanban.storage.allocate_next_id",
            wraps=allocate_next_id,
        ) as spy:
            task = engine.create_task("regression-task")

        # --- Basic contract --- (these assertions pass even without the refactor)
        assert task.id == 1001
        assert task.title == "regression-task"

        task_files = list((kanban_dir / "tasks").glob("1001-*.md"))
        assert len(task_files) == 1, "Task file must be written to tasks/ dir"

        config_after = load_config(kanban_dir)
        assert config_after.next_id == 1002, (
            f"config.next_id must be 1002 after create_task; got {config_after.next_id}"
        )

        # --- Routing assertion (fails in RED) ---
        assert spy.call_count == 1, (
            f"AC-3 regression: create_task must route through allocate_next_id "
            f"(call_count=1), got {spy.call_count}. Refactor not yet applied."
        )
