"""Tests for QUESTION_PENDING emission from AskUserToolset and ApprovalGateToolset.

TDD RED-phase tests for task #970.  ``QuestionPendingData`` is not yet exported
from ``owlbear.core.hooks`` — all tests fail with ``ImportError`` in RED phase.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from conftest import make_mock_toolset  # type: ignore[import-untyped]

from owlbear.config import OwlBearSettings
from owlbear.core.hooks import (
    HookEvent,
    HookRegistry,
    QuestionPendingData,  # does not exist yet → ImportError (RED trigger)
)
from owlbear.safety.gate import ApprovalGateToolset
from owlbear.safety.policy import ApprovalPolicy, ApprovalRule, ApprovalSession
from owlbear.tools.ask_user import AskUserToolset

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_channel(receive_response: str | None = "ok") -> MagicMock:
    ch = MagicMock()
    ch.name = "test"
    ch.send = AsyncMock()
    ch.send_blocks = AsyncMock()
    ch.receive = AsyncMock(return_value=receive_response)
    return ch


def _make_gate(
    *,
    rules: list[ApprovalRule] | None = None,
    hooks: HookRegistry | None = None,
    channel: MagicMock | None = None,
    session: ApprovalSession | None = None,
) -> ApprovalGateToolset:
    inner = make_mock_toolset()
    policy = ApprovalPolicy(rules=rules or [])
    return ApprovalGateToolset(
        wrapped=inner,
        policy=policy,
        session=session or ApprovalSession(),
        channel=channel or _make_channel(),
        hooks=hooks or HookRegistry(),
    )


# ---------------------------------------------------------------------------
# QuestionPendingData TypedDict structure
# ---------------------------------------------------------------------------


class TestFromAC_QuestionPendingData:
    """``QuestionPendingData`` TypedDict must have the correct key contract."""

    def test_source_is_required_key(self) -> None:
        """``source`` must be a required key."""
        assert "source" in QuestionPendingData.__required_keys__

    def test_question_is_required_key(self) -> None:
        """``question`` must be a required key."""
        assert "question" in QuestionPendingData.__required_keys__

    def test_tool_name_is_optional_key(self) -> None:
        """``tool_name`` (NotRequired) must be registered as an optional key."""
        assert "tool_name" in QuestionPendingData.__optional_keys__

    def test_only_source_and_question_are_required(self) -> None:
        """Exactly two required keys: source and question."""
        assert QuestionPendingData.__required_keys__ == frozenset({"source", "question"})

    def test_instantiation_with_required_keys_only(self) -> None:
        """TypedDict can be instantiated with just source and question."""
        data: QuestionPendingData = {"source": "ask_user", "question": "Are you there?"}
        assert data["source"] == "ask_user"
        assert data["question"] == "Are you there?"

    def test_instantiation_with_optional_tool_name(self) -> None:
        """TypedDict can include the optional tool_name."""
        data: QuestionPendingData = {
            "source": "approval_gate",
            "question": "Approve?",
            "tool_name": "delete_file",
        }
        assert data["tool_name"] == "delete_file"


# ---------------------------------------------------------------------------
# AskUserToolset — QUESTION_PENDING emission
# ---------------------------------------------------------------------------


class TestFromAC_AskUserEmitsQuestionPending:
    """``AskUserToolset.ask_user()`` must emit QUESTION_PENDING before channel.receive()."""

    @pytest.mark.asyncio
    async def test_emits_question_pending_before_receive(self) -> None:
        """QUESTION_PENDING must be emitted before channel.receive() is awaited."""
        call_order: list[str] = []

        channel = MagicMock()
        channel.send = AsyncMock()

        async def _receive() -> str:
            call_order.append("receive")
            return "answer"

        channel.receive = AsyncMock(side_effect=_receive)

        hooks = HookRegistry()

        async def _on_pending(_data: object) -> None:
            call_order.append("question_pending")

        hooks.register(HookEvent.QUESTION_PENDING, _on_pending)  # type: ignore[arg-type]

        ts = AskUserToolset(channel, hooks=hooks)
        await ts.ask_user("Who are you?")

        assert "question_pending" in call_order
        assert "receive" in call_order
        assert call_order.index("question_pending") < call_order.index("receive")

    @pytest.mark.asyncio
    async def test_emit_source_is_ask_user(self) -> None:
        """Emitted QUESTION_PENDING data must have source='ask_user'."""
        channel = _make_channel("yes")
        emitted: list[dict[str, Any]] = []

        hooks = HookRegistry()
        hooks.register(HookEvent.QUESTION_PENDING, emitted.append)  # type: ignore[arg-type]

        ts = AskUserToolset(channel, hooks=hooks)
        await ts.ask_user("Ready?")

        assert len(emitted) == 1
        assert emitted[0]["source"] == "ask_user"

    @pytest.mark.asyncio
    async def test_emit_question_matches_plain_question(self) -> None:
        """Emitted QUESTION_PENDING data must have question= the formatted prompt text."""
        channel = _make_channel("yes")
        emitted: list[dict[str, Any]] = []

        hooks = HookRegistry()
        hooks.register(HookEvent.QUESTION_PENDING, emitted.append)  # type: ignore[arg-type]

        ts = AskUserToolset(channel, hooks=hooks)
        await ts.ask_user("What is 2+2?")

        assert len(emitted) == 1
        assert emitted[0]["question"] == "What is 2+2?"

    @pytest.mark.asyncio
    async def test_emit_question_is_formatted_prompt_with_options(self) -> None:
        """With options, question= must be the multi-line formatted prompt."""
        channel = _make_channel("1")
        emitted: list[dict[str, Any]] = []

        hooks = HookRegistry()
        hooks.register(HookEvent.QUESTION_PENDING, emitted.append)  # type: ignore[arg-type]

        ts = AskUserToolset(channel, hooks=hooks)
        await ts.ask_user("Pick one:", options=["alpha", "beta"])

        assert len(emitted) == 1
        assert "alpha" in emitted[0]["question"]
        assert "beta" in emitted[0]["question"]

    @pytest.mark.asyncio
    async def test_emits_exactly_once_per_call(self) -> None:
        """QUESTION_PENDING must be emitted exactly once per ask_user() invocation."""
        channel = _make_channel("yes")
        emitted: list[dict[str, Any]] = []

        hooks = HookRegistry()
        hooks.register(HookEvent.QUESTION_PENDING, emitted.append)  # type: ignore[arg-type]

        ts = AskUserToolset(channel, hooks=hooks)
        await ts.ask_user("Only once?")

        assert len(emitted) == 1


# ---------------------------------------------------------------------------
# AskUserToolset — hooks=None does not error
# ---------------------------------------------------------------------------


class TestFromAC_AskUserNullHooks:
    """``AskUserToolset(channel, hooks=None)`` must not raise on ask_user()."""

    @pytest.mark.asyncio
    async def test_hooks_none_does_not_raise(self) -> None:
        """Passing hooks=None must not cause any error during ask_user()."""
        channel = _make_channel("response")
        ts = AskUserToolset(channel, hooks=None)
        result = await ts.ask_user("Say hi.")
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_hooks_absent_by_default_does_not_raise(self) -> None:
        """When hooks is omitted, ask_user() still works without errors."""
        channel = _make_channel("response")
        ts = AskUserToolset(channel)
        result = await ts.ask_user("No hooks here.")
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# ApprovalGateToolset — QUESTION_PENDING emission
# ---------------------------------------------------------------------------


class TestFromAC_ApprovalGateEmitsQuestionPending:
    """``ApprovalGateToolset.call_tool()`` must emit QUESTION_PENDING before receive()."""

    @pytest.mark.asyncio
    async def test_emits_question_pending_before_receive(self) -> None:
        """QUESTION_PENDING must be emitted before channel.receive() is called."""
        call_order: list[str] = []

        channel = MagicMock()
        channel.send = AsyncMock()
        channel.send_blocks = AsyncMock()

        async def _receive() -> str:
            call_order.append("receive")
            return "yes"

        channel.receive = AsyncMock(side_effect=_receive)

        hooks = HookRegistry()

        async def _on_pending(_data: object) -> None:
            call_order.append("question_pending")

        hooks.register(HookEvent.QUESTION_PENDING, _on_pending)  # type: ignore[arg-type]

        gate = _make_gate(
            rules=[ApprovalRule(tool_name="delete_file")],
            hooks=hooks,
            channel=channel,
        )
        ctx = MagicMock()
        tool = MagicMock()
        await gate.call_tool("delete_file", {}, ctx, tool)

        assert "question_pending" in call_order
        assert "receive" in call_order
        assert call_order.index("question_pending") < call_order.index("receive")

    @pytest.mark.asyncio
    async def test_emit_source_is_approval_gate(self) -> None:
        """Emitted QUESTION_PENDING data must have source='approval_gate'."""
        channel = _make_channel("yes")
        emitted: list[dict[str, Any]] = []

        hooks = HookRegistry()
        hooks.register(HookEvent.QUESTION_PENDING, emitted.append)  # type: ignore[arg-type]

        gate = _make_gate(
            rules=[ApprovalRule(tool_name="git_push")],
            hooks=hooks,
            channel=channel,
        )
        ctx = MagicMock()
        tool = MagicMock()
        await gate.call_tool("git_push", {"branch": "main"}, ctx, tool)

        assert len(emitted) >= 1
        assert emitted[0]["source"] == "approval_gate"

    @pytest.mark.asyncio
    async def test_emit_question_contains_prompt_text(self) -> None:
        """Emitted QUESTION_PENDING data must have a non-empty question= string."""
        channel = _make_channel("yes")
        emitted: list[dict[str, Any]] = []

        hooks = HookRegistry()
        hooks.register(HookEvent.QUESTION_PENDING, emitted.append)  # type: ignore[arg-type]

        gate = _make_gate(
            rules=[ApprovalRule(tool_name="git_push")],
            hooks=hooks,
            channel=channel,
        )
        ctx = MagicMock()
        tool = MagicMock()
        await gate.call_tool("git_push", {"branch": "main"}, ctx, tool)

        assert len(emitted) >= 1
        assert isinstance(emitted[0]["question"], str)
        assert len(emitted[0]["question"]) > 0

    @pytest.mark.asyncio
    async def test_emit_tool_name_matches_gated_tool(self) -> None:
        """Emitted QUESTION_PENDING data must have tool_name= equal to the gated tool."""
        channel = _make_channel("yes")
        emitted: list[dict[str, Any]] = []

        hooks = HookRegistry()
        hooks.register(HookEvent.QUESTION_PENDING, emitted.append)  # type: ignore[arg-type]

        gate = _make_gate(
            rules=[ApprovalRule(tool_name="delete_file")],
            hooks=hooks,
            channel=channel,
        )
        ctx = MagicMock()
        tool = MagicMock()
        await gate.call_tool("delete_file", {"path": "/test/x"}, ctx, tool)

        assert len(emitted) >= 1
        assert emitted[0]["tool_name"] == "delete_file"

    @pytest.mark.asyncio
    async def test_no_emit_when_approval_not_required(self) -> None:
        """QUESTION_PENDING must NOT be emitted when the tool does not need approval."""
        channel = _make_channel("yes")
        emitted: list[dict[str, Any]] = []

        hooks = HookRegistry()
        hooks.register(HookEvent.QUESTION_PENDING, emitted.append)  # type: ignore[arg-type]

        # No rules → no tool requires approval
        gate = _make_gate(rules=[], hooks=hooks, channel=channel)
        ctx = MagicMock()
        tool = MagicMock()
        await gate.call_tool("harmless_tool", {}, ctx, tool)

        assert emitted == []

    @pytest.mark.asyncio
    async def test_no_emit_when_pre_granted(self) -> None:
        """QUESTION_PENDING must NOT be emitted when the tool is already pre-granted."""
        channel = _make_channel("yes")
        emitted: list[dict[str, Any]] = []

        hooks = HookRegistry()
        hooks.register(HookEvent.QUESTION_PENDING, emitted.append)  # type: ignore[arg-type]

        session = ApprovalSession()
        session.grant("git_push")  # pre-grant with no TTL/use-limit

        gate = _make_gate(
            rules=[ApprovalRule(tool_name="git_push")],
            hooks=hooks,
            channel=channel,
            session=session,
        )
        ctx = MagicMock()
        tool = MagicMock()
        await gate.call_tool("git_push", {}, ctx, tool)

        assert emitted == []


# ---------------------------------------------------------------------------
# OwlBearSettings — notification_events default
# ---------------------------------------------------------------------------


class TestFromAC_NotificationEventsDefault:
    """``OwlBearSettings().notification_events`` default must NOT include 'question_pending'."""

    def test_question_pending_not_in_default_notification_events(
        self, default_settings: OwlBearSettings
    ) -> None:
        """question_pending must not be in the default notification event list."""
        assert "question_pending" not in default_settings.notification_events

    def test_default_notification_events_unchanged(self, default_settings: OwlBearSettings) -> None:
        """Default notification events must be exactly task_complete and on_error."""
        assert set(default_settings.notification_events) == {"task_complete", "on_error"}


# ---------------------------------------------------------------------------
# Strengthen: QuestionPendingData value type annotations (reviewer gap 1)
# ---------------------------------------------------------------------------


class TestFromAC_970_QuestionPendingDataTypeAnnotations:
    """``QuestionPendingData`` value annotations must be exactly str / NotRequired[str]."""

    def test_source_annotation_is_str(self) -> None:
        """``source`` must be annotated as ``str``, not a subtype or alias."""
        from typing import get_type_hints

        hints = get_type_hints(QuestionPendingData, include_extras=True)
        assert hints["source"] is str

    def test_question_annotation_is_str(self) -> None:
        """``question`` must be annotated as ``str``."""
        from typing import get_type_hints

        hints = get_type_hints(QuestionPendingData, include_extras=True)
        assert hints["question"] is str

    def test_tool_name_annotation_is_not_required_str(self) -> None:
        """``tool_name`` must be annotated as ``NotRequired[str]``."""
        from typing import NotRequired, get_type_hints

        hints = get_type_hints(QuestionPendingData, include_extras=True)
        assert hints["tool_name"] == NotRequired[str]


# ---------------------------------------------------------------------------
# Strengthen: AskUser emitted question equals exactly the formatted prompt
# (reviewer gap 2 — options branch only checked substrings)
# ---------------------------------------------------------------------------


class TestFromAC_970_AskUserExactFormattedPrompt:
    """The emitted ``question`` must equal the exact formatted prompt, not just contain it."""

    @pytest.mark.asyncio
    async def test_emit_question_is_exact_plain_question(self) -> None:
        """No-options question emitted verbatim, no extra whitespace or wrapping."""
        channel = _make_channel("yes")
        emitted: list[dict[str, Any]] = []

        hooks = HookRegistry()
        hooks.register(HookEvent.QUESTION_PENDING, emitted.append)  # type: ignore[arg-type]

        ts = AskUserToolset(channel, hooks=hooks)
        await ts.ask_user("Are you sure?")

        assert len(emitted) == 1
        assert emitted[0]["question"] == "Are you sure?"

    @pytest.mark.asyncio
    async def test_emit_question_is_exact_options_prompt(self) -> None:
        """Options question emitted as the full numbered-list prompt, not just a substring."""
        channel = _make_channel("1")
        emitted: list[dict[str, Any]] = []

        hooks = HookRegistry()
        hooks.register(HookEvent.QUESTION_PENDING, emitted.append)  # type: ignore[arg-type]

        ts = AskUserToolset(channel, hooks=hooks)
        await ts.ask_user("Pick one:", options=["alpha", "beta"])

        expected = "Pick one:\n[1] alpha\n[2] beta\nChoose [1-2]:"
        assert len(emitted) == 1
        assert emitted[0]["question"] == expected

    @pytest.mark.asyncio
    async def test_emit_question_three_options_exact(self) -> None:
        """Three-option prompt has correct numbering and terminator."""
        channel = _make_channel("2")
        emitted: list[dict[str, Any]] = []

        hooks = HookRegistry()
        hooks.register(HookEvent.QUESTION_PENDING, emitted.append)  # type: ignore[arg-type]

        ts = AskUserToolset(channel, hooks=hooks)
        await ts.ask_user("Choose:", options=["x", "y", "z"])

        expected = "Choose:\n[1] x\n[2] y\n[3] z\nChoose [1-3]:"
        assert len(emitted) == 1
        assert emitted[0]["question"] == expected


# ---------------------------------------------------------------------------
# Strengthen: ApprovalGate emitted question equals text_fallback exactly
# (reviewer gap 3 — existing test only checks non-empty string)
# ---------------------------------------------------------------------------


class TestFromAC_970_ApprovalGateExactFallbackText:
    """The emitted ``question`` must equal the ``text_fallback`` string exactly."""

    @pytest.mark.asyncio
    async def test_emit_question_equals_text_fallback_no_args(self) -> None:
        """No-arg tool: emitted question matches 'Action requires approval: {name}...' verbatim."""
        channel = _make_channel("yes")
        emitted: list[dict[str, Any]] = []

        hooks = HookRegistry()
        hooks.register(HookEvent.QUESTION_PENDING, emitted.append)  # type: ignore[arg-type]

        gate = _make_gate(
            rules=[ApprovalRule(tool_name="rm_all")],
            hooks=hooks,
            channel=channel,
        )
        ctx = MagicMock()
        tool = MagicMock()
        await gate.call_tool("rm_all", {}, ctx, tool)

        expected = "Action requires approval: rm_all. Approve? (yes/no/approve all rm_all)"
        assert len(emitted) >= 1
        assert emitted[0]["question"] == expected

    @pytest.mark.asyncio
    async def test_emit_question_equals_text_fallback_with_args(self) -> None:
        """With tool args: emitted question embeds the args summary verbatim."""
        channel = _make_channel("yes")
        emitted: list[dict[str, Any]] = []

        hooks = HookRegistry()
        hooks.register(HookEvent.QUESTION_PENDING, emitted.append)  # type: ignore[arg-type]

        gate = _make_gate(
            rules=[ApprovalRule(tool_name="git_push")],
            hooks=hooks,
            channel=channel,
        )
        ctx = MagicMock()
        tool = MagicMock()
        await gate.call_tool("git_push", {"branch": "main"}, ctx, tool)

        expected = (
            "Action requires approval: git_push(branch='main')."
            " Approve? (yes/no/approve all git_push)"
        )
        assert len(emitted) >= 1
        assert emitted[0]["question"] == expected

    @pytest.mark.asyncio
    async def test_emit_question_not_a_generic_placeholder(self) -> None:
        """Emitted question must contain the actual tool name and 'Action requires approval'."""
        channel = _make_channel("yes")
        emitted: list[dict[str, Any]] = []

        hooks = HookRegistry()
        hooks.register(HookEvent.QUESTION_PENDING, emitted.append)  # type: ignore[arg-type]

        gate = _make_gate(
            rules=[ApprovalRule(tool_name="deploy")],
            hooks=hooks,
            channel=channel,
        )
        ctx = MagicMock()
        tool = MagicMock()
        await gate.call_tool("deploy", {"env": "prod"}, ctx, tool)

        assert len(emitted) >= 1
        question = emitted[0]["question"]
        assert "Action requires approval:" in question
        assert "deploy" in question
        assert "yes/no" in question
