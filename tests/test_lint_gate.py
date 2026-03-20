"""Tests for the deterministic post-implementation lint gate (#704).

Re-cycle RED phase — reviewer rejected for dead-code LintGateError and
duplicated retry logic.  Revised tests enforce that lint failure routes
through the existing task-level retry mechanism (#625) via LintGateError,
rather than duplicating the retry code path.

Tests define the expected contract for:
- LintGateResult dataclass: passed, errors, files_checked
- LintGateError exception carrying lint output
- run_lint_gate(): git diff strategy, ruff subprocess, graceful degradation
- Integration with reconcile_tasks: lint pass → review, lint fail → retry
  via existing mechanism (including hook emission)
- Config toggle: lint_gate_enabled in OwlBearSettings
"""

from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _git_mock(stdout: str, returncode: int = 0) -> MagicMock:
    return MagicMock(stdout=stdout, returncode=returncode)


def _ruff_mock(stdout: str = "", returncode: int = 0) -> MagicMock:
    return MagicMock(stdout=stdout, returncode=returncode)


def _resolve(val: MagicMock | Exception) -> MagicMock:
    """Return *val* if it's a mock, raise it if it's an exception."""
    if isinstance(val, Exception):
        raise val
    return val


def _make_subprocess_router(
    git_uncommitted: MagicMock | Exception,
    git_last_commit: MagicMock | Exception | None = None,
    ruff_check: MagicMock | Exception | None = None,
    ruff_format: MagicMock | Exception | None = None,
) -> Any:
    """Build a side_effect function for subprocess.run that routes by command."""
    if git_last_commit is None:
        git_last_commit = git_uncommitted
    if ruff_check is None:
        ruff_check = _ruff_mock()
    if ruff_format is None:
        ruff_format = _ruff_mock()

    def _route(cmd: list[str], **_kw: object) -> MagicMock:
        cmd_str = " ".join(cmd)
        if "git" in cmd_str and "HEAD~1" in cmd_str:
            return _resolve(git_last_commit)
        if "git" in cmd_str:
            return _resolve(git_uncommitted)
        if "ruff" in cmd_str and "format" in cmd_str:
            return _resolve(ruff_format)
        if "ruff" in cmd_str and "check" in cmd_str:
            return _resolve(ruff_check)
        return _ruff_mock()

    return _route


def _make_done_task(*, exception: BaseException | None = None) -> MagicMock:
    """Build a mock asyncio.Task that is done with optional exception."""
    task = MagicMock(spec=asyncio.Task)
    task.done.return_value = True
    task.exception.return_value = exception
    task.result.return_value = "built" if exception is None else None
    return task


# ---------------------------------------------------------------------------
# AC 1: LintGateResult dataclass
# ---------------------------------------------------------------------------


class TestFromACLintGateResult:
    """LintGateResult dataclass in src/owlbear/core/lint_gate.py:
    passed: bool, errors: str, files_checked: list[str]."""

    def test_import_exists(self) -> None:
        from owlbear.core.lint_gate import LintGateResult  # noqa: F401

    def test_construct_passing(self) -> None:
        from owlbear.core.lint_gate import LintGateResult

        result = LintGateResult(passed=True, errors="", files_checked=["a.py"])
        assert result.passed is True
        assert result.errors == ""
        assert result.files_checked == ["a.py"]

    def test_construct_failing(self) -> None:
        from owlbear.core.lint_gate import LintGateResult

        result = LintGateResult(
            passed=False,
            errors="E501 line too long",
            files_checked=["b.py", "c.py"],
        )
        assert result.passed is False
        assert "E501" in result.errors
        assert len(result.files_checked) == 2

    def test_empty_files_checked(self) -> None:
        from owlbear.core.lint_gate import LintGateResult

        result = LintGateResult(passed=True, errors="", files_checked=[])
        assert result.files_checked == []


# ---------------------------------------------------------------------------
# AC 5: LintGateError exception
# ---------------------------------------------------------------------------


