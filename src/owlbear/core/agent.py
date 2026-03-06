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
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from pydantic_ai import Agent

from owlbear.core.deps import OwlBearDeps
from owlbear.core.hooks import HookEvent, HookRegistry

if TYPE_CHECKING:
    from collections.abc import Sequence

    from pydantic_ai._agent_graph import HistoryProcessor
    from pydantic_ai.models import Model
    from pydantic_ai.toolsets.abstract import AbstractToolset

    from owlbear.channels.base import ChannelPlugin
    from owlbear.core.agent_registry import AgentRegistry
    from owlbear.memory.context import ContextManager
    from owlbear.memory.knowledge.query_service import KnowledgeQueryService
    from owlbear.memory.session import SessionStore
    from owlbear.memory.usage import UsageTracker

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

    def __init__(  # noqa: PLR0913
        self,
        *,
        model: str | Model,
        session: SessionStore,
        context: ContextManager | None = None,
        hooks: HookRegistry | None = None,
        channel: ChannelPlugin | None = None,
        tracker: UsageTracker | None = None,
        provider: str = "copilot",
        toolsets: Sequence[AbstractToolset] | None = None,
        history_processors: Sequence[HistoryProcessor[OwlBearDeps]] | None = None,
        knowledge_service: KnowledgeQueryService | None = None,
    ) -> None:
        self.session = session
        self.context = context
        self.hooks = hooks or HookRegistry()
        self.channel = channel
        self.tracker = tracker
        self.provider = provider
        self.toolsets: list[AbstractToolset] = list(toolsets or [])
        self._model_name = self._extract_model_name(model)
        self._deps = OwlBearDeps(hooks=self.hooks, tracker=self.tracker)
        self._knowledge_service = knowledge_service

        instructions = context.instructions if context else ""
        self.inner: Agent[OwlBearDeps, str] = Agent(
            model,
            instructions=instructions or None,
            toolsets=toolsets or [],
            history_processors=history_processors,
        )

    def update_model(self, new_model: str | Model) -> None:
        """Replace the inner Agent's model in-place.

        Uses PydanticAI's ``Agent.model`` setter — no Agent rebuild needed.
        Also updates ``_model_name`` for usage tracking.

        Args:
            new_model: A :class:`Model` instance or model name string.
        """
        self.inner.model = new_model
        self._model_name = self._extract_model_name(new_model)

    def set_agent_registry(self, registry: AgentRegistry) -> None:
        """Assign the agent registry on the shared deps."""
        self._deps.agent_registry = registry

    @staticmethod
    def _extract_model_name(model: str | Model) -> str:
        """Return a plain string model name for usage tracking."""
        if isinstance(model, str):
            return model
        return getattr(model, "model_name", str(model))

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

        # Knowledge context injection (per-turn)
        run_kwargs: dict[str, object] = {}
        if self._knowledge_service is not None:
            try:
                run_kwargs["instructions"] = self._knowledge_service.query_for_context(prompt)
            except Exception:  # noqa: BLE001
                logger.warning(
                    "Knowledge context injection failed for prompt: %s",
                    prompt[:100],
                    exc_info=True,
                )

        try:
            result = await self.inner.run(
                prompt,
                message_history=history or None,
                deps=self._deps,
                **run_kwargs,
            )
        except Exception as exc:
            await self.hooks.emit(HookEvent.ON_ERROR, {"error": exc, "prompt": prompt})
            raise

        self.session.save(result.all_messages())

        if self.tracker is not None:
            self._record_usage(result)

        return result.output

    def _record_usage(self, result: object) -> None:
        """Append a :class:`UsageRecord` from the agent run result."""
        from owlbear.memory.usage import UsageRecord  # noqa: PLC0415

        try:
            usage = result.usage()  # type: ignore[attr-defined]

            estimated_cost: float | None = None
            try:
                from owlbear.memory.usage_cost import (  # noqa: PLC0415
                    calc_estimated_cost,
                )

                estimated_cost = calc_estimated_cost(
                    self._model_name,
                    self.provider,
                    usage.input_tokens or 0,
                    usage.output_tokens or 0,
                )
            except Exception:  # noqa: BLE001
                logger.debug("Cost calculation unavailable", exc_info=True)

            premium: float | None = None
            if self.provider == "copilot":
                try:
                    from owlbear.providers.copilot_multipliers import (  # noqa: PLC0415
                        get_premium_requests,
                    )

                    premium = get_premium_requests(self._model_name)
                except Exception:  # noqa: BLE001
                    logger.debug("Premium request lookup unavailable", exc_info=True)

            record = UsageRecord(
                timestamp=datetime.now(UTC),
                session_id=str(self.session.path),
                model=self._model_name,
                provider=self.provider,
                input_tokens=usage.input_tokens or 0,
                output_tokens=usage.output_tokens or 0,
                cache_read_tokens=usage.cache_read_tokens or 0,
                cache_write_tokens=usage.cache_write_tokens or 0,
                requests=usage.requests or 0,
                tool_calls=usage.tool_calls or 0,
                estimated_cost_usd=estimated_cost,
                premium_requests=premium,
            )
            self.tracker.append(record)  # type: ignore[union-attr]
        except Exception:  # noqa: BLE001
            logger.debug("Failed to record usage", exc_info=True)
