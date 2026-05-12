"""Entity extraction pipeline — DI-based implementation.

:class:`EntityExtractor` delegates to an injected :class:`StructuredExtractor`
for LLM-backed entity and relationship extraction.  Pass ``extractor=`` to wire
in a real backend; omit it for a no-op stub (backward-compatible).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field

from owlbear_knowledge.models import Edge, Entity  # noqa: TC001 — needed by Pydantic at runtime

if TYPE_CHECKING:
    from owlbear_knowledge.protocol import StructuredExtractor

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
    """Entity extractor with optional injected :class:`StructuredExtractor`.

    When ``extractor`` is provided, non-empty input is forwarded to it (with
    an optional metadata prefix).  When omitted, the extractor behaves as a
    no-op stub returning empty :class:`ExtractionResult`.

    Args:
        extractor: Injected :class:`StructuredExtractor` for structured extraction.
    """

    def __init__(
        self,
        *,
        extractor: StructuredExtractor | None = None,
    ) -> None:
        self._extractor = extractor

    async def extract(
        self,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> ExtractionResult:
        """Extract entities and edges from *text*.

        Args:
            text: Source text to extract from.
            metadata: Optional key/value pairs prepended to the prompt.

        Returns:
            :class:`ExtractionResult` from the injected extractor, or an
            empty result when input is blank or no extractor is wired.
        """
        if not text or not text.strip():
            return ExtractionResult()
        if self._extractor is None:
            logger.debug(
                "EntityExtractor.extract called — returning empty result (no-op)"
            )
            return ExtractionResult()
        prompt = text
        if metadata:
            prefix = "\n".join(f"{k}: {v}" for k, v in metadata.items())
            prompt = f"{prefix}\n{text}"
        return await self._extractor.extract(prompt)
