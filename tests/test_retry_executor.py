"""RED-phase tests for make_retry_executor hook executor factory (#996).

Tests describe the contract for:

    def make_retry_executor(state, kanban, ...) -> Executor

All tests MUST FAIL until make_retry_executor is implemented in owlbear.daemon.

Imports verified against AC1:
- owlbear.daemon: make_retry_executor, OrchestratorState, RetryEntry, schedule_task_retry
- owlbear.core.hook_reaction_router: HookReactionRouter
"""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock

import pytest

# ---------------------------------------------------------------------------
# AC2: Factory returns a callable
# ---------------------------------------------------------------------------


class TestFromAC_RetryExecutorFactory:
    """AC2: make_retry_executor factory returns a callable."""

    def test_make_retry_executor_returns_callable(self) -> None:
        """AC2: factory returns callable(result) == True."""
        from owlbear.daemon import OrchestratorState, make_retry_executor

        state = OrchestratorState()
        kanban = AsyncMock()
        result = make_retry_executor(state=state, kanban=kanban)
        assert callable(result)


# ---------------------------------------------------------------------------
# AC3-AC5: Executor unit behaviour
# ---------------------------------------------------------------------------


class TestFromAC_RetryExecutorUnit:
    """AC3-AC5: Executor behaviour for various input data cases."""

    @pytest.mark.asyncio
    async def test_retry_executor_missing_task_id_logs_warning(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """AC3: Empty data dict → warning-level log + state.retries stays empty."""
        from owlbear.daemon import OrchestratorState, make_retry_executor

        state = OrchestratorState()
        kanban = AsyncMock()
        executor = make_retry_executor(state=state, kanban=kanban)

        with caplog.at_level(logging.WARNING):
            await executor({})

        assert state.retries == {}
        assert any(r.levelno == logging.WARNING for r in caplog.records)

    @pytest.mark.asyncio
    async def test_retry_executor_budget_exceeded_skips(self) -> None:
        """AC4: outcome=budget_exceeded → state.retries remains empty."""
        from owlbear.daemon import OrchestratorState, make_retry_executor

        state = OrchestratorState()
        kanban = AsyncMock()
        executor = make_retry_executor(state=state, kanban=kanban)

        await executor({"task_id": "1", "outcome": "budget_exceeded"})

        assert state.retries == {}

    @pytest.mark.asyncio
    async def test_retry_executor_failure_schedules_entry(self) -> None:
        """AC5: outcome=failure → RetryEntry in state.retries with attempt==1 and error text."""
        from owlbear.daemon import OrchestratorState, RetryEntry, make_retry_executor

        state = OrchestratorState()
        kanban = AsyncMock()
        executor = make_retry_executor(state=state, kanban=kanban)

        await executor({"task_id": "1", "outcome": "failure", "error": "boom"})

        assert "1" in state.retries
        entry = state.retries["1"]
        assert isinstance(entry, RetryEntry)
        assert entry.attempt == 1
        assert "boom" in entry.last_error


# ---------------------------------------------------------------------------
# AC6-AC7: Integration tests
# ---------------------------------------------------------------------------


class TestFromAC_RetryExecutorIntegration:
    """AC6-AC7: Integration with HookRegistry and HookReactionRouter."""

    @pytest.mark.asyncio
    async def test_retry_executor_integration_via_hooks(self) -> None:
        """AC6: Full wire-up schedules RetryEntry when hook is emitted with failure outcome."""
        from owlbear.config import HookReactionRule
        from owlbear.core.hook_reaction_router import HookReactionRouter
        from owlbear.core.hooks import HookEvent, HookRegistry
        from owlbear.daemon import OrchestratorState, RetryEntry, make_retry_executor

        state = OrchestratorState()
        kanban = AsyncMock()

        rule = HookReactionRule(
            events=["task_complete"],
            actions=["retry"],
            match={"outcome": "failure"},
        )
        executor = make_retry_executor(state=state, kanban=kanban)
        router = HookReactionRouter(rules=[rule], executors={"retry": executor})
        hooks = HookRegistry()
        router.register(hooks)

        await hooks.emit(
            HookEvent.TASK_COMPLETE,
            {"task_id": "42", "outcome": "failure", "error": "test error"},
        )

        assert "42" in state.retries
        assert isinstance(state.retries["42"], RetryEntry)

    @pytest.mark.asyncio
    async def test_retry_executor_idempotent_with_reconcile(self) -> None:
        """AC7: Executor is no-op when RetryEntry already exists from schedule_task_retry."""
        from owlbear.daemon import (
            OrchestratorState,
            make_retry_executor,
            schedule_task_retry,
        )

        state = OrchestratorState()
        kanban = AsyncMock()

        # Seed state via direct schedule_task_retry call → attempt=1
        await schedule_task_retry(
            state=state,
            kanban=kanban,
            task_id="1",
            error=RuntimeError("first error"),
            max_attempts=5,
            backoff_base=10.0,
            backoff_max=320.0,
        )
        assert state.retries["1"].attempt == 1

        # Fire executor for the same task — should be idempotent (no-op)
        executor = make_retry_executor(state=state, kanban=kanban)
        await executor({"task_id": "1", "outcome": "failure", "error": "second error"})

        assert state.retries["1"].attempt == 1
