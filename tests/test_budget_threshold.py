"""Tests for budget threshold feature — task #750.

RED phase: all tests must fail against the current codebase because
BudgetExceededError, BUDGET_WARNING, BudgetWarningData, _check_budget,
and budget_limit_usd do not exist yet.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from owlbear.config import OwlBearSettings
from owlbear.core.errors import ErrorCategory, classify_error
from owlbear.core.hooks import HookEvent, HookRegistry
from owlbear.memory.usage import UsageSummary

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run(coro: object) -> object:
    """Run an async coroutine synchronously."""
    return asyncio.run(coro)  # type: ignore[arg-type]


def _make_done_task(*, exception: BaseException | None = None) -> MagicMock:
    """Create a mock asyncio.Task that reports done with optional exception."""
    t = MagicMock(spec=asyncio.Task)
    t.done.return_value = True
    t.exception.return_value = exception
    t.result.return_value = None
    return t


def _make_mock_agent_result() -> MagicMock:
    """Build a mock result object with usage() and all_messages()."""
    usage = MagicMock()
    usage.input_tokens = 100
    usage.output_tokens = 50
    usage.cache_read_tokens = 0
    usage.cache_write_tokens = 0
    usage.requests = 1
    usage.tool_calls = 0

    result = MagicMock()
    result.usage.return_value = usage
    result.all_messages.return_value = []
    result.output = "response text"
    return result


def _make_agent(
    *,
    tracker: MagicMock | None = None,
    hooks: HookRegistry | None = None,
    budget_limit_usd: float | None = None,
) -> object:
    """Build an OwlBearAgent with mocked session and optional tracker/hooks."""
    from owlbear.core.agent import OwlBearAgent

    session = MagicMock()
    session.load.return_value = []
    session.path = Path("test.jsonl")

    return OwlBearAgent(
        model="test",
        session=session,
        hooks=hooks,
        tracker=tracker,
        budget_limit_usd=budget_limit_usd,
    )


async def _run_turn(agent: object) -> str:
    """Run a single turn() with a mocked inner.run."""
    mock_result = _make_mock_agent_result()
    with patch.object(agent.inner, "run", new_callable=AsyncMock, return_value=mock_result):  # type: ignore[union-attr]
        return await agent.turn("test prompt")  # type: ignore[union-attr]


# ===================================================================
# AC1: OwlBearSettings.budget_limit_usd field + validator
# ===================================================================


class TestFromAC_SettingsBudgetLimit:  # noqa: N801
    """OwlBearSettings must have a budget_limit_usd field that defaults
    to None (unlimited) and validates > 0 when set."""

    def test_default_is_none(self) -> None:
        """budget_limit_usd defaults to None (unlimited)."""
        settings = OwlBearSettings()
        assert settings.budget_limit_usd is None

    def test_accepts_positive_float(self) -> None:
        """budget_limit_usd accepts a positive float value."""
        settings = OwlBearSettings(budget_limit_usd=10.0)
        assert settings.budget_limit_usd == 10.0

    def test_rejects_zero(self) -> None:
        """budget_limit_usd=0 must raise ValidationError (not extra_forbidden)."""
        with pytest.raises(ValidationError, match="budget_limit_usd") as exc_info:
            OwlBearSettings(budget_limit_usd=0.0)
        # Must fail because of value constraint, not because field doesn't exist
        assert "extra_forbidden" not in str(exc_info.value)

    def test_rejects_negative(self) -> None:
        """budget_limit_usd=-5 must raise ValidationError (not extra_forbidden)."""
        with pytest.raises(ValidationError, match="budget_limit_usd") as exc_info:
            OwlBearSettings(budget_limit_usd=-5.0)
        # Must fail because of value constraint, not because field doesn't exist
        assert "extra_forbidden" not in str(exc_info.value)

    def test_accepts_small_positive(self) -> None:
        """budget_limit_usd=0.01 is valid."""
        settings = OwlBearSettings(budget_limit_usd=0.01)
        assert settings.budget_limit_usd == pytest.approx(0.01)

    def test_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """OWLBEAR_BUDGET_LIMIT_USD env var overrides the default None."""
        monkeypatch.setenv("OWLBEAR_BUDGET_LIMIT_USD", "25.5")
        settings = OwlBearSettings()
        assert settings.budget_limit_usd == pytest.approx(25.5)


# ===================================================================
# AC2: OwlBearAgent.__init__ budget_limit_usd param
# ===================================================================


class TestFromAC_AgentBudgetParam:  # noqa: N801
    """OwlBearAgent.__init__ must accept budget_limit_usd and store it."""

    def test_agent_stores_budget_limit(self) -> None:
        """budget_limit_usd=5.0 is stored as self._budget_limit_usd."""
        agent = _make_agent(budget_limit_usd=5.0)
        assert agent._budget_limit_usd == 5.0  # type: ignore[union-attr]

    def test_agent_default_budget_is_none(self) -> None:
        """When omitted, _budget_limit_usd is None."""
        agent = _make_agent()
        assert agent._budget_limit_usd is None  # type: ignore[union-attr]


# ===================================================================
# AC3: HookEvent.BUDGET_WARNING + BudgetWarningData TypedDict
# ===================================================================


class TestFromAC_BudgetWarningHook:  # noqa: N801
    """HookEvent must have BUDGET_WARNING member; BudgetWarningData must exist."""

    def test_budget_warning_event_exists(self) -> None:
        """HookEvent.BUDGET_WARNING is a valid enum member."""
        assert hasattr(HookEvent, "BUDGET_WARNING")
        assert HookEvent.BUDGET_WARNING == "budget_warning"

    def test_budget_warning_data_typeddict_exists(self) -> None:
        """BudgetWarningData TypedDict is importable from hooks module."""
        from owlbear.core.hooks import BudgetWarningData

        # Verify it has the required keys
        annotations = BudgetWarningData.__annotations__
        assert "cost_usd" in annotations
        assert "limit_usd" in annotations
        assert "pct" in annotations

    def test_budget_warning_data_can_be_constructed(self) -> None:
        """BudgetWarningData can be instantiated with required fields."""
        from owlbear.core.hooks import BudgetWarningData

        data: BudgetWarningData = {
            "cost_usd": 4.0,
            "limit_usd": 5.0,
            "pct": 0.8,
        }
        assert data["cost_usd"] == 4.0
        assert data["limit_usd"] == 5.0
        assert data["pct"] == 0.8


# ===================================================================
# AC4: BudgetExceededError + classify_error PERMANENT
# ===================================================================


class TestFromAC_BudgetExceededError:  # noqa: N801
    """BudgetExceededError must exist and classify as PERMANENT."""

    def test_error_class_exists(self) -> None:
        """BudgetExceededError is importable from core.errors."""
        from owlbear.core.errors import BudgetExceededError

        assert issubclass(BudgetExceededError, Exception)

    def test_classify_error_returns_permanent(self) -> None:
        """classify_error(BudgetExceededError(...)) returns PERMANENT."""
        from owlbear.core.errors import BudgetExceededError

        exc = BudgetExceededError("over budget")
        assert classify_error(exc) == ErrorCategory.PERMANENT

    def test_error_carries_message(self) -> None:
        """BudgetExceededError stores a descriptive message."""
        from owlbear.core.errors import BudgetExceededError

        exc = BudgetExceededError("$5.00 limit exceeded at $5.50")
        assert "5.00" in str(exc)
        assert "5.50" in str(exc)


# ===================================================================
# AC5: turn() calls _check_budget after _record_usage
# ===================================================================


class TestFromAC_TurnBudgetCheck:  # noqa: N801
    """turn() must call _check_budget() after _record_usage() when
    budget_limit_usd is set, computing pct and emitting/raising accordingly."""

    def test_below_threshold_no_action(self) -> None:
        """When cost is 50% of limit, no warning or error."""
        hooks = HookRegistry()
        handler = MagicMock()
        hooks.register(HookEvent.BUDGET_WARNING, handler)

        tracker = MagicMock()
        tracker.summary.return_value = UsageSummary(total_cost_usd=2.5)

        agent = _make_agent(hooks=hooks, tracker=tracker, budget_limit_usd=5.0)
        _run(_run_turn(agent))

        handler.assert_not_called()

    def test_at_80_pct_emits_warning(self) -> None:
        """When cost reaches 80% of limit, BUDGET_WARNING is emitted."""
        hooks = HookRegistry()
        handler = MagicMock()
        hooks.register(HookEvent.BUDGET_WARNING, handler)

        tracker = MagicMock()
        tracker.summary.return_value = UsageSummary(total_cost_usd=4.0)

        agent = _make_agent(hooks=hooks, tracker=tracker, budget_limit_usd=5.0)
        result = _run(_run_turn(agent))

        # Warning emitted but turn continues (non-blocking)
        handler.assert_called_once()
        payload = handler.call_args[0][0]
        assert payload["pct"] == pytest.approx(0.8)
        assert payload["cost_usd"] == pytest.approx(4.0)
        assert payload["limit_usd"] == pytest.approx(5.0)
        assert result == "response text"

    def test_above_80_pct_emits_warning(self) -> None:
        """At 90% (above 80% threshold), warning is emitted."""
        hooks = HookRegistry()
        handler = MagicMock()
        hooks.register(HookEvent.BUDGET_WARNING, handler)

        tracker = MagicMock()
        tracker.summary.return_value = UsageSummary(total_cost_usd=4.5)

        agent = _make_agent(hooks=hooks, tracker=tracker, budget_limit_usd=5.0)
        result = _run(_run_turn(agent))

        handler.assert_called_once()
        assert result == "response text"

    def test_at_100_pct_raises_budget_exceeded(self) -> None:
        """When cost reaches 100% of limit, BudgetExceededError is raised."""
        from owlbear.core.errors import BudgetExceededError

        tracker = MagicMock()
        tracker.summary.return_value = UsageSummary(total_cost_usd=5.0)

        agent = _make_agent(hooks=HookRegistry(), tracker=tracker, budget_limit_usd=5.0)

        with pytest.raises(BudgetExceededError):
            _run(_run_turn(agent))

    def test_over_100_pct_raises_budget_exceeded(self) -> None:
        """When cost exceeds 100%, BudgetExceededError is raised."""
        from owlbear.core.errors import BudgetExceededError

        tracker = MagicMock()
        tracker.summary.return_value = UsageSummary(total_cost_usd=7.5)

        agent = _make_agent(hooks=HookRegistry(), tracker=tracker, budget_limit_usd=5.0)

        with pytest.raises(BudgetExceededError):
            _run(_run_turn(agent))

    def test_usage_recorded_even_at_100_pct(self) -> None:
        """Usage is always appended even when budget is exceeded."""
        from owlbear.core.errors import BudgetExceededError

        tracker = MagicMock()
        tracker.summary.return_value = UsageSummary(total_cost_usd=5.0)

        agent = _make_agent(hooks=HookRegistry(), tracker=tracker, budget_limit_usd=5.0)

        with pytest.raises(BudgetExceededError):
            _run(_run_turn(agent))

        # Usage was recorded before the budget check raised
        tracker.append.assert_called_once()


# ===================================================================
# AC6: reconcile_tasks skips retry for BudgetExceededError
# ===================================================================


class TestFromAC_ReconcileBudgetExceeded:  # noqa: N801
    """reconcile_tasks must skip retry logic when exc is BudgetExceededError
    and block the task immediately."""

    def test_budget_exceeded_blocks_immediately_no_retry(self) -> None:
        """BudgetExceededError causes immediate block, no retry scheduling."""
        from owlbear.core.errors import BudgetExceededError
        from owlbear.daemon import OrchestratorState, RunningTask, reconcile_tasks

        state = OrchestratorState()
        mock_kanban = AsyncMock()

        exc = BudgetExceededError("$5.00 limit reached")
        state.running["T1"] = RunningTask(
            task_id="T1",
            asyncio_task=_make_done_task(exception=exc),
        )
        state.claimed.add("T1")

        _run(reconcile_tasks(state=state, kanban=mock_kanban, max_retry_attempts=5))

        # Task is blocked on kanban with a reason mentioning budget
        mock_kanban.kanban_edit.assert_called_once()
        call_kwargs = mock_kanban.kanban_edit.call_args
        block_arg = call_kwargs.kwargs.get("block", "")
        assert "budget" in block_arg.lower()

        # No retry was scheduled
        assert "T1" not in state.retries
        # Task released from claimed
        assert "T1" not in state.claimed

    def test_budget_exceeded_first_attempt_no_retry(self) -> None:
        """Even on first attempt, BudgetExceededError does NOT schedule retry."""
        from owlbear.core.errors import BudgetExceededError
        from owlbear.daemon import OrchestratorState, RunningTask, reconcile_tasks

        state = OrchestratorState()
        mock_kanban = AsyncMock()

        exc = BudgetExceededError("over budget")
        state.running["T2"] = RunningTask(
            task_id="T2",
            asyncio_task=_make_done_task(exception=exc),
        )
        state.claimed.add("T2")

        _run(reconcile_tasks(state=state, kanban=mock_kanban, max_retry_attempts=5))

        # No retry scheduled
        assert "T2" not in state.retries
        # kanban_edit was called to block
        mock_kanban.kanban_edit.assert_called_once()


# ===================================================================
# AC7: None budget = zero overhead (no summary() call)
# ===================================================================


class TestFromAC_NoBudgetZeroOverhead:  # noqa: N801
    """When budget_limit_usd is None, tracker.summary() must NOT be called."""

    def test_no_summary_call_when_budget_is_none(self) -> None:
        """With budget=None, turn() should not call tracker.summary()."""
        tracker = MagicMock()
        agent = _make_agent(tracker=tracker)

        _run(_run_turn(agent))

        # Usage appended, but summary() never called
        tracker.append.assert_called_once()
        tracker.summary.assert_not_called()

    def test_no_warning_when_budget_is_none(self) -> None:
        """With budget=None, no BUDGET_WARNING hook is ever emitted."""
        hooks = HookRegistry()
        handler = MagicMock()
        hooks.register(HookEvent.BUDGET_WARNING, handler)

        tracker = MagicMock()
        agent = _make_agent(hooks=hooks, tracker=tracker)

        _run(_run_turn(agent))

        handler.assert_not_called()


# ===================================================================
# Boundary conditions for budget percentage calculation
# ===================================================================


class TestFromAC_BudgetBoundaryConditions:  # noqa: N801
    """Boundary conditions around 80% and 100% thresholds."""

    def test_just_below_80_pct_no_warning(self) -> None:
        """At 79.9% no warning should be emitted."""
        hooks = HookRegistry()
        handler = MagicMock()
        hooks.register(HookEvent.BUDGET_WARNING, handler)

        tracker = MagicMock()
        # 3.995 / 5.0 = 0.799 — just below 0.8
        tracker.summary.return_value = UsageSummary(total_cost_usd=3.995)

        agent = _make_agent(hooks=hooks, tracker=tracker, budget_limit_usd=5.0)
        _run(_run_turn(agent))

        handler.assert_not_called()

    def test_just_below_100_pct_warning_only(self) -> None:
        """At 99.9% warning is emitted but no error raised."""
        hooks = HookRegistry()
        handler = MagicMock()
        hooks.register(HookEvent.BUDGET_WARNING, handler)

        tracker = MagicMock()
        # 4.995 / 5.0 = 0.999 — above 0.8 but below 1.0
        tracker.summary.return_value = UsageSummary(total_cost_usd=4.995)

        agent = _make_agent(hooks=hooks, tracker=tracker, budget_limit_usd=5.0)
        result = _run(_run_turn(agent))

        handler.assert_called_once()
        assert result == "response text"

    def test_total_cost_none_treated_as_zero(self) -> None:
        """If summary().total_cost_usd is None, treated as 0 (no warning)."""
        hooks = HookRegistry()
        handler = MagicMock()
        hooks.register(HookEvent.BUDGET_WARNING, handler)

        tracker = MagicMock()
        tracker.summary.return_value = UsageSummary(total_cost_usd=None)

        agent = _make_agent(hooks=hooks, tracker=tracker, budget_limit_usd=5.0)
        _run(_run_turn(agent))

        handler.assert_not_called()

    def test_no_tracker_no_budget_check(self) -> None:
        """When tracker is None, no budget check even if limit is set."""
        hooks = HookRegistry()
        handler = MagicMock()
        hooks.register(HookEvent.BUDGET_WARNING, handler)

        agent = _make_agent(hooks=hooks, tracker=None, budget_limit_usd=5.0)
        _run(_run_turn(agent))

        handler.assert_not_called()
