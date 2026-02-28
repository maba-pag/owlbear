"""Tests for owlbear.providers.copilot_multipliers — premium request lookup."""

from __future__ import annotations

from owlbear.providers.copilot_multipliers import get_premium_requests

# ---------------------------------------------------------------------------
# Known base models — 1.0 multiplier
# ---------------------------------------------------------------------------


class TestBaseModels:
    """Base models like gpt-4o cost 1 premium request."""

    def test_gpt4o_returns_one(self) -> None:
        assert get_premium_requests("gpt-4o") == 1.0

    def test_returns_float_type(self) -> None:
        result = get_premium_requests("gpt-4o")
        assert isinstance(result, float)


# ---------------------------------------------------------------------------
# Unknown model — defaults to 1.0
# ---------------------------------------------------------------------------


class TestUnknownModel:
    """Unknown models default to 1.0 premium request."""

    def test_unknown_model_defaults_to_one(self) -> None:
        assert get_premium_requests("totally-fake-model-xyz") == 1.0

    def test_empty_string_defaults_to_one(self) -> None:
        assert get_premium_requests("") == 1.0


# ---------------------------------------------------------------------------
# Reasoning models — multiplier > 1.0
# ---------------------------------------------------------------------------


class TestReasoningModels:
    """Known reasoning models have a multiplier greater than 1.0."""

    def test_o1_returns_greater_than_one(self) -> None:
        result = get_premium_requests("o1")
        assert result > 1.0

    def test_o3_mini_returns_greater_than_one(self) -> None:
        result = get_premium_requests("o3-mini")
        assert result > 1.0

    def test_reasoning_multiplier_is_float(self) -> None:
        result = get_premium_requests("o1")
        assert isinstance(result, float)
