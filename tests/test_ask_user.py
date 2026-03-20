"""Tests for AskUserToolset — channel-based ask_user tool.

Covers: free-text questions, option formatting and validation,
index/text matching, retry exhaustion, timeout handling,
and TimeoutAction.ABORT vs SKIP behavior.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, PropertyMock

import pytest

from owlbear.tools.ask_user import (
    AskUserTimeoutError,
    AskUserToolset,
    TimeoutAction,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_channel(
    *,
    receive_returns: list[str | None] | str | None = "hello",
) -> AsyncMock:
    """Create a mock ChannelPlugin with configurable receive() responses."""
    channel = AsyncMock()
    type(channel).name = PropertyMock(return_value="test")

    if isinstance(receive_returns, list):
        channel.receive = AsyncMock(side_effect=receive_returns)
    else:
        channel.receive = AsyncMock(return_value=receive_returns)

    return channel


# ---------------------------------------------------------------------------
# Toolset registration
# ---------------------------------------------------------------------------


class TestAskUserToolsetRegistration:
    """AskUserToolset registers the ask_user tool on FunctionToolset."""

    def test_inherits_function_toolset(self) -> None:
        from pydantic_ai.toolsets import FunctionToolset

        ts = AskUserToolset(_make_channel())
        assert isinstance(ts, FunctionToolset)

    def test_registers_ask_user(self) -> None:
        ts = AskUserToolset(_make_channel())
        assert "ask_user" in ts.tools

    def test_single_tool_registered(self) -> None:
        ts = AskUserToolset(_make_channel())
        assert len(ts.tools) == 1


# ---------------------------------------------------------------------------
# Free-text question
# ---------------------------------------------------------------------------


class TestAskUserFreeText:
    """ask_user with no options sends question via channel and returns response."""

    @pytest.mark.asyncio
    async def test_sends_question_and_returns_response(self) -> None:
        channel = _make_channel(receive_returns="42")
        ts = AskUserToolset(channel)

        result = await (ts.ask_user("What is the answer?"))

        channel.send.assert_called_once_with("What is the answer?")
        assert result == "42"

    @pytest.mark.asyncio
    async def test_returns_channel_receive_value(self) -> None:
        channel = _make_channel(receive_returns="some response")
        ts = AskUserToolset(channel)

        result = await (ts.ask_user("Tell me something"))
        assert result == "some response"


# ---------------------------------------------------------------------------
# Options formatting
# ---------------------------------------------------------------------------


class TestAskUserOptionsFormatting:
    """ask_user with options formats a numbered list prompt."""

    @pytest.mark.asyncio
    async def test_formats_numbered_list(self) -> None:
        channel = _make_channel(receive_returns="1")
        ts = AskUserToolset(channel)

        await (ts.ask_user("Pick one:", options=["alpha", "beta"]))

        expected_prompt = "Pick one:\n[1] alpha\n[2] beta\nChoose [1-2]:"
        channel.send.assert_called_once_with(expected_prompt)

    @pytest.mark.asyncio
    async def test_formats_three_options(self) -> None:
        channel = _make_channel(receive_returns="2")
        ts = AskUserToolset(channel)

        await (ts.ask_user("Choose:", options=["a", "b", "c"]))

        expected_prompt = "Choose:\n[1] a\n[2] b\n[3] c\nChoose [1-3]:"
        channel.send.assert_called_once_with(expected_prompt)


# ---------------------------------------------------------------------------
# Option matching — by index
# ---------------------------------------------------------------------------


class TestAskUserOptionsByIndex:
    """ask_user with options accepts index input and returns option text."""

    @pytest.mark.asyncio
    async def test_index_1_returns_first_option(self) -> None:
        channel = _make_channel(receive_returns="1")
        ts = AskUserToolset(channel)

        result = await (ts.ask_user("Pick:", options=["high", "low"]))
        assert result == "high"

    @pytest.mark.asyncio
    async def test_index_2_returns_second_option(self) -> None:
        channel = _make_channel(receive_returns="2")
        ts = AskUserToolset(channel)

        result = await (ts.ask_user("Pick:", options=["high", "low"]))
        assert result == "low"


# ---------------------------------------------------------------------------
# Option matching — by text (case-insensitive)
# ---------------------------------------------------------------------------


class TestAskUserOptionsByText:
    """ask_user with options accepts text input (case-insensitive match)."""

    @pytest.mark.asyncio
    async def test_exact_text_match(self) -> None:
        channel = _make_channel(receive_returns="high")
        ts = AskUserToolset(channel)

        result = await (ts.ask_user("Pick:", options=["high", "low"]))
        assert result == "high"

    @pytest.mark.asyncio
    async def test_uppercase_text_match(self) -> None:
        channel = _make_channel(receive_returns="HIGH")
        ts = AskUserToolset(channel)

        result = await (ts.ask_user("Pick:", options=["high", "low"]))
        assert result == "high"

    @pytest.mark.asyncio
    async def test_mixed_case_text_match(self) -> None:
        channel = _make_channel(receive_returns="Low")
        ts = AskUserToolset(channel)

        result = await (ts.ask_user("Pick:", options=["high", "low"]))
        assert result == "low"


# ---------------------------------------------------------------------------
# Invalid input — retry behavior
# ---------------------------------------------------------------------------


class TestAskUserInvalidInput:
    """ask_user re-asks on invalid input up to max_retries."""

    @pytest.mark.asyncio
    async def test_reasks_on_invalid_then_accepts_valid(self) -> None:
        channel = _make_channel(receive_returns=["invalid", "1"])
        ts = AskUserToolset(channel, max_retries=3)

        result = await (ts.ask_user("Pick:", options=["alpha", "beta"]))
        assert result == "alpha"
        # send() called twice: initial prompt + re-ask prompt
        assert channel.send.call_count == 2

    @pytest.mark.asyncio
    async def test_reasks_multiple_times(self) -> None:
        channel = _make_channel(receive_returns=["bad", "worse", "1"])
        ts = AskUserToolset(channel, max_retries=3)

        result = await (ts.ask_user("Pick:", options=["alpha", "beta"]))
        assert result == "alpha"
        assert channel.send.call_count == 3


# ---------------------------------------------------------------------------
# Retry exhaustion + TimeoutAction.ABORT
# ---------------------------------------------------------------------------


class TestAskUserRetryExhaustionAbort:
    """Exhausting retries with ABORT raises AskUserTimeoutError."""

    @pytest.mark.asyncio
    async def test_raises_after_max_retries(self) -> None:
        channel = _make_channel(receive_returns=["bad", "bad", "bad"])
        ts = AskUserToolset(
            channel,
            max_retries=3,
            timeout_action=TimeoutAction.ABORT,
        )

        with pytest.raises(AskUserTimeoutError):
            await (ts.ask_user("Pick:", options=["alpha", "beta"]))

    def test_error_is_timeout_error_subclass(self) -> None:
        assert issubclass(AskUserTimeoutError, TimeoutError)


# ---------------------------------------------------------------------------
# Retry exhaustion + TimeoutAction.SKIP
# ---------------------------------------------------------------------------


class TestAskUserRetryExhaustionSkip:
    """Exhausting retries with SKIP returns default_response."""

    @pytest.mark.asyncio
    async def test_returns_default_response(self) -> None:
        channel = _make_channel(receive_returns=["bad", "bad", "bad"])
        ts = AskUserToolset(
            channel,
            max_retries=3,
            timeout_action=TimeoutAction.SKIP,
            default_response="(skipped)",
        )

        result = await (ts.ask_user("Pick:", options=["alpha", "beta"]))
        assert result == "(skipped)"

    @pytest.mark.asyncio
    async def test_returns_builtin_default(self) -> None:
        channel = _make_channel(receive_returns=["bad", "bad", "bad"])
        ts = AskUserToolset(
            channel,
            max_retries=3,
            timeout_action=TimeoutAction.SKIP,
        )

        result = await (ts.ask_user("Pick:", options=["alpha", "beta"]))
        assert result == "(no response)"


# ---------------------------------------------------------------------------
# Timeout + TimeoutAction.ABORT
# ---------------------------------------------------------------------------


class TestAskUserTimeoutAbort:
    """Timeout with ABORT raises AskUserTimeoutError."""

    @pytest.mark.asyncio
    async def test_raises_on_timeout(self) -> None:
        channel = _make_channel()
        channel.receive = AsyncMock(side_effect=asyncio.TimeoutError)
        ts = AskUserToolset(
            channel,
            timeout_seconds=0.01,
            timeout_action=TimeoutAction.ABORT,
        )

        with pytest.raises(AskUserTimeoutError):
            await (ts.ask_user("Are you there?"))


# ---------------------------------------------------------------------------
# Timeout + TimeoutAction.SKIP
# ---------------------------------------------------------------------------


class TestAskUserTimeoutSkip:
    """Timeout with SKIP returns default_response."""

    @pytest.mark.asyncio
    async def test_returns_default_on_timeout(self) -> None:
        channel = _make_channel()
        channel.receive = AsyncMock(side_effect=asyncio.TimeoutError)
        ts = AskUserToolset(
            channel,
            timeout_seconds=0.01,
            timeout_action=TimeoutAction.SKIP,
            default_response="(timed out)",
        )

        result = await (ts.ask_user("Are you there?"))
        assert result == "(timed out)"

    @pytest.mark.asyncio
    async def test_returns_builtin_default_on_timeout(self) -> None:
        channel = _make_channel()
        channel.receive = AsyncMock(side_effect=asyncio.TimeoutError)
        ts = AskUserToolset(
            channel,
            timeout_seconds=0.01,
            timeout_action=TimeoutAction.SKIP,
        )

        result = await (ts.ask_user("Are you there?"))
        assert result == "(no response)"


# ---------------------------------------------------------------------------
# Retroactive coverage: _receive_option edge paths (#831)
# ---------------------------------------------------------------------------


class TestFromAC_ReceiveOptionEdgePaths:  # noqa: N801
    """Cover _receive_option paths: TimeoutError and None from channel."""

    @pytest.mark.asyncio
    async def test_receive_option_timeout_triggers_handle_timeout_abort(self) -> None:
        """TimeoutError during _receive_option with ABORT raises AskUserTimeoutError."""
        channel = _make_channel()
        channel.receive = AsyncMock(side_effect=asyncio.TimeoutError)
        ts = AskUserToolset(
            channel,
            timeout_seconds=0.01,
            timeout_action=TimeoutAction.ABORT,
        )

        with pytest.raises(AskUserTimeoutError):
            await (ts.ask_user("Pick one", options=["a", "b"]))

    @pytest.mark.asyncio
    async def test_receive_option_timeout_triggers_handle_timeout_skip(self) -> None:
        """TimeoutError during _receive_option with SKIP returns default."""
        channel = _make_channel()
        channel.receive = AsyncMock(side_effect=asyncio.TimeoutError)
        ts = AskUserToolset(
            channel,
            timeout_seconds=0.01,
            timeout_action=TimeoutAction.SKIP,
            default_response="(skipped)",
        )

        result = await (ts.ask_user("Pick one", options=["a", "b"]))
        assert result == "(skipped)"

    @pytest.mark.asyncio
    async def test_receive_option_none_triggers_handle_timeout_abort(self) -> None:
        """channel.receive() returning None with ABORT raises AskUserTimeoutError."""
        channel = _make_channel(receive_returns=None)
        ts = AskUserToolset(
            channel,
            timeout_seconds=5.0,
            timeout_action=TimeoutAction.ABORT,
        )

        with pytest.raises(AskUserTimeoutError):
            await (ts.ask_user("Pick one", options=["a", "b"]))

    @pytest.mark.asyncio
    async def test_receive_option_none_triggers_handle_timeout_skip(self) -> None:
        """channel.receive() returning None with SKIP returns default."""
        channel = _make_channel(receive_returns=None)
        ts = AskUserToolset(
            channel,
            timeout_seconds=5.0,
            timeout_action=TimeoutAction.SKIP,
            default_response="(no answer)",
        )

        result = await (ts.ask_user("Pick one", options=["a", "b"]))
        assert result == "(no answer)"
