"""Tests for Slack interactive features — approval gate enrichment + routing.

Task #416: ApprovalGateToolset sends Block Kit approval buttons on Slack;
           plain text on CLI; button clicks route through text bridge.
Task #419: Unit tests for Slack interactive features.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from conftest import make_mock_toolset  # type: ignore[import-untyped]

from owlbear.channels.slack_templates import format_approval_blocks
from owlbear.core.hooks import HookRegistry
from owlbear.safety.gate import ApprovalGateToolset
from owlbear.safety.policy import ApprovalPolicy, ApprovalRule, ApprovalSession

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_slack_channel(
    receive_responses: list[str | None] | None = None,
) -> MagicMock:
    """Create a mock SlackChannel with send, send_blocks, and receive.

    ``send`` and ``send_blocks`` record all calls.
    ``receive`` pops from *receive_responses* in order.
    """
    if receive_responses is None:
        receive_responses = ["approved"]

    channel = MagicMock()
    channel.name = "slack"
    channel.send = AsyncMock()
    channel.send_blocks = AsyncMock()
    responses = list(receive_responses)
    channel.receive = AsyncMock(side_effect=responses)
    return channel


def _make_cli_channel(
    receive_responses: list[str | None] | None = None,
) -> MagicMock:
    """Create a mock CLIChannel with send, send_blocks, and receive.

    Mirrors CLIChannel which inherits ``send_blocks`` from ChannelPlugin.
    """
    if receive_responses is None:
        receive_responses = ["yes"]

    channel = MagicMock(spec=["name", "send", "send_blocks", "receive"])
    channel.name = "cli"
    channel.send = AsyncMock()
    channel.send_blocks = AsyncMock()
    responses = list(receive_responses)
    channel.receive = AsyncMock(side_effect=responses)
    return channel


def _make_gate(
    *,
    rules: list[ApprovalRule] | None = None,
    channel: MagicMock | None = None,
    session: ApprovalSession | None = None,
    hooks: HookRegistry | None = None,
) -> tuple[ApprovalGateToolset, MagicMock, MagicMock]:
    """Build an ApprovalGateToolset, return (gate, inner_toolset, channel)."""
    policy = ApprovalPolicy(
        rules=rules or [ApprovalRule(tool_name="git_push")],
    )
    if session is None:
        session = ApprovalSession()
    if channel is None:
        channel = _make_slack_channel()
    inner = make_mock_toolset()

    gate = ApprovalGateToolset(
        wrapped=inner,
        policy=policy,
        session=session,
        channel=channel,
        hooks=hooks or HookRegistry(),
    )
    return gate, inner, channel


# ---------------------------------------------------------------------------
# AC #416: Slack channel gets Block Kit approval buttons via send_blocks
# ---------------------------------------------------------------------------


class TestApprovalGateSlackEnrichment:
    """ApprovalGateToolset sends Block Kit blocks when channel has send_blocks."""

    @pytest.mark.asyncio
    async def test_slack_channel_receives_blocks(self) -> None:
        """When channel has send_blocks(), it's called instead of send()."""
        gate, _inner, channel = _make_gate()
        ctx, tool = MagicMock(), MagicMock()

        await (gate.call_tool("git_push", {"branch": "main"}, ctx, tool))

        channel.send_blocks.assert_called_once()
        channel.send.assert_not_called()

    @pytest.mark.asyncio
    async def test_blocks_contain_approve_deny_buttons(self) -> None:
        """Blocks sent to Slack must contain Approve / Deny action buttons."""
        gate, _inner, channel = _make_gate()
        ctx, tool = MagicMock(), MagicMock()

        await (gate.call_tool("git_push", {}, ctx, tool))

        blocks = channel.send_blocks.call_args[0][0]
        # Find actions block
        actions_blocks = [b for b in blocks if b.get("type") == "actions"]
        assert len(actions_blocks) == 1
        elements = actions_blocks[0]["elements"]
        values = {e["value"] for e in elements}
        assert "approved" in values
        assert "denied" in values

    @pytest.mark.asyncio
    async def test_blocks_include_tool_name_in_description(self) -> None:
        """Approval block description should mention the tool being gated."""
        gate, _inner, channel = _make_gate()
        ctx, tool = MagicMock(), MagicMock()

        await (gate.call_tool("git_push", {"branch": "main"}, ctx, tool))

        blocks = channel.send_blocks.call_args[0][0]
        # Section block should mention the tool name
        section_texts = [
            b["text"]["text"]
            for b in blocks
            if b.get("type") == "section" and "text" in b.get("text", {})
        ]
        combined = " ".join(section_texts)
        assert "git_push" in combined

    @pytest.mark.asyncio
    async def test_text_fallback_passed_to_send_blocks(self) -> None:
        """send_blocks receives a text_fallback string for notifications."""
        gate, _inner, channel = _make_gate()
        ctx, tool = MagicMock(), MagicMock()

        await (gate.call_tool("git_push", {"branch": "main"}, ctx, tool))

        # Second positional arg or keyword arg is text_fallback
        call_args = channel.send_blocks.call_args
        text_fallback = (
            call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("text_fallback")
        )
        assert isinstance(text_fallback, str)
        assert "git_push" in text_fallback

    @pytest.mark.asyncio
    async def test_action_id_prefix_contains_tool_name(self) -> None:
        """Approval button action_ids should be prefixed with the tool name."""
        gate, _inner, channel = _make_gate()
        ctx, tool = MagicMock(), MagicMock()

        await (gate.call_tool("git_push", {}, ctx, tool))

        blocks = channel.send_blocks.call_args[0][0]
        actions_blocks = [b for b in blocks if b.get("type") == "actions"]
        elements = actions_blocks[0]["elements"]
        action_ids = {e["action_id"] for e in elements}
        assert any("git_push" in aid for aid in action_ids)


