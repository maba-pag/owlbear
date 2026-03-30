"""Failing tests for task #153: planner board reader (TDD RED).

Covers the interface contract from AC:
  - read_board() success: returns list[Task] from parsed subprocess JSON
  - read_board() empty board: returns empty list
  - read_board() non-zero exit: raises BoardReadError containing stderr
  - read_board() missing binary: propagates FileNotFoundError
  - read_board() scope filter: adds --tag {scope} to subprocess args
  - read_board() default args: --json --unblocked --not-blocked --unclaimed --no-color --dir

All tests FAIL in RED phase — ImportError expected until builder implements #144.
Mocking pattern follows packages/mcp-kanban/tests/test_server.py.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

# ---------------------------------------------------------------------------
# Import targets — will raise ImportError until builder implements #144 (RED)
# ---------------------------------------------------------------------------
from owlbear.planner.board import BoardReadError, read_board  # type: ignore[import]

# ---------------------------------------------------------------------------
# Canned subprocess stdout — minimal valid kanban-md JSON (S3.1 schema)
# ---------------------------------------------------------------------------

_TASK_OBJ = (
    '{"id":42,"title":"Test task","status":"todo","priority":"important",'
    '"created":"2026-01-01T00:00:00+00:00","updated":"2026-01-01T00:00:00+00:00",'
    '"tags":[],"depends_on":[],"class":"standard","body":"","file":"/k/42.md"}'
)
CANNED_TASK_JSON = f"[{_TASK_OBJ}]"

KANBAN_BIN = Path("/fake/kanban-md")
KANBAN_DIR = Path("/fake/kanban")


def _mock_proc(
    stdout: str = CANNED_TASK_JSON,
    stderr: str = "",
    returncode: int = 0,
) -> AsyncMock:
    """Return a mock asyncio Process with configurable output."""
    proc = AsyncMock()
    proc.communicate.return_value = (stdout.encode(), stderr.encode())
    proc.returncode = returncode
    return proc


# ---------------------------------------------------------------------------
# TestFromAC_ReadBoard
# ---------------------------------------------------------------------------


class TestFromAC_ReadBoard:
    """Contract tests for read_board() async function derived from #153 AC."""

    @pytest.mark.asyncio
    async def test_success_returns_list_of_tasks(self) -> None:
        """read_board() success: mocked subprocess returns valid JSON → list[Task]."""
        mock_proc = _mock_proc()
        with patch("owlbear.planner.board.asyncio.create_subprocess_exec", return_value=mock_proc):
            tasks = await read_board(KANBAN_BIN, KANBAN_DIR)
        assert isinstance(tasks, list)
        assert len(tasks) == 1
        assert tasks[0].id == 42

    @pytest.mark.asyncio
    async def test_empty_board_returns_empty_list(self) -> None:
        """read_board() with subprocess stdout='[]' returns an empty list."""
        mock_proc = _mock_proc(stdout="[]")
        with patch("owlbear.planner.board.asyncio.create_subprocess_exec", return_value=mock_proc):
            tasks = await read_board(KANBAN_BIN, KANBAN_DIR)
        assert tasks == []

    @pytest.mark.asyncio
    async def test_non_zero_exit_raises_board_read_error(self) -> None:
        """read_board() with rc=1 raises BoardReadError."""
        mock_proc = _mock_proc(stdout="", stderr="fatal: command failed", returncode=1)
        with (
            patch("owlbear.planner.board.asyncio.create_subprocess_exec", return_value=mock_proc),
            pytest.raises(BoardReadError),
        ):
            await read_board(KANBAN_BIN, KANBAN_DIR)

    @pytest.mark.asyncio
    async def test_board_read_error_contains_stderr(self) -> None:
        """BoardReadError message includes the stderr text from the subprocess."""
        mock_proc = _mock_proc(stdout="", stderr="binary crashed: SIGKILL", returncode=2)
        with (
            patch("owlbear.planner.board.asyncio.create_subprocess_exec", return_value=mock_proc),
            pytest.raises(BoardReadError, match="binary crashed: SIGKILL"),
        ):
            await read_board(KANBAN_BIN, KANBAN_DIR)

    @pytest.mark.asyncio
    async def test_missing_binary_propagates_file_not_found(self) -> None:
        """read_board() propagates FileNotFoundError when the kanban-md binary is absent."""
        with (
            patch(
                "owlbear.planner.board.asyncio.create_subprocess_exec",
                side_effect=FileNotFoundError("No such file or directory: '/fake/kanban-md'"),
            ),
            pytest.raises(FileNotFoundError),
        ):
            await read_board(KANBAN_BIN, KANBAN_DIR)

    @pytest.mark.asyncio
    async def test_scope_filter_adds_tag_flag(self) -> None:
        """scope='phase-2' adds --tag phase-2 to the subprocess invocation args."""
        mock_proc = _mock_proc()
        with patch(
            "owlbear.planner.board.asyncio.create_subprocess_exec",
            return_value=mock_proc,
        ) as mock_exec:
            await read_board(KANBAN_BIN, KANBAN_DIR, scope="phase-2")

        flat_args = " ".join(str(a) for a in mock_exec.call_args.args)
        assert "--tag" in flat_args
        assert "phase-2" in flat_args

    @pytest.mark.asyncio
    async def test_default_args_include_required_flags(self) -> None:
        """Default call includes --json, --unblocked, --not-blocked, --unclaimed, --no-color, --dir."""
        mock_proc = _mock_proc()
        with patch(
            "owlbear.planner.board.asyncio.create_subprocess_exec",
            return_value=mock_proc,
        ) as mock_exec:
            await read_board(KANBAN_BIN, KANBAN_DIR)

        flat_args = " ".join(str(a) for a in mock_exec.call_args.args)
        for flag in ("--json", "--unblocked", "--not-blocked", "--unclaimed", "--no-color", "--dir"):
            assert flag in flat_args, f"Missing expected flag: {flag}"

    @pytest.mark.asyncio
    async def test_board_read_error_is_owlbear_error(self) -> None:
        """BoardReadError is a subclass of OwlBearError (follows project exception hierarchy)."""
        from owlbear.errors import OwlBearError  # noqa: PLC0415

        assert issubclass(BoardReadError, OwlBearError)