class TestFromACLintGateError:
    """LintGateError(Exception) in lint_gate.py carries lint output string."""

    def test_import_exists(self) -> None:
        from owlbear.core.lint_gate import LintGateError  # noqa: F401

    def test_carries_lint_output(self) -> None:
        from owlbear.core.lint_gate import LintGateError

        err = LintGateError("ruff check found 3 errors")
        assert "3 errors" in str(err)

    def test_is_exception_subclass(self) -> None:
        from owlbear.core.lint_gate import LintGateError

        assert issubclass(LintGateError, Exception)

    def test_can_be_raised_and_caught(self) -> None:
        from owlbear.core.lint_gate import LintGateError

        with pytest.raises(LintGateError, match="lint failed"):
            raise LintGateError("lint failed")  # noqa: EM101, TRY003


# ---------------------------------------------------------------------------
# AC 2: run_lint_gate — happy path
# ---------------------------------------------------------------------------


class TestFromACRunLintGateHappy:
    """run_lint_gate returns passing result when ruff reports no issues."""

    @pytest.mark.asyncio
    async def test_lint_pass_returns_passed_true(self) -> None:
        from owlbear.core.lint_gate import run_lint_gate

        workspace = Path("/fake/workspace")
        router = _make_subprocess_router(
            git_uncommitted=_git_mock("src/a.py\nsrc/b.py\n"),
            git_last_commit=_git_mock("src/b.py\nsrc/c.py\n"),
            ruff_check=_ruff_mock(),
            ruff_format=_ruff_mock(),
        )

        with patch("subprocess.run", side_effect=router):
            result = await (run_lint_gate(workspace))

        assert result.passed is True
        assert result.errors == ""
        # Union of uncommitted + last commit .py files: a.py, b.py, c.py
        assert len(result.files_checked) == 3

    @pytest.mark.asyncio
    async def test_files_checked_is_union_of_both_diffs(self) -> None:
        """Changed-files strategy: union of uncommitted + last commit diffs."""
        from owlbear.core.lint_gate import run_lint_gate

        workspace = Path("/fake/workspace")
        router = _make_subprocess_router(
            git_uncommitted=_git_mock("x.py\n"),
            git_last_commit=_git_mock("y.py\n"),
        )

        with patch("subprocess.run", side_effect=router):
            result = await (run_lint_gate(workspace))

        assert sorted(result.files_checked) == ["x.py", "y.py"]


# ---------------------------------------------------------------------------
# AC 2: run_lint_gate — lint failure
# ---------------------------------------------------------------------------


class TestFromACRunLintGateFailure:
    """run_lint_gate returns LintGateResult(passed=False) when ruff fails."""

    @pytest.mark.asyncio
    async def test_ruff_check_failure_returns_passed_false(self) -> None:
        from owlbear.core.lint_gate import run_lint_gate

        workspace = Path("/fake/workspace")
        router = _make_subprocess_router(
            git_uncommitted=_git_mock("bad.py\n"),
            ruff_check=_ruff_mock("bad.py:1:1 E501 line too long", returncode=1),
        )

        with patch("subprocess.run", side_effect=router):
            result = await (run_lint_gate(workspace))

        assert result.passed is False
        assert "E501" in result.errors

    @pytest.mark.asyncio
    async def test_ruff_format_failure_returns_passed_false(self) -> None:
        from owlbear.core.lint_gate import run_lint_gate

        workspace = Path("/fake/workspace")
        router = _make_subprocess_router(
            git_uncommitted=_git_mock("ugly.py\n"),
            ruff_format=_ruff_mock("ugly.py would be reformatted", returncode=1),
        )

        with patch("subprocess.run", side_effect=router):
            result = await (run_lint_gate(workspace))

        assert result.passed is False
        assert "reformatted" in result.errors

    @pytest.mark.asyncio
    async def test_combined_check_and_format_errors(self) -> None:
        from owlbear.core.lint_gate import run_lint_gate

        workspace = Path("/fake/workspace")
        router = _make_subprocess_router(
            git_uncommitted=_git_mock("mess.py\n"),
            ruff_check=_ruff_mock("check error", returncode=1),
            ruff_format=_ruff_mock("format error", returncode=1),
        )

        with patch("subprocess.run", side_effect=router):
            result = await (run_lint_gate(workspace))

        assert result.passed is False
        assert "check error" in result.errors
        assert "format error" in result.errors


# ---------------------------------------------------------------------------
# AC 2: run_lint_gate — empty changeset
# ---------------------------------------------------------------------------