# ---------------------------------------------------------------------------
# AC #416: CLI channel falls back to plain text send()
# ---------------------------------------------------------------------------


class TestApprovalGateCLIFallback:
    """ApprovalGateToolset falls back to send() when channel lacks send_blocks."""

    @pytest.mark.asyncio
    async def test_cli_channel_gets_prompt_via_send_blocks(self) -> None:
        """CLIChannel receives approval prompt in send_blocks text_fallback."""
        cli_channel = _make_cli_channel(["yes"])
        gate, _inner, _channel = _make_gate(channel=cli_channel)
        ctx, tool = MagicMock(), MagicMock()

        await (gate.call_tool("git_push", {"branch": "main"}, ctx, tool))

        cli_channel.send_blocks.assert_called_once()
        text_fallback: str = cli_channel.send_blocks.call_args[0][1]
        assert "git_push" in text_fallback
        assert "Approve?" in text_fallback

    @pytest.mark.asyncio
    async def test_cli_channel_has_send_blocks(self) -> None:
        """CLIChannel inherits send_blocks from ChannelPlugin — gate uses it."""
        cli_channel = _make_cli_channel(["yes"])
        gate, _, _ = _make_gate(channel=cli_channel)
        ctx, tool = MagicMock(), MagicMock()

        await (gate.call_tool("git_push", {}, ctx, tool))

        assert hasattr(cli_channel, "send_blocks")
        cli_channel.send_blocks.assert_called_once()


# ---------------------------------------------------------------------------
# AC #416: Button click values route through existing yes/no flow
# ---------------------------------------------------------------------------


