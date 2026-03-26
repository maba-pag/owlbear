"""Tests for #1004 — assembly-time notify dedup in build_hooks (RED phase).

Tests verify that build_hooks() excludes events from NotificationHook.notification_events
when unconditional notify reactions cover those events.

Tests T-1/T-4/T-7 may pass on current HEAD (no dedup implemented yet).
Tests T-2/T-3/T-5/T-6 must fail (dedup not yet implemented).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from unittest.mock import patch

from owlbear.bootstrap.hooks import build_hooks
from owlbear.config import OwlBearSettings
from owlbear.core.hooks import HookEvent, HookRegistry
from owlbear.core.notification_hook import NotificationHook

if TYPE_CHECKING:
    import pytest


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _build_and_capture(settings: OwlBearSettings) -> tuple[HookRegistry, list[str]]:
    """Call build_hooks and capture notification_events passed to NotificationHook.

    Uses a spy factory so the real NotificationHook is still constructed and
    registers handlers normally — only the events argument is captured.
    """
    captured: list[list[str]] = []
    _real_hook = NotificationHook

    def _spy_factory(**kwargs: object) -> NotificationHook:
        captured.append(list(kwargs["notification_events"]))  # type: ignore[arg-type]
        return _real_hook(**kwargs)  # type: ignore[arg-type]

    with patch("owlbear.bootstrap.hooks.NotificationHook", side_effect=_spy_factory):
        hooks, _ = build_hooks(settings)

    return hooks, captured[0] if captured else []


# ---------------------------------------------------------------------------
# T-1: Legacy-only — no reactions
# ---------------------------------------------------------------------------


class TestFromAC_NotifyDedup:
    """Assembly-time notify deduplication in build_hooks (AC lines T-1 through T-7)."""

    def test_t1_legacy_only_receives_full_events(self) -> None:
        """T-1 happy: With empty hook_reactions, NotificationHook receives all events."""
        settings = OwlBearSettings(
            hook_reactions=[],
            notification_events=["task_complete", "on_error"],
        )
        _, events = _build_and_capture(settings)
        assert set(events) == {"task_complete", "on_error"}, (
            f"Legacy mode must pass the full events list; got {events!r}"
        )

    def test_t1_legacy_handler_count(self) -> None:
        """T-1 boundary: One handler per notification event in legacy mode (no reactions)."""
        settings = OwlBearSettings(
            hook_reactions=[],
            notification_events=["task_complete", "on_error"],
        )
        hooks, _ = build_hooks(settings)
        # NotificationHook registers exactly one handler per event; no other built-in hook
        # registers on TASK_COMPLETE or ON_ERROR in the default build_hooks() call.
        assert len(hooks.handlers.get(HookEvent.TASK_COMPLETE, [])) == 1
        assert len(hooks.handlers.get(HookEvent.ON_ERROR, [])) == 1

    # ---------------------------------------------------------------------------
    # T-2: Reaction-only — unconditional notify covers all events
    # ---------------------------------------------------------------------------

    def test_t2_unconditional_covers_all_events_empty_list(self) -> None:
        """T-2 happy: When unconditional notify covers every event, NotificationHook receives []."""
        settings = OwlBearSettings(
            hook_reactions=[
                {"events": ["task_complete"], "actions": ["notify"]},
                {"events": ["on_error"], "actions": ["notify"]},
            ],
            notification_events=["task_complete", "on_error"],
        )
        _, events = _build_and_capture(settings)
        assert events == [], (
            f"All events should be excluded from NotificationHook but got {events!r}"
        )

    def test_t2_zero_notification_handlers_on_excluded_event(self) -> None:
        """T-2 boundary: After full dedup, only the reaction router's handler remains."""
        settings = OwlBearSettings(
            hook_reactions=[
                {"events": ["task_complete"], "actions": ["notify"]},
            ],
            notification_events=["task_complete"],
        )
        # On HEAD (no dedup): NotificationHook AND Router both register → count == 2
        # After dedup: only Router registers → count == 1
        hooks, _ = build_hooks(settings)
        assert len(hooks.handlers.get(HookEvent.TASK_COMPLETE, [])) == 1, (
            "Only the reaction router handler should remain after dedup"
        )

    # ---------------------------------------------------------------------------
    # T-3: Mixed — unconditional notify covers subset (task_complete only)
    # ---------------------------------------------------------------------------

    def test_t3_unconditional_subset_excludes_covered_event(self) -> None:
        """T-3 happy: Unconditional notify for task_complete excludes it from NotificationHook."""
        settings = OwlBearSettings(
            hook_reactions=[
                {"events": ["task_complete"], "actions": ["notify"]},
            ],
            notification_events=["task_complete", "on_error"],
        )
        _, events = _build_and_capture(settings)
        assert "task_complete" not in events, (
            f"task_complete should be excluded by dedup but found in {events!r}"
        )

    def test_t3_unconditional_subset_preserves_uncovered_event(self) -> None:
        """T-3 edge: on_error must remain in NotificationHook; only task_complete is excluded."""
        settings = OwlBearSettings(
            hook_reactions=[
                {"events": ["task_complete"], "actions": ["notify"]},
            ],
            notification_events=["task_complete", "on_error"],
        )
        _, events = _build_and_capture(settings)
        assert "on_error" in events, (
            f"on_error should be preserved in NotificationHook but events were {events!r}"
        )

    def test_t3_excluded_events_match_exactly(self) -> None:
        """T-3 boundary: Only the unconditionally-covered event is excluded; list is [on_error]."""
        settings = OwlBearSettings(
            hook_reactions=[
                {"events": ["task_complete"], "actions": ["notify"]},
            ],
            notification_events=["task_complete", "on_error"],
        )
        _, events = _build_and_capture(settings)
        assert set(events) == {"on_error"}, (
            f"NotificationHook should receive only ['on_error'] but got {events!r}"
        )

    # ---------------------------------------------------------------------------
    # T-4: Conditional match rule preserved
    # ---------------------------------------------------------------------------

    def test_t4_conditional_match_preserves_event(self) -> None:
        """T-4 happy: A notify rule with non-None match does NOT exclude the event."""
        settings = OwlBearSettings(
            hook_reactions=[
                {"events": ["task_complete"], "actions": ["notify"], "match": {"status": "done"}},
            ],
            notification_events=["task_complete", "on_error"],
        )
        _, events = _build_and_capture(settings)
        assert "task_complete" in events, (
            "task_complete should remain in NotificationHook events when rule is conditional"
        )

    def test_t4_conditional_match_full_events_preserved(self) -> None:
        """T-4 edge: Conditional-only reactions leave the full notification_events list intact."""
        settings = OwlBearSettings(
            hook_reactions=[
                {"events": ["task_complete"], "actions": ["notify"], "match": {"status": "done"}},
                {"events": ["on_error"], "actions": ["notify"], "match": {"code": 500}},
            ],
            notification_events=["task_complete", "on_error"],
        )
        _, events = _build_and_capture(settings)
        assert set(events) == {"task_complete", "on_error"}, (
            f"All events should be preserved with conditional-only rules; got {events!r}"
        )

    # ---------------------------------------------------------------------------
    # T-5: Mixed conditional and unconditional — unconditional wins
    # ---------------------------------------------------------------------------

    def test_t5_unconditional_wins_over_conditional(self) -> None:
        """T-5 happy: Conditional + unconditional rules for same event: unconditional wins."""
        settings = OwlBearSettings(
            hook_reactions=[
                {"events": ["task_complete"], "actions": ["notify"], "match": {"status": "done"}},
                {"events": ["task_complete"], "actions": ["notify"]},  # unconditional
            ],
            notification_events=["task_complete", "on_error"],
        )
        _, events = _build_and_capture(settings)
        assert "task_complete" not in events, (
            "task_complete should be excluded: unconditional rule present alongside conditional"
        )

    def test_t5_unconditional_wins_preserves_other_event(self) -> None:
        """T-5 edge: Unconditional win for task_complete does not affect on_error."""
        settings = OwlBearSettings(
            hook_reactions=[
                {"events": ["task_complete"], "actions": ["notify"], "match": {"status": "done"}},
                {"events": ["task_complete"], "actions": ["notify"]},
            ],
            notification_events=["task_complete", "on_error"],
        )
        _, events = _build_and_capture(settings)
        assert "on_error" in events, (
            f"on_error must remain in NotificationHook events; got {events!r}"
        )

    # ---------------------------------------------------------------------------
    # T-6: Debug log on exclusion
    # ---------------------------------------------------------------------------

    def test_t6_debug_log_emitted_on_exclusion(self, caplog: pytest.LogCaptureFixture) -> None:
        """T-6 happy: A DEBUG log listing excluded event names is emitted by build_hooks."""
        settings = OwlBearSettings(
            hook_reactions=[
                {"events": ["task_complete"], "actions": ["notify"]},
            ],
            notification_events=["task_complete", "on_error"],
        )
        with caplog.at_level(logging.DEBUG, logger="owlbear.bootstrap.hooks"):
            build_hooks(settings)

        excluded_debug_records = [
            r
            for r in caplog.records
            if r.levelno == logging.DEBUG and "task_complete" in r.getMessage()
        ]
        assert excluded_debug_records, (
            "Expected a DEBUG-level log from owlbear.bootstrap.hooks mentioning 'task_complete'"
        )

    def test_t6_debug_log_not_emitted_when_nothing_excluded(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """T-6 edge: When no events are excluded, no exclusion DEBUG log is emitted."""
        settings = OwlBearSettings(
            hook_reactions=[
                # conditional only — no exclusion should happen
                {"events": ["task_complete"], "actions": ["notify"], "match": {"status": "done"}},
            ],
            notification_events=["task_complete", "on_error"],
        )
        with caplog.at_level(logging.DEBUG, logger="owlbear.bootstrap.hooks"):
            build_hooks(settings)

        # No "excluded" debug log should appear because dedup does not trigger
        excluded_records = [
            r
            for r in caplog.records
            if r.levelno == logging.DEBUG and "exclud" in r.getMessage().lower()
        ]
        assert not excluded_records, (
            f"No exclusion log expected when no events are excluded; found: {excluded_records}"
        )

    def test_t6_out_of_scope_notify_rule_no_exclusion_log(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """T-6 edge: Unconditional notify targeting an event NOT in notification_events
        must NOT emit a DEBUG exclusion log — no events were actually excluded."""
        settings = OwlBearSettings(
            hook_reactions=[
                {"events": ["question_pending"], "actions": ["notify"]},  # out-of-scope
            ],
            notification_events=["task_complete", "on_error"],
        )
        with caplog.at_level(logging.DEBUG, logger="owlbear.bootstrap.hooks"):
            build_hooks(settings)

        exclusion_records = [
            r
            for r in caplog.records
            if r.levelno == logging.DEBUG and "exclud" in r.getMessage().lower()
        ]
        assert not exclusion_records, (
            "No exclusion log expected when notify rule targets an out-of-scope event "
            f"(no NotificationHook events were actually removed); "
            f"found: {[r.getMessage() for r in exclusion_records]}"
        )

    def test_t6_log_does_not_show_empty_exclusion_list(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """T-6 boundary: When an unconditional notify reaction covers an event NOT in
        notification_events, the logger must not emit an exclusion message with an
        empty list ('[]') — that is a false positive indicating the guard is leaking."""
        settings = OwlBearSettings(
            hook_reactions=[
                {"events": ["question_pending"], "actions": ["notify"]},  # out-of-scope
            ],
            notification_events=["task_complete", "on_error"],
        )
        with caplog.at_level(logging.DEBUG, logger="owlbear.bootstrap.hooks"):
            build_hooks(settings)

        empty_exclusion_records = [
            r
            for r in caplog.records
            if r.levelno == logging.DEBUG
            and "exclud" in r.getMessage().lower()
            and "[]" in r.getMessage()
        ]
        assert not empty_exclusion_records, (
            "Must not emit a DEBUG exclusion log with an empty list when no "
            "NotificationHook events were removed; "
            f"found: {[r.getMessage() for r in empty_exclusion_records]}"
        )

    # ---------------------------------------------------------------------------
    # T-7: Non-notify actions ignored
    # ---------------------------------------------------------------------------

    def test_t7_retry_action_does_not_exclude_events(self) -> None:
        """T-7 happy: A retry-only reaction rule does not exclude events from NotificationHook."""
        settings = OwlBearSettings(
            hook_reactions=[
                {"events": ["task_complete"], "actions": ["retry"]},
            ],
            notification_events=["task_complete", "on_error"],
        )
        _, events = _build_and_capture(settings)
        assert "task_complete" in events, (
            "retry-only rule must not exclude task_complete from NotificationHook"
        )

    def test_t7_escalate_action_does_not_exclude_events(self) -> None:
        """T-7 happy: An escalate-only rule does not exclude events from NotificationHook."""
        settings = OwlBearSettings(
            hook_reactions=[
                {"events": ["on_error"], "actions": ["escalate"]},
            ],
            notification_events=["task_complete", "on_error"],
        )
        _, events = _build_and_capture(settings)
        assert "on_error" in events, (
            "escalate-only rule must not exclude on_error from NotificationHook"
        )

    def test_t7_non_notify_rules_preserve_all_events(self) -> None:
        """T-7 boundary: Multiple non-notify rules leave the full notification_events intact."""
        settings = OwlBearSettings(
            hook_reactions=[
                {"events": ["task_complete"], "actions": ["retry"]},
                {"events": ["on_error"], "actions": ["escalate"]},
            ],
            notification_events=["task_complete", "on_error"],
        )
        _, events = _build_and_capture(settings)
        assert set(events) == {"task_complete", "on_error"}, (
            f"Non-notify rules must not reduce notification events; got {events!r}"
        )
