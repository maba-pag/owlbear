"""Token-usage tracking — append-only JSONL persistence.

Records per-request usage (tokens, cost, premium requests) and provides
time-windowed querying and aggregation.  Follows the same
:class:`~owlbear.memory.session.SessionStore` pattern: ``TypeAdapter``
serialization, append-only JSONL, ``Path``-based constructor.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel

from owlbear.core.jsonl_store import JsonlStore

if TYPE_CHECKING:
    from datetime import timedelta
    from pathlib import Path

    from pydantic_ai.models import Model

_logger = logging.getLogger(__name__)


class UsageRecord(BaseModel):
    """A single LLM usage observation."""

    timestamp: datetime
    session_id: str
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    requests: int
    tool_calls: int = 0
    estimated_cost_usd: float | None = None
    premium_requests: float | None = None
    operation: str = "turn"

    @property
    def total_tokens(self) -> int:
        """Sum of input and output tokens."""
        return self.input_tokens + self.output_tokens


class UsageSummary(BaseModel):
    """Aggregated usage statistics over a time window."""

    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    total_requests: int = 0
    total_cost_usd: float | None = None
    total_premium_requests: float | None = None
    record_count: int = 0
    models: list[str] = []


class UsageTracker(JsonlStore[UsageRecord]):
    """Append-only JSONL store for :class:`UsageRecord`.

    Usage::

        tracker = UsageTracker(Path("~/.owlbear/usage.jsonl"))
        tracker.append(record)
        recent = tracker.query(timedelta(hours=1))
        totals = tracker.summary(timedelta(hours=24))
    """

    def __init__(self, path: Path) -> None:
        super().__init__(path, UsageRecord)

    # -- query ---------------------------------------------------------------

    def query(self, window: timedelta) -> list[UsageRecord]:
        """Return records whose timestamp falls within *window* from now."""
        cutoff = datetime.now(UTC) - window
        return [r for r in self.load() if r.timestamp >= cutoff]

    # -- aggregation ---------------------------------------------------------

    def summary(self, window: timedelta | None = None) -> UsageSummary:
        """Aggregate records within *window* (``None`` = all records)."""
        records = self.load() if window is None else self.query(window)

        if not records:
            return UsageSummary()

        total_cost: float | None = None
        total_premium: float | None = None

        for r in records:
            if r.estimated_cost_usd is not None:
                total_cost = (total_cost or 0.0) + r.estimated_cost_usd
            if r.premium_requests is not None:
                total_premium = (total_premium or 0.0) + r.premium_requests

        models = sorted({r.model for r in records})

        return UsageSummary(
            total_input_tokens=sum(r.input_tokens for r in records),
            total_output_tokens=sum(r.output_tokens for r in records),
            total_tokens=sum(r.total_tokens for r in records),
            total_requests=sum(r.requests for r in records),
            total_cost_usd=total_cost,
            total_premium_requests=total_premium,
            record_count=len(records),
            models=models,
        )


def record_agent_usage(  # noqa: PLR0913
    *,
    tracker: UsageTracker | None,
    result: object,
    model: str | Model,
    provider: str,
    session_id: str,
    operation: str = "turn",
) -> None:
    """Append a :class:`UsageRecord` from *result* to *tracker*.

    A silent no-op when *tracker* is ``None``.  Cost-enrichment errors are
    swallowed so callers are never disrupted by pricing-lookup failures.
    """
    if tracker is None:
        return

    try:
        model_name = model if isinstance(model, str) else getattr(model, "model_name", str(model))
        usage = result.usage()

        estimated_cost: float | None = None
        premium: float | None = None
        try:
            from owlbear.memory.usage_cost import calc_estimated_cost  # noqa: PLC0415

            estimated_cost = calc_estimated_cost(
                model_name,
                provider,
                usage.input_tokens or 0,
                usage.output_tokens or 0,
            )
            if provider == "copilot":
                from owlbear.providers.copilot_multipliers import (  # noqa: PLC0415
                    get_premium_requests,
                )

                premium = get_premium_requests(model_name)
        except Exception:  # noqa: BLE001
            _logger.warning("Usage enrichment unavailable", exc_info=True)

        record = UsageRecord(
            timestamp=datetime.now(UTC),
            session_id=session_id,
            model=model_name,
            provider=provider,
            input_tokens=usage.input_tokens or 0,
            output_tokens=usage.output_tokens or 0,
            cache_read_tokens=usage.cache_read_tokens or 0,
            cache_write_tokens=usage.cache_write_tokens or 0,
            requests=usage.requests or 0,
            tool_calls=usage.tool_calls or 0,
            estimated_cost_usd=estimated_cost,
            premium_requests=premium,
            operation=operation,
        )
        tracker.append(record)
    except Exception:  # noqa: BLE001
        _logger.warning("Failed to record usage", exc_info=True)
