"""LLM-based entity extraction using PydanticAI structured output."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic_ai import Agent

from owlbear.memory.knowledge.models import Edge, Entity  # noqa: TC001 — Pydantic needs at runtime

if TYPE_CHECKING:
    from pydantic_ai.models import Model

    from owlbear.memory.usage import UsageTracker

from owlbear.memory.usage import record_agent_usage

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """\
Extract entities and relationships from the given text.

Identify:
- **Entities**: functions, classes, patterns, decisions, concepts, files
- **Relationships**: defines, imports, depends_on, related_to, implements, documents

Return your findings as JSON matching the ExtractionResult schema.

Each entity needs:
  - name: a short identifier
  - entity_type: one of file, function, class_, decision, pattern, concept
  - description: a brief description of what it is or does
  - importance: a 0.0 to 1.0 score indicating how important the entity is
    (0.0 = trivial, 1.0 = critical)

Each edge needs:
  - source_id: the id of the source entity
  - target_id: the id of the target entity
  - relation: one of defines, imports, depends_on, related_to, implements, documents
"""


class ExtractionResult(BaseModel):
    """Result of entity extraction — entities and relationships found in text."""

    model_config = ConfigDict(frozen=True)

    entities: list[Entity] = Field(default_factory=list)
    edges: list[Edge] = Field(default_factory=list)


class EntityExtractor:
    """LLM-based entity and relationship extractor using PydanticAI.

    Uses a PydanticAI ``Agent[None, ExtractionResult]`` with structured output
    to identify entities (functions, classes, concepts, …) and their
    relationships from a text chunk.

    Usage::

        extractor = EntityExtractor(model="openai:gpt-4o")
        result = await extractor.extract("def hello(): ...")
        print(result.entities, result.edges)
    """

    def __init__(
        self,
        model: str | Model,
        tracker: UsageTracker | None = None,
        provider: str | None = None,
    ) -> None:
        self._agent: Agent[None, ExtractionResult] = Agent(
            model,
            output_type=ExtractionResult,
            system_prompt=EXTRACTION_PROMPT,
        )
        self._tracker = tracker
        self._provider = provider

    async def extract(
        self,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> ExtractionResult:
        """Extract entities and edges from *text*.

        Returns an empty ``ExtractionResult`` for empty/whitespace-only text
        or when the LLM call fails.
        """
        if not text or not text.strip():
            return ExtractionResult()

        prompt = text
        if metadata:
            prompt = f"Context metadata: {metadata}\n\n{text}"

        try:
            result = await self._agent.run(prompt)
        except Exception:  # noqa: BLE001
            logger.warning("Entity extraction failed for text chunk", exc_info=True)
            return ExtractionResult()
        else:
            if self._tracker is not None:
                record_agent_usage(
                    tracker=self._tracker,
                    result=result,
                    model=str(self._agent.model or ""),
                    provider=self._provider or "",
                    session_id="background:entity_extraction",
                    operation="entity_extraction",
                )
            return result.output
