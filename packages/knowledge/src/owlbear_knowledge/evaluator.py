"""Source evaluation pipeline — no-op stub implementation.

Provides the EvaluationResult schema and a stub SourceEvaluator that
returns neutral results without making LLM calls. Real LLM wiring
happens at the application layer.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from pydantic import BaseModel, ConfigDict, Field

EVALUATION_PROMPT = """\
You are a source relevance evaluator. Given a content excerpt and a project \
context, score how relevant this content is to the project.

Evaluate the content on these criteria:
- **Relevance**: How closely does the content relate to the project's goals \
and description?
- **Usefulness**: Does the content contain reusable knowledge, patterns, or \
code that could benefit the project?
- **Quality**: Is the content well-written, accurate, and substantive?

Return your evaluation as JSON matching the EvaluationResult schema:
- relevance_score: float between 0.0 (completely irrelevant) and 1.0 \
(perfectly relevant)
- tags: list of short keyword tags categorizing the content
- summary: 2-3 sentence summary of what the content covers
- worth_ingesting: boolean — true if the content contains reusable knowledge \
worth storing in the knowledge base
"""


class EvaluationResult(BaseModel):
    """Result of evaluating a source for ingestion relevance."""

    model_config = ConfigDict(frozen=True)

    relevance_score: float = Field(ge=0.0, le=1.0)
    tags: list[str] = Field(default_factory=list)
    summary: str = ""
    worth_ingesting: bool = False


EvaluateFn = Callable[[str], Awaitable[EvaluationResult]]


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
        if not content or not content.strip():
            return EvaluationResult(relevance_score=0.0, tags=[], summary="")
        return EvaluationResult(relevance_score=0.5, tags=[], summary="")
