"""RED-phase tests for schedule_task_retry standalone function (#990 / #984).

Tests describe the contract for:
    async def schedule_task_retry(
        *, state, kanban, task_id, error, max_attempts, backoff_base, backoff_max
    ) -> None

All tests MUST FAIL until #984 extracts the function from reconcile_tasks.

AC1 — function signature (added by #984 test-writer)
AC6 — reconcile_tasks delegates (added by #984 test-writer)
AC2/AC3/AC4/AC5 — already covered by #990 classes below.
"""

from __future__ import annotations

import asyncio
import inspect
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_retry_entry(task_id: str, attempt: int, delay_seconds: float = 10.0) -> object:
    """Build a RetryEntry pre-seeded in state for existing-retry scenarios."""
    from owlbear.daemon import RetryEntry

    return RetryEntry(
        task_id=task_id,
        attempt=attempt,
        next_due=datetime.now(UTC) + timedelta(seconds=delay_seconds),
        last_error="prior error",
    )


# ---------------------------------------------------------------------------
# AC2: Successful retry scheduling
# ---------------------------------------------------------------------------


class TestFromAC_ScheduleTaskRetry_Schedule:
    """schedule_task_retry writes RetryEntry to state.retries on first failure."""

    @pytest.mark.asyncio
    async def test_first_failure_creates_retry_entry(self) -> None:
        """AC2: state.retries[tid] receives a RetryEntry on first call."""
        from owlbear.daemon import OrchestratorState, RetryEntry, schedule_task_retry

        state = OrchestratorState()
        state.claimed.add("t1")
        mock_kanban = AsyncMock()

        await schedule_task_retry(
            state=state,
            kanban=mock_kanban,
            task_id="t1",
            error=RuntimeError("boom"),
            max_attempts=5,
            backoff_base=10.0,
            backoff_max=320.0,
        )

        assert "t1" in state.retries
        assert isinstance(state.retries["t1"], RetryEntry)

    @pytest.mark.asyncio
    async def test_first_failure_attempt_is_one(self) -> None:
        """AC2: Fresh task gets attempt=1 on first failure."""
        from owlbear.daemon import OrchestratorState, schedule_task_retry

        state = OrchestratorState()
        state.claimed.add("t2")
        mock_kanban = AsyncMock()

        await schedule_task_retry(
            state=state,
            kanban=mock_kanban,
            task_id="t2",
            error=RuntimeError("crash"),
            max_attempts=5,
            backoff_base=10.0,
            backoff_max=320.0,
        )

        assert state.retries["t2"].attempt == 1

    @pytest.mark.asyncio
    async def test_entry_delay_matches_compute_retry_delay(self) -> None:
        """AC2: next_due offset equals _compute_retry_delay(attempt=1, base, max)."""
        from owlbear.daemon import OrchestratorState, _compute_retry_delay, schedule_task_retry

        state = OrchestratorState()
        state.claimed.add("t3")
        mock_kanban = AsyncMock()
        before = datetime.now(UTC)

        await schedule_task_retry(
            state=state,
            kanban=mock_kanban,
            task_id="t3",
            error=RuntimeError("x"),
            max_attempts=5,
            backoff_base=10.0,
            backoff_max=320.0,
        )

        after = datetime.now(UTC)
        expected_delay = _compute_retry_delay(attempt=1, base=10.0, maximum=320.0)
        entry = state.retries["t3"]
        # next_due should be approximately now + expected_delay
        assert entry.next_due >= before + timedelta(seconds=expected_delay)
        assert entry.next_due <= after + timedelta(seconds=expected_delay)

    @pytest.mark.asyncio
    async def test_entry_last_error_contains_exception_message(self) -> None:
        """AC2: last_error is derived from str(error)."""
        from owlbear.daemon import OrchestratorState, schedule_task_retry

        state = OrchestratorState()
        state.claimed.add("t4")
        mock_kanban = AsyncMock()

        await schedule_task_retry(
            state=state,
            kanban=mock_kanban,
            task_id="t4",
            error=RuntimeError("agent exploded"),
            max_attempts=5,
            backoff_base=10.0,
            backoff_max=320.0,
        )

        assert "agent exploded" in state.retries["t4"].last_error

    @pytest.mark.asyncio
    async def test_task_stays_in_claimed_after_scheduling(self) -> None:
        """AC2: task_id remains in state.claimed (retry pending, slot held)."""
        from owlbear.daemon import OrchestratorState, schedule_task_retry

        state = OrchestratorState()
        state.claimed.add("t5")
        mock_kanban = AsyncMock()

        await schedule_task_retry(
            state=state,
            kanban=mock_kanban,
            task_id="t5",
            error=RuntimeError("fail"),
            max_attempts=5,
            backoff_base=10.0,
            backoff_max=320.0,
        )

        assert "t5" in state.claimed

    @pytest.mark.asyncio
    async def test_second_failure_increments_attempt(self) -> None:
        """AC2: Second call (pre-existing entry at attempt=1) writes attempt=2."""
        from owlbear.daemon import OrchestratorState, schedule_task_retry

        state = OrchestratorState()
        state.claimed.add("t6")
        mock_kanban = AsyncMock()
        # Pre-seed: first failure already happened
        state.retries["t6"] = _make_retry_entry("t6", attempt=1)  # type: ignore[assignment]

        await schedule_task_retry(
            state=state,
            kanban=mock_kanban,
            task_id="t6",
            error=RuntimeError("second crash"),
            max_attempts=5,
            backoff_base=10.0,
            backoff_max=320.0,
        )

        assert state.retries["t6"].attempt == 2

    @pytest.mark.asyncio
    async def test_second_failure_delay_doubles(self) -> None:
        """AC2: attempt=2 uses delay = base*2**(2-1) = 20s (doubled from attempt=1)."""
        from owlbear.daemon import OrchestratorState, schedule_task_retry

        state = OrchestratorState()
        state.claimed.add("t7")
        mock_kanban = AsyncMock()
        state.retries["t7"] = _make_retry_entry("t7", attempt=1)  # type: ignore[assignment]
        before = datetime.now(UTC)

        await schedule_task_retry(
            state=state,
            kanban=mock_kanban,
            task_id="t7",
            error=RuntimeError("again"),
            max_attempts=5,
            backoff_base=10.0,
            backoff_max=320.0,
        )

        after = datetime.now(UTC)
        # delay for attempt=2 with base=10: 10 * 2^1 = 20s
        assert state.retries["t7"].next_due >= before + timedelta(seconds=20)
        assert state.retries["t7"].next_due <= after + timedelta(seconds=20)

    @pytest.mark.asyncio
    async def test_normal_retry_does_not_call_kanban_edit(self) -> None:
        """AC2: Retry scheduling (not exhaustion) must NOT call kanban_edit."""
        from owlbear.daemon import OrchestratorState, schedule_task_retry

        state = OrchestratorState()
        state.claimed.add("t8")
        mock_kanban = AsyncMock()

        await schedule_task_retry(
            state=state,
            kanban=mock_kanban,
            task_id="t8",
            error=RuntimeError("transient"),
            max_attempts=5,
            backoff_base=10.0,
            backoff_max=320.0,
        )

        mock_kanban.kanban_edit.assert_not_called()


