"""Agent registry — scan, instantiate, and cache PydanticAI agents.

Scans a directory of agent definition markdown files, parses their YAML
frontmatter into :class:`AgentDefinition` metadata, and lazily instantiates
PydanticAI :class:`Agent` instances on first access.

Usage::

    from owlbear.core.agent_registry import AgentRegistry
    registry = AgentRegistry(Path(".github/agents"), tool_resolver)
    registry.scan()
    agent = registry.get("builder")
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pydantic_ai import Agent

from owlbear.core.agent_def import AgentDefinition, parse_agent_definition
from owlbear.core.roles import BUILDER_POLICY, VALIDATOR_POLICY, AgentRole, apply_role_policy

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from pydantic_ai.toolsets.abstract import AbstractToolset

    from owlbear.core.deps import OwlBearDeps
    from owlbear.skills.registry import SkillRegistry
    from owlbear.tools.mcp_registry import MCPServerRegistry

__all__ = ["AgentRegistry"]

logger = logging.getLogger(__name__)

_ROLE_POLICIES = {
    AgentRole.BUILDER: BUILDER_POLICY,
    AgentRole.VALIDATOR: VALIDATOR_POLICY,
}


class AgentRegistry:
    """Central registry for agent definitions and lazy agent instantiation.

    Args:
        agents_dir: Directory containing agent ``.md`` definition files.
        tool_resolver: Callback mapping tool name strings to
            :class:`AbstractToolset` instances.
        skill_registry: Optional :class:`SkillRegistry` for skill toolsets.
        default_model: Model name used when an agent definition specifies
            ``model: null``.
        mcp_registry: Optional :class:`MCPServerRegistry` for resolving
            ``mcp:<name>`` tool references.
    """

    def __init__(
        self,
        agents_dir: Path,
        tool_resolver: Callable[[str], AbstractToolset],
        skill_registry: SkillRegistry | None = None,
        default_model: str = "gpt-4o",
        mcp_registry: MCPServerRegistry | None = None,
    ) -> None:
        self._agents_dir = agents_dir
        self._tool_resolver = tool_resolver
        self._skill_registry = skill_registry
        self._default_model = default_model
        self._mcp_registry = mcp_registry
        self._definitions: dict[str, AgentDefinition] = {}
        self._cache: dict[str, Agent[OwlBearDeps, str]] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def scan(self) -> None:
        """Parse all ``.md`` files in *agents_dir*, storing metadata.

        Invalid files are logged as warnings and skipped — this method
        never raises.
        """
        self._definitions.clear()
        self._cache.clear()

        if not self._agents_dir.is_dir():
            logger.debug("Agents directory does not exist: %s", self._agents_dir)
            return

        for md_path in sorted(self._agents_dir.glob("*.md")):
            try:
                defn = parse_agent_definition(md_path)
            except (ValueError, TypeError, OSError) as exc:
                logger.warning("Skipping unparseable agent file %s: %s", md_path, exc)
                continue
            self._definitions[defn.name] = defn
            logger.debug("Registered agent definition: %s", defn.name)

    def get(self, name: str) -> Agent[OwlBearDeps, str]:
        """Return a PydanticAI Agent for *name*, instantiating on first call.

        Args:
            name: Agent name as declared in the definition's ``name`` field.

        Returns:
            Cached :class:`Agent` instance.

        Raises:
            KeyError: If *name* is not a registered agent. The error
                message includes the list of available agent names.
        """
        if name in self._cache:
            return self._cache[name]

        defn = self._definitions.get(name)
        if defn is None:
            available = ", ".join(sorted(self._definitions))
            msg = f"Agent '{name}' not found. Available: {available}"
            raise KeyError(msg)

        agent = self._build_agent(defn)
        self._cache[name] = agent
        return agent

    def list_agents(self) -> list[AgentDefinition]:
        """Return all scanned agent definitions."""
        return list(self._definitions.values())

    @property
    def definitions(self) -> dict[str, AgentDefinition]:
        """Read-only copy of registered agent definitions."""
        return dict(self._definitions)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    _MCP_PREFIX = "mcp:"

    def _resolve_tool(self, tool_name: str) -> AbstractToolset:
        """Resolve a tool name to an :class:`AbstractToolset`.

        Names starting with ``mcp:`` are routed to the MCP server
        registry; all others are forwarded to the standard tool resolver.

        Args:
            tool_name: Tool identifier, optionally prefixed with ``mcp:``.

        Returns:
            An :class:`AbstractToolset` instance.

        Raises:
            KeyError: If an ``mcp:`` name is not found in the MCP registry,
                or if no MCP registry is configured.
        """
        if tool_name.startswith(self._MCP_PREFIX):
            server_name = tool_name[len(self._MCP_PREFIX) :]
            if self._mcp_registry is None:
                msg = f"Tool '{tool_name}' uses mcp: prefix but no MCPServerRegistry is configured"
                raise KeyError(msg)
            return self._mcp_registry.get(server_name)
        return self._tool_resolver(tool_name)

    def _build_agent(self, defn: AgentDefinition) -> Agent[OwlBearDeps, str]:
        """Instantiate a PydanticAI Agent from an AgentDefinition."""
        model = defn.model or self._default_model

        # Resolve toolsets from tool names.
        toolsets: list[AbstractToolset] = [
            self._resolve_tool(tool_name) for tool_name in defn.tools
        ]

        # Add skill registry if available and the definition lists skills.
        if self._skill_registry is not None and defn.skills:
            toolsets.append(self._skill_registry)

        agent: Agent[OwlBearDeps, str] = Agent(
            model,
            instructions=defn.system_prompt or None,
            toolsets=toolsets,
        )

        # Apply role policy for non-builder roles.
        role_str = defn.role.lower()
        if role_str != AgentRole.BUILDER:
            policy = _ROLE_POLICIES.get(AgentRole(role_str), BUILDER_POLICY)
            if policy.denied_tools:
                # Filter each toolset through the role policy.
                filtered: list[AbstractToolset] = [apply_role_policy(ts, policy) for ts in toolsets]
                agent = Agent(
                    model,
                    instructions=defn.system_prompt or None,
                    toolsets=filtered,
                )

        return agent
