"""Core agent loop, message model, hooks, and configuration."""

from __future__ import annotations

from owlbear.core.agent import OwlBearAgent
from owlbear.core.deps import OwlBearDeps
from owlbear.core.hooks import HookEvent, HookRegistry
from owlbear.core.roles import AgentRole, RolePolicy

__all__ = [
    "AgentRole",
    "HookEvent",
    "HookRegistry",
    "OwlBearAgent",
    "OwlBearDeps",
    "RolePolicy",
]
