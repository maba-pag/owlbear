"""Approval-gate policy models — tool-level approval rules.

Provides :class:`ApprovalRule`, :class:`ApprovalPolicy`, and
:class:`ApprovalSession` for gating destructive tool calls behind
explicit user confirmation.

``ApprovalPolicy`` is a Pydantic model loaded from configuration.
``ApprovalSession`` tracks per-session pre-grants so users can approve
a tool once and skip future prompts during the same turn.
"""

from __future__ import annotations

import re
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
        return any(
            isinstance(v, str) and compiled.search(v) is not None
            for v in args.values()
        )


class ApprovalSession:
    """Per-session state for pre-granted tool approvals.

    Allows users to approve a tool once (e.g. "approve all git_push this
    session") and skip future prompts for the remainder of the turn.
    """

    def __init__(self) -> None:
        self._pre_grants: set[str] = set()

    def is_pre_granted(self, tool_name: str) -> bool:
        """Return ``True`` if *tool_name* has been pre-granted."""
        return tool_name in self._pre_grants

    def grant(self, tool_name: str) -> None:
        """Pre-grant *tool_name* for the remainder of this session."""
        self._pre_grants.add(tool_name)

    def clear(self) -> None:
        """Remove all pre-grants."""
        self._pre_grants.clear()
