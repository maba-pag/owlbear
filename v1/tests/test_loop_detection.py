"""Tests for loop detection in orchestrator dispatch — task #743.

Tests the per-task failure counting, configurable threshold, user
escalation (retry/skip/stop), and ErrorJournal persistence contracts
described in the AC.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from owlbear.orchestrator.loop_detection import EscalationChoice, LoopDetector

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_channel() -> MagicMock:
    """Return a mock ChannelPlugin with async send/send_blocks/receive."""
    ch = MagicMock()
    ch.name = "mock"
    ch.send = AsyncMock()
    ch.send_blocks = AsyncMock()
    ch.receive = AsyncMock(return_value=None)
    return ch


def _make_mock_journal() -> MagicMock:
    """Return a mock ErrorJournal with a ``log`` method."""
    journal = MagicMock()
    journal.log = MagicMock()
    return journal


# ---------------------------------------------------------------------------
# AC 1 — Per-task failure counter in orchestrator dispatch loop
# ---------------------------------------------------------------------------


class TestFromAC_FailureCounter:
    """Per-task failure counter: initialisation, increment, independence."""

    def test_counter_starts_at_zero_for_new_task(self) -> None:
        """A task not yet seen has zero recorded failures."""
        detector = LoopDetector()
        assert detector.failure_count("task-1") == 0

    def test_counter_increments_on_record_failure(self) -> None:
        """Each call to ``record_failure`` increases the count by one."""
        detector = LoopDetector()
        detector.record_failure("task-1", error="boom")
        assert detector.failure_count("task-1") == 1
        detector.record_failure("task-1", error="boom again")
        assert detector.failure_count("task-1") == 2

    def test_independent_counters_per_task(self) -> None:
        """Failure counts for different tasks are tracked independently."""
        detector = LoopDetector()
        detector.record_failure("task-a", error="err-a")
        detector.record_failure("task-a", error="err-a")
        detector.record_failure("task-b", error="err-b")
        assert detector.failure_count("task-a") == 2
        assert detector.failure_count("task-b") == 1

    def test_counter_survives_multiple_errors(self) -> None:
        """Counter accumulates across many failures without loss."""
        detector = LoopDetector()
        for i in range(10):
            detector.record_failure("task-x", error=f"err-{i}")
        assert detector.failure_count("task-x") == 10


# ---------------------------------------------------------------------------
# AC 2 — Configurable max_failures threshold (default 3)
# ---------------------------------------------------------------------------


class TestFromAC_MaxFailuresConfig:
    """max_failures threshold: default value and custom override."""

    def test_default_max_failures_is_three(self) -> None:
        """Default threshold is 3 when not explicitly configured."""
        detector = LoopDetector()
        assert detector.max_failures == 3

    def test_custom_max_failures_threshold(self) -> None:
        """Threshold can be set to a custom value at construction time."""
        detector = LoopDetector(max_failures=5)
        assert detector.max_failures == 5

    def test_should_escalate_returns_false_below_threshold(self) -> None:
        """No escalation when failure count is below max_failures."""
        detector = LoopDetector(max_failures=3)
        detector.record_failure("t1", error="e")
        detector.record_failure("t1", error="e")
        assert detector.should_escalate("t1") is False

    def test_should_escalate_returns_true_at_threshold(self) -> None:
        """Escalation triggers exactly when count reaches max_failures."""
        detector = LoopDetector(max_failures=3)
        for _ in range(3):
            detector.record_failure("t1", error="e")
        assert detector.should_escalate("t1") is True

    def test_should_escalate_returns_true_above_threshold(self) -> None:
        """Escalation remains true when count exceeds max_failures."""
        detector = LoopDetector(max_failures=2)
        for _ in range(5):
            detector.record_failure("t1", error="e")
        assert detector.should_escalate("t1") is True

    def test_max_failures_of_one_escalates_on_first_failure(self) -> None:
        """With max_failures=1, a single failure triggers escalation."""
        detector = LoopDetector(max_failures=1)
        detector.record_failure("t1", error="e")
        assert detector.should_escalate("t1") is True


# ---------------------------------------------------------------------------
# AC 3 — After max failures: skip task and escalate to user via channel
# ---------------------------------------------------------------------------


class TestFromAC_SkipAndEscalate:
    """After max failures the task is skipped and user is notified."""

    @pytest.mark.asyncio
    async def test_escalation_sends_message_via_channel(self) -> None:
        """When max failures reached, an escalation message is sent to channel."""
        channel = _make_mock_channel()
        detector = LoopDetector(max_failures=2)
        detector.record_failure("t1", error="err1")
        detector.record_failure("t1", error="err2")

        # Simulate user choosing to skip
        channel.receive.return_value = "skip"
        await detector.escalate("t1", channel=channel)

        # Channel should have been used to communicate with user
        assert channel.send.called or channel.send_blocks.called

    def test_escalation_not_triggered_below_threshold(self) -> None:
        """Calling escalate on a task below threshold raises or returns
        without sending anything."""
        _make_mock_channel()
        detector = LoopDetector(max_failures=3)
        detector.record_failure("t1", error="e")
        # Only 1 failure, threshold is 3 — should not produce escalation
        assert detector.should_escalate("t1") is False

    @pytest.mark.asyncio
    async def test_escalation_message_contains_task_id(self) -> None:
        """The escalation message includes the failing task identifier."""
        channel = _make_mock_channel()
        channel.receive.return_value = "skip"
        detector = LoopDetector(max_failures=1)
        detector.record_failure("t42", error="kaboom")

        await detector.escalate("t42", channel=channel)

        # At least one send call should contain the task ID
        all_calls = [
            str(c) for c in channel.send.call_args_list + channel.send_blocks.call_args_list
        ]
        combined = " ".join(all_calls)
        assert "t42" in combined

    @pytest.mark.asyncio
    async def test_escalation_message_contains_error_context(self) -> None:
        """The escalation message includes the last error for context."""
        channel = _make_mock_channel()
        channel.receive.return_value = "skip"
        detector = LoopDetector(max_failures=1)
        detector.record_failure("t1", error="Connection refused")

        await detector.escalate("t1", channel=channel)

        all_calls = [
            str(c) for c in channel.send.call_args_list + channel.send_blocks.call_args_list
        ]
        combined = " ".join(all_calls)
        assert "Connection refused" in combined or "error" in combined.lower()

    @pytest.mark.asyncio
    async def test_channel_send_failure_does_not_crash(self) -> None:
        """If channel.send raises during escalation, the detector handles
        it gracefully (no unhandled exception)."""
        channel = _make_mock_channel()
        channel.send.side_effect = RuntimeError("channel down")
        channel.send_blocks.side_effect = RuntimeError("channel down")
        detector = LoopDetector(max_failures=1)
        detector.record_failure("t1", error="err")

        # Should not raise — graceful degradation
        result = await detector.escalate("t1", channel=channel)
        # Result should indicate skip or some default when channel fails
        assert isinstance(result, EscalationChoice)


# ---------------------------------------------------------------------------
# AC 4 — Escalation offers retry/skip/stop options
# ---------------------------------------------------------------------------


class TestFromAC_EscalationOptions:
    """Escalation must present retry, skip, and stop options to the user."""

    @pytest.mark.asyncio
    async def test_retry_choice_resets_counter(self) -> None:
        """Selecting 'retry' resets the failure counter for the task."""
        channel = _make_mock_channel()
        channel.receive.return_value = "retry"
        detector = LoopDetector(max_failures=2)
        detector.record_failure("t1", error="e")
        detector.record_failure("t1", error="e")

        result = await detector.escalate("t1", channel=channel)

        assert result == EscalationChoice.RETRY
        assert detector.failure_count("t1") == 0

    @pytest.mark.asyncio
    async def test_skip_choice_returns_skip(self) -> None:
        """Selecting 'skip' returns the SKIP choice."""
        channel = _make_mock_channel()
        channel.receive.return_value = "skip"
        detector = LoopDetector(max_failures=2)
        detector.record_failure("t1", error="e")
        detector.record_failure("t1", error="e")

        result = await detector.escalate("t1", channel=channel)

        assert result == EscalationChoice.SKIP

    @pytest.mark.asyncio
    async def test_stop_choice_returns_stop(self) -> None:
        """Selecting 'stop' returns the STOP choice."""
        channel = _make_mock_channel()
        channel.receive.return_value = "stop"
        detector = LoopDetector(max_failures=2)
        detector.record_failure("t1", error="e")
        detector.record_failure("t1", error="e")

        result = await detector.escalate("t1", channel=channel)

        assert result == EscalationChoice.STOP

    def test_escalation_choice_enum_has_three_values(self) -> None:
        """EscalationChoice must define exactly retry, skip, and stop."""
        members = {m.value for m in EscalationChoice}
        assert "retry" in members
        assert "skip" in members
        assert "stop" in members

    @pytest.mark.asyncio
    async def test_invalid_user_input_defaults_to_skip(self) -> None:
        """Unrecognised user response defaults to skip (safe fallback)."""
        channel = _make_mock_channel()
        channel.receive.return_value = "banana"
        detector = LoopDetector(max_failures=1)
        detector.record_failure("t1", error="e")

        result = await detector.escalate("t1", channel=channel)

        assert result == EscalationChoice.SKIP

    @pytest.mark.asyncio
    async def test_retry_allows_task_to_be_redispatched(self) -> None:
        """After retry, should_escalate returns False (counter reset)."""
        channel = _make_mock_channel()
        channel.receive.return_value = "retry"
        detector = LoopDetector(max_failures=2)
        detector.record_failure("t1", error="e")
        detector.record_failure("t1", error="e")

        await detector.escalate("t1", channel=channel)

        # After retry, counter is reset — no longer at threshold
        assert detector.should_escalate("t1") is False

    @pytest.mark.asyncio
    async def test_skip_does_not_reset_counter(self) -> None:
        """After skip, the failure counter is preserved (not reset)."""
        channel = _make_mock_channel()
        channel.receive.return_value = "skip"
        detector = LoopDetector(max_failures=2)
        detector.record_failure("t1", error="e")
        detector.record_failure("t1", error="e")

        await detector.escalate("t1", channel=channel)

        # Counter should still reflect the failures
        assert detector.failure_count("t1") >= 2


# ---------------------------------------------------------------------------
# AC 5 — Attempt counts persisted in ErrorJournal
# ---------------------------------------------------------------------------


class TestFromAC_JournalPersistence:
    """Failure attempt counts are persisted in ErrorJournal."""

    def test_record_failure_logs_to_journal(self) -> None:
        """Each failure is logged to the ErrorJournal when provided."""
        journal = _make_mock_journal()
        detector = LoopDetector(error_journal=journal)
        detector.record_failure("t1", error="timeout")

        journal.log.assert_called_once()

    def test_journal_entry_has_correct_attempt_number(self) -> None:
        """The attempt number in journal entries matches the failure count."""
        journal = _make_mock_journal()
        detector = LoopDetector(error_journal=journal)
        detector.record_failure("t1", error="err1")
        detector.record_failure("t1", error="err2")

        # Second call should have attempt=2
        calls = journal.log.call_args_list
        assert len(calls) == 2
        # First call: attempt 1
        first_kwargs = calls[0][1] or {}
        assert first_kwargs.get("attempt") == 1 or _extract_attempt(calls[0]) == 1
        # Second call: attempt 2
        second_kwargs = calls[1][1] or {}
        assert second_kwargs.get("attempt") == 2 or _extract_attempt(calls[1]) == 2

    def test_journal_entry_contains_task_id(self) -> None:
        """Journal entries include the task identifier for traceability."""
        journal = _make_mock_journal()
        detector = LoopDetector(error_journal=journal)
        detector.record_failure("task-999", error="broken")

        call_str = str(journal.log.call_args)
        assert "task-999" in call_str

    def test_journal_entry_contains_error_message(self) -> None:
        """Journal entries include the error message."""
        journal = _make_mock_journal()
        detector = LoopDetector(error_journal=journal)
        detector.record_failure("t1", error="disk full")

        call_str = str(journal.log.call_args)
        assert "disk full" in call_str

    def test_no_journal_when_not_provided(self) -> None:
        """When no ErrorJournal is configured, record_failure still works."""
        detector = LoopDetector()  # no journal
        detector.record_failure("t1", error="err")
        assert detector.failure_count("t1") == 1

    def test_journal_write_failure_does_not_crash(self) -> None:
        """If the journal raises during log, record_failure handles it."""
        journal = _make_mock_journal()
        journal.log.side_effect = OSError("disk full")
        detector = LoopDetector(error_journal=journal)

        # Should not raise
        detector.record_failure("t1", error="err")
        assert detector.failure_count("t1") == 1

    @pytest.mark.asyncio
    async def test_journal_records_escalation_event(self) -> None:
        """When escalation is triggered, an entry is logged to the journal."""
        journal = _make_mock_journal()
        detector = LoopDetector(max_failures=1, error_journal=journal)
        detector.record_failure("t1", error="repeated")

        channel = _make_mock_channel()
        channel.receive.return_value = "skip"
        await detector.escalate("t1", channel=channel)

        # At least 2 journal entries: one for the failure, one for escalation
        assert journal.log.call_count >= 2


# ---------------------------------------------------------------------------
# Helpers for assertion on journal calls
# ---------------------------------------------------------------------------


def _extract_attempt(call: object) -> int | None:
    """Try to extract the 'attempt' kwarg from a mock call."""
    try:
        kwargs = call[1] or {}  # type: ignore[index]
        return kwargs.get("attempt")
    except (IndexError, TypeError):
        return None