class TestButtonClickRouting:
    """Button click values ('approved'/'denied') parsed correctly by gate."""

    @pytest.mark.asyncio
    async def test_approved_value_proceeds_with_tool_call(self) -> None:
        """'approved' button value (from Slack interactive) → tool executes."""
        gate, inner, _channel = _make_gate(
            channel=_make_slack_channel(["approved"]),
        )
        ctx, tool = MagicMock(), MagicMock()

        result = await (gate.call_tool("git_push", {}, ctx, tool))

        inner.call_tool.assert_called_once()
        assert result == "tool_result"

    @pytest.mark.asyncio
    async def test_denied_value_skips_tool_call(self) -> None:
        """'denied' button value (from Slack interactive) → tool denied."""
        gate, inner, _channel = _make_gate(
            channel=_make_slack_channel(["denied"]),
        )
        ctx, tool = MagicMock(), MagicMock()

        result = await (gate.call_tool("git_push", {}, ctx, tool))

        inner.call_tool.assert_not_called()
        assert isinstance(result, str)
        assert "denied" in result.lower()

    @pytest.mark.asyncio
    async def test_approved_hook_records_approval(self) -> None:
        """Hook payload should record 'approved' decision from button click."""
        hooks = HookRegistry()
        captured: list[dict[str, Any]] = []
        hooks.register("post_tool_use", captured.append)

        gate, _inner, _channel = _make_gate(
            channel=_make_slack_channel(["approved"]),
            hooks=hooks,
        )
        ctx, tool = MagicMock(), MagicMock()

        await (gate.call_tool("git_push", {}, ctx, tool))

        decisions = [p for p in captured if p.get("approval_decision")]
        assert len(decisions) >= 1
        assert decisions[0]["approval_decision"] == "approved"

    @pytest.mark.asyncio
    async def test_denied_hook_records_denial(self) -> None:
        """Hook payload should record 'denied' decision from button click."""
        hooks = HookRegistry()
        captured: list[dict[str, Any]] = []
        hooks.register("post_tool_use", captured.append)

        gate, _inner, _channel = _make_gate(
            channel=_make_slack_channel(["denied"]),
            hooks=hooks,
        )
        ctx, tool = MagicMock(), MagicMock()

        await (gate.call_tool("git_push", {}, ctx, tool))

        decisions = [p for p in captured if p.get("approval_decision")]
        assert len(decisions) >= 1
        assert decisions[0]["approval_decision"] == "denied"


# ---------------------------------------------------------------------------
# AC #419: Interactive payload routing — block_actions via socket handler
# ---------------------------------------------------------------------------


class TestInteractivePayloadRouting:
    """Block action payloads are correctly routed through SlackChannel handler."""

    @pytest.mark.asyncio
    @patch("owlbear.channels.slack.SocketModeClient")
    async def test_approve_button_enqueues_approved(
        self,
        mock_socket_cls: MagicMock,
    ) -> None:
        """Clicking Approve sends 'approved' value to the message queue."""
        from owlbear.channels.slack import SlackChannel

        mock_socket_instance = AsyncMock()
        mock_socket_instance.socket_mode_request_listeners = []
        mock_socket_cls.return_value = mock_socket_instance

        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
        )
        await channel.connect()
        handler = mock_socket_instance.socket_mode_request_listeners[0]

        fake_request = MagicMock()
        fake_request.type = "interactive"
        fake_request.payload = {
            "type": "block_actions",
            "actions": [
                {"action_id": "approval_git_push_approve", "value": "approved"},
            ],
        }

        await handler(mock_socket_instance, fake_request)

        result = channel._message_queue.get_nowait()
        assert result == "approved"

    @pytest.mark.asyncio
    @patch("owlbear.channels.slack.SocketModeClient")
    async def test_deny_button_enqueues_denied(
        self,
        mock_socket_cls: MagicMock,
    ) -> None:
        """Clicking Deny sends 'denied' value to the message queue."""
        from owlbear.channels.slack import SlackChannel

        mock_socket_instance = AsyncMock()
        mock_socket_instance.socket_mode_request_listeners = []
        mock_socket_cls.return_value = mock_socket_instance

        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
        )
        await channel.connect()
        handler = mock_socket_instance.socket_mode_request_listeners[0]

        fake_request = MagicMock()
        fake_request.type = "interactive"
        fake_request.payload = {
            "type": "block_actions",
            "actions": [
                {"action_id": "approval_git_push_deny", "value": "denied"},
            ],
        }

        await handler(mock_socket_instance, fake_request)

        result = channel._message_queue.get_nowait()
        assert result == "denied"


# ---------------------------------------------------------------------------
# AC #419: Template output produces valid Block Kit JSON
# ---------------------------------------------------------------------------


