"""Token-usage tracking — append-only JSONL persistence.

Records per-request usage (tokens, cost, premium requests) and provides
time-windowed querying and aggregation.  Follows the same
:class:`~owlbear.memory.session.SessionStore` pattern: ``TypeAdapter``
serialization, append-only JSONL, ``Path``-based constructor.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, TypeAdapter

if TYPE_CHECKING:
    from datetime import timedelta
    from pathlib import Path


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


_adapter: TypeAdapter[UsageRecord] = TypeAdapter(UsageRecord)


class UsageTracker:
    """Append-only JSONL store for :class:`UsageRecord`.

    Usage::

        tracker = UsageTracker(Path("~/.owlbear/usage.jsonl"))
        tracker.append(record)
        recent = tracker.query(timedelta(hours=1))
        totals = tracker.summary(timedelta(hours=24))
    """

    def __init__(self, path: Path) -> None:
        self._path = path

    @property
    def path(self) -> Path:
        """Location of the JSONL file."""
        return self._path

    # -- write ---------------------------------------------------------------

    def append(self, record: UsageRecord) -> None:
        """Serialize *record* and append it as a new JSONL line."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        line = _adapter.dump_json(record).decode("utf-8")
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    # -- read ----------------------------------------------------------------

    def load(self) -> list[UsageRecord]:
        """Deserialize all records from the JSONL file.

        Returns an empty list when the file doesn't exist or is empty.
        """
        if not self._path.exists():
            return []
        lines = self._path.read_text(encoding="utf-8").strip().splitlines()
        return [_adapter.validate_json(line) for line in lines if line]

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
