"""Per-task failure counting and user escalation for orchestrator dispatch.

Tracks how many times each task has failed during wave dispatch. When a
configurable threshold is reached the task is skipped and the user is
offered retry / skip / stop via the active channel.

See docs/research/mission-control.md §3.2 and §4.
"""

from __future__ import annotations

import enum
import logging
from datetime import UTC, datetime
from typing import Any

__all__ = ["EscalationChoice", "LoopDetector"]

_log = logging.getLogger(__name__)


class EscalationChoice(enum.Enum):
    """User response to a loop-detection escalation."""

    RETRY = "retry"
    SKIP = "skip"
    STOP = "stop"


_VALID_CHOICES = {m.value for m in EscalationChoice}


class LoopDetector:
    """Track per-task failures and escalate when a threshold is reached.

    Args:
        max_failures: Number of failures before escalation (default 3).
        error_journal: Optional ``ErrorJournal`` (or mock) for persistence.
    """

    def __init__(
        self,
        max_failures: int = 3,
        error_journal: Any = None,  # noqa: ANN401
    ) -> None:
        self._max_failures = max_failures
        self._journal = error_journal
        self._counts: dict[str, int] = {}
        self._last_errors: dict[str, str] = {}

    # -- properties ----------------------------------------------------------

    @property
    def max_failures(self) -> int:
        """Configured failure threshold."""
        return self._max_failures

    # -- counting ------------------------------------------------------------

    def failure_count(self, task_id: str) -> int:
        """Return the current failure count for *task_id*."""
        return self._counts.get(task_id, 0)

    def record_failure(self, task_id: str, *, error: str) -> None:
        """Increment failure counter for *task_id* and persist to journal."""
        self._counts[task_id] = self._counts.get(task_id, 0) + 1
        self._last_errors[task_id] = error
        attempt = self._counts[task_id]
        self._log_to_journal(task_id=task_id, error=error, attempt=attempt, action="failure")

    def should_escalate(self, task_id: str) -> bool:
        """Return ``True`` when *task_id* has reached the failure threshold."""
        return self._counts.get(task_id, 0) >= self._max_failures

    # -- escalation ----------------------------------------------------------

    async def escalate(self, task_id: str, *, channel: Any) -> EscalationChoice:  # noqa: ANN401
        """Notify user via *channel* and return their chosen action.

        Sends a message containing the task ID and last error, then waits
        for a response.  Unrecognised responses default to ``SKIP``.
        If the channel raises, returns ``SKIP`` as a safe fallback.
        """
        last_error = self._last_errors.get(task_id, "unknown error")
        count = self._counts.get(task_id, 0)
        msg = (
            f"Task {task_id} has failed {count} time(s).\n"
            f"Last error: {last_error}\n"
            f"Options: retry / skip / stop"
        )

        try:
            await channel.send(msg)
        except Exception:  # noqa: BLE001
            _log.warning("Failed to send escalation message for %s", task_id)
            self._log_to_journal(
                task_id=task_id,
                error=last_error,
                attempt=count,
                action="escalation_send_failed",
            )
            return EscalationChoice.SKIP

        try:
            raw = await channel.receive()
        except Exception:  # noqa: BLE001
            raw = None

        choice = self._parse_choice(raw)

        if choice == EscalationChoice.RETRY:
            self._counts[task_id] = 0

        self._log_to_journal(
            task_id=task_id,
            error=last_error,
            attempt=count,
            action=f"escalation:{choice.value}",
        )
        return choice

    # -- internals -----------------------------------------------------------

    @staticmethod
    def _parse_choice(raw: str | None) -> EscalationChoice:
        """Map raw user input to an EscalationChoice, defaulting to SKIP."""
        if raw is None:
            return EscalationChoice.SKIP
        normalized = str(raw).strip().lower()
        if normalized in _VALID_CHOICES:
            return EscalationChoice(normalized)
        return EscalationChoice.SKIP

    def _log_to_journal(
        self,
        *,
        task_id: str,
        error: str,
        attempt: int,
        action: str,
    ) -> None:
        """Best-effort write to the error journal."""
        if self._journal is None:
            return
        try:
            self._journal.log(
                ts=datetime.now(tz=UTC).isoformat(),
                error_type="loop_detection",
                tool_name="orchestrator",
                exc_message=f"[{task_id}] {error}",
                action_taken=action,
                attempt=attempt,
                resolved=False,
                session_id="",
            )
        except Exception:  # noqa: BLE001
            _log.debug("Journal write failed for task %s", task_id, exc_info=True)
