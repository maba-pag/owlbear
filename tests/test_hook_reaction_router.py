"""Tests for HookReactionRule schema, HookReactionRouter registration and matching.

These are RED-phase tests written from the AC for task #965.
All tests are expected to FAIL until #955 implements the module.
"""

from __future__ import annotations

import logging
from typing import Any
from unittest.mock import AsyncMock

import pytest
from owlbear.core.hook_reaction_router import HookReactionRouter, HookReactionRule

from owlbear.core.hooks import HookEvent, HookRegistry

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_router(
    rules: list[HookReactionRule],
    *,
    notify: Any = None,
    retry: Any = None,
    escalate: Any = None,
) -> HookReactionRouter:
    """Construct a HookReactionRouter with mock executors for each action kind."""
    executors: dict[str, Any] = {
        "notify": notify or AsyncMock(),
        "retry": retry or AsyncMock(),
        "escalate": escalate or AsyncMock(),
    }
    return HookReactionRouter(rules=rules, executors=executors)


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------


class TestFromAC_HookReactionRuleSchema:
    """AC: HookReactionRule accepts only notify, retry, and escalate actions,
    rejects empty events/actions, unknown action kinds, non-scalar match
    values, and unknown keys.
    """

    # -- happy path ----------------------------------------------------------

    def test_accepts_notify_action(self) -> None:
        rule = HookReactionRule(events=["task_complete"], actions=["notify"])
        assert "notify" in rule.actions

    def test_accepts_retry_action(self) -> None:
        rule = HookReactionRule(events=["on_error"], actions=["retry"])
        assert "retry" in rule.actions

    def test_accepts_escalate_action(self) -> None:
        rule = HookReactionRule(events=["budget_warning"], actions=["escalate"])
        assert "escalate" in rule.actions

    def test_accepts_all_three_valid_actions(self) -> None:
        rule = HookReactionRule(
            events=["task_complete"],
            actions=["notify", "retry", "escalate"],
        )
        assert len(rule.actions) == 3

    def test_accepts_scalar_string_match_value(self) -> None:
        rule = HookReactionRule(
            events=["task_complete"],
            actions=["notify"],
            match={"outcome": "success"},
        )
        assert rule.match == {"outcome": "success"}

    def test_accepts_scalar_int_match_value(self) -> None:
        rule = HookReactionRule(
            events=["budget_warning"],
            actions=["escalate"],
            match={"pct": 90},
        )
        assert rule.match["pct"] == 90

    def test_match_field_is_optional(self) -> None:
        rule = HookReactionRule(events=["task_complete"], actions=["notify"])
        # match may be None or an empty dict when not supplied
        assert rule.match is None or rule.match == {}

    def test_multiple_events_accepted(self) -> None:
        rule = HookReactionRule(
            events=["task_complete", "on_error"],
            actions=["notify"],
        )
        assert len(rule.events) == 2

    # -- error paths ---------------------------------------------------------

    def test_rejects_empty_events(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            HookReactionRule(events=[], actions=["notify"])

    def test_rejects_empty_actions(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            HookReactionRule(events=["task_complete"], actions=[])

    def test_rejects_unknown_action_kind(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            HookReactionRule(events=["task_complete"], actions=["xyzzy"])

    def test_rejects_unknown_action_alongside_valid(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            HookReactionRule(events=["task_complete"], actions=["notify", "xyzzy"])

    def test_rejects_non_scalar_match_value_nested_dict(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            HookReactionRule(
                events=["task_complete"],
                actions=["notify"],
                match={"outcome": {"nested": "value"}},
            )

    def test_rejects_non_scalar_match_value_list(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            HookReactionRule(
                events=["task_complete"],
                actions=["notify"],
                match={"outcome": [1, 2, 3]},
            )

    def test_rejects_extra_unknown_fields(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            HookReactionRule(
                events=["task_complete"],
                actions=["notify"],
                unknown_field="bad",  # type: ignore[call-arg]
            )


# ---------------------------------------------------------------------------
# Router registration
# ---------------------------------------------------------------------------


class TestFromAC_HookReactionRouterRegistration:
    """AC: HookReactionRouter.register() resolves event strings to HookEvent
    and registers one handler per configured event.
    AC: invalid event names fail at registration, not silently skipped.
    """

    def test_register_resolves_event_string_to_hook_event(self) -> None:
        hooks = HookRegistry()
        rule = HookReactionRule(events=["task_complete"], actions=["notify"])
        router = _make_router([rule])

        before = len(hooks.handlers.get(HookEvent.TASK_COMPLETE, []))
        router.register(hooks)
        after = len(hooks.handlers.get(HookEvent.TASK_COMPLETE, []))

        assert after == before + 1

    def test_register_adds_one_handler_per_distinct_event(self) -> None:
        hooks = HookRegistry()
        rule = HookReactionRule(events=["on_error"], actions=["retry"])
        router = _make_router([rule])

        before = len(hooks.handlers.get(HookEvent.ON_ERROR, []))
        router.register(hooks)
        after = len(hooks.handlers.get(HookEvent.ON_ERROR, []))

        assert after == before + 1

    def test_register_multiple_events_in_one_rule_registers_each(self) -> None:
        hooks = HookRegistry()
        rule = HookReactionRule(
            events=["task_complete", "budget_warning"],
            actions=["notify"],
        )
        router = _make_router([rule])
        router.register(hooks)

        assert len(hooks.handlers.get(HookEvent.TASK_COMPLETE, [])) >= 1
        assert len(hooks.handlers.get(HookEvent.BUDGET_WARNING, [])) >= 1

    def test_register_multiple_rules_each_add_handlers(self) -> None:
        hooks = HookRegistry()
        rule1 = HookReactionRule(events=["task_complete"], actions=["notify"])
        rule2 = HookReactionRule(events=["on_error"], actions=["escalate"])
        router = _make_router([rule1, rule2])
        router.register(hooks)

        assert len(hooks.handlers.get(HookEvent.TASK_COMPLETE, [])) >= 1
        assert len(hooks.handlers.get(HookEvent.ON_ERROR, [])) >= 1

    def test_register_invalid_event_name_raises_not_skips(self) -> None:
        hooks = HookRegistry()
        rule = HookReactionRule.__new__(HookReactionRule)
        # Bypass validation to simulate a bad-event-name reaching register()
        object.__setattr__(rule, "events", ["not_a_real_hook_event"])
        object.__setattr__(rule, "actions", ["notify"])
        object.__setattr__(rule, "match", None)
        router = _make_router([rule])

        with pytest.raises((ValueError, KeyError)):
            router.register(hooks)


# ---------------------------------------------------------------------------
# Router matching semantics
# ---------------------------------------------------------------------------


class TestFromAC_HookReactionRouterMatching:
    """AC: router runs actions in listed order when event matches and every
    configured scalar match pair equals the payload.
    Missing or unequal match keys skip executor calls.
    """

    @pytest.mark.asyncio
    async def test_actions_run_in_declared_order(self) -> None:
        hooks = HookRegistry()
        call_order: list[str] = []

        async def mock_notify(_data: dict[str, Any]) -> None:
            call_order.append("notify")

        async def mock_retry(_data: dict[str, Any]) -> None:
            call_order.append("retry")

        rule = HookReactionRule(
            events=["task_complete"],
            actions=["notify", "retry"],
        )
        router = HookReactionRouter(
            rules=[rule],
            executors={"notify": mock_notify, "retry": mock_retry, "escalate": AsyncMock()},
        )
        router.register(hooks)

        await hooks.emit(HookEvent.TASK_COMPLETE, {"task_id": "t1", "outcome": "success"})

        assert call_order == ["notify", "retry"]

    @pytest.mark.asyncio
    async def test_actions_run_with_no_match_filter(self) -> None:
        hooks = HookRegistry()
        mock_notify = AsyncMock()

        rule = HookReactionRule(events=["task_complete"], actions=["notify"])
        router = HookReactionRouter(
            rules=[rule],
            executors={"notify": mock_notify, "retry": AsyncMock(), "escalate": AsyncMock()},
        )
        router.register(hooks)

        await hooks.emit(HookEvent.TASK_COMPLETE, {"task_id": "t1", "outcome": "any"})

        mock_notify.assert_called_once()

    @pytest.mark.asyncio
    async def test_all_match_pairs_equal_triggers_actions(self) -> None:
        hooks = HookRegistry()
        mock_notify = AsyncMock()

        rule = HookReactionRule(
            events=["task_complete"],
            actions=["notify"],
            match={"outcome": "success"},
        )
        router = HookReactionRouter(
            rules=[rule],
            executors={"notify": mock_notify, "retry": AsyncMock(), "escalate": AsyncMock()},
        )
        router.register(hooks)

        await hooks.emit(HookEvent.TASK_COMPLETE, {"task_id": "t1", "outcome": "success"})

        mock_notify.assert_called_once()

    @pytest.mark.asyncio
    async def test_missing_match_key_skips_actions(self) -> None:
        hooks = HookRegistry()
        mock_notify = AsyncMock()

        rule = HookReactionRule(
            events=["task_complete"],
            actions=["notify"],
            match={"outcome": "success"},
        )
        router = HookReactionRouter(
            rules=[rule],
            executors={"notify": mock_notify, "retry": AsyncMock(), "escalate": AsyncMock()},
        )
        router.register(hooks)

        # Payload is missing the "outcome" key entirely
        await hooks.emit(HookEvent.TASK_COMPLETE, {"task_id": "t1"})

        mock_notify.assert_not_called()

    @pytest.mark.asyncio
    async def test_unequal_match_key_skips_actions(self) -> None:
        hooks = HookRegistry()
        mock_notify = AsyncMock()

        rule = HookReactionRule(
            events=["task_complete"],
            actions=["notify"],
            match={"outcome": "success"},
        )
        router = HookReactionRouter(
            rules=[rule],
            executors={"notify": mock_notify, "retry": AsyncMock(), "escalate": AsyncMock()},
        )
        router.register(hooks)

        # Payload has "outcome" but value is different
        await hooks.emit(HookEvent.TASK_COMPLETE, {"task_id": "t1", "outcome": "failure"})

        mock_notify.assert_not_called()

    @pytest.mark.asyncio
    async def test_wrong_event_does_not_trigger_rule_actions(self) -> None:
        hooks = HookRegistry()
        mock_escalate = AsyncMock()

        rule = HookReactionRule(events=["budget_warning"], actions=["escalate"])
        router = HookReactionRouter(
            rules=[rule],
            executors={"notify": AsyncMock(), "retry": AsyncMock(), "escalate": mock_escalate},
        )
        router.register(hooks)

        # Emit a different event that the rule does not cover
        await hooks.emit(HookEvent.TASK_COMPLETE, {"task_id": "t1", "outcome": "success"})

        mock_escalate.assert_not_called()

    @pytest.mark.asyncio
    async def test_partial_match_second_key_unequal_skips(self) -> None:
        hooks = HookRegistry()
        mock_notify = AsyncMock()

        rule = HookReactionRule(
            events=["task_complete"],
            actions=["notify"],
            match={"outcome": "success", "task_id": "expected-id"},
        )
        router = HookReactionRouter(
            rules=[rule],
            executors={"notify": mock_notify, "retry": AsyncMock(), "escalate": AsyncMock()},
        )
        router.register(hooks)

        # outcome matches, but task_id differs
        await hooks.emit(
            HookEvent.TASK_COMPLETE,
            {"task_id": "other-id", "outcome": "success"},
        )

        mock_notify.assert_not_called()

    @pytest.mark.asyncio
    async def test_all_match_pairs_equal_multiple_conditions(self) -> None:
        hooks = HookRegistry()
        mock_notify = AsyncMock()

        rule = HookReactionRule(
            events=["task_complete"],
            actions=["notify"],
            match={"outcome": "success", "task_id": "t99"},
        )
        router = HookReactionRouter(
            rules=[rule],
            executors={"notify": mock_notify, "retry": AsyncMock(), "escalate": AsyncMock()},
        )
        router.register(hooks)

        await hooks.emit(
            HookEvent.TASK_COMPLETE,
            {"task_id": "t99", "outcome": "success"},
        )

        mock_notify.assert_called_once()


# ---------------------------------------------------------------------------
# Executor exception handling
# ---------------------------------------------------------------------------


class TestFromAC_HookReactionRouterErrorHandling:
    """AC: executor exceptions are logged and swallowed without recursive
    HookEvent.ON_ERROR emission.
    """

    @pytest.mark.asyncio
    async def test_executor_exception_is_swallowed(self) -> None:
        hooks = HookRegistry()

        async def failing_notify(_data: dict[str, Any]) -> None:
            msg = "notify failed"
            raise RuntimeError(msg)

        rule = HookReactionRule(events=["task_complete"], actions=["notify"])
        router = HookReactionRouter(
            rules=[rule],
            executors={"notify": failing_notify, "retry": AsyncMock(), "escalate": AsyncMock()},
        )
        router.register(hooks)

        # Must not raise — executor failure is silently swallowed
        await hooks.emit(HookEvent.TASK_COMPLETE, {"task_id": "t1", "outcome": "success"})

    @pytest.mark.asyncio
    async def test_executor_exception_is_logged(self, caplog: pytest.LogCaptureFixture) -> None:
        hooks = HookRegistry()

        async def failing_notify(_data: dict[str, Any]) -> None:
            msg = "notify exploded"
            raise RuntimeError(msg)

        rule = HookReactionRule(events=["task_complete"], actions=["notify"])
        router = HookReactionRouter(
            rules=[rule],
            executors={"notify": failing_notify, "retry": AsyncMock(), "escalate": AsyncMock()},
        )
        router.register(hooks)

        with caplog.at_level(logging.WARNING):
            await hooks.emit(HookEvent.TASK_COMPLETE, {"task_id": "t1", "outcome": "ok"})

        assert any(
            "notify" in record.message.lower() or "failed" in record.message.lower()
            for record in caplog.records
        )

    @pytest.mark.asyncio
    async def test_no_recursive_on_error_emission(self) -> None:
        hooks = HookRegistry()
        on_error_call_count = 0

        async def counting_escalate(_data: dict[str, Any]) -> None:
            msg = "escalate failed"
            raise RuntimeError(msg)

        async def track_on_error(_data: dict[str, Any]) -> None:
            nonlocal on_error_call_count
            on_error_call_count += 1

        # Rule: ON_ERROR triggers escalate (which will fail)
        rule = HookReactionRule(events=["on_error"], actions=["escalate"])
        router = HookReactionRouter(
            rules=[rule],
            executors={
                "notify": AsyncMock(),
                "retry": AsyncMock(),
                "escalate": counting_escalate,
            },
        )
        router.register(hooks)
        hooks.register(HookEvent.ON_ERROR, track_on_error)

        # Emit ON_ERROR once. track_on_error should be called exactly once
        # (from the original emit), not a second time from error re-emission.
        await hooks.emit(
            HookEvent.ON_ERROR,
            {"error": RuntimeError("original"), "prompt": "p"},
        )

        # track_on_error runs exactly once (the original emit)
        assert on_error_call_count == 1

    @pytest.mark.asyncio
    async def test_subsequent_actions_still_run_after_one_failure(self) -> None:
        hooks = HookRegistry()
        mock_retry = AsyncMock()

        async def failing_notify(_data: dict[str, Any]) -> None:
            msg = "notify failed"
            raise RuntimeError(msg)

        # notify before retry — notify fails but retry should still run
        rule = HookReactionRule(events=["task_complete"], actions=["notify", "retry"])
        router = HookReactionRouter(
            rules=[rule],
            executors={
                "notify": failing_notify,
                "retry": mock_retry,
                "escalate": AsyncMock(),
            },
        )
        router.register(hooks)

        await hooks.emit(HookEvent.TASK_COMPLETE, {"task_id": "t1", "outcome": "ok"})

        mock_retry.assert_called_once()
