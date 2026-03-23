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

from owlbear.config import HookReactionRule

if TYPE_CHECKING:
    from owlbear.core.hooks import HookRegistry

logger = logging.getLogger(__name__)

__all__ = ["HookReactionRouter", "HookReactionRule"]

Executor = Callable[[dict[str, Any]], Any]


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
