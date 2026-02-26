"""OwlBearAgent — thin wrapper composing PydanticAI Agent with OwlBear concerns.

This is the central orchestrator.  It wires together:

- **PydanticAI Agent** for LLM interaction, tool execution, and retries
- **SessionStore** for JSONL message persistence
- **ContextManager** for static workspace instructions
- **HookRegistry** for lifecycle event observation
- **ChannelPlugin** for user-facing I/O (optional)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pydantic_ai import Agent

from owlbear.core.hooks import HookEvent, HookRegistry

if TYPE_CHECKING:
    from owlbear.channels.base import ChannelPlugin
    from owlbear.memory.context import ContextManager
    from owlbear.memory.session import SessionStore

logger = logging.getLogger(__name__)


class OwlBearAgent:
    """Compose PydanticAI Agent with persistence, hooks, and channels.

    Usage::

        agent = OwlBearAgent(
            model="openai:gpt-4o",
            session=SessionStore(Path("sessions/abc.jsonl")),
            context=ContextManager(Path("/project")),
        )
        reply = await agent.turn("What files are in src/?")
    """

    def __init__(
        self,
        *,
        model: str,
        session: SessionStore,
        context: ContextManager | None = None,
        hooks: HookRegistry | None = None,
        channel: ChannelPlugin | None = None,
    ) -> None:
        self.session = session
        self.hooks = hooks or HookRegistry()
        self.channel = channel

        instructions = context.instructions if context else ""
        self.inner: Agent[None, str] = Agent(
            model,
            instructions=instructions or None,
        )

    async def turn(self, prompt: str) -> str:
        """Execute a single conversational turn.

        1. Emit ON_MESSAGE hook with the user prompt
        2. Load session history
        3. Call PydanticAI Agent.run() with history
        4. Persist the updated message list
        5. Return the model's text response

        On error, emits ON_ERROR hook then re-raises.
        """
        await self.hooks.emit(HookEvent.ON_MESSAGE, {"prompt": prompt})

        history = self.session.load()

        try:
            result = await self.inner.run(
                prompt,
                message_history=history or None,
            )
        except Exception as exc:
            await self.hooks.emit(HookEvent.ON_ERROR, {"error": exc, "prompt": prompt})
            raise

        self.session.save(result.all_messages())
        return result.output
