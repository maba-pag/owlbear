"""Source evaluation pipeline — no-op stub implementation.

Provides the EvaluationResult schema and a stub SourceEvaluator that
returns neutral results without making LLM calls. Real LLM wiring
happens at the application layer.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class EvaluationResult(BaseModel):
    """Result of evaluating a source for ingestion relevance."""

    model_config = ConfigDict(frozen=True)

    relevance_score: float = Field(ge=0.0, le=1.0)
    tags: list[str] = Field(default_factory=list)
    summary: str
    worth_ingesting: bool = False


class SourceEvaluator:
    """Schema-only source evaluator with no LLM dependency.

    Returns neutral EvaluationResult (relevance_score=0.5, worth_ingesting=False)
    for non-empty content and (relevance_score=0.0, worth_ingesting=False) for
    empty content. Wire up a real LLM backend at the application layer.

    Args:
        model: Ignored — kept for API compatibility.
    """

    def __init__(self, model: str | object | None = None) -> None:
        self._model = model

    async def evaluate(
        self,
        content: str,
        project_context: dict[str, object] | None = None,  # noqa: ARG002
    ) -> EvaluationResult:
        """Return a stub EvaluationResult with no LLM dependency."""
        if not content:
            return EvaluationResult(relevance_score=0.0, tags=[], summary="")
        return EvaluationResult(relevance_score=0.5, tags=[], summary="")
