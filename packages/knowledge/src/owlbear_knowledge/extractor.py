"""Entity extraction pipeline — no-op implementation.

PydanticAI has been removed per AC. This module provides the
ExtractionResult schema and a stub EntityExtractor that returns empty
results without making LLM calls. Real extraction is wired up at the
application layer.
"""

from __future__ import annotations

import logging

from pydantic import BaseModel, ConfigDict, Field

from owlbear_knowledge.models import Edge, Entity  # noqa: TC001 — needed by Pydantic at runtime

logger = logging.getLogger(__name__)


class ExtractionResult(BaseModel):
    """Result of entity extraction — entities and relationships found in text."""

    model_config = ConfigDict(frozen=True)

    entities: list[Entity] = Field(default_factory=list)
    edges: list[Edge] = Field(default_factory=list)


class EntityExtractor:
    """Schema-only entity extractor with no LLM dependency.

    Returns empty ExtractionResult for all inputs. Wire up a real
    LLM backend at the application layer if extraction is needed.

    Args:
        model: Ignored — kept for API compatibility.
    """

    def __init__(self, model: str | object, **_kwargs: object) -> None:
        self._model = model

    async def extract(self, text: str) -> ExtractionResult:
        """Return an empty ExtractionResult (no LLM dependency)."""
        if not text or not text.strip():
            return ExtractionResult()
        logger.debug("EntityExtractor.extract called — returning empty result (no-op)")
        return ExtractionResult()
