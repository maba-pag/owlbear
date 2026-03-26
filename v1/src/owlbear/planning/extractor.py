"""LLM-based project definition extraction using PydanticAI structured output."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pydantic_ai import Agent

from owlbear.planning.models import ProjectDefinition

if TYPE_CHECKING:
    from pydantic_ai.models import Model

    from owlbear.memory.usage import UsageTracker

from owlbear.memory.usage import record_agent_usage

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """\
Extract a structured project definition from the given conversation text.

Identify and return as JSON matching the ProjectDefinition schema:
  - name: a short project name
  - description: a concise summary of what the project is
  - goals: a list of high-level goals or objectives
  - requirements: a list of requirements, each with description, kind \
(functional / non-functional), and priority
  - acceptance_criteria: a list of measurable acceptance criteria
  - tech_stack: technologies, languages, or frameworks mentioned (may be empty)
  - risks: identified risks or concerns (may be empty)
  - open_questions: unresolved questions needing further clarification (may be \
empty)
"""


def _default_definition() -> ProjectDefinition:
    """Return an empty ProjectDefinition with all required fields set to blanks."""
    return ProjectDefinition(
        name="",
        description="",
        goals=[],
        requirements=[],
        acceptance_criteria=[],
    )


class ProjectDefinitionExtractor:
    """LLM-based project definition extractor using PydanticAI.

    Uses a PydanticAI ``Agent[None, ProjectDefinition]`` with structured output
    to extract a project definition from conversation text.

    Usage::

        extractor = ProjectDefinitionExtractor(model="openai:gpt-4o")
        definition = await extractor.extract("We want to build ...")
        print(definition.name, definition.goals)

    Args:
        model: PydanticAI model string or :class:`~pydantic_ai.models.Model` instance.
        tracker: Optional :class:`~owlbear.memory.usage.UsageTracker` to record
            per-extraction usage via ``operation='project_extraction'``.
        provider: Provider name forwarded to the usage record (e.g. ``'copilot'``).
            Only meaningful when *tracker* is set.
    """

    def __init__(
        self,
        model: str | Model,
        tracker: UsageTracker | None = None,
        provider: str = "copilot",
    ) -> None:
        self._agent: Agent[None, ProjectDefinition] = Agent(
            model,
            output_type=ProjectDefinition,
            system_prompt=EXTRACTION_PROMPT,
        )
        self._tracker = tracker
        self._provider = provider

    async def extract(self, text: str) -> ProjectDefinition:
        """Extract a project definition from *text*.

        Returns an empty ``ProjectDefinition`` for empty/whitespace-only text
        or when the LLM call fails.
        """
        if not text or not text.strip():
            return _default_definition()

        try:
            result = await self._agent.run(text)
        except Exception:  # noqa: BLE001
            logger.warning("Project definition extraction failed", exc_info=True)
            return _default_definition()
        else:
            if self._tracker is not None:
                record_agent_usage(
                    tracker=self._tracker,
                    result=result,
                    model=self._agent.model or "",
                    provider=self._provider,
                    session_id="background:project_extraction",
                    operation="project_extraction",
                )
            return result.output
