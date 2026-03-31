"""Failing tests for task #89: mcp-kanban full tool set (TDD RED).

Covers the interface contract from #56 AC:
  - Lifespan: AppContext initialization, binary resolution, env var override
  - _run_kanban: argv construction, return tuple shape
  - Tools (7 success paths): each tool passes correct args to _run_kanban
  - Tools (error path): all 7 tools return "error: {stderr}" on non-zero rc

All tests FAIL in RED phase — ImportError expected until builder implements #56.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Import target — will raise ImportError until builder implements #56 (RED)
# ---------------------------------------------------------------------------
from owlbear_mcp_kanban.server import (  # type: ignore[import]
    AppContext,
    _run_kanban,
    app_lifespan,
    create_task,
    edit_task,
    list_tasks,
    move_task,
    pick_task,
    show_task,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_app_context(
    kanban_bin: Path = Path("/fake/kanban-md"),
    kanban_dir: Path = Path("/fake/kanban"),
) -> AppContext:
    """Return a minimal AppContext for tool tests."""
    return AppContext(kanban_bin=kanban_bin, kanban_dir=kanban_dir)


def _make_mcp_ctx(app_ctx: AppContext | None = None) -> MagicMock:
    """Return a MagicMock mimicking an MCP Context with lifespan_context."""
    ctx = MagicMock()
    ctx.request_context.lifespan_context = app_ctx or _make_app_context()
    return ctx


def _mock_proc(stdout: str = "ok", stderr: str = "", returncode: int = 0) -> AsyncMock:
    """Return a mock asyncio Process with configurable output."""
    proc = AsyncMock()
    proc.communicate.return_value = (stdout.encode(), stderr.encode())
    proc.returncode = returncode
    return proc


# ---------------------------------------------------------------------------
# TestFromAC_Lifespan
# ---------------------------------------------------------------------------


class TestFromAC_Lifespan:
    """Contract tests for app_lifespan derived from #56 AC."""

    # AC: app_lifespan yields AppContext with kanban_bin (Path) and kanban_dir (Path)
    @pytest.mark.asyncio
    async def test_lifespan_yields_app_context_with_path_fields(self) -> None:
        """app_lifespan yields AppContext; kanban_bin and kanban_dir are Path instances."""
        mock_server = MagicMock()
        with patch("owlbear_mcp_kanban.server.Path.exists", return_value=True):
            async with app_lifespan(mock_server) as ctx:
                assert isinstance(ctx, AppContext)
                assert isinstance(ctx.kanban_bin, Path)
                assert isinstance(ctx.kanban_dir, Path)

    # AC: app_lifespan raises FileNotFoundError when binary path does not exist
    @pytest.mark.asyncio
    async def test_lifespan_raises_file_not_found_when_binary_missing(self) -> None:
        """app_lifespan raises FileNotFoundError with a descriptive message when binary is absent."""
        mock_server = MagicMock()
        with patch("owlbear_mcp_kanban.server.Path.exists", return_value=False), pytest.raises(FileNotFoundError, match=r".+"):
            async with app_lifespan(mock_server) as _ctx:
                pass  # pragma: no cover

    # AC: app_lifespan respects KANBAN_BIN env var override for binary resolution
    @pytest.mark.asyncio
    async def test_lifespan_respects_kanban_bin_env_var(self) -> None:
        """When KANBAN_BIN is set, app_lifespan uses that path as kanban_bin."""
        mock_server = MagicMock()
        custom_bin = "/custom/path/kanban-md"
        with patch.dict(os.environ, {"KANBAN_BIN": custom_bin}), patch("owlbear_mcp_kanban.server.Path.exists", return_value=True):
            async with app_lifespan(mock_server) as ctx:
                assert str(ctx.kanban_bin) == custom_bin


# ---------------------------------------------------------------------------
# TestFromAC_RunKanban
# ---------------------------------------------------------------------------


