"""KanbanToolset — FunctionToolset wrapping kanban-md CLI operations.

Provides tools for kanban board management (list, show, create, move, edit,
pick, context) via :func:`asyncio.create_subprocess_exec`.  Mutating
operations (create, move, edit, pick) emit :attr:`HookEvent.PRE_TOOL_USE`
before executing.

Usage::

    from owlbear.tools.kanban import KanbanToolset

    toolset = KanbanToolset(kanban_dir=Path("kanban"))
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

__all__ = ["KanbanToolset"]

logger = logging.getLogger(__name__)


class KanbanToolset(FunctionToolset):
    """FunctionToolset subclass wrapping kanban-md CLI operations.

    Each tool calls ``kanban-md`` via :func:`asyncio.create_subprocess_exec`.
    ``--no-color`` and ``--dir {kanban_dir}`` are appended to every command.
    Mutating operations (create, move, edit, pick) emit
    :attr:`HookEvent.PRE_TOOL_USE` before executing.

    Args:
        kanban_dir: Directory containing kanban tasks (passed as ``--dir``).
        kanban_bin: Path to the kanban-md binary.  When ``None``, defaults
            to ``kanban_dir / 'kanban-md.exe'``.
        hooks: Optional :class:`HookRegistry` for hook emission on
            mutating operations.
    """

    def __init__(
        self,
        kanban_dir: Path,
        kanban_bin: Path | None = None,
        hooks: HookRegistry | None = None,
    ) -> None:
        super().__init__()
        self._kanban_dir = kanban_dir
        self._kanban_bin = kanban_bin if kanban_bin is not None else kanban_dir / "kanban-md.exe"
        self._hooks = hooks
        self._register_tools()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _run_kanban(self, *args: str) -> tuple[str, str, int]:
        """Run ``kanban-md <args> --no-color --dir {kanban_dir}``.

        Returns ``(stdout, stderr, returncode)``.
        """
        full_args = [*args, "--no-color", "--dir", str(self._kanban_dir)]
        proc = await asyncio.create_subprocess_exec(
            str(self._kanban_bin),
            *full_args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
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
        """Register all kanban tools on this toolset."""
        self.add_function(
            self.kanban_list,
            name="kanban_list",
            description="List kanban tasks with optional filters.",
        )
        self.add_function(
            self.kanban_show,
            name="kanban_show",
            description="Show a kanban task by ID (JSON output).",
        )
        self.add_function(
            self.kanban_create,
            name="kanban_create",
            description="Create a new kanban task.",
        )
        self.add_function(
            self.kanban_move,
            name="kanban_move",
            description="Move a kanban task to a new status.",
        )
        self.add_function(
            self.kanban_edit,
            name="kanban_edit",
            description="Edit a kanban task's properties.",
        )
        self.add_function(
            self.kanban_pick,
            name="kanban_pick",
            description="Pick the next task from the board.",
        )
        self.add_function(
            self.kanban_context,
            name="kanban_context",
            description="Show board context summary.",
        )

    # ------------------------------------------------------------------
    # Tool implementations
    # ------------------------------------------------------------------

    async def kanban_list(  # noqa: PLR0913
        self,
        *,
        status: str | None = None,
        tag: str | None = None,
        priority: str | None = None,
        blocked: bool = False,
        not_blocked: bool = False,
        unblocked: bool = False,
    ) -> str:
        """List tasks with optional filters.

        Args:
            status: Filter by status column.
            tag: Filter by tag.
            priority: Filter by priority level.
            blocked: Show only blocked tasks.
            not_blocked: Show only non-blocked tasks.
            unblocked: Show only unblocked tasks.
        """
        args: list[str] = ["list", "--compact"]
        if status is not None:
            args.extend(["--status", status])
        if tag is not None:
            args.extend(["--tag", tag])
        if priority is not None:
            args.extend(["--priority", priority])
        if blocked:
            args.append("--blocked")
        if not_blocked:
            args.append("--not-blocked")
        if unblocked:
            args.append("--unblocked")
        stdout, stderr, rc = await self._run_kanban(*args)
        if rc != 0:
            return f"error: {stderr.strip()}"
        return stdout

    async def kanban_show(self, task_id: str) -> str:
        """Show task details in JSON format.

        Args:
            task_id: The task ID to show.
        """
        stdout, stderr, rc = await self._run_kanban("show", task_id, "--json")
        if rc != 0:
            return f"error: {stderr.strip()}"
        return stdout

    async def kanban_create(
        self,
        title: str,
        *,
        priority: str | None = None,
        tags: str | None = None,
        body: str | None = None,
        depends_on: str | None = None,
    ) -> str:
        """Create a new task.

        Args:
            title: Task title.
            priority: Priority level.
            tags: Comma-separated tags.
            body: Task body / acceptance criteria.
            depends_on: Comma-separated dependency task IDs.
        """
        await self._emit_hook("kanban_create", {"title": title})
        args: list[str] = ["create", title]
        if priority is not None:
            args.extend(["--priority", priority])
        if tags is not None:
            args.extend(["--tags", tags])
        if body is not None:
            args.extend(["--body", body])
        if depends_on is not None:
            args.extend(["--depends-on", depends_on])
        stdout, stderr, rc = await self._run_kanban(*args)
        if rc != 0:
            return f"error: {stderr.strip()}"
        return stdout

    async def kanban_move(self, task_id: str, status: str) -> str:
        """Move a task to a new status.

        Args:
            task_id: The task ID to move.
            status: Target status column.
        """
        await self._emit_hook("kanban_move", {"task_id": task_id, "status": status})
        stdout, stderr, rc = await self._run_kanban("move", task_id, status)
        if rc != 0:
            return f"error: {stderr.strip()}"
        return stdout

    async def kanban_edit(  # noqa: PLR0913
        self,
        task_id: str,
        *,
        body: str | None = None,
        block: str | None = None,
        unblock: bool = False,
        tags: str | None = None,
        priority: str | None = None,
        append_body: str | None = None,
    ) -> str:
        """Edit a task's properties.

        Args:
            task_id: The task ID to edit.
            body: Replace task body.
            block: Set block reason.
            unblock: Remove block status.
            tags: Replace tags (comma-separated).
            priority: Change priority level.
            append_body: Append text to task body.
        """
        await self._emit_hook("kanban_edit", {"task_id": task_id})
        args: list[str] = ["edit", task_id]
        if body is not None:
            args.extend(["--body", body])
        if block is not None:
            args.extend(["--block", block])
        if unblock:
            args.append("--unblock")
        if tags is not None:
            args.extend(["--tags", tags])
        if priority is not None:
            args.extend(["--priority", priority])
        if append_body is not None:
            args.extend(["--append-body", append_body])
        stdout, stderr, rc = await self._run_kanban(*args)
        if rc != 0:
            return f"error: {stderr.strip()}"
        return stdout

    async def kanban_pick(
        self,
        *,
        status: str | None = None,
        claim: str | None = None,
        move: str | None = None,
    ) -> str:
        """Pick the next task from the board.

        Args:
            status: Filter by status before picking.
            claim: Claim the task for an agent/user.
            move: Move the picked task to this status.
        """
        await self._emit_hook("kanban_pick", {})
        args: list[str] = ["pick"]
        if status is not None:
            args.extend(["--status", status])
        if claim is not None:
            args.extend(["--claim", claim])
        if move is not None:
            args.extend(["--move", move])
        stdout, stderr, rc = await self._run_kanban(*args)
        if rc != 0:
            return f"error: {stderr.strip()}"
        return stdout

    async def kanban_context(self) -> str:
        """Show board context summary."""
        stdout, stderr, rc = await self._run_kanban("context")
        if rc != 0:
            return f"error: {stderr.strip()}"
        return stdout
