"""Failing tests for board_config() defensive copy (#805, RED phase).

AC coverage:
  AC1 - board_config() returns config with valid statuses and display order
        — verified by checking statuses survive a consumer mutation of a prior
        copy (order guarantee requires isolation)
  AC2 - board_config() returns config with valid priorities and display order
        — same pattern as AC1
  AC3 - returned object is a copy (mutation doesn't affect engine internal state)
        — three tests: append to statuses list, append to priorities list,
        mutate a nested status dict

All tests in this file MUST FAIL until #805 is implemented GREEN
(fix: model_copy(deep=True) in engine.board_config()).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from owlbear_kanban import KanbanEngine

# ---------------------------------------------------------------------------
# Shared config — mirrors _BASE_CONFIG_YAML from test_config_staleness_fix_828.py
# ---------------------------------------------------------------------------

_BASE_CONFIG_YAML = """\
version: 10
board:
    name: OwlBear
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
tui:
    title_lines: 2
    hide_empty_columns: true
next_id: 100
"""

_EXPECTED_STATUS_NAMES = ["research", "backlog", "todo", "in-progress", "review", "docs", "done"]
_EXPECTED_PRIORITIES = ["someday", "nice-to-have", "important", "needed", "critical"]


@pytest.fixture()
def kanban_dir(tmp_path: Path) -> Path:
    """Minimal kanban directory with config.yml and empty tasks/ sub-dir."""
    (tmp_path / "config.yml").write_text(_BASE_CONFIG_YAML, encoding="utf-8")
    (tmp_path / "tasks").mkdir()
    return tmp_path


@pytest.fixture()
def engine(kanban_dir: Path) -> KanbanEngine:
    """KanbanEngine instance wired to the temp kanban_dir."""
    return KanbanEngine(kanban_dir)


# ===========================================================================
# TestFromAC_BoardConfig
# AC1: statuses content and display order
# AC2: priorities content and display order
# AC3: returned object is a defensive copy
# ===========================================================================


class TestFromAC_BoardConfig:
    """Tests for KanbanEngine.board_config() — content, order, and copy isolation."""

    # ------------------------------------------------------------------
    # AC1 — statuses: valid content and display order
    # Designed RED: proves the order guarantee requires copy isolation.
    # If mutation leaks, the second call returns the mutated (wrong) list.
    # ------------------------------------------------------------------

    def test_board_config_statuses_display_order_survives_consumer_mutation(
        self, engine: KanbanEngine
    ) -> None:
        """board_config() statuses order is stable after a consumer clears a prior copy.

        With a shallow copy, clearing copy1.statuses also clears engine's
        internal list, so the second call returns an empty list.  A proper
        deep copy must break that reference so the order guarantee holds.
        """
        copy1 = engine.board_config()
        copy1.statuses.clear()  # consumer side-effect; must not affect engine

        copy2 = engine.board_config()
        actual_names = [s["name"] for s in copy2.statuses]
        assert actual_names == _EXPECTED_STATUS_NAMES

    # ------------------------------------------------------------------
    # AC2 — priorities: valid content and display order
    # Designed RED: same isolation-via-ordering proof for priorities.
    # ------------------------------------------------------------------

    def test_board_config_priorities_display_order_survives_consumer_mutation(
        self, engine: KanbanEngine
    ) -> None:
        """board_config() priorities order is stable after a consumer clears a prior copy.

        With a shallow copy, clearing copy1.priorities also clears the engine's
        internal list.  A deep copy must isolate them so the order is preserved.
        """
        copy1 = engine.board_config()
        copy1.priorities.clear()  # consumer side-effect; must not affect engine

        copy2 = engine.board_config()
        assert copy2.priorities == _EXPECTED_PRIORITIES

    # ------------------------------------------------------------------
    # AC3a — appending to returned statuses list must not leak to engine
    # ------------------------------------------------------------------

    def test_board_config_statuses_append_does_not_leak_to_engine(
        self, engine: KanbanEngine
    ) -> None:
        """Appending a status to the returned copy must not be visible in a second call.

        With model_copy() (shallow), copy.statuses is the same list object as
        engine._config.statuses, so appending to it mutates engine state.
        """
        copy = engine.board_config()
        original_count = len(copy.statuses)
        copy.statuses.append({"name": "INJECTED"})

        second = engine.board_config()
        assert len(second.statuses) == original_count

    # ------------------------------------------------------------------
    # AC3b — appending to returned priorities list must not leak to engine
    # ------------------------------------------------------------------

    def test_board_config_priorities_append_does_not_leak_to_engine(
        self, engine: KanbanEngine
    ) -> None:
        """Appending a priority to the returned copy must not be visible in a second call.

        With model_copy() (shallow), copy.priorities is the same list object
        as engine._config.priorities.
        """
        copy = engine.board_config()
        original_count = len(copy.priorities)
        copy.priorities.append("INJECTED")

        second = engine.board_config()
        assert len(second.priorities) == original_count

    # ------------------------------------------------------------------
    # AC3c — mutating a nested status dict must not leak to engine
    # ------------------------------------------------------------------

    def test_board_config_nested_status_dict_mutation_does_not_leak_to_engine(
        self, engine: KanbanEngine
    ) -> None:
        """Mutating a dict inside the returned statuses list must not affect engine state.

        With model_copy() (shallow), copy.statuses[0] is the same dict object
        as engine._config.statuses[0], so adding a key mutates engine state.
        """
        copy = engine.board_config()
        copy.statuses[0]["INJECTED_KEY"] = True  # mutate nested dict

        second = engine.board_config()
        assert "INJECTED_KEY" not in second.statuses[0]