class TestFromACRunLintGateEmptyChangeset:
    """Empty changeset: if union of changed .py files is empty, return passed."""

    @pytest.mark.asyncio
    async def test_no_changed_files_passes(self) -> None:
        from owlbear.core.lint_gate import run_lint_gate

        workspace = Path("/fake/workspace")
        router = _make_subprocess_router(git_uncommitted=_git_mock("\n"))

        with patch("subprocess.run", side_effect=router):
            result = await (run_lint_gate(workspace))

        assert result.passed is True
        assert result.errors == ""
        assert result.files_checked == []

    @pytest.mark.asyncio
    async def test_only_non_python_files_passes(self) -> None:
        from owlbear.core.lint_gate import run_lint_gate

        workspace = Path("/fake/workspace")
        router = _make_subprocess_router(
            git_uncommitted=_git_mock("README.md\npackage.json\n"),
        )

        with patch("subprocess.run", side_effect=router):
            result = await (run_lint_gate(workspace))

        assert result.passed is True
        assert result.files_checked == []


# ---------------------------------------------------------------------------
# AC 2: run_lint_gate — .py extension filter
# ---------------------------------------------------------------------------


class TestFromACRunLintGatePyFilter:
    """Changed-files are filtered to .py extensions only."""

    @pytest.mark.asyncio
    async def test_filters_to_py_only(self) -> None:
        from owlbear.core.lint_gate import run_lint_gate

        workspace = Path("/fake/workspace")
        router = _make_subprocess_router(
            git_uncommitted=_git_mock("a.py\nb.txt\nc.py\nd.json\n"),
        )

        with patch("subprocess.run", side_effect=router):
            result = await (run_lint_gate(workspace))

        assert sorted(result.files_checked) == ["a.py", "c.py"]


# ---------------------------------------------------------------------------
# AC 2: run_lint_gate — git diff union deduplication
# ---------------------------------------------------------------------------


class TestFromACRunLintGateDedup:
    """Files appearing in both diffs are only checked once."""

    @pytest.mark.asyncio
    async def test_deduplicates_across_diffs(self) -> None:
        from owlbear.core.lint_gate import run_lint_gate

        workspace = Path("/fake/workspace")
        router = _make_subprocess_router(
            git_uncommitted=_git_mock("shared.py\nonly_a.py\n"),
            git_last_commit=_git_mock("shared.py\nonly_b.py\n"),
        )

        with patch("subprocess.run", side_effect=router):
            result = await (run_lint_gate(workspace))

        # shared.py should appear once, not twice
        assert sorted(result.files_checked) == ["only_a.py", "only_b.py", "shared.py"]


# ---------------------------------------------------------------------------
# AC 2: run_lint_gate — graceful degradation
# ---------------------------------------------------------------------------


class TestFromACRunLintGateGracefulDegradation:
    """Graceful degradation: ruff/git binary missing or subprocess timeout
    returns passed=True with warning log. Never blocks pipeline."""

    @pytest.mark.asyncio
    async def test_ruff_binary_missing_degrades_gracefully(self) -> None:
        from owlbear.core.lint_gate import run_lint_gate

        workspace = Path("/fake/workspace")
        router = _make_subprocess_router(
            git_uncommitted=_git_mock("a.py\n"),
            ruff_check=FileNotFoundError("ruff not found"),
        )

        with patch("subprocess.run", side_effect=router):
            result = await (run_lint_gate(workspace))

        assert result.passed is True

    @pytest.mark.asyncio
    async def test_git_binary_missing_degrades_gracefully(self) -> None:
        from owlbear.core.lint_gate import run_lint_gate

        workspace = Path("/fake/workspace")
        router = _make_subprocess_router(
            git_uncommitted=FileNotFoundError("git not found"),
        )

        with patch("subprocess.run", side_effect=router):
            result = await (run_lint_gate(workspace))

        assert result.passed is True

    @pytest.mark.asyncio
    async def test_subprocess_timeout_degrades_gracefully(self) -> None:
        from owlbear.core.lint_gate import run_lint_gate

        workspace = Path("/fake/workspace")
        router = _make_subprocess_router(
            git_uncommitted=_git_mock("a.py\n"),
            ruff_check=subprocess.TimeoutExpired(cmd=["ruff"], timeout=10),
        )

        with patch("subprocess.run", side_effect=router):
            result = await (run_lint_gate(workspace))

        assert result.passed is True

    @pytest.mark.asyncio
    async def test_git_timeout_degrades_gracefully(self) -> None:
        from owlbear.core.lint_gate import run_lint_gate

        workspace = Path("/fake/workspace")
        router = _make_subprocess_router(
            git_uncommitted=subprocess.TimeoutExpired(cmd=["git"], timeout=10),
        )

        with patch("subprocess.run", side_effect=router):
            result = await (run_lint_gate(workspace))

        assert result.passed is True


