"""Pattern detector functions for orchestrator audit events."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta

from owlbear.audit.models import CompletionEvent, DispatchEvent
from owlbear_orchestrator.analysis.models import AnalysisProposal

# ---------------------------------------------------------------------------
# Threshold constants — module-level named constants for tuning
# ---------------------------------------------------------------------------

ERROR_RATE_THRESHOLD: float = 0.4
MIN_DISPATCHES: int = 3
SLOW_FACTOR: int = 2
STALE_THRESHOLD: timedelta = timedelta(hours=1)
MIN_REPEATED_FAILURES: int = 2


def high_error_rate_detector(events: list[CompletionEvent]) -> list[AnalysisProposal]:
    """Fire when an agent has >= 40% failure rate with >= 3 completions."""
    by_agent: dict[str, list[CompletionEvent]] = defaultdict(list)
    for e in events:
        by_agent[e.agent].append(e)

    proposals: list[AnalysisProposal] = []
    for agent, completions in by_agent.items():
        if len(completions) < MIN_DISPATCHES:
            continue
        failures = sum(1 for c in completions if c.outcome == "failure")
        rate = failures / len(completions)
        if rate >= ERROR_RATE_THRESHOLD:
            proposals.append(
                AnalysisProposal(
                    target_agent=agent,
                    category="reliability",
                    pattern="high_error_rate",
                    rationale=(
                        f"Agent {agent!r} has {rate:.0%} failure rate over {len(completions)} completions"
                    ),
                    evidence={
                        "failure_rate": rate,
                        "total": len(completions),
                        "failures": failures,
                    },
                    suggested_action="Investigate agent error logs and reduce failure rate",
                )
            )
    return proposals


def slow_agent_detector(events: list[CompletionEvent]) -> list[AnalysisProposal]:
    """Fire when an agent's avg duration is > 2x the other-agents average with >= 3 completions."""
    if not events:
        return []

    by_agent: dict[str, list[CompletionEvent]] = defaultdict(list)
    for e in events:
        by_agent[e.agent].append(e)

    proposals: list[AnalysisProposal] = []
    for agent, completions in by_agent.items():
        if len(completions) < MIN_DISPATCHES:
            continue
        agent_avg = sum(c.duration_ms for c in completions) / len(completions)
        other_events = [e for e in events if e.agent != agent]
        if not other_events:
            continue
        other_avg = sum(e.duration_ms for e in other_events) / len(other_events)
        if other_avg > 0 and agent_avg / other_avg > SLOW_FACTOR:
            ratio = agent_avg / other_avg
            proposals.append(
                AnalysisProposal(
                    target_agent=agent,
                    category="performance",
                    pattern="slow_agent",
                    rationale=f"Agent {agent!r} avg duration is {ratio:.2f}x the other-agents avg",
                    evidence={
                        "agent_avg_ms": agent_avg,
                        "other_avg_ms": other_avg,
                        "ratio": ratio,
                    },
                    suggested_action="Review agent implementation for performance bottlenecks",
                )
            )
    return proposals


def repeated_failure_detector(events: list[CompletionEvent]) -> list[AnalysisProposal]:
    """Fire when the same task_id accumulates >= 2 failure CompletionEvents."""
    failures_by_task: dict[int, list[CompletionEvent]] = defaultdict(list)
    for e in events:
        if e.outcome == "failure":
            failures_by_task[e.task_id].append(e)

    proposals: list[AnalysisProposal] = []
    for task_id, failure_events in failures_by_task.items():
        count = len(failure_events)
        if count >= MIN_REPEATED_FAILURES:
            agent_counts: dict[str, int] = defaultdict(int)
            for fe in failure_events:
                agent_counts[fe.agent] += 1
            primary_agent = max(agent_counts, key=lambda a: agent_counts[a])
            proposals.append(
                AnalysisProposal(
                    target_agent=primary_agent,
                    category="reliability",
                    pattern="repeated_failure",
                    rationale=f"Task {task_id} has failed {count} times",
                    evidence={"failure_count": count, "task_id": task_id},
                    suggested_action="Review task AC and agent implementation for task causes",
                )
            )
    return proposals


def stale_dispatch_detector(
    events: list[DispatchEvent | CompletionEvent],
    now: datetime,
) -> list[AnalysisProposal]:
    """Fire for dispatches > 1h old with no matching completion (task_id + agent)."""
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
        if age > STALE_THRESHOLD:
            proposals.append(
                AnalysisProposal(
                    target_agent=d.agent,
                    category="stability",
                    pattern="stale_dispatch",
                    rationale=(
                        f"Dispatch for task {d.task_id} via {d.agent!r} has been pending for over 1h"
                    ),
                    evidence={
                        "age_seconds": age.total_seconds(),
                        "dispatched_at": d.timestamp,
                        "task_id": d.task_id,
                    },
                    suggested_action="Check if the agent is still running or restart the dispatch",
                )
            )
    return proposals
