"""Tests for GitLocalToolset — subprocess git operations.

Covers: git_status, git_diff, git_add, git_commit, git_branch, git_log,
git_push, error handling, constructor, hook integration, and
FunctionToolset registration.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from owlbear.core.hooks import HookEvent, HookRegistry
from owlbear.tools.git_local import GitLocalToolset

WORKSPACE = Path("/fake/workspace")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_proc(stdout: str = "", stderr: str = "", returncode: int = 0) -> AsyncMock:
    """Build a mock subprocess with the given outputs and return code."""
    proc = AsyncMock()
    proc.communicate.return_value = (
        stdout.encode("utf-8"),
        stderr.encode("utf-8"),
    )
    proc.returncode = returncode
    return proc


def _patch_exec(proc: AsyncMock):
    """Patch asyncio.create_subprocess_exec to return *proc*."""
    return patch("owlbear.tools.git_local.asyncio.create_subprocess_exec", return_value=proc)


# ---------------------------------------------------------------------------
# Constructor
# ---------------------------------------------------------------------------


class TestConstructor:
    """GitLocalToolset stores workspace_root and hooks."""

    def test_workspace_root_stored(self) -> None:
        ts = GitLocalToolset(workspace_root=WORKSPACE)
        assert ts._workspace_root == WORKSPACE

    def test_hooks_stored_when_provided(self) -> None:
        hooks = HookRegistry()
        ts = GitLocalToolset(workspace_root=WORKSPACE, hooks=hooks)
        assert ts._hooks is hooks

    def test_hooks_default_none(self) -> None:
        ts = GitLocalToolset(workspace_root=WORKSPACE)
        assert ts._hooks is None

    def test_inherits_function_toolset(self) -> None:
        from pydantic_ai.toolsets import FunctionToolset

        ts = GitLocalToolset(workspace_root=WORKSPACE)
        assert isinstance(ts, FunctionToolset)


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------


class TestToolRegistration:
    """All 7 git tools are registered on the FunctionToolset."""

    def test_all_tools_registered(self) -> None:
        ts = GitLocalToolset(workspace_root=WORKSPACE)
        expected = {
            "git_status",
            "git_diff",
            "git_add",
            "git_commit",
            "git_branch",
            "git_log",
            "git_push",
        }
        assert expected == set(ts.tools)

    def test_tool_count(self) -> None:
        ts = GitLocalToolset(workspace_root=WORKSPACE)
        assert len(ts.tools) == 7


# ---------------------------------------------------------------------------
# git_status
# ---------------------------------------------------------------------------


class TestGitStatus:
    """git_status calls git status --porcelain and returns output."""

    @pytest.mark.asyncio
    async def test_porcelain_flag(self) -> None:
        proc = _make_proc(stdout=" M file.py\n?? new.txt\n")
        with _patch_exec(proc) as mock_exec:
            ts = GitLocalToolset(workspace_root=WORKSPACE)
            await ts.git_status()

        mock_exec.assert_called_once()
        args = mock_exec.call_args[0]
        assert args[0] == "git"
        assert "status" in args
        assert "--porcelain" in args

    @pytest.mark.asyncio
    async def test_returns_status_output(self) -> None:
        proc = _make_proc(stdout=" M file.py\n")
        with _patch_exec(proc):
            ts = GitLocalToolset(workspace_root=WORKSPACE)
            result = await ts.git_status()

        assert " M file.py" in result

    @pytest.mark.asyncio
    async def test_cwd_is_workspace_root(self) -> None:
        proc = _make_proc()
        with _patch_exec(proc) as mock_exec:
            ts = GitLocalToolset(workspace_root=WORKSPACE)
            await ts.git_status()

        _, kwargs = mock_exec.call_args
        assert kwargs["cwd"] == WORKSPACE

    @pytest.mark.asyncio
    async def test_empty_status(self) -> None:
        proc = _make_proc(stdout="")
        with _patch_exec(proc):
            ts = GitLocalToolset(workspace_root=WORKSPACE)
            result = await ts.git_status()

        assert result == ""


# ---------------------------------------------------------------------------
# git_diff
# ---------------------------------------------------------------------------


class TestGitDiff:
    """git_diff returns diff text for staged and unstaged changes."""

    @pytest.mark.asyncio
    async def test_unstaged_diff(self) -> None:
        diff_text = "diff --git a/file.py b/file.py\n-old\n+new\n"
        proc = _make_proc(stdout=diff_text)
        with _patch_exec(proc) as mock_exec:
            ts = GitLocalToolset(workspace_root=WORKSPACE)
            result = await ts.git_diff()

        args = mock_exec.call_args[0]
        assert "diff" in args
        assert "--cached" not in args
        assert result == diff_text

    @pytest.mark.asyncio
    async def test_staged_diff(self) -> None:
        diff_text = "diff --git a/staged.py b/staged.py\n+added\n"
        proc = _make_proc(stdout=diff_text)
        with _patch_exec(proc) as mock_exec:
            ts = GitLocalToolset(workspace_root=WORKSPACE)
            result = await ts.git_diff(staged=True)

        args = mock_exec.call_args[0]
        assert "--cached" in args
        assert result == diff_text


# ---------------------------------------------------------------------------
# git_add
# ---------------------------------------------------------------------------


class TestGitAdd:
    """git_add calls git add with correct path arguments."""

    @pytest.mark.asyncio
    async def test_add_specific_files(self) -> None:
        proc = _make_proc()
        with _patch_exec(proc) as mock_exec:
            ts = GitLocalToolset(workspace_root=WORKSPACE)
            await ts.git_add("file1.py", "file2.py")

        args = mock_exec.call_args[0]
        assert args[0] == "git"
        assert "add" in args
        assert "file1.py" in args
        assert "file2.py" in args

    @pytest.mark.asyncio
    async def test_add_default_dot(self) -> None:
        proc = _make_proc()
        with _patch_exec(proc) as mock_exec:
            ts = GitLocalToolset(workspace_root=WORKSPACE)
            await ts.git_add()

        args = mock_exec.call_args[0]
        assert "." in args

    @pytest.mark.asyncio
    async def test_add_returns_staged(self) -> None:
        proc = _make_proc(stdout="")
        with _patch_exec(proc):
            ts = GitLocalToolset(workspace_root=WORKSPACE)
            result = await ts.git_add("file.py")

        assert result == "staged"


# ---------------------------------------------------------------------------
# git_commit
# ---------------------------------------------------------------------------


class TestGitCommit:
    """git_commit emits PRE_TOOL_USE hook and calls git commit -m."""

    @pytest.mark.asyncio
    async def test_commit_message_passed(self) -> None:
        proc = _make_proc(stdout="[main abc1234] fix bug\n")
        with _patch_exec(proc) as mock_exec:
            ts = GitLocalToolset(workspace_root=WORKSPACE)
            result = await ts.git_commit("fix bug")

        args = mock_exec.call_args[0]
        assert "commit" in args
        assert "-m" in args
        msg_idx = args.index("-m") + 1
        assert args[msg_idx].startswith("fix bug")
        assert "abc1234" in result

    @pytest.mark.asyncio
    async def test_pre_tool_use_emitted(self) -> None:
        hooks = HookRegistry()
        captured: list[dict] = []
        hooks.register(HookEvent.PRE_TOOL_USE, captured.append)

        proc = _make_proc(stdout="committed\n")
        with _patch_exec(proc):
            ts = GitLocalToolset(workspace_root=WORKSPACE, hooks=hooks)
            await ts.git_commit("test commit")

        assert len(captured) == 1
        assert captured[0]["tool_name"] == "git_commit"
        assert captured[0]["args"]["message"].startswith("test commit")

    @pytest.mark.asyncio
    async def test_hook_emitted_before_subprocess(self) -> None:
        """PRE_TOOL_USE must be emitted BEFORE the subprocess call."""
        call_order: list[str] = []

        hooks = HookRegistry()
        hooks.register(HookEvent.PRE_TOOL_USE, lambda _: call_order.append("hook"))

        proc = _make_proc(stdout="committed\n")

        async def tracking_exec(*_args: object, **_kwargs: object) -> AsyncMock:
            call_order.append("subprocess")
            return proc

        with patch(
            "owlbear.tools.git_local.asyncio.create_subprocess_exec",
            side_effect=tracking_exec,
        ):
            ts = GitLocalToolset(workspace_root=WORKSPACE, hooks=hooks)
            await ts.git_commit("ordered commit")

        assert call_order == ["hook", "subprocess"]

    @pytest.mark.asyncio
    async def test_no_hooks_no_error(self) -> None:
        proc = _make_proc(stdout="committed\n")
        with _patch_exec(proc):
            ts = GitLocalToolset(workspace_root=WORKSPACE, hooks=None)
            result = await ts.git_commit("quiet commit")

        assert "committed" in result


# ---------------------------------------------------------------------------
# Co-authored-by trailer
# ---------------------------------------------------------------------------


class TestCoAuthoredByTrailer:
    """git_commit appends a Co-authored-by trailer for OwlBear."""

    @pytest.mark.asyncio
    async def test_trailer_appended_to_commit_message(self) -> None:
        """The trailer is appended to the message passed to git."""
        proc = _make_proc(stdout="[main abc1234] feat: add feature\n")
        with _patch_exec(proc) as mock_exec:
            ts = GitLocalToolset(workspace_root=WORKSPACE)
            await ts.git_commit("feat: add feature")

        args = mock_exec.call_args[0]
        msg_idx = args.index("-m") + 1
        actual_msg = args[msg_idx]
        assert actual_msg.endswith("\n\nCo-authored-by: OwlBear <owlbear@noreply>")
        assert actual_msg.startswith("feat: add feature")

    @pytest.mark.asyncio
    async def test_trailer_not_duplicated_if_already_present(self) -> None:
        """If the message already contains the trailer, don't add it again."""
        original = "fix: typo\n\nCo-authored-by: OwlBear <owlbear@noreply>"
        proc = _make_proc(stdout="[main abc1234] fix: typo\n")
        with _patch_exec(proc) as mock_exec:
            ts = GitLocalToolset(workspace_root=WORKSPACE)
            await ts.git_commit(original)

        args = mock_exec.call_args[0]
        msg_idx = args.index("-m") + 1
        actual_msg = args[msg_idx]
        # Trailer should appear exactly once
        assert actual_msg.count("Co-authored-by: OwlBear <owlbear@noreply>") == 1

    @pytest.mark.asyncio
    async def test_trailer_matches_github_format(self) -> None:
        """Exact format follows GitHub's recognized Co-authored-by pattern."""
        proc = _make_proc(stdout="committed\n")
        with _patch_exec(proc) as mock_exec:
            ts = GitLocalToolset(workspace_root=WORKSPACE)
            await ts.git_commit("chore: cleanup")

        args = mock_exec.call_args[0]
        msg_idx = args.index("-m") + 1
        actual_msg = args[msg_idx]
        # GitHub pattern: "Co-authored-by: NAME <EMAIL>"
        assert "Co-authored-by: OwlBear <owlbear@noreply>" in actual_msg
        # Must be separated from body by blank line (two newlines)
        assert "\n\nCo-authored-by:" in actual_msg


