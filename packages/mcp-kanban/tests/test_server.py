"""Failing tests for task #89: mcp-kanban full tool set (TDD RED).

Covers the interface contract from #56 AC:
  - Lifespan: AppContext initialization, binary resolution, env var override
  - _run_kanban: argv construction, return tuple shape
  - Tools (7 success paths): each tool passes correct args to _run_kanban
  - Tools (error path): all 7 tools return "error: {stderr}" on non-zero rc

All tests FAIL in RED phase — ImportError expected until builder implements #56.
"""

from __future__ import annotations

import json
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
    end_work,
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


_DEFAULT_STATUSES: list[str] = [
    "ideation", "backlog", "todo", "in-progress", "review", "docs", "done"
]


def _make_app_context_with_statuses(
    statuses: list[str] | None = None,
    kanban_bin: Path = Path("/fake/kanban-md"),
    kanban_dir: Path = Path("/fake/kanban"),
) -> AppContext:
    """Return an AppContext with statuses for end_work tests.

    RED phase: fails until builder adds statuses field to AppContext.
    """
    return AppContext(
        kanban_bin=kanban_bin,
        kanban_dir=kanban_dir,
        statuses=statuses if statuses is not None else list(_DEFAULT_STATUSES),
    )


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
        """list_tasks passes --json + all filter args to _run_kanban when rc=0."""
        mcp_ctx = _make_mcp_ctx()
        with self._patch_run() as mock_run:
            result = await list_tasks(
                mcp_ctx,
                status="todo",
                tag="phase-3",
                priority="important",
                blocked=True,
                search="keyword",
                sort="priority",
                unclaimed=True,
            )

        assert result == _FAKE_STDOUT
        args_used: tuple[Any, ...] = mock_run.call_args[0]
        assert "list" in args_used
        assert "--json" in args_used
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
        """list_tasks passes --not-blocked to _run_kanban when blocked=False."""
        mcp_ctx = _make_mcp_ctx()
        with self._patch_run() as mock_run:
            result = await list_tasks(mcp_ctx, blocked=False)

        assert result == _FAKE_STDOUT
        args_used: tuple[Any, ...] = mock_run.call_args[0]
        assert "--not-blocked" in args_used
        assert "--blocked" not in args_used

    @pytest.mark.asyncio
    async def test_list_tasks_blocked_filter_does_not_pass_not_blocked(self) -> None:
        """list_tasks passes --blocked (not --not-blocked) when blocked=True."""
        mcp_ctx = _make_mcp_ctx()
        with self._patch_run() as mock_run:
            await list_tasks(mcp_ctx, blocked=True)

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


# ---------------------------------------------------------------------------
# TestFromAC_AppContextStatuses
# ---------------------------------------------------------------------------


