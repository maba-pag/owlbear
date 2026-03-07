"""Tests for owlbear.core.condenser — SummarizingCondenser history processor.

TDD red phase: tests define the interface for SummarizingCondenser before
implementation. The module owlbear.core.condenser does not exist yet, so
condenser-class tests will fail with ImportError at collection time.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)

from owlbear.config import OwlBearSettings

if TYPE_CHECKING:
    from pydantic_ai.messages import ModelMessage


# ---------------------------------------------------------------------------
# Helpers — build realistic conversation message lists
# ---------------------------------------------------------------------------


def _make_request(content: str) -> ModelRequest:
    """Build a simple user ModelRequest."""
    return ModelRequest(parts=[UserPromptPart(content=content)])


def _make_response(content: str) -> ModelResponse:
    """Build a simple text ModelResponse."""
    return ModelResponse(parts=[TextPart(content=content)])


def _make_tool_call_response(tool_name: str, call_id: str) -> ModelResponse:
    """Build a ModelResponse with a ToolCallPart."""
    return ModelResponse(parts=[ToolCallPart(tool_name=tool_name, args={}, tool_call_id=call_id)])


def _make_tool_return_request(tool_name: str, call_id: str) -> ModelRequest:
    """Build a ModelRequest with a ToolReturnPart."""
    return ModelRequest(
        parts=[ToolReturnPart(tool_name=tool_name, content="result", tool_call_id=call_id)]
    )


def _make_conversation(n: int) -> list[ModelMessage]:
    """Build an alternating Request/Response conversation of *n* messages.

    Always starts with ModelRequest and ends with ModelRequest (to satisfy
    PydanticAI invariant that history ends with ModelRequest).
    """
    messages: list[ModelMessage] = []
    for i in range(n):
        if i % 2 == 0:
            messages.append(_make_request(f"user-{i}"))
        else:
            messages.append(_make_response(f"assistant-{i}"))
    # Ensure last message is ModelRequest (PydanticAI invariant)
    if isinstance(messages[-1], ModelResponse):
        messages.append(_make_request(f"user-{n}"))
    return messages[:n] if 0 < n < len(messages) else messages


def _make_conversation_ending_request(n: int) -> list[ModelMessage]:
    """Build a conversation of exactly *n* messages ending with ModelRequest."""
    msgs: list[ModelMessage] = []
    for i in range(n):
        if i % 2 == 0:
            msgs.append(_make_request(f"user-{i}"))
        else:
            msgs.append(_make_response(f"assistant-{i}"))
    # If last is ModelResponse, replace it with a ModelRequest
    if msgs and isinstance(msgs[-1], ModelResponse):
        msgs[-1] = _make_request(f"user-final-{n}")
    return msgs


# ---------------------------------------------------------------------------
# SummarizingCondenser — core behavior
# ---------------------------------------------------------------------------


class TestSummarizingCondenserNoOp:
    """When message count is at or below max_events, condenser is a no-op."""

    @pytest.mark.asyncio
    async def test_noop_below_threshold(self) -> None:
        from owlbear.core.condenser import SummarizingCondenser

        condenser = SummarizingCondenser(max_events=10, model=None)
        messages = _make_conversation_ending_request(5)
        ctx = MagicMock()
        result = await condenser(ctx, messages)
        assert result is messages  # identity — returned unchanged

    @pytest.mark.asyncio
    async def test_noop_at_threshold(self) -> None:
        from owlbear.core.condenser import SummarizingCondenser

        condenser = SummarizingCondenser(max_events=6, model=None)
        messages = _make_conversation_ending_request(6)
        ctx = MagicMock()
        result = await condenser(ctx, messages)
        assert result is messages


class TestSummarizingCondenserCondenses:
    """When message count exceeds max_events, condenser summarizes the middle."""

    @pytest.mark.asyncio
    async def test_condenses_above_threshold(self) -> None:
        from owlbear.core.condenser import SummarizingCondenser

        condenser = SummarizingCondenser(max_events=6, model="test")
        messages = _make_conversation_ending_request(12)
        ctx = MagicMock()
        result = await condenser(ctx, messages)
        # Result should be head + summary + tail, shorter than input
        assert len(result) < len(messages)
        # Structure: keep_first=4 head msgs + 1 summary + tail msgs
        assert isinstance(result[0], ModelRequest)  # head preserved


class TestKeepFirst:
    """First keep_first messages are always preserved unchanged."""

    @pytest.mark.asyncio
    async def test_keep_first_preserved(self) -> None:
        from owlbear.core.condenser import SummarizingCondenser

        keep_first = 4
        condenser = SummarizingCondenser(max_events=6, model="test", keep_first=keep_first)
        messages = _make_conversation_ending_request(14)
        ctx = MagicMock()
        result = await condenser(ctx, messages)
        # First keep_first messages must be the exact same objects
        for i in range(keep_first):
            assert result[i] is messages[i], f"Message at index {i} was not preserved"


class TestTargetSize:
    """Output length matches target_size formula."""

    @pytest.mark.asyncio
    async def test_target_size_respected(self) -> None:
        from owlbear.core.condenser import SummarizingCondenser

        max_events = 12
        keep_first = 2
        # target_size defaults to max_events // 2 = 6
        target_size = max_events // 2
        condenser = SummarizingCondenser(max_events=max_events, model="test", keep_first=keep_first)
        messages = _make_conversation_ending_request(20)
        ctx = MagicMock()
        result = await condenser(ctx, messages)
        # output = keep_first + 1 (summary) + tail_size
        # tail_size = target_size - keep_first - 1
        assert len(result) == target_size

    @pytest.mark.asyncio
    async def test_custom_target_size(self) -> None:
        from owlbear.core.condenser import SummarizingCondenser

        condenser = SummarizingCondenser(max_events=20, model="test", keep_first=2, target_size=8)
        messages = _make_conversation_ending_request(30)
        ctx = MagicMock()
        result = await condenser(ctx, messages)
        assert len(result) == 8


class TestSummaryMessage:
    """The injected summary ModelRequest has expected metadata and content."""

    @pytest.mark.asyncio
    async def test_summary_metadata(self) -> None:
        from owlbear.core.condenser import SummarizingCondenser

        keep_first = 2
        condenser = SummarizingCondenser(max_events=6, model="test", keep_first=keep_first)
        messages = _make_conversation_ending_request(12)
        ctx = MagicMock()
        result = await condenser(ctx, messages)

        # The summary message sits right after the head
        summary_msg = result[keep_first]
        assert isinstance(summary_msg, ModelRequest)
        assert summary_msg.metadata is not None
        assert "condensed_at" in summary_msg.metadata
        assert isinstance(summary_msg.metadata["condensed_at"], str)
        assert "forgotten_count" in summary_msg.metadata
        assert isinstance(summary_msg.metadata["forgotten_count"], int)
        assert summary_msg.metadata["forgotten_count"] > 0

    @pytest.mark.asyncio
    async def test_summary_content_prefix(self) -> None:
        from owlbear.core.condenser import SummarizingCondenser

        keep_first = 2
        condenser = SummarizingCondenser(max_events=6, model="test", keep_first=keep_first)
        messages = _make_conversation_ending_request(12)
        ctx = MagicMock()
        result = await condenser(ctx, messages)

        summary_msg = result[keep_first]
        assert isinstance(summary_msg, ModelRequest)
        user_part = summary_msg.parts[0]
        assert isinstance(user_part, UserPromptPart)
        assert user_part.content.startswith("[Condensed Context]\n")


class TestPydanticAIInvariant:
    """Output must always end with ModelRequest per PydanticAI contract."""

    @pytest.mark.asyncio
    async def test_ends_with_model_request(self) -> None:
        from owlbear.core.condenser import SummarizingCondenser

        condenser = SummarizingCondenser(max_events=6, model="test")
        messages = _make_conversation_ending_request(12)
        ctx = MagicMock()
        result = await condenser(ctx, messages)
        assert isinstance(result[-1], ModelRequest)


class TestBoundaryAlignment:
    """Tool-call/return pairs must not be split across head/tail boundary."""

    @pytest.mark.asyncio
    async def test_boundary_alignment_tool_pair(self) -> None:
        from owlbear.core.condenser import SummarizingCondenser

        # Build a conversation where a ToolCallPart response and its
        # ToolReturnPart request sit right at the boundary that would
        # normally be split between head and middle.
        keep_first = 3
        condenser = SummarizingCondenser(max_events=8, model="test", keep_first=keep_first)

        messages: list[ModelMessage] = [
            _make_request("user-0"),  # 0: head
            _make_response("assistant-1"),  # 1: head
            _make_request("user-2"),  # 2: head (last keep_first)
            # Index 3 would be first "middle" — but it's a tool call response
            _make_tool_call_response("read_file", "tc-1"),  # 3: tool call
            _make_tool_return_request("read_file", "tc-1"),  # 4: tool return
            _make_response("assistant-5"),  # 5
            _make_request("user-6"),  # 6
            _make_response("assistant-7"),  # 7
            _make_request("user-8"),  # 8
            _make_response("assistant-9"),  # 9
            _make_request("user-10"),  # 10: tail
            _make_response("assistant-11"),  # 11: tail
            _make_request("user-12"),  # 12: tail (last)
        ]

        ctx = MagicMock()
        result = await condenser(ctx, messages)

        # The tool call (index 3) and tool return (index 4) must both be
        # in the head or both in the tail — never split.
        tool_call_in_result = any(
            isinstance(m, ModelResponse)
            and any(isinstance(p, ToolCallPart) and p.tool_call_id == "tc-1" for p in m.parts)
            for m in result
        )
        tool_return_in_result = any(
            isinstance(m, ModelRequest)
            and any(isinstance(p, ToolReturnPart) and p.tool_call_id == "tc-1" for p in m.parts)
            for m in result
        )
        # If one is present, the other must be too
        assert tool_call_in_result == tool_return_in_result, (
            "ToolCallPart and ToolReturnPart with same call_id must not be split"
        )


class TestConstructor:
    """SummarizingCondenser constructor stores model correctly."""

    def test_model_none_uses_test_model(self) -> None:
        from owlbear.core.condenser import SummarizingCondenser

        condenser = SummarizingCondenser(max_events=10, model=None)
        assert condenser._model is None


# ---------------------------------------------------------------------------
# Config defaults — OwlBearSettings condenser fields
# ---------------------------------------------------------------------------


class TestCondenserConfig:
    """OwlBearSettings has condenser config fields with correct defaults."""

    def test_config_defaults(self) -> None:
        settings = OwlBearSettings()
        assert settings.condenser_enabled is False
        assert settings.condenser_max_events == 120


# ---------------------------------------------------------------------------
# Bootstrap wiring — condenser integrated when enabled
# ---------------------------------------------------------------------------


class TestBootstrapCondenserWiring:
    """Bootstrap correctly wires SummarizingCondenser based on config."""

    @pytest.mark.asyncio
    async def test_bootstrap_wires_condenser_when_enabled(self, tmp_path: Path) -> None:
        from owlbear.bootstrap import bootstrap

        mock_model = MagicMock()
        mock_model.model_name = "test-model"
        settings = OwlBearSettings(condenser_enabled=True)

        with (
            patch(
                "owlbear.bootstrap.create_copilot_model",
                new_callable=AsyncMock,
                return_value=mock_model,
            ),
            patch("owlbear.core.agent.Agent"),
        ):
            result = await bootstrap(settings, workspace_root=tmp_path)

        # The inner agent should have history_processors with a condenser
        processors = result.agent.inner.history_processors
        assert len(processors) >= 1

        from owlbear.core.condenser import SummarizingCondenser

        assert any(isinstance(p, SummarizingCondenser) for p in processors)

    @pytest.mark.asyncio
    async def test_bootstrap_no_condenser_when_disabled(self, tmp_path: Path) -> None:
        from owlbear.bootstrap import bootstrap

        mock_model = MagicMock()
        mock_model.model_name = "test-model"
        settings = OwlBearSettings(condenser_enabled=False)

        with (
            patch(
                "owlbear.bootstrap.create_copilot_model",
                new_callable=AsyncMock,
                return_value=mock_model,
            ),
            patch("owlbear.core.agent.Agent"),
        ):
            result = await bootstrap(settings, workspace_root=tmp_path)

        # No condenser should be wired
        processors = result.agent.inner.history_processors
        # Either empty or no SummarizingCondenser instances
        for p in processors:
            assert type(p).__name__ != "SummarizingCondenser"