class TestApprovalTemplateValidity:
    """format_approval_blocks output is structurally valid Block Kit."""

    def test_blocks_are_list_of_dicts(self) -> None:
        blocks = format_approval_blocks("Deploy to prod", "approval_deploy")
        assert isinstance(blocks, list)
        assert all(isinstance(b, dict) for b in blocks)

    def test_all_blocks_have_type(self) -> None:
        blocks = format_approval_blocks("Push to main", "approval_push")
        for block in blocks:
            assert "type" in block

    def test_actions_block_has_elements(self) -> None:
        blocks = format_approval_blocks("Delete files", "approval_delete")
        actions = [b for b in blocks if b["type"] == "actions"]
        assert len(actions) == 1
        assert "elements" in actions[0]
        assert len(actions[0]["elements"]) == 2

    def test_buttons_have_required_fields(self) -> None:
        """Each button must have type, text, action_id, and value."""
        blocks = format_approval_blocks("Dangerous op", "approval_danger")
        actions = next(b for b in blocks if b["type"] == "actions")
        for element in actions["elements"]:
            assert element["type"] == "button"
            assert "text" in element
            assert element["text"]["type"] == "plain_text"
            assert "action_id" in element
            assert "value" in element

    def test_approve_button_is_primary_style(self) -> None:
        blocks = format_approval_blocks("Op", "approval_op")
        actions = next(b for b in blocks if b["type"] == "actions")
        approve_btn = next(e for e in actions["elements"] if e["value"] == "approved")
        assert approve_btn["style"] == "primary"

    def test_deny_button_is_danger_style(self) -> None:
        blocks = format_approval_blocks("Op", "approval_op")
        actions = next(b for b in blocks if b["type"] == "actions")
        deny_btn = next(e for e in actions["elements"] if e["value"] == "denied")
        assert deny_btn["style"] == "danger"


# ---------------------------------------------------------------------------
# AC #419: Thread registry + context_key integration
# ---------------------------------------------------------------------------


class TestThreadRegistryIntegration:
    """Thread registry correctly auto-threads approval messages."""

    @pytest.mark.asyncio
    async def test_send_blocks_threads_with_registry(self) -> None:
        """send_blocks with context_key uses thread registry."""
        from owlbear.channels.slack import SlackChannel

        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
        )
        channel._web_client = AsyncMock()
        channel._web_client.chat_postMessage.return_value = {
            "ok": True,
            "ts": "1111111111.000001",
        }

        blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": "test"}}]

        # First send creates thread
        await channel.send_blocks(blocks, "test", context_key="session:approval")
        assert channel._thread_registry["session:approval"] == "1111111111.000001"

        # Second send auto-threads
        await channel.send_blocks(blocks, "followup", context_key="session:approval")
        second_call = channel._web_client.chat_postMessage.call_args_list[1]
        assert second_call.kwargs.get("thread_ts") == "1111111111.000001"


# ---------------------------------------------------------------------------
# AC #419: Fallback paths — full integration check
# ---------------------------------------------------------------------------


class TestFallbackPathsIntegration:
    """Verify the full fallback path: Slack gets blocks, CLI gets text."""

    @pytest.mark.asyncio
    async def test_slack_channel_full_flow(self) -> None:
        """SlackChannel mock: send_blocks called, user approves, tool runs."""
        slack = _make_slack_channel(["approved"])
        gate, inner, _ = _make_gate(channel=slack)
        ctx, tool = MagicMock(), MagicMock()

        result = await (gate.call_tool("git_push", {"branch": "main"}, ctx, tool))

        slack.send_blocks.assert_called_once()
        slack.send.assert_not_called()
        inner.call_tool.assert_called_once()
        assert result == "tool_result"

    @pytest.mark.asyncio
    async def test_cli_channel_full_flow(self) -> None:
        """CLIChannel mock: send_blocks() called, user approves, tool runs."""
        cli = _make_cli_channel(["yes"])
        gate, inner, _ = _make_gate(channel=cli)
        ctx, tool = MagicMock(), MagicMock()

        result = await (gate.call_tool("git_push", {"branch": "main"}, ctx, tool))

        cli.send_blocks.assert_called_once()
        text_fallback = cli.send_blocks.call_args[0][1]
        assert "git_push" in text_fallback
        inner.call_tool.assert_called_once()
        assert result == "tool_result"

    @pytest.mark.asyncio
    async def test_slack_deny_full_flow(self) -> None:
        """SlackChannel: user clicks Deny → tool not called, denial returned."""
        slack = _make_slack_channel(["denied"])
        gate, inner, _ = _make_gate(channel=slack)
        ctx, tool = MagicMock(), MagicMock()

        result = await (gate.call_tool("git_push", {}, ctx, tool))

        slack.send_blocks.assert_called_once()
        inner.call_tool.assert_not_called()
        assert "denied" in str(result).lower()

    @pytest.mark.asyncio
    async def test_cli_deny_full_flow(self) -> None:
        """CLIChannel: user types 'no' → tool not called, denial returned."""
        cli = _make_cli_channel(["no"])
        gate, inner, _ = _make_gate(channel=cli)
        ctx, tool = MagicMock(), MagicMock()

        result = await (gate.call_tool("git_push", {}, ctx, tool))

        cli.send_blocks.assert_called_once()
        inner.call_tool.assert_not_called()
        assert "denied" in str(result).lower()


