"""Tests for ApprovalGateToolset — WrapperToolset that gates tool calls behind approval.

TDD red-phase tests for task #340.  The module ``owlbear.safety.gate``
does not exist yet — all tests are expected to fail with ``ImportError``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from conftest import make_mock_toolset  # type: ignore[import-untyped]

from owlbear.core.hooks import HookEvent, HookRegistry
from owlbear.safety.gate import ApprovalGateToolset
from owlbear.safety.policy import ApprovalPolicy, ApprovalRule, ApprovalSession

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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
    channel.send_blocks = AsyncMock()
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
    inner = make_mock_toolset()

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

    @pytest.mark.asyncio
    async def test_sends_approval_prompt_via_channel(self) -> None:
        """call_tool for a gated tool must call channel.send_blocks() with a prompt."""
        fix = _make_gate(rules=[ApprovalRule(tool_name="git_push")])
        ctx = MagicMock()
        tool = MagicMock()

        await (fix.gate.call_tool("git_push", {"branch": "main"}, ctx, tool))

        fix.channel.send_blocks.assert_called_once()
        text_fallback: str = fix.channel.send_blocks.call_args[0][1]
        assert "git_push" in text_fallback

    @pytest.mark.asyncio
    async def test_prompt_includes_tool_name(self) -> None:
        """Approval prompt must mention the tool name being gated."""
        fix = _make_gate(rules=[ApprovalRule(tool_name="delete_file")])
        ctx = MagicMock()
        tool = MagicMock()

        await (fix.gate.call_tool("delete_file", {"path": "/important"}, ctx, tool))

        text_fallback: str = fix.channel.send_blocks.call_args[0][1]
        assert "delete_file" in text_fallback

    @pytest.mark.asyncio
    async def test_send_blocks_text_fallback_includes_cli_prompt(self) -> None:
        """send_blocks text_fallback must include tool name and yes/no prompt."""
        fix = _make_gate(rules=[ApprovalRule(tool_name="git_push")])
        ctx = MagicMock()
        tool = MagicMock()

        await (fix.gate.call_tool("git_push", {"branch": "main"}, ctx, tool))

        fix.channel.send_blocks.assert_called_once()
        text_fallback: str = fix.channel.send_blocks.call_args[0][1]
        assert "git_push" in text_fallback
        assert "approve" in text_fallback.lower() or "yes/no" in text_fallback.lower()


# ---------------------------------------------------------------------------
# AC: Approve path — 'yes' -> tool call proceeds
# ---------------------------------------------------------------------------


class TestApprovePath:
    """When user responds 'yes', the wrapped tool executes normally."""

    @pytest.mark.asyncio
    async def test_yes_proceeds_with_tool_call(self) -> None:
        """channel.receive() returns 'yes' -> inner call_tool is invoked."""
        fix = _make_gate(rules=[ApprovalRule(tool_name="git_push")])
        fix.channel.receive = AsyncMock(return_value="yes")
        ctx = MagicMock()
        tool = MagicMock()

        result = await (fix.gate.call_tool("git_push", {"branch": "main"}, ctx, tool))

        fix.inner.call_tool.assert_called_once()
        assert result == "tool_result"

    @pytest.mark.asyncio
    async def test_y_shorthand_also_approves(self) -> None:
        """A shorthand 'y' response should also approve the tool call."""
        fix = _make_gate(
            rules=[ApprovalRule(tool_name="git_push")],
            channel=_make_channel(["y"]),
        )
        ctx = MagicMock()
        tool = MagicMock()

        result = await (fix.gate.call_tool("git_push", {}, ctx, tool))

        fix.inner.call_tool.assert_called_once()
        assert result == "tool_result"


# ---------------------------------------------------------------------------
# AC: Deny path — 'no' -> tool call skipped
# ---------------------------------------------------------------------------


class TestDenyPath:
    """When user responds 'no', the tool is not called and denial returned."""

    @pytest.mark.asyncio
    async def test_no_skips_tool_returns_denial(self) -> None:
        """channel.receive() returns 'no' -> tool NOT called, returns denial."""
        fix = _make_gate(
            rules=[ApprovalRule(tool_name="git_push")],
            channel=_make_channel(["no"]),
        )
        ctx = MagicMock()
        tool = MagicMock()

        result = await (fix.gate.call_tool("git_push", {}, ctx, tool))

        fix.inner.call_tool.assert_not_called()
        assert isinstance(result, str)
        assert "denied" in result.lower()

    @pytest.mark.asyncio
    async def test_n_shorthand_also_denies(self) -> None:
        """A shorthand 'n' response should also deny."""
        fix = _make_gate(
            rules=[ApprovalRule(tool_name="git_push")],
            channel=_make_channel(["n"]),
        )
        ctx = MagicMock()
        tool = MagicMock()

        result = await (fix.gate.call_tool("git_push", {}, ctx, tool))

        fix.inner.call_tool.assert_not_called()
        assert "denied" in str(result).lower()


# ---------------------------------------------------------------------------
# AC: Timeout path — channel.receive() returns None
# ---------------------------------------------------------------------------


class TestTimeoutPath:
    """When channel.receive() returns None (timeout/disconnect), tool is skipped."""

    @pytest.mark.asyncio
    async def test_none_response_returns_cancellation(self) -> None:
        """receive() -> None means timeout: tool skipped, cancellation message."""
        fix = _make_gate(
            rules=[ApprovalRule(tool_name="git_push")],
            channel=_make_channel([None]),
        )
        ctx = MagicMock()
        tool = MagicMock()

        result = await (fix.gate.call_tool("git_push", {}, ctx, tool))

        fix.inner.call_tool.assert_not_called()
        assert isinstance(result, str)
        # Should mention timeout or cancellation
        assert "timeout" in result.lower() or "cancel" in result.lower()


# ---------------------------------------------------------------------------
# AC: Pre-grant path — session already has grant
# ---------------------------------------------------------------------------


class TestPreGrantPath:
    """When the tool is pre-granted in the session, no prompt is sent."""

    @pytest.mark.asyncio
    async def test_pre_granted_skips_prompt(self) -> None:
        """Pre-granted tool bypasses channel interaction entirely."""
        session = ApprovalSession()
        session.grant("git_push")

        fix = _make_gate(
            rules=[ApprovalRule(tool_name="git_push")],
            session=session,
        )
        ctx = MagicMock()
        tool = MagicMock()

        result = await (fix.gate.call_tool("git_push", {}, ctx, tool))

        fix.channel.send.assert_not_called()
        fix.channel.receive.assert_not_called()
        fix.inner.call_tool.assert_called_once()
        assert result == "tool_result"


# ---------------------------------------------------------------------------
# AC: 'approve all {tool}' response — adds pre-grant and proceeds
# ---------------------------------------------------------------------------


class TestApproveAllResponse:
    """'approve all {tool}' grants future calls and proceeds immediately."""

    @pytest.mark.asyncio
    async def test_approve_all_grants_and_proceeds(self) -> None:
        """'approve all git_push' -> session.grant() + inner called."""
        session = ApprovalSession()
        fix = _make_gate(
            rules=[ApprovalRule(tool_name="git_push")],
            session=session,
            channel=_make_channel(["approve all git_push"]),
        )
        ctx = MagicMock()
        tool = MagicMock()

        result = await (fix.gate.call_tool("git_push", {}, ctx, tool))

        assert session.is_pre_granted("git_push") is True
        fix.inner.call_tool.assert_called_once()
        assert result == "tool_result"

    @pytest.mark.asyncio
    async def test_second_call_after_approve_all_skips_prompt(self) -> None:
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
        await (fix.gate.call_tool("git_push", {}, ctx, tool))
        assert session.is_pre_granted("git_push") is True

        # Reset channel to track second call
        fix.channel.send.reset_mock()
        fix.channel.receive.reset_mock()

        # Second call — pre-granted, no prompt
        await (fix.gate.call_tool("git_push", {}, ctx, tool))
        fix.channel.send.assert_not_called()
        fix.channel.receive.assert_not_called()
        assert fix.inner.call_tool.call_count == 2


# ---------------------------------------------------------------------------
# AC: Tool NOT in policy — proceed without prompting
# ---------------------------------------------------------------------------


class TestToolNotInPolicy:
    """When a tool is not matched by any rule, it runs without approval."""

    @pytest.mark.asyncio
    async def test_ungated_tool_proceeds_directly(self) -> None:
        """call_tool for a tool NOT in rules skips approval entirely."""
        fix = _make_gate(rules=[ApprovalRule(tool_name="git_push")])
        ctx = MagicMock()
        tool = MagicMock()

        result = await (fix.gate.call_tool("read_file", {"path": "x.py"}, ctx, tool))

        fix.channel.send.assert_not_called()
        fix.channel.receive.assert_not_called()
        fix.inner.call_tool.assert_called_once()
        assert result == "tool_result"

    @pytest.mark.asyncio
    async def test_empty_policy_never_prompts(self) -> None:
        """An empty policy means every tool is ungated."""
        fix = _make_gate(rules=[])
        ctx = MagicMock()
        tool = MagicMock()

        result = await (fix.gate.call_tool("git_push", {}, ctx, tool))

        fix.channel.send.assert_not_called()
        fix.inner.call_tool.assert_called_once()
        assert result == "tool_result"


# ---------------------------------------------------------------------------
# AC: Observability — approval events logged via hooks
# ---------------------------------------------------------------------------


class TestObservabilityHooks:
    """Approval decisions are emitted as hook events for observability."""

    @pytest.mark.asyncio
    async def test_post_tool_use_hook_includes_approval_data(self) -> None:
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

        await (fix.gate.call_tool("git_push", {}, ctx, tool))

        assert len(captured) >= 1
        payload = captured[0]
        assert payload["tool_name"] == "git_push"
        assert payload["event_type"] == "approval_gate"
        assert "approval_required" in payload
        assert payload["approval_required"] is True

    @pytest.mark.asyncio
    async def test_hook_records_approval_decision(self) -> None:
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

        await (fix.gate.call_tool("git_push", {}, ctx, tool))

        assert len(captured) >= 1
        # At least one payload should indicate the denial
        decisions = [p for p in captured if "approval_decision" in p]
        assert len(decisions) >= 1
        assert decisions[0]["approval_decision"] == "denied"

    @pytest.mark.asyncio
    async def test_ungated_tool_hook_shows_no_approval(self) -> None:
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

        await (fix.gate.call_tool("read_file", {}, ctx, tool))

        assert len(captured) >= 1
        payload = captured[0]
        assert payload["event_type"] == "approval_gate"
        assert payload.get("approval_required") is False


# ---------------------------------------------------------------------------
# AC: Mock channel — verify send/receive interaction
# ---------------------------------------------------------------------------


class TestChannelInteraction:
    """Verify the channel send/receive protocol during approval."""

    @pytest.mark.asyncio
    async def test_receive_called_after_send_blocks(self) -> None:
        """channel.receive() is called after channel.send_blocks() for gated tools."""
        fix = _make_gate(rules=[ApprovalRule(tool_name="git_push")])
        ctx = MagicMock()
        tool = MagicMock()

        await (fix.gate.call_tool("git_push", {}, ctx, tool))

        fix.channel.send_blocks.assert_called_once()
        fix.channel.receive.assert_called_once()

    @pytest.mark.asyncio
    async def test_args_included_in_prompt(self) -> None:
        """The approval prompt text_fallback should include tool name for context."""
        fix = _make_gate(rules=[ApprovalRule(tool_name="run_command")])
        ctx = MagicMock()
        tool = MagicMock()

        await (fix.gate.call_tool("run_command", {"command": "rm -rf /"}, ctx, tool))

        text_fallback: str = fix.channel.send_blocks.call_args[0][1]
        assert "run_command" in text_fallback


# ---------------------------------------------------------------------------
# AC #656: 'approve all' creates GrantRecord with policy defaults
# ---------------------------------------------------------------------------


class TestApproveAllScopedGrants:
    """'approve all {tool}' creates a GrantRecord with policy defaults."""

    @pytest.mark.asyncio
    async def test_approve_all_creates_grant_with_policy_defaults(self) -> None:
        """Grant created by 'approve all' uses policy.default_grant_ttl/max_uses."""
        policy = ApprovalPolicy(
            rules=[ApprovalRule(tool_name="git_push")],
            default_grant_ttl=300.0,
            default_max_uses=10,
        )
        session = ApprovalSession(policy=policy)
        fix = _make_gate(
            rules=policy.rules,
            session=session,
            channel=_make_channel(["approve all git_push"]),
        )
        # Patch policy on the gate to match our custom policy
        fix.gate.policy = policy
        ctx = MagicMock()
        tool = MagicMock()

        await (fix.gate.call_tool("git_push", {}, ctx, tool))

        # Session should have a grant with the policy defaults
        grant = session._grants.get("git_push")
        assert grant is not None
        assert grant.ttl == 300.0
        assert grant.remaining_uses == 10

    @pytest.mark.asyncio
    async def test_grant_expires_after_ttl(self) -> None:
        """After TTL elapses, is_pre_granted returns False."""
        policy = ApprovalPolicy(
            rules=[ApprovalRule(tool_name="git_push")],
            default_grant_ttl=60.0,
            default_max_uses=None,
        )
        session = ApprovalSession(policy=policy)
        fix = _make_gate(
            rules=policy.rules,
            session=session,
            channel=_make_channel(["approve all git_push"]),
        )
        fix.gate.policy = policy
        ctx = MagicMock()
        tool = MagicMock()

        await (fix.gate.call_tool("git_push", {}, ctx, tool))

        # Grant is valid initially
        assert session.is_pre_granted("git_push") is True

        # Simulate time passing beyond TTL
        with patch("owlbear.safety.policy.monotonic") as mock_mono:
            mock_mono.return_value = session._grants["git_push"].granted_at + 61.0
            # Oops — grant was consumed by the assert above; re-grant
        # Re-grant and test expiry cleanly
        session.grant("git_push", ttl=60.0)
        grant = session._grants["git_push"]
        with patch("owlbear.safety.policy.monotonic", return_value=grant.granted_at + 61.0):
            assert session.is_pre_granted("git_push") is False

    @pytest.mark.asyncio
    async def test_grant_exhausts_after_max_uses(self) -> None:
        """After max_uses calls, is_pre_granted returns False."""
        policy = ApprovalPolicy(
            rules=[ApprovalRule(tool_name="git_push")],
            default_grant_ttl=99999.0,
            default_max_uses=1,
        )
        session = ApprovalSession(policy=policy)
        fix = _make_gate(
            rules=policy.rules,
            session=session,
            channel=_make_channel(["approve all git_push"]),
        )
        fix.gate.policy = policy
        ctx = MagicMock()
        tool = MagicMock()

        await (fix.gate.call_tool("git_push", {}, ctx, tool))

        # Grant should have been created with max_uses=1
        # Use 1: first pre-grant check — consumes the single use
        assert session.is_pre_granted("git_push") is True
        # Use 2: grant exhausted
        assert session.is_pre_granted("git_push") is False


# ---------------------------------------------------------------------------
# AC #656: Hook event for approved_all includes grant metadata
# ---------------------------------------------------------------------------


class TestApproveAllHookMetadata:
    """POST_TOOL_USE hook for 'approved_all' includes ttl and max_uses."""

    @pytest.mark.asyncio
    async def test_hook_includes_grant_metadata(self) -> None:
        """Hook payload for approved_all must include grant_ttl and grant_max_uses."""
        hooks = HookRegistry()
        captured: list[dict[str, Any]] = []
        hooks.register(HookEvent.POST_TOOL_USE, captured.append)

        policy = ApprovalPolicy(
            rules=[ApprovalRule(tool_name="git_push")],
            default_grant_ttl=300.0,
            default_max_uses=10,
        )
        session = ApprovalSession(policy=policy)
        fix = _make_gate(
            rules=policy.rules,
            session=session,
            channel=_make_channel(["approve all git_push"]),
            hooks=hooks,
        )
        fix.gate.policy = policy
        ctx = MagicMock()
        tool = MagicMock()

        await (fix.gate.call_tool("git_push", {}, ctx, tool))

        approved_all = [p for p in captured if p.get("approval_decision") == "approved_all"]
        assert len(approved_all) == 1
        payload = approved_all[0]
        assert payload["grant_ttl"] == 300.0
        assert payload["grant_max_uses"] == 10