# ---------------------------------------------------------------------------
# AC 2: run_lint_gate — cwd parameter
# ---------------------------------------------------------------------------


class TestFromACRunLintGateCwd:
    """run_lint_gate runs subprocess with cwd=workspace."""

    @pytest.mark.asyncio
    async def test_subprocess_cwd_is_workspace(self) -> None:
        from owlbear.core.lint_gate import run_lint_gate

        workspace = Path("/my/project")
        cwd_values: list[object] = []

        def _spy(cmd: list[str], **kw: object) -> MagicMock:
            cwd_values.append(kw.get("cwd"))
            cmd_str = " ".join(cmd)
            if "git" in cmd_str:
                return _git_mock("a.py\n")
            return _ruff_mock()

        with patch("subprocess.run", side_effect=_spy):
            await (run_lint_gate(workspace))

        # All subprocess calls should use cwd=workspace
        assert all(cwd == workspace for cwd in cwd_values)


# ---------------------------------------------------------------------------
# AC 3: Integration in reconcile_tasks — lint pass proceeds to review
# ---------------------------------------------------------------------------


class TestFromACReconcileLintPass:
    """After builder success with lint gate enabled, lint pass -> review."""

    @pytest.mark.asyncio
    async def test_lint_pass_moves_to_review(self) -> None:
        from owlbear.daemon import OrchestratorState, RunningTask, reconcile_tasks

        state = OrchestratorState()
        mock_kanban = AsyncMock()

        state.running["704"] = RunningTask(task_id="704", asyncio_task=_make_done_task())
        state.claimed.add("704")
        mock_kanban.kanban_move.return_value = "moved"

        with patch("owlbear.daemon.run_lint_gate") as mock_lint:
            from owlbear.core.lint_gate import LintGateResult

            mock_lint.return_value = LintGateResult(
                passed=True,
                errors="",
                files_checked=["a.py"],
            )

            async def go() -> None:
                await reconcile_tasks(
                    state=state,
                    kanban=mock_kanban,
                    lint_gate_enabled=True,
                    workspace=Path("/fake"),
                )

            await (go())

        mock_kanban.kanban_move.assert_any_call("704", "review")
        assert "704" not in state.running


# ---------------------------------------------------------------------------
# AC 3: Integration — lint fail triggers retry via existing mechanism
# ---------------------------------------------------------------------------