# ---------------------------------------------------------------------------
# AC3: Exhaustion blocking
# ---------------------------------------------------------------------------


class TestFromAC_ScheduleTaskRetry_Exhaustion:
    """When next_attempt > max_attempts, block on kanban and clean up state."""

    @pytest.mark.asyncio
    async def test_exhaustion_calls_kanban_edit_with_block(self) -> None:
        """AC3: kanban.kanban_edit(task_id, block=...) called on exhaustion."""
        from owlbear.daemon import OrchestratorState, schedule_task_retry

        state = OrchestratorState()
        state.claimed.add("e1")
        mock_kanban = AsyncMock()
        mock_kanban.kanban_edit = AsyncMock(return_value="ok")
        # Pre-seed: already at attempt=5 (max_attempts=5), next would be 6 > 5
        state.retries["e1"] = _make_retry_entry("e1", attempt=5)  # type: ignore[assignment]

        await schedule_task_retry(
            state=state,
            kanban=mock_kanban,
            task_id="e1",
            error=RuntimeError("sixth fail"),
            max_attempts=5,
            backoff_base=10.0,
            backoff_max=320.0,
        )

        mock_kanban.kanban_edit.assert_called_once()
        call_kwargs = mock_kanban.kanban_edit.call_args
        assert call_kwargs is not None
        # Must pass block= keyword argument
        block_arg = call_kwargs.kwargs.get("block", "")
        assert block_arg, "block= kwarg must be non-empty"

    @pytest.mark.asyncio
    async def test_exhaustion_pops_from_retries(self) -> None:
        """AC3: state.retries[task_id] is popped on exhaustion."""
        from owlbear.daemon import OrchestratorState, schedule_task_retry

        state = OrchestratorState()
        state.claimed.add("e2")
        mock_kanban = AsyncMock()
        state.retries["e2"] = _make_retry_entry("e2", attempt=5)  # type: ignore[assignment]

        await schedule_task_retry(
            state=state,
            kanban=mock_kanban,
            task_id="e2",
            error=RuntimeError("exhausted"),
            max_attempts=5,
            backoff_base=10.0,
            backoff_max=320.0,
        )

        assert "e2" not in state.retries

    @pytest.mark.asyncio
    async def test_exhaustion_discards_from_claimed(self) -> None:
        """AC3: state.claimed.discard(task_id) called on exhaustion."""
        from owlbear.daemon import OrchestratorState, schedule_task_retry

        state = OrchestratorState()
        state.claimed.add("e3")
        mock_kanban = AsyncMock()
        state.retries["e3"] = _make_retry_entry("e3", attempt=5)  # type: ignore[assignment]

        await schedule_task_retry(
            state=state,
            kanban=mock_kanban,
            task_id="e3",
            error=RuntimeError("no more retries"),
            max_attempts=5,
            backoff_base=10.0,
            backoff_max=320.0,
        )

        assert "e3" not in state.claimed

    @pytest.mark.asyncio
    async def test_exhaustion_block_reason_mentions_attempts(self) -> None:
        """AC3: block reason references attempt count or last error."""
        from owlbear.daemon import OrchestratorState, schedule_task_retry

        state = OrchestratorState()
        state.claimed.add("e4")
        mock_kanban = AsyncMock()
        mock_kanban.kanban_edit = AsyncMock(return_value="ok")
        state.retries["e4"] = _make_retry_entry("e4", attempt=3)  # type: ignore[assignment]

        await schedule_task_retry(
            state=state,
            kanban=mock_kanban,
            task_id="e4",
            error=RuntimeError("last error message"),
            max_attempts=3,
            backoff_base=10.0,
            backoff_max=320.0,
        )

        call_args = mock_kanban.kanban_edit.call_args
        block_str = call_args.kwargs.get("block", "")
        # Block reason must mention exhaustion or last error
        assert any(
            word in block_str.lower()
            for word in ("exhaust", "attempt", "retry", "error", "last error message")
        )