class TestFromAC_RunKanban:
    """Contract tests for the _run_kanban helper derived from #56 AC."""

    # AC: Constructs correct argv: binary path + command args + --no-color --dir {kanban_dir}
    @pytest.mark.asyncio
    async def test_constructs_correct_argv(self) -> None:
        """_run_kanban calls subprocess with binary + user args + --no-color --dir kanban_dir."""
        ctx = _make_app_context(
            kanban_bin=Path("/bin/kanban-md"),
            kanban_dir=Path("/kanban"),
        )
        proc = _mock_proc()
        with patch("asyncio.create_subprocess_exec", return_value=proc) as mock_exec:
            await _run_kanban(ctx, "list", "--compact")

        argv: tuple[Any, ...] = mock_exec.call_args[0]  # positional args to create_subprocess_exec
        assert argv[0] == str(ctx.kanban_bin)
        assert "list" in argv
        assert "--compact" in argv
        assert "--no-color" in argv
        assert "--dir" in argv
        dir_idx = list(argv).index("--dir")
        assert argv[dir_idx + 1] == str(ctx.kanban_dir)

    # AC: Returns (stdout: str, stderr: str, returncode: int) tuple from subprocess result
    @pytest.mark.asyncio
    async def test_returns_stdout_stderr_returncode_tuple(self) -> None:
        """_run_kanban returns (stdout, stderr, returncode) as a 3-tuple of (str, str, int)."""
        ctx = _make_app_context()
        proc = _mock_proc(stdout="output text", stderr="err text", returncode=0)
        with patch("asyncio.create_subprocess_exec", return_value=proc):
            result = await _run_kanban(ctx, "show", "42")

        assert isinstance(result, tuple)
        assert len(result) == 3
        stdout_out, stderr_out, rc = result
        assert isinstance(stdout_out, str)
        assert isinstance(stderr_out, str)
        assert isinstance(rc, int)
        assert "output text" in stdout_out
        assert rc == 0


# ---------------------------------------------------------------------------
# TestFromAC_Tools
# ---------------------------------------------------------------------------

_FAKE_STDOUT = "board output"
_FAKE_STDERR = "something failed"


