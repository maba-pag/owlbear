"""Generate review-only self-improvement proposals from observability metrics."""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from datetime import timedelta

    from owlbear.core.observability import EventStore, ObservabilityEvent

_MIN_TOTAL_CALLS = 5
_MIN_TOOL_CALLS = 3
_ERROR_RATE_THRESHOLD = 0.5
_HIGH_LATENCY_THRESHOLD_MS = 3000.0


class ImprovementProposal(BaseModel):
    """Review artifact describing a proposed improvement from runtime metrics.

    These proposals are intentionally descriptive only. They do not trigger
    any autonomous writes, prompts, or code mutations by themselves.
    """

    model_config = ConfigDict(frozen=True)

    target_agent: str
    change_category: str
    rationale: str
    evidence: str | dict[str, Any]
    suggested_change: str


def generate_proposals(
    store: EventStore,
    window: timedelta | None = None,
) -> list[ImprovementProposal]:
    """Return review-only proposals inferred from observability aggregates.

    Args:
        store: Event source queried via existing ``EventStore`` APIs.
        window: Optional lookback duration; ``None`` means all available events.

    Returns:
        List of proposal artifacts. Returns an empty list when the data has
        insufficient signal or does not cross proposal thresholds.
    """
    summary = store.summary(window)
    if summary["total_tool_calls"] < _MIN_TOTAL_CALLS:
        return []

    tool_stats = store.tool_stats(window)
    if not tool_stats:
        return []

    events = _window_events(store, window)
    proposals: list[ImprovementProposal] = []

    for tool_name, stats in tool_stats.items():
        call_count = stats["call_count"]
        if call_count < _MIN_TOOL_CALLS:
            continue

        error_count = stats["error_count"]
        error_rate = error_count / call_count if call_count else 0.0

        if error_rate >= _ERROR_RATE_THRESHOLD:
            proposals.append(
                ImprovementProposal(
                    target_agent=_target_agent(events, tool_name),
                    change_category="reliability",
                    rationale=(
                        f"Tool '{tool_name}' failed {error_count} of {call_count} "
                        f"calls ({error_rate:.0%})."
                    ),
                    evidence={
                        "tool_name": tool_name,
                        "error_count": error_count,
                        "call_count": call_count,
                        "error_rate": round(error_rate, 3),
                    },
                    suggested_change=(
                        "Investigate recurring failures for this tool, add targeted "
                        "guardrails/retry handling, and document a safer invocation "
                        "pattern for the owning agent."
                    ),
                )
            )
            continue

        avg_duration_ms = stats["avg_duration_ms"]
        if avg_duration_ms >= _HIGH_LATENCY_THRESHOLD_MS:
            proposals.append(
                ImprovementProposal(
                    target_agent=_target_agent(events, tool_name),
                    change_category="performance",
                    rationale=(
                        f"Tool '{tool_name}' has high average latency "
                        f"({avg_duration_ms:.1f} ms across {call_count} calls)."
                    ),
                    evidence={
                        "tool_name": tool_name,
                        "avg_duration_ms": round(avg_duration_ms, 1),
                        "call_count": call_count,
                        "window_avg_tool_duration_ms": round(
                            float(summary["avg_tool_duration_ms"]),
                            1,
                        ),
                    },
                    suggested_change=(
                        "Profile this tool path and reduce latency by simplifying "
                        "inputs, caching repeatable work, or replacing slow steps "
                        "with cheaper alternatives."
                    ),
                )
            )

    return proposals


def _window_events(store: EventStore, window: timedelta | None) -> list[ObservabilityEvent]:
    """Load events from the requested window using existing EventStore APIs."""
    return store.load() if window is None else store.query(window)


def _target_agent(events: list[ObservabilityEvent], tool_name: str) -> str:
    """Return the most common agent observed for ``tool_name`` calls."""
    agents = [
        event.agent_name
        for event in events
        if event.event_type == "post_tool_use"
        and event.tool_name == tool_name
        and event.agent_name
    ]
    if not agents:
        return "builder"
    return Counter(agents).most_common(1)[0][0]


__all__ = ["ImprovementProposal", "generate_proposals"]