# ---------------------------------------------------------------------------
# AC4: Budget-exceeded bypass
# ---------------------------------------------------------------------------


class TestFromAC_ScheduleTaskRetry_BudgetExceeded:
    """BudgetExceededError triggers immediate block with no RetryEntry created."""

    @pytest.mark.asyncio
    async def test_budget_exceeded_calls_kanban_edit(self) -> None:
        """AC4: kanban.kanban_edit(task_id, block=...) called for BudgetExceededError."""
        from owlbear.core.errors import BudgetExceededError
        from owlbear.daemon import OrchestratorState, schedule_task_retry

        state = OrchestratorState()
        state.claimed.add("b1")
        mock_kanban = AsyncMock()
        mock_kanban.kanban_edit = AsyncMock(return_value="ok")

        await schedule_task_retry(
            state=state,
            kanban=mock_kanban,
            task_id="b1",
            error=BudgetExceededError("$10 limit"),
            max_attempts=5,
            backoff_base=10.0,
            backoff_max=320.0,
        )

        mock_kanban.kanban_edit.assert_called_once()

    @pytest.mark.asyncio
    async def test_budget_exceeded_discards_from_claimed(self) -> None:
        """AC4: state.claimed.discard(task_id) called for BudgetExceededError."""
        from owlbear.core.errors import BudgetExceededError
        from owlbear.daemon import OrchestratorState, schedule_task_retry

        state = OrchestratorState()
        state.claimed.add("b2")
        mock_kanban = AsyncMock()

        await schedule_task_retry(
            state=state,
            kanban=mock_kanban,
            task_id="b2",
            error=BudgetExceededError("over limit"),
            max_attempts=5,
            backoff_base=10.0,
            backoff_max=320.0,
        )

        assert "b2" not in state.claimed

    @pytest.mark.asyncio
    async def test_budget_exceeded_no_retry_entry_created(self) -> None:
        """AC4: state.retries must NOT contain task_id after BudgetExceededError."""
        from owlbear.core.errors import BudgetExceededError
        from owlbear.daemon import OrchestratorState, schedule_task_retry

        state = OrchestratorState()
        state.claimed.add("b3")
        mock_kanban = AsyncMock()

        await schedule_task_retry(
            state=state,
            kanban=mock_kanban,
            task_id="b3",
            error=BudgetExceededError("exceeded"),
            max_attempts=5,
            backoff_base=10.0,
            backoff_max=320.0,
        )

        assert "b3" not in state.retries

    @pytest.mark.asyncio
    async def test_budget_exceeded_block_reason_mentions_budget(self) -> None:
        """AC4: block reason communicates budget context."""
        from owlbear.core.errors import BudgetExceededError
        from owlbear.daemon import OrchestratorState, schedule_task_retry

        state = OrchestratorState()
        state.claimed.add("b4")
        mock_kanban = AsyncMock()
        mock_kanban.kanban_edit = AsyncMock(return_value="ok")

        await schedule_task_retry(
            state=state,
            kanban=mock_kanban,
            task_id="b4",
            error=BudgetExceededError("$5.00 limit reached"),
            max_attempts=5,
            backoff_base=10.0,
            backoff_max=320.0,
        )

        call_args = mock_kanban.kanban_edit.call_args
        block_str = call_args.kwargs.get("block", "")
        assert "budget" in block_str.lower() or "exceeded" in block_str.lower()


