"""RED phase tests — MCP KANBAN_DIR board binding validation (#1349).

Tests the new KANBAN_DIR env-var support and startup validation in app_lifespan.
All tests must FAIL against current code (which ignores KANBAN_DIR and does no
path-resolution or startup validation).

AC1 (td:2): KANBAN_DIR env var read with default fallback.
AC2 (td:2): Relative paths resolved to absolute; AppContext.kanban_dir always absolute.
AC3 (td:2): Three-layer startup validation (kanban_dir.is_dir, engine init, tasks_dir.is_dir).
AC4 (td:1): Failure message names resolved path and 'KANBAN_DIR' remediation var.
AC5 (td:1): engine.sweep() runs only after all validation passes.
AC6-AC8: td:0 - not tested here.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from owlbear_mcp_kanban.server import AppContext, app_lifespan

# ---------------------------------------------------------------------------
# Shared helpers
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
next_id: 1
archive_dir: archive
activity_log: false
agent_map:
  research: researcher
  backlog: architect
  todo: test-writer
  in-progress: builder
  review: reviewer
  docs: doc-writer
  done: auditor
agent_types: {}
agent_compatibility: {}
non_impl_tags: []
archival_reasons: [completed, deprecated, dropped, duplicate, wontfix]
status_predicates: {}
"""


