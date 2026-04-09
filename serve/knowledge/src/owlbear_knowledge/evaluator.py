"""Source evaluation pipeline — LLM callable injection.

Provides the EvaluationResult schema and SourceEvaluator that delegates
relevance scoring to an injected async callable.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

MAX_CONTENT_LENGTH = 2000

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


def make_pydantic_evaluate_fn(model: str) -> EvaluateFn:
    """Return an async EvaluateFn backed by a PydanticAI Agent.

    Constructs ``pydantic_ai.Agent(model, output_type=EvaluationResult,
    system_prompt=EVALUATION_PROMPT)`` and returns a coroutine callable that
    forwards the prompt to ``agent.run()`` and returns ``result.output``.

    Raises:
        ImportError: when pydantic-ai is not installed.
    """
    import pydantic_ai  # noqa: PLC0415

    agent = pydantic_ai.Agent(
        model,
        output_type=EvaluationResult,
        system_prompt=EVALUATION_PROMPT,
    )

    async def _evaluate(prompt: str) -> EvaluationResult:
        result = await agent.run(prompt)
        return result.output

    return _evaluate


def _default_result() -> EvaluationResult:
    """Return a neutral EvaluationResult when no project context is available."""
    return EvaluationResult(
        relevance_score=0.5,
        tags=[],
        summary="No project context available -- neutral evaluation.",
        worth_ingesting=True,
    )


def _build_prompt(content: str, project_context: dict[str, object]) -> str:
    """Build an evaluation prompt from content and project context.

    Truncates content to MAX_CONTENT_LENGTH characters.
    """
    excerpt = content[:MAX_CONTENT_LENGTH]
    name = project_context.get("name", "")
    desc = project_context.get("description", "")
    goals = project_context.get("goals", "")
    context_parts = [str(p) for p in (name, desc, goals) if p]
    context_text = "\n".join(context_parts)
    return f"## Project Context\n{context_text}\n\n## Content Excerpt\n{excerpt}"


class SourceEvaluator:
    """Source evaluator that delegates to an injected async LLM callable.

    Args:
        llm_fn: Async callable that accepts a prompt string and returns
            an EvaluationResult. If None or a non-callable is supplied
            (backward-compat with model-string wiring), evaluate() returns
            _default_result() instead of crashing.
    """

    def __init__(self, llm_fn: EvaluateFn | None = None, **_kwargs: object) -> None:
        self._llm_fn: EvaluateFn | None = llm_fn if callable(llm_fn) else None

    async def evaluate(
        self,
        content: str,
        project_context: dict[str, object] | None = None,
    ) -> EvaluationResult:
        """Evaluate content for ingestion relevance.

        Returns:
            EvaluationResult with relevance_score=0.0 for empty content,
            _default_result() when project_context is None, or the LLM
            result for valid inputs.
        """
        if not content or not content.strip():
            return EvaluationResult(
                relevance_score=0.0,
                tags=[],
                summary="Empty content -- nothing to evaluate.",
                worth_ingesting=False,
            )

        if project_context is None or self._llm_fn is None:
            return _default_result()

        prompt = _build_prompt(content, project_context)
        try:
            return await self._llm_fn(prompt)
        except Exception:  # noqa: BLE001
            logger.warning("LLM evaluation failed", exc_info=True)
            return EvaluationResult(
                relevance_score=0.5,
                tags=[],
                summary="Evaluation failed -- returning neutral score.",
                worth_ingesting=False,
            )
