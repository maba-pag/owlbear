"""Supplementary GREEN verification tests for create_task implicit config refresh (#844).

These tests verify *existing* behavior — NOT a RED→GREEN TDD pair.
Architecture Review (2026-04-12) confirmed the implementation is already in place
(engine.py lines 294-296: self._config = config; self._tasks_dir = ...).
Tests are expected to PASS immediately on first run.

AC coverage:
  AC1 - after external config change on disk (e.g. new status added),
        create_task reflects the new config in self._config (not just local variable)
        — verified via board_config().statuses containing the newly added status
        and statuses count matching the extended config

  AC2 - calling create_task after disk config change uses the refreshed _tasks_dir
        and rank maps (consistent with refresh_config() behavior)
        — verified via board_config() consistency with an explicit refresh_config() call,
        and rank-derived state (new status immediately usable without explicit refresh)
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

_BASE_STATUS_COUNT = 7  # number of statuses in _BASE_CONFIG_YAML


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


def _config_with_extra_status(extra_status: str = "blocked") -> str:
    """Return _BASE_CONFIG_YAML with *extra_status* appended after 'done'."""
    return _BASE_CONFIG_YAML.replace(
        "    - name: done\n",
        f"    - name: done\n    - name: {extra_status}\n",
    )


# ===========================================================================
# TestFromAC_CreateTaskImplicitConfigRefresh
#
# AC1: self._config is updated with the full reloaded BoardConfig (not only
#      next_id) after create_task completes.
# AC2: _tasks_dir and rank maps (derived from self._config) are consistent
#      with the state produced by an explicit refresh_config() call.
# ===========================================================================


class TestFromAC_CreateTaskImplicitConfigRefresh:
    """Supplementary GREEN verification for create_task's implicit self._config update.

    Arch Review (2026-04-12): verifies existing behaviour; all tests expected
    to PASS without source changes.  The implicit refresh path tested here
    (external disk change → create_task alone) is NOT covered by
    test_config_staleness_fix_828.py (which focuses on next_id and tasks_dir
    physical writes) or test_refresh_config_803.py (which uses explicit refresh).
    """

    # --- AC1: full config (including new statuses) is in self._config ------

    def test_new_status_present_in_board_config_after_external_addition(
        self, kanban_dir: Path, engine: KanbanEngine
    ) -> None:
        """board_config().statuses contains a status added to disk before create_task.

        External disk change appends 'blocked' to statuses.  After create_task's
        implicit config reload, self._config must hold the FULL updated config —
        not merely have its next_id incremented from the stale copy.
        """
        (kanban_dir / "config.yml").write_text(
            _config_with_extra_status("blocked"), encoding="utf-8"
        )

        engine.create_task("Trigger implicit refresh")

        status_names = {s["name"] for s in engine.board_config().statuses}
        assert "blocked" in status_names

    def test_statuses_count_reflects_external_addition_after_create(
        self, kanban_dir: Path, engine: KanbanEngine
    ) -> None:
        """board_config().statuses length is _BASE_STATUS_COUNT + 1 after disk adds one status.

        Guards against a partial fix that only updates next_id but leaves the
        statuses list stale at the original seven entries.
        """
        (kanban_dir / "config.yml").write_text(
            _config_with_extra_status("blocked"), encoding="utf-8"
        )

        engine.create_task("Statuses count check")

        assert len(engine.board_config().statuses) == _BASE_STATUS_COUNT + 1

    # --- AC2: rank maps and _tasks_dir match refresh_config() result -------

    def test_statuses_after_create_match_refresh_config_after_external_change(
        self, kanban_dir: Path, engine: KanbanEngine
    ) -> None:
        """board_config().statuses after create_task equals the value after refresh_config().

        The status rank map (derived from self._config.statuses) must be
        identical whether produced by create_task's implicit reload or an
        explicit refresh_config() call on the same disk state.
        """
        (kanban_dir / "config.yml").write_text(
            _config_with_extra_status("blocked"), encoding="utf-8"
        )

        engine.create_task("Rank consistency check")
        statuses_after_create = engine.board_config().statuses

        engine.refresh_config()
        statuses_after_refresh = engine.board_config().statuses

        assert statuses_after_create == statuses_after_refresh

    def test_new_status_usable_in_next_create_without_explicit_refresh(
        self, kanban_dir: Path, engine: KanbanEngine
    ) -> None:
        """New status added to disk is immediately valid for a subsequent create_task.

        After create_task picks up the new config implicitly, the next
        create_task(status='blocked') must NOT raise ValueError.  Confirms
        the valid-statuses set (rank map input) is derived from the updated
        self._config rather than the stale initial copy.
        """
        (kanban_dir / "config.yml").write_text(
            _config_with_extra_status("blocked"), encoding="utf-8"
        )

        engine.create_task("Trigger implicit reload")

        # New status must be accepted — no explicit refresh_config() call
        task = engine.create_task("Use new status", status="blocked")
        assert task.status == "blocked"

    def test_priorities_after_create_match_refresh_config_after_external_change(
        self, kanban_dir: Path, engine: KanbanEngine
    ) -> None:
        """board_config().priorities after create_task equals the value after refresh_config().

        Adds 'urgent' to the priorities list on disk.  Verifies the priority
        rank map (derived from self._config.priorities) is consistent between
        the implicit reload and an explicit refresh_config() call.
        """
        new_config = _BASE_CONFIG_YAML.replace(
            "    - critical\ndefaults:",
            "    - critical\n    - urgent\ndefaults:",
        )
        (kanban_dir / "config.yml").write_text(new_config, encoding="utf-8")

        engine.create_task("Priority rank check")
        priorities_after_create = engine.board_config().priorities

        engine.refresh_config()
        priorities_after_refresh = engine.board_config().priorities

        assert priorities_after_create == priorities_after_refresh