class TestFromAC_AppContextStatuses:
    """Contract tests for AppContext.statuses extension and lifespan config population (#497 AC)."""

    # AC: Extend AppContext with statuses: list[str] field
    def test_app_context_has_statuses_field(self) -> None:
        """AppContext accepts a statuses kwarg and exposes it as a list[str] field."""
        ctx = _make_app_context_with_statuses(["todo", "in-progress", "done"])
        assert hasattr(ctx, "statuses")
        assert isinstance(ctx.statuses, list)
        assert all(isinstance(s, str) for s in ctx.statuses)

    # AC: populated from config subprocess (JSON mode) during app_lifespan
    @pytest.mark.asyncio
    async def test_lifespan_populates_statuses_from_config_json(self) -> None:
        """app_lifespan runs config --json and stores returned statuses in AppContext.statuses."""
        expected_statuses = ["todo", "in-progress", "review", "done"]
        config_output = json.dumps({"statuses": expected_statuses})
        mock_server = MagicMock()

        async def _fake_exec(*args: Any, **_kwargs: Any) -> Any:
            if "config" in args:
                return _mock_proc(stdout=config_output)
            return _mock_proc()

        with (
            patch("owlbear_mcp_kanban.server.Path.exists", return_value=True),
            patch("asyncio.create_subprocess_exec", side_effect=_fake_exec),
        ):
            async with app_lifespan(mock_server) as ctx:
                assert hasattr(ctx, "statuses")
                assert ctx.statuses == expected_statuses

    # AC: cached once at startup
    @pytest.mark.asyncio
    async def test_lifespan_calls_config_exactly_once(self) -> None:
        """app_lifespan calls the config subprocess exactly once (cached; not repeated per tool call)."""
        config_output = json.dumps({"statuses": ["todo", "in-progress", "done"]})
        mock_server = MagicMock()
        config_call_count = 0

        async def _fake_exec(*args: Any, **_kwargs: Any) -> Any:
            nonlocal config_call_count
            if "config" in args:
                config_call_count += 1
            return _mock_proc(stdout=config_output)

        with (
            patch("owlbear_mcp_kanban.server.Path.exists", return_value=True),
            patch("asyncio.create_subprocess_exec", side_effect=_fake_exec),
        ):
            async with app_lifespan(mock_server) as _ctx:
                pass

        assert config_call_count == 1


# ---------------------------------------------------------------------------
# TestFromAC_EndWork
# ---------------------------------------------------------------------------


