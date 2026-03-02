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

from pydantic_ai import RunContext  # noqa: TC002
from pydantic_ai.toolsets import FunctionToolset

from owlbear.core.deps import OwlBearDeps  # noqa: TC001
from owlbear.core.errors import ErrorCategory, ToolError, classify_error

__all__ = ["MAX_DELEGATION_DEPTH", "DelegationToolset"]

logger = logging.getLogger(__name__)

MAX_DELEGATION_DEPTH: int = 5
"""Maximum nesting depth for agent-to-agent delegation."""


class DelegationToolset(FunctionToolset):
    """FunctionToolset subclass that registers a ``delegate_to_agent`` tool.

    The tool uses :class:`~pydantic_ai.RunContext` to access the shared
    :class:`~owlbear.core.deps.OwlBearDeps`, looks up the target agent
    by name, and runs it with incremented delegation depth.
    """

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
        depth = ctx.deps._delegation_depth  # noqa: SLF001
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
            _delegation_depth=depth + 1,
        )

        # -- Run inner agent ----------------------------------------------
        try:
            result = await agent.run(task, deps=inner_deps, usage=ctx.usage)
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
                    message=f"delegation to '{agent_name}' failed: {exc}",
                ).to_dict()
            )

        return result.output
