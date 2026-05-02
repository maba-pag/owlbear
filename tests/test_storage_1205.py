"""RED-phase tests for threading cached config through read_task hot path (#1205).

AC1 (td:1) → TestFromAC_ReadTaskCachedConfig.test_ac1_accepts_config_keyword_arg
AC1 (td:1) → TestFromAC_ReadTaskCachedConfig.test_ac1_config_provided_skips_load_config_call
AC1 (td:1) → TestFromAC_ReadTaskCachedConfig.test_ac1_config_param_is_keyword_only
AC2 (td:2) → TestFromAC_ReadTaskCachedConfig.test_ac2_happy_valid_task_no_config_yml_config_provided
AC2 (td:2) → TestFromAC_ReadTaskCachedConfig.test_ac2_edge_corrupt_task_no_config_yml_config_provided_raises
AC2 (td:2) → TestFromAC_ReadTaskCachedConfig.test_ac2_error_corrupt_task_config_yml_present_config_provided_raises
AC2 (td:2) → TestFromAC_ReadTaskCachedConfig.test_ac2_boundary_detection_runs_even_when_config_yml_absent
AC3 (td:1) → TestFromAC_ReadTaskCachedConfig.test_ac3_explicit_none_returns_task
AC3 (td:1) → TestFromAC_ReadTaskCachedConfig.test_ac3_explicit_none_calls_load_config
AC4 (td:1) → TestFromAC_ReadTaskCachedConfig.test_ac4_engine_all_call_sites_pass_config
"""

from __future__ import annotations

import ast
from pathlib import Path
from unittest.mock import patch

import pytest

from owlbear_kanban.corruption import ERR_CORRUPT_INVALID_STATUS, CorruptionError
from owlbear_kanban.models import BoardConfig
from owlbear_kanban.storage import load_config, read_task

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_STATUSES = ["research", "backlog", "todo", "in-progress", "review", "done"]
_PRIORITIES = ["someday", "nice-to-have", "important", "needed", "critical"]

_CONFIG_YAML = """\
schema: grouped
statuses:
  - research
  - backlog
  - todo
  - in-progress
  - review
  - done
priorities:
  - someday
  - nice-to-have
  - important
  - needed
  - critical
next_id: 2
paths:
    tasks_dir: tasks
    archive_dir: archive
pipeline:
    entry_status: research
    terminal_status: done
    wave_size: 4
    claim_timeout: 1h
agents:
    agent_map: {}
    agent_types: {}
    agent_compatibility: {}
policy:
    non_impl_tags: [research, docs]
    archival_reasons: [completed, deprecated, dropped, duplicate, wontfix]
    status_predicates: {}
"""

_VALID_TASK_YAML = """\
---
id: 1
title: Test Task
status: todo
priority: important
created: 2026-01-01 00:00:00+00:00
updated: 2026-01-01 00:00:00+00:00
tags: []
depends_on: []
blocked: false
---
"""

_CORRUPT_TASK_YAML = """\
---
id: 1
title: Corrupt Task
status: invalid-status
priority: important
created: 2026-01-01 00:00:00+00:00
updated: 2026-01-01 00:00:00+00:00
tags: []
depends_on: []
blocked: false
---
"""


def _make_config() -> BoardConfig:
    """Return an in-memory BoardConfig with standard statuses/priorities."""
    return BoardConfig(statuses=_STATUSES, priorities=_PRIORITIES, next_id=1)


