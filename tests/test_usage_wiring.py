"""Tests for UsageTracker secondary wiring — TDD RED phase (#846).

AC coverage:
1. UsageRecord.operation field (default 'turn', backward compat)
2. record_agent_usage() creates correct UsageRecord and appends to tracker
3. record_agent_usage() is a no-op when tracker is None
4. record_agent_usage() enriches estimated_cost_usd and premium_requests
5. SummarizingCondenser records UsageRecord with operation='condenser'
6. EntityExtractor records UsageRecord with operation='entity_extraction'
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from owlbear.memory.usage import UsageRecord, UsageTracker

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_usage_result(
    input_tokens: int = 10,
    output_tokens: int = 5,
    requests: int = 1,
) -> MagicMock:
    """Return a mock pydantic_ai RunResult with a usage() method."""
    usage = MagicMock()
    usage.input_tokens = input_tokens
    usage.output_tokens = output_tokens
    usage.cache_read_tokens = 0
    usage.cache_write_tokens = 0
    usage.requests = requests
    usage.tool_calls = 0

    result = MagicMock()
    result.usage.return_value = usage
    return result


def _make_tracker(tmp_path: Path) -> UsageTracker:
    return UsageTracker(tmp_path / "usage.jsonl")


# ===========================================================================
# AC1 — UsageRecord.operation field
# ===========================================================================


class TestFromAC_UsageRecordOperationField:
    """AC1: UsageRecord accepts operation field with default 'turn'."""

    def test_operation_field_default_is_turn(self) -> None:
        """UsageRecord created without operation should default to 'turn'."""
        record = UsageRecord(
            timestamp=datetime.now(UTC),
            session_id="test-session",
            model="gpt-4o",
            provider="copilot",
            input_tokens=10,
            output_tokens=5,
            requests=1,
        )
        assert record.operation == "turn"

    def test_operation_field_accepts_custom_value(self) -> None:
        """UsageRecord.operation can be set to any string value."""
        record = UsageRecord(
            timestamp=datetime.now(UTC),
            session_id="test-session",
            model="gpt-4o",
            provider="copilot",
            input_tokens=10,
            output_tokens=5,
            requests=1,
            operation="condenser",
        )
        assert record.operation == "condenser"

    def test_backward_compat_jsonl_without_operation(self) -> None:
        """Deserializing a JSONL record that lacks 'operation' remains valid."""
        raw = {
            "timestamp": datetime.now(UTC).isoformat(),
            "session_id": "old-session",
            "model": "gpt-4o",
            "provider": "copilot",
            "input_tokens": 10,
            "output_tokens": 5,
            "requests": 1,
        }
        record = UsageRecord.model_validate(raw)
        assert record.operation == "turn"

    def test_operation_field_serializes(self) -> None:
        """operation field is included in model_dump output."""
        record = UsageRecord(
            timestamp=datetime.now(UTC),
            session_id="s",
            model="m",
            provider="p",
            input_tokens=1,
            output_tokens=1,
            requests=1,
            operation="entity_extraction",
        )
        data = record.model_dump()
        assert "operation" in data
        assert data["operation"] == "entity_extraction"


# ===========================================================================
# AC2, AC3, AC4 — record_agent_usage()
# ===========================================================================


class TestFromAC_RecordAgentUsage:
    """AC2-4: record_agent_usage() helper in memory.usage."""

    def test_import_from_memory_usage(self) -> None:
        """record_agent_usage must be importable from owlbear.memory.usage."""
        from owlbear.memory.usage import record_agent_usage  # noqa: F401 — existence check

    def test_creates_record_appended_to_tracker(self, tmp_path: Path) -> None:
        """AC2: creates a UsageRecord and appends it to the tracker."""
        from owlbear.memory.usage import record_agent_usage

        tracker = _make_tracker(tmp_path)
        result = _make_usage_result()

        record_agent_usage(
            tracker=tracker,
            result=result,
            model="gpt-4o",
            provider="copilot",
            session_id="background:condenser",
            operation="condenser",
        )

        records = tracker.load()
        assert len(records) == 1
        rec = records[0]
        assert rec.model == "gpt-4o"
        assert rec.provider == "copilot"
        assert rec.session_id == "background:condenser"
        assert rec.operation == "condenser"
        assert rec.input_tokens == 10
        assert rec.output_tokens == 5

    def test_noop_when_tracker_is_none(self) -> None:
        """AC3: record_agent_usage is a silent no-op when tracker is None."""
        from owlbear.memory.usage import record_agent_usage

        result = _make_usage_result()
        # Must not raise anything
        record_agent_usage(
            tracker=None,
            result=result,
            model="gpt-4o",
            provider="copilot",
            session_id="background:entity_extraction",
            operation="entity_extraction",
        )

    def test_enriches_estimated_cost_usd(self, tmp_path: Path) -> None:
        """AC4: record_agent_usage populates estimated_cost_usd via calc_estimated_cost."""
        from owlbear.memory.usage import record_agent_usage

        tracker = _make_tracker(tmp_path)
        result = _make_usage_result()

        with patch(
            "owlbear.memory.usage_cost.calc_estimated_cost",
            return_value=0.0042,
        ):
            record_agent_usage(
                tracker=tracker,
                result=result,
                model="gpt-4o",
                provider="copilot",
                session_id="background:condenser",
                operation="condenser",
            )

        records = tracker.load()
        assert len(records) == 1
        assert records[0].estimated_cost_usd == 0.0042

    def test_enriches_premium_requests(self, tmp_path: Path) -> None:
        """AC4: record_agent_usage populates premium_requests via get_premium_requests."""
        from owlbear.memory.usage import record_agent_usage

        tracker = _make_tracker(tmp_path)
        result = _make_usage_result()

        with (
            patch(
                "owlbear.memory.usage_cost.calc_estimated_cost",
                return_value=None,
            ),
            patch(
                "owlbear.providers.copilot_multipliers.get_premium_requests",
                return_value=2.5,
            ),
        ):
            record_agent_usage(
                tracker=tracker,
                result=result,
                model="gpt-4o",
                provider="copilot",
                session_id="background:condenser",
                operation="condenser",
            )

        records = tracker.load()
        assert len(records) == 1
        assert records[0].premium_requests == 2.5

    def test_operation_stored_in_record(self, tmp_path: Path) -> None:
        """AC2: operation argument is stored on the created UsageRecord."""
        from owlbear.memory.usage import record_agent_usage

        tracker = _make_tracker(tmp_path)
        result = _make_usage_result()

        record_agent_usage(
            tracker=tracker,
            result=result,
            model="gpt-4o",
            provider="copilot",
            session_id="background:entity_extraction",
            operation="entity_extraction",
        )

        records = tracker.load()
        assert records[0].operation == "entity_extraction"

    def test_enrichment_failure_does_not_raise(self, tmp_path: Path) -> None:
        """AC4: enrichment errors are swallowed (mirrors existing _record_usage pattern)."""
        from owlbear.memory.usage import record_agent_usage

        tracker = _make_tracker(tmp_path)
        result = _make_usage_result()

        with patch(
            "owlbear.memory.usage_cost.calc_estimated_cost",
            side_effect=RuntimeError("price lookup failed"),
        ):
            # Must not raise — mirrors try/except in _record_usage
            record_agent_usage(
                tracker=tracker,
                result=result,
                model="gpt-4o",
                provider="copilot",
                session_id="background:condenser",
                operation="condenser",
            )


# ===========================================================================
# AC5 — SummarizingCondenser records usage
# ===========================================================================


class TestFromAC_CondenserUsageWiring:
    """AC5: SummarizingCondenser records UsageRecord with operation='condenser'."""

    def test_condenser_constructor_accepts_tracker_and_provider(self, tmp_path: Path) -> None:
        """SummarizingCondenser accepts tracker and provider constructor params."""
        from owlbear.core.condenser import SummarizingCondenser

        tracker = _make_tracker(tmp_path)
        condenser = SummarizingCondenser(
            model="gpt-4o",
            tracker=tracker,
            provider="copilot",
        )
        assert condenser is not None

    @pytest.mark.asyncio
    async def test_condenser_records_operation_condenser(self, tmp_path: Path) -> None:
        """AC5: after condensation appends record with operation='condenser'."""
        from pydantic_ai.messages import ModelRequest, UserPromptPart

        from owlbear.core.condenser import SummarizingCondenser

        tracker = _make_tracker(tmp_path)
        condenser = SummarizingCondenser(
            max_events=2,
            keep_first=1,
            target_size=2,
            model="test",
            tracker=tracker,
            provider="copilot",
        )

        # Build a message list that triggers condensation (len > max_events)
        messages = [ModelRequest(parts=[UserPromptPart(content=f"msg {i}")]) for i in range(4)]
        ctx = MagicMock()

        with (
            patch.object(condenser, "_summarize", new_callable=AsyncMock, return_value="summary"),
            patch("owlbear.core.condenser.record_agent_usage") as mock_record,
        ):
            await condenser(ctx, messages)
            mock_record.assert_called_once()
            call_kwargs = mock_record.call_args
            # Verify operation='condenser' was passed
            assert call_kwargs.kwargs.get("operation") == "condenser" or (
                len(call_kwargs.args) >= 6 and call_kwargs.args[5] == "condenser"
            )

    @pytest.mark.asyncio
    async def test_condenser_no_record_when_no_tracker(self) -> None:
        """AC5: no UsageRecord created when condenser has no tracker."""
        from pydantic_ai.messages import ModelRequest, UserPromptPart

        from owlbear.core.condenser import SummarizingCondenser

        condenser = SummarizingCondenser(
            max_events=2,
            keep_first=1,
            target_size=2,
            model="test",
            tracker=None,
        )
        messages = [ModelRequest(parts=[UserPromptPart(content=f"msg {i}")]) for i in range(4)]
        ctx = MagicMock()

        with (
            patch.object(condenser, "_summarize", new_callable=AsyncMock, return_value="summary"),
            patch("owlbear.core.condenser.record_agent_usage") as mock_record,
        ):
            await condenser(ctx, messages)
            mock_record.assert_not_called()

    @pytest.mark.asyncio
    async def test_condenser_no_record_when_below_threshold(self, tmp_path: Path) -> None:
        """Edge: no condensation (below threshold) means no UsageRecord appended."""
        from pydantic_ai.messages import ModelRequest, UserPromptPart

        from owlbear.core.condenser import SummarizingCondenser

        tracker = _make_tracker(tmp_path)
        condenser = SummarizingCondenser(
            max_events=100,
            model="test",
            tracker=tracker,
            provider="copilot",
        )
        messages = [ModelRequest(parts=[UserPromptPart(content="only one")])]
        ctx = MagicMock()

        await condenser(ctx, messages)

        assert tracker.load() == []


# ===========================================================================
# AC6 — EntityExtractor records usage
# ===========================================================================


class TestFromAC_EntityExtractorUsageWiring:
    """AC6: EntityExtractor records UsageRecord with operation='entity_extraction'."""

    def test_extractor_constructor_accepts_tracker_and_provider(self, tmp_path: Path) -> None:
        """EntityExtractor accepts tracker and provider constructor params."""
        from owlbear.memory.knowledge.extractor import EntityExtractor

        tracker = _make_tracker(tmp_path)
        extractor = EntityExtractor(
            model="test",
            tracker=tracker,
            provider="copilot",
        )
        assert extractor is not None

    @pytest.mark.asyncio
    async def test_extractor_records_operation_entity_extraction(self, tmp_path: Path) -> None:
        """AC6: after extraction appends record with operation='entity_extraction'."""
        from owlbear.memory.knowledge.extractor import EntityExtractor, ExtractionResult

        tracker = _make_tracker(tmp_path)
        extractor = EntityExtractor(
            model="test",
            tracker=tracker,
            provider="copilot",
        )

        mock_run_result = MagicMock()
        mock_run_result.output = ExtractionResult()
        mock_run_result.usage.return_value = MagicMock(
            input_tokens=5,
            output_tokens=3,
            cache_read_tokens=0,
            cache_write_tokens=0,
            requests=1,
            tool_calls=0,
        )

        mock_run = AsyncMock(return_value=mock_run_result)
        with (
            patch.object(extractor._agent, "run", mock_run),
            patch("owlbear.memory.knowledge.extractor.record_agent_usage") as mock_record,
        ):
            await extractor.extract("some text")
            mock_record.assert_called_once()
            call_kwargs = mock_record.call_args
            assert call_kwargs.kwargs.get("operation") == "entity_extraction" or (
                len(call_kwargs.args) >= 6 and call_kwargs.args[5] == "entity_extraction"
            )

    @pytest.mark.asyncio
    async def test_extractor_no_record_when_no_tracker(self) -> None:
        """AC6: no UsageRecord when extractor has no tracker."""
        from owlbear.memory.knowledge.extractor import EntityExtractor, ExtractionResult

        extractor = EntityExtractor(model="test", tracker=None)

        mock_run_result = MagicMock()
        mock_run_result.output = ExtractionResult()
        mock_run_result.usage.return_value = MagicMock(
            input_tokens=5,
            output_tokens=3,
            cache_read_tokens=0,
            cache_write_tokens=0,
            requests=1,
            tool_calls=0,
        )

        mock_run = AsyncMock(return_value=mock_run_result)
        with (
            patch.object(extractor._agent, "run", mock_run),
            patch("owlbear.memory.knowledge.extractor.record_agent_usage") as mock_record,
        ):
            await extractor.extract("some text")
            mock_record.assert_not_called()

    @pytest.mark.asyncio
    async def test_extractor_no_record_on_empty_text(self, tmp_path: Path) -> None:
        """Edge: empty/whitespace text returns early — no usage recorded."""
        from owlbear.memory.knowledge.extractor import EntityExtractor

        tracker = _make_tracker(tmp_path)
        extractor = EntityExtractor(
            model="test",
            tracker=tracker,
            provider="copilot",
        )

        await extractor.extract("")
        assert tracker.load() == []
