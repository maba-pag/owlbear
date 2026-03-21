"""Public API for the owlbear.planning package.

Provides project-scoping and definition extraction: structured models
(``ProjectDefinition``, ``Requirement``), an LLM-based extractor
(``ProjectDefinitionExtractor``), and a markdown renderer
(``project_definition_to_markdown``).
"""

from __future__ import annotations

from owlbear.planning.extractor import ProjectDefinitionExtractor
from owlbear.planning.markdown import project_definition_to_markdown
from owlbear.planning.models import ProjectDefinition, Requirement

__all__ = [
    "ProjectDefinition",
    "ProjectDefinitionExtractor",
    "Requirement",
    "project_definition_to_markdown",
]
