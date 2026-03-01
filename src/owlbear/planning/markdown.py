"""Markdown generator for ProjectDefinition models.

Converts a ``ProjectDefinition`` into a human-readable markdown document
with structured sections for goals, requirements, acceptance criteria,
and optional metadata.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from owlbear.planning.models import ProjectDefinition, Requirement


def _format_requirement(req: Requirement) -> str:
    """Format a single requirement line, showing priority only if non-default."""
    line = f"- {req.description}"
    if req.priority != "important":
        line += f" (priority: {req.priority})"
    return line


def _bullet_list(items: list[str]) -> str:
    """Render a list of strings as markdown bullet items."""
    return "\n".join(f"- {item}" for item in items)


def _optional_section(heading: str, items: list[str]) -> str:
    """Render an optional section — returns empty string if items is empty."""
    if not items:
        return ""
    return f"## {heading}\n\n{_bullet_list(items)}\n"


def project_definition_to_markdown(defn: ProjectDefinition) -> str:
    """Convert a ProjectDefinition to a markdown string.

    Sections are rendered in order: name (h1), description, goals,
    requirements (grouped by kind), acceptance criteria, then optional
    sections (tech stack, risks, open questions) — only if non-empty.

    Args:
        defn: The project definition model to render.

    Returns:
        A markdown-formatted string.
    """
    sections: list[str] = []

    # H1 — project name
    sections.append(f"# {defn.name}\n")

    # Description
    sections.append(f"## Description\n\n{defn.description}\n")

    # Goals — bullet list
    sections.append(f"## Goals\n\n{_bullet_list(defn.goals)}\n")

    # Requirements — grouped by kind
    functional = [r for r in defn.requirements if r.kind == "functional"]
    non_functional = [r for r in defn.requirements if r.kind == "non-functional"]

    req_parts: list[str] = ["## Requirements\n"]
    if functional:
        req_parts.append("### Functional\n")
        req_parts.append(
            "\n".join(_format_requirement(r) for r in functional) + "\n"
        )
    if non_functional:
        req_parts.append("### Non-Functional\n")
        req_parts.append(
            "\n".join(_format_requirement(r) for r in non_functional) + "\n"
        )
    sections.append("\n".join(req_parts))

    # Acceptance criteria — checklist
    checklist = "\n".join(f"- [ ] {item}" for item in defn.acceptance_criteria)
    sections.append(f"## Acceptance Criteria\n\n{checklist}\n")

    # Optional sections — omitted when empty
    for heading, items in [
        ("Tech Stack", defn.tech_stack),
        ("Risks", defn.risks),
        ("Open Questions", defn.open_questions),
    ]:
        section = _optional_section(heading, items)
        if section:
            sections.append(section)

    return "\n".join(sections)
