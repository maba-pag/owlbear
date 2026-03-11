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
    """Declares which tools a given role may or may not use.

    *allowed_tools* — when non-empty, only these tools pass the filter
    (fail-safe allow-list).  An empty frozenset means "no allow-list
    restriction" (backwards-compatible full access).

    *denied_tools* — tools explicitly excluded regardless of the
    allow-list.  Denial always wins over allowance.
    """

    role: AgentRole
    denied_tools: frozenset[str] = frozenset()
    allowed_tools: frozenset[str] = frozenset()


# ── Built-in policies ────────────────────────────────────────────

BUILDER_POLICY = RolePolicy(
    role=AgentRole.BUILDER,
    denied_tools=frozenset(),
)
"""Builder: full access — no tool restrictions."""

VALIDATOR_POLICY = RolePolicy(
    role=AgentRole.VALIDATOR,
    allowed_tools=frozenset(
        {
            # File read
            "read_file",
            "list_directory",
            "search_files",
            # Git read-only
            "git_status",
            "git_diff",
            "git_log",
            # Browser read
            "browser_read_text",
            "browser_screenshot",
            # Knowledge
            "query_knowledge",
            "list_knowledge_sources",
            "list_bookmarks",
            # Web read
            "web_search",
            "web_read",
            # Kanban read
            "kanban_list",
            "kanban_show",
            "kanban_context",
            # Kanban write — validators must append notes and advance status (#741)
            "kanban_create",
            "kanban_edit",
            "kanban_move",
            # GitHub read
            "list_prs",
            "list_issues",
            "get_issue",
            # Project read
            "list_projects",
            "list_sources",
            # Terminal — validators need pytest/ruff, protected by CommandSafetyGuard (#741)
            "run_command",
        }
    ),
)
"""Validator: allow-list model — only explicitly listed tools are available."""


# ── Policy application ───────────────────────────────────────────


def apply_role_policy(
    toolset: AbstractToolset,
    policy: RolePolicy,
) -> AbstractToolset:
    """Return a filtered view of *toolset* respecting *policy*.

    When *allowed_tools* is non-empty, only tools named in that set
    pass.  Tools in *denied_tools* are always excluded.  If both sets
    are empty the original toolset is returned as-is.
    """
    allowed = policy.allowed_tools
    denied = policy.denied_tools

    if not allowed and not denied:
        return toolset

    def _filter(
        _ctx: object,
        tool_def: object,
    ) -> bool:
        name = getattr(tool_def, "name", "")
        if denied and name in denied:
            return False
        return not (allowed and name not in allowed)

    return toolset.filtered(_filter)
