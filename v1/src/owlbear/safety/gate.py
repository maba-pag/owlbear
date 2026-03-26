"""ApprovalGateToolset — WrapperToolset that gates tool calls behind user approval.

Wraps any :class:`~pydantic_ai.toolsets.AbstractToolset` and checks
:class:`ApprovalPolicy` rules before allowing tool execution.  When a tool
requires approval, the gate sends a prompt through a
:class:`~owlbear.channels.base.ChannelPlugin` and waits for the user's
response.

Nests **outside** :class:`~owlbear.tools.hooked.HookedToolset` in the
wrapping chain so approval happens before hook-level guards.

Usage::

    gate = ApprovalGateToolset(
        wrapped=hooked_toolset,
        policy=policy,
        session=session,
        channel=channel,
        hooks=registry,
    )
    agent = Agent("model", toolsets=[gate])
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import TYPE_CHECKING

from pydantic_ai.toolsets.wrapper import WrapperToolset

from owlbear.core.hooks import HookEvent, HookRegistry, QuestionPendingData
from owlbear.safety.policy import ApprovalPolicy, ApprovalSession

if TYPE_CHECKING:
    from collections.abc import Callable

    from pydantic_ai import RunContext
    from pydantic_ai.toolsets.abstract import ToolsetTool

    from owlbear.channels.base import ChannelPlugin

__all__ = ["ApprovalGateToolset"]

logger = logging.getLogger(__name__)


@dataclass
class ApprovalGateToolset(WrapperToolset):  # type: ignore[type-arg]
    """WrapperToolset that gates destructive tool calls behind user approval.

    Args:
        wrapped: The inner toolset to delegate to.
        policy: Rules defining which tools require approval.
        session: Per-session pre-grant tracker.
        channel: I/O channel for sending prompts and receiving responses.
        hooks: Registry used to emit approval-related lifecycle events.
    """

    policy: ApprovalPolicy = field(default_factory=ApprovalPolicy)
    session: ApprovalSession = field(default_factory=ApprovalSession)
    channel: ChannelPlugin = None  # type: ignore[assignment]
    hooks: HookRegistry = field(default_factory=HookRegistry)
    audit_sink: Callable[[object], None] | None = None

    async def call_tool(
        self,
        name: str,
        tool_args: dict[str, object],
        ctx: RunContext,  # type: ignore[type-arg]
        tool: ToolsetTool,  # type: ignore[type-arg]
    ) -> object:
        """Check policy, prompt user if needed, then delegate or deny.

        Flow:
        1. If the tool is not matched by any policy rule, proceed directly.
        2. If the tool is pre-granted in the session, proceed directly.
        3. Otherwise, send an approval prompt via the channel and emit
           :attr:`~owlbear.core.hooks.HookEvent.QUESTION_PENDING`.
        4. Based on the user's response:
           - ``yes`` / ``y``: proceed with the wrapped tool call.
           - ``no`` / ``n``: return a denial message.
           - ``None``: return a timeout/cancellation message.
           - ``approve all {tool}``: create a scoped grant (TTL and
             max-uses from policy defaults), then proceed.
        """
        requires = self.policy.requires_approval(name, dict(tool_args))

        if not requires:
            await self.hooks.emit(
                HookEvent.POST_TOOL_USE,
                {"tool_name": name, "event_type": "approval_gate", "approval_required": False},
            )
            return await super().call_tool(name, tool_args, ctx, tool)

        # Pre-granted tools skip the prompt entirely
        if self.session.is_pre_granted(name):
            return await super().call_tool(name, tool_args, ctx, tool)

        # Build and send the approval prompt
        args_summary = ", ".join(f"{k}={v!r}" for k, v in tool_args.items())
        action_description = f"{name}({args_summary})" if args_summary else name

        from owlbear.channels.slack_templates import format_approval_blocks  # noqa: PLC0415

        action_id_prefix = f"approval_{name}"
        blocks = format_approval_blocks(action_description, action_id_prefix)
        text_fallback = (
            f"Action requires approval: {action_description}. Approve? (yes/no/approve all {name})"
        )
        await self.channel.send_blocks(blocks, text_fallback)

        payload: QuestionPendingData = {
            "source": "approval_gate",
            "question": text_fallback,
            "tool_name": name,
        }
        await self.hooks.emit(HookEvent.QUESTION_PENDING, payload)

        # Wait for the user's response
        response = await self.channel.receive()

        if response is None:
            self._emit_audit_event(
                event_type="approval_timeout",
                tool_name=name,
                detail=f"Approval timed out for {action_description}",
                metadata={"response": None},
            )
            await self.hooks.emit(
                HookEvent.POST_TOOL_USE,
                {
                    "tool_name": name,
                    "event_type": "approval_gate",
                    "approval_required": True,
                    "approval_decision": "timeout",
                },
            )
            return f"Action {name} timed out — cancelled (safe default)."

        normalised = response.strip().lower()

        if normalised in ("yes", "y", "approved"):
            self._emit_audit_event(
                event_type="approval_granted",
                tool_name=name,
                detail=f"Approval granted for {action_description}",
                metadata={"response": response},
            )
            await self.hooks.emit(
                HookEvent.POST_TOOL_USE,
                {
                    "tool_name": name,
                    "event_type": "approval_gate",
                    "approval_required": True,
                    "approval_decision": "approved",
                },
            )
            return await super().call_tool(name, tool_args, ctx, tool)

        if normalised.startswith("approve all "):
            tool_to_grant = normalised[len("approve all ") :]
            self.session.grant(
                tool_to_grant,
                ttl=self.policy.default_grant_ttl,
                max_uses=self.policy.default_max_uses,
            )
            self._emit_audit_event(
                event_type="approval_granted_all",
                tool_name=name,
                detail=f"Approval granted for all uses of {tool_to_grant}",
                metadata={
                    "response": response,
                    "tool_to_grant": tool_to_grant,
                    "grant_ttl": self.policy.default_grant_ttl,
                    "grant_max_uses": self.policy.default_max_uses,
                },
            )
            await self.hooks.emit(
                HookEvent.POST_TOOL_USE,
                {
                    "tool_name": name,
                    "event_type": "approval_gate",
                    "approval_required": True,
                    "approval_decision": "approved_all",
                    "grant_ttl": self.policy.default_grant_ttl,
                    "grant_max_uses": self.policy.default_max_uses,
                },
            )
            return await super().call_tool(name, tool_args, ctx, tool)

        # Default: deny (no, n, or unrecognised input)
        self._emit_audit_event(
            event_type="approval_denied",
            tool_name=name,
            detail=f"Approval denied for {action_description}",
            metadata={"response": response},
        )
        await self.hooks.emit(
            HookEvent.POST_TOOL_USE,
            {
                "tool_name": name,
                "event_type": "approval_gate",
                "approval_required": True,
                "approval_decision": "denied",
            },
        )
        return f"Action {name} denied by user."

    def _emit_audit_event(
        self,
        *,
        event_type: str,
        tool_name: str,
        detail: str,
        metadata: dict[str, object],
    ) -> None:
        """Best-effort emit to the injected audit sink."""
        if self.audit_sink is None:
            return

        event = SimpleNamespace(
            timestamp=datetime.now(UTC).isoformat(),
            event_type=event_type,
            severity="medium",
            actor="user",
            session_id="",
            tool_name=tool_name,
            detail=detail,
            metadata=metadata,
        )
        try:
            self.audit_sink(event)
        except Exception:  # noqa: BLE001
            logger.debug("Security audit sink failed in ApprovalGateToolset", exc_info=True)
