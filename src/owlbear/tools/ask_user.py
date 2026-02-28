"""AskUserToolset — FunctionToolset wrapping ``ask_user`` for human-in-the-loop.

Provides a single ``ask_user`` tool that sends a question to the user via a
:class:`~owlbear.channels.base.ChannelPlugin`, optionally with numbered
options, validates the response, and returns the answer.

Usage::

    from owlbear.channels.cli import CLIChannel
    from owlbear.tools.ask_user import AskUserToolset

    channel = CLIChannel()
    toolset = AskUserToolset(channel)
    answer = await toolset.ask_user("What priority?", options=["high", "low"])
"""

from __future__ import annotations

import asyncio
import enum
import logging
from typing import TYPE_CHECKING

from pydantic_ai.toolsets import FunctionToolset

if TYPE_CHECKING:
    from owlbear.channels.base import ChannelPlugin

__all__ = ["AskUserTimeoutError", "AskUserToolset", "TimeoutAction"]

logger = logging.getLogger(__name__)


class TimeoutAction(enum.StrEnum):
    """Behaviour when the user fails to respond in time."""

    ABORT = "abort"
    SKIP = "skip"


class AskUserTimeoutError(TimeoutError):
    """Raised when the user does not respond and ``timeout_action`` is ABORT."""


class AskUserToolset(FunctionToolset):
    """FunctionToolset subclass that registers an ``ask_user`` tool.

    Args:
        channel: Channel adapter used to communicate with the user.
        timeout_seconds: Seconds to wait for each ``channel.receive()`` call.
        max_retries: Maximum re-ask attempts when option input is invalid.
        timeout_action: Behaviour on timeout or retry exhaustion.
        default_response: String returned when ``timeout_action`` is SKIP.
    """

    def __init__(
        self,
        channel: ChannelPlugin,
        timeout_seconds: float = 120.0,
        max_retries: int = 3,
        timeout_action: TimeoutAction = TimeoutAction.ABORT,
        default_response: str = "(no response)",
    ) -> None:
        super().__init__()
        self._channel = channel
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries
        self._timeout_action = timeout_action
        self._default_response = default_response
        self._register_tools()

    # ------------------------------------------------------------------
    # Tool registration
    # ------------------------------------------------------------------

    def _register_tools(self) -> None:
        """Register the ``ask_user`` tool on this toolset."""
        self.add_function(
            self.ask_user,
            name="ask_user",
            description=(
                "Ask the user a question and return their answer. "
                "Optionally provide a list of options for the user to pick from."
            ),
        )

    # ------------------------------------------------------------------
    # Core tool
    # ------------------------------------------------------------------

    async def ask_user(
        self,
        question: str,
        options: list[str] | None = None,
    ) -> str:
        """Send *question* to the user and return their response.

        When *options* is provided, formats a numbered list and validates
        the response (by index or case-insensitive text match).  Invalid
        input triggers a re-ask up to ``max_retries`` times.
        """
        prompt = self._format_prompt(question, options)
        await self._channel.send(prompt)

        if options is None:
            return await self._receive_with_timeout()

        return await self._receive_option(options)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _format_prompt(question: str, options: list[str] | None) -> str:
        """Build the user-facing prompt string."""
        if options is None:
            return question

        lines = [question]
        for i, opt in enumerate(options, 1):
            lines.append(f"[{i}] {opt}")
        lines.append(f"Choose [1-{len(options)}]:")
        return "\n".join(lines)

    async def _receive_with_timeout(self) -> str:
        """Wait for a single channel response, handling timeout."""
        try:
            response = await asyncio.wait_for(
                self._channel.receive(),
                timeout=self._timeout_seconds,
            )
        except TimeoutError:
            return self._handle_timeout()
        else:
            return response or self._default_response

    async def _receive_option(self, options: list[str]) -> str:
        """Validate option input, re-asking on invalid up to max_retries."""
        lower_map = {opt.lower(): opt for opt in options}

        for attempt in range(self._max_retries):
            try:
                raw = await asyncio.wait_for(
                    self._channel.receive(),
                    timeout=self._timeout_seconds,
                )
            except TimeoutError:
                return self._handle_timeout()

            if raw is None:
                return self._handle_timeout()

            text = raw.strip()

            # Try index match.
            if text.isdigit():
                idx = int(text)
                if 1 <= idx <= len(options):
                    return options[idx - 1]

            # Try case-insensitive text match.
            if text.lower() in lower_map:
                return lower_map[text.lower()]

            # Invalid — re-ask (unless last attempt).
            if attempt < self._max_retries - 1:
                prompt = self._format_prompt(
                    "Invalid choice. Please try again:",
                    options,
                )
                await self._channel.send(prompt)

        # Exhausted retries.
        return self._handle_timeout()

    def _handle_timeout(self) -> str:
        """Apply timeout_action: raise or return default."""
        if self._timeout_action == TimeoutAction.ABORT:
            msg = "User did not respond in time"
            raise AskUserTimeoutError(msg)
        return self._default_response