# ---------------------------------------------------------------------------
# AC5: Idempotency
# ---------------------------------------------------------------------------


class TestFromAC_ScheduleTaskRetry_Idempotency:
    """Concurrent calls for same task_id produce at most one state mutation."""

    @pytest.mark.asyncio
    async def test_idempotent_concurrent_calls_write_retry_once(self) -> None:
        """AC5: Two concurrent calls starting from same state write only attempt=1.

        Simulates two coroutines computing next_attempt=1 concurrently (neither
        sees a prior entry). After both complete, attempt must be 1 — not 2.
        The idempotency guard ('state.retries[tid].attempt >= computed_next_attempt')
        must fire for the second call after the first writes the entry.
        """
        from owlbear.daemon import OrchestratorState, schedule_task_retry

        state = OrchestratorState()
        state.claimed.add("idem1")
        mock_kanban = AsyncMock()
        error = RuntimeError("transient fail")

        await asyncio.gather(
            schedule_task_retry(
                state=state,
                kanban=mock_kanban,
                task_id="idem1",
                error=error,
                max_attempts=5,
                backoff_base=10.0,
                backoff_max=320.0,
            ),
            schedule_task_retry(
                state=state,
                kanban=mock_kanban,
                task_id="idem1",
                error=error,
                max_attempts=5,
                backoff_base=10.0,
                backoff_max=320.0,
            ),
        )

        # Idempotency: attempt must be 1, not 2 (second call was no-op)
        assert "idem1" in state.retries
        assert state.retries["idem1"].attempt == 1

    @pytest.mark.asyncio
    async def test_idempotent_concurrent_no_extra_kanban_call(self) -> None:
        """AC5: Two concurrent calls produce zero kanban_edit calls (normal retry path)."""
        from owlbear.daemon import OrchestratorState, schedule_task_retry

        state = OrchestratorState()
        state.claimed.add("idem2")
        mock_kanban = AsyncMock()
        error = RuntimeError("fail")

        await asyncio.gather(
            schedule_task_retry(
                state=state,
                kanban=mock_kanban,
                task_id="idem2",
                error=error,
                max_attempts=5,
                backoff_base=10.0,
                backoff_max=320.0,
            ),
            schedule_task_retry(
                state=state,
                kanban=mock_kanban,
                task_id="idem2",
                error=error,
                max_attempts=5,
                backoff_base=10.0,
                backoff_max=320.0,
            ),
        )

        # Normal retry path never calls kanban_edit
        mock_kanban.kanban_edit.assert_not_called()

    @pytest.mark.asyncio
    async def test_idempotent_guard_prevents_lower_attempt_overwrite(self) -> None:
        """AC5: Guard 'state.retries[tid].attempt >= computed_next_attempt' → return.

        Scenario: a concurrent call already advanced entry to attempt=2.
        This call computed next_attempt=2 (from stale prev.attempt=1 snapshot).
        Guard fires: 2 >= 2 → return early, state unchanged.

        Verified via asyncio.gather with initial state having no entry — both
        calls compute next_attempt=1, but only one should write. The first
        completes, the second detects state.retries[tid].attempt==1 >= 1 → no-op.
        """
        from owlbear.daemon import OrchestratorState, schedule_task_retry

        state = OrchestratorState()
        state.claimed.add("idem3")
        mock_kanban = AsyncMock()

        # Run three concurrent calls — with the idempotency guard, only the first
        # should write attempt=1; the rest are no-ops once the entry exists.
        error = RuntimeError("concurrent fail")
        await asyncio.gather(
            schedule_task_retry(
                state=state,
                kanban=mock_kanban,
                task_id="idem3",
                error=error,
                max_attempts=5,
                backoff_base=10.0,
                backoff_max=320.0,
            ),
            schedule_task_retry(
                state=state,
                kanban=mock_kanban,
                task_id="idem3",
                error=error,
                max_attempts=5,
                backoff_base=10.0,
                backoff_max=320.0,
            ),
            schedule_task_retry(
                state=state,
                kanban=mock_kanban,
                task_id="idem3",
                error=error,
                max_attempts=5,
                backoff_base=10.0,
                backoff_max=320.0,
            ),
        )

        # Guard must prevent attempt from being 2 or 3 from triple-increment
        assert "idem3" in state.retries
        assert state.retries["idem3"].attempt == 1


