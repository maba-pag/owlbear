"""Tests for #1174 — delete config_loader.save_config and _merge_into dead code.

AC1: save_config and _merge_into are deleted from owlbear_kanban.config_loader
AC2: load_config still works (regression guard)
AC3: no new test failures introduced by the deletion — task-scoped suite green and no
     regressions in serve/kanban/ test surface (td:0; no task-local test mapping required)
AC4: grep confirms no remaining references to deleted functions in source
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

import owlbear_kanban.config_loader as _mod
from owlbear_kanban.config_loader import load_config
from owlbear_kanban.models import BoardConfig

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
claim_timeout: 1h
next_id: 1001
agent_map:
  research: []
  backlog: []
  todo: []
  in-progress: []
  review: []
  docs: []
  done: []
"""


def _make_board(tmp_path: Path) -> Path:
    kanban_dir = tmp_path / "board"
    kanban_dir.mkdir()
    (kanban_dir / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
    (kanban_dir / "tasks").mkdir()
    return kanban_dir


class TestFromAC_ConfigLoaderCleanup:
    """AC1 + AC4 — save_config and _merge_into deleted; no remaining references."""

    # ---- AC1: save_config deleted -------------------------------------------

    def test_save_config_not_in_module_attrs(self) -> None:
        """save_config must not exist as an attribute of config_loader."""
        assert not hasattr(_mod, "save_config")

    # ---- AC1: _merge_into deleted -------------------------------------------

    def test_merge_into_not_in_module_attrs(self) -> None:
        """_merge_into must not exist as an attribute of config_loader."""
        assert not hasattr(_mod, "_merge_into")

    # ---- AC4: no references remain in source --------------------------------

    def test_source_has_no_save_config_reference(self) -> None:
        """config_loader.py source must contain no 'save_config' reference at all.

        Covers function definition, docstring mention, and any call sites.
        """
        source = Path(inspect.getfile(_mod)).read_text(encoding="utf-8")
        assert "save_config" not in source

    def test_source_has_no_merge_into_reference(self) -> None:
        """config_loader.py source must contain no '_merge_into' reference at all.

        Covers function definition and any call sites.
        """
        source = Path(inspect.getfile(_mod)).read_text(encoding="utf-8")
        assert "_merge_into" not in source


class TestFromAC_LoadConfigRegression:
    """AC2 — load_config still works after deletion (regression guard).

    These tests verify no regressions are introduced during the cleanup.
    They pass in RED phase because load_config already works.
    """

    def test_load_config_returns_board_config(self, tmp_path: Path) -> None:
        """load_config must return a BoardConfig for a valid config.yml."""
        kanban_dir = _make_board(tmp_path)
        result = load_config(kanban_dir)
        assert isinstance(result, BoardConfig)

    def test_load_config_statuses_parsed(self, tmp_path: Path) -> None:
        """load_config must correctly parse statuses list from config.yml."""
        kanban_dir = _make_board(tmp_path)
        config = load_config(kanban_dir)
        assert "todo" in config.statuses
        assert "done" in config.statuses

    def test_load_config_raises_on_missing_file(self, tmp_path: Path) -> None:
        """load_config must raise FileNotFoundError when config.yml is absent."""
        with pytest.raises(FileNotFoundError):
            load_config(tmp_path / "nonexistent")
