"""DelegationToolset — orchestrator dispatches subtasks to inner agents.

Provides a ``delegate_to_agent`` tool that looks up a named agent via
:class:`~owlbear.core.agent_registry.AgentRegistry`, creates child
dependencies with incremented delegation depth, and runs the inner
agent on the given task.

Usage::

    from owlbear.core.delegation import DelegationToolset

    toolset = DelegationToolset()
    # Register on an Agent — PydanticAI injects RunContext automatically.
"""

from __future__ import annotations

import dataclasses
import json
import logging
from typing import TYPE_CHECKING

from pydantic_ai import RunContext  # noqa: TC002
from pydantic_ai.toolsets import FunctionToolset

from owlbear.core.deps import OwlBearDeps  # noqa: TC001

if TYPE_CHECKING:
    from typing import ClassVar
from owlbear.core.errors import ErrorCategory, ToolError, classify_error, error_to_user_message

__all__ = [
    "MAX_DELEGATION_DEPTH",
    "DelegationToolset",
    "DispatchContext",
    "format_dispatch_context",
]

logger = logging.getLogger(__name__)

MAX_DELEGATION_DEPTH: int = 5
"""Maximum nesting depth for agent-to-agent delegation."""


@dataclasses.dataclass
class DispatchContext:
    """Runtime context forwarded to child agents during delegation.

    Attributes:
        workspace_root: Absolute path to the active workspace.
        channel_name: Name of the channel that initiated the run.
        task_id: Kanban task ID, if the run is task-scoped.
        task_title: Short title of the task, if available.
        task_status: Current task status, if available.
    """

    workspace_root: str
    channel_name: str
    task_id: str | None = None
    task_title: str | None = None
    task_status: str | None = None


def format_dispatch_context(ctx: DispatchContext) -> tuple[str, dict[str, str]]:
    """Format *ctx* into per-run instructions text and a metadata dict.

    Args:
        ctx: Populated :class:`DispatchContext` for the current run.

    Returns:
        A ``(instructions, metadata)`` pair where *instructions* is a
        human-readable string and *metadata* contains only the fields
        that are present on *ctx*.
    """
    lines = [
        f"Workspace: {ctx.workspace_root}",
        f"Channel: {ctx.channel_name}",
    ]
    metadata: dict[str, str] = {}

    if ctx.task_id is not None:
        lines.append(f"Task ID: {ctx.task_id}")
        metadata["task_id"] = ctx.task_id

    if ctx.task_title is not None:
        lines.append(f"Task: {ctx.task_title}")
        metadata["task_title"] = ctx.task_title

    if ctx.task_status is not None:
        lines.append(f"Status: {ctx.task_status}")
        metadata["task_status"] = ctx.task_status

    return "\n".join(lines), metadata


class DelegationToolset(FunctionToolset):
    """FunctionToolset subclass that registers a ``delegate_to_agent`` tool.

    The tool uses :class:`~pydantic_ai.RunContext` to access the shared
    :class:`~owlbear.core.deps.OwlBearDeps`, looks up the target agent
    by name, and runs it with incremented delegation depth.
    """

    tool_alias: ClassVar[str] = "delegation"

    def __init__(self) -> None:
        super().__init__()
        self._register_tools()

    # ------------------------------------------------------------------
    # Tool registration
    # ------------------------------------------------------------------

    def _register_tools(self) -> None:
        """Register the ``delegate_to_agent`` tool on this toolset."""
        self.add_function(
            self._delegate,
            name="delegate_to_agent",
            description=(
                "Delegate a subtask to another agent by name. "
                "Returns the agent's text output on success, "
                "or a descriptive error string on failure."
            ),
        )

    # ------------------------------------------------------------------
    # Core tool
    # ------------------------------------------------------------------

    async def _delegate(
        self,
        ctx: RunContext[OwlBearDeps],
        agent_name: str,
        task: str,
    ) -> str:
        """Dispatch *task* to the agent named *agent_name*.

        Args:
            ctx: PydanticAI run context (injected automatically).
            agent_name: Name of the target agent in the registry.
            task: Prompt / instruction to send to the inner agent.

        Returns:
            The inner agent's text output, or a descriptive error string
            if delegation fails for any reason.
        """
        # -- Guard: registry must exist -----------------------------------
        registry = ctx.deps.agent_registry
        if registry is None:
            return json.dumps(
                ToolError(
                    error_type=ErrorCategory.PERMANENT,
                    tool_name="delegate_to_agent",
                    message="agent_registry is not configured on deps.",
                ).to_dict()
            )

        # -- Guard: depth limit -------------------------------------------
        depth = ctx.deps.delegation_depth
        if depth >= MAX_DELEGATION_DEPTH:
            return json.dumps(
                ToolError(
                    error_type=ErrorCategory.PERMANENT,
                    tool_name="delegate_to_agent",
                    message=(
                        f"max delegation depth ({MAX_DELEGATION_DEPTH}) "
                        f"exceeded (current depth: {depth})."
                    ),
                ).to_dict()
            )

        # -- Look up agent ------------------------------------------------
        try:
            agent = registry.get(agent_name)
        except KeyError:
            available = ", ".join(sorted(registry.definitions))
            return json.dumps(
                ToolError(
                    error_type=ErrorCategory.TOOL_SEMANTIC,
                    tool_name="delegate_to_agent",
                    message=f"agent '{agent_name}' not found. Available: {available}",
                ).to_dict()
            )

        # -- Build child deps with incremented depth ----------------------
        inner_deps = dataclasses.replace(
            ctx.deps,
            delegation_depth=depth + 1,
        )

        # -- Build per-run kwargs from dispatch context -------------------
        run_kwargs: dict[str, object] = {
            "deps": inner_deps,
            "usage": ctx.usage,
        }
        dc = ctx.deps.dispatch_context
        if dc is not None:
            instructions, metadata = format_dispatch_context(dc)  # type: ignore[arg-type]
            run_kwargs["instructions"] = instructions
            run_kwargs["metadata"] = metadata

        # -- Run inner agent ----------------------------------------------
        try:
            result = await agent.run(task, **run_kwargs)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Delegation to '%s' failed: %s",
                agent_name,
                exc,
                exc_info=True,
            )
            return json.dumps(
                ToolError(
                    error_type=classify_error(exc),
                    tool_name="delegate_to_agent",
                    message=f"delegation to '{agent_name}' failed: {error_to_user_message(exc)}",
                ).to_dict()
            )

        return result.output