class TestFromACReconcileLintFail:
    """After builder success, lint FAIL -> raise LintGateError -> existing
    task-level retry mechanism (#625) handles it, including WIP + hooks."""

    @pytest.mark.asyncio
    async def test_lint_fail_does_not_advance_to_review(self) -> None:
        from owlbear.daemon import OrchestratorState, RunningTask, reconcile_tasks

        state = OrchestratorState()
        mock_kanban = AsyncMock()

        state.running["705"] = RunningTask(task_id="705", asyncio_task=_make_done_task())
        state.claimed.add("705")

        with patch("owlbear.daemon.run_lint_gate") as mock_lint:
            from owlbear.core.lint_gate import LintGateResult

            mock_lint.return_value = LintGateResult(
                passed=False,
                errors="E501 line too long",
                files_checked=["bad.py"],
            )

            async def go() -> None:
                await reconcile_tasks(
                    state=state,
                    kanban=mock_kanban,
                    lint_gate_enabled=True,
                    workspace=Path("/fake"),
                )

            await (go())

        review_calls = [
            c for c in mock_kanban.kanban_move.call_args_list if c.args == ("705", "review")
        ]
        assert len(review_calls) == 0

    @pytest.mark.asyncio
    async def test_lint_fail_stores_lint_errors_in_wip(self) -> None:
        from owlbear.daemon import OrchestratorState, RunningTask, reconcile_tasks

        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_wip = MagicMock()

        state.running["706"] = RunningTask(task_id="706", asyncio_task=_make_done_task())
        state.claimed.add("706")

        with patch("owlbear.daemon.run_lint_gate") as mock_lint:
            from owlbear.core.lint_gate import LintGateResult

            mock_lint.return_value = LintGateResult(
                passed=False,
                errors="E501 line too long\nW291 trailing whitespace",
                files_checked=["file.py"],
            )

            async def go() -> None:
                await reconcile_tasks(
                    state=state,
                    kanban=mock_kanban,
                    wip_store=mock_wip,
                    lint_gate_enabled=True,
                    workspace=Path("/fake"),
                )

            await (go())

        mock_wip.save.assert_called_once()
        summary = mock_wip.save.call_args.kwargs["summary"]
        assert "E501" in summary or "lint" in summary.lower()

    @pytest.mark.asyncio
    async def test_lint_fail_triggers_retry(self) -> None:
        """Lint failure must schedule a retry via the existing mechanism."""
        from owlbear.daemon import OrchestratorState, RunningTask, reconcile_tasks

        state = OrchestratorState()
        mock_kanban = AsyncMock()

        state.running["707"] = RunningTask(task_id="707", asyncio_task=_make_done_task())
        state.claimed.add("707")

        with patch("owlbear.daemon.run_lint_gate") as mock_lint:
            from owlbear.core.lint_gate import LintGateResult

            mock_lint.return_value = LintGateResult(
                passed=False,
                errors="E501 line too long",
                files_checked=["bad.py"],
            )

            async def go() -> None:
                await reconcile_tasks(
                    state=state,
                    kanban=mock_kanban,
                    lint_gate_enabled=True,
                    workspace=Path("/fake"),
                )

            await (go())

        assert "707" in state.retries

    @pytest.mark.asyncio
    async def test_lint_fail_emits_task_complete_failure_hook(self) -> None:
        """AC says 'raise LintGateError to trigger existing task-level retry
        mechanism (#625)'.  The existing mechanism emits TASK_COMPLETE with
        outcome='failure'.  If lint failure bypasses hook emission, the
        implementation is duplicating retry logic instead of reusing it."""
        from owlbear.core.hooks import HookEvent
        from owlbear.daemon import OrchestratorState, RunningTask, reconcile_tasks

        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_hooks = AsyncMock()

        state.running["708"] = RunningTask(task_id="708", asyncio_task=_make_done_task())
        state.claimed.add("708")

        with patch("owlbear.daemon.run_lint_gate") as mock_lint:
            from owlbear.core.lint_gate import LintGateResult

            mock_lint.return_value = LintGateResult(
                passed=False,
                errors="E501 line too long",
                files_checked=["bad.py"],
            )

            async def go() -> None:
                await reconcile_tasks(
                    state=state,
                    kanban=mock_kanban,
                    hooks=mock_hooks,
                    lint_gate_enabled=True,
                    workspace=Path("/fake"),
                )

            await (go())

        # The existing retry mechanism (#625) emits TASK_COMPLETE with failure.
        # If this assertion fails, lint failure is using a separate code path.
        mock_hooks.emit.assert_any_call(
            HookEvent.TASK_COMPLETE,
            {"task_id": "708", "outcome": "failure"},
        )


# ---------------------------------------------------------------------------
# AC 3: Integration — lint retry exhaustion blocks task
# ---------------------------------------------------------------------------


