"""Failing tests for board_config() defensive copy — implementation task #806.

AC coverage:
  AC1 - board_config() method on KanbanEngine returns a BoardConfig instance
        with valid statuses and priorities (consumer-facing content)
  AC2 - Returns model_copy() of cached config (valid fields: version, board,
        tasks_dir, defaults, statuses display order, priorities display order)
  AC3 - Returned object is a defensive copy — mutating nested Pydantic sub-models
        (board, defaults) does not affect engine state; scalar field replacement
        does not affect engine state

NOTE: The #805 builder implemented model_copy(deep=True) out-of-order — all
tests in this file pass GREEN immediately.  They are retained as regression
coverage complementing test_board_config_805.py (which covers statuses/priorities
list mutation; this file covers board/defaults sub-model mutation and scalar-field
content verification).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_kanban.models import BoardConfig

# ---------------------------------------------------------------------------
# Shared config — mirrors _BASE_CONFIG_YAML from test_board_config_805.py
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
# TestFromAC_BoardConfig_806
# AC1: board_config() exists and returns a BoardConfig instance
# AC2: returned config has correct scalar field values as loaded from config.yml
# AC3: defensive copy — sub-model (board, defaults) mutation does not leak
# ===========================================================================


class TestFromAC_BoardConfig_806:
    """Tests for KanbanEngine.board_config() — scalar content and sub-model isolation."""

    # ------------------------------------------------------------------
    # AC1 — method exists and returns a BoardConfig instance
    # ------------------------------------------------------------------

    def test_board_config_returns_board_config_instance(self, engine: KanbanEngine) -> None:
        """board_config() must return an instance of BoardConfig, not None or raw dict."""
        result = engine.board_config()
        assert isinstance(result, BoardConfig)

    # ------------------------------------------------------------------
    # AC2 — scalar field content matches config.yml values
    # ------------------------------------------------------------------

    def test_board_config_version_matches_config(self, engine: KanbanEngine) -> None:
        """board_config() must return config with version matching config.yml."""
        config = engine.board_config()
        assert config.version == 10

    def test_board_config_board_name_matches_config(self, engine: KanbanEngine) -> None:
        """board_config() must return config whose board.name matches config.yml."""
        config = engine.board_config()
        assert config.board.name == "OwlBear"

    def test_board_config_tasks_dir_matches_config(self, engine: KanbanEngine) -> None:
        """board_config() must return config whose tasks_dir matches config.yml."""
        config = engine.board_config()
        assert config.tasks_dir == "tasks"

    def test_board_config_default_status_matches_config(self, engine: KanbanEngine) -> None:
        """board_config() must return config whose defaults.status matches config.yml."""
        config = engine.board_config()
        assert config.defaults.status == "research"

    def test_board_config_default_priority_matches_config(self, engine: KanbanEngine) -> None:
        """board_config() must return config whose defaults.priority matches config.yml."""
        config = engine.board_config()
        assert config.defaults.priority == "important"

    # ------------------------------------------------------------------
    # AC2 — repeated calls return equal but distinct objects
    # ------------------------------------------------------------------

    def test_board_config_repeated_calls_return_equal_objects(
        self, engine: KanbanEngine
    ) -> None:
        """Two successive calls with no writes between them return equivalent configs.

        This verifies that the engine's cached _config remains stable and that
        each copy faithfully mirrors the same cached source.
        """
        copy1 = engine.board_config()
        copy2 = engine.board_config()
        assert copy1.statuses == copy2.statuses
        assert copy1.priorities == copy2.priorities
        assert copy1.version == copy2.version

    def test_board_config_repeated_calls_return_distinct_objects(
        self, engine: KanbanEngine
    ) -> None:
        """Two successive calls must return distinct objects, not the same identity.

        If board_config() returned engine._config directly (no copy), mutating
        one return value would mutate all subsequent return values.
        """
        copy1 = engine.board_config()
        copy2 = engine.board_config()
        assert copy1 is not copy2

    # ------------------------------------------------------------------
    # AC3 — sub-model mutation isolation: board.name
    # With shallow model_copy(), copy.board is the same BoardInfo object as
    # engine._config.board, so mutating copy.board.name corrupts engine state.
    # ------------------------------------------------------------------

    def test_board_config_board_submodel_mutation_does_not_leak_to_engine(
        self, engine: KanbanEngine
    ) -> None:
        """Mutating board.name on the returned copy must not affect engine state.

        With model_copy() (shallow), copy.board is the same BoardInfo instance
        as engine._config.board — assigning copy.board.name changes the engine's
        cached name.  A deep copy must break that reference.
        """
        copy = engine.board_config()
        copy.board.name = "INJECTED"

        second = engine.board_config()
        assert second.board.name == "OwlBear"

    # ------------------------------------------------------------------
    # AC3 — sub-model mutation isolation: defaults.status
    # With shallow model_copy(), copy.defaults is the same BoardDefaults object.
    # ------------------------------------------------------------------

    def test_board_config_defaults_submodel_mutation_does_not_leak_to_engine(
        self, engine: KanbanEngine
    ) -> None:
        """Mutating defaults.status on the returned copy must not affect engine state.

        With model_copy() (shallow), copy.defaults is the same BoardDefaults
        instance as engine._config.defaults — assigning a new status corrupts
        the engine's cached defaults.  A deep copy must isolate them.
        """
        copy = engine.board_config()
        copy.defaults.status = "done"

        second = engine.board_config()
        assert second.defaults.status == "research"
