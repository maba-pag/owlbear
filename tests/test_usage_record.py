"""Tests for owlbear.memory.usage — UsageRecord data model."""

from __future__ import annotations

from datetime import UTC, datetime

from owlbear.memory.usage import UsageRecord
from pydantic import TypeAdapter


def _sample_record(**overrides: object) -> UsageRecord:
    """Build a UsageRecord with sensible defaults, overridable per-field."""
    defaults: dict[str, object] = {
        "timestamp": datetime(2026, 2, 27, 12, 0, 0, tzinfo=UTC),
        "model": "gpt-4o",
        "provider": "copilot",
        "session_id": "sess-001",
        "requests": 1,
        "input_tokens": 500,
        "output_tokens": 150,
    }
    defaults.update(overrides)
    return UsageRecord(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Construction — all fields
# ---------------------------------------------------------------------------


class TestUsageRecordConstruction:
    """UsageRecord can be constructed with all required and optional fields."""

    def test_create_with_required_fields(self) -> None:
        rec = _sample_record()
        assert rec.model == "gpt-4o"
        assert rec.provider == "copilot"
        assert rec.session_id == "sess-001"
        assert rec.requests == 1
        assert rec.input_tokens == 500
        assert rec.output_tokens == 150

    def test_timestamp_stored(self) -> None:
        ts = datetime(2026, 2, 27, 12, 0, 0, tzinfo=UTC)
        rec = _sample_record(timestamp=ts)
        assert rec.timestamp == ts

    def test_create_with_all_optional_fields(self) -> None:
        rec = _sample_record(
            cache_write_tokens=10,
            cache_read_tokens=20,
            tool_calls=3,
            estimated_cost_usd=0.005,
            premium_requests=1.0,
        )
        assert rec.cache_write_tokens == 10
        assert rec.cache_read_tokens == 20
        assert rec.tool_calls == 3
        assert rec.estimated_cost_usd == 0.005
        assert rec.premium_requests == 1.0


# ---------------------------------------------------------------------------
# Optional field defaults
# ---------------------------------------------------------------------------


class TestUsageRecordDefaults:
    """Optional fields default to None or zero as appropriate."""

    def test_estimated_cost_defaults_to_none(self) -> None:
        rec = _sample_record()
        assert rec.estimated_cost_usd is None

    def test_premium_requests_defaults_to_none(self) -> None:
        rec = _sample_record()
        assert rec.premium_requests is None

    def test_cache_tokens_default_to_zero(self) -> None:
        rec = _sample_record()
        assert rec.cache_write_tokens == 0
        assert rec.cache_read_tokens == 0

    def test_tool_calls_default_to_zero(self) -> None:
        rec = _sample_record()
        assert rec.tool_calls == 0


# ---------------------------------------------------------------------------
# Computed property: total_tokens
# ---------------------------------------------------------------------------


class TestUsageRecordTotalTokens:
    """total_tokens is a computed property: input_tokens + output_tokens."""

    def test_total_tokens_equals_sum(self) -> None:
        rec = _sample_record(input_tokens=500, output_tokens=150)
        assert rec.total_tokens == 650

    def test_total_tokens_zero_when_both_zero(self) -> None:
        rec = _sample_record(input_tokens=0, output_tokens=0)
        assert rec.total_tokens == 0

    def test_total_tokens_large_values(self) -> None:
        rec = _sample_record(input_tokens=100_000, output_tokens=50_000)
        assert rec.total_tokens == 150_000


# ---------------------------------------------------------------------------
# TypeAdapter JSON serialization roundtrip
# ---------------------------------------------------------------------------

_adapter: TypeAdapter[UsageRecord] = TypeAdapter(UsageRecord)


class TestUsageRecordSerialization:
    """UsageRecord survives a JSON serialize → deserialize roundtrip."""

    def test_json_roundtrip_required_fields(self) -> None:
        rec = _sample_record()
        json_bytes = _adapter.dump_json(rec)
        restored = _adapter.validate_json(json_bytes)
        assert restored.model == rec.model
        assert restored.input_tokens == rec.input_tokens
        assert restored.output_tokens == rec.output_tokens
        assert restored.timestamp == rec.timestamp

    def test_json_roundtrip_with_optional_fields(self) -> None:
        rec = _sample_record(estimated_cost_usd=0.0123, premium_requests=2.0)
        json_bytes = _adapter.dump_json(rec)
        restored = _adapter.validate_json(json_bytes)
        assert restored.estimated_cost_usd == rec.estimated_cost_usd
        assert restored.premium_requests == rec.premium_requests

    def test_json_roundtrip_preserves_total_tokens(self) -> None:
        rec = _sample_record(input_tokens=300, output_tokens=200)
        json_bytes = _adapter.dump_json(rec)
        restored = _adapter.validate_json(json_bytes)
        assert restored.total_tokens == 500

    def test_json_bytes_is_valid_utf8(self) -> None:
        rec = _sample_record()
        json_bytes = _adapter.dump_json(rec)
        text = json_bytes.decode("utf-8")
        assert '"model"' in text
        assert '"gpt-4o"' in text