class TestFromACReconcileLintRetryExhaustion:
    """When lint gate fails and retries are exhausted, block the task."""

    @pytest.mark.asyncio
    async def test_lint_retry_exhausted_blocks_task(self) -> None:
        """After max retry attempts for lint failures, task should be blocked
        on kanban and claim released — same as the existing retry mechanism."""
        from owlbear.daemon import (
            OrchestratorState,
            RetryEntry,
            RunningTask,
            reconcile_tasks,
        )

        state = OrchestratorState()
        mock_kanban = AsyncMock()

        state.running["709"] = RunningTask(task_id="709", asyncio_task=_make_done_task())
        state.claimed.add("709")
        # Already at max attempts (5 by default)
        state.retries["709"] = RetryEntry(
            task_id="709",
            attempt=5,
            next_due=MagicMock(),
            last_error="previous lint failure",
        )

        with patch("owlbear.daemon.run_lint_gate") as mock_lint:
            from owlbear.core.lint_gate import LintGateResult

            mock_lint.return_value = LintGateResult(
                passed=False,
                errors="E501 still failing",
                files_checked=["bad.py"],
            )

            async def go() -> None:
                await reconcile_tasks(
                    state=state,
                    kanban=mock_kanban,
                    lint_gate_enabled=True,
                    workspace=Path("/fake"),
                )

            await (go())

        # Task should be blocked on kanban
        mock_kanban.kanban_edit.assert_called_once()
        block_arg = mock_kanban.kanban_edit.call_args.kwargs.get("block", "")
        assert "retry" in block_arg.lower() or "exhaust" in block_arg.lower()

        # Claim should be released
        assert "709" not in state.claimed


# ---------------------------------------------------------------------------
# AC 3: Integration — gate disabled skips lint
# ---------------------------------------------------------------------------


class TestFromACReconcileLintDisabled:
    """When lint_gate_enabled=False or workspace=None, skip lint gate."""

    @pytest.mark.asyncio
    async def test_disabled_flag_skips_gate(self) -> None:
        from owlbear.daemon import OrchestratorState, RunningTask, reconcile_tasks

        state = OrchestratorState()
        mock_kanban = AsyncMock()

        state.running["710"] = RunningTask(task_id="710", asyncio_task=_make_done_task())
        state.claimed.add("710")
        mock_kanban.kanban_move.return_value = "moved"

        with patch("owlbear.daemon.run_lint_gate") as mock_lint:

            async def go() -> None:
                await reconcile_tasks(
                    state=state,
                    kanban=mock_kanban,
                    lint_gate_enabled=False,
                    workspace=Path("/fake"),
                )

            await (go())

        mock_lint.assert_not_called()
        mock_kanban.kanban_move.assert_any_call("710", "review")

    @pytest.mark.asyncio
    async def test_none_workspace_skips_gate(self) -> None:
        from owlbear.daemon import OrchestratorState, RunningTask, reconcile_tasks

        state = OrchestratorState()
        mock_kanban = AsyncMock()

        state.running["711"] = RunningTask(task_id="711", asyncio_task=_make_done_task())
        state.claimed.add("711")
        mock_kanban.kanban_move.return_value = "moved"

        with patch("owlbear.daemon.run_lint_gate") as mock_lint:

            async def go() -> None:
                await reconcile_tasks(
                    state=state,
                    kanban=mock_kanban,
                    lint_gate_enabled=True,
                    workspace=None,
                )

            await (go())

        mock_lint.assert_not_called()
        mock_kanban.kanban_move.assert_any_call("711", "review")

    @pytest.mark.asyncio
    async def test_default_params_skip_gate(self) -> None:
        """Default lint_gate_enabled=False and workspace=None skip gate."""
        from owlbear.daemon import OrchestratorState, RunningTask, reconcile_tasks

        state = OrchestratorState()
        mock_kanban = AsyncMock()

        state.running["712"] = RunningTask(task_id="712", asyncio_task=_make_done_task())
        state.claimed.add("712")
        mock_kanban.kanban_move.return_value = "moved"

        with patch("owlbear.daemon.run_lint_gate") as mock_lint:

            async def go() -> None:
                await reconcile_tasks(state=state, kanban=mock_kanban)

            await (go())

        mock_lint.assert_not_called()
        mock_kanban.kanban_move.assert_any_call("712", "review")


# ---------------------------------------------------------------------------
# AC 6: Config field lint_gate_enabled
# ---------------------------------------------------------------------------


class TestFromACLintGateConfig:
    """OwlBearSettings.lint_gate_enabled: bool, default=True."""

    def test_config_field_exists(self, default_settings: object) -> None:
        assert hasattr(default_settings, "lint_gate_enabled")

    def test_default_is_true(self, default_settings: object) -> None:
        """default=True because this is safety infrastructure, not feature flag."""
        assert default_settings.lint_gate_enabled is True  # type: ignore[attr-defined]

    def test_can_disable_via_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import os

        for var in [k for k in os.environ if k.startswith("OWLBEAR_")]:
            monkeypatch.delenv(var, raising=False)
        monkeypatch.setenv("OWLBEAR_LINT_GATE_ENABLED", "false")
        from owlbear.config import OwlBearSettings

        settings = OwlBearSettings()
        assert settings.lint_gate_enabled is False