class TestFromAC_Tools:
    """Contract tests for the 7 MCP tools derived from #56 AC (success and error paths)."""

    # ------------------------------------------------------------------ helpers
    def _patch_run(self, stdout: str = _FAKE_STDOUT, stderr: str = "", rc: int = 0) -> Any:
        return patch(
            "owlbear_mcp_kanban.server._run_kanban",
            new=AsyncMock(return_value=(stdout, stderr, rc)),
        )

    # ------------------------------------------------------------------ list_tasks
    @pytest.mark.asyncio
    async def test_list_tasks_success_passes_args(self) -> None:
        """list_tasks passes --compact + all filter args to _run_kanban when rc=0."""
        mcp_ctx = _make_mcp_ctx()
        with self._patch_run() as mock_run:
            result = await list_tasks(
                mcp_ctx,
                status="todo",
                tag="phase-3",
                priority="important",
                block_filter="blocked",
                search="keyword",
                sort="priority",
                unclaimed=True,
            )

        assert result == _FAKE_STDOUT
        args_used: tuple[Any, ...] = mock_run.call_args[0]
        assert "list" in args_used
        assert "--compact" in args_used
        assert "--status" in args_used
        assert "todo" in args_used
        assert "--tag" in args_used
        assert "phase-3" in args_used
        assert "--priority" in args_used
        assert "important" in args_used

    # ------------------------------------------------------------------ show_task
    @pytest.mark.asyncio
    async def test_show_task_success_passes_args(self) -> None:
        """show_task passes task_id and --json flag to _run_kanban when rc=0."""
        mcp_ctx = _make_mcp_ctx()
        with self._patch_run() as mock_run:
            result = await show_task(mcp_ctx, task_id="42")

        assert result == _FAKE_STDOUT
        args_used: tuple[Any, ...] = mock_run.call_args[0]
        assert "show" in args_used
        assert "42" in args_used
        assert "--json" in args_used

    # ------------------------------------------------------------------ create_task
    @pytest.mark.asyncio
    async def test_create_task_success_passes_args(self) -> None:
        """create_task passes title + all optional flags to _run_kanban when rc=0."""
        mcp_ctx = _make_mcp_ctx()
        with self._patch_run() as mock_run:
            result = await create_task(
                mcp_ctx,
                title="My new task",
                priority="needed",
                tags="phase-3,mcp",
                body="## AC\n- do stuff",
                depends_on="7",
                claim="builder",
            )

        assert result == _FAKE_STDOUT
        args_used: tuple[Any, ...] = mock_run.call_args[0]
        assert "create" in args_used
        assert "My new task" in args_used
        assert "--priority" in args_used
        assert "needed" in args_used
        assert "--tags" in args_used
        assert "--body" in args_used
        assert "--depends-on" in args_used
        assert "--claim" in args_used

    # ------------------------------------------------------------------ move_task
    @pytest.mark.asyncio
    async def test_move_task_success_passes_args(self) -> None:
        """move_task passes task_id and status to _run_kanban as positional args when rc=0."""
        mcp_ctx = _make_mcp_ctx()
        with self._patch_run() as mock_run:
            result = await move_task(mcp_ctx, task_id="42", status="in-progress")

        assert result == _FAKE_STDOUT
        args_used: tuple[Any, ...] = mock_run.call_args[0]
        assert "move" in args_used
        assert "42" in args_used
        assert "in-progress" in args_used
        assert "--json" in args_used

    # ------------------------------------------------------------------ edit_task
    @pytest.mark.asyncio
    async def test_edit_task_success_passes_args(self) -> None:
        """edit_task maps all flag kwargs to the correct CLI flags for _run_kanban when rc=0."""
        mcp_ctx = _make_mcp_ctx()
        with self._patch_run() as mock_run:
            result = await edit_task(
                mcp_ctx,
                task_id="42",
                body="new body",
                block="waiting on user",
                unblock=False,
                tags="phase-3",
                priority="critical",
                append_body="## Notes\n- added",
                claim="builder",
                release=False,
                status="review",
                timestamp=True,
            )

        assert result == _FAKE_STDOUT
        args_used: tuple[Any, ...] = mock_run.call_args[0]
        assert "edit" in args_used
        assert "42" in args_used
        assert "--body" in args_used
        assert "--block" in args_used
        assert "--tags" in args_used
        assert "--priority" in args_used
        assert "--claim" in args_used
        assert "--status" in args_used
        # append_body maps to -a or --append-body
        assert any(arg in args_used for arg in ("-a", "--append-body"))
        # timestamp=True maps to --timestamp
        assert "--timestamp" in args_used

    # ------------------------------------------------------------------ edit_task boolean flags (retry: LAX coverage)
    @pytest.mark.asyncio
    async def test_edit_task_passes_unblock_flag_when_true(self) -> None:
        """edit_task passes --unblock to _run_kanban when unblock=True (not False)."""
        mcp_ctx = _make_mcp_ctx()
        with self._patch_run() as mock_run:
            await edit_task(mcp_ctx, task_id="42", unblock=True)

        args_used: tuple[Any, ...] = mock_run.call_args[0]
        assert "--unblock" in args_used

    @pytest.mark.asyncio
    async def test_edit_task_omits_unblock_flag_when_false(self) -> None:
        """edit_task does NOT include --unblock when unblock=False."""
        mcp_ctx = _make_mcp_ctx()
        with self._patch_run() as mock_run:
            await edit_task(mcp_ctx, task_id="42", unblock=False)

        args_used: tuple[Any, ...] = mock_run.call_args[0]
        assert "--unblock" not in args_used

    @pytest.mark.asyncio
    async def test_edit_task_passes_release_flag_when_true(self) -> None:
        """edit_task passes --release to _run_kanban when release=True (not False)."""
        mcp_ctx = _make_mcp_ctx()
        with self._patch_run() as mock_run:
            await edit_task(mcp_ctx, task_id="42", release=True)

        args_used: tuple[Any, ...] = mock_run.call_args[0]
        assert "--release" in args_used

    @pytest.mark.asyncio
    async def test_edit_task_omits_release_flag_when_false(self) -> None:
        """edit_task does NOT include --release when release=False."""
        mcp_ctx = _make_mcp_ctx()
        with self._patch_run() as mock_run:
            await edit_task(mcp_ctx, task_id="42", release=False)

        args_used: tuple[Any, ...] = mock_run.call_args[0]
        assert "--release" not in args_used

    # ------------------------------------------------------------------ list_tasks search/sort/unclaimed (retry: LAX coverage from cycle 1+2)
    @pytest.mark.asyncio
    async def test_list_tasks_passes_search_flag(self) -> None:
        """list_tasks passes --search and value to _run_kanban when search is non-empty."""
        mcp_ctx = _make_mcp_ctx()
        with self._patch_run() as mock_run:
            await list_tasks(mcp_ctx, search="keyword")

        args_used: tuple[Any, ...] = mock_run.call_args[0]
        assert "--search" in args_used
        assert "keyword" in args_used

    @pytest.mark.asyncio
    async def test_list_tasks_omits_search_flag_when_empty(self) -> None:
        """list_tasks does NOT pass --search when search is empty string (default)."""
        mcp_ctx = _make_mcp_ctx()
        with self._patch_run() as mock_run:
            await list_tasks(mcp_ctx, search="")

        args_used: tuple[Any, ...] = mock_run.call_args[0]
        assert "--search" not in args_used

    @pytest.mark.asyncio
    async def test_list_tasks_passes_sort_flag(self) -> None:
        """list_tasks passes --sort and value to _run_kanban when sort is non-empty."""
        mcp_ctx = _make_mcp_ctx()
        with self._patch_run() as mock_run:
            await list_tasks(mcp_ctx, sort="priority")

        args_used: tuple[Any, ...] = mock_run.call_args[0]
        assert "--sort" in args_used
        assert "priority" in args_used

    @pytest.mark.asyncio
    async def test_list_tasks_omits_sort_flag_when_empty(self) -> None:
        """list_tasks does NOT pass --sort when sort is empty string (default)."""
        mcp_ctx = _make_mcp_ctx()
        with self._patch_run() as mock_run:
            await list_tasks(mcp_ctx, sort="")

        args_used: tuple[Any, ...] = mock_run.call_args[0]
        assert "--sort" not in args_used

    @pytest.mark.asyncio
    async def test_list_tasks_passes_unclaimed_flag_when_true(self) -> None:
        """list_tasks passes --unclaimed to _run_kanban when unclaimed=True."""
        mcp_ctx = _make_mcp_ctx()
        with self._patch_run() as mock_run:
            await list_tasks(mcp_ctx, unclaimed=True)

        args_used: tuple[Any, ...] = mock_run.call_args[0]
        assert "--unclaimed" in args_used

    @pytest.mark.asyncio
    async def test_list_tasks_omits_unclaimed_flag_when_false(self) -> None:
        """list_tasks does NOT pass --unclaimed when unclaimed=False (default)."""
        mcp_ctx = _make_mcp_ctx()
        with self._patch_run() as mock_run:
            await list_tasks(mcp_ctx, unclaimed=False)

        args_used: tuple[Any, ...] = mock_run.call_args[0]
        assert "--unclaimed" not in args_used

    # ------------------------------------------------------------------ list_tasks block_filter branches (retry: LAX coverage)
    @pytest.mark.asyncio
    async def test_list_tasks_not_blocked_filter(self) -> None:
        """list_tasks passes --not-blocked to _run_kanban when block_filter='not-blocked'."""
        mcp_ctx = _make_mcp_ctx()
        with self._patch_run() as mock_run:
            result = await list_tasks(mcp_ctx, block_filter="not-blocked")

        assert result == _FAKE_STDOUT
        args_used: tuple[Any, ...] = mock_run.call_args[0]
        assert "--not-blocked" in args_used
        assert "--blocked" not in args_used

    @pytest.mark.asyncio
    async def test_list_tasks_blocked_filter_does_not_pass_not_blocked(self) -> None:
        """list_tasks passes --blocked (not --not-blocked) when block_filter='blocked'."""
        mcp_ctx = _make_mcp_ctx()
        with self._patch_run() as mock_run:
            await list_tasks(mcp_ctx, block_filter="blocked")

        args_used: tuple[Any, ...] = mock_run.call_args[0]
        assert "--blocked" in args_used
        assert "--not-blocked" not in args_used

    # ------------------------------------------------------------------ pick_task
    @pytest.mark.asyncio
    async def test_pick_task_success_passes_args(self) -> None:
        """pick_task passes optional filter args to _run_kanban when rc=0."""
        mcp_ctx = _make_mcp_ctx()
        with self._patch_run() as mock_run:
            result = await pick_task(
                mcp_ctx,
                status="todo",
                claim="builder",
                move="in-progress",
                tags="phase-3",
            )

        assert result == _FAKE_STDOUT
        args_used: tuple[Any, ...] = mock_run.call_args[0]
        assert "pick" in args_used
        assert "--status" in args_used
        assert "todo" in args_used
        assert "--claim" in args_used
        assert "--move" in args_used
        assert "--tags" in args_used
        assert "--json" in args_used

    # ------------------------------------------------------------------ error path (parametrized)
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("tool_fn", "kwargs"),
        [
            (list_tasks, {}),
            (show_task, {"task_id": "1"}),
            (create_task, {"title": "t"}),
            (move_task, {"task_id": "1", "status": "done"}),
            (edit_task, {"task_id": "1"}),
            (pick_task, {}),
        ],
        ids=["list_tasks", "show_task", "create_task", "move_task", "edit_task", "pick_task"],
    )
    async def test_all_tools_return_error_string_on_non_zero_rc(
        self, tool_fn: Any, kwargs: dict[str, Any]
    ) -> None:
        """Every tool returns 'error: {stderr.strip()}' string when _run_kanban rc != 0."""
        mcp_ctx = _make_mcp_ctx()
        with patch(
            "owlbear_mcp_kanban.server._run_kanban",
            new=AsyncMock(return_value=("", _FAKE_STDERR, 1)),
        ):
            result = await tool_fn(mcp_ctx, **kwargs)

        assert isinstance(result, str)
        assert result.startswith("error:")
        assert _FAKE_STDERR.strip() in result
