"""Bootstrap MCP and agent registry builders."""

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING

from owlbear.core.agent_registry import AgentRegistry
from owlbear.tools.mcp_registry import MCPServerRegistry
from owlbear.tools.protocols import unwrap

from ._types import ComponentStatus

if TYPE_CHECKING:
    from pydantic_ai.models import Model
    from pydantic_ai.toolsets.abstract import AbstractToolset

    from owlbear.config import OwlBearSettings
    from owlbear.skills.registry import SkillRegistry

logger = logging.getLogger(__name__)


def build_mcp_registry(
    settings: OwlBearSettings,
    summary: list[ComponentStatus] | None = None,
) -> MCPServerRegistry | None:
    """Build the MCP server registry, or ``None`` if no servers configured."""
    if not settings.mcp_servers:
        return None

    registry = MCPServerRegistry()
    _pkg = sys.modules[__package__]
    try:
        _pkg.register_default_servers(registry, settings)
        if summary is not None:
            summary.append(ComponentStatus(name="MCPRegistry", loaded=True))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to register MCP default servers", exc_info=True)
        if summary is not None:
            summary.append(
                ComponentStatus(name="MCPRegistry", loaded=False, error=str(exc), level="ERROR")
            )
    return registry


def build_agent_registry(
    settings: OwlBearSettings,
    toolsets: list[AbstractToolset],
    mcp_registry: MCPServerRegistry | None,
    skill_registry: SkillRegistry | None = None,
    model: str | Model | None = None,
) -> AgentRegistry:
    """Build and scan the :class:`AgentRegistry`."""
    # Build a name → toolset resolver from the toolsets list.
    tool_map: dict[str, AbstractToolset] = {}
    _aliases: dict[str, str] = {}
    for ts in toolsets:
        inner = unwrap(ts)
        name = type(inner).__name__
        tool_map[name] = ts
        alias = getattr(inner, "tool_alias", None)
        if alias:
            _aliases[alias] = name

    def _resolve(name: str) -> AbstractToolset:
        if name in tool_map:
            return tool_map[name]
        class_name = _aliases.get(name)
        if class_name and class_name in tool_map:
            return tool_map[class_name]
        msg = f"Unknown tool: {name!r}"
        raise KeyError(msg)

    default_model = model if model is not None else settings.chat_model

    registry = AgentRegistry(
        agents_dir=settings.agents_dir,
        tool_resolver=_resolve,
        skill_registry=skill_registry,
        default_model=default_model,
        mcp_registry=mcp_registry,
    )
    registry.scan()
    return registry
