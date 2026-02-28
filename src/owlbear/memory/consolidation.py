"""LLM-based memory consolidation using PydanticAI structured output.

Summarises unconsolidated conversation turns into a persistent MEMORY.md
(always in context) and appends a timestamped entry to HISTORY.md (searchable
log).  Follows the nanobot two-layer memory pattern.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel
from pydantic_ai import Agent

if TYPE_CHECKING:
    from pathlib import Path

    from pydantic_ai.models import Model

    from owlbear.memory.session import SessionStore

logger = logging.getLogger(__name__)

_CONSOLIDATION_PROMPT = """\
Summarize the following conversation into a concise memory document.

Return:
- A brief summary (2-3 sentences, ~100 words)
- A list of key facts, decisions, and context worth remembering

Focus on actionable information: what was decided, what was learned,
what the user's preferences and goals are.
"""


class ConsolidationResult(BaseModel):
    """Structured output from the consolidation LLM call."""

    summary: str
    key_facts: list[str]


class MemoryConsolidator:
    """Consolidate conversation history into MEMORY.md and HISTORY.md.

    Uses a lightweight PydanticAI Agent with structured output to summarise
    unconsolidated messages.  Triggered when the number of new messages
    exceeds *threshold*.

    Args:
        workspace_root: Directory where MEMORY.md and HISTORY.md live.
        model: PydanticAI model name or instance (cheap/fast model).
        threshold: Minimum unconsolidated messages before consolidation fires.
    """

    def __init__(
        self,
        workspace_root: Path,
        model: str | Model = "test",
        threshold: int = 20,
    ) -> None:
        self._root = workspace_root
        self._threshold = threshold
        self._agent: Agent[None, ConsolidationResult] = Agent(
            model,
            output_type=ConsolidationResult,
            system_prompt=_CONSOLIDATION_PROMPT,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def consolidate(self, session: SessionStore) -> bool:
        """Consolidate unconsolidated session messages.

        Returns ``True`` if consolidation was performed, ``False`` if the
        number of unconsolidated messages was at or below *threshold*.
        """
        messages = session.load()
        last = session.last_consolidated or 0
        unconsolidated = messages[last:]

        if len(unconsolidated) <= self._threshold:
            return False

        prompt = _messages_to_text(unconsolidated)
        result = await self._agent.run(prompt)
        output: ConsolidationResult = result.output

        self._write_memory(output)
        self._append_history(output)

        session.last_consolidated = len(messages)
        session.save(messages)

        logger.info(
            "Consolidated %d messages (index %d→%d)",
            len(unconsolidated),
            last,
            len(messages),
        )
        return True

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _write_memory(self, result: ConsolidationResult) -> None:
        """Overwrite MEMORY.md with the latest consolidation."""
        facts = "\n".join(f"- {f}" for f in result.key_facts)
        content = f"# Memory\n\n## Summary\n{result.summary}\n\n## Key Facts\n{facts}\n"
        path = self._root / "MEMORY.md"
        path.write_text(content, encoding="utf-8")

    def _append_history(self, result: ConsolidationResult) -> None:
        """Append a timestamped entry to HISTORY.md."""
        ts = datetime.now(UTC).isoformat(timespec="seconds")
        entry = f"## {ts}\n{result.summary}\n---\n"
        path = self._root / "HISTORY.md"
        with path.open("a", encoding="utf-8") as fh:
            fh.write(entry)


def _messages_to_text(messages: list[object]) -> str:
    """Convert a list of ModelMessage objects to plain text for the LLM."""
    from pydantic_ai.messages import ModelRequest, ModelResponse  # noqa: PLC0415

    lines: list[str] = []
    for msg in messages:
        if isinstance(msg, ModelRequest):
            lines.extend(f"User: {part.content}" for part in msg.parts if hasattr(part, "content"))
        elif isinstance(msg, ModelResponse):
            lines.extend(
                f"Assistant: {part.content}" for part in msg.parts if hasattr(part, "content")
            )
    return "\n".join(lines)
