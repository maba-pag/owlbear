"""analyze() entrypoint: reads audit JSONL files and returns AnalysisProposals."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from owlbear.audit.models import CompletionEvent, DispatchEvent, audit_adapter
from owlbear_orchestrator.analysis.detectors import (
    high_error_rate_detector,
    repeated_failure_detector,
    slow_agent_detector,
    stale_dispatch_detector,
)

if TYPE_CHECKING:
    from pathlib import Path

    from owlbear_orchestrator.analysis.models import AnalysisProposal

DEFAULT_WINDOW = timedelta(days=7)


def analyze(
    audit_dir: Path,
    window: timedelta | None = None,
    now: datetime | None = None,
) -> list[AnalysisProposal]:
    """Read all JSONL audit files in audit_dir, apply all detectors, return proposals."""
    if now is None:
        now = datetime.now(UTC)
    if window is None:
        window = DEFAULT_WINDOW

    cutoff = now - window
    all_events: list[DispatchEvent | CompletionEvent] = []

    for jsonl_path in sorted(audit_dir.glob("*.jsonl")):
        for line in jsonl_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            raw = json.loads(stripped)
            event = audit_adapter.validate_python(raw)
            ts = datetime.fromisoformat(event.timestamp)
            if ts >= cutoff:
                all_events.append(event)

    completions = [e for e in all_events if isinstance(e, CompletionEvent)]

    proposals: list[AnalysisProposal] = []
    proposals.extend(high_error_rate_detector(completions))
    proposals.extend(slow_agent_detector(completions))
    proposals.extend(repeated_failure_detector(completions))
    proposals.extend(stale_dispatch_detector(all_events, now=now))
    return proposals