# ---------------------------------------------------------------------------
# AC6: Kanban failure during block — not propagated
# ---------------------------------------------------------------------------


class TestFromAC_ScheduleTaskRetry_KanbanFailure:
    """kanban.kanban_edit raising during block must not propagate the exception."""

    @pytest.mark.asyncio
    async def test_kanban_failure_during_exhaustion_not_propagated(self) -> None:
        """AC6: kanban_edit raising on exhaustion is swallowed (logged, not re-raised)."""
        from owlbear.daemon import OrchestratorState, schedule_task_retry

        state = OrchestratorState()
        state.claimed.add("kf1")
        mock_kanban = AsyncMock()
        mock_kanban.kanban_edit = AsyncMock(side_effect=RuntimeError("kanban down"))
        state.retries["kf1"] = _make_retry_entry("kf1", attempt=5)  # type: ignore[assignment]

        # Must not raise — exception is logged and swallowed
        await schedule_task_retry(
            state=state,
            kanban=mock_kanban,
            task_id="kf1",
            error=RuntimeError("sixth fail"),
            max_attempts=5,
            backoff_base=10.0,
            backoff_max=320.0,
        )

        # State still cleaned up despite kanban failure
        assert "kf1" not in state.claimed

    @pytest.mark.asyncio
    async def test_kanban_failure_during_budget_block_not_propagated(self) -> None:
        """AC6: kanban_edit raising on budget-exceeded is swallowed (logged, not re-raised)."""
        from owlbear.core.errors import BudgetExceededError
        from owlbear.daemon import OrchestratorState, schedule_task_retry

        state = OrchestratorState()
        state.claimed.add("kf2")
        mock_kanban = AsyncMock()
        mock_kanban.kanban_edit = AsyncMock(side_effect=ConnectionError("network gone"))

        # Must not raise
        await schedule_task_retry(
            state=state,
            kanban=mock_kanban,
            task_id="kf2",
            error=BudgetExceededError("limit hit"),
            max_attempts=5,
            backoff_base=10.0,
            backoff_max=320.0,
        )

        # claimed still discarded despite kanban error
        assert "kf2" not in state.claimed


