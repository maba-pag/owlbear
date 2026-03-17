"""Context condenser — PydanticAI HistoryProcessor that LLM-summarizes old messages.

Adapted from the OpenHands ``LLMSummarizingCondenser`` pattern for PydanticAI's
``ModelMessage`` structure.  Used as a ``history_processors`` entry on the OwlBear
agent to keep long conversations within context-window limits.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from pydantic_ai import Agent
from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)

if TYPE_CHECKING:
    from pydantic_ai import RunContext
    from pydantic_ai.messages import ModelMessage
    from pydantic_ai.models import Model

    from owlbear.memory.usage import UsageTracker

from owlbear.memory.usage import record_agent_usage

logger = logging.getLogger(__name__)

_SUMMARY_PROMPT = (
    "Summarize the following conversation segment concisely. "
    "Preserve key decisions, tool results, and action items. "
    "Omit pleasantries and redundant exchanges.\n\n"
)


class SummarizingCondenser:
    """HistoryProcessor that condenses conversation history via LLM summarization.

    When the message list exceeds *max_events*, the middle portion is replaced
    with a single LLM-generated summary while preserving the first *keep_first*
    messages and a computed tail.

    Args:
        max_events: Trigger threshold — condense only when ``len(messages)`` exceeds this.
        keep_first: Number of messages at the start to always preserve.
        target_size: Desired output length. Defaults to ``max_events // 2``.
        model: PydanticAI model for the summarization call.  ``None`` defers model
            selection (the internal agent will raise if actually invoked without one).
    """

    def __init__(  # noqa: PLR0913
        self,
        max_events: int = 120,
        keep_first: int = 4,
        target_size: int | None = None,
        model: str | Model | None = None,
        tracker: UsageTracker | None = None,
        provider: str | None = None,
    ) -> None:
        self._max_events = max_events
        self._keep_first = keep_first
        self._target_size = target_size if target_size is not None else max_events // 2
        self._model = model
        self._tracker = tracker
        self._provider = provider

    async def __call__(
        self,
        _ctx: RunContext[object],
        messages: list[ModelMessage],
    ) -> list[ModelMessage]:
        """Condense *messages* when they exceed the threshold.

        Returns the original list unchanged when ``len(messages) <= max_events``.
        Otherwise returns ``head + [summary] + tail``.
        """
        if len(messages) <= self._max_events:
            return messages

        head, middle, tail = self._split(messages)
        summary_result = await self._summarize(middle)
        summary_text = getattr(summary_result, "output", summary_result)

        if self._tracker is not None:
            record_agent_usage(
                tracker=self._tracker,
                result=summary_result,
                model=str(self._model or ""),
                provider=self._provider or "",
                session_id="background:condenser",
                operation="condenser",
            )

        summary_msg = ModelRequest(
            parts=[UserPromptPart(content=f"[Condensed Context]\n{summary_text}")],
            metadata={
                "condensed_at": datetime.now(UTC).isoformat(),
                "forgotten_count": len(middle),
            },
        )

        result = [*head, summary_msg, *tail]

        # PydanticAI invariant: must end with ModelRequest
        if result and not isinstance(result[-1], ModelRequest):
            result.append(ModelRequest(parts=[UserPromptPart(content="(continue)")]))

        logger.info(
            "Condensed %d messages → %d (forgot %d, summarized middle)",
            len(messages),
            len(result),
            len(middle),
        )
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _split(
        self, messages: list[ModelMessage]
    ) -> tuple[list[ModelMessage], list[ModelMessage], list[ModelMessage]]:
        """Split messages into head, middle (to summarize), and tail."""
        keep_first = min(self._keep_first, len(messages))
        # tail_size = target_size - keep_first - 1 (for the summary message)
        tail_size = max(self._target_size - keep_first - 1, 1)

        head_end = keep_first
        tail_start = len(messages) - tail_size

        # Boundary alignment: if the message at head_end is a ToolReturnPart
        # request that pairs with a ToolCallPart response at head_end-1,
        # pull it into the head. Conversely, if head_end lands on a
        # ToolCallPart response whose return is at head_end+1, include both.
        head_end = self._align_boundary(messages, head_end, tail_start)

        head = messages[:head_end]
        tail = messages[tail_start:]
        middle = messages[head_end:tail_start]

        return head, middle, tail

    def _align_boundary(self, messages: list[ModelMessage], head_end: int, tail_start: int) -> int:
        """Adjust head_end so tool-call / tool-return pairs stay together."""
        if head_end >= tail_start or head_end >= len(messages):
            return head_end

        msg = messages[head_end]

        # Case 1: head_end is a ToolCallPart response — include its return too
        if (
            isinstance(msg, ModelResponse)
            and any(isinstance(p, ToolCallPart) for p in msg.parts)
            and head_end + 1 < tail_start
            and isinstance(messages[head_end + 1], ModelRequest)
        ):
            next_msg = messages[head_end + 1]
            if any(isinstance(p, ToolReturnPart) for p in next_msg.parts):
                return head_end + 2

        # Case 2: previous message is a ToolCallPart response and head_end
        # is its ToolReturnPart request — pull the pair into head
        if (
            head_end > 0
            and isinstance(msg, ModelRequest)
            and any(isinstance(p, ToolReturnPart) for p in msg.parts)
        ):
            prev = messages[head_end - 1]
            if isinstance(prev, ModelResponse) and any(
                isinstance(p, ToolCallPart) for p in prev.parts
            ):
                return head_end + 1

        return head_end

    async def _summarize(self, middle: list[ModelMessage]) -> object:
        """Use an internal PydanticAI agent to summarize the middle segment."""
        # Build a text representation of the middle messages for the LLM
        lines: list[str] = []
        for msg in middle:
            if isinstance(msg, ModelRequest):
                for part in msg.parts:
                    if isinstance(part, UserPromptPart):
                        lines.append(f"User: {part.content}")
                    elif isinstance(part, ToolReturnPart):
                        lines.append(f"Tool({part.tool_name}): {part.content}")
            elif isinstance(msg, ModelResponse):
                for part in msg.parts:
                    if isinstance(part, ToolCallPart):
                        lines.append(f"Assistant→{part.tool_name}()")
                    elif isinstance(part, TextPart):
                        lines.append(f"Assistant: {part.content}")

        text_block = "\n".join(lines)

        summarizer: Agent[None, str] = Agent(
            self._model or "test",
            system_prompt=_SUMMARY_PROMPT,
        )
        return await summarizer.run(text_block)