# ---------------------------------------------------------------------------
# AC #533 / Task #794: send_image context_key threading
# ---------------------------------------------------------------------------


class TestFromAC_SendImageContextKey:
    """send_image must support context_key for thread registry integration."""

    def test_send_image_accepts_context_key_kwarg(self) -> None:
        """send_image signature must accept context_key as keyword argument."""
        import inspect

        from owlbear.channels.slack import SlackChannel

        sig = inspect.signature(SlackChannel.send_image)
        assert "context_key" in sig.parameters, (
            "send_image must accept a context_key keyword argument"
        )
        param = sig.parameters["context_key"]
        assert param.kind in (
            inspect.Parameter.KEYWORD_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        )

    @pytest.mark.asyncio
    async def test_send_image_context_key_resolves_thread_ts(self) -> None:
        """send_image with context_key uses thread_ts from _thread_registry."""
        from owlbear.channels.slack import SlackChannel

        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
        )
        channel._web_client = AsyncMock()
        channel._web_client.files_upload_v2.return_value = {
            "ok": True,
            "file": {"id": "F123"},
        }
        # Pre-populate registry so context_key resolves
        channel._thread_registry["img:task42"] = "8888888888.000001"

        await channel.send_image(b"png-data", caption="chart", context_key="img:task42")

        call_kwargs = channel._web_client.files_upload_v2.call_args.kwargs
        assert call_kwargs["thread_ts"] == "8888888888.000001"

    @pytest.mark.asyncio
    async def test_send_image_first_call_registers_ts(self) -> None:
        """First send_image with context_key registers ts from response."""
        from owlbear.channels.slack import SlackChannel

        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
        )
        channel._web_client = AsyncMock()
        channel._web_client.files_upload_v2.return_value = {
            "ok": True,
            "file": {"id": "F456", "shares": {"public": {"C12345": [{"ts": "7777777777.000001"}]}}},
        }

        await channel.send_image(
            b"img-bytes", caption="screenshot", context_key="proj:task99"
        )

        assert "proj:task99" in channel._thread_registry
        assert channel._thread_registry["proj:task99"]  # non-empty string

    @pytest.mark.asyncio
    async def test_explicit_thread_ts_takes_precedence(self) -> None:
        """Explicit thread_ts must take precedence over context_key lookup."""
        from owlbear.channels.slack import SlackChannel

        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
        )
        channel._web_client = AsyncMock()
        channel._web_client.files_upload_v2.return_value = {
            "ok": True,
            "file": {"id": "F789"},
        }
        # Pre-populate registry
        channel._thread_registry["proj:task1"] = "9999999999.000001"

        await channel.send_image(
            b"data",
            caption="img",
            thread_ts="5555555555.000001",
            context_key="proj:task1",
        )

        call_kwargs = channel._web_client.files_upload_v2.call_args.kwargs
        # Explicit thread_ts wins over registry
        assert call_kwargs["thread_ts"] == "5555555555.000001"

    @pytest.mark.asyncio
    async def test_error_fallback_forwards_context_key(self) -> None:
        """When files_upload_v2 fails, fallback send() receives context_key."""
        from owlbear.channels.slack import SlackChannel

        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
        )
        channel._web_client = AsyncMock()
        channel._web_client.files_upload_v2.side_effect = Exception("upload boom")
        channel._web_client.chat_postMessage.return_value = {
            "ok": True,
            "ts": "6666666666.000001",
        }

        await channel.send_image(
            b"data", caption="fallback", context_key="ctx:fallback"
        )

        # send() should have been called with context_key
        channel._web_client.chat_postMessage.assert_awaited_once()
        # After fallback send, context_key should register from the send() call
        assert "ctx:fallback" in channel._thread_registry

    @pytest.mark.asyncio
    async def test_send_image_without_context_key_regression(self) -> None:
        """send_image without context_key works exactly as before (regression).

        Also verifies that context_key=None is the default (signature check),
        ensuring the parameter exists even when unused.
        """
        import inspect

        from owlbear.channels.slack import SlackChannel

        # Verify context_key parameter exists with None default
        sig = inspect.signature(SlackChannel.send_image)
        param = sig.parameters["context_key"]
        assert param.default is None

        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
        )
        channel._web_client = AsyncMock()

        await channel.send_image("/images/chart.png", caption="Chart")

        channel._web_client.files_upload_v2.assert_awaited_once()
        call_kwargs = channel._web_client.files_upload_v2.call_args.kwargs
        assert "thread_ts" not in call_kwargs
        assert channel._thread_registry == {}


