"""Tests for usage tracking integration with OwlBearAgent.turn()."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from pydantic_ai.messages import ModelRequest, ModelResponse, TextPart, UserPromptPart

from owlbear.core.agent import OwlBearAgent
from owlbear.memory.session import SessionStore
from owlbear.memory.usage import UsageRecord, UsageTracker


def _mock_result(output: str, messages: list[object]) -> MagicMock:
    """Build a mock PydanticAI AgentRunResult with usage data."""
    result = MagicMock()
    result.output = output
    result.all_messages.return_value = messages
    # Mock usage data matching pydantic_ai.usage.Usage
    usage = MagicMock()
    usage.requests = 1
    usage.input_tokens = 500
    usage.output_tokens = 150
    usage.cache_write_tokens = 0
    usage.cache_read_tokens = 0
    usage.tool_calls = 0
    usage.total_tokens = 650
    result.usage.return_value = usage
    return result


def _simple_messages() -> list[object]:
    """Minimal two-turn conversation."""
    return [
        ModelRequest(parts=[UserPromptPart(content="hi")]),
        ModelResponse(parts=[TextPart(content="hello")]),
    ]


# ---------------------------------------------------------------------------
# OwlBearAgent.turn() calls tracker.append() when tracker provided
# ---------------------------------------------------------------------------


class TestUsageTrackingIntegration:
    """OwlBearAgent.turn() records usage when a UsageTracker is provided."""

    def test_turn_calls_tracker_append(self, tmp_path: Path) -> None:
        """When a UsageTracker is provided, turn() appends a record."""
        tracker = MagicMock(spec=UsageTracker)
        agent = OwlBearAgent(
            model="test",
            session=SessionStore(tmp_path / "s.jsonl"),
            tracker=tracker,
        )
        mock = _mock_result("hello", _simple_messages())
        agent.inner = MagicMock()
        agent.inner.run = AsyncMock(return_value=mock)

        asyncio.run(agent.turn("hi"))

        tracker.append.assert_called_once()
        record = tracker.append.call_args[0][0]
        assert isinstance(record, UsageRecord)
        assert record.input_tokens == 500
        assert record.output_tokens == 150

    def test_turn_record_has_correct_model(self, tmp_path: Path) -> None:
        """The recorded UsageRecord carries the agent's model name."""
        tracker = MagicMock(spec=UsageTracker)
        agent = OwlBearAgent(
            model="test",
            session=SessionStore(tmp_path / "s.jsonl"),
            tracker=tracker,
        )
        mock = _mock_result("hello", _simple_messages())
        agent.inner = MagicMock()
        agent.inner.run = AsyncMock(return_value=mock)

        asyncio.run(agent.turn("hi"))

        record = tracker.append.call_args[0][0]
        assert isinstance(record, UsageRecord)
        # Model name should be present in the record
        assert record.model is not None


# ---------------------------------------------------------------------------
# Graceful skip when tracker is None
# ---------------------------------------------------------------------------


class TestUsageTrackingSkip:
    """OwlBearAgent.turn() works normally when no tracker is provided."""

    def test_turn_without_tracker_succeeds(self, tmp_path: Path) -> None:
        """When tracker is None (default), turn() completes normally."""
        agent = OwlBearAgent(
            model="test",
            session=SessionStore(tmp_path / "s.jsonl"),
        )
        mock = _mock_result("hello", _simple_messages())
        agent.inner = MagicMock()
        agent.inner.run = AsyncMock(return_value=mock)

        result = asyncio.run(agent.turn("hi"))
        assert result == "hello"

    def test_turn_without_tracker_returns_response(self, tmp_path: Path) -> None:
        """Response text is unaffected by tracker absence."""
        agent = OwlBearAgent(
            model="test",
            session=SessionStore(tmp_path / "s.jsonl"),
        )
        mock = _mock_result("world", _simple_messages())
        agent.inner = MagicMock()
        agent.inner.run = AsyncMock(return_value=mock)

        result = asyncio.run(agent.turn("hello"))
        assert result == "world"


# ---------------------------------------------------------------------------
# Error isolation — tracker error does not propagate
# ---------------------------------------------------------------------------


class TestUsageTrackingErrorIsolation:
    """Tracker errors must not escape to the caller of turn()."""

    def test_tracker_append_error_does_not_propagate(self, tmp_path: Path) -> None:
        """If tracker.append() raises, turn() still returns normally."""
        tracker = MagicMock(spec=UsageTracker)
        tracker.append.side_effect = OSError("disk full")

        agent = OwlBearAgent(
            model="test",
            session=SessionStore(tmp_path / "s.jsonl"),
            tracker=tracker,
        )
        mock = _mock_result("hello", _simple_messages())
        agent.inner = MagicMock()
        agent.inner.run = AsyncMock(return_value=mock)

        # Must NOT raise — tracker error is swallowed
        result = asyncio.run(agent.turn("hi"))
        assert result == "hello"

    def test_tracker_exception_logged_not_raised(self, tmp_path: Path) -> None:
        """Tracker failure should be logged, not raised."""
        tracker = MagicMock(spec=UsageTracker)
        tracker.append.side_effect = RuntimeError("tracker broken")

        agent = OwlBearAgent(
            model="test",
            session=SessionStore(tmp_path / "s.jsonl"),
            tracker=tracker,
        )
        mock = _mock_result("ok", _simple_messages())
        agent.inner = MagicMock()
        agent.inner.run = AsyncMock(return_value=mock)

        # No exception should escape
        result = asyncio.run(agent.turn("test"))
        assert result == "ok"
