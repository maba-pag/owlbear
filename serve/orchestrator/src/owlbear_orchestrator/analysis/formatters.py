"""Output formatters for AnalysisProposal lists."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from owlbear_orchestrator.analysis.models import AnalysisProposal


def format_json(proposals: list[AnalysisProposal]) -> str:
    """Serialize proposals to a JSON array string using Pydantic serialization."""
    return json.dumps([p.model_dump() for p in proposals])


def format_markdown(proposals: list[AnalysisProposal]) -> str:
    """Format proposals as a Markdown table."""
    if not proposals:
        return "No analysis proposals."

    rows = [f"| {p.pattern} | {p.category} | {p.target_agent} | {p.rationale} |" for p in proposals]
    lines = [
        "| Pattern | Category | Agent | Rationale |",
        "|---|---|---|---|",
        *rows,
    ]
    return "\n".join(lines)
