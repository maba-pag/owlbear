"""GitLocalToolset — FunctionToolset wrapping local git CLI operations.

Provides tools for common git operations (status, diff, add, commit, branch,
log, push) via :func:`asyncio.create_subprocess_exec`.  Destructive
operations (commit, push) emit :attr:`HookEvent.PRE_TOOL_USE` before
executing.

Usage::

    from owlbear.tools.git_local import GitLocalToolset

    toolset = GitLocalToolset(workspace_root=Path("."))
    agent = Agent("model", toolsets=[toolset])
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from pydantic_ai.toolsets import FunctionToolset

from owlbear.core.hooks import HookEvent

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear.core.hooks import HookRegistry

__all__ = ["GitLocalToolset"]

logger = logging.getLogger(__name__)

_CO_AUTHORED_BY = "Co-authored-by: OwlBear <owlbear@noreply>"


class GitLocalToolset(FunctionToolset):
    """FunctionToolset subclass wrapping local git CLI operations.

    Each tool calls ``git`` via :func:`asyncio.create_subprocess_exec`
    with *workspace_root* as the working directory.  Destructive
    operations (commit, push) emit :attr:`HookEvent.PRE_TOOL_USE`
    before executing.

    Args:
        workspace_root: Directory used as ``cwd`` for all git commands.
        hooks: Optional :class:`HookRegistry` for hook emission on
            destructive operations.
    """

    def __init__(
        self,
        workspace_root: Path,
        hooks: HookRegistry | None = None,
    ) -> None:
        super().__init__()
        self._workspace_root = workspace_root
        self._hooks = hooks
        self._register_tools()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _run_git(self, *args: str) -> tuple[str, str, int]:
        """Run ``git <args>`` and return ``(stdout, stderr, returncode)``."""
        proc = await asyncio.create_subprocess_exec(
            "git",
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self._workspace_root,
        )
        stdout_bytes, stderr_bytes = await proc.communicate()
        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")
        return stdout, stderr, proc.returncode or 0

    async def _emit_hook(self, tool_name: str, args: dict[str, object]) -> None:
        """Emit :attr:`HookEvent.PRE_TOOL_USE` if hooks are configured."""
        if self._hooks is not None:
            await self._hooks.emit(
                HookEvent.PRE_TOOL_USE,
                {"tool_name": tool_name, "args": args},
            )

    # ------------------------------------------------------------------
    # Tool registration
    # ------------------------------------------------------------------

    def _register_tools(self) -> None:
        """Register all git tools on this toolset."""
        self.add_function(
            self.git_status,
            name="git_status",
            description="Show working tree status (porcelain format).",
        )
        self.add_function(
            self.git_diff,
            name="git_diff",
            description="Show changes in working tree or staged changes.",
        )
        self.add_function(
            self.git_add,
            name="git_add",
            description="Stage files for commit.",
        )
        self.add_function(
            self.git_commit,
            name="git_commit",
            description="Commit staged changes with a message.",
        )
        self.add_function(
            self.git_branch,
            name="git_branch",
            description="Create a new branch.",
        )
        self.add_function(
            self.git_log,
            name="git_log",
            description="Show commit log (oneline format).",
        )
        self.add_function(
            self.git_push,
            name="git_push",
            description="Push commits to remote.",
        )

    # ------------------------------------------------------------------
    # Tool implementations
    # ------------------------------------------------------------------

    async def git_status(self) -> str:
        """Return ``git status --porcelain`` output."""
        stdout, stderr, rc = await self._run_git("status", "--porcelain")
        if rc != 0:
            return f"error: {stderr.strip()}"
        return stdout

    async def git_diff(self, *, staged: bool = False) -> str:
        """Return diff output, optionally for staged changes.

        Args:
            staged: If ``True``, show ``--cached`` (staged) diff.
        """
        args = ["diff"]
        if staged:
            args.append("--cached")
        stdout, stderr, rc = await self._run_git(*args)
        if rc != 0:
            return f"error: {stderr.strip()}"
        return stdout

    async def git_add(self, *paths: str) -> str:
        """Stage one or more paths.

        Args:
            paths: File paths to stage.  Defaults to ``"."`` when empty.
        """
        targets = paths or (".",)
        stdout, stderr, rc = await self._run_git("add", *targets)
        if rc != 0:
            return f"error: {stderr.strip()}"
        return stdout or "staged"

    async def git_commit(self, message: str) -> str:
        """Commit staged changes with *message*.

        Appends a ``Co-authored-by`` trailer for OwlBear (unless already
        present).  Emits :attr:`HookEvent.PRE_TOOL_USE` before executing.
        """
        if _CO_AUTHORED_BY not in message:
            message = f"{message}\n\n{_CO_AUTHORED_BY}"
        await self._emit_hook("git_commit", {"message": message})
        stdout, stderr, rc = await self._run_git("commit", "-m", message)
        if rc != 0:
            return f"error: {stderr.strip()}"
        return stdout

    async def git_branch(self, name: str) -> str:
        """Create a new branch named *name*."""
        stdout, stderr, rc = await self._run_git("branch", name)
        if rc != 0:
            return f"error: {stderr.strip()}"
        return stdout or f"created branch '{name}'"

    async def git_log(self, n: int = 10) -> str:
        """Return the last *n* commits in oneline format."""
        stdout, stderr, rc = await self._run_git("log", "--oneline", "-n", str(n))
        if rc != 0:
            return f"error: {stderr.strip()}"
        return stdout

    async def git_push(self, remote: str = "origin", branch: str = "main") -> str:
        """Push to *remote*/*branch*.

        Emits :attr:`HookEvent.PRE_TOOL_USE` before executing.
        """
        await self._emit_hook("git_push", {"remote": remote, "branch": branch})
        stdout, stderr, rc = await self._run_git("push", remote, branch)
        if rc != 0:
            return f"error: {stderr.strip()}"
        return stdout or "pushed"
