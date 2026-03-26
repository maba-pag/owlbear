"""Tests for _record_usage exception consolidation (#528, #816).

These tests verify the refactored _record_usage contracts:
- Single enrichment try/except block (cost + premium as unit)
- logger.warning on all failure paths (not debug)
- Partial-success: enrichment failure → core record still saved with
  estimated_cost_usd=None, premium_requests=None
- Premium-only failure preserves cost (AC #816)
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from pydantic_ai.messages import ModelRequest, ModelResponse, TextPart, UserPromptPart

from owlbear.core.agent import OwlBearAgent
from owlbear.memory.session import SessionStore
from owlbear.memory.usage import UsageTracker


def _mock_result_with_usage(
    output: str,
    messages: list[object],
    *,
    input_tokens: int = 100,
    output_tokens: int = 50,
) -> MagicMock:
    """Build a mock PydanticAI result that includes a .usage() method."""
    result = MagicMock()
    result.output = output
    result.all_messages.return_value = messages
    usage = MagicMock()
    usage.input_tokens = input_tokens
    usage.output_tokens = output_tokens
    usage.cache_read_tokens = 0
    usage.cache_write_tokens = 0
    usage.requests = 1
    usage.tool_calls = 0
    result.usage.return_value = usage
    return result


def _simple_messages() -> list[object]:
    return [
        ModelRequest(parts=[UserPromptPart(content="hi")]),
        ModelResponse(parts=[TextPart(content="ok")]),
    ]


def _make_agent(tmp_path: Path, *, provider: str = "copilot") -> tuple[OwlBearAgent, UsageTracker]:
    """Create an OwlBearAgent wired to a fresh tracker."""
    tracker = UsageTracker(tmp_path / "usage.jsonl")
    agent = OwlBearAgent(
        model="test",
        session=SessionStore(tmp_path / "s.jsonl"),
        tracker=tracker,
        provider=provider,
    )
    mock = _mock_result_with_usage("ok", _simple_messages())
    agent.inner = MagicMock()
    agent.inner.run = AsyncMock(return_value=mock)
    return agent, tracker


class TestFromACEnrichmentFailsAsUnit:
    """When calc_estimated_cost raises, the entire enrichment block fails.

    After consolidation, cost + premium are in a single try/except.
    If cost raises, premium lookup is skipped and both fields are None.
    """

    def test_cost_raises_both_fields_none(self, tmp_path: Path) -> None:
        """cost raise → estimated_cost_usd=None AND premium_requests=None."""
        agent, tracker = _make_agent(tmp_path, provider="copilot")

        with patch(
            "owlbear.memory.usage_cost.calc_estimated_cost",
            side_effect=Exception("cost boom"),
        ):
            asyncio.run(agent.turn("hi"))

        records = tracker.load()
        assert len(records) == 1
        assert records[0].estimated_cost_usd is None
        # KEY ASSERTION: after consolidation, premium is also None when cost raises
        assert records[0].premium_requests is None


class TestFromACLogLevelWarning:
    """All logger calls in _record_usage must use WARNING, not DEBUG."""

    def test_enrichment_failure_logs_warning(self, tmp_path: Path, caplog: object) -> None:
        """Enrichment block failure logs at WARNING with exc_info."""
        agent, _tracker = _make_agent(tmp_path, provider="copilot")

        with (
            patch(
                "owlbear.memory.usage_cost.calc_estimated_cost",
                side_effect=Exception("cost fail"),
            ),
            caplog.at_level(logging.DEBUG, logger="owlbear.core.agent"),  # type: ignore[union-attr]
        ):
            asyncio.run(agent.turn("hi"))

        warning_records = [
            r
            for r in caplog.records  # type: ignore[union-attr]
            if r.levelno == logging.WARNING and "owlbear.core.agent" in r.name
        ]
        assert len(warning_records) >= 1, (
            "Expected at least one WARNING log from enrichment failure; "
            f"got levels: {[r.levelname for r in caplog.records]}"  # type: ignore[union-attr]
        )
        # exc_info must be set (logs the traceback)
        assert any(r.exc_info for r in warning_records), "WARNING log should include exc_info=True"

    def test_outer_usage_failure_logs_warning(self, tmp_path: Path, caplog: object) -> None:
        """When result.usage() itself raises, log at WARNING not DEBUG."""
        tracker = UsageTracker(tmp_path / "usage.jsonl")
        agent = OwlBearAgent(
            model="test",
            session=SessionStore(tmp_path / "s.jsonl"),
            tracker=tracker,
            provider="copilot",
        )
        mock_result = MagicMock()
        mock_result.output = "ok"
        mock_result.all_messages.return_value = _simple_messages()
        mock_result.usage.side_effect = RuntimeError("usage() exploded")

        agent.inner = MagicMock()
        agent.inner.run = AsyncMock(return_value=mock_result)

        with caplog.at_level(logging.DEBUG, logger="owlbear.core.agent"):  # type: ignore[union-attr]
            asyncio.run(agent.turn("hi"))

        warning_records = [
            r
            for r in caplog.records  # type: ignore[union-attr]
            if r.levelno == logging.WARNING and "owlbear.core.agent" in r.name
        ]
        assert len(warning_records) >= 1, (
            "Expected WARNING for outer usage failure; "
            f"got levels: {[r.levelname for r in caplog.records]}"  # type: ignore[union-attr]
        )

    def test_no_debug_level_in_record_usage(self, tmp_path: Path, caplog: object) -> None:
        """After refactor, _record_usage should never log at DEBUG for errors."""
        agent, _tracker = _make_agent(tmp_path, provider="copilot")

        with (
            patch(
                "owlbear.memory.usage_cost.calc_estimated_cost",
                side_effect=Exception("boom"),
            ),
            caplog.at_level(logging.DEBUG, logger="owlbear.core.agent"),  # type: ignore[union-attr]
        ):
            asyncio.run(agent.turn("hi"))

        debug_records = [
            r
            for r in caplog.records  # type: ignore[union-attr]
            if r.levelno == logging.DEBUG
            and "owlbear.core.agent" in r.name
            and any(
                kw in r.message.lower()
                for kw in ("cost", "usage", "premium", "enrichment", "unavailable")
            )
        ]
        assert len(debug_records) == 0, (
            f"_record_usage should log at WARNING, not DEBUG; found {debug_records}"
        )


class TestFromACStructuralConstraints:
    """Structural assertions: at most 2 exception handlers, single enrichment block."""

    def test_at_most_two_except_handlers(self) -> None:
        """_record_usage method body contains at most 2 'except' keywords."""
        import ast
        import inspect
        import textwrap

        source = inspect.getsource(OwlBearAgent._record_usage)
        source = textwrap.dedent(source)
        tree = ast.parse(source)

        except_count = sum(1 for node in ast.walk(tree) if isinstance(node, ast.ExceptHandler))
        assert except_count <= 2, (
            f"_record_usage should have at most 2 except handlers, found {except_count}"
        )

    def test_no_logger_debug_calls_in_source(self) -> None:
        """_record_usage source contains no logger.debug calls."""
        import inspect

        source = inspect.getsource(OwlBearAgent._record_usage)
        assert "logger.debug" not in source, (
            "All logger calls in _record_usage should be logger.warning, not logger.debug"
        )


# ---------------------------------------------------------------------------
# AC #816: premium-only failure path
# ---------------------------------------------------------------------------


class TestFromACPremiumFailureCostPreserved:
    """AC2: When get_premium_requests raises but cost succeeds,
    record is still created with cost set and premium_requests=None.
    """

    def test_premium_raises_cost_preserved_premium_none(self, tmp_path: Path) -> None:
        """Cost value is preserved when premium lookup fails."""
        agent, tracker = _make_agent(tmp_path, provider="copilot")

        with (
            patch(
                "owlbear.memory.usage_cost.calc_estimated_cost",
                return_value=0.0042,
            ),
            patch(
                "owlbear.providers.copilot_multipliers.get_premium_requests",
                side_effect=Exception("premium boom"),
            ),
        ):
            asyncio.run(agent.turn("hi"))

        records = tracker.load()
        assert len(records) == 1
        assert records[0].estimated_cost_usd == 0.0042, (
            "Cost must be preserved when only premium lookup fails"
        )
        assert records[0].premium_requests is None, (
            "Premium must be None when get_premium_requests raises"
        )

    def test_premium_failure_core_record_still_appended(self, tmp_path: Path) -> None:
        """Core record fields (tokens, model, provider) intact despite premium failure."""
        agent, tracker = _make_agent(tmp_path, provider="copilot")

        with (
            patch(
                "owlbear.memory.usage_cost.calc_estimated_cost",
                return_value=0.01,
            ),
            patch(
                "owlbear.providers.copilot_multipliers.get_premium_requests",
                side_effect=RuntimeError("multiplier lookup exploded"),
            ),
        ):
            asyncio.run(agent.turn("hi"))

        records = tracker.load()
        assert len(records) == 1
        assert records[0].input_tokens == 100
        assert records[0].output_tokens == 50
        assert records[0].model == "test"
        assert records[0].provider == "copilot"


class TestFromACPremiumFailureLogging:
    """AC3 (premium path): premium failure specifically logs WARNING with exc_info."""

    def test_premium_failure_logs_warning_with_exc_info(
        self, tmp_path: Path, caplog: object
    ) -> None:
        """When get_premium_requests raises, WARNING is logged with exc_info."""
        agent, _tracker = _make_agent(tmp_path, provider="copilot")

        with (
            patch(
                "owlbear.memory.usage_cost.calc_estimated_cost",
                return_value=0.01,
            ),
            patch(
                "owlbear.providers.copilot_multipliers.get_premium_requests",
                side_effect=Exception("premium fail"),
            ),
            caplog.at_level(logging.DEBUG, logger="owlbear.core.agent"),  # type: ignore[union-attr]
        ):
            asyncio.run(agent.turn("hi"))

        warning_records = [
            r
            for r in caplog.records  # type: ignore[union-attr]
            if r.levelno == logging.WARNING and "owlbear.core.agent" in r.name
        ]
        assert len(warning_records) >= 1, (
            "Expected WARNING log from premium failure; "
            f"got levels: {[r.levelname for r in caplog.records]}"  # type: ignore[union-attr]
        )
        assert any(r.exc_info for r in warning_records), (
            "WARNING log for premium failure should include exc_info=True"
        )
