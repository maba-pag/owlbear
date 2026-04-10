"""Analysis package for orchestrator audit pattern detection."""

from __future__ import annotations

from owlbear_orchestrator.analysis.analyze import analyze
from owlbear_orchestrator.analysis.detectors import (
    high_error_rate_detector,
    repeated_failure_detector,
    slow_agent_detector,
    stale_dispatch_detector,
)
from owlbear_orchestrator.analysis.formatters import format_json, format_markdown
from owlbear_orchestrator.analysis.models import AnalysisProposal

__all__ = [
    "AnalysisProposal",
    "analyze",
    "format_json",
    "format_markdown",
    "high_error_rate_detector",
    "repeated_failure_detector",
    "slow_agent_detector",
    "stale_dispatch_detector",
]
