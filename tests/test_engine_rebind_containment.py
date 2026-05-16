"""Failing tests for create_task post-write rebind containment (#1357).

All tests must be RED (failing) until the builder implements:
  - validate_path_containment(self._kanban_dir, self._tasks_dir) after rebind in create_task
  - validate_path_containment(self._kanban_dir, self._archive_dir) after rebind in create_task
  (engine.py ~L1035-1036)

Threat model: if a symlink target changes between engine construction and the
load_config reload that follows write_task, the rebound _tasks_dir/_archive_dir
can resolve outside kanban_dir, poisoning engine state for all subsequent ops.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from owlbear_kanban import KanbanEngine
from owlbear_kanban.config_loader import load_config

# ---------------------------------------------------------------------------
# Minimal board config (grouped schema) — provenance: mirrors 1351 test helper
# ---------------------------------------------------------------------------

_CONFIG_YAML = """\
next_id: 1
"""


# ---------------------------------------------------------------------------
# Board / engine helpers
# ---------------------------------------------------------------------------


def _make_board(base_dir: Path) -> Path:
    """Create a minimal valid kanban board. Returns kanban_dir."""
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


def _make_engine(kanban_dir: Path) -> KanbanEngine:
    """Return an initialised KanbanEngine for the board."""
    return KanbanEngine(kanban_dir, activity_log=False)


def _poisoned_config(tasks_dir_name: str, archive_dir_name: str) -> MagicMock:
    """Return a mock BoardConfig where paths resolve to the given dir names.

    Uses MagicMock so that str path attribute access (used in
    ``self._tasks_dir = self._kanban_dir / self._config.paths.tasks_dir``)
    returns the provided string values, triggering validate_path_containment
    on the resulting Path when called by the builder's fix.
    """
    mock = MagicMock()
    mock.paths.tasks_dir = tasks_dir_name
    mock.paths.archive_dir = archive_dir_name
    return mock


def _side_effect_first_real_then_poisoned(
    real_config: object,
    poisoned: object,
) -> list[object]:
    """Return a side_effect list: [real_config, poisoned] for two load_config calls.

    create_task makes exactly two calls to load_config (name 'load_config' in
    engine module):
      1. Initial pre-write load for status/priority validation (line ~976)
      2. Post-write reload for _tasks_dir/_archive_dir rebind (line ~1033)
    """
    return [real_config, poisoned]


# ---------------------------------------------------------------------------
# AC1 + AC2 — post-write rebind must call validate_path_containment
# ---------------------------------------------------------------------------


class TestFromAC_CreateTaskRebindContainment:
    """AC1 + AC2: validate_path_containment must be called after tasks_dir/archive_dir
    rebind in create_task. Tests use monkeypatched load_config to simulate a
    symlink-escaping reloaded config returned after write_task completes (AC2).
    """

    # --- error paths: tasks_dir escape ---

    def test_symlink_escaping_tasks_dir_raises_permission_error(self, tmp_path: Path) -> None:
        """create_task raises PermissionError when post-write reload returns a
        tasks_dir that is a symlink resolving outside kanban_dir.

        Proves the rebind calls validate_path_containment(kanban_dir, tasks_dir).
        Currently FAILS (RED): no validate_path_containment call after rebind.
        """
        kanban_dir = _make_board(tmp_path)
        engine = _make_engine(kanban_dir)
        real_config = load_config(kanban_dir)

        outside = tmp_path / "outside"
        outside.mkdir()
        (kanban_dir / "escape_tasks").symlink_to(outside)

        poisoned = _poisoned_config(
            tasks_dir_name="escape_tasks",
            archive_dir_name="archive",
        )

        with (
            patch(
                "owlbear_kanban.engine.load_config",
                side_effect=_side_effect_first_real_then_poisoned(real_config, poisoned),
            ),
            pytest.raises(PermissionError),
        ):
            engine.create_task("Test Task")

    # --- error paths: archive_dir escape ---

    def test_symlink_escaping_archive_dir_raises_permission_error(self, tmp_path: Path) -> None:
        """create_task raises PermissionError when post-write reload returns an
        archive_dir that is a symlink resolving outside kanban_dir.

        Proves the rebind calls validate_path_containment(kanban_dir, archive_dir).
        Currently FAILS (RED): no validate_path_containment call after rebind.
        """
        kanban_dir = _make_board(tmp_path)
        engine = _make_engine(kanban_dir)
        real_config = load_config(kanban_dir)

        outside = tmp_path / "outside"
        outside.mkdir()
        (kanban_dir / "escape_archive").symlink_to(outside)

        poisoned = _poisoned_config(
            tasks_dir_name="tasks",
            archive_dir_name="escape_archive",
        )

        with (
            patch(
                "owlbear_kanban.engine.load_config",
                side_effect=_side_effect_first_real_then_poisoned(real_config, poisoned),
            ),
            pytest.raises(PermissionError),
        ):
            engine.create_task("Test Task")

    # --- edge: both dirs poisoned simultaneously ---

    def test_both_dirs_poisoned_raises_permission_error(self, tmp_path: Path) -> None:
        """create_task raises PermissionError when both tasks_dir and archive_dir
        point outside kanban_dir via symlink escape.

        The first validate_path_containment call (on tasks_dir) fires.
        """
        kanban_dir = _make_board(tmp_path)
        engine = _make_engine(kanban_dir)
        real_config = load_config(kanban_dir)

        outside = tmp_path / "outside"
        outside.mkdir()
        (kanban_dir / "escape_tasks").symlink_to(outside)
        (kanban_dir / "escape_archive").symlink_to(outside)

        poisoned = _poisoned_config(
            tasks_dir_name="escape_tasks",
            archive_dir_name="escape_archive",
        )

        with (
            patch(
                "owlbear_kanban.engine.load_config",
                side_effect=_side_effect_first_real_then_poisoned(real_config, poisoned),
            ),
            pytest.raises(PermissionError),
        ):
            engine.create_task("Test Task")

    # --- error: regression proof — poison only reaches post-write reload ---

    def test_permission_error_raised_after_both_load_config_calls(self, tmp_path: Path) -> None:
        """PermissionError originates from the post-write rebind, not the pre-write load.

        Asserts that both load_config calls inside create_task complete before the
        error is raised, proving the gap is specifically in the rebind path (AC2c:
        the old code did NOT validate there).
        """
        kanban_dir = _make_board(tmp_path)
        engine = _make_engine(kanban_dir)
        real_config = load_config(kanban_dir)

        outside = tmp_path / "outside"
        outside.mkdir()
        (kanban_dir / "escape_tasks").symlink_to(outside)

        poisoned = _poisoned_config(
            tasks_dir_name="escape_tasks",
            archive_dir_name="archive",
        )

        call_log: list[str] = []

        def tracking_side_effect(_kd: Path) -> object:
            call_log.append("load_config")
            if len(call_log) == 1:
                return real_config
            return poisoned

        with (
            patch(
                "owlbear_kanban.engine.load_config",
                side_effect=tracking_side_effect,
            ),
            pytest.raises(PermissionError),
        ):
            engine.create_task("Test Task")

        # Both calls happened: pre-write (call 1) and post-write (call 2)
        assert len(call_log) == 2

    # --- boundary: symlink targets kanban_dir parent ---

    def test_symlink_to_parent_of_kanban_dir_raises_permission_error(self, tmp_path: Path) -> None:
        """create_task raises PermissionError when tasks_dir symlink points to
        kanban_dir's own parent — the immediate-parent boundary case.

        tmp_path is kanban_dir's parent; kanban_dir = tmp_path / 'board'.
        """
        kanban_dir = _make_board(tmp_path)
        engine = _make_engine(kanban_dir)
        real_config = load_config(kanban_dir)

        # kanban_dir's parent is tmp_path — one level outside
        (kanban_dir / "escape_parent").symlink_to(tmp_path)

        poisoned = _poisoned_config(
            tasks_dir_name="escape_parent",
            archive_dir_name="archive",
        )

        with (
            patch(
                "owlbear_kanban.engine.load_config",
                side_effect=_side_effect_first_real_then_poisoned(real_config, poisoned),
            ),
            pytest.raises(PermissionError),
        ):
            engine.create_task("Test Task")