# ---------------------------------------------------------------------------
# AC #533 line 4: ts extraction failure → log debug + skip registration
# ---------------------------------------------------------------------------


class TestFromAC_SendImageTsExtractionFailure:
    """When ts cannot be extracted from files_upload_v2 response, send_image
    must log a debug message and skip thread registry registration — without
    raising an exception.
    """

    @pytest.mark.asyncio
    async def test_missing_shares_logs_debug_and_skips_registration(
        self,
    ) -> None:
        """Response has file but no shares dict → debug log, no registration."""
        from owlbear.channels.slack import SlackChannel

        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
        )
        channel._web_client = AsyncMock()
        channel._web_client.files_upload_v2.return_value = {
            "ok": True,
            "file": {"id": "F100"},
        }

        with patch("owlbear.channels.slack.logger") as mock_logger:
            await channel.send_image(
                b"img-data", caption="test", context_key="ctx:no-shares"
            )

        # Registration must be skipped
        assert "ctx:no-shares" not in channel._thread_registry
        # A debug-level log must be emitted explaining why registration was skipped
        mock_logger.debug.assert_called_once()

    @pytest.mark.asyncio
    async def test_empty_shares_logs_debug_and_skips_registration(
        self,
    ) -> None:
        """Response has file.shares but both public and private are empty."""
        from owlbear.channels.slack import SlackChannel

        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
        )
        channel._web_client = AsyncMock()
        channel._web_client.files_upload_v2.return_value = {
            "ok": True,
            "file": {"id": "F200", "shares": {"public": {}, "private": {}}},
        }

        with patch("owlbear.channels.slack.logger") as mock_logger:
            await channel.send_image(
                b"img-data", caption="test", context_key="ctx:empty-shares"
            )

        assert "ctx:empty-shares" not in channel._thread_registry
        mock_logger.debug.assert_called_once()

    @pytest.mark.asyncio
    async def test_minimal_response_logs_debug_and_skips_registration(
        self,
    ) -> None:
        """Response is minimal (no file key at all) → graceful degradation."""
        from owlbear.channels.slack import SlackChannel

        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
        )
        channel._web_client = AsyncMock()
        channel._web_client.files_upload_v2.return_value = {"ok": True}

        with patch("owlbear.channels.slack.logger") as mock_logger:
            await channel.send_image(
                b"img-data", caption="test", context_key="ctx:minimal"
            )

        assert "ctx:minimal" not in channel._thread_registry
        mock_logger.debug.assert_called_once()

    @pytest.mark.asyncio
    async def test_shares_with_missing_ts_logs_debug(self) -> None:
        """Response has shares entries but ts key is absent → debug log."""
        from owlbear.channels.slack import SlackChannel

        channel = SlackChannel(
            app_token="xapp-test",
            bot_token="xoxb-test",
            channel_id="C12345",
        )
        channel._web_client = AsyncMock()
        channel._web_client.files_upload_v2.return_value = {
            "ok": True,
            "file": {
                "id": "F300",
                "shares": {"public": {"C12345": [{"no_ts_here": "1"}]}},
            },
        }

        with patch("owlbear.channels.slack.logger") as mock_logger:
            await channel.send_image(
                b"img-data", caption="test", context_key="ctx:no-ts-field"
            )

        assert "ctx:no-ts-field" not in channel._thread_registry
        mock_logger.debug.assert_called_once()