# ---------------------------------------------------------------------------
# git_branch
# ---------------------------------------------------------------------------


class TestGitBranch:
    """git_branch creates a new branch via subprocess."""

    @pytest.mark.asyncio
    async def test_create_branch(self) -> None:
        proc = _make_proc(stdout="")
        with _patch_exec(proc) as mock_exec:
            ts = GitLocalToolset(workspace_root=WORKSPACE)
            result = await ts.git_branch("feature-x")

        args = mock_exec.call_args[0]
        assert "branch" in args
        assert "feature-x" in args
        assert "feature-x" in result

    @pytest.mark.asyncio
    async def test_branch_error(self) -> None:
        proc = _make_proc(stderr="fatal: branch already exists", returncode=128)
        with _patch_exec(proc):
            ts = GitLocalToolset(workspace_root=WORKSPACE)
            result = await ts.git_branch("existing")

        assert "error:" in result
        assert "already exists" in result


# ---------------------------------------------------------------------------
# git_log
# ---------------------------------------------------------------------------


class TestGitLog:
    """git_log calls git log --oneline -n {count}."""

    @pytest.mark.asyncio
    async def test_default_count(self) -> None:
        log_output = "abc1234 first commit\ndef5678 second commit\n"
        proc = _make_proc(stdout=log_output)
        with _patch_exec(proc) as mock_exec:
            ts = GitLocalToolset(workspace_root=WORKSPACE)
            result = await ts.git_log()

        args = mock_exec.call_args[0]
        assert "--oneline" in args
        assert "-n" in args
        # Default n=10
        n_idx = args.index("-n")
        assert args[n_idx + 1] == "10"
        assert result == log_output

    @pytest.mark.asyncio
    async def test_custom_count(self) -> None:
        proc = _make_proc(stdout="abc1234 only one\n")
        with _patch_exec(proc) as mock_exec:
            ts = GitLocalToolset(workspace_root=WORKSPACE)
            await ts.git_log(n=5)

        args = mock_exec.call_args[0]
        n_idx = args.index("-n")
        assert args[n_idx + 1] == "5"


