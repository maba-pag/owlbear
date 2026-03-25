"""LLM-based source relevance evaluator using PydanticAI structured output."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic_ai import Agent

if TYPE_CHECKING:
    from pydantic_ai.models import Model

    from owlbear.memory.usage import UsageTracker

from owlbear.memory.usage import record_agent_usage

logger = logging.getLogger(__name__)

MAX_CONTENT_LENGTH = 2000
"""Maximum number of characters from content to include in the evaluation prompt."""

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
    """Result of source relevance evaluation — score, tags, summary, ingest flag."""

    model_config = ConfigDict(frozen=True)

    relevance_score: float = Field(ge=0.0, le=1.0)
    tags: list[str] = Field(default_factory=list)
    summary: str = ""
    worth_ingesting: bool = False


def _default_result(
    *,
    relevance_score: float = 0.5,
    summary: str = "No project context available — neutral evaluation.",
    worth_ingesting: bool = True,
) -> EvaluationResult:
    """Build a neutral fallback result."""
    return EvaluationResult(
        relevance_score=relevance_score,
        tags=[],
        summary=summary,
        worth_ingesting=worth_ingesting,
    )


def _build_prompt(content: str, project_context: dict[str, Any]) -> str:
    """Build the user prompt with truncated content and project context."""
    excerpt = content[:MAX_CONTENT_LENGTH]

    project_section = (
        f"Project: {project_context.get('name', 'Unknown')}\n"
        f"Description: {project_context.get('description', 'N/A')}\n"
        f"Goals: {', '.join(project_context.get('goals', []))}"
    )

    return f"## Project Context\n{project_section}\n\n## Content Excerpt\n{excerpt}"


class SourceEvaluator:
    """LLM-based source relevance evaluator using PydanticAI.

    Uses a PydanticAI ``Agent[None, EvaluationResult]`` with structured output
    to score how relevant a piece of content is to the current project.

    Usage::

        evaluator = SourceEvaluator(model="openai:gpt-4o")
        result = await evaluator.evaluate(content, {"name": "MyProject", ...})
        print(result.relevance_score, result.tags)
    """

    def __init__(
        self,
        model: str | Model,
        tracker: UsageTracker | None = None,
        provider: str = "copilot",
    ) -> None:
        self._agent: Agent[None, EvaluationResult] = Agent(
            model,
            output_type=EvaluationResult,
            system_prompt=EVALUATION_PROMPT,
        )
        self._tracker = tracker
        self._provider = provider

    async def evaluate(
        self,
        content: str,
        project_context: dict[str, Any] | None = None,
    ) -> EvaluationResult:
        """Evaluate relevance of *content* to the project.

        Args:
            content (str): Text content to evaluate. Truncated to first 2000 chars.
            project_context (dict[str, Any] | None): Dict with ``name``, ``description``, ``goals`` keys.
                When ``None``, returns a neutral score (0.5) without calling the LLM.

        Returns:
            EvaluationResult: Structured evaluation with score, tags, summary, and ingest flag.
"""
        if not content or not content.strip():
            return EvaluationResult(
                relevance_score=0.0,
                tags=[],
                summary="Empty content — nothing to evaluate.",
                worth_ingesting=False,
            )

        if project_context is None:
            return _default_result()

        prompt = _build_prompt(content, project_context)

        try:
            result = await self._agent.run(prompt)
        except Exception:  # noqa: BLE001
            logger.warning("Source evaluation failed", exc_info=True)
            return EvaluationResult(
                relevance_score=0.5,
                tags=[],
                summary="Evaluation failed — returning neutral score.",
                worth_ingesting=False,
            )
        else:
            if self._tracker is not None:
                record_agent_usage(
                    tracker=self._tracker,
                    result=result,
                    model=self._agent.model or "",
                    provider=self._provider,
                    session_id="background:source_evaluation",
                    operation="source_evaluation",
                )
            return result.output