# ---------------------------------------------------------------------------
# AC1: schedule_task_retry exists as a module-level async function with the
#      correct signature  (added for #984 task)
# ---------------------------------------------------------------------------


class TestFromAC_ScheduleTaskRetry_Signature:
    """AC1: function exists at module level with keyword-only args and returns None."""

    def test_is_importable_from_daemon(self) -> None:
        """schedule_task_retry is importable from owlbear.daemon as a callable."""
        from owlbear.daemon import schedule_task_retry

        assert callable(schedule_task_retry)

    def test_is_async_function(self) -> None:
        """schedule_task_retry is a coroutine function (async def)."""
        from owlbear.daemon import schedule_task_retry

        assert asyncio.iscoroutinefunction(schedule_task_retry)

    def test_has_required_parameters(self) -> None:
        """Signature includes all seven required parameters from AC1."""
        from owlbear.daemon import schedule_task_retry

        sig = inspect.signature(schedule_task_retry)
        params = set(sig.parameters.keys())
        required = {
            "state",
            "kanban",
            "task_id",
            "error",
            "max_attempts",
            "backoff_base",
            "backoff_max",
        }
        assert required.issubset(params), f"Missing parameters: {required - params}"

    def test_all_params_are_keyword_only(self) -> None:
        """All parameters must be keyword-only (function uses * separator)."""
        from owlbear.daemon import schedule_task_retry

        sig = inspect.signature(schedule_task_retry)
        for name, param in sig.parameters.items():
            assert param.kind in (
                inspect.Parameter.KEYWORD_ONLY,
                inspect.Parameter.VAR_KEYWORD,
            ), f"Parameter '{name}' is not keyword-only"


# ---------------------------------------------------------------------------
# AC6: reconcile_tasks calls schedule_task_retry instead of inline retry logic
#      (added for #984 task)
# ---------------------------------------------------------------------------


