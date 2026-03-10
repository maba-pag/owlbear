"""Core agent loop, message model, hooks, and configuration."""

from __future__ import annotations

from owlbear.core.agent import OwlBearAgent
from owlbear.core.deps import OwlBearDeps
from owlbear.core.hooks import (
    DaemonStartupData,
    HookEvent,
    HookRegistry,
    OnErrorData,
    OnMessageData,
    PostToolUseData,
    PreToolUseData,
    SessionEndData,
    SessionStartData,
    SubagentCompleteData,
    TaskCompleteData,
)
from owlbear.core.roles import AgentRole, RolePolicy

__all__ = [
    "AgentRole",
    "DaemonStartupData",
    "HookEvent",
    "HookRegistry",
    "OnErrorData",
    "OnMessageData",
    "OwlBearAgent",
    "OwlBearDeps",
    "PostToolUseData",
    "PreToolUseData",
    "RolePolicy",
    "SessionEndData",
    "SessionStartData",
    "SubagentCompleteData",
    "TaskCompleteData",
]
