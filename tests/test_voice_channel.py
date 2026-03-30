"""Failing RED-phase tests for task #142: VoiceChannel adapter.

Covers: protocol compliance, send() behavior, receive() behavior,
receive() prompt, lazy spawn, lifecycle, and rich methods (ChannelPlugin defaults).

All tests fail on current HEAD because
``packages/orchestrator/src/owlbear/voice/channel.py``
does not yet exist.
"""

from __future__ import annotations

import inspect
from unittest.mock import AsyncMock, MagicMock

import pytest

from owlbear.voice.channel import VoiceChannel
from owlbear.voice.process import VoiceProcessError, VoiceProcessManager
from owlbear.voice.protocol import (
    ErrorMsg,
    PartialMsg,
    SpeakMsg,
    StatusMsg,
    TranscriptMsg,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_manager(*, receive_side_effect: list | None = None) -> MagicMock:
    """Return a mock VoiceProcessManager with AsyncMock methods."""
    mgr = MagicMock(spec=VoiceProcessManager)
    mgr.__aenter__ = AsyncMock(return_value=mgr)
    mgr.__aexit__ = AsyncMock(return_value=None)
    mgr.send = AsyncMock()
    mgr.shutdown = AsyncMock()
    if receive_side_effect is not None:
        mgr.receive = AsyncMock(side_effect=receive_side_effect)
    else:
        mgr.receive = AsyncMock()
    return mgr


# ---------------------------------------------------------------------------
# Protocol compliance (TestFromAC_Protocol)
# ---------------------------------------------------------------------------


class TestFromAC_Protocol:  # noqa: N801
    """VoiceChannel satisfies the ChannelPlugin protocol contract."""

    def test_name_property_returns_voice(self) -> None:
        mgr = _make_manager()
        channel = VoiceChannel(manager=mgr)
        assert channel.name == "voice"

    def test_send_is_async_method(self) -> None:
        mgr = _make_manager()
        channel = VoiceChannel(manager=mgr)
        assert callable(channel.send)
        assert inspect.iscoroutinefunction(channel.send)

    def test_receive_is_async_method(self) -> None:
        mgr = _make_manager()
        channel = VoiceChannel(manager=mgr)
        assert callable(channel.receive)
        assert inspect.iscoroutinefunction(channel.receive)


# ---------------------------------------------------------------------------
# send() behavior (TestFromAC_Send)
# ---------------------------------------------------------------------------


class TestFromAC_Send:  # noqa: N801
    """send() creates SpeakMsg and delegates to manager.send()."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_send_calls_manager_with_speak_msg(self) -> None:
        mgr = _make_manager()
        channel = VoiceChannel(manager=mgr)
        await channel.send("hello world")
        mgr.send.assert_called_once()
        sent_msg = mgr.send.call_args[0][0]
        assert isinstance(sent_msg, SpeakMsg)

    @pytest.mark.asyncio(loop_scope="function")
    async def test_send_sets_exact_speak_msg_fields(self) -> None:
        mgr = _make_manager()
        channel = VoiceChannel(manager=mgr)
        await channel.send("say this")
        sent_msg = mgr.send.call_args[0][0]
        assert sent_msg.text == "say this"
        assert sent_msg.interrupt is False
        assert sent_msg.type == "speak"


# ---------------------------------------------------------------------------
# receive() behavior (TestFromAC_Receive)
# ---------------------------------------------------------------------------


class TestFromAC_Receive:  # noqa: N801
    """receive() filters messages and returns TranscriptMsg.text on final=True."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_returns_text_for_final_transcript(self) -> None:
        final_msg = TranscriptMsg(text="done speaking", line_idx=0, final=True)
        mgr = _make_manager(receive_side_effect=[final_msg])
        channel = VoiceChannel(manager=mgr)
        result = await channel.receive()
        assert result == "done speaking"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_skips_status_msg_and_returns_next_transcript(self) -> None:
        status = StatusMsg(state="listening")
        final_msg = TranscriptMsg(text="got it", line_idx=0, final=True)
        mgr = _make_manager(receive_side_effect=[status, final_msg])
        channel = VoiceChannel(manager=mgr)
        result = await channel.receive()
        assert result == "got it"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_skips_partial_and_error_msgs(self) -> None:
        partial = PartialMsg(text="hel", line_idx=0)
        error = ErrorMsg(code="E1", message="oops")
        final_msg = TranscriptMsg(text="final", line_idx=0, final=True)
        mgr = _make_manager(receive_side_effect=[partial, error, final_msg])
        channel = VoiceChannel(manager=mgr)
        result = await channel.receive()
        assert result == "final"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_skips_non_final_transcript(self) -> None:
        partial_transcript = TranscriptMsg(text="not yet", line_idx=0, final=False)
        final_msg = TranscriptMsg(text="complete", line_idx=0, final=True)
        mgr = _make_manager(receive_side_effect=[partial_transcript, final_msg])
        channel = VoiceChannel(manager=mgr)
        result = await channel.receive()
        assert result == "complete"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_returns_none_on_voice_process_error(self) -> None:
        mgr = _make_manager(receive_side_effect=[VoiceProcessError("dead")])
        channel = VoiceChannel(manager=mgr)
        result = await channel.receive()
        assert result is None


# ---------------------------------------------------------------------------
# receive() prompt (TestFromAC_ReceivePrompt)
# ---------------------------------------------------------------------------


class TestFromAC_ReceivePrompt:  # noqa: N801
    """When prompt is provided, send(prompt) is called before listening."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_prompt_sent_before_listening(self) -> None:
        final_msg = TranscriptMsg(text="response", line_idx=0, final=True)
        mgr = _make_manager(receive_side_effect=[final_msg])
        channel = VoiceChannel(manager=mgr)
        result = await channel.receive(prompt="say something")

        # manager.send should have been called (with the prompt SpeakMsg)
        # and manager.receive should have been called after
        assert mgr.send.called
        prompt_msg = mgr.send.call_args[0][0]
        assert isinstance(prompt_msg, SpeakMsg)
        assert prompt_msg.text == "say something"

        # receive() must return the transcript text
        assert result == "response"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_prompt_send_occurs_before_manager_receive(self) -> None:
        final_msg = TranscriptMsg(text="heard", line_idx=0, final=True)
        mgr = _make_manager(receive_side_effect=[final_msg])
        channel = VoiceChannel(manager=mgr)
        await channel.receive(prompt="go ahead")

        # mock_calls captures every call on the manager in order;
        # send(...) must appear before receive() in the log.
        call_names = [str(c) for c in mgr.mock_calls]
        send_indices = [i for i, c in enumerate(call_names) if ".send(" in c]
        receive_indices = [i for i, c in enumerate(call_names) if ".receive(" in c]
        assert send_indices, "manager.send was never called"
        assert receive_indices, "manager.receive was never called"
        assert min(send_indices) < min(receive_indices)


# ---------------------------------------------------------------------------
# Lazy spawn (TestFromAC_LazySpawn)
# ---------------------------------------------------------------------------


class TestFromAC_LazySpawn:  # noqa: N801
    """Manager is not entered at construction; first receive() enters it; second does not re-enter."""

    def test_manager_not_entered_on_construction(self) -> None:
        mgr = _make_manager()
        _channel = VoiceChannel(manager=mgr)
        mgr.__aenter__.assert_not_called()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_first_receive_enters_manager(self) -> None:
        final_msg = TranscriptMsg(text="hi", line_idx=0, final=True)
        mgr = _make_manager(receive_side_effect=[final_msg])
        channel = VoiceChannel(manager=mgr)
        await channel.receive()
        mgr.__aenter__.assert_called_once()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_second_receive_does_not_re_enter_manager(self) -> None:
        msg1 = TranscriptMsg(text="first", line_idx=0, final=True)
        msg2 = TranscriptMsg(text="second", line_idx=0, final=True)
        mgr = _make_manager(receive_side_effect=[msg1, msg2])
        channel = VoiceChannel(manager=mgr)
        await channel.receive()
        await channel.receive()
        assert mgr.__aenter__.call_count == 1


# ---------------------------------------------------------------------------
# Lifecycle (TestFromAC_Lifecycle)
# ---------------------------------------------------------------------------


class TestFromAC_Lifecycle:  # noqa: N801
    """Async context manager protocol: __aenter__ returns self, __aexit__ shuts down if started."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_aenter_returns_self(self) -> None:
        mgr = _make_manager()
        channel = VoiceChannel(manager=mgr)
        result = await channel.__aenter__()
        assert result is channel

    @pytest.mark.asyncio(loop_scope="function")
    async def test_aexit_calls_shutdown_if_started(self) -> None:
        final_msg = TranscriptMsg(text="done", line_idx=0, final=True)
        mgr = _make_manager(receive_side_effect=[final_msg])
        channel = VoiceChannel(manager=mgr)
        await channel.receive()  # triggers lazy start
        await channel.__aexit__(None, None, None)
        mgr.shutdown.assert_called_once()

    @pytest.mark.asyncio(loop_scope="function")
    async def test_aexit_noop_if_never_started(self) -> None:
        mgr = _make_manager()
        channel = VoiceChannel(manager=mgr)
        await channel.__aexit__(None, None, None)
        mgr.shutdown.assert_not_called()


# ---------------------------------------------------------------------------
# Rich methods (TestFromAC_RichMethods)
# ---------------------------------------------------------------------------


class TestFromAC_RichMethods:  # noqa: N801
    """send_file, send_blocks, send_image delegate through send()."""

    @pytest.mark.asyncio(loop_scope="function")
    async def test_send_file_delegates_to_send_with_path_text(self) -> None:
        from pathlib import Path

        mgr = _make_manager()
        channel = VoiceChannel(manager=mgr)
        await channel.send_file(Path("audio.mp3"), caption="My file")
        mgr.send.assert_called_once()
        sent_msg = mgr.send.call_args[0][0]
        assert isinstance(sent_msg, SpeakMsg)
        assert "audio.mp3" in sent_msg.text or "My file" in sent_msg.text

    @pytest.mark.asyncio(loop_scope="function")
    async def test_send_blocks_delegates_to_send_with_fallback(self) -> None:
        mgr = _make_manager()
        channel = VoiceChannel(manager=mgr)
        await channel.send_blocks([{"type": "section", "text": "block"}], text_fallback="plain text")
        mgr.send.assert_called_once()
        sent_msg = mgr.send.call_args[0][0]
        assert isinstance(sent_msg, SpeakMsg)
        assert sent_msg.text == "plain text"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_send_image_with_caption_sends_caption(self) -> None:
        mgr = _make_manager()
        channel = VoiceChannel(manager=mgr)
        await channel.send_image(b"\x89PNG", caption="a photo")
        mgr.send.assert_called_once()
        sent_msg = mgr.send.call_args[0][0]
        assert isinstance(sent_msg, SpeakMsg)
        assert sent_msg.text == "a photo"

    @pytest.mark.asyncio(loop_scope="function")
    async def test_send_image_without_caption_sends_image_placeholder(self) -> None:
        mgr = _make_manager()
        channel = VoiceChannel(manager=mgr)
        await channel.send_image(b"\x89PNG")
        mgr.send.assert_called_once()
        sent_msg = mgr.send.call_args[0][0]
        assert isinstance(sent_msg, SpeakMsg)
        assert sent_msg.text == "[image]"

