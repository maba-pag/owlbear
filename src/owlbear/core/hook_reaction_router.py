"""Hook reaction router — event-driven policy executor for OwlBear.

Provides :class:`HookReactionRule` (Pydantic schema) and
:class:`HookReactionRouter` (registration + matching + dispatch).

Design notes
------------
- ``HookReactionRule`` validates event strings as plain strings; resolution to
  :class:`~owlbear.core.hooks.HookEvent` happens at registration time so
  ``config.py`` stays a leaf module with no hook-enum dependency.
- ``HookReactionRouter.register()`` raises ``ValueError`` for unknown event
  strings instead of silently skipping them (fail-fast).
- Executor failures are logged and swallowed per-action so a failing action
  never blocks subsequent actions and never re-emits ``ON_ERROR``.

Part of the hook reaction policy introduced in #955/#965.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, field_validator

if TYPE_CHECKING:
    from owlbear.core.hooks import HookRegistry

logger = logging.getLogger(__name__)

__all__ = ["HookReactionRouter", "HookReactionRule"]

_ALLOWED_ACTIONS: frozenset[str] = frozenset({"notify", "retry", "escalate"})

Executor = Callable[[dict[str, Any]], Any]


class HookReactionRule(BaseModel):
    """Schema for a single hook reaction rule.

    Attributes:
        events:  Non-empty list of event-name strings (e.g. ``"task_complete"``).
        actions: Ordered, non-empty list of action kinds — must be a subset of
                 ``{"notify", "retry", "escalate"}``.
        match:   Optional shallow equality predicate.  Each value must be a
                 scalar (not a ``dict`` or ``list``).  All pairs must match the
                 emitted payload for the rule to fire.
    """

    model_config = ConfigDict(extra="forbid")

    events: list[str]
    actions: list[str]
    match: dict[str, Any] | None = None

    @field_validator("events")
    @classmethod
    def _non_empty_events(cls, v: list[str]) -> list[str]:
        if not v:
            msg = "events must be non-empty"
            raise ValueError(msg)
        return v

    @field_validator("actions")
    @classmethod
    def _valid_actions(cls, v: list[str]) -> list[str]:
        if not v:
            msg = "actions must be non-empty"
            raise ValueError(msg)
        unknown = set(v) - _ALLOWED_ACTIONS
        if unknown:
            msg = (
                f"Unknown action kinds: {sorted(unknown)}. "
                f"Allowed: {sorted(_ALLOWED_ACTIONS)}"
            )
            raise ValueError(msg)
        return v

    @field_validator("match")
    @classmethod
    def _scalar_match_values(cls, v: dict[str, Any] | None) -> dict[str, Any] | None:
        if v is None:
            return v
        for key, val in v.items():
            if isinstance(val, (dict, list)):
                msg = (
                    f"match values must be scalars; "
                    f"key {key!r} has a non-scalar value ({type(val).__name__})"
                )
                raise ValueError(msg)  # noqa: TRY004 — must be ValueError for Pydantic ValidationError wrapping
        return v


class HookReactionRouter:
    """Register configured reaction rules as hook handlers.

    Executors are injected so the router stays decoupled from concrete retry,
    escalation, and notification implementations.

    Args:
        rules:     Ordered list of :class:`HookReactionRule` objects.
        executors: Mapping from action kind to async callable.
    """

    def __init__(
        self,
        rules: list[HookReactionRule],
        executors: dict[str, Executor],
    ) -> None:
        self._rules = rules
        self._executors = executors

    def register(self, hooks: HookRegistry) -> None:
        """Register one handler per (rule, event) pair on *hooks*.

        Raises:
            ValueError: If any event string in a rule is not a valid
                :class:`~owlbear.core.hooks.HookEvent` value.
        """
        from owlbear.core.hooks import HookEvent  # noqa: PLC0415

        for rule in self._rules:
            for event_name in rule.events:
                event = HookEvent(event_name)  # raises ValueError if unknown
                hooks.register(event, self._make_handler(rule))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _make_handler(self, rule: HookReactionRule) -> Callable[[dict[str, Any]], Any]:
        """Return an async handler closure bound to *rule*."""
        executors = self._executors

        async def handler(data: dict[str, Any]) -> None:
            # Evaluate optional match predicate — all pairs must equal payload.
            if rule.match:
                for key, expected in rule.match.items():
                    if not isinstance(data, dict) or data.get(key) != expected:
                        return

            # Dispatch actions in declared order; log and swallow per-action failures
            # so a failing action never blocks subsequent ones and never re-emits ON_ERROR.
            for action in rule.actions:
                executor = executors.get(action)
                if executor is None:
                    continue
                try:
                    result = executor(data)
                    if asyncio.iscoroutine(result):
                        await result
                except Exception:  # noqa: BLE001
                    logger.warning(
                        "Hook reaction executor for action %r failed",
                        action,
                        exc_info=True,
                    )

        return handler