def _make_board_with_task(tmp_path: Path) -> tuple[Path, Path]:
    """Create a board dir with config.yml and a valid task file.

    Returns (board_dir, task_path).
    """
    board_dir = tmp_path / "board"
    tasks_dir = board_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    (board_dir / "archive").mkdir()
    (board_dir / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
    task_path = tasks_dir / "1-test-task.md"
    task_path.write_text(_VALID_TASK_YAML, encoding="utf-8")
    return board_dir, task_path


def _make_task_no_config_yml(tmp_path: Path, *, corrupt: bool = False) -> Path:
    """Create a board dir WITHOUT config.yml, with a task file.

    Returns task_path. Used to test that config= param bypasses the
    config_path.exists() guard.
    """
    board_dir = tmp_path / "board_no_cfg"
    tasks_dir = board_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    (board_dir / "archive").mkdir()
    # Deliberately NO config.yml
    task_content = _CORRUPT_TASK_YAML if corrupt else _VALID_TASK_YAML
    task_path = tasks_dir / "1-test-task.md"
    task_path.write_text(task_content, encoding="utf-8")
    return task_path


# ---------------------------------------------------------------------------
# TestFromAC_ReadTaskCachedConfig
# ---------------------------------------------------------------------------


class TestFromAC_ReadTaskCachedConfig:
    """Tests for AC1-AC4: read_task optional cached-config parameter."""

    # ------------------------------------------------------------------
    # AC1 — read_task accepts keyword-only config=BoardConfig|None
    # ------------------------------------------------------------------

    def test_ac1_accepts_config_keyword_arg(self, tmp_path: Path) -> None:
        """AC1: read_task(path, config=...) must accept a BoardConfig without error."""
        _, task_path = _make_board_with_task(tmp_path)
        config = _make_config()
        # Will TypeError pre-impl: "got an unexpected keyword argument 'config'"
        task = read_task(task_path, config=config)
        assert task.id == 1

    def test_ac1_config_provided_skips_load_config_call(self, tmp_path: Path) -> None:
        """AC1: when config is provided, load_config must NOT be called."""
        _, task_path = _make_board_with_task(tmp_path)
        config = _make_config()
        with patch("owlbear_kanban.storage.load_config") as mock_load:
            # Will TypeError pre-impl before the assertion is reached
            read_task(task_path, config=config)
        mock_load.assert_not_called()

    def test_ac1_config_param_is_keyword_only(self, tmp_path: Path) -> None:
        """AC1: config= must be keyword-only — positional use raises TypeError."""
        _, task_path = _make_board_with_task(tmp_path)
        config = _make_config()
        # Post-impl: passing config positionally must raise TypeError.
        # Pre-impl: TypeError for unknown argument — still fails, different message.
        with pytest.raises(TypeError):
            read_task(task_path, config)  # type: ignore[call-arg]

        # After impl, calling with the keyword must NOT raise TypeError.
        # This assertion fails pre-impl because the line above raises TypeError
        # and does NOT advance past the raises block to reach this assertion.
        _ = read_task(task_path, config=config)  # Will TypeError pre-impl

    # ------------------------------------------------------------------
    # AC2 — when config provided, detection runs unconditionally
    # ------------------------------------------------------------------

    def test_ac2_happy_valid_task_no_config_yml_config_provided(
        self, tmp_path: Path
    ) -> None:
        """AC2: valid task + config provided + no config.yml → task returned cleanly."""
        task_path = _make_task_no_config_yml(tmp_path, corrupt=False)
        config = _make_config()
        # Without config= the function would skip detection (no config.yml).
        # With config= the function runs detection; valid task → returns successfully.
        task = read_task(task_path, config=config)  # TypeError pre-impl
        assert task.id == 1

    def test_ac2_edge_corrupt_task_no_config_yml_config_provided_raises(
        self, tmp_path: Path
    ) -> None:
        """AC2 edge: corrupt task + config provided + no config.yml → CorruptionError.

        The config.yml absence guard is skipped because config is pre-resolved.
        Detection runs unconditionally and must surface the corrupt status.
        """
        task_path = _make_task_no_config_yml(tmp_path, corrupt=True)
        config = _make_config()
        # Pre-impl: TypeError for unexpected config= kwarg
        # Post-impl: CorruptionError for invalid status
        with pytest.raises(CorruptionError) as exc_info:
            read_task(task_path, config=config)
        assert exc_info.value.code == ERR_CORRUPT_INVALID_STATUS

    def test_ac2_error_corrupt_task_config_yml_present_config_provided_raises(
        self, tmp_path: Path
    ) -> None:
        """AC2 error: corrupt task + config.yml present + config provided → CorruptionError."""
        board_dir, _ = _make_board_with_task(tmp_path)
        tasks_dir = board_dir / "tasks"
        corrupt_path = tasks_dir / "1-corrupt.md"
        corrupt_path.write_text(_CORRUPT_TASK_YAML, encoding="utf-8")
        config = _make_config()
        with pytest.raises(CorruptionError) as exc_info:
            read_task(corrupt_path, config=config)  # TypeError pre-impl
        assert exc_info.value.code == ERR_CORRUPT_INVALID_STATUS

    def test_ac2_boundary_detection_runs_even_when_config_yml_absent(
        self, tmp_path: Path
    ) -> None:
        """AC2 boundary: config.yml absent + config provided → CorruptionError, not silent skip.

        Without the guard bypass, missing config.yml would silently skip detection
        and return the (corrupt) task. With config provided, the guard is bypassed
        and detection runs unconditionally, raising CorruptionError.
        Pre-impl: TypeError (unexpected kwarg) — test fails.
        Post-impl: CorruptionError (invalid status surfaced without config.yml).
        """
        task_path = _make_task_no_config_yml(tmp_path, corrupt=True)
        config = _make_config()
        with pytest.raises(CorruptionError) as exc_info:
            read_task(task_path, config=config)
        assert exc_info.value.code == ERR_CORRUPT_INVALID_STATUS

    # ------------------------------------------------------------------
    # AC3 — config=None preserves existing behavior: guard + load_config
    # ------------------------------------------------------------------

    def test_ac3_explicit_none_returns_task(self, tmp_path: Path) -> None:
        """AC3: read_task(path, config=None) must return task identical to read_task(path)."""
        _, task_path = _make_board_with_task(tmp_path)
        # Pre-impl: TypeError for unknown kwarg config=None
        task = read_task(task_path, config=None)
        assert task.id == 1

    def test_ac3_explicit_none_calls_load_config(self, tmp_path: Path) -> None:
        """AC3: when config=None, load_config is still called from disk."""
        _, task_path = _make_board_with_task(tmp_path)
        with patch("owlbear_kanban.storage.load_config", wraps=load_config) as mock_load:
            # Pre-impl: TypeError before mock can capture the call
            read_task(task_path, config=None)
        mock_load.assert_called_once()

    # ------------------------------------------------------------------
    # AC4 — all engine.py call sites pass config=self._config
    # ------------------------------------------------------------------

    def test_ac4_engine_all_call_sites_pass_config(self) -> None:
        """AC4: every read_task() call in engine.py must include config= keyword arg."""
        engine_py = (
            Path(__file__).parent.parent
            / "serve/kanban/src/owlbear_kanban/engine.py"
        )
        source = engine_py.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(engine_py))

        violations: list[int] = []
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "read_task"
            ):
                kwarg_names = [kw.arg for kw in node.keywords]
                if "config" not in kwarg_names:
                    violations.append(node.lineno)

        assert not violations, (
            f"read_task() calls in engine.py missing config= keyword argument "
            f"at lines: {violations}. All engine call sites must pass "
            f"config=self._config per AC4."
        )
