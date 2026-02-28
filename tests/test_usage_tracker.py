"""Tests for owlbear.memory.usage — UsageTracker JSONL persistence."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from owlbear.memory.usage import UsageRecord, UsageSummary, UsageTracker
from pydantic import TypeAdapter

_adapter: TypeAdapter[UsageRecord] = TypeAdapter(UsageRecord)


def _record(
    *,
    minutes_ago: int = 0,
    input_tokens: int = 500,
    output_tokens: int = 150,
    model: str = "gpt-4o",
) -> UsageRecord:
    """Build a UsageRecord with a timestamp *minutes_ago* from now."""
    ts = datetime.now(UTC) - timedelta(minutes=minutes_ago)
    return UsageRecord(
        timestamp=ts,
        model=model,
        provider="copilot",
        session_id="sess-001",
        requests=1,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )


def _write_jsonl(path: Path, records: list[UsageRecord]) -> None:
    """Manually write records as JSONL for test fixtures."""
    with path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(_adapter.dump_json(rec).decode("utf-8") + "\n")


# ---------------------------------------------------------------------------
# Append — writes one JSONL line
# ---------------------------------------------------------------------------


class TestUsageTrackerAppend:
    """UsageTracker.append() writes one JSON line per record."""

    def test_append_creates_file(self, tmp_path: Path) -> None:
        tracker = UsageTracker(tmp_path / "usage.jsonl")
        tracker.append(_record())
        assert tracker.path.exists()

    def test_append_writes_one_line(self, tmp_path: Path) -> None:
        tracker = UsageTracker(tmp_path / "usage.jsonl")
        tracker.append(_record())
        lines = tracker.path.read_text().strip().splitlines()
        assert len(lines) == 1

    def test_append_writes_valid_json(self, tmp_path: Path) -> None:
        tracker = UsageTracker(tmp_path / "usage.jsonl")
        tracker.append(_record())
        line = tracker.path.read_text().strip()
        data = json.loads(line)
        assert data["model"] == "gpt-4o"

    def test_append_multiple_records(self, tmp_path: Path) -> None:
        tracker = UsageTracker(tmp_path / "usage.jsonl")
        tracker.append(_record(input_tokens=100))
        tracker.append(_record(input_tokens=200))
        tracker.append(_record(input_tokens=300))
        lines = tracker.path.read_text().strip().splitlines()
        assert len(lines) == 3

    def test_append_creates_parent_dirs(self, tmp_path: Path) -> None:
        tracker = UsageTracker(tmp_path / "sub" / "dir" / "usage.jsonl")
        tracker.append(_record())
        assert tracker.path.exists()


# ---------------------------------------------------------------------------
# Load — returns list[UsageRecord]
# ---------------------------------------------------------------------------


class TestUsageTrackerLoad:
    """UsageTracker.load() reads all records from the JSONL file."""

    def test_load_returns_records(self, tmp_path: Path) -> None:
        p = tmp_path / "usage.jsonl"
        records = [_record(input_tokens=100), _record(input_tokens=200)]
        _write_jsonl(p, records)
        tracker = UsageTracker(p)
        loaded = tracker.load()
        assert len(loaded) == 2
        assert all(isinstance(r, UsageRecord) for r in loaded)

    def test_load_preserves_field_values(self, tmp_path: Path) -> None:
        p = tmp_path / "usage.jsonl"
        rec = _record(input_tokens=999, output_tokens=111, model="o1")
        _write_jsonl(p, [rec])
        tracker = UsageTracker(p)
        loaded = tracker.load()
        assert loaded[0].input_tokens == 999
        assert loaded[0].output_tokens == 111
        assert loaded[0].model == "o1"

    def test_load_empty_file_returns_empty_list(self, tmp_path: Path) -> None:
        p = tmp_path / "usage.jsonl"
        p.write_text("")
        tracker = UsageTracker(p)
        assert tracker.load() == []

    def test_load_nonexistent_file_returns_empty_list(self, tmp_path: Path) -> None:
        tracker = UsageTracker(tmp_path / "nope.jsonl")
        assert tracker.load() == []


# ---------------------------------------------------------------------------
# Query — filter by time window
# ---------------------------------------------------------------------------


class TestUsageTrackerQuery:
    """UsageTracker.query(timedelta) filters records by timestamp window."""

    def test_query_returns_recent_records(self, tmp_path: Path) -> None:
        p = tmp_path / "usage.jsonl"
        recent = _record(minutes_ago=5)
        old = _record(minutes_ago=120)
        _write_jsonl(p, [old, recent])
        tracker = UsageTracker(p)
        result = tracker.query(timedelta(hours=1))
        assert len(result) == 1
        assert result[0].input_tokens == recent.input_tokens

    def test_query_returns_all_within_window(self, tmp_path: Path) -> None:
        p = tmp_path / "usage.jsonl"
        records = [_record(minutes_ago=i) for i in range(5)]
        _write_jsonl(p, records)
        tracker = UsageTracker(p)
        result = tracker.query(timedelta(hours=1))
        assert len(result) == 5

    def test_query_excludes_old_records(self, tmp_path: Path) -> None:
        p = tmp_path / "usage.jsonl"
        old = _record(minutes_ago=1440)  # 24h ago
        _write_jsonl(p, [old])
        tracker = UsageTracker(p)
        result = tracker.query(timedelta(hours=1))
        assert len(result) == 0

    def test_query_empty_file_returns_empty(self, tmp_path: Path) -> None:
        tracker = UsageTracker(tmp_path / "nope.jsonl")
        assert tracker.query(timedelta(hours=1)) == []


# ---------------------------------------------------------------------------
# Summary — aggregate totals
# ---------------------------------------------------------------------------


class TestUsageTrackerSummary:
    """UsageTracker.summary(timedelta) returns UsageSummary with correct totals."""

    def test_summary_totals_tokens(self, tmp_path: Path) -> None:
        p = tmp_path / "usage.jsonl"
        r1 = _record(minutes_ago=5, input_tokens=100, output_tokens=50)
        r2 = _record(minutes_ago=10, input_tokens=200, output_tokens=100)
        _write_jsonl(p, [r1, r2])
        tracker = UsageTracker(p)
        summary = tracker.summary(timedelta(hours=1))
        assert isinstance(summary, UsageSummary)
        assert summary.total_input_tokens == 300
        assert summary.total_output_tokens == 150
        assert summary.total_tokens == 450

    def test_summary_counts_requests(self, tmp_path: Path) -> None:
        p = tmp_path / "usage.jsonl"
        records = [_record(minutes_ago=i) for i in range(3)]
        _write_jsonl(p, records)
        tracker = UsageTracker(p)
        summary = tracker.summary(timedelta(hours=1))
        assert summary.total_requests == 3

    def test_summary_record_count(self, tmp_path: Path) -> None:
        p = tmp_path / "usage.jsonl"
        records = [_record(minutes_ago=i) for i in range(4)]
        _write_jsonl(p, records)
        tracker = UsageTracker(p)
        summary = tracker.summary(timedelta(hours=1))
        assert summary.record_count == 4

    def test_summary_empty_returns_zero_totals(self, tmp_path: Path) -> None:
        tracker = UsageTracker(tmp_path / "nope.jsonl")
        summary = tracker.summary(timedelta(hours=1))
        assert summary.total_input_tokens == 0
        assert summary.total_output_tokens == 0
        assert summary.total_tokens == 0
        assert summary.total_requests == 0
        assert summary.record_count == 0

    def test_summary_respects_time_window(self, tmp_path: Path) -> None:
        p = tmp_path / "usage.jsonl"
        recent = _record(minutes_ago=5, input_tokens=100, output_tokens=50)
        old = _record(minutes_ago=120, input_tokens=999, output_tokens=999)
        _write_jsonl(p, [old, recent])
        tracker = UsageTracker(p)
        summary = tracker.summary(timedelta(hours=1))
        assert summary.total_input_tokens == 100
        assert summary.record_count == 1