def _make_board(base_dir: Path) -> Path:
    """Create a minimal valid kanban board under *base_dir* and return its path."""
    kanban_dir = base_dir / "board"
    kanban_dir.mkdir(parents=True, exist_ok=True)
    (kanban_dir / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
    (kanban_dir / "tasks").mkdir(exist_ok=True)
    (kanban_dir / "archive").mkdir(exist_ok=True)
    return kanban_dir


def _server_mock() -> MagicMock:
    """Minimal FastMCP mock — app_lifespan only queries remove_tool via it."""
    server = MagicMock()
    server.remove_tool.side_effect = Exception("no tool")
    return server


def _mocked_engine(*, tasks_dir_exists: bool = True) -> MagicMock:
    """Return a KanbanEngine mock whose tasks_dir.is_dir() returns *tasks_dir_exists*."""
    engine = MagicMock()
    engine.tasks_dir = MagicMock(spec=Path)
    engine.tasks_dir.is_dir.return_value = tasks_dir_exists
    return engine


# ---------------------------------------------------------------------------
# AC1 + AC2 — KANBAN_DIR reading and absolute-path resolution
# ---------------------------------------------------------------------------


class TestFromAC_KanbanDirBinding:
    """AC1 + AC2: env-var reading, default fallback, path resolution to absolute."""

    @pytest.mark.asyncio
    async def test_kanban_dir_env_overrides_default(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC1: When KANBAN_DIR is set (non-empty) the lifespan uses that board."""
        board = _make_board(tmp_path)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("KANBAN_DIR", str(board))

        with patch("owlbear_mcp_kanban.server.KanbanEngine") as mock_cls:
            mock_cls.return_value = _mocked_engine()
            async with app_lifespan(_server_mock()) as ctx:
                # kanban_dir must equal the path from KANBAN_DIR, not the default
                assert ctx.kanban_dir.resolve() == board.resolve(), (
                    f"Expected kanban_dir={board.resolve()!r}, got {ctx.kanban_dir!r}"
                )

    @pytest.mark.asyncio
    async def test_default_binding_uses_cwd_when_no_env(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC1: Without KANBAN_DIR, default is cwd/.owlbear/kanban, stored as absolute path."""
        default_board = tmp_path / ".owlbear" / "kanban"
        default_board.mkdir(parents=True)
        (default_board / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
        (default_board / "tasks").mkdir()
        (default_board / "archive").mkdir()
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("KANBAN_DIR", raising=False)

        async with app_lifespan(_server_mock()) as ctx:
            expected = default_board.resolve()
            assert ctx.kanban_dir == expected, (
                f"Default kanban_dir should be absolute {expected!r}, got {ctx.kanban_dir!r}"
            )

    @pytest.mark.asyncio
    async def test_empty_kanban_dir_falls_back_to_default(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC1: KANBAN_DIR='' (empty string) falls back to default cwd/.owlbear/kanban."""
        default_board = tmp_path / ".owlbear" / "kanban"
        default_board.mkdir(parents=True)
        (default_board / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
        (default_board / "tasks").mkdir()
        (default_board / "archive").mkdir()
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("KANBAN_DIR", "")

        async with app_lifespan(_server_mock()) as ctx:
            expected = default_board.resolve()
            assert ctx.kanban_dir == expected, (
                f"Empty KANBAN_DIR must fall back to default {expected!r}, got {ctx.kanban_dir!r}"
            )

    @pytest.mark.asyncio
    async def test_relative_kanban_dir_resolved_to_absolute(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC2: Relative KANBAN_DIR is resolved to absolute using process cwd."""
        board = _make_board(tmp_path)
        relative = board.relative_to(tmp_path)  # e.g. "board"
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("KANBAN_DIR", str(relative))

        with patch("owlbear_mcp_kanban.server.KanbanEngine") as mock_cls:
            mock_cls.return_value = _mocked_engine()
            async with app_lifespan(_server_mock()) as ctx:
                assert ctx.kanban_dir.is_absolute(), (
                    f"Relative KANBAN_DIR must produce absolute kanban_dir, got {ctx.kanban_dir!r}"
                )
                assert ctx.kanban_dir == board.resolve()

    @pytest.mark.asyncio
    async def test_app_context_kanban_dir_is_always_absolute(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC2: AppContext.kanban_dir must be absolute regardless of KANBAN_DIR form."""
        board = _make_board(tmp_path)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("KANBAN_DIR", str(board))

        with patch("owlbear_mcp_kanban.server.KanbanEngine") as mock_cls:
            mock_cls.return_value = _mocked_engine()
            async with app_lifespan(_server_mock()) as ctx:
                assert ctx.kanban_dir.is_absolute(), (
                    f"AppContext.kanban_dir must be absolute, got {ctx.kanban_dir!r}"
                )

    @pytest.mark.asyncio
    async def test_absolute_kanban_dir_stored_correctly(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC2: An absolute KANBAN_DIR is stored as-is (still absolute) in AppContext."""
        board = _make_board(tmp_path)
        absolute_path = board.resolve()
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("KANBAN_DIR", str(absolute_path))

        with patch("owlbear_mcp_kanban.server.KanbanEngine") as mock_cls:
            mock_cls.return_value = _mocked_engine()
            async with app_lifespan(_server_mock()) as ctx:
                assert ctx.kanban_dir == absolute_path, (
                    f"Absolute KANBAN_DIR {absolute_path!r} must be stored as-is, "
                    f"got {ctx.kanban_dir!r}"
                )


# ---------------------------------------------------------------------------
# AC3 + AC4 — Startup validation and actionable failure messages
# ---------------------------------------------------------------------------


class TestFromAC_StartupValidation:
    """AC3 + AC4: three-layer validation and actionable exception messages."""

    @pytest.mark.asyncio
    async def test_nonexistent_kanban_dir_raises_on_startup(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC3a: kanban_dir.is_dir() fails → startup raises before engine construction."""
        nonexistent = tmp_path / "does_not_exist"
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("KANBAN_DIR", str(nonexistent))

        with pytest.raises(Exception, match=str(nonexistent)):
            async with app_lifespan(_server_mock()) as _ctx:
                pass

    @pytest.mark.asyncio
    async def test_kanban_dir_without_config_raises_on_startup(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC3b: kanban_dir exists but config.yml absent → engine construction raises."""
        empty_dir = tmp_path / "empty_board"
        empty_dir.mkdir()
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("KANBAN_DIR", str(empty_dir))

        with pytest.raises(Exception, match=str(empty_dir)):
            async with app_lifespan(_server_mock()) as _ctx:
                pass

    @pytest.mark.asyncio
    async def test_missing_tasks_dir_raises_on_startup(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC3c: kanban_dir + config.yml present but tasks_dir absent → startup raises."""
        board = tmp_path / "board"
        board.mkdir()
        (board / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
        # tasks/ deliberately absent
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("KANBAN_DIR", str(board))

        with patch("owlbear_mcp_kanban.server.KanbanEngine") as mock_cls:
            mock_cls.return_value = _mocked_engine(tasks_dir_exists=False)
            with pytest.raises(Exception):  # noqa: B017
                async with app_lifespan(_server_mock()) as _ctx:
                    pass

    @pytest.mark.asyncio
    async def test_valid_board_yields_app_context(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC3 happy path: full valid board → AppContext yielded without exception."""
        board = _make_board(tmp_path)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("KANBAN_DIR", str(board))

        async with app_lifespan(_server_mock()) as ctx:
            assert isinstance(ctx, AppContext)
            assert ctx.engine is not None

    @pytest.mark.asyncio
    async def test_failure_message_names_resolved_kanban_dir_path(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC4: Exception from missing kanban_dir names the resolved path."""
        nonexistent = tmp_path / "missing_board"
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("KANBAN_DIR", str(nonexistent))

        with pytest.raises(Exception, match=str(nonexistent)):
            async with app_lifespan(_server_mock()) as _ctx:
                pass

    @pytest.mark.asyncio
    async def test_failure_message_includes_kanban_dir_env_var_name(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC4: Exception message includes 'KANBAN_DIR' as the remediation env var."""
        nonexistent = tmp_path / "missing_board"
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("KANBAN_DIR", str(nonexistent))

        with pytest.raises(Exception, match="KANBAN_DIR"):
            async with app_lifespan(_server_mock()) as _ctx:
                pass

    @pytest.mark.asyncio
    async def test_engine_init_failure_message_names_path_and_kanban_dir(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC4 (engine-init branch): exception names the resolved path AND 'KANBAN_DIR'."""
        empty_dir = tmp_path / "no_config_board"
        empty_dir.mkdir()
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("KANBAN_DIR", str(empty_dir))

        with pytest.raises(Exception) as exc_info:
            async with app_lifespan(_server_mock()) as _ctx:
                pass

        error_msg = str(exc_info.value)
        assert str(empty_dir.resolve()) in error_msg, (
            f"Engine-init failure must name the resolved board path "
            f"{str(empty_dir.resolve())!r} in: {error_msg!r}"
        )
        assert "KANBAN_DIR" in error_msg, (
            f"Engine-init failure must include 'KANBAN_DIR' remediation hint in: {error_msg!r}"
        )

    @pytest.mark.asyncio
    async def test_tasks_dir_failure_message_names_path_and_kanban_dir(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC4 (tasks-dir branch): exception names the resolved board path AND 'KANBAN_DIR'."""
        board = tmp_path / "board_no_tasks"
        board.mkdir()
        (board / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("KANBAN_DIR", str(board))

        with patch("owlbear_mcp_kanban.server.KanbanEngine") as mock_cls:
            mock_cls.return_value = _mocked_engine(tasks_dir_exists=False)
            with pytest.raises(Exception) as exc_info:
                async with app_lifespan(_server_mock()) as _ctx:
                    pass

        error_msg = str(exc_info.value)
        assert str(board.resolve()) in error_msg, (
            f"Tasks-dir failure must name the resolved board path "
            f"{str(board.resolve())!r} in: {error_msg!r}"
        )
        assert "KANBAN_DIR" in error_msg, (
            f"Tasks-dir failure must include 'KANBAN_DIR' remediation hint in: {error_msg!r}"
        )

    @pytest.mark.asyncio
    async def test_nonexistent_board_skips_engine_construction(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC3a ordering: is_dir() fails before KanbanEngine is ever constructed."""
        nonexistent = tmp_path / "ghost_board"
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("KANBAN_DIR", str(nonexistent))

        with patch("owlbear_mcp_kanban.server.KanbanEngine") as mock_cls, pytest.raises(
            Exception, match=str(nonexistent)
        ):
            async with app_lifespan(_server_mock()) as _ctx:
                pass

        mock_cls.assert_not_called()


# ---------------------------------------------------------------------------
# AC5 — sweep() ordering: only called after all validation passes
# ---------------------------------------------------------------------------


class TestFromAC_SweepOrdering:
    """AC5: engine.sweep() must run only after board selection and all validation."""

    @pytest.mark.asyncio
    async def test_sweep_not_called_when_kanban_dir_does_not_exist(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC5: If kanban_dir.is_dir() fails, sweep() must not be called."""
        nonexistent = tmp_path / "missing"
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("KANBAN_DIR", str(nonexistent))
        sweep_calls: list[None] = []

        with patch("owlbear_mcp_kanban.server.KanbanEngine") as mock_cls:
            engine_instance = _mocked_engine()
            engine_instance.sweep.side_effect = lambda: sweep_calls.append(None)
            mock_cls.return_value = engine_instance

            with pytest.raises(Exception):  # noqa: B017
                async with app_lifespan(_server_mock()) as _ctx:
                    pass

        assert sweep_calls == [], (
            "sweep() must not be called when kanban_dir validation fails; "
            f"got {len(sweep_calls)} call(s)"
        )

    @pytest.mark.asyncio
    async def test_sweep_not_called_when_tasks_dir_missing(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC5: If tasks_dir.is_dir() fails, sweep() must not be called."""
        board = tmp_path / "board"
        board.mkdir()
        (board / "config.yml").write_text(_CONFIG_YAML, encoding="utf-8")
        # tasks/ deliberately absent — engine mock simulates missing tasks_dir
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("KANBAN_DIR", str(board))
        sweep_calls: list[None] = []

        with patch("owlbear_mcp_kanban.server.KanbanEngine") as mock_cls:
            engine_instance = _mocked_engine(tasks_dir_exists=False)
            engine_instance.sweep.side_effect = lambda: sweep_calls.append(None)
            mock_cls.return_value = engine_instance

            with pytest.raises(Exception):  # noqa: B017
                async with app_lifespan(_server_mock()) as _ctx:
                    pass

        assert sweep_calls == [], (
            "sweep() must not be called when tasks_dir validation fails; "
            f"got {len(sweep_calls)} call(s)"
        )

    @pytest.mark.asyncio
    async def test_engine_constructed_with_kanban_dir_path_before_sweep(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """AC5: Engine is constructed with the resolved KANBAN_DIR path, then sweep() called."""
        board = _make_board(tmp_path)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("KANBAN_DIR", str(board))

        with patch("owlbear_mcp_kanban.server.KanbanEngine") as mock_cls:
            engine_instance = _mocked_engine()
            mock_cls.return_value = engine_instance

            async with app_lifespan(_server_mock()) as _ctx:
                pass

        # Engine must be constructed with the resolved KANBAN_DIR path — not the default
        mock_cls.assert_called_once_with(board.resolve())
        # sweep() must be called exactly once (after validation)
        engine_instance.sweep.assert_called_once()
