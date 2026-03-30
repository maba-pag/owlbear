"""Pattern-detection analysis module for orchestrator audit events."""

from __future__ import annotations

import dataclasses
import json
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from owlbear.audit.models import CompletionEvent, DispatchEvent, audit_adapter

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Any

DEFAULT_WINDOW = timedelta(days=7)

_MIN_COMPLETIONS: int = 3
_ERROR_RATE_THRESHOLD: float = 0.4
_SLOW_AGENT_RATIO: int = 2
_MIN_REPEATED_FAILURES: int = 2


@dataclasses.dataclass(frozen=True)
class AnalysisProposal:
    """An immutable pattern-detection finding produced by a detector."""

    detector: str
    agent: str | None
    task_id: int | None
    severity: str
    message: str
    evidence: dict[str, Any]


def high_error_rate_detector(events: list[CompletionEvent]) -> list[AnalysisProposal]:
    """Fire when an agent has >= 40% failure rate with >= 3 completions."""
    by_agent: dict[str, list[CompletionEvent]] = defaultdict(list)
    for e in events:
        by_agent[e.agent].append(e)

    proposals: list[AnalysisProposal] = []
    for agent, completions in by_agent.items():
        if len(completions) < _MIN_COMPLETIONS:
            continue
        failures = sum(1 for c in completions if c.outcome == "failure")
        rate = failures / len(completions)
        if rate >= _ERROR_RATE_THRESHOLD:
            proposals.append(
                AnalysisProposal(
                    detector="high_error_rate",
                    agent=agent,
                    task_id=None,
                    severity="warning",
                    message=(
                        f"Agent {agent!r} has {rate:.0%} failure rate"
                        f" over {len(completions)} completions"
                    ),
                    evidence={
                        "failure_rate": rate,
                        "total": len(completions),
                        "failures": failures,
                    },
                )
            )
    return proposals


def slow_agent_detector(events: list[CompletionEvent]) -> list[AnalysisProposal]:
    """Fire when an agent's avg duration is > 2x the global average with >= 3 completions."""
    if not events:
        return []

    global_avg = sum(e.duration_ms for e in events) / len(events)

    by_agent: dict[str, list[CompletionEvent]] = defaultdict(list)
    for e in events:
        by_agent[e.agent].append(e)

    proposals: list[AnalysisProposal] = []
    for agent, completions in by_agent.items():
        if len(completions) < _MIN_COMPLETIONS:
            continue
        agent_avg = sum(c.duration_ms for c in completions) / len(completions)
        if global_avg > 0 and agent_avg / global_avg > _SLOW_AGENT_RATIO:
            ratio = agent_avg / global_avg
            proposals.append(
                AnalysisProposal(
                    detector="slow_agent",
                    agent=agent,
                    task_id=None,
                    severity="warning",
                    message=f"Agent {agent!r} avg duration is {ratio:.2f}x the global avg",
                    evidence={
                        "agent_avg_ms": agent_avg,
                        "global_avg_ms": global_avg,
                        "ratio": ratio,
                    },
                )
            )
    return proposals


def repeated_failure_detector(events: list[CompletionEvent]) -> list[AnalysisProposal]:
    """Fire when the same task_id accumulates >= 2 failures."""
    failures_by_task: dict[int, int] = defaultdict(int)
    for e in events:
        if e.outcome == "failure":
            failures_by_task[e.task_id] += 1

    proposals: list[AnalysisProposal] = []
    for task_id, count in failures_by_task.items():
        if count >= _MIN_REPEATED_FAILURES:
            proposals.append(
                AnalysisProposal(
                    detector="repeated_failure",
                    agent=None,
                    task_id=task_id,
                    severity="warning",
                    message=f"Task {task_id} has failed {count} times",
                    evidence={"failure_count": count},
                )
            )
    return proposals


def stale_dispatch_detector(
    events: list[DispatchEvent | CompletionEvent],
    now: datetime,
) -> list[AnalysisProposal]:
    """Fire for dispatches > 1h old that have no matching completion."""
    dispatches = [e for e in events if isinstance(e, DispatchEvent)]
    completed_keys = {
        (e.task_id, e.agent) for e in events if isinstance(e, CompletionEvent)
    }

    proposals: list[AnalysisProposal] = []
    for d in dispatches:
        if (d.task_id, d.agent) in completed_keys:
            continue
        dispatch_time = datetime.fromisoformat(d.timestamp)
        age = now - dispatch_time
        if age > timedelta(hours=1):
            proposals.append(
                AnalysisProposal(
                    detector="stale_dispatch",
                    agent=d.agent,
                    task_id=d.task_id,
                    severity="warning",
                    message=(
                        f"Dispatch for task {d.task_id} via {d.agent!r}"
                        " has been pending for over 1h"
                    ),
                    evidence={
                        "age_seconds": age.total_seconds(),
                        "dispatched_at": d.timestamp,
                    },
                )
            )
    return proposals


def analyze(
    audit_dir: Path,
    now: datetime | None = None,
    window: timedelta = DEFAULT_WINDOW,
) -> list[AnalysisProposal]:
    """Read all JSONL audit files in audit_dir, apply all detectors, return proposals."""
    if now is None:
        now = datetime.now(UTC)

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


def format_json(proposals: list[AnalysisProposal]) -> str:
    """Serialize proposals to a JSON array string."""
    return json.dumps([dataclasses.asdict(p) for p in proposals])


def format_markdown(proposals: list[AnalysisProposal]) -> str:
    """Format proposals as a Markdown table."""
    if not proposals:
        return "No analysis proposals."

    lines = [
        "| Detector | Agent | Task | Severity | Message |",
        "|---|---|---|---|---|",
    ]
    for p in proposals:
        agent = p.agent or "-"
        task = str(p.task_id) if p.task_id is not None else "-"
        lines.append(f"| {p.detector} | {agent} | {task} | {p.severity} | {p.message} |")
    return "\n".join(lines)
