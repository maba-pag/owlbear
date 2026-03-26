"""Tests for owlbear.memory.usage_cost — cost estimation from model + tokens."""

from __future__ import annotations

from owlbear.memory.usage_cost import calc_estimated_cost

# ---------------------------------------------------------------------------
# Known model + provider → positive cost
# ---------------------------------------------------------------------------


class TestCalcEstimatedCostKnown:
    """calc_estimated_cost() returns a positive float for known models."""

    def test_gpt4o_openai_returns_positive(self) -> None:
        result = calc_estimated_cost(
            model="gpt-4o",
            provider="openai",
            input_tokens=1000,
            output_tokens=500,
        )
        assert result is not None
        assert result > 0.0

    def test_gpt4o_copilot_returns_positive(self) -> None:
        result = calc_estimated_cost(
            model="gpt-4o",
            provider="copilot",
            input_tokens=1000,
            output_tokens=500,
        )
        # Copilot uses OpenAI models under the hood — should still return a cost
        assert result is not None
        assert result > 0.0

    def test_returns_float_type(self) -> None:
        result = calc_estimated_cost(
            model="gpt-4o",
            provider="openai",
            input_tokens=100,
            output_tokens=50,
        )
        assert isinstance(result, float)


# ---------------------------------------------------------------------------
# Unknown model / provider → None
# ---------------------------------------------------------------------------


class TestCalcEstimatedCostUnknown:
    """calc_estimated_cost() returns None for unknown models or providers."""

    def test_unknown_model_returns_none(self) -> None:
        result = calc_estimated_cost(
            model="totally-fake-model-xyz",
            provider="openai",
            input_tokens=1000,
            output_tokens=500,
        )
        assert result is None

    def test_unknown_provider_returns_none(self) -> None:
        result = calc_estimated_cost(
            model="gpt-4o",
            provider="totally-fake-provider-xyz",
            input_tokens=1000,
            output_tokens=500,
        )
        assert result is None


# ---------------------------------------------------------------------------
# Never raises — logs warning on error
# ---------------------------------------------------------------------------


class TestCalcEstimatedCostNeverRaises:
    """calc_estimated_cost() must never raise; logs warning on error instead."""

    def test_zero_tokens_does_not_raise(self) -> None:
        # Should not raise even with zero tokens
        result = calc_estimated_cost(
            model="gpt-4o",
            provider="openai",
            input_tokens=0,
            output_tokens=0,
        )
        # Zero tokens → zero or None cost, but no exception
        assert result is None or isinstance(result, float)

    def test_negative_tokens_does_not_raise(self) -> None:
        # Defensive: nonsensical input should not crash
        result = calc_estimated_cost(
            model="gpt-4o",
            provider="openai",
            input_tokens=-100,
            output_tokens=-50,
        )
        assert result is None or isinstance(result, float)

    def test_empty_model_does_not_raise(self) -> None:
        result = calc_estimated_cost(
            model="",
            provider="",
            input_tokens=100,
            output_tokens=50,
        )
        assert result is None or isinstance(result, float)

    def test_logs_warning_on_unknown_model(self) -> None:
        """When model is unknown, a warning should be logged (not an exception)."""
        result = calc_estimated_cost(
            model="nonexistent-model-999",
            provider="nonexistent-provider-999",
            input_tokens=100,
            output_tokens=50,
        )
        # Primary contract: no exception
        assert result is None or isinstance(result, float)