# ---------------------------------------------------------------------------
# AC 6 + AC 3 wiring: run_daemon passes lint_gate_enabled + workspace to poll_loop
# ---------------------------------------------------------------------------


class _MockChannel:
    """Minimal ChannelPlugin for run_daemon tests."""

    def __init__(self) -> None:
        self.sent: list[str] = []

    @property
    def name(self) -> str:
        return "mock"

    async def send(self, message: str) -> None:
        self.sent.append(message)

    async def receive(self, *, prompt: str | None = None) -> str | None:  # noqa: ARG002
        return None


class TestFromACRunDaemonLintGateWiring:
    """run_daemon() passes lint_gate_enabled=settings.lint_gate_enabled and
    workspace=Path.cwd() to poll_loop when autonomous mode is active."""

    @pytest.mark.asyncio
    async def test_run_daemon_passes_lint_gate_enabled_to_poll_loop(self, tmp_path: Path) -> None:
        """AC: In run_daemon(), pass lint_gate_enabled from settings to poll_loop."""
        captured_kwargs: dict[str, object] = {}

        async def fake_poll_loop(**kwargs: object) -> None:
            captured_kwargs.update(kwargs)
            shutdown = kwargs["shutdown_event"]
            shutdown.set()  # type: ignore[union-attr]

        async def fake_channel_loop(
            shutdown_event: asyncio.Event, *_a: object, **_kw: object
        ) -> None:
            await shutdown_event.wait()

        channel = _MockChannel()
        mock_agent = AsyncMock()
        mock_agent.hooks = AsyncMock()
        mock_agent.session = MagicMock()
        mock_agent.session.path = Path("/fake/session")
        mock_agent.session.load.return_value = []

        settings = MagicMock()
        settings.autonomous_mode = True
        settings.heartbeat_enabled = False
        settings.lint_gate_enabled = True  # <-- the value we expect forwarded

        with (
            patch("owlbear.daemon.poll_loop", side_effect=fake_poll_loop),
            patch("owlbear.daemon.channel_loop", side_effect=fake_channel_loop),
            patch("owlbear.memory.wip.WipStore", return_value=MagicMock()),
        ):
            from owlbear.daemon import run_daemon

            await (
                run_daemon(
                    channel=channel,
                    agent=mock_agent,
                    config_dir=tmp_path,
                    settings=settings,
                    kanban_toolset=AsyncMock(),
                    agent_registry=MagicMock(),
                )
            )

        assert captured_kwargs.get("lint_gate_enabled") is True

    @pytest.mark.asyncio
    async def test_run_daemon_passes_workspace_as_path_cwd(self, tmp_path: Path) -> None:
        """AC: In run_daemon(), pass workspace=Path.cwd() (the daemon's launch
        directory) when constructing the poll_loop call."""
        captured_kwargs: dict[str, object] = {}

        async def fake_poll_loop(**kwargs: object) -> None:
            captured_kwargs.update(kwargs)
            shutdown = kwargs["shutdown_event"]
            shutdown.set()  # type: ignore[union-attr]

        async def fake_channel_loop(
            shutdown_event: asyncio.Event, *_a: object, **_kw: object
        ) -> None:
            await shutdown_event.wait()

        channel = _MockChannel()
        mock_agent = AsyncMock()
        mock_agent.hooks = AsyncMock()
        mock_agent.session = MagicMock()
        mock_agent.session.path = Path("/fake/session")
        mock_agent.session.load.return_value = []

        settings = MagicMock()
        settings.autonomous_mode = True
        settings.heartbeat_enabled = False
        settings.lint_gate_enabled = False

        with (
            patch("owlbear.daemon.poll_loop", side_effect=fake_poll_loop),
            patch("owlbear.daemon.channel_loop", side_effect=fake_channel_loop),
            patch("owlbear.memory.wip.WipStore", return_value=MagicMock()),
        ):
            from owlbear.daemon import run_daemon

            await (
                run_daemon(
                    channel=channel,
                    agent=mock_agent,
                    config_dir=tmp_path,
                    settings=settings,
                    kanban_toolset=AsyncMock(),
                    agent_registry=MagicMock(),
                )
            )

        # workspace should be Path.cwd() — a real Path, not None
        assert captured_kwargs.get("workspace") is not None
        assert isinstance(captured_kwargs["workspace"], Path)
        assert captured_kwargs["workspace"] == Path.cwd()

    @pytest.mark.asyncio
    async def test_run_daemon_forwards_disabled_lint_gate(self, tmp_path: Path) -> None:
        """When settings.lint_gate_enabled is False, poll_loop gets False."""
        captured_kwargs: dict[str, object] = {}

        async def fake_poll_loop(**kwargs: object) -> None:
            captured_kwargs.update(kwargs)
            shutdown = kwargs["shutdown_event"]
            shutdown.set()  # type: ignore[union-attr]

        async def fake_channel_loop(
            shutdown_event: asyncio.Event, *_a: object, **_kw: object
        ) -> None:
            await shutdown_event.wait()

        channel = _MockChannel()
        mock_agent = AsyncMock()
        mock_agent.hooks = AsyncMock()
        mock_agent.session = MagicMock()
        mock_agent.session.path = Path("/fake/session")
        mock_agent.session.load.return_value = []

        settings = MagicMock()
        settings.autonomous_mode = True
        settings.heartbeat_enabled = False
        settings.lint_gate_enabled = False  # <-- disabled

        with (
            patch("owlbear.daemon.poll_loop", side_effect=fake_poll_loop),
            patch("owlbear.daemon.channel_loop", side_effect=fake_channel_loop),
            patch("owlbear.memory.wip.WipStore", return_value=MagicMock()),
        ):
            from owlbear.daemon import run_daemon

            await (
                run_daemon(
                    channel=channel,
                    agent=mock_agent,
                    config_dir=tmp_path,
                    settings=settings,
                    kanban_toolset=AsyncMock(),
                    agent_registry=MagicMock(),
                )
            )

        assert captured_kwargs.get("lint_gate_enabled") is False


