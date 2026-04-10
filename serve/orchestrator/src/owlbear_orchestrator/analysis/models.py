"""AnalysisProposal Pydantic model for pattern-detection findings."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class AnalysisProposal(BaseModel):
    """An immutable pattern-detection finding produced by a detector."""

    model_config = ConfigDict(frozen=True)

    target_agent: str
    category: str
    pattern: str
    rationale: str
    evidence: dict[str, Any]
    suggested_action: str
