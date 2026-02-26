"""Agent role policies — restrict toolsets by role.

Defines :class:`AgentRole` (builder / validator) and
:func:`apply_role_policy` which returns a filtered toolset that respects
the role's denied-tools list.

Usage::

    from owlbear.core.roles import VALIDATOR_POLICY, apply_role_policy

    full = build_full_toolset()
    read_only = apply_role_policy(full, VALIDATOR_POLICY)
    agent = Agent("model", toolsets=[read_only])
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pydantic_ai.toolsets import FunctionToolset
    from pydantic_ai.toolsets.abstract import AbstractToolset

__all__ = [
    "BUILDER_POLICY",
    "VALIDATOR_POLICY",
    "AgentRole",
    "RolePolicy",
    "apply_role_policy",
]


class AgentRole(enum.StrEnum):
    """Named agent roles with distinct tool-access levels."""

    BUILDER = "builder"
    VALIDATOR = "validator"


@dataclass(frozen=True, slots=True)
class RolePolicy:
    """Declares which tools are denied for a given role.

    *denied_tools* lists tool names that must be excluded when
    :func:`apply_role_policy` creates a filtered toolset.  An empty
    set means "allow everything".
    """

    role: AgentRole
    denied_tools: frozenset[str] = frozenset()


# ── Built-in policies ────────────────────────────────────────────

BUILDER_POLICY = RolePolicy(
    role=AgentRole.BUILDER,
    denied_tools=frozenset(),
)
"""Builder: full access — no tool restrictions."""

VALIDATOR_POLICY = RolePolicy(
    role=AgentRole.VALIDATOR,
    denied_tools=frozenset({
        "file_write",
        "file_edit",
        "file_delete",
        "execute_command",
    }),
)
"""Validator: read-only — cannot write, edit, delete, or execute."""


# ── Policy application ───────────────────────────────────────────

def apply_role_policy(
    toolset: FunctionToolset,
    policy: RolePolicy,
) -> AbstractToolset:
    """Return a filtered view of *toolset* respecting *policy*.

    Tools whose names appear in ``policy.denied_tools`` are excluded.
    If *denied_tools* is empty the original toolset is returned as-is.
    """
    if not policy.denied_tools:
        return toolset

    denied = policy.denied_tools

    def _filter(
        _ctx: object,
        tool_def: object,
    ) -> bool:
        return getattr(tool_def, "name", "") not in denied

    return toolset.filtered(_filter)