# ---------------------------------------------------------------------------
# AC 3 wiring: poll_tick threads lint_gate_enabled + workspace to reconcile_tasks
# ---------------------------------------------------------------------------


class TestFromACPollTickLintGateWiring:
    """poll_tick() threads lint_gate_enabled and workspace through to
    reconcile_tasks(), following the existing parameter-threading pattern."""

    @pytest.mark.asyncio
    async def test_poll_tick_passes_lint_gate_enabled_to_reconcile(self) -> None:
        from owlbear.daemon import OrchestratorState, poll_tick

        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_kanban.kanban_list.return_value = "[]"

        with patch("owlbear.daemon.reconcile_tasks", new_callable=AsyncMock) as mock_recon:

            async def go() -> None:
                await poll_tick(
                    state=state,
                    kanban=mock_kanban,
                    agent_registry=MagicMock(),
                    max_concurrent=5,
                    shutdown_event=asyncio.Event(),
                    lint_gate_enabled=True,
                    workspace=Path("/my/workspace"),
                )

            await (go())

        mock_recon.assert_called_once()
        call_kwargs = mock_recon.call_args.kwargs
        assert call_kwargs["lint_gate_enabled"] is True
        assert call_kwargs["workspace"] == Path("/my/workspace")

    @pytest.mark.asyncio
    async def test_poll_tick_defaults_skip_lint_gate(self) -> None:
        from owlbear.daemon import OrchestratorState, poll_tick

        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_kanban.kanban_list.return_value = "[]"

        with patch("owlbear.daemon.reconcile_tasks", new_callable=AsyncMock) as mock_recon:

            async def go() -> None:
                await poll_tick(
                    state=state,
                    kanban=mock_kanban,
                    agent_registry=MagicMock(),
                    max_concurrent=5,
                    shutdown_event=asyncio.Event(),
                )

            await (go())

        mock_recon.assert_called_once()
        call_kwargs = mock_recon.call_args.kwargs
        assert call_kwargs["lint_gate_enabled"] is False
        assert call_kwargs["workspace"] is None