class TestFromAC_ReconcileCallsScheduleTaskRetry:
    """AC6: reconcile_tasks delegates retry logic to schedule_task_retry on failure."""

    @pytest.mark.asyncio
    async def test_reconcile_calls_schedule_task_retry_on_failure(self) -> None:
        """Failed task triggers schedule_task_retry call instead of inline retry."""
        from owlbear.daemon import OrchestratorState, RunningTask, reconcile_tasks

        state = OrchestratorState()
        mock_kanban = AsyncMock()

        dummy = MagicMock(spec=asyncio.Task)
        dummy.done.return_value = True
        dummy.exception.return_value = RuntimeError("agent fail")

        state.running["rc1"] = RunningTask(task_id="rc1", asyncio_task=dummy)
        state.claimed.add("rc1")

        schedule_calls: list[dict[str, object]] = []

        async def mock_schedule(**kwargs: object) -> None:
            schedule_calls.append(dict(kwargs))

        with patch("owlbear.daemon.schedule_task_retry", side_effect=mock_schedule):
            await reconcile_tasks(state=state, kanban=mock_kanban)

        assert len(schedule_calls) == 1, (
            "reconcile_tasks must delegate to schedule_task_retry on failure. "
            f"Got {len(schedule_calls)} calls."
        )

    @pytest.mark.asyncio
    async def test_reconcile_passes_state_kanban_task_id_error(self) -> None:
        """schedule_task_retry receives state, kanban, task_id, and error from reconcile."""
        from owlbear.daemon import OrchestratorState, RunningTask, reconcile_tasks

        state = OrchestratorState()
        mock_kanban = AsyncMock()

        error = RuntimeError("delegate-me")
        dummy = MagicMock(spec=asyncio.Task)
        dummy.done.return_value = True
        dummy.exception.return_value = error

        state.running["rc2"] = RunningTask(task_id="rc2", asyncio_task=dummy)
        state.claimed.add("rc2")

        schedule_calls: list[dict[str, object]] = []

        async def mock_schedule(**kwargs: object) -> None:
            schedule_calls.append(dict(kwargs))

        with patch("owlbear.daemon.schedule_task_retry", side_effect=mock_schedule):
            await reconcile_tasks(state=state, kanban=mock_kanban)

        call = schedule_calls[0]
        assert call["state"] is state
        assert call["kanban"] is mock_kanban
        assert call["task_id"] == "rc2"
        assert call["error"] is error

    @pytest.mark.asyncio
    async def test_reconcile_passes_retry_config_params(self) -> None:
        """schedule_task_retry receives max_attempts, backoff_base, backoff_max from reconcile."""
        from owlbear.daemon import (
            _DEFAULT_BACKOFF_BASE,
            _DEFAULT_BACKOFF_MAX,
            _DEFAULT_MAX_RETRY_ATTEMPTS,
            OrchestratorState,
            RunningTask,
            reconcile_tasks,
        )

        state = OrchestratorState()
        mock_kanban = AsyncMock()

        dummy = MagicMock(spec=asyncio.Task)
        dummy.done.return_value = True
        dummy.exception.return_value = RuntimeError("x")

        state.running["rc3"] = RunningTask(task_id="rc3", asyncio_task=dummy)
        state.claimed.add("rc3")

        schedule_calls: list[dict[str, object]] = []

        async def mock_schedule(**kwargs: object) -> None:
            schedule_calls.append(dict(kwargs))

        with patch("owlbear.daemon.schedule_task_retry", side_effect=mock_schedule):
            await reconcile_tasks(state=state, kanban=mock_kanban)

        call = schedule_calls[0]
        assert call["max_attempts"] == _DEFAULT_MAX_RETRY_ATTEMPTS
        assert call["backoff_base"] == _DEFAULT_BACKOFF_BASE
        assert call["backoff_max"] == _DEFAULT_BACKOFF_MAX

    @pytest.mark.asyncio
    async def test_reconcile_passes_custom_retry_config(self) -> None:
        """Custom max_retry_attempts/backoff values are forwarded to schedule_task_retry."""
        from owlbear.daemon import OrchestratorState, RunningTask, reconcile_tasks

        state = OrchestratorState()
        mock_kanban = AsyncMock()

        dummy = MagicMock(spec=asyncio.Task)
        dummy.done.return_value = True
        dummy.exception.return_value = RuntimeError("y")

        state.running["rc4"] = RunningTask(task_id="rc4", asyncio_task=dummy)
        state.claimed.add("rc4")

        schedule_calls: list[dict[str, object]] = []

        async def mock_schedule(**kwargs: object) -> None:
            schedule_calls.append(dict(kwargs))

        with patch("owlbear.daemon.schedule_task_retry", side_effect=mock_schedule):
            await reconcile_tasks(
                state=state,
                kanban=mock_kanban,
                max_retry_attempts=7,
                backoff_base=15.0,
                backoff_max=500.0,
            )

        call = schedule_calls[0]
        assert call["max_attempts"] == 7
        assert call["backoff_base"] == 15.0
        assert call["backoff_max"] == 500.0

    @pytest.mark.asyncio
    async def test_reconcile_does_not_call_schedule_on_success(self) -> None:
        """Successful tasks do not trigger schedule_task_retry."""
        from owlbear.daemon import OrchestratorState, RunningTask, reconcile_tasks

        state = OrchestratorState()
        mock_kanban = AsyncMock()
        mock_kanban.kanban_move.return_value = "moved"

        dummy = MagicMock(spec=asyncio.Task)
        dummy.done.return_value = True
        dummy.exception.return_value = None

        state.running["rc5"] = RunningTask(task_id="rc5", asyncio_task=dummy)
        state.claimed.add("rc5")

        schedule_calls: list[dict[str, object]] = []

        async def mock_schedule(**kwargs: object) -> None:  # noqa: ARG001
            schedule_calls.append({})

        with patch("owlbear.daemon.schedule_task_retry", side_effect=mock_schedule):
            await reconcile_tasks(state=state, kanban=mock_kanban)

        assert len(schedule_calls) == 0