# ---------------------------------------------------------------------------
# git_push
# ---------------------------------------------------------------------------


class TestGitPush:
    """git_push emits PRE_TOOL_USE hook and calls git push."""

    @pytest.mark.asyncio
    async def test_push_default_args(self) -> None:
        proc = _make_proc(stdout="")
        with _patch_exec(proc) as mock_exec:
            ts = GitLocalToolset(workspace_root=WORKSPACE)
            result = await ts.git_push()

        args = mock_exec.call_args[0]
        assert "push" in args
        assert "origin" in args
        assert "main" in args
        assert result == "pushed"

    @pytest.mark.asyncio
    async def test_push_custom_remote_branch(self) -> None:
        proc = _make_proc(stdout="")
        with _patch_exec(proc) as mock_exec:
            ts = GitLocalToolset(workspace_root=WORKSPACE)
            await ts.git_push(remote="upstream", branch="develop")

        args = mock_exec.call_args[0]
        assert "upstream" in args
        assert "develop" in args

    @pytest.mark.asyncio
    async def test_pre_tool_use_emitted(self) -> None:
        hooks = HookRegistry()
        captured: list[dict] = []
        hooks.register(HookEvent.PRE_TOOL_USE, captured.append)

        proc = _make_proc(stdout="")
        with _patch_exec(proc):
            ts = GitLocalToolset(workspace_root=WORKSPACE, hooks=hooks)
            await ts.git_push()

        assert len(captured) == 1
        assert captured[0]["tool_name"] == "git_push"
        assert captured[0]["args"]["remote"] == "origin"
        assert captured[0]["args"]["branch"] == "main"

    @pytest.mark.asyncio
    async def test_hook_emitted_before_subprocess(self) -> None:
        """PRE_TOOL_USE must be emitted BEFORE the subprocess call."""
        call_order: list[str] = []

        hooks = HookRegistry()
        hooks.register(HookEvent.PRE_TOOL_USE, lambda _: call_order.append("hook"))

        proc = _make_proc(stdout="")

        async def tracking_exec(*_args: object, **_kwargs: object) -> AsyncMock:
            call_order.append("subprocess")
            return proc

        with patch(
            "owlbear.tools.git_local.asyncio.create_subprocess_exec",
            side_effect=tracking_exec,
        ):
            ts = GitLocalToolset(workspace_root=WORKSPACE, hooks=hooks)
            await ts.git_push()

        assert call_order == ["hook", "subprocess"]


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """Non-zero exit codes return error strings, not exceptions."""

    @pytest.mark.asyncio
    async def test_status_error(self) -> None:
        proc = _make_proc(stderr="fatal: not a git repo", returncode=128)
        with _patch_exec(proc):
            ts = GitLocalToolset(workspace_root=WORKSPACE)
            result = await ts.git_status()

        assert isinstance(result, str)
        assert "error:" in result
        assert "not a git repo" in result

    @pytest.mark.asyncio
    async def test_diff_error(self) -> None:
        proc = _make_proc(stderr="fatal: bad revision", returncode=128)
        with _patch_exec(proc):
            ts = GitLocalToolset(workspace_root=WORKSPACE)
            result = await ts.git_diff()

        assert "error:" in result

    @pytest.mark.asyncio
    async def test_add_error(self) -> None:
        proc = _make_proc(stderr="fatal: pathspec 'x' did not match", returncode=128)
        with _patch_exec(proc):
            ts = GitLocalToolset(workspace_root=WORKSPACE)
            result = await ts.git_add("x")

        assert "error:" in result

    @pytest.mark.asyncio
    async def test_commit_error(self) -> None:
        proc = _make_proc(stderr="nothing to commit", returncode=1)
        with _patch_exec(proc):
            ts = GitLocalToolset(workspace_root=WORKSPACE)
            result = await ts.git_commit("msg")

        assert "error:" in result
        assert "nothing to commit" in result

    @pytest.mark.asyncio
    async def test_log_error(self) -> None:
        proc = _make_proc(stderr="fatal: bad default revision", returncode=128)
        with _patch_exec(proc):
            ts = GitLocalToolset(workspace_root=WORKSPACE)
            result = await ts.git_log()

        assert "error:" in result

    @pytest.mark.asyncio
    async def test_push_error(self) -> None:
        proc = _make_proc(stderr="fatal: no upstream", returncode=128)
        with _patch_exec(proc):
            ts = GitLocalToolset(workspace_root=WORKSPACE)
            result = await ts.git_push()

        assert "error:" in result
        assert "no upstream" in result

    @pytest.mark.asyncio
    async def test_error_returns_string_not_exception(self) -> None:
        """Verify that errors don't raise — they return a string."""
        proc = _make_proc(stderr="something failed", returncode=1)
        with _patch_exec(proc):
            ts = GitLocalToolset(workspace_root=WORKSPACE)
            # Should NOT raise
            result = await ts.git_status()

        assert isinstance(result, str)
        assert "error:" in result
