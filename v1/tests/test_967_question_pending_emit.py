"""Tests for task #967: Emit QUESTION_PENDING from AskUserToolset and ApprovalGateToolset.

Covers the contract for:
- QuestionPendingData TypedDict shape + __all__ export (hooks.py)
- Typed emit overload for HookEvent.QUESTION_PENDING (hooks.py)
- AskUserToolset hooks constructor param and emit behavior (ask_user.py)
- ApprovalGateToolset.call_tool() emit + skip conditions (gate.py)
- build_toolsets() passing hooks to AskUserToolset (bootstrap/toolsets.py)
- OwlBearSettings.notification_events default unchanged (config.py)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from owlbear.core.hooks import HookEvent, HookRegistry, QuestionPendingData
from owlbear.tools.ask_user import AskUserToolset

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_channel(receive_returns: list[str | None] | str | None = "yes") -> MagicMock:
    """Create a mock ChannelPlugin with configurable receive() responses."""
    ch = MagicMock()
    ch.name = "test"
    ch.send = AsyncMock()
    ch.send_blocks = AsyncMock()
    if isinstance(receive_returns, list):
        ch.receive = AsyncMock(side_effect=receive_returns)
    else:
        ch.receive = AsyncMock(return_value=receive_returns)
    return ch


@dataclass
class _GateFixture:
    """Bundle returned by :func:`_make_approval_gate`."""

    gate: object  # ApprovalGateToolset
    inner: MagicMock
    channel: MagicMock
    hooks: HookRegistry


def _make_approval_gate(
    *,
    rule_tool_name: str = "run_shell",
    receive: str | list[str | None] = "yes",
    hooks: HookRegistry | None = None,
) -> _GateFixture:
    """Build an ApprovalGateToolset requiring approval for *rule_tool_name*."""
    from conftest import make_mock_toolset  # type: ignore[import-untyped]

    from owlbear.safety.gate import ApprovalGateToolset
    from owlbear.safety.policy import ApprovalPolicy, ApprovalRule, ApprovalSession

    channel = _make_channel(receive)
    registry = hooks or HookRegistry()
    inner = make_mock_toolset()
    gate = ApprovalGateToolset(
        wrapped=inner,
        policy=ApprovalPolicy(rules=[ApprovalRule(tool_name=rule_tool_name)]),
        session=ApprovalSession(),
        channel=channel,
        hooks=registry,
    )
    return _GateFixture(gate=gate, inner=inner, channel=channel, hooks=registry)


# ---------------------------------------------------------------------------
# AC items 1-3: QuestionPendingData TypedDict, typed emit overload, __all__
# ---------------------------------------------------------------------------


class TestFromAC_967_QuestionPendingSchema:
    """QuestionPendingData TypedDict has the right shape; exported in __all__."""

    def test_source_and_question_are_required_keys(self) -> None:
        """source and question must be required keys of QuestionPendingData."""
        required = QuestionPendingData.__required_keys__
        assert "source" in required, "source must be a required key"
        assert "question" in required, "question must be a required key"

    def test_tool_name_is_not_required(self) -> None:
        """tool_name must be an optional (NotRequired) key."""
        optional = QuestionPendingData.__optional_keys__
        assert "tool_name" in optional, "tool_name must be NotRequired"

    def test_no_extra_keys(self) -> None:
        """QuestionPendingData must have exactly source, question, tool_name."""
        all_keys = QuestionPendingData.__required_keys__ | QuestionPendingData.__optional_keys__
        assert all_keys == {"source", "question", "tool_name"}

    def test_exported_in_hooks_all(self) -> None:
        """QuestionPendingData must appear in owlbear.core.hooks.__all__."""
        import owlbear.core.hooks as hooks_mod

        assert "QuestionPendingData" in hooks_mod.__all__

    @pytest.mark.asyncio
    async def test_emit_overload_accepts_question_pending_data(self) -> None:
        """HookRegistry.emit() must accept (QUESTION_PENDING, QuestionPendingData) without error."""
        registry = HookRegistry()
        received: list[object] = []

        async def handler(data: object) -> None:
            received.append(data)

        registry.register(HookEvent.QUESTION_PENDING, handler)
        payload: QuestionPendingData = {"source": "ask_user", "question": "Should I?"}
        await registry.emit(HookEvent.QUESTION_PENDING, payload)
        assert len(received) == 1
        assert received[0] == payload  # type: ignore[comparison-overlap]

    @pytest.mark.asyncio
    async def test_emit_overload_accepts_optional_tool_name(self) -> None:
        """QUESTION_PENDING emit with tool_name field must succeed."""
        registry = HookRegistry()
        received: list[object] = []

        async def handler(data: object) -> None:
            received.append(data)

        registry.register(HookEvent.QUESTION_PENDING, handler)
        payload: QuestionPendingData = {
            "source": "approval_gate",
            "question": "Approve run_shell?",
            "tool_name": "run_shell",
        }
        await registry.emit(HookEvent.QUESTION_PENDING, payload)
        assert received[0] == payload  # type: ignore[comparison-overlap]


# ---------------------------------------------------------------------------
# AC items 4-5: AskUserToolset hooks param + emit behavior
# ---------------------------------------------------------------------------


class TestFromAC_967_AskUserEmit:
    """AskUserToolset accepts hooks param; ask_user() emits QUESTION_PENDING before receive()."""

    def test_init_default_hooks_is_none(self) -> None:
        """AskUserToolset() without hooks argument stores _hooks=None."""
        ts = AskUserToolset(_make_channel())
        assert ts._hooks is None

    def test_init_stores_provided_hooks(self) -> None:
        """AskUserToolset(channel, hooks=registry) stores the registry in _hooks."""
        registry = HookRegistry()
        ts = AskUserToolset(_make_channel(), hooks=registry)
        assert ts._hooks is registry

    @pytest.mark.asyncio
    async def test_ask_user_emits_question_pending_before_receive(self) -> None:
        """QUESTION_PENDING must be emitted before channel.receive() is awaited."""
        call_order: list[str] = []

        registry = HookRegistry()

        async def on_pending(_data: object) -> None:
            call_order.append("emit")

        registry.register(HookEvent.QUESTION_PENDING, on_pending)

        ch = MagicMock()
        ch.send = AsyncMock()

        async def tracked_receive() -> str:
            call_order.append("receive")
            return "answer"

        ch.receive = tracked_receive

        ts = AskUserToolset(ch, hooks=registry)
        await ts.ask_user("Yes or no?")

        assert call_order.index("emit") < call_order.index("receive"), (
            "QUESTION_PENDING emit must precede channel.receive()"
        )

    @pytest.mark.asyncio
    async def test_ask_user_emits_source_is_ask_user(self) -> None:
        """QUESTION_PENDING payload must have source='ask_user'."""
        payloads: list[object] = []
        registry = HookRegistry()
        registry.register(HookEvent.QUESTION_PENDING, payloads.append)

        ts = AskUserToolset(_make_channel("reply"), hooks=registry)
        await ts.ask_user("What colour?")

        assert len(payloads) == 1
        payload = payloads[0]
        assert isinstance(payload, dict)
        assert payload["source"] == "ask_user"

    @pytest.mark.asyncio
    async def test_ask_user_emits_question_equals_formatted_prompt(self) -> None:
        """QUESTION_PENDING payload question must equal the text sent to the channel."""
        payloads: list[object] = []
        registry = HookRegistry()
        registry.register(HookEvent.QUESTION_PENDING, payloads.append)

        ch = _make_channel("1")
        ts = AskUserToolset(ch, hooks=registry)
        await ts.ask_user("Pick one", options=["alpha", "beta"])

        payload = payloads[0]
        assert isinstance(payload, dict)
        sent_text: str = ch.send.call_args[0][0]
        assert payload["question"] == sent_text, (
            "question in payload must match the formatted prompt sent to the channel"
        )

    @pytest.mark.asyncio
    async def test_ask_user_emits_exactly_once(self) -> None:
        """ask_user() must emit QUESTION_PENDING exactly once per invocation."""
        count = 0

        async def on_pending(_data: object) -> None:
            nonlocal count
            count += 1

        registry = HookRegistry()
        registry.register(HookEvent.QUESTION_PENDING, on_pending)

        ts = AskUserToolset(_make_channel("yes"), hooks=registry)
        await ts.ask_user("Confirm?")

        assert count == 1

    @pytest.mark.asyncio
    async def test_no_emit_when_hooks_is_none(self) -> None:
        """ask_user() must not raise when hooks=None (no hook registry configured)."""
        ts = AskUserToolset(_make_channel("fine"))
        # Must complete without error or AttributeError
        result = await ts.ask_user("Are you there?")
        assert result == "fine"


# ---------------------------------------------------------------------------
# AC item 6: ApprovalGateToolset.call_tool() emit + skip conditions
# ---------------------------------------------------------------------------


class TestFromAC_967_ApprovalGateEmit:
    """ApprovalGateToolset emits QUESTION_PENDING exactly once before approval receive()."""

    @pytest.mark.asyncio
    async def test_emits_question_pending_before_channel_receive(self) -> None:
        """QUESTION_PENDING must be emitted before channel.receive() during approval flow."""
        call_order: list[str] = []
        registry = HookRegistry()

        async def on_pending(_data: object) -> None:
            call_order.append("emit")

        registry.register(HookEvent.QUESTION_PENDING, on_pending)

        ch = MagicMock()
        ch.send = AsyncMock()
        ch.send_blocks = AsyncMock()

        async def tracked_receive() -> str:
            call_order.append("receive")
            return "yes"

        ch.receive = tracked_receive

        fix = _make_approval_gate(rule_tool_name="rm_rf", hooks=registry)
        # Override channel to track order but keep the hook registry
        fix.gate.channel = ch  # type: ignore[attr-defined]

        ctx = MagicMock()
        tool = MagicMock()
        await fix.gate.call_tool("rm_rf", {}, ctx, tool)

        assert "emit" in call_order, "QUESTION_PENDING was never emitted"
        assert "receive" in call_order, "channel.receive was never called"
        assert call_order.index("emit") < call_order.index("receive")

    @pytest.mark.asyncio
    async def test_question_pending_source_is_approval_gate(self) -> None:
        """QUESTION_PENDING payload must have source='approval_gate'."""
        payloads: list[object] = []
        registry = HookRegistry()
        registry.register(HookEvent.QUESTION_PENDING, payloads.append)

        fix = _make_approval_gate(rule_tool_name="delete", hooks=registry)
        ctx = MagicMock()
        tool = MagicMock()
        await fix.gate.call_tool("delete", {}, ctx, tool)

        assert len(payloads) >= 1
        assert payloads[0]["source"] == "approval_gate"  # type: ignore[index]

    @pytest.mark.asyncio
    async def test_question_pending_includes_gated_tool_name(self) -> None:
        """QUESTION_PENDING payload must include tool_name= the gated tool."""
        payloads: list[object] = []
        registry = HookRegistry()
        registry.register(HookEvent.QUESTION_PENDING, payloads.append)

        fix = _make_approval_gate(rule_tool_name="drop_db", hooks=registry)
        ctx = MagicMock()
        tool = MagicMock()
        await fix.gate.call_tool("drop_db", {}, ctx, tool)

        payload = payloads[0]
        assert isinstance(payload, dict)
        assert payload.get("tool_name") == "drop_db"

    @pytest.mark.asyncio
    async def test_question_pending_question_is_fallback_text(self) -> None:
        """QUESTION_PENDING question field must contain the approval prompt fallback text."""
        payloads: list[object] = []
        registry = HookRegistry()
        registry.register(HookEvent.QUESTION_PENDING, payloads.append)

        fix = _make_approval_gate(rule_tool_name="exec_cmd", hooks=registry)
        ctx = MagicMock()
        tool = MagicMock()
        await fix.gate.call_tool("exec_cmd", {}, ctx, tool)

        payload = payloads[0]
        assert isinstance(payload, dict)
        question: str = payload["question"]  # type: ignore[index]
        # The fallback approval text must reference the tool name
        assert "exec_cmd" in question

    @pytest.mark.asyncio
    async def test_no_emit_when_approval_not_required(self) -> None:
        """QUESTION_PENDING must NOT be emitted when the policy does not require approval."""
        from conftest import make_mock_toolset  # type: ignore[import-untyped]

        from owlbear.safety.gate import ApprovalGateToolset
        from owlbear.safety.policy import ApprovalPolicy, ApprovalSession

        payloads: list[object] = []
        registry = HookRegistry()
        registry.register(HookEvent.QUESTION_PENDING, payloads.append)

        # Empty policy — nothing requires approval
        gate = ApprovalGateToolset(
            wrapped=make_mock_toolset(),
            policy=ApprovalPolicy(rules=[]),
            session=ApprovalSession(),
            channel=_make_channel(),
            hooks=registry,
        )
        ctx = MagicMock()
        tool = MagicMock()
        await gate.call_tool("safe_tool", {}, ctx, tool)

        assert len(payloads) == 0, "QUESTION_PENDING must not fire when approval is not required"

    @pytest.mark.asyncio
    async def test_no_emit_when_pre_granted(self) -> None:
        """QUESTION_PENDING must NOT be emitted when the tool is pre-granted in the session."""
        from owlbear.safety.policy import ApprovalSession

        payloads: list[object] = []
        registry = HookRegistry()
        registry.register(HookEvent.QUESTION_PENDING, payloads.append)

        session = ApprovalSession()
        session.grant("privileged_op", ttl=300.0, max_uses=10)

        fix = _make_approval_gate(rule_tool_name="privileged_op", hooks=registry)
        fix.gate.session = session  # type: ignore[attr-defined]

        ctx = MagicMock()
        tool = MagicMock()
        await fix.gate.call_tool("privileged_op", {}, ctx, tool)

        assert len(payloads) == 0, "QUESTION_PENDING must not fire when tool is pre-granted"


# ---------------------------------------------------------------------------
# AC item 7: build_toolsets() passes hooks to AskUserToolset — EXPECTED TO FAIL
# ---------------------------------------------------------------------------


class TestFromAC_967_BuildToolsetsHooksWiring:
    """build_toolsets() must wire the hooks registry into AskUserToolset."""

    def test_ask_user_toolset_receives_hooks_from_build_toolsets(self, tmp_path: Path) -> None:
        """AskUserToolset inside build_toolsets output must have _hooks == passed registry."""
        from owlbear.bootstrap.toolsets import build_toolsets
        from owlbear.config import OwlBearSettings
        from owlbear.tools.hooked import HookedToolset

        settings = OwlBearSettings(approval_policy=[])
        hooks = HookRegistry()
        channel = MagicMock()
        channel.name = "test"

        toolsets, *_ = build_toolsets(settings, tmp_path, hooks, channel)

        ask_user_instances = [
            ts.wrapped
            for ts in toolsets
            if isinstance(ts, HookedToolset) and isinstance(ts.wrapped, AskUserToolset)
        ]
        assert len(ask_user_instances) == 1, (
            "Expected exactly one AskUserToolset in HookedToolset in build_toolsets output"
        )
        ask_user_ts: AskUserToolset = ask_user_instances[0]
        assert ask_user_ts._hooks is hooks, (
            "build_toolsets() must pass hooks=hooks to AskUserToolset; "
            f"got _hooks={ask_user_ts._hooks!r}"
        )


# ---------------------------------------------------------------------------
# AC item 8: OwlBearSettings.notification_events default unchanged
# ---------------------------------------------------------------------------


class TestFromAC_967_NotificationEventsDefault:
    """OwlBearSettings.notification_events default must not include question_pending."""

    def test_default_excludes_question_pending(self) -> None:
        """Default notification_events must be ['task_complete', 'on_error'] only."""
        from owlbear.config import OwlBearSettings

        settings = OwlBearSettings()
        assert "question_pending" not in settings.notification_events

    def test_default_contains_task_complete_and_on_error(self) -> None:
        """Default notification_events must contain task_complete and on_error."""
        from owlbear.config import OwlBearSettings

        settings = OwlBearSettings()
        assert "task_complete" in settings.notification_events
        assert "on_error" in settings.notification_events
