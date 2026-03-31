"""Failing RED-phase tests for owlbear CLI trigger commands.

Covers: CLI app structure (--help lists dispatch/run/status), dispatch command
(success output, task-not-found, already-claimed, ACP error, Copilot missing),
run command (single task, no tasks, --all loop, board re-read per iteration),
status command (counts per column, blocked tasks, exit 0), and error routing
(stderr via typer.echo err=True, exit 1 on all errors).

All tests fail on current HEAD because ``owlbear/cli.py`` does not exist yet.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner
from click.testing import Result as _ClickResult

from owlbear.cli import app  # ImportError until cli.py is implemented
from owlbear.planner.models import DispatchEntry, DispatchPlan, Task
from owlbear_orchestrator.acp_client import AcpClientError, ErrorCategory

_NOW = datetime(2026, 3, 30, tzinfo=UTC)
_CLI = "owlbear.cli"


# Click 8.2+ changed result.output to mix stdout+stderr. Restore pre-8.2 semantics
# so tests can assert stdout and stderr separately (test-writer intent).
class _Result(_ClickResult):
    @property
    def output(self) -> str:  # type: ignore[override]
        """Return stdout only (pre-8.2 semantics; tests assert stderr separately)."""
        return self.stdout


class _SeparatedCliRunner(CliRunner):
    def invoke(self, *args, **kwargs):  # type: ignore[override]
        result = super().invoke(*args, **kwargs)
        result.__class__ = _Result
        return result


runner = _SeparatedCliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _task(
    *,
    task_id: int = 1,
    title: str = "Test task",
    status: str = "todo",
    claimed_by: str | None = None,
) -> Task:
    """Return a minimal frozen Task for use in tests."""
    return Task(
        id=task_id,
        title=title,
        status=status,
        priority="important",
        created=_NOW,
        updated=_NOW,
        tags=[],
        depends_on=[],
        claimed_by=claimed_by,
        task_class="standard",
        body="",
        file=f"kanban/tasks/{task_id:03d}.md",
    )


def _entry(task_id: int = 1, agent: str = "builder") -> DispatchEntry:
    """Return a minimal DispatchEntry for use in tests."""
    return DispatchEntry(task_id=task_id, agent=agent, target_status="in-progress")


# ---------------------------------------------------------------------------
# CLI app structure
# ---------------------------------------------------------------------------


class TestFromAC_CLIAppStructure:  # noqa: N801
    """Typer app at owlbear.cli:app; --help output lists dispatch, run, status."""

    def test_help_lists_dispatch_command(self) -> None:
        """owlbear --help output contains 'dispatch'."""
        result = runner.invoke(app, ["--help"])
        assert "dispatch" in result.output

    def test_help_lists_run_command(self) -> None:
        """owlbear --help output contains 'run'."""
        result = runner.invoke(app, ["--help"])
        assert "run" in result.output

    def test_help_lists_status_command(self) -> None:
        """owlbear --help output contains 'status'."""
        result = runner.invoke(app, ["--help"])
        assert "status" in result.output


# ---------------------------------------------------------------------------
# owlbear dispatch <task_id>
# ---------------------------------------------------------------------------


class TestFromAC_DispatchCommand:  # noqa: N801
    """dispatch: positional int task_id, 'Dispatched #N to <agent>' on success, exit codes."""

    def test_dispatch_success_stdout_format(self) -> None:
        """Successful dispatch prints 'Dispatched #<id> to <agent>' and exits 0.

        Assumes cli.py name-imports: read_board, select_tasks (or equivalent),
        and a dispatch routine. Patch targets use owlbear.cli.* namespace.
        """
        entry = _entry(task_id=42, agent="builder")
        plan = DispatchPlan(entries=[entry])
        with (
            patch(f"{_CLI}.shutil.which", return_value="/usr/local/bin/gh"),
            patch(f"{_CLI}.read_board", new=AsyncMock(return_value=[_task(task_id=42)])),
            patch(f"{_CLI}.select_tasks", return_value=plan),
            patch(f"{_CLI}.AcpClient") as mock_acp,
        ):
            mock_acp.return_value.__aenter__ = AsyncMock(return_value=mock_acp.return_value)
            mock_acp.return_value.__aexit__ = AsyncMock(return_value=False)
            result = runner.invoke(app, ["dispatch", "42"])

        assert result.exit_code == 0
        assert "Dispatched #42" in result.output
        assert "builder" in result.output

    def test_dispatch_task_not_found_exits_1_stderr(self) -> None:
        """Unknown task_id: 'Task #<id> not found.' on stderr, exit 1."""
        with (
            patch(f"{_CLI}.shutil.which", return_value="/usr/local/bin/gh"),
            patch(f"{_CLI}.read_board", new=AsyncMock(return_value=[])),
        ):
            result = runner.invoke(app, ["dispatch", "9999"])

        assert result.exit_code == 1
        assert "9999" in result.stderr
        assert "not found" in result.stderr.lower()

    def test_dispatch_already_claimed_exits_1_stderr(self) -> None:
        """Claimed task: 'Task #<id> is already claimed by <agent>.' on stderr, exit 1."""
        claimed = _task(task_id=5, claimed_by="reviewer")
        with (
            patch(f"{_CLI}.shutil.which", return_value="/usr/local/bin/gh"),
            patch(f"{_CLI}.read_board", new=AsyncMock(return_value=[claimed])),
        ):
            result = runner.invoke(app, ["dispatch", "5"])

        assert result.exit_code == 1
        assert "5" in result.stderr
        assert "already claimed" in result.stderr.lower()
        assert "reviewer" in result.stderr

    def test_dispatch_acp_client_error_exits_1_stderr(self) -> None:
        """AcpClientError during dispatch: some message on stderr, exit 1."""
        entry = _entry(task_id=10, agent="builder")
        plan = DispatchPlan(entries=[entry])
        with (
            patch(f"{_CLI}.shutil.which", return_value="/usr/local/bin/gh"),
            patch(f"{_CLI}.read_board", new=AsyncMock(return_value=[_task(task_id=10)])),
            patch(f"{_CLI}.select_tasks", return_value=plan),
            patch(
                f"{_CLI}.AcpClient",
                side_effect=AcpClientError("connection refused", category=ErrorCategory.TRANSIENT),
            ),
        ):
            result = runner.invoke(app, ["dispatch", "10"])

        assert result.exit_code == 1
        assert result.stderr  # some error message present

    def test_dispatch_copilot_not_found_exact_message(self) -> None:
        """Copilot CLI missing: exact install hint on stderr, exit 1."""
        with patch(f"{_CLI}.shutil.which", return_value=None):
            result = runner.invoke(app, ["dispatch", "1"])

        assert result.exit_code == 1
        assert "Copilot CLI not found" in result.stderr
        assert "gh extension install github/gh-copilot" in result.stderr

    def test_dispatch_non_integer_task_id_rejected(self) -> None:
        """Non-integer task_id is rejected by Typer argument validation (exit != 0)."""
        result = runner.invoke(app, ["dispatch", "abc"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# owlbear run [--all]
# ---------------------------------------------------------------------------


class TestFromAC_RunCommand:  # noqa: N801
    """run: dispatches top-priority task; --all loops until board is empty."""

    def test_run_no_args_dispatches_top_priority_task(self) -> None:
        """run with no args dispatches the single top-priority task and exits 0."""
        task = _task(task_id=7, status="todo")
        plan = DispatchPlan(entries=[_entry(task_id=7, agent="builder")])
        with (
            patch(f"{_CLI}.shutil.which", return_value="/usr/local/bin/gh"),
            patch(f"{_CLI}.read_board", new=AsyncMock(return_value=[task])),
            patch(f"{_CLI}.select_tasks", return_value=plan),
            patch(f"{_CLI}.AcpClient") as mock_acp,
        ):
            mock_acp.return_value.__aenter__ = AsyncMock(return_value=mock_acp.return_value)
            mock_acp.return_value.__aexit__ = AsyncMock(return_value=False)
            result = runner.invoke(app, ["run"])

        assert result.exit_code == 0
        # Output contains task ID or agent name as confirmation
        assert "7" in result.output or "builder" in result.output

    def test_run_no_actionable_tasks_message_exit_0(self) -> None:
        """Empty board: prints 'No actionable tasks on the board.' and exits 0."""
        with (
            patch(f"{_CLI}.shutil.which", return_value="/usr/local/bin/gh"),
            patch(f"{_CLI}.read_board", new=AsyncMock(return_value=[])),
            patch(f"{_CLI}.select_tasks", return_value=DispatchPlan(entries=[])),
        ):
            result = runner.invoke(app, ["run"])

        assert result.exit_code == 0
        assert "No actionable tasks on the board." in result.output

    def test_run_all_loops_dispatches_each_task(self) -> None:
        """run --all dispatches all tasks across iterations, printing each result."""
        task_a = _task(task_id=1, status="todo")
        task_b = _task(task_id=2, status="todo")
        boards = [[task_a, task_b], [task_b], []]
        plans = [
            DispatchPlan(entries=[_entry(task_id=1, agent="builder")]),
            DispatchPlan(entries=[_entry(task_id=2, agent="reviewer")]),
            DispatchPlan(entries=[]),
        ]
        board_iter = iter(boards)
        plan_iter = iter(plans)
        with (
            patch(f"{_CLI}.shutil.which", return_value="/usr/local/bin/gh"),
            patch(f"{_CLI}.read_board", new=AsyncMock(side_effect=lambda *_a, **_kw: next(board_iter))),
            patch(f"{_CLI}.select_tasks", side_effect=lambda _: next(plan_iter)),
            patch(f"{_CLI}.AcpClient") as mock_acp,
        ):
            mock_acp.return_value.__aenter__ = AsyncMock(return_value=mock_acp.return_value)
            mock_acp.return_value.__aexit__ = AsyncMock(return_value=False)
            result = runner.invoke(app, ["run", "--all"])

        assert result.exit_code == 0
        # Both task IDs dispatched; confirm at least the first appeared
        assert "1" in result.output or "builder" in result.output

    def test_run_all_rereads_board_each_iteration(self) -> None:
        """run --all re-reads the board after each dispatch; tasks change mid-loop."""
        task = _task(task_id=3, status="todo")
        boards = [[task], []]
        plans = [
            DispatchPlan(entries=[_entry(task_id=3, agent="builder")]),
            DispatchPlan(entries=[]),
        ]
        board_mock = AsyncMock(side_effect=iter(boards))
        select_mock = MagicMock(side_effect=iter(plans))
        with (
            patch(f"{_CLI}.shutil.which", return_value="/usr/local/bin/gh"),
            patch(f"{_CLI}.read_board", new=board_mock),
            patch(f"{_CLI}.select_tasks", new=select_mock),
            patch(f"{_CLI}.AcpClient") as mock_acp,
        ):
            mock_acp.return_value.__aenter__ = AsyncMock(return_value=mock_acp.return_value)
            mock_acp.return_value.__aexit__ = AsyncMock(return_value=False)
            runner.invoke(app, ["run", "--all"])

        # Board must be read at least twice: once to find the task, once to detect empty
        assert board_mock.call_count >= 2  # noqa: PLR2004


# ---------------------------------------------------------------------------
# owlbear status
# ---------------------------------------------------------------------------

_STATUS_JSON = (
    '[{"id":1,"title":"T1","status":"backlog","priority":"important",'
    '"created":"2026-03-30T00:00:00Z","updated":"2026-03-30T00:00:00Z",'
    '"tags":[],"depends_on":[],"class":"standard","body":"","file":"f1.md"},'
    '{"id":2,"title":"T2","status":"backlog","priority":"important",'
    '"created":"2026-03-30T00:00:00Z","updated":"2026-03-30T00:00:00Z",'
    '"tags":[],"depends_on":[],"class":"standard","body":"","file":"f2.md"},'
    '{"id":3,"title":"T3","status":"todo","priority":"important",'
    '"created":"2026-03-30T00:00:00Z","updated":"2026-03-30T00:00:00Z",'
    '"tags":[],"depends_on":[],"class":"standard","body":"","file":"f3.md"}]'
)

_BLOCKED_JSON = (
    '[{"id":5,"title":"Blocked task","status":"todo","priority":"important",'
    '"created":"2026-03-30T00:00:00Z","updated":"2026-03-30T00:00:00Z",'
    '"tags":[],"depends_on":[],"class":"standard","body":"","file":"f5.md",'
    '"blocked":"Waiting on user decision"}]'
)


class TestFromAC_StatusCommand:  # noqa: N801
    """status: task counts per column via kanban-md subprocess, blocked task display, exit 0."""

    def _mock_subprocess(self, stdout: str) -> MagicMock:
        """Return a mock subprocess.CompletedProcess."""
        m = MagicMock()
        m.returncode = 0
        m.stdout = stdout
        return m

    def test_status_prints_count_per_status_column(self) -> None:
        """Output contains column names and their task counts (e.g. 'backlog: 2')."""
        with patch(f"{_CLI}.subprocess.run", return_value=self._mock_subprocess(_STATUS_JSON)):
            result = runner.invoke(app, ["status"])

        assert "backlog" in result.output
        assert "todo" in result.output
        assert "2" in result.output  # 2 backlog tasks in the mock data

    def test_status_shows_blocked_tasks_with_block_reason(self) -> None:
        """Blocked tasks and their block reasons appear in status output."""
        with patch(f"{_CLI}.subprocess.run", return_value=self._mock_subprocess(_BLOCKED_JSON)):
            result = runner.invoke(app, ["status"])

        # Some indicator of blocked status and the reason
        assert "Waiting on user decision" in result.output

    def test_status_always_exits_0(self) -> None:
        """status exits 0 regardless of board content."""
        with patch(f"{_CLI}.subprocess.run", return_value=self._mock_subprocess("[]")):
            result = runner.invoke(app, ["status"])

        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Error handling — stderr routing
# ---------------------------------------------------------------------------


class TestFromAC_ErrorHandling:  # noqa: N801
    """All error messages go to stderr via typer.echo(..., err=True); exit 1 on errors."""

    def test_copilot_not_found_install_hint_on_stderr(self) -> None:
        """Exact install hint 'gh extension install github/gh-copilot' on stderr."""
        with patch(f"{_CLI}.shutil.which", return_value=None):
            result = runner.invoke(app, ["dispatch", "1"])

        assert result.exit_code == 1
        assert "gh extension install github/gh-copilot" in result.stderr

    def test_task_not_found_message_contains_id_and_phrase(self) -> None:
        """'Task #<id> not found.' present on stderr when task does not exist."""
        with (
            patch(f"{_CLI}.shutil.which", return_value="/usr/bin/gh"),
            patch(f"{_CLI}.read_board", new=AsyncMock(return_value=[])),
        ):
            result = runner.invoke(app, ["dispatch", "123"])

        assert "123" in result.stderr
        assert "not found" in result.stderr.lower()

    def test_already_claimed_message_contains_id_and_agent(self) -> None:
        """'Task #<id> is already claimed by <agent>.' on stderr."""
        claimed = _task(task_id=99, claimed_by="architect")
        with (
            patch(f"{_CLI}.shutil.which", return_value="/usr/bin/gh"),
            patch(f"{_CLI}.read_board", new=AsyncMock(return_value=[claimed])),
        ):
            result = runner.invoke(app, ["dispatch", "99"])

        assert "99" in result.stderr
        assert "architect" in result.stderr

    def test_error_message_not_on_stdout(self) -> None:
        """Error messages must NOT appear on stdout; stdout stays clean on error."""
        with patch(f"{_CLI}.shutil.which", return_value=None):
            result = runner.invoke(app, ["dispatch", "1"])

        assert result.exit_code == 1
        assert "Copilot CLI not found" not in result.output  # stdout clean
        assert "Copilot CLI not found" in result.stderr


# ---------------------------------------------------------------------------
# ACP dispatch contract (retry-cycle additions — reviewer FAIL)
# ---------------------------------------------------------------------------


class TestFromAC_ACPDispatchContract:  # noqa: N801
    """AC: 'Dispatches to selected agent via AcpClient (async, wrapped with asyncio.run())'.

    The prior cycle's _do_dispatch stub opens an AcpClient context with ``pass`` and
    calls no methods. These tests prove the contract: AcpClient must invoke
    new_session() for the command to dispatch. All three FAIL against the stub.
    """

    def test_dispatch_command_calls_new_session_on_acp_client(self) -> None:
        """dispatch invokes client.new_session() -- a no-op stub fails this assertion.

        AC: 'Dispatches to selected agent via AcpClient'
        """
        entry = _entry(task_id=77, agent="builder")
        plan = DispatchPlan(entries=[entry])
        mock_client = AsyncMock()
        mock_instance = MagicMock()
        mock_instance.__aenter__ = AsyncMock(return_value=mock_client)
        mock_instance.__aexit__ = AsyncMock(return_value=False)
        with (
            patch(f"{_CLI}.shutil.which", return_value="/usr/local/bin/gh"),
            patch(f"{_CLI}.read_board", new=AsyncMock(return_value=[_task(task_id=77)])),
            patch(f"{_CLI}.select_tasks", return_value=plan),
            patch(f"{_CLI}.AcpClient", return_value=mock_instance),
        ):
            runner.invoke(app, ["dispatch", "77"])

        mock_client.new_session.assert_called_once()

    def test_run_command_calls_new_session_on_acp_client(self) -> None:
        """run invokes client.new_session() -- a no-op stub fails this assertion.

        AC: 'Dispatches to selected agent via AcpClient'
        """
        task = _task(task_id=88, status="todo")
        plan = DispatchPlan(entries=[_entry(task_id=88, agent="reviewer")])
        mock_client = AsyncMock()
        mock_instance = MagicMock()
        mock_instance.__aenter__ = AsyncMock(return_value=mock_client)
        mock_instance.__aexit__ = AsyncMock(return_value=False)
        with (
            patch(f"{_CLI}.shutil.which", return_value="/usr/local/bin/gh"),
            patch(f"{_CLI}.read_board", new=AsyncMock(return_value=[task])),
            patch(f"{_CLI}.select_tasks", return_value=plan),
            patch(f"{_CLI}.AcpClient", return_value=mock_instance),
        ):
            runner.invoke(app, ["run"])

        mock_client.new_session.assert_called_once()

    def test_run_new_session_acp_error_exits_1_stderr(self) -> None:
        """AcpClientError from new_session in run: message on stderr, exit 1.

        Tests lines 99-101: run._run_once() catches AcpClientError and routes to stderr.
        Against stub: new_session is never called, no exception raised, run exits 0 -- FAILS.
        Against correct impl: new_session raises, _run_once catches it, exits 1 -- PASSES.
        """
        task = _task(task_id=99, status="todo")
        plan = DispatchPlan(entries=[_entry(task_id=99, agent="builder")])
        mock_client = AsyncMock()
        mock_client.new_session.side_effect = AcpClientError(
            "session start failed", category=ErrorCategory.TRANSIENT
        )
        mock_instance = MagicMock()
        mock_instance.__aenter__ = AsyncMock(return_value=mock_client)
        mock_instance.__aexit__ = AsyncMock(return_value=False)
        with (
            patch(f"{_CLI}.shutil.which", return_value="/usr/local/bin/gh"),
            patch(f"{_CLI}.read_board", new=AsyncMock(return_value=[task])),
            patch(f"{_CLI}.select_tasks", return_value=plan),
            patch(f"{_CLI}.AcpClient", return_value=mock_instance),
        ):
            result = runner.invoke(app, ["run"])

        assert result.exit_code == 1
        assert result.stderr  # error message routed to stderr


# ---------------------------------------------------------------------------
# Builder-discovered edge cases
# ---------------------------------------------------------------------------


class TestBuilderDiscovered:
    """Edge cases discovered during GREEN phase implementation."""

    def test_dispatch_no_plan_entries_exits_1_stderr(self) -> None:
        """dispatch: task exists but select_tasks returns no entries → 'not found' stderr, exit 1.

        Covers the no-plan path in dispatch (cli.py lines 67-68).
        """
        with (
            patch(f"{_CLI}.shutil.which", return_value="/usr/local/bin/gh"),
            patch(f"{_CLI}.read_board", new=AsyncMock(return_value=[_task(task_id=55)])),
            patch(f"{_CLI}.select_tasks", return_value=DispatchPlan(entries=[])),
        ):
            result = runner.invoke(app, ["dispatch", "55"])

        assert result.exit_code == 1
        assert "55" in result.stderr
        assert "not found" in result.stderr.lower()

