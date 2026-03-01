"""Tests for ApprovalGateToolset — WrapperToolset that gates tool calls behind approval.

TDD red-phase tests for task #340.  The module ``owlbear.safety.gate``
does not exist yet — all tests are expected to fail with ``ImportError``.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from owlbear.core.hooks import HookEvent, HookRegistry
from owlbear.safety.gate import ApprovalGateToolset
from owlbear.safety.policy import ApprovalPolicy, ApprovalRule, ApprovalSession

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run(coro: object) -> object:
    """Run an async coroutine synchronously."""
    return asyncio.run(coro)  # type: ignore[arg-type]


def _make_mock_toolset(return_value: object = "tool_result") -> MagicMock:
    """Create a mock AbstractToolset with an async call_tool."""
    mock_ts = MagicMock()
    mock_ts.call_tool = AsyncMock(return_value=return_value)
    return mock_ts


def _make_channel(
    receive_responses: list[str | None] | None = None,
) -> MagicMock:
    """Create a mock ChannelPlugin with send/receive queues.

    ``send`` records all messages sent.
    ``receive`` pops from *receive_responses* in order (defaults to ``['yes']``).
    """
    if receive_responses is None:
        receive_responses = ["yes"]

    channel = MagicMock()
    channel.name = "test"
    channel.send = AsyncMock()
    responses = list(receive_responses)  # copy so pop is safe
    channel.receive = AsyncMock(side_effect=responses)
    return channel


@dataclass
class _GateFixture:
    """Bundle returned by :func:`_make_gate`."""

    gate: ApprovalGateToolset
    inner: MagicMock
    channel: MagicMock


def _make_gate(
    *,
    rules: list[ApprovalRule] | None = None,
    timeout: float = 120.0,
    session: ApprovalSession | None = None,
    channel: MagicMock | None = None,
    hooks: HookRegistry | None = None,
) -> _GateFixture:
    """Build an ApprovalGateToolset with sensible defaults."""
    policy = ApprovalPolicy(
        rules=rules or [],
        default_timeout=timeout,
    )
    if session is None:
        session = ApprovalSession()
    if channel is None:
        channel = _make_channel()
    inner = _make_mock_toolset()

    gate = ApprovalGateToolset(
        wrapped=inner,
        policy=policy,
        session=session,
        channel=channel,
        hooks=hooks or HookRegistry(),
    )
    return _GateFixture(gate=gate, inner=inner, channel=channel)


# ---------------------------------------------------------------------------
# AC: Test call_tool() with tool requiring approval sends prompt
# ---------------------------------------------------------------------------


class TestApprovalPromptSent:
    """When a gated tool is called, the channel receives an approval prompt."""

    def test_sends_approval_prompt_via_channel(self) -> None:
        """call_tool for a gated tool must call channel.send() with a prompt."""
        fix = _make_gate(rules=[ApprovalRule(tool_name="git_push")])
        ctx = MagicMock()
        tool = MagicMock()

        _run(fix.gate.call_tool("git_push", {"branch": "main"}, ctx, tool))

        fix.channel.send.assert_called_once()
        prompt_text: str = fix.channel.send.call_args[0][0]
        assert "git_push" in prompt_text

    def test_prompt_includes_tool_name(self) -> None:
        """Approval prompt must mention the tool name being gated."""
        fix = _make_gate(rules=[ApprovalRule(tool_name="delete_file")])
        ctx = MagicMock()
        tool = MagicMock()

        _run(fix.gate.call_tool("delete_file", {"path": "/important"}, ctx, tool))

        prompt_text: str = fix.channel.send.call_args[0][0]
        assert "delete_file" in prompt_text


# ---------------------------------------------------------------------------
# AC: Approve path — 'yes' -> tool call proceeds
# ---------------------------------------------------------------------------


class TestApprovePath:
    """When user responds 'yes', the wrapped tool executes normally."""

    def test_yes_proceeds_with_tool_call(self) -> None:
        """channel.receive() returns 'yes' -> inner call_tool is invoked."""
        fix = _make_gate(rules=[ApprovalRule(tool_name="git_push")])
        fix.channel.receive = AsyncMock(return_value="yes")
        ctx = MagicMock()
        tool = MagicMock()

        result = _run(fix.gate.call_tool("git_push", {"branch": "main"}, ctx, tool))

        fix.inner.call_tool.assert_called_once()
        assert result == "tool_result"

    def test_y_shorthand_also_approves(self) -> None:
        """A shorthand 'y' response should also approve the tool call."""
        fix = _make_gate(
            rules=[ApprovalRule(tool_name="git_push")],
            channel=_make_channel(["y"]),
        )
        ctx = MagicMock()
        tool = MagicMock()

        result = _run(fix.gate.call_tool("git_push", {}, ctx, tool))

        fix.inner.call_tool.assert_called_once()
        assert result == "tool_result"


# ---------------------------------------------------------------------------
# AC: Deny path — 'no' -> tool call skipped
# ---------------------------------------------------------------------------


class TestDenyPath:
    """When user responds 'no', the tool is not called and denial returned."""

    def test_no_skips_tool_returns_denial(self) -> None:
        """channel.receive() returns 'no' -> tool NOT called, returns denial."""
        fix = _make_gate(
            rules=[ApprovalRule(tool_name="git_push")],
            channel=_make_channel(["no"]),
        )
        ctx = MagicMock()
        tool = MagicMock()

        result = _run(fix.gate.call_tool("git_push", {}, ctx, tool))

        fix.inner.call_tool.assert_not_called()
        assert isinstance(result, str)
        assert "denied" in result.lower()

    def test_n_shorthand_also_denies(self) -> None:
        """A shorthand 'n' response should also deny."""
        fix = _make_gate(
            rules=[ApprovalRule(tool_name="git_push")],
            channel=_make_channel(["n"]),
        )
        ctx = MagicMock()
        tool = MagicMock()

        result = _run(fix.gate.call_tool("git_push", {}, ctx, tool))

        fix.inner.call_tool.assert_not_called()
        assert "denied" in str(result).lower()


# ---------------------------------------------------------------------------
# AC: Timeout path — channel.receive() returns None
# ---------------------------------------------------------------------------


class TestTimeoutPath:
    """When channel.receive() returns None (timeout/disconnect), tool is skipped."""

    def test_none_response_returns_cancellation(self) -> None:
        """receive() -> None means timeout: tool skipped, cancellation message."""
        fix = _make_gate(
            rules=[ApprovalRule(tool_name="git_push")],
            channel=_make_channel([None]),
        )
        ctx = MagicMock()
        tool = MagicMock()

        result = _run(fix.gate.call_tool("git_push", {}, ctx, tool))

        fix.inner.call_tool.assert_not_called()
        assert isinstance(result, str)
        # Should mention timeout or cancellation
        assert "timeout" in result.lower() or "cancel" in result.lower()


# ---------------------------------------------------------------------------
# AC: Pre-grant path — session already has grant
# ---------------------------------------------------------------------------


class TestPreGrantPath:
    """When the tool is pre-granted in the session, no prompt is sent."""

    def test_pre_granted_skips_prompt(self) -> None:
        """Pre-granted tool bypasses channel interaction entirely."""
        session = ApprovalSession()
        session.grant("git_push")

        fix = _make_gate(
            rules=[ApprovalRule(tool_name="git_push")],
            session=session,
        )
        ctx = MagicMock()
        tool = MagicMock()

        result = _run(fix.gate.call_tool("git_push", {}, ctx, tool))

        fix.channel.send.assert_not_called()
        fix.channel.receive.assert_not_called()
        fix.inner.call_tool.assert_called_once()
        assert result == "tool_result"


# ---------------------------------------------------------------------------
# AC: 'approve all {tool}' response — adds pre-grant and proceeds
# ---------------------------------------------------------------------------


class TestApproveAllResponse:
    """'approve all {tool}' grants future calls and proceeds immediately."""

    def test_approve_all_grants_and_proceeds(self) -> None:
        """'approve all git_push' -> session.grant() + inner called."""
        session = ApprovalSession()
        fix = _make_gate(
            rules=[ApprovalRule(tool_name="git_push")],
            session=session,
            channel=_make_channel(["approve all git_push"]),
        )
        ctx = MagicMock()
        tool = MagicMock()

        result = _run(fix.gate.call_tool("git_push", {}, ctx, tool))

        assert session.is_pre_granted("git_push") is True
        fix.inner.call_tool.assert_called_once()
        assert result == "tool_result"

    def test_second_call_after_approve_all_skips_prompt(self) -> None:
        """After 'approve all', subsequent calls skip the approval prompt."""
        session = ApprovalSession()
        fix = _make_gate(
            rules=[ApprovalRule(tool_name="git_push")],
            session=session,
            channel=_make_channel(["approve all git_push"]),
        )
        ctx = MagicMock()
        tool = MagicMock()

        # First call — goes through approval, grants
        _run(fix.gate.call_tool("git_push", {}, ctx, tool))
        assert session.is_pre_granted("git_push") is True

        # Reset channel to track second call
        fix.channel.send.reset_mock()
        fix.channel.receive.reset_mock()

        # Second call — pre-granted, no prompt
        _run(fix.gate.call_tool("git_push", {}, ctx, tool))
        fix.channel.send.assert_not_called()
        fix.channel.receive.assert_not_called()
        assert fix.inner.call_tool.call_count == 2


# ---------------------------------------------------------------------------
# AC: Tool NOT in policy — proceed without prompting
# ---------------------------------------------------------------------------


class TestToolNotInPolicy:
    """When a tool is not matched by any rule, it runs without approval."""

    def test_ungated_tool_proceeds_directly(self) -> None:
        """call_tool for a tool NOT in rules skips approval entirely."""
        fix = _make_gate(rules=[ApprovalRule(tool_name="git_push")])
        ctx = MagicMock()
        tool = MagicMock()

        result = _run(fix.gate.call_tool("read_file", {"path": "x.py"}, ctx, tool))

        fix.channel.send.assert_not_called()
        fix.channel.receive.assert_not_called()
        fix.inner.call_tool.assert_called_once()
        assert result == "tool_result"

    def test_empty_policy_never_prompts(self) -> None:
        """An empty policy means every tool is ungated."""
        fix = _make_gate(rules=[])
        ctx = MagicMock()
        tool = MagicMock()

        result = _run(fix.gate.call_tool("git_push", {}, ctx, tool))

        fix.channel.send.assert_not_called()
        fix.inner.call_tool.assert_called_once()
        assert result == "tool_result"


# ---------------------------------------------------------------------------
# AC: Observability — approval events logged via hooks
# ---------------------------------------------------------------------------


class TestObservabilityHooks:
    """Approval decisions are emitted as hook events for observability."""

    def test_post_tool_use_hook_includes_approval_data(self) -> None:
        """POST_TOOL_USE hook payload should include approval_required flag."""
        hooks = HookRegistry()
        captured: list[dict[str, Any]] = []
        hooks.register(HookEvent.POST_TOOL_USE, captured.append)

        fix = _make_gate(
            rules=[ApprovalRule(tool_name="git_push")],
            hooks=hooks,
        )
        ctx = MagicMock()
        tool = MagicMock()

        _run(fix.gate.call_tool("git_push", {}, ctx, tool))

        assert len(captured) >= 1
        payload = captured[0]
        assert payload["tool_name"] == "git_push"
        assert payload["event_type"] == "approval_gate"
        assert "approval_required" in payload
        assert payload["approval_required"] is True

    def test_hook_records_approval_decision(self) -> None:
        """Hook payload should include the approval decision (approved/denied)."""
        hooks = HookRegistry()
        captured: list[dict[str, Any]] = []
        hooks.register(HookEvent.POST_TOOL_USE, captured.append)

        fix = _make_gate(
            rules=[ApprovalRule(tool_name="git_push")],
            hooks=hooks,
            channel=_make_channel(["no"]),
        )
        ctx = MagicMock()
        tool = MagicMock()

        _run(fix.gate.call_tool("git_push", {}, ctx, tool))

        assert len(captured) >= 1
        # At least one payload should indicate the denial
        decisions = [p for p in captured if "approval_decision" in p]
        assert len(decisions) >= 1
        assert decisions[0]["approval_decision"] == "denied"

    def test_ungated_tool_hook_shows_no_approval(self) -> None:
        """For ungated tools, hook should indicate approval was not required."""
        hooks = HookRegistry()
        captured: list[dict[str, Any]] = []
        hooks.register(HookEvent.POST_TOOL_USE, captured.append)

        fix = _make_gate(
            rules=[ApprovalRule(tool_name="git_push")],
            hooks=hooks,
        )
        ctx = MagicMock()
        tool = MagicMock()

        _run(fix.gate.call_tool("read_file", {}, ctx, tool))

        assert len(captured) >= 1
        payload = captured[0]
        assert payload["event_type"] == "approval_gate"
        assert payload.get("approval_required") is False


# ---------------------------------------------------------------------------
# AC: Mock channel — verify send/receive interaction
# ---------------------------------------------------------------------------


class TestChannelInteraction:
    """Verify the channel send/receive protocol during approval."""

    def test_receive_called_after_send(self) -> None:
        """channel.receive() is called after channel.send() for gated tools."""
        fix = _make_gate(rules=[ApprovalRule(tool_name="git_push")])
        ctx = MagicMock()
        tool = MagicMock()

        _run(fix.gate.call_tool("git_push", {}, ctx, tool))

        fix.channel.send.assert_called_once()
        fix.channel.receive.assert_called_once()

    def test_args_included_in_prompt(self) -> None:
        """The approval prompt should include tool arguments for context."""
        fix = _make_gate(rules=[ApprovalRule(tool_name="run_command")])
        ctx = MagicMock()
        tool = MagicMock()

        _run(fix.gate.call_tool("run_command", {"command": "rm -rf /"}, ctx, tool))

        prompt_text: str = fix.channel.send.call_args[0][0]
        assert "run_command" in prompt_text
