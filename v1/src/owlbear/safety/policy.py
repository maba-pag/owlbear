"""Approval-gate policy models — tool-level approval rules.

Provides :class:`ApprovalRule`, :class:`ApprovalPolicy`,
:class:`GrantRecord`, and :class:`ApprovalSession` for gating
destructive tool calls behind explicit user confirmation.

``ApprovalPolicy`` is a Pydantic model loaded from configuration.
``ApprovalSession`` tracks per-session pre-grants so users can approve
a tool once and skip future prompts during the same turn.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from time import monotonic
from typing import Any

from pydantic import BaseModel, Field


class ApprovalRule(BaseModel):
    """A single approval rule matching a tool name and optional arg pattern.

    Attributes:
        tool_name: Exact tool name to match, or ``"*"`` for wildcard.
        arg_pattern: Optional regex pattern matched against all string-valued
            tool arguments.  ``None`` means the tool name alone triggers
            approval.
    """

    tool_name: str
    arg_pattern: str | None = None


class ApprovalPolicy(BaseModel):
    """Configurable policy defining which tool calls require user approval.

    Attributes:
        rules: Ordered list of :class:`ApprovalRule` objects.  An empty list
            means no tool ever requires approval.
        default_timeout: Seconds to wait for user response before auto-denying.
    """

    rules: list[ApprovalRule] = Field(default_factory=list)
    default_timeout: float = 120.0
    default_grant_ttl: float = 300.0
    default_max_uses: int | None = 10

    def requires_approval(self, tool_name: str, args: dict[str, Any]) -> bool:
        """Return ``True`` if *tool_name* + *args* match any rule.

        Matching logic:

        1. A rule with ``tool_name="*"`` matches every tool.
        2. Otherwise, the rule's ``tool_name`` must equal *tool_name* exactly.
        3. If a matched rule has ``arg_pattern``, the pattern is searched
           (via :func:`re.search`) against every *string* value in *args*.
           The rule matches only if at least one arg value contains the
           pattern.
        4. If a matched rule has no ``arg_pattern``, the tool name alone
           is sufficient.
        """
        for rule in self.rules:
            if not self._tool_matches(rule, tool_name):
                continue
            if rule.arg_pattern is None:
                return True
            if self._args_match(rule.arg_pattern, args):
                return True
        return False

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _tool_matches(rule: ApprovalRule, tool_name: str) -> bool:
        """Check if *rule* matches *tool_name* (exact or wildcard)."""
        return rule.tool_name in ("*", tool_name)

    @staticmethod
    def _args_match(pattern: str, args: dict[str, Any]) -> bool:
        """Return ``True`` if any string arg value matches *pattern*."""
        compiled = re.compile(pattern)
        return any(isinstance(v, str) and compiled.search(v) is not None for v in args.values())


@dataclass
class GrantRecord:
    """A single scoped grant with optional expiry, usage limit, and arg filter."""

    tool_name: str
    granted_at: float
    remaining_uses: int | None = None
    ttl: float | None = None
    arg_pattern: str | None = None


class ApprovalSession:
    """Per-session state for pre-granted tool approvals.

    Allows users to approve a tool once (e.g. "approve all git_push this
    session") and skip future prompts for the remainder of the turn.

    Grants may be scoped with TTL, max-uses, and arg-pattern constraints.
    """

    def __init__(self, policy: ApprovalPolicy | None = None) -> None:
        self._grants: dict[str, GrantRecord] = {}
        self._policy = policy

    def is_pre_granted(
        self,
        tool_name: str,
        *,
        args: dict[str, Any] | None = None,
    ) -> bool:
        """Return ``True`` if *tool_name* has a valid grant.

        Checks TTL expiry, remaining uses, and arg-pattern match.
        Expired or exhausted grants are removed automatically.
        """
        grant = self._grants.get(tool_name)
        if grant is None:
            return False

        # TTL check
        if grant.ttl is not None and (monotonic() - grant.granted_at) > grant.ttl:
            del self._grants[tool_name]
            return False

        # Remaining-uses check
        if grant.remaining_uses is not None and grant.remaining_uses <= 0:
            del self._grants[tool_name]
            return False

        # Arg-pattern check
        if grant.arg_pattern is not None and args is not None:
            compiled = re.compile(grant.arg_pattern)
            if not any(
                isinstance(v, str) and compiled.search(v) is not None for v in args.values()
            ):
                return False

        # Decrement remaining uses
        if grant.remaining_uses is not None:
            grant.remaining_uses -= 1
            if grant.remaining_uses <= 0:
                del self._grants[tool_name]

        return True

    def grant(
        self,
        tool_name: str,
        *,
        max_uses: int | None = None,
        ttl: float | None = None,
        arg_pattern: str | None = None,
    ) -> None:
        """Pre-grant *tool_name* with optional scope constraints.

        When called with no keyword arguments and a policy is set, the
        policy's ``default_grant_ttl`` and ``default_max_uses`` are applied.
        """
        effective_ttl = ttl
        effective_uses = max_uses

        # Apply policy defaults only when caller provided no explicit kwargs
        if self._policy is not None and ttl is None and max_uses is None and arg_pattern is None:
            effective_ttl = self._policy.default_grant_ttl
            effective_uses = self._policy.default_max_uses

        self._grants[tool_name] = GrantRecord(
            tool_name=tool_name,
            granted_at=monotonic(),
            remaining_uses=effective_uses,
            ttl=effective_ttl,
            arg_pattern=arg_pattern,
        )

    def clear(self) -> None:
        """Remove all grants."""
        self._grants.clear()
