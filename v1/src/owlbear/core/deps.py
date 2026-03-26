"""Shared dependency container for OwlBear agents.

Passed as ``deps`` to every PydanticAI ``Agent.run()`` call, making hooks
and usage tracking available to tools via ``ctx.deps``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from owlbear.config import RigorProfile
    from owlbear.core.agent_registry import AgentRegistry
    from owlbear.core.delegation import DispatchContext
    from owlbear.core.hooks import HookRegistry
    from owlbear.memory.usage import UsageTracker


@dataclass
class OwlBearDeps:
    """Shared dependencies injected into all OwlBear agents.

    Keep this minimal — only fields that multiple agents need via
    ``RunContext.deps``.  Per-agent state (session, workspace_root)
    belongs on the agent instance, not here.
    """

    hooks: HookRegistry
    tracker: UsageTracker | None = field(default=None)
    agent_registry: AgentRegistry | None = field(default=None)
    delegation_depth: int = field(default=0)
    rigor_profile: RigorProfile | None = field(default=None)
    dispatch_context: DispatchContext | None = field(default=None)