class TestFromAC_EndWork:
    """Contract tests for end_work compound tool derived from #497 AC."""

    # ------------------------------------------------------------------ helpers

    def _make_mcp_ctx_with_statuses(
        self, statuses: list[str] | None = None
    ) -> MagicMock:
        return _make_mcp_ctx(_make_app_context_with_statuses(statuses))

    def _show_json(
        self,
        status: str = "in-progress",
        claimed_by: str = "test-agent",
        task_id: int = 42,
    ) -> str:
        return json.dumps({"id": task_id, "status": status, "claimed_by": claimed_by})

    def _patch_run_seq(self, *responses: tuple[str, str, int]) -> Any:
        """Patch _run_kanban with sequential (stdout, stderr, rc) responses."""
        if len(responses) == 1:
            return patch(
                "owlbear_mcp_kanban.server._run_kanban",
                new=AsyncMock(return_value=responses[0]),
            )
        return patch(
            "owlbear_mcp_kanban.server._run_kanban",
            new=AsyncMock(side_effect=list(responses)),
        )

    def _patch_run_always(self, stdout: str = '{"id": 42}', rc: int = 0) -> Any:
        """Patch _run_kanban to always return the same (stdout, '', rc) for any call count."""
        return patch(
            "owlbear_mcp_kanban.server._run_kanban",
            new=AsyncMock(return_value=(stdout, "", rc)),
        )

    def _edit_calls(self, mock_run: AsyncMock) -> list[Any]:
        return [c for c in mock_run.call_args_list if "edit" in c[0]]

    def _all_cmds(self, mock_run: AsyncMock) -> list[str]:
        return [c[0][1] for c in mock_run.call_args_list if len(c[0]) > 1]

    # ------------------------------------------------------------------ outcome=success (happy)

    # AC: verify edit called with -a NOTE -t --status NEXT_STATUS --release --json
    @pytest.mark.asyncio
    async def test_success_edit_includes_next_status(self) -> None:
        """outcome=success: edit call includes --status set to statuses[current_index + 1]."""
        statuses = ["todo", "in-progress", "review", "docs", "done"]
        mcp_ctx = self._make_mcp_ctx_with_statuses(statuses)
        show_resp = (self._show_json(status="in-progress", claimed_by="builder"), "", 0)
        edit_resp = ('{"id": 42, "status": "review"}', "", 0)

        with self._patch_run_seq(show_resp, edit_resp) as mock_run:
            await end_work(mcp_ctx, task_id="42", note="done!", outcome="success")

        edit_calls = self._edit_calls(mock_run)
        assert edit_calls, "edit was not called for success outcome"
        edit_args = list(edit_calls[-1][0])
        assert "--status" in edit_args
        assert edit_args[edit_args.index("--status") + 1] == "review"
        assert "--release" in edit_args
        assert "--json" in edit_args

    @pytest.mark.asyncio
    async def test_success_edit_includes_note_and_timestamp(self) -> None:
        """outcome=success: edit call includes -a NOTE and --timestamp (-t) flags."""
        statuses = ["todo", "in-progress", "review"]
        mcp_ctx = self._make_mcp_ctx_with_statuses(statuses)
        show_resp = (self._show_json(status="in-progress"), "", 0)
        edit_resp = ('{"id": 42}', "", 0)
        note_text = "implementation complete"

        with self._patch_run_seq(show_resp, edit_resp) as mock_run:
            await end_work(mcp_ctx, task_id="42", note=note_text, outcome="success")

        edit_calls = self._edit_calls(mock_run)
        assert edit_calls
        edit_args = list(edit_calls[-1][0])
        assert "-a" in edit_args
        assert any(note_text in arg for arg in edit_args)
        assert "--timestamp" in edit_args

    # AC: return JSON string from final CLI call
    @pytest.mark.asyncio
    async def test_success_returns_json_from_final_cli_call(self) -> None:
        """end_work returns the stdout of the final _run_kanban call (edit response)."""
        statuses = ["todo", "in-progress", "review"]
        mcp_ctx = self._make_mcp_ctx_with_statuses(statuses)
        show_resp = (self._show_json(status="in-progress"), "", 0)
        final_json = '{"id": 42, "status": "review", "title": "my task"}'
        edit_resp = (final_json, "", 0)

        with self._patch_run_seq(show_resp, edit_resp):
            result = await end_work(mcp_ctx, task_id="42", note="done", outcome="success")

        assert result == final_json

    # ------------------------------------------------------------------ outcome=success at done (edge)

    # AC: verify edit + archive sequence (two _run_kanban calls)
    @pytest.mark.asyncio
    async def test_success_at_done_calls_edit_then_archive(self) -> None:
        """outcome=success when task is at done status: _run_kanban is called with archive."""
        statuses = ["todo", "in-progress", "done"]
        mcp_ctx = self._make_mcp_ctx_with_statuses(statuses)
        show_resp = (self._show_json(status="done", claimed_by="builder"), "", 0)
        edit_resp = ('{"id": 42, "status": "done"}', "", 0)
        archive_resp = ('{"id": 42, "status": "archived"}', "", 0)

        with self._patch_run_seq(show_resp, edit_resp, archive_resp) as mock_run:
            await end_work(mcp_ctx, task_id="42", note="done", outcome="success")

        cmds = self._all_cmds(mock_run)
        assert "archive" in cmds, "archive was not called for done→success path"

    # AC: if archive fails after edit succeeds, return the error
    @pytest.mark.asyncio
    async def test_success_at_done_returns_error_if_archive_fails(self) -> None:
        """outcome=success at done: if archive subprocess fails, end_work returns error string."""
        statuses = ["todo", "done"]
        mcp_ctx = self._make_mcp_ctx_with_statuses(statuses)
        show_resp = (self._show_json(status="done"), "", 0)
        edit_resp = ('{"id": 42}', "", 0)
        archive_fail = ("", "archive failed: permission denied", 1)

        with self._patch_run_seq(show_resp, edit_resp, archive_fail):
            result = await end_work(mcp_ctx, task_id="42", note="done", outcome="success")

        assert isinstance(result, str)
        assert "error" in result.lower()

    # ------------------------------------------------------------------ next-status derivation (boundary)

    # AC: statuses[current_index + 1]
    @pytest.mark.asyncio
    async def test_next_status_derivation_uses_statuses_index(self) -> None:
        """Next status is statuses[index + 1]; index comes from current task status position."""
        # Use non-default ordering to verify derivation is not hardcoded
        custom_statuses = ["alpha", "beta", "gamma", "delta"]
        mcp_ctx = self._make_mcp_ctx_with_statuses(custom_statuses)
        show_resp = (self._show_json(status="beta"), "", 0)
        edit_resp = ('{"id": 42}', "", 0)

        with self._patch_run_seq(show_resp, edit_resp) as mock_run:
            await end_work(mcp_ctx, task_id="42", note="done", outcome="success")

        edit_calls = self._edit_calls(mock_run)
        assert edit_calls
        edit_args = list(edit_calls[-1][0])
        assert "--status" in edit_args
        assert edit_args[edit_args.index("--status") + 1] == "gamma"

    # ------------------------------------------------------------------ outcome=fail (happy)

    # AC: verify edit called with -a NOTE -t --release --json (no status change)
    @pytest.mark.asyncio
    async def test_fail_edit_has_no_status_flag(self) -> None:
        """outcome=fail: edit call does NOT include --status (task stays at current status)."""
        mcp_ctx = self._make_mcp_ctx_with_statuses()

        with self._patch_run_always() as mock_run:
            await end_work(
                mcp_ctx, task_id="42", note="couldn't finish", outcome="fail", claim="my-agent"
            )

        edit_calls = self._edit_calls(mock_run)
        assert edit_calls
        edit_args = edit_calls[-1][0]
        assert "--status" not in edit_args
        assert "--release" in edit_args
        assert "-a" in edit_args

    @pytest.mark.asyncio
    async def test_fail_edit_includes_timestamp_and_release(self) -> None:
        """outcome=fail: edit includes --timestamp and --release flags."""
        mcp_ctx = self._make_mcp_ctx_with_statuses()

        with self._patch_run_always() as mock_run:
            await end_work(
                mcp_ctx, task_id="42", note="context overflow", outcome="fail", claim="agent"
            )

        edit_calls = self._edit_calls(mock_run)
        assert edit_calls
        edit_args = edit_calls[-1][0]
        assert "--timestamp" in edit_args
        assert "--release" in edit_args

    # ------------------------------------------------------------------ outcome=block (happy)

    # AC: verify edit called with -a NOTE -t --block REASON --release --json
    @pytest.mark.asyncio
    async def test_block_edit_includes_block_reason_and_release(self) -> None:
        """outcome=block: edit call includes --block {block_reason} and --release."""
        mcp_ctx = self._make_mcp_ctx_with_statuses()
        reason = "waiting on user decision #DR-42"

        with self._patch_run_always() as mock_run:
            await end_work(
                mcp_ctx,
                task_id="42",
                note="blocked",
                outcome="block",
                block_reason=reason,
                claim="agent",
            )

        edit_calls = self._edit_calls(mock_run)
        assert edit_calls
        edit_args = list(edit_calls[-1][0])
        assert "--block" in edit_args
        assert edit_args[edit_args.index("--block") + 1] == reason
        assert "--release" in edit_args

    # ------------------------------------------------------------------ outcome=block validation (error)

    # AC: verify error returned (validation) when block_reason is empty
    @pytest.mark.asyncio
    async def test_block_without_reason_returns_error_before_any_cli_calls(self) -> None:
        """outcome=block with empty block_reason: returns error string, zero CLI calls."""
        mcp_ctx = self._make_mcp_ctx_with_statuses()

        with patch(
            "owlbear_mcp_kanban.server._run_kanban",
            new=AsyncMock(return_value=('{"id": 42}', "", 0)),
        ) as mock_run:
            result = await end_work(
                mcp_ctx, task_id="42", note="blocked", outcome="block", block_reason=""
            )

        assert isinstance(result, str)
        assert "error" in result.lower()
        mock_run.assert_not_called()

    # ------------------------------------------------------------------ outcome=reject (happy + boundary)

    # AC: verify edit called with -a NOTE -t --status move_to --release --json
    @pytest.mark.asyncio
    async def test_reject_edit_uses_move_to_status(self) -> None:
        """outcome=reject: edit call includes --status {move_to}."""
        mcp_ctx = self._make_mcp_ctx_with_statuses()

        with self._patch_run_always() as mock_run:
            await end_work(
                mcp_ctx,
                task_id="42",
                note="fundamental issue",
                outcome="reject",
                move_to="backlog",
                claim="agent",
            )

        edit_calls = self._edit_calls(mock_run)
        assert edit_calls
        edit_args = list(edit_calls[-1][0])
        assert "--status" in edit_args
        assert edit_args[edit_args.index("--status") + 1] == "backlog"
        assert "--release" in edit_args

    # AC: default move_to is ideation
    @pytest.mark.asyncio
    async def test_reject_default_move_to_is_ideation(self) -> None:
        """outcome=reject without explicit move_to: --status ideation is used."""
        mcp_ctx = self._make_mcp_ctx_with_statuses()

        with self._patch_run_always() as mock_run:
            await end_work(
                mcp_ctx, task_id="42", note="rejected", outcome="reject", claim="agent"
            )

        edit_calls = self._edit_calls(mock_run)
        assert edit_calls
        edit_args = list(edit_calls[-1][0])
        assert "--status" in edit_args
        assert edit_args[edit_args.index("--status") + 1] == "ideation"

    # ------------------------------------------------------------------ claim parameter (happy)

    # AC: when provided, pass to edit's --claim flag
    @pytest.mark.asyncio
    async def test_claim_provided_passed_to_edit(self) -> None:
        """When claim param is provided, it appears as --claim {claim} in the edit call."""
        statuses = ["todo", "in-progress", "review"]
        mcp_ctx = self._make_mcp_ctx_with_statuses(statuses)
        # claimed_by in show is different from provided claim — correct value must win
        show_resp = (self._show_json(status="in-progress", claimed_by="old-agent"), "", 0)
        edit_resp = ('{"id": 42}', "", 0)

        with self._patch_run_seq(show_resp, edit_resp) as mock_run:
            await end_work(
                mcp_ctx, task_id="42", note="done", outcome="success", claim="provided-agent"
            )

        edit_calls = self._edit_calls(mock_run)
        assert edit_calls
        edit_args = list(edit_calls[-1][0])
        assert "--claim" in edit_args
        assert edit_args[edit_args.index("--claim") + 1] == "provided-agent"

    # AC: when absent, read claimed_by from show JSON output
    @pytest.mark.asyncio
    async def test_claim_absent_reads_claimed_by_from_show_json(self) -> None:
        """When claim param is omitted, the claimed_by value from show JSON is used for --claim."""
        statuses = ["todo", "in-progress", "review"]
        mcp_ctx = self._make_mcp_ctx_with_statuses(statuses)
        show_resp = (self._show_json(status="in-progress", claimed_by="the-builder-agent"), "", 0)
        edit_resp = ('{"id": 42}', "", 0)

        with self._patch_run_seq(show_resp, edit_resp) as mock_run:
            # No claim param — must derive from show
            await end_work(mcp_ctx, task_id="42", note="done", outcome="success")

        edit_calls = self._edit_calls(mock_run)
        assert edit_calls
        edit_args = list(edit_calls[-1][0])
        assert "--claim" in edit_args
        assert edit_args[edit_args.index("--claim") + 1] == "the-builder-agent"

    # ------------------------------------------------------------------ error propagation (error)

    @pytest.mark.asyncio
    async def test_show_error_is_propagated(self) -> None:
        """If the initial show call fails, end_work returns an error string immediately."""
        mcp_ctx = self._make_mcp_ctx_with_statuses()

        with self._patch_run_seq(("", "task not found", 1)):
            result = await end_work(mcp_ctx, task_id="999", note="done", outcome="success")

        assert isinstance(result, str)
        assert "error" in result.lower()
